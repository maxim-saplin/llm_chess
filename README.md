# LLM Chess: Benchmarking Reasoning and Instruction-Following in LLMs

[![Leaderboard](https://img.shields.io/badge/Live%20Leaderboard-%20🏆-blueviolet)](https://maxim-saplin.github.io/llm_chess/)
[![Paper](https://img.shields.io/badge/Paper-NeurIPS%20FoRLM%202025-green)](https://arxiv.org/abs/2512.01992)

LLM Chess is a benchmark that evaluates Large Language Models (LLMs) on their reasoning and instruction-following abilities in an agentic setting. LLMs engage in multi-turn dialogs to play chess against opponents like a Random Player or the Komodo Dragon chess engine. This setup tests both strategic reasoning (chess skill) and protocol adherence (sustained interaction without errors).

Key insights from the benchmark:
- Early models (2024) struggled with basic instruction following, often hallucinating illegal moves or failing dialogs.
- Advanced reasoning models (e.g., o1, o3, o4-mini) in 2025 saturated random-based evaluations, prompting the addition of Dragon as a stronger opponent for Elo anchoring.
- Metrics separate chess skill (Win/Loss, Elo) from durability (Game Duration), revealing trade-offs in model capabilities.

See the [live leaderboard](https://maxim-saplin.github.io/llm_chess/) for rankings and the [NeurIPS FoRLM 2025 paper](docs/LLM%20CHESS%2C%20Benchmarking%20Reasoning%20and%20Instruction-Following%20in%20LLMs%20through%20Chess%20-%20NeurIPS%20FoRLM%202025.pdf) for full details.

<img width="2118" height="1582" alt="image" src="https://github.com/user-attachments/assets/4375a8a8-e226-4ed1-820f-86006d0404e2" />

## Installation and Setup

1. **Clone the repository**:
   ```
   git clone https://github.com/maxim-saplin/llm_chess.git
   cd llm_chess
   ```

2. **Create a virtual environment** (recommended):
   ```
   # Using uv (fast alternative to pip)
   uv venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate

   # Or using pip/venv
   python -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```
   uv pip install -r requirements.txt  # Or pip install -r requirements.txt
   ```

4. **Configure LLMs**:
   - Copy `.env.sample` to `.env` and add your API keys.
   - Suffixes like `_W` (white) and `_B` (black) distinguish configs for multi-LLM setups.
   - Supports Azure OpenAI, OpenAI, Anthropic, Google, Groq, and local models via Autogen.
   - For local models, ensure Ollama or LM Studio is running.

5. **Chess Engines** (optional, for stronger opponents):
   - **Komodo Dragon**: Download binaries from [komodochess.com](https://komodochess.com/installation.htm) and place in `dragon/`. Set `llm_chess.dragon_path`.
   - **Stockfish**: Install via `brew install stockfish` (macOS) or equivalent. Set `llm_chess.stockfish_path` (default: `/opt/homebrew/bin/stockfish`).

## Running Games

### Single Game
Run a single chess simulation:
```
python llm_chess.py
```
- Default: Random Player (white) vs. LLM (black).
- Logs saved to `_logs/` with JSON details and optional video recordings.

### Multiple Games
For benchmarking, run multiple simulations:
```
python run_multiple_games.py
```
- Default: 42 games.
- Customize in the script:
  - `NUM_REPETITIONS`: Number of games (e.g., 30+ for reliable stats).
  - `LOG_FOLDER`: Output directory (e.g., `_logs/random_vs_llm/`).
  - `STORE_INDIVIDUAL_LOGS`: Set to `False` for aggregate JSON only.
- Aggregates results in `aggregate_results.json` and individual logs in `{timestamp}.json`.

## Game Rules

- **Players**: Random (white) vs. LLM (black) by default. Supports LLM vs. LLM, engine vs. LLM.
- **Constraints**:
  - Max 200 moves (100 per player).
  - Max 10 turns per LLM move (user/assistant pairs).
  - Max 3 mistakes per dialog (illegal moves/actions); exceeds → LLM loss.
- **Outcomes**:
  - **Win/Loss**: Checkmate or opponent errors/timeouts.
  - **Draw**: Max moves reached, stalemate, insufficient material, repetition, or 75-move rule.
  - **Errors**: Programmatic issues → Draw (manual review for API throttles/model failures → discard or LLM loss).
- Games use UCI notation for moves and Unicode boards for visualization.

## Configurations

Edit globals in `llm_chess.py` or pass via `run_multiple_games.py`:

- `white_player_type` / `black_player_type`: `RANDOM_PLAYER`, `LLM`, `CHESS_ENGINE_DRAGON`, `CHESS_ENGINE_STOCKFISH`.
- `enable_reflection`: Enable "reflect" action for strategic thinking (extra tokens).
- `use_fen_board`: Use FEN notation instead of Unicode board (default: False).
- `max_game_moves`: Max moves (default: 200).
- Per-move LLM limits:
  - `max_llm_turns`: Max dialog turns (default: 10).
  - `max_failed_attempts`: Max errors before loss (default: 3).
- `throttle_delay_moves`: API delay (default: 1s) to avoid rate limits.

## Agents

- **LLM Agent**: Autogen `ConversableAgent` for dialog-based moves. Prompts guide actions: `get_current_board`, `get_legal_moves`, `make_move <UCI>`.
- **Random Agent**: Custom; requests legal moves, picks randomly. Always white.
- **Proxy Agent**: Custom `AutoReplyAgent`; orchestrates dialogs, provides board/moves.
- **Chess Engines**:
  - **Dragon**: Elo-rated. Binaries in `dragon/`.
    - Level 1: 250 Elo
    - Level 2: 375 Elo
    - Level 3: 500 Elo
    - Level 4: 625 Elo
    - Level 5: 750 Elo
    - Level 6: 875 Elo
    - Level 7: 1000 Elo
    - Formula: Elo = 125 × (level + 1)
  - **Stockfish**: Strong engine; install separately.

## Processing Logs

Logs in `_logs/` contain JSON per game. Aggregate and refine:

   ```
   python data_processing/get_refined_elo.py
   ```
   - Handles multiple directories (Random vs. LLM, Dragon vs. LLM).
   - Computes Elo (anchored to Dragon levels: Elo ≈ 125 × (level + 1)), Win/Loss %, Game Duration %.
   - Filters low-sample models; supports overrides/aliases.
   - Output: CSV with player stats, usage (tokens/cost), interruptions.



Manual review: Check logs for API errors (discard) vs. model failures (LLM loss).

## Metrics

From refined CSV/leaderboard:

- **Elo**: Estimated rating (±95% CI), anchored to Dragon/chess.com. Combines Random/Dragon data.
- **Win/Loss**: (Wins - Losses) / Total % (0-100%). Blends skill + instruction following. 50% = balanced.
- **Game Duration**: % of max moves completed (0-100%). Measures dialog stability (100% = no interruptions).
- **Tokens**: Completions per move. Indicates verbosity/efficiency.
- **Other**: Mistakes/1000 moves, cost/game, material diff, interruptions.

Primary sort: Elo (DESC), then Win/Loss (DESC), Duration (DESC), Tokens (ASC). Dragon-tested models marked with *.

Matrix View (in leaderboard): Win Rate (skill) vs. Duration (following) for 2D clustering.

## Sample Dialog (Single Move)

Example with GPT-4o Mini (Black):

```
Proxy (to Player_Black):
You are a professional chess player and you play as black. Now is your turn to make a move. Before making a move you can pick one of the following actions:
- 'get_current_board' to get the schema and current status of the board
- 'get_legal_moves' to get a UCI formatted list of available moves
- 'make_move <UCI formatted move>' when you are ready to complete your turn (e.g., 'make_move e2e4')
Respond with the action.

Player_Black (to Proxy):
get_current_board

Proxy (to Player_Black):
♜ ♞ ♝ ♛ ♚ ♝ ♞ ♜
♟ ♟ ♟ ♟ ♟ ♟ ♟ ♟
· · · · · · · ·
· · · · · · · ·
· · · · · · · ·
· · · · · · · ·
♙ ♙ ♙ ♙ ♙ ♙ ♙ ♙
♖ ♘ ♗ ♕ ♔ ♗ ♘ ♖


Player_Black (to Proxy):
get_legal_moves

Proxy (to Player_Black):
a7a6, b7b6, c7c6, d7d6, e7e6, f7f6, g7g6, h7h6, a7a5, b7b5, c7c5, d7d5, e7e5, f7f5, g7g5, h7h5

Player_Black (to Proxy):
make_move e7e5

Proxy (to Player_Black):
Move made, switching player
```

## References

- **Libraries**: `chess` (board rules), Autogen (agents/dialogs), Stockfish/Dragon (engines).
- **Data**: Logs in `_logs/`; analysis in `data_processing/` and `analysis_logs/`.
- **Notes/Changelog**: [docs/notes.md](docs/notes.md) for updates, model tiers, and insights.
- **License**: MIT (see LICENSE).
- **Contribute**: Fork, PR improvements to setup, agents, or analysis.

For issues or questions, open a GitHub issue.
