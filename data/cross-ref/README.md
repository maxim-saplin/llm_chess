# Cross-Ref Research Workspace

## Purpose

This workspace tests whether frozen external benchmark scores line up with LLM Chess outcomes after conservative model identity mapping.

This README is the operating guide. It should stay stable across result refreshes: use it for layout, artifact roles, commands, and methodology. Use [CONSOLIDATED_REPORT.md](CONSOLIDATED_REPORT.md) and the per-eval result artifacts for current findings.

## Artifact Map

| Artifact | Role |
| --- | --- |
| [CONSOLIDATED_REPORT.md](CONSOLIDATED_REPORT.md) | Cross-eval findings, current caveats, and research next steps. |
| [results/eci_summary.json](results/eci_summary.json), [results/arc_agi_2_summary.json](results/arc_agi_2_summary.json), [results/bullshit_bench_summary.json](results/bullshit_bench_summary.json), [results/delegate_52_summary.json](results/delegate_52_summary.json), [results/vals_index_summary.json](results/vals_index_summary.json) | Machine-readable per-eval facts used for reporting. |
| [results/eci.html](results/eci.html), [results/arc_agi_2.html](results/arc_agi_2.html), [results/bullshit_bench.html](results/bullshit_bench.html), [results/delegate_52.html](results/delegate_52.html), [results/vals_index.html](results/vals_index.html) | Human-readable per-eval reports. |
| [results/eci_coverage.csv](results/eci_coverage.csv), [results/arc_agi_2_coverage.csv](results/arc_agi_2_coverage.csv), [results/bullshit_bench_coverage.csv](results/bullshit_bench_coverage.csv), [results/delegate_52_coverage.csv](results/delegate_52_coverage.csv), [results/vals_index_coverage.csv](results/vals_index_coverage.csv) | Row-level coverage and inclusion surfaces. |
| [mappings/eci.csv](mappings/eci.csv), [mappings/arc_agi_2.csv](mappings/arc_agi_2.csv), [mappings/bullshit_bench.csv](mappings/bullshit_bench.csv), [mappings/delegate_52.csv](mappings/delegate_52.csv), [mappings/vals_index.csv](mappings/vals_index.csv) | Runtime model-identity source of truth. |
| [mapping-research](mapping-research) | Evidence notes behind mapping decisions. |
| [evals/eci/SOURCE.md](evals/eci/SOURCE.md), [evals/arc-agi-2/SOURCE.md](evals/arc-agi-2/SOURCE.md), [evals/bullshit-bench/SOURCE.md](evals/bullshit-bench/SOURCE.md), [evals/delegate-52/SOURCE.md](evals/delegate-52/SOURCE.md), [evals/vals-index/SOURCE.md](evals/vals-index/SOURCE.md) | External source provenance and score semantics. |
| [evals/eci/epoch_eci_jul_2026.csv](evals/eci/epoch_eci_jul_2026.csv), [evals/arc-agi-2/arc-agi-2-jul-2026.csv](evals/arc-agi-2/arc-agi-2-jul-2026.csv), [evals/bullshit-bench/bullshit_bench_v2_may_2026.csv](evals/bullshit-bench/bullshit_bench_v2_may_2026.csv), [evals/delegate-52/delegate-52-may-2026.csv](evals/delegate-52/delegate-52-may-2026.csv), [evals/vals-index/vals_index_v1_2_july_2026.csv](evals/vals-index/vals_index_v1_2_july_2026.csv) | Frozen external source snapshots. |

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

### Stage Ownership

Each stage below is either deterministic script logic or an agent judgment call, never both. Read the owner column before changing anything: it says whether the correct edit target is an input you author or a code path you fix.

