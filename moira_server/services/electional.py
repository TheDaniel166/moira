"""Service layer for P13-01 bounded electional-window routes."""

from __future__ import annotations

from types import MappingProxyType
from typing import Any, Callable

from moira.constants import HOUSE_SYSTEM_NAMES
from moira.electional import (
    ElectionalPolicy,
    ElectionalScoredWindow,
    ElectionalWindow,
    find_electional_moments,
    find_electional_windows,
    find_scored_windows,
)
from moira.houses import house_of

from ..models.electional import (
    ELECTIONAL_SUBJECTS,
    ElectionalBoundsResponse,
    ElectionalMomentPolicyResponse,
    ElectionalMomentsListResponse,
    ElectionalMomentsProvenanceResponse,
    ElectionalMomentsRequest,
    ElectionalMomentsResponse,
    ElectionalPredicateCatalogResponse,
    ElectionalPredicateProfileId,
    ElectionalPredicateProfileResponse,
    ElectionalPredicateResponse,
    ElectionalPolicyResponse,
    ElectionalScoreSummaryResponse,
    ElectionalScoredPolicyResponse,
    ElectionalScoredProvenanceResponse,
    ElectionalScoredRequest,
    ElectionalScoredResponse,
    ElectionalScoredScanResponse,
    ElectionalScoredWindowResponse,
    ElectionalScanResponse,
    ElectionalScorerCatalogResponse,
    ElectionalScorerProfileId,
    ElectionalScorerProfileResponse,
    ElectionalScorerResponse,
    ElectionalValidationResponse,
    ElectionalWindowResponse,
    ElectionalWindowsRequest,
    ElectionalWindowsResponse,
    ElectionalProvenanceResponse,
    clean_subject,
    finite_float,
    scan_point_count,
    strict_int,
)


PROFILE_VERSION = "1"


def _reader_from_engine(engine: Any) -> tuple[Any | None, str]:
    try:
        reader = getattr(engine, "_reader", None)
    except Exception:
        reader = None
    if reader is not None:
        return reader, "server_explicit_reader"
    return None, "backend_default_reader"


def _short_arc_distance(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0)


def _arc_contains(longitude: float, start: float, end: float) -> bool:
    lon = longitude % 360.0
    start = start % 360.0
    end = end % 360.0
    if start <= end:
        return start <= lon <= end
    return lon >= start or lon <= end


def _payload_longitude(payload: Any, subject: str) -> float:
    if hasattr(payload, "longitudes"):
        longitudes = getattr(payload, "longitudes")
        if subject in longitudes:
            return float(longitudes[subject])
    planets = getattr(payload, "planets", None)
    if planets is not None and subject in planets:
        value = planets[subject]
        if hasattr(value, "longitude"):
            return float(value.longitude)
        return float(value)
    if isinstance(payload, dict):
        planets = payload.get("planets", {})
        if subject in planets:
            value = planets[subject]
            if hasattr(value, "longitude"):
                return float(value.longitude)
            return float(value)
        if subject in payload:
            return float(payload[subject])
    raise ValueError(f"predicate subject {subject!r} is absent from the chart payload")


def _payload_houses(payload: Any) -> Any:
    chart = getattr(payload, "chart", payload)
    houses = getattr(chart, "houses", None)
    if houses is None and isinstance(chart, dict):
        houses = chart.get("houses")
    if houses is None:
        raise ValueError("predicate requires houses but chart payload has none")
    return houses


def _clean_parameter_keys(params: dict[str, Any], allowed: set[str]) -> None:
    extra = sorted(set(params) - allowed)
    if extra:
        raise ValueError(f"predicate_parameters contains unsupported fields: {', '.join(extra)}")
    missing = sorted(allowed - set(params))
    if missing:
        raise ValueError(f"predicate_parameters missing required fields: {', '.join(missing)}")


def _clean_scorer_parameter_keys(params: dict[str, Any], allowed: set[str]) -> None:
    extra = sorted(set(params) - allowed)
    if extra:
        raise ValueError(f"scorer_parameters contains unsupported fields: {', '.join(extra)}")
    missing = sorted(allowed - set(params))
    if missing:
        raise ValueError(f"scorer_parameters missing required fields: {', '.join(missing)}")


