"""Independent vector, ERFA and HTTP witnesses for supplied coordinates."""

import math
from dataclasses import asdict

import pytest
from fastapi.testclient import TestClient

from moira.coordinates import horizontal_to_equatorial_with_truth, transform_ecliptic_equatorial_with_truth
from moira_server.app import create_app
from moira_server.dependencies import get_engine


pytestmark = pytest.mark.loopback
_PATH = "/v1/coordinates/transform"
_EPS = 23.4392911
_ECLIPTIC = "ecliptic_to_equatorial"
_EQUATORIAL = "equatorial_to_ecliptic"
_HORIZONTAL = "horizontal_to_equatorial"


@pytest.fixture
def client():
    app = create_app()

    def unexpected_engine():
        pytest.fail("Supplied coordinates must be available without an ephemeris reader.")

    app.dependency_overrides[get_engine] = unexpected_engine
    return TestClient(app)


def _post(client, **payload):
    response = client.post(_PATH, json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def _angular_error(actual, expected):
    return abs(math.remainder(actual - expected, 360.0))


def _cartesian(longitude, latitude):
    lon, lat = map(math.radians, (longitude, latitude))
    return math.cos(lat) * math.cos(lon), math.cos(lat) * math.sin(lon), math.sin(lat)


@pytest.mark.parametrize(("lon", "lat", "obliquity"), [
    (123.4, -12.5, _EPS), (-0.001, 89.99999, 23.436), (481, 5, 0), (49, -33, 137),
])
def test_ecliptic_equatorial_rotation_matches_cartesian_and_round_trips(client, lon, lat, obliquity):
    forward = _post(
        client, transform=_ECLIPTIC, ecliptic_longitude_deg=lon,
        ecliptic_latitude_deg=lat, obliquity_deg=obliquity,
    )
    assert forward == asdict(transform_ecliptic_equatorial_with_truth(lon, lat, obliquity, transform=_ECLIPTIC))
    x, y, z = _cartesian(lon, lat)
    eps = math.radians(obliquity)
    expected = (x, y * math.cos(eps) - z * math.sin(eps), y * math.sin(eps) + z * math.cos(eps))
    rotated = _cartesian(forward["right_ascension_deg"], forward["declination_deg"])
    assert rotated == pytest.approx(expected, abs=1e-14)

    reverse = _post(
        client, transform=_EQUATORIAL, right_ascension_deg=forward["right_ascension_deg"],
        declination_deg=forward["declination_deg"], obliquity_deg=obliquity,
    )
    assert reverse == asdict(transform_ecliptic_equatorial_with_truth(
        forward["right_ascension_deg"], forward["declination_deg"], obliquity, transform=_EQUATORIAL,
    ))
    assert _cartesian(reverse["ecliptic_longitude_deg"], reverse["ecliptic_latitude_deg"]) == pytest.approx(
        (x, y, z), abs=1e-14,
    )


@pytest.mark.parametrize(("sign", "pole_longitude"), [(1, 90), (-1, 270)])
def test_celestial_pole_angle_is_null_and_reusable_as_input(client, sign, pole_longitude):
    pole_latitude = sign * (90 - _EPS)
    forward = _post(
        client, transform=_ECLIPTIC, ecliptic_longitude_deg=pole_longitude,
        ecliptic_latitude_deg=pole_latitude, obliquity_deg=_EPS,
    )
    assert forward["right_ascension_deg"] is None
    assert forward["declination_deg"] == sign * 90
    reverse = _post(client, transform=_EQUATORIAL, declination_deg=sign * 90, obliquity_deg=_EPS)
    assert reverse["right_ascension_deg"] is None
    assert _angular_error(reverse["ecliptic_longitude_deg"], pole_longitude) < 1e-12
    assert reverse["ecliptic_latitude_deg"] == pytest.approx(pole_latitude, abs=1e-12)
    near = _post(
        client, transform=_ECLIPTIC, ecliptic_longitude_deg=pole_longitude,
        ecliptic_latitude_deg=pole_latitude - sign * 1e-8, obliquity_deg=_EPS,
    )
    assert near["right_ascension_deg"] is not None
    assert abs(near["declination_deg"]) < 90


def test_ecliptic_pole_longitude_is_null_and_reusable_as_input(client):
    reverse = _post(
        client, transform=_EQUATORIAL, right_ascension_deg=270,
        declination_deg=90 - _EPS, obliquity_deg=_EPS,
    )
    assert reverse["ecliptic_longitude_deg"] is None
    assert reverse["ecliptic_latitude_deg"] == 90
    forward = _post(
        client, transform=_ECLIPTIC, ecliptic_longitude_deg=55,
        ecliptic_latitude_deg=90, obliquity_deg=_EPS,
    )
    assert forward["ecliptic_longitude_deg"] is None
    assert _angular_error(forward["right_ascension_deg"], 270) < 1e-12
    assert forward["declination_deg"] == pytest.approx(90 - _EPS, abs=1e-12)


@pytest.mark.parametrize(("az", "alt", "lst", "lat"), [
    (115, -34, 271, -33.9), (361, 25, -1, 51.5), (90, 0, 270, 0),
    (120, 27, 100, 90), (120, 27, 100, -90),
    (120, 27, 100, 89.999999), (120, 27, 100, -89.999999),
])
def test_horizontal_inverse_matches_erfa_at_supplied_meridian(client, az, alt, lst, lat):
    erfa = pytest.importorskip("erfa")
    result = _post(
        client, transform=_HORIZONTAL, azimuth_deg=az, altitude_deg=alt,
        local_sidereal_time_deg=lst, observer_latitude_deg=lat,
    )
    assert result == asdict(horizontal_to_equatorial_with_truth(az, alt, lst, lat))
    h, d = erfa.ae2hd(*map(math.radians, (az, alt, lat)))
    assert _angular_error(result["hour_angle_deg"], math.degrees(h)) < 1e-11
    assert _angular_error(result["right_ascension_deg"], lst - math.degrees(h)) < 1e-11
    assert abs(result["declination_deg"] - math.degrees(d)) < 1e-11
    az_back, alt_back = erfa.hd2ae(
        *map(math.radians, (result["hour_angle_deg"], result["declination_deg"], lat))
    )
    assert _angular_error(az, math.degrees(az_back)) < 1e-11
    assert abs(alt - math.degrees(alt_back)) < 1e-11


@pytest.mark.parametrize(("alt", "lat", "expected_dec", "expected_ra"), [
    (90, 40, 40, 100), (-90, 40, -40, 280), (90, 90, 90, None), (90, -90, -90, None),
])
def test_vertical_direction_has_undefined_azimuth(client, alt, lat, expected_dec, expected_ra):
    payload = {
        "transform": _HORIZONTAL, "altitude_deg": alt,
        "local_sidereal_time_deg": 100, "observer_latitude_deg": lat,
    }
    result = _post(client, **payload)
    assert result == _post(client, azimuth_deg=84, **payload)
    assert result["azimuth_deg"] is None
    assert result["declination_deg"] == pytest.approx(expected_dec, abs=1e-12)
    if expected_ra is None:
        assert result["right_ascension_deg"] is None
        assert result["hour_angle_deg"] is None
    else:
        assert _angular_error(result["right_ascension_deg"], expected_ra) < 1e-12


@pytest.mark.parametrize(("az", "alt", "expected_dec"), [(0, 40, 90), (180, -40, -90)])
def test_celestial_pole_from_nonvertical_horizon_direction(client, az, alt, expected_dec):
    result = _post(
        client, transform=_HORIZONTAL, azimuth_deg=az, altitude_deg=alt,
        local_sidereal_time_deg=100, observer_latitude_deg=40,
    )
    assert result["azimuth_deg"] == az
    assert result["declination_deg"] == expected_dec
    assert result["right_ascension_deg"] is None
    assert result["hour_angle_deg"] is None


@pytest.mark.parametrize("payload", [
    {"transform": "equatorial_to_horizontal"},
    {"transform": _ECLIPTIC, "ecliptic_latitude_deg": 0, "obliquity_deg": _EPS},
    {"transform": _EQUATORIAL, "declination_deg": 0, "obliquity_deg": _EPS},
    {"transform": _ECLIPTIC, "ecliptic_longitude_deg": 0, "ecliptic_latitude_deg": 91, "obliquity_deg": 23},
    {"transform": _EQUATORIAL, "right_ascension_deg": 0, "declination_deg": -91, "obliquity_deg": 23},
    {"transform": _ECLIPTIC, "ecliptic_longitude_deg": 0, "ecliptic_latitude_deg": 0, "obliquity_deg": 181},
    {"transform": _ECLIPTIC, "ecliptic_longitude_deg": "0", "ecliptic_latitude_deg": 0, "obliquity_deg": 23},
    {"transform": _HORIZONTAL, "local_sidereal_time_deg": 0, "observer_latitude_deg": 0, "altitude_deg": 0},
    {"transform": _HORIZONTAL, "local_sidereal_time_deg": True, "observer_latitude_deg": 0,
     "altitude_deg": 0, "azimuth_deg": 0},
    {"transform": _HORIZONTAL, "local_sidereal_time_deg": 0, "observer_latitude_deg": -91,
     "altitude_deg": 0, "azimuth_deg": 0},
    {"transform": _HORIZONTAL, "local_sidereal_time_deg": 0, "observer_latitude_deg": 0,
     "altitude_deg": 91, "azimuth_deg": 0},
    {"transform": _HORIZONTAL, "local_sidereal_time_deg": 0, "observer_latitude_deg": 0,
     "altitude_deg": 0, "azimuth_deg": 0, "jd_ut1": 2451545},
])
def test_rejects_ambiguous_or_invalid_requests(client, payload):
    response = client.post(_PATH, json=payload)
    assert response.status_code == 422, response.text


def test_openapi_discriminates_all_supplied_transform_inputs_and_results(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200, response.text
    schema = response.json()
    route = schema["paths"][_PATH]["post"]
    assert route["tags"] == ["coordinates"]
    request = route["requestBody"]["content"]["application/json"]["schema"]
    result = route["responses"]["200"]["content"]["application/json"]["schema"]
    for contract in (request, result):
        assert contract["discriminator"]["propertyName"] == "transform"
        assert set(contract["discriminator"]["mapping"]) == {_ECLIPTIC, _EQUATORIAL, _HORIZONTAL}
