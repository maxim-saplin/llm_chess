from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import random
import re
import json

app = FastAPI()

USE_THINKING = True
CALL_COUNT = 0
SCENARIO_TYPE = "default"  # Can be: "default", "wrong_actions", "max_turns", "max_moves", "invalid_action", "non_game_agent"

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[dict]
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    n: Optional[int] = None
    stream: Optional[bool] = None
    stop: Optional[str] = None
    max_tokens: Optional[int] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    logit_bias: Optional[dict] = None
    user: Optional[str] = None

class ChatCompletionResponse(BaseModel):
    id: str = "chatcmpl-123"
    object: str = "chat.completion"
    created: int = 1677652288
    model: str = "gpt-3.5-turbo"
    choices: List[dict]
    usage: dict

class MockChessBot:
    def __init__(self):
        self.board = [
            ["r", "n", "b", "q", "k", "b", "n", "r"],
            ["p", "p", "p", "p", "p", "p", "p", "p"],
            [" ", " ", " ", " ", " ", " ", " ", " "],
            [" ", " ", " ", " ", " ", " ", " ", " "],
            [" ", " ", " ", " ", " ", " ", " ", " "],
            [" ", " ", " ", " ", " ", " ", " ", " "],
            ["P", "P", "P", "P", "P", "P", "P", "P"],
            ["R", "N", "B", "Q", "K", "B", "N", "R"]
        ]

    def generate_reply(self, messages):
        global CALL_COUNT, SCENARIO_TYPE
        CALL_COUNT += 1

        # === NEW: NonGameAgent scenario ===
        if SCENARIO_TYPE == "non_game_agent":
            if CALL_COUNT == 1:
                return "First LLM worker response"
            elif CALL_COUNT == 2:
                return "Second LLM worker response"
            else:
                # synthesizer call must return a valid move
                return "make_move e2e4"
        # === existing scenarios below ===

        # ... existing logic ...

chess_bot = MockChessBot()

REQUEST_LOG: List[List[dict]] = []  # store each incoming messages list

@app.middleware("http")
async def log_requests(request: Request, call_next):
    if request.url.path.endswith("/chat/completions"):
        try:
            body = await request.json()
            REQUEST_LOG.append(body.get("messages", []))
        except:
            pass
    return await call_next(request)

@app.post("/v1/chat/completions")
async def create_chat_completion(request: ChatCompletionRequest):
    global CALL_COUNT, SCENARIO_TYPE
    response_text = None
    # Delegate to MockChessBot
    response_text = chess_bot.generate_reply(request.messages)
    return ChatCompletionResponse(
        choices=[{
            "message": {"role": "assistant", "content": response_text},
            "finish_reason": "stop",
            "index": 0
        }],
        usage={
            "prompt_tokens": 10,
            "completion_tokens": 10,
            "total_tokens": 20
        }
    )

# New endpoints for inspection
@app.get("/v1/requests")
def get_requests():
    return {"requests": REQUEST_LOG}

@app.get("/v1/call_count")
def get_call_count():
    return {"call_count": CALL_COUNT}

@app.post("/v1/reset")
async def reset_server_state(request: Request):
    global CALL_COUNT, USE_THINKING, SCENARIO_TYPE, REQUEST_LOG
    data = await request.json()
    CALL_COUNT = 0
    USE_THINKING = data.get("useThinking", False)
    SCENARIO_TYPE = data.get("scenarioType", "default")
    REQUEST_LOG = []
    return {"status": "success", "message": "Server state has been reset."}

def start_server(port):
    uvicorn.run(app, host="0.0.0.0", port=port)