def _longitude_range_predicate(params: dict[str, Any]) -> tuple[Callable[[Any], bool], dict[str, Any], list[str]]:
    _clean_parameter_keys(params, {"subject", "start_longitude", "end_longitude"})
    subject = clean_subject(params["subject"], "predicate_parameters.subject")
    start = finite_float(params["start_longitude"], "predicate_parameters.start_longitude")
    end = finite_float(params["end_longitude"], "predicate_parameters.end_longitude")

    def predicate(payload: Any) -> bool:
        return _arc_contains(_payload_longitude(payload, subject), start, end)

    return (
        predicate,
        {"subject": subject, "start_longitude": start, "end_longitude": end},
        [subject],
    )


def _house_membership_predicate(params: dict[str, Any]) -> tuple[Callable[[Any], bool], dict[str, Any], list[str]]:
    _clean_parameter_keys(params, {"subject", "houses"})
    subject = clean_subject(params["subject"], "predicate_parameters.subject")
    houses_raw = params["houses"]
    if not isinstance(houses_raw, list) or not houses_raw:
        raise ValueError("predicate_parameters.houses must be a non-empty list")
    houses: list[int] = []
    seen: set[int] = set()
    for index, raw_house in enumerate(houses_raw):
        house = strict_int(raw_house, f"predicate_parameters.houses[{index}]")
        if house < 1 or house > 12:
            raise ValueError("predicate_parameters.houses entries must be in [1, 12]")
        if house in seen:
            raise ValueError(f"predicate_parameters.houses contains duplicate house {house}")
        houses.append(house)
        seen.add(house)
    house_set = frozenset(houses)

    def predicate(payload: Any) -> bool:
        return house_of(_payload_longitude(payload, subject), _payload_houses(payload)) in house_set

    return predicate, {"subject": subject, "houses": houses}, [subject]


def _angular_separation_predicate(params: dict[str, Any]) -> tuple[Callable[[Any], bool], dict[str, Any], list[str]]:
    _clean_parameter_keys(params, {"subject_a", "subject_b", "min_angle", "max_angle"})
    subject_a = clean_subject(params["subject_a"], "predicate_parameters.subject_a")
    subject_b = clean_subject(params["subject_b"], "predicate_parameters.subject_b")
    if subject_a == subject_b:
        raise ValueError("predicate_parameters.subject_a and subject_b must differ")
    min_angle = finite_float(params["min_angle"], "predicate_parameters.min_angle")
    max_angle = finite_float(params["max_angle"], "predicate_parameters.max_angle")
    if min_angle < 0 or min_angle > 180 or max_angle < 0 or max_angle > 180:
        raise ValueError("predicate angle bounds must be in [0, 180]")
    if min_angle > max_angle:
        raise ValueError("predicate_parameters.min_angle must be <= max_angle")

    def predicate(payload: Any) -> bool:
        distance = _short_arc_distance(
            _payload_longitude(payload, subject_a),
            _payload_longitude(payload, subject_b),
        )
        return min_angle <= distance <= max_angle

    return (
        predicate,
        {
            "subject_a": subject_a,
            "subject_b": subject_b,
            "min_angle": min_angle,
            "max_angle": max_angle,
        },
        [subject_a, subject_b],
    )


def _predicate_from_request(
    request: ElectionalWindowsRequest | ElectionalMomentsRequest | ElectionalScoredRequest,
) -> tuple[Callable[[Any], bool], dict[str, Any], list[str]]:
    if request.predicate_profile is ElectionalPredicateProfileId.BODY_LONGITUDE_RANGE:
        return _longitude_range_predicate(request.predicate_parameters)
    if request.predicate_profile is ElectionalPredicateProfileId.BODY_HOUSE_MEMBERSHIP:
        if request.policy.zodiac_frame.value != "tropical":
            raise ValueError("body_house_membership_v1 supports tropical evaluation only")
        return _house_membership_predicate(request.predicate_parameters)
    if request.predicate_profile is ElectionalPredicateProfileId.BODY_ANGULAR_SEPARATION_RANGE:
        return _angular_separation_predicate(request.predicate_parameters)
    raise ValueError(f"unsupported predicate_profile {request.predicate_profile!r}")


