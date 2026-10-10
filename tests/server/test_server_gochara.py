"""Gochar transport parity, source, omission and invalid-input contracts."""
import itertools
import json
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from moira.gochara import (
    GOCHARA_PLANETS, GocharaPolicy, GocharaVedhaMode, GocharaCompleteness,
    GocharaBavMode, gochara_from_positions, gochara_doctrine_options,
)
from moira.ashtakavarga import BhinnashtakavargaResult
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.gochara import GocharaSnapshotRequest
from moira_server.serializers.gochara import serialize_gochara_result

pytestmark = pytest.mark.loopback


@pytest.fixture(scope="module")
def client():
    # Direct doctrine routes must neither request nor inspect a kernel reader.
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("moira_server.app.create_engine", lambda config: object())
        app = create_app(ServerConfig(docs_enabled=True, prewarm_enabled=False))
        with TestClient(app) as value:
            yield value


def payload():
    return {"natal_moon_sidereal_longitude": 0, "transit_sidereal_longitudes": {"Mercury": 210, "Venus": 0}}


_MODES = list(itertools.product(GocharaVedhaMode, GocharaCompleteness, GocharaBavMode))


@pytest.mark.parametrize("vedha,completeness,bav", _MODES)
def test_every_policy_combination_preserves_engine_truth(client, vedha, completeness, bav):
    positions = dict(zip(GOCHARA_PLANETS, (60, 30, 180, 210, 90, 0, 270)))
    raw = {p: [4] * 12 for p in positions} if bav is not GocharaBavMode.OMIT else None
    body = {"natal_moon_sidereal_longitude": 0, "transit_sidereal_longitudes": positions,
            "raw_bav": raw, "policy": {"vedha_mode": vedha.value, "completeness": completeness.value, "bav_mode": bav.value}}
    bhinna = None if raw is None else {p: BhinnashtakavargaResult(p, tuple(v), sum(v)) for p, v in raw.items()}
    direct = gochara_from_positions(0, positions, bhinna=bhinna,
        policy=GocharaPolicy(vedha_mode=vedha, completeness=completeness, bav_mode=bav))
    result = client.post("/v1/gochara/evaluate", json=body)
    assert result.status_code == 200, result.text
    assert result.json() == serialize_gochara_result(direct).model_dump(mode="json")
    profile = client.post("/v1/gochara/profile", json=body)
    assert profile.status_code == 200, profile.text
    assert profile.json()["snapshot"] == result.json()
    assert sum(v[1] for v in profile.json()["chart_summary"]["condition_counts"]) == 7
    network = profile.json()["vedha_network"]
    assert sum(n["observed_in_degree"] for n in network["nodes"]) == len(network["active_edges"])
    assert sum(n["observed_out_degree"] for n in network["nodes"]) == len(network["active_edges"])
    assert network["vedha_evaluated"] is (vedha is GocharaVedhaMode.ORDINARY)


def test_blocked_partial_snapshot_and_network_direction_are_visible(client):
    response = client.post("/v1/gochara/profile", json=payload())
    assert response.status_code == 200
    value = response.json()
    assert value["chart_summary"]["blocked_planets"] == ["Mercury", "Venus"]
    assert value["chart_summary"]["incomplete_observation_planets"] == ["Mercury", "Venus"]
    assert [(w["blocker"]["planet"], w["subject"]["planet"]) for w in value["vedha_network"]["active_edges"]] == [("Venus", "Mercury"), ("Mercury", "Venus")]
    assert value["snapshot"]["source_url"].endswith("-text.pdf")
    assert len(value["snapshot"]["policy"]["selected_options"]) == 8


def test_exempt_occupant_never_becomes_a_blocking_edge(client):
    body = {"natal_moon_sidereal_longitude": 0, "transit_sidereal_longitudes": {"Sun": 60, "Saturn": 240}}
    response = client.post("/v1/gochara/profile", json=body)
    value = response.json()
    sun = value["snapshot"]["planets"][0]
    assert sun["vedha_status"] == "incomplete"
    assert sun["active_vedha_witnesses"] == []
    assert sun["exempt_vedha_witnesses"][0]["exempt"] is True
    assert len(value["vedha_network"]["exempt_edges"]) == 1


