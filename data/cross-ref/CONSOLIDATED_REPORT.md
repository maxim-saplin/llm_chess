# Consolidated Cross-Ref Report

## Bottom Line

**Two evals now clear every axis at a usable sample size, not one.** Epoch ECI remains the
strongest: raw Elo `r=0.782` (`n=81`), still `p<0.001` after release-month control (`r=0.584`), and a
cross-validated prediction well above the mean baseline (`R2=0.557`). The 2026-07-28 ECI refresh
strengthened it on every axis while growing the sample by ten rows (`r=0.766`→`0.782`, `n=71`→`81`);
the conclusion is the same one, on more evidence. ARC-AGI-2 joined it in the 2026-07-28 ARC refresh:
raw Elo `r=0.730` (`n=67`), release-controlled `r=0.520` (`p<0.001`), and `R2=+0.250` against a
`-0.030` baseline — the second-largest prediction margin in the set. Both refreshes moved through
coverage, not through a changed relationship; the isolation checks are in the per-eval notes below.
Read the pair as agreement between two capability-index-style evals, not as independent confirmation:
they overlap heavily in models and both correlate with release date. The newly added Vals Index looks
strong on raw and rank correlation (`r=0.622`, `rho=0.669`) but at `n=17` with a bootstrap 95%
interval of `0.26–0.87`, and its prediction is far below baseline. BullshitBench v2 is weak and
almost entirely chronological: `r=0.291` raw collapses to `r=0.078` (`p=0.565`) once release month is
controlled. DELEGATE-52 stays the least conclusive: `r=0.386` at `n=14`, not significant, prediction
far below baseline.

Do not sell this as broad benchmark validation. It is a five-eval comparison over **316 unresolved
mapping rows**, two of the five samples are `n<20`, and the evals still disagree about which chess
behavior tracks external capability.

Figures reflect the current published snapshots against the current `elo_refined.csv`, regenerated
by the 2026-07-28 republish: the 2026-07-28 ECI refresh (213 rows), the 2026-07-28 ARC-AGI-2 refresh
(187 rows, 177 with a numeric score), the BullshitBench v2 leaderboard (162 model/reasoning rows,
upstream commit `88e06ae`, 2026-05-29), DELEGATE-52 (19 models, transcribed from the paper's Table 1,
arXiv `2604.15597v1`, 2026-04-17), and Vals Index v1.2 (40 rows, `metadata.updated` 2026-07-23).
`run_cross_ref.py verify` passes all four checks against this state.

DELEGATE-52 measures long-horizon delegated document-editing fidelity (the Reconstruction Score after
each of up to 20 interactions, higher = less corruption). Because each model is a curve rather than a
single number, the analysis reports the Elo correlation at every interaction depth instead of one
chosen depth. The shape of the previously reported finding survives: the Elo correlation rises with
interaction depth (Pearson `+0.169` at RS@2 to `+0.386` at RS@20), and the degradation slope
(RS@2 − RS@20) correlates negatively with Elo (Pearson `-0.455`). But none of those values is
significant at `n=14` — the degradation correlation is `p=0.102` — so read it as a shape, not a
result.

BullshitBench measures one behavior — whether a model pushes back on a nonsense premise instead of
playing along — on a 0-2 scale where higher is better. It is a deliberately different axis from a
capability index like ECI, and the data show it: the release-controlled correlation is
indistinguishable from zero, and the strongest chess associate is not a strength metric at all
(see the exploratory section below).

## Signal Table

