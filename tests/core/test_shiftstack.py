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

from orbitalis_core.errors import CoreError, EmptyResultError
from orbitalis_core.shiftstack import (
    Frame,
    InvalidInputError,
    MotionVector,
    WorkBudgetExceededError,
    combine,
    search,
    shift_and_combine,
    shift_image,
    shift_variance,
)
from orbitalis_core.shiftstack.errors import ShiftStackError
from orbitalis_core.shiftstack.models import ShiftCombineResult


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
    edge = np.zeros((5, 5), dtype=float)
    edge[1, 4] = 10.0
    shifted_edge = shift_image(edge, 0.0, 1.0)
    assert not np.any(shifted_edge == 10.0)
    assert np.all(np.isnan(shifted_edge[:, 0]))


def test_negative_shift() -> None:
    image = np.zeros((5, 5), dtype=float)
    image[2, 3] = 7.0
    shifted = shift_image(image, 0.0, -1.0)
    assert shifted[2, 2] == 7.0


def test_subpixel_shift_consistent() -> None:
    image = np.zeros((5, 5), dtype=float)
    image[2, 2] = 1.0
    shifted = shift_image(image, 0.0, 0.5)
    assert shifted[2, 2] == pytest.approx(0.5)
    assert shifted[2, 3] == pytest.approx(0.5)


def test_nan_pixels_do_not_contaminate_shift() -> None:
    image = np.zeros((5, 5), dtype=float)
    image[2, 2] = 1.0
    image[2, 3] = np.nan
    shifted = shift_image(image, 0.0, 0.5)
    assert shifted[2, 2] == pytest.approx(0.5)
    assert np.isnan(shifted[2, 3])
    assert np.all(np.isnan(shifted[:, 0]))


def test_validity_aware_integer_shift_near_nan_and_boundary() -> None:
    image = np.zeros((5, 5), dtype=float)
    image[2, 2] = 1.0
    image[2, 3] = np.nan
    shifted = shift_image(image, 0.0, 1.0)
    # The valid source shifts into (2, 3) without using the NaN neighbor.
    assert shifted[2, 3] == 1.0
    assert shifted[2, 2] == 0.0
    assert np.all(np.isnan(shifted[:, 0]))


def test_validity_aware_subpixel_shift_near_boundary() -> None:
    image = np.zeros((5, 5), dtype=float)
    image[2, 2] = 1.0
    shifted = shift_image(image, 0.0, 0.5)
    assert shifted[2, 2] == pytest.approx(0.5)
    assert shifted[2, 3] == pytest.approx(0.5)
    assert np.all(np.isnan(shifted[:, 0]))


def test_valid_zero_pixels_preserved() -> None:
    image = np.zeros((4, 4), dtype=float)
    shifted = shift_image(image, 0.3, -0.2)
    assert np.all((shifted == 0.0) | np.isnan(shifted))


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
    var = np.array([[np.nan, np.nan]])
    combined, variance, coverage = combine([image, image.copy()], [var, var.copy()])
    assert np.all(np.isnan(combined))
    assert np.all(np.isnan(variance))
    assert np.array_equal(coverage, np.array([[0, 0]]))


def test_motion_recovery() -> None:
    size = 15
    frames = []
    velocity = (2.0, 1.0)
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
    peak = np.unravel_index(np.nanargmax(result.best_score_map), result.best_score_map.shape)
    assert result.best_trial_index_map[peak] == 2
    assert 0 not in result.best_trial_index_map[result.best_trial_index_map >= 0]
    assert result.work_estimate == 4 * 3 * size * size


def test_zero_motion_does_not_update_best_maps() -> None:
    size = 9
    frames = []
    for t in range(3):
        image = np.zeros((size, size), dtype=float)
        image[4, 4] = 8.0
        frames.append(Frame(image=image, time=float(t), variance=np.ones((size, size))))
    result = search(frames, [MotionVector(0.0, 0.0), MotionVector(1.0, 0.0)])
    assert 0 not in result.best_trial_index_map[result.best_trial_index_map >= 0]
    assert np.all(np.isnan(result.best_score_map) | (result.best_trial_index_map != 0))


def test_shift_and_combine_single_motion() -> None:
    image = np.zeros((5, 5), dtype=float)
    image[2, 2] = 4.0
    frame = Frame(image=image, time=0.0)
    result = shift_and_combine([frame], MotionVector(1.0, 0.0))
    assert np.array_equal(result.combined, image)
    assert result.variance is None
    assert result.coverage[2, 2] == 1


