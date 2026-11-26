"""HTTP parity witnesses for shared-ARMC house comparison."""

from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from moira.constants import HouseSystem
from moira.houses import compare_systems, houses_from_armc
from moira_server.app import create_app
from moira_server.dependencies import get_engine


pytestmark = pytest.mark.loopback
_PATH = "/v1/houses/compare"
_BASE = {"armc": 95.0, "obliquity": 23.4392911, "latitude": -72.0}


@pytest.fixture
def client():
    app = create_app()

    def unexpected_engine():
        pytest.fail("Static house comparison must not require an ephemeris engine.")

    app.dependency_overrides[get_engine] = unexpected_engine
    return TestClient(app)


def _assert_engine_comparison(response, shared, left_system, right_system):
    assert response.status_code == 200, response.text
    compared = response.json()
    arguments = shared.copy()
    armc = arguments.pop("armc")
    obliquity = arguments.pop("obliquity")
    latitude = arguments.pop("latitude")
    left = houses_from_armc(armc, obliquity, latitude, left_system, **arguments)
    right = houses_from_armc(armc, obliquity, latitude, right_system, **arguments)
    expected = compare_systems(left, right)

    for key, figure in (("left", left), ("right", right)):
        actual = compared[key]
        assert actual["cusps"] == list(figure.cusps)
        for name in ("system", "effective_system", "fallback", "fallback_reason", "armc", "asc", "mc"):
            assert actual[name] == getattr(figure, name)
    assert compared["cusp_deltas"] == list(expected.cusp_deltas)
    for name in ("systems_agree", "fallback_differs", "families_differ"):
        assert compared[name] is getattr(expected, name)
    return compared


@pytest.mark.parametrize(("armc", "latitude", "left", "right"), [
    (95, 40, HouseSystem.PORPHYRY, HouseSystem.PLACIDUS),
    (95, -72, HouseSystem.PULLEN_SD, HouseSystem.PORPHYRY),
    (220, 80, HouseSystem.PORPHYRY, HouseSystem.PULLEN_SD),
])
def test_house_comparison_matches_direct_engine(client, armc, latitude, left, right):
    shared = {**_BASE, "armc": armc, "latitude": latitude}
    result = client.post(_PATH, json={**shared, "left_system": left, "right_system": right})
    compared = _assert_engine_comparison(result, shared, left, right)
    assert compared["left"]["boundary_geometry"] is None
    assert compared["right"]["boundary_geometry"] is None


def test_house_comparison_shares_solar_input_and_carries_zodiac_geometry(client):
    shared = {**_BASE, "ayanamsa_offset": 24, "sun_longitude": 98, "include_boundary_geometry": True}
    response = client.post(_PATH, json={**shared, "left_system": "Whole Sign", "right_system": "Solar Sign"})
    result = _assert_engine_comparison(response, shared, HouseSystem.WHOLE_SIGN, HouseSystem.SOLAR_SIGN)
    for figure in (result["left"], result["right"]):
        geometry = figure["boundary_geometry"]
        assert geometry["zodiac_offset_deg"] == 24
        assert geometry["observer_latitude_deg"] == -72
        assert geometry["obliquity_deg"] == _BASE["obliquity"]


def test_house_comparison_preserves_polar_fallback_and_strict_refusal(client):
    request = {**_BASE, "left_system": HouseSystem.KOCH, "right_system": HouseSystem.PORPHYRY}
    result = _assert_engine_comparison(client.post(_PATH, json=request), _BASE, HouseSystem.KOCH, HouseSystem.PORPHYRY)
    assert result["left"]["effective_system"] == result["right"]["effective_system"] == HouseSystem.PORPHYRY
    assert result["left"]["fallback"] is True
    assert result["right"]["fallback"] is False
    assert result["systems_agree"] is result["fallback_differs"] is True
    assert result["cusp_deltas"] == [0.0] * 12

    strict = client.post(_PATH, json={**request, "policy": {"polar_fallback": "raise"}})
    assert strict.status_code == 422, strict.text
    assert strict.json()["message"].startswith("left_system:")


