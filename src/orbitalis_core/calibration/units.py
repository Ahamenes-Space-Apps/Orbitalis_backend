"""Surface-brightness unit conversion (stub).

Purpose: Placeholder for ``to_surface_brightness``. Deliberately unimplemented:
the Level-2 imaging path is already in MJy/sr end to end (SDD D-03), so no
caller exists yet. The real converters — flux-per-pixel to surface brightness
and back — belong to spectrum extraction (CORE.08) and injection (VAL.01);
their signatures are fixed there, not guessed now (roadmap CORE.03a).
Inputs: TBD.
Outputs: TBD.
Called by: TBD.
"""

from __future__ import annotations


def to_surface_brightness(*args: object, **kwargs: object) -> object:
    """Not implemented — see module docstring (roadmap CORE.03a)."""
    raise NotImplementedError(
        "to_surface_brightness is not implemented; imaging stays in MJy/sr "
        "(SDD D-03). Flux<->surface-brightness converters land with CORE.08/VAL.01."
    )


__all__ = ["to_surface_brightness"]
