"""REST contracts for solar global circumstances and cartography."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from moira.julian import julian_day
from moira_server.app import create_app
from moira_server.config import ServerConfig
import moira_server.models as public_models
import moira_server.serializers as public_serializers
import moira_server.services as public_services
from moira_server.models.phenomena import SolarEclipseCartographyRequest


def test_solar_product_server_packages_reexport_complete_surface() -> None:
    for name in (
        "SolarEclipseGlobalCircumstancesRequest",
        "SolarEclipseGlobalCircumstancesResponse",
        "SolarEclipseConjunctionResponse",
        "SolarEclipseUmbralContactResponse",
        "SolarEclipseUmbralContactsResponse",
        "SolarEclipseCartographyRequest",
        "SolarEclipseCartographyResponse",
        "EclipseContourComponentResponse",
        "EclipseContourLevelResponse",
    ):
        assert name in public_models.__all__
        assert hasattr(public_models, name)
    assert "serialize_solar_eclipse_global_circumstances" in (
        public_serializers.__all__
    )
    assert "serialize_solar_eclipse_cartography" in public_serializers.__all__
    assert "compute_solar_eclipse_global_circumstances" in public_services.__all__
    assert "compute_solar_eclipse_cartography" in public_services.__all__


@pytest.mark.parametrize(
    ("payload", "field"),
    (
        ({"jd_start": "2451545.0"}, "jd_start"),
        ({"jd_start": 2451545.0, "mesh_depth": True}, "mesh_depth"),
        ({"jd_start": 2451545.0, "mesh_depth": 4}, "mesh_depth"),
        ({"jd_start": 2451545.0, "time_samples": 10}, "time_samples"),
        ({"jd_start": 2451545.0, "angular_tolerance_deg": 0.0}, "angular_tolerance_deg"),
        ({"jd_start": 2451545.0, "field_tolerance": 0.5}, "field_tolerance"),
        ({"jd_start": 2451545.0, "magnitude_levels": [0.8, 0.2]}, "magnitude_levels"),
        ({"jd_start": 2451545.0, "obscuration_levels": [0.0]}, "obscuration_levels"),
    ),
)
def test_solar_cartography_request_rejects_ambiguous_policy(
    payload: dict[str, Any],
    field: str,
) -> None:
    with pytest.raises(ValidationError) as exc_info:
        SolarEclipseCartographyRequest.model_validate(payload)
    assert any(error["loc"] == (field,) for error in exc_info.value.errors())


class _FakeFacade:
    def __init__(self, cartography) -> None:
        self.cartography = cartography
        self.global_circumstances = cartography.global_circumstances
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def solar_global_circumstances(self, jd_start: float, **kwargs):
        self.calls.append(("global", {"jd_start": jd_start, **kwargs}))
        return self.global_circumstances

    def solar_eclipse_cartography(self, jd_start: float, **kwargs):
        self.calls.append(("cartography", {"jd_start": jd_start, **kwargs}))
        return self.cartography


@pytest.mark.slow
@pytest.mark.loopback
def test_solar_product_routes_preserve_engine_semantics(
    eclipse_calculator,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seed = julian_day(2027, 7, 20)
    cartography = eclipse_calculator.solar_eclipse_cartography(
        seed,
        kind="total",
        magnitude_levels=(0.2, 0.8),
        obscuration_levels=(0.2, 0.8),
        mesh_depth=0,
        time_samples=9,
    )
    engine = _FakeFacade(cartography)
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: engine)
    app = create_app(ServerConfig(docs_enabled=False))

    with TestClient(app) as client:
        global_response = client.post(
            "/v1/eclipses/solar/global-circumstances",
            json={"jd_start": seed, "kind": "total"},
        )
        map_response = client.post(
            "/v1/eclipses/solar/cartography",
            json={
                "jd_start": seed,
                "kind": "total",
                "magnitude_levels": [0.2, 0.8],
                "obscuration_levels": [0.2, 0.8],
                "mesh_depth": 0,
                "time_samples": 9,
                "angular_tolerance_deg": 8.0,
                "field_tolerance": 0.01,
            },
        )

    assert global_response.status_code == 200, global_response.text
    global_body = global_response.json()
    assert global_body["greatest"]["local_class"] == "total"
    assert global_body["greatest"]["obscuration"] == 1.0
    assert global_body["equatorial_conjunction"]["kind"] == "equatorial"
    assert global_body["ecliptic_conjunction"]["kind"] == "ecliptic"
    assert global_body["gamma_earth_radii"] == pytest.approx(
        cartography.global_circumstances.gamma_earth_radii
    )
    assert global_body["first_central_line_limit"] is not None
    assert global_body["last_central_line_limit"] is not None
    assert global_body["umbral_contacts_admitted"] is True
    assert [
        global_body["umbral_contacts"][kind]["kind"]
        for kind in ("u1", "u2", "u3", "u4")
    ] == ["u1", "u2", "u3", "u4"]
    assert (
        global_body["umbral_contacts"]["u1"]["epoch"]["jd_ut1"]
        < global_body["umbral_contacts"]["u2"]["epoch"]["jd_ut1"]
        < global_body["event"]["jd_ut"]
        < global_body["umbral_contacts"]["u3"]["epoch"]["jd_ut1"]
        < global_body["umbral_contacts"]["u4"]["epoch"]["jd_ut1"]
    )
    assert global_body["greatest_duration_admitted"] is True
    assert global_body["greatest_duration"]["central_duration_seconds"] >= (
        global_body["greatest"]["central_duration_seconds"]
    )

    assert map_response.status_code == 200, map_response.text
    map_body = map_response.json()
    assert len(map_body["samples"]) == 12
    assert [level["threshold"] for level in map_body["magnitude_levels"]] == [
        0.2,
        0.8,
    ]
    assert [level["threshold"] for level in map_body["obscuration_levels"]] == [
        0.2,
        0.8,
    ]
    assert map_body["duration_contours_available"] is False
    assert map_body["projection"] == "SPHERICAL_GEOGRAPHIC"
    assert map_body["achieved_mesh_depth"] == 0
    assert map_body["mesh_triangle_count"] == 20
    assert map_body["unresolved_edge_count"] >= 0


def test_solar_product_openapi_contracts_are_typed() -> None:
    schema = create_app(ServerConfig(docs_enabled=False)).openapi()
    for path, request_name, response_name in (
        (
            "/v1/eclipses/solar/global-circumstances",
            "SolarEclipseGlobalCircumstancesRequest",
            "SolarEclipseGlobalCircumstancesResponse",
        ),
        (
            "/v1/eclipses/solar/cartography",
            "SolarEclipseCartographyRequest",
            "SolarEclipseCartographyResponse",
        ),
    ):
        operation = schema["paths"][path]["post"]
        assert operation["requestBody"]["content"]["application/json"]["schema"] == {
            "$ref": f"#/components/schemas/{request_name}"
        }
        assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
            "$ref": f"#/components/schemas/{response_name}"
        }
