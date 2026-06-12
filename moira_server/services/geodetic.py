"""Service helpers for Phase-10 Geodetic routes (P10-03)."""

from __future__ import annotations

from dataclasses import dataclass

from moira import Moira
from moira.geodetic import GeodeticChart, geodetic_chart, geodetic_equivalents
from moira.julian import ut_to_tt
from moira.obliquity import true_obliquity
from moira.sidereal import ayanamsa

from ..models.chart import ChartRequest
from ..models.geodetic import (
    CoordinateSource,
    GEODETIC_MAX_BODIES,
    GeodeticChartBackedChartRequest,
    GeodeticChartBackedEquivalentsRequest,
    GeodeticDirectChartRequest,
    GeodeticDirectEquivalentsRequest,
    ZodiacName,
)
from ._shared import build_chart_context, require_supported_chart_bodies


DIRECT_CHART_STAGE_SEQUENCE = (
    "direct_geographic_validation",
    "zodiac_policy_validation",
    "obliquity_validation",
    "geodetic_chart_computation",
    "response_materialization",
)
CHART_CHART_STAGE_SEQUENCE = (
    "datetime_validation",
    "chart_context_derivation",
    "zodiac_policy_validation",
    "obliquity_derivation",
    "ayanamsa_resolution",
    "geodetic_chart_computation",
    "response_materialization",
)
DIRECT_EQUIVALENTS_STAGE_SEQUENCE = (
    "direct_longitude_validation",
    "zodiac_policy_validation",
    "geodetic_equivalent_computation",
    "response_materialization",
)
CHART_EQUIVALENTS_STAGE_SEQUENCE = (
    "datetime_validation",
    "chart_context_derivation",
    "chart_body_validation",
    "zodiac_policy_validation",
    "ayanamsa_resolution",
    "longitude_selection",
    "geodetic_equivalent_computation",
    "response_materialization",
)


@dataclass(frozen=True, slots=True)
class GeodeticProvenance:
    requested_datetime: str | None
    normalized_datetime_utc: str | None
    jd_ut: float | None
    jd_tt: float | None
    obliquity_deg: float | None
    zodiac: ZodiacName
    ayanamsa_system: str | None
    ayanamsa_deg: float
    requested_bodies: tuple[str, ...] | None
    returned_bodies: tuple[str, ...]
    coordinate_source: CoordinateSource
    stage_sequence: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GeodeticChartResult:
    chart: GeodeticChart
    provenance: GeodeticProvenance


@dataclass(frozen=True, slots=True)
class GeodeticEquivalentsResult:
    equivalents: dict[str, float]
    provenance: GeodeticProvenance


def compute_geodetic_direct_chart(
    request: GeodeticDirectChartRequest,
) -> GeodeticChartResult:
    ayanamsa_deg = _direct_ayanamsa(request.zodiac, request.ayanamsa_deg)
    chart = geodetic_chart(
        request.geo_longitude,
        request.geo_latitude,
        request.obliquity,
        ayanamsa_deg=ayanamsa_deg,
        zodiac=request.zodiac,
    )
    return GeodeticChartResult(
        chart=chart,
        provenance=GeodeticProvenance(
            requested_datetime=None,
            normalized_datetime_utc=None,
            jd_ut=None,
            jd_tt=None,
            obliquity_deg=request.obliquity,
            zodiac=request.zodiac,
            ayanamsa_system=None,
            ayanamsa_deg=ayanamsa_deg,
            requested_bodies=None,
            returned_bodies=(),
            coordinate_source="direct_geographic_obliquity",
            stage_sequence=DIRECT_CHART_STAGE_SEQUENCE,
        ),
    )


def compute_geodetic_chart_backed_chart(
    engine: Moira,
    request: GeodeticChartBackedChartRequest,
) -> GeodeticChartResult:
    chart_context = _build_chart(engine, request, bodies=["Sun"])
    jd_tt = _jd_tt(chart_context)
    obliquity = true_obliquity(jd_tt)
    ayanamsa_deg = _chart_ayanamsa(
        zodiac=request.zodiac,
        ayanamsa_system=request.ayanamsa_system,
        jd_ut=chart_context.jd_ut,
    )
    chart = geodetic_chart(
        request.geo_longitude,
        request.geo_latitude,
        obliquity,
        ayanamsa_deg=ayanamsa_deg,
        zodiac=request.zodiac,
    )
    return GeodeticChartResult(
        chart=chart,
        provenance=_chart_provenance(
            request=request,
            chart_context=chart_context,
            obliquity=obliquity,
            ayanamsa_deg=ayanamsa_deg,
            requested_bodies=None,
            returned_bodies=(),
            coordinate_source="chart_epoch_obliquity",
            stage_sequence=CHART_CHART_STAGE_SEQUENCE,
        ),
    )


