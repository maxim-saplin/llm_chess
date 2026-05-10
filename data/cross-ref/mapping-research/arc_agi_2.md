# ARC-AGI-2 Mapping Research

Mapping file: `data/cross-ref/mappings/arc_agi_2.csv`

Access date: 2026-04-28.

## Run-Time Source Of Truth

- `data/cross-ref/run_cross_ref.py arc_agi_2` uses `data/cross-ref/mappings/arc_agi_2.csv` directly.
- The mapping CSV is the live run-time source of truth for ARC cross-reference runs.
- The notes in this file explain how the CSV was built and why some rows remain unresolved. They do not override the mapping CSV that the runner actually loads.

## Sources Used

- Leaderboard: <https://arcprize.org/leaderboard>
- ARC-AGI-2 page: <https://arcprize.org/arc-agi/2>
- ARC announcement / methodology framing: <https://arcprize.org/blog/announcing-arc-agi-2-and-arc-prize-2025>
- ARC policy page: <https://arcprize.org/policy>
- LLM Chess inventory: `data/cross-ref/model-identity/llm_chess_models.csv`

## Decision Rules Applied

- Exact family, tier, version, and config matches are preferred.
- `alias` is used when the benchmark row and the LLM Chess row are the same model/config with only a surface-name difference.
- `variant-compatible` is used when the same model family is clear but the benchmark row adds a config axis that is not encoded the same way in the LLM Chess player ID.
- `ambiguous` is used when multiple plausible LLM Chess rows exist or when the benchmark row introduces a distinct config axis such as `Pro`, `xHigh`, `Max`, `Refine.`, `Deep Think`, token budgets, preview variants, or context-window variants.
- `unmatched` is used when the family or version is absent from the current LLM Chess inventory.
- `excluded` is used for human baselines and benchmark-system rows that should not be treated as one model identity.

## High-Impact Outcomes

- GPT-5.5 and Claude 4.7 rows remain `unmatched` because there are no corresponding current LLM Chess rows.
- Gemini 3.1 Pro (Preview), Grok 4.20 (Reasoning), GLM-5, Kimi K2.5, Minimax M2.5, GPT-5.4 tier rows, GPT-5.2 tier rows, GPT-5 tier rows, o3 tier rows, o4-mini tier rows, and several legacy-model rows map cleanly.
- Gemini `Deep Think`, GPT `Pro`, `xHigh`, ARC `Refine.`, Claude 4.6 `120K`, and many token-budget rows remain `ambiguous` on purpose.
- Human and system baselines such as `Human Panel`, `Avg. Mturker`, `Stem Grad`, `NVARC`, `ARChitects`, `Icecuber`, `TRM`, and `HRM` are preserved but `excluded` from model matching.

## Current Status Mix

Generated from the current mapping CSV:

- `accepted`: 9
- `alias`: 45
- `variant-compatible`: 12
- `ambiguous`: 55
- `unmatched`: 28
- `excluded`: 8

## Review Notes

- The mapping intentionally leaves many rows unresolved rather than inflating the matched sample.
- Preview, beta, reasoning-budget, and context-window variants should stay unresolved until stronger evidence exists.
- The mapping CSV is the current published source of truth used by the shared runner for ARC cross-reference runs.