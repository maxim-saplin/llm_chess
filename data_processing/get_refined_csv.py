"""
Refine per-game chess logs and print leaderboards.

Modes (GameMode):
- RANDOM_VS_LLM: White=random, Black=LLM. Groups by Player. Writes data_processing/refined.csv.
  Leaderboard: Win/Loss DESC, then Game Duration DESC, then Tokens ASC.
- DRAGON_VS_LLM: White=Dragon, Black=LLM. Groups by (Player, white_opponent). Writes
  data_processing/dragon_refined.csv. Leaderboard: Dragon level ASC, then Win Rate DESC,
  then Win/Loss DESC.
- ELO: Combines Random-vs-LLM and Dragon-vs-LLM to estimate Elo per Player and prints an Elo
  leaderboard. Writes data_processing/elo_refined.csv.

Elo (brief):
- Anchors: Dragon level ℓ → Elo = 125(ℓ+1). Random is calibrated vs Dragon using misc/dragon
  aggregates. Color advantage γ=35: models play Black, so we adjust by +γ (equivalently shift
  the opponent Elo).
- Estimation: For each Player, collect blocks (opponent Elo, wins, draws, losses) across
  Random (if calibrated) and Dragon. If ELO_DRAGON_ONLY_MIN_GAMES>0 and a Player meets it,
  Elo uses dragon-only; 0 means always mix. Solve Σ n_k (s_k − E_k(R)) = 0 via Brent; 95% CI
  from Fisher information. Columns added: elo, elo_moe_95, games_vs_random, games_vs_dragon.
- Empty Elo: left blank if no anchored-opponent games exist, or if all outcomes vs anchored
  opponents are 100% wins or 100% losses (MLE diverges).

Data sources:
- Random logs: _logs/rand_vs_llm, _logs/_pre_aug_2025/new, _logs/_pre_aug_2025/no_reflection.
- Dragon logs: _logs/engine_vs_llm and _logs/_pre_aug_2025/dragon_vs_llm.
- Random calibration: _logs/misc/dragon and _logs/_pre_aug_2025/misc/dragon.

Usage:
- Programmatic: call build_refined_rows_from_logs(..., mode=GameMode.*) then write_* CSV.
- CLI: run this module with GAME_MODE set; Elo leaderboard sorts by Elo DESC, then Win Rate,
  then Win/Loss.
- Optional: set INCLUDE_ABNORMAL_FINISH_STATS=True to emit per-reason abnormal termination counts
  (Too many wrong actions, max turns, unknown issues, runtime errors) in the refined CSV outputs.

Model naming (applies to Dragon mode, Elo, and any consumer of Dragon logs):
1. Directory aliases: entries inside LOGS_DIRS/ENGINE_LOGS_DIRS can be dicts such as
   {"path": "alias"}. Every JSON under that path is forced to the alias before any other rule.
2. Structured runs: if `_run.json` exists, _model_label_from_run_json() reads llm_configs,
   takes the base model, and appends reasoning_effort plus thinking_budget as
   `model-reasoning-thinking_XXXX`.
3. Legacy runs without `_run.json`: we fall back to the model identifier recorded in
   the per-game JSON (Player_Black.model).
4. Usage Stats Fallback: If the model is "N/A", "placeholder", or "Player_Black", we attempt
   to recover the model ID from `usage_stats.black` keys (ignoring "total_cost").
   Directory names are NOT used to infer model IDs.
5. Overrides & ignores: MODEL_OVERRIDES rewrites specific run directory suffixes (or maps them
   to `"ignore"` so the run is dropped) before logs are grouped.
6. Aliases: after logs are loaded, ALIASES normalizes already-clean labels to preferred display
   names, letting us merge vendor spelling variants without editing old runs.
7. Filters: FILTER_OUT_MODELS removes models from leaderboards entirely even if earlier steps
   produced a label.
These steps happen once when logs are ingested; the same canonical name drives refined CSVs,
pricing lookups, win-rate exports, and Elo estimation, so directory hygiene matters.

Pricing & tokens: model prices from data_processing/models_metadata.csv (per 1M tokens). If
usage missing, cost/token metrics fall back to 0 for that game.
"""

import os
import csv
import json
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar, Dict, Any, List, Union, Tuple
from statistics import mean, stdev
from functools import lru_cache
from tabulate import tabulate
from scipy.optimize import root_scalar
from llm_chess import TerminationReason

# Source directories for Random-vs-LLM runs (Black = LLM). Order matters when deduping.
LOGS_DIRS = [
    "_logs/rand_vs_llm",
    "_logs/_pre_aug_2025/new",
    "_logs/_pre_aug_2025/no_reflection",  # 16.03.2025 - wrong actions and wrong moves stats has been wrongly collected (underreporting) in all prior logs, the mistakes metric for all prior logs in invalid
]


# Game modes supported by this module.
class GameMode(Enum):
    RANDOM_VS_LLM = "random_vs_llm"
    DRAGON_VS_LLM = "dragon_vs_llm"
    ELO = "elo"


# Default CLI mode; tests change this at runtime.
GAME_MODE: GameMode = GameMode.ELO

# Engine-vs-LLM sources. `_logs/engine_vs_llm` is the structured pipeline; `_pre_aug_2025`
# contains legacy folders that still feed historical stats and Elo calibration.
ENGINE_LOGS_DIRS_NEW = [
    "_logs/engine_vs_llm",
]
ENGINE_LOGS_DIRS_LEGACY = [
    "_logs/_pre_aug_2025/dragon_vs_llm",
]

FILTER_OUT_BELOW_N_RANDOM = 10
FILTER_OUT_BELOW_N_MISC = 2
DATE_AFTER = None  # "2025.12.01_00:00"

# Output files
OUTPUT_DIR = "data_processing"
REFINED_CSV = os.path.join(OUTPUT_DIR, "refined.csv")

# Elo mode constants and outputs
ELO_REFINED_CSV = os.path.join(OUTPUT_DIR, "elo_refined.csv")
ELO_WHITE_ADVANTAGE = 35.0
# If >0 and a model has at least this many Dragon games, compute Elo from Dragon-only blocks.
# If set to 0, always mix Random and Dragon blocks when Random is calibrated.
ELO_DRAGON_ONLY_MIN_GAMES = 0

# Directories with engine aggregate records for Random/Stockfish vs Dragon
MISC_DRAGON_DIRS = [
    "_logs/misc/dragon",
    "_logs/_pre_aug_2025/misc/dragon",
]

FILTER_OUT_MODELS = [
    "llama-4-scout-17b-16e-instruct",
    "N/A",
    "o4-mini-2025-04-16-high_timeout-60m",
    "o4-mini-2025-04-16-high_timeout-20m",
    "o3-2025-04-16-medium_timeout-60m",
    "deepseek-r1-distill-qwen-32b@q4_k_m|noisol_temp03",
    "deepseek-r1-distill-qwen-32b@q4_k_m|noisol_temp06",
    "anthropic.claude-v3-5-sonnet",
    "llama-3.1-tulu-3-8b@q4_k_m",
    "claude-3-5-haiku",  # using newer runs
    "anthropic.claude-v3-5-sonnet-v2",  # using newer runs
    "anthropic.claude-v3-5-sonnet-v1",  # using newer runs
    "anthropic.claude-3-7-sonnet-20250219-v1:0",  # using newer runs
    "llama-3.1-8b-instant",  # Groq
    "meta-llama-3.1-8b-instruct-fp16",  # local
    "gemini-2.0-pro-exp-02-05",  # to many errors, I'm done with EXP models, to much trouble, going to use only release versions
    "qwq-32b-thinking-not-cleaned",
    "google_gemma-3-27b-it@q4_k_m",
    "google_gemma-3-12b-it@q4_k_m",
    "ring-mini-2.0@q4_k_m",
    "gpt-5-codex-2025-09-15-low",  # too many errors
    "gpt-4o-mini-2024-07-18-moa-basline",
    "rekaai_reka-flash-3@q6_k_l",
    "mixtral-8x7b-32768",
    "qwen2.5-vl-72b-instruct",
    "gpt-5.1-codex-mini-2025-11-13-high",  ## TBD, to few runs
    "gpt-5-2025-08-07-medium",  ## TBD, to few runs
    "ignore",  # models marked to be ignored via MODEL_OVERRIDES
]

# Per-run path filters (skip failed/error batches without touching the filesystem).
FILTER_OUT_PATH_KEYWORDS = ["errors-", "fails-", "skip-"]

# Paths to suppress "Recovered model from usage_stats" warnings for
SUPPRESS_MODEL_RECOVERY_WARNINGS = [
    "lvl-1_vs_claude-3-7-sonnet-20250219-thinking-budget-5000",
    "lvl-1_vs_o3-mini-2025-01-31-medium",
    "lvl-1_vs_o4-mini-2025-04-16-medium",
]

