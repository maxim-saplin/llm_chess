import time
import traceback
import chess
import chess.svg
from typing import Any, Dict, Tuple, List
from enum import Enum
from custom_agents import GameAgent, RandomPlayerAgent, AutoReplyAgent, ChessEngineStockfishAgent, ChessEngineDragonAgent, NonGameAgent
from utils import calculate_material_count, generate_game_stats, get_llms_autogen, display_board, display_store_game_video_and_stats

class BoardRepresentation(Enum):
    FEN_ONLY = 1
    UNICODE_ONLY = 2
    UNICODE_WITH_PGN = 3
    ASCII_ONLY = 4  # Plain ASCII with uppercase (White) and lowercase (Black) letters


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
    CHESS_ENGINE_DRAGON = 6  # Add this new entry for Dragon engine
    LLM_NON = 7  # Represents a mixture of agents player using multiple LLMs

# Hyper params such as temperature are defined in `utils.py`
white_player_type = PlayerType.RANDOM_PLAYER
black_player_type = PlayerType.LLM_BLACK
enable_reflection = False  # Whether to offer the LLM time to think and evaluate moves
board_representation_mode = BoardRepresentation.FEN_ONLY  # BoardRepresentation.UNICODE_ONLY  # What kind of board is printed in response to get_current_board
rotate_board_for_white = False # Whether to rotate the Uicode board for the white player so it gets it's pieces at the bottom
llm_actions: List[str] = ["make_move", "get_legal_moves"]  # ["get_current_board", "get_legal_moves", "make_move"]  # List of actions the LLM agent should take; actions not included will be auto-provided

# Game configuration
max_game_moves = 200  # maximum number of game moves before terminating, dafault 200
max_llm_turns = 10  # how many conversation turns can an LLM make deciding on a move, e.g. repeating valid actions many times, default 10
max_failed_attempts = 3  # number of wrong replies within a dialog (e.g. non existing action) before stopping/giving a loss, default 3
throttle_delay = 0 # some LLM providers might thorttle frequent API reuqests, make a delay (in seconds) between moves
dialog_turn_delay = 1  # adds a delay in seconds inside LLM agent, i.e. delays between turns in a dialog happenning within a move
random_print_board = (
    False  # if set to True the random player will also print it's board to Console
)
visualize_board = False  # You can skip board visualization (animated board in popup window) to speed up execution
# Move style for input moves: "UCI" (coordinate notation) or "SAN" (Standard Algebraic Notation)
DEFAULT_MOVE_STYLE = "UCI"
# If True, LLM prompts include all previous moves in SAN notation
SEE_PREVIOUS_MOVES = True  # False

# Set to None to use defaults, "remove" to not send it
# o1-mini fails with any params other than 1.0 or not present, R1 distil recomends 0.5-0.7, kimi-k1.5-preview 0.3
temp_override = None

reasoning_effort = None # Default is None, used with OpenAI models low, medium, or high

thinking_budget = None # Default is None, if set will enable extended thinking with Anthropic models, min 1024 for Claude 3.7

# Tell AutoReply agent to remove given pieces of text from BOTH agents history when processing replies
# (using re.sub(self.ignore_text, '', action_choice, flags=re.DOTALL))
# It is needed to remove isolating thinking tokens. E.g. Deepseek R1 32B uses <think> tags that can have actions mentioned breaking execution (r"<think>.*?</think>")
# r"<think>.*?</think>" - Deepseek R1 Distil
# r"◁think▷.*?◁/think▷ - Kimi 1.5
# r"<reasoning>.*?</reasoning>" - Reka Flash
# Default None
remove_text = None

# LLM
llm_config_white, llm_config_black = get_llms_autogen(temp_override, reasoning_effort, thinking_budget)
# llm_config_white = llm_config_black  # Quick hack to use same model

non_llm_configs_white = [{
                **llm_config_white,
                "temperature": 0.0
            }, {
                **llm_config_white,
                "temperature": 1.0
            }]
