"""Combination helpers for shift-and-stack.

Purpose: NaN-aware combination of aligned images, with optional inverse-variance
weighting and coverage counting.
Inputs: Sequences of two-dimensional arrays and optional variance arrays.
Outputs: Combined image, combined variance, and coverage arrays.
Called by: orbitalis_core.shiftstack.search and callers.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np

from .errors import InvalidInputError


def _as_float_image(image: Any) -> np.ndarray:
    arr = np.asarray(image)
    if arr.ndim != 2:
        raise InvalidInputError("image must be a two-dimensional array")
    if np.iscomplexobj(arr) or arr.dtype.kind == "c":
        raise InvalidInputError("image must be real-valued")
    if not np.issubdtype(arr.dtype, np.number):
        raise InvalidInputError("image must be a numeric array")
    if not np.all(np.isfinite(arr) | np.isnan(arr)):
        raise InvalidInputError("image may contain only finite values or NaN")
    return np.array(arr, dtype=np.float64, copy=True)


def _as_variance(variance: Any, shape: tuple[int, int]) -> np.ndarray:
    arr = np.asarray(variance)
    if arr.shape != shape:
        raise InvalidInputError("variance must have the same shape as the image")
    if np.iscomplexobj(arr) or arr.dtype.kind == "c":
        raise InvalidInputError("variance must be real-valued")
    if not np.issubdtype(arr.dtype, np.number):
        raise InvalidInputError("variance must be a numeric array")
    if not np.all(np.isfinite(arr) | np.isnan(arr)):
        raise InvalidInputError("variance may contain only finite values or NaN")
    if np.any(np.isfinite(arr) & (arr < 0.0)):
        raise InvalidInputError("variance must be non-negative")
    return np.array(arr, dtype=np.float64, copy=True)


def _combine_prepared(
    images: list[np.ndarray],
    variances: list[np.ndarray] | None,
) -> tuple[np.ndarray, np.ndarray | None, np.ndarray]:
    """Combine already validated float64 arrays.

    This helper performs no validation or dtype conversion. ``images`` must be
    non-empty, same-shaped, finite-or-NaN float64 arrays. ``variances``, when
    not None, must match in number and shape and contain finite-or-NaN
    non-negative values.
    """
    if len(images) == 0:
        raise InvalidInputError("at least one image is required for combination")
    shape = images[0].shape
    if any(image.shape != shape for image in images):
        raise InvalidInputError("all images must have the same shape")

    stack = np.stack(images, axis=0)
    valid_image = np.isfinite(stack)

    if variances is None:
        coverage = valid_image.sum(axis=0).astype(np.int64)
        combined = np.zeros(shape, dtype=np.float64)
        count = np.zeros(shape, dtype=np.float64)
        for index in range(stack.shape[0]):
            value = stack[index]
            valid = valid_image[index]
            new_count = count + np.where(valid, 1.0, 0.0)
            with np.errstate(divide="ignore", invalid="ignore"):
                old_fraction = np.where(
                    valid & (new_count > 0.0),
                    count / np.where(new_count > 0.0, new_count, 1.0),
                    0.0,
                )
                new_fraction = np.where(
                    valid & (new_count > 0.0),
                    1.0 / np.where(new_count > 0.0, new_count, 1.0),
                    0.0,
                )
                updated_mean = old_fraction * combined + new_fraction * value
            combined = np.where(valid & (new_count > 0.0), updated_mean, combined)
            count = new_count
        has_contributors = count > 0.0
        combined = np.where(has_contributors, combined, np.nan)
        return combined, None, coverage

    variance_stack = np.stack(variances, axis=0)
    finite_variance = np.isfinite(variance_stack)
    zero_variance = finite_variance & (variance_stack == 0.0)
    positive_variance = finite_variance & (variance_stack > 0.0)
    zero_contributors = valid_image & zero_variance
    positive_contributors = valid_image & positive_variance
    zero_count = zero_contributors.sum(axis=0).astype(np.int64)

    zero_combined = np.zeros(shape, dtype=np.float64)
    zero_total_count = np.zeros(shape, dtype=np.float64)
    for index in range(stack.shape[0]):
        valid = zero_contributors[index]
        value = stack[index]
        new_count = zero_total_count + np.where(valid, 1.0, 0.0)
        with np.errstate(divide="ignore", invalid="ignore"):
            old_fraction = np.where(
                valid & (new_count > 0.0),
                zero_total_count / np.where(new_count > 0.0, new_count, 1.0),
                0.0,
            )
            new_fraction = np.where(
                valid & (new_count > 0.0),
                1.0 / np.where(new_count > 0.0, new_count, 1.0),
                0.0,
            )
            updated_mean = old_fraction * zero_combined + new_fraction * value
        zero_combined = np.where(valid & (new_count > 0.0), updated_mean, zero_combined)
        zero_total_count = new_count

    has_zero = zero_total_count > 0.0
    zero_combined = np.where(has_zero, zero_combined, np.nan)
    zero_variance_result = np.where(has_zero, 0.0, np.nan)

    masked_positive_contributors = np.where(has_zero[None, ...], False, positive_contributors)
    positive_coverage = masked_positive_contributors.sum(axis=0).astype(np.int64)

    masked_variance_stack = np.where(masked_positive_contributors, variance_stack, np.inf)
    v_min = masked_variance_stack.min(axis=0)
    has_positive = masked_positive_contributors.any(axis=0)
    safe_v_min = np.where(has_positive, v_min, 1.0)
    relative_weights = np.where(
        masked_positive_contributors,
        safe_v_min / np.where(masked_positive_contributors, variance_stack, 1.0),
        0.0,
    )

    positive_combined = np.zeros(shape, dtype=np.float64)
    total_relative_weight = np.zeros(shape, dtype=np.float64)
    for index in range(stack.shape[0]):
        weight = relative_weights[index]
        value = stack[index]
        valid = masked_positive_contributors[index]
        new_total = total_relative_weight + np.where(valid, weight, 0.0)
        with np.errstate(divide="ignore", invalid="ignore"):
            old_fraction = np.where(
                valid & (new_total > 0.0),
                total_relative_weight / np.where(new_total > 0.0, new_total, 1.0),
                0.0,
            )
            new_fraction = np.where(
                valid & (new_total > 0.0),
                weight / np.where(new_total > 0.0, new_total, 1.0),
                0.0,
            )
            updated_mean = old_fraction * positive_combined + new_fraction * value
        positive_combined = np.where(valid & (new_total > 0.0), updated_mean, positive_combined)
        total_relative_weight = new_total

    has_positive_contributors = total_relative_weight > 0.0
    safe_total_relative_weight = np.where(has_positive_contributors, total_relative_weight, 1.0)
    positive_combined = np.where(has_positive_contributors, positive_combined, np.nan)
    positive_variance = np.where(
        has_positive_contributors,
        safe_v_min / safe_total_relative_weight,
        np.nan,
    )

    combined = np.where(has_zero, zero_combined, positive_combined)
    combined_variance = np.where(has_zero, zero_variance_result, positive_variance)
    coverage = np.where(has_zero, zero_count, positive_coverage).astype(np.int64)
    return combined, combined_variance, coverage


def combine(
    images: Sequence[Any],
    variances: Sequence[Any] | None = None,
) -> tuple[np.ndarray, np.ndarray | None, np.ndarray]:
    """Combine aligned images.

    When variance arrays are not supplied, an unweighted NaN-aware mean is
    calculated. When every image has a variance array, zero-variance
    observations take precedence: if any finite zero variance exists at a pixel,
    only those observations are averaged and the combined variance is 0.0.
    Otherwise, inverse-variance weighting is used for strictly positive
    variances. Invalid weights are ignored. Pixels with no valid contributors
    produce NaN combined values and NaN combined variance.

    This function receives already-aligned images and variance arrays. Coverage
    counts the observations actually used for each pixel.

    Returns ``(combined, combined_variance_or_None, coverage)``.
    """
    if len(images) == 0:
        raise InvalidInputError("at least one image is required for combination")
    image_arrays = [_as_float_image(image) for image in images]
    shape = image_arrays[0].shape
    if any(image.shape != shape for image in image_arrays):
        raise InvalidInputError("all images must have the same shape")

    if variances is None:
        variance_arrays = None
    else:
        if len(variances) != len(images):
            raise InvalidInputError("variances must match images in number")
        if any(v is not None for v in variances) and not all(v is not None for v in variances):
            raise InvalidInputError("variances must be provided for all images or none")
        variance_arrays = (
            None
            if all(v is None for v in variances)
            else [_as_variance(v, shape) for v in variances]  # type: ignore[arg-type]
        )

    return _combine_prepared(image_arrays, variance_arrays)


__all__ = ["combine"]
