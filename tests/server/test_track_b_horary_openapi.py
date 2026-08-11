"""OpenAPI closure gates for the Track B Horary transport."""

from __future__ import annotations

from moira.constants import HOUSE_SYSTEM_NAMES
from moira_server.app import create_app
from moira_server.config import ServerConfig


_PATH = "/v1/horary/evidence-profile"


def _reachable_schemas(
    schemas: dict[str, dict],
    root_name: str,
) -> dict[str, dict]:
    reachable: dict[str, dict] = {}
    pending = [root_name]
    while pending:
        name = pending.pop()
        if name in reachable:
            continue
        schema = schemas[name]
        reachable[name] = schema

        def visit(value: object) -> None:
            if isinstance(value, dict):
                ref = value.get("$ref")
                if isinstance(ref, str) and ref.startswith(
                    "#/components/schemas/"
                ):
                    pending.append(ref.rsplit("/", 1)[-1])
                for item in value.values():
                    visit(item)
            elif isinstance(value, list):
                for item in value:
                    visit(item)

        visit(schema)
    return reachable


def test_horary_operation_is_one_typed_post_in_named_family() -> None:
    openapi = create_app(ServerConfig(docs_enabled=False)).openapi()
    operation = openapi["paths"][_PATH]
    post = operation["post"]
    tag = {item["name"]: item for item in openapi["tags"]}["horary"]

    assert set(operation) == {"post"}
    assert post["operationId"] == "horary_evidence_profile"
    assert post["tags"] == ["horary"]
    assert post["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/HoraryEvidenceProfileRequest"
    }
    assert post["responses"]["200"]["content"]["application/json"][
        "schema"
    ] == {"$ref": "#/components/schemas/HoraryEvidenceProfileResponse"}
    assert tag["x-family"] == "classical-vedic"
    assert tag["x-familyLabel"] == "Classical and Vedic Doctrine"


def test_horary_request_schema_is_explicit_closed_and_source_bounded() -> None:
    schemas = create_app(ServerConfig(docs_enabled=False)).openapi()[
        "components"
    ]["schemas"]
    request = schemas["HoraryEvidenceProfileRequest"]
    properties = request["properties"]

    assert request["additionalProperties"] is False
    assert set(request["required"]) == {
        "question_id",
        "question_instant",
        "stated_basis",
        "stated_basis_source",
        "source_calendar",
        "source_instant_label",
        "conversion_policy_id",
        "latitude_deg",
        "longitude_deg",
        "house_system",
        "perspective_path",
        "terminal_topic_house",
    }
    assert properties["stated_basis"]["const"] == (
        "question_proposed_and_figure_erected"
    )
    assert properties["source_calendar"]["const"] == "gregorian"
    assert properties["conversion_policy_id"]["const"] == (
        "moira.julian.jd_from_datetime+utc_to_ut1:v1"
    )
    assert properties["question_instant"]["format"] == "date-time"
    assert set(properties["house_system"]["enum"]) == set(HOUSE_SYSTEM_NAMES)
    assert "Regiomontanus" not in properties["house_system"]["enum"]
    assert properties["terminal_topic_house"]["minimum"] == 1
    assert properties["terminal_topic_house"]["maximum"] == 12
    assert {
        "question_receipt",
        "house_geometry",
        "planetary_hour_receipt",
        "consideration_inputs",
        "perfection_analysis",
        "score",
        "outcome",
        "advice",
    }.isdisjoint(properties)


def test_horary_response_graph_has_only_explicit_closed_models() -> None:
    schemas = create_app(ServerConfig(docs_enabled=False)).openapi()[
        "components"
    ]["schemas"]
    reachable = _reachable_schemas(schemas, "HoraryEvidenceProfileResponse")
    root = schemas["HoraryEvidenceProfileResponse"]

    assert root["properties"]["house_geometry"]["$ref"].endswith(
        "/HoraryHouseGeometryResponse"
    )
    assert root["properties"]["significators"]["$ref"].endswith(
        "/HorarySignificatorSetResponse"
    )
    assert root["properties"]["perfection"]["$ref"].endswith(
        "/HoraryPerfectionEvidenceResponse"
    )
    assert all(
        schema.get("additionalProperties") is not True
        for schema in reachable.values()
    )
    assert all(
        not isinstance(property_schema, dict)
        or property_schema.get("additionalProperties") is not True
        for schema in reachable.values()
        for property_schema in schema.get("properties", {}).values()
    )
    property_names = {
        property_name
        for schema in reachable.values()
        for property_name in schema.get("properties", {})
    }
    assert {"score", "outcome", "advice", "recommendation"}.isdisjoint(
        property_names
    )
    assert {
        "HoraryObservedValueResponse",
        "HousesResponse",
        "SolarProximityTruthResponse",
        "ClassicalPerfectionEvaluationResponse",
    }.issubset(reachable)
