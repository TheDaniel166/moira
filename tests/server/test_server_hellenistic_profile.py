"""REST and OpenAPI gates for the Phase 5 Hellenistic profile."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

import moira_server.models as public_models
import moira_server.serializers as public_serializers
import moira_server.services as public_services
from moira.hellenistic import HellenisticProfileExclusion
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.hellenistic_profile import (
    HellenisticChartProfileRequest,
    HellenisticChartProfileResponse,
)
from moira_server.serializers.hellenistic_profile import (
    serialize_hellenistic_chart_profile,
)
from moira_server.services.hellenistic_profile import (
    compute_hellenistic_chart_profile,
)


pytestmark = pytest.mark.loopback


NATAL_DT = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
CURRENT_DT = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)
PAYLOAD = {
    "natal_dt": "2000-01-01T12:00:00Z",
    "current_dt": "2024-06-01T12:00:00Z",
    "civil_timezone": "America/New_York",
    "observer_lat": 40.7128,
    "observer_lon": -74.0060,
    "observer_elev_m": 10.0,
}


@pytest.fixture
def client_with_engine(
    moira_engine,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    monkeypatch.setattr(
        "moira_server.app.create_engine",
        lambda config: moira_engine,
    )
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        yield client


def _request() -> HellenisticChartProfileRequest:
    return HellenisticChartProfileRequest(
        natal_dt=NATAL_DT,
        current_dt=CURRENT_DT,
        civil_timezone="America/New_York",
        observer_lat=40.7128,
        observer_lon=-74.0060,
        observer_elev_m=10.0,
    )


def test_service_separates_planetary_and_observer_geometry() -> None:
    calls: dict[str, tuple[tuple, dict]] = {}
    chart = SimpleNamespace(name="geocentric-chart")
    houses = SimpleNamespace(name="observer-houses")
    expected = SimpleNamespace(name="profile")

    class RecordingEngine:
        def chart(self, *args, **kwargs):
            calls["chart"] = (args, kwargs)
            return chart

        def houses(self, *args, **kwargs):
            calls["houses"] = (args, kwargs)
            return houses

        def hellenistic_chart_profile(self, *args, **kwargs):
            calls["profile"] = (args, kwargs)
            return expected

    result = compute_hellenistic_chart_profile(RecordingEngine(), _request())

    assert result is expected
    assert calls["chart"][1] == {
        "bodies": [
            "Sun",
            "Moon",
            "Mercury",
            "Venus",
            "Mars",
            "Jupiter",
            "Saturn",
        ],
        "include_nodes": False,
    }
    assert calls["houses"][1]["latitude"] == PAYLOAD["observer_lat"]
    assert calls["houses"][1]["longitude"] == PAYLOAD["observer_lon"]
    assert calls["profile"][1]["position_frame"] == (
        "apparent_geocentric_true_ecliptic_of_date_"
        "positions_and_longitude_rates"
    )
    assert calls["profile"][1]["civil_timezone"] == "America/New_York"


def _paths_with_named_keys(
    value: object,
    fragments: tuple[str, ...],
    path: str = "",
) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{path}.{key}" if path else key
            if any(fragment in key.lower() for fragment in fragments):
                found.append(child)
            found.extend(_paths_with_named_keys(item, fragments, child))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(
                _paths_with_named_keys(
                    item,
                    fragments,
                    f"{path}[{index}]",
                )
            )
    return found


@pytest.mark.requires_ephemeris
def test_route_matches_engine_service_and_preserves_profile_boundaries(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    direct = serialize_hellenistic_chart_profile(
        compute_hellenistic_chart_profile(moira_engine, _request())
    ).model_dump(mode="json")

    response = client_with_engine.post(
        "/v1/hellenistic/chart-profile",
        json=PAYLOAD,
    )

    assert response.status_code == 200
    body = response.json()
    assert body == direct
    assert body["layer"] == "hellenistic"
    assert body["house_system"] == "W"
    assert len(body["planets"]) == 7
    assert len(body["lots"]) == 4
    assert body["observer"] == {
        "latitude": PAYLOAD["observer_lat"],
        "longitude": PAYLOAD["observer_lon"],
        "elevation_m": PAYLOAD["observer_elev_m"],
        "source": "supplied_geographic_observer",
    }
    assert set(body["excluded_components"]) == {
        item.value for item in HellenisticProfileExclusion
    }
    assert body["provenance"]["kernel_id"]
    assert body["provenance"]["kernel_coverage"]
    assert body["provenance"]["position_frame"] == (
        "apparent_geocentric_true_ecliptic_of_date_"
        "positions_and_longitude_rates"
    )
    assert body["profection"]["chronology"]["civil_timezone"] == (
        "America/New_York"
    )
    assert body["policy"]["monthly_profection_interval_policy"] == (
        "equal_twelfths_of_civil_anniversary_year"
    )
    assert body["policy"]["profection_ambiguous_time_policy"] is None
    assert body["provenance"]["method_id"] == (
        "moira.hellenistic_chart_profile.v2"
    )
    assert not _paths_with_named_keys(body, ("score",))
    assert not _paths_with_named_keys(
        body,
        (
            "firdaria",
            "almuten",
            "electional",
            "primary_direction",
            "deep_subdivision",
            "hermetic",
        ),
    )


def test_request_validation_rejects_ambiguous_or_closed_exclusion_inputs() -> None:
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        invalid_payloads = (
            {
                **PAYLOAD,
                "natal_dt": "2000-01-01T12:00:00",
            },
            {
                **PAYLOAD,
                "current_dt": "1999-01-01T12:00:00Z",
            },
            {
                **PAYLOAD,
                "house_system": "P",
            },
            {
                **PAYLOAD,
                "policy": {
                    "dignity": {
                        "essential": {"doctrine": "modern_co_rulers"}
                    }
                },
            },
            {
                **PAYLOAD,
                "policy": {
                    "lots": {"unresolved_reference_mode": "raise"}
                },
            },
            {
                **PAYLOAD,
                "policy": {
                    "profection_ambiguous_time_policy": "guess"
                },
            },
            {
                **PAYLOAD,
                "policy": {
                    "decennials": {
                        "deep_subdivision_method": "valens"
                    }
                },
            },
        )
        for payload in invalid_payloads:
            response = client.post(
                "/v1/hellenistic/chart-profile",
                json=payload,
            )
            assert response.status_code == 422
            assert response.json()["error_code"] == "validation_error"


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


def test_openapi_profile_graph_is_typed_score_free_with_closed_exclusions() -> None:
    openapi = create_app(ServerConfig(docs_enabled=False)).openapi()
    operation = openapi["paths"]["/v1/hellenistic/chart-profile"]["post"]
    schemas = openapi["components"]["schemas"]
    reachable = _reachable_schemas(
        schemas,
        "HellenisticChartProfileResponse",
    )

    assert operation["tags"] == ["hellenistic-profile"]
    assert (
        operation["responses"]["200"]["content"]["application/json"]["schema"][
            "$ref"
        ]
        == "#/components/schemas/HellenisticChartProfileResponse"
    )
    property_names = {
        property_name
        for schema in reachable.values()
        for property_name in schema.get("properties", {})
    }
    assert not {
        name
        for name in property_names
        if "score" in name.lower()
    }
    assert {
        "firdaria",
        "almuten",
        "electional",
        "primary_direction",
        "deep_subdivision_method",
        "hermetic_decan",
    }.isdisjoint(property_names)
    levels = schemas["HellenisticDecennialPeriodResponse"]["properties"][
        "level"
    ]
    assert levels["minimum"] == 1
    assert levels["maximum"] == 2
    assert "HellenisticProfileExclusion" in schemas
    assert "triacontaeteris" in schemas["HellenisticProfileExclusion"]["enum"]


def test_server_aggregators_export_the_profile_contract_by_identity() -> None:
    for name in (
        "HellenisticChartProfileRequest",
        "HellenisticChartProfileResponse",
        "HellenisticProfilePolicyRequest",
        "HellenisticDecennialPeriodResponse",
    ):
        assert name in public_models.__all__
    assert (
        public_models.HellenisticChartProfileResponse
        is HellenisticChartProfileResponse
    )
    assert (
        public_serializers.serialize_hellenistic_chart_profile
        is serialize_hellenistic_chart_profile
    )
    assert "serialize_hellenistic_chart_profile" in public_serializers.__all__
    assert (
        public_services.compute_hellenistic_chart_profile
        is compute_hellenistic_chart_profile
    )
    assert "compute_hellenistic_chart_profile" in public_services.__all__
