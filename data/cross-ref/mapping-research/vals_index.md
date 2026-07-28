# Vals Index Mapping Research

Mapping CSV: `data/cross-ref/mappings/vals_index.csv`
Snapshot: `data/cross-ref/evals/vals-index/vals_index_v1_2_july_2026.csv` (40 rows, v1.2, 2026-07-23)
Reviewed: 2026-07 (`reviewer = cross_ref_vals_index_2026_07`)

## Join Key

The mapping joins on `eval_model_label` = the snapshot's `model_key`, the upstream `provider/slug`
identity (e.g. `openai/gpt-5.6-sol`). The Vals payload has **no display-name field**, so there is no
display name to map from and none is used — see `evals/vals-index/SOURCE.md`. This is the same
`provider/slug` shape BullshitBench already uses, so the two mappings read alike.

`eval_row_id` embeds the normalize-time row position, and the snapshot is sorted by `vals_index`
descending, so **re-key the mapping whenever the row set or sort order changes.**

## Outcome

| | Rows |
| --- | ---: |
| Total snapshot rows | 40 |
| Matched (in statistics) | **17** |
| — `accepted` | 4 |
| — `alias` | 1 |
| — `variant-compatible` | 12 |
| `unmatched` | 23 |

All 17 matched targets were verified to exist in `data/elo_refined.csv` with a non-null Elo, so
`run_cross_ref.py verify` reports `mapping_player_resolution: pass` with 0 dangling and 0
metadata-only rows. The funnel is lossless after mapping: 17 accepted → 17 metric rows → 17 Elo rows,
with 0 duplicate mapping keys and 0 duplicate joined players.

## Reasoning Effort — why this eval leans on clause 3

Vals states a per-row effort tier for 24 of 40 rows (in `reasoning_effort`, or `compute_effort` for
Anthropic). That is stronger tier evidence than any other cross-ref eval carries. It does **not**
translate into more exact matches, because Vals' tier vocabulary runs *above* LLM Chess's: Vals uses
`max` and `xhigh`, and **LLM Chess has neither tier for any model.** So the better evidence mostly
routes rows into clause 3 (`nearest-tier`, substituting upward) rather than clause 2.

Applied clauses across the 17 matched rows:

| Clause | `reasoning_rule_applied` | Rows |
| --- | --- | ---: |
| 3 — stated effort absent from LLM Chess, substitute in the same direction | `nearest-tier` | 10 |
| 2 — exact effort match | `effort_to_effort` | 5 |
| 1 — effort unstated, assume the highest | `assume-highest` | 2 |

### Clause 3, upward substitution (7 rows)

`max` or `xhigh` stated, no such tier in LLM Chess, so the highest available tier is taken:

| `model_key` | stated | → `llm_chess_player` |
| --- | --- | --- |
| `openai/gpt-5.6-sol` | `max` | `gpt-5.6-sol-2026-07-09-high` |
| `openai/gpt-5.6-luna` | `max` | `gpt-5.6-luna-2026-07-09-high` |
| `openai/gpt-5.6-terra` | `xhigh` | `gpt-5.6-terra-2026-07-09-high` |
| `openai/gpt-5.5` | `xhigh` | `gpt-5.5-high` |
| `openai/gpt-5.4-mini-2026-03-17` | `xhigh` | `gpt-5.4-mini-high` |
| `anthropic/claude-opus-4-8` | `max` (compute) | `claude-opus-4-8_adaptive-thinking-high` |
| `anthropic/claude-sonnet-4-6` | `max` (compute) | `claude-sonnet-4-6_thinking-high` |

Each of the first five had a real choice — `-high` and `-medium` (or `-low`) both exist — and
direction sends them to `-high`. The two Anthropic rows had one candidate each.

`anthropic/claude-sonnet-4-6` is the one row where the *variant*, not just the tier, had to be
decided: LLM Chess has both `claude-sonnet-4-6` (non-thinking) and `claude-sonnet-4-6_thinking-high`.
The Vals row sets `reasoning: True`, so it is the thinking configuration and maps to the thinking run.
Without that field the row would have been ambiguous.

### Clause 3, forced substitution against the stated direction (3 rows)

These are the rows where coverage wins but the mapping must **not** be read as the two efforts
agreeing. Each has its conflict recorded in `open_questions`:

- `google/gemini-3.5-flash` states `high`, and `gemini-3.5-flash-medium` is the **only** LLM Chess
  tier. Direction-aware substitution has a single candidate, so a high-effort external row maps to a
  medium-effort chess run. This is the same forced outcome README documents for
  `google/gemini-3-pro-preview@reasoning=low` in BullshitBench, inverted.
- `google/gemini-3-flash-preview` and `google/gemini-3.1-flash-lite-preview` both state `high`, and
  their single LLM Chess runs carry **no effort suffix at all**, so the chess-side thinking budget is
  unrecorded and cannot be checked against `high`.

### Clause 2, exact match (5 rows)

`google/gemini-3.6-flash` → `gemini-3.6-flash-high`, `google/gemini-3.1-pro-preview` →
`gemini-3.1-pro-preview-high`, `openai/gpt-5.4-nano-2026-03-17` → `gpt-5.4-nano-high`,
`grok/grok-4.3` → `grok-4.3-high` — all `high` → `-high`, all `accepted`.

`anthropic/claude-opus-4-7` also matches on effort (`compute_effort=high` →
`..._adaptive-thinking-high`) but is held at `variant-compatible`: the effort agrees while the
thinking *mode* is labelled differently on the two sides (Vals `compute_effort` vs LLM Chess
`adaptive-thinking`), which is a variant difference, not an exact identity.

