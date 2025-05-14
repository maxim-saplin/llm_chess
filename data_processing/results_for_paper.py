import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches # Needed for custom legend
import matplotlib.ticker as mtick  # For formatting y-axis as percentage
import numpy as np
import re
import os

def is_reasoning_model(player_name):
    """
    Checks if a player name matches criteria for reasoning models.

    Args:
        player_name (str): The name of the player/model.

    Returns:
        bool: True if the name matches reasoning criteria, False otherwise.
    """
    if not isinstance(player_name, str):
        return False
    # Check for specific substrings
    if any(term in player_name for term in ['r1', 'thinking', 'phi-4', 'qwq-32b', 'sky-t1', 'gemini-2.5', 'grok-3-mini-beta-low', 'grok-3-mini-beta-high']):
        return True
    # Check for specific prefixes using regex for word boundaries or start of string
    if re.search(r'^(o1|o3|o4)', player_name):
        return True
    return False

def generate_latex_table(data_frame, caption="Players with Zero Win/Loss Ratio (*Reasoning Model)", label="tab:zero_win_loss"):
    """
    Generates a LaTeX table string using booktabs format for the given DataFrame,
    marking reasoning models.

    Args:
        data_frame (pd.DataFrame): DataFrame containing player data (expects 'Player' column).
        caption (str): Caption for the LaTeX table.
        label (str): LaTeX label for referencing the table.

    Returns:
        str: A string containing the LaTeX code for the table.
             Returns an empty string if the DataFrame is empty.
    """
    if data_frame.empty:
        return ""

    # Start LaTeX table environment
    latex_string = "\\begin{table}[htbp]\n"
    latex_string += "  \\centering\n"
    latex_string += f"  \\caption{{{caption}}}\n"
    latex_string += f"  \\label{{{label}}}\n"
    latex_string += "  \\begin{tabular}{l}\n" # Simple table with one left-aligned column
    latex_string += "    \\toprule\n"
    latex_string += "    Player (Model) \\\\\n" # Header
    latex_string += "    \\midrule\n"

    # Add data rows
    for player in data_frame['Player']:
        # Escape special LaTeX characters in player names if necessary (basic example)
        safe_player = player.replace('_', '\\_').replace('%', '\\%').replace('&', '\\&')
        marker = "*" if is_reasoning_model(player) else ""
        latex_string += f"    {safe_player}{marker} \\\\\n" # Add marker if reasoning model

    # End LaTeX table environment
    latex_string += "    \\bottomrule\n"
    latex_string += "  \\end{tabular}\n"
    latex_string += "\\end{table}\n"

    return latex_string

