"""
Convert aggregated chess game statistics
from a CSV file into a refined format used for Web publishing.
The refined format includes calculated
percentages and differences that are useful for analyzing player performance
over multiple games.

Usage:
    Set constants to path and run as script OR call build_refined_rows_from_logs()
"""

import os
import sys
import csv
import json
import math
from dataclasses import dataclass, field
from typing import ClassVar, Dict, Any, List, Union
from statistics import mean, stdev
from functools import lru_cache
from tabulate import tabulate  # Add this import for the print_leaderboard function
# Try direct import first
try:
    from llm_chess import TerminationReason
except ImportError:
    # Try relative import (for tests)
    try:
        from ..llm_chess import TerminationReason
    except ImportError:
        # Add project root to path (for direct script execution)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if project_root not in sys.path:
            sys.path.append(project_root)
        # Now try the direct import again
        from llm_chess import TerminationReason

# Define a list of log directories to process
# Restrict to rand_vs_llm per current requirement
LOGS_DIRS = [
    "_logs/rand_vs_llm",
]

FILTER_OUT_BELOW_N = 30 # 0
DATE_AFTER = None # "2025.04.01_00:00"

# Output files
OUTPUT_DIR = "data_processing"
REFINED_CSV = os.path.join(OUTPUT_DIR, "refined.csv")
# Historical refined CSV to ingest/merge
PREV_REFINED_CSV = os.path.join("_logs", "_pre_aug_2025", "refined.csv")

FILTER_OUT_MODELS = [
    "llama-4-scout-17b-16e-instruct",
    "ignore",  # models marked to be ignored via MODEL_OVERRIDES
]

ALIASES = {
    # "llama-4-scout-17b-16e-instruct": "llama-4-scout-cerebras"
}

# Metadata CSV for pricing
MODELS_METADATA_CSV = "data_processing/models_metadata.csv"

# Dictionary to override model names in the logs with more descriptive names, matches key as a substring in log file path
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
    suffix: list[str] = []
    if isinstance(reasoning_effort, str) and reasoning_effort:
        suffix.append(reasoning_effort)
    if isinstance(thinking_budget, int) and thinking_budget > 0:
        suffix.append(f"tb_{thinking_budget}")
    return f"{base_model}-{'-'.join(suffix)}" if suffix else base_model


@lru_cache(maxsize=4096)
def _model_label_from_run_json(run_dir: str) -> str | None:
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


def load_game_log(file_path: str) -> GameLog:
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        white_usage_keys = list(data["usage_stats"]["white"])
        black_usage_keys = list(data["usage_stats"]["black"])
        return GameLog(
            time_started=data["time_started"],
            winner=data["winner"],
            reason=data["reason"],
            number_of_moves=data["number_of_moves"],
            player_white=PlayerStats(**data["player_white"]),
            player_black=PlayerStats(**data["player_black"]),
            material_count=data["material_count"],
            usage_stats_white=UsageStats(
                total_cost=data["usage_stats"]["white"][white_usage_keys[0]],
                details=(data["usage_stats"]["white"].get(white_usage_keys[1], None) if len(white_usage_keys) > 1 else None),
            ),
            usage_stats_black=UsageStats(
                total_cost=data["usage_stats"]["black"][black_usage_keys[0]],
                details=(data["usage_stats"]["black"].get(black_usage_keys[1], None) if len(black_usage_keys) > 1 else None),
            ),
        )


