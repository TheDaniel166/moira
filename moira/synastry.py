"""
Moira — Synastry Engine
=======================

Archetype: Engine

Purpose
-------
Governs relationship chart computation: synastry inter-aspects, composite
midpoint charts, and Davison relationship charts.

Boundary declaration
--------------------
Owns: inter-chart aspect comparison, composite midpoint arithmetic,
      Davison time/location midpoint resolution and chart construction.
Delegates: planetary position computation to ``moira.planets``,
           house calculation to ``moira.houses``,
           aspect detection to ``moira.aspects``,
           Julian Day arithmetic to ``moira.julian``.

Import-time side effects: None

External dependency assumptions
--------------------------------
No Qt main thread required. No database access. Pure computation over
``ChartContext`` instances and Julian Day values.

Public surface
--------------
``synastry_aspects`` — inter-aspects between two natal charts.
``composite_chart``  — midpoint composite chart from two natal charts.
``davison_chart``    — real chart at the midpoint time and location.
``CompositeChart``   — vessel for composite chart data.
``DavisonInfo``      — vessel for Davison midpoint time/location metadata.
``DavisonChart``     — vessel for the Davison relationship chart.
"""


import math
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import TYPE_CHECKING

from .constants import Body, DEG2RAD, RAD2DEG
from .midpoints import _midpoint
from .aspects import AspectData, aspects_between
from .julian import jd_from_datetime, datetime_from_jd, delta_t
from .planets import all_planets_at
from .nodes import true_node, mean_node, mean_lilith
from .obliquity import true_obliquity
from .houses import HouseCusps, calculate_houses
from .constants import HouseSystem, sign_of
from .spk_reader import get_reader, SpkReader

if TYPE_CHECKING:
    from .__init__ import Chart


# ---------------------------------------------------------------------------
# Synastry aspects (inter-aspects between two charts)
# ---------------------------------------------------------------------------

def synastry_aspects(
    chart_a: "Chart",
    chart_b: "Chart",
    tier: int = 2,
    orbs: dict[float, float] | None = None,
    orb_factor: float = 1.0,
    include_nodes: bool = True,
) -> list[AspectData]:
    """
    Find all inter-aspects between two natal charts (synastry).

    Every body in chart_a is compared to every body in chart_b.
    No intra-chart aspects are included.

    Parameters
    ----------
    chart_a       : first natal Chart
    chart_b       : second natal Chart
    tier          : aspect set (1=major only, 2=all, default 2)
    orbs          : custom orb table {angle: max_orb}
    orb_factor    : multiplier for default orbs
    include_nodes : include True Node / Mean Node / Lilith

    Returns
    -------
    List of AspectData sorted by orb.
    """
    lons_a = chart_a.longitudes(include_nodes=include_nodes)
    lons_b = chart_b.longitudes(include_nodes=include_nodes)

    speeds_a = chart_a.speeds()
    speeds_b = chart_b.speeds()

    results: list[AspectData] = []
    for name_a, lon_a in lons_a.items():
        for name_b, lon_b in lons_b.items():
            found = aspects_between(
                name_a, lon_a,
                name_b, lon_b,
                tier=tier,
                orbs=orbs,
                orb_factor=orb_factor,
                speed_a=speeds_a.get(name_a),
                speed_b=speeds_b.get(name_b),
            )
            results.extend(found)

    results.sort(key=lambda a: a.orb)
    return results


# ---------------------------------------------------------------------------
# Composite chart
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class CompositeChart:
    """
    RITE: The Midpoint Vessel — synthetic chart born of two lives merged.

    THEOREM: Holds the midpoint ecliptic longitudes of corresponding planetary
    positions from two natal charts, forming a synthetic composite chart.

    RITE OF PURPOSE:
        Serves the Synastry Engine as the primary data vessel for composite
        relationship charts. A composite chart does not correspond to any real
        moment in time; it represents the combined midpoint geometry of two
        natal charts. Without this vessel, composite chart data would have no
        structured home in the pillar.

    LAW OF OPERATION:
        Responsibilities:
            - Store midpoint planetary longitudes keyed by body name.
            - Store midpoint node longitudes keyed by node name.
            - Store optional midpoint house cusps and angles (ASC, MC).
            - Expose a flat ``longitudes()`` accessor for downstream aspect work.
        Non-responsibilities:
            - Does not compute midpoints (delegated to ``composite_chart``).
            - Does not cast a real chart (no ephemeris access).
            - Does not validate that midpoints are astronomically meaningful.
        Dependencies:
            - Populated exclusively by ``composite_chart()``.
        Structural invariants:
            - ``planets`` and ``nodes`` are always present (may be empty dicts).
            - ``cusps`` is an empty list when house data was not requested.
            - ``asc`` and ``mc`` are ``None`` when house data was not requested.
        Succession stance: terminal — not designed for subclassing.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.synastry.CompositeChart",
        "risk": "medium",
        "api": {
            "public_methods": ["longitudes"],
            "public_attributes": ["planets", "nodes", "cusps", "asc", "mc", "jd_mean"]
        },
        "state": {
            "mutable": false,
            "fields": ["planets", "nodes", "cusps", "asc", "mc", "jd_mean"]
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
            "policy": "caller ensures valid midpoint data before construction"
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
    planets   : body name → midpoint ecliptic longitude (°)
    nodes     : node name → midpoint ecliptic longitude (°)
    cusps     : 12 house cusp midpoints (°), or empty list if not computed
    asc       : midpoint ASC longitude (°), or None
    mc        : midpoint MC longitude (°), or None
    jd_mean   : arithmetic mean of the two natal Julian Days (for reference)
    """
    planets:  dict[str, float]
    nodes:    dict[str, float]
    cusps:    list[float]
    asc:      float | None
    mc:       float | None
    jd_mean:  float

    def longitudes(self, include_nodes: bool = True) -> dict[str, float]:
        """Return flat dict body_name → composite longitude."""
        lons = dict(self.planets)
        if include_nodes:
            lons.update(self.nodes)
        return lons


