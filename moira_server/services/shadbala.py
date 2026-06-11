"""Service helpers for Phase-9 Shadbala routes (P9-02)."""

from __future__ import annotations

from dataclasses import dataclass

from moira import Moira
from moira.dignities import is_day_chart
from moira.panchanga import panchanga_at
from moira.shadbala import (
    GrahaYuddha,
    ShadbalaChartProfile,
    ShadbalaConditionProfile,
    ShadbalaNetworkProfile,
    ShadbalaResult,
    graha_yuddha_pairs,
    shadbala,
    shadbala_chart_profile,
    shadbala_condition_profile,
    shadbala_network_profile,
    validate_shadbala_output,
)
from moira.sidereal import tropical_to_sidereal

from ..models.shadbala import ShadbalaChartRequest, ShadbalaConditionChartRequest
from ._shared import require_aware_datetime


_SEVEN_PLANETS: tuple[str, ...] = (
    "Sun",
    "Moon",
    "Mars",
    "Mercury",
    "Jupiter",
    "Venus",
    "Saturn",
)


@dataclass(frozen=True, slots=True)
class _ShadbalaSupportTruth:
    result: ShadbalaResult
    wars: tuple[GrahaYuddha, ...]


def _ayanamsa_from_request(request: ShadbalaChartRequest) -> str:
    if request.policy is not None:
        return request.policy.ayanamsa_system
    return request.ayanamsa_system


def _derive_shadbala_support_truth(
    engine: Moira,
    request: ShadbalaChartRequest,
) -> _ShadbalaSupportTruth:
    require_aware_datetime(request.dt)

    ayanamsa_system = _ayanamsa_from_request(request)

    chart = engine.chart(
        request.dt,
        bodies=list(_SEVEN_PLANETS),
        include_nodes=False,
        observer_lat=request.observer_lat,
        observer_lon=request.observer_lon,
        observer_elev_m=request.observer_elev_m,
    )
    houses = engine.houses(
        request.dt,
        latitude=request.observer_lat,
        longitude=request.observer_lon,
        system=request.house_system,
    )

    tropical_longitudes = chart.longitudes(include_nodes=False)
    sidereal_longitudes = {
        planet: tropical_to_sidereal(
            tropical_longitudes[planet],
            chart.jd_ut,
            system=ayanamsa_system,
        )
        for planet in _SEVEN_PLANETS
    }
    planet_speeds = {
        planet: chart.planets[planet].speed
        for planet in _SEVEN_PLANETS
    }
    planet_latitudes = {
        planet: chart.planets[planet].latitude
        for planet in _SEVEN_PLANETS
    }

    panchanga_support = panchanga_at(
        tropical_longitudes["Sun"],
        tropical_longitudes["Moon"],
        chart.jd_ut,
        ayanamsa_system=ayanamsa_system,
    )
    tithi_number = panchanga_support.tithi.number
    vara_lord = panchanga_support.vara_lord
    day_chart = is_day_chart(tropical_longitudes["Sun"], houses.asc)
    hora_lord = request.hora_lord

    result = shadbala(
        sidereal_longitudes=sidereal_longitudes,
        planet_speeds=planet_speeds,
        houses=houses,
        jd=chart.jd_ut,
        tithi_number=tithi_number,
        vara_lord=vara_lord,
        is_day=day_chart,
        ayanamsa_system=ayanamsa_system,
        hora_lord=hora_lord,
        planet_latitudes=planet_latitudes,
    )
    validate_shadbala_output(result)

    wars = graha_yuddha_pairs(sidereal_longitudes, planet_latitudes)
    return _ShadbalaSupportTruth(result=result, wars=wars)


def compute_shadbala_chart(
    engine: Moira,
    request: ShadbalaChartRequest,
) -> ShadbalaResult:
    return _derive_shadbala_support_truth(engine, request).result


def compute_shadbala_chart_profile(
    engine: Moira,
    request: ShadbalaChartRequest,
) -> ShadbalaChartProfile:
    return shadbala_chart_profile(_derive_shadbala_support_truth(engine, request).result)


def compute_shadbala_chart_network(
    engine: Moira,
    request: ShadbalaChartRequest,
) -> ShadbalaNetworkProfile:
    support = _derive_shadbala_support_truth(engine, request)
    return shadbala_network_profile(support.result, support.wars)


def compute_shadbala_chart_condition(
    engine: Moira,
    request: ShadbalaConditionChartRequest,
) -> ShadbalaConditionProfile:
    result = _derive_shadbala_support_truth(engine, request).result
    return shadbala_condition_profile(result.planets[request.planet])


__all__ = [
    "compute_shadbala_chart",
    "compute_shadbala_chart_condition",
    "compute_shadbala_chart_network",
    "compute_shadbala_chart_profile",
]