def test_empty_motion_grid_raises() -> None:
    image = np.zeros((2, 2), dtype=float)
    frame = Frame(image=image, time=0.0, variance=np.ones((2, 2)))
    with pytest.raises(InvalidInputError):
        search([frame], [])


def test_zero_motion_only_grid_raises() -> None:
    image = np.zeros((2, 2), dtype=float)
    frame = Frame(image=image, time=0.0, variance=np.ones((2, 2)))
    with pytest.raises(InvalidInputError):
        search([frame], [MotionVector(0.0, 0.0)])


def test_mixed_zero_and_nonzero_motion_allowed() -> None:
    image = np.zeros((3, 3), dtype=float)
    image[1, 1] = 1.0
    frame = Frame(image=image, time=0.0, variance=np.ones((3, 3)))
    result = search([frame], [MotionVector(0.0, 0.0), MotionVector(1.0, 0.0)])
    assert 0 not in result.best_trial_index_map[result.best_trial_index_map >= 0]


def test_empty_search_result_raises() -> None:
    image = np.full((2, 2), np.nan, dtype=float)
    frame = Frame(image=image, time=0.0, variance=np.full((2, 2), np.nan, dtype=float))
    with pytest.raises(EmptyResultError):
        search([frame], [MotionVector(1.0, 0.0)])


def test_partially_nan_search_result_preserved() -> None:
    image = np.zeros((2, 2), dtype=float)
    image[0, 0] = np.nan
    variance = np.ones((2, 2), dtype=float)
    frame = Frame(image=image, time=0.0, variance=variance)
    result = search([frame], [MotionVector(1.0, 0.0)], min_coverage_fraction=1.0)
    assert np.isnan(result.best_score_map[0, 0])
    assert np.isfinite(result.best_score_map[1, 1])


def test_normal_valid_search_result() -> None:
    image = np.zeros((3, 3), dtype=float)
    image[1, 1] = 4.0
    frame = Frame(image=image, time=0.0, variance=np.ones((3, 3)))
    result = search([frame], [MotionVector(1.0, 0.0)])
    peak = np.unravel_index(np.nanargmax(result.best_score_map), result.best_score_map.shape)
    assert result.best_trial_index_map[peak] == 0


def test_empty_frames_raises() -> None:
    with pytest.raises(InvalidInputError):
        search([], [MotionVector(0.0, 0.0)])


def test_work_budget_rejects_excessive_search() -> None:
    image = np.zeros((4, 4), dtype=float)
    frame = Frame(image=image, time=0.0, variance=np.ones((4, 4)))
    with pytest.raises(WorkBudgetExceededError):
        search([frame], [MotionVector(1.0, 0.0)], work_budget=0)


def test_different_image_shapes_raise() -> None:
    a = Frame(image=np.zeros((3, 3)), time=0.0, variance=np.ones((3, 3)))
    b = Frame(image=np.zeros((3, 4)), time=1.0, variance=np.ones((3, 4)))
    with pytest.raises(InvalidInputError):
        search([a, b], [MotionVector(0.0, 0.0)])


def test_nonfinite_time_raises() -> None:
    frame = Frame(image=np.zeros((2, 2)), time=float("nan"), variance=np.ones((2, 2)))
    with pytest.raises(InvalidInputError):
        search([frame], [MotionVector(0.0, 0.0)])


def test_input_not_mutated() -> None:
    image = np.array([[1.0, 2.0], [3.0, 4.0]])
    original = image.copy()
    frame = Frame(image=image, time=0.0, variance=np.ones((2, 2)))
    _ = shift_image(image, 1.0, 1.0)
    _ = search([frame], [MotionVector(1.0, 0.0)])
    assert np.array_equal(image, original)


def test_deterministic() -> None:
    image = np.zeros((4, 4), dtype=float)
    image[1, 1] = 5.0
    frame = Frame(image=image, time=0.0, variance=np.ones((4, 4)))
    r1 = search([frame], [MotionVector(1.0, 0.0)])
    r2 = search([frame], [MotionVector(1.0, 0.0)])
    assert np.array_equal(r1.best_score_map, r2.best_score_map, equal_nan=True)
    assert np.array_equal(r1.best_trial_index_map, r2.best_trial_index_map)


