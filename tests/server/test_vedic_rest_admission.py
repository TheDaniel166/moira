"""VED-005 admission matrix: malformed inputs fail before astronomy dispatch."""
from __future__ import annotations

from copy import deepcopy
from contextvars import Context
import json

from fastapi.testclient import TestClient
import pytest

from moira_server.app import create_app
from moira_server.config import ServerConfig

pytestmark = pytest.mark.loopback

ISO = "2000-01-01T12:00:00Z"
OBSERVER = {"dt": ISO, "observer_lat": 40.7128, "observer_lon": -74.006, "observer_elev_m": 10.0}
NATAL = {"dt": ISO, "ayanamsa": "Lahiri", "year_basis": "julian_365.25"}
ALT = {"moon_tropical_lon": 10.0, "natal_jd": 2451545.0, "levels": 1}
PERIOD = {"system": "ashtottari", "level": 1, "lord": "Sun", "start_jd": 2451545.0, "end_jd": 2451546.0}
OFF = {"chart": False, "panchanga": False, "panchanga_profile": False,
       "shadbala": False, "shadbala_profile": False, "dasha_current": False, "dasha_lord_pair": False}

CASES = {
    "/v1/dasha/vimshottari/sequence": {"natal": NATAL, "levels": 1},
    "/v1/dasha/vimshottari/balance": NATAL,
    "/v1/dasha/vimshottari/current": {"natal": NATAL, "current_dt": "2001-01-01T00:00:00Z", "levels": 2},
    "/v1/dasha/vimshottari/profile": {"natal": NATAL, "levels": 1},
    "/v1/dasha/vimshottari/lord-pair": {"natal": NATAL, "current_dt": "2001-01-01T00:00:00Z", "levels": 2},
    "/v1/dasha/alternate/period-profile": PERIOD,
    "/v1/sade-sati/status": {"natal_moon_sidereal_lon": 10.0, "saturn_sidereal_lon": 330.0},
    "/v1/sade-sati/windows": {"natal_moon_sidereal_lon": 10.0, "start_dt": ISO, "end_dt": "2000-01-02T12:00:00Z", "ayanamsa_system": "Lahiri"},
    "/v1/vedic/chart-profile": {**OBSERVER, "include": {**OFF, "panchanga": True}, "include_nodes": True, "dasha_levels": 2},
}
for system in ("ashtottari", "yogini"):
    policy = {"ayanamsa_system": "Lahiri", "year_basis": "julian_365.25"}
    if system == "ashtottari":
        policy.update(bypass_eligibility=True, lagna_sign_index=0)
    for kind in ("sequence", "profile"):
        CASES[f"/v1/dasha/alternate/{system}/{kind}"] = {**ALT, "policy": policy}
        CASES[f"/v1/dasha/alternate/{system}/chart/{kind}"] = {
            **OBSERVER, "levels": 1, "include_nodes": False, "policy": policy,
        }
for kind in ("", "/profile", "/network", "/condition", "/bhava", "/full"):
    payload = {**OBSERVER, "ayanamsa_system": "Lahiri", "house_system": "P", "policy": {"ayanamsa_system": "Lahiri"}}
    if kind == "/condition":
        payload["planet"] = "Mars"
    CASES[f"/v1/shadbala/chart{kind}"] = payload
for kind in ("dignity", "condition"):
    CASES[f"/v1/vedic-dignities/{kind}"] = {"planet": "Sun", "sidereal_longitude": 10.0}
for kind in ("relationships", "chart-profile"):
    CASES[f"/v1/vedic-dignities/{kind}"] = {"sidereal_longitudes": {"Sun": 10.0, "Moon": 50.0}}
for kind in ("dignity", "relationships", "profile"):
    payload = {**OBSERVER, "include_nodes": False, "ayanamsa_system": "Lahiri"}
    if kind == "dignity":
        payload["planet"] = "Sun"
    CASES[f"/v1/vedic-dignities/chart/{kind}"] = payload


def leaves(value, path=()):
    for key, item in value.items():
        if isinstance(item, dict):
            yield from leaves(item, (*path, key))
        else:
            yield (*path, key), item


def changed(payload, path, value):
    result = deepcopy(payload)
    target = result
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return result


