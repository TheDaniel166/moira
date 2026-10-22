"""
Moira — Geodetic Astrology Engine
==================================

Archetype: Engine

Purpose
-------
Governs computation of Geodetic Astrology — the direct mapping of the
tropical (or sidereal) zodiac onto geographic longitude.  Every location
on Earth carries a native Geodetic MC and a derived Geodetic Ascendant
without requiring a birth time.

The foundational mapping (Sepharial / Johndro tradition):

    Geodetic MC (tropical) = geographic longitude (°E, 0–360)

    Geographic latitude is taken as supplied in signed decimal degrees and is
    passed unchanged into the Ascendant geometry. No datum or geodetic-to-
    geocentric/astronomical latitude conversion is inferred.

    0° Aries (tropical) ≡ 0° geographic longitude (Greenwich meridian)
    30° Aries           ≡ 30° E
    0° Taurus           ≡ 30° E
    …and so on eastward through the full 360°

The Geodetic Ascendant is the ecliptic degree rising on the eastern
horizon at the given latitude for the Geodetic MC, computed via the
standard hour-angle / ARMC formula.

Both tropical and sidereal paths are supported:

  tropical — Geodetic MC = geographic longitude (mod 360)
  sidereal — Geodetic MC = (geographic longitude − ayanamsa) mod 360
             expressed in the chosen sidereal zodiac.  The inverse
             (geodetic equivalents) adds the ayanamsa back.

Boundary declaration
--------------------
Owns: Geodetic MC derivation, Geodetic chart vessel (``GeodeticChart``),
      geodetic equivalents map, and the tropical/sidereal ayanamsa lane policy.
Delegates: the Ascendant branch selection and circular normalization to
      ``moira._angles``, shared with ``moira.houses``; obliquity at a Julian
      Day to ``moira.obliquity``; ayanamsa to ``moira.sidereal``.

Import-time side effects: None

External dependency assumptions
--------------------------------
No Qt main thread required.  No database access.  Caller supplies
either raw geographic coordinates + obliquity, or a ``ChartContext``
for the convenience wrappers.

Public surface
--------------
``GeodeticChart``               — vessel for a single geodetic chart.
``geodetic_mc``                 — Geodetic MC from geographic longitude.
``geodetic_asc``                — Geodetic ASC from location + obliquity.
``geodetic_chart``              — full GeodeticChart from coordinates.
``geodetic_chart_from_chart``   — convenience wrapper for a ChartContext.
``geodetic_equivalents``        — geographic longitudes native to each planet.
``geodetic_equivalents_from_chart`` — equivalents directly from a ChartContext.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Literal

from .constants import DEG2RAD, RAD2DEG
from .geoutils import wrap_longitude_deg
from ._angles import _asc_from_armc  # noqa: F401 - canonical doctrine lives in moira._angles

__all__ = [
    "GeodeticChart",
    "GeodeticChartProvenance",
    "geodetic_mc",
    "geodetic_asc",
    "geodetic_chart",
    "geodetic_chart_from_chart",
    "geodetic_equivalents",
    "geodetic_equivalents_from_chart",
]


# ---------------------------------------------------------------------------
# Data vessel
# ---------------------------------------------------------------------------

_GEODETIC_LATITUDE_CONVENTION = "caller_supplied_geographic_latitude_no_conversion"
_EARTH_OBLIQUITY_MIN_DEG = 22.0
_EARTH_OBLIQUITY_MAX_DEG = 25.0


@dataclass(slots=True, frozen=True)
class GeodeticChartProvenance:
    """Calculation provenance retained by a ``GeodeticChart`` result.

    Direct calculations retain their caller-supplied coordinates and numeric
    parameters on ``GeodeticChart`` itself. Chart-backed calculations also
    preserve the exact chart epochs and astronomy model identities used by the
    wrapper. Latitude is passed through unchanged; no datum or conversion is
    inferred from the numeric value.
    """

    calculation_source: Literal["direct_inputs", "chart_context"] = "direct_inputs"
    latitude_convention: Literal[
        "caller_supplied_geographic_latitude_no_conversion"
    ] = _GEODETIC_LATITUDE_CONVENTION
    chart_jd_ut: float | None = None
    chart_jd_tt: float | None = None
    obliquity_timescale: Literal["TT"] | None = None
    mean_obliquity_model: str | None = None
    nutation_model: str | None = None
    ayanamsa_system: str | None = None
    ayanamsa_timescale: Literal["UT"] | None = None

    def __post_init__(self) -> None:
        if self.calculation_source not in ("direct_inputs", "chart_context"):
            raise ValueError(
                "calculation_source must be 'direct_inputs' or 'chart_context'"
            )
        if self.latitude_convention != _GEODETIC_LATITUDE_CONVENTION:
            raise ValueError("unsupported geodetic latitude convention")
        for name in ("chart_jd_ut", "chart_jd_tt"):
            value = getattr(self, name)
            if value is not None and not math.isfinite(value):
                raise ValueError(f"{name} must be finite when supplied")

        if self.calculation_source == "direct_inputs":
            chart_fields = (
                self.chart_jd_ut,
                self.chart_jd_tt,
                self.obliquity_timescale,
                self.mean_obliquity_model,
                self.nutation_model,
                self.ayanamsa_system,
                self.ayanamsa_timescale,
            )
            if any(value is not None for value in chart_fields):
                raise ValueError(
                    "direct-input provenance cannot claim chart-derived epochs or models"
                )
            return

        if self.chart_jd_ut is None or self.chart_jd_tt is None:
            raise ValueError("chart-context provenance requires both chart Julian Days")
        if self.obliquity_timescale != "TT":
            raise ValueError("chart-context obliquity provenance must name TT")
        if not self.mean_obliquity_model or not self.nutation_model:
            raise ValueError("chart-context provenance requires obliquity model identities")
        if (self.ayanamsa_system is None) != (self.ayanamsa_timescale is None):
            raise ValueError("ayanamsa system and timescale provenance must be supplied together")
        if self.ayanamsa_system is not None and not self.ayanamsa_system.strip():
            raise ValueError("ayanamsa_system must be non-empty when supplied")
        if self.ayanamsa_timescale not in (None, "UT"):
            raise ValueError("chart-context ayanamsa provenance must name UT")


@dataclass(slots=True, frozen=True)
class GeodeticChart:
    """
    RITE: The Location-Native Chart — a place's inherent zodiacal identity.

    THEOREM: Holds the Geodetic MC, Geodetic Ascendant, and the derivation
    parameters for a single geographic location.  No birth time is required
    or stored.

    RITE OF PURPOSE:
        Serves the Geodetic Engine as the canonical result vessel.  Without
        this vessel callers would have no structured representation of the
        location-native angles needed for relocation analysis, mundane
        astrology, or overlay against natal charts.

    LAW OF OPERATION:
        Responsibilities:
            - Store the geographic coordinates, Geodetic MC, Geodetic ASC,
              obliquity used, zodiac path, applied ayanamsa, and calculation
              provenance when it is available.
        Non-responsibilities:
            - Does not compute angles (delegated to ``geodetic_chart``).
            - Does not render or project onto a map.
            - Does not infer a coordinate datum or convert latitude conventions.
        Structural invariants:
            - ``mc`` and ``asc`` are always in [0°, 360°).
            - ``zodiac`` and ``ayanamsa_deg`` agree: a tropical vessel always
              carries exactly 0.0, because the tropical lane has no displacement.
            - ``zodiac`` is either "tropical" or "sidereal".
            - Geographic latitude is caller-supplied and passed through without
              geodetic/geocentric conversion.
            - Earth obliquity is finite and lies in [22°, 25°], a guarded
              envelope around the established long-term terrestrial range.
        Succession stance: terminal.

    Canon: Sepharial, "The World Horoscope" (1910);
           Johndro, "The Stars: How and Where They Influence" (1929);
           Meeus, "Astronomical Algorithms" Ch. 13.

    [MACHINE_CONTRACT v2]
    {
        "scope": "class",
        "id": "moira.geodetic.GeodeticChart",
        "risk": "low",
        "api": {
            "public_methods": ["__repr__"],
            "public_attributes": [
                "geo_latitude", "geo_longitude", "mc", "asc",
                "obliquity", "zodiac", "ayanamsa_deg", "provenance"
            ]
        },
        "state": {
            "mutable": false,
            "fields": [
                "geo_latitude", "geo_longitude", "mc", "asc",
                "obliquity", "zodiac", "ayanamsa_deg", "provenance"
            ]
        },
        "effects": {"io": [], "signals_emitted": [], "db_writes": []},
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": {
            "raises": ["ValueError"],
            "policy": "construction enforces coordinate, angle, zodiac, and provenance invariants"
        },
        "succession": {"stance": "terminal", "override_points": []},
        "agent": "urania"
    }
    [/MACHINE_CONTRACT]
    """

    geo_latitude:  float  # Observer latitude  (degrees, −90 to +90)
    geo_longitude: float  # Observer longitude (degrees, −180 to +180)
    mc:            float  # Geodetic MC (degrees, 0–360, tropical or sidereal)
    asc:           float  # Geodetic Ascendant (degrees, 0–360)
    obliquity:     float  # True obliquity of the ecliptic used (degrees)
    zodiac:        str    # "tropical" or "sidereal"
    ayanamsa_deg:  float  # Ayanamsa applied; 0.0 for tropical
    provenance:    GeodeticChartProvenance | None = None

    def __post_init__(self) -> None:
        _validate_geodetic_inputs(
            self.geo_longitude,
            self.geo_latitude,
            self.obliquity,
            self.ayanamsa_deg,
        )
        _validate_zodiac(self.zodiac)
        _validate_zodiac_policy(self.zodiac, ayanamsa_deg=self.ayanamsa_deg)
        for name, value in (("mc", self.mc), ("asc", self.asc)):
            _validate_finite(name, value)
            if not 0.0 <= value < 360.0:
                raise ValueError(f"{name} must be in [0, 360), got {value!r}")
        if not -180.0 <= self.geo_longitude <= 180.0:
            raise ValueError(
                "stored geo_longitude must be wrapped to [-180, 180], "
                f"got {self.geo_longitude!r}"
            )
        if self.provenance is not None:
            if not isinstance(self.provenance, GeodeticChartProvenance):
                raise TypeError("provenance must be a GeodeticChartProvenance or None")
            if self.provenance.calculation_source == "chart_context":
                if self.zodiac == "sidereal" and self.provenance.ayanamsa_system is None:
                    raise ValueError(
                        "sidereal chart-context provenance requires ayanamsa_system"
                    )
                if self.zodiac == "tropical" and self.provenance.ayanamsa_system is not None:
                    raise ValueError(
                        "tropical chart-context provenance must not carry ayanamsa_system"
                    )

    def __repr__(self) -> str:
        return (
            f"GeodeticChart("
            f"lat={self.geo_latitude:.4f}°, "
            f"lon={self.geo_longitude:.4f}°, "
            f"MC={self.mc:.4f}°, "
            f"ASC={self.asc:.4f}°, "
            f"zodiac={self.zodiac!r})"
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _armc_from_mc(mc_deg: float, obliquity: float) -> float:
    """
    Convert ecliptic MC longitude to ARMC (Right Ascension of the MC).

    The MC is the ecliptic degree culminating on the upper meridian.  Its
    ARMC is the RA of that ecliptic degree at zero ecliptic latitude:

        ARMC = atan2(sin(λ_MC) · cos(ε),  cos(λ_MC))

    This is the standard ecliptic-to-equatorial RA formula restricted to
    ecliptic latitude = 0.  Meeus, "Astronomical Algorithms" Ch. 13.
    """
    l_r   = mc_deg    * DEG2RAD
    eps_r = obliquity * DEG2RAD
    return math.atan2(math.sin(l_r) * math.cos(eps_r), math.cos(l_r)) * RAD2DEG % 360.0


def _validate_finite(name: str, value: float) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite, got {value!r}")


# Same margin as the _POLAR_EPS convention declared in moira.houses: a shared
# numeric stand-in for "this latitude is the pole", not a physical threshold.
_POLAR_REFUSAL_MARGIN_DEG = 1e-6


def _validate_geodetic_inputs(
    geo_longitude: float,
    geo_latitude: float,
    obliquity: float,
    ayanamsa_deg: float,
) -> None:
    _validate_finite("geo_longitude", geo_longitude)
    _validate_finite("geo_latitude", geo_latitude)
    _validate_finite("obliquity", obliquity)
    _validate_finite("ayanamsa_deg", ayanamsa_deg)
    if not _EARTH_OBLIQUITY_MIN_DEG <= obliquity <= _EARTH_OBLIQUITY_MAX_DEG:
        raise ValueError(
            "Earth obliquity must be in [22, 25] degrees, a guarded envelope "
            f"around its terrestrial range, got {obliquity!r}"
        )
    if not -90.0 <= geo_latitude <= 90.0:
        raise ValueError(f"geo_latitude must be in [-90, 90], got {geo_latitude!r}")
    if abs(geo_latitude) > 90.0 - _POLAR_REFUSAL_MARGIN_DEG:
        raise ValueError(
            "geo_latitude is at the geographic pole, where the horizon and the "
            "ecliptic no longer define a rising Ascendant; refuse instead of "
            f"extrapolate, got {geo_latitude!r} "
            f"(limit +/-{90.0 - _POLAR_REFUSAL_MARGIN_DEG})"
        )


def _validate_zodiac(zodiac: str) -> None:
    if zodiac not in ("tropical", "sidereal"):
        raise ValueError(f"zodiac must be 'tropical' or 'sidereal', got {zodiac!r}")


def _validate_zodiac_policy(
    zodiac: str,
    *,
    ayanamsa_deg: float | None = None,
    ayanamsa_system: str | None = None,
) -> None:
    """
    Enforce that the ayanamsa belongs to the sidereal lane alone.

    The tropical lane is the ayanamsa-zero lane: Geodetic MC is geographic
    longitude with no displacement.  An ayanamsa supplied alongside
    ``zodiac="tropical"`` therefore contradicts the declared lane instead of
    being a value to tolerate or quietly drop.

    The opposite requirement — that sidereal output name its displacement — is
    checked where the displacement is resolved, because a sidereal ayanamsa of
    exactly ``0.0`` is a legal (if degenerate) claim that the lanes coincide.
    """
    if zodiac != "tropical":
        return
    if ayanamsa_deg is not None and ayanamsa_deg != 0.0:
        raise ValueError(
            "tropical zodiac must not carry an ayanamsa offset; the tropical "
            f"Geodetic MC is geographic longitude, got ayanamsa_deg={ayanamsa_deg!r}"
        )
    if ayanamsa_system is not None:
        raise ValueError(
            "tropical zodiac must not carry an ayanamsa_system; a named ayanamsa "
            f"belongs to the sidereal lane, got ayanamsa_system={ayanamsa_system!r}"
        )


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------

def geodetic_mc(
    geo_longitude: float,
    ayanamsa_deg: float = 0.0,
) -> float:
    """
    Geodetic MC for a geographic longitude.

    Maps a geographic longitude directly to an ecliptic zodiac degree.

    For the tropical path (``ayanamsa_deg = 0.0``):

        Geodetic MC = geo_longitude (mod 360°)

    For the sidereal path (``ayanamsa_deg > 0``):

        Geodetic MC (sidereal) = (geo_longitude − ayanamsa_deg) mod 360°

    Parameters
    ----------
    geo_longitude : Geographic longitude in decimal degrees.
                    Any value is accepted; the result is wrapped to [0°, 360°).
    ayanamsa_deg  : Ayanamsa in degrees.  Pass 0.0 (default) for tropical.
                    Pass the active ayanamsa for sidereal output.

    Returns
    -------
    float — Geodetic MC in degrees, range [0°, 360°).
    """
    _validate_finite("geo_longitude", geo_longitude)
    _validate_finite("ayanamsa_deg", ayanamsa_deg)
    return (geo_longitude - ayanamsa_deg) % 360.0


def geodetic_asc(
    geo_longitude: float,
    geo_latitude: float,
    obliquity: float,
    ayanamsa_deg: float = 0.0,
) -> float:
    """
    Geodetic Ascendant for a geographic location.

    Derives the ARMC from the tropical Geodetic MC, computes the tropical
    rising horizon intersection, and applies the zodiac displacement only to
    the returned longitude. The physical geographic meridian is independent
    of zodiac.

    Parameters
    ----------
    geo_longitude : Geographic longitude (decimal degrees, any range).
    geo_latitude  : Caller-supplied geographic latitude (decimal degrees,
                    north-positive; passed through without conversion or an
                    inferred datum; strictly inside the poles — see Notes).
    obliquity     : True obliquity of the ecliptic (degrees).
    ayanamsa_deg  : Ayanamsa in degrees. Pass 0.0 (default) for tropical; a
                    sidereal result is the tropical Ascendant minus this value.

    Returns
    -------
    float — Geodetic Ascendant in degrees, range [0°, 360°).

    Notes
    -----
    At a geographic pole the horizon no longer singles out a rising ecliptic
    degree, so latitudes within ``_POLAR_REFUSAL_MARGIN_DEG`` of |90| are
    refused with ``ValueError`` rather than answered with an extrapolation.
    Latitudes just inside that margin are computed, but their Ascendant is a
    mathematical extrapolation, not an observationally meaningful direction.
    """
    _validate_geodetic_inputs(geo_longitude, geo_latitude, obliquity, ayanamsa_deg)
    tropical_mc = geodetic_mc(geo_longitude)
    armc = _armc_from_mc(tropical_mc, obliquity)
    tropical_asc = _asc_from_armc(armc, obliquity, geo_latitude)
    return (tropical_asc - ayanamsa_deg) % 360.0


def geodetic_chart(
    geo_longitude: float,
    geo_latitude:  float,
    obliquity:     float,
    ayanamsa_deg:  float | None = None,
    zodiac:        str   = "tropical",
) -> GeodeticChart:
    """
    Build a full GeodeticChart vessel from geographic coordinates.

    Parameters
    ----------
    geo_longitude : Geographic longitude (decimal degrees, any range;
                    stored wrapped to [−180°, +180°]).
    geo_latitude  : Caller-supplied geographic latitude (decimal degrees,
                    north-positive; passed through without conversion or an
                    inferred datum).
    obliquity     : True obliquity of the ecliptic (degrees).  Use
                    ``moira.obliquity.true_obliquity(jd_tt)`` for epoch-
                    appropriate values.
    ayanamsa_deg  : Ayanamsa in degrees. Omit for tropical (equivalent to
                    ``0.0``); required for sidereal, where an explicit
                    ``0.0`` is valid when the caller declares coincident lanes.
    zodiac        : "tropical" (default) or "sidereal".  Selects the lane and
                    constrains ``ayanamsa_deg``; it is not merely a label on
                    the result.

    Returns
    -------
    GeodeticChart — immutable vessel with MC, ASC, derivation metadata, and
    provenance identifying the direct-input policy.

    Raises
    ------
    ValueError
        If ``zodiac`` is unknown, if a sidereal request omits
        ``ayanamsa_deg``, if Earth obliquity is outside [22°, 25°], or if a
        tropical request carries a nonzero offset.
    """
    _validate_zodiac(zodiac)
    _validate_zodiac_policy(zodiac, ayanamsa_deg=ayanamsa_deg)
    if zodiac == "sidereal" and ayanamsa_deg is None:
        raise ValueError(
            "ayanamsa_deg is required when zodiac='sidereal'. "
            "Pass the sidereal offset explicitly, including 0.0 if intended."
        )
    resolved_ayanamsa = 0.0 if ayanamsa_deg is None else ayanamsa_deg
    _validate_geodetic_inputs(geo_longitude, geo_latitude, obliquity, resolved_ayanamsa)
    mc  = geodetic_mc(geo_longitude, resolved_ayanamsa)
    asc = geodetic_asc(geo_longitude, geo_latitude, obliquity, resolved_ayanamsa)
    return GeodeticChart(
        geo_latitude  = geo_latitude,
        geo_longitude = wrap_longitude_deg(geo_longitude),
        mc            = mc,
        asc           = asc,
        obliquity     = obliquity,
        zodiac        = zodiac,
        ayanamsa_deg  = resolved_ayanamsa,
        provenance    = GeodeticChartProvenance(),
    )


def geodetic_chart_from_chart(
    chart,
    zodiac:          str = "tropical",
    ayanamsa_system: str | None = None,
) -> GeodeticChart:
    """
    Convenience wrapper: build a GeodeticChart from a Moira ChartContext.

    Reads two different clock coordinates from the vessel, because the two
    authorities ask for different ones: true obliquity is a TT function, while
    ``moira.sidereal.ayanamsa`` is contracted for UT and performs its own
    UT→TT step.  Feeding it ``chart.jd_tt`` would shift the epoch twice.

    Parameters
    ----------
    chart            : a ``ChartContext`` instance (from ``moira.chart``).
    zodiac           : "tropical" (default) or "sidereal".
    ayanamsa_system  : Ayanamsa system name (from ``moira.sidereal.Ayanamsa``).
                       Required when ``zodiac="sidereal"``; must be omitted for
                       tropical.

    Returns
    -------
    GeodeticChart — derived from ``chart.latitude``, ``chart.longitude``,
    and obliquity at ``chart.jd_tt``.

    Raises
    ------
    ValueError
        If ``zodiac="sidereal"`` and ``ayanamsa_system`` is not provided, or if
        ``zodiac="tropical"`` and an ``ayanamsa_system`` is provided.
    """
    _validate_zodiac(zodiac)
    _validate_zodiac_policy(zodiac, ayanamsa_system=ayanamsa_system)
    from .obliquity import true_obliquity_with_truth

    if zodiac == "sidereal" and ayanamsa_system is None:
        raise ValueError(
            "ayanamsa_system is required when zodiac='sidereal'. "
            "Pass a system name from moira.sidereal.Ayanamsa."
        )

    obliquity_truth = true_obliquity_with_truth(chart.jd_tt)
    obliquity = obliquity_truth.true_obliquity_deg
    ayanamsa_deg = 0.0

    if zodiac == "sidereal":
        from .sidereal import ayanamsa as compute_ayanamsa
        ayanamsa_deg = compute_ayanamsa(chart.jd_ut, ayanamsa_system)

    result = geodetic_chart(
        geo_longitude = chart.longitude,
        geo_latitude  = chart.latitude,
        obliquity     = obliquity,
        ayanamsa_deg  = ayanamsa_deg,
        zodiac        = zodiac,
    )
    return replace(
        result,
        provenance=GeodeticChartProvenance(
            calculation_source="chart_context",
            chart_jd_ut=chart.jd_ut,
            chart_jd_tt=chart.jd_tt,
            obliquity_timescale=obliquity_truth.input_timescale,
            mean_obliquity_model=obliquity_truth.mean_model,
            nutation_model=obliquity_truth.nutation_model,
            ayanamsa_system=ayanamsa_system,
            ayanamsa_timescale="UT" if zodiac == "sidereal" else None,
        ),
    )


# ---------------------------------------------------------------------------
# Geodetic equivalents
# ---------------------------------------------------------------------------

def geodetic_equivalents(
    planet_longitudes: dict[str, float],
    ayanamsa_deg:      float = 0.0,
) -> dict[str, float]:
    """
    Geographic longitude where each planet's position is the native Geodetic MC.

    Inverse of ``geodetic_mc``: given a planet's ecliptic longitude, return
    the geographic longitude at which that planet's degree falls exactly on
    the Geodetic MC.

    For the tropical path (``ayanamsa_deg = 0.0``):

        geographic longitude = planet tropical longitude

    For the sidereal path (``ayanamsa_deg > 0``, input is sidereal positions):

        geographic longitude = planet sidereal longitude + ayanamsa
                             = planet tropical longitude

    In both cases the geographic longitude equals the planet's tropical
    ecliptic longitude.  The ayanamsa cancels in the inversion.  The
    meaningful distinction is that the sidereal path accepts sidereal input
    and recovers the geographic anchor, while the tropical path accepts
    tropical input directly.

    Parameters
    ----------
    planet_longitudes : dict mapping body name → ecliptic longitude (degrees).
                        Tropical if ``ayanamsa_deg = 0.0``; sidereal otherwise.
    ayanamsa_deg      : Ayanamsa in degrees.  Pass 0.0 for tropical input.

    Returns
    -------
    dict mapping body name → geographic longitude in [−180°, +180°].
    """
    _validate_finite("ayanamsa_deg", ayanamsa_deg)
    result: dict[str, float] = {}
    for body, lon in planet_longitudes.items():
        if not body:
            raise ValueError("Geodetic equivalent body names must be non-empty")
        _validate_finite(f"longitude for {body!r}", lon)
        geo_lon = (lon + ayanamsa_deg) % 360.0
        result[body] = wrap_longitude_deg(geo_lon)
    return result


def geodetic_equivalents_from_chart(
    chart,
    bodies:          list[str] | None = None,
    zodiac:          str               = "tropical",
    ayanamsa_system: str | None        = None,
) -> dict[str, float]:
    """
    Convenience wrapper: geographic equivalents for natal planets from a ChartContext.

    For each planet, returns the geographic longitude at which that planet's
    ecliptic position is the native Geodetic MC.

    The ayanamsa for the sidereal path is resolved at ``chart.jd_ut``, matching
    the UT input contract of ``moira.sidereal.ayanamsa``.

    Parameters
    ----------
    chart            : a ``ChartContext`` instance.
    bodies           : list of body names to include.  Defaults to all bodies
                       present in ``chart.planets``.
    zodiac           : "tropical" (default) or "sidereal".
    ayanamsa_system  : Ayanamsa system name.  Required when ``zodiac="sidereal"``;
                       must be omitted for tropical.

    Returns
    -------
    dict mapping body name → geographic longitude in [−180°, +180°].

    A geographic meridian is zodiac-independent, so both lanes resolve the
    same anchor; ``zodiac`` selects only how the body position is expressed on
    the way into the inversion.

    Raises
    ------
    ValueError
        If ``zodiac="sidereal"`` and ``ayanamsa_system`` is not provided, or if
        ``zodiac="tropical"`` and an ``ayanamsa_system`` is provided.
    """
    _validate_zodiac(zodiac)
    _validate_zodiac_policy(zodiac, ayanamsa_system=ayanamsa_system)
    if zodiac == "sidereal" and ayanamsa_system is None:
        raise ValueError(
            "ayanamsa_system is required when zodiac='sidereal'. "
            "Pass a system name from moira.sidereal.Ayanamsa."
        )

    if bodies is None:
        bodies = list(chart.planets.keys())

    ayanamsa_deg = 0.0
    if zodiac == "sidereal":
        from .sidereal import ayanamsa as compute_ayanamsa
        ayanamsa_deg = compute_ayanamsa(chart.jd_ut, ayanamsa_system)

    planet_longitudes: dict[str, float] = {}
    for body in bodies:
        longitude = chart.planets[body].longitude
        if zodiac == "sidereal":
            # ``ChartContext`` stores tropical positions, but the inversion
            # helper reads a nonzero ayanamsa as "these inputs are sidereal".
            # Express the position in the requested lane before inverting,
            # otherwise the ayanamsa is applied twice.
            longitude = (longitude - ayanamsa_deg) % 360.0
        planet_longitudes[body] = longitude

    return geodetic_equivalents(planet_longitudes, ayanamsa_deg)