# Models whose tokens and price metrics should be zeroed
ZERO_TOKENS: set[str] = {
    "grok-3-mini-beta-low",
    "grok-3-mini-beta-high",
}  # Grok-3 reasoning logs have wrong token usage due tp different reporting by API (https://dev.to/maximsaplin/grok-3-api-reasoning-tokens-are-counted-differently-197)

# Metadata CSV for pricing
MODELS_METADATA_CSV = "data_processing/models_metadata.csv"

# Model naming controls:
# - MODEL_OVERRIDES: rewrite specific run directories when the log label is wrong or should be ignored.
#   Key: trailing path segment (timestamp folder parent). Value: replacement label; use "ignore" to drop the run.
# - ALIASES: normalize already-clean labels (exact match) to preferred display names.
MODEL_OVERRIDES = {
    "2025-21-01_deepseek-r1-distill-qwen-32b@q4_k_m_no_thinking_isol": "deepseek-r1-distill-qwen-32b@q4_k_m|noisol_temp03",
    "2025-21-01_deepseek-r1-distill-qwen-32b@q4_k_m_temp06_thinking_isol": "deepseek-r1-distill-qwen-32b@q4_k_m|isol_temp06",
    "2025-21-01_deepseek-r1-distill-qwen-32b@q4_k_m_temp06_no_thinking_isol": "deepseek-r1-distill-qwen-32b@q4_k_m|noisol_temp06",
    "2025-02-06_o3-mini-2025-01-31_1": "ignore",
    "2025-02-06_o3-mini-2025-01-31_2": "ignore",
    "2025-02-06_o3-mini-2025-01-31_3": "ignore",
    "2025-02-09_o3-mini-2025-01-31-high_24_GAMES_TIMEDOUT": "ignore",
    "2025-02-10_o3-mini-2025-01-31-high-again_timeouts": "ignore",
    "2025-02-10_o1-mini-2024-09-12_plenty_connection_errors": "ignore",
}
ALIASES = {
    # Use sparingly: these aliases are applied after overrides and after _run.json inference.
    # If the incoming name equals the key, replace it with the curated value.
    "grok-3-mini-fast-beta-high": "grok-3-mini-beta-high",
}


# Toggle abnormal-finish instrumentation directly in this module (no CLI flag needed).
# When enabled, refined CSVs add per-reason counts/percents for early terminations such as
# too many wrong actions, max turns, unknown issues, or runtime errors.
INCLUDE_ABNORMAL_FINISH_STATS = False
ABNORMAL_TERMINATION_REASONS = {
    "too_many_wrong_actions": TerminationReason.TOO_MANY_WRONG_ACTIONS.value,
    "max_turns": TerminationReason.MAX_TURNS.value,
    "unknown_issue": TerminationReason.UNKNOWN_ISSUE.value,
    "error": TerminationReason.ERROR.value,
}
ABNORMAL_TERMINATION_LOOKUP = {v: k for k, v in ABNORMAL_TERMINATION_REASONS.items()}
ABNORMAL_FINISH_HEADERS: list[str] = []
if INCLUDE_ABNORMAL_FINISH_STATS:
    ABNORMAL_FINISH_HEADERS = [
        "abnormal_finishes_total",
        "abnormal_finishes_percent",
    ]
    for slug in ABNORMAL_TERMINATION_REASONS:
        ABNORMAL_FINISH_HEADERS.append(f"abnormal_{slug}_count")
        ABNORMAL_FINISH_HEADERS.append(f"abnormal_{slug}_percent")


#
# Log loading and builder (unified, no aggregate.csv dependency)
#


@dataclass
class PlayerStats:
    name: str
    wrong_moves: int
    wrong_actions: int
    reflections_used: int
    reflections_used_before_board: int
    model: str
    get_board_count: int = -1
    get_legal_moves_count: int = -1
    make_move_count: int = -1
    accumulated_reply_time_seconds: float = 0.0

    @property
    def mistakes(self) -> int:
        return self.wrong_moves + self.wrong_actions


@dataclass
class UsageStats:
    total_cost: float
    prompt_tokens: int = 0
    completion_tokens: int = 0
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GameLog:
    time_started: str
    winner: str
    reason: str
    number_of_moves: int
    player_white: PlayerStats
    player_black: PlayerStats
    material_count: Dict[str, int]
    usage_stats_white: UsageStats
    usage_stats_black: UsageStats
    # For engine-vs-LLM mode; opponent descriptor e.g., "dragon-lvl-3"
    white_opponent: str = ""

    max_moves_in_game: ClassVar[int] = 200

    @property
    def is_interrupted(self) -> int:
        return self.reason in {
            TerminationReason.ERROR.value,
            TerminationReason.UNKNOWN_ISSUE.value,
            TerminationReason.MAX_TURNS.value,
            TerminationReason.TOO_MANY_WRONG_ACTIONS.value,
        }

    @property
    def game_duration(self) -> float:
        return 1.0 if not self.is_interrupted else self.number_of_moves / GameLog.max_moves_in_game


@lru_cache(maxsize=4096)
def _compose_model_label(base_model: str, reasoning_effort: str | None, thinking_budget: int | None) -> str:
    """Combine raw model plus reasoning knobs into a single stable label."""
    suffix: list[str] = []
    if isinstance(reasoning_effort, str) and reasoning_effort:
        suffix.append(reasoning_effort)
    if isinstance(thinking_budget, int) and thinking_budget > 0:
        suffix.append(f"thinking_{thinking_budget}")
    return f"{base_model}-{'-'.join(suffix)}" if suffix else base_model


@lru_cache(maxsize=4096)
def _model_label_from_run_json(run_dir: str) -> str | None:
    """Parse `_run.json` next to a run folder to recover the canonical label.

    Reads llm_configs[{white|black}] → {model, reasoning_effort, thinking_budget} and feeds the
    values into `_compose_model_label`. Returns None if the file is missing or malformed."""
    try:
        run_json_path = os.path.join(run_dir, "_run.json")
        if not os.path.exists(run_json_path):
            return None
        with open(run_json_path, "r", encoding="utf-8") as f:
            md = json.load(f)

        player_types = md.get("player_types") or {}
        llm_configs = md.get("llm_configs") or {}

        side_key = None
        if player_types.get("black_player_type") in ("LLM_BLACK", "LLM_NON"):
            side_key = "black"
        elif player_types.get("white_player_type") in ("LLM_WHITE", "LLM_NON"):
            side_key = "white"
        else:
            side_key = "black"

        side_cfg = llm_configs.get(side_key)
        if not isinstance(side_cfg, dict):
            return None

        base_model = side_cfg.get("model")
        reasoning = side_cfg.get("reasoning_effort")
        thinking_budget = side_cfg.get("thinking_budget")
        if not base_model:
            return None
        return _compose_model_label(base_model, reasoning, thinking_budget)
    except Exception:
        return None


@lru_cache(maxsize=4096)
def _white_opponent_from_run_dir(run_dir: str) -> str | None:
    """Infer white opponent label for engine-vs-LLM runs.

    Priority:
    1) Read from _run.json → chess_engines.dragon.level → "dragon-lvl-{level}"
    2) Infer from path segment: any "dragon-lvl-{N}" or "lvl-{N}" → "dragon-lvl-{N}"
    """
    try:
        run_json_path = os.path.join(run_dir, "_run.json")
        if os.path.exists(run_json_path):
            with open(run_json_path, "r", encoding="utf-8") as f:
                md = json.load(f)
            engines = md.get("chess_engines") or {}
            dragon = engines.get("dragon") if isinstance(engines, dict) else None
            if isinstance(dragon, dict) and "level" in dragon:
                level = dragon.get("level")
                try:
                    level_int = int(level)
                    return f"dragon-lvl-{level_int}"
                except Exception:
                    print(f"WARNING: Invalid dragon level in _run.json at {run_dir}: {level}")
            else:
                print(f"WARNING: No dragon engine section in _run.json at {run_dir}")
        # Path-based fallback
        path_lower = run_dir.lower()
        import re

        m = re.search(r"dragon-lvl-(\d+)", path_lower)
        if m:
            return f"dragon-lvl-{int(m.group(1))}"
        m2 = re.search(r"lvl-(\d+)", path_lower)
        if m2:
            return f"dragon-lvl-{int(m2.group(1))}"
        return None
    except Exception:
        return None


def load_game_log(file_path: str) -> GameLog:
    """Load a single per-game JSON into a strongly typed GameLog dataclass."""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

        def _extract_usage(stats_dict: dict) -> UsageStats:
            total_cost = stats_dict.get("total_cost", 0)
            prompt_tokens = 0
            completion_tokens = 0

            # Find the inner dictionary that holds token counts (keyed by model name)
            for k, v in stats_dict.items():
                if k != "total_cost" and isinstance(v, dict):
                    prompt_tokens = v.get("prompt_tokens", 0)
                    completion_tokens = v.get("completion_tokens", 0)
                    break

            return UsageStats(
                total_cost=total_cost,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                details=stats_dict,
            )

        return GameLog(
            time_started=data["time_started"],
            winner=data["winner"],
            reason=data["reason"],
            number_of_moves=data["number_of_moves"],
            player_white=PlayerStats(**data["player_white"]),
            player_black=PlayerStats(**data["player_black"]),
            material_count=data["material_count"],
            usage_stats_white=_extract_usage(data["usage_stats"]["white"]),
            usage_stats_black=_extract_usage(data["usage_stats"]["black"]),
        )


