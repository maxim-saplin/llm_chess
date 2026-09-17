"""Mocked unit tests for TypeSafe Jev agent (no real API calls)."""

import unittest
from unittest.mock import MagicMock, patch

import chess

from custom_agents import TypeSafeJevAgent
from llm_chess import PlayerType


class TestTypeSafeJevAgent(unittest.TestCase):
    def test_player_type_exists(self):
        self.assertEqual(PlayerType.TYPESAFE_JEV.value, 8)

    def test_initialization(self):
        board = chess.Board()
        agent = TypeSafeJevAgent(
            name="JevAgent",
            board=board,
            make_move_action="make_move",
            model="jev-latest",
        )
        self.assertEqual(agent.name, "JevAgent")
        self.assertEqual(agent.board, board)
        self.assertEqual(agent.make_move_action, "make_move")
        self.assertEqual(agent.model, "jev-latest")

    @patch("typesafe_sdk.TypeSafeClient")
    @patch("typesafe_sdk.Choice")
    def test_generate_reply_returns_make_move(self, mock_choice, mock_client_cls):
        board = chess.Board()
        agent = TypeSafeJevAgent(
            name="JevAgent",
            board=board,
            make_move_action="make_move",
            model="jev-test",
        )

        mock_choice_answer = MagicMock()
        mock_choice_answer.choice = "e2e4"
        mock_response = MagicMock()
        mock_response.choices = {"move": mock_choice_answer}

        mock_client = MagicMock()
        mock_client.system_one.return_value = mock_response
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = False
        mock_client_cls.return_value = mock_client

        reply = agent.generate_reply(messages=[{"content": "Your turn"}])

        self.assertEqual(reply, "make_move e2e4")
        mock_client_cls.assert_called_once_with(model="jev-test")
        mock_client.system_one.assert_called_once()
        call_kwargs = mock_client.system_one.call_args.kwargs
        self.assertIn("fen", call_kwargs["state"])
        self.assertEqual(call_kwargs["state"]["side_to_move"], "white")
        self.assertIn("move", call_kwargs["questions"])
        mock_choice.assert_called_once()
        criteria = mock_choice.call_args.kwargs["criteria"]
        self.assertIn("e2e4", criteria)
        self.assertEqual(criteria["e2e4"], "e4")

    @patch("typesafe_sdk.TypeSafeClient")
    def test_generate_reply_api_error_returns_none(self, mock_client_cls):
        board = chess.Board()
        agent = TypeSafeJevAgent(
            name="JevAgent",
            board=board,
            make_move_action="make_move",
        )
        mock_client = MagicMock()
        mock_client.__enter__.side_effect = RuntimeError("API down")
        mock_client_cls.return_value = mock_client

        reply = agent.generate_reply(messages=[{"content": "Your turn"}])
        self.assertIsNone(reply)

    def test_too_many_legal_moves_returns_none(self):
        board = chess.Board()
        agent = TypeSafeJevAgent(
            name="JevAgent",
            board=board,
            make_move_action="make_move",
        )
        fake_moves = [chess.Move.from_uci("a2a3")] * (
            TypeSafeJevAgent.MAX_CHOICE_OPTIONS + 1
        )
        with patch.object(agent, "board") as mock_board:
            mock_board.legal_moves = fake_moves
            mock_board.turn = chess.WHITE
            mock_board.fen.return_value = chess.STARTING_FEN
            reply = agent.generate_reply(messages=[{"content": "Your turn"}])
            self.assertIsNone(reply)


if __name__ == "__main__":
    unittest.main()
