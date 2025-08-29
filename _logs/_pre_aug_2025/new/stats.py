import os
import sys
from prettytable import PrettyTable

# Import the required functions from the codebase
sys.path.insert(0, os.path.abspath("."))
from data_processing.get_refined_csv import load_game_log
from llm_chess import TerminationReason

# Define the root directory where logs are stored
root_dir = "./_logs/new"

includes = [] # ["o3", "o4"] # Example values

# Get all direct child folders
child_folders = [
    d for d in os.listdir(root_dir)
    if os.path.isdir(os.path.join(root_dir, d)) and not d.startswith(".") and (not includes or any(inc in d for inc in includes))
]

# Initialize a dictionary to store counts and material diffs for each folder
folder_counts = {}

# Process each folder
for folder in child_folders:
    folder_path = os.path.join(root_dir, folder)
    
    # Initialize counters for this folder
    reason_counts = {reason.value: 0 for reason in TerminationReason}
    total_logs = 0
    black_wins = 0
    black_losses = 0
    draws = 0

    # For material diff
    material_diffs = []
    material_diffs_no_error = []
    
    # Walk through all files in the folder
    for subdir, _, files in os.walk(folder_path):

        for file in files:
            if file.endswith(".json") and not file.endswith("_aggregate_results.json"):
                file_path = os.path.join(subdir, file)
                try:
                    log = load_game_log(file_path)

                    # Count the termination reason
                    if log.reason in reason_counts:
                        reason_counts[log.reason] += 1
                    # Count black player wins
                    if log.winner == "Player_Black" or log.winner == "NoN_Synthesizer":
                        black_wins += 1
                    # Count black player losses (white wins)
                    if log.winner == "Chess_Engine_Dragon_White":
                        black_losses += 1
                    # Count draws (NONE winner and not error)
                    if (
                        log.winner == "NONE"
                        and log.reason != TerminationReason.ERROR.value
                    ):
                        draws += 1
                    # Material diff (black - white)
                    if hasattr(log, "material_count") and "black" in log.material_count and "white" in log.material_count:
                        diff = log.material_count["black"] - log.material_count["white"]
                        material_diffs.append(diff)
                        if log.reason != TerminationReason.ERROR.value:
                            material_diffs_no_error.append(diff)
                    total_logs += 1
                except Exception as e:
                    print(f"Error loading {file_path}: {e}")
    
    # Compute averages
    avg_material_diff = sum(material_diffs) / len(material_diffs) if material_diffs else 0
    avg_material_diff_no_error = sum(material_diffs_no_error) / len(material_diffs_no_error) if material_diffs_no_error else 0

    # Store the counts and material diffs for this folder
    folder_counts[folder] = {
        "total": total_logs,
        "black_wins": black_wins,
        "black_losses": black_losses,
        "draws": draws,
        "reasons": reason_counts,
        "avg_material_diff": avg_material_diff,
        "avg_material_diff_no_error": avg_material_diff_no_error,
    }

# Create a pretty table for output
table = PrettyTable()

# Define columns: folder name, total, error count, black win rate, win rate excl. errors, loss rate, loss rate excl. errors, material diff, material diff excl. errors
table.field_names = [
    "Folder",
    "Tota logs",
    "Errors",
    "Black Win Rate (%)",
    # "Win Rate Excl. Errors (%)",
    # "Black Loss Rate (%)",
    # "Loss Rate Excl. Errors (%)",
    # "Material Diff",
    # "Material Diff Excl. Errors",
]

# Sort the folders alphabetically before adding to the table
for folder in sorted(folder_counts.keys()):
    counts = folder_counts[folder]
    error_count = counts["reasons"].get(TerminationReason.ERROR.value, 0)
    win_rate = (counts["black_wins"] / counts["total"] * 100) if counts["total"] > 0 else 0
    loss_rate = (counts["black_losses"] / counts["total"] * 100) if counts["total"] > 0 else 0

    # Calculate win rate and loss rate excluding error games
    non_error_games = counts["total"] - error_count
    win_rate_excl_errors = (counts["black_wins"] / non_error_games * 100) if non_error_games > 0 else 0
    loss_rate_excl_errors = (counts["black_losses"] / non_error_games * 100) if non_error_games > 0 else 0

    row = [
        folder,
        counts["total"],
        error_count,
        f"{win_rate:.2f}",
        # f"{win_rate_excl_errors:.2f}",
        # f"{loss_rate:.2f}",
        # f"{loss_rate_excl_errors:.2f}",
        # f"{counts['avg_material_diff']:.2f}",
        # f"{counts['avg_material_diff_no_error']:.2f}",
    ]
    table.add_row(row)

# Print the table
print(table)