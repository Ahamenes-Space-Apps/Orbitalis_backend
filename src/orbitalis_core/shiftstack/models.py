"""Data models for the shift-and-stack core module.

Purpose: Lightweight input and output structures for aligned frames, motion
vectors, combined images, and search results.
Inputs: Arrays, timestamps, and motion values supplied by callers.
Outputs: Dataclasses used by the shift-and-stack public API.
Called by: orbitalis_core.shiftstack modules and callers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .errors import InvalidInputError


@dataclass(frozen=True)
class Frame:
    """One aligned SPHEREx frame in MJy/sr surface-brightness units.

    ``time`` is the observation time in days (MJD is conventional). ``variance``
    is optional for combination, but detection search requires it.
    """

    image: np.ndarray
    time: float
    variance: np.ndarray | None = None
    frame_id: str | None = None


def _coerce_motion_component(value: Any) -> float:
    if isinstance(value, (bool, np.bool_)):
        raise InvalidInputError("motion components must be finite real numbers")
    if isinstance(value, (complex, np.complexfloating)):
        raise InvalidInputError("motion components must be finite real numbers")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise InvalidInputError("motion components must be finite real numbers") from exc
    if not np.isfinite(result):
        raise InvalidInputError("motion components must be finite real numbers")
    return result


@dataclass(frozen=True)
class MotionVector:
    """A trial motion on the common pixel grid.

    Units are pixels per day on the aligned image grid. ``dx_px_per_day`` is the
    horizontal (column/x) rate and ``dy_px_per_day`` is the vertical (row/y)
    rate. Positive x moves toward increasing column indices; positive y moves
    toward increasing row indices.

    The mapping from sky motion (arcsec/day, position angle east of north) to
    these pixel rates is intentionally outside this module. SDD D-17 remains
    unresolved.
    """

    dx_px_per_day: float
    dy_px_per_day: float

    def __post_init__(self) -> None:
        dx = _coerce_motion_component(self.dx_px_per_day)
        dy = _coerce_motion_component(self.dy_px_per_day)
        object.__setattr__(self, "dx_px_per_day", dx)
        object.__setattr__(self, "dy_px_per_day", dy)


@dataclass
class ShiftCombineResult:
    """Result of aligning and combining frames for one motion vector."""

    combined: np.ndarray
    variance: np.ndarray | None
    coverage: np.ndarray
    motion: MotionVector
    reference_time: float


@dataclass
class SearchResult:
    """Result of evaluating a grid of trial motions.

    ``best_score_map`` and ``best_trial_index_map`` are per-pixel. Zero-motion
    trials do not contribute to either map. ``best_coverage_map`` stores the
    coverage count for the winning trial at each pixel, or ``-1`` where no trial
    wins.

    Trial maps are retained only when ``return_trial_maps=True``.
    """

    motion_vectors: tuple[MotionVector, ...]
    reference_time: float
    best_score_map: np.ndarray
    best_trial_index_map: np.ndarray
    best_coverage_map: np.ndarray
    work_estimate: int
    min_coverage_fraction: float
    score_maps: tuple[np.ndarray, ...] | None = None
    combined_images: tuple[np.ndarray, ...] | None = None
    combined_variances: tuple[np.ndarray, ...] | None = None
    coverage_maps: tuple[np.ndarray, ...] | None = None
