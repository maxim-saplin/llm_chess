import time
import random
import traceback
from typing import Any, Dict, List, Optional, Union
import chess
import chess.svg
from pprint import pprint
from autogen import Agent, ConversableAgent, gather_usage_summary

from utils import get_llms_autogen, display_board, save_video
from typing_extensions import Annotated

# Global params

use_random_player = True  # if True the randomm player will be assinged to White player, it will randomly pick any legal move in every turn
max_game_turns = 10  # maximum number of game moves before terminating
max_llm_turns = 10  # how many turns can an LLM make while making a move
max_failed_attempts = 3  # number of wrong replies/actions before halting the game and giving the player a loss
throttle_delay_moves = 1  # some LLM provider might thorttle frequent API reuqests, make a delay (in seconds) between moves

# LLM

llm_config_white, llm_config_black = get_llms_autogen()
llm_config_white = llm_config_black  # Quick hack to use same model

# Init chess board
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
too_many_failed_actions = "Too many wrong actions, interrupting"
termination_conditions = [
    move_was_made.lower(),
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


class RandomPlayer(ConversableAgent):
    def generate_reply(
        self,
        messages: Optional[List[Dict[str, Any]]] = None,
        sender: Optional["Agent"] = None,
        **kwargs: Any,
    ) -> Union[str, Dict, None]:
        # Termination
        if self._is_termination_msg(messages[-1]):
            return None

        last_message = messages[-1]["content"].lower().strip()

        try:
            legal_moves = last_message.split(",")
            if legal_moves:
                random_move = random.choice(legal_moves)
                if chess.Move.from_uci(random_move).uci() == random_move:
                    return f"make_move {random_move}"
                return "get_legal_moves"
        except Exception:
            return "get_legal_moves"

        return "get_legal_moves"


# Instantiate RandomPlayer
random_player = RandomPlayer(
    name="Random_Player",
    system_message="",
    description="You are a random chess player.",
    llm_config=llm_config_white,
    human_input_mode="NEVER",
    is_termination_msg=is_termination_message,
)

if use_random_player:
    player_white = random_player


# TODO, try out self-reflection by giving some of the agent ability to evaluate several moves,
# i.e. add 4th "consider" action which will engage LLM to make few turns duscissing the board
# and next move, can be same agent with LLM config and generate_reply() method deciding when
# to hand over the contorol
class AutoReplyAgent(ConversableAgent):
    def generate_reply(
        self,
        messages: Optional[List[Dict[str, Any]]] = None,
        sender: Optional["Agent"] = None,
        **kwargs: Any,
    ) -> Union[str, Dict, None]:
        # Termination, who could have guessed, fucking Autogen
        if self._is_termination_msg(messages[-1]):
            return None
        # if messages[-1]["name"] == self.name:
        #     return None
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
                reply = move_was_made
            # TODO, stats, wrong moves per player (not accounted in wwrong actions)
            except Exception as e:
                reply = f"Failed to make move: {e}"
                failed_action_attempts += 1
                sender.wrong_moves += 1
        else:
            reply = invalid_action_message
            failed_action_attempts += 1
            sender.wrong_actions += 1

        # TODO, stats, wrong actions per player
        if failed_action_attempts >= max_failed_attempts:
            print(reply)
            reply = too_many_failed_actions

        return reply


proxy_agent = AutoReplyAgent(
    name="Proxy",
    human_input_mode="NEVER",
    llm_config=llm_config_white,
    is_termination_msg=is_termination_message,
)


# for player in [player_white, player_black]:
#     proxy_agent.register_reply(
#         player,
#         reply_func=auto_reply,
#         # config={"callback": None},
#     )

# The Game

# Initialize fields dynamically
player_white.wrong_moves = 0
player_white.wrong_actions = 0
player_black.wrong_moves = 0
player_black.wrong_actions = 0

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
            print(f"\033[94mMADE OVE {current_move}\033[0m")
            print(f"\033[94mLast Message: {last_message}\033[0m")
            _, last_usage = list(
                chat_result.cost["usage_including_cached_inference"].items()
            )[-1]
            prompt_tokens = (
                last_usage["prompt_tokens"] if isinstance(last_usage, dict) else 0
            )
            completion_tokens = (
                last_usage["completion_tokens"] if isinstance(last_usage, dict) else 0
            )
            print(f"\033[94mPrompt Tokens: {prompt_tokens}\033[0m")
            print(f"\033[94mCompletion Tokens: {completion_tokens}\033[0m")
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
            elif last_message.lower().strip() != move_was_made.lower().strip():
                game_over = True
                winner = "NONE"
                reason = f"Unknown issue, {player.name} failed to make a move"
            player.clear_history()
            proxy_agent.clear_history()
            time.sleep(throttle_delay_moves)

    if not reason and current_move >= max_game_turns:
        winner = "NONE"
        reason = "Max moves reached"


except Exception as e:
    print("\033[91mExecution was halted due to error.\033[0m")
    print(f"Exception details: {e}")
    traceback.print_exc()
    winner = "NONE"
    reason = "ERROR OCCURED"

save_video(f"llm_chess_{time.strftime('%H:%M_%d.%m.%Y')}.mp4")

print("\033[92m\nGAME OVER\n\033[0m")
print(f"\033[92m{winner} wins due to {reason}.\033[0m")
print(f"\033[92mNumber of moves made: {current_move}\033[0m")
print("\nWrong Moves (LLM asked to make illegal/impossible move):")
print(f"Player White: {player_white.wrong_moves}")
print(f"Player Black: {player_black.wrong_moves}")

print("\nWrong Actions (LLM responded with non parseable message):")
print(f"Player White: {player_white.wrong_actions}")
print(f"Player Black: {player_black.wrong_actions}")

print("\nCosts per agent (white and black):\n")
white_summary = gather_usage_summary([player_white])
black_summary = gather_usage_summary([player_black])

if white_summary:
    pprint(white_summary["usage_excluding_cached_inference"])
if black_summary:
    pprint(black_summary["usage_excluding_cached_inference"])
# input("Press any key to quit...")
