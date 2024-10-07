import unittest
import chess
from utils import calculate_material_count


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


if __name__ == "__main__":
    unittest.main()
