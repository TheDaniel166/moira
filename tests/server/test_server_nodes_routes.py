from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import ANY

from fastapi.testclient import TestClient
import pytest

from moira.planetary_nodes import OrbitalNode
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


def test_node_catalog_route_declares_distinct_methods(client: TestClient) -> None:
    response = client.get("/v1/nodes/catalog")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 9
    assert body["bodies"][0] == {
        "name": "Mercury",
        "methods": ["mean_elements", "geometric_osculating"],
        "mean_requires_kernel": False,
        "geometric_requires_kernel": True,
        "notes": [
            "mean_elements is kernel-free",
            "geometric_osculating uses the strict Sun-centered orbital core",
            "true-date geometric nodes require JD(TT) 2415020.0 through 2488070.0",
        ],
    }
    assert body["bodies"][-1]["name"] == "loaded_spk_body"
    assert body["bodies"][-1]["mean_requires_kernel"] is None
    assert body["bodies"][-1]["geometric_requires_kernel"] is True
    assert body["provenance"]["stage_sequence"] == [
        "strict_orbital_core_policy_declaration",
        "node_method_catalog_serialization",
    ]
    assert body["provenance"]["geometric_source"] == (
        "moira.orbits strict Sun-centered true-date osculating core, "
        "adapted by moira.planetary_nodes"
    )


