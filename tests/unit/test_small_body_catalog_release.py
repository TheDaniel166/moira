import hashlib
import json
from pathlib import Path

import pytest

from moira.small_body_catalog_release import (
    CatalogReleaseError,
    IncludedReleaseFile,
    create_release_archive,
    prepare_release,
    verify_archive_checksum,
    verify_release,
)


_RELEASED_UTC = "2026-07-27T12:00:00Z"


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _make_source(tmp_path: Path) -> tuple[Path, Path, Path]:
    source = tmp_path / "source"
    source.mkdir()
    shard_specs = (
        (0, "asteroid_shard_000.bsp", [2000001, 2000002], b"first-kernel"),
        (1, "asteroid_shard_001.bsp", [2000003], b"second-kernel"),
    )
    shards = []
    for index, name, bodies, payload in shard_specs:
        kernel_path = source / name
        kernel_path.write_bytes(payload)
        metadata_path = kernel_path.with_suffix(".metadata.json")
        _write_json(
            metadata_path,
            {
                "shard": index,
                "kernel": name,
                "kernel_bytes": len(payload),
                "records": [
                    {"number": body - 2_000_000, "naif_id": body}
                    for body in bodies
                ],
                "failures": [],
            },
        )
        shards.append(
            {
                "index": index,
                "path": name,
                "body_count": len(bodies),
                "bodies": bodies,
            }
        )
    _write_json(
        source / "manifest.json",
        {
            "manifest_schema": "moira.small-body-catalog/v1",
            "catalog_id": "moira-asteroids",
            "source": "MOIRA UNIFIED ASTEROID CATALOG (JPL Horizons)",
            "provenance": {
                "artifact_author": "Moira",
                "trajectory_source": "JPL Horizons VECTORS",
            },
            "body_count": 3,
            "shard_count": 2,
            "shards": shards,
        },
    )
    _write_json(source / "unified_master.json", {"built": 3, "failed": 0})
    license_path = tmp_path / "LICENSE"
    license_path.write_text("MIT License\n", encoding="utf-8")
    notice_path = tmp_path / "NOTICE.source.md"
    notice_path.write_text("Moira-generated Type-13 BSP files.\n", encoding="utf-8")
    return source, license_path, notice_path


def _prepare(tmp_path: Path, *, output_name: str = "moira-asteroids-2026.07.27.1"):
    source, license_path, notice_path = _make_source(tmp_path)
    output = tmp_path / output_name
    result = prepare_release(
        source,
        output,
        catalog_id="moira-asteroids",
        catalog_version="2026.07.27.1",
        license_path=license_path,
        notice_path=notice_path,
        support_files=("unified_master.json",),
        released_utc=_RELEASED_UTC,
        source_revision="test-revision",
    )
    return source, output, result


def test_prepare_release_embeds_per_file_identity_and_verifies(tmp_path: Path) -> None:
    source, output, result = _prepare(tmp_path)

    assert result.catalog_id == "moira-asteroids"
    assert result.catalog_version == "2026.07.27.1"
    assert result.shard_count == 2
    assert result.body_count == 3
    assert result.file_count == 9
    assert not (source / "SHA256SUMS").exists()

    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    first_shard = manifest["shards"][0]
    assert first_shard["bytes"] == len(b"first-kernel")
    assert first_shard["sha256"] == hashlib.sha256(b"first-kernel").hexdigest()
    assert first_shard["metadata"]["path"] == (
        "asteroid_shard_000.metadata.json"
    )
    assert manifest["release"]["integrity"]["algorithm"] == "sha256"
    assert manifest["release"]["source_revision"] == "test-revision"
    assert {
        record["path"] for record in manifest["release"]["files"]
    } == {"LICENSE", "NOTICE.md", "unified_master.json"}

    verified = verify_release(output)
    assert verified.manifest_sha256 == result.manifest_sha256


def test_prepare_release_refuses_to_overwrite_identity(tmp_path: Path) -> None:
    _source, output, _result = _prepare(tmp_path)

    with pytest.raises(CatalogReleaseError, match="will not be overwritten"):
        prepare_release(
            tmp_path / "source",
            output,
            catalog_id="moira-asteroids",
            catalog_version="2026.07.27.1",
            license_path=tmp_path / "LICENSE",
            notice_path=tmp_path / "NOTICE.source.md",
            released_utc=_RELEASED_UTC,
        )


