# analyze_chess_json.py (Version 4.1 - Restore Possibility Summaries)
import chess
import chess.engine
import chess.polyglot
import json
import argparse
import os
import logging
import re
from tqdm import tqdm
import math
import collections
import time
from collections import defaultdict

# --- Configuration ---
# (Defaults remain the same)
DEFAULT_STOCKFISH_PATH = "/opt/homebrew/bin/stockfish"
DEFAULT_ANALYSIS_DEPTH = 14
DEFAULT_ANALYSIS_TIME_LIMIT = None
DEFAULT_OUTPUT_SUFFIX = "_analyzed" # Update suffix
DEFAULT_OPENING_BOOK_PATH = None
MATERIAL_VALUES = { chess.PAWN: 100, chess.KNIGHT: 300, chess.BISHOP: 300, chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 0 }
PIECE_NAMES = { chess.PAWN: "Pawn", chess.KNIGHT: "Knight", chess.BISHOP: "Bishop", chess.ROOK: "Rook", chess.QUEEN: "Queen", chess.KING: "King" }
# Thresholds based on difference in Lichess Win%: https://github.com/lichess-org/lila/blob/cf9e10df24b767b3bc5ee3d88c45437ac722025d/modules/analyse/src/main/Advice.scala#L52.
BLUNDER_THRESHOLD = 30
MISTAKE_THRESHOLD = 20
INACCURACY_THRESHOLD = 10

# TODO: Decide hyperparameters for game phase heuristics. This is very arbitrary.
OPENING_MAX_PLY = 20
ENDGAME_MATERIAL_THRESHOLD = 1800
NO_QUEENS_ENDGAME = True

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Helper Functions ---
# (score_to_cp, classify_move, get_material_diff, get_total_material,
#  get_pawn_structure_metrics, get_game_phase remain unchanged from V4)

def score_to_cp(score_in):
    """Converts a chess.engine.Score object (Cp, Mate, or PovScore) to centipawns from White's perspective."""
    if score_in is None:
        return 0
    score = score_in.white() if isinstance(score_in, chess.engine.PovScore) else score_in
    if score.is_mate():
        mate_in = score.mate()
        # Cap the centipawn loss at 1000 for missed mates
        return 1000 if mate_in > 0 else -1000
    return score.score()

def score_to_cp_old(score_in):
    """Converts a chess.engine.Score object (Cp, Mate, or PovScore) to centipawns from White's perspective."""
    if score_in is None: return 0
    mate_score = 30000
    try:
        score = score_in.white() if isinstance(score_in, chess.engine.PovScore) else score_in
    except AttributeError:
         logging.warning(f"Could not normalize score: {score_in}. Returning 0.")
         return 0
    if isinstance(score, chess.engine.Mate):
        mate_in = score.mate()
        if mate_in == 0: return 0
        cp = mate_score - (abs(mate_in) * 10)
        return cp if mate_in > 0 else -cp
    elif isinstance(score, chess.engine.Cp):
        cp_value = score.score()
        return cp_value if cp_value is not None else 0
    else:
        logging.warning(f"Unexpected score type after normalization: {type(score)}. Returning 0.")
        return 0

def classify_move(delta_win_pct, best_move_played, classification_override=None):
    """Classifies a move based on the evaluation drop and if it was the best. Allows override.

    Blunder/Mistake/Inaccuracy thresholds are calculated based on win-pct from Lichess: https://github.com/lichess-org/lila/blob/cf9e10df24b767b3bc5ee3d88c45437ac722025d/modules/analyse/src/main/Advice.scala#L52.
    
    """
    if classification_override: return classification_override
    if best_move_played: return "Best"
    if delta_win_pct > 0: return "OK"  # If win % increased, we consider it OK
    delta_win_pct = abs(delta_win_pct)  # Use absolute value for classification, as here it means delta_win_pct is negative (e.g., -50 means win % decreased by 50)
    if delta_win_pct >= BLUNDER_THRESHOLD: return "Blunder"
    if delta_win_pct >= MISTAKE_THRESHOLD: return "Mistake"
    if delta_win_pct >= INACCURACY_THRESHOLD: return "Inaccuracy"
    return "OK"

def get_material_diff(board):
    """Calculates material difference (White - Black) in centipawns."""
    white_mat = sum(len(board.pieces(pt, chess.WHITE)) * MATERIAL_VALUES[pt] for pt in MATERIAL_VALUES)
    black_mat = sum(len(board.pieces(pt, chess.BLACK)) * MATERIAL_VALUES[pt] for pt in MATERIAL_VALUES)
    return white_mat - black_mat

