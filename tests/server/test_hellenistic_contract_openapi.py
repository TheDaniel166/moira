"""OpenAPI guards for the Phase 4 Hellenistic typed-truth contract."""

from __future__ import annotations

import pytest

from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.network


def _schema_refs(value: object) -> set[str]:
    if isinstance(value, dict):
        refs = {value["$ref"]} if "$ref" in value else set()
        for nested in value.values():
            refs.update(_schema_refs(nested))
        return refs
    if isinstance(value, list):
        refs: set[str] = set()
        for nested in value:
            refs.update(_schema_refs(nested))
        return refs
    return set()


def _assert_typed_ref(
    schemas: dict[str, dict],
    schema_name: str,
    field_name: str,
    expected_component: str,
) -> None:
    field_schema = schemas[schema_name]["properties"][field_name]
    assert (
        f"#/components/schemas/{expected_component}"
        in _schema_refs(field_schema)
    )
    assert "additionalProperties" not in field_schema


def test_openapi_preserves_typed_phase_3_receipts() -> None:
    schemas = create_app(ServerConfig(docs_enabled=False)).openapi()[
        "components"
    ]["schemas"]

    typed_fields = (
        (
            "PlanetaryDignityResponse",
            "essential_truth",
            "EssentialDignityTruthResponse",
        ),
        (
            "PlanetaryDignityResponse",
            "accidental_truth",
            "AccidentalDignityTruthResponse",
        ),
        (
            "ArabicPartResponse",
            "computation_truth",
            "ArabicPartComputationTruthResponse",
        ),
        (
            "ArabicPartResponse",
            "dependency_completeness",
            "LotDependencyCompletenessTruthResponse",
        ),
        (
            "ArabicPartResponse",
            "astrological_condition_truth",
            "LotAstrologicalConditionTruthResponse",
        ),
        (
            "LotsResultResponse",
            "not_evaluable",
            "LotNotEvaluableResponse",
        ),
        (
            "ProfectionResultResponse",
            "activation_truth",
            "ProfectionActivationTruthResponse",
        ),
        (
            "ProfectionResultResponse",
            "chronology",
            "ProfectionChronologyResponse",
        ),
        (
            "ProfectionChronologyResponse",
            "intervals",
            "MonthlyProfectionIntervalResponse",
        ),
        (
            "DecennialPeriodResponse",
            "sequence_truth",
            "DecennialSequenceAssemblyTruthResponse",
        ),
        (
            "ZRReleasingPeriodResponse",
            "fortune_angularity_truth",
            "ZRFortuneAngularityTruthResponse",
        ),
        (
            "WholeSignAspectResponse",
            "hellenistic_superiority_truth",
            "HellenisticSuperiorityTruthResponse",
        ),
        (
            "OvercomingResponse",
            "hellenistic_superiority_truth",
            "HellenisticSuperiorityTruthResponse",
        ),
    )
    for schema_name, field_name, expected_component in typed_fields:
        _assert_typed_ref(
            schemas,
            schema_name,
            field_name,
            expected_component,
        )

    chronology = schemas["ProfectionChronologyResponse"]
    assert chronology["additionalProperties"] is False
    assert chronology["properties"]["interval_policy"]["$ref"].endswith(
        "/MonthlyProfectionIntervalPolicy"
    )
    assert chronology["properties"]["method"]["$ref"].endswith(
        "/ProfectionChronologyMethod"
    )
    ambiguous_policy = chronology["properties"]["ambiguous_time_policy"]
    ambiguous_refs = {
        choice.get("$ref", "")
        for choice in ambiguous_policy["anyOf"]
    }
    assert any(
        reference.endswith("/ProfectionAmbiguousTimePolicy")
        for reference in ambiguous_refs
    )
    assert chronology["properties"]["boundary_semantics"]["$ref"].endswith(
        "/ProfectionIntervalBoundarySemantics"
    )


def test_openapi_keeps_decennial_depth_and_unadmitted_hermetic_routes_absent() -> None:
    openapi = create_app(ServerConfig(docs_enabled=False)).openapi()
    request_properties = openapi["components"]["schemas"][
        "DecennialNatalRequest"
    ]["properties"]
    levels = request_properties["levels"]

    assert levels["minimum"] == 1
    assert levels["maximum"] == 2
    assert "deep_subdivision_method" not in request_properties
    schemas = openapi["components"]["schemas"]
    assert "DecennialDeepSubdivisionMethod" not in schemas
    for schema_name in (
        "DecennialPeriodResponse",
        "DecennialSequenceResponse",
        "DecennialGroupsResponse",
        "DecennialCurrentResponse",
        "DecennialConditionProfileResponse",
        "DecennialSequenceProfileResponse",
        "DecennialActivePairOptionalResponse",
        "DecennialActivePathOptionalResponse",
    ):
        assert (
            schemas[schema_name]["properties"]["deep_subdivision_method"][
                "type"
            ]
            == "null"
        )
    assert not any(
        path.startswith("/v1/hermetic-decans")
        for path in openapi["paths"]
    )
