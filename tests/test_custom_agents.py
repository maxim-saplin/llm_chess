import unittest
import llm_chess
import chess
from custom_agents import GameAgent, RandomPlayerAgent, AutoReplyAgent, ChessEngineStockfishAgent
from utils import generate_game_stats
import time
from unittest.mock import patch

class TestCustomAgents(unittest.TestCase):
    def test_game_agent_initialization(self):
        agent = GameAgent(name="TestAgent", dialog_turn_delay=2)
        self.assertEqual(agent.name, "TestAgent")
        self.assertEqual(agent.dialog_turn_delay, 2)
        self.assertEqual(agent.wrong_moves, 0)
        self.assertEqual(agent.wrong_actions, 0)

    def test_random_player_agent_initialization(self):
        agent = RandomPlayerAgent(
            name="RandomAgent",
            make_move_action="make_move",
            get_legal_moves_action="get_legal_moves",
            get_current_board_action="get_current_board",
        )
        self.assertEqual(agent.name, "RandomAgent")
        self.assertEqual(agent.make_move_action, "make_move")
        self.assertEqual(agent.get_legal_moves_action, "get_legal_moves")
        self.assertEqual(agent.get_current_board_action, "get_current_board")

    def test_auto_reply_agent_initialization(self):
        agent = AutoReplyAgent(
            name="AutoReplyAgent",
            get_current_board=lambda: "board_state",
            get_legal_moves=lambda: "legal_moves",
            make_move=lambda move: None,
            move_was_made_message="Move made",
            invalid_action_message="Invalid action. Pick one, reply exactly with the name and space delimitted argument: get_current_board, get_legal_moves, make_move <UCI formatted move>",
            too_many_failed_actions_message="Too many failed actions",
            max_failed_attempts=3,
            get_current_board_action="get_current_board",
            get_legal_moves_action="get_legal_moves",
            reflect_action="reflect",
            make_move_action="make_move",
            reflect_prompt="Reflecting...",
            reflection_followup_prompt="Follow-up reflection",
            remove_text=None,
        )
        self.assertEqual(agent.name, "AutoReplyAgent")
        self.assertEqual(agent.max_failed_attempts, 3)
        self.assertEqual(agent.move_was_made, "Move made")
        self.assertEqual(agent.invalid_action_message, "Invalid action. Pick one, reply exactly with the name and space delimitted argument: get_current_board, get_legal_moves, make_move <UCI formatted move>")

    def test_chess_engine_stockfish_agent_initialization(self):
        board = chess.Board()
        agent = ChessEngineStockfishAgent(
            name="StockfishAgent",
            board=board,
            make_move_action="make_move",
            stockfish_path="/path/to/stockfish",
            time_limit=0.1,
            level=5,
        )
        self.assertEqual(agent.name, "StockfishAgent")
        self.assertEqual(agent.board, board)
        self.assertEqual(agent.make_move_action, "make_move")
        self.assertEqual(agent.stockfish_path, "/path/to/stockfish")
        self.assertEqual(agent.time_limit, 0.1)
        self.assertEqual(agent.level, 5)

    def test_game_stats_includes_action_counters(self):
        agent_white = GameAgent(name="WhiteAgent")
        agent_black = GameAgent(name="BlackAgent")

        # Simulate some increments
        agent_white.get_board_count = 2
        agent_white.get_legal_moves_count = 1
        agent_white.make_move_count = 3
        agent_white.reflections_used = 1
        agent_white.reflections_used_before_board = 0
        agent_black.get_board_count = 5
        agent_black.get_legal_moves_count = 6
        agent_black.make_move_count = 7
        agent_black.reflections_used = 2
        agent_black.reflections_used_before_board = 1

        game_stats = generate_game_stats(
            time_started="2025.03.16_22:18",
            winner="WhiteAgent",
            reason="Checkmate",
            current_move=10,
            player_white=agent_white,
            player_black=agent_black,
            material_count={"white": 39, "black": 38},
            pgn_string=""
        )

        # Check JSON for counters
        self.assertEqual(game_stats["player_white"]["get_board_count"], 2)
        self.assertEqual(game_stats["player_white"]["get_legal_moves_count"], 1)
        self.assertEqual(game_stats["player_white"]["make_move_count"], 3)
        self.assertEqual(game_stats["player_white"]["reflections_used"], 1)
        self.assertEqual(game_stats["player_white"]["reflections_used_before_board"], 0)
        self.assertEqual(game_stats["player_black"]["get_board_count"], 5)
        self.assertEqual(game_stats["player_black"]["get_legal_moves_count"], 6)
        self.assertEqual(game_stats["player_black"]["make_move_count"], 7)
        self.assertEqual(game_stats["player_black"]["reflections_used"], 2)
        self.assertEqual(game_stats["player_black"]["reflections_used_before_board"], 1)

