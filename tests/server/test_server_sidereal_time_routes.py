"""HTTP and ERFA witnesses for sidereal time at explicit UT1 and TT."""

import math
from dataclasses import asdict

import pytest
from fastapi.testclient import TestClient

from moira import julian
from moira_server.app import create_app
from moira_server.dependencies import get_engine


pytestmark = pytest.mark.loopback
_PATH = "/v1/time/sidereal"
_EPOCH = {"jd_ut1": 2451545.25, "jd_tt": 2451545.25 + 64.0 / 86400}
_GREENWICH = {**_EPOCH, "mode": "mean", "reference": "greenwich"}


@pytest.fixture
def client():
    app = create_app()

    def unexpected_engine():
        pytest.fail("Sidereal time must be available without an ephemeris reader.")

    app.dependency_overrides[get_engine] = unexpected_engine
    return TestClient(app)


def _post(client, **fields):
    response = client.post(_PATH, json={**_GREENWICH, **fields})
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize("mode", ["mean", "apparent"])
@pytest.mark.parametrize("reference", ["greenwich", "local"])
def test_sidereal_time_matches_direct_engine(client, monkeypatch, mode, reference):
    def unexpected_delta_t(_jd):
        pytest.fail("The explicit TT epoch must bypass Delta-T conversion.")

    monkeypatch.setattr(julian, "ut_to_tt", unexpected_delta_t)
    longitude = -74.006 if reference == "local" else 0.0
    location = {"longitude_deg_east": longitude} if reference == "local" else {}
    result = _post(client, mode=mode, reference=reference, **location)
    truth = julian.local_sidereal_time_with_truth(
        _EPOCH["jd_ut1"], longitude, mode=mode, jd_tt=_EPOCH["jd_tt"],
    )

    assert result["request"] == {**_EPOCH, "mode": mode, "reference": reference, **location}
    assert result["sidereal_time_deg"] == truth.local_sidereal_time_deg
    assert result["provenance"] == asdict(truth)


@pytest.mark.parametrize("mode", ["mean", "apparent"])
def test_sidereal_time_uses_both_explicit_clocks_against_erfa(client, mode):
    erfa = pytest.importorskip("erfa")
    oracle = erfa.gmst06 if mode == "mean" else erfa.gst06a
    tolerance = 2e-7 if mode == "mean" else 1e-6
    longitude = 77.209
    angles = []
    for tt in (_EPOCH["jd_tt"], _EPOCH["jd_tt"] + 1):
        result = _post(
            client, mode=mode, reference="local", longitude_deg_east=longitude, jd_tt=tt,
        )
        expected = math.degrees(oracle(_EPOCH["jd_ut1"], 0, tt, 0)) + longitude
        angle = result["sidereal_time_deg"]
        assert abs(math.remainder(angle - expected, 360.0)) < tolerance
        assert result["provenance"]["jd_tt"] == tt
        angles.append(angle)

    # An exaggerated TT change isolates the TT terms from UT1 Earth rotation.
    assert abs(math.remainder(angles[1] - angles[0], 360.0)) > 1e-5
    later_ut1 = _EPOCH["jd_ut1"] + 0.125
    later = _post(client, mode=mode, jd_ut1=later_ut1)["sidereal_time_deg"]
    expected = math.degrees(oracle(later_ut1, 0, _EPOCH["jd_tt"], 0))
    assert abs(math.remainder(later - expected, 360.0)) < tolerance


@pytest.mark.parametrize("mode", ["mean", "apparent"])
def test_east_positive_longitude_and_wrap(client, mode):
    greenwich = _post(client, mode=mode)["sidereal_time_deg"]
    assert 0 < greenwich < 180
    rounded_seam = math.nextafter(-greenwich, -math.inf)
    for longitude in (0.0, 30.0, -30.0, -180.0, 180.0, -greenwich, rounded_seam):
        result = _post(client, mode=mode, reference="local", longitude_deg_east=longitude)
        angle = result["sidereal_time_deg"]
        assert 0 <= angle < 360
        assert abs(math.remainder(angle - (greenwich + longitude), 360.0)) < 1e-12


@pytest.mark.parametrize("required", ["jd_ut1", "jd_tt", "mode", "reference"])
def test_required_clock_inputs(client, required):
    payload = {key: value for key, value in _GREENWICH.items() if key != required}
    assert client.post(_PATH, json=payload).status_code == 422


@pytest.mark.parametrize(
    "fields",
    [
        {"mode": "true"},
        {"reference": "utc"},
        {"reference": "local"},
        {"longitude_deg_east": 0},
        {"reference": "local", "longitude_deg_east": 180.01},
        {"reference": "local", "longitude_deg_east": -180.01},
        {"reference": "local", "longitude_deg_east": True},
        {"jd_ut1": "2451545.25"},
        {"jd_tt": False},
        {"jd_tt": 40_000_001},
        {"jd_ut1": -40_000_001},
        {"jd_ut1": 1e300},
    ],
)
def test_rejects_invalid_clocks_and_meridians(client, fields):
    response = client.post(_PATH, json={**_GREENWICH, **fields})
    assert response.status_code == 422, response.text


def test_openapi_requires_both_timescales_and_discriminates_meridians(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200, response.text
    schema = response.json()
    request = schema["paths"][_PATH]["post"]["requestBody"]["content"]["application/json"]["schema"]
    assert request["discriminator"]["propertyName"] == "reference"
    variants = request["discriminator"]["mapping"]
    assert set(variants) == {"greenwich", "local"}
    for reference, path in variants.items():
        variant = schema["components"]["schemas"][path.rsplit("/", 1)[-1]]
        required = {"jd_ut1", "jd_tt", "mode", "reference"}
        if reference == "local":
            required.add("longitude_deg_east")
        assert set(variant["required"]) == required
        assert variant["additionalProperties"] is False
