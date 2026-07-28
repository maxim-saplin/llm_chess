# ARC-AGI-2 Mapping Research

Mapping file: `data/cross-ref/mappings/arc_agi_2.csv`

Access date: 2026-07-28 (snapshot `arc-agi-2-jul-2026.csv`, upstream data `last-modified: 2026-07-24`).

## Run-Time Source Of Truth

- `data/cross-ref/run_cross_ref.py arc_agi_2` uses `data/cross-ref/mappings/arc_agi_2.csv` directly.
- The mapping CSV is the live run-time source of truth for ARC cross-reference runs.
- The notes in this file explain how the CSV was built and why some rows remain unresolved. They do not override the mapping CSV that the runner actually loads.

## Sources Used

- Leaderboard: <https://arcprize.org/leaderboard>
- Leaderboard data files (the canonical machine-readable source since the 2026-07 refresh): <https://arcprize.org/media/data/evaluations.json>, <https://arcprize.org/media/data/models.json>, <https://arcprize.org/media/data/datasets.json>, <https://arcprize.org/media/data/providers.json>
- ARC-AGI-2 page: <https://arcprize.org/arc-agi/2>
- ARC announcement / methodology framing: <https://arcprize.org/blog/announcing-arc-agi-2-and-arc-prize-2025>
- ARC policy page: <https://arcprize.org/policy>
- LLM Chess inventory: `data/cross-ref/model-identity/llm_chess_models.csv`

## Decision Rules Applied

- Exact family, tier, version, and config matches are preferred.
- `alias` is used when the benchmark row and the LLM Chess row are the same model/config with only a surface-name difference.
- `variant-compatible` is used when the same model family is clear but the benchmark row adds a config axis that is not encoded the same way in the LLM Chess player ID. Nearest-tier effort substitutions land here.
- `ambiguous` is used when multiple plausible LLM Chess rows exist or when the benchmark row introduces a distinct *identity* axis such as `Pro`, `Refine.`, `Deep Think`, token budgets, preview variants, or context-window variants.
- `unmatched` is used when the family or version is absent from the current LLM Chess inventory.
- `excluded` is used for human baselines and benchmark-system rows that should not be treated as one model identity.

Reasoning effort is **not** an identity axis and never grounds a hold on its own. It resolves coverage-first by the direction-aware nearest-tier rule in [../README.md](../README.md) ("Stage Ownership"): unstated effort assumes the highest tier (`assume-highest`), a stated effort that exists in LLM Chess wins exactly, and a stated effort with no LLM Chess tier takes the nearest available tier in the same direction (`nearest-tier`). Rows resolved by the first or third clause name the clause in `reasoning_rule_applied`. A missing `xHigh`, `Max`, or `Minimal` tier is therefore a substitution to record, not a reason to leave the row out of the sample; a missing `Pro` product tier still is.

## High-Impact Outcomes

- `elo_refined.csv` carries GPT-5.5 as `-medium` and `-high`, GPT-5.4 Mini as `-low` and `-high`, Gemini 3.5 Flash as `-medium` only, and Claude Opus 4.7/4.8 only as `_adaptive-thinking-high`. The ARC tier labels do not line up one-to-one with that inventory, so several rows resolve by substitution rather than by exact match:
  - `GPT-5.5 (High)` → `gpt-5.5-high` and `GPT-5.5 (Medium)` → `gpt-5.5-medium` (`accepted`, exact tier ids).
  - `GPT-5.5 (Low)` → `gpt-5.5-medium` (`nearest-tier`; no `gpt-5.5-low` exists, so the lowest available tier is used and the row is never promoted to `-high`).
  - `GPT-5.5 (xHigh)` → `gpt-5.5-high` (`nearest-tier`; highest available).
  - `GPT-5.4 Mini (Low)` → `gpt-5.4-mini-low` (exact); `GPT-5.4 Mini (Medium)` → `gpt-5.4-mini-high` (`nearest-tier`, equidistant tiebreak resolved upward by convention, not by evidence).
  - `Gemini 3.5 Flash (Minimal/High)` → `gemini-3.5-flash-medium` (`variant-compatible`, `nearest-tier`). `-medium` is the only tier, so the Minimal row is a forced upward inversion; both rows record the effort conflict in `open_questions`.
  - `Claude 4.7 (High)` → `claude-opus-4-7_adaptive-thinking-high` (`variant-compatible`; family/effort clear, ARC label omits the Opus tier and the adaptive-thinking suffix). Confirmed Opus by the sibling `Opus 4.7 (High)` ARC-AGI-3 row.
  - `GPT-5.2 (High)`, `GPT-5.1 (Thinking, High)`, `GPT-5 (High)`, and `o3 (High)` → the `-medium` tier of each family (`nearest-tier`). None of those families has a `-high` run in `elo_refined.csv`, so High is compared against `-medium` and each row says so in `open_questions`.
