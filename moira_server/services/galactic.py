"""Service helpers for Phase-10 Galactic Coordinates routes (P10-04)."""

from __future__ import annotations

from dataclasses import dataclass

from moira import Moira
from moira.galactic import (
    GalacticPosition,
    all_galactic_positions,
    ecliptic_to_galactic,
    equatorial_to_galactic,
    galactic_reference_points,
    galactic_to_ecliptic,
    galactic_to_equatorial,
)
from moira.julian import ut_to_tt
from moira.obliquity import true_obliquity

from ..models.chart import ChartRequest
from ..models.galactic import (
    GALACTIC_MAX_BODIES,
    CoordinateSource,
    FrameName,
    GalacticChartPositionsRequest,
    GalacticEclipticToGalacticRequest,
    GalacticEquatorialToGalacticRequest,
    GalacticGalacticToEclipticRequest,
    GalacticGalacticToEquatorialRequest,
    GalacticReferencePointsRequest,
)
from ._shared import build_chart_context, require_supported_chart_bodies


EQUATORIAL_TO_GALACTIC_STAGE_SEQUENCE = (
    "direct_equatorial_validation",
    "iau_galactic_rotation",
    "response_materialization",
)
GALACTIC_TO_EQUATORIAL_STAGE_SEQUENCE = (
    "direct_galactic_validation",
    "iau_galactic_inverse_rotation",
    "response_materialization",
)
ECLIPTIC_TO_GALACTIC_STAGE_SEQUENCE = (
    "direct_ecliptic_validation",
    "ecliptic_to_true_equatorial",
    "true_equatorial_to_j2000_icrs",
    "iau_galactic_rotation",
    "response_materialization",
)
GALACTIC_TO_ECLIPTIC_STAGE_SEQUENCE = (
    "direct_galactic_validation",
    "iau_galactic_inverse_rotation",
    "j2000_icrs_to_true_equatorial",
    "true_equatorial_to_ecliptic",
    "response_materialization",
)
REFERENCE_POINTS_STAGE_SEQUENCE = (
    "epoch_validation",
    "j2000_reference_point_selection",
    "j2000_icrs_to_true_equatorial",
    "true_equatorial_to_ecliptic",
    "response_materialization",
)
CHART_POSITIONS_STAGE_SEQUENCE = (
    "datetime_validation",
    "chart_context_derivation",
    "chart_body_validation",
    "obliquity_derivation",
    "jd_tt_derivation",
    "chart_ecliptic_coordinate_selection",
    "ecliptic_to_galactic_computation",
    "response_materialization",
)


@dataclass(frozen=True, slots=True)
class GalacticProvenance:
    requested_datetime: str | None
    normalized_datetime_utc: str | None
    jd_ut: float | None
    jd_tt: float | None
    obliquity_deg: float | None
    requested_bodies: tuple[str, ...] | None
    returned_bodies: tuple[str, ...]
    source_frame: FrameName
    target_frame: FrameName
    coordinate_source: CoordinateSource
    stage_sequence: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GalacticCoordinateResult:
    galactic_longitude: float
    galactic_latitude: float
    provenance: GalacticProvenance


@dataclass(frozen=True, slots=True)
class EquatorialCoordinateResult:
    right_ascension: float
    declination: float
    provenance: GalacticProvenance


@dataclass(frozen=True, slots=True)
class EclipticCoordinateResult:
    ecliptic_longitude: float
    ecliptic_latitude: float
    provenance: GalacticProvenance


@dataclass(frozen=True, slots=True)
class GalacticReferencePointsResult:
    points: dict[str, tuple[float, float]]
    provenance: GalacticProvenance


@dataclass(frozen=True, slots=True)
class GalacticPositionsResult:
    positions: list[GalacticPosition]
    provenance: GalacticProvenance


def compute_equatorial_to_galactic(
    request: GalacticEquatorialToGalacticRequest,
) -> GalacticCoordinateResult:
    longitude, latitude = equatorial_to_galactic(
        request.right_ascension,
        request.declination,
    )
    return GalacticCoordinateResult(
        galactic_longitude=longitude,
        galactic_latitude=latitude,
        provenance=_direct_provenance(
            source_frame="equatorial_j2000_icrs",
            target_frame="galactic_iau_1958",
            coordinate_source="direct_equatorial_j2000_icrs",
            stage_sequence=EQUATORIAL_TO_GALACTIC_STAGE_SEQUENCE,
        ),
    )


def compute_galactic_to_equatorial(
    request: GalacticGalacticToEquatorialRequest,
) -> EquatorialCoordinateResult:
    right_ascension, declination = galactic_to_equatorial(
        request.galactic_longitude,
        request.galactic_latitude,
    )
    return EquatorialCoordinateResult(
        right_ascension=right_ascension,
        declination=declination,
        provenance=_direct_provenance(
            source_frame="galactic_iau_1958",
            target_frame="equatorial_j2000_icrs",
            coordinate_source="direct_galactic_iau_1958",
            stage_sequence=GALACTIC_TO_EQUATORIAL_STAGE_SEQUENCE,
        ),
    )


