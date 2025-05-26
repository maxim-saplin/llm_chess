Using LLM Chess default params - temp 0.3, top_p 1.0

Errors are treated as losses:

```
openai.BadRequestError: Error code: 400 - {'message': 'Please reduce the length of the messages or completion. Current length is 16425 while limit is 16382', 'type': 'invalid_request_error', 'param': 'messages', 'code': 'context_length_exceeded'}
```