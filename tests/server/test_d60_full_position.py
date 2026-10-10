"""PVR full-profile transport, hostile preflight and real-reader checks."""
import json
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

from moira.varga import D60Method, shashtiamsha
from moira_server.app import create_app
from moira_server.config import ServerConfig

pytestmark = pytest.mark.loopback
PROFILE = "pvr_textbook_linear"
DERIVED_PROFILE = "classical_derived_linear"
CHART = {"dt": "2000-01-01T12:00:00+00:00", "ayanamsa_system": "Lahiri"}
ROUTES = [
    ("named", {"sidereal_longitude": 31.125, "varga": "shashtiamsha"}, ()),
    ("named/batch", {"longitudes": {"Sun": 31.125, "Moon": 359.75}, "varga": "shashtiamsha"}, ("results", "Sun")),
    ("shodashvarga", {"sidereal_longitude": 31.125}, ("vargas", "shashtiamsha")),
    ("shodashvarga/batch", {"longitudes": {"Sun": 31.125, "Moon": 359.75}}, ("results", "Sun", "shashtiamsha")),
    ("chart/named", CHART | {"body": "Sun", "varga": "shashtiamsha"}, ("result",)),
    ("chart/shodashvarga", CHART | {"body": "Sun"}, ("result", "vargas", "shashtiamsha")),
    ("chart/shodashvarga/batch", CHART | {"bodies": ["Sun", "Moon"]}, ("results", "Sun", "shashtiamsha")),
]


@pytest.fixture(scope="module")
def client():
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("moira_server.app.create_engine", lambda config: object())
        with TestClient(create_app(ServerConfig(prewarm_enabled=False))) as value:
            yield value


def context(engine, request, required_bodies):
    return SimpleNamespace(
        requested_datetime=CHART["dt"], normalized_datetime_utc=CHART["dt"], jd_ut=2451545,
        ayanamsa_system="Lahiri", ayanamsa_offset=23.85, requested_bodies=required_bodies,
        returned_bodies=required_bodies, sidereal_longitudes={body: 31.125 if body == "Sun" else 359.75 for body in required_bodies},
        observer=None, houses=None, tropical_lagna=None, sidereal_lagna=None,
        sidereal_lagna_sign_index=None, stage_sequence=("context_materialization",),
    )


def point_at(body, path):
    for key in path:
        body = body[key]
    return body


@pytest.fixture(params=[PROFILE, DERIVED_PROFILE])
def profile(request):
    return request.param


def assert_point(point, longitude, profile):
    engine = shashtiamsha(longitude, d60_method=D60Method(profile))
    for field in ("longitude", "varga_longitude", "sign", "sign_degree", "deity"):
        assert point[field] == getattr(engine, field)
    assert point["d60_method"] == profile
    assert point["d60_source_references"] == list(engine.d60_source_references)
    assert point["d60_degree_attribution"] == engine.d60_degree_attribution


@pytest.mark.parametrize("route,payload,path", ROUTES)
def test_all_full_point_shapes_apply_profile_and_source_receipt(client, monkeypatch, route, payload, path, profile):
    monkeypatch.setattr("moira_server.services.varga._derive_varga_context", context)
    response = client.post("/v1/varga/" + route, json=payload | {"d60_method": profile})
    assert response.status_code == 200, response.text
    assert_point(point_at(response.json(), path), 31.125, profile)
    default = client.post("/v1/varga/" + route, json=payload)
    assert default.status_code == 200, default.text
    assert point_at(default.json(), path)["d60_method"] == "harmonic"
    body = response.json()
    if "shodashvarga" in route:
        root = body.get("result", body)
        charts = root.get("results", {"Sun": root.get("vargas")})
        for chart in charts.values():
            assert chart["navamsa"]["d60_method"] is None
            assert chart["navamsa"]["d60_source_references"] == []
            assert chart["navamsa"]["d60_degree_attribution"] is None
    if "batch" in route:
        other = body["results"]["Moon"]
        assert_point(other["shashtiamsha"] if "shodashvarga" in route else other, 359.75, profile)


@pytest.mark.parametrize("route,payload,path", ROUTES)
@pytest.mark.parametrize("method", ["unknown", "bphs_santhanam_sign", True, None])
def test_invalid_full_profile_rejected_before_resources(client, monkeypatch, route, payload, path, method):
    monkeypatch.setattr("moira_server.services.varga._derive_varga_context", lambda *a, **kw: pytest.fail("preflight must reject before chart work"))
    response = client.post("/v1/varga/" + route, json=payload | {"d60_method": method})
    assert response.status_code == 422, response.text
    assert response.json()["error_code"] == "validation_error"
    assert response.json()["request_id"] == response.headers["X-Request-ID"]