def test_tuple_frame_and_motion_inputs_rejected() -> None:
    image = np.zeros((3, 3), dtype=float)
    image[1, 1] = 2.0
    frames = [(image, 0.0)]
    motions = [(0.0, 0.0)]
    with pytest.raises(InvalidInputError):
        search(frames, motions)


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
    result = search([frame], [MotionVector(1.0, 0.0)], return_trial_maps=True)
    assert result.combined_variances is not None
    assert result.combined_variances[0][1, 1] == pytest.approx(4.0)
    assert result.score_maps is not None
    assert result.score_maps[0][1, 1] == pytest.approx(3.0)


def test_search_requires_variance() -> None:
    image = np.array([[1.0, 2.0], [3.0, 4.0]])
    frame = Frame(image=image, time=0.0)
    with pytest.raises(InvalidInputError):
        search([frame], [MotionVector(0.0, 0.0)])


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
    result = search(frames, grid, return_trial_maps=True)
    peak = np.unravel_index(np.nanargmax(result.best_score_map), result.best_score_map.shape)
    assert result.best_trial_index_map[peak] == 1
    assert 0 not in result.best_trial_index_map[result.best_trial_index_map >= 0]
    assert result.score_maps is not None


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


def test_complex_image_rejected() -> None:
    image = np.zeros((2, 2), dtype=complex)
    with pytest.raises(InvalidInputError):
        shift_image(image, 0.0, 0.0)
    with pytest.raises(InvalidInputError):
        combine([image, image])
    frame = Frame(image=image, time=0.0, variance=np.ones((2, 2)))
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
    assert combined[0, 0] == pytest.approx(5.0)
    assert result_variance[0, 0] == 0.0
    assert np.isnan(combined[0, 1])
    assert np.isnan(result_variance[0, 1])
    np.testing.assert_array_equal(coverage, np.array([[2, 0]]))


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


def test_min_coverage_threshold() -> None:
    image = np.zeros((2, 2), dtype=float)
    image[0, 0] = np.nan
    variance = np.ones((2, 2), dtype=float)
    frames = [
        Frame(image=image.copy(), time=0.0, variance=variance),
        Frame(image=image.copy(), time=1.0, variance=variance),
    ]
    result = search(frames, [MotionVector(1.0, 0.0)], min_coverage_fraction=1.0)
    assert np.isnan(result.best_score_map[0, 0])
    assert result.best_trial_index_map[0, 0] == -1
    assert result.best_coverage_map[0, 0] == -1


def test_canonical_api_only() -> None:
    import orbitalis_core.shiftstack.models as models

    aliases = (
        "ShiftAndCombineResult",
        "CombinedResult",
        "StackResult",
        "SearchResults",
        "ShiftStackResult",
    )
    for alias in aliases:
        assert not hasattr(models, alias)
    assert not hasattr(Frame, "id")
    assert not hasattr(MotionVector, "dx")
    assert not hasattr(MotionVector, "dy")
    assert not hasattr(MotionVector, "vx")
    assert not hasattr(MotionVector, "vy")
    assert not hasattr(ShiftCombineResult, "combined_image")
    assert not hasattr(ShiftCombineResult, "combined_variance")


def test_float32_score_maps_when_safe() -> None:
    image = np.zeros((3, 3), dtype=float)
    image[1, 1] = 6.0
    frame = Frame(image=image, time=0.0, variance=np.full((3, 3), 4.0))
    result = search([frame], [MotionVector(1.0, 0.0)], return_trial_maps=False)
    assert result.best_score_map.dtype == np.float32


def test_work_budget_validation() -> None:
    image = np.zeros((2, 2), dtype=float)
    frame = Frame(image=image, time=0.0, variance=np.ones((2, 2)))
    motion = MotionVector(0.0, 0.0)
    with pytest.raises(InvalidInputError):
        search([frame], [motion], work_budget=True)
    with pytest.raises(InvalidInputError):
        search([frame], [motion], work_budget=1.5)
    with pytest.raises(InvalidInputError):
        search([frame], [motion], work_budget=-1)


def test_shift_variance_integer_preserves_value() -> None:
    variance = np.zeros((5, 5), dtype=float)
    variance[2, 2] = 4.0
    shifted = shift_variance(variance, 0.0, 1.0)
    assert shifted[2, 3] == pytest.approx(4.0)
    assert np.all(np.isnan(shifted[:, 0]))


