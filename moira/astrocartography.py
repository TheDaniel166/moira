"""
Moira — Astrocartography Engine
=================================

Archetype: Engine

Purpose
-------
Governs computation of Astro*Carto*Graphy (ACG) lines — the geographic
curves and meridians showing where each natal planet was on the MC, IC,
Ascendant, or Descendant at the birth moment.

Boundary declaration
--------------------
Owns: MC/IC meridian computation, ASC/DSC curve sampling, and the
      ``ACGLine`` result vessel.
Delegates: apparent RA/Dec retrieval to ``moira.planets.sky_position_at``,
           Greenwich Apparent Sidereal Time to ``moira.julian``,
           nutation to ``moira.obliquity``.

Import-time side effects: None

External dependency assumptions
--------------------------------
No Qt main thread required. No database access. Requires caller to supply
apparent geocentric equatorial coordinates (RA/Dec) and GMST, or a
``ChartContext`` for the convenience wrapper.

Public surface
--------------
``ACGLine``        — vessel for a single ACG line (one planet, one line type).
``acg_lines``      — compute all four ACG lines for a dict of bodies.
``acg_from_chart`` — convenience wrapper for a ``ChartContext``.
"""


import math
from dataclasses import dataclass, field

from .constants import DEG2RAD, RAD2DEG, Body
from .geoutils import wrap_longitude_deg

try:
    import numpy as _np
    _HAS_NUMPY = True
except ImportError:
    _np = None
    _HAS_NUMPY = False

# WGS-84 first eccentricity squared: e² = 1 − (b/a)² ≈ 0.006694379990
# Used to convert geodetic latitude → geocentric latitude for the horizon
# hour-angle formula.  The maximum difference is ~11.5′ near ±45°, which
# can shift an ASC/DSC line by several kilometres on a rendered map.
_WGS84_E2 = 0.00669437999014

__all__ = [
    "ACGLine",
    "acg_lines",
    "acg_from_chart",
]

# ---------------------------------------------------------------------------
# Data structure
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class ACGLine:
    """
    RITE: The Geographic Vessel — a planet's line of power across the Earth.

    THEOREM: Holds the planet name, line type (MC/IC/ASC/DSC/ZEN/NAD), and either
    a single meridian longitude, a single geographic point, or a list of sampled
    (latitude, longitude) curve points representing one ACG line.

    RITE OF PURPOSE:
        Serves the Astrocartography Engine as the canonical result vessel for
        ACG line data. Each planet produces six primary geographic features;
        without this vessel, callers would have no structured representation
        of the curves, meridians, and zenith points needed for map rendering.

    LAW OF OPERATION:
        Responsibilities:
            - Store the planet name and line type string.
            - For MC/IC lines: store the single geographic longitude.
            - For ASC/DSC lines: store sampled (lat, lon) curve points.
            - For ZEN/NAD points: store the single geographic (lat, lon) point.
        Non-responsibilities:
            - Does not compute lines (delegated to ``acg_lines``).
            - Does not render or project lines onto a map.
        Dependencies:
            - Populated by ``acg_lines()`` or ``acg_from_chart()``.
        Structural invariants:
            - For MC/IC: ``longitude`` is set, ``points`` is empty.
            - For ASC/DSC: ``points`` is non-empty, ``longitude`` is None.
            - For ZEN/NAD: ``points`` contains exactly one tuple, ``longitude`` is None.
        Succession stance: terminal.

    Canon: Lewis, "Astro*Carto*Graphy" (1976);
           Meeus, "Astronomical Algorithms" Ch. 24.

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.astrocartography.ACGLine",
        "risk": "medium",
        "api": {"frozen": ["planet", "line_type", "longitude", "points"], "internal": []},
        "state": {"mutable": false, "owners": []},
        "effects": {"signals_emitted": [], "io": [], "mutation": "none"},
        "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
        "failures": {"policy": "raise"},
        "succession": {"stance": "terminal"},
        "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]

    For MC/IC lines: ``longitude`` holds the geographic longitude value.
    For ASC/DSC lines: ``points`` holds a list of ``(latitude, longitude)`` pairs.
    For ZEN/NAD points: ``points`` holds a single ``(latitude, longitude)`` pair.
    """

    planet:    str
    line_type: str              # "MC", "IC", "ASC", "DSC", "ZEN", or "NAD"

    # For MC/IC lines: single geographic longitude, valid at every latitude.
    longitude: float | None = None

    # For ASC/DSC lines (sampled points) or ZEN/NAD points (single point).
    points: list[tuple[float, float]] = field(default_factory=list)

    def __repr__(self) -> str:
        if self.line_type in ("MC", "IC"):
            return (
                f"ACGLine({self.planet!r}, {self.line_type!r}, "
                f"lon={self.longitude:.4f}°)"
            )
        if self.line_type in ("ZEN", "NAD"):
            lat, lon = self.points[0]
            return (
                f"ACGLine({self.planet!r}, {self.line_type!r}, "
                f"at {lat:.4f}°, {lon:.4f}°)"
            )
        return (
            f"ACGLine({self.planet!r}, {self.line_type!r}, "
            f"{len(self.points)} points)"
        )



# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------

def _compute_acg_vectorized(
    ra: float,
    dec: float,
    gmst_deg: float,
    lats: list[float],
    sin_h0: float,
) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    """Optional NumPy-accelerated path for ASC/DSC sampling."""
    phi = _np.array(lats, dtype=_np.float64)
    phi_r = phi * DEG2RAD
    
    # Spheroid correction
    phi_gc_r = _np.arctan((1.0 - _WGS84_E2) * _np.tan(phi_r))
    
    dec_r = dec * DEG2RAD
    cos_phi = _np.cos(phi_gc_r)
    cos_dec = math.cos(dec_r)
    
    denom = cos_phi * cos_dec
    # Avoid division by zero at poles (though lats are already clipped)
    mask = _np.abs(denom) > 1e-12
    
    cos_ha = _np.full_like(phi, _np.nan)
    cos_ha[mask] = (sin_h0 - _np.sin(phi_gc_r[mask]) * math.sin(dec_r)) / denom[mask]
    
    # Filter for valid HA range
    valid_mask = (_np.abs(cos_ha) <= 1.0) & mask
    
    phi_valid = phi[valid_mask]
    ha_deg = _np.arccos(cos_ha[valid_mask]) * RAD2DEG
    
    # ASC / DSC
    lon_asc = (ra - gmst_deg - ha_deg) % 360.0
    lon_dsc = (ra - gmst_deg + ha_deg) % 360.0
    
    # Convert to wrapped longitude [-180, 180]
    # (Doing this via math to avoid complex numpy wrapping logic if possible, 
    # but let's just use the scalar wrapper for consistency for now)
    asc_pts = [(float(p), wrap_longitude_deg(float(l))) for p, l in zip(phi_valid, lon_asc)]
    dsc_pts = [(float(p), wrap_longitude_deg(float(l))) for p, l in zip(phi_valid, lon_dsc)]
    
    return asc_pts, dsc_pts


