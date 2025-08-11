import json
import tempfile
import os
import unittest
from unittest.mock import patch

import llm_chess
from utils import get_llms
from get_run_metadata import collect_run_metadata, write_run_metadata

from unittest.mock import patch
from .helper import _MockServerTestCaseBase, get_mock_base_url


def _dummy_llm_config(model: str):
    """Return a minimal autogen-style config for testing."""
    return {
        "config_list": [
            {
                "model": model,
                "api_key": "SECRET",
                "api_type": "openai",
            }
        ],
        "timeout": 600,
        "temperature": 0.3,
    }


class TestRunMetadata(unittest.TestCase):
    """Unit-tests for the `_run.json` metadata helper."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.log_folder = os.path.join(self.temp_dir.name, "logs")
        os.makedirs(self.log_folder, exist_ok=True)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_basic_creation_and_redaction(self):
        # Ensure both sides are treated as LLMs for this test so both configs appear
        llm_chess.white_player_type = llm_chess.PlayerType.LLM_WHITE
        llm_chess.black_player_type = llm_chess.PlayerType.LLM_BLACK

        md = collect_run_metadata(
            log_folder_relative=self.log_folder,
            num_repetitions=2,
            store_individual_logs=True,
            llm_config_white=_dummy_llm_config("gpt-4-turbo"),
            llm_config_black=_dummy_llm_config("gpt-4-turbo"),
        )

        # Validate top-level keys
        self.assertTrue({"metadata", "player_types", "config", "llm_configs"}.issubset(md.keys()))
        self.assertNotIn("chess_engines", md)

        # API key redaction (both sides present)
        self.assertEqual(md["llm_configs"]["white"]["api_key"], "REDACTED")
        self.assertEqual(md["llm_configs"]["black"]["api_key"], "REDACTED")

        # Write to disk and compare
        run_path = os.path.join(self.log_folder, "_run.json")
        write_run_metadata(md, run_path)
        with open(run_path, encoding="utf-8") as f:
            data_back = json.load(f)
        self.assertEqual(data_back, md)

    def test_reasoning_effort_and_thinking_budget_captured(self):
        """Ensure reasoning_effort (nested) and thinking_budget are recorded."""
        # Treat both sides as LLMs so llm_configs section appears
        llm_chess.white_player_type = llm_chess.PlayerType.LLM_WHITE
        llm_chess.black_player_type = llm_chess.PlayerType.LLM_BLACK

        cfg_w = {
            "config_list": [
                {
                    "model": "model-w",
                    "api_key": "SECRET",
                    "api_type": "openai",
                    "reasoning_effort": "high",
                }
            ],
            "timeout": 600,
            "top_p": 1.0,
        }
        cfg_b = {
            "config_list": [
                {
                    "model": "model-b",
                    "api_key": "SECRET",
                    "api_type": "anthropic",
                }
            ],
            "timeout": 600,
            "thinking": {"type": "enabled", "budget_tokens": 4096},
        }

        md = collect_run_metadata(
            log_folder_relative=self.log_folder,
            num_repetitions=1,
            store_individual_logs=False,
            llm_config_white=cfg_w,
            llm_config_black=cfg_b,
        )

        self.assertEqual(md["llm_configs"]["white"]["reasoning_effort"], "high")
        self.assertEqual(md["llm_configs"]["black"]["thinking_budget"], 4096)
        # Ensure redaction still active
        self.assertEqual(md["llm_configs"]["white"]["api_key"], "REDACTED")

    def test_api_type_inference_from_base_url(self):
        # Ensure both sides treated as LLMs so llm_configs is populated
        llm_chess.white_player_type = llm_chess.PlayerType.LLM_WHITE
        llm_chess.black_player_type = llm_chess.PlayerType.LLM_BLACK

        def cfg_with_base_url(url: str):
            return {
                "config_list": [
                    {
                        "model": "dummy",
                        "api_key": "SECRET",
                        "base_url": url,
                        # Note: api_type intentionally omitted to test inference
                    }
                ],
                "timeout": 600,
            }

        cases = [
            ("http://localhost:1234/v1", "local"),
            ("http://127.0.0.1:1234/v1", "local"),
            ("https://api.deepseek.com", "deepseek"),
            ("https://api.hunyuan.cloud.tencent.com/v1", "tencent"),
            ("https://api.x.ai/v1", "xai"),
            ("https://dashscope-intl.aliyuncs.com/compatible-mode/v1", "dashscope"),
            ("https://openrouter.ai/api/v1", "openrouter"),
            ("https://api.inceptionlabs.ai/v1", "inceptionlabs"),
            ("https://api.cerebras.ai/v1", "cerebras"),
            ("https://api.groq.com/openai/v1", "groq"),
            ("https://some.custom.host/v1", "oai_comp_endpoint"),
        ]

        for base_url, expected_api_type in cases:
            with self.subTest(base_url=base_url):
                md = collect_run_metadata(
                    log_folder_relative=self.log_folder,
                    num_repetitions=1,
                    store_individual_logs=False,
                    llm_config_white=cfg_with_base_url(base_url),
                    llm_config_black=None,
                )
                self.assertIn("llm_configs", md)
                self.assertIn("white", md["llm_configs"])
                self.assertEqual(md["llm_configs"]["white"]["api_type"], expected_api_type)
                self.assertEqual(md["llm_configs"]["white"]["api_key"], "REDACTED")

# Copy of helper from test_per_model_config (kept local to avoid import cycles)
_ENV_TEMPLATES = {
    "local": [
        "LOCAL_MODEL_NAME_{}",
        "LOCAL_BASE_URL_{}",
        "LOCAL_API_KEY_{}",
    ],
}

def _prepare_env(kind_w="local", kind_b="local"):
    env_updates = {
        "MODEL_KIND_W": kind_w,
        "MODEL_KIND_B": kind_b,
    }
    for key_suffix in ["W", "B"]:
        for tmpl in _ENV_TEMPLATES[kind_w if key_suffix == "W" else kind_b]:
            env_updates[tmpl.format(key_suffix)] = f"model-{key_suffix.lower()}"
    return patch.dict(os.environ, env_updates, clear=False)

class TestRunScenarios(_MockServerTestCaseBase):
    max_moves_for_tests = 2  # keep tests fast

    def setUp(self):
        # Common fast-run flags
        llm_chess.visualize_board = False
        llm_chess.throttle_delay = 0
        llm_chess.dialog_turn_delay = 0
        llm_chess.max_game_moves = self.max_moves_for_tests
        # Disable API retries for these tests to avoid noisy retry logs
        self._orig_max_api_retries = llm_chess.max_api_retries
        self._orig_api_retry_delay = llm_chess.api_retry_delay
        llm_chess.max_api_retries = 0
        llm_chess.api_retry_delay = 0

    def tearDown(self):
        # Restore original retry config
        llm_chess.max_api_retries = self._orig_max_api_retries
        llm_chess.api_retry_delay = self._orig_api_retry_delay

    # ---------------------------------------------------------------------
    # LLM vs Random Player
    # ---------------------------------------------------------------------
    def test_llm_vs_random(self):
        llm_chess.white_player_type = llm_chess.PlayerType.LLM_WHITE
        llm_chess.black_player_type = llm_chess.PlayerType.RANDOM_PLAYER

        with _prepare_env():
            cfg_w, cfg_b = get_llms({}, {})
            stats, _, p_black = llm_chess.run(
                log_dir=None,
                llm_config_white=cfg_w,
                llm_config_black=cfg_b,
            )

        # Basic assertions – game finished and players have expected names
        self.assertIsNotNone(stats["winner"])
        self.assertLessEqual(stats["number_of_moves"], self.max_moves_for_tests)
        self.assertEqual(p_black.name, "Random_Player")

    # ---------------------------------------------------------------------
    # LLM vs Chess Engine (Stockfish) – engine generate_reply patched
    # ---------------------------------------------------------------------
    @patch(
        "custom_agents.ChessEngineStockfishAgent.generate_reply",
        lambda self, messages, sender=None, **kwargs: "get_moves" if messages[-1]["content"].startswith("get_legal") else "make_move e2e4",
    )
    def test_llm_vs_stockfish(self):
        llm_chess.white_player_type = llm_chess.PlayerType.LLM_WHITE
        llm_chess.black_player_type = llm_chess.PlayerType.CHESS_ENGINE_STOCKFISH

        with _prepare_env():
            cfg_w, cfg_b = get_llms({}, {})
            stats, _, p_black = llm_chess.run(
                log_dir=None,
                llm_config_white=cfg_w,
                llm_config_black=cfg_b,
            )

        self.assertIsNotNone(stats["winner"])
        self.assertLessEqual(stats["number_of_moves"], self.max_moves_for_tests)
        self.assertEqual(p_black.name, "Chess_Engine_Stockfish_Black")


class TestRunJsonGolden(unittest.TestCase):
    """Validate that collect_run_metadata outputs the expected structure for key game setups."""

    def _dummy_cfg(self, model: str, *, reasoning_effort: str | None = None, thinking_budget: int | None = None):
        cfg = {
            "config_list": [
                {
                    "model": model,
                    "api_key": "SECRET",
                    "api_type": "openai" if reasoning_effort else "anthropic" if thinking_budget else "openai",
                }
            ],
            "timeout": 600,
            **({"top_p": llm_chess.default_hyperparams["top_p"]} if not thinking_budget else {}),
        }
        if reasoning_effort:
            cfg["config_list"][0]["reasoning_effort"] = reasoning_effort
        if thinking_budget is not None:
            cfg["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}
        return cfg

    def _validate_common(self, md):
        # Basic mandatory sections
        self.assertIn("metadata", md)
        self.assertIn("player_types", md)
        self.assertIn("config", md)
        self.assertIn("llm_configs", md)
        # redact check
        for side in md["llm_configs"].values():
            self.assertEqual(side.get("api_key"), "REDACTED")

    def _normalize(self, md):
        """Strip reactive fields for comparison with golden dicts."""
        md = md.copy()
        md["metadata"]["time_started_formatted"] = "<TIME>"
        md["metadata"]["python_version"] = "<PY>"
        return md

    @patch("llm_chess.time.strftime", return_value="<TIME>")
    @patch("platform.python_version", return_value="<PY>")
    def test_random_vs_llm_black(self, _pv, _ts):
        llm_chess.white_player_type = llm_chess.PlayerType.RANDOM_PLAYER
        llm_chess.black_player_type = llm_chess.PlayerType.LLM_BLACK

        md = collect_run_metadata(
            log_folder_relative="/tmp",
            num_repetitions=1,
            store_individual_logs=False,
            llm_config_white=None,
            llm_config_black=self._dummy_cfg("gpt-b", reasoning_effort="high"),
        )
        golden = {
            "metadata": {
                "time_started_formatted": "<TIME>",
                "log_folder_relative": "/tmp",
                "num_repetitions": 1,
                "store_individual_logs": False,
                "python_version": "<PY>",
            },
            "player_types": {
                "white_player_type": "RANDOM_PLAYER",
                "black_player_type": "LLM_BLACK",
            },
            "config": md["config"],  # re-use since config section not focus here
            "llm_configs": {
                "black": {
                    "model": "gpt-b",
                    "api_type": "openai",
                    "api_key": "REDACTED",
                    "timeout": 600,
                    "reasoning_effort": "high",
                    "top_p": llm_chess.default_hyperparams["top_p"],
                }
            },
        }
        self.assertEqual(self._normalize(md), golden)

    @patch("llm_chess.time.strftime", return_value="<TIME>")
    @patch("platform.python_version", return_value="<PY>")
    def test_llm_vs_llm(self, _pv, _ts):
        llm_chess.white_player_type = llm_chess.PlayerType.LLM_WHITE
        llm_chess.black_player_type = llm_chess.PlayerType.LLM_BLACK

        md = collect_run_metadata(
            log_folder_relative="/tmp",
            num_repetitions=1,
            store_individual_logs=False,
            llm_config_white=self._dummy_cfg("gpt-w", reasoning_effort="low"),
            llm_config_black=self._dummy_cfg("gpt-b", thinking_budget=2048),
        )
        golden = {
            "metadata": {
                "time_started_formatted": "<TIME>",
                "log_folder_relative": "/tmp",
                "num_repetitions": 1,
                "store_individual_logs": False,
                "python_version": "<PY>",
            },
            "player_types": {
                "white_player_type": "LLM_WHITE",
                "black_player_type": "LLM_BLACK",
            },
            "config": md["config"],
            "llm_configs": {
                "white": {
                    "model": "gpt-w",
                    "api_type": "openai",
                    "api_key": "REDACTED",
                    "timeout": 600,
                    "reasoning_effort": "low",
                    "top_p": llm_chess.default_hyperparams["top_p"],
                },
                "black": {
                    "model": "gpt-b",
                    "api_type": "anthropic",
                    "api_key": "REDACTED",
                    "timeout": 600,
                    "thinking_budget": 2048,
                },
            },
        }
        self.assertEqual(self._normalize(md), golden)

    @patch("llm_chess.time.strftime", return_value="<TIME>")
    @patch("platform.python_version", return_value="<PY>")
    def test_engine_vs_llm(self, _pv, _ts):
        llm_chess.white_player_type = llm_chess.PlayerType.CHESS_ENGINE_STOCKFISH
        llm_chess.black_player_type = llm_chess.PlayerType.LLM_BLACK

        md = collect_run_metadata(
            log_folder_relative="/tmp",
            num_repetitions=1,
            store_individual_logs=False,
            llm_config_white=None,
            llm_config_black=self._dummy_cfg("gpt-b"),
        )
        golden = {
            "metadata": {
                "time_started_formatted": "<TIME>",
                "log_folder_relative": "/tmp",
                "num_repetitions": 1,
                "store_individual_logs": False,
                "python_version": "<PY>",
            },
            "player_types": {
                "white_player_type": "CHESS_ENGINE_STOCKFISH",
                "black_player_type": "LLM_BLACK",
            },
            "config": md["config"],
            "chess_engines": md["chess_engines"],
            "llm_configs": {
                "black": {
                    "model": "gpt-b",
                    "api_type": "openai",
                    "api_key": "REDACTED",
                    "timeout": 600,
                    "top_p": llm_chess.default_hyperparams["top_p"],
                }
            },
        }
        self.assertEqual(self._normalize(md), golden)