| Eval | Raw Elo | Release-controlled | Top chess metric | OLS CV |
| --- | --- | --- | --- | --- |
| Epoch ECI | Pearson `0.782` (p `<0.001`), Spearman `0.788`, `n=81` | Pearson `0.584` (p `<0.001`), `n=80` | `player_wins_percent`: Pearson `0.692` (p `<0.001`), Spearman `0.793`, `n=97` | `R2=0.557` vs baseline `-0.034`; rank Spearman `0.762`; `n=91` |
| ARC-AGI-2 | Pearson `0.730` (p `<0.001`), Spearman `0.773`, `n=67` | Pearson `0.520` (p `<0.001`), `n=67` | `player_wins_percent`: Pearson `0.511` (p `<0.001`), Spearman `0.674`, `n=70` | `R2=0.250` vs baseline `-0.030`; rank Spearman `0.704`; `n=68` |
| Vals Index v1.2 | Pearson `0.622` (p `0.008`), Spearman `0.669`, `n=17` | Pearson `0.411` (p `0.114`), `n=17` | `player_wins_percent`: Pearson `0.512` (p `0.036`), Spearman `0.517`, `n=17` | `R2=-1.200` vs baseline `-0.158`; rank Spearman `-0.100`; `n=15` |
| DELEGATE-52 (RS@20) | Pearson `0.386` (p `0.172`), Spearman `0.538`, `n=14` | Pearson `0.285` (p `0.345`), `n=14` | `completion_tokens_black_per_move`: Pearson `-0.583` (p `0.023`), Spearman `-0.418`, `n=15` | `R2=-0.928` vs baseline `-0.146`; rank Spearman `0.234`; `n=15` |
| BullshitBench v2 | Pearson `0.291` (p `0.025`), Spearman `0.471`, `n=59` | Pearson `0.078` (p `0.565`), `n=58` | `games_interrupted_percent`: Pearson `-0.407` (p `0.001`), Spearman `-0.476`, `n=62` | `R2=0.046` vs baseline `-0.032`; rank Spearman `0.477`; `n=59` |

The OLS CV column now carries its own `n`. That is deliberate: the cross-validated `R2` is computed
on the rows that survive dropping any missing target or candidate feature, which is smaller than the
metric-analysis sample the block was handed (ECI: `R2` on 91 rows drawn from a sample of 97). The
aggregate artifacts previously reported only the larger number next to the `R2`, which overstated the
sample behind every published prediction figure.

p-values are two-sided tests on each correlation (`pearson_p` in the per-eval `*_summary.json`, also
carried in `cross_ref_summary.json` and the HTML reports). Release-controlled p-values are computed
at `df = n - 3`, not `n - 2`: residualizing both variables on release month spends a degree of
freedom on the covariate, and each block now records its `df` and `controlled_variables` explicitly.
The p-values remain descriptive, not multiplicity-controlled: each eval tests 8 non-Elo chess metrics
plus raw and release-controlled Elo, and the "Top chess metric" column is the strongest of those by
construction, so its p-value is optimistic — read it as "the leading metric clears the bar," not as a
corrected significance claim. The max-dedupe selection (highest external score per player) and small
samples (DELEGATE-52 `n=14`, Vals Index `n=17`) also mean these p-values assume more than the design
delivers. Where uncertainty matters most, the bootstrap 95% CIs in each eval's `raw_elo` block are
the more honest read.

Interpretation:

- **ECI**: usable relationship, and the strongest on every axis. Raw Elo is `p<0.001` at
  `n=81` (bootstrap 95% CI `0.705–0.842`), and — the part that matters — the relationship still
  clears `p<0.001` *after* release-month control (`r=0.584`, `n=80`). So ECI's link to chess Elo is
  not just the chronology trend that BullshitBench mostly reduces to. `player_wins_percent` is the
  strongest non-Elo metric and is also `p<0.001`. Fold-local OLS predicts the index well above a
  trivial baseline (`R2=0.557` on 91 rows). This is the eval to treat as a real signal. The
  2026-07-28 refresh moved every figure up against the previous publish (`0.766`→`0.782` raw,
  `0.549`→`0.584` release-controlled, `R2` `0.547`→`0.557`) on a sample that grew from 71 to 81, and
  the bootstrap interval tightened at its lower end (`0.675`→`0.705`). The movement is a coverage
  effect rather than a change in the underlying relationship: re-running the previous snapshot and
  mapping through current code reproduces the published `r=0.766`/`n=71` exactly, and holding the
  mapping decisions fixed while swapping in the new snapshot leaves it at `r=0.764`/`n=71`. The
  eleven newly accepted rows are what moved it.
