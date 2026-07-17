"""Request-scoped sidereal chart derivation service."""

from __future__ import annotations

import math
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from moira import Moira
from moira.julian import jd_from_datetime, utc_to_ut1
from moira.sidereal import ayanamsa

from ..models.chart import HousesRequest
from ..models.sidereal_context import SiderealChartBaseRequest
from ._shared import (
    build_chart_context,
    build_houses_context,
    require_supported_chart_bodies,
)


SIDEREAL_CONTEXT_STAGE_SEQUENCE: tuple[str, ...] = (
    "datetime_validation",
    "chart_body_validation",
    "tropical_chart_derivation",
    "ayanamsa_resolution",
    "tropical_to_sidereal_reduction",
    "optional_house_derivation",
    "optional_lagna_reduction",
    "context_materialization",
)


@dataclass(frozen=True, slots=True)
class SiderealChartRequirements:
    required_bodies: tuple[str, ...]
    include_nodes: bool = False
    require_houses: bool = False
    require_lagna: bool = False
    require_speeds: bool = False
    observer_required: bool = False

    def __post_init__(self) -> None:
        if not self.required_bodies:
            raise ValueError("required_bodies must be non-empty")
        if any(not body for body in self.required_bodies):
            raise ValueError("required_bodies entries must be non-empty")
        require_supported_chart_bodies(list(self.required_bodies))
        if self.require_houses or self.require_lagna:
            object.__setattr__(self, "observer_required", True)


@dataclass(frozen=True, slots=True)
class SiderealObserverContext:
    latitude: float
    longitude: float
    elevation_m: float


@dataclass(frozen=True, slots=True)
class SiderealHouseContext:
    system: str
    effective_system: str
    ascendant: float
    midheaven: float
    cusps: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class SiderealChartContext:
    requested_datetime: str
    normalized_datetime_utc: str
    jd_ut: float
    ayanamsa_system: str
    ayanamsa_offset: float
    requested_bodies: tuple[str, ...]
    returned_bodies: tuple[str, ...]
    tropical_longitudes: Mapping[str, float]
    sidereal_longitudes: Mapping[str, float]
    sidereal_sign_indices: Mapping[str, int]
    speeds: Mapping[str, float] | None
    observer: SiderealObserverContext | None
    houses: SiderealHouseContext | None
    tropical_lagna: float | None
    sidereal_lagna: float | None
    sidereal_lagna_sign_index: int | None
    stage_sequence: tuple[str, ...]


def derive_sidereal_chart_context(
    engine: Moira,
    request: SiderealChartBaseRequest,
    requirements: SiderealChartRequirements,
) -> SiderealChartContext:
    _validate_observer_requirements(request, requirements)
    bodies = _merge_bodies(requirements.required_bodies, request.bodies)
    require_supported_chart_bodies(list(bodies))

    chart_request = request.model_copy(
        update={
            "bodies": list(bodies),
            "include_nodes": request.include_nodes or requirements.include_nodes,
        }
    )
    chart = build_chart_context(engine, chart_request)
    jd_utc = getattr(chart, "jd_ut", None)
    if jd_utc is None:
        jd_utc = jd_from_datetime(request.dt)
    jd_ut = utc_to_ut1(jd_utc)
    ayanamsa_offset = ayanamsa(jd_ut, request.ayanamsa_system)

    tropical_longitudes = {
        name: planet.longitude
        for name, planet in chart.planets.items()
    }
    speeds: dict[str, float] | None = None
    if requirements.require_speeds:
        speeds = {
            name: planet.speed
            for name, planet in chart.planets.items()
        }

    if request.include_nodes or requirements.include_nodes:
        for name, node in chart.nodes.items():
            tropical_longitudes[name] = node.longitude
        if speeds is not None:
            for name, node in chart.nodes.items():
                speeds[name] = node.speed

    sidereal_longitudes = {
        name: (longitude - ayanamsa_offset) % 360.0
        for name, longitude in tropical_longitudes.items()
    }
    sidereal_sign_indices = {
        name: int(longitude % 360.0 // 30.0)
        for name, longitude in sidereal_longitudes.items()
    }

    observer = _observer_context(request)
    houses = None
    tropical_lagna = None
    sidereal_lagna = None
    sidereal_lagna_sign_index = None
    if requirements.require_houses or requirements.require_lagna:
        house_request = HousesRequest(
            dt=request.dt,
            latitude=request.observer_lat,
            longitude=request.observer_lon,
            system=request.house_system,
        )
        house_vessel = build_houses_context(engine, house_request)
        tropical_lagna = house_vessel.asc
        sidereal_lagna = (tropical_lagna - ayanamsa_offset) % 360.0
        sidereal_lagna_sign_index = int(sidereal_lagna // 30.0)
        houses = SiderealHouseContext(
            system=house_vessel.system,
            effective_system=house_vessel.effective_system,
            ascendant=house_vessel.asc,
            midheaven=house_vessel.mc,
            cusps=tuple(house_vessel.cusps),
        )

    return SiderealChartContext(
        requested_datetime=request.dt.isoformat(),
        normalized_datetime_utc=chart.datetime_utc.isoformat(),
        jd_ut=jd_ut,
        ayanamsa_system=request.ayanamsa_system,
        ayanamsa_offset=ayanamsa_offset,
        requested_bodies=tuple(bodies),
        returned_bodies=tuple(tropical_longitudes),
        tropical_longitudes=_frozen_float_map(tropical_longitudes),
        sidereal_longitudes=_frozen_float_map(sidereal_longitudes),
        sidereal_sign_indices=MappingProxyType(dict(sidereal_sign_indices)),
        speeds=(_frozen_float_map(speeds) if speeds is not None else None),
        observer=observer,
        houses=houses,
        tropical_lagna=tropical_lagna,
        sidereal_lagna=sidereal_lagna,
        sidereal_lagna_sign_index=sidereal_lagna_sign_index,
        stage_sequence=SIDEREAL_CONTEXT_STAGE_SEQUENCE,
    )


def _merge_bodies(required_bodies: tuple[str, ...], requested: list[str] | None) -> tuple[str, ...]:
    merged: list[str] = []
    for body in (*required_bodies, *(requested or ())):
        if body not in merged:
            merged.append(body)
    return tuple(merged)


def _validate_observer_requirements(
    request: SiderealChartBaseRequest,
    requirements: SiderealChartRequirements,
) -> None:
    if requirements.observer_required and (
        request.observer_lat is None or request.observer_lon is None
    ):
        raise ValueError("observer latitude and longitude are required")
    for value in (request.observer_lat, request.observer_lon, request.observer_elev_m):
        if value is not None and not math.isfinite(value):
            raise ValueError("observer values must be finite")


def _observer_context(request: SiderealChartBaseRequest) -> SiderealObserverContext | None:
    if request.observer_lat is None or request.observer_lon is None:
        return None
    return SiderealObserverContext(
        latitude=request.observer_lat,
        longitude=request.observer_lon,
        elevation_m=request.observer_elev_m,
    )


def _frozen_float_map(value: Mapping[str, float]) -> Mapping[str, float]:
    return MappingProxyType(dict(value))


__all__ = [
    "SIDEREAL_CONTEXT_STAGE_SEQUENCE",
    "SiderealChartContext",
    "SiderealChartRequirements",
    "SiderealHouseContext",
    "SiderealObserverContext",
    "derive_sidereal_chart_context",
]
