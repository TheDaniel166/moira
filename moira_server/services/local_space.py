"""Service helpers for Phase-10 Local Space routes (P10-02)."""

from __future__ import annotations

from dataclasses import dataclass

from moira import Moira
from moira.julian import local_sidereal_time, ut_to_tt
from moira.local_space import LocalSpacePosition, local_space_positions
from moira.obliquity import nutation, true_obliquity
from moira.planets import sky_position_at

from ..models.chart import ChartRequest
from ..models.local_space import (
    LOCAL_SPACE_MAX_BODIES,
    CoordinateSource,
    LocalSpaceChartPositionsRequest,
    LocalSpaceDirectPositionsRequest,
    ObserverSource,
)
from ._shared import build_chart_context, require_supported_chart_bodies


DIRECT_STAGE_SEQUENCE = (
    "direct_ra_dec_validation",
    "observer_latitude_validation",
    "local_sidereal_time_validation",
    "local_space_computation",
    "response_materialization",
)
CHART_STAGE_SEQUENCE = (
    "datetime_validation",
    "chart_context_derivation",
    "observer_policy_validation",
    "local_sidereal_time_derivation",
    "body_ra_dec_derivation",
    "local_space_computation",
    "response_materialization",
)


@dataclass(frozen=True, slots=True)
class LocalSpaceObserverContext:
    latitude: float
    longitude: float | None
    elevation_m: float | None
    source: ObserverSource


@dataclass(frozen=True, slots=True)
class LocalSpaceProvenance:
    requested_datetime: str | None
    normalized_datetime_utc: str | None
    jd_ut: float | None
    jd_tt: float | None
    lst_deg: float
    observer: LocalSpaceObserverContext
    requested_bodies: tuple[str, ...] | None
    returned_bodies: tuple[str, ...]
    coordinate_source: CoordinateSource
    stage_sequence: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LocalSpacePositionsResult:
    positions: list[LocalSpacePosition]
    provenance: LocalSpaceProvenance


def compute_local_space_direct_positions(
    request: LocalSpaceDirectPositionsRequest,
) -> LocalSpacePositionsResult:
    planet_ra_dec = _direct_ra_dec_map(request.positions)
    positions = local_space_positions(
        planet_ra_dec,
        latitude=request.latitude,
        lst_deg=request.lst_deg,
    )
    returned_bodies = tuple(position.body for position in positions)
    return LocalSpacePositionsResult(
        positions=positions,
        provenance=LocalSpaceProvenance(
            requested_datetime=None,
            normalized_datetime_utc=None,
            jd_ut=None,
            jd_tt=None,
            lst_deg=request.lst_deg,
            observer=LocalSpaceObserverContext(
                latitude=request.latitude,
                longitude=None,
                elevation_m=None,
                source="direct_request",
            ),
            requested_bodies=tuple(request.positions),
            returned_bodies=returned_bodies,
            coordinate_source="direct_ra_dec",
            stage_sequence=DIRECT_STAGE_SEQUENCE,
        ),
    )


def compute_local_space_chart_positions(
    engine: Moira,
    request: LocalSpaceChartPositionsRequest,
) -> LocalSpacePositionsResult:
    chart = _build_chart(engine, request)
    bodies = _selected_bodies(request.bodies, chart.planets)
    jd_tt = ut_to_tt(chart.jd_ut)
    dpsi, _ = nutation(jd_tt)
    obliquity = true_obliquity(jd_tt)
    lst_deg = local_sidereal_time(chart.jd_ut, request.observer_lon, dpsi, obliquity)
    reader = getattr(engine, "_reader", None)
    planet_ra_dec = {
        body: _sky_ra_dec(
            body=body,
            jd_ut=chart.jd_ut,
            observer_lat=request.observer_lat,
            observer_lon=request.observer_lon,
            observer_elev_m=request.observer_elev_m,
            reader=reader,
        )
        for body in bodies
    }
    positions = local_space_positions(
        planet_ra_dec,
        latitude=request.observer_lat,
        lst_deg=lst_deg,
    )
    returned_bodies = tuple(position.body for position in positions)
    return LocalSpacePositionsResult(
        positions=positions,
        provenance=LocalSpaceProvenance(
            requested_datetime=request.dt.isoformat(),
            normalized_datetime_utc=chart.datetime_utc.isoformat(),
            jd_ut=chart.jd_ut,
            jd_tt=jd_tt,
            lst_deg=lst_deg,
            observer=LocalSpaceObserverContext(
                latitude=request.observer_lat,
                longitude=request.observer_lon,
                elevation_m=request.observer_elev_m,
                source="chart_request",
            ),
            requested_bodies=tuple(request.bodies) if request.bodies is not None else None,
            returned_bodies=returned_bodies,
            coordinate_source="chart_apparent_topocentric_ra_dec",
            stage_sequence=CHART_STAGE_SEQUENCE,
        ),
    )


def _build_chart(engine: Moira, request: LocalSpaceChartPositionsRequest):
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
    if len(bodies) > LOCAL_SPACE_MAX_BODIES:
        raise ValueError(f"bodies may contain at most {LOCAL_SPACE_MAX_BODIES} entries")
    return bodies


def _sky_ra_dec(
    *,
    body: str,
    jd_ut: float,
    observer_lat: float,
    observer_lon: float,
    observer_elev_m: float,
    reader,
) -> tuple[float, float]:
    sky = sky_position_at(
        body,
        jd_ut,
        observer_lat=observer_lat,
        observer_lon=observer_lon,
        observer_elev_m=observer_elev_m,
        reader=reader,
    )
    return sky.right_ascension, sky.declination


def _direct_ra_dec_map(positions) -> dict[str, tuple[float, float]]:
    return {
        body: (coordinate.right_ascension, coordinate.declination)
        for body, coordinate in positions.items()
    }


__all__ = [
    "LocalSpaceObserverContext",
    "LocalSpacePositionsResult",
    "LocalSpaceProvenance",
    "compute_local_space_chart_positions",
    "compute_local_space_direct_positions",
]
