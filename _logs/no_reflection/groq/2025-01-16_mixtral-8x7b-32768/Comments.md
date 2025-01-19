Mixtral failed to respond with propper names of action ading slashes, e.g. using `get\_current\_board` instead of requested `get_current_board`

```
Proxy (to Player_Black):

You are a professional chess player and you play as black. Now is your turn to make a move. Before making a move you can pick one of the following actions:
- 'get_current_board' to get the schema and current status of the board
- 'get_legal_moves' to get a UCI formatted list of available moves
- 'make_move <UCI formatted move>' when you are ready to complete your turn (e.g., 'make_move e2e4')

--------------------------------------------------------------------------------
[_ag.oai.client: 01-16 21:26:07] {349} WARNING - Model mixtral-8x7b-32768 is not found. The cost will be 0. In your config_list, add field {"price" : [prompt_price_per_1k, completion_token_price_per_1k]} for customized pricing.
Player_Black (to Proxy):

get\_current\_board

--------------------------------------------------------------------------------
Proxy (to Player_Black):

Invalid action. Pick one, reply exactly with the name and space delimitted argument: get_current_board, get_legal_moves, make_move <UCI formatted move>

--------------------------------------------------------------------------------
[_ag.oai.client: 01-16 21:26:13] {349} WARNING - Model mixtral-8x7b-32768 is not found. The cost will be 0. In your config_list, add field {"price" : [prompt_price_per_1k, completion_token_price_per_1k]} for customized pricing.
Player_Black (to Proxy):

get\_current\_board

--------------------------------------------------------------------------------
Proxy (to Player_Black):

Invalid action. Pick one, reply exactly with the name and space delimitted argument: get_current_board, get_legal_moves, make_move <UCI formatted move>

--------------------------------------------------------------------------------
[_ag.oai.client: 01-16 21:26:18] {349} WARNING - Model mixtral-8x7b-32768 is not found. The cost will be 0. In your config_list, add field {"price" : [prompt_price_per_1k, completion_token_price_per_1k]} for customized pricing.
Player_Black (to Proxy):

I apologize for the mistake. Here is the correct response:

get\_current\_board

--------------------------------------------------------------------------------
BREAKING >>> Invalid action. Pick one, reply exactly with the name and space delimitted argument: get_current_board, get_legal_moves, make_move <UCI formatted move>
Proxy (to Player_Black):

Too many wrong actions
```