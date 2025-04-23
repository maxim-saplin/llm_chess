import math
import json

data = json.load(open("stockfish_elos/stockfish_logs/level2.json"))

# Pool totals
total_W = sum(entry["summary"]["SF_wins"]   for entry in data)
total_D = sum(entry["summary"]["draws"]     for entry in data)
total_L = sum(entry["summary"]["Maia_wins"] for entry in data)
N       = total_W + total_D + total_L

S = (total_W + 0.5 * total_D) / N

delta = -400 * math.log10(1/S - 1)

weighted_sum = sum(
    entry["Maia_elo"] * (entry["summary"]["SF_wins"] + entry["summary"]["draws"] + entry["summary"]["Maia_wins"])
    for entry in data
)
M_ref = weighted_sum / N

estimated_elo = M_ref + delta

print(f"Total games: {N}")
print(f"Score fraction S = {S:.3f}")
print(f"Weighted Maia Elo = {M_ref:.1f}")
print(f"Δ = {delta:.1f}")
print(f"Estimated Stockfish skill 2 Elo ≈ {estimated_elo:.0f}")
