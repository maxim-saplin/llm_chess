import random
import re
import chess
import chess.engine
from autogen import ConversableAgent
from sunfish import Searcher, Position, parse, render, pst
from typing import Any, Dict, List, Optional, Union


class RandomPlayerAgent(ConversableAgent):
    """
    A random chess player agent that selects moves randomly from legal options.

    Attributes:
        make_move_action (str): The action string for making a move.
        get_legal_moves_action (str): The action string for getting legal moves.
    """

    def __init__(
        self,
        make_move_action: str,
        get_legal_moves_action: str,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.make_move_action = make_move_action
        self.get_legal_moves_action = get_legal_moves_action

    def generate_reply(
        self,
        messages: Optional[List[Dict[str, Any]]] = None,
        sender: Optional[ConversableAgent] = None,
        **kwargs: Any,
    ) -> Union[str, Dict, None]:
        if self._is_termination_msg(messages[-1]):
            return None

        last_message = messages[-1]["content"].strip()

        try:
            legal_moves = last_message.split(",")
            if legal_moves:
                random_move = random.choice(legal_moves)
                if chess.Move.from_uci(random_move).uci() == random_move:
                    return f"{self.make_move_action} {random_move}"
                return self.get_legal_moves_action
        except Exception:
            return self.get_legal_moves_action

        return self.get_legal_moves_action


class AutoReplyAgent(ConversableAgent):
    """
    An agent that automatically replies based on predefined actions and conditions.

    Attributes:
        max_failed_attempts (int): Maximum failed attempts before halting.
        get_current_board (function): Function to get the current board state.
        get_legal_moves (function): Function to get legal moves.
        make_move (function): Function to make a move.
        move_was_made_message (str): Reply message to use indicating a move was made.
        invalid_action_message (str): Reply message to use for invalid actions.
        too_many_failed_actions (str): Reply message to use for too many failed actions.
        get_current_board_action (str): The action string for getting the current board state.
        get_legal_moves_action (str): The action string for getting legal moves.
        make_move_action (str): The action string for making a move.
    """

    def __init__(
        self,
        get_current_board,
        get_legal_moves,
        reflect,
        make_move,
        move_was_made_message,
        invalid_action_message,
        too_many_failed_actions_message,
        max_failed_attempts,
        get_current_board_action,
        get_legal_moves_action,
        reflect_action,
        reflection_followup_prompt,
        make_move_action,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.get_current_board = get_current_board
        self.get_legal_moves = get_legal_moves
        self.reflect = reflect
        self.make_move = make_move
        self.move_was_made = move_was_made_message
        self.invalid_action_message = invalid_action_message
        self.too_many_failed_actions = too_many_failed_actions_message
        self.max_failed_attempts = max_failed_attempts
        self.failed_action_attempts = 0
        self.get_current_board_action = get_current_board_action
        self.get_legal_moves_action = get_legal_moves_action
        self.reflect_action = reflect_action
        self.reflection_followup_prompt = reflection_followup_prompt
        self.make_move_action = make_move_action

    def generate_reply(
        self,
        messages: Optional[List[Dict[str, Any]]] = None,
        sender: Optional[ConversableAgent] = None,
        **kwargs: Any,
    ) -> Union[str, Dict, None]:
        if self._is_termination_msg(messages[-1]):
            return None
        action_choice = messages[-1]["content"].lower().strip()

        reply = ""

        # Use a switch statement to call the corresponding function
        if self.get_current_board_action in action_choice:
            reply = self.get_current_board()
            sender.has_requested_board = True
        elif self.get_legal_moves_action in action_choice:
            reply = self.get_legal_moves()
            sender.has_requested_board = True
        elif (
            len(messages) > 1
            and messages[-2]["content"].lower().strip() == self.reflect_action
        ):
            reply = self.reflection_followup_prompt
        elif self.reflect_action in action_choice:
            reply = self.reflect()
            sender.reflections_used += 1
            if not sender.has_requested_board:
                sender.reflections_used_before_board += 1

        else:
            # E.g. make_move e2e4 OR make_move c2c1r
            match = re.search(
                rf"{self.make_move_action} ([a-zA-Z0-9]{{4,5}})", action_choice
            )
            if match:
                try:
                    move = match.group(1)
                    self.make_move(move)
                    reply = self.move_was_made
                except Exception as e:
                    reply = f"Failed to make move: {e}"
                    self.failed_action_attempts += 1
                    sender.wrong_moves += 1
            else:
                reply = self.invalid_action_message
                self.failed_action_attempts += 1
                sender.wrong_actions += 1

        if self.failed_action_attempts >= self.max_failed_attempts:
            print(reply)
            reply = self.too_many_failed_actions

        return reply


class ChessEngineSunfishAgent(ConversableAgent):
    """
    A chess player agent that uses the Sunfish engine to select moves.
    Since it doesn't use move history, jsut the board state it must be inferior
    to a propper move selection accouinting for move history

    Attributes:
        make_move_action (str): The action string for making a move.
        get_current_board_action (str): The action string for getting legal moves.
    """

    def __init__(
        self,
        make_move_action: str,
        get_current_board_action: str,
        is_white: bool,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.make_move_action = make_move_action
        self.get_current_board_action = get_current_board_action
        self.is_white = is_white
        self.searcher = Searcher()

    def fen_to_sunfish(self, board: str) -> str:
        # Split the FEN string to get the board part and other components
        parts = board.split()
        board_part, color, castling, enpas = parts[0], parts[1], parts[2], parts[3]

        # Replace numbers with dots to represent empty squares
        board = re.sub(r"\d", lambda m: "." * int(m.group(0)), board_part)

        # Convert the board to the Sunfish format
        board = list(21 * " " + "  ".join(board.split("/")) + 21 * " ")
        board[9::10] = ["\n"] * 12
        board = "".join(board)

        # Calculate castling rights
        wc = ("Q" in castling, "K" in castling)
        bc = ("k" in castling, "q" in castling)

        # Calculate en passant square
        ep = parse(enpas) if enpas != "-" else 0

        # Calculate the score
        score = sum(pst[c][i] for i, c in enumerate(board) if c.isupper())
        score -= sum(
            pst[c.upper()][119 - i] for i, c in enumerate(board) if c.islower()
        )

        # Adjust score based on the player's color
        if color == "b":
            score = -score

        # Create the position
        pos = Position(board, score, wc, bc, ep, 0)
        return pos if self.is_white else pos.rotate()

    def move_to_uci(self, move):
        if move is None:
            return "(none)"
        i, j = move.i, move.j
        if not self.is_white:
            i, j = 119 - i, 119 - j
        return render(i) + render(j) + move.prom.lower()

    def generate_reply(
        self,
        messages: Optional[List[Dict[str, Any]]] = None,
        sender: Optional[ConversableAgent] = None,
        **kwargs: Any,
    ) -> Union[str, Dict, None]:
        if self._is_termination_msg(messages[-1]):
            return None

        last_message = messages[-1]["content"]

        try:
            # Convert the FEN to Sunfish format
            sunfish_position = self.fen_to_sunfish(last_message)

            # Use Sunfish to propose a move

            searcher = Searcher()
            best_move = None

            for _, gamma, score, move in searcher.search([sunfish_position]):
                if score >= gamma:
                    best_move = move
                    break

            # Make the move
            if best_move:
                move_str = self.move_to_uci(move)
                return f"{self.make_move_action} {move_str}"
            else:
                raise "No best move"

        except Exception:
            # Request the board state if parsing fails
            return self.get_current_board_action

        return self.get_legal_moves_action


class ChessEngineStockfishAgent(ConversableAgent):
    def __init__(
        self,
        board,
        make_move_action: str,
        time_limit=0.01,
        stockfish_path="/opt/homebrew/bin/stockfish",
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.board = board
        self.make_move_action = make_move_action
        self.stockfish_path = stockfish_path
        self.time_limit = time_limit

    def generate_reply(
        self,
        messages: Optional[List[Dict[str, Any]]] = None,
        sender: Optional[ConversableAgent] = None,
        **kwargs: Any,
    ) -> Union[str, Dict, None]:
        if self._is_termination_msg(messages[-1]):
            return None

        try:
            with chess.engine.SimpleEngine.popen_uci(self.stockfish_path) as engine:
                result = engine.play(
                    self.board, chess.engine.Limit(time=self.time_limit)
                )
                move = result.move
                return f"{self.make_move_action} {move.uci()}"
        except Exception as e:
            print(f"Error using Stockfish: {e}")
            return None
