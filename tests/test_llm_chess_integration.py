import unittest
import chess
from llm_chess import (
    PlayerType,
    run,
    TerminationReason
)

class TestRandomVsRandomGame(unittest.TestCase):
    def setUp(self):
        # Configure game settings for testing
        import llm_chess
        # Override global variables for testing
        llm_chess.white_player_type = PlayerType.RANDOM_PLAYER
        llm_chess.black_player_type = PlayerType.RANDOM_PLAYER
        llm_chess.max_game_moves = 10  # Test exactly 10 turns
        llm_chess.visualize_board = False  # Disable visualization
        llm_chess.throttle_delay = 0  # No delays needed for testing
        llm_chess.dialog_turn_delay = 0
        llm_chess.random_print_board = False

    def test_ten_turn_game(self):
        # Run a 10-turn game
        game_stats, player_white, player_black = run(save_logs=False)
        
        # Basic game completion checks
        self.assertIsNotNone(game_stats)
        self.assertIsNotNone(game_stats["winner"])
        self.assertIsNotNone(game_stats["reason"])
        
        # Verify number of moves is 10 or less (could be less if game ended earlier)
        self.assertLessEqual(game_stats["number_of_moves"], 10)
        
        # Verify players were correctly initialized
        self.assertEqual(player_white.name, "Random_Player")
        self.assertEqual(player_black.name, "Random_Player")
        
        # Verify no wrong moves or actions (random player should always make valid moves)
        self.assertEqual(game_stats["player_white"]["wrong_moves"], 0)
        self.assertEqual(game_stats["player_white"]["wrong_actions"], 0)
        self.assertEqual(game_stats["player_black"]["wrong_moves"], 0)
        self.assertEqual(game_stats["player_black"]["wrong_actions"], 0)

        # Verify material counts are valid
        self.assertLessEqual(game_stats["material_count"]["white"], 39)
        self.assertLessEqual(game_stats["material_count"]["black"], 39)
        self.assertGreaterEqual(game_stats["material_count"]["white"], 0)
        self.assertGreaterEqual(game_stats["material_count"]["black"], 0)

        # If game ended due to max moves, verify it was exactly 10 moves
        if game_stats["reason"] == TerminationReason.MAX_MOVES.value:
            self.assertEqual(game_stats["number_of_moves"], 10)

if __name__ == "__main__":
    unittest.main()
