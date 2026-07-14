"""Service orchestration for bounded Western electional evaluation."""

from __future__ import annotations

from moira import Moira
from moira.western_electional import RameseyMoonConditionEvaluation

from ..models.western_electional import RameseyMoonConditionRequest


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


__all__ = ["compute_ramesey_moon_condition"]
