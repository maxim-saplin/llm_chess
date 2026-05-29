# ECI Mapping Research

Mapping file: `data/cross-ref/mappings/eci.csv`

Access date: 2026-04-28.

## Run-Time Source Of Truth

- `data/cross-ref/run_cross_ref.py eci` uses `data/cross-ref/mappings/eci.csv` directly.
- The source column `llm_chess_model` is the seed input that helped create the CSV. It is not the live mapping surface once the CSV exists.
- If a future reviewed mapping differs from the seed bridge, the published summary exposes that difference in `mapping_source_of_truth.changed_source_bridge_matches` and the coverage CSV exposes the affected row.

## Input Basis

- Source snapshot: `data/cross-ref/evals/eci/epoch_eci_may_2026.csv`
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

## Current State

- Seed mapping generated from the source bridge and written to `data/cross-ref/mappings/eci.csv`.
- The mapping CSV is the current published source of truth used by the shared runner for ECI cross-reference runs.

## Mapping Priority Queue (2026-05-13)

No ECI mapping rows were changed for this queue. Rows below retain their current `unmatched` status until exact model/config evidence supports a CSV change.

Rank unresolved ECI rows by external score, cross-eval inconsistency, current frontier family, and plausible inventory matches with missing evidence:

1. GPT Pro variants: `eci:0000` GPT-5.4 Pro (`score_numeric=158.0`), `eci:0006` GPT-5.2 Pro (`154.0`), and `eci:0011` GPT-5 Pro (`150.0`). Current inventory has plain or tiered GPT rows, but the Pro axis is not represented exactly; do not collapse these to GPT-5.4, GPT-5.2, or GPT-5 without source evidence.
2. Claude Opus 4.7: `eci:0003` Claude Opus 4.7 (`156.0`). ARC also has Claude 4.7 frontier rows marked unmatched. Keep this row unmatched until an exact LLM Chess Claude 4.7/Opus 4.7 row exists.
3. DeepSeek-V3.2 consistency review: `eci:0024` DeepSeek-V3.2 (`146.0`) and `eci:0028` DeepSeek-V3.2-Exp (`145.0`). ARC maps `arc_agi_2:0054:deepseek_v3_2` to `deepseek-V3.2_non-reasoning`, while inventory also contains a separate `DeepSeek-V3.2-Speciale` metadata-only row. Verify whether the ECI plain label is the same non-reasoning identity, an experimental variant, or a separate reasoning setup before changing status.
4. High-score open-weight/local rows with family-level but not exact candidates: `eci:0026` Qwen3-235B-A22B-Thinking (`145.0`), `eci:0027` Kimi K2 Thinking (`145.0`), `eci:0031` GLM-4.7 (`144.0`), `eci:0032` Qwen3-Max (`144.0`), `eci:0042` GLM-4.6 (`141.0`), `eci:0046` Kimi K2 (Jul 2025) (`140.0`), and `eci:0051` Qwen3-235B-A22B (`140.0`). Use exact release/config evidence, not broad family similarity, before mapping.
5. Other high-score unmatched rows: `eci:0005` Muse Spark (`155.0`) and `eci:0016` o3-pro (`148.0`). These remain no-bridge rows; prioritize them after the cross-eval/frontier groups unless new inventory evidence appears.