def test_house_comparison_respects_unknown_system_policy(client):
    request = {**_BASE, "latitude": 40, "left_system": HouseSystem.PORPHYRY, "right_system": "unknown"}
    response = client.post(_PATH, json=request)
    assert response.status_code == 200, response.text
    assert response.json()["right"]["fallback"] is True
    assert response.json()["right"]["effective_system"] == HouseSystem.PLACIDUS
    strict = client.post(_PATH, json={**request, "policy": {"unknown_system": "raise"}})
    assert strict.status_code == 422, strict.text
    assert strict.json()["message"].startswith("right_system:")


@pytest.mark.parametrize("armc_at_crossing", [216.91232061213, 323.08767938787])
def test_house_comparison_preserves_pullen_sd_at_the_narrow_quadrant_crossing(client, armc_at_crossing):
    figures = []
    for offset in (-0.001, 0.001):
        shared = {**_BASE, "armc": armc_at_crossing + offset, "latitude": 65}
        payload = {**shared, "left_system": HouseSystem.PULLEN_SD, "right_system": HouseSystem.PORPHYRY}
        result = _assert_engine_comparison(
            client.post(_PATH, json=payload), shared, HouseSystem.PULLEN_SD, HouseSystem.PORPHYRY,
        )
        figures.append(result["left"])

    narrow_widths = sorted(
        min((figure["asc"] - figure["mc"]) % 360, (figure["ic"] - figure["asc"]) % 360)
        for figure in figures
    )
    assert narrow_widths[0] < 30 < narrow_widths[1]
    assert figures[0]["cusps"] == pytest.approx(figures[1]["cusps"], abs=0.003)


@pytest.mark.parametrize(("right_first_cusp", "expected"), [(2.0, 3.0), (179.0, 180.0)])
def test_house_comparison_serializes_signed_wrap_and_antipodal_tie(client, monkeypatch, right_first_cusp, expected):
    figure = houses_from_armc(95, 23.4392911, -72, HouseSystem.WHOLE_SIGN)
    left = replace(figure, cusps=tuple((359.0 + 30 * i) % 360 for i in range(12)))
    right = replace(figure, cusps=tuple((right_first_cusp + 30 * i) % 360 for i in range(12)))
    figures = iter((left, right))
    monkeypatch.setattr("moira_server.services.chart.houses_from_armc", lambda *args, **kwargs: next(figures))

    response = client.post(_PATH, json={**_BASE, "left_system": "W", "right_system": "W"})
    assert response.status_code == 200, response.text
    assert response.json()["cusp_deltas"] == [expected] * 12


@pytest.mark.parametrize(("override", "side_or_field"), [
    ({"armc": True}, "armc"),
    ({"obliquity": 90}, "obliquity"),
    ({"latitude": 91}, "latitude"),
    ({"sun_longitude": "NaN"}, "sun_longitude"),
    ({"left_system": ""}, "left_system"),
    ({"right_system": " "}, "right_system"),
    ({"right_system": HouseSystem.SOLAR_SIGN}, "right_system"),
    ({"right_system": HouseSystem.MAKRANSKY_SUNSHINE}, "right_system"),
    ({"right_latitude": 25}, "right_latitude"),
])
def test_house_comparison_rejects_invalid_figures(client, override, side_or_field):
    payload = {**_BASE, "left_system": HouseSystem.WHOLE_SIGN, "right_system": HouseSystem.PORPHYRY, **override}
    response = client.post(_PATH, json=payload)
    assert response.status_code == 422, response.text
    data = response.json()
    assert side_or_field in data["message"] or f"body.{side_or_field}" in (data.get("details") or {})
    assert "left" not in data and "right" not in data


def test_house_comparison_publishes_shared_geometry_schema(client):
    schema = client.app.openapi()
    operation = schema["paths"][_PATH]["post"]
    assert operation["requestBody"]["content"]["application/json"]["schema"]["$ref"].endswith("/HouseComparisonRequest")
    assert operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("/HouseComparisonResponse")
    models = schema["components"]["schemas"]
    request = models["HouseComparisonRequest"]
    assert set(request["required"]) == {"armc", "obliquity", "latitude", "left_system", "right_system"}
    deltas = models["HouseComparisonResponse"]["properties"]["cusp_deltas"]
    assert deltas["minItems"] == deltas["maxItems"] == 12
    assert deltas["items"]["exclusiveMinimum"] == -180
    assert deltas["items"]["maximum"] == 180
