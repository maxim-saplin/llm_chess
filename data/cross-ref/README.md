# Cross-Ref Workspace

This workspace cross-references LLM Chess model performance against external evaluation leaderboards.

Supported evals:

- `eci` for Epoch ECI
- `arc_agi_2` for ARC-AGI-2

`data/cross-ref/results/` is the only authoritative home for published cross-ref outputs.

## Layout

```text
data/cross-ref/
  README.md
  CONSOLIDATED_REPORT.md
  run_cross_ref.py
  adapters/
  framework/
  evals/
    eci/
    arc-agi-2/
  mapping-research/
  mappings/
  model-identity/
  results/
```

What each area is for:

- `evals/`: raw eval-specific source files and source notes only
- `adapters/`: eval-specific normalization and summary assembly
- `framework/`: shared loading, mapping, rendering, serialization, and statistics helpers
- `mapping-research/`: notes explaining how each mapping CSV was built and what it means
- `mappings/`: row-level eval-to-LLM-Chess mapping CSVs used directly at run time
- `model-identity/`: canonical LLM Chess inventory used as the mapping target surface
- `results/`: published summaries, HTML reports, normalized CSVs, and coverage CSVs

## Run-Time Source Of Truth

Every published run uses the mapping CSV in `data/cross-ref/mappings/` directly.

- ECI: `data/cross-ref/mappings/eci.csv` is the run-time source of truth. It was seeded from the source column `llm_chess_model`, but the source column is not the live mapping surface once the CSV exists.
- ARC-AGI-2: `data/cross-ref/mappings/arc_agi_2.csv` is the run-time source of truth. It is a reviewed row-level mapping from ARC leaderboard labels into the current LLM Chess inventory.
- `SOURCE.md` files explain provenance. `mapping-research/*.md` files explain how the mapping CSV was created. Neither replaces the mapping CSV that the runner actually uses.

## Funnel Definitions

Each published summary now exposes the same funnel with plain-English stage names.

Base stages:

1. numeric external eval rows
2. numeric eval rows with an accepted mapping
3. accepted eval rows joined to a LLM Chess metrics row from `data/elo_refined.csv`

Metric branch:

4. deduped metric-analysis rows

Elo branch:

5. accepted eval rows joined to LLM Chess rows with non-null Elo
6. deduped Elo-analysis rows

Which published sections use which sample:

- `relationships.selected_metrics` and `prediction` use the metric-analysis sample
- `relationships.raw_elo` and `relationships.release_controlled_elo` use the Elo-analysis sample

This matters because rows can have valid non-Elo chess metrics even when Elo is missing. Those rows stay in the metric branch and drop only from the Elo branch.

## Core Research Questions

This workspace is not only asking whether an external eval lines up with Elo.

The published analyses ask four separate questions:

1. Does the external eval score track LLM Chess Elo at all?
2. Does that relationship still hold after controlling for release month?
3. Which non-Elo LLM Chess metrics move with the external eval score?
4. Can a small multivariable OLS regression model fit the external eval score from LLM Chess metrics better than a naive mean baseline?

## Metrics Investigated

The candidate chess-side metrics currently tested in `relationships.selected_metrics` come from `data/elo_refined.csv`:

- `elo`
- `player_wins_percent`
- `player_draws_percent`
- `games_interrupted_percent`
- `wrong_moves_per_1000moves`
- `mistakes_per_1000moves`
- `average_moves`
- `average_time_per_game_seconds`
- `average_game_cost`
- `completion_tokens_black_per_move`
- `material_diff_player_llm_minus_opponent`

These are not all used in the same way.

- `relationships.raw_elo` is the dedicated Elo relationship analysis on the Elo-analysis sample.
- `relationships.release_controlled_elo` reruns the Elo relationship after removing a linear release-month effect.
- `relationships.selected_metrics` runs one-metric-at-a-time associations on the metric-analysis sample and reports Pearson correlation, Spearman correlation, linear slope/intercept, `R^2`, and a partial release-month correlation where the sample supports it.

## Multivariable OLS Regression And Prediction

The `prediction` block summarizes the multivariable OLS regression analysis.

Current method:

- Elo is excluded from the feature set so the multivariable regression answers a non-Elo question.
- Up to 4 features are chosen by absolute Pearson correlation with the target score.
- A repeated 5-fold cross-validated OLS model is fit using seeds `11`, `23`, and `37`.
- The OLS model is compared with a repeated mean-prediction baseline on the same folds.
- Published metrics include cross-validated `R^2`, RMSE, MAE, rank-Spearman, in-sample fit, and the largest prediction misses.

This means the report can distinguish between three different kinds of evidence:

- simple Elo alignment
- one-metric-at-a-time chess-signal associations
- multivariable regression fit quality

## Current Published Findings

The current published summaries already show that the research is broader than a single Elo number.

- ECI: strongest non-Elo associations are `player_wins_percent`, `games_interrupted_percent`, `average_time_per_game_seconds`, `material_diff_player_llm_minus_opponent`, and `mistakes_per_1000moves`; the 4-feature OLS regression materially beats the mean baseline.
- ARC-AGI-2: strongest non-Elo associations are `player_wins_percent`, `average_time_per_game_seconds`, `player_draws_percent`, `material_diff_player_llm_minus_opponent`, and `average_moves`; the 4-feature OLS regression is much weaker than ECI and should be treated as exploratory.

## Coverage CSV Truth Surface

The per-eval coverage CSV is the row-by-row truth surface.

For every eval row it now records:

- whether the row had a numeric score
- whether it made accepted mapping
- whether it joined a LLM Chess metrics row
- whether it survived metric dedupe
- whether it joined a non-null Elo row
- whether it survived Elo dedupe
- the metric-branch drop stage and reason, if any
- the Elo-branch drop stage and reason, if any
- the first failed stage overall
- which kept row won the dedupe conflict, when a row loses dedupe

Use the coverage CSV when you want to answer questions like “why did this row disappear?” or “which duplicate row won?”

## Operate

Run commands from the repository root.

Refresh the model inventory:

```bash
.venv/bin/python data/cross-ref/run_cross_ref.py inventory
```

Run the focused cross-ref regression tests:

```bash
.venv/bin/python -m pytest tests/test_cross_ref.py
```

Publish shared analyses:

```bash
.venv/bin/python data/cross-ref/run_cross_ref.py eci
.venv/bin/python data/cross-ref/run_cross_ref.py arc_agi_2
```

The shared runner writes the published artifacts into `data/cross-ref/results/`.

## Review Results

Use this order when reviewing research results:

1. Start with `data/cross-ref/CONSOLIDATED_REPORT.md` for the short cross-eval read.
2. Open the per-eval HTML reports in `data/cross-ref/results/`.
3. Inspect the machine-readable summaries in `data/cross-ref/results/*_summary.json`.
4. Use the coverage CSVs for row-level drop reasons and dedupe outcomes.
5. Read the source notes in `data/cross-ref/evals/*/SOURCE.md`.
6. Read the mapping research notes in `data/cross-ref/mapping-research/*.md`.

If you are checking trustworthiness rather than just headline numbers, focus on these summary sections:

- `mapping_source_of_truth`
- `coverage`
- `analysis_surfaces`
- `funnel`
- `relationships`
- `prediction`
- `verification`

For method details, the most important summary sections are:

- `relationships.raw_elo`
- `relationships.release_controlled_elo`
- `relationships.selected_metrics`
- `prediction`
- `sensitivity`

## Maintain

When maintaining or extending this workspace:

1. Keep eval-specific source files under `data/cross-ref/evals/<eval-folder>/`.
2. Keep authoritative published outputs under `data/cross-ref/results/`.
3. Preserve `SOURCE.md` for each eval with provenance, score meaning, and caveats.
4. Update or add the adapter in `data/cross-ref/adapters/`.
5. Keep mapping decisions explicit in `data/cross-ref/mappings/` and documented in `data/cross-ref/mapping-research/`.
6. Regenerate published results after code or path changes.
7. Update `CONSOLIDATED_REPORT.md` from the final published summaries, not from draft numbers.

## Safe Update Flow

1. Run `tests/test_cross_ref.py`.
2. Run shared analyses against temporary output paths if you want a non-mutating dry run.
3. Publish final `eci` and `arc_agi_2` artifacts through `run_cross_ref.py` with verification-bearing CLI flags when you are ready to update `results/`.
4. Search for stale path references before and after final publication.
5. Update `CONSOLIDATED_REPORT.md` from the final published summaries.

## Related Files

- `.agents/skills/cross-ref-research/SKILL.md`