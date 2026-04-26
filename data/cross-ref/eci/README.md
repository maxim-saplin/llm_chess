# ECI Cross-Reference Dashboard

This folder contains the reproducible Epoch ECI cross-reference analysis against the current `llm_chess` CSVs.

Open `index.html` in a browser or Cursor preview to view the dashboard. The dashboard is generated from `eci_prediction_summary.json`; it is intentionally static and has no runtime dependencies.

Run from the repository root to regenerate both artifacts:

```bash
uv run python data/cross-ref/eci/analyze_eci_vs_llm_chess.py --output data/cross-ref/eci/eci_prediction_summary.json
```

The analysis reads `data/elo_refined.csv`, `data/models_metadata.csv`, and `data/cross-ref/eci/epoch_eci_apr_2026.csv`. The `llm_chess` CSVs are not copied into this folder.
