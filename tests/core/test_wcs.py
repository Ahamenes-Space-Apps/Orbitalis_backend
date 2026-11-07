"""Tests for WCS-WAVE parsing and wavelength interpolation (FR-CORE-02).

Purpose: Verify own bilinear interpolation of the WCS-WAVE lookup against
known answers, a real IRSA cutout fixture, out-of-range behaviour, and input
validation.
Inputs: Synthetic tables plus tests/fixtures/wcs_wave.npz (real QR2 cutout).
Outputs: Test results.
Called by: pytest.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from astropy.io import fits

from orbitalis_core.errors import InvalidInputError
from orbitalis_core.wcs import WaveTab, bandwidth_at, wavelength_at, wavelength_map

FIXTURE = Path(__file__).parent.parent / "fixtures" / "wcs_wave.npz"


def _load_fixture() -> dict[str, np.ndarray]:
    return dict(np.load(FIXTURE))


def _header(**overrides: float) -> fits.Header:
    hdr = fits.Header()
    hdr["CRPIX1W"] = -10.0
    hdr["CRPIX2W"] = -10.0
    hdr["CRVAL1W"] = 0.0
    hdr["CRVAL2W"] = 0.0
    hdr["CDELT1W"] = 1.0
    hdr["CDELT2W"] = 1.0
    for key, value in overrides.items():
        hdr[key] = value
    return hdr


def _identity_tab() -> WaveTab:
    """3x3 table where wavelength = 10*x_tab - 5*y_tab (a plane)."""
    x = np.array([10.0, 20.0, 30.0])
    y = np.array([100.0, 200.0, 300.0])
    xx, yy = np.meshgrid(x, y)
    wave = 10.0 * xx - 5.0 * yy
    band = np.full_like(wave, 0.5)
    values = np.stack([wave, band], axis=-1)
    return WaveTab.from_columns(x, y, values)


# --- CORE-WCS-01: nodes exact, between nodes bilinear ---------------------


def test_wavelength_at_control_points_exact() -> None:
    tab = _identity_tab()
    hdr = _header()
    for x_tab, y_tab in zip(tab.x, tab.y, strict=True):
        for x_pix, y_pix in [(x_tab - 10, y_tab - 10)]:
            # header maps pixel p -> table coord p + 10
            assert wavelength_at(hdr, tab, x_pix, y_pix) == pytest.approx(
                10.0 * x_tab - 5.0 * y_tab
            )


def test_wavelength_at_bilinear_between_nodes() -> None:
    tab = _identity_tab()
    hdr = _header()
    # Table coord (15, 150) is inside cell [10,20]x[100,200].
    # Plane value = 10*15 - 5*150 = -600; bilinear reproduces planes exactly.
    assert wavelength_at(hdr, tab, 5.0, 140.0) == pytest.approx(-600.0)
    # Off-midpoint check: coord (17, 130) -> 170 - 650 = -480
    assert wavelength_at(hdr, tab, 7.0, 120.0) == pytest.approx(-480.0)


def test_wavelength_at_hand_computed_cell() -> None:
    # Non-planar table: values at corners of one cell are distinct.
    x = np.array([0.0, 1.0])
    y = np.array([0.0, 1.0])
    values = np.array(
        [
            [[0.0, 0.1], [10.0, 0.1]],  # iy=0: y=0 row -> wavelengths 0, 10
            [[20.0, 0.1], [40.0, 0.1]],  # iy=1: y=1 row -> wavelengths 20, 40
        ]
    )
    tab = WaveTab.from_columns(x, y, values)
    hdr = _header(CRPIX1W=0.0, CRPIX2W=0.0)  # pixel == table coord
    # At (0.5, 0.5): mean of corners = (0+10+20+40)/4 = 17.5
    assert wavelength_at(hdr, tab, 0.5, 0.5) == pytest.approx(17.5)
    # At (0.25, 0.5): tx=0.25, ty=0.5 -> 0.375*0 + 0.625*10 + 0.375*20 + 0.625*40... compute:
    # v = (1-tx)(1-ty)*0 + tx(1-ty)*10 + (1-tx)ty*20 + tx*ty*40
    #   = 0.75*0.5*0 + 0.25*0.5*10 + 0.75*0.5*20 + 0.25*0.5*40 = 1.25+7.5+5 = 13.75
    assert wavelength_at(hdr, tab, 0.25, 0.5) == pytest.approx(13.75)


def test_bandwidth_at_returns_second_component() -> None:
    tab = _identity_tab()
    hdr = _header()
    assert bandwidth_at(hdr, tab, 15.0, 150.0) == pytest.approx(0.5)


# --- Real IRSA fixture (CORE-WCS-01 known answer) -------------------------


def test_fixture_matches_astropy_reference() -> None:
    """Our interpolation reproduces astropy's WAVE-TAB within ~1 nm."""
    fx = _load_fixture()
    tab = WaveTab.from_columns(fx["X"], fx["Y"], fx["VALUES"])
    hdr = fits.Header()
    for key in ("CRPIX1W", "CRPIX2W", "CRVAL1W", "CRVAL2W", "CDELT1W", "CDELT2W"):
        hdr[key] = fx[key].item()
    errs = [
        abs(wavelength_at(hdr, tab, px, py) - wl)
        for px, py, wl in zip(fx["ref_px"], fx["ref_py"], fx["ref_wl_um"], strict=True)
    ]
    assert max(errs) < 0.001  # 1 nm = 0.001 um
    berrs = [
        abs(bandwidth_at(hdr, tab, px, py) - bw)
        for px, py, bw in zip(fx["ref_px"], fx["ref_py"], fx["ref_bw_um"], strict=True)
    ]
    assert max(berrs) < 0.001