def assert_rejected(client, route, payload):
    response = client.post(route, content=json.dumps(payload), headers={"Content-Type": "application/json"})
    assert response.status_code == 422, (route, payload, response.text)
    body = response.json()
    assert body["error_code"] == "validation_error"
    assert body["category"] == "input_validation"
    assert body["request_id"] == response.headers["X-Request-ID"]
    assert body["request_id"]


@pytest.fixture(scope="module")
def admission_client():
    # Any attempted dispatch fails the test, including an invalid request
    # accidentally reaching a chart, house, window or profile computation.
    from unittest.mock import patch
    class NoComputation:
        def __getattr__(self, name):
            raise AssertionError(f"malformed request dispatched engine.{name}")
    with patch("moira_server.app.create_engine", return_value=NoComputation()):
        with TestClient(create_app(ServerConfig(prewarm_enabled=False))) as client:
            yield client


@pytest.mark.parametrize("route", sorted(CASES))
def test_every_route_rejects_hostile_scalar_types_before_dispatch(admission_client, route):
    payload = CASES[route]
    assert_rejected(admission_client, route, {**payload, "unexpected": 1})
    for path, value in leaves(payload):
        if isinstance(value, bool):
            bad = (0, 1, "true", "false", None)
        elif isinstance(value, int):
            bad = (True, False, "1", 1.0, 1.5, -1, 99)
        elif isinstance(value, float):
            bad = (True, False, "10", "NaN", float("nan"), float("inf"), float("-inf"))
        elif path[-1] in ("dt", "current_dt", "start_dt", "end_dt"):
            bad = (946728000, 946728000.0, "946728000", " 946728000 ", True, "2000-01-01T12:00:00")
        elif path[-1] in ("ayanamsa", "ayanamsa_system", "year_basis", "house_system", "planet", "lord", "system"):
            bad = ("unknown", "", 1)
        else:
            continue
        for malformed in bad:
            assert_rejected(admission_client, route, changed(payload, path, malformed))


def test_sade_sati_order_and_profile_preflight(admission_client):
    route = "/v1/sade-sati/windows"
    assert_rejected(admission_client, route, {**CASES[route], "end_dt": ISO})
    route = "/v1/vedic/chart-profile"
    assert_rejected(admission_client, route, {**CASES[route], "hora_lord": "Pluto"})
    assert_rejected(admission_client, route, {**OBSERVER, "bodies": ["UnknownBody"]})
    assert_rejected(admission_client, route, {**OBSERVER, "include": {**OFF, "dasha_current": True}})
    assert_rejected(admission_client, route, {**OBSERVER, "include": {**OFF, "dasha_current": True}, "current_dt": "1999-01-01T12:00:00Z"})
    assert_rejected(admission_client, route, {**OBSERVER, "panchanga_policy": {"ayanamsa_system": "unknown"}})
    # Previously a numeric string bypassed the direct Panchanga guard too.
    assert_rejected(admission_client, "/v1/panchanga/chart", {**OBSERVER, "dt": "946728000"})


@pytest.mark.parametrize("child", [
    {**PERIOD, "system": "yogini", "lord": "Mangala", "level": 2},
    {**PERIOD, "level": 3},
    {**PERIOD, "level": 2, "start_jd": 2451544.0},
    {**PERIOD, "level": 2, "end_jd": 2451547.0},
])
def test_supplied_period_tree_has_one_system_and_parent_containment(admission_client, child):
    assert_rejected(admission_client, "/v1/dasha/alternate/period-profile", {**PERIOD, "sub": [child]})


def test_period_subdivision_count_is_bounded(admission_client):
    children = [{**PERIOD, "level": 2, "start_jd": 2451545.0 + index * 0.1,
                 "end_jd": 2451545.0 + index * 0.1 + 0.05} for index in range(9)]
    assert_rejected(admission_client, "/v1/dasha/alternate/period-profile", {**PERIOD, "sub": children})


@pytest.mark.requires_ephemeris
def test_all_thirty_routes_accept_valid_requests_without_inherited_reader_context(moira_engine, monkeypatch):
    import moira.spk_reader as readers
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    original = readers.get_reader
    seen = []
    def witness(*args, **kwargs):
        reader = original(*args, **kwargs)
        assert reader is moira_engine._reader_obj
        seen.append(reader)
        return reader
    monkeypatch.setattr(readers, "get_reader", witness)
    def run():
        with TestClient(create_app(ServerConfig(prewarm_enabled=False))) as client:
            for route, payload in CASES.items():
                response = client.post(route, json=payload)
                assert response.status_code == 200, (route, response.text)
                body = response.json()
                if route.startswith("/v1/shadbala/"):
                    policy = body["policy_receipt"]
                    assert policy["effective_house_system"] == "P"
                    assert policy["applied_ayanamsa_system"] == "Lahiri"
                    assert policy["ayanamsa_precedence"] == "policy"
            assert len(CASES) == 30
    Context().run(run)
    assert seen, "Shadbala's module computation must observe its owning reader"


