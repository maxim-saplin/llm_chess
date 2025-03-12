import os
import sys
import re
from _ag import gather_usage_summary
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


def get_llms_autogen(temperature=None, reasoning_effort=None):
    """
    Retrieve the configuration for LLMs (Large Language Models) with optional temperature setting.

    Note:
    If the Azure type is used, Autogen removes dots from the model name.
    If this is an issue (e.g., you are using an LLM gateway that works like Azure but accepts model names with dots),
    you should disable this behavior in the Autogen source code 'oia/client.py'.

    Example of disabling in source code:
    if openai_config["azure_deployment"] is not None:
        openai_config["azure_deployment"] = openai_config["azure_deployment"].replace(".", "")

    Args:
        temperature (float, optional): The temperature setting for the model. Defaults to None.

    Returns:
        tuple: A tuple containing two configuration dictionaries for the models.
    """
    model_kinds = [
        os.environ.get("MODEL_KIND_W", "azure"),
        os.environ.get("MODEL_KIND_B", "azure"),
    ]

    def azure_config(key):
        return {
            "api_type": "azure",
            "model": os.environ[f"AZURE_OPENAI_DEPLOYMENT_{key}"],
            "api_key": os.environ[f"AZURE_OPENAI_KEY_{key}"],
            "base_url": os.environ[f"AZURE_OPENAI_ENDPOINT_{key}"],
            "api_version": os.environ[f"AZURE_OPENAI_VERSION_{key}"],
        }

    def local_config(key):
        return {
            "model": os.environ[f"LOCAL_MODEL_NAME_{key}"],
            "base_url": os.environ[f"LOCAL_BASE_URL_{key}"],
            "api_key": os.environ.get(f"LOCAL_API_KEY_{key}", "any"),
        }

    def gemini_config(key):
        return {
            "model": os.environ[f"GEMINI_MODEL_NAME_{key}"],
            "api_key": os.environ[f"GEMINI_API_KEY_{key}"],
            "api_type": "google",
        }

    def create_config(config_list):
        config = {
            "config_list": config_list,
            "top_p": 1.0,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
            # "stream": False,
            "timeout": 600
        }

        # Add temperature only if it is not "remove"
        if temperature != "remove":
            config["temperature"] = temperature if temperature is not None else 0.3

        # Add reasoning_effort if it is not None
        if reasoning_effort is not None:
            config["reasoning_effort"] = reasoning_effort

        return config

    configs = []
    for kind, key in zip(model_kinds, ["W", "B"]):
        if kind == "azure":
            configs.append(create_config([azure_config(key)]))
        elif kind == "local":
            configs.append(create_config([local_config(key)]))
        elif kind == "gemini":
            configs.append(create_config([gemini_config(key)]))

    for config in configs:
        config["cache_seed"] = None

    return configs[0], configs[1]


def generate_game_stats(
    time_started: str,
    winner: str,
    reason: str,
    current_move: int,
    player_white: Any,
    player_black: Any,
    material_count: dict,
    pgn_string: str = None,
) -> dict:
    """Generate game statistics."""
    white_summary = gather_usage_summary([player_white])
    black_summary = gather_usage_summary([player_black])

    stats = {
        "time_started": time_started,
        "winner": winner,
        "reason": reason,
        "number_of_moves": current_move,
        "player_white": {
            "name": player_white.name,
            "wrong_moves": player_white.wrong_moves,
            "wrong_actions": player_white.wrong_actions,
            "reflections_used": player_white.reflections_used,
            "reflections_used_before_board": player_white.reflections_used_before_board,
            "model": (
                player_white.llm_config["config_list"][0]["model"]
                if isinstance(player_white.llm_config, dict)
                else "N/A"
            ),
        },
        "material_count": material_count,
        "player_black": {
            "name": player_black.name,
            "wrong_moves": player_black.wrong_moves,
            "wrong_actions": player_black.wrong_actions,
            "reflections_used": player_black.reflections_used,
            "reflections_used_before_board": player_black.reflections_used_before_board,
            "model": (
                player_black.llm_config["config_list"][0]["model"]
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
    
    # Add PGN string if available
    if pgn_string:
        stats["pgn"] = pgn_string
    
    return stats


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
        if os.path.exists(
            filename
        ):  # if running automated games they can complete within same second
            base, ext = os.path.splitext(filename)
            import time

            timestamp = int(time.time() * 1000)
            filename = f"{base}_{timestamp}{ext}"
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
    
    # Print PGN if available
    if "pgn" in game_stats:
        print("\n\033[96mGame PGN:\033[0m")
        print(game_stats["pgn"])

    print("\nCosts per agent (white and black):\n")
    if white_summary:
        pprint(white_summary["usage_excluding_cached_inference"])
    if black_summary:
        pprint(black_summary["usage_excluding_cached_inference"])


def setup_console_logging(log_folder, filename="output.txt"):
    """
    Redirect console output to a file and optionally also print to the console.

    Args:
        log_folder (str): The folder where the log file will be saved.
        filename (str): The name of the log file. Defaults to "output.txt".
    """
    log_file_path = os.path.join(log_folder, filename)
    os.makedirs(log_folder, exist_ok=True)  # Ensure the log folder exists
    log_file = open(log_file_path, "w")

    # Regular expression to match ANSI escape codes
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

    # Redirect stdout and stderr to the log file
    class Tee:
        def __init__(self, *streams):
            self.streams = streams

        def write(self, data):
            # Write original data (with ANSI codes) to the console
            for stream in self.streams:
                if stream == log_file:
                    # Remove ANSI escape codes before writing to the log file
                    cleaned_data = ansi_escape.sub('', data)
                    stream.write(cleaned_data)
                else:
                    # Write original data (with ANSI codes) to the console
                    stream.write(data)
                stream.flush()

        def flush(self):
            for stream in self.streams:
                stream.flush()

    # Redirect stdout and stderr to both console and file
    sys.stdout = Tee(sys.__stdout__, log_file)
    sys.stderr = Tee(sys.__stderr__, log_file)