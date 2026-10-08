"""Service helpers for Phase-9 Shadbala routes (P9-02)."""

from __future__ import annotations

from dataclasses import dataclass

from moira import Moira
from moira.dignities import is_day_chart
from moira.julian import utc_to_ut1
from moira.panchanga import _panchanga_from_utc
from moira.shadbala import (
    BhavaBalaResult,
    GrahaYuddha,
    ShadbalaChartProfile,
    ShadbalaConditionProfile,
    ShadbalaNetworkProfile,
    ShadbalaResult,
    bhava_bala,
    graha_yuddha_pairs,
    shadbala_chart_profile,
    shadbala_condition_profile,
    shadbala_network_profile,
    validate_shadbala_output,
)
from moira.sidereal import tropical_to_sidereal

from ..models.shadbala import (
    ShadbalaAppliedPolicyResponse, ShadbalaChartRequest, ShadbalaConditionChartRequest,
    ShadbalaResultResponse, ShadbalaChartProfileResponse, ShadbalaNetworkProfileResponse,
    ShadbalaConditionProfileResponse, BhavaBalaResultResponse, ShadbalaFullResponse,
)
from ..models._vedic_inputs import resolve_vedic_house_system
from ..serializers.shadbala import (
    serialize_bhava_bala_result, serialize_shadbala_chart_profile,
    serialize_shadbala_condition_profile, serialize_shadbala_full,
    serialize_shadbala_network_profile, serialize_shadbala_result,
)
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
    sidereal_longitudes: dict[str, float]
    houses: object
    policy_receipt: ShadbalaAppliedPolicyResponse


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
    house_system = resolve_vedic_house_system(request.house_system)

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
        system=house_system,
    )
    jd_utc = chart.jd_ut
    jd_ut = utc_to_ut1(jd_utc)

    tropical_longitudes = chart.longitudes(include_nodes=False)
    sidereal_longitudes = {
        planet: tropical_to_sidereal(
            tropical_longitudes[planet],
            jd_ut,
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

    panchanga_support = _panchanga_from_utc(
        tropical_longitudes["Sun"],
        tropical_longitudes["Moon"],
        jd_utc,
        ayanamsa_system=ayanamsa_system,
        policy=None,
    )
    tithi_number = panchanga_support.tithi.number
    vara_lord = panchanga_support.vara_lord
    day_chart = is_day_chart(tropical_longitudes["Sun"], houses.asc)
    hora_lord = request.hora_lord

    result = engine.shadbala(
        sidereal_longitudes=sidereal_longitudes,
        planet_speeds=planet_speeds,
        houses=houses,
        jd=jd_ut,
        tithi_number=tithi_number,
        vara_lord=vara_lord,
        is_day=day_chart,
        ayanamsa_system=ayanamsa_system,
        hora_lord=hora_lord,
        planet_latitudes=planet_latitudes,
    )
    validate_shadbala_output(result)

    wars = graha_yuddha_pairs(sidereal_longitudes, planet_latitudes, planet_speeds)
    return _ShadbalaSupportTruth(
        result=result,
        wars=wars,
        sidereal_longitudes=sidereal_longitudes,
        houses=houses,
        policy_receipt=ShadbalaAppliedPolicyResponse(
            requested_ayanamsa_system=request.ayanamsa_system,
            policy_ayanamsa_system=(request.policy.ayanamsa_system if request.policy else None),
            applied_ayanamsa_system=ayanamsa_system,
            ayanamsa_precedence="policy" if request.policy else "request",
            requested_house_system=request.house_system,
            resolved_house_system=house_system,
            effective_house_system=houses.effective_system,
            polar_fallback_applied=houses.effective_system != house_system,
            hora_lord=request.hora_lord,
        ),
    )


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


def compute_bhava_bala_chart(
    engine: Moira,
    request: ShadbalaChartRequest,
) -> BhavaBalaResult:
    support = _derive_shadbala_support_truth(engine, request)
    return bhava_bala(support.result, support.sidereal_longitudes, support.houses)


@dataclass(frozen=True, slots=True)
class ShadbalaFullTruth:
    """All four Shadbala surfaces from one support-truth derivation."""

    result: ShadbalaResult
    profile: ShadbalaChartProfile
    network: ShadbalaNetworkProfile
    bhava: BhavaBalaResult


def compute_shadbala_full(
    engine: Moira,
    request: ShadbalaChartRequest,
) -> ShadbalaFullTruth:
    """Derive support truth once; build chart, profile, network, and bhava
    from that single derivation so all four surfaces agree exactly."""
    support = _derive_shadbala_support_truth(engine, request)
    return ShadbalaFullTruth(
        result=support.result,
        profile=shadbala_chart_profile(support.result),
        network=shadbala_network_profile(support.result, support.wars),
        bhava=bhava_bala(support.result, support.sidereal_longitudes, support.houses),
    )


def build_shadbala_chart_response(engine: Moira, request: ShadbalaChartRequest) -> ShadbalaResultResponse:
    support = _derive_shadbala_support_truth(engine, request)
    return serialize_shadbala_result(support.result, policy_receipt=support.policy_receipt)


def build_shadbala_profile_response(engine: Moira, request: ShadbalaChartRequest) -> ShadbalaChartProfileResponse:
    support = _derive_shadbala_support_truth(engine, request)
    return serialize_shadbala_chart_profile(
        shadbala_chart_profile(support.result), policy_receipt=support.policy_receipt,
    )


def build_shadbala_network_response(engine: Moira, request: ShadbalaChartRequest) -> ShadbalaNetworkProfileResponse:
    support = _derive_shadbala_support_truth(engine, request)
    return serialize_shadbala_network_profile(
        shadbala_network_profile(support.result, support.wars), policy_receipt=support.policy_receipt,
    )


def build_shadbala_condition_response(engine: Moira, request: ShadbalaConditionChartRequest) -> ShadbalaConditionProfileResponse:
    support = _derive_shadbala_support_truth(engine, request)
    return serialize_shadbala_condition_profile(
        shadbala_condition_profile(support.result.planets[request.planet]), policy_receipt=support.policy_receipt,
    )


def build_shadbala_bhava_response(engine: Moira, request: ShadbalaChartRequest) -> BhavaBalaResultResponse:
    support = _derive_shadbala_support_truth(engine, request)
    return serialize_bhava_bala_result(
        bhava_bala(support.result, support.sidereal_longitudes, support.houses), policy_receipt=support.policy_receipt,
    )


def build_shadbala_full_response(engine: Moira, request: ShadbalaChartRequest) -> ShadbalaFullResponse:
    support = _derive_shadbala_support_truth(engine, request)
    return serialize_shadbala_full(
        support.result, shadbala_chart_profile(support.result),
        shadbala_network_profile(support.result, support.wars),
        bhava_bala(support.result, support.sidereal_longitudes, support.houses),
        policy_receipt=support.policy_receipt,
    )


__all__ = [
    "build_shadbala_chart_response", "build_shadbala_profile_response",
    "build_shadbala_network_response", "build_shadbala_condition_response",
    "build_shadbala_bhava_response", "build_shadbala_full_response",
    "ShadbalaFullTruth",
    "compute_bhava_bala_chart",
    "compute_shadbala_chart",
    "compute_shadbala_chart_condition",
    "compute_shadbala_chart_network",
    "compute_shadbala_chart_profile",
    "compute_shadbala_full",
]
