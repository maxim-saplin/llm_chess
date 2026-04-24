"""Shared string-enum for game termination reasons.

Isolated into its own tiny module so lightweight consumers (e.g. log refiners,
offline analysis scripts) can read these constants without paying the ~3.5s
import cost of `llm_chess`, which transitively pulls in `autogen`, `matplotlib`,
`moviepy`, Google Cloud AI Platform, etc.

`llm_chess.TerminationReason` is re-exported from this module, so existing
callers that do `from llm_chess import TerminationReason` keep working
unchanged.
"""

from enum import Enum


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


__all__ = ["TerminationReason"]
