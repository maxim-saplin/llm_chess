import os
import sys
import re
from autogen import gather_usage_summary
from typing import Any
from pprint import pprint
from dotenv import load_dotenv
import json
import chess
from typing import Optional, Dict, Tuple
from urllib.parse import urlsplit, urlunsplit

# Capability mapping for model-specific features
PROVIDER_CAPABILITIES = {
    "openai": {"reasoning_effort", "frequency_penalty", "presence_penalty"},
    "azure": {"reasoning_effort", "frequency_penalty", "presence_penalty"},
    "azure_responses": {"reasoning_effort", "frequency_penalty", "presence_penalty"},
    "xai": {"reasoning_effort", "frequency_penalty", "presence_penalty"},
    "anthropic": {"thinking_budget", "max_tokens"},
    "google": {"top_k"},
    "local": {"reasoning_effort"},
    "groq": {"reasoning_effort"},
    "cerebras": {"reasoning_effort"},
    "mistral": set(),
}

def infer_api_type_for_metadata(provider_conf: Dict[str, Any]) -> Optional[str]:
    """Infer a provider api_type from a runtime provider config for metadata only.

    Rules:
    - If provider_conf already declares api_type, return it.
    - If base_url points to localhost/127.0.0.1 → "local".
    - Recognize common OpenAI-compatible hosts and return their short ids.
    - Otherwise return "oai_comp_endpoint" to denote a generic OpenAI-compatible endpoint.
    """
    try:
        declared = provider_conf.get("api_type")
        if isinstance(declared, str) and declared:
            return declared

        base_url = str(provider_conf.get("base_url", "")).strip().lower()
        if not base_url:
            return None

        # Explicit local endpoints
        if base_url.startswith("http://localhost") or base_url.startswith("https://localhost") or "127.0.0.1" in base_url:
            return "local"

        # Known hosted OpenAI-compatible providers
        if "api.deepseek.com" in base_url or "deepseek" in base_url:
            return "deepseek"
        if "hunyuan" in base_url or "tencent" in base_url:
            return "tencent"
        if "dashscope" in base_url or "aliyuncs.com" in base_url:
            return "dashscope"
        if "openrouter.ai" in base_url:
            return "openrouter"
        if "inceptionlabs" in base_url:
            return "inceptionlabs"
        if "x.ai" in base_url:
            return "xai"

        # Default for unknown remote OpenAI-compatible endpoints
        return "oai_comp_endpoint"
    except Exception:
        return None

def extract_reasoning_effort(provider_conf: Dict[str, Any]) -> Any:
    """Read reasoning effort from current extra_body configs or legacy direct fields."""
    effort = provider_conf.get("reasoning_effort")
    if effort is not None:
        return effort

    extra_body = provider_conf.get("extra_body")
    if not isinstance(extra_body, dict):
        return None

    effort = extra_body.get("reasoning_effort")
    if effort is not None:
        return effort

    reasoning = extra_body.get("reasoning")
    if isinstance(reasoning, dict):
        return reasoning.get("effort")
    return None


_REQUEST_BODY_REASONING_API_TYPES = {"openai", "azure", "responses", "groq", "cerebras"}


def _provider_conf_with_reasoning_effort(provider_conf: Dict[str, Any], effort: Any) -> Dict[str, Any]:
    """Set effort using raw request bodies for configured chat/Responses APIs."""
    api_type = provider_conf.get("api_type") or "openai"
    normalized_conf = provider_conf.copy()

    if api_type not in _REQUEST_BODY_REASONING_API_TYPES:
        normalized_conf["reasoning_effort"] = effort
        return normalized_conf

    normalized_conf.pop("reasoning_effort", None)
    extra_body = normalized_conf.get("extra_body")
    if extra_body is None:
        extra_body = {}
    elif isinstance(extra_body, dict):
        extra_body = extra_body.copy()
    else:
        raise ValueError("extra_body must be a dictionary to set reasoning_effort")

    if api_type == "responses":
        reasoning = extra_body.get("reasoning")
        if reasoning is None:
            reasoning = {}
        elif isinstance(reasoning, dict):
            reasoning = reasoning.copy()
        else:
            raise ValueError("extra_body['reasoning'] must be a dictionary for the Responses API")
        reasoning["effort"] = effort
        extra_body["reasoning"] = reasoning
    else:
        extra_body["reasoning_effort"] = effort

    normalized_conf["extra_body"] = extra_body
    return normalized_conf


