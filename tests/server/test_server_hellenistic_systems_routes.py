"""REST admission tests for circumambulations, transmissions, and offices."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from moira.circumambulations import circumambulate
from moira.egyptian_bounds import EgyptianBoundsDoctrine, EgyptianBoundsPolicy
from moira.hellenistic_offices import OFFICE_NOT_ADMITTED_REASON
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.loopback


class _FakeEngine:
    pass


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: _FakeEngine())
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as test_client:
        yield test_client


def test_circumambulations_route_preserves_bound_walk(client: TestClient) -> None:
    direct = circumambulate(10.0, 2451545.0, significator_name="Ascendant")
    response = client.post(
        "/v1/hellenistic/circumambulations",
        json={
            "significator_name": "Ascendant",
            "significator_longitude": 10.0,
            "start_jd": 2451545.0,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "evaluated"
    assert body["periods"][0]["lord"] == direct.periods[0].lord
    assert body["periods"][0]["years"] == pytest.approx(direct.periods[0].years or 0.0)
    assert body["provenance"]["engine_entrypoint"] == "circumambulate"


def test_circumambulations_route_fallbacks_scaling_and_refusals(client: TestClient) -> None:
    request = {"significator_name": "Ascendant", "significator_longitude": 370.5, "start_jd": 2451545.0}

    def post(**fields):
        return client.post("/v1/hellenistic/circumambulations", json={**request, **fields})

    solar = post(year_days=365.25, bounds_doctrine="ptolemaic").json()
    direct = circumambulate(10.5, 2451545.0, significator_name="Ascendant", year_days=365.25,
                            bounds_policy=EgyptianBoundsPolicy(doctrine=EgyptianBoundsDoctrine.PTOLEMAIC))
    assert solar["significator_longitude"] == 10.5 and solar["bounds_doctrine"] == "ptolemaic"
    assert sum(p["span_deg"] for p in solar["periods"]) == pytest.approx(360.0)
    assert [p["lord"] for p in solar["periods"]] == [p.lord for p in direct.periods]
    first = solar["periods"][0]
    assert first["end_jd"] - first["start_jd"] == pytest.approx(first["years"] * 365.25)

    for key, reason in (("rising_times", "rising_time_table_not_admitted"),
                        ("equatorial", "equatorial_key_is_primary_direction")):
        withheld = post(time_key=key)
        assert withheld.status_code == 200
        assert withheld.json()["status"] == "not_evaluable"
        assert withheld.json()["reason"] == reason and withheld.json()["periods"] == []

    for refused in (post(year_days=0.0), post(time_key="ascensional"), post(bounds_doctrine="babylonian"),
                    post(significator_name=" "), post(extra=1)):
        assert refused.status_code == 422
        assert refused.json()["error_code"] == "validation_error"


def test_transmissions_route_has_no_effect_fields(client: TestClient) -> None:
    response = client.post(
        "/v1/hellenistic/transmissions",
        json={
            "positions": {"Sun": 10.0, "Moon": 45.0},
            "asc_longitude": 15.0,
            "decennial_l1": "Sun",
            "decennial_l2": "Moon",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "evaluated"
    assert body["edges"]
    assert "effect" not in body
    assert all("effect" not in edge for edge in body["edges"])


def test_offices_route_names_the_missing_ptolemy_input(client: TestClient) -> None:
    response = client.post(
        "/v1/hellenistic/offices",
        json={
            "positions": {
                "Sun": 10.0,
                "Moon": 45.0,
                "Mercury": 80.0,
                "Venus": 120.0,
                "Mars": 160.0,
                "Jupiter": 220.0,
                "Saturn": 300.0,
            },
            "is_day_chart": True,
            "asc_longitude": 15.0,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "not_evaluable"
    assert body["predominator"] is None
    assert body["house_master"] is None
    assert body["house_master_reason"] == OFFICE_NOT_ADMITTED_REASON
    assert body["reason"] == "prenatal_new_moon_longitude_required_for_ruler_over_luminary_check"
    assert body["predominator_determination"]["doctrine"] == "ptolemy_tetrabiblos_iii_10"
    assert body["candidates"]


def test_offices_route_selects_ptolemy_predominator(client: TestClient) -> None:
    response = client.post(
        "/v1/hellenistic/offices",
        json={
            "positions": {
                "Sun": 10.0,
                "Moon": 100.0,
                "Mercury": 20.0,
                "Venus": 40.0,
                "Mars": 80.0,
                "Jupiter": 200.0,
                "Saturn": 300.0,
            },
            "is_day_chart": True,
            "asc_longitude": 200.0,
            "prenatal_new_moon_longitude": 355.0,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "selected"
    assert body["predominator"] == "Venus"
    assert body["reason"] is None
    determination = body["predominator_determination"]
    assert determination["selection_step"] == "ruler_preferred_over_luminary"
    assert determination["ruler_candidates"] == ["Venus"]
    assert "Tetrabiblos III.10" in body["provenance"]["source_refs"][0]


def test_hellenistic_system_routes_are_registered(client: TestClient) -> None:
    paths = {route.path for route in client.app.routes}
    assert {
        "/v1/hellenistic/circumambulations",
        "/v1/hellenistic/transmissions",
        "/v1/hellenistic/offices",
    } <= paths


def test_system_routes_reject_extra_keys(client: TestClient) -> None:
    response = client.post(
        "/v1/hellenistic/offices",
        json={
            "positions": {"Sun": 10.0},
            "is_day_chart": True,
            "hyleg": "Sun",
        },
    )
    assert response.status_code == 422
    assert "Extra inputs are not permitted" in response.json()["message"]
