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

SUPPORT_THRESHOLD = 0.99


def _as_image_array(image: Any) -> np.ndarray:
    if image is None:
        raise InvalidInputError("image must be a two-dimensional array")
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


def _as_variance_array(variance: Any) -> np.ndarray:
    arr = _as_image_array(variance)
    if np.any(np.isfinite(arr) & (arr < 0.0)):
        raise InvalidInputError("variance must be non-negative")
    return arr


def _shift_image_array(arr: np.ndarray, shift_y: float, shift_x: float) -> np.ndarray:
    """Shift an already validated float64 image array."""
    valid = np.isfinite(arr)
    values = np.where(valid, arr, 0.0)

    shifted_values = ndimage.shift(
        values,
        shift=(shift_y, shift_x),
        order=1,
        mode="constant",
        cval=0.0,
        prefilter=False,
    )
    shifted_validity = ndimage.shift(
        valid,
        shift=(shift_y, shift_x),
        order=0,
        mode="constant",
        cval=False,
        prefilter=False,
    )
    support = ndimage.shift(
        valid.astype(np.float64),
        shift=(shift_y, shift_x),
        order=1,
        mode="constant",
        cval=0.0,
        prefilter=False,
    )

    with np.errstate(divide="ignore", invalid="ignore"):
        normalized = shifted_values / np.where(support > 0.0, support, 1.0)
    result = np.where(
        shifted_validity & (support >= SUPPORT_THRESHOLD),
        normalized,
        np.nan,
    )
    return np.asarray(result, dtype=np.float64)


def _shift_variance_array(arr: np.ndarray, shift_y: float, shift_x: float) -> np.ndarray:
    """Shift an already validated float64 variance array."""
    valid = np.isfinite(arr)
    values = np.where(valid, arr, 0.0)

    height, width = arr.shape
    src_y = np.arange(height, dtype=np.float64)[:, None] - shift_y
    src_x = np.arange(width, dtype=np.float64)[None, :] - shift_x
    y0 = np.floor(src_y).astype(np.int64)
    x0 = np.floor(src_x).astype(np.int64)
    dy = src_y - y0
    dx = src_x - x0

    variance_sum = np.zeros((height, width), dtype=np.float64)
    support = np.zeros((height, width), dtype=np.float64)

    for iy in (0, 1):
        wy = (1.0 - dy) if iy == 0 else dy
        for ix in (0, 1):
            wx = (1.0 - dx) if ix == 0 else dx
            weight = wy * wx
            yy = y0 + iy
            xx = x0 + ix
            in_bounds = (yy >= 0) & (yy < height) & (xx >= 0) & (xx < width)
            yy_safe = np.clip(yy, 0, height - 1)
            xx_safe = np.clip(xx, 0, width - 1)
            neighbor_valid = valid[yy_safe, xx_safe] & in_bounds
            neighbor_variance = values[yy_safe, xx_safe]
            contribution = np.where(neighbor_valid, weight, 0.0)
            support = support + contribution
            variance_sum = variance_sum + np.where(
                neighbor_valid, (weight * weight) * neighbor_variance, 0.0
            )

    shifted_validity = ndimage.shift(
        valid,
        shift=(shift_y, shift_x),
        order=0,
        mode="constant",
        cval=False,
        prefilter=False,
    )
    scipy_support = ndimage.shift(
        valid.astype(np.float64),
        shift=(shift_y, shift_x),
        order=1,
        mode="constant",
        cval=0.0,
        prefilter=False,
    )

    with np.errstate(divide="ignore", invalid="ignore"):
        normalized_variance = variance_sum / np.where(support > 0.0, support * support, 1.0)
    result = np.where(
        shifted_validity & (scipy_support >= SUPPORT_THRESHOLD),
        normalized_variance,
        np.nan,
    )
    return np.asarray(result, dtype=np.float64)


def shift_image(
    image: Any,
    shift_y: float,
    shift_x: float,
) -> np.ndarray:
    """Shift an image by ``(shift_y, shift_x)`` pixels.

    Values and validity are shifted separately. The validity mask uses
    nearest-neighbour (order 0) shifting, while fractional support uses
    bilinear (order 1) shifting. The shifted values are normalized by the
    support. Pixels are set to NaN where the shifted validity mask is invalid or
    support is below ``SUPPORT_THRESHOLD``.
    """
    arr = _as_image_array(image)
    try:
        sy = float(shift_y)
        sx = float(shift_x)
    except (TypeError, ValueError) as exc:
        raise InvalidInputError("shift amounts must be finite numbers") from exc
    if not np.isfinite(sy) or not np.isfinite(sx):
        raise InvalidInputError("shift amounts must be finite numbers")

    return _shift_image_array(arr, sy, sx)


def shift_variance(
    variance: Any,
    shift_y: float,
    shift_x: float,
) -> np.ndarray:
    """Shift a variance array using squared normalized bilinear weights.

    Finite, non-negative input variances contribute. The output is

        V_out = sum((w_i / S)^2 * V_i)

    where ``w_i`` are bilinear weights, ``S`` is the sum of valid weights, and
    ``V_i`` are input variances. The same validity and support rules as
    ``shift_image`` are applied.
    """
    arr = _as_variance_array(variance)
    try:
        sy = float(shift_y)
        sx = float(shift_x)
    except (TypeError, ValueError) as exc:
        raise InvalidInputError("shift amounts must be finite numbers") from exc
    if not np.isfinite(sy) or not np.isfinite(sx):
        raise InvalidInputError("shift amounts must be finite numbers")

    return _shift_variance_array(arr, sy, sx)


__all__ = ["SUPPORT_THRESHOLD", "shift_image", "shift_variance"]