def get_total_material(board):
    """Calculates total material value on the board (excluding kings)."""
    return sum(len(board.pieces(pt, c)) * MATERIAL_VALUES[pt] for pt in MATERIAL_VALUES for c in [chess.WHITE, chess.BLACK])

def get_game_phase(board, ply):
    """Determines the game phase based on ply and material."""
    if ply <= OPENING_MAX_PLY: return "Opening"
    total_material = get_total_material(board)
    no_queens = not board.pieces(chess.QUEEN, chess.WHITE) and not board.pieces(chess.QUEEN, chess.BLACK)
    if total_material < ENDGAME_MATERIAL_THRESHOLD or (NO_QUEENS_ENDGAME and no_queens and ply > OPENING_MAX_PLY + 10):
        return "Endgame"
    return "Middlegame"

# --- Analysis Function ---

def analyze_game(game_data, engine, analysis_limit, llm_color_str, opening_book_reader, game_stats_aggregator):
    """Analyzes a single game dictionary, updates stats_aggregator."""
    start_time_game = time.time()
    game_id = game_data.get('game_id', 'N/A')
    logging.info(f"Analyzing Game ID: {game_id}")
    board = chess.Board()
    game_analysis = []
    llm_color = chess.WHITE if llm_color_str == 'white' else chess.BLACK
    llm_thought_index = 0
    opening_book_active = (opening_book_reader is not None)

    # Validation checks...
    if not game_data.get("moves_uci"): game_data['analysis_error'] = "No UCI moves"; return game_data
    if game_data.get("error_message") or game_data.get("result", "*") == "*":
        if "LLM failed" in game_data.get("outcome_description", ""): logging.warning(f"Game ID {game_id}: LLM failure.")
        elif game_data.get("error_message"): logging.warning(f"Game ID {game_id}: Runtime error - {game_data['error_message']}.")
        elif not game_data.get("moves_uci"): game_data['analysis_error'] = "Premature end, no moves"; return game_data

    total_moves_to_analyze = len(game_data["moves_uci"])
    if total_moves_to_analyze == 0: game_data['analysis_error'] = "Empty move list"; return game_data

    # --- Game Loop ---
    for i, uci_move_str in enumerate(tqdm(game_data["moves_uci"], desc=f"Game {game_id} Moves", leave=False)):
        ply = i
        turn_before_move = board.turn
        player_role = 'llm' if turn_before_move == llm_color else 'opponent'

        # --- Data Collection (Before Move) ---
        fen_before = board.fen()
        game_phase = get_game_phase(board, ply)
        is_check_before = board.is_check()
        material_diff_cp = get_material_diff(board)
        # --- Modify possible_moves structure ---
        possible_moves_output = None # Initialize as None

        # --- Analyze Move Possibilities (if LLM's turn) ---
        if player_role == 'llm':
            possible_moves_output = {
                "summary": {
                    "possible_checks_uci": [],
                    "possible_captures_uci": [],
                    "possible_promotions_uci": [],
                    "count_legal_moves": 0
                },
                "details": [] # List of described moves
            }
            try:
                legal_moves = list(board.legal_moves)
                possible_moves_output["summary"]["count_legal_moves"] = len(legal_moves)

                for m in legal_moves:
                    # Check characteristics
                    is_check = board.gives_check(m)
                    is_capture = board.is_capture(m)
                    is_promotion = (m.promotion is not None)

                    # Add to detailed list
                    possible_moves_output["details"].append({
                        "uci": m.uci(),
                        "is_check": is_check,
                        "is_capture": is_capture,
                        "is_promotion": is_promotion
                    })

                    # Add to summary lists
                    if is_check: possible_moves_output["summary"]["possible_checks_uci"].append(m.uci())
                    if is_capture: possible_moves_output["summary"]["possible_captures_uci"].append(m.uci())
                    if is_promotion: possible_moves_output["summary"]["possible_promotions_uci"].append(m.uci())

            except Exception as e:
                 logging.error(f"Game {game_id}, Ply {ply}: Error describing possible moves: {e}", exc_info=False)
                 possible_moves_output = {"error": "Failed to generate possibilities"} # Indicate error


        # --- Initialize Analysis Dictionary ---
        move_analysis = {
            "ply": ply, "uci_played": uci_move_str, "san_played": "N/A",
            "player": player_role, "game_phase": game_phase,
            "position_fen": fen_before, "is_check_before": is_check_before,
            "material_diff_cp": material_diff_cp,
            "possible_moves": possible_moves_output, # Use the new structure
            "eval_before_white_pov": None, "eval_after_white_pov": None, "eval_delta_cp": None, # Renamed for clarity
            "win_pct_before": None, "win_pct_after": None, "accuracy_pct": None,  # From Lichess: https://lichess.org/page/accuracy
            "engine_best_move_uci": None, "classification": "N/A", "is_opening_book_move": None,
            "is_capture": None, "is_promotion": None, "is_castling": None,
            "gives_check_after": None, "delivers_mate": False, "delivers_stalemate": False,
            "llm_thought": None,
        }

        # --- Parse Move ---
        move_obj = None
        try:
            move_obj = board.parse_uci(uci_move_str)
            move_analysis["san_played"] = board.san(move_obj)
            move_analysis["is_capture"] = board.is_capture(move_obj)
            move_analysis["is_castling"] = board.is_castling(move_obj)
            move_analysis["is_promotion"] = (move_obj.promotion is not None)

            # Opening Book Check
            if opening_book_active and game_phase == "Opening":
                try:
                    move_analysis["is_opening_book_move"] = any(bm.move == move_obj for bm in opening_book_reader.find_all(board))
                except Exception as book_e:
                     logging.warning(f"Game {game_id}, Ply {ply}: Error reading book: {book_e}")
                     move_analysis["is_opening_book_move"] = None
            else:
                 move_analysis["is_opening_book_move"] = None

        except (ValueError, AssertionError) as e:
             logging.error(f"Game {game_id}, Ply {ply}: Illegal/unparseable move '{uci_move_str}' from FEN {fen_before}. Error: {e}. Stopping.")
             game_data['analysis_error'] = f"Illegal move {uci_move_str} at ply {ply}"
             break
        except Exception as e:
             logging.error(f"Game {game_id}, Ply {ply}: Error parsing move '{uci_move_str}': {e}. FEN: {fen_before}. Stopping.")
             game_data['analysis_error'] = f"Move parsing error at ply {ply}"
             break

        # --- Engine Analysis (Before Move) ---
        eval_before_white_pov = 0
        best_move_uci_before = None
        try:
            analysis_result = engine.analyse(board, analysis_limit)
            score_obj_before = analysis_result.get('score')
            if score_obj_before is None: raise ValueError("Engine score missing")
            eval_before_white_pov = score_to_cp(score_obj_before) # White's perspective before the move. Positive means advantage for White, negative for black. If the delta is positive, White is better, else Black is better.
            move_analysis["eval_before_white_pov"] = eval_before_white_pov

            if analysis_result.get('pv') and len(analysis_result['pv']) > 0:
                 best_move_uci_before = analysis_result['pv'][0].uci()
                 move_analysis["engine_best_move_uci"] = best_move_uci_before
            else:
                 logging.warning(f"Game {game_id}, Ply {ply}: Engine analysis did not return PV.")

        except Exception as e:
            logging.error(f"Game {game_id}, Ply {ply}: Engine analysis failed before move {uci_move_str}: {e}", exc_info=False)
            game_data['analysis_error'] = f"Engine analysis failed at ply {ply} (before move)"
            break

        # --- Make the Move ---
        board.push(move_obj)

        # --- Data Collection & Analysis (After Move) ---
        move_analysis["gives_check_after"] = board.is_check()
        move_analysis["delivers_mate"] = board.is_checkmate()
        move_analysis["delivers_stalemate"] = board.is_stalemate()

        eval_after_white_pov = 0
        classification_override = None

        if not board.is_game_over(claim_draw=True):
            try:
                analysis_result_after = engine.analyse(board, analysis_limit)
                score_obj_after = analysis_result_after.get('score')
                if score_obj_after is None: raise ValueError("Engine score missing after move.")
                eval_after_white_pov = score_to_cp(score_obj_after) # White's perspective after the move.
                move_analysis["eval_after_white_pov"] = eval_after_white_pov

            except Exception as e:
                logging.error(f"Game {game_id}, Ply {ply}: Engine analysis failed AFTER move {uci_move_str}: {e}", exc_info=False)
                classification_override = "Analysis Failed After Move"
        else:
            if len(game_data.get("moves_uci", [])) >= 200:
                classification_override = "Max Moves Reached"
                eval_after_white_pov = 0
            elif move_analysis["delivers_mate"]:
                classification_override = "Checkmate Delivered"
                mate_score_obj = chess.engine.PovScore(chess.engine.Mate(1), turn_before_move)
                eval_after_white_pov = score_to_cp(mate_score_obj)
            elif move_analysis["delivers_stalemate"] or board.is_insufficient_material() or board.is_seventyfive_moves() or board.is_fivefold_repetition():
                classification_override = "Draw Delivered"
                eval_after_white_pov = 0
            else:
                classification_override = "Game End (Other)"
                eval_after_white_pov = 0
            move_analysis["eval_after_white_pov"] = eval_after_white_pov

        # --- Calculate Delta and Classify ---
        eval_before_this_pov = eval_before_white_pov if turn_before_move == chess.WHITE else -eval_before_white_pov
        eval_after_this_pov = eval_after_white_pov if turn_before_move == chess.WHITE else -eval_after_white_pov
        eval_delta_cp = eval_after_this_pov - eval_before_this_pov # This is the change in evaluation from before to after the move in centipawns. Positive is always better for the player who just moved (we reverse if black, since by default cp is always from white's perspective). Higher is better for current player.
        move_analysis["eval_delta_cp"] = eval_delta_cp

        def get_win_pct(centipawns):
            """From Lichess: https://lichess.org/page/accuracy"""
            return 50 + 50 * (2 / (1 + math.exp(-0.00368208 * centipawns)) - 1)
        move_analysis["win_pct_before"] = get_win_pct(eval_before_this_pov)
        move_analysis["win_pct_after"] = get_win_pct(eval_after_this_pov)
        delta_win_pct = move_analysis["win_pct_after"] - move_analysis["win_pct_before"]

        best_move_played = (best_move_uci_before == uci_move_str)
        move_analysis["classification"] = classify_move(delta_win_pct, best_move_played, classification_override)

        # --- Update Stats ---
        cls = move_analysis["classification"]
        if cls and cls != "N/A":
             game_stats_aggregator[player_role][game_phase][cls] += 1
             game_stats_aggregator[player_role]["Overall"][cls] += 1
             game_stats_aggregator["Overall"][game_phase][cls] += 1
             game_stats_aggregator["Overall"]["Overall"][cls] += 1

        # --- Add LLM Thought ---
        # No thoughts easily available.
        # if player_role == 'llm':
        #     if llm_thought_index < len(game_data.get("llm_thoughts", [])):
        #         move_analysis["llm_thought"] = game_data["llm_thoughts"][llm_thought_index]
        #         llm_thought_index += 1
        #     else:
        #         logging.warning(f"Game {game_id}, Ply {ply}: Expected LLM thought missing.")

        game_analysis.append(move_analysis)

        # --- Check for Game Over ---
        if board.is_game_over(claim_draw=True):
            logging.debug(f"Game {game_id} ended per board after ply {ply}. Result: {board.result(claim_draw=True)}")
            if i < total_moves_to_analyze - 1: logging.warning(f"Game {game_id} board ended ply {ply}, but JSON has more moves.")
            break

    # --- Finalize ---
    game_data["analysis"] = game_analysis
    if len(game_data.get("moves_uci", [])) >= 200:
        classification_override = "Max Moves Reached"
        eval_after_white_pov = 0
    else:
        if move_analysis["delivers_mate"]:
            classification_override = "Checkmate Delivered"
            mate_score_obj = chess.engine.PovScore(chess.engine.Mate(1), turn_before_move)
            eval_after_white_pov = score_to_cp(mate_score_obj)
        elif move_analysis["delivers_stalemate"] or board.is_insufficient_material() or board.is_seventyfive_moves() or board.is_fivefold_repetition():
            classification_override = "Draw Delivered"
            eval_after_white_pov = 0
        else:
            classification_override = "Game End (Other)"
            eval_after_white_pov = 0
    game_data["classification_override"] = classification_override
    end_time_game = time.time()
    game_data["analysis_time_seconds"] = round(end_time_game - start_time_game, 2)
    return game_data

