from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient
import pytest

from moira.asteroids import ASTEROID_NAIF, AsteroidData
from moira.comets import COMET_NAIF, CometData
from moira.julian import jd_from_datetime, utc_to_ut1
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.network


class _FakeReader:
    def __init__(self, covered_ids: set[int]):
        self._covered_ids = frozenset(covered_ids)

    def covered_bodies(self) -> frozenset[int]:
        return self._covered_ids


class _FakeEngine:
    def __init__(self, covered_ids: set[int]):
        self._reader = _FakeReader(covered_ids)


@pytest.fixture
def client_with_small_body_reader(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    covered_ids = {
        ASTEROID_NAIF["Ceres"],
        ASTEROID_NAIF["Vesta"],
        COMET_NAIF["Halley"],
        COMET_NAIF["Encke"],
    }
    monkeypatch.setattr(
        "moira_server.app.create_engine",
        lambda config: _FakeEngine(covered_ids),
    )
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        yield client


def test_asteroid_list_route_returns_structured_records_for_loaded_bodies(
    client_with_small_body_reader: TestClient,
) -> None:
    response = client_with_small_body_reader.get("/v1/asteroids/list")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["bodies"] == [
        {"name": "Ceres", "naif_id": ASTEROID_NAIF["Ceres"]},
        {"name": "Vesta", "naif_id": ASTEROID_NAIF["Vesta"]},
    ]
    assert body["provenance"] == {
        "catalog_source": "ASTEROID_NAIF",
        "catalog_scope": "known_asteroid_identity_mapping",
        "availability_source": "loaded_reader_covered_bodies",
        "loaded_kernel_available": True,
        "requested_query": None,
        "limit": 500,
        "returned_count": 2,
        "stage_sequence": [
            "reader_coverage_intersection",
            "loaded_kernel_list_serialization",
        ],
    }


def test_asteroid_list_route_filters_by_name_or_naif_id(
    client_with_small_body_reader: TestClient,
) -> None:
    by_name = client_with_small_body_reader.get("/v1/asteroids/list?q=ceres")
    by_naif = client_with_small_body_reader.get(f"/v1/asteroids/list?q={ASTEROID_NAIF['Vesta']}")

    assert by_name.status_code == 200
    by_name_body = by_name.json()
    assert by_name_body["bodies"] == [
        {"name": "Ceres", "naif_id": ASTEROID_NAIF["Ceres"]}
    ]
    assert by_name_body["total"] == 1
    assert by_name_body["provenance"]["requested_query"] == "ceres"
    assert by_naif.status_code == 200
    by_naif_body = by_naif.json()
    assert by_naif_body["bodies"] == [
        {"name": "Vesta", "naif_id": ASTEROID_NAIF["Vesta"]}
    ]
    assert by_naif_body["total"] == 1
    assert by_naif_body["provenance"]["requested_query"] == str(ASTEROID_NAIF["Vesta"])


def test_asteroid_list_route_honors_limit(
    client_with_small_body_reader: TestClient,
) -> None:
    response = client_with_small_body_reader.get("/v1/asteroids/list?limit=1")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["provenance"]["limit"] == 1
    assert body["provenance"]["returned_count"] == 1


def test_asteroid_list_route_rejects_invalid_limit(
    client_with_small_body_reader: TestClient,
) -> None:
    response = client_with_small_body_reader.get("/v1/asteroids/list?limit=501")

    assert response.status_code == 422


def test_asteroid_position_route_returns_position_with_provenance(
    client_with_small_body_reader: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dt = "2026-06-13T12:00:00+00:00"
    expected_jd = utc_to_ut1(
        jd_from_datetime(datetime(2026, 6, 13, 12, tzinfo=timezone.utc))
    )
    calls: list[tuple[str | int, float, object]] = []

    def fake_asteroid_at(body: str | int, jd_ut: float, *, reader: object | None = None) -> AsteroidData:
        calls.append((body, jd_ut, reader))
        return AsteroidData(
            name="Ceres",
            naif_id=ASTEROID_NAIF["Ceres"],
            longitude=15.25,
            latitude=1.5,
            distance=315_000_000.0,
            speed=0.22,
            retrograde=False,
        )

    monkeypatch.setattr("moira_server.services.asteroids.asteroid_at", fake_asteroid_at)

    response = client_with_small_body_reader.post(
        "/v1/asteroids/position",
        json={"dt": dt, "body": " Ceres "},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Ceres"
    assert body["naif_id"] == ASTEROID_NAIF["Ceres"]
    assert body["is_sovereign"] is True
    assert body["provenance"]["requested_body"] == "Ceres"
    assert body["provenance"]["returned_naif_id"] == ASTEROID_NAIF["Ceres"]
    assert body["provenance"]["known_catalog_entry"] is True
    assert body["provenance"]["loaded_kernel_available"] is True
    assert body["provenance"]["kernel_source"] == "loaded_small_body_reader"
    assert body["provenance"]["jd_ut"] == expected_jd
    assert body["provenance"]["stage_sequence"] == [
        "datetime_validation",
        "julian_day_conversion",
        "asteroid_identity_resolution",
        "small_body_kernel_evaluation",
        "asteroid_response_serialization",
    ]
    assert calls[0][0] == "Ceres"
    assert calls[0][1] == expected_jd
    assert calls[0][2] is not None


def test_asteroid_position_route_does_not_overclaim_unloaded_kernel_body(
    client_with_small_body_reader: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_asteroid_at(body: str | int, jd_ut: float, *, reader: object | None = None) -> AsteroidData:
        return AsteroidData(
            name="Pallas",
            naif_id=ASTEROID_NAIF["Pallas"],
            longitude=88.0,
            latitude=-2.0,
            distance=420_000_000.0,
            speed=-0.1,
            retrograde=True,
        )

    monkeypatch.setattr("moira_server.services.asteroids.asteroid_at", fake_asteroid_at)

    response = client_with_small_body_reader.post(
        "/v1/asteroids/position",
        json={"dt": "2026-06-13T12:00:00+00:00", "body": "Pallas"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["is_sovereign"] is False
    assert body["provenance"]["known_catalog_entry"] is True
    assert body["provenance"]["loaded_kernel_available"] is False


def test_asteroid_position_route_marks_numeric_string_naif_as_known_catalog_entry(
    client_with_small_body_reader: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_asteroid_at(body: str | int, jd_ut: float, *, reader: object | None = None) -> AsteroidData:
        return AsteroidData(
            name="Ceres",
            naif_id=ASTEROID_NAIF["Ceres"],
            longitude=15.25,
            latitude=1.5,
            distance=315_000_000.0,
            speed=0.22,
            retrograde=False,
        )

    monkeypatch.setattr("moira_server.services.asteroids.asteroid_at", fake_asteroid_at)

    response = client_with_small_body_reader.post(
        "/v1/asteroids/position",
        json={
            "dt": "2026-06-13T12:00:00+00:00",
            "body": str(ASTEROID_NAIF["Ceres"]),
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["provenance"]["requested_body"] == str(ASTEROID_NAIF["Ceres"])
    assert body["provenance"]["known_catalog_entry"] is True


def test_asteroid_position_route_rejects_naive_datetime(
    client_with_small_body_reader: TestClient,
) -> None:
    response = client_with_small_body_reader.post(
        "/v1/asteroids/position",
        json={"dt": "2026-06-13T12:00:00", "body": "Ceres"},
    )

    assert response.status_code == 422


def test_asteroid_position_route_rejects_empty_body(
    client_with_small_body_reader: TestClient,
) -> None:
    response = client_with_small_body_reader.post(
        "/v1/asteroids/position",
        json={"dt": "2026-06-13T12:00:00+00:00", "body": "   "},
    )

    assert response.status_code == 422


def test_asteroids_bulk_route_returns_results_missing_and_provenance(
    client_with_small_body_reader: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_asteroid_at(body: str | int, jd_ut: float, *, reader: object | None = None) -> AsteroidData:
        if str(body) == "Missing":
            raise KeyError(body)
        naif_id = ASTEROID_NAIF[str(body)]
        return AsteroidData(
            name=str(body),
            naif_id=naif_id,
            longitude=20.0,
            latitude=0.25,
            distance=300_000_000.0,
            speed=0.15,
            retrograde=False,
        )

    monkeypatch.setattr("moira_server.services.asteroids.asteroid_at", fake_asteroid_at)

    response = client_with_small_body_reader.post(
        "/v1/asteroids/bulk",
        json={
            "dt": "2026-06-13T12:00:00+00:00",
            "bodies": ["Ceres", "Pallas", "Missing"],
            "skip_missing": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert sorted(body["results"]) == ["Ceres", "Pallas"]
    assert body["results"]["Ceres"]["is_sovereign"] is True
    assert body["results"]["Pallas"]["is_sovereign"] is False
    assert body["missing"] == ["Missing"]
    assert body["sovereign_used"] is True
    assert body["provenance"]["requested_bodies"] == ["Ceres", "Pallas", "Missing"]
    assert body["provenance"]["returned_bodies"] == ["Ceres", "Pallas"]
    assert body["provenance"]["missing_bodies"] == ["Missing"]
    assert body["provenance"]["loaded_kernel_available"] is True


def test_asteroids_bulk_route_rejects_invalid_bodies(
    client_with_small_body_reader: TestClient,
) -> None:
    empty_list = client_with_small_body_reader.post(
        "/v1/asteroids/bulk",
        json={"dt": "2026-06-13T12:00:00+00:00", "bodies": []},
    )
    empty_entry = client_with_small_body_reader.post(
        "/v1/asteroids/bulk",
        json={"dt": "2026-06-13T12:00:00+00:00", "bodies": ["Ceres", " "]},
    )
    oversized = client_with_small_body_reader.post(
        "/v1/asteroids/bulk",
        json={
            "dt": "2026-06-13T12:00:00+00:00",
            "bodies": ["Ceres"] * 501,
        },
    )

    assert empty_list.status_code == 422
    assert empty_entry.status_code == 422
    assert oversized.status_code == 422


def test_asteroid_subsets_route_lists_admitted_subset_registries(
    client_with_small_body_reader: TestClient,
) -> None:
    response = client_with_small_body_reader.get("/v1/asteroids/subsets")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 4
    assert [item["subset"] for item in body["subsets"]] == [
        "classical",
        "main_belt",
        "centaurs",
        "tnos",
    ]
    assert body["stage_sequence"] == ["subset_registry_serialization"]


def test_asteroid_subset_list_route_returns_membership_and_kernel_availability(
    client_with_small_body_reader: TestClient,
) -> None:
    response = client_with_small_body_reader.get("/v1/asteroids/subsets/classical/list")

    assert response.status_code == 200
    body = response.json()
    assert body["subset"] == "classical"
    assert body["total"] == 4
    by_name = {item["name"]: item for item in body["bodies"]}
    assert by_name["Ceres"]["loaded_kernel_available"] is True
    assert by_name["Vesta"]["loaded_kernel_available"] is True
    assert by_name["Pallas"]["loaded_kernel_available"] is False
    assert by_name["Juno"]["loaded_kernel_available"] is False
    assert body["provenance"]["catalog_source"] == "CLASSICAL_NAMES"
    assert body["provenance"]["subset_source_module"] == "moira.classical_asteroids"


def test_asteroid_subset_list_route_rejects_unknown_subset_and_invalid_limit(
    client_with_small_body_reader: TestClient,
) -> None:
    unknown = client_with_small_body_reader.get("/v1/asteroids/subsets/unknown/list")
    invalid_limit = client_with_small_body_reader.get(
        "/v1/asteroids/subsets/classical/list?limit=501"
    )

    assert unknown.status_code == 422
    assert invalid_limit.status_code == 422


def test_asteroid_subset_positions_route_returns_bounded_subset_positions(
    client_with_small_body_reader: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_asteroid_at(body: str | int, jd_ut: float, *, reader: object | None = None) -> AsteroidData:
        name = str(body)
        return AsteroidData(
            name=name,
            naif_id=ASTEROID_NAIF[name],
            longitude=30.0,
            latitude=1.0,
            distance=300_000_000.0,
            speed=0.12,
            retrograde=False,
        )

    monkeypatch.setattr("moira_server.services.asteroids.asteroid_at", fake_asteroid_at)

    response = client_with_small_body_reader.post(
        "/v1/asteroids/subsets/classical/positions",
        json={"dt": "2026-06-13T12:00:00+00:00"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["subset"] == "classical"
    assert sorted(body["results"]) == ["Ceres", "Juno", "Pallas", "Vesta"]
    assert body["results"]["Ceres"]["is_sovereign"] is True
    assert body["results"]["Vesta"]["is_sovereign"] is True
    assert body["results"]["Pallas"]["is_sovereign"] is False
    assert body["missing"] == []
    assert body["provenance"]["resolved_subset_bodies"] == [
        "Ceres",
        "Pallas",
        "Juno",
        "Vesta",
    ]
    assert body["provenance"]["stage_sequence"] == [
        "subset_catalog_selection",
        "datetime_validation",
        "julian_day_conversion",
        "asteroid_bulk_position_transport",
        "subset_position_response_serialization",
    ]


def test_asteroid_subset_positions_route_reports_out_of_subset_bodies_as_missing(
    client_with_small_body_reader: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_asteroid_at(body: str | int, jd_ut: float, *, reader: object | None = None) -> AsteroidData:
        return AsteroidData(
            name=str(body),
            naif_id=ASTEROID_NAIF[str(body)],
            longitude=30.0,
            latitude=1.0,
            distance=300_000_000.0,
            speed=0.12,
            retrograde=False,
        )

    monkeypatch.setattr("moira_server.services.asteroids.asteroid_at", fake_asteroid_at)

    response = client_with_small_body_reader.post(
        "/v1/asteroids/subsets/classical/positions",
        json={
            "dt": "2026-06-13T12:00:00+00:00",
            "bodies": ["Ceres", "Ixion"],
            "skip_missing": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert sorted(body["results"]) == ["Ceres"]
    assert body["missing"] == ["Ixion"]
    assert body["provenance"]["resolved_subset_bodies"] == ["Ceres"]


def test_asteroid_subset_positions_route_rejects_naive_datetime_and_empty_bodies(
    client_with_small_body_reader: TestClient,
) -> None:
    naive_dt = client_with_small_body_reader.post(
        "/v1/asteroids/subsets/classical/positions",
        json={"dt": "2026-06-13T12:00:00"},
    )
    empty_body = client_with_small_body_reader.post(
        "/v1/asteroids/subsets/classical/positions",
        json={"dt": "2026-06-13T12:00:00+00:00", "bodies": [" "]},
    )

    assert naive_dt.status_code == 422
    assert empty_body.status_code == 422


def test_asteroid_family_by_number_route_returns_catalog_provenance(
    client_with_small_body_reader: TestClient,
) -> None:
    response = client_with_small_body_reader.get("/v1/asteroids/families/by-number/4")

    assert response.status_code == 200
    body = response.json()
    assert body["number"] == 4
    assert body["family_name"] == "Vesta"
    assert body["family_names"] == ["Vesta"]
    assert body["provenance"]["catalog_source"] == (
        "Proper25_2026_plus_NASA_PDS_2015_excluded_populations"
    )
    assert body["provenance"]["number_system"] == "MPC_catalog_number"


def test_asteroid_family_members_route_is_bounded(
    client_with_small_body_reader: TestClient,
) -> None:
    response = client_with_small_body_reader.get(
        "/v1/asteroids/families/Vesta/members?limit=2"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["family_name"] == "Vesta"
    assert len(body["members"]) == 2
    assert body["total_available"] >= 2
    assert body["returned_count"] == 2
    assert body["provenance"]["limit"] == 2


def test_asteroid_family_routes_reject_invalid_bounds(
    client_with_small_body_reader: TestClient,
) -> None:
    invalid_number = client_with_small_body_reader.get("/v1/asteroids/families/by-number/0")
    invalid_limit = client_with_small_body_reader.get(
        "/v1/asteroids/families/Vesta/members?limit=501"
    )

    assert invalid_number.status_code == 422
    assert invalid_limit.status_code == 422


def test_asteroid_families_in_chart_route_groups_mpc_numbers(
    client_with_small_body_reader: TestClient,
) -> None:
    response = client_with_small_body_reader.post(
        "/v1/asteroids/families/chart",
        json={"numbers": [1, 4, 158, 167, 243, 832]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["groups"]["Karin"] == [158, 167, 832]
    assert body["groups"]["Koronis"] == [158, 167, 243, 832]
    assert body["groups"]["Koronis2"] == [158, 167, 832]
    assert body["groups"]["Vesta"] == [4]
    assert body["ungrouped_numbers"] == [1]
    assert body["provenance"]["number_system"] == "MPC_catalog_number"
    assert body["provenance"]["grouped_count"] == 5


def test_asteroid_families_in_chart_route_rejects_invalid_numbers(
    client_with_small_body_reader: TestClient,
) -> None:
    empty = client_with_small_body_reader.post(
        "/v1/asteroids/families/chart",
        json={"numbers": []},
    )
    non_positive = client_with_small_body_reader.post(
        "/v1/asteroids/families/chart",
        json={"numbers": [4, 0]},
    )
    oversized = client_with_small_body_reader.post(
        "/v1/asteroids/families/chart",
        json={"numbers": [4] * 501},
    )

    assert empty.status_code == 422
    assert non_positive.status_code == 422
    assert oversized.status_code == 422


def test_asteroid_family_resonance_network_route_returns_ui_ready_edges(
    client_with_small_body_reader: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_jd = utc_to_ut1(
        jd_from_datetime(datetime(2026, 6, 13, 12, tzinfo=timezone.utc))
    )
    calls: list[tuple[str | int, float, object]] = []

    def fake_asteroid_at(body: str | int, jd_ut: float, *, reader: object | None = None) -> AsteroidData:
        calls.append((body, jd_ut, reader))
        if body == ASTEROID_NAIF["Vesta"]:
            return AsteroidData(
                name="Vesta",
                naif_id=ASTEROID_NAIF["Vesta"],
                longitude=10.0,
                latitude=0.1,
                distance=250_000_000.0,
                speed=0.11,
                retrograde=False,
            )
        if body == ASTEROID_NAIF["Ausonia"]:
            return AsteroidData(
                name="Ausonia",
                naif_id=ASTEROID_NAIF["Ausonia"],
                longitude=10.5,
                latitude=-0.2,
                distance=275_000_000.0,
                speed=0.08,
                retrograde=False,
            )
        raise KeyError(body)

    monkeypatch.setattr("moira_server.services.asteroids.asteroid_at", fake_asteroid_at)

    response = client_with_small_body_reader.post(
        "/v1/asteroids/families/chart/resonance-network",
        json={
            "dt": "2026-06-13T12:00:00+00:00",
            "numbers": [4, 63],
            "aspect_tier": 0,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["families"] == ["Vesta"]
    assert body["total_aspects"] == 1
    assert body["resonant_aspect_count"] == 1
    assert body["sovereign_used"] is True
    nodes_by_name = {node["body"]: node for node in body["nodes"]}
    assert nodes_by_name["Vesta"]["mpc_number"] == 4
    assert nodes_by_name["Vesta"]["family_name"] == "Vesta"
    assert nodes_by_name["Vesta"]["family_names"] == ["Vesta"]
    assert nodes_by_name["Vesta"]["is_sovereign"] is True
    assert nodes_by_name["Ausonia"]["mpc_number"] == 63
    assert nodes_by_name["Ausonia"]["family_name"] == "Vesta"
    assert nodes_by_name["Ausonia"]["is_sovereign"] is False

    edge = body["edges"][0]
    assert edge["source"] == "Vesta"
    assert edge["target"] == "Ausonia"
    assert edge["family_name"] == "Vesta"
    assert edge["body1_number"] == 4
    assert edge["body2_number"] == 63
    assert edge["aspect"]["aspect"] == "Conjunction"
    assert edge["aspect"]["orb"] == pytest.approx(0.5)
    assert edge["aspect"]["classification"]["family"] == "conjunction"
    assert body["network"]["Vesta"] == [edge]
    assert body["provenance"]["identity_source"] == "mpc_catalog_number"
    assert body["provenance"]["requested_bodies"] == ["4", "63"]
    assert body["provenance"]["resolved_bodies"] == ["Vesta", "Ausonia"]
    assert body["provenance"]["jd_ut"] == expected_jd
    assert body["provenance"]["stage_sequence"] == [
        "datetime_validation",
        "julian_day_conversion",
        "asteroid_position_transport",
        "mpc_number_derivation",
        "aspect_detection",
        "family_resonance_filter",
        "resonance_network_serialization",
    ]
    assert [call[0] for call in calls] == [ASTEROID_NAIF["Vesta"], ASTEROID_NAIF["Ausonia"]]
    assert all(call[1] == expected_jd for call in calls)
    assert all(call[2] is not None for call in calls)


def test_asteroid_family_resonance_network_route_rejects_invalid_requests(
    client_with_small_body_reader: TestClient,
) -> None:
    dt = "2026-06-13T12:00:00+00:00"
    too_few_numbers = client_with_small_body_reader.post(
        "/v1/asteroids/families/chart/resonance-network",
        json={"dt": dt, "numbers": [4]},
    )
    ambiguous_identity = client_with_small_body_reader.post(
        "/v1/asteroids/families/chart/resonance-network",
        json={"dt": dt, "bodies": ["Vesta", "Ausonia"], "numbers": [4, 63]},
    )
    mpc_number_in_body_field = client_with_small_body_reader.post(
        "/v1/asteroids/families/chart/resonance-network",
        json={"dt": dt, "bodies": [4, ASTEROID_NAIF["Ausonia"]]},
    )
    invalid_tier = client_with_small_body_reader.post(
        "/v1/asteroids/families/chart/resonance-network",
        json={"dt": dt, "numbers": [4, 63], "aspect_tier": 3},
    )

    assert too_few_numbers.status_code == 422
    assert ambiguous_identity.status_code == 422
    assert mpc_number_in_body_field.status_code == 422
    assert invalid_tier.status_code == 422


def test_comet_list_route_returns_structured_records_and_filters(
    client_with_small_body_reader: TestClient,
) -> None:
    response = client_with_small_body_reader.get("/v1/comets/list?q=halley")

    assert response.status_code == 200
    body = response.json()
    assert body["bodies"] == [{"name": "1P/Halley", "naif_id": COMET_NAIF["Halley"]}]
    assert body["total"] == 1
    assert body["provenance"] == {
        "catalog_source": "COMET_NAIF",
        "catalog_scope": "numbered_periodic_comet_identity_mapping",
        "availability_source": "loaded_reader_covered_bodies",
        "loaded_kernel_available": True,
        "requested_query": "halley",
        "limit": 500,
        "returned_count": 1,
        "stage_sequence": [
            "reader_coverage_intersection",
            "loaded_kernel_list_serialization",
        ],
    }


def test_comet_list_route_honors_limit(
    client_with_small_body_reader: TestClient,
) -> None:
    response = client_with_small_body_reader.get("/v1/comets/list?limit=1")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["provenance"]["limit"] == 1
    assert body["provenance"]["returned_count"] == 1


def test_comet_list_route_rejects_invalid_limit(
    client_with_small_body_reader: TestClient,
) -> None:
    response = client_with_small_body_reader.get("/v1/comets/list?limit=501")

    assert response.status_code == 422


def test_comet_position_route_returns_position_with_provenance(
    client_with_small_body_reader: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dt = "2026-06-13T12:00:00+00:00"
    expected_jd = utc_to_ut1(
        jd_from_datetime(datetime(2026, 6, 13, 12, tzinfo=timezone.utc))
    )
    calls: list[tuple[str, float, object]] = []

    def fake_comet_at(body: str, jd_ut: float, *, reader: object | None = None) -> CometData:
        calls.append((body, jd_ut, reader))
        return CometData(
            name="Halley",
            naif_id=COMET_NAIF["Halley"],
            longitude=215.5,
            latitude=-12.25,
            distance=4.25,
            speed=0.08,
            retrograde=False,
            sign="Scorpio",
            sign_symbol="Sc",
        )

    monkeypatch.setattr("moira_server.services.comets.comet_at", fake_comet_at)

    response = client_with_small_body_reader.post(
        "/v1/comets/position",
        json={"dt": dt, "body": " Halley "},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Halley"
    assert body["naif_id"] == COMET_NAIF["Halley"]
    assert body["is_sovereign"] is True
    assert body["provenance"]["requested_body"] == "Halley"
    assert body["provenance"]["resolved_body"] == "Halley"
    assert body["provenance"]["returned_naif_id"] == COMET_NAIF["Halley"]
    assert body["provenance"]["known_catalog_entry"] is True
    assert body["provenance"]["loaded_kernel_available"] is True
    assert body["provenance"]["kernel_source"] == "loaded_small_body_reader"
    assert body["provenance"]["jd_ut"] == expected_jd
    assert body["provenance"]["naif_convention"] == "periodic_comet_naif_id_1000000_plus_number"
    assert body["provenance"]["stage_sequence"] == [
        "datetime_validation",
        "julian_day_conversion",
        "comet_identity_resolution",
        "small_body_kernel_evaluation",
        "comet_response_serialization",
    ]
    assert calls[0] == ("Halley", expected_jd, calls[0][2])
    assert calls[0][2] is not None


def test_comet_position_route_resolves_numeric_string_naif_id(
    client_with_small_body_reader: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fake_comet_at(body: str, jd_ut: float, *, reader: object | None = None) -> CometData:
        calls.append(body)
        return CometData(
            name="Halley",
            naif_id=COMET_NAIF["Halley"],
            longitude=215.5,
            latitude=-12.25,
            distance=4.25,
            speed=0.08,
            retrograde=False,
            sign="Scorpio",
            sign_symbol="Sc",
        )

    monkeypatch.setattr("moira_server.services.comets.comet_at", fake_comet_at)

    response = client_with_small_body_reader.post(
        "/v1/comets/position",
        json={
            "dt": "2026-06-13T12:00:00+00:00",
            "body": str(COMET_NAIF["Halley"]),
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert calls == ["1P/Halley"]
    assert body["provenance"]["requested_body"] == str(COMET_NAIF["Halley"])
    assert body["provenance"]["resolved_body"] == "1P/Halley"
    assert body["provenance"]["known_catalog_entry"] is True


def test_comet_position_route_does_not_overclaim_unloaded_kernel_body(
    client_with_small_body_reader: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_comet_at(body: str, jd_ut: float, *, reader: object | None = None) -> CometData:
        return CometData(
            name="Tempel1",
            naif_id=COMET_NAIF["Tempel1"],
            longitude=40.0,
            latitude=3.0,
            distance=2.5,
            speed=-0.03,
            retrograde=True,
            sign="Taurus",
            sign_symbol="Ta",
        )

    monkeypatch.setattr("moira_server.services.comets.comet_at", fake_comet_at)

    response = client_with_small_body_reader.post(
        "/v1/comets/position",
        json={"dt": "2026-06-13T12:00:00+00:00", "body": "Tempel1"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["is_sovereign"] is False
    assert body["provenance"]["known_catalog_entry"] is True
    assert body["provenance"]["loaded_kernel_available"] is False


def test_comet_position_route_rejects_naive_datetime(
    client_with_small_body_reader: TestClient,
) -> None:
    response = client_with_small_body_reader.post(
        "/v1/comets/position",
        json={"dt": "2026-06-13T12:00:00", "body": "Halley"},
    )

    assert response.status_code == 422


def test_comet_position_route_rejects_empty_body(
    client_with_small_body_reader: TestClient,
) -> None:
    response = client_with_small_body_reader.post(
        "/v1/comets/position",
        json={"dt": "2026-06-13T12:00:00+00:00", "body": "   "},
    )

    assert response.status_code == 422


def test_comets_bulk_route_returns_results_missing_and_provenance(
    client_with_small_body_reader: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_comet_at(body: str, jd_ut: float, *, reader: object | None = None) -> CometData:
        if body == "Swift-Tuttle":
            raise KeyError(body)
        return CometData(
            name=body,
            naif_id=COMET_NAIF[body],
            longitude=200.0,
            latitude=-4.0,
            distance=3.0,
            speed=0.04,
            retrograde=False,
            sign="Libra",
            sign_symbol="Li",
        )

    monkeypatch.setattr("moira_server.services.comets.comet_at", fake_comet_at)

    response = client_with_small_body_reader.post(
        "/v1/comets/bulk",
        json={
            "dt": "2026-06-13T12:00:00+00:00",
            "bodies": ["Halley", "Tempel1", "Swift-Tuttle"],
            "skip_missing": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert sorted(body["results"]) == ["Halley", "Tempel1"]
    assert body["results"]["Halley"]["is_sovereign"] is True
    assert body["results"]["Tempel1"]["is_sovereign"] is False
    assert body["missing"] == ["Swift-Tuttle"]
    assert body["sovereign_used"] is True
    assert body["provenance"]["requested_bodies"] == ["Halley", "Tempel1", "Swift-Tuttle"]
    assert body["provenance"]["returned_bodies"] == ["Halley", "Tempel1"]
    assert body["provenance"]["missing_bodies"] == ["Swift-Tuttle"]
    assert body["provenance"]["loaded_kernel_available"] is True


def test_comets_bulk_route_rejects_invalid_bodies(
    client_with_small_body_reader: TestClient,
) -> None:
    empty_list = client_with_small_body_reader.post(
        "/v1/comets/bulk",
        json={"dt": "2026-06-13T12:00:00+00:00", "bodies": []},
    )
    empty_entry = client_with_small_body_reader.post(
        "/v1/comets/bulk",
        json={"dt": "2026-06-13T12:00:00+00:00", "bodies": ["Halley", " "]},
    )
    oversized = client_with_small_body_reader.post(
        "/v1/comets/bulk",
        json={
            "dt": "2026-06-13T12:00:00+00:00",
            "bodies": ["Halley"] * 501,
        },
    )

    assert empty_list.status_code == 422
    assert empty_entry.status_code == 422
    assert oversized.status_code == 422
