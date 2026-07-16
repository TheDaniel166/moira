"""P12-06 sunrise-based planetary-hours route admission tests."""

from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from moira.planetary_hours import PlanetaryHour, PlanetaryHoursDay
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.network


class _FakeEngine:
    def __init__(self, reader=None) -> None:
        self._reader = reader


def _make_day(
    *,
    requested_jd: float = 2451545.5,
    sunrise_jd: float = 2451545.25,
    sunset_jd: float = 2451545.75,
    latitude: float = 0.0,
    longitude: float = 0.0,
) -> PlanetaryHoursDay:
    day_len = (sunset_jd - sunrise_jd) / 12.0
    next_sunrise = sunrise_jd + 1.0
    night_len = (next_sunrise - sunset_jd) / 12.0
    rulers = ["Sun", "Venus", "Mercury", "Moon", "Saturn", "Jupiter", "Mars"]
    hours: list[PlanetaryHour] = []
    for i in range(12):
        start = sunrise_jd + i * day_len
        hours.append(
            PlanetaryHour(
                hour_number=i + 1,
                ruler=rulers[i % len(rulers)],
                jd_start=start,
                jd_end=start + day_len,
                is_daytime=True,
            )
        )
    for i in range(12):
        start = sunset_jd + i * night_len
        hours.append(
            PlanetaryHour(
                hour_number=i + 13,
                ruler=rulers[(i + 12) % len(rulers)],
                jd_start=start,
                jd_end=start + night_len,
                is_daytime=False,
            )
        )
    return PlanetaryHoursDay(
        date_jd=requested_jd,
        latitude=latitude,
        longitude=longitude,
        sunrise_jd=sunrise_jd,
        sunset_jd=sunset_jd,
        hours=tuple(hours),
    )


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: _FakeEngine())
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as test_client:
        yield test_client


def _assert_validation_envelope(response, *, message_fragment: str) -> None:
    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "validation_error"
    assert body["category"] == "input_validation"
    assert body["request_id"]
    assert response.headers["X-Request-ID"] == body["request_id"]
    assert message_fragment in body["message"]