def graph_results(csv_file, win_loss_threshold=1.0, reasoning_color='coral', default_color='skyblue', fig_path="figures_for_paper"):
    """
    Reads CSV results, generates two bar charts for players with win_loss > 0
    (split by a threshold, highlighting reasoning models, y-axis as percentage,
    horizontal line at 100%), and prints LaTeX code for players with win_loss == 0
    (highlighting reasoning models).

    Args:
        csv_file (str): The path to the CSV file.
                        Expected columns: 'Player', 'win_loss'.
        win_loss_threshold (float): The value to split the graphs on for win_loss > 0.
                                    Defaults to 1.0 (corresponds to 100%).
        reasoning_color (str): Color for reasoning model bars.
        default_color (str): Color for other model bars.
    """
    # --- Input Validation ---
    if not isinstance(csv_file, str):
        print(f"Error: csv_file path must be a string. Got: {type(csv_file)}")
        return
    if not os.path.exists(csv_file):
        print(f"Error: File not found at path: {csv_file}")
        return
    if not os.path.isfile(csv_file):
         print(f"Error: Path provided is not a file: {csv_file}")
         return

    try:
        # --- Read CSV Data ---
        df = pd.read_csv(csv_file)

        # --- Data Validation ---
        required_columns = ['Player', 'win_loss']
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            print(f"Error: Missing required columns in CSV: {missing}")
            return

        # --- Data Preparation ---
        plot_data = df[['Player', 'win_loss']].copy()
        plot_data['win_loss'] = pd.to_numeric(plot_data['win_loss'], errors='coerce')
        plot_data.replace([np.inf, -np.inf], np.nan, inplace=True)

        # Handle missing/non-numeric values
        original_rows = len(plot_data)
        plot_data.dropna(subset=['win_loss'], inplace=True)
        rows_dropped = original_rows - len(plot_data)
        if rows_dropped > 0:
            print(f"Warning: Dropped {rows_dropped} rows with invalid or missing 'win_loss' values.")

        if plot_data.empty:
             print("Error: No valid data to process after cleaning.")
             return

        # --- Separate Zero Win/Loss Players ---
        zero_win_loss_players = plot_data[plot_data['win_loss'] == 0].copy()
        positive_win_loss_players = plot_data[plot_data['win_loss'] > 0].copy()

        # --- Generate and Print LaTeX Table for Zero Win/Loss ---
        if not zero_win_loss_players.empty:
            print("\n--- LaTeX Code for Players with Zero Win/Loss Ratio ---")
            latex_table_code = generate_latex_table(zero_win_loss_players,
                                                    caption="Players with Zero Win/Loss Ratio (*Denotes Reasoning Model)",
                                                    label="tab:zero_win_loss")
            print(latex_table_code)
            print("-------------------------------------------------------\n")
        else:
            print("\nNo players found with a zero win/loss ratio.\n")

        # --- Process and Plot Positive Win/Loss Players ---
        if positive_win_loss_players.empty:
            print("No players found with a positive win/loss ratio to plot.")
            return # Exit if no data left for graphs

        # --- Split Positive Data ---
        # Note: Threshold is still based on the original ratio (e.g., 1.0)
        data_below_threshold = positive_win_loss_players[positive_win_loss_players['win_loss'] <= win_loss_threshold].sort_values('win_loss')
        data_above_threshold = positive_win_loss_players[positive_win_loss_players['win_loss'] > win_loss_threshold].sort_values('win_loss')

        # --- Plotting Function ---
        def create_plot(data, title_suffix, figure_number):
            """Helper function to create a single plot with highlighting, % y-axis, and horizontal line."""
            if data.empty:
                print(f"No data to plot for '{title_suffix}'. Skipping this graph.")
                return False # Indicate that plot was not created

            # Determine colors based on reasoning model status
            colors = [reasoning_color if is_reasoning_model(player) else default_color for player in data['Player']]

            fig, ax = plt.subplots(figsize=(14, 8)) # Use subplots to easily access the axes object
            fig.number = figure_number # Assign figure number

            ax.bar(data['Player'], data['win_loss'], color=colors) # Use the generated color list
            # ax.set_xlabel("Player (Model)", fontsize=12)
            ax.set_ylabel("Win/Loss Ratio (%)", fontsize=12) # Update Y-axis label
            # Updated title to include the suffix for clarity between the two plots
            # ax.set_title(f"Win/Loss Ratio per Player", fontsize=14, fontweight='bold')

            # Rotate x-axis labels
            plt.setp(ax.get_xticklabels(), rotation=75, ha='right', fontsize=9)
            plt.setp(ax.get_yticklabels(), fontsize=10)

            # Format Y-axis as percentage
            # xmax=1 means the value 1.0 on the axis corresponds to 100%
            ax.yaxis.set_major_formatter(mtick.PercentFormatter(xmax=1.0))

            # Add horizontal line at 1.0 (which will be displayed as 100%)
            # --- MODIFIED LINE ---
            ax.axhline(y=0.5, color='black', linestyle='--', linewidth=1.5, label='Equal Wins/total_games (50%)') # Made line black and thicker

            ax.grid(axis='y', linestyle='--', alpha=0.7)

            # Create legend patches for model types
            reasoning_patch = mpatches.Patch(color=reasoning_color, label='Reasoning')
            default_patch = mpatches.Patch(color=default_color, label='Non-Reasoning')

            # Build handles list for legend, including the horizontal line
            handles = []
            unique_colors = set(colors)
            if reasoning_color in unique_colors:
                handles.append(reasoning_patch)
            if default_color in unique_colors:
                 handles.append(default_patch)
            # Add the horizontal line's implicit handle to the legend
            handles.append(ax.get_lines()[0]) # Get the handle for the axhline

            if handles: # Add legend if there's anything to show
                 ax.legend(handles=handles)

            # Ensure y-axis starts at 0 (0%)
            ax.set_ylim(bottom=0)

            plt.tight_layout()
            plt.savefig(f"data_processing/{fig_path}/win_loss_ratio_plot_{figure_number}.png", dpi=300) # Save the plot as a PNG file
            plt.savefig(f"data_processing/{fig_path}/win_loss_ratio_plot_{figure_number}.svg", dpi=300) # Save the plot as a SVG file
            return True # Indicate plot was created

        # --- Generate Plots ---
        # Use the title_suffix argument passed to create_plot for dynamic titles
        plot1_created = create_plot(data_below_threshold, f"0 < Ratio <= {win_loss_threshold*100:.0f}%", 1)
        plot2_created = create_plot(data_above_threshold, f"Ratio > {win_loss_threshold*100:.0f}%", 2)

        # --- Display Plots ---
        if plot1_created or plot2_created:
             print("Displaying plots for players with positive win/loss ratios...")
             plt.show()
        else:
             print("No plots were generated for positive win/loss ratios.")


    except (FileNotFoundError, pd.errors.EmptyDataError, pd.errors.ParserError, KeyError, Exception) as e:
         print(f"An error occurred during processing or plotting: {e}")

