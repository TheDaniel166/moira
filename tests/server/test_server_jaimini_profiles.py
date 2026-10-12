"""Source fixtures through public Python, services, actual HTTP and OpenAPI."""

from dataclasses import asdict
import importlib
import json
from pathlib import Path

from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from moira import (
    Moira,
    JaiminiChart,
    ArgalaReference,
    assess_argala,
    evaluate_chara_profile,
)
from moira.jaimini_profile_policy import ARGALA_IDS, CHARA_IDS, list_jaimini_profiles
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.jaimini_profiles import (
    ArgalaAssessmentRequest,
    CharaProfileRequest,
)
from moira_server.services.jaimini_profiles import (
    compute_argala_assessment,
    compute_chara_profile,
    serialize_argala_assessment,
    serialize_chara_profile,
)

pytestmark = pytest.mark.loopback
ROOT = Path(__file__).parents[1] / "fixtures/jaimini_profiles"
CHARA = json.loads((ROOT / "chara_source_cases.json").read_text())
ARGALA = json.loads((ROOT / "argala_source_cases.json").read_text())
CROUTE = "/v1/jaimini/extended/chara-dasha/profile"
AROUTE = "/v1/jaimini/extended/argala/assessment"


@pytest.fixture(scope="module")
def client():
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("moira_server.app.create_engine", lambda config: object())
        with TestClient(create_app(ServerConfig(prewarm_enabled=False))) as c:
            yield c


def chara_request():
    return {"chart": CHARA["durations"][1]["chart"], "profile_id": CHARA_IDS[1]}


def argala_request(kind=0):
    return {
        "chart": ARGALA["pvr_exercise16"]["chart"],
        "profile_id": ARGALA_IDS[kind],
        "references": [{"kind": "house", "value": h} for h in range(1, 13)],
    }


def reject(client, route, payload):
    r = client.post(
        route, content=json.dumps(payload), headers={"Content-Type": "application/json"}
    )
    assert r.status_code == 422, r.text
    assert r.json()["error_code"] == "validation_error"


@pytest.mark.parametrize("case", CHARA["durations"], ids=lambda c: c["id"])
def test_chara_source_durations_all_surfaces(client, case):
    pid = dict(zip(("method1", "male", "female"), CHARA_IDS))[case["recipe"]]
    request = {"chart": case["chart"], "profile_id": pid}
    chart = JaiminiChart(**case["chart"])
    expected = evaluate_chara_profile(chart, profile_id=pid)
    for surface in ("moira", "moira.facade", "moira.vedic"):
        assert (
            getattr(importlib.import_module(surface), "evaluate_chara_profile")(
                chart, profile_id=pid
            )
            == expected
        )
    assert Moira.evaluate_chara_profile(object(), chart, profile_id=pid) == expected
    service = compute_chara_profile(CharaProfileRequest(**request)).model_dump(
        mode="json"
    )
    r = client.post(CROUTE, json=request)
    assert r.status_code == 200, r.text
    assert (
        r.json() == service == serialize_chara_profile(expected).model_dump(mode="json")
    )
    assert [
        [p["sign"], p["years"]] for p in r.json()["rows"][: len(case["expected"])]
    ] == case["expected"]


@pytest.mark.parametrize(
    "case", CHARA["sequences"], ids=lambda c: f"{c['branch']}-{c['lagna']}"
)
def test_all_printed_sequences_over_http(client, case):
    request = chara_request()
    request["chart"] = {**request["chart"], "lagna": case["lagna"]}
    request["profile_id"] = CHARA_IDS[1 if case["branch"] == "male" else 2]
    r = client.post(CROUTE, json=request)
    assert r.status_code == 200, r.text
    assert [p["sign"] for p in r.json()["rows"]] == case["expected_signs"]


