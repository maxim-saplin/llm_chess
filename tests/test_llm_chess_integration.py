import re
import unittest
import multiprocessing
import json
import time
import os
import requests
import llm_chess 
import shutil
import tempfile
from llm_chess import (
    PlayerType,
    run,
    TerminationReason
)
from tests.mock_openai_server import start_server

# White player settings
os.environ["MODEL_KIND_W"] = "azure"
os.environ["AZURE_OPENAI_VERSION_W"] = "2024-02-15-preview"
os.environ["AZURE_OPENAI_ENDPOINT_W"] = "https://your-endpoint.openai.azure.com"
os.environ["AZURE_OPENAI_KEY_W"] = "your-azure-key"
os.environ["AZURE_OPENAI_DEPLOYMENT_W"] = "gpt-4o"

# Black player settings
os.environ["MODEL_KIND_B"] = "local"
os.environ["LOCAL_MODEL_NAME_B"] = "llama-3.1-70b"
os.environ["LOCAL_BASE_URL_B"] = "http://localhost:8000/v1"
os.environ["LOCAL_API_KEY_B"] = "your-local-key"

class TestRandomVsRandomGame(unittest.TestCase):
    def setUp(self):
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
        game_stats, player_white, player_black = run(log_dir=None)
        
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

        self.assertEqual(game_stats["reason"], TerminationReason.MAX_MOVES.value)


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
        cls.temp_dir = tempfile.mkdtemp(prefix="test_llm_chess_integration_")

    @classmethod
    def tearDownClass(cls):
        cls.server_process.terminate()
        cls.server_process.join()
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def setUp(self):
        # Reset the mock OpenAI server state before each test
        try:
            response = requests.post("http://localhost:8080/v1/reset", json={"scenarioType": "default", "useThinking": False}, timeout=5) # Add timeout
            response.raise_for_status() # Raise exception for bad status codes (4xx or 5xx)
            print(f"DEBUG: Reset response: {response.status_code} - {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"DEBUG: Failed to reset mock server: {e}")
        # Configure game settings for testing
        llm_chess.white_player_type = PlayerType.RANDOM_PLAYER
        llm_chess.black_player_type = PlayerType.LLM_BLACK
        llm_chess.max_game_moves = 10
        llm_chess.visualize_board = False
        llm_chess.throttle_delay = 0
        llm_chess.dialog_turn_delay = 0
        llm_chess.random_print_board = False

    def test_random_vs_mock_llm_game(self):
        game_stats, player_white, player_black = run(log_dir=None)
        
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
            game_stats, _, _ = run(log_dir=None)
            self.assertIsNotNone(game_stats["winner"])
            self.assertLessEqual(game_stats["number_of_moves"], 10)

    def test_remove_text_removes_think_tags(self):
        """Test that remove_text properly removes think tags during game."""

        requests.post("http://localhost:8080/v1/reset", json={"scenarioType": "default", "useThinking": True})
        
        # Configure game with remove_text

        llm_chess.max_game_moves = 3
        llm_chess.remove_text = r"<think>.*?</think>"
        
        # Run game
        _, _, black_player = run(log_dir=None)
        
        # Verify think tags were removed from all messages
        for msgs in black_player._oai_messages.values():
            for msg in msgs:
                self.assertNotIn("<think>", msg["content"])
                self.assertNotIn("</think>", msg["content"])
                self.assertNotIn("Thinking about my move", msg["content"])

    def test_preserve_think_tags_when_remove_text_disabled(self):
        """Test that think tags are preserved when remove_text is disabled."""
        
        requests.post("http://localhost:8080/v1/reset", json={"scenarioType": "default", "useThinking": True})
        
        # Configure game without remove_text
        llm_chess.white_player_type = PlayerType.RANDOM_PLAYER
        llm_chess.black_player_type = PlayerType.LLM_BLACK
        llm_chess.max_game_moves = 3
        llm_chess.remove_text = None
        
        # Run game
        _, _, black_player = run(log_dir=None)
        
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


    def test_pgn_board_representation_used(self):
        """Test that PGN board representation is used when configured."""

        # Configure game to use PGN board representation
        llm_chess.board_representation_mode = llm_chess.BoardRepresentation.UNICODE_WITH_PGN
        llm_chess.max_game_moves = 2

        # Run game
        _, _, black_player = run(log_dir=None)

        # Verify that the PGN board representation is present in the message log
        pgn_found = False
        for msgs in black_player._oai_messages.values():
            for msg in msgs:
                if "PGN:" in msg["content"]:
                    pgn_found = True
                    break
            if pgn_found:
                break

        self.assertTrue(pgn_found, "Expected PGN board representation in messages when configured.")

    def test_random_vs_llm_game_logging_and_stats(self):
        """
        Runs a short game (max 5 moves) between a random player (white) and LLM (black),
        checks that game_stats and the saved JSON log match.
        """
        llm_chess.max_game_moves = 6  # override for a short test
        game_stats, player_white, player_black = run(log_dir=self.temp_dir)
        self.assertIn("winner", game_stats)
        self.assertIn("reason", game_stats)
        self.assertLessEqual(game_stats["number_of_moves"], 6)

        log_filepath = os.path.join(self.temp_dir, f"{game_stats['time_started']}.json")
        self.assertTrue(os.path.exists(log_filepath), "Expected game result JSON not found.")
        with open(log_filepath, "r") as f:
            logged_stats = json.load(f)

        expected_stats = {
            "time_started": game_stats["time_started"],
            "winner": "NONE",
            "reason": "Max moves reached",
            "number_of_moves": 6,
            "player_white": {
                "name": "Random_Player",
                "wrong_moves": 0,
                "wrong_actions": 0,
                "reflections_used": 0,
                "reflections_used_before_board": 0,
                "get_board_count": 0,
                "get_legal_moves_count": 3,
                "make_move_count": 3,
                "accumulated_reply_time_seconds": round(player_white.accumulated_reply_time_seconds, 3),
                "model": "N/A"
            },
            "material_count": {
                "white": 39,
                "black": 39
            },
            "player_black": {
                "name": "Player_Black",
                "wrong_moves": 0,
                "wrong_actions": 0,
                "reflections_used": 0,
                "reflections_used_before_board": 0,
                "get_board_count": 3,
                "get_legal_moves_count": 3,
                "make_move_count": 3,
                "accumulated_reply_time_seconds": round(player_black.accumulated_reply_time_seconds, 3),
                "model": "gpt-3.5-turbo"
            },
            "usage_stats": {
                "white": {
                    "total_cost": 0
                },
                "black": {
                    "total_cost": 0,
                    "null": {
                        "cost": 0,
                        "prompt_tokens": 90,
                        "completion_tokens": 90,
                        "total_tokens": 180
                    }
                }
            },
            "pgn": game_stats["pgn"]
        }

        self.assertEqual(logged_stats, expected_stats)

    def test_proxy_prompts_are_not_changed(self):
        """
        Verify there're no surprises in how the proxy proimpts an LLM, any prompt changes must be changed in this test manually.
        """

        llm_chess.max_game_moves = 2
        requests.post("http://localhost:8080/v1/reset", json={"useNegative": False, "useThinking": False})

        _, _, black_player = run(log_dir=None)

        # Define valid prompt patterns
        valid_prompts = [
            r"You are a professional chess player and you play as black\. Now is your turn to make a move\.",
            r"([♜♞♝♛♚♝♞♜♟♙♖♘♗♕♔⭘\s]+)",  # Chess board pattern
            r"([a-h][1-8][a-h][1-8][qrbn]?,?)+",  # UCI moves list
            r"Move made, switching player"
        ]

        found_prompts = {prompt: False for prompt in valid_prompts}

        # Check prompts/error messages by the proxy are correct
        for msgs in black_player._oai_messages.values():
            for msg in msgs:
                for prompt in valid_prompts:
                    if re.match(prompt, msg["content"]):
                        found_prompts[prompt] = True

        for prompt, found in found_prompts.items():
            self.assertTrue(found, f"Expected prompt matching '{prompt}' not found.")

    def test_llm_illegal_move_and_invalid_action(self):
        """
        The mock server's first response is invalid_action,
        the second is an illegal move 'd4d5',
        then normal moves. Verify the proxy's error handling and stats.
        """

        llm_chess.max_game_moves = 2
        # Reset the server with the invalid_action scenario
        requests.post("http://localhost:8080/v1/reset", json={"scenarioType": "invalid_action", "useThinking": False})

        # Make sure we're using the default values for these parameters
        llm_chess.max_failed_attempts = 3
        llm_chess.max_llm_turns = 10

        game_stats, _, black_player = run(log_dir=None)

        # Debug output to help diagnose the issue
        print(f"Debug - wrong_actions: {black_player.wrong_actions}, wrong_moves: {black_player.wrong_moves}")
        print(f"Debug - game stats: {game_stats['player_black']}")

        # We expect exactly one wrong action and one wrong move in the LLM stats
        self.assertEqual(game_stats["player_black"]["wrong_actions"], 1)
        self.assertEqual(black_player.wrong_actions, 1)
        self.assertEqual(game_stats["player_black"]["wrong_moves"], 1)
        self.assertEqual(black_player.wrong_moves, 1)

        foundWrongActionPrompt = False
        foundIllegalMovePrompt = False
        # Check prompts/error messages by the proxy are correct

        for msgs in black_player._oai_messages.values():
            for msg in msgs:
                if msg["content"] == "Invalid action. Pick one, reply exactly with the name and space delimitted argument: get_current_board, get_legal_moves, make_move <UCI formatted move>":
                    foundWrongActionPrompt = True
                if re.match(r"Failed to make move: illegal uci: 'd4d5' in .*?", msg["content"]):
                    foundIllegalMovePrompt = True
        
        self.assertTrue(foundWrongActionPrompt, "Expected wrong action response/prompt not found.")
        self.assertTrue(foundIllegalMovePrompt, "Expected illegal move response/prompt not found.")

    def test_too_many_wrong_actions(self):
        """
        Test that the game ends with TOO_MANY_WRONG_ACTIONS when the LLM consistently
        provides invalid responses.
        """
        llm_chess.max_game_moves = 100  # Set higher to ensure we hit wrong actions first
        llm_chess.max_failed_attempts = 3
        llm_chess.max_llm_turns = 20  # Set higher to ensure we hit wrong actions first
        requests.post("http://localhost:8080/v1/reset", json={"scenarioType": "wrong_actions"})

        game_stats, _, black_player = run(log_dir=None)

        # Verify the game ended due to too many wrong actions
        self.assertEqual(game_stats["reason"], TerminationReason.TOO_MANY_WRONG_ACTIONS.value)
        self.assertEqual(game_stats["winner"], "Random_Player")  # White player should win
        self.assertEqual(black_player.wrong_actions, 3)  # Should have 3 wrong actions

    def test_max_turns_in_dialog(self):
        """
        Test that the game ends with MAX_TURNS when the LLM keeps requesting the board
        without making a move, hitting the max_llm_turns limit.
        """
        llm_chess.max_game_moves = 100  # Set higher to ensure we hit max turns first
        llm_chess.max_llm_turns = 5  # Set a low value to trigger quickly
        requests.post("http://localhost:8080/v1/reset", json={"scenarioType": "max_turns"})

        game_stats, _, _ = run(log_dir=None)

        # Verify the game ended due to max turns in a dialog
        self.assertEqual(game_stats["reason"], TerminationReason.MAX_TURNS.value)
        self.assertEqual(game_stats["winner"], "Random_Player")  # White player should win

    def test_max_moves_reached(self):
        """
        Test that the game ends with MAX_MOVES when the maximum number of moves is reached.
        """
        llm_chess.max_game_moves = 4 
        requests.post("http://localhost:8080/v1/reset", json={"scenarioType": "max_moves"})

        game_stats, _, _ = run(log_dir=None)
        self.assertEqual(game_stats["reason"], TerminationReason.MAX_MOVES.value)
        self.assertEqual(game_stats["winner"], "NONE") 
        self.assertEqual(game_stats["number_of_moves"], 4) 

        # Verify odd number of moves
        llm_chess.max_game_moves = 3
        game_stats, _, _ = run(log_dir=None)
        self.assertEqual(game_stats["reason"], TerminationReason.MAX_MOVES.value)
        self.assertEqual(game_stats["winner"], "NONE") 
        self.assertEqual(game_stats["number_of_moves"], 3) 


class TestBoardRepresentationIntegration(unittest.TestCase):
    def setUp(self):
        self.original_mode = llm_chess.board_representation_mode
        llm_chess.board.reset()
        llm_chess.game_moves.clear()

    def tearDown(self):
        llm_chess.board_representation_mode = self.original_mode

    def test_fen_only_mode(self):
        llm_chess.board_representation_mode = llm_chess.BoardRepresentation.FEN_ONLY
        actual = llm_chess.get_current_board()
        self.assertEqual(
            actual,
            llm_chess.board.fen(),
            "When BoardRepresentation.FEN_ONLY, get_current_board() should match board.fen()."
        )

    def test_unicode_only_mode(self):
        llm_chess.board_representation_mode = llm_chess.BoardRepresentation.UNICODE_ONLY
        move = llm_chess.chess.Move.from_uci("e2e4")
        llm_chess.board.push(move)
        self.assertEqual(
            llm_chess.get_current_board(),
            llm_chess.board.unicode(),
            "When BoardRepresentation.UNICODE_ONLY, get_current_board() should match board.unicode()."
        )

    def test_unicode_with_pgn_mode(self):
        llm_chess.board_representation_mode = llm_chess.BoardRepresentation.UNICODE_WITH_PGN
        move = llm_chess.chess.Move.from_uci("e2e4")
        san = llm_chess.board.san(move)
        llm_chess.board.push(move)
        llm_chess.game_moves.append(san)
        output = llm_chess.get_current_board()
        self.assertIn(llm_chess.board.unicode(), output, "Should include a unicode board representation.")
        self.assertIn("[Event \"Chess Game\"]", output, "Should include the PGN header.")
        self.assertIn("1. e4", output, "Should include the SAN move in the PGN portion.")


class TestRandomVsStockfishGame(unittest.TestCase):
    """
    TestRandomVsStockfishGame tests the integration of a random player against the Stockfish chess engine.
    This test requires Stockfish to be installed and accessible at the specified path in llm_chess.py.

    Quick install on WSL (using default path used by the engine):
    ```
    cd ~
    wget https://github.com/official-stockfish/Stockfish/releases/latest/download/stockfish-ubuntu-x86-64-avx2.tar
    tar -xvf stockfish-ubuntu-x86-64-avx2.tar
    sudo mkdir -p /opt/homebrew/bin
    sudo cp stockfish/stockfish-ubuntu-x86-64-avx2 /opt/homebrew/bin/stockfish
    ```
    """
    def setUp(self):
        llm_chess.white_player_type = PlayerType.RANDOM_PLAYER
        llm_chess.black_player_type = PlayerType.CHESS_ENGINE_STOCKFISH
        llm_chess.stockfish_level = 20
        llm_chess.max_game_moves = 50 
        llm_chess.visualize_board = False
        llm_chess.throttle_delay = 0
        llm_chess.dialog_turn_delay = 0
        llm_chess.random_print_board = False

    def test_game(self):
        game_stats, player_white, player_black = run(log_dir=None)
        
        # Basic game completion checks
        self.assertIsNotNone(game_stats)
        self.assertIsNotNone(game_stats["winner"])
        self.assertIsNotNone(game_stats["reason"])
        
        # Verify number of moves is 10 or less (could be less if game ended earlier)
        self.assertLessEqual(game_stats["number_of_moves"], 50)
        
        self.assertEqual(player_white.name, "Random_Player")
        self.assertEqual(player_black.name, "Chess_Engine_Stockfish_Black")
        
        self.assertEqual(game_stats["player_white"]["wrong_moves"], 0)
        self.assertEqual(game_stats["player_white"]["wrong_actions"], 0)
        self.assertEqual(game_stats["player_black"]["wrong_moves"], 0)
        self.assertEqual(game_stats["player_black"]["wrong_actions"], 0)

        self.assertGreater(game_stats["material_count"]["black"], game_stats["material_count"]["white"])

        self.assertEqual(game_stats["reason"] , TerminationReason.CHECKMATE.value)

if __name__ == "__main__":
    unittest.main()