def _effective_bodies(
    request: ElectionalWindowsRequest | ElectionalMomentsRequest | ElectionalScoredRequest,
    required: list[str],
) -> list[str] | None:
    if request.policy.bodies is None:
        return None
    missing = sorted(set(required) - set(request.policy.bodies))
    if missing:
        raise ValueError(
            "policy.bodies must include predicate-required or scorer-required subjects: "
            + ", ".join(missing)
        )
    return list(request.policy.bodies)


def _engine_policy(
    request: ElectionalWindowsRequest | ElectionalMomentsRequest | ElectionalScoredRequest,
    bodies: list[str] | None,
    *,
    max_windows: int | None,
    boundary_refine_steps: int,
) -> ElectionalPolicy:
    return ElectionalPolicy(
        step_days=request.policy.step_days,
        merge_gap_days=request.policy.merge_gap_days,
        house_system=request.policy.house_system,
        bodies=tuple(bodies) if bodies is not None else None,
        zodiac_frame=request.policy.zodiac_frame.value,
        ayanamsa_system=request.policy.ayanamsa_system,
        ayanamsa_mode=request.policy.ayanamsa_mode.value,
        boundary_refine_steps=boundary_refine_steps,
        max_windows=max_windows,
    )


def _profile_responses() -> list[ElectionalPredicateProfileResponse]:
    no_judgement = [
        "electional advice",
        "auspicious/inauspicious judgement",
        "arbitrary executable predicates",
    ]
    return [
        ElectionalPredicateProfileResponse(
            profile_id=ElectionalPredicateProfileId.BODY_LONGITUDE_RANGE.value,
            version=PROFILE_VERSION,
            description="Subject longitude lies inside a caller-supplied zodiacal arc.",
            required_parameters=["subject", "start_longitude", "end_longitude"],
            required_chart_fields=["planet longitude"],
            supported_frames=["tropical", "sidereal"],
            doctrine_status="numeric_scan_predicate_not_electional_judgement",
            non_goals=no_judgement,
        ),
        ElectionalPredicateProfileResponse(
            profile_id=ElectionalPredicateProfileId.BODY_HOUSE_MEMBERSHIP.value,
            version=PROFILE_VERSION,
            description="Subject occupies one of the requested houses.",
            required_parameters=["subject", "houses"],
            required_chart_fields=["planet longitude", "house cusps"],
            supported_frames=["tropical"],
            doctrine_status="house_position_scan_predicate_not_electional_judgement",
            non_goals=no_judgement,
        ),
        ElectionalPredicateProfileResponse(
            profile_id=ElectionalPredicateProfileId.BODY_ANGULAR_SEPARATION_RANGE.value,
            version=PROFILE_VERSION,
            description="Two subjects have shortest angular separation inside a numeric range.",
            required_parameters=["subject_a", "subject_b", "min_angle", "max_angle"],
            required_chart_fields=["planet longitudes"],
            supported_frames=["tropical", "sidereal"],
            doctrine_status="numeric_separation_scan_predicate_not_aspect_judgement",
            non_goals=no_judgement,
        ),
    ]


def _score_from_distance(distance: float, max_orb: float) -> float:
    score = 1.0 - (distance / max_orb)
    return max(0.0, min(1.0, score))


def _clean_max_orb(value: Any) -> float:
    max_orb = finite_float(value, "scorer_parameters.max_orb")
    if max_orb <= 0.0 or max_orb > 180.0:
        raise ValueError("scorer_parameters.max_orb must be in (0, 180]")
    return max_orb


def _longitude_target_closeness_scorer(
    params: dict[str, Any],
) -> tuple[Callable[[Any], float], dict[str, Any], list[str]]:
    _clean_scorer_parameter_keys(params, {"subject", "target_longitude", "max_orb"})
    subject = clean_subject(params["subject"], "scorer_parameters.subject")
    target = finite_float(params["target_longitude"], "scorer_parameters.target_longitude") % 360.0
    max_orb = _clean_max_orb(params["max_orb"])

    def scorer(payload: Any) -> float:
        distance = _short_arc_distance(_payload_longitude(payload, subject), target)
        return _score_from_distance(distance, max_orb)

    return (
        scorer,
        {"subject": subject, "target_longitude": target, "max_orb": max_orb},
        [subject],
    )