@pytest.mark.requires_ephemeris
def test_profile_receipts_preserve_component_overrides_and_omission(moira_engine, monkeypatch):
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    def run():
        with TestClient(create_app(ServerConfig(prewarm_enabled=False))) as client:
            payload = {**OBSERVER, "ayanamsa_system": "Lahiri", "house_system": "Whole Sign",
                       "panchanga_policy": {"ayanamsa_system": "Raman"},
                       "shadbala_policy": {"ayanamsa_system": "Krishnamurti"},
                       "include": {**OFF, "panchanga": True, "shadbala": True}}
            response = client.post("/v1/vedic/chart-profile", json=payload)
            assert response.status_code == 200, response.text
            body = response.json()
            assert body["policy_receipt"]["component_ayanamsa_systems"] == {"panchanga": "Raman", "shadbala": "Krishnamurti"}
            assert body["policy_receipt"]["mixed_ayanamsa_frames"] is True
            assert body["panchanga"]["ayanamsa_system"] == "Raman"
            assert body["shadbala"]["ayanamsa_system"] == "Krishnamurti"
            assert body["shadbala"]["policy_receipt"]["resolved_house_system"] == "W"
            assert body["shadbala"]["policy_receipt"]["effective_house_system"] == "W"
            payload["include"] = {**OFF, "panchanga": True}
            payload["hora_lord"] = "Mars"
            body = client.post("/v1/vedic/chart-profile", json=payload).json()
            assert body["included_sections"] == ["panchanga"]
            assert body["shadbala"] is None
            assert body["policy_receipt"]["inactive_inputs"] == ["house_system", "hora_lord", "shadbala_policy"]
    Context().run(run)


@pytest.mark.requires_ephemeris
def test_alternate_chart_omitted_policy_uses_requested_ayanamsa(moira_engine, monkeypatch):
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    with TestClient(create_app(ServerConfig(prewarm_enabled=False))) as client:
        for system in ("ashtottari", "yogini"):
            for kind in ("sequence", "profile"):
                response = client.post(f"/v1/dasha/alternate/{system}/chart/{kind}", json={
                    "dt": ISO, "ayanamsa_system": "Raman", "levels": 1,
                })
                assert response.status_code == 200
                body = response.json()
                sequence = body["result"] if kind == "sequence" else body["result"]["sequence"]
                assert sequence["ayanamsa_system"] == body["provenance"]["ayanamsa_system"] == "Raman"
                direct = client.post(f"/v1/dasha/alternate/{system}/sequence", json={
                    "moon_tropical_lon": body["moon_tropical_longitude"],
                    "natal_jd": body["natal_jd"], "levels": 1,
                    "policy": {"ayanamsa_system": "Raman"},
                })
                assert direct.status_code == 200
                assert sequence == direct.json()


@pytest.mark.requires_ephemeris
def test_polar_house_receipt_preserves_engine_fallback(moira_engine, monkeypatch):
    from datetime import datetime, timezone
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    payload = {**OBSERVER, "dt": "2000-03-21T12:00:00Z", "observer_lat": 78.0}
    houses = moira_engine.houses(datetime(2000, 3, 21, 12, tzinfo=timezone.utc), latitude=78.0, longitude=-74.006, system="P")
    def run():
        with TestClient(create_app(ServerConfig(prewarm_enabled=False))) as client:
            response = client.post("/v1/shadbala/chart", json=payload)
            assert response.status_code == 200, response.text
            receipt = response.json()["policy_receipt"]
            assert receipt["requested_house_system"] == "P"
            assert receipt["effective_house_system"] == houses.effective_system
            assert receipt["polar_fallback_applied"] == houses.fallback is True
            winter = client.post("/v1/shadbala/chart", json=payload | {"dt": OBSERVER["dt"]})
            assert winter.status_code == 422
            assert winter.json()["error_code"] == "shadbala_context_unavailable"
    Context().run(run)
