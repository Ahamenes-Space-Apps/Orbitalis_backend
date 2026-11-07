"""Tests for sigma-clipped stacking and difference imaging (FR-CORE-05).

Purpose: Verify outlier rejection, NaN handling, variance propagation against
analytic values, and difference mask union.
Inputs: Tiny synthetic frame sets.
Outputs: Test results.
Called by: pytest.
"""

from __future__ import annotations

import numpy as np
import pytest

from orbitalis_core.errors import EmptyResultError, InvalidInputError
from orbitalis_core.stack import combine, difference


def _frames(n: int, value: float = 1.0, shape: tuple[int, int] = (4, 4)) -> np.ndarray:
    return np.full((n,) + shape, value)


# --- CORE-STK-01: sigma-clipped combine ------------------------------------


def test_outlier_frame_rejected() -> None:
    frames = _frames(5, 1.0)
    frames[2, 1, 1] = 100.0  # single-frame outlier at one pixel
    out = combine(frames)
    assert out.data[1, 1] == pytest.approx(1.0, abs=1e-9)
    assert out.coverage[1, 1] == 4  # outlier excluded


def test_no_outlier_keeps_all_frames() -> None:
    frames = _frames(4, 2.0)
    frames[0] += 0.01
    frames[1] -= 0.01
    frames[2] += 0.02
    frames[3] -= 0.02
    out = combine(frames)
    assert out.coverage.min() == 4
    assert out.data.mean() == pytest.approx(2.0, abs=1e-9)


def test_nan_frames_ignored() -> None:
    frames = _frames(4, 3.0)
    frames[1, :, :] = np.nan  # one fully masked frame
    out = combine(frames)
    assert np.allclose(out.data, 3.0)
    assert out.coverage.min() == 3


def test_all_nan_pixel_stays_nan() -> None:
    frames = _frames(3, 1.0)
    frames[:, 0, 0] = np.nan
    out = combine(frames)
    assert np.isnan(out.data[0, 0])
    assert out.coverage[0, 0] == 0
    assert np.isfinite(out.data[1:, 1:]).all()


def test_single_frame_passthrough() -> None:
    out = combine(np.array([[[1.0, 2.0], [3.0, 4.0]]]))
    np.testing.assert_allclose(out.data, [[1.0, 2.0], [3.0, 4.0]])
    assert out.coverage.min() == 1


def test_median_method() -> None:
    frames = _frames(5, 1.0)
    frames[0] = 50.0  # strong outlier frame
    out = combine(frames, method="median")
    assert out.data.mean() == pytest.approx(1.0, abs=1e-9)
    assert out.variance is None


def test_variance_matches_analytic_value() -> None:
    """3 frames, each variance 0.09 -> mean variance = 3*0.09/9 = 0.03."""
    frames = _frames(3, 1.0, shape=(2, 2))
    frames[0] += 0.1
    frames[1] -= 0.1
    frames[2] += 0.2
    variances = np.full((3, 2, 2), 0.09)
    out = combine(frames, variances=variances)
    np.testing.assert_allclose(out.variance, 0.03, rtol=1e-9)


def test_variance_none_without_variances() -> None:
    out = combine(_frames(3, 1.0))
    assert out.variance is None


def test_clipped_pixel_variance_uses_kept_count() -> None:
    frames = _frames(4, 1.0, shape=(1, 1))
    frames[3, 0, 0] = 100.0  # clipped outlier
    variances = np.full((4, 1, 1), 0.04)
    out = combine(frames, variances=variances)
    # 3 kept frames -> sum(var)/n^2 = 3*0.04/9 = 0.01333...
    assert out.variance[0, 0] == pytest.approx(0.04 * 3 / 9)


def test_zero_mad_rejects_deviating_minority() -> None:
    """MAD == 0: only values equal to the median survive (documented behavior)."""
    frames = _frames(4, 1.0, shape=(1, 1))
    frames = np.concatenate([frames, np.full((1, 1, 1), 1.2)])
    out = combine(frames)
    assert out.data[0, 0] == pytest.approx(1.0)
    assert out.coverage[0, 0] == 4


def test_nan_variance_yields_nan_output_variance() -> None:
    """A kept frame with NaN variance must not underestimate the result."""
    frames = _frames(4, 1.0, shape=(1, 1))
    frames[0, 0, 0] += 0.1
    frames[1, 0, 0] -= 0.1
    frames[2, 0, 0] += 0.2
    variances = np.full((4, 1, 1), 0.09)
    variances[1, 0, 0] = np.nan
    out = combine(frames, variances=variances)
    assert np.isnan(out.variance[0, 0])


def test_all_nan_result_raises() -> None:
    frames = np.full((2, 2, 2), np.nan)
    with pytest.raises(EmptyResultError):
        combine(frames)


def test_combine_validation() -> None:
    with pytest.raises(InvalidInputError):
        combine([])
    with pytest.raises(InvalidInputError):
        combine(_frames(2, 1.0), method="bogus")
    with pytest.raises(InvalidInputError):
        combine(_frames(2, 1.0), sigma=0.0)
    with pytest.raises(InvalidInputError):
        combine([np.ones((2, 2)), np.ones((3, 3))])
    with pytest.raises(InvalidInputError):
        combine(_frames(2, 1.0), variances=np.zeros((2, 2, 3)))


# --- CORE-STK-02: difference ------------------------------------------------


def test_difference_identical_frames_zero() -> None:
    a = np.array([[1.0, np.nan], [3.0, 4.0]])
    out = difference(a, a.copy())
    np.testing.assert_allclose(out[np.isfinite(out)], 0.0)
    assert np.isnan(out[0, 1])  # the only masked input pixel


def test_difference_mask_is_union() -> None:
    a = np.array([[1.0, np.nan], [3.0, 4.0]])
    b = np.array([[np.nan, 2.0], [1.0, 4.0]])
    out = difference(a, b)
    assert np.isnan(out[0, 0]) and np.isnan(out[0, 1])  # union of both masks
    assert out[1, 0] == 2.0 and out[1, 1] == 0.0


def test_difference_validation() -> None:
    with pytest.raises(InvalidInputError):
        difference(np.ones((2, 2)), np.ones((2, 3)))
    with pytest.raises(EmptyResultError):
        difference(np.full((2, 2), np.nan), np.ones((2, 2)))
