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
SCENARIO_TYPE = "default"  # Can be: "default", "wrong_actions", "max_turns", "max_moves", "invalid_action", "non"

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
        
    def _generate_default_reply(self, messages: List[dict]) -> str:
        """Generates a reply based on the default logic."""
        last_message = messages[-1]["content"].strip()
        try:
            if self.flip_flag:
                self.flip_flag = False
                return "get_current_board" if not USE_THINKING else "<think>Thinking about my move...</think>get_current_board"
            
            # NoN, remove 'User query\\>\n\n ' and everything after '\n\nModel 1' if present
            # This will extract only the legal moves string
            if last_message.startswith("User query\\>"):
                # Find the start of the moves (after 'User query\\>\n\n ')
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

    def generate_reply(self, messages: List[dict]) -> str:
        global CALL_COUNT, SCENARIO_TYPE
        last_message = messages[-1]["content"].strip()
        CALL_COUNT += 1

        # Handle different scenarios
        if SCENARIO_TYPE == "wrong_actions":
            # Always return invalid responses to trigger too many wrong actions
            # Return something that's not a valid action format
            return "I'm thinking about my next move..."
                
        elif SCENARIO_TYPE == "max_turns":
            # Keep requesting the board without making a move to hit max_turns
            return "get_current_board"
            
        elif SCENARIO_TYPE == "max_moves":
            # Normal behavior but we'll let the test run until max_moves is reached
            if self.flip_flag:
                self.flip_flag = False
                return "get_current_board"
            
            legal_moves = last_message.split(",")
            if legal_moves and all(self._is_valid_move(move) for move in legal_moves):
                random_move = random.choice(legal_moves)
                self.flip_flag = True
                return f"make_move {random_move}" 
            
            return "get_legal_moves"
            
        elif SCENARIO_TYPE == "invalid_action":
            if CALL_COUNT == 1:
                return "some_invalid_action"
            elif CALL_COUNT == 2:
                # Make an invalid move format on the second call
                return "make_move d4d5" # Assuming this format is invalid based on context
        
        elif SCENARIO_TYPE == "non":
            if CALL_COUNT % 3 == 1 or CALL_COUNT % 3 == 2:
                return "non"
            else: # Every 3rd call
                # Reset flip_flag state for the default logic if needed, 
                # assuming the 3rd call should behave like the *first* default call.
                # If it should continue the default sequence state, remove this line.
                # self.flip_flag = True # Or manage state more carefully if needed
                return self._generate_default_reply(messages)

        # Default behavior uses the helper method
        return self._generate_default_reply(messages)
    
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
        
        return {"status": "success", "message": "Server state has been reset."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def start_server(port: int = 8080):
    uvicorn.run(app, host="127.0.0.1", port=port)


if __name__ == "__main__":
    start_server()
