import os
import json
import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate LaTeX table for Random Player vs Black tests')
    parser.add_argument('--logs-dir', type=str, required=True,
                        help='Path to _logs/new directory')
    parser.add_argument('--per-ply-dir', type=str, required=True,
                        help='Path to per_ply_analysis directory')
    args = parser.parse_args()

    # collect tests
    # map test_name -> model -> metrics
    data = {}
    models = set()
    tests = []
    for model_dir in os.listdir(args.logs_dir):
        model_path = os.path.join(args.logs_dir, model_dir)
        if not os.path.isdir(model_path): continue
        for test in os.listdir(model_path):
            test_path = os.path.join(model_path, test)
            agg = os.path.join(test_path, '_aggregate_results.json')
            if not os.path.isfile(agg):
                continue
            # load aggregate
            with open(agg) as f:
                js = json.load(f)
            if js.get('player_white',{}).get('name') != 'Random_Player':
                continue
            black_model = js['player_black']['model']
            total = js.get('total_games', 1)
            bw = js.get('black_wins', 0)
            win_pct = bw/total*100
            # load CP Loss
            ply_path = os.path.join(args.per_ply_dir, 'RANDOM_PLAYER_vs_LLM_BLACK', test, 'overall.json')
            if os.path.isfile(ply_path):
                with open(ply_path) as pf:
                    js2 = json.load(pf)
                key2 = [k for k in js2 if k!='phase'][0]
                cp = js2[key2]['black']['avg_cp_loss']
                cp_loss = cp*100 if cp<=1 else cp
            else:
                cp_loss = None
            # record
            tests.append(test)
            models.add(black_model)
            data.setdefault(test, {})[black_model] = (win_pct, round(cp_loss,2) if cp_loss is not None else None)

    # use tests from per_ply_analysis/RANDOM_PLAYER_vs_LLM_BLACK
    ply_tests_dir = os.path.join(args.per_ply_dir, 'RANDOM_PLAYER_vs_LLM_BLACK')
    tests = sorted([d for d in os.listdir(ply_tests_dir)
                    if os.path.isdir(os.path.join(ply_tests_dir, d))])
    # restrict to specific models
    allowed = ['grok-3-mini-beta', 'o4-mini']
    models = [m for m in sorted(models) if m in allowed]

    # print Win % table
    print("\\begin{table}[ht]")
    print("  \\centering")
    print(r"  \\caption{Win \% for Random Player vs Black}")
    cols = tests
    print("  \\begin{tabular}{l" + "r"*len(cols) + "}")
    print("    \\toprule")
    header = "    Model " + " & ".join(cols) + " \\\\"
    print(header)
    print("    \\midrule")
    for m in models:
        row = [f"{data.get(t,{}).get(m,(0,0))[0]:.2f}" if m in data.get(t,{}) else "-" for t in cols]
        print(f"    \\texttt{{{m}}} & " + " & ".join(row) + r" \\\\ ")
    print("    \\bottomrule")
    print("  \\end{tabular}")
    print("\\end{table}")

    # print CP Loss table
    print("\\begin{table}[ht]")
    print("  \\centering")
    print(r"  \\caption{CP Loss for Random Player vs Black}")
    print("  \\begin{tabular}{l" + "r"*len(cols) + "}")
    print("    \\toprule")
    header = "    Model " + " & ".join(cols) + " \\\\"
    print(header)
    print("    \\midrule")
    for m in models:
        row = [f"{data.get(t,{}).get(m,(0,0))[1]:.2f}" if data.get(t,{}).get(m,(0,0))[1] is not None else "-" for t in cols]
        print(f"    \\texttt{{{m}}} & " + " & ".join(row) + r" \\\\ ")
    print("    \\bottomrule")
    print("  \\end{tabular}")
    print("\\end{table}")
