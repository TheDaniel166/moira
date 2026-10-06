"""Adversarial direct Vedic inputs fail before doctrine dispatch."""
import copy
import json

from fastapi.testclient import TestClient
import pytest

from moira_server.app import create_app
from moira_server.config import ServerConfig

pytestmark = pytest.mark.loopback

_LONS = {"Sun": 10, "Moon": 35, "Mars": 190, "Mercury": 160, "Jupiter": 100, "Venus": 185, "Saturn": 280}
_SIGNS = {p: int(v // 30) for p, v in _LONS.items()} | {"Lagna": 0}
_DIRECT = [
    ("/v1/yogas/evaluate", {"sidereal_longitudes": _LONS, "lagna_sidereal_lon": 0}),
    ("/v1/avasthas/evaluate", {"sidereal_longitudes": _LONS, "lagna_sidereal_lon": 0}),
    ("/v1/jaimini/extended/arudhas", {"sidereal_longitudes": _LONS, "lagna_sidereal_lon": 0}),
    ("/v1/jaimini/extended/argala", {"sidereal_longitudes": _LONS, "lagna_sidereal_lon": 0}),
    ("/v1/jaimini/extended/karakamsa", {"sidereal_longitudes": _LONS, "lagna_sidereal_lon": 0}),
    ("/v1/jaimini/extended/chara-dasha", {"sidereal_longitudes": _LONS, "lagna_sidereal_lon": 0, "birth_jd": 2451545}),
    ("/v1/varga/vimshopaka", {"sidereal_longitudes": _LONS}),
]


@pytest.fixture(scope="module")
def client():
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("moira_server.app.create_engine", lambda config: object())
        with TestClient(create_app(ServerConfig(prewarm_enabled=False))) as value:
            yield value


def rejected(client, route, body):
    response = client.post(route, content=json.dumps(body), headers={"Content-Type": "application/json"})
    assert response.status_code == 422, response.text
    assert response.json()["error_code"] == "validation_error"
    return response


@pytest.mark.parametrize("route,body", _DIRECT)
@pytest.mark.parametrize("bad", [True, "12", "NaN", float("inf")])
def test_classical_longitude_values_are_strict_and_finite(client, route, body, bad):
    request = copy.deepcopy(body)
    request["sidereal_longitudes"]["Sun"] = bad
    rejected(client, route, request)


@pytest.mark.parametrize("route,body", _DIRECT)
def test_unknown_body_and_missing_classical_body_are_rejected(client, route, body):
    request = copy.deepcopy(body)
    request["sidereal_longitudes"]["Pluto"] = 12
    rejected(client, route, request)
    request = copy.deepcopy(body)
    del request["sidereal_longitudes"]["Mars"]
    rejected(client, route, request)


@pytest.mark.parametrize("route,body", _DIRECT[:-1])
def test_lagna_is_finite(client, route, body):
    request = copy.deepcopy(body)
    request["lagna_sidereal_lon"] = float("nan")
    rejected(client, route, request)


@pytest.mark.parametrize("route", ["avasthas/evaluate", "jaimini/extended/arudhas", "jaimini/extended/argala", "jaimini/extended/chara-dasha"])
@pytest.mark.parametrize("nodes", [{"Sun": 1}, {"Rahu": True}, {"Ketu": "Infinity"}])
def test_node_maps_cannot_overwrite_classical_bodies_or_admit_bad_numbers(client, route, nodes):
    body = {"sidereal_longitudes": _LONS, "lagna_sidereal_lon": 0, "node_longitudes": nodes}
    if route.endswith("chara-dasha"):
        body["birth_jd"] = 2451545
    rejected(client, "/v1/" + route, body)


def test_karakamsa_eight_requires_rahu_and_preserves_both_readings(client):
    body = {"sidereal_longitudes": _LONS, "scheme": 8}
    rejected(client, "/v1/jaimini/extended/karakamsa", body)
    body["sidereal_longitudes"] = _LONS | {"Rahu": 80}
    response = client.post("/v1/jaimini/extended/karakamsa", json=body)
    assert response.status_code == 200
    assert response.json()["d9_reading"] and response.json()["d1_reading"]
    assert response.json()["svamsa_sign"] is None


def test_arudha_co_lord_policy_requires_the_declared_node_pair(client):
    body = {"sidereal_longitudes": _LONS, "lagna_sidereal_lon": 0, "arudha_lords": "jaimini_co_lords"}
    rejected(client, "/v1/jaimini/extended/arudhas", body)
    body["node_longitudes"] = {"Rahu": 20}
    rejected(client, "/v1/jaimini/extended/arudhas", body)
    body["node_longitudes"]["Ketu"] = 200
    assert client.post("/v1/jaimini/extended/arudhas", json=body).status_code == 200


def test_avastha_fraction_policy_is_available_without_inventing_the_default(client):
    body = {"sidereal_longitudes": _LONS | {"Sun": 20}, "lagna_sidereal_lon": 0}
    response = client.post("/v1/avasthas/evaluate", json=body)
    assert response.status_code == 200
    assert response.json()["planets"]["Sun"]["baladi_effect_fraction"] is None
    body["vriddha_fraction"] = 0.1
    response = client.post("/v1/avasthas/evaluate", json=body)
    assert response.status_code == 200
    assert response.json()["planets"]["Sun"]["baladi_effect_fraction"] == 0.1
    assert response.json()["vriddha_fraction"] == 0.1
    assert response.json()["relationship_scheme"] == "compound"
    body["vriddha_fraction"] = 2
    rejected(client, "/v1/avasthas/evaluate", body)


@pytest.mark.parametrize("route", ["kakshya-transit", "shodhya-pinda"])
@pytest.mark.parametrize("signs", [{}, _SIGNS | {"Sun": 12}, _SIGNS | {"Sun": True}, _SIGNS | {"Pluto": 0}])
def test_ashtakavarga_references_are_complete_and_bounded(client, route, signs):
    body = {"planet": "Sun", "sign_indices": signs}
    body.update({"transit_sidereal_lon": 1} if route == "kakshya-transit" else {"reduced_rekhas": [1] * 12})
    rejected(client, "/v1/ashtakavarga/" + route, body)


@pytest.mark.parametrize("rekhas", [[0] * 11, [0] * 13, [True] * 12, [-1] * 12, [9] * 12])
def test_shodhya_reduced_table_is_exactly_twelve_integer_counts(client, rekhas):
    rejected(client, "/v1/ashtakavarga/shodhya-pinda", {"planet": "Sun", "sign_indices": _SIGNS, "reduced_rekhas": rekhas})


def test_ashtakavarga_helpers_preserve_direct_engine_results(client):
    from moira.ashtakavarga import kakshya_transit, shodhya_pinda
    response = client.post("/v1/ashtakavarga/kakshya-transit", json={"planet": "Sun", "sign_indices": _SIGNS, "transit_sidereal_lon": 65})
    assert response.status_code == 200
    assert response.json()["lord_contributed"] is kakshya_transit("Sun", 65, _SIGNS).lord_contributed
    response = client.post("/v1/ashtakavarga/shodhya-pinda", json={"planet": "Sun", "sign_indices": _SIGNS, "reduced_rekhas": [1] * 12})
    assert response.status_code == 200
    assert response.json()["shodhya_pinda"] == shodhya_pinda("Sun", (1,) * 12, _SIGNS).shodhya_pinda


@pytest.mark.parametrize("field,value", [("latitude", 91), ("longitude", 181), ("latitude", "NaN"), ("longitude", True)])
def test_kalavela_coordinates_fail_at_request_boundary(client, field, value):
    rejected(client, "/v1/upagrahas/kalavelas", {"dt": "2000-01-01T00:00:00Z", "latitude": 0, "longitude": 0} | {field: value})


def test_yoga_speed_and_chara_epoch_reject_non_finite_values(client):
    rejected(client, "/v1/yogas/evaluate", {"sidereal_longitudes": _LONS, "lagna_sidereal_lon": 0, "planet_speeds": {"Mars": "NaN"}})
    rejected(client, "/v1/jaimini/extended/chara-dasha", {"sidereal_longitudes": _LONS, "lagna_sidereal_lon": 0, "birth_jd": float("nan")})
