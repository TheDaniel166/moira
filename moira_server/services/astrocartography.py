"""Service helpers for Phase-10 Astrocartography routes (P10-01)."""

from __future__ import annotations

from dataclasses import dataclass

from moira import Moira
from moira.astrocartography import (
    ACGLine,
    SubPlanetaryPoint,
    acg_lines,
    subplanetary_points,
)
from moira.coordinates import ecliptic_to_equatorial
from moira.julian import apparent_sidereal_time, ut_to_tt
from moira.obliquity import nutation, true_obliquity
from moira.planets import planet_at, sky_position_at

from ..models.astrocartography import (
    ASTROCARTOGRAPHY_MAX_BODIES,
    AstrocartographyChartLinesRequest,
    AstrocartographyChartSubplanetaryRequest,
    AstrocartographyDirectLinesRequest,
    AstrocartographyDirectSubplanetaryRequest,
    CoordinateSource,
    ObserverSource,
)
from ..models.chart import ChartRequest
from ._shared import build_chart_context, require_supported_chart_bodies


DIRECT_LINES_STAGE_SEQUENCE = (
    "direct_ra_dec_validation",
    "sidereal_time_validation",
    "sampling_policy_validation",
    "acg_line_computation",
    "response_materialization",
)
CHART_LINES_STAGE_SEQUENCE = (
    "datetime_validation",
    "chart_context_derivation",
    "observer_policy_resolution",
    "apparent_sidereal_time_derivation",
    "body_ra_dec_derivation",
    "sampling_policy_validation",
    "acg_line_computation",
    "response_materialization",
)
DIRECT_SUBPLANETARY_STAGE_SEQUENCE = (
    "direct_ra_dec_validation",
    "sidereal_time_validation",
    "subplanetary_point_computation",
    "response_materialization",
)
CHART_SUBPLANETARY_STAGE_SEQUENCE = (
    "datetime_validation",
    "chart_context_derivation",
    "apparent_sidereal_time_derivation",
    "geocentric_ecliptic_position_derivation",
    "ecliptic_to_equatorial_conversion",
    "subplanetary_point_computation",
    "response_materialization",
)


@dataclass(frozen=True, slots=True)
class AstrocartographyObserverContext:
    latitude: float | None
    longitude: float | None
    elevation_m: float | None
    source: ObserverSource


@dataclass(frozen=True, slots=True)
class AstrocartographyProvenance:
    requested_datetime: str | None
    normalized_datetime_utc: str | None
    jd_ut: float | None
    jd_tt: float | None
    gmst_deg: float
    obliquity_deg: float | None
    nutation_longitude_deg: float | None
    requested_bodies: tuple[str, ...] | None
    returned_bodies: tuple[str, ...]
    observer: AstrocartographyObserverContext
    coordinate_source: CoordinateSource
    lat_step: float | None
    refraction: bool | None
    stage_sequence: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AstrocartographyLinesResult:
    lines: list[ACGLine]
    provenance: AstrocartographyProvenance


@dataclass(frozen=True, slots=True)
class AstrocartographySubplanetaryResult:
    points: list[SubPlanetaryPoint]
    provenance: AstrocartographyProvenance


def compute_astrocartography_direct_lines(
    request: AstrocartographyDirectLinesRequest,
) -> AstrocartographyLinesResult:
    planet_ra_dec = _direct_ra_dec_map(request.positions)
    lines = acg_lines(
        planet_ra_dec,
        request.gmst_deg,
        lat_step=request.lat_step,
        jd_ut=request.jd_ut,
        refraction=request.refraction,
    )
    return AstrocartographyLinesResult(
        lines=lines,
        provenance=AstrocartographyProvenance(
            requested_datetime=None,
            normalized_datetime_utc=None,
            jd_ut=request.jd_ut,
            jd_tt=None,
            gmst_deg=request.gmst_deg,
            obliquity_deg=None,
            nutation_longitude_deg=None,
            requested_bodies=tuple(request.positions),
            returned_bodies=tuple(request.positions),
            observer=AstrocartographyObserverContext(
                latitude=None,
                longitude=None,
                elevation_m=None,
                source="direct_none",
            ),
            coordinate_source="direct_ra_dec",
            lat_step=request.lat_step,
            refraction=request.refraction,
            stage_sequence=DIRECT_LINES_STAGE_SEQUENCE,
        ),
    )