- `Pro` rows stay unresolved on the product axis, not the effort axis: `GPT-5.5 Pro (High/xHigh)`, `GPT-5.4 Pro (xHigh)`, `GPT-5.2 Pro (High/Medium)`, `GPT-5 Pro`, and the `o3-Pro` tiers have no Pro counterpart in LLM Chess.
- `Claude 4.7 (Low/Medium/Max)` remain `unmatched` even though `claude-opus-4-7_adaptive-thinking-high` exists. Under the current reasoning-effort rule these are nearest-tier candidates rather than genuine identity gaps; see "Open Rule Application Gap" below.
- `GPT-5.5 (High)` and `Opus 4.7 (High)` also appear as ARC-AGI-3 entries that carry no ARC-AGI-2 score, so they map to their LLM Chess players but stay out of the ARC-AGI-2 sample.
- Gemini 3.1 Pro (Preview) maps to `gemini-3.1-pro-preview-high` and Gemini 3 Pro to `gemini-3-pro-preview-high` (`assume-highest`; both LLM Chess players were renamed to carry an explicit `-high` tier, and the ARC labels state no effort). Grok 4.20 (Reasoning), GLM-5, Kimi K2.5, Minimax M2.5, GPT-5.4 tier rows, o4-mini tier rows, and several legacy-model rows map cleanly.
- Gemini `Deep Think`, GPT `Pro`, ARC `Refine.`, Claude 4.6 `120K`, Llama 4 Scout (three candidate inventory rows), and many token-budget rows remain `ambiguous` on purpose. `xHigh` no longer belongs on this list: it is an effort label, so it resolves by `nearest-tier` instead of holding the row.
- Human and system baselines such as `Human Panel`, `Avg. Mturker`, `Stem Grad`, `NVARC`, `ARChitects`, `Icecuber`, `TRM`, and `HRM` are preserved but `excluded` from model matching.

## 2026-07 Refresh Additions

The refresh to `arc-agi-2-jul-2026.csv` retained all 161 prior rows and added 26. The mapping was
re-keyed by matching each retained row to its new position on `(AI SYSTEM, AUTHOR, DATE, ARC-AGI-1,
ARC-AGI-2, ARC-AGI-3)`; every reviewed decision carried over and no row resolved to
`mapping_status = missing`. Inherited decisions were **not** re-litigated: no new LLM Chess model
appeared in `elo_refined.csv` between the two snapshots, so nothing triggered the "revisit inherited
mappings" clause. The rows listed under "Open Rule Application Gap" below are unchanged.

The 26 new rows resolve as follows (`reviewer = cross_ref_refresh_jul_2026`,
`review_status = reviewed_2026_07_arc_refresh`):

