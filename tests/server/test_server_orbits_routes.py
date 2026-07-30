from __future__ import annotations

from unittest.mock import ANY

from fastapi.testclient import TestClient
import pytest

from moira.orbits import DistanceExtremes, KeplerianElements
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.loopback


class _FakeReader:
    pass


class _FakeEngine:
    def __init__(self) -> None:
        self._reader = _FakeReader()


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: _FakeEngine())
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as test_client:
        yield test_client


def test_orbital_elements_route_returns_engine_elements_and_provenance(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, float, object | None]] = []

    def fake_orbital_elements_at(
        body: str,
        jd_ut: float,
        reader: object | None,
    ) -> KeplerianElements:
        calls.append((body, jd_ut, reader))
        return KeplerianElements(
            name=body,
            epoch_jd=jd_ut,
            semi_major_axis_au=1.000001,
            eccentricity=0.0167,
            inclination_deg=0.0001,
            lon_ascending_node_deg=174.9,
            arg_perihelion_deg=288.1,
            mean_anomaly_deg=357.5,
            mean_motion_deg_per_day=0.9856,
            orbital_period_days=365.25,
        )

    monkeypatch.setattr(
        "moira_server.services.orbits.orbital_elements_at",
        fake_orbital_elements_at,
    )

    response = client.post(
        "/v1/orbits/elements",
        json={"body": " Earth ", "jd_ut": 2451545.0},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["request"] == {"body": "Earth", "jd_ut": 2451545.0}
    assert body["time"] == {
        "input_time_scale": "UT_JD",
        "state_evaluation_scale": "TT_internal",
        "delta_t_policy": "engine_default",
    }
    assert body["elements"] == {
        "name": "Earth",
        "epoch_jd": 2451545.0,
        "semi_major_axis_au": 1.000001,
        "eccentricity": 0.0167,
        "inclination_deg": 0.0001,
        "lon_ascending_node_deg": 174.9,
        "arg_perihelion_deg": 288.1,
        "mean_anomaly_deg": 357.5,
        "mean_motion_deg_per_day": 0.9856,
        "orbital_period_days": 365.25,
        "perihelion_distance_au": pytest.approx(0.9833009833),
        "aphelion_distance_au": pytest.approx(1.0167010167),
    }
    provenance = body["provenance"]
    assert provenance["source_module"] == "moira.orbits"
    assert provenance["engine_entrypoint"] == "orbital_elements_at"
    assert provenance["reader_owner"] == "Moira engine instance"
    assert provenance["center"] == "sun"
    assert provenance["frame"] == "J2000_ecliptic_and_equinox"
    assert provenance["element_type"] == "osculating"
    assert provenance["state_source"] == "DE_series_kernel"
    assert provenance["apparent_corrections"] == "not_applied"
    assert provenance["light_time_correction"] == "not_applied"
    assert provenance["mean_element_table"] == "not_used"
    assert provenance["event_basis"] is None
    assert provenance["stage_sequence"] == [
        "input_validation",
        "reader_binding",
        "engine_call",
        "elements_serialization",
        "provenance_serialization",
    ]
    assert calls == [("Earth", 2451545.0, ANY)]
    assert calls[0][2] is not None


def test_orbital_elements_route_handles_outer_planet(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_orbital_elements_at(
        body: str,
        jd_ut: float,
        reader: object | None,
    ) -> KeplerianElements:
        return KeplerianElements(
            name=body,
            epoch_jd=jd_ut,
            semi_major_axis_au=5.2,
            eccentricity=0.049,
            inclination_deg=1.3,
            lon_ascending_node_deg=100.5,
            arg_perihelion_deg=273.8,
            mean_anomaly_deg=20.0,
            mean_motion_deg_per_day=0.083,
            orbital_period_days=4332.6,
        )

    monkeypatch.setattr(
        "moira_server.services.orbits.orbital_elements_at",
        fake_orbital_elements_at,
    )

    response = client.post(
        "/v1/orbits/elements",
        json={"body": "Jupiter", "jd_ut": 2451545.0},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["elements"]["name"] == "Jupiter"
    assert body["elements"]["semi_major_axis_au"] == 5.2
    assert body["elements"]["perihelion_distance_au"] == pytest.approx(4.9452)
    assert body["elements"]["aphelion_distance_au"] == pytest.approx(5.4548)


def test_distance_extremes_route_returns_engine_extremes_and_curve_provenance(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, float, object | None]] = []

    def fake_distance_extremes_at(
        body: str,
        jd_ut: float,
        reader: object | None,
    ) -> DistanceExtremes:
        calls.append((body, jd_ut, reader))
        return DistanceExtremes(
            name=body,
            perihelion_jd=2451600.25,
            perihelion_distance_au=0.98329,
            aphelion_jd=2451782.75,
            aphelion_distance_au=1.01671,
        )

    monkeypatch.setattr(
        "moira_server.services.orbits.distance_extremes_at",
        fake_distance_extremes_at,
    )

    response = client.post(
        "/v1/orbits/distance-extremes",
        json={"body": "Venus", "jd_ut": 2451545.0},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["request"] == {"body": "Venus", "jd_ut": 2451545.0}
    assert body["distance_extremes"] == {
        "name": "Venus",
        "perihelion_jd": 2451600.25,
        "perihelion_distance_au": 0.98329,
        "aphelion_jd": 2451782.75,
        "aphelion_distance_au": 1.01671,
    }
    provenance = body["provenance"]
    assert provenance["engine_entrypoint"] == "distance_extremes_at"
    assert provenance["event_basis"] == "live_heliocentric_distance_curve"
    assert provenance["search_direction"] == "forward_from_jd_ut"
    assert provenance["search_owner"] == "moira.phenomena"
    assert provenance["perihelion_event"] == "next_local_minimum"
    assert provenance["aphelion_event"] == "next_local_maximum"
    assert provenance["chronological_order_forced"] is False
    assert provenance["stage_sequence"] == [
        "input_validation",
        "reader_binding",
        "engine_call",
        "distance_extrema_serialization",
        "provenance_serialization",
    ]
    assert calls == [("Venus", 2451545.0, ANY)]
    assert calls[0][2] is not None


@pytest.mark.parametrize(
    ("payload", "message_fragment"),
    [
        ({"body": "Sun", "jd_ut": 2451545.0}, "body must be one of"),
        ({"body": "Moon", "jd_ut": 2451545.0}, "body must be one of"),
        ({"body": "Ceres", "jd_ut": 2451545.0}, "body must be one of"),
        ({"body": " ", "jd_ut": 2451545.0}, "body must be non-empty"),
        ({"body": "Earth", "jd_ut": "NaN"}, "jd_ut must be finite"),
    ],
)
def test_orbits_routes_reject_invalid_inputs(
    client: TestClient,
    payload: dict[str, object],
    message_fragment: str,
) -> None:
    elements = client.post("/v1/orbits/elements", json=payload)
    extremes = client.post("/v1/orbits/distance-extremes", json=payload)

    assert elements.status_code == 422
    assert extremes.status_code == 422
    assert message_fragment in elements.json()["message"]
    assert message_fragment in extremes.json()["message"]


def test_orbits_routes_reject_extra_fields(client: TestClient) -> None:
    elements = client.post(
        "/v1/orbits/elements",
        json={"body": "Earth", "jd_ut": 2451545.0, "frame": "mean"},
    )
    extremes = client.post(
        "/v1/orbits/distance-extremes",
        json={"body": "Earth", "jd_ut": 2451545.0, "frame": "mean"},
    )

    assert elements.status_code == 422
    assert extremes.status_code == 422


def test_orbits_get_is_not_admitted(client: TestClient) -> None:
    assert client.get("/v1/orbits/elements").status_code == 405
    assert client.get("/v1/orbits/distance-extremes").status_code == 405
