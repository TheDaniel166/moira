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
_ORACLE_DIR = REPOSITORY_ROOT / "tests" / "artifacts" / "oracle"
# The September receipt is historical and immutable. A successor receipt
# admits a later sealed release against the same frozen authority fixture; it
# never relabels the earlier one.
ADMISSION_PATH = _ORACLE_DIR / "small_body_orbital_catalog_admission_2026-09-28.json"
SUCCESSOR_ADMISSION_PATHS = (
    _ORACLE_DIR / "small_body_orbital_catalog_admission_2026-10-29.json",
)
FIXTURE_BYTES = FIXTURE_PATH.read_bytes()
FIXTURE_SHA256 = hashlib.sha256(FIXTURE_BYTES).hexdigest()
FIXTURE = json.loads(FIXTURE_BYTES)
CATALOG_RECORDS = tuple(FIXTURE["records"])
ADMISSION = json.loads(ADMISSION_PATH.read_text(encoding="utf-8"))
ADMISSIONS = (ADMISSION,) + tuple(
    json.loads(path.read_text(encoding="utf-8"))
    for path in SUCCESSOR_ADMISSION_PATHS
)
ACCEPTANCE_GATES = ADMISSION["acceptance_gates"]
for _admission in ADMISSIONS:
    if _admission["authority_fixture"]["sha256"] != FIXTURE_SHA256:
        raise RuntimeError("an orbital catalog admission binds a different authority fixture")
    if _admission["acceptance_gates"] != ACCEPTANCE_GATES:
        raise RuntimeError("orbital catalog admissions disagree on acceptance gates")


def admitted_release_for_record(
    record: dict,
    manifest_paths: Iterable[Path],
) -> dict | None:
    """Return the exact admitted installed release containing *record*.

    A release identity that lists ``authority_bodies`` admits only those
    fixture records; one without the field admits every record it contains.
    """

    target = int(record["body_naif_id"])
    admitted = {
        (item["catalog_id"], item["catalog_version"]): item
        for admission in ADMISSIONS
        for item in admission["catalog_release_identity"]
        if record["body"] in item.get("authority_bodies", (record["body"],))
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
    "ADMISSIONS",
    "ADMISSION_PATH",
    "CATALOG_RECORDS",
    "FIXTURE",
    "FIXTURE_BYTES",
    "FIXTURE_PATH",
    "FIXTURE_SHA256",
    "SUCCESSOR_ADMISSION_PATHS",
    "admitted_release_for_record",
]
