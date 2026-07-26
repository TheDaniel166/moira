"""Service helpers for Phase-9 Classical Lots routes (P9-05)."""

from __future__ import annotations

from dataclasses import dataclass

from moira import Moira
from moira.lots import (
    ArabicPart,
    ArabicPartsService,
    LotChartConditionProfile,
    LotConditionNetworkProfile,
    LotConditionProfile,
    LotDependency,
    LotsComputationPolicy,
    LotsDerivedReferencePolicy,
    LotsEvaluation,
    LotsExternalReferencePolicy,
    PARTS_DEFINITIONS,
    PartDefinition,
)

from ..models.lots import (
    LotsChartRequest,
    LotsComputationPolicyRequest,
    LotsConditionChartRequest,
)
from ._shared import require_aware_datetime


_LOT_BODIES: tuple[str, ...] = (
    "Sun",
    "Moon",
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
    "Uranus",
    "Neptune",
    "Pluto",
)


@dataclass(frozen=True, slots=True)
class _LotsSupportTruth:
    planet_longitudes: dict[str, float]
    house_cusps: dict[int, float]
    asc_longitude: float
    mc_longitude: float
    is_day_chart: bool
    policy: LotsComputationPolicy | None


_SERVICE = ArabicPartsService()


def _policy_from_request(
    request_policy: LotsComputationPolicyRequest | None,
) -> LotsComputationPolicy | None:
    if request_policy is None:
        return None
    return LotsComputationPolicy(
        unresolved_reference_mode=request_policy.unresolved_reference_mode,
        derived=LotsDerivedReferencePolicy(
            include_fortune=request_policy.derived.include_fortune,
            include_spirit=request_policy.derived.include_spirit,
            include_eros_valens=request_policy.derived.include_eros_valens,
        ),
        external=LotsExternalReferencePolicy(
            include_syzygy=request_policy.external.include_syzygy,
            include_prenatal_new_moon=request_policy.external.include_prenatal_new_moon,
            include_prenatal_full_moon=request_policy.external.include_prenatal_full_moon,
            include_lord_of_hour=request_policy.external.include_lord_of_hour,
        ),
    )


