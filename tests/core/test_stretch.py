"""Tests for fixed display stretch (FR-CORE-06).

Purpose: Verify fit determinism, the freeze-after-N-frames rule, apply
endpoints, NaN handling and validation.
Inputs: Tiny synthetic arrays.
Outputs: Test results.
Called by: pytest.
"""

from __future__ import annotations

import numpy as np
import pytest

from orbitalis_core.errors import EmptyResultError, InvalidInputError
from orbitalis_core.stretch import StretchState, apply_stretch, fit_stretch, initial_stretch


def _frames(n: int, base: float = 0.0) -> list[np.ndarray]:
    rng = np.random.default_rng(7)
    return [base + rng.random((8, 8)) for _ in range(n)]


# --- CORE-STR-01 ------------------------------------------------------------


def test_fit_is_deterministic() -> None:
    frames = _frames(4)
    p1 = fit_stretch(frames)
    p2 = fit_stretch(frames)
    assert p1 == p2


def test_fit_uses_finite_pixels_only() -> None:
    frames = _frames(2)
    frames[0][0, 0] = np.nan
    frames[0][0, 1] = 1e9  # extreme but finite value
    p = fit_stretch(frames, lo_percentile=0.0, hi_percentile=100.0)
    assert np.isfinite(p.lo) and np.isfinite(p.hi)
    assert p.hi >= 1e9 - 1e-6  # max finite pixel sets hi at 100th percentile
    assert p.n_pixels == 2 * 64 - 1


def test_apply_endpoints_and_nan() -> None:
    frames = _frames(2)
    params = fit_stretch(frames)
    arr = np.array([[params.lo, params.hi], [np.nan, (params.lo + params.hi) / 2]])
    out = apply_stretch(arr, params)
    assert out[0, 0] == pytest.approx(0.0, abs=1e-9)
    assert out[0, 1] == pytest.approx(1.0, abs=1e-9)
    assert np.isnan(out[1, 0])
    assert 0.0 < out[1, 1] < 1.0
    assert np.nanmin(out) >= 0.0 and np.nanmax(out) <= 1.0


def test_apply_clips_outside_range() -> None:
    frames = _frames(2)
    params = fit_stretch(frames)
    lo, hi = params.lo, params.hi
    out = apply_stretch(np.array([[lo - 100.0, hi + 100.0]]), params)
    assert out[0, 0] == 0.0 and out[0, 1] == 1.0


def test_stretch_state_freezes_after_n_frames() -> None:
    state = StretchState(fix_n=3)
    frames = _frames(6)
    assert state.observe(frames[0]) is None
    assert state.observe(frames[1]) is None
    p = state.observe(frames[2])
    assert p is not None and state.is_frozen
    frozen = p
    # Later, wildly different frames must not change the parameters.
    crazy = [np.full((8, 8), 1e6) for _ in range(3)]
    for f in crazy:
        assert state.observe(f) == frozen
    assert state.params == frozen


def test_stretch_state_params_none_before_freeze() -> None:
    state = StretchState(fix_n=8)
    for f in _frames(7):
        assert state.observe(f) is None
    assert state.params is None and not state.is_frozen


def test_stretch_state_provisional_before_freeze() -> None:
    """Provisional curve is returned pre-freeze, then replaced by the fit."""
    provisional = fit_stretch(_frames(2, base=100.0))
    state = StretchState(fix_n=3, provisional=provisional)
    frames = _frames(4)
    for f in frames[:2]:
        assert state.observe(f) == provisional
    fitted = state.observe(frames[2])
    assert fitted is not None and fitted != provisional
    assert state.observe(frames[3]) == fitted


def test_initial_stretch_fits_first_frame() -> None:
    frame = _frames(1)[0]
    p = initial_stretch(frame)
    p_direct = fit_stretch([frame])
    assert p == p_direct
    with pytest.raises(EmptyResultError):
        initial_stretch(np.full((4, 4), np.nan))


def test_stretch_state_rejects_bad_provisional() -> None:
    with pytest.raises(InvalidInputError):
        StretchState(fix_n=2, provisional="nope")  # type: ignore[arg-type]


def test_stretch_state_validates_fix_n() -> None:
    with pytest.raises(InvalidInputError):
        StretchState(fix_n=0)
    with pytest.raises(InvalidInputError):
        StretchState(fix_n=2.5)  # type: ignore[arg-type]


def test_fit_all_nan_raises() -> None:
    with pytest.raises(EmptyResultError):
        fit_stretch([np.full((4, 4), np.nan)])


def test_fit_degenerate_constant_field() -> None:
    with pytest.raises(InvalidInputError):
        fit_stretch([np.full((4, 4), 2.0)])


def test_apply_all_nan_raises() -> None:
    params = fit_stretch(_frames(2))
    with pytest.raises(EmptyResultError):
        apply_stretch(np.full((4, 4), np.nan), params)


def test_apply_rejects_bad_params_and_array() -> None:
    params = fit_stretch(_frames(2))
    with pytest.raises(InvalidInputError):
        apply_stretch(np.zeros((3, 3, 3)), params)
    with pytest.raises(InvalidInputError):
        apply_stretch(np.zeros((2, 2)), "not-params")  # type: ignore[arg-type]


def test_fit_rejects_bad_inputs() -> None:
    with pytest.raises(InvalidInputError):
        fit_stretch([])
    with pytest.raises(InvalidInputError):
        fit_stretch([np.zeros((2, 2, 2))])
    with pytest.raises(InvalidInputError):
        fit_stretch(_frames(2), lo_percentile=50.0, hi_percentile=10.0)
    with pytest.raises(InvalidInputError):
        fit_stretch(_frames(2), softness=-1.0)
