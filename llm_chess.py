import time
import chess
import chess.svg
from pprint import pprint
from autogen import ConversableAgent, gather_usage_summary
from moviepy.editor import ImageSequenceClip
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import cairosvg
import io
import numpy as np
from typing_extensions import Annotated
from dotenv import load_dotenv
from utils import get_llms_autogen

load_dotenv()

llm_config_white, llm_config_black = get_llms_autogen()
max_turns = (
    100  # maximum number of conversation turns in upper level chat between players
)

# Init chess board
board = chess.Board()
made_move = False
frames = []
fig = plt.figure()


def display_board(board, move):
    svg = chess.svg.board(
        board,
        arrows=[(move.from_square, move.to_square)],
        fill={move.from_square: "gray"},
        size=200,
    )
    png_data = cairosvg.svg2png(bytestring=svg.encode("utf-8"), dpi=200)
    img = mpimg.imread(io.BytesIO(png_data), format="png")

    # Display the image
    plt.imshow(img)
    plt.axis("off")
    fig = plt.gcf()
    fig.set_dpi(200)
    plt.pause(0.1)

    # Convert the image to a NumPy array for video frames
    fig.canvas.draw()
    io_buf = io.BytesIO()
    fig.savefig(io_buf, format="raw", dpi=200)
    io_buf.seek(0)
    frame = np.reshape(
        np.frombuffer(io_buf.getvalue(), dtype=np.uint8),
        newshape=(int(fig.bbox.bounds[3]), int(fig.bbox.bounds[2]), -1),
    )
    global frames
    frames.append(frame)

    plt.clf()


# Actions


def get_legal_moves() -> Annotated[str, "A list of legal moves in UCI format"]:
    if board.legal_moves.count() == 0:
        global made_move
        made_move = True
        return "You won!"
    return "Legal moves: " + ",".join([str(move) for move in board.legal_moves])


def get_current_board() -> (
    Annotated[str, "A text representation of the current board state"]
):
    return board.unicode()


def make_move(
    move: Annotated[str, "A move in UCI format."]
) -> Annotated[str, "Result of the move."]:
    move = chess.Move.from_uci(move)
    board.push_uci(str(move))
    global made_move
    made_move = True
    display_board(board, move)


# Agents

termination_messages = ["You won!", "I won!", "It's a tie!"]

common_prompt = f"""Now is your turn to make a move. Before making a move you can pick one of 3 actions:
    - 'get_current_board' to get the schema and current status of the board
    - 'get_legal_moves' to get a UCI formatted list of available moves
    - 'make_move <UCI formatted move>' when you are ready complete your turn (e.g., 'make_move e2e4')
Respond with the [action] or [termination message] if the game is finished ({', '.join(termination_messages)}).
"""

player_white = ConversableAgent(
    name="Player_White",
    system_message="You are a professional chess player and you play as white. "
    + common_prompt,
    llm_config=llm_config_white,
    is_termination_msg=lambda msg: any(
        term_msg.lower() in msg["content"].lower() for term_msg in termination_messages
    ),
)

player_black = ConversableAgent(
    name="Player_Black",
    system_message="You are a professional chess player and you play as black. "
    + common_prompt,
    llm_config=llm_config_black,
    is_termination_msg=lambda msg: "you won" in msg["content"].lower(),
)

# The Game

try:
    current_turn = 0

    while current_turn < max_turns:
        for player in [player_white, player_black]:
            failed_action_attempts = 0
            max_failed_attempts = 3
            action = player.initiate_chat(
                player_white if player == player_black else player_black,
                message=common_prompt,
                max_turns=1,
            )

            # Parse the response to get the chosen action
            action_choice = action.lower().strip()

            # Use a switch statement to call the corresponding function
            if action_choice == "get_current_board":
                print(get_current_board())
                failed_action_attempts = 0
            elif action_choice == "get_legal_moves":
                print(get_legal_moves())
                failed_action_attempts = 0
            elif action_choice.startswith("make_move"):
                try:
                    # Extract the move from the response
                    move = action_choice.split()[-1]
                    print(make_move(move))
                    failed_action_attempts = 0
                except Exception as e:
                    print(f"Failed to make move: {e}")
                    failed_action_attempts += 1
            else:
                print("Invalid action. Please choose a valid action.")
                failed_action_attempts += 1

            # Check for termination condition
            if (
                "you won" in action_choice
                or failed_action_attempts >= max_failed_attempts
            ):
                if failed_action_attempts >= max_failed_attempts:
                    print("Too many failed attempts. Ending the game.")
                break
        current_turn += 1

except Exception as e:
    print("\033[91mExecution was halted due to error.\033[0m")
    print(f"Exception details: {e}")

if len(frames) > 0:
    clip = ImageSequenceClip(frames, fps=1)
    clip.write_videofile(
        f"llm_chess_{time.strftime('%H:%M_%d.%m.%Y')}.mp4", codec="libx264"
    )
else:
    print("No frames to save to a video file")

print("\033[92m\nCOMPLETED THE GAME\n\033[0m")

# if hasattr(chat_result, "cost"):
#     print(f"\n\n\n COST\n{chat_result.cost} \n\n")

# if hasattr(chat_result, "chat_history"):
#     print(f"Number of turns taken: {len(chat_result.chat_history)/2}")

print("\nCosts per agent:\n")
white_summary = gather_usage_summary([player_white])
black_summary = gather_usage_summary([player_black])

if white_summary:
    pprint(white_summary)
if black_summary:
    pprint(black_summary)
# input("Press any key to quit...")
