"""SPHEREx pixel flag bit definitions.

Purpose: Single source of truth for SPHEREx FLAGS-layer bit constants and the
flag-name to bit-value lookup table.
Inputs: None.
Outputs: Flag constants and ``FLAG_BITS`` mapping.
Called by: ``orbitalis_core.flags.mask`` and re-exported by ``orbitalis_core.flags``.
"""

from __future__ import annotations

# Flag definitions taken from the Data & Science Specification, Table 16
# (Explanatory Supplement v2.0, pipeline R7). Bit n has value 2**n.
FLAG_TRANSIENT = 1 << 0
FLAG_OVERFLOW = 1 << 1
FLAG_SUR_ERROR = 1 << 2
FLAG_NONFUNC = 1 << 6
FLAG_DICHROIC = 1 << 7
FLAG_MISSING_DATA = 1 << 9
FLAG_HOT = 1 << 10
FLAG_COLD = 1 << 11
FLAG_FULLSAMPLE = 1 << 12
FLAG_PHANMISS = 1 << 14
FLAG_NONLINEAR = 1 << 15
FLAG_PERSIST = 1 << 17
FLAG_OUTLIER = 1 << 19
FLAG_CROSSTALK = 1 << 20
FLAG_SOURCE = 1 << 21
FLAG_GHOST = 1 << 22
# NOTE: DS spec Table 16 labels GHOST_FPA as "Ignore", but the SDD default masking
# policy masks every bit except SOURCE and FULLSAMPLE. Implementation follows the
# SDD; this discrepancy should be documented in SDD Appendix D.
FLAG_GHOST_FPA = 1 << 23
FLAG_GHOST_EXT = 1 << 24
FLAG_STREAK = 1 << 25
FLAG_BLOOM = 1 << 26
FLAG_SNOWBALL = 1 << 27
FLAG_HALO = 1 << 28
FLAG_SATELLITE_HALO = 1 << 29

# Ordered to mirror Table 16.
FLAG_BITS: dict[str, int] = {
    "TRANSIENT": FLAG_TRANSIENT,
    "OVERFLOW": FLAG_OVERFLOW,
    "SUR_ERROR": FLAG_SUR_ERROR,
    "NONFUNC": FLAG_NONFUNC,
    "DICHROIC": FLAG_DICHROIC,
    "MISSING_DATA": FLAG_MISSING_DATA,
    "HOT": FLAG_HOT,
    "COLD": FLAG_COLD,
    "FULLSAMPLE": FLAG_FULLSAMPLE,
    "PHANMISS": FLAG_PHANMISS,
    "NONLINEAR": FLAG_NONLINEAR,
    "PERSIST": FLAG_PERSIST,
    "OUTLIER": FLAG_OUTLIER,
    "CROSSTALK": FLAG_CROSSTALK,
    "SOURCE": FLAG_SOURCE,
    "GHOST": FLAG_GHOST,
    "GHOST_FPA": FLAG_GHOST_FPA,
    "GHOST_EXT": FLAG_GHOST_EXT,
    "STREAK": FLAG_STREAK,
    "BLOOM": FLAG_BLOOM,
    "SNOWBALL": FLAG_SNOWBALL,
    "HALO": FLAG_HALO,
    "SATELLITE_HALO": FLAG_SATELLITE_HALO,
}

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
]