def composite_chart(
    chart_a: "Chart",
    chart_b: "Chart",
    houses_a: HouseCusps | None = None,
    houses_b: HouseCusps | None = None,
) -> CompositeChart:
    """
    Build a Composite chart from two natal charts.

    Matching planets are combined via the shorter-arc midpoint.  If both
    sets of house cusps are supplied, composite house cusps are also computed.

    Parameters
    ----------
    chart_a / chart_b   : natal Chart instances
    houses_a / houses_b : optional natal HouseCusps for composite houses

    Returns
    -------
    CompositeChart instance
    """
    # --- Planet midpoints ---
    planets: dict[str, float] = {}
    for name, pd_a in chart_a.planets.items():
        if name in chart_b.planets:
            planets[name] = _midpoint(pd_a.longitude, chart_b.planets[name].longitude)

    # --- Node midpoints ---
    nodes: dict[str, float] = {}
    for name, nd_a in chart_a.nodes.items():
        if name in chart_b.nodes:
            nodes[name] = _midpoint(nd_a.longitude, chart_b.nodes[name].longitude)

    # --- House cusp midpoints (optional) ---
    cusps: list[float] = []
    asc_mid: float | None = None
    mc_mid:  float | None = None

    if houses_a is not None and houses_b is not None:
        cusps = [
            _midpoint(houses_a.cusps[i], houses_b.cusps[i])
            for i in range(12)
        ]
        asc_mid = _midpoint(houses_a.asc, houses_b.asc)
        mc_mid  = _midpoint(houses_a.mc,  houses_b.mc)

    jd_mean = (chart_a.jd_ut + chart_b.jd_ut) / 2.0

    return CompositeChart(
        planets=planets,
        nodes=nodes,
        cusps=cusps,
        asc=asc_mid,
        mc=mc_mid,
        jd_mean=jd_mean,
    )


# ---------------------------------------------------------------------------
# Davison chart
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class DavisonInfo:
    """
    RITE: The Midpoint Witness — records the exact time and place of union.

    THEOREM: Holds the computed midpoint Julian Day, UTC datetime, and
    geographic coordinates used to cast a Davison relationship chart.

    RITE OF PURPOSE:
        Serves the Synastry Engine as a metadata vessel for the Davison chart
        construction. It preserves the midpoint time and location so callers
        can inspect or display the Davison chart's reference coordinates without
        re-deriving them from the original birth data.

    LAW OF OPERATION:
        Responsibilities:
            - Store the midpoint Julian Day (UT).
            - Store the midpoint UTC datetime.
            - Store the midpoint geographic latitude and longitude.
        Non-responsibilities:
            - Does not compute midpoints (delegated to ``davison_chart``).
            - Does not validate geographic coordinates.
        Dependencies:
            - Populated exclusively by ``davison_chart()``.
        Succession stance: terminal — not designed for subclassing.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.synastry.DavisonInfo",
        "risk": "low",
        "api": {
            "public_methods": [],
            "public_attributes": ["jd_midpoint", "datetime_utc", "latitude_midpoint", "longitude_midpoint"]
        },
        "state": {
            "mutable": false,
            "fields": ["jd_midpoint", "datetime_utc", "latitude_midpoint", "longitude_midpoint"]
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
            "policy": "caller ensures valid midpoint data before construction"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "kiro"
    }
    [/MACHINE_CONTRACT]
    """
    jd_midpoint:        float
    datetime_utc:       datetime
    latitude_midpoint:  float
    longitude_midpoint: float