# --- Initialize Stats Structure ---
def initialize_stats():
    phases = ["Opening", "Middlegame", "Endgame", "Overall"]
    players = ["llm", "opponent", "Overall"]
    classifications = ["Best", "OK", "Inaccuracy", "Mistake", "Blunder", "Checkmate Delivered", "Draw Delivered", "Game End (Other)", "Analysis Failed After Move", "N/A"]
    stats = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    for p in players:
        for ph in phases:
            for cl in classifications:
                stats[p][ph][cl] = 0
    return stats

# --- Format and Print Stats ---
def print_stats(stats):
    # (Unchanged from V4)
    print("\n--- Analysis Summary Statistics ---")
    phases = ["Opening", "Middlegame", "Endgame", "Overall"]
    players = ["llm", "opponent", "Overall"]
    classifications = ["Best", "OK", "Inaccuracy", "Mistake", "Blunder", "Checkmate Delivered", "Draw Delivered", "Game End (Other)", "Analysis Failed After Move"]
    for player in players:
        print(f"\n--- {player.upper()} ---")
        header = f"{'Phase':<12}" + "".join([f"{cls[:10]:>12}" for cls in classifications]) + f"{'Total':>12}" # Truncate names
        print(header)
        print("-" * len(header))
        for phase in phases:
            total_moves_phase = sum(stats[player][phase].values())
            if total_moves_phase == 0 and phase != "Overall": continue
            row = f"{phase:<12}"
            for cls in classifications:
                count = stats[player][phase].get(cls, 0)
                row += f"{count:>12}"
            row += f"{total_moves_phase:>12}"
            print(row)
    print("-" * len(header))
    print("-----------------------------------\n")

