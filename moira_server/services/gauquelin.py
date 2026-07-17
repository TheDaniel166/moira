"""Service helpers for Phase-10 Gauquelin Sectors routes (P10-06)."""

from __future__ import annotations

from dataclasses import dataclass

from moira import Moira
from moira.gauquelin import GauquelinPosition, all_gauquelin_sectors, gauquelin_sector
from moira.julian import local_sidereal_time, utc_to_tt, utc_to_ut1
from moira.obliquity import nutation, true_obliquity
from moira.planets import sky_position_at

from ..models.chart import ChartRequest
from ..models.gauquelin import (
    CoordinateSource,
    GAUQUELIN_MAX_CHART_BODIES,
    GauquelinChartSectorsRequest,
    GauquelinDirectSectorRequest,
    GauquelinDirectSectorsRequest,
)
from ._shared import build_chart_context, require_supported_chart_bodies


DIRECT_SECTOR_STAGE_SEQUENCE = (
    "direct_ra_dec_validation",
    "location_validation",
    "lst_validation",
    "horizon_altitude_validation",
    "canonical_sector_policy_validation",
    "gauquelin_sector_computation",
    "response_materialization",
)
DIRECT_SECTORS_STAGE_SEQUENCE = (
    "direct_body_list_validation",
    "direct_ra_dec_validation",
    "location_validation",
    "lst_validation",
    "horizon_altitude_validation",
    "canonical_sector_policy_validation",
    "gauquelin_sector_computation",
    "response_materialization",
)
CHART_SECTORS_STAGE_SEQUENCE = (
    "datetime_validation",
    "location_validation",
    "chart_body_validation",
    "jd_ut_derivation",
    "jd_tt_derivation",
    "nutation_derivation",
    "true_obliquity_derivation",
    "local_sidereal_time_derivation",
    "apparent_topocentric_ra_dec_derivation",
    "horizon_altitude_validation",
    "canonical_sector_policy_validation",
    "gauquelin_sector_computation",
    "response_materialization",
)


@dataclass(frozen=True, slots=True)
class GauquelinSourceCoordinate:
    right_ascension: float
    declination: float


@dataclass(frozen=True, slots=True)
class GauquelinProvenance:
    requested_datetime: str | None
    normalized_datetime_utc: str | None
    jd_ut: float | None
    jd_tt: float | None
    latitude: float
    longitude: float | None
    local_sidereal_time: float
    horizon_altitude: float
    sectors: int
    requested_bodies: tuple[str, ...] | None
    returned_bodies: tuple[str, ...]
    coordinate_source: CoordinateSource
    stage_sequence: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GauquelinPositionResult:
    position: GauquelinPosition
    source_coordinate: GauquelinSourceCoordinate | None = None


@dataclass(frozen=True, slots=True)
class GauquelinSectorResult:
    position: GauquelinPositionResult
    provenance: GauquelinProvenance


@dataclass(frozen=True, slots=True)
class GauquelinSectorsResult:
    positions: list[GauquelinPositionResult]
    provenance: GauquelinProvenance


def compute_gauquelin_sector(
    request: GauquelinDirectSectorRequest,
) -> GauquelinSectorResult:
    body = request.body or ""
    position = gauquelin_sector(
        request.right_ascension,
        request.declination,
        request.latitude,
        request.local_sidereal_time,
        body=body,
        horizon_altitude=request.horizon_altitude,
        sectors=request.sectors,
    )
    returned_bodies = (position.body,) if position.body else ()
    return GauquelinSectorResult(
        position=GauquelinPositionResult(position=position),
        provenance=GauquelinProvenance(
            requested_datetime=None,
            normalized_datetime_utc=None,
            jd_ut=None,
            jd_tt=None,
            latitude=request.latitude,
            longitude=None,
            local_sidereal_time=request.local_sidereal_time,
            horizon_altitude=request.horizon_altitude,
            sectors=request.sectors,
            requested_bodies=(body,) if body else None,
            returned_bodies=returned_bodies,
            coordinate_source="direct_apparent_ra_dec_lst",
            stage_sequence=DIRECT_SECTOR_STAGE_SEQUENCE,
        ),
    )


