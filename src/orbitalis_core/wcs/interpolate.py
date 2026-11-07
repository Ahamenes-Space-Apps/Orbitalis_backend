"""Bilinear interpolation of the WCS-WAVE lookup table.

Purpose: Evaluate per-pixel wavelength (and bandwidth) in micrometres from a
``WaveTab``, using our own bilinear interpolation — astropy is not used for
the spectral axis (SDD section 6.1, DS spec "Wavelength per pixel").
Inputs: A ``WaveTab`` plus either an astropy spectral (``key="W"``) WCS or a
FITS header carrying the ``*W`` linear keywords; pixel coordinates are
0-based array indices (x = column, y = row).
Outputs: Scalar floats from ``*_at`` and float64 arrays from ``*_map``.
Called by: ``orbitalis_core.wcs`` consumers — pipeline frame preparation and
tests.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from orbitalis_core.errors import InvalidInputError

from .tab import WaveTab


def _linear_params(src: Any) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Extract (crpix, crval, cdelt, pc) of the spectral linear transform.

    ``src`` is either an astropy ``WCS`` built with ``key="W"`` (its ``.wcs``
    struct already holds the linear part; the lookup itself is ours) or a
    FITS header, in which case the ``*W``-suffixed keywords are read.
    Pixel coordinates are 0-based array indices; ``crpix`` keeps its FITS
    header value, matching the convention verified against live IRSA data.
    """
    if hasattr(src, "wcs"):
        w = src.wcs
        ctype = [str(c) for c in np.atleast_1d(w.ctype)]
        if not any("WAVE-TAB" in c for c in ctype):
            raise InvalidInputError(
                "WCS object is not the spectral WAVE-TAB WCS "
                f'(CTYPE={ctype}); pass key="W" or the IMAGE header'
            )
        crpix = np.asarray(w.crpix, dtype=np.float64)
        crval = np.asarray(w.crval, dtype=np.float64)
        cdelt = np.ones(2) if w.cdelt is None else np.asarray(w.cdelt, dtype=np.float64)
        pc = np.eye(2) if w.pc is None else np.asarray(w.pc, dtype=np.float64).reshape(2, 2)
        return crpix, crval, cdelt, pc

    get = src.get
    try:
        crpix = np.array([get("CRPIX1W"), get("CRPIX2W")], dtype=np.float64)
        crval = np.array([get("CRVAL1W"), get("CRVAL2W")], dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise InvalidInputError("header lacks CRPIXnW/CRVALnW spectral WCS keywords") from exc
    if np.any(np.isnan(crpix)) or np.any(np.isnan(crval)):
        raise InvalidInputError("header lacks CRPIXnW/CRVALnW spectral WCS keywords")
    cdelt = np.array([get("CDELT1W", 1.0), get("CDELT2W", 1.0)], dtype=np.float64)
    pc = np.eye(2)
    for i in (0, 1):
        for j in (0, 1):
            key = f"PC{i + 1}_{j + 1}W"
            if get(key) is not None:
                pc[i, j] = get(key)
    return crpix, crval, cdelt, pc


def _table_coords(src: Any, x: Any, y: Any) -> tuple[np.ndarray, np.ndarray]:
    """Map 0-based pixel coords (x=col, y=row) to table pixel coords."""
    crpix, crval, cdelt, pc = _linear_params(src)
    px = np.asarray(x, dtype=np.float64)
    py = np.asarray(y, dtype=np.float64)
    dx = px - crpix[0]
    dy = py - crpix[1]
    qx = crval[0] + pc[0, 0] * cdelt[0] * dx + pc[0, 1] * cdelt[1] * dy
    qy = crval[1] + pc[1, 0] * cdelt[0] * dx + pc[1, 1] * cdelt[1] * dy
    return qx, qy


def _interp2(tab: WaveTab, field: str, qx: Any, qy: Any) -> tuple[np.ndarray, np.ndarray]:
    """Bilinear interpolation of ``field``; returns (values, inside_mask)."""
    grid = getattr(tab, field)
    qx = np.asarray(qx, dtype=np.float64)
    qy = np.asarray(qy, dtype=np.float64)
    # side="right" puts an exact left-edge node inside cell 0 with t=0; the
    # inside mask below then admits both edges inclusive.
    ix = np.searchsorted(tab.x, qx, side="right") - 1
    iy = np.searchsorted(tab.y, qy, side="right") - 1
    inside = (qx >= tab.x[0]) & (qx <= tab.x[-1]) & (qy >= tab.y[0]) & (qy <= tab.y[-1])
    ix_c = np.clip(ix, 0, tab.x.size - 2)
    iy_c = np.clip(iy, 0, tab.y.size - 2)
    x0 = tab.x[ix_c]
    x1 = tab.x[ix_c + 1]
    y0 = tab.y[iy_c]
    y1 = tab.y[iy_c + 1]
    tx = np.divide(qx - x0, x1 - x0, out=np.full_like(qx, np.nan), where=x1 != x0)
    ty = np.divide(qy - y0, y1 - y0, out=np.full_like(qy, np.nan), where=y1 != y0)
    v00 = grid[iy_c, ix_c]
    v10 = grid[iy_c, ix_c + 1]
    v01 = grid[iy_c + 1, ix_c]
    v11 = grid[iy_c + 1, ix_c + 1]
    vals = (1 - tx) * (1 - ty) * v00 + tx * (1 - ty) * v10 + (1 - tx) * ty * v01 + tx * ty * v11
    return vals, inside


def _at(src: Any, tab: WaveTab, field: str, x: float, y: float) -> float:
    qx, qy = _table_coords(src, x, y)
    vals, inside = _interp2(tab, field, qx, qy)
    if not bool(np.all(inside)):
        raise InvalidInputError(
            f"pixel ({x}, {y}) maps to table coordinate outside the WCS-WAVE grid"
        )
    return float(np.asarray(vals))


def _map(src: Any, tab: WaveTab, field: str, shape: tuple[int, int]) -> np.ndarray:
    rows = np.arange(shape[0], dtype=np.float64)
    cols = np.arange(shape[1], dtype=np.float64)
    px, py = np.meshgrid(cols, rows)  # px[x], py[y] -> index [row, col]
    qx, qy = _table_coords(src, px, py)
    vals, inside = _interp2(tab, field, qx, qy)
    return np.where(inside, vals, np.nan)


def wavelength_at(header_or_wcs: Any, tab: WaveTab, x: float, y: float) -> float:
    """Wavelength in micrometres at pixel (x, y); raises if outside the table."""
    return _at(header_or_wcs, tab, "wavelength", x, y)


def bandwidth_at(header_or_wcs: Any, tab: WaveTab, x: float, y: float) -> float:
    """Bandwidth in micrometres at pixel (x, y); raises if outside the table."""
    return _at(header_or_wcs, tab, "bandwidth", x, y)


def wavelength_map(header_or_wcs: Any, tab: WaveTab, shape: tuple[int, int]) -> np.ndarray:
    """Wavelength map in micrometres with shape ``(rows, cols)``.

    Pixels outside the WCS-WAVE grid are NaN, never extrapolated.
    """
    return _map(header_or_wcs, tab, "wavelength", shape)


def bandwidth_map(header_or_wcs: Any, tab: WaveTab, shape: tuple[int, int]) -> np.ndarray:
    """Bandwidth map in micrometres with shape ``(rows, cols)``; NaN outside."""
    return _map(header_or_wcs, tab, "bandwidth", shape)


__all__ = [
    "bandwidth_at",
    "bandwidth_map",
    "wavelength_at",
    "wavelength_map",
]
