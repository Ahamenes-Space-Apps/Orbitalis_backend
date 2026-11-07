"""Reprojection of frames onto a common sky grid.

Purpose: ``to_common_grid`` resamples one frame onto the field's shared
tangent-plane grid. Imaging stays in MJy/sr (surface brightness), so
interpolation conserves the quantity we combine — see SDD D-03.
Inputs: A 2-D float array in MJy/sr (NaN = masked), its celestial astropy
WCS, the target celestial WCS, and the output ``(rows, cols)`` shape.
Outputs: ``(array, footprint)`` — the resampled MJy/sr array and a boolean
footprint of output pixels covered by the input. Inputs are never mutated.
Called by: ``orbitalis_core.align`` consumers — the field pipeline and tests.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from reproject import reproject_interp

from orbitalis_core.errors import InvalidInputError, check_not_all_nan


def _check_celestial(wcs: Any, name: str) -> None:
    try:
        ctype = [str(c) for c in np.atleast_1d(wcs.wcs.ctype)]
    except AttributeError as exc:
        raise InvalidInputError(f"{name} must be an astropy WCS, got {type(wcs).__name__}") from exc
    if len(ctype) < 2 or not ctype[0].startswith("RA") or not ctype[1].startswith("DEC"):
        raise InvalidInputError(f"{name} must be a celestial RA/DEC WCS, got CTYPE={ctype}")


def to_common_grid(
    data: Any,
    wcs: Any,
    target_wcs: Any,
    shape: tuple[int, int],
) -> tuple[np.ndarray, np.ndarray]:
    """Reproject ``data`` onto ``target_wcs`` with shape ``(rows, cols)``.

    ``data`` must be a 2-D numeric array in MJy/sr; NaN marks invalid pixels
    and propagates through the interpolation. Returns the resampled array
    (float64, NaN where uncovered) and ``footprint``, the boolean coverage
    mask reproject reports. Mask dilation for conservative footprints is the
    caller's job (DS spec §7). An all-NaN result raises
    ``EmptyResultError`` (SDD §6.1).
    """
    arr = np.asarray(data)
    if arr.ndim != 2 or arr.dtype.kind not in "fiu":
        raise InvalidInputError("data must be a 2-D numeric MJy/sr array")
    if (
        not isinstance(shape, tuple)
        or len(shape) != 2
        or any(not isinstance(n, int) or n < 1 for n in shape)
    ):
        raise InvalidInputError(
            f"shape must be a (rows, cols) tuple of positive ints, got {shape!r}"
        )
    _check_celestial(wcs, "wcs")
    _check_celestial(target_wcs, "target_wcs")

    out, footprint = reproject_interp(
        (arr.astype(np.float64, copy=False), wcs),
        target_wcs,
        tuple(shape),
        order="bilinear",
        return_footprint=True,
    )
    out = check_not_all_nan(np.asarray(out, dtype=np.float64), name="reprojected frame")
    return out, np.asarray(footprint, dtype=bool)


__all__ = ["to_common_grid"]
