import unittest
import os
import csv
import tempfile
import shutil
from data_processing.get_refined_csv import (
    build_refined_rows_from_logs,
    write_refined_csv,
    GameMode,
)


class TestAggrToRefined(unittest.TestCase):
    def setUp(self):
        # Create isolated temp directory and paths to avoid parallel conflicts
        self._tmp_dir = tempfile.mkdtemp(prefix="refined_logs_test_")
        self.mock_logs_dir = os.path.join(self._tmp_dir, "mock_logs")
        self.mock_aggregate_csv = os.path.join(self._tmp_dir, "mock_aggregate.csv")
        self.mock_refined_csv = os.path.join(self._tmp_dir, "mock_refined.csv")

        # Create mock logs directory and files
        os.makedirs(self.mock_logs_dir, exist_ok=True)
        self.mock_log_files = [
            {
                "filename": "mock_log_1.json",
                "content": """{
                    "time_started": "2025.01.15_12:38",
                    "winner": "Random_Player",
                    "reason": "Too many wrong actions",
                    "number_of_moves": 6,
                    "player_white": {
                        "name": "Random_Player",
                        "wrong_moves": 0,
                        "wrong_actions": 0,
                        "reflections_used": 0,
                        "reflections_used_before_board": 0,
                        "get_board_count": 0,
                        "get_legal_moves_count": 0,
                        "make_move_count": 0,
                        "model": "N/A"
                    },
                    "material_count": {
                        "white": 39,
                        "black": 39
                    },
                    "player_black": {
                        "name": "Player_Black",
                        "wrong_moves": 3,
                        "wrong_actions": 0,
                        "reflections_used": 0,
                        "reflections_used_before_board": 0,
                        "get_board_count": 0,
                        "get_legal_moves_count": 0,
                        "make_move_count": 0,
                        "model": "internlm3-8b-instruct"
                    },
                    "usage_stats": {
                        "white": {
                            "total_cost": 0
                        },
                        "black": {
                            "total_cost": 0,
                            "internlm3-8b-instruct": {
                                "cost": 0,
                                "prompt_tokens": 5881,
                                "completion_tokens": 3489,
                                "total_tokens": 9370
                            }
                        }
                    }
                }""",
            },
            {
                "filename": "mock_log_2.json",
                "content": """{
                    "time_started": "2025.01.15_12:38",
                    "winner": "Random_Player",
                    "reason": "Too many wrong actions",
                    "number_of_moves": 6,
                    "player_white": {
                        "name": "Random_Player",
                        "wrong_moves": 0,
                        "wrong_actions": 0,
                        "reflections_used": 0,
                        "reflections_used_before_board": 0,
                        "get_board_count": 0,
                        "get_legal_moves_count": 0,
                        "make_move_count": 0,
                        "model": "N/A"
                    },
                    "material_count": {
                        "white": 39,
                        "black": 39
                    },
                    "player_black": {
                        "name": "Player_Black",
                        "wrong_moves": 3,
                        "wrong_actions": 0,
                        "reflections_used": 0,
                        "reflections_used_before_board": 0,
                        "get_board_count": 0,
                        "get_legal_moves_count": 0,
                        "make_move_count": 0,
                        "model": "llama3-8b"
                    },
                    "usage_stats": {
                        "white": {
                            "total_cost": 0
                        },
                        "black": {
                            "total_cost": 0,
                            "llama3-8b": {
                                "cost": 0,
                                "prompt_tokens": 5881,
                                "completion_tokens": 3489,
                                "total_tokens": 9370
                            }
                        }
                    }
                }""",
            },
        ]

        for log in self.mock_log_files:
            with open(
                os.path.join(self.mock_logs_dir, log["filename"]), "w"
            ) as log_file:
                log_file.write(log["content"])

    def tearDown(self):
        # Clean up temp directory recursively
        if os.path.isdir(self._tmp_dir):
            shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def test_propagation_to_refined_csv(self):
        # Build refined rows directly from logs and write CSV
        rows = build_refined_rows_from_logs(self.mock_logs_dir, filter_out_below_n=0, mode=GameMode.RANDOM_VS_LLM)
        write_refined_csv(rows, self.mock_refined_csv)

        # Read the refined CSV and validate the contents
        with open(self.mock_refined_csv, "r") as ref_file:
            reader = csv.DictReader(ref_file)
            rows = list(reader)

        # Ensure two rows are written (one for each mock log)
        self.assertEqual(len(rows), 2)

        # Order-independent checks
        by_player = {r["Player"]: r for r in rows}
        self.assertIn("internlm3-8b-instruct", by_player)
        self.assertIn("llama3-8b", by_player)

        row_1 = by_player["internlm3-8b-instruct"]
        self.assertEqual(int(row_1["total_games"]), 1)
        self.assertEqual(int(row_1["player_wins"]), 0)
        self.assertEqual(int(row_1["opponent_wins"]), 1)
        self.assertEqual(int(row_1["draws"]), 0)

        row_2 = by_player["llama3-8b"]
        self.assertEqual(int(row_2["total_games"]), 1)
        self.assertEqual(int(row_2["player_wins"]), 0)
        self.assertEqual(int(row_2["opponent_wins"]), 1)
        self.assertEqual(int(row_2["draws"]), 0)

    def test_win_loss_non_interrupted_propagation(self):
        """Tests that the new metrics are correctly present in refined CSV."""
        rows = build_refined_rows_from_logs(self.mock_logs_dir, filter_out_below_n=0, mode=GameMode.RANDOM_VS_LLM)
        write_refined_csv(rows, self.mock_refined_csv)

        # Read the refined CSV and validate the presence of new metrics
        with open(self.mock_refined_csv, "r") as ref_file:
            reader = csv.DictReader(ref_file)
            rows = list(reader)

        # Check that each row has the new metrics
        for row in rows:
            # Check win_loss_non_interrupted and related fields
            self.assertIn("win_loss_non_interrupted", row)
            self.assertIn("moe_win_loss_non_interrupted", row)
            
            # These metrics should all be present and have values
            self.assertIsNotNone(row["win_loss_non_interrupted"])
            self.assertIsNotNone(row["moe_win_loss_non_interrupted"])
            
            # Check games_not_interrupted and related fields
            self.assertIn("games_not_interrupted", row)
            self.assertIn("games_not_interrupted_percent", row)
            self.assertIn("moe_games_not_interrupted", row)
            
            # Since all mock logs are interrupted (reason = Too many wrong actions),
            # games_not_interrupted should be 0 and games_not_interrupted_percent should be 0
            self.assertEqual(int(row["games_not_interrupted"]), 0)
            self.assertEqual(float(row["games_not_interrupted_percent"]), 0.0)
            
            # Similarly, since all games are interrupted, win_loss_non_interrupted should be 0.5
            # (no wins or losses among non-interrupted games, just the default value)
            self.assertEqual(float(row["win_loss_non_interrupted"]), 0.5)

    def test_cost_metrics_propagation(self):
        """Tests that cost metrics are present in refined CSV."""
        rows = build_refined_rows_from_logs(self.mock_logs_dir, filter_out_below_n=0, mode=GameMode.RANDOM_VS_LLM)
        write_refined_csv(rows, self.mock_refined_csv)

        # Read the refined CSV and validate the presence of cost metrics
        with open(self.mock_refined_csv, "r") as ref_file:
            reader = csv.DictReader(ref_file)
            rows = list(reader)

        # Check that each row has the cost metrics
        for row in rows:
            self.assertIn("average_game_cost", row)
            self.assertIn("moe_average_game_cost", row)
            
            # These metrics should be present with default values
            self.assertIsNotNone(row["average_game_cost"])
            self.assertIsNotNone(row["moe_average_game_cost"])

    def test_time_metrics_propagation(self):
        """Tests that measured time metrics are present in refined CSV."""
        rows = build_refined_rows_from_logs(self.mock_logs_dir, filter_out_below_n=0, mode=GameMode.RANDOM_VS_LLM)
        write_refined_csv(rows, self.mock_refined_csv)

        with open(self.mock_refined_csv, "r") as ref_file:
            reader = csv.DictReader(ref_file)
            rows = list(reader)

        for row in rows:
            self.assertIn("average_time_per_game_seconds", row)
            self.assertIn("moe_average_time_per_game_seconds", row)

    def test_win_loss_normalized_bounds(self):
        """win_loss must be normalized to [0,1] and not negative."""
        rows = build_refined_rows_from_logs(self.mock_logs_dir, filter_out_below_n=0, mode=GameMode.RANDOM_VS_LLM)
        # Write and read back via CSV to mimic end-to-end
        write_refined_csv(rows, self.mock_refined_csv)
        with open(self.mock_refined_csv, "r") as ref_file:
            reader = csv.DictReader(ref_file)
            loaded = list(reader)

        for row in loaded:
            wl = float(row["win_loss"])  # normalized
            self.assertGreaterEqual(wl, 0.0)
            self.assertLessEqual(wl, 1.0)
            # In these mocks, all games are losses for black
            self.assertEqual(wl, 0.0)


