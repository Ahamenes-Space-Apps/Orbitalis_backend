"""Search implementation for shift-and-stack.

Purpose: Evaluate a grid of trial motions and return per-pixel best maps.
Inputs: Prepared aligned frames and a motion grid.
Outputs: ``SearchResult`` containing per-pixel best maps and optional diagnostics.
Called by: Callers of ``orbitalis_core.shiftstack.search``.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any

import numpy as np

from ..errors import check_not_all_nan
from .combining import _combine_prepared, combine
from .errors import InvalidInputError, WorkBudgetExceededError
from .models import Frame, MotionVector, SearchResult, ShiftCombineResult
from .shifting import _shift_image_array, _shift_variance_array, shift_image, shift_variance

DEFAULT_WORK_BUDGET = 50_000_000
SCORE_FLOAT32_RTOL = 1e-5
SCORE_FLOAT32_ATOL = 1e-6


def _validate_frames(frames: list[Frame], *, require_variance: bool = True) -> None:
    if not frames:
        raise InvalidInputError("frames must contain at least one frame")
    images = [np.asarray(frame.image) for frame in frames]
    for index, image in enumerate(images):
        if image.ndim != 2:
            raise InvalidInputError(f"frame {index} image must be two-dimensional")
        if np.iscomplexobj(image) or image.dtype.kind == "c":
            raise InvalidInputError(f"frame {index} image must be real-valued")
        if not np.issubdtype(image.dtype, np.number):
            raise InvalidInputError(f"frame {index} image must be numeric")
        if not np.all(np.isfinite(image) | np.isnan(image)):
            raise InvalidInputError(f"frame {index} image contains non-finite values")
    shape = images[0].shape
    if any(image.shape != shape for image in images):
        raise InvalidInputError("all frame images must have the same shape")

    has_variance = [frame.variance is not None for frame in frames]
    if require_variance and not all(has_variance):
        raise InvalidInputError("search requires a variance array for every frame")
    if any(has_variance) and not all(has_variance):
        raise InvalidInputError("variance must be provided for all frames or none")

    for index, frame in enumerate(frames):
        try:
            time = float(frame.time)
        except (TypeError, ValueError) as exc:
            raise InvalidInputError(f"frame {index} time must be numeric") from exc
        if not np.isfinite(time):
            raise InvalidInputError(f"frame {index} time must be finite")
        if frame.variance is not None:
            variance = np.asarray(frame.variance)
            if variance.shape != shape:
                raise InvalidInputError(f"frame {index} variance must match image shape")
            if np.iscomplexobj(variance) or variance.dtype.kind == "c":
                raise InvalidInputError(f"frame {index} variance must be real-valued")
            if not np.issubdtype(variance.dtype, np.number):
                raise InvalidInputError(f"frame {index} variance must be numeric")
            if not np.all(np.isfinite(variance) | np.isnan(variance)):
                raise InvalidInputError(f"frame {index} variance contains non-finite values")
            if np.any(np.isfinite(variance) & (variance < 0.0)):
                raise InvalidInputError(f"frame {index} variance must be non-negative")


def _validate_work_budget(work_budget: int | None) -> None:
    if work_budget is None:
        return
    if isinstance(work_budget, bool) or not isinstance(work_budget, int):
        raise InvalidInputError("work_budget must be an integer or None")
    if work_budget < 0:
        raise InvalidInputError("work_budget must be non-negative")


def _validate_min_coverage_fraction(value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float, np.integer, np.floating)):
        raise InvalidInputError("min_coverage_fraction must be numeric")
    value = float(value)
    if not np.isfinite(value):
        raise InvalidInputError("min_coverage_fraction must be finite")
    if value < 0.0 or value > 1.0:
        raise InvalidInputError("min_coverage_fraction must be within [0, 1]")
    return value


def _as_score_map(score: np.ndarray) -> np.ndarray:
    arr = np.asarray(score, dtype=np.float64)
    finite = np.isfinite(arr)
    if finite.any():
        max_abs = float(np.max(np.abs(arr[finite])))
        if max_abs <= float(np.finfo(np.float32).max):
            candidate = arr.astype(np.float32)
            if np.allclose(
                arr, candidate, rtol=SCORE_FLOAT32_RTOL, atol=SCORE_FLOAT32_ATOL, equal_nan=True
            ):
                return candidate
    # All-NaN or non-finite-only maps can still use float32 storage.
    if not finite.any():
        return arr.astype(np.float32)
    return arr


def _is_zero_motion(motion: MotionVector) -> bool:
    return motion.dx_px_per_day == 0.0 and motion.dy_px_per_day == 0.0


def search(
    frames: Iterable[Any],
    motion_grid: Iterable[Any],
    *,
    reference_time: float | None = None,
    work_budget: int | None = DEFAULT_WORK_BUDGET,
    min_coverage_fraction: float = 0.5,
    return_trial_maps: bool = False,
) -> SearchResult:
    """Evaluate every motion in ``motion_grid``.

    Variance is required for detection significance. ``motion_grid`` values must
    be ``MotionVector`` instances. Frames must be ``Frame`` instances.

    ``min_coverage_fraction`` is converted to a per-pixel minimum coverage count
    using ``ceil(min_coverage_fraction * number_of_frames)``. Pixels below this
    threshold cannot update the per-pixel best maps.

    Zero-motion trials are evaluated and retained when ``return_trial_maps`` is
    true, but they do not contribute to ``best_score_map`` or
    ``best_trial_index_map``.

    Memory use is reduced by default: full per-trial arrays are retained only
    when ``return_trial_maps=True``.

    Motion components are in pixels per day on the common image grid. The
    conversion from sky motion (arcsec/day, position angle east of north) is
    intentionally outside this module; SDD D-17 remains unresolved.
    """
    if not isinstance(frames, Iterable):
        raise InvalidInputError("frames must be an iterable of Frame instances")
    if not isinstance(motion_grid, Iterable):
        raise InvalidInputError("motion_grid must be an iterable of MotionVector instances")

    frame_list = list(frames)
    motion_list = list(motion_grid)
    if any(not isinstance(frame, Frame) for frame in frame_list):
        raise InvalidInputError("frames must contain Frame instances only")
    if any(not isinstance(motion, MotionVector) for motion in motion_list):
        raise InvalidInputError("motion_grid must contain MotionVector instances only")
    if not motion_list:
        raise InvalidInputError("motion_grid must contain at least one MotionVector")
    if all(_is_zero_motion(motion) for motion in motion_list):
        raise InvalidInputError("motion_grid must contain at least one non-zero motion hypothesis")

    _validate_frames(frame_list)
    min_coverage_fraction = _validate_min_coverage_fraction(min_coverage_fraction)
    _validate_work_budget(work_budget)

    if reference_time is None:
        reference_time = min(float(frame.time) for frame in frame_list)
    else:
        try:
            reference_time = float(reference_time)
        except (TypeError, ValueError) as exc:
            raise InvalidInputError("reference_time must be numeric") from exc
        if not np.isfinite(reference_time):
            raise InvalidInputError("reference_time must be finite")

    height, width = np.asarray(frame_list[0].image).shape
    work_estimate = len(motion_list) * len(frame_list) * height * width
    if work_budget is not None and work_estimate > work_budget:
        raise WorkBudgetExceededError(
            f"search work estimate {work_estimate} exceeds budget {work_budget}"
        )

    score_maps: list[np.ndarray] = []
    combined_images: list[np.ndarray] = []
    combined_variances: list[np.ndarray] = []
    coverage_maps: list[np.ndarray] = []

    best_score_map = np.full((height, width), -np.inf, dtype=np.float32)
    best_trial_index_map = np.full((height, width), -1, dtype=np.int64)
    best_coverage_map = np.full((height, width), -1, dtype=np.int64)
    min_coverage_count = math.ceil(min_coverage_fraction * len(frame_list))

    prepared_frames = []
    for frame in frame_list:
        image = np.array(frame.image, dtype=np.float64, copy=True)
        variance = (
            None
            if frame.variance is None
            else np.array(frame.variance, dtype=np.float64, copy=True)
        )
        prepared_frames.append((image, float(frame.time), variance))

    for trial_index, motion in enumerate(motion_list):
        aligned_images: list[np.ndarray] = []
        aligned_variances: list[np.ndarray] = []
        for image, time, variance in prepared_frames:
            dt = time - reference_time
            shift_y = -motion.dy_px_per_day * dt
            shift_x = -motion.dx_px_per_day * dt
            aligned_images.append(_shift_image_array(image, shift_y, shift_x))
            aligned_variances.append(_shift_variance_array(variance, shift_y, shift_x))

        combined, combined_variance, coverage = _combine_prepared(aligned_images, aligned_variances)

        coverage_fraction_valid = coverage >= min_coverage_count
        combined = np.where(coverage_fraction_valid, combined, np.nan)
        combined_variance = np.where(coverage_fraction_valid, combined_variance, np.nan)

        with np.errstate(divide="ignore", invalid="ignore"):
            safe_variance = np.where(combined_variance > 0.0, combined_variance, np.nan)
            raw_score = combined / np.sqrt(safe_variance)
        score = _as_score_map(raw_score)
        score = np.where(coverage_fraction_valid, score, np.nan)

        is_zero_motion = _is_zero_motion(motion)
        if not is_zero_motion:
            finite_score = np.isfinite(score)
            candidate_score = np.asarray(score)
            better = finite_score & (
                ~np.isfinite(best_score_map) | (candidate_score > best_score_map)
            )
            best_score_map = np.where(better, candidate_score, best_score_map)
            best_trial_index_map = np.where(better, trial_index, best_trial_index_map)
            best_coverage_map = np.where(better, coverage, best_coverage_map)

        if return_trial_maps:
            score_maps.append(np.asarray(score))
            combined_images.append(np.asarray(combined, dtype=np.float64))
            combined_variances.append(np.asarray(combined_variance, dtype=np.float64))
            coverage_maps.append(np.asarray(coverage))

        # Release temporary per-trial arrays when diagnostics are not requested.
        del (
            aligned_images,
            aligned_variances,
            combined,
            combined_variance,
            coverage,
            score,
            raw_score,
        )

    best_score_map = np.where(np.isfinite(best_score_map), best_score_map, np.nan)
    check_not_all_nan(best_score_map, name="search result")

    motion_tuple = tuple(motion_list)
    return SearchResult(
        motion_vectors=motion_tuple,
        reference_time=reference_time,
        best_score_map=best_score_map,
        best_trial_index_map=best_trial_index_map,
        best_coverage_map=best_coverage_map,
        work_estimate=work_estimate,
        min_coverage_fraction=min_coverage_fraction,
        score_maps=tuple(score_maps) if return_trial_maps else None,
        combined_images=tuple(combined_images) if return_trial_maps else None,
        combined_variances=tuple(combined_variances) if return_trial_maps else None,
        coverage_maps=tuple(coverage_maps) if return_trial_maps else None,
    )


def shift_and_combine(
    frames: Iterable[Any],
    vector: Any,
    *,
    reference_time: float | None = None,
    work_budget: int | None = DEFAULT_WORK_BUDGET,
) -> ShiftCombineResult:
    """Align and combine frames for a single motion vector."""
    if not isinstance(frames, Iterable):
        raise InvalidInputError("frames must be an iterable of Frame instances")
    if not isinstance(vector, MotionVector):
        raise InvalidInputError("vector must be a MotionVector instance")

    frame_list = list(frames)
    if any(not isinstance(frame, Frame) for frame in frame_list):
        raise InvalidInputError("frames must contain Frame instances only")
    _validate_frames(frame_list, require_variance=False)

    if reference_time is None:
        reference_time = min(float(frame.time) for frame in frame_list)
    else:
        try:
            reference_time = float(reference_time)
        except (TypeError, ValueError) as exc:
            raise InvalidInputError("reference_time must be numeric") from exc
        if not np.isfinite(reference_time):
            raise InvalidInputError("reference_time must be finite")

    _validate_work_budget(work_budget)
    height, width = np.asarray(frame_list[0].image).shape
    work_estimate = 1 * len(frame_list) * height * width
    if work_budget is not None and work_estimate > work_budget:
        raise WorkBudgetExceededError(
            f"search work estimate {work_estimate} exceeds budget {work_budget}"
        )

    prepared_frames = []
    for frame in frame_list:
        image = np.array(frame.image, dtype=np.float64, copy=True)
        variance = (
            None
            if frame.variance is None
            else np.array(frame.variance, dtype=np.float64, copy=True)
        )
        prepared_frames.append((image, float(frame.time), variance))

    motion = vector
    aligned_images: list[np.ndarray] = []
    aligned_variances: list[np.ndarray | None] = []
    for image, time, variance in prepared_frames:
        dt = time - reference_time
        shift_y = -motion.dy_px_per_day * dt
        shift_x = -motion.dx_px_per_day * dt
        aligned_images.append(shift_image(image, shift_y, shift_x))
        if variance is None:
            aligned_variances.append(None)
        else:
            aligned_variances.append(shift_variance(variance, shift_y, shift_x))

    combined, combined_variance, coverage = combine(aligned_images, aligned_variances)
    return ShiftCombineResult(
        combined=np.asarray(combined, dtype=np.float64),
        variance=None
        if combined_variance is None
        else np.asarray(combined_variance, dtype=np.float64),
        coverage=np.asarray(coverage),
        motion=motion,
        reference_time=reference_time,
    )


__all__ = ["DEFAULT_WORK_BUDGET", "search", "shift_and_combine"]