- **ARC-AGI-2**: the second-strongest eval, and the 2026-07-28 snapshot refresh strengthened it
  again. Raw Elo went `0.697`→`0.730` (`n` 60→67, bootstrap 95% CI `0.582–0.837`), Spearman
  `0.729`→`0.773`, and the OLS prediction `R2` `+0.157`→`+0.250` on 68 rows against a `-0.030`
  baseline. Release-controlled Elo is the one figure that did not move up (`0.530`→`0.520`), but it
  stays `p<0.001` at `df=64`, so the relationship is still not just chronology. As with ECI, the
  movement is a **coverage effect, not a changed relationship**: re-running the previous snapshot and
  mapping through current code reproduces the published `r=0.697`/`n=60` exactly, and the new
  snapshot with its 26 new rows held unmatched reproduces `r=0.697168635085473`/`n=60` to the last
  digit — every retained row is unchanged. The 19 newly mapped rows, which add seven LLM Chess
  players to the Elo sample (the `-high` and `-medium` tiers of GPT-5.6 Sol, Terra, and Luna, plus
  `claude-opus-4-8_adaptive-thinking-high`), are what moved it. Those seven are frontier models at
  the top of the ARC score range, which is why a 7-row addition moves `r` this much — and is also the
  caveat: the sample gained range, not just size.
- **Vals Index**: v1.2 is promising but not yet weight-bearing. Raw `r=0.622` (`p=0.008`) and
  `rho=0.669` (`p=0.003`) at `n=17` are the second-strongest raw figures in the set, but the
  bootstrap 95% Pearson interval spans `0.256–0.870`, release-month control drops it to `r=0.411`
  (`p=0.114`, not significant at `df=14`), and the OLS prediction is far below baseline
  (`R2=-1.200` on 15 rows, rank Spearman `-0.100`). The component tasks do not track Elo uniformly:
  `terminal_bench_2_1` alone reaches `r=0.791` while `corp_fin_v2` is `r=0.303` (`p=0.237`), so the
  composite should not be read as one undifferentiated capability signal. Treat it as indicative.
- **DELEGATE-52**: still the least conclusive. Raw endpoint correlation is `r=0.386` and **not
  significant** (`p=0.172`, `n=14`; bootstrap 95% CI `-0.129 – 0.808`, which includes zero), partly
  deflated by release-month control (`0.386` → `0.285`, `p=0.345`), and OLS prediction is far below
  the mean baseline (`R2=-0.928`). Rank correlation is the one figure that clears `p<0.05`
  (`rho=0.538`, `p=0.047`). The `completion_tokens_black_per_move` association is negative
  (`-0.583`, `p=0.023`): models that spend more tokens per chess move tend to corrupt documents more
  — but at `n=15` this is fragile and exploratory. See the transcription caveat below before citing
  any DELEGATE-52 figure.
- **BullshitBench**: rank ordering is positive (`Spearman 0.471`) but the linear fit is low and the
  relationship almost entirely collapses under release-month control (`0.291` → `0.078`), meaning
  most of the apparent association is chronology, not a model-capability link. Raw Elo is only
  marginal (`p=0.025`) and the release-controlled correlation is indistinguishable from zero
  (`p=0.565`). Its OLS prediction does edge past the mean baseline (`R2=+0.046` vs `-0.032`), which
  contradicts the previous report's "neither beats the mean baseline" — but at that magnitude the
  honest reading is "no useful prediction either way," not a win.
- **No shared headline metric, but the majority has shifted**: `player_wins_percent` now leads for
  ECI, Vals Index, *and* ARC-AGI-2, while BullshitBench leads with `games_interrupted_percent` and
  DELEGATE-52 with `completion_tokens_black_per_move`. Read the three-way agreement cautiously: ARC's
  lead changed hands only in this refresh (`average_game_cost` led the previous publish) and is a
  near-tie now (`player_wins_percent` `+0.511` vs `average_game_cost` `+0.476`, and
  `average_game_cost` still wins on rank, `+0.675` vs `+0.674`). BullshitBench's lead is a near-tie
  too (`games_interrupted_percent` `-0.407` vs `average_game_cost` `+0.404`). Do not treat which
  metric ranks first as a finding in either case.

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
- Raw Elo correlates external score directly with LLM Chess Elo, tested at `df = n - 2`.
- Release-controlled Elo first predicts each side from release month, subtracts predicted from
  actual on both sides, then correlates the two residual lists — tested at `df = n - 3`, because the
  covariate costs a degree of freedom. Each release-controlled block records its own `df`.
