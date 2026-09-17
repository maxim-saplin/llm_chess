"""Mocked unit tests for TypeSafe Jev agent and pipeline wiring (no real API calls)."""

from __future__ import annotations

import importlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import chess

from custom_agents import TypeSafeJevAgent
from llm_chess import PlayerType
from utils import generate_game_stats


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
        self.assertEqual(agent.total_prompt_tokens, 0)
        self.assertEqual(agent.total_cost, 0.0)
        self.assertEqual(agent.accumulated_reply_time_seconds, 0.0)

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
        mock_response.usage = None

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
        self.assertGreater(agent.accumulated_reply_time_seconds, 0.0)

    @patch("typesafe_sdk.TypeSafeClient")
    @patch("typesafe_sdk.Choice")
    def test_generate_reply_accumulates_usage_and_cost(self, mock_choice, mock_client_cls):
        board = chess.Board()
        agent = TypeSafeJevAgent(
            name="JevAgent",
            board=board,
            make_move_action="make_move",
            model="jev-test",
        )

        mock_choice_answer = MagicMock()
        mock_choice_answer.choice = "e2e4"
        mock_usage = MagicMock()
        mock_usage.input_tokens = 1000
        mock_usage.output_tokens = 200
        mock_response = MagicMock()
        mock_response.choices = {"move": mock_choice_answer}
        mock_response.usage = mock_usage

        mock_client = MagicMock()
        mock_client.system_one.return_value = mock_response
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = False
        mock_client_cls.return_value = mock_client

        reply = agent.generate_reply(messages=[{"content": "Your turn"}])
        self.assertEqual(reply, "make_move e2e4")
        self.assertEqual(agent.total_prompt_tokens, 1000)
        self.assertEqual(agent.total_completion_tokens, 200)
        self.assertEqual(agent.total_tokens, 1200)
        self.assertAlmostEqual(agent.total_cost, 1000 * 0.042 / 1_000_000)
        self.assertEqual(agent.usage_model_name, "jev-test")

    @patch("typesafe_sdk.TypeSafeClient")
    @patch("typesafe_sdk.Choice")
    def test_rejects_uci_not_in_criteria(self, mock_choice, mock_client_cls):
        board = chess.Board()
        agent = TypeSafeJevAgent(
            name="JevAgent",
            board=board,
            make_move_action="make_move",
            model="jev-test",
            max_retries=0,
        )
        mock_choice_answer = MagicMock()
        mock_choice_answer.choice = "a2a2"  # illegal / not in criteria
        mock_response = MagicMock()
        mock_response.choices = {"move": mock_choice_answer}
        mock_response.usage = None
        mock_client = MagicMock()
        mock_client.system_one.return_value = mock_response
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = False
        mock_client_cls.return_value = mock_client

        reply = agent.generate_reply(messages=[{"content": "Your turn"}])
        self.assertIsNone(reply)

    @patch("typesafe_sdk.TypeSafeClient")
    def test_generate_reply_api_error_returns_none(self, mock_client_cls):
        board = chess.Board()
        agent = TypeSafeJevAgent(
            name="JevAgent",
            board=board,
            make_move_action="make_move",
            max_retries=0,
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
            max_retries=0,
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


class TestTypeSafePipelineWiring(unittest.TestCase):
    def test_player_maps_use_standard_names(self):
        import llm_chess

        # Build agents the same way run() does for TYPESAFE_JEV sides.
        board = chess.Board()
        white = TypeSafeJevAgent(
            name="Player_White",
            board=board,
            make_move_action="make_move",
        )
        black = TypeSafeJevAgent(
            name="Player_Black",
            board=board,
            make_move_action="make_move",
        )
        self.assertEqual(white.name, "Player_White")
        self.assertEqual(black.name, "Player_Black")

        # Spot-check source wiring (rename fix for refined CSV).
        src = Path("llm_chess.py").read_text(encoding="utf-8")
        self.assertIn('name="Player_White"', src)
        self.assertIn('name="Player_Black"', src)
        self.assertNotIn("TypeSafe_Jev_White", src)
        self.assertNotIn("TypeSafe_Jev_Black", src)

    def test_generate_game_stats_shape_for_jev(self):
        board = chess.Board()
        white = TypeSafeJevAgent(
            name="Random_Player",
            board=board,
            make_move_action="make_move",
        )
        # Pretend random: zero usage attrs still present on Jev-like agent — use a simple stub for white.
        class _Stub:
            name = "Random_Player"
            wrong_moves = 0
            wrong_actions = 0
            reflections_used = 0
            reflections_used_before_board = 0
            get_board_count = 0
            get_legal_moves_count = 1
            make_move_count = 1
            accumulated_reply_time_seconds = 0.0
            llm_config = {"config_list": [{"model": "N/A"}]}

        black = TypeSafeJevAgent(
            name="Player_Black",
            board=board,
            make_move_action="make_move",
            model="jev-latest",
        )
        black.total_prompt_tokens = 500
        black.total_completion_tokens = 10
        black.total_tokens = 510
        black.total_cost = 500 * 0.042 / 1_000_000
        black.accumulated_reply_time_seconds = 1.25
        black.reflections_used = 0
        black.reflections_used_before_board = 0

        with patch("utils.gather_usage_summary", return_value=None):
            stats = generate_game_stats(
                time_started="t",
                winner="Player_Black",
                reason="Checkmate",
                current_move=10,
                player_white=_Stub(),
                player_black=black,
                material_count={"white": 39, "black": 39},
            )
        self.assertEqual(stats["player_black"]["name"], "Player_Black")
        self.assertEqual(stats["player_black"]["model"], "jev-latest")
        self.assertEqual(stats["winner"], "Player_Black")
        self.assertAlmostEqual(stats["usage_stats"]["black"]["total_cost"], black.total_cost)
        self.assertEqual(stats["player_black"]["accumulated_reply_time_seconds"], 1.25)

    def test_model_label_from_run_json_typesafe(self):
        from data.get_refined_csv import _model_label_from_run_json

        _model_label_from_run_json.cache_clear()
        with tempfile.TemporaryDirectory() as td:
            run = {
                "player_types": {
                    "white_player_type": "RANDOM_PLAYER",
                    "black_player_type": "TYPESAFE_JEV",
                },
                "llm_configs": {"black": {"model": "jev-latest"}},
                "chess_engines": {"typesafe_jev": {"model": "jev-latest"}},
            }
            (Path(td) / "_run.json").write_text(json.dumps(run), encoding="utf-8")
            self.assertEqual(_model_label_from_run_json(td), "jev-latest")

        _model_label_from_run_json.cache_clear()
        with tempfile.TemporaryDirectory() as td2:
            # Engine-only shape (no llm_configs) still recovers model.
            run2 = {
                "player_types": {
                    "white_player_type": "CHESS_ENGINE_DRAGON",
                    "black_player_type": "TYPESAFE_JEV",
                },
                "chess_engines": {
                    "dragon": {"level": 1},
                    "typesafe_jev": {"model": "jev-1.13.0"},
                },
            }
            (Path(td2) / "_run.json").write_text(json.dumps(run2), encoding="utf-8")
            self.assertEqual(_model_label_from_run_json(td2), "jev-1.13.0")

    def test_refined_csv_accepts_player_black_jev(self):
        from data.get_refined_csv import GameMode, load_game_logs

        with tempfile.TemporaryDirectory() as td:
            game = {
                "time_started": "t",
                "winner": "Player_Black",
                "reason": "Checkmate",
                "number_of_moves": 20,
                "player_white": {
                    "name": "Random_Player",
                    "wrong_moves": 0,
                    "wrong_actions": 0,
                    "reflections_used": 0,
                    "reflections_used_before_board": 0,
                    "get_board_count": 0,
                    "get_legal_moves_count": 0,
                    "make_move_count": 10,
                    "accumulated_reply_time_seconds": 0.0,
                    "model": "N/A",
                },
                "player_black": {
                    "name": "Player_Black",
                    "wrong_moves": 0,
                    "wrong_actions": 0,
                    "reflections_used": 0,
                    "reflections_used_before_board": 0,
                    "get_board_count": 0,
                    "get_legal_moves_count": 0,
                    "make_move_count": 10,
                    "accumulated_reply_time_seconds": 1.0,
                    "model": "jev-latest",
                },
                "material_count": {"white": 20, "black": 39},
                "usage_stats": {
                    "white": {"total_cost": 0},
                    "black": {
                        "total_cost": 0.001,
                        "jev-latest": {
                            "prompt_tokens": 100,
                            "completion_tokens": 0,
                            "total_tokens": 100,
                        },
                    },
                },
            }
            (Path(td) / "game.json").write_text(json.dumps(game), encoding="utf-8")
            (Path(td) / "_run.json").write_text(
                json.dumps(
                    {
                        "player_types": {
                            "white_player_type": "RANDOM_PLAYER",
                            "black_player_type": "TYPESAFE_JEV",
                        },
                        "llm_configs": {"black": {"model": "jev-latest"}},
                        "chess_engines": {"typesafe_jev": {"model": "jev-latest"}},
                    }
                ),
                encoding="utf-8",
            )
            logs = load_game_logs(td, mode=GameMode.RANDOM_VS_LLM)
            self.assertEqual(len(logs), 1)
            self.assertEqual(logs[0].player_black.name, "Player_Black")
            self.assertEqual(logs[0].player_black.model, "jev-latest")
            self.assertEqual(logs[0].winner, "Player_Black")

    def test_runner_import_does_not_start_games(self):
        # Importing the module must not execute games (__main__ guard).
        with patch("llm_chess.run") as mock_run:
            import run_jev_vs_random
            import run_jev_vs_dragon

            importlib.reload(run_jev_vs_random)
            importlib.reload(run_jev_vs_dragon)
            mock_run.assert_not_called()
            self.assertTrue(callable(run_jev_vs_random.main))
            self.assertTrue(callable(run_jev_vs_dragon.main))
            import sys

            path = run_jev_vs_dragon._default_dragon_path()
            if sys.platform == "darwin":
                self.assertIn("dragon-osx", path)
            elif sys.platform.startswith("win"):
                self.assertIn("dragon.exe", path)
            else:
                self.assertIn("dragon-linux", path)


if __name__ == "__main__":
    unittest.main()
