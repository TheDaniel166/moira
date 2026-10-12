"""Tests for the bounded Light Box product-usage scanner."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).parents[2]
SCRIPT = REPO_ROOT / "scripts" / "audit_lightbox_product_usage.py"


def _module():
    spec = importlib.util.spec_from_file_location(
        "audit_lightbox_product_usage", SCRIPT
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_scanner_finds_exact_route_and_explicit_facade_import(
    tmp_path, monkeypatch
) -> None:
    scanner = _module()
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "consumer.ts").write_text(
        'const route = "/v1/chart/reduction";\n',
        encoding="utf-8",
    )
    (tmp_path / "worker.py").write_text(
        "from moira import acg_from_chart\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(scanner, "_git_revision", lambda _root: "a" * 40)
    inventory = scanner._load_inventory()
    snapshot = scanner.build_snapshot(
        inventory,
        [("fixture", tmp_path)],
        audit_date="2026-10-12",
    )
    ids = {row["surface_id"] for row in snapshot["entries"]}
    assert "rest:POST:/v1/chart/reduction" in ids
    assert "python:moira.facade:acg_from_chart" in ids
    assert "rest:POST:/v1/chart" not in ids
    assert scanner.validate_snapshot(snapshot, inventory) == []


def test_scanner_excludes_tests_docs_and_generated_workspace(
    tmp_path, monkeypatch
) -> None:
    scanner = _module()
    for relative in (
        Path("tests/test_route.py"),
        Path("docs/example.ts"),
        Path("client/src/workspace/generated.ts"),
    ):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('const route = "/v1/chart/reduction";\n', encoding="utf-8")
    monkeypatch.setattr(scanner, "_git_revision", lambda _root: "b" * 40)
    inventory = scanner._load_inventory()
    snapshot = scanner.build_snapshot(
        inventory,
        [("fixture", tmp_path)],
        audit_date="2026-10-12",
    )
    assert snapshot["entries"] == []


def test_snapshot_requires_current_inventory_identity(tmp_path, monkeypatch) -> None:
    scanner = _module()
    monkeypatch.setattr(scanner, "_git_revision", lambda _root: "c" * 40)
    inventory = scanner._load_inventory()
    snapshot = scanner.build_snapshot(
        inventory,
        [("fixture", tmp_path)],
        audit_date="2026-10-12",
    )
    changed = dict(snapshot)
    changed["inventory_fingerprint_sha256"] = "0" * 64
    assert "inventory drift" in "\n".join(scanner.validate_snapshot(changed, inventory))
