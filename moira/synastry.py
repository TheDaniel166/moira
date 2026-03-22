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
from .coordinates import ecliptic_to_equatorial
from .midpoints import _midpoint
from .aspects import AspectData, aspects_between
from .julian import jd_from_datetime, datetime_from_jd, delta_t
from .planets import all_planets_at
from .nodes import true_node, mean_node, mean_lilith
from .obliquity import true_obliquity
from .houses import (
    HouseCusps,
    HousePlacement,
    HousePolicy,
    PolarFallbackPolicy,
    UnknownSystemPolicy,
    _KNOWN_SYSTEMS,
    _POLAR_SYSTEMS,
    _alcabitius,
    _apc,
    _asc_from_armc,
    _azimuthal,
    _campanus,
    _carter,
    _equal_house,
    _koch,
    _krusinski,
    _mc_from_armc,
    _meridian,
    _morinus,
    _placidus,
    _porphyry,
    _pullen_sd,
    _pullen_sr,
    _regiomontanus,
    _sunshine,
    _topocentric,
    _vehlow,
    _whole_sign,
    assign_house,
    calculate_houses,
    classify_house_system,
)
from .constants import HouseSystem, sign_of
from .spk_reader import get_reader, SpkReader

if TYPE_CHECKING:
    from .__init__ import Chart


# ---------------------------------------------------------------------------
# Synastry aspects (inter-aspects between two charts)
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class SynastryHouseOverlay:
    """Directional synastry house-overlay result."""

    source_label: str
    target_label: str
    placements: dict[str, HousePlacement]
    include_nodes: bool = True

    def __post_init__(self) -> None:
        if not self.source_label.strip():
            raise ValueError("source_label must be non-empty")
        if not self.target_label.strip():
            raise ValueError("target_label must be non-empty")

    def bodies_in_house(self, house: int) -> tuple[str, ...]:
        """Return the deterministically ordered bodies placed in one target house."""

        return tuple(sorted(
            name for name, placement in self.placements.items() if placement.house == house
        ))


@dataclass(slots=True)
class MutualHouseOverlay:
    """Container for the two directional house overlays in a synastry pair."""

    first_in_second: SynastryHouseOverlay
    second_in_first: SynastryHouseOverlay

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


def house_overlay(
    chart_source: "Chart",
    target_houses: HouseCusps,
    *,
    include_nodes: bool = True,
    source_label: str = "A",
    target_label: str = "B",
) -> SynastryHouseOverlay:
    """
    Place one chart's points into another chart's houses.

    This is the standard backend house-overlay technique used in synastry:
    each selected body or node from ``chart_source`` is assigned to a house in
    ``target_houses`` using the existing house membership doctrine.
    """

    longitudes = chart_source.longitudes(include_nodes=include_nodes)
    placements = {
        name: assign_house(longitude, target_houses)
        for name, longitude in longitudes.items()
    }
    return SynastryHouseOverlay(
        source_label=source_label,
        target_label=target_label,
        placements=placements,
        include_nodes=include_nodes,
    )


def mutual_house_overlays(
    chart_a: "Chart",
    houses_a: HouseCusps,
    chart_b: "Chart",
    houses_b: HouseCusps,
    *,
    include_nodes: bool = True,
    first_label: str = "A",
    second_label: str = "B",
) -> MutualHouseOverlay:
    """Compute house overlays in both synastry directions."""

    return MutualHouseOverlay(
        first_in_second=house_overlay(
            chart_a,
            houses_b,
            include_nodes=include_nodes,
            source_label=first_label,
            target_label=second_label,
        ),
        second_in_first=house_overlay(
            chart_b,
            houses_a,
            include_nodes=include_nodes,
            source_label=second_label,
            target_label=first_label,
        ),
    )


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