def graph_scaling_results(csv_file, reasoning_color='coral', default_color='skyblue', fig_path="figures_for_paper"):
    """
    Reads CSV results, generates a line graph for players with scaling results.

    We calculate for the following models: o4-mini (low, medium, high), o3 (low, medium), grok-3-mini (low, high).

    On the x-axis is reasoning effort (low, medium, high) and on the y-axis is win/loss ratio.
    """
    # --- Input Validation ---
    if not isinstance(csv_file, str):
        print(f"Error: csv_file path must be a string. Got: {type(csv_file)}")
        return
    if not os.path.exists(csv_file):
        print(f"Error: File not found at path: {csv_file}")
        return
    if not os.path.isfile(csv_file):
        print(f"Error: Path provided is not a file: {csv_file}")
        return
    try:
        # --- Read CSV Data ---
        df = pd.read_csv(csv_file)
        # --- Data Validation ---
        required_columns = ['Player', 'win_loss']
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            print(f"Error: Missing required columns in CSV: {missing}")
            return
        # --- Data Preparation ---
        plot_data = df[['Player', 'win_loss']].copy()
        plot_data['win_loss'] = pd.to_numeric(plot_data['win_loss'], errors='coerce')
        plot_data.replace([np.inf, -np.inf], np.nan, inplace=True)
        original_rows = len(plot_data)
        plot_data.dropna(subset=['win_loss'], inplace=True)
        rows_dropped = original_rows - len(plot_data)
        if rows_dropped > 0:
            print(f"Warning: Dropped {rows_dropped} rows with invalid or missing 'win_loss' values.")
        if plot_data.empty:
            print("Error: No valid data to process after cleaning.")
            return
        # --- Extract Effort and Model ---
        model_pattern = re.compile(
            r'^(o1(?!-mini|-preview)|o3(?!-mini)|o4-mini|grok-3-mini-beta).*?(low|medium|high)',
            re.IGNORECASE
        )
        plot_data['Effort'] = plot_data['Player'].apply(lambda x: model_pattern.search(x).group(2) if model_pattern.search(x) else None)
        allowed_efforts = ['low', 'medium', 'high']
        plot_data = plot_data[plot_data['Effort'].isin(allowed_efforts)].copy()
        if plot_data.empty:
            print("No scaling results found for effort levels.")
            return
        plot_data['Model'] = plot_data['Player'].apply(lambda x: model_pattern.match(x).group(1) if model_pattern.match(x) else None)
        plot_data.dropna(subset=['Model'], inplace=True)
        if plot_data.empty:
            print("No scaling models found in CSV.")
            return
        # --- Prepare Data for Plotting ---
        # Convert win_loss ratio to percentage
        plot_data['win_loss'] = plot_data['win_loss'] * 100
        # Friendly model names
        plot_data['Model'] = plot_data['Model'].replace({'grok-3-mini-beta': 'Grok 3 Mini'})
        # --- Sort and Categorical Effort ---
        effort_order = ['low', 'medium', 'high']
        plot_data['Effort'] = pd.Categorical(plot_data['Effort'], categories=effort_order, ordered=True)
        plot_data.sort_values(['Model', 'Effort'], inplace=True)
        # --- Plotting with seaborn ---
        import seaborn as sns
        sns.set_theme(style="whitegrid", palette="colorblind")
        # Define plot order for models
        model_order = ['o1', 'o3', 'o4-mini', 'Grok 3 Mini']
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.lineplot(
            data=plot_data,
            x='Effort',
            y='win_loss',
            hue='Model',
            hue_order=model_order,
            marker='o',
            ax=ax,
            estimator=None,
            sort=False,
            palette=sns.color_palette("colorblind"),
            legend='full',
        )
        # Formatting
        ax.set_xlabel("Reasoning Effort", fontsize=12)
        ax.set_ylabel("Win/Loss Ratio (%)", fontsize=12)
        # Format y-axis ticks as percentages
        ax.yaxis.set_major_formatter(mtick.PercentFormatter(xmax=100.0))
        # ax.set_title("Win/Loss Ratio vs Reasoning Effort", fontsize=14, fontweight='bold')
        # Capitalize effort tick labels
        ax.set_xticklabels([label.get_text().capitalize() for label in ax.get_xticklabels()])
        plt.tight_layout()
        # Save and Display
        plt.savefig(f"data_processing/{fig_path}/reasoning_scaling_results_plot.png", dpi=300)
        # now as svg
        plt.savefig(f"data_processing/{fig_path}/reasoning_scaling_results_plot.svg", dpi=300)
        print("Displaying scaling results plot...")
        plt.show()
    except (FileNotFoundError, pd.errors.EmptyDataError, pd.errors.ParserError, KeyError, Exception) as e:
        print(f"An error occurred during processing or plotting: {e}")
    
