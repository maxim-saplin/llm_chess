# Epoch ECI Source Note

Snapshot file: `data/cross-ref/evals/eci/epoch_eci_may_2026.csv`

Access date for supporting sources: 2026-05-29.

This snapshot is a refresh of the overall (composite) Epoch ECI leaderboard taken from
`https://epoch.ai/data/eci_scores.csv` on 2026-05-29 (178 models). It supersedes the prior
`epoch_eci_apr_2026.csv` (168 models): Epoch added 14 models and dropped 4 unscored ones since
that snapshot. `Score` and the `90% CI` bounds are Epoch's published `eci`, `eci_ci_low`, and
`eci_ci_high` rounded to integers to match the website display and the prior snapshot schema. The
`llm_chess_model` snapshot bridge column is historical seed data and was carried over by label for
retained models only; `mappings/eci.csv` is the live mapping source of truth.

Mapping reconciliation in this refresh:
- `GPT-5.4` was re-pointed from `gpt-5.4-low` to `gpt-5.4-medium` (the prior pick predated
  `gpt-5.4-medium` existing in `elo_refined.csv`; base GPT-5.x rows map to the `-medium` tier).
- Of the 14 new ECI models, 4 with clear LLM Chess counterparts were accepted following the family
  tier convention (`GPT-5.5`→`gpt-5.5-medium`, `GPT-5.3 Codex`→`gpt-5.3-codex-medium`,
  `GPT-5.4 Mini`→`gpt-5.4-mini-high`, `GPT-5.4 Nano`→`gpt-5.4-nano-high`).
- `grok-4-20-reasoning` was reassigned from Epoch `Grok 4` to Epoch `Grok 4.20` (maintainer-confirmed
  that the LLM Chess id is Grok 4.20). Epoch `Grok 4` is now `unmatched` (no plain grok-4 in
  `elo_refined.csv`). Net accepted mappings: 93.
- The remaining new/affected rows stay `unmatched` with explicit reasons in `open_questions` (no LLM
  Chess entry, or a distinct product/host tier): GPT-5.5 Pro, Kimi K2.6, GLM-5.1, Gemini 3.5 Flash,
  and the hosted Qwen 3.5/3.6 models.

## Provenance

- Primary benchmark hub: <https://epoch.ai/benchmarks>
- Methodology / about page: <https://epoch.ai/benchmarks/about>
- Explainer: <https://epoch.ai/blog/a-rosetta-stone-for-ai-benchmarks>
- Paper: <https://arxiv.org/abs/2512.00193>
- Reference implementation: <https://github.com/epoch-research/benchmark-stitching>

## Local Snapshot

- Local file columns: `Model`, `Score`, `90% CI`, `llm_chess_model`.
- The local `llm_chess_model` column is historical bridge seed data. It is preserved for migration and parity checks, but it is no longer treated as authoritative mapping truth.
- The snapshot is used to compare Epoch's composite ECI capability estimate against LLM Chess Elo and behavior metrics.

## Score Meaning

- ECI is a stitched capability index across multiple benchmarks.
- Higher ECI means higher estimated capability.
- The scale is relative rather than bounded; Epoch describes the current normalization such that Claude 3.5 Sonnet is anchored at 130 and GPT-5 at 150.
- Confidence intervals in the local snapshot are 90 percent intervals.

## Methodology Notes

- Epoch stitches benchmark results onto a common capability scale rather than treating raw benchmark accuracy as directly comparable across tasks.
- The benchmark stitching system uses both internally run evaluations and external leaderboard or primary-source results.
- Epoch reports that developer-reported scores can be cherry-picked, and that internal evals plus independently run leaderboards are used to reduce that bias.
- Models must have enough benchmark coverage to be included in ECI; the benchmark hub states a minimum of four benchmark evaluations.

## Cross-Ref Caveats

- ECI is a composite score, not a single-task accuracy metric.
- ECI rows can reflect best-of benchmark settings within Epoch's aggregation rules, which do not always align one-to-one with the LLM Chess model/config inventory.
- The migrated generic mapping file lives at `data/cross-ref/mappings/eci.csv` and should be reviewed through that contract rather than by reading the source bridge column directly.