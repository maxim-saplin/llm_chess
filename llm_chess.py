import time
import traceback
from typing import Any, Dict
from enum import Enum
import chess
import chess.svg
from custom_agents import (
    GameAgent,
    RandomPlayerAgent,
    AutoReplyAgent,
    ChessEngineSunfishAgent,
    ChessEngineStockfishAgent,
)

from utils import (
    calculate_material_count,
    generate_game_stats,
    get_llms_autogen,
    display_board,
    display_store_game_video_and_stats,
)
from typing_extensions import Annotated


class TerminationReason(Enum):
    TOO_MANY_WRONG_ACTIONS = "Too many wrong actions"
    CHECKMATE = "Checkmate"
    STALEMATE = "Stalemate"
    INSUFFICIENT_MATERIAL = "Insufficient material"
    SEVENTYFIVE_MOVES = "Seventy-five moves rule"
    FIVEFOLD_REPETITION = "Fivefold repetition"
    MAX_TURNS = "Max turns in single dialog"
    UNKNOWN_ISSUE = "Unknown issue, failed to make a move"
    MAX_MOVES = "Max moves reached"
    ERROR = "ERROR OCCURED"


class PlayerType(Enum):
    LLM_WHITE = 1  # Represents a white player controlled by an LLM and using *_W config keys from .env
    LLM_BLACK = 2  # Represents a black player controlled by an LLM and using *_B config keys from .env
    RANDOM_PLAYER = 3  # Represents a player making random moves
    CHESS_ENGINE_SUNFISH = 4
    CHESS_ENGINE_STOCKFISH = 5


# Hyper params such as temperature are defined in `utils.py`
white_player_type = PlayerType.RANDOM_PLAYER
black_player_type = PlayerType.LLM_BLACK
enable_reflection = False  # Whether to offer the LLM time to think and evaluate moves
use_fen_board = False  # Whther to use graphical UNICODE representation board OR single line FEN format (returned from get_current_board)
max_game_moves = 200  # maximum number of game moves before terminating
max_llm_turns = 10  # how many conversation turns can an LLM make deciding on a move, e.g. repeating valid actions many times
max_failed_attempts = 3  # count of wrong replies in a single-move dialog (e.g. non existing action) before stopping the game, giving a loss
throttle_delay = 3  # some LLM providers might thorttle frequent API reuqests, make a delay (in seconds) between moves
dialog_turn_delay = 6  # adds a delay in seconds inside auto reply agent, i.e. delays between turns in a dialog happenning within a move
random_print_board = (
    False  # if set to True the random player will also print it's board to Console
)
visualize_board = True  # You can skip board visualization to speed up execution
remove_description = False  # Turns out Autogen can substitute system message with decription, o1-mini doesn't support system role

temp_override = None  # Set to None to use defaults, o1-mini fails with any params other than 1.0 (added as a workaround for o1-mini)

# Add a warning if both remove_description is True or False and temp_override is not None
if (remove_description in [True]) and temp_override is not None:
    print(
        "\033[93mWarning: 'remove_description' is set to True and 'temp_override' is not None."
        " This overrides ARE ONLY NEEDED to o1 models\033[0m"
    )

stockfish_path = "/opt/homebrew/bin/stockfish"