### Clause 1, effort unstated (2 rows)

- `grok/grok-4.20-0309-reasoning` → `grok-4-20-reasoning`. Status **`alias`**: same model under
  different punctuation, and both names state the reasoning variant explicitly. No effort stated, so
  clause 1 assumes the highest — which is the only reasoning run LLM Chess has.
- `anthropic/claude-haiku-4-5-20251001-thinking` → `claude-haiku-4-5_thinking_16000`. The `-thinking`
  suffix picks the thinking run over plain `claude-haiku-4-5`. LLM Chess expresses this run as a
  16000-token budget rather than a tier, and Vals states no budget, so the two configurations cannot
  be checked against each other.

## Status Choice

`mapping_status` was chosen on the evidence rather than defaulted:

- **`accepted` (4)** — same model, exact stated-effort match, no variant question.
- **`alias` (1)** — same model, different name spelling, no tier substitution.
- **`variant-compatible` (12)** — the tier or the variant had to be substituted or assumed: 10
  clause-3 rows, `claude-opus-4-7` (mode labelled differently), and `claude-haiku-4-5_thinking_16000`
  (budget vs tier).

## Unmatched — 23 rows, two rationale groups

### A. No LLM Chess counterpart at any version (13 rows)

`anthropic/claude-fable-5`, `anthropic/claude-opus-5`, `anthropic/claude-sonnet-5`, `grok/grok-4.5`,
`deepseek/deepseek-v4-pro`, `meta/muse_spark_1_1`, `thinkingmachines/inkling`, `poolside/laguna-m.1`,
`poolside/laguna-xs.2`, `xiaomi/mimo-v2.5`, `xiaomi/mimo-v2.5-pro`, `mistralai/mistral-medium-3.5`,
`google/gemini-3.5-flash-lite`.

Nothing to map — the model has never been run in LLM Chess. These stay visible in coverage and out of
every statistic.

**This group costs the comparison its top end.** The three highest-scoring rows upstream —
`claude-fable-5` (75.145), `claude-opus-5` (74.820) and `kimi/kimi-k3` (74.700, group B) — are all
unmatched, so the correlation is computed over a narrower score range than the leaderboard spans.

`mistralai/mistral-medium-3.5` deserves its own line: LLM Chess holds `mistral-nemo-12b-instruct` and
`mistral-small-*`, which are different *models*, not other versions of Mistral Medium. Same vendor is
not same model.

### B. Same family, different version (10 rows)

Deliberately unmatched on the identity rule, **not** a coverage gap to be closed later:

| `model_key` | Nearest LLM Chess sibling | Why not a match |
| --- | --- | --- |
| `kimi/kimi-k3` | `kimi-k2.5`, `kimi-k2-instruct` | Different generation. |
| `kimi/kimi-k2.6` | `kimi-k2.5` | Adjacent minor versions are still different models. |
| `zai/glm-5.2` | `zai.glm-5` | Chess name carries no minor version. |
| `zai/glm-5.1` | `zai.glm-5` | Same — and `zai.glm-5` cannot be shown to be either 5.1 or 5.2. |
| `alibaba/qwen3.7-max` | `qwen-max` | Chess name is unversioned. |
| `alibaba/qwen3.7-plus` | `qwen-plus` | Chess name is unversioned. |
| `alibaba/qwen3.6-plus` | `qwen-plus` | Same — two Vals versions compete for one unversioned row. |
| `minimax/MiniMax-M3` | `minimax.minimax-m2.5` etc. | Different generation. |
| `minimax/MiniMax-M2.7` | `minimax.minimax-m2.5` | Adjacent minor versions. |
| `nvidia/nemotron-3-ultra-550b-a55b` | `nemotron-3-nano@q3_k_l` | Different size class **and** a local q3_k_l quant: two differences at once. |

The unversioned-target rows (`zai.glm-5`, `qwen-max`, `qwen-plus`) are the instructive ones. Each is a
name that *could* absorb any of two or three Vals rows, which is exactly why it absorbs none: mapping
`qwen3.7-plus` and `qwen3.6-plus` both onto `qwen-plus` would invent a duplicate and let dedupe pick a
winner arbitrarily. These are held as `unmatched` rather than `ambiguous` because the target's version
is genuinely unrecorded, not merely unclear from this eval's side.

## Indicative Correlation — not a finding

On the 17 matched rows, `vals_index` against LLM Chess Elo gives **Spearman 0.669 / Pearson 0.622**
(bootstrap 95% Pearson ≈ 0.26–0.87). Re-pointing the four `gpt-5.6-*`/`gpt-5.5` rows at their
`-medium` counterparts instead gives Spearman 0.601, so the `-high`-leaning mapping this rule produces
is the higher of the two — as expected, since substituting `max`/`xhigh` upward is what clause 3
requires.

**Do not present this as a result.** n=17 is small, comparable to DELEGATE-52's 14 where one row moved
the correlation from 0.381 to 0.207, and the sample is truncated at its high end (above). The interval
is wide enough that the point estimate alone says little.

## Evidence Refs

- `vals_index_v1_2_payload` — the extracted `.benchmarkView.tasks.overall` blob; procedure and
  verification in `evals/vals-index/SOURCE.md`.
- `elo_refined.csv`, `models_metadata.csv` — LLM Chess target inventory.
- `reasoning_effort_rule:README.md#stage-ownership` — the three-clause rule, cited on every row
  resolved by a clause.