import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

def graph_loss_reasons(csv_file, models=None, fig_path="figures_for_paper"):
    """
    Reads an aggregate CSV and plots loss-reason percentages for each model,
    then prints a LaTeX table with the new layout.
    """
    if not isinstance(csv_file, str) or not os.path.isfile(csv_file):
        print(f"Error: Invalid CSV file path: {csv_file}")
        return
    table = generate_latex_loss_reason_table(csv_file, models=models)
    print("\n--- LaTeX Table ---\n")
    print(table)
    input("Press Enter to continue...")


def generate_latex_loss_reason_table(
    csv_file,
    models=None,
    top_n=2,
    caption="Loss reason breakdown for top and bottom two reasoning and non-reasoning models.",
    label="tab:loss_reasons"
):
    """
    Builds a single LaTeX table with:
      1) Reasoning Avg
      2) Non-Reasoning Avg
      3) Reasoning: top_n by win rate / bottom_n by win rate
      4) Non-Reasoning: top_n by win rate / bottom_n by win rate

    Columns: Instruction (%) , Draw (%) , MateW (%) , MateB (%).
    Bold = highest value in each column.
    """
    if not os.path.isfile(csv_file):
        return f"% Error: file not found: {csv_file}"
    df = pd.read_csv(csv_file)

    # 1) identify id & win‐rate
    idcol = 'Player' if 'Player' in df.columns else 'model_name'
    if 'win_loss' in df.columns:
        wincol = 'win_loss'
    elif 'win_rate' in df.columns:
        wincol = 'win_rate'
    elif 'player_wins' in df.columns and 'total_games' in df.columns:
        df['win_rate'] = df['player_wins'] / df['total_games']
        wincol = 'win_rate'
    else:
        return "% Error: no win rate column found."

    # 2) required raw columns
    req = [
        'reason_unknown_issue','reason_error',
        'reason_too_many_wrong_actions','reason_max_turns','reason_max_moves',
        'reason_stalemate','reason_insufficient_material',
        'reason_seventyfive_moves','reason_fivefold_repetition',
        'white_checkmates','black_checkmates','total_games'
    ]
    missing = [c for c in req if c not in df.columns]
    if missing:
        return f"% Error: missing columns {missing}"

    # 3) optional model filter
    if models is not None:
        df = df[df[idcol].isin(models)]
    if df.empty:
        return "% Warning: no models to include."

    # 4) compute percentages
    df = df.copy()
    df['Instruction%'] = (
        df['reason_too_many_wrong_actions']
      + df['reason_max_turns']
    ) * 100.0
    df['Draw%'] = (
        df['reason_stalemate']
      + df['reason_insufficient_material']
      + df['reason_seventyfive_moves']
      + df['reason_fivefold_repetition']
      + df['reason_max_moves']
    ) * 100.0
    df['MateW%'] = df['white_checkmates'] / df['total_games'] * 100.0
    df['MateB%'] = df['black_checkmates'] / df['total_games'] * 100.0

    # 5) tag reasoning
    df['IsReasoning'] = df[idcol].apply(is_reasoning_model)

    # helper: slice top/bottom n in a group (drop zero wins)
    def slice_group(sub):
        s = sub[sub[wincol] > 0].sort_values(wincol, ascending=False)
        return s.head(top_n), s.tail(top_n)

    r_df = df[df['IsReasoning']]
    nr_df = df[~df['IsReasoning']]

    r_top, r_bot   = slice_group(r_df)
    nr_top, nr_bot = slice_group(nr_df)

    # 6) overall averages
    def mean_row(sub, name):
        if sub.empty:
            return {'model': name, 'Instruction': 0., 'Draw': 0., 'MateW': 0., 'MateB': 0.}
        return {
            'model': name,
            'Instruction': sub['Instruction%'].mean(),
            'Draw':        sub['Draw%'].mean(),
            'MateW':        sub['MateW%'].mean(),
            'MateB':        sub['MateB%'].mean(),
        }

    avg_r  = mean_row(r_df,  "Reasoning Avg")
    avg_nr = mean_row(nr_df, "Non-Reasoning Avg")

    # 7) collect all entries for bolding logic
    all_entries = [avg_r, avg_nr]
    def collect(chunk, section, pos):
        for _, r in chunk.iterrows():
            all_entries.append({
                'section': section,
                'pos': pos,
                'model': r[idcol],
                'Instruction': r['Instruction%'],
                'Draw':        r['Draw%'],
                'MateW':        r['MateW%'],
                'MateB':        r['MateB%'],
            })
    collect(r_top,   "Reasoning",     "top")
    collect(r_bot,   "Reasoning",     "bottom")
    collect(nr_top,  "Non-Reasoning", "top")
    collect(nr_bot,  "Non-Reasoning", "bottom")

    if len(all_entries) <= 2:
        return "% Warning: insufficient data after filtering zero wins."

    # 8) find column maxima
    max_vals = {
        'Instruction': max(e['Instruction'] for e in all_entries),
        'Draw':        max(e['Draw']       for e in all_entries),
        'MateW':        max(e['MateW']       for e in all_entries),
        'MateB':        max(e['MateB']       for e in all_entries),
    }

    def fmt(val, key):
        s = f"{val:5.1f}"
        return r"\textbf{" + s + "}" if abs(val - max_vals[key]) < 1e-6 else s

    # 9) start LaTeX
    lines = []
    lines.append(r"\begin{table}[ht]")
    lines.append(r"  \centering")
    lines.append(f"  \\caption{{{caption}}}")
    lines.append(f"  \\label{{{label}}}")
    lines.append(r"  \begin{tabular}{lrrrr}")
    lines.append(r"    \toprule")
    lines.append(r"    Model & Instruction (\%) & Draw (\%) & MateW (\%) & MateB (\%) \\")
    lines.append(r"    \midrule")

    # 10) print averages
    for avg in (avg_r, avg_nr):
        lines.append(
            f"    {avg['model']} & "
            f"{fmt(avg['Instruction'], 'Instruction')} & "
            f"{fmt(avg['Draw'],        'Draw')} & "
            f"{fmt(avg['MateW'],        'MateW')} & "
            f"{fmt(avg['MateB'],        'MateB')} \\\\"
        )
    lines.append(r"    \midrule")

    # helper to print each block
    def print_block(section_name):
        lines.append(r"    \addlinespace")
        lines.append(
            f"    \\multicolumn{{5}}{{l}}{{\\textbf{{{section_name} (top {top_n} / bottom {top_n})}}}}\\\\"
        )
        lines.append(r"    \midrule")
        # top n
        for e in all_entries:
            if e.get('section') == section_name and e.get('pos') == 'top':
                lines.append(
                    f"    {e['model']} & "
                    f"{fmt(e['Instruction'], 'Instruction')} & "
                    f"{fmt(e['Draw'],        'Draw')} & "
                    f"{fmt(e['MateW'],        'MateW')} & "
                    f"{fmt(e['MateB'],        'MateB')} \\\\"
                )
        lines.append(r"    \cmidrule(l){1-5}")
        # bottom n
        for e in all_entries:
            if e.get('section') == section_name and e.get('pos') == 'bottom':
                lines.append(
                    f"    {e['model']} & "
                    f"{fmt(e['Instruction'], 'Instruction')} & "
                    f"{fmt(e['Draw'],        'Draw')} & "
                    f"{fmt(e['MateW'],        'MateW')} & "
                    f"{fmt(e['MateB'],        'MateB')} \\\\"
                )
        lines.append(r"    \midrule")

    print_block("Reasoning")
    print_block("Non-Reasoning")

    lines.append(r"    \bottomrule")
    lines.append(r"  \end{tabular}")
    lines.append(r"\end{table}")

    return "\n".join(lines)