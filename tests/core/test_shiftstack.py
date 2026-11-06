"""Tests for the SPHEREx shift-and-stack core module.

Purpose: Verify shifting, combination, motion recovery, validation, and
scientific integrity using small synthetic arrays.
Inputs: Synthetic NumPy arrays.
Outputs: Test results.
Called by: pytest.
"""

from __future__ import annotations

import numpy as np
import pytest

from orbitalis_core.shiftstack import (
    Frame,
    InvalidInputError,
    MotionVector,
    WorkBudgetExceededError,
    combine,
    search,
    shift_and_combine,
    shift_image,
)


def test_zero_shift_leaves_image_unchanged() -> None:
    image = np.arange(12, dtype=float).reshape(3, 4)
    shifted = shift_image(image, 0.0, 0.0)
    assert np.array_equal(shifted, image, equal_nan=True)


def test_integer_shift_moves_source_without_wraparound() -> None:
    image = np.zeros((5, 5), dtype=float)
    image[1, 1] = 10.0
    shifted = shift_image(image, 0.0, 1.0)
    assert shifted[1, 2] == 10.0
    assert shifted[1, 1] == 0.0
    # No wraparound at the edge.
    edge = np.zeros((5, 5), dtype=float)
    edge[1, 4] = 10.0
    shifted_edge = shift_image(edge, 0.0, 1.0)
    assert np.all(np.isnan(shifted_edge[:, 0]) | (shifted_edge[:, 0] == 0.0))
    assert not np.any(shifted_edge == 10.0)


def test_negative_shift() -> None:
    image = np.zeros((5, 5), dtype=float)
    image[2, 3] = 7.0
    shifted = shift_image(image, 0.0, -1.0)
    assert shifted[2, 2] == 7.0


def test_subpixel_shift_consistent() -> None:
    image = np.zeros((5, 5), dtype=float)
    image[2, 2] = 1.0
    shifted = shift_image(image, 0.0, 0.5)
    # Bilinear result: half the value in each of two adjacent pixels.
    assert shifted[2, 2] == pytest.approx(0.5)
    assert shifted[2, 3] == pytest.approx(0.5)


def test_nan_pixels_do_not_contaminate_shift() -> None:
    image = np.zeros((5, 5), dtype=float)
    image[2, 2] = 1.0
    image[2, 3] = np.nan
    shifted = shift_image(image, 0.0, 0.5)
    # The valid source contributes without fabricating a value in the NaN neighbor.
    assert shifted[2, 2] == pytest.approx(0.5)
    assert np.isnan(shifted[2, 3])
    # Out-of-bounds pixels stay NaN and do not wrap around.
    assert np.all(np.isnan(shifted[:, 0]))


def test_combine_identical_images() -> None:
    image = np.array([[1.0, 2.0], [3.0, 4.0]])
    combined, variance, coverage = combine([image, image.copy()])
    assert np.array_equal(combined, image)
    assert variance is None
    assert np.array_equal(coverage, np.array([[2, 2], [2, 2]]))


def test_combine_nan_does_not_contaminate() -> None:
    a = np.array([[1.0, 2.0], [3.0, np.nan]])
    b = np.array([[1.0, np.nan], [3.0, 4.0]])
    combined, _variance, coverage = combine([a, b])
    assert combined[0, 0] == 1.0
    assert combined[0, 1] == 2.0
    assert combined[1, 0] == 3.0
    assert combined[1, 1] == 4.0
    assert np.array_equal(coverage, np.array([[2, 1], [2, 1]]))


def test_combine_no_valid_contributors_is_nan() -> None:
    a = np.array([[np.nan, 1.0]])
    b = np.array([[np.nan, np.nan]])
    combined, _variance, coverage = combine([a, b])
    assert np.isnan(combined[0, 0])
    assert coverage[0, 0] == 0


def test_weighted_mean_and_variance() -> None:
    image = np.array([[5.0]])
    var = np.array([[4.0]])
    combined, variance, coverage = combine([image, image.copy()], [var, var.copy()])
    assert combined[0, 0] == pytest.approx(5.0)
    assert variance[0, 0] == pytest.approx(2.0)
    assert coverage[0, 0] == 2


def test_invalid_variance_ignored() -> None:
    image = np.array([[5.0, 5.0]])
    var = np.array([[0.0, np.nan]])
    combined, variance, coverage = combine([image, image.copy()], [var, var.copy()])
    # Both variance values invalid, so no weighted contributors.
    assert np.all(np.isnan(combined))
    assert np.all(np.isnan(variance))
    assert np.array_equal(coverage, np.array([[0, 0]]))


