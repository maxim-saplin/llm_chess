# ARC-AGI-2 Source Note

Snapshot file: `data/cross-ref/evals/arc-agi-2/arc-agi-2-apr-2026.csv`

Access date for supporting sources: 2026-04-28.

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

## Score Meaning

- Higher ARC-AGI scores are better.
- ARC describes ARC-AGI-2 as a reasoning benchmark with comparable public, semi-private, and private sets.
- ARC describes ARC-AGI-3 as an interactive agent benchmark; it is present in the export but not the primary target of this first cross-ref run.

## Cost Notes

- ARC policy says leaderboard costs use public retail pricing when possible and are generally reported as average cost per test-pair attempt.
- The official pages located during this implementation explain the general cost-per-task framing.
- No primary ARC source was located that defined a distinct `COST (V3)` field. That column is therefore preserved as source evidence, parsed conservatively, and called out as unresolved.

## Cross-Ref Caveats

- Leaderboard rows can represent systems, reasoning configurations, or benchmark-specific setups rather than plain base-model identities.
- Labels such as `Refine.`, `Deep Think`, `Max`, `xHigh`, token budgets, and context-window variants must not be collapsed casually into one LLM Chess row.
- Human baselines and system-level benchmark entries are kept in the normalized source and mapping outputs but are excluded from LLM Chess correlation samples.
- The row-to-LLM-Chess mapping for this snapshot lives at `data/cross-ref/mappings/arc_agi_2.csv` and must be reviewed there rather than inferred from the source labels alone.