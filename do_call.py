import json
import os
import requests
from autogen import ConversableAgent
from utils import get_llms


def R(m):  # (has_reasoning, example_dict|None)
    c = (m or {}).get("custom_content") or {}
    for x in (c.get("state") or {}).get("claude_message_content") or []:
        if isinstance(x, dict) and x.get("type") == "thinking":
            s = x.get("signature")
            if isinstance(s, str) and len(s) > 48:
                s = s[:48] + "..."
            e = {"type": "thinking", "thinking": x.get("thinking")}
            if s is not None:
                e["signature"] = s
            return True, e
    t = c.get("stages")
    return (True, {"stages": t[:1]}) if isinstance(t, list) and t else (False, None)


_, cfg = get_llms(black_hyperparams={"reasoning_effort": "low"})
a = ConversableAgent("test", llm_config=cfg, max_consecutive_auto_reply=2, human_input_mode="NEVER")
print(a.generate_reply(messages=[{"role": "user", "content": "Hello, how are you?"}]))
print("AG2 custom reasoning:", "yes" if next((R(m)[0] for v in a._oai_messages.values() for m in reversed(v) if isinstance(m, dict) and m.get("role") == "assistant"), False) else "no")
print("--- Raw HTTP ---")
if os.getenv("MODEL_KIND_B") != "local":
    print("skip: not local")
elif not (u := os.getenv("LOCAL_BASE_URL_B", "").strip()) or not (k := os.getenv("LOCAL_API_KEY_B", "").strip()):
    print("skip: no URL/key")
else:
    p = (cfg.get("config_list") or [{}])[0]
    mt = p.get("max_tokens") or (65535 if "thinking" in os.getenv("LOCAL_MODEL_NAME_B", "").lower() else 256)
    try:
        r = requests.post(
            f"{u.rstrip('/')}/chat/completions?api-version=2024-02-01",
            headers={"Api-Key": k, "Content-Type": "application/json"},
            json={"messages": [{"role": "user", "content": "Say hi in 3 words"}], "max_tokens": int(mt)},
            timeout=120,
        )
    except requests.RequestException as e:
        print("HTTP error:", e)
    else:
        if r.status_code != 200:
            print(r.status_code, r.text[:400])
        else:
            try:
                d = r.json()
            except json.JSONDecodeError:
                print("bad json", r.text[:400])
            else:
                if d.get("error"):
                    print(json.dumps(d["error"], indent=2))
                else:
                    ok, sn = R((d.get("choices") or [{}])[0].get("message"))
                    print("reasoning:", "yes" if ok else "no")
                    if sn:
                        print(json.dumps(sn, indent=2))
