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
   # Using uv (recommended)
   uv sync
   ```

3. **Install dependencies**:
   ```
   # Already handled by `uv sync` above
   ```

4. **Configure LLMs**:
   - Copy `.env.sample` to `.env` and add your API keys.
   - Suffixes like `_W` (white) and `_B` (black) distinguish configs for multi-LLM setups.
   - Supports Azure OpenAI chat completions (`MODEL_KIND=azure`), Azure OpenAI Responses API (`MODEL_KIND=azure_responses`), OpenAI, Anthropic, Google, Groq, and local models via Autogen.
   - For local models, ensure Ollama or LM Studio is running.

5. **Chess Engines** (optional, for stronger opponents):
   - **Komodo Dragon**: Download binaries from [komodochess.com](https://komodochess.com/installation.htm) and place in `dragon/`. Set `llm_chess.dragon_path`.
   - **Stockfish**: Install via `brew install stockfish` (macOS) or equivalent. Set `llm_chess.stockfish_path` (default: `/opt/homebrew/bin/stockfish`).

## Running Games

### Single Game
Run a single chess simulation:
```
uv run llm-chess
```
- Default: Random Player (white) vs. LLM (black).
- Logs saved to `_logs/` with JSON details and optional video recordings.

### Multiple Games
For benchmarking, run multiple simulations:
```
uv run python run_multiple_games.py
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

- Provider choice comes from `MODEL_KIND_W` / `MODEL_KIND_B` in `.env`.
- Use `azure` for classic Azure chat-completions deployments.
- Use `azure_responses` for Azure deployments that require the Responses API. Keep `AZURE_OPENAI_ENDPOINT_*` at the resource root such as `https://your-resource.openai.azure.com`; the runtime will normalize it to the Responses base path automatically.

