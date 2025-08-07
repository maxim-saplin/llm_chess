#!/usr/bin/env python3
"""
Batch script to analyze all JSONs in a folder sequentially.
For each JSON file, calls analyse_game.py with --source json, --json_file, and incremented game_id.
"""
import os
import sys
import argparse
import subprocess
import re
import json


def find_valid_json_dirs():
    """
    Find all directories where ALL JSON files (excluding '_aggregate_results.json')
    contain a 'pgn' key whose value does NOT fully match the template,
    and then sorts the resulting directories by name.
    """
    logs_dir = "_logs"
    valid_dirs = []

    for root, dirs, files in os.walk(logs_dir):
        valid_dir = True
        has_json = False
        for file in files:
            if file.endswith(".json") and file != "_aggregate_results.json":
                has_json = True
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                        template = (
                            r'\[Event "Chess Game"]\n'
                            r'\[Date "\d{4}\.\d{2}\.\d{2}"]\n'
                            r'\[White "Player White"]\n'
                            r'\[Black "Player Black"]\n'
                            r'\[Result "(1-0|0-1|1/2-1/2)"]\n\n'
                            r' (1-0|0-1|1/2-1/2)'
                        )
                        if "pgn" not in data or re.fullmatch(template, data["pgn"]):
                            valid_dir = False
                            break  # At least one JSON doesn't meet the criteria
                except (json.JSONDecodeError, IOError) as e:
                    print(f"Error reading {filepath}: {e}")
                    valid_dir = False
                    break  # Treat as invalid if a file can't be read

        if has_json and valid_dir:
            valid_dirs.append(root)

    # Remove the dirs that are in the following dirs:
    remove_dirs = ["llm_vs_llm", "experiments", "no_reflection", "pgn", "sotckfish_vs_llm", "new/google_gemma-3-4b-it-PGN", "new/o4-mini-2025-04-16-low_pgn"]  # can't use o4-mini as this is the scenario where pgn is provided.
    valid_dirs = [d for d in valid_dirs if not any(d.startswith(os.path.join(logs_dir, r)) for r in remove_dirs)]

    # Sort the valid directories by name
    valid_dirs.sort()

    # Output the result
    print("Valid directories (sorted by name) where all relevant JSON files have a 'pgn' key that does not fully match the template:")
    for d in valid_dirs:
        print(d)

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
    find_valid_json_dirs()
    # main()