| Stage | Owner | Where |
| --- | --- | --- |
| Author external provenance, score semantics, columns, and caveats | agent | `evals/<eval>/SOURCE.md` |
| Normalize the frozen snapshot into rows and assign `eval_row_id` | script | `adapters/*.py`, `normalize_source` |
| Parse score and cost columns into numbers | script | [framework/normalization.py](framework/normalization.py): `safe_float`, `parse_percent`, `parse_currency` |
| Decide `llm_chess_player` and `mapping_status` for each external row, applying the reasoning-effort rule below | agent | `mappings/<eval_id>.csv` |
| Record why: `rationale`, `open_questions`, `evidence_refs`, `confidence` | agent | `mappings/<eval_id>.csv`, `mapping-research/<eval_id>.md` |
| Merge the mapping onto normalized rows on `(eval_id, eval_row_id, eval_model_label, eval_variant_label)` | script | [framework/mapping.py:56](framework/mapping.py#L56) |
| Filter to `accepted`, `alias`, and `variant-compatible` rows with a non-null player | script | [framework/eval_analysis.py:83](framework/eval_analysis.py#L83) |
| Join surviving rows to `data/elo_refined.csv` by player name | script | [framework/analysis_surface.py:43](framework/analysis_surface.py#L43) |
| Keep the highest external score per player | script | [framework/analysis_surface.py:16](framework/analysis_surface.py#L16) |
| Apply data-quality masks and mistake-stats gating | script | [framework/data_quality.py:85](framework/data_quality.py#L85), [:42](framework/data_quality.py#L42) |
| Compute every correlation, residual, regression, and CV figure | script | [framework/statistics.py](framework/statistics.py) |
| Build the coverage funnel and per-row `metric_drop_reason` | script | [framework/analysis_surface.py:110](framework/analysis_surface.py#L110), [:270](framework/analysis_surface.py#L270) |
| Write artifacts, record provenance hashes, gate publication | script | [run_cross_ref.py:45](run_cross_ref.py#L45), [framework/cross_eval.py:28](framework/cross_eval.py#L28) |
| Review generated outputs and decide whether they are trustworthy | agent | reading `results/`, `audit`, `rerun-diff` |
| Write cross-eval narrative from generated facts only | agent | [CONSOLIDATED_REPORT.md](CONSOLIDATED_REPORT.md) |
| Decide when a reviewed run becomes checked-in state | agent | choosing to pass `--publish` |

Reasoning effort in the mapping stage resolves **coverage-first**, by **direction-aware nearest-tier substitution**. Never leave a row unmatched merely because the exact tier is missing; equally, never promote a stated low-effort external run to a high chess tier when a lower one exists. Three clauses, in order:

1. External effort unstated or unclear (`assume-highest`): assume the run used the highest, then map to the highest tier LLM Chess has for that model. An ECI row reading only `GPT-5.4` maps to `gpt-5.4-high`.
2. External effort stated and LLM Chess has that exact tier: use it. An exact match always wins, which is why ARC's explicit labels stay as they read — `GPT-5.5 (High)` maps to `gpt-5.5-high`.
3. External effort stated but absent from LLM Chess (`nearest-tier`): substitute the nearest available tier *in the same direction*. Stated `high`, `xhigh`, or `max` takes the highest tier available; stated `low` or `minimal` takes the lowest tier available; stated `medium` takes the nearest by distance, and the higher of the two when equidistant. Direction binds even when a higher tier exists: `openai/gpt-5.5@reasoning=low` maps to `gpt-5.5-medium`, the lowest LLM Chess offers for that model, and is never promoted to `gpt-5.5-high`.

Two consequences are worth stating outright, because both occur in current data. When a model has only one tier in LLM Chess, directional substitution has a single candidate: the bullshit-bench row `google/gemini-3-pro-preview@reasoning=low` resolves to `gemini-3-pro-preview-high`, inverting the stated effort because no lower tier exists. That outcome is forced, not reasoned. Coverage still wins, but record the conflict in `open_questions` instead of letting the mapping imply the two efforts agree. When clause 3's `medium` tiebreak fires, it is a convention rather than evidence: ARC's `GPT-5.4 Mini (Medium)` has only `-low` and `-high` to choose between, and the rule takes `-high` because a tie has to break somewhere.

A row resolved by clause 1 or clause 3 must name the applied clause — `assume-highest` or `nearest-tier` — in the mapping CSV's `reasoning_rule_applied` column, alongside the existing values `reasoning_kind_match`, `name_alias`, and `effort_to_effort`. That column is currently blank on 181 of the 249 accepted rows, which is precisely why the previous convention could not be audited after the fact.

**The load-bearing invariant: everything the agent decides lands in a mapping CSV or a `.md` file. Nothing the agent decides is ever written into [results](results).** Every file under `results/` is generated, and comes only from a `--publish` run. If a figure there looks wrong, the fix is upstream — a mapping row, an adapter, a statistic — followed by a republish.

Commit `d8f72caf` broke this and went unnoticed for five weeks. It hand-edited `llm_chess_player` labels directly inside three generated summaries — `results/eci_summary.json`, `results/arc_agi_2_summary.json`, and `results/delegate_52_summary.json` — instead of editing the mapping CSVs and republishing. Two things broke at once. The three summaries stopped agreeing with the coverage CSVs and HTML produced by the same publish: `results/eci_summary.json` says `gemini-3.1-pro-preview-high` where `results/eci_coverage.csv` and `results/eci.html` still say `gemini-3.1-pro-preview`. And their content hashes stopped matching the `summary_sha256` values recorded in `results/cross_ref_summary.json`; `bullshit_bench_summary.json`, the one per-eval summary that commit did not touch, still matches its recorded hash. A hand-edit that looks like a one-line label fix desynchronizes an entire publish.

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

1. Run `verify` first: it checks whether the checked-in artifacts in [results](results) still correspond to current inputs, and exits non-zero when they do not.
2. Read [CONSOLIDATED_REPORT.md](CONSOLIDATED_REPORT.md) for the cross-eval bottom line and current caveats.
3. Inspect [results/eci.html](results/eci.html), [results/arc_agi_2.html](results/arc_agi_2.html), [results/bullshit_bench.html](results/bullshit_bench.html), and [results/delegate_52.html](results/delegate_52.html) for per-eval detail.
4. Check [results/eci_summary.json](results/eci_summary.json), [results/arc_agi_2_summary.json](results/arc_agi_2_summary.json), [results/bullshit_bench_summary.json](results/bullshit_bench_summary.json), and [results/delegate_52_summary.json](results/delegate_52_summary.json) when a claim needs machine-readable backing.
5. Use [results/eci_coverage.csv](results/eci_coverage.csv), [results/arc_agi_2_coverage.csv](results/arc_agi_2_coverage.csv), [results/bullshit_bench_coverage.csv](results/bullshit_bench_coverage.csv), [results/delegate_52_coverage.csv](results/delegate_52_coverage.csv), and the mapping CSVs to review row-level inclusion decisions.
6. Use `mapping-review` or `audit` commands below for generated review surfaces that are not necessarily checked in.

## Commands

Run from the repository root. `.venv` is gitignored, so a fresh checkout has none; create it with `uv sync`, which provisions `.venv` from `uv.lock`.

```bash
.venv/bin/python data/cross-ref/run_cross_ref.py eci
.venv/bin/python data/cross-ref/run_cross_ref.py arc_agi_2
.venv/bin/python data/cross-ref/run_cross_ref.py bullshit_bench
.venv/bin/python data/cross-ref/run_cross_ref.py delegate_52
.venv/bin/python data/cross-ref/run_cross_ref.py cross-eval
.venv/bin/python data/cross-ref/run_cross_ref.py mapping-review
.venv/bin/python data/cross-ref/run_cross_ref.py audit
```

Default runs write scratch review outputs. Add explicit output paths when you need a stable temporary artifact. The available flags differ per subcommand:

| Subcommand | Output flags |
| --- | --- |
| `eci`, `arc_agi_2`, `bullshit_bench`, `delegate_52` | `--summary-output`, `--html-output`, `--coverage-output`, `--normalized-output` |
| `cross-eval`, `audit` | `--summary-output`, `--report-output` |
| `mapping-review` | `--csv-output`, `--html-output` |
| `rerun-diff` | `--diff-json-output`, `--diff-md-output` |
| `inventory` | `--inventory-output` |

Check `run_cross_ref.py <subcommand> --help` rather than guessing; no single subcommand accepts all four of the flags this section used to list. Use `--publish` only after reviewing outputs and intentionally updating checked-in generated artifacts.

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