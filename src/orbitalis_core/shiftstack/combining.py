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
    return np.array(arr, dtype=np.float64, copy=True)


def combine(
    images: Sequence[Any],
    variances: Sequence[Any] | None = None,
) -> tuple[np.ndarray, np.ndarray | None, np.ndarray]:
    """Combine aligned images.

    When variance arrays are not supplied, an unweighted NaN-aware mean is
    calculated. When every image has a variance array, inverse-variance
    weighting is used: the weight is ``1 / variance`` for finite, strictly
    positive variance values, and invalid weights are ignored. The combined
    variance is ``1 / sum(weights)``. Pixels with no valid weighted
    contributors produce NaN combined values and NaN combined variance.

    Variance arrays are interpolated and aligned with the same spatial transform
    as the images, which is an approximation rather than an exact propagation.

    Returns ``(combined, combined_variance_or_None, coverage)``. Coverage counts
    contributing observations per pixel. Pixels with no contributors are NaN in
    ``combined``.
    """
    if len(images) == 0:
        raise InvalidInputError("at least one image is required for combination")
    image_arrays = [_as_float_image(image) for image in images]
    shape = image_arrays[0].shape
    if any(image.shape != shape for image in image_arrays):
        raise InvalidInputError("all images must have the same shape")

    use_variance = (
        variances is not None
        and len(variances) == len(images)
        and all(v is not None for v in variances)
    )
    if variances is not None and len(variances) != len(images):
        raise InvalidInputError("variances must match images in number")
    if (
        variances is not None
        and any(v is not None for v in variances)
        and not all(v is not None for v in variances)
    ):
        raise InvalidInputError("variances must be provided for all images or none")

    stack = np.stack(image_arrays, axis=0)
    valid_image = np.isfinite(stack)

    if not use_variance:
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

    variance_arrays = [_as_variance(v, shape) for v in variances]  # type: ignore[arg-type]
    variance_stack = np.stack(variance_arrays, axis=0)
    valid_variance = np.isfinite(variance_stack) & (variance_stack > 0.0)
    contributors = valid_image & valid_variance
    coverage = contributors.sum(axis=0).astype(np.int64)

    # Use the minimum valid variance as the scaling reference. Relative weights
    # are v_min / variance, so no reciprocal of an extreme variance is formed.
    # The mean is accumulated incrementally to avoid multiplying or summing
    # large image values by large weights.
    masked_variance = np.where(contributors, variance_stack, np.inf)
    v_min = masked_variance.min(axis=0)
    has_contributors = contributors.any(axis=0)
    safe_v_min = np.where(has_contributors, v_min, 1.0)
    relative_weights = np.where(
        contributors, safe_v_min / np.where(contributors, variance_stack, 1.0), 0.0
    )

    combined = np.zeros(shape, dtype=np.float64)
    total_relative_weight = np.zeros(shape, dtype=np.float64)
    for index in range(stack.shape[0]):
        weight = relative_weights[index]
        value = stack[index]
        valid = contributors[index]
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
            updated_mean = old_fraction * combined + new_fraction * value
        combined = np.where(valid & (new_total > 0.0), updated_mean, combined)
        total_relative_weight = new_total

    has_contributors = total_relative_weight > 0.0
    safe_total_relative_weight = np.where(has_contributors, total_relative_weight, 1.0)
    combined = np.where(has_contributors, combined, np.nan)
    # variance = 1 / sum(1 / variance) = v_min / sum(relative_weights)
    combined_variance = np.where(
        has_contributors,
        safe_v_min / safe_total_relative_weight,
        np.nan,
    )
    return combined, combined_variance, coverage


__all__ = ["combine"]
