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


def _assert_validation_envelope(response, *, message_fragment: str) -> None:
    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "validation_error"
    assert body["category"] == "input_validation"
    assert message_fragment in body["message"]


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
    provenance = body["provenance"]
    assert provenance["coordinate_source"] == "sovereign_star_registry"
    assert provenance["source"] == direct.source
    assert provenance["source_mode"] == direct.computation_truth.source_mode
    assert provenance["lookup_kind"] == direct.computation_truth.lookup_kind
    assert provenance["hipparcos_name"] == direct.computation_truth.hipparcos_name
    assert provenance["gaia_match_status"] == direct.computation_truth.gaia_match_status
    assert provenance["source_kind"] == direct.classification.source_kind
    assert provenance["merge_state"] == direct.classification.merge_state
    assert provenance["observer_mode"] == direct.classification.observer_mode
    assert provenance["relation_kind"] == direct.relation.kind
    assert provenance["relation_basis"] == direct.relation.basis
    assert provenance["condition_result_kind"] == direct.condition_profile.result_kind
    assert provenance["condition_state"] == direct.condition_profile.condition_state.name
    assert provenance["jd_tt"] == pytest.approx(jd_tt)
    assert provenance["stage_sequence"][0] == "datetime_validation"


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
    assert body["results"]["Sirius"]["provenance"]["coordinate_source"] == "sovereign_star_registry"
    assert body["results"]["Sirius"]["provenance"]["lookup_kind"] == direct.computation_truth.lookup_kind
    assert body["missing"] == ["DefinitelyNotAStar"]


def test_star_position_route_rejects_naive_datetime(client_with_engine: TestClient) -> None:
    response = client_with_engine.post(
        "/v1/stars/position",
        json={"dt": "2000-01-01T12:00:00", "star": "Sirius"},
    )

    _assert_validation_envelope(response, message_fragment="timezone-aware")


def test_star_position_route_rejects_empty_star_name(client_with_engine: TestClient) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)

    response = client_with_engine.post(
        "/v1/stars/position",
        json={"dt": dt.isoformat(), "star": "   "},
    )

    _assert_validation_envelope(response, message_fragment="star must be non-empty")


def test_stars_bulk_route_rejects_empty_star_list(client_with_engine: TestClient) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)

    response = client_with_engine.post(
        "/v1/stars/bulk",
        json={"dt": dt.isoformat(), "stars": [], "skip_missing": True},
    )

    _assert_validation_envelope(response, message_fragment="at least 1 item")


def test_stars_bulk_route_rejects_empty_star_entry(client_with_engine: TestClient) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)

    response = client_with_engine.post(
        "/v1/stars/bulk",
        json={"dt": dt.isoformat(), "stars": ["Sirius", " "], "skip_missing": True},
    )

    _assert_validation_envelope(response, message_fragment="stars entries must be non-empty")


def test_stars_bulk_route_rejects_oversized_star_list(client_with_engine: TestClient) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)

    response = client_with_engine.post(
        "/v1/stars/bulk",
        json={
            "dt": dt.isoformat(),
            "stars": [f"Star{i}" for i in range(501)],
            "skip_missing": True,
        },
    )

    _assert_validation_envelope(response, message_fragment="at most 500 items")


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
    provenance = body["provenance"]
    assert provenance["catalog_source"] == ["GCVS", "AAVSO VSX", "published_linear_ephemerides"]
    assert provenance["var_type"] == direct.var_type
    assert provenance["epoch_jd"] == pytest.approx(direct.epoch_jd)
    assert provenance["epoch_is_minimum"] is direct.epoch_is_minimum
    assert provenance["period_days"] == pytest.approx(direct.period_days)
    assert provenance["stage_sequence"][0] == "variable_star_catalog_resolution"


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
    provenance = body["provenance"]
    assert provenance["computation_source"] == "variable_star_oracle"
    assert provenance["catalog_source"] == ["GCVS", "AAVSO VSX", "published_linear_ephemerides"]
    assert provenance["requested_stars"] == ["Algol"]
    assert provenance["returned_stars"] == ["Algol"]
    assert provenance["jd"] == pytest.approx(jd)
    assert provenance["eclipse_threshold"] == pytest.approx(0.05)
    assert provenance["stage_sequence"][0] == "datetime_validation"


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
    provenance = body["provenance"]
    assert provenance["computation_source"] == "variable_star_oracle"
    assert provenance["requested_stars"] == ["Algol"]
    assert provenance["returned_stars"] == ["Algol"]
    assert "jd_range_validation" in provenance["stage_sequence"]


def test_variable_star_range_route_rejects_reversed_window(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/stars/variable/range",
        json={"star": "Algol", "jd_start": 2451555.0, "jd_end": 2451545.0},
    )

    assert response.status_code == 422
    assert "jd_end" in response.json()["message"]


def test_variable_star_range_route_rejects_oversized_window(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/stars/variable/range",
        json={"star": "Algol", "jd_start": 2451545.0, "jd_end": 2451545.0 + 367.0},
    )

    _assert_validation_envelope(response, message_fragment="at most 366 days")


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
    provenance = body["provenance"]
    assert provenance["computation_source"] == "variable_star_oracle"
    assert provenance["returned_stars"] == list_variable_stars()
    assert provenance["jd"] == pytest.approx(jd_from_datetime(dt))
    assert provenance["stage_sequence"][0] == "datetime_validation"


