# Default QA Mode

Fast single QA mode.

## Roles
- Implementer: prepares the handoff package and performs rework.
- Reviewer: one QA reviewer

## Workflow
### 1. Build The Handoff Package
Assemble one handoff package with these sections:
- Conversation Story
  - what the user asked for, including scope changes or clarifications
  - decisions the implementer made and why
- What Was Done
  - files created, modified, or deleted, with one-line summaries
  - design decisions, trade-offs, and anything intentionally left out
- Verification Evidence
  - paste actual output, not summaries
  - include each applicable evidence category: preflight or admission-gate output, CLI or runtime verification output, headless app assertions for UI work, linter output, negative and corner coverage, plan traceability rows, data proof when data is claimed, multi-target coverage, and `N/A` justifications or user-approved waivers
- Prior QA History (rounds 2+)
  - full FAIL report from each prior round
  - what rework was done in response

Before assembling or reviewing evidence, read `references/evidence-taxonomy.md`.

### 2. Review The Submission
Send the package to one QA reviewer. The reviewer applies the shared invariants from `SKILL.md`, the verdict rules below, and `references/evidence-taxonomy.md`.

### 3. Apply The Verdict
Return `PASS` when all required evidence is present and no FAIL conditions apply.
- `PASS` means the implementation can be reported to the user.
- `FAIL` means do not report to the user yet.
- Ambiguous or unusable reviewer output counts as FAIL.

Return `FAIL` when any of the following is true:
- A required preflight or admission gate was only run after code edits.
- A required preflight failed but implementation continued without an explicit user-approved blocker workaround.
- Evidence is happy-path-only for behavior that has plausible negative or corner states.
- Stateful UI logic is validated only by "no exceptions" checks.
- Claimed verification lacks pasted runtime output.
- Negative or corner coverage is omitted without explicit `N/A` justification.
- A plan requirement has no matching evidence row.
- A failed dependency is counted as "negative-path success" for a scenario that needed it happy-path.
- Data requirements are evidenced only by widget or screen presence, not actual data.
- A plan-named target or platform has zero evidence.
- The implementer self-waived without user approval.

### 4. Rework And Retry
After a failed round:
- address all QA findings
- carry the full prior FAIL report into the next round
- document what changed in response

Do not report to the user on round 1 or round 2 failures.

### 5. Stop After 3 Failed Rounds
If QA has not passed by round 3, stop rework and report the final findings honestly.

## Reporting
- On `PASS`: report completed work, note QA passed `(round N/3)`, and summarize which negative or corner cases were covered, or why `N/A` applied.
- On 1st or 2nd `FAIL`: do not report to the user. Rework and resubmit.
- On 3rd `FAIL`: report what was accomplished, that QA did not pass after 3 rounds, the final QA findings, and prior-round history.
