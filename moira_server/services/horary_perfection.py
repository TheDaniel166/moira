"""Transport-to-engine adapter for Lilly P4 perfection routes."""

from __future__ import annotations

from moira import Moira
from moira.horary_moon import LillyP3State
from moira.horary_perfection_routes import (
    LILLY_BOOK_II_PRACTICE,
    LillyBeholdingReading,
    LillyCollectionReading,
    LillyConditionEpoch,
    LillyDwellingReading,
    LillyFrustrationReading,
    LillyHeavinessReading,
    LillyHouseClass,
    LillyMalevolentReading,
    LillyPerfectionReadings,
    LillyPerfectionRoutes,
    LillyPerfectionSearchPolicy,
    LillyProhibitionReading,
    LillyRefranationReading,
    LillyRouteCondition,
    LillyRouteConditions,
    LillyTranslationReading,
)

from ..models.horary_perfection import (
    LILLY_PERFECTION_ROUTES_PROFILE_ID,
    LillyPerfectionRoutesRequest,
    RouteConditionRequest,
)


_CONDITION_FIELDS = (
    "good_houses", "well_dignified", "querent_degree_dignity", "quesited_degree_dignity",
    "proper_good_houses", "friendly_houses", "moon_condition", "dwelling_placement",
)


def _condition(name: str, value: RouteConditionRequest | None) -> LillyRouteCondition | None:
    if value is None:
        return None
    return LillyRouteCondition(name, LillyP3State(value.state), LillyConditionEpoch(value.epoch),
                               value.source, tuple(value.evidence_ids))


def build_perfection_inputs(request: LillyPerfectionRoutesRequest):
    """Translate the strict request into engine readings, conditions and policy."""

    r = request.readings
    if request.readings_preset == "lilly_book_ii_practice":
        readings = LILLY_BOOK_II_PRACTICE
    else:
        readings = LillyPerfectionReadings(
            LillyTranslationReading(r.translation), LillyProhibitionReading(r.prohibition),
            LillyMalevolentReading(r.malevolent), LillyBeholdingReading(r.beholding),
            LillyHeavinessReading(r.heaviness), LillyRefranationReading(r.refranation),
            LillyFrustrationReading(r.frustration), LillyCollectionReading(r.collection),
            LillyDwellingReading(r.dwelling),
        )
    supplied = request.conditions
    if supplied is None:
        conditions = LillyRouteConditions()
    else:
        conditions = LillyRouteConditions(
            house_class=None if supplied.house_class is None else LillyHouseClass(supplied.house_class),
            **{name: _condition(name, getattr(supplied, name)) for name in _CONDITION_FIELDS},
            planet_house_classes=tuple((body, LillyHouseClass(value))
                                       for body, value in sorted(supplied.planet_house_classes.items())),
            evil_house_lords=None if supplied.evil_house_lords is None else tuple(supplied.evil_house_lords),
            impedited_planets=None if supplied.impedited_planets is None else tuple(supplied.impedited_planets),
        )
    search = request.search
    policy = (LillyPerfectionSearchPolicy() if search is None
              else LillyPerfectionSearchPolicy(past_days=search.past_days, future_days=search.future_days))
    return readings, conditions, policy


def compute_lilly_perfection_routes(engine: Moira, request: LillyPerfectionRoutesRequest) -> LillyPerfectionRoutes:
    """Delegate once to the facade; no doctrine is decided in transport."""

    readings, conditions, policy = build_perfection_inputs(request)
    result = engine.lilly_perfection_routes_at(
        request.jd_ut, request.querent, request.quesited,
        is_day_chart=request.is_day_chart, readings=readings, conditions=conditions, policy=policy,
        epoch=request.epoch_label,
    )
    if result.profile_id != LILLY_PERFECTION_ROUTES_PROFILE_ID or result.verdict is not None:
        raise RuntimeError("facade returned an unexpected perfection-routes profile")
    return result


__all__ = ["build_perfection_inputs", "compute_lilly_perfection_routes"]
