"""Shared immutable taxonomy for Moira aspect domains.

This module contains only the type vocabulary shared by the longitude and
declination aspect engines.  Detection, doctrine, and motion computations
remain owned by their respective public modules.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AspectDomain(str, Enum):
    """Measurement domain used to admit an aspect."""

    ZODIACAL = "zodiacal"
    DECLINATION = "declination"
    WHOLE_SIGN = "whole_sign"


class AspectTier(str, Enum):
    """Canonical tier within the longitude-aspect set."""

    MAJOR = "major"
    COMMON_MINOR = "common_minor"
    EXTENDED_MINOR = "extended_minor"


class AspectFamily(str, Enum):
    """Harmonic or measurement family assigned to an admitted aspect."""

    CONJUNCTION = "conjunction"
    OPPOSITION = "opposition"
    SQUARE = "square"
    TRINE = "trine"
    SEXTILE = "sextile"
    SEMISEXTILE = "semisextile"
    SEMISQUARE = "semisquare"
    SESQUIQUADRATE = "sesquiquadrate"
    QUINCUNX = "quincunx"
    QUINTILE = "quintile"
    SEPTILE = "septile"
    NOVILE = "novile"
    DECILE = "decile"
    UNDECILE = "undecile"
    QUINDECILE = "quindecile"
    VIGINTILE = "vigintile"
    DECLINATION = "declination"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class AspectClassification:
    """Immutable domain, tier, and family description of an aspect."""

    domain: AspectDomain
    tier: AspectTier
    family: AspectFamily


# Preserve the historical public/pickle path while keeping implementation
# ownership in this private shared taxonomy module.
for _public_type in (AspectClassification, AspectDomain, AspectFamily, AspectTier):
    _public_type.__module__ = "moira.aspects"


__all__ = [
    "AspectClassification",
    "AspectDomain",
    "AspectFamily",
    "AspectTier",
]
