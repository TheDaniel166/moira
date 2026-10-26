"""Explicit model-policy transport, source receipts and real geometric Arta inputs."""

from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

from moira.hypothetical import arta_osculating_set_at
from moira.orbits import OrbitalFrame
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.dependencies import get_engine

pytestmark = pytest.mark.loopback

POLICY = dict(source_equinox_jd_tt=2451545.0, timescale="TT", epoch_hour=0.0, year_days=365.25)
BASE_ORBIT = dict(epoch_jd=2451545.0, frame="J2000_ECLIPTIC")


@pytest.fixture
def client(monkeypatch):
    engine = SimpleNamespace(_reader=None)
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: engine)
    app = create_app(ServerConfig(docs_enabled=False, prewarm_enabled=False))
    app.dependency_overrides[get_engine] = lambda: engine
    with TestClient(app) as result:
        yield result


def test_catalog_and_supplied_arta_keep_fourfold_identity(client):
    catalog = client.get("/v1/hypothetical/catalog")
    assert catalog.status_code == 200 and catalog.json()["count"] == 11
    arta = client.post("/v1/hypothetical/arta/from-longitudes", json={
        "lunar_node": 17, "lunar_apogee": 31, "solar_apogee": 211,
        "input_model": "supplied_mean", "frame": "common_source_frame",
    })
    assert arta.status_code == 200
    assert arta.json()["longitudes"] == [17, 107, 197, 287]
    assert arta.json()["symbol"] == "\u2bdf"
    assert "longitude" not in arta.json()


def test_selena_and_proserpina_preserve_selected_anchor_clock_and_variant(client):
    selena = client.post("/v1/hypothetical/selena", json={
        "epoch_jd": 2451545.0, "anchor_jd": 2451545.0, "anchor_longitude": 123.5,
        "year_days": 365.25, "timescale": "TT", "frame": "selected_tropical_frame",
    })
    assert selena.status_code == 200 and selena.json()["longitude"] == 123.5
    assert selena.json()["timescale"] == "TT"
    assert selena.json()["parameters"] == [["anchor_jd", 2451545], ["anchor_longitude", 123.5], ["year_days", 365.25]]
    assert "distance_au" not in selena.json()
    proserpina = client.post("/v1/hypothetical/proserpina", json={
        "epoch_jd": 2415020.5, "rule": "abramov_calendar", "timescale": "UT1", "frame": "declared_source_frame",
    })
    assert proserpina.status_code == 200
    assert proserpina.json()["longitude"] == 170.73
    assert proserpina.json()["model"] == "abramov_calendar"
    assert proserpina.json()["symbol"] == "\u2bd8"


@pytest.mark.parametrize("body,center", [
    (dict(model="waldemath_koch_quoted_2006", source_equinox_jd_tt=2414291.0,
          berlin_local_minus_ut1_hours=0.8933333), "EARTH"),
    (dict(model="weston_stahl_1968", source_equinox_jd_tt=2415020.0, year_days=365.25), "SUN"),
    (dict(model="harrington_1988", policy=POLICY), "SUN"),
    (dict(model="adams_1846_second_hypothesis", policy=POLICY,
          uranus_semimajor_axis_au=19.18, uranus_sidereal_period_days=30688), "SUN"),
    (dict(model="leverrier_1846_gould_1850", policy=POLICY), "SUN"),
])
def test_named_orbits_round_trip_full_source_policy(client, body, center):
    response = client.post("/v1/hypothetical/orbit", json=dict(BASE_ORBIT, **body))
    assert response.status_code == 200
    result = response.json()
    assert result["distance_au"] > 0
    assert len(result["vector_au"]) == 3
    assert result["reduction"] == "geometric_no_light_time_no_aberration"
    source = result["source_orbit"]
    assert source["model"] == body["model"] and source["center"] == center
    assert source["source_url"] and source["source_location"] and source["realization"]
    assert "naif_id" not in source
    if "policy" in body:
        assert source["source_equinox_jd_tt"] == POLICY["source_equinox_jd_tt"]
        assert source["timescale"] == POLICY["timescale"]


