import unittest
import chess
from custom_agents import GameAgent, RandomPlayerAgent, AutoReplyAgent, ChessEngineStockfishAgent
from utils import generate_game_stats
import time
from unittest.mock import patch, MagicMock

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
        messages = [{"content": "invalid_action"}]
        reply = self.agent.generate_reply(messages=messages, sender=self.mock_sender)
        expected_reply = "Invalid action. Pick one, reply exactly with the name and space delimitted argument: get_current_board, get_legal_moves, make_move <UCI formatted move>"
        self.assertEqual(reply, expected_reply)
        self.assertEqual(self.mock_sender.wrong_actions, 1)
        self.assertEqual(self.mock_sender.failed_action_attempts, 1)


    def test_max_failed_attempts(self):
        """Test that agent stops after reaching max failed attempts."""
        self.mock_sender.failed_action_attempts = self.agent.max_failed_attempts - 1
        messages = [{"content": "invalid_action"}]
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
    
    def test_reply_time_tracking_initialization(self):
        """Test that the accumulated_reply_time_seconds is initialized to 0."""
        agent = GameAgent(name="TestAgent")
        self.assertEqual(agent.accumulated_reply_time_seconds, 0.0)
    
    def test_reply_time_accumulation(self):
        """Test that reply time is properly accumulated across multiple calls."""
        # Create a game agent
        agent = GameAgent(name="TestAgent")
        
        # Create a mock sender
        mock_sender = MagicMock()
        
        # Create mock messages
        mock_messages = [{"content": "Hello"}]
        
        # Mock the parent's generate_reply to avoid actual LLM calls
        with patch('autogen.ConversableAgent.generate_reply', return_value="Mock reply"):
            # Call generate_reply multiple times
            for _ in range(3):
                # Add a small delay to simulate processing time
                time.sleep(0.01)
                agent.generate_reply(messages=mock_messages, sender=mock_sender)
            
            # Check that accumulated_reply_time_seconds is greater than 0
            self.assertGreater(agent.accumulated_reply_time_seconds, 0.0)
            
            # Get the current accumulated time for later comparison
            current_time = agent.accumulated_reply_time_seconds
            
            # Call again and check that the time increases
            agent.generate_reply(messages=mock_messages, sender=mock_sender)
            self.assertGreater(agent.accumulated_reply_time_seconds, current_time)
    
    def test_game_stats_includes_reply_time(self):
        """Test that reply time is included in game stats."""
        # Create game agents
        white_agent = GameAgent(name="WhitePlayer")
        black_agent = GameAgent(name="BlackPlayer")
        
        # Set accumulated_reply_time_seconds for testing
        white_agent.accumulated_reply_time_seconds = 1.5
        black_agent.accumulated_reply_time_seconds = 2.5
        
        # Add required attributes for game_stats
        white_agent.wrong_moves = 0
        white_agent.wrong_actions = 0
        white_agent.reflections_used = 0
        white_agent.reflections_used_before_board = 0
        white_agent.get_board_count = 0
        white_agent.get_legal_moves_count = 0
        white_agent.make_move_count = 0
        white_agent.llm_config = None
        
        black_agent.wrong_moves = 0
        black_agent.wrong_actions = 0
        black_agent.reflections_used = 0
        black_agent.reflections_used_before_board = 0
        black_agent.get_board_count = 0
        black_agent.get_legal_moves_count = 0
        black_agent.make_move_count = 0
        black_agent.llm_config = None
        
        # Generate game stats
        stats = generate_game_stats(
            time_started="2023-01-01_12-00-00",
            winner="White",
            reason="Checkmate",
            current_move=10,
            player_white=white_agent,
            player_black=black_agent,
            material_count={"white": 39, "black": 39}
        )
        
        # Check that accumulated_reply_time_seconds is included in stats
        self.assertEqual(stats["player_white"]["accumulated_reply_time_seconds"], 1.5)
        self.assertEqual(stats["player_black"]["accumulated_reply_time_seconds"], 2.5)
    
    def test_dialog_turn_delay_not_included_in_time(self):
        """Test that dialog_turn_delay is NOT included in the accumulated time."""
        # Create a game agent with a delay (use integer to match implementation)
        agent = GameAgent(name="DelayedAgent", dialog_turn_delay=1)
        
        # Create mock messages and sender
        mock_messages = [{"content": "Hello"}]
        mock_sender = MagicMock()
        
        # Mock both time.sleep (to avoid actual delay) and the parent's generate_reply
        with patch('time.sleep') as mock_sleep, \
             patch('autogen.ConversableAgent.generate_reply', return_value="Mock reply"):
            
            # Call generate_reply
            agent.generate_reply(messages=mock_messages, sender=mock_sender)
            
            # Verify time.sleep was called with the delay value 
            mock_sleep.assert_called_once_with(1)
            
            # The accumulated time should be very small since we're just measuring
            # the execution time of the mocked generate_reply, not the delay
            self.assertLess(agent.accumulated_reply_time_seconds, 0.01)  # Should be small without delay


if __name__ == "__main__":
    unittest.main()
