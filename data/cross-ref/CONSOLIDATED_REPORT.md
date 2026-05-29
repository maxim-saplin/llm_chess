# Consolidated Cross-Ref Report

## Bottom Line

Epoch ECI is still the only external eval with a strong enough signal to treat as useful. ARC-AGI-2
has a moderate raw and rank relationship to LLM Chess Elo but its calibrated prediction is no better
than the mean baseline. BullshitBench v2 is the weakest of the three: a modest rank relationship
that mostly disappears once release timing is controlled.

Do not sell this as broad benchmark validation. It is now a three-eval comparison with a large pile
of unresolved identity debt, and the three evals disagree about which chess behaviors track external
capability.

Figures reflect the current published snapshots against the current `elo_refined.csv`: the
2026-05-29 ECI refresh (178 models), the 2026-05 ARC-AGI-2 refresh (152 rows), and the newly added
BullshitBench v2 leaderboard (162 model/reasoning rows, upstream commit `88e06ae`, 2026-05-29).

BullshitBench measures one behavior — whether a model pushes back on a nonsense premise instead of
playing along — on a 0-2 scale where higher is better. It is a deliberately different axis from a
capability index like ECI, and the data show it: the strongest nonsense-detectors in the matched
sample are mid-Elo Claude models, while the highest-Elo OpenAI/Gemini reasoning models sit mid-pack.

## Signal Table

| Eval | Raw Elo | Release-controlled | Top chess metric | OLS CV |
| --- | --- | --- | --- | --- |
| Epoch ECI | Pearson `0.757`, Spearman `0.744`, `n=70` | Pearson `0.551`, `n=69` | `player_wins_percent`: Pearson `0.689`, Spearman `0.791`, `n=85` | `R2=0.527`; rank Spearman `0.739` |
| ARC-AGI-2 | Pearson `0.584`, Spearman `0.660`, `n=57` | Pearson `0.412`, `n=57` | `average_game_cost`: Pearson `0.473`, Spearman `0.621`, `n=58` | `R2=-0.119`; rank Spearman `0.522` |
| BullshitBench v2 | Pearson `0.303`, Spearman `0.480`, `n=55` | Pearson `0.118`, `n=54` | `average_game_cost`: Pearson `0.428`, Spearman `0.575`, `n=56` | `R2=0.090`; rank Spearman `0.472` |

Interpretation:

- ECI: usable relationship. The signal survives release-month control, and fold-local OLS predicts
  the index well above a trivial baseline.
- ARC-AGI-2: weak relationship under prediction. Raw and rank correlation are moderate, but the
  calibrated OLS prediction is below the mean baseline (`R2=-0.119`), so treat ARC as a rank-order
  signal only.
- BullshitBench: weakest of the three. Rank ordering is positive (`Spearman 0.480`) but the linear
  fit is low and the relationship mostly collapses under release-month control (`0.303` → `0.118`),
  meaning most of the apparent association is chronology, not a model-capability link.
- No shared headline metric anymore: `player_wins_percent` is the strongest non-Elo chess metric for
  ECI, but for ARC and BullshitBench `average_game_cost` leads instead. For BullshitBench in
  particular, `player_wins_percent` is essentially flat (Pearson `0.060`), so chess win rate does
  not predict nonsense detection at all.

## Method In One Screen

- Only mapped rows with status `accepted`, `alias`, or `variant-compatible` enter analysis.
- `ambiguous`, `unmatched`, and `excluded` rows stay visible in coverage and mapping review, but do
  not enter correlations.
- Multiple external rows for one LLM Chess player are deduped by keeping the highest external score.
  For BullshitBench this collapses a model's reasoning-level rows to one model-level point.
- Pearson `r` measures linear fit; Spearman `rho` measures rank-order fit.
- Raw Elo correlates external score directly with LLM Chess Elo.
- Release-controlled Elo first predicts each side from release month, subtracts predicted from
  actual on both sides, then correlates the two residual lists.
- OLS CV uses repeated 5-fold cross-validation over 3 seeds.
  Feature selection happens inside each training fold, not on the full target sample.

## Coverage Debt

| Eval | Numeric rows | Accepted mappings | Metric sample | Elo sample | Unmatched/ambiguous rows | High-impact unresolved |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Epoch ECI | 178 | 93 | 85 | 70 | 85 / 0 | 15 |
| ARC-AGI-2 | 152 | 71 | 60 | 57 | 24 / 54 | 15 |
| BullshitBench v2 | 162 | 66 | 58 | 55 | 90 / 6 | 15 |