def _angular_target_closeness_scorer(
    params: dict[str, Any],
) -> tuple[Callable[[Any], float], dict[str, Any], list[str]]:
    _clean_scorer_parameter_keys(params, {"subject_a", "subject_b", "target_angle", "max_orb"})
    subject_a = clean_subject(params["subject_a"], "scorer_parameters.subject_a")
    subject_b = clean_subject(params["subject_b"], "scorer_parameters.subject_b")
    if subject_a == subject_b:
        raise ValueError("scorer_parameters.subject_a and subject_b must differ")
    target = finite_float(params["target_angle"], "scorer_parameters.target_angle")
    if target < 0.0 or target > 180.0:
        raise ValueError("scorer_parameters.target_angle must be in [0, 180]")
    max_orb = _clean_max_orb(params["max_orb"])

    def scorer(payload: Any) -> float:
        separation = _short_arc_distance(
            _payload_longitude(payload, subject_a),
            _payload_longitude(payload, subject_b),
        )
        distance = abs(separation - target)
        return _score_from_distance(distance, max_orb)

    return (
        scorer,
        {
            "subject_a": subject_a,
            "subject_b": subject_b,
            "target_angle": target,
            "max_orb": max_orb,
        },
        [subject_a, subject_b],
    )


def _scorer_from_request(
    request: ElectionalScoredRequest,
) -> tuple[Callable[[Any], float], dict[str, Any], list[str]]:
    if request.scorer_profile is ElectionalScorerProfileId.BODY_LONGITUDE_TARGET_CLOSENESS:
        return _longitude_target_closeness_scorer(request.scorer_parameters)
    if (
        request.scorer_profile
        is ElectionalScorerProfileId.BODY_ANGULAR_SEPARATION_TARGET_CLOSENESS
    ):
        return _angular_target_closeness_scorer(request.scorer_parameters)
    raise ValueError(f"unsupported scorer_profile {request.scorer_profile!r}")


def _scorer_profile_responses() -> list[ElectionalScorerProfileResponse]:
    no_judgement = [
        "electional advice",
        "auspicious/inauspicious judgement",
        "arbitrary executable scorers",
        "Western electional scoring doctrine",
    ]
    return [
        ElectionalScorerProfileResponse(
            profile_id=ElectionalScorerProfileId.BODY_LONGITUDE_TARGET_CLOSENESS.value,
            version=PROFILE_VERSION,
            description="Score closeness of one subject longitude to a target longitude.",
            required_parameters=["subject", "target_longitude", "max_orb"],
            required_chart_fields=["planet longitude"],
            supported_frames=["tropical", "sidereal"],
            score_scale=[0.0, 1.0],
            score_direction="higher_is_closer_numeric_fit",
            doctrine_status="numeric_fit_not_electional_judgement",
            non_goals=no_judgement,
        ),
        ElectionalScorerProfileResponse(
            profile_id=(
                ElectionalScorerProfileId.BODY_ANGULAR_SEPARATION_TARGET_CLOSENESS.value
            ),
            version=PROFILE_VERSION,
            description="Score closeness of two-subject angular separation to a target angle.",
            required_parameters=["subject_a", "subject_b", "target_angle", "max_orb"],
            required_chart_fields=["planet longitudes"],
            supported_frames=["tropical", "sidereal"],
            score_scale=[0.0, 1.0],
            score_direction="higher_is_closer_numeric_fit",
            doctrine_status="numeric_fit_not_electional_judgement",
            non_goals=no_judgement,
        ),
    ]


def electional_predicate_catalog() -> ElectionalPredicateCatalogResponse:
    return ElectionalPredicateCatalogResponse(
        profiles=_profile_responses(),
        bounds=ElectionalBoundsResponse(),
        provenance={
            "source_module": "moira.electional",
            "predicate_owner": "server_defined",
            "western_electional_doctrine": "not_admitted",
            "stage_sequence": ["catalog_serialization"],
        },
    )


def electional_scorer_catalog() -> ElectionalScorerCatalogResponse:
    return ElectionalScorerCatalogResponse(
        profiles=_scorer_profile_responses(),
        bounds=ElectionalBoundsResponse(),
        provenance={
            "source_module": "moira.electional",
            "scorer_owner": "server_defined",
            "score_scale": [0.0, 1.0],
            "score_direction": "higher_is_closer_numeric_fit",
            "western_electional_doctrine": "not_admitted",
            "stage_sequence": ["catalog_serialization"],
        },
    )


