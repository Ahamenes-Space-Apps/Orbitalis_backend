"""Image shifting helpers for shift-and-stack.

Purpose: Sub-pixel shifting of aligned images with explicit boundary handling.
Inputs: Two-dimensional NumPy arrays and shift amounts in pixels.
Outputs: Shifted floating-point arrays.
Called by: orbitalis_core.shiftstack.search and callers.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy import ndimage

from .errors import InvalidInputError


def _as_image_array(image: Any) -> np.ndarray:
    arr = np.asarray(image)
    if arr.ndim != 2:
        raise InvalidInputError("image must be a two-dimensional array")
    if np.iscomplexobj(arr) or arr.dtype.kind == "c":
        raise InvalidInputError("image must be real-valued")
    if not np.issubdtype(arr.dtype, np.number):
        raise InvalidInputError("image must be a numeric array")
    if not np.all(np.isfinite(arr) | np.isnan(arr)):
        raise InvalidInputError("image may contain only finite values or NaN")
    return np.array(arr, dtype=np.float64, copy=True)


def shift_image(
    image: Any,
    shift_y: float,
    shift_x: float,
    *,
    order: int = 1,
) -> np.ndarray:
    """Shift an image by ``(shift_y, shift_x)`` pixels.

    The shift is applied with SciPy's spline interpolation. ``mode='constant'``
    with a NaN fill value is used, so pixels shifted outside the image become
    NaN instead of wrapping around. NaN input pixels may propagate to output
    pixels whose interpolation footprint includes them. This conservatively
    preserves masked regions. ``order=1`` gives bilinear interpolation for
    sub-pixel shifts.
    """
    arr = _as_image_array(image)
    try:
        sy = float(shift_y)
        sx = float(shift_x)
    except (TypeError, ValueError) as exc:
        raise InvalidInputError("shift amounts must be finite numbers") from exc
    if not np.isfinite(sy) or not np.isfinite(sx):
        raise InvalidInputError("shift amounts must be finite numbers")
    if order not in (0, 1, 2, 3, 4, 5):
        raise InvalidInputError("interpolation order must be between 0 and 5")
    shifted = ndimage.shift(
        arr,
        shift=(sy, sx),
        order=order,
        mode="constant",
        cval=np.nan,
        prefilter=order > 1,
    )
    return np.asarray(shifted, dtype=np.float64)


__all__ = ["shift_image"]
