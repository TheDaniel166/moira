"""Refresh family annotations without rebuilding asteroid BSP shards.

This changes JSON metadata only.  It never opens or writes a BSP file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from moira.asteroid_families import (
    ASTEROID_FAMILY_CATALOG_SOURCE,
    asteroid_families,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_json_write(path: Path, payload: object, *, compact: bool = False) -> None:
    temporary = path.with_name(f"{path.name}.family-refresh-{os.getpid()}.tmp")
    if compact:
        rendered = json.dumps(payload, separators=(",", ":"))
    else:
        rendered = json.dumps(payload, indent=2)
    temporary.write_text(rendered + "\n", encoding="utf-8")
    temporary.replace(path)


def _annotate_record(record: dict[str, object]) -> tuple[bool, bool]:
    number = int(record["number"])
    memberships = asteroid_families(number)
    record["family"] = memberships[0] if memberships else None
    record["families"] = memberships
    return bool(memberships), len(memberships) > 1


def refresh(targets_path: Path, metadata_dir: Path, receipt_path: Path) -> None:
    targets_hash_before = _sha256(targets_path)
    targets = json.loads(targets_path.read_text(encoding="utf-8"))
    matched = 0
    multiple = 0
    for target in targets:
        has_family, has_multiple = _annotate_record(target)
        matched += has_family
        multiple += has_multiple
    _atomic_json_write(targets_path, targets, compact=True)

    metadata_files_updated = 0
    metadata_records_updated = 0
    skipped_metadata_files: list[str] = []
    for metadata_path in sorted(metadata_dir.glob("asteroid_shard_*.metadata.json")):
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            skipped_metadata_files.append(metadata_path.name)
            continue
        records = metadata.get("records")
        if not isinstance(records, list):
            skipped_metadata_files.append(metadata_path.name)
            continue
        for record in records:
            _annotate_record(record)
        metadata["family_catalog_source"] = ASTEROID_FAMILY_CATALOG_SOURCE
        _atomic_json_write(metadata_path, metadata)
        metadata_files_updated += 1
        metadata_records_updated += len(records)

    master_path = metadata_dir / "unified_master.json"
    master_updated = False
    if master_path.exists():
        master = json.loads(master_path.read_text(encoding="utf-8"))
        for record in master.get("records", []):
            _annotate_record(record)
        for failure in master.get("failures", []):
            _annotate_record(failure)
        master["family_catalog_source"] = ASTEROID_FAMILY_CATALOG_SOURCE
        _atomic_json_write(master_path, master)
        master_updated = True

    receipt = {
        "refreshed_at_utc": datetime.now(timezone.utc).isoformat(),
        "catalog_source": ASTEROID_FAMILY_CATALOG_SOURCE,
        "targets_path": str(targets_path.resolve()),
        "targets_sha256_before": targets_hash_before,
        "targets_sha256_after": _sha256(targets_path),
        "target_count": len(targets),
        "targets_with_membership": matched,
        "targets_without_membership": len(targets) - matched,
        "targets_with_multiple_memberships": multiple,
        "metadata_directory": str(metadata_dir.resolve()),
        "metadata_files_updated": metadata_files_updated,
        "metadata_records_updated": metadata_records_updated,
        "skipped_metadata_files": skipped_metadata_files,
        "unified_master_updated": master_updated,
        "bsp_files_touched": 0,
    }
    _atomic_json_write(receipt_path, receipt)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("targets", type=Path)
    parser.add_argument("metadata_dir", type=Path)
    parser.add_argument(
        "--receipt",
        type=Path,
        default=None,
        help="defaults to METADATA_DIR/family_annotation_receipt.json",
    )
    args = parser.parse_args()
    receipt = args.receipt or args.metadata_dir / "family_annotation_receipt.json"
    refresh(args.targets, args.metadata_dir, receipt)


if __name__ == "__main__":
    main()