def _serialize_policy(
    request: ElectionalWindowsRequest,
    engine_policy: ElectionalPolicy,
    bodies: list[str] | None,
) -> ElectionalPolicyResponse:
    return ElectionalPolicyResponse(
        requested_step_days=request.policy.step_days,
        effective_step_days=engine_policy.step_days,
        requested_merge_gap_days=request.policy.merge_gap_days,
        effective_merge_gap_days=engine_policy.effective_merge_gap,
        requested_house_system=request.policy.house_system,
        effective_house_system=engine_policy.house_system,
        requested_bodies=request.policy.bodies,
        effective_bodies=bodies,
        requested_zodiac_frame=request.policy.zodiac_frame.value,
        effective_zodiac_frame=engine_policy.zodiac_frame,
        requested_ayanamsa_system=request.policy.ayanamsa_system,
        effective_ayanamsa_system=engine_policy.ayanamsa_system,
        requested_ayanamsa_mode=request.policy.ayanamsa_mode.value,
        effective_ayanamsa_mode=engine_policy.ayanamsa_mode,
        requested_boundary_refine_steps=request.policy.boundary_refine_steps,
        effective_boundary_refine_steps=engine_policy.boundary_refine_steps,
        requested_max_windows=request.policy.max_windows,
        effective_max_windows=engine_policy.max_windows or request.policy.max_windows,
    )


def _serialize_scored_policy(
    request: ElectionalScoredRequest,
    engine_policy: ElectionalPolicy,
    bodies: list[str] | None,
) -> ElectionalScoredPolicyResponse:
    policy = _serialize_policy(request, engine_policy, bodies)
    return ElectionalScoredPolicyResponse(**policy.model_dump())


def _serialize_moment_policy(
    request: ElectionalMomentsRequest,
    engine_policy: ElectionalPolicy,
    bodies: list[str] | None,
) -> ElectionalMomentPolicyResponse:
    return ElectionalMomentPolicyResponse(
        requested_step_days=request.policy.step_days,
        effective_step_days=engine_policy.step_days,
        requested_merge_gap_days=request.policy.merge_gap_days,
        effective_merge_gap_days=engine_policy.effective_merge_gap,
        requested_house_system=request.policy.house_system,
        effective_house_system=engine_policy.house_system,
        requested_bodies=request.policy.bodies,
        effective_bodies=bodies,
        requested_zodiac_frame=request.policy.zodiac_frame.value,
        effective_zodiac_frame=engine_policy.zodiac_frame,
        requested_ayanamsa_system=request.policy.ayanamsa_system,
        effective_ayanamsa_system=engine_policy.ayanamsa_system,
        requested_ayanamsa_mode=request.policy.ayanamsa_mode.value,
        effective_ayanamsa_mode=engine_policy.ayanamsa_mode,
        requested_boundary_refine_steps=request.policy.boundary_refine_steps,
        effective_boundary_refine_steps=engine_policy.boundary_refine_steps,
        requested_max_windows=request.policy.max_windows,
        effective_max_windows=engine_policy.max_windows,
    )


def _serialize_window(
    window: ElectionalWindow,
    *,
    include_qualifying_jds: bool,
    include_boundary_brackets: bool,
) -> ElectionalWindowResponse:
    return ElectionalWindowResponse(
        jd_start=window.jd_start,
        jd_end=window.jd_end,
        duration_hours=window.duration_hours,
        qualifying_count=len(window.qualifying_jds),
        qualifying_jds=list(window.qualifying_jds) if include_qualifying_jds else None,
        entry_bracket=(
            list(window.entry_bracket)
            if include_boundary_brackets and window.entry_bracket is not None
            else None
        ),
        exit_bracket=(
            list(window.exit_bracket)
            if include_boundary_brackets and window.exit_bracket is not None
            else None
        ),
    )


def _serialize_scored_window(
    scored: ElectionalScoredWindow,
    *,
    score_rank: int | None,
    include_qualifying_jds: bool,
    include_boundary_brackets: bool,
) -> ElectionalScoredWindowResponse:
    window = _serialize_window(
        scored.window,
        include_qualifying_jds=include_qualifying_jds,
        include_boundary_brackets=include_boundary_brackets,
    )
    return ElectionalScoredWindowResponse(
        **window.model_dump(),
        score=scored.score,
        peak_jd=scored.peak_jd,
        score_rank=score_rank,
    )


