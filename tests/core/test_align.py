"""Tests for common-grid alignment (FR-CORE-04) and the D-03 measurement.

Purpose: Verify to_common_grid lands a shifted image on the target grid,
conserves surface brightness, propagates masks, and — as the D-03 evidence —
that resampling MJy/sr agrees with the DS-spec flux-per-pixel path within a
stated tolerance.
Inputs: Synthetic astropy TAN WCS objects and small NumPy arrays.
Outputs: Test results.
Called by: pytest.
"""

from __future__ import annotations

import numpy as np
import pytest
from astropy.wcs import WCS
from reproject import reproject_exact

from orbitalis_core.align import to_common_grid
from orbitalis_core.calibration import solid_angle_map
from orbitalis_core.errors import EmptyResultError, InvalidInputError


def _tan_wcs(crval: tuple[float, float], crpix: tuple[float, float], cdelt_deg: float) -> WCS:
    w = WCS(naxis=2)
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    w.wcs.crval = list(crval)
    w.wcs.crpix = list(crpix)
    w.wcs.cdelt = [cdelt_deg, cdelt_deg]
    return w


def _field(seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    yy, xx = np.indices((40, 40))
    data = 2.0 + 0.05 * rng.standard_normal((40, 40))
    data += 3.0 * np.exp(-(((yy - 20) ** 2 + (xx - 20) ** 2) / 8.0))
    data[0, :] = np.nan  # masked row
    return data


# --- CORE-ALN-01/02 ---------------------------------------------------------


def test_identity_reprojection_unchanged() -> None:
    w = _tan_wcs((10.0, 20.0), (20.5, 20.5), 0.0017)
    data = _field()
    out, footprint = to_common_grid(data, w, w, (40, 40))
    inner = np.s_[2:-2, 2:-2]
    np.testing.assert_allclose(out[inner], data[inner], atol=1e-6)
    assert footprint[inner].all()


def test_shifted_image_lands_on_target_grid() -> None:
    w1 = _tan_wcs((10.0, 20.0), (20.5, 20.5), 0.0017)
    # target shifted ~2 px in RA and ~1 px in Dec relative to source
    w2 = _tan_wcs((10.0 + 0.0017 * 2, 20.0 - 0.0017), (20.5, 20.5), 0.0017)
    data = _field()
    out, footprint = to_common_grid(data, w1, w2, (40, 40))
    # The blob's sky position must be preserved: output peak pixel -> world
    # via w2 must coincide with input blob centre (pixel 20,20) -> world via w1.
    peak_rc = np.unravel_index(np.nanargmax(out), out.shape)
    lon_in, lat_in = w1.all_pix2world(np.array(20.0), np.array(20.0), 0)
    lon_out, lat_out = w2.all_pix2world(np.array(float(peak_rc[1])), np.array(float(peak_rc[0])), 0)
    sep_deg = np.sqrt(
        ((np.asarray(lon_out) - np.asarray(lon_in)) * np.cos(np.deg2rad(20.0))) ** 2
        + (np.asarray(lat_out) - np.asarray(lat_in)) ** 2
    )
    assert float(np.max(sep_deg)) < 0.0017 * 1.5  # within ~1.5 output pixels
    assert footprint[peak_rc]


def test_nan_mask_propagates() -> None:
    w1 = _tan_wcs((10.0, 20.0), (20.5, 20.5), 0.0017)
    w2 = _tan_wcs((10.002, 19.999), (20.5, 20.5), 0.0017)
    data = _field()
    out, _ = to_common_grid(data, w1, w2, (40, 40))
    assert np.isnan(out[0, :]).all() or np.isnan(out[:3, :]).any()


def test_flux_conserved_for_constant_surface_brightness() -> None:
    """A uniform MJy/sr field stays uniform after reprojection (CORE-ALN)."""
    w1 = _tan_wcs((10.0, 20.0), (20.5, 20.5), 0.0017)
    w2 = _tan_wcs((10.003, 19.998), (20.5, 20.5), 0.0017)
    data = np.full((40, 40), 3.0)
    out, _ = to_common_grid(data, w1, w2, (40, 40))
    inner = np.s_[4:-4, 4:-4]
    np.testing.assert_allclose(out[inner], 3.0, rtol=0.01)


def test_input_not_mutated() -> None:
    w = _tan_wcs((10.0, 20.0), (20.5, 20.5), 0.0017)
    data = _field()
    before = data.copy()
    to_common_grid(data, w, w, (40, 40))
    np.testing.assert_array_equal(np.nan_to_num(data), np.nan_to_num(before))
    assert np.isnan(data[0, 0])


def test_all_nan_output_raises() -> None:
    w1 = _tan_wcs((10.0, 20.0), (20.5, 20.5), 0.0017)
    # target grid far away: no overlap -> all NaN
    w2 = _tan_wcs((50.0, 60.0), (20.5, 20.5), 0.0017)
    with pytest.raises(EmptyResultError):
        to_common_grid(np.ones((10, 10)), w1, w2, (10, 10))


def test_validation() -> None:
    w = _tan_wcs((10.0, 20.0), (20.5, 20.5), 0.0017)
    with pytest.raises(InvalidInputError):
        to_common_grid(np.zeros((3, 3, 3)), w, w, (4, 4))
    with pytest.raises(InvalidInputError):
        to_common_grid(np.zeros((4, 4)), w, w, (4,))  # type: ignore[arg-type]
    noncel = WCS(naxis=2)
    noncel.wcs.ctype = ["FREQ", "STOKES"]
    noncel.wcs.crval = [1.0, 1.0]
    noncel.wcs.crpix = [1.0, 1.0]
    noncel.wcs.cdelt = [1.0, 1.0]
    with pytest.raises(InvalidInputError):
        to_common_grid(np.ones((4, 4)), noncel, w, (4, 4))


# --- D-03 measurement: MJy/sr resampling vs flux-per-pixel resampling --------


def test_d03_surface_brightness_vs_flux_per_pixel() -> None:
    """SDD D-03 evidence: both resampling orders agree within 2%.

    Path A (SDD): resample MJy/sr directly with interpolation.
    Path B (DS spec): multiply by the solid-angle map to get flux per pixel,
    resample with the flux-conserving reproject_exact, divide by the target
    solid angle. On a field where pixel area varies, the two must agree —
    that is the measurement that closes D-03.
    """
    w1 = _tan_wcs((30.0, 40.0), (30.5, 30.5), 0.02)  # ~1.2 deg field -> omega varies
    w2 = _tan_wcs((30.004, 39.996), (30.5, 30.5), 0.02)
    shape = (60, 60)
    rng = np.random.default_rng(1)
    yy, xx = np.indices(shape)
    sb = 2.0 + 0.1 * rng.standard_normal(shape)
    sb += 2.0 * np.exp(-(((yy - 30) ** 2 + (xx - 30) ** 2) / 30.0))

    omega_in = solid_angle_map(w1, shape)
    omega_out = solid_angle_map(w2, shape)

    path_a, _ = to_common_grid(sb, w1, w2, shape)

    flux_in = sb * omega_in  # arbitrary flux units; only ratios matter
    flux_out = reproject_exact((flux_in, w1), w2, shape, return_footprint=False)
    path_b = flux_out / omega_out

    mask = np.isfinite(path_a) & np.isfinite(path_b) & (omega_out > 0)
    mask[:3, :] = mask[-3:, :] = mask[:, :3] = mask[:, -3:] = False
    rel = np.abs(path_a[mask] - path_b[mask]) / np.abs(path_b[mask])
    # bilinear interpolation smooths the peak slightly; tolerance covers that
    assert np.median(rel) < 0.02
    assert np.percentile(rel, 95) < 0.10
