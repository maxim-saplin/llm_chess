import time
import traceback
from typing import Any, Dict
import chess
import chess.svg
from autogen import ConversableAgent
from custom_agents import RandomPlayerAgent, AutoReplyAgent
from utils import (
    calculate_material_count,
    generate_game_stats,
    get_llms_autogen,
    display_board,
    display_store_game_video_and_stats,
)
from typing_extensions import Annotated


use_random_player = True  # if True the randomm player will be assinged to White player, it will randomly pick any legal move and make it
max_game_moves = 200  # maximum number of game moves before terminating
max_llm_turns = 10  # how many turns can an LLM make while making a move
max_failed_attempts = 3  # number of wrong replies/actions before halting the game and giving the player a loss
throttle_delay_moves = 1  # some LLM provider might thorttle frequent API reuqests, make a delay (in seconds) between moves
time_started = time.strftime("%Y.%m.%d_%H:%M")

# Action names
get_current_board_action = "get_current_board"
get_legal_moves_action = "get_legal_moves"
make_move_action = "make_move"

# LLM

llm_config_white, llm_config_black = get_llms_autogen()
# llm_config_white = llm_config_black  # Quick hack to use same model
# llm_config_black = llm_config_white

# Init chess board
material_count = {"white": 0, "black": 0}
board = chess.Board()
game_over = False
winner = None
reason = None


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
move_was_made = "Move made, switching player"
too_many_failed_actions_message = "Too many wrong actions, interrupting"
termination_conditions = [
    move_was_made.lower(),
    too_many_failed_actions_message.lower(),
]

# Action names
get_current_board_action = "get_current_board"
get_legal_moves_action = "get_legal_moves"
make_move_action = "make_move"


common_prompt = f"""Now is your turn to make a move. Before making a move you can pick one of 3 actions:
    - '{get_current_board_action}' to get the schema and current status of the board
    - '{get_legal_moves_action}' to get a UCI formatted list of available moves
    - '{make_move_action} <UCI formatted move>' when you are ready to complete your turn (e.g., '{make_move_action} e2e4')
Respond with the action.
"""

invalid_action_message = (
    "Invalid action. Pick one, reply exactly with the name and space delimetted argument: "
    "get_current_board, get_legal_moves, make_move <UCI formatted move>"
)


def is_termination_message(msg: Dict[str, Any]) -> bool:
    return any(
        term_msg == msg["content"].lower().strip()
        for term_msg in termination_conditions
    )


player_white = ConversableAgent(
    name="Player_White",
    # Not using system message as some LLMs can ignore it
    system_message="",
    description="You are a professional chess player and you play as white. "
    + common_prompt,
    llm_config=llm_config_white,
    is_termination_msg=is_termination_message,
    human_input_mode="NEVER",
)

# This fu..ing Autogen drives me crazy, some spagetti code with broken logic and common sense...
# Spend hours debuging circular loops in termination message and prompt and figuring out None is not good for system message
# Termination approach is hoooooorible
player_black = ConversableAgent(
    name="Player_Black",
    system_message="",
    description="You are a professional chess player and you play as black. "
    + common_prompt,
    llm_config=llm_config_black,
    is_termination_msg=is_termination_message,
    human_input_mode="NEVER",
)


failed_action_attempts = 0


# Instantiate RandomPlayer
random_player = RandomPlayerAgent(
    name="Random_Player",
    system_message="",
    description="You are a random chess player.",
    human_input_mode="NEVER",
    is_termination_msg=is_termination_message,
    make_move_action=make_move_action,
    get_legal_moves_action=get_legal_moves_action,
)

if use_random_player:
    player_white = random_player

proxy_agent = AutoReplyAgent(
    name="Proxy",
    human_input_mode="NEVER",
    is_termination_msg=is_termination_message,
    max_failed_attempts=max_failed_attempts,
    get_current_board=get_current_board,
    get_legal_moves=get_legal_moves,
    make_move=make_move,
    move_was_made_message=move_was_made,
    invalid_action_message=invalid_action_message,
    too_many_failed_actions_message=too_many_failed_actions_message,
    get_current_board_action=get_current_board_action,
    get_legal_moves_action=get_legal_moves_action,
    make_move_action=make_move_action,
)

# The Game

for player in [player_white, player_black]:
    player.wrong_moves = 0
    player.wrong_actions = 0
    player.material_count = {"white": 0, "black": 0}

try:
    current_move = 0

    while current_move < max_game_moves and not board.is_game_over() and not game_over:
        for player in [player_white, player_black]:
            proxy_agent.failed_action_attempts = 0
            chat_result = proxy_agent.initiate_chat(
                recipient=player,
                message=player.description,
                max_turns=max_llm_turns,
            )
            current_move += 1
            last_message = chat_result.summary
            print(f"\033[94mMADE MOVE {current_move}\033[0m")
            print(f"\033[94mLast Message: {last_message}\033[0m")
            _, last_usage = list(
                chat_result.cost["usage_including_cached_inference"].items()
            )[-1]

            white_material, black_material = calculate_material_count(board)
            print(
                f"\033[94mMaterial Count - White: {white_material}, Black: {black_material}\033[0m"
            )
            material_count["white"] = white_material
            material_count["black"] = black_material

            prompt_tokens = (
                last_usage["prompt_tokens"] if isinstance(last_usage, dict) else 0
            )
            completion_tokens = (
                last_usage["completion_tokens"] if isinstance(last_usage, dict) else 0
            )
            print(f"\033[94mPrompt Tokens: {prompt_tokens}\033[0m")
            print(f"\033[94mCompletion Tokens: {completion_tokens}\033[0m")
            if (
                last_message.lower().strip()
                == too_many_failed_actions_message.lower().strip()
            ):
                game_over = True
                winner = (
                    player_black.name if player == player_white else player_white.name
                )
                reason = f"{player.name} chose wrong actions to many times failing to make a move"
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
            elif last_message.lower().strip() != move_was_made.lower().strip():
                game_over = True
                winner = "NONE"
                reason = f"Unknown issue, {player.name} failed to make a move"
            proxy_agent.clear_history()
            time.sleep(throttle_delay_moves)
            if game_over:
                break

    if not reason and current_move >= max_game_moves:
        winner = "NONE"
        reason = "Max moves reached"


except Exception as e:
    print("\033[91mExecution was halted due to error.\033[0m")
    print(f"Exception details: {e}")
    traceback.print_exc()
    winner = "NONE"
    reason = "ERROR OCCURED"

game_stats = generate_game_stats(
    time_started,
    winner,
    reason,
    current_move,
    player_white,
    player_black,
    material_count,
)

display_store_game_video_and_stats(game_stats)
# input("Press any key to quit...")
