import os
import unittest
from unittest.mock import patch

from utils import DEFAULT_HYPERPARAMS, get_llms_autogen_per_model

# ---------------------------------------------------------------------------
# Helper utilities for environment setup
# ---------------------------------------------------------------------------
_ENV_TEMPLATES = {
    "local": [
        "LOCAL_MODEL_NAME_{}",
        "LOCAL_BASE_URL_{}",
        "LOCAL_API_KEY_{}",
    ],
    "openai": [
        "OPENAI_MODEL_NAME_{}",
        "OPENAI_API_KEY_{}",
    ],
    "anthropic": [
        "ANTHROPIC_MODEL_NAME_{}",
        "ANTHROPIC_API_KEY_{}",
    ],
}


def _prepare_env(kind_w: str, kind_b: str):
    """Populate minimal environment variables so utils can build configs."""
    env_updates = {
        "MODEL_KIND_W": kind_w,
        "MODEL_KIND_B": kind_b,
    }

    for key_suffix, provider in zip(["W", "B"], [kind_w, kind_b]):
        for tmpl in _ENV_TEMPLATES.get(provider, []):
            env_updates[tmpl.format(key_suffix)] = f"{provider.lower()}-{key_suffix.lower()}"

    return patch.dict(os.environ, env_updates, clear=False)

# ---------------------------------------------------------------------------
# Per-model config tests
# ---------------------------------------------------------------------------
class TestPerModelConfig(unittest.TestCase):
    """Unit-tests for the per-model configuration system."""

    def test_default_hyperparams_are_applied(self):
        with _prepare_env("local", "local"):
            cfg_w, cfg_b = get_llms_autogen_per_model({}, {})
        self.assertEqual(cfg_w["temperature"], DEFAULT_HYPERPARAMS["temperature"])
        self.assertEqual(cfg_b["top_p"], DEFAULT_HYPERPARAMS["top_p"])

    def test_white_override_does_not_touch_black(self):
        with _prepare_env("local", "local"):
            cfg_w, cfg_b = get_llms_autogen_per_model({"hyperparams": {"temperature": 0.75}}, {})
        self.assertEqual(cfg_w["temperature"], 0.75)
        self.assertEqual(cfg_b["temperature"], DEFAULT_HYPERPARAMS["temperature"])

    def test_reasoning_effort_strips_temp_and_top_p(self):
        with _prepare_env("openai", "openai"):
            cfg_w, cfg_b = get_llms_autogen_per_model({"reasoning_effort": "high"}, {"reasoning_effort": "low"})
        self.assertIn("reasoning_effort", cfg_w)
        self.assertNotIn("temperature", cfg_w)
        self.assertNotIn("top_p", cfg_w)
        self.assertEqual(cfg_b["reasoning_effort"], "low")

    def test_thinking_budget_sets_thinking_and_strips_top_p(self):
        with _prepare_env("openai", "anthropic"):
            cfg_w, cfg_b = get_llms_autogen_per_model({}, {"thinking_budget": 4096})
        self.assertIn("temperature", cfg_w)
        self.assertIn("thinking", cfg_b)
        self.assertEqual(cfg_b["thinking"]["budget_tokens"], 4096)
        self.assertNotIn("top_p", cfg_b)

# ---------------------------------------------------------------------------
# remove_text feature tests
# ---------------------------------------------------------------------------
from custom_agents import AutoReplyAgent

class TestRemoveTextFeature(unittest.TestCase):
    """Unit-tests for per-agent remove_text handling."""

    def test_remove_text_cleans_messages(self):
        pattern = r"<think>.*?</think>"
        raw_msg = "Hello <think>SECRET</think> world"

        # build a proxy agent with remove_text pattern
        proxy = AutoReplyAgent(
            name="Proxy",
            human_input_mode="NEVER",
            is_termination_msg=lambda msg: False,
            max_failed_attempts=3,
            get_current_board=lambda: "board",
            get_legal_moves=lambda: "e2e4",
            make_move=lambda mv: None,
            move_was_made_message="move",
            invalid_action_message="invalid",
            too_many_failed_actions_message="too_many",
            get_current_board_action="get_board",
            get_legal_moves_action="get_moves",
            reflect_action="reflect",
            make_move_action="make_move",
            reflect_prompt="reflect prompt",
            reflection_followup_prompt="follow up",
            remove_text=pattern,
        )

        # Message list with pattern
        msgs = [{"content": raw_msg, "role": "user"}]
        proxy.generate_reply(messages=list(msgs), sender=proxy)  # mutate inside
        self.assertNotIn("<think>", msgs[0]["content"], "Pattern not removed when remove_text set")

        # Disable pattern and ensure content stays
        msgs2 = [{"content": raw_msg, "role": "user"}]
        proxy.remove_text = None
        proxy.generate_reply(messages=msgs2, sender=proxy)
        self.assertIn("<think>", msgs2[0]["content"], "Pattern removed even when remove_text is None")


if __name__ == "__main__":
    unittest.main()