def test_schedule_route_serializes_twenty_four_ordered_hours(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "moira_server.services.planetary_hours.planetary_hours",
        lambda jd, lat, lon, reader=None: _make_day(
            requested_jd=jd,
            latitude=lat,
            longitude=lon,
        ),
    )

    response = client.post(
        "/v1/planetary-hours/schedule",
        json={"jd": 2451545.5, "latitude": 0.0, "longitude": 0.0},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["requested_jd"] == pytest.approx(2451545.5)
    assert body["sunrise_jd"] == pytest.approx(2451545.25)
    assert body["sunset_jd"] == pytest.approx(2451545.75)
    assert body["next_sunrise_jd"] == pytest.approx(2451546.25)
    assert body["day_duration_days"] == pytest.approx(0.5)
    assert body["night_duration_days"] == pytest.approx(0.5)
    assert len(body["hours"]) == 24
    assert [hour["hour_number"] for hour in body["hours"]] == list(range(1, 25))
    assert [hour["is_daytime"] for hour in body["hours"][:12]] == [True] * 12
    assert [hour["is_daytime"] for hour in body["hours"][12:]] == [False] * 12
    for current, next_hour in zip(body["hours"], body["hours"][1:], strict=False):
        assert current["jd_end"] == pytest.approx(next_hour["jd_start"])
        assert current["jd_end"] > current["jd_start"]
    assert body["hours"][0]["start_utc"].endswith("Z")
    assert body["hours"][0]["end_utc"].endswith("Z")
    provenance = body["provenance"]
    assert provenance["source_module"] == "moira.planetary_hours"
    assert provenance["vessel"] == "moira.planetary_hours.PlanetaryHour"
    assert provenance["not_vessel"] == "moira.cycles.PlanetaryHour"
    assert provenance["timezone_policy"] == "utc_output_only"


def test_schedule_route_can_omit_iso_timestamps(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "moira_server.services.planetary_hours.planetary_hours",
        lambda jd, lat, lon, reader=None: _make_day(requested_jd=jd),
    )

    response = client.post(
        "/v1/planetary-hours/schedule",
        json={
            "jd": 2451545.5,
            "latitude": 0.0,
            "longitude": 0.0,
            "include_iso_utc": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["hours"][0]["start_utc"] is None
    assert body["hours"][0]["end_utc"] is None
    assert body["provenance"]["iso_timestamp_policy"] == "not_requested"


def test_schedule_route_serializes_bce_calendar_timestamps(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "moira_server.services.planetary_hours.planetary_hours",
        lambda jd, lat, lon, reader=None: _make_day(
            requested_jd=jd,
            sunrise_jd=-1000.25,
            sunset_jd=-999.75,
            latitude=lat,
            longitude=lon,
        ),
    )

    response = client.post(
        "/v1/planetary-hours/schedule",
        json={"jd": -1000.0, "latitude": 0.0, "longitude": 0.0},
    )

    assert response.status_code == 200
    first_hour = response.json()["hours"][0]
    assert first_hour["start_utc"].startswith("-")
    assert first_hour["start_utc"].endswith("Z")


def test_hour_at_route_returns_containing_hour_and_window(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "moira_server.services.planetary_hours.planetary_hours",
        lambda jd, lat, lon, reader=None: _make_day(requested_jd=jd),
    )

    response = client.post(
        "/v1/planetary-hours/hour-at",
        json={"jd": 2451545.5, "latitude": 0.0, "longitude": 0.0},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["requested_jd"] == pytest.approx(2451545.5)
    assert body["hour"]["hour_number"] == 7
    assert body["hour"]["jd_start"] <= body["requested_jd"] < body["hour"]["jd_end"]
    assert body["schedule"] is None
    assert body["schedule_window"] == {
        "sunrise_jd": pytest.approx(2451545.25),
        "sunset_jd": pytest.approx(2451545.75),
        "next_sunrise_jd": pytest.approx(2451546.25),
        "day_duration_days": pytest.approx(0.5),
        "night_duration_days": pytest.approx(0.5),
        "contains_requested_jd": True,
    }
    assert "hour_lookup" in body["provenance"]["stage_sequence"]


def test_hour_at_route_returns_null_outside_resolved_window(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "moira_server.services.planetary_hours.planetary_hours",
        lambda jd, lat, lon, reader=None: _make_day(
            requested_jd=jd,
            sunrise_jd=2451545.25,
            sunset_jd=2451545.75,
        ),
    )

    response = client.post(
        "/v1/planetary-hours/hour-at",
        json={"jd": 2451544.0, "latitude": 0.0, "longitude": 0.0},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["hour"] is None
    assert body["schedule_window"]["contains_requested_jd"] is False


def test_hour_at_route_can_include_schedule(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "moira_server.services.planetary_hours.planetary_hours",
        lambda jd, lat, lon, reader=None: _make_day(requested_jd=jd),
    )

    response = client.post(
        "/v1/planetary-hours/hour-at",
        json={
            "jd": 2451545.5,
            "latitude": 0.0,
            "longitude": 0.0,
            "include_schedule": True,
        },
    )

    assert response.status_code == 200
    assert len(response.json()["schedule"]["hours"]) == 24


def test_before_sunrise_input_preserves_previous_sunrise_window(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "moira_server.services.planetary_hours.planetary_hours",
        lambda jd, lat, lon, reader=None: _make_day(
            requested_jd=jd,
            sunrise_jd=2451544.20,
            sunset_jd=2451544.70,
        ),
    )

    response = client.post(
        "/v1/planetary-hours/schedule",
        json={"jd": 2451545.10, "latitude": 0.0, "longitude": 0.0},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["sunrise_jd"] == pytest.approx(2451544.20)
    assert body["sunset_jd"] == pytest.approx(2451544.70)
    assert body["next_sunrise_jd"] == pytest.approx(2451545.20)


def test_explicit_server_reader_is_passed_to_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    explicit_reader = object()
    seen = {}

    def fake_planetary_hours(jd, lat, lon, reader=None):
        seen["reader"] = reader
        return _make_day(requested_jd=jd, latitude=lat, longitude=lon)

    monkeypatch.setattr("moira_server.app.create_engine", lambda config: _FakeEngine(explicit_reader))
    monkeypatch.setattr(
        "moira_server.services.planetary_hours.planetary_hours",
        fake_planetary_hours,
    )
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        response = client.post(
            "/v1/planetary-hours/schedule",
            json={"jd": 2451545.5, "latitude": 0.0, "longitude": 0.0},
        )

    assert response.status_code == 200
    assert seen["reader"] is explicit_reader
    assert response.json()["provenance"]["reader_policy"] == "server_explicit_reader"


def test_sunrise_resolution_failure_is_visible_without_fallback(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(jd, lat, lon, reader=None):
        raise RuntimeError("no sunrise for requested latitude")

    monkeypatch.setattr("moira_server.services.planetary_hours.planetary_hours", fail)

    response = client.post(
        "/v1/planetary-hours/schedule",
        json={"jd": 2451545.5, "latitude": 89.0, "longitude": 0.0},
    )

    _assert_validation_envelope(
        response,
        message_fragment="planetary hours sunrise/sunset resolution failed",
    )
    assert "no sunrise" in response.json()["message"]


def test_planetary_hours_routes_reject_invalid_inputs(client: TestClient) -> None:
    non_finite_jd = client.post(
        "/v1/planetary-hours/schedule",
        json={"jd": "NaN", "latitude": 0.0, "longitude": 0.0},
    )
    invalid_lat = client.post(
        "/v1/planetary-hours/schedule",
        json={"jd": 2451545.5, "latitude": 90.1, "longitude": 0.0},
    )
    invalid_lon = client.post(
        "/v1/planetary-hours/schedule",
        json={"jd": 2451545.5, "latitude": 0.0, "longitude": 180.1},
    )
    bad_include_iso = client.post(
        "/v1/planetary-hours/schedule",
        json={
            "jd": 2451545.5,
            "latitude": 0.0,
            "longitude": 0.0,
            "include_iso_utc": "yes",
        },
    )
    bad_include_schedule = client.post(
        "/v1/planetary-hours/hour-at",
        json={
            "jd": 2451545.5,
            "latitude": 0.0,
            "longitude": 0.0,
            "include_schedule": 1,
        },
    )

    _assert_validation_envelope(non_finite_jd, message_fragment="jd must be finite")
    _assert_validation_envelope(invalid_lat, message_fragment="less than or equal to 90")
    _assert_validation_envelope(invalid_lon, message_fragment="less than or equal to 180")
    _assert_validation_envelope(bad_include_iso, message_fragment="include_iso_utc must be a boolean")
    _assert_validation_envelope(
        bad_include_schedule,
        message_fragment="include_schedule must be a boolean",
    )


def test_planetary_hours_routes_are_registered(client: TestClient) -> None:
    paths = {
        route.path
        for route in client.app.routes
        if route.path.startswith("/v1/planetary-hours/")
    }

    assert paths == {
        "/v1/planetary-hours/schedule",
        "/v1/planetary-hours/hour-at",
    }
