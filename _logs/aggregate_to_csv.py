import os
import json
import csv


def aggregate_results_to_csv(
    logs_dir="_logs/no_reflection",
    output_csv="_logs/no_reflection/aggregate_results.csv",
):
    csv_data = []
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
        "material_diff_llm_minus_rand_per_100moves",  # New header
        "wrong_actions_per_100moves",
        "wrong_moves_per_100moves",
        "average_moves",
        "std_dev_moves",
    ]

    for root, _, files in os.walk(logs_dir):
        for file in files:
            if file.endswith("_aggregate_results.json"):
                file_path = os.path.join(root, file)
                with open(file_path, "r") as f:
                    data = json.load(f)
                    print(f"Processing file: {file_path}")
                    model_name = data["player_black"]["model"]
                    print(f"Model: {model_name}")
                    total_moves = data["total_moves"]
                    wrong_actions_per_100moves = (
                        data["player_black"]["wrong_actions"] / total_moves * 100
                    )
                    wrong_moves_per_100moves = (
                        data["player_black"]["wrong_moves"] / total_moves * 100
                    )
                    material_diff = (
                        data["player_black"]["avg_material"]
                        - data["player_white"]["avg_material"]
                    )

                    material_diff_llm_minus_rand_per_100moves = material_diff / total_moves * 100

                    csv_data.append(
                        [
                            model_name,
                            data["total_games"],
                            data["black_wins"],
                            data["white_wins"],
                            data["draws"],
                            data["total_moves"],
                            data["player_black"]["wrong_actions"],
                            data["player_black"]["wrong_moves"],
                            data["player_black"]["avg_material"],
                            data["player_black"]["std_dev_material"],
                            data["player_white"]["avg_material"],
                            data["player_white"]["std_dev_material"],
                            material_diff,
                            material_diff_llm_minus_rand_per_100moves,  # New value
                            wrong_actions_per_100moves,
                            wrong_moves_per_100moves,
                            data["average_moves"],
                            data["std_dev_moves"],
                        ]
                    )

    csv_data.sort(key=lambda x: x[0])  # Sort by model_name
    print(f"Total records: {len(csv_data)}")
    with open(output_csv, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)
        writer.writerows(csv_data)


if __name__ == "__main__":
    aggregate_results_to_csv()
