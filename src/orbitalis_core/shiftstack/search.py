"""Search implementation for shift-and-stack.

Purpose: Evaluate a grid of trial motions and return score maps.
Inputs: Prepared aligned frames and a motion grid.
Outputs: ``SearchResult`` containing score maps and supporting products.
Called by: Callers of ``orbitalis_core.shiftstack.search``.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import numpy as np

from .combining import combine
from .errors import InvalidInputError, WorkBudgetExceededError
from .models import Frame, SearchResult, ShiftCombineResult, _as_frame, _as_motion
from .shifting import shift_image

DEFAULT_WORK_BUDGET = 2_000_000_000


def _validate_frames(frames: list[Frame]) -> None:
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


def search(
    frames: Iterable[Any],
    motion_grid: Iterable[Any],
    *,
    reference_time: float | None = None,
    work_budget: int | None = DEFAULT_WORK_BUDGET,
) -> SearchResult:
    """Evaluate every motion in ``motion_grid``.

    Frames are assumed to be already aligned to a common grid. ``motion_grid``
    values may be ``MotionVector`` instances, two-value sequences, mappings, or
    objects exposing ``dx``/``dy`` (or ``dx_px_per_day``/``dy_px_per_day``).

    When variance is available, each score map is ``combined / sqrt(combined_variance)``.
    Without variance, the score map is the combined image and is not a
    signal-to-noise ratio.

    The work estimate is ``trials * frames * height * width``. If it exceeds
    ``work_budget`` (default 2e9), ``WorkBudgetExceededError`` is raised before
    any expensive shifting. Pass ``work_budget=None`` to disable the check.

    Memory use scales with ``trials * height * width`` for score maps plus the
    stored combined images, variances, and coverage maps. The work budget bounds
    computation but not output memory; callers should keep motion grids and frame
    sizes bounded.
    """
    try:
        frame_list = [_as_frame(value) for value in frames]
    except Exception as exc:  # noqa: BLE001 - convert to domain error
        if isinstance(exc, InvalidInputError):
            raise
        raise InvalidInputError("frames must be an iterable of frame-like objects") from exc
    _validate_frames(frame_list)

    try:
        motion_list = [_as_motion(value) for value in motion_grid]
    except Exception as exc:  # noqa: BLE001 - convert to domain error
        if isinstance(exc, InvalidInputError):
            raise
        raise InvalidInputError("motion_grid must be an iterable of motion-like values") from exc

    if reference_time is None:
        reference_time = min(float(frame.time) for frame in frame_list)
    else:
        try:
            reference_time = float(reference_time)
        except (TypeError, ValueError) as exc:
            raise InvalidInputError("reference_time must be numeric") from exc
        if not np.isfinite(reference_time):
            raise InvalidInputError("reference_time must be finite")

    if work_budget is not None:
        if isinstance(work_budget, bool) or not isinstance(work_budget, int):
            raise InvalidInputError("work_budget must be an integer or None")
        if work_budget < 0:
            raise InvalidInputError("work_budget must be non-negative")

    height, width = np.asarray(frame_list[0].image).shape
    work_estimate = len(motion_list) * len(frame_list) * height * width
    if work_budget is not None and work_estimate > work_budget:
        raise WorkBudgetExceededError(
            f"search work estimate {work_estimate} exceeds budget {work_budget}"
        )

    score_maps: list[np.ndarray] = []
    combined_images: list[np.ndarray] = []
    combined_variances: list[np.ndarray | None] = []
    coverage_maps: list[np.ndarray] = []

    for motion in motion_list:
        aligned_images: list[np.ndarray] = []
        aligned_variances: list[np.ndarray | None] = []
        for frame in frame_list:
            dt = float(frame.time) - reference_time
            shift_y = -motion.dy_px_per_day * dt
            shift_x = -motion.dx_px_per_day * dt
            aligned_images.append(shift_image(frame.image, shift_y, shift_x))
            if frame.variance is None:
                aligned_variances.append(None)
            else:
                aligned_variances.append(shift_image(frame.variance, shift_y, shift_x))

        has_variance = all(v is not None for v in aligned_variances)
        variance_arg = aligned_variances if has_variance else None
        combined, combined_variance, coverage = combine(aligned_images, variance_arg)

        if combined_variance is None:
            score = np.array(combined, dtype=np.float64, copy=True)
        else:
            with np.errstate(divide="ignore", invalid="ignore"):
                safe_variance = np.where(combined_variance > 0.0, combined_variance, np.nan)
                score = combined / np.sqrt(safe_variance)

        score_maps.append(np.asarray(score, dtype=np.float64))
        combined_images.append(np.asarray(combined, dtype=np.float64))
        combined_variances.append(
            None if combined_variance is None else np.asarray(combined_variance, dtype=np.float64)
        )
        coverage_maps.append(np.asarray(coverage))

    motion_tuple = tuple(motion_list)
    best_index: int | None = None
    best_value = -np.inf
    for index, score_map in enumerate(score_maps):
        if score_map.size == 0 or not np.isfinite(score_map).any():
            continue
        value = float(np.nanmax(score_map))
        if value > best_value:
            best_value = value
            best_index = index

    return SearchResult(
        motion_vectors=motion_tuple,
        reference_time=reference_time,
        score_maps=tuple(score_maps),
        combined_images=tuple(combined_images),
        combined_variances=tuple(combined_variances),
        coverage_maps=tuple(coverage_maps),
        work_estimate=work_estimate,
        best_index=best_index,
    )


def shift_and_combine(
    frames: Iterable[Any],
    vector: Any,
    *,
    reference_time: float | None = None,
    work_budget: int | None = DEFAULT_WORK_BUDGET,
) -> ShiftCombineResult:
    """Align and combine frames for a single motion vector."""
    result = search(frames, [vector], reference_time=reference_time, work_budget=work_budget)
    if not result.combined_images:
        raise InvalidInputError("no combined result was produced")
    return ShiftCombineResult(
        combined=result.combined_images[0],
        variance=result.combined_variances[0],
        coverage=result.coverage_maps[0],
        motion=result.motion_vectors[0],
        reference_time=result.reference_time,
    )


__all__ = ["DEFAULT_WORK_BUDGET", "search", "shift_and_combine"]
