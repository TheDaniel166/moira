"""Tests for the bounded Light Box product-usage scanner."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
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


def _git(root: Path, *arguments: str) -> str:
    process = subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return process.stdout.strip()


def _commit_fixture(root: Path) -> str:
    _git(root, "init", "--quiet")
    _git(root, "config", "user.name", "Light Box Test")
    _git(root, "config", "user.email", "lightbox-test@example.invalid")
    _git(root, "add", "--all")
    _git(root, "commit", "--quiet", "--allow-empty", "-m", "fixture")
    return _git(root, "rev-parse", "HEAD")


def test_scanner_finds_exact_route_and_explicit_facade_import(
    tmp_path,
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
    revision = _commit_fixture(tmp_path)
    # A revision-bound scan must ignore both dirty tracked content and untracked files.
    (tmp_path / "src" / "consumer.ts").write_text(
        'const route = "/v1/chart";\n',
        encoding="utf-8",
    )
    (tmp_path / "src" / "untracked.ts").write_text(
        'const route = "/v1/aspects/from-longitudes";\n',
        encoding="utf-8",
    )
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
    assert "rest:POST:/v1/aspects/from-longitudes" not in ids
    assert snapshot["roots"][0]["source_revision"] == revision
    assert scanner.validate_snapshot(snapshot, inventory) == []


def test_scanner_excludes_tests_docs_and_generated_workspace(
    tmp_path,
) -> None:
    scanner = _module()
    for relative in (
        Path("tests/test_route.py"),
        Path("docs/example.ts"),
        Path("design/archive/example.tsx"),
        Path("dist_package/example.js"),
        Path(".worktrees/old/src/example.ts"),
        Path("client/src/workspace/generated.ts"),
        Path("src/Changelog.tsx"),
    ):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('const route = "/v1/chart/reduction";\n', encoding="utf-8")
    (tmp_path / "src" / "app.ts").write_text(
        "export const app = true;\n",
        encoding="utf-8",
    )
    _commit_fixture(tmp_path)
    inventory = scanner._load_inventory()
    snapshot = scanner.build_snapshot(
        inventory,
        [("fixture", tmp_path)],
        audit_date="2026-10-12",
    )
    assert snapshot["entries"] == []
    assert snapshot["roots"][0]["files_scanned"] == 1


def test_snapshot_requires_current_inventory_identity(tmp_path) -> None:
    scanner = _module()
    _commit_fixture(tmp_path)
    inventory = scanner._load_inventory()
    snapshot = scanner.build_snapshot(
        inventory,
        [("fixture", tmp_path)],
        audit_date="2026-10-12",
    )
    changed = dict(snapshot)
    changed["inventory_fingerprint_sha256"] = "0" * 64
    assert "inventory drift" in "\n".join(scanner.validate_snapshot(changed, inventory))
