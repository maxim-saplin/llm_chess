# BullshitBench Mapping Research

Source snapshot: `evals/bullshit-bench/bullshit_bench_v2_may_2026.csv` (v2 leaderboard, 162
model/reasoning rows, upstream commit `88e06ae`, 2026-05-29). Runtime mapping source of truth:
`mappings/bullshit_bench.csv`. Joins live LLM Chess identity against `data/elo_refined.csv` and
`data/models_metadata.csv`.

## Mapping Rule

BullshitBench labels are `provider/model@reasoning=level`, so every row carries both a model
version and an explicit reasoning level (`none`, `low`, `medium`, `high`, `xhigh`, `max`,
`minimal`, `default`). The mapping follows the same effort-aware convention already used for
ARC-AGI-2, with conservative fallbacks:

1. **Exact effort tier (`accepted`)** — when LLM Chess exposes the matching `-low`/`-medium`/`-high`
   tier for that model version, the BullshitBench level maps straight to it
   (e.g. `openai/gpt-oss-120b@reasoning=low` → `gpt-oss-120b-low`, `openai/o4-mini@reasoning=high`
   → `o4-mini-high`, `openai/gpt-5.4-mini@reasoning=high` → `gpt-5.4-mini-high`).
2. **Reasoning-kind match (`variant-compatible`)** — when the model version exists but the exact
   effort tier does not, the row maps to the available reasoning run with a noted config caveat:
   - `high` → a Claude `_thinking-high`/`_thinking_16000` reasoning run.
   - `none` → the non-reasoning / `-chat` LLM Chess player (e.g. `gpt-5.2@none` → `gpt-5.2-chat`,
     `claude-sonnet-4.6@none` → `claude-sonnet-4-6`).
   - Effort levels with no tier (`xhigh`, `max`, `default`, or a `low`/`high` where only `-medium`
     exists) collapse to the family representative tier (base → `-medium`), and the framework's
     max-dedupe keeps the highest `avg_score` per LLM Chess player.
3. **Name alias (`alias`)** — single-variant models that are the same model under a renamed label
   (e.g. `moonshotai/kimi-k2` → `kimi-k2-instruct`, `meta-llama/llama-4-scout` →
   `meta.llama4-scout-17b-instruct-v1:0`, `x-ai/grok-4.1-fast@high` → `grok-4-1-fast-reasoning`).
4. **`ambiguous`** — model identity is plausible but the configuration gap is real: a preview
   `beta` tag, an unknown thinking budget, or a hosted full-precision model versus a heavily
   quantized local LLM Chess run.
5. **`unmatched`** — no LLM Chess counterpart for that model version, or a `none`/`xhigh`/`max` row
   whose only same-model match would force a non-reasoning↔reasoning or absent-tier collision.

Statuses `accepted`, `alias`, and `variant-compatible` enter analysis; `ambiguous` and `unmatched`
stay visible in coverage only.

## Result Of This Mapping

| Status | Rows |
| --- | ---: |
| accepted | 6 |
| alias | 21 |
| variant-compatible | 39 |
| ambiguous | 6 |
| unmatched | 90 |

66 mapped rows resolve to 58 unique LLM Chess players; the Elo sample is 55 after max-dedupe and
the non-null-Elo requirement.

## Notable Decisions

- **Frontier OpenAI / Gemini reasoning models** (`gpt-5.5`, `gpt-5.4`, `gpt-5.3-codex`, `gpt-5.2`,
  `gpt-5.1`, `gpt-5`, `o3`, `gemini-3-pro-preview`, `gemini-3.1-pro-preview`) appear at reasoning
  levels that do not line up with the LLM Chess tier grid, so they map to the family `-medium`
  representative (or the single available reasoning tier) as `variant-compatible`. This matches how
  ECI already treats these base models. The non-reasoning `none` rows for these families stay
  `unmatched` because there is no non-reasoning / `-chat` counterpart in `elo_refined.csv`.
- **Claude 4.x** maps cleanly on both sides: `none` → the non-reasoning player, `high` → the
  `_thinking` / `_thinking-high` reasoning run. Claude is where the effort dimension is genuinely
  shared between the two sources.
- **`claude-opus-4.8`** has no LLM Chess counterpart yet (newest opus in `elo_refined.csv` is 4.7);
  both rows are `unmatched`.
- **Held `ambiguous`**: `x-ai/grok-4.20-beta` (preview tag plus non-aligning effort levels versus
  the released `grok-4-20-reasoning`), `claude-3.7-sonnet:thinking` (unspecified thinking budget),
  `nvidia/nemotron-3-nano-30b-a3b:free` and `google/gemma-3-27b-it` (hosted full precision versus a
  quantized local LLM Chess run).
- **Long-tail / distinct families** with no LLM Chess entry stay `unmatched`: Xiaomi MiMo, StepFun,
  ByteDance Seed, Baidu ERNIE, AI21 Jamba, Prime Intellect, Arcee, hosted Qwen 3.5/3.6/3.7,
  GLM-5-turbo/5.1/4.5, DeepSeek V4, Gemma 4, Nemotron-3-Super/Nano-9B, GPT-5.5 Pro, GPT-5.x-Codex
  tiers absent from elo, and the `openrouter/*-alpha` stealth rows.

## Caveats Carried Into Analysis

- `avg_score` is one behavioral skill (nonsense detection), not a capability index. In this sample
  the strongest detectors are Claude models at mid-range Elo, while the highest-Elo OpenAI/Gemini
  reasoning models sit mid-pack — which is why the Elo correlation is weak and
  `player_wins_percent` is near zero, unlike ECI and ARC-AGI-2.
- The `variant-compatible` rows collapse reasoning effort onto one LLM Chess tier; treat each as a
  model-level point, not an effort-level point.
