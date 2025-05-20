"""Holds results for paper. Called by get_refined_csv_for_paper.py. Note for Elo we use a separate file: data_processing/elo_graph_for_paper.py"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches # Needed for custom legend
import matplotlib.ticker as mtick  # For formatting y-axis as percentage
import numpy as np
import seaborn as sns
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
    if any(term in player_name.lower() for term in ['low', 'medium', 'high', 'think', 'r1', 'phi 4', 'sky', 'gemini 2.5']):
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

def graph_results(csv_file,
                  win_loss_threshold=1.0,
                  reasoning_color='coral',
                  default_color='skyblue',
                  fig_path="figures_for_paper",
                  orientation='vertical', # Default changed to 'vertical'
                  show_value_labels=False,
                  neurips_style=True):
    """
    Reads CSV results, generates two bar charts for players with win_loss > 0
    (split by a threshold, highlighting reasoning models, y-axis as percentage,
    reference line at 50%), and prints LaTeX code for players with win_loss == 0
    (highlighting reasoning models).

    Args:
        csv_file (str): The path to the CSV file.
                        Expected columns: 'Player', 'win_loss'.
        win_loss_threshold (float): The value to split the graphs on for win_loss > 0.
                                    Defaults to 1.0 (corresponds to 100%).
        reasoning_color (str): Color for reasoning model bars.
        default_color (str): Color for other model bars.
        fig_path (str): Path to save figures.
        orientation (str): Plot orientation, 'horizontal' or 'vertical'. Defaults to 'vertical'.
        show_value_labels (bool): If True, adds value labels to bars. Defaults to False.
        neurips_style (bool): If True, applies styling suitable for NeurIPS. Defaults to True.
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
    if orientation not in ['horizontal', 'vertical']:
        print(f"Error: Invalid orientation '{orientation}'. Choose 'horizontal' or 'vertical'.")
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
        plot_data['Player'] = plot_data['Player'].astype(str)
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

        # --- Separate Zero Win/Loss Players ---
        zero_win_loss_players = plot_data[plot_data['win_loss'] == 0].copy()
        positive_win_loss_players = plot_data[plot_data['win_loss'] > 0].copy()

        # --- Generate and Print LaTeX Table for Zero Win/Loss ---
        if not zero_win_loss_players.empty:
            print("\n--- LaTeX Code for Players with Zero Win/Loss Ratio ---")
            latex_table_code = generate_latex_table(
                zero_win_loss_players[['Player', 'win_loss']],
                caption="Players with Zero Win/Loss Ratio (*Denotes Reasoning Model)",
                label="tab:zero_win_loss"
            )
            print(latex_table_code)
            print("-------------------------------------------------------\n")
        else:
            print("\nNo players found with a zero win/loss ratio.\n")

        # --- Process and Plot Positive Win/Loss Players ---
        if positive_win_loss_players.empty:
            print("No players found with a positive win/loss ratio to plot.")
            return

        sort_ascending = True
        data_below_threshold = positive_win_loss_players[
            positive_win_loss_players['win_loss'] <= win_loss_threshold
        ].sort_values('win_loss', ascending=sort_ascending)
        data_above_threshold = positive_win_loss_players[
            positive_win_loss_players['win_loss'] > win_loss_threshold
        ].sort_values('win_loss', ascending=sort_ascending)

        print(f"Number of players with win/loss ratio <= {win_loss_threshold*100:.0f}%: {len(data_below_threshold)}")
        print(f"Number of players with win/loss ratio > {win_loss_threshold*100:.0f}%: {len(data_above_threshold)}")

        # import pdb; pdb.set_trace() 

        # --- Plotting Function (Revised for Orientation and Features) ---
        def create_plot(data, title_suffix, figure_number, plot_orientation,
                        add_labels, apply_neurips_style):
            if data.empty:
                print(f"No data to plot for '{title_suffix}'. Skipping this graph.")
                return False

            colors = [reasoning_color if is_reasoning_model(player) else default_color for player in data['Player']]
            num_items = len(data['Player'])

            # --- Figure Size ---
            if plot_orientation == 'horizontal':
                bar_thickness_inches = 0.22
                base_fig_height = 1.8
                fig_h = min(max(3.0, base_fig_height + num_items * bar_thickness_inches), 15.0)
                fig_w = 7.0 if num_items > 10 else 6.0
                if apply_neurips_style and fig_w > 3.5: # If neurips style and intended for wider than single column
                    pass # Keep fig_w as calculated for full page horizontal
                elif apply_neurips_style: # Strict single column horizontal
                    fig_w = 3.4
                    # bar_thickness_inches might need adjustment if too many items for this width
            else: # Vertical
                if apply_neurips_style:
                    # For NeurIPS, typically single column width. Taller for ~half page height.
                    fig_w = 3.4 * 2 + 0.5  # Standard single column width
                    fig_h = 4.5 + 0.5 # Taller - aiming for roughly half a page height
                else:
                    # General purpose vertical plot sizing
                    bar_width_inches = 0.3
                    base_fig_width = 4.0
                    calculated_fig_w = base_fig_width + num_items * bar_width_inches
                    fig_w = min(max(6.0, calculated_fig_w), 18.0)
                    fig_h = 6.0 # Taller default for general vertical plots

            fig, ax = plt.subplots(figsize=(fig_w, fig_h))
            fig.number = figure_number

            label_fontsize = 9 if apply_neurips_style else 10
            tick_fontsize = 7 if apply_neurips_style else 8
            legend_fontsize = 7 if apply_neurips_style else 8
            value_label_fontsize = 6 if apply_neurips_style else 7

            if plot_orientation == 'horizontal':
                bars = ax.barh(data['Player'], data['win_loss'], color=colors, height=0.7)
                ax.set_xlabel("Win/Loss (%)", fontsize=label_fontsize)
                plt.setp(ax.get_yticklabels(), ha='right', fontsize=tick_fontsize)
                ax.xaxis.set_major_formatter(mtick.PercentFormatter(xmax=1.0))
                ax.axvline(x=0.5, color='black', linestyle='--', linewidth=1.0, label='50% Ratio')
                ax.grid(axis='x', linestyle=':', linewidth=0.7, alpha=0.7)
                ax.set_xlim(left=0, right=1.05)
                legend_loc = 'lower right'
                if add_labels:
                    for bar in bars:
                        width = bar.get_width()
                        ax.text(width + 0.01, bar.get_y() + bar.get_height() / 2,
                                f'{width:.1%}', ha='left', va='center', fontsize=value_label_fontsize)
            else: # Vertical
                bars = ax.bar(data['Player'], data['win_loss'], color=colors, width=0.8)
                ax.set_ylabel("Win/Loss (%)", fontsize=label_fontsize)
                plt.setp(ax.get_xticklabels(), rotation=60, ha='right', fontsize=tick_fontsize)
                ax.yaxis.set_major_formatter(mtick.PercentFormatter(xmax=1.0))
                ax.axhline(y=0.5, color='black', linestyle='--', linewidth=1.0, label='50% Ratio')
                ax.grid(axis='y', linestyle=':', linewidth=0.7, alpha=0.7)
                ax.set_ylim(bottom=0, top=1.05)
                legend_loc = 'upper left'
                if add_labels:
                    for bar in bars:
                        height = bar.get_height()
                        ax.text(bar.get_x() + bar.get_width() / 2, height + 0.01,
                                f'{height:.1%}', ha='center', va='bottom', fontsize=value_label_fontsize)

            reasoning_patch = mpatches.Patch(color=reasoning_color, label='Reasoning Model')
            default_patch = mpatches.Patch(color=default_color, label='Non-Reasoning Model')
            handles = []
            unique_colors_in_plot = set(colors)
            if reasoning_color in unique_colors_in_plot: handles.append(reasoning_patch)
            if default_color in unique_colors_in_plot: handles.append(default_patch)
            if ax.get_lines(): handles.append(ax.get_lines()[0])
            if handles:
                ax.legend(handles=handles, fontsize=legend_fontsize, loc=legend_loc, frameon=False if apply_neurips_style else True)

            if apply_neurips_style:
                ax.spines['top'].set_visible(False)
                ax.spines['right'].set_visible(False)
                ax.spines['left'].set_linewidth(0.8)
                ax.spines['bottom'].set_linewidth(0.8)
                ax.tick_params(axis='both', which='major', width=0.8, length=3)
            else:
                ax.spines['left'].set_linewidth(1)
                ax.spines['bottom'].set_linewidth(1)

            plt.tight_layout(pad=0.5)

            save_directory = f"data_processing/{fig_path}"
            if not os.path.exists(save_directory):
                os.makedirs(save_directory)
                print(f"Created directory: {save_directory}")

            plot_filename_base = os.path.join(save_directory, f"win_loss_ratio_{plot_orientation}_{figure_number}")
            plt.savefig(f"{plot_filename_base}.png", dpi=300, bbox_inches='tight')
            plt.savefig(f"{plot_filename_base}.svg", format='svg', bbox_inches='tight')
            plt.savefig(f"{plot_filename_base}.pdf", format='pdf', bbox_inches='tight')
            print(f"Saved plot as {plot_filename_base}.png, .svg, and .pdf")
            return True

        plot1_created = create_plot(data_below_threshold, f"0 < Ratio <= {win_loss_threshold*100:.0f}%", 1,
                                    orientation, show_value_labels, neurips_style)
        plot2_created = create_plot(data_above_threshold, f"Ratio > {win_loss_threshold*100:.0f}%", 2,
                                    orientation, show_value_labels, neurips_style)

        if plot1_created or plot2_created:
            print(f"Plots saved in data_processing/{fig_path}/ with {orientation} orientation.")
        else:
            print(f"No plots were generated for {orientation} orientation.")

    except FileNotFoundError:
        print(f"Error: The file {csv_file} was not found.")
    except pd.errors.EmptyDataError:
        print(f"Error: The file {csv_file} is empty.")
    except pd.errors.ParserError:
        print(f"Error: Could not parse the file {csv_file}. Check its format.")
    except KeyError as e:
        print(f"Error: A required column is missing in the CSV: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during processing or plotting: {e}")
        import traceback
        traceback.print_exc()

