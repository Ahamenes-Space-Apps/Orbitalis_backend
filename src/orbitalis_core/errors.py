"""Typed error hierarchy for the pure science library.

Purpose: Single ``CoreError`` base with per-failure subclasses carrying the
``ORB-CORE-*`` codes from SDD Appendix B, plus the all-NaN output guard that
SDD §6.1 requires of every core function.
Inputs: Exception messages; ``check_not_all_nan`` takes array-likes.
Outputs: Exception classes and ``check_not_all_nan``.
Called by: Every ``orbitalis_core`` submodule and, at the API boundary, the
single exception-to-HTTP mapper in ``orbitalis.errors``.
"""

from __future__ import annotations

from typing import Any, ClassVar

import numpy as np


class CoreError(Exception):
    """Base class for every failure raised inside ``orbitalis_core``.

    Core code never sees HTTP. Each concrete subclass carries an ``ORB-*``
    code in ``code``; the API layer maps codes to status codes in one place.
    A bare ``CoreError`` has no code and maps to ``ORB-SYS-001`` upstream.
    """

    code: ClassVar[str | None] = None


class InvalidInputError(CoreError):
    """Input data is invalid or corrupt (bad shape, dtype, out-of-range value).

    Maps to ``ORB-CORE-001``.
    """

    code: ClassVar[str] = "ORB-CORE-001"


class EmptyResultError(CoreError):
    """A computation produced no usable output (empty or all-NaN result).

    Maps to ``ORB-CORE-002``. Per SDD §6.1 an all-NaN output is an error,
    never a silent result.
    """

    code: ClassVar[str] = "ORB-CORE-002"


def check_not_all_nan(result: Any, *, name: str = "result") -> np.ndarray:
    """Return ``result`` as an array, raising ``EmptyResultError`` if unusable.

    Raises when the array has zero elements or, for inexact dtypes, every
    element is NaN. Integer and boolean arrays cannot contain NaN and are
    returned as-is (still subject to the empty check). The input is not
    modified.
    """
    arr = np.asarray(result)
    if arr.size == 0:
        raise EmptyResultError(f"{name} is empty")
    if np.issubdtype(arr.dtype, np.inexact) and bool(np.all(np.isnan(arr))):
        raise EmptyResultError(f"{name} is all NaN")
    return arr


__all__ = [
    "CoreError",
    "EmptyResultError",
    "InvalidInputError",
    "check_not_all_nan",
]