def run(log_dir="_logs", save_logs=True):

    time_started = time.strftime("%Y.%m.%d_%H:%M")

    # Action names
    get_current_board_action = "get_current_board"
    get_legal_moves_action = "get_legal_moves"
    make_move_action = "make_move"

    # LLM

    llm_config_white, llm_config_black = get_llms_autogen(temp_override)
    # llm_config_white = llm_config_black  # Quick hack to use same model

    # Init chess board
    material_count = {"white": 0, "black": 0}
    board = chess.Board()
    game_over = False
    winner = None
    reason = None

    # Actions

    def get_legal_moves() -> Annotated[str, "A list of legal moves in UCI format"]:
        if board.legal_moves.count() == 0:
            return None
        return ",".join([str(move) for move in board.legal_moves])

    if black_player_type == PlayerType.CHESS_ENGINE_SUNFISH and not use_fen_board:
        print(
            "Warning: Chess engine SUNFISH is selected but FEN board is not used. It will fail"
        )

    def get_current_board() -> (
        Annotated[str, "A text representation of the current board state"]
    ):
        return board.fen() if use_fen_board else board.unicode()

    def make_move(
        move: Annotated[str, "A move in UCI format."]
    ) -> Annotated[str, "Result of the move."]:
        move = chess.Move.from_uci(move)
        board.push_uci(str(move))
        if visualize_board:
            display_board(board, move)
        # print(",".join([str(move) for move in board.legal_moves]))

    # Agents

    # termination_messages = ["You won!", "I won!", "It's a tie!"]
    move_was_made = "Move made, switching player"
    termination_conditions = [
        move_was_made.lower(),
        TerminationReason.TOO_MANY_WRONG_ACTIONS.value.lower(),
    ]

    # Action names
    get_current_board_action = "get_current_board"
    get_legal_moves_action = "get_legal_moves"
    reflect_action = "do_reflection"
    make_move_action = "make_move"

    common_prompt = (
        "Now is your turn to make a move. Before making a move you can pick one of the following actions:\n"
        f"- '{get_current_board_action}' to get the schema and current status of the board\n"
        f"- '{get_legal_moves_action}' to get a UCI formatted list of available moves\n"
        f"{f"- '{reflect_action}' to take a moment to think about your strategy\n" if enable_reflection else ""}"
        f"- '{make_move_action} <UCI formatted move>' when you are ready to complete your turn (e.g., '{make_move_action} e2e4')"
    )

    reflect_prompt = (
        "Before deciding on the next move you can reflect on your current situation, write down notes and evaluate.\n"
        "Here're a few recommendations that you can follow to make a better move decision:\n"
        "- Shortlist the most valuable next moves\n"
        "- Consider how they affect the situation\n"
        "- What could be the next moves from your opponent in each case\n"
        "- Is there any strategy fitting the situation and your choice of moves\n"
        "- Rerank the shortlisted moves based on the previous steps\n"
    )

    reflection_followup_prompt = (
        "Now that you reflected please choose any of the valid actions: "
        f"{get_current_board_action}, {get_legal_moves_action}, {reflect_action}, "
        f"{make_move_action} <UCI formatted move>"
    )

    invalid_action_message = (
        f"Invalid action. Pick one, reply exactly with the name and space delimitted argument: "
        f"{get_current_board_action}, {get_legal_moves_action}"
        f"{', ' + reflect_action if enable_reflection else ''}"
        f", {make_move_action} <UCI formatted move>"
    )

    # This fu..ing Autogen drives me crazy, some spagetti code with broken logic and common sense...
    # Spend hours debuging circular loops in termination message and prompt and figuring out None is not good for system message
    # Termination approach is hoooooorible
    def is_termination_message(msg: Dict[str, Any]) -> bool:
        return any(
            term_msg == msg["content"].lower().strip()
            for term_msg in termination_conditions
        )

    llm_white = GameAgent(
        name="Player_White",
        # Not using system message as some LLMs can ignore it
        system_message="",
        description=(
            ""
            if remove_description
            else "You are a professional chess player and you play as white. "
            + common_prompt
        ),
        llm_config=llm_config_white,
        is_termination_msg=is_termination_message,
        human_input_mode="NEVER",
        dialog_turn_delay=dialog_turn_delay,
    )

    llm_black = GameAgent(
        name="Player_Black",
        system_message="",
        description="You are a professional chess player and you play as black. "
        + common_prompt,
        llm_config=llm_config_black,
        is_termination_msg=is_termination_message,
        human_input_mode="NEVER",
        dialog_turn_delay=dialog_turn_delay,
    )

    random_player = RandomPlayerAgent(
        name="Random_Player",
        system_message="",
        description="You are a random chess player.",
        human_input_mode="NEVER",
        is_termination_msg=is_termination_message,
        make_move_action=make_move_action,
        get_legal_moves_action=get_legal_moves_action,
        get_current_board_action=(
            get_current_board_action if random_print_board else None
        ),
    )

    proxy_agent = AutoReplyAgent(
        name="Proxy",
        human_input_mode="NEVER",
        is_termination_msg=is_termination_message,
        max_failed_attempts=max_failed_attempts,
        get_legal_moves=get_legal_moves,
        get_current_board=get_current_board,
        make_move=make_move,
        move_was_made_message=move_was_made,
        invalid_action_message=invalid_action_message,
        too_many_failed_actions_message=TerminationReason.TOO_MANY_WRONG_ACTIONS.value,
        get_current_board_action=get_current_board_action,
        reflect_action=reflect_action,
        get_legal_moves_action=get_legal_moves_action,
        reflect_prompt=reflect_prompt,
        reflection_followup_prompt=reflection_followup_prompt,
        make_move_action=make_move_action,
    )

    player_white = {
        PlayerType.LLM_WHITE: llm_white,
        PlayerType.LLM_BLACK: llm_black,
        PlayerType.RANDOM_PLAYER: random_player,
        PlayerType.CHESS_ENGINE_SUNFISH: ChessEngineSunfishAgent(
            name="Chess_Engine_Sunfish_White",
            system_message="",
            description="You are a chess player using the Sunfish engine.",
            human_input_mode="NEVER",
            is_termination_msg=is_termination_message,
            make_move_action=make_move_action,
            get_current_board_action=get_current_board_action,
            is_white=True,
        ),
        PlayerType.CHESS_ENGINE_STOCKFISH: ChessEngineStockfishAgent(
            name="Chess_Engine_Stockfish_White",
            board=board,
            make_move_action=make_move_action,
            stockfish_path=stockfish_path,
            is_termination_msg=is_termination_message,
        ),
    }.get(white_player_type)

    player_black = {
        PlayerType.LLM_WHITE: llm_white,
        PlayerType.LLM_BLACK: llm_black,
        PlayerType.RANDOM_PLAYER: random_player,
        PlayerType.CHESS_ENGINE_SUNFISH: ChessEngineSunfishAgent(
            name="Chess_Engine_Sunfish_Black",
            system_message="",
            description="You are a chess player using the Sunfish engine.",
            human_input_mode="NEVER",
            is_termination_msg=is_termination_message,
            make_move_action=make_move_action,
            get_current_board_action=get_current_board_action,
            is_white=False,
        ),
        PlayerType.CHESS_ENGINE_STOCKFISH: ChessEngineStockfishAgent(
            name="Chess_Engine_Stockfish_Black",
            board=board,
            make_move_action=make_move_action,
            stockfish_path=stockfish_path,
            is_termination_msg=is_termination_message,
        ),
    }.get(black_player_type)

    for player in [player_white, player_black]:
        # Reflection counts are global
        player.reflections_used = 0
        player.reflections_used_before_board = 0
        player.material_count = {"white": 0, "black": 0}

    try:
        current_move = 0

        while (
            current_move < max_game_moves and not board.is_game_over() and not game_over
        ):
            for player in [player_white, player_black]:
                # Reset player state variables before each move: wrong_moves, wrong_actions, has_requested_board, failed_action_attempts
                proxy_agent.prep_to_move()
                player.prep_to_move()
                # player.wrong_moves = 0
                # player.wrong_actions = 0
                # player.has_requested_board = False
                # proxy_agent.failed_action_attempts = 0
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
                    last_usage["completion_tokens"]
                    if isinstance(last_usage, dict)
                    else 0
                )
                print(f"\033[94mPrompt Tokens: {prompt_tokens}\033[0m")
                print(f"\033[94mCompletion Tokens: {completion_tokens}\033[0m")
                if (
                    last_message.lower().strip()
                    == TerminationReason.TOO_MANY_WRONG_ACTIONS.value.lower().strip()
                ):
                    game_over = True
                    winner = (
                        player_black.name
                        if player == player_white
                        else player_white.name
                    )
                    # reason = f"{player.name} chose wrong actions to many times failing to make a move"
                    reason = TerminationReason.TOO_MANY_WRONG_ACTIONS.value
                elif board.is_game_over():
                    game_over = True
                    if board.is_checkmate():
                        winner = player_black.name if board.turn else player_white.name
                        reason = TerminationReason.CHECKMATE.value
                    elif board.is_stalemate():
                        winner = "NONE"
                        reason = TerminationReason.STALEMATE.value
                    elif board.is_insufficient_material():
                        winner = "NONE"
                        reason = TerminationReason.INSUFFICIENT_MATERIAL.value
                    elif board.is_seventyfive_moves():
                        reason = TerminationReason.SEVENTYFIVE_MOVES.value
                    elif board.is_fivefold_repetition():
                        reason = TerminationReason.FIVEFOLD_REPETITION.value
                elif (
                    last_message.lower().strip() != move_was_made.lower().strip()
                    and len(chat_result.chat_history) >= max_llm_turns * 2
                ):
                    game_over = True
                    winner = (
                        player_black.name
                        if player == player_white
                        else player_white.name
                    )
                    reason = TerminationReason.MAX_TURNS.value
                elif last_message.lower().strip() != move_was_made.lower().strip():
                    game_over = True
                    winner = "NONE"
                    reason = TerminationReason.UNKNOWN_ISSUE.value
                proxy_agent.clear_history()
                time.sleep(throttle_delay)
                if game_over:
                    break

        if not reason and current_move >= max_game_moves:
            winner = "NONE"
            reason = TerminationReason.MAX_MOVES.value

    except Exception as e:
        print("\033[91mExecution was halted due to error.\033[0m")
        print(f"Exception details: {e}")
        traceback.print_exc()
        winner = "NONE"
        reason = TerminationReason.ERROR.value

    game_stats = generate_game_stats(
        time_started,
        winner,
        reason,
        current_move,
        player_white,
        player_black,
        material_count,
    )

    display_store_game_video_and_stats(game_stats, log_dir, save_logs)
    return game_stats, player_white, player_black


if __name__ == "__main__":
    run()
