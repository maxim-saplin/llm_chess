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


# Material values: pawn = 1, knight = 3, bishop = 3, rook = 5, queen = 9
# The maximum total material in chess is 39 for each player


def calculate_material_count(board):
    piece_values = {
        chess.PAWN: 1,
        chess.KNIGHT: 3,
        chess.BISHOP: 3,
        chess.ROOK: 5,
        chess.QUEEN: 9,
    }
    white_material = sum(
        piece_values.get(piece.piece_type, 0)
        for piece in board.piece_map().values()
        if piece.color == chess.WHITE
    )
    black_material = sum(
        piece_values.get(piece.piece_type, 0)
        for piece in board.piece_map().values()
        if piece.color == chess.BLACK
    )
    return white_material, black_material


load_dotenv()


def get_llms_autogen():
    # NOTE, if Azure type is used Autogen removes dots from model name,
    # If that is an issues (i.e. you are using LLM gateway that works like Azure but accupts model names with dots)
    # You better disable this in Autogen source code 'oia/client.py'
    #  if openai_config["azure_deployment"] is not None:
    #         openai_config["azure_deployment"] = openai_config["azure_deployment"].replace(".", "")
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
    material_count: dict,
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
        "material_count": material_count,
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


def display_store_game_video_and_stats(game_stats, log_dir="_logs", save_logs=True):
    white_summary = gather_usage_summary([game_stats["player_white"]])
    black_summary = gather_usage_summary([game_stats["player_black"]])

    video_dir = f"{log_dir}/videos"
    os.makedirs(video_dir, exist_ok=True)

    if save_logs:
        log_filename = f"{log_dir}/{game_stats['time_started']}.json"
        if os.path.exists(
            log_filename
        ):  # if running automated games they can complete within same second
            base, ext = os.path.splitext(log_filename)
            import time

            timestamp = int(time.time() * 1000)
            log_filename = f"{base}_{timestamp}{ext}"
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

    print("\nMaterial Count:")
    print(f"Player White: {game_stats['material_count']['white']}")
    print(f"Player Black: {game_stats['material_count']['black']}")

    print("\nCosts per agent (white and black):\n")
    if white_summary:
        pprint(white_summary["usage_excluding_cached_inference"])
    if black_summary:
        pprint(black_summary["usage_excluding_cached_inference"])
