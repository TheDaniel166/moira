"""Source corpus transport, hostile requests and real application lifecycle."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from importlib import import_module
import json
from pathlib import Path

from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from moira import Moira, evaluate_yoga_extensions, list_yoga_extension_rules
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.yoga_extensions import YogaExtensionEvaluateRequest
from moira_server.models.yogas import YogaEvaluateRequest
from moira_server.services.yoga_extensions import (
    compute_yoga_extensions,
    serialize_yoga_extensions,
)
from moira_server.services.yogas import compute_yogas

pytestmark = pytest.mark.loopback
CORPUS = json.loads(
    (
        Path(__file__).parents[1] / "fixtures/yoga_extensions/source_cases.json"
    ).read_text()
)
PROFILES = [p.profile_id for p in list_yoga_extension_rules().profiles]
BASE = {
    "Sun": 10.0,
    "Moon": 45.0,
    "Mars": 20.0,
    "Mercury": 160.0,
    "Jupiter": 245.0,
    "Venus": 185.0,
    "Saturn": 280.0,
}
ROUTE = "/v1/yogas/extended/evaluate"


def body():
    return dict(
        sidereal_longitudes=BASE.copy(),
        lagna_sidereal_lon=5.0,
        profile_ids=PROFILES.copy(),
    )


@pytest.fixture(scope="module")
def client():
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("moira_server.app.create_engine", lambda config: object())
        with TestClient(create_app(ServerConfig(prewarm_enabled=False))) as value:
            yield value


@pytest.mark.parametrize("case", CORPUS["cases"], ids=lambda c: c["case_id"])
def test_source_corpus_all_public_paths_and_http(client, case):
    request = dict(
        sidereal_longitudes=case["longitudes"],
        lagna_sidereal_lon=case["lagna"],
        profile_ids=[case["profile_id"]],
    )
    expected = evaluate_yoga_extensions(
        case["longitudes"], case["lagna"], profile_ids=request["profile_ids"]
    )
    for module in ("moira.yoga_extensions", "moira", "moira.facade", "moira.vedic"):
        assert (
            getattr(import_module(module), "evaluate_yoga_extensions")(**request)
            == expected
        )
    assert Moira.yoga_extensions_from_longitudes(object(), **request) == expected
    service = compute_yoga_extensions(
        YogaExtensionEvaluateRequest(**request)
    ).model_dump(mode="json")
    response = client.post(ROUTE, json=request)
    assert response.status_code == 200, response.text
    assert (
        response.json()
        == service
        == serialize_yoga_extensions(expected).model_dump(mode="json")
    )
    row = next(r for r in service["results"] if r["rule"]["rule_id"] == case["rule_id"])
    assert row["formation_state"] == case["expected"]


def test_catalogue_filter_counts_and_policy(client):
    catalogue = client.get("/v1/yogas/extended/catalogue").json()
    assert len(catalogue["profiles"]) == 4 and len(catalogue["rules"]) == 22
    assert catalogue["rules"][-1]["admission"] == "research_required"
    full = client.post(ROUTE, json=body()).json()
    filtered = client.post(ROUTE, json=body() | {"include_absent": False}).json()
    assert full["evaluated_count"] == full["returned_count"] == 21
    assert full["evaluated_count"] == sum(
        full[k] for k in ("formed_count", "not_formed_count", "not_applicable_count")
    )
    assert filtered["results"] == [
        r for r in full["results"] if r["formation_state"] == "formed"
    ]
    assert filtered["returned_count"] == full["formed_count"]
    for key in (
        "evaluated_count",
        "formed_count",
        "not_formed_count",
        "not_applicable_count",
        "policy",
        "positions",
    ):
        assert full[key] == filtered[key]
    assert full["policy"]["profile_ids"] == PROFILES
    empty = client.post(
        ROUTE, json=body() | {"profile_ids": PROFILES[:2], "include_absent": False}
    ).json()
    assert (
        empty["results"] == []
        and empty["not_applicable_count"] == empty["evaluated_count"] == 2
    )


def rejected(client, request, route=ROUTE):
    response = client.post(
        route, content=json.dumps(request), headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422, response.text
    assert response.json()["error_code"] == "validation_error"


@pytest.mark.parametrize(
    "value", [True, False, "12", "NaN", float("nan"), float("inf"), -1, 360, None]
)
def test_bad_numeric_inputs_fail_before_dispatch(client, monkeypatch, value):
    def forbidden(*args, **kwargs):
        pytest.fail("invalid chart reached evaluator")

    monkeypatch.setattr(
        "moira_server.services.yoga_extensions.evaluate_yoga_extensions", forbidden
    )
    request = body()
    request["sidereal_longitudes"]["Sun"] = value
    rejected(client, request)
    rejected(client, body() | {"lagna_sidereal_lon": value})


@pytest.mark.parametrize(
    "profiles",
    [
        [],
        ["unknown"],
        [PROFILES[0]] * 2,
        PROFILES + [PROFILES[0]],
        PROFILES[0],
        [True],
        None,
    ],
)
def test_bad_selection(client, profiles):
    rejected(client, body() | {"profile_ids": profiles})


@pytest.mark.parametrize(
    "extra",
    [
        {"planet_speeds": {}},
        {"d9_signs": {}},
        {"strength": 1},
        {"profile": PROFILES[0]},
    ],
)
def test_unsupported_context_is_rejected(client, extra):
    rejected(client, body() | extra)


def test_missing_extra_keys_and_profiles(client):
    request = body()
    del request["sidereal_longitudes"]["Mars"]
    rejected(client, request)
    request = body()
    request["sidereal_longitudes"]["Rahu"] = 1
    rejected(client, request)
    request = body()
    del request["profile_ids"]
    rejected(client, request)


@pytest.mark.parametrize("value", [1, 0, "true", "false", None])
def test_strict_transport_and_legacy_policy_booleans(client, value):
    rejected(client, body() | {"include_absent": value})
    legacy = {k: v for k, v in body().items() if k != "profile_ids"}
    rejected(client, legacy | {"include_absent": value}, "/v1/yogas/evaluate")
    rejected(
        client,
        legacy | {"policy": {"budhaditya_combustion_cancel": value}},
        "/v1/yogas/evaluate",
    )


def test_legacy_unknown_motion_survives_filter_and_policy_is_reported(client):
    request = dict(
        sidereal_longitudes=BASE | {"Mercury": 333.0, "Jupiter": 35.0, "Moon": 5.0},
        lagna_sidereal_lon=5.0,
    )
    full = client.post(
        "/v1/yogas/evaluate", json=request | {"include_absent": True}
    ).json()
    filtered = client.post("/v1/yogas/evaluate", json=request).json()
    unknown = [y for y in full["yogas"] if y["formation_state"] == "indeterminate"]
    assert unknown and all(y in filtered["yogas"] for y in unknown)
    assert any(
        c["evaluation_state"] == "not_evaluated"
        for y in unknown
        for c in y["conditions"]
    )
    assert (
        full["policy"] == filtered["policy"]
        and full["policy"]["budhaditya_combustion_cancel"] is False
    )
    known = client.post(
        "/v1/yogas/evaluate",
        json=request | {"planet_speeds": {"Mercury": 0.1}, "include_absent": True},
    ).json()
    assert all(
        y["formation_state"] != "indeterminate"
        for y in known["yogas"]
        if y["name"] in {u["name"] for u in unknown}
    )


def test_constructed_requests_and_inconsistent_proofs_rejected():
    bad = YogaExtensionEvaluateRequest.model_construct(
        **(body() | {"include_absent": "false"})
    )
    with pytest.warns(UserWarning), pytest.raises(ValidationError):
        compute_yoga_extensions(bad)
    bad = YogaEvaluateRequest.model_construct(
        sidereal_longitudes=BASE, lagna_sidereal_lon=5.0, include_absent=1
    )
    with pytest.warns(UserWarning), pytest.raises(ValidationError):
        compute_yogas(bad)
    result = evaluate_yoga_extensions(BASE, 5.0, profile_ids=PROFILES)
    with pytest.raises(ValueError):
        serialize_yoga_extensions(result, include_absent=1)
    with pytest.raises(ValueError):
        replace(result, results=result.results[:-1])
    # A frozen vessel bypass is rejected again at the service boundary.
    object.__setattr__(result.results[2].branches[0].clauses[0], "state", "forged")
    with pytest.raises(ValueError):
        serialize_yoga_extensions(result)


def test_openapi_and_model_curation(client):
    schema = client.get("/openapi.json").json()
    model = schema["components"]["schemas"]["YogaExtensionEvaluateRequest"]
    assert model["additionalProperties"] is False
    assert set(model["required"]) == {
        "sidereal_longitudes",
        "lagna_sidereal_lon",
        "profile_ids",
    }
    profiles = model["properties"]["profile_ids"]
    assert (
        profiles["minItems"] == 1
        and profiles["maxItems"] == 4
        and profiles["items"]["enum"] == PROFILES
    )
    angle = model["properties"]["lagna_sidereal_lon"]
    assert angle["minimum"] == 0 and angle["exclusiveMaximum"] == 360
    response = schema["paths"][ROUTE]["post"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]
    assert response["$ref"].endswith("/YogaExtensionChartResponse")
    owner = import_module("moira_server.models.yoga_extensions")
    aggregate = import_module("moira_server.models")
    assert all(
        n in aggregate.__all__ and getattr(aggregate, n) is getattr(owner, n)
        for n in owner.__all__
    )


def test_concurrent_selection_is_call_local(client):
    requests = [body() | {"profile_ids": [p]} for p in PROFILES] * 3
    expected = [client.post(ROUTE, json=r).json() for r in requests]
    with ThreadPoolExecutor(max_workers=4) as pool:
        actual = list(pool.map(lambda r: client.post(ROUTE, json=r).json(), requests))
    assert actual == expected


def test_normal_application_lifecycle_without_engine_mock(monkeypatch):
    # The feature itself is resource-free; real startup uses the locally resolved
    # engine resource, without requiring a download on resource-free CI workers.
    from moira_server.lifecycle import create_engine

    # Restore the production factory while the module's fast-client fixture lives.
    monkeypatch.setattr("moira_server.app.create_engine", create_engine)
    with TestClient(create_app(ServerConfig(prewarm_enabled=False))) as client:
        assert isinstance(client.app.state.engine, Moira)
        assert client.get("/v1/yogas/extended/catalogue").status_code == 200
        response = client.post(ROUTE, json=body())
        assert response.status_code == 200 and response.json()["evaluated_count"] == 21
