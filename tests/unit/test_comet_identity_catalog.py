from __future__ import annotations

import hashlib
import json
import unicodedata
from pathlib import Path

import pytest

from moira.asteroids import ASTEROID_NAIF
from moira.comets import (
    COMET_NAIF,
    _CANONICAL_COMET_NAIF,
    _COMET_ALIASES,
    _load_identity_registry,
)
from moira.small_body_catalog_release import (
    IncludedReleaseFile,
    prepare_release,
)
from scripts.build_comet_identity_catalog import build_catalog


DATA_DIR = Path(__file__).resolve().parents[2] / "moira" / "data"
CATALOG_PATH = DATA_DIR / "comet_catalog_naif.json"
METADATA_PATH = DATA_DIR / "comet_catalog_naif.metadata.json"
ALIASES_PATH = DATA_DIR / "comet_catalog_aliases.json"

EXPECTED_CATALOG_SHA256 = (
    "77651edfa286678f487214902a7538c411c5fdfd00c26c7959e887b3ccd83a35"
)
EXPECTED_METADATA_SHA256 = (
    "fc71181f2694c64a13da688fe5c220f8b5c949d8cc8effe555ad9bf59dd39f7c"
)
EXPECTED_ALIASES_SHA256 = (
    "f613e2301d891b7baf6ad734bdfa6cb29dcc2d0e9f76ddb7e9651bace828fa9b"
)
EXPECTED_RELEASE_MANIFEST_SHA256 = (
    "31fbbedbb3ea7ba276fa9d49d52211ae41d90f76c74fb49ec0a6bafb014f07a1"
)
EXPECTED_MASTER_SHA256 = (
    "78dc12291bf8b3e1a7eab844666632ccffd98b3f362c2d2a1442e9a8714d33f6"
)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _make_release(
    tmp_path: Path,
    *,
    alias_target: str = "1P/Halley",
) -> Path:
    source = tmp_path / "source"
    source.mkdir()
    kernel_name = "comet_shard_000.bsp"
    kernel_bytes = b"comet-kernel"
    (source / kernel_name).write_bytes(kernel_bytes)
    records = [
        {
            "number": 1,
            "naif_id": 1_000_001,
            "name": "1P/Halley",
            "full_name": "1P/Halley",
        },
        {
            "number": 2,
            "naif_id": 1_000_002,
            "name": "2P/Encke",
            "full_name": "2P/Encke",
        },
    ]
    _write_json(
        source / "comet_shard_000.metadata.json",
        {
            "shard": 0,
            "kernel": kernel_name,
            "kernel_bytes": len(kernel_bytes),
            "records": records,
            "failures": [],
        },
    )
    _write_json(
        source / "manifest.json",
        {
            "manifest_schema": "moira.small-body-catalog/v1",
            "catalog_id": "moira-comets",
            "source": "test numbered comet catalog",
            "provenance": {
                "trajectory_source": "JPL Horizons VECTORS",
                "horizons_api": "https://ssd.jpl.nasa.gov/api/horizons.api",
                "query_policy": {
                    "command_template": "DES={number}P;NOFRAG;CAP",
                },
            },
            "body_count": 2,
            "shard_count": 1,
            "shards": [
                {
                    "index": 0,
                    "path": kernel_name,
                    "body_count": 2,
                    "bodies": [1_000_001, 1_000_002],
                }
            ],
        },
    )
    _write_json(
        source / "comet_master.json",
        {
            "requested": 2,
            "built": 2,
            "failed": 0,
            "records": records,
            "naif_map": {
                "1P/Halley": 1_000_001,
                "2P/Encke": 1_000_002,
            },
        },
    )
    aliases_path = tmp_path / "comet_catalog_aliases.json"
    _write_json(
        aliases_path,
        {
            "schema_version": 1,
            "catalog_id": "moira-comets",
            "aliases": [
                {
                    "alias": "Halley",
                    "alias_kind": "legacy_short_name",
                    "canonical_name": alias_target,
                }
            ],
            "policy": {
                "global_namespace": (
                    "aliases are comet-family scoped and make no cross-family "
                    "uniqueness claim"
                )
            },
        },
    )
    license_path = tmp_path / "LICENSE"
    license_path.write_text("MIT License\n", encoding="utf-8")
    notice_path = tmp_path / "NOTICE.md"
    notice_path.write_text("Moira comet catalog notice.\n", encoding="utf-8")
    release = tmp_path / "release"
    prepare_release(
        source,
        release,
        catalog_id="moira-comets",
        catalog_version="test-release",
        license_path=license_path,
        notice_path=notice_path,
        support_files=("comet_master.json",),
        included_files=(
            IncludedReleaseFile(
                source_path=aliases_path,
                release_path="identity/comet_catalog_aliases.json",
                role="identity_alias_policy",
            ),
        ),
        released_utc="2026-07-28T12:00:00Z",
        source_revision="test-source-revision",
    )
    return release


