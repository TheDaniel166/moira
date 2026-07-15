"""Service orchestration for bounded Western electional evaluation."""

from __future__ import annotations

from moira import Moira
from moira.western_electional import (
    MoonConnectionFlowPolicy,
    MoonPreviousEventWindowPolicy,
    DorotheusMatter,
    DorotheusMatterProfileEvaluation,
    DorotheusMatterProfileId,
    DorotheusConstructionEvaluation,
    DorotheusMoonConditionEvaluation,
    DorotheusRootedContextEvaluation,
    RameseyMoonConditionEvaluation,
    SahlBurntPathVariant,
    SahlEighthRuleVariant,
    SahlMoonConditionEvaluation,
    WesternElectionClass,
    WesternElectionalProfileId,
    WesternElectionalProfileScan,
    WesternElectionalProfileScanPolicy,
    WesternElectionalQualificationStatus,
)

from ..models.western_electional import (
    DorotheusMoonConditionRequest,
    DorotheusConstructionRequest,
    DorotheusMatterProfileRequest,
    DorotheusRootedContextRequest,
    RameseyMoonConditionRequest,
    SahlMoonConditionRequest,
    WesternProfileWindowsRequest,
)


def compute_western_profile_windows(
    engine: Moira,
    request: WesternProfileWindowsRequest,
) -> WesternElectionalProfileScan:
    """Scan one named Moon profile through the reader-bound public facade."""

    scan_policy = WesternElectionalProfileScanPolicy(
        step_days=request.policy.step_days,
        merge_gap_days=request.policy.merge_gap_days,
        max_scan_points=request.policy.max_scan_points,
        max_windows=request.policy.max_windows,
        qualifying_statuses=tuple(
            WesternElectionalQualificationStatus(status)
            for status in request.qualification_statuses
        ),
    )
    burnt = (
        SahlBurntPathVariant(request.sahl_burnt_path_variant)
        if request.sahl_burnt_path_variant is not None
        else None
    )
    eighth = (
        SahlEighthRuleVariant(request.sahl_eighth_rule_variant)
        if request.sahl_eighth_rule_variant is not None
        else None
    )
    return engine.western_electional_profile_windows(
        request.jd_start,
        request.jd_end,
        request.latitude,
        request.longitude,
        house_system=request.house_system,
        profile_id=WesternElectionalProfileId(request.profile_id),
        scan_policy=scan_policy,
        unavoidable_time_urgency=request.unavoidable_time_urgency,
        sahl_burnt_path_variant=burnt,
        sahl_eighth_rule_variant=eighth,
    )


def compute_dorotheus_construction(
    engine: Moira,
    request: DorotheusConstructionRequest,
) -> DorotheusConstructionEvaluation:
    """Evaluate the complete V.7 profile through the public facade."""

    result = engine.dorotheus_construction_at(
        request.jd_ut,
        request.latitude,
        request.longitude,
        house_system=request.house_system,
        election_class=WesternElectionClass(request.election_class),
        natal_jd_ut=request.natal_jd_ut,
        natal_latitude=request.natal_latitude,
        natal_longitude=request.natal_longitude,
        natal_house_system=request.natal_house_system,
        unavoidable_time_urgency=request.unavoidable_time_urgency,
    )
    if result.profile_id != request.profile_id:
        raise RuntimeError(
            "facade returned a Western electional profile different from the request"
        )
    return result


def compute_dorotheus_matter_profile(
    engine: Moira,
    request: DorotheusMatterProfileRequest,
) -> DorotheusMatterProfileEvaluation:
    """Evaluate one V.8, V.9, or V.11 profile through the public facade."""

    flow_request = request.moon_flow_policy
    flow_policy = (
        None
        if flow_request is None
        else MoonConnectionFlowPolicy(
            previous_window=MoonPreviousEventWindowPolicy(
                flow_request.previous_window
            ),
            previous_lookback_days=flow_request.previous_lookback_days,
            modern=flow_request.modern,
        )
    )
    result = engine.dorotheus_matter_profile_at(
        request.jd_ut,
        request.latitude,
        request.longitude,
        house_system=request.house_system,
        profile_id=DorotheusMatterProfileId(request.profile_id),
        election_class=WesternElectionClass(request.election_class),
        natal_jd_ut=request.natal_jd_ut,
        natal_latitude=request.natal_latitude,
        natal_longitude=request.natal_longitude,
        natal_house_system=request.natal_house_system,
        unavoidable_time_urgency=request.unavoidable_time_urgency,
        moon_flow_policy=flow_policy,
    )
    if result.profile_id.value != request.profile_id:
        raise RuntimeError("facade returned a matter profile different from the request")
    return result


def compute_dorotheus_rooted_context(
    engine: Moira,
    request: DorotheusRootedContextRequest,
) -> DorotheusRootedContextEvaluation:
    """Evaluate the admitted rooted context through the public facade."""

    result = engine.dorotheus_rooted_context_at(
        request.jd_ut,
        request.latitude,
        request.longitude,
        house_system=request.house_system,
        matter=DorotheusMatter(request.matter),
        election_class=WesternElectionClass(request.election_class),
        natal_jd_ut=request.natal_jd_ut,
        natal_latitude=request.natal_latitude,
        natal_longitude=request.natal_longitude,
        natal_house_system=request.natal_house_system,
    )
    if result.profile_id != request.profile_id:
        raise RuntimeError(
            "facade returned a Western electional profile different from the request"
        )
    return result


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
    "compute_dorotheus_construction",
    "compute_dorotheus_matter_profile",
    "compute_dorotheus_rooted_context",
    "compute_dorotheus_moon_condition",
    "compute_ramesey_moon_condition",
    "compute_sahl_moon_condition",
    "compute_western_profile_windows",
]
