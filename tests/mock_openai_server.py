from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import random
import re

app = FastAPI()

USE_THINKING = True # This doesn't influence rest of the tests anyway but is needed for `remove_text` tests

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
        last_message = messages[-1]["content"].strip()
        
        # Emulate Random Player logic
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

def start_server(port: int = 8080):
    uvicorn.run(app, host="127.0.0.1", port=port)

if __name__ == "__main__":
    start_server()