- **GPT-5.6 Sol / Terra / Luna, five ARC tiers each (15 rows).** `elo_refined.csv` carries
  `-medium` and `-high` for all three. `(Medium)` and `(High)` are exact tier matches (`accepted`,
  `effort_to_effort`). `(Low)` takes `-medium` and `(xHigh)`/`(Max)` take `-high`
  (`variant-compatible`, `nearest-tier`); each records the effort conflict in `open_questions`.
  Sol's `(High)`, `(xHigh)`, and `(Max)` rows share one player, so max dedupe keeps the highest
  ARC-AGI-2 score among them — `Max` at `92.5`, not `High` at `85.4`. The same holds for Terra and
  Luna. This is the documented coverage-first consequence, not an effort-matched comparison.
- **Claude Opus 4.8, four ARC tiers (4 rows).** `claude-opus-4-8_adaptive-thinking-high` is the only
  Opus 4.8 run. `(High)` is an exact effort match (`accepted`, `effort_to_effort`); `(Low)`,
  `(Medium)`, and `(Max)` are single-candidate clause-3 substitutions (`variant-compatible`,
  `nearest-tier`), with `(Low)` and `(Medium)` recorded as forced upward inversions. `(Max)` has no
  ARC-AGI-2 score, so it never reaches the sample. Matches the `eci` and `bullshit_bench` treatment
  of the same model.
- **`Claude Opus 5 (High)` and `(Max)`** stay `unmatched`: LLM Chess has run no Opus 5. `eci` and
  `vals_index` hold the same model unmatched.
- **`Grok 4.5 (Low/Medium/High)`** stay `unmatched`: `grok-4.3-high` and the `grok-4-20` entries are
  different releases, not tiers of 4.5. `vals_index` holds `grok/grok-4.5` unmatched on the same
  grounds.
- **`GLM-5.2`** stays `unmatched` against `zai.glm-5`, a same-family-different-version row, matching
  `eci` and `vals_index`.
- **`Inkling`** (Thinking Machines) stays `unmatched`: no counterpart anywhere in `elo_refined.csv`.

Net effect: 19 of the 26 new rows resolve to a player, adding 7 unique LLM Chess players to the Elo
sample — the `-high` and `-medium` tiers of Sol, Terra, and Luna, plus
`claude-opus-4-8_adaptive-thinking-high`.

## Current Status Mix

Generated from the current mapping CSV (`arc-agi-2-jul-2026.csv`, 187 rows):

- `accepted`: 22
- `alias`: 46
- `variant-compatible`: 30
- `ambiguous`: 54
- `unmatched`: 27
- `excluded`: 8

## Review Notes

- The mapping intentionally leaves many rows unresolved rather than inflating the matched sample.
- Preview, beta, reasoning-budget, and context-window variants should stay unresolved until stronger evidence exists.
- The mapping CSV is the current published source of truth used by the shared runner for ARC cross-reference runs.

## Mapping Priority Queue (2026-07-27)

This queue is keyed by `eval_model_label`, not by `eval_row_id`. **Do not re-key it to `eval_row_id`.** That id embeds the normalize-time row position, so an upstream refresh silently repoints every entry: the 2026-05-13 edition of this queue was written against the pre-2026-05-29 row order, and after the refresh 20 of its 21 cited ids resolved to a different model — several to rows that were by then `accepted`. Model labels survive a reordering; positions do not.

Ranked by ARC-AGI-2 score among rows that are still `ambiguous` or `unmatched` (81 of 187 rows after the 2026-07 refresh). Scores are from `arc-agi-2-jul-2026.csv`. The refresh added seven entries to this queue — `Claude Opus 5 (High)` (`88.3`) and `(Max)` (`90.4`), the three `Grok 4.5` tiers, `GLM-5.2`, and `Inkling` — all of them absent-family holds rather than rule-application gaps.

