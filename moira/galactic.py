"""
Moira — Galactic Engine
========================

Archetype: Engine

Purpose
-------
Governs transformation between ecliptic, equatorial, and galactic coordinate
frames, and provides the ``GalacticPosition`` vessel for expressing any
celestial body's position in the IAU galactic coordinate system.

Boundary declaration
--------------------
Owns: IAU 1958/J2000 rotation matrix, equatorial-to-galactic and
      galactic-to-equatorial transforms, ecliptic bridge functions,
      galactic reference point computation, and the ``GalacticPosition``
      result vessel.
Delegates: ecliptic/equatorial conversion to ``moira.coordinates``.

Import-time side effects: None

External dependency assumptions
--------------------------------
No Qt main thread required. No database access. Pure matrix arithmetic
using the Liu, Zhu & Zhang (2011) ICRS rotation constants.

Public surface
--------------
``GalacticPosition``          — vessel for a body's galactic frame position.
``equatorial_to_galactic``    — convert RA/Dec to galactic (l, b).
``galactic_to_equatorial``    — convert galactic (l, b) to RA/Dec.
``ecliptic_to_galactic``      — convert ecliptic lon/lat to galactic (l, b).
``galactic_to_ecliptic``      — convert galactic (l, b) to ecliptic lon/lat.
``galactic_position_of``      — compute galactic position for a single body.
``all_galactic_positions``    — compute galactic positions for a full chart.
``galactic_reference_points`` — ecliptic coordinates of five galactic landmarks.
"""

import math
from dataclasses import dataclass

from .constants import DEG2RAD, RAD2DEG
from .coordinates import ecliptic_to_equatorial, equatorial_to_ecliptic


# ---------------------------------------------------------------------------
# IAU / J2000 rotation matrix: ICRS equatorial → galactic
# Row 0 = galactic x-axis (toward GC)
# Row 1 = galactic y-axis (l = 90°, b = 0°)
# Row 2 = galactic z-axis (toward NGP)
# Source: Liu, Zhu & Zhang (2011, A&A 526, A16)
# ---------------------------------------------------------------------------
_A = (
    (-0.054875539396, -0.873437104728, -0.483834991770),
    ( 0.494109453628, -0.444829594298,  0.746982248700),
    (-0.867666135683, -0.198076389613,  0.455983794521),
)

# Transpose of _A — used for the inverse transform (galactic → equatorial).
# Since _A is an orthogonal rotation matrix, A_T = A^{-1}.
_A_T = (
    (_A[0][0], _A[1][0], _A[2][0]),
    (_A[0][1], _A[1][1], _A[2][1]),
    (_A[0][2], _A[1][2], _A[2][2]),
)


# ---------------------------------------------------------------------------
# J2000 equatorial coordinates of named galactic reference points
# ---------------------------------------------------------------------------

# Galactic Center (IAU 1958 definition point; closely matches Sgr A*)
_GC_RA   =  266.405100   # degrees
_GC_DEC  =  -28.936175   # degrees

# North Galactic Pole (in Coma Berenices)
_NGP_RA  =  192.859508
_NGP_DEC =   27.128336

# Galactic Anti-Center (directly opposite the GC, in Gemini/Auriga direction)
_GAC_RA  = (_GC_RA  + 180.0) % 360.0   # = 86.405100°
_GAC_DEC = -_GC_DEC                     # = +28.936175°

# South Galactic Pole
_SGP_RA  = (_NGP_RA + 180.0) % 360.0
_SGP_DEC = -_NGP_DEC

# Super-Galactic Center: center of the Local Supercluster (Virgo cluster / M87)
# Equatorial J2000: RA=187.7059°, Dec=+12.3911°  (~2° Libra ecliptic)
_SGC_RA  = 187.7059
_SGC_DEC =  12.3911


# ---------------------------------------------------------------------------
# Core coordinate transforms
# ---------------------------------------------------------------------------

def equatorial_to_galactic(ra: float, dec: float) -> tuple[float, float]:
    """
    Convert equatorial RA/Dec (degrees, J2000/ICRS) to galactic (ℓ, b).

    Returns
    -------
    (galactic_longitude, galactic_latitude) in degrees.
    ℓ ∈ [0°, 360°), b ∈ [−90°, +90°].
    """
    ra_r  = ra  * DEG2RAD
    dec_r = dec * DEG2RAD

    x = math.cos(dec_r) * math.cos(ra_r)
    y = math.cos(dec_r) * math.sin(ra_r)
    z = math.sin(dec_r)

    gx = _A[0][0]*x + _A[0][1]*y + _A[0][2]*z
    gy = _A[1][0]*x + _A[1][1]*y + _A[1][2]*z
    gz = _A[2][0]*x + _A[2][1]*y + _A[2][2]*z

    b = math.asin(max(-1.0, min(1.0, gz))) * RAD2DEG
    l = math.atan2(gy, gx) * RAD2DEG % 360.0
    return l, b


