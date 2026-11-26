"""Dated and static house parity for caller-supplied anchors and zodiac offset."""

from datetime import datetime
import math

import pytest
from fastapi.testclient import TestClient

from moira import houses, planets
from moira.constants import HouseSystem
from moira.julian import jd_from_datetime, ut_to_tt, utc_to_ut1
from moira.obliquity import true_obliquity
from moira.spk_reader import get_active_reader
from moira_server.app import create_app
from moira_server.dependencies import get_engine


pytestmark = [pytest.mark.loopback, pytest.mark.requires_ephemeris]
_DATED_PATHS = ("/v1/houses", "/v1/houses/reduction")
_BASE = {
    "dt": "2000-01-01T07:00:00-05:00",
    "latitude": 40.0,
    "longitude": -74.006,
    "include_boundary_geometry": True,
}
_JD_UT1 = utc_to_ut1(jd_from_datetime(datetime.fromisoformat(_BASE["dt"])))
_ANCHORS = ("sun_longitude", "sun_declination", "ayanamsa_offset")


@pytest.fixture
def client(moira_engine):
    app = create_app()
    app.dependency_overrides[get_engine] = lambda: moira_engine
    return TestClient(app)


def _post(client, path, payload):
    response = client.post(path, json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def _dated_figure(client, payload):
    compact = _post(client, _DATED_PATHS[0], payload)
    full = _post(client, _DATED_PATHS[1], payload)
    truth = compact.pop("computation_truth")
    assert compact == full["result"]
    assert truth == full["reduction"]
    assert truth["engine_surface"] == "Moira.houses"
    assert truth["normalized_jd_ut"] == _JD_UT1
    return compact, truth


def _static_figure(client, dated, payload, **resolved):
    obliquity = dated["boundary_geometry"]["obliquity_deg"]
    assert obliquity == pytest.approx(true_obliquity(ut_to_tt(_JD_UT1)), abs=1e-12)
    return _post(client, "/v1/houses/armc", {
        **{name: payload[name] for name in ("latitude", "system", "policy", *_ANCHORS) if name in payload},
        "armc": dated["armc"],
        "obliquity": obliquity,
        "include_boundary_geometry": True,
        **resolved,
    })


@pytest.mark.parametrize(("system", "anchors", "expected_system", "extra"), [
    ("Solar Sign", {"sun_longitude": 7, "ayanamsa_offset": 24}, HouseSystem.SOLAR_SIGN, {}),
    ("Sunshine", {"sun_longitude": 0}, HouseSystem.SUNSHINE, {}),
    ("Makransky Sunshine", {"sun_declination": 0}, HouseSystem.MAKRANSKY_SUNSHINE, {}),
    ("Whole Sign", {"ayanamsa_offset": -12.125}, HouseSystem.WHOLE_SIGN, {}),
    (
        "Koch", {"ayanamsa_offset": 24}, HouseSystem.WHOLE_SIGN,
        {"latitude": 80, "policy": {"polar_fallback": "fallback_to_whole_sign"}},
    ),
])
def test_dated_anchors_match_static_armc_without_solar_resolution(
    client, monkeypatch, system, anchors, expected_system, extra,
):
    def unexpected_solar_read(*_args, **_kwargs):
        pytest.fail("Caller-supplied solar anchors must bypass solar ephemeris resolution.")

    monkeypatch.setattr(houses, "_solar_house_anchor_longitude", unexpected_solar_read)
    monkeypatch.setattr(planets, "planet_at", unexpected_solar_read)
    payload = {**_BASE, "system": system, **anchors, **extra}
    dated, truth = _dated_figure(client, payload)
    assert dated == _static_figure(client, dated, payload)
    assert dated["effective_system"] == truth["effective_system"] == expected_system
    assert dated["boundary_geometry"]["zodiac_offset_deg"] == anchors.get("ayanamsa_offset", 0)

    if expected_system == HouseSystem.SOLAR_SIGN:
        assert dated["cusps"][0] == 330
    elif expected_system == HouseSystem.WHOLE_SIGN:
        assert dated["cusps"][0] == 30 * math.floor(dated["asc"] / 30)
    if system == "Koch":
        assert dated["fallback"] and truth["fallback"]
        assert dated["fallback_reason"] == truth["fallback_reason"]


@pytest.mark.parametrize(("system", "field"), [
    ("Solar Sign", "sun_longitude"), ("Makransky Sunshine", "sun_declination"),
])
def test_omitted_solar_values_use_the_serving_reader(client, moira_engine, monkeypatch, system, field):
    planet_at = planets.planet_at
    reader = moira_engine._reader
    seen = []

    def record_reader(jd_ut1):
        assert get_active_reader() is reader
        seen.append(jd_ut1)

    if field == "sun_longitude":
        expected = planet_at("Sun", _JD_UT1, reader=reader).longitude
        resolve_longitude = houses._solar_house_anchor_longitude

        def resolve(jd_ut1):
            record_reader(jd_ut1)
            return resolve_longitude(jd_ut1)

        monkeypatch.setattr(houses, "_solar_house_anchor_longitude", resolve)
    else:
        sun = planet_at("Sun", _JD_UT1, frame="cartesian", reader=reader)
        expected = math.degrees(math.atan2(sun.z, math.hypot(sun.x, sun.y)))

        def resolve(body, jd_ut1, *, frame):
            assert body == "Sun" and frame == "cartesian"
            record_reader(jd_ut1)
            return planet_at(body, jd_ut1, frame=frame)

        monkeypatch.setattr(planets, "planet_at", resolve)

    payload = {**_BASE, "system": system, "ayanamsa_offset": 24}
    dated, _ = _dated_figure(client, payload)
    assert dated == _static_figure(client, dated, payload, **{field: expected})
    assert seen == [_JD_UT1, _JD_UT1]


def test_offset_shifts_quadrant_labels_and_preserves_physical_boundaries(client):
    payload = {**_BASE, "system": "Campanus"}
    tropical, _ = _dated_figure(client, payload)
    offset = 24.5
    shifted, _ = _dated_figure(client, {**payload, "ayanamsa_offset": offset})
    assert shifted["armc"] == tropical["armc"]
    assert shifted["boundary_geometry"]["zodiac_offset_deg"] == offset
    for before, after in zip(tropical["cusps"], shifted["cusps"], strict=True):
        assert abs(math.remainder(after - before + offset, 360)) < 1e-10
    for before, after in zip(
        tropical["boundary_geometry"]["boundaries"], shifted["boundary_geometry"]["boundaries"], strict=True,
    ):
        assert after["anchor_direction"] == before["anchor_direction"]
        assert after["plane_normal"] == before["plane_normal"]


@pytest.mark.parametrize("path", _DATED_PATHS)
def test_explicit_nulls_preserve_default_dated_result(client, path):
    payload = {**_BASE, "system": "Placidus"}
    assert _post(client, path, payload) == _post(client, path, {
        **payload, **dict.fromkeys(_ANCHORS),
    })


@pytest.mark.parametrize("path", _DATED_PATHS)
@pytest.mark.parametrize(("fields", "detail"), [
    ({"sun_longitude": "0"}, "sun_longitude"),
    ({"sun_declination": True}, "sun_declination"),
    ({"ayanamsa_offset": "24"}, "ayanamsa_offset"),
    ({"system": "Makransky Sunshine", "sun_declination": 90}, "declination"),
    ({"time_unknown": True, "ayanamsa_offset": 24}, "unknown birth time"),
    (
        {"latitude": 80, "system": "Koch", "ayanamsa_offset": 24, "policy": {"polar_fallback": "raise"}},
        "critical latitude",
    ),
])
def test_invalid_anchors_and_existing_rejections_are_422(client, path, fields, detail):
    response = client.post(path, json={**_BASE, **fields})
    assert response.status_code == 422, response.text
    assert detail in response.text.lower()


def test_dated_house_openapi_lists_optional_anchor_fields(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200, response.text
    schema = response.json()
    for path in _DATED_PATHS:
        request = schema["paths"][path]["post"]["requestBody"]["content"]["application/json"]["schema"]
        model = schema["components"]["schemas"][request["$ref"].rsplit("/", 1)[-1]]
        for name in _ANCHORS:
            assert model["properties"][name]["anyOf"] == [{"type": "number"}, {"type": "null"}]
            assert name not in model["required"]
