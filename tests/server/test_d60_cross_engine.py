"""All seven full-point transports and live-reader charts use external outputs."""
import json
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira.varga import D60Method, shashtiamsha

pytestmark = pytest.mark.loopback
ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = json.loads((ROOT / "tests/artifacts/oracle/d60_cross_engine_2026-10-07.json").read_text(encoding="utf-8"))
CASES = EVIDENCE["cases"]
TOLERANCE = EVIDENCE["numeric_absolute_tolerance_deg"]
PROFILE = EVIDENCE["profile"]
SIGNS = ("Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
         "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces")
CHARTS = sorted({(row["dt"], row["ayanamsa_system"]) for row in CASES if row["kind"] == "planetary"})
REPRESENTATIVES = [next(row for row in CASES if row["kind"] == "random" and row["natal_sign_index"] == sign) for sign in range(12)]
ROUTES = [
    ("named", ()), ("named/batch", ("results", "Sun")),
    ("shodashvarga", ("vargas", "shashtiamsha")),
    ("shodashvarga/batch", ("results", "Sun", "shashtiamsha")),
    ("chart/named", ("result",)),
    ("chart/shodashvarga", ("result", "vargas", "shashtiamsha")),
    ("chart/shodashvarga/batch", ("results", "Sun", "shashtiamsha")),
]


@pytest.fixture(scope="module")
def client():
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("moira_server.app.create_engine", lambda config: object())
        with TestClient(create_app(ServerConfig(prewarm_enabled=False))) as value:
            yield value


@pytest.fixture(params=[PROFILE, "classical_derived_linear"])
def profile(request):
    return request.param


def assert_external_position(point, row, profile):
    assert point["sign"] == SIGNS[row["pyjhora_sign_index"]], row["id"]
    assert int(point["varga_longitude"] // 30) == row["pyjhora_sign_index"] == row["maitreya_sign_index"]
    assert point["sign_degree"] == pytest.approx(row["pyjhora_sign_degree"], abs=TOLERANCE, rel=0), row["id"]
    assert point["varga_longitude"] == pytest.approx(row["maitreya_instrumented_longitude"], abs=TOLERANCE, rel=0), row["id"]
    assert point["d60_method"] == profile
    # Numeric expectations above remain independently frozen; the transport
    # must also copy the selected canonical source/derivation receipt.
    engine = shashtiamsha(row["longitude"], d60_method=D60Method(profile))
    assert point["d60_source_references"] == list(engine.d60_source_references)
    assert point["d60_degree_attribution"] == engine.d60_degree_attribution


@pytest.mark.parametrize("route,path", ROUTES)
@pytest.mark.parametrize("row", REPRESENTATIVES, ids=lambda row: row["id"])
def test_all_full_point_shapes_against_external_expected_values(client, monkeypatch, route, path, row, profile):
    def context(engine, request, required_bodies):
        return SimpleNamespace(
            requested_datetime="2000-01-01T12:00:00+00:00", normalized_datetime_utc="2000-01-01T12:00:00+00:00",
            jd_ut=2451545, ayanamsa_system="Lahiri", ayanamsa_offset=23.85,
            requested_bodies=required_bodies, returned_bodies=required_bodies,
            sidereal_longitudes={body: row["longitude"] for body in required_bodies},
            observer=None, houses=None, tropical_lagna=None, sidereal_lagna=None,
            sidereal_lagna_sign_index=None, stage_sequence=("context_materialization",),
        )
    monkeypatch.setattr("moira_server.services.varga._derive_varga_context", context)
    payload = {"d60_method": profile}
    if route.startswith("chart/"):
        payload.update(dt="2000-01-01T12:00:00+00:00", ayanamsa_system="Lahiri")
        payload["bodies" if route.endswith("batch") else "body"] = ["Sun"] if route.endswith("batch") else "Sun"
    elif route.endswith("batch"):
        payload["longitudes"] = {"Sun": row["longitude"]}
    else:
        payload["sidereal_longitude"] = row["longitude"]
    if route.endswith("named") or route == "named/batch":
        payload["varga"] = "shashtiamsha"
    response = client.post("/v1/varga/" + route, json=payload)
    assert response.status_code == 200, response.text
    point = response.json()
    for key in path:
        point = point[key]
    assert_external_position(point, row, profile)


@pytest.mark.parametrize("route", ["named/batch", "shodashvarga/batch"])
def test_batch_preserves_120_independent_full_positions(client, route, profile):
    rows = [row for row in CASES if row["kind"] == "random"]
    payload = {"d60_method": profile, "longitudes": {row["id"]: row["longitude"] for row in rows}}
    if route.startswith("named"):
        payload["varga"] = "shashtiamsha"
    response = client.post("/v1/varga/" + route, json=payload)
    assert response.status_code == 200, response.text
    results = response.json()["results"]
    assert set(results) == {row["id"] for row in rows}
    for row in rows:
        value = results[row["id"]]
        assert_external_position(value["shashtiamsha"] if route.startswith("shodashvarga") else value, row, profile)


@pytest.mark.parametrize("date,frame", CHARTS)
def test_real_reader_chart_batch_matches_frozen_independent_d60_outputs(moira_engine, monkeypatch, date, frame, profile):
    rows = [row for row in CASES if row["kind"] == "planetary" and (row["dt"], row["ayanamsa_system"]) == (date, frame)]
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    with TestClient(create_app(ServerConfig(prewarm_enabled=False))) as value:
        response = value.post("/v1/varga/chart/shodashvarga/batch", json={"dt": date, "ayanamsa_system": frame, "bodies": [row["body"] for row in rows], "d60_method": profile})
    assert response.status_code == 200, response.text
    result = response.json()
    for row in rows:
        assert result["provenance"]["sidereal_longitudes"][row["body"]] == row["longitude"]
        assert_external_position(result["results"][row["body"]]["shashtiamsha"], row, profile)


@pytest.mark.parametrize("date,frame", CHARTS)
@pytest.mark.parametrize("group,weight", [("dashavarga", 5), ("shodashavarga", 4)])
def test_strength_transport_selects_externally_corroborated_signs(client, date, frame, group, weight, profile):
    rows = [row for row in CASES if row["kind"] == "planetary" and (row["dt"], row["ayanamsa_system"]) == (date, frame)]
    response = client.post("/v1/varga/vimshopaka", json={"sidereal_longitudes": {row["body"]: row["longitude"] for row in rows}, "group": group, "d60_method": profile})
    assert response.status_code == 200, response.text
    for row in rows:
        entry = next(entry for entry in response.json()["planets"][row["body"]]["entries"] if entry["division"] == 60)
        assert entry["varga_sign_index"] == row["pyjhora_sign_index"] == row["maitreya_sign_index"]
        assert entry["weight"] == weight
