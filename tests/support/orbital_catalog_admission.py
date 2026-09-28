"""Governed release-side admission for small-body orbital authority tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = (
    REPOSITORY_ROOT
    / "tests"
    / "fixtures"
    / "horizons_orbital_elements_catalog_holdout_2026_09_28.json"
)
ADMISSION_PATH = (
    REPOSITORY_ROOT
    / "tests"
    / "artifacts"
    / "oracle"
    / "small_body_orbital_catalog_admission_2026-09-28.json"
)
FIXTURE_BYTES = FIXTURE_PATH.read_bytes()
FIXTURE_SHA256 = hashlib.sha256(FIXTURE_BYTES).hexdigest()
FIXTURE = json.loads(FIXTURE_BYTES)
CATALOG_RECORDS = tuple(FIXTURE["records"])
ADMISSION = json.loads(ADMISSION_PATH.read_text(encoding="utf-8"))
ACCEPTANCE_GATES = ADMISSION["acceptance_gates"]


def admitted_release_for_record(
    record: dict,
    manifest_paths: Iterable[Path],
) -> dict | None:
    """Return the exact admitted installed release containing *record*."""

    target = int(record["body_naif_id"])
    admitted = {
        (item["catalog_id"], item["catalog_version"]): item
        for item in ADMISSION["catalog_release_identity"]
    }
    for manifest_path in manifest_paths:
        manifest_bytes = manifest_path.read_bytes()
        manifest = json.loads(manifest_bytes)
        body_ids = {
            int(body_id)
            for shard in manifest.get("shards", ())
            for body_id in shard.get("bodies", ())
        }
        if target not in body_ids:
            continue
        key = (manifest.get("catalog_id"), manifest.get("catalog_version"))
        release = admitted.get(key)
        if release is None:
            continue
        if hashlib.sha256(manifest_bytes).hexdigest() != release["manifest_sha256"]:
            continue
        return release
    return None


__all__ = [
    "ACCEPTANCE_GATES",
    "ADMISSION",
    "ADMISSION_PATH",
    "CATALOG_RECORDS",
    "FIXTURE",
    "FIXTURE_BYTES",
    "FIXTURE_PATH",
    "FIXTURE_SHA256",
    "admitted_release_for_record",
]
