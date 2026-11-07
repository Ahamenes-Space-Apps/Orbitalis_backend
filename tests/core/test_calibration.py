"""Tests for calibration helpers (FR-CORE-03).

Purpose: Verify solid_angle_map against known footprints and pixel scales,
and subtract_zodi arithmetic, mask propagation and input hygiene.
Inputs: Synthetic astropy WCS objects and small NumPy arrays.
Outputs: Test results.
Called by: pytest.
"""

from __future__ import annotations

import numpy as np
import pytest
from astropy.wcs import WCS

from orbitalis_core.calibration import solid_angle_map, subtract_zodi, to_surface_brightness
from orbitalis_core.errors import EmptyResultError, InvalidInputError


def _tan_wcs(crval_dec: float, cdelt_deg: float, crpix: tuple[float, float]) -> WCS:
    w = WCS(naxis=2)
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    w.wcs.crval = [0.0, crval_dec]
    w.wcs.crpix = list(crpix)
    w.wcs.cdelt = [cdelt_deg, cdelt_deg]
    return w


# --- solid_angle_map -------------------------------------------------------


def test_nominal_615_arcsec_pixel() -> None:
    """CORE-CAL-02: 6.15 arcsec/px gives ~8.89e-10 sr within 1%."""
    w = _tan_wcs(0.0, 6.15 / 3600.0, (5.5, 5.5))
    out = solid_angle_map(w, (10, 10))
    expected = (6.15 / 206265.0) ** 2
    np.testing.assert_allclose(out, expected, rtol=0.01)


def test_map_sums_to_footprint() -> None:
    """Sum of per-pixel solid angles equals the rectangular footprint area."""
    n = 30
    fov_deg = 30.0 / 60.0  # 30 arcmin field
    w = _tan_wcs(0.0, fov_deg / n, (n / 2, n / 2))
    out = solid_angle_map(w, (n, n))
    pixel_rad = (fov_deg / n) * np.pi / 180.0
    expected = (n * pixel_rad) ** 2
    assert out.sum() == pytest.approx(expected, rel=0.01)


def test_solid_angle_not_constant_across_wide_field() -> None:
    """Pixel corners are used, not a nominal scale: 5 deg field varies >0.1%."""
    n = 60
    w = _tan_wcs(0.0, 5.0 / n, (n / 2, n / 2))
    out = solid_angle_map(w, (n, n))
    assert (out.max() - out.min()) / out.mean() > 0.001


def test_solid_angle_map_rejects_non_celestial_wcs() -> None:
    w = WCS(naxis=2)
    w.wcs.ctype = ["FREQ", "STOKES"]
    w.wcs.crval = [1.0, 1.0]
    w.wcs.crpix = [1.0, 1.0]
    w.wcs.cdelt = [1.0, 1.0]
    with pytest.raises(InvalidInputError):
        solid_angle_map(w, (4, 4))


def test_solid_angle_map_rejects_bad_shape() -> None:
    w = _tan_wcs(0.0, 0.001, (2.0, 2.0))
    with pytest.raises(InvalidInputError):
        solid_angle_map(w, (4,))  # type: ignore[arg-type]


# --- subtract_zodi ---------------------------------------------------------


def test_subtract_zodi_basic() -> None:
    image = np.array([[2.0, 4.0], [6.0, 8.0]])
    zodi = np.array([[0.5, 1.0], [1.5, 2.0]])
    out = subtract_zodi(image, zodi)
    np.testing.assert_allclose(out, image - zodi)


def test_subtract_zodi_nan_propagates() -> None:
    image = np.array([[np.nan, 2.0], [3.0, 4.0]])
    zodi = np.array([[1.0, np.nan], [1.0, 1.0]])
    out = subtract_zodi(image, zodi)
    assert np.isnan(out[0, 0]) and np.isnan(out[0, 1])
    assert out[1, 0] == 2.0 and out[1, 1] == 3.0


def test_subtract_zodi_does_not_mutate_inputs() -> None:
    image = np.array([[2.0, 4.0]])
    zodi = np.array([[1.0, 1.0]])
    image_copy = image.copy()
    zodi_copy = zodi.copy()
    subtract_zodi(image, zodi)
    np.testing.assert_array_equal(image, image_copy)
    np.testing.assert_array_equal(zodi, zodi_copy)


def test_subtract_zodi_shape_mismatch() -> None:
    with pytest.raises(InvalidInputError):
        subtract_zodi(np.zeros((2, 2)), np.zeros((2, 3)))


def test_subtract_zodi_rejects_non_numeric() -> None:
    with pytest.raises(InvalidInputError):
        subtract_zodi(np.array([["a"]]), np.array([[1.0]]))


def test_subtract_zodi_all_nan_raises() -> None:
    nan = np.full((2, 2), np.nan)
    with pytest.raises(EmptyResultError):
        subtract_zodi(nan, np.zeros((2, 2)))


# --- to_surface_brightness stub --------------------------------------------


def test_to_surface_brightness_not_implemented() -> None:
    with pytest.raises(NotImplementedError):
        to_surface_brightness(np.zeros((2, 2)))
