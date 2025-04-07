"""
The main processing module that collects all individual game log JSON files, groups by model IDs
and produces a CSV with a set of aggregate statistics

Contain types definitnions for a Game log
"""

import os
import sys
import json
import csv
import math
from dataclasses import dataclass, field
from typing import ClassVar, Dict, Any, List, Union
from statistics import mean, stdev

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

# Directory where log files are stored
LOGS_DIRS = [
    "_logs/no_reflection",
    # Add other log directories here as needed
]

# Path to the output CSV file where aggregated results will be saved
OUTPUT_CSV = "_logs/aggregate_models.csv"

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

    max_moves_in_game: ClassVar[int] = 200  # Global config defing the max duration of a game used to define relative duration, change in case non default game durations were used

    @property
    def is_interrupted(self) -> int:
        """
        Aka 'game loop broken'. A flag determining is the game was endeddue to a normal flows (e.g. check mate or max moves limmit was reached)
        or due to abnormal execution (too many wrong actiuons, to many actions in a dialog, error - i.e. any failures within the game loop)

        Reasons for game interruption include:
            - Error: An error occurred during execution.
            - Unknown Issue: An unknown issue prevented the game from proceeding.
            - Max Turns: The maximum number of turns in a dialog was reached.
            - Too Many Wrong Actions: The player made too many wrong actions in the dialog.
        """
        return self.reason in {
            TerminationReason.ERROR.value,
            TerminationReason.UNKNOWN_ISSUE.value,
            TerminationReason.MAX_TURNS.value,
            TerminationReason.TOO_MANY_WRONG_ACTIONS.value,
        }
    
    @property
    def game_duration(self) -> float:
        return 1.0 if not self.is_interrupted else self.number_of_moves / GameLog.max_moves_in_game


def load_game_logs(logs_dirs: Union[str, List[str]], model_overrides):
    """
    Load game logs from one or more directories.
    
    Args:
        logs_dirs: Either a single directory path or a list of directory paths
        model_overrides: Dictionary for model name overrides
    
    Returns:
        List of GameLog objects
    """
    logs = []
    
    # Convert single directory to list for consistent handling
    if isinstance(logs_dirs, str):
        logs_dirs = [logs_dirs]
    
    def _load_game_log(file_path: str) -> GameLog:
        with open(file_path, "r") as f:
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
                    details=(
                        data["usage_stats"]["white"].get(white_usage_keys[1], None)
                        if len(white_usage_keys) > 1
                        else None
                    ),
                ),
                usage_stats_black=UsageStats(
                    total_cost=data["usage_stats"]["black"][black_usage_keys[0]],
                    details=(
                        data["usage_stats"]["black"].get(black_usage_keys[1], None)
                        if len(black_usage_keys) > 1
                        else None
                    ),
                ),
            )

    for logs_dir in logs_dirs:
        print(f"Loading logs from directory: {logs_dir}")
        
        for root, _, files in os.walk(logs_dir):
            for file in files:
                if file.endswith(".json") and not file.endswith("_aggregate_results.json"):
                    file_path = os.path.join(root, file)
                    try:
                        game_log = _load_game_log(file_path)
                        # Use model ID from log, override if specified
                        model_name = game_log.player_black.model
                        if model_overrides:
                            key = next(
                                (
                                    k
                                    for k in model_overrides
                                    if os.path.dirname(file_path).endswith(k)
                                ),
                                None,
                            )
                            if key:
                                original_model_name = model_name
                                model_name = model_overrides[key]
                                print(
                                    f"Warning: Overriding model name from '{original_model_name}' to '{model_name}' for file '{file_path}'"
                                )
                        game_log.player_black.model = model_name
                        logs.append(game_log)
                    except Exception as e:
                        print(f"Skipping invalid JSON file: {file_path}. Error: {e}")
    
    print(f"Total logs loaded from all directories: {len(logs)}")
    return logs


def aggregate_models_to_csv(
    logs_dirs: Union[str, List[str]], output_csv: str, model_overrides: dict = None
) -> None:
    """
    Aggregates game logs from one or more directories and writes the results to a CSV file.

    Args:
        logs_dirs: Either a single directory path or a list of directory paths containing game logs
        output_csv: The path to the output CSV file where aggregated results will be saved
        model_overrides: A dictionary mapping file path to model names for overriding

    Returns:
        None
    """
    logs = load_game_logs(logs_dirs, model_overrides)

    headers = [
        "model_name",
        "total_games",
        "black_llm_wins",
        "white_rand_wins",
        "draws",
        "black_llm_win_rate",
        "std_dev_black_llm_win_rate",
        "moe_black_llm_win_rate",
        "black_llm_loss_rate",
        "std_dev_black_llm_loss_rate",
        "moe_black_llm_loss_rate",
        "draw_rate",
        "std_dev_draw_rate",
        "moe_draw_rate",
        "black_llm_wins_percent",
        "black_llm_draws_percent",
        "white_rand_wins_percent",
        "win_loss",
        "std_dev_win_loss",
        "moe_win_loss",
        "win_loss_non_interrupted",
        "std_dev_win_loss_non_interrupted",
        "moe_win_loss_non_interrupted",
        "game_duration",
        "std_dev_game_duration", 
        "moe_game_duration",
        "games_interrupted",
        "games_interrupted_percent",
        "std_dev_games_interrupted",
        "moe_games_interrupted",
        "games_not_interrupted",
        "games_not_interrupted_percent",
        "std_dev_games_not_interrupted",
        "moe_games_not_interrupted",
        "llm_total_moves",
        "average_moves",
        "std_dev_moves",
        "moe_avg_moves",
        "llm_wrong_actions",
        "llm_wrong_moves",
        "wrong_actions_per_100moves",
        "wrong_moves_per_100moves",
        "wrong_actions_per_1000moves",
        "wrong_moves_per_1000moves",
        "mistakes_per_1000moves",
        "std_dev_wrong_actions_per_1000moves",
        "std_dev_wrong_moves_per_1000moves",
        "std_dev_mistakes_per_1000moves",
        "moe_wrong_actions_per_1000moves",
        "moe_wrong_moves_per_1000moves",
        "moe_mistakes_per_1000moves",
        "llm_avg_material",
        "llm_std_dev_material",
        "rand_avg_material",
        "rand_std_dev_material",
        "material_diff_llm_minus_rand",
        "material_diff_llm_minus_rand_per_100moves",
        "moe_material_diff_llm_minus_rand",
        "completion_tokens_black",
        "completion_tokens_black_per_move",
        "std_dev_completion_tokens_black_per_move",
        "moe_completion_tokens_black_per_move",
        "min_moves",
        "max_moves",
        "prompt_tokens_black",
        "total_tokens_black",
    ]

    csv_data = []

    # Group logs by model name
    model_groups = {}
    for log in logs:
        model_name = log.player_black.model
        if model_name not in model_groups:
            model_groups[model_name] = []
        model_groups[model_name].append(log)

    for model_name, model_logs in model_groups.items():
        total_games = len(model_logs)
        black_llm_wins = sum(1 for log in model_logs if log.winner == "Player_Black")
        white_rand_wins = sum(1 for log in model_logs if log.winner == "Random_Player")
        draws = total_games - black_llm_wins - white_rand_wins

        black_llm_wins_percent = (black_llm_wins / total_games) * 100 if total_games > 0 else 0
        black_llm_draws_percent = (draws / total_games) * 100 if total_games > 0 else 0

        # Calculate win_loss metric
        win_loss = ((black_llm_wins - white_rand_wins) / total_games) / 2 + 0.5 if total_games > 0 else 0.5

        # Calculate standard deviation and margin of error for win_loss
        per_game_win_loss = [(1 / 2 + 0.5) if log.winner == "Player_Black" else 
                            (-1 / 2 + 0.5) if log.winner == "Random_Player" else 
                            0.5 for log in model_logs]
        std_dev_win_loss = stdev(per_game_win_loss) if total_games > 1 else 0
        moe_win_loss = 1.96 * (std_dev_win_loss / math.sqrt(total_games)) if total_games > 1 else 0

        # Calculate game_duration metric
        game_duration = mean([log.game_duration for log in model_logs]) if model_logs else 0
        std_dev_game_duration = stdev([log.game_duration for log in model_logs]) if total_games > 1 else 0
        moe_game_duration = 1.96 * (std_dev_game_duration / math.sqrt(total_games)) if total_games > 1 else 0

        # Calculate games_interrupted metric
        games_interrupted = sum(1 for log in model_logs if log.is_interrupted)
        games_interrupted_percent = (games_interrupted / total_games * 100) if total_games > 0 else 0
        p_interrupted = games_interrupted / total_games if total_games > 0 else 0
        std_dev_games_interrupted = math.sqrt((p_interrupted * (1 - p_interrupted)) / total_games) if total_games > 1 else 0
        moe_games_interrupted = 1.96 * std_dev_games_interrupted if total_games > 1 else 0

        # Calculate games_not_interrupted metrics
        games_not_interrupted = total_games - games_interrupted
        games_not_interrupted_percent = (games_not_interrupted / total_games * 100) if total_games > 0 else 0
        p_not_interrupted = games_not_interrupted / total_games if total_games > 0 else 0
        std_dev_games_not_interrupted = math.sqrt((p_not_interrupted * (1 - p_not_interrupted)) / total_games) if total_games > 1 else 0
        moe_games_not_interrupted = 1.96 * std_dev_games_not_interrupted if total_games > 1 else 0

        # Calculate win_loss_non_interrupted metric (excluding interrupted games)
        non_interrupted_logs = [log for log in model_logs if not log.is_interrupted]
        non_interrupted_games = len(non_interrupted_logs)
        black_llm_wins_non_interrupted = sum(1 for log in non_interrupted_logs if log.winner == "Player_Black")
        white_rand_wins_non_interrupted = sum(1 for log in non_interrupted_logs if log.winner == "Random_Player")
        
        if non_interrupted_games > 0:
            win_loss_non_interrupted = ((black_llm_wins_non_interrupted - white_rand_wins_non_interrupted) / non_interrupted_games) / 2 + 0.5
            
            # Calculate standard deviation and margin of error for win_loss_non_interrupted
            per_game_win_loss_non_interrupted = [(1 / 2 + 0.5) if log.winner == "Player_Black" else 
                                                (-1 / 2 + 0.5) if log.winner == "Random_Player" else 
                                                0.5 for log in non_interrupted_logs]
            std_dev_win_loss_non_interrupted = stdev(per_game_win_loss_non_interrupted) if non_interrupted_games > 1 else 0
            moe_win_loss_non_interrupted = 1.96 * (std_dev_win_loss_non_interrupted / math.sqrt(non_interrupted_games)) if non_interrupted_games > 1 else 0
        else:
            win_loss_non_interrupted = 0.5
            std_dev_win_loss_non_interrupted = 0
            moe_win_loss_non_interrupted = 0

        # Calculate win rate, standard deviation, and margin of error
        black_llm_win_rate = black_llm_wins / total_games if total_games > 0 else 0
        if total_games > 0:
            std_dev_black_llm_win_rate = math.sqrt(
                (black_llm_win_rate * (1 - black_llm_win_rate)) / total_games
            )
            moe_black_llm_win_rate = 1.96 * std_dev_black_llm_win_rate
        else:
            std_dev_black_llm_win_rate = 0
            moe_black_llm_win_rate = 0

        # Calculate loss rate
        black_llm_loss_rate = white_rand_wins / total_games if total_games > 0 else 0

        # Calculate standard deviation and margin of error for loss rate
        if total_games > 0:
            std_dev_black_llm_loss_rate = math.sqrt(
                (black_llm_loss_rate * (1 - black_llm_loss_rate)) / total_games
            )
            moe_black_llm_loss_rate = 1.96 * std_dev_black_llm_loss_rate
        else:
            std_dev_black_llm_loss_rate = 0
            moe_black_llm_loss_rate = 0

        # Calculate draw rate
        draw_rate = draws / total_games if total_games > 0 else 0

        # Calculate standard deviation and margin of error for draw rate
        if total_games > 0:
            std_dev_draw_rate = math.sqrt((draw_rate * (1 - draw_rate)) / total_games)
            moe_draw_rate = 1.96 * std_dev_draw_rate
        else:
            std_dev_draw_rate = 0.0
            moe_draw_rate = 0.0

        llm_total_moves = sum(log.number_of_moves for log in model_logs)
        llm_wrong_actions = sum(log.player_black.wrong_actions for log in model_logs)
        llm_wrong_moves = sum(log.player_black.wrong_moves for log in model_logs)

        # Calculate per-game material counts
        per_game_llm_material = [log.material_count["black"] for log in model_logs]
        per_game_rand_material = [log.material_count["white"] for log in model_logs]

        llm_avg_material = mean(per_game_llm_material)
        llm_std_dev_material = stdev(per_game_llm_material) if total_games > 1 else 0
        rand_avg_material = mean(per_game_rand_material)
        rand_std_dev_material = stdev(per_game_rand_material) if total_games > 1 else 0

        # Calculate per-game material difference
        per_game_material_diff = [
            llm_material - rand_material
            for llm_material, rand_material in zip(
                per_game_llm_material, per_game_rand_material
            )
        ]
        material_diff_llm_minus_rand = mean(per_game_material_diff)
        std_dev_material_diff = stdev(per_game_material_diff) if total_games > 1 else 0

        # Calculate per-game material difference per 100 moves
        per_game_material_diff_per_100moves = [
            (diff / log.number_of_moves * 100)
            for diff, log in zip(per_game_material_diff, model_logs)
            if log.number_of_moves > 0
        ]
        material_diff_llm_minus_rand_per_100moves = (
            mean(per_game_material_diff_per_100moves)
            if per_game_material_diff_per_100moves
            else 0
        )

        # Calculate per-game rates
        per_game_wrong_actions_per_1000moves = [
            (log.player_black.wrong_actions / log.number_of_moves * 1000)
            for log in model_logs
            if log.number_of_moves > 0
        ]
        per_game_wrong_moves_per_1000moves = [
            (log.player_black.wrong_moves / log.number_of_moves * 1000)
            for log in model_logs
            if log.number_of_moves > 0
        ]
        per_game_mistakes_per_1000moves = [
            (
                (log.player_black.wrong_actions + log.player_black.wrong_moves)
                / log.number_of_moves
                * 1000
            )
            for log in model_logs
            if log.number_of_moves > 0
        ]

        # Compute mean and standard deviation of per-game rates
        wrong_actions_per_1000moves = (
            mean(per_game_wrong_actions_per_1000moves)
            if per_game_wrong_actions_per_1000moves
            else 0
        )
        std_dev_wrong_actions_per_1000moves = (
            stdev(per_game_wrong_actions_per_1000moves)
            if len(per_game_wrong_actions_per_1000moves) > 1
            else 0
        )

        wrong_moves_per_1000moves = (
            mean(per_game_wrong_moves_per_1000moves)
            if per_game_wrong_moves_per_1000moves
            else 0
        )
        std_dev_wrong_moves_per_1000moves = (
            stdev(per_game_wrong_moves_per_1000moves)
            if len(per_game_wrong_moves_per_1000moves) > 1
            else 0
        )

        mistakes_per_1000moves = (
            mean(per_game_mistakes_per_1000moves)
            if per_game_mistakes_per_1000moves
            else 0
        )
        std_dev_mistakes_per_1000moves = (
            stdev(per_game_mistakes_per_1000moves)
            if len(per_game_mistakes_per_1000moves) > 1
            else 0
        )

        # Similarly for per 100 moves
        per_game_wrong_actions_per_100moves = [
            (log.player_black.wrong_actions / log.number_of_moves * 100)
            for log in model_logs
            if log.number_of_moves > 0
        ]
        per_game_wrong_moves_per_100moves = [
            (log.player_black.wrong_moves / log.number_of_moves * 100)
            for log in model_logs
            if log.number_of_moves > 0
        ]

        wrong_actions_per_100moves = (
            mean(per_game_wrong_actions_per_100moves)
            if per_game_wrong_actions_per_100moves
            else 0
        )
        wrong_moves_per_100moves = (
            mean(per_game_wrong_moves_per_100moves)
            if per_game_wrong_moves_per_100moves
            else 0
        )

        # Moves statistics
        per_game_moves = [log.number_of_moves for log in model_logs]
        average_moves = mean(per_game_moves)
        std_dev_moves = stdev(per_game_moves) if total_games > 1 else 0
        min_moves = min(per_game_moves)
        max_moves = max(per_game_moves)

        # Token usage calculations
        completion_tokens_black = sum(
            (
                log.usage_stats_black.details.get("completion_tokens", 0)
                if log.usage_stats_black.details
                else 0
            )
            for log in model_logs
        )
        completion_tokens_black_per_move = (
            completion_tokens_black / llm_total_moves if llm_total_moves > 0 else 0
        )

        # Calculate std_dev and moe for completion_tokens_black_per_move
        per_game_completion_tokens_black_per_move = [
            (
                (
                    log.usage_stats_black.details.get("completion_tokens", 0)
                    if log.usage_stats_black.details
                    else 0
                )
                / log.number_of_moves
            )
            for log in model_logs
            if log.number_of_moves > 0
        ]
        std_dev_completion_tokens_black_per_move = (
            stdev(per_game_completion_tokens_black_per_move)
            if len(per_game_completion_tokens_black_per_move) > 1
            else 0
        )
        if total_games > 1:
            standard_error_completion_tokens_black_per_move = (
                std_dev_completion_tokens_black_per_move / math.sqrt(total_games)
            )
            moe_completion_tokens_black_per_move = (
                1.96 * standard_error_completion_tokens_black_per_move
            )
        else:
            moe_completion_tokens_black_per_move = 0

        prompt_tokens_black = sum(
            log.usage_stats_black.details.get("prompt_tokens", 0)
            for log in model_logs
            if log.usage_stats_black.details
        )
        total_tokens_black = completion_tokens_black + prompt_tokens_black

        # Calculate margins of error
        if total_games > 1:
            z_score = 1.96  # Z-score for 95% confidence

            sample_size = total_games

            standard_error_wrong_actions = (
                std_dev_wrong_actions_per_1000moves / math.sqrt(sample_size)
            )
            moe_wrong_actions_per_1000moves = z_score * standard_error_wrong_actions

            standard_error_wrong_moves = std_dev_wrong_moves_per_1000moves / math.sqrt(
                sample_size
            )
            moe_wrong_moves_per_1000moves = z_score * standard_error_wrong_moves

            standard_error_mistakes = std_dev_mistakes_per_1000moves / math.sqrt(
                sample_size
            )
            moe_mistakes_per_1000moves = z_score * standard_error_mistakes

            standard_error_material_diff = std_dev_material_diff / math.sqrt(
                sample_size
            )
            moe_material_diff_llm_minus_rand = z_score * standard_error_material_diff

            standard_error_moves = std_dev_moves / math.sqrt(sample_size)
            moe_avg_moves = z_score * standard_error_moves
        else:
            moe_wrong_actions_per_1000moves = 0
            moe_wrong_moves_per_1000moves = 0
            moe_mistakes_per_1000moves = 0
            moe_material_diff_llm_minus_rand = 0
            moe_avg_moves = 0

        # Append the calculated data to the CSV data list
        csv_data.append(
            [
                model_name,
                total_games,
                black_llm_wins,
                white_rand_wins,
                draws,
                black_llm_win_rate,
                std_dev_black_llm_win_rate,
                moe_black_llm_win_rate,
                black_llm_loss_rate,
                std_dev_black_llm_loss_rate,
                moe_black_llm_loss_rate,
                draw_rate,
                std_dev_draw_rate,
                moe_draw_rate,
                black_llm_wins_percent,
                black_llm_draws_percent,
                (white_rand_wins / total_games) * 100 if total_games > 0 else 0,
                win_loss,
                std_dev_win_loss,
                moe_win_loss,
                win_loss_non_interrupted,
                std_dev_win_loss_non_interrupted,
                moe_win_loss_non_interrupted,
                game_duration,
                std_dev_game_duration, 
                moe_game_duration,
                games_interrupted,
                games_interrupted_percent,
                std_dev_games_interrupted,
                moe_games_interrupted,
                games_not_interrupted,
                games_not_interrupted_percent,
                std_dev_games_not_interrupted,
                moe_games_not_interrupted,
                llm_total_moves,
                average_moves,
                std_dev_moves,
                moe_avg_moves,
                llm_wrong_actions,
                llm_wrong_moves,
                wrong_actions_per_100moves,
                wrong_moves_per_100moves,
                wrong_actions_per_1000moves,
                wrong_moves_per_1000moves,
                mistakes_per_1000moves,
                std_dev_wrong_actions_per_1000moves,
                std_dev_wrong_moves_per_1000moves,
                std_dev_mistakes_per_1000moves,
                moe_wrong_actions_per_1000moves,
                moe_wrong_moves_per_1000moves,
                moe_mistakes_per_1000moves,
                llm_avg_material,
                llm_std_dev_material,
                rand_avg_material,
                rand_std_dev_material,
                material_diff_llm_minus_rand,
                material_diff_llm_minus_rand_per_100moves,
                moe_material_diff_llm_minus_rand,
                completion_tokens_black,
                completion_tokens_black_per_move,
                std_dev_completion_tokens_black_per_move,
                moe_completion_tokens_black_per_move,
                min_moves,
                max_moves,
                prompt_tokens_black,
                total_tokens_black,
            ]
        )

    # Sort the data by model name and write to CSV
    csv_data.sort(key=lambda x: x[0])  # Sort by model_name
    with open(output_csv, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)
        writer.writerows(csv_data)


if __name__ == "__main__":
    aggregate_models_to_csv(LOGS_DIRS, OUTPUT_CSV, MODEL_OVERRIDES)
