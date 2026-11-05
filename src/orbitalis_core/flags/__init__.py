"""SPHEREx pixel flag decoding and default masking.

Purpose: Decode SPHEREx FLAGS-layer bitmasks into per-flag Boolean arrays and build
the default bad-pixel mask used by the core pipeline.
Inputs: A NumPy array (or array-like) of integer pixel flag values.
Outputs: ``decode`` returns ``dict[str, np.ndarray]`` of Boolean arrays; ``default_mask``
    returns a Boolean array where ``True`` means the pixel is masked/bad.
Called by: Core processing pipeline, store/frame preparation, and tests.
"""

from __future__ import annotations

from typing import Any

import numpy as np

# Flag definitions taken from the Data & Science Specification, Table 16
# (Explanatory Supplement v2.0, pipeline R7). Bit n has value 2**n.
FLAG_TRANSIENT = 1 << 0
FLAG_OVERFLOW = 1 << 1
FLAG_SUR_ERROR = 1 << 2
FLAG_NONFUNC = 1 << 6
FLAG_DICHROIC = 1 << 7
FLAG_MISSING_DATA = 1 << 9
FLAG_HOT = 1 << 10
FLAG_COLD = 1 << 11
FLAG_FULLSAMPLE = 1 << 12
FLAG_PHANMISS = 1 << 14
FLAG_NONLINEAR = 1 << 15
FLAG_PERSIST = 1 << 17
FLAG_OUTLIER = 1 << 19
FLAG_CROSSTALK = 1 << 20
FLAG_SOURCE = 1 << 21
FLAG_GHOST = 1 << 22
FLAG_GHOST_FPA = 1 << 23
FLAG_GHOST_EXT = 1 << 24
FLAG_STREAK = 1 << 25
FLAG_BLOOM = 1 << 26
FLAG_SNOWBALL = 1 << 27
FLAG_HALO = 1 << 28
FLAG_SATELLITE_HALO = 1 << 29

# Ordered to mirror Table 16.
_FLAG_BITS: dict[str, int] = {
    "TRANSIENT": FLAG_TRANSIENT,
    "OVERFLOW": FLAG_OVERFLOW,
    "SUR_ERROR": FLAG_SUR_ERROR,
    "NONFUNC": FLAG_NONFUNC,
    "DICHROIC": FLAG_DICHROIC,
    "MISSING_DATA": FLAG_MISSING_DATA,
    "HOT": FLAG_HOT,
    "COLD": FLAG_COLD,
    "FULLSAMPLE": FLAG_FULLSAMPLE,
    "PHANMISS": FLAG_PHANMISS,
    "NONLINEAR": FLAG_NONLINEAR,
    "PERSIST": FLAG_PERSIST,
    "OUTLIER": FLAG_OUTLIER,
    "CROSSTALK": FLAG_CROSSTALK,
    "SOURCE": FLAG_SOURCE,
    "GHOST": FLAG_GHOST,
    "GHOST_FPA": FLAG_GHOST_FPA,
    "GHOST_EXT": FLAG_GHOST_EXT,
    "STREAK": FLAG_STREAK,
    "BLOOM": FLAG_BLOOM,
    "SNOWBALL": FLAG_SNOWBALL,
    "HALO": FLAG_HALO,
    "SATELLITE_HALO": FLAG_SATELLITE_HALO,
}

_KNOWN_BITS: int = 0
for _bit in _FLAG_BITS.values():
    _KNOWN_BITS |= _bit

# Pixels are masked for everything except SOURCE and FULLSAMPLE.
_ALLOWED_BITS: int = FLAG_SOURCE | FLAG_FULLSAMPLE


def _as_integer_array(flags_array: Any) -> np.ndarray:
    if flags_array is None or isinstance(flags_array, (str, bytes, bytearray)):
        raise TypeError("flags_array must be an array-like of integers, not "
                        f"{type(flags_array).__name__}")
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
    for name, bit in _FLAG_BITS.items():
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


__all__ = [
    "decode",
    "default_mask",
    "FLAG_SOURCE",
    "FLAG_FULLSAMPLE",
] + [f"FLAG_{name}" for name in _FLAG_BITS if name not in ("SOURCE", "FULLSAMPLE")]
