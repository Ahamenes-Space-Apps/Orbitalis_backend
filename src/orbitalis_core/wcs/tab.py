"""WCS-WAVE binary-table parsing into a ``WaveTab`` lookup.

Purpose: Turn the SPHEREx WCS-WAVE FITS binary table (1 row, columns X, Y,
VALUES) into a validated rectilinear control-point grid.
Inputs: ``X``, ``Y`` and ``VALUES`` column arrays, or a BinTableHDU.
Outputs: ``WaveTab`` holding 1-based FITS pixel coordinates and per-point
wavelength/bandwidth in micrometres.
Called by: ``orbitalis_core.wcs.interpolate`` consumers (pipeline, research).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from orbitalis_core.errors import InvalidInputError


@dataclass(frozen=True)
class WaveTab:
    """Rectilinear WCS-WAVE control-point grid.

    ``x`` and ``y`` are the control-point pixel coordinates in the FITS
    1-based convention used by the table (verified against live IRSA data:
    X and Y span 1..2040 on a 2040x2040 detector). ``wavelength`` and
    ``bandwidth`` have shape ``(len(y), len(x))`` in micrometres; element
    ``[iy, ix]`` is the value at control point ``(x[ix], y[iy])``.
    """

    x: np.ndarray
    y: np.ndarray
    wavelength: np.ndarray
    bandwidth: np.ndarray

    @classmethod
    def from_columns(cls, x: Any, y: Any, values: Any) -> WaveTab:
        """Build a ``WaveTab`` from raw X, Y and VALUES column arrays.

        ``values`` must have shape ``(len(y), len(x), 2)`` — the ordering
        astropy produces for the FITS ``TDIM3 = '(2,11,11)'`` column — with
        the last axis ``(wavelength, bandwidth)`` in micrometres.
        """
        xs = cls._coords(x, "x")
        ys = cls._coords(y, "y")
        vals = np.asarray(values, dtype=np.float64)
        if vals.ndim != 3 or vals.shape[2] != 2:
            raise InvalidInputError(f"VALUES must have shape (len(y), len(x), 2), got {vals.shape}")
        if vals.shape[0] != ys.size or vals.shape[1] != xs.size:
            raise InvalidInputError(
                f"VALUES grid {vals.shape[:2]} does not match "
                f"x ({xs.size}) and y ({ys.size}) control points"
            )
        if not np.all(np.isfinite(vals)):
            raise InvalidInputError("VALUES contains non-finite entries")
        return cls(
            x=xs,
            y=ys,
            wavelength=vals[:, :, 0].copy(),
            bandwidth=vals[:, :, 1].copy(),
        )

    @classmethod
    def from_hdu(cls, hdu: Any) -> WaveTab:
        """Build a ``WaveTab`` from a WCS-WAVE binary-table HDU."""
        data = hdu.data
        try:
            x = np.asarray(data["X"][0])
            y = np.asarray(data["Y"][0])
            values = np.asarray(data["VALUES"][0])
        except (KeyError, IndexError, TypeError) as exc:
            raise InvalidInputError(
                "HDU is not a WCS-WAVE table (needs X, Y, VALUES columns)"
            ) from exc
        return cls.from_columns(x, y, values)

    @staticmethod
    def _coords(coords: Any, name: str) -> np.ndarray:
        arr = np.asarray(coords, dtype=np.float64)
        if arr.ndim != 1 or arr.size < 2:
            raise InvalidInputError(f"{name} control points must be a 1-D array of >= 2 values")
        if not np.all(np.isfinite(arr)):
            raise InvalidInputError(f"{name} control points contain non-finite values")
        if not np.all(np.diff(arr) > 0):
            raise InvalidInputError(f"{name} control points must be strictly increasing")
        return arr


__all__ = ["WaveTab"]
