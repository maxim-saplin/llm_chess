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
import sys

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
    # split by player color if available, else by ply index
    white_data = [ply for ply in data if ply.get('player') == 'white']
    black_data = [ply for ply in data if ply.get('player') == 'black']
    # fallback: use ply index parity
    if not white_data and not black_data:
        white_data = data[0::2]
        black_data = data[1::2]
    def stats(dset):
        deltas_ = [ply['win_pct_after'] - ply['win_pct_before'] for ply in dset]
        evals_ = [ply['eval_delta_cp'] for ply in dset]
        abs_evals_ = [abs(ply['eval_delta_cp']) for ply in dset]
        wins_ = [ply['win_pct_after'] for ply in dset]
        total_ = len(dset)
        rates_ = {cls: (sum(1 for ply in dset if ply.get('classification','').lower() == cls)/total_ if total_ else 0) for cls in ['blunder','inaccuracy','mistake','best','ok']}
        return {
            'games_processed': 1,
            'avg_delta_win_pct': mean(deltas_) if deltas_ else 0,
            'avg_eval_delta_cp': mean(evals_) if evals_ else 0,
            'avg_cp_loss': mean(abs_evals_) if abs_evals_ else 0,
            'avg_win_pct': mean(wins_) if wins_ else 0,
            'classification_rates': rates_
        }
    return {'white': stats(white_data), 'black': stats(black_data), 'total': stats(data)}

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
            'white': {
                'avg_delta_win_pct': mean(g['white']['avg_delta_win_pct'] for g in games_stats),
                'avg_eval_delta_cp': mean(g['white']['avg_eval_delta_cp'] for g in games_stats),
                'avg_cp_loss': mean(g['white']['avg_cp_loss'] for g in games_stats),
                'avg_win_pct': mean(g['white']['avg_win_pct'] for g in games_stats),
                'classification_rates': {cls: mean(g['white']['classification_rates'][cls] for g in games_stats) for cls in games_stats[0]['white']['classification_rates']}
            },
            'black': {
                'avg_delta_win_pct': mean(g['black']['avg_delta_win_pct'] for g in games_stats),
                'avg_eval_delta_cp': mean(g['black']['avg_eval_delta_cp'] for g in games_stats),
                'avg_cp_loss': mean(g['black']['avg_cp_loss'] for g in games_stats),
                'avg_win_pct': mean(g['black']['avg_win_pct'] for g in games_stats),
                'classification_rates': {cls: mean(g['black']['classification_rates'][cls] for g in games_stats) for cls in games_stats[0]['black']['classification_rates']}
            },
            'total': {
                'avg_delta_win_pct': mean(g['total']['avg_delta_win_pct'] for g in games_stats),
                'avg_eval_delta_cp': mean(g['total']['avg_eval_delta_cp'] for g in games_stats),
                'avg_cp_loss': mean(g['total']['avg_cp_loss'] for g in games_stats),
                'avg_win_pct': mean(g['total']['avg_win_pct'] for g in games_stats),
                'classification_rates': {cls: mean(g['total']['classification_rates'][cls] for g in games_stats) for cls in games_stats[0]['total']['classification_rates']}
            }
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
    orig_per_ply = PER_PLY_DIR
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
        # iterate over each strategy folder under RANDOM_PLAYER_vs_LLM_BLACK
        strategies = [d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d))]
        for strat in sorted(strategies):
            strat_root = os.path.join(root, strat)
            # models under this strategy
            models = [d for d in os.listdir(strat_root) if os.path.isdir(os.path.join(strat_root, d))]
            # output dir per strategy
            strat_out = os.path.join(orig_per_ply, base, strat)
            os.makedirs(strat_out, exist_ok=True)
            # override PER_PLY_DIR for this strategy
            globals()['PER_PLY_DIR'] = strat_out
            for model in sorted(models):
                inp = os.path.join(strat_root, model)
                print(f"Processing strategy {strat}, model {model}")
                main(inp, args.max_games, args.output)
        # restore PER_PLY_DIR and exit
        globals()['PER_PLY_DIR'] = orig_per_ply
        sys.exit(0)
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