@pytest.mark.parametrize(
    "kind,case",
    [(0, "bphs_corrected_chart"), (1, "pvr_exercise16"), (2, "rath_standard_nativity")],
)
def test_argala_source_witnesses_all_surfaces(client, kind, case):
    request = {**argala_request(kind), "chart": ARGALA[case]["chart"]}
    chart = JaiminiChart(**request["chart"])
    refs = tuple(ArgalaReference(**r) for r in request["references"])
    expected = assess_argala(chart, profile_id=ARGALA_IDS[kind], references=refs)
    for surface in ("moira", "moira.facade", "moira.vedic"):
        assert (
            getattr(importlib.import_module(surface), "assess_argala")(
                chart, profile_id=ARGALA_IDS[kind], references=refs
            )
            == expected
        )
    assert (
        Moira.assess_argala(
            object(), chart, profile_id=ARGALA_IDS[kind], references=refs
        )
        == expected
    )
    service = compute_argala_assessment(ArgalaAssessmentRequest(**request)).model_dump(
        mode="json"
    )
    r = client.post(AROUTE, json=request)
    assert r.status_code == 200, r.text
    assert (
        r.json()
        == service
        == serialize_argala_assessment(expected).model_dump(mode="json")
    )
    if kind == 1:
        for row, source in zip(r.json()["references"], ARGALA[case]["expected"]):
            positions = {}
            for p in row["pairs"]:
                positions[p["causer_house"]] = p["causers"]
                positions[p["blocker_house"]] = p["blockers"]
            assert [positions[h] for h in ARGALA[case]["positions"]] == source


def test_zero_projection_and_boundary_metadata_over_http(client):
    request = chara_request()
    request["profile_id"] = CHARA_IDS[0]
    request["chart"] = {
        "basis": "signs",
        "positions": {p: 0 for p in request["chart"]["positions"]} | {"Jupiter": 9},
        "lagna": 8,
    }
    request["projection"] = {
        "epoch_jd": 2451545.0,
        "projection_id": "moira_fixed_365_25_day_projection_v1",
    }
    r = client.post(CROUTE, json=request)
    assert r.status_code == 200, r.text
    result = r.json()
    assert len(result["rows"]) == 12 and result["rows"][0]["years"] == 0
    assert 0 in result["schedule"]["not_scheduled_zero_duration"]
    assert all(p["row_ordinal"] != 0 for p in result["schedule"]["intervals"])
    assert result["schedule"]["projection"] == request["projection"]
    request["projection"]["epoch_jd"] = 1e300
    reject(client, CROUTE, request)


def test_quarter_and_uncertainty_evidence_survive_http(client):
    request = argala_request()
    request["chart"] = {
        "basis": "sidereal_longitudes",
        "positions": {p: 1.0 for p in request["chart"]["positions"]}
        | {"Venus": 31.0, "Mercury": 39.0, "Sun": 355.0, "Saturn": 355.0},
        "lagna": 0.0,
    }
    request["references"] = [{"kind": "lagna"}]
    r = client.post(AROUTE, json=request)
    assert r.status_code == 200, r.text
    pair = r.json()["references"][0]["pairs"][0]
    assert pair["reason_codes"] == ["multioccupant_quarter_composition_unestablished"]
    assert (
        len(pair["quarter_pairs"]) == 4
        and pair["causer_count"] == pair["blocker_count"] == 2
    )
    assert all(isinstance(p["qualifies"], bool) for p in pair["quarter_pairs"])


@pytest.mark.parametrize(
    "value", [True, False, "1", None, float("nan"), float("inf"), -1, 12, 1.2]
)
@pytest.mark.parametrize("route", [CROUTE, AROUTE])
def test_invalid_sign_numbers_never_reach_engine(client, monkeypatch, value, route):
    def forbidden(*a, **kw):
        pytest.fail("invalid request reached evaluator")

    monkeypatch.setattr(
        "moira_server.services.jaimini_profiles.evaluate_chara_profile", forbidden
    )
    monkeypatch.setattr(
        "moira_server.services.jaimini_profiles.assess_argala", forbidden
    )
    request = json.loads(
        json.dumps(chara_request() if route == CROUTE else argala_request())
    )
    request["chart"]["positions"]["Sun"] = value
    reject(client, route, request)


@pytest.mark.parametrize("value", [True, "1", float("nan"), float("inf"), 360, -1])
def test_invalid_canonical_degrees(client, value):
    request = argala_request()
    request["chart"] = {
        "basis": "sidereal_longitudes",
        "positions": {p: 0.0 for p in request["chart"]["positions"]},
        "lagna": value,
    }
    reject(client, AROUTE, request)


@pytest.mark.parametrize(
    "extra",
    [
        {"cycles": 2},
        {"antardashas": True},
        {"node_longitudes": {}},
        {"strength": 3},
        {"include_absent": False},
    ],
)
def test_unsupported_switches(client, extra):
    reject(client, CROUTE, chara_request() | extra)
    reject(client, AROUTE, argala_request() | extra)


