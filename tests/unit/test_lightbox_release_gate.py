"""Release-regression tests for the Light Box governance gate."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).parents[2]
SCRIPT = REPO_ROOT / "scripts" / "check_lightbox_release_gate.py"


def _module():
    spec = importlib.util.spec_from_file_location("check_lightbox_release_gate", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_source_gate_passes_current_reviewed_baseline() -> None:
    gate = _module()
    assert gate.evaluate() == []


def test_exact_release_gate_refuses_local_unreleased_receipts(tmp_path: Path) -> None:
    gate = _module()
    matrix = gate._load(gate.MATRIX_PATH)
    matrix["receipt_artifact_status"] = "local_unreleased_worktree"
    release = matrix["summary"]["evidence_classes"]["release"]
    release["passed_local"] = matrix["summary"]["surfaces_with_contracts"]
    release["passed_exact_source"] = 0
    matrix_path = tmp_path / "local-matrix.json"
    matrix_path.write_text(json.dumps(matrix), encoding="utf-8")
    errors = gate.evaluate(exact_release=True, matrix_path=matrix_path)
    assert any(
        "not bound to a clean exact source revision" in error for error in errors
    )
    assert any("no release evidence cell" in error for error in errors)


def test_exact_release_gate_accepts_matrix_for_current_clean_revision(
    tmp_path: Path,
) -> None:
    gate = _module()
    matrix = gate._load(gate.MATRIX_PATH)
    matrix["receipt_artifact_status"] = "exact_source_revision"
    matrix["receipt_source_revision"] = gate._git_head()
    release = matrix["summary"]["evidence_classes"]["release"]
    covered = matrix["summary"]["surfaces_with_contracts"]
    release["passed_local"] = 0
    release["passed_exact_source"] = covered
    release["not_run"] = matrix["summary"]["canonical_surfaces"] - covered
    matrix_path = tmp_path / "matrix.json"
    matrix_path.write_text(json.dumps(matrix), encoding="utf-8")
    assert gate.evaluate(exact_release=True, matrix_path=matrix_path) == []
