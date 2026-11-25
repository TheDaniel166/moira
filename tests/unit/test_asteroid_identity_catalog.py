from __future__ import annotations

import hashlib
import json
import unicodedata
from pathlib import Path

import pytest

from moira.asteroids import ASTEROID_NAIF, _NAIF_TO_NAME
from scripts.build_asteroid_identity_catalog import build_catalog


DATA_DIR = Path(__file__).resolve().parents[2] / "moira" / "data"
CATALOG_PATH = DATA_DIR / "asteroid_catalog_naif.json"
METADATA_PATH = DATA_DIR / "asteroid_catalog_naif.metadata.json"

EXPECTED_CATALOG_SHA256 = (
    "46f6ab9acbefccfba8df17fd9f2bc4b77d156e44154e828bfb28d1cbf4b2ad88"
)
EXPECTED_RELEASE_MANIFEST_SHA256 = (
    "6ba756bfc291983b306986b7f0e51319c88795d9723b5e4d97e13dd6d8260173"
)
EXPECTED_UNIFIED_MASTER_SHA256 = (
    "694befd672129c692c6e1fe5b617f9be5da944cb840999342aa402804250733f"
)
EXPECTED_ADMITTED_TARGETS_SHA256 = (
    "e81f253ac9d8a7a9f6c2df9d57316e17129f529236b9d01078931b3ca7b589be"
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


@pytest.mark.parametrize("qualified_build", [False, True])
def test_identity_builder_derives_names_from_one_bound_release(
    tmp_path: Path, qualified_build: bool,
) -> None:
    provisional = {"designation": "2026 ED138", "naif_id": 54_667_839}
    targets = [{"number": 1}, {"number": 1_383}, provisional]
    master = {
        "requested": 3,
        "built": 3,
        "failed": 0,
        "records": [
            {"number": 1, "naif_id": 2_000_001, "name": "Ceres"},
            {"number": 1_383, "naif_id": 2_001_383, "name": "Limburgia"},
            {**provisional, "name": "2026 ED138"},
        ],
        "naif_map": {"Ceres": 2_000_001, "Limburgia": 2_001_383, "2026 ED138": 54_667_839},
    }
    targets_path = tmp_path / "moira_public_asteroid_targets.json"
    master_path = tmp_path / "unified_master.json"
    _write_json(targets_path, targets)
    _write_json(master_path, master)
    manifest = {
        "catalog_id": "moira-asteroids",
        "catalog_version": "test-release",
        "body_count": 3,
        "source": "test source",
        "provenance": {
            "trajectory_source": "JPL Horizons VECTORS",
            "horizons_api": "https://ssd.jpl.nasa.gov/api/horizons.api",
        },
        "shards": [
            {"bodies": [2_000_001]},
            {"bodies": [2_001_383]},
            {"bodies": [54_667_839]},
        ],
        "release": {
            "source_revision": "test-source",
            "released_utc": "2026-07-27T00:00:00Z",
            "files": [_file_spec(master_path), _file_spec(targets_path)],
        },
    }
    manifest_path = tmp_path / "manifest.json"
    qualification_path = tmp_path / "catalog-qualification.json"
    if qualified_build:
        manifest["release"].pop("source_revision")
        manifest["release"]["source_manifest_sha256"] = "0a" * 32
        _write_json(qualification_path, {"bodies_total": 3, "qualified": 3})
        manifest["release"]["files"].append(_file_spec(qualification_path))
    _write_json(manifest_path, manifest)
    manifest_sha256 = hashlib.sha256(manifest_path.read_bytes()).hexdigest()

    catalog_bytes, metadata_bytes = build_catalog(
        tmp_path,
        expected_manifest_sha256=manifest_sha256,
    )

    assert json.loads(catalog_bytes) == {
        "Ceres": 2_000_001,
        "Limburgia": 2_001_383,
        "2026 ED138": 54_667_839,
    }
    metadata = json.loads(metadata_bytes)
    assert metadata["catalog_version"] == "test-release"
    assert metadata["source"]["release_manifest_sha256"] == manifest_sha256
    assert metadata["artifact"]["canonical_name_count"] == 3
    if qualified_build:
        assert metadata["source"]["release_source_manifest_sha256"] == "0a" * 32
        assert metadata["source"]["catalog_qualification_sha256"] == _file_spec(qualification_path)["sha256"]
        _write_json(qualification_path, {"bodies_total": 3, "qualified": 2})
        manifest["release"]["files"][-1] = _file_spec(qualification_path)
        _write_json(manifest_path, manifest)
        with pytest.raises(ValueError, match="qualification does not cover the complete release"):
            build_catalog(tmp_path)
        _write_json(qualification_path, {"bodies_total": 3, "qualified": 3})
        manifest["release"]["files"][-1] = _file_spec(qualification_path)
    else:
        assert metadata["source"]["release_source_revision"] == "test-source"

    provisional["naif_id"] = 54_667_840
    _write_json(targets_path, targets)
    manifest["release"]["files"][1] = _file_spec(targets_path)
    _write_json(manifest_path, manifest)
    with pytest.raises(ValueError, match="has NAIF ID 54667839, expected 54667840"):
        build_catalog(tmp_path)


def test_packaged_asteroid_identity_catalog_is_release_bound() -> None:
    catalog_bytes = CATALOG_PATH.read_bytes()
    metadata = _load_json(METADATA_PATH)

    assert hashlib.sha256(catalog_bytes).hexdigest() == EXPECTED_CATALOG_SHA256
    assert metadata["schema_version"] == 1
    assert metadata["catalog_id"] == "moira-asteroids"
    assert metadata["catalog_version"] == "2026.11.24.1"
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
        "canonical_name_count": 11_250,
        "unique_naif_id_count": 11_250,
    }