@pytest.mark.parametrize(
    "refs",
    [
        [],
        [{"kind": "lagna"}] * 2,
        [{"kind": "house", "value": True}],
        [{"kind": "house", "value": 1.0}],
        [{"kind": "planet", "value": "Pluto"}],
        [{"kind": "sign", "value": 0}],
        [{"kind": "lagna", "value": 1}],
        [{"kind": "lagna"}] * 23,
    ],
)
def test_bad_references(client, refs):
    reject(client, AROUTE, argala_request() | {"references": refs})


def test_missing_nodes_extra_fields_and_discovery_only_profiles(client):
    for body in ("Rahu", "Ketu", "Mars"):
        request = json.loads(json.dumps(argala_request()))
        del request["chart"]["positions"][body]
        reject(client, AROUTE, request)
    request = json.loads(json.dumps(chara_request()))
    request["chart"]["positions"]["Rahu"] = 0
    reject(client, CROUTE, request)
    for p in list_jaimini_profiles().profiles:
        if p.admission != "admitted_bounded":
            reject(client, CROUTE, chara_request() | {"profile_id": p.profile_id})
            reject(client, AROUTE, argala_request() | {"profile_id": p.profile_id})


def test_forged_service_models_revalidated():
    original = ArgalaAssessmentRequest(**argala_request())
    a = ArgalaAssessmentRequest.model_construct(
        chart=original.chart, profile_id="unknown", references=original.references
    )
    a.profile_id = "unknown"
    with pytest.raises(ValidationError):
        compute_argala_assessment(a)
    c = CharaProfileRequest(**chara_request())
    c.chart.lagna = True
    with pytest.raises(ValidationError):
        compute_chara_profile(c)


def test_catalogue_openapi_and_legacy_receipt(client):
    result = client.get("/v1/jaimini/extended/profiles")
    assert result.status_code == 200, result.text
    assert result.json() == json.loads(json.dumps(asdict(list_jaimini_profiles())))
    schema = client.get("/openapi.json").json()
    components = schema["components"]["schemas"]
    assert (
        components["CharaProfileRequest"]["properties"]["chart"]["discriminator"][
            "propertyName"
        ]
        == "basis"
    )
    assert (
        components["ArgalaAssessmentRequest"]["properties"]["references"]["maxItems"]
        == 22
    )
    assert (
        components["ArgalaSignChart"]["properties"]["positions"]["minProperties"] == 9
    )
    assert set(
        components["CharaProfileRequest"]["properties"]["profile_id"]["enum"]
    ) == set(CHARA_IDS)
    assert components["CharaProfileRequest"]["additionalProperties"] is False
    assert components["PairAssessmentResponse"]["properties"]["reason_codes"]["items"][
        "enum"
    ]
    legacy = {
        "sidereal_longitudes": {p: 0.0 for p in chara_request()["chart"]["positions"]},
        "lagna_sidereal_lon": 0.0,
        "node_longitudes": {"Ketu": 195.0},
    }
    response = client.post("/v1/jaimini/extended/argala", json=legacy)
    assert response.status_code == 200, response.text
    assert response.json()["computation"]["profile_id"] == "moira_argala_existing_v1"
    for nodes in ({}, {"Rahu": 15.0}, {"Ketu": 195.0}):
        assert (
            client.post(
                "/v1/jaimini/extended/argala", json=legacy | {"node_longitudes": nodes}
            ).status_code
            == 200
        )


def test_real_application_lifecycle(monkeypatch):
    # Unpatched initialization: distinguish app resource discovery from evaluator IO.
    from moira_server.lifecycle import create_engine

    monkeypatch.setattr("moira_server.app.create_engine", create_engine)
    with TestClient(create_app(ServerConfig(prewarm_enabled=False))) as client:
        assert isinstance(client.app.state.engine, Moira)
        assert client.get("/v1/jaimini/extended/profiles").status_code == 200
        r = client.post(CROUTE, json=chara_request())
        assert r.status_code == 200, r.text
        r = client.post(AROUTE, json=argala_request())
        assert r.status_code == 200, r.text


def test_corrupt_result_is_an_internal_failure():
    chart = JaiminiChart(**chara_request()["chart"])
    result = evaluate_chara_profile(chart, profile_id=CHARA_IDS[1])
    object.__setattr__(result, "catalogue_version", "forged")
    with pytest.raises(RuntimeError, match="invariant"):
        serialize_chara_profile(result)
    request = argala_request()
    result = assess_argala(
        JaiminiChart(**request["chart"]),
        profile_id=ARGALA_IDS[0],
        references=(ArgalaReference("lagna"),),
    )
    object.__setattr__(result, "character_component", "made_up")
    with pytest.raises(RuntimeError, match="invariant"):
        serialize_argala_assessment(result)


