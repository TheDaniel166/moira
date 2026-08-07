"""Fail-closed policy tests for the reviewed assurance matrix."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from evidence.contracts import CONTRACTS
from evidence.receipts import (
    AssuranceReceiptError,
    _coverage_context,
    _is_regression_only_protected_target,
    load_assurance_requirements,
    validate_requirements_against_contracts,
)


pytestmark = pytest.mark.parallel(reason="isolated_resources")


_ROOT = Path(__file__).resolve().parents[2]
_REQUIREMENTS = _ROOT / "tests" / "evidence" / "assurance_requirements.json"
_MATRIX = _ROOT / "tests" / "evidence" / "assurance_matrix.json"
_SCRIPT = _ROOT / "scripts" / "build_test_assurance_matrix.py"


def test_reviewed_requirements_are_independent_complete_and_percentage_free() -> None:
    requirements = load_assurance_requirements(_REQUIREMENTS)
    validate_requirements_against_contracts(requirements, CONTRACTS)

    assert requirements["policy"]["global_percentage_gate"] is None
    assert requirements["policy"]["coverage_is_scientific_gate"] is False
    assert requirements["policy"]["coverage_core"] == "ctrace"
    assert requirements["policy"]["admission_scope"] == (
        "phase9_and_phase10_reviewed_claims"
    )
    assert {
        cell["evidence_class"] for cell in requirements["cells"]
    } == {"authority", "invariant", "native_parity"}
    assert {cell["required_claim_id"] for cell in requirements["cells"]} == set(
        CONTRACTS
    )


def test_deleting_a_contract_cannot_delete_its_independent_requirement() -> None:
    requirements = load_assurance_requirements(_REQUIREMENTS)
    reduced = {
        claim_id: contract
        for claim_id, contract in CONTRACTS.items()
        if claim_id != "MOIRA-SPK-CONTENT-IDENTITY-V1"
    }
    with pytest.raises(AssuranceReceiptError, match="required.*missing"):
        validate_requirements_against_contracts(requirements, reduced)


def test_requirement_cannot_silently_change_class_or_target() -> None:
    requirements = load_assurance_requirements(_REQUIREMENTS)
    mutations = []

    wrong_class = deepcopy(requirements)
    wrong_class["cells"][0]["evidence_class"] = "regression"
    mutations.append(wrong_class)

    wrong_target = deepcopy(requirements)
    wrong_target["cells"][0]["targets"][0]["qualname"] = "forged_target"
    mutations.append(wrong_target)

    wrong_digest = deepcopy(requirements)
    wrong_digest["cells"][0]["expected_contract_sha256"] = "0" * 64
    mutations.append(wrong_digest)

    for mutation in mutations:
        with pytest.raises(AssuranceReceiptError):
            validate_requirements_against_contracts(mutation, CONTRACTS)


def test_context_parser_uses_the_final_separator_and_rejects_foreign_phases() -> None:
    assert _coverage_context(
        "tests/unit/test_probe.py::test_probe[value|with|pipes]|run"
    ) == (
        "tests/unit/test_probe.py::test_probe[value|with|pipes]",
        "run",
    )
    assert _coverage_context("tests/unit/test_probe.py::test_probe|call") is None
    assert _coverage_context("foreign") is None
    assert _coverage_context("|run") is None


def test_exact_reviewed_case_manifest_is_sorted_unique_and_complete() -> None:
    requirements = load_assurance_requirements(_REQUIREMENTS)
    nodeids = [
        nodeid
        for cell in requirements["cells"]
        for binding in cell["expected_bindings"]
        for nodeid in binding["nodeids"]
    ]
    assert len(nodeids) == 38
    assert len(nodeids) == len(set(nodeids))
    for cell in requirements["cells"]:
        for binding in cell["expected_bindings"]:
            assert binding["nodeids"] == sorted(binding["nodeids"])


def test_regression_only_classification_is_explicitly_target_scoped() -> None:
    assert _is_regression_only_protected_target(
        protected=True,
        evidence_classes={"regression"},
    )
    assert not _is_regression_only_protected_target(
        protected=True,
        evidence_classes={"regression", "authority"},
    )
    assert not _is_regression_only_protected_target(
        protected=False,
        evidence_classes={"regression"},
    )


def test_generated_matrix_is_deterministic_and_check_mode_is_read_only() -> None:
    before = _MATRIX.read_bytes()
    completed = subprocess.run(
        [sys.executable, str(_SCRIPT), "--check-static"],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert "7 required cells" in completed.stdout
    assert _MATRIX.read_bytes() == before

    runtime_missing = subprocess.run(
        [sys.executable, str(_SCRIPT), "--check"],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert runtime_missing.returncode == 1
    assert "requires --receipt-dir and --coverage-file" in runtime_missing.stderr

    payload = json.loads(before)
    assert payload["summary"] == {
        "evidence_classes": ["authority", "invariant", "native_parity"],
        "global_percentage_gate": None,
        "required_cells": 7,
    }
    assert [cell["cell_id"] for cell in payload["cells"]] == sorted(
        cell["cell_id"] for cell in payload["cells"]
    )
