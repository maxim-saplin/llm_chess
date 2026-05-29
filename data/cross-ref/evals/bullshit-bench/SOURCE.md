# BullshitBench Source Note

Snapshot file: `data/cross-ref/evals/bullshit-bench/bullshit_bench_v2_may_2026.csv`

Access date for supporting sources: 2026-05-29.

This snapshot is the published v2 leaderboard from the BullshitBench project, copied byte-for-byte
from `data/v2/latest/leaderboard.csv` in `petergpt/bullshit-benchmark` at upstream commit
`88e06aeb2e5c746c86bdb5cd351076c86877173b` ("Publish Claude Opus 4.8 benchmark results",
2026-05-29). The upstream leaderboard manifest reports it was generated at `2026-05-29T09:12:42Z`
from completed 3-judge panels over 16,200 aggregate rows (162 model/reasoning rows × 100 prompts).

## Canonical Machine-Readable URL

For the next refresh start from the raw published v2 leaderboard:
`https://raw.githubusercontent.com/petergpt/bullshit-benchmark/main/data/v2/latest/leaderboard.csv`

The project also publishes a v1 leaderboard at `data/latest/leaderboard.csv` (55 prompts). v2 (100
prompts across five domains) supersedes v1 and is the snapshot frozen here. Keep the v2 leaderboard
as the cross-ref source unless the maintainer chooses to track v1 separately.

## Benchmark Definition

- BullshitBench measures whether a model detects nonsense premises, calls them out clearly, and
  avoids confidently continuing with invalid assumptions.
- v2 uses 100 nonsense prompts across five domains: Software (40), Finance (15), Legal (15),
  Medical (15), Physics (15), built from 13 nonsense techniques.
- Each response is judged by a 3-judge panel (Claude Sonnet, GPT-5.2, Gemini 3.1 Pro) and the
  per-prompt scores are mean-aggregated.

## Local Snapshot

- Local file columns: `rank`, `model`, `org`, `reasoning`, `avg_score`, `green_rate`, `red_rate`,
  `score_2`, `score_1`, `score_0`, `nonsense_count`, `error_count`.
- `model` is an OpenRouter-style slug with an explicit reasoning suffix, e.g.
  `anthropic/claude-opus-4.8@reasoning=none`. The `reasoning` column repeats the suffix level
  (`none`, `low`, `medium`, `high`, `xhigh`, `max`, `minimal`, `default`).
- Each row is one model run at one reasoning level. The same base model can appear several times at
  different reasoning levels.

## Score Meaning

- `avg_score` is the cross-ref target. It is the mean of per-prompt judge scores on a 0-2 scale:
  - `2` = Clear Pushback (the model clearly rejects the broken premise),
  - `1` = Partial Challenge (the model flags issues but still engages the bad premise),
  - `0` = Accepted Nonsense (the model treats the nonsense as valid).
- Higher `avg_score` means better nonsense detection.
- `green_rate` is the share of prompts scored 2 (Clear Pushback); `red_rate` is the share scored 0
  (Accepted Nonsense). `score_2`/`score_1`/`score_0` are the per-prompt counts out of
  `nonsense_count` (100 in this snapshot). `error_count` is 0 for every row in this snapshot.

## Cross-Ref Caveats

- `avg_score` is a single-skill behavioral metric (nonsense detection), not a broad capability
  index like ECI. It can move in the opposite direction from raw capability: some strong reasoning
  configurations over-engage with the bad premise and score low.
- Rows are per reasoning level, so one base model maps to several external rows. The cross-ref
  framework dedupes multiple external rows per LLM Chess player by keeping the highest `avg_score`.
- Many leaderboard models have no LLM Chess counterpart (different host tier, open-weight long-tail,
  stealth/`openrouter/*-alpha` rows, or simply untested in LLM Chess). Those stay `unmatched`.
- The row-to-LLM-Chess mapping for this snapshot lives at
  `data/cross-ref/mappings/bullshit_bench.csv` and must be reviewed there rather than inferred from
  the source labels alone.

## Provenance

- Repository: <https://github.com/petergpt/bullshit-benchmark>
- v2 leaderboard: `data/v2/latest/leaderboard.csv`
- Technical notes: `docs/TECHNICAL.md`
- License: MIT
