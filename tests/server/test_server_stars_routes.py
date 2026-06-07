from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient
import pytest

from moira.julian import jd_from_datetime, ut_to_tt
from moira.multiple_stars import (
    angular_separation_at,
    combined_magnitude,
    components_at,
    is_resolvable,
    multiple_star,
    position_angle_at,
)
from moira.stars import star_at
from moira.variable_stars import (
    catalog_profile,
    list_variable_stars,
    maxima_in_range,
    minima_in_range,
    next_maximum,
    next_minimum,
    star_condition_profile,
    star_state_pair,
    variable_star,
)
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.network


@pytest.fixture
def client_with_engine(
    moira_engine,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        yield client


def test_server_startup_includes_stars_router(
    moira_engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)

    app = create_app(ServerConfig(docs_enabled=True))
    with TestClient(app) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/v1/stars/position" in paths
    assert "/v1/stars/bulk" in paths
    assert "/v1/stars/list" in paths
    assert "/v1/stars/variable/state" in paths
    assert "/v1/stars/variable/catalog-profile" in paths
    assert "/v1/stars/multiple/state" in paths


@pytest.mark.requires_ephemeris
def test_star_position_route_converts_transport_datetime_to_jd_tt(
    client_with_engine: TestClient,
) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    jd_tt = ut_to_tt(jd_from_datetime(dt))
    direct = star_at("Sirius", jd_tt)

    response = client_with_engine.post(
        "/v1/stars/position",
        json={
            "dt": dt.isoformat(),
            "star": "Sirius",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == direct.name
    assert body["longitude"] == pytest.approx(direct.longitude)
    assert body["latitude"] == pytest.approx(direct.latitude)
    assert body["magnitude"] == pytest.approx(direct.magnitude)


@pytest.mark.requires_ephemeris
def test_stars_bulk_route_preserves_valid_results_and_collects_missing_names(
    client_with_engine: TestClient,
) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    jd_tt = ut_to_tt(jd_from_datetime(dt))
    direct = star_at("Sirius", jd_tt)

    response = client_with_engine.post(
        "/v1/stars/bulk",
        json={
            "dt": dt.isoformat(),
            "stars": ["Sirius", "DefinitelyNotAStar"],
            "skip_missing": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert "Sirius" in body["results"]
    assert body["results"]["Sirius"]["longitude"] == pytest.approx(direct.longitude)
    assert body["missing"] == ["DefinitelyNotAStar"]


def test_variable_star_catalog_route_preserves_catalog_truth(
    client_with_engine: TestClient,
) -> None:
    direct = variable_star("Algol")

    response = client_with_engine.get("/v1/stars/variable/Algol")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == direct.name
    assert body["designation"] == direct.designation
    assert body["var_type"] == direct.var_type
    assert body["classical_quality"] == direct.classical_quality
    assert body["amplitude"] == pytest.approx(direct.amplitude)
    assert body["type_class"] == direct.type_class


def test_variable_star_state_route_matches_engine_condition(
    client_with_engine: TestClient,
) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    jd = jd_from_datetime(dt)
    star = variable_star("Algol")
    direct = star_condition_profile(star, jd)

    response = client_with_engine.post(
        "/v1/stars/variable/state",
        json={"dt": dt.isoformat(), "star": "Algol"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["star"]["name"] == "Algol"
    assert body["condition"]["phase"] == pytest.approx(direct.phase)
    assert body["condition"]["magnitude"] == pytest.approx(direct.magnitude)
    assert body["condition"]["malefic_score"] == pytest.approx(direct.malefic_score)
    assert body["condition"]["benefic_score"] == pytest.approx(direct.benefic_score)
    assert body["condition"]["in_eclipse"] is direct.in_eclipse
    assert body["next_minimum_jd"] == pytest.approx(next_minimum(star, jd))
    assert body["next_maximum_jd"] == pytest.approx(next_maximum(star, jd))


def test_variable_star_range_route_matches_engine_extrema(
    client_with_engine: TestClient,
) -> None:
    star = variable_star("Algol")
    jd_start = 2451545.0
    jd_end = jd_start + 10.0

    response = client_with_engine.post(
        "/v1/stars/variable/range",
        json={"star": "Algol", "jd_start": jd_start, "jd_end": jd_end},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["star"] == "Algol"
    assert body["minima_jd"] == pytest.approx(minima_in_range(star, jd_start, jd_end))
    assert body["maxima_jd"] == pytest.approx(maxima_in_range(star, jd_start, jd_end))


def test_variable_star_range_route_rejects_reversed_window(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/stars/variable/range",
        json={"star": "Algol", "jd_start": 2451555.0, "jd_end": 2451545.0},
    )

    assert response.status_code == 422
    assert "jd_end" in response.json()["message"]


def test_variable_star_catalog_profile_route_matches_engine_aggregate(
    client_with_engine: TestClient,
) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    direct = catalog_profile(jd_from_datetime(dt))

    response = client_with_engine.post(
        "/v1/stars/variable/catalog-profile",
        json={"dt": dt.isoformat()},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["star_count"] == direct.star_count
    assert body["star_count"] == len(list_variable_stars())
    assert body["eclipsing_count"] == direct.eclipsing_count
    assert body["eclipse_active_count"] == direct.eclipse_active_count
    assert body["has_active_eclipses"] is direct.has_active_eclipses


def test_variable_star_pair_route_matches_engine_pair(
    client_with_engine: TestClient,
) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    direct = star_state_pair(variable_star("Algol"), variable_star("Mira"), jd_from_datetime(dt))

    response = client_with_engine.post(
        "/v1/stars/variable/pair",
        json={"dt": dt.isoformat(), "primary": "Algol", "secondary": "Mira"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["primary"]["name"] == direct.primary.name
    assert body["secondary"]["name"] == direct.secondary.name
    assert body["is_same_type_class"] is direct.is_same_type_class
    assert body["is_same_quality"] is direct.is_same_quality
    assert body["quality_conflict"] is direct.quality_conflict


def test_multiple_star_catalog_route_preserves_components_and_orbits(
    client_with_engine: TestClient,
) -> None:
    direct = multiple_star("Sirius")

    response = client_with_engine.get("/v1/stars/multiple/Sirius")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == direct.name
    assert body["designation"] == direct.designation
    assert body["system_type"] == direct.system_type
    assert body["combined_mag"] == pytest.approx(direct.combined_mag)
    assert body["computed_combined_magnitude"] == pytest.approx(combined_magnitude(direct))
    assert body["components"][0]["label"] == direct.components[0].label
    assert body["orbits"][0]["label"] == direct.orbits[0].label


def test_multiple_star_state_route_matches_engine_snapshot(
    client_with_engine: TestClient,
) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    jd = jd_from_datetime(dt)
    system = multiple_star("Sirius")
    snapshot = components_at(system, jd)

    response = client_with_engine.post(
        "/v1/stars/multiple/state",
        json={"dt": dt.isoformat(), "system": "Sirius", "aperture_mm": 100.0},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["system"]["name"] == "Sirius"
    assert body["separation_arcsec"] == pytest.approx(angular_separation_at(system, jd))
    assert body["position_angle_deg"] == pytest.approx(position_angle_at(system, jd))
    assert body["separation_arcsec"] == pytest.approx(snapshot["separation_arcsec"])
    assert body["position_angle_deg"] == pytest.approx(snapshot["position_angle_deg"])
    assert body["is_resolvable"] is is_resolvable(system, jd, 100.0)
    assert body["dominant_component"] == snapshot["dominant_component"]
    assert "A" in body["components"]


def test_multiple_star_state_route_rejects_non_positive_aperture(
    client_with_engine: TestClient,
) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)

    response = client_with_engine.post(
        "/v1/stars/multiple/state",
        json={"dt": dt.isoformat(), "system": "Sirius", "aperture_mm": 0.0},
    )

    assert response.status_code == 422
    assert "aperture_mm" in response.json()["message"]
