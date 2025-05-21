"""Run `calc_elos.py --model_name 'all'` to get the Elo ratings for all models.

To replicate results in the paper, use the logs at commit `75f0898445a53682d161478609dd74b9930ac0af` of the `main` branch.

"""
import argparse
import json
import re
from pathlib import Path
import numpy as np
import pandas as pd
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
    
    return f"{R_hat_true} +/- {1.96 * se_true}", R_hat_true, 1.96 * se_true

def lvl_to_elo(lvl):
    return (lvl + 1) * 125

def df_to_booktabs_latex(df, caption="Model Evaluation", label="tab:model_evaluation"):
    from io import StringIO

    buf = StringIO()
    buf.write("\\begin{table}[ht]\n")
    buf.write("\\centering\n")
    buf.write("\\caption{" + caption + "}\n")
    buf.write("\\label{" + label + "}\n")
    buf.write("\\begin{tabular}{lrrrrrrr}\n")
    buf.write("\\toprule\n")
    buf.write("Model & Elo & CI & Win/Loss & Total \\\\\n")
    buf.write("\\midrule\n")

    for _, row in df.iterrows():
        buf.write(
            f"{row['Model']} & "
            f"{row['Elo']} & "
            f"{row['95\\% Confidence Interval']} & "
            f"{row['\\winloss']} & "
            f"{row['Total Games']} & \\\\\n"
        )

    buf.write("\\bottomrule\n")
    buf.write("\\end{tabular}\n")
    buf.write("\\end{table}\n")
    return buf.getvalue()

def results_by_skill_to_booktabs_latex(df,
                                       caption="Win/Loss by Skill Level",
                                       label="tab:by_skill"):
    """
    results_by_skill: list of dicts with keys
        "Model"        (raw),
        "Skill"        (e.g. '1', '2', …),
        "Total Games"  (int),
        "\\winloss"    (string like '52.3')
    model_name_mapping: dict to rename raw model → pretty name
    """

    lines = []
    lines.append(r"\begin{table}[ht]")
    lines.append(r"\centering")
    lines.append(r"\caption{%s}" % caption)
    lines.append(r"\label{%s}" % label)
    lines.append(r"\begin{tabular}{lrrr}")
    lines.append(r"\toprule")
    lines.append(r"Model & Skill & Total Games & Win \% \\")
    lines.append(r"\midrule")

    # group by model
    for model, group in df.groupby('Model', sort=False):
        n = len(group)
        for i, row in enumerate(group.itertuples()):
            skill       = row.Skill
            total_games = row._3         # "Total Games" column
            winpct      = row._4         # "\\winloss" column
            if i == 0:
                lines.append(r"\multirow{%d}{*}{%s} & %s & %d & %s \\"
                             % (n, model, skill, total_games, winpct))
            else:
                lines.append(r" & %s & %d & %s \\"
                             % (skill, total_games, winpct))
        lines.append(r"\midrule")

    # replace the very last \midrule with \bottomrule
    lines[-1] = lines[-1].replace(r"\midrule", r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table}")

    return "\n".join(lines)

WINNER_TO_SCORE = {
    "Player_Black": 1.0,
    "NoN_Synthesizer": 1.0,
    "NONE": 0.5,
    "Chess_Engine_Dragon_White": 0.0,
}