def compute_astrocartography_direct_subplanetary(
    request: AstrocartographyDirectSubplanetaryRequest,
) -> AstrocartographySubplanetaryResult:
    planet_ra_dec = _direct_ra_dec_map(request.positions)
    points = subplanetary_points(planet_ra_dec, request.gmst_deg)
    return AstrocartographySubplanetaryResult(
        points=points,
        provenance=AstrocartographyProvenance(
            requested_datetime=None,
            normalized_datetime_utc=None,
            jd_ut=None,
            jd_tt=None,
            gmst_deg=request.gmst_deg,
            obliquity_deg=None,
            nutation_longitude_deg=None,
            requested_bodies=tuple(request.positions),
            returned_bodies=tuple(request.positions),
            observer=AstrocartographyObserverContext(
                latitude=None,
                longitude=None,
                elevation_m=None,
                source="direct_none",
            ),
            coordinate_source="direct_ra_dec",
            lat_step=None,
            refraction=None,
            stage_sequence=DIRECT_SUBPLANETARY_STAGE_SEQUENCE,
        ),
    )


def compute_astrocartography_chart_lines(
    engine: Moira,
    request: AstrocartographyChartLinesRequest,
) -> AstrocartographyLinesResult:
    chart = _build_chart(engine, request)
    bodies = _selected_bodies(request.bodies, chart.planets)
    observer = _resolve_line_observer(request, chart)
    dpsi, obliquity, gmst_deg, jd_tt = _sidereal_context(chart.jd_ut)
    reader = getattr(engine, "_reader", None)
    planet_ra_dec = {
        body: _sky_ra_dec(
            body=body,
            jd_ut=chart.jd_ut,
            observer=observer,
            reader=reader,
            refraction=request.refraction,
        )
        for body in bodies
    }
    lines = acg_lines(
        planet_ra_dec,
        gmst_deg,
        lat_step=request.lat_step,
        jd_ut=chart.jd_ut,
        refraction=request.refraction,
    )
    return AstrocartographyLinesResult(
        lines=lines,
        provenance=_chart_provenance(
            request=request,
            chart=chart,
            bodies=bodies,
            observer=observer,
            coordinate_source="chart_apparent_topocentric_ra_dec",
            lat_step=request.lat_step,
            refraction=request.refraction,
            gmst_deg=gmst_deg,
            jd_tt=jd_tt,
            dpsi=dpsi,
            obliquity=obliquity,
            stage_sequence=CHART_LINES_STAGE_SEQUENCE,
        ),
    )


def compute_astrocartography_chart_subplanetary(
    engine: Moira,
    request: AstrocartographyChartSubplanetaryRequest,
) -> AstrocartographySubplanetaryResult:
    chart = _build_chart(engine, request)
    bodies = _selected_bodies(request.bodies, chart.planets)
    dpsi, obliquity, gmst_deg, jd_tt = _sidereal_context(chart.jd_ut)
    reader = getattr(engine, "_reader", None)
    planet_ra_dec = {}
    for body in bodies:
        position = planet_at(body, chart.jd_ut, reader=reader)
        planet_ra_dec[body] = ecliptic_to_equatorial(
            position.longitude,
            position.latitude,
            obliquity,
        )
    points = subplanetary_points(planet_ra_dec, gmst_deg)
    return AstrocartographySubplanetaryResult(
        points=points,
        provenance=_chart_provenance(
            request=request,
            chart=chart,
            bodies=bodies,
            observer=AstrocartographyObserverContext(
                latitude=None,
                longitude=None,
                elevation_m=None,
                source="direct_none",
            ),
            coordinate_source="chart_geocentric_ecliptic_to_equatorial",
            lat_step=None,
            refraction=None,
            gmst_deg=gmst_deg,
            jd_tt=jd_tt,
            dpsi=dpsi,
            obliquity=obliquity,
            stage_sequence=CHART_SUBPLANETARY_STAGE_SEQUENCE,
        ),
    )


def _build_chart(engine: Moira, request):
    require_supported_chart_bodies(request.bodies)
    return build_chart_context(
        engine,
        ChartRequest(
            dt=request.dt,
            bodies=request.bodies,
            include_nodes=False,
            observer_lat=request.observer_lat,
            observer_lon=request.observer_lon,
            observer_elev_m=request.observer_elev_m,
        ),
    )


