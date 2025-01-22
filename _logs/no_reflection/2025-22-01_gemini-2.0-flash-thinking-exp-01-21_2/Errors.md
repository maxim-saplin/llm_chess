Model happened to return empty response, counting as a loss:

```
Execution was halted due to error.
Exception details: list index out of range
Traceback (most recent call last):
  File "/private/var/user/src/llm_chess/llm_chess.py", line 304, in run
    chat_result = proxy_agent.initiate_chat(
                  ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/private/var/user/src/llm_chess/_ag/agentchat/conversable_agent.py", line 1255, in initiate_chat
    self.send(msg2send, recipient, request_reply=True, silent=silent)
  File "/private/var/user/src/llm_chess/_ag/agentchat/conversable_agent.py", line 869, in send
    recipient.receive(message, self, request_reply, silent)
  File "/private/var/user/src/llm_chess/_ag/agentchat/conversable_agent.py", line 1050, in receive
    reply = self.generate_reply(messages=self.chat_messages[sender], sender=sender)
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/private/var/user/src/llm_chess/custom_agents.py", line 49, in generate_reply
    return super().generate_reply(messages, sender, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/private/var/user/src/llm_chess/_ag/agentchat/conversable_agent.py", line 2335, in generate_reply
    final, reply = reply_func(
                   ^^^^^^^^^^^
  File "/private/var/user/src/llm_chess/_ag/agentchat/conversable_agent.py", line 1620, in generate_oai_reply
    extracted_response = self._generate_oai_reply_from_client(
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/private/var/user/src/llm_chess/_ag/agentchat/conversable_agent.py", line 1653, in _generate_oai_reply_from_client
    response = llm_client.create(
               ^^^^^^^^^^^^^^^^^^
  File "/private/var/user/src/llm_chess/_ag/oai/client.py", line 766, in create
    response = client.create(params)
               ^^^^^^^^^^^^^^^^^^^^^
  File "/private/var/user/src/llm_chess/.venv/lib/python3.12/site-packages/autogen/oai/gemini.py", line 243, in create
    ans: str = chat.history[-1].parts[0].text
               ~~~~~~~~~~~~~~~~~~~~~~^^^
  File "/private/var/user/src/llm_chess/.venv/lib/python3.12/site-packages/proto/marshal/collections/repeated.py", line 130, in __getitem__
    return self._marshal.to_python(self._pb_type, self.pb[key])
                                                  ~~~~~~~^^^^^
IndexError: list index out of range
```

Another issue is related to some copyright erorr code:
````
RuntimeError: Google GenAI exception occurred while calling Gemini API: finish_reason: RECITATION
```