def create_latex_reason_table(zero_win_loss_df):
    """
    Generates a booktabs LaTeX table from a DataFrame, focusing on 'reason_' columns.

    Args:
        zero_win_loss_df (pd.DataFrame): Input DataFrame with 'Player' and 'reason_...' columns.

    Returns:
        str: A string containing the LaTeX table.
    """
    # Select 'Player' and 'reason_' columns
    reason_cols = [col for col in zero_win_loss_df.columns if col.startswith('reason_')]
    if not reason_cols:
        return "\\textit{No 'reason_' columns found in the DataFrame.}"

    df_selected = zero_win_loss_df[['Player'] + reason_cols].copy()

    # Identify and drop reason_ columns with all zero values
    cols_to_drop = []
    for col in reason_cols:
        # Using np.isclose for robust zero checking with floats
        if np.isclose(df_selected[col], 0).all():
            cols_to_drop.append(col)

    active_reason_cols = [col for col in reason_cols if col not in cols_to_drop]

    if not active_reason_cols:
        return "\\textit{All 'reason_' columns have zero values after filtering.}"

    # Keep only 'Player' and active reason columns
    df_final = df_selected[['Player'] + active_reason_cols].copy() # Use .copy()

    # Convert reason columns to percentage
    for col in active_reason_cols:
        df_final[col] = df_final[col] * 100

    # Prepare new column names for LaTeX
    new_column_names = {'Player': 'Player'}
    for col in active_reason_cols:
        # Remove 'reason_', replace '_', title case
        clean_name = col.replace('reason_', '').replace('_', ' ').title()
        new_column_names[col] = clean_name

    df_final.rename(columns=new_column_names, inplace=True)

    # Define formatters for the numeric columns to ensure one decimal place
    # Get the renamed active reason columns
    renamed_active_reason_cols = [new_column_names[col] for col in active_reason_cols]
    
    formatters = {}
    for col_name in renamed_active_reason_cols:
        formatters[col_name] = lambda x: f"{x:.1f}"
        
    # Define column alignment: 'l' for Player, 'r' for numeric (reason) columns
    num_reason_cols = len(active_reason_cols)
    column_format = 'l' + 'r' * num_reason_cols

    # Generate LaTeX table
    # Ensure caption and label are added outside if needed, or passed as parameters
    latex_table = df_final.to_latex(
        index=False,
        # booktabs=True,
        escape=True, # Escapes LaTeX special characters in Player names
        column_format=column_format,
        formatters=formatters
    )

    return latex_table