- OLS CV uses repeated 5-fold cross-validation over 3 seeds. Feature selection happens inside each
  training fold, not on the full target sample. Its `n` is the post-dropna row count, reported
  alongside every `R2`.

## Coverage Debt

| Eval | Numeric rows | Accepted mappings | Metric sample | Elo sample | Unresolved rows (unmatched / ambiguous / excluded) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Epoch ECI | 213 | 104 | 97 | 81 | 109 (109 / 0 / 0) |
| ARC-AGI-2 | 177 | 93 | 70 | 67 | 89 (27 / 54 / 8) |
| BullshitBench v2 | 162 | 71 | 62 | 59 | 91 (85 / 6 / 0) |
| Vals Index v1.2 | 40 | 17 | 17 | 17 | 23 (23 / 0 / 0) |
| DELEGATE-52 | 19 | 15 | 15 | 14 | 4 (2 / 2 / 0) |

ARC's 93 accepted mappings are five fewer than its 98 accepted-status rows: the remaining five carry
no numeric ARC score and are filtered before analysis.

Each per-eval summary's `unresolved_high_impact_rows` block lists the **15 highest-scoring**
unresolved rows, capped at 15 — it is a review queue, not a count. DELEGATE-52's block holds 4
because that is all it has.

The published audit (`results/audit_summary.json`, regenerated 2026-07-28) reports
`reproducibility_status = pass` — all **five** per-eval artifacts reproduce cleanly against current
authoritative inputs, `evals_with_diff_count = 0` — with `coverage_status = review-needed` and
`overall_status = review-needed`. The `review-needed` verdict is driven entirely by
`unresolved_row_count = 316` across the five external evals (621 mapping rows total, 133 unique LLM
Chess players) against an `allowed_unresolved_row_count` of 0. Separately,
`run_cross_ref.py verify` reports `overall_status = pass` on all four checks: published summary
hashes, recorded LLM Chess input rows, artifact/player agreement, and mapping player resolution.

### Epoch ECI Mapping Shape

The 2026-07-28 snapshot's 213 rows resolve to 104 `accepted` mappings (104 rows → 97 unique LLM Chess
players in the metric sample, 81 in the Elo sample after dedupe) and 109 `unmatched`, with no
`alias`, `variant-compatible`, `ambiguous`, or `excluded` rows. Upstream added 38 models and dropped
3 since the 2026-05-29 snapshot; 7 of the 38 additions are accepted (the GPT-5.6 Sol/Terra/Luna trio,
Claude Opus 4.8, Grok 4.3 Beta, Gemini 3.1 Flash-Lite, Amazon Nova Pro) and 5 inherited rows were
revisited into accepted or better-targeted mappings. **The unresolved count rose from 84 to 109
even as coverage improved**, because most of what Epoch added is either a model LLM Chess has never
run or an older backfill row. As with Vals Index, the highest-scoring rows upstream
(`GPT-5.5 Pro`, `Claude Fable 5`, `Claude Opus 5`) have no counterpart, so the matched sample is
truncated at its high end.

Two mapped ECI rows carry caveats worth naming. `Amazon Nova Pro` maps to `amazon.nova-pro-v1`, which
has 33 chess games but no rated Elo, so it contributes to the metric sample and to nothing Elo-based.
`DeepSeek-V3.2` is a forced reasoning substitution: ECI publishes no effort, the assume-highest clause
points at a reasoning run, and `deepseek-V3.2_non-reasoning` is the only V3.2 player LLM Chess has.
Because ECI states no effort on any row, every accepted reasoning-model row is an assumed-highest
mapping, not a sourced one — see `evals/eci/SOURCE.md` and `mapping-research/eci.md`.