class TestRandomPlayerAgentLogic(unittest.TestCase):
    def setUp(self):
        """Set up a RandomPlayerAgent instance for testing."""
        self.agent = RandomPlayerAgent(
            name="RandomAgent",
            make_move_action="make_move",
            get_legal_moves_action="get_legal_moves",
            get_current_board_action="get_current_board",
        )

    def test_initialization(self):
        """Test that the agent initializes with the correct attributes."""
        self.assertEqual(self.agent.name, "RandomAgent")
        self.assertEqual(self.agent.make_move_action, "make_move")
        self.assertEqual(self.agent.get_legal_moves_action, "get_legal_moves")
        self.assertEqual(self.agent.get_current_board_action, "get_current_board")
        self.assertTrue(self.agent.flip_flag)

    def test_select_legal_move(self):
        """Test that the agent selects a move from the provided legal moves."""
        self.agent.flip_flag = False  # Ensure the agent is ready to make a move
        messages = [{"content": "e2e4,e7e5,g1f3"}]
        reply = self.agent.generate_reply(messages=messages)
        self.assertTrue(reply.startswith("make_move"))
        move = reply.split(" ")[1]
        self.assertIn(move, ["e2e4", "e7e5", "g1f3"])

    def test_invalid_input_requests_legal_moves(self):
        """Test that the agent requests legal moves again if the input is invalid."""
        self.agent.flip_flag = False  # Ensure the agent is not requesting the board
        messages = [{"content": "invalid_move"}]
        reply = self.agent.generate_reply(messages=messages)
        self.assertEqual(reply, "get_legal_moves")

    def test_empty_input_requests_legal_moves(self):
        """Test that the agent requests legal moves again if the input is empty."""
        self.agent.flip_flag = False  # Ensure the agent is not requesting the board
        messages = [{"content": ""}]
        reply = self.agent.generate_reply(messages=messages)
        self.assertEqual(reply, "get_legal_moves")

    def test_request_board_before_move(self):
        """Test that the agent requests the board state before making a move."""
        self.agent.flip_flag = True  # Ensure the flag is set to request the board
        messages = [{"content": "e2e4,e7e5,g1f3"}]
        reply = self.agent.generate_reply(messages=messages)
        self.assertEqual(reply, "get_current_board")
        self.assertFalse(self.agent.flip_flag)  # Ensure the flag toggles

    def test_flip_flag_behavior(self):
        """Test that the flip_flag toggles correctly."""
        self.agent.flip_flag = True
        messages = [{"content": "e2e4,e7e5,g1f3"}]
        reply = self.agent.generate_reply(messages=messages)
        self.assertEqual(reply, "get_current_board")
        self.assertFalse(self.agent.flip_flag)

        # Simulate the next call where the agent should make a move
        reply = self.agent.generate_reply(messages=messages)
        self.assertTrue(reply.startswith("make_move"))
        self.assertTrue(self.agent.flip_flag)  # Ensure the flag toggles back


