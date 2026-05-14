# Cross-Ref Research Workspace

## Essence

This workspace tests whether external benchmark scores line up with LLM Chess results after conservative model mapping.

Current answer: Epoch ECI has a real positive relationship with LLM Chess Elo. ARC-AGI-2 is positive but weaker, noisier, and more blocked by model-identity ambiguity.

## Methodology

| Step | Rule | Why it matters |
| --- | --- | --- |
| Source parse | Keep external snapshots in `evals/`; parse the target score to a numeric column. | The benchmark score must be traceable to a frozen source file. |
| Model mapping | Only `accepted`, `alias`, and `variant-compatible` rows enter analysis. `ambiguous`, `unmatched`, and `excluded` rows stay visible but out of correlations. | Weak identity guesses would move the numbers more than the math does. |
| Join to chess | Mapped rows join to LLM Chess rows by canonical player name. | The row must exist in the current chess dataset. |
| Deduplication | If several eval rows map to one chess player, keep the highest external score for that player. | One chess player should not get multiple votes in a correlation. |
| Metric sample | Non-Elo chess metrics use `metric_analysis_rows_max_dedupe`. | These rows have chess metrics even when Elo is missing. |
| Elo sample | Elo relationships use `elo_analysis_rows_max_dedupe`. | These rows have both an external score and non-null LLM Chess Elo. |

## Statistics

- Pearson `r`: linear correlation. Larger absolute value means a straighter line.
- Spearman `rho`: rank correlation. Larger absolute value means the ordering agrees more, even if the line is not clean.
- Simple `R2`: Pearson `r` squared for one metric against the external score.
- Release-controlled Elo: Pearson correlation after both external score and LLM Chess Elo are residualized on release month.
- OLS CV: repeated 5-fold cross-validation over 3 seeds. Features are selected inside each training fold from predeclared non-Elo chess metrics, then scored on held-out rows.

## Current Signal

| Eval | Raw Elo | Release-controlled | Top chess metric | OLS CV |
| --- | --- | --- | --- | --- |
| Epoch ECI | Pearson `0.697`, Spearman `0.698`, `n=66` | Pearson `0.493`, `n=65` | `player_wins_percent`: Pearson `0.637`, Spearman `0.769`, `n=81` | `R2=0.381` vs mean baseline `-0.043`; rank Spearman `0.683` |
| ARC-AGI-2 | Pearson `0.527`, Spearman `0.630`, `n=52` | Pearson `0.384`, `n=52` | `player_wins_percent`: Pearson `0.401`, Spearman `0.607`, `n=55` | `R2=-0.041` vs mean baseline `-0.044`; rank Spearman `0.485` |

Interpretation: ECI carries usable signal. ARC carries some rank-order signal, but its calibrated prediction result is basically baseline-level.

## Trust Status

- Published artifacts currently reproduce: audit `reproducibility_status = pass`.
- Coverage is not clean: audit `coverage_status = review-needed` because `169` mapping rows still need review.
- Do not turn the correlations into capability claims until the high-impact mapping queue shrinks.

## Review Order

1. [CONSOLIDATED_REPORT.md](CONSOLIDATED_REPORT.md): current findings and next actions.
2. [results/cross_ref_summary.json](results/cross_ref_summary.json): machine-readable aggregate facts.
3. [results/mapping_review.csv](results/mapping_review.csv): row-level mapping debt.
4. [mappings/eci.csv](mappings/eci.csv) and [mappings/arc_agi_2.csv](mappings/arc_agi_2.csv): identity source of truth used by the runner.

## Commands

From the repository root with `.venv` active:

```bash
.venv/bin/python data/cross-ref/run_cross_ref.py audit
```

The default run writes temporary review outputs. Use `--publish` only after reviewing the output and intentionally updating checked-in artifacts.

Detailed agent-only command and artifact contracts live in the cross-ref skill references: [commands](../../.agents/skills/cross-ref-research/references/commands.md), [artifacts](../../.agents/skills/cross-ref-research/references/artifacts.md), [methodology](../../.agents/skills/cross-ref-research/references/methodology.md), and [mapping rules](../../.agents/skills/cross-ref-research/references/mapping-rules.md).

## Layout

- `evals/`: frozen external source snapshots and provenance notes.
- `mappings/`: mapping CSVs read by the runner.
- `mapping-research/`: evidence notes for mapping decisions.
- `model-identity/`: generated LLM Chess model inventory.
- `results/`: generated summaries, coverage, audit, and review surfaces.
- `adapters/`, `framework/`, `run_cross_ref.py`: normalization, analysis, and publication code.