def load_game_logs(
    logs_dirs: Union[str, List[Union[str, Dict[str, str]]]],
    model_overrides: dict | None = None,
    mode: GameMode = GAME_MODE,
) -> List[GameLog]:
    """Walk configured directories, load valid JSON logs, and normalize model labels."""
    logs: list[GameLog] = []
    # Maps absolute dir paths → forced labels (configured via LOGS_DIRS entries that are dicts).
    directory_aliases: dict[str, str] = {}

    if isinstance(logs_dirs, str):
        logs_dirs = [logs_dirs]

    processed_logs_dirs: list[str] = []
    for entry in logs_dirs:
        if isinstance(entry, dict):
            for dir_path, alias in entry.items():
                processed_logs_dirs.append(dir_path)
                directory_aliases[dir_path] = alias
        else:
            processed_logs_dirs.append(entry)

    for logs_dir in processed_logs_dirs:
        for root, _, files in os.walk(logs_dir):
            for file in files:
                if file.endswith(".json") and not file.endswith("_aggregate_results.json") and file != "_run.json":
                    file_path = os.path.join(root, file)
                    # Filter out paths containing excluded keywords
                    file_path_lower = file_path.lower()
                    if any(keyword.lower() in file_path_lower for keyword in FILTER_OUT_PATH_KEYWORDS):
                        continue
                    try:
                        game_log = load_game_log(file_path)
                        run_dir = os.path.dirname(file_path)

                        if mode == GameMode.RANDOM_VS_LLM:
                            # Ensure opponent and black roles are expected
                            if game_log.player_white.name != "Random_Player":
                                continue
                            if game_log.player_black.name != "Player_Black":
                                continue

                            if logs_dir in directory_aliases:
                                # Hard override: entire directory is aliased to a single label.
                                model_name = directory_aliases[logs_dir]
                            else:
                                label_from_run = _model_label_from_run_json(run_dir)
                                model_name = label_from_run or game_log.player_black.model
                                if model_overrides:
                                    key = next((k for k in model_overrides if os.path.dirname(file_path).endswith(k)), None)
                                    if key:
                                        model_name = model_overrides[key]

                            game_log.player_black.model = model_name
                            logs.append(game_log)

                        elif mode == GameMode.DRAGON_VS_LLM:
                            # Require LLM on black
                            if game_log.player_black.name != "Player_Black":
                                continue

                            # New-format strictness: require _run.json under engine_vs_llm base
                            is_new_format_base = os.path.normpath(logs_dir).endswith(os.path.normpath("_logs/engine_vs_llm"))

                            # Resolve model label
                            label_from_run = _model_label_from_run_json(run_dir)

                            model_name = label_from_run or game_log.player_black.model

                            if not is_new_format_base and model_name in ("placeholder", "Player_Black", "N/A", ""):
                                # Try to recover from usage_stats keys (ignore total_cost)
                                candidate = None
                                if game_log.usage_stats_black and game_log.usage_stats_black.details:
                                    candidate = next((k for k in game_log.usage_stats_black.details.keys() if k != "total_cost"), None)

                                if candidate:
                                    if not any(s in file_path for s in SUPPRESS_MODEL_RECOVERY_WARNINGS):
                                        print(
                                            f"WARNING: Recovered model '{candidate}' from usage_stats for log with invalid model '{model_name}' at {file_path}"
                                        )
                                    model_name = candidate
                                else:
                                    print(
                                        f"WARNING: Could not determine model ID for log at {file_path}. Player.model='{model_name}', usage_stats keys={list(game_log.usage_stats_black.details.keys()) if game_log.usage_stats_black.details else 'None'}"
                                    )

                            if label_from_run is None:
                                if is_new_format_base:
                                    print(
                                        f"WARNING: Missing or invalid _run.json for run at {run_dir}; skipping (engine_vs_llm new format)"
                                    )
                                    continue

                            if logs_dir in directory_aliases:
                                # Even Dragon runs can be hard-aliased directory-wide.
                                model_name = directory_aliases[logs_dir]
                            if model_overrides:
                                key = next((k for k in model_overrides if os.path.dirname(file_path).endswith(k)), None)
                                if key:
                                    model_name = model_overrides[key]

                            # Resolve white opponent (engine descriptor)
                            white_op = _white_opponent_from_run_dir(run_dir)
                            if white_op is None:
                                if is_new_format_base:
                                    print(f"WARNING: Could not infer dragon engine level for run at {run_dir}; skipping")
                                    continue
                                else:
                                    # Legacy path without clear level — skip conservatively
                                    print(f"WARNING: Legacy path without parseable dragon level at {run_dir}; skipping")
                                    continue

                            game_log.player_black.model = model_name
                            game_log.white_opponent = white_op
                            logs.append(game_log)

                        else:
                            # Unknown mode; skip
                            continue
                    except Exception:
                        # Skip invalid JSON files
                        continue
    return logs


