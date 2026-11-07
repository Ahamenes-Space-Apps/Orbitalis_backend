"""Tests for the orbitalis_core error hierarchy (FR-CORE-07).

Purpose: Verify the CoreError base, per-failure subclasses, ORB-CORE codes,
and the all-NaN output guard required by SDD §6.1.
Inputs: Synthetic NumPy arrays.
Outputs: Test results.
Called by: pytest.
"""

from __future__ import annotations

import numpy as np
import pytest

from orbitalis_core import (
    CoreError,
    EmptyResultError,
    InvalidInputError,
    check_not_all_nan,
)


def test_core_error_is_exception_base() -> None:
    assert issubclass(CoreError, Exception)


def test_invalid_input_error_derives_from_core_error() -> None:
    assert issubclass(InvalidInputError, CoreError)


def test_empty_result_error_derives_from_core_error() -> None:
    assert issubclass(EmptyResultError, CoreError)


def test_bare_core_error_has_no_code() -> None:
    assert CoreError.code is None


def test_invalid_input_error_maps_to_orb_core_001() -> None:
    assert InvalidInputError("bad input").code == "ORB-CORE-001"


def test_empty_result_error_maps_to_orb_core_002() -> None:
    assert EmptyResultError("nothing left").code == "ORB-CORE-002"


def test_code_is_readable_on_instance() -> None:
    err = InvalidInputError("shape mismatch")
    assert isinstance(err, CoreError)
    assert err.args == ("shape mismatch",)


def test_check_not_all_nan_returns_valid_array() -> None:
    arr = np.array([1.0, np.nan, 3.0])
    out = check_not_all_nan(arr, name="stack")
    assert out is arr
    np.testing.assert_array_equal(out, arr)


def test_check_not_all_nan_raises_on_all_nan() -> None:
    with pytest.raises(EmptyResultError, match="all NaN"):
        check_not_all_nan(np.full((4, 4), np.nan), name="wcs map")


def test_check_not_all_nan_raises_on_empty() -> None:
    with pytest.raises(EmptyResultError, match="empty"):
        check_not_all_nan(np.empty((0, 0)), name="cutout")


def test_check_not_all_nan_accepts_integer_array() -> None:
    arr = np.zeros((2, 2), dtype=np.int32)
    out = check_not_all_nan(arr)
    assert out.dtype == np.int32


def test_check_not_all_nan_raises_on_empty_list() -> None:
    with pytest.raises(EmptyResultError):
        check_not_all_nan([], name="frames")