def galactic_to_equatorial(l: float, b: float) -> tuple[float, float]:
    """
    Convert galactic (ℓ, b) to equatorial RA/Dec (degrees, J2000/ICRS).

    Returns
    -------
    (right_ascension, declination) in degrees.
    RA ∈ [0°, 360°), Dec ∈ [−90°, +90°].
    """
    l_r = l * DEG2RAD
    b_r = b * DEG2RAD

    gx = math.cos(b_r) * math.cos(l_r)
    gy = math.cos(b_r) * math.sin(l_r)
    gz = math.sin(b_r)

    x = _A_T[0][0]*gx + _A_T[0][1]*gy + _A_T[0][2]*gz
    y = _A_T[1][0]*gx + _A_T[1][1]*gy + _A_T[1][2]*gz
    z = _A_T[2][0]*gx + _A_T[2][1]*gy + _A_T[2][2]*gz

    dec = math.asin(max(-1.0, min(1.0, z))) * RAD2DEG
    ra  = math.atan2(y, x) * RAD2DEG % 360.0
    return ra, dec


def ecliptic_to_galactic(
    lon: float,
    lat: float,
    obliquity: float,
) -> tuple[float, float]:
    """
    Convert ecliptic (longitude, latitude) to galactic (ℓ, b).

    Parameters
    ----------
    lon       : ecliptic longitude in degrees
    lat       : ecliptic latitude in degrees
    obliquity : true obliquity of the ecliptic in degrees (epoch of date)

    Returns
    -------
    (galactic_longitude, galactic_latitude) in degrees.
    """
    ra, dec = ecliptic_to_equatorial(lon, lat, obliquity)
    return equatorial_to_galactic(ra, dec)


def galactic_to_ecliptic(
    l: float,
    b: float,
    obliquity: float,
) -> tuple[float, float]:
    """
    Convert galactic (ℓ, b) to ecliptic (longitude, latitude).

    Parameters
    ----------
    l         : galactic longitude in degrees
    b         : galactic latitude in degrees
    obliquity : true obliquity of the ecliptic in degrees (epoch of date)

    Returns
    -------
    (ecliptic_longitude, ecliptic_latitude) in degrees.
    """
    ra, dec = galactic_to_equatorial(l, b)
    return equatorial_to_ecliptic(ra, dec, obliquity)


# ---------------------------------------------------------------------------
# GalacticPosition dataclass
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class GalacticPosition:
    """
    RITE: The Galactic Vessel — a body's place in the Milky Way frame.

    THEOREM: Holds the galactic longitude (l), galactic latitude (b), and
    source ecliptic coordinates for a single celestial body, together with
    derived proximity properties relative to galactic landmarks.

    RITE OF PURPOSE:
        Serves the Galactic Engine as the canonical result vessel for
        galactic coordinate computations. Without this vessel, callers would
        receive raw (l, b) floats with no proximity context, making galactic
        plane analysis, anti-center detection, and landmark distance queries
        impossible.

    LAW OF OPERATION:
        Responsibilities:
            - Store body name, galactic longitude l (0-360°), galactic
              latitude b (-90 to +90°), and source ecliptic coordinates.
            - Expose ``near_galactic_plane``, ``galactic_hemisphere``,
              ``angular_distance_to_gc``, and
              ``angular_distance_to_anticenter`` computed properties.
        Non-responsibilities:
            - Does not compute galactic coordinates (delegated to
              ``galactic_position_of``).
            - Does not apply proper motion or parallax corrections.
        Dependencies:
            - Populated by ``galactic_position_of()`` or
              ``all_galactic_positions()``.
        Structural invariants:
            - ``lon`` is always in [0, 360).
            - ``lat`` is always in [-90, +90].
        Succession stance: terminal — not designed for subclassing.

    Canon: Liu, Zhu & Zhang (2011, A&A 526, A16);
           IAU 1958 galactic coordinate system definition.

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.galactic.GalacticPosition",
        "risk": "medium",
        "api": {
            "public_methods": [
                "near_galactic_plane", "galactic_hemisphere",
                "angular_distance_to_gc", "angular_distance_to_anticenter",
                "__repr__"
            ],
            "public_attributes": ["body", "lon", "lat", "ecliptic_lon", "ecliptic_lat"]
        },
        "state": {
            "mutable": false,
            "fields": ["body", "lon", "lat", "ecliptic_lon", "ecliptic_lat"]
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
            "policy": "caller ensures valid ecliptic coordinates before construction"
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
    body         : body name (e.g., "Sun", "Jupiter")
    lon          : galactic longitude l (0-360°), increasing toward Cygnus
    lat          : galactic latitude b (-90 to +90°), positive = northern hemisphere
    ecliptic_lon : input ecliptic longitude (degrees)
    ecliptic_lat : input ecliptic latitude (degrees)
    """
    body:         str
    lon:          float   # galactic longitude ℓ
    lat:          float   # galactic latitude b
    ecliptic_lon: float
    ecliptic_lat: float

    @property
    def near_galactic_plane(self) -> bool:
        """True if body is within 5° of the galactic equator (dense stellar band)."""
        return abs(self.lat) <= 5.0

    @property
    def galactic_hemisphere(self) -> str:
        """'north' or 'south' galactic hemisphere (or 'plane' if within ±1°)."""
        if abs(self.lat) <= 1.0:
            return "plane"
        return "north" if self.lat > 0.0 else "south"

    @property
    def angular_distance_to_gc(self) -> float:
        """Great-circle angular distance from the Galactic Center (degrees)."""
        return _great_circle(self.lon, self.lat, 0.0, 0.0)

    @property
    def angular_distance_to_anticenter(self) -> float:
        """Great-circle angular distance from the Galactic Anti-Center (degrees)."""
        return _great_circle(self.lon, self.lat, 180.0, 0.0)

    def __repr__(self) -> str:
        return (
            f"GalacticPosition({self.body!r}, "
            f"ℓ={self.lon:.4f}°, b={self.lat:+.4f}°)"
        )


