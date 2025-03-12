import time, traceback, chess, chess.svg
from typing import Any, Dict
from enum import Enum
from custom_agents import GameAgent, RandomPlayerAgent, AutoReplyAgent, ChessEngineStockfishAgent
from utils import calculate_material_count, generate_game_stats, get_llms_autogen, display_board, display_store_game_video_and_stats

class BoardRepresentation(Enum):
    FEN_ONLY = 1
    UNICODE_ONLY = 2
    UNICODE_WITH_PGN = 3


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
    CHESS_ENGINE_STOCKFISH = 5

# Hyper params such as temperature are defined in `utils.py`
white_player_type = PlayerType.RANDOM_PLAYER
black_player_type = PlayerType.LLM_BLACK
enable_reflection = False  # Whether to offer the LLM time to think and evaluate moves
board_representation_mode = BoardRepresentation.UNICODE_ONLY  # What kind of board is printed in response to get_current_board

# Game configuration
max_game_moves = 200  # maximum number of game moves before terminating, dafault 200
max_llm_turns = 10  # how many conversation turns can an LLM make deciding on a move, e.g. repeating valid actions many times, default 10
max_failed_attempts = 3  # number of wrong replies within a dialog (e.g. non existing action) before stopping/giving a loss, default 3
throttle_delay = 1 # some LLM providers might thorttle frequent API reuqests, make a delay (in seconds) between moves
dialog_turn_delay = 1  # adds a delay in seconds inside LLM agent, i.e. delays between turns in a dialog happenning within a move
random_print_board = (
    False  # if set to True the random player will also print it's board to Console
)
visualize_board = False  # You can skip board visualization (animated board in popup window) to speed up execution

# Set to None to use defaults, "remove" to not send it
# o1-mini fails with any params other than 1.0 or not present, R1 distil recomends 0.5-0.7, kimi-k1.5-preview 0.3
temp_override = None

reasoning_effort = None # Default is None, used with OpenAI models low, medium, or high

# Tell AutoReply agent to remove given pieces of text from BOTH agents history when processing replies
# (using re.sub(self.ignore_text, '', action_choice, flags=re.DOTALL))
# It is needed to remove isolating thinking tokens. E.g. Deepseek R1 32B uses <think> tags that can have actions mentioned breaking execution (r"<think>.*?</think>")
# r"<think>.*?</think>" - Deepseek R1 Distil
# r"◁think▷.*?◁/think▷ - Kimi 1.5
# r"<reasoning>.*?</reasoning>" - Reka Flash
# Default None
remove_text = None

# Add warnings for both temp_override and reasoning_effort
if temp_override is not None:
    print(
        "\033[93mWarning: 'temp_override' is not None."
        " This override is only needed for special models (e.g., o1 requires temp 1.0, Deepseek R1 local models recommend 0.5 - 0.7)\033[0m"
    )
if reasoning_effort is not None:
    print(
        "\033[93mWarning: 'reasoning_effort' is set to '{}'."
        " This setting is only applicable to specific models and may not be supported by all models.\033[0m".format(reasoning_effort)
    )

stockfish_path = "/opt/homebrew/bin/stockfish"
reset_stockfish_history = (
    True  # If True, Stockfish will get no history before making a move, default is True
)
stockfish_level = 1  # Set to an integer (0-20) to override Stockfish skill level, or None to use default
stockfish_time_per_move = (
    0.1  # Time limit (in seconds) for Stockfish to think per move, default is 0.1
)

## Actions

board = chess.Board()
game_moves = []

def get_current_board() -> str:
    """
    Returns:
        str: A text representation of the current board state.
    """
    if board_representation_mode == BoardRepresentation.FEN_ONLY:
        return board.fen()
    elif board_representation_mode == BoardRepresentation.UNICODE_ONLY:
        return board.unicode()
    elif board_representation_mode == BoardRepresentation.UNICODE_WITH_PGN:
        pgn_header = (
            "[Event \"Chess Game\"]\n"
            f"[Date \"{time.strftime('%Y.%m.%d')}\"]\n"
            "[White \"Player White\"]\n"
            "[Black \"Player Black\"]\n"
            "[Result \"*\"]\n\n"
        )

        pgn_moves = ""
        for i, move in enumerate(game_moves):
            if i % 2 == 0:
                pgn_moves += f"{(i // 2) + 1}. {move} "
            else:
                pgn_moves += f"{move} "

            if i > 0 and i % 10 == 9:
                pgn_moves += "\n"

        return f"{board.unicode()}\n\nPGN:\n{pgn_header}{pgn_moves}"


def get_legal_moves() -> str:
    """
    Returns:
        str: A list of legal moves in UCI format, separated by commas.
    """
    if board.legal_moves.count() == 0:
        return None
    return ",".join([str(move) for move in board.legal_moves])


