"""Probe black model (.env): AG2 vs raw HTTP, low/high reasoning_effort. uv run python do_call.py"""

import json
import os

import requests
from autogen import ConversableAgent
from utils import get_llms

PROMPT = "You play black. One action: get_current_board, get_legal_moves, or make_move e7e5."
REASONING_EFFORTS = ("low", "high")


def fmt_usage(usage: dict) -> str:
    p = usage.get("prompt_tokens", 0)
    c = usage.get("completion_tokens", 0)
    t = usage.get("total_tokens", 0)
    r = (usage.get("completion_tokens_details") or {}).get("reasoning_tokens")
    if r is None:
        r = max(0, t - p - c)
        tag = "hidden"
    else:
        tag = "reasoning"
    return f"prompt={p}  completion={c}  {tag}={r}  total={t}"


def ag2_call(effort: str) -> None:
    _, cfg = get_llms(black_hyperparams={"reasoning_effort": effort})
    model = cfg["config_list"][0]["model"]
    agent = ConversableAgent("probe", llm_config=cfg, human_input_mode="NEVER")
    reply = agent.generate_reply(messages=[{"role": "user", "content": PROMPT}])
    usage = next(v for k, v in agent.get_total_usage().items() if k != "total_cost")
    print(f"  model={model}")
    print(f"  reply: {(reply or '')[:120]}")
    print(f"  {fmt_usage(usage)}")


def http_call(effort: str) -> None:
    get_llms()
    base = os.environ["AZURE_OPENAI_ENDPOINT_B"].rstrip("/")
    dep = os.environ["AZURE_OPENAI_DEPLOYMENT_B"]
    url = f"{base}/openai/deployments/{dep}/chat/completions"
    r = requests.post(
        url,
        params={"api-version": os.environ["AZURE_OPENAI_VERSION_B"]},
        headers={"api-key": os.environ["AZURE_OPENAI_KEY_B"], "Content-Type": "application/json"},
        json={"messages": [{"role": "user", "content": PROMPT}], "reasoning_effort": effort},
        timeout=180,
    )
    r.raise_for_status()
    data = r.json()
    msg = (data.get("choices") or [{}])[0].get("message", {})
    print(f"  model={dep}")
    print(f"  reply: {(msg.get('content') or '')[:120]}")
    print(f"  {fmt_usage(data.get('usage') or {})}")
    details = (data.get("usage") or {}).get("completion_tokens_details")
    if details:
        print(f"  completion_tokens_details: {json.dumps(details)}")


for effort in REASONING_EFFORTS:
    print(f"\n=== reasoning_effort={effort} ===")
    print("ag2:")
    ag2_call(effort)
    print("http:")
    http_call(effort)