def test_packaged_asteroid_identities_are_unique_and_canonical() -> None:
    catalog = _load_json(CATALOG_PATH)
    folded_names = {
        unicodedata.normalize("NFKC", name).casefold() for name in catalog
    }

    assert len(catalog) == 11_250
    assert len(set(catalog.values())) == 11_250
    assert len(folded_names) == 11_250
    assert all(unicodedata.normalize("NFC", name) == name for name in catalog)
    assert all(isinstance(naif_id, int) and naif_id > 2_000_000 for naif_id in catalog.values())


def test_runtime_registry_matches_the_packaged_canonical_artifact() -> None:
    catalog = _load_json(CATALOG_PATH)

    assert ASTEROID_NAIF == catalog
    assert len(ASTEROID_NAIF) == 11_250
    assert len(_NAIF_TO_NAME) == 11_250
    assert ASTEROID_NAIF["Ceres"] == 2_000_001
    assert ASTEROID_NAIF["Limburgia"] == 2_001_383
    assert ASTEROID_NAIF["Jacquet"] == 2_020_395
    assert ASTEROID_NAIF["Guyidong"] == 2_010_946
    assert ASTEROID_NAIF["Bussey"] == 2_014_380
    assert ASTEROID_NAIF["Arawn"] == 2_015_810
    assert ASTEROID_NAIF["Narcissus"] == 2_037_117
    assert ASTEROID_NAIF["Mani"] == 2_307_261
    assert ASTEROID_NAIF["'Aylo'chaxnim"] == 2_594_913
    assert ASTEROID_NAIF["Ka`epaoka`awela"] == 2_514_107
    assert "Asteroid20395" not in ASTEROID_NAIF
    assert "Asteroid10946" not in ASTEROID_NAIF
    assert "Asteroid14380" not in ASTEROID_NAIF
    assert _NAIF_TO_NAME[2_001_383] == "Limburgia"
    assert _NAIF_TO_NAME[2_020_395] == "Jacquet"
    assert _NAIF_TO_NAME[2_010_946] == "Guyidong"
    assert _NAIF_TO_NAME[2_014_380] == "Bussey"
    assert _NAIF_TO_NAME[2_015_810] == "Arawn"
    assert _NAIF_TO_NAME[2_037_117] == "Narcissus"
    assert _NAIF_TO_NAME[2_307_261] == "Mani"
    assert _NAIF_TO_NAME[2_594_913] == "'Aylo'chaxnim"
    assert _NAIF_TO_NAME[2_514_107] == "Ka`epaoka`awela"
    assert ASTEROID_NAIF["2012 VP113"] == 50_666_516
    assert ASTEROID_NAIF["2014 UZ224"] == 50_760_674
    assert ASTEROID_NAIF["2017 OF201"] == 54_533_005
    assert ASTEROID_NAIF["2021 DR15"] == 54_231_255
    assert ASTEROID_NAIF["2026 ED138"] == 54_667_839
