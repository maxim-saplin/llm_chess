"""
Script: generate_comparison_table.py
Generates a LaTeX table comparing specified metrics between selected models and a baseline (e.g., engine level 1).
"""
import os
import json
import argparse
import pandas as pd

# Default metrics and labels
METRIC_KEYS = [
    'black.avg_win_pct',
    'black.avg_cp_loss',
    'black.avg_eval_delta_cp',
    'black.avg_delta_win_pct'
]
METRIC_LABELS = {
    'black.avg_win_pct': 'Win %',
    'black.avg_cp_loss': 'CP Loss',
    'black.avg_eval_delta_cp': 'Eval Δ (CP)',
    'black.avg_delta_win_pct': 'Δ Win %'
}
METRIC_UNITS = {
    'black.avg_win_pct': '%',
    'black.avg_cp_loss': 'cp',
    'black.avg_eval_delta_cp': 'cp/ply',
    'black.avg_delta_win_pct': '%/ply'
}

# CLI
parser = argparse.ArgumentParser(description="Generate LaTeX comparison table for models vs baseline.")
parser.add_argument('--models', nargs='+', default=[
    'o4-mini-2025-04-16-low',
    'o4-mini-2025-04-16-medium',
    'o4-mini-2025-04-16-high'
], help="List of model folder names to compare.")
parser.add_argument('--baseline', type=str, default='lvl1', help="Baseline model folder (e.g., lvl1).")
parser.add_argument('--phase', choices=['overall','opening','middle','endgame'], default='overall', help="Phase JSON to load.")
parser.add_argument('--base-dir', type=str,
                    default=os.path.abspath(os.path.join(os.path.dirname(__file__), '../per_ply_analysis')),
                    help="Base directory containing per-ply JSON folders.")
args = parser.parse_args()

# Build list of all folders to load
folders = args.models + [args.baseline]

data = {'Model': []}
# initialize columns
for key in METRIC_KEYS:
    label = METRIC_LABELS.get(key, key)
    unit = METRIC_UNITS.get(key, '')
    col = f"{label} ({unit})" if unit else label
    data[col] = []

# Load data
for folder in folders:
    path = os.path.join(args.base_dir, folder, f"{args.phase}.json")
    if not os.path.isfile(path):
        print(f"Warning: JSON not found for {folder} at {path}")
        continue
    with open(path) as f:
        js = json.load(f)
    key = [k for k in js if k != 'phase'][0]
    node = js[key]
    data['Model'].append(folder)
    for mk in METRIC_KEYS:
        val = node
        for part in mk.split('.'):
            val = val.get(part)
        # format percent
        if METRIC_UNITS.get(mk) == '%':
            val = val * 100 if val <= 1 else val
        data_label = f"{METRIC_LABELS.get(mk, mk)} ({METRIC_UNITS.get(mk,'')})"
        data[data_label].append(round(val, 2))

# Create DataFrame and reorder rows (baseline last)
df = pd.DataFrame(data)
# Move baseline to bottom
order = [m for m in args.models if m in df['Model'].values] + [args.baseline]
df = df.set_index('Model').loc[order].reset_index()

# Output LaTeX
latex = df.to_latex(index=False, caption="Comparison of Metrics: Models vs Level 1 Baseline", label="tab:comp",
                     float_format="%.2f", column_format='l' + 'r'* (len(df.columns)-1), longtable=False, escape=False)
print(latex)
