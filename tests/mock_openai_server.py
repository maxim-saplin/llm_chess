# import datetime
# import json
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import random
import re

app = FastAPI()

USE_THINKING = True
CALL_COUNT = 0
SCENARIO_TYPE = "default"  # Can be: "default", "wrong_actions", "max_turns", "max_moves", "invalid_action", "non", "non_max_turns", "non_max_moves"

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[dict]
    temperature: Optional[float] = 0.7

class ChatCompletionResponse(BaseModel):
    choices: List[dict]
    usage: dict

class MockChessBot:
    def __init__(self):
        self.flip_flag = True
        
    def generate_reply(self, messages: List[dict]) -> str:
        global CALL_COUNT, SCENARIO_TYPE
        # increment the incoming-call counter
        CALL_COUNT += 1

        # dispatch based on the active scenario
        handlers = {
            "wrong_actions": self._handle_wrong_actions,
            "max_turns":      self._handle_max_turns,
            "max_moves":      self._handle_max_moves,
            "invalid_action": self._handle_invalid_action,
            "non":            self._handle_non,
            "non_max_turns":  self._handle_non_max_turns,
            "non_max_moves":  self._handle_non_max_moves,
            "default":        self._handle_default,
        }
        handler = handlers.get(SCENARIO_TYPE, self._handle_default)
        return handler(messages)

    # ---- scenario-specific methods ----
    def _handle_wrong_actions(self, messages: List[dict]) -> str:
        return "I'm thinking about my next move..."

    def _handle_max_turns(self, messages: List[dict]) -> str:
        return "get_current_board"

    def _handle_non_max_turns(self, messages: List[dict]) -> str:
        # For NoN testing: first two calls are intermediate steps, every third is relevant
        if CALL_COUNT % 3 != 0:
            return "non"  # Intermediate step
        return "get_current_board"  # Actual response that will trigger max turns

    def _handle_non_max_moves(self, messages: List[dict]) -> str:
        """Handle the NoN max moves scenario by making valid moves to reach MAX_MOVES termination."""
        # The first two calls of every three should return "non" (intermediate steps)
        if CALL_COUNT % 3 != 0:
            return "non"  # Return "non" for the first two calls of every three
            
        # Keep a static counter to track actual chess move flow (every 3rd call)
        if not hasattr(self, '_move_counter'):
            self._move_counter = 0
        
        # Increment the counter for every 3rd call (actual chess logic)
        self._move_counter += 1
        
        # On even counts (2, 4, 6...), make a move. On odd counts (1, 3, 5...), get legal moves
        if self._move_counter % 2 == 0:  # Even counts: make a move
            # Extract legal moves from the last message
            last_message = messages[-1]["content"]
            moves = []
            for part in last_message.split(","):
                move = part.strip()
                if self._is_valid_move(move):
                    moves.append(move)
            
            if moves:
                return f"make_move {random.choice(moves)}"
        
        # On odd counts (or if no valid moves found above): get legal moves
        return "get_legal_moves"

    def _handle_max_moves(self, messages: List[dict]) -> str:
        last = messages[-1]["content"].strip()
        if self.flip_flag:
            self.flip_flag = False
            return "get_current_board"
        moves = last.split(",")
        if moves and all(self._is_valid_move(m) for m in moves):
            choice = random.choice(moves)
            self.flip_flag = True
            return f"make_move {choice}"
        return "get_legal_moves"

    def _handle_invalid_action(self, messages: List[dict]) -> str:
        # call #1 → totally invalid
        if CALL_COUNT == 1:
            return "some_invalid_action"
        # call #2 → malformed move
        if CALL_COUNT == 2:
            return "make_move d4d5"
        # afterwards fallback to default logic
        return self._handle_default(messages)

    def _handle_non(self, messages: List[dict]) -> str:
        # first two of every three calls: "non"
        if CALL_COUNT % 3 in (1, 2):
            return "non"
        return self._handle_default(messages)

    def _handle_default(self, messages: List[dict]) -> str:
        """Default behavior for normal chess moves."""
        last_message = messages[-1]["content"].strip()
        try:
            if self.flip_flag:
                self.flip_flag = False
                return "get_current_board" if not USE_THINKING else "<think>Thinking about my move...</think>get_current_board"
            
            # NoN, extract just the legal moves from the message
            if last_message.startswith("User query\\>"):
                user_query_marker = "User query\\>\n\n "
                model1_marker = "\n\nModel 1"
                start_idx = last_message.find(user_query_marker)
                if start_idx != -1:
                    start_idx += len(user_query_marker)
                    end_idx = last_message.find(model1_marker, start_idx)
                    if end_idx != -1:
                        last_message = last_message[start_idx:end_idx].strip()
                    else:
                        last_message = last_message[start_idx:].strip()
            
            legal_moves = last_message.split(",")
            if legal_moves and all(self._is_valid_move(move) for move in legal_moves):
                random_move = random.choice(legal_moves)
                self.flip_flag = True
                return f"make_move {random_move}" if not USE_THINKING else f"<think>Thinking about my move...</think>make_move {random_move}"
        except Exception:
            pass
        
        return "get_legal_moves" if not USE_THINKING else "<think>Thinking about my move...</think>get_legal_moves"

    def _is_valid_move(self, move: str) -> bool:
        try:
            return bool(re.match(r'^[a-h][1-8][a-h][1-8][qrbn]?$', move.strip()))
        except Exception:
            return False

chess_bot = MockChessBot()

@app.post("/v1/chat/completions")
async def create_chat_completion(request: ChatCompletionRequest):
    try:
        response = chess_bot.generate_reply(request.messages)
        
        return ChatCompletionResponse(
            choices=[{
                "message": {"role": "assistant", "content": response},
                "finish_reason": "stop",
                "index": 0
            }],
            usage={
                "prompt_tokens": 10,
                "completion_tokens": 10,
                "total_tokens": 20
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/reset")
async def reset_server_state(request: Request):
    try:
        data = await request.json()
        global CALL_COUNT, USE_THINKING, SCENARIO_TYPE

        CALL_COUNT = 0
        USE_THINKING = data.get("useThinking", False)
        SCENARIO_TYPE = data.get("scenarioType", "default")
        
        # Reset the chess bot's move counter if it exists
        if hasattr(chess_bot, '_move_counter'):
            chess_bot._move_counter = 0
        
        return {"status": "success", "message": "Server state has been reset."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def start_server(port: int = 8080):
    uvicorn.run(app, host="127.0.0.1", port=port)


if __name__ == "__main__":
    start_server()