class TestAutoReplyAgent(unittest.TestCase):
    def setUp(self):
        """Set up a basic AutoReplyAgent for testing."""
        self.board = chess.Board()
        
        # Mock functions for testing
        self.get_current_board = lambda: "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        self.get_legal_moves = lambda: "e2e4,d2d4,g1f3"
        
        def mock_make_move(move):
            if move == "e9e9":  # Invalid move
                raise ValueError("Invalid move")
        
        self.make_move = mock_make_move
        
        # Create a mock sender (GameAgent) for testing
        self.mock_sender = GameAgent(
            name="MockPlayer"
        )
        # Initialize reflection counters used by AutoReplyAgent
        self.mock_sender.reflections_used = 0
        self.mock_sender.reflections_used_before_board = 0
        
        self.agent = AutoReplyAgent(
            name="TestAutoReply",
            get_current_board=self.get_current_board,
            get_legal_moves=self.get_legal_moves,
            make_move=self.make_move,
            move_was_made_message="Move made",
            invalid_action_message="Invalid action. Pick one, reply exactly with the name and space delimitted argument: get_current_board, get_legal_moves, make_move <UCI formatted move>",
            too_many_failed_actions_message="Too many failed actions",
            max_failed_attempts=3,
            get_current_board_action="get_current_board",
            get_legal_moves_action="get_legal_moves",
            reflect_action="reflect",
            make_move_action="make_move",
            reflect_prompt="Reflecting...",
            reflection_followup_prompt="Follow-up reflection",
            remove_text=None
        )

    def test_get_current_board(self):
        """Test requesting current board state."""
        messages = [
            {"content": "You are a random chess player."},
            {"content": "get_current_board"}
            ]
        reply = self.agent.generate_reply(messages=messages, sender=self.mock_sender)
        self.assertEqual(reply, self.get_current_board())
        self.assertTrue(self.mock_sender.has_requested_board)

    def test_get_legal_moves(self):
        """Test requesting legal moves."""
        messages = [
            {"content": "You are a random chess player."},
            {"content": "get_legal_moves"}]
        reply = self.agent.generate_reply(messages=messages, sender=self.mock_sender)
        self.assertEqual(reply, self.get_legal_moves())
        self.assertTrue(self.mock_sender.has_requested_board)
    
    def test_remove_text_functionality(self):
        """Test that remove_text pattern properly modifies message history."""
        agent_with_remove = AutoReplyAgent(
            name="TestAutoReply",
            get_current_board=self.get_current_board,
            get_legal_moves=self.get_legal_moves,
            make_move=self.make_move,
            move_was_made_message="Move made",
            invalid_action_message="Invalid action. Pick one, reply exactly with the name and space delimitted argument: get_current_board, get_legal_moves, make_move <UCI formatted move>",
            too_many_failed_actions_message="Too many failed actions",
            max_failed_attempts=3,
            get_current_board_action="get_current_board",
            get_legal_moves_action="get_legal_moves",
            reflect_action="reflect",
            make_move_action="make_move",
            reflect_prompt="Reflecting...",
            reflection_followup_prompt="Follow-up reflection",
            remove_text=r"<think>.*?</think>"
        )
        
        # Test with remove_text enabled
        messages = [
            {"content": "<think>some thinking</think>make_move e2e4"},
            {"content": "<think>more thinking</think>get_legal_moves"}
        ]
        original_messages = messages.copy()
        
        agent_with_remove.generate_reply(messages=messages, sender=self.mock_sender)
        
        # Check that messages were modified
        self.assertEqual(messages[0]["content"], "make_move e2e4")
        self.assertEqual(messages[1]["content"], "get_legal_moves")
        
        # Test with remove_text disabled
        agent_without_remove = AutoReplyAgent(
            name="TestAutoReply",
            get_current_board=self.get_current_board,
            get_legal_moves=self.get_legal_moves,
            make_move=self.make_move,
            move_was_made_message="Move made",
            invalid_action_message="Invalid action",
            too_many_failed_actions_message="Too many failed actions",
            max_failed_attempts=3,
            get_current_board_action="get_current_board",
            get_legal_moves_action="get_legal_moves",
            reflect_action="reflect",
            make_move_action="make_move",
            reflect_prompt="Reflecting...",
            reflection_followup_prompt="Follow-up reflection",
            remove_text=None
        )
        
        messages = original_messages.copy()
        agent_without_remove.generate_reply(messages=messages, sender=self.mock_sender)
        
        # Check that messages were not modified
        self.assertEqual(messages[0]["content"], original_messages[0]["content"])
        self.assertEqual(messages[1]["content"], original_messages[1]["content"])

    def test_default_remove_text_regex_covers_known_cases(self):
        """Default remove regex should strip everything up to known closing tags.
        Covers: </think>, ◁/think▷, </reasoning>, and no-op when no tags."""
        agent = AutoReplyAgent(
            name="TestAutoReplyDefaultRegex",
            get_current_board=self.get_current_board,
            get_legal_moves=self.get_legal_moves,
            make_move=self.make_move,
            move_was_made_message="Move made",
            invalid_action_message="Invalid action",
            too_many_failed_actions_message="Too many failed actions",
            max_failed_attempts=3,
            get_current_board_action="get_current_board",
            get_legal_moves_action="get_legal_moves",
            reflect_action="reflect",
            make_move_action="make_move",
            reflect_prompt="Reflecting...",
            reflection_followup_prompt="Follow-up reflection",
            remove_text=llm_chess.DEFAULT_REMOVE_TEXT_REGEX,
        )

        scenarios = [
            {"inp": "<think>some internal\nstuff</think>\nmake_move e2e4", "exp": "make_move e2e4"},
            {"inp": "garbage preface\n</think>\nget_current_board", "exp": "get_current_board"},
            {"inp": "◁think▷ tokens ... ◁/think▷\nget_legal_moves", "exp": "get_legal_moves"},
            {"inp": "random preface\n◁/think▷\nreflect", "exp": "reflect"},
            {"inp": "<reasoning>analysis...</reasoning>\nmake_move a2a4", "exp": "make_move a2a4"},
            {"inp": "No tags here\nget_legal_moves", "exp": "No tags here\nget_legal_moves"},
        ]

        for case in scenarios:
            with self.subTest(inp=case["inp"]):
                msgs = [{"content": case["inp"]}]
                # Trigger cleaning
                _ = agent.generate_reply(messages=msgs, sender=self.mock_sender)
                self.assertEqual(msgs[0]["content"], case["exp"])

    def test_make_move_valid(self):
        """Test making a valid move."""
        messages = [{"content": "make_move e2e4"}]
        reply = self.agent.generate_reply(messages=messages, sender=self.mock_sender)
        self.assertEqual(reply, "Move made")
        self.assertEqual(self.mock_sender.wrong_moves, 0)
        self.assertEqual(self.mock_sender.wrong_actions, 0)

    def test_make_move_invalid(self):
        """Test making an invalid move."""
        messages = [{"content": "make_move e9e9"}]  # Invalid move
        reply = self.agent.generate_reply(messages=messages, sender=self.mock_sender)
        self.assertTrue(reply.startswith("Failed to make move:"))
        self.assertEqual(self.mock_sender.wrong_moves, 1)
        self.assertEqual(self.mock_sender.failed_action_attempts, 1)

    def test_make_move_illegal_d4d5(self):
        """
        Test scenario for an illegal move 'd4d5' from a custom FEN,
        verifying the full returned message matches exactly.
        """
        self.board.set_fen("r1bqkbnr/pppppppp/4B3/8/3n4/3P2P1/PPP1PP1P/RNBQK1NR b KQkq - 2 5")
        
        def mock_make_move(move):
            if move == "d4d5":
                raise ValueError(f"illegal uci: 'd4d5' in {self.board.fen()}")

        self.agent.make_move = mock_make_move
        messages = [{"content": "make_move d4d5"}]
        reply = self.agent.generate_reply(messages=messages, sender=self.mock_sender)
        expected_reply = f"Failed to make move: illegal uci: 'd4d5' in {self.board.fen()}"
        self.assertEqual(reply, expected_reply)
        self.assertEqual(self.mock_sender.wrong_moves, 1)
        self.assertEqual(self.mock_sender.failed_action_attempts, 1)

    def test_invalid_action_format(self):
        """Test handling of incorrectly formatted actions."""
        messages = [{"content": "message_with_invalid_action"}]
        reply = self.agent.generate_reply(messages=messages, sender=self.mock_sender)
        expected_reply = "Invalid action. Pick one, reply exactly with the name and space delimitted argument: get_current_board, get_legal_moves, make_move <UCI formatted move>"
        self.assertEqual(reply, expected_reply)
        self.assertEqual(self.mock_sender.wrong_actions, 1)
        self.assertEqual(self.mock_sender.failed_action_attempts, 1)


    def test_max_failed_attempts(self):
        """Test that agent stops after reaching max failed attempts."""
        self.mock_sender.failed_action_attempts = self.agent.max_failed_attempts - 1
        messages = [{"content": "message_with_invalid_action"}]
        reply = self.agent.generate_reply(messages=messages, sender=self.mock_sender)
        self.assertEqual(reply, self.agent.too_many_failed_actions_message)

    def test_prep_to_move(self):
        """Test resetting of state variables before each move."""
        self.agent.failed_action_attempts = 2
        self.mock_sender.wrong_moves = 3
        self.mock_sender.wrong_actions = 2
        self.mock_sender.has_requested_board = True
        
        self.agent.prep_to_move()
        self.mock_sender.prep_to_move()
        
        self.assertEqual(self.agent.failed_action_attempts, 0)
        self.assertFalse(self.mock_sender.has_requested_board)

    def test_auto_reply_action_counters(self):
        # Check get_current_board increments sender counter
        messages = [{"content": "get_current_board"}]
        _ = self.agent.generate_reply(messages=messages, sender=self.mock_sender)
        self.assertEqual(self.mock_sender.get_board_count, 1)

        # Check get_legal_moves increments sender counter
        messages = [{"content": "get_legal_moves"}]
        _ = self.agent.generate_reply(messages=messages, sender=self.mock_sender)
        self.assertEqual(self.mock_sender.get_legal_moves_count, 1)

        # Check make_move increments sender counter
        messages = [{"content": "make_move e2e4"}]
        _ = self.agent.generate_reply(messages=messages, sender=self.mock_sender)
        self.assertEqual(self.mock_sender.make_move_count, 1)


