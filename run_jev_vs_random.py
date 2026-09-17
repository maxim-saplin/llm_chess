"""RANDOM (white) vs TypeSafe Jev (black). Delays/timeouts zeroed for speed.

Usage:
  uv run python run_jev_vs_random.py            # default 10 games
  uv run python run_jev_vs_random.py --games 1  # dry-run / smoke
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from datetime import datetime
from pathlib import Path


def _load_typesafe_key() -> None:
    if os.environ.get("TYPESAFE_API_KEY"):
        return
    for secrets_path in (
        Path("/home/box/sand-data/box-secrets.json"),
        Path("/home/box/agent-data/box-secrets.json"),
    ):
        if secrets_path.exists():
            data = json.loads(secrets_path.read_text())
            card = data.get("card") or {}
            key = card.get("TYPESAFE_API_KEY")
            if key:
                os.environ["TYPESAFE_API_KEY"] = key
                return



def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RANDOM vs TypeSafe Jev")
    parser.add_argument("--games", type=int, default=10, help="Number of games (default 10)")
    parser.add_argument(
        "--log-folder",
        default=None,
        help="Log directory (default _logs/rand_vs_llm/<model>/<timestamp>)",
    )
    args = parser.parse_args(argv)

    _load_typesafe_key()

    import llm_chess
    from get_run_metadata import collect_run_metadata, write_run_metadata
    from utils import setup_console_logging

    num = max(1, args.games)
    model_name = os.environ.get("TYPESAFE_MODEL", "jev-latest")
    run_ts = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    log_folder = args.log_folder or str(
        Path("_logs") / "rand_vs_llm" / model_name / run_ts
    )

    llm_chess.throttle_delay = 0
    llm_chess.dialog_turn_delay = 0
    llm_chess.max_api_retries = 3
    llm_chess.api_retry_delay = 1.0
    llm_chess.visualize_board = False
    llm_chess.random_print_board = False
    llm_chess.white_player_type = llm_chess.PlayerType.RANDOM_PLAYER
    llm_chess.black_player_type = llm_chess.PlayerType.TYPESAFE_JEV
    llm_chess.typesafe_model = model_name

    os.makedirs(log_folder, exist_ok=True)
    setup_console_logging(log_folder)

    empty = {"config_list": [{"model": "n/a", "api_key": "n/a"}], "timeout": 0}
    try:
        meta = collect_run_metadata(
            log_folder_relative=log_folder,
            num_repetitions=num,
            store_individual_logs=True,
            llm_config_white=empty,
            llm_config_black=empty,
        )
        write_run_metadata(meta, os.path.join(log_folder, "_run.json"))
    except Exception as err:
        print(f"[run_metadata] Error: {err}", flush=True)

    aggregate = {
        "matchup": "RANDOM_PLAYER (white) vs TYPESAFE_JEV (black)",
        "model": model_name,
        "throttle_delay": llm_chess.throttle_delay,
        "dialog_turn_delay": llm_chess.dialog_turn_delay,
        "autogen_timeout": 0,
        "total_games": 0,
        "white_wins": 0,
        "black_wins": 0,
        "draws": 0,
        "total_moves": 0,
        "reasons": {},
        "games": [],
    }
    moves_list: list[int] = []

    for i in range(num):
        print(f"\n===== GAME {i+1}/{num} =====", flush=True)
        game_stats, player_white, player_black = llm_chess.run(
            log_dir=log_folder,
            llm_config_white=empty,
            llm_config_black=empty,
        )
        moves = game_stats["number_of_moves"]
        moves_list.append(moves)
        aggregate["total_games"] += 1
        aggregate["total_moves"] += moves
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
        row = {
            "game": i + 1,
            "winner": result,
            "reason": reason,
            "moves": moves,
            "material": game_stats.get("material_count"),
            "black_model": game_stats.get("player_black", {}).get("model"),
            "black_cost": (game_stats.get("usage_stats") or {}).get("black", {}).get(
                "total_cost"
            ),
            "black_reply_time_s": game_stats.get("player_black", {}).get(
                "accumulated_reply_time_seconds"
            ),
        }
        aggregate["games"].append(row)
        print(
            f"Game {i+1}: {result} | {reason} | moves={moves} | "
            f"model={row['black_model']} cost={row['black_cost']}",
            flush=True,
        )

    aggregate["average_moves"] = aggregate["total_moves"] / aggregate["total_games"]
    aggregate["std_dev_moves"] = (
        statistics.stdev(moves_list) if len(moves_list) > 1 else 0.0
    )
    out = os.path.join(log_folder, "_aggregate_results.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(aggregate, f, indent=2)
    print("\n===== AGGREGATE =====", flush=True)
    print(json.dumps(aggregate, indent=2), flush=True)
    print(f"Wrote {out}", flush=True)
    print(f"Log folder: {log_folder}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
