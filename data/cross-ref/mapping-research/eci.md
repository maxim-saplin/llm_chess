# ECI Mapping Research

Mapping file: `data/cross-ref/mappings/eci.csv`

Access date: 2026-04-28.

## Run-Time Source Of Truth

- `data/cross-ref/run_cross_ref.py eci` uses `data/cross-ref/mappings/eci.csv` directly.
- The source column `llm_chess_model` is the seed input that helped create the CSV. It is not the live mapping surface once the CSV exists.
- If a future reviewed mapping differs from the seed bridge, the published summary exposes that difference in `mapping_source_of_truth.changed_source_bridge_matches` and the coverage CSV exposes the affected row.

## Input Basis

- Source snapshot: `data/cross-ref/evals/eci/epoch_eci_apr_2026.csv`
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