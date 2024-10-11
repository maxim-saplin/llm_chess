Putting LLMs up against each other in chess game. Testing basic instruction following capabilities and of course chess proficiency :)

- `llm_chessp.py` runs the game, collects the results, records video
    

## Running

 - Decide if you would like to put one LLM against the other OR a random player (chaos monkey picking randome move out of a list of legal moves provided to it)
    - Set `use_random_player` to True to make make random player play white and LLM play black
 - Set LLM params in .env file (API key, etc.) for both white and black player agents
    - Azure Open AI i used buy default, modify `utils.py` to use a different provider that is supported by [Autogen](https://microsoft.github.io/autogen/docs/topics/llm_configuration/)
 - Check configs (see next)
 - `pip install -r requirements.txt`
    - Optionally create a VENV
 - Run `llm_chess.py`
    - llm_chess_tool_call.py is older version relying on native tool call support, not maintained, keeping JIC

### Multiple Games and Aggregation of Results

The `run_multiple_games.py` script allows you to execute multiple chess games between different agents and aggregate the results.

To run multiple games:
- Adjust the `NUM_REPETITIONS` variable to set the number of games you want to simulate.
- The results, including win/loss statistics and material counts, are aggregated and can be analyzed to understand the strengths and weaknesses of each player type.
- Aggregate log and logs for individual games (if `STORE_INDIVIDUAL_LOGS` is set to True) can be stored in the specified `LOG_FOLDER` for further inspection.

This feature is used to compare different kinds of players and generalize the findings. For LLM playes 10 games were used, for random/chess engine players 1000 games, some states is provided below.


## Configs

Adjust the global configs at `llm_chess.py`.

- `white_player_type`: Determines the type of player controlling the white pieces. Options include `RANDOM_PLAYER`, `LLM_WHITE`, `LLM_BLACK`, `CHESS_ENGINE_SUNFISH`, and `CHESS_ENGINE_STOCKFISH`.
- `black_player_type`: Determines the type of player controlling the black pieces. Options include `RANDOM_PLAYER`, `LLM_WHITE`, `LLM_BLACK`, `CHESS_ENGINE_SUNFISH`, and `CHESS_ENGINE_STOCKFISH`.
- `use_fen_board`: A boolean indicating whether to use the FEN format for board representation. Default is `True`.
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
- Chess Engine Players:
  - Sunfish: A simple Python engine.
  - Stockfish: A powerful engine requiring separate installation.

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

## Model Zoo

### Model vs Random Player

I have conducted a number of games putting LLM (playing with black) against a Random Player (as white), typically 10 games with a cap of 200 moves.

### Problems with instructuin following

!NOTE, not touching prompts, changin parsing logic to be more relaxed, logs before 08.10.2024 (first 8) are more strict with wrong moves stats

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
Invalid action. Pick one, reply exactly with the name and space delimetted argument: "get_current_board, get_legal_moves, make_move <UCI formatted move>
```

- GPT-4o, GPT-4o mini, gemini-1.5-pro-preview-0409 worked fine with the ogirinal prompts and exact match logic for make_move
- Claude 3.5 Sonnet failed to reply with simple string always adding verbosity
```
Proxy (to Player_Black):

Invalid action. Pick one, reply exactly with the name and space delimetted argument: get_current_board, get_legal_moves, make_move <UCI formatted move>

--------------------------------------------------------------------------------
Player_Black (to Proxy):

I apologize for the continued confusion. Let me provide the correct format for the move I want to make:

make_move c7c5
```

- Gemini-1.5-flash-001 alaways wrapped answers in JSON code blocks (while not asked)

## Random and Chess Engine Players

- Random players requests for all legal moves and randomly picks one thus always making valid moves
- Chess engines 
 - Simple no dependency Pyhton engine Sunfish (https://github.com/thomasahle/sunfish)
 - Powerful Stockfish
    - Requires separate installation and properly defining path with python-chess
        - On macOS I installed it via `brew install stockfish`
        - Path to Stockfish is identified via `where stockfish` yielding `/opt/homebrew/bin/stockfish`
        - Set the path in `llm_chess.py`.

Below is some stats simulating many games (1000) and collecting stats to get an idea of a baseline for LLM players palying against random player

### Random Player (white) vs Cheess Engine (black, Stockfish, time per move 0.01s)

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

### Random Player (white) vs Cheess Engine (black, Sunfish)

Simulating 1000 games of a chess engine against show that with chess engine it takes around 100 moves to complete the game, chess engine dominates judging by ammount of material (weighted sum of piaces standing at the board)
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

## Can LLM discernt Unicode encoded pieces?

Prompt:
```
Please name chess pieces and their colors

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