def test_empty_observation_is_rejected_like_the_engine(client):
    body = {"natal_moon_sidereal_longitude": 0, "transit_sidereal_longitudes": {}}
    with pytest.raises(ValueError):
        gochara_from_positions(0, {})
    response = client.post("/v1/gochara/profile", json=body)
    assert response.status_code == 422
    assert response.json()["error_code"] == "validation_error"


def test_source_fixture_governs_all_36_http_vedha_pairs(client):
    source = json.loads((Path(__file__).parents[1] / "fixtures/gochara_phaladeepika_26.json").read_text(encoding="utf-8"))
    for subject, rule in source["rules"].items():
        blocker = next(p for p in GOCHARA_PLANETS if p != subject and p not in rule["exempt"])
        for favorable, blocking in rule["vedha"]:
            body = {"natal_moon_sidereal_longitude": 0, "transit_sidereal_longitudes": {subject: (favorable - 1) * 30, blocker: (blocking - 1) * 30}}
            response = client.post("/v1/gochara/evaluate", json=body)
            assert response.status_code == 200
            item = next(p for p in response.json()["planets"] if p["position"]["planet"] == subject)
            assert item["vedha_status"] == "blocked"
            assert item["active_vedha_witnesses"][0]["directed_pair"] == [favorable, blocking]
            assert item["indication_source"].endswith(str(rule["indication_verses"][favorable - 1]))


@pytest.mark.parametrize("route", ["evaluate", "profile"])
@pytest.mark.parametrize("bad", [True, "12", "NaN", float("nan"), float("inf"), None, [], {}])
def test_invalid_natal_numbers_return_structured_422(client, route, bad):
    body = payload()
    body["natal_moon_sidereal_longitude"] = bad
    response = client.post("/v1/gochara/" + route, content=json.dumps(body), headers={"Content-Type": "application/json"})
    assert response.status_code == 422
    assert response.json()["error_code"] == "validation_error"
    assert response.json()["request_id"]


@pytest.mark.parametrize("field,value", [
    ("transit_sidereal_longitudes", {"Rahu": 1}),
    ("transit_sidereal_longitudes", {"Sun": True}),
    ("transit_sidereal_longitudes", {"Sun": "NaN"}),
    ("policy", {"source_profile": "prasna_marga"}),
    ("policy", {"vedha_mode": "counter_vedha"}),
    ("policy", {"reference": "lagna"}),
    ("policy", {"completeness": "require_complete"}),
    ("policy", {"bav_mode": "require_all_raw"}),
    ("raw_bav", {"Sun": [4] * 12}),
    ("raw_bav", {"Mercury": [4] * 11}),
    ("raw_bav", {"Mercury": [9] * 12}),
    ("raw_bav", {"Mercury": [True] * 12}),
    ("raw_bav", {"Mercury": [4.0] * 12}),
    ("raw_bav", {"Rahu": [4] * 12}),
    ("nodes", True),
])
def test_unsupported_scope_and_bad_bav_are_rejected(client, field, value):
    body = payload()
    body[field] = value
    response = client.post("/v1/gochara/evaluate", json=body)
    assert response.status_code == 422, response.text


def test_catalogue_and_openapi_discovery_are_complete(client):
    result = client.get("/v1/gochara/doctrine-options")
    assert result.status_code == 200
    assert [v["id"] for v in result.json()["options"]] == [v.id for v in gochara_doctrine_options()]
    nodes = client.get("/v1/gochara/doctrine-options?topic=nodes").json()["options"]
    assert nodes and all(v["status"] != "admitted" for v in nodes)
    assert client.get("/v1/gochara/doctrine-options?topic=made_up").status_code == 422
    schema = client.get("/openapi.json").json()
    assert schema["paths"]["/v1/gochara/profile"]["post"]["tags"] == ["gochara"]
    assert all(schema["components"]["schemas"][n]["additionalProperties"] is False for n in ["GocharaSnapshotRequest", "GocharaPolicyRequest"])
    assert schema["components"]["schemas"]["GocharaDoctrineOptionResponse"]["properties"]["status"]
    discovery = client.get("/v1/meta/routes?tag=gochara").json()
    assert discovery["count"] == 5
    assert all(r["family"] == "classical-vedic" for r in discovery["routes"])


def test_request_and_public_model_identity():
    import moira_server.models as public
    assert public.GocharaSnapshotRequest is GocharaSnapshotRequest