def test_shift_variance_subpixel_squared_weights() -> None:
    variance = np.zeros((5, 5), dtype=float)
    variance[2, 2] = 4.0
    variance[2, 3] = 4.0
    shifted = shift_variance(variance, 0.0, 0.5)
    assert shifted[2, 2] == pytest.approx(1.0)
    assert shifted[2, 3] == pytest.approx(2.0)
    assert np.all(np.isnan(shifted[:, 0]))


def test_shift_variance_equal_independent_variances() -> None:
    variance = np.full((5, 5), 4.0, dtype=float)
    shifted = shift_variance(variance, 0.0, 0.5)
    assert shifted[2, 2] == pytest.approx(2.0)
    assert shifted[2, 3] == pytest.approx(2.0)


def test_shift_variance_nan_excluded() -> None:
    variance = np.zeros((5, 5), dtype=float)
    variance[2, 2] = 4.0
    variance[2, 3] = np.nan
    shifted = shift_variance(variance, 0.0, 1.0)
    assert shifted[2, 3] == pytest.approx(4.0)
    assert np.isnan(shifted[2, 4])


def test_shift_variance_insufficient_support_is_nan() -> None:
    variance = np.full((5, 5), np.nan, dtype=float)
    variance[2, 2] = 4.0
    shifted = shift_variance(variance, 0.0, 0.5)
    assert np.isnan(shifted[2, 2])
    assert np.isnan(shifted[2, 3])


def test_shift_variance_zero_image_pixels_remain_valid() -> None:
    image = np.zeros((4, 4), dtype=float)
    shifted_image = shift_image(image, 0.3, -0.2)
    assert np.all((shifted_image == 0.0) | np.isnan(shifted_image))


def test_shift_variance_validity_agrees_with_image() -> None:
    image = np.zeros((4, 4), dtype=float)
    image[1, 1] = 1.0
    variance = np.ones((4, 4), dtype=float)
    image[2, 2] = np.nan
    variance[2, 2] = np.nan
    shifted_image = shift_image(image, 0.0, 0.0)
    shifted_variance = shift_variance(variance, 0.0, 0.0)
    image_valid = np.isfinite(shifted_image)
    variance_valid = np.isfinite(shifted_variance)
    assert np.array_equal(image_valid, variance_valid)


def test_shift_variance_boundary_invalid() -> None:
    variance = np.zeros((4, 4), dtype=float)
    variance[0, 0] = 4.0
    shifted = shift_variance(variance, -1.0, 0.0)
    assert not np.any(shifted == 4.0)


def test_shift_variance_subpixel_near_nan() -> None:
    variance = np.zeros((5, 5), dtype=float)
    variance[2, 2] = 4.0
    variance[2, 3] = np.nan
    shifted = shift_variance(variance, 0.0, 0.5)
    assert shifted[2, 2] == pytest.approx(1.0)
    assert np.isnan(shifted[2, 3])


def test_shift_variance_zero_variance_is_valid() -> None:
    variance = np.zeros((4, 4), dtype=float)
    shifted = shift_variance(variance, 0.0, 0.0)
    assert np.all(shifted == 0.0)


def test_shift_variance_zero_variance_contributes_zero() -> None:
    variance = np.zeros((5, 5), dtype=float)
    variance[2, 2] = 4.0
    variance[2, 3] = 0.0
    shifted = shift_variance(variance, 0.0, 0.5)
    assert shifted[2, 3] == pytest.approx(1.0)
    assert np.all(np.isnan(shifted[:, 0]))


def test_shift_variance_zero_and_nan_validity_agree() -> None:
    image = np.zeros((4, 4), dtype=float)
    image[1, 1] = 1.0
    variance = np.zeros((4, 4), dtype=float)
    image[2, 2] = np.nan
    variance[2, 2] = np.nan
    shifted_image = shift_image(image, 0.0, 0.0)
    shifted_variance = shift_variance(variance, 0.0, 0.0)
    assert np.array_equal(np.isfinite(shifted_image), np.isfinite(shifted_variance))


def test_zero_variance_single_determines_combined_value() -> None:
    image = np.array([[7.0]])
    variance = np.array([[0.0]])
    combined, result_variance, coverage = combine([image], [variance])
    assert combined[0, 0] == pytest.approx(7.0)
    assert result_variance[0, 0] == 0.0
    assert coverage[0, 0] == 1


def test_zero_variance_multiple_uses_arithmetic_mean() -> None:
    images = [np.array([[4.0]]), np.array([[8.0]])]
    variances = [np.array([[0.0]]), np.array([[0.0]])]
    combined, result_variance, coverage = combine(images, variances)
    assert combined[0, 0] == pytest.approx(6.0)
    assert result_variance[0, 0] == 0.0
    assert coverage[0, 0] == 2


