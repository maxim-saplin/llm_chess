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
- `alias`: 46
- `variant-compatible`: 12
- `ambiguous`: 54
- `unmatched`: 28
- `excluded`: 8

## Review Notes

- The mapping intentionally leaves many rows unresolved rather than inflating the matched sample.
- Preview, beta, reasoning-budget, and context-window variants should stay unresolved until stronger evidence exists.
- The mapping CSV is the current published source of truth used by the shared runner for ARC cross-reference runs.

## Mapping Priority Queue (2026-05-13)

No ARC-AGI-2 mapping rows were changed for this queue. Rows below retain their current `ambiguous`, `unmatched`, or `excluded` statuses until exact model/config evidence supports a CSV change.

Rank unresolved ARC rows by ARC-AGI-2 score, cross-eval inconsistency, current frontier family, and plausible inventory matches with missing evidence:

1. GPT-5.5 frontier family: `arc_agi_2:0005:gpt_5_5_xhigh` (`score_arc_agi_2=85.0`), `arc_agi_2:0000:gpt_5_5_pro_high` (`84.6`), `arc_agi_2:0001:gpt_5_5_pro_xhigh` (`84.2`), `arc_agi_2:0004:gpt_5_5_high` (`83.3`), `arc_agi_2:0003:gpt_5_5_medium` (`70.4`), and `arc_agi_2:0002:gpt_5_5_low` (`33.3`). These remain `unmatched` because no exact GPT-5.5 LLM Chess inventory family/version exists.
2. GPT Pro, xHigh, and refinement axes: `arc_agi_2:0026:gpt_5_4_pro_xhigh` GPT-5.4 Pro (xHigh) (`83.3`, `ambiguous`), `arc_agi_2:0025:gpt_5_4_xhigh` GPT-5.4 (xHigh) (`74.0`, `unmatched`), and `arc_agi_2:0038:gpt_5_2_refine` GPT-5.2 (Refine.) (`72.9`, `ambiguous`). ECI has high-score GPT Pro rows with no bridge. Keep these unresolved until source evidence distinguishes Pro, xHigh, and benchmark-system behavior from plain/tiered GPT rows.
3. Claude 4.7 frontier family: `arc_agi_2:0009:claude_4_7_max` (`75.8`), `arc_agi_2:0008:claude_4_7_high` (`68.3`), `arc_agi_2:0007:claude_4_7_medium` (`67.5`), and `arc_agi_2:0006:claude_4_7_low` (`62.1`). These remain `unmatched` because no exact Claude 4.7 LLM Chess inventory family/version exists; ECI `eci:0003` Claude Opus 4.7 is the matching cross-eval priority.
4. Gemini Deep Think variants: `arc_agi_2:0032:gemini_3_deep_think_2_26` (`84.6`) and `arc_agi_2:0031:gemini_3_deep_think_preview_2` (`45.1`). These remain `ambiguous` because Deep Think is a separate reasoning setup from existing Gemini 3 Pro/Preview inventory rows.
5. Claude Opus 4.6 120K variants: `arc_agi_2:0036:claude_opus_4_6_120k_high` (`69.2`), `arc_agi_2:0037:claude_opus_4_6_120k_max` (`68.8`), `arc_agi_2:0035:claude_opus_4_6_120k_medium` (`66.3`), and `arc_agi_2:0034:claude_opus_4_6_120k_low` (`64.6`). These remain `ambiguous` because the 120K context/config axis is not represented exactly in LLM Chess.
6. DeepSeek-V3.2 consistency check: `arc_agi_2:0054:deepseek_v3_2` is already `alias` to `deepseek-V3.2_non-reasoning`, but ECI `eci:0024` DeepSeek-V3.2 and `eci:0028` DeepSeek-V3.2-Exp remain unmatched. Use source evidence to decide whether the ECI plain row can share this non-reasoning mapping or must stay separate.
7. Excluded high-score baselines and systems: `arc_agi_2:0154:human_panel` (`100.0`) and other human/system rows remain `excluded`. They are part of the unresolved review count, but they are not model-mapping candidates unless review finds a hidden model identity.