class TestReplyTimeTracking(unittest.TestCase):
    def setUp(self):
        """Set up a GameAgent instance for testing reply time tracking."""
        self.agent = GameAgent(name="TestAgent", dialog_turn_delay=0)

    def test_reply_time_tracking_initialization(self):
        """Test that reply time tracking initializes correctly."""
        self.assertEqual(self.agent.accumulated_reply_time_seconds, 0.0)

    def test_reply_time_accumulation(self):
        """Test that reply time accumulates correctly across multiple calls."""
        # Mock the super().generate_reply method to control timing
        
        def mock_generate_reply(*args, **kwargs):
            time.sleep(0.1)  # Simulate processing time
            return "Test response"
        
        with patch.object(self.agent.__class__.__bases__[0], 'generate_reply', side_effect=mock_generate_reply):
            # First call
            self.agent.generate_reply(messages=[{"content": "test"}])
            first_time = self.agent.accumulated_reply_time_seconds
            self.assertGreater(first_time, 0.05)  # Should be around 0.1 seconds
            
            # Second call
            self.agent.generate_reply(messages=[{"content": "test2"}])
            second_time = self.agent.accumulated_reply_time_seconds
            self.assertGreater(second_time, first_time)  # Should accumulate
            self.assertGreater(second_time, 0.15)  # Should be around 0.2 seconds total

    def test_game_stats_includes_reply_time(self):
        """Test that game stats include reply time for agents."""
        # Set up agents with some reply time
        agent_white = GameAgent(name="WhiteAgent")
        agent_black = GameAgent(name="BlackAgent")
        
        agent_white.accumulated_reply_time_seconds = 5.5
        agent_black.accumulated_reply_time_seconds = 7.2
        
        # Mock other required attributes
        agent_white.get_board_count = 1
        agent_white.get_legal_moves_count = 2
        agent_white.make_move_count = 3
        agent_white.reflections_used = 0
        agent_white.reflections_used_before_board = 0
        agent_white.wrong_moves = 0
        agent_white.wrong_actions = 0
        agent_white.material_count = {"white": 39, "black": 38}
        
        agent_black.get_board_count = 2
        agent_black.get_legal_moves_count = 3
        agent_black.make_move_count = 4
        agent_black.reflections_used = 1
        agent_black.reflections_used_before_board = 0
        agent_black.wrong_moves = 1
        agent_black.wrong_actions = 2
        agent_black.material_count = {"white": 39, "black": 38}
        
        game_stats = generate_game_stats(
            time_started="2025.03.16_22:18",
            winner="WhiteAgent",
            reason="Checkmate",
            current_move=10,
            player_white=agent_white,
            player_black=agent_black,
            material_count={"white": 39, "black": 38},
            pgn_string=""
        )
        
        # Check that reply times are included in game stats
        self.assertEqual(game_stats["player_white"]["accumulated_reply_time_seconds"], 5.5)
        self.assertEqual(game_stats["player_black"]["accumulated_reply_time_seconds"], 7.2)

    def test_dialog_turn_delay_not_included_in_time(self):
        """Test that dialog turn delay is not included in accumulated reply time."""
        # Create agent with dialog turn delay (use integer to match the implementation check)
        agent = GameAgent(name="TestAgent", dialog_turn_delay=1)  # Use integer as per implementation
        
        def mock_generate_reply(*args, **kwargs):
            time.sleep(0.01)  # Simulate very short processing time
            return "Test response"
        
        with patch.object(agent.__class__.__bases__[0], 'generate_reply', side_effect=mock_generate_reply):
            start_time = time.time()
            agent.generate_reply(messages=[{"content": "test"}])
            end_time = time.time()
            
            # Total elapsed time should include the dialog delay
            total_elapsed = end_time - start_time
            self.assertGreater(total_elapsed, 0.8)  # Should be at least close to the 1 second delay
            
            # But accumulated reply time should only be the processing time (much smaller)
            self.assertLess(agent.accumulated_reply_time_seconds, 0.1)
            self.assertGreater(agent.accumulated_reply_time_seconds, 0.005)


