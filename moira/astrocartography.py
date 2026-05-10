"""
Moira - Astrocartography Engine
=================================

Archetype: Engine

Purpose
-------
Governs computation of Astro*Carto*Graphy (ACG) lines - the geographic
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
``ACGLine``        - vessel for a single ACG line (one planet, one line type).
``acg_lines``      - compute all four ACG lines for a dict of bodies.
``acg_from_chart`` - convenience wrapper for a ``ChartContext``.
"""


import inspect
import math
from dataclasses import dataclass, field

from .constants import DEG2RAD, RAD2DEG, Body

# WGS-84 first eccentricity squared: e^2 = 1 - (b/a)^2 ~= 0.006694379990
# Used to convert geodetic latitude -> geocentric latitude for the horizon
# hour-angle formula. The maximum difference is ~11.5 arcminutes near +/-45 deg,
# which can shift an ASC/DSC line by several kilometres on a rendered map.
_WGS84_E2 = 0.00669437999014

__all__ = [
    "ACGLine",
    "acg_lines",
    "acg_from_chart",
]


@dataclass(slots=True)
class ACGLine:
    """
    RITE: The Geographic Vessel - a planet's line of power across the Earth.

    THEOREM: Holds the planet name, line type (MC/IC/ASC/DSC), and either
    a single meridian longitude or a list of sampled (latitude, longitude)
    curve points representing one ACG line.

    RITE OF PURPOSE:
        Serves the Astrocartography Engine as the canonical result vessel for
        ACG line data. Each planet produces four primary geographic features;
        without this vessel, callers would have no structured representation
        of the curves and meridians needed for map rendering.

    LAW OF OPERATION:
        Responsibilities:
            - Store the planet name and line type string.
            - For MC/IC lines: store the single geographic longitude.
            - For ASC/DSC lines: store sampled (latitude, longitude) curve points.
        Non-responsibilities:
            - Does not compute lines (delegated to ``acg_lines``).
            - Does not render or project lines onto a map.
        Dependencies:
            - Populated by ``acg_lines()`` or ``acg_from_chart()``.
        Structural invariants:
            - For MC/IC: ``longitude`` is set, ``points`` is empty.
            - For ASC/DSC: ``points`` is non-empty, ``longitude`` is None.
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
    """

    planet: str
    line_type: str
    longitude: float | None = None
    points: list[tuple[float, float]] = field(default_factory=list)

    def __repr__(self) -> str:
        if self.line_type in ("MC", "IC"):
            return (
                f"ACGLine({self.planet!r}, {self.line_type!r}, "
                f"lon={self.longitude:.4f}deg)"
            )
        return (
            f"ACGLine({self.planet!r}, {self.line_type!r}, "
            f"{len(self.points)} points)"
        )