def test_zero_variance_excludes_positive_variance() -> None:
    images = [np.array([[10.0]]), np.array([[100.0]])]
    variances = [np.array([[0.0]]), np.array([[1.0]])]
    combined, result_variance, coverage = combine(images, variances)
    assert combined[0, 0] == pytest.approx(10.0)
    assert result_variance[0, 0] == 0.0
    assert coverage[0, 0] == 1


def test_zero_variance_coverage_counts_only_zero() -> None:
    images = [np.array([[1.0]]), np.array([[2.0]]), np.array([[3.0]])]
    variances = [np.array([[0.0]]), np.array([[1.0]]), np.array([[0.0]])]
    combined, result_variance, coverage = combine(images, variances)
    assert combined[0, 0] == pytest.approx(2.0)
    assert result_variance[0, 0] == 0.0
    assert coverage[0, 0] == 2


def test_positive_variance_still_weighted() -> None:
    image = np.array([[5.0]])
    variance = np.array([[4.0]])
    combined, result_variance, coverage = combine(
        [image, image.copy()], [variance, variance.copy()]
    )
    assert combined[0, 0] == pytest.approx(5.0)
    assert result_variance[0, 0] == pytest.approx(2.0)
    assert coverage[0, 0] == 2


def test_negative_variance_raises() -> None:
    image = np.array([[1.0]])
    variance = np.array([[-1.0]])
    with pytest.raises(InvalidInputError):
        combine([image], [variance])


def test_nan_image_and_variance_excluded() -> None:
    images = [np.array([[np.nan]]), np.array([[5.0]])]
    variances = [np.array([[0.0]]), np.array([[np.nan]])]
    combined, result_variance, coverage = combine(images, variances)
    assert np.isnan(combined[0, 0])
    assert np.isnan(result_variance[0, 0])
    assert coverage[0, 0] == 0


def test_no_valid_contributors_nan() -> None:
    image = np.array([[1.0]])
    variance = np.array([[np.nan]])
    combined, result_variance, coverage = combine([image], [variance])
    assert np.isnan(combined[0, 0])
    assert np.isnan(result_variance[0, 0])
    assert coverage[0, 0] == 0


def test_float64_score_map_when_score_exceeds_float32_range() -> None:
    image = np.zeros((3, 3), dtype=float)
    image[1, 1] = 1e39
    frame = Frame(image=image, time=0.0, variance=np.ones((3, 3), dtype=float))
    result = search([frame], [MotionVector(1.0, 0.0)], return_trial_maps=False)
    assert result.best_score_map.dtype == np.float64
    peak = np.unravel_index(np.nanargmax(result.best_score_map), result.best_score_map.shape)
    assert np.isfinite(result.best_score_map[peak])
    np.testing.assert_allclose(result.best_score_map[peak], 1e39)


