"""Service helpers for Phase-10 Galactic Houses routes (P10-05)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timezone

from moira import Moira
from moira.galactic import ecliptic_to_galactic
from moira.galactic_houses import (
    GalacticAngles,
    GalacticHouseBoundaryProfile,
    GalacticHouseCusps,
    GalacticHousePlacement,
    assign_galactic_house,
    body_galactic_house_position,
    calculate_galactic_houses,
    describe_galactic_boundary,
)
from moira.julian import jd_from_datetime, local_sidereal_time, ut_to_tt
from moira.obliquity import nutation, true_obliquity

from ..models.chart import ChartRequest
from ..models.galactic_houses import (
    GALACTIC_HOUSES_MAX_BODIES,
    CoordinateSource,
    GalacticHouseCuspsRequest,
    GalacticHousePlacementRequest,
    GalacticHousesChartPlacementsRequest,
    GalacticHousesChartRequest,
)
from ._shared import build_chart_context, require_supported_chart_bodies


CUSPS_STAGE_SEQUENCE = (
    "datetime_validation",
    "location_validation",
    "jd_ut_derivation",
    "jd_tt_derivation",
    "obliquity_derivation",
    "armc_derivation",
    "galactic_angle_search",
    "galactic_porphyry_trisection",
    "ecliptic_projection",
    "response_materialization",
)
DIRECT_PLACEMENT_STAGE_SEQUENCE = (
    "direct_galactic_longitude_validation",
    "supplied_cusp_validation",
    "galactic_house_assignment",
    "fractional_position_derivation",
    "boundary_profile_derivation",
    "response_materialization",
)
CHART_PLACEMENTS_STAGE_SEQUENCE = (
    "datetime_validation",
    "location_validation",
    "chart_context_derivation",
    "chart_body_validation",
    "jd_tt_derivation",
    "obliquity_derivation",
    "armc_derivation",
    "galactic_angle_search",
    "galactic_porphyry_trisection",
    "chart_ecliptic_coordinate_selection",
    "ecliptic_to_galactic_computation",
    "galactic_house_assignment",
    "fractional_position_derivation",
    "boundary_profile_derivation",
    "response_materialization",
)


@dataclass(frozen=True, slots=True)
class GalacticHousesProvenance:
    requested_datetime: str | None
    normalized_datetime_utc: str | None
    jd_ut: float | None
    jd_tt: float | None
    latitude: float | None
    longitude: float | None
    obliquity_deg: float | None
    armc_deg: float | None
    requested_bodies: tuple[str, ...] | None
    returned_bodies: tuple[str, ...]
    coordinate_source: CoordinateSource
    stage_sequence: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GalacticHousePlacementResult:
    placement: GalacticHousePlacement
    fractional_position: float
    boundary: GalacticHouseBoundaryProfile


@dataclass(frozen=True, slots=True)
class GalacticHouseCuspsResult:
    cusps: GalacticHouseCusps
    provenance: GalacticHousesProvenance


@dataclass(frozen=True, slots=True)
class GalacticHouseDirectPlacementResult:
    placement_result: GalacticHousePlacementResult
    provenance: GalacticHousesProvenance


@dataclass(frozen=True, slots=True)
class GalacticHouseBodyPlacementResult:
    body: str
    ecliptic_longitude: float
    ecliptic_latitude: float
    galactic_longitude: float
    galactic_latitude: float
    placement_result: GalacticHousePlacementResult


@dataclass(frozen=True, slots=True)
class GalacticHouseChartPlacementsResult:
    cusps: GalacticHouseCusps
    placements: list[GalacticHouseBodyPlacementResult]
    provenance: GalacticHousesProvenance


def compute_galactic_house_cusps(
    request: GalacticHousesChartRequest,
) -> GalacticHouseCuspsResult:
    jd_ut = jd_from_datetime(request.dt)
    jd_tt, obliquity, armc = _epoch_context(
        jd_ut=jd_ut,
        longitude=request.longitude,
    )
    cusps = calculate_galactic_houses(
        jd_ut,
        request.latitude,
        request.longitude,
    )
    return GalacticHouseCuspsResult(
        cusps=cusps,
        provenance=_chart_provenance(
            request=request,
            normalized_datetime_utc=request.dt.astimezone(timezone.utc).isoformat(),
            jd_ut=jd_ut,
            jd_tt=jd_tt,
            obliquity=obliquity,
            armc=armc,
            requested_bodies=None,
            returned_bodies=(),
            coordinate_source="chart_time_location_galactic_porphyry",
            stage_sequence=CUSPS_STAGE_SEQUENCE,
        ),
    )


def compute_galactic_house_placement(
    request: GalacticHousePlacementRequest,
) -> GalacticHouseDirectPlacementResult:
    cusps = _request_to_cusps(request.house_cusps)
    placement_result = _placement_result(
        galactic_longitude=request.galactic_longitude,
        cusps=cusps,
        near_cusp_threshold=request.near_cusp_threshold,
    )
    return GalacticHouseDirectPlacementResult(
        placement_result=placement_result,
        provenance=GalacticHousesProvenance(
            requested_datetime=None,
            normalized_datetime_utc=None,
            jd_ut=None,
            jd_tt=None,
            latitude=None,
            longitude=None,
            obliquity_deg=None,
            armc_deg=None,
            requested_bodies=None,
            returned_bodies=(),
            coordinate_source="direct_galactic_longitude_and_supplied_cusps",
            stage_sequence=DIRECT_PLACEMENT_STAGE_SEQUENCE,
        ),
    )


def compute_galactic_house_chart_placements(
    engine: Moira,
    request: GalacticHousesChartPlacementsRequest,
) -> GalacticHouseChartPlacementsResult:
    chart = _build_chart(engine, request)
    bodies = _selected_bodies(request.bodies, chart.planets)
    jd_tt, obliquity, armc = _epoch_context(
        jd_ut=chart.jd_ut,
        longitude=request.longitude,
    )
    cusps = calculate_galactic_houses(
        chart.jd_ut,
        request.latitude,
        request.longitude,
    )
    placements: list[GalacticHouseBodyPlacementResult] = []
    for body in bodies:
        planet = chart.planets[body]
        gal_lon, gal_lat = ecliptic_to_galactic(
            planet.longitude,
            planet.latitude,
            obliquity,
            jd_tt,
        )
        placements.append(
            GalacticHouseBodyPlacementResult(
                body=body,
                ecliptic_longitude=planet.longitude,
                ecliptic_latitude=planet.latitude,
                galactic_longitude=gal_lon,
                galactic_latitude=gal_lat,
                placement_result=_placement_result(
                    galactic_longitude=gal_lon,
                    cusps=cusps,
                    near_cusp_threshold=request.near_cusp_threshold,
                ),
            )
        )
    returned_bodies = tuple(placement.body for placement in placements)
    return GalacticHouseChartPlacementsResult(
        cusps=cusps,
        placements=placements,
        provenance=_chart_provenance(
            request=request,
            normalized_datetime_utc=chart.datetime_utc.isoformat(),
            jd_ut=chart.jd_ut,
            jd_tt=jd_tt,
            obliquity=obliquity,
            armc=armc,
            requested_bodies=tuple(request.bodies) if request.bodies is not None else None,
            returned_bodies=returned_bodies,
            coordinate_source="chart_ecliptic_to_galactic_positions",
            stage_sequence=CHART_PLACEMENTS_STAGE_SEQUENCE,
        ),
    )


def _placement_result(
    *,
    galactic_longitude: float,
    cusps: GalacticHouseCusps,
    near_cusp_threshold: float,
) -> GalacticHousePlacementResult:
    placement = assign_galactic_house(galactic_longitude, cusps)
    fractional_position = body_galactic_house_position(galactic_longitude, cusps)
    boundary = describe_galactic_boundary(
        placement,
        near_cusp_threshold=near_cusp_threshold,
    )
    return GalacticHousePlacementResult(
        placement=placement,
        fractional_position=fractional_position,
        boundary=boundary,
    )


def _request_to_cusps(request: GalacticHouseCuspsRequest) -> GalacticHouseCusps:
    angles = GalacticAngles(
        ga_lon=request.angles.ga_lon,
        gmc_lon=request.angles.gmc_lon,
        gd_lon=request.angles.gd_lon,
        gic_lon=request.angles.gic_lon,
        ga_ecl=request.angles.ga_ecl,
        gmc_ecl=request.angles.gmc_ecl,
        gd_ecl=request.angles.gd_ecl,
        gic_ecl=request.angles.gic_ecl,
    )
    return GalacticHouseCusps(
        cusps_ecl=tuple(request.cusps_ecl),
        cusps_gal=tuple(request.cusps_gal),
        angles=angles,
        forward=request.forward,
    )


def _epoch_context(
    *,
    jd_ut: float,
    longitude: float,
) -> tuple[float, float, float]:
    jd_tt = ut_to_tt(jd_ut)
    dpsi, _ = nutation(jd_tt)
    obliquity = true_obliquity(jd_tt)
    armc = local_sidereal_time(jd_ut, longitude, dpsi, obliquity)
    return jd_tt, obliquity, armc


def _chart_provenance(
    *,
    request,
    normalized_datetime_utc: str,
    jd_ut: float,
    jd_tt: float,
    obliquity: float,
    armc: float,
    requested_bodies: tuple[str, ...] | None,
    returned_bodies: tuple[str, ...],
    coordinate_source: CoordinateSource,
    stage_sequence: tuple[str, ...],
) -> GalacticHousesProvenance:
    return GalacticHousesProvenance(
        requested_datetime=request.dt.isoformat(),
        normalized_datetime_utc=normalized_datetime_utc,
        jd_ut=jd_ut,
        jd_tt=jd_tt,
        latitude=request.latitude,
        longitude=request.longitude,
        obliquity_deg=obliquity,
        armc_deg=armc,
        requested_bodies=requested_bodies,
        returned_bodies=returned_bodies,
        coordinate_source=coordinate_source,
        stage_sequence=stage_sequence,
    )


def _build_chart(engine: Moira, request: GalacticHousesChartPlacementsRequest):
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
    if len(bodies) > GALACTIC_HOUSES_MAX_BODIES:
        raise ValueError(f"bodies may contain at most {GALACTIC_HOUSES_MAX_BODIES} entries")
    return bodies


__all__ = [
    "GalacticHouseBodyPlacementResult",
    "GalacticHouseChartPlacementsResult",
    "GalacticHouseCuspsResult",
    "GalacticHouseDirectPlacementResult",
    "GalacticHousePlacementResult",
    "GalacticHousesProvenance",
    "compute_galactic_house_chart_placements",
    "compute_galactic_house_cusps",
    "compute_galactic_house_placement",
]
