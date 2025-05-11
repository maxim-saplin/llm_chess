#!/usr/bin/env python3
"""
Batch script to analyze all JSONs in a folder sequentially.
For each JSON file, calls analyse_game.py with --source json, --json_file, and incremented game_id.
"""
import os
import sys
import argparse
import subprocess

def main():
    parser = argparse.ArgumentParser(description='Batch analyze JSON game files')
    parser.add_argument('folder', help='Directory with JSON files to analyze')
    parser.add_argument('--start-id', type=int, default=1,
                        help='Starting game_id index (default: 1)')
    args = parser.parse_args()

    folder = args.folder
    if not os.path.isdir(folder):
        print(f"Error: {folder} is not a directory.")
        sys.exit(1)

    files = [f for f in os.listdir(folder) if f.endswith('.json') and f != '_aggregate_results.json']
    files.sort()

    script = os.path.join(os.path.dirname(__file__), 'analyse_game.py')
    python_exec = sys.executable

    for offset, fname in enumerate(files):
        game_id = args.start_id + offset
        json_path = os.path.join(folder, fname)
        print(f"Analyzing {fname} as game {game_id}")
        cmd = [python_exec, script,
               '--source', 'json',
               '--json_file', json_path,
               '--game_id', str(game_id)]
        result = subprocess.run(cmd)
        if result.returncode != 0:
            print(f"Error: analysis failed for {fname}")
        else:
            print(f"Completed game {game_id}")

if __name__ == '__main__':
    main()
