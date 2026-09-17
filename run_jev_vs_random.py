"""Batch: RANDOM (white) vs TypeSafe Jev (black). Delays/timeouts zeroed.

Env:
  TYPESAFE_API_KEY   required (or set in .env)
  TYPESAFE_MODEL     default jev-latest
  JEV_NUM_GAMES      default 10
"""
import json
import os
import statistics
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

import llm_chess
from utils import setup_console_logging

NUM_REPETITIONS = int(os.environ.get("JEV_NUM_GAMES", "10"))
MODEL_NAME = os.environ.get("TYPESAFE_MODEL", "jev-latest")
RUN_TS = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
LOG_FOLDER = f"_logs/rand_vs_llm/{MODEL_NAME}/{RUN_TS}"

if not os.environ.get("TYPESAFE_API_KEY"):
    raise SystemExit("Set TYPESAFE_API_KEY in the environment or .env")

llm_chess.throttle_delay = 0
llm_chess.dialog_turn_delay = 0
llm_chess.max_api_retries = 3
llm_chess.api_retry_delay = 1.0
llm_chess.visualize_board = False
llm_chess.random_print_board = False
llm_chess.white_player_type = llm_chess.PlayerType.RANDOM_PLAYER
llm_chess.black_player_type = llm_chess.PlayerType.TYPESAFE_JEV
llm_chess.typesafe_model = MODEL_NAME

os.makedirs(LOG_FOLDER, exist_ok=True)
setup_console_logging(LOG_FOLDER)

EMPTY = {"config_list": [{"model": "n/a", "api_key": "n/a"}], "timeout": 0}

with open(os.path.join(LOG_FOLDER, "_run.json"), "w", encoding="utf-8") as f:
    json.dump(
        {
            "metadata": {
                "time_started_formatted": datetime.now().strftime("%Y.%m.%d_%H:%M"),
                "log_folder_relative": LOG_FOLDER,
                "num_repetitions": NUM_REPETITIONS,
                "store_individual_logs": True,
            },
            "player_types": {
                "white_player_type": "RANDOM_PLAYER",
                "black_player_type": "TYPESAFE_JEV",
            },
            "llm_configs": {"black": {"model": MODEL_NAME}},
        },
        f,
        indent=2,
    )

aggregate = {
    "matchup": "RANDOM_PLAYER (white) vs TYPESAFE_JEV (black)",
    "model": MODEL_NAME,
    "total_games": 0,
    "white_wins": 0,
    "black_wins": 0,
    "draws": 0,
    "total_moves": 0,
    "total_prompt_tokens": 0,
    "total_completion_tokens": 0,
    "total_cost_usd": 0.0,
    "reasons": {},
    "games": [],
}
moves_list = []

for i in range(NUM_REPETITIONS):
    print(f"\n===== GAME {i+1}/{NUM_REPETITIONS} =====", flush=True)
    game_stats, player_white, player_black = llm_chess.run(
        log_dir=LOG_FOLDER,
        llm_config_white=EMPTY,
        llm_config_black=EMPTY,
    )
    moves = game_stats["number_of_moves"]
    moves_list.append(moves)
    aggregate["total_games"] += 1
    aggregate["total_moves"] += moves
    black_usage = game_stats.get("usage_stats", {}).get("black", {})
    aggregate["total_cost_usd"] += float(black_usage.get("total_cost", 0) or 0)
    for k, v in black_usage.items():
        if k != "total_cost" and isinstance(v, dict):
            aggregate["total_prompt_tokens"] += int(v.get("prompt_tokens", 0) or 0)
            aggregate["total_completion_tokens"] += int(v.get("completion_tokens", 0) or 0)
            break
    winner = game_stats["winner"]
    if winner == player_white.name:
        aggregate["white_wins"] += 1
        result = "white (random)"
    elif winner == player_black.name:
        aggregate["black_wins"] += 1
        result = "black (jev)"
    else:
        aggregate["draws"] += 1
        result = "draw"
    reason = game_stats["reason"]
    aggregate["reasons"][reason] = aggregate["reasons"].get(reason, 0) + 1
    aggregate["games"].append(
        {
            "game": i + 1,
            "winner": result,
            "reason": reason,
            "moves": moves,
            "material": game_stats.get("material_count"),
            "black_usage": black_usage,
        }
    )
    print(
        f"Game {i+1}: {result} | {reason} | moves={moves} | cost={black_usage.get('total_cost', 0)}",
        flush=True,
    )

aggregate["average_moves"] = aggregate["total_moves"] / aggregate["total_games"]
aggregate["std_dev_moves"] = statistics.stdev(moves_list) if len(moves_list) > 1 else 0.0
out = os.path.join(LOG_FOLDER, "_aggregate_results.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(aggregate, f, indent=2)
print("\n===== AGGREGATE =====", flush=True)
print(json.dumps(aggregate, indent=2), flush=True)
print(f"Wrote {out}", flush=True)
