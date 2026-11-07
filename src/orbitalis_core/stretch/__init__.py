"""Display stretch fitting and application.

Purpose: Public surface for the fixed stretch used in frame rendering.
Inputs: None at import.
Outputs: Re-exported functions, params and state types.
Called by: Pipeline PNG rendering, research handlers and tests.
"""

from .stretch import (
    DEFAULT_HI_PERCENTILE,
    DEFAULT_LO_PERCENTILE,
    DEFAULT_SOFTNESS,
    StretchParams,
    StretchState,
    apply_stretch,
    fit_stretch,
)

__all__ = [
    "DEFAULT_HI_PERCENTILE",
    "DEFAULT_LO_PERCENTILE",
    "DEFAULT_SOFTNESS",
    "StretchParams",
    "StretchState",
    "apply_stretch",
    "fit_stretch",
]
