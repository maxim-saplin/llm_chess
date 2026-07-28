# ECI Mapping Research

Mapping file: `data/cross-ref/mappings/eci.csv`

Access date: 2026-07-28.

## Run-Time Source Of Truth

- `data/cross-ref/run_cross_ref.py eci` uses `data/cross-ref/mappings/eci.csv` directly.
- The source column `llm_chess_model` is the seed input that helped create the CSV. It is not the live mapping surface once the CSV exists.
- If a future reviewed mapping differs from the seed bridge, the published summary exposes that difference in `mapping_source_of_truth.changed_source_bridge_matches` and the coverage CSV exposes the affected row.

## Input Basis

- Source snapshot: `data/cross-ref/evals/eci/epoch_eci_jul_2026.csv`
- Historical bridge seed: source column `llm_chess_model`
- LLM Chess inventory: `data/cross-ref/model-identity/llm_chess_models.csv`

## Migration Rule

- Every ECI row is migrated into the generic mapping contract.
- The source bridge value is preserved as `source_llm_chess_model`.
- Rows with a non-null historical bridge are seeded as `accepted` with `seed-medium` confidence for review in the mapping CSV.
- Rows without a historical bridge stay explicit as `unmatched` rather than being guessed.

## Why This Is Still Reviewable Work

- The local bridge column is useful historical evidence, but the run-time source of truth is the mapping CSV.
- Future changed matches should still be reviewed for parity against the legacy bridge behavior.
- Any future changed matches should be surfaced through the generic mapping contract rather than hidden in source-specific code.

## Expected Review Focus

- Rows with no bridge value.
- Rows where future reviewed mappings diverge from `source_llm_chess_model`.
- Duplicate bridge keys that collapse multiple ECI rows onto one LLM Chess player.

## Reasoning Effort

ECI publishes no reasoning-effort column: every row in the snapshot has an unstated effort. Under the rule in [../README.md](../README.md) ("Stage Ownership") that means clause 1 applies throughout — `assume-highest` — so an ECI row maps to the highest tier LLM Chess has for that model, and the row records `assume-highest` in `reasoning_rule_applied`.

The practical consequence is that ECI targets move whenever a higher LLM Chess tier appears. `GPT-5.5` and `GPT-5.4` were on `-medium` under the retired "base GPT-5.x → -medium" family convention and are now on `-high`; `Gemini 3.1 Pro` and `Gemini 3 Pro` moved to the renamed `-high` player ids; and the 2026-07 refresh moved `Claude Sonnet 4.6` from `claude-sonnet-4-6` to `claude-sonnet-4-6_thinking-high`, which the earlier pass had missed while moving the sibling `Claude Opus 4.6` row. Because the effort is assumed rather than sourced, each of these rows carries that caveat in `open_questions`, and a reader should not treat an ECI row as evidence about high-effort behaviour specifically.

Clause 1 can also invert an effort when LLM Chess has only one entry and it is the lower one. `DeepSeek-V3.2` is the current instance: the assumed-highest reading points at Epoch's reasoning run, but `deepseek-V3.2_non-reasoning` is the only V3.2 player, so the substitution is forced rather than reasoned and the conflict is recorded in that row's `open_questions`.

## Current State

- Seed mapping generated from the source bridge and written to `data/cross-ref/mappings/eci.csv`.
- The mapping CSV is the current published source of truth used by the shared runner for ECI cross-reference runs.
- Status mix over 213 rows: `accepted` 104, `unmatched` 109.

## Mapping Priority Queue (2026-07-28)

This queue is keyed by `Model` label, not by `eval_row_id`. **Do not re-key it to `eval_row_id`.** ECI row ids are bare row positions (`eci:0000`, `eci:0001`, …), so an upstream refresh repoints every entry while leaving the ids syntactically valid — a stale queue keeps resolving, just to the wrong models. All 15 entries in the 2026-05-13 edition of this queue pointed at a different model after the 2026-05 refresh, and 10 of them landed on rows that were by then `accepted`.