def test_mean_planetary_node_route_returns_node_and_provenance(client: TestClient) -> None:
    response = client.post(
        "/v1/nodes/planetary/mean",
        json={"planet": " mars ", "jd": 2451545.0},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["node"]["body"] == "Mars"
    assert 0.0 <= body["node"]["ascending_node"] < 360.0
    assert body["node"]["descending_node"] == pytest.approx(
        (body["node"]["ascending_node"] + 180.0) % 360.0
    )
    assert body["provenance"]["method"] == "mean_elements"
    assert body["provenance"]["requested_body"] == "mars"
    assert body["provenance"]["returned_body"] == "Mars"
    assert body["provenance"]["kernel_required"] is False
    assert body["provenance"]["stage_sequence"] == [
        "jd_validation",
        "mean_planet_identity_resolution",
        "mean_element_polynomial_evaluation",
        "orbital_node_response_serialization",
    ]


def test_mean_planetary_node_route_rejects_invalid_inputs(client: TestClient) -> None:
    empty_planet = client.post(
        "/v1/nodes/planetary/mean",
        json={"planet": " ", "jd": 2451545.0},
    )
    non_finite_jd = client.post(
        "/v1/nodes/planetary/mean",
        json={"planet": "Mars", "jd": "NaN"},
    )
    unknown_planet = client.post(
        "/v1/nodes/planetary/mean",
        json={"planet": "Pluto", "jd": 2451545.0},
    )

    assert empty_planet.status_code == 422
    assert non_finite_jd.status_code == 422
    assert unknown_planet.status_code == 422
    assert "Unknown planet" in unknown_planet.json()["message"]


def test_mean_planetary_nodes_bulk_route_defaults_to_all_mean_planets(
    client: TestClient,
) -> None:
    response = client.post(
        "/v1/nodes/planetary/mean/bulk",
        json={"jd": 2451545.0},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 8
    assert list(body["nodes"]) == [
        "Mercury",
        "Venus",
        "Earth",
        "Mars",
        "Jupiter",
        "Saturn",
        "Uranus",
        "Neptune",
    ]
    assert body["provenance"]["method"] == "mean_elements"
    assert body["provenance"]["kernel_required"] is False


def test_mean_planetary_nodes_bulk_route_rejects_empty_and_oversized_lists(
    client: TestClient,
) -> None:
    empty_entry = client.post(
        "/v1/nodes/planetary/mean/bulk",
        json={"jd": 2451545.0, "planets": ["Mars", " "]},
    )
    oversized = client.post(
        "/v1/nodes/planetary/mean/bulk",
        json={
            "jd": 2451545.0,
            "planets": [
                "Mercury",
                "Venus",
                "Earth",
                "Mars",
                "Jupiter",
                "Saturn",
                "Uranus",
                "Neptune",
                "Pluto",
            ],
        },
    )

    assert empty_entry.status_code == 422
    assert oversized.status_code == 422


def test_geometric_node_route_uses_engine_reader_and_declares_osculating_truth(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, float, object | None]] = []

    def fake_geometric_node_computation(
        body: str,
        jd_ut: float,
        reader: object | None = None,
    ) -> SimpleNamespace:
        calls.append((body, jd_ut, reader))
        node = OrbitalNode(
            planet="Ceres",
            ascending_node=80.0,
            perihelion=120.0,
            aphelion=300.0,
            inclination=10.5,
            eccentricity=0.08,
            semi_major_axis=2.77,
        )
        conversion = SimpleNamespace(
            delta_t_policy="MOIRA_SOURCE_OWNED_DELTA_T_V1",
            delta_t_source_product="iers_eop_direct",
            delta_t_retarget_mode="basis_neutral",
            delta_t_correction_seconds=0.0,
            identity_iterations=2,
            tt_tdb_policy="NAIF_LSK_DELTET",
            tt_tdb_version="naif0012",
            tt_tdb_source_url="https://naif.jpl.nasa.gov/example",
            tt_tdb_source_sha256="a" * 64,
            tt_tdb_source_bytes=5257,
            tt_tdb_iterations=3,
        )
        gravity = SimpleNamespace(
            rule="SUN_MASSLESS_SMALL_BODY",
            gm_km3_s2=132712440041.27942,
            component_naif_ids=(10,),
            component_gm_km3_s2=(132712440041.27942,),
            policy="HORIZONS_GM_2026_09_15",
            source_url="https://ssd.jpl.nasa.gov/example",
            retrieved_date="2026-09-15",
            source_sha256="b" * 64,
            source_bytes=15428,
            planetary_ephemeris="DE441",
        )
        frame = SimpleNamespace(
            frame=SimpleNamespace(value="TRUE_ECLIPTIC_OF_DATE"),
            routine="OBL06_NUT06A_PNM06A_RX",
            router_branch="modern_true",
            precession_model="IAU_2006_PMAT06",
            obliquity_model="IAU_2006_OBL06",
            nutation_model="IAU_2006_2000A_NUT06A",
        )
        source = SimpleNamespace(
            legs=(
                SimpleNamespace(
                    center_naif_id=10,
                    target_naif_id=2000001,
                    traversal_sign=1,
                    segment_type=13,
                    coverage_start_tdb=2451545.0,
                    coverage_end_tdb=2462502.5,
                    kernel_label="SB441_CERES",
                    kernel_sha256="c" * 64,
                    kernel_bytes=4096,
                    pool_index=1,
                    catalog_id="moira-asteroids-wheel",
                    catalog_version="2026.08.14.1",
                    manifest_sha256="d" * 64,
                    released_utc="2026-08-14T21:53:17Z",
                    planetary_ephemeris=None,
                    coverage_restricted_to_observed_arc=True,
                ),
            ),
            covered_intervals_tdb=((2451545.0, 2462502.5),),
            pool_generation=2,
        )
        elements = SimpleNamespace(
            body=SimpleNamespace(
                name="Ceres",
                naif_id=2000001,
                kind=SimpleNamespace(value="ASTEROID"),
            ),
            center=SimpleNamespace(value="SUN"),
            frame=SimpleNamespace(value="TRUE_ECLIPTIC_OF_DATE"),
            jd_ut=jd_ut,
            epoch_tt=2460110.5008,
            epoch_tdb=2460110.5008,
            delta_t_seconds=69.0,
            tdb_minus_tt_seconds=0.001,
            provenance=SimpleNamespace(
                time_conversion=conversion,
                gravity=gravity,
                frame_construction=frame,
                frame_model_interval_tt=(2415020.0, 2488070.0),
                state_source=source,
                singularity_thresholds=SimpleNamespace(
                    policy="MOIRA_OSCULATING_ELEMENTS_STAGE1_V1"
                ),
            ),
        )
        return SimpleNamespace(node=node, elements=elements)

    monkeypatch.setattr(
        "moira_server.services.nodes._geometric_node_computation",
        fake_geometric_node_computation,
    )

    response = client.post(
        "/v1/nodes/geometric",
        json={"body": " Ceres ", "jd_ut": 2460110.5},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["node"] == {
        "body": "Ceres",
        "ascending_node": 80.0,
        "descending_node": 260.0,
        "perihelion": 120.0,
        "aphelion": 300.0,
        "inclination": 10.5,
        "eccentricity": 0.08,
        "semi_major_axis": 2.77,
    }
    assert body["provenance"]["method"] == "geometric_osculating"
    assert body["provenance"]["jd_scale"] == "UT1_JD"
    assert body["provenance"]["center"] == "SUN"
    assert body["provenance"]["frame"] == "TRUE_ECLIPTIC_OF_DATE"
    assert body["provenance"]["body_naif_id"] == 2000001
    assert body["provenance"]["body_kind"] == "ASTEROID"
    assert body["provenance"]["kernel_required"] is True
    assert body["provenance"]["kernel_source"] == "loaded_engine_reader"
    assert body["provenance"]["coordinate_basis"] == (
        "strict_orbital_core_angular_momentum_and_eccentricity_vector"
    )
    assert body["provenance"]["time"]["input_time_scale"] == "UT1_JD"
    assert body["provenance"]["time"]["state_evaluation_scale"] == "TDB_JD"
    assert body["provenance"]["gravity"]["rule"] == "SUN_MASSLESS_SMALL_BODY"
    assert body["provenance"]["frame_construction"]["routine"] == (
        "OBL06_NUT06A_PNM06A_RX"
    )
    assert body["provenance"]["state_source"]["legs"][0]["kernel_sha256"] == (
        "c" * 64
    )
    assert body["provenance"]["singularity_policy"] == (
        "MOIRA_OSCULATING_ELEMENTS_STAGE1_V1"
    )
    assert calls == [("Ceres", 2460110.5, ANY)]
    assert calls[0][2] is not None


def test_geometric_node_route_rejects_invalid_inputs(client: TestClient) -> None:
    empty_body = client.post(
        "/v1/nodes/geometric",
        json={"body": " ", "jd_ut": 2460110.5},
    )
    non_finite_jd = client.post(
        "/v1/nodes/geometric",
        json={"body": "Ceres", "jd_ut": "Infinity"},
    )
    boolean_jd = client.post(
        "/v1/nodes/geometric",
        json={"body": "Ceres", "jd_ut": True},
    )
    sun = client.post(
        "/v1/nodes/geometric",
        json={"body": "Sun", "jd_ut": 2460110.5},
    )

    assert empty_body.status_code == 422
    assert non_finite_jd.status_code == 422
    assert boolean_jd.status_code == 422
    assert sun.status_code == 422
    assert sun.json()["error_code"] == "body_not_supported"
    assert sun.json()["details"] == {
        "body": "Sun",
        "kind": "non-orbital point",
        "reason": "Body.SUN is a center or calculated point, not an orbital target",
    }
