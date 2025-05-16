"""
Script: generate_phase_tables.py
Generates LaTeX tables comparing specified metrics for given run directories across multiple game phases.
"""
import os
import json
import argparse
import pandas as pd

# Metrics to include
METRIC_KEYS = [
    'black.avg_win_pct',
    'black.avg_cp_loss',
    'black.avg_eval_delta_cp',
    'black.avg_delta_win_pct'
]
METRIC_LABELS = {
    'black.avg_win_pct': 'Win \\%',
    'black.avg_cp_loss': 'CP Loss',
    'black.avg_eval_delta_cp': 'Eval \\Delta (CP)',
    'black.avg_delta_win_pct': '\\Delta Win \\%'
}
METRIC_UNITS = {
    'black.avg_win_pct': '\\%',
    'black.avg_cp_loss': 'cp',
    'black.avg_eval_delta_cp': 'cp/ply',
    'black.avg_delta_win_pct': '\\%/ply'
}

# CLI args
parser = argparse.ArgumentParser(description="Generate LaTeX tables for runs across phases.")
parser.add_argument('--runs', nargs='+', required=True,
                    help="List of run directory names under per_ply_analysis.")
parser.add_argument('--phases', nargs='+', default=['overall','opening','middlegame'],
                    help="Phases to generate tables for.")
parser.add_argument('--base-dir', type=str,
                    default=os.path.abspath(os.path.join(os.path.dirname(__file__), '../per_ply_analysis')),
                    help="Base directory containing run subfolders.")
args = parser.parse_args()

# build simple name map: strip 'lvl-<num>_vs_' prefix
NAME_MAP = {run: run.split('_vs_',1)[1] for run in args.runs}

# For each phase, build and print LaTeX table
for phase in args.phases:
    data = {'Run': []}
    # initialize columns
    cols = []
    for key in METRIC_KEYS:
        label = METRIC_LABELS.get(key, key)
        unit = METRIC_UNITS.get(key, '')
        col_name = f"{label} ({unit})" if unit else label
        data[col_name] = []
        cols.append(col_name)

    # load each run
    for run in args.runs:
        json_path = os.path.join(args.base_dir, run, f"{phase}.json")
        if not os.path.isfile(json_path):
            print(f"Warning: {json_path} not found, skipping.")
            continue
        with open(json_path) as f:
            js = json.load(f)
        key = [k for k in js if k != 'phase'][0]
        node = js[key]
        data['Run'].append(run)
        for mk in METRIC_KEYS:
            val = node
            for part in mk.split('.'):
                val = val.get(part)
            # convert ratio to percent if needed
            if METRIC_UNITS.get(mk) == '\\%':
                val = val * 100 if val <= 1 else val
            data[f"{METRIC_LABELS.get(mk, mk)} ({METRIC_UNITS.get(mk,'')})"].append(round(val, 2))

    # DataFrame
    df = pd.DataFrame(data)
    if df.empty:
        print(f"No data for phase {phase}, table skipped.")
        continue
    # reorder rows as given
    df = df.set_index('Run').loc[args.runs].reset_index()

    # Custom LaTeX table
    caption = f"Comparison of Metrics across runs (phase: {phase})"
    label = f"tab:comp_{phase}"
    # header
    print(f"\\begin{{table}}[ht]")
    print("  \\centering")
    print(f"  \\caption{{{caption}}}")
    print(f"  \\label{{{label}}}")
    print(f"  \\begin{{tabular}}{{l{'r'*len(cols)}}}")
    print("    \\toprule")
    # column names
    header = "    Run " + " & " + " & ".join(cols) + " \\\\"
    print(header)
    print("    \\midrule")
    # rows
    for i, row in df.iterrows():
        run = row.name
        # map to simple display name
        run_name = NAME_MAP.get(row['Run'], row['Run'])
        cells = []
        for j, col in enumerate(cols):
            val = row[col]
            s = f"{val:.2f}"
            cells.append(s)
        print(f"    \\texttt{{{run_name}}} & " + " & ".join(cells) + " \\\\")
    print("    \\bottomrule")
    print("  \\end{tabular}")
    print("\\end{table}\n")