def compute_geodetic_direct_equivalents(
    request: GeodeticDirectEquivalentsRequest,
) -> GeodeticEquivalentsResult:
    ayanamsa_deg = _direct_ayanamsa(request.zodiac, request.ayanamsa_deg)
    equivalents = geodetic_equivalents(
        dict(request.longitudes),
        ayanamsa_deg=ayanamsa_deg,
    )
    returned_bodies = tuple(equivalents)
    return GeodeticEquivalentsResult(
        equivalents=equivalents,
        provenance=GeodeticProvenance(
            requested_datetime=None,
            normalized_datetime_utc=None,
            jd_ut=None,
            jd_tt=None,
            obliquity_deg=None,
            zodiac=request.zodiac,
            ayanamsa_system=None,
            ayanamsa_deg=ayanamsa_deg,
            requested_bodies=tuple(request.longitudes),
            returned_bodies=returned_bodies,
            coordinate_source="direct_ecliptic_longitudes",
            stage_sequence=DIRECT_EQUIVALENTS_STAGE_SEQUENCE,
        ),
    )


def compute_geodetic_chart_backed_equivalents(
    engine: Moira,
    request: GeodeticChartBackedEquivalentsRequest,
) -> GeodeticEquivalentsResult:
    chart_context = _build_chart(engine, request, bodies=request.bodies)
    bodies = _selected_bodies(request.bodies, chart_context.planets)
    ayanamsa_deg = _chart_ayanamsa(
        zodiac=request.zodiac,
        ayanamsa_system=request.ayanamsa_system,
        jd_ut=chart_context.jd_ut,
    )
    longitudes = {
        body: chart_context.planets[body].longitude
        for body in bodies
    }
    coordinate_source: CoordinateSource = "chart_tropical_longitudes"
    if request.zodiac == "sidereal":
        longitudes = {
            body: (longitude - ayanamsa_deg) % 360.0
            for body, longitude in longitudes.items()
        }
        coordinate_source = "chart_sidereal_longitudes"
    equivalents = geodetic_equivalents(longitudes, ayanamsa_deg=ayanamsa_deg)
    returned_bodies = tuple(equivalents)
    return GeodeticEquivalentsResult(
        equivalents=equivalents,
        provenance=_chart_provenance(
            request=request,
            chart_context=chart_context,
            obliquity=None,
            ayanamsa_deg=ayanamsa_deg,
            requested_bodies=tuple(request.bodies) if request.bodies is not None else None,
            returned_bodies=returned_bodies,
            coordinate_source=coordinate_source,
            stage_sequence=CHART_EQUIVALENTS_STAGE_SEQUENCE,
        ),
    )


def _build_chart(engine: Moira, request, *, bodies: list[str] | None):
    require_supported_chart_bodies(bodies)
    return build_chart_context(
        engine,
        ChartRequest(
            dt=request.dt,
            bodies=bodies,
            include_nodes=False,
            observer_lat=request.geo_latitude,
            observer_lon=request.geo_longitude,
            observer_elev_m=0.0,
        ),
    )


def _selected_bodies(
    requested: list[str] | None,
    chart_planets,
) -> tuple[str, ...]:
    bodies = tuple(requested or chart_planets.keys())
    if len(bodies) > GEODETIC_MAX_BODIES:
        raise ValueError(f"bodies may contain at most {GEODETIC_MAX_BODIES} entries")
    return bodies


def _direct_ayanamsa(zodiac: ZodiacName, ayanamsa_deg: float | None) -> float:
    if zodiac == "sidereal":
        if ayanamsa_deg is None:
            raise ValueError("sidereal zodiac requires ayanamsa_deg")
        return ayanamsa_deg
    return ayanamsa_deg if ayanamsa_deg is not None else 0.0


def _chart_ayanamsa(
    *,
    zodiac: ZodiacName,
    ayanamsa_system: str | None,
    jd_ut: float,
) -> float:
    if zodiac == "sidereal":
        if ayanamsa_system is None:
            raise ValueError("sidereal zodiac requires ayanamsa_system")
        return ayanamsa(jd_ut, ayanamsa_system)
    return 0.0


def _chart_provenance(
    *,
    request,
    chart_context,
    obliquity: float | None,
    ayanamsa_deg: float,
    requested_bodies: tuple[str, ...] | None,
    returned_bodies: tuple[str, ...],
    coordinate_source: CoordinateSource,
    stage_sequence: tuple[str, ...],
) -> GeodeticProvenance:
    return GeodeticProvenance(
        requested_datetime=request.dt.isoformat(),
        normalized_datetime_utc=chart_context.datetime_utc.isoformat(),
        jd_ut=chart_context.jd_ut,
        jd_tt=_jd_tt(chart_context),
        obliquity_deg=obliquity,
        zodiac=request.zodiac,
        ayanamsa_system=request.ayanamsa_system if request.zodiac == "sidereal" else None,
        ayanamsa_deg=ayanamsa_deg,
        requested_bodies=requested_bodies,
        returned_bodies=returned_bodies,
        coordinate_source=coordinate_source,
        stage_sequence=stage_sequence,
    )


def _jd_tt(chart_context) -> float:
    return getattr(chart_context, "jd_tt", ut_to_tt(chart_context.jd_ut))


__all__ = [
    "GeodeticChartResult",
    "GeodeticEquivalentsResult",
    "GeodeticProvenance",
    "compute_geodetic_chart_backed_chart",
    "compute_geodetic_chart_backed_equivalents",
    "compute_geodetic_direct_chart",
    "compute_geodetic_direct_equivalents",
]
