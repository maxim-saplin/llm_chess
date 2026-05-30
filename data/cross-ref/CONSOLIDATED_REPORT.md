# Consolidated Cross-Ref Report

## Bottom Line

Epoch ECI is still the only external eval with a strong enough signal to treat as useful. ARC-AGI-2
has a moderate raw and rank relationship to LLM Chess Elo but its calibrated prediction is no better
than the mean baseline. DELEGATE-52 and BullshitBench v2 are the weakest: modest rank relationships
that mostly disappear once release timing is controlled, and neither beats the mean baseline under
cross-validated prediction.

Do not sell this as broad benchmark validation. It is now a four-eval comparison with a large pile
of unresolved identity debt, and the evals disagree about which chess behaviors track external
capability.

Figures reflect the current published snapshots against the current `elo_refined.csv`: the
2026-05-29 ECI refresh (178 models), the 2026-05 ARC-AGI-2 refresh (152 rows), the BullshitBench v2
leaderboard (162 model/reasoning rows, upstream commit `88e06ae`, 2026-05-29), and the newly added
DELEGATE-52 (19 models, transcribed from the paper's Table 1, arXiv `2604.15597v1`, 2026-04-17).

DELEGATE-52 measures long-horizon delegated document-editing fidelity (the Reconstruction Score after
each of up to 20 interactions, higher = less corruption). Because each model is a curve rather than a
single number, the analysis reports the Elo correlation at every interaction depth instead of one
chosen depth. The distinctive finding is about *degradation*, not level: the Elo correlation rises
with interaction depth (Pearson `+0.17` at RS@2 to `+0.38` at RS@20), and the degradation slope
(RS@2 − RS@20) correlates negatively with Elo (Pearson `-0.45`) — higher-Elo models corrupt
documents less over long workflows, even though their one-round-trip fidelity is only weakly tied to
chess strength.

BullshitBench measures one behavior — whether a model pushes back on a nonsense premise instead of
playing along — on a 0-2 scale where higher is better. It is a deliberately different axis from a
capability index like ECI, and the data show it: the strongest nonsense-detectors in the matched
sample are mid-Elo Claude models, while the highest-Elo OpenAI/Gemini reasoning models sit mid-pack.

## Signal Table

| Eval | Raw Elo | Release-controlled | Top chess metric | OLS CV |
| --- | --- | --- | --- | --- |
| Epoch ECI | Pearson `0.757` (p `<0.001`), Spearman `0.744`, `n=70` | Pearson `0.551` (p `<0.001`), `n=69` | `player_wins_percent`: Pearson `0.689` (p `<0.001`), Spearman `0.791`, `n=85` | `R2=0.527`; rank Spearman `0.739` |
| ARC-AGI-2 | Pearson `0.584` (p `<0.001`), Spearman `0.660`, `n=57` | Pearson `0.412` (p `0.001`), `n=57` | `average_game_cost`: Pearson `0.473` (p `<0.001`), Spearman `0.621`, `n=58` | `R2=-0.119`; rank Spearman `0.522` |
| BullshitBench v2 | Pearson `0.303` (p `0.025`), Spearman `0.480`, `n=55` | Pearson `0.118` (p `0.397`), `n=54` | `average_game_cost`: Pearson `0.428` (p `0.001`), Spearman `0.575`, `n=56` | `R2=0.090`; rank Spearman `0.472` |
| DELEGATE-52 (RS@20) | Pearson `0.381` (p `0.179`), Spearman `0.538`, `n=14` | Pearson `0.283` (p `0.327`), `n=14` | `completion_tokens_black_per_move`: Pearson `-0.630` (p `0.012`), Spearman `-0.464`, `n=15` | `R2=-0.682`; rank Spearman `0.246` |

p-values are two-sided Pearson tests on each correlation (`pearson_p` in the per-eval `*_summary.json`,
now also carried in `cross_ref_summary.json` and the HTML reports). They are descriptive, not
multiplicity-controlled: each eval tests ~11 chess metrics plus raw and release-controlled Elo, and
the "Top chess metric" column is the strongest of those metrics by construction, so its p-value is
optimistic — read it as "the leading metric clears the bar," not as a corrected significance claim.
The max-dedupe selection (highest external score per player) and small samples (DELEGATE-52 `n=14`)
also mean these p-values assume more than the design delivers. Where uncertainty matters most, the
bootstrap 95% CIs in each eval's `raw_elo` block are the more honest read.

Interpretation:

- ECI: usable relationship, and the only eval where the p-values reinforce rather than undercut the
  headline. Raw Elo is `p<0.001` at `n=70`, and — the part that matters — the relationship still
  clears `p<0.001` *after* release-month control (`r=0.551`, `n=69`). So ECI's link to chess Elo is
  not just the chronology trend that the other evals mostly reduce to; `player_wins_percent` is the
  strongest non-Elo metric and is also `p<0.001`. Fold-local OLS predicts the index well above a
  trivial baseline. This is the eval to treat as a real signal.
- ARC-AGI-2: weak relationship under prediction. Raw and rank correlation are moderate, but the
  calibrated OLS prediction is below the mean baseline (`R2=-0.119`), so treat ARC as a rank-order
  signal only.
- BullshitBench: rank ordering is positive (`Spearman 0.480`) but the linear fit is low and the
  relationship mostly collapses under release-month control (`0.303` → `0.118`), meaning most of the
  apparent association is chronology, not a model-capability link. The p-values make this concrete:
  raw Elo is only marginal (`p=0.025`) and the release-controlled correlation is indistinguishable
  from zero (`p=0.397`).
- DELEGATE-52: weak-to-moderate at the long-horizon endpoint (`Pearson 0.381`, `Spearman 0.538`,
  `n=14`), partly deflated by release-month control (`0.381` → `0.283`), and OLS prediction is below
  the mean baseline (`R2=-0.682`). Read it as a rank/degradation signal only — and note the raw
  endpoint correlation is not significant at this sample (`p=0.179`, `n=14`). The `completion_tokens_
  black_per_move` association is negative (`-0.630`, `p=0.012`): models that spend more tokens per
  chess move tend to corrupt documents more — but at `n=15` this is fragile and exploratory.
- No shared headline metric: `player_wins_percent` is the strongest non-Elo chess metric for ECI, but
  ARC and BullshitBench lead with `average_game_cost`, and DELEGATE-52 leads with
  `completion_tokens_black_per_move`. The four evals do not agree on which chess behavior tracks
  external capability.

## Method In One Screen

- Only mapped rows with status `accepted`, `alias`, or `variant-compatible` enter analysis.
- `ambiguous`, `unmatched`, and `excluded` rows stay visible in coverage and mapping review, but do
  not enter correlations.
- Multiple external rows for one LLM Chess player are deduped by keeping the highest external score.
  For BullshitBench this collapses a model's reasoning-level rows to one model-level point.
- Pearson `r` measures linear fit; Spearman `rho` measures rank-order fit.
- Each correlation carries a two-sided p-value (`pearson_p`/`spearman_p`). They are per-test and
  uncorrected for the many metrics tested, so use them to separate "clears the bar" from "no
  distinguishable signal," not as a multiplicity-controlled significance verdict.
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
| DELEGATE-52 | 19 | 15 | 15 | 14 | 2 / 2 | 4 |

The audit reports `reproducibility_status = pass` (all four per-eval artifacts reproduce cleanly,
`evals_with_diff_count = 0`), `coverage_status = review-needed`, and `unresolved_row_count = 271`
across the four external evals. The ECI, ARC-AGI-2, and BullshitBench baselines were republished
alongside this change to pick up the `elo_refined.csv` `min_game_date` column and the `mistake_stats`
summary block; that republish changed only recorded input metadata, no relationship, coverage, or
prediction value.

### DELEGATE-52 Mapping Shape

The 19 Table-1 rows resolve to 13 `variant-compatible` and 2 `alias` mappings (15 mapped rows → 15
unique LLM Chess players, 14 in the Elo sample after `claude-opus-4-6` drops for missing Elo), with 2
`unmatched` (Mistral Large 3; the original Grok 4, distinct from the `grok-4-20*` revision in
`elo_refined.csv`) and 2 `ambiguous` (an unspecified GPT-4o snapshot; `gpt-oss-120b` with an
unspecified reasoning tier). The paper does not publish exact reasoning configs (Appendix L was not
machine-extractable), so reasoning-capable base models are mapped with a config caveat following the
shared tier convention (base GPT-5.x → `-medium`, mini/nano → `-high`). See
`mapping-research/delegate_52.md`. The source is paper-transcribed, weaker provenance than the other
three evals (which snapshot machine-readable upstream files); this is documented in
`evals/delegate-52/SOURCE.md`.

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
- DELEGATE-52 summary: [results/delegate_52_summary.json](results/delegate_52_summary.json)
- ECI report: [results/eci.html](results/eci.html)
- ARC report: [results/arc_agi_2.html](results/arc_agi_2.html)
- BullshitBench report: [results/bullshit_bench.html](results/bullshit_bench.html)
- DELEGATE-52 report: [results/delegate_52.html](results/delegate_52.html)
- Coverage: [results/eci_coverage.csv](results/eci_coverage.csv), [results/arc_agi_2_coverage.csv](results/arc_agi_2_coverage.csv), [results/bullshit_bench_coverage.csv](results/bullshit_bench_coverage.csv), [results/delegate_52_coverage.csv](results/delegate_52_coverage.csv)
- Mapping sources: [mappings/eci.csv](mappings/eci.csv), [mappings/arc_agi_2.csv](mappings/arc_agi_2.csv), [mappings/bullshit_bench.csv](mappings/bullshit_bench.csv), [mappings/delegate_52.csv](mappings/delegate_52.csv)
- Mapping rationale: [mapping-research/bullshit_bench.md](mapping-research/bullshit_bench.md), [mapping-research/delegate_52.md](mapping-research/delegate_52.md)
