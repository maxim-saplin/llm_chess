#!/usr/bin/env python3
"""
calc_elos_pipeline.py

Compute Elo ratings in four stages:
1) Engine vs Dragon (random & stockfish) from _logs/misc/dragon.
2) LLM vs Dragon from _logs/dragon_vs_llm.
3) Unified Leaderboard combining engines, LLMs, and Dragon-level baselines.
4) Extended Elo vs Random using data_processing/refined.csv.

Outputs formatted tables for each stage and Dragon levels 1–5 Elo mapping.

Usage:
  python calc_elos_pipeline.py
"""

import json
import re
from pathlib import Path
import csv
import warnings
warnings.filterwarnings('ignore', 'Cannot bracket root.*', UserWarning)
import numpy as np
from scipy.optimize import root_scalar

# Constants for input log directories
ENGINE_AGGR_FOLDER   = Path("_logs/misc/dragon")
DRAGON_VS_LLM_FOLDER = Path("_logs/dragon_vs_llm")
REFINED_CSV_PATH    = Path("data_processing/refined.csv")
MIN_GAMES = 30

# Alias mapping: canonical model names -> list of folder variants
DRAGON_VS_LLM_MODEL_ALIASES = {
    "grok-3-mini-beta-high": ["grok-3-mini-beta-high", "grok-3-mini-fast-beta-high"],
    "o4-mini-2025-04-16-high": ["o4-mini-2025-04-16-high", "o4-mini-2025-04-16-high_timeout-20m", "o4-mini-2025-04-16-high_timeout-60m"],
}

# ANSI escape codes for green coloring
GREEN = "\033[32m"
RESET = "\033[0m"

def expected_score(R, opponent_ratings):
    """Compute expected score vs. an array of opponent ratings."""
    diff = opponent_ratings - R
    return 1.0 / (1.0 + 10.0 ** (diff / 400.0))


def estimate_elo(records, white_advantage=35):
    """
    Estimate the Elo rating from (opponent_elo, score) records.

    Args:
        records: list of (opponent_elo, score) tuples
        white_advantage: Elo correction to add to the solved 'black' rating

    Returns:
        (R_true, se_true): the adjusted Elo and standard error
    """
    opponent_elos = np.array([r for r, _ in records], dtype=float)
    scores        = np.array([s for _, s in records], dtype=float)

    # Define MLE condition function: sum(observed - expected) = 0
    def f(R):
        return np.sum(scores - expected_score(R, opponent_elos))

    # Bracket search: start at [min-400, max+400], expand if needed
    a = float(opponent_elos.min() - 400)
    b = float(opponent_elos.max() + 400)
    fa = f(a)
    fb = f(b)
    # Expand bracket until signs differ or give up after a few tries
    if fa * fb > 0:
        width = 400.0
        for _ in range(5):
            a -= width
            b += width
            fa = f(a)
            fb = f(b)
            if fa * fb <= 0:
                break
            width *= 2
    if fa * fb > 0:
        # Degenerate case: all wins or all losses; mark Elo as undefined
        import warnings
        warnings.warn(
            f"Cannot bracket root (f(a)={fa:.3f}, f(b)={fb:.3f}): no valid root found; setting Elo to NaN.")
        R_black = float('nan')
    else:
        # Found valid bracket
        result = root_scalar(f, bracket=(a, b), method="brentq")
        R_black = result.root

    # Fisher information for standard error
    # If se_black undefined (degenerate), this will override
    E_hat = expected_score(R_black, opponent_elos)
    info  = np.sum(E_hat * (1 - E_hat)) * (np.log(10)/400.0)**2
    se_black = 1.0 / np.sqrt(info) if not np.isnan(R_black) else float('nan')

    # Adjust for white advantage: R_true = R_black + white_advantage
    R_true  = R_black + white_advantage
    se_true = se_black

    return R_true, se_true


def lvl_to_elo(lvl):
    """Convert a Dragon level integer to its corresponding Elo."""
    return (lvl + 1) * 125


