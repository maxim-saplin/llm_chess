import unittest
import tempfile
import os
import json
import csv
from data_processing.aggregate_logs_to_csv import aggregate_models_to_csv


class TestAggregateMetrics(unittest.TestCase):
    def setUp(self):
        """Set up a temporary directory and mock logs for testing."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_csv = os.path.join(self.temp_dir.name, "aggregate_output.csv")

        # Create mock JSON logs
        self.logs = create_mock_json_logs()

        # Write logs to the temporary directory
        write_mock_logs_to_temp_dir(self.logs, self.temp_dir.name)

    def tearDown(self):
        """Clean up the temporary directory."""
        self.temp_dir.cleanup()

    def test_total_games(self):
        """Tests that the total number of games is correctly aggregated."""
        aggregate_models_to_csv(self.temp_dir.name, self.output_csv)

        # Read the output CSV
        csv_data = read_csv_as_dict(self.output_csv)

        # Verify the total number of games for each model
        model_1_data = next(row for row in csv_data if row["model_name"] == "model_1")
        model_2_data = next(row for row in csv_data if row["model_name"] == "model_2")

        self.assertEqual(int(model_1_data["total_games"]), 2)
        self.assertEqual(int(model_2_data["total_games"]), 2)

    def test_black_llm_wins(self):
        """Tests that the number of black LLM wins is correctly aggregated."""
        aggregate_models_to_csv(self.temp_dir.name, self.output_csv)

        # Read the output CSV
        csv_data = read_csv_as_dict(self.output_csv)

        # Verify the black LLM wins for each model
        model_1_data = next(row for row in csv_data if row["model_name"] == "model_1")
        model_2_data = next(row for row in csv_data if row["model_name"] == "model_2")

        self.assertEqual(int(model_1_data["black_llm_wins"]), 0)
        self.assertEqual(int(model_2_data["black_llm_wins"]), 0)

    def test_draws(self):
        """Tests that the number of draws is correctly aggregated."""
        aggregate_models_to_csv(self.temp_dir.name, self.output_csv)

        # Read the output CSV
        csv_data = read_csv_as_dict(self.output_csv)

        # Verify the draws for each model
        model_1_data = next(row for row in csv_data if row["model_name"] == "model_1")
        model_2_data = next(row for row in csv_data if row["model_name"] == "model_2")

        self.assertEqual(int(model_1_data["draws"]), 1)
        self.assertEqual(int(model_2_data["draws"]), 1)

    def test_average_moves(self):
        """Tests that the average number of moves is correctly calculated."""
        aggregate_models_to_csv(self.temp_dir.name, self.output_csv)

        # Read the output CSV
        csv_data = read_csv_as_dict(self.output_csv)

        # Verify the average moves for each model
        model_1_data = next(row for row in csv_data if row["model_name"] == "model_1")
        model_2_data = next(row for row in csv_data if row["model_name"] == "model_2")

        self.assertAlmostEqual(float(model_1_data["average_moves"]), 166.0)
        self.assertAlmostEqual(float(model_2_data["average_moves"]), 182.0)

    def test_std_dev_moves(self):
        """Tests that the standard deviation of moves is correctly calculated."""
        aggregate_models_to_csv(self.temp_dir.name, self.output_csv)

        # Read the output CSV
        csv_data = read_csv_as_dict(self.output_csv)

        # Verify the standard deviation of moves for each model
        model_1_data = next(row for row in csv_data if row["model_name"] == "model_1")
        model_2_data = next(row for row in csv_data if row["model_name"] == "model_2")

        self.assertAlmostEqual(float(model_1_data["std_dev_moves"]), 48.08326112068523)
        self.assertAlmostEqual(float(model_2_data["std_dev_moves"]), 25.45584412271571)

    def test_mistakes_per_1000moves(self):
        """Tests that the mistakes per 1000 moves are correctly calculated."""
        aggregate_models_to_csv(self.temp_dir.name, self.output_csv)

        # Read the output CSV
        csv_data = read_csv_as_dict(self.output_csv)

        # Verify the mistakes per 1000 moves for each model
        model_1_data = next(row for row in csv_data if row["model_name"] == "model_1")
        model_2_data = next(row for row in csv_data if row["model_name"] == "model_2")

        self.assertAlmostEqual(
            float(model_1_data["mistakes_per_1000moves"]), 11.363636363636363
        )
        self.assertAlmostEqual(
            float(model_2_data["mistakes_per_1000moves"]), 9.146341463414634
        )

    def test_material_diff(self):
        """Tests that the material difference is correctly calculated."""
        aggregate_models_to_csv(self.temp_dir.name, self.output_csv)

        # Read the output CSV
        csv_data = read_csv_as_dict(self.output_csv)

        # Verify the material difference for each model
        model_1_data = next(row for row in csv_data if row["model_name"] == "model_1")
        model_2_data = next(row for row in csv_data if row["model_name"] == "model_2")

        # Corrected expected value for model_1
        self.assertAlmostEqual(
            float(model_1_data["material_diff_llm_minus_rand"]), -8.0
        )
        self.assertAlmostEqual(float(model_2_data["material_diff_llm_minus_rand"]), 1.5)

    def test_black_llm_win_rate_and_moe(self):
        """Tests that the black LLM win rate and margin of error are correctly calculated."""
        aggregate_models_to_csv(self.temp_dir.name, self.output_csv)

        # Read the output CSV
        csv_data = read_csv_as_dict(self.output_csv)

        # Verify the black LLM win rate and margin of error for each model
        model_1_data = next(row for row in csv_data if row["model_name"] == "model_1")
        model_2_data = next(row for row in csv_data if row["model_name"] == "model_2")

        self.assertAlmostEqual(float(model_1_data["black_llm_wins_percent"]), 0.0)
        self.assertAlmostEqual(float(model_2_data["black_llm_wins_percent"]), 0.0)

        self.assertAlmostEqual(float(model_1_data["moe_black_llm_win_rate"]), 0.0)
        self.assertAlmostEqual(float(model_2_data["moe_black_llm_win_rate"]), 0.0)

    def test_draw_rate_and_moe(self):
        """Tests that the draw rate and margin of error are correctly calculated."""
        aggregate_models_to_csv(self.temp_dir.name, self.output_csv)

        # Read the output CSV
        csv_data = read_csv_as_dict(self.output_csv)

        # Verify the draw rate and margin of error for each model
        model_1_data = next(row for row in csv_data if row["model_name"] == "model_1")
        model_2_data = next(row for row in csv_data if row["model_name"] == "model_2")

        self.assertAlmostEqual(float(model_1_data["black_llm_draws_percent"]), 50.0)
        self.assertAlmostEqual(float(model_2_data["black_llm_draws_percent"]), 50.0)

        self.assertAlmostEqual(float(model_1_data["moe_draw_rate"]), 0.69296465)
        self.assertAlmostEqual(float(model_2_data["moe_draw_rate"]), 0.69296465)

    def test_aggregation_output_fields(self):
        aggregate_models_to_csv(self.temp_dir.name, self.output_csv)

        with open(self.output_csv, "r") as csvfile:
            reader = csv.DictReader(csvfile)
            read_headers = reader.fieldnames

        # Expected headers
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
            "std_dev_black_llm_win_rate",
            "moe_black_llm_win_rate",
            "std_dev_draw_rate",
            "moe_draw_rate",
        ]

        # Verify that all expected fields are present in the aggregated CSV
        for field in headers:
            self.assertIn(field, read_headers)


def create_mock_json_logs():
    """Creates a list of mock JSON strings representing game logs."""
    return [
        json.dumps(
            {
                "time_started": "2025.02.09_09:31",
                "winner": "NONE",
                "reason": "Max moves reached",
                "number_of_moves": 200,
                "player_white": {
                    "name": "Random_Player",
                    "wrong_moves": 0,
                    "wrong_actions": 0,
                    "reflections_used": 0,
                    "reflections_used_before_board": 0,
                    "model": "N/A",
                },
                "material_count": {"white": 11, "black": 12},
                "player_black": {
                    "name": "Player_Black",
                    "wrong_moves": 0,
                    "wrong_actions": 0,
                    "reflections_used": 0,
                    "reflections_used_before_board": 0,
                    "model": "model_1",
                },
                "usage_stats": {
                    "white": {"total_cost": 0},
                    "black": {
                        "total_cost": 0.08589000000000013,
                        "model_1": {
                            "cost": 0.08589000000000013,
                            "prompt_tokens": 111510,
                            "completion_tokens": 20090,
                            "total_tokens": 131600,
                        },
                    },
                },
            }
        ),
        json.dumps(
            {
                "time_started": "2025.02.09_09:32",
                "winner": "Random_Player",
                "reason": "Too many wrong actions",
                "number_of_moves": 132,
                "player_white": {
                    "name": "Random_Player",
                    "wrong_moves": 0,
                    "wrong_actions": 0,
                    "reflections_used": 0,
                    "reflections_used_before_board": 0,
                    "model": "N/A",
                },
                "material_count": {"white": 21, "black": 4},
                "player_black": {
                    "name": "Player_Black",
                    "wrong_moves": 3,
                    "wrong_actions": 0,
                    "reflections_used": 0,
                    "reflections_used_before_board": 0,
                    "model": "model_1",
                },
                "usage_stats": {
                    "white": {"total_cost": 0},
                    "black": {
                        "total_cost": 0.055271500000000036,
                        "model_1": {
                            "cost": 0.055271500000000036,
                            "prompt_tokens": 73145,
                            "completion_tokens": 12466,
                            "total_tokens": 85611,
                        },
                    },
                },
            }
        ),
        json.dumps(
            {
                "time_started": "2025.02.09_09:33",
                "winner": "NONE",
                "reason": "Max moves reached",
                "number_of_moves": 200,
                "player_white": {
                    "name": "Random_Player",
                    "wrong_moves": 0,
                    "wrong_actions": 0,
                    "reflections_used": 0,
                    "reflections_used_before_board": 0,
                    "model": "N/A",
                },
                "material_count": {"white": 12, "black": 11},
                "player_black": {
                    "name": "Player_Black",
                    "wrong_moves": 0,
                    "wrong_actions": 0,
                    "reflections_used": 0,
                    "reflections_used_before_board": 0,
                    "model": "model_2",
                },
                "usage_stats": {
                    "white": {"total_cost": 0},
                    "black": {
                        "total_cost": 0.0822600000000002,
                        "model_2": {
                            "cost": 0.0822600000000002,
                            "prompt_tokens": 108030,
                            "completion_tokens": 18830,
                            "total_tokens": 126860,
                        },
                    },
                },
            }
        ),
        json.dumps(
            {
                "time_started": "2025.02.09_10:06",
                "winner": "Random_Player",
                "reason": "Too many wrong actions",
                "number_of_moves": 164,
                "player_white": {
                    "name": "Random_Player",
                    "wrong_moves": 0,
                    "wrong_actions": 0,
                    "reflections_used": 0,
                    "reflections_used_before_board": 0,
                    "model": "N/A",
                },
                "material_count": {"white": 12, "black": 16},
                "player_black": {
                    "name": "Player_Black",
                    "wrong_moves": 3,
                    "wrong_actions": 0,
                    "reflections_used": 0,
                    "reflections_used_before_board": 0,
                    "model": "model_2",
                },
                "usage_stats": {
                    "white": {"total_cost": 0},
                    "black": {
                        "total_cost": 0.065411,
                        "model_2": {
                            "cost": 0.065411,
                            "prompt_tokens": 88387,
                            "completion_tokens": 14145,
                            "total_tokens": 102532,
                        },
                    },
                },
            }
        ),
    ]


def write_mock_logs_to_temp_dir(logs, temp_dir):
    """Writes a list of mock JSON strings to files in a temporary directory."""
    for i, log in enumerate(logs):
        log_path = os.path.join(temp_dir, f"log_{i}.json")
        with open(log_path, "w") as f:
            f.write(log)


def read_csv_as_dict(csv_path):
    """Reads a CSV file and returns its contents as a list of dictionaries."""
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        return list(reader)


if __name__ == "__main__":
    unittest.main()
