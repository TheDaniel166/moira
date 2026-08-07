"""Build a deterministic release archive for a physical-visibility data pack.

The visibility pack is a separately licensed runtime resource.  It is never
embedded in the ``moira-astro`` wheel and is never downloaded by the engine.
This tool validates the manifest-owned inventory and emits a reproducible
``tar.gz`` that can be published beside an engine release.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import tarfile
from pathlib import Path
from typing import Any, Iterable


_MANIFEST_SCHEMAS = frozenset({
    "moira.physical-heliacal-visibility-data-pack-manifest/v1",
})
_RECEIPT_SCHEMA = "moira.physical-visibility.data-pack-release-receipt/v1"


class PhysicalVisibilityPackReleaseError(ValueError):
    """Raised when a candidate pack cannot become a release artifact."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_manifest(directory: Path) -> dict[str, Any]:
    manifest_path = directory / "manifest.json"
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PhysicalVisibilityPackReleaseError(
            f"cannot read visibility manifest: {manifest_path}"
        ) from exc
    if (
        not isinstance(payload, dict)
        or payload.get("schema") not in _MANIFEST_SCHEMAS
    ):
        raise PhysicalVisibilityPackReleaseError(
            "physical-visibility resource manifest schema is not admitted"
        )
    return payload


def _manifest_inventory(
    directory: Path, manifest: dict[str, Any]
) -> tuple[Path, ...]:
    declared = manifest.get("payload_files")
    if not isinstance(declared, list) or not declared:
        raise PhysicalVisibilityPackReleaseError(
            "visibility manifest has no payload inventory"
        )

    names = ["manifest.json"]
    for item in declared:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            raise PhysicalVisibilityPackReleaseError(
                "visibility manifest payload entry is malformed"
            )
        name = item["path"]
        candidate = Path(name)
        if candidate.is_absolute() or candidate.parts != (name,):
            raise PhysicalVisibilityPackReleaseError(
                f"visibility payload path is not a root file: {name!r}"
            )
        names.append(name)

    if len(names) != len(set(names)):
        raise PhysicalVisibilityPackReleaseError(
            "visibility manifest payload inventory contains duplicates"
        )

    expected = set(names)
    actual: set[str] = set()
    for path in directory.iterdir():
        if path.is_symlink():
            raise PhysicalVisibilityPackReleaseError(
                f"visibility pack contains a symlink: {path.name}"
            )
        if not path.is_file():
            raise PhysicalVisibilityPackReleaseError(
                f"visibility pack contains a non-file entry: {path.name}"
            )
        actual.add(path.name)
    if actual != expected:
        missing = sorted(expected - actual)
        unexpected = sorted(actual - expected)
        raise PhysicalVisibilityPackReleaseError(
            "visibility pack inventory differs from manifest: "
            f"missing={missing}, unexpected={unexpected}"
        )

    by_name = {
        item["path"]: item
        for item in declared
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    }
    for name, item in by_name.items():
        path = directory / name
        if path.stat().st_size != item.get("bytes"):
            raise PhysicalVisibilityPackReleaseError(
                f"visibility payload byte length differs: {name}"
            )
        if _sha256(path) != item.get("sha256"):
            raise PhysicalVisibilityPackReleaseError(
                f"visibility payload checksum differs: {name}"
            )

    return tuple(directory / name for name in sorted(expected))


def _normalized_tar_info(path: Path, archive_name: str) -> tarfile.TarInfo:
    info = tarfile.TarInfo(archive_name)
    info.size = path.stat().st_size
    info.mode = 0o644
    info.mtime = 0
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    return info


def _write_deterministic_archive(
    files: Iterable[Path], output: Path, root_name: str
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
            with tarfile.open(
                fileobj=zipped,
                mode="w",
                format=tarfile.PAX_FORMAT,
            ) as archive:
                for path in files:
                    info = _normalized_tar_info(
                        path, f"{root_name}/{path.name}"
                    )
                    with path.open("rb") as stream:
                        archive.addfile(info, stream)


def build_release_archive(directory: Path, output: Path) -> dict[str, Any]:
    """Validate *directory*, build *output*, and return its release receipt."""

    directory = directory.resolve()
    output = output.resolve()
    if not directory.is_dir():
        raise PhysicalVisibilityPackReleaseError(
            f"visibility data-pack directory does not exist: {directory}"
        )
    manifest = _load_manifest(directory)
    files = _manifest_inventory(directory, manifest)

    pack_id = manifest.get("pack_id")
    version = manifest.get("version")
    if not isinstance(pack_id, str) or not isinstance(version, str):
        raise PhysicalVisibilityPackReleaseError(
            "visibility manifest has no pack identity"
        )
    root_name = f"{pack_id}-{version}"
    _write_deterministic_archive(files, output, root_name)

    return {
        "schema": _RECEIPT_SCHEMA,
        "status": "complete_deterministic_external_release_artifact",
        "pack": {
            "pack_id": pack_id,
            "version": version,
            "license": manifest.get("license"),
            "manifest_sha256": _sha256(directory / "manifest.json"),
            "source_artifact_manifest_sha256": (
                manifest.get("source_artifact", {})
                .get("manifest", {})
                .get("sha256")
            ),
        },
        "archive": {
            "filename": output.name,
            "bytes": output.stat().st_size,
            "sha256": _sha256(output),
            "root_directory": root_name,
            "file_count": len(files),
            "normalization": {
                "entry_order": "lexicographic_filename",
                "gzip_mtime": 0,
                "tar_mtime": 0,
                "uid": 0,
                "gid": 0,
                "file_mode": "0644",
            },
        },
        "runtime_boundary": {
            "embedded_in_python_distribution": False,
            "automatic_download_allowed": False,
            "caller_or_server_supplied_directory_required": True,
        },
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-pack", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--receipt", type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    receipt = build_release_archive(args.data_pack, args.output)
    rendered = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.receipt is not None:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
