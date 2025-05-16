import os
import json
import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate LaTeX table from aggregate_results.json files')
    parser.add_argument('--files', nargs='+', required=True,
                        help='Paths to aggregate JSON files (_aggregate_results.json)')
    args = parser.parse_args()

    rows = []
    for filepath in args.files:
        if not os.path.isfile(filepath):
            continue
        with open(filepath) as f:
            data = json.load(f)
        # derive name from parent directory
        name = os.path.basename(os.path.dirname(filepath))
        rows.append({
            'name': name,
            'total_games': data.get('total_games', 0),
            'white_wins': data.get('white_wins', 0),
            'black_wins': data.get('black_wins', 0),
            'draws': data.get('draws', 0),
            'avg_moves': data.get('average_moves', 0.0),
            'std_dev_moves': data.get('std_dev_moves', 0.0)
        })

    # print LaTeX table
    print("\\begin{table}[ht]")
    print("  \\centering")
    print("  \\caption{Aggregate Results}")
    print("  \\begin{tabular}{lrrrrrr}")
    print("    \\toprule")
    header = "    Run & Total Games & White Wins & Black Wins & Draws & Avg Moves & Std Dev Moves \\\\"
    print(header)
    print("    \\midrule")
    for row in rows:
        name = row['name']
        tg = row['total_games']
        ww = row['white_wins']
        bw = row['black_wins']
        dr = row['draws']
        am = row['avg_moves']
        sm = row['std_dev_moves']
        print(f"    \\texttt{{{name}}} & {tg} & {ww} & {bw} & {dr} & {am:.2f} & {sm:.2f} \\")
    print("    \\bottomrule")
    print("  \\end{tabular}")
    print("\\end{table}")
