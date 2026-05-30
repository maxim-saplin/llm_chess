# Cross-Eval Report

Generated facts from published per-eval summaries. It does not rerun evals; regenerate with `run_cross_ref.py cross-eval --publish`.

## Method

- `raw Elo`: Pearson and Spearman correlation between external score and LLM Chess Elo on deduped mapped rows with non-null Elo.
- `release-controlled`: Pearson correlation after both external score and Elo are residualized on release month.
- `top chess metric`: strongest non-Elo LLM Chess metric by absolute Pearson correlation on the metric-analysis sample.
- `OLS CV`: repeated 5-fold CV over 3 seeds. Features are selected inside each training fold from predeclared non-Elo chess metrics.
- Deduplication keeps the highest external score per mapped LLM Chess player.

## Inputs

| Eval | Summary | SHA256 | Coverage |
| --- | --- | --- | --- |
| arc_agi_2 | `data/cross-ref/results/arc_agi_2_summary.json` | `fb0292f2e736` | `data/cross-ref/results/arc_agi_2_coverage.csv` |
| bullshit_bench | `data/cross-ref/results/bullshit_bench_summary.json` | `94771ba2e5e3` | `data/cross-ref/results/bullshit_bench_coverage.csv` |
| delegate_52 | `data/cross-ref/results/delegate_52_summary.json` | `b7fa123b7292` | `data/cross-ref/results/delegate_52_coverage.csv` |
| eci | `data/cross-ref/results/eci_summary.json` | `7c079bc1cfd1` | `data/cross-ref/results/eci_coverage.csv` |

## Signal

| Eval | Raw Elo | Release-controlled | Top chess metric | OLS CV |
| --- | --- | --- | --- | --- |
| ARC-AGI-2 | r `0.584`, rho `0.660`, n `57` | r `0.412`, n `57` | `average_game_cost`: r `0.473`, rho `0.621`, n `58` | R2 `-0.119` vs baseline `-0.028`, rank rho `0.522` |
| BullshitBench v2 | r `0.303`, rho `0.480`, n `55` | r `0.118`, n `54` | `average_game_cost`: r `0.428`, rho `0.575`, n `56` | R2 `0.090` vs baseline `-0.017`, rank rho `0.472` |
| DELEGATE-52 | r `0.381`, rho `0.538`, n `14` | r `0.283`, n `14` | `completion_tokens_black_per_move`: r `-0.630`, rho `-0.464`, n `15` | R2 `-0.682` vs baseline `-0.146`, rank rho `0.246` |
| Epoch ECI | r `0.757`, rho `0.744`, n `70` | r `0.551`, n `69` | `player_wins_percent`: r `0.689`, rho `0.791`, n `85` | R2 `0.527` vs baseline `-0.021`, rank rho `0.739` |

## Coverage

| Eval | Numeric rows | Mapped rows | Metric sample | Elo sample | Unmatched external | High-impact unresolved |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ARC-AGI-2 | 152 | 71 | 60 | 57 | 89 | 15 |
| BullshitBench v2 | 162 | 66 | 58 | 55 | 96 | 15 |
| DELEGATE-52 | 19 | 15 | 15 | 14 | 4 | 4 |
| Epoch ECI | 178 | 93 | 85 | 70 | 85 | 15 |

Primary human report: `data/cross-ref/CONSOLIDATED_REPORT.md`.
Primary machine-readable artifact: `data/cross-ref/results/cross_ref_summary.json`.
