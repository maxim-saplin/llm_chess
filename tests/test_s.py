import unittest
import chess
import os
import csv
from utils import calculate_material_count, generate_game_stats
from data_processing.aggr_to_refined import convert_aggregate_to_refined
from data_processing.aggregate_logs_to_csv import (
    aggregate_models_to_csv,
    MODEL_OVERRIDES,
)


class TestMaterialCount(unittest.TestCase):
    def test_initial_position(self):
        board = chess.Board()
        white_material, black_material = calculate_material_count(board)
        self.assertEqual(
            white_material, 39
        )  # 8 pawns, 2 knights, 2 bishops, 2 rooks, 1 queen
        self.assertEqual(black_material, 39)

    def test_custom_position(self):
        board = chess.Board("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
        board.remove_piece_at(chess.E2)  # Remove a white pawn
        white_material, black_material = calculate_material_count(board)
        self.assertEqual(white_material, 38)
        self.assertEqual(black_material, 39)


class TestUtils(unittest.TestCase):
    def test_generate_game_stats(self):
        player_white = type(
            "Player",
            (object,),
            {
                "name": "White",
                "wrong_moves": 2,
                "wrong_actions": 1,
                "reflections_used": 0,
                "reflections_used_before_board": 0,
                "llm_config": {"config_list": [{"model": "test_model"}]},
            },
        )()

        player_black = type(
            "Player",
            (object,),
            {
                "name": "Black",
                "wrong_moves": 3,
                "wrong_actions": 2,
                "reflections_used": 0,
                "reflections_used_before_board": 0,
                "llm_config": {"config_list": [{"model": "test_model"}]},
            },
        )()

        material_count = {"white": 15, "black": 10}

        stats = generate_game_stats(
            "2024.10.07_12:00",
            "White",
            "Checkmate",
            40,
            player_white,
            player_black,
            material_count,
        )

        self.assertEqual(stats["winner"], "White")
        self.assertEqual(stats["reason"], "Checkmate")
        self.assertEqual(stats["number_of_moves"], 40)
        self.assertEqual(stats["player_white"]["wrong_moves"], 2)
        self.assertEqual(stats["player_black"]["wrong_moves"], 3)
        self.assertEqual(stats["material_count"]["white"], 15)
        self.assertEqual(stats["material_count"]["black"], 10)
        self.assertEqual(stats["player_white"]["model"], "test_model")
        self.assertEqual(stats["player_black"]["model"], "test_model")


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


if __name__ == "__main__":
    unittest.main()