def _compute_acg_curve_samples(
    ra: float,
    dec: float,
    gmst_deg: float,
    lats: list[float],
    sin_h0: float,
) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    """Return ASC and DSC samples for a fixed RA/Dec body."""
    dec_r = dec * DEG2RAD
    sin_dec = math.sin(dec_r)
    cos_dec = math.cos(dec_r)
    asc_pts: list[tuple[float, float]] = []
    dsc_pts: list[tuple[float, float]] = []

    for phi in lats:
        phi_r = phi * DEG2RAD
        phi_gc_r = math.atan((1.0 - _WGS84_E2) * math.tan(phi_r))
        denom = math.cos(phi_gc_r) * cos_dec
        if abs(denom) < 1e-12:
            continue

        cos_ha = (sin_h0 - math.sin(phi_gc_r) * sin_dec) / denom
        if abs(cos_ha) > 1.0:
            continue

        ha_deg = math.degrees(math.acos(cos_ha))
        asc_pts.append((phi, (ra - gmst_deg - ha_deg) % 360.0))
        dsc_pts.append((phi, (ra - gmst_deg + ha_deg) % 360.0))

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
    planet_ra_dec : dict of body name -> (RA degrees, Dec degrees).
                    RA and Dec are typically apparent geocentric equatorial
                    coordinates.
    gmst_deg      : Greenwich Apparent Sidereal Time at the birth moment (deg).
    lat_step      : latitude sampling resolution for ASC/DSC curves (degrees).
    jd_ut         : Julian Day (UT1). Required for topocentric lunar correction.
    refraction    : If True, apply atmospheric refraction (~34') to the horizon.

    Returns
    -------
    list[ACGLine] - four lines per planet (MC, IC, ASC, DSC).
    """
    from .planets import sky_position_at

    lines: list[ACGLine] = []
    h0 = -0.5667 if refraction else 0.0
    sin_h0 = math.sin(h0 * DEG2RAD)
    lats = [
        -89.0 + i * lat_step
        for i in range(int(178.0 / lat_step) + 1)
        if -89.0 + i * lat_step <= 89.0
    ]

    for body, (ra_geo, dec_geo) in planet_ra_dec.items():
        lon_mc = (ra_geo - gmst_deg) % 360.0
        lon_ic = (lon_mc + 180.0) % 360.0

        lines.append(ACGLine(planet=body, line_type="MC", longitude=lon_mc))
        lines.append(ACGLine(planet=body, line_type="IC", longitude=lon_ic))

        if body != Body.MOON or jd_ut is None:
            asc_points, dsc_points = _compute_acg_curve_samples(
                ra_geo, dec_geo, gmst_deg, lats, sin_h0
            )
        else:
            asc_points = []
            dsc_points = []
            for phi in lats:
                phi_r = phi * DEG2RAD
                phi_gc_r = math.atan((1.0 - _WGS84_E2) * math.tan(phi_r))

                sky = sky_position_at(body, jd_ut, observer_lat=phi, observer_lon=lon_mc)
                ra, dec = sky.right_ascension, sky.declination
                dec_r = dec * DEG2RAD
                denom = math.cos(phi_gc_r) * math.cos(dec_r)
                if abs(denom) < 1e-12:
                    continue

                cos_ha = (sin_h0 - math.sin(phi_gc_r) * math.sin(dec_r)) / denom
                if abs(cos_ha) > 1.0:
                    continue

                ha_deg = math.degrees(math.acos(cos_ha))
                asc_points.append((phi, (ra - gmst_deg - ha_deg) % 360.0))
                dsc_points.append((phi, (ra - gmst_deg + ha_deg) % 360.0))

        lines.append(ACGLine(planet=body, line_type="ASC", points=asc_points))
        lines.append(ACGLine(planet=body, line_type="DSC", points=dsc_points))

    return lines


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
    bodies      : list of body names to include. Defaults to all bodies
                  present in ``chart.planets``.
    lat_step    : latitude sampling step passed through to :func:`acg_lines`.
    refraction  : if True, apply atmospheric refraction to horizon curves.

    Returns
    -------
    list[ACGLine] - four lines per planet.
    """
    from .planets import sky_position_at
    from .julian import apparent_sidereal_time, ut_to_tt
    from .obliquity import nutation, true_obliquity

    if bodies is None:
        bodies = list(chart.planets.keys())

    jd_tt = ut_to_tt(chart.jd_ut)
    dpsi, _ = nutation(jd_tt)
    obliq = true_obliquity(jd_tt)
    gmst_deg = apparent_sidereal_time(chart.jd_ut, dpsi, obliq)

    planet_ra_dec: dict[str, tuple[float, float]] = {}
    for body in bodies:
        sky = sky_position_at(
            body,
            chart.jd_ut,
            observer_lat=chart.latitude,
            observer_lon=chart.longitude,
        )
        planet_ra_dec[body] = (sky.right_ascension, sky.declination)

    params = inspect.signature(acg_lines).parameters
    kwargs: dict[str, object] = {"lat_step": lat_step}
    if "jd_ut" in params:
        kwargs["jd_ut"] = chart.jd_ut
    if "refraction" in params:
        kwargs["refraction"] = refraction
    return acg_lines(planet_ra_dec, gmst_deg, **kwargs)