# --- PGN Parsing for Single-Game JSON ---
def extract_moves_from_pgn(pgn_str):
    """Extracts a list of UCI moves from a PGN string for analysis."""
    board = chess.Board()
    moves_uci = []
    for move in pgn_str.split():
        if move in ["1-0", "0-1", "1/2-1/2", "*"]:
            break
        try:
            uci_move = board.push_san(move)
            moves_uci.append(uci_move.uci())
        except ValueError:
            continue
    return moves_uci

# Function to parse output.txt and extract game moves in UCI format

def parse_output_txt(file_path):
    """Parses the output.txt file to extract moves in UCI format."""
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    moves = []
    for line in lines:
        if line.startswith("make_move"):
            move = line.split()[1].strip()
            moves.append(move)

    return moves

def prepare_game_data_with_uci(json_file_path):
    """Reads the JSON file, extracts UCI moves from PGN, and prepares game data."""
    with open(json_file_path, 'r') as file:
        game_data = json.load(file)
        if "pgn" in game_data:
            pgn_str = game_data["pgn"]
            game_data["moves_uci"] = extract_moves_from_pgn(pgn_str)
        else:
            logging.error("No PGN data found in JSON.")
            return None
    return game_data

# --- Main Execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze chess games using Stockfish.")
    parser.add_argument("--source", type=str, choices=["json", "output_txt"], default="json",
                        help="Specify the source of game data: 'json' or 'output_txt'.")
    parser.add_argument("--json_file", type=str, help="Path to the JSON file containing game data.")
    parser.add_argument("--output_txt_file", type=str, default='/Users/saikolasani/llmchess/llm_chess/sample_output.txt',
                        help="Path to the output.txt file containing game data.")
    parser.add_argument("--stockfish_path", type=str, default=DEFAULT_STOCKFISH_PATH,
                        help="Path to the Stockfish engine executable.")
    parser.add_argument("--depth", type=int, default=DEFAULT_ANALYSIS_DEPTH,
                        help="Depth of analysis for Stockfish.")
    parser.add_argument("--time_limit", type=float, default=DEFAULT_ANALYSIS_TIME_LIMIT,
                        help="Time limit for analysis per move in seconds.")
    parser.add_argument("--output_file", type=str, default=None,
                        help="Output file to save analyzed data.")
    parser.add_argument("--engine_options", type=str, default='{}',
                        help="JSON string of engine options for Stockfish.")
    parser.add_argument("--opening_book", type=str, default=DEFAULT_OPENING_BOOK_PATH,
                        help="Path to the opening book file.")
    parser.add_argument("--skip_stats", action='store_true',
                        help="Skip printing statistics after analysis.")

    args = parser.parse_args()

    # Initialize the Stockfish engine
    engine = None
    engine_options = {}
    try:
        engine_options = json.loads(args.engine_options)
        logging.info(f"Using engine options: {engine_options}")
    except json.JSONDecodeError:
        logging.error(f"Invalid JSON --engine_options: {args.engine_options}")
        exit(1)
    try:
        engine = chess.engine.SimpleEngine.popen_uci(args.stockfish_path)
        if engine_options:
            engine.configure(engine_options)
        else:
            engine.configure({
                "Threads": 1,           # use 1 CPU core
                "Hash": 128,           # 128 MB transposition table               
                "Skill Level": 20,
            })
    except Exception as e:
        logging.error(f"Failed to initialize Stockfish: {e}")
        exit(1)

    # Determine source and parse moves
    moves_uci = []
    if args.source == "json":
        game_data = prepare_game_data_with_uci(args.json_file)
        if game_data:
            moves_uci = game_data.get("moves_uci", [])
    elif args.source == "output_txt":
        moves_uci = parse_output_txt(args.output_txt_file)

    # Analyze the moves
    if moves_uci:
        # Assuming a function analyze_moves exists that takes moves_uci and performs the analysis
        data = {"games": [{"moves_uci": moves_uci}]}
        game_stats_aggregator = initialize_stats()
        experiment_llm_color = 'black'
        logging.info(f"LLM is always the black player.")
        analyzed_games_list = []
        game_iterator = tqdm(data["games"], desc="Analyzing Games")
        for game_data in game_iterator:
            game_llm_color = 'black'
            print(f"Game LLM Color: {game_llm_color} (LLM is always black)")
            # Analyze this game with determined LLM color
            analyzed_game_result = analyze_game(
                game_data, engine, chess.engine.Limit(depth=20), game_llm_color,
                None, game_stats_aggregator
            )
            classification_override = analyzed_game_result.get("classification_override", "Unknown")
            analyzed_games_list.append(analyzed_game_result)

        # Shutdown Engine & Book...
        logging.info("Quitting Stockfish engine.")
        if engine:
            try:
                engine.quit()
            except chess.engine.EngineTerminatedError:
                logging.warning("Engine already terminated.")
            except Exception as e:
                logging.error(f"Error shutting down engine: {e}")

        # Prepare Final Output Data...
        data["games"] = analyzed_games_list
        data["analysis_parameters"] = {
            "engine_path": args.stockfish_path,
            "analysis_depth": 20,
            "analysis_time_limit": None,
            "engine_options": {"Threads": 1, "Hash": 128, "UCI_AnalyseMode": True, "MultiPV": 1, "Skill Level": 20},
            "classification_thresholds_cp": {"inaccuracy": INACCURACY_THRESHOLD, "mistake": MISTAKE_THRESHOLD, "blunder": BLUNDER_THRESHOLD},
            "game_phase_definition": {"opening_max_ply": OPENING_MAX_PLY, "endgame_material_threshold": ENDGAME_MATERIAL_THRESHOLD, "no_queens_is_endgame": NO_QUEENS_ENDGAME}
        }
        data["analysis_summary_stats"] = json.loads(json.dumps(game_stats_aggregator)) # Convert defaultdict to dict

        # Save Analyzed Data...
        if args.output_file:
            output_json_path = args.output_file
        else:
            if args.source == "json":
                output_json_path = f"{os.path.splitext(args.json_file)[0]}{DEFAULT_OUTPUT_SUFFIX}{os.path.splitext(args.json_file)[1]}"
            else:
                # Specify model name for output log when using output.txt
                model_name = "default_model"  # Replace with actual model name if available
                output_json_path = f"output_{model_name}_analyzed.json"

        logging.info(f"Saving analyzed data to: {output_json_path}")
        try:
            with open(output_json_path, 'w', encoding='utf-8') as f: json.dump(data, f, indent=2)
        except Exception as e: logging.error(f"Failed to save analyzed JSON: {e}")

        # Print Stats...
        if not args.skip_stats:
            print_stats(game_stats_aggregator)
            # Compute and display average centipawn loss per player
            cp_loss_agg = {"llm": {"sum": 0, "count": 0}, "opponent": {"sum": 0, "count": 0}}
            for game in analyzed_games_list:
                for mv in game.get("analysis", []):
                    player = mv.get("player")
                    delta = mv.get("eval_delta_cp")
                    if delta is None: continue
                    cp_loss_agg[player]["sum"] += abs(delta)
                    cp_loss_agg[player]["count"] += 1
            avg_llm = cp_loss_agg["llm"]["sum"] / cp_loss_agg["llm"]["count"] if cp_loss_agg["llm"]["count"] else 0
            avg_opp = cp_loss_agg["opponent"]["sum"] / cp_loss_agg["opponent"]["count"] if cp_loss_agg["opponent"]["count"] else 0
            print(f"Average Centipawn Loss - LLM: {avg_llm:.2f}, Opponent: {avg_opp:.2f}")
            print(f"Reason for Game End: {classification_override}")

    else:
        logging.error("No moves found to analyze.")
        exit(1)