"""OpenAPI closure gates for the Track B Mundane transport."""

from __future__ import annotations

from moira.constants import HOUSE_SYSTEM_NAMES
from moira_server.app import create_app
from moira_server.config import ServerConfig


_PATH = "/v1/mundane/event-chart-profile"
_EVENT_SCHEMAS = {
    "cardinal_ingress": "CardinalIngressProfileRequest",
    "primary_syzygy": "PrimarySyzygyProfileRequest",
    "eclipse": "EclipseProfileRequest",
    "jupiter_saturn_ecliptic_longitude_conjunction": (
        "JupiterSaturnProfileRequest"
    ),
}


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


def _assert_no_arbitrary_json(value: object) -> None:
    if isinstance(value, dict):
        assert value, "reachable OpenAPI schema contains an untyped empty object"
        if value.get("type") == "object":
            assert value.get("additionalProperties") is False
        for item in value.values():
            _assert_no_arbitrary_json(item)
    elif isinstance(value, list):
        for item in value:
            _assert_no_arbitrary_json(item)


def test_mundane_operation_is_exactly_one_typed_post_in_predictive_family() -> None:
    openapi = create_app(ServerConfig(docs_enabled=False)).openapi()
    operation = openapi["paths"][_PATH]
    post = operation["post"]
    tag = {item["name"]: item for item in openapi["tags"]}["mundane"]

    assert set(operation) == {"post"}
    assert post["operationId"] == "mundane_event_chart_profile"
    assert post["tags"] == ["mundane"]
    assert post["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/MundaneEventChartProfileRequest"
    }
    assert post["responses"]["200"]["content"]["application/json"][
        "schema"
    ] == {"$ref": "#/components/schemas/MundaneEventChartProfileResponse"}
    assert tag["x-family"] == "predictive"
    assert tag["x-familyLabel"] == "Predictive Timing"


def test_request_is_a_real_closed_four_way_discriminated_union() -> None:
    schemas = create_app(ServerConfig(docs_enabled=False)).openapi()[
        "components"
    ]["schemas"]
    root = schemas["MundaneEventChartProfileRequest"]
    mapping = root["discriminator"]["mapping"]

    assert root["discriminator"]["propertyName"] == "event_type"
    assert mapping == {
        event_type: f"#/components/schemas/{schema_name}"
        for event_type, schema_name in _EVENT_SCHEMAS.items()
    }
    assert {
        item["$ref"].rsplit("/", 1)[-1] for item in root["oneOf"]
    } == set(_EVENT_SCHEMAS.values())
    for event_type, schema_name in _EVENT_SCHEMAS.items():
        schema = schemas[schema_name]
        properties = schema["properties"]
        assert schema["additionalProperties"] is False
        assert properties["event_type"]["const"] == event_type
        assert properties["search_start_utc"]["format"] == "date-time"
        assert properties["search_end_utc"]["format"] == "date-time"
        assert set(properties["house_system"]["enum"]) == set(HOUSE_SYSTEM_NAMES)
        assert {"search_start_utc", "search_end_utc", "location", "house_system"}.issubset(
            schema["required"]
        )
        assert {
            "receipt",
            "provenance",
            "source_refs",
            "clock",
            "score",
            "outcome",
            "advice",
        }.isdisjoint(properties)


def test_request_exposes_only_explicit_event_and_caller_location_inputs() -> None:
    schemas = create_app(ServerConfig(docs_enabled=False)).openapi()[
        "components"
    ]["schemas"]
    location = schemas["MundaneLocationRequest"]

    assert location["additionalProperties"] is False
    assert set(location["required"]) == {
        "label",
        "role",
        "source_id",
        "valid_from_utc",
        "valid_until_utc",
        "latitude_deg",
        "longitude_deg_east",
    }
    assert set(location["properties"]) == set(location["required"])
    assert schemas["CardinalIngressProfileRequest"]["properties"][
        "selected_ingress"
    ]["$ref"].endswith("/CardinalIngress")
    assert schemas["CardinalIngressProfileRequest"]["properties"][
        "selection_policy"
    ]["$ref"].endswith("/CardinalIngressSelectionPolicy")
    assert schemas["PrimarySyzygyProfileRequest"]["properties"][
        "anchor_ingress"
    ]["$ref"].endswith("/CardinalIngress")
    eclipse = schemas["EclipseProfileRequest"]["properties"]
    assert eclipse["eclipse_kind"]["$ref"].endswith("/EclipseKind")
    assert eclipse["chart_epoch_kind"]["$ref"].endswith("/EclipseAnchorEpoch")
    root_index = schemas["JupiterSaturnProfileRequest"]["properties"][
        "selected_root_index"
    ]
    assert root_index["type"] == "integer"
    assert root_index["minimum"] == 0


def test_response_graph_is_closed_typed_and_keeps_each_selection_family() -> None:
    schemas = create_app(ServerConfig(docs_enabled=False)).openapi()[
        "components"
    ]["schemas"]
    reachable = _reachable_schemas(
        schemas,
        "MundaneEventChartProfileResponse",
    )
    root = schemas["MundaneEventChartProfileResponse"]
    selection = root["properties"]["selection"]

    assert selection["discriminator"]["propertyName"] == "event_type"
    assert root["properties"]["profile"]["$ref"].endswith(
        "/MundaneProfileResponse"
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
    for schema in reachable.values():
        _assert_no_arbitrary_json(schema)
    assert {
        "CardinalIngressReceiptResponse",
        "PrimarySyzygyReceiptResponse",
        "EclipseEventReceiptResponse",
        "JupiterSaturnConjunctionReceiptResponse",
        "JupiterSaturnSequenceResponse",
        "MundaneNotEvaluableResponse",
        "HousesResponse",
    }.issubset(reachable)


def test_response_schema_contains_evidence_not_judgement_fields() -> None:
    schemas = create_app(ServerConfig(docs_enabled=False)).openapi()[
        "components"
    ]["schemas"]
    reachable = _reachable_schemas(
        schemas,
        "MundaneEventChartProfileResponse",
    )
    property_names = {
        property_name
        for schema in reachable.values()
        for property_name in schema.get("properties", {})
    }

    assert {
        "judgement",
        "score",
        "outcome",
        "advice",
        "recommendation",
        "prediction",
    }.isdisjoint(property_names)
    assert {
        "status",
        "not_evaluable",
        "included_components",
        "excluded_components",
        "source_refs",
        "solver_semantics",
        "verified_reader_identity",
    }.issubset(property_names)
