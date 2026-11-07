"""Image stacking and difference imaging.

Purpose: Public surface for sigma-clipped combination and frame differencing.
Inputs: None at import.
Outputs: Re-exported functions and result types.
Called by: Pipeline group combine, research handlers and tests.
"""

from .combine import CombineResult, combine, difference

__all__ = ["CombineResult", "combine", "difference"]
