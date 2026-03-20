"""
Moira — Local Space Engine
===========================

Archetype: Engine

Purpose
-------
Governs computation of horizon-based azimuth and altitude positions for
celestial bodies as seen from a terrestrial observer, producing a Local
Space chart where each body is plotted by its compass direction and
elevation above or below the horizon.

Boundary declaration
--------------------
Owns: azimuth/altitude computation, 8-point compass labelling, and the
      ``LocalSpacePosition`` result vessel.
Delegates: apparent RA/Dec retrieval to ``moira.planets.sky_position_at``,
           Local Sidereal Time computation to ``moira.julian``,
           nutation to ``moira.obliquity``.

Import-time side effects: None

External dependency assumptions
--------------------------------
No Qt main thread required. No database access. Requires caller to supply
apparent geocentric equatorial coordinates (RA/Dec) and Local Sidereal Time,
or a ``ChartContext`` for the convenience wrapper.

Public surface
--------------
``LocalSpacePosition``    — vessel for a body's horizon-based position.
``local_space_positions`` — compute azimuth/altitude for a dict of bodies.
``local_space_from_chart``— convenience wrapper for a ``ChartContext``.
"""


import math
from dataclasses import dataclass

from .constants import DEG2RAD, RAD2DEG


# ---------------------------------------------------------------------------
# Data structure
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class LocalSpacePosition:
    """
    RITE: The Horizon Vessel — a body's place in the compass of the sky.

    THEOREM: Holds the azimuth, altitude, and above-horizon flag for a single
    celestial body as seen from a terrestrial observer at a specific moment.

    RITE OF PURPOSE:
        Serves the Local Space Engine as the canonical result vessel for
        horizon-based chart positions. Without this vessel, callers would
        receive raw azimuth/altitude floats with no compass context or
        visibility flag, making relocation analysis and directional display
        impossible.

    LAW OF OPERATION:
        Responsibilities:
            - Store the body name, azimuth (0–360°, North = 0°), altitude
              (signed degrees), and above-horizon boolean.
            - Expose ``compass_direction()`` for an 8-point compass label.
        Non-responsibilities:
            - Does not compute azimuth/altitude (delegated to
              ``local_space_positions``).
            - Does not apply atmospheric refraction corrections.
        Dependencies:
            - Populated by ``local_space_positions()`` or
              ``local_space_from_chart()``.
        Structural invariants:
            - ``azimuth`` is always in [0, 360).
            - ``altitude`` is in [−90, +90].
            - ``is_above`` is always ``altitude >= 0``.
        Succession stance: terminal — not designed for subclassing.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.local_space.LocalSpacePosition",
        "risk": "medium",
        "api": {
            "public_methods": ["compass_direction", "__repr__"],
            "public_attributes": ["body", "azimuth", "altitude", "is_above"]
        },
        "state": {
            "mutable": false,
            "fields": ["body", "azimuth", "altitude", "is_above"]
        },
        "effects": {
            "io": [],
            "signals_emitted": [],
            "db_writes": []
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": {
            "raises": [],
            "policy": "caller ensures valid RA/Dec/lat/LST before construction"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "kiro"
    }
    [/MACHINE_CONTRACT]

    Attributes
    ----------
    body      : name of the celestial body.
    azimuth   : compass bearing in degrees, North = 0°/360°, East = 90°,
                South = 180°, West = 270°.
    altitude  : elevation above (+) or below (−) the horizon, degrees.
    is_above  : ``True`` when ``altitude >= 0`` (body is visible above horizon).
    """

    body:     str
    azimuth:  float   # 0–360°, North = 0, East = 90
    altitude: float   # −90 to +90  (negative = below horizon)
    is_above: bool    # True if altitude >= 0

    # ------------------------------------------------------------------
    # Derived helpers
    # ------------------------------------------------------------------

    def compass_direction(self) -> str:
        """
        Return an approximate 8-point compass label for the azimuth.

        The mapping is:

        ======  ============
        Range   Label
        ======  ============
        337.5–360 or 0–22.5   N
        22.5–67.5             NE
        67.5–112.5            E
        112.5–157.5           SE
        157.5–202.5           S
        202.5–247.5           SW
        247.5–292.5           W
        292.5–337.5           NW
        ======  ============
        """
        az = self.azimuth % 360.0
        labels = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
        # Each octant spans 45°; offset by half-octant (22.5°) so North is centred.
        index = int((az + 22.5) / 45.0) % 8
        return labels[index]

    def __repr__(self) -> str:
        above = "above" if self.is_above else "below"
        return (
            f"LocalSpacePosition({self.body!r}, "
            f"az={self.azimuth:.4f}° [{self.compass_direction()}], "
            f"alt={self.altitude:+.4f}° [{above} horizon])"
        )


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------

