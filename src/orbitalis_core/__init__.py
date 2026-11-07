"""Public surface of the pure science library.

Purpose: Re-export the shared ``CoreError`` hierarchy (FR-CORE-07) so every
``orbitalis_core`` submodule raises the same typed errors. Submodule
functions are imported from their own packages, not from here.
Inputs: None.
Outputs: Re-exported exception classes and the all-NaN guard.
Called by: All ``orbitalis_core`` submodules and downstream application code.
"""

from .errors import (
    CoreError,
    EmptyResultError,
    InvalidInputError,
    check_not_all_nan,
)

__all__ = [
    "CoreError",
    "EmptyResultError",
    "InvalidInputError",
    "check_not_all_nan",
]
