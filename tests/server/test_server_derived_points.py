"""Derived-point discovery, strict inputs and complete source-receipt transport."""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from moira.derived_points import baker_vulcan_at, osculating_priapus, second_focus_from_elements
from moira.orbits import OrbitalCenterNotAllowedError, OrbitShape
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.dependencies import get_engine
from tests.server.test_server_orbits_routes import _strict_elements

pytestmark = pytest.mark.loopback


@pytest.fixture
def client(monkeypatch):
    engine = SimpleNamespace(_reader=object())
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: engine)
    app = create_app(ServerConfig(docs_enabled=False, prewarm_enabled=False))
    app.dependency_overrides[get_engine] = lambda: engine
    # A stub engine keeps these transport contracts independent of resources.
    with TestClient(app) as result:
        yield result


def test_catalog_and_kernel_free_computations(client, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("kernel-free endpoints must not request an engine")

    client.app.dependency_overrides[get_engine] = forbidden
    response = client.get("/v1/derived-points/catalog")
    assert response.status_code == 200
    assert response.json()["count"] == 4
    assert {row["id"] for row in response.json()["points"]} == {
        "baker_vulcan", "mean_priapus", "osculating_priapus", "orbital_second_focus",
    }
    baker = client.post("/v1/derived-points/baker-vulcan/from-longitudes", json={
        "sun_longitude": 359, "mercury_longitude": 10,
    })
    assert baker.status_code == 200
    assert baker.json()["longitude"] == 7
    assert baker.json()["kernel_identity"] is None
    assert "distance_au" not in baker.json() and "speed" not in baker.json()
    mean = client.post("/v1/derived-points/priapus/mean", json={"jd_ut": 2451545, "nutation": False})
    assert mean.status_code == 200
    assert mean.json()["model"] == "mean_priapus"
    assert mean.json()["frame"] == "mean_ecliptic_and_equinox_of_date"


@pytest.mark.parametrize("path,body", [
    ("baker-vulcan", {"jd_ut": True}),
    ("priapus/mean", {"jd_ut": "2451545"}),
    ("priapus/mean", {"jd_ut": 2451545, "nutation": "false"}),
    ("priapus/osculating", {"jd_ut": False}),
    ("baker-vulcan/from-longitudes", {"sun_longitude": True, "mercury_longitude": 20}),
    ("baker-vulcan/from-longitudes", {"sun_longitude": 0, "mercury_longitude": 180}),
    ("second-focus", {"body": True, "jd_ut": 2451545, "center": "SUN", "frame": "J2000_ECLIPTIC"}),
    ("second-focus", {"body": " ", "jd_ut": 2451545, "center": "SUN", "frame": "J2000_ECLIPTIC"}),
    ("second-focus", {"body": "Earth", "jd_ut": 2451545}),
    ("second-focus", {"body": "Earth", "jd_ut": 2451545, "center": "Mars", "frame": "J2000_ECLIPTIC"}),
    ("priapus/osculating", {"jd_ut": 2451545, "model": "Selena"}),
])
def test_invalid_requests_use_standard_error_envelope(client, path, body):
    response = client.post(f"/v1/derived-points/{path}", json=body)
    assert response.status_code == 422
    error = response.json()
    assert error["category"] == "input_validation"
    assert error["request_id"] == response.headers["X-Request-ID"]


@pytest.mark.parametrize("shape,e,a,status", [
    (OrbitShape.ELLIPTIC, 0.4, 2.0, "DEFINED"),
    (OrbitShape.ELLIPTIC, 0.0, 2.0, "COINCIDENT_FOCI"),
    (OrbitShape.HYPERBOLIC, 1.5, -2.0, "NON_ELLIPTIC"),
])
def test_second_focus_preserves_full_typed_source_receipt(client, monkeypatch, shape, e, a, status):
    source = _strict_elements("Earth", 2451545, shape=shape,
                              eccentricity=e, semi_major_axis_au=a)
    if e == 0:
        source = replace(source, pericenter_ecliptic_lon_deg=None, pericenter_ecliptic_lat_deg=None)
    result = second_focus_from_elements(source)
    calls = []

    def compute(*args, **kwargs):
        calls.append((args, kwargs))
        return result

    monkeypatch.setattr("moira_server.services.derived_points.orbital_second_focus", compute)
    response = client.post("/v1/derived-points/second-focus", json={
        "body": 399, "jd_ut": 2451545, "center": "SUN", "frame": "J2000_ECLIPTIC",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == status
    assert body["origin"] == "selected_central_focus"
    actual = body["source_elements"]
    assert actual["body"]["naif_id"] == 399
    assert actual["center"] == "SUN" and actual["frame"] == "J2000_ECLIPTIC"
    assert actual["epoch_tdb"] == source.epoch_tdb
    receipt = actual["provenance"]
    assert receipt["gravity"]["gm_km3_s2"] == source.provenance.gravity.gm_km3_s2
    assert receipt["state_source"]["legs"][0]["kernel_sha256"] == "a" * 64
    assert receipt["singularity_thresholds"]["policy"] == source.provenance.singularity_thresholds.policy
    assert calls[0][0] == (399, 2451545)
    assert calls[0][1]["reader"] is client.app.dependency_overrides[get_engine]()._reader


def test_openapi_names_explicit_center_frame_and_models(client):
    schema = client.app.openapi()
    request = schema["components"]["schemas"]["SecondFocusRequest"]
    assert set(request["required"]) == {"body", "jd_ut", "center", "frame"}
    tag = next(tag for tag in schema["tags"] if tag["name"] == "derived-points")
    assert tag["x-family"] == "catalogs"
    assert len([path for path in schema["paths"] if path.startswith("/v1/derived-points/")]) == 6


def test_missing_reader_does_not_fabricate_a_symbolic_or_lunar_result(client, monkeypatch):
    client.app.dependency_overrides[get_engine] = lambda: SimpleNamespace(_reader=None)
    monkeypatch.setattr("moira.derived_points.get_active_reader", lambda: None)
    for path in ("baker-vulcan", "priapus/osculating"):
        response = client.post(f"/v1/derived-points/{path}", json={"jd_ut": 2451545})
        assert response.status_code == 503
        assert response.json()["category"] == "kernel_readiness"
        assert response.json()["error_code"] == "kernel_not_ready"
        assert "longitude" not in response.json()


def test_second_focus_retains_structured_core_failure(client, monkeypatch):
    def fail(*args, **kwargs):
        raise OrbitalCenterNotAllowedError("Mars", "EARTH", ("SUN",))

    monkeypatch.setattr("moira_server.services.derived_points.orbital_second_focus", fail)
    response = client.post("/v1/derived-points/second-focus", json={
        "body": "Mars", "jd_ut": 2451545, "center": "EARTH", "frame": "J2000_ECLIPTIC",
    })
    assert response.status_code == 422
    assert response.json()["details"] == {"body": "Mars", "center": "EARTH", "allowed_centers": ["SUN"]}


@pytest.mark.requires_ephemeris
def test_kernel_bound_routes_with_real_engine(client, moira_engine):
    client.app.dependency_overrides[get_engine] = lambda: moira_engine
    jd = 2451545.0
    baker = client.post("/v1/derived-points/baker-vulcan", json={"jd_ut": jd})
    assert baker.status_code == 200
    expected = baker_vulcan_at(jd, reader=moira_engine._reader)
    assert baker.json()["longitude"] == expected.longitude
    assert baker.json()["kernel_identity"] == expected.kernel_identity
    assert baker.json()["epoch_tdb"] == expected.epoch_tdb

    priapus = client.post("/v1/derived-points/priapus/osculating", json={"jd_ut": jd})
    assert priapus.status_code == 200
    expected = osculating_priapus(jd, reader=moira_engine._reader)
    assert priapus.json()["longitude"] == expected.longitude
    assert priapus.json()["source_apogee_truth"]["kernel_identity"] == expected.source_apogee_truth.kernel_identity
    assert priapus.json()["source_apogee_truth"]["speed_method"] == expected.speed_method

    focus = client.post("/v1/derived-points/second-focus", json={
        "body": "Moon", "jd_ut": jd, "center": "EARTH", "frame": "TRUE_ECLIPTIC_OF_DATE",
    })
    assert focus.status_code == 200
    receipt = focus.json()["source_elements"]
    assert receipt["body"]["naif_id"] == 301
    assert receipt["center"] == "EARTH"
    assert receipt["provenance"]["state_source"]["legs"]
