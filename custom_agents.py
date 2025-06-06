import copy
import random
import time  # Add this import
import re
import chess
import chess.engine

from autogen import ConversableAgent
from typing import Any, Dict, List, Optional, Union

# Define retryable exceptions
RETRYABLE_EXCEPTIONS = (
    # OpenAI exceptions
    "openai.InternalServerError",
    # "openai.RateLimitError", 
    # "openai.APITimeoutError",
    # "openai.APIConnectionError",
    # # Anthropic exceptions
    # "anthropic.InternalServerError",
    # "anthropic.RateLimitError",
    # "anthropic.APITimeoutError", 
    # "anthropic.APIConnectionError",
    # # Generic connection/service errors
    # "ConnectionError",
    # "TimeoutError",
    # "ServiceUnavailableError",
)

def is_retryable_error(exception) -> bool:
    """Check if an exception is retryable based on its type or message."""
    exception_name = type(exception).__name__
    exception_module = type(exception).__module__
    full_exception_name = f"{exception_module}.{exception_name}"
    
    # Check if the exception type is in our retryable list
    for retryable in RETRYABLE_EXCEPTIONS:
        if retryable in full_exception_name or retryable in exception_name:
            return True
    
    # Check specific error messages
    error_message = str(exception).lower()
    retryable_messages = [
        "service is not available",
        "rate limit",
        "timeout",
        "connection error",
        "temporarily unavailable",
        "try again later",
        "internal server error"
    ]
    
    return any(msg in error_message for msg in retryable_messages)


