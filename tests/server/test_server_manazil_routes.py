from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from moira.manazil import MANSION_SPAN
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.loopback


@pytest.fixture
def client() -> TestClient:
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as test_client:
        yield test_client


def test_manazil_catalog_route_returns_28_equal_mansions(client: TestClient) -> None:
    response = client.get("/v1/manazil/catalog")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 28
    assert body["span_degrees"] == MANSION_SPAN
    assert body["mansions"][0]["index"] == 1
    assert body["mansions"][0]["latin_name"] == "Alnath"
    assert body["traditions"] == [
        "al_biruni",
        "abenragel",
        "ibn_alarabi",
        "agrippa",
        "picatrix",
    ]
    assert body["provenance"]["mansion_system"] == "Arabic_Manazil_28_equal_mansions"
    assert body["provenance"]["stage_sequence"] == ["mansion_catalog_serialization"]


def test_manazil_position_route_preserves_boundary_truth(client: TestClient) -> None:
    before = client.post(
        "/v1/manazil/position",
        json={"longitude": MANSION_SPAN - 0.001, "tradition": "agrippa"},
    )
    at_boundary = client.post(
        "/v1/manazil/position",
        json={"longitude": MANSION_SPAN, "tradition": "agrippa"},
    )
    wrap = client.post(
        "/v1/manazil/position",
        json={"longitude": 360.0, "tradition": "agrippa"},
    )

    assert before.status_code == 200
    assert at_boundary.status_code == 200
    assert wrap.status_code == 200
    assert before.json()["result"]["mansion"]["index"] == 1
    assert at_boundary.json()["result"]["mansion"]["index"] == 2
    assert wrap.json()["result"]["mansion"]["index"] == 1
    assert at_boundary.json()["provenance"]["stage_sequence"] == [
        "longitude_validation",
        "tropical_longitude_use",
        "equal_28_mansion_assignment",
        "tradition_attribution_selection",
        "mansion_response_serialization",
    ]


def test_manazil_position_route_applies_tradition_attribution(client: TestClient) -> None:
    response = client.post(
        "/v1/manazil/position",
        json={"longitude": 0.0, "tradition": "abenragel"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["result"]["mansion"]["index"] == 1
    assert body["result"]["mansion"]["nature"] == "Fortunate"
    assert body["provenance"]["tradition"] == "abenragel"


def test_manazil_sidereal_position_requires_jd_ut(client: TestClient) -> None:
    missing_jd = client.post(
        "/v1/manazil/position",
        json={"longitude": 30.0, "mode": "sidereal", "tradition": "agrippa"},
    )
    with_jd = client.post(
        "/v1/manazil/position",
        json={"longitude": 30.0, "mode": "sidereal", "jd_ut": 2451545.0, "tradition": "agrippa"},
    )

    assert missing_jd.status_code == 422
    assert missing_jd.json()["message"] == "sidereal mansion computation requires jd_ut"
    assert with_jd.status_code == 200
    assert with_jd.json()["provenance"]["mode"] == "sidereal"
    assert with_jd.json()["provenance"]["ayanamsa_system"] == "Lahiri"


def test_manazil_position_route_rejects_non_finite_longitude(client: TestClient) -> None:
    response = client.post(
        "/v1/manazil/position",
        json={"longitude": "NaN"},
    )

    assert response.status_code == 422


def test_manazil_bulk_route_returns_named_positions(client: TestClient) -> None:
    response = client.post(
        "/v1/manazil/bulk",
        json={
            "positions": {
                "Moon": 0.0,
                "Mars": MANSION_SPAN,
            },
            "tradition": "picatrix",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["results"]["Moon"]["mansion"]["index"] == 1
    assert body["results"]["Mars"]["mansion"]["index"] == 2
    assert body["provenance"]["tradition"] == "picatrix"


def test_manazil_bulk_route_rejects_empty_keys_and_oversized_payload(
    client: TestClient,
) -> None:
    empty_key = client.post(
        "/v1/manazil/bulk",
        json={"positions": {" ": 0.0}},
    )
    oversized = client.post(
        "/v1/manazil/bulk",
        json={"positions": {f"Body{i}": 0.0 for i in range(501)}},
    )

    assert empty_key.status_code == 422
    assert oversized.status_code == 422


def test_manazil_tradition_lookup_route_returns_variant_text(client: TestClient) -> None:
    response = client.get("/v1/manazil/traditions/ibn_alarabi/mansions/1")

    assert response.status_code == 200
    body = response.json()
    assert body["mansion_index"] == 1
    assert body["tradition"] == "ibn_alarabi"
    assert "Divine Name" in body["signification"]
    assert body["provenance"]["stage_sequence"] == [
        "mansion_index_validation",
        "tradition_attribution_lookup",
        "tradition_response_serialization",
    ]


def test_manazil_tradition_lookup_route_rejects_invalid_inputs(client: TestClient) -> None:
    invalid_index = client.get("/v1/manazil/traditions/al_biruni/mansions/29")
    invalid_tradition = client.get("/v1/manazil/traditions/unknown/mansions/1")

    assert invalid_index.status_code == 422
    assert invalid_tradition.status_code == 422


def test_manazil_position_accepts_a_bare_longitude(client: TestClient) -> None:
    # The default tradition is the equal-division Agrippa scheme, which needs no date.
    response = client.post("/v1/manazil/position", json={"longitude": 254.526})
    assert response.status_code == 200
    body = response.json()
    assert body["provenance"]["tradition"] == "agrippa"
    assert body["result"]["mansion"]["index"] == 20
    assert body["result"]["computation_longitude"] == pytest.approx(254.526)
    assert body["provenance"]["computational_basis"] == "equal_division_360_by_28"
    assert body["provenance"]["default_authority"] == "agrippa_de_occulta_philosophia_ii_33"


@pytest.mark.requires_ephemeris
def test_manazil_star_based_position_reports_its_own_basis(client: TestClient) -> None:
    response = client.post(
        "/v1/manazil/position",
        json={"longitude": 254.526, "tradition": "al_biruni", "jd_ut": 2407422.951412},
    )
    assert response.status_code == 200
    body = response.json()
    # The computation longitude is the longitude used, not an equal-division rebuild.
    assert body["result"]["computation_longitude"] == pytest.approx(254.526)
    assert body["provenance"]["computational_basis"] == "marker_star_boundaries"
    assert body["provenance"]["default_authority"] == "al_biruni_book_of_instruction"
    assert "marker_star_mansion_assignment" in body["provenance"]["stage_sequence"]
    assert "equal_28_mansion_assignment" not in body["provenance"]["stage_sequence"]


def test_manazil_catalog_applies_the_requested_tradition(client: TestClient) -> None:
    picatrix = client.get("/v1/manazil/catalog", params={"tradition": "picatrix"}).json()
    lookup = client.get("/v1/manazil/traditions/picatrix/mansions/2").json()
    assert picatrix["mansions"][1]["nature"] == lookup["nature"]
    assert picatrix["provenance"]["default_authority"] == "picatrix_i_4"
    star = client.get("/v1/manazil/catalog", params={"tradition": "al_biruni"}).json()
    assert star["span_degrees"] is None
    assert star["provenance"]["computational_basis"] == "marker_star_boundaries"
