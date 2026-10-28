"""P10-03c Geodetic timing route: POST /v1/geodetic/chart/transits.

Governing object: docs/architecture/P10-03C_GEODETIC_TIMING_TRANSPORT_DESIGN.md.
The route freezes a place's Geodetic angles at reference_dt and returns
Moira.geodetic_transits for one mover, serialized without loss.

Evidence classes (design record section 5):
- parity: route JSON == the facade result through the same serializer, in
  both zodiac lanes, for a major planet and the Moon;
- invariant: a place on Mars's own longitude has an MC contact at the
  reference epoch (Geodetic MC equals geographic longitude);
- adversarial: aware datetimes, span cap, every policy ceiling, lane law,
  numeric and ambiguous movers;
- behavioural: exhausted budget is 200 incomplete, repeats are cached, and
  the route works with no global kernel.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient
import pytest

from moira.geodetic import GeodeticLocation
from moira.geodetic_timing import GeodeticTimingPolicy
from moira.julian import _ut1_to_utc, datetime_from_jd, jd_from_datetime, utc_to_ut1
from moira.planets import planet_at
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.geodetic import GeodeticTimingAspectModel
from moira_server.serializers.geodetic import serialize_geodetic_transits

pytestmark = pytest.mark.loopback

REFERENCE = datetime(2000, 1, 1, 12, tzinfo=timezone.utc)
START = datetime(2000, 1, 1, tzinfo=timezone.utc)
END = datetime(2000, 4, 1, tzinfo=timezone.utc)
NEW_YORK = {"geo_latitude": 40.7, "geo_longitude": -74.0}
ASPECTS = [{"angle_deg": 0.0, "orb_deg": 1.0}, {"angle_deg": 90.0, "orb_deg": 1.0}]
BODY = {**NEW_YORK, "reference_dt": "2000-01-01T12:00:00Z", "mover": "Mars",
        "start_dt": "2000-01-01T00:00:00Z", "end_dt": "2000-04-01T00:00:00Z", "aspects": ASPECTS}


@pytest.fixture
def client(moira_engine, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    with TestClient(create_app(ServerConfig(docs_enabled=False)), raise_server_exceptions=False) as test_client:
        yield test_client


def _facade(engine, body: dict, *, place=NEW_YORK, mover="Mars", start=START, end=END, step=0.5, **lane):
    aspects = [GeodeticTimingAspectModel(**a) for a in body["aspects"]]
    result = engine.geodetic_transits(
        GeodeticLocation(place["geo_latitude"], place["geo_longitude"]), REFERENCE, mover, start, end,
        aspects=tuple((a.angle_deg, a.orb_deg) for a in aspects),
        policy=GeodeticTimingPolicy(step_days=step), **lane,
    )
    return serialize_geodetic_transits(result, aspects).model_dump(mode="json")


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("lane", [{}, {"zodiac": "sidereal", "ayanamsa_system": "Lahiri"}], ids=["tropical", "sidereal"])
def test_route_matches_facade(client, moira_engine, lane) -> None:
    response = client.post("/v1/geodetic/chart/transits", json={**BODY, **lane})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body == _facade(moira_engine, BODY, **lane)
    assert body["complete"] is True
    assert body["timescale"] == "JD_UT1"
    assert all(e["window_index"] is not None for e in body["events"])


@pytest.mark.requires_ephemeris
def test_moon_route_matches_facade_with_every_contact_windowed(client, moira_engine) -> None:
    end = datetime(2000, 1, 31, tzinfo=timezone.utc)
    body = {**BODY, "mover": "Moon", "end_dt": "2000-01-31T00:00:00Z"}
    response = client.post("/v1/geodetic/chart/transits", json=body)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data == _facade(moira_engine, body, mover="Moon", end=end)
    # The narrow-window repair: no Moon contact may lose its orb window.
    assert data["events"] and all(e["window_index"] is not None for e in data["events"])


@pytest.mark.requires_ephemeris
def test_built_in_mc_contact_is_found_at_the_reference_epoch(client, moira_engine) -> None:
    jd_ut1 = utc_to_ut1(jd_from_datetime(REFERENCE))
    mars = planet_at("Mars", jd_ut1, reader=moira_engine._reader).longitude
    place = {"geo_latitude": 35.0, "geo_longitude": (mars + 180.0) % 360.0 - 180.0}
    response = client.post("/v1/geodetic/chart/transits", json={
        **BODY, **place, "angles": ["MC"], "aspects": [{"angle_deg": 0.0, "orb_deg": 1.0}],
        "start_dt": "1999-12-30T12:00:00Z", "end_dt": "2000-01-03T12:00:00Z",
    })
    assert response.status_code == 200, response.text
    events = response.json()["events"]
    assert any(abs(e["epoch"]["jd_ut1"] - jd_ut1) <= 2e-6 for e in events)


@pytest.mark.requires_ephemeris
def test_epochs_carry_their_utc_rendering(client) -> None:
    data = client.post("/v1/geodetic/chart/transits", json=BODY).json()
    epochs = [e["epoch"] for e in data["events"]] + [w["entry"] for w in data["windows"] if w["entry"]]
    assert epochs
    for epoch in epochs:
        assert epoch["datetime_utc"] == datetime_from_jd(_ut1_to_utc(epoch["jd_ut1"])).isoformat()


@pytest.mark.requires_ephemeris
def test_exhausted_budget_is_an_incomplete_answer_not_an_error(client) -> None:
    response = client.post("/v1/geodetic/chart/transits", json={**BODY, "policy": {"max_evaluations": 10}})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["complete"] is False
    assert data["status"] == "incomplete"
    assert "search_budget_exhausted" in data["reasons"]
    assert data["policy"]["max_evaluations"] == 10


@pytest.mark.requires_ephemeris
def test_identical_requests_are_served_from_the_cache(moira_engine, monkeypatch: pytest.MonkeyPatch) -> None:
    import moira_server.routers.geodetic as router

    calls = []
    original = router.compute_geodetic_chart_transits
    monkeypatch.setattr(router, "compute_geodetic_chart_transits",
                        lambda engine, request: calls.append(1) or original(engine, request))
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    with TestClient(create_app(ServerConfig(docs_enabled=False))) as client:
        first = client.post("/v1/geodetic/chart/transits", json=BODY).json()
        second = client.post("/v1/geodetic/chart/transits", json=BODY).json()
    assert first == second
    assert len(calls) == 1


@pytest.mark.requires_ephemeris
def test_route_works_without_a_global_kernel(moira_engine, monkeypatch: pytest.MonkeyPatch) -> None:
    import moira.spk_reader as spk_reader

    monkeypatch.setattr(spk_reader, "_reader", None)
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    with spk_reader.use_reader_override(None):
        with TestClient(create_app(ServerConfig()), raise_server_exceptions=False) as client:
            assert client.post("/v1/geodetic/chart/transits", json=BODY).status_code == 200


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("mover", ["499", "Halley", "asteroid:Definitely Not A Body"])
def test_unresolved_movers_are_refused(client, mover) -> None:
    assert client.post("/v1/geodetic/chart/transits", json={**BODY, "mover": mover}).status_code == 422


@pytest.mark.parametrize("change,fragment", [
    ({"reference_dt": "2000-01-01T12:00:00"}, "timezone-aware"),
    ({"start_dt": "2000-01-01T00:00:00"}, "timezone-aware"),
    ({"end_dt": "2000-01-01T00:00:00Z"}, "after start_dt"),
    ({"end_dt": "2001-01-02T00:00:01Z"}, "at most 366 days"),
    ({"aspects": []}, "aspects"),
    ({"aspects": [{"angle_deg": float(i), "orb_deg": 1.0} for i in range(9)]}, "aspects"),
    ({"aspects": [{"angle_deg": 90.0, "orb_deg": 1.0}, {"angle_deg": 90.0, "orb_deg": 2.0}]}, "unique"),
    ({"aspects": [{"angle_deg": 181.0, "orb_deg": 1.0}]}, "angle_deg"),
    ({"aspects": [{"angle_deg": 90.0, "orb_deg": 10.5}]}, "orb_deg"),
    ({"angles": ["MC", "MC"]}, "unique"),
    ({"policy": {"step_days": 0.2}}, "step_days"),
    ({"policy": {"step_days": 5.5}}, "step_days"),
    ({"policy": {"max_evaluations": 50001}}, "max_evaluations"),
    ({"policy": {"max_subdivisions": 10001}}, "max_subdivisions"),
    ({"policy": {"max_depth": 13}}, "max_depth"),
    ({"policy": {"maximum_light_time_days": 2.5}}, "maximum_light_time_days"),
    ({"policy": {"coverage_policy": "best_effort"}}, "coverage_policy"),
    ({"zodiac": "sidereal"}, "sidereal zodiac requires"),
    ({"ayanamsa_system": "Lahiri"}, "tropical zodiac must not carry"),
    ({"mover": " Mars"}, "trimmed"),
    ({"geo_latitude": 90.0}, "geo_latitude"),
    ({"unexpected": True}, "Extra inputs"),
])
def test_admission(change, fragment, monkeypatch: pytest.MonkeyPatch) -> None:
    class _NoEngine:
        def __getattr__(self, name):
            raise AssertionError(f"admission reached the engine: {name}")

    monkeypatch.setattr("moira_server.app.create_engine", lambda config: _NoEngine())
    with TestClient(create_app(ServerConfig(docs_enabled=False)), raise_server_exceptions=False) as client:
        response = client.post("/v1/geodetic/chart/transits", json={**BODY, **change})
    assert response.status_code == 422, response.text
    assert fragment in response.text


def test_route_is_registered_as_a_post_operation() -> None:
    paths = create_app(ServerConfig()).openapi()["paths"]
    assert set(paths["/v1/geodetic/chart/transits"]) == {"post"}
