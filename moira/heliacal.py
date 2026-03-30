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
   the unified star subsystem (stars.py / STARS_BACKEND_STANDARD.md),
   not a standalone Swiss compatibility shim.

Constitution entry
------------------
    Subsystem:    Heliacal / Visibility
    SCP entry:    moira/stars.py, STARS_BACKEND_STANDARD.md
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

import math
from dataclasses import dataclass
from enum import Enum

from .constants import Body


__all__ = [
    "HeliacalEventKind",
    "VisibilityModel",
    "HeliacalPolicy",
    "PlanetHeliacalEvent",
    "planet_heliacal_rising",
    "planet_heliacal_setting",
    "planet_acronychal_rising",
    "planet_acronychal_setting",
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


# ---------------------------------------------------------------------------
# Internal constants
# ---------------------------------------------------------------------------

_HELIACAL_PLANETS: frozenset[str] = frozenset({
    Body.MERCURY, Body.VENUS, Body.MARS,
    Body.JUPITER, Body.SATURN, Body.URANUS, Body.NEPTUNE,
})

# Minimum elongation (°) from the Sun before bothering to test visibility.
# Below this the planet is lost in the solar glare regardless of magnitude.
_ELONG_MIN: float = 5.0


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _signed_elongation(body: str, jd: float) -> float:
    """
    Signed ecliptic elongation of *body* from the Sun (degrees).

    Positive = east of Sun (evening star).
    Negative = west of Sun (morning star).
    Range: (−180, +180].
    """
    from .planets import planet_at
    p = planet_at(body, jd)
    s = planet_at(Body.SUN, jd)
    return (p.longitude - s.longitude + 180.0) % 360.0 - 180.0


def _planet_alt(body: str, jd: float, lat: float, lon: float) -> float:
    """Altitude of *body* above the observer's horizon (degrees)."""
    from .rise_set import _altitude
    return _altitude(jd, lat, lon, body)


def _sun_alt(jd: float, lat: float, lon: float) -> float:
    """Altitude of the Sun above the observer's horizon (degrees)."""
    from .rise_set import _altitude
    return _altitude(jd, lat, lon, Body.SUN)


def _arcus_visionis(mag: float, model: VisibilityModel) -> float:
    """
    Solar depression (degrees) required for a body of apparent magnitude *mag*
    to be visible under the given atmospheric conditions.

    Based on the classical stepped table (Ptolemy / Schoch), scaled for
    non-standard limiting magnitude and extinction coefficient.
    """
    if mag <= -4.0:
        base = 5.0
    elif mag <= -2.0:
        base = 6.5
    elif mag <= -1.0:
        base = 7.5
    elif mag <= 0.0:
        base = 9.0
    elif mag <= 1.0:
        base = 10.0
    elif mag <= 2.0:
        base = 11.0
    elif mag <= 3.0:
        base = 12.0
    elif mag <= 4.0:
        base = 13.0
    else:
        base = 14.5
    # Adjust for limiting magnitude (observer acuity) and extinction
    base += (6.5 - model.limiting_magnitude) * 0.8
    base += (model.extinction_coefficient - 0.25) * 4.0
    return max(3.0, base)


def _find_sun_at_alt(
    jd_midnight: float,
    lat: float,
    lon: float,
    target_alt: float,
    morning: bool,
) -> float | None:
    """
    Find the JD when the Sun's altitude equals *target_alt* within one
    half-day window.

    Parameters
    ----------
    jd_midnight : JD of the midnight that begins the civil day being searched.
    morning     : True  → search the morning half [midnight, noon].
                  False → search the evening half [noon, next-midnight].
    target_alt  : Target solar altitude (negative for twilight, e.g. −12.0).

    Returns None if no crossing exists (polar day/night, or wrong half-day).
    """
    t0 = jd_midnight if morning else jd_midnight + 0.5
    t1 = t0 + 0.5
    a0 = _sun_alt(t0, lat, lon)
    a1 = _sun_alt(t1, lat, lon)

    if morning:
        # Sun should be rising through target: a0 â‰¤ target â‰¤ a1
        if not (a0 <= target_alt <= a1):
            return None
    else:
        # Sun should be descending through target: a1 â‰¤ target â‰¤ a0
        if not (a1 <= target_alt <= a0):
            return None

    for _ in range(22):
        tm = (t0 + t1) * 0.5
        am = _sun_alt(tm, lat, lon)
        if (a0 - target_alt) * (am - target_alt) <= 0.0:
            t1, a1 = tm, am
        else:
            t0, a0 = tm, am
    return (t0 + t1) * 0.5


def _check_visibility(
    body: str,
    jd_midnight: float,
    lat: float,
    lon: float,
    morning: bool,
    model: VisibilityModel,
) -> tuple[float, float, float, float] | None:
    """
    Check whether *body* is visible at the arcus-visionis twilight moment on
    the given day.

    Returns ``(twilight_jd, planet_alt_deg, sun_alt_deg, magnitude)`` if
    visible, else ``None``.
    """
    from .phase import apparent_magnitude
    try:
        mag = apparent_magnitude(body, jd_midnight + 0.5)
    except Exception:
        return None
    av = _arcus_visionis(mag, model)
    twilight_jd = _find_sun_at_alt(jd_midnight, lat, lon, -av, morning)
    if twilight_jd is None:
        return None
    planet_alt = _planet_alt(body, twilight_jd, lat, lon)
    if planet_alt <= model.horizon_altitude_deg:
        return None
    return twilight_jd, planet_alt, -av, mag


def _validate_args(
    body: str,
    jd_start: float,
    lat: float,
    lon: float,
    search_days: int,
) -> None:
    if body not in _HELIACAL_PLANETS:
        raise ValueError(
            f"body must be a planet (not SUN, MOON, or EARTH); got {body!r}"
        )
    if not math.isfinite(jd_start):
        raise ValueError(f"jd_start must be finite, got {jd_start}")
    if not -90.0 <= lat <= 90.0:
        raise ValueError(f"lat must be in [-90, 90], got {lat}")
    if not -180.0 <= lon <= 180.0:
        raise ValueError(f"lon must be in [-180, 180], got {lon}")
    if not (isinstance(search_days, int) and search_days > 0):
        raise ValueError(f"search_days must be a positive integer, got {search_days!r}")


# ---------------------------------------------------------------------------
# PlanetHeliacalEvent
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class PlanetHeliacalEvent:
    """
    Result vessel for a planet heliacal or acronychal visibility event.

    Fields
    ------
    body : str
        Planet name (one of the ``Body.*`` constants).
    kind : HeliacalEventKind
        The event type.
    jd_ut : float
        Julian Day (UT1) of the event — the moment when the Sun's altitude
        equals ``−arcus_visionis`` (the visibility threshold crossing).
    elongation_deg : float
        Signed elongation from the Sun at the event day.
        Negative = west of Sun (morning sky).
        Positive = east of Sun (evening sky).
    planet_altitude_deg : float
        Planet's altitude above the observer's horizon at ``jd_ut``.
    sun_altitude_deg : float
        Sun's altitude at ``jd_ut`` (equals ``−arcus_visionis`` by construction).
    apparent_magnitude : float
        Planet's apparent V magnitude on the event date.
    """
    body:                  str
    kind:                  HeliacalEventKind
    jd_ut:                 float
    elongation_deg:        float
    planet_altitude_deg:   float
    sun_altitude_deg:      float
    apparent_magnitude:    float


# ---------------------------------------------------------------------------
# Public computation layer
# ---------------------------------------------------------------------------

def planet_heliacal_rising(
    body: str,
    jd_start: float,
    lat: float,
    lon: float,
    policy: HeliacalPolicy | None = None,
    search_days: int = 400,
) -> PlanetHeliacalEvent | None:
    """
    Find the next heliacal rising of a planet from ``jd_start``.

    The heliacal rising is the first morning when the planet is visible in
    the eastern sky before sunrise, after a period of solar invisibility.
    This is the classical *first appearance* — Venus rising as the morning
    star (Lucifer / Phosphoros), or Mars/Jupiter/Saturn emerging from the
    Sun's rays.

    Parameters
    ----------
    body        : Planet body constant (``Body.VENUS``, ``Body.MARS``, etc.).
                  ``Body.SUN``, ``Body.MOON``, and ``Body.EARTH`` raise
                  ``ValueError``.
    jd_start    : Julian Day (UT1) to begin the forward search.
                  Start near or just before the expected solar conjunction
                  for best results.
    lat         : Observer latitude (degrees, north positive).
    lon         : Observer longitude (degrees, east positive).
    policy      : :class:`HeliacalPolicy` governing visibility conditions.
                  Defaults to standard naked-eye dark-sky conditions.
    search_days : Maximum number of days to scan forward.  Increase for
                  slow outer planets.  Default 400.

    Returns
    -------
    :class:`PlanetHeliacalEvent` or ``None`` if no event is found within
    ``search_days``.

    Algorithm
    ---------
    For each day in the search window:

    1. Compute signed elongation.  Skip if ≥ 0° (planet not in morning sky)
       or |elongation| < 5° (too close to Sun).
    2. Compute the planet's apparent magnitude → arcus visionis.
    3. Find the moment when the Sun's altitude = −arcus_visionis before
       sunrise (bisection on solar altitude).
    4. Compute planet altitude at that moment.  If planet is above the
       visibility horizon → heliacal rising.
    """
    _validate_args(body, jd_start, lat, lon, search_days)
    policy = policy if policy is not None else HeliacalPolicy.default()
    model  = policy.visibility_model

    # Normalize jd_start to the preceding midnight
    jd_mid0 = math.floor(jd_start + 0.5) - 0.5

    # Scan forward: first day where planet is in morning sky and visible at twilight.
    for d in range(search_days):
        jd_midnight = jd_mid0 + d
        se = _signed_elongation(body, jd_midnight + 0.5)
        if se >= 0.0 or abs(se) < _ELONG_MIN:
            continue
        vis = _check_visibility(body, jd_midnight, lat, lon, morning=True, model=model)
        if vis is not None:
            jd_ev, p_alt, s_alt, mag = vis
            return PlanetHeliacalEvent(
                body=body,
                kind=HeliacalEventKind.HELIACAL_RISING,
                jd_ut=jd_ev,
                elongation_deg=se,
                planet_altitude_deg=p_alt,
                sun_altitude_deg=s_alt,
                apparent_magnitude=mag,
            )
    return None


def planet_heliacal_setting(
    body: str,
    jd_start: float,
    lat: float,
    lon: float,
    policy: HeliacalPolicy | None = None,
    search_days: int = 400,
) -> PlanetHeliacalEvent | None:
    """
    Find the next heliacal setting of a planet from ``jd_start``.

    The heliacal setting is the last morning when the planet is visible
    before it disappears into the Sun's light ahead of solar conjunction.

    The search scans forward, tracking the last visible morning.  When the
    planet's elongation drops below the minimum threshold (planet re-enters
    the Sun's glare), the last recorded visible morning is returned.

    Parameters
    ----------
    body, jd_start, lat, lon, policy, search_days : see
        :func:`planet_heliacal_rising`.

    Notes
    -----
    Start ``jd_start`` when the planet is already in the morning sky for
    best results.  If no visible morning is found before the search ends,
    returns ``None``.
    """
    _validate_args(body, jd_start, lat, lon, search_days)
    policy = policy if policy is not None else HeliacalPolicy.default()
    model  = policy.visibility_model

    jd_mid0 = math.floor(jd_start + 0.5) - 0.5

    last: tuple[float, float, float, float, float] | None = None  # (jd, alt, sun_alt, mag, elong)

    for d in range(search_days):
        jd_midnight = jd_mid0 + d
        se = _signed_elongation(body, jd_midnight + 0.5)
        abs_se = abs(se)

        if se < 0.0 and abs_se >= _ELONG_MIN:
            vis = _check_visibility(body, jd_midnight, lat, lon, morning=True, model=model)
            if vis is not None:
                jd_ev, p_alt, s_alt, mag = vis
                last = (jd_ev, p_alt, s_alt, mag, se)
        elif last is not None and abs_se < _ELONG_MIN:
            # Planet was visible but is now in the Sun's rays — heliacal setting
            jd_ev, p_alt, s_alt, mag, elong = last
            return PlanetHeliacalEvent(
                body=body,
                kind=HeliacalEventKind.HELIACAL_SETTING,
                jd_ut=jd_ev,
                elongation_deg=elong,
                planet_altitude_deg=p_alt,
                sun_altitude_deg=s_alt,
                apparent_magnitude=mag,
            )

    return None


def planet_acronychal_rising(
    body: str,
    jd_start: float,
    lat: float,
    lon: float,
    policy: HeliacalPolicy | None = None,
    search_days: int = 400,
) -> PlanetHeliacalEvent | None:
    """
    Find the next acronychal rising of a planet from ``jd_start``.

    The acronychal rising is the first evening when the planet is visible
    in the western sky after sunset — the first appearance as an evening
    star.  For Venus this is the Hesperus / evening-star phase; for outer
    planets it corresponds to the first evening visibility after the planet
    has passed through the morning sky and now re-enters evening apparition.

    Parameters
    ----------
    body, jd_start, lat, lon, policy, search_days : see
        :func:`planet_heliacal_rising`.
    """
    _validate_args(body, jd_start, lat, lon, search_days)
    policy = policy if policy is not None else HeliacalPolicy.default()
    model  = policy.visibility_model

    jd_mid0 = math.floor(jd_start + 0.5) - 0.5

    # Scan forward: first day where planet is in evening sky and visible at dusk.
    for d in range(search_days):
        jd_midnight = jd_mid0 + d
        se = _signed_elongation(body, jd_midnight + 0.5)
        if se <= 0.0 or abs(se) < _ELONG_MIN:
            continue
        vis = _check_visibility(body, jd_midnight, lat, lon, morning=False, model=model)
        if vis is not None:
            jd_ev, p_alt, s_alt, mag = vis
            return PlanetHeliacalEvent(
                body=body,
                kind=HeliacalEventKind.ACRONYCHAL_RISING,
                jd_ut=jd_ev,
                elongation_deg=se,
                planet_altitude_deg=p_alt,
                sun_altitude_deg=s_alt,
                apparent_magnitude=mag,
            )
    return None


def planet_acronychal_setting(
    body: str,
    jd_start: float,
    lat: float,
    lon: float,
    policy: HeliacalPolicy | None = None,
    search_days: int = 400,
) -> PlanetHeliacalEvent | None:
    """
    Find the next acronychal setting of a planet from ``jd_start``.

    The acronychal setting is the last evening when the planet is visible
    after sunset before it disappears into the Sun's light ahead of solar
    conjunction.

    Parameters
    ----------
    body, jd_start, lat, lon, policy, search_days : see
        :func:`planet_heliacal_rising`.
    """
    _validate_args(body, jd_start, lat, lon, search_days)
    policy = policy if policy is not None else HeliacalPolicy.default()
    model  = policy.visibility_model

    jd_mid0 = math.floor(jd_start + 0.5) - 0.5

    last: tuple[float, float, float, float, float] | None = None

    for d in range(search_days):
        jd_midnight = jd_mid0 + d
        se = _signed_elongation(body, jd_midnight + 0.5)
        abs_se = abs(se)

        if se > 0.0 and abs_se >= _ELONG_MIN:
            vis = _check_visibility(body, jd_midnight, lat, lon, morning=False, model=model)
            if vis is not None:
                jd_ev, p_alt, s_alt, mag = vis
                last = (jd_ev, p_alt, s_alt, mag, se)
        elif last is not None and abs_se < _ELONG_MIN:
            jd_ev, p_alt, s_alt, mag, elong = last
            return PlanetHeliacalEvent(
                body=body,
                kind=HeliacalEventKind.ACRONYCHAL_SETTING,
                jd_ut=jd_ev,
                elongation_deg=elong,
                planet_altitude_deg=p_alt,
                sun_altitude_deg=s_alt,
                apparent_magnitude=mag,
            )

    return None

