import unittest
import chess
from custom_agents import GameAgent, RandomPlayerAgent, AutoReplyAgent, ChessEngineStockfishAgent

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
            invalid_action_message="Invalid action",
            too_many_failed_actions_message="Too many failed actions",
            max_failed_attempts=3,
            get_current_board_action="get_current_board",
            get_legal_moves_action="get_legal_moves",
            reflect_action="reflect",
            make_move_action="make_move",
            reflect_prompt="Reflecting...",
            reflection_followup_prompt="Follow-up reflection",
            ignore_text=None,
        )
        self.assertEqual(agent.name, "AutoReplyAgent")
        self.assertEqual(agent.max_failed_attempts, 3)
        self.assertEqual(agent.move_was_made, "Move made")
        self.assertEqual(agent.invalid_action_message, "Invalid action")

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
            invalid_action_message="Invalid action",
            too_many_failed_actions_message="Too many failed actions",
            max_failed_attempts=3,
            get_current_board_action="get_current_board",
            get_legal_moves_action="get_legal_moves",
            reflect_action="reflect",
            make_move_action="make_move",
            reflect_prompt="Reflecting...",
            reflection_followup_prompt="Follow-up reflection",
            ignore_text=None
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
    
    def test_ignore_text(self):
        """Test that ignore_text pattern is properly applied."""
        agent_with_ignore = AutoReplyAgent(
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
            ignore_text=r"<think>.*?</think>"
        )
        
        messages = [{"content": "<think>some thinking</think>make_move e2e4"}]
        reply = agent_with_ignore.generate_reply(messages=messages, sender=self.mock_sender)
        self.assertEqual(reply, "Move made")

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
        self.assertEqual(self.agent.failed_action_attempts, 1)

    def test_invalid_action_format(self):
        """Test handling of incorrectly formatted actions."""
        messages = [{"content": "invalid_action"}]
        reply = self.agent.generate_reply(messages=messages, sender=self.mock_sender)
        self.assertEqual(reply, self.agent.invalid_action_message)
        self.assertEqual(self.mock_sender.wrong_actions, 1)
        self.assertEqual(self.agent.failed_action_attempts, 1)


    def test_max_failed_attempts(self):
        """Test that agent stops after reaching max failed attempts."""
        self.agent.failed_action_attempts = self.agent.max_failed_attempts - 1
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
        self.assertEqual(self.mock_sender.wrong_moves, 0)
        self.assertEqual(self.mock_sender.wrong_actions, 0)
        self.assertFalse(self.mock_sender.has_requested_board)


if __name__ == "__main__":
    unittest.main()
