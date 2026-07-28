# ARC-AGI-2 Source Note

Snapshot file: `data/cross-ref/evals/arc-agi-2/arc-agi-2-jul-2026.csv`

Access date: 2026-07-28 (upstream data `last-modified: 2026-07-24 18:00:09 GMT`).

This snapshot is a refresh of the ARC Prize leaderboard table. It supersedes the prior
`arc-agi-2-may-2026.csv` (161 rows): ARC added 26 systems and dropped none, so the file now holds
187 rows. Rows stay in the rendered leaderboard's order, which is model release date descending with
the three undated human baselines last.

## Provenance

The leaderboard page renders client-side and offers no CSV download, but the four data files it
joins are published at stable paths. All four were re-fetched with `curl` on 2026-07-28:

| URL | Role |
| --- | --- |
| <https://arcprize.org/media/data/evaluations.json> | 696 records keyed `(datasetId, modelId)`, with `score`, `costPerTask` or `cost`, `resultsUrl`, `display`. |
| <https://arcprize.org/media/data/models.json> | 206 systems: `id`, `displayName`, `modelReleaseDate`, `providerId`, `modelType`, `paperUrl`, `codeUrl`. |
| <https://arcprize.org/media/data/datasets.json> | 8 dataset ids and their display names. |
| <https://arcprize.org/media/data/providers.json> | 20 provider ids and their display names. |

These URLs are **stable**: the retrieval path carries no Next.js build id and no content hash, unlike
the `/_next/static/chunks/...` bundles that render them. They are the canonical machine-readable
entry point for the next refresh, and meet the same standard as the ECI and Vals Index sources. The
2026-07-28 fetch returned `etag: "6529094085f9ca7ce5f3c2e1957d3b9c"` for `evaluations.json`
(sha256 `de040bd62e3042e17aad3fa8183a92acb60ddae0eebfa9cc15cd93ac3909230f`) and
`etag: "bbdf5725ef7a703a7f0970e913262b6f"` for `models.json`
(sha256 `eea02d0a20d8eae6ae0e0eaebfe2d645050033756436d72bdd8632c75c6d27a2`).

Supporting pages:

- Leaderboard: <https://arcprize.org/leaderboard>
- ARC-AGI-1: <https://arcprize.org/arc-agi/1>
- ARC-AGI-2: <https://arcprize.org/arc-agi/2>
- ARC-AGI-2 announcement / technical framing: <https://arcprize.org/blog/announcing-arc-agi-2-and-arc-prize-2025>
- ARC-AGI-3 overview: <https://arcprize.org/arc-agi/3>
- ARC policy page: <https://arcprize.org/policy>

## How To Refresh This Snapshot

The snapshot is the rendered leaderboard table, but from this refresh onward it is **reconstructed
from the JSON above and then verified against the rendered page**, rather than scraped. The
reconstruction is deterministic:

1. **Row set.** One row per `modelId` that has at least one record in `evaluations.json` whose
   `datasetId` is `v1_Semi_Private`, `v2_Semi_Private`, or `v3_Semi_Private`. The three public-eval
   datasets and `v2_Private_Eval` never surface in the table. The record-level `display` flag is
   **not** a table filter: 14 of the semi-private records carry `display: false`, and the 7 models
   whose semi-private records are all `display: false` are rendered anyway, so the flag gates the
   page's scatter plot rather than the table. No cost filter is applied either — the earlier note
   describing a `< $10,000` cost filter is unsupported, and applying none reproduces the table
   exactly (the largest `COST/TASK` in the data is $200.00, so such a rule would not bind today
   even if it exists).
2. **Column mapping.**

   | Column | Source |
   | --- | --- |
   | `AI SYSTEM` | `models.json` `displayName` |
   | `AUTHOR` | `providers.json` `displayName` for the model's `providerId` |
   | `DATE` | `models.json` `modelReleaseDate`, date part only, reformatted ISO → day-month-year |
   | `SYSTEM TYPE` | `models.json` `modelType`, `N/A` when null |
   | `ARC-AGI-1` | `v1_Semi_Private` `score` |
   | `ARC-AGI-2` | `v2_Semi_Private` `score` |
   | `ARC-AGI-3` | `v3_Semi_Private` `score` |
   | `COST/TASK` | `costPerTask` of the `v2_Semi_Private` record, falling back to `v1_Semi_Private` |
   | `COST (V3)` | `cost` of the `v3_Semi_Private` record — that dataset publishes `cost`, never `costPerTask` |
   | `CODE / PAPER` | 📄 when `paperUrl` is set, 💻 when `codeUrl` is set, both concatenated, `—` when neither |

3. **Formatting.** JSON scores are fractions in `0..1`; the table renders `(score * 100).toFixed(1)`
   with a `%` suffix. `COST/TASK` is `toFixed(3)` below `$1` and `toFixed(2)` at or above it.
   `COST (V3)` is `(cost / 1000).toFixed(1)` with a `K` suffix. Reproduce JavaScript `toFixed`
   semantics — round half away from zero on the exact double — not Python's round-half-even; six
   cells in this snapshot differ between the two (for example `0.0125` renders `1.3%`, not `1.2%`).
4. **Order.** Release date descending; models with a null `modelReleaseDate` (the human baselines)
   keep their `models.json` order at the end.
