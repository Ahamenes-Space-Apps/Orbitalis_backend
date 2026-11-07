"""WCS-WAVE handling and wavelength interpolation.

Purpose: Public surface for the SPHEREx spectral WCS lookup — parse the
WCS-WAVE binary table into a ``WaveTab`` and evaluate per-pixel wavelength
and bandwidth in micrometres with our own bilinear interpolation.
Inputs: None at import; functions take a ``WaveTab`` and a spectral WCS
(``key="W"``) or FITS header.
Outputs: Re-exported ``WaveTab`` and interpolation functions.
Called by: Pipeline frame preparation, research handlers and tests.
"""

from .interpolate import (
    bandwidth_at,
    bandwidth_map,
    wavelength_at,
    wavelength_map,
)
from .tab import WaveTab

__all__ = [
    "WaveTab",
    "bandwidth_at",
    "bandwidth_map",
    "wavelength_at",
    "wavelength_map",
]