def _score_rank_map(scored_windows: list[ElectionalScoredWindow]) -> dict[int, int]:
    ranked = sorted(
        enumerate(scored_windows),
        key=lambda item: (-item[1].score, item[1].peak_jd, item[1].window.jd_start),
    )
    return {index: rank for rank, (index, _) in enumerate(ranked, start=1)}


def _score_summary(scored_windows: list[ElectionalScoredWindow]) -> ElectionalScoreSummaryResponse:
    scores = [scored.score for scored in scored_windows]
    return ElectionalScoreSummaryResponse(
        count=len(scored_windows),
        highest_score=max(scores) if scores else None,
        lowest_score=min(scores) if scores else None,
    )


def _provenance(
    *,
    request: ElectionalWindowsRequest,
    reader_owner: str,
) -> ElectionalProvenanceResponse:
    stages = [
        "input_validation",
        "predicate_profile_binding",
        "search_policy_binding",
        "chart_scan",
        "predicate_evaluation",
        "window_merge",
    ]
    if request.policy.boundary_refine_steps > 0:
        stages.append("boundary_refinement")
    stages.append("response_serialization")
    return ElectionalProvenanceResponse(
        predicate_profile=request.predicate_profile.value,
        predicate_profile_version=PROFILE_VERSION,
        reader_owner=reader_owner,
        stage_sequence=stages,
    )


def _moments_provenance(
    *,
    request: ElectionalMomentsRequest,
    reader_owner: str,
) -> ElectionalMomentsProvenanceResponse:
    return ElectionalMomentsProvenanceResponse(
        predicate_profile=request.predicate_profile.value,
        predicate_profile_version=PROFILE_VERSION,
        reader_owner=reader_owner,
        stage_sequence=[
            "input_validation",
            "predicate_profile_binding",
            "search_policy_binding",
            "chart_scan",
            "predicate_evaluation",
            "raw_moment_collection",
            "response_serialization",
        ],
    )


def _scored_provenance(
    *,
    request: ElectionalScoredRequest,
    reader_owner: str,
) -> ElectionalScoredProvenanceResponse:
    stages = [
        "input_validation",
        "predicate_profile_binding",
        "scorer_profile_binding",
        "search_policy_binding",
        "chart_scan",
        "predicate_evaluation",
        "scorer_evaluation",
        "window_merge",
        "score_peak_selection",
        "score_rank_assignment",
    ]
    if request.policy.boundary_refine_steps > 0:
        stages.append("boundary_refinement")
    stages.append("response_serialization")
    return ElectionalScoredProvenanceResponse(
        predicate_profile=request.predicate_profile.value,
        predicate_profile_version=PROFILE_VERSION,
        scorer_profile=request.scorer_profile.value,
        scorer_profile_version=PROFILE_VERSION,
        reader_owner=reader_owner,
        stage_sequence=stages,
    )


def compute_electional_windows(
    request: ElectionalWindowsRequest,
    engine: Any,
) -> ElectionalWindowsResponse:
    predicate, params, required_subjects = _predicate_from_request(request)
    bodies = _effective_bodies(request, required_subjects)
    policy = _engine_policy(
        request,
        bodies,
        max_windows=request.policy.max_windows,
        boundary_refine_steps=request.policy.boundary_refine_steps,
    )
    reader, reader_owner = _reader_from_engine(engine)
    windows = find_electional_windows(
        request.jd_start,
        request.jd_end,
        request.latitude,
        request.longitude,
        predicate,
        policy=policy,
        reader=reader,
    )
    count = scan_point_count(request.jd_start, request.jd_end, request.policy.step_days)
    return ElectionalWindowsResponse(
        predicate=ElectionalPredicateResponse(
            profile_id=request.predicate_profile.value,
            profile_version=PROFILE_VERSION,
            parameters=params,
        ),
        policy=_serialize_policy(request, policy, bodies),
        scan=ElectionalScanResponse(
            jd_start=request.jd_start,
            jd_end=request.jd_end,
            span_days=request.jd_end - request.jd_start,
            scan_point_count=count,
        ),
        windows=[
            _serialize_window(
                window,
                include_qualifying_jds=request.include_qualifying_jds,
                include_boundary_brackets=request.include_boundary_brackets,
            )
            for window in windows
        ],
        bounds=ElectionalBoundsResponse(),
        validation=ElectionalValidationResponse(passed=True, failures=[]),
        provenance=_provenance(request=request, reader_owner=reader_owner),
    )