def escape_latex_text(text):
    """Robustly escapes LaTeX special characters in a string."""
    if not isinstance(text, str):
        text = str(text)
    # Order of replacements can be important for some sequences
    replacements = [
        ('\\', r'\textbackslash{}'), # Must be first
        ('{', r'\{'),
        ('}', r'\}'),
        ('&', r'\&'),
        ('%', r'\%'),
        ('$', r'\$'),
        ('#', r'\#'),
        ('_', r'\_'),
        ('~', r'\textasciitilde{}'),
        ('^', r'\textasciicircum{}'),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text

def create_latex_reason_table_extended(df):
    """
    Generates a booktabs LaTeX table with grouped 'reason_' columns.
    - win_loss is in pct with 1 decimal.
    - Percentages do not display the '%' symbol (caption should specify units).
    - Reason columns are grouped with multi-column headers and vertical lines.
    - Assumes booktabs package (\toprule, \midrule, \bottomrule, \cmidrule) in LaTeX doc.

    Args:
        df (pd.DataFrame): Input DataFrame with 'Player', 'total_games', 
                           'win_loss', and 'reason_...' columns.

    Returns:
        str: A string containing the LaTeX table.
    """
    # --- 1. Sort the DataFrame ---
    df_sorted = df.copy()
    df_sorted.sort_values(by=['win_loss', 'total_games'], ascending=[False, False], inplace=True)

    # --- 2. Define column groups and identify active reason columns ---
    all_reason_cols_in_df = [col for col in df_sorted.columns if col.startswith('reason_')]

    active_reason_cols_overall = []
    if all_reason_cols_in_df:
        for col in all_reason_cols_in_df:
            # Ensure column exists and then check if not all values are close to zero
            if col in df_sorted.columns and not np.isclose(df_sorted[col].fillna(0), 0).all():
                active_reason_cols_overall.append(col)
    
    # Define the structure and preferred order of reason groups
    group_definitions = {
        'Checkmate': ['reason_checkmate'],
        'Instruction Issues': ['reason_too_many_wrong_actions', 'reason_max_turns'],
        'Draws': ['reason_stalemate', 'reason_insufficient_material', 
                  'reason_seventyfive_moves', 'reason_fivefold_repetition', 'reason_max_moves'],
        # 'Other Issues' will be dynamically populated
    }
    # Explicit order for processing and display of groups
    group_display_order = ['Checkmate', 'Instruction Issues', 'Draws'] 
    
    active_cols_by_group = {} # Stores {group_name: [active_col1, active_col2]}
    final_ordered_reason_cols = [] # Stores original reason col names in final display order
    processed_reasons_in_groups = set()

    # Populate groups based on definitions and active columns
    for group_name in group_display_order:
        defined_cols_for_group = group_definitions.get(group_name, [])
        current_group_active_cols = [col for col in defined_cols_for_group if col in active_reason_cols_overall]
        if current_group_active_cols:
            active_cols_by_group[group_name] = current_group_active_cols
            final_ordered_reason_cols.extend(current_group_active_cols)
            processed_reasons_in_groups.update(current_group_active_cols)

    # Collect any remaining active reasons into 'Other Issues'
    other_active_reasons = [col for col in active_reason_cols_overall if col not in processed_reasons_in_groups]
    if other_active_reasons:
        group_display_order.append('Other Issues') # Add to display order if it has content
        active_cols_by_group['Other Issues'] = other_active_reasons
        final_ordered_reason_cols.extend(other_active_reasons)

    # --- 3. Prepare DataFrame for LaTeX (select and order columns) ---
    cols_for_final_df = ['Player', 'total_games', 'win_loss'] + final_ordered_reason_cols
    df_final = df_sorted[cols_for_final_df].copy()

    # --- 4. Data Transformations (Convert to Percentages) ---
    df_final['win_loss'] = df_final['win_loss'] * 100
    for col in final_ordered_reason_cols:
        df_final[col] = df_final[col] * 100

    # --- 5. Column Name Cleaning (for second header row display) ---
    cleaned_reason_display_names = {} 
    for original_col_name in final_ordered_reason_cols:
        display_name = original_col_name.replace('reason_', '').replace('_', ' ').title()
        if display_name == "Too Many Wrong Actions": display_name = "Wrong Actions"
        if display_name == "Insufficient Material": display_name = "Insuff. Material"
        if display_name == "Seventyfive Moves": display_name = "75 Moves"
        if display_name == "Fivefold Repetition": display_name = "5x Repetition"
        
        cleaned_reason_display_names[original_col_name] = display_name
    
    # --- 6. Formatters (Numeric formatting, no '%' symbol) ---
    formatters = {
        'total_games': lambda x: f"{int(x):d}",
        'win_loss': lambda x: f"{x:.1f}" if pd.notnull(x) else ""
    }
    for original_col_name in final_ordered_reason_cols:
        formatters[original_col_name] = lambda x: f"{x:.1f}" if pd.notnull(x) else ""

    # --- 7. Construct LaTeX Table String ---
    # Initial parts for Player, Total Games, Win/Loss
    header1_parts = ['Player', 'Total Games', 'Win/Loss'] # Top-level headers
    header2_parts = ['', '', '']                         # Sub-level headers (empty for first 3)
    column_format_parts = ['l', 'r', 'r']                # LaTeX column specifiers
    
    cmidrule_definitions = [] # For \cmidrule commands
    current_latex_col_index = 3 # Tracks 1-based column index for LaTeX rules

    first_reason_group_added = False
    for group_name_key in group_display_order: # Iterate in the order they should appear
        if group_name_key in active_cols_by_group and active_cols_by_group[group_name_key]:
            actual_cols_in_this_group = active_cols_by_group[group_name_key]
            num_display_cols_in_group = len(actual_cols_in_this_group)

            if num_display_cols_in_group > 0:
                # Add vertical line separator in column_format_parts before this group
                if not first_reason_group_added:
                    if column_format_parts: column_format_parts[-1] += '|' # After Win/Loss
                    first_reason_group_added = True
                else:
                    if column_format_parts: column_format_parts[-1] += '|' # After previous group
                
                # Top-level header for the group
                header1_parts.append(f"\\multicolumn{{{num_display_cols_in_group}}}{{c}}{{{group_name_key}}}")
                
                # \cmidrule for this group
                cmid_start_col = current_latex_col_index + 1
                cmid_end_col = current_latex_col_index + num_display_cols_in_group
                cmidrule_definitions.append(f"\\cmidrule(lr){{{cmid_start_col}-{cmid_end_col}}}")
                
                # Sub-level headers (cleaned names) and column formats for each column in group
                for original_col_name in actual_cols_in_this_group:
                    header2_parts.append(cleaned_reason_display_names[original_col_name])
                    column_format_parts.append('r') # All reason columns are right-aligned
                    current_latex_col_index += 1
    
    final_latex_column_spec = "".join(column_format_parts)
    
    # Assemble the LaTeX table
    latex_output_lines = ["\\begin{tabular}{" + final_latex_column_spec + "}"]
    latex_output_lines.append("\\toprule")
    latex_output_lines.append(" & ".join(header1_parts) + " \\\\") 
    if cmidrule_definitions: 
        latex_output_lines.append(" ".join(cmidrule_definitions)) 
    latex_output_lines.append(" & ".join(header2_parts) + " \\\\") 
    latex_output_lines.append("\\midrule")

    # Add data rows
    for _, row_data in df_final.iterrows():
        current_row_latex_values = []
        # Player name (escaped)
        current_row_latex_values.append(escape_latex_text(row_data['Player']))
        # Total Games and Win/Loss (formatted)
        current_row_latex_values.append(formatters['total_games'](row_data['total_games']))
        current_row_latex_values.append(formatters['win_loss'](row_data['win_loss']))
        
        # Reason columns (formatted)
        for original_col_name in final_ordered_reason_cols:
            current_row_latex_values.append(formatters[original_col_name](row_data[original_col_name]))
            
        latex_output_lines.append(" & ".join(current_row_latex_values) + " \\\\")

    latex_output_lines.append("\\bottomrule")
    latex_output_lines.append("\\end{tabular}")
    
    return "\n".join(latex_output_lines)

def graph_results(csv_file,
                  win_loss_threshold=1.0,
                  reasoning_color='coral',
                  default_color='skyblue',
                  fig_path="figures_for_paper",
                  orientation='vertical', # Default changed to 'vertical'
                  show_value_labels=False,
                  neurips_style=True):
    """
    Reads CSV results, generates two bar charts for players with win_loss > 0
    (split by a threshold, highlighting reasoning models, y-axis as percentage,
    reference line at 50%), and prints LaTeX code for players with win_loss == 0
    (highlighting reasoning models).

    Args:
        csv_file (str): The path to the CSV file.
                        Expected columns: 'Player', 'win_loss'.
        win_loss_threshold (float): The value to split the graphs on for win_loss > 0.
                                    Defaults to 1.0 (corresponds to 100%).
        reasoning_color (str): Color for reasoning model bars.
        default_color (str): Color for other model bars.
        fig_path (str): Path to save figures.
        orientation (str): Plot orientation, 'horizontal' or 'vertical'. Defaults to 'vertical'.
        show_value_labels (bool): If True, adds value labels to bars. Defaults to False.
        neurips_style (bool): If True, applies styling suitable for NeurIPS. Defaults to True.
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
    if orientation not in ['horizontal', 'vertical']:
        print(f"Error: Invalid orientation '{orientation}'. Choose 'horizontal' or 'vertical'.")
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
        plot_data['Player'] = plot_data['Player'].astype(str)
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

        # --- Separate Zero Win/Loss Players ---
        zero_win_loss_players = plot_data[plot_data['win_loss'] == 0].copy()
        positive_win_loss_players = plot_data[plot_data['win_loss'] > 0].copy()

        # --- Generate and Print LaTeX Table for Zero Win/Loss ---
        if not zero_win_loss_players.empty:
            print("\n--- LaTeX Code for Players with Zero Win/Loss Ratio ---")
            zero_win_loss_df = df[df['win_loss'] == 0].copy()
            # get distribution of reasons why it lost
            print(zero_win_loss_df[['Player', 'win_loss', 'reason_too_many_wrong_actions', 'reason_checkmate', 'reason_stalemate', 'reason_insufficient_material', 'reason_seventyfive_moves', 'reason_fivefold_repetition', 'reason_max_turns', 'reason_unknown_issue', 'reason_max_moves', 'reason_error']])
            # latex_table_code = generate_latex_table(
            #     zero_win_loss_players[['Player', 'win_loss']],
            #     caption="Players with Zero Win/Loss Ratio (*Denotes Reasoning Model)",
            #     label="tab:zero_win_loss"
            # )
            latex_table_code = create_latex_reason_table(zero_win_loss_df)
            print(latex_table_code)
            print("-------------------------------------------------------\n")
            input("Save the table. Press Enter to continue...")
        else:
            print("\nNo players found with a zero win/loss ratio.\n")

        # --- Process and Plot Positive Win/Loss Players ---
        if positive_win_loss_players.empty:
            print("No players found with a positive win/loss ratio to plot.")
            return

        # --- Generate and Print LaTeX Table for >0 Win/Loss ---
        print("\n--- LaTeX Code for Players with Win/Loss Ratio > 0 ---")
        over_zero_win_loss_df = df[df['win_loss'] > 0].copy()
        # get distribution of reasons why it lost
        print(over_zero_win_loss_df[['Player', 'total_games', 'win_loss', 'reason_too_many_wrong_actions', 'reason_checkmate', 'reason_stalemate', 'reason_insufficient_material', 'reason_seventyfive_moves', 'reason_fivefold_repetition', 'reason_max_turns', 'reason_unknown_issue', 'reason_max_moves', 'reason_error']])
        latex_table_code = create_latex_reason_table_extended(over_zero_win_loss_df)
        print(latex_table_code)
        print("-------------------------------------------------------\n")
        input("Save the table. Press Enter to continue...")

        sort_ascending = True
        data_below_threshold = positive_win_loss_players[
            positive_win_loss_players['win_loss'] <= win_loss_threshold
        ].sort_values('win_loss', ascending=sort_ascending)
        data_above_threshold = positive_win_loss_players[
            positive_win_loss_players['win_loss'] > win_loss_threshold
        ].sort_values('win_loss', ascending=sort_ascending)

        print(f"Number of players with win/loss ratio <= {win_loss_threshold*100:.0f}%: {len(data_below_threshold)}")
        print(f"Number of players with win/loss ratio > {win_loss_threshold*100:.0f}%: {len(data_above_threshold)}")

        # --- Plotting Function (Revised for Orientation and Features) ---
        def create_plot(data, title_suffix, figure_number, plot_orientation,
                        add_labels, apply_neurips_style):
            if data.empty:
                print(f"No data to plot for '{title_suffix}'. Skipping this graph.")
                return False

            colors = [reasoning_color if is_reasoning_model(player) else default_color for player in data['Player']]
            num_items = len(data['Player'])

            # import pdb; pdb.set_trace()

            # --- Figure Size ---
            if plot_orientation == 'horizontal':
                # Sizing for horizontal plots (typically full page width if many items)
                bar_thickness_inches = 0.22
                base_fig_height = 1.8
                fig_h = min(max(3.0, base_fig_height + num_items * bar_thickness_inches), 15.0) # Cap height
                fig_w = 7.0 if num_items > 10 else 6.0 # Full NeurIPS text width for many items
                if apply_neurips_style and fig_w <= 3.5: # If trying to fit horizontal in single column
                    fig_w = 3.4 # Strict single column width
                    # Note: bar_thickness_inches might need to be smaller for many items in single column horizontal
            else: # Vertical
                if apply_neurips_style:
                    # For NeurIPS, aiming for full text width, with a moderate height
                    fig_w = 7.0  # Full NeurIPS text width (approx. for two columns)
                    fig_h = 6.0  # Moderate height, adjust as needed
                                 # This is taller than a typical small plot, but not excessively so for a wide plot.
                else:
                    # General purpose vertical plot sizing (can be wider if many items)
                    bar_width_inches = 0.3 # How much width each bar contributes to auto-sizing
                    base_fig_width = 4.0   # Base width for axes, labels etc.
                    # Calculate width based on items, but cap it to avoid excessively wide plots
                    calculated_fig_w = base_fig_width + num_items * bar_width_inches
                    fig_w = min(max(6.0, calculated_fig_w), 18.0) # Min width 6, max 18
                    fig_h = 6.0 # Taller default for general vertical plots

            fig, ax = plt.subplots(figsize=(fig_w, fig_h))
            fig.number = figure_number

            # --- Font Sizes (adjust for NeurIPS if needed, 7pt is often minimum) ---
            multiplier = 1.2
            label_fontsize = (9 if apply_neurips_style else 10) * multiplier
            tick_fontsize = (7 if apply_neurips_style else 8) * multiplier
            legend_fontsize = (7 if apply_neurips_style else 8) * multiplier 
            value_label_fontsize = (6 if apply_neurips_style else 7) * multiplier


            if plot_orientation == 'horizontal':
                bars = ax.barh(data['Player'], data['win_loss'], color=colors, height=0.7)
                ax.set_xlabel("Win/Loss (%)", fontsize=label_fontsize)
                plt.setp(ax.get_yticklabels(), ha='right', fontsize=tick_fontsize) # Player names
                ax.xaxis.set_major_formatter(mtick.PercentFormatter(xmax=1.0))
                ax.axvline(x=0.5, color='black', linestyle='--', linewidth=1.0, label='50% Ratio')
                ax.grid(axis='x', linestyle=':', linewidth=0.7, alpha=0.7) # Lighter grid
                ax.set_xlim(left=0, right=1.05)
                legend_loc = 'lower right'
                if add_labels:
                    for bar in bars:
                        width = bar.get_width()
                        ax.text(width + 0.01, # Position x
                                bar.get_y() + bar.get_height() / 2, # Position y
                                f'{width:.1%}', # Text
                                ha='left', va='center', fontsize=value_label_fontsize)
            else: # Vertical
                bars = ax.bar(data['Player'], data['win_loss'], color=colors, width=0.8) # Bar width
                ax.set_ylabel("Win/Loss (%)", fontsize=label_fontsize)
                # X-tick label rotation and font size are critical for vertical plots with many items
                rotation_angle = 60 if num_items < 30 else 75 # Steeper angle for more items
                if fig_w < 5 and num_items > 20: # Very narrow and many items
                    rotation_angle = 90
                current_tick_fontsize = tick_fontsize
                if num_items > 40 and fig_w < 7: # If many items and not super wide, shrink font
                    current_tick_fontsize = max(5, tick_fontsize -1)


                plt.setp(ax.get_xticklabels(), rotation=rotation_angle, ha='right', fontsize=current_tick_fontsize)
                ax.yaxis.set_major_formatter(mtick.PercentFormatter(xmax=1.0))
                ax.axhline(y=0.5, color='black', linestyle='--', linewidth=1.0, label='50% Ratio')
                ax.grid(axis='y', linestyle=':', linewidth=0.7, alpha=0.7) # Lighter grid
                ax.set_ylim(bottom=0, top=1.05)
                legend_loc = 'upper left'
                if add_labels:
                    for bar in bars:
                        height = bar.get_height()
                        ax.text(bar.get_x() + bar.get_width() / 2, # Position x
                                height + 0.01, # Position y
                                f'{height:.1%}', # Text
                                ha='center', va='bottom', fontsize=value_label_fontsize)

            # --- Legend ---
            reasoning_patch = mpatches.Patch(color=reasoning_color, label='Reasoning Model')
            default_patch = mpatches.Patch(color=default_color, label='Non-Reasoning Model')
            handles = []
            unique_colors_in_plot = set(colors)
            if reasoning_color in unique_colors_in_plot: handles.append(reasoning_patch)
            if default_color in unique_colors_in_plot: handles.append(default_patch)
            # if ax.get_lines(): handles.append(ax.get_lines()[0]) # For the 50% line
            if handles:
                ax.legend(handles=handles, fontsize=legend_fontsize, loc=legend_loc, frameon=False if apply_neurips_style else True)

            # --- NeurIPS Styling: Minimalist approach ---
            if apply_neurips_style:
                ax.spines['top'].set_visible(False)
                ax.spines['right'].set_visible(False)
                ax.spines['left'].set_linewidth(0.8)
                ax.spines['bottom'].set_linewidth(0.8)
                ax.tick_params(axis='both', which='major', width=0.8, length=3)
            else: # Keep default spines or slightly more prominent
                ax.spines['left'].set_linewidth(1)
                ax.spines['bottom'].set_linewidth(1)


            plt.tight_layout(pad=0.5) # Adjust padding

            save_directory = f"data_processing/{fig_path}"
            if not os.path.exists(save_directory):
                os.makedirs(save_directory)
                print(f"Created directory: {save_directory}")

            plot_filename_base = os.path.join(save_directory, f"win_loss_ratio_{plot_orientation}_{figure_number}")
            plt.savefig(f"{plot_filename_base}.png", dpi=300, bbox_inches='tight')
            plt.savefig(f"{plot_filename_base}.svg", format='svg', bbox_inches='tight')
            plt.savefig(f"{plot_filename_base}.pdf", format='pdf', bbox_inches='tight') # Essential for LaTeX
            return True

        # --- Generate Plots ---
        plot1_created = create_plot(data_below_threshold, f"0 < Ratio <= {win_loss_threshold*100:.0f}%", 1,
                                    orientation, show_value_labels, neurips_style)
        plot2_created = create_plot(data_above_threshold, f"Ratio > {win_loss_threshold*100:.0f}%", 2,
                                    orientation, show_value_labels, neurips_style)

        if plot1_created or plot2_created:
            print(f"Plots saved in data_processing/{fig_path}/ with {orientation} orientation.")
            # plt.show() # Uncomment for interactive display
        else:
            print(f"No plots were generated for {orientation} orientation.")

    except FileNotFoundError:
        print(f"Error: The file {csv_file} was not found.")
    except pd.errors.EmptyDataError:
        print(f"Error: The file {csv_file} is empty.")
    except pd.errors.ParserError:
        print(f"Error: Could not parse the file {csv_file}. Check its format.")
    except KeyError as e:
        print(f"Error: A required column is missing in the CSV: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during processing or plotting: {e}")
        import traceback
        traceback.print_exc()

def graph_scaling_results(csv_file,
                          fig_path="figures_for_paper",
                          plot_types=['line']): # Focusing on the refined 'line' plot
    """
    Reads CSV results, generates a refined horizontal line graph with specific adjustments.

    Args:
        csv_file (str): Path to the CSV results file.
        fig_path (str): Subdirectory within 'data_processing/' to save figures.
        plot_types (list): Specifies plot types; we'll focus on 'line'.
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

    valid_plot_types = {'line', 'line_vertical', 'bar', 'heatmap'}
    active_plot_types = [pt for pt in plot_types if pt in valid_plot_types and pt == 'line']
    if not active_plot_types:
        print("No 'line' plot type selected for refinement. Exiting.")
        return

    try:
        # --- Read CSV Data & Initial Prep (Consistent with previous full versions) ---
        df = pd.read_csv(csv_file)
        required_columns = ['Player', 'win_loss']
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            print(f"Error: Missing required columns in CSV: {missing}")
            return

        processed_data = df[['Player', 'win_loss']].copy()
        processed_data['win_loss'] = pd.to_numeric(processed_data['win_loss'], errors='coerce')
        processed_data.replace([np.inf, -np.inf], np.nan, inplace=True)
        processed_data.dropna(subset=['win_loss'], inplace=True)

        model_pattern = re.compile(
            r'^(o1(?!-mini|-preview)|o3(?!-mini)|o4-mini|Grok 3 Mini).*?(low|medium|high)',
            re.IGNORECASE
        )
        def extract_model_effort(player_name):
            match = model_pattern.search(player_name)
            if match:
                return match.group(1).lower(), match.group(2).lower()
            return None, None
        processed_data[['Model_temp', 'Effort_temp']] = processed_data['Player'].apply(
            lambda x: pd.Series(extract_model_effort(x))
        )
        allowed_efforts = ['low', 'medium', 'high']
        processed_data = processed_data[processed_data['Effort_temp'].isin(allowed_efforts)].copy()
        processed_data.dropna(subset=['Model_temp', 'Effort_temp'], inplace=True)

        if processed_data.empty:
            print("No scaling results found after filtering.")
            return

        processed_data['win_loss_pct'] = processed_data['win_loss'] * 100
        processed_data['Model'] = processed_data['Model_temp'].replace({'grok 3 mini': 'Grok 3 Mini'})
        effort_order = ['low', 'medium', 'high']
        processed_data['Effort'] = pd.Categorical(processed_data['Effort_temp'], categories=effort_order, ordered=True)

        predefined_model_order = ['o1', 'o3', 'o4-mini', 'Grok 3 Mini']
        model_order_from_data = processed_data['Model'].unique().tolist()
        model_order = [m for m in predefined_model_order if m in model_order_from_data]


        final_plot_data = processed_data[processed_data['Model'].isin(model_order)].copy()
        final_plot_data['Model'] = pd.Categorical(final_plot_data['Model'], categories=model_order, ordered=True)
        final_plot_data.sort_values(['Model', 'Effort'], inplace=True)

        if final_plot_data.empty:
            print("No data available for the specified models after final filtering.")
            return

        save_dir = os.path.join("data_processing", fig_path)
        os.makedirs(save_dir, exist_ok=True)
        base_plot_filename = "reasoning_scaling_results"
        
        sns.set_theme(style="whitegrid", palette="colorblind")

        # === REFINED HORIZONTAL LINE PLOT (Further Adjustments) ===
        if 'line' in active_plot_types:
            print("\nGenerating Further Refined Horizontal Line Plot...")
            # 1. Further reduce width for less room between x-axis efforts
            fig_line_h, ax_line_h = plt.subplots(figsize=(6, 7.1))  # 7.5, 5.5)) # Example: 7.5 width, 5.5 height
            
            line_plot_obj = sns.lineplot( # Renamed to avoid conflict if you use `line_plot` variable name later
                data=final_plot_data, x='Effort', y='win_loss_pct', hue='Model',
                hue_order=model_order, 
                marker='o', markersize=8,
                linewidth=3.5,
                ax=ax_line_h,
                estimator=None, 
                sort=False, 
                legend=False 
            )
            
            texts_h = []
            # Ensure line_plot_obj.lines is available and matches model_order length
            # This can be tricky if some models have no data and thus no line.
            # A safer way is to map model names to colors from the palette directly.
            palette_colors = sns.color_palette("colorblind", len(model_order))
            model_to_color = {model: palette_colors[i] for i, model in enumerate(model_order)}

            fontsize = 22
            for model_name in model_order:
                model_data = final_plot_data[final_plot_data['Model'] == model_name]
                if not model_data.empty:
                    line_color = model_to_color.get(model_name)
                    last_point = model_data.sort_values('Effort').iloc[-1]
                    effort_categories_numeric = list(range(len(effort_order))) # 0, 1, 2
                    x_text_pos_numeric = effort_categories_numeric[effort_order.index(last_point['Effort'])]
                    
                    # 2. Larger model names
                    texts_h.append(ax_line_h.text(x_text_pos_numeric + 0.02, # Fine-tune offset
                                                last_point['win_loss_pct'] + 0.5, # Fine-tune offset
                                                f" {model_name}",
                                                color=line_color, 
                                                verticalalignment='center',
                                                horizontalalignment='left',
                                                fontsize=fontsize - 1, # Increased font size
                                                weight='bold'))
            
            # if texts_h and 'adjust_text' in globals():
            #     adjust_text(texts_h, ax=ax_line_h,
            #                 arrowprops=dict(arrowstyle='-', color='gray', lw=0.5))

            # ax_line_h.set_title("Model Performance Scaling with Reasoning Effort", fontsize=15, pad=15)
            ax_line_h.set_xlabel("Reasoning Effort", fontsize=fontsize, labelpad=10)
            ax_line_h.set_ylabel("Win/Loss (%)", fontsize=fontsize, labelpad=10)
            ax_line_h.yaxis.set_major_formatter(mtick.PercentFormatter(xmax=100.0))
            
            # 3. Adjusted Y-axis top limit
            min_y_data = final_plot_data['win_loss_pct'].min()
            max_y_data = final_plot_data['win_loss_pct'].max()

            y_axis_bottom = max(0, (min_y_data if pd.notna(min_y_data) else 0) - 2) # Small padding below
            
            # Ensure top doesn't nonsensically exceed 100% by much
            # If max data is 100%, cap y-axis at 100% or 100.5% for a tiny bit of visual space.
            if pd.notna(max_y_data) and max_y_data >= 99.0: # If data reaches near or at 100%
                y_axis_top = 100.5 
            elif pd.notna(max_y_data):
                y_axis_top = min(100.5, max_y_data + 2) # Add small padding but cap near 100
            else: # Fallback if no max_y_data (empty plot_data after filtering?)
                y_axis_top = 100.5
            
            ax_line_h.set_ylim(y_axis_bottom, y_axis_top)

            ax_line_h.set_xticklabels([label.get_text().capitalize() for label in ax_line_h.get_xticklabels()])
            ax_line_h.tick_params(axis='both', which='major', labelsize=18) # Slightly smaller ticks
            
            sns.despine(ax=ax_line_h)
            
            plt.tight_layout(pad=0.5)
            line_h_filename = os.path.join(save_dir, f"{base_plot_filename}_line_final_refined")
            plt.savefig(f"{line_h_filename}.png", dpi=300, bbox_inches='tight')
            plt.savefig(f"{line_h_filename}.svg", dpi=300, bbox_inches='tight')
            print(f"Further refined horizontal line plot saved to {line_h_filename}.png/.svg")
            plt.show()
            plt.close(fig_line_h)

        print("\nSelected plots generated.")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()

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
        'white_checkmates','black_checkmates','total_games',
        'average_moves'
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
    # Add average moves per game
    df['AvgMoves'] = df['average_moves']

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
    # print rank of these selected models like 1/10, 2/10
    print(f"Ranked {top_n} models in each group:")
    print(f"  Reasoning: {r_top[idcol].tolist()} / {r_bot[idcol].tolist()}")
    print(f"There are {len(r_df)} reasoning models in total, the number of which have nonzero wins is {r_df[r_df[wincol] > 0].shape[0]}")
    print(f"  Non-Reasoning: {nr_top[idcol].tolist()} / {nr_bot[idcol].tolist()}")
    print(f"There are {len(nr_df)} non-reasoning models in total, the number of which have nonzero wins is {nr_df[nr_df[wincol] > 0].shape[0]}")
    # import pdb; pdb.set_trace()

    # 6) overall averages
    def mean_row(sub, name):
        if sub.empty:
            return {'model': name, 'Instruction': 0., 'Draw': 0., 'MateW': 0., 'MateB': 0., 'AvgMoves': 0.}
        return {
            'model': name,
            'Instruction': sub['Instruction%'].mean(),
            'Draw':        sub['Draw%'].mean(),
            'MateW':        sub['MateW%'].mean(),
            'MateB':        sub['MateB%'].mean(),
            'AvgMoves':    sub['AvgMoves'].mean(),
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
                'MateW':       r['MateW%'],
                'MateB':       r['MateB%'],
                'AvgMoves':    r['AvgMoves'],
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
        'MateW':       max(e['MateW']      for e in all_entries),
        'MateB':       max(e['MateB']      for e in all_entries),
        'AvgMoves':    max(e.get('AvgMoves', 0) for e in all_entries),
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
    lines.append(r"  \begin{tabular}{lrrr|r|r}")
    lines.append(r"    \toprule")
    lines.append(r"    Model & Instruction (\%) & Draw (\%) & MateW (\%) & MateB (\%) & Avg Moves \\")
    lines.append(r"    \midrule")

    # 10) print averages
    for avg in (avg_r, avg_nr):
        lines.append(
            f"    {avg['model']} & "
            f"{fmt(avg['Instruction'], 'Instruction')} & "
            f"{fmt(avg['Draw'],        'Draw')} & "
            f"{fmt(avg['MateW'],       'MateW')} & "
            f"{fmt(avg['MateB'],       'MateB')} & "
            f"{fmt(avg['AvgMoves'],    'AvgMoves')} \\\\"
        )
    lines.append(r"    \midrule")

    # helper to print each block
    def print_block(section_name):
        lines.append(r"    \addlinespace")
        lines.append(
            # f"    \\multicolumn{{6}}{{l}}{{\\textbf{{{section_name} (top {top_n} / bottom {top_n})}}}}\\\\"
            f"    \\multicolumn{{6}}{{l}}{{\\textbf{{{section_name} }}}}\\\\"
        )
        lines.append(r"    \midrule")
        # top n
        for e in all_entries:
            if e.get('section') == section_name and e.get('pos') == 'top':
                lines.append(
                    f"    {e['model']} & "
                    f"{fmt(e['Instruction'], 'Instruction')} & "
                    f"{fmt(e['Draw'],        'Draw')} & "
                    f"{fmt(e['MateW'],       'MateW')} & "
                    f"{fmt(e['MateB'],       'MateB')} & "
                    f"{fmt(e['AvgMoves'],    'AvgMoves')} \\\\"
                )
        lines.append(r"    \cmidrule(l){1-6}")
        # bottom n
        for e in all_entries:
            if e.get('section') == section_name and e.get('pos') == 'bottom':
                lines.append(
                    f"    {e['model']} & "
                    f"{fmt(e['Instruction'], 'Instruction')} & "
                    f"{fmt(e['Draw'],        'Draw')} & "
                    f"{fmt(e['MateW'],       'MateW')} & "
                    f"{fmt(e['MateB'],       'MateB')} & "
                    f"{fmt(e['AvgMoves'],    'AvgMoves')} \\\\"
                )
        lines.append(r"    \midrule")

    print_block("Reasoning")
    print_block("Non-Reasoning")

    lines.append(r"    \bottomrule")
    lines.append(r"  \end{tabular}")
    lines.append(r"\end{table}")

    return "\n".join(lines)
    
# New function to generate instruction-following metrics table
def generate_latex_instruction_following_table(
    csv_file,
    top_n=5,
    caption="Instruction-Following Metrics for Worst Models",
    label="tab:instruction_following"
):
    """
    Builds a LaTeX table showing wrong action and wrong move rates for the
    worst-performing reasoning and non-reasoning models.
    Columns: Wrong Actions per 1000 Moves, Wrong Moves per 1000 Moves.
    """
    if not os.path.isfile(csv_file):
        return f"% Error: file not found: {csv_file}"
    df = pd.read_csv(csv_file)
    idcol = "Player"
    # Ensure required columns exist
    req_cols = ["wrong_actions_per_1000moves", "wrong_moves_per_1000moves"]
    missing = [c for c in req_cols if c not in df.columns]
    if missing:
        return f"% Error: missing columns {missing}"

    # Tag reasoning models
    df["IsReasoning"] = df[idcol].apply(is_reasoning_model)
    # Ensure win-rate exists
    if 'win_loss' not in df.columns and 'player_wins' in df.columns and 'total_games' in df.columns:
        raise ValueError("Missing 'win_loss' column. Ensure 'player_wins' and 'total_games' are present.")
        # df['win_loss'] = df['player_wins'] / df['total_games'] * 100.0
    # Compute wrong-actions and wrong-moves percentages per move
    df['WrongActions%'] = df['wrong_actions_per_1000moves'] / 100
    df['WrongMoves%'] = df['wrong_moves_per_1000moves'] / 100

    # Select worst models by win rate (lowest win_loss)
    r_df = df[df["IsReasoning"]]
    nr_df = df[~df["IsReasoning"]]
    # Ensure win_loss column exists
    if 'win_loss' not in df.columns:
        raise ValueError("Missing 'win_loss' column. Ensure 'player_wins' and 'total_games' are present.")
        df['win_loss'] = df['player_wins'] / df['total_games'] * 100.0
    # Exclude models with zero wins
    r_df = r_df[r_df['win_loss'] > 0]
    nr_df = nr_df[nr_df['win_loss'] > 0]
    # Sort by win rate and select top_n worst models
    r_worst = r_df.nsmallest(top_n, "win_loss")
    nr_worst = nr_df.nsmallest(top_n, "win_loss")

    # Build LaTeX table with instruction-following metrics
    lines = []
    lines.append(r"\begin{table}[ht]")
    lines.append(r"  \centering")
    lines.append(f"  \\caption{{{caption}}}")
    lines.append(f"  \\label{{{label}}}")
    # Columns: Model, WA(%), WM(%), get_board/Move, get_legal_moves/Move, make_move/Move
    lines.append(r"  \begin{tabular}{lrrrrr}")
    lines.append(r"    \toprule")
    lines.append(r"    Model & WA(%) & WM(%) & get_board/Move & get_legal_moves/Move & make_move/Move \\")
    lines.append(r"    \midrule")
    # Reasoning worst by win rate
    lines.append(r"    \multicolumn{6}{l}{\textbf{Reasoning (worst " + str(top_n) + ")}}\\")
    for _, row in r_worst.iterrows():
        lines.append(
            f"    {row[idcol]} & {row['WrongActions%']:.1f} & {row['WrongMoves%']:.1f} & "
            f"{row['get_board_actions_per_move']:.2f} & {row['get_legal_moves_per_move']:.2f} & {row['make_move_per_move']:.2f} \\\\"
        )
    lines.append(r"    \midrule")
    # Non-Reasoning worst by win rate
    lines.append(r"    \multicolumn{6}{l}{\textbf{Non-Reasoning (worst " + str(top_n) + ")}}\\")
    for _, row in nr_worst.iterrows():
        lines.append(
            f"    {row[idcol]} & {row['WrongActions%']:.1f} & {row['WrongMoves%']:.1f} & "
            f"{row['get_board_actions_per_move']:.2f} & {row['get_legal_moves_per_move']:.2f} & {row['make_move_per_move']:.2f} \\\\"
        )
    lines.append(r"    \bottomrule")
    lines.append(r"  \\end{tabular}")
    lines.append(r"\\end{table}")
    return "\n".join(lines)

def generate_per_ply_metrics_for_table():
    """Using Maxim's final CSV (data_processing/final_data/dragon_vs_llm_aggr.csv) to get the average win rate on each skill level."""
    file_path = 'data_processing/final_data/dragon_vs_llm_aggr.csv'
    df_csv = pd.read_csv(file_path)
    # Data from the LaTeX table
    win_pct_per_ply_grok_table = {1: 74.69, 2: 68.08, 3: 54.62, 4: 50.96, 5: 29.24}
    win_pct_per_ply_o3_table = {1: 75.74, 2: 78.44, 3: 74.85, 4: 63.77, 5: 56.52}

    players_grok_map = {
        1: "lvl-1_vs_grok-3-mini-beta-high", 2: "lvl-2_vs_grok-3-mini-beta-high",
        3: "lvl-3_vs_grok-3-mini-beta-high", 4: "lvl-4_vs_grok-3-mini-fast-beta-high",
        5: "lvl-5_vs_grok-3-mini-fast-beta-high"
    }
    players_o3_map = {
        1: "lvl-1_vs_o3-2025-04-16-low", 2: "lvl-2_vs_o3-2025-04-16-low",
        3: "lvl-3_vs_o3-2025-04-16-low", 4: "lvl-4_vs_o3-2025-04-16-low",
        5: "lvl-5_vs_o3-2025-04-16-low"
    }
    skill_levels = sorted(win_pct_per_ply_grok_table.keys())

    data_for_plot_list = []
    for skill in skill_levels:
        grok_csv_row = df_csv[df_csv['Player'] == players_grok_map[skill]]
        o3_csv_row = df_csv[df_csv['Player'] == players_o3_map[skill]]
        data_for_plot_list.append({
            'Skill': skill,
            'Grok_Win_Rate': grok_csv_row['win_loss'].iloc[0] * 100 if not grok_csv_row.empty else np.nan,
            'O3_Win_Rate': o3_csv_row['win_loss'].iloc[0] * 100 if not o3_csv_row.empty else np.nan,
            'Grok_Win_Percent': win_pct_per_ply_grok_table[skill],
            'O3_Win_Percent': win_pct_per_ply_o3_table[skill]
        })
    plot_df = pd.DataFrame(data_for_plot_list)

    # --- Line Plot with Shaded Differentials (No Shading in Legend) ---
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(13, 5))

    # Font sizes
    axis_label_fontsize = 16
    tick_label_fontsize = 14
    legend_fontsize = 14
    grok_color = 'blue' # Define base color for Grok
    o3_color = 'green'  # Define base color for o3

    # Plotting order changed for legend: Win% then Win Rate
    # Grok 3 Mini Data
    ax.plot(plot_df['Skill'], plot_df['Grok_Win_Percent'], marker='o', linestyle='-', color=grok_color)
    ax.plot(plot_df['Skill'], plot_df['Grok_Win_Rate'], marker='o', linestyle='--', color=grok_color)
    # Add shading for Grok differential - no label for legend
    ax.fill_between(plot_df['Skill'], plot_df['Grok_Win_Rate'], plot_df['Grok_Win_Percent'], color=grok_color, alpha=0.2)

    # o3 Data
    ax.plot(plot_df['Skill'], plot_df['O3_Win_Percent'], marker='s', linestyle='-', color=o3_color)
    ax.plot(plot_df['Skill'], plot_df['O3_Win_Rate'], marker='s', linestyle='--', color=o3_color)
    # Add shading for o3 differential - no label for legend
    ax.fill_between(plot_df['Skill'], plot_df['O3_Win_Rate'], plot_df['O3_Win_Percent'], color=o3_color, alpha=0.2)

    # Customization
    ax.set_xlabel('Skill Level', fontsize=axis_label_fontsize)
    ax.set_ylabel('Percentage (%)', fontsize=axis_label_fontsize)
    ax.tick_params(axis='both', which='major', labelsize=tick_label_fontsize)
    ax.set_xticks(skill_levels)
    ax.set_ylim(20, 105)

    # --- MODIFIED LEGEND ---
    # Create custom legend handles
    # Handles for Models (color and marker)
    from matplotlib.lines import Line2D
    grok_model_handle = Line2D([0], [0], color=grok_color, marker='o', linestyle='None', label='Grok 3 Mini')
    o3_model_handle = Line2D([0], [0], color=o3_color, marker='s', linestyle='None', label='o3')

    # Handles for Line Styles (metric types)
    avg_percent_handle = Line2D([0], [0], color='black', linestyle='-', label='Avg Win%')
    win_rate_handle = Line2D([0], [0], color='black', linestyle='--', label='Win/Loss')

    # Combine handles for the legend
    custom_handles = [grok_model_handle, o3_model_handle, avg_percent_handle, win_rate_handle]

    # Add the legend to the plot
    ax.legend(handles=custom_handles, loc='upper right',  bbox_to_anchor=(0.925, 0.98), fontsize=legend_fontsize, fancybox=True)
    # --- END OF MODIFIED LEGEND ---

    plt.tight_layout() # Adjust layout to prevent clipping
    # save as svg
    # Make sure the directory 'data_processing/figures_for_paper/' exists or change the path
    # For this example, I'll comment out the saving line if the directory might not exist.
    plt.savefig('data_processing/figures_for_paper/per_ply_metrics_skill.svg', format='svg', bbox_inches='tight')
    plt.show() 

def generate_moa_experiments():
    """Using Maxim's `data_processing/final_data/dragon_vs_llm_aggr.csv` to get a bar chart with win_loss on the y axis, setting on the x, and then cost as well.
    Read the csv in as a df:
>>> df.columns
Index(['Player', 'total_games', 'player_wins', 'opponent_wins', 'draws',
       'player_wins_percent', 'player_draws_percent', 'average_moves',
       'moe_average_moves', 'total_moves', 'player_wrong_actions',
       'player_wrong_moves', 'wrong_actions_per_1000moves',
       'wrong_moves_per_1000moves', 'mistakes_per_1000moves',
       'moe_mistakes_per_1000moves', 'player_avg_material',
       'opponent_avg_material', 'material_diff_player_llm_minus_opponent',
       'moe_material_diff_llm_minus_rand', 'completion_tokens_black_per_move',
       'moe_completion_tokens_black_per_move', 'moe_black_llm_win_rate',
       'moe_draw_rate', 'moe_black_llm_loss_rate', 'win_loss', 'moe_win_loss',
       'win_loss_non_interrupted', 'moe_win_loss_non_interrupted',
       'game_duration', 'moe_game_duration', 'games_interrupted',
       'games_interrupted_percent', 'moe_games_interrupted',
       'games_not_interrupted', 'games_not_interrupted_percent',
       'moe_games_not_interrupted', 'average_game_cost',
       'moe_average_game_cost', 'price_per_1000_moves',
       'moe_price_per_1000_moves'],
      dtype='object')
>>> df.iloc[13][['win_loss', 'average_game_cost']]

    Then, get the following Players:
    lvl-1_vs_3x-o4-mini-2025-04-16-low_o4-mini-2025-04-16-medium
    lvl-1_vs_5x-o4-mini-2025-04-16-low_o4-mini-2025-04-16-medium
    lvl-1_vs_o4-mini-2025-04-16-low
    lvl-1_vs_o4-mini-2025-04-16-medium
    lvl-1_vs_o4-mini-2025-04-16-high
    """
    try:
        # Load the dataframe -
        # IMPORTANT: Make sure 'dragon_vs_llm_aggr.csv' is in the same directory
        # as this script, or provide the full path to the file.
        df = pd.read_csv('data_processing/final_data/dragon_vs_llm_aggr.csv')
    except FileNotFoundError:
        print("Error: 'dragon_vs_llm_aggr.csv' not found.")
        print("Please make sure the file is in the correct directory or provide the full path.")
        return

        # Define player groups by their original names
    moa_players_original = [
        'lvl-1_vs_3x-o4-mini-2025-04-16-low_o4-mini-2025-04-16-medium',
        'lvl-1_vs_5x-o4-mini-2025-04-16-low_o4-mini-2025-04-16-medium'
    ]
    standard_players_original = [
        'lvl-1_vs_o4-mini-2025-04-16-low',
        'lvl-1_vs_o4-mini-2025-04-16-medium',
        'lvl-1_vs_o4-mini-2025-04-16-high'
    ]
    all_players_to_filter = moa_players_original + standard_players_original

    # Simplified player names for the plot
    player_name_map = {
        'lvl-1_vs_3x-o4-mini-2025-04-16-low_o4-mini-2025-04-16-medium': '3x MoA',
        'lvl-1_vs_5x-o4-mini-2025-04-16-low_o4-mini-2025-04-16-medium': '5x MoA',
        'lvl-1_vs_o4-mini-2025-04-16-low': 'Low',
        'lvl-1_vs_o4-mini-2025-04-16-medium': 'Medium',
        'lvl-1_vs_o4-mini-2025-04-16-high': 'High'
    }

    # Filter the DataFrame for the specified players
    filtered_df = df[df['Player'].isin(all_players_to_filter)].copy()

    # Map to new display names and calculate Win/Loss Percentage
    filtered_df['DisplayName'] = filtered_df['Player'].map(player_name_map)
    filtered_df['Win/Loss (%)'] = filtered_df['win_loss'] * 100

    # Separate dataframes for each group and sort by cost
    moa_df = filtered_df[filtered_df['Player'].isin(moa_players_original)].sort_values(by='average_game_cost').reset_index(drop=True)
    standard_df = filtered_df[filtered_df['Player'].isin(standard_players_original)].sort_values(by='average_game_cost').reset_index(drop=True)

    # Create the line plot
    plt.style.use('seaborn-v0_8-whitegrid')
    # Attempt to set a cleaner, common sans-serif font
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Liberation Sans', 'Bitstream Vera Sans', 'sans-serif']

    fig, ax = plt.subplots(figsize=(7, 8)) # Adjusted figure size for larger elements

    # Increased line width, marker size, and font sizes
    line_width = 3.5
    marker_size = 10
    annotation_fontsize = 22
    axis_label_fontsize = 23
    tick_label_fontsize = 18
    legend_fontsize = 18


    # Plotting MoA models
    ax.plot(moa_df['average_game_cost'], moa_df['Win/Loss (%)'], marker='o', linestyle='-', color='royalblue', markersize=marker_size, linewidth=line_width, label='MoA')
    # Plotting Standard models
    ax.plot(standard_df['average_game_cost'], standard_df['Win/Loss (%)'], marker='s', linestyle='--', color='forestgreen', markersize=marker_size, linewidth=line_width, label='Single Model')

    texts = []

    # Adding annotations for each point in MoA models with adjusted offsets and no arrows
    for i, row in moa_df.iterrows():
        xytext_offset = (0, 20) # Default offset: above
        ha_align = 'center'
        if row['DisplayName'] == '3x MoA':
            xytext_offset = (90, -5) # Move further down and left
            ha_align = 'right'
        elif row['DisplayName'] == '5x MoA':
            # xytext_offset = (125, 25)  # Move further up and right
            ha_align = 'left'
        
        texts.append(ax.annotate(row['DisplayName'],
                    (row['average_game_cost'], row['Win/Loss (%)']),
                    textcoords="offset points",
                    xytext=xytext_offset,
                    ha=ha_align,
                    va='center',
                    fontsize=annotation_fontsize))

    # Adding annotations for each point in Standard models with adjusted offsets and no arrows
    for i, row in standard_df.iterrows():
        xytext_offset = (0,0) # Default, will be overridden
        ha_align = 'center'
        va_align = 'center'

        if row['DisplayName'] == 'Low':
            xytext_offset = (15, 7)  # Move more to the right, vertically centered
            ha_align = 'left'
        elif row['DisplayName'] == 'Medium':
            xytext_offset = (-40, 5) # Move directly on top, further up
            va_align = 'bottom'
        elif row['DisplayName'] == 'High':
            xytext_offset = (0, -22.5) # Move directly below, further down
            va_align = 'top'
        
        texts.append(ax.annotate(row['DisplayName'],
                    (row['average_game_cost'], row['Win/Loss (%)']),
                    textcoords="offset points",
                    xytext=xytext_offset,
                    ha=ha_align,
                    va=va_align,
                    fontsize=annotation_fontsize))

    # adjust_text(texts) # Uncomment if you install and want to use adjust_text

    # Setting labels with increased font size
    ax.set_xlabel('Average Game Cost ($)', fontsize=axis_label_fontsize)
    ax.set_ylabel('Win/Loss (%)', fontsize=axis_label_fontsize)
    # No title as requested

    # Formatting axes
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
    ax.xaxis.set_major_formatter(mtick.FormatStrFormatter('$%.2f'))

    # Customizing ticks with increased font size
    ax.tick_params(axis='both', which='major', labelsize=tick_label_fontsize, pad=7) # Added padding to ticks

    # Add legend
    ax.legend(fontsize=legend_fontsize, frameon=True, loc='best') # Added frame for better visibility

    # Adjust layout to prevent clipping of labels
    fig.tight_layout(pad=2.0) # Increased padding

    # Save the plot to a file
    new_plot_filename = 'moa_experiments_cost_performance_grouped_plot.png'
    try:
        plt.savefig(new_plot_filename, bbox_inches='tight', dpi=300)
        print(f"Plot saved as {new_plot_filename}")
    except Exception as e:
        print(f"Error saving plot: {e}")

    # Save as SVG
    new_plot_filename_svg = 'data_processing/figures_for_paper/moa_experiments_cost_performance_grouped_plot.svg'
    plt.savefig(new_plot_filename_svg, format='svg', bbox_inches='tight', dpi=300)

    # Display the plot
    plt.show()

    # Print the relevant data for verification
    print("\nData for MoA Models (Sorted by Cost):")
    print(moa_df[['DisplayName', 'average_game_cost', 'Win/Loss (%)']])
    print("\nData for Standard Models (Sorted by Cost):")
    print(standard_df[['DisplayName', 'average_game_cost', 'Win/Loss (%)']])


def generate_winpct_vs_winrate_scatter(refined_csv_file_path):
    """Using Sai's `data_processing/final_data/black_avg_win_pct_overall_plot.csv` along with the refined csv to get win pct (in final_data) vs win loss (in refined_csv_file). We will plot models of the same provider the same color. Remember, refined_csv_file has `Player` column for model and `win_loss` column for win loss.

    black_avg_win_pct_overall_plot.csv:
Model,black.avg_win_pct
gpt-4.1-mini-2025-04-14,26.353368956290375
claude-3-5-haiku-20241022,29.72004938297354
gpt-4.1-2025-04-14,33.661022055456336
grok-3-beta,41.72083011897906
claude-3-7-sonnet-20250219,61.454789846168914
claude-3-7-sonnet-20250219-thinking_budget_2048,74.66005962195726
o4-mini-2025-04-16-low,77.85214495624204
grok-3-mini-beta-low,80.18175318363465
grok-3-mini-beta,84.96954212533515
o4-mini-2025-04-16-medium,85.50243783830182
grok-3-mini-beta-high,87.42515048230356

    """
    try:
        black_avg_win_pct_df = pd.read_csv("data_processing/final_data/black_avg_win_pct_overall_plot.csv")
    except Exception as e:
        print(f"Error reading internal black_avg_win_pct_data: {e}")
        return

    # 2. Read data from refined_csv_file (passed as argument)
    try:
        refined_df = pd.read_csv(refined_csv_file_path)
    except FileNotFoundError:
        print(f"Error: The file '{refined_csv_file_path}' was not found.")
        return
    except pd.errors.EmptyDataError:
        print(f"Error: The file '{refined_csv_file_path}' is empty.")
        return
    except Exception as e:
        print(f"Error reading '{refined_csv_file_path}': {e}")
        return

    # Validate required columns in refined_df
    if 'Player' not in refined_df.columns or 'win_loss' not in refined_df.columns:
        print(f"Error: '{refined_csv_file_path}' must contain 'Player' and 'win_loss' columns.")
        return

    # 3. Merge data
    # Rename 'Player' in refined_df to 'Model' for merging
    refined_df = refined_df.rename(columns={'Player': 'Model'})
    merged_df = pd.merge(black_avg_win_pct_df, refined_df, on='Model', how='inner')

    if merged_df.empty:
        print("Error: No common models found between the two CSV files. The merged DataFrame is empty.")
        print("Models in black_avg_win_pct_overall_plot.csv:", black_avg_win_pct_df['Model'].tolist())
        print("Models in refined_csv_file (as 'Player'):", refined_df['Model'].tolist())
        return

    # 4. Extract provider name
    def get_provider(model_name_series):
        # Ensure model_name_series is treated as a string
        model_name = str(model_name_series).lower()
        if 'gpt' in model_name:
            return 'OpenAI'
        elif 'claude' in model_name:
            return 'Anthropic'
        elif 'grok' in model_name:
            return 'xAI'
        elif 'o4' in model_name or 'o4-' in model_name : # e.g. o4-mini...
            return 'O4Provider' # Placeholder, adjust as needed
        else:
            return 'Other'

    merged_df['Provider'] = merged_df['Model'].apply(get_provider)

    # 5. Create scatter plot
    plt.figure(figsize=(14, 10)) # Increased figure size for better readability
    sns.set_theme(style="whitegrid") # Using a seaborn theme

    scatter_plot = sns.scatterplot(
        data=merged_df,
        x='win_loss',
        y='black.avg_win_pct',
        hue='Provider',
        size='black.avg_win_pct', # Optionally size points by one of the metrics
        sizes=(50, 250), # Range of sizes
        palette='viridis', # Using a different color palette
        legend='full'
    )

    # Add labels and title
    plt.xlabel("Win/Loss Rate (from refined_csv_file)", fontsize=12)
    plt.ylabel("Black Average Win Percentage (from black_avg_win_pct_overall_plot.csv)", fontsize=12)
    plt.title("Win Pct vs. Win/Loss Rate by Model Provider", fontsize=16, fontweight='bold')

    # Annotate points with model names for clarity
    for i in range(merged_df.shape[0]):
        plt.text(
            x=merged_df['win_loss'].iloc[i] * 1.01,  # Slight offset for x
            y=merged_df['black.avg_win_pct'].iloc[i] * 1.01,  # Slight offset for y
            s=merged_df['Model'].iloc[i],
            fontdict=dict(color='black', size=9, style='italic'),
            bbox=dict(facecolor='white', alpha=0.5, pad=0.2, edgecolor='none') # Add a faint background to text
        )

    plt.legend(title='Provider', bbox_to_anchor=(1.05, 1), loc='upper left') # Move legend outside plot
    plt.tight_layout(rect=[0, 0, 0.85, 1]) # Adjust layout to make space for legend

    # Save the plot to a file
    plot_filename = "winpct_vs_winrate_scatter.png"
    try:
        plt.savefig(plot_filename)
        print(f"Scatter plot saved as {plot_filename}")
        # plt.show() # This would display the plot if running in an interactive environment
    except Exception as e:
        print(f"Error saving plot: {e}")


    print("\n--- Merged Data Used for Plotting ---")
    print(merged_df)
    print("------------------------------------")

if __name__ == "__main__":
    generate_per_ply_metrics_for_table()
    # generate_moa_experiments()