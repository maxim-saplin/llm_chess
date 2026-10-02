import copy
import os
import unittest
from unittest.mock import patch

import llm_chess
from autogen.llm_config import LLMConfig
from run_multiple_games import _extract_llm_model_and_suffix
from utils import get_llms, normalize_reasoning_effort_config

# ---------------------------------------------------------------------------
# Helper utilities for environment setup
# ---------------------------------------------------------------------------
_ENV_TEMPLATES = {
    "local": [
        "LOCAL_MODEL_NAME_{}",
        "LOCAL_BASE_URL_{}",
        "LOCAL_API_KEY_{}",
    ],
    "azure": [
        "AZURE_OPENAI_VERSION_{}",
        "AZURE_OPENAI_ENDPOINT_{}",
        "AZURE_OPENAI_KEY_{}",
        "AZURE_OPENAI_DEPLOYMENT_{}",
    ],
    "azure_responses": [
        "AZURE_OPENAI_VERSION_{}",
        "AZURE_OPENAI_ENDPOINT_{}",
        "AZURE_OPENAI_KEY_{}",
        "AZURE_OPENAI_DEPLOYMENT_{}",
    ],
    "openai": [
        "OPENAI_MODEL_NAME_{}",
        "OPENAI_API_KEY_{}",
    ],
    "xai": [
        "XAI_MODEL_NAME_{}",
        "XAI_API_KEY_{}",
    ],
    "anthropic": [
        "ANTHROPIC_MODEL_NAME_{}",
        "ANTHROPIC_API_KEY_{}",
    ],
    "groq": [
        "GROQ_MODEL_NAME_{}",
        "GROQ_API_KEY_{}",
    ],
    "cerebras": [
        "CEREBRAS_MODEL_NAME_{}",
        "CEREBRAS_API_KEY_{}",
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
            env_key = tmpl.format(key_suffix)
            if "ENDPOINT" in env_key:
                env_updates[env_key] = f"https://{provider.lower()}-{key_suffix.lower()}.openai.azure.com"
            elif "VERSION" in env_key:
                env_updates[env_key] = "2025-03-01-preview"
            elif "KEY" in env_key:
                env_updates[env_key] = f"{provider.lower()}-{key_suffix.lower()}-key"
            else:
                env_updates[env_key] = f"{provider.lower()}-{key_suffix.lower()}"

    return patch.dict(os.environ, env_updates, clear=False)

# ---------------------------------------------------------------------------
# Per-model config tests
# ---------------------------------------------------------------------------
class TestPerModelConfig(unittest.TestCase):
    """Unit-tests for the per-model configuration system."""

    def test_default_hyperparams_are_applied(self):
        with _prepare_env("local", "local"):
            cfg_w, cfg_b = get_llms(white_hyperparams={"hyperparams": llm_chess.default_hyperparams}, black_hyperparams={"hyperparams": llm_chess.default_hyperparams})
        self.assertEqual(cfg_w["temperature"], llm_chess.default_hyperparams["temperature"])
        self.assertEqual(cfg_b["top_p"], llm_chess.default_hyperparams["top_p"])

    def test_white_override_does_not_touch_black(self):
        with _prepare_env("local", "local"):
            cfg_w, cfg_b = get_llms(white_hyperparams={"hyperparams": {"temperature": 0.75}}, black_hyperparams={"hyperparams": llm_chess.default_hyperparams})
        self.assertEqual(cfg_w["temperature"], 0.75)
        self.assertEqual(cfg_b["temperature"], llm_chess.default_hyperparams["temperature"])

    def test_reasoning_effort_uses_extra_body_and_bypasses_ag2_literal(self):
        with _prepare_env("openai", "openai"):
            cfg_w, cfg_b = get_llms(
                white_hyperparams={"reasoning_effort": "max", "hyperparams": llm_chess.default_hyperparams},
                black_hyperparams={"reasoning_effort": "low", "hyperparams": llm_chess.default_hyperparams},
            )

        provider_conf = cfg_w["config_list"][0]
        self.assertEqual(provider_conf["extra_body"], {"reasoning_effort": "max"})
        self.assertNotIn("reasoning_effort", provider_conf)
        self.assertEqual(cfg_b["config_list"][0]["extra_body"]["reasoning_effort"], "low")
        # Temperature is removed, while top_p remains as before the migration.
        self.assertNotIn("temperature", cfg_w)
        self.assertIn("top_p", cfg_w)

        # AG2's typed Literal rejects "max" in the direct field; the raw body field validates.
        typed_config = LLMConfig.ensure_config(copy.deepcopy(cfg_w))
        self.assertEqual(
            typed_config.config_list[0].get("extra_body"),
            {"reasoning_effort": "max"},
        )

    def test_reasoning_effort_provider_overrides_are_normalized_and_merged(self):
        with _prepare_env("openai", "openai"):
            _, cfg = get_llms(
                white_hyperparams={},
                black_hyperparams={
                    "reasoning_effort": "max",
                    "hyperparams": llm_chess.default_hyperparams,
                    "provider_overrides": {"extra_body": {"vendor_option": True}},
                },
            )

        provider_conf = cfg["config_list"][0]
        self.assertEqual(
            provider_conf["extra_body"],
            {"vendor_option": True, "reasoning_effort": "max"},
        )
        self.assertNotIn("reasoning_effort", provider_conf)
        self.assertNotIn("temperature", cfg)

    def test_legacy_reasoning_provider_override_is_moved_to_extra_body(self):
        with _prepare_env("openai", "openai"):
            _, cfg = get_llms(
                white_hyperparams={},
                black_hyperparams={"provider_overrides": {"reasoning_effort": "max"}},
            )

        provider_conf = cfg["config_list"][0]
        self.assertEqual(provider_conf["extra_body"], {"reasoning_effort": "max"})
        self.assertNotIn("reasoning_effort", provider_conf)

    def test_legacy_raw_openai_config_is_normalized_without_mutation(self):
        legacy_config = {
            "temperature": 0.5,
            "config_list": [
                {"api_type": "openai", "model": "gpt-test", "reasoning_effort": "max"}
            ],
        }

        normalized = normalize_reasoning_effort_config(legacy_config)

        self.assertEqual(
            normalized["config_list"][0]["extra_body"],
            {"reasoning_effort": "max"},
        )
        self.assertNotIn("reasoning_effort", normalized["config_list"][0])
        self.assertNotIn("temperature", normalized)
        self.assertEqual(legacy_config["config_list"][0]["reasoning_effort"], "max")
        self.assertEqual(legacy_config["temperature"], 0.5)

    def test_responses_extra_body_merges_reasoning_options(self):
        legacy_config = {
            "temperature": 0.5,
            "config_list": [
                {
                    "api_type": "responses",
                    "model": "responses-test",
                    "reasoning_effort": "max",
                    "extra_body": {"reasoning": {"summary": "auto", "effort": "low"}},
                }
            ],
        }

        normalized = normalize_reasoning_effort_config(legacy_config)

        self.assertEqual(
            normalized["config_list"][0]["extra_body"],
            {"reasoning": {"summary": "auto", "effort": "max"}},
        )
        self.assertEqual(
            legacy_config["config_list"][0]["extra_body"]["reasoning"]["effort"],
            "low",
        )

    def test_invalid_extra_body_conflicts_fail_before_provider_validation(self):
        invalid_configs = [
            {
                "config_list": [
                    {"api_type": "openai", "reasoning_effort": "max", "extra_body": "bad"}
                ]
            },
            {
                "config_list": [
                    {
                        "api_type": "responses",
                        "reasoning_effort": "max",
                        "extra_body": {"reasoning": "bad"},
                    }
                ]
            },
        ]

        for config in invalid_configs:
            with self.subTest(config=config), self.assertRaises(ValueError):
                normalize_reasoning_effort_config(config)

    def test_custom_chat_providers_use_extra_body_and_validate(self):
        with _prepare_env("groq", "cerebras"):
            cfg_groq, cfg_cerebras = get_llms(
                white_hyperparams={"reasoning_effort": "max"},
                black_hyperparams={"reasoning_effort": "max"},
            )

        for cfg in (cfg_groq, cfg_cerebras):
            provider_conf = cfg["config_list"][0]
            self.assertEqual(provider_conf["extra_body"], {"reasoning_effort": "max"})
            self.assertNotIn("reasoning_effort", provider_conf)
            typed_config = LLMConfig.ensure_config(copy.deepcopy(cfg))
            self.assertEqual(
                typed_config.config_list[0].get("extra_body"),
                {"reasoning_effort": "max"},
            )

    def test_unsupported_provider_and_none_effort_are_unchanged(self):
        native_config = {
            "temperature": 0.4,
            "config_list": [{"api_type": "anthropic", "reasoning_effort": "high"}],
        }
        no_effort_config = {
            "temperature": 0.4,
            "config_list": [{"api_type": "openai", "reasoning_effort": None}],
        }

        self.assertIs(normalize_reasoning_effort_config(native_config), native_config)
        self.assertIs(normalize_reasoning_effort_config(no_effort_config), no_effort_config)
        self.assertEqual(native_config["config_list"][0]["reasoning_effort"], "high")
        self.assertEqual(no_effort_config["temperature"], 0.4)

    def test_xai_openai_compatible_config_uses_extra_body(self):
        with _prepare_env("xai", "xai"):
            cfg_w, _ = get_llms(
                white_hyperparams={"reasoning_effort": "max"},
                black_hyperparams={},
            )

        provider_conf = cfg_w["config_list"][0]
        self.assertEqual(provider_conf["extra_body"], {"reasoning_effort": "max"})
        self.assertNotIn("reasoning_effort", provider_conf)
        typed_config = LLMConfig.ensure_config(copy.deepcopy(cfg_w))
        self.assertEqual(
            typed_config.config_list[0].get("extra_body"),
            {"reasoning_effort": "max"},
        )

    def test_thinking_budget_sets_thinking_and_strips_top_p(self):
        with _prepare_env("openai", "anthropic"):
            cfg_w, cfg_b = get_llms(white_hyperparams={"hyperparams": llm_chess.default_hyperparams}, black_hyperparams={"thinking_budget": 4096, "hyperparams": llm_chess.default_hyperparams})
        self.assertIn("temperature", cfg_w)
        self.assertIn("thinking", cfg_b["config_list"][0])
        self.assertEqual(cfg_b["config_list"][0]["thinking"]["budget_tokens"], 4096)
        self.assertNotIn("top_p", cfg_b)

    def test_azure_responses_uses_responses_api_shape(self):
        with _prepare_env("azure_responses", "local"):
            cfg_w, _ = get_llms(
                white_hyperparams={
                    "reasoning_effort": "high",
                    "hyperparams": llm_chess.default_hyperparams,
                },
                black_hyperparams={"hyperparams": llm_chess.default_hyperparams},
            )

        provider_conf = cfg_w["config_list"][0]
        self.assertEqual(provider_conf["api_type"], "responses")
        self.assertEqual(provider_conf["model"], "azure_responses-w")
        self.assertEqual(
            provider_conf["base_url"],
            "https://azure_responses-w.openai.azure.com/openai/v1",
        )
        self.assertEqual(
            provider_conf["default_query"],
            {"api-version": "2025-03-01-preview"},
        )
        self.assertEqual(
            provider_conf["extra_body"],
            {"reasoning": {"effort": "high"}},
        )
        self.assertNotIn("reasoning_effort", provider_conf)
        self.assertNotIn("api_version", provider_conf)
        self.assertNotIn("temperature", cfg_w)
        self.assertIn("top_p", cfg_w)
        typed_config = LLMConfig.ensure_config(copy.deepcopy(cfg_w))
        self.assertEqual(
            typed_config.config_list[0].get("extra_body"),
            {"reasoning": {"effort": "high"}},
        )

    def test_azure_still_uses_chat_completions_shape(self):
        with _prepare_env("azure", "local"):
            cfg_w, _ = get_llms(
                white_hyperparams={
                    "reasoning_effort": "max",
                    "hyperparams": llm_chess.default_hyperparams,
                },
                black_hyperparams={"hyperparams": llm_chess.default_hyperparams},
            )

        provider_conf = cfg_w["config_list"][0]
        self.assertEqual(provider_conf["api_type"], "azure")
        self.assertEqual(provider_conf["model"], "azure-w")
        self.assertEqual(provider_conf["base_url"], "https://azure-w.openai.azure.com")
        self.assertEqual(provider_conf["api_version"], "2025-03-01-preview")
        self.assertEqual(provider_conf["extra_body"], {"reasoning_effort": "max"})
        self.assertNotIn("reasoning_effort", provider_conf)
        typed_config = LLMConfig.ensure_config(copy.deepcopy(cfg_w))
        self.assertEqual(
            typed_config.config_list[0].get("extra_body"),
            {"reasoning_effort": "max"},
        )

    def test_reasoning_effort_log_suffix_reads_extra_body(self):
        self.assertEqual(
            _extract_llm_model_and_suffix(
                {
                    "config_list": [
                        {
                            "model": "gpt-test",
                            "extra_body": {"reasoning_effort": "max"},
                        }
                    ]
                }
            ),
            "gpt-test-max",
        )
        self.assertEqual(
            _extract_llm_model_and_suffix(
                {"config_list": [{"model": "gpt-test", "reasoning_effort": "high"}]}
            ),
            "gpt-test-high",
        )

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