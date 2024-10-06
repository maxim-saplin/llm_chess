import os
from autogen import gather_usage_summary
from typing import Any
from pprint import pprint
from dotenv import load_dotenv
import json
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import cairosvg
import io
import numpy as np
from moviepy.editor import ImageSequenceClip
import chess.svg

load_dotenv()


def get_llms_autogen():
    llm_config_white = {
        "api_type": "azure",
        "model": os.environ["AZURE_OPENAI_DEPLOYMENT_W"],
        "api_key": os.environ["AZURE_OPENAI_KEY_W"],
        "base_url": os.environ["AZURE_OPENAI_ENDPOINT_W"],
        "api_version": os.environ["AZURE_OPENAI_VERSION_W"],
    }

    llm_config_black = {
        "api_type": "azure",
        "model": os.environ["AZURE_OPENAI_DEPLOYMENT_B"],
        "api_key": os.environ["AZURE_OPENAI_KEY_B"],
        "base_url": os.environ["AZURE_OPENAI_ENDPOINT_B"],
        "api_version": os.environ["AZURE_OPENAI_VERSION_B"],
    }

    # Disabling LLM caching to avoid loops, also since the game is dynamic caching doesn't make sense
    llm_config_white["cache_seed"] = llm_config_black["cache_seed"] = None

    return llm_config_white, llm_config_black


def generate_game_stats(
    time_started: str,
    winner: str,
    reason: str,
    current_move: int,
    player_white: Any,
    player_black: Any,
    llm_config_white: dict,
    llm_config_black: dict,
) -> dict:
    """Generate game statistics."""
    white_summary = gather_usage_summary([player_white])
    black_summary = gather_usage_summary([player_black])

    return {
        "time_started": time_started,
        "winner": winner,
        "reason": reason,
        "number_of_moves": current_move,
        "player_white": {
            "name": player_white.name,
            "wrong_moves": player_white.wrong_moves,
            "wrong_actions": player_white.wrong_actions,
            "model": (
                player_white.llm_config["model"]
                if isinstance(player_white.llm_config, dict)
                else "N/A"
            ),
        },
        "player_black": {
            "name": player_black.name,
            "wrong_moves": player_black.wrong_moves,
            "wrong_actions": player_black.wrong_actions,
            "model": (
                player_black.llm_config["model"]
                if isinstance(player_black.llm_config, dict)
                else "N/A"
            ),
        },
        "usage_stats": {
            "white": (
                white_summary["usage_excluding_cached_inference"]
                if white_summary
                else {}
            ),
            "black": (
                black_summary["usage_excluding_cached_inference"]
                if black_summary
                else {}
            ),
        },
    }


load_dotenv()

_frames = []
_fig = plt.figure()


def display_board(board, move):
    """Display the board and capture the frame."""
    svg = chess.svg.board(
        board,
        arrows=[(move.from_square, move.to_square)],
        fill={move.from_square: "gray"},
        size=200,
    )
    png_data = cairosvg.svg2png(bytestring=svg.encode("utf-8"), dpi=200)
    img = mpimg.imread(io.BytesIO(png_data), format="png")

    plt.imshow(img)
    plt.axis("off")
    _fig.set_dpi(200)
    plt.pause(0.1)

    _fig.canvas.draw()
    io_buf = io.BytesIO()
    _fig.savefig(io_buf, format="raw", dpi=200)
    io_buf.seek(0)
    frame = np.reshape(
        np.frombuffer(io_buf.getvalue(), dtype=np.uint8),
        newshape=(int(_fig.bbox.bounds[3]), int(_fig.bbox.bounds[2]), -1),
    )
    _frames.append(frame)
    plt.clf()


def save_video(filename):
    """Save the captured frames to a video file."""
    if _frames:
        clip = ImageSequenceClip(_frames, fps=1)
        clip.write_videofile(filename, codec="libx264")
    else:
        print("No frames to save to a video file")


def display_store_game_video_and_stats(game_stats):
    white_summary = gather_usage_summary([game_stats["player_white"]])
    black_summary = gather_usage_summary([game_stats["player_black"]])

    log_dir = "_logs"
    video_dir = f"{log_dir}/videos"
    os.makedirs(video_dir, exist_ok=True)

    log_filename = f"{log_dir}/{game_stats['time_started']}.json"
    with open(log_filename, "w") as log_file:
        json.dump(game_stats, log_file, indent=4)
    save_video(f"{video_dir}/{game_stats['time_started']}.mp4")
    print("\033[92m\nGAME OVER\n\033[0m")
    print(f"\033[92m{game_stats['winner']} wins due to {game_stats['reason']}.\033[0m")
    print(f"\033[92mNumber of moves made: {game_stats['number_of_moves']}\033[0m")
    print("\nWrong Moves (LLM asked to make illegal/impossible move):")
    print(f"Player White: {game_stats['player_white']['wrong_moves']}")
    print(f"Player Black: {game_stats['player_black']['wrong_moves']}")

    print("\nWrong Actions (LLM responded with non parseable message):")
    print(f"Player White: {game_stats['player_white']['wrong_actions']}")
    print(f"Player Black: {game_stats['player_black']['wrong_actions']}")

    print("\nCosts per agent (white and black):\n")
    if white_summary:
        pprint(white_summary["usage_excluding_cached_inference"])
    if black_summary:
        pprint(black_summary["usage_excluding_cached_inference"])
