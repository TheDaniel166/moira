"""Finalize and seal the staged expanded Moira asteroid release.

Enriches manifest.json with byte counts and SHA-256 hashes for all 449 shards,
binds the admitted target list, expansion receipt, LICENSE, and NOTICE,
generates the SHA256SUMS ledger, and executes verify_release.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from moira.small_body_catalog_release import verify_release  # noqa: E402


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    release_dir = Path(r"c:\dev\moira-asteroid-releases\moira-asteroids-2026.09.18.1")
    staging_base = Path(r"c:\dev\moira-asteroid-releases")

    print(f"Finalizing release at {release_dir}...")

    # 1. Bind support files
    targets_source = staging_base / "moira_public_expanded_asteroid_targets.json"
    targets_dest = release_dir / "moira_public_asteroid_targets.json"
    shutil.copy2(targets_source, targets_dest)

    receipt_source = staging_base / "moira_expansion_1198_metadata.json"
    receipt_dest = release_dir / "moira_public_11223_expansion_receipt.json"
    shutil.copy2(receipt_source, receipt_dest)

    shutil.copy2(REPO_ROOT / "LICENSE", release_dir / "LICENSE")
    shutil.copy2(
        REPO_ROOT / "moira" / "kernels" / "SMALL_BODY_CATALOG_NOTICE.md",
        release_dir / "NOTICE.md",
    )

    # 2. Read existing manifest
    manifest_path = release_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    # Clean out old release block to get clean builder manifest
    manifest.pop("release", None)
    manifest.pop("catalog_version", None)

    enriched_shards: list[dict] = []
    shards_list = manifest["shards"]
    print(f"Enriching {len(shards_list)} shards...")
    for s in shards_list:
        kpath = release_dir / s["path"]
        mpath = release_dir / f"asteroid_shard_{s['index']:03d}.metadata.json"
        if not kpath.is_file():
            raise FileNotFoundError(kpath)
        if not mpath.is_file():
            raise FileNotFoundError(mpath)

        kb_len = kpath.stat().st_size
        kb_sha = s.get("sha256")
        if not kb_sha or kb_len != s.get("bytes"):
            kb_sha = sha256_file(kpath)

        mb_len = mpath.stat().st_size
        mb_sha = s.get("metadata", {}).get("sha256")
        if not mb_sha or mb_len != s.get("metadata", {}).get("bytes"):
            mb_sha = sha256_file(mpath)

        enriched_shards.append({
            "index": s["index"],
            "path": s["path"],
            "body_count": s["body_count"],
            "bodies": s["bodies"],
            "bytes": kb_len,
            "sha256": kb_sha,
            "metadata": {
                "path": mpath.name,
                "bytes": mb_len,
                "sha256": mb_sha,
            },
        })

    manifest["shards"] = enriched_shards
    manifest["catalog_id"] = "moira-asteroids"

    # Compute source manifest hash
    source_manifest_bytes = (json.dumps(manifest, indent=2) + "\n").encode("utf-8")
    source_manifest_sha256 = hashlib.sha256(source_manifest_bytes).hexdigest()

    # Build support files list
    support_files_to_bind = [
        (release_dir / "LICENSE", "LICENSE", "license"),
        (release_dir / "NOTICE.md", "NOTICE.md", "provenance_notice"),
        (
            release_dir / "moira_public_11223_expansion_receipt.json",
            "moira_public_11223_expansion_receipt.json",
            "catalog_build_evidence",
        ),
        (
            release_dir / "moira_public_asteroid_targets.json",
            "moira_public_asteroid_targets.json",
            "catalog_build_evidence",
        ),
        (
            release_dir / "unified_master.json",
            "unified_master.json",
            "catalog_build_evidence",
        ),
    ]

    release_file_records = []
    receipt_lines: dict[str, str] = {}

    for file_path, rel_path, role in support_files_to_bind:
        flen = file_path.stat().st_size
        fsha = sha256_file(file_path)
        release_file_records.append({
            "path": rel_path,
            "role": role,
            "bytes": flen,
            "sha256": fsha,
        })
        receipt_lines[rel_path] = fsha

    # Add shards to receipt_lines
    for s in enriched_shards:
        receipt_lines[s["path"]] = s["sha256"]
        receipt_lines[s["metadata"]["path"]] = s["metadata"]["sha256"]

    # Finalize release block in manifest
    manifest["catalog_version"] = "2026.09.18.1"
    manifest["release"] = {
        "released_utc": "2026-09-18T00:00:00Z",
        "source_manifest_sha256": source_manifest_sha256,
        "integrity": {
            "algorithm": "sha256",
            "receipt": "SHA256SUMS",
            "receipt_scope": (
                "manifest, kernels, per-shard metadata, and included support files; "
                "the receipt itself is excluded"
            ),
        },
        "files": release_file_records,
        "source_revision": "92ce4257-builder9c705620-target676ca3b0",
    }

    # Write finalized manifest
    final_manifest_bytes = (json.dumps(manifest, indent=2) + "\n").encode("utf-8")
    manifest_path.write_bytes(final_manifest_bytes)
    manifest_sha = hashlib.sha256(final_manifest_bytes).hexdigest()
    receipt_lines["manifest.json"] = manifest_sha

    # Write SHA256SUMS
    sha256sums_path = release_dir / "SHA256SUMS"
    sha256sums_content = "".join(
        f"{receipt_lines[path]}  {path}\n"
        for path in sorted(receipt_lines.keys())
    )
    sha256sums_path.write_text(sha256sums_content, encoding="utf-8")

    print(f"Receipt written with {len(receipt_lines)} entries.")
    print("Running verify_release...")
    verification = verify_release(release_dir)
    print("SUCCESS!")
    print(
        f"Verified: catalog={verification.catalog_id}, "
        f"version={verification.catalog_version}, "
        f"shards={verification.shard_count}, "
        f"bodies={verification.body_count}, "
        f"files={verification.file_count}, "
        f"manifest_sha256={verification.manifest_sha256}"
    )


if __name__ == "__main__":
    main()
