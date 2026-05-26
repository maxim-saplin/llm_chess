# Epoch ECI Source Note

Snapshot file: `data/cross-ref/evals/eci/epoch_eci_apr_2026.csv`

Access date for supporting sources: 2026-04-28.

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