class TestRetryLogic(unittest.TestCase):
    """Test suite for API retry logic in GameAgent."""
    
    def setUp(self):
        """Set up a GameAgent instance for testing retry logic."""
        self.agent = GameAgent(
            name="TestAgent", 
            dialog_turn_delay=0,
            max_retries=3,
            retry_delay=0.1  # Short delay for testing
        )
    
    def test_retry_initialization(self):
        """Test that retry parameters are properly initialized."""
        self.assertEqual(self.agent.max_retries, 3)
        self.assertEqual(self.agent.retry_delay, 0.1)
    
    def test_no_retry_on_success(self):
        """Test that successful calls don't trigger retries."""
        with patch.object(self.agent.__class__.__bases__[0], 'generate_reply', return_value="Success"):
            result = self.agent.generate_reply(messages=[{"content": "test"}])
            self.assertEqual(result, "Success")
    
    def test_retry_on_openai_internal_server_error(self):
        """Test that openai.InternalServerError triggers retries."""
        # Create a mock exception that matches the pattern
        class MockInternalServerError(Exception):
            def __init__(self, message="Service is not available"):
                super().__init__(message)
                self.__module__ = "openai"
                self.__class__.__name__ = "InternalServerError"
        
        call_count = 0
        def mock_generate_reply(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:  # Fail first 2 times
                raise MockInternalServerError("Service is not available")
            return "Success after retry"
        
        with patch.object(self.agent.__class__.__bases__[0], 'generate_reply', side_effect=mock_generate_reply):
            with patch('builtins.print'):  # Suppress print output during test
                result = self.agent.generate_reply(messages=[{"content": "test"}])
                self.assertEqual(result, "Success after retry")
                self.assertEqual(call_count, 3)  # Should have been called 3 times
    
    def test_max_retries_reached(self):
        """Test that after max retries, the original exception is raised."""
        # Create a mock exception that matches the pattern
        class MockInternalServerError(Exception):
            def __init__(self, message="Service is not available"):
                super().__init__(message)
                self.__module__ = "openai"
                self.__class__.__name__ = "InternalServerError"
        
        def mock_generate_reply(*args, **kwargs):
            raise MockInternalServerError("Service is not available")
        
        with patch.object(self.agent.__class__.__bases__[0], 'generate_reply', side_effect=mock_generate_reply):
            with patch('builtins.print'):  # Suppress print output during test
                with self.assertRaises(MockInternalServerError):
                    self.agent.generate_reply(messages=[{"content": "test"}])
    
    def test_non_retryable_error_no_retry(self):
        """Test that non-retryable errors don't trigger retries."""
        class NonRetryableError(Exception):
            def __init__(self, message="Authentication failed"):
                super().__init__(message)
        
        call_count = 0
        def mock_generate_reply(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise NonRetryableError("Authentication failed")
        
        with patch.object(self.agent.__class__.__bases__[0], 'generate_reply', side_effect=mock_generate_reply):
            with patch('builtins.print'):  # Suppress print output during test
                with self.assertRaises(NonRetryableError):
                    self.agent.generate_reply(messages=[{"content": "test"}])
                self.assertEqual(call_count, 1)  # Should only be called once
    
    def test_exponential_backoff_timing(self):
        """Test that exponential backoff timing works correctly."""
        # Create a mock exception that matches the pattern
        class MockInternalServerError(Exception):
            def __init__(self, message="Service is not available"):
                super().__init__(message)
                self.__module__ = "openai"
                self.__class__.__name__ = "InternalServerError"
        
        call_times = []
        def mock_generate_reply(*args, **kwargs):
            call_times.append(time.time())
            raise MockInternalServerError("Service is not available")
        
        with patch.object(self.agent.__class__.__bases__[0], 'generate_reply', side_effect=mock_generate_reply):
            with patch('builtins.print'):  # Suppress print output during test
                with self.assertRaises(MockInternalServerError):
                    self.agent.generate_reply(messages=[{"content": "test"}])
        
        # Check that we have the expected number of calls (1 initial + 3 retries)
        self.assertEqual(len(call_times), 4)
        
        # Check exponential backoff timing (with some tolerance for test execution)
        # Expected delays: 0.1s, 0.2s, 0.4s
        if len(call_times) >= 2:
            delay1 = call_times[1] - call_times[0]
            self.assertGreater(delay1, 0.08)  # Should be around 0.1s
            self.assertLess(delay1, 0.15)
        
        if len(call_times) >= 3:
            delay2 = call_times[2] - call_times[1]
            self.assertGreater(delay2, 0.18)  # Should be around 0.2s
            self.assertLess(delay2, 0.25)
    
    def test_is_retryable_error_function(self):
        """Test the is_retryable_error function directly."""
        from custom_agents import is_retryable_error
        
        # Test retryable exception by type
        class MockInternalServerError(Exception):
            def __init__(self, message="Service is not available"):
                super().__init__(message)
                self.__module__ = "openai"
                self.__class__.__name__ = "InternalServerError"
        
        retryable_error = MockInternalServerError("Service is not available")
        self.assertTrue(is_retryable_error(retryable_error))
        
        # Test retryable exception by message
        class GenericError(Exception):
            pass
        
        retryable_by_message = GenericError("service is not available")
        self.assertTrue(is_retryable_error(retryable_by_message))
        
        # Test non-retryable exception
        non_retryable = GenericError("Authentication failed")
        self.assertFalse(is_retryable_error(non_retryable))
    
    def test_retry_with_dialog_turn_delay(self):
        """Test that retry logic works correctly when dialog_turn_delay is set."""
        # Create agent with dialog turn delay
        agent = GameAgent(
            name="TestAgent",
            dialog_turn_delay=0.02,  # Very small delay for testing
            max_retries=2,
            retry_delay=0.02  # Very small retry delay
        )
        
        # Create a mock exception that matches the pattern
        class MockInternalServerError(Exception):
            def __init__(self, message="Service is not available"):
                super().__init__(message)
                self.__module__ = "openai"
                self.__class__.__name__ = "InternalServerError"
        
        call_count = 0
        def mock_generate_reply(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # Fail first time
                raise MockInternalServerError("Service is not available")
            return "Success after retry"
        
        with patch.object(agent.__class__.__bases__[0], 'generate_reply', side_effect=mock_generate_reply):
            with patch('builtins.print'):  # Suppress print output during test
                start_time = time.time()
                result = agent.generate_reply(messages=[{"content": "test"}])
                end_time = time.time()
                
                self.assertEqual(result, "Success after retry")
                self.assertEqual(call_count, 2)
                
                # Just verify that some time passed (more forgiving test)
                total_time = end_time - start_time
                self.assertGreater(total_time, 0.01)  # Should be at least some minimal time
    
    def test_accumulated_reply_time_with_retries(self):
        """Test that accumulated reply time is properly tracked even with retries."""
        # Create a mock exception that matches the pattern
        class MockInternalServerError(Exception):
            def __init__(self, message="Service is not available"):
                super().__init__(message)
                self.__module__ = "openai"
                self.__class__.__name__ = "InternalServerError"
        
        call_count = 0
        def mock_generate_reply(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            time.sleep(0.01)  # Simulate processing time
            if call_count <= 2:  # Fail first 2 times
                raise MockInternalServerError("Service is not available")
            return "Success after retry"
        
        with patch.object(self.agent.__class__.__bases__[0], 'generate_reply', side_effect=mock_generate_reply):
            with patch('builtins.print'):  # Suppress print output during test
                self.agent.generate_reply(messages=[{"content": "test"}])
                
                # Should have accumulated time the last call
                self.assertGreater(self.agent.accumulated_reply_time_seconds, 0.01)
                # Allow more time due to test overhead and retry delays
                self.assertLess(self.agent.accumulated_reply_time_seconds, 1.0)


class TestToolCallHandling(unittest.TestCase):
    def test_extract_message_text_from_tool_call(self):
        from custom_agents import extract_message_text
        msg = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "fc_123",
                    "type": "function",
                    "function": {"name": "get_legal_moves", "arguments": "{}"},
                }
            ],
        }
        self.assertEqual(extract_message_text(msg), "get_legal_moves")

    def test_auto_reply_handles_tool_call_action(self):
        # Minimal AutoReplyAgent setup
        get_current_board = lambda: "board_state"
        get_legal_moves = lambda: "e2e4,d2d4,g1f3"
        def make_move(move):
            return None
        agent = AutoReplyAgent(
            name="ProxyTest",
            get_current_board=get_current_board,
            get_legal_moves=get_legal_moves,
            make_move=make_move,
            move_was_made_message="Move made",
            invalid_action_message="Invalid action",
            too_many_failed_actions_message="Too many failed actions",
            max_failed_attempts=3,
            get_current_board_action="get_current_board",
            get_legal_moves_action="get_legal_moves",
            reflect_action="reflect",
            make_move_action="make_move",
            reflect_prompt="Reflecting...",
            reflection_followup_prompt="Follow-up reflection",
            remove_text=None,
        )
        sender = GameAgent(name="MockPlayer")
        sender.reflections_used = 0
        sender.reflections_used_before_board = 0

        # Last message is a tool call with no textual content
        messages = [
            {"content": "You are a random chess player."},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "fc_1",
                        "type": "function",
                        "function": {"name": "get_legal_moves", "arguments": "{}"},
                    }
                ],
            },
        ]
        reply = agent.generate_reply(messages=messages, sender=sender)
        self.assertEqual(reply, get_legal_moves())

    def test_termination_check_handles_tool_call_without_content(self):
        from custom_agents import extract_message_text
        # Termination when tool name equals "move made"
        def is_term(msg):
            return extract_message_text(msg).lower().strip() == "move made"

        agent = RandomPlayerAgent(
            name="RandomTerminator",
            make_move_action="make_move",
            get_legal_moves_action="get_legal_moves",
            get_current_board_action="get_current_board",
            is_termination_msg=is_term,
        )

        messages = [
            {"content": "prev"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "fc_2",
                        "type": "function",
                        "function": {"name": "move made", "arguments": "{}"},
                    }
                ],
            },
        ]

        self.assertIsNone(agent.generate_reply(messages=messages))


if __name__ == '__main__':
    unittest.main()
