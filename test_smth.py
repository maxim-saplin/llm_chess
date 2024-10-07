import unittest
import chess
from utils import calculate_material_count, generate_game_stats


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
                "material_count": 15,
                "llm_config": {"model": "test_model"},
            },
        )()

        player_black = type(
            "Player",
            (object,),
            {
                "name": "Black",
                "wrong_moves": 3,
                "wrong_actions": 2,
                "material_count": 10,
                "llm_config": {"model": "test_model"},
            },
        )()

        stats = generate_game_stats(
            "2024.10.07_12:00",
            "White",
            "Checkmate",
            40,
            player_white,
            player_black,
            player_white.llm_config,
            player_black.llm_config,
        )

        self.assertEqual(stats["winner"], "White")
        self.assertEqual(stats["reason"], "Checkmate")
        self.assertEqual(stats["number_of_moves"], 40)
        self.assertEqual(stats["player_white"]["wrong_moves"], 2)
        self.assertEqual(stats["player_black"]["wrong_moves"], 3)


if __name__ == "__main__":
    unittest.main()
