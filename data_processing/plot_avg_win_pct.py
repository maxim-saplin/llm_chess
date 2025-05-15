import json
import os
import sys
import argparse
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

REASONING_COLOR = 'coral'
DEFAULT_COLOR = 'skyblue'

PHASES = ['overall','opening','middlegame']

METRIC_LABELS = {
    'total.avg_win_pct': 'Average Win %',
    'white.avg_win_pct': 'Average Win %',
    'black.avg_win_pct': 'Average Win %',
    'total.avg_cp_loss': 'Average CP Loss',
    'white.avg_cp_loss': 'Average CP Loss',
    'black.avg_cp_loss': 'Average CP Loss',
    'white.avg_eval_delta_cp': 'Average CP Loss Per Ply',
    'black.avg_eval_delta_cp': 'Average CP Loss Per Ply',
    'total.avg_eval_delta_cp': 'Average CP Loss Per Ply',
    'total.avg_delta_win_pct': 'Average Change in Win % Per Ply',
    'white.avg_delta_win_pct': 'Average Change in Win % Per Ply',
    'black.avg_delta_win_pct': 'Average Change in Win % Per Ply'
}

METRIC_UNITS = {
    'total.avg_win_pct': '%',
    'white.avg_win_pct': '%',
    'black.avg_win_pct': '%',
    'total.avg_cp_loss': 'cp',
    'white.avg_cp_loss': 'cp',
    'black.avg_cp_loss': 'cp',
    'white.avg_eval_delta_cp': 'cp/ply',
    'black.avg_eval_delta_cp': 'cp/ply',
    'total.avg_eval_delta_cp': 'cp/ply',
    'total.avg_delta_win_pct': '%/ply',
    'white.avg_delta_win_pct': '%/ply',
    'black.avg_delta_win_pct': '%/ply'
}

REASONING_MODELS = [
    'grok-3-mini-beta-low',
    'grok-3-mini-beta-high',
    'claude-3-7-sonnet-20250219-thinking_budget_2048',
    'o4-mini-2025-04-16-medium',
    'o4-mini-2025-04-16-low'
]

NON_REASONING_MODELS = [
    'grok-3-mini-beta',
    'grok-3-beta',
    'gpt-4.1-mini-2025-04-14',
    'gpt-4.1-2025-04-14',
    'claude-3-7-sonnet-20250219',
    'claude-3.5-haiku-20241022',
]

def run_plot(metric, phase, threshold, base_dir):
    metric_parts = metric.split('.')
    # Discover JSON files
    json_files = []
    for model in sorted(os.listdir(base_dir)):
        if model.startswith('lvl') or model in ('LLM_WHITE_vs_RANDOM_PLAYER', 'RANDOM_PLAYER_vs_LLM_BLACK', 'CHESS_ENGINE_DRAGON_vs_LLM_BLACK'):
            continue
        fpath = os.path.join(base_dir, model, f"{phase}.json")
        if os.path.isfile(fpath):
            json_files.append((model, fpath))
    # Collect data
    labels, values = [], []
    for model, path in json_files:
        with open(path) as f:
            js = json.load(f)
        key = [k for k in js.keys() if k != 'phase'][0]
        metric_js = js[key]
        val = metric_js
        for part in metric_parts:
            val = val.get(part)
        labels.append(model)
        values.append(val)
    # Sort by value
    pairs = sorted(zip(labels, values), key=lambda x: x[1])
    if not pairs:
        print(f"No data for metric={metric}, phase={phase}")
        return
    labels, values = zip(*pairs)
    # Colors
    colors = [REASONING_COLOR if model in REASONING_MODELS else DEFAULT_COLOR for model in labels]
    # Plot
    plt.figure(figsize=(12, 6))
    plt.ioff()
    plt.bar(labels, values, color=colors)
    if threshold is not None:
        plt.axhline(threshold, color='black', linestyle='--')
    handles = [Patch(color=REASONING_COLOR, label='Reasoning'), Patch(color=DEFAULT_COLOR, label='Non-Reasoning')]
    plt.legend(handles=handles)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    unit = METRIC_UNITS.get(metric, '')
    label_text = METRIC_LABELS.get(metric, metric)
    full_label = f"{label_text} ({unit})" if unit else label_text
    plt.ylabel(full_label)
    plt.xticks(rotation=45, ha='right')
    # If metric is a percentage metric (unit '%'), constrain y-axis to 0-100
    unit = METRIC_UNITS.get(metric, '')
    if unit == '%':
        plt.ylim(0, 100)
    plt.tight_layout()
    # Save
    out_dir = os.path.join(os.path.dirname(__file__), 'analysis_plots')
    os.makedirs(out_dir, exist_ok=True)
    file_base = metric.replace('.', '_') + f"_{phase}_plot"
    plt.savefig(os.path.join(out_dir, f"{file_base}.png"), dpi=300)
    plt.savefig(os.path.join(out_dir, f"{file_base}.svg"), dpi=300)
    plt.clf()

# Parse args
parser = argparse.ArgumentParser(description="Plot any metric from per-ply analysis overall JSONs")
parser.add_argument('--metric', type=str, default='total.avg_win_pct',
                    help="Metric path, e.g. total.avg_win_pct or white.avg_cp_loss")
parser.add_argument('--threshold', type=float, default=None, help="Optional threshold for coloring bars")
parser.add_argument('--base-dir', type=str,
                    default=os.path.join(os.path.dirname(__file__), '../per_ply_analysis'),
                    help="Base directory for per_ply_analysis")
parser.add_argument('--phase', choices=['overall','opening','middle','endgame'], default='overall',
                    help="Game phase to include (loads <phase>.json per model)")
parser.add_argument('--batch', action='store_true', help="Generate all metrics for all phases")
args = parser.parse_args()
phase = args.phase.lower()
base_dir = os.path.abspath(args.base_dir)

# Batch invocation: inline calls
if args.batch:
    for ph in PHASES:
        for m in METRIC_LABELS.keys():
            if not m.startswith('black.'):
                continue
            print(f"Plotting metric={m}, phase={ph}")
            run_plot(m, ph, args.threshold, base_dir)
    sys.exit(0)

# Default run
run_plot(args.metric, phase, args.threshold, base_dir)