The audit currently reports `reproducibility_status = pass`, `coverage_status = review-needed`, and
`unresolved_row_count = 267` across the three external evals. All published per-eval artifacts
reproduce cleanly (`evals_with_diff_count = 0`).

### BullshitBench Mapping Shape

The 162 leaderboard rows resolve to 6 `accepted`, 21 `alias`, and 39 `variant-compatible` mappings
(66 mapped rows → 58 unique LLM Chess players, 55 in the Elo sample after dedupe), with 90
`unmatched` and 6 `ambiguous`. Most unmatched rows are models with no LLM Chess counterpart (hosted
Qwen 3.5/3.6/3.7, GLM-5-turbo/5.1/4.5, DeepSeek V4, Gemma 4, Nemotron Super/Nano-9B, MiMo, StepFun,
Seed, ERNIE, Jamba, Prime Intellect, Arcee, GPT-5.5 Pro, and the `openrouter/*-alpha` stealth rows)
or non-reasoning `none` rows for OpenAI families that exist in `elo_refined.csv` only at reasoning
tiers. See `mapping-research/bullshit_bench.md` for the full effort-to-effort rule and the held-out
`ambiguous` cases (grok-4.20-beta, an unspecified Claude 3.7 thinking budget, and two hosted-vs-quant
local runs).

## Exploratory: discipline beats strength (BullshitBench)

This is a research lead, outside the governed numbers. Running BullshitBench in clean mode
(`run_cross_ref.py bullshit_bench --mistake-stats clean_only` — drops every model whose earliest
LLM Chess game predates the 2025-03-16 logging fix, leaving n=51 metric / 49 Elo) lets us use the
normally-excluded error metrics. Rank correlation vs `avg_score`:

| Chess metric | Spearman |
| --- | ---: |
| `wrong_actions_per_1000moves` | -0.58 |
| `mistakes_per_1000moves` | -0.56 |
| `games_interrupted_percent` | -0.42 |
| LLM Chess Elo | +0.40 |
| `player_wins_percent` | +0.03 |

Sloppy chess (illegal actions, blunders, interrupted games) tracks *failing* BullshitBench better
than raw strength does, and win rate is noise. It's a non-linear rank association only: a
multi-factor OLS still doesn't beat the mean baseline (CV `R2=-0.13`). So nonsense detection looks
like a carefulness/discipline trait, not a capability one — a lead, not a validated result.

## What Raises Signal

1. Resolve high-impact mapping rows first: frontier GPT, Claude, Gemini, Grok, DeepSeek, Qwen, Kimi,
   and GLM rows near the top of each leaderboard.
2. Keep plain-model rows separate from reasoning effort, product tier, context-window,
   benchmark-system, and preview variants unless source evidence proves equivalence.
3. Treat BullshitBench as a behavioral contrast eval, not a capability eval. Its value is showing
   where chess strength and epistemic pushback diverge, not validating Elo.
4. Add more external evals only after their source score semantics and model identities are clear
   enough to avoid another ambiguity pile.
5. Treat OLS prediction as secondary. The primary signal is still raw and release-controlled Elo
   correlation plus row-level mapping quality.

## Evidence Pointers

- Methodology and workspace guide: [README.md](README.md)
- ECI summary: [results/eci_summary.json](results/eci_summary.json)
- ARC summary: [results/arc_agi_2_summary.json](results/arc_agi_2_summary.json)
- BullshitBench summary: [results/bullshit_bench_summary.json](results/bullshit_bench_summary.json)
- ECI report: [results/eci.html](results/eci.html)
- ARC report: [results/arc_agi_2.html](results/arc_agi_2.html)
- BullshitBench report: [results/bullshit_bench.html](results/bullshit_bench.html)
- Coverage: [results/eci_coverage.csv](results/eci_coverage.csv), [results/arc_agi_2_coverage.csv](results/arc_agi_2_coverage.csv), [results/bullshit_bench_coverage.csv](results/bullshit_bench_coverage.csv)
- Mapping sources: [mappings/eci.csv](mappings/eci.csv), [mappings/arc_agi_2.csv](mappings/arc_agi_2.csv), [mappings/bullshit_bench.csv](mappings/bullshit_bench.csv)
- Mapping rationale: [mapping-research/bullshit_bench.md](mapping-research/bullshit_bench.md)
