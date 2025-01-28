"""
Convert aggregated chess game statistics
from a CSV file into a refined format used for Web publishing.
The refined format includes calculated
percentages and differences that are useful for analyzing player performance
over multiple games.

Functions:
    convert_aggregate_to_refined(aggregate_file, refined_file):
        Reads an aggregate CSV file containing game statistics, processes the
        data to calculate additional metrics, and writes the results to a
        refined CSV file with a new structure.

Usage:
    Set constants to path and run as script OR call the convert_aggregate_to_refined() function
"""

import csv

AGGREGATE_FILE = None  #  "_logs/no_reflection/aggregate_models.csv"
REFINED_FILE = None  # "docs/_data/refined.csv"


def convert_aggregate_to_refined(aggregate_file, refined_file):
    with open(aggregate_file, "r") as agg_file:
        reader = csv.DictReader(agg_file)

        # Define the headers for the refined CSV
        refined_headers = [
            "Player",
            "total_games",
            "player_wins",
            "opponent_wins",
            "draws",
            "player_wins_percent",
            "player_draws_percent",
            "total_moves",
            "player_wrong_actions",
            "player_wrong_moves",
            "player_avg_material",
            "opponent_avg_material",
            "material_diff_player_llm_minus_opponent",
            "material_diff_player_minus_opponent_per_1000moves",
            "wrong_actions_per_1000moves",
            "wrong_moves_per_1000moves",
            "average_moves",
            "completion_tokens_black_per_move",
        ]

        # Prepare to write to the refined CSV
        with open(refined_file, "w", newline="") as ref_file:
            writer = csv.DictWriter(ref_file, fieldnames=refined_headers)
            writer.writeheader()

            for row in reader:
                # Calculate the necessary fields for the refined CSV
                total_games = int(row["total_games"])
                player_wins = int(row["black_llm_wins"])
                opponent_wins = int(row["white_rand_wins"])
                draws = int(row["draws"])
                total_moves = int(row["llm_total_moves"])
                player_wrong_actions = int(row["llm_wrong_actions"])
                player_wrong_moves = int(row["llm_wrong_moves"])
                player_avg_material = float(row["llm_avg_material"])
                opponent_avg_material = float(row["rand_avg_material"])
                material_diff = float(row["material_diff_llm_minus_rand"])
                material_diff_per_1000moves = (
                    float(row["material_diff_llm_minus_rand_per_100moves"]) * 10
                )
                wrong_actions_per_1000moves = (
                    float(row["wrong_actions_per_100moves"]) * 10
                )
                wrong_moves_per_1000moves = float(row["wrong_moves_per_100moves"]) * 10
                average_moves = float(row["average_moves"])
                completion_tokens_black_per_move = float(
                    row["completion_tokens_black_per_move"]
                )

                # Calculate percentages
                player_wins_percent = (player_wins / total_games) * 100
                player_draws_percent = (draws / total_games) * 100

                # Write the row to the refined CSV
                writer.writerow(
                    {
                        "Player": row["model_name"],
                        "total_games": total_games,
                        "player_wins": player_wins,
                        "opponent_wins": opponent_wins,
                        "draws": draws,
                        "player_wins_percent": player_wins_percent,
                        "player_draws_percent": player_draws_percent,
                        "total_moves": total_moves,
                        "player_wrong_actions": player_wrong_actions,
                        "player_wrong_moves": player_wrong_moves,
                        "player_avg_material": player_avg_material,
                        "opponent_avg_material": opponent_avg_material,
                        "material_diff_player_llm_minus_opponent": material_diff,
                        "material_diff_player_minus_opponent_per_1000moves": material_diff_per_1000moves,
                        "wrong_actions_per_1000moves": wrong_actions_per_1000moves,
                        "wrong_moves_per_1000moves": wrong_moves_per_1000moves,
                        "average_moves": average_moves,
                        "completion_tokens_black_per_move": completion_tokens_black_per_move,
                    }
                )


if __name__ == "__main__":
    convert_aggregate_to_refined(AGGREGATE_FILE, REFINED_FILE)