def test_identity_builder_derives_canonical_names_and_bound_aliases(
    tmp_path: Path,
) -> None:
    release = _make_release(tmp_path)
    manifest_sha256 = hashlib.sha256(
        (release / "manifest.json").read_bytes()
    ).hexdigest()

    catalog_bytes, metadata_bytes = build_catalog(
        release,
        expected_manifest_sha256=manifest_sha256,
    )

    assert json.loads(catalog_bytes) == {
        "1P/Halley": 1_000_001,
        "2P/Encke": 1_000_002,
    }
    metadata = json.loads(metadata_bytes)
    assert metadata["catalog_version"] == "test-release"
    assert metadata["source"]["release_manifest_sha256"] == manifest_sha256
    assert metadata["aliases"]["records"] == [
        {
            "alias": "Halley",
            "alias_kind": "legacy_short_name",
            "canonical_name": "1P/Halley",
        }
    ]


def test_identity_builder_rejects_an_unknown_alias_target(tmp_path: Path) -> None:
    release = _make_release(tmp_path, alias_target="3P/Wrong")

    with pytest.raises(ValueError, match="unknown target"):
        build_catalog(release)


def test_packaged_comet_identity_catalog_is_release_bound() -> None:
    catalog_bytes = CATALOG_PATH.read_bytes()
    metadata_bytes = METADATA_PATH.read_bytes()
    aliases_bytes = ALIASES_PATH.read_bytes()
    metadata = _load_json(METADATA_PATH)

    assert hashlib.sha256(catalog_bytes).hexdigest() == EXPECTED_CATALOG_SHA256
    assert hashlib.sha256(metadata_bytes).hexdigest() == EXPECTED_METADATA_SHA256
    assert hashlib.sha256(aliases_bytes).hexdigest() == EXPECTED_ALIASES_SHA256
    assert metadata["schema_version"] == 1
    assert metadata["catalog_id"] == "moira-comets"
    assert metadata["catalog_version"] == "2026.07.28.1"
    assert metadata["source"]["release_manifest_sha256"] == (
        EXPECTED_RELEASE_MANIFEST_SHA256
    )
    assert metadata["source"]["comet_master_sha256"] == EXPECTED_MASTER_SHA256
    assert metadata["source"]["release_source_revision"] == (
        "49e7b2b42a4d80a68ccbe1f2f07d64c5dc80ba50"
    )
    assert metadata["source"]["released_utc"] == "2026-07-28T12:47:17Z"
    assert metadata["artifact"] == {
        "path": "moira/data/comet_catalog_naif.json",
        "sha256": EXPECTED_CATALOG_SHA256,
        "canonical_name_count": 497,
        "unique_naif_id_count": 497,
    }
    assert metadata["aliases"]["sha256"] == EXPECTED_ALIASES_SHA256
    assert metadata["aliases"]["alias_count"] == 5


def test_packaged_comet_identities_are_unique_and_canonical() -> None:
    catalog = _load_json(CATALOG_PATH)
    folded_names = {
        unicodedata.normalize("NFKC", name).casefold() for name in catalog
    }

    assert len(catalog) == 497
    assert len(set(catalog.values())) == 497
    assert len(folded_names) == 497
    assert all(unicodedata.normalize("NFC", name) == name for name in catalog)
    assert all(
        isinstance(naif_id, int) and naif_id > 1_000_000
        for naif_id in catalog.values()
    )


def test_runtime_registry_matches_canonical_and_alias_artifacts() -> None:
    catalog = _load_json(CATALOG_PATH)
    metadata = _load_json(METADATA_PATH)
    aliases = {
        record["alias"]: record["canonical_name"]
        for record in metadata["aliases"]["records"]
    }

    assert _CANONICAL_COMET_NAIF == catalog
    assert _COMET_ALIASES == aliases
    assert len(COMET_NAIF) == 502
    assert COMET_NAIF["1P/Halley"] == 1_000_001
    assert COMET_NAIF["Halley"] == 1_000_001
    assert COMET_NAIF["2P/Encke"] == 1_000_002
    assert COMET_NAIF["Encke"] == 1_000_002


def test_cross_family_alias_collisions_are_visible_not_claimed_unique() -> None:
    metadata = _load_json(METADATA_PATH)
    comet_aliases = {
        record["alias"].casefold()
        for record in metadata["aliases"]["records"]
    }
    asteroid_names = {name.casefold() for name in ASTEROID_NAIF}

    assert comet_aliases & asteroid_names == {"encke", "halley"}
    assert metadata["identity_policy"]["alias_scope"] == "comet_family_only"
    assert "reject ambiguous names" in metadata["identity_policy"][
        "global_collision_policy"
    ]


def test_runtime_identity_loader_fails_closed_on_catalog_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import moira.comets as comets

    canonical_path = tmp_path / "comet_catalog_naif.json"
    metadata_path = tmp_path / "comet_catalog_naif.metadata.json"
    aliases_path = tmp_path / "comet_catalog_aliases.json"
    canonical_path.write_bytes(CATALOG_PATH.read_bytes() + b" ")
    metadata_path.write_bytes(METADATA_PATH.read_bytes())
    aliases_path.write_bytes(ALIASES_PATH.read_bytes())
    monkeypatch.setattr(comets, "_CANONICAL_CATALOG_PATH", canonical_path)
    monkeypatch.setattr(comets, "_CATALOG_METADATA_PATH", metadata_path)
    monkeypatch.setattr(comets, "_ALIAS_CATALOG_PATH", aliases_path)

    with pytest.raises(RuntimeError, match="SHA-256 mismatch"):
        _load_identity_registry()
