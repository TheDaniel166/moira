from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.loopback


@pytest.fixture
def client_with_engine(
    moira_engine,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        yield client


@pytest.mark.requires_ephemeris
def test_visibility_assessment_route_matches_engine_selected_truth(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    direct = moira_engine.visibility_tonight("Venus", 2451545.0, 0.0, 0.0)

    response = client_with_engine.post(
        "/v1/visibility/assessment",
        json={
            "body": "Venus",
            "jd_ut": 2451545.0,
            "lat": 0.0,
            "lon": 0.0,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["body"] == direct.body
    assert body["criterion_family"] == direct.criterion_family.value
    assert body["effective_limiting_magnitude"] == pytest.approx(direct.effective_limiting_magnitude)
    assert body["apparent_altitude_deg"] == pytest.approx(direct.apparent_altitude_deg)
    assert body["observable"] is direct.observable


@pytest.mark.requires_ephemeris
def test_visibility_tonight_route_matches_engine_alias_truth(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    direct = moira_engine.visibility_tonight("Venus", 2451545.0, 35.0, 35.0)

    response = client_with_engine.post(
        "/v1/visibility/tonight",
        json={
            "body": "Venus",
            "jd_ut": 2451545.0,
            "lat": 35.0,
            "lon": 35.0,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["body"] == "Venus"
    assert body["true_altitude_deg"] == pytest.approx(direct.true_altitude_deg)
    assert body["solar_elongation_deg"] == pytest.approx(direct.solar_elongation_deg)
    assert body["observable"] is direct.observable


@pytest.mark.requires_ephemeris
def test_visibility_routes_reject_unsupported_target_with_validation_envelope(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/visibility/assessment",
        json={
            "body": "NotAPlanet",
            "jd_ut": 2451545.0,
            "lat": 0.0,
            "lon": 0.0,
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "validation_error"
    assert body["category"] == "input_validation"
    assert "NotAPlanet" in body["message"]


def test_atmospheric_extinction_route_exposes_declared_model(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/visibility/atmospheric-extinction",
        json={
            "apparent_altitude_deg": 30.0,
            "model": "kasten_young_1989_broadband",
            "extinction_coefficient_k": 0.2,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["model"] == "kasten_young_1989_broadband"
    assert body["broadband_airmass"] == pytest.approx(1.9942928525)
    assert body["extinction_magnitude"] == pytest.approx(0.3988585705)
    assert body["sky_brightness_extinction_coefficient"] == pytest.approx(0.2)
    assert body["rayleigh_airmass"] is None


def test_visibility_openapi_exposes_bounded_physical_contracts(
    client_with_engine: TestClient,
) -> None:
    schema = client_with_engine.app.openapi()
    paths = schema["paths"]
    assert {
        "/v1/visibility/atmospheric-extinction",
        "/v1/visibility/twilight-sky-brightness",
        "/v1/visibility/point-source-threshold",
    } <= set(paths)

    schemas = schema["components"]["schemas"]
    extinction_model = schemas["AtmosphericExtinctionRequest"]["properties"]["model"]
    allowed_models = set(extinction_model.get("enum", []))
    if not allowed_models:
        allowed_models = {
            item["const"]
            for item in extinction_model["anyOf"]
            if "const" in item
        }
    assert allowed_models == {
        "kasten_young_1989_broadband",
        "schaefer_1993_components",
    }

    policy_properties = schemas["VisibilityPolicyRequest"]["properties"]
    assert "crumey_field_factor_includes_atmosphere" in policy_properties
    response_properties = schemas["VisibilityAssessmentResponse"]["properties"]
    assert {
        "criterion_target_magnitude",
        "target_extinction_applied_separately",
        "atmospheric_extinction",
        "twilight_sky_brightness",
        "point_source_threshold",
    } <= set(response_properties)
    extinction_response_properties = schemas[
        "AtmosphericExtinctionResponse"
    ]["properties"]
    assert "sky_brightness_extinction_coefficient" in (
        extinction_response_properties
    )


def test_twilight_and_crumey_threshold_routes_preserve_validity(
    client_with_engine: TestClient,
) -> None:
    twilight = client_with_engine.post(
        "/v1/visibility/twilight-sky-brightness",
        json={
            "target_altitude_deg": 90.0,
            "sun_altitude_deg": -12.0,
            "sun_target_separation_deg": 90.0,
            "extinction_coefficient_k": 0.2,
        },
    )
    assert twilight.status_code == 200
    twilight_body = twilight.json()
    assert twilight_body["model"] == "schaefer_1993_directional"
    assert twilight_body["valid"] is True
    assert twilight_body["sky_nanolamberts"] == pytest.approx(751.4833448)

    threshold = client_with_engine.post(
        "/v1/visibility/point-source-threshold",
        json={
            "background_nanolamberts": 2.0e-4 * 3.141592653589793 / 1.0e-5,
            "field_factor": 2.0,
        },
    )
    assert threshold.status_code == 200
    threshold_body = threshold.json()
    assert threshold_body["criterion_family"] == "crumey_2014_point_source"
    assert threshold_body["valid"] is True
    assert threshold_body["limiting_magnitude"] == pytest.approx(6.1818775043)


@pytest.mark.requires_ephemeris
def test_visibility_assessment_route_accepts_explicit_physical_policy(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/visibility/assessment",
        json={
            "body": "Venus",
            "jd_ut": 2451545.0,
            "lat": 0.0,
            "lon": 0.0,
            "policy": {
                "criterion_family": "crumey_2014_point_source",
                "extinction_model": "kasten_young_1989_broadband",
                "twilight_model": "schaefer_1993_directional",
                "environment": {
                    "sky_surface_brightness_mag_arcsec2": 21.25,
                },
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["criterion_family"] == "crumey_2014_point_source"
    assert body["criterion_applicable"] in {True, False}
    if body["atmospheric_extinction"] is not None:
        assert (
            body["atmospheric_extinction"]["model"]
            == "kasten_young_1989_broadband"
        )
    if body["criterion_target_magnitude"] is not None:
        assert body["criterion_target_magnitude"] == pytest.approx(
            body["apparent_magnitude"]
        )
        assert body["target_extinction_applied_separately"] is False
