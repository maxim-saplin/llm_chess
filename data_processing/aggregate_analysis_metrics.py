"""
Aggregate analysis_metrics.json files across models (max 30 games each) and compute per-model averages:
- avg change in win% per ply
- avg eval_delta_cp per ply
- avg win% per ply
- classification rates (blunder, inaccuracy, mistake, best)
- average absolute centipawn loss per game (avg_cp_loss)
"""
import os
import glob
import json
from statistics import mean
import argparse
import re
import shutil

# Configuration
PHASES = ['Overall', 'Opening', 'Middlegame']
PER_PLY_DIR = os.path.join(os.getcwd(), 'per_ply_analysis')

def parse_args():
    p = argparse.ArgumentParser(description="Aggregate analysis_metrics JSON files")
    p.add_argument("input_dir", help="Path to folder containing JSON subfolders")
    p.add_argument("--max-games", type=int, default=30, help="Max games per model")
    p.add_argument("--output", default=os.path.join(os.path.dirname(__file__), 'analysis_summary.json'), help="Output JSON path")
    return p.parse_args()

def process_game(file_path, phase):
    raw = json.load(open(file_path))
    # extract ply list from analysis JSON
    games_list = raw.get('games', [])
    if not games_list or 'analysis' not in games_list[0]:
        return {'avg_delta_win_pct':0,'avg_eval_delta_cp':0,'avg_cp_loss':0,'avg_win_pct':0,'classification_rates':{cls:0 for cls in ['blunder','inaccuracy','mistake','best','ok']}}
    data = games_list[0]['analysis']
    # filter by phase
    if phase != 'Overall':
        data = [ply for ply in data if ply.get('game_phase') == phase]
    deltas = [ply['win_pct_after'] - ply['win_pct_before'] for ply in data]
    evals = [ply['eval_delta_cp'] for ply in data]
    abs_evals = [abs(ply['eval_delta_cp']) for ply in data]
    wins = [ply['win_pct_after'] for ply in data]
    total = len(data)
    rates = {}
    for cls in ['Blunder', 'Inaccuracy', 'Mistake', 'Best', 'OK']:
        count = sum(1 for ply in data if ply.get('classification') == cls)
        rates[cls.lower()] = count / total if total else 0
    return {
        'avg_delta_win_pct': mean(deltas) if deltas else 0,
        'avg_eval_delta_cp': mean(evals) if evals else 0,
        'avg_cp_loss': mean(abs_evals) if abs_evals else 0,
        'avg_win_pct': mean(wins) if wins else 0,
        'classification_rates': rates
    }

def main(input_dir, max_games, output_json):
    # Derive model name from the input directory itself
    model_name = os.path.basename(os.path.normpath(input_dir))
    game_dirs = [os.path.join(input_dir, d) for d in os.listdir(input_dir) if os.path.isdir(os.path.join(input_dir, d))]
    # Collect all analyzed.json files across subfolders (timestamps)
    all_files = []
    for game_dir in game_dirs:
        pattern = os.path.join(game_dir, '**', '*_analyzed.json')
        all_files.extend(sorted(glob.glob(pattern, recursive=True))[:max_games])
    # Limit to max_games
    all_files = all_files[:max_games]
    # Loop phases
    for phase in PHASES:
        summary = {}
        games_stats = [process_game(fp, phase) for fp in all_files]
        if not games_stats: continue
        summary[model_name] = {
            'games_processed': len(games_stats),
            'avg_delta_win_pct': mean(g['avg_delta_win_pct'] for g in games_stats),
            'avg_eval_delta_cp': mean(g['avg_eval_delta_cp'] for g in games_stats),
            'avg_cp_loss': mean(g['avg_cp_loss'] for g in games_stats),
            'avg_win_pct': mean(g['avg_win_pct'] for g in games_stats),
            'classification_rates': {cls: mean(g['classification_rates'][cls] for g in games_stats) for cls in games_stats[0]['classification_rates']}
        }
        # prepare per-phase output data
        out_data = {'phase': phase}
        out_data.update(summary)
        # determine model_name (expect single-key summary)
        model_keys = [k for k in summary.keys()]
        model_name = model_keys[0] if model_keys else 'unknown'
        dest_dir = os.path.join(PER_PLY_DIR, model_name)
        os.makedirs(dest_dir, exist_ok=True)
        # write summary JSON into per_ply_analysis/{model_name}
        dest_file = os.path.join(dest_dir, f'{phase.lower()}.json')
        with open(dest_file, 'w') as f:
            json.dump(out_data, f, indent=2)
        print(f"{phase} summary written to {dest_file}")

if __name__ == '__main__':
    args = parse_args()
    root = args.input_dir
    base = os.path.basename(os.path.normpath(root))
    # Multi-model root: iterate model folders under analysis_logs
    if base == 'analysis_logs':
        SKIP = ['RANDOM_PLAYER_vs_LLM_BLACK', 'LLM_WHITE_vs_RANDOM_PLAYER', 'CHESS_ENGINE_DRAGON_vs_LLM_BLACK']
        models = [d for d in os.listdir(root)
                  if os.path.isdir(os.path.join(root, d))
                  and not d.startswith('game_')
                  and d not in SKIP]
        for name in sorted(models):
            print(f"Processing model folder: {name}")
            main(os.path.join(root, name), args.max_games, args.output)
    elif base == 'RANDOM_PLAYER_vs_LLM_BLACK':
        # group summaries under per_ply_analysis/RANDOM_PLAYER_vs_LLM_BLACK/{model_name}
        group_root = os.path.join(PER_PLY_DIR, base)
        os.makedirs(group_root, exist_ok=True)
        # strategies contain folders (e.g., always_board_state)
        strategies = [d for d in os.listdir(root)
                      if os.path.isdir(os.path.join(root, d))]
        if not strategies:
            pass
        else:
            # model_names are subfolders under the first strategy
            first = strategies[0]
            model_dir = os.path.join(root, first)
            model_names = [d for d in os.listdir(model_dir)
                           if os.path.isdir(os.path.join(model_dir, d))]
            for model in sorted(model_names):
                model_out = os.path.join(group_root, model)
                os.makedirs(model_out, exist_ok=True)
                # override PER_PLY_DIR to model output
                prev = globals().get('PER_PLY_DIR')
                globals()['PER_PLY_DIR'] = model_out
                for strat in strategies:
                    inp = os.path.join(root, strat, model)
                    print(f"Processing model {model}, strategy {strat}")
                    main(inp, args.max_games, args.output)
                # restore PER_PLY_DIR
                globals()['PER_PLY_DIR'] = prev
    elif base == 'LLM_WHITE_vs_RANDOM_PLAYER':
        # group summaries under per_ply_analysis/LLM_WHITE_vs_RANDOM_PLAYER/{model_name}
        group_dir = os.path.join(PER_PLY_DIR, base)
        os.makedirs(group_dir, exist_ok=True)
        # override PER_PLY_DIR for child runs
        for name in sorted([d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d))]):
            print(f"Processing model folder: {name}")
            globals()['PER_PLY_DIR'] = group_dir
            main(os.path.join(root, name), args.max_games, args.output)
    elif base == 'CHESS_ENGINE_DRAGON_vs_LLM_BLACK':
        # aggregate across all timestamp subfolders as single model
        print(f"Processing model folder: {base}")
        main(root, args.max_games, args.output)
    else:
        # Single model/run directory: aggregate all *_analyzed.json under it
        print(f"Processing model folder: {base}")
        main(root, args.max_games, args.output)
