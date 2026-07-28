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
| arc_agi_2 | `data/cross-ref/results/arc_agi_2_summary.json` | `6bfbf64576c5` | `data/cross-ref/results/arc_agi_2_coverage.csv` |
| bullshit_bench | `data/cross-ref/results/bullshit_bench_summary.json` | `e78f95c09877` | `data/cross-ref/results/bullshit_bench_coverage.csv` |
| delegate_52 | `data/cross-ref/results/delegate_52_summary.json` | `daf993587cc2` | `data/cross-ref/results/delegate_52_coverage.csv` |
| eci | `data/cross-ref/results/eci_summary.json` | `04e17d517e0c` | `data/cross-ref/results/eci_coverage.csv` |
| vals_index | `data/cross-ref/results/vals_index_summary.json` | `ca87fd853be3` | `data/cross-ref/results/vals_index_coverage.csv` |

## Signal

| Eval | Raw Elo | Release-controlled | Top chess metric | OLS CV |
| --- | --- | --- | --- | --- |
| ARC-AGI-2 | r `0.730` (p `<0.001`), rho `0.773`, n `67` | r `0.520` (p `<0.001`), n `67` | `player_wins_percent`: r `0.511` (p `<0.001`), rho `0.674`, n `70` | R2 `0.250` vs baseline `-0.030`, rank rho `0.704`, n `68` |
| BullshitBench v2 | r `0.291` (p `0.025`), rho `0.471`, n `59` | r `0.078` (p `0.565`), n `58` | `games_interrupted_percent`: r `-0.407` (p `0.001`), rho `-0.476`, n `62` | R2 `0.046` vs baseline `-0.032`, rank rho `0.477`, n `59` |
| DELEGATE-52 | r `0.386` (p `0.172`), rho `0.538`, n `14` | r `0.285` (p `0.345`), n `14` | `completion_tokens_black_per_move`: r `-0.583` (p `0.023`), rho `-0.418`, n `15` | R2 `-0.928` vs baseline `-0.146`, rank rho `0.234`, n `15` |
| Epoch ECI | r `0.782` (p `<0.001`), rho `0.788`, n `81` | r `0.584` (p `<0.001`), n `80` | `player_wins_percent`: r `0.692` (p `<0.001`), rho `0.793`, n `97` | R2 `0.557` vs baseline `-0.034`, rank rho `0.762`, n `91` |
| Vals Index | r `0.622` (p `0.008`), rho `0.669`, n `17` | r `0.411` (p `0.114`), n `17` | `player_wins_percent`: r `0.512` (p `0.036`), rho `0.517`, n `17` | R2 `-1.200` vs baseline `-0.158`, rank rho `-0.100`, n `15` |

## Coverage

| Eval | Numeric rows | Mapped rows | Metric sample | Elo sample | Unmatched external | High-impact unresolved |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ARC-AGI-2 | 177 | 93 | 70 | 67 | 84 | 15 |
| BullshitBench v2 | 162 | 71 | 62 | 59 | 91 | 15 |
| DELEGATE-52 | 19 | 15 | 15 | 14 | 4 | 4 |
| Epoch ECI | 213 | 104 | 97 | 81 | 109 | 15 |
| Vals Index | 40 | 17 | 17 | 17 | 23 | 15 |

Primary human report: `data/cross-ref/CONSOLIDATED_REPORT.md`.
Primary machine-readable artifact: `data/cross-ref/results/cross_ref_summary.json`.
