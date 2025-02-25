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


if __name__ == "__main__":
    unittest.main()
