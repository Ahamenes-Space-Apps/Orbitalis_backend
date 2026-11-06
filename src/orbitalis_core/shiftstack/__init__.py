"""Trial motion vectors, shift-and-combine and score maps.

Purpose: Public surface for the pure shift-and-stack science module.
Inputs: None.
Outputs: Re-exported models, helpers, and search functions.
Called by: Research handlers and tests.
"""

from .combining import combine
from .errors import InvalidInputError, ShiftStackError, WorkBudgetExceededError
from .models import (
    CombinedResult,
    Frame,
    MotionVector,
    SearchResult,
    SearchResults,
    ShiftAndCombineResult,
    ShiftCombineResult,
    ShiftStackResult,
)
from .search import DEFAULT_WORK_BUDGET, search, shift_and_combine
from .shifting import shift_image

__all__ = [
    "DEFAULT_WORK_BUDGET",
    "CombinedResult",
    "Frame",
    "InvalidInputError",
    "MotionVector",
    "SearchResult",
    "SearchResults",
    "ShiftAndCombineResult",
    "ShiftCombineResult",
    "ShiftStackError",
    "ShiftStackResult",
    "WorkBudgetExceededError",
    "combine",
    "search",
    "shift_and_combine",
    "shift_image",
]
