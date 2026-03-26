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

from .constants import DEG2RAD, RAD2DEG

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

    THEOREM: Holds the planet name, line type (MC/IC/ASC/DSC), and either a
    single meridian longitude or a list of sampled (latitude, longitude) curve
    points representing one Astro*Carto*Graphy line.

    RITE OF PURPOSE:
        Serves the Astrocartography Engine as the canonical result vessel for
        ACG line data. Each planet produces four lines; without this vessel,
        callers would have no structured representation of the geographic
        curves and meridians needed for map rendering or relocation analysis.

    LAW OF OPERATION:
        Responsibilities:
            - Store the planet name and line type string.
            - For MC/IC lines: store the single geographic longitude valid at
              all latitudes (``longitude`` field).
            - For ASC/DSC lines: store the sampled (lat, lon) curve points
              (``points`` field).
        Non-responsibilities:
            - Does not compute lines (delegated to ``acg_lines``).
            - Does not render or project lines onto a map.
            - Does not validate that ``line_type`` is one of MC/IC/ASC/DSC.
        Dependencies:
            - Populated exclusively by ``acg_lines()`` or ``acg_from_chart()``.
        Structural invariants:
            - For MC/IC: ``longitude`` is set, ``points`` is empty.
            - For ASC/DSC: ``points`` is non-empty (may be empty at extreme
              latitudes where the body is circumpolar), ``longitude`` is None.
        Succession stance: terminal — not designed for subclassing.

    Canon: Lewis, "Astro*Carto*Graphy" (1976);
           Meeus, "Astronomical Algorithms" Ch. 24.

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.astrocartography.ACGLine",
        "risk": "medium",
        "api": {
            "public_methods": ["__repr__"],
            "public_attributes": ["planet", "line_type", "longitude", "points"]
        },
        "state": {
            "mutable": false,
            "fields": ["planet", "line_type", "longitude", "points"]
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
            "policy": "caller ensures valid RA/Dec/GMST before construction"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "kiro"
    }
    [/MACHINE_CONTRACT]

    For MC/IC lines the line is a meridian: ``longitude`` holds the single
    geographic longitude value, valid for all latitudes (``points`` is empty).

    For ASC/DSC lines the line is a curve across the globe: ``points`` is a
    list of ``(latitude, longitude)`` pairs sampled from -90° to +90°
    (``longitude`` is ``None``).
    """

    planet:    str
    line_type: str              # "MC", "IC", "ASC", or "DSC"

    # For MC/IC lines: single geographic longitude, valid at every latitude.
    longitude: float | None = None

    # For ASC/DSC lines: sampled (lat, lon) curve points.
    points: list[tuple[float, float]] = field(default_factory=list)

    def __repr__(self) -> str:
        if self.line_type in ("MC", "IC"):
            return (
                f"ACGLine({self.planet!r}, {self.line_type!r}, "
                f"lon={self.longitude:.4f}°)"
            )
        return (
            f"ACGLine({self.planet!r}, {self.line_type!r}, "
            f"{len(self.points)} points)"
        )


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------

def acg_lines(
    planet_ra_dec: dict[str, tuple[float, float]],
    gmst_deg: float,
    lat_step: float = 2.0,
) -> list[ACGLine]:
    """
    Compute ACG lines for all planets given their RA/Dec and GMST at birth.

    Parameters
    ----------
    planet_ra_dec : dict of body name → (RA degrees, Dec degrees).
                    RA and Dec must be apparent geocentric equatorial coordinates.
    gmst_deg      : Greenwich Mean Sidereal Time at the birth moment (degrees).
    lat_step      : latitude sampling resolution for ASC/DSC curves (degrees).
                    Smaller values produce smoother curves at the cost of more
                    computation.  Default 2.0°.

    Returns
    -------
    list[ACGLine] — four lines per planet (MC, IC, ASC, DSC), in the order the
    planets appear in *planet_ra_dec*.

    Notes
    -----
    MC/IC lines are simple meridians (geographic longitude = constant).  The
    formula is exact regardless of latitude.

    ASC/DSC lines are computed by sampling geographic latitudes in the range
    [−89°, +89°] (the poles are excluded because the hour-angle formula is
    singular there).  For each latitude the hour angle at which the planet
    rises or sets is derived from:

        cos HA = −tan φ' · tan δ

    where φ' is the *geocentric* latitude (converted from geodetic φ via
    ``tan φ' = (1 − e²) · tan φ``, WGS-84) and δ is the planet's declination.
    The geodetic→geocentric correction shifts lines by up to ~11.5′ of latitude
    (≈ several kilometres) near ±45°; it is applied here for consistency with
    the sub-milliarcsecond precision standard of the rest of the library.
    If |cos HA| > 1 the planet is either circumpolar or never rises at that
    latitude; those latitudes are silently omitted from the curve.
    """
    lines: list[ACGLine] = []

    # Sample latitudes for ASC/DSC curves (avoid ±90° singularity).
    lats = [
        -89.0 + i * lat_step
        for i in range(int(178.0 / lat_step) + 1)
        if -89.0 + i * lat_step <= 89.0
    ]

    for body, (ra, dec) in planet_ra_dec.items():
        # ------------------------------------------------------------------
        # MC line — planet on the upper meridian
        # Geographic longitude where LST = RA  →  lon = RA − GMST
        # ------------------------------------------------------------------
        lon_mc = (ra - gmst_deg) % 360.0

        # ------------------------------------------------------------------
        # IC line — planet on the lower meridian (antipodal)
        # ------------------------------------------------------------------
        lon_ic = (lon_mc + 180.0) % 360.0

        lines.append(ACGLine(planet=body, line_type="MC", longitude=lon_mc))
        lines.append(ACGLine(planet=body, line_type="IC", longitude=lon_ic))

        # ------------------------------------------------------------------
        # ASC / DSC lines — planet on the eastern / western horizon
        # ------------------------------------------------------------------
        dec_r = dec * DEG2RAD
        tan_dec = math.tan(dec_r)

        asc_points: list[tuple[float, float]] = []
        dsc_points: list[tuple[float, float]] = []

        for phi in lats:
            phi_r    = phi * DEG2RAD
            # Convert geodetic → geocentric latitude before the horizon formula.
            # tan φ' = (1 − e²) · tan φ  (WGS-84 spheroid correction)
            phi_gc_r = math.atan((1.0 - _WGS84_E2) * math.tan(phi_r))
            cos_ha   = -math.tan(phi_gc_r) * tan_dec

            # Skip latitudes where the planet is circumpolar or never rises.
            if abs(cos_ha) > 1.0:
                continue

            ha_deg = math.acos(cos_ha) * RAD2DEG  # always in [0°, 180°]

            # ASC: planet rising on the eastern horizon
            lon_asc = (ra - gmst_deg - ha_deg) % 360.0
            asc_points.append((phi, lon_asc))

            # DSC: planet setting on the western horizon
            lon_dsc = (ra - gmst_deg + ha_deg) % 360.0
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
) -> list[ACGLine]:
    """
    Convenience wrapper: compute ACG lines directly from a Moira ChartContext.

    Extracts apparent RA/Dec for each requested body via
    ``moira.planets.sky_position_at()`` and GMST from ``chart.jd_ut``.

    Parameters
    ----------
    chart       : a ``ChartContext`` instance (from ``moira.chart``).
    bodies      : list of body names to include.  Defaults to all bodies
                  present in ``chart.planets`` (the classical ten planets).
    lat_step    : latitude sampling step passed through to :func:`acg_lines`.

    Returns
    -------
    list[ACGLine] — four lines per planet.
    """
    from .planets import sky_position_at
    from .julian import apparent_sidereal_time, ut_to_tt
    from .obliquity import nutation, true_obliquity

    if bodies is None:
        bodies = list(chart.planets.keys())

    # Use GAST (apparent sidereal time), not GMST — planets' apparent RA is
    # referred to the true equinox, so the correct counterpart is GAST which
    # includes the equation of the equinoxes (Δψ·cos ε).
    jd_tt   = ut_to_tt(chart.jd_ut)
    dpsi, _ = nutation(jd_tt)
    obliq   = true_obliquity(jd_tt)
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

    return acg_lines(planet_ra_dec, gmst_deg, lat_step=lat_step)
