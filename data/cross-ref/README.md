# Cross-Ref Research Workspace

## Purpose

This workspace tests whether frozen external benchmark scores line up with LLM Chess outcomes after conservative model identity mapping.

This README is the operating guide. It should stay stable across result refreshes: use it for layout, artifact roles, commands, and methodology. Use [CONSOLIDATED_REPORT.md](CONSOLIDATED_REPORT.md) and the per-eval result artifacts for current findings.

## Artifact Map

| Artifact | Role |
| --- | --- |
| [CONSOLIDATED_REPORT.md](CONSOLIDATED_REPORT.md) | Cross-eval findings, current caveats, and research next steps. |
| [results/eci_summary.json](results/eci_summary.json), [results/arc_agi_2_summary.json](results/arc_agi_2_summary.json) | Machine-readable per-eval facts used for reporting. |
| [results/eci.html](results/eci.html), [results/arc_agi_2.html](results/arc_agi_2.html) | Human-readable per-eval reports. |
| [results/eci_coverage.csv](results/eci_coverage.csv), [results/arc_agi_2_coverage.csv](results/arc_agi_2_coverage.csv) | Row-level coverage and inclusion surfaces. |
| [mappings/eci.csv](mappings/eci.csv), [mappings/arc_agi_2.csv](mappings/arc_agi_2.csv) | Runtime model-identity source of truth. |
| [mapping-research](mapping-research) | Evidence notes behind mapping decisions. |
| [evals/eci/SOURCE.md](evals/eci/SOURCE.md), [evals/arc-agi-2/SOURCE.md](evals/arc-agi-2/SOURCE.md) | External source provenance and score semantics. |
| [evals/eci/epoch_eci_may_2026.csv](evals/eci/epoch_eci_may_2026.csv), [evals/arc-agi-2/arc-agi-2-apr-2026.csv](evals/arc-agi-2/arc-agi-2-apr-2026.csv) | Frozen external source snapshots. |

## Methodology

### Pipeline

1. Parse each frozen external snapshot into normalized rows with one numeric target score.
2. Map external model names to canonical LLM Chess player names through the mapping CSVs.
3. Include only `accepted`, `alias`, and `variant-compatible` mappings in statistics.
4. Keep `ambiguous`, `unmatched`, and `excluded` rows visible in coverage outputs, but out of correlations.
5. Join included mappings to LLM Chess rows by canonical player name.
6. If multiple external rows map to one chess player, keep the highest external score for that player.
7. Compute non-Elo metric relationships on `metric_analysis_rows_max_dedupe`.
8. Compute Elo relationships on `elo_analysis_rows_max_dedupe`, which requires non-null external score and LLM Chess Elo.

The mapping step is intentionally conservative. A plausible name match is not enough when reasoning mode, product tier, context window, benchmark system, or preview status could change the identity of the model being evaluated.

## Statistics

- Pearson `r`: linear correlation. Larger absolute value means a straighter line.
- Spearman `rho`: rank correlation. Larger absolute value means the ordering agrees more, even if the line is not clean.
- Raw Elo correlation: `corr(external_score, llm_chess_elo)` on the Elo sample.
- Simple `R2`: Pearson `r` squared for one single metric against the external score.
- OLS CV: repeated 5-fold cross-validation over 3 seeds. Features are selected inside each training fold from predeclared non-Elo chess metrics, then scored on held-out rows.

### Release-Controlled Elo

Raw Elo correlation uses two lists: external scores and LLM Chess Elo values. Release-controlled Elo uses the same final correlation operation, but first replaces both lists with release-date residuals.

Starting from the Elo sample, keep rows with usable release-month metadata:

1. Convert each model release date to a release-month value.
2. Fit a linear model that predicts external score from release month.
3. Subtract predicted external score from actual external score. This gives one external-score residual per row.
4. Fit a separate linear model that predicts LLM Chess Elo from release month.
5. Subtract predicted Elo from actual Elo. This gives one Elo residual per row.
6. Compute Pearson correlation between the two residual lists.

In formula form:

```text
raw_elo = corr(external_score, llm_chess_elo)

external_residual = external_score - predict(external_score from release_month)
elo_residual = llm_chess_elo - predict(llm_chess_elo from release_month)

release_controlled_elo = corr(external_residual, elo_residual)
```

The release-controlled value answers a stricter question: among models with comparable release timing, do models that beat their date-based external-score expectation also beat their date-based chess-Elo expectation? It removes only the linear release-month trend, not every possible time-related confounder.

## Interpretation Boundaries

- Correlation is association, not causation.
- Raw Elo correlation can be inflated by chronology because newer models often improve across many benchmarks at once.
- Release-controlled correlation is a timing check, not a full causal adjustment.
- OLS CV is a prediction check; it can fail even when rank correlation is positive.
- Mapping uncertainty is part of the result. Do not hide unresolved rows just because they are excluded from statistics.

## Review Order

1. Read [CONSOLIDATED_REPORT.md](CONSOLIDATED_REPORT.md) for the cross-eval bottom line and current caveats.
2. Inspect [results/eci.html](results/eci.html) and [results/arc_agi_2.html](results/arc_agi_2.html) for per-eval detail.
3. Check [results/eci_summary.json](results/eci_summary.json) and [results/arc_agi_2_summary.json](results/arc_agi_2_summary.json) when a claim needs machine-readable backing.
4. Use [results/eci_coverage.csv](results/eci_coverage.csv), [results/arc_agi_2_coverage.csv](results/arc_agi_2_coverage.csv), and the mapping CSVs to review row-level inclusion decisions.
5. Use `mapping-review` or `audit` commands below for generated review surfaces that are not necessarily checked in.

## Commands

From the repository root with `.venv` active:

```bash
.venv/bin/python data/cross-ref/run_cross_ref.py eci
.venv/bin/python data/cross-ref/run_cross_ref.py arc_agi_2
.venv/bin/python data/cross-ref/run_cross_ref.py cross-eval
.venv/bin/python data/cross-ref/run_cross_ref.py mapping-review
.venv/bin/python data/cross-ref/run_cross_ref.py audit
```

Default runs write scratch review outputs. Add explicit `--summary-output`, `--report-output`, `--csv-output`, or `--html-output` paths when you need a stable temporary artifact. Use `--publish` only after reviewing outputs and intentionally updating checked-in generated artifacts.

Focused examples:

```bash
.venv/bin/python data/cross-ref/run_cross_ref.py mapping-review --status ambiguous --eval-id eci
.venv/bin/python data/cross-ref/run_cross_ref.py rerun-diff eci
.venv/bin/python data/cross-ref/run_cross_ref.py cross-eval --summary-output /tmp/cross_ref_summary.json
```

## Layout

- [evals](evals): frozen external source snapshots and provenance notes.
- [mappings](mappings): mapping CSVs read by the runner.
- [mapping-research](mapping-research): evidence notes for mapping decisions.
- [model-identity](model-identity): generated LLM Chess model inventory.
- [results](results): checked-in per-eval summaries, coverage files, and human reports.
- [adapters](adapters), [framework](framework), and [run_cross_ref.py](run_cross_ref.py): normalization, analysis, and publication code.