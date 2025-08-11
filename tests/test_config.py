import os
import requests
from unittest.mock import patch

from .helper import _MockServerTestCaseBase, get_mock_base_url

# Importing after env vars are set
import llm_chess
from utils import get_llms

class TestConfigurationPropagation(_MockServerTestCaseBase):
    """Test that configuration parameters from run_multiple_games.py globals are properly propagated."""
    
    def setUp(self):
        try:
            base_url = get_mock_base_url()
            response = requests.post(f"{base_url}/reset", json={"scenarioType": "default", "useThinking": False}, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            self.fail(f"Failed to reset mock server: {e}")
            
        # Configure game settings for testing
        llm_chess.white_player_type = llm_chess.PlayerType.RANDOM_PLAYER
        llm_chess.black_player_type = llm_chess.PlayerType.LLM_BLACK
        llm_chess.max_game_moves = 2
        llm_chess.visualize_board = False
        llm_chess.throttle_delay = 0
        llm_chess.dialog_turn_delay = 0
        llm_chess.random_print_board = False

    def test_custom_hyperparameters_propagation(self):
        """Test that custom hyperparameters are properly applied to LLM configs."""

        custom_hyperparams = {"temperature": 0.7, "top_p": 0.8}
        black_config = {"hyperparams": custom_hyperparams}
        llm_config_white, llm_config_black = get_llms(
            white_hyperparams={},
            black_hyperparams=black_config
        )

        game_stats, _, player_black = llm_chess.run(
            log_dir=None,
            llm_config_white=llm_config_white,
            llm_config_black=llm_config_black
        )

        # The custom hyperparameters should be on the top-level config dict
        cfg = player_black.llm_config
        self.assertIsNotNone(cfg)
        self.assertEqual(cfg.get("temperature"), 0.7)
        self.assertEqual(cfg.config_list[0].get("top_p"), 0.8)

        self.assertIsNotNone(game_stats["winner"])
        self.assertIsNotNone(game_stats["reason"])


    def test_custom_hyperparameters_propagation_white(self):
        """Test that custom hyperparameters are properly applied to LLM configs."""

        llm_chess.white_player_type = llm_chess.PlayerType.LLM_WHITE
        llm_chess.black_player_type = llm_chess.PlayerType.RANDOM_PLAYER

        custom_hyperparams = {"temperature": 0.7, "top_p": 0.8}
        white_config = {"hyperparams": custom_hyperparams}
        llm_config_white, llm_config_black = get_llms(
            white_hyperparams=white_config,
            black_hyperparams={}
        )

        game_stats, player_white, _ = llm_chess.run(
            log_dir=None,
            llm_config_white=llm_config_white,
            llm_config_black=llm_config_black
        )

        # The custom hyperparameters should be on the top-level config dict
        cfg = player_white.llm_config
        self.assertIsNotNone(cfg)
        self.assertEqual(cfg.get("temperature"), 0.7)
        self.assertEqual(cfg.config_list[0].get("top_p"), 0.8)

        self.assertIsNotNone(game_stats["winner"])
        self.assertIsNotNone(game_stats["reason"])

    def test_reasoning_effort_propagation(self):
        """Test that reasoning_effort parameter is properly applied."""

        # Define reasoning effort
        reasoning_effort = "high"

        # Get LLM configs with reasoning effort
        black_config = {"reasoning_effort": reasoning_effort}
        llm_config_white, llm_config_black = get_llms(
            white_hyperparams={},
            black_hyperparams=black_config
        )

        # Run game with reasoning effort config
        game_stats, _, _ = llm_chess.run(
            log_dir=None,
            llm_config_white=llm_config_white,
            llm_config_black=llm_config_black
        )

        # Azure (white) config should include reasoning_effort in its inner config
        cfg = llm_config_black
        inner_white = cfg["config_list"][0]
        self.assertEqual(inner_white.get("reasoning_effort"), reasoning_effort)
        # Because reasoning_effort was set, top-level temperature should be removed
        self.assertNotIn("temperature", cfg)

        self.assertIsNotNone(game_stats["winner"])
        self.assertIsNotNone(game_stats["reason"])

    def test_thinking_budget_propagation(self):
        """Test that thinking_budget parameter is properly applied."""

        thinking_budget = 5000
        black_config = {"thinking_budget": thinking_budget}
        env_patch = {
            "MODEL_KIND_B": "anthropic",
            "ANTHROPIC_MODEL_NAME_B": "anthropic-test",
            "ANTHROPIC_API_KEY_B": "dummy"
        }
        with patch.dict(os.environ, env_patch, clear=False):
            llm_config_white, llm_config_black = get_llms(
                white_hyperparams={},
                black_hyperparams=black_config
            )

        game_stats, _, player_black = llm_chess.run(
            log_dir=None,
            llm_config_white=llm_config_white,
            llm_config_black=llm_config_black
        )

        # With thinking_budget, top-level hyperparameters are removed
        cfg = player_black.llm_config

        self.assertIsNone(cfg.temperature)
        self.assertIsNone(cfg.config_list[0]["top_p"])

        self.assertIsNotNone(game_stats["winner"])
        self.assertIsNotNone(game_stats["reason"])

    def test_combined_configuration_propagation(self):
        """Test that all configuration parameters work together."""

        custom_hyperparams = {"temperature": 0.9, "top_p": 0.95}
        thinking_budget = 8000
        black_config = {
            "hyperparams": custom_hyperparams,
            "thinking_budget": thinking_budget
        }
        env_patch = {
            "MODEL_KIND_B": "anthropic",
            "ANTHROPIC_MODEL_NAME_B": "anthropic-test",
            "ANTHROPIC_API_KEY_B": "dummy"
        }
        with patch.dict(os.environ, env_patch, clear=False):
            llm_config_white, llm_config_black = get_llms(
                white_hyperparams={},
                black_hyperparams=black_config
            )

        game_stats, _, player_black = llm_chess.run(
            log_dir=None,
            llm_config_white=llm_config_white,
            llm_config_black=llm_config_black
        )

        # With both reasoning_effort and thinking_budget, top-level temperature & top_p are removed
        cfg = player_black.llm_config
        self.assertIsNone(cfg.temperature)
        self.assertIsNone(cfg.config_list[0]["top_p"])
        # Inner config must still exist without error
        self.assertGreater(len(cfg.get("config_list", [])), 0)

        self.assertIsNotNone(game_stats["winner"])
        self.assertIsNotNone(game_stats["reason"])

    def test_default_vs_custom_hyperparams_difference(self):
        """Test difference between default and custom hyperparameters."""

        _, default_cfg_black = get_llms(
            white_hyperparams={}, black_hyperparams={}
        )
        custom_hyperparams = {"temperature": 0.9, "top_p": 0.7}
        black_config = {"hyperparams": custom_hyperparams}
        _, custom_cfg_black = get_llms(
            white_hyperparams={}, black_hyperparams=black_config
        )

        default_temp = default_cfg_black.get("temperature")
        custom_temp = custom_cfg_black.get("temperature")
        default_top_p = default_cfg_black.get("top_p")
        custom_top_p = custom_cfg_black.get("top_p")

        self.assertNotEqual(default_temp, custom_temp)
        self.assertNotEqual(default_top_p, custom_top_p)
        self.assertEqual(custom_temp, 0.9)
        self.assertEqual(custom_top_p, 0.7)

    def test_config_persistence_through_game_execution(self):
        """Test that configurations persist throughout game execution."""

        test_hyperparams = {"temperature": 0.42, "top_p": 0.88}
        black_config = {"hyperparams": test_hyperparams}
        llm_config_white, llm_config_black = get_llms(
            white_hyperparams={}, black_hyperparams=black_config
        )

        llm_chess.max_game_moves = 4
        game_stats, _, player_black = llm_chess.run(
            log_dir=self.temp_dir,
            llm_config_white=llm_config_white,
            llm_config_black=llm_config_black
        )

        cfg = player_black.llm_config
        self.assertEqual(cfg.get("temperature"), 0.42)
        self.assertEqual(cfg.config_list[0].get("top_p"), 0.88)

        self.assertIsNotNone(game_stats["winner"])
        self.assertLessEqual(game_stats["number_of_moves"], 4)
        self.assertEqual(game_stats["player_black"]["wrong_moves"], 0)
        self.assertEqual(game_stats["player_black"]["wrong_actions"], 0)