def compute_ecliptic_to_galactic(
    request: GalacticEclipticToGalacticRequest,
) -> GalacticCoordinateResult:
    longitude, latitude = ecliptic_to_galactic(
        request.ecliptic_longitude,
        request.ecliptic_latitude,
        request.obliquity,
        request.jd_tt,
    )
    return GalacticCoordinateResult(
        galactic_longitude=longitude,
        galactic_latitude=latitude,
        provenance=_epoch_provenance(
            jd_tt=request.jd_tt,
            obliquity=request.obliquity,
            source_frame="ecliptic_true_of_date",
            target_frame="galactic_iau_1958",
            coordinate_source="direct_ecliptic_true_of_date",
            stage_sequence=ECLIPTIC_TO_GALACTIC_STAGE_SEQUENCE,
        ),
    )


def compute_galactic_to_ecliptic(
    request: GalacticGalacticToEclipticRequest,
) -> EclipticCoordinateResult:
    longitude, latitude = galactic_to_ecliptic(
        request.galactic_longitude,
        request.galactic_latitude,
        request.obliquity,
        request.jd_tt,
    )
    return EclipticCoordinateResult(
        ecliptic_longitude=longitude,
        ecliptic_latitude=latitude,
        provenance=_epoch_provenance(
            jd_tt=request.jd_tt,
            obliquity=request.obliquity,
            source_frame="galactic_iau_1958",
            target_frame="ecliptic_true_of_date",
            coordinate_source="direct_galactic_iau_1958",
            stage_sequence=GALACTIC_TO_ECLIPTIC_STAGE_SEQUENCE,
        ),
    )


def compute_galactic_reference_points(
    request: GalacticReferencePointsRequest,
) -> GalacticReferencePointsResult:
    points = galactic_reference_points(request.obliquity, request.jd_tt)
    return GalacticReferencePointsResult(
        points=points,
        provenance=_epoch_provenance(
            jd_tt=request.jd_tt,
            obliquity=request.obliquity,
            source_frame="equatorial_j2000_icrs",
            target_frame="ecliptic_true_of_date",
            coordinate_source="reference_point_catalog_j2000_icrs",
            stage_sequence=REFERENCE_POINTS_STAGE_SEQUENCE,
        ),
    )


def compute_galactic_chart_positions(
    engine: Moira,
    request: GalacticChartPositionsRequest,
) -> GalacticPositionsResult:
    chart = _build_chart(engine, request)
    bodies = _selected_bodies(request.bodies, chart.planets)
    jd_tt = ut_to_tt(chart.jd_ut)
    obliquity = true_obliquity(jd_tt)
    body_data = {
        body: (chart.planets[body].longitude, chart.planets[body].latitude)
        for body in bodies
    }
    positions = all_galactic_positions(body_data, obliquity, jd_tt)
    returned_bodies = tuple(position.body for position in positions)
    return GalacticPositionsResult(
        positions=positions,
        provenance=GalacticProvenance(
            requested_datetime=request.dt.isoformat(),
            normalized_datetime_utc=chart.datetime_utc.isoformat(),
            jd_ut=chart.jd_ut,
            jd_tt=jd_tt,
            obliquity_deg=obliquity,
            requested_bodies=tuple(request.bodies) if request.bodies is not None else None,
            returned_bodies=returned_bodies,
            source_frame="ecliptic_true_of_date",
            target_frame="galactic_iau_1958",
            coordinate_source="chart_ecliptic_true_of_date",
            stage_sequence=CHART_POSITIONS_STAGE_SEQUENCE,
        ),
    )


def _direct_provenance(
    *,
    source_frame: FrameName,
    target_frame: FrameName,
    coordinate_source: CoordinateSource,
    stage_sequence: tuple[str, ...],
) -> GalacticProvenance:
    return GalacticProvenance(
        requested_datetime=None,
        normalized_datetime_utc=None,
        jd_ut=None,
        jd_tt=None,
        obliquity_deg=None,
        requested_bodies=None,
        returned_bodies=(),
        source_frame=source_frame,
        target_frame=target_frame,
        coordinate_source=coordinate_source,
        stage_sequence=stage_sequence,
    )


def _epoch_provenance(
    *,
    jd_tt: float,
    obliquity: float,
    source_frame: FrameName,
    target_frame: FrameName,
    coordinate_source: CoordinateSource,
    stage_sequence: tuple[str, ...],
) -> GalacticProvenance:
    return GalacticProvenance(
        requested_datetime=None,
        normalized_datetime_utc=None,
        jd_ut=None,
        jd_tt=jd_tt,
        obliquity_deg=obliquity,
        requested_bodies=None,
        returned_bodies=(),
        source_frame=source_frame,
        target_frame=target_frame,
        coordinate_source=coordinate_source,
        stage_sequence=stage_sequence,
    )


def _build_chart(engine: Moira, request: GalacticChartPositionsRequest):
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
    if len(bodies) > GALACTIC_MAX_BODIES:
        raise ValueError(f"bodies may contain at most {GALACTIC_MAX_BODIES} entries")
    return bodies


__all__ = [
    "EclipticCoordinateResult",
    "EquatorialCoordinateResult",
    "GalacticCoordinateResult",
    "GalacticPositionsResult",
    "GalacticProvenance",
    "GalacticReferencePointsResult",
    "compute_ecliptic_to_galactic",
    "compute_equatorial_to_galactic",
    "compute_galactic_chart_positions",
    "compute_galactic_reference_points",
    "compute_galactic_to_ecliptic",
    "compute_galactic_to_equatorial",
]
