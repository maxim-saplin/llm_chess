import unittest
import chess
import os
import csv
from utils import calculate_material_count, generate_game_stats
from data_processing.get_refined_csv import convert_aggregate_to_refined
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
                "get_board_count": 0,
                "get_legal_moves_count": 0,
                "make_move_count": 0,
                "accumulated_reply_time": 1.25,
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
                "get_board_count": 0,
                "get_legal_moves_count": 0,
                "make_move_count": 0,
                "accumulated_reply_time": 1.75,
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
        self.assertEqual(stats["player_white"]["accumulated_reply_time"], 1.25)
        self.assertEqual(stats["player_black"]["accumulated_reply_time"], 1.75)

if __name__ == "__main__":
    unittest.main()
