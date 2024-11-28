There were 4 errors with same error message:

```
  File "/private/var/user/src/llm_chess/.venv/lib/python3.12/site-packages/openai/_base_client.py", line 1051, in _request
    raise self._make_status_error_from_response(err.response) from None
openai.InternalServerError: Error code: 500 - {'error': {'message': 'The model produced invalid content. Consider modifying your prompt if you are seeing this error persistently. You can retry your request, or contact us through an Azure support request at: https://go.microsoft.com/fwlink/?linkid=2213926 if the error persists. (Please include the request ID 3c7c86f9-8025-42c7-b83d-f8550cd94360 in your message.)', 'type': 'model_error', 'param': None, 'code': None}}
```