ALIASES = {
    "o3-2025-04-16-low": ["o3-2025-04-16-low"],
    "grok-3-mini-beta-high": ["grok-3-mini-beta-high", "grok-3-mini-fast-beta-high"],
    # "3x-gpt-4.1-mini-2025-04-14-low_41mini-t03": ["3x-gpt-4.1-mini-2025-04-14-low_41mini-t03"],
    # "claude-3-7-sonnet-20250219-thinking-budget-5000": ["claude-3-7-sonnet-20250219-thinking-budget-5000"],
    # "claude-3-7-sonnet-20250219-thinking-budget-10000": ["claude-3-7-sonnet-20250219-thinking-budget-10000"],
    # "gemini-25pro-t03_mini41-t00_mini41-t03": ["gemini-25pro-t03_mini41-t00_mini41-t03"],
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
        model_names = [args.model_name] if args.model_name != 'all' else ALIASES.keys()
        results_by_skill = []
        results = []
        for args_model_name in model_names:
            records = []
            lvl_to_win_draw_loss = {}  # dict of skill to [win, draw, loss] numbers.
            pattern = re.compile(r'^lvl-(\d+)_vs_(.+)$')
            for path in Path("_logs/dragon_vs_llm").rglob('*'):
                if path.is_file() and path.suffix == '.json' and "_aggregate_results" not in path.name:
                
                    config = path.parent.parent.name
                    match = pattern.match(config)
                    if match:
                        lvl, model_name = match.groups()
                    else:
                        continue

                    if model_name not in ALIASES[args_model_name]:
                        continue

                    output = json.load(open(path))

                    if output["reason"] == "ERROR OCCURED":
                        continue

                    outcome = output["winner"]
                    records.append((lvl_to_elo(int(lvl)), WINNER_TO_SCORE[outcome]))
                    if lvl not in lvl_to_win_draw_loss:
                        lvl_to_win_draw_loss[lvl] = {'win': 0, 'draw': 0, 'loss': 0}
                    if WINNER_TO_SCORE[outcome] == 1.0:
                        lvl_to_win_draw_loss[lvl]['win'] += 1
                    elif WINNER_TO_SCORE[outcome] == 0.5:
                        lvl_to_win_draw_loss[lvl]['draw'] += 1
                    else:
                        lvl_to_win_draw_loss[lvl]['loss'] += 1

            if len(records) == 0:
                print(f"{args_model_name}: N/A")
                exit()

            result, elo, ci = estimate_elo(records, white_advantage = -35 if args.model_name == "random" else 35)
            print(f"{args_model_name} ({len(records)} games) : {result}")
            print(f"{args_model_name} W/D/L by Skill: {lvl_to_win_draw_loss}")

            # Sum W/D/L over all levels
            total_wins = sum(v['win'] for v in lvl_to_win_draw_loss.values())
            total_draws = sum(v['draw'] for v in lvl_to_win_draw_loss.values())
            total_losses = sum(v['loss'] for v in lvl_to_win_draw_loss.values())
            total_games = total_wins + total_draws + total_losses

            # Assume black_llm_wins = total_wins, white_rand_wins = total_losses
            win_loss = (
                ((total_wins - total_losses) / total_games) / 2 + 0.5
                if total_games > 0 else 0.5
            )

            results.append({
                "Model": args_model_name,
                "Total Games": total_games,
                "Elo": f"{elo:.2f}",
                "95\% Confidence Interval": f"{ci:.2f}",
                "\\winloss": f"{win_loss * 100:.1f}",
                # "Wins": total_wins,
                # "Draws": total_draws,
                # "Losses": total_losses,
            })

            # Now add results by skill
            for lvl, result in lvl_to_win_draw_loss.items():
                total_wins = result['win']
                total_draws = result['draw']
                total_losses = result['loss']
                total_games = total_wins + total_draws + total_losses

                # Assume black_llm_wins = total_wins, white_rand_wins = total_losses
                win_loss = (
                    ((total_wins - total_losses) / total_games) / 2 + 0.5
                    if total_games > 0 else 0.5
                )

                results_by_skill.append({
                    "Model": args_model_name,
                    "Skill": lvl,
                    "Total Games": total_games,
                    "\\winloss": f"{win_loss * 100:.1f}",
                })

        # Create and show/save DataFrame
        df = pd.DataFrame(results)
        model_name_mapping = {
            "o3-2025-04-16-low": "o3 (low)",
            "grok-3-mini-beta-high": "Grok 3 Mini (high)",
            "o3-mini-2025-01-31-low": "o3-mini (low)",
            "o3-mini-2025-01-31-medium": "o3-mini (medium)",
            "o3-mini-2025-01-31-high": "o3-mini (high)",
            "o4-mini-2025-04-16-low": "o4-mini (low)",
            "o4-mini-2025-04-16-medium": "o4-mini (medium)",
            "o4-mini-2025-04-16-high": "o4-mini (high)"
        }
        df['Model'] = df['Model'].replace(model_name_mapping)
        df_sorted = df.sort_values("Elo", ascending=False)
        print(df_sorted)
        # df.to_csv("elo_results.csv", index=False)  # Optional save
        latex_table = df_to_booktabs_latex(df_sorted, caption="Model Evaluation", label="tab:model_evaluation")
        print(latex_table)

        # Now do the same for results by skill
        df = pd.DataFrame(results_by_skill)
        df['Model'] = df['Model'].replace(model_name_mapping)
        # sort so that all levels of a model are together
        df = df.sort_values(['Model','Skill']).reset_index(drop=True)
        # df_skill.to_csv("elo_results_by_skill.csv", index=False)  # Optional save
        latex_table_skill = results_by_skill_to_booktabs_latex(
            df,
            caption="Win/Loss by Skill Level",
            label="tab:by_skill"
        )
        print(latex_table_skill)