def acg_lines(
    planet_ra_dec: dict[str, tuple[float, float]],
    gmst_deg: float,
    lat_step: float = 2.0,
    jd_ut: float | None = None,
    refraction: bool = False,
) -> list[ACGLine]:
    """
    Compute ACG lines for all planets given their RA/Dec and GMST at birth.

    Parameters
    ----------
    planet_ra_dec : dict of body name → (RA degrees, Dec degrees).
                    RA and Dec are typically apparent geocentric equatorial
                    coordinates.
    gmst_deg      : Greenwich Apparent Sidereal Time at the birth moment (deg).
    lat_step      : latitude sampling resolution for ASC/DSC curves (degrees).
    jd_ut         : Julian Day (UT1). Required for topocentric lunar correction.
    refraction    : If True, apply atmospheric refraction (~34') to the horizon.

    Returns
    -------
    list[ACGLine] — six lines/points per planet (MC, IC, ASC, DSC, ZEN, NAD).
    """
    from .planets import sky_position_at

    lines: list[ACGLine] = []

    # Horizon altitude for ASC/DSC (0.0 geometric, -0.5667 apparent with refraction)
    h0 = -0.5667 if refraction else 0.0
    sin_h0 = math.sin(h0 * DEG2RAD)

    # Sample latitudes for ASC/DSC curves (avoid ±90° singularity).
    lats = [
        -89.0 + i * lat_step
        for i in range(int(178.0 / lat_step) + 1)
        if -89.0 + i * lat_step <= 89.0
    ]

    for body, (ra_geo, dec_geo) in planet_ra_dec.items():
        # 1. MC / IC Meridians
        lon_mc = wrap_longitude_deg(ra_geo - gmst_deg)
        lon_ic = wrap_longitude_deg(lon_mc + 180.0)

        lines.append(ACGLine(planet=body, line_type="MC", longitude=lon_mc))
        lines.append(ACGLine(planet=body, line_type="IC", longitude=lon_ic))

        # 2. ZEN / NAD Points
        lines.append(ACGLine(planet=body, line_type="ZEN", points=[(dec_geo, lon_mc)]))
        lines.append(ACGLine(planet=body, line_type="NAD", points=[(-dec_geo, lon_ic)]))

        # 3. ASC / DSC Lines
        # Use vectorized path if NumPy is available and not doing topocentric Moon.
        if _HAS_NUMPY and not (body == Body.MOON and jd_ut is not None):
            asc_points, dsc_points = _compute_acg_vectorized(
                ra_geo, dec_geo, gmst_deg, lats, sin_h0
            )
        else:
            asc_points = []
            dsc_points = []
            for phi in lats:
                phi_r = phi * DEG2RAD
                phi_gc_r = math.atan((1.0 - _WGS84_E2) * math.tan(phi_r))
                
                if body == Body.MOON and jd_ut is not None:
                    sky = sky_position_at(body, jd_ut, observer_lat=phi, observer_lon=lon_mc)
                    ra, dec = sky.right_ascension, sky.declination
                else:
                    ra, dec = ra_geo, dec_geo

                dec_r = dec * DEG2RAD
                cos_phi = math.cos(phi_gc_r)
                cos_dec = math.cos(dec_r)
                
                denom = cos_phi * cos_dec
                if abs(denom) < 1e-12:
                    continue
                    
                cos_ha = (sin_h0 - math.sin(phi_gc_r) * math.sin(dec_r)) / denom
                if abs(cos_ha) > 1.0:
                    continue

                ha_deg = math.acos(cos_ha) * RAD2DEG
                lon_asc = wrap_longitude_deg(ra - gmst_deg - ha_deg)
                asc_points.append((phi, lon_asc))
                lon_dsc = wrap_longitude_deg(ra - gmst_deg + ha_deg)
                dsc_points.append((phi, lon_dsc))

        lines.append(ACGLine(planet=body, line_type="ASC", points=asc_points))
        lines.append(ACGLine(planet=body, line_type="DSC", points=dsc_points))

    return lines


# ---------------------------------------------------------------------------
# Convenience wrapper for a Moira ChartContext
# ---------------------------------------------------------------------------

def acg_from_chart(
    chart,
    bodies: list[str] | None = None,
    lat_step: float = 2.0,
    refraction: bool = False,
) -> list[ACGLine]:
    """
    Convenience wrapper: compute ACG lines directly from a Moira ChartContext.

    Extracts apparent RA/Dec for each requested body via
    ``moira.planets.sky_position_at()`` and GMST from ``chart.jd_ut``.

    Parameters
    ----------
    chart       : a ``ChartContext`` instance (from ``moira.chart``).
    bodies      : list of body names to include.  Defaults to all bodies
                  present in ``chart.planets``.
    lat_step    : latitude sampling step passed through to :func:`acg_lines`.
    refraction  : if True, apply atmospheric refraction to horizon curves.

    Returns
    -------
    list[ACGLine] — six lines/points per planet.
    """
    from .planets import sky_position_at
    from .julian import apparent_sidereal_time, ut_to_tt
    from .obliquity import nutation, true_obliquity

    if bodies is None:
        bodies = list(chart.planets.keys())

    # Use GAST (apparent sidereal time)
    jd_tt   = ut_to_tt(chart.jd_ut)
    dpsi, _ = nutation(jd_tt)
    obliq   = true_obliquity(jd_tt)
    gmst_deg = apparent_sidereal_time(chart.jd_ut, dpsi, obliq)

    planet_ra_dec: dict[str, tuple[float, float]] = {}
    for body in bodies:
        # Initial geocentric RA/Dec for meridians and seed
        sky = sky_position_at(
            body,
            chart.jd_ut,
            observer_lat=chart.latitude,
            observer_lon=chart.longitude,
        )
        planet_ra_dec[body] = (sky.right_ascension, sky.declination)

    return acg_lines(
        planet_ra_dec,
        gmst_deg,
        lat_step=lat_step,
        jd_ut=chart.jd_ut,
        refraction=refraction
    )
