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
cross-checked across independent reads and agreed exactly. **That assurance is now known to be
insufficient for two rows — see "Unresolved Row-Order Discrepancy" immediately below.**

## Unresolved Row-Order Discrepancy (OPEN — read before using these figures)

**Status as of 2026-07-27: unresolved. The `GPT 5` and `Grok 4` rows must be re-verified against the
paper's Table 1 before this eval's figures are relied on.**

Because this snapshot has no machine-readable upstream (see above), row ordering was one of the only
independent cross-checks available on the transcription — and it fails. Against a descending
long-horizon (`rs_at_20`) order, the transcribed file contains four inversions:

| CSV lines | rows | `rs_at_20` | gap |
| --- | --- | --- | ---: |
| 5 → 6 | Claude 4.6 Sonnet → GPT 5.2 | 66.0 → 66.1 | +0.1 |
| 7 → 8 | GPT 5.1 → Kimi K2.5 | 60.5 → 64.1 | +3.6 |
| 9 → 10 | **GPT 5 → Grok 4** | **48.3 → 59.3** | **+11.0** |
| 12 → 13 | o1 → o3 | 48.1 → 48.2 | +0.1 |

The two 0.1 gaps are consistent with Table 1 being sorted on an unrounded value or on a column other
than `rs_at_20`, and are not concerning on their own. **The 11.0-point `GPT 5` / `Grok 4` inversion is
not explainable that way.** Evidence that this row pair specifically deserves scrutiny:

- The pair is inverted at *every* depth, including `rs_at_2` (91.5 vs 91.7), so no choice of sort
  column explains it away.
- `GPT 5` starts in the top cluster (`rs_at_2` = 91.5) but ends at 48.3. Every other row starting at
  `rs_at_2` ≥ 90 ends at ≥ 59.3, and `GPT 5`'s 43.2-point total drop is the steepest in that cluster.
- Neither obvious repair restores the ordering: swapping the two rows' positions, or swapping their
  values, merely relocates the inversion (whichever model then holds 48.3 sits above `GPT 4.1` at
  49.5). The discrepancy therefore cannot be resolved by inference from the snapshot alone.

What is *not* in doubt: the column schema and the 19-row count are as documented, and all 19 rows are
internally consistent — every row is monotonically non-increasing across the ten depths. **No data
value has been altered, and none should be "corrected" by guesswork.** This note records the
discrepancy; it does not resolve it.

To resolve, open arXiv `2604.15597v1` Table 1 and re-read (a) the full ten-column `GPT 5` and `Grok 4`
rows and (b) the table's actual row-ordering rule. Until then, treat the `GPT 5` row as unverified,
and treat any DELEGATE-52 conclusion that depends on `GPT 5`'s rank or magnitude as provisional.

## Local Snapshot

- Local file columns: `model`, `provider`, `rs_at_2`, `rs_at_4`, `rs_at_6`, `rs_at_8`, `rs_at_10`,
  `rs_at_12`, `rs_at_14`, `rs_at_16`, `rs_at_18`, `rs_at_20`.
- One row per evaluated model (19 rows), kept in the paper's Table 1 row order. That order is *close
  to* `rs_at_20` descending but is **not** strictly sorted by it: four adjacent pairs are inverted (see
  "Unresolved Row-Order Discrepancy" above). No depth column is strictly descending in file order
  either — `rs_at_16` comes closest with 2 inversions, `rs_at_20` has 4, `rs_at_2` has 7 — so the row
  order must not be treated as a ranking or relied on as a sort key.
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
   since this snapshot is the source of truth and cannot be regenerated from a download. **Start with
   the `GPT 5` and `Grok 4` rows and with Table 1's row-ordering rule** — those are the open items in
   "Unresolved Row-Order Discrepancy" above. Record the outcome there either way, including if the
   transcription turns out to be correct and the paper's table simply is not score-ordered.
4. Keep the file date-named for the refresh month and update the adapter `SOURCE_PATH`, this note, the
   `README.md` artifact map, `mapping-research/delegate_52.md`, and the filename assertion in
   `tests/test_cross_ref.py`.

## Score Meaning

- Higher `rs_at_k` is better: it is the fidelity with which the document is preserved after `k`
  delegated edit interactions. Lower means the model corrupted the document more.
- The benchmark's point is **long-horizon degradation**: every model declines as `k` grows (verified —
  all 19 rows are monotonically non-increasing across the ten depths). `rs_at_20` is used as the
  framework's internal anchor column because it is the paper's headline long-horizon endpoint and the
  deepest depth measured, i.e. the point the benchmark exists to expose.
- `rs_at_20` is **not** the most discriminating depth, and the anchor choice should not be justified
  that way. Across these 19 rows it has the second-lowest standard deviation of the ten depths (19.87;
  only `rs_at_2` is lower at 17.13, while `rs_at_8` is highest at 21.35), and its range is 70.9 against
  78.6 at `rs_at_6`. It does sit near the top on IQR (24.60, third of ten; `rs_at_14` and `rs_at_18`
  lead at 24.80 — inclusive-quantile method). Spread is broadly flat from `rs_at_6` onwards, so no
  depth is meaningfully "the discriminating one". The anchor is an interpretability choice, not a
  spread argument, and the reported result is the correlation profile across all depths
  (`rs_at_2 … rs_at_20`) plus the mean and the degradation slope, not any single cherry-picked depth.
- The paper headlines that frontier models lose ~25% of document content over 20 interactions. **This
  is the paper's own framing, not a figure recomputed here**, and the transcribed numbers match it only
  under one reading of the baseline: the top three rows end at `rs_at_20` = 80.9 / 73.1 / 71.5, i.e.
  19.1 / 26.9 / 28.5 points below a pristine 100 (mean 24.8, ≈ 25%). Measured instead from `rs_at_2` —
  which already carries one relay's degradation — the same three rows lose 15.9 / 21.1 / 22.8 (mean
  19.9). Do not restate the ~25% figure without stating which baseline it is against.

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
