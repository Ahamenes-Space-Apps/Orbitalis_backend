"""Image alignment onto a common grid.

Purpose: Public surface for reprojection helpers.
Inputs: None at import.
Outputs: Re-exported functions.
Called by: Pipeline, research handlers and tests.
"""

from .grid import to_common_grid

__all__ = ["to_common_grid"]
