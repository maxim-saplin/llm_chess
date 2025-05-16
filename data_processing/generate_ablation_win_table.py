import os
import json
import argparse

TEST_ORDER = [
    'always_board_state', 'always_legal_moves', 'ascii', 'fen',
    'only_make_move', 'only_make_move_previous_moves', 'previous_moves'
]
MODEL_FILTER = ['grok-3-mini', 'o4-mini']

def display_label(name):
    # convert snake_case to Title Case
    return name.replace('_', ' ').replace('-', ' ').title()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate LaTeX table of avg_win_pct for ablation tests')
    parser.add_argument('--per-ply-dir', type=str, required=True,
                        help='Path to per_ply_analysis directory')
    args = parser.parse_args()

    root = os.path.join(args.per_ply_dir, 'RANDOM_PLAYER_vs_LLM_BLACK')
    # determine tests
    tests = [t for t in TEST_ORDER if os.path.isdir(os.path.join(root, t))]
    # determine common models
    common = None
    for t in tests:
        models = set(os.listdir(os.path.join(root, t)))
        common = models if common is None else common & models
    # filter models
    models = sorted([m for m in common if any(f in m for f in MODEL_FILTER)])

    # gather data
    data = {m: {} for m in models}
    for t in tests:
        for m in models:
            path = os.path.join(root, t, m, 'overall.json')
            if os.path.isfile(path):
                with open(path) as f:
                    js = json.load(f)
                # extract avg_win_pct under model key
                key = [k for k in js if k.lower() != 'phase'][0]
                # use black player's average win percentage
                val = js[key]['black']['avg_cp_loss']
                data[m][t] = val
            else:
                data[m][t] = None

    # print LaTeX table
    print("\\begin{table}[htbp]")
    print("\\centering")
    print(r"\\caption{Win rates on LLM vs Random ablations}")
    print(r"\\label{tab:llm-ablation-win-rates}")
    print(r"\\resizebox{\\linewidth}{!}{")
    cols_spec = 'l' + 'r' * len(tests)
    print(f"\\begin{{tabular}}{{{cols_spec}}}")
    print("\\toprule")
    header = 'Model & ' + ' & '.join(display_label(t) for t in tests) + r" \\\\"
    print(header)
    print("\\midrule")
    for m in models:
        disp = display_label(m)
        row = [f"{data[m][t]:.1f}" if data[m][t] is not None else '-' for t in tests]
        print(f"\\texttt{{{disp}}} & " + ' & '.join(row) + r" \\\\")
    print("\\bottomrule")
    print("\\end{tabular}")
    print(r"}")
    print("\\end{table}")
