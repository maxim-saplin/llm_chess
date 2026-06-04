# DELEGATE-52 Source Note

Snapshot file: `data/cross-ref/evals/delegate-52/delegate-52-may-2026.csv`

Access date for supporting sources: 2026-05-29.

## Provenance

- Paper: *"LLMs Corrupt Your Documents When You Delegate"*, Microsoft Research, arXiv `2604.15597`
  (v1, submitted 2026-04-17). HTML: <https://arxiv.org/html/2604.15597v1>
- Benchmark code: <https://github.com/microsoft/DELEGATE52>
- Dataset: <https://huggingface.co/datasets/microsoft/delegate52> (`delegate52.jsonl`, 52 domains)

This snapshot is **transcribed by hand from the paper's Table 1** ("Round-trip relay results for 19
LLMs"). Unlike the other cross-ref evals (ECI, ARC-AGI-2, BullshitBench), DELEGATE-52 publishes **no
machine-readable results file**: the GitHub repo hosts only the evaluation harness (`run_relay.py`,
domain definitions), and the HuggingFace dataset hosts only the input documents — neither contains a
leaderboard/scores CSV or JSON. Table 1 in the paper is the authoritative, and only, results set, and
it is the most recent one (arXiv shows a single version, v1). The transcribed values were verified by
reading Table 1 twice; the `RS@2`, `RS@10`, `RS@20` and the intermediate even-`k` columns were
cross-checked across independent reads and agreed exactly.

## Local Snapshot

- Local file columns: `model`, `provider`, `rs_at_2`, `rs_at_4`, `rs_at_6`, `rs_at_8`, `rs_at_10`,
  `rs_at_12`, `rs_at_14`, `rs_at_16`, `rs_at_18`, `rs_at_20`.
- One row per evaluated model (19 rows), ordered by `rs_at_20` descending, matching the paper.
- `rs_at_k` is the Reconstruction Score after `k` interactions (= `k/2` round-trip relays), as a
  0–100 number. The full curve is kept so the cross-ref analysis is not limited to a single depth.
- `provider` is the model family/vendor as grouped in the paper (OpenAI, Anthropic, Google, Mistral,
  xAI, Moonshot).

## How To Refresh This Snapshot

There is no upstream machine-readable file to re-pull. To refresh:

1. Check arXiv `2604.15597` for a newer version (v2+) or an updated Table 1, and check the GitHub repo
   for any later-added results/leaderboard artifact (none existed as of 2026-05-29).
2. Re-transcribe Table 1 into the same column schema above, keeping `provider` grouping consistent.
3. Re-verify digits against the rendered table (and the PDF if precise claims depend on a value),
   since this snapshot is the source of truth and cannot be regenerated from a download.
4. Keep the file date-named for the refresh month and update the adapter `SOURCE_PATH`, this note, the
   `README.md` artifact map, `mapping-research/delegate_52.md`, and the filename assertion in
   `tests/test_cross_ref.py`.

## Score Meaning

- Higher `rs_at_k` is better: it is the fidelity with which the document is preserved after `k`
  delegated edit interactions. Lower means the model corrupted the document more.
- The benchmark's point is **long-horizon degradation**: every model declines as `k` grows, so the
  spread (and the discrimination between models) is largest at `rs_at_20`. `rs_at_20` is therefore
  used as the framework's internal anchor column, but the reported result is the correlation profile
  across all depths (`rs_at_2 … rs_at_20`), plus the mean and the degradation slope, not any single
  cherry-picked depth.
- The paper headlines that frontier models lose ~25% of document content over 20 interactions.

## Cross-Ref Caveats

- **Reconstruction Score is a narrow behavior** (delegated long-horizon document-editing fidelity),
  not a broad capability index like ECI. It can diverge from chess strength.
- **Reasoning/version configs are unspecified in the machine-extractable text.** The paper relegates
  exact API model identifiers, reasoning-effort levels, and thinking budgets to Appendix L, which was
  not reliably extractable. The mapping therefore treats per-model reasoning configuration as
  *unspecified* and applies the established cross-ref tier convention with a config caveat
  (`variant-compatible`), holding genuinely uncertain identities (e.g. unspecified GPT-4o snapshot,
  GPT-OSS-120B reasoning tier) as `ambiguous` and absent counterparts (Mistral Large 3, the original
  Grok 4 release) as `unmatched`.
- Labels in Table 1 (e.g. "GPT 5", "Grok 4", "OSS 120B") are display names, not API identifiers, and
  must not be collapsed casually into one LLM Chess row.
- The row-to-LLM-Chess mapping for this snapshot lives at `data/cross-ref/mappings/delegate_52.csv`
  and must be reviewed there rather than inferred from the source labels alone.
