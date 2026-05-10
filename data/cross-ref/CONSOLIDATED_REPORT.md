# Consolidated Cross-Ref Report

Status: current published cross-ref summary as of 2026-04-28.

This report summarizes the authoritative outputs in `data/cross-ref/results/`.

## Research Method

This workspace runs three different analysis surfaces per eval, not just one Elo correlation.

- `relationships.raw_elo`: Pearson, Spearman, and linear-fit relationship against LLM Chess Elo on the Elo-analysis sample.
- `relationships.release_controlled_elo`: partial correlation after removing a linear release-month effect.
- `relationships.selected_metrics`: one-metric-at-a-time associations against the external target score using the metric-analysis sample.
- `prediction`: a repeated cross-validated OLS fit using up to 4 non-Elo chess metrics, compared against a repeated mean baseline.

Candidate chess-side metrics currently investigated:

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

How to read the samples:

- Eval-row counts are raw external rows after score parsing and mapping filters.
- The metric-analysis sample is the deduped set of eval rows joined to LLM Chess metric rows from `data/elo_refined.csv`. `relationships.selected_metrics` and `prediction` use this sample.
- The Elo-analysis sample is the deduped set of eval rows joined to LLM Chess players with non-null Elo. `relationships.raw_elo` and `relationships.release_controlled_elo` use this sample.
- When a row has chess metrics but missing Elo, it stays in the metric branch and drops only from the Elo branch.

## Epoch ECI

What it measures:

- A stitched capability index assembled by Epoch across multiple benchmarks.

Run-time mapping source of truth:

- `data/cross-ref/mappings/eci.csv` is the mapping file used directly by the runner.
- That CSV was seeded from the source column `llm_chess_model`, but the source column is historical evidence, not the live run-time mapping surface.

Published funnel:

- `161` external rows have a numeric ECI score.
- `89` numeric rows have an accepted mapping into LLM Chess.
- All `89` accepted rows join to a LLM Chess metrics row.
- The metric branch keeps `81` deduped player rows for selected-metric analysis and prediction.
- The Elo branch drops `15` of those joined rows because the mapped LLM Chess player exists but has no Elo, leaving `74` Elo-joined rows.
- The Elo branch then drops `8` duplicate player rows, leaving `66` deduped Elo-analysis rows.

Core findings:

- Raw Elo relationship on the Elo-analysis sample is strong: `n = 66`, Pearson `r = 0.6968`, `R^2 = 0.4855`.
- The release-controlled Elo relationship remains clearly positive after removing release-month trend: `n = 65`, partial Pearson `r = 0.4932`.
- The broader metric-analysis sample is `81` rows, so non-Elo metrics are analyzed on a larger surface than the `66`-row Elo sample.

Strongest non-Elo metric relationships on the `81`-row metric sample:

- `player_wins_percent`: Pearson `r = 0.6368`, Spearman `r = 0.7690`, release-controlled Pearson `r = 0.4682`.
- `games_interrupted_percent`: Pearson `r = -0.5910`, Spearman `r = -0.5908`, release-controlled Pearson `r = -0.4971`.
- `average_time_per_game_seconds`: Pearson `r = 0.5894`, Spearman `r = 0.8009`, release-controlled Pearson `r = 0.3151`.
- `material_diff_player_llm_minus_opponent`: Pearson `r = 0.5692`, Spearman `r = 0.6063`, release-controlled Pearson `r = 0.3857`.
- `mistakes_per_1000moves`: Pearson `r = -0.5092`, Spearman `r = -0.3879`, release-controlled Pearson `r = -0.5380`.

Multivariable OLS regression:

- Selected OLS features: `player_wins_percent`, `games_interrupted_percent`, `average_time_per_game_seconds`, `material_diff_player_llm_minus_opponent`.
- Repeated cross-validated mean baseline is weak: `R^2 = -0.0096`, RMSE `12.3913`, MAE `10.0698`, rank-Spearman `-0.1325`.
- Repeated cross-validated OLS fit is materially better: `R^2 = 0.5037`, RMSE `8.6883`, MAE `7.0228`, rank-Spearman `0.7325`.
- In-sample OLS fit is `R^2 = 0.5488`, which is close enough to the cross-validated result to support a real signal rather than pure overfit.

Interpretation:

- ECI remains the strongest current cross-ref result in this workspace.
- The result is not only an Elo story. Win rate, interruption rate, time usage, material edge, and error rate all move in coherent directions.
- The 4-feature OLS model captures substantial structure beyond a naive baseline, so ECI is the only current eval here with a clearly useful multivariable regression fit.
- The main remaining limitation is coverage, not signal direction: `79` source rows still have no accepted bridge into the current LLM Chess inventory.

Inspect next:

- `data/cross-ref/results/eci.html`
- `data/cross-ref/results/eci_summary.json`
- `data/cross-ref/results/eci_coverage.csv`
- `data/cross-ref/evals/eci/SOURCE.md`
- `data/cross-ref/mapping-research/eci.md`

## ARC-AGI-2

What it measures:

- ARC Prize leaderboard performance on ARC-AGI-2, a reasoning-oriented benchmark.

Run-time mapping source of truth:

- `data/cross-ref/mappings/arc_agi_2.csv` is the mapping file used directly by the runner.
- That CSV is a reviewed row-level mapping from leaderboard labels into the current LLM Chess inventory.

Published funnel:

- `150` external rows have a numeric ARC-AGI-2 score.
- `64` numeric rows have an accepted mapping into LLM Chess.
- `57` accepted rows join to a LLM Chess metrics row.
- The metric branch drops `3` duplicate player rows and keeps `54` deduped player rows for selected-metric analysis and prediction.
- The Elo branch separately drops `3` joined rows because the mapped LLM Chess player has no Elo, leaving `54` Elo-joined rows.
- The Elo branch then drops `3` duplicate player rows, leaving `51` deduped Elo-analysis rows.

Core findings:

- Raw Elo relationship on the Elo-analysis sample is positive but weaker than ECI: `n = 51`, Pearson `r = 0.5231`, `R^2 = 0.2736`.
- The release-controlled Elo relationship remains positive but drops in strength: `n = 51`, partial Pearson `r = 0.3852`.
- The broader metric-analysis sample is `54` rows, so the non-Elo metric analysis is slightly less Elo-gated than the headline Elo result.

Strongest non-Elo metric relationships on the `54`-row metric sample:

- `player_wins_percent`: Pearson `r = 0.3959`, Spearman `r = 0.5939`, release-controlled Pearson `r = 0.3153`.
- `average_time_per_game_seconds`: Pearson `r = 0.3868`, Spearman `r = 0.5604`, release-controlled Pearson `r = 0.3485`.
- `player_draws_percent`: Pearson `r = -0.3232`, Spearman `r = -0.2675`, release-controlled Pearson `r = -0.2368`.
- `material_diff_player_llm_minus_opponent`: Pearson `r = 0.2873`, Spearman `r = 0.4550`, release-controlled Pearson `r = 0.2674`.
- `average_moves`: Pearson `r = -0.2422`, Spearman `r = -0.3138`, release-controlled Pearson `r = -0.1604`.

Multivariable OLS regression:

- Selected OLS features: `player_wins_percent`, `average_time_per_game_seconds`, `player_draws_percent`, `material_diff_player_llm_minus_opponent`.
- Repeated cross-validated mean baseline is poor: `R^2 = -0.0388`, RMSE `14.9541`, MAE `8.7348`, rank-Spearman `-0.1901`.
- Repeated cross-validated OLS fit improves ranking but not by much on absolute error: `R^2 = 0.0251`, RMSE `14.4868`, MAE `8.9191`, rank-Spearman `0.4498`.
- In-sample OLS fit reaches only `R^2 = 0.2505`, which is another sign that the multivariable regression signal is still weak and noisy.

Mapping status mix:

- `accepted`: `9`
- `alias`: `45`
- `variant-compatible`: `12`
- `ambiguous`: `55`
- `unmatched`: `28`
- `excluded`: `8`

Interpretation:

- ARC-AGI-2 still shows positive signal, but the mapping surface is materially noisier than ECI.
- The metric-level picture is real but shallow: win rate and time usage point in the expected direction, but the multivariable OLS regression is only marginally better than the naive baseline.
- The result is useful for directional analysis, but claims should stay conservative because many leaderboard rows encode system variants rather than one clean base-model identity.

Inspect next:

- `data/cross-ref/results/arc_agi_2.html`
- `data/cross-ref/results/arc_agi_2_summary.json`
- `data/cross-ref/results/arc_agi_2_coverage.csv`
- `data/cross-ref/evals/arc-agi-2/SOURCE.md`
- `data/cross-ref/mapping-research/arc_agi_2.md`

## Review Path

1. Open the per-eval HTML report.
2. Check the summary JSON for `mapping_source_of_truth`, `coverage`, `analysis_surfaces`, `funnel`, `relationships`, `prediction`, `sensitivity`, and `verification`.
3. Use the coverage CSV when you need to inspect a row drop, a missing-Elo case, or a dedupe loser.
4. Read the source note and mapping research note before turning the correlation into a model-capability claim.

## Bottom Line

- ECI is still the cleanest and strongest current cross-ref in this workspace, and it is the only current eval here with a clearly useful multivariable regression fit.
- ARC-AGI-2 remains directionally promising but more fragile because mapping ambiguity is higher and the multivariable OLS regression is still weak.
- `data/cross-ref/results/` is the authoritative published output surface. Everything else supports provenance, mapping review, or implementation.