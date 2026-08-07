"""Fail-closed linkage canaries for Phase 9 evidence exemplars."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from evidence.contracts import (
    CONTRACTS,
    HOUSE_ROUND_TRIP_COMPARISON,
    NUTATION_DEPS_PARITY_COMPARISON,
    NUTATION_DPSI_PARITY_COMPARISON,
)
from moira import moira_native
from moira._native_build_provenance import native_build_input_manifest
from _pytest_plugins.evidence_schema import canonical_python_ast_sha256


pytestmark = pytest.mark.parallel(reason="read_only")


_ROOT = Path(__file__).resolve().parents[2]


def _function(tree: ast.Module, name: str) -> ast.FunctionDef:
    matches = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == name
    ]
    assert len(matches) == 1
    return matches[0]


def test_exported_exemplar_comparisons_are_the_registry_objects() -> None:
    house = CONTRACTS["MOIRA-HOUSE-EQUATORIAL-ECLIPTIC-ROUNDTRIP-V1"]
    native = CONTRACTS["MOIRA-NUTATION-2000A-PY-NATIVE-PARITY-V1"]

    assert HOUSE_ROUND_TRIP_COMPARISON is house.comparisons[0]
    assert NUTATION_DPSI_PARITY_COMPARISON is native.comparisons[0]
    assert NUTATION_DEPS_PARITY_COMPARISON is native.comparisons[1]


def test_loaded_native_backend_is_built_from_current_checkout_inputs() -> None:
    manifest = native_build_input_manifest(_ROOT)
    assert moira_native._build_input_manifest_sha256() == manifest["sha256"]


def test_every_exemplar_binds_its_scoped_executable_protocol() -> None:
    for contract in CONTRACTS.values():
        expected_test_paths = {
            nodeid.split("::", 1)[0] for nodeid in contract.nodeids
        }
        fixture_sources = {
            source.locator: source
            for source in contract.fixtures.sources
            if source.local
        }
        assert expected_test_paths <= set(fixture_sources)
        for path_text in expected_test_paths:
            path = _ROOT / path_text
            source = fixture_sources[path_text]
            assert source.hash_mode == "python_ast_v1"
            assert canonical_python_ast_sha256(path, source.symbols) == (
                source.sha256
            )


def test_house_exemplar_binds_its_shared_numeric_assertion_closure() -> None:
    contract = CONTRACTS["MOIRA-HOUSE-EQUATORIAL-ECLIPTIC-ROUNDTRIP-V1"]
    matches = [
        source
        for source in contract.fixtures.sources
        if source.locator == "tests/support/numeric_assertions.py"
    ]
    assert len(matches) == 1
    source = matches[0]
    assert source.hash_mode == "python_ast_v1"
    assert source.symbols == (
        "assert_canonical_longitude_degrees",
        "assert_circular_degrees",
    )
    assert canonical_python_ast_sha256(
        _ROOT / source.locator,
        source.symbols,
    ) == source.sha256


def test_house_exemplar_builds_its_tolerance_from_the_contract() -> None:
    tree = ast.parse(
        (_ROOT / "tests/unit/test_house_projection_geometry.py").read_text(
            encoding="utf-8"
        )
    )
    assignments = [
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name)
            and target.id == "_EQUATORIAL_ECLIPTIC_ROUND_TRIP"
            for target in node.targets
        )
    ]
    assert len(assignments) == 1
    constructor = assignments[0].value
    assert isinstance(constructor, ast.Call)
    keywords = {keyword.arg: keyword.value for keyword in constructor.keywords}
    assert ast.unparse(keywords["absolute"]) == (
        "HOUSE_ROUND_TRIP_COMPARISON.absolute"
    )
    assert ast.unparse(keywords["basis"]) == "HOUSE_ROUND_TRIP_COMPARISON.basis"

    admitted = _function(tree, "test_equatorial_ecliptic_round_trip")
    circular_calls = [
        node
        for node in ast.walk(admitted)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "assert_circular_degrees"
    ]
    assert len(circular_calls) == 1
    call_keywords = {
        keyword.arg: keyword.value for keyword in circular_calls[0].keywords
    }
    assert ast.unparse(call_keywords["tolerance"]) == (
        "_EQUATORIAL_ECLIPTIC_ROUND_TRIP"
    )


def test_native_exemplar_uses_each_contract_comparison_directly() -> None:
    tree = ast.parse(
        (_ROOT / "tests/unit/test_native_nutation_2000a.py").read_text(
            encoding="utf-8"
        )
    )
    admitted = _function(
        tree,
        "test_native_nutation_2000a_matches_scalar_reference",
    )
    residual_bounds = {
        ast.unparse(node)
        for node in ast.walk(admitted)
        if isinstance(node, ast.Compare)
        and len(node.ops) == 1
        and isinstance(node.ops[0], ast.LtE)
    }
    assert residual_bounds == {
        "dpsi_residual <= NUTATION_DPSI_PARITY_COMPARISON.absolute",
        "deps_residual <= NUTATION_DEPS_PARITY_COMPARISON.absolute",
    }
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "pytest"
        and node.func.attr == "approx"
        for node in ast.walk(admitted)
    )
