"""Structural failure witnesses for the reviewed capability bindings."""

import pytest

from scripts import check_rest_capability_map as checker


@pytest.fixture
def ledger():
    return {
        "direct_modules": [],
        "capabilities": [{
            "capability": "static_armc_fixture",
            "engine": ["moira.houses:houses_from_armc"],
            "witness": "tests/unit/test_rest_capability_map.py::test_schema_drift_is_detected",
            "routes": [{"operation": "POST /test", "request": ["armc"], "response": ["cusps"]}],
        }],
    }


def test_schema_drift_is_detected(ledger):
    operation = {
        "requestBody": {"schema": {"$ref": "#/components/schemas/Input"}},
        "responses": {"200": {"schema": {"properties": {"cusps": {}}}}},
    }
    schema = {
        "paths": {"/test": {"post": operation}},
        "components": {"schemas": {"Input": {"properties": {"armc": {}}}}},
    }
    checker.check_bindings(ledger, schema)
    schema["components"]["schemas"] = {}
    with pytest.raises(ValueError, match="unresolved schema link"):
        checker.check_bindings(ledger, schema)
    schema["paths"] = {}
    with pytest.raises(ValueError, match="missing POST /test"):
        checker.check_bindings(ledger, schema)


def test_a_new_unmapped_callable_changes_the_baseline(monkeypatch, ledger):
    baseline = {"moira.houses:houses_from_armc", "moira.houses:compare_systems"}
    monkeypatch.setattr(checker, "public_capabilities", lambda modules: baseline)
    before = checker.unmapped_capabilities(ledger)
    assert before == ["moira.houses:compare_systems"]
    baseline.add("moira.houses:new_callable")
    assert checker.capability_fingerprint(before) != checker.capability_fingerprint(checker.unmapped_capabilities(ledger))