def normalize_reasoning_effort_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Move typed AG2 reasoning fields into raw request bodies where supported.

    Chat-style APIs use ``extra_body.reasoning_effort``; the Responses API uses
    ``extra_body.reasoning.effort``. Other provider clients retain their native
    config field. The input config is not mutated.
    """
    if not isinstance(config, dict):
        return config

    config_list = config.get("config_list")
    if not isinstance(config_list, list):
        return config

    normalized_list = list(config_list)
    changed = False

    for index, provider_conf in enumerate(config_list):
        if (
            not isinstance(provider_conf, dict)
            or provider_conf.get("reasoning_effort") is None
        ):
            continue

        api_type = provider_conf.get("api_type") or "openai"
        if api_type not in _REQUEST_BODY_REASONING_API_TYPES:
            continue

        normalized_list[index] = _provider_conf_with_reasoning_effort(
            provider_conf, provider_conf["reasoning_effort"]
        )
        changed = True

    if not changed:
        return config

    normalized_config = config.copy()
    normalized_config["config_list"] = normalized_list
    # Match the existing reasoning-mode behavior when normalizing a raw config.
    normalized_config.pop("temperature", None)
    return normalized_config


def _merge_hyperparams(model_params: Optional[Dict]) -> Dict:
    """Return a copy of per-model hyperparams (no defaults here by design)."""
    merged: Dict = {}
    if model_params and "hyperparams" in model_params:
        merged.update(model_params["hyperparams"])  # shallow copy of provided hyperparams
    return merged


def _normalize_azure_responses_endpoint(endpoint: str, api_version: str) -> Tuple[str, Dict[str, str]]:
    """Convert an Azure endpoint into an OpenAI Responses-compatible base URL."""
    parsed = urlsplit(endpoint.strip())
    base_path = parsed.path.rstrip("/")

    if base_path.endswith("/openai/v1"):
        normalized_path = base_path
    elif base_path.endswith("/openai"):
        normalized_path = f"{base_path}/v1"
    else:
        openai_index = base_path.find("/openai/")
        if openai_index != -1:
            base_path = base_path[:openai_index]
        normalized_path = f"{base_path}/openai/v1" if base_path else "/openai/v1"

    normalized_base_url = urlunsplit(
        (parsed.scheme, parsed.netloc, normalized_path, "", "")
    )
    return normalized_base_url, {"api-version": api_version}


def validate_model_config(model_config: Dict, provider_type: str):
    """Validate that the provided configuration is compatible with the provider."""
    if not model_config:
        return
    capabilities = PROVIDER_CAPABILITIES.get(provider_type, set())
    if "reasoning_effort" in model_config and "reasoning_effort" not in capabilities:
        raise ValueError(f"reasoning_effort not supported by {provider_type}")
    if "thinking_budget" in model_config and "thinking_budget" not in capabilities:
        raise ValueError(f"thinking_budget not supported by {provider_type}")


def _apply_model_specific_config(config: Dict, model_params: Dict, provider_type: str):
    """Apply merged hyperparameters and provider-specific features."""
    merged_hyperparams = _merge_hyperparams(model_params)

    # Provider-specific features
    if provider_type in ("openai", "azure", "azure_responses", "xai", "local", "groq", "cerebras"):
        if model_params and model_params.get("reasoning_effort") is not None:
            # Use raw request fields for OpenAI-compatible APIs; keep custom clients native.
            if config.get("config_list"):
                config["config_list"][0] = _provider_conf_with_reasoning_effort(
                    config["config_list"][0], model_params["reasoning_effort"]
                )
        config = normalize_reasoning_effort_config(config)
        if config.get("config_list") and extract_reasoning_effort(config["config_list"][0]) is not None:
            # Remove temperature when reasoning_effort is used (top_p is preserved).
            merged_hyperparams.pop("temperature", None)
    elif provider_type == "anthropic":
        if model_params and "thinking_budget" in model_params:
            # Store thinking configuration inside the provider-specific entry to comply with AutoGen's schema
            if config.get("config_list"):
                config["config_list"][0]["thinking"] = {
                    "type": "enabled",
                    "budget_tokens": model_params["thinking_budget"],
                }
            # Remove top_p in thinking mode
            merged_hyperparams.pop("top_p", None)
            # Remove temperature in thinking mode to match get_llms_autogen behavior
            merged_hyperparams.pop("temperature", None)

    # Apply final hyperparams
    for param, value in merged_hyperparams.items():
        if value is not None:
            config[param] = value
    return config


def get_llms(
    white_hyperparams: Optional[Dict] = None,
    black_hyperparams: Optional[Dict] = None,
    timeout: int = 1800,
) -> Tuple[Dict, Dict]:
    """Create LLM configurations from environment + per-model hyperparameter settings.

    Note: This function is intentionally "dumb" about defaults. Provide defaults
    via the caller (e.g., from llm_chess.default_hyperparams) inside the
    `{"hyperparams": {...}}` dicts passed in.
    """
    load_dotenv()
    white_hyperparams = white_hyperparams or {}
    black_hyperparams = black_hyperparams or {}

    model_kinds = [
        os.environ.get("MODEL_KIND_W", "none"),
        os.environ.get("MODEL_KIND_B", "none"),
    ]

    def _provider_base_config(kind: str, key: str) -> Dict:
        if kind == "azure":
            return {
                "api_type": "azure",
                "model": os.environ[f"AZURE_OPENAI_DEPLOYMENT_{key}"],
                "api_key": os.environ[f"AZURE_OPENAI_KEY_{key}"],
                "base_url": os.environ[f"AZURE_OPENAI_ENDPOINT_{key}"],
                "api_version": os.environ[f"AZURE_OPENAI_VERSION_{key}"],
            }
        elif kind == "azure_responses":
            base_url, default_query = _normalize_azure_responses_endpoint(
                os.environ[f"AZURE_OPENAI_ENDPOINT_{key}"],
                os.environ[f"AZURE_OPENAI_VERSION_{key}"],
            )
            return {
                "api_type": "responses",
                "model": os.environ[f"AZURE_OPENAI_DEPLOYMENT_{key}"],
                "api_key": os.environ[f"AZURE_OPENAI_KEY_{key}"],
                "base_url": base_url,
                "default_query": default_query,
            }
        elif kind == "local":
            return {
                "model": os.environ[f"LOCAL_MODEL_NAME_{key}"],
                "base_url": os.environ[f"LOCAL_BASE_URL_{key}"],
                "api_key": os.environ.get(f"LOCAL_API_KEY_{key}", "any"),
                "default_headers": {"Api-Key": os.environ.get(f"LOCAL_API_KEY_{key}", "any")},
            }
        elif kind == "groq":
            return {
                "model": os.environ[f"GROQ_MODEL_NAME_{key}"],
                "api_key": os.environ.get(f"GROQ_API_KEY_{key}", "any"),
                "api_type": "groq",
            }
        elif kind == "cerebras":
            return {
                "model": os.environ[f"CEREBRAS_MODEL_NAME_{key}"],
                "api_key": os.environ.get(f"CEREBRAS_API_KEY_{key}", "any"),
                "api_type": "cerebras",
            }
        elif kind == "google":
            return {
                "model": os.environ[f"GEMINI_MODEL_NAME_{key}"],
                "api_key": os.environ[f"GEMINI_API_KEY_{key}"],
                "api_type": "google",
            }
        elif kind == "openai":
            return {
                "model": os.environ[f"OPENAI_MODEL_NAME_{key}"],
                "api_key": os.environ[f"OPENAI_API_KEY_{key}"],
                "api_type": "openai",
            }
        elif kind == "xai":
            return {
                "model": os.environ[f"XAI_MODEL_NAME_{key}"],
                "api_key": os.environ[f"XAI_API_KEY_{key}"],
                "base_url": "https://api.x.ai/v1",
            }
        elif kind == "anthropic":
            return {
                "model": os.environ[f"ANTHROPIC_MODEL_NAME_{key}"],
                "api_key": os.environ[f"ANTHROPIC_API_KEY_{key}"],
                "api_type": "anthropic",
                "max_tokens": 32768,
                "timeout": timeout,
            }
        elif kind == "mistral":
            return {
                "model": os.environ[f"MISTRAL_MODEL_NAME_{key}"],
                "api_key": os.environ[f"MISTRAL_API_KEY_{key}"],
                "api_type": "mistral",
            }
        else:
            raise ValueError(f"Unsupported provider type '{kind}'")

    def _build_config(kind: str, key: str, model_params: Dict) -> Dict:
        provider_conf = _provider_base_config(kind, key)
        # Apply provider overrides if any
        if model_params and "provider_overrides" in model_params:
            provider_conf.update(model_params["provider_overrides"])

        config = {
            "config_list": [provider_conf],
            "timeout": timeout,
            "cache_seed": None,
        }

        validate_model_config(model_params, kind)
        return _apply_model_specific_config(config, model_params, kind)

    config_white = _build_config(model_kinds[0], "W", white_hyperparams)
    config_black = _build_config(model_kinds[1], "B", black_hyperparams)
    return config_white, config_black


# Material values: pawn = 1, knight = 3, bishop = 3, rook = 5, queen = 9
# The maximum total material in chess is 39 for each player


def calculate_material_count(board):
    piece_values = {
        chess.PAWN: 1,
        chess.KNIGHT: 3,
        chess.BISHOP: 3,
        chess.ROOK: 5,
        chess.QUEEN: 9,
    }
    white_material = sum(
        piece_values.get(piece.piece_type, 0)
        for piece in board.piece_map().values()
        if piece.color == chess.WHITE
    )
    black_material = sum(
        piece_values.get(piece.piece_type, 0)
        for piece in board.piece_map().values()
        if piece.color == chess.BLACK
    )
    return white_material, black_material


load_dotenv()

def generate_game_stats(
    time_started: str,
    winner: str,
    reason: str,
    current_move: int,
    player_white: Any,
    player_black: Any,
    material_count: dict,
    pgn_string: str = None,
) -> dict:
    """Generate game statistics."""
    # Determine model name and usage stats for white player
    if hasattr(player_white, 'total_prompt_tokens') and hasattr(player_white, 'total_completion_tokens'):
        white_model = "non"
        white_usage = {
            "total_cost": player_white.total_cost if hasattr(player_white, 'total_cost') else 0,
            "non": {
                "prompt_tokens": player_white.total_prompt_tokens,
                "completion_tokens": player_white.total_completion_tokens,
                "total_tokens": player_white.total_tokens if hasattr(player_white, 'total_tokens') else 0
            }
        }
    else:
        white_summary = gather_usage_summary([player_white])
        # Try to extract the model name from player_white.llm_config, supporting both dict and LLMConfig object
        if isinstance(player_white.llm_config, dict):
            white_model = player_white.llm_config.get("config_list", [{}])[0].get("model", "N/A")
        elif hasattr(player_white.llm_config, "config_list"):
            # LLMConfig object: config_list is a list of dicts or config entries
            config_list = getattr(player_white.llm_config, "config_list", [])
            if config_list:
                # config_list may contain dicts or objects with .model attribute
                first_entry = config_list[0]
                if isinstance(first_entry, dict):
                    white_model = first_entry.get("model", "N/A")
                elif hasattr(first_entry, "model"):
                    white_model = getattr(first_entry, "model", "N/A")
                else:
                    white_model = "N/A"
            else:
                white_model = "N/A"
        else:
            white_model = "N/A"
        white_usage = white_summary["usage_excluding_cached_inference"] if white_summary else {}

    # Determine model name and usage stats for black player
    if hasattr(player_black, 'total_prompt_tokens') and hasattr(player_black, 'total_completion_tokens'):
        black_model = "non"
        black_usage = {
            "total_cost": player_black.total_cost if hasattr(player_black, 'total_cost') else 0,
            "non": {
                "prompt_tokens": player_black.total_prompt_tokens,
                "completion_tokens": player_black.total_completion_tokens,
                "total_tokens": player_black.total_tokens if hasattr(player_black, 'total_tokens') else 0
            }
        }
    else:
        black_summary = gather_usage_summary([player_black])
        # Try to extract the model name from player_black.llm_config, supporting both dict and LLMConfig object
        if isinstance(player_black.llm_config, dict):
            black_model = player_black.llm_config.get("config_list", [{}])[0].get("model", "N/A")
        elif hasattr(player_black.llm_config, "config_list"):
            # LLMConfig object: config_list is a list of dicts or config entries
            config_list = getattr(player_black.llm_config, "config_list", [])
            if config_list:
                # config_list may contain dicts or objects with .model attribute
                first_entry = config_list[0]
                if isinstance(first_entry, dict):
                    black_model = first_entry.get("model", "N/A")
                elif hasattr(first_entry, "model"):
                    black_model = getattr(first_entry, "model", "N/A")
                else:
                    black_model = "N/A"
            else:
                black_model = "N/A"
        else:
            black_model = "N/A"
        black_usage = black_summary["usage_excluding_cached_inference"] if black_summary else {}

    stats = {
        "time_started": time_started,
        "winner": winner,
        "reason": reason,
        "number_of_moves": current_move,
        "player_white": {
            "name": player_white.name,
            "wrong_moves": player_white.wrong_moves,
            "wrong_actions": player_white.wrong_actions,
            "reflections_used": player_white.reflections_used,
            "reflections_used_before_board": player_white.reflections_used_before_board,
            "get_board_count": player_white.get_board_count,
            "get_legal_moves_count": player_white.get_legal_moves_count,
            "make_move_count": player_white.make_move_count,
            "accumulated_reply_time_seconds": player_white.accumulated_reply_time_seconds,
            "model": white_model,
        },
        "material_count": material_count,
        "player_black": {
            "name": player_black.name,
            "wrong_moves": player_black.wrong_moves,
            "wrong_actions": player_black.wrong_actions,
            "reflections_used": player_black.reflections_used,
            "reflections_used_before_board": player_black.reflections_used_before_board,
            "get_board_count": player_black.get_board_count,
            "get_legal_moves_count": player_black.get_legal_moves_count,
            "make_move_count": player_black.make_move_count,
            "accumulated_reply_time_seconds": player_black.accumulated_reply_time_seconds,
            "model": black_model,
        },
        "usage_stats": {
            "white": white_usage,
            "black": black_usage,
        },
    }
    
    # Add usage_stats_per_non_agent for white player if it's a NoN agent
    if hasattr(player_white, 'usage_stats_per_agent'):
        stats["usage_stats_per_non_agent_white"] = []
        for agent_stats in player_white.usage_stats_per_agent:
            # Extract simplified stats from each agent
            for model_name, model_data in agent_stats.items():
                if model_name != "total_cost" and isinstance(model_data, dict):
                    stats["usage_stats_per_non_agent_white"].append({
                        "model": model_name,
                        "prompt_tokens": model_data.get("prompt_tokens", 0),
                        "completion_tokens": model_data.get("completion_tokens", 0),
                        "total_tokens": model_data.get("total_tokens", 0)
                    })
                    break  # Only take the first model data
    
    # Add usage_stats_per_non_agent for black player if it's a NoN agent
    if hasattr(player_black, 'usage_stats_per_agent'):
        stats["usage_stats_per_non_agent_black"] = []
        for agent_stats in player_black.usage_stats_per_agent:
            # Extract simplified stats from each agent
            for model_name, model_data in agent_stats.items():
                if model_name != "total_cost" and isinstance(model_data, dict):
                    stats["usage_stats_per_non_agent_black"].append({
                        "model": model_name,
                        "prompt_tokens": model_data.get("prompt_tokens", 0),
                        "completion_tokens": model_data.get("completion_tokens", 0),
                        "total_tokens": model_data.get("total_tokens", 0)
                    })
                    break  # Only take the first model data
    
    # Add PGN string if available
    if pgn_string:
        stats["pgn"] = pgn_string
    
    return stats


load_dotenv()

def display_store_game_video_and_stats(game_stats, log_dir="_logs"):
    # 1) Gather usage summaries
    white_summary = gather_usage_summary([game_stats["player_white"]])
    black_summary = gather_usage_summary([game_stats["player_black"]])

    # 2) Save results to file
    _save_game_to_file(game_stats, log_dir)

    # 3) Print outcome
    _print_game_outcome(game_stats, white_summary, black_summary)


def _save_game_to_file(game_stats, log_dir):
    if log_dir is None:
        return
        
    # Save game stats to JSON file
    log_filename = f"{log_dir}/{game_stats['time_started']}.json"
    if os.path.exists(log_filename):
        base, ext = os.path.splitext(log_filename)
        import time
        timestamp = int(time.time() * 1000)
        log_filename = f"{base}_{timestamp}{ext}"
    
    # Create a deep copy of game_stats to avoid modifying the original
    import copy
    game_stats_copy = copy.deepcopy(game_stats)
    
    # Round accumulated reply times to 3 decimal places
    game_stats_copy['player_white']['accumulated_reply_time_seconds'] = round(
        game_stats_copy['player_white']['accumulated_reply_time_seconds'], 3)
    game_stats_copy['player_black']['accumulated_reply_time_seconds'] = round(
        game_stats_copy['player_black']['accumulated_reply_time_seconds'], 3)
    
    with open(log_filename, "w") as log_file:
        json.dump(game_stats_copy, log_file, indent=4)
    
def _print_game_outcome(game_stats, white_summary, black_summary):
    print("\033[92m\nGAME OVER\n\033[0m")
    print(f"\033[92m{game_stats['winner']} wins due to {game_stats['reason']}.\033[0m")
    print(f"\033[92mNumber of moves made: {game_stats['number_of_moves']}\033[0m")
    print("\nWrong Moves (LLM asked to make illegal/impossible move):")
    print(f"Player White: {game_stats['player_white']['wrong_moves']}")
    print(f"Player Black: {game_stats['player_black']['wrong_moves']}")
    print("\nWrong Actions (LLM responded with non parseable message):")
    print(f"Player White: {game_stats['player_white']['wrong_actions']}")
    print(f"Player Black: {game_stats['player_black']['wrong_actions']}")
    print("\nMaterial Count:")
    print(f"Player White: {game_stats['material_count']['white']}")
    print(f"Player Black: {game_stats['material_count']['black']}")
    print("\nAccumulated Reply Time (seconds):")
    print(f"Player White: {game_stats['player_white']['accumulated_reply_time_seconds']:.3f}")
    print(f"Player Black: {game_stats['player_black']['accumulated_reply_time_seconds']:.3f}")
    if "pgn" in game_stats:
        print("\n\033[96mGame PGN:\033[0m")
        print(game_stats["pgn"])
    print("\nCosts per agent (white and black):\n")
    if white_summary:
        pprint(white_summary["usage_excluding_cached_inference"])
    if black_summary:
        pprint(black_summary["usage_excluding_cached_inference"])

def setup_console_logging(log_folder, filename="output.txt"):
    """
    Redirect console output to a file and optionally also print to the console.

    Args:
        log_folder (str): The folder where the log file will be saved.
        filename (str): The name of the log file. Defaults to "output.txt".
    """
    log_file_path = os.path.join(log_folder, filename)
    os.makedirs(log_folder, exist_ok=True)  # Ensure the log folder exists
    log_file = open(log_file_path, "w")

    # Regular expression to match ANSI escape codes
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

    # Redirect stdout and stderr to the log file
    class Tee:
        def __init__(self, *streams):
            self.streams = streams

        def write(self, data):
            # Write original data (with ANSI codes) to the console
            for stream in self.streams:
                if stream == log_file:
                    # Remove ANSI escape codes before writing to the log file
                    cleaned_data = ansi_escape.sub('', data)
                    stream.write(cleaned_data)
                else:
                    # Write original data (with ANSI codes) to the console
                    stream.write(data)
                stream.flush()

        def flush(self):
            for stream in self.streams:
                stream.flush()

    # Redirect stdout and stderr to both console and file
    sys.stdout = Tee(sys.__stdout__, log_file)
    sys.stderr = Tee(sys.__stderr__, log_file)