@pytest.mark.parametrize("route,payload,path", [ROUTES[0], ROUTES[1], ROUTES[4]])
def test_profile_inapplicable_to_other_named_division(client, monkeypatch, route, payload, path, profile):
    monkeypatch.setattr("moira_server.services.varga._derive_varga_context", lambda *a, **kw: pytest.fail("inapplicable method must reject before chart work"))
    response = client.post("/v1/varga/" + route, json=payload | {"varga": "navamsa", "d60_method": profile})
    assert response.status_code == 422, response.text


@pytest.mark.parametrize("route,payload,path", ROUTES[:4])
@pytest.mark.parametrize("bad", [True, "12", float("nan"), float("inf"), 10**400])
def test_source_longitude_preflight_is_strict_finite(client, route, payload, path, bad, profile):
    body = payload | {"d60_method": profile}
    if "longitudes" in body:
        body["longitudes"] = {"Sun": bad}
    else:
        body["sidereal_longitude"] = bad
    response = client.post("/v1/varga/" + route, content=json.dumps(body), headers={"Content-Type": "application/json"})
    assert response.status_code == 422, response.text


def test_openapi_and_sign_only_profile_projection(client):
    schemas = client.app.openapi()["components"]["schemas"]
    for name in ("VargaNamedRequest", "VargaNamedBatchRequest", "VargaShodashvargaRequest", "VargaShodashvargaBatchRequest", "VargaChartNamedRequest", "VargaChartShodashvargaRequest", "VargaChartShodashvargaBatchRequest"):
        assert set(schemas[name]["properties"]["d60_method"]["enum"]) == {"harmonic", PROFILE, DERIVED_PROFILE}
    result = client.post("/v1/varga/d60/sign", json={"sidereal_longitude": 31.125, "method": PROFILE})
    assert result.status_code == 200
    assert result.json()["sign"] == "Cancer"
    assert "sign_degree" not in result.json()
    assert "2000:6.2.20" in result.json()["source_reference"]
    assert "d60_method" not in schemas["VargaGenericRequest"]["properties"]


@pytest.mark.parametrize("route,payload,path", ROUTES[:4])
def test_source_composition_preserves_tiny_negative_left_wrap(client, route, payload, path, profile):
    body = payload | {"d60_method": profile}
    if "longitudes" in body:
        body["longitudes"] = {"Sun": -1e-300}
    else:
        body["sidereal_longitude"] = -1e-300
    response = client.post("/v1/varga/" + route, json=body)
    assert response.status_code == 200, response.text
    assert_point(point_at(response.json(), path), -1e-300, profile)


def test_derived_sign_projection_has_classical_sign_locator(client):
    response = client.post("/v1/varga/d60/sign", json={"sidereal_longitude": 31.125, "method": DERIVED_PROFILE})
    assert response.status_code == 200
    assert response.json()["source_reference"] == "BPHS-Santhanam-Vol1:6.33:printed83:commentary"
    assert "sign_degree" not in response.json()


def test_strength_composition_preserves_tiny_negative_left_wrap(client, profile):
    lons = {"Sun": -1e-300, "Moon": 200, "Mars": 125, "Mercury": 315,
            "Jupiter": 105, "Venus": 283 + 25 / 60, "Saturn": 190}
    response = client.post("/v1/varga/vimshopaka", json={"sidereal_longitudes": lons, "d60_method": profile})
    assert response.status_code == 200, response.text
    for planet, value in response.json()["planets"].items():
        assert value["d60_method"] == profile
        assert value["d60_source_references"] == list(shashtiamsha(lons[planet], d60_method=D60Method(profile)).d60_source_references)


@pytest.mark.parametrize("group", ["dashavarga", "shodashavarga"])
def test_strength_profile_receipt_is_copied_from_engine(client, group, profile):
    lons = {"Sun": 130, "Moon": 200, "Mars": 125, "Mercury": 315,
            "Jupiter": 105, "Venus": 283 + 25 / 60, "Saturn": 190}
    request = {"sidereal_longitudes": lons, "group": group}
    result = client.post("/v1/varga/vimshopaka", json=request | {"d60_method": profile})
    source = client.post("/v1/varga/vimshopaka", json=request | {"d60_method": "bphs_santhanam_sign"})
    assert result.status_code == source.status_code == 200
    for planet, value in result.json()["planets"].items():
        assert value["d60_method"] == profile
        assert value["entries"] == source.json()["planets"][planet]["entries"]
        assert value["total"] == source.json()["planets"][planet]["total"]
        assert value["d60_source_references"] == list(shashtiamsha(lons[planet], d60_method=D60Method(profile)).d60_source_references)


@pytest.mark.parametrize("route,payload,path", ROUTES[4:])
def test_real_reader_chart_profile_uses_returned_sidereal_frame(moira_engine, monkeypatch, route, payload, path, profile):
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    with TestClient(create_app(ServerConfig(prewarm_enabled=False))) as value:
        result = value.post("/v1/varga/" + route, json=payload | {"d60_method": profile})
    assert result.status_code == 200, result.text
    body = result.json()
    assert_point(point_at(body, path), body["provenance"]["sidereal_longitudes"]["Sun"], profile)
