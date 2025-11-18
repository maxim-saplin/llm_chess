import json

# 1. Load your data
# If your data is in a file, replace the list below with:
# data = json.load(open("your_data.json"))
data = json.load(open("stockfish_elos/maia_logs/final_results/results_maia.json"))

# 2. Organize into a nested dict: pivot[skill][maia] = (SF_wins, draws, Maia_wins)
pivot = {}
for entry in data:
    lvl = entry["skill_level"]
    melo = entry["Maia_elo"]
    w = entry["summary"]["SF_wins"]
    d = entry["summary"]["draws"]
    l = entry["summary"]["Maia_wins"]
    total = w + d + l
    pivot.setdefault(lvl, {})[melo] = (w/total*100, d/total*100, l/total*100)

# 3. Prepare sorted rows and columns
levels = sorted(pivot.keys())
maia_elos = sorted({e["Maia_elo"] for e in data})

# 4. Print header
col_width = 16
header = "Skill".ljust(6) + "| " + " | ".join(f"{m}".center(col_width) for m in maia_elos)
print(header)
print("-" * len(header))

# 5. Print each row
for lvl in levels:
    row = f"{lvl:<6}| "
    for m in maia_elos:
        if m in pivot[lvl]:
            sf, dr, ma = pivot[lvl][m]
            cell = f"{sf:.1f}/{dr:.1f}/{ma:.1f}"
        else:
            cell = "-"
        row += cell.center(col_width) + " | "
    print(row)
