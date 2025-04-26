o4 mini used as synthesizer with the below prompt yieled poor results.

- System prompt:
```
You will be provided with a set of responses from various open-source models to the latest user query.
Your task is to synthesize these responses into a single, high-quality response in British English spelling.
It is crucial to critically evaluate the information provided in these responses, recognizing that some of it may be biased or incorrect.
Your response should not simply replicate the given answers but should offer a refined, accurate, and comprehensive reply to the instruction.
Ensure your response is well-structured, coherent and adheres to the highest standards of accuracy and reliability.
```

- Dialog:
<system prompt/>
<user message/>
<model response/>
<user's last message>
User query\\>

<|some text|>

Model 1 response\\>

<|some text|>

Model 2 response\\>

<|some text|>
</user's last message>

The failure mode is that the model didn't understand the task of synthesizing the answer but engaged in a dialog with the proxy:

```
Proxy (to NoN_Synthesizer):

You are a professional chess player and you play as black. Now is your turn to make a move. Before making a move you can pick one of the following actions:
- 'get_current_board' to get the schema and current status of the board
- 'get_legal_moves' to get a UCI formatted list of available moves
- 'make_move <UCI formatted move>' when you are ready to complete your turn (e.g., 'make_move e2e4')

--------------------------------------------------------------------------------
NoN_Synthesizer (to Proxy):

Both responses are identical—each asks for the current board—and are equally appropriate.
```