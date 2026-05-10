---
name: cross-ref-research
description: Implement or extend LLM Chess cross-reference eval workflows with source research, conservative model mapping, runtime verification, and QA.
---
# Cross-Ref Research

Use this skill when you are adding or maintaining an external-eval cross-reference under `data/cross-ref/`.

Do not use this skill for ad hoc leaderboard summaries, fuzzy one-off model matching, or work that will not end in generated result artifacts plus QA.

## Preconditions

- Work from the repository `.venv`.
- Treat the current task instructions plus the checked-in cross-ref docs as the governing plan.
- Do not create or depend on a durable cross-ref research-plan file.
- Keep source snapshots, mapping files, generated results, and reusable code separate.
- Do not write this skill early. It belongs at the end of a real verified run.

## Verified Preflight

Run these commands before refactoring or adding an eval:

```text
.venv/bin/python --version
.venv/bin/python -c "import sys; print(sys.executable)"
.venv/bin/python -c "import pandas, numpy, scipy, pytest, chess; print('imports-ok')"
.venv/bin/python -m pytest --version
```

For cross-ref work, also run the current ECI workflow through the shared runner and confirm it is non-mutating:

```text
.venv/bin/python data/cross-ref/run_cross_ref.py eci \
  --inventory-output /tmp/llm_chess_preflight_models.csv \
  --summary-output /tmp/llm_chess_eci_preflight_summary.json \
  --html-output /tmp/llm_chess_eci_preflight.html \
  --normalized-output /tmp/llm_chess_eci_preflight_normalized.csv \
  --coverage-output /tmp/llm_chess_eci_preflight_coverage.csv \
  --test-status preflight \
  --mapping-qa-status preflight \
  --run-qa-status preflight
```

Working markers from this implementation:

- `Python 3.12.13`
- `imports-ok`
- `pytest 9.0.2`
- ECI preflight summary still showed `matched_sample_max_dedupe = 66` and `pearson_r = 0.6967985896751968`
- `git status --short --untracked-files=all -- data/cross-ref` stayed unchanged across the smoke run

Do not continue if that smoke path fails.

## Current Framework Surface

Shared code lives here:

- `data/cross-ref/run_cross_ref.py`
- `data/cross-ref/framework/`
- `data/cross-ref/adapters/eci.py`
- `data/cross-ref/adapters/arc_agi_2.py`

Current supported evals:

- `eci`
- `arc_agi_2`

Generated outputs live here:

- `data/cross-ref/results/{eval_id}_summary.json`
- `data/cross-ref/results/{eval_id}.html`
- `data/cross-ref/results/{eval_id}_normalized.csv`
- `data/cross-ref/results/{eval_id}_coverage.csv`

Model identity and mappings live here:

- `data/cross-ref/model-identity/llm_chess_models.csv`
- `data/cross-ref/mappings/eci.csv`
- `data/cross-ref/mappings/arc_agi_2.csv`

## Source Package Discipline

For every eval source package:

1. Preserve the raw source snapshot with minimal edits.
2. Write `SOURCE.md` with provenance URLs, access date, columns, score meaning, and unresolved caveats.
3. Keep generated artifacts out of the source folder.
4. Preserve source-specific unresolved fields rather than inventing semantics.

Executed examples:

- `data/cross-ref/evals/eci/SOURCE.md`
- `data/cross-ref/evals/arc-agi-2/SOURCE.md`

ARC-specific lesson from this run:

- `COST (V3)` stayed unresolved in official sources; keep it in the source contract, parse it conservatively, and surface the limitation explicitly.

## Mapping Discipline

Mapping is a research task, not a fuzzy-matching task.

- Use the LLM Chess inventory in `data/cross-ref/model-identity/llm_chess_models.csv` as the canonical target surface.
- Python may generate clerical candidates, but accepted identity decisions need evidence.
- Keep row-level rationale, confidence, review status, and open questions in the mapping CSV.
- Preserve unresolved rows as `ambiguous`, `unmatched`, or `excluded`.

Statuses used in the current framework:

- `accepted`
- `alias`
- `variant-compatible`
- `ambiguous`
- `unmatched`
- `excluded`

Reasoning and variant rules exercised in this run:

- Do not collapse `Pro`, `xHigh`, `Max`, `Deep Think`, `Refine.`, token-budget, preview, or context-window variants casually.
- If multiple reasoning variants exist and the benchmark row does not state the effort level clearly, keep it `ambiguous` unless one exact compatible row is defensible.
- Human baselines and benchmark-system rows stay in the source and coverage outputs but are `excluded` from LLM Chess correlation samples.

Current mapping notes to reuse:

- `data/cross-ref/mapping-research/eci.md`
- `data/cross-ref/mapping-research/arc_agi_2.md`

