"""Fixed display stretch for frame rendering.

Purpose: Fit a normalization curve once from the first N frames, then apply
it unchanged to every later frame so scrubbing does not flicker (SDD §9.4,
must-not-regress #5, ``ORB_STRETCH_FIX_N``).
Inputs: 2-D MJy/sr arrays with NaN masks; percentile bounds and an asinh
softness.
Outputs: ``StretchParams`` and stretched arrays scaled to [0, 1].
Called by: ``orbitalis_core.stretch`` consumers — the pipeline PNG renderer
and tests.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

from orbitalis_core.errors import EmptyResultError, InvalidInputError, check_not_all_nan

# PROVISIONAL(ML): percentile bounds and asinh softness are display choices,
# not science values; tune against real frames at G1 if the UX needs it.
DEFAULT_LO_PERCENTILE = 1.0
DEFAULT_HI_PERCENTILE = 99.9
DEFAULT_SOFTNESS = 10.0


@dataclass(frozen=True)
class StretchParams:
    """Frozen stretch parameters.

    ``lo``/``hi`` are data values (MJy/sr) mapped to output 0 and 1.
    ``softness`` controls the asinh curve: larger values approach a linear
    stretch, smaller values lift faint structure. ``n_pixels`` records how
    many finite pixels the fit used.
    """

    lo: float
    hi: float
    softness: float
    lo_percentile: float
    hi_percentile: float
    n_pixels: int


def _finite_values(arrays: Sequence[Any]) -> np.ndarray:
    parts = []
    for arr in arrays:
        a = np.asarray(arr)
        if a.ndim != 2 or a.dtype.kind not in "fiu":
            raise InvalidInputError("stretch inputs must be 2-D numeric arrays")
        parts.append(a[np.isfinite(a)])
    if not parts:
        raise InvalidInputError("fit_stretch needs at least one array")
    return np.concatenate(parts)


def fit_stretch(
    arrays: Sequence[Any],
    *,
    lo_percentile: float = DEFAULT_LO_PERCENTILE,
    hi_percentile: float = DEFAULT_HI_PERCENTILE,
    softness: float = DEFAULT_SOFTNESS,
) -> StretchParams:
    """Fit stretch parameters from one or more frames.

    Deterministic for the same inputs: percentiles are exact numpy
    computations over the finite pixel values. Raises ``EmptyResultError``
    if every input pixel is masked and ``InvalidInputError`` if the data
    range is degenerate (``hi <= lo``, e.g. a constant field) or arguments
    are invalid.
    """
    if not (0.0 <= lo_percentile < hi_percentile <= 100.0):
        raise InvalidInputError("need 0 <= lo_percentile < hi_percentile <= 100")
    if not np.isfinite(softness) or softness <= 0:
        raise InvalidInputError("softness must be a positive finite number")
    values = _finite_values(arrays)
    if values.size == 0:
        raise EmptyResultError("no finite pixels to fit the stretch")
    lo, hi = np.percentile(values, [lo_percentile, hi_percentile])
    if not hi > lo:
        raise InvalidInputError("degenerate stretch: hi <= lo (constant field?)")
    return StretchParams(
        lo=float(lo),
        hi=float(hi),
        softness=float(softness),
        lo_percentile=float(lo_percentile),
        hi_percentile=float(hi_percentile),
        n_pixels=int(values.size),
    )


def apply_stretch(array: Any, params: StretchParams) -> np.ndarray:
    """Apply frozen stretch parameters, returning a new [0, 1] float array.

    ``x == lo`` maps to 0, ``x == hi`` maps to 1; values outside are clipped.
    NaN stays NaN. An all-NaN result raises ``EmptyResultError``.
    """
    arr = np.asarray(array)
    if arr.ndim != 2 or arr.dtype.kind not in "fiu":
        raise InvalidInputError("array must be a 2-D numeric array")
    if not isinstance(params, StretchParams):
        raise InvalidInputError("params must be a StretchParams")
    t = (arr.astype(np.float64, copy=False) - params.lo) / (params.hi - params.lo)
    out = np.arcsinh(params.softness * t) / np.arcsinh(params.softness)
    out = np.clip(out, 0.0, 1.0)
    out = np.where(np.isfinite(arr), out, np.nan)
    return check_not_all_nan(out, name="stretched image")


class StretchState:
    """Freeze-after-N-frames stretch bookkeeping (must-not-regress #5).

    Feed every frame to ``observe`` in arrival order. Until ``fix_n`` frames
    have been seen it returns ``None``; on the ``fix_n``-th frame it fits the
    parameters once and returns them; every later call returns the same
    frozen ``StretchParams`` — later frames can never change them.
    """

    def __init__(self, fix_n: int = 8, **fit_kwargs: Any) -> None:
        if not isinstance(fix_n, int) or fix_n < 1:
            raise InvalidInputError("fix_n must be a positive integer")
        self._fix_n = fix_n
        self._fit_kwargs = fit_kwargs
        self._buffer: list[np.ndarray] = []
        self._params: StretchParams | None = None

    def observe(self, array: Any) -> StretchParams | None:
        """Record a frame; return frozen params once ``fix_n`` is reached."""
        if self._params is not None:
            return self._params
        arr = np.asarray(array)
        if arr.ndim != 2 or arr.dtype.kind not in "fiu":
            raise InvalidInputError("stretch inputs must be 2-D numeric arrays")
        self._buffer.append(arr)
        if len(self._buffer) < self._fix_n:
            return None
        self._params = fit_stretch(self._buffer, **self._fit_kwargs)
        self._buffer.clear()
        return self._params

    @property
    def params(self) -> StretchParams | None:
        """The frozen parameters, or ``None`` before the freeze point."""
        return self._params

    @property
    def is_frozen(self) -> bool:
        return self._params is not None


__all__ = [
    "DEFAULT_HI_PERCENTILE",
    "DEFAULT_LO_PERCENTILE",
    "DEFAULT_SOFTNESS",
    "StretchParams",
    "StretchState",
    "apply_stretch",
    "fit_stretch",
]
