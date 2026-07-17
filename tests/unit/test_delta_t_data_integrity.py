"""Integrity checks for the packaged Delta-T data manifest.

These tests prove that the manifest describes the files shipped in this
checkout.  They deliberately do not claim scientific accuracy for any data
product.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any


_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_DATA_DIRECTORY = (_REPOSITORY_ROOT / "moira" / "data").resolve()
_MANIFEST_PATH = _DATA_DIRECTORY / "delta_t_manifest.json"

_HASH_CANONICALIZATION = (
    "UTF-8 text with CRLF and CR normalized to LF before hashing"
)
_REQUIRED_MANIFEST_FIELDS = {
    "schema_version",
    "generated_at_utc",
    "hash_algorithm",
    "hash_canonicalization",
    "datasets",
}
_REQUIRED_DATASET_FIELDS = {
    "path",
    "product",
    "source",
    "retrieved_at_utc",
    "transformation",
    "units",
    "coverage",
    "row_count",
    "sha256",
    "runtime_status",
    "caveats",
}
_EXPECTED_RUNTIME_STATUS = {
    "iers_eop.txt": "admitted_for_utc_to_ut1",
    "delta_t_hpiers_2016.txt": "admitted_with_explicit_epoch_policy",
    "core_angular_momentum.txt": "quarantined_research_only",
    "grace_lod_contribution.txt": "quarantined_audit_reproduction_only",
    "aam_glaam_annual.txt": "quarantined_diagnostic_only",
    "oam_ecco_annual.txt": "quarantined_diagnostic_only",
}
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")


def _load_manifest() -> dict[str, Any]:
    return json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))


def _canonical_text(path: Path) -> str:
    text = path.read_bytes().decode("utf-8")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _data_rows(path: Path) -> list[str]:
    return [
        line
        for line in _canonical_text(path).splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def test_delta_t_manifest_schema_and_runtime_status_are_explicit() -> None:
    manifest = _load_manifest()

    assert _REQUIRED_MANIFEST_FIELDS <= manifest.keys()
    assert manifest["schema_version"] == 1
    assert manifest["hash_algorithm"] == "sha256"
    assert manifest["hash_canonicalization"] == _HASH_CANONICALIZATION
    assert isinstance(manifest["generated_at_utc"], str)
    assert manifest["generated_at_utc"]

    datasets = manifest["datasets"]
    assert isinstance(datasets, list)
    assert datasets

    paths = [dataset["path"] for dataset in datasets]
    assert len(paths) == len(set(paths))
    assert set(paths) == set(_EXPECTED_RUNTIME_STATUS)

    statuses = {dataset["path"]: dataset["runtime_status"] for dataset in datasets}
    assert statuses == _EXPECTED_RUNTIME_STATUS
    assert any(status.startswith("admitted_") for status in statuses.values())
    assert any(status.startswith("quarantined_") for status in statuses.values())
    assert all(
        status.startswith(("admitted_", "quarantined_"))
        for status in statuses.values()
    )


def test_delta_t_manifest_entries_match_packaged_files() -> None:
    manifest = _load_manifest()

    for dataset in manifest["datasets"]:
        assert _REQUIRED_DATASET_FIELDS <= dataset.keys()

        relative_path = Path(dataset["path"])
        assert isinstance(dataset["path"], str)
        assert dataset["path"]
        assert not relative_path.is_absolute()
        assert len(relative_path.parts) == 1

        data_path = (_DATA_DIRECTORY / relative_path).resolve()
        assert data_path.parent == _DATA_DIRECTORY
        assert data_path.is_file()

        assert isinstance(dataset["product"], str) and dataset["product"]
        assert isinstance(dataset["transformation"], str) and dataset["transformation"]
        assert dataset["retrieved_at_utc"] is None or (
            isinstance(dataset["retrieved_at_utc"], str)
            and bool(dataset["retrieved_at_utc"])
        )

        source = dataset["source"]
        assert set(source) >= {"authority", "url"}
        assert isinstance(source["authority"], str) and source["authority"]
        assert isinstance(source["url"], str) and source["url"].startswith("https://")

        units = dataset["units"]
        assert isinstance(units, dict) and units
        assert all(
            isinstance(name, str)
            and bool(name)
            and isinstance(unit, str)
            and bool(unit)
            for name, unit in units.items()
        )

        coverage = dataset["coverage"]
        assert set(coverage) >= {"first_epoch", "last_epoch"}
        first_epoch = float(coverage["first_epoch"])
        last_epoch = float(coverage["last_epoch"])
        assert math.isfinite(first_epoch)
        assert math.isfinite(last_epoch)
        assert first_epoch <= last_epoch

        assert isinstance(dataset["row_count"], int)
        assert not isinstance(dataset["row_count"], bool)
        assert dataset["row_count"] > 0
        assert isinstance(dataset["sha256"], str)
        assert _SHA256_PATTERN.fullmatch(dataset["sha256"])
        assert isinstance(dataset["caveats"], list)
        assert all(isinstance(caveat, str) and caveat for caveat in dataset["caveats"])

        canonical_bytes = _canonical_text(data_path).encode("utf-8")
        assert hashlib.sha256(canonical_bytes).hexdigest() == dataset["sha256"]

        rows = _data_rows(data_path)
        assert len(rows) == dataset["row_count"]
        epochs = [float(row.split()[0]) for row in rows]
        assert all(math.isfinite(epoch) for epoch in epochs)
        assert epochs[0] == first_epoch
        assert epochs[-1] == last_epoch
        assert min(epochs) == first_epoch
        assert max(epochs) == last_epoch


def test_hpiers_modern_epochs_restore_the_declared_half_year_cadence() -> None:
    path = _DATA_DIRECTORY / "delta_t_hpiers_2016.txt"
    rows = [line.split() for line in _data_rows(path)]
    modern = [row for row in rows if 1950.0 <= float(row[0]) <= 2016.0]
    unique_epochs = tuple(sorted({float(row[0]) for row in modern}))

    assert unique_epochs == tuple(1950.0 + 0.5 * index for index in range(133))
    by_epoch: dict[float, list[tuple[str, ...]]] = {}
    for row in modern:
        by_epoch.setdefault(float(row[0]), []).append(tuple(row[1:]))
    assert by_epoch[1972.0] == [by_epoch[1972.0][0], by_epoch[1972.0][0]]
    assert by_epoch[1994.0] == [by_epoch[1994.0][0], by_epoch[1994.0][0]]