### ARC-AGI-2 Mapping Shape

The 2026-07-28 snapshot's 187 rows resolve to 22 `accepted`, 46 `alias`, and 30 `variant-compatible`
mappings (98 mapped rows, 93 with a numeric score → 70 unique LLM Chess players in the metric sample,
67 in the Elo sample after dedupe), with 54 `ambiguous`, 27 `unmatched`, and 8 `excluded`. Upstream
added 26 rows and dropped none. 19 of the 26 are mapped; the 7 that are not (`Claude Opus 5`
`(High)`/`(Max)`, the three `Grok 4.5` tiers, `GLM-5.2`, `Inkling`) are absent-family holds that
`eci` and `vals_index` hold on the same grounds. As on every other eval, the highest-scoring
unresolved row is a model LLM Chess has never run — `Claude Opus 5 (Max)` at `90.4`.

Two structural caveats belong with any ARC figure. First, ARC states an effort tier on nearly every
row and publishes tiers LLM Chess does not have, so 22 mapped rows are `nearest-tier` substitutions
rather than effort-matched comparisons (16 of the 30 `variant-compatible` rows, plus 3 `accepted` and
3 `alias`). Second, because dedupe keeps the highest external score per player, an ARC `xHigh` or
`Max` configuration can supply the score attributed to a `-high` chess run:
`gpt-5.6-sol-2026-07-09-high` enters the sample at `92.5` (the `Max` row), not at the `85.4` its own
`(High)` row scored. That is the documented coverage-first consequence, and it sets the external
score for 5 of the 67 Elo-sample rows — the three GPT-5.6 `(Max)` rows plus `GPT-5.5 (xHigh)` and
`GPT-5.4 (xHigh)`. The `ambiguous` block is
unchanged from the previous publish and is still dominated by the `Pro` product axis, Gemini
`Deep Think`, ARC `Refine.` harnesses, Claude Opus 4.6 `120K` context variants, and token-budget
rows. See `mapping-research/arc_agi_2.md`, including its "Open Rule Application Gap" section, which
this refresh deliberately did not close.

### Vals Index Mapping Shape

The 40 leaderboard rows resolve to 4 `accepted`, 1 `alias`, and 12 `variant-compatible` mappings (17
mapped rows → 17 unique LLM Chess players, all 17 in the Elo sample), with 23 `unmatched` and no
`ambiguous` or `excluded`. The three highest-scoring rows upstream (`anthropic/claude-fable-5`,
`anthropic/claude-opus-5`, `kimi/kimi-k3`) all lack an LLM Chess counterpart, so the matched sample
is **truncated at its high end** and the correlation is computed over a narrower score range than
the leaderboard covers. Vals states a per-row effort tier more often than any other cross-ref eval,
which makes the reasoning-effort mapping unusually well evidenced here — but the tier lives in
`reasoning_effort` for most vendors and in `compute_effort` for Anthropic, and 16 of 40 rows state
neither. See `mapping-research/vals_index.md` and `evals/vals-index/SOURCE.md`.

### DELEGATE-52 Mapping Shape

The 19 Table-1 rows resolve to 13 `variant-compatible` and 2 `alias` mappings (15 mapped rows → 15
unique LLM Chess players, 14 in the Elo sample), with 2 `unmatched` (Mistral Large 3; the original
Grok 4, distinct from the `grok-4-20*` revision in `elo_refined.csv`) and 2 `ambiguous` (an
unspecified GPT-4o snapshot; `gpt-oss-120b` with an unspecified reasoning tier). The paper does not
publish exact reasoning configs (Appendix L was not machine-extractable), so reasoning-capable base
models are mapped with a config caveat following the shared tier convention. See
`mapping-research/delegate_52.md`.

### BullshitBench Mapping Shape