def test_motion_recovery() -> None:
    size = 15
    frames = []
    velocity = (2.0, 1.0)  # dx, dy pixels/day
    for t in range(3):
        image = np.zeros((size, size), dtype=float)
        x = 5 + int(round(velocity[0] * t))
        y = 5 + int(round(velocity[1] * t))
        image[y, x] = 10.0
        frames.append(Frame(image=image, time=float(t), variance=np.ones((size, size))))
    motion_grid = [
        MotionVector(0.0, 0.0),
        MotionVector(1.0, 0.0),
        MotionVector(2.0, 1.0),
        MotionVector(3.0, 2.0),
    ]
    result = search(frames, motion_grid)
    assert result.best_motion == MotionVector(2.0, 1.0)
    correct_score = result.score_maps[2]
    zero_score = result.score_maps[0]
    assert np.nanmax(correct_score) > np.nanmax(zero_score)
    assert result.work_estimate == 4 * 3 * size * size


def test_zero_motion_stationary_source() -> None:
    size = 9
    frames = []
    for t in range(3):
        image = np.zeros((size, size), dtype=float)
        image[4, 4] = 8.0
        frames.append(Frame(image=image, time=float(t), variance=np.ones((size, size))))
    result = search(frames, [MotionVector(0.0, 0.0), MotionVector(1.0, 0.0)])
    assert result.best_motion == MotionVector(0.0, 0.0)


def test_shift_and_combine_single_motion() -> None:
    image = np.zeros((5, 5), dtype=float)
    image[2, 2] = 4.0
    frame = Frame(image=image, time=0.0)
    result = shift_and_combine([frame], MotionVector(1.0, 0.0))
    assert np.array_equal(result.combined, image)
    assert result.variance is None
    assert result.coverage[2, 2] == 1


def test_empty_motion_grid() -> None:
    image = np.zeros((3, 3), dtype=float)
    frame = Frame(image=image, time=0.0)
    result = search([frame], [])
    assert result.score_maps == ()
    assert result.best_index is None
    assert result.best_motion is None


def test_empty_frames_raises() -> None:
    with pytest.raises(InvalidInputError):
        search([], [MotionVector(0.0, 0.0)])


def test_work_budget_rejects_excessive_search() -> None:
    image = np.zeros((4, 4), dtype=float)
    frame = Frame(image=image, time=0.0)
    with pytest.raises(WorkBudgetExceededError):
        search([frame], [MotionVector(0.0, 0.0)], work_budget=0)


def test_different_image_shapes_raise() -> None:
    a = Frame(image=np.zeros((3, 3)), time=0.0)
    b = Frame(image=np.zeros((3, 4)), time=1.0)
    with pytest.raises(InvalidInputError):
        search([a, b], [MotionVector(0.0, 0.0)])


def test_nonfinite_time_raises() -> None:
    frame = Frame(image=np.zeros((2, 2)), time=float("nan"))
    with pytest.raises(InvalidInputError):
        search([frame], [MotionVector(0.0, 0.0)])


def test_input_not_mutated() -> None:
    image = np.array([[1.0, 2.0], [3.0, 4.0]])
    original = image.copy()
    frame = Frame(image=image, time=0.0)
    _ = shift_image(image, 1.0, 1.0)
    _ = search([frame], [MotionVector(0.0, 0.0)])
    assert np.array_equal(image, original)


def test_deterministic() -> None:
    image = np.zeros((4, 4), dtype=float)
    image[1, 1] = 5.0
    frame = Frame(image=image, time=0.0, variance=np.ones((4, 4)))
    r1 = search([frame], [MotionVector(0.0, 0.0)])
    r2 = search([frame], [MotionVector(0.0, 0.0)])
    assert np.array_equal(r1.score_maps[0], r2.score_maps[0])


def test_tuple_frame_and_motion_inputs() -> None:
    image = np.zeros((3, 3), dtype=float)
    image[1, 1] = 2.0
    frames = [(image, 0.0)]
    motions = [(0.0, 0.0)]
    result = search(frames, motions)
    assert result.best_motion == MotionVector(0.0, 0.0)


def test_shift_image_rejects_wraparound_at_boundary() -> None:
    image = np.zeros((4, 4), dtype=float)
    image[0, 0] = 1.0
    shifted = shift_image(image, -1.0, 0.0)
    assert np.all(np.isnan(shifted[3, :]) | (shifted[3, :] == 0.0))
    assert not np.any(shifted == 1.0)


def test_score_uses_variance() -> None:
    image = np.zeros((3, 3), dtype=float)
    image[1, 1] = 6.0
    frame = Frame(image=image, time=0.0, variance=np.full((3, 3), 4.0))
    result = search([frame], [MotionVector(0.0, 0.0)])
    assert result.combined_variances[0][1, 1] == pytest.approx(4.0)
    assert result.score_maps[0][1, 1] == pytest.approx(3.0)


