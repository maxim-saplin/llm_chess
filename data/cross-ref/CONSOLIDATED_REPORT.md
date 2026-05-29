# Consolidated Cross-Ref Report

## Bottom Line

Epoch ECI is the only supported external eval with a strong enough signal to treat as useful right now. ARC-AGI-2 has a positive Elo/rank relationship, but the prediction fit is baseline-level and the mapping ambiguity is much worse.

Do not sell this as broad benchmark validation. It is a two-eval comparison with unresolved identity debt.

Figures reflect the 2026-05-29 ECI refresh (overall Epoch index, 178 models) against the current `elo_refined.csv`. The ECI signal strengthened versus the prior snapshot, mainly from reconciling the mapping (e.g. `GPT-5.4` now `gpt-5.4-medium`) and adding four newly matched GPT-5.x models.

## Signal Table

| Eval | Raw Elo | Release-controlled | Top chess metric | OLS CV |
| --- | --- | --- | --- | --- |
| Epoch ECI | Pearson `0.757`, Spearman `0.744`, `n=70` | Pearson `0.551`, `n=69` | `player_wins_percent`: Pearson `0.689`, Spearman `0.791`, `n=85` | `R2=0.527` vs mean baseline `-0.021`; rank Spearman `0.739` |
| ARC-AGI-2 | Pearson `0.520`, Spearman `0.637`, `n=54` | Pearson `0.348`, `n=54` | `player_wins_percent`: Pearson `0.360`, Spearman `0.583`, `n=57` | `R2=-0.016` vs mean baseline `-0.042`; rank Spearman `0.494` |

Interpretation:

- ECI: usable relationship. The signal survives release-month control, and fold-local OLS beats the mean baseline.
- ARC-AGI-2: weak relationship. Rank ordering is not empty, but calibrated prediction does not beat baseline in a meaningful way.
- Shared signal: `player_wins_percent` is the strongest non-Elo chess metric for both evals.

## Method In One Screen

- Only mapped rows with status `accepted`, `alias`, or `variant-compatible` enter analysis.
- `ambiguous`, `unmatched`, and `excluded` rows stay visible in coverage and mapping review, but do not enter correlations.
- Multiple external rows for one LLM Chess player are deduped by keeping the highest external score.
- Pearson `r` measures linear fit; Spearman `rho` measures rank-order fit.
- Raw Elo correlates external score directly with LLM Chess Elo.
- Release-controlled Elo first predicts each side from release month, subtracts predicted from actual on both sides, then correlates the two residual lists.
- OLS CV uses repeated 5-fold cross-validation over 3 seeds. Feature selection happens inside each training fold, not on the full target sample.

## Coverage Debt

| Eval | Numeric rows | Accepted mappings | Metric sample | Elo sample | Unmatched external rows | High-impact unresolved |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Epoch ECI | 178 | 93 | 85 | 70 | 85 | 15 |
| ARC-AGI-2 | 150 | 65 | 57 | 54 | 90 | 15 |

The audit currently reports `reproducibility_status = pass`, `coverage_status = review-needed`, and `unresolved_row_count = 175`.

## What Raises Signal

1. Resolve high-impact mapping rows first: frontier GPT, Claude, Gemini Deep Think, DeepSeek, Qwen, Kimi, and GLM rows near the top of each leaderboard.
2. Keep plain-model rows separate from reasoning effort, product tier, context-window, benchmark-system, and preview variants unless source evidence proves equivalence.
3. Add more external evals only after their source score semantics and model identities are clear enough to avoid another ambiguity pile.
4. Treat OLS prediction as secondary. The primary signal is still raw and release-controlled Elo correlation plus row-level mapping quality.

## Evidence Pointers

- Methodology and workspace guide: [README.md](README.md)
- ECI summary: [results/eci_summary.json](results/eci_summary.json)
- ARC summary: [results/arc_agi_2_summary.json](results/arc_agi_2_summary.json)
- ECI report: [results/eci.html](results/eci.html)
- ARC report: [results/arc_agi_2.html](results/arc_agi_2.html)
- ECI coverage: [results/eci_coverage.csv](results/eci_coverage.csv)
- ARC coverage: [results/arc_agi_2_coverage.csv](results/arc_agi_2_coverage.csv)
- Mapping sources: [mappings/eci.csv](mappings/eci.csv), [mappings/arc_agi_2.csv](mappings/arc_agi_2.csv)