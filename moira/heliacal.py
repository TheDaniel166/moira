"""
Moira — heliacal.py
Heliacal and Visibility Doctrine Layer

Archetype: Design vessel module (Phase 3 — Defer.Design + Defer.Validation)

Purpose
-------
Provides the typed doctrine surfaces for heliacal phenomena (first/last
visibility, acronychal rising/setting, cosmic rising/setting) and the
observer visibility model that governs them.

This module is a design vessel — it defines the event kinds, policy surfaces,
and visibility model types that will govern a future heliacal computation
subsystem.  No event computation is present yet.

Phase 3 mandate
---------------
The heliacal domain is deferred because it requires:

1. A coherent subsystem design (not a bag of Swiss flag constants).
   Swiss ``swe_heliacal_ut`` exposes raw integer bitfields for visibility
   conditions, object types, and atmospheric parameters.  Moira's surface
   must express these as typed, named policy objects.

2. A validation oracle.  Heliacal phenomena are date- and location-specific
   to within minutes or hours.  A public surface requires a comparison corpus
   of known historical or computed phenomena before it can be declared stable.

3. Integration with the fixed_stars subsystem.  Stellar heliacal events depend
   on the star's catalog position and proper motion; this is naturally owned by
   the unified star subsystem (fixed_stars.py / STARS_BACKEND_STANDARD.md),
   not a standalone Swiss compatibility shim.

Constitution entry
------------------
    Subsystem:    Heliacal / Visibility
    SCP entry:    moira/fixed_stars.py, STARS_BACKEND_STANDARD.md
    Defer kind:   Defer.Design + Defer.Validation
    Blocker A:    HeliacalPolicy surface not yet locked
    Blocker B:    No validation corpus exists for heliacal times
    Blocker C:    Integration with fixed_stars pipeline TBD

    Design invariants (must hold when implementation is added):
    - No Swiss integer bitfields.  All options are HeliacalPolicy fields.
    - VisibilityModel encapsulates all observer and atmospheric parameters.
    - HeliacalEventKind is an exhaustive enum; new kinds require a doctrinal
      justification and validation case.
    - Results must be in Julian Day (UT1), never a formatted string.

    Validation plan:
    - Build a corpus of ≥20 historical heliacal events from published
      Babylonian and modern ephemeris sources before the surface goes public.
    - Each event must be reproducible within ±0.25 day.
    - Star-anchored events must use true stellar positions from the Moira
      fixed-star catalog, not Swiss catalog offsets.

Public surface
--------------
    HeliacalEventKind   — enum of all supported heliacal event types
    VisibilityModel     — typed observer + atmosphere vessel
    HeliacalPolicy      — typed control policy for heliacal computation

Import-time side effects: None
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


__all__ = [
    "HeliacalEventKind",
    "VisibilityModel",
    "HeliacalPolicy",
]


# ---------------------------------------------------------------------------
# HeliacalEventKind
# ---------------------------------------------------------------------------

class HeliacalEventKind(str, Enum):
    """
    The kind of heliacal or visibility event being sought.

    Doctrine
    --------
    These are the six canonical heliacal phenomena recognised in classical
    and modern observational astronomy.  The six form two symmetric pairs
    around the Sun:

    Heliacal phenomena (eastern sky near sunrise):
        HELIACAL_RISING      — body first visible in the east before sunrise
                                after a period of solar invisibility (the
                                classical *first appearance*, *acronychal
                                rising* in some traditions).
        HELIACAL_SETTING     — body last visible in the east before sunrise
                                before solar invisibility begins (*last
                                appearance*, eastern sky).

    Acronychal phenomena (western sky near sunset):
        ACRONYCHAL_RISING    — body first visible in the west after sunset.
        ACRONYCHAL_SETTING   — body last visible in the west after sunset.

    Cosmic phenomena (astronomical twilight boundary):
        COSMIC_RISING        — body rises exactly at true astronomical
                                dawn (no refraction or disc corrections).
        COSMIC_SETTING       — body sets exactly at true astronomical
                                dusk.

    Implementation note: these map to the Swiss SE_HELIACAL_RISING etc.
    integer constants but are expressed as a typed enum so that callers
    cannot accidentally pass an out-of-range integer.
    """
    HELIACAL_RISING   = "heliacal_rising"
    HELIACAL_SETTING  = "heliacal_setting"
    ACRONYCHAL_RISING = "acronychal_rising"
    ACRONYCHAL_SETTING = "acronychal_setting"
    COSMIC_RISING     = "cosmic_rising"
    COSMIC_SETTING    = "cosmic_setting"


# ---------------------------------------------------------------------------
# VisibilityModel
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class VisibilityModel:
    """
    Observer and atmospheric parameters governing naked-eye visibility.

    Replaces Swiss Ephemeris ``AtmosphericConditions`` integer-indexed
    array with a typed, self-documenting, immutable vessel.

    Doctrine
    --------
    Visibility depends on three layers:

    1. Observer physiology — naked-eye limiting magnitude (``limiting_mag``).
       The standard value 6.5 represents an ideal dark-sky observer.
       Light-polluted sites typically range from 4.0 to 5.5.

    2. Atmospheric extinction — how much light is absorbed per unit airmass.
       Encoded as ``extinction_coefficient`` (k in magnitudes/airmass).
       Clear mountain sky ≈ 0.20; average site ≈ 0.25; hazy ≈ 0.35.

    3. Sky background — the brightness of the sky at the horizon that a
       body must exceed to be seen.  The ``horizon_altitude_deg`` field
       defines how far above the geometric horizon the effective visibility
       horizon lies, accounting for local obstructions.

    All fields have documented physical units.  Callers must not pass raw
    Swiss integer-array indices to any Moira heliacal function.

    Args:
        limiting_magnitude: Faintest magnitude visible to the naked eye
            under these conditions (dimensionless, positive).
            Default 6.5 (ideal dark sky).
        extinction_coefficient: Atmospheric extinction per airmass
            (magnitudes/airmass).  Default 0.25 (average site).
        horizon_altitude_deg: Effective visibility horizon altitude above
            the geometric horizon (degrees).  Default 0.0.
        temperature_c: Ambient temperature (°C) for refraction.  Default 10.
        pressure_mbar: Atmospheric pressure (mbar) for refraction.
            Default 1013.25 (sea level ISA).
        relative_humidity: Relative humidity [0.0, 1.0] for extended
            refraction model.  Default 0.5.
    """
    limiting_magnitude:     float = 6.5
    extinction_coefficient: float = 0.25
    horizon_altitude_deg:   float = 0.0
    temperature_c:          float = 10.0
    pressure_mbar:          float = 1013.25
    relative_humidity:      float = 0.5

    def __post_init__(self) -> None:
        if not 0.0 <= self.relative_humidity <= 1.0:
            raise ValueError(
                f"VisibilityModel.relative_humidity must be in [0, 1], "
                f"got {self.relative_humidity}"
            )
        if self.extinction_coefficient < 0.0:
            raise ValueError(
                f"VisibilityModel.extinction_coefficient must be >= 0, "
                f"got {self.extinction_coefficient}"
            )


# ---------------------------------------------------------------------------
# HeliacalPolicy
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class HeliacalPolicy:
    """
    Typed doctrine control for heliacal event computation.

    Replaces Swiss Ephemeris ``swe_heliacal_ut`` integer flag bitfield
    (SE_HELFLAG_OPTICAL_PARAMS, SE_HELFLAG_NO_DETAILS, etc.) with a
    typed, immutable, self-documenting policy object.

    Doctrine
    --------
    The policy governs three independent doctrinal choices:

    1. Optical aid — whether the observer uses naked eye, binoculars, or a
       telescope.  Optical aid changes the effective ``limiting_magnitude``
       of the observer and the angular disc threshold.

    2. Atmospheric details — whether the full extended refraction model
       (humidity, wavelength) is applied, or the standard two-parameter
       (pressure, temperature) model is used.  The extended model is more
       accurate but requires additional observer inputs.

    3. Body type — whether the target is a star, planet, or the Moon.
       Some visibility criteria differ (e.g. phase angle for planets,
       disc threshold for the Moon).

    Args:
        optical_aid: One of ``'naked_eye'``, ``'binoculars'``, or
            ``'telescope'``.  Default ``'naked_eye'``.
        use_extended_atmosphere: If ``True``, apply the extended refraction
            model (requires humidity/wavelength in VisibilityModel).
            Default ``False``.
        visibility_model: :class:`VisibilityModel` instance governing
            observer and atmospheric parameters.  Default is standard
            dark-sky conditions.

    Design note: ``body_type`` is intentionally not a field here — it is
    inferred from the body name at call time (star → catalog lookup;
    planet → DE441; Moon → lunar orbit).  Forcing callers to specify it
    would be Swiss-style API clutter.
    """
    optical_aid:               str            = 'naked_eye'
    use_extended_atmosphere:   bool           = False
    visibility_model:          VisibilityModel = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        valid = ('naked_eye', 'binoculars', 'telescope')
        if self.optical_aid not in valid:
            raise ValueError(
                f"HeliacalPolicy.optical_aid must be one of {valid}, "
                f"got {self.optical_aid!r}"
            )
        # Replace None sentinel with the default VisibilityModel
        if self.visibility_model is None:
            object.__setattr__(self, 'visibility_model', VisibilityModel())

    @classmethod
    def default(cls) -> 'HeliacalPolicy':
        """Return the standard naked-eye dark-sky policy."""
        return cls()
