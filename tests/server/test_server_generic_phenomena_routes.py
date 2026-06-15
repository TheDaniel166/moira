from __future__ import annotations

from unittest.mock import ANY

from fastapi.testclient import TestClient
import pytest

from moira.dignities_types import SolarConditionTruth
from moira.phenomena import PhenomenonEvent, PlanetPhenomena, ProximityEvent
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.network


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


def test_planet_phenomena_route_returns_snapshot_and_provenance(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, float]] = []

    def fake_planet_phenomena_at(body: str, jd_ut: float) -> PlanetPhenomena:
        calls.append((body, jd_ut))
        return PlanetPhenomena(
            body=body,
            jd_ut=jd_ut,
            phase_angle_deg=36.5,
            illuminated_fraction=0.91,
            elongation_deg=42.0,
            angular_diameter_arcsec=12.3,
            apparent_magnitude=-4.1,
        )

    monkeypatch.setattr(
        "moira_server.services.generic_phenomena.planet_phenomena_at",
        fake_planet_phenomena_at,
    )

    response = client.post(
        "/v1/phenomena/planet",
        json={"body": " Venus ", "jd_ut": 2451545.0},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["request"] == {"body": "Venus", "jd_ut": 2451545.0}
    assert body["phenomena"] == {
        "body": "Venus",
        "jd_ut": 2451545.0,
        "phase_angle_deg": 36.5,
        "illuminated_fraction": 0.91,
        "elongation_deg": 42.0,
        "angular_diameter_arcsec": 12.3,
        "apparent_magnitude": -4.1,
    }
    provenance = body["provenance"]
    assert provenance["source_module"] == "moira.phenomena"
    assert provenance["engine_entrypoint"] == "planet_phenomena_at"
    assert provenance["reader_owner"] == "Moira engine instance"
    assert provenance["search_performed"] is False
    assert provenance["phase_photometry_source"] == "moira.phase"
    assert "engine_call" in provenance["stage_sequence"]
    assert calls == [("Venus", 2451545.0)]


def test_orbital_phenomena_events_route_filters_and_serializes_events(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str, float, object | None, float]] = []

    def fake_greatest_elongation(
        body: str,
        jd_start: float,
        *,
        direction: str,
        reader: object | None,
        max_days: float,
    ) -> PhenomenonEvent:
        calls.append(("elongation", direction, jd_start, reader, max_days))
        return PhenomenonEvent(
            body=body,
            phenomenon="Greatest Eastern Elongation",
            jd_ut=jd_start + 2.0,
            value=46.0,
        )

    def fake_perihelion(
        body: str,
        jd_start: float,
        *,
        reader: object | None,
        max_days: float,
    ) -> PhenomenonEvent:
        calls.append(("perihelion", body, jd_start, reader, max_days))
        return PhenomenonEvent(
            body=body,
            phenomenon="Perihelion",
            jd_ut=jd_start + 1.0,
            value=0.72,
        )

    monkeypatch.setattr(
        "moira_server.services.generic_phenomena.greatest_elongation",
        fake_greatest_elongation,
    )
    monkeypatch.setattr(
        "moira_server.services.generic_phenomena.perihelion",
        fake_perihelion,
    )

    response = client.post(
        "/v1/phenomena/orbital-events",
        json={
            "body": "Venus",
            "jd_start": 2451545.0,
            "jd_end": 2451575.0,
            "event_kinds": ["greatest_eastern_elongation", "perihelion"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert [event["event_kind"] for event in body["events"]] == [
        "perihelion",
        "greatest_eastern_elongation",
    ]
    assert [event["value_unit"] for event in body["events"]] == ["AU", "degrees"]
    assert body["provenance"]["product_kind"] == "bounded_orbital_event_search"
    assert body["provenance"]["search_span_days"] == 30.0
    assert calls == [
        ("elongation", "east", 2451545.0, ANY, 30.0),
        ("perihelion", "Venus", 2451545.0, ANY, 30.0),
    ]
    assert calls[0][3] is not None
    assert calls[1][3] is not None


def test_proximity_events_route_returns_threshold_crossings(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str, float, float, float, object | None]] = []

    def fake_proximity_events_in_range(
        body1: str,
        body2: str,
        jd_start: float,
        jd_end: float,
        *,
        threshold_deg: float,
        reader: object | None,
    ) -> list[ProximityEvent]:
        calls.append((body1, body2, jd_start, jd_end, threshold_deg, reader))
        return [
            ProximityEvent(
                body1=body1,
                body2=body2,
                jd_ut=2451546.0,
                threshold_deg=threshold_deg,
                body1_longitude=280.0,
                body2_longitude=282.0,
                body2_latitude=0.4,
                body2_retrograde=False,
                is_ingress=True,
                label="Mars enters 3.0 deg of Jupiter",
            )
        ]

    monkeypatch.setattr(
        "moira_server.services.generic_phenomena.proximity_events_in_range",
        fake_proximity_events_in_range,
    )

    response = client.post(
        "/v1/phenomena/proximity",
        json={
            "body1": "Mars",
            "body2": "Jupiter",
            "jd_start": 2451545.0,
            "jd_end": 2451555.0,
            "threshold_deg": 3.0,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["events"][0]["threshold_abs_deg"] == 3.0
    assert body["events"][0]["is_ingress"] is True
    assert body["provenance"]["event_direction_model"] == "ingress_when_separation_decreasing"
    assert calls == [("Mars", "Jupiter", 2451545.0, 2451555.0, 3.0, ANY)]
    assert calls[0][5] is not None


def test_solar_condition_instant_route_returns_truth_and_thresholds(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, float, object | None]] = []

    def fake_solar_condition_at(
        body: str,
        jd_ut: float,
        *,
        reader: object | None,
    ) -> SolarConditionTruth:
        calls.append((body, jd_ut, reader))
        return SolarConditionTruth(
            present=True,
            condition="cazimi",
            label="Cazimi",
            score=5,
            distance_from_sun=0.1,
        )

    monkeypatch.setattr(
        "moira_server.services.generic_phenomena.solar_condition_at",
        fake_solar_condition_at,
    )

    response = client.post(
        "/v1/solar-condition/instant",
        json={"body": "Mercury", "jd_ut": 2451545.0},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["solar_condition"] == {
        "body": "Mercury",
        "jd_ut": 2451545.0,
        "present": True,
        "condition": "cazimi",
        "label": "Cazimi",
        "score": 5,
        "distance_from_sun": 0.1,
        "distance_unit": "degrees",
    }
    assert body["provenance"]["thresholds_deg"]["cazimi"] == pytest.approx(17.0 / 60.0)
    assert body["provenance"]["luminary_policy"] == "Sun and Moon return absent truth"
    assert calls == [("Mercury", 2451545.0, ANY)]
    assert calls[0][2] is not None


def test_solar_condition_events_route_returns_condition_crossings(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, float, float, str, object | None]] = []

    def fake_solar_condition_events_in_range(
        body: str,
        jd_start: float,
        jd_end: float,
        *,
        condition: str,
        reader: object | None,
    ) -> list[ProximityEvent]:
        calls.append((body, jd_start, jd_end, condition, reader))
        return [
            ProximityEvent(
                body1="Sun",
                body2=body,
                jd_ut=2451549.0,
                threshold_deg=-8.0,
                body1_longitude=280.0,
                body2_longitude=288.0,
                body2_latitude=-0.2,
                body2_retrograde=True,
                is_ingress=False,
                label="Venus exits combust",
            )
        ]

    monkeypatch.setattr(
        "moira_server.services.generic_phenomena.solar_condition_events_in_range",
        fake_solar_condition_events_in_range,
    )

    response = client.post(
        "/v1/solar-condition/events",
        json={
            "body": "Venus",
            "jd_start": 2451545.0,
            "jd_end": 2451605.0,
            "condition": "combust",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["events"][0]["body1"] == "Sun"
    assert body["events"][0]["body2"] == "Venus"
    assert body["events"][0]["threshold_deg"] == -8.0
    assert body["events"][0]["threshold_abs_deg"] == 8.0
    assert body["provenance"]["product_kind"] == "classical_solar_condition_threshold_crossings"
    assert calls == [("Venus", 2451545.0, 2451605.0, "combust", ANY)]
    assert calls[0][4] is not None


@pytest.mark.parametrize(
    ("route", "payload"),
    [
        ("/v1/phenomena/planet", {"body": "Sun", "jd_ut": 2451545.0}),
        ("/v1/phenomena/planet", {"body": "Venus", "jd_ut": "NaN"}),
        (
            "/v1/phenomena/orbital-events",
            {
                "body": "Mars",
                "jd_start": 2451545.0,
                "jd_end": 2451555.0,
                "event_kinds": ["greatest_eastern_elongation"],
            },
        ),
        (
            "/v1/phenomena/proximity",
            {
                "body1": "Mars",
                "body2": "Mars",
                "jd_start": 2451545.0,
                "jd_end": 2451555.0,
                "threshold_deg": 3.0,
            },
        ),
        (
            "/v1/phenomena/proximity",
            {
                "body1": "Mars",
                "body2": "Jupiter",
                "jd_start": 2451545.0,
                "jd_end": 2451555.0,
                "threshold_deg": 31.0,
            },
        ),
        (
            "/v1/solar-condition/events",
            {
                "body": "Sun",
                "jd_start": 2451545.0,
                "jd_end": 2451555.0,
                "condition": "combust",
            },
        ),
        (
            "/v1/solar-condition/events",
            {
                "body": "Venus",
                "jd_start": 2451545.0,
                "jd_end": 2451555.0,
                "condition": "heliacal",
            },
        ),
    ],
)
def test_generic_phenomena_routes_reject_invalid_inputs(
    client: TestClient,
    route: str,
    payload: dict[str, object],
) -> None:
    response = client.post(route, json=payload)

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "validation_error"
    assert body["category"] == "input_validation"


def test_generic_phenomena_routes_reject_extra_fields(client: TestClient) -> None:
    response = client.post(
        "/v1/solar-condition/instant",
        json={"body": "Sun", "jd_ut": 2451545.0, "interpretation": True},
    )

    assert response.status_code == 422


def test_generic_phenomena_get_is_not_admitted(client: TestClient) -> None:
    assert client.get("/v1/phenomena/planet").status_code == 405
    assert client.get("/v1/phenomena/orbital-events").status_code == 405
    assert client.get("/v1/phenomena/proximity").status_code == 405
    assert client.get("/v1/solar-condition/instant").status_code == 405
    assert client.get("/v1/solar-condition/events").status_code == 405
