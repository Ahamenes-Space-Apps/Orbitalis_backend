"""Zodiacal-light model handling.

Purpose: ``subtract_zodi`` removes the ZODI model layer from an IMAGE array.
Inputs: Two equally shaped float arrays in MJy/sr (units are a caller
contract — core arrays carry no unit metadata; see module docstring).
Outputs: A new float64 array; inputs are never mutated. NaN propagates:
a masked pixel stays masked and a NaN model value yields NaN, never a guess.
Called by: Pipeline background handling and tests. Never applied by default —
the Level-2 IMAGE already contains the sky signal; ZODI is a model, not a
measured background (DS spec; verified on a QR2 IRSA cutout: ZODI is a
``ModifiedKelsallModelWithHPFT`` model in MJy/sr and is not subtracted from
IMAGE upstream).
"""

from __future__ import annotations

from typing import Any

import numpy as np

from orbitalis_core.errors import InvalidInputError, check_not_all_nan


def _as_image(array: Any, name: str) -> np.ndarray:
    arr = np.asarray(array)
    if arr.dtype.kind not in "fiu":
        raise InvalidInputError(f"{name} must be a numeric array, got dtype {arr.dtype}")
    return arr.astype(np.float64, copy=False)


def subtract_zodi(image: Any, zodi: Any) -> np.ndarray:
    """Return ``image - zodi`` as a new float64 array.

    Both inputs must be MJy/sr arrays of identical shape. ``image`` keeps its
    mask semantics: NaN in either input produces NaN in the output. An
    all-NaN result raises ``EmptyResultError`` (SDD §6.1).
    """
    img = _as_image(image, "image")
    zod = _as_image(zodi, "zodi")
    if img.shape != zod.shape:
        raise InvalidInputError(
            f"image and zodi must have the same shape, got {img.shape} vs {zod.shape}"
        )
    return check_not_all_nan(img - zod, name="zodi-subtracted image")


__all__ = ["subtract_zodi"]
