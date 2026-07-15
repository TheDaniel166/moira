"""Service orchestration for bounded Western electional evaluation."""

from __future__ import annotations

from moira import Moira
from moira.western_electional import (
    DorotheusMoonConditionEvaluation,
    RameseyMoonConditionEvaluation,
    SahlBurntPathVariant,
    SahlEighthRuleVariant,
    SahlMoonConditionEvaluation,
)

from ..models.western_electional import (
    DorotheusMoonConditionRequest,
    RameseyMoonConditionRequest,
    SahlMoonConditionRequest,
)


def compute_dorotheus_moon_condition(
    engine: Moira,
    request: DorotheusMoonConditionRequest,
) -> DorotheusMoonConditionEvaluation:
    """Evaluate the admitted Dorotheus profile through the public facade."""

    result = engine.dorotheus_moon_condition_at(
        request.jd_ut,
        request.latitude,
        request.longitude,
        house_system=request.house_system,
        unavoidable_time_urgency=request.unavoidable_time_urgency,
    )
    if result.profile_id != request.profile_id:
        raise RuntimeError(
            "facade returned a Western electional profile different from the request"
        )
    return result


def compute_ramesey_moon_condition(
    engine: Moira,
    request: RameseyMoonConditionRequest,
) -> RameseyMoonConditionEvaluation:
    """Evaluate the admitted profile through the public ``Moira`` facade."""

    result = engine.ramesey_moon_condition_at(
        request.jd_ut,
        request.latitude,
        request.longitude,
        house_system=request.house_system,
        unavoidable_time_urgency=request.unavoidable_time_urgency,
    )
    if result.profile_id != request.profile_id:
        raise RuntimeError(
            "facade returned a Western electional profile different from the request"
        )
    return result


def compute_sahl_moon_condition(
    engine: Moira,
    request: SahlMoonConditionRequest,
) -> SahlMoonConditionEvaluation:
    """Evaluate the admitted Sahl profile through the public facade."""

    result = engine.sahl_moon_condition_at(
        request.jd_ut,
        request.latitude,
        request.longitude,
        house_system=request.house_system,
        burnt_path_variant=SahlBurntPathVariant(request.burnt_path_variant),
        eighth_rule_variant=SahlEighthRuleVariant(request.eighth_rule_variant),
    )
    if result.profile_id != request.profile_id:
        raise RuntimeError(
            "facade returned a Western electional profile different from the request"
        )
    return result


__all__ = [
    "compute_dorotheus_moon_condition",
    "compute_ramesey_moon_condition",
    "compute_sahl_moon_condition",
]
