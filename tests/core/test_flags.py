"""Tests for SPHEREx pixel flag decoding and default masking.

Purpose: Verify flag decoding, default masking polarity, and NaN application.
Inputs: Synthetic NumPy arrays.
Outputs: Test results.
Called by: pytest.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from orbitalis_core.flags import apply_default_mask, decode, default_mask

SOURCE = 1 << 21
FULLSAMPLE = 1 << 12
TRANSIENT = 1 << 0


def test_unflagged_pixel_is_valid() -> None:
    flags = np.array([0])
    mask = default_mask(flags)
    assert mask.dtype == bool
    assert mask.shape == flags.shape
    assert not mask[0]


def test_source_only_is_valid() -> None:
    flags = np.array([SOURCE])
    assert not default_mask(flags)[0]


def test_fullsample_only_is_valid() -> None:
    flags = np.array([FULLSAMPLE])
    assert not default_mask(flags)[0]


def test_other_flag_is_masked() -> None:
    flags = np.array([TRANSIENT])
    assert default_mask(flags)[0]


def test_source_plus_excluded_is_masked() -> None:
    flags = np.array([SOURCE | TRANSIENT])
    assert default_mask(flags)[0]


def test_fullsample_plus_excluded_is_masked() -> None:
    flags = np.array([FULLSAMPLE | TRANSIENT])
    assert default_mask(flags)[0]


def test_multiple_excluded_flags_masked() -> None:
    flags = np.array([TRANSIENT | (1 << 1)])
    assert default_mask(flags)[0]


def test_array_of_multiple_pixels() -> None:
    flags = np.array([0, SOURCE, FULLSAMPLE, TRANSIENT, SOURCE | TRANSIENT])
    mask = default_mask(flags)
    expected = np.array([False, False, False, True, True])
    assert np.array_equal(mask, expected)


def test_decode_identifies_flags_present() -> None:
    flags = np.array([0, SOURCE, FULLSAMPLE, TRANSIENT, SOURCE | TRANSIENT | (1 << 30)])
    decoded = decode(flags)
    assert isinstance(decoded, dict)
    assert set(decoded.keys()) >= {"SOURCE", "FULLSAMPLE", "TRANSIENT", "UNKNOWN"}
    assert decoded["SOURCE"].shape == flags.shape
    assert not decoded["SOURCE"][0]
    assert decoded["SOURCE"][1]
    assert not decoded["SOURCE"][2]
    assert decoded["TRANSIENT"][3]
    assert decoded["UNKNOWN"][4]
    assert not decoded["UNKNOWN"][1]


def test_decode_does_not_mutate_input() -> None:
    flags = np.array([SOURCE | TRANSIENT])
    original = flags.copy()
    decode(flags)
    assert np.array_equal(flags, original)


def test_invalid_inputs() -> None:
    with pytest.raises(TypeError):
        default_mask(None)
    with pytest.raises(TypeError):
        decode("not-an-array")
    with pytest.raises(ValueError):
        default_mask(np.array([1.0, 2.0]))
    with pytest.raises(ValueError):
        decode(np.array([-1]))


def test_masked_scientific_pixels_become_nan() -> None:
    flags = np.array([0, SOURCE, TRANSIENT])
    data = np.array([1.0, 2.0, 3.0])
    mask = default_mask(flags)
    result = data.copy()
    result[mask] = np.nan
    assert result[0] == 1.0
    assert result[1] == 2.0
    assert math.isnan(result[2])
    # Ensure masked pixel is NaN, not zero.
    assert result[2] != 0.0


def test_decode_scalar_input() -> None:
    decoded = decode(SOURCE)
    assert isinstance(decoded, dict)
    assert bool(decoded["SOURCE"]) is True
    assert bool(decoded["TRANSIENT"]) is False
    assert bool(decoded["UNKNOWN"]) is False


def test_default_mask_scalar() -> None:
    assert bool(default_mask(0)) is False
    assert bool(default_mask(SOURCE)) is False
    assert bool(default_mask(TRANSIENT)) is True


@pytest.mark.parametrize("dtype", [np.int8, np.uint8, np.int16, np.uint16])
def test_narrow_integer_dtypes(dtype: np.dtype) -> None:
    # Use a flag value representable in every narrow dtype (TRANSIENT = 1).
    flags = np.array([0, 1], dtype=dtype)
    mask = default_mask(flags)
    assert isinstance(mask, np.ndarray)
    assert mask.dtype == bool
    assert np.array_equal(mask, np.array([False, True]))
    decoded = decode(flags)
    assert decoded["TRANSIENT"].dtype == bool
    assert np.array_equal(decoded["TRANSIENT"], np.array([False, True]))


@pytest.mark.parametrize("dtype", [np.uint32, np.uint64])
def test_wide_unsigned_integer_dtypes(dtype: np.dtype) -> None:
    flags = np.array([0, SOURCE, FULLSAMPLE, SOURCE | TRANSIENT], dtype=dtype)
    mask = default_mask(flags)
    assert isinstance(mask, np.ndarray)
    assert np.array_equal(mask, np.array([False, False, False, True]))
    decoded = decode(flags)
    assert bool(decoded["SOURCE"][1]) is True
    assert bool(decoded["FULLSAMPLE"][2]) is True


def test_unknown_only_bits_are_masked() -> None:
    unknown_bit = 1 << 30
    flags = np.array([unknown_bit])
    assert bool(default_mask(flags)[0]) is True
    decoded = decode(flags)
    assert bool(decoded["UNKNOWN"][0]) is True
    assert not bool(decoded["TRANSIENT"][0])


def test_source_or_fullsample_remains_valid() -> None:
    flags = np.array([SOURCE | FULLSAMPLE])
    assert not default_mask(flags)[0]


def test_multidimensional_shape_preservation() -> None:
    flags = np.arange(6, dtype=np.int32).reshape(2, 3)
    flags[0, 0] = SOURCE
    flags[1, 2] = TRANSIENT
    mask = default_mask(flags)
    assert mask.shape == flags.shape
    decoded = decode(flags)
    assert decoded["SOURCE"].shape == flags.shape
    assert decoded["TRANSIENT"].shape == flags.shape


def test_empty_arrays() -> None:
    flags = np.array([], dtype=np.int32)
    mask = default_mask(flags)
    assert isinstance(mask, np.ndarray)
    assert mask.shape == (0,)
    assert mask.dtype == bool
    decoded = decode(flags)
    assert all(isinstance(v, np.ndarray) and v.shape == (0,) for v in decoded.values())


def test_default_mask_does_not_mutate_input() -> None:
    flags = np.array([1], dtype=np.int8)
    original = flags.copy()
    _ = default_mask(flags)
    assert np.array_equal(flags, original)


def test_scalar_return_types() -> None:
    mask = default_mask(SOURCE)
    assert isinstance(mask, np.ndarray)
    assert mask.shape == ()
    assert mask.dtype == bool
    assert bool(mask) is False

    decoded = decode(TRANSIENT)
    assert isinstance(decoded, dict)
    assert all(isinstance(v, np.ndarray) and v.shape == () for v in decoded.values())
    assert bool(decoded["TRANSIENT"]) is True
    assert bool(decoded["UNKNOWN"]) is False


def test_apply_default_mask_basic() -> None:
    image = np.array([1.0, 2.0, 3.0])
    flags = np.array([0, 1 << 0, 1 << 21])
    result = apply_default_mask(image, flags)
    assert isinstance(result, np.ndarray)
    assert result.dtype == np.float64
    assert result[0] == 1.0
    assert np.isnan(result[1])
    assert result[2] == 3.0
    # Original unchanged.
    assert image.dtype != np.float64 or image[1] == 2.0


def test_apply_default_mask_integer_image() -> None:
    image = np.array([10, 20, 30], dtype=np.int32)
    flags = np.array([0, 1 << 0, 0])
    result = apply_default_mask(image, flags)
    assert result.dtype == np.float64
    assert result[0] == 10.0
    assert np.isnan(result[1])
    assert result[2] == 30.0
    assert image.dtype == np.int32


def test_apply_default_mask_does_not_mutate_original() -> None:
    image = np.array([1.0, 2.0, 3.0])
    flags = np.array([1 << 0, 0, 0])
    original = image.copy()
    _ = apply_default_mask(image, flags)
    assert np.array_equal(image, original)


def test_apply_default_mask_shape_mismatch() -> None:
    image = np.array([1.0, 2.0])
    flags = np.array([0, 0, 0])
    with pytest.raises(ValueError):
        apply_default_mask(image, flags)


def test_apply_default_mask_preserves_unmasked() -> None:
    image = np.array([[1.0, 2.0], [3.0, 4.0]])
    flags = np.array([[0, 1 << 0], [1 << 21, 1 << 12]])
    result = apply_default_mask(image, flags)
    assert result.shape == image.shape
    assert result[0, 0] == 1.0
    assert np.isnan(result[0, 1])
    assert result[1, 0] == 3.0
    assert result[1, 1] == 4.0
