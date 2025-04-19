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
SCENARIO_TYPE = "default"  # Can be: "default", "wrong_actions", "max_turns", "max_moves", "invalid_action"

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
                return "make_move d4d5"

        # Default behavior (same as original)
        try:
            if self.flip_flag:
                self.flip_flag = False
                return "get_current_board" if not USE_THINKING else "<think>Thinking about my move...</think>get_current_board"
            
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
            return bool(re.match(r'^[a-h][1-8][a-h][1-8][qrbn]?$', move))
        except Exception:
            return False

chess_bot = MockChessBot()

@app.post("/v1/chat/completions")
async def create_chat_completion(request: ChatCompletionRequest):
    try:
        # Log request with timestamp
        # timestamp = datetime.datetime.now().strftime("%H_%M_%S_%f")[:-3]
        # log_filename = f"/Users/admin/src/llm_chess/_temp/{timestamp}_request.json"
        
        # # Create log content with request details
        # log_content = {
        #     "timestamp": timestamp,
        #     "model": request.model,
        #     "messages": request.messages,
        #     "temperature": request.temperature,
        # }
        # with open(log_filename, "w") as f:
        #     json.dump(log_content, f, indent=2)

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
