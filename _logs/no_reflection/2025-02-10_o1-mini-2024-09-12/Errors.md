There were 4 incomplete response errors (in 10 games), giving LLM losses there. SOmething I haven't seen back in December.

The errors seem to be swarmed at following one after another, which suggests there was some time dependent issue. Yet at teh same time in parallel I had o3-mini tested in Medium reasoninig effort, not a single error

```
  File "/home/user/src/llm_chess/.venv/lib/python3.11/site-packages/httpx/_transports/default.py", line 118, in map_httpcore_exceptions
    raise mapped_exc(message) from exc
httpx.RemoteProtocolError: peer closed connection without sending complete message body (incomplete chunked read)
```