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
2. **Nearest available tier (`variant-compatible`)** — when the model version exists but the exact
   effort tier does not, the row maps to the nearest available tier *in the same direction*, per the
   rule in [../README.md](../README.md) ("Stage Ownership"), with the conflict noted in
   `open_questions`:
   - `high` → a Claude `_thinking-high`/`_thinking_16000` reasoning run.
   - `none` → the non-reasoning / `-chat` LLM Chess player (e.g. `gpt-5.2@none` → `gpt-5.2-chat`,
     `claude-sonnet-4.6@none` → `claude-sonnet-4-6`).
   - `xhigh` and `max` take the **highest** available tier, so `gpt-5.5@xhigh` → `gpt-5.5-high` and
     `gpt-5.4@xhigh` → `gpt-5.4-high`. They no longer collapse onto a `-medium` family
     representative; that convention is retired.
   - `low` and `minimal` take the **lowest** available tier, so `gpt-5.5@low` → `gpt-5.5-medium` and
     is never promoted to `-high`.
   - Where a model has only one tier, direction has a single candidate and the substitution is
     forced: `gemini-3-pro-preview@low` and `gemini-3.1-pro-preview@low` resolve to the `-high`
     players, inverting the stated effort. Those rows say so explicitly rather than implying the
     efforts agree.
   - The framework's max-dedupe keeps the highest `avg_score` per LLM Chess player when several
     rows land on one.
3. **Name alias (`alias`)** — single-variant models that are the same model under a renamed label
   (e.g. `moonshotai/kimi-k2` → `kimi-k2-instruct`, `meta-llama/llama-4-scout` →
   `meta.llama4-scout-17b-instruct-v1:0`, `x-ai/grok-4.1-fast@high` → `grok-4-1-fast-reasoning`).
4. **`ambiguous`** — model identity is plausible but the configuration gap is real: a preview
   `beta` tag, an unknown thinking budget, or a hosted full-precision model versus a heavily
   quantized local LLM Chess run.
5. **`unmatched`** — no LLM Chess counterpart for that model version at any tier. An absent effort
   tier on its own is **not** grounds to leave a row unmatched; it is a substitution to record. But
   a `none` row stays unmatched whenever the only same-model candidate is a reasoning run:
   `reasoning=none` is a reasoning-**kind** difference, and the nearest-tier rule governs effort
   only. Crossing the kind boundary would change which model is being compared, so
   `claude-opus-4.7@none` and `claude-opus-4.8@none` are both held even though a `_thinking`/
   `_adaptive-thinking` run of each exists.

Statuses `accepted`, `alias`, and `variant-compatible` enter analysis; `ambiguous` and `unmatched`
stay visible in coverage only.

## Result Of This Mapping

| Status | Rows |
| --- | ---: |
| accepted | 6 |
| alias | 21 |
| variant-compatible | 44 |
| ambiguous | 6 |
| unmatched | 85 |

71 mapped rows resolve to 62 unique LLM Chess players; the Elo sample is 59 after max-dedupe and
the non-null-Elo requirement.

## Notable Decisions

- **Frontier OpenAI / Gemini reasoning models** (`gpt-5.5`, `gpt-5.4`, `gpt-5.3-codex`, `gpt-5.2`,
  `gpt-5.1`, `gpt-5`, `o3`, `gemini-3-pro-preview`, `gemini-3.1-pro-preview`) appear at reasoning
  levels that do not line up with the LLM Chess tier grid, so each row takes the nearest available
  tier in the direction its stated effort points, as `variant-compatible`. `xhigh` rows go up
  (`gpt-5.5@xhigh` → `gpt-5.5-high`, `gpt-5.4@xhigh` → `gpt-5.4-high`), `low` rows go down
  (`gpt-5.5@low` → `gpt-5.5-medium`), and the single-tier Gemini previews absorb both directions
  into `-high`. The non-reasoning `none` rows for these families stay `unmatched` because there is
  no non-reasoning / `-chat` counterpart in `elo_refined.csv`.
- **Claude 4.x** maps cleanly on both sides: `none` → the non-reasoning player, `high` → the
  `_thinking` / `_thinking-high` reasoning run. Claude is where the effort dimension is genuinely
  shared between the two sources.
- **`claude-opus-4.8`** splits by reasoning kind. `claude-opus-4-8_adaptive-thinking-high` entered
  `elo_refined.csv` under that name (renamed from `anthropic.claude-opus-4-8` in commit `108a9567`),
  so the `@reasoning=xhigh` row maps to it as `variant-compatible`: two reasoning runs whose effort
  labels differ, which is what the nearest-tier rule is for. The `@reasoning=none` row stays
  `unmatched`. Opus 4.8 has no non-reasoning LLM Chess run, and substituting a thinking run for a
  non-reasoning one is a kind change rather than an effort change — the same call already made for
  `claude-opus-4.7@reasoning=none`. Every other mapped `none` row in this file targets a genuine
  non-reasoning player.
- **`grok-4.3`** now maps to `grok-4.3-high` for both the `minimal` and `xhigh` rows. `-high` is the
  only Grok 4.3 tier, so the `minimal` row is a forced upward inversion.
- **`gemini-3.5-flash`** now maps to `gemini-3.5-flash-medium` for both the `xhigh` and `minimal`
  rows, `-medium` being the only tier; the `minimal` row is again a forced inversion.
- **Held `ambiguous`**: `x-ai/grok-4.20-beta` (preview tag plus non-aligning effort levels versus
  the released `grok-4-20-reasoning`), `claude-3.7-sonnet:thinking` (unspecified thinking budget),
  `nvidia/nemotron-3-nano-30b-a3b:free` and `google/gemma-3-27b-it` (hosted full precision versus a
  quantized local LLM Chess run).
- **Long-tail / distinct families** with no LLM Chess entry at any tier stay `unmatched`: Xiaomi
  MiMo, StepFun, ByteDance Seed, Baidu ERNIE, AI21 Jamba, Prime Intellect, Arcee, hosted Qwen
  3.5/3.6/3.7, GLM-5-turbo/5.1/4.5, DeepSeek V4, Gemma 4, Nemotron-3-Super/Nano-9B, `gpt-5.5-pro`,
  `gpt-5.5-chat`, the `gpt-5-codex` and `gpt-5.2-codex` families, and the `openrouter/*-alpha`
  stealth rows. These are family absences, not tier absences — `gpt-5.1-codex` and `gpt-5.3-codex`
  do exist in `elo_refined.csv` and their rows map by nearest tier.

## Caveats Carried Into Analysis

- `avg_score` is one behavioral skill (nonsense detection), not a capability index. In this sample
  the strongest detectors are Claude models at mid-range Elo, while the highest-Elo OpenAI/Gemini
  reasoning models sit mid-pack — which is why the Elo correlation is weak and
  `player_wins_percent` is near zero, unlike ECI and ARC-AGI-2.
- The `variant-compatible` rows collapse reasoning effort onto one LLM Chess tier; treat each as a
  model-level point, not an effort-level point.