- `white_player_type` / `black_player_type`: `RANDOM_PLAYER`, `LLM`, `CHESS_ENGINE_DRAGON`, `CHESS_ENGINE_STOCKFISH`, `TYPESAFE_JEV`.
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
    - Practical rule of thumb for stronger models:
      - Use completed games at the strongest Dragon level already tested and compute `S = (wins + 0.5 * draws) / N`.
      - If `35% <= S <= 65%`, stay at that level; this is the informative range for Elo estimation.
      - If `S > 65%` across roughly 15 to 20 clean games, test a higher Dragon level.
      - If `65% <= S < 80%`, move up 1 level. If `80% <= S < 90%`, move up 2 levels. If `S >= 90%`, move up 3 levels.
      - If the model is at `100%` wins on its strongest tested level, treat the current Elo as under-resolved and keep raising Dragon until the strongest-level score drops back near `35%` to `65%`.
  - **Stockfish**: Strong engine; install separately.
  - **TypeSafe Jev**: Constrained Choice player via TypeSafe System One (not a dialog LLM). Set `PlayerType.TYPESAFE_JEV`, provide `TYPESAFE_API_KEY`, optional `TYPESAFE_MODEL` (default `jev-latest`). See [TypeSafe Jev request / response](#typesafe-jev-request--response) for the per-move I/O shape. Usage is accumulated into game `usage_stats` (input $0.042/1M tokens; output free).

## Processing Logs

Logs in `_logs/` contain JSON per game. Aggregate and refine:

   ```
   uv run get-refined-csv
   ```
   - Handles multiple directories (Random vs. LLM, Dragon vs. LLM).
   - Computes Elo (anchored to Dragon levels: Elo ≈ 125 × (level + 1)), Win/Loss %, Game Duration %.
   - Filters low-sample models; supports overrides/aliases.
   - Output: CSV with player stats, usage (tokens/cost), interruptions.



Manual review: Check logs for API errors (discard) vs. model failures (LLM loss).

## Tests

Run the test suite (parallel by default):

```
uv run pytest -q -n auto tests
```

## Metrics

From refined CSV/leaderboard:

- **Elo**: Estimated rating (±95% CI), anchored to Dragon/chess.com. Combines Random/Dragon data.
- **Win/Loss**: (Wins - Losses) / Total % (0-100%). Blends skill + instruction following. 50% = balanced.
- **Game Duration**: % of max moves completed (0-100%). Measures dialog stability (100% = no interruptions).
- **Tokens**: Completions per move. Indicates verbosity/efficiency.
- **Other**: Mistakes/1000 moves, cost/game, material diff, interruptions.

Primary sort: Elo (DESC), then Win/Loss (DESC), Duration (DESC), Tokens (ASC). Dragon-tested models marked with *.

Matrix View (in leaderboard): Win Rate (skill) vs. Duration (following) for 2D clustering.


## TypeSafe Jev request / response

Jev is **not** a chat model. There is no multi-turn `get_board` / `get_legal_moves` dialog. For each ply, `TypeSafeJevAgent` makes **one** TypeSafe System One call (`POST /v1/systemone` via `typesafe-sdk`), then returns a single Proxy action string: `make_move <uci>`.

Batch helpers: `run_jev_vs_random.py`, `run_jev_vs_dragon.py` (need `TYPESAFE_API_KEY` in `.env`).

### Simplified schema

```text
Runner (per ply)
  │
  ├─ state: { fen, side_to_move }          # board snapshot
  ├─ model: "jev-latest"                   # or TYPESAFE_MODEL / pinned id
  └─ questions.move: Choice
        instructions: "best legal move…"
        criteria: { "<uci>": "<SAN>", … }  # ≤255 legal options
        │
        ▼  TypeSafe System One (Jev)
        │
Response
  ├─ answers.move: { type, choice, probabilities, confidence }
  │                 choice ∈ criteria keys (UCI)
  └─ usage: { input_tokens, output_tokens }
        │
        ▼
Agent → Proxy:  "make_move <uci>"
```

Wire field names match the API (`answers`). The Python SDK also exposes `response.choices["move"]` as a filtered view of Choice answers; this repo reads `response.choices["move"].choice`.

### Detailed per-move exchange

**1. Build inputs from `python-chess`**

| Field | Source | Notes |
|-------|--------|--------|
| `state.fen` | `board.fen()` | Full FEN including side, castling, EP, clocks |
| `state.side_to_move` | `"white"` / `"black"` from `board.turn` | Redundant with FEN; kept explicit for the model |
| `questions.move.criteria` | `{ move.uci(): board.san(move) for move in board.legal_moves }` | Keys = UCI (what we play); values = SAN (human-readable criteria text) |
| Cap | `len(criteria) ≤ 255` | TypeSafe Choice limit; rare chess positions can exceed this (agent errors out today) |

**2. Example request** (Black to move after `1. e4`, abbreviated criteria)

Equivalent JSON body sent to `https://api.typesafe.ai/v1/systemone`:

```json
{
  "model": "jev-latest",
  "state": {
    "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
    "side_to_move": "black"
  },
  "questions": {
    "move": {
      "type": "choice",
      "instructions": "Choose the best legal chess move for the side to move. Options are UCI moves; descriptions are SAN.",
      "criteria": {
        "e7e5": "e5",
        "c7c5": "c5",
        "g8f6": "Nf6",
        "b8c6": "Nc6",
        "d7d5": "d5"
      }
    }
  }
}
```

In code (`custom_agents.TypeSafeJevAgent._system_one_move`):

```python
from typesafe_sdk import Choice, TypeSafeClient

state = {"fen": board.fen(), "side_to_move": "black"}  # or "white"
criteria = {m.uci(): board.san(m) for m in board.legal_moves}  # full legal set

with TypeSafeClient(model="jev-latest") as client:
    response = client.system_one(
        state=state,
        questions={
            "move": Choice(
                instructions=(
                    "Choose the best legal chess move for the side to move. "
                    "Options are UCI moves; descriptions are SAN."
                ),
                criteria=criteria,
            ),
        },
    )

uci = response.choices["move"].choice   # must be a key in criteria
# → agent returns: f"make_move {uci}"
```

Auth: `TYPESAFE_API_KEY` (SDK default). Model: constructor arg, else `TYPESAFE_MODEL`, else `jev-latest`.

**3. Example response** (illustrative probabilities; real values vary)

```json
{
  "model": "jev-latest",
  "answers": {
    "move": {
      "type": "choice",
      "choice": "e7e5",
      "confidence": 0.72,
      "probabilities": {
        "e7e5": 0.41,
        "c7c5": 0.28,
        "g8f6": 0.18,
        "b8c6": 0.08,
        "d7d5": 0.05
      }
    }
  },
  "usage": {
    "input_tokens": 1840,
    "output_tokens": 420
  }
}
```

| Response field | Use in llm_chess |
|----------------|------------------|
| `answers.move.choice` | Selected UCI; validated ∈ `criteria`, then `make_move {uci}` |
| `answers.move.probabilities` | Not logged today (available on the SDK object) |
| `answers.move.confidence` | Not logged today |
| `usage.input_tokens` | Added to `total_prompt_tokens`; cost `× $0.042 / 1M` |
| `usage.output_tokens` | Added to `total_completion_tokens`; **not billed** (price 0 in `models_metadata.csv`) |

**4. What the Proxy / game log sees**

Unlike dialog LLMs, the Autogen `.txt` trace only shows the thin wrapper (`make_move e7e5`). There is no free-text board dump from Jev. Per-game JSON still records `player_black.model` (e.g. `jev-latest`), `accumulated_reply_time_seconds`, and top-level `usage_stats.black` with token totals and cost.

**5. Contrast with dialog LLMs**

| | Dialog LLM (`LLM_BLACK`) | TypeSafe Jev |
|--|--------------------------|--------------|
| Protocol | Multi-turn Proxy chat | One System One call / ply |
| Board access | `get_current_board` / `get_legal_moves` | FEN + full legal Choice in the request |
| Move output | Free-text `make_move <uci>` (must parse) | Typed `choice` ∈ UCI keys |
| Failure mode | Illegal / unparseable → wrong_actions | Missing/illegal choice → retry or `None` |

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
- **Data**: Logs in `_logs/`; analysis in `data/`.
- **Notes/Changelog**: [docs/notes.md](docs/notes.md) for updates, model tiers, and insights.
- **License**: MIT (see LICENSE).
- **Contribute**: Fork, PR improvements to setup, agents, or analysis.

For issues or questions, open a GitHub issue.
