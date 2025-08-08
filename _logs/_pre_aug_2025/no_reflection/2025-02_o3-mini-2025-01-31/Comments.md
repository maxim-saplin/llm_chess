## Instability

For o3 models I received odd instability, in some cases server dropped connection. At first I considered this to be some network instability not related to the model. Yet latter I noticed that it happen too often while at the same time I have never seen this rate of connection errors (and this sort of errors) with other OpenAI models. Reserching internet didn't yield conclusive results, other than some users reported similar issues with them being fixed by using different model alials. As well as there was a mention that this behavior could be related to model failure (some forum in regards to ChatGPT). I have also observed odd behaviour when using chat UI with o1 models when sometimes I received connection errors. For thr time being considering those errors as model errors and assinging losses to LLM.

```
httpx.RemoteProtocolError: peer closed connection without sending complete message body (incomplete chunked read)
```

The peer closed connection issues seem to pertain to low reasoning effort mode, also I tried o1-mini at about the same time and received a few of this errors as well

## Not using get_legal_moves action

- Low (_logs/no_reflection/2025-02-06-10_o3-mini-2025-01-31/2025-02-09_o3-mini-2025-01-31-low_1)
    - get_current_board: 2235
    - get_legal_moves: 1625
    - ratio (board/moves): 1.375
- Medium (_logs/no_reflection/2025-02-06-10_o3-mini-2025-01-31/2025-02-09_o3-mini-2025-01-31-medium_2)
    - get_current_board: 1338
    - get_legal_moves: 512
    - ratio (board/moves): 2.613
- Hard (_logs/no_reflection/2025-02-06-10_o3-mini-2025-01-31/2025-02-09_o3-mini-2025-01-31-high_24_GAMES_TIMEDOUT)
    - get_current_board: 902
    - get_legal_moves: 20
    - ratio (board/moves): 45.1
- o1-mini (_logs/no_reflection/2024-12-21_o1-mini-2024-09-12_3)
    - get_current_board: 730
    - get_legal_moves: 498
    - ratio (board/moves): 1.465
- Deepseek r1 (_logs/no_reflection/2025-01-22_deepSeek-r1)
    - get_current_board: 188
    - get_legal_moves: 97
    - ratio (board/moves): 1.938
- gpt-4-32k-0613 (_logs/no_reflection/2025-01-22_gpt-4-32k-0613_2)
    - get_current_board: 6
    - get_legal_moves: 978
    - ratio (board/moves): 0.006
- qwen-max-2025-01-25 (_logs/no_reflection/2025-01-30_qwen-max-2025-01-25_3)
    - get_current_board: 2000
    - get_legal_moves: 2006
    - ratio (board/moves): 0.997
- gemini-2.0-flash-001 (_logs/no_reflection/2025-02-05-09_gemini-2.0/2025-02-08_gemini-2.0-flash-001_2)
    - get_current_board: 358
    - get_legal_moves: 376
    - ratio (board/moves): 0.952
- anthropic.claude-v3-5-sonnet-v2 (_logs/no_reflection/2025-01-19_anthropic.claude-v3-5-sonnet-v2_2)
    - get_current_board: 1636
    - get_legal_moves: 1637
    - ratio (board/moves): 0.999
- gpt-4o-2024-11-20 (_logs/no_reflection/2025-01-16_gpt-4o-2024-11-20)
    - get_current_board: 860
    - get_legal_moves: 861
    - ratio board/moves: 0,999

### Ratios
- o3-mini-low: 1.375
- o3-mini-medium: 2.613
- o3-mini-hard: 45.1
- o1-mini: 1.465
- deepSeek-r1: 1.938
- gpt-4-32k: 0.006
- qwen-max-2025-01-25: 0.997
- gemini-2.0-flash-001: 0.952
- anthropic.claude-v3-5-sonnet-v2: 0.999
- gpt-4o-2024-11-20: 0.999

## Matching actions regex

Player_Black \(to Proxy\):(?:(?!\n-{3,})[\s\S])*?get_current_board[\s\S]*?\n-{3,}
Player_Black \(to Proxy\):(?:(?!\n-{3,})[\s\S])*?get_legal_moves[\s\S]*?\n-{3,}