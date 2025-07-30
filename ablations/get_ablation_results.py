"""Get results of all ablation experiments and place in a booktabs latex table."""

import json
import os
import re
from collections import defaultdict

def extract_info_from_path(file_path):
    """
    Extracts the model name and setting from the file path.
    Assumes a path structure like:
    './<setting>/<model_name>/<player_vs_llm>/<timestamp>/_aggregate_results.json'
    or similar variations where the setting is the first main directory and
    model_name is the directory after that.

    Args:
        file_path (str): The full path to the JSON file.

    Returns:
        tuple: (model_name, setting) or (None, None) if not found.
    """
    parts = file_path.split(os.sep)
    # Expected structure:
    # parts[-5] is likely the setting (e.g., 'llm_vs_random_only_make_move_previous_moves')
    # parts[-4] is likely the model name (e.g., 'grok-3-mini-beta')

    if len(parts) >= 5:
        setting = parts[-5] # Or adjust based on your actual depth
        model_name = parts[-4] # Or adjust
        return model_name, setting
    return None, None


def get_llm_player_info(data):
    """
    Determines if the LLM was player_white or player_black and returns its stats.
    """
    if data.get("player_white", {}).get("model"): # Check if 'model' field is non-empty
        return "white", data["player_white"], data["white_wins"]
    elif data.get("player_black", {}).get("model"):
        return "black", data["player_black"], data["black_wins"]
    # Fallback if "model" key is empty but name might indicate LLM
    elif "LLM" in data.get("player_white", {}).get("name", "").upper() or \
         data.get("player_white", {}).get("name", "") not in ["Random_Player", "RANDOM_PLAYER"]:
        return "white", data["player_white"], data["white_wins"]
    elif "LLM" in data.get("player_black", {}).get("name", "").upper() or \
         data.get("player_black", {}).get("name", "") not in ["Random_Player", "RANDOM_PLAYER"]:
        return "black", data["player_black"], data["black_wins"]
    return None, None, 0


def generate_latex_table(aggregated_results):
    """
    Generates a LaTeX table string using booktabs.

    Args:
        aggregated_results (dict): A dictionary of the form
                                   {model: {setting: win_rate, ...}, ...}
    """
    if not aggregated_results:
        return "\\textit{No data to display.}"

    # Get all unique settings (columns) and sort them
    all_settings = sorted(list(set(setting for model_data in aggregated_results.values() for setting in model_data)))
    # Get all unique models (rows) and sort them
    all_models = sorted(list(aggregated_results.keys()))

    # Start LaTeX table
    latex_string = "\\begin{table}[htbp]\n"
    latex_string += "\\centering\n"
    latex_string += "\\caption{LLM Win Rates}\n"
    latex_string += "\\label{tab:llm_win_rates}\n"
    # Define columns: Model + one for each setting
    column_format = "l" + "c" * len(all_settings) # l for left-aligned model name, c for centered win rates
    latex_string += f"\\begin{{tabular}}{{{column_format}}}\n"
    latex_string += "\\toprule\n"

    # Header row
    header = "Model"
    for setting in all_settings:
        # Make setting names more LaTeX friendly (replace underscores)
        header += f" & {setting.replace('_', ' ').title().replace('Llm Vs Random', '').strip()}"
    latex_string += header + " \\\\\n"
    latex_string += "\\midrule\n"

    # Get max score per model so we can bold the best score across settings
    max_scores = {model: max(aggregated_results[model].values()) for model in all_models}

    # Data rows
    for model in all_models:
        row = model.replace('_', '\\_') # Escape underscores in model names for LaTeX
        for setting in all_settings:
            win_rate = aggregated_results.get(model, {}).get(setting)
            if win_rate is not None:
                pct_win_rate = win_rate * 100
                if win_rate == max_scores[model]:
                    row += f" & \\textbf{{{pct_win_rate:.1f}}}"
                else:
                    row += f" & {pct_win_rate:.1f}" # Format to 2 decimal places
            else:
                row += " & --" # Placeholder if no data for this model/setting
        latex_string += row + " \\\\\n"

    latex_string += "\\bottomrule\n"
    latex_string += "\\end{tabular}\n"
    latex_string += "\\end{table}\n"

    return latex_string