def load_aggregate_records(aggr_dir, player_name):
    """
    Load aggregate JSONs for a given player from the misc directory.

    Returns:
      records: list of (opponent_elo, score)
      dragon_levels: sorted list of unique Dragon levels encountered
    """
    pattern = re.compile(rf"^{re.escape(player_name)}.*_vs_dragon-lvl-(\d+)\.json$")
    records = []
    dragon_levels = set()

    for path in aggr_dir.glob("*.json"):
        match = pattern.match(path.name)
        if not match:
            continue
        lvl = int(match.group(1))
        dragon_levels.add(lvl)
        data = json.load(path.open())

        white_wins = data.get("white_wins", 0)
        draws      = data.get("draws", 0)
        black_wins = data.get("black_wins", 0)

        opp_elo = lvl_to_elo(lvl)
        # Expand counts into per-game records
        records.extend([(opp_elo, 1.0)] * white_wins)
        records.extend([(opp_elo, 0.5)] * draws)
        records.extend([(opp_elo, 0.0)] * black_wins)

    return records, sorted(dragon_levels)


# Mapping of JSON "winner" field to score for the Black player (LLM)
WINNER_TO_SCORE = {
    "Player_Black": 1.0,
    "NoN_Synthesizer": 1.0,
    "NONE": 0.5,
    "Chess_Engine_Dragon_White": 0.0,
}

def load_llm_vs_dragon_records(vslm_dir):
    """
    Load per-game JSON logs for LLM vs Dragon at various levels.
    Returns a dict mapping normalized model_key -> list of (opponent_elo, score) records.
    """
    pattern = re.compile(r"^lvl-(\d+)_vs_(.+)$")
    llm_records = {}
    if not vslm_dir.is_dir():
        return llm_records
    for cfg_dir in vslm_dir.iterdir():
        if not cfg_dir.is_dir():
            continue
        m = pattern.match(cfg_dir.name)
        if not m:
            continue
        lvl = int(m.group(1))
        # if lvl != 1:
        #     continue
        raw_model = m.group(2)
        # map folder variant to canonical alias if defined
        model_key = raw_model
        for canon, variants in DRAGON_VS_LLM_MODEL_ALIASES.items():
            if raw_model in variants:
                model_key = canon
                break
        # descend into timestamped subdirectories
        for ts_dir in cfg_dir.iterdir():
            if not ts_dir.is_dir():
                continue
            for game_file in ts_dir.glob("*.json"):
                if game_file.name == "_aggregate_results.json":
                    continue
                try:
                    data = json.load(game_file.open())
                except Exception:
                    continue
                winner = data.get("winner")
                score = WINNER_TO_SCORE.get(winner)
                if score is None:
                    continue
                opp_elo = lvl_to_elo(lvl)
                llm_records.setdefault(model_key, []).append((opp_elo, score))
    return llm_records


def print_elos_stage(title, results, keys, baseline_keys=set()):
    """Print a formatted Elo table for a given subset of results."""
    player_col = max(len("Player"), max(len(k) + (1 if k in baseline_keys else 0) for k in keys)) + 2
    games_col  = max(len("Games"), max(len(str(results[k][0])) for k in keys)) + 2
    elo_col    = max(len("Elo"), max(len(f"{results[k][1]:.1f}") for k in keys)) + 2
    ci_col     = max(len("±95%CI"), max(len(f"{results[k][2]:.1f}") for k in keys)) + 2

    print(f"\n{title}")
    header = f"{'Player':<{player_col}} {'Games':>{games_col}} {'Elo':>{elo_col}} {'±95%CI':>{ci_col}}"
    print(header)
    print('-' * len(header))

    for name in keys:
        n, R, ci = results[name]
        display_name = '*' + name if name in baseline_keys else name
        row = f"{display_name:<{player_col}} {n:>{games_col}d} {R:>{elo_col}.1f} {ci:>{ci_col}.1f}"
        if name in baseline_keys:
            print(f"{GREEN}{row}{RESET}")
        else:
            print(row)