@pytest.mark.parametrize("path,body", [
    ("selena", {"epoch_jd": 2451545}),
    ("selena", dict(epoch_jd=True, anchor_jd=2451545, anchor_longitude=0,
                    year_days=365.25, timescale="TT", frame="x")),
    ("proserpina", dict(epoch_jd=2451545, rule="Proserpina", timescale="TT", frame="x")),
    ("proserpina", dict(epoch_jd=2451545, rule="abramov_calendar", timescale="UTC", frame="x")),
    ("arta/from-longitudes", dict(lunar_node=1, lunar_apogee=2, solar_apogee=3)),
    ("arta/osculating", dict(jd_ut=True, frame="J2000_ECLIPTIC")),
    ("orbit", dict(BASE_ORBIT, model="Vulcan")),
    ("orbit", dict(BASE_ORBIT, model="harrington_1988")),
    ("orbit", dict(BASE_ORBIT, model="harrington_1988", policy=dict(POLICY, epoch_hour=True))),
    ("orbit", dict(BASE_ORBIT, model="weston_stahl_1968", source_equinox_jd_tt=2451545,
                   year_days=365.25, unrelated_override=1)),
])
def test_missing_or_ambiguous_policies_reject_with_standard_envelope(client, path, body):
    response = client.post(f"/v1/hypothetical/{path}", json=body)
    assert response.status_code == 422
    result = response.json()
    assert result["category"] == "input_validation"
    assert result["request_id"] == response.headers["X-Request-ID"]


def test_arta_requires_instance_kernel_but_scenario_does_not(client):
    arta = client.post("/v1/hypothetical/arta/osculating", json={"jd_ut": 2451545, "frame": "J2000_ECLIPTIC"})
    assert arta.status_code == 503
    assert arta.json()["error_code"] == "kernel_not_ready"
    scenario = client.post("/v1/hypothetical/planet-nine-scenario", json={
        "true_anomaly_deg": 0, "source_equinox_jd_tt": 2451545,
    })
    assert scenario.status_code == 200 and scenario.json()["distance_au"] == pytest.approx(280)
    assert "epoch_jd" not in scenario.json()


@pytest.mark.requires_ephemeris
def test_real_arta_transport_retains_both_kernel_receipts(client, moira_engine):
    client.app.dependency_overrides[get_engine] = lambda: moira_engine
    response = client.post("/v1/hypothetical/arta/osculating", json={
        "jd_ut": 2451545, "frame": "TRUE_ECLIPTIC_OF_DATE",
    })
    assert response.status_code == 200
    body = response.json()
    expected = arta_osculating_set_at(2451545, frame=OrbitalFrame.TRUE_ECLIPTIC_OF_DATE,
                                       reader=moira_engine._reader)
    assert body["points"]["longitudes"] == list(expected.points.longitudes)
    for name, center, body_id in [("lunar_elements", "EARTH", 301), ("earth_elements", "SUN", 399)]:
        assert body[name]["center"] == center
        assert body[name]["body"]["naif_id"] == body_id
        assert body[name]["provenance"]["state_source"]["legs"]
        assert body[name]["frame"] == "TRUE_ECLIPTIC_OF_DATE"
    assert body["points"]["solar_apogee"] == body["earth_elements"]["pericenter_ecliptic_lon_deg"]


def test_openapi_preserves_discriminated_union_and_required_scientific_choices(client):
    schema = client.app.openapi()
    body = schema["paths"]["/v1/hypothetical/orbit"]["post"]["requestBody"]["content"]["application/json"]["schema"]
    assert body["discriminator"]["propertyName"] == "model"
    assert len(body["oneOf"]) == 5
    selena = schema["components"]["schemas"]["SelenaRequest"]
    assert set(selena["required"]) == {"epoch_jd", "anchor_jd", "anchor_longitude", "year_days", "timescale", "frame"}
    assert selena["additionalProperties"] is False
    assert len([p for p in schema["paths"] if p.startswith("/v1/hypothetical/")]) == 7