def test_no_variance_score_is_combined_image() -> None:
    image = np.array([[1.0, 2.0], [3.0, 4.0]])
    frame = Frame(image=image, time=0.0)
    result = search([frame], [MotionVector(0.0, 0.0)])
    assert np.array_equal(result.score_maps[0], image)


def test_invalid_variance_shape_raises() -> None:
    frame = Frame(image=np.zeros((2, 2)), time=0.0, variance=np.ones((3, 3)))
    with pytest.raises(InvalidInputError):
        search([frame], [MotionVector(0.0, 0.0)])


def _render_point(shape: tuple[int, int], x: float, y: float, flux: float = 10.0) -> np.ndarray:
    image = np.zeros(shape, dtype=float)
    x0 = int(np.floor(x))
    y0 = int(np.floor(y))
    wx = x - x0
    wy = y - y0
    for iy in (0, 1):
        for ix in (0, 1):
            yy = y0 + iy
            xx = x0 + ix
            if 0 <= yy < shape[0] and 0 <= xx < shape[1]:
                wyw = (1.0 - wy) if iy == 0 else wy
                wxw = (1.0 - wx) if ix == 0 else wx
                image[yy, xx] += flux * wyw * wxw
    return image


def test_motion_recovery_subpixel() -> None:
    size = 21
    frames = []
    for t in range(5):
        x = 8.0 + 0.5 * t
        y = 8.0 + 0.25 * t
        image = _render_point((size, size), x, y)
        frames.append(Frame(image=image, time=float(t), variance=np.ones((size, size))))
    grid = [MotionVector(0.0, 0.0), MotionVector(0.5, 0.25), MotionVector(1.0, 0.5)]
    result = search(frames, grid)
    assert result.best_motion == MotionVector(0.5, 0.25)


def test_mixed_variance_availability_raises() -> None:
    image = np.zeros((2, 2), dtype=float)
    frames = [
        Frame(image=image, time=0.0, variance=np.ones((2, 2))),
        Frame(image=image, time=1.0),
    ]
    with pytest.raises(InvalidInputError):
        search(frames, [MotionVector(0.0, 0.0)])


def test_combine_mixed_variance_raises() -> None:
    image = np.zeros((2, 2), dtype=float)
    with pytest.raises(InvalidInputError):
        combine([image, image], [np.ones((2, 2)), None])


def test_invalid_motion_vector_raises() -> None:
    with pytest.raises(InvalidInputError):
        MotionVector(float("nan"), 0.0)
    with pytest.raises(InvalidInputError):
        MotionVector(1 + 2j, 0.0)  # type: ignore[arg-type]

    normalized = MotionVector("1.5", "2.0")  # type: ignore[arg-type]
    assert type(normalized.dx_px_per_day) is float
    assert type(normalized.dy_px_per_day) is float
    assert normalized.dx_px_per_day == 1.5
    assert normalized.dy_px_per_day == 2.0
    with pytest.raises(InvalidInputError):
        MotionVector(0.0, float("inf"))
    # Dict/tuple/object inputs are validated too.
    with pytest.raises(InvalidInputError):
        from orbitalis_core.shiftstack.models import _as_motion

        _as_motion({"dx": 1.0, "dy": float("nan")})
    with pytest.raises(InvalidInputError):
        from orbitalis_core.shiftstack.models import _as_motion

        _as_motion((float("inf"), 0.0))


def test_complex_image_rejected() -> None:
    image = np.zeros((2, 2), dtype=complex)
    with pytest.raises(InvalidInputError):
        shift_image(image, 0.0, 0.0)
    with pytest.raises(InvalidInputError):
        combine([image, image])
    frame = Frame(image=image, time=0.0)
    with pytest.raises(InvalidInputError):
        search([frame], [MotionVector(0.0, 0.0)])


def test_complex_variance_rejected() -> None:
    image = np.zeros((2, 2), dtype=float)
    variance = np.ones((2, 2), dtype=complex)
    with pytest.raises(InvalidInputError):
        combine([image, image], [variance, variance])
    frame = Frame(image=image, time=0.0, variance=variance)
    with pytest.raises(InvalidInputError):
        search([frame], [MotionVector(0.0, 0.0)])


def test_weighted_mean_numerical_stability() -> None:
    # Direct float64 multiplication would overflow for these finite values.
    image = np.full((2, 2), 1e200, dtype=float)
    variance = np.full((2, 2), 1e-200, dtype=float)
    combined, result_variance, coverage = combine(
        [image, image.copy()], [variance, variance.copy()]
    )
    np.testing.assert_allclose(combined, np.full((2, 2), 1e200))
    np.testing.assert_allclose(result_variance, np.full((2, 2), 5e-201))
    np.testing.assert_array_equal(coverage, np.full((2, 2), 2))