class GameAgent(ConversableAgent):
    def __init__(
        self,
        dialog_turn_delay=0,
        max_retries=3,
        retry_delay=2.0,
        *args,
        **kwargs,
    ):
        """
        Initialize a GameAgent instance.

        Parameters:
            dialog_turn_delay (int): The delay (in seconds) before the agent responds during a dialog turn. Set to 0.
            max_retries (int): Maximum number of retries for API errors. Default is 3.
            retry_delay (float): Base delay in seconds between retries. Uses exponential backoff. Default is 2.0.
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
        # Track execution time of generate_reply
        self.accumulated_reply_time_seconds = 0.0
        # Retry configuration
        self.max_retries = max_retries
        self.retry_delay = retry_delay

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
        # Apply the delay before starting timing
        if isinstance(self.dialog_turn_delay, int) and self.dialog_turn_delay > 0:
            time.sleep(self.dialog_turn_delay)
        
        # Start timing only after the delay
        start_time = time.time()
        
        # Implement retry logic for API errors
        for attempt in range(self.max_retries + 1):  # +1 for initial attempt
            try:
                start_time = time.time()
                reply = super().generate_reply(messages, sender, **kwargs)
                end_time = time.time()
                # Accumulate only the actual execution time, not the delay
                self.accumulated_reply_time_seconds += (end_time - start_time)
                return reply
                
            except Exception as e:
                if attempt < self.max_retries and is_retryable_error(e):
                    # Calculate exponential backoff delay
                    delay = self.retry_delay * (2 ** attempt)
                    print(f"\033[93mAPI error on attempt {attempt + 1}/{self.max_retries + 1} for {self.name}: {str(e)}\033[0m")
                    print(f"\033[93mRetrying in {delay:.1f} seconds...\033[0m")
                    time.sleep(delay)
                    continue
                else:
                    # Either max retries reached or non-retryable error
                    end_time = time.time()
                    self.accumulated_reply_time_seconds += (end_time - start_time)
                    if attempt >= self.max_retries:
                        print(f"\033[91mMax retries ({self.max_retries}) reached for {self.name}. Error: {str(e)}\033[0m")
                    else:
                        print(f"\033[91mNon-retryable error for {self.name}: {str(e)}\033[0m")
                    raise e
        
        # This should never be reached, but just in case
        end_time = time.time()
        self.accumulated_reply_time_seconds += (end_time - start_time)
        return None


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


class ChessEngineDragonAgent(GameAgent):
    """
    A chess agent that uses the Komodo Dragon engine to determine moves.

    Parameters:
        board (chess.Board): The current state of the chess board.
        make_move_action (str): The action string used to indicate a move should be made.
        time_limit (float, optional): The maximum time (in seconds) the Dragon engine is allowed to think for a move. Default is 0.01s.
        level (Optional[int], optional): The skill level for the Dragon engine. Values typically range from 1-25. Default is 1.
        dragon_path (str, optional): The file path to the Dragon executable. Default is "./dragon/dragon-osx".
        remove_history (bool, optional): If True, the agent will reset the board's move history before making a decision. Default is False.
    """

    def __init__(
        self,
        board,
        make_move_action: str,
        time_limit=0.01,
        level: int = 1,
        dragon_path="./dragon/dragon-osx",
        remove_history: bool = False,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.board = board
        self.make_move_action = make_move_action
        self.dragon_path = dragon_path
        self.time_limit = time_limit
        self.remove_history = remove_history
        self.level = level  # Store skill level

    def generate_reply(
        self,
        messages: Optional[List[Dict[str, Any]]] = None,
        sender: Optional[ConversableAgent] = None,
        **kwargs: Any,
    ) -> Union[str, Dict, None]:
        if self._is_termination_msg(messages[-1]):
            return None

        try:
            with chess.engine.SimpleEngine.popen_uci(self.dragon_path) as engine:

                # Set Dragon skill level if specified
                if self.level is not None:
                    engine.configure({"Skill": self.level})

                b = self.board
                if self.remove_history:
                    b = chess.Board(b.fen())
                result = engine.play(b, chess.engine.Limit(time=self.time_limit))
                move = result.move
                return f"{self.make_move_action} {move.uci()}"
        except Exception as e:
            print(f"Error using Dragon engine: {e}")
            return None


class NonGameAgent(GameAgent):
    """
    A Network-of-Networks (NoN) GameAgent that routes queries through multiple LLMs and synthesizes their responses.

    This agent is designed to collect answers from a set of large language models (LLMs), critically evaluate their outputs,
    and produce a single, high-quality synthesized response. It tracks usage statistics for each underlying agent and
    is intended for scenarios where ensemble reasoning or model comparison is desired.

    Attributes:
        llm_config: the syntehesizer model
        llm_configs (List[Dict]): List of configuration dictionaries for the LLMs used by this agent.
        usage_stats_per_agent (List[Dict]): Tracks usage statistics for each LLM agent. The last element in the list is the synthesizer. First and seconnd correspond to models in llm_configs.
        total_prompt_tokens (int): Total prompt tokens used across all agents.
        total_completion_tokens (int): Total completion tokens used across all agents.
        total_tokens (int): Total tokens used across all agents.
        total_cost (float): Total cost incurred across all agents.
    """

    def __init__(
        self,
        dialog_turn_delay=0,
        llm_configs=None,
        *args,
        **kwargs,
    ):
        """
        Initialize a Network-of-Networks Agent that run the question through multiple LLMs and then synthesizes the responses.

        Parameters:
            dialog_turn_delay (int): The delay (in seconds) before the agent responds during a dialog turn.
            llm_configs (List[Dict]): List of configuration dictionaries for the multiple LLMs this agent will use.
            *args, **kwargs: Additional arguments passed to the parent GameAgent class.
        """
        super().__init__(dialog_turn_delay=dialog_turn_delay, *args, **kwargs)
        self.llm_configs = llm_configs
#         self.synthesizer = ConversableAgent(
#             name="NoN_Synthesizer",
#             llm_config=self.llm_config,
#             human_input_mode="NEVER",
#             system_message = """\
# You will be provided with a set of responses from various open-source models to the latest user query.
# Your task is to synthesize these responses into a single, high-quality response in British English spelling.
# It is crucial to critically evaluate the information provided in these responses, recognizing that some of it may be biased or incorrect.
# Your response should not simply replicate the given answers but should offer a refined, accurate, and comprehensive reply to the instruction.
# Ensure your response is well-structured, coherent and adheres to the highest standards of accuracy and reliability.
# """
#         )
        self._name = "NoN_Synthesizer"
        self._human_input_mode="NEVER",
        self._system_message = """\
You will be provided with a set of responses from various open-source models to the latest user query.
Your task is to synthesize these responses into a single, high-quality response in British English spelling.
It is crucial to critically evaluate the information provided in these responses, recognizing that some of it may be biased or incorrect.
Your response should not simply replicate the given answers but should offer a refined, accurate, and comprehensive reply to the instruction.
Ensure your response is well-structured, coherent and adheres to the highest standards of accuracy and reliability.
"""
        # Initialize usage statistics tracking
        self.usage_stats_per_agent = []
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_tokens = 0
        self.total_cost = 0


    def generate_reply(
        self,
        messages: Optional[List[Dict[str, Any]]] = None,
        sender: Optional[ConversableAgent] = None,
        **kwargs: Any,
    ) -> Union[str, Dict, None]:
        if self._is_termination_msg(messages[-1]):
            return None

        user_query = messages[-1]["content"]
        responses = []
        usage_stats = []
        
        # First collect all responses from the LLMs
        for i, config in enumerate(self.llm_configs):
            ag = ConversableAgent(
                name=f"NoN_LLM_{i}",
                llm_config=config,
                human_input_mode="NEVER",
                **kwargs,
            )
            ag.reset() # clear associated usage stats in the client
            
            # Add retry logic for generate_reply
            max_retries = 4
            retry_count = 0
            response = None
            
            while retry_count < max_retries:
                try:
                    start_time = time.time()
                    response = ag.generate_reply(messages)
                    end_time = time.time()
                    self.accumulated_reply_time_seconds += (end_time - start_time)
                    break  # Success, exit the retry loop
                except Exception as e:
                    retry_count += 1
                    print(f"API error on model {i} (attempt {retry_count}/{max_retries}): {str(e)}")
                    if retry_count < max_retries:
                        print("Retrying in 4 seconds...")
                        time.sleep(4)
                    else:
                        print(f"Failed after {max_retries} attempts.")
                        response = f"[Error: Failed to get response from model {i} after {max_retries} attempts]"
            
            responses.append(response)
            
            ag_usage = ag.get_total_usage()
            if ag_usage:
                usage_stats.append(ag_usage)
        
        # Prepare the merged query for the synthesizer
        merged_query = f"User query\\>\n\n {user_query}\n\n"
        for i, response in enumerate(responses):
            merged_query += f"Model {i+1} response\\>\n{response}\n\n"
        
        # Get synthesizer response with retry logic
        new_messages = messages[:-1] if messages else []
        new_messages.append({"content": merged_query, "role": "user"})
        
        response = super().generate_reply(new_messages, sender, **kwargs)

        # Ensure we have enough slots in total_usage_stats
        if len(self.usage_stats_per_agent) < len(self.llm_configs) + 1:
            for _ in range(len(self.usage_stats_per_agent), len(self.llm_configs) + 1):
                self.usage_stats_per_agent.append({})
        
        # Update total usage statistics once before returning
        for i, stats in enumerate(usage_stats):
            # Update or initialize the stats for this agent
            if not self.usage_stats_per_agent[i]:
                self.usage_stats_per_agent[i] = copy.deepcopy(stats)
            else:
                for model, data in stats.items():
                    if model != "total_cost" and isinstance(data, dict):
                        model_stats = self.usage_stats_per_agent[i][model]
                        model_stats["prompt_tokens"] += data.get("prompt_tokens", 0)
                        model_stats["completion_tokens"] += data.get("completion_tokens", 0)
                        model_stats["total_tokens"] += data.get("total_tokens", 0)
            
            # Update the global token counters
            for model_name, model_data in stats.items():
                if model_name != "total_cost" and isinstance(model_data, dict):
                    self.total_prompt_tokens += model_data.get("prompt_tokens", 0)
                    self.total_completion_tokens += model_data.get("completion_tokens", 0)
                    self.total_tokens += model_data.get("total_tokens", 0)


        ## Add synthesizer usage separately
        synthesizer_usage = copy.deepcopy(self.get_total_usage())

        if not self.usage_stats_per_agent[-1]:
            self.usage_stats_per_agent[-1] = copy.deepcopy(synthesizer_usage)
            for model, data in self.usage_stats_per_agent[-1].items():
                if model != "total_cost" and isinstance(data, dict):
                        model_stats = self.usage_stats_per_agent[-1][model]
                        model_stats["prompt_tokens"] = 0
                        model_stats["completion_tokens"] = 0
                        model_stats["total_tokens"] = 0

        prev_synthesizer_usage = self.usage_stats_per_agent[-1]
        self.usage_stats_per_agent[-1] = synthesizer_usage

        for model, data in self.usage_stats_per_agent[-1].items():
            if model != "total_cost" and isinstance(data, dict):
                self.total_prompt_tokens += synthesizer_usage[model].get("prompt_tokens", 0) - prev_synthesizer_usage[model].get("prompt_tokens", 0)
                self.total_completion_tokens += synthesizer_usage[model].get("completion_tokens", 0) - prev_synthesizer_usage[model].get("completion_tokens", 0)
                self.total_tokens += synthesizer_usage[model].get("total_tokens", 0) - prev_synthesizer_usage[model].get("total_tokens", 0)

        return response