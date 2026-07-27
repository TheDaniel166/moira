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
    "95c4f5a1c0a8dbb80656f1efce34ff97d9bcf1d3b1d213e5584530de787160ee"
)
EXPECTED_RELEASE_MANIFEST_SHA256 = (
    "0560302f877a46cebc550376ae70665fefab84801078181cf3c4199ce86d49d0"
)
EXPECTED_UNIFIED_MASTER_SHA256 = (
    "348891dd2e371a919fd276f2edd41b75e9b56513b7edc2176079f84ec989eb96"
)
EXPECTED_ADMITTED_TARGETS_SHA256 = (
    "1877e224431c62b2e3cf1dbdf3d13fccf45892a395616ca64b69ad5807f35b39"
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
    catalog = json.loads(catalog_bytes)
    metadata = _load_json(METADATA_PATH)

    assert hashlib.sha256(catalog_bytes).hexdigest() == EXPECTED_CATALOG_SHA256
    assert metadata["schema_version"] == 1
    assert metadata["catalog_id"] == "moira-asteroids"
    assert metadata["catalog_version"] == "2026.07.27.1"
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
        "canonical_name_count": 9_974,
        "unique_naif_id_count": 9_974,
    }


def test_packaged_asteroid_identities_are_unique_and_canonical() -> None:
    catalog = _load_json(CATALOG_PATH)
    folded_names = {
        unicodedata.normalize("NFKC", name).casefold() for name in catalog
    }

    assert len(catalog) == 9_974
    assert len(set(catalog.values())) == 9_974
    assert len(folded_names) == 9_974
    assert all(unicodedata.normalize("NFC", name) == name for name in catalog)
    assert all(isinstance(naif_id, int) and naif_id > 2_000_000 for naif_id in catalog.values())


def test_runtime_registry_matches_the_packaged_canonical_artifact() -> None:
    catalog = _load_json(CATALOG_PATH)

    assert ASTEROID_NAIF == catalog
    assert len(ASTEROID_NAIF) == 9_974
    assert len(_NAIF_TO_NAME) == 9_974
    assert ASTEROID_NAIF["Ceres"] == 2_000_001
    assert ASTEROID_NAIF["Limburgia"] == 2_001_383
    assert ASTEROID_NAIF["Jacquet"] == 2_020_395
    assert ASTEROID_NAIF["Mani"] == 2_307_261
    assert "Asteroid20395" not in ASTEROID_NAIF
    assert _NAIF_TO_NAME[2_001_383] == "Limburgia"
    assert _NAIF_TO_NAME[2_020_395] == "Jacquet"
    assert _NAIF_TO_NAME[2_307_261] == "Mani"
