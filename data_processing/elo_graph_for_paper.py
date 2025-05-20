import re
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
# from datetime import datetime # Not strictly needed if we remove date parsing from names

# New datastring
data_string = """
o3 (low) (197 games) : 758.4177303490669 +/- 65.20379872056112
Grok 3 Mini (high) (169 games) : 456.34546138931 +/- 59.3001144878849
o3-mini (low) (33 games) : -85.30158865115494 +/- 192.4918355141965
o3-mini (medium) (38 games) : 210.74536921523534 +/- 113.00108793958876
o3-mini (high) (57 games) : 438.517459864085 +/- 94.90804947726514
o4-mini (low) (33 games) : 140.30886559296286 +/- 128.97140348468602
o4-mini (medium) (40 games) : 311.1066926050366 +/- 107.97551285047572
o4-mini (high) (49 games) : 407.608667421743 +/- 100.51652169237231
"""

data = []
# Regex to capture the model name, games, performance, and confidence interval
regex = re.compile(r"^(.*?)\s*\((\d+)\s*games\)\s*:\s*(-?[\d\.]+)\s*\+/-\s*([\d\.]+)$")

for line in data_string.strip().split('\n'):
    match = regex.match(line)
    if match:
        model_name_full, games, performance, confidence = match.groups()
        # Use the model name as captured, stripping whitespace. No date parsing needed for this data.
        display_name = model_name_full.strip()
        
        data.append({
            "model_name": display_name,
            "games": int(games),
            "performance": float(performance), # This will be treated as Elo
            "confidence": float(confidence)
        })
    else:
        print(f"Warning: Could not parse line: {line}")

df = pd.DataFrame(data)
df_sorted = df.sort_values(by="performance", ascending=False).reset_index(drop=True)

# --- Plotting ---
# Adjust font sizes for paper readiness
plt.rcParams.update({'font.size': 10}) # Default font size

# Figure size: width, height in inches. Adjust for your paper's column width.
# Made it taller to accommodate more items or larger text comfortably.
fig, ax = plt.subplots(figsize=(8.5, 5.5)) # Example: 6.5 inches wide, 5.5 inches tall
fig.patch.set_facecolor('#FFFFFF') 
ax.set_facecolor('#FFFFFF') 

# Define colors
error_bar_color = '#BDBDBD' # Lighter Grey (Material Grey 400) - per last user preference
text_color = '#212121'      # Darker text color for better readability (almost black)
axis_color = '#757575'      # Slightly darker axis lines
grid_color = '#E0E0E0' 
title_color = '#000000'     # Black title

num_bars = len(df_sorted)
colormap = plt.cm.get_cmap('tab10', num_bars) # tab10 for good distinct colors, cycles if >10 bars
bar_colors = [colormap(i) for i in range(num_bars)]

y_pos = np.arange(len(df_sorted))
bars = ax.barh(y_pos, df_sorted["performance"], 
               xerr=df_sorted["confidence"], 
               align='center', 
               color=bar_colors, 
               height=0.7, # Adjust bar height/thickness
               capsize=3, 
               error_kw=dict(ecolor=error_bar_color, elinewidth=1.5, capthick=1.2))

ax.set_yticks(y_pos)
ax.set_yticklabels(df_sorted["model_name"], fontsize=10) # Y-axis label font size
ax.invert_yaxis()  

# ax.set_title("Elo Comparison", fontsize=14, color=title_color, pad=15, loc='center') # Centered title
ax.set_xlabel("Elo Rating", fontsize=12, color=text_color, labelpad=10) # X-axis label font size

# Spines
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_color(axis_color)
ax.spines['left'].set_linewidth(0.8)
ax.spines['bottom'].set_color(axis_color)
ax.spines['bottom'].set_linewidth(0.8)

