"""Storage-only validation views must retain real release verification."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from moira import small_body_catalog_release as release
from scripts.prepare_small_body_validation_view import prepare_validation_view


def _source(tmp_path: Path) -> Path:
    source = tmp_path / "source"
    source.mkdir()
    (source / "one.bsp").write_bytes(b"kernel bytes")
    (source / "one.metadata.json").write_text(json.dumps({
        "shard": 0, "kernel": "one.bsp", "kernel_bytes": 12,
        "records": [{"number": 1, "naif_id": 2000001}], "failures": [],
    }), encoding="utf-8")
    (source / "manifest.json").write_text(json.dumps({
        "manifest_schema": release.MANIFEST_SCHEMA,
        "catalog_id": "moira-asteroids",
        "provenance": {"trajectory_source": "test only"},
        "body_count": 1,
        "shard_count": 1,
        "shards": [{"index": 0, "path": "one.bsp", "body_count": 1,
                    "bodies": [2000001]}],
    }), encoding="utf-8")
    return source


def _prepare(tmp_path: Path, version="2026.10.03.validation1"):
    source = _source(tmp_path)
    notice = tmp_path / "notice"
    notice.write_text("validation only", encoding="utf-8")
    output = tmp_path / "validation"
    result = prepare_validation_view(
        source, output, catalog_id="moira-asteroids", catalog_version=version,
        license_path=notice, notice_path=notice,
    )
    return source, output, result


def test_view_links_only_kernels_and_preserves_source(tmp_path):
    ordinary_copy = release._copy_and_hash
    source, output, result = _prepare(tmp_path)
    assert os.path.samefile(source / "one.bsp", output / "one.bsp")
    assert not os.path.samefile(
        source / "one.metadata.json", output / "one.metadata.json"
    )
    assert not (source / "SHA256SUMS").exists()
    assert "release" not in json.loads((source / "manifest.json").read_text())
    assert release.verify_release(output) == result
    assert release._copy_and_hash is ordinary_copy


def test_view_cannot_use_a_publishable_version(tmp_path):
    with pytest.raises(release.CatalogReleaseError, match=".validation"):
        _prepare(tmp_path, "2026.10.03.1")
    assert not (tmp_path / "validation").exists()


def test_shared_kernel_mutation_still_fails_the_real_verifier(tmp_path):
    source, output, _ = _prepare(tmp_path)
    (source / "one.bsp").write_bytes(b"changed data")
    with pytest.raises(release.CatalogReleaseError, match="mismatch"):
        release.verify_release(output)