Ranked by ECI score among the 109 rows that are still `unmatched` after the 2026-07 refresh. Two
entries from the 2026-07-27 edition are now resolved and have been removed: `Claude Opus 4.7` is
accepted against `claude-opus-4-7_adaptive-thinking-high`, and the `DeepSeek-V3.2` consistency review
closed in favour of `deepseek-V3.2_non-reasoning` (see `../evals/eci/SOURCE.md`).

1. GPT `Pro` product axis: `GPT-5.5 Pro` (`161`), `GPT-5.4 Pro` (`158`), `GPT-5.2 Pro` (`155`), `GPT-5 Pro` (`150`), and `o3-pro` (`148`). LLM Chess has plain and tiered GPT rows but no Pro run, so this is an identity gap that the reasoning-effort rule does not reach. ARC carries the same unresolved Pro rows. Do not collapse them onto the base families.
2. Frontier models with no LLM Chess run at any version, newly added in this refresh: `Claude Fable 5` (`161`), `Claude Opus 5` (`159`), `Kimi K3` (`156`), `Grok 4.5` (`154`), `Claude Sonnet 5` (`153`), `DeepSeek-V4-Pro` (`149`), and `MiniMax-M3` (`147`). These are the highest-scoring gaps in the table and they truncate the comparison at its top end. They resolve only when LLM Chess runs the model.
3. Models absent from LLM Chess entirely, carried from the previous queue: `Muse Spark` (`154`), `Kimi K2.6` (`151`), `GLM-5.1` (`150`), `Qwen 3.6 Max (Preview)` (`150`), `Qwen 3.6 Plus` (`149`), and `Qwen 3.5 Plus (hosted 397B-A17B)` (`147`). No counterpart exists at any tier, so no substitution is possible.
4. Same-family-different-version rows, where a sibling exists but is not the same model: `Qwen3.7-Max` (`153`) against `qwen-max`, `GLM-5.2` (`151`) against `zai.glm-5`, `Kimi K2.7 Code` (`150`) against `kimi-k2.5`, `MiniMax-M2.7` (`146`) against `minimax.minimax-m2.5`, and `Qwen 3.6 35B-A3B` against `qwen3.6-27b@q4_k_s`. A different version is not a match; do not promote these onto the nearest sibling.
5. `Grok 4` (`147`). LLM Chess has `grok-4-20-*`, `grok-4-fast-*`, `grok-4-1-fast-*`, and now `grok-4.3-high`, but no plain `grok-4`; `grok-4-20-reasoning` is already assigned to Epoch's `Grok 4.20` row per the maintainer. Needs a maintainer decision on whether base Grok 4 has a counterpart, not a tier substitution.
6. Open-weight rows with family-level but not exact candidates: `DeepSeek-V3.2-Exp` (`145`), `Qwen3-235B-A22B-Thinking (Jul 2025)` (`145`), `Kimi K2 Thinking` (`146`), and the GLM-4.x rows. Use exact release/config evidence, not broad family similarity, before mapping. The inventory also carries a separate `DeepSeek-V3.2-Speciale` metadata-only row, which is a third identity and not a candidate for either V3.2 ECI row.
7. The 2026-07 backfill of pre-2024 and coder-family models (PaLM 2-L/M/S, the Qwen2.5-Coder sizes, `CodeQwen1.5-7B`, `DeepSeek-Coder-V2-Lite-Base`, `internlm-7b`/`internlm-20b`, `Yi-9B`, `chatglm2-6b`, `vicuna-13b-v1.1`, `Qwen-1_8B`, `open_llama_7b`, `RedPajama-INCITE-7B-Base`, `stablelm-tuned-alpha-7b`). All score below the mapped sample's floor and none has an LLM Chess counterpart; they are low priority. The PaLM 2 rows are the only ones with a near-candidate, `chat-bison-32k@002`, and it is unresolvable because Google never published which parameter tier that endpoint serves.