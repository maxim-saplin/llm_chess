# Vals Index Source Note

Snapshot file: `data/cross-ref/evals/vals-index/vals_index_v1_2_july_2026.csv`

Access date: 2026-07-27. Upstream `metadata.updated`: 2026-07-23. Index version: **v1.2**.

## Provenance

- Canonical URL: <https://www.vals.ai/benchmarks/vals_index>
- Retrieved with a single `curl` — HTTP 200, 448,980 bytes, `text/html`. **No browser is needed to
  refresh this snapshot.**

### The data is an embedded props blob, not a published file

**Read this before trusting or refreshing the snapshot.** This is the weakest provenance of the five
cross-ref evals, and it is weak in a specific way worth naming: ECI is refreshed from Epoch's
*published* `eci_scores.csv`, a file whose existence upstream has committed to. The Vals Index has no
equivalent. There is no CSV, no JSON download, and no API. Verified on 2026-07-27:

| Probe | Result |
| --- | --- |
| `https://www.vals.ai/api/benchmarks/vals_index` | 404 |
| `https://www.vals.ai/robots.txt` | 404 |
| `https://www.vals.ai/sitemap.xml` | 404 |

The page is an [Astro](https://astro.build) island: client-rendered, with the leaderboard data
serialized into the HTML as a component props attribute. The three probes above were re-run for this
snapshot; the further finding that the page issues **no data XHR** comes from the earlier browser
spike that located this path, and was not re-checked here — a curl-only refresh cannot check it. What
we read is therefore **an undocumented framework internal** — Astro's hydration payload format — not
an interface Vals publishes or promises to keep. If Vals switches the component to a client-side
fetch, or to full server-side rendering that emits only rendered markup, **this extraction path
breaks with no warning and no deprecation notice.** Treat a future refresh that returns 0 rows as an
upstream format change, not as an empty leaderboard.

### Extraction procedure

1. Fetch the canonical URL.
2. Select the `<astro-island>` element whose `component-url` **basename starts with
   `BenchmarkView`**.
3. HTML-entity-unescape that element's `props` attribute, then `json.loads` it.
4. Recursively unwrap Astro's `[PROP_TYPE, value]` tuples (`0` = Value, `1` = JSON, `11` = Infinity).
   Both `0` and `1` can carry containers whose *children* are themselves tuples, so the unwrap must
   recurse through either — stopping at type `0` yields a half-decoded tree.
5. Read `.benchmarkView.tasks.overall`.

**The deploy hash in the island's `component-url` is not part of the retrieval path.** On this fetch
the attribute read `component-url="/_astro/BenchmarkView.DySTHnY3.js"`, and `DySTHnY3` is a build
hash that changes on every Vals deploy. It is used here **only as a selector**: match on the
`BenchmarkView` basename *prefix* and the hash is irrelevant. Do not record it, pin it, or conclude
that the snapshot is deploy-scoped — a refresher who treats the hash as load-bearing will think the
path is broken when it is merely rebuilt.

### Shape of the payload

`.benchmarkView.tasks.overall` is a **dict keyed by `model_key`**, not a list of rows — 40 keys, one
per model. The sibling task maps `corp_fin_v2`, `finance_agent`, `swebench`, `terminal_bench_2_1` and
`vibe_code_bench` are each also 40 keys, and each covers exactly the same 40 `model_key` values as
`overall` (verified: zero missing). `.benchmarkView.metadata` supplies `version: "1.2"`,
`updated: "2026-07-23"`, `dataset_type: "private"`, and `total_models: 40`.

**The payload contains no display-name field.** Model identity upstream *is* the `model_key`, a
`provider/slug` string such as `openai/gpt-5.6-sol`. The snapshot is therefore keyed on `model_key`,
and `provider` comes from the payload's own per-row `provider` field. `model_slug` in the snapshot is
derived mechanically as the substring after the first `/`; it is presentational only, and **no column
the pipeline reads depends on a display name.** This is deliberate: display names are only available
from the rendered DOM, and a curl-only refresh must not need a browser.

## Version Pinning — cross-version comparison is not meaningful

**This snapshot is pinned to Vals Index v1.2 and its scores must not be compared against any other
index version.** The Vals Index is a *composite*, and its definition changed three times in 2026.
Per the page's own Updates log:

| Date | Change |
| --- | --- |
| 5/27/2026 | Coding bucket's Terminal-Bench moved to **2.1** (same 0.25 weight). |
| 5/13/2026 | Finance side swapped to **Finance Agent v2** (index subset, three runs averaged per model). |
| 5/4/2026 | **Vibe Code Bench added** to coding at 0.5 weight; **Law sector (CaseLaw) removed** as saturated, and the denominator rebalanced **3.7 → 3.4** for the dropped 0.3 law weight. |

A denominator change alone rescales every model's score. A model's v1.1 number and its v1.2 number
are different measurements, not a trend.

Current (v1.2) formula, quoted from the page:

```text
Coding     = 0.25 * SWE_Bench + 0.25 * TBench + 0.5 * VibeCodeBench
Vals_Index = ( 2.0 * AVG(CorpFin, FinanceAgent) + 1.4 * Coding ) / 3.4
```

Weights are the sectors' stated U.S. GDP contribution: Finance 2.0 (~$2T), Coding 1.4 (~$1.4T).

**This formula was verified against the snapshot, not merely quoted.** Recomputing the anchor from
the five component columns reproduces all 40 published `vals_index` values to within 0.00049 — the
rounding of the published number to three decimals. That is an independent check that the anchor and
the component columns in this snapshot are mutually consistent and correctly decoded.

Archived versions have stable slugs: `https://www.vals.ai/benchmarks/vals_index_v1_1` returns HTTP
200 (248,294 bytes). A future refresher who needs the v1.1 numbers can fetch them directly rather
than reconstructing them.

## Local Snapshot

40 rows × 20 columns, one row per evaluated model, sorted by `vals_index` descending (ties broken by
`model_key`) so the row order is leaderboard order and stable across refetches — the payload dict's
insertion order is not a documented guarantee, so it is not relied on.

| Column | Meaning |
| --- | --- |
| `model_key` | Upstream identity, `provider/slug`. The mapping's join label. |
| `model_slug` | Derived from `model_key` after the first `/`. Presentational only. |
| `provider` | Payload's per-row vendor label (e.g. `OpenAI`, `Moonshot AI`, `SpaceXAI`). |
| `vals_index` | **Anchor.** The composite index score. |
| `corp_fin_v2`, `finance_agent`, `swebench`, `terminal_bench_2_1`, `vibe_code_bench` | The five component task scores. |
| `stderr` | Upstream standard error of the index score. |
| `latency`, `cost_per_test` | Upstream run cost/latency figures. |
| `reasoning_effort`, `compute_effort`, `reasoning`, `verbosity`, `temperature`, `top_p`, `max_output_tokens`, `harness` | Per-row run configuration as published. |

### Score semantics

- All scores are **already 0–100**; no percent parsing or rescaling is applied. Verified against the
  rendered page: the top three are 75.145 (`anthropic/claude-fable-5`), 74.820
  (`anthropic/claude-opus-5`), 74.700 (`kimi/kimi-k3`). Observed `vals_index` range across the 40
  rows: 30.041 – 75.145.
- Higher is better, for the anchor and for all five component columns.
- `dataset_type` is `private`, so the underlying task instances are not inspectable. Contamination
  claims cannot be checked from this source in either direction.

### Effort metadata is split across two columns

Vals states a per-row effort tier more often than any other cross-ref eval, which makes it better
tier evidence than the mapping usually gets — but **it lives in two different columns depending on
vendor**, and neither alone tells you whether a row stated one:

- `reasoning_effort` — most vendors. Values across the 40 rows: `high` ×10, `max` ×4, `xhigh` ×4,
  `0.99` ×1, null ×21.
- `compute_effort` — **Anthropic** rows carry their tier here instead: `max` ×4, `high` ×1, null ×35.
  All 5 non-null `compute_effort` rows are Anthropic; the remaining 2 Anthropic rows state neither.

Merged, that gives `high` ×11, `max` ×8, `xhigh` ×4, `0.99` ×1.

The adapter therefore derives a single `stated_effort` as `reasoning_effort` falling back to
`compute_effort`. That yields 24 of 40 rows with a stated tier and 16 unstated.

Two irregularities to keep in view:

- `thinkingmachines/inkling` reports `reasoning_effort` as the float **`0.99`**, not a tier name. It
  is not on any tier scale the mapping rule speaks, and the row has no LLM Chess counterpart anyway.
- `grok/grok-4.20-0309-reasoning` and `anthropic/claude-haiku-4-5-20251001-thinking` state no effort
  at all; their reasoning *kind* is encoded in the model name suffix instead.

## How To Refresh This Snapshot

1. `curl https://www.vals.ai/benchmarks/vals_index` into a scratch file. Confirm HTTP 200 and a
   plausible byte count. **No browser, no `--publish`.**
2. Re-run the extraction procedure above. **Check `.benchmarkView.metadata.version` first.** If it is
   no longer `1.2`, the index definition has changed: read the Updates log, re-pin this note to the
   new version, and do **not** diff the new scores against the v1.2 snapshot as if they were a trend.
3. Confirm `metadata.total_models` equals the `overall` key count, and that every sibling task map
   covers the same keys.
4. Re-verify the anchor against the published formula, as above. It is the cheapest available check
   that the decode is correct, and it is independent of the anchor column itself.
5. Re-key the mapping. `eval_row_id` is the normalize-time row position, so any change in the row set
   or in the sort order needs a fresh key: index the existing mapping by `eval_model_label`
   (= `model_key`), carry each retained model's reviewed decision onto its new position, and drop
   rows upstream no longer lists.
6. Rename the file for the new version and date, then update the adapter `SOURCE_PATH`, this note, the
   `README.md` artifact map, `mapping-research/vals_index.md`, and the filename assertion in
   `tests/test_cross_ref.py`.

## Cross-Ref Caveats

- **The retrieval path is an undocumented internal.** See above. This is a real step below ECI's
  published `eci_scores.csv` and should be stated whenever this eval's figures are cited.
- **The matched sample is small: 17 of 40 rows.** That is close to DELEGATE-52's 14, where a single
  row moved the reported correlation from 0.381 to 0.207. **Treat any Vals Index correlation as
  indicative, not as a finding.** The bootstrap 95% interval on the Pearson value spans roughly
  0.26–0.87 — wide enough that the point estimate should not be quoted without it.
- The three highest-scoring rows upstream (`claude-fable-5`, `claude-opus-5`, `kimi-k3`) all lack an
  LLM Chess counterpart, so the matched sample is **truncated at its high end**. The correlation is
  computed over a narrower score range than the leaderboard covers.
- **The index measures weighted finance and coding task performance, not broad capability.** Two
  sectors, five tasks, weights chosen by GDP contribution rather than by breadth. It can diverge from
  chess Elo for reasons that are about the benchmark's scope, not about model quality.
- Because the anchor is a composite, the reported analysis carries the Elo relationship for each of
  the five component tasks and for the two weighted buckets alongside it, so no single sub-benchmark
  silently drives the conclusion. Worth noting from the current run: the component columns do **not**
  track Elo uniformly — `terminal_bench_2_1` alone ranks higher against Elo than the composite does,
  while `corp_fin_v2` is near zero. At n=17 that spread is not a finding, but it is a reason not to
  read the composite as one undifferentiated capability signal.
- The row-to-LLM-Chess mapping lives at `data/cross-ref/mappings/vals_index.csv` and must be reviewed
  there rather than inferred from `model_key` alone. Evidence notes:
  `mapping-research/vals_index.md`.
