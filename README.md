## Running the Tests

- Clone the repo
- Create and source venv, e.g. `uv venv .venv && source .venv/bin/activate`
- Install dependenciesm, e.g. `uv pip install -r requirements.txt`
- Check `.env.sample` for sample LLM config and create your own version in `.env`
  - `_W` postfix in LLM config is used for LLM agent playing as white, `_B` for black LLM player
- Execute `run_multiple_games.py` with default params, get game logs at `_logs`
  - By default Random (as White) plays vs LLM (as black, hence using `MODEL_KIND_B` from `.env`)
  - 42 games

## Default Rules

- Random players plays as white, LLM as black
- Game constraints:
    - Max 200 moves (100 moves per player)
    - Max 10 turns in LLM dialog when deciding on a move (a turn being a user/assistant pair of messages)
    - Max 3 mistakes in LLM dialog (i.e. 3rd mistakes in the dialog breaks game loop and assignes a LOSS to LLM)
- Win OR Loss
    - In LLM dialog if max turns is reached OR 3 mistakes are made by LMM, Random Players gets a WIN and LLM gets a LOSS
    - If max moves is reached a DRAW is given
    - Chess engine evaluates the board after each move and can give the corresponding player a WIN in case of a checkmate or stop the game and give a DRAW for the following reasons: Stalemate, Insufficient Material, Seventy-five Moves, or Fivefold Repetition.
 - Exceptions/Execution Errors:
    - If the execution is halted due to a programatic error the game is stopped and DRAW is scored.
    - MANUAL inspection of logs is required:
        - If the error happens to be connectivity or thorrle limmit error by API the game to be discarded
        - If the error is model error (e.g. ""The model produced invalid content. Consider modifying your prompt if you are seeing this error persistently." by OpenAI or 400 or 500 errors by Local Models) the draw to be changed to a LOSS to LLM


## Configs

In `run_multiple_games.py`:
- Set `LOG_FOLDER`
- Adjust the `NUM_REPETITIONS` variable to set the number of games you want to simulate.
- Set `STORE_INDIVIDUAL_LOGS` to false if you want just the aggregate results JSON for the game run

Indidual game configs at `llm_chess.py` (can be set in `run_multiple_games.py`)

- `white_player_type`: Determines the type of player controlling the white pieces. Options include `RANDOM_PLAYER`, `LLM_WHITE`, `LLM_BLACK`, `CHESS_ENGINE_DRAGON`, and `CHESS_ENGINE_STOCKFISH`.
- `black_player_type`: Determines the type of player controlling the black pieces. Options include `RANDOM_PLAYER`, `LLM_WHITE`, `LLM_BLACK`, `CHESS_ENGINE_DRAGON`, and `CHESS_ENGINE_STOCKFISH`.
- `enable_reflection`:  whether to offer the LLM time to think and evaluate moves by giving an extra "reflect" action
- `use_fen_board`: A boolean indicating whether to use the FEN format for board representation. The default is `False`.
- `max_game_moves`: An integer specifying the maximum number of moves allowed in a game before it is automatically terminated. The default is 200.
- Constraints for a single move (LLM dialogs if LLM agent is used)
    - `max_llm_turns`: An integer indicating the maximum number of conversation turns (pairs of user/assistant messages) an LLM can take while deciding and making a move. The default is 10.
    - `max_failed_attempts`: An integer that sets the number of incorrect replies or actions a player agent can make before the game is halted and the player is declared the loser. E.g. if a model returns an action name not in the requested format OR asks to make a move that is not possible an internal counter will grow, and the model will be asked to self-correct. If the `max_failed_attempts` is reached the game is interrupted, and WIN is given to the opposite player. The default value is 3.
- `throttle_delay_moves`: A delay in seconds between moves to prevent throttling by LLM providers due to frequent API requests. The default is 1 second.

These settings configure the game environment and control the flow of the chess match between the agents.

## Multiple Games Summary Results

When running multiple games individual logs are collected in `{date_time}.json` files (e.g. 2024.10.11_17:34.json) which are collected in a directory. After the games are finished summary results are collected in `aggregate_results.csv`.

Notes:
- "wrong_moves" and "wrong_actions" is the total number of erroneous replies by the player (e.g. not following convention) made in "inner" dialogs between the proxy and player. To get the total number of erroneous replies add up the metrics (i.e. `wrong_moves` do not include `wrong_actions`)
  - A single game is finished if any of the players make more than `max_failed_attempts` in the inner dialogs (i.e. `wrong_moves` + `wrong_actions` < `max_failed_attempts` - see above config)

## Processing Logs

- `data_processing/get_refined_csv.py` can process individual games logs within a given folder and produce a CSV grouping logs by model name and aggregating stats.

## Kinds of Agents

- LLM Player Agent (instantiated from Autogen's standard ConversiableAgent) is used to evaluate the board and make moves on behalf of one of the players (white or black)
- Random Player Agent (custom RandomPlayerAgent) requests for a list of legal moves, randomly picks one, and then makes a move. Always plays as white
- Proxy Agent (custom AutoReplyAgent) is used to kick off conversation with a player agent and provides a list of available actions (get_current_board, get_legal_moves, make_move)
- Chess Engine Players:
  - Komodo Dragon: chess.com Elo rated (Skill 1 - Elo 250, Skill 2 - Elo 400 etc.)
    - Binaries downloaded from https://komodochess.com are supplied in the `dragon/` folder
    - Make sure you set the right path in `llm_chess.dragon_path`
  - Stockfish: A powerful engine requiring separate installation.
    - You need to install Stockfish (e.g. `brew install stockfish`)
    - Make sure correct path is set in `llm_chess.stockfish_path` (the default one assumes Brew installation on macOS - "/opt/homebrew/bin/stockfish") 


## Sample Dialog Happening within a Single Move

GPT-4o-Mini

```
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
```