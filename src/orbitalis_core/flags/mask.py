"""SPHEREx pixel flag decoding, masking, and mask application.

Purpose: Decode SPHEREx FLAGS-layer bitmasks, build the default bad-pixel mask,
and apply that mask to image data.
Inputs: NumPy arrays (or array-likes) of integer flag values and image arrays.
Outputs: Boolean arrays, decoded flag mappings, and floating-point image arrays.
Called by: Core processing pipeline, store/frame preparation, and tests.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from .bits import FLAG_BITS, FLAG_FULLSAMPLE, FLAG_SOURCE

_KNOWN_BITS: int = 0
for _bit in FLAG_BITS.values():
    _KNOWN_BITS |= _bit

_ALLOWED_BITS: int = FLAG_SOURCE | FLAG_FULLSAMPLE


def _as_integer_array(flags_array: Any) -> np.ndarray:
    if flags_array is None or isinstance(flags_array, (str, bytes, bytearray)):
        raise TypeError(
            f"flags_array must be an array-like of integers, not {type(flags_array).__name__}"
        )
    try:
        arr = np.asarray(flags_array)
    except (TypeError, ValueError) as exc:
        raise TypeError("flags_array must be an array-like of integers") from exc
    if arr.dtype == object:
        raise TypeError("flags_array must be an array-like of integers")
    if not np.issubdtype(arr.dtype, np.integer):
        raise ValueError("flags_array must have an integer dtype")
    if arr.size and np.any(arr < 0):
        raise ValueError("flag values must be non-negative")
    # Flag constants use bits up to 29. Narrow integer dtypes can overflow during
    # bitwise operations, so normalize to a wide unsigned type. astype() returns
    # a new array and never mutates the caller's input.
    return arr.astype(np.uint64)


def decode(flags_array: Any) -> dict[str, np.ndarray]:
    """Decode a flag array into a mapping of flag name -> Boolean array.

    Each value is a Boolean array of the same shape as ``flags_array``, with
    ``True`` where that flag bit is set. An ``"UNKNOWN"`` entry is ``True``
    where any bit outside the Table 16 definitions is set. The input is not
    modified.
    """
    arr = _as_integer_array(flags_array)
    result: dict[str, np.ndarray] = {}
    for name, bit in FLAG_BITS.items():
        result[name] = np.asarray((arr & bit) != 0, dtype=bool)
    result["UNKNOWN"] = np.asarray((arr & _KNOWN_BITS) != arr, dtype=bool)
    return result


def default_mask(flags_array: Any) -> np.ndarray:
    """Return the default bad-pixel mask.

    ``True`` means the pixel is masked/bad and should become NaN in scientific
    data; ``False`` means valid. Every flag bit except ``SOURCE`` (bit 21) and
    ``FULLSAMPLE`` (bit 12) causes masking, including unrecognized bits.
    """
    arr = _as_integer_array(flags_array)
    return np.asarray((arr & _ALLOWED_BITS) != arr, dtype=bool)


def apply_default_mask(image: Any, flags: Any) -> np.ndarray:
    """Apply the default flag mask to an image, returning a new float array.

    Pixels marked as masked become ``NaN`` (never zero). Unmasked values are
    preserved. The original image is not modified. ``image`` and ``flags`` must
    have compatible (broadcastable) shapes.
    """
    image_arr = np.asarray(image)
    if not np.issubdtype(image_arr.dtype, np.number):
        raise ValueError("image must be a numeric array")
    flags_arr = _as_integer_array(flags)
    try:
        out_shape = np.broadcast_shapes(image_arr.shape, flags_arr.shape)
    except ValueError as exc:
        raise ValueError("image and flags must have compatible shapes") from exc
    mask = np.broadcast_to(default_mask(flags_arr), out_shape)
    image_bc = np.broadcast_to(image_arr, out_shape)
    result = image_bc.astype(np.float64, copy=True)
    result[mask] = np.nan
    return result


__all__ = ["apply_default_mask", "decode", "default_mask"]
