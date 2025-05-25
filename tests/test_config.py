import requests

from .helper import _MockServerTestCaseBase

# Importing after env vars are set
import llm_chess
from utils import get_llms_autogen

class TestConfigurationPropagation(_MockServerTestCaseBase):
    """Test that configuration parameters from run_multiple_games.py globals are properly propagated."""
    
    def setUp(self):
        try:
            response = requests.post("http://localhost:8080/v1/reset", json={"scenarioType": "default", "useThinking": False}, timeout=10)
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
        llm_config_white, llm_config_black = get_llms_autogen(
            hyperparams=custom_hyperparams,
            reasoning_effort=None,
            thinking_budget=None
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
        self.assertEqual(cfg.get("top_p"), 0.8)

        self.assertIsNotNone(game_stats["winner"])
        self.assertIsNotNone(game_stats["reason"])


    def test_custom_hyperparameters_propagation_white(self):
        """Test that custom hyperparameters are properly applied to LLM configs."""

        llm_chess.white_player_type = llm_chess.PlayerType.LLM_WHITE
        llm_chess.black_player_type = llm_chess.PlayerType.RANDOM_PLAYER

        custom_hyperparams = {"temperature": 0.7, "top_p": 0.8}
        llm_config_white, llm_config_black = get_llms_autogen(
            hyperparams=custom_hyperparams,
            reasoning_effort=None,
            thinking_budget=None
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
        self.assertEqual(cfg.get("top_p"), 0.8)

        self.assertIsNotNone(game_stats["winner"])
        self.assertIsNotNone(game_stats["reason"])

    def test_reasoning_effort_propagation(self):
        """Test that reasoning_effort parameter is properly applied."""

        # Define reasoning effort
        reasoning_effort = "high"

        # Get LLM configs with reasoning effort
        llm_config_white, llm_config_black = get_llms_autogen(
            hyperparams=llm_chess.default_hyperparams,
            reasoning_effort=reasoning_effort,
            thinking_budget=None
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
        llm_config_white, llm_config_black = get_llms_autogen(
            hyperparams=llm_chess.default_hyperparams,
            reasoning_effort=None,
            thinking_budget=thinking_budget
        )

        game_stats, player_white, player_black = llm_chess.run(
            log_dir=None,
            llm_config_white=llm_config_white,
            llm_config_black=llm_config_black
        )

        # With thinking_budget, top-level hyperparameters are removed
        cfg = player_black.llm_config
        self.assertNotIn("temperature", cfg)
        self.assertNotIn("top_p", cfg)
        # If using Anthropic, the inner config would have a 'thinking' field:
        inner = cfg.get("config_list", [])[0]
        if "thinking" in inner:
            self.assertEqual(inner["thinking"].get("budget_tokens"), thinking_budget)

        self.assertIsNotNone(game_stats["winner"])
        self.assertIsNotNone(game_stats["reason"])

    def test_combined_configuration_propagation(self):
        """Test that all configuration parameters work together."""

        custom_hyperparams = {"temperature": 0.9, "top_p": 0.95}
        reasoning_effort = "medium"
        thinking_budget = 8000
        llm_config_white, llm_config_black = get_llms_autogen(
            hyperparams=custom_hyperparams,
            reasoning_effort=reasoning_effort,
            thinking_budget=thinking_budget
        )

        game_stats, player_white, player_black = llm_chess.run(
            log_dir=None,
            llm_config_white=llm_config_white,
            llm_config_black=llm_config_black
        )

        # With both reasoning_effort and thinking_budget, top-level temperature & top_p are removed
        cfg = player_black.llm_config
        self.assertNotIn("temperature", cfg)
        self.assertNotIn("top_p", cfg)
        # Inner config must still exist without error
        self.assertGreater(len(cfg.get("config_list", [])), 0)

        self.assertIsNotNone(game_stats["winner"])
        self.assertIsNotNone(game_stats["reason"])

    def test_default_vs_custom_hyperparams_difference(self):
        """Test difference between default and custom hyperparameters."""

        default_cfg_white, default_cfg_black = get_llms_autogen(
            llm_chess.default_hyperparams, None, None
        )
        custom_hyperparams = {"temperature": 0.9, "top_p": 0.7}
        custom_cfg_white, custom_cfg_black = get_llms_autogen(
            custom_hyperparams, None, None
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
        llm_config_white, llm_config_black = get_llms_autogen(
            test_hyperparams, None, None
        )

        llm_chess.max_game_moves = 4
        game_stats, player_white, player_black = llm_chess.run(
            log_dir=self.temp_dir,
            llm_config_white=llm_config_white,
            llm_config_black=llm_config_black
        )

        cfg = player_black.llm_config
        self.assertEqual(cfg.get("temperature"), 0.42)
        self.assertEqual(cfg.get("top_p"), 0.88)

        self.assertIsNotNone(game_stats["winner"])
        self.assertLessEqual(game_stats["number_of_moves"], 4)
        self.assertEqual(game_stats["player_black"]["wrong_moves"], 0)
        self.assertEqual(game_stats["player_black"]["wrong_actions"], 0)

