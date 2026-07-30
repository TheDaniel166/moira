"""REST contracts for lunar global circumstances."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from moira.eclipse import LunarEclipseGlobalCircumstances
from moira.julian import julian_day
from moira_server.app import create_app
from moira_server.config import ServerConfig
import moira_server.models as public_models
import moira_server.models.phenomena as phenomena_models
from moira_server.models.phenomena import (
    LunarEclipseGlobalCircumstancesRequest,
)
import moira_server.serializers as public_serializers
import moira_server.serializers.phenomena as phenomena_serializers
import moira_server.services as public_services
import moira_server.services.phenomena as phenomena_services


def test_lunar_global_server_packages_reexport_complete_surface() -> None:
    model_names = (
        "EclipseEpochResponse",
        "EclipseGeocentricBodyStateResponse",
        "LunarEclipseGlobalCircumstancesRequest",
        "LunarEclipseGlobalCircumstancesResponse",
        "LunarEclipseShadowStateResponse",
    )
    for name in model_names:
        assert name in public_models.__all__
        assert getattr(public_models, name) is getattr(phenomena_models, name)
    assert "serialize_lunar_eclipse_global_circumstances" in (
        public_serializers.__all__
    )
    assert (
        public_serializers.serialize_lunar_eclipse_global_circumstances
        is phenomena_serializers.serialize_lunar_eclipse_global_circumstances
    )
    assert "compute_lunar_eclipse_global_circumstances" in public_services.__all__
    assert (
        public_services.compute_lunar_eclipse_global_circumstances
        is phenomena_services.compute_lunar_eclipse_global_circumstances
    )


@pytest.mark.parametrize(
    ("payload", "field"),
    (
        ({"jd_start": "2451545.0"}, "jd_start"),
        ({"jd_start": 2451545.0, "backward": 1}, "backward"),
        ({"jd_start": 2451545.0, "kind": "hybrid"}, "kind"),
        ({"jd_start": 2451545.0, "mode": "approximate"}, "mode"),
    ),
)
def test_lunar_global_request_rejects_ambiguous_inputs(
    payload: dict[str, Any],
    field: str,
) -> None:
    with pytest.raises(ValidationError) as exc_info:
        LunarEclipseGlobalCircumstancesRequest.model_validate(payload)
    assert any(error["loc"] == (field,) for error in exc_info.value.errors())


class _FakeFacade:
    def __init__(self, result: LunarEclipseGlobalCircumstances) -> None:
        self.result = result
        self.calls: list[dict[str, Any]] = []

    def lunar_global_circumstances(
        self,
        jd_start: float,
        *,
        kind: str,
        backward: bool,
        mode: str,
    ) -> LunarEclipseGlobalCircumstances:
        self.calls.append(
            {
                "jd_start": jd_start,
                "kind": kind,
                "backward": backward,
                "mode": mode,
            }
        )
        return self.result


@pytest.mark.slow
@pytest.mark.loopback
def test_lunar_global_route_delegates_and_serializes_model_metadata(
    eclipse_calculator,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seed = julian_day(2026, 8, 20)
    result = eclipse_calculator.lunar_global_circumstances(
        seed,
        kind="partial",
        mode="nasa_compat",
    )
    engine = _FakeFacade(result)
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: engine)
    app = create_app(ServerConfig(docs_enabled=False))

    with TestClient(app) as client:
        response = client.post(
            "/v1/eclipses/lunar/global-circumstances",
            json={
                "jd_start": seed,
                "kind": "partial",
                "mode": "nasa_compat",
            },
        )

    assert response.status_code == 200, response.text
    assert engine.calls == [
        {
            "jd_start": seed,
            "kind": "partial",
            "backward": False,
            "mode": "nasa_compat",
        }
    ]
    body = response.json()
    assert body["mode"] == "nasa_compat"
    assert body["ephemeris"] == "DE-0441LE-0441"
    assert body["greatest"]["jd_tt"] == pytest.approx(result.greatest.jd_tt)
    assert body["greatest"]["jd_ut1"] == pytest.approx(result.greatest.jd_ut1)
    assert body["greatest"]["time_policy"] == result.greatest.time_policy
    assert body["sun"]["origin"] == "earth_center"
    assert body["sun"]["frame"] == "true_equator_and_equinox_of_date"
    assert body["shadow"]["gamma_earth_radii"] == pytest.approx(
        result.shadow.gamma_earth_radii
    )
    assert body["shadow"]["penumbral_magnitude"] == pytest.approx(
        result.shadow.penumbral_magnitude
    )
    assert body["partial_duration_seconds"] is not None
    assert body["total_duration_seconds"] is None


def test_lunar_global_openapi_contract_is_typed() -> None:
    schema = create_app(ServerConfig(docs_enabled=False)).openapi()
    operation = schema[
        "paths"
    ]["/v1/eclipses/lunar/global-circumstances"]["post"]
    assert operation["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/LunarEclipseGlobalCircumstancesRequest"
    }
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/LunarEclipseGlobalCircumstancesResponse"
    }
    request = schema["components"]["schemas"][
        "LunarEclipseGlobalCircumstancesRequest"
    ]
    assert request["properties"]["kind"]["enum"] == [
        "any",
        "total",
        "partial",
        "penumbral",
    ]
    assert request["properties"]["mode"]["enum"] == ["native", "nasa_compat"]