def main():
    misc_dir = ENGINE_AGGR_FOLDER
    if not misc_dir.is_dir():
        print(f"Error: misc logs directory not found at {misc_dir}")
        return
    # Directory of per-game LLM vs Dragon logs
    vslm_dir = DRAGON_VS_LLM_FOLDER

    # 1) Discover 'random' and 'stockfish-lvl-1' automatically
    players = set()
    for path in misc_dir.glob("*_vs_dragon-lvl-*.json"):
        player = path.name.split("_vs_dragon")[0]
        if player.startswith("dragon-lvl"):
            continue
        players.add(player)

    # Only include random and stockfish baselines in this first run
    players = sorted(p for p in players if p in {"random", "stockfish-lvl-1"})

    results = {}
    # Collect dragon levels seen; ensure levels 1 through 5 are always included
    all_dragon_levels = set()

    for player in players:
        records, dragon_lvls = load_aggregate_records(misc_dir, player)
        all_dragon_levels.update(dragon_lvls)
        if not records:
            print(f"{player}: no aggregate records found.")
            continue

        # Both 'random' and 'stockfish' are always white in these logs
        white_advantage = -35
        R, se = estimate_elo(records, white_advantage)
        ci95 = 1.96 * se
        results[player] = (len(records), R, ci95)

    print_elos_stage("Engine Elo ratings:", results, players)

    # 2) Load LLM vs Dragon games and estimate each LLM's Elo
    llm_records = load_llm_vs_dragon_records(vslm_dir)
    for model_key in sorted(llm_records):
        records = llm_records[model_key]
        if not records:
            continue
        # LLM always Black vs Dragon White
        R, se = estimate_elo(records, white_advantage=35)
        ci95 = 1.96 * se
        results[model_key] = (len(records), R, ci95)
        # also register the dragon levels encountered here
        # but mapping is static 1-5 below

    # Stage 2: LLM Elo ratings
    print_elos_stage("Stage 2: LLM Elo Ratings", results, sorted(llm_records))

    # Always include dragon levels 1-5 as known baselines and insert them into results
    all_dragon_levels.update(range(1, 6))
    for lvl in sorted(all_dragon_levels):
        key = f"dragon-lvl-{lvl}*"
        # Known Elo, zero games, zero CI
        results[key] = (0, lvl_to_elo(lvl), 0.0)

    # Stage 3: Unified Elo Ratings
    baseline_keys = set(players) | {f"dragon-lvl-{lvl}*" for lvl in all_dragon_levels}
    # Capture existing models for Stage 4
    pre_existing = set(results.keys())
    combined_items = sorted(results.items(), key=lambda it: it[1][1], reverse=True)
    combined_keys = [name for name, _ in combined_items if name in baseline_keys or results[name][0] >= MIN_GAMES]
    print_elos_stage("Stage 3: Unified Elo Ratings", results, combined_keys, baseline_keys)

    # Stage 4: Extended Elo Ratings vs Random
    if REFINED_CSV_PATH.is_file():
        random_elo = results.get("random", (None, None, None))[1]
        if random_elo is None:
            print("Skipping Stage 4: random Elo not found.")
        else:
            with REFINED_CSV_PATH.open() as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = row["Player"]
                    if name in pre_existing:
                        continue
                    total = int(row.get("total_games", 0))
                    wins = int(row.get("player_wins", 0))
                    draws = int(row.get("draws", 0))
                    losses = int(row.get("opponent_wins", 0))
                    recs = [(random_elo, 1.0)] * wins + [(random_elo, 0.5)] * draws + [(random_elo, 0.0)] * losses
                    if total < MIN_GAMES:
                        continue
                    R_ext, se_ext = estimate_elo(recs, white_advantage=35)
                    ci95_ext = 1.96 * se_ext
                    results[name] = (total, R_ext, ci95_ext)
            # Build and print extended combined table including new models, with NaNs last
            # Select candidates: baselines or sufficient games
            candidates = [(name, data) for name, data in results.items() if name in baseline_keys or data[0] >= MIN_GAMES]
            # Separate out non-NaN and NaN Elo entries
            non_nan = sorted(
                [(n, d) for n, d in candidates if not np.isnan(d[1])],
                key=lambda it: it[1][1], reverse=True)
            nan_entries = sorted(
                [(n, d) for n, d in candidates if np.isnan(d[1])],
                key=lambda it: it[0])
            ext_keys = [n for n, _ in non_nan] + [n for n, _ in nan_entries]
            print_elos_stage("Stage 4: Extended Elo Ratings vs Random", results, ext_keys, baseline_keys)
            # Note about undefined Elo estimates
            print("\nNote: Elo=NaN indicates no valid root was found (e.g., all wins or all losses), so Elo is undefined.")

    # Print Dragon level Elo mapping
    print("\nDragon levels (theoretical Elo):")
    for lvl in sorted(all_dragon_levels):
        print(f"  lvl-{lvl:<2d}: {lvl_to_elo(lvl):5d}")

if __name__ == "__main__":
    main() 