def _derive_lots_support_truth(
    engine: Moira,
    request: LotsChartRequest,
) -> _LotsSupportTruth:
    require_aware_datetime(request.dt)

    chart = engine.chart(
        request.dt,
        bodies=list(_LOT_BODIES),
        include_nodes=True,
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

    planet_longitudes = {
        name: position.longitude
        for name, position in chart.planets.items()
    }
    planet_longitudes.update(
        {
            name: position.longitude
            for name, position in chart.nodes.items()
        }
    )
    house_cusps = {
        index + 1: cusp
        for index, cusp in enumerate(houses.cusps)
    }
    return _LotsSupportTruth(
        planet_longitudes=planet_longitudes,
        house_cusps=house_cusps,
        asc_longitude=houses.asc,
        mc_longitude=houses.mc,
        is_day_chart=_SERVICE.is_day_chart(planet_longitudes["Sun"], houses.asc),
        policy=_policy_from_request(request.policy),
    )


def list_lot_catalog() -> list[PartDefinition]:
    return list(PARTS_DEFINITIONS)


def compute_lots_chart(
    engine: Moira,
    request: LotsChartRequest,
) -> list[ArabicPart]:
    support = _derive_lots_support_truth(engine, request)
    return _SERVICE.calculate_parts(
        support.planet_longitudes,
        support.house_cusps,
        support.is_day_chart,
        policy=support.policy,
        asc_longitude=support.asc_longitude,
        mc_longitude=support.mc_longitude,
        syzygy=request.syzygy,
        prenatal_new_moon=request.prenatal_new_moon,
        prenatal_full_moon=request.prenatal_full_moon,
        lord_of_hour=request.lord_of_hour,
    )


def compute_lots_chart_evaluation(
    engine: Moira,
    request: LotsChartRequest,
) -> LotsEvaluation:
    """Evaluate the whole lot catalog and retain typed unresolved receipts."""

    support = _derive_lots_support_truth(engine, request)
    return _SERVICE.evaluate_parts(
        support.planet_longitudes,
        support.house_cusps,
        support.is_day_chart,
        policy=support.policy,
        asc_longitude=support.asc_longitude,
        mc_longitude=support.mc_longitude,
        syzygy=request.syzygy,
        prenatal_new_moon=request.prenatal_new_moon,
        prenatal_full_moon=request.prenatal_full_moon,
        lord_of_hour=request.lord_of_hour,
    )


def compute_lots_chart_dependencies(
    engine: Moira,
    request: LotsChartRequest,
) -> list[LotDependency]:
    support = _derive_lots_support_truth(engine, request)
    return _SERVICE.calculate_dependencies(
        support.planet_longitudes,
        support.house_cusps,
        support.is_day_chart,
        policy=support.policy,
        asc_longitude=support.asc_longitude,
        mc_longitude=support.mc_longitude,
        syzygy=request.syzygy,
        prenatal_new_moon=request.prenatal_new_moon,
        prenatal_full_moon=request.prenatal_full_moon,
        lord_of_hour=request.lord_of_hour,
    )


def compute_lots_chart_conditions(
    engine: Moira,
    request: LotsChartRequest,
) -> list[LotConditionProfile]:
    support = _derive_lots_support_truth(engine, request)
    return _SERVICE.calculate_condition_profiles(
        support.planet_longitudes,
        support.house_cusps,
        support.is_day_chart,
        policy=support.policy,
        asc_longitude=support.asc_longitude,
        mc_longitude=support.mc_longitude,
        syzygy=request.syzygy,
        prenatal_new_moon=request.prenatal_new_moon,
        prenatal_full_moon=request.prenatal_full_moon,
        lord_of_hour=request.lord_of_hour,
    )


def compute_lots_chart_condition(
    engine: Moira,
    request: LotsConditionChartRequest,
) -> LotConditionProfile:
    profiles = compute_lots_chart_conditions(engine, request)
    for profile in profiles:
        if profile.part_name == request.part_name:
            return profile
    raise ValueError(f"part_name {request.part_name!r} not found in lot condition profiles")


def compute_lots_chart_profile(
    engine: Moira,
    request: LotsChartRequest,
) -> LotChartConditionProfile:
    support = _derive_lots_support_truth(engine, request)
    return _SERVICE.calculate_chart_condition_profile(
        support.planet_longitudes,
        support.house_cusps,
        support.is_day_chart,
        policy=support.policy,
        asc_longitude=support.asc_longitude,
        mc_longitude=support.mc_longitude,
        syzygy=request.syzygy,
        prenatal_new_moon=request.prenatal_new_moon,
        prenatal_full_moon=request.prenatal_full_moon,
        lord_of_hour=request.lord_of_hour,
    )


def compute_lots_chart_network(
    engine: Moira,
    request: LotsChartRequest,
) -> LotConditionNetworkProfile:
    support = _derive_lots_support_truth(engine, request)
    return _SERVICE.calculate_condition_network_profile(
        support.planet_longitudes,
        support.house_cusps,
        support.is_day_chart,
        policy=support.policy,
        asc_longitude=support.asc_longitude,
        mc_longitude=support.mc_longitude,
        syzygy=request.syzygy,
        prenatal_new_moon=request.prenatal_new_moon,
        prenatal_full_moon=request.prenatal_full_moon,
        lord_of_hour=request.lord_of_hour,
    )


__all__ = [
    "compute_lots_chart",
    "compute_lots_chart_evaluation",
    "compute_lots_chart_condition",
    "compute_lots_chart_conditions",
    "compute_lots_chart_dependencies",
    "compute_lots_chart_network",
    "compute_lots_chart_profile",
    "list_lot_catalog",
]
