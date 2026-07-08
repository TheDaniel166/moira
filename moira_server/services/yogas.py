"""Service helpers for the Yoga engine routes."""

from __future__ import annotations

from moira.yogas import YogaPolicy, YogaResult, evaluate_yogas

from ..models.yogas import (
    YogaChartResponse,
    YogaConditionResponse,
    YogaEvaluateRequest,
    YogaResultResponse,
)


def _policy_from_request(request: YogaEvaluateRequest) -> YogaPolicy:
    if request.policy is None:
        return YogaPolicy()
    return YogaPolicy(
        moon_benefic_mode=request.policy.moon_benefic_mode,
        mercury_benefic_mode=request.policy.mercury_benefic_mode,
        mahapurusha_reference=request.policy.mahapurusha_reference,
        gajakesari_mode=request.policy.gajakesari_mode,
        budhaditya_combustion_cancel=request.policy.budhaditya_combustion_cancel,
        viparita_mode=request.policy.viparita_mode,
    )


def _serialize_yoga(result: YogaResult) -> YogaResultResponse:
    return YogaResultResponse(
        name=result.name,
        family=result.family,
        formed=result.formed,
        cancelled=result.cancelled,
        present=result.present,
        conditions=tuple(
            YogaConditionResponse(
                description=c.description,
                satisfied=c.satisfied,
                observed=c.observed,
            )
            for c in result.conditions
        ),
        cancellations=tuple(
            YogaConditionResponse(
                description=c.description,
                satisfied=c.satisfied,
                observed=c.observed,
            )
            for c in result.cancellations
        ),
        participants=result.participants,
        houses_involved=result.houses_involved,
        source=result.source,
        suppressed_by=result.suppressed_by,
        notes=result.notes,
    )


def compute_yogas(request: YogaEvaluateRequest) -> YogaChartResponse:
    """Evaluate every yoga family; optionally include unformed proof objects."""
    result = evaluate_yogas(
        request.sidereal_longitudes,
        request.lagna_sidereal_lon,
        _policy_from_request(request),
        planet_speeds=request.planet_speeds,
    )
    yogas = result.yogas if request.include_absent else tuple(
        y for y in result.yogas
        if y.present or y.formed  # formed-but-cancelled/suppressed stay visible
    )
    return YogaChartResponse(
        lagna_sign_index=result.lagna_sign_index,
        present_names=result.present_names,
        evaluated_count=len(result.yogas),
        yogas=tuple(_serialize_yoga(y) for y in yogas),
    )


__all__ = ["compute_yogas"]