# Ticks
ax.tick_params(axis='x', colors=text_color, labelsize=10) # X-axis tick label font size
ax.tick_params(axis='y', colors=text_color, length=0) 
ax.xaxis.grid(True, linestyle='-', alpha=0.5, color=grid_color, linewidth=0.6)
ax.set_axisbelow(True) 

max_val_with_error = (df_sorted["performance"] + df_sorted["confidence"]).max()
min_val_with_error = (df_sorted["performance"] - df_sorted["confidence"]).min()

# Adjust x-axis limits based on data range to provide space for annotations
# Consider a fixed padding or a percentage of the range
data_range = max_val_with_error - min_val_with_error
padding_perc = 0.05 # Percentage padding on each side for values
text_space_perc = 0.25 # Additional percentage of data range for text on the right

# Sensible defaults if data_range is zero (e.g. single point)
if data_range == 0:
    data_range = abs(max_val_with_error * 0.2) if max_val_with_error != 0 else 10
    text_space_perc = 0.5


left_limit = min_val_with_error - data_range * padding_perc
# If all values are positive, and left_limit without padding is near zero, consider starting at zero.
if min_val_with_error >= 0 and (min_val_with_error - data_range * padding_perc) < (0.1 * data_range):
     left_limit = -data_range * 0.02 # Allow a tiny bit left of zero for visual balance or if bars are near zero
     if len(df_sorted[df_sorted["performance"] <0]) == 0 and min_val_with_error > 0: # if truly all positive
        left_limit = -max(abs(df_sorted["performance"].min() * 0.1), data_range * 0.02)


right_limit = max_val_with_error + data_range * text_space_perc # More space on the right for text

# Ensure a minimum visible range if all values are zero or very close
if left_limit == 0 and right_limit == 0:
    left_limit = -10
    right_limit = 10
elif left_limit > right_limit: # safety if min > max after padding
    left_limit, right_limit = right_limit, left_limit # swap
    right_limit += data_range * text_space_perc # re-add text space

ax.set_xlim(left_limit, right_limit)

for i, (bar, perf, conf) in enumerate(zip(bars, df_sorted["performance"], df_sorted["confidence"])):
    error_bar_max_x = perf + conf
    current_xlim = ax.get_xlim()
    plot_width_for_text_offset = current_xlim[1] - current_xlim[0]
    
    # Position text slightly to the right of the error bar
    text_label_x = error_bar_max_x + (plot_width_for_text_offset * 0.010) # Reduced offset
    ha = 'left'

    # Simple check if text might overflow (less aggressive than before)
    # A more robust solution would be to get text width, but this is an approximation
    # Check if the starting point of text plus an estimated length goes beyond 98% of xlim
    estimated_text_length_fraction = 0.15 # Assume text takes up to 15% of plot width (can be tuned)
    if text_label_x + (plot_width_for_text_offset * estimated_text_length_fraction) > current_xlim[1] * 0.99:
        # If likely to overflow, place to the left of the bar's start (performance - confidence)
        text_label_x = perf - conf - (plot_width_for_text_offset * 0.010)
        ha = 'right'
    
    ax.text(text_label_x, 
            bar.get_y() + bar.get_height()/2, 
            f"{perf:.2f} ± {conf:.2f}", 
            va='center', 
            ha=ha, 
            fontsize=9, # Annotation text font size (can be 9 or 10)
            color=text_color)

# Adjust layout to prevent labels from being cut off
plt.tight_layout(pad=1.0, rect=[0.01, 0.01, 0.99, 0.97]) # rect=[left, bottom, right, top]

# Example of saving the figure for a paper
# plt.savefig("elo_comparison_plot.png", dpi=300, bbox_inches='tight')
# plt.savefig("elo_comparison_plot.pdf", bbox_inches='tight') # PDF is often preferred for vector graphics
plt.savefig("data_processing/figures_for_paper/elo_comparison_plot.svg", dpi=300, bbox_inches='tight')
plt.savefig("data_processing/figures_for_paper/elo_comparison_plot.png", dpi=300, bbox_inches='tight')

plt.show()