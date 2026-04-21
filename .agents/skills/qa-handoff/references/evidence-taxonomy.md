# Evidence Taxonomy

Use this reference when assembling the handoff package or reviewing it. The entrypoint names every required category; this file spells out the stricter coverage rules.

## Negative And Corner Coverage
Where applicable, evidence must cover more than the happy path. Include a compact matrix per touched behavior:
- Happy path: expected valid flow.
- Negative path: invalid, missing, denied, or conflicting input or state.
- Corner path: boundary, small-data, or rerun edge case.

For UI or stateful logic such as `session_state`, query params, filters, pagination, or role gates, provide:
- One assertion that user action changes state or output as intended.
- One negative or corner assertion that guards against stale or invalid state.

For tasks with a required readiness or control-surface preflight, also state:
- Which preflight scope or admission gate applied.
- Whether it passed before any code edits.
- If it failed first, what blocker was reported and whether coding stopped until the environment was restored.

If negative or corner coverage is genuinely not applicable, explicitly state `N/A` with a one-line justification.

## Plan Traceability
When a plan, spec, or checklist drives the task, every numbered requirement needs a corresponding evidence row. No proof row means FAIL. "Screen rendered" never satisfies "data loaded."

## Data Proof
If a requirement claims data such as rows, counts, or records, all four must be present:
- service dependency running
- correct seeded user
- positive data assertion
- absence of error state

Any missing item means FAIL.

## Multi-Target Coverage
If the plan names N targets, the evidence must cover N targets. No silent drops.

## Waivers
Only the user can waive a requirement. Self-waivers are FAIL.