5. **Verify.** Load <https://arcprize.org/leaderboard>, extract the rendered `<table>`, and compare
   row for row. The 2026-07-28 reconstruction matched the rendered table on **187 of 187 rows across
   all ten columns**, and independently reproduced the prior hand-scraped snapshot on 160 of its 161
   retained rows byte for byte (the one difference is `GPT-5.2 (Refine.)`, whose `CODE / PAPER` cell
   gained a paper link upstream). Do not ship a reconstruction that does not reproduce the rendered
   table exactly.

## Local Snapshot

- Local file columns: `AI SYSTEM`, `AUTHOR`, `DATE`, `SYSTEM TYPE`, `ARC-AGI-1`, `ARC-AGI-2`,
  `ARC-AGI-3`, `COST/TASK`, `COST (V3)`, `CODE / PAPER`. The schema is unchanged from the prior
  snapshot; the adapter reads these exact names.
- The file carries a UTF-8 BOM, as the previous snapshot did.
- Dates use day-month-year formatting, reformatted from the upstream ISO dates.
- Scores are percentage-like strings or `N/A` values.
- `ARC-AGI-3` is still sparse: 26 of 187 rows carry a score, up from 6 of 161.

### Duplicate Labels

Four `AI SYSTEM` labels appear twice: `Grok 4 (Refine.)` (distinguished only by `AUTHOR`,
`J. Berman` versus `E. Pang`), and `GPT-5.5 (High)`, `GPT-5.4 (High)`, `Gemini 3.1 Pro (Preview)`
(each a separate ARC-AGI-3-only entry alongside the ARC-AGI-1/2 entry, with a different release
date). `models.json` **does** give every one of them a distinct stable `id` —
`jeremy_sept_2025` versus `eric_pang_sept_2025`, `gpt-5-4-high` versus
`openai-gpt-5-4-2026-03-05-high`, and so on. That id is a better disambiguator than `AUTHOR` and is
stable across refreshes, unlike the row position `eval_row_id` encodes. It is not currently carried
into the snapshot schema, because doing so would change the columns the adapter reads; carrying it
would be a worthwhile follow-up.

## Score Meaning

- Higher ARC-AGI scores are better.
- ARC describes ARC-AGI-2 as a reasoning benchmark with comparable public, semi-private, and private
  sets. The leaderboard's `ARC-AGI-2` column is the **semi-private** set.
- ARC describes ARC-AGI-3 as an interactive agent benchmark; it is present in the export but is not
  the cross-ref target.

## Cost Notes

- ARC policy says leaderboard costs use public retail pricing when possible and are generally
  reported as average cost per test-pair attempt.
- `COST/TASK` tracks the ARC-AGI-1/2 datasets and parses at 1.0.
- `COST (V3)` is the per-task cost on the ARC-AGI-3 (`v3_Semi_Private`) dataset. This refresh
  confirmed it directly: `v3_Semi_Private` evaluation records carry a `cost` field where every other
  dataset carries `costPerTask`, and the leaderboard divides it by 1000 and appends `K`.
  `parse_currency` now expands that shorthand, so `cost_v3` parses at 1.0 rather than the previous
  0.0. Two caveats remain, so keep cost interpretation conservative: the rendered value is rounded to
  one decimal of a thousand dollars, which discards up to ±$50 of precision against the underlying
  JSON number, and only 26 of 187 rows carry a value. The column feeds no statistic.

## Cross-Ref Caveats

- Leaderboard rows can represent systems, reasoning configurations, or benchmark-specific setups
  rather than plain base-model identities.
- Labels such as `Refine.`, `Deep Think`, `Max`, `xHigh`, token budgets, and context-window variants
  must not be collapsed casually into one LLM Chess row. Those suffixes come from the upstream
  `displayName` and are not derived by us.
- Human baselines and system-level benchmark entries are kept in the normalized source and mapping
  outputs but are excluded from LLM Chess correlation samples.
- The row-to-LLM-Chess mapping for this snapshot lives at `data/cross-ref/mappings/arc_agi_2.csv` and
  must be reviewed there rather than inferred from the source labels alone.

## Row-Set Delta And Mapping Re-Key

All 161 prior rows are retained; ARC dropped none. The 26 additions are `Claude Opus 5 (High/Max)`,
`Claude Opus 4.8 (Low/Medium/High/Max)`, the fifteen `GPT-5.6 Sol`/`Terra`/`Luna`
`(Low/Medium/High/xHigh/Max)` rows, `Grok 4.5 (Low/Medium/High)`, `GLM-5.2`, and `Inkling`.

Because `eval_row_id` is the normalize-time row position, `mappings/arc_agi_2.csv` was re-keyed. Each
retained row was matched to its new position on `(AI SYSTEM, AUTHOR, DATE, ARC-AGI-1, ARC-AGI-2,
ARC-AGI-3)`, which is unique in both files and survives the duplicate-label cases; all 161 reviewed
decisions carried over, and 26 rows were added. No row ends with `mapping_status` `missing`, which is
the check that the carry landed on the right positions.

Of the 26 new rows, 19 resolve to an LLM Chess player and 7 stay `unmatched`
(`Claude Opus 5`, `Grok 4.5`, `GLM-5.2`, and `Inkling` have no counterpart in `elo_refined.csv`).
See `data/cross-ref/mapping-research/arc_agi_2.md` for the per-row reasoning clauses.
