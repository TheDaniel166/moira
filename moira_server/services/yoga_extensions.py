"""Canonical yoga extension transport; no source doctrine in the server."""

from dataclasses import asdict

from moira.yoga_extension_policy import list_yoga_extension_rules
from moira.yoga_extensions import evaluate_yoga_extensions, YogaExtensionChartResult
from ..models.yoga_extensions import (
    YogaExtensionCatalogueResponse,
    YogaExtensionChartResponse,
    YogaExtensionEvaluateRequest,
)


def yoga_extension_catalogue() -> YogaExtensionCatalogueResponse:
    return YogaExtensionCatalogueResponse.model_validate(
        asdict(list_yoga_extension_rules())
    )


def serialize_yoga_extensions(
    result: YogaExtensionChartResult, *, include_absent: bool = True
) -> YogaExtensionChartResponse:
    if type(include_absent) is not bool or type(result) is not YogaExtensionChartResult:
        raise ValueError("typed chart result and boolean include_absent required")
    result.__post_init__()
    data = asdict(result)
    for key in (
        "catalogue_version",
        "house_frame",
        "aspect_model",
        "conjunction_model",
        "navamsa_model",
    ):
        data["policy"][key] = getattr(result.policy, key)
    rows = []
    for yoga in result.results:
        if not include_absent and yoga.formation_state != "formed":
            continue
        row = asdict(yoga)
        row.update(
            aggregation=yoga.aggregation,
            formation_state=yoga.formation_state,
            cancellation_assessment=yoga.cancellation_assessment,
            qualifications=[asdict(q) for q in yoga.qualifications],
        )
        for out, branch in zip(row["branches"], yoga.branches):
            out.update(aggregation=branch.aggregation, state=branch.state)
        rows.append(row)
    data["results"] = rows
    for key in (
        "evaluated_count",
        "formed_count",
        "not_formed_count",
        "not_applicable_count",
    ):
        data[key] = getattr(result, key)
    data["returned_count"] = len(rows)
    return YogaExtensionChartResponse.model_validate(data)


def compute_yoga_extensions(
    request: YogaExtensionEvaluateRequest,
) -> YogaExtensionChartResponse:
    # Revalidate a caller-built/model_construct request before doctrine dispatch.
    request = YogaExtensionEvaluateRequest.model_validate(request.model_dump())
    result = evaluate_yoga_extensions(
        request.sidereal_longitudes,
        request.lagna_sidereal_lon,
        profile_ids=request.profile_ids,
    )
    return serialize_yoga_extensions(result, include_absent=request.include_absent)
