"""Service boundary for Church of Light natal Astrodynes routes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from moira import Moira
from moira.astrodynes import (
    ASTRODYNE_ASPECT_ORB_ROWS,
    ASTRODYNE_DIGNITY_ROWS,
    ASTRODYNE_ELEMENT_GROUPS,
    ASTRODYNE_HOUSE_CLASSES,
    ASTRODYNE_HOUSE_POWER_ROWS,
    ASTRODYNE_PLANETS,
    ASTRODYNE_POINTS,
    ASTRODYNE_QUALITY_GROUPS,
    ASTRODYNE_SIGNS,
    ASTRODYNE_SOCIETY_GROUPS,
    ASTRODYNE_TRINITY_GROUPS,
    DEFAULT_ASTRODYNE_POLICY,
    AstrodyneAspectOrbRow,
    AstrodyneChartResult,
    AstrodyneDignityRow,
    AstrodyneHousePowerRow,
    AstrodynePolicy,
    natal_astrodynes_from_geometry,
)
from moira.coordinates import ecliptic_to_equatorial
from moira.houses import HousePolicy
from moira.julian import utc_to_ut1

from ..models.astrodynes import AstrodynesChartRequest, AstrodynesGeometryRequest
from ._shared import _resolve_house_system, require_aware_datetime


_STAGE_SEQUENCE: tuple[str, ...] = (
    "geometry_normalization",
    "relation_detection",
    "relation_admission_and_scoring",
    "body_condition_profiles",
    "sign_and_house_aggregation",
    "summary_profiles",
    "condition_network",
    "cross_layer_validation",
)


@dataclass(frozen=True, slots=True)
class AstrodynesDoctrineTruth:
    planets: tuple[str, ...]
    points: tuple[str, ...]
    signs: tuple[str, ...]
    house_classes: tuple[str, ...]
    policy: AstrodynePolicy
    dignity_rows: tuple[AstrodyneDignityRow, ...]
    house_power_rows: tuple[AstrodyneHousePowerRow, ...]
    aspect_orb_rows: tuple[AstrodyneAspectOrbRow, ...]
    summary_groups: tuple[tuple[str, str, tuple[int | str, ...]], ...]


@dataclass(frozen=True, slots=True)
class AstrodynesCalculationTruth:
    result: AstrodyneChartResult
    source_mode: Literal["explicit_geometry", "chart_backed"]
    dt: datetime | None
    observer_lat: float | None
    observer_lon: float | None
    jd_ut: float | None
    obliquity_deg: float | None
    planet_longitudes: dict[str, float]
    declinations: dict[str, float]
    cusp_longitudes: tuple[float, ...]
    mc_longitude: float
    asc_longitude: float
    requested_house_system: str | None
    effective_house_system: str | None
    house_fallback: bool
    house_fallback_reason: str | None
    engine_entrypoint: str
    planetary_frame: Literal["caller_supplied", "geocentric_apparent"]
    kernel_required: bool
    stage_sequence: tuple[str, ...] = _STAGE_SEQUENCE


def _require_admitted_cusp_distribution(cusps: tuple[float, ...]) -> None:
    counts = {
        sign: sum(
            1
            for cusp in cusps
            if ASTRODYNE_SIGNS[int((cusp % 360.0) // 30.0)] == sign
        )
        for sign in ASTRODYNE_SIGNS
    }
    unsupported = tuple(
        f"{sign}={count}" for sign, count in counts.items() if count > 2
    )
    if unsupported:
        raise ValueError(
            "the validated Astrodyne aggregate admits at most two house cusps "
            "per sign; unsupported cusp distribution: " + ", ".join(unsupported)
        )


def get_astrodynes_doctrine() -> AstrodynesDoctrineTruth:
    """Return the exact immutable tables and fixed policy admitted by the engine."""

    summary_groups = tuple(
        (family, name, tuple(members))
        for family, groups in (
            ("society", ASTRODYNE_SOCIETY_GROUPS),
            ("trinity", ASTRODYNE_TRINITY_GROUPS),
            ("element", ASTRODYNE_ELEMENT_GROUPS),
            ("quality", ASTRODYNE_QUALITY_GROUPS),
        )
        for name, members in groups
    )
    return AstrodynesDoctrineTruth(
        planets=ASTRODYNE_PLANETS,
        points=ASTRODYNE_POINTS,
        signs=ASTRODYNE_SIGNS,
        house_classes=ASTRODYNE_HOUSE_CLASSES,
        policy=DEFAULT_ASTRODYNE_POLICY,
        dignity_rows=ASTRODYNE_DIGNITY_ROWS,
        house_power_rows=ASTRODYNE_HOUSE_POWER_ROWS,
        aspect_orb_rows=ASTRODYNE_ASPECT_ORB_ROWS,
        summary_groups=summary_groups,
    )


def compute_astrodynes_geometry(
    request: AstrodynesGeometryRequest,
) -> AstrodynesCalculationTruth:
    """Compute a complete natal result from caller-supplied tropical geometry."""

    _require_admitted_cusp_distribution(request.cusp_longitudes)
    result = natal_astrodynes_from_geometry(
        request.planet_longitudes,
        request.declinations,
        request.cusp_longitudes,
        request.mc_longitude,
        request.asc_longitude,
    )
    return AstrodynesCalculationTruth(
        result=result,
        source_mode="explicit_geometry",
        dt=None,
        observer_lat=None,
        observer_lon=None,
        jd_ut=None,
        obliquity_deg=None,
        planet_longitudes={
            item.body: item.longitude_deg
            for item in result.inputs
            if item.body in ASTRODYNE_PLANETS
        },
        declinations={
            item.body: item.declination_deg
            for item in result.inputs
            if item.declination_deg is not None
        },
        cusp_longitudes=tuple(value % 360.0 for value in request.cusp_longitudes),
        mc_longitude=request.mc_longitude % 360.0,
        asc_longitude=request.asc_longitude % 360.0,
        requested_house_system=None,
        effective_house_system=None,
        house_fallback=False,
        house_fallback_reason=None,
        engine_entrypoint="moira.astrodynes.natal_astrodynes_from_geometry",
        planetary_frame="caller_supplied",
        kernel_required=False,
    )


def compute_astrodynes_chart(
    engine: Moira,
    request: AstrodynesChartRequest,
) -> AstrodynesCalculationTruth:
    """Derive the exact Astrodyne geometry from one chart and house figure."""

    require_aware_datetime(request.dt)
    requested_system = _resolve_house_system(request.house_system)
    house_policy = (
        HousePolicy.default() if request.allow_house_fallback else HousePolicy.strict()
    )

    houses = engine.houses(
        request.dt,
        latitude=request.observer_lat,
        longitude=request.observer_lon,
        system=requested_system,
        policy=house_policy,
    )
    _require_admitted_cusp_distribution(tuple(houses.cusps))

    # Astrodyne declinations are geocentric apparent chart quantities.  The
    # observer coordinates govern houses only; passing them into chart() would
    # silently make the Moon topocentric and change the doctrinal object.
    chart = engine.chart(
        request.dt,
        bodies=list(ASTRODYNE_PLANETS),
        include_nodes=False,
    )

    planet_longitudes = {
        body: chart.planets[body].longitude for body in ASTRODYNE_PLANETS
    }
    declinations = {
        body: ecliptic_to_equatorial(
            chart.planets[body].longitude,
            chart.planets[body].latitude,
            chart.obliquity,
        )[1]
        for body in ASTRODYNE_PLANETS
    }
    declinations["M.C."] = ecliptic_to_equatorial(
        houses.mc, 0.0, chart.obliquity
    )[1]
    declinations["Asc."] = ecliptic_to_equatorial(
        houses.asc, 0.0, chart.obliquity
    )[1]

    result = engine.astrodynes_from_geometry(
        planet_longitudes,
        declinations,
        houses.cusps,
        houses.mc,
        houses.asc,
    )
    return AstrodynesCalculationTruth(
        result=result,
        source_mode="chart_backed",
        dt=request.dt,
        observer_lat=request.observer_lat,
        observer_lon=request.observer_lon,
        jd_ut=utc_to_ut1(chart.jd_ut),
        obliquity_deg=chart.obliquity,
        planet_longitudes={
            item.body: item.longitude_deg
            for item in result.inputs
            if item.body in ASTRODYNE_PLANETS
        },
        declinations={
            item.body: item.declination_deg
            for item in result.inputs
            if item.declination_deg is not None
        },
        cusp_longitudes=tuple(houses.cusps),
        mc_longitude=houses.mc,
        asc_longitude=houses.asc,
        requested_house_system=houses.system,
        effective_house_system=houses.effective_system,
        house_fallback=houses.fallback,
        house_fallback_reason=houses.fallback_reason,
        engine_entrypoint="Moira.astrodynes_from_geometry",
        planetary_frame="geocentric_apparent",
        kernel_required=True,
    )


__all__ = [
    "AstrodynesCalculationTruth",
    "AstrodynesDoctrineTruth",
    "compute_astrodynes_chart",
    "compute_astrodynes_geometry",
    "get_astrodynes_doctrine",
]
