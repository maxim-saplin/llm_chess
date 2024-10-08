import random
import re
import chess
from autogen import ConversableAgent
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

        last_message = messages[-1]["content"].lower().strip()

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
        make_move,
        move_was_made_message,
        invalid_action_message,
        too_many_failed_actions_message,
        max_failed_attempts,
        get_current_board_action,
        get_legal_moves_action,
        make_move_action,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.get_current_board = get_current_board
        self.get_legal_moves = get_legal_moves
        self.make_move = make_move
        self.move_was_made = move_was_made_message
        self.invalid_action_message = invalid_action_message
        self.too_many_failed_actions = too_many_failed_actions_message
        self.max_failed_attempts = max_failed_attempts
        self.failed_action_attempts = 0
        self.get_current_board_action = get_current_board_action
        self.get_legal_moves_action = get_legal_moves_action
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
        elif self.get_legal_moves_action in action_choice:
            reply = self.get_legal_moves()
        else:
            match = re.search(rf"{self.make_move_action} (\S{{4}})", action_choice)
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

class ChessEnginePlayerAgent(ConversableAgent):