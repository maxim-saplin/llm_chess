"""Normalize model metadata for the public leaderboard visualizations."""

from __future__ import annotations

import csv
import json
import os
import re
import tempfile
from typing import Dict, Iterable, List, Tuple


MODEL_METADATA_ALIASES: Dict[str, str] = {
    "claude-opus-4-5-20251101_thinking_16000": "claude-opus-4-5-thinking_16000",
}

# These rows have malformed or shifted metadata columns. Keep the model name
# untouched and use the intended reasoning classification from the audit.
MODEL_METADATA_OVERRIDES: Dict[str, Tuple[str, str]] = {
    "muse-glimmer-30b@q4_k_m": ("muse-glimmer-30b@q4_k_m", "default"),
    "unsloth/qwen3.8-27b@q2_k_xl": ("unsloth/qwen3.8-27b@q2_k_xl", "default"),
}

_QUALITATIVE_LEVELS = {"low", "medium", "high", "xhigh"}
_EFFORT_SUFFIX = re.compile(
    r"(?P<separator>[_-])(?P<mode>adaptive-thinking|thinking)[_-]"
    r"(?P<level>low|medium|high|xhigh)(?P<config>(?:[@|].*)?)$",
    re.IGNORECASE,
)
_BUDGET_SUFFIX = re.compile(
    r"(?P<separator>[_-])(?P<mode>adaptive-thinking|thinking)_(?P<budget>\d+)"
    r"(?P<config>(?:[@|].*)?)$",
    re.IGNORECASE,
)
_PLAIN_THINKING_SUFFIX = re.compile(
    r"(?P<separator>[_-])(?P<mode>adaptive-thinking|thinking)(?P<config>(?:[@|].*)?)$",
    re.IGNORECASE,
)
_REASONING_SUFFIX = re.compile(
    r"(?P<separator>[_-])(?P<mode>non-reasoning|reasoning)(?P<config>(?:[@|].*)?)$",
    re.IGNORECASE,
)
_LEVEL_SUFFIX = re.compile(
    r"(?P<separator>[_-])(?P<level>low|medium|high|xhigh)(?P<config>(?:[@|].*)?)$",
    re.IGNORECASE,
)


def _status_level(reasoning_status: str) -> str:
    status = (reasoning_status or "").strip().lower()
    if status == "reasoning":
        return "default"
    if status == "not_reasoning":
        return "none"
    return "unknown"


def split_model_identity(model: str, reasoning_status: str = "") -> Tuple[str, str]:
    """Return ``(mode_family, reasoning_level)`` without changing ``model``."""
    name = (model or "").strip()
    if not name:
        return "", "unknown"

    if name in MODEL_METADATA_OVERRIDES:
        return MODEL_METADATA_OVERRIDES[name]

    family = name
    level = ""

    match = _EFFORT_SUFFIX.search(family)
    if match:
        family = family[: match.start()] + (match.group("config") or "")
        level = match.group("level").lower()
    else:
        match = _BUDGET_SUFFIX.search(family)
        if match:
            family = family[: match.start()] + (match.group("config") or "")
            level = f"budget_{match.group('budget')}"
        else:
            match = _REASONING_SUFFIX.search(family)
            if match:
                family = family[: match.start()] + (match.group("config") or "")
                level = "none" if match.group("mode").lower() == "non-reasoning" else "default"
            else:
                match = _LEVEL_SUFFIX.search(family)
                if match:
                    family = family[: match.start()] + (match.group("config") or "")
                    level = match.group("level").lower()
                else:
                    match = _PLAIN_THINKING_SUFFIX.search(family)
                    if match:
                        family = family[: match.start()] + (match.group("config") or "")
                        level = "default"

    if not level:
        level = _status_level(reasoning_status)

    # A malformed row or a future naming convention must never leak the
    # Anthropic implementation detail into the public reasoning level.
    level = level.replace("adaptive_thinking", "").strip("_-") or "unknown"
    return family or name, level


def enrich_metadata_rows(rows: Iterable[dict]) -> List[dict]:
    enriched: List[dict] = []
    for source in rows:
        row = dict(source)
        model = (row.get("model") or "").strip()
        family, level = split_model_identity(model, row.get("reasoning_status", ""))
        row["mode_family"] = family
        row["reasoning_level"] = level
        enriched.append(row)
    return enriched


def load_metadata_rows(metadata_csv_path: str) -> Tuple[List[str], List[dict]]:
    with open(metadata_csv_path, "r", encoding="utf-8", newline="") as metadata_file:
        reader = csv.DictReader(metadata_file)
        fieldnames = list(reader.fieldnames or [])
        rows = enrich_metadata_rows(reader)

    for field in ("mode_family", "reasoning_level"):
        if field not in fieldnames:
            fieldnames.append(field)
    return fieldnames, rows


def write_enriched_metadata_csv(metadata_csv_path: str) -> List[dict]:
    fieldnames, rows = load_metadata_rows(metadata_csv_path)
    directory = os.path.dirname(os.path.abspath(metadata_csv_path)) or "."
    fd, temporary_path = tempfile.mkstemp(prefix=".models_metadata.", suffix=".csv", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as output_file:
            writer = csv.DictWriter(output_file, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow({field: row.get(field, "") for field in fieldnames})
        os.replace(temporary_path, metadata_csv_path)
    finally:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)
    return rows


def write_docs_metadata_js(
    metadata_csv_path: str,
    js_path: str,
) -> None:
    rows = write_enriched_metadata_csv(metadata_csv_path)
    models = {
        row["model"]: {
            "mode_family": row["mode_family"],
            "reasoning_level": row["reasoning_level"],
        }
        for row in rows
        if row.get("model")
    }
    payload = {
        "models": models,
        "aliases": MODEL_METADATA_ALIASES,
    }
    javascript = "const modelMetadata = " + json.dumps(payload, indent=2, sort_keys=True) + ";\n"
    os.makedirs(os.path.dirname(os.path.abspath(js_path)), exist_ok=True)
    with open(js_path, "w", encoding="utf-8") as output_file:
        output_file.write(javascript)

