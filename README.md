# [>>> LEADERBOARD <<<](https://maxim-saplin.github.io/llm_chess/)

Putting LLMs up against ~each other~ Randmon Player in a chess game. Testing basic instruction following capabilities and of course chess proficiency :)

- `llm_chessp.py` runs the game, collects the results, records video

## Rules

- Random players plays as white, LLM as black
- Game constraints:
    - Max 200 moves (100 moves per player)
    - Max 10 turns in LLM dialog when deciding on a move (a turn being a user/assistant pair of messages)
    - Max 3 mistakes in LLM dialog
- Win OR Loss
    - In LLM dialog if max turns is reached OR 3 mistakes are made by LMM, Random Players gets a WIN and LLM gets a LOSS
    - If max moves is reached a DRAW is given
    - Chess engine evaluates the board after each move and can give the corresponding player a WIN in case of a checkmate or stop the game and give a DRAW for the following reasons: Stalemate, Insufficient Material, Seventy-five Moves, or Fivefold Repetition.
 - Exceptions/Execution Errors:
    - If the execution is halted due to a programatic error the game is stopped and DRAW is scored.
    - MANUAL inspection of logs is required:
        - If the error happens to be connectivity or thorrle limmit error by API the game to be discarded
        - If the error is model error (e.g. ""The model produced invalid content. Consider modifying your prompt if you are seeing this error persistently." by OpenAI or 400 or 500 errors by Local Models) the draw to be changed to a LOSS to LLM

## Running the Games

 - Decide if you would like to put one LLM against the other OR a random player (chaos monkey picking random move out of a list of legal moves provided to it)
    - Set `use_random_player` to True to make random player play white and LLM play black
 - Set LLM params in the .env file (API key, etc.) for both white and black player agents
    - Azure Open AI used by default, modify `utils.py` to use a different provider that is supported by [Autogen 0.2](https://microsoft.github.io/autogen/docs/topics/llm_configuration/)
 - Check configs (see next)
 - `pip install -r requirements.txt`
    - Optionally create a VENV
 - Run `llm_chess.py`
    - llm_chess_tool_call.py is an older version relying on native tool call support, not maintained, keeping JIC

### Configs

Adjust the global configs at `llm_chess.py`.

- `white_player_type`: Determines the type of player controlling the white pieces. Options include `RANDOM_PLAYER`, `LLM_WHITE`, `LLM_BLACK`, `CHESS_ENGINE_SUNFISH`, and `CHESS_ENGINE_STOCKFISH`.
- `black_player_type`: Determines the type of player controlling the black pieces. Options include `RANDOM_PLAYER`, `LLM_WHITE`, `LLM_BLACK`, `CHESS_ENGINE_SUNFISH`, and `CHESS_ENGINE_STOCKFISH`.
- `enable_reflection`:  whether to offer the LLM time to think and evaluate moves by giving an extra "reflect" action
- `use_fen_board`: A boolean indicating whether to use the FEN format for board representation. The default is `False`.
- `max_game_moves`: An integer specifying the maximum number of moves allowed in a game before it is automatically terminated. The default is 200.
- Constraints for a single move (LLM dialogs if LLM agent is used)
    - `max_llm_turns`: An integer indicating the maximum number of conversation turns (pairs of user/assistant messages) an LLM can take while deciding and making a move. The default is 10.
    - `max_failed_attempts`: An integer that sets the number of incorrect replies or actions a player agent can make before the game is halted and the player is declared the loser. E.g. if a model returns an action name not in the requested format OR asks to make a move that is not possible an internal counter will grow, and the model will be asked to self-correct. If the `max_failed_attempts` is reached the game is interrupted, and WIN is given to the opposite player. The default value is 3.
- `throttle_delay_moves`: A delay in seconds between moves to prevent throttling by LLM providers due to frequent API requests. The default is 1 second.

These settings configure the game environment and control the flow of the chess match between the agents.

### Multiple Games

The `run_multiple_games.py` script allows you to execute multiple chess games between different agents and aggregate the results.

To run multiple games:
- Adjust the `NUM_REPETITIONS` variable to set the number of games you want to simulate.
- The results, including win/loss statistics and material counts, are aggregated and can be analyzed to understand the strengths and weaknesses of each player type.
- Aggregate logs and logs for individual games (if `STORE_INDIVIDUAL_LOGS` is set to True) can be stored in the specified `LOG_FOLDER` for further inspection.

This feature is used to compare different kinds of players and generalize the findings. For LLM playes 10 games were used, for random/chess engine players 1000 games, some states is provided below.

#### Aggregate Result

When running multiple games individual logs are collected in `{date_time}.json` files (e.g. 2024.10.11_17:34.json) which are collected in a directory. After the games are finished aggregate results are collected in `aggregate_results.csv`.

Notes:
- "wrong_moves" and "wrong_actions" is the total number of erroneous replies by the player (e.g. not following convention) made in "inner" dialogs between the proxy and player. To get the total number of erroneous replies add up the metrics (i.e. `wrong_moves` do not include `wrong_actions`)
  - A single game is finished if any of the players make more than `max_failed_attempts` in the inner dialogs (i.e. `wrong_moves` + `wrong_actions` < `max_failed_attempts` - see above config)

## Processing Logs & Prepping for Web

`_logs/aggregate_models_to_csv.py` can process individual games logs within a given folder and produce a CSV grouping logs by model name and aggregating stats. 

Change the default params to point the script to the correct folder and output CSV file:

```python
def aggregate_models_to_csv(
    logs_dir="_logs/no_reflection",
    output_csv="_logs/no_reflection/aggregate_models.csv",
):
```

### Web

Run `_docs/data/aggr_to_refined.py` to prdouce `refined.csv` (from `aggregate_models.csv`) ready for `index.html` emdedding. Manually copy the needed rows to `index.html` const in JS - the data will be used in the Web Leaderboard.

Why copy manually? Cause you are likely updating a leaderboard and some of the models in the Web migth have different names, not the ones used in the logs.

## Kinds of Agents

- LLM Player Agent (instantiated from Autogen's standard ConversiableAgent) is used to evaluate the board and make moves on behalf of one of the players (white or black)
- Random Player Agent (custom RandomPlayerAgent) requests for a list of legal moves, randomly picks one, and then makes a move. Always plays as white
- Proxy Agent (custom AutoReplyAgent) is used to kick off conversation with a player agent and provides a list of available actions (get_current_board, get_legal_moves, make_move)
- Chess Engine Players:
  - Sunfish: A simple Python engine.
  - Stockfish: A powerful engine requiring separate installation.

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
## Logs

Game run results are stored under the `_logs` folder.

## Changes Affecting Evals

- Logs before 08.10.2024 (first 8) are more strict with wrong moves stats
- Logs before 16.10.2024 had ambiguous "Unknown issue, Player_Black failed to make a move" reason which often meant that a single dialog took more than 10 turns (20 total messages) and execution was halted, changed to include a more specific reason "Max turns in single dialog"
- Different configs could be used, directory folder
- Log `_15.10.2024_gpt-4o-anthropic.claude-v3-5-sonnet_reflectio` had timeout error, aggregate only had 9 out of 10 consistent runs
- After 19.10.2024 setting default hyperparams ("temperature": 0.7, "top_p": 1.0, "frequency_penalty": 0.0, "presence_penalty": 0.0,)
- 19.10.2024, Gemini-1.5-flash-001 consistently failed to follow the instructions:
- 22.10.2024, slightly updated common prompt removing excessive tabs
- 05.11.2024, fixed bug with wrong action counting (not global per game but per move), set temperature to 0.7, re-ran no_reflection
- 14.01.2025, changed logs aand switched DRAWS for LLM losses due to model error to Gemini-1.5-pro-preview-0409 (8 logs from November, no reflection), qwq-32b-preview@q4_k_m (1 log from January 9, no reflection), sky-t1-32b-preview@q4_0 (1 log from January 14, no reflection), o1-mini-2024-09-12 (1 lof fro December 22, no reflection), gpt-4-turbo-2024-04-09 (4 logs from November, reflection)

## Model vs Random Player

I have conducted a number of games putting LLM (playing with black) against a Random Player (as white), typically 10 games with a cap of 200 moves.


## Model Zoo

### Problems with the instruction following

!NOTE, not touching prompts, changing parsing logic to be more relaxed, logs before 08.10.2024 (first 8) are more strict with wrong moves stats

Original kick-off prompt:
```
You are a professional chess player and you play as black. Now is your turn to make a move. Before making a move you can pick one of 3 actions:
    - 'get_current_board' to get the schema and current status of the board
    - 'get_legal_moves' to get a UCI formatted list of available moves
    - 'make_move <UCI formatted move>' when you are ready to complete your turn (e.g., 'make_move e2e4')
Respond with the action.
```
And the failure message:
```
Invalid action. Pick one, reply exactly with the name and space delimited argument: "get_current_board, get_legal_moves, make_move <UCI formatted move>
```

- GPT-4o, GPT-4o mini, gemini-1.5-pro-preview-0409 worked fine with the original prompts and exact match logic for make_move
- Claude 3.5 Sonnet failed to reply with a simple string always adding verbosity
```
Proxy (to Player_Black):

Invalid action. Pick one, reply exactly with the name and space delimited argument: get_current_board, get_legal_moves, make_move <UCI formatted move>

--------------------------------------------------------------------------------
Player_Black (to Proxy):

I apologize for the continued confusion. Let me provide the correct format for the move I want to make:

make_move c7c5
```

- Gemini-1.5-flash-001 always wrapped answers in JSON code blocks (while not asked)
- lama-3.1-nemotron-70b-instruct-hf 4 bit was too verbose failing to make any actions (2024.10.22_23:18_lama-3.1-nemotron-70b-instruct-hf.md)
- gpt-35-turbo-0125 failed to make any moves by not complying with the instructions and reply format (see _23.10.2024_gpt-35-turbo-0125/fail.md)

#### Example of a Model (gemini-1.5-pro-preview-0409) Failing to Pick a Valid Move

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

♜ ♞ ♝ ♛ ♚ ♝ ⭘ ⭘
⭘ ♟ ♟ ♟ ♟ ⭘ ⭘ ♜
♟ ⭘ ⭘ ⭘ ⭘ ♟ ♟ ♟
♙ ⭘ ⭘ ⭘ ⭘ ⭘ ⭘ ♞
⭘ ⭘ ⭘ ♙ ⭘ ♙ ⭘ ⭘
⭘ ♙ ♘ ⭘ ⭘ ♘ ⭘ ⭘
♖ ⭘ ♙ ⭘ ♙ ⭘ ♙ ♙
⭘ ⭘ ♗ ♕ ♔ ♗ ⭘ ♖

--------------------------------------------------------------------------------
Player_Black (to Proxy):

get_legal_moves 


--------------------------------------------------------------------------------
Proxy (to Player_Black):

f8g7,e8f7,b8c6,a8a7,h7h8,h7g7,h7f7,h5g7,h5f4,h5g3,e7e6,d7d6,c7c6,b7b6,g6g5,f6f5,e7e5,d7d5,c7c5,b7b5

--------------------------------------------------------------------------------
Player_Black (to Proxy):

make_move h7h6 


--------------------------------------------------------------------------------
Proxy (to Player_Black):

Failed to make move: illegal uci: 'h7h6' in rnbqkb2/1pppp2r/p4ppp/P6n/3P1P2/1PN2N2/R1P1P1PP/2BQKB1R b Kq - 2 8
```

## Random and Chess Engine Players

- Random players request all legal moves and randomly pick one thus always making valid moves
- Chess engines 
 - Simple no dependency Pyhton engine Sunfish (https://github.com/thomasahle/sunfish)
 - Powerful Stockfish
    - Requires separate installation and properly defining path with python-chess
        - On macOS, I installed it via `brew install stockfish`
        - Path to Stockfish is identified via `where stockfish` yielding `/opt/homebrew/bin/stockfish`
        - Set the path in `llm_chess.py`.

Below are some stats simulating many games (1000) and collecting stats to get an idea of a baseline for LLM players playing against a random player

### Random Player (white) vs Chess Engine (black, Stockfish, time per move 0.01s)

```json
{
    "total_games": 1000,
    "white_wins": 0,
    "black_wins": 1000,
    "draws": 0,
    "total_moves": 32368,
    "reasons": {
        "Checkmate": 1000
    },
    "player_white": {
        "name": "Random_Player",
        "model": "",
        "total_material": 21006,
        "wrong_moves": 0,
        "wrong_actions": 0,
        "avg_material": 21.006,
        "std_dev_material": 9.191324411881263
    },
    "player_black": {
        "name": "Chess_Engine_Stockfish_Black",
        "model": "",
        "total_material": 38214,
        "wrong_moves": 0,
        "wrong_actions": 0,
        "avg_material": 38.214,
        "std_dev_material": 3.77391659240721
    },
    "average_moves": 32.368,
    "std_dev_moves": 13.554050622905622
}
```

### Random Player (white) vs Chess Engine (black, Sunfish)

Simulating 1000 games of a chess engine shows that with a chess engine, it takes around 100 moves to complete the game, The chess engine dominates judging by the amount of material (weighted sum of pieces standing on the board)
```json
{
    "total_games": 1000,
    "white_wins": 0,
    "black_wins": 190,
    "draws": 810,
    "total_moves": 99252,
    "reasons": {
        "Checkmate": 190,
        "Stalemate": 406,
        "Max moves reached": 34,
        "Fivefold repetition": 370
    },
    "player_white": {
        "name": "Random_Player",
        "model": "",
        "total_material": 1183,
        "wrong_moves": 0,
        "wrong_actions": 0,
        "avg_material": 1.183,
        "std_dev_material": 4.750587235182518
    },
    "player_black": {
        "name": "Chess_Engine_Player_Black",
        "model": "",
        "total_material": 39549,
        "wrong_moves": 0,
        "wrong_actions": 0,
        "avg_material": 39.549,
        "std_dev_material": 9.469597260299524
    },
    "average_moves": 99.252,
    "std_dev_moves": 51.129705091490045
}
```

### Random vs Random

```json
{
    "total_games": 1000,
    "white_wins": 105,
    "black_wins": 0,
    "draws": 895,
    "total_moves": 190073,
    "reasons": {
        "Max moves reached": 886,
        "Checkmate": 105,
        "Stalemate": 9
    },
    "player_white": {
        "name": "Random_Player",
        "model": "",
        "total_material": 10555,
        "wrong_moves": 0,
        "wrong_actions": 0,
        "avg_material": 10.555,
        "std_dev_material": 7.228224001940049
    },
    "player_black": {
        "name": "Random_Player",
        "model": "",
        "total_material": 11076,
        "wrong_moves": 0,
        "wrong_actions": 0,
        "avg_material": 11.076,
        "std_dev_material": 7.491217680880882
    },
    "average_moves": 190.073,
    "std_dev_moves": 32.05006829755403
}
```

## Reflection

If enabled (`enable_reflection = True`) an extract action is added to the list of available options offerrin an LLM to reflect on best move generating more tokens and thinking through the best next move.

Sample dialog:
```
Proxy (to Player_Black):

You are a professional chess player and you play as black. Now is your turn to make a move. Before making a move you can pick one of 3 actions:
        - 'get_current_board' to get the schema and current status of the board
        - 'get_legal_moves' to get a UCI formatted list of available moves
        - 'do_reflection' to take a moment to think about your strategy
        - 'make_move <UCI formatted move>' when you are ready to complete your turn (e.g., 'make_move e2e4')
    

--------------------------------------------------------------------------------
Player_Black (to Proxy):

I'll start by checking the current state of the board.

Action: `get_current_board`

--------------------------------------------------------------------------------
Proxy (to Player_Black):

♜ ♞ ♝ ♛ ♚ ♝ ♞ ♜
♟ ♟ ♟ ⭘ ⭘ ♟ ♟ ♟
⭘ ⭘ ⭘ ⭘ ⭘ ⭘ ⭘ ⭘
⭘ ⭘ ⭘ ♟ ♟ ⭘ ⭘ ⭘
⭘ ⭘ ⭘ ⭘ ⭘ ⭘ ⭘ ⭘
♙ ⭘ ⭘ ♙ ♙ ⭘ ⭘ ⭘
⭘ ♙ ♙ ⭘ ⭘ ♙ ♙ ♙
♖ ♘ ♗ ♕ ♔ ♗ ♘ ♖

--------------------------------------------------------------------------------
Player_Black (to Proxy):

Let's analyze the board further by checking possible moves.

Action: `get_legal_moves`

--------------------------------------------------------------------------------
Proxy (to Player_Black):

g8e7,g8h6,g8f6,f8e7,f8d6,f8c5,f8b4,f8a3,e8e7,e8d7,d8e7,d8d7,d8f6,d8d6,d8g5,d8h4,c8d7,c8e6,c8f5,c8g4,c8h3,b8d7,b8c6,b8a6,h7h6,g7g6,f7f6,c7c6,b7b6,a7a6,e5e4,d5d4,h7h5,g7g5,f7f5,c7c5,b7b5,a7a5

--------------------------------------------------------------------------------
Player_Black (to Proxy):

I'll think about the best strategy given these options.

Action: `do_reflection`

--------------------------------------------------------------------------------
Proxy (to Player_Black):

Before deciding on the next move you can reflect on your current situation, write down notes, and evaluate.
    Here are a few recommendations that you can follow to make a better move decision:
    - Shortlist the most valuable next moves
    - Consider how they affect the situation
    - What could be the next moves from your opponent in each case
    - Is there any strategy fitting the situation and your choice of moves
    - Rerank the shortlisted moves based on the previous steps
    

--------------------------------------------------------------------------------
Player_Black (to Proxy):

**Reflection:**

1. **Shortlist Valuable Moves:**
   - **g8f6**: Develops the knight, controls the center, and targets e4.
   - **h7h6**: Prepares to fianchetto the bishop or prevents a knight pin on g5.
   - **c7c5**: Challenges the center and prepares to expand on the queenside.

2. **Immediate Effects:**
   - **g8f6**: Develops a piece, and brings the knight nearer to the center.
   - **h7h6**: Solidifies kingside but is more of a precautionary move.
   - **c7c5**: Direct action against the center, preparing for future breaks.

3. **Opponent's Responses:**
   - **g8f6**: White might continue developing with Nc3 or push e4.
   - **h7h6**: White might ignore it and proceed with normal development.
   - **c7c5**: White could opt for dxc5 or develop with Nc3.

4. **Strategy Considerations:**
   - Aim to control the center and set up a solid defensive position.
   - Balance between development and maintaining structural integrity.

5. **Rerank Shortlisted Moves:**
   - **1. g8f6**: Best for development and central control.
   - **2. c7c5**: Strong challenge to the center.
   - **3. h7h6**: Defensive but adds limited value immediately.

With that in mind, I’ll proceed with the development strategy.

Action: `make_move g8f6`

--------------------------------------------------------------------------------
Proxy (to Player_Black):

Move made, switching player
```

## Can LLMs discern Unicode-encoded pieces? Yes, they can

Prompt:
```
Please name chess pieces and their colors.

♕ ♔ ♗ ♘ ♖ ♙
♛ ♚ ♝ ♞ ♜ ♟
```

### Claude 3.5 Sonnet - YES

```
Here are the chess pieces and their colors:
White pieces: ♕ Queen ♔ King ♗ Bishop ♘ Knight ♖ Rook ♙ Pawn
Black pieces: ♛ Queen ♚ King ♝ Bishop ♞ Knight ♜ Rook ♟ Pawn
In a standard chess set, one player uses the white pieces, and the other player uses the black pieces. Each side starts with 16 pieces: 1 king, 1 queen, 2 rooks, 2 knights, 2 bishops, and 8 pawns.
```

### Gemini 1.5 Flash - YES

```
Here are the chess pieces and their colors:

**White Pieces:**

* ♕ Queen
* ♔ King
* ♗ Bishop
* ♘ Knight
* ♖ Rook
* ♙ Pawn

**Black Pieces:**

* ♛ Queen
* ♚ King
* ♝ Bishop
* ♞ Knight
* ♜ Rook
* ♟ Pawn 

```

### Gemini 1.5 Pro - YES

```
White Pieces

♕: White Queen
♔: White King
♗: White Bishop
♘: White Knight
♖: White Rook
♙: White Pawn
Black Pieces

♛: Black Queen
♚: Black King
♝: Black Bishop
♞: Black Knight
♜: Black Rook
♟: Black Pawn
```

### GPT-4o mini 2024-07-18 - YES

```
In chess, the pieces are typically divided into two colors: white and black. Here’s a breakdown of the pieces and their corresponding colors:

White Pieces:

♕ - White Queen
♔ - White King
♗ - White Bishop
♘ - White Knight
♖ - White Rook
♙ - White Pawn
Black Pieces:

♛ - Black Queen
♚ - Black King
♝ - Black Bishop
♞ - Black Knight
♜ - Black Rook
♟ - Black Pawn
Each player controls one color and aims to checkmate the opponent's king.
```
