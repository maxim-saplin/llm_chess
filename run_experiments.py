#!/usr/bin/env python3
"""
Script to run multiple chess experiments based on a JSON config.
Each experiment can specify:
  - name: identifier for the experiment
  - num_games: total number of games to run
  - white_player_type: PlayerType enum name for white
  - black_player_type: PlayerType enum name for black
  - symmetric: if true and one side is an LLM, split games equally and swap roles
  - board_representation_mode: BoardRepresentation enum name
  - llm_actions: list of actions (e.g. ["make_move", "get_legal_moves"])
  - default_move_style: e.g. "UCI" or "SAN"
  - see_previous_moves: boolean

Config file example (experiments.json):
{
  "experiments": [
    {
      "name": "llm_vs_stockfish",
      "num_games": 20,
      "white_player_type": "LLM_WHITE",
      "black_player_type": "CHESS_ENGINE_STOCKFISH",
      "symmetric": true,
      "board_representation_mode": "UNICODE_WITH_PGN",
      "llm_actions": ["make_move"],
      "default_move_style": "UCI",
      "see_previous_moves": false
    }
  ]
}
"""
import os
import json
import datetime
import argparse

import llm_chess
from llm_chess import PlayerType, BoardRepresentation
from run_multiple_games import run_games

def load_config(path):
    with open(path, 'r') as f:
        data = json.load(f)
    return data.get('experiments', [])

def swap_player_type(pt: PlayerType) -> PlayerType:
    if pt == PlayerType.LLM_WHITE:
        return PlayerType.LLM_BLACK
    if pt == PlayerType.LLM_BLACK:
        return PlayerType.LLM_WHITE
    return pt

def main():
    parser = argparse.ArgumentParser(description="Run chess experiments from a JSON config file")
    parser.add_argument('-c', '--config', required=True, help='Path to JSON config file')
    args = parser.parse_args()

    experiments = load_config(args.config)
    if not experiments:
        print(f"No experiments found in config file: {args.config}")
        return

    for exp in experiments:
        name = exp.get('name', 'experiment')
        total_games = exp['num_games']
        white_cfg = exp['white_player_type']
        black_cfg = exp['black_player_type']
        symmetric = exp.get('symmetric', False)
        board_repr = exp['board_representation_mode']
        llm_actions = exp['llm_actions']
        default_move_style = exp['default_move_style']
        see_prev = exp['see_previous_moves']

        # Parse enum values
        try:
            white_pt = PlayerType[white_cfg]
            black_pt = PlayerType[black_cfg]
            board_mode = BoardRepresentation[board_repr]
        except KeyError as e:
            print(f"Invalid enum name in experiment '{name}': {e}")
            continue

        # Build assignment list
        assignments = []
        if symmetric and (white_pt.name.startswith('LLM') or black_pt.name.startswith('LLM')):
            half = total_games // 2
            remainder = total_games - half * 2
            # first group: original roles
            assignments.append((white_pt, black_pt, half + remainder))
            # second group: swapped roles
            swapped_white = swap_player_type(black_pt)
            swapped_black = swap_player_type(white_pt)
            assignments.append((swapped_white, swapped_black, half))
        else:
            assignments.append((white_pt, black_pt, total_games))

        # Run each assignment
        for idx, (w_pt, b_pt, games) in enumerate(assignments, start=1):
            # Override llm_chess globals
            llm_chess.white_player_type = w_pt
            llm_chess.black_player_type = b_pt
            llm_chess.board_representation_mode = board_mode
            llm_chess.llm_actions = llm_actions
            llm_chess.DEFAULT_MOVE_STYLE = default_move_style
            llm_chess.SEE_PREVIOUS_MOVES = see_prev

            # Prepare log folder
            ts = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
            tag = f"{w_pt.name}_vs_{b_pt.name}"
            if symmetric and len(assignments) > 1:
                tag = f"{tag}_{idx}"
            log_folder = os.path.join('_logs', 'ablations', name, tag, ts)
            os.makedirs(log_folder, exist_ok=True)

            print(f"Running '{name}' [{idx}/{len(assignments)}]: {w_pt.name} vs {b_pt.name}, games={games}, log_folder={log_folder}")
            run_games(games, log_folder)

if __name__ == '__main__':
    main()