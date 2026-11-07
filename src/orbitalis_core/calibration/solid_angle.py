"""Per-pixel solid angle computed from the spatial WCS.

Purpose: Solid-angle (sr) per pixel for flux-density conversion. Used only
where surface brightness meets flux — spectrum extraction and injection —
never in the imaging path, which stays in MJy/sr (SDD D-03).
Inputs: An astropy celestial WCS (RA/DEC TAN-SIP) and a ``(rows, cols)``
shape. Pixel corners, not a constant pixel scale, set each value.
Outputs: float64 array of steradians per pixel; NaN where the WCS cannot
place a corner. All-NaN output raises ``EmptyResultError``.
Called by: ``orbitalis_core.calibration`` consumers — spectrum extraction,
injection, tests.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from orbitalis_core.errors import InvalidInputError, check_not_all_nan


def _unit_vectors(lon_rad: np.ndarray, lat_rad: np.ndarray) -> np.ndarray:
    """Return unit-sphere vectors with shape ``lon.shape + (3,)``."""
    cos_lat = np.cos(lat_rad)
    return np.stack(
        [
            cos_lat * np.cos(lon_rad),
            cos_lat * np.sin(lon_rad),
            np.sin(lat_rad),
        ],
        axis=-1,
    )


def _triangle_area(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> np.ndarray:
    """Solid angle of the spherical triangle (a, b, c) in steradians.

    Van Oosterom-Strackee formula; vectorised over leading axes. Sign follows
    vertex order, so callers take the absolute value per pixel quad.
    """
    num = np.abs(np.sum(a * np.cross(b, c), axis=-1))
    den = 1.0 + np.sum(a * b, axis=-1) + np.sum(b * c, axis=-1) + np.sum(c * a, axis=-1)
    return 2.0 * np.arctan2(num, den)


def solid_angle_map(wcs: Any, shape: tuple[int, int]) -> np.ndarray:
    """Per-pixel solid angle in steradians for the given image shape.

    ``wcs`` must be a celestial (RA/DEC) astropy WCS — SIP distortion is
    honoured because astropy applies it in ``all_pix2world``. Each pixel's
    four corners are transformed and the spherical-quad area is summed from
    two triangles, so the value is exact for the projection rather than a
    nominal pixel scale. For a 6.15 arcsec pixel this gives about
    8.89e-10 sr. Cost is O((rows+1) x (cols+1)) world-coordinate
    evaluations; intended for on-demand spectrum/injection use, not per-frame
    imaging.
    """
    if (
        not isinstance(shape, tuple)
        or len(shape) != 2
        or any(not isinstance(n, int) or n < 1 for n in shape)
    ):
        raise InvalidInputError(
            f"shape must be a (rows, cols) tuple of positive ints, got {shape!r}"
        )
    ny, nx = shape
    ctype = [str(c) for c in np.atleast_1d(wcs.wcs.ctype)]
    if len(ctype) < 2 or not ctype[0].startswith("RA") or not ctype[1].startswith("DEC"):
        raise InvalidInputError(f"wcs must be a celestial RA/DEC WCS, got CTYPE={ctype}")

    # Pixel edges in 0-based astropy pixel coords: centre i spans [i-0.5, i+0.5].
    xs = np.arange(nx + 1, dtype=np.float64) - 0.5
    ys = np.arange(ny + 1, dtype=np.float64) - 0.5
    gx, gy = np.meshgrid(xs, ys)
    world = wcs.all_pix2world(gx, gy, 0)
    if len(world) < 2:
        raise InvalidInputError("wcs did not produce two world coordinate arrays")
    lon = np.deg2rad(np.asarray(world[0], dtype=np.float64))
    lat = np.deg2rad(np.asarray(world[1], dtype=np.float64))
    vec = _unit_vectors(lon, lat)

    # Corner indices for pixel (i, j): 00=(i,j) 10=(i,j+1) 11=(i+1,j+1) 01=(i+1,j)
    v00 = vec[:-1, :-1]
    v10 = vec[:-1, 1:]
    v11 = vec[1:, 1:]
    v01 = vec[1:, :-1]
    area = np.abs(_triangle_area(v00, v10, v11)) + np.abs(_triangle_area(v00, v11, v01))
    return check_not_all_nan(area, name="solid_angle_map")


__all__ = ["solid_angle_map"]
