from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from framework.model_identity import infer_provider_or_family


PROVIDER_GROUP_ALIASES: dict[str, tuple[str, ...]] = {
    "Anthropic": ("anthropic", "claude"),
    "OpenAI": ("openai", "chatgpt", "gpt", "o1", "o3", "o4"),
    "Google": ("google", "gemini", "gemma", "bison", "chat"),
    "xAI": ("xai", "grok"),
    "Meta": ("meta", "llama"),
    "Z.ai": ("z ai", "zai", "glm"),
    "Alibaba": ("alibaba", "qwen"),
    "DeepSeek": ("deepseek",),
    "Minimax": ("minimax",),
    "Moonshot": ("moonshot", "kimi"),
    "Amazon": ("amazon", "nova"),
    "Mistral": ("mistral", "magistral", "ministral"),
    "Cohere": ("cohere", "command"),
    "Cerebras": ("cerebras",),
}


def _normalize_provider_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = re.sub(r"[^a-z0-9]+", " ", str(value).strip().casefold())
    return re.sub(r"\s+", " ", text).strip()


_PROVIDER_ALIAS_LOOKUP = {
    _normalize_provider_text(alias): canonical
    for canonical, aliases in PROVIDER_GROUP_ALIASES.items()
    for alias in (canonical, *aliases)
}


def _canonical_provider_for_value(value: object) -> str | None:
    normalized = _normalize_provider_text(value)
    if not normalized:
        return None
    direct_match = _PROVIDER_ALIAS_LOOKUP.get(normalized)
    if direct_match:
        return direct_match
    inferred_provider, _ = infer_provider_or_family(value)
    inferred_normalized = _normalize_provider_text(inferred_provider)
    if inferred_normalized and inferred_normalized != normalized:
        return _PROVIDER_ALIAS_LOOKUP.get(inferred_normalized)
    return None


def canonicalize_provider_filter(value: str | None) -> str | None:
    if value is None:
        return None
    canonical = _canonical_provider_for_value(value)
    if canonical:
        return canonical
    text = str(value).strip()
    return text or None


def load_inventory_provider_lookup(inventory_path: Path) -> dict[str, str]:
    if not inventory_path.exists():
        return {}
    inventory = pd.read_csv(inventory_path)
    if "llm_chess_player" not in inventory.columns or "provider_or_family" not in inventory.columns:
        return {}
    return (
        inventory.loc[:, ["llm_chess_player", "provider_or_family"]]
        .fillna("")
        .set_index("llm_chess_player")["provider_or_family"]
        .to_dict()
    )


def derive_provider_group(row: pd.Series, inventory_provider_lookup: dict[str, str]) -> dict[str, str]:
    llm_chess_player = str(row.get("llm_chess_player") or "").strip()
    inventory_provider = inventory_provider_lookup.get(llm_chess_player, "")
    canonical_inventory_provider = _canonical_provider_for_value(inventory_provider)
    if canonical_inventory_provider:
        return {
            "provider_group": canonical_inventory_provider,
            "provider_group_source": "llm_chess_inventory",
            "provider_group_confidence": "high",
        }

    if llm_chess_player:
        canonical_player_provider = _canonical_provider_for_value(llm_chess_player)
        if canonical_player_provider:
            return {
                "provider_group": canonical_player_provider,
                "provider_group_source": "llm_chess_player",
                "provider_group_confidence": "medium",
            }

    mapping_provider = str(row.get("provider_or_family") or "").strip()
    canonical_mapping_provider = _canonical_provider_for_value(mapping_provider)
    if canonical_mapping_provider:
        return {
            "provider_group": canonical_mapping_provider,
            "provider_group_source": "mapping_provider_or_family",
            "provider_group_confidence": "medium",
        }
    if mapping_provider:
        return {
            "provider_group": mapping_provider,
            "provider_group_source": "mapping_provider_or_family",
            "provider_group_confidence": "low",
        }

    eval_model_label = str(row.get("eval_model_label") or "").strip()
    canonical_eval_provider = _canonical_provider_for_value(eval_model_label)
    if canonical_eval_provider:
        return {
            "provider_group": canonical_eval_provider,
            "provider_group_source": "eval_model_label",
            "provider_group_confidence": "low",
        }

    return {
        "provider_group": "unknown",
        "provider_group_source": "unknown",
        "provider_group_confidence": "unknown",
    }