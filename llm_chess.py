import time
from typing import Any, Dict, List, Optional, Union
import chess
import chess.svg
from pprint import pprint
from autogen import Agent, ConversableAgent, gather_usage_summary
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
# llm_config_white = llm_config_black
max_game_turns = 100  # maximum number of game moves before terminating
max_llm_turns = 10  # how many turns can an LLM make while making a move
max_failed_attempts = 3  # number of wrong replies/actions before halting the game and giving the player a loss
throttle_delay_moves = 1  # some LLM provider might thorttle frequent API reuqests, make a delay (in seconds) between moves

# Init chess board
board = chess.Board()
game_over = False
winner = None
reason = None
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
    return ",".join([str(move) for move in board.legal_moves])


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

# termination_messages = ["You won!", "I won!", "It's a tie!"]
moved_condition = "Move done, switching player"
too_many_failed_actions = "Too many wrong actions, interrupting"
termination_conditions = [
    moved_condition.lower(),
    too_many_failed_actions.lower(),
]

common_prompt = """Now is your turn to make a move. Before making a move you can pick one of 3 actions:
    - 'get_current_board' to get the schema and current status of the board
    - 'get_legal_moves' to get a UCI formatted list of available moves
    - 'make_move <UCI formatted move>' when you are ready complete your turn (e.g., 'make_move e2e4')
Respond with the action.
"""
# Respond with the [action] or [termination message] if the game is finished ({', '.join(termination_messages)}).

invalid_action_message = (
    "Invalid action. Pick one, reply exactly with the name and space delimetted argument: "
    "get_current_board, get_legal_moves, make_move <UCI formatted move>"
)

player_white = ConversableAgent(
    name="Player_White",
    # Not using system message as some LLMs can ignore it
    system_message="",
    description="You are a professional chess player and you play as white. "
    + common_prompt,
    llm_config=llm_config_white,
    is_termination_msg=lambda msg: any(
        term_msg == msg["content"].lower().strip()
        for term_msg in termination_conditions
    ),
    human_input_mode="NEVER",
)

player_black = ConversableAgent(
    name="Player_Black",
    system_message="",
    description="You are a professional chess player and you play as black. "
    + common_prompt,
    llm_config=llm_config_black,
    is_termination_msg=lambda msg: any(
        term_msg == msg["content"].lower().strip()
        for term_msg in termination_conditions
    ),
    human_input_mode="NEVER",
)

failed_action_attempts = 0


# This fu..ing Autogen drives me crazy, some spagetti code with broken logic and common sense...
# Spend hours debuging circular loops in termination message and prompt and figuring out None is not good for system message
# Termination approach is hoooooorible
class AutoReplyAgent(ConversableAgent):
    def generate_reply(
        self,
        messages: Optional[List[Dict[str, Any]]] = None,
        sender: Optional["Agent"] = None,
        **kwargs: Any,
    ) -> Union[str, Dict, None]:
        # Termination, who could have guessed, fucking Autogen
        if messages[-1]["name"] == self.name:
            return None
        action_choice = messages[-1]["content"].lower().strip()

        reply = ""
        global failed_action_attempts

        # Use a switch statement to call the corresponding function
        if "get_current_board" in action_choice:
            reply = get_current_board()
        elif "get_legal_moves" in action_choice:
            reply = get_legal_moves()
        elif action_choice.startswith("make_move"):
            try:
                # Extract the move from the response
                move = action_choice.split()[-1]
                make_move(move)
                reply = moved_condition
            # TODO, stats, wrong moves per player (not accounted in wwrong actions)
            except Exception as e:
                reply = f"Failed to make move: {e}"
                failed_action_attempts += 1
        else:
            reply = invalid_action_message
            failed_action_attempts += 1

        # TODO, stats, wrong actions per player
        if failed_action_attempts >= max_failed_attempts:
            print(reply)
            reply = too_many_failed_actions

        return reply


proxy_agent = AutoReplyAgent(
    name="Proxy",
    human_input_mode="NEVER",
    llm_config=llm_config_white,
    is_termination_msg=lambda msg: any(
        term_msg == msg["content"].lower().strip()
        for term_msg in termination_conditions
    ),
)


# for player in [player_white, player_black]:
#     proxy_agent.register_reply(
#         player,
#         reply_func=auto_reply,
#         # config={"callback": None},
#     )

# The Game

try:
    current_move = 0

    while current_move < max_game_turns and not board.is_game_over() and not game_over:
        for player in [player_white, player_black]:
            failed_action_attempts = 0
            chat_result = proxy_agent.initiate_chat(
                recipient=player,
                message=player.description,
                max_turns=max_llm_turns,
            )
            current_move += 1
            last_message = chat_result.summary
            print(f"\033[94mMOVE {current_move}\033[0m")
            print(f"\033[94mLast Message: {last_message}\033[0m")
            _, last_usage = list(
                chat_result.cost["usage_including_cached_inference"].items()
            )[-1]
            print(f"\033[94mPrompt Tokens: {last_usage['prompt_tokens']}\033[0m")
            print(
                f"\033[94mCompletion Tokens: {last_usage['completion_tokens']}\033[0m"
            )
            if last_message.lower().strip() == too_many_failed_actions:
                game_over = True
                winner = (
                    player_black.name if player == player_white else player_white.name
                )
                reason = (
                    "Opponent chose wrong actions to many times failing to make a move"
                )
            elif board.is_game_over():
                game_over = True
                if board.is_checkmate():
                    winner = player_black.name if board.turn else player_white.name
                    reason = "Checkmate"
                elif board.is_stalemate():
                    winner = "NONE"
                    reason = "Stalemate"
                elif board.is_insufficient_material():
                    winner = "NONE"
                    reason = "Insufficient material"
                # elif board.is_seventyfive_moves():
                #     reason = "Seventy-five moves rule"
                # elif board.is_fivefold_repetition():
                #     reason = "Fivefold repetition"
            else:
                winner = "NONE"
                reason = f"Unknown issue, {player_white.name if player == player_white else player_white.name} failed to make a move"
            player.clear_history()
            proxy_agent.clear_history()
            time.sleep(throttle_delay_moves)

    if not reason and current_move >= max_game_turns:
        winner = "NONE"
        reason = "Max moves reached"


except Exception as e:
    print("\033[91mExecution was halted due to error.\033[0m")
    print(f"Exception details: {e}")
    raise e

if game_over:
    print(f"\033[92m{winner} wins due to {reason}.\033[0m")

if frames:
    clip = ImageSequenceClip(frames, fps=1)
    clip.write_videofile(
        f"llm_chess_{time.strftime('%H:%M_%d.%m.%Y')}.mp4", codec="libx264"
    )
else:
    print("No frames to save to a video file")

print("\033[92m\nCOMPLETED THE GAME\n\033[0m")


print("\nCosts per agent:\n")
white_summary = gather_usage_summary([player_white])
black_summary = gather_usage_summary([player_black])

if white_summary:
    pprint(white_summary)
if black_summary:
    pprint(black_summary)
# input("Press any key to quit...")