The 162 leaderboard rows resolve to 6 `accepted`, 21 `alias`, and 44 `variant-compatible` mappings
(71 mapped rows → 62 unique LLM Chess players, 59 in the Elo sample after dedupe), with 85
`unmatched` and 6 `ambiguous`. Most unmatched rows are models with no LLM Chess counterpart (hosted
Qwen 3.5/3.6/3.7, GLM-5-turbo/5.1/4.5, DeepSeek V4, Gemma 4, Nemotron Super/Nano-9B, MiMo, StepFun,
Seed, ERNIE, Jamba, Prime Intellect, Arcee, GPT-5.5 Pro, and the `openrouter/*-alpha` stealth rows)
or non-reasoning `none` rows for OpenAI families that exist in `elo_refined.csv` only at reasoning
tiers. See `mapping-research/bullshit_bench.md`.

## Load-Bearing Caveats

- **Vals Index provenance is the weakest of the five.** There is no published CSV, JSON, or API. The
  snapshot is extracted from an Astro hydration payload embedded in the leaderboard page — an
  **undocumented framework internal**. If Vals switches to a client-side fetch or full server-side
  rendering, the extraction path breaks with no warning. The snapshot is also **pinned to index
  v1.2**, whose definition changed three times in 2026 (including a denominator rebalance from 3.7 to
  3.4 when the Law sector was dropped); a v1.1 number and a v1.2 number are different measurements,
  not a trend. See `evals/vals-index/SOURCE.md`.
- **DELEGATE-52 has an unresolved transcription discrepancy.** Its `GPT 5` and `Grok 4` rows fail the
  descending-order cross-check against the paper's Table 1 by 11.0 points, and the discrepancy cannot
  be resolved from the snapshot alone. Until someone re-reads arXiv `2604.15597v1` Table 1, treat the
  `GPT 5` row as unverified and any DELEGATE-52 conclusion that depends on its rank or magnitude as
  provisional. See `evals/delegate-52/SOURCE.md`, "Unresolved Row-Order Discrepancy".
- **Small-n evals are fragile, and this republish demonstrated it.** The mapping repoint moved
  DELEGATE-52's Elo sample from 13 to 14 rows and its CV sample from 14 to 15. That one row moved raw
  Elo `r` from `0.207` to `0.386` and the CV `R2` from `+0.031` to `-0.928`. Vals Index sits at
  `n=17`. Neither eval's point estimate should be quoted without its bootstrap interval.
- **Coverage debt is the dominant uncertainty, and it grew again.** 316 unresolved mapping rows means the audit's
  `coverage_status` is `review-needed` by design, and no claim here is safe if it assumes those rows
  would resolve in its favour.

## Exploratory: discipline beats strength (BullshitBench)

This is a research lead, outside the governed numbers. Running BullshitBench in clean mode
(`--mistake-stats clean_only` — drops every model whose earliest LLM Chess game predates the
2025-03-16 logging fix, leaving n=55 metric / 53 Elo) lets us use the normally-excluded error
metrics. `clean_only` refuses `--publish` by design, so these figures are **not** in `results/`;
they come from a regenerated run saved at
[exploratory/bullshit_bench_clean_only_summary.json](exploratory/bullshit_bench_clean_only_summary.json),
produced against the same snapshot, mapping CSV, and `elo_refined.csv` as the current publish. The
command that reproduces it is in [exploratory/README.md](exploratory/README.md).

Rank correlation vs `avg_score`, from that summary:

| Chess metric | Spearman | n |
| --- | ---: | ---: |
| `wrong_actions_per_1000moves` | -0.572 | 55 |
| `mistakes_per_1000moves` | -0.564 | 55 |
| `average_game_cost` | +0.517 | 52 |
| `games_interrupted_percent` | -0.416 | 55 |
| LLM Chess Elo | +0.390 | 53 |
| `wrong_moves_per_1000moves` | -0.339 | 55 |
| `player_wins_percent` | +0.032 | 55 |