def _great_circle(l1: float, b1: float, l2: float, b2: float) -> float:
    """Great-circle distance between two galactic positions (degrees)."""
    l1r = l1 * DEG2RAD;  b1r = b1 * DEG2RAD
    l2r = l2 * DEG2RAD;  b2r = b2 * DEG2RAD
    cos_d = (math.sin(b1r)*math.sin(b2r)
             + math.cos(b1r)*math.cos(b2r)*math.cos(l1r - l2r))
    return math.acos(max(-1.0, min(1.0, cos_d))) * RAD2DEG


# ---------------------------------------------------------------------------
# Named galactic reference points
# ---------------------------------------------------------------------------

def galactic_reference_points(obliquity: float) -> dict[str, tuple[float, float]]:
    """
    Return the ecliptic longitudes and latitudes of the five principal
    galactic reference points, computed at the given obliquity.

    Parameters
    ----------
    obliquity : true obliquity of the ecliptic in degrees (epoch of chart)

    Returns
    -------
    dict mapping point name → (ecliptic_longitude, ecliptic_latitude) in degrees.

    Keys
    ----
    "Galactic Center"      — ℓ=0°,   b=0° (Sagittarius A* direction)
    "Galactic Anti-Center" — ℓ=180°, b=0° (Gemini/Auriga direction)
    "North Galactic Pole"  — b=+90°  (Coma Berenices / Leo border)
    "South Galactic Pole"  — b=−90°  (Sculptor constellation)
    "Super-Galactic Center"— center of Local Supercluster (M87/Virgo cluster)
    """
    def _ecl(ra: float, dec: float) -> tuple[float, float]:
        return equatorial_to_ecliptic(ra, dec, obliquity)

    return {
        "Galactic Center":       _ecl(_GC_RA,  _GC_DEC),
        "Galactic Anti-Center":  _ecl(_GAC_RA, _GAC_DEC),
        "North Galactic Pole":   _ecl(_NGP_RA,  _NGP_DEC),
        "South Galactic Pole":   _ecl(_SGP_RA,  _SGP_DEC),
        "Super-Galactic Center": _ecl(_SGC_RA,  _SGC_DEC),
    }


# ---------------------------------------------------------------------------
# Single-body convenience function
# ---------------------------------------------------------------------------

def galactic_position_of(
    body: str,
    ecliptic_lon: float,
    ecliptic_lat: float,
    obliquity: float,
) -> GalacticPosition:
    """
    Compute the galactic position of a single body from its ecliptic coordinates.

    Parameters
    ----------
    body        : name label (e.g., "Mars")
    ecliptic_lon: ecliptic longitude in degrees
    ecliptic_lat: ecliptic latitude in degrees
    obliquity   : true obliquity of the ecliptic in degrees (epoch of date)

    Returns
    -------
    GalacticPosition
    """
    l, b = ecliptic_to_galactic(ecliptic_lon, ecliptic_lat, obliquity)
    return GalacticPosition(
        body=body,
        lon=l,
        lat=b,
        ecliptic_lon=ecliptic_lon,
        ecliptic_lat=ecliptic_lat,
    )


# ---------------------------------------------------------------------------
# Batch function for a full chart
# ---------------------------------------------------------------------------

def all_galactic_positions(
    body_data: dict[str, tuple[float, float]],
    obliquity: float,
) -> list[GalacticPosition]:
    """
    Compute galactic positions for all bodies in a chart.

    Parameters
    ----------
    body_data : mapping of body name → (ecliptic_longitude, ecliptic_latitude)
                in degrees.  PlanetData objects work if you pass
                {name: (p.longitude, p.latitude) for name, p in chart.planets.items()}.
    obliquity : true obliquity of the ecliptic in degrees (use chart.obliquity).

    Returns
    -------
    List of GalacticPosition, one per body, in input order.
    """
    return [
        galactic_position_of(name, lon, lat, obliquity)
        for name, (lon, lat) in body_data.items()
    ]
