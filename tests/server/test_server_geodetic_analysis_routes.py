"""Kernel-free Geodetic analysis routes (houses, geometry, sensitivity, uncertainty).

Governing object: each route admits caller-supplied geography, obliquity and
zodiac policy, calls exactly one owning engine function, and serializes the
result without reinterpretation. No engine or ephemeris is involved.

Evidence classes: dual-path equivalence (route == direct engine call, exact),
transport admission (lane law, bounds, strict models), the declared house
policy default (strict, the Geodetic owner's default), and the kernel-free
taboo (an engine that fails on any attribute access is never touched).
"""

from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from moira.constants import HouseSystem
from moira.geodetic import (
    GeodeticInputUncertainty,
    GeodeticLocation,
    geodetic_chart,
    geodetic_chart_sensitivity,
    geodetic_geometry,
)
from moira.geodetic_analysis import geodetic_house_chart
from moira.geodetic_uncertainty import GeodeticDiagnosticPolicy, diagnose_geodetic_uncertainty
from moira.houses import HousePolicy
from moira_server.app import create_app
from moira_server.config import ServerConfig

pytestmark = pytest.mark.loopback

BASE = {"geo_longitude": -74.0, "geo_latitude": 40.7, "obliquity": 23.44}
SIDEREAL = {"zodiac": "sidereal", "ayanamsa_deg": 23.85}
UNCERTAINTY = {"longitude_deg": 0.1, "latitude_deg": 0.1, "obliquity_deg": 0.0}


class _NoEngine:
    """Fails on any access: these routes must never consult the engine."""

    def __getattr__(self, name: str):
        raise AssertionError(f"kernel-free Geodetic route touched engine.{name}")


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: _NoEngine())
    with TestClient(create_app(ServerConfig(docs_enabled=False)), raise_server_exceptions=False) as test_client:
        yield test_client


def _ok(client: TestClient, path: str, body: dict) -> dict:
    response = client.post(f"/v1/geodetic/{path}", json=body)
    assert response.status_code == 200, response.text
    return response.json()


def _refused(client: TestClient, path: str, body: dict, fragment: str) -> None:
    response = client.post(f"/v1/geodetic/{path}", json=body)
    assert response.status_code == 422, response.text
    assert fragment in response.text


@pytest.mark.parametrize("lane", [{}, SIDEREAL], ids=["tropical", "sidereal"])
@pytest.mark.parametrize("system", [HouseSystem.PLACIDUS, HouseSystem.EQUAL, HouseSystem.WHOLE_SIGN])
def test_houses_match_the_owner(client: TestClient, lane: dict, system: str) -> None:
    body = _ok(client, "houses", {**BASE, **lane, "system": system})
    expected = geodetic_house_chart(
        GeodeticLocation(BASE["geo_latitude"], BASE["geo_longitude"]),
        obliquity=BASE["obliquity"], system=system,
        zodiac=lane.get("zodiac", "tropical"), ayanamsa_deg=lane.get("ayanamsa_deg"),
    )
    assert body["houses"]["cusps"] == list(expected.houses.cusps)
    assert body["houses"]["effective_system"] == expected.houses.effective_system
    assert body["chart"]["mc"] == expected.angles.mc
    assert body["chart"]["asc"] == expected.angles.asc
    assert body["targets"] == expected.targets
    assert body["source_frame"] == expected.source_frame
    assert body["provenance"]["coordinate_source"] == "direct_geographic_obliquity"
    assert body["provenance"]["ayanamsa_deg"] == lane.get("ayanamsa_deg", 0.0)


def test_houses_default_to_strict_and_honour_an_explicit_fallback(client: TestClient) -> None:
    polar = {"geo_longitude": 0.0, "geo_latitude": 80.0, "obliquity": 23.44, "system": HouseSystem.PLACIDUS}
    _refused(client, "houses", polar, "RAISE")

    body = _ok(client, "houses", {**polar, "policy": {"polar_fallback": "fallback_to_porphyry"}})
    expected = geodetic_house_chart(
        GeodeticLocation(80.0, 0.0), obliquity=23.44, system=HouseSystem.PLACIDUS,
        house_policy=HousePolicy.default(),
    )
    assert body["houses"]["fallback"] is True
    assert body["houses"]["cusps"] == list(expected.houses.cusps)


def test_solar_house_systems_need_a_supplied_sun(client: TestClient) -> None:
    sunshine = {**BASE, "system": HouseSystem.SUNSHINE}
    _refused(client, "houses", sunshine, "sun")
    body = _ok(client, "houses", {**sunshine, "sun_longitude": 42.0})
    assert len(body["houses"]["cusps"]) == 12


@pytest.mark.parametrize("latitude", [40.7, -33.9, 89.9])
def test_geometry_matches_the_owner(client: TestClient, latitude: float) -> None:
    body = _ok(client, "geometry", {**BASE, "geo_latitude": latitude})
    witness = geodetic_geometry(BASE["geo_longitude"], latitude, BASE["obliquity"])
    assert body == {
        "tropical_mc_deg": witness.tropical_mc_deg, "armc_deg": witness.armc_deg,
        "intersection_norm": witness.intersection_norm,
        "meridian_altitude_sine": witness.meridian_altitude_sine,
        "rising_rate": witness.rising_rate, "asc_deg": witness.asc_deg,
        "status": witness.status, "policy": witness.policy, "roundoff_guard": witness.roundoff_guard,
    }