def compute_gauquelin_sectors(
    request: GauquelinDirectSectorsRequest,
) -> GauquelinSectorsResult:
    body_coordinates = {
        body.body: (body.right_ascension, body.declination)
        for body in request.bodies
    }
    positions = all_gauquelin_sectors(
        body_coordinates,
        lat=request.latitude,
        lst=request.local_sidereal_time,
        horizon_altitude=request.horizon_altitude,
        sectors=request.sectors,
    )
    returned_bodies = tuple(position.body for position in positions)
    return GauquelinSectorsResult(
        positions=[
            GauquelinPositionResult(position=position)
            for position in positions
        ],
        provenance=GauquelinProvenance(
            requested_datetime=None,
            normalized_datetime_utc=None,
            jd_ut=None,
            jd_tt=None,
            latitude=request.latitude,
            longitude=None,
            local_sidereal_time=request.local_sidereal_time,
            horizon_altitude=request.horizon_altitude,
            sectors=request.sectors,
            requested_bodies=tuple(body_coordinates),
            returned_bodies=returned_bodies,
            coordinate_source="direct_apparent_ra_dec_map_lst",
            stage_sequence=DIRECT_SECTORS_STAGE_SEQUENCE,
        ),
    )


def compute_gauquelin_chart_sectors(
    engine: Moira,
    request: GauquelinChartSectorsRequest,
) -> GauquelinSectorsResult:
    chart = _build_chart(engine, request)
    bodies = _selected_bodies(request.bodies, chart.planets)
    jd_tt = utc_to_tt(chart.jd_ut)
    jd_ut1 = utc_to_ut1(chart.jd_ut)
    dpsi, _ = nutation(jd_tt)
    obliquity = true_obliquity(jd_tt)
    lst = local_sidereal_time(jd_ut1, request.longitude, dpsi, obliquity)
    reader = getattr(engine, "_reader", None)

    positions: list[GauquelinPositionResult] = []
    for body in bodies:
        sky = sky_position_at(
            body,
            jd_ut1,
            observer_lat=request.latitude,
            observer_lon=request.longitude,
            observer_elev_m=0.0,
            reader=reader,
        )
        position = gauquelin_sector(
            sky.right_ascension,
            sky.declination,
            request.latitude,
            lst,
            body=body,
            horizon_altitude=request.horizon_altitude,
            sectors=request.sectors,
        )
        positions.append(
            GauquelinPositionResult(
                position=position,
                source_coordinate=GauquelinSourceCoordinate(
                    right_ascension=sky.right_ascension,
                    declination=sky.declination,
                ),
            )
        )

    returned_bodies = tuple(position.position.body for position in positions)
    return GauquelinSectorsResult(
        positions=positions,
        provenance=GauquelinProvenance(
            requested_datetime=request.dt.isoformat(),
            normalized_datetime_utc=chart.datetime_utc.isoformat(),
            jd_ut=jd_ut1,
            jd_tt=jd_tt,
            latitude=request.latitude,
            longitude=request.longitude,
            local_sidereal_time=lst,
            horizon_altitude=request.horizon_altitude,
            sectors=request.sectors,
            requested_bodies=tuple(request.bodies) if request.bodies is not None else None,
            returned_bodies=returned_bodies,
            coordinate_source="chart_apparent_topocentric_ra_dec_lst",
            stage_sequence=CHART_SECTORS_STAGE_SEQUENCE,
        ),
    )


def _build_chart(engine: Moira, request: GauquelinChartSectorsRequest):
    require_supported_chart_bodies(request.bodies)
    return build_chart_context(
        engine,
        ChartRequest(
            dt=request.dt,
            bodies=request.bodies,
            include_nodes=False,
            observer_lat=request.latitude,
            observer_lon=request.longitude,
            observer_elev_m=0.0,
        ),
    )


def _selected_bodies(
    requested: list[str] | None,
    chart_planets,
) -> tuple[str, ...]:
    bodies = tuple(requested or chart_planets.keys())
    if len(bodies) > GAUQUELIN_MAX_CHART_BODIES:
        raise ValueError(f"bodies may contain at most {GAUQUELIN_MAX_CHART_BODIES} entries")
    return bodies


__all__ = [
    "GauquelinPositionResult",
    "GauquelinProvenance",
    "GauquelinSectorResult",
    "GauquelinSectorsResult",
    "GauquelinSourceCoordinate",
    "compute_gauquelin_chart_sectors",
    "compute_gauquelin_sector",
    "compute_gauquelin_sectors",
]
