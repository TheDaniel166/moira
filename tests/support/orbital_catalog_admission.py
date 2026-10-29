"""Governed release-side admission for small-body orbital authority tests.

Each admission receipt binds one frozen Horizons authority fixture and the
exact sealed releases it admits. Receipts are immutable: a later release is
admitted by a successor receipt, never by relabelling an earlier one. A
refreshed authority fixture is a new dated file; the earlier one stays frozen
for the receipts that bind it.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_FIXTURE_DIR = REPOSITORY_ROOT / "tests" / "fixtures"
_ORACLE_DIR = REPOSITORY_ROOT / "tests" / "artifacts" / "oracle"

FIXTURE_PATH = _FIXTURE_DIR / "horizons_orbital_elements_catalog_holdout_2026_09_28.json"
AUTHORITY_FIXTURE_PATHS = (
    FIXTURE_PATH,
    _FIXTURE_DIR / "horizons_orbital_elements_catalog_holdout_2026_10_29.json",
)
ADMISSION_PATH = _ORACLE_DIR / "small_body_orbital_catalog_admission_2026-09-28.json"
SUCCESSOR_ADMISSION_PATHS = (
    _ORACLE_DIR / "small_body_orbital_catalog_admission_2026-10-29.json",
    _ORACLE_DIR / "small_body_orbital_catalog_admission_2026-10-29_comets.json",
)


def _relative(path: Path) -> str:
    return path.relative_to(REPOSITORY_ROOT).as_posix()


_FIXTURE_BYTES = {_relative(path): path.read_bytes() for path in AUTHORITY_FIXTURE_PATHS}
_FIXTURES = {name: json.loads(data) for name, data in _FIXTURE_BYTES.items()}

FIXTURE_BYTES = _FIXTURE_BYTES[_relative(FIXTURE_PATH)]
FIXTURE_SHA256 = hashlib.sha256(FIXTURE_BYTES).hexdigest()
FIXTURE = _FIXTURES[_relative(FIXTURE_PATH)]

# Every record of every authority fixture, tagged with the fixture it came
# from so that only receipts binding that fixture can admit it.
CATALOG_RECORDS = tuple(
    {**record, "authority_fixture": name}
    for name, fixture in _FIXTURES.items()
    for record in fixture["records"]
)


def _fixture_date(name: str) -> str:
    """Return ``YYYY-MM-DD`` from a ``..._YYYY_MM_DD.json`` fixture name."""
    return "-".join(name.removesuffix(".json").rsplit("_", 3)[-3:])


# Test IDs name the body and its authority fixture date, e.g.
# "2P/Encke@2026-10-29", because a refreshed fixture repeats a body.
CATALOG_RECORD_IDS = tuple(
    f"{record['body']}@{_fixture_date(record['authority_fixture'])}"
    for record in CATALOG_RECORDS
)

ADMISSION = json.loads(ADMISSION_PATH.read_text(encoding="utf-8"))
ADMISSIONS = (ADMISSION,) + tuple(
    json.loads(path.read_text(encoding="utf-8"))
    for path in SUCCESSOR_ADMISSION_PATHS
)
ACCEPTANCE_GATES = ADMISSION["acceptance_gates"]
for _admission in ADMISSIONS:
    _bound = _admission["authority_fixture"]
    if _bound["path"] not in _FIXTURE_BYTES:
        raise RuntimeError(f"admission binds an unregistered authority fixture: {_bound['path']}")
    if _bound["sha256"] != hashlib.sha256(_FIXTURE_BYTES[_bound["path"]]).hexdigest():
        raise RuntimeError(f"authority fixture bytes changed under its admission: {_bound['path']}")
    if _admission["acceptance_gates"] != ACCEPTANCE_GATES:
        raise RuntimeError("orbital catalog admissions disagree on acceptance gates")


def admitted_release_for_record(
    record: dict,
    manifest_paths: Iterable[Path],
) -> dict | None:
    """Return the exact admitted installed release containing *record*.

    Only receipts that bind the record's own authority fixture are consulted.
    A release identity that lists ``authority_bodies`` admits only those
    records; one without the field admits every record it contains.
    """

    target = int(record["body_naif_id"])
    fixture = record.get("authority_fixture", _relative(FIXTURE_PATH))
    admitted = {
        (item["catalog_id"], item["catalog_version"]): item
        for admission in ADMISSIONS
        if admission["authority_fixture"]["path"] == fixture
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
    "AUTHORITY_FIXTURE_PATHS",
    "CATALOG_RECORDS",
    "CATALOG_RECORD_IDS",
    "FIXTURE",
    "FIXTURE_BYTES",
    "FIXTURE_PATH",
    "FIXTURE_SHA256",
    "SUCCESSOR_ADMISSION_PATHS",
    "admitted_release_for_record",
]
