# ARC-AGI-2 Source Note

Snapshot file: `data/cross-ref/evals/arc-agi-2/arc-agi-2-may-2026.csv`

Access date for supporting sources: 2026-05-29 (upstream data `last-modified: 2026-05-19`).

## Provenance

- Leaderboard: <https://arcprize.org/leaderboard>
- ARC-AGI-1: <https://arcprize.org/arc-agi/1>
- ARC-AGI-2: <https://arcprize.org/arc-agi/2>
- ARC-AGI-2 announcement / technical framing: <https://arcprize.org/blog/announcing-arc-agi-2-and-arc-prize-2025>
- ARC-AGI-3 overview: <https://arcprize.org/arc-agi/3>
- ARC policy page: <https://arcprize.org/policy>

## Local Snapshot

- Local file columns: `AI SYSTEM`, `AUTHOR`, `DATE`, `SYSTEM TYPE`, `ARC-AGI-1`, `ARC-AGI-2`, `ARC-AGI-3`, `COST/TASK`, `COST (V3)`, `CODE / PAPER`.
- Dates use day-month-year formatting in the source export.
- Scores are percentage-like strings or `N/A` values.
- `ARC-AGI-3` is sparse in this snapshot.

## How To Refresh This Snapshot

The leaderboard table at <https://arcprize.org/leaderboard> renders client-side from machine-readable JSON; there is no single CSV download. The frozen snapshot is the rendered leaderboard table (all ten columns above), with the `DATE` column reformatted from ISO `YYYY-MM-DD` to day-month-year. To refresh:

1. Load the leaderboard, extract the rendered `<table>` rows (a11y/DOM), and reformat the date column.
2. The underlying data files the page joins are also fetchable directly:
   - `https://arcprize.org/media/data/models.json` (id, displayName, modelReleaseDate, providerId, modelType, paperUrl, codeUrl)
   - `https://arcprize.org/media/data/evaluations.json` (datasetId, modelId, score, costPerTask/cost, display)
   - `https://arcprize.org/media/data/providers.json` and `datasets.json`
   Reconstructing the table from these requires reproducing the site's join, dedup, and `< $10,000` cost filter, so the rendered table stays the authoritative export basis.

## Score Meaning

- Higher ARC-AGI scores are better.
- ARC describes ARC-AGI-2 as a reasoning benchmark with comparable public, semi-private, and private sets.
- ARC describes ARC-AGI-3 as an interactive agent benchmark; it is present in the export but not the primary target of this first cross-ref run.

## Cost Notes

- ARC policy says leaderboard costs use public retail pricing when possible and are generally reported as average cost per test-pair attempt.
- The official pages located during this implementation explain the general cost-per-task framing.
- `COST (V3)` is the per-task cost on the ARC-AGI-3 (`v3_Semi_Private`) dataset, distinct from `COST/TASK` which tracks the ARC-AGI-1/2 datasets. This was confirmed from the upstream `evaluations.json` during the 2026-05 refresh: ARC-AGI-3 evaluation records carry a `cost` field, and the leaderboard renders it in the `COST (V3)` column. The values are large (thousands of dollars per task) and remain `N/A` for most rows. The adapter still parses this column conservatively — `parse_currency` does not handle the `$X.XK` shorthand, so the `cost_v3` numeric parse rate is 0.0 and the column is not used in any statistic.

## Cross-Ref Caveats

- Leaderboard rows can represent systems, reasoning configurations, or benchmark-specific setups rather than plain base-model identities.
- Labels such as `Refine.`, `Deep Think`, `Max`, `xHigh`, token budgets, and context-window variants must not be collapsed casually into one LLM Chess row.
- Human baselines and system-level benchmark entries are kept in the normalized source and mapping outputs but are excluded from LLM Chess correlation samples.
- The row-to-LLM-Chess mapping for this snapshot lives at `data/cross-ref/mappings/arc_agi_2.csv` and must be reviewed there rather than inferred from the source labels alone.