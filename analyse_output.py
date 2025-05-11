import os
import sys
import argparse
import subprocess
import re

def split_games(input_path, output_dir, delimiter='total_cost', start_delimiter=None):
    # Reads all lines
    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    os.makedirs(output_dir, exist_ok=True)
    game_lines = []
    game_idx = 1
    # Choose splitting strategy
    if start_delimiter:
        for line in lines:
            # exact start-of-game marker
            if game_lines and line.strip() == start_delimiter:
                # start of next game, write current
                out_path = os.path.join(output_dir, f'game_{game_idx}.txt')
                with open(out_path, 'w', encoding='utf-8') as out_f:
                    out_f.writelines(game_lines)
                print(f'Wrote: {out_path}')
                game_idx += 1
                game_lines = []
            game_lines.append(line)
    else:
        prev_delim = False
        for line in lines:
            game_lines.append(line)
            if delimiter in line:
                if prev_delim:
                    out_path = os.path.join(output_dir, f'game_{game_idx}.txt')
                    with open(out_path, 'w', encoding='utf-8') as out_f:
                        out_f.writelines(game_lines)
                    print(f'Wrote: {out_path}')
                    game_idx += 1
                    game_lines = []
                    prev_delim = False
                else:
                    prev_delim = True
            else:
                prev_delim = False
    # write last game if any
    if game_lines:
        out_path = os.path.join(output_dir, f'game_{game_idx}.txt')
        with open(out_path, 'w', encoding='utf-8') as out_f:
            out_f.writelines(game_lines)
        print(f'Wrote: {out_path}')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Split a large output.txt into individual game files')
    parser.add_argument('--input', '-i', required=True, help='Path to the big output.txt file')
    parser.add_argument('--output_dir', '-o', required=False, default=None,
                        help='Directory to write separated game files (defaults to a subfolder next to input file)')
    parser.add_argument('--delimiter', '-d', default='total_cost', help='End-of-game delimiter string')
    parser.add_argument('--start_delimiter', '-s', default=None, help='Start-of-game delimiter string (overrides end delimiter)')
    args = parser.parse_args()
    # Determine output directory for split games
    output_dir = args.output_dir
    if not output_dir:
        parent_dir = os.path.dirname(args.input)
        base = os.path.splitext(os.path.basename(args.input))[0]
        output_dir = os.path.join(parent_dir, f"{base}_games")
    split_games(args.input, output_dir, args.delimiter, args.start_delimiter)
    # always run analysis on each split file
    # Path to analyse_game script
    script = os.path.join(os.path.dirname(__file__), 'analyse_game.py')
    python_exec = sys.executable
    # List and sort split game files by numeric suffix
    game_files = [f for f in os.listdir(output_dir) if f.startswith('game_') and f.endswith('.txt')]
    game_files.sort(key=lambda fn: int(re.match(r'game_(\d+)\.txt$', fn).group(1)))
    for fname in game_files:
        inp = os.path.join(output_dir, fname)
        # extract game number
        m = re.match(r'game_(\d+)\.txt$', fname)
        gid = m.group(1) if m else None
        # build command
        cmd = [python_exec, script, '--source', 'output_txt', '--output_txt_file', inp]
        if gid:
            cmd.extend(['--game_id', gid])
        print(f'Analyzing {fname}' + (f' as game {gid}' if gid else ''))
        result = subprocess.run(cmd)
        if result.returncode != 0:
            print(f'Error: analysis failed for {fname}')
