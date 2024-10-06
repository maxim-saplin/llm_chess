import os
from dotenv import load_dotenv

load_dotenv()

import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import cairosvg
import io
import numpy as np
from moviepy.editor import ImageSequenceClip
import chess.svg

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