def load_model_prices(metadata_file_path: str) -> dict[str, tuple[float, float]]:
    model_prices: dict[str, tuple[float, float]] = {}
    try:
        with open(metadata_file_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if len(row) >= 3 and row[0].strip() and row[1].strip() and row[2].strip():
                    model_name = row[0].strip()
                    try:
                        prompt_price = float(row[1].strip().replace(",", ""))
                        completion_price = float(row[2].strip().replace(",", ""))
                        model_prices[model_name] = (prompt_price, completion_price)
                    except (ValueError, IndexError):
                        continue
    except Exception:
        pass
    return model_prices


def build_refined_rows_from_logs(
    logs_dirs: Union[str, List[Union[str, Dict[str, str]]]],
    model_overrides: dict | None = None,
    only_after_date: str | None = None,
    filter_out_below_n: int = 30,
    filter_out_models: list[str] | None = None,
    model_aliases: dict[str, str] | None = None,
    models_metadata_csv: str = MODELS_METADATA_CSV,
    mode: GameMode = GAME_MODE,
) -> list[dict[str, Any]]:
    if filter_out_models is None:
        filter_out_models = []
    if model_aliases is None:
        model_aliases = {}

    logs = load_game_logs(logs_dirs, model_overrides, mode=mode)
    if only_after_date:
        logs = [log for log in logs if log.time_started >= only_after_date]

    # Group by model (and by white_opponent in dragon mode)
    if mode == GameMode.DRAGON_VS_LLM:
        model_groups: dict[tuple[str, str], list[GameLog]] = {}
        for log in logs:
            model_name = log.player_black.model
            model_name = model_aliases.get(model_name, model_name)
            if model_name in filter_out_models:
                continue
            opponent_label = log.white_opponent or "dragon-lvl-?"
            model_groups.setdefault((model_name, opponent_label), []).append(log)
    else:
        model_groups: dict[str, list[GameLog]] = {}
        for log in logs:
            model_name = log.player_black.model
            model_name = model_aliases.get(model_name, model_name)
            if model_name in filter_out_models:
                continue
            model_groups.setdefault(model_name, []).append(log)

    model_prices = load_model_prices(models_metadata_csv)

    refined_rows: list[dict[str, Any]] = []
    for group_key, model_logs in model_groups.items():
        if mode == GameMode.DRAGON_VS_LLM:
            model_name, opponent_label = group_key
        else:
            model_name = group_key
            opponent_label = ""
        total_games = len(model_logs)
        if total_games < filter_out_below_n:
            continue

        black_llm_wins = sum(1 for log in model_logs if log.winner in ("Player_Black", "NoN_Synthesizer"))
        opponent_wins = sum(1 for log in model_logs if log.winner == log.player_white.name)
        draws = total_games - black_llm_wins - opponent_wins

        player_wins_percent = (black_llm_wins / total_games) * 100 if total_games > 0 else 0
        player_draws_percent = (draws / total_games) * 100 if total_games > 0 else 0

        # Normalized win_loss in [0,1]
        win_loss = (((black_llm_wins - opponent_wins) / total_games) / 2 + 0.5) if total_games > 0 else 0.5
        per_game_win_loss = [
            (1 / 2 + 0.5)
            if log.winner in ("Player_Black", "NoN_Synthesizer")
            else (-1 / 2 + 0.5)
            if log.winner == log.player_white.name
            else 0.5
            for log in model_logs
        ]
        std_dev_win_loss = stdev(per_game_win_loss) if total_games > 1 else 0
        moe_win_loss = 1.96 * (std_dev_win_loss / math.sqrt(total_games)) if total_games > 1 else 0

        game_duration = mean([log.game_duration for log in model_logs]) if model_logs else 0
        std_dev_game_duration = stdev([log.game_duration for log in model_logs]) if total_games > 1 else 0
        moe_game_duration = 1.96 * (std_dev_game_duration / math.sqrt(total_games)) if total_games > 1 else 0

        games_interrupted = sum(1 for log in model_logs if log.is_interrupted)
        games_interrupted_percent = (games_interrupted / total_games * 100) if total_games > 0 else 0
        p_interrupted = games_interrupted / total_games if total_games > 0 else 0
        std_dev_games_interrupted = math.sqrt((p_interrupted * (1 - p_interrupted)) / total_games) if total_games > 1 else 0
        moe_games_interrupted = 1.96 * std_dev_games_interrupted if total_games > 1 else 0

        games_not_interrupted = total_games - games_interrupted
        games_not_interrupted_percent = (games_not_interrupted / total_games * 100) if total_games > 0 else 0
        p_not_interrupted = games_not_interrupted / total_games if total_games > 0 else 0
        std_dev_games_not_interrupted = math.sqrt((p_not_interrupted * (1 - p_not_interrupted)) / total_games) if total_games > 1 else 0
        moe_games_not_interrupted = 1.96 * std_dev_games_not_interrupted if total_games > 1 else 0

        if INCLUDE_ABNORMAL_FINISH_STATS:
            abnormal_counts = {slug: 0 for slug in ABNORMAL_TERMINATION_REASONS}
            for log in model_logs:
                slug = ABNORMAL_TERMINATION_LOOKUP.get(log.reason)
                if slug:
                    abnormal_counts[slug] += 1
            abnormal_total = sum(abnormal_counts.values())
            row_abnormal_percent = round((abnormal_total / total_games) * 100, 3) if total_games > 0 else 0

        # win_loss excluding interrupted games
        non_interrupted_logs = [log for log in model_logs if not log.is_interrupted]
        non_interrupted_games = len(non_interrupted_logs)
        if non_interrupted_games > 0:
            black_llm_wins_ni = sum(1 for log in non_interrupted_logs if log.winner in ("Player_Black", "NoN_Synthesizer"))
            opponent_wins_ni = sum(1 for log in non_interrupted_logs if log.winner == log.player_white.name)
            win_loss_non_interrupted = ((black_llm_wins_ni - opponent_wins_ni) / non_interrupted_games) / 2 + 0.5
            per_game_win_loss_ni = [
                (1 / 2 + 0.5)
                if log.winner in ("Player_Black", "NoN_Synthesizer")
                else (-1 / 2 + 0.5)
                if log.winner == log.player_white.name
                else 0.5
                for log in non_interrupted_logs
            ]
            std_dev_win_loss_non_interrupted = stdev(per_game_win_loss_ni) if non_interrupted_games > 1 else 0
            moe_win_loss_non_interrupted = (
                1.96 * (std_dev_win_loss_non_interrupted / math.sqrt(non_interrupted_games)) if non_interrupted_games > 1 else 0
            )
        else:
            win_loss_non_interrupted = 0.5
            moe_win_loss_non_interrupted = 0

        llm_total_moves = sum(log.number_of_moves for log in model_logs)
        llm_wrong_actions = sum(log.player_black.wrong_actions for log in model_logs)
        llm_wrong_moves = sum(log.player_black.wrong_moves for log in model_logs)

        per_game_llm_material = [log.material_count["black"] for log in model_logs]
        per_game_rand_material = [log.material_count["white"] for log in model_logs]
        llm_avg_material = mean(per_game_llm_material)
        rand_avg_material = mean(per_game_rand_material)

        per_game_material_diff = [lm - rm for lm, rm in zip(per_game_llm_material, per_game_rand_material)]
        material_diff_llm_minus_rand = mean(per_game_material_diff)
        std_dev_material_diff = stdev(per_game_material_diff) if total_games > 1 else 0
        moe_material_diff_llm_minus_rand = 1.96 * (std_dev_material_diff / math.sqrt(total_games)) if total_games > 1 else 0

        per_game_wrong_actions_per_1000moves = [
            (log.player_black.wrong_actions / log.number_of_moves * 1000) for log in model_logs if log.number_of_moves > 0
        ]
        per_game_wrong_moves_per_1000moves = [
            (log.player_black.wrong_moves / log.number_of_moves * 1000) for log in model_logs if log.number_of_moves > 0
        ]
        per_game_mistakes_per_1000moves = [
            ((log.player_black.wrong_actions + log.player_black.wrong_moves) / log.number_of_moves * 1000)
            for log in model_logs
            if log.number_of_moves > 0
        ]

        wrong_actions_per_1000moves = mean(per_game_wrong_actions_per_1000moves) if per_game_wrong_actions_per_1000moves else 0
        wrong_moves_per_1000moves = mean(per_game_wrong_moves_per_1000moves) if per_game_wrong_moves_per_1000moves else 0
        mistakes_per_1000moves = mean(per_game_mistakes_per_1000moves) if per_game_mistakes_per_1000moves else 0

        std_dev_wrong_actions_per_1000moves = (
            stdev(per_game_wrong_actions_per_1000moves) if len(per_game_wrong_actions_per_1000moves) > 1 else 0
        )
        std_dev_wrong_moves_per_1000moves = stdev(per_game_wrong_moves_per_1000moves) if len(per_game_wrong_moves_per_1000moves) > 1 else 0
        std_dev_mistakes_per_1000moves = stdev(per_game_mistakes_per_1000moves) if len(per_game_mistakes_per_1000moves) > 1 else 0

        if total_games > 1:
            z_score = 1.96
            sample_size = total_games
            # Only emit moe_mistakes_per_1000moves in refined; compute others locally if needed
            _moe_wrong_actions_per_1000moves = z_score * (std_dev_wrong_actions_per_1000moves / math.sqrt(sample_size))
            _moe_wrong_moves_per_1000moves = z_score * (std_dev_wrong_moves_per_1000moves / math.sqrt(sample_size))
            moe_mistakes_per_1000moves = z_score * (std_dev_mistakes_per_1000moves / math.sqrt(sample_size))
            per_game_moves = [log.number_of_moves for log in model_logs]
            std_dev_moves = stdev(per_game_moves)
            moe_avg_moves = z_score * (std_dev_moves / math.sqrt(sample_size))
        else:
            moe_mistakes_per_1000moves = 0
            moe_avg_moves = 0

        completion_tokens_black = sum(log.usage_stats_black.completion_tokens for log in model_logs)
        completion_tokens_black_per_move = (completion_tokens_black / llm_total_moves) if llm_total_moves > 0 else 0
        per_game_completion_tokens_black_per_move = [
            (log.usage_stats_black.completion_tokens / log.number_of_moves) for log in model_logs if log.number_of_moves > 0
        ]
        std_dev_completion_tokens_black_per_move = (
            stdev(per_game_completion_tokens_black_per_move) if len(per_game_completion_tokens_black_per_move) > 1 else 0
        )
        moe_completion_tokens_black_per_move = (
            (1.96 * (std_dev_completion_tokens_black_per_move / math.sqrt(total_games))) if total_games > 1 else 0
        )

        # pricing
        prompt_price = 0.0
        completion_price = 0.0
        if model_name in model_prices:
            prompt_price, completion_price = model_prices[model_name]
        else:
            matching_models = [m for m in model_prices if m in model_name or model_name in m]
            if matching_models:
                closest_match = max(matching_models, key=len)
                prompt_price, completion_price = model_prices[closest_match]

        per_game_costs: list[float] = []
        per_game_price_per_1000_moves: list[float] = []
        for log in model_logs:
            prompt_tokens = log.usage_stats_black.prompt_tokens
            completion_tokens = log.usage_stats_black.completion_tokens
            prompt_cost = prompt_tokens * (prompt_price / 1_000_000)
            completion_cost = completion_tokens * (completion_price / 1_000_000)
            game_cost = prompt_cost + completion_cost
            per_game_costs.append(game_cost)
            moves = log.number_of_moves
            per_game_price_per_1000_moves.append((game_cost / moves * 1000) if moves > 0 else 0)

        average_game_cost = mean(per_game_costs) if per_game_costs else 0
        std_dev_game_cost = stdev(per_game_costs) if len(per_game_costs) > 1 else 0
        moe_average_game_cost = (1.96 * (std_dev_game_cost / math.sqrt(total_games))) if total_games > 1 else 0
        average_price_per_1000_moves = mean(per_game_price_per_1000_moves) if per_game_price_per_1000_moves else 0
        std_dev_price_per_1000_moves = stdev(per_game_price_per_1000_moves) if len(per_game_price_per_1000_moves) > 1 else 0
        moe_price_per_1000_moves = 1.96 * (std_dev_price_per_1000_moves / math.sqrt(total_games)) if total_games > 1 else 0
        price_per_1000_moves = average_price_per_1000_moves

        per_game_time_seconds = [
            float(log.player_black.accumulated_reply_time_seconds)
            for log in model_logs
            if isinstance(log.player_black.accumulated_reply_time_seconds, (int, float))
            and log.player_black.accumulated_reply_time_seconds > 0
        ]
        if per_game_time_seconds:
            average_time_per_game_seconds = mean(per_game_time_seconds)
            std_dev_time_per_game_seconds = stdev(per_game_time_seconds) if len(per_game_time_seconds) > 1 else 0
            moe_average_time_per_game_seconds = (
                1.96 * (std_dev_time_per_game_seconds / math.sqrt(len(per_game_time_seconds))) if len(per_game_time_seconds) > 1 else 0
            )
        else:
            average_time_per_game_seconds = 0.0
            moe_average_time_per_game_seconds = 0.0

        row = {
            "Player": model_name,
            "total_games": total_games,
            "player_wins": black_llm_wins,
            "opponent_wins": opponent_wins,
            "draws": draws,
            "player_wins_percent": round(player_wins_percent, 3),
            "player_draws_percent": round(player_draws_percent, 3),
            "average_moves": round((llm_total_moves / total_games), 3) if total_games else 0,
            "moe_average_moves": round(moe_avg_moves, 3),
            "total_moves": llm_total_moves,
            "player_wrong_actions": llm_wrong_actions,
            "player_wrong_moves": llm_wrong_moves,
            "wrong_actions_per_1000moves": round(wrong_actions_per_1000moves, 3),
            "wrong_moves_per_1000moves": round(wrong_moves_per_1000moves, 3),
            "mistakes_per_1000moves": round(mistakes_per_1000moves, 3),
            "moe_mistakes_per_1000moves": round(moe_mistakes_per_1000moves, 3),
            "player_avg_material": round(llm_avg_material, 3),
            "opponent_avg_material": round(rand_avg_material, 3),
            "material_diff_player_llm_minus_opponent": round(material_diff_llm_minus_rand, 3),
            "moe_material_diff_llm_minus_rand": round(moe_material_diff_llm_minus_rand, 3),
            "completion_tokens_black_per_move": round(completion_tokens_black_per_move, 3),
            "moe_completion_tokens_black_per_move": round(moe_completion_tokens_black_per_move, 3),
            "moe_black_llm_win_rate": round(
                (1.96 * math.sqrt(((black_llm_wins / total_games) * (1 - (black_llm_wins / total_games))) / total_games))
                if total_games > 1
                else 0,
                3,
            )
            if total_games
            else 0,
            "moe_draw_rate": round(
                (1.96 * math.sqrt(((draws / total_games) * (1 - (draws / total_games))) / total_games)) if total_games > 1 else 0, 3
            )
            if total_games
            else 0,
            "moe_black_llm_loss_rate": round(
                (1.96 * math.sqrt(((opponent_wins / total_games) * (1 - (opponent_wins / total_games))) / total_games))
                if total_games > 1
                else 0,
                3,
            )
            if total_games
            else 0,
            "win_loss": round(win_loss, 3),
            "moe_win_loss": round(moe_win_loss, 3),
            "win_loss_non_interrupted": round(win_loss_non_interrupted, 3),
            "moe_win_loss_non_interrupted": round(moe_win_loss_non_interrupted, 3),
            "game_duration": round(game_duration, 3),
            "moe_game_duration": round(moe_game_duration, 3),
            "games_interrupted": games_interrupted,
            "games_interrupted_percent": round(games_interrupted_percent, 3),
            "moe_games_interrupted": round(moe_games_interrupted, 3),
            "games_not_interrupted": games_not_interrupted,
            "games_not_interrupted_percent": round(games_not_interrupted_percent, 3),
            "moe_games_not_interrupted": round(moe_games_not_interrupted, 3),
            "average_game_cost": round(average_game_cost, 5),
            "moe_average_game_cost": round(moe_average_game_cost, 5),
            "price_per_1000_moves": round(price_per_1000_moves, 5),
            "moe_price_per_1000_moves": round(moe_price_per_1000_moves, 5),
            "average_time_per_game_seconds": round(average_time_per_game_seconds, 3),
            "moe_average_time_per_game_seconds": round(moe_average_time_per_game_seconds, 3),
        }
        if INCLUDE_ABNORMAL_FINISH_STATS:
            row["abnormal_finishes_total"] = abnormal_total
            row["abnormal_finishes_percent"] = row_abnormal_percent
            for slug, count in abnormal_counts.items():
                row[f"abnormal_{slug}_count"] = count
                row[f"abnormal_{slug}_percent"] = round((count / total_games) * 100, 3) if total_games > 0 else 0
        if mode == GameMode.DRAGON_VS_LLM:
            row["white_opponent"] = opponent_label
        refined_rows.append(row)

    return refined_rows


# Unified refined CSV headers used across functions
BASE_REFINED_HEADERS = [
    "Player",
    "total_games",
    "player_wins",
    "opponent_wins",
    "draws",
    "player_wins_percent",
    "player_draws_percent",
    "average_moves",
    "moe_average_moves",
    "total_moves",
    "player_wrong_actions",
    "player_wrong_moves",
    "wrong_actions_per_1000moves",
    "wrong_moves_per_1000moves",
    "mistakes_per_1000moves",
    "moe_mistakes_per_1000moves",
    "player_avg_material",
    "opponent_avg_material",
    "material_diff_player_llm_minus_opponent",
    "moe_material_diff_llm_minus_rand",
    "completion_tokens_black_per_move",
    "moe_completion_tokens_black_per_move",
    "moe_black_llm_win_rate",
    "moe_draw_rate",
    "moe_black_llm_loss_rate",
    "win_loss",
    "moe_win_loss",
    "win_loss_non_interrupted",
    "moe_win_loss_non_interrupted",
    "game_duration",
    "moe_game_duration",
    "games_interrupted",
    "games_interrupted_percent",
    "moe_games_interrupted",
    "games_not_interrupted",
    "games_not_interrupted_percent",
    "moe_games_not_interrupted",
    "average_game_cost",
    "moe_average_game_cost",
    "price_per_1000_moves",
    "moe_price_per_1000_moves",
    "average_time_per_game_seconds",
    "moe_average_time_per_game_seconds",
]
REFINED_HEADERS = BASE_REFINED_HEADERS + ABNORMAL_FINISH_HEADERS if INCLUDE_ABNORMAL_FINISH_STATS else BASE_REFINED_HEADERS.copy()

# Dragon-vs-LLM refined CSV headers (adds white_opponent field)
DRAGON_REFINED_HEADERS = REFINED_HEADERS + [
    "white_opponent",
]


# Elo-refined headers (union metrics + Elo & per-opponent game breakdown)
ELO_REFINED_HEADERS = REFINED_HEADERS + [
    "elo",
    "elo_moe_95",
    "games_vs_random",
    "games_vs_dragon",
]


def collapse_refined_rows_by_player(rows):
    """Collapse duplicate Player rows by merging counts and weighted averages.

    - Sums integer count fields (games, moves, wins, losses, draws, wrong actions/moves, interrupts)
    - Weighted-average by games for per-game means (e.g., game_duration, average_game_cost)
    - Weighted-average by moves for per-move means (completion_tokens_black_per_move)
    - Weighted-average by non-interrupted games for win_loss_non_interrupted
    - Recomputes derived percentages and ratios from merged totals
    - Uses conservative max for all MOE fields
    """

    def to_int(value):
        try:
            # Some inputs may already be int/float
            return int(float(value))
        except (TypeError, ValueError):
            return 0

    def to_float(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def weighted_mean(a, aw, b, bw):
        total_w = aw + bw
        if total_w <= 0:
            return 0.0
        return (a * aw + b * bw) / total_w

    grouped = {}
    for row in rows:
        player = row.get("Player")
        if not player:
            # Skip rows without Player name
            continue
        # Keep dragon-vs-LLM rows separated by opponent label
        opponent_label = row.get("white_opponent", "")
        group_key = (player, opponent_label)
        if group_key not in grouped:
            grouped[group_key] = dict(row)
            continue

        g = grouped[group_key]

        # Preserve previous weights before updating totals
        tg_prev = to_int(g.get("total_games"))
        tm_prev = to_int(g.get("total_moves"))
        gni_prev = to_int(g.get("games_not_interrupted"))

        tg_new = to_int(row.get("total_games"))
        tm_new = to_int(row.get("total_moves"))
        gni_new = to_int(row.get("games_not_interrupted"))

        # Sum integer count fields
        count_fields = [
            "total_games",
            "player_wins",
            "opponent_wins",
            "draws",
            "total_moves",
            "player_wrong_actions",
            "player_wrong_moves",
            "games_interrupted",
            "games_not_interrupted",
        ]
        if INCLUDE_ABNORMAL_FINISH_STATS:
            count_fields.append("abnormal_finishes_total")
            count_fields.extend([f"abnormal_{slug}_count" for slug in ABNORMAL_TERMINATION_REASONS])
        for key in count_fields:
            g[key] = to_int(g.get(key)) + to_int(row.get(key))

        # Weighted by games
        for key in [
            "player_avg_material",
            "opponent_avg_material",
            "game_duration",
            "average_game_cost",
            "price_per_1000_moves",
            "average_time_per_game_seconds",
        ]:
            g[key] = weighted_mean(to_float(g.get(key)), tg_prev, to_float(row.get(key)), tg_new)

        # Weighted by moves
        for key in [
            "completion_tokens_black_per_move",
        ]:
            g[key] = weighted_mean(to_float(g.get(key)), tm_prev, to_float(row.get(key)), tm_new)

        # Weighted by non-interrupted games
        g["win_loss_non_interrupted"] = weighted_mean(
            to_float(g.get("win_loss_non_interrupted")),
            gni_prev,
            to_float(row.get("win_loss_non_interrupted")),
            gni_new,
        )

        # Conservative merge for MOE fields: take the max
        for key in [
            "moe_average_moves",
            "moe_material_diff_llm_minus_rand",
            "moe_mistakes_per_1000moves",
            "moe_completion_tokens_black_per_move",
            "moe_black_llm_win_rate",
            "moe_draw_rate",
            "moe_black_llm_loss_rate",
            "moe_win_loss",
            "moe_win_loss_non_interrupted",
            "moe_game_duration",
            "moe_average_game_cost",
            "moe_price_per_1000_moves",
            "moe_average_time_per_game_seconds",
        ]:
            g[key] = max(to_float(g.get(key)), to_float(row.get(key)))

    # Recompute derived metrics from merged totals
    out = []
    for (player, _opponent_label), g in grouped.items():
        tg = to_int(g.get("total_games"))
        tm = to_int(g.get("total_moves"))
        wins = to_int(g.get("player_wins"))
        losses = to_int(g.get("opponent_wins"))
        draws = to_int(g.get("draws"))
        wa = to_int(g.get("player_wrong_actions"))
        wm = to_int(g.get("player_wrong_moves"))
        gi = to_int(g.get("games_interrupted"))
        gni = to_int(g.get("games_not_interrupted"))

        g["Player"] = player
        g["player_wins_percent"] = round((wins / tg) * 100, 3) if tg else 0
        g["player_draws_percent"] = round((draws / tg) * 100, 3) if tg else 0
        g["average_moves"] = round((tm / tg), 3) if tg else 0
        g["wrong_actions_per_1000moves"] = round((wa / tm) * 1000, 3) if tm else 0
        g["wrong_moves_per_1000moves"] = round((wm / tm) * 1000, 3) if tm else 0
        g["mistakes_per_1000moves"] = round(((wa + wm) / tm) * 1000, 3) if tm else 0
        g["material_diff_player_llm_minus_opponent"] = round(
            to_float(g.get("player_avg_material")) - to_float(g.get("opponent_avg_material")),
            3,
        )
        # Normalize win_loss back to [0,1]
        g["win_loss"] = round((((wins - losses) / tg) / 2 + 0.5), 3) if tg else 0.5
        # Keep percents in 0–100
        g["games_interrupted_percent"] = round(((gi / tg) * 100), 3) if tg else 0
        g["games_not_interrupted_percent"] = round(((gni / tg) * 100), 3) if tg else 0
        if INCLUDE_ABNORMAL_FINISH_STATS:
            abnormal_total = to_int(g.get("abnormal_finishes_total"))
            g["abnormal_finishes_percent"] = round(((abnormal_total / tg) * 100), 3) if tg else 0
            for slug in ABNORMAL_TERMINATION_REASONS:
                count = to_int(g.get(f"abnormal_{slug}_count"))
                g[f"abnormal_{slug}_percent"] = round(((count / tg) * 100), 3) if tg else 0

        # Zero tokens and price metrics for selected canonical IDs after alias merge
        if player in ZERO_TOKENS:
            g["completion_tokens_black_per_move"] = 0.0
            g["moe_completion_tokens_black_per_move"] = 0.0
            g["average_game_cost"] = 0.0
            g["moe_average_game_cost"] = 0.0
            g["price_per_1000_moves"] = 0.0
            g["moe_price_per_1000_moves"] = 0.0

        out.append(g)

    return out


def write_refined_csv(rows, output_file):
    with open(output_file, "w", newline="", encoding="utf-8") as f_out:
        # Choose headers based on presence of white_opponent in rows
        has_opponent = any("white_opponent" in r for r in rows)
        headers = DRAGON_REFINED_HEADERS if has_opponent else REFINED_HEADERS
        writer = csv.DictWriter(f_out, fieldnames=headers)
        writer.writeheader()
        for r in rows:
            # Normalize: ensure all headers present
            out_row = {k: r.get(k, "0") for k in headers}
            out_row["Player"] = r.get("Player", "")
            writer.writerow(out_row)


def write_elo_refined_csv(rows, output_file):
    with open(output_file, "w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=ELO_REFINED_HEADERS)
        writer.writeheader()
        for r in rows:
            out_row = {k: r.get(k, "0") for k in ELO_REFINED_HEADERS}
            out_row["Player"] = r.get("Player", "")
            writer.writerow(out_row)


# --------------------- Elo helpers ---------------------


def lvl_to_elo(level: int) -> float:
    try:
        return float((level + 1) * 125)
    except Exception:
        return float("nan")


def _expected_score(R: float, opp_elos: List[float]) -> List[float]:
    # E = 1 / (1 + 10^((R_opp - R)/400))
    es: List[float] = []
    for opp in opp_elos:
        es.append(1.0 / (1.0 + 10.0 ** ((opp - R) / 400.0)))
    return es


def estimate_elo_from_blocks(
    blocks: List[Tuple[float, int, int, int]], white_advantage: float = ELO_WHITE_ADVANTAGE
) -> Tuple[float, float]:
    """
    Estimate Elo from aggregated blocks where the model is always Black.

    blocks: list of (opponent_elo, wins, draws, losses)
    white_advantage: Elo points to add after solving the Black-only MLE.

    Returns: (R_true, se_true) — where R_true includes white_advantage.
    """
    if not blocks:
        return float("nan"), float("nan")

    opp_elos: List[float] = []
    Ns: List[int] = []
    Ss: List[float] = []
    for opp_elo, wins, draws, losses in blocks:
        N = int(wins) + int(draws) + int(losses)
        if N <= 0 or not isinstance(opp_elo, (int, float)):
            continue
        S = (int(wins) + 0.5 * int(draws)) / N
        opp_elos.append(float(opp_elo))
        Ns.append(N)
        Ss.append(S)

    if not opp_elos:
        return float("nan"), float("nan")

    # Define f(R) = Σ N_k (S_k - E_k(R))
    def f(R: float) -> float:
        total = 0.0
        for opp, N, S in zip(opp_elos, Ns, Ss):
            E = 1.0 / (1.0 + 10.0 ** ((opp - R) / 400.0))
            total += N * (S - E)
        return total

    # Bracket the root around the opponent Elo range
    a = min(opp_elos) - 800.0
    b = max(opp_elos) + 800.0
    fa = f(a)
    fb = f(b)
    if fa * fb > 0:
        width = 800.0
        for _ in range(6):
            a -= width
            b += width
            fa = f(a)
            fb = f(b)
            if fa * fb <= 0:
                break
            width *= 2.0
    if fa * fb > 0:
        return float("nan"), float("nan")

    root = root_scalar(f, bracket=(a, b), method="brentq").root

    # Fisher information at root
    info = 0.0
    for opp, N in zip(opp_elos, Ns):
        E = 1.0 / (1.0 + 10.0 ** ((opp - root) / 400.0))
        info += N * E * (1.0 - E)
    info *= (math.log(10.0) / 400.0) ** 2
    se_black = (1.0 / math.sqrt(info)) if info > 0 else float("nan")

    R_true = root + white_advantage
    return float(R_true), float(se_black)


def _parse_dragon_level(opponent_label: str) -> int | None:
    try:
        import re

        m = re.search(r"dragon-lvl-(\d+)", (opponent_label or "").lower())
        if m:
            return int(m.group(1))
        m2 = re.search(r"lvl-(\d+)", (opponent_label or "").lower())
        if m2:
            return int(m2.group(1))
        return None
    except Exception:
        return None


def _calibrate_random_elo_from_misc(dirs: List[str]) -> Tuple[float, float, int]:
    """
    Scan aggregate JSONs under misc/dragon to calibrate Random vs Dragon levels.
    Returns (R_random, se_random, total_games). If not found, returns (nan, nan, 0).
    """
    pattern = r"^random.*_vs_dragon-lvl-(\d+)\.json$"
    import re

    records: List[Tuple[float, int, int, int]] = []

    for base in dirs:
        if not os.path.isdir(base):
            continue
        for root, _dirs, files in os.walk(base):
            for fn in files:
                if not fn.endswith(".json"):
                    continue
                m = re.match(pattern, fn)
                if not m:
                    continue
                try:
                    lvl = int(m.group(1))
                except Exception:
                    continue
                opp_elo = lvl_to_elo(lvl)
                try:
                    with open(os.path.join(root, fn), "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    continue
                # In these aggregates, the calibrated player (Random) is White.
                white_wins = int(data.get("white_wins", 0))
                draws = int(data.get("draws", 0))
                black_wins = int(data.get("black_wins", 0))
                N = white_wins + draws + black_wins
                if N <= 0:
                    continue
                records.append((opp_elo, white_wins, draws, black_wins))

    if not records:
        return float("nan"), float("nan"), 0

    # Random is White in these logs; adjust post-solve by -γ
    # Implement a variant that just flips color by using negative white advantage
    R_true, se = estimate_elo_from_blocks(records, white_advantage=-ELO_WHITE_ADVANTAGE)
    total_games = sum(w + d + losses for _opp, w, d, losses in records)
    return R_true, se, total_games


def print_leaderboard(csv_file, top_n=None):
    """Print a formatted leaderboard to the console with the same metrics as the web version."""
    rows = []

    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        data = list(reader)

    # Sorting
    has_opponent = any("white_opponent" in r for r in data)
    if has_opponent:
        # Opponent-level ASC, then Win Rate DESC, then Win/Loss DESC
        import re

        def parse_level(op):
            if not op:
                return 999
            m = re.search(r"dragon-lvl-(\d+)", op.lower()) or re.search(r"lvl-(\d+)", op.lower())
            try:
                return int(m.group(1)) if m else 999
            except Exception:
                return 999

        def sf(v):
            try:
                return float(v)
            except (TypeError, ValueError):
                return 0.0

        sorted_data = sorted(
            data,
            key=lambda x: (
                parse_level(x.get("white_opponent", "")),
                -sf(x.get("player_wins_percent", 0)),
                -sf(x.get("win_loss", 0)),
            ),
        )
    else:
        # Default: Win/Loss DESC, then Game Duration DESC, then Tokens ASC
        sorted_data = sorted(
            data, key=lambda x: (-float(x["win_loss"]), -float(x["game_duration"]), float(x["completion_tokens_black_per_move"]))
        )

    # Limit to top N if specified
    if top_n:
        sorted_data = sorted_data[:top_n]

    # Prepare data for tabulate
    total_cost_all_models = 0.0
    for rank, row in enumerate(sorted_data, 1):
        player_name = row["Player"]
        white_op = row.get("white_opponent", "")

        # Format the metrics like in the web version
        win_loss = f"{float(row['win_loss']) * 100:.2f}%"
        game_duration = f"{float(row['game_duration']) * 100:.2f}%"
        tokens = float(row["completion_tokens_black_per_move"])
        tokens_str = f"{tokens:.1f}" if tokens > 1000 else f"{tokens:.2f}"

        # Format the cost with margin of error
        cost = float(row["average_game_cost"])
        moe = float(row["moe_average_game_cost"])
        cost_str = f"${cost:.4f}±{moe:.4f}"

        # Calculate total cost per model
        total_games = int(row["total_games"])
        total_cost = cost * total_games
        total_cost_str = f"${total_cost:.2f}"
        total_cost_all_models += total_cost

        # Prefer measured average time per game if available; otherwise N/A
        try:
            measured_time = float(row.get("average_time_per_game_seconds", 0) or 0)
        except (ValueError, TypeError):
            measured_time = 0.0
        if measured_time > 0:
            if measured_time < 60:
                time_str = f"{measured_time:.1f}s"
            elif measured_time < 3600:
                time_str = f"{measured_time / 60:.1f}m"
            else:
                time_str = f"{measured_time / 3600:.2f}h"
        else:
            time_str = "N/A"

        # Win Rate column (player_wins_percent)
        try:
            win_rate_col = f"{float(row.get('player_wins_percent', 0)):.2f}%"
        except (ValueError, TypeError):
            win_rate_col = "0.00%"

        # Include opponent column if present
        if white_op:
            rows.append(
                [
                    rank,
                    player_name,
                    white_op,
                    win_rate_col,
                    win_loss,
                    game_duration,
                    tokens_str,
                    cost_str,
                    time_str,
                    total_games,
                    total_cost_str,
                ]
            )
        else:
            rows.append(
                [rank, player_name, win_rate_col, win_loss, game_duration, tokens_str, cost_str, time_str, total_games, total_cost_str]
            )

    # Print the table with headers
    headers = (
        ["#", "Player", "Opponent", "Win Rate", "Win/Loss", "Game Duration", "Tokens", "Cost/Game", "Time/Game", "Games", "Total Cost"]
        if has_opponent
        else ["#", "Player", "Win Rate", "Win/Loss", "Game Duration", "Tokens", "Cost/Game", "Time/Game", "Games", "Total Cost"]
    )
    print(tabulate(rows, headers=headers, tablefmt="grid"))
    print(f"\nTotal cost across all models: ${total_cost_all_models:.2f}")


def print_elo_leaderboard(csv_file, top_n=None):
    """Print a leaderboard for Elo-refined CSV, with Elo as the first column.

    Sorting: Elo DESC (non-NaN first), then Player ASC. Models without Elo go last.
    Columns mirror the non-opponent leaderboard with Elo prepended.
    """
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        data = list(reader)

    def sf(v, default=0.0):
        try:
            return float(v)
        except (TypeError, ValueError):
            return float(default)

    # Split into non-NaN Elo and NaN Elo
    with_elo = [r for r in data if r.get("elo") not in (None, "", "nan")]
    without_elo = [r for r in data if r.get("elo") in (None, "", "nan")]

    # Sort
    def sort_key_with_elo(r):
        elo = sf(r.get("elo"))
        win_rate = sf(r.get("player_wins_percent"))  # percent
        win_loss = sf(r.get("win_loss"))  # [0,1]
        # Sort DESC by elo, then win_rate, then win_loss
        return (-elo, -win_rate, -win_loss)

    def sort_key_without_elo(r):
        win_rate = sf(r.get("player_wins_percent"))
        win_loss = sf(r.get("win_loss"))
        return (-win_rate, -win_loss, (r.get("Player") or ""))

    with_elo_sorted = sorted(with_elo, key=sort_key_with_elo)
    without_elo_sorted = sorted(without_elo, key=sort_key_without_elo)

    sorted_data = with_elo_sorted + without_elo_sorted
    if top_n:
        sorted_data = sorted_data[:top_n]

    total_cost_all_models = 0.0
    table_rows = []
    for rank, row in enumerate(sorted_data, 1):
        player_name = row.get("Player", "")
        elo_str = row.get("elo") or ""
        elo_moe = row.get("elo_moe_95") or ""

        # Reuse formatting from non-opponent leaderboard
        try:
            win_loss = f"{float(row.get('win_loss', 0)) * 100:.2f}%"
        except (TypeError, ValueError):
            win_loss = "0.00%"
        try:
            game_duration = f"{float(row.get('game_duration', 0)) * 100:.2f}%"
        except (TypeError, ValueError):
            game_duration = "0.00%"

        tokens = sf(row.get("completion_tokens_black_per_move"))
        tokens_str = f"{tokens:.1f}" if tokens > 1000 else f"{tokens:.2f}"

        cost = sf(row.get("average_game_cost"))
        moe = sf(row.get("moe_average_game_cost"))
        cost_str = f"${cost:.4f}±{moe:.4f}"

        total_games = int(sf(row.get("total_games"), 0))
        total_cost = cost * total_games
        total_cost_all_models += total_cost
        total_cost_str = f"${total_cost:.2f}"

        try:
            games_vs_random = int(sf(row.get("games_vs_random"), 0))
        except (ValueError, TypeError):
            games_vs_random = 0

        try:
            measured_time = float(row.get("average_time_per_game_seconds", 0) or 0)
        except (TypeError, ValueError):
            measured_time = 0.0
        if measured_time > 0:
            if measured_time < 60:
                time_str = f"{measured_time:.1f}s"
            elif measured_time < 3600:
                time_str = f"{measured_time / 60:.1f}m"
            else:
                time_str = f"{measured_time / 3600:.2f}h"
        else:
            time_str = "N/A"

        # Win Rate column (player_wins_percent)
        try:
            win_rate_col = f"{float(row.get('player_wins_percent', 0)):.2f}%"
        except (TypeError, ValueError):
            win_rate_col = "0.00%"

        elo_display = elo_str if not elo_moe else f"{elo_str}±{elo_moe}"
        table_rows.append(
            [
                rank,
                player_name,
                elo_display,
                win_rate_col,
                win_loss,
                game_duration,
                tokens_str,
                cost_str,
                time_str,
                total_games,
                games_vs_random,
                total_cost_str,
            ]
        )

    headers = [
        "#",
        "Player",
        "Elo",
        "Win Rate",
        "Win/Loss",
        "Game Duration",
        "Tokens",
        "Cost/Game",
        "Time/Game",
        "Games",
        "Games vs Random",
        "Total Cost",
    ]
    print(tabulate(table_rows, headers=headers, tablefmt="grid"))
    print(f"\nTotal cost across all models: ${total_cost_all_models:.2f}")


def main():
    if GAME_MODE == GameMode.DRAGON_VS_LLM:
        print(f"Building DRAGON_VS_LLM refined rows from: {ENGINE_LOGS_DIRS_NEW + ENGINE_LOGS_DIRS_LEGACY}")
        logs_dirs = ENGINE_LOGS_DIRS_NEW + ENGINE_LOGS_DIRS_LEGACY
        new_rows = build_refined_rows_from_logs(
            logs_dirs,
            model_overrides=MODEL_OVERRIDES,
            only_after_date=DATE_AFTER,
            filter_out_below_n=FILTER_OUT_BELOW_N_MISC,
            filter_out_models=FILTER_OUT_MODELS,
            model_aliases=ALIASES,
            models_metadata_csv=MODELS_METADATA_CSV,
            mode=GameMode.DRAGON_VS_LLM,
        )
        # Collapse duplicates while preserving opponent separation
        new_rows = collapse_refined_rows_by_player(new_rows)
        output_csv = os.path.join(OUTPUT_DIR, "dragon_refined.csv")
        write_refined_csv(new_rows, output_csv)
        print(f"Wrote dragon refined CSV: {output_csv}")

        print("\n=== DRAGON vs LLM LEADERBOARD ===\n")
        print_leaderboard(output_csv)
    elif GAME_MODE == GameMode.ELO:
        print("Building ELO-refined rows (combining Random and Dragon logs)")

        # 0) Calibrate Random Elo vs Dragon
        random_elo, random_se, random_n = _calibrate_random_elo_from_misc(MISC_DRAGON_DIRS)
        if not isinstance(random_elo, float) or math.isnan(random_elo):
            print("WARNING: Could not calibrate Random Elo from misc/dragon; random-only models will not get Elo.")
        else:
            print(f"Calibrated Random Elo: {random_elo:.1f} ± {1.96 * random_se:.1f} (n={random_n})")

        # 1) Load and aggregate rows from Random-vs-LLM (Black is LLM)
        rows_random = build_refined_rows_from_logs(
            LOGS_DIRS,
            model_overrides=MODEL_OVERRIDES,
            only_after_date=DATE_AFTER,
            filter_out_below_n=FILTER_OUT_BELOW_N_RANDOM,
            filter_out_models=FILTER_OUT_MODELS,
            model_aliases=ALIASES,
            models_metadata_csv=MODELS_METADATA_CSV,
            mode=GameMode.RANDOM_VS_LLM,
        )

        # 2) Load and aggregate rows from Dragon-vs-LLM (per opponent)
        rows_dragon = build_refined_rows_from_logs(
            ENGINE_LOGS_DIRS_NEW + ENGINE_LOGS_DIRS_LEGACY,
            model_overrides=MODEL_OVERRIDES,
            only_after_date=DATE_AFTER,
            filter_out_below_n=FILTER_OUT_BELOW_N_MISC,
            filter_out_models=FILTER_OUT_MODELS,
            model_aliases=ALIASES,
            models_metadata_csv=MODELS_METADATA_CSV,
            mode=GameMode.DRAGON_VS_LLM,
        )
        # Ensure per-(player, opponent) collapse inside Dragon mode
        rows_dragon = collapse_refined_rows_by_player(rows_dragon)

        # 3) Compute breakdown counts per player
        games_vs_random: Dict[str, int] = {}
        blocks_random_by_player: Dict[str, Tuple[int, int, int]] = {}
        for r in rows_random:
            name = r.get("Player")
            if not name:
                continue
            total = int(float(r.get("total_games", 0) or 0))
            games_vs_random[name] = games_vs_random.get(name, 0) + total
            wins = int(float(r.get("player_wins", 0) or 0))
            draws = int(float(r.get("draws", 0) or 0))
            losses = int(float(r.get("opponent_wins", 0) or 0))
            blocks_random_by_player[name] = (
                blocks_random_by_player.get(name, (0, 0, 0))[0] + wins,
                blocks_random_by_player.get(name, (0, 0, 0))[1] + draws,
                blocks_random_by_player.get(name, (0, 0, 0))[2] + losses,
            )

        games_vs_dragon: Dict[str, int] = {}
        blocks_dragon_by_player: Dict[str, List[Tuple[float, int, int, int]]] = {}
        for r in rows_dragon:
            name = r.get("Player")
            if not name:
                continue
            lvl = _parse_dragon_level(r.get("white_opponent", ""))
            if lvl is None:
                continue
            opp_elo = lvl_to_elo(lvl)
            wins = int(float(r.get("player_wins", 0) or 0))
            draws = int(float(r.get("draws", 0) or 0))
            losses = int(float(r.get("opponent_wins", 0) or 0))
            total = wins + draws + losses
            games_vs_dragon[name] = games_vs_dragon.get(name, 0) + total
            blocks_dragon_by_player.setdefault(name, []).append((opp_elo, wins, draws, losses))

        # 4) Build combined metrics rows by merging Random and Dragon rows
        # Force Dragon rows to have empty opponent label for union collapse
        dragon_rows_union = []
        for r in rows_dragon:
            rc = dict(r)
            rc["white_opponent"] = ""
            dragon_rows_union.append(rc)
        combined_rows = collapse_refined_rows_by_player(rows_random + dragon_rows_union)

        # 5) Compute Elo per model
        out_rows: List[Dict[str, Any]] = []
        for row in combined_rows:
            name = row.get("Player")
            if not name:
                continue

            # Choose blocks based on threshold policy
            dragon_blocks = blocks_dragon_by_player.get(name, [])
            total_dragon_games = games_vs_dragon.get(name, 0)

            use_dragon_only = False
            if ELO_DRAGON_ONLY_MIN_GAMES and total_dragon_games >= ELO_DRAGON_ONLY_MIN_GAMES:
                use_dragon_only = True

            blocks: List[Tuple[float, int, int, int]] = []
            if use_dragon_only:
                blocks = dragon_blocks
            else:
                blocks.extend(dragon_blocks)
                # Add random block if calibrated
                if isinstance(random_elo, float) and not math.isnan(random_elo):
                    rw, rd, rl = blocks_random_by_player.get(name, (0, 0, 0))
                    if (rw + rd + rl) > 0:
                        blocks.append((float(random_elo), int(rw), int(rd), int(rl)))

            R, se = estimate_elo_from_blocks(blocks, white_advantage=ELO_WHITE_ADVANTAGE)
            row["elo"] = f"{R:.3f}" if isinstance(R, float) and not math.isnan(R) else ""
            row["elo_moe_95"] = f"{(1.96 * se):.3f}" if isinstance(se, float) and not math.isnan(se) else ""
            row["games_vs_random"] = str(games_vs_random.get(name, 0))
            row["games_vs_dragon"] = str(games_vs_dragon.get(name, 0))
            out_rows.append(row)

        write_elo_refined_csv(out_rows, ELO_REFINED_CSV)
        print(f"Wrote ELO refined CSV: {ELO_REFINED_CSV}")
        print("\n=== ELO LEADERBOARD ===\n")
        print_elo_leaderboard(ELO_REFINED_CSV)
    else:
        print(f"Building refined rows directly from logs: {LOGS_DIRS}")
        new_rows = build_refined_rows_from_logs(
            LOGS_DIRS,
            model_overrides=MODEL_OVERRIDES,
            only_after_date=DATE_AFTER,
            filter_out_below_n=FILTER_OUT_BELOW_N_RANDOM,
            filter_out_models=FILTER_OUT_MODELS,
            model_aliases=ALIASES,
            models_metadata_csv=MODELS_METADATA_CSV,
            mode=GameMode.RANDOM_VS_LLM,
        )
        # Collapse duplicates (e.g., aliased models)
        new_rows = collapse_refined_rows_by_player(new_rows)
        print(f"Computed refined rows in memory: {len(new_rows)}")

        write_refined_csv(new_rows, REFINED_CSV)
        print(f"Wrote refined CSV: {REFINED_CSV}")

        # Leaderboard
        print("\n=== LLM CHESS LEADERBOARD ===\n")
        print_leaderboard(REFINED_CSV)
        print("\nMETRICS EXPLANATION:")
        print("- Win/Loss: Difference between wins and losses as a percentage (0-100%). Higher is better.")
        print(
            "- Game Duration: Percentage of maximum possible game length completed (0-100%). Higher indicates better instruction following."
        )
        print("- Tokens: Number of tokens generated per move. Shows model verbosity/efficiency.")
        print("- Cost/Game: Average cost per game with margin of error. Lower is more economical.")
        print("- Time/Game: Measured average time per game from logs; N/A if unavailable.")
        print("- Total Cost: Total cost across all games for this model.")


if __name__ == "__main__":
    main()
