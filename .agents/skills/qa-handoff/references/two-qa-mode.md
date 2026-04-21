# Two-QA Mode

Use this mode only when the user asks for a stronger QA gate or when you intentionally want both `qa-1` and `qa-2` to review the same implementation.

Use the handoff package requirements, reviewer standards, and reporting rules from `references/default-qa-mode.md`, then apply the dual-review rules in this file. Where this file conflicts with default mode wording, this file governs for two-QA runs.

## Roles
- Implementer: prepares one shared handoff package and performs all rework.
- Reviewer A: `qa-1`
- Reviewer B: `qa-2`

There is no tie-breaker and no majority vote. The implementer must satisfy both reviewers.

## Workflow
### 1. Build One Shared Package Per Round
Send the same handoff package to both reviewers for the current round. Do not send different framing or different evidence to each reviewer.

### 2. Review In Parallel
Both reviewers assess the same submission in the same round using `references/default-qa-mode.md` plus `references/evidence-taxonomy.md`.

### 3. Apply The Round Verdict
- `PASS + PASS` means the implementation passes QA.
- `PASS + FAIL`, `FAIL + PASS`, or `FAIL + FAIL` means the round fails.
- Ambiguous or unusable reviewer output counts as FAIL for that reviewer.

Prior PASS does not carry forward after rework. Both reviewers must PASS on the same round.

### 4. Rework Against Both Reviewers
After a failed round, consider and satisfy both QA reports before resubmitting. The next handoff package must include:
- the full prior-round report from `qa-1`, explicitly labeled
- the full prior-round report from `qa-2`, explicitly labeled
- what changed in response to each reviewer's feedback, or `no change requested` for that reviewer

### 5. Handle Contradictory Feedback Explicitly
If the reviewers ask for conflicting changes:
- document the conflict in the next handoff package
- explain the reconciliation or trade-off you chose
- resubmit the updated work to both reviewers

Do not ignore one reviewer because the other already passed.

### 6. Stop After 3 Failed Rounds
The 3-round cap applies to the whole run, not per reviewer. If both reviewers have not passed by round 3, stop and report the final findings honestly.