def test_wcs_object_path() -> None:
    """A spectral WCS object (key='W') gives the same answers as the header."""
    fx = _load_fixture()
    tab = WaveTab.from_columns(fx["X"], fx["Y"], fx["VALUES"])

    class FakeWcsprm:
        ctype = np.array(["WAVE-TAB", "WAVE-TAB"])
        crpix = np.array([fx["CRPIX1W"].item(), fx["CRPIX2W"].item()], dtype=np.float64)
        crval = np.array([fx["CRVAL1W"].item(), fx["CRVAL2W"].item()], dtype=np.float64)
        cdelt = np.array([fx["CDELT1W"].item(), fx["CDELT2W"].item()], dtype=np.float64)
        pc = np.eye(2)

    class FakeWcs:
        wcs = FakeWcsprm()

    hdr = fits.Header()
    for key in ("CRPIX1W", "CRPIX2W", "CRVAL1W", "CRVAL2W", "CDELT1W", "CDELT2W"):
        hdr[key] = fx[key].item()
    px, py = float(fx["ref_px"][0]), float(fx["ref_py"][0])
    assert wavelength_at(FakeWcs(), tab, px, py) == pytest.approx(wavelength_at(hdr, tab, px, py))
    assert wavelength_at(FakeWcs(), tab, px, py) == pytest.approx(
        float(fx["ref_wl_um"][0]), abs=0.001
    )


# --- CORE-WCS-02: outside the table is an error / NaN, never extrapolation


def test_wavelength_at_outside_table_raises() -> None:
    tab = _identity_tab()
    hdr = _header()  # pixel p -> table coord p + 10; table x range 10..30
    with pytest.raises(InvalidInputError):
        wavelength_at(hdr, tab, -5.0, 140.0)  # table x = 5 < 10


def test_wavelength_map_nan_outside_table() -> None:
    x = np.array([10.0, 20.0])
    y = np.array([10.0, 20.0])
    xx, yy = np.meshgrid(x, y)
    values = np.stack([xx + yy, np.full_like(xx, 1.0)], axis=-1)
    tab = WaveTab.from_columns(x, y, values)
    hdr = _header(CRPIX1W=0.0, CRPIX2W=0.0, CRVAL1W=0.0, CRVAL2W=0.0)
    # pixel == table coord; shape (15,15): pixels 0..9 are below x/y min 10.
    out = wavelength_map(hdr, tab, (15, 15))
    assert out.shape == (15, 15)
    assert np.isnan(out[:10, :10]).all() or np.isnan(out[0, 0])
    # corner (14,14) -> coord (14,14) inside [10,20]^2
    assert out[14, 14] == pytest.approx(28.0)
    # edge pixels outside on one axis only are NaN too
    assert np.isnan(out[0, 14])
    assert np.isnan(out[14, 0])


# --- Validation ------------------------------------------------------------


def test_from_columns_rejects_wrong_values_shape() -> None:
    with pytest.raises(InvalidInputError):
        WaveTab.from_columns([0.0, 1.0], [0.0, 1.0], np.zeros((2, 2, 3)))


def test_from_columns_rejects_mismatched_grid() -> None:
    values = np.zeros((3, 3, 2))
    with pytest.raises(InvalidInputError):
        WaveTab.from_columns([0.0, 1.0], [0.0, 1.0], values)


def test_from_columns_rejects_nonincreasing_coords() -> None:
    values = np.zeros((2, 2, 2))
    with pytest.raises(InvalidInputError):
        WaveTab.from_columns([1.0, 1.0], [0.0, 1.0], values)
    with pytest.raises(InvalidInputError):
        WaveTab.from_columns([0.0, 1.0], [1.0, 0.5], values)


def test_from_columns_rejects_nonfinite() -> None:
    values = np.full((2, 2, 2), np.nan)
    with pytest.raises(InvalidInputError):
        WaveTab.from_columns([0.0, 1.0], [0.0, 1.0], values)


def test_from_hdu_parses_binary_table() -> None:
    x = np.array([1.0, 2.0])
    y = np.array([3.0, 4.0])
    values = np.zeros((2, 2, 2))
    hdu = fits.BinTableHDU(
        fits.FITS_rec.from_columns(
            [
                fits.Column(name="X", format="2J", dim="(2)", array=x.astype(">i4")[None, :]),
                fits.Column(name="Y", format="2J", dim="(2)", array=y.astype(">i4")[None, :]),
                fits.Column(
                    name="VALUES",
                    format="8E",
                    dim="(2,2,2)",
                    array=values.astype(">f4").reshape(1, 8),
                ),
            ]
        )
    )
    tab = WaveTab.from_hdu(hdu)
    assert tab.x.tolist() == [1.0, 2.0]
    assert tab.y.tolist() == [3.0, 4.0]
    assert tab.wavelength.shape == (2, 2)


def test_from_hdu_rejects_wrong_hdu() -> None:
    hdu = fits.ImageHDU(data=np.zeros((2, 2)))
    with pytest.raises(InvalidInputError):
        WaveTab.from_hdu(hdu)


def test_non_wcs_tab_rejected() -> None:
    hdr = fits.Header()
    hdr["CRPIX1"] = 0.0  # spatial keywords only, no *W
    tab = _identity_tab()
    with pytest.raises(InvalidInputError):
        wavelength_at(hdr, tab, 15.0, 150.0)
