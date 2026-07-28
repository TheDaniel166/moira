"""
Prepare and verify immutable Moira small-body catalog releases.

This module does not calculate or rebuild ephemerides.  It copies an existing
manifest-declared Type-13 shard set into a new release directory, records the
exact bytes with SHA-256, and optionally creates a byte-pinned ZIP archive.

Command examples::

    python -m moira.small_body_catalog_release prepare SOURCE OUTPUT \
        --catalog-id moira-asteroids \
        --catalog-version 2026.07.27.1 \
        --license LICENSE \
        --notice moira/kernels/SMALL_BODY_CATALOG_NOTICE.md \
        --support-file unified_master.json \
        --support-file unified_targets.json \
        --archive OUTPUT.zip

    python -m moira.small_body_catalog_release verify OUTPUT
    python -m moira.small_body_catalog_release verify-archive OUTPUT.zip
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence


MANIFEST_SCHEMA = "moira.small-body-catalog/v1"
DEFAULT_RECEIPT_NAME = "SHA256SUMS"
_HASH_ALGORITHM = "sha256"
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_IDENTITY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_COPY_CHUNK_BYTES = 1024 * 1024


class CatalogReleaseError(ValueError):
    """Raised when a catalog cannot be prepared or verified safely."""


@dataclass(frozen=True)
class FileIdentity:
    """Byte identity for one release file."""

    path: str
    bytes: int
    sha256: str
    role: str

    def as_manifest_record(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "role": self.role,
            "bytes": self.bytes,
            "sha256": self.sha256,
        }


@dataclass(frozen=True)
class ReleaseVerification:
    """Verified identity and counts for one release directory."""

    root: Path
    catalog_id: str
    catalog_version: str
    file_count: int
    shard_count: int
    body_count: int
    manifest_sha256: str


@dataclass(frozen=True)
class ArchiveIdentity:
    """Byte identity for a release archive."""

    path: Path
    bytes: int
    sha256: str
    checksum_path: Path


@dataclass(frozen=True)
class IncludedReleaseFile:
    """One explicitly bound file copied into a catalog release."""

    source_path: Path
    release_path: str
    role: str


def _json_bytes(payload: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _sha256_path(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while chunk := stream.read(_COPY_CHUNK_BYTES):
            size += len(chunk)
            digest.update(chunk)
    return size, digest.hexdigest()


def _copy_and_hash(
    source: Path,
    destination: Path,
    *,
    release_path: str,
    role: str,
) -> FileIdentity:
    if not source.is_file() or source.is_symlink():
        raise CatalogReleaseError(f"Release input is not a regular file: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    size = 0
    with source.open("rb") as source_stream, destination.open("xb") as target_stream:
        while chunk := source_stream.read(_COPY_CHUNK_BYTES):
            target_stream.write(chunk)
            size += len(chunk)
            digest.update(chunk)
    return FileIdentity(
        path=release_path,
        bytes=size,
        sha256=digest.hexdigest(),
        role=role,
    )


def _safe_release_path(raw_path: str, *, field: str) -> str:
    if not isinstance(raw_path, str) or not raw_path:
        raise CatalogReleaseError(f"{field} must be a non-empty relative path")
    if "\\" in raw_path:
        raise CatalogReleaseError(f"{field} must use '/' path separators: {raw_path!r}")
    path = PurePosixPath(raw_path)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise CatalogReleaseError(f"{field} escapes the catalog root: {raw_path!r}")
    normalized = path.as_posix()
    if normalized != raw_path:
        raise CatalogReleaseError(
            f"{field} is not in canonical relative form: {raw_path!r}"
        )
    return normalized


def _path_under(root: Path, release_path: str) -> Path:
    safe_path = _safe_release_path(release_path, field="release file path")
    root_resolved = root.resolve()
    candidate = (root_resolved / Path(*PurePosixPath(safe_path).parts)).resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise CatalogReleaseError(
            f"Release file escapes the catalog root: {release_path!r}"
        ) from exc
    return candidate


def _canonical_released_utc(raw_value: str | None) -> str:
    if raw_value is None:
        instant = datetime.now(timezone.utc).replace(microsecond=0)
    else:
        if not raw_value.endswith("Z"):
            raise CatalogReleaseError("released UTC must end in 'Z'")
        try:
            instant = datetime.fromisoformat(raw_value[:-1] + "+00:00")
        except ValueError as exc:
            raise CatalogReleaseError(
                f"released UTC is not an ISO-8601 instant: {raw_value!r}"
            ) from exc
        if instant.utcoffset() != timezone.utc.utcoffset(instant):
            raise CatalogReleaseError("released UTC must use the UTC offset")
        instant = instant.astimezone(timezone.utc)
    return instant.isoformat(timespec="seconds").replace("+00:00", "Z")


def _validate_identity(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not _IDENTITY_RE.fullmatch(value):
        raise CatalogReleaseError(
            f"{field} must contain only letters, digits, '.', '_', or '-': {value!r}"
        )
    return value


def _load_json_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CatalogReleaseError(f"Unable to read {label} JSON at {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise CatalogReleaseError(f"{label} must contain a JSON object: {path}")
    return payload


def _metadata_path_for_shard(shard_path: str) -> str:
    path = PurePosixPath(shard_path)
    return path.with_suffix(".metadata.json").as_posix()


def _require_int(value: Any, *, field: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise CatalogReleaseError(f"{field} must be an integer >= {minimum}")
    return value


def _validate_digest(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise CatalogReleaseError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _validate_manifest_structure(
    manifest: Mapping[str, Any],
    *,
    root: Path,
    require_release_identity: bool,
) -> tuple[list[dict[str, Any]], int]:
    raw_shards = manifest.get("shards")
    if not isinstance(raw_shards, list) or not raw_shards:
        raise CatalogReleaseError("manifest.shards must be a non-empty list")
    declared_shards = _require_int(
        manifest.get("shard_count"), field="manifest.shard_count", minimum=1
    )
    if declared_shards != len(raw_shards):
        raise CatalogReleaseError(
            "manifest.shard_count does not equal the number of shard records"
        )

    seen_indices: set[int] = set()
    seen_paths: set[str] = set()
    seen_bodies: set[int] = set()
    total_bodies = 0
    normalized_shards: list[dict[str, Any]] = []

    for position, raw_shard in enumerate(raw_shards):
        if not isinstance(raw_shard, dict):
            raise CatalogReleaseError(f"manifest.shards[{position}] must be an object")
        index = _require_int(
            raw_shard.get("index"),
            field=f"manifest.shards[{position}].index",
        )
        if index in seen_indices:
            raise CatalogReleaseError(f"Duplicate shard index in manifest: {index}")
        seen_indices.add(index)

        shard_path = _safe_release_path(
            raw_shard.get("path"),
            field=f"manifest.shards[{position}].path",
        )
        if shard_path in seen_paths:
            raise CatalogReleaseError(f"Duplicate shard path in manifest: {shard_path}")
        seen_paths.add(shard_path)

        bodies = raw_shard.get("bodies")
        if not isinstance(bodies, list) or not bodies:
            raise CatalogReleaseError(
                f"manifest.shards[{position}].bodies must be a non-empty list"
            )
        body_ids = [
            _require_int(
                body,
                field=f"manifest.shards[{position}].bodies",
                minimum=1,
            )
            for body in bodies
        ]
        if len(set(body_ids)) != len(body_ids):
            raise CatalogReleaseError(f"Shard {index} contains duplicate body IDs")
        overlap = seen_bodies.intersection(body_ids)
        if overlap:
            raise CatalogReleaseError(
                f"Body IDs occur in more than one shard: {sorted(overlap)[:5]}"
            )
        seen_bodies.update(body_ids)

        body_count = _require_int(
            raw_shard.get("body_count"),
            field=f"manifest.shards[{position}].body_count",
            minimum=1,
        )
        if body_count != len(body_ids):
            raise CatalogReleaseError(
                f"Shard {index} body_count does not equal its body list length"
            )

        shard = dict(raw_shard)
        shard["path"] = shard_path
        if require_release_identity:
            shard["bytes"] = _require_int(
                raw_shard.get("bytes"),
                field=f"manifest.shards[{position}].bytes",
                minimum=1,
            )
            shard["sha256"] = _validate_digest(
                raw_shard.get("sha256"),
                field=f"manifest.shards[{position}].sha256",
            )
            raw_metadata = raw_shard.get("metadata")
            if not isinstance(raw_metadata, dict):
                raise CatalogReleaseError(
                    f"manifest.shards[{position}].metadata must be an object"
                )
            metadata = dict(raw_metadata)
            metadata["path"] = _safe_release_path(
                raw_metadata.get("path"),
                field=f"manifest.shards[{position}].metadata.path",
            )
            metadata["bytes"] = _require_int(
                raw_metadata.get("bytes"),
                field=f"manifest.shards[{position}].metadata.bytes",
                minimum=1,
            )
            metadata["sha256"] = _validate_digest(
                raw_metadata.get("sha256"),
                field=f"manifest.shards[{position}].metadata.sha256",
            )
            shard["metadata"] = metadata

        normalized_shards.append(shard)
        total_bodies += body_count

    declared_bodies = _require_int(
        manifest.get("body_count"), field="manifest.body_count", minimum=1
    )
    if declared_bodies != total_bodies:
        raise CatalogReleaseError(
            "manifest.body_count does not equal the sum of shard body counts"
        )

    for shard in normalized_shards:
        shard_path = _path_under(root, shard["path"])
        if not shard_path.is_file() or shard_path.is_symlink():
            raise CatalogReleaseError(f"Manifest shard is missing: {shard_path}")

        metadata_path_value = (
            shard["metadata"]["path"]
            if require_release_identity
            else _metadata_path_for_shard(shard["path"])
        )
        metadata_path = _path_under(root, metadata_path_value)
        if not metadata_path.is_file() or metadata_path.is_symlink():
            raise CatalogReleaseError(
                f"Per-shard metadata is missing for {shard['path']}: {metadata_path}"
            )
        metadata = _load_json_object(metadata_path, label="shard metadata")
        if metadata.get("shard") != shard["index"]:
            raise CatalogReleaseError(
                f"Metadata shard index disagrees for {shard['path']}"
            )
        if metadata.get("kernel") != PurePosixPath(shard["path"]).name:
            raise CatalogReleaseError(
                f"Metadata kernel name disagrees for {shard['path']}"
            )
        metadata_records = metadata.get("records")
        if not isinstance(metadata_records, list):
            raise CatalogReleaseError(
                f"Metadata records are missing for {shard['path']}"
            )
        metadata_bodies = [record.get("naif_id") for record in metadata_records]
        if metadata_bodies != shard["bodies"]:
            raise CatalogReleaseError(
                f"Metadata body order disagrees for {shard['path']}"
            )
        if metadata.get("kernel_bytes") != shard_path.stat().st_size:
            raise CatalogReleaseError(
                f"Metadata kernel byte count disagrees for {shard['path']}"
            )

    return normalized_shards, total_bodies


def _write_bytes_exclusive(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


def _receipt_bytes(records: Iterable[FileIdentity]) -> bytes:
    ordered = sorted(records, key=lambda record: record.path)
    return "".join(
        f"{record.sha256}  {record.path}\n" for record in ordered
    ).encode("utf-8")


def _parse_receipt(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise CatalogReleaseError(f"Unable to read checksum receipt {path}: {exc}") from exc
    for line_number, line in enumerate(lines, start=1):
        if len(line) < 67 or line[64:66] != "  ":
            raise CatalogReleaseError(
                f"Invalid SHA256SUMS syntax at line {line_number}"
            )
        digest = _validate_digest(
            line[:64], field=f"SHA256SUMS line {line_number} digest"
        )
        release_path = _safe_release_path(
            line[66:], field=f"SHA256SUMS line {line_number} path"
        )
        if release_path in entries:
            raise CatalogReleaseError(
                f"Duplicate path in checksum receipt: {release_path}"
            )
        entries[release_path] = digest
    if not entries:
        raise CatalogReleaseError("Checksum receipt is empty")
    return entries


def prepare_release(
    source_directory: str | Path,
    output_directory: str | Path,
    *,
    catalog_id: str,
    catalog_version: str,
    license_path: str | Path,
    notice_path: str | Path,
    support_files: Sequence[str] = (),
    included_files: Sequence[IncludedReleaseFile] = (),
    released_utc: str | None = None,
    source_revision: str | None = None,
) -> ReleaseVerification:
    """
    Copy and finalize an existing small-body catalog without rebuilding it.

    ``output_directory`` must not already exist.  All manifest-declared kernels
    and their per-shard metadata are required and are byte-identified.
    """

    source_root = Path(source_directory).resolve()
    output_root = Path(output_directory).resolve()
    catalog_id = _validate_identity(catalog_id, field="catalog ID")
    catalog_version = _validate_identity(catalog_version, field="catalog version")
    released_utc = _canonical_released_utc(released_utc)

    if not source_root.is_dir():
        raise CatalogReleaseError(f"Catalog source directory does not exist: {source_root}")
    if output_root.exists():
        raise CatalogReleaseError(
            f"Release output already exists and will not be overwritten: {output_root}"
        )
    if source_root == output_root or source_root in output_root.parents:
        raise CatalogReleaseError("Release output must not be inside the source catalog")

    source_manifest_path = source_root / "manifest.json"
    source_manifest_bytes = source_manifest_path.read_bytes()
    manifest = _load_json_object(source_manifest_path, label="catalog manifest")
    if "release" in manifest or "catalog_version" in manifest:
        raise CatalogReleaseError(
            "Source manifest is already release-finalized; verify it instead"
        )
    existing_catalog_id = manifest.get("catalog_id")
    if existing_catalog_id is not None and existing_catalog_id != catalog_id:
        raise CatalogReleaseError(
            f"Catalog ID {catalog_id!r} disagrees with source manifest "
            f"{existing_catalog_id!r}"
        )
    if not isinstance(manifest.get("provenance"), dict):
        raise CatalogReleaseError(
            "Source manifest must declare a provenance object before release"
        )

    shards, _ = _validate_manifest_structure(
        manifest,
        root=source_root,
        require_release_identity=False,
    )

    output_root.parent.mkdir(parents=True, exist_ok=True)
    temp_root = Path(
        tempfile.mkdtemp(prefix=f".{output_root.name}.", dir=output_root.parent)
    )
    try:
        enriched_shards: list[dict[str, Any]] = []
        receipt_records: list[FileIdentity] = []
        occupied_paths: set[str] = {"manifest.json", DEFAULT_RECEIPT_NAME}

        for shard in shards:
            shard_path = shard["path"]
            metadata_path = _metadata_path_for_shard(shard_path)
            for release_path in (shard_path, metadata_path):
                if release_path in occupied_paths:
                    raise CatalogReleaseError(
                        f"Release file path is declared more than once: {release_path}"
                    )
                occupied_paths.add(release_path)

            kernel_identity = _copy_and_hash(
                _path_under(source_root, shard_path),
                _path_under(temp_root, shard_path),
                release_path=shard_path,
                role="type13_kernel",
            )
            metadata_identity = _copy_and_hash(
                _path_under(source_root, metadata_path),
                _path_under(temp_root, metadata_path),
                release_path=metadata_path,
                role="shard_build_evidence",
            )
            receipt_records.extend((kernel_identity, metadata_identity))

            enriched = dict(shard)
            enriched["bytes"] = kernel_identity.bytes
            enriched["sha256"] = kernel_identity.sha256
            enriched["metadata"] = {
                "path": metadata_identity.path,
                "bytes": metadata_identity.bytes,
                "sha256": metadata_identity.sha256,
            }
            enriched_shards.append(enriched)

        release_files: list[FileIdentity] = []
        fixed_inputs = (
            (Path(license_path).resolve(), "LICENSE", "license"),
            (Path(notice_path).resolve(), "NOTICE.md", "provenance_notice"),
        )
        for source_path, release_path, role in fixed_inputs:
            if release_path in occupied_paths:
                raise CatalogReleaseError(
                    f"Release file path is declared more than once: {release_path}"
                )
            occupied_paths.add(release_path)
            identity = _copy_and_hash(
                source_path,
                _path_under(temp_root, release_path),
                release_path=release_path,
                role=role,
            )
            release_files.append(identity)
            receipt_records.append(identity)

        for raw_support_path in support_files:
            release_path = _safe_release_path(
                raw_support_path, field="support file path"
            )
            if release_path in occupied_paths:
                raise CatalogReleaseError(
                    f"Release file path is declared more than once: {release_path}"
                )
            occupied_paths.add(release_path)
            identity = _copy_and_hash(
                _path_under(source_root, release_path),
                _path_under(temp_root, release_path),
                release_path=release_path,
                role="catalog_build_evidence",
            )
            release_files.append(identity)
            receipt_records.append(identity)

        for included in included_files:
            release_path = _safe_release_path(
                included.release_path,
                field="included file release path",
            )
            role = _validate_identity(included.role, field="included file role")
            if release_path in occupied_paths:
                raise CatalogReleaseError(
                    f"Release file path is declared more than once: {release_path}"
                )
            occupied_paths.add(release_path)
            identity = _copy_and_hash(
                Path(included.source_path).resolve(),
                _path_under(temp_root, release_path),
                release_path=release_path,
                role=role,
            )
            release_files.append(identity)
            receipt_records.append(identity)

        finalized_manifest = dict(manifest)
        finalized_manifest["manifest_schema"] = MANIFEST_SCHEMA
        finalized_manifest["catalog_id"] = catalog_id
        finalized_manifest["catalog_version"] = catalog_version
        finalized_manifest["shards"] = enriched_shards
        release_payload: dict[str, Any] = {
            "released_utc": released_utc,
            "source_manifest_sha256": hashlib.sha256(source_manifest_bytes).hexdigest(),
            "integrity": {
                "algorithm": _HASH_ALGORITHM,
                "receipt": DEFAULT_RECEIPT_NAME,
                "receipt_scope": (
                    "manifest, kernels, per-shard metadata, and included support "
                    "files; the receipt itself is excluded"
                ),
            },
            "files": [
                identity.as_manifest_record()
                for identity in sorted(release_files, key=lambda item: item.path)
            ],
        }
        if source_revision is not None:
            if not source_revision.strip():
                raise CatalogReleaseError("source revision must not be blank")
            release_payload["source_revision"] = source_revision.strip()
        finalized_manifest["release"] = release_payload

        manifest_bytes = _json_bytes(finalized_manifest)
        manifest_path = temp_root / "manifest.json"
        _write_bytes_exclusive(manifest_path, manifest_bytes)
        manifest_identity = FileIdentity(
            path="manifest.json",
            bytes=len(manifest_bytes),
            sha256=hashlib.sha256(manifest_bytes).hexdigest(),
            role="catalog_manifest",
        )
        receipt_records.append(manifest_identity)
        _write_bytes_exclusive(
            temp_root / DEFAULT_RECEIPT_NAME,
            _receipt_bytes(receipt_records),
        )

        verification = verify_release(temp_root)
        temp_root.replace(output_root)
        return ReleaseVerification(
            root=output_root,
            catalog_id=verification.catalog_id,
            catalog_version=verification.catalog_version,
            file_count=verification.file_count,
            shard_count=verification.shard_count,
            body_count=verification.body_count,
            manifest_sha256=verification.manifest_sha256,
        )
    except Exception:
        shutil.rmtree(temp_root, ignore_errors=True)
        raise


def _manifest_release_records(
    manifest: Mapping[str, Any],
) -> tuple[list[FileIdentity], str]:
    records: list[FileIdentity] = []
    for shard in manifest["shards"]:
        records.append(
            FileIdentity(
                path=shard["path"],
                role="type13_kernel",
                bytes=shard["bytes"],
                sha256=shard["sha256"],
            )
        )
        metadata = shard["metadata"]
        records.append(
            FileIdentity(
                path=metadata["path"],
                role="shard_build_evidence",
                bytes=metadata["bytes"],
                sha256=metadata["sha256"],
            )
        )

    release = manifest.get("release")
    if not isinstance(release, dict):
        raise CatalogReleaseError("manifest.release must be an object")
    raw_released_utc = release.get("released_utc")
    if not isinstance(raw_released_utc, str):
        raise CatalogReleaseError(
            "manifest.release.released_utc must be an ISO-8601 UTC instant"
        )
    if _canonical_released_utc(raw_released_utc) != raw_released_utc:
        raise CatalogReleaseError(
            "manifest.release.released_utc must use canonical whole-second UTC form"
        )
    _validate_digest(
        release.get("source_manifest_sha256"),
        field="manifest.release.source_manifest_sha256",
    )
    source_revision = release.get("source_revision")
    if source_revision is not None and (
        not isinstance(source_revision, str) or not source_revision.strip()
    ):
        raise CatalogReleaseError(
            "manifest.release.source_revision must be a non-empty string"
        )
    integrity = release.get("integrity")
    if not isinstance(integrity, dict):
        raise CatalogReleaseError("manifest.release.integrity must be an object")
    if integrity.get("algorithm") != _HASH_ALGORITHM:
        raise CatalogReleaseError("Only SHA-256 catalog receipts are supported")
    receipt_path = _safe_release_path(
        integrity.get("receipt"), field="manifest.release.integrity.receipt"
    )
    if receipt_path != DEFAULT_RECEIPT_NAME:
        raise CatalogReleaseError(
            f"Release receipt must be named {DEFAULT_RECEIPT_NAME!r}"
        )
    raw_release_files = release.get("files")
    if not isinstance(raw_release_files, list):
        raise CatalogReleaseError("manifest.release.files must be a list")
    roles: list[str] = []
    for position, raw_record in enumerate(raw_release_files):
        if not isinstance(raw_record, dict):
            raise CatalogReleaseError(
                f"manifest.release.files[{position}] must be an object"
            )
        role = raw_record.get("role")
        if not isinstance(role, str) or not role:
            raise CatalogReleaseError(
                f"manifest.release.files[{position}].role must be non-empty"
            )
        roles.append(role)
        records.append(
            FileIdentity(
                path=_safe_release_path(
                    raw_record.get("path"),
                    field=f"manifest.release.files[{position}].path",
                ),
                role=role,
                bytes=_require_int(
                    raw_record.get("bytes"),
                    field=f"manifest.release.files[{position}].bytes",
                    minimum=1,
                ),
                sha256=_validate_digest(
                    raw_record.get("sha256"),
                    field=f"manifest.release.files[{position}].sha256",
                ),
            )
        )
    for required_role in ("license", "provenance_notice"):
        if roles.count(required_role) != 1:
            raise CatalogReleaseError(
                f"manifest.release.files must contain exactly one "
                f"{required_role!r} record"
            )
    return records, receipt_path


def verify_release(directory: str | Path) -> ReleaseVerification:
    """Verify every declared byte and structural invariant in a release."""

    root = Path(directory).resolve()
    if not root.is_dir():
        raise CatalogReleaseError(f"Release directory does not exist: {root}")
    manifest_path = root / "manifest.json"
    manifest = _load_json_object(manifest_path, label="release manifest")
    if manifest.get("manifest_schema") != MANIFEST_SCHEMA:
        raise CatalogReleaseError(
            f"Unsupported manifest schema: {manifest.get('manifest_schema')!r}"
        )
    catalog_id = _validate_identity(
        manifest.get("catalog_id"), field="manifest.catalog_id"
    )
    catalog_version = _validate_identity(
        manifest.get("catalog_version"), field="manifest.catalog_version"
    )
    _validate_manifest_structure(
        manifest,
        root=root,
        require_release_identity=True,
    )
    declared_records, receipt_path_value = _manifest_release_records(manifest)

    expected_records: dict[str, FileIdentity] = {}
    for record in declared_records:
        if record.path in expected_records:
            raise CatalogReleaseError(
                f"Release file is declared more than once: {record.path}"
            )
        expected_records[record.path] = record

    manifest_bytes_count, manifest_digest = _sha256_path(manifest_path)
    manifest_record = FileIdentity(
        path="manifest.json",
        role="catalog_manifest",
        bytes=manifest_bytes_count,
        sha256=manifest_digest,
    )
    if manifest_record.path in expected_records:
        raise CatalogReleaseError("manifest.json must not be listed in release.files")
    expected_records[manifest_record.path] = manifest_record

    receipt_path = _path_under(root, receipt_path_value)
    receipt_entries = _parse_receipt(receipt_path)
    if set(receipt_entries) != set(expected_records):
        missing = sorted(set(expected_records) - set(receipt_entries))
        unexpected = sorted(set(receipt_entries) - set(expected_records))
        raise CatalogReleaseError(
            f"Checksum receipt scope disagrees with the manifest; "
            f"missing={missing}, unexpected={unexpected}"
        )

    for release_path, record in expected_records.items():
        file_path = _path_under(root, release_path)
        if not file_path.is_file() or file_path.is_symlink():
            raise CatalogReleaseError(f"Release file is missing: {file_path}")
        actual_size, actual_digest = _sha256_path(file_path)
        if actual_size != record.bytes:
            raise CatalogReleaseError(
                f"Byte count mismatch for {release_path}: "
                f"expected {record.bytes}, found {actual_size}"
            )
        if actual_digest != record.sha256:
            raise CatalogReleaseError(f"Manifest SHA-256 mismatch for {release_path}")
        if receipt_entries[release_path] != actual_digest:
            raise CatalogReleaseError(f"Receipt SHA-256 mismatch for {release_path}")

    actual_files: set[str] = set()
    for path in root.rglob("*"):
        if path.is_symlink():
            raise CatalogReleaseError(f"Release contains a symbolic link: {path}")
        if path.is_file():
            actual_files.add(path.relative_to(root).as_posix())
    expected_files = set(expected_records)
    expected_files.add(receipt_path_value)
    if actual_files != expected_files:
        missing = sorted(expected_files - actual_files)
        unexpected = sorted(actual_files - expected_files)
        raise CatalogReleaseError(
            f"Release directory contains unreceipted or missing files; "
            f"missing={missing}, unexpected={unexpected}"
        )

    return ReleaseVerification(
        root=root,
        catalog_id=catalog_id,
        catalog_version=catalog_version,
        file_count=len(actual_files),
        shard_count=manifest["shard_count"],
        body_count=manifest["body_count"],
        manifest_sha256=manifest_digest,
    )


def _zip_timestamp(released_utc: str) -> tuple[int, int, int, int, int, int]:
    instant = datetime.fromisoformat(released_utc[:-1] + "+00:00")
    if instant.year < 1980:
        raise CatalogReleaseError("ZIP releases require a release year of 1980 or later")
    return (
        instant.year,
        instant.month,
        instant.day,
        instant.hour,
        instant.minute,
        instant.second,
    )


def create_release_archive(
    release_directory: str | Path,
    archive_path: str | Path,
) -> ArchiveIdentity:
    """Create a deterministic stored ZIP and an adjacent SHA-256 receipt."""

    verification = verify_release(release_directory)
    root = verification.root
    archive = Path(archive_path).resolve()
    checksum_path = archive.with_name(archive.name + ".sha256")
    if archive.exists() or checksum_path.exists():
        raise CatalogReleaseError(
            f"Archive output already exists and will not be overwritten: {archive}"
        )
    archive.parent.mkdir(parents=True, exist_ok=True)

    manifest = _load_json_object(root / "manifest.json", label="release manifest")
    date_time = _zip_timestamp(manifest["release"]["released_utc"])
    receipt_entries = _parse_receipt(root / DEFAULT_RECEIPT_NAME)
    archive_files = sorted((*receipt_entries.keys(), DEFAULT_RECEIPT_NAME))
    prefix = root.name

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{archive.name}.", dir=archive.parent
    )
    os.close(descriptor)
    temporary_archive = Path(temporary_name)
    try:
        with zipfile.ZipFile(
            temporary_archive,
            mode="w",
            compression=zipfile.ZIP_STORED,
            allowZip64=True,
        ) as bundle:
            for release_path in archive_files:
                source_path = _path_under(root, release_path)
                archive_name = f"{prefix}/{release_path}"
                info = zipfile.ZipInfo(archive_name, date_time=date_time)
                info.compress_type = zipfile.ZIP_STORED
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                with source_path.open("rb") as source, bundle.open(info, "w") as target:
                    shutil.copyfileobj(source, target, length=_COPY_CHUNK_BYTES)
        archive_size, archive_digest = _sha256_path(temporary_archive)
        temporary_archive.replace(archive)
        _write_bytes_exclusive(
            checksum_path,
            f"{archive_digest}  {archive.name}\n".encode("utf-8"),
        )
        return ArchiveIdentity(
            path=archive,
            bytes=archive_size,
            sha256=archive_digest,
            checksum_path=checksum_path,
        )
    except Exception:
        temporary_archive.unlink(missing_ok=True)
        archive.unlink(missing_ok=True)
        checksum_path.unlink(missing_ok=True)
        raise


def verify_archive_checksum(
    archive_path: str | Path,
    checksum_path: str | Path | None = None,
) -> ArchiveIdentity:
    """Verify an archive against its adjacent single-entry SHA-256 receipt."""

    archive = Path(archive_path).resolve()
    receipt = (
        Path(checksum_path).resolve()
        if checksum_path is not None
        else archive.with_name(archive.name + ".sha256")
    )
    if not archive.is_file() or archive.is_symlink():
        raise CatalogReleaseError(f"Release archive is missing: {archive}")
    entries = _parse_receipt(receipt)
    if entries.keys() != {archive.name}:
        raise CatalogReleaseError(
            f"Archive checksum must contain exactly {archive.name!r}"
        )
    size, digest = _sha256_path(archive)
    if entries[archive.name] != digest:
        raise CatalogReleaseError(f"Archive SHA-256 mismatch: {archive}")
    try:
        with zipfile.ZipFile(archive, "r") as bundle:
            corrupt_member = bundle.testzip()
    except zipfile.BadZipFile as exc:
        raise CatalogReleaseError(f"Release archive is not a valid ZIP: {archive}") from exc
    if corrupt_member is not None:
        raise CatalogReleaseError(
            f"Release archive contains a corrupt member: {corrupt_member}"
        )
    return ArchiveIdentity(
        path=archive,
        bytes=size,
        sha256=digest,
        checksum_path=receipt,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare and verify immutable Moira small-body catalog releases."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser(
        "prepare", help="copy and byte-identify an existing catalog"
    )
    prepare.add_argument("source_directory", type=Path)
    prepare.add_argument("output_directory", type=Path)
    prepare.add_argument("--catalog-id", required=True)
    prepare.add_argument("--catalog-version", required=True)
    prepare.add_argument("--released-utc")
    prepare.add_argument("--source-revision")
    prepare.add_argument("--license", dest="license_path", type=Path, required=True)
    prepare.add_argument("--notice", dest="notice_path", type=Path, required=True)
    prepare.add_argument("--support-file", action="append", default=[])
    prepare.add_argument(
        "--include-file",
        action="append",
        nargs=3,
        default=[],
        metavar=("SOURCE", "RELEASE_PATH", "ROLE"),
        help=(
            "include an explicitly located file under a canonical release path "
            "and role; may be repeated"
        ),
    )
    prepare.add_argument("--archive", type=Path)

    verify = subparsers.add_parser("verify", help="verify an extracted release")
    verify.add_argument("release_directory", type=Path)

    verify_archive = subparsers.add_parser(
        "verify-archive", help="verify a ZIP against its adjacent SHA-256 receipt"
    )
    verify_archive.add_argument("archive_path", type=Path)
    verify_archive.add_argument("--checksum", dest="checksum_path", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "prepare":
        verification = prepare_release(
            args.source_directory,
            args.output_directory,
            catalog_id=args.catalog_id,
            catalog_version=args.catalog_version,
            license_path=args.license_path,
            notice_path=args.notice_path,
            support_files=args.support_file,
            included_files=tuple(
                IncludedReleaseFile(
                    source_path=Path(source),
                    release_path=release_path,
                    role=role,
                )
                for source, release_path, role in args.include_file
            ),
            released_utc=args.released_utc,
            source_revision=args.source_revision,
        )
        print(
            f"prepared {verification.catalog_id} {verification.catalog_version}: "
            f"{verification.shard_count} shards, {verification.body_count} bodies, "
            f"{verification.file_count} files"
        )
        print(f"manifest sha256: {verification.manifest_sha256}")
        if args.archive is not None:
            archive = create_release_archive(verification.root, args.archive)
            print(f"archive sha256: {archive.sha256}  {archive.path}")
        return 0
    if args.command == "verify":
        verification = verify_release(args.release_directory)
        print(
            f"verified {verification.catalog_id} {verification.catalog_version}: "
            f"{verification.shard_count} shards, {verification.body_count} bodies, "
            f"{verification.file_count} files"
        )
        print(f"manifest sha256: {verification.manifest_sha256}")
        return 0
    if args.command == "verify-archive":
        archive = verify_archive_checksum(args.archive_path, args.checksum_path)
        print(f"verified archive sha256: {archive.sha256}  {archive.path}")
        return 0
    raise AssertionError(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
