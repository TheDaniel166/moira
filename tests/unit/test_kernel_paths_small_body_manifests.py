from __future__ import annotations

import json
from pathlib import Path

import moira._kernel_paths as kernel_paths


def _write_manifest(path: Path, shard_paths: list[str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"shards": [{"path": shard_path} for shard_path in shard_paths]}),
        encoding="utf-8",
    )
    return path


def test_automatic_discovery_skips_metadata_only_manifest(
    monkeypatch,
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(
        tmp_path / "asteroids" / "manifest.json",
        ["asteroid_shard_000.bsp"],
    )
    monkeypatch.setattr(kernel_paths, "kernel_search_dirs", lambda: (tmp_path,))
    monkeypatch.delenv(kernel_paths.SOVEREIGN_SMALL_BODY_MANIFEST_ENV, raising=False)

    assert manifest.exists()
    assert kernel_paths.find_sovereign_small_body_manifest() is None
    assert kernel_paths.find_all_small_body_manifests() == []


def test_automatic_discovery_admits_installed_manifest(
    monkeypatch,
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(
        tmp_path / "asteroids" / "manifest.json",
        ["asteroid_shard_000.bsp"],
    )
    (manifest.parent / "asteroid_shard_000.bsp").touch()
    monkeypatch.setattr(kernel_paths, "kernel_search_dirs", lambda: (tmp_path,))
    monkeypatch.delenv(kernel_paths.SOVEREIGN_SMALL_BODY_MANIFEST_ENV, raising=False)

    assert kernel_paths.find_sovereign_small_body_manifest() == manifest
    assert kernel_paths.find_all_small_body_manifests() == [manifest]


def test_partial_installation_remains_discoverable_for_loader_validation(
    monkeypatch,
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(
        tmp_path / "asteroids" / "manifest.json",
        ["asteroid_shard_000.bsp", "asteroid_shard_001.bsp"],
    )
    (manifest.parent / "asteroid_shard_000.bsp").touch()
    monkeypatch.setattr(kernel_paths, "kernel_search_dirs", lambda: (tmp_path,))
    monkeypatch.delenv(kernel_paths.SOVEREIGN_SMALL_BODY_MANIFEST_ENV, raising=False)

    assert kernel_paths.find_all_small_body_manifests() == [manifest]


def test_explicit_metadata_only_manifest_remains_fail_visible(
    monkeypatch,
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(
        tmp_path / "configured" / "manifest.json",
        ["missing.bsp"],
    )
    monkeypatch.setattr(kernel_paths, "kernel_search_dirs", lambda: ())
    monkeypatch.setenv(
        kernel_paths.SOVEREIGN_SMALL_BODY_MANIFEST_ENV,
        str(manifest),
    )

    assert kernel_paths.find_sovereign_small_body_manifest() == manifest
    assert kernel_paths.find_all_small_body_manifests() == [manifest]