def test_stationary_source_interference_in_nonzero_trials() -> None:
    size = 31
    frames = []
    for t in range(5):
        image = np.zeros((size, size), dtype=float)
        image[size // 2, size // 2] = 100.0
        image[size // 2, 5 + t] += 5.0
        frames.append(Frame(image=image, time=float(t), variance=np.ones((size, size))))

    result = search(
        frames,
        [MotionVector(0.0, 0.0), MotionVector(1.0, 0.0)],
        return_trial_maps=True,
    )
    assert result.score_maps is not None
    zero_score = result.score_maps[0]
    moving_score = result.score_maps[1]
    stationary_center = (size // 2, size // 2)
    moving_location = (size // 2, 5)

    # The stationary source is much stronger than the moving source.
    assert zero_score[stationary_center] > moving_score[moving_location]
    # A stationary-source residual remains in the non-zero-motion trial.
    assert np.isfinite(moving_score[stationary_center])
    assert moving_score[stationary_center] > moving_score[moving_location]
    # Excluding the zero-motion trial does not remove that residual from the
    # best-moving-score map.
    best_peak = np.unravel_index(np.nanargmax(result.best_score_map), result.best_score_map.shape)
    assert best_peak == (size // 2, 11)
    assert result.best_trial_index_map[best_peak] == 1
    assert 0 not in result.best_trial_index_map[result.best_trial_index_map >= 0]


def test_coverage_odd_frame_count_default_threshold() -> None:
    image = np.zeros((2, 2), dtype=float)
    image[0, 0] = np.nan
    variance = np.ones((2, 2), dtype=float)
    frames = [
        Frame(image=image.copy(), time=0.0, variance=variance),
        Frame(image=np.zeros((2, 2)), time=1.0, variance=variance),
        Frame(image=np.zeros((2, 2)), time=2.0, variance=variance),
    ]
    motion_grid = [MotionVector(0.0, 0.0), MotionVector(1.0, 0.0)]
    result = search(frames, motion_grid, return_trial_maps=True)
    assert result.score_maps is not None
    # ceil(0.5 * 3) == 2; the NaN pixel has enough coverage in the zero trial.
    assert np.isfinite(result.score_maps[0][0, 0])


def test_coverage_threshold_exact_and_above() -> None:
    image = np.zeros((3, 3), dtype=float)
    image[1, 1] = 1.0
    variance = np.ones((3, 3), dtype=float)
    frames = [Frame(image=image.copy(), time=float(t), variance=variance) for t in range(4)]
    frames[2].image[1, 1] = np.nan
    frames[3].image[1, 1] = np.nan
    motion_grid = [MotionVector(0.0, 0.0), MotionVector(0.1, 0.0)]
    result = search(frames, motion_grid, min_coverage_fraction=0.5, return_trial_maps=True)
    assert result.score_maps is not None
    # ceil(0.5 * 4) == 2; coverage is exactly 2.
    assert np.isfinite(result.score_maps[0][1, 1])

    result_strict = search(frames, motion_grid, min_coverage_fraction=0.75, return_trial_maps=True)
    assert result_strict.score_maps is not None
    # ceil(0.75 * 4) == 3; coverage 2 is below the threshold.
    assert np.isnan(result_strict.score_maps[0][1, 1])


def test_coverage_partially_nan_observations() -> None:
    image = np.zeros((2, 2), dtype=float)
    variance = np.ones((2, 2), dtype=float)
    frames = [
        Frame(image=image, time=0.0, variance=variance),
        Frame(image=np.full((2, 2), np.nan), time=1.0, variance=variance),
    ]
    with pytest.raises(EmptyResultError):
        search(frames, [MotionVector(1.0, 0.0)], min_coverage_fraction=1.0)


def test_motion_vector_small_nonzero_not_zero() -> None:
    image = np.zeros((3, 3), dtype=float)
    image[1, 1] = 1.0
    frame = Frame(image=image, time=0.0, variance=np.ones((3, 3)))
    result = search([frame], [MotionVector(1e-12, -1e-12)])
    peak = np.unravel_index(np.nanargmax(result.best_score_map), result.best_score_map.shape)
    assert result.best_trial_index_map[peak] == 0


def test_motion_vector_signs() -> None:
    image = np.zeros((5, 5), dtype=float)
    image[2, 2] = 1.0
    shifted_positive = shift_image(image, 1.0, 1.0)
    shifted_negative = shift_image(image, -1.0, -1.0)
    assert shifted_positive[3, 3] == 1.0
    assert shifted_negative[1, 1] == 1.0


def test_reference_time_and_timestamps() -> None:
    image = np.zeros((3, 3), dtype=float)
    image[1, 1] = 1.0
    frames = [
        Frame(image=image, time=10.0, variance=np.ones((3, 3))),
        Frame(image=image, time=20.0, variance=np.ones((3, 3))),
    ]
    result = search(frames, [MotionVector(1.0, 0.0)])
    assert result.reference_time == 10.0
    assert np.isfinite(result.best_score_map[1, 1])


def test_trial_maps_and_float64_promotion() -> None:
    image = np.zeros((3, 3), dtype=float)
    image[1, 1] = 1e39
    frame = Frame(image=image, time=0.0, variance=np.ones((3, 3)))
    result = search([frame], [MotionVector(1.0, 0.0)], return_trial_maps=True)
    assert result.score_maps is not None
    assert result.score_maps[0].dtype == np.float64
    assert result.best_score_map.dtype == np.float64


def test_core_error_base() -> None:
    assert issubclass(InvalidInputError, CoreError)
    assert issubclass(WorkBudgetExceededError, ShiftStackError)
    assert issubclass(WorkBudgetExceededError, CoreError)
    err = InvalidInputError("bad")
    assert err.code is None
    budget_err = WorkBudgetExceededError("too big")
    assert budget_err.code == "ORB-RS-003"