def _selected_bodies(
    requested: list[str] | None,
    chart_planets,
) -> tuple[str, ...]:
    bodies = tuple(requested or chart_planets.keys())
    if len(bodies) > ASTROCARTOGRAPHY_MAX_BODIES:
        raise ValueError(f"bodies may contain at most {ASTROCARTOGRAPHY_MAX_BODIES} entries")
    return bodies


def _resolve_line_observer(
    request: AstrocartographyChartLinesRequest,
    chart,
) -> AstrocartographyObserverContext:
    if request.acg_observer_lat is not None and request.acg_observer_lon is not None:
        return AstrocartographyObserverContext(
            latitude=request.acg_observer_lat,
            longitude=request.acg_observer_lon,
            elevation_m=request.acg_observer_elev_m or 0.0,
            source="acg_override",
        )
    if request.observer_lat is not None and request.observer_lon is not None:
        return AstrocartographyObserverContext(
            latitude=request.observer_lat,
            longitude=request.observer_lon,
            elevation_m=request.observer_elev_m,
            source="chart_request",
        )
    chart_latitude = getattr(chart, "latitude", None)
    chart_longitude = getattr(chart, "longitude", None)
    if chart_latitude is not None and chart_longitude is not None:
        return AstrocartographyObserverContext(
            latitude=chart_latitude,
            longitude=chart_longitude,
            elevation_m=getattr(chart, "elevation_m", 0.0),
            source="chart_request",
        )
    return AstrocartographyObserverContext(
        latitude=0.0,
        longitude=0.0,
        elevation_m=0.0,
        source="default_zero",
    )


def _sidereal_context(jd_ut: float) -> tuple[float, float, float, float]:
    jd_tt = ut_to_tt(jd_ut)
    dpsi, _ = nutation(jd_tt)
    obliquity = true_obliquity(jd_tt)
    gmst_deg = apparent_sidereal_time(jd_ut, dpsi, obliquity)
    return dpsi, obliquity, gmst_deg, jd_tt


def _sky_ra_dec(
    *,
    body: str,
    jd_ut: float,
    observer: AstrocartographyObserverContext,
    reader,
    refraction: bool,
) -> tuple[float, float]:
    sky = sky_position_at(
        body,
        jd_ut,
        observer_lat=observer.latitude or 0.0,
        observer_lon=observer.longitude or 0.0,
        observer_elev_m=observer.elevation_m or 0.0,
        reader=reader,
        refraction=refraction,
    )
    return sky.right_ascension, sky.declination


def _chart_provenance(
    *,
    request,
    chart,
    bodies: tuple[str, ...],
    observer: AstrocartographyObserverContext,
    coordinate_source: CoordinateSource,
    lat_step: float | None,
    refraction: bool | None,
    gmst_deg: float,
    jd_tt: float,
    dpsi: float,
    obliquity: float,
    stage_sequence: tuple[str, ...],
) -> AstrocartographyProvenance:
    return AstrocartographyProvenance(
        requested_datetime=request.dt.isoformat(),
        normalized_datetime_utc=chart.datetime_utc.isoformat(),
        jd_ut=chart.jd_ut,
        jd_tt=jd_tt,
        gmst_deg=gmst_deg,
        obliquity_deg=obliquity,
        nutation_longitude_deg=dpsi,
        requested_bodies=tuple(request.bodies) if request.bodies is not None else None,
        returned_bodies=bodies,
        observer=observer,
        coordinate_source=coordinate_source,
        lat_step=lat_step,
        refraction=refraction,
        stage_sequence=stage_sequence,
    )


def _direct_ra_dec_map(positions) -> dict[str, tuple[float, float]]:
    return {
        body: (coordinate.right_ascension, coordinate.declination)
        for body, coordinate in positions.items()
    }


__all__ = [
    "AstrocartographyLinesResult",
    "AstrocartographyObserverContext",
    "AstrocartographyProvenance",
    "AstrocartographySubplanetaryResult",
    "compute_astrocartography_chart_lines",
    "compute_astrocartography_chart_subplanetary",
    "compute_astrocartography_direct_lines",
    "compute_astrocartography_direct_subplanetary",
]