def compute_electional_scored(
    request: ElectionalScoredRequest,
    engine: Any,
) -> ElectionalScoredResponse:
    predicate, predicate_params, predicate_subjects = _predicate_from_request(request)
    scorer, scorer_params, scorer_subjects = _scorer_from_request(request)
    required_subjects = sorted(set(predicate_subjects) | set(scorer_subjects))
    bodies = _effective_bodies(request, required_subjects)
    policy = _engine_policy(
        request,
        bodies,
        max_windows=request.policy.max_windows,
        boundary_refine_steps=request.policy.boundary_refine_steps,
    )
    reader, reader_owner = _reader_from_engine(engine)
    scored_windows = find_scored_windows(
        request.jd_start,
        request.jd_end,
        request.latitude,
        request.longitude,
        predicate,
        scorer,
        policy=policy,
        reader=reader,
    )
    for scored in scored_windows:
        if scored.score < 0.0 or scored.score > 1.0:
            raise ValueError("scorer output must be in [0.0, 1.0]")
    count = scan_point_count(request.jd_start, request.jd_end, request.policy.step_days)
    rank_map = _score_rank_map(scored_windows) if request.include_score_rank else {}
    return ElectionalScoredResponse(
        predicate=ElectionalPredicateResponse(
            profile_id=request.predicate_profile.value,
            profile_version=PROFILE_VERSION,
            parameters=predicate_params,
        ),
        scorer=ElectionalScorerResponse(
            profile_id=request.scorer_profile.value,
            profile_version=PROFILE_VERSION,
            parameters=scorer_params,
        ),
        policy=_serialize_scored_policy(request, policy, bodies),
        scan=ElectionalScoredScanResponse(
            jd_start=request.jd_start,
            jd_end=request.jd_end,
            span_days=request.jd_end - request.jd_start,
            scan_point_count=count,
        ),
        scored_windows=[
            _serialize_scored_window(
                scored,
                score_rank=rank_map.get(index),
                include_qualifying_jds=request.include_qualifying_jds,
                include_boundary_brackets=request.include_boundary_brackets,
            )
            for index, scored in enumerate(scored_windows)
        ],
        score_summary=_score_summary(scored_windows),
        bounds=ElectionalBoundsResponse(),
        validation=ElectionalValidationResponse(passed=True, failures=[]),
        provenance=_scored_provenance(request=request, reader_owner=reader_owner),
    )


def compute_electional_moments(
    request: ElectionalMomentsRequest,
    engine: Any,
) -> ElectionalMomentsResponse:
    predicate, params, required_subjects = _predicate_from_request(request)
    bodies = _effective_bodies(request, required_subjects)
    policy = _engine_policy(
        request,
        bodies,
        max_windows=None,
        boundary_refine_steps=0,
    )
    reader, reader_owner = _reader_from_engine(engine)
    moments = find_electional_moments(
        request.jd_start,
        request.jd_end,
        request.latitude,
        request.longitude,
        predicate,
        policy=policy,
        reader=reader,
    )
    count = scan_point_count(request.jd_start, request.jd_end, request.policy.step_days)
    return ElectionalMomentsResponse(
        predicate=ElectionalPredicateResponse(
            profile_id=request.predicate_profile.value,
            profile_version=PROFILE_VERSION,
            parameters=params,
        ),
        policy=_serialize_moment_policy(request, policy, bodies),
        scan=ElectionalScanResponse(
            jd_start=request.jd_start,
            jd_end=request.jd_end,
            span_days=request.jd_end - request.jd_start,
            scan_point_count=count,
        ),
        moments=ElectionalMomentsListResponse(
            count=len(moments),
            jds=list(moments) if request.include_moments else None,
            first_jd=moments[0] if moments else None,
            last_jd=moments[-1] if moments else None,
        ),
        bounds=ElectionalBoundsResponse(),
        validation=ElectionalValidationResponse(passed=True, failures=[]),
        provenance=_moments_provenance(request=request, reader_owner=reader_owner),
    )
