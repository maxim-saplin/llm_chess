The model sometimes replied with empty strings, which (when added to dailog) lead to consecutive error...

```
Proxy (to Player_Black):

You are a professional chess player and you play as black. Now is your turn to make a move. Before making a move you can pick one of the following actions:
- 'get_current_board' to get the schema and current status of the board
- 'get_legal_moves' to get a UCI formatted list of available moves
- 'make_move <UCI formatted move>' when you are ready to complete your turn (e.g., 'make_move e2e4')

--------------------------------------------------------------------------------
[autogen.oai.client: 11-06 13:07:25] {349} WARNING - Model None is not found. The cost will be 0. In your config_list, add field {"price" : [prompt_price_per_1k, completion_token_price_per_1k]} for customized pricing.
Player_Black (to Proxy):

get_current_board 


--------------------------------------------------------------------------------
Proxy (to Player_Black):

♜ ♞ ⭘ ⭘ ⭘ ♚ ⭘ ⭘
♟ ♟ ♟ ⭘ ⭘ ♟ ♜ ⭘
⭘ ⭘ ♙ ⭘ ⭘ ♙ ♟ ♟
⭘ ⭘ ⭘ ♟ ⭘ ⭘ ⭘ ♞
♙ ♙ ⭘ ♙ ♝ ♟ ⭘ ♙
⭘ ⭘ ⭘ ⭘ ⭘ ⭘ ⭘ ⭘
♖ ♘ ♕ ⭘ ♙ ♙ ♗ ♘
⭘ ⭘ ⭘ ⭘ ♔ ⭘ ⭘ ♖

--------------------------------------------------------------------------------
[autogen.oai.client: 11-06 13:07:26] {349} WARNING - Model None is not found. The cost will be 0. In your config_list, add field {"price" : [prompt_price_per_1k, completion_token_price_per_1k]} for customized pricing.
Player_Black (to Proxy):

get_legal_moves


--------------------------------------------------------------------------------
Proxy (to Player_Black):

f8g8,f8e8,b8d7,b8c6,b8a6,g7g8,g7h7,h5f6,h5g3,e4f5,e4f3,e4d3,e4g2,e4c2,b7c6,b7b6,a7a6,g6g5,f4f3,b7b5,a7a5

--------------------------------------------------------------------------------
[autogen.oai.client: 11-06 13:07:33] {349} WARNING - Model None is not found. The cost will be 0. In your config_list, add field {"price" : [prompt_price_per_1k, completion_token_price_per_1k]} for customized pricing.
Player_Black (to Proxy):

make_move g7g5


--------------------------------------------------------------------------------
Proxy (to Player_Black):

Failed to make move: illegal uci: 'g7g5' in rn3k2/ppp2pr1/2P2Ppp/3p3n/PP1Pbp1P/8/RNQ1PPBN/4K2R b - - 0 37

--------------------------------------------------------------------------------
[autogen.oai.client: 11-06 13:07:34] {349} WARNING - Model None is not found. The cost will be 0. In your config_list, add field {"price" : [prompt_price_per_1k, completion_token_price_per_1k]} for customized pricing.
Player_Black (to Proxy):



--------------------------------------------------------------------------------
Proxy (to Player_Black):

Invalid action. Pick one, reply exactly with the name and space delimitted argument: get_current_board, get_legal_moves, make_move <UCI formatted move>

--------------------------------------------------------------------------------
Execution was halted due to error.
Exception details: Error code: 400 - {'error': {'message': 'Invalid argument: 400 Unable to submit request because it has an empty text parameter. Add a value to the parameter and try again. Learn more: https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/gemini', 'type': 'invalid_request_error', 'code': 'invalid_argument'}}
```