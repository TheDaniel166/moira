from __future__ import annotations

import hashlib
import json
import unicodedata
from pathlib import Path

from moira.asteroids import ASTEROID_NAIF, _NAIF_TO_NAME
from scripts.build_asteroid_identity_catalog import build_catalog


DATA_DIR = Path(__file__).resolve().parents[2] / "moira" / "data"
CATALOG_PATH = DATA_DIR / "asteroid_catalog_naif.json"
METADATA_PATH = DATA_DIR / "asteroid_catalog_naif.metadata.json"

EXPECTED_CATALOG_SHA256 = (
    "1630b618b46706fa6a40011c6ef80c000e9fbe77d04204e1c7bc446af562d4d4"
)
EXPECTED_RELEASE_MANIFEST_SHA256 = (
    "c151348a9edd3620716da8849ceb239d0ab39688ead948ffecb592c13e068c64"
)
EXPECTED_UNIFIED_MASTER_SHA256 = (
    "72c0dd9a07ba2b2af610f8755b785d2f473a550b62d77aeaf4d45ac2d3ae185d"
)
EXPECTED_ADMITTED_TARGETS_SHA256 = (
    "08927dcb994388902bea186c70d286d7e85334f863309123b194aafc8915ad91"
)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _file_spec(path: Path) -> dict[str, object]:
    payload = path.read_bytes()
    return {
        "path": path.name,
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def test_identity_builder_derives_names_from_one_bound_release(
    tmp_path: Path,
) -> None:
    targets = [{"number": 1}, {"number": 1_383}]
    master = {
        "requested": 2,
        "built": 2,
        "failed": 0,
        "records": [
            {"number": 1, "naif_id": 2_000_001, "name": "Ceres"},
            {"number": 1_383, "naif_id": 2_001_383, "name": "Limburgia"},
        ],
        "naif_map": {"Ceres": 2_000_001, "Limburgia": 2_001_383},
    }
    targets_path = tmp_path / "moira_public_asteroid_targets.json"
    master_path = tmp_path / "unified_master.json"
    _write_json(targets_path, targets)
    _write_json(master_path, master)
    manifest = {
        "catalog_id": "moira-asteroids",
        "catalog_version": "test-release",
        "body_count": 2,
        "source": "test source",
        "provenance": {
            "trajectory_source": "JPL Horizons VECTORS",
            "horizons_api": "https://ssd.jpl.nasa.gov/api/horizons.api",
        },
        "shards": [
            {"bodies": [2_000_001]},
            {"bodies": [2_001_383]},
        ],
        "release": {
            "source_revision": "test-source",
            "released_utc": "2026-07-27T00:00:00Z",
            "files": [_file_spec(master_path), _file_spec(targets_path)],
        },
    }
    manifest_path = tmp_path / "manifest.json"
    _write_json(manifest_path, manifest)
    manifest_sha256 = hashlib.sha256(manifest_path.read_bytes()).hexdigest()

    catalog_bytes, metadata_bytes = build_catalog(
        tmp_path,
        expected_manifest_sha256=manifest_sha256,
    )

    assert json.loads(catalog_bytes) == {
        "Ceres": 2_000_001,
        "Limburgia": 2_001_383,
    }
    metadata = json.loads(metadata_bytes)
    assert metadata["catalog_version"] == "test-release"
    assert metadata["source"]["release_manifest_sha256"] == manifest_sha256
    assert metadata["artifact"]["canonical_name_count"] == 2


def test_packaged_asteroid_identity_catalog_is_release_bound() -> None:
    catalog_bytes = CATALOG_PATH.read_bytes()
    metadata = _load_json(METADATA_PATH)

    assert hashlib.sha256(catalog_bytes).hexdigest() == EXPECTED_CATALOG_SHA256
    assert metadata["schema_version"] == 1
    assert metadata["catalog_id"] == "moira-asteroids"
    assert metadata["catalog_version"] == "2026.08.12.1"
    assert metadata["source"]["release_manifest_sha256"] == (
        EXPECTED_RELEASE_MANIFEST_SHA256
    )
    assert metadata["source"]["unified_master_sha256"] == (
        EXPECTED_UNIFIED_MASTER_SHA256
    )
    assert metadata["source"]["admitted_targets_sha256"] == (
        EXPECTED_ADMITTED_TARGETS_SHA256
    )
    assert metadata["artifact"] == {
        "path": "moira/data/asteroid_catalog_naif.json",
        "sha256": EXPECTED_CATALOG_SHA256,
        "canonical_name_count": 10_025,
        "unique_naif_id_count": 10_025,
    }


def test_packaged_asteroid_identities_are_unique_and_canonical() -> None:
    catalog = _load_json(CATALOG_PATH)
    folded_names = {
        unicodedata.normalize("NFKC", name).casefold() for name in catalog
    }

    assert len(catalog) == 10_025
    assert len(set(catalog.values())) == 10_025
    assert len(folded_names) == 10_025
    assert all(unicodedata.normalize("NFC", name) == name for name in catalog)
    assert all(isinstance(naif_id, int) and naif_id > 2_000_000 for naif_id in catalog.values())


def test_runtime_registry_matches_the_packaged_canonical_artifact() -> None:
    catalog = _load_json(CATALOG_PATH)

    assert ASTEROID_NAIF == catalog
    assert len(ASTEROID_NAIF) == 10_025
    assert len(_NAIF_TO_NAME) == 10_025
    assert ASTEROID_NAIF["Ceres"] == 2_000_001
    assert ASTEROID_NAIF["Limburgia"] == 2_001_383
    assert ASTEROID_NAIF["Jacquet"] == 2_020_395
    assert ASTEROID_NAIF["Mani"] == 2_307_261
    assert ASTEROID_NAIF["'Aylo'chaxnim"] == 2_594_913
    assert ASTEROID_NAIF["Ka`epaoka`awela"] == 2_514_107
    assert "Asteroid20395" not in ASTEROID_NAIF
    assert _NAIF_TO_NAME[2_001_383] == "Limburgia"
    assert _NAIF_TO_NAME[2_020_395] == "Jacquet"
    assert _NAIF_TO_NAME[2_307_261] == "Mani"
    assert _NAIF_TO_NAME[2_594_913] == "'Aylo'chaxnim"
    assert _NAIF_TO_NAME[2_514_107] == "Ka`epaoka`awela"