non_llm_configs_black = [{
                **llm_config_black,
                "temperature": 0.0
            }, {
                **llm_config_black,
                "temperature": 1.0
            }]


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
reset_stockfish_history = True  # If True, Stockfish will get no history before making a move, default is True
stockfish_level = 1  # Set to an integer (0-20) to override Stockfish skill level, or None to use default
stockfish_time_per_move = 0.1  # Time limit (in seconds) for Stockfish to think per move, default is 0.1

# Komodo Dragon chess engine configuration
dragon_path = "./dragon/dragon-osx"  # Path to Komodo Dragon executable
reset_dragon_history = True  # If True, Dragon will get no history before making a move
dragon_level = 1  # Skill level (1-25) for Komodo Dragon
dragon_time_per_move = 0.1  # Time limit (in seconds) for Dragon to think per move

## Actions

board = chess.Board()
game_moves = []

def get_current_board() -> str:
    """
    Returns:
        str: A text representation of the current board state.
    """
    orientation = not (rotate_board_for_white and board.turn) # True is default orientation, False is rotated
    if board_representation_mode == BoardRepresentation.FEN_ONLY:
        return board.fen()
    elif board_representation_mode == BoardRepresentation.ASCII_ONLY:
        # ASCII board uses uppercase for White, lowercase for Black
        return str(board)
    elif board_representation_mode == BoardRepresentation.UNICODE_ONLY:
        return board.unicode(orientation=orientation)
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

        return f"{board.unicode(orientation=orientation)}\n\nPGN:\n{pgn_header}{pgn_moves}"


def get_legal_moves() -> str:
    """
    Returns:
        str: A list of legal moves in UCI format, separated by commas.
    """
    if board.legal_moves.count() == 0:
        return None
    return ",".join([str(move) for move in board.legal_moves])


def make_move(move: str):
    """
    Args:
        move (str): A move in DEFAULT_MOVE_STYLE notation ("UCI" or "SAN").

    """
    # Copy board to generate SAN notation after applying the move
    san_board = board.copy()
    # Parse and apply move based on DEFAULT_MOVE_STYLE
    if DEFAULT_MOVE_STYLE.upper() == "SAN":
        move_obj = board.parse_san(move)
        board.push(move_obj)
    else:
        move_obj = chess.Move.from_uci(move)
        board.push(move_obj)
    # Record move notation based on DEFAULT_MOVE_STYLE
    if DEFAULT_MOVE_STYLE.upper() == "SAN":
        notation = san_board.san(move_obj)
    else:
        notation = move_obj.uci()
    game_moves.append(notation)

    # Visualize the board if enabled
    if visualize_board:
        display_board(board, move_obj)