Sloppy chess (illegal actions, blunders, interrupted games) tracks *failing* BullshitBench better
than raw strength does, and win rate is noise. It remains a rank association only: a multi-factor OLS
still does not beat the mean baseline (CV `R2=-0.264` on 52 rows vs baseline `-0.055`). So nonsense
detection looks like a carefulness/discipline trait, not a capability one — a lead, not a validated
result, and one that rests on artifacts outside the verified publish surface.

## What Raises Signal

1. Resolve high-impact mapping rows first: frontier GPT, Claude, Gemini, Grok, DeepSeek, Qwen, Kimi,
   and GLM rows near the top of each leaderboard. 316 unresolved rows is the single biggest
   constraint on every conclusion above.
2. Re-verify the DELEGATE-52 `GPT 5` and `Grok 4` rows against the paper. It is a bounded task that
   would move one eval from "provisional" to usable.
3. Keep plain-model rows separate from reasoning effort, product tier, context-window,
   benchmark-system, and preview variants unless source evidence proves equivalence.
4. Treat BullshitBench as a behavioral contrast eval, not a capability eval. Its value is showing
   where chess strength and epistemic pushback diverge, not validating Elo.
5. Grow the Vals Index matched sample before treating its `r=0.622` as real; at `n=17` with a
   high-end-truncated range, the bootstrap interval is doing most of the talking.
6. Treat OLS prediction as secondary. The primary signal is still raw and release-controlled Elo
   correlation plus row-level mapping quality.

## Evidence Pointers

- Methodology and workspace guide: [README.md](README.md)
- Audit status: [results/audit_summary.json](results/audit_summary.json), [results/audit_report.md](results/audit_report.md)
- Cross-eval aggregate: [results/cross_ref_summary.json](results/cross_ref_summary.json), [results/cross_ref_report.md](results/cross_ref_report.md)
- ECI summary: [results/eci_summary.json](results/eci_summary.json)
- ARC summary: [results/arc_agi_2_summary.json](results/arc_agi_2_summary.json)
- BullshitBench summary: [results/bullshit_bench_summary.json](results/bullshit_bench_summary.json)
- DELEGATE-52 summary: [results/delegate_52_summary.json](results/delegate_52_summary.json)
- Vals Index summary: [results/vals_index_summary.json](results/vals_index_summary.json)
- Per-eval reports: [results/eci.html](results/eci.html), [results/arc_agi_2.html](results/arc_agi_2.html), [results/bullshit_bench.html](results/bullshit_bench.html), [results/delegate_52.html](results/delegate_52.html), [results/vals_index.html](results/vals_index.html)
- Coverage: [results/eci_coverage.csv](results/eci_coverage.csv), [results/arc_agi_2_coverage.csv](results/arc_agi_2_coverage.csv), [results/bullshit_bench_coverage.csv](results/bullshit_bench_coverage.csv), [results/delegate_52_coverage.csv](results/delegate_52_coverage.csv), [results/vals_index_coverage.csv](results/vals_index_coverage.csv)
- Exploratory (not published, not verified): [exploratory/README.md](exploratory/README.md)
- Mapping sources: [mappings/eci.csv](mappings/eci.csv), [mappings/arc_agi_2.csv](mappings/arc_agi_2.csv), [mappings/bullshit_bench.csv](mappings/bullshit_bench.csv), [mappings/delegate_52.csv](mappings/delegate_52.csv), [mappings/vals_index.csv](mappings/vals_index.csv)
- Mapping rationale: [mapping-research/eci.md](mapping-research/eci.md), [mapping-research/arc_agi_2.md](mapping-research/arc_agi_2.md), [mapping-research/bullshit_bench.md](mapping-research/bullshit_bench.md), [mapping-research/delegate_52.md](mapping-research/delegate_52.md), [mapping-research/vals_index.md](mapping-research/vals_index.md)
- External provenance: [evals/eci/SOURCE.md](evals/eci/SOURCE.md), [evals/arc-agi-2/SOURCE.md](evals/arc-agi-2/SOURCE.md), [evals/vals-index/SOURCE.md](evals/vals-index/SOURCE.md), [evals/delegate-52/SOURCE.md](evals/delegate-52/SOURCE.md)