def test_prepare_release_receipts_an_explicit_external_file(tmp_path: Path) -> None:
    source, license_path, notice_path = _make_source(tmp_path)
    alias_source = tmp_path / "identity" / "comet_catalog_aliases.json"
    _write_json(alias_source, {"aliases": [{"alias": "Halley"}]})
    output = tmp_path / "release"

    result = prepare_release(
        source,
        output,
        catalog_id="moira-asteroids",
        catalog_version="2026.07.27.1",
        license_path=license_path,
        notice_path=notice_path,
        included_files=(
            IncludedReleaseFile(
                source_path=alias_source,
                release_path="identity/comet_catalog_aliases.json",
                role="identity_alias_policy",
            ),
        ),
        released_utc=_RELEASED_UTC,
    )

    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    identity_record = next(
        record
        for record in manifest["release"]["files"]
        if record["role"] == "identity_alias_policy"
    )
    assert identity_record["path"] == "identity/comet_catalog_aliases.json"
    assert identity_record["sha256"] == hashlib.sha256(
        alias_source.read_bytes()
    ).hexdigest()
    assert (
        output / "identity" / "comet_catalog_aliases.json"
    ).read_bytes() == alias_source.read_bytes()
    assert verify_release(output).manifest_sha256 == result.manifest_sha256


def test_prepare_release_rejects_duplicate_included_file_path(
    tmp_path: Path,
) -> None:
    source, license_path, notice_path = _make_source(tmp_path)

    with pytest.raises(CatalogReleaseError, match="declared more than once"):
        prepare_release(
            source,
            tmp_path / "release",
            catalog_id="moira-asteroids",
            catalog_version="2026.07.27.1",
            license_path=license_path,
            notice_path=notice_path,
            included_files=(
                IncludedReleaseFile(
                    source_path=license_path,
                    release_path="LICENSE",
                    role="duplicate_license",
                ),
            ),
            released_utc=_RELEASED_UTC,
        )


def test_verify_release_fails_closed_after_kernel_tampering(tmp_path: Path) -> None:
    _source, output, _result = _prepare(tmp_path)
    (output / "asteroid_shard_001.bsp").write_bytes(b"tampered")

    with pytest.raises(CatalogReleaseError, match="byte count"):
        verify_release(output)


def test_verify_release_requires_license_and_provenance_notice(tmp_path: Path) -> None:
    _source, output, _result = _prepare(tmp_path)
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["release"]["files"] = [
        record
        for record in manifest["release"]["files"]
        if record["role"] != "provenance_notice"
    ]
    _write_json(manifest_path, manifest)

    with pytest.raises(CatalogReleaseError, match="provenance_notice"):
        verify_release(output)


def test_prepare_release_rejects_manifest_path_escape(tmp_path: Path) -> None:
    source, license_path, notice_path = _make_source(tmp_path)
    manifest_path = source / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["shards"][0]["path"] = "../outside.bsp"
    _write_json(manifest_path, manifest)

    with pytest.raises(CatalogReleaseError, match="escapes the catalog root"):
        prepare_release(
            source,
            tmp_path / "release",
            catalog_id="moira-asteroids",
            catalog_version="2026.07.27.1",
            license_path=license_path,
            notice_path=notice_path,
            released_utc=_RELEASED_UTC,
        )


def test_archive_is_byte_pinned_and_reproducible(tmp_path: Path) -> None:
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first_root.mkdir()
    second_root.mkdir()
    _source_a, release_a, _result_a = _prepare(first_root)
    _source_b, release_b, _result_b = _prepare(second_root)

    archive_a = create_release_archive(release_a, tmp_path / "first.zip")
    archive_b = create_release_archive(release_b, tmp_path / "second.zip")

    assert archive_a.sha256 == archive_b.sha256
    assert archive_a.bytes == archive_b.bytes
    assert verify_archive_checksum(archive_a.path).sha256 == archive_a.sha256


def test_verify_archive_rejects_checksum_drift(tmp_path: Path) -> None:
    _source, output, _result = _prepare(tmp_path)
    archive = create_release_archive(output, tmp_path / "release.zip")
    archive.path.write_bytes(archive.path.read_bytes() + b"drift")

    with pytest.raises(CatalogReleaseError, match="Archive SHA-256 mismatch"):
        verify_archive_checksum(archive.path)