@pytest.mark.parametrize("is_chara", [True, False])
@pytest.mark.parametrize("defect", ["wrong_result_type", "response_contract"])
def test_engine_transport_defects_are_http_500(client, monkeypatch, is_chara, defect):
    import moira_server.services.jaimini_profiles as services

    if defect == "wrong_result_type":
        monkeypatch.setattr(
            services,
            "evaluate_chara_profile" if is_chara else "assess_argala",
            lambda *args, **kwargs: object(),
        )
    else:

        def reject_engine_response(data):
            raise ValueError("simulated invalid engine response contract")

        monkeypatch.setattr(
            services.CharaProfileResponse
            if is_chara
            else services.ArgalaAssessmentResponse,
            "model_validate",
            reject_engine_response,
        )
    with TestClient(client.app, raise_server_exceptions=False) as http:
        response = http.post(
            CROUTE if is_chara else AROUTE,
            json=chara_request() if is_chara else argala_request(),
        )
    assert response.status_code == 500


@pytest.mark.parametrize("error_type", [ValueError, TypeError, KeyError])
@pytest.mark.parametrize("module,vessel,route", [
    ("moira.chara_profiles", "CharaArithmeticRow", CROUTE),
    ("moira.chara_profiles", "CharaArithmeticResult", CROUTE),
    ("moira.chara_profiles", "CharaProfileInterval", CROUTE),
    ("moira.chara_profiles", "CharaProfileSchedule", CROUTE),
    ("moira.argala_assessment", "ArgalaCharacter", AROUTE),
    ("moira.argala_assessment", "ArgalaPairAssessment", AROUTE),
    ("moira.argala_assessment", "ArgalaAssessmentResult", AROUTE),
])
def test_result_constructor_failures_are_http_500(
    client, monkeypatch, error_type, module, vessel, route,
):
    def broken_result(self):
        raise error_type("injected internal evidence failure")

    monkeypatch.setattr(getattr(importlib.import_module(module), vessel), "__post_init__", broken_result)
    request = chara_request() if route == CROUTE else argala_request()
    if route == CROUTE:
        request["projection"] = {
            "epoch_jd": 2451545.0,
            "projection_id": "moira_fixed_365_25_day_projection_v1",
        }
    with TestClient(client.app, raise_server_exceptions=False) as http:
        response = http.post(route, json=request)
    assert response.status_code == 500, response.text
    assert "injected" not in response.text


@pytest.mark.parametrize("defect", ["chara_direction", "chara_count", "argala_effect", "argala_degree"])
def test_contradictory_engine_evidence_never_serializes_over_http(client, monkeypatch, defect):
    import moira_server.services.jaimini_profiles as services

    is_chara = defect.startswith("chara")
    request = chara_request() if is_chara else argala_request()
    if is_chara:
        result = evaluate_chara_profile(JaiminiChart(**request["chart"]), profile_id=request["profile_id"])
        target, name, value = (
            (result, "sequence_direction", -result.sequence_direction)
            if defect == "chara_direction"
            else (result.rows[0], "inclusive_count", result.rows[0].inclusive_count % 12 + 1)
        )
        object.__setattr__(target, name, value)
    else:
        request["chart"] = {
            "basis": "sidereal_longitudes", "lagna": 0.0,
            "positions": dict.fromkeys(request["chart"]["positions"], 95.0)
            | {"Venus": 31.0, "Sun": 355.0, "Ketu": 215.0},
        }
        request["references"] = [{"kind": "lagna"}]
        result = assess_argala(
            JaiminiChart(**request["chart"]), profile_id=request["profile_id"],
            references=(ArgalaReference("lagna"),),
        )
        pair = result.references[0].pairs[0]
        if defect == "argala_effect":
            object.__setattr__(pair, "effect_state", "unobstructed")
            object.__setattr__(pair, "reason_codes", ())
            object.__setattr__(pair, "strength_comparison", "not_required")
        else:
            object.__setattr__(pair.quarter_pairs[0], "causer_degree", 4.0)
    monkeypatch.setattr(
        services, "evaluate_chara_profile" if is_chara else "assess_argala",
        lambda *args, **kwargs: result,
    )
    with TestClient(client.app, raise_server_exceptions=False) as http:
        response = http.post(CROUTE if is_chara else AROUTE, json=request)
    assert response.status_code == 500, response.text