def test_weighted_mean_large_weights_mixed() -> None:
    images = [
        np.array([[1e200, 2e200]]),
        np.array([[3e200, 4e200]]),
    ]
    variances = [
        np.array([[1e-200, 1e-200]]),
        np.array([[1e-100, 1e-100]]),
    ]
    combined, result_variance, coverage = combine(images, variances)
    # The first contributor dominates the first pixel.
    assert combined[0, 0] > 1e199
    assert np.isfinite(combined[0, 0])
    assert np.isfinite(result_variance[0, 0])
    np.testing.assert_array_equal(coverage, np.array([[2, 2]]))


def test_weighted_mean_invalid_contributors_ignored() -> None:
    image = np.array([[5.0, 5.0]])
    variance = np.array([[0.0, np.nan]])
    combined, result_variance, coverage = combine(
        [image, image.copy()], [variance, variance.copy()]
    )
    assert np.all(np.isnan(combined))
    assert np.all(np.isnan(result_variance))
    np.testing.assert_array_equal(coverage, np.array([[0, 0]]))


def test_weighted_mean_no_valid_contributors_nan() -> None:
    image = np.array([[1.0]])
    variance = np.array([[np.nan]])
    combined, result_variance, coverage = combine([image], [variance])
    assert np.isnan(combined[0, 0])
    assert np.isnan(result_variance[0, 0])
    assert coverage[0, 0] == 0


def test_shift_and_combine_work_budget_exceeded() -> None:
    image = np.zeros((4, 4), dtype=float)
    frame = Frame(image=image, time=0.0)
    with pytest.raises(WorkBudgetExceededError):
        shift_and_combine([frame], MotionVector(0.0, 0.0), work_budget=0)


def test_shift_and_combine_work_budget_sufficient() -> None:
    image = np.zeros((3, 3), dtype=float)
    image[1, 1] = 4.0
    frame = Frame(image=image, time=0.0)
    result = shift_and_combine([frame], MotionVector(0.0, 0.0), work_budget=1000)
    assert np.array_equal(result.combined, image)
    assert result.coverage[1, 1] == 1


def test_shift_and_combine_default_budget() -> None:
    image = np.zeros((2, 2), dtype=float)
    frame = Frame(image=image, time=0.0)
    result = shift_and_combine([frame], MotionVector(0.0, 0.0))
    assert np.array_equal(result.combined, image)


def test_weighted_mean_convex_update_large_opposite_values() -> None:
    images = [
        np.array([[1e308]]),
        np.array([[-1e308]]),
    ]
    variances = [
        np.ones((1, 1), dtype=float),
        np.ones((1, 1), dtype=float),
    ]
    combined, variance, coverage = combine(images, variances)
    np.testing.assert_allclose(combined, np.array([[0.0]]))
    np.testing.assert_allclose(variance, np.array([[0.5]]))
    np.testing.assert_array_equal(coverage, np.array([[2]]))


def test_weighted_mean_large_finite_values() -> None:
    image = np.full((1, 1), 1e308, dtype=float)
    variance = np.ones((1, 1), dtype=float)
    combined, variance_result, coverage = combine(
        [image, image.copy()], [variance, variance.copy()]
    )
    np.testing.assert_allclose(combined, np.array([[1e308]]))
    np.testing.assert_allclose(variance_result, np.array([[0.5]]))
    np.testing.assert_array_equal(coverage, np.array([[2]]))


def test_unweighted_mean_large_finite_values() -> None:
    image = np.full((1, 1), 1e308, dtype=float)
    combined, variance, coverage = combine([image, image.copy()])
    np.testing.assert_allclose(combined, np.array([[1e308]]))
    assert variance is None
    np.testing.assert_array_equal(coverage, np.array([[2]]))


def test_extreme_small_variance_does_not_overflow() -> None:
    image = np.array([[1.0]])
    tiny = np.array([[5e-324]])
    combined, variance, coverage = combine([image, image], [tiny, tiny])
    np.testing.assert_allclose(combined, np.array([[1.0]]))
    np.testing.assert_allclose(variance, np.array([[0.0]]))
    np.testing.assert_array_equal(coverage, np.array([[2]]))


def test_work_budget_validation() -> None:
    image = np.zeros((2, 2), dtype=float)
    frame = Frame(image=image, time=0.0)
    motion = MotionVector(0.0, 0.0)
    with pytest.raises(InvalidInputError):
        search([frame], [motion], work_budget=True)
    with pytest.raises(InvalidInputError):
        search([frame], [motion], work_budget=1.5)
    with pytest.raises(InvalidInputError):
        search([frame], [motion], work_budget=-1)
