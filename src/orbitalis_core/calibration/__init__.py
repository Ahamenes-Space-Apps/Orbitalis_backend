"""Calibration: units, solid angle, and background handling.

Purpose: Public surface for calibration helpers. Imaging stays in MJy/sr
end to end; solid-angle conversion is applied only where surface brightness
meets flux (spectra, injection) per SDD D-03.
Inputs: None at import.
Outputs: Re-exported functions.
Called by: Pipeline, research handlers and tests.
"""

from .solid_angle import solid_angle_map
from .units import to_surface_brightness
from .zodi import subtract_zodi

__all__ = ["solid_angle_map", "subtract_zodi", "to_surface_brightness"]
