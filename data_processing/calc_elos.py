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
    
    return f"{R_hat_true} +/- {1.96 * se_true}"

def lvl_to_elo(lvl):
    return (lvl + 1) * 125

WINNER_TO_SCORE = {
    "Player_Black": 1.0,
    "NoN_Synthesizer": 1.0,
    "NONE": 0.5,
    "Chess_Engine_Dragon_White": 0.0,
}

ALIASES = {
    "o3-2025-04-16-low": ["o3-2025-04-16-low"],
    "grok-3-mini-beta-high": ["grok-3-mini-beta-high", "grok-3-mini-fast-beta-high"],
    "3x-gpt-4.1-mini-2025-04-14-low_41mini-t03": ["3x-gpt-4.1-mini-2025-04-14-low_41mini-t03"],
    "claude-3-7-sonnet-20250219-thinking-budget-5000": ["claude-3-7-sonnet-20250219-thinking-budget-5000"],
    "claude-3-7-sonnet-20250219-thinking-budget-10000": ["claude-3-7-sonnet-20250219-thinking-budget-10000"],
    "gemini-25pro-t03_mini41-t00_mini41-t03": ["gemini-25pro-t03_mini41-t00_mini41-t03"],
    # "o1-2024-12-17-low": ["o1-2024-12-17-low"],
    # "o1-mini-2024-09-12": ["o1-mini-2024-09-12"],
    "o3-mini-2025-01-31-low": ["o3-mini-2025-01-31-low"],
    "o3-mini-2025-01-31-medium": ["o3-mini-2025-01-31-medium"],
    "o3-mini-2025-01-31-high": ["o3-mini-2025-01-31-high"],
    "o4-mini-2025-04-16-low": ["o4-mini-2025-04-16-low"],
    "o4-mini-2025-04-16-medium": ["o4-mini-2025-04-16-medium"],
    "o4-mini-2025-04-16-high": ["o4-mini-2025-04-16-high"],
}

# Example usage:
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_name", type=str, required=True)
    args = parser.parse_args()  

    records = []

    if args.model_name == "random":
        for path in Path("_logs/misc/dragon").rglob('*'):
            if path.is_file() and path.suffix == '.json' and path.name.startswith("random"):

                match = match = re.search(r"lvl-(\d+)", path.name)
                if match:
                    lvl = match.group(1)
                else:
                    continue

                output = json.load(open(path))
                white_wins = output["white_wins"]
                black_wins = output["black_wins"]
                draws = output["draws"]

                for _ in range(output["white_wins"]):
                    records.append((lvl_to_elo(int(lvl)), 1.0))
                for _ in range(output["draws"]):
                    records.append((lvl_to_elo(int(lvl)), 0.5))
                for _ in range(output["black_wins"]):
                    records.append((lvl_to_elo(int(lvl)), 0.0))

    else:
        pattern = re.compile(r'^lvl-(\d+)_vs_(.+)$')
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

                if output["reason"] == "ERROR OCCURED":
                    continue

                outcome = output["winner"]
                records.append((lvl_to_elo(int(lvl)), WINNER_TO_SCORE[outcome]))

    if len(records) == 0:
        print(f"{args.model_name}: N/A")
        exit()

    result = estimate_elo(records, white_advantage = -35 if args.model_name == "random" else 35)
    print(f"{args.model_name} ({len(records)} games) : {result}")