@dataclass(slots=True)
class DavisonChart:
    """
    RITE: The Vessel of the Real Moment — a true chart born at the midpoint.

    THEOREM: Holds a real natal chart cast at the midpoint time and location
    between two people's birth data, together with its house cusps and
    midpoint metadata.

    RITE OF PURPOSE:
        Serves the Synastry Engine as the primary vessel for Davison relationship
        charts. Unlike the composite chart, the Davison chart corresponds to a
        real astronomical moment and can be interpreted like any natal chart.
        Without this vessel, the Davison chart's chart, houses, and metadata
        would have no unified home in the pillar.

    LAW OF OPERATION:
        Responsibilities:
            - Hold the natal ``Chart`` cast at the midpoint time.
            - Hold the ``HouseCusps`` computed at the midpoint time and location.
            - Hold the ``DavisonInfo`` metadata (midpoint JD, datetime, lat/lon).
        Non-responsibilities:
            - Does not compute the midpoint (delegated to ``davison_chart``).
            - Does not validate that the chart is astronomically consistent.
        Dependencies:
            - Populated exclusively by ``davison_chart()``.
            - ``chart`` is a ``ChartContext`` instance from ``moira.chart``.
        Succession stance: terminal — not designed for subclassing.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.synastry.DavisonChart",
        "risk": "medium",
        "api": {
            "public_methods": [],
            "public_attributes": ["chart", "houses", "info"]
        },
        "state": {
            "mutable": false,
            "fields": ["chart", "houses", "info"]
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
            "policy": "caller ensures valid chart and info before construction"
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
    chart  : natal Chart at the midpoint time
    houses : HouseCusps at midpoint time + location (None if no location given)
    info   : midpoint time and location details
    """
    chart:  "Chart"
    houses: HouseCusps | None
    info:   DavisonInfo


def _lon_midpoint(lon_a: float, lon_b: float) -> float:
    """Shorter-arc geographic longitude midpoint, handling antimeridian."""
    diff = abs(lon_a - lon_b)
    if diff > 180.0:
        # Shorter arc crosses the antimeridian — offset one side by 360° before averaging
        if lon_a < lon_b:
            lon_a += 360.0
        else:
            lon_b += 360.0
        mid = (lon_a + lon_b) / 2.0
        # Normalise to (-180, 180]
        if mid > 180.0:
            mid -= 360.0
        return mid
    return (lon_a + lon_b) / 2.0


def davison_chart(
    dt_a: datetime,
    lat_a: float,
    lon_a: float,
    dt_b: datetime,
    lat_b: float,
    lon_b: float,
    house_system: str = HouseSystem.PLACIDUS,
    reader: SpkReader | None = None,
) -> DavisonChart:
    """
    Calculate a Davison Relationship Chart.

    The chart is cast for the exact midpoint in both time and space.

    Parameters
    ----------
    dt_a / dt_b         : birth datetimes (timezone-aware; naïve = UTC)
    lat_a / lat_b       : geographic latitudes (°, north positive)
    lon_a / lon_b       : geographic longitudes (°, east positive)
    house_system        : house system for the Davison chart
    reader              : SpkReader instance (uses module singleton if None)

    Returns
    -------
    DavisonChart with chart, houses, and midpoint info.
    """
    if reader is None:
        reader = get_reader()

    # Ensure UTC
    if dt_a.tzinfo is None:
        dt_a = dt_a.replace(tzinfo=timezone.utc)
    if dt_b.tzinfo is None:
        dt_b = dt_b.replace(tzinfo=timezone.utc)

    jd_a = jd_from_datetime(dt_a)
    jd_b = jd_from_datetime(dt_b)

    # Time midpoint
    jd_mid = (jd_a + jd_b) / 2.0
    dt_mid = datetime_from_jd(jd_mid)

    # Location midpoint
    lat_mid = (lat_a + lat_b) / 2.0
    lon_mid = _lon_midpoint(lon_a, lon_b)

    # Build chart at the midpoint using the same public chart-state logic
    # as the main engine: geocentric UT chart positions with Moira's standard
    # obliquity and Delta T fields.
    planets = all_planets_at(jd_mid, reader=reader)

    nodes = {
        Body.TRUE_NODE: true_node(jd_mid, reader=reader),
        Body.MEAN_NODE: mean_node(jd_mid),
        Body.LILITH:    mean_lilith(jd_mid),
    }

    year = dt_mid.year if dt_mid.year > -9999 else -9999
    dt_s = delta_t(float(year))
    obl = true_obliquity(jd_mid)

    # Import Chart here to avoid circular dependency at module level
    from . import Chart

    chart = Chart(
        jd_ut=jd_mid,
        planets=planets,
        nodes=nodes,
        obliquity=obl,
        delta_t=dt_s,
    )

    houses = calculate_houses(jd_mid, lat_mid, lon_mid, house_system)

    info = DavisonInfo(
        jd_midpoint=jd_mid,
        datetime_utc=dt_mid,
        latitude_midpoint=lat_mid,
        longitude_midpoint=lon_mid,
    )

    return DavisonChart(chart=chart, houses=houses, info=info)
