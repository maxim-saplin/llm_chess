import unittest
import os
import csv
from data_processing.get_refined_csv import convert_aggregate_to_refined
from data_processing.aggregate_logs_to_csv import (
    aggregate_models_to_csv,
    MODEL_OVERRIDES,
)


class TestAggrToRefined(unittest.TestCase):
    def setUp(self):
        # Create mock log files and output CSV paths
        self.mock_logs_dir = "_mock_logs"
        self.mock_aggregate_csv = "mock_aggregate.csv"
        self.mock_refined_csv = "mock_refined.csv"

        # Create mock logs directory and files
        os.makedirs(self.mock_logs_dir, exist_ok=True)
        self.mock_log_files = [
            {
                "filename": "mock_log_1.json",
                "content": """{
                    "time_started": "2025.01.15_12:38",
                    "winner": "Random_Player",
                    "reason": "Too many wrong actions",
                    "number_of_moves": 6,
                    "player_white": {
                        "name": "Random_Player",
                        "wrong_moves": 0,
                        "wrong_actions": 0,
                        "reflections_used": 0,
                        "reflections_used_before_board": 0,
                        "get_board_count": 0,
                        "get_legal_moves_count": 0,
                        "make_move_count": 0,
                        "model": "N/A"
                    },
                    "material_count": {
                        "white": 39,
                        "black": 39
                    },
                    "player_black": {
                        "name": "Player_Black",
                        "wrong_moves": 3,
                        "wrong_actions": 0,
                        "reflections_used": 0,
                        "reflections_used_before_board": 0,
                        "get_board_count": 0,
                        "get_legal_moves_count": 0,
                        "make_move_count": 0,
                        "model": "internlm3-8b-instruct"
                    },
                    "usage_stats": {
                        "white": {
                            "total_cost": 0
                        },
                        "black": {
                            "total_cost": 0,
                            "internlm3-8b-instruct": {
                                "cost": 0,
                                "prompt_tokens": 5881,
                                "completion_tokens": 3489,
                                "total_tokens": 9370
                            }
                        }
                    }
                }""",
            },
            {
                "filename": "mock_log_2.json",
                "content": """{
                    "time_started": "2025.01.15_12:38",
                    "winner": "Random_Player",
                    "reason": "Too many wrong actions",
                    "number_of_moves": 6,
                    "player_white": {
                        "name": "Random_Player",
                        "wrong_moves": 0,
                        "wrong_actions": 0,
                        "reflections_used": 0,
                        "reflections_used_before_board": 0,
                        "get_board_count": 0,
                        "get_legal_moves_count": 0,
                        "make_move_count": 0,
                        "model": "N/A"
                    },
                    "material_count": {
                        "white": 39,
                        "black": 39
                    },
                    "player_black": {
                        "name": "Player_Black",
                        "wrong_moves": 3,
                        "wrong_actions": 0,
                        "reflections_used": 0,
                        "reflections_used_before_board": 0,
                        "get_board_count": 0,
                        "get_legal_moves_count": 0,
                        "make_move_count": 0,
                        "model": "llama3-8b"
                    },
                    "usage_stats": {
                        "white": {
                            "total_cost": 0
                        },
                        "black": {
                            "total_cost": 0,
                            "llama3-8b": {
                                "cost": 0,
                                "prompt_tokens": 5881,
                                "completion_tokens": 3489,
                                "total_tokens": 9370
                            }
                        }
                    }
                }""",
            },
        ]

        for log in self.mock_log_files:
            with open(
                os.path.join(self.mock_logs_dir, log["filename"]), "w"
            ) as log_file:
                log_file.write(log["content"])

    def tearDown(self):
        # Clean up mock files and directories
        if os.path.exists(self.mock_logs_dir):
            for file in os.listdir(self.mock_logs_dir):
                os.remove(os.path.join(self.mock_logs_dir, file))
            os.rmdir(self.mock_logs_dir)
        if os.path.exists(self.mock_aggregate_csv):
            os.remove(self.mock_aggregate_csv)
        if os.path.exists(self.mock_refined_csv):
            os.remove(self.mock_refined_csv)

    def test_propagation_to_refined_csv(self):
        # Generate aggregate CSV from mock logs
        aggregate_models_to_csv(
            self.mock_logs_dir, self.mock_aggregate_csv, MODEL_OVERRIDES
        )

        # Convert aggregate CSV to refined CSV
        convert_aggregate_to_refined(
            self.mock_aggregate_csv, self.mock_refined_csv, filter_out_below_n=0
        )

        # Read the refined CSV and validate the contents
        with open(self.mock_refined_csv, "r") as ref_file:
            reader = csv.DictReader(ref_file)
            rows = list(reader)

        # Ensure two rows are written (one for each mock log)
        self.assertEqual(len(rows), 2)

        # Validate the propagated values for the first row
        row_1 = rows[0]
        self.assertEqual(row_1["Player"], "internlm3-8b-instruct")
        self.assertEqual(int(row_1["total_games"]), 1)
        self.assertEqual(int(row_1["player_wins"]), 0)
        self.assertEqual(int(row_1["opponent_wins"]), 1)
        self.assertEqual(int(row_1["draws"]), 0)

        # Validate the propagated values for the second row
        row_2 = rows[1]
        self.assertEqual(row_2["Player"], "llama3-8b")
        self.assertEqual(int(row_2["total_games"]), 1)
        self.assertEqual(int(row_2["player_wins"]), 0)
        self.assertEqual(int(row_2["opponent_wins"]), 1)
        self.assertEqual(int(row_2["draws"]), 0)

    def test_win_loss_non_interrupted_propagation(self):
        """Tests that the new metrics are correctly propagated from aggregate to refined CSV."""
        # Generate aggregate CSV from mock logs
        aggregate_models_to_csv(
            self.mock_logs_dir, self.mock_aggregate_csv, MODEL_OVERRIDES
        )

        # Convert aggregate CSV to refined CSV
        convert_aggregate_to_refined(
            self.mock_aggregate_csv, self.mock_refined_csv, filter_out_below_n=0
        )

        # Read the refined CSV and validate the presence of new metrics
        with open(self.mock_refined_csv, "r") as ref_file:
            reader = csv.DictReader(ref_file)
            rows = list(reader)

        # Check that each row has the new metrics
        for row in rows:
            # Check win_loss_non_interrupted and related fields
            self.assertIn("win_loss_non_interrupted", row)
            self.assertIn("moe_win_loss_non_interrupted", row)
            
            # These metrics should all be present and have values
            self.assertIsNotNone(row["win_loss_non_interrupted"])
            self.assertIsNotNone(row["moe_win_loss_non_interrupted"])
            
            # Check games_not_interrupted and related fields
            self.assertIn("games_not_interrupted", row)
            self.assertIn("games_not_interrupted_percent", row)
            self.assertIn("moe_games_not_interrupted", row)
            
            # Since all mock logs are interrupted (reason = Too many wrong actions),
            # games_not_interrupted should be 0 and games_not_interrupted_percent should be 0
            self.assertEqual(int(row["games_not_interrupted"]), 0)
            self.assertEqual(float(row["games_not_interrupted_percent"]), 0.0)
            
            # Similarly, since all games are interrupted, win_loss_non_interrupted should be 0.5
            # (no wins or losses among non-interrupted games, just the default value)
            self.assertEqual(float(row["win_loss_non_interrupted"]), 0.5)

    def test_cost_metrics_propagation(self):
        """Tests that cost metrics are correctly propagated from aggregate to refined CSV."""
        # Generate aggregate CSV from mock logs
        aggregate_models_to_csv(
            self.mock_logs_dir, self.mock_aggregate_csv, MODEL_OVERRIDES
        )

        # Convert aggregate CSV to refined CSV
        convert_aggregate_to_refined(
            self.mock_aggregate_csv, self.mock_refined_csv, filter_out_below_n=0
        )

        # Read the refined CSV and validate the presence of cost metrics
        with open(self.mock_refined_csv, "r") as ref_file:
            reader = csv.DictReader(ref_file)
            rows = list(reader)

        # Check that each row has the cost metrics
        for row in rows:
            self.assertIn("average_game_cost", row)
            self.assertIn("moe_average_game_cost", row)
            
            # These metrics should be present with default values
            self.assertIsNotNone(row["average_game_cost"])
            self.assertIsNotNone(row["moe_average_game_cost"])

    def test_time_metrics_propagation(self):
        """Tests that measured time metrics are propagated to refined CSV."""
        aggregate_models_to_csv(
            self.mock_logs_dir, self.mock_aggregate_csv, MODEL_OVERRIDES
        )

        convert_aggregate_to_refined(
            self.mock_aggregate_csv, self.mock_refined_csv, filter_out_below_n=0
        )

        with open(self.mock_refined_csv, "r") as ref_file:
            reader = csv.DictReader(ref_file)
            rows = list(reader)

        for row in rows:
            self.assertIn("average_time_per_game_seconds", row)
            self.assertIn("moe_average_time_per_game_seconds", row)


if __name__ == "__main__":
    unittest.main() 