ECI migration rule that worked:

- preserve the legacy bridge as `source_llm_chess_model`
- seed non-null bridge rows into the generic mapping file
- keep no-bridge rows explicit as `unmatched`
- use the shared mapping file for new analysis instead of the source column directly

ARC lessons from the executed mapping:

- GPT-5.5 and Claude 4.7 rows stayed `unmatched` because there were no compatible current LLM Chess rows
- many GPT/Claude/Gemini effort and configuration variants stayed `ambiguous` on purpose
- current status mix was: `accepted 9`, `alias 45`, `variant-compatible 12`, `ambiguous 55`, `unmatched 28`, `excluded 8`

## Commands That Worked

Refresh inventory:

```text
.venv/bin/python data/cross-ref/run_cross_ref.py inventory
```

Focused regression test slice:

```text
.venv/bin/python -m pytest tests/test_cross_ref.py
```

Generate final ECI artifacts with embedded verification evidence:

```text
.venv/bin/python data/cross-ref/run_cross_ref.py eci \
  --verification-command ".venv/bin/python -m pytest tests/test_cross_ref.py" \
  --verification-output-file /tmp/cross_ref_pytest_output.txt \
  --verification-command "eci adapter verification probe" \
  --verification-output-file /tmp/eci_verification_output.txt \
  --test-status passed \
  --mapping-qa-status pass \
  --run-qa-status pass
```

Generate final ARC artifacts with embedded verification evidence:

```text
.venv/bin/python data/cross-ref/run_cross_ref.py arc_agi_2 \
  --verification-command ".venv/bin/python -m pytest tests/test_cross_ref.py" \
  --verification-output-file /tmp/cross_ref_pytest_output.txt \
  --verification-command "arc adapter verification probe" \
  --verification-output-file /tmp/arc_verification_output.txt \
  --test-status passed \
  --mapping-qa-status pass \
  --run-qa-status pass
```

## Stable Markers From This Run

Use these as sanity checks when refactoring:

- ECI shared-runner parity: `matched_sample_max_dedupe = 66`
- ECI shared-runner parity: `pearson_r = 0.6967985896751968`
- Published ECI coverage currently separates:
  - `accepted_mapping_rows = 89`
  - `rows_joined_to_llm_chess_elo = 74`
  - `unique_llm_chess_players_joined_to_elo = 66`
  - `regression_rows_max_dedupe = 66`
- Published ARC matched rows currently equal `54`
- Published ARC `cost_v3` parse rate currently equals `0.0`

## Output Contract Rules

Published summaries must carry these sections:

- `inputs`
- `llm_chess_inputs`
- `mapping`
- `coverage`
- `relationships`
- `prediction`
- `sensitivity`
- `verification`

The `verification` block must include:

- command strings
- embedded command output in `verification_checks`
- artifact paths
- test status
- mapping QA status
- run QA status
- known limitations

The runner now fills `verification.known_limitations` from the summary `limitations` list when the CLI does not provide them explicitly.

## QA Gates

Required order that worked here:

1. preflight
2. focused tests
3. runner execution
4. QA review of framework/results
5. update published QA statuses to `pass`
6. write the skill
7. QA the skill file path

Use the repo QA skill before reporting done:

- `.agents/skills/qa-handoff/SKILL.md`

## Failure Modes Fixed In This Implementation

1. Stale ad hoc JSON probes caused false terminal failures.
  - The ECI summary output uses `counts.matched_sample_max_dedupe` and `relationship.pearson_r`.
   - Shared result summaries use `coverage` and `relationships`, not `sample_sizes`.

2. ECI coverage was ambiguous until the counts were split.
   - Keep accepted mappings, rows joined to non-null Elo, unique joined players, and deduped regression rows as separate fields.

3. Published summaries initially failed QA because they only stored verification command strings.
   - Embed actual command output in `verification.verification_checks`.

4. ARC limitations were easy to lose during publication.
   - Ensure the final summary retains them in `verification.known_limitations`.

## Extending To A New Eval

1. Add the raw snapshot under `data/cross-ref/<eval-source>/` and write `SOURCE.md` from actual web research.
2. Add or update the adapter under `data/cross-ref/adapters/`.
3. Normalize source columns into explicit score fields and parse-rate evidence.
4. Create `data/cross-ref/mappings/<eval_id>.csv` with conservative statuses.
5. Keep ambiguous/unmatched rows visible in coverage output.
6. Add or update focused tests in `tests/test_cross_ref.py`.
7. Run the eval through `run_cross_ref.py` with embedded verification outputs.
8. Send the code and generated artifacts through QA before reporting done.

If you cannot produce actual command output, actual artifact files, and QA evidence, the packet is not done.