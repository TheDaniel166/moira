from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient
import pytest

from moira.planets import planet_at
from moira.julian import jd_from_datetime, local_sidereal_time, utc_to_tt, utc_to_ut1
from moira.obliquity import nutation, true_obliquity

from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.network


@pytest.fixture
def client_with_engine(
    moira_engine,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        yield client


def _local_sidereal_time_for(jd_utc: float, longitude: float) -> float:
    jd_tt = utc_to_tt(jd_utc)
    jd_ut1 = utc_to_ut1(jd_utc)
    dpsi_deg, _ = nutation(jd_tt)
    obliquity_deg = true_obliquity(jd_tt)
    return local_sidereal_time(jd_ut1, longitude, dpsi_deg, obliquity_deg)


@pytest.mark.requires_ephemeris
def test_chart_route_matches_engine_selected_truth(client_with_engine: TestClient, moira_engine) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    direct = moira_engine.chart(dt, bodies=["Sun", "Moon"], include_nodes=True)

    response = client_with_engine.post(
        "/v1/chart",
        json={
            "dt": dt.isoformat(),
            "bodies": ["Sun", "Moon"],
            "include_nodes": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["jd_ut"] == pytest.approx(direct.jd_ut)
    assert body["obliquity"] == pytest.approx(direct.obliquity)
    assert body["delta_t"] == pytest.approx(direct.delta_t)
    assert body["planets"]["Sun"]["longitude"] == pytest.approx(direct.planets["Sun"].longitude)
    assert body["planets"]["Moon"]["speed"] == pytest.approx(direct.planets["Moon"].speed)
    assert body["nodes"]["True Node"]["longitude"] == pytest.approx(direct.nodes["True Node"].longitude)


@pytest.mark.requires_ephemeris
def test_chart_reduction_route_exposes_pipeline_truth(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    direct = moira_engine.chart(
        dt,
        bodies=["Sun", "Moon"],
        include_nodes=True,
        observer_lat=40.7128,
        observer_lon=-74.0060,
        observer_elev_m=10.0,
    )

    response = client_with_engine.post(
        "/v1/chart/reduction",
        json={
            "dt": dt.isoformat(),
            "bodies": ["Sun", "Moon"],
            "include_nodes": True,
            "observer_lat": 40.7128,
            "observer_lon": -74.0060,
            "observer_elev_m": 10.0,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["result"]["jd_ut"] == pytest.approx(direct.jd_ut)
    assert body["result"]["planets"]["Sun"]["longitude"] == pytest.approx(direct.planets["Sun"].longitude)
    assert body["result"]["planets"]["Moon"]["is_topocentric"] is True
    assert body["result"]["nodes"]["True Node"]["longitude"] == pytest.approx(direct.nodes["True Node"].longitude)
    assert body["reduction"]["engine_surface"] == "Moira.chart"
    assert body["reduction"]["source_vessel"] == "Chart"
    assert body["reduction"]["requested_bodies"] == ["Sun", "Moon"]
    assert body["reduction"]["returned_bodies"] == ["Sun", "Moon"]
    assert body["reduction"]["include_nodes_requested"] is True
    assert body["reduction"]["include_nodes_returned"] is True
    assert body["reduction"]["topocentric_requested"] is True
    assert body["reduction"]["observer"]["latitude"] == pytest.approx(40.7128)
    assert body["reduction"]["observer"]["longitude"] == pytest.approx(-74.0060)
    assert body["reduction"]["observer"]["local_sidereal_time_deg"] is not None
    assert "all_planets_at" in body["reduction"]["stage_sequence"]
    assert body["reduction"]["planet_reductions"]["Moon"]["topocentric_applied"] is True
    assert body["reduction"]["planet_reductions"]["Sun"]["center"] == "geocentric"
    assert body["reduction"]["node_reductions"]["True Node"]["source_surface"] == "moira.true_node"
    assert body["reduction"]["node_reductions"]["Mean Node"]["nutation"] is True
    assert (
        body["reduction"]["node_reductions"]["Mean Node"]["frame"]
        == "true_ecliptic_and_equinox_of_date"
    )
    assert (
        "iers_2003_mean_node_solution"
        in body["reduction"]["node_reductions"]["Mean Node"]["stage_sequence"]
    )
    assert (
        "iau_2000a_nutation_in_longitude"
        in body["reduction"]["node_reductions"]["Lilith"]["stage_sequence"]
    )


@pytest.mark.requires_ephemeris
def test_chart_reduction_route_admits_small_bodies(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    direct = moira_engine.chart(dt, bodies=["Ceres"], include_nodes=False)

    response = client_with_engine.post(
        "/v1/chart/reduction",
        json={
            "dt": dt.isoformat(),
            "bodies": ["Ceres"],
            "include_nodes": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["result"]["planets"]["Ceres"]["longitude"] == pytest.approx(direct.planets["Ceres"].longitude)
    assert body["result"]["planets"]["Ceres"]["latitude"] == pytest.approx(direct.planets["Ceres"].latitude)
    assert body["reduction"]["requested_bodies"] == ["Ceres"]
    assert body["reduction"]["returned_bodies"] == ["Ceres"]
    assert body["reduction"]["planet_reductions"]["Ceres"]["selection_surface"] == "chart.planets[body]"


@pytest.mark.requires_ephemeris
def test_planet_position_route_matches_engine_selected_truth(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    direct = moira_engine.chart(dt, bodies=["Mars"], include_nodes=False).planets["Mars"]

    response = client_with_engine.post(
        "/v1/positions/planet",
        json={
            "dt": dt.isoformat(),
            "body": "Mars",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Mars"
    assert body["longitude"] == pytest.approx(direct.longitude)
    assert body["latitude"] == pytest.approx(direct.latitude)
    assert body["speed"] == pytest.approx(direct.speed)
    assert body["retrograde"] is direct.retrograde


@pytest.mark.requires_ephemeris
def test_planet_position_route_preserves_topocentric_truth(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    jd_utc = jd_from_datetime(dt)
    jd_ut = utc_to_ut1(jd_utc)
    lst_deg = _local_sidereal_time_for(jd_utc, -74.0060)
    direct = planet_at(
        "Moon",
        jd_ut,
        reader=None,
        apparent=True,
        aberration=True,
        grav_deflection=True,
        nutation=True,
        observer_lat=40.7128,
        observer_lon=-74.0060,
        observer_elev_m=10.0,
        lst_deg=lst_deg,
    )

    response = client_with_engine.post(
        "/v1/positions/planet",
        json={
            "dt": dt.isoformat(),
            "body": "Moon",
            "observer_lat": 40.7128,
            "observer_lon": -74.0060,
            "observer_elev_m": 10.0,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Moon"
    assert body["is_topocentric"] is True
    assert body["longitude"] == pytest.approx(direct.longitude)
    assert body["latitude"] == pytest.approx(direct.latitude)
    assert body["distance_au"] == pytest.approx(direct.distance_au)


@pytest.mark.requires_ephemeris
def test_planet_position_reduction_route_exposes_pipeline_truth(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    jd_utc = jd_from_datetime(dt)
    jd_ut = utc_to_ut1(jd_utc)
    lst_deg = _local_sidereal_time_for(jd_utc, -74.0060)
    direct = planet_at(
        "Moon",
        jd_ut,
        reader=None,
        apparent=True,
        aberration=True,
        grav_deflection=True,
        nutation=True,
        observer_lat=40.7128,
        observer_lon=-74.0060,
        observer_elev_m=10.0,
        lst_deg=lst_deg,
    )

    response = client_with_engine.post(
        "/v1/positions/planet/reduction",
        json={
            "dt": dt.isoformat(),
            "body": "Moon",
            "observer_lat": 40.7128,
            "observer_lon": -74.0060,
            "observer_elev_m": 10.0,
            "apparent": True,
            "aberration": True,
            "grav_deflection": True,
            "nutation": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["result"]["longitude"] == pytest.approx(direct.longitude)
    assert body["result"]["is_topocentric"] is True
    assert body["reduction"]["engine_surface"] == "Moira.planet_at"
    assert body["reduction"]["source_vessel"] == "PlanetData"
    assert body["reduction"]["selection_surface"] == "planet_at"
    assert body["reduction"]["topocentric_requested"] is True
    assert body["reduction"]["topocentric_applied"] is True
    assert body["reduction"]["observer"]["latitude"] == pytest.approx(40.7128)
    assert body["reduction"]["observer"]["longitude"] == pytest.approx(-74.0060)
    assert body["reduction"]["observer"]["local_sidereal_time_deg"] is not None
    assert body["reduction"]["jd_ut"] == pytest.approx(jd_ut, abs=1.0e-12)
    assert body["reduction"]["stages"][-1]["name"] == "Topocentric diurnal aberration"
    assert "all_planets_at" in body["reduction"]["stage_sequence"]
    assert "planet_selection" in body["reduction"]["stage_sequence"]
    # New correction controls reflected in reduction (requested == applied for default full)
    assert body["reduction"]["apparent"] is True
    assert body["reduction"]["aberration"] is True
    assert body["reduction"]["grav_deflection"] is True
    assert body["reduction"]["nutation"] is True


@pytest.mark.requires_ephemeris
def test_planet_position_reduction_route_admits_small_bodies(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    direct = planet_at(
        "Ceres",
        jd_from_datetime(dt),
        reader=None,
        apparent=True,
        aberration=True,
        grav_deflection=True,
        nutation=True,
    )

    response = client_with_engine.post(
        "/v1/positions/planet/reduction",
        json={
            "dt": dt.isoformat(),
            "body": "Ceres",
            "apparent": True,
            "aberration": True,
            "grav_deflection": True,
            "nutation": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["result"]["name"] == "Ceres"
    assert body["result"]["longitude"] == pytest.approx(direct.longitude)
    assert body["result"]["latitude"] == pytest.approx(direct.latitude)
    assert body["reduction"]["engine_surface"] == "Moira.planet_at"
    assert body["reduction"]["selection_surface"] == "planet_at"
    assert body["reduction"]["apparent"] is True
    assert body["reduction"]["aberration"] is True


@pytest.mark.requires_ephemeris
def test_sky_position_route_matches_engine_selected_truth(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    direct = moira_engine.sky_position(dt, "Venus", 51.5, -0.1)

    response = client_with_engine.post(
        "/v1/positions/sky",
        json={
            "dt": dt.isoformat(),
            "body": "Venus",
            "latitude": 51.5,
            "longitude": -0.1,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Venus"
    assert body["right_ascension"] == pytest.approx(direct.right_ascension)
    assert body["declination"] == pytest.approx(direct.declination)
    assert body["azimuth"] == pytest.approx(direct.azimuth)
    assert body["altitude"] == pytest.approx(direct.altitude)


@pytest.mark.requires_ephemeris
def test_sky_position_reduction_route_exposes_pipeline_truth(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    direct = moira_engine.sky_position(dt, "Venus", 51.5, -0.1)

    response = client_with_engine.post(
        "/v1/positions/sky/reduction",
        json={
            "dt": dt.isoformat(),
            "body": "Venus",
            "latitude": 51.5,
            "longitude": -0.1,
            "aberration": True,
            "grav_deflection": True,
            "nutation": True,
            "refraction": True,
            "pressure_mbar": 1013.25,
            "temperature_c": 10.0,
            "relative_humidity": 0.0,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["result"]["right_ascension"] == pytest.approx(direct.right_ascension)
    assert body["result"]["declination"] == pytest.approx(direct.declination)
    assert body["reduction"]["engine_surface"] == "Moira.sky_position"
    assert body["reduction"]["source_vessel"] == "SkyPosition"
    assert body["reduction"]["observer"]["latitude"] == pytest.approx(51.5)
    assert body["reduction"]["observer"]["longitude"] == pytest.approx(-0.1)
    assert body["reduction"]["observer"]["local_sidereal_time_deg"] is not None
    assert body["reduction"]["refraction"] is True
    assert body["reduction"]["coordinate_frames"] == ["equatorial", "horizontal"]
    assert "horizontal_projection" in body["reduction"]["stage_sequence"]
    assert "optional_refraction" in body["reduction"]["stage_sequence"]
    # Refraction params from request, reflected (closing hardcode gap)
    assert body["reduction"]["pressure_mbar"] == 1013.25
    assert body["reduction"]["temperature_c"] == 10.0
    assert body["reduction"]["relative_humidity"] == 0.0


@pytest.mark.requires_ephemeris
def test_sky_position_routes_admit_small_bodies(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    direct = moira_engine.sky_position(dt, "Ceres", 51.5, -0.1)

    response = client_with_engine.post(
        "/v1/positions/sky",
        json={
            "dt": dt.isoformat(),
            "body": "Ceres",
            "latitude": 51.5,
            "longitude": -0.1,
        },
    )
    reduction_response = client_with_engine.post(
        "/v1/positions/sky/reduction",
        json={
            "dt": dt.isoformat(),
            "body": "Ceres",
            "latitude": 51.5,
            "longitude": -0.1,
            "aberration": True,
            "grav_deflection": True,
            "nutation": True,
            "refraction": True,
            "pressure_mbar": 1013.25,
            "temperature_c": 10.0,
            "relative_humidity": 0.0,
        },
    )

    assert response.status_code == 200
    assert reduction_response.status_code == 200

    body = response.json()
    reduction_body = reduction_response.json()
    assert body["name"] == "Ceres"
    assert body["right_ascension"] == pytest.approx(direct.right_ascension)
    assert body["declination"] == pytest.approx(direct.declination)
    assert body["azimuth"] == pytest.approx(direct.azimuth)
    assert body["altitude"] == pytest.approx(direct.altitude)
    assert reduction_body["result"]["name"] == "Ceres"
    assert reduction_body["result"]["right_ascension"] == pytest.approx(direct.right_ascension)
    assert reduction_body["result"]["declination"] == pytest.approx(direct.declination)
    assert reduction_body["reduction"]["engine_surface"] == "Moira.sky_position"


@pytest.mark.requires_ephemeris
def test_houses_route_matches_engine_selected_truth(client_with_engine: TestClient, moira_engine) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    direct = moira_engine.houses(dt, latitude=51.5, longitude=-0.1)

    response = client_with_engine.post(
        "/v1/houses",
        json={
            "dt": dt.isoformat(),
            "latitude": 51.5,
            "longitude": -0.1,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["system"] == direct.system
    assert body["effective_system"] == direct.effective_system
    assert body["asc"] == pytest.approx(direct.asc)
    assert body["mc"] == pytest.approx(direct.mc)
    assert body["cusps"][0] == pytest.approx(direct.cusps[0])


@pytest.mark.requires_ephemeris
def test_houses_route_exposes_governing_policy(client_with_engine: TestClient, moira_engine) -> None:
    """Policy echo is now present (robustness: the doctrine actually applied is visible)."""
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    response = client_with_engine.post(
        "/v1/houses",
        json={
            "dt": dt.isoformat(),
            "latitude": 51.5,
            "longitude": -0.1,
            "system": "PLAcidUS",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert "policy" in body
    assert body["policy"] is not None
    assert "unknown_system" in body["policy"]
    assert "polar_fallback" in body["policy"]


@pytest.mark.requires_ephemeris
def test_houses_reduction_route_exposes_doctrine_truth(client_with_engine: TestClient, moira_engine) -> None:
    """Dedicated reduction surface for houses (per audit: policy and reduction sibling for houses).

    Now exposes the *full* HousePolicy as a nested schema (rich polar fallback options documented
    via the enum-backed model) and richer truth including requested_policy and nested classification.
    """
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    response = client_with_engine.post(
        "/v1/houses/reduction",
        json={
            "dt": dt.isoformat(),
            "latitude": 51.5,
            "longitude": -0.1,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert "result" in body
    assert "reduction" in body
    red = body["reduction"]
    assert red["engine_surface"] == "Moira.houses"
    assert red["source_vessel"] == "HouseCusps"
    assert "applied_policy" in red
    assert isinstance(red.get("applied_policy"), dict)
    assert "unknown_system" in red["applied_policy"]
    assert "polar_fallback" in red["applied_policy"]
    assert red["fallback"] is not None
    assert "effective_system" in red

    # More fields in reduction truth: nested schemas for policy and classification
    # classification may be present
    if "classification" in red and red["classification"] is not None:
        cls = red["classification"]
        assert "family" in cls
        assert "cusp_basis" in cls
        assert "latitude_sensitive" in cls
        assert "polar_capable" in cls

    # requested_policy present (None for default case is fine)
    assert "requested_policy" in red


@pytest.mark.requires_ephemeris
def test_houses_policy_input_is_respected(client_with_engine: TestClient, moira_engine) -> None:
    """Input policy is accepted and the echoed policy reflects control (robustness for doctrine)."""
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    # Use strict policy (should still succeed for normal lat, but proves transport)
    response = client_with_engine.post(
        "/v1/houses",
        json={
            "dt": dt.isoformat(),
            "latitude": 51.5,
            "longitude": -0.1,
            "system": "placidus",
            "policy": {
                "unknown_system": "fallback_to_placidus",
                "polar_fallback": "raise",
            },
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["policy"]["polar_fallback"] == "raise"

    # Also verify reduction carries the full requested vs applied policy shapes (rich nested)
    red_resp = client_with_engine.post(
        "/v1/houses/reduction",
        json={
            "dt": dt.isoformat(),
            "latitude": 51.5,
            "longitude": -0.1,
            "system": "placidus",
            "policy": {
                "unknown_system": "fallback_to_placidus",
                "polar_fallback": "raise",
            },
        },
    )
    assert red_resp.status_code == 200
    red_body = red_resp.json()["reduction"]
    assert red_body["requested_policy"] is not None
    assert red_body["requested_policy"]["polar_fallback"] == "raise"
    assert red_body["applied_policy"]["polar_fallback"] == "raise"


@pytest.mark.requires_ephemeris
def test_houses_explicit_default_policy_preserves_ut1_numeric_path(
    client_with_engine: TestClient,
) -> None:
    payload = {
        "dt": "2000-01-01T12:00:00+00:00",
        "latitude": 51.5,
        "longitude": -0.1,
        "system": "P",
    }
    default_response = client_with_engine.post("/v1/houses", json=payload)
    explicit_response = client_with_engine.post(
        "/v1/houses",
        json={
            **payload,
            "policy": {
                "unknown_system": "fallback_to_placidus",
                "polar_fallback": "fallback_to_porphyry",
            },
        },
    )

    assert default_response.status_code == 200
    assert explicit_response.status_code == 200
    default_body = default_response.json()
    explicit_body = explicit_response.json()
    assert explicit_body["armc"] == pytest.approx(default_body["armc"], abs=1e-12)
    assert explicit_body["cusps"] == pytest.approx(default_body["cusps"], abs=1e-12)


@pytest.mark.parametrize(
    ("field", "value"),
    [("latitude", -90.0001), ("latitude", 90.0001), ("longitude", -180.0001), ("longitude", 180.0001)],
)
def test_houses_route_rejects_out_of_range_location(
    client_with_engine: TestClient,
    field: str,
    value: float,
) -> None:
    payload = {
        "dt": "2000-01-01T12:00:00+00:00",
        "latitude": 0.0,
        "longitude": 0.0,
        field: value,
    }

    response = client_with_engine.post("/v1/houses", json=payload)

    assert response.status_code == 422
    assert response.json()["error_code"] == "validation_error"


@pytest.mark.requires_ephemeris
def test_houses_polar_fallback_policies(client_with_engine: TestClient, moira_engine) -> None:
    """Exercise the FastAPI houses endpoints (compact and reduction) for polar fallback doctrine.

    Covers:
    - Default policy at supra-critical latitude (triggers fallback, echoes default polar_fallback).
    - RAISE policy at polar latitude (surfaces as 422 validation_error with engine's polar/raise message).
    - Reduction endpoint reports the applied polar_fallback policy.
    Uses koch at 70° (a system that remains polar-incapable under default doctrine).
    """
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    lat = 70.0  # well above critical latitude (~66.56°)
    lon = 0.0
    system = "koch"  # remains polar-incapable under default doctrine (clean fallback to porphyry)

    # Default policy at polar latitude: API should produce fallback=True and echo the engine default polar_fallback
    resp = client_with_engine.post(
        "/v1/houses",
        json={
            "dt": dt.isoformat(),
            "latitude": lat,
            "longitude": lon,
            "system": system,
        },
    )
    if resp.status_code != 200:
        print("DEFAULT POLAR ERROR BODY:", resp.json())
    assert resp.status_code == 200
    body = resp.json()
    assert body["system"] == "K"
    assert body["effective_system"] == "O"
    assert body["fallback"] is True
    assert body["policy"] is not None
    assert body["policy"]["polar_fallback"] == "fallback_to_porphyry"

    # RAISE at polar latitude must fail with proper error envelope (ValueError from engine -> 422)
    resp_raise = client_with_engine.post(
        "/v1/houses",
        json={
            "dt": dt.isoformat(),
            "latitude": lat,
            "longitude": lon,
            "system": system,
            "policy": {
                "unknown_system": "fallback_to_placidus",
                "polar_fallback": "raise",
            },
        },
    )
    assert resp_raise.status_code == 422
    err = resp_raise.json()
    assert err["error_code"] == "validation_error"
    msg = err.get("message", "").lower()
    assert "latitude" in msg or "polar" in msg or "raise" in msg

    # Reduction surface also respects and reports the polar fallback policy
    red_resp = client_with_engine.post(
        "/v1/houses/reduction",
        json={
            "dt": dt.isoformat(),
            "latitude": lat,
            "longitude": lon,
            "system": system,
        },
    )
    if red_resp.status_code != 200:
        print("REDUCTION DEFAULT POLAR ERROR BODY:", red_resp.json())
    assert red_resp.status_code == 200
    red = red_resp.json()["reduction"]
    assert red["applied_policy"]["polar_fallback"] == "fallback_to_porphyry"
    assert red["fallback"] is True


def test_phase_two_routes_reject_naive_datetimes_as_validation_failures(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/chart",
        json={"dt": "2000-01-01T12:00:00", "bodies": ["Sun"]},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "validation_error"
    assert body["category"] == "input_validation"
    assert "timezone-aware" in body["message"]


@pytest.mark.requires_ephemeris
def test_planet_position_route_rejects_invalid_body_with_validation_envelope(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/positions/planet",
        json={
            "dt": "2000-01-01T12:00:00+00:00",
            "body": "NotAPlanet",
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "validation_error"
    assert body["category"] == "input_validation"
    assert "NotAPlanet" in body["message"]
