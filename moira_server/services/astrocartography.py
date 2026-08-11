"""Service helpers for Phase-10 Astrocartography routes (P10-01)."""

from __future__ import annotations

from dataclasses import dataclass

from moira import Body, Moira
from moira.astrocartography import (
    ACGLine,
    SubPlanetaryPoint,
    acg_lines,
    fixed_star_equatorial_subject,
    subplanetary_points,
)
from moira.coordinates import ecliptic_to_equatorial
from moira.julian import apparent_sidereal_time, utc_to_tt, utc_to_ut1
from moira.obliquity import nutation, true_obliquity
from moira.planets import planet_at, sky_position_at
from moira.small_body_identity import resolve_small_body_identity

from ..models.astrocartography import (
    ASTROCARTOGRAPHY_MAX_BODIES,
    AstrocartographyChartLinesRequest,
    AstrocartographyChartSubplanetaryRequest,
    AstrocartographyDirectLinesRequest,
    AstrocartographyDirectSubplanetaryRequest,
    AstrocartographySubjectChartLinesRequest,
    AstrocartographySubjectChartSubplanetaryRequest,
    AstrocartographySubjectRequest,
    CoordinateSource,
    ObserverSource,
    SubjectClass,
)
from ..models.chart import ChartRequest
from ..models.lots import LotsChartRequest
from ._shared import build_chart_context, require_supported_chart_bodies
from .lots import compute_lots_chart


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
SUBJECT_LINES_STAGE_SEQUENCE = (
    "datetime_validation",
    "chart_context_derivation",
    "observer_policy_resolution",
    "apparent_sidereal_time_derivation",
    "mixed_subject_resolution",
    "subject_ra_dec_materialization",
    "sampling_policy_validation",
    "acg_line_computation",
    "response_materialization",
)
SUBJECT_SUBPLANETARY_STAGE_SEQUENCE = (
    "datetime_validation",
    "chart_context_derivation",
    "apparent_sidereal_time_derivation",
    "mixed_subject_resolution",
    "subject_ra_dec_materialization",
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
class AstrocartographySubjectProvenance:
    requested_label: str
    returned_label: str
    subject_class: SubjectClass
    canonical_name: str | None
    naif_id: int | None
    position_source: str


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
    subjects: tuple[AstrocartographySubjectProvenance, ...]
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


@dataclass(frozen=True, slots=True)
class ResolvedAstrocartographySubject:
    label: str
    right_ascension: float
    declination: float
    provenance: AstrocartographySubjectProvenance


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
            subjects=_direct_subject_provenance(tuple(request.positions)),
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
            subjects=_direct_subject_provenance(tuple(request.positions)),
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
    dpsi, obliquity, gmst_deg, jd_ut, jd_tt = _sidereal_context(chart.jd_ut)
    reader = getattr(engine, "_reader", None)
    planet_ra_dec = {
        body: _sky_ra_dec(
            body=body,
            jd_ut=jd_ut,
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
        jd_ut=jd_ut,
        refraction=request.refraction,
        reader=reader,
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
            jd_ut=jd_ut,
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
    dpsi, obliquity, gmst_deg, jd_ut, jd_tt = _sidereal_context(chart.jd_ut)
    reader = getattr(engine, "_reader", None)
    planet_ra_dec = {}
    for body in bodies:
        position = planet_at(body, jd_ut, reader=reader)
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
            jd_ut=jd_ut,
            jd_tt=jd_tt,
            dpsi=dpsi,
            obliquity=obliquity,
            stage_sequence=CHART_SUBPLANETARY_STAGE_SEQUENCE,
        ),
    )


def compute_astrocartography_subject_chart_lines(
    engine: Moira,
    request: AstrocartographySubjectChartLinesRequest,
) -> AstrocartographyLinesResult:
    chart = _build_subject_chart(engine, request)
    observer = _resolve_line_observer(request, chart)
    dpsi, obliquity, gmst_deg, jd_ut, jd_tt = _sidereal_context(chart.jd_ut)
    resolved = _resolve_subjects(
        engine=engine,
        request=request,
        chart=chart,
        jd_ut=jd_ut,
        observer=observer,
        obliquity=obliquity,
        jd_tt=jd_tt,
        refraction=request.refraction,
        line_mode=True,
    )
    subject_ra_dec = _resolved_ra_dec_map(resolved)
    reader = getattr(engine, "_reader", None)
    lines = acg_lines(
        subject_ra_dec,
        gmst_deg,
        lat_step=request.lat_step,
        jd_ut=jd_ut,
        refraction=request.refraction,
        reader=reader,
    )
    return AstrocartographyLinesResult(
        lines=lines,
        provenance=_subject_chart_provenance(
            request=request,
            chart=chart,
            resolved=resolved,
            observer=observer,
            lat_step=request.lat_step,
            refraction=request.refraction,
            gmst_deg=gmst_deg,
            jd_ut=jd_ut,
            jd_tt=jd_tt,
            dpsi=dpsi,
            obliquity=obliquity,
            stage_sequence=SUBJECT_LINES_STAGE_SEQUENCE,
        ),
    )


def compute_astrocartography_subject_chart_subplanetary(
    engine: Moira,
    request: AstrocartographySubjectChartSubplanetaryRequest,
) -> AstrocartographySubplanetaryResult:
    chart = _build_subject_chart(engine, request)
    dpsi, obliquity, gmst_deg, jd_ut, jd_tt = _sidereal_context(chart.jd_ut)
    resolved = _resolve_subjects(
        engine=engine,
        request=request,
        chart=chart,
        jd_ut=jd_ut,
        observer=AstrocartographyObserverContext(
            latitude=None,
            longitude=None,
            elevation_m=None,
            source="direct_none",
        ),
        obliquity=obliquity,
        jd_tt=jd_tt,
        refraction=False,
        line_mode=False,
    )
    points = subplanetary_points(_resolved_ra_dec_map(resolved), gmst_deg)
    return AstrocartographySubplanetaryResult(
        points=points,
        provenance=_subject_chart_provenance(
            request=request,
            chart=chart,
            resolved=resolved,
            observer=AstrocartographyObserverContext(
                latitude=None,
                longitude=None,
                elevation_m=None,
                source="direct_none",
            ),
            lat_step=None,
            refraction=None,
            gmst_deg=gmst_deg,
            jd_ut=jd_ut,
            jd_tt=jd_tt,
            dpsi=dpsi,
            obliquity=obliquity,
            stage_sequence=SUBJECT_SUBPLANETARY_STAGE_SEQUENCE,
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


def _build_subject_chart(engine: Moira, request):
    bodies = _subject_chart_bodies(request.subjects)
    require_supported_chart_bodies(bodies)
    return build_chart_context(
        engine,
        ChartRequest(
            dt=request.dt,
            bodies=bodies,
            include_nodes=False,
            observer_lat=request.observer_lat,
            observer_lon=request.observer_lon,
            observer_elev_m=request.observer_elev_m,
        ),
    )


def _subject_chart_bodies(subjects: list[AstrocartographySubjectRequest]) -> list[str]:
    bodies = []
    for subject in subjects:
        if subject.name is None:
            continue
        if subject.kind == "planet":
            bodies.append(subject.name)
        elif subject.kind == "asteroid":
            bodies.append(f"asteroid:{subject.name}")
    return bodies or [Body.SUN]


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


def _sidereal_context(jd_utc: float) -> tuple[float, float, float, float, float]:
    jd_ut = utc_to_ut1(jd_utc)
    jd_tt = utc_to_tt(jd_utc)
    dpsi, _ = nutation(jd_tt)
    obliquity = true_obliquity(jd_tt)
    gmst_deg = apparent_sidereal_time(jd_ut, dpsi, obliquity)
    return dpsi, obliquity, gmst_deg, jd_ut, jd_tt


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


def _resolve_subjects(
    *,
    engine: Moira,
    request,
    chart,
    jd_ut: float,
    observer: AstrocartographyObserverContext,
    obliquity: float,
    jd_tt: float,
    refraction: bool,
    line_mode: bool,
) -> tuple[ResolvedAstrocartographySubject, ...]:
    reader = getattr(engine, "_reader", None)
    lots_by_name = _lot_map(engine, request) if _has_lot_subjects(request.subjects) else {}
    resolved = tuple(
        _resolve_subject(
            subject,
            chart=chart,
            jd_ut=jd_ut,
            observer=observer,
            reader=reader,
            obliquity=obliquity,
            jd_tt=jd_tt,
            refraction=refraction,
            line_mode=line_mode,
            lots_by_name=lots_by_name,
        )
        for subject in request.subjects
    )
    labels = [subject.label for subject in resolved]
    if len(set(labels)) != len(labels):
        raise ValueError("resolved astrocartography subject labels must be unique")
    return resolved


def _resolve_subject(
    subject: AstrocartographySubjectRequest,
    *,
    chart,
    jd_ut: float,
    observer: AstrocartographyObserverContext,
    reader,
    obliquity: float,
    jd_tt: float,
    refraction: bool,
    line_mode: bool,
    lots_by_name: dict[str, object],
) -> ResolvedAstrocartographySubject:
    if subject.kind in {"planet", "asteroid", "comet"}:
        return _resolve_physical_subject(
            subject,
            chart=chart,
            jd_ut=jd_ut,
            observer=observer,
            reader=reader,
            obliquity=obliquity,
            refraction=refraction,
            line_mode=line_mode,
        )
    if subject.kind == "fixed_star":
        return _resolve_fixed_star_subject(subject, obliquity=obliquity, jd_tt=jd_tt)
    if subject.kind == "lot":
        return _resolve_lot_subject(subject, lots_by_name=lots_by_name, obliquity=obliquity)
    if subject.kind == "ecliptic_point":
        return _resolve_ecliptic_point_subject(subject, obliquity=obliquity)
    if subject.kind == "ra_dec_point":
        return _resolve_ra_dec_point_subject(subject)
    raise ValueError(f"unsupported astrocartography subject kind {subject.kind!r}")


def _resolve_physical_subject(
    subject: AstrocartographySubjectRequest,
    *,
    chart,
    jd_ut: float,
    observer: AstrocartographyObserverContext,
    reader,
    obliquity: float,
    refraction: bool,
    line_mode: bool,
) -> ResolvedAstrocartographySubject:
    name = subject.name or ""
    family, canonical_name, naif_id = _physical_subject_identity(subject)
    engine_body = (
        name
        if family == "planet"
        else f"{family}:{canonical_name}"
    )
    label = _subject_label(subject, fallback=canonical_name)
    if line_mode and family in {"planet", "asteroid"}:
        right_ascension, declination = _sky_ra_dec(
            body=engine_body,
            jd_ut=jd_ut,
            observer=observer,
            reader=reader,
            refraction=refraction,
        )
        position_source = f"moira.planets.sky_position_at:{family}"
    else:
        position = planet_at(engine_body, jd_ut, reader=reader)
        right_ascension, declination = ecliptic_to_equatorial(
            position.longitude,
            position.latitude,
            obliquity,
        )
        position_source = f"moira.planets.planet_at:{family}:ecliptic_to_equatorial"
    return ResolvedAstrocartographySubject(
        label=label,
        right_ascension=right_ascension,
        declination=declination,
        provenance=AstrocartographySubjectProvenance(
            requested_label=_subject_label(subject, fallback=name),
            returned_label=label,
            subject_class=family,
            canonical_name=canonical_name,
            naif_id=naif_id,
            position_source=position_source,
        ),
    )


def _physical_subject_identity(subject: AstrocartographySubjectRequest) -> tuple[SubjectClass, str, int | None]:
    name = subject.name or ""
    if subject.kind == "planet":
        if name not in Body.ALL_PLANETS:
            raise ValueError(f"planet subject {name!r} is not an admitted planet")
        return "planet", name, None
    identity = resolve_small_body_identity(name, family=subject.kind)
    if identity is None:
        raise ValueError(f"{subject.kind} subject {name!r} is not an admitted small body")
    return identity.family, identity.canonical_name, identity.naif_id


def _resolve_fixed_star_subject(
    subject: AstrocartographySubjectRequest,
    *,
    obliquity: float,
    jd_tt: float,
) -> ResolvedAstrocartographySubject:
    star = fixed_star_equatorial_subject(subject.name or "", jd_tt, obliquity)
    label = _subject_label(subject, fallback=star.canonical_name)
    return ResolvedAstrocartographySubject(
        label=label,
        right_ascension=star.right_ascension,
        declination=star.declination,
        provenance=AstrocartographySubjectProvenance(
            requested_label=_subject_label(subject, fallback=subject.name or ""),
            returned_label=label,
            subject_class="fixed_star",
            canonical_name=star.canonical_name,
            naif_id=None,
            position_source=star.position_source,
        ),
    )


def _resolve_lot_subject(
    subject: AstrocartographySubjectRequest,
    *,
    lots_by_name: dict[str, object],
    obliquity: float,
) -> ResolvedAstrocartographySubject:
    lookup = (subject.name or "").casefold()
    lot = lots_by_name.get(lookup)
    if lot is None:
        raise ValueError(f"lot subject {subject.name!r} was not computed by the lots engine")
    label = _subject_label(subject, fallback=lot.name)
    right_ascension, declination = ecliptic_to_equatorial(
        lot.longitude,
        0.0,
        obliquity,
    )
    return ResolvedAstrocartographySubject(
        label=label,
        right_ascension=right_ascension,
        declination=declination,
        provenance=AstrocartographySubjectProvenance(
            requested_label=_subject_label(subject, fallback=subject.name or ""),
            returned_label=label,
            subject_class="lot",
            canonical_name=lot.name,
            naif_id=None,
            position_source="moira.lots.calculate_parts:ecliptic_point_to_equatorial",
        ),
    )


def _resolve_ecliptic_point_subject(
    subject: AstrocartographySubjectRequest,
    *,
    obliquity: float,
) -> ResolvedAstrocartographySubject:
    label = _subject_label(subject, fallback="Ecliptic Point")
    right_ascension, declination = ecliptic_to_equatorial(
        subject.longitude or 0.0,
        subject.latitude,
        obliquity,
    )
    return ResolvedAstrocartographySubject(
        label=label,
        right_ascension=right_ascension,
        declination=declination,
        provenance=AstrocartographySubjectProvenance(
            requested_label=label,
            returned_label=label,
            subject_class="ecliptic_point",
            canonical_name=None,
            naif_id=None,
            position_source="caller_supplied_ecliptic_point:ecliptic_to_equatorial",
        ),
    )


def _resolve_ra_dec_point_subject(
    subject: AstrocartographySubjectRequest,
) -> ResolvedAstrocartographySubject:
    label = _subject_label(subject, fallback="RA/Dec Point")
    return ResolvedAstrocartographySubject(
        label=label,
        right_ascension=subject.right_ascension or 0.0,
        declination=subject.declination or 0.0,
        provenance=AstrocartographySubjectProvenance(
            requested_label=label,
            returned_label=label,
            subject_class="ra_dec_point",
            canonical_name=None,
            naif_id=None,
            position_source="caller_supplied_direct_ra_dec",
        ),
    )


def _has_lot_subjects(subjects: list[AstrocartographySubjectRequest]) -> bool:
    return any(subject.kind == "lot" for subject in subjects)


def _lot_map(engine: Moira, request) -> dict[str, object]:
    parts = compute_lots_chart(
        engine,
        LotsChartRequest(
            dt=request.dt,
            observer_lat=request.observer_lat,
            observer_lon=request.observer_lon,
            observer_elev_m=request.observer_elev_m,
            house_system=request.house_system,
            syzygy=request.syzygy,
            prenatal_new_moon=request.prenatal_new_moon,
            prenatal_full_moon=request.prenatal_full_moon,
            lord_of_hour=request.lord_of_hour,
            policy=request.policy,
        ),
    )
    return {part.name.casefold(): part for part in parts}


def _resolved_ra_dec_map(
    resolved: tuple[ResolvedAstrocartographySubject, ...],
) -> dict[str, tuple[float, float]]:
    return {
        subject.label: (subject.right_ascension, subject.declination)
        for subject in resolved
    }


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
    jd_ut: float,
    jd_tt: float,
    dpsi: float,
    obliquity: float,
    stage_sequence: tuple[str, ...],
) -> AstrocartographyProvenance:
    return AstrocartographyProvenance(
        requested_datetime=request.dt.isoformat(),
        normalized_datetime_utc=chart.datetime_utc.isoformat(),
        jd_ut=jd_ut,
        jd_tt=jd_tt,
        gmst_deg=gmst_deg,
        obliquity_deg=obliquity,
        nutation_longitude_deg=dpsi,
        requested_bodies=tuple(request.bodies) if request.bodies is not None else None,
        returned_bodies=bodies,
        observer=observer,
        coordinate_source=coordinate_source,
        subjects=_chart_subject_provenance(bodies, coordinate_source),
        lat_step=lat_step,
        refraction=refraction,
        stage_sequence=stage_sequence,
    )


def _subject_chart_provenance(
    *,
    request,
    chart,
    resolved: tuple[ResolvedAstrocartographySubject, ...],
    observer: AstrocartographyObserverContext,
    lat_step: float | None,
    refraction: bool | None,
    gmst_deg: float,
    jd_ut: float,
    jd_tt: float,
    dpsi: float,
    obliquity: float,
    stage_sequence: tuple[str, ...],
) -> AstrocartographyProvenance:
    labels = tuple(subject.label for subject in resolved)
    return AstrocartographyProvenance(
        requested_datetime=request.dt.isoformat(),
        normalized_datetime_utc=chart.datetime_utc.isoformat(),
        jd_ut=jd_ut,
        jd_tt=jd_tt,
        gmst_deg=gmst_deg,
        obliquity_deg=obliquity,
        nutation_longitude_deg=dpsi,
        requested_bodies=tuple(_subject_label(subject, fallback=subject.name or "") for subject in request.subjects),
        returned_bodies=labels,
        observer=observer,
        coordinate_source="chart_mixed_subject_ra_dec",
        subjects=tuple(subject.provenance for subject in resolved),
        lat_step=lat_step,
        refraction=refraction,
        stage_sequence=stage_sequence,
    )


def _direct_ra_dec_map(positions) -> dict[str, tuple[float, float]]:
    return {
        body: (coordinate.right_ascension, coordinate.declination)
        for body, coordinate in positions.items()
    }


def _direct_subject_provenance(
    bodies: tuple[str, ...],
) -> tuple[AstrocartographySubjectProvenance, ...]:
    return tuple(
        AstrocartographySubjectProvenance(
            requested_label=body,
            returned_label=body,
            subject_class="caller_supplied",
            canonical_name=None,
            naif_id=None,
            position_source="caller_supplied_direct_ra_dec",
        )
        for body in bodies
    )


def _chart_subject_provenance(
    bodies: tuple[str, ...],
    coordinate_source: CoordinateSource,
) -> tuple[AstrocartographySubjectProvenance, ...]:
    return tuple(
        _chart_subject_for_body(body, coordinate_source)
        for body in bodies
    )


def _chart_subject_for_body(
    body: str,
    coordinate_source: CoordinateSource,
) -> AstrocartographySubjectProvenance:
    identity = resolve_small_body_identity(body)
    if identity is not None:
        return AstrocartographySubjectProvenance(
            requested_label=body,
            returned_label=body,
            subject_class=identity.family,
            canonical_name=identity.canonical_name,
            naif_id=identity.naif_id,
            position_source=_chart_position_source(
                identity.family,
                coordinate_source,
            ),
        )
    if body in Body.ALL_PLANETS:
        return AstrocartographySubjectProvenance(
            requested_label=body,
            returned_label=body,
            subject_class="planet",
            canonical_name=body,
            naif_id=None,
            position_source=_chart_position_source("planet", coordinate_source),
        )
    return AstrocartographySubjectProvenance(
        requested_label=body,
        returned_label=body,
        subject_class="caller_supplied",
        canonical_name=None,
        naif_id=None,
        position_source=_chart_position_source("unknown", coordinate_source),
    )

def _chart_position_source(family: str, coordinate_source: CoordinateSource) -> str:
    if coordinate_source == "chart_apparent_topocentric_ra_dec":
        return f"moira.planets.sky_position_at:{family}"
    if coordinate_source == "chart_geocentric_ecliptic_to_equatorial":
        return f"moira.planets.planet_at:{family}"
    return str(coordinate_source)


def _subject_label(
    subject: AstrocartographySubjectRequest,
    *,
    fallback: str,
) -> str:
    return subject.label or subject.name or fallback


__all__ = [
    "AstrocartographyLinesResult",
    "AstrocartographyObserverContext",
    "AstrocartographyProvenance",
    "ResolvedAstrocartographySubject",
    "AstrocartographySubjectProvenance",
    "AstrocartographySubplanetaryResult",
    "compute_astrocartography_chart_lines",
    "compute_astrocartography_chart_subplanetary",
    "compute_astrocartography_direct_lines",
    "compute_astrocartography_direct_subplanetary",
    "compute_astrocartography_subject_chart_lines",
    "compute_astrocartography_subject_chart_subplanetary",
]
