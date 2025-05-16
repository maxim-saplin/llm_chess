"""
Script: generate_winpct_level_table.py
Generates a LaTeX table of win % for two models vs baseline levels 1-5.
"""
import os
import json
import argparse

parser = argparse.ArgumentParser(description="Generate Win % table vs levels")
parser.add_argument('--models', nargs=2, required=True,
                    help="Two model folder names to compare, e.g. grok-3-mini-beta-high o3-2025-04-16-low")
parser.add_argument('--levels', nargs='+', type=int, default=[1,2,3,4,5],
                    help="List of baseline levels, e.g. 1 2 3 4 5")
parser.add_argument('--phase', choices=['overall','opening','middle','endgame'],
                    default='overall', help="Game phase JSON to load")
parser.add_argument('--base-dir', type=str,
                    default=os.path.abspath(os.path.join(os.path.dirname(__file__), '../per_ply_analysis')),
                    help="Base dir for per_ply_analysis")
args = parser.parse_args()

model1, model2 = args.models
levels = args.levels
phase = args.phase
# Build runs1 with special handling for grok-3-mini variants
runs1 = []
for lvl in levels:
    # For grok-3-mini, use mini-fast-beta-high at levels 4 and 5
    if model1 == 'grok-3-mini-beta-high' and lvl in [4,5]:
        runs1.append(f"lvl-{lvl}_vs_grok-3-mini-fast-beta-high")
    else:
        runs1.append(f"lvl-{lvl}_vs_{model1}")
runs2 = [f"lvl-{lvl}_vs_{model2}" for lvl in levels]

# collect win% values
vals1, vals2 = [], []
for run in runs1:
    path = os.path.join(args.base_dir, run, f"{phase}.json")
    with open(path) as f:
        js = json.load(f)
    key = [k for k in js if k!='phase'][0]
    # use black win %
    val = js[key]['black']['avg_win_pct']
    pct = val*100 if val<=1 else val
    vals1.append(round(pct,2))
for run in runs2:
    path = os.path.join(args.base_dir, run, f"{phase}.json")
    with open(path) as f:
        js = json.load(f)
    key = [k for k in js if k!='phase'][0]
    # use black win %
    val = js[key]['black']['avg_win_pct']
    pct = val*100 if val<=1 else val
    vals2.append(round(pct,2))

# print LaTeX
caption = f"Black Win % Comparison ({phase})"
label = f"tab:black_winpct_{phase}"
print("\\begin{table}[ht]")
print("  \\centering")
print(f"  \\caption{{{caption}}}")
print(f"  \\label{{{label}}}")
print("  \\begin{tabular}{lrr}")
print("    \\toprule")
# header
print("    Level & %s & %s \\" % (model1, model2))
print("    \\midrule")
for lvl, v1, v2 in zip(levels, vals1, vals2):
    s1 = "{:.2f}".format(v1)
    s2 = "{:.2f}".format(v2)
    print("    %d & %s & %s \\" % (lvl, s1, s2))
print("    \\bottomrule")
print("  \\end{tabular}")
print("\\end{table}")
