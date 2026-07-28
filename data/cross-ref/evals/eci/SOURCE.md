# Epoch ECI Source Note

Snapshot file: `data/cross-ref/evals/eci/epoch_eci_jul_2026.csv`

Access date for supporting sources: 2026-07-28.

This snapshot is a refresh of the overall (composite) Epoch ECI leaderboard taken from
`https://epoch.ai/data/eci_scores.csv` on 2026-07-28 (213 models). It supersedes the prior
`epoch_eci_may_2026.csv` (178 models): Epoch added 38 models and dropped 3 since that snapshot.
Rows are kept in upstream order, which is descending ECI.

Schema transform from the live CSV, which publishes `Model`, `Display name`, `eci`, `eci_ci_low`,
`eci_ci_high`, `date`, and organization/accessibility columns:

- `Model` is the upstream `Model` column. It is identical to `Display name` on every row of this
  snapshot, and it has no duplicates.
- `Score` is `eci` rounded half-up to an integer; the `90% CI` bounds are `eci_ci_low` and
  `eci_ci_high` rounded the same way and rendered as `(low - high)`. Rounding matches the website
  display and the prior snapshot schema. Half-up rather than banker's rounding changes exactly three
  cells in this snapshot (`Qwen-1_8B` score, `Claude Fable 5` and `GPT-4.5` CI lows), none of which
  is a mapped row's score.
- Every rounded `Score` falls inside its own rounded CI, and the published anchors hold:
  `Claude 3.5 Sonnet` = 130, `GPT-5` = 150.
- Upstream now publishes no CI for those two anchor rows, so their `90% CI` cells are empty. The
  adapter parses an empty cell to a null CI and excludes it from the numeric parse rate, so both
  rates stay 1.0. The CI columns feed no statistic.
- The `llm_chess_model` snapshot bridge column is historical seed data and was carried over by label
  for retained models only (88 of the prior 89 values; the dropped `Gemini 1.5 Pro (Feb 2024)` row
  held the 89th). `mappings/eci.csv` is the live mapping source of truth.

Row-set delta: 175 of the 178 prior models are retained. Epoch dropped `DeepSeek-V3.1`,
`Gemini 1.5 Pro (Feb 2024)`, and `Kimi K2 (Sep 2025)`. The 38 additions are a mix of new frontier
releases (the GPT-5.6 Sol/Terra/Luna trio, Claude Fable 5, Claude Opus 5, Claude Sonnet 5, Claude
Opus 4.8, Grok 4.5, Grok 4.3 Beta, Kimi K3, Kimi K2.7 Code, GLM-5.2, DeepSeek-V4-Pro, MiniMax-M3,
MiniMax-M2.7, Qwen3.7-Max, Qwen 3.6 35B-A3B, Gemma 4 31B IT, Gemini 3.1 Flash-Lite, Mistral Small
3.1) and a backfill of older open-weight and pre-2024 models (PaLM 2-L/M/S, the Qwen2.5-Coder and
CodeQwen families, `DeepSeek-Coder-V2-Lite-Base`, `internlm-7b`/`internlm-20b`, `Yi-9B`,
`chatglm2-6b`, `vicuna-13b-v1.1`, `Qwen-1_8B`, `open_llama_7b`, `RedPajama-INCITE-7B-Base`,
`Amazon Nova Pro`, `stablelm-tuned-alpha-7b`).

Because `eval_row_id` is the normalize-time row position, `mappings/eci.csv` was re-keyed: each
retained model's reviewed decision was carried onto its new position by `eval_model_label`, the three
dropped models' rows were removed, and 38 rows were added. No row ends with `mapping_status`
`missing`, which is the check that the carry landed on the right positions.

Mapping reconciliation in this refresh (mapping status is now `accepted` 104, `unmatched` 109):

- **7 of the 38 new models are accepted.** `GPT-5.6 Sol`, `GPT-5.6 Terra`, and `GPT-5.6 Luna` take
  the `-high` tier of their LLM Chess runs; `Claude Opus 4.8`, `Grok 4.3 Beta`, and
  `Gemini 3.1 Flash-Lite` each have exactly one LLM Chess entry. All six resolve through clause 1
  (`assume-highest`), because ECI publishes no reasoning effort on any row. `Amazon Nova Pro` maps to
  `amazon.nova-pro-v1` with no reasoning clause, since neither side has effort tiers; that player has
  33 games but no rated Elo, so the row joins the non-Elo metric sample only.
- **The remaining 31 new models stay `unmatched`**, each with a reason in `open_questions`. They are
  either models LLM Chess has never run (Claude Fable 5, Claude Opus 5, Claude Sonnet 5, Kimi K3,
  DeepSeek-V4-Pro, Grok 4.5, Gemma 4 31B IT, and the pre-2024 backfill) or same-family-different-version
  rows, which are not matches (`GLM-5.2` against `zai.glm-5`, `MiniMax-M2.7`/`M3` against
  `minimax.minimax-m2.5`, `Kimi K2.7 Code` against `kimi-k2.5`, `Qwen3.7-Max` against `qwen-max`,
  `Mistral Small 3.1` against the Mistral Small 3 run, `internlm-7b`/`internlm-20b` against
  `internlm3-8b-instruct`, `Qwen 3.6 35B-A3B` against `qwen3.6-27b@q4_k_s`). The three PaLM 2 rows
  stay unmatched because `chat-bison-32k@002` is a chat-tuned PaLM 2 endpoint whose L/M/S parameter
  tier Google never published.
- **5 inherited rows were revisited**, as the refresh protocol requires. Four were `unmatched` only
  because the legacy bridge column had no value for them, and all four have a counterpart another
  eval's reviewed mapping already uses: `Claude Opus 4.7`→`claude-opus-4-7_adaptive-thinking-high`
  (the explicit hold condition in `mapping-research/eci.md` is now satisfied),
  `DeepSeek-V3.2`→`deepseek-V3.2_non-reasoning`, `Kimi K2 (Jul 2025)`→`kimi-k2-instruct`, and
  `Llama 4 Scout`→`meta.llama4-scout-17b-instruct-v1:0`. The fifth, `Claude Sonnet 4.6`, was
  re-pointed from `claude-sonnet-4-6` to `claude-sonnet-4-6_thinking-high`: clause 1 takes the highest
  tier, and the 2026-07 reasoning-rule pass moved the sibling Claude Opus 4.6 row but missed this one.
- `DeepSeek-V3.2` is a forced substitution and is flagged as one. Clause 1 assumes Epoch ran the
  reasoning mode, but `deepseek-V3.2_non-reasoning` is the only V3.2 entry LLM Chess has, so coverage
  wins while the two efforts disagree. `DeepSeek-V3.2-Exp` stays unmatched as a distinct release.
- Net effect on the mapping: 93 accepted rows carried forward (94 prior, less the dropped
  `Gemini 1.5 Pro (Feb 2024)` row), plus 7 new and 4 revisited, for 104 accepted.

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