def make_move(move: str) -> str:
    """
    Args:
        move (str): A move in UCI format.

    Returns:
        str: Result of the move.
    """
    move_obj = chess.Move.from_uci(move)
    
    # Get the SAN representation of the move before making it
    san_move = board.san(move_obj)
    
    # Make the move and record it
    board.push(move_obj)
    game_moves.append(san_move)
    
    # Visualize the board if enabled
    if visualize_board:
        display_board(board, move_obj)
    # print(",".join([str(move) for move in board.legal_moves]))


def run(log_dir="_logs", save_logs=True):

    time_started = time.strftime("%Y.%m.%d_%H:%M")

    # Action names
    get_current_board_action = "get_current_board"
    get_legal_moves_action = "get_legal_moves"
    make_move_action = "make_move"

    # LLM
    llm_config_white, llm_config_black = get_llms_autogen(temp_override, reasoning_effort)
    # llm_config_white = llm_config_black  # Quick hack to use same model

    # Init chess board and game state
    material_count = {"white": 0, "black": 0}
    global board, game_moves
    board.reset()
    game_moves.clear()
    game_over = False
    winner = None
    reason = None

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
        + (
            f"- '{reflect_action}' to take a moment to think about your strategy\n"
            if enable_reflection
            else ""
        )
        + f"- '{make_move_action} <UCI formatted move>' when you are ready to complete your turn (e.g., '{make_move_action} e2e4')"
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
        description="",
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
        remove_text=remove_text,
    )

    player_white = {
        PlayerType.LLM_WHITE: llm_white,
        PlayerType.LLM_BLACK: llm_black,
        PlayerType.RANDOM_PLAYER: random_player,
        PlayerType.CHESS_ENGINE_STOCKFISH: ChessEngineStockfishAgent(
            name="Chess_Engine_Stockfish_White",
            board=board,
            make_move_action=make_move_action,
            stockfish_path=stockfish_path,
            remove_history=reset_stockfish_history,
            is_termination_msg=is_termination_message,
            level=stockfish_level,
            time_limit=stockfish_time_per_move,  # Pass the stockfish_level parameter
        ),
    }.get(white_player_type)

    player_black = {
        PlayerType.LLM_WHITE: llm_white,
        PlayerType.LLM_BLACK: llm_black,
        PlayerType.RANDOM_PLAYER: random_player,
        PlayerType.CHESS_ENGINE_STOCKFISH: ChessEngineStockfishAgent(
            name="Chess_Engine_Stockfish_Black",
            board=board,
            make_move_action=make_move_action,
            stockfish_path=stockfish_path,
            remove_history=reset_stockfish_history,
            is_termination_msg=is_termination_message,
            level=stockfish_level,
            time_limit=stockfish_time_per_move,
        ),
    }.get(black_player_type)

    for player in [player_white, player_black]:
        # Reflection counts are global
        player.reflections_used = 0
        player.reflections_used_before_board = 0
        player.material_count = {"white": 0, "black": 0}

    # Function to generate PGN string
    def get_pgn_string():
        # Determine result based on game state
        result = "*"  # Default for in-progress games
        if winner == "NONE":
            result = "1/2-1/2"  # Draw
        elif winner == player_white.name:
            result = "1-0"  # White wins
        elif winner == player_black.name:
            result = "0-1"  # Black wins
            
        # Create PGN header
        pgn_header = (
            "[Event \"Chess Game\"]\n"
            f"[Date \"{time.strftime('%Y.%m.%d')}\"]\n"
            "[White \"Player White\"]\n"
            "[Black \"Player Black\"]\n"
            f"[Result \"{result}\"]\n\n"
        )
        
        # Format the moves list into PGN format
        pgn_moves = ""
        for i, move in enumerate(game_moves):
            if i % 2 == 0:  # White's move - add move number
                pgn_moves += f"{(i // 2) + 1}. {move} "
            else:  # Black's move
                pgn_moves += f"{move} "
                
            # Add newline every 5 full moves for readability
            if i > 0 and i % 10 == 9:
                pgn_moves += "\n"
        
        # Add result at the end
        pgn_moves += f" {result}"
        
        return pgn_header + pgn_moves
    
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
                        winner = "NONE"
                        reason = TerminationReason.SEVENTYFIVE_MOVES.value
                    elif board.is_fivefold_repetition():
                        winner = "NONE"
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

    # Generate the PGN string for the complete game
    pgn_string = get_pgn_string()
    
    game_stats = generate_game_stats(
        time_started,
        winner,
        reason,
        current_move,
        player_white,
        player_black,
        material_count,
        pgn_string,
    )

    display_store_game_video_and_stats(game_stats, log_dir, save_logs)
    return game_stats, player_white, player_black


if __name__ == "__main__":
    run()
