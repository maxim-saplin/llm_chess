import os
import json
import csv


def aggregate_logs_to_csv(logs_dir, output_csv):
    # Open the CSV file for writing
    with open(output_csv, mode="w", newline="") as csvfile:
        # Define the CSV fieldnames
        fieldnames = [
            "path",
            "time_started",
            "winner",
            "reason",
            "number_of_moves",
            "player_white_name",
            "player_white_wrong_moves",
            "player_white_wrong_actions",
            "player_white_reflections_used",
            "player_white_reflections_used_before_board",
            "player_white_model",
            "material_count_white",
            "material_count_black",
            "player_black_name",
            "player_black_wrong_moves",
            "player_black_wrong_actions",
            "player_black_reflections_used",
            "player_black_reflections_used_before_board",
            "player_black_model",
            "usage_stats_white_total_cost",
            "usage_stats_black_total_cost",
            "usage_stats_black_model_cost",
            "usage_stats_black_model_prompt_tokens",
            "usage_stats_black_model_completion_tokens",
            "usage_stats_black_model_total_tokens",
        ]

        # Create a CSV DictWriter
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        # Iterate over all log files
        for root, _, files in os.walk(logs_dir):
            for file in files:
                if file.endswith(".json") and not file.endswith(
                    "_aggregate_results.json"
                ):
                    file_path = os.path.join(root, file)

                    # Read and parse the JSON file
                    with open(file_path, "r") as f:
                        data = json.load(f)

                    # Flatten the JSON data
                    row = {
                        "path": file_path,
                        "time_started": data.get("time_started"),
                        "winner": data.get("winner"),
                        "reason": data.get("reason"),
                        "number_of_moves": data.get("number_of_moves"),
                        "player_white_name": data["player_white"].get("name"),
                        "player_white_wrong_moves": data["player_white"].get(
                            "wrong_moves"
                        ),
                        "player_white_wrong_actions": data["player_white"].get(
                            "wrong_actions"
                        ),
                        "player_white_reflections_used": data["player_white"].get(
                            "reflections_used"
                        ),
                        "player_white_reflections_used_before_board": data[
                            "player_white"
                        ].get("reflections_used_before_board"),
                        "player_white_model": data["player_white"].get("model"),
                        "material_count_white": data["material_count"].get("white"),
                        "material_count_black": data["material_count"].get("black"),
                        "player_black_name": data["player_black"].get("name"),
                        "player_black_wrong_moves": data["player_black"].get(
                            "wrong_moves"
                        ),
                        "player_black_wrong_actions": data["player_black"].get(
                            "wrong_actions"
                        ),
                        "player_black_reflections_used": data["player_black"].get(
                            "reflections_used"
                        ),
                        "player_black_reflections_used_before_board": data[
                            "player_black"
                        ].get("reflections_used_before_board"),
                        "player_black_model": data["player_black"].get("model"),
                        "usage_stats_white_total_cost": data["usage_stats"][
                            "white"
                        ].get("total_cost"),
                        "usage_stats_black_total_cost": data["usage_stats"][
                            "black"
                        ].get("total_cost"),
                        "usage_stats_black_model_cost": data["usage_stats"]["black"]
                        .get(data["player_black"]["model"], {})
                        .get("cost"),
                        "usage_stats_black_model_prompt_tokens": data["usage_stats"][
                            "black"
                        ]
                        .get(data["player_black"]["model"], {})
                        .get("prompt_tokens"),
                        "usage_stats_black_model_completion_tokens": data[
                            "usage_stats"
                        ]["black"]
                        .get(data["player_black"]["model"], {})
                        .get("completion_tokens"),
                        "usage_stats_black_model_total_tokens": data["usage_stats"][
                            "black"
                        ]
                        .get(data["player_black"]["model"], {})
                        .get("total_tokens"),
                    }

                    # Write the row to the CSV
                    writer.writerow(row)