1. `Pro` product axis, highest-scoring unresolved group: `GPT-5.5 Pro (High)` (`84.6`), `GPT-5.5 Pro (xHigh)` (`84.2`), `GPT-5.4 Pro (xHigh)` (`83.3`), `GPT-5.2 Pro (High)` (`54.2`), `GPT-5.2 Pro (Medium)` (`38.5`), `GPT-5 Pro`, and the three `o3-Pro` tiers. LLM Chess has no Pro run for any GPT family, so these are genuine identity gaps rather than effort gaps. ECI carries the same unresolved Pro rows. Do not collapse them onto the plain or tiered GPT players.
2. Gemini `Deep Think`: `Gemini 3 Deep Think (2/26)` (`84.6`) and `Gemini 3 Deep Think (Preview) ²` (`45.1`). Deep Think is a separate reasoning *setup*, not an effort tier on the Gemini 3 Pro ladder, so the nearest-tier rule does not reach it.
3. ARC `Refine.` benchmark systems: `GPT-5.2 (Refine.)` (`72.9`), `Gemini 3 Pro (Refine.)` (`54.0`), and the two `Grok 4 (Refine.)` rows. `Refine.` is a benchmark harness rather than a model identity. The two Grok rows share a label and are distinguished only by `AUTHOR` (`J. Berman` and `E. Pang`), which is mirrored in `provider_or_family`.
4. Claude Opus 4.6 `120K` context variants: `(120K, High)` (`69.2`), `(120K, Max)` (`68.8`), `(120K, Medium)` (`66.3`), `(120K, Low)` (`64.6`). The context-window axis is not represented in LLM Chess and is an identity axis, not an effort axis.
5. Reasoning-budget rows: the `Gemini 2.5 Pro`/`Gemini 2.5 Flash` `Thinking 1K/8K/16K/24K/32K` rows and `Opus 4.5 (Thinking, 64K)` (`37.6`). Token budgets are not on the minimal/low/medium/high/xhigh/max ladder, so direction-aware substitution has no defined direction for them. Deciding whether a budget maps onto a named tier needs source evidence and is the main remaining methodology question here.
6. Under-specified base labels: `GPT-5.2` and `Codex Mini (Latest)` stay `ambiguous` because the label does not say which chat/tiered/codex LLM Chess row is meant. This is a label-resolution problem, not an effort problem.
7. Absent families: `Magistral Medium (Thinking)` has no reasoning counterpart in LLM Chess, and `Grok 4 (Thinking)` does not say whether it is the fast or 4.20 reasoning variant.
8. Human and system baselines (`Human Panel`, `Avg. Mturker`, `Stem Grad`, `NVARC`, `ARChitects`, `Icecuber`, `TRM`, `HRM`) stay `excluded` and are not model-mapping candidates.

## Open Rule Application Gap

The 2026-07-27 pass applied the reasoning-effort rule to every row whose mapped target was wrong or dangling, and to the rows whose `unmatched` rationale had become factually false. It did **not** sweep every row the rule could newly reach. These rows are still `unmatched` for a missing effort tier alone, which the current rule treats as a substitution rather than a hold, and their family is present in `elo_refined.csv`:

- `Claude 4.7 (Low)`, `(Medium)`, `(Max)` → `claude-opus-4-7_adaptive-thinking-high` is the only Opus 4.7 run; `Claude 4.7 (High)` already maps to it.
- `GPT-5.4 Mini (xHigh)` → `gpt-5.4-mini-high`; `GPT-5.4 Nano (xHigh/Medium/Low)` → `gpt-5.4-nano-high` (its only tier).
- `GPT-5.2 (xHigh)` → `gpt-5.2-medium`.
- `GPT-5 (Minimal)` → `gpt-5-low`; `GPT-5 Mini (Minimal)` → `gpt-5-mini-low`; `GPT-5 Nano (Minimal)` → `gpt-5-nano-low`.

Each would be a `variant-compatible` `nearest-tier` row. Where only one tier exists the substitution is forced and inverts the stated effort upward: `Claude 4.7 (Low)` and `(Medium)` onto `-high`, and `GPT-5.4 Nano (Medium)` and `(Low)` onto `-high`. Resolving these is a coverage decision for the maintainer, not a data question.