"""REST contracts for the global lunar-eclipse visibility map."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from moira.eclipse import LunarEclipseVisibilityMap
from moira_server.app import create_app
from moira_server.config import ServerConfig
import moira_server.models as public_models
import moira_server.models.phenomena as phenomena_models
from moira_server.models.phenomena import LunarEclipseVisibilityRequest
import moira_server.serializers as public_serializers
import moira_server.serializers.phenomena as phenomena_serializers
import moira_server.services as public_services
import moira_server.services.phenomena as phenomena_services


def test_lunar_visibility_server_packages_reexport_complete_surface() -> None:
    model_names = (
        "LunarEclipseAnalysisModeValue",
        "LunarEclipseSearchKind",
        "LunarEclipseVisibilityContactKindValue",
        "LunarEclipseVisibilityLimitResponse",
        "LunarEclipseVisibilityMapResponse",
        "LunarEclipseVisibilityPointResponse",
        "LunarEclipseVisibilityRequest",
    )
    serializer_names = (
        "serialize_lunar_eclipse_visibility_limit",
        "serialize_lunar_eclipse_visibility_map",
        "serialize_lunar_eclipse_visibility_point",
    )
    for name in model_names:
        assert name in public_models.__all__
        assert getattr(public_models, name) is getattr(phenomena_models, name)
    for name in serializer_names:
        assert name in public_serializers.__all__
        assert getattr(public_serializers, name) is getattr(phenomena_serializers, name)
    assert "compute_lunar_eclipse_visibility" in public_services.__all__
    assert (
        public_services.compute_lunar_eclipse_visibility
        is phenomena_services.compute_lunar_eclipse_visibility
    )


@pytest.mark.parametrize(
    ("payload", "field"),
    (
        ({"jd_start": "2451545.0"}, "jd_start"),
        ({"jd_start": 2451545.0, "backward": 1}, "backward"),
        ({"jd_start": 2451545.0, "sample_count": True}, "sample_count"),
        ({"jd_start": 2451545.0, "sample_count": 8}, "sample_count"),
        ({"jd_start": 2451545.0, "kind": "hybrid"}, "kind"),
        ({"jd_start": 2451545.0, "mode": "approximate"}, "mode"),
    ),
)
def test_lunar_visibility_request_rejects_ambiguous_inputs(
    payload: dict[str, Any],
    field: str,
) -> None:
    with pytest.raises(ValidationError) as exc_info:
        LunarEclipseVisibilityRequest.model_validate(payload)
    assert any(error["loc"] == (field,) for error in exc_info.value.errors())


class _FakeFacade:
    def __init__(self, result: LunarEclipseVisibilityMap) -> None:
        self.result = result
        self.calls: list[dict[str, Any]] = []

    def lunar_eclipse_visibility_map(
        self,
        jd_start: float,
        *,
        kind: str,
        backward: bool,
        mode: str,
        sample_count: int,
    ) -> LunarEclipseVisibilityMap:
        self.calls.append(
            {
                "jd_start": jd_start,
                "kind": kind,
                "backward": backward,
                "mode": mode,
                "sample_count": sample_count,
            }
        )
        return self.result


@pytest.mark.slow
@pytest.mark.network
def test_lunar_visibility_route_delegates_and_serializes_map(
    eclipse_calculator,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = eclipse_calculator.lunar_eclipse_visibility_map(
        2_451_560.0,
        kind="total",
        sample_count=9,
    )
    engine = _FakeFacade(result)
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: engine)
    app = create_app(ServerConfig(docs_enabled=False))

    with TestClient(app) as client:
        response = client.post(
            "/v1/eclipses/lunar/visibility",
            json={
                "jd_start": 2_451_560.0,
                "kind": "total",
                "sample_count": 9,
            },
        )

    assert response.status_code == 200
    assert engine.calls == [
        {
            "jd_start": 2_451_560.0,
            "kind": "total",
            "backward": False,
            "mode": "native",
            "sample_count": 9,
        }
    ]
    body = response.json()
    assert body["event"]["jd_ut"] == pytest.approx(result.analysis.event.jd_ut)
    assert [limit["contact"] for limit in body["limits"]] == [
        "p1", "u1", "u2", "greatest", "u3", "u4", "p4"
    ]
    assert all(len(limit["points"]) == 9 for limit in body["limits"])
    assert all(limit["points"][0] == limit["points"][-1] for limit in body["limits"])
    assert body["horizon_model"] == "RETARDED_GEOMETRIC_MOON_CENTER"
    assert body["visible_side"] == "CONTAINS_SUBLUNAR_POINT"
    assert body["atmospheric_refraction"] is False


def test_lunar_visibility_openapi_contract_is_typed_and_bounded() -> None:
    schema = create_app(ServerConfig(docs_enabled=False)).openapi()
    operation = schema["paths"]["/v1/eclipses/lunar/visibility"]["post"]
    assert operation["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/LunarEclipseVisibilityRequest"
    }
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/LunarEclipseVisibilityMapResponse"
    }
    request = schema["components"]["schemas"]["LunarEclipseVisibilityRequest"]
    assert request["properties"]["kind"]["enum"] == [
        "any", "total", "partial", "penumbral"
    ]
    assert request["properties"]["mode"]["enum"] == ["native", "nasa_compat"]
    assert request["properties"]["sample_count"]["minimum"] == 9
    assert request["properties"]["sample_count"]["maximum"] == 721
    limit = schema["components"]["schemas"]["LunarEclipseVisibilityLimitResponse"]
    assert limit["properties"]["points"]["minItems"] == 9
