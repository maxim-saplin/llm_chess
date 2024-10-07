Putting LLMs up against each other in chess game. Testing basic instruction following capabilities and of course chess proficiency :)

- `llm_chessp.py` runs the game, collects the results, records video
    

## Running
 - Decide if you would like to put one LLM against the other OR a random player (chaos monkey picking randome move out of a list of legal moves provided to it)
    - Set `use_random_player` to True to make make random player play white and LLM play black
 - Set LLM params in .env file (API key, etc.) for both white and black player agents
    - Azure Open AI i used buy default, modify `utils.py` to use a different provider that is supported by [Autogen](https://microsoft.github.io/autogen/docs/topics/llm_configuration/)
 - Check configs (see next)
 - Run `llm_chess.py`
    - llm_chess_tool_call.py is older version relying on native tool call support, not maintained, keeping JIC

## Configs

Adjust the global configs at `llm_chess.py`.

- `use_random_player`: A boolean flag that determines if the Random Player Agent is assigned to play as the white player. If set to `True`, the Random Player will make random legal moves.
- `max_game_moves`: An integer specifying the maximum number of moves allowed in a game before it is automatically terminated. Default is 200.
- Constrains for a single move (LLM dialogs if LLM agent is used)
    - `max_llm_turns`: An integer indicating the maximum number of conversation turns (pairs of user/assistant messages) an LLM can take while deciding and making a move. Default is 10.
    - `max_failed_attempts`: An integer that sets the number of incorrect replies or actions a player agent can make before the game is halted and the player is declared the loser. E.g. if a model returns action name not in the requested format OR asks to make a move that is not possible an internal counter will grow, the model will be asked to self-correct. If the `max_failed_attempts` is reached the game is interrupted, WIN is given to the opposite player. Default value is 3.
- `throttle_delay_moves`: A delay in seconds between moves to prevent throttling by LLM providers due to frequent API requests. Default is 1 second.

These settings are used to configure the game environment and control the flow of the chess match between the agents.


## Kinds of Agents

- LLM Player Agent (instantiated from Autogen's standard ConversiableAgent) is used to evaluate the board and make moves on behalf of one of the players (white or black)
- Random Player Agent (custom RandomPlayerAgent) requests for a list of legal moves, randomly picks one and than makes a moive. Always plays as white
- Proxy Agent (custom AutoReplyAgent) is used to kick-off conversation with player agent, provides a list of available actions (get_current_board, get_legal_moves, make_move)

## Sample Dialog Happenning within a Single Move

Proxy (to Player_Black):

You are a professional chess player and you play as black. Now is your turn to make a move. Before making a move you can pick one of 3 actions:
    - 'get_current_board' to get the schema and current status of the board
    - 'get_legal_moves' to get a UCI formatted list of available moves
    - 'make_move <UCI formatted move>' when you are ready to complete your turn (e.g., 'make_move e2e4')
Respond with the action.


--------------------------------------------------------------------------------
Player_Black (to Proxy):

get_current_board

--------------------------------------------------------------------------------
Proxy (to Player_Black):

⭘ ♜ ♝ ♛ ♚ ♜ ⭘ ⭘
♟ ♟ ♟ ♟ ♟ ♟ ♝ ♟
⭘ ⭘ ♞ ⭘ ⭘ ♞ ⭘ ⭘
⭘ ⭘ ⭘ ⭘ ⭘ ⭘ ⭘ ♕
♙ ♙ ⭘ ⭘ ♙ ⭘ ⭘ ⭘
⭘ ⭘ ⭘ ♙ ♔ ⭘ ⭘ ⭘
⭘ ⭘ ♙ ⭘ ⭘ ♙ ♙ ♙
♖ ♘ ♗ ⭘ ⭘ ♗ ⭘ ♖

--------------------------------------------------------------------------------
Player_Black (to Proxy):

get_legal_moves

--------------------------------------------------------------------------------
Proxy (to Player_Black):

f8h8,f8g8,b8a8,g7h8,g7h6,f6g8,f6h5,f6d5,f6g4,f6e4,c6e5,c6a5,c6d4,c6b4,h7h6,e7e6,d7d6,b7b6,a7a6,e7e5,d7d5,b7b5,a7a5

--------------------------------------------------------------------------------
Player_Black (to Proxy):

make_move f8g8

--------------------------------------------------------------------------------
Proxy (to Player_Black):

Move made, switching player