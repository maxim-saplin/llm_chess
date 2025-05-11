import argparse
import json
import re
from pathlib import Path
import numpy as np
from scipy.optimize import root_scalar

def expected_score(R, opponent_ratings):
    """Compute expected scores vs. opponents at given rating R."""
    diff = opponent_ratings - R
    return 1 / (1 + 10**(diff / 400))

def estimate_elo(records, white_advantage=35):
    """
    Estimate the LLM's Elo rating from head-to-head records.
    
    records : list of (opponent_elo, score) tuples
    white_advantage : Elo points to add for Black-only bias correction
    """
    opponent_ratings = np.array([r for r, _ in records])
    scores = np.array([o for _, o in records])
    
    # Define the function whose root is the MLE condition
    def f(R):
        E = expected_score(R, opponent_ratings)
        return np.sum(scores - E)
    
    # Root-find for R such that f(R) = 0
    bracket = (np.min(opponent_ratings) - 400, np.max(opponent_ratings) + 400)
    result = root_scalar(f, bracket=bracket, method='brentq')
    R_hat_black = result.root
    
    # Compute Fisher information and standard error
    E_hat = expected_score(R_hat_black, opponent_ratings)
    info = np.sum(E_hat * (1 - E_hat)) * (np.log(10)/400)**2
    se_black = 1 / np.sqrt(info)
    
    # Adjust for White advantage
    R_hat_true = R_hat_black + white_advantage
    se_true = se_black  # if white_advantage treated as fixed
    
    return {
        'R_hat_black': R_hat_black,
        'se_black': se_black,
        'R_hat_true': R_hat_true,
        'se_true': se_true,
        'ci_95_true': (float(R_hat_true - 1.96 * se_true), float(R_hat_true + 1.96 * se_true))
    }

LVL_TO_ELO = {
    1: 250,
    2: 400,
    3: 550,
    4: 700,
    5: 850,
    6: 1000,
    7: 1100,
    8: 1200,
    9: 1300,
    10: 1400,
    11: 1500,
    12: 1600,
    13: 1700,
    14: 1800,
    15: 1900,
    16: 2000,
    17: 2100,
    18: 2200,
    19: 2300,
    20: 2400,
    21: 2500,
    22: 2600,
    23: 2700,
    24: 2900,
    25: 3200,
}

WINNER_TO_SCORE = {
    "Player_Black": 1.0,
    "NONE": 0.5,
    "Chess_Engine_Dragon_White": 0.0,
}

ALIASES = {
    "o3-2025-04-16-low": ["o3-2025-04-16-low"],
    "grok-3-mini-beta-high": ["grok-3-mini-beta-high", "grok-3-mini-fast-beta-high"],
}

# Example usage:
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_name", type=str, required=True)
    args = parser.parse_args()

    records = []
    pattern = re.compile(r'^lvl-(\d+)_vs_([A-Za-z0-9-]+)$')
    for path in Path("_logs/dragon_vs_llm").rglob('*'):
        if path.is_file() and path.suffix == '.json' and "_aggregate_results" not in path.name:
            
            config = path.parent.parent.name
            match = pattern.match(config)
            if match:
                lvl, model_name = match.groups()
            else:
                continue

            if model_name not in ALIASES[args.model_name]:
                continue

            output = json.load(open(path))

            outcome = output["winner"]
            records.append((LVL_TO_ELO[int(lvl)], WINNER_TO_SCORE[outcome]))

    print("Found", len(records), "games")
    print("Number of Wins:", sum(1 for _, score in records if score == 1.0))
    print("Number of Draws:", sum(1 for _, score in records if score == 0.5))
    print("Number of Losses:", sum(1 for _, score in records if score == 0.0))
    result = estimate_elo(records)
    # print("Estimated Elo (Black-only):", result['R_hat_black'])
    print("Estimated Elo (color-neutral):", result['R_hat_true'])
    print("95% CI (color-neutral):", result['ci_95_true'])