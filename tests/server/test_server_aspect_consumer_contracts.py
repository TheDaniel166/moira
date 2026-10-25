"""Aspect policy inputs keep the same strict types across REST consumers."""

from pydantic import ValidationError
import pytest
from types import SimpleNamespace

from fastapi.testclient import TestClient

from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.asteroids import AsteroidFamilyResonanceNetworkRequest
from moira_server.models.chart_wheel import ChartWheelConfig
from moira_server.models.forecasting import CompositeTransitRequest
from moira_server.models.relationship import SynastryPairRequest


pytestmark = pytest.mark.loopback


_PARTY = {"dt": "2000-01-01T12:00:00Z", "latitude": 0, "longitude": 0}
_CASES = [
    (SynastryPairRequest, {"first": _PARTY, "second": _PARTY}, "tier"),
    (ChartWheelConfig, {}, "aspect_tier"),
    (AsteroidFamilyResonanceNetworkRequest, {"dt": _PARTY["dt"], "numbers": [4, 63]}, "aspect_tier"),
]


@pytest.mark.parametrize(("model", "payload", "tier_field"), _CASES)
@pytest.mark.parametrize("value", [True, "2", 1.0])
def test_aspect_tier_types_do_not_coerce_at_transport_boundary(model, payload, tier_field, value):
    model.model_validate(payload)
    with pytest.raises(ValidationError):
        model.model_validate({**payload, tier_field: value})


@pytest.mark.parametrize(("model", "payload", "tier_field"), _CASES)
@pytest.mark.parametrize("value", [True, float("inf"), float("nan")])
def test_aspect_orb_multipliers_are_finite_numbers(model, payload, tier_field, value):
    model.model_validate(payload)
    with pytest.raises(ValidationError):
        model.model_validate({**payload, "orb_factor": value})


@pytest.mark.parametrize("value", [1, "true", "false"])
def test_synastry_node_flag_does_not_coerce(value):
    with pytest.raises(ValidationError):
        SynastryPairRequest(first=_PARTY, second=_PARTY, include_nodes=value)


@pytest.mark.parametrize(("model", "payload", "field"), [
    (ChartWheelConfig, {}, "include_aspects"),
    (AsteroidFamilyResonanceNetworkRequest, {"dt": _PARTY["dt"], "numbers": [4, 63]}, "include_minor"),
])
@pytest.mark.parametrize("value", [1, "true", "false"])
def test_other_aspect_inclusion_flags_do_not_coerce(model, payload, field, value):
    model.model_validate(payload)
    with pytest.raises(ValidationError):
        model.model_validate({**payload, field: value})


def test_forecast_tuple_aliases_normalize_identically_to_json_lists():
    payload = {
        "chart": {"first": _PARTY, "second": _PARTY}, "moving_bodies": ["Mars"],
        "jd_start": 2_460_000, "jd_end": 2_460_001, "tier": 2,
        "optional_sets": ["H13"],
    }
    for names in (["quindecile (165°)", "TREDECILE (13TH HARMONIC)"],
                  ("quindecile (165°)", "TREDECILE (13TH HARMONIC)")):
        request = CompositeTransitRequest.model_validate({**payload, "aspect_names": names})
        assert request.aspect_names == ["Tao", "H13 1/13"]


def test_pattern_route_retains_the_registered_septile_triangle(monkeypatch):
    from moira_server.services import relationship

    positions = {"Sun": 0, "Moon": 360 / 7, "Mercury": 1080 / 7}
    chart = SimpleNamespace(longitudes=lambda **_: positions, speeds=lambda: {})
    monkeypatch.setattr(relationship, "_build_party_chart", lambda *args, **kwargs: chart)
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: object())
    app = create_app(ServerConfig(docs_enabled=False, prewarm_enabled=False))
    with TestClient(app) as client:
        response = client.post("/v1/patterns/find", json={"chart": _PARTY, "include": ["Septile Triangle"]})
    assert response.status_code == 200
    body = response.json()
    assert body["computation_truth"]["aspect_catalog"] == "standard_longitude"
    assert body["computation_truth"]["aspect_tier"] == 2
    assert [event["name"] for event in body["events"]] == ["Septile Triangle"]
    assert {aspect["aspect"] for aspect in body["events"][0]["aspects"]} == {"Septile", "Biseptile", "Triseptile"}


@pytest.mark.parametrize("route", ["aspects", "contacts"])
def test_invalid_synastry_policy_rejects_before_chart_computation(monkeypatch, route):
    def unexpected(*args, **kwargs):
        pytest.fail("invalid aspect policy reached chart computation")

    monkeypatch.setattr("moira_server.services.relationship._pair_charts", unexpected)
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: object())
    app = create_app(ServerConfig(docs_enabled=False, prewarm_enabled=False))
    with TestClient(app) as client:
        for policy in ({"tier": True}, {"orb_factor": True}, {"include_nodes": 1}):
            response = client.post(f"/v1/synastry/{route}", json={"first": _PARTY, "second": _PARTY, **policy})
            assert response.status_code == 422


@pytest.mark.parametrize("route", ["composite", "davison"])
def test_unavailable_forecast_names_reject_before_chart_construction(monkeypatch, route):
    def unexpected(*args, **kwargs):
        pytest.fail("unavailable catalog selection reached chart construction")

    monkeypatch.setattr(f"moira_server.services.forecasting.compute_{route}_chart", unexpected)
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: object())
    app = create_app(ServerConfig(docs_enabled=False, prewarm_enabled=False))
    payload = {
        "chart": {"first": _PARTY, "second": _PARTY}, "moving_bodies": ["Mars"],
        "jd_start": 2_460_000, "jd_end": 2_460_001,
    }
    with TestClient(app) as client:
        for selection in ({"tier": 0, "aspect_names": ["Octile"]},
                          {"tier": 2, "aspect_names": ["1/13"]}):
            response = client.post(f"/v1/{route}/transits", json={**payload, **selection})
            assert response.status_code == 422