def test_variable_star_list_route_exposes_catalog_names(
    client_with_engine: TestClient,
) -> None:
    direct = list_variable_stars()[:5]

    response = client_with_engine.get("/v1/stars/variable/list?limit=5")

    assert response.status_code == 200
    body = response.json()
    assert body["stars"] == direct
    assert body["total"] == len(direct)


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
    provenance = body["provenance"]
    assert provenance["computation_source"] == "variable_star_oracle"
    assert provenance["requested_stars"] == ["Algol", "Mira"]
    assert provenance["returned_stars"] == ["Algol", "Mira"]
    assert provenance["stage_sequence"][0] == "datetime_validation"


def test_variable_star_state_route_rejects_naive_datetime(client_with_engine: TestClient) -> None:
    response = client_with_engine.post(
        "/v1/stars/variable/state",
        json={"dt": "2000-01-01T12:00:00", "star": "Algol"},
    )

    _assert_validation_envelope(response, message_fragment="timezone-aware")


def test_variable_star_state_route_rejects_invalid_threshold(client_with_engine: TestClient) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)

    response = client_with_engine.post(
        "/v1/stars/variable/state",
        json={"dt": dt.isoformat(), "star": "Algol", "eclipse_threshold": 5.5},
    )

    _assert_validation_envelope(response, message_fragment="less than or equal to 5")


def test_variable_star_pair_route_rejects_empty_name(client_with_engine: TestClient) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)

    response = client_with_engine.post(
        "/v1/stars/variable/pair",
        json={"dt": dt.isoformat(), "primary": "Algol", "secondary": ""},
    )

    _assert_validation_envelope(response, message_fragment="String should have at least 1 character")


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
    provenance = body["provenance"]
    assert provenance["catalog_source"][0] == "WDS"
    assert provenance["system_type"] == direct.system_type
    assert provenance["orbit_model"] == "kepler_thiele_innes_visual_binary"
    assert provenance["primary_orbit_label"] == direct.orbits[0].label
    assert provenance["primary_orbit_period_uncertain"] is direct.orbits[0].period_uncertain
    assert provenance["resolvability_doctrine"] == "Dawes limit: 116 / aperture_mm arcseconds"
    assert provenance["stage_sequence"][0] == "multiple_star_catalog_resolution"


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
    provenance = body["provenance"]
    assert provenance["computation_source"] == "multiple_star_oracle"
    assert provenance["catalog_source"][0] == "WDS"
    assert provenance["requested_system"] == "Sirius"
    assert provenance["returned_system"] == "Sirius"
    assert provenance["system_type"] == system.system_type
    assert provenance["orbit_model"] == "kepler_thiele_innes_visual_binary"
    assert provenance["aperture_mm"] == pytest.approx(100.0)
    assert provenance["dawes_limit_arcsec"] == pytest.approx(116.0 / 100.0)
    assert provenance["jd"] == pytest.approx(jd)
    assert provenance["stage_sequence"][0] == "datetime_validation"


def test_multiple_star_list_route_preserves_bounded_catalog_provenance(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.get("/v1/stars/multiple/list?system_type=visual&limit=2")

    assert response.status_code == 200
    body = response.json()
    assert body["systems"]
    assert body["total"] <= 2
    provenance = body["provenance"]
    assert provenance["catalog_source"][0] == "WDS"
    assert provenance["requested_system_type"] == "visual"
    assert provenance["limit"] == 2
    assert provenance["returned_count"] == body["total"]
    assert provenance["stage_sequence"][0] == "multiple_star_catalog_filtering"


def test_multiple_star_state_route_rejects_non_positive_aperture(
    client_with_engine: TestClient,
) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)

    response = client_with_engine.post(
        "/v1/stars/multiple/state",
        json={"dt": dt.isoformat(), "system": "Sirius", "aperture_mm": 0.0},
    )

    assert response.status_code == 422
    assert "greater than 0" in response.json()["message"]


def test_multiple_star_state_route_rejects_naive_datetime(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/stars/multiple/state",
        json={"dt": "2000-01-01T12:00:00", "system": "Sirius", "aperture_mm": 100.0},
    )

    _assert_validation_envelope(response, message_fragment="timezone-aware")


def test_multiple_star_state_route_rejects_empty_system(
    client_with_engine: TestClient,
) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)

    response = client_with_engine.post(
        "/v1/stars/multiple/state",
        json={"dt": dt.isoformat(), "system": " ", "aperture_mm": 100.0},
    )

    _assert_validation_envelope(response, message_fragment="system must be non-empty")


def test_multiple_star_state_route_rejects_oversized_aperture(
    client_with_engine: TestClient,
) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)

    response = client_with_engine.post(
        "/v1/stars/multiple/state",
        json={"dt": dt.isoformat(), "system": "Sirius", "aperture_mm": 10001.0},
    )

    _assert_validation_envelope(response, message_fragment="less than or equal to 10000")


def test_multiple_star_list_route_rejects_invalid_limit(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.get("/v1/stars/multiple/list?limit=0")

    _assert_validation_envelope(response, message_fragment="greater than or equal to 1")
