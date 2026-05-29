---
name: cross-ref-research
description: "Use when implementing, extending, auditing, or QAing LLM Chess data/cross-ref workflows: external eval source snapshots, conservative model mapping, run_cross_ref.py commands, generated results, consolidated reports, mapping review, cross-eval reports, reproducibility audits, and verification."
---
# Cross-Ref Research

Use this skill for work under `data/cross-ref/`: adding or maintaining external evals, changing model mappings, regenerating published artifacts, auditing trust status, or updating the consolidated cross-eval report from generated facts.

Do not use this skill for ad hoc leaderboard commentary, fuzzy one-off model matching, or claims that will not be backed by source snapshots, mapping rows, generated artifacts, and runtime checks.

## Start Here

1. Read `data/cross-ref/README.md` for the research workspace shape, artifact roles, and trust boundaries.
2. Read `data/cross-ref/CONSOLIDATED_REPORT.md` when the task touches published findings or unresolved mapping caveats.
3. Choose the narrow task path: output review, mapping row review, command execution, publication, or methodology change.
4. Work from the repository root with `.venv` active. Non-publish commands default to review outputs outside `data/cross-ref/`; use `--publish` only when intentionally updating checked-in generated artifacts.

## Procedure

1. Anchor the task in the smallest controlled surface: source snapshot, mapping CSV, adapter, generated result, report section, or failing command.
2. Preserve the workspace contract: source snapshots, mappings, mapping rationale, generated results, and code live in separate folders.
3. Treat model identity as research, in both directions. Map a model when the evidence is clear — a counterpart that exists in `elo_refined.csv` and fits the established tier convention belongs in the comparison. Hold a row as `ambiguous`, `unmatched`, or `excluded` when identity, configuration, or tier is genuinely uncertain. The goal is the mapping that reflects the evidence: neither inventing matches nor withholding obvious ones.
4. Run the cheapest check that can disprove the current change before expanding scope. For mapping or adapter edits, that is usually a focused `run_cross_ref.py` command with explicit `/tmp` outputs or `tests/test_cross_ref.py`.
5. Publish generated artifacts only through `data/cross-ref/run_cross_ref.py --publish`. Do not hand-edit files under `data/cross-ref/results/`.
6. Update `data/cross-ref/CONSOLIDATED_REPORT.md` only from generated summaries and reports, then keep caveats explicit when unresolved rows constrain conclusions.
7. Before reporting done, run the task-relevant verification commands and the requested final checks. Use the QA handoff skill when the change is implementation-heavy or affects published artifacts.

## Examples

Existing mapping correction:

```text
1. Inspect data/cross-ref/mappings/{eval_id}.csv and mapping-research notes.
2. Update only rows with evidence; leave weak matches unresolved.
3. Run the eval in review mode or to explicit `/tmp` outputs, then tests/test_cross_ref.py.
4. If publishing, regenerate the eval artifacts, mapping_review.*, and cross-eval outputs as needed.
```

Existing output trust check:

```text
1. Run audit in default review mode while investigating, and add `--publish` only when refreshing checked-in audit outputs.
2. Read audit status fields separately: reproducibility can pass while coverage remains review-needed.
3. Trace headline claims through *_summary.json before editing narrative reports.
```

Adding another eval:

```text
1. Add evals/<eval-folder>/SOURCE.md with provenance, score meaning, columns, and caveats.
2. Add adapter and runner registration.
3. Add mappings/<eval_id>.csv with conservative statuses and rationale.
4. Add focused tests, generate /tmp artifacts, review coverage, then publish through the runner.
```

## Refreshing an External Snapshot

Refreshing an existing eval's source snapshot with newer upstream data has its own steps beyond the examples above. Work through them in order.

1. Fetch upstream into a scratch file and keep the snapshot schema identical to the prior file. Record the canonical machine-readable URL in the eval's `SOURCE.md` so the next refresh starts from it (for ECI it is `https://epoch.ai/data/eci_scores.csv`, the published overall index; the leaderboard page renders that data dynamically and offers no direct download).
2. Re-key the mapping to the new rows. The mapping joins on `(eval_row_id, eval_model_label)`, and `eval_row_id` is the row position assigned at normalize time, so a changed row set or order needs a fresh key. Index the existing mapping by `eval_model_label`, carry each retained model's reviewed decision onto its new position, and drop rows for models upstream no longer lists.
3. Reconcile the mapping with current data. Map new upstream models that have a clear LLM Chess counterpart, following the established tier convention (base GPT-5.x → `-medium`; mini/nano → `-high`; the reasoning run rather than the chat or non-reasoning variant). Revisit inherited mappings too, since a newly added LLM Chess model can be the better match — for example `GPT-5.4` moves to `gpt-5.4-medium` once that run exists. Keep a row `unmatched` when identity is genuinely uncertain or no counterpart exists, note why in `open_questions`, and raise true identity conflicts with the maintainer.
4. Update the snapshot name and its references. Snapshots are date-named, so rename to the new date and update the adapter `SOURCE_PATH`, `SOURCE.md`, the `README.md` artifact map, `mapping-research/<eval>.md`, and any filename assertions in `tests/test_cross_ref.py`.
5. Separate the data effect from any code change. Checked-in `results/` baselines may predate the current code (signs: `llm_chess_inputs.data_quality` is null, or `prediction.ols.in_sample` is present). For a clean data-only diff, regenerate the baseline by running current code on the previous inputs — check the old snapshot and mapping out to `/tmp` — then diff the new run against that baseline.
6. Read the test results in context. `tests/test_cross_ref.py` pins dataset-derived counts and correlations, so a refresh will move several of them; refresh those expectations as part of the change and confirm the structural assertions still hold.

## Optional Work Splitting

For large mechanical row review or command-output verification, an agent may ask another agent to inspect a bounded slice. Keep the request mechanical, provide exact files and acceptance criteria, and re-check the answer against the source artifacts yourself. These helper notes are not cross-ref artifacts and are not required workflow.

## Edge Cases

- Python and pytest version strings are informational unless a command actually fails.
- The mapping is keyed by `eval_row_id` (the normalize-time row position) together with `eval_model_label`, so re-key it whenever a snapshot's rows change order or membership (see Refreshing an External Snapshot).
- A `rerun-diff` is a clean data comparison only when the baseline `results/` were generated by the current code; regenerate the baseline first if they may be older.
- ARC `COST (V3)` remains unresolved in located official sources; keep cost interpretation conservative.
- Human baselines and benchmark-system rows stay visible in source and coverage outputs but are excluded from LLM Chess correlation samples.
- Release-controlled correlations are lower than raw Elo correlations; do not present raw correlations as model-capability proof without the timing caveat.
- If generated outputs differ after a rerun, inspect whether the difference comes from source, mapping, code, dependency behavior, or expected artifact metadata before publishing.