def main(root_dir):
    """
    Main function to find JSONs, parse them, and generate the LaTeX table.
    """
    aggregated_results = defaultdict(dict) # {model: {setting: win_rate}}
    file_paths = []

    dir_paths = [
        # For original NeurIPS submission:
        # "llm_vs_random_previous_moves/o4-mini/RANDOM_PLAYER_vs_LLM_BLACK/2025-05-03-20-16-03",
        # "llm_vs_random_previous_moves/grok-3-mini-beta/RANDOM_PLAYER_vs_LLM_BLACK/2025-05-05-11-57-01",
        # "llm_vs_random_always_legal_moves/o4-mini/RANDOM_PLAYER_vs_LLM_BLACK/2025-05-03-20-16-28",
        # "llm_vs_random_always_legal_moves/grok-3-mini-beta/RANDOM_PLAYER_vs_LLM_BLACK/2025-05-05-11-25-50",
        # "llm_vs_random_always_board_state/o4-mini/RANDOM_PLAYER_vs_LLM_BLACK/2025-05-03-20-17-01",
        # "llm_vs_random_always_board_state/grok-3-mini-beta/RANDOM_PLAYER_vs_LLM_BLACK/2025-05-05-11-28-09",
        # "llm_vs_random_only_make_move/o4-mini/RANDOM_PLAYER_vs_LLM_BLACK/2025-05-04-18-09-44",
        # "llm_vs_random_only_make_move/grok-3-mini-beta/RANDOM_PLAYER_vs_LLM_BLACK/2025-05-05-11-17-02",
        # "llm_vs_random_only_make_move_previous_moves/grok-3-mini-beta/RANDOM_PLAYER_vs_LLM_BLACK/2025-05-06-10-20-00",
        # "llm_vs_random_only_make_move_previous_moves/o4-mini/RANDOM_PLAYER_vs_LLM_BLACK/2025-05-08-08-47-26",
        # "llm_vs_random_ascii/o4-mini/RANDOM_PLAYER_vs_LLM_BLACK/2025-05-08-08-45-58",
        # "llm_vs_random_ascii/grok-3-mini-beta/RANDOM_PLAYER_vs_LLM_BLACK/2025-05-06-21-27-29",
        # "llm_vs_random_fen/o4-mini/RANDOM_PLAYER_vs_LLM_BLACK/2025-05-08-08-46-29",
        # "llm_vs_random_fen/grok-3-mini-beta/RANDOM_PLAYER_vs_LLM_BLACK/2025-05-06-21-27-25",
        # "llm_white_vs_random/o4-mini/LLM_WHITE_vs_RANDOM_PLAYER/2025-05-09-10-03-48",
        # "llm_white_vs_random/grok-3-mini-beta/LLM_WHITE_vs_RANDOM_PLAYER/2025-05-09-14-15-32",
        # "llm_vs_random_no_legal_moves_fen/o4-mini/RANDOM_PLAYER_vs_LLM_BLACK/2025-05-14-20-39-54/",
        # "llm_vs_random_no_legal_moves_fen/grok-3-mini-fast-beta/RANDOM_PLAYER_vs_LLM_BLACK/2025-05-14-13-24-43/",
        # For NeurIPS rebuttals:
        "llm_vs_random_realistic/o4-mini/RANDOM_PLAYER_vs_LLM_BLACK/2025-07-24-19-29-57",
        "llm_vs_random_realistic/grok-3-mini-beta/RANDOM_PLAYER_vs_LLM_BLACK/2025-07-27-22-19-44",
        ("llm_black_vs_default_dragon/grok-3-mini-beta/CHESS_ENGINE_DRAGON_vs_LLM_BLACK/2025-07-28-11-58-11", "Skill 1 (default)"),
        ("llm_vs_dragon_only_make_move/grok-3-mini-beta/CHESS_ENGINE_DRAGON_vs_LLM_BLACK/2025-07-26-21-07-17", "Skill 1"),
        ("llm_vs_dragon_only_make_move/grok-3-mini-beta/CHESS_ENGINE_DRAGON_vs_LLM_BLACK/2025-07-27-10-08-46", "Skill 2"),
        ("llm_vs_dragon_only_make_move/grok-3-mini-beta/CHESS_ENGINE_DRAGON_vs_LLM_BLACK/2025-07-26-21-06-58", "Skill 3"),
        ("llm_vs_dragon_only_make_move/grok-3-mini-beta/CHESS_ENGINE_DRAGON_vs_LLM_BLACK/2025-07-27-10-20-42", "Skill 4"),
        ("llm_vs_dragon_only_make_move/grok-3-mini-beta/CHESS_ENGINE_DRAGON_vs_LLM_BLACK/2025-07-26-10-50-27", "Skill 5"),
        ("llm_black_vs_default_dragon/grok-3-mini-beta/CHESS_ENGINE_DRAGON_vs_LLM_BLACK/2025-07-28-11-56-23", "Skill 5 (default)"),
    ]

    # We know there is _aggregate_results.json in each of these folders
    for dir_path in dir_paths:
        if isinstance(dir_path, tuple):
            dir_path, additional_info = dir_path
        file_path = os.path.join("../_logs/ablations", dir_path, "_aggregate_results.json")
        if os.path.exists(file_path):
            file_paths.append(file_path)
        else:
            print(f"File not found: {file_path}")
            continue
        with open(file_path, 'r') as f:
            data = json.load(f)
        model_name, setting = extract_info_from_path(file_path)
        if model_name is None or setting is None:
            print(f"Could not extract model name or setting from path: {file_path}")
            continue
        player_color, player_info, wins = get_llm_player_info(data)
        total_games = data["total_games"]
        win_rate = None  # wins / total_games if total_games > 0 else 0  # NOTE: We use win/loss instead.
        white_rand_wins = data["white_wins"] if player_color == "black" else data["black_wins"]
        win_loss = (
            ((wins - white_rand_wins) / total_games) / 2 + 0.5
            if total_games > 0
            else 0.5
        )
        aggregated_results[model_name][setting] = win_loss
        if "additional_info" in locals():
            setting += f" ({additional_info})"
        print(f"Model: {model_name}, Setting: {setting}, Win/Loss: {win_loss:.2f}")

    # Generate LaTeX table
    latex_table = generate_latex_table(aggregated_results)
    print(latex_table)

if __name__ == "__main__":
    root_dir = "./"  # Adjust this to your root directory if needed
    main(root_dir)
