"""Service helpers for Phase-9 Classical Dignities routes (P9-04)."""

from __future__ import annotations

from dataclasses import dataclass

from moira import Moira
from moira.dignities import DignitiesService
from moira.dignities_types import (
    AccidentalDignityPolicy,
    ChartConditionProfile,
    ConditionNetworkProfile,
    DignityComputationPolicy,
    EssentialDignityDoctrine,
    EssentialDignityPolicy,
    MutualReceptionPolicy,
    PlanetaryConditionProfile,
    PlanetaryDignity,
    PlanetaryReception,
    SectHayzPolicy,
    SolarConditionPolicy,
)

from ..models.dignities import (
    DignitiesChartRequest,
    DignitiesConditionChartRequest,
    DignityComputationPolicyRequest,
)
from ._shared import require_aware_datetime


_SEVEN_PLANETS: tuple[str, ...] = (
    "Sun",
    "Moon",
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
)
_MODERN_DIGNITY_PLANETS: tuple[str, ...] = (
    *_SEVEN_PLANETS,
    "Uranus",
    "Neptune",
    "Pluto",
)


@dataclass(frozen=True, slots=True)
class _DignitySupportTruth:
    planet_positions: list[dict]
    house_positions: list[dict]
    policy: DignityComputationPolicy | None


_SERVICE = DignitiesService()


def _bodies_for_policy(policy: DignityComputationPolicy | None) -> tuple[str, ...]:
    if policy is not None and policy.essential.doctrine is EssentialDignityDoctrine.MODERN_CO_RULERS:
        return _MODERN_DIGNITY_PLANETS
    return _SEVEN_PLANETS


def _policy_from_request(
    request_policy: DignityComputationPolicyRequest | None,
) -> DignityComputationPolicy | None:
    if request_policy is None:
        return None
    essential = EssentialDignityPolicy(
        doctrine=request_policy.essential.doctrine,
    )
    accidental = AccidentalDignityPolicy(
        include_house_strength=request_policy.accidental.include_house_strength,
        include_motion=request_policy.accidental.include_motion,
        solar=SolarConditionPolicy(
            include_cazimi=request_policy.accidental.solar.include_cazimi,
            include_combust=request_policy.accidental.solar.include_combust,
            include_under_sunbeams=request_policy.accidental.solar.include_under_sunbeams,
            include_for_luminaries=request_policy.accidental.solar.include_for_luminaries,
        ),
        mutual_reception=MutualReceptionPolicy(
            include_domicile=request_policy.accidental.mutual_reception.include_domicile,
            include_exaltation=request_policy.accidental.mutual_reception.include_exaltation,
        ),
        sect=SectHayzPolicy(
            mercury_sect_model=request_policy.accidental.sect.mercury_sect_model,
            include_hayz=request_policy.accidental.sect.include_hayz,
        ),
        include_timelord_distributions=request_policy.accidental.include_timelord_distributions,
    )
    return DignityComputationPolicy(essential=essential, accidental=accidental)


def _derive_dignity_support_truth(
    engine: Moira,
    request: DignitiesChartRequest,
) -> _DignitySupportTruth:
    require_aware_datetime(request.dt)
    policy = _policy_from_request(request.policy)
    bodies = _bodies_for_policy(policy)

    chart = engine.chart(
        request.dt,
        bodies=list(bodies),
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

    planet_positions = [
        {
            "name": planet,
            "degree": chart.planets[planet].longitude,
            "is_retrograde": chart.planets[planet].speed < 0.0,
        }
        for planet in bodies
    ]
    house_positions = [
        {
            "number": index + 1,
            "degree": cusp,
        }
        for index, cusp in enumerate(houses.cusps)
    ]
    return _DignitySupportTruth(
        planet_positions=planet_positions,
        house_positions=house_positions,
        policy=policy,
    )


def compute_dignities_chart(
    engine: Moira,
    request: DignitiesChartRequest,
) -> list[PlanetaryDignity]:
    support = _derive_dignity_support_truth(engine, request)
    return _SERVICE.calculate_dignities(
        support.planet_positions,
        support.house_positions,
        policy=support.policy,
    )


def compute_dignities_chart_receptions(
    engine: Moira,
    request: DignitiesChartRequest,
) -> list[PlanetaryReception]:
    support = _derive_dignity_support_truth(engine, request)
    return _SERVICE.calculate_receptions(
        support.planet_positions,
        policy=support.policy,
    )


def compute_dignities_chart_conditions(
    engine: Moira,
    request: DignitiesChartRequest,
) -> list[PlanetaryConditionProfile]:
    support = _derive_dignity_support_truth(engine, request)
    return _SERVICE.calculate_condition_profiles(
        support.planet_positions,
        support.house_positions,
        policy=support.policy,
    )


def compute_dignities_chart_condition(
    engine: Moira,
    request: DignitiesConditionChartRequest,
) -> PlanetaryConditionProfile:
    profiles = compute_dignities_chart_conditions(engine, request)
    for profile in profiles:
        if profile.planet == request.planet:
            return profile
    raise ValueError(f"planet {request.planet!r} not found in dignity condition profiles")


def compute_dignities_chart_profile(
    engine: Moira,
    request: DignitiesChartRequest,
) -> ChartConditionProfile:
    support = _derive_dignity_support_truth(engine, request)
    return _SERVICE.calculate_chart_condition_profile(
        support.planet_positions,
        support.house_positions,
        policy=support.policy,
    )


def compute_dignities_chart_network(
    engine: Moira,
    request: DignitiesChartRequest,
) -> ConditionNetworkProfile:
    support = _derive_dignity_support_truth(engine, request)
    return _SERVICE.calculate_condition_network_profile(
        support.planet_positions,
        support.house_positions,
        policy=support.policy,
    )


__all__ = [
    "compute_dignities_chart",
    "compute_dignities_chart_condition",
    "compute_dignities_chart_conditions",
    "compute_dignities_chart_network",
    "compute_dignities_chart_profile",
    "compute_dignities_chart_receptions",
]
