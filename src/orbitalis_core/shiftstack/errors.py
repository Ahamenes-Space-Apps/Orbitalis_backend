"""Exceptions for the shift-and-stack core module.

Purpose: Focused error types for invalid inputs and excessive computation.
Inputs: None.
Outputs: Exception classes.
Called by: orbitalis_core.shiftstack modules.
"""

from __future__ import annotations


class ShiftStackError(ValueError):
    """Base class for shift-and-stack input and computation errors."""


class InvalidInputError(ShiftStackError):
    """Raised when frames, motion vectors, or supporting arrays are invalid."""


class WorkBudgetExceededError(ShiftStackError):
    """Raised when a search would exceed its configured work budget."""
