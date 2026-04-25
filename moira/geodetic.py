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
Owns: Geodetic MC derivation, Geodetic ASC derivation, geodetic
      chart vessel (``GeodeticChart``), geodetic equivalents map.
Delegates: obliquity at a Julian Day to ``moira.obliquity``,
           ayanamsa to ``moira.sidereal``.

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

import math
from dataclasses import dataclass, field

from .constants import DEG2RAD, RAD2DEG
from .geoutils import wrap_longitude_deg

__all__ = [
    "GeodeticChart",
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
              obliquity used, zodiac path, and applied ayanamsa.
        Non-responsibilities:
            - Does not compute angles (delegated to ``geodetic_chart``).
            - Does not render or project onto a map.
            - Does not validate geographic coordinates.
        Structural invariants:
            - ``mc`` and ``asc`` are always in [0°, 360°).
            - ``ayanamsa_deg`` is 0.0 for tropical, positive for sidereal.
            - ``zodiac`` is either "tropical" or "sidereal".
        Succession stance: terminal.

    Canon: Sepharial, "The World Horoscope" (1910);
           Johndro, "The Stars: How and Where They Influence" (1929);
           Meeus, "Astronomical Algorithms" Ch. 13.

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.geodetic.GeodeticChart",
        "risk": "low",
        "api": {
            "public_methods": ["__repr__"],
            "public_attributes": [
                "geo_latitude", "geo_longitude", "mc", "asc",
                "obliquity", "zodiac", "ayanamsa_deg"
            ]
        },
        "state": {
            "mutable": false,
            "fields": [
                "geo_latitude", "geo_longitude", "mc", "asc",
                "obliquity", "zodiac", "ayanamsa_deg"
            ]
        },
        "effects": {"io": [], "signals_emitted": [], "db_writes": []},
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": {
            "raises": [],
            "policy": "caller ensures valid coordinates and obliquity"
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


def _asc_from_armc(armc: float, obliquity: float, lat: float) -> float:
    """
    Ascendant from ARMC, obliquity, and geographic latitude.

    Standard Placidus / Regiomontanus ASC formula:

        tan(ASC) = −cos(ARMC) / (sin(ε)·tan(φ) + cos(ε)·sin(ARMC))

    atan2 yields two candidates 180° apart; the Ascendant is the one
    whose ecliptic longitude falls in the same 180° semicircle as
    ARMC + 90° (the approximate RA of the eastern horizon).

    Derived from Meeus, "Astronomical Algorithms" Ch. 24.
    (Same formulation used in moira.houses._asc_from_armc.)
    """
    armc_r = armc     * DEG2RAD
    eps_r  = obliquity * DEG2RAD
    lat_r  = lat      * DEG2RAD

    y   = -math.cos(armc_r)
    x   =  math.sin(armc_r) * math.cos(eps_r) + math.tan(lat_r) * math.sin(eps_r)
    raw = math.atan2(y, x) * RAD2DEG % 360.0

    expected = (armc + 90.0) % 360.0
    alt      = (raw + 180.0) % 360.0

    def _adist(a: float, b: float) -> float:
        d = abs(a - b) % 360.0
        return d if d <= 180.0 else 360.0 - d

    return alt if _adist(alt, expected) < _adist(raw, expected) else raw


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
    return (geo_longitude - ayanamsa_deg) % 360.0


def geodetic_asc(
    geo_longitude: float,
    geo_latitude: float,
    obliquity: float,
    ayanamsa_deg: float = 0.0,
) -> float:
    """
    Geodetic Ascendant for a geographic location.

    Derives the ARMC from the Geodetic MC, then computes the Ascendant
    using the standard hour-angle formula.

    Parameters
    ----------
    geo_longitude : Geographic longitude (decimal degrees, any range).
    geo_latitude  : Geographic latitude  (decimal degrees, −90 to +90).
    obliquity     : True obliquity of the ecliptic (degrees).
    ayanamsa_deg  : Ayanamsa in degrees.  Pass 0.0 (default) for tropical.

    Returns
    -------
    float — Geodetic Ascendant in degrees, range [0°, 360°).

    Notes
    -----
    The formula is undefined (singular) at the geographic poles (|lat| = 90°).
    Results very near the poles are mathematically extrapolated but
    observationally meaningless.
    """
    mc   = geodetic_mc(geo_longitude, ayanamsa_deg)
    armc = _armc_from_mc(mc, obliquity)
    return _asc_from_armc(armc, obliquity, geo_latitude)


def geodetic_chart(
    geo_longitude: float,
    geo_latitude:  float,
    obliquity:     float,
    ayanamsa_deg:  float = 0.0,
    zodiac:        str   = "tropical",
) -> GeodeticChart:
    """
    Build a full GeodeticChart vessel from geographic coordinates.

    Parameters
    ----------
    geo_longitude : Geographic longitude (decimal degrees, any range;
                    stored wrapped to [−180°, +180°]).
    geo_latitude  : Geographic latitude  (decimal degrees, −90 to +90).
    obliquity     : True obliquity of the ecliptic (degrees).  Use
                    ``moira.obliquity.true_obliquity(jd_tt)`` for epoch-
                    appropriate values.
    ayanamsa_deg  : Ayanamsa in degrees.  Pass 0.0 (default) for tropical.
    zodiac        : "tropical" (default) or "sidereal".  Informational only;
                    the computation uses ``ayanamsa_deg`` to branch.

    Returns
    -------
    GeodeticChart — immutable vessel with MC, ASC, and derivation metadata.
    """
    mc   = geodetic_mc(geo_longitude, ayanamsa_deg)
    armc = _armc_from_mc(mc, obliquity)
    asc  = _asc_from_armc(armc, obliquity, geo_latitude)
    return GeodeticChart(
        geo_latitude  = geo_latitude,
        geo_longitude = wrap_longitude_deg(geo_longitude),
        mc            = mc,
        asc           = asc,
        obliquity     = obliquity,
        zodiac        = zodiac,
        ayanamsa_deg  = ayanamsa_deg,
    )


def geodetic_chart_from_chart(
    chart,
    zodiac:          str = "tropical",
    ayanamsa_system: str | None = None,
) -> GeodeticChart:
    """
    Convenience wrapper: build a GeodeticChart from a Moira ChartContext.

    Uses the natal chart's Julian Day (TT) to derive true obliquity, and
    optionally the chosen ayanamsa system for the sidereal path.

    Parameters
    ----------
    chart            : a ``ChartContext`` instance (from ``moira.chart``).
    zodiac           : "tropical" (default) or "sidereal".
    ayanamsa_system  : Ayanamsa system name (from ``moira.sidereal.Ayanamsa``).
                       Required when ``zodiac="sidereal"``.  Ignored for tropical.

    Returns
    -------
    GeodeticChart — derived from ``chart.latitude``, ``chart.longitude``,
    and obliquity at ``chart.jd_tt``.

    Raises
    ------
    ValueError
        If ``zodiac="sidereal"`` and ``ayanamsa_system`` is not provided.
    """
    from .obliquity import true_obliquity

    if zodiac == "sidereal" and ayanamsa_system is None:
        raise ValueError(
            "ayanamsa_system is required when zodiac='sidereal'. "
            "Pass a system name from moira.sidereal.Ayanamsa."
        )

    obliquity    = true_obliquity(chart.jd_tt)
    ayanamsa_deg = 0.0

    if zodiac == "sidereal":
        from .sidereal import ayanamsa as compute_ayanamsa
        ayanamsa_deg = compute_ayanamsa(chart.jd_tt, ayanamsa_system)

    return geodetic_chart(
        geo_longitude = chart.longitude,
        geo_latitude  = chart.latitude,
        obliquity     = obliquity,
        ayanamsa_deg  = ayanamsa_deg,
        zodiac        = zodiac,
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
    result: dict[str, float] = {}
    for body, lon in planet_longitudes.items():
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

    Parameters
    ----------
    chart            : a ``ChartContext`` instance.
    bodies           : list of body names to include.  Defaults to all bodies
                       present in ``chart.planets``.
    zodiac           : "tropical" (default) or "sidereal".
    ayanamsa_system  : Ayanamsa system name.  Required when ``zodiac="sidereal"``.

    Returns
    -------
    dict mapping body name → geographic longitude in [−180°, +180°].

    Raises
    ------
    ValueError
        If ``zodiac="sidereal"`` and ``ayanamsa_system`` is not provided.
    """
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
        ayanamsa_deg = compute_ayanamsa(chart.jd_tt, ayanamsa_system)

    planet_longitudes: dict[str, float] = {}
    for body in bodies:
        planet_longitudes[body] = chart.planets[body].longitude

    return geodetic_equivalents(planet_longitudes, ayanamsa_deg)
