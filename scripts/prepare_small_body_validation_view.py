"""Seal a local, unpublished catalog view for release-bound integration tests.

Only BSP copies are replaced by same-volume hard links during the existing
release preparer's copy step. All hashing, ledgers, metadata copying and release
verification remain real. The input must stay unchanged while this view is in
use; shared kernel storage makes this unsuitable for publishing an immutable
release. Versions are deliberately restricted to validation-only identities.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from moira import small_body_catalog_release as release  # noqa: E402


def prepare_validation_view(
    source: Path,
    output: Path,
    *,
    catalog_id: str,
    catalog_version: str,
    license_path: Path,
    notice_path: Path,
    support_files: tuple[str, ...] = (),
    included_files: tuple[release.IncludedReleaseFile, ...] = (),
    released_utc: str | None = None,
) -> release.ReleaseVerification:
    if ".validation" not in catalog_version:
        raise release.CatalogReleaseError(
            "Hard-linked views require an explicit .validation version; "
            "they must never be published as immutable catalog releases"
        )
    ordinary_copy = release._copy_and_hash

    def link_kernel(source_path, destination, *, release_path, role):
        if role != "type13_kernel":
            return ordinary_copy(
                source_path, destination, release_path=release_path, role=role
            )
        if not source_path.is_file() or source_path.is_symlink():
            raise release.CatalogReleaseError(
                f"Validation kernel is not a regular file: {source_path}"
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.link(source_path, destination)
        size, digest = release._sha256_path(destination)
        return release.FileIdentity(release_path, size, digest, role)

    # This is a sequential, tests-only disk-storage adapter, not a replacement
    # for the production verifier or an accuracy/admission override.
    with patch.object(release, "_copy_and_hash", link_kernel):
        return release.prepare_release(
            source,
            output,
            catalog_id=catalog_id,
            catalog_version=catalog_version,
            license_path=license_path,
            notice_path=notice_path,
            support_files=support_files,
            included_files=included_files,
            released_utc=released_utc,
            source_revision="validation-only view of an uncommitted worktree",
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--catalog-id", required=True)
    parser.add_argument("--catalog-version", required=True)
    parser.add_argument("--support-file", action="append", default=[])
    parser.add_argument("--include-file", nargs=3, action="append", default=[])
    args = parser.parse_args()
    result = prepare_validation_view(
        args.source,
        args.output,
        catalog_id=args.catalog_id,
        catalog_version=args.catalog_version,
        license_path=REPO_ROOT / "LICENSE",
        notice_path=REPO_ROOT / "moira/kernels/SMALL_BODY_CATALOG_NOTICE.md",
        support_files=tuple(args.support_file),
        included_files=tuple(
            release.IncludedReleaseFile(Path(source), path, role)
            for source, path, role in args.include_file
        ),
    )
    print(result, flush=True)


if __name__ == "__main__":
    main()
