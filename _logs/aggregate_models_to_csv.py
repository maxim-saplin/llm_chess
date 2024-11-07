import os
import json
import csv
from utils import generate_game_stats


def aggregate_models_to_csv(
    logs_dir="_logs/no_reflection",
    output_csv="_logs/no_reflection/aggregate_models.csv",
):
    csv_data = []
    model_aggregates = {}

    for root, _, files in os.walk(logs_dir):
        for file in files:
            if file.endswith(".json") and not file.endswith("_aggregate_results.json"):
                file_path = os.path.join(root, file)
                with open(file_path, "r") as f:
                    try:
                        data = json.load(f)
                        # Use generate_game_stats to parse the game log
                        game_stats = generate_game_stats(
                            data["time_started"],
                            data["winner"],
                            data["reason"],
                            data["number_of_moves"],
                            data["player_white"],
                            data["player_black"],
                            data["material_count"],
                        )
                        model_name = game_stats["player_black"]["model"]
                        total_moves = game_stats["number_of_moves"]
                        material_diff = (
                            game_stats["material_count"]["black"]
                            - game_stats["material_count"]["white"]
                        )
                        material_diff_llm_minus_rand_per_100moves = (
                            material_diff / total_moves * 100
                        )

                        if model_name not in model_aggregates:
                            model_aggregates[model_name] = {
                                "total_games": 0,
                                "black_wins": 0,
                                "white_wins": 0,
                                "draws": 0,
                                "total_moves": 0,
                                "wrong_actions": 0,
                                "wrong_moves": 0,
                                "sum_avg_material_black": 0,
                                "sum_avg_material_white": 0,
                                "sum_squares_avg_material_black": 0,
                                "sum_squares_avg_material_white": 0,
                                "sum_avg_moves": 0,
                                "sum_squares_avg_moves": 0,
                            }

                        model_aggregates[model_name]["total_games"] += 1
                        if game_stats["winner"] == "Player_Black":
                            model_aggregates[model_name]["black_wins"] += 1
                        elif game_stats["winner"] == "Random_Player":
                            model_aggregates[model_name]["white_wins"] += 1
                        else:
                            model_aggregates[model_name]["draws"] += 1

                        model_aggregates[model_name]["total_moves"] += total_moves
                        model_aggregates[model_name]["wrong_actions"] += game_stats[
                            "player_black"
                        ]["wrong_actions"]
                        model_aggregates[model_name]["wrong_moves"] += game_stats[
                            "player_black"
                        ]["wrong_moves"]
                        model_aggregates[model_name]["sum_avg_material_black"] += (
                            game_stats["material_count"]["black"] * total_moves
                        )
                        model_aggregates[model_name]["sum_avg_material_white"] += (
                            game_stats["material_count"]["white"] * total_moves
                        )
                        model_aggregates[model_name][
                            "sum_squares_avg_material_black"
                        ] += (game_stats["material_count"]["black"] ** 2) * total_moves
                        model_aggregates[model_name][
                            "sum_squares_avg_material_white"
                        ] += (game_stats["material_count"]["white"] ** 2) * total_moves
                        model_aggregates[model_name]["sum_avg_moves"] += total_moves
                        model_aggregates[model_name]["sum_squares_avg_moves"] += (
                            total_moves**2
                        )

                    except json.JSONDecodeError:
                        print(f"Skipping invalid JSON file: {file_path}")

    headers = [
        "model_name",
        "total_games",
        "black_llm_wins",
        "white_rand_wins",
        "draws",
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
        "average_moves",
        "std_dev_moves",
    ]

    for model_name, aggregate in model_aggregates.items():
        total_moves = aggregate["total_moves"]
        weighted_avg_material_black = aggregate["sum_avg_material_black"] / total_moves
        weighted_avg_material_white = aggregate["sum_avg_material_white"] / total_moves
        weighted_avg_moves = aggregate["sum_avg_moves"] / aggregate["total_games"]

        variance_material_black = (
            aggregate["sum_squares_avg_material_black"] / total_moves
        ) - (weighted_avg_material_black**2)
        variance_material_white = (
            aggregate["sum_squares_avg_material_white"] / total_moves
        ) - (weighted_avg_material_white**2)
        variance_moves = (
            aggregate["sum_squares_avg_moves"] / aggregate["total_games"]
        ) - (weighted_avg_moves**2)

        std_dev_material_black = variance_material_black**0.5
        std_dev_material_white = variance_material_white**0.5
        std_dev_moves = variance_moves**0.5

        material_diff = weighted_avg_material_black - weighted_avg_material_white
        material_diff_llm_minus_rand_per_100moves = material_diff / total_moves * 100

        csv_data.append(
            [
                model_name,
                aggregate["total_games"],
                aggregate["black_wins"],
                aggregate["white_wins"],
                aggregate["draws"],
                total_moves,
                aggregate["wrong_actions"],
                aggregate["wrong_moves"],
                weighted_avg_material_black,
                std_dev_material_black,
                weighted_avg_material_white,
                std_dev_material_white,
                material_diff,
                material_diff_llm_minus_rand_per_100moves,
                aggregate["wrong_actions"] / total_moves * 100,
                aggregate["wrong_moves"] / total_moves * 100,
                weighted_avg_moves,
                std_dev_moves,
            ]
        )

    csv_data.sort(key=lambda x: x[0])  # Sort by model_name
    with open(output_csv, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)
        writer.writerows(csv_data)


if __name__ == "__main__":
    aggregate_models_to_csv()
