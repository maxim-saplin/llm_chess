import unittest
import multiprocessing
import time
import os
from llm_chess import (
    PlayerType,
    run,
    TerminationReason
)
from tests.mock_openai_server import start_server

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


class TestLLMvsRandomGame(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Start mock OpenAI server in a separate process
        cls.server_process = multiprocessing.Process(target=start_server, args=(8080,))
        cls.server_process.start()
        time.sleep(2)  # Wait for server to start
        
        # Configure environment for local OpenAI-compatible endpoint
        os.environ["MODEL_KIND_B"] = "local"
        os.environ["LOCAL_MODEL_NAME_B"] = "gpt-3.5-turbo"
        os.environ["LOCAL_BASE_URL_B"] = "http://localhost:8080/v1"
        os.environ["LOCAL_API_KEY_B"] = "mock-key"

    @classmethod
    def tearDownClass(cls):
        cls.server_process.terminate()
        cls.server_process.join()

    def setUp(self):
        # Configure game settings for testing
        import llm_chess
        llm_chess.white_player_type = PlayerType.RANDOM_PLAYER
        llm_chess.black_player_type = PlayerType.LLM_BLACK
        llm_chess.max_game_moves = 10
        llm_chess.visualize_board = False
        llm_chess.throttle_delay = 0
        llm_chess.dialog_turn_delay = 0
        llm_chess.random_print_board = False

    def test_random_vs_mock_llm_game(self):
        game_stats, player_white, player_black = run(save_logs=False)
        
        # Verify game completed
        self.assertIsNotNone(game_stats["winner"])
        self.assertIsNotNone(game_stats["reason"])
        self.assertLessEqual(game_stats["number_of_moves"], 10)
        
        # Verify players
        self.assertEqual(player_white.name, "Random_Player")
        self.assertEqual(player_black.name, "Player_Black")
        
        # Verify no errors in moves
        self.assertEqual(game_stats["player_white"]["wrong_moves"], 0)
        self.assertEqual(game_stats["player_white"]["wrong_actions"], 0)
        self.assertEqual(game_stats["player_black"]["wrong_moves"], 0)
        self.assertEqual(game_stats["player_black"]["wrong_actions"], 0)

        # Verify material counts are valid
        self.assertLessEqual(game_stats["material_count"]["white"], 39)
        self.assertLessEqual(game_stats["material_count"]["black"], 39)
        self.assertGreaterEqual(game_stats["material_count"]["white"], 0)
        self.assertGreaterEqual(game_stats["material_count"]["black"], 0)

    def test_multiple_games(self):
        # Run multiple games to ensure stability
        for _ in range(3):
            game_stats, _, _ = run(save_logs=False)
            self.assertIsNotNone(game_stats["winner"])
            self.assertLessEqual(game_stats["number_of_moves"], 10)

    def test_remove_text_removes_think_tags(self):
        """Test that remove_text properly removes think tags during game."""
        import llm_chess
        import requests
        
        # Enable think tags in mock server
        requests.post("http://localhost:8080/v1/config/think_tags/true")
        
        # Configure game with remove_text
        llm_chess.white_player_type = PlayerType.RANDOM_PLAYER
        llm_chess.black_player_type = PlayerType.LLM_BLACK
        llm_chess.max_game_moves = 3
        llm_chess.visualize_board = False
        llm_chess.throttle_delay = 0
        llm_chess.dialog_turn_delay = 0
        llm_chess.remove_text = r"<think>.*?</think>"
        
        # Run game
        _, _, black_player = run(save_logs=False)
        
        # Verify think tags were removed from all messages
        for msgs in black_player._oai_messages.values():
            for msg in msgs:
                self.assertNotIn("<think>", msg["content"])
                self.assertNotIn("</think>", msg["content"])
                self.assertNotIn("Thinking about my move", msg["content"])

    def test_preserve_think_tags_when_remove_text_disabled(self):
        """Test that think tags are preserved when remove_text is disabled."""
        import llm_chess
        import requests
        
        # Enable think tags in mock server
        requests.post("http://localhost:8080/v1/config/think_tags/true")
        
        # Configure game without remove_text
        llm_chess.white_player_type = PlayerType.RANDOM_PLAYER
        llm_chess.black_player_type = PlayerType.LLM_BLACK
        llm_chess.max_game_moves = 3
        llm_chess.visualize_board = False
        llm_chess.throttle_delay = 0
        llm_chess.dialog_turn_delay = 0
        llm_chess.remove_text = None
        
        # Run game
        _, _, black_player = run(save_logs=False)
        
        # Verify at least one message contains think tags
        found_think_tags = False
        for msgs in black_player._oai_messages.values():
            for msg in msgs:
                if "<think>" in msg["content"] and "</think>" in msg["content"]:
                    found_think_tags = True
                    self.assertIn("Thinking about my move", msg["content"])
                    break
            if found_think_tags:
                break
        
        self.assertTrue(found_think_tags, "Expected to find think tags in messages when remove_text is disabled")


if __name__ == "__main__":
    unittest.main()