def test_geometry_admits_the_pole_so_its_refusal_status_is_reachable(client: TestClient) -> None:
    body = _ok(client, "geometry", {**BASE, "geo_latitude": 90.0})
    assert body["status"] == "polar_refusal"
    assert body["asc_deg"] is None
    # A chart is never computed at the pole.
    _refused(client, "houses", {**BASE, "geo_latitude": 90.0, "system": HouseSystem.EQUAL}, "geo_latitude")


@pytest.mark.parametrize("lane", [{}, SIDEREAL], ids=["tropical", "sidereal"])
def test_sensitivity_matches_the_owner(client: TestClient, lane: dict) -> None:
    body = _ok(client, "sensitivity", {**BASE, **lane, "uncertainty": UNCERTAINTY})
    expected = geodetic_chart_sensitivity(
        geodetic_chart(BASE["geo_longitude"], BASE["geo_latitude"], BASE["obliquity"],
                       ayanamsa_deg=lane.get("ayanamsa_deg"), zodiac=lane.get("zodiac", "tropical")),
        GeodeticInputUncertainty(**UNCERTAINTY),
    )
    assert body["mc_linearized_radius_deg"] == expected.mc_linearized_radius_deg
    assert body["asc_linearized_radius_deg"] == expected.asc_linearized_radius_deg
    assert body["asc_derivatives"]["geo_latitude_deg"] == expected.asc_derivatives.geo_latitude_deg
    assert body["latitude_margin_to_pole_deg"] == expected.latitude_margin_to_pole_deg
    assert body["interpretation"] == "first_order_local_not_a_bound"


def test_uncertainty_matches_the_owner_and_states_its_limits(client: TestClient) -> None:
    policy = {"residual_tolerance_deg": 1e-3, "max_evaluations": 512, "max_depth": 3}
    body = _ok(client, "uncertainty", {**BASE, "uncertainty": UNCERTAINTY, "policy": policy})
    expected = diagnose_geodetic_uncertainty(
        geodetic_chart(BASE["geo_longitude"], BASE["geo_latitude"], BASE["obliquity"]),
        GeodeticInputUncertainty(**UNCERTAINTY),
        policy=GeodeticDiagnosticPolicy(1e-3, 512, 3),
    )
    assert body["status"] == expected.status
    assert body["reasons"] == list(expected.reasons)
    assert body["sampled_max_deviation_deg"] == expected.sampled_max_deviation_deg
    assert body["sampled_max_residual_deg"] == expected.sampled_max_residual_deg
    assert body["evaluations"] == expected.evaluations <= 512
    assert body["sampling_complete"] == expected.sampling_complete
    assert body["interpretation"] == expected.interpretation
    assert body["policy"] == policy


def test_uncertainty_crossing_the_pole_is_reported_not_computed(client: TestClient) -> None:
    body = _ok(client, "uncertainty", {
        **BASE, "geo_latitude": 89.95, "uncertainty": {"latitude_deg": 0.1},
        "policy": {"residual_tolerance_deg": 1e-3},
    })
    assert body["status"] == "domain_intersection"
    assert body["reasons"]


@pytest.mark.parametrize("path,extra", [
    ("houses", {"system": HouseSystem.EQUAL}),
    ("sensitivity", {"uncertainty": UNCERTAINTY}),
    ("uncertainty", {"uncertainty": UNCERTAINTY, "policy": {"residual_tolerance_deg": 1e-3}}),
])
def test_zodiac_lane_law_is_enforced(client: TestClient, path: str, extra: dict) -> None:
    _refused(client, path, {**BASE, **extra, "ayanamsa_deg": 0.0}, "tropical zodiac must not carry ayanamsa_deg")
    _refused(client, path, {**BASE, **extra, "zodiac": "sidereal"}, "sidereal zodiac requires ayanamsa_deg")


@pytest.mark.parametrize("path,body,fragment", [
    ("houses", {**BASE, "system": ""}, "system"),
    ("houses", {**BASE, "system": "P", "unexpected": 1}, "Extra inputs"),
    ("geometry", {**BASE, "obliquity": 30.0}, "Earth obliquity"),
    ("geometry", {**BASE, "zodiac": "tropical"}, "Extra inputs"),
    ("sensitivity", {**BASE, "uncertainty": {"latitude_deg": -0.1}}, "greater than or equal to 0"),
    ("uncertainty", {**BASE, "uncertainty": UNCERTAINTY,
                     "policy": {"residual_tolerance_deg": 1e-3, "max_evaluations": 4097}}, "less than or equal to 4096"),
    ("uncertainty", {**BASE, "uncertainty": UNCERTAINTY,
                     "policy": {"residual_tolerance_deg": 0.0}}, "greater than 0"),
    ("uncertainty", {**BASE, "uncertainty": UNCERTAINTY,
                     "policy": {"residual_tolerance_deg": 1e-3, "max_depth": 13}}, "less than or equal to 12"),
])
def test_admission_bounds(client: TestClient, path: str, body: dict, fragment: str) -> None:
    _refused(client, path, body, fragment)


def test_routes_are_registered_as_post_operations() -> None:
    paths = create_app(ServerConfig()).openapi()["paths"]
    for name in ("houses", "geometry", "sensitivity", "uncertainty"):
        assert set(paths[f"/v1/geodetic/{name}"]) == {"post"}