def load_game_logs(logs_dirs: Union[str, List[Union[str, Dict[str, str]]]], model_overrides: dict | None = None) -> List[GameLog]:
    logs: list[GameLog] = []
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
                if (
                    file.endswith(".json")
                    and not file.endswith("_aggregate_results.json")
                    and file != "_run.json"
                ):
                    file_path = os.path.join(root, file)
                    try:
                        game_log = load_game_log(file_path)

                        # Ensure opponent and black roles are expected
                        if game_log.player_white.name != "Random_Player":
                            continue
                        if game_log.player_black.name != "Player_Black":
                            continue

                        if logs_dir in directory_aliases:
                            model_name = directory_aliases[logs_dir]
                        else:
                            run_dir = os.path.dirname(file_path)
                            label_from_run = _model_label_from_run_json(run_dir)
                            model_name = label_from_run or game_log.player_black.model
                            if model_overrides:
                                key = next((k for k in model_overrides if os.path.dirname(file_path).endswith(k)), None)
                                if key:
                                    model_name = model_overrides[key]

                        game_log.player_black.model = model_name
                        logs.append(game_log)
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
) -> list[dict[str, Any]]:
    if filter_out_models is None:
        filter_out_models = []
    if model_aliases is None:
        model_aliases = {}

    logs = load_game_logs(logs_dirs, model_overrides)
    if only_after_date:
        logs = [log for log in logs if log.time_started >= only_after_date]

    # Group by model name
    model_groups: dict[str, list[GameLog]] = {}
    for log in logs:
        model_name = log.player_black.model
        model_name = model_aliases.get(model_name, model_name)
        if model_name in filter_out_models:
            continue
        model_groups.setdefault(model_name, []).append(log)

    model_prices = load_model_prices(models_metadata_csv)

    refined_rows: list[dict[str, Any]] = []
    for model_name, model_logs in model_groups.items():
        total_games = len(model_logs)
        if total_games < filter_out_below_n:
            continue

        black_llm_wins = sum(1 for log in model_logs if log.winner in ("Player_Black", "NoN_Synthesizer"))
        white_rand_wins = sum(1 for log in model_logs if log.winner == "Random_Player")
        draws = total_games - black_llm_wins - white_rand_wins

        player_wins_percent = (black_llm_wins / total_games) * 100 if total_games > 0 else 0
        player_draws_percent = (draws / total_games) * 100 if total_games > 0 else 0

        # Normalized win_loss in [0,1]
        win_loss = (((black_llm_wins - white_rand_wins) / total_games) / 2 + 0.5) if total_games > 0 else 0.5
        per_game_win_loss = [
            (1 / 2 + 0.5) if log.winner in ("Player_Black", "NoN_Synthesizer") else (-1 / 2 + 0.5) if log.winner == "Random_Player" else 0.5
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

        # win_loss excluding interrupted games
        non_interrupted_logs = [log for log in model_logs if not log.is_interrupted]
        non_interrupted_games = len(non_interrupted_logs)
        if non_interrupted_games > 0:
            black_llm_wins_ni = sum(1 for log in non_interrupted_logs if log.winner in ("Player_Black", "NoN_Synthesizer"))
            white_rand_wins_ni = sum(1 for log in non_interrupted_logs if log.winner == "Random_Player")
            win_loss_non_interrupted = ((black_llm_wins_ni - white_rand_wins_ni) / non_interrupted_games) / 2 + 0.5
            per_game_win_loss_ni = [
                (1 / 2 + 0.5) if log.winner in ("Player_Black", "NoN_Synthesizer") else (-1 / 2 + 0.5) if log.winner == "Random_Player" else 0.5
                for log in non_interrupted_logs
            ]
            std_dev_win_loss_non_interrupted = stdev(per_game_win_loss_ni) if non_interrupted_games > 1 else 0
            moe_win_loss_non_interrupted = 1.96 * (std_dev_win_loss_non_interrupted / math.sqrt(non_interrupted_games)) if non_interrupted_games > 1 else 0
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
            ((log.player_black.wrong_actions + log.player_black.wrong_moves) / log.number_of_moves * 1000) for log in model_logs if log.number_of_moves > 0
        ]

        wrong_actions_per_1000moves = mean(per_game_wrong_actions_per_1000moves) if per_game_wrong_actions_per_1000moves else 0
        wrong_moves_per_1000moves = mean(per_game_wrong_moves_per_1000moves) if per_game_wrong_moves_per_1000moves else 0
        mistakes_per_1000moves = mean(per_game_mistakes_per_1000moves) if per_game_mistakes_per_1000moves else 0

        std_dev_wrong_actions_per_1000moves = stdev(per_game_wrong_actions_per_1000moves) if len(per_game_wrong_actions_per_1000moves) > 1 else 0
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

        completion_tokens_black = sum((log.usage_stats_black.details.get("completion_tokens", 0) if log.usage_stats_black.details else 0) for log in model_logs)
        completion_tokens_black_per_move = (completion_tokens_black / llm_total_moves) if llm_total_moves > 0 else 0
        per_game_completion_tokens_black_per_move = [
            ((log.usage_stats_black.details.get("completion_tokens", 0) if log.usage_stats_black.details else 0) / log.number_of_moves)
            for log in model_logs if log.number_of_moves > 0
        ]
        std_dev_completion_tokens_black_per_move = stdev(per_game_completion_tokens_black_per_move) if len(per_game_completion_tokens_black_per_move) > 1 else 0
        moe_completion_tokens_black_per_move = (1.96 * (std_dev_completion_tokens_black_per_move / math.sqrt(total_games))) if total_games > 1 else 0

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
            prompt_tokens = (log.usage_stats_black.details.get("prompt_tokens", 0) if log.usage_stats_black.details else 0)
            completion_tokens = (log.usage_stats_black.details.get("completion_tokens", 0) if log.usage_stats_black.details else 0)
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
            if isinstance(log.player_black.accumulated_reply_time_seconds, (int, float)) and log.player_black.accumulated_reply_time_seconds > 0
        ]
        if per_game_time_seconds:
            average_time_per_game_seconds = mean(per_game_time_seconds)
            std_dev_time_per_game_seconds = stdev(per_game_time_seconds) if len(per_game_time_seconds) > 1 else 0
            moe_average_time_per_game_seconds = 1.96 * (std_dev_time_per_game_seconds / math.sqrt(len(per_game_time_seconds))) if len(per_game_time_seconds) > 1 else 0
        else:
            average_time_per_game_seconds = 0.0
            moe_average_time_per_game_seconds = 0.0

        refined_rows.append({
            "Player": model_name,
            "total_games": total_games,
            "player_wins": black_llm_wins,
            "opponent_wins": white_rand_wins,
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
            "moe_black_llm_win_rate": round((1.96 * math.sqrt(((black_llm_wins/total_games) * (1 - (black_llm_wins/total_games))) / total_games)) if total_games > 1 else 0, 3) if total_games else 0,
            "moe_draw_rate": round((1.96 * math.sqrt(((draws/total_games) * (1 - (draws/total_games))) / total_games)) if total_games > 1 else 0, 3) if total_games else 0,
            "moe_black_llm_loss_rate": round((1.96 * math.sqrt(((white_rand_wins/total_games) * (1 - (white_rand_wins/total_games))) / total_games)) if total_games > 1 else 0, 3) if total_games else 0,
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
        })

    return refined_rows