def local_space_positions(
    planet_ra_dec: dict[str, tuple[float, float]],
    latitude: float,
    lst_deg: float,
) -> list[LocalSpacePosition]:
    """
    Compute Local Space azimuth/altitude for each planet.

    Parameters
    ----------
    planet_ra_dec : dict of body name → (RA degrees, Dec degrees).
                    RA and Dec must be apparent geocentric equatorial
                    coordinates (matching the supplied LST).
    latitude      : observer's geographic latitude (degrees, signed;
                    positive = North).
    lst_deg       : Local (Apparent) Sidereal Time at the birth moment
                    (degrees).

    Returns
    -------
    list[LocalSpacePosition] sorted by azimuth (0° → 360°).

    Notes
    -----
    The standard spherical-astronomy transformation is used::

        H = LST − RA                              (hour angle, degrees)

        sin(alt) = sin(φ)·sin(δ) + cos(φ)·cos(δ)·cos(H)

        az  = atan2(sin(H)·cos(δ),
                    cos(H)·cos(δ)·sin(φ) − sin(δ)·cos(φ))  + 180°

    The +180° offset converts from the traditional astronomical azimuth
    (South = 0°) to the navigational convention (North = 0°, East = 90°).
    """
    lat_r = latitude * DEG2RAD

    results: list[LocalSpacePosition] = []

    for body, (ra, dec) in planet_ra_dec.items():
        dec_r = dec * DEG2RAD

        # Hour angle — positive when the body is west of the meridian.
        ha_deg = (lst_deg - ra) % 360.0
        if ha_deg > 180.0:
            ha_deg -= 360.0
        ha_r = ha_deg * DEG2RAD

        # Altitude
        sin_alt = (
            math.sin(lat_r) * math.sin(dec_r)
            + math.cos(lat_r) * math.cos(dec_r) * math.cos(ha_r)
        )
        sin_alt = max(-1.0, min(1.0, sin_alt))
        alt_deg = math.asin(sin_alt) * RAD2DEG

        # Azimuth (navigational convention: North = 0°, East = 90°)
        #   az_astro = atan2(sin H · cos δ,  cos H · cos δ · sin φ − sin δ · cos φ)
        #   az_nav   = az_astro + 180°
        sin_az_num = math.sin(ha_r) * math.cos(dec_r)
        cos_az_num = (
            math.cos(ha_r) * math.cos(dec_r) * math.sin(lat_r)
            - math.sin(dec_r) * math.cos(lat_r)
        )
        az_deg = (math.atan2(sin_az_num, cos_az_num) * RAD2DEG + 180.0) % 360.0

        results.append(
            LocalSpacePosition(
                body=body,
                azimuth=az_deg,
                altitude=alt_deg,
                is_above=(alt_deg >= 0.0),
            )
        )

    results.sort(key=lambda p: p.azimuth)
    return results


# ---------------------------------------------------------------------------
# Convenience wrapper for a Moira ChartContext
# ---------------------------------------------------------------------------

def local_space_from_chart(
    chart,
    observer_lat: float,
    observer_lon: float,
    bodies: list[str] | None = None,
) -> list[LocalSpacePosition]:
    """
    Convenience wrapper: compute a Local Space chart from a Moira ChartContext.

    Computes the Local Apparent Sidereal Time from ``chart.jd_ut`` and the
    supplied ``observer_lon``, then delegates to
    :func:`local_space_positions`.

    Parameters
    ----------
    chart        : a ``ChartContext`` instance (from ``moira.chart``).
    observer_lat : observer's geographic latitude (degrees, signed).
    observer_lon : observer's geographic longitude (degrees, east positive).
    bodies       : list of body names to include.  Defaults to all bodies
                   in ``chart.planets``.

    Returns
    -------
    list[LocalSpacePosition] sorted by azimuth.
    """
    from .planets import sky_position_at
    from .julian import local_sidereal_time
    from .obliquity import nutation, true_obliquity
    from .julian import ut_to_tt

    if bodies is None:
        bodies = list(chart.planets.keys())

    # Compute Local Apparent Sidereal Time for the observer's longitude.
    jd_tt    = ut_to_tt(chart.jd_ut)
    dpsi, _  = nutation(jd_tt)
    obliquity = true_obliquity(jd_tt)
    lst_deg  = local_sidereal_time(chart.jd_ut, observer_lon, dpsi, obliquity)

    # Collect apparent RA/Dec for each body.
    planet_ra_dec: dict[str, tuple[float, float]] = {}
    for body in bodies:
        sky = sky_position_at(
            body,
            chart.jd_ut,
            observer_lat=observer_lat,
            observer_lon=observer_lon,
        )
        planet_ra_dec[body] = (sky.right_ascension, sky.declination)

    return local_space_positions(planet_ra_dec, observer_lat, lst_deg)
