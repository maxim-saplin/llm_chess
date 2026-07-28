# Exploratory Runs

Generated artifacts from **research-only** runner modes that cannot be published into
[../results](../results). Nothing here is part of the governed publish surface: these files are not
covered by `run_cross_ref.py verify`, not hashed into `results/cross_ref_summary.json`, and not
checked by `run_cross_ref.py audit`. They exist so that exploratory figures quoted in
[../CONSOLIDATED_REPORT.md](../CONSOLIDATED_REPORT.md) point at an artifact instead of at a vanished
scratch directory.

Treat every number here as a research lead, not a finding.

## bullshit_bench_clean_only

`bullshit_bench --mistake-stats clean_only` re-enables the error/discipline metrics
(`wrong_actions_per_1000moves`, `wrong_moves_per_1000moves`, `mistakes_per_1000moves`) that the
default mode excludes, by dropping every model whose earliest LLM Chess game predates the
2025-03-16 logging fix. `clean_only` refuses `--publish` by design, which is exactly why these
outputs live here.

Regenerate with:

```bash
.venv/bin/python data/cross-ref/run_cross_ref.py bullshit_bench \
  --mistake-stats clean_only \
  --summary-output data/cross-ref/exploratory/bullshit_bench_clean_only_summary.json \
  --html-output data/cross-ref/exploratory/bullshit_bench_clean_only.html \
  --coverage-output data/cross-ref/exploratory/bullshit_bench_clean_only_coverage.csv
```

These files were regenerated on 2026-07-27 against the same source snapshot, mapping CSV, and
`data/elo_refined.csv` as the current publish, so they are directly comparable to it. A later
republish does **not** refresh them automatically — rerun the command above, or the numbers quoted
in the consolidated report will silently drift out of date.
