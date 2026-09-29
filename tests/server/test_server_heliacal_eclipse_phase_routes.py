"""6.9.9 REST additions: standard heliacal kinds, phasis search, previous
eclipses, and lunar-phase longitudes."""
from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from moira.constants import Body
from moira.eclipse import EclipseCalculator
from moira.heliacal import HeliacalEventKind, phasis_events_near, visibility_event
from moira.planets import planet_at
from moira.spk_reader import use_reader_override
from moira.transits import find_lunar_phases
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.loopback


@pytest.fixture
def client_with_engine(
    moira_engine,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        yield client


@pytest.mark.requires_ephemeris
def test_previous_eclipse_routes_match_engine_truth(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    calc = EclipseCalculator(reader=getattr(moira_engine, "_reader", None))
    direct_solar = calc.previous_solar_eclipse(2451545.0)
    direct_lunar = calc.previous_lunar_eclipse(2451545.0, kind="total")

    solar = client_with_engine.post("/v1/eclipses/solar/previous", json={"jd_start": 2451545.0})
    lunar = client_with_engine.post(
        "/v1/eclipses/lunar/previous",
        json={"jd_start": 2451545.0, "kind": "total"},
    )

    assert solar.status_code == 200
    solar_body = solar.json()
    assert solar_body["jd_ut"] == pytest.approx(direct_solar.jd_ut)
    assert solar_body["jd_ut"] < 2451545.0
    assert solar_body["data"]["eclipse_type"] == str(direct_solar.data.eclipse_type)
    assert set(solar_body) == {"jd_ut", "datetime_utc", "data"}

    assert lunar.status_code == 200
    lunar_body = lunar.json()
    assert lunar_body["jd_ut"] == pytest.approx(direct_lunar.jd_ut)
    assert lunar_body["jd_ut"] < 2451545.0


def test_previous_eclipse_routes_reject_invalid_kind(client_with_engine: TestClient) -> None:
    response = client_with_engine.post(
        "/v1/eclipses/lunar/previous",
        json={"jd_start": 2451545.0, "kind": "sideways"},
    )
    assert response.status_code == 422
    assert response.json()["error_code"] == "validation_error"


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize(
    ("kind", "jd_start"),
    [
        ("heliacal_setting", 2460200.5),
        ("acronychal_rising", 2460100.5),
        ("cosmical_setting", 2460100.5),
        ("acronychal_setting", 2460200.5),
    ],
)
def test_planet_heliacal_route_serves_standard_kinds(
    client_with_engine: TestClient,
    moira_engine,
    kind: str,
    jd_start: float,
) -> None:
    with use_reader_override(getattr(moira_engine, "_reader", None)):
        direct = visibility_event("Saturn", HeliacalEventKind(kind), jd_start, 35.0, 35.0)
    response = client_with_engine.post(
        "/v1/heliacal/planet",
        json={"body": "Saturn", "kind": kind, "jd_start": jd_start, "lat": 35.0, "lon": 35.0},
    )
    assert response.status_code == 200
    assert direct is not None
    body = response.json()
    assert body["kind"] == kind
    assert body["jd_ut"] == pytest.approx(direct.jd_ut)


@pytest.mark.requires_ephemeris
def test_planet_heliacal_route_returns_null_for_inapplicable_kind(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/heliacal/planet",
        json={"body": "Saturn", "kind": "evening_first", "jd_start": 2460100.5, "lat": 35.0, "lon": 35.0},
    )
    assert response.status_code == 200
    assert response.json() is None


@pytest.mark.requires_ephemeris
def test_heliacal_phasis_route_matches_engine(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    with use_reader_override(getattr(moira_engine, "_reader", None)):
        direct = phasis_events_near("Saturn", 2460170.0, 35.0, 35.0)
    response = client_with_engine.post(
        "/v1/heliacal/phasis",
        json={"body": "Saturn", "jd_ut": 2460170.0, "lat": 35.0, "lon": 35.0},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["window_days"] == 7.0
    assert body["lookahead_days"] == direct.lookahead_days
    assert [entry["kind"] for entry in body["events"]] == [
        "heliacal_rising",
        "heliacal_setting",
        "evening_first",
        "morning_last",
        "acronychal_rising",
        "cosmical_setting",
    ]
    for entry, expected in zip(body["events"], direct.results):
        assert entry["applicable"] is expected.applicable
        assert entry["found"] is (expected.event is not None)
        if expected.event is not None:
            assert entry["event"]["jd_ut"] == pytest.approx(expected.event.jd_ut)
            assert entry["offset_days"] == pytest.approx(expected.offset_days)
        else:
            assert entry["event"] is None
    acronychal = body["events"][4]
    assert acronychal["found"] is True
    assert -7.0 <= acronychal["offset_days"] <= 7.0


def test_heliacal_phasis_route_rejects_window_out_of_range(client_with_engine: TestClient) -> None:
    response = client_with_engine.post(
        "/v1/heliacal/phasis",
        json={"body": "Saturn", "jd_ut": 2460170.0, "lat": 35.0, "lon": 35.0, "window_days": 45},
    )
    assert response.status_code == 422


@pytest.mark.requires_ephemeris
def test_lunar_phase_route_carries_moon_and_sun_longitudes(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    reader = getattr(moira_engine, "_reader", None)
    direct = find_lunar_phases(2451545.0, 2451545.0 + 30.0, reader=reader)
    response = client_with_engine.post(
        "/v1/lunar-phases",
        json={"jd_start": 2451545.0, "jd_end": 2451545.0 + 30.0},
    )
    assert response.status_code == 200
    events = response.json()["events"]
    assert len(events) == len(direct)
    for entry, event in zip(events, direct):
        moon = planet_at(Body.MOON, event.jd_ut, reader=reader).longitude
        sun = planet_at(Body.SUN, event.jd_ut, reader=reader).longitude
        assert entry["moon_longitude"] == pytest.approx(moon)
        assert entry["sun_longitude"] == pytest.approx(sun)
        delta = (entry["moon_longitude"] - entry["sun_longitude"]) % 360.0
        diff = (delta - entry["phase_angle"] + 180.0) % 360.0 - 180.0
        assert abs(diff) < 1e-9
