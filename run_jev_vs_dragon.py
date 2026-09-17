"""Dragon (white) vs TypeSafe Jev (black).

Defaults: dragon_time_per_move=0.1 (strength-valid). Use --time-per-move 0 for fast dry-runs.

Usage:
  uv run python run_jev_vs_dragon.py --levels 1 --games-per-level 1
  uv run python run_jev_vs_dragon.py --levels 1,2,3 --games-per-level 10
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


def _default_dragon_path() -> str:
    if sys.platform == "darwin":
        return "./dragon/dragon-osx"
    if sys.platform.startswith("win"):
        return "./dragon/dragon.exe"
    return "./dragon/dragon-linux"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dragon vs TypeSafe Jev")
    parser.add_argument(
        "--levels",
        default="1,2,3",
        help="Comma-separated Dragon skill levels (default 1,2,3)",
    )
    parser.add_argument(
        "--games-per-level",
        type=int,
        default=10,
        help="Games per skill level (default 10)",
    )
    parser.add_argument(
        "--time-per-move",
        type=float,
        default=0.1,
        help="Dragon time_per_move seconds (default 0.1; use 0 for fast dry-run)",
    )
    parser.add_argument(
        "--dragon-path",
        default=None,
        help="Override Dragon binary path (default: platform-specific)",
    )
    args = parser.parse_args(argv)

    _load_typesafe_key()

    import llm_chess
    from get_run_metadata import collect_run_metadata, write_run_metadata
    from utils import setup_console_logging

    levels = [int(x.strip()) for x in args.levels.split(",") if x.strip()]
    num_per = max(1, args.games_per_level)
    model_name = os.environ.get("TYPESAFE_MODEL", "jev-latest")
    run_ts = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    root = Path("_logs/engine_vs_llm")

    llm_chess.throttle_delay = 0
    llm_chess.dialog_turn_delay = 0
    llm_chess.max_api_retries = 3
    llm_chess.api_retry_delay = 1.0
    llm_chess.visualize_board = False
    llm_chess.random_print_board = False
    llm_chess.dragon_path = args.dragon_path or _default_dragon_path()
    llm_chess.typesafe_model = model_name
    llm_chess.dragon_time_per_move = args.time_per_move
    llm_chess.white_player_type = llm_chess.PlayerType.CHESS_ENGINE_DRAGON
    llm_chess.black_player_type = llm_chess.PlayerType.TYPESAFE_JEV

    empty = {"config_list": [{"model": "n/a", "api_key": "n/a"}], "timeout": 0}

    overall = {
        "matchup": "CHESS_ENGINE_DRAGON (white) vs TYPESAFE_JEV (black)",
        "model": model_name,
        "dragon_path": llm_chess.dragon_path,
        "dragon_time_per_move": llm_chess.dragon_time_per_move,
        "throttle_delay": 0,
        "dialog_turn_delay": 0,
        "autogen_timeout": 0,
        "levels": {},
    }

    def run_level(level: int) -> dict:
        llm_chess.dragon_level = level
        log_folder = root / f"dragon-lvl-{level}" / model_name / run_ts
        log_folder.mkdir(parents=True, exist_ok=True)
        setup_console_logging(str(log_folder))

        try:
            meta = collect_run_metadata(
                log_folder_relative=str(log_folder),
                num_repetitions=num_per,
                store_individual_logs=True,
                llm_config_white=empty,
                llm_config_black=empty,
            )
            write_run_metadata(meta, str(log_folder / "_run.json"))
        except Exception as err:
            print(f"[run_metadata] Error: {err}", flush=True)

        aggregate = {
            "dragon_level": level,
            "model": model_name,
            "dragon_time_per_move": llm_chess.dragon_time_per_move,
            "total_games": 0,
            "white_wins": 0,
            "black_wins": 0,
            "draws": 0,
            "total_moves": 0,
            "reasons": {},
            "games": [],
        }
        moves_list: list[int] = []

        for i in range(num_per):
            print(f"\n===== LEVEL {level} | GAME {i+1}/{num_per} =====", flush=True)
            game_stats, player_white, player_black = llm_chess.run(
                log_dir=str(log_folder),
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
                result = "white (dragon)"
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
            }
            aggregate["games"].append(row)
            print(
                f"L{level} G{i+1}: {result} | {reason} | moves={moves} | "
                f"model={row['black_model']} cost={row['black_cost']}",
                flush=True,
            )

        aggregate["average_moves"] = aggregate["total_moves"] / aggregate["total_games"]
        aggregate["std_dev_moves"] = (
            statistics.stdev(moves_list) if len(moves_list) > 1 else 0.0
        )
        out = log_folder / "_aggregate_results.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(aggregate, f, indent=2)
        print(f"Wrote {out}", flush=True)
        return {"log_folder": str(log_folder), **aggregate}

    for level in levels:
        overall["levels"][str(level)] = run_level(level)

    summary_path = root / f"jev_vs_dragon_summary_{run_ts}.json"
    root.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(overall, f, indent=2)
    print("\n===== OVERALL =====", flush=True)
    print(json.dumps(overall, indent=2), flush=True)
    print(f"Wrote {summary_path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
