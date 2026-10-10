"""VED-001/003 strict preflight, transport, OpenAPI and real-reader checks."""
import json
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

from moira.varga import shashtiamsha
from moira_server.app import create_app
from moira_server.config import ServerConfig

pytestmark = pytest.mark.loopback

LONS = {"Sun": 130, "Moon": 200, "Mars": 125, "Mercury": 315,
        "Jupiter": 105, "Venus": 283 + 25 / 60, "Saturn": 190}
CHARA = {"sidereal_longitudes": LONS, "lagna_sidereal_lon": 5, "birth_jd": 2451545}
CHART = {"dt": "2000-01-01T12:00:00+00:00", "ayanamsa_system": "Lahiri"}
SOURCE = "bphs_santhanam_sign"
PLACEMENTS = [
    ("generic", {"sidereal_longitude": 2.75, "divisor": 60}, (), None),
    ("named", {"sidereal_longitude": 2.75, "varga": "shashtiamsha"}, (), "Kinnara"),
    ("shodashvarga", {"sidereal_longitude": 2.75}, ("vargas", "shashtiamsha"), "Kinnara"),
    ("named/batch", {"longitudes": {"Sun": 2.75}, "varga": "shashtiamsha"}, ("results", "Sun"), "Kinnara"),
    ("shodashvarga/batch", {"longitudes": {"Sun": 2.75}}, ("results", "Sun", "shashtiamsha"), "Kinnara"),
    ("chart/named", CHART | {"body": "Sun", "varga": "shashtiamsha"}, ("result",), "Kinnara"),
    ("chart/shodashvarga", CHART | {"body": "Sun"}, ("result", "vargas", "shashtiamsha"), "Kinnara"),
    ("chart/shodashvarga/batch", CHART | {"bodies": ["Sun"]}, ("results", "Sun", "shashtiamsha"), "Kinnara"),
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
    assert response.json()["request_id"] == response.headers["X-Request-ID"]
    return response


@pytest.mark.parametrize("cycles", [True, False, 0, -1, 3, 2.0, "2", None])
def test_chara_cycle_rejection_is_validation_not_dispatch(client, cycles):
    assert "cycles" in rejected(client, "/v1/jaimini/extended/chara-dasha", CHARA | {"cycles": cycles}).text


@pytest.mark.parametrize("nodes", [{}, {"Rahu": 45}, {"Ketu": 225}])
def test_chara_node_pair_preflight(client, nodes):
    assert "node_longitudes" in rejected(client, "/v1/jaimini/extended/chara-dasha", CHARA | {"node_longitudes": nodes}).text


def test_chara_default_and_second_cycle_copy_engine_receipt(client):
    first = client.post("/v1/jaimini/extended/chara-dasha", json=CHARA).json()
    second = client.post("/v1/jaimini/extended/chara-dasha", json=CHARA | {"cycles": 2, "node_longitudes": {"Rahu": 45, "Ketu": 225}}).json()
    assert first["period_count"] == len(first["periods"]) == 12
    assert second["period_count"] == len(second["periods"]) == 24
    assert first["computation"]["cycle_count"] == 1
    assert second["computation"] == {
        "cycle_count": 2, "lord_mode": "moira_existing_co_lords", "formulation_id": "moira_kn_rao_existing_v1",
        "cycle_policy": "repeat_first_cycle", "year_basis": "julian_365.25", "year_days": 365.25,
        "epoch_basis": "caller_supplied_julian_day",
    }
    assert first["computation"]["lord_mode"] == "classical_seven"


def stub_context(engine, request, required_bodies):
    return SimpleNamespace(
        requested_datetime=CHART["dt"], normalized_datetime_utc=CHART["dt"], jd_ut=2451545,
        ayanamsa_system="Lahiri", ayanamsa_offset=23.85, requested_bodies=required_bodies,
        returned_bodies=required_bodies, sidereal_longitudes={body: 2.75 for body in required_bodies},
        observer=None, houses=None, tropical_lagna=None, sidereal_lagna=None,
        sidereal_lagna_sign_index=None, stage_sequence=("context_materialization",),
    )


@pytest.mark.parametrize("route,payload,path,deity", PLACEMENTS)
def test_all_eight_placement_routes_preserve_nullable_engine_deity(client, monkeypatch, route, payload, path, deity):
    monkeypatch.setattr("moira_server.services.varga._derive_varga_context", stub_context)
    response = client.post("/v1/varga/" + route, json=payload)
    assert response.status_code == 200, response.text
    point = response.json()
    for key in path:
        point = point[key]
    assert "deity" in point and point["deity"] == deity
    assert point["d60_method"] == "harmonic"
    assert point["sign"] == "Virgo"  # legacy harmonic midpoint 2.75d * 60


@pytest.mark.parametrize("route,payload,path,deity", PLACEMENTS[1:])
@pytest.mark.parametrize("method", [SOURCE, "unknown", None])
def test_full_point_method_fails_before_chart_resource_work(client, monkeypatch, route, payload, path, deity, method):
    def forbidden(*args, **kwargs):
        pytest.fail("sign-only/unknown method reached chart derivation")
    monkeypatch.setattr("moira_server.services.varga._derive_varga_context", forbidden)
    assert "d60_method" in rejected(client, "/v1/varga/" + route, payload | {"d60_method": method}).text


def test_sign_only_route_has_no_continuous_degree_claim(client):
    response = client.post("/v1/varga/d60/sign", json={"sidereal_longitude": 283 + 25 / 60, "method": SOURCE})
    assert response.status_code == 200, response.text
    point = response.json()
    assert (point["sign_index"], point["sign"], point["method"], point["position_scope"]) == (11, "Pisces", SOURCE, "sign_only")
    assert "sign_degree" not in point and "varga_longitude" not in point
    harmonic = client.post("/v1/varga/d60/sign", json={"sidereal_longitude": 283 + 25 / 60}).json()
    assert harmonic["sign"] == "Gemini" and harmonic["method"] == "harmonic"
    assert harmonic["source_reference"] == "moira_generic_harmonic"


@pytest.mark.parametrize("bad", [True, "12", float("nan"), float("inf")])
def test_sign_route_strict_finite_preflight(client, bad):
    rejected(client, "/v1/varga/d60/sign", {"sidereal_longitude": bad, "method": SOURCE})


def test_sign_route_unknown_method_is_not_a_fallback(client):
    rejected(client, "/v1/varga/d60/sign", {"sidereal_longitude": 10, "method": "unknown"})


@pytest.mark.parametrize("group,weight", [("dashavarga", 5.0), ("shodashavarga", 4.0)])
def test_vimshopaka_applied_method_and_weighted_effect(client, group, weight):
    payload = {"sidereal_longitudes": LONS, "group": group}
    old = client.post("/v1/varga/vimshopaka", json=payload).json()["planets"]["Venus"]
    new = client.post("/v1/varga/vimshopaka", json=payload | {"d60_method": SOURCE}).json()["planets"]["Venus"]
    assert old["d60_method"] == "harmonic" and new["d60_method"] == SOURCE
    assert old["entries"][:-1] == new["entries"][:-1]
    entry = new["entries"][-1]
    assert (entry["varga_sign_index"], entry["lord"], entry["dignity"], entry["weight"], entry["points"]) == (11, "Jupiter", "shatru", weight, weight * 7 / 20)
    assert new["total"] - old["total"] == pytest.approx(-11 * weight / 20, abs=1e-12)
    rejected(client, "/v1/varga/vimshopaka", payload | {"d60_method": "unknown"})


def test_vimshopaka_non_d60_group_method_is_inapplicable(client):
    payload = {"sidereal_longitudes": LONS, "group": "shadvarga"}
    rejected(client, "/v1/varga/vimshopaka", payload | {"d60_method": SOURCE})
    assert client.post("/v1/varga/vimshopaka", json=payload).json()["planets"]["Sun"]["d60_method"] is None


def test_openapi_distinguishes_sign_only_and_full_point_methods(client):
    schema = client.app.openapi()
    schemas = schema["components"]["schemas"]
    assert "/v1/varga/d60/sign" in schema["paths"]
    assert set(schemas["D60Method"]["enum"]) == {"harmonic", SOURCE, "pvr_textbook_linear", "classical_derived_linear"}
    assert schemas["D60SignResponse"]["properties"]["position_scope"]["const"] == "sign_only"
    assert "sign_degree" not in schemas["D60SignResponse"]["properties"]
    for name in ("VargaNamedRequest", "VargaNamedBatchRequest", "VargaShodashvargaRequest", "VargaShodashvargaBatchRequest", "VargaChartNamedRequest", "VargaChartShodashvargaRequest", "VargaChartShodashvargaBatchRequest"):
        assert set(schemas[name]["properties"]["d60_method"]["enum"]) == {"harmonic", "pvr_textbook_linear", "classical_derived_linear"}
    assert {part.get("type") for part in schemas["VargaPointResponse"]["properties"]["deity"]["anyOf"]} == {"string", "null"}
    assert schemas["CharaDashaRequest"]["properties"]["cycles"]["minimum"] == 1
    assert schemas["CharaDashaRequest"]["properties"]["cycles"]["maximum"] == 2
    assert schemas["CharaDashaComputationResponse"]["properties"]["year_days"]["const"] == 365.25


@pytest.mark.parametrize("route,payload,path,deity", PLACEMENTS[5:])
def test_real_reader_chart_routes_preserve_d60_receipt(moira_engine, monkeypatch, route, payload, path, deity):
    # Real DE441 chart + Lahiri context; this is a transport/parity check,
    # not an external accuracy oracle for the astronomical longitude.
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    with TestClient(create_app(ServerConfig(prewarm_enabled=False))) as value:
        response = value.post("/v1/varga/" + route, json=payload)
    assert response.status_code == 200, response.text
    body = response.json()
    direct = shashtiamsha(body["provenance"]["sidereal_longitudes"]["Sun"])
    point = body
    for key in path:
        point = point[key]
    assert point["deity"] == direct.deity and point["deity"] is not None
    assert point["d60_method"] == direct.d60_method.value == "harmonic"
    assert point["varga_longitude"] == direct.varga_longitude
