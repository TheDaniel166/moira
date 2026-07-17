"""Service helpers for Phase-9 Jaimini routes (P9-03)."""

from __future__ import annotations

from moira import Body, Moira
from moira.jaimini import (
    JaiminiChartProfile,
    JaiminiKarakaResult,
    JaiminiPolicy,
    KarakaConditionProfile,
    KarakaPair,
    jaimini_chart_profile,
    jaimini_karakas,
    karaka_condition_profile,
    karaka_pair,
    validate_jaimini_output,
)
from moira.julian import utc_to_ut1
from moira.sidereal import tropical_to_sidereal

from ..models.jaimini import (
    JaiminiChartRequest,
    JaiminiConditionChartRequest,
    JaiminiConditionDirectRequest,
    JaiminiDirectRequest,
    JaiminiPairChartRequest,
    JaiminiPairDirectRequest,
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


def _policy_from_request(request: JaiminiDirectRequest | JaiminiChartRequest) -> JaiminiPolicy | None:
    if request.policy is None:
        return None
    return JaiminiPolicy(
        scheme=request.policy.scheme,
        ayanamsa_system=request.policy.ayanamsa_system,
    )


def _scheme_from_request(request: JaiminiDirectRequest | JaiminiChartRequest) -> int:
    if request.policy is not None:
        return request.policy.scheme
    return request.scheme


def _ayanamsa_from_request(request: JaiminiChartRequest) -> str:
    if request.policy is not None:
        return request.policy.ayanamsa_system
    return request.ayanamsa_system


def _select_assignment(result: JaiminiKarakaResult, *, karaka_name: str | None, planet: str | None):
    if karaka_name is not None:
        assignment = result.by_karaka(karaka_name)
        if assignment is None:
            raise ValueError(f"karaka_name {karaka_name!r} not found in result")
        return assignment
    if planet is not None:
        assignment = result.by_planet(planet)
        if assignment is None:
            raise ValueError(f"planet {planet!r} not found in result")
        return assignment
    raise ValueError("provide exactly one of karaka_name or planet")


def compute_jaimini_direct(request: JaiminiDirectRequest) -> JaiminiKarakaResult:
    result = jaimini_karakas(
        request.sidereal_longitudes,
        scheme=request.scheme,
        policy=_policy_from_request(request),
    )
    validate_jaimini_output(result)
    return result


def compute_jaimini_direct_profile(
    request: JaiminiDirectRequest,
) -> JaiminiChartProfile:
    return jaimini_chart_profile(compute_jaimini_direct(request))


def compute_jaimini_direct_condition(
    request: JaiminiConditionDirectRequest,
) -> KarakaConditionProfile:
    result = compute_jaimini_direct(request)
    assignment = _select_assignment(
        result,
        karaka_name=request.karaka_name,
        planet=request.planet,
    )
    return karaka_condition_profile(assignment, result.scheme)


def compute_jaimini_direct_pair(
    request: JaiminiPairDirectRequest,
) -> KarakaPair:
    return karaka_pair(compute_jaimini_direct(request), request.role_a, request.role_b)


def compute_jaimini_chart(
    engine: Moira,
    request: JaiminiChartRequest,
) -> JaiminiKarakaResult:
    require_aware_datetime(request.dt)

    scheme = _scheme_from_request(request)
    ayanamsa_system = _ayanamsa_from_request(request)
    include_nodes = scheme == 8

    chart = engine.chart(
        request.dt,
        bodies=list(_SEVEN_PLANETS),
        include_nodes=include_nodes,
    )
    jd_ut = utc_to_ut1(chart.jd_ut)
    tropical_longitudes = chart.longitudes(include_nodes=False)
    sidereal_longitudes = {
        planet: tropical_to_sidereal(
            tropical_longitudes[planet],
            jd_ut,
            system=ayanamsa_system,
        )
        for planet in _SEVEN_PLANETS
    }
    if scheme == 8:
        true_node = chart.nodes[Body.TRUE_NODE]
        rahu_tropical_longitude = true_node.longitude
        sidereal_longitudes["Rahu"] = tropical_to_sidereal(
            rahu_tropical_longitude,
            jd_ut,
            system=ayanamsa_system,
        )

    result = jaimini_karakas(
        sidereal_longitudes,
        scheme=request.scheme,
        policy=_policy_from_request(request),
    )
    validate_jaimini_output(result)
    return result


def compute_jaimini_chart_profile(
    engine: Moira,
    request: JaiminiChartRequest,
) -> JaiminiChartProfile:
    return jaimini_chart_profile(compute_jaimini_chart(engine, request))


def compute_jaimini_chart_condition(
    engine: Moira,
    request: JaiminiConditionChartRequest,
) -> KarakaConditionProfile:
    result = compute_jaimini_chart(engine, request)
    assignment = _select_assignment(
        result,
        karaka_name=request.karaka_name,
        planet=request.planet,
    )
    return karaka_condition_profile(assignment, result.scheme)


def compute_jaimini_chart_pair(
    engine: Moira,
    request: JaiminiPairChartRequest,
) -> KarakaPair:
    return karaka_pair(compute_jaimini_chart(engine, request), request.role_a, request.role_b)


__all__ = [
    "compute_jaimini_chart",
    "compute_jaimini_chart_condition",
    "compute_jaimini_chart_pair",
    "compute_jaimini_chart_profile",
    "compute_jaimini_direct",
    "compute_jaimini_direct_condition",
    "compute_jaimini_direct_pair",
    "compute_jaimini_direct_profile",
]