# Unified refined CSV headers used across functions
REFINED_HEADERS = [
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
        if player not in grouped:
            # Make a shallow copy to avoid mutating the original
            grouped[player] = dict(row)
            continue

        g = grouped[player]

        # Preserve previous weights before updating totals
        tg_prev = to_int(g.get("total_games"))
        tm_prev = to_int(g.get("total_moves"))
        gni_prev = to_int(g.get("games_not_interrupted"))

        tg_new = to_int(row.get("total_games"))
        tm_new = to_int(row.get("total_moves"))
        gni_new = to_int(row.get("games_not_interrupted"))

        # Sum integer count fields
        for key in [
            "total_games",
            "player_wins",
            "opponent_wins",
            "draws",
            "total_moves",
            "player_wrong_actions",
            "player_wrong_moves",
            "games_interrupted",
            "games_not_interrupted",
        ]:
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
            g[key] = weighted_mean(
                to_float(g.get(key)), tg_prev, to_float(row.get(key)), tg_new
            )

        # Weighted by moves
        for key in [
            "completion_tokens_black_per_move",
        ]:
            g[key] = weighted_mean(
                to_float(g.get(key)), tm_prev, to_float(row.get(key)), tm_new
            )

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
    for player, g in grouped.items():
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
        g["wrong_actions_per_1000moves"] = (
            round((wa / tm) * 1000, 3) if tm else 0
        )
        g["wrong_moves_per_1000moves"] = (
            round((wm / tm) * 1000, 3) if tm else 0
        )
        g["mistakes_per_1000moves"] = (
            round(((wa + wm) / tm) * 1000, 3) if tm else 0
        )
        g["material_diff_player_llm_minus_opponent"] = round(
            to_float(g.get("player_avg_material")) - to_float(g.get("opponent_avg_material")),
            3,
        )
        # Normalize win_loss back to [0,1]
        g["win_loss"] = round((((wins - losses) / tg) / 2 + 0.5), 3) if tg else 0.5
        # Keep percents in 0–100
        g["games_interrupted_percent"] = round(((gi / tg) * 100), 3) if tg else 0
        g["games_not_interrupted_percent"] = round(((gni / tg) * 100), 3) if tg else 0

        out.append(g)

    return out

# Deprecated aggregate-CSV converter removed

def merge_refined_csvs(new_refined_file, old_refined_file, output_file):
    """Merge two refined CSVs into one, preferring rows from new_refined_file on Player conflicts.

    If old_refined_file does not exist, simply copy new_refined_file -> output_file.
    """
    # Load rows from new refined file
    with open(new_refined_file, "r", encoding="utf-8") as f_new:
        reader_new = csv.DictReader(f_new)
        by_player = {row.get("Player"): row for row in reader_new if row.get("Player")}

    # Load rows from old refined file if present
    if os.path.exists(old_refined_file):
        with open(old_refined_file, "r", encoding="utf-8") as f_old:
            reader_old = csv.DictReader(f_old)
            for row in reader_old:
                player = row.get("Player")
                if not player:
                    continue
                # Only add if not present; prefer new on conflict
                if player not in by_player:
                    by_player[player] = row

    # Normalize rows to have all required headers
    normalized_rows = []
    for player, row in by_player.items():
        normalized = {}
        for key in REFINED_HEADERS:
            if key in row and row[key] != "":
                normalized[key] = row[key]
            else:
                # Default missing numeric fields to 0, strings to empty
                normalized[key] = "0" if key != "Player" else player
        normalized_rows.append(normalized)

    # Write merged output
    with open(output_file, "w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=REFINED_HEADERS)
        writer.writeheader()
        # Sort by Win/Loss desc then Game Duration desc then Tokens asc to keep deterministic output
        def sort_key(x):
            try:
                return (
                    -float(x.get("win_loss", 0) or 0),
                    -float(x.get("game_duration", 0) or 0),
                    float(x.get("completion_tokens_black_per_move", 0) or 0),
                )
            except (ValueError, TypeError):
                return (0, 0, 0)
        for row in sorted(normalized_rows, key=sort_key):
            writer.writerow(row)

# Deprecated aggregate-CSV converter removed

def merge_refined_rows_and_old(new_rows, old_refined_file):
    """Merge refined rows in memory with an existing refined.csv from disk.

    Prefers new_rows on Player conflicts.
    Returns merged, normalized, sorted rows.
    """
    # Collapse in-memory rows by Player to merge aliased duplicates before merging with history
    collapsed_new_rows = collapse_refined_rows_by_player(new_rows)
    by_player = {row.get("Player"): row for row in collapsed_new_rows if row.get("Player")}

    if os.path.exists(old_refined_file):
        with open(old_refined_file, "r", encoding="utf-8") as f_old:
            reader_old = csv.DictReader(f_old)
            for row in reader_old:
                player = row.get("Player")
                if player and player not in by_player:
                    by_player[player] = row

    normalized_rows = []
    for player, row in by_player.items():
        normalized = {}
        for key in REFINED_HEADERS:
            normalized[key] = row.get(key, "0") if key != "Player" else player
        normalized_rows.append(normalized)

    def sort_key(x):
        try:
            return (
                -float(x.get("win_loss", 0) or 0),
                -float(x.get("game_duration", 0) or 0),
                float(x.get("completion_tokens_black_per_move", 0) or 0),
            )
        except (ValueError, TypeError):
            return (0, 0, 0)

    return sorted(normalized_rows, key=sort_key)

def write_refined_csv(rows, output_file):
    with open(output_file, "w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=REFINED_HEADERS)
        writer.writeheader()
        writer.writerows(rows)

def print_leaderboard(csv_file, top_n=None):
    """Print a formatted leaderboard to the console with the same metrics as the web version."""
    rows = []
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        data = list(reader)
    
    # Sort data using the same logic as in the web version:
    # Win/Loss DESC, then Game Duration DESC, then Tokens ASC
    sorted_data = sorted(
        data, 
        key=lambda x: (
            -float(x['win_loss']),  # DESC
            -float(x['game_duration']),  # DESC
            float(x['completion_tokens_black_per_move'])  # ASC
        )
    )
    
    # Limit to top N if specified
    if top_n:
        sorted_data = sorted_data[:top_n]
    
    # Prepare data for tabulate
    total_cost_all_models = 0.0
    for rank, row in enumerate(sorted_data, 1):
        player_name = row['Player']
        
        # Format the metrics like in the web version
        win_loss = f"{float(row['win_loss']) * 100:.2f}%"
        game_duration = f"{float(row['game_duration']) * 100:.2f}%"
        tokens = float(row['completion_tokens_black_per_move'])
        tokens_str = f"{tokens:.1f}" if tokens > 1000 else f"{tokens:.2f}"
        
        # Format the cost with margin of error
        cost = float(row['average_game_cost'])
        moe = float(row['moe_average_game_cost'])
        cost_str = f"${cost:.4f}±{moe:.4f}"
        
        # Calculate total cost per model
        total_games = int(row['total_games'])
        total_cost = cost * total_games
        total_cost_str = f"${total_cost:.2f}"
        total_cost_all_models += total_cost
        
        # Prefer measured average time per game if available; otherwise N/A
        try:
            measured_time = float(row.get('average_time_per_game_seconds', 0) or 0)
        except (ValueError, TypeError):
            measured_time = 0.0
        if measured_time > 0:
            if measured_time < 60:
                time_str = f"{measured_time:.1f}s"
            elif measured_time < 3600:
                time_str = f"{measured_time/60:.1f}m"
            else:
                time_str = f"{measured_time/3600:.2f}h"
        else:
            time_str = "N/A"
        
        rows.append([
            rank,
            player_name,
            win_loss,
            game_duration,
            tokens_str,
            cost_str,
            time_str,
            total_games,
            total_cost_str
        ])
    
    # Print the table with headers
    headers = ['#', 'Player', 'Win/Loss', 'Game Duration', 'Tokens', 'Cost/Game', 'Time/Game', 'Games', 'Total Cost']
    print(tabulate(rows, headers=headers, tablefmt='grid'))
    print(f"\nTotal cost across all models: ${total_cost_all_models:.2f}")


def main():
    print(f"Building refined rows directly from logs: {LOGS_DIRS}")
    new_rows = build_refined_rows_from_logs(
        LOGS_DIRS,
        model_overrides=MODEL_OVERRIDES,
        only_after_date=DATE_AFTER,
        filter_out_below_n=FILTER_OUT_BELOW_N,
        filter_out_models=FILTER_OUT_MODELS,
        model_aliases=ALIASES,
        models_metadata_csv=MODELS_METADATA_CSV,
    )
    # Collapse duplicates (e.g., aliased models)
    new_rows = collapse_refined_rows_by_player(new_rows)
    print(f"Computed refined rows in memory: {len(new_rows)}")

    # Merge with historical refined CSV (insert-only; prefer new on conflict)
    merged_rows = merge_refined_rows_and_old(new_rows, PREV_REFINED_CSV)
    write_refined_csv(merged_rows, REFINED_CSV)
    print(f"Wrote merged refined CSV: {REFINED_CSV}")

    # Leaderboard
    print("\n=== LLM CHESS LEADERBOARD (Merged) ===\n")
    print_leaderboard(REFINED_CSV)
    print("\nMETRICS EXPLANATION:")
    print("- Win/Loss: Difference between wins and losses as a percentage (0-100%). Higher is better.")
    print("- Game Duration: Percentage of maximum possible game length completed (0-100%). Higher indicates better instruction following.")
    print("- Tokens: Number of tokens generated per move. Shows model verbosity/efficiency.")
    print("- Cost/Game: Average cost per game with margin of error. Lower is more economical.")
    print("- Time/Game: Measured average time per game from logs; N/A if unavailable.")
    print("- Total Cost: Total cost across all games for this model.")


if __name__ == "__main__":
    main()
