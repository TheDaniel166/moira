"""Frame-specific HTTP parity, admission and receipt checks."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json

from fastapi.testclient import TestClient
import pytest

from moira.julian import jd_from_datetime, tt_to_tdb, utc_to_tt, utc_to_ut1
from moira.planetocentric import VALID_OBSERVER_BODIES, all_planetocentric_at_with_truth
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


def _assert_validation_envelope(response, *, message_fragment: str | None = None) -> None:
    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "validation_error"
    assert body["category"] == "input_validation"
    assert body["request_id"]
    assert response.headers["X-Request-ID"] == body["request_id"]
    if message_fragment is not None:
        assert message_fragment in body["message"]


@pytest.mark.requires_ephemeris
def test_frame_heliocentric_route_matches_facade_for_explicit_bodies(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    direct = moira_engine.heliocentric(dt, bodies=["Mercury", "Mars"])

    response = client_with_engine.post(
        "/v1/positions/frame/heliocentric",
        json={"dt": dt.isoformat(), "bodies": ["Mercury", "Mars"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert list(body["positions"]) == ["Mercury", "Mars"]
    assert body["positions"]["Mercury"]["longitude"] == pytest.approx(direct["Mercury"].longitude)
    assert body["positions"]["Mars"]["distance_au"] == pytest.approx(direct["Mars"].distance_au)
    assert body["frame"]["center"] == "sun"
    assert body["frame"]["product_kind"] == "geometric_heliocentric_position"
    assert body["provenance"]["source_module"] == "moira.planets"
    assert body["provenance"]["kernel_mutation"] == "not_performed"


@pytest.mark.requires_ephemeris
def test_frame_heliocentric_route_supports_default_bodies(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/positions/frame/heliocentric",
        json={"dt": "2000-01-01T12:00:00+00:00"},
    )

    assert response.status_code == 200
    body = response.json()
    assert "Sun" not in body["positions"]
    assert "Moon" not in body["positions"]
    assert body["bounds"]["body_count"] == len(body["positions"])


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize(("year", "observer", "bodies", "center_id", "target_ids", "center_kind"), [
    (2000, "Mars", ["Jupiter", "Earth"], 4, [5, 399], "planetary_system_barycenter"),
    (100, "Earth", ["Moon", "Saturn"], 399, [301, 6], "body_center"),
])
def test_frame_planetocentric_route_matches_facade_and_reduction(
    client_with_engine: TestClient,
    moira_engine,
    year, observer, bodies, center_id, target_ids, center_kind,
) -> None:
    dt = datetime(year, 7, 1, 12, 0, tzinfo=timezone.utc)
    jd_utc = jd_from_datetime(dt)
    jd_ut1 = utc_to_ut1(jd_utc)
    direct = moira_engine.planetocentric(observer, dt, bodies=bodies)
    receipts = all_planetocentric_at_with_truth(
        observer, jd_ut1, bodies=bodies, reader=moira_engine._reader,
    )

    response = client_with_engine.post(
        "/v1/positions/frame/planetocentric",
        json={"dt": dt.isoformat(), "observer": observer, "bodies": bodies},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert list(body["positions"]) == bodies
    assert body["time"]["jd_tt"] == utc_to_tt(jd_utc)
    assert body["frame"]["center"] == observer
    assert body["provenance"]["engine_entrypoint"] == "all_planetocentric_at_with_truth"
    for name, target_id in zip(bodies, target_ids, strict=True):
        item = body["positions"][name]
        position = direct[name]
        assert item["observer"] == item["center"] == observer
        assert item["name"] == name
        assert item["longitude"] == position.longitude
        assert item["latitude"] == position.latitude
        assert item["distance_km"] == position.distance
        assert item["speed"] == position.speed
        assert item["retrograde"] is position.retrograde
        receipt = item["reduction"]
        assert receipt == json.loads(json.dumps(asdict(receipts[name].truth)))
        assert (receipt["center_body"], receipt["target_body"]) == (observer, name)
        assert (receipt["center_naif_id"], receipt["target_naif_id"]) == (center_id, target_id)
        assert receipt["center_kind"] == center_kind
        assert receipt["frame"]["result_frame"] == "true_ecliptic_and_equinox_of_date"
        assert receipt["frame"]["light_time_applied"] is False
        time = receipt["time_binding"]
        assert time["jd_ut1"] == jd_ut1
        assert time["jd_tdb"] == tt_to_tdb(time["jd_tt"])
        if year == 100:
            assert time["delta_t_retarget_mode"] == "declared"
            assert time["delta_t_correction_seconds"] > 26
            assert time["delta_t_kernel_identity"] == "DE-0441LE-0441"
            assert time["jd_tt"] > body["time"]["jd_tt"]
        else:
            assert time["delta_t_correction_seconds"] == 0
            assert time["delta_t_kernel_identity"] is None
        rate = receipt["rate_sampling"]
        assert rate["method"] == "instantaneous_state_vector"
        assert rate["ephemeris_state_samples_per_body"] == 1
        assert rate["frame_derivative_timescale"] == "TT"
        assert rate["frame_derivative_half_span_days"] == 0.001
        assert rate["frame_derivative_jd_tt"] == [time["jd_tt"] - 0.001, time["jd_tt"] + 0.001]


@pytest.mark.requires_ephemeris
def test_frame_planetocentric_default_bodies_all_have_receipts(client_with_engine):
    response = client_with_engine.post(
        "/v1/positions/frame/planetocentric",
        json={"dt": "2000-01-01T13:00:00+01:00", "observer": "Sun"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert list(body["positions"]) == sorted(VALID_OBSERVER_BODIES - {"Sun"})
    assert all(item["reduction"]["center_naif_id"] == 10 for item in body["positions"].values())
    assert body["bounds"]["body_count"] == len(body["positions"])


@pytest.mark.requires_ephemeris
def test_frame_ssb_route_includes_sun_and_matches_facade(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    direct = moira_engine.ssb_chart(dt, bodies=["Sun", "Earth"])

    response = client_with_engine.post(
        "/v1/positions/frame/ssb",
        json={"dt": dt.isoformat(), "bodies": ["Sun", "Earth"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert list(body["positions"]) == ["Sun", "Earth"]
    assert body["positions"]["Sun"]["longitude"] == pytest.approx(direct["Sun"].longitude)
    assert body["positions"]["Earth"]["distance_km"] == pytest.approx(direct["Earth"].distance)
    assert body["frame"]["center"] == "solar_system_barycenter"
    assert body["provenance"]["source_module"] == "moira.ssb"


@pytest.mark.requires_ephemeris
def test_frame_received_light_route_matches_facade_for_outer_planet(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    direct = moira_engine.received_light(dt, bodies=["Jupiter"])

    response = client_with_engine.post(
        "/v1/positions/frame/received-light",
        json={"dt": dt.isoformat(), "bodies": ["Jupiter"]},
    )

    assert response.status_code == 200
    body = response.json()
    position = body["positions"]["Jupiter"]
    assert position["apparent_longitude"] == pytest.approx(direct["Jupiter"].apparent_longitude)
    assert position["geometric_longitude"] == pytest.approx(direct["Jupiter"].geometric_longitude)
    assert position["light_travel_minutes"] == pytest.approx(direct["Jupiter"].light_travel_minutes)
    assert body["frame"]["light_time_corrected"] is True
    assert body["frame"]["geometric_comparison_included"] is True
    assert body["provenance"]["source_module"] == "moira.light_cone"


@pytest.mark.requires_ephemeris
def test_frame_position_time_metadata_reports_ut1(
    client_with_engine: TestClient,
) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    jd_utc = jd_from_datetime(dt)

    response = client_with_engine.post(
        "/v1/positions/frame/ssb",
        json={"dt": dt.isoformat(), "bodies": ["Sun"]},
    )

    assert response.status_code == 200
    time = response.json()["time"]
    assert time["jd_ut"] == pytest.approx(utc_to_ut1(jd_utc), abs=1.0e-12)
    assert time["jd_tt"] == pytest.approx(utc_to_tt(jd_utc), abs=1.0e-12)


def test_frame_position_compute_routes_do_not_admit_get(client_with_engine: TestClient) -> None:
    response = client_with_engine.get("/v1/positions/frame/heliocentric")

    assert response.status_code == 405


def test_frame_positions_reject_naive_datetime(client_with_engine: TestClient) -> None:
    response = client_with_engine.post(
        "/v1/positions/frame/ssb",
        json={"dt": "2000-01-01T12:00:00", "bodies": ["Sun"]},
    )

    _assert_validation_envelope(response, message_fragment="timezone-aware")


def test_frame_positions_reject_duplicate_bodies(client_with_engine: TestClient) -> None:
    response = client_with_engine.post(
        "/v1/positions/frame/ssb",
        json={"dt": "2000-01-01T12:00:00+00:00", "bodies": ["Mars", " Mars "]},
    )

    _assert_validation_envelope(response, message_fragment="unique after trimming")


def test_frame_positions_reject_body_cap(client_with_engine: TestClient) -> None:
    response = client_with_engine.post(
        "/v1/positions/frame/ssb",
        json={
            "dt": "2000-01-01T12:00:00+00:00",
            "bodies": [f"Body{i}" for i in range(13)],
        },
    )

    _assert_validation_envelope(response, message_fragment="at most 12")


def test_frame_heliocentric_rejects_sun_and_moon(client_with_engine: TestClient) -> None:
    sun_response = client_with_engine.post(
        "/v1/positions/frame/heliocentric",
        json={"dt": "2000-01-01T12:00:00+00:00", "bodies": ["Sun"]},
    )
    moon_response = client_with_engine.post(
        "/v1/positions/frame/heliocentric",
        json={"dt": "2000-01-01T12:00:00+00:00", "bodies": ["Moon"]},
    )

    _assert_validation_envelope(sun_response, message_fragment="do not admit Sun or Moon")
    _assert_validation_envelope(moon_response, message_fragment="do not admit Sun or Moon")


def test_frame_planetocentric_rejects_observer_equal_to_target(client_with_engine: TestClient) -> None:
    response = client_with_engine.post(
        "/v1/positions/frame/planetocentric",
        json={"dt": "2000-01-01T12:00:00+00:00", "observer": "Mars", "bodies": ["Mars"]},
    )

    _assert_validation_envelope(response, message_fragment="must not include the observer")


def test_frame_received_light_rejects_nonphysical_point(client_with_engine: TestClient) -> None:
    response = client_with_engine.post(
        "/v1/positions/frame/received-light",
        json={"dt": "2000-01-01T12:00:00+00:00", "bodies": ["True Node"]},
    )

    _assert_validation_envelope(response, message_fragment="unsupported received-light bodies")