if __name__ == "__main__":
    unittest.main() 


class TestDragonVsLLMRefined(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = tempfile.mkdtemp(prefix="dragon_vs_llm_test_")

    def tearDown(self):
        if os.path.isdir(self._tmp_dir):
            shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def _write_file(self, path, content):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def test_engine_new_format_parsing(self):
        # Create new-format directory with _run.json and two game logs
        run_dir = os.path.join(
            self._tmp_dir,
            "engine_vs_llm",
            "dragon-lvl-3",
            "gpt-5-nano-2025-08-07-low",
            "2025-09-01-17-46-03",
        )

        run_json = """{
            "metadata": {"time_started_formatted": "2025.09.01_17:46"},
            "player_types": {"white_player_type": "CHESS_ENGINE_DRAGON", "black_player_type": "LLM_BLACK"},
            "chess_engines": {"dragon": {"level": 3, "time_per_move": 0.1}},
            "llm_configs": {"black": {"model": "gpt-5-nano-2025-08-07", "reasoning_effort": "low", "thinking_budget": 0}}
        }"""
        self._write_file(os.path.join(run_dir, "_run.json"), run_json)

        game1 = """{
            "time_started": "2025.09.01_17:46",
            "winner": "Player_Black",
            "reason": "OK",
            "number_of_moves": 20,
            "player_white": {"name": "CHESS_ENGINE_DRAGON", "wrong_moves": 0, "wrong_actions": 0, "reflections_used": 0, "reflections_used_before_board": 0, "get_board_count": 0, "get_legal_moves_count": 0, "make_move_count": 0, "model": "N/A"},
            "material_count": {"white": 39, "black": 39},
            "player_black": {"name": "Player_Black", "wrong_moves": 0, "wrong_actions": 0, "reflections_used": 0, "reflections_used_before_board": 0, "get_board_count": 0, "get_legal_moves_count": 0, "make_move_count": 0, "model": "placeholder"},
            "usage_stats": {"white": {"total_cost": 0}, "black": {"total_cost": 0, "gpt-5-nano-2025-08-07": {"cost": 0, "prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300}}}
        }"""
        game2 = """{
            "time_started": "2025.09.01_17:47",
            "winner": "CHESS_ENGINE_DRAGON",
            "reason": "OK",
            "number_of_moves": 18,
            "player_white": {"name": "CHESS_ENGINE_DRAGON", "wrong_moves": 0, "wrong_actions": 0, "reflections_used": 0, "reflections_used_before_board": 0, "get_board_count": 0, "get_legal_moves_count": 0, "make_move_count": 0, "model": "N/A"},
            "material_count": {"white": 39, "black": 39},
            "player_black": {"name": "Player_Black", "wrong_moves": 0, "wrong_actions": 0, "reflections_used": 0, "reflections_used_before_board": 0, "get_board_count": 0, "get_legal_moves_count": 0, "make_move_count": 0, "model": "placeholder"},
            "usage_stats": {"white": {"total_cost": 0}, "black": {"total_cost": 0, "gpt-5-nano-2025-08-07": {"cost": 0, "prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300}}}
        }"""
        self._write_file(os.path.join(run_dir, "game_1.json"), game1)
        self._write_file(os.path.join(run_dir, "game_2.json"), game2)

        rows = build_refined_rows_from_logs(
            os.path.join(self._tmp_dir, "engine_vs_llm"),
            filter_out_below_n=0,
            mode=GameMode.DRAGON_VS_LLM,
        )
        # Expect a single grouped row by (Player, opponent)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        # Player should be composed from _run.json model + reasoning suffix
        self.assertEqual(row["Player"], "gpt-5-nano-2025-08-07-low")
        # Opponent from _run.json dragon level
        self.assertEqual(row.get("white_opponent"), "dragon-lvl-3")
        # 2 games, one win for black, one for white
        self.assertEqual(int(row["total_games"]), 2)
        self.assertEqual(int(row["player_wins"]), 1)
        self.assertEqual(int(row["opponent_wins"]), 1)

    def test_engine_legacy_path_parsing(self):
        # Create legacy layout: lvl-3_vs_MODEL/<timestamp>/game.json
        legacy_base = os.path.join(self._tmp_dir, "dragon_vs_llm")
        run_dir = os.path.join(legacy_base, "lvl-3_vs_gpt-5-nano-2025-08-07-low", "2025-05-02-00-02")

        game = """{
            "time_started": "2025.05.02_00:02",
            "winner": "CHESS_ENGINE_DRAGON",
            "reason": "OK",
            "number_of_moves": 12,
            "player_white": {"name": "CHESS_ENGINE_DRAGON", "wrong_moves": 0, "wrong_actions": 0, "reflections_used": 0, "reflections_used_before_board": 0, "get_board_count": 0, "get_legal_moves_count": 0, "make_move_count": 0, "model": "N/A"},
            "material_count": {"white": 39, "black": 39},
            "player_black": {"name": "Player_Black", "wrong_moves": 0, "wrong_actions": 0, "reflections_used": 0, "reflections_used_before_board": 0, "get_board_count": 0, "get_legal_moves_count": 0, "make_move_count": 0, "model": "placeholder"},
            "usage_stats": {"white": {"total_cost": 0}, "black": {"total_cost": 0, "gpt-5-nano-2025-08-07-low": {"cost": 0, "prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}}}
        }"""
        self._write_file(os.path.join(run_dir, "game_1.json"), game)

        rows = build_refined_rows_from_logs(
            legacy_base,
            filter_out_below_n=0,
            mode=GameMode.DRAGON_VS_LLM,
        )
        self.assertEqual(len(rows), 1)
        row = rows[0]
        # Player should be parsed from path segment after lvl-N_vs_
        self.assertEqual(row["Player"], "gpt-5-nano-2025-08-07-low")
        # Opponent should be inferred from "lvl-3" → dragon-lvl-3
        self.assertEqual(row.get("white_opponent"), "dragon-lvl-3")
        self.assertEqual(int(row["total_games"]), 1)
        self.assertEqual(int(row["player_wins"]), 0)
        self.assertEqual(int(row["opponent_wins"]), 1)