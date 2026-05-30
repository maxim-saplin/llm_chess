# DELEGATE-52 Mapping Research

## Run-Time Source Of Truth

The runner reads `data/cross-ref/mappings/delegate_52.csv` directly. This note is the evidence behind
those rows; if the two disagree, the CSV is authoritative and this note must be corrected.

## Sources Used

- DELEGATE-52 paper Table 1 ("Round-trip relay results for 19 LLMs"), arXiv `2604.15597v1`
  (2026-04-17), via <https://arxiv.org/html/2604.15597v1>. Display names only; exact API
  identifiers and reasoning configs are in Appendix L, which was not machine-extractable.
- LLM Chess inventory: `data/elo_refined.csv` (player ids + Elo) and
  `data/cross-ref/model-identity/llm_chess_models.csv` / `models_metadata.csv`.

## Decision Rules Applied

- **Reasoning config is unspecified by the paper.** Where a clear same-family counterpart exists, map
  it `variant-compatible` and record the config caveat rather than inventing an effort level.
- **Tier convention** (shared with ECI/BullshitBench): base GPT-5.x → `-medium`; `mini`/`nano` →
  `-high`; `o1`/`o3` base → `-medium` representative tier.
- **Aliases** (`name_alias`): non-reasoning models whose display name maps to exactly one elo id with
  no tier ambiguity → `gpt-4.1`, `gpt-5-chat`.
- **Hold uncertain identities.** Unspecified snapshot/tier or absent family stays `ambiguous` or
  `unmatched`; these stay visible in coverage but out of the correlation samples.

## High-Impact Outcomes

- **Matched (15):** Gemini 3.1 Pro, Gemini 3 Flash, GPT 5.4/5.2/5.1/5, GPT 5 Chat, GPT 5 Mini,
  GPT 5 Nano, GPT 4.1, o1, o3, Kimi K2.5, Claude 4.6 Opus, Claude 4.6 Sonnet.
- **Unmatched (2):** Mistral Large 3 (no Mistral Large family in elo); Grok 4 (the original Grok 4
  release; elo has the distinct `grok-4-20*` revision and `grok-4-fast*`, not the same model).
- **Ambiguous (2):** GPT 4o (snapshot date unspecified; elo has 2024-05-13/-08-06/-11-20);
  OSS 120B / `gpt-oss-120b` (reasoning tier unspecified, and the high/medium/low tiers differ enough
  to change rank materially).
- **Elo-sample note:** `claude-opus-4-6` has no Elo in `elo_refined.csv`, so it contributes to the
  metric sample but is dropped from the Elo correlation sample. Expected Elo sample ≈ 14 models.

## Current Status Mix

15 variant-compatible/alias, 2 unmatched, 2 ambiguous (19 rows total). Confidence is `medium` for the
config-unspecified matches, `high` for the two non-reasoning aliases, `low`/`none` for held rows.

## Review Notes

- Reasoning config is the dominant uncertainty; if Appendix L is later extracted, revisit the
  GPT-5.x / o-series effort levels and the Claude 4.6 thinking-on/off question, and reconsider whether
  OSS 120B can be resolved to a specific `gpt-oss-120b` tier.
- Grok 4 should remain unmatched unless the paper's exact Grok identifier is confirmed to match an
  elo release.
