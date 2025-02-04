import os
import json
import csv
import math
from dataclasses import dataclass, field
from typing import Dict, Any
from statistics import mean, stdev

# Directory where log files are stored
LOGS_DIR = "_logs/no_reflection"

# Path to the output CSV file where aggregated results will be saved
OUTPUT_CSV = "_logs/no_reflection/aggregate_models.csv"

# Dictionary to override model names in the logs with more descriptive names, matches key as a substring in log file path
MODEL_OVERRIDES = {
    "2025-21-01_deepseek-r1-distill-qwen-32b@q4_k_m_no_thinking_isol": "deepseek-r1-distill-qwen-32b@q4_k_m|noisol_temp03",
    "2025-21-01_deepseek-r1-distill-qwen-32b@q4_k_m_temp06_thinking_isol": "deepseek-r1-distill-qwen-32b@q4_k_m|isol_temp06",
    "2025-21-01_deepseek-r1-distill-qwen-32b@q4_k_m_temp06_no_thinking_isol": "deepseek-r1-distill-qwen-32b@q4_k_m|noisol_temp06",
}


@dataclass
class PlayerStats:
    name: str
    wrong_moves: int
    wrong_actions: int
    reflections_used: int
    reflections_used_before_board: int
    model: str

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


def load_game_logs(logs_dir, model_overrides):
    logs = []

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

    return logs


def aggregate_models_to_csv(
    logs_dir: str, output_csv: str, model_overrides: dict = None
) -> None:
    """
    Aggregates game logs from a specified directory and writes the results to a CSV file.

    Args:
        logs_dir (str): The directory containing the game log files in JSON format.
        output_csv (str): The path to the output CSV file where aggregated results will be saved.
        model_overrides (dict, optional): A dictionary mapping file path (the last part of the path
                                          i.e. 'def' from '/abc/def/') to model names,
                                          used to override the model name in the logs if specified.

    Returns:
        None
    """
    logs = load_game_logs(logs_dir, model_overrides)

    headers = [
        "model_name",
        "total_games",
        "black_llm_wins",
        "white_rand_wins",
        "draws",
        "black_llm_wins_percent",
        "black_llm_draws_percent",
        "white_rand_wins_percent",
        "llm_total_moves",
        "llm_wrong_actions",
        "llm_wrong_moves",
        "llm_avg_material",
        "llm_std_dev_material",
        "rand_avg_material",
        "rand_std_dev_material",
        "material_diff_llm_minus_rand",
        "material_diff_llm_minus_rand_per_100moves",
        "wrong_actions_per_100moves",
        "wrong_moves_per_100moves",
        "wrong_actions_per_1000moves",
        "wrong_moves_per_1000moves",
        "mistakes_per_1000moves",
        "std_dev_wrong_actions_per_1000moves",
        "std_dev_wrong_moves_per_1000moves",
        "std_dev_mistakes_per_1000moves",
        "average_moves",
        "std_dev_moves",
        "completion_tokens_black",
        "completion_tokens_black_per_move",
        "std_dev_completion_tokens_black_per_move",
        "moe_completion_tokens_black_per_move",
        "min_moves",
        "max_moves",
        "prompt_tokens_black",
        "total_tokens_black",
        "moe_material_diff",
        "moe_avg_moves",
        "moe_wrong_actions_per_1000moves",
        "moe_wrong_moves_per_1000moves",
        "moe_mistakes_per_1000moves",
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

        black_llm_wins_percent = (
            (black_llm_wins / total_games) * 100 if total_games > 0 else 0
        )
        black_llm_draws_percent = (draws / total_games) * 100 if total_games > 0 else 0

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
            moe_material_diff = z_score * standard_error_material_diff

            standard_error_moves = std_dev_moves / math.sqrt(sample_size)
            moe_avg_moves = z_score * standard_error_moves
        else:
            moe_wrong_actions_per_1000moves = 0
            moe_wrong_moves_per_1000moves = 0
            moe_mistakes_per_1000moves = 0
            moe_material_diff = 0
            moe_avg_moves = 0

        # Append the calculated data to the CSV data list
        csv_data.append(
            [
                model_name,
                total_games,
                black_llm_wins,
                white_rand_wins,
                draws,
                black_llm_wins_percent,
                black_llm_draws_percent,
                (white_rand_wins / total_games) * 100 if total_games > 0 else 0,
                llm_total_moves,
                llm_wrong_actions,
                llm_wrong_moves,
                llm_avg_material,
                llm_std_dev_material,
                rand_avg_material,
                rand_std_dev_material,
                material_diff_llm_minus_rand,
                material_diff_llm_minus_rand_per_100moves,
                wrong_actions_per_100moves,
                wrong_moves_per_100moves,
                wrong_actions_per_1000moves,
                wrong_moves_per_1000moves,
                mistakes_per_1000moves,
                std_dev_wrong_actions_per_1000moves,
                std_dev_wrong_moves_per_1000moves,
                std_dev_mistakes_per_1000moves,
                average_moves,
                std_dev_moves,
                completion_tokens_black,
                completion_tokens_black_per_move,
                std_dev_completion_tokens_black_per_move,
                moe_completion_tokens_black_per_move,
                min_moves,
                max_moves,
                prompt_tokens_black,
                total_tokens_black,
                moe_material_diff,
                moe_avg_moves,
                moe_wrong_actions_per_1000moves,
                moe_wrong_moves_per_1000moves,
                moe_mistakes_per_1000moves,
            ]
        )

    # Sort the data by model name and write to CSV
    csv_data.sort(key=lambda x: x[0])  # Sort by model_name
    with open(output_csv, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)
        writer.writerows(csv_data)


if __name__ == "__main__":
    aggregate_models_to_csv(LOGS_DIR, OUTPUT_CSV, MODEL_OVERRIDES)
