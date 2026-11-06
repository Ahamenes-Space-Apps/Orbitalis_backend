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
    is optional and, when present, must have the same shape as ``image`` and
    contain values in (MJy/sr)^2. Invalid variance values are ignored rather
    than treated as weights.
    """

    image: np.ndarray
    time: float
    variance: np.ndarray | None = None
    frame_id: str | None = None

    @property
    def id(self) -> str | None:
        return self.frame_id


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
    toward increasing row indices. The mapping from sky motion (arcsec/day,
    position angle) to these pixel rates is intentionally left to the caller
    until the project's motion convention (SDD D-17) is settled.
    """

    dx_px_per_day: float
    dy_px_per_day: float

    def __post_init__(self) -> None:
        dx = _coerce_motion_component(self.dx_px_per_day)
        dy = _coerce_motion_component(self.dy_px_per_day)
        object.__setattr__(self, "dx_px_per_day", dx)
        object.__setattr__(self, "dy_px_per_day", dy)

    @property
    def dx(self) -> float:
        return self.dx_px_per_day

    @property
    def dy(self) -> float:
        return self.dy_px_per_day

    @property
    def vx(self) -> float:
        return self.dx_px_per_day

    @property
    def vy(self) -> float:
        return self.dy_px_per_day


@dataclass
class ShiftCombineResult:
    """Result of aligning and combining frames for one motion vector."""

    combined: np.ndarray
    variance: np.ndarray | None
    coverage: np.ndarray
    motion: MotionVector
    reference_time: float

    @property
    def combined_image(self) -> np.ndarray:
        return self.combined

    @property
    def combined_variance(self) -> np.ndarray | None:
        return self.variance


# Backwards/alternative names that callers or tests may use.
ShiftAndCombineResult = ShiftCombineResult
CombinedResult = ShiftCombineResult
StackResult = ShiftCombineResult


@dataclass
class SearchResult:
    """Result of evaluating a grid of trial motions."""

    motion_vectors: tuple[MotionVector, ...]
    reference_time: float
    score_maps: tuple[np.ndarray, ...]
    combined_images: tuple[np.ndarray, ...]
    combined_variances: tuple[np.ndarray | None, ...]
    coverage_maps: tuple[np.ndarray, ...]
    work_estimate: int
    best_index: int | None = None

    @property
    def best_motion(self) -> MotionVector | None:
        if self.best_index is None:
            return None
        return self.motion_vectors[self.best_index]

    @property
    def best_score_map(self) -> np.ndarray | None:
        if self.best_index is None:
            return None
        return self.score_maps[self.best_index]

    @property
    def best_score(self) -> float | None:
        if self.best_index is None or not self.score_maps:
            return None
        arr = self.score_maps[self.best_index]
        if arr.size == 0 or not np.isfinite(arr).any():
            return None
        return float(np.nanmax(arr))


# Alternative names that callers or tests may use.
SearchResults = SearchResult
ShiftStackResult = SearchResult


def _as_frame(value: Any) -> Frame:
    if isinstance(value, Frame):
        return value
    if isinstance(value, dict):
        if "image" not in value or "time" not in value:
            raise InvalidInputError("frame mapping must contain 'image' and 'time'")
        return Frame(
            image=value["image"],
            time=value["time"],
            variance=value.get("variance"),
            frame_id=value.get("frame_id", value.get("id")),
        )
    if isinstance(value, (tuple, list)):
        if len(value) < 2 or len(value) > 4:
            raise InvalidInputError("frame sequence must have 2 to 4 items")
        image, time = value[0], value[1]
        variance = value[2] if len(value) >= 3 else None
        frame_id = value[3] if len(value) >= 4 else None
        return Frame(image=image, time=time, variance=variance, frame_id=frame_id)
    image = getattr(value, "image", None)
    time = getattr(value, "time", None)
    if image is None or time is None:
        raise InvalidInputError("frame object must provide 'image' and 'time'")
    variance = getattr(value, "variance", None)
    frame_id = getattr(value, "frame_id", getattr(value, "id", None))
    return Frame(image=image, time=time, variance=variance, frame_id=frame_id)


def _as_motion(value: Any) -> MotionVector:
    if isinstance(value, MotionVector):
        if not (np.isfinite(value.dx_px_per_day) and np.isfinite(value.dy_px_per_day)):
            raise InvalidInputError("motion components must be finite real numbers")
        return value
    if isinstance(value, dict):
        if "dx_px_per_day" in value and "dy_px_per_day" in value:
            dx, dy = value["dx_px_per_day"], value["dy_px_per_day"]
        elif "dx" in value and "dy" in value:
            dx, dy = value["dx"], value["dy"]
        elif "vx" in value and "vy" in value:
            dx, dy = value["vx"], value["vy"]
        else:
            raise InvalidInputError("motion mapping must contain dx/dy (or vx/vy) values")
    elif isinstance(value, (tuple, list)):
        if len(value) != 2:
            raise InvalidInputError("motion sequence must contain exactly two values")
        dx, dy = value[0], value[1]
    else:
        dx = getattr(value, "dx_px_per_day", getattr(value, "dx", getattr(value, "vx", None)))
        dy = getattr(value, "dy_px_per_day", getattr(value, "dy", getattr(value, "vy", None)))
        if dx is None or dy is None:
            raise InvalidInputError("motion object must provide dx and dy values")

    dx_f = _coerce_motion_component(dx)
    dy_f = _coerce_motion_component(dy)
    return MotionVector(dx_f, dy_f)