def composite_chart_reference_place(
    chart_a: "Chart",
    chart_b: "Chart",
    houses_a: HouseCusps,
    houses_b: HouseCusps,
    reference_latitude: float,
    house_system: str = HouseSystem.PLACIDUS,
) -> CompositeChart:
    """
    Composite chart using midpoint planets and a reference-place house method.

    This follows the mainstream "reference place method" doctrine: planets and
    nodes use midpoint longitudes, while the house frame is derived from the
    composite MC/ARMC and a supplied reference latitude.
    """

    composite = composite_chart(chart_a, chart_b)
    composite_mc = _midpoint(houses_a.mc, houses_b.mc)
    mean_obliquity = (chart_a.obliquity + chart_b.obliquity) / 2.0
    composite_armc, _ = ecliptic_to_equatorial(composite_mc, 0.0, mean_obliquity)
    composite_sun_lon = composite.planets.get(Body.SUN)
    houses = _synastry_houses_from_armc(
        armc=composite_armc,
        latitude=reference_latitude,
        obliquity=mean_obliquity,
        system=house_system,
        sun_lon=composite_sun_lon,
    )
    return CompositeChart(
        planets=composite.planets,
        nodes=composite.nodes,
        cusps=list(houses.cusps),
        asc=houses.asc,
        mc=houses.mc,
        jd_mean=composite.jd_mean,
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


def _lon_midpoint_uncorrected(lon_a: float, lon_b: float) -> float:
    """Arithmetic longitude midpoint used by uncorrected Davison doctrine."""

    mid = (lon_a + lon_b) / 2.0
    if mid <= -180.0:
        mid += 360.0
    elif mid > 180.0:
        mid -= 360.0
    return mid


def _spherical_geo_midpoint(
    lat_a: float,
    lon_a: float,
    lat_b: float,
    lon_b: float,
) -> tuple[float, float]:
    """Great-circle midpoint of two geographic coordinates on the unit sphere."""

    lat_a_r = lat_a * DEG2RAD
    lon_a_r = lon_a * DEG2RAD
    lat_b_r = lat_b * DEG2RAD
    lon_b_r = lon_b * DEG2RAD

    x_a = math.cos(lat_a_r) * math.cos(lon_a_r)
    y_a = math.cos(lat_a_r) * math.sin(lon_a_r)
    z_a = math.sin(lat_a_r)
    x_b = math.cos(lat_b_r) * math.cos(lon_b_r)
    y_b = math.cos(lat_b_r) * math.sin(lon_b_r)
    z_b = math.sin(lat_b_r)

    x = x_a + x_b
    y = y_a + y_b
    z = z_a + z_b
    hyp = math.hypot(x, y)
    lat_mid = math.atan2(z, hyp) * RAD2DEG
    lon_mid = math.atan2(y, x) * RAD2DEG
    if lon_mid <= -180.0:
        lon_mid += 360.0
    elif lon_mid > 180.0:
        lon_mid -= 360.0
    return lat_mid, lon_mid


def _build_relationship_chart(
    jd_ut: float,
    latitude: float,
    longitude: float,
    house_system: str,
    reader: SpkReader,
) -> DavisonChart:
    """Build a real chart and house frame for one relationship-chart moment/place."""

    dt_mid = datetime_from_jd(jd_ut)
    planets = all_planets_at(jd_ut, reader=reader)
    nodes = {
        Body.TRUE_NODE: true_node(jd_ut, reader=reader),
        Body.MEAN_NODE: mean_node(jd_ut),
        Body.LILITH: mean_lilith(jd_ut),
    }
    year = dt_mid.year if dt_mid.year > -9999 else -9999
    dt_s = delta_t(float(year))
    obl = true_obliquity(jd_ut)

    from . import Chart

    chart = Chart(
        jd_ut=jd_ut,
        planets=planets,
        nodes=nodes,
        obliquity=obl,
        delta_t=dt_s,
    )
    houses = calculate_houses(jd_ut, latitude, longitude, house_system)
    info = DavisonInfo(
        jd_midpoint=jd_ut,
        datetime_utc=dt_mid,
        latitude_midpoint=latitude,
        longitude_midpoint=longitude,
    )
    return DavisonChart(chart=chart, houses=houses, info=info)


def _synastry_houses_from_armc(
    *,
    armc: float,
    latitude: float,
    obliquity: float,
    system: str,
    sun_lon: float | None = None,
) -> HouseCusps:
    """HouseCusps constructor for reference-place relationship-chart techniques."""

    active_policy = HousePolicy.default()
    critical_lat = 90.0 - obliquity
    polar = abs(latitude) >= critical_lat and system in _POLAR_SYSTEMS
    effective_system = system
    fallback = False
    fallback_reason: str | None = None

    if polar:
        if active_policy.polar_fallback == PolarFallbackPolicy.RAISE:
            raise ValueError("reference-place synastry houses hit polar fallback under strict policy")
        effective_system = HouseSystem.PORPHYRY
        fallback = True
        fallback_reason = "reference-place synastry houses fell back to Porphyry at critical latitude"
    elif system not in _KNOWN_SYSTEMS:
        if active_policy.unknown_system == UnknownSystemPolicy.RAISE:
            raise ValueError("reference-place synastry houses received unknown system under strict policy")
        effective_system = HouseSystem.PLACIDUS
        fallback = True
        fallback_reason = f"unknown system code {system!r}; fell back to Placidus"

    mc = _mc_from_armc(armc, obliquity, latitude)
    asc = _asc_from_armc(armc, obliquity, latitude)
    vertex = _asc_from_armc((armc + 90.0) % 360.0, obliquity, -latitude)
    anti_vertex = (vertex + 180.0) % 360.0

    if effective_system == HouseSystem.WHOLE_SIGN:
        cusps = _whole_sign(asc)
    elif effective_system == HouseSystem.EQUAL:
        cusps = _equal_house(asc)
    elif effective_system == HouseSystem.PORPHYRY:
        cusps = _porphyry(asc, mc)
    elif effective_system == HouseSystem.PLACIDUS:
        cusps = _placidus(armc, obliquity, latitude)
    elif effective_system == HouseSystem.KOCH:
        cusps = _koch(armc, obliquity, latitude)
    elif effective_system == HouseSystem.CAMPANUS:
        cusps = _campanus(armc, obliquity, latitude)
    elif effective_system == HouseSystem.REGIOMONTANUS:
        cusps = _regiomontanus(armc, obliquity, latitude)
    elif effective_system == HouseSystem.ALCABITIUS:
        cusps = _alcabitius(armc, obliquity, latitude)
    elif effective_system == HouseSystem.MORINUS:
        cusps = _morinus(armc, obliquity)
    elif effective_system == HouseSystem.TOPOCENTRIC:
        cusps = _topocentric(armc, obliquity, latitude)
    elif effective_system == HouseSystem.MERIDIAN:
        cusps = _meridian(armc, obliquity)
    elif effective_system == HouseSystem.VEHLOW:
        cusps = _vehlow(asc)
    elif effective_system == HouseSystem.SUNSHINE:
        if sun_lon is None:
            raise ValueError("Sunshine reference-place synastry houses require sun_lon")
        cusps = _sunshine(sun_lon, latitude, obliquity)
    elif effective_system == HouseSystem.AZIMUTHAL:
        cusps = _azimuthal(armc, obliquity, latitude)
    elif effective_system == HouseSystem.CARTER:
        cusps = _carter(armc, obliquity, latitude)
    elif effective_system == HouseSystem.PULLEN_SD:
        cusps = _pullen_sd(armc, obliquity, latitude)
    elif effective_system == HouseSystem.PULLEN_SR:
        cusps = _pullen_sr(armc, obliquity, latitude)
    elif effective_system == HouseSystem.KRUSINSKI:
        cusps = _krusinski(armc, obliquity, latitude)
    elif effective_system == HouseSystem.APC:
        cusps = _apc(armc, obliquity, latitude)
    else:
        cusps = _placidus(armc, obliquity, latitude)

    return HouseCusps(
        system=system,
        cusps=[c % 360.0 for c in cusps],
        asc=asc % 360.0,
        mc=mc % 360.0,
        armc=armc % 360.0,
        vertex=vertex % 360.0,
        anti_vertex=anti_vertex % 360.0,
        effective_system=effective_system,
        fallback=fallback,
        fallback_reason=fallback_reason,
        classification=classify_house_system(effective_system),
        policy=active_policy,
    )


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


def davison_chart_uncorrected(
    dt_a: datetime,
    lat_a: float,
    lon_a: float,
    dt_b: datetime,
    lat_b: float,
    lon_b: float,
    house_system: str = HouseSystem.PLACIDUS,
    reader: SpkReader | None = None,
) -> DavisonChart:
    """Davison chart using arithmetic midpoint time and arithmetic location."""

    if reader is None:
        reader = get_reader()
    if dt_a.tzinfo is None:
        dt_a = dt_a.replace(tzinfo=timezone.utc)
    if dt_b.tzinfo is None:
        dt_b = dt_b.replace(tzinfo=timezone.utc)

    jd_mid = (jd_from_datetime(dt_a) + jd_from_datetime(dt_b)) / 2.0
    lat_mid = (lat_a + lat_b) / 2.0
    lon_mid = _lon_midpoint_uncorrected(lon_a, lon_b)
    return _build_relationship_chart(jd_mid, lat_mid, lon_mid, house_system, reader)


def davison_chart_reference_place(
    dt_a: datetime,
    dt_b: datetime,
    reference_latitude: float,
    reference_longitude: float,
    house_system: str = HouseSystem.PLACIDUS,
    reader: SpkReader | None = None,
) -> DavisonChart:
    """Davison chart using midpoint time and an explicit reference place."""

    if reader is None:
        reader = get_reader()
    if dt_a.tzinfo is None:
        dt_a = dt_a.replace(tzinfo=timezone.utc)
    if dt_b.tzinfo is None:
        dt_b = dt_b.replace(tzinfo=timezone.utc)

    jd_mid = (jd_from_datetime(dt_a) + jd_from_datetime(dt_b)) / 2.0
    return _build_relationship_chart(jd_mid, reference_latitude, reference_longitude, house_system, reader)


def davison_chart_spherical_midpoint(
    dt_a: datetime,
    lat_a: float,
    lon_a: float,
    dt_b: datetime,
    lat_b: float,
    lon_b: float,
    house_system: str = HouseSystem.PLACIDUS,
    reader: SpkReader | None = None,
) -> DavisonChart:
    """Davison chart using midpoint time and great-circle midpoint location."""

    if reader is None:
        reader = get_reader()
    if dt_a.tzinfo is None:
        dt_a = dt_a.replace(tzinfo=timezone.utc)
    if dt_b.tzinfo is None:
        dt_b = dt_b.replace(tzinfo=timezone.utc)

    jd_mid = (jd_from_datetime(dt_a) + jd_from_datetime(dt_b)) / 2.0
    lat_mid, lon_mid = _spherical_geo_midpoint(lat_a, lon_a, lat_b, lon_b)
    return _build_relationship_chart(jd_mid, lat_mid, lon_mid, house_system, reader)


def davison_chart_corrected(
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
    Davison chart with midpoint location and corrected time to preserve midpoint MC.

    The current embodied correction doctrine searches around the midpoint time
    until the cast chart's MC matches the midpoint of the two natal MCs.
    """

    if reader is None:
        reader = get_reader()
    if dt_a.tzinfo is None:
        dt_a = dt_a.replace(tzinfo=timezone.utc)
    if dt_b.tzinfo is None:
        dt_b = dt_b.replace(tzinfo=timezone.utc)

    jd_a = jd_from_datetime(dt_a)
    jd_b = jd_from_datetime(dt_b)
    jd_mid = (jd_a + jd_b) / 2.0
    lat_mid = (lat_a + lat_b) / 2.0
    lon_mid = _lon_midpoint_uncorrected(lon_a, lon_b)
    houses_a = calculate_houses(jd_a, lat_a, lon_a, house_system)
    houses_b = calculate_houses(jd_b, lat_b, lon_b, house_system)
    target_mc = _midpoint(houses_a.mc, houses_b.mc)

    def _signed_diff(jd_value: float) -> float:
        mc = calculate_houses(jd_value, lat_mid, lon_mid, house_system).mc
        return ((mc - target_mc + 540.0) % 360.0) - 180.0

    bracket_left = jd_mid - 0.5
    left_diff = _signed_diff(bracket_left)
    right_jd = bracket_left
    right_diff = left_diff
    found_bracket = False
    for step in range(1, 145):
        probe = jd_mid - 0.5 + (step / 144.0)
        probe_diff = _signed_diff(probe)
        if left_diff == 0.0:
            right_jd = bracket_left
            right_diff = left_diff
            found_bracket = True
            break
        if left_diff * probe_diff <= 0.0:
            right_jd = probe
            right_diff = probe_diff
            found_bracket = True
            break
        bracket_left = probe
        left_diff = probe_diff

    corrected_jd = jd_mid
    if found_bracket:
        left_jd = bracket_left
        for _ in range(80):
            mid_probe = (left_jd + right_jd) / 2.0
            mid_diff = _signed_diff(mid_probe)
            if abs(mid_diff) < 1e-10:
                corrected_jd = mid_probe
                break
            if left_diff * mid_diff <= 0.0:
                right_jd = mid_probe
                right_diff = mid_diff
            else:
                left_jd = mid_probe
                left_diff = mid_diff
            corrected_jd = mid_probe

    return _build_relationship_chart(corrected_jd, lat_mid, lon_mid, house_system, reader)
