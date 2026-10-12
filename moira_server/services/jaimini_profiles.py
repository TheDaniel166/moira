"""Thin VED-013 transport; engine owns input admission and every source decision."""

from dataclasses import asdict

from moira._jaimini_profile_inputs import ArgalaReference, CharaProjection, JaiminiChart
from moira.argala_assessment import ArgalaAssessmentResult, assess_argala
from moira.chara_profiles import CharaArithmeticResult, evaluate_chara_profile
from moira.jaimini_profile_policy import list_jaimini_profiles
from ..models.jaimini_profiles import (
    ArgalaAssessmentRequest,
    ArgalaAssessmentResponse,
    CharaProfileRequest,
    CharaProfileResponse,
    JaiminiCatalogueResponse,
)


def jaimini_profile_catalogue() -> JaiminiCatalogueResponse:
    return JaiminiCatalogueResponse.model_validate(asdict(list_jaimini_profiles()))


def serialize_chara_profile(result: CharaArithmeticResult) -> CharaProfileResponse:
    if type(result) is not CharaArithmeticResult:
        raise RuntimeError("typed engine Chara arithmetic result required")
    try:
        result.__post_init__()
    except (ValueError, TypeError) as exc:
        raise RuntimeError("invalid engine Chara result invariant") from exc
    data = asdict(result)
    data["chart"]["positions"] = dict(result.chart.positions)
    try:
        return CharaProfileResponse.model_validate(data)
    except (ValueError, TypeError) as exc:
        raise RuntimeError("invalid engine Chara response contract") from exc


def serialize_argala_assessment(
    result: ArgalaAssessmentResult,
) -> ArgalaAssessmentResponse:
    if type(result) is not ArgalaAssessmentResult:
        raise RuntimeError("typed engine Argala assessment result required")
    try:
        result.__post_init__()
    except (ValueError, TypeError) as exc:
        raise RuntimeError("invalid engine Argala result invariant") from exc
    data = asdict(result)
    data["chart"]["positions"] = dict(result.chart.positions)
    for ref, row in zip(result.references, data["references"]):
        for pair, item in zip(ref.pairs, row["pairs"]):
            item.update(
                causer_count=pair.causer_count, blocker_count=pair.blocker_count
            )
    try:
        return ArgalaAssessmentResponse.model_validate(data)
    except (ValueError, TypeError) as exc:
        raise RuntimeError("invalid engine Argala response contract") from exc


def compute_chara_profile(request: CharaProfileRequest) -> CharaProfileResponse:
    request = CharaProfileRequest.model_validate(request.model_dump())
    result = evaluate_chara_profile(
        JaiminiChart(**request.chart.model_dump()),
        profile_id=request.profile_id,
        projection=CharaProjection(**request.projection.model_dump())
        if request.projection
        else None,
    )
    return serialize_chara_profile(result)


def compute_argala_assessment(
    request: ArgalaAssessmentRequest,
) -> ArgalaAssessmentResponse:
    request = ArgalaAssessmentRequest.model_validate(request.model_dump())
    result = assess_argala(
        JaiminiChart(**request.chart.model_dump()),
        profile_id=request.profile_id,
        references=tuple(ArgalaReference(**r.model_dump()) for r in request.references),
    )
    return serialize_argala_assessment(result)
