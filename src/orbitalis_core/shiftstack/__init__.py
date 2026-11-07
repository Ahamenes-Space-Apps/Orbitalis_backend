"""Trial motion vectors, shift-and-combine and score maps.

Purpose: Public surface for the pure shift-and-stack science module.
Inputs: None.
Outputs: Re-exported models, helpers, and search functions.
Called by: Research handlers and tests.
"""

from .combining import combine
from .errors import InvalidInputError, ShiftStackError, WorkBudgetExceededError
from .models import Frame, MotionVector, SearchResult, ShiftCombineResult
from .search import DEFAULT_WORK_BUDGET, search, shift_and_combine
from .shifting import SUPPORT_THRESHOLD, shift_image, shift_variance

__all__ = [
    "DEFAULT_WORK_BUDGET",
    "SUPPORT_THRESHOLD",
    "Frame",
    "InvalidInputError",
    "MotionVector",
    "SearchResult",
    "ShiftCombineResult",
    "ShiftStackError",
    "WorkBudgetExceededError",
    "combine",
    "search",
    "shift_and_combine",
    "shift_image",
    "shift_variance",
]
