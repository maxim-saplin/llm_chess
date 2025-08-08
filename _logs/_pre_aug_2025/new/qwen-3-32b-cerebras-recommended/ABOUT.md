Using Qwen 3 recommended params for thinking mode - temp 0.7, top_p 0.8 (vs 0.3/1.0). This helped mitigate the max length error with model goping into generating long scrolls of text, yet 1 ocaasion happened. Thinking mode (no /no_think passed in).

Errors are treated as losses:

```
openai.BadRequestError: Error code: 400 - {'message': 'Please reduce the length of the messages or completion. Current length is 16425 while limit is 16382', 'type': 'invalid_request_error', 'param': 'messages', 'code': 'context_length_exceeded'}
```