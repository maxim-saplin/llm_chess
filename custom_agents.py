import random
import time  # Add this import
import re
import chess
import chess.engine

from autogen import ConversableAgent
from typing import Any, Dict, List, Optional, Union


class GameAgent(ConversableAgent):
    def __init__(
        self,
        dialog_turn_delay=0,
        *args,
        **kwargs,
    ):
        """
        Initialize a GameAgent instance.

        Parameters:
            dialog_turn_delay (int): The delay (in seconds) before the agent responds during a dialog turn. Set to 0.
        """
        super().__init__(*args, **kwargs)
        # Initialize the counter for wrong moves made by the agent.
        self.wrong_moves = 0
        # Initialize the counter for wrong actions performed by the agent.
        self.wrong_actions = 0
        self.get_board_count = 0
        self.get_legal_moves_count = 0
        self.make_move_count = 0
        # Flag to track if the agent has requested the board state (either current board or legal moves).
        self.has_requested_board = False
        # Counter to track the number of failed action attempts by the agent.
        self.failed_action_attempts = 0
        self.dialog_turn_delay = dialog_turn_delay  # Store it locally

    def prep_to_move(self):
        """
        Prepares the player agent to make a move by resetting relevant state variables.
        """
        self.has_requested_board = False
        self.failed_action_attempts = 0

    def generate_reply(
        self,
        messages: Optional[List[Dict[str, Any]]] = None,
        sender: Optional[ConversableAgent] = None,
        **kwargs: Any,
    ) -> Union[str, Dict, None]:
        if isinstance(self.dialog_turn_delay, int) and self.dialog_turn_delay > 0:
            time.sleep(self.dialog_turn_delay)
        return super().generate_reply(messages, sender, **kwargs)


class RandomPlayerAgent(GameAgent):
    """
    A random chess player agent that selects moves randomly from legal options.

    Attributes:
        make_move_action (str): The action string for making a move.
        get_legal_moves_action (str): The action string for getting legal moves.
        get_current_board_action (Optional[str]): Set to action name if you want board printed while random player makes moves
    """

    def __init__(
        self,
        make_move_action: str,
        get_legal_moves_action: str,
        get_current_board_action: Optional[str] = None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.make_move_action = make_move_action
        self.get_legal_moves_action = get_legal_moves_action
        self.get_current_board_action = get_current_board_action
        self.flip_flag = True

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
                if self.flip_flag and self.get_current_board_action:
                    self.flip_flag = False
                    return self.get_current_board_action

                random_move = random.choice(legal_moves)

                chess.Move.from_uci(
                    random_move
                ).uci()  # Throws if invalid move is provided, i.e. if previous action was not get_legal_moves
                self.flip_flag = True
                return f"{self.make_move_action} {random_move}"
        except Exception:
            return self.get_legal_moves_action

        return self.get_legal_moves_action


class AutoReplyAgent(GameAgent):
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
        ignore_text (str): A regex pattern to identify and ignore specific text segments in replies.
    """

    def __init__(
        self,
        get_current_board,
        get_legal_moves,
        make_move,
        move_was_made_message,
        invalid_action_message,
        too_many_failed_actions_message,
        max_failed_attempts,
        get_current_board_action,
        get_legal_moves_action,
        reflect_action,
        make_move_action,
        reflect_prompt,
        reflection_followup_prompt,
        remove_text,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.get_current_board = get_current_board
        self.get_legal_moves = get_legal_moves
        self.make_move = make_move
        self.move_was_made = move_was_made_message
        self.invalid_action_message = invalid_action_message
        self.too_many_failed_actions_message = too_many_failed_actions_message
        self.max_failed_attempts = max_failed_attempts
        self.get_current_board_action = get_current_board_action
        self.get_legal_moves_action = get_legal_moves_action
        self.reflect_action = reflect_action
        self.make_move_action = make_move_action
        self.reflect_prompt = reflect_prompt
        self.reflection_followup_prompt = reflection_followup_prompt
        self.remove_text = remove_text

    def generate_reply(
        self,
        messages: Optional[List[Dict[str, Any]]] = None,
        sender: Optional[ConversableAgent] = None,
        **kwargs: Any,
    ) -> Union[str, Dict, None]:
        if self._is_termination_msg(messages[-1]):
            return None

        # Apply remove_text regex to modify message history
        if self.remove_text:
            # Clean all messages in the current conversation
            for msg in messages:
                msg["content"] = re.sub(self.remove_text, "", msg["content"], flags=re.DOTALL)
            
            # Clean internal message histories
            if sender and hasattr(sender, '_oai_messages'):
                for msgs in sender._oai_messages.values():
                    for msg in msgs:
                        if "content" in msg:  # Make sure content exists
                            msg["content"] = re.sub(self.remove_text, "", msg["content"], flags=re.DOTALL)
            
            if hasattr(self, '_oai_messages'):
                for msgs in self._oai_messages.values():
                    for msg in msgs:
                        if "content" in msg:  # Make sure content exists
                            msg["content"] = re.sub(self.remove_text, "", msg["content"], flags=re.DOTALL)

        action_choice = messages[-1]["content"].lower().strip()
        reply = ""

        if self.get_current_board_action in action_choice:
            sender.get_board_count += 1
            reply = self.get_current_board()
            sender.has_requested_board = True
        elif self.get_legal_moves_action in action_choice:
            sender.get_legal_moves_count += 1
            reply = self.get_legal_moves()
            sender.has_requested_board = True
        elif len(messages) > 2 and messages[-2]["content"] == self.reflect_prompt:
            reply = self.reflection_followup_prompt
        elif self.reflect_action in action_choice:
            reply = self.reflect_prompt
            sender.reflections_used += 1
            if not sender.has_requested_board:
                sender.reflections_used_before_board += 1

        else:
            # E.g. make_move e2e4 OR make_move c2c1r
            match = re.search(
                rf"{self.make_move_action} ([a-zA-Z0-9]{{4,5}})", action_choice
            )
            if match:
                sender.make_move_count += 1
                try:
                    move = match.group(1)
                    self.make_move(move)
                    reply = self.move_was_made
                except Exception as e:
                    reply = f"Failed to make move: {e}"
                    sender.failed_action_attempts += 1
                    sender.wrong_moves += 1
            else:
                reply = self.invalid_action_message
                sender.failed_action_attempts += 1
                sender.wrong_actions += 1

        if sender.failed_action_attempts >= self.max_failed_attempts:
            print("BREAKING >>> " + reply)
            reply = self.too_many_failed_actions_message

        return reply


class ChessEngineStockfishAgent(GameAgent):
    """
    A chess agent that uses the Stockfish engine to determine moves.

    Parameters:
        board (chess.Board): The current state of the chess board.
        make_move_action (str): The action string used to indicate a move should be made.
        time_limit (float, optional): The maximum time (in seconds) the Stockfish engine is allowed to think for a move. Default is 0.01s.
        stockfish_path (str, optional): The file path to the Stockfish executable. Default is "/opt/homebrew/bin/stockfish".
        remove_history (bool, optional): If True, the agent will reset the board's move history before making a decision. Default is False.
    """

    def __init__(
        self,
        board,
        make_move_action: str,
        time_limit=0.01,
        level: Optional[int] = None,
        stockfish_path="/opt/homebrew/bin/stockfish",
        remove_history: bool = False,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.board = board
        self.make_move_action = make_move_action
        self.stockfish_path = stockfish_path
        self.time_limit = time_limit
        self.remove_history = remove_history
        self.level = level  # Store stockfish_level

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

                # Set Stockfish skill level (0-20)
                if self.level is not None:
                    engine.configure({"Skill Level": self.level})

                b = self.board
                if self.remove_history:
                    b = chess.Board(b.fen())
                result = engine.play(b, chess.engine.Limit(time=self.time_limit))
                move = result.move
                return f"{self.make_move_action} {move.uci()}"
        except Exception as e:
            print(f"Error using Stockfish: {e}")
            return None
