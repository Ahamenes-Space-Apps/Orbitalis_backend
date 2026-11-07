"""Sigma-clipped image combination across frames.

Purpose: ``combine`` stacks aligned MJy/sr frames into one image with
sigma-clipping, NaN-aware statistics, and optional variance propagation.
``difference`` subtracts two aligned images for difference imaging.
Inputs: Sequences of equally shaped 2-D numeric arrays (MJy/sr, NaN = masked);
optional per-frame variance arrays of the same shape.
Outputs: ``CombineResult`` (data, variance, coverage) and difference arrays.
Called by: ``orbitalis_core.stack`` consumers — the pipeline group combine
and tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from orbitalis_core.errors import InvalidInputError, check_not_all_nan


@dataclass(frozen=True)
class CombineResult:
    """Result of ``combine``.

    ``data`` is the stacked MJy/sr image (NaN where no frame contributed).
    ``variance`` is the propagated variance for ``method="mean"`` — the
    analytic value ``sum(var_i) / n_kept**2`` under independent frames — or
    ``None`` for ``method="median"`` (no closed form; see docstring).
    ``coverage`` is the number of frames that contributed per pixel.
    """

    data: np.ndarray
    variance: np.ndarray | None
    coverage: np.ndarray


def _as_stack(frames: Any) -> tuple[np.ndarray, tuple[int, int]]:
    if isinstance(frames, np.ndarray):
        if frames.ndim != 3:
            raise InvalidInputError(
                "frames must be a sequence of 2-D arrays or a (n, rows, cols) array"
            )
        arr = frames.astype(np.float64, copy=False)
    else:
        seq = list(frames)
        if not seq:
            raise InvalidInputError("frames must contain at least one image")
        try:
            arr = np.stack([np.asarray(f, dtype=np.float64) for f in seq])
        except ValueError as exc:
            raise InvalidInputError("all frames must have the same shape") from exc
    if arr.ndim != 3 or any(d < 1 for d in arr.shape[1:]):
        raise InvalidInputError("frames must be 2-D images of positive size")
    return arr, (int(arr.shape[1]), int(arr.shape[2]))


def _check_variances(variances: Any, shape: tuple[int, int], n_frames: int) -> np.ndarray | None:
    if variances is None:
        return None
    if isinstance(variances, np.ndarray):
        var = variances.astype(np.float64, copy=False)
    else:
        var = np.stack([np.asarray(v, dtype=np.float64) for v in variances])
    if var.shape != (n_frames,) + shape:
        raise InvalidInputError(f"variances must have shape {(n_frames,) + shape}, got {var.shape}")
    return var


def combine(
    frames: Any,
    *,
    method: str = "mean",
    sigma: float = 3.0,
    variances: Any = None,
) -> CombineResult:
    """Sigma-clipped combine of aligned frames.

    Per pixel, values beyond ``median +/- sigma * std`` (NaN-aware, computed
    on the finite values) are rejected before averaging; pixels with fewer
    than two finite frames or zero spread keep all finite values. ``method``
    is ``"mean"`` or ``"median"``. ``variances`` optionally supplies one
    variance array per frame; for ``method="mean"`` the output variance is
    ``sum(var_i)/n_kept**2`` (independent frames, unweighted mean). For
    ``method="median"`` no closed-form variance exists, so ``variance`` is
    ``None``. Pixels where every frame is masked stay NaN; an all-NaN result
    raises ``EmptyResultError``.
    """
    if method not in ("mean", "median"):
        raise InvalidInputError(f"method must be 'mean' or 'median', got {method!r}")
    if not np.isfinite(sigma) or sigma <= 0:
        raise InvalidInputError("sigma must be a positive finite number")

    cube, shape = _as_stack(frames)
    var_cube = _check_variances(variances, shape, cube.shape[0])

    finite = np.isfinite(cube)
    n_finite = finite.sum(axis=0)
    with np.errstate(all="ignore"):
        med = np.nanmedian(cube, axis=0)
        # Robust spread via MAD: a plain std is inflated by the very outliers
        # clipping must remove. scale = 1.4826*MAD approximates sigma for
        # Gaussian data; MAD == 0 means "typical value is exact", in which
        # case only values equal to the median survive (deviation > 0 fails).
        mad = np.nanmedian(np.abs(cube - med[None, :, :]), axis=0)
        scale = 1.4826 * mad
    # Clip only where clipping is meaningful: >=3 finite frames.
    clip = n_finite >= 3
    deviation = np.abs(cube - med[None, :, :])
    keep = finite & (~clip[None, :, :] | (deviation <= sigma * scale[None, :, :]))
    kept = np.where(keep, cube, np.nan)
    n_kept = np.isfinite(kept).sum(axis=0)

    with np.errstate(all="ignore"):
        if method == "mean":
            data = np.nanmean(kept, axis=0)
        else:
            data = np.nanmedian(kept, axis=0)
    data = np.where(n_kept > 0, data, np.nan)

    variance = None
    if method == "mean" and var_cube is not None:
        kept_var = np.where(keep, var_cube, np.nan)
        var_sum = np.nansum(kept_var, axis=0)
        variance = np.where(n_kept > 0, var_sum / np.maximum(n_kept, 1) ** 2, np.nan)

    coverage = n_kept.astype(np.int64)
    return CombineResult(
        data=check_not_all_nan(data, name="combined image"),
        variance=variance,
        coverage=coverage,
    )


def difference(a: Any, b: Any) -> np.ndarray:
    """Return ``a - b`` for two aligned images.

    Inputs must have identical shapes. NaN propagates, so the mask of the
    result is the union of the input masks. An all-NaN result raises
    ``EmptyResultError``.
    """
    aa = np.asarray(a)
    bb = np.asarray(b)
    if (
        aa.shape != bb.shape
        or aa.ndim != 2
        or aa.dtype.kind not in "fiu"
        or bb.dtype.kind not in "fiu"
    ):
        raise InvalidInputError("a and b must be equally shaped 2-D numeric arrays")
    return check_not_all_nan(
        aa.astype(np.float64, copy=False) - bb.astype(np.float64, copy=False),
        name="difference image",
    )


__all__ = ["CombineResult", "combine", "difference"]
