"""HTTP and membership witnesses for shared-ARMC placement comparison."""

import pytest
from fastapi.testclient import TestClient

from moira.constants import HouseSystem
from moira.houses import compare_placements, houses_from_armc
from moira_server.app import create_app
from moira_server.dependencies import get_engine
from moira_server.models.common import REST_BATCH_MAX_ITEMS


pytestmark = pytest.mark.loopback
_PATH = "/v1/houses/placements/compare"
_GEOMETRY = {"armc": 220.0, "obliquity": 23.4392911, "latitude": 80.0}
_PAYLOAD = {**_GEOMETRY, "left_system": "Pullen SD", "right_system": "Porphyry"}


@pytest.fixture
def client():
    app = create_app()

    def unexpected_engine():
        pytest.fail("Static placement comparison must not require an ephemeris engine.")

    app.dependency_overrides[get_engine] = unexpected_engine
    return TestClient(app)


def _post(client, **payload):
    response = client.post(_PATH, json={**_PAYLOAD, **payload})
    assert response.status_code == 200, response.text
    return response.json()


def test_placement_comparison_matches_direct_engine(client):
    left = houses_from_armc(220, 23.4392911, 80, HouseSystem.PULLEN_SD)
    right = houses_from_armc(220, 23.4392911, 80, HouseSystem.PORPHYRY)
    duplicated_cusp = left.cusps[1]
    points = {"Before": duplicated_cusp - 0.01, "Opening cusp": duplicated_cusp, "Wrapped": -390.0}
    result = _post(client, points=points)

    assert result["left"]["cusps"] == list(left.cusps)
    assert result["right"]["cusps"] == list(right.cusps)
    assert result["zodiac_offset_deg"] == 0
    assert set(result["placements"]) == set(points)
    for name, longitude in points.items():
        expected = compare_placements(longitude, left, right)
        actual = result["placements"][name]
        assert actual["longitude"] == expected.longitude
        for side, placement in zip(("left", "right"), expected.placements, strict=True):
            assert actual[side] == {
                "house": placement.house,
                "exact_on_cusp": placement.exact_on_cusp,
                "cusp_longitude": placement.cusp_longitude,
            }
        assert actual["all_agree"] is expected.all_agree
        assert actual["angularity_agrees"] is expected.angularity_agrees

    # Pullen SD houses 2 and 3 share an opening cusp here. Only house 3
    # has a non-empty interval starting there.
    assert duplicated_cusp == left.cusps[2]
    placements = result["placements"]
    assert placements["Before"]["left"]["house"] == 1
    assert placements["Opening cusp"]["left"]["house"] == 3
    assert placements["Opening cusp"]["left"]["exact_on_cusp"] is True
    assert placements["Opening cusp"]["right"]["house"] == 2
    assert placements["Opening cusp"]["all_agree"] is False
    assert placements["Opening cusp"]["angularity_agrees"] is False
    assert placements["Wrapped"]["longitude"] == 330.0


def test_placement_comparison_uses_returned_cusp_zodiac(client):
    result = _post(
        client, left_system="Whole Sign", right_system="Solar Sign",
        ayanamsa_offset=24, sun_longitude=27, include_boundary_geometry=True,
        points={"Spring point": 360.0, "Rounded seam": -1e-15, "Previous arc": -0.01},
    )
    assert result["zodiac_offset_deg"] == 24
    for side in ("left", "right"):
        assert result[side]["boundary_geometry"]["zodiac_offset_deg"] == 24
    assert result["right"]["cusps"][0] == 0

    placements = result["placements"]
    for name in ("Spring point", "Rounded seam"):
        assert placements[name]["longitude"] == 0
        assert placements[name]["right"] == {"house": 1, "exact_on_cusp": True, "cusp_longitude": 0}
    assert placements["Previous arc"]["right"]["house"] == 12
    assert placements["Previous arc"]["right"]["exact_on_cusp"] is False


def test_placement_comparison_computes_each_fallback_figure_once(client, monkeypatch):
    systems = []

    def record_figures(armc, obliquity, latitude, system, **kwargs):
        systems.append(system)
        return houses_from_armc(armc, obliquity, latitude, system, **kwargs)

    monkeypatch.setattr("moira_server.services.chart.houses_from_armc", record_figures)
    points = {f"Point {index}": index for index in range(REST_BATCH_MAX_ITEMS)}
    result = _post(client, left_system="Koch", points=points)
    assert systems == [HouseSystem.KOCH, HouseSystem.PORPHYRY]
    assert result["left"]["system"] == HouseSystem.KOCH
    assert result["left"]["effective_system"] == result["right"]["effective_system"] == HouseSystem.PORPHYRY
    assert result["left"]["fallback"] is True
    assert result["left"]["fallback_reason"]
    assert result["right"]["fallback"] is False
    assert len(result["placements"]) == REST_BATCH_MAX_ITEMS
    assert all(row["all_agree"] and row["angularity_agrees"] for row in result["placements"].values())


@pytest.mark.parametrize(("override", "side"), [
    ({"left_system": "Koch", "policy": {"polar_fallback": "raise"}}, "left_system"),
    ({"right_system": "Solar Sign"}, "right_system"),
])
def test_placement_comparison_identifies_refused_side(client, override, side):
    response = client.post(_PATH, json={**_PAYLOAD, "points": {"Sun": 0}, **override})
    assert response.status_code == 422, response.text
    assert response.json()["message"].startswith(f"{side}:")
    assert "placements" not in response.json()


@pytest.mark.parametrize("points", [
    {},
    {"": 0},
    {" Sun": 0},
    {"X" * 129: 0},
    {"Sun": True},
    {"Sun": "42"},
    {str(i): i for i in range(REST_BATCH_MAX_ITEMS + 1)},
])
def test_invalid_placement_inputs_do_not_compute_houses(client, monkeypatch, points):
    def unexpected_computation(*args, **kwargs):
        pytest.fail("The route computed a house figure for invalid points.")

    monkeypatch.setattr("moira_server.services.chart.houses_from_armc", unexpected_computation)
    response = client.post(_PATH, json={**_PAYLOAD, "points": points})
    assert response.status_code == 422, response.text


def test_placement_comparison_rejects_nonfinite_longitude(client):
    response = client.post(
        _PATH, headers={"Content-Type": "application/json"},
        content='{"armc":220,"obliquity":23.4392911,"latitude":80,"left_system":"PSD",'
                '"right_system":"O","points":{"Sun":1e400}}',
    )
    assert response.status_code == 422, response.text


def test_placement_comparison_openapi_preserves_pair_inputs_and_bounds(client):
    schema = client.app.openapi()
    models = schema["components"]["schemas"]
    request = models["HousePlacementComparisonRequest"]
    base = models["HouseComparisonRequest"]
    assert set(request["required"]) == set(base["required"]) | {"points"}
    assert all(request["properties"][key] == value for key, value in base["properties"].items())
    points = request["properties"]["points"]
    assert points["minProperties"] == 1
    assert points["maxProperties"] == REST_BATCH_MAX_ITEMS
    operation = schema["paths"][_PATH]["post"]
    assert operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/HousePlacementComparisonResponse"
    )
