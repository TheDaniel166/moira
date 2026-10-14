"""Release-regression tests for the Light Box governance gate."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

import pytest


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


def _exact_artifacts(
    gate: Any, tmp_path: Path, source_revision: str
) -> tuple[Path, Path]:
    matrix = gate._load(gate.MATRIX_PATH)
    receipts = gate._load(gate.RECEIPTS_PATH)
    receipts["source_revision"] = source_revision
    receipts["working_tree_clean"] = True
    receipts["artifact_status"] = "exact_source_revision"
    for receipt in receipts["receipts"]:
        receipt["source_revision"] = source_revision
        receipt["working_tree_clean"] = True
        receipt["artifact_status"] = "exact_source_revision"
        receipt["status"] = "passed"
    receipts["summary"]["contracts_run"] = len(receipts["receipts"])
    receipts["summary"]["passed"] = len(receipts["receipts"])
    receipts["summary"]["failed"] = 0
    receipt_path = tmp_path / "receipts.json"
    receipt_path.write_text(json.dumps(receipts), encoding="utf-8")

    matrix["receipt_artifact_status"] = "exact_source_revision"
    matrix["receipt_source_revision"] = source_revision
    release = matrix["summary"]["evidence_classes"]["release"]
    covered = matrix["summary"]["surfaces_with_contracts"]
    release["passed_local"] = 0
    release["passed_exact_source"] = covered
    release["not_run"] = matrix["summary"]["canonical_surfaces"] - covered
    matrix_path = tmp_path / "matrix.json"
    matrix_path.write_text(json.dumps(matrix), encoding="utf-8")
    return matrix_path, receipt_path


def _patch_git(
    gate: Any,
    monkeypatch: pytest.MonkeyPatch,
    *,
    head: str,
    changed: frozenset[str],
    parents: tuple[str, ...] = (),
    committed: frozenset[str] = frozenset(),
    nested_errors: list[str] | None = None,
) -> None:
    monkeypatch.setattr(gate, "_git_head", lambda: head)
    monkeypatch.setattr(gate, "_worktree_paths", lambda: changed)
    monkeypatch.setattr(gate, "_git_parents", lambda revision: parents)
    monkeypatch.setattr(gate, "_commit_paths", lambda parent, revision: committed)
    monkeypatch.setattr(gate, "_gitlink_revision", lambda revision: f"wiki-{revision}")
    monkeypatch.setattr(
        gate, "_nested_wiki_errors", lambda old, new: nested_errors or []
    )


def test_exact_release_gate_refuses_local_unreleased_receipts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = _module()
    source = "1" * 40
    matrix_path, receipt_path = _exact_artifacts(gate, tmp_path, source)
    receipts = gate._load(receipt_path)
    receipts["artifact_status"] = "local_unreleased_worktree"
    receipt_path.write_text(json.dumps(receipts), encoding="utf-8")
    _patch_git(gate, monkeypatch, head=source, changed=gate.EVIDENCE_PATHS)
    errors = gate.evaluate(
        exact_release=True,
        matrix_path=matrix_path,
        receipts_path=receipt_path,
    )
    assert any(
        "receipt set is not bound to a clean exact source revision" in error
        for error in errors
    )


def test_exact_release_gate_accepts_pre_attestation_evidence_only_worktree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = _module()
    source = "1" * 40
    matrix_path, receipt_path = _exact_artifacts(gate, tmp_path, source)
    _patch_git(gate, monkeypatch, head=source, changed=gate.EVIDENCE_PATHS)
    assert (
        gate.evaluate(
            exact_release=True,
            matrix_path=matrix_path,
            receipts_path=receipt_path,
        )
        == []
    )


def test_exact_release_gate_accepts_clean_attestation_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = _module()
    source = "1" * 40
    attestation = "2" * 40
    matrix_path, receipt_path = _exact_artifacts(gate, tmp_path, source)
    _patch_git(
        gate,
        monkeypatch,
        head=attestation,
        changed=frozenset(),
        parents=(source,),
        committed=gate.ATTESTATION_PATHS,
    )
    assert (
        gate.evaluate(
            exact_release=True,
            matrix_path=matrix_path,
            receipts_path=receipt_path,
        )
        == []
    )


@pytest.mark.parametrize(
    "variant",
    ["missing", "extra"],
)
def test_exact_release_gate_rejects_missing_or_extra_pre_attestation_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    variant: str,
) -> None:
    gate = _module()
    source = "1" * 40
    matrix_path, receipt_path = _exact_artifacts(gate, tmp_path, source)
    changed = (
        frozenset()
        if variant == "missing"
        else gate.EVIDENCE_PATHS | {"src/moira/example.py"}
    )
    _patch_git(gate, monkeypatch, head=source, changed=changed)
    errors = gate.evaluate(
        exact_release=True,
        matrix_path=matrix_path,
        receipts_path=receipt_path,
    )
    assert any(
        "must contain exactly the five generated evidence files" in error
        for error in errors
    )


def test_exact_release_gate_rejects_merge_or_wrong_parent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = _module()
    source = "1" * 40
    attestation = "2" * 40
    matrix_path, receipt_path = _exact_artifacts(gate, tmp_path, source)
    _patch_git(
        gate,
        monkeypatch,
        head=attestation,
        changed=frozenset(),
        parents=("3" * 40, "4" * 40),
    )
    errors = gate.evaluate(
        exact_release=True,
        matrix_path=matrix_path,
        receipts_path=receipt_path,
    )
    assert any("exactly one parent" in error for error in errors)

    _patch_git(
        gate,
        monkeypatch,
        head=attestation,
        changed=frozenset(),
        parents=("3" * 40,),
    )
    errors = gate.evaluate(
        exact_release=True,
        matrix_path=matrix_path,
        receipts_path=receipt_path,
    )
    assert any("not the sole parent" in error for error in errors)


def test_exact_release_gate_rejects_dirty_or_overbroad_attestation_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = _module()
    source = "1" * 40
    attestation = "2" * 40
    matrix_path, receipt_path = _exact_artifacts(gate, tmp_path, source)
    _patch_git(
        gate,
        monkeypatch,
        head=attestation,
        changed=frozenset({"README.md"}),
        parents=(source,),
        committed=gate.ATTESTATION_PATHS | {"README.md"},
    )
    errors = gate.evaluate(
        exact_release=True,
        matrix_path=matrix_path,
        receipts_path=receipt_path,
    )
    assert any("post-attestation worktree is not clean" in error for error in errors)
    assert any("exactly the approved evidence paths" in error for error in errors)


def test_exact_release_gate_propagates_nested_wiki_attestation_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = _module()
    source = "1" * 40
    attestation = "2" * 40
    matrix_path, receipt_path = _exact_artifacts(gate, tmp_path, source)
    _patch_git(
        gate,
        monkeypatch,
        head=attestation,
        changed=frozenset(),
        parents=(source,),
        committed=gate.ATTESTATION_PATHS,
        nested_errors=["exact release: nested wiki contains an extra file"],
    )
    errors = gate.evaluate(
        exact_release=True,
        matrix_path=matrix_path,
        receipts_path=receipt_path,
    )
    assert "exact release: nested wiki contains an extra file" in errors
