"""SPHEREx pixel flag decoding, masking, and mask application.

Purpose: Public surface for SPHEREx flag constants, decoding, and masking.
Inputs: None.
Outputs: Re-exported constants and functions.
Called by: Core processing pipeline, store/frame preparation, and tests.
"""

from .bits import (
    FLAG_BITS,
    FLAG_BLOOM,
    FLAG_COLD,
    FLAG_CROSSTALK,
    FLAG_DICHROIC,
    FLAG_FULLSAMPLE,
    FLAG_GHOST,
    FLAG_GHOST_EXT,
    FLAG_GHOST_FPA,
    FLAG_HALO,
    FLAG_HOT,
    FLAG_MISSING_DATA,
    FLAG_NONFUNC,
    FLAG_NONLINEAR,
    FLAG_OUTLIER,
    FLAG_OVERFLOW,
    FLAG_PERSIST,
    FLAG_PHANMISS,
    FLAG_SATELLITE_HALO,
    FLAG_SNOWBALL,
    FLAG_SOURCE,
    FLAG_STREAK,
    FLAG_SUR_ERROR,
    FLAG_TRANSIENT,
)
from .mask import apply_default_mask, decode, default_mask

__all__ = [
    "FLAG_TRANSIENT",
    "FLAG_OVERFLOW",
    "FLAG_SUR_ERROR",
    "FLAG_NONFUNC",
    "FLAG_DICHROIC",
    "FLAG_MISSING_DATA",
    "FLAG_HOT",
    "FLAG_COLD",
    "FLAG_FULLSAMPLE",
    "FLAG_PHANMISS",
    "FLAG_NONLINEAR",
    "FLAG_PERSIST",
    "FLAG_OUTLIER",
    "FLAG_CROSSTALK",
    "FLAG_SOURCE",
    "FLAG_GHOST",
    "FLAG_GHOST_FPA",
    "FLAG_GHOST_EXT",
    "FLAG_STREAK",
    "FLAG_BLOOM",
    "FLAG_SNOWBALL",
    "FLAG_HALO",
    "FLAG_SATELLITE_HALO",
    "FLAG_BITS",
    "decode",
    "default_mask",
    "apply_default_mask",
]