def run(log_dir="_logs") -> Tuple[Dict[str, Any], GameAgent, GameAgent]:
    """
    Runs the chess game simulation.

    Args:
        log_dir (str): Directory to save log file with game result. Set to NONE to not create one

    Returns:
        tuple: A tuple containing game statistics, the white player, and the black player.
    """

    time_started = time.strftime("%Y.%m.%d_%H:%M")

    # Action names
    get_current_board_action = "get_current_board"
    get_legal_moves_action = "get_legal_moves"
    make_move_action = "make_move"

    # Init chess board and game state
    material_count = {"white": 0, "black": 0}
    global board, game_moves
    board.reset()
    game_moves.clear()
    winner = None
    reason = None

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

    # Determine which actions the LLM should handle vs auto-provided
    handle_board = 'get_current_board' in llm_actions
    handle_legal = 'get_legal_moves' in llm_actions
    handle_move = 'make_move' in llm_actions

    # Build common_prompt listing only allowed actions
    prompt_options = []
    if handle_board:
        prompt_options.append(f"- '{get_current_board_action}' to get the schema and current status of the board")
    if handle_legal:
        prompt_options.append(f"- '{get_legal_moves_action}' to get a UCI formatted list of available moves")
    if enable_reflection:
        prompt_options.append(f"- '{reflect_action}' to take a moment to think about your strategy")
    if handle_move:
        prompt_options.append(f"- '{make_move_action} <UCI formatted move>' when you are ready to complete your turn (e.g., '{make_move_action} e2e4')")
    common_prompt = "Now is your turn to make a move. Before making a move you can pick one of the following actions:\n" + "\n".join(prompt_options)

    # Reflection prompt remains unchanged
    reflect_prompt = (
        "Before deciding on the next move you can reflect on your current situation, write down notes and evaluate.\n"
        "Here're a few recommendations that you can follow to make a better move decision:\n"
        "- Shortlist the most valuable next moves\n"
        "- Consider how they affect the situation\n"
        "- What could be the next moves from your opponent in each case\n"
        "- Is there any strategy fitting the situation and your choice of moves\n"
        "- Rerank the shortlisted moves based on the previous steps\n"
    )

    # Build reflection_followup_prompt listing only allowed actions
    followup_options = []
    if handle_board:
        followup_options.append(get_current_board_action)
    if handle_legal:
        followup_options.append(get_legal_moves_action)
    if enable_reflection:
        followup_options.append(reflect_action)
    if handle_move:
        followup_options.append(f"{make_move_action} <UCI formatted move>")
    reflection_followup_prompt = "Now that you reflected please choose any of the valid actions: " + ", ".join(followup_options)

    # Build invalid_action_message listing only allowed actions
    invalid_options = []
    if handle_board:
        invalid_options.append(get_current_board_action)
    if handle_legal:
        invalid_options.append(get_legal_moves_action)
    if enable_reflection:
        invalid_options.append(reflect_action)
    if handle_move:
        invalid_options.append(f"{make_move_action} <UCI formatted move>")
    invalid_action_message = "Invalid action. Pick one, reply exactly with the name and space delimitted argument: " + ", ".join(invalid_options)

    # Spend hours debuging circular loops in termination message and prompt and figuring out None is not good for system message
    def is_termination_message(msg: Dict[str, Any]) -> bool:
        return any(
            term_msg == msg["content"].lower().strip()
            for term_msg in termination_conditions
        )

    llm_white = GameAgent(
        name="Player_White",
        # Not using system message as some LLMs can ignore it
        system_message="",
        description="You are a professional chess player and you play as white. "
        + common_prompt,
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
        get_current_board_action=get_current_board_action if handle_board else None,
        reflect_action=reflect_action,
        get_legal_moves_action=get_legal_moves_action if handle_legal else None,
        reflect_prompt=reflect_prompt,
        reflection_followup_prompt=reflection_followup_prompt,
        make_move_action=make_move_action if handle_move else None,
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
            time_limit=stockfish_time_per_move,
        ),
        PlayerType.CHESS_ENGINE_DRAGON: ChessEngineDragonAgent(
            name="Chess_Engine_Dragon_White",
            board=board,
            make_move_action=make_move_action,
            dragon_path=dragon_path,
            remove_history=reset_dragon_history,
            is_termination_msg=is_termination_message,
            level=dragon_level,
            time_limit=dragon_time_per_move,
        ),
        PlayerType.LLM_NON: NonGameAgent(
            name="Player_Non_White",
            system_message="",
            description="You are a professional chess player and you play as white. " + common_prompt,
            llm_config=llm_config_white,
            llm_configs=non_llm_configs_white,
            is_termination_msg=is_termination_message,
            human_input_mode="NEVER",
            dialog_turn_delay=dialog_turn_delay,
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
        PlayerType.CHESS_ENGINE_DRAGON: ChessEngineDragonAgent(
            name="Chess_Engine_Dragon_Black",
            board=board,
            make_move_action=make_move_action,
            dragon_path=dragon_path,
            remove_history=reset_dragon_history,
            is_termination_msg=is_termination_message,
            level=dragon_level,
            time_limit=dragon_time_per_move,
        ),
        PlayerType.LLM_NON: NonGameAgent(
            name="Player_Non_Black",
            system_message="",
            description="You are a professional chess player and you play as black. " + common_prompt,
            llm_config=llm_config_black,
            llm_configs=non_llm_configs_black,
            is_termination_msg=is_termination_message,
            human_input_mode="NEVER",
            dialog_turn_delay=dialog_turn_delay,
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
        reason = None

        while (
            current_move < max_game_moves and not reason
        ):
            for player in [player_white, player_black]:
                # Reset player state variables before each move: has_requested_board, failed_action_attempts
                player.prep_to_move()
                # Include formatted previous moves if enabled
                if SEE_PREVIOUS_MOVES and game_moves:
                    # Group moves into numbered pairs for clarity
                    pairs = []
                    for i in range(0, len(game_moves), 2):
                        white_move = game_moves[i]
                        black_move = game_moves[i+1] if i+1 < len(game_moves) else ''
                        pair = f"{(i//2)+1}. {white_move}" + (f" {black_move}" if black_move else '')
                        pairs.append(pair)
                    auto_context = f"Previous moves ({DEFAULT_MOVE_STYLE}): " + ", ".join(pairs) + "\n\n"
                else:
                    auto_context = ""
                # Auto-provide excluded action outputs
                if not handle_board:
                    auto_context += "Current board state:\n" + get_current_board() + "\n\n"
                if not handle_legal:
                    legal = get_legal_moves()
                    auto_context += "Legal moves:\n" + (legal or "None") + "\n\n"   # + "Please reason before making a move.\n\n"  # NOTE: This reasoning prompt was necessary for gpt-4.1-mini else it would just give the answer.
                # Build message for the LLM with auto-provided context
                message = auto_context + player.description
                chat_result = proxy_agent.initiate_chat(
                    recipient=player,
                    message=message,
                    max_turns=max_llm_turns,
                    cache=None
                )
                current_move += 1
                last_message = chat_result.summary

                print(f"\033[94mMADE MOVE {current_move}\033[0m")
                # print(f"\033[94mLast Message: {last_message}\033[0m")
                _, last_usage = list(
                    chat_result.cost["usage_including_cached_inference"].items()
                )[-1]

                white_material, black_material = calculate_material_count(board)
                print(
                    f"\033[94mMaterial Count - White: {white_material}, Black: {black_material}\033[0m"
                )
                material_count["white"] = white_material
                material_count["black"] = black_material

                # Get token usage stats - different for NoN agents
                if isinstance(player, NonGameAgent):
                    # NoN agents store stats directly in the agent
                    prompt_tokens = player.total_prompt_tokens
                    completion_tokens = player.total_completion_tokens
                else:
                    # Standard agents get stats from chat result
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
                    winner = (
                        player_black.name
                        if player == player_white
                        else player_white.name
                    )
                    reason = TerminationReason.TOO_MANY_WRONG_ACTIONS.value
                elif board.is_game_over():
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
                    # TODO: fix max llm turns for NoN, seems like missing chat history broke this check
                    and len(chat_result.chat_history) >= max_llm_turns * 2
                ):
                    winner = (
                        player_black.name
                        if player == player_white
                        else player_white.name
                    )
                    reason = TerminationReason.MAX_TURNS.value
                elif current_move >= max_game_moves:
                    winner = "NONE"
                    reason = TerminationReason.MAX_MOVES.value
                elif (
                    last_message.lower().strip() not in [
                        move_was_made.lower().strip(),
                        invalid_action_message.lower().strip()
                    ]
                    and not last_message.lower().startswith("failed to make move:")
                ):
                    winner = "NONE"
                    reason = TerminationReason.UNKNOWN_ISSUE.value

                proxy_agent.clear_history()
                time.sleep(throttle_delay)
                if reason:
                    break


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

    display_store_game_video_and_stats(game_stats, log_dir)
    return game_stats, player_white, player_black


if __name__ == "__main__":
    run()
