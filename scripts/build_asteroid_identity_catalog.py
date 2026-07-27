"""Build Moira's packaged asteroid name-to-NAIF identity registry.

The input is one finalized sovereign asteroid release.  The release manifest,
its unified build ledger, and its admitted target list jointly define the
catalog boundary.  This script does not query the network and does not infer
names from orbital data.

The emitted registry is canonical identity metadata, not an ephemeris.  Each
entry binds the JPL Horizons target name captured during the release build to
the NAIF small-body convention ``2_000_000 + MPC catalog number``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import unicodedata
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "moira" / "data" / "asteroid_catalog_naif.json"
DEFAULT_METADATA_OUTPUT = (
    REPO_ROOT / "moira" / "data" / "asteroid_catalog_naif.metadata.json"
)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _release_file_spec(manifest: dict[str, Any], relative_path: str) -> dict[str, Any]:
    for item in manifest.get("release", {}).get("files", []):
        if item.get("path") == relative_path:
            return item
    raise ValueError(f"release manifest does not bind {relative_path!r}")


def _verify_bound_file(
    release_dir: Path,
    manifest: dict[str, Any],
    relative_path: str,
) -> Path:
    spec = _release_file_spec(manifest, relative_path)
    path = release_dir / relative_path
    if not path.is_file():
        raise FileNotFoundError(path)
    actual_bytes = path.stat().st_size
    actual_sha256 = _sha256_file(path)
    if actual_bytes != int(spec["bytes"]):
        raise ValueError(
            f"{relative_path} byte count {actual_bytes} != manifest {spec['bytes']}"
        )
    if actual_sha256 != str(spec["sha256"]):
        raise ValueError(
            f"{relative_path} SHA-256 {actual_sha256} != manifest {spec['sha256']}"
        )
    return path


def build_catalog(
    release_dir: Path,
    *,
    expected_manifest_sha256: str | None = None,
) -> tuple[bytes, bytes]:
    """Return deterministic registry and provenance metadata bytes."""
    release_dir = release_dir.resolve()
    manifest_path = release_dir / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)

    manifest_sha256 = _sha256_file(manifest_path)
    if (
        expected_manifest_sha256 is not None
        and manifest_sha256 != expected_manifest_sha256.lower()
    ):
        raise ValueError(
            f"release manifest SHA-256 {manifest_sha256} != expected "
            f"{expected_manifest_sha256.lower()}"
        )

    manifest = _read_json(manifest_path)
    master_path = _verify_bound_file(release_dir, manifest, "unified_master.json")
    targets_path = _verify_bound_file(
        release_dir,
        manifest,
        "moira_public_asteroid_targets.json",
    )
    master = _read_json(master_path)
    targets = _read_json(targets_path)

    if manifest.get("catalog_id") != "moira-asteroids":
        raise ValueError(f"unexpected catalog_id: {manifest.get('catalog_id')!r}")
    if int(master.get("failed", -1)) != 0:
        raise ValueError(f"unified master records failures: {master.get('failed')!r}")

    records = master.get("records")
    if not isinstance(records, list):
        raise ValueError("unified master records must be a list")
    if not isinstance(targets, list):
        raise ValueError("admitted targets must be a list")

    expected_count = int(manifest["body_count"])
    if len(records) != expected_count:
        raise ValueError(
            f"unified master has {len(records)} records, expected {expected_count}"
        )
    if len(targets) != expected_count:
        raise ValueError(
            f"admitted target list has {len(targets)} records, expected {expected_count}"
        )
    if int(master.get("requested", -1)) != expected_count:
        raise ValueError("unified master requested count does not match manifest")
    if int(master.get("built", -1)) != expected_count:
        raise ValueError("unified master built count does not match manifest")

    target_numbers = [int(target["number"]) for target in targets]
    record_numbers = [int(record["number"]) for record in records]
    if target_numbers != record_numbers:
        raise ValueError("unified master record order does not match admitted targets")

    catalog: dict[str, int] = {}
    seen_ids: set[int] = set()
    seen_casefold_names: dict[str, str] = {}
    for record in records:
        number = int(record["number"])
        naif_id = int(record["naif_id"])
        name = record["name"]
        if not isinstance(name, str) or not name or name != name.strip():
            raise ValueError(f"invalid canonical name for asteroid {number}: {name!r}")
        if unicodedata.normalize("NFC", name) != name:
            raise ValueError(f"canonical name is not NFC-normalized: {name!r}")
        if naif_id != 2_000_000 + number:
            raise ValueError(
                f"asteroid {number} has NAIF ID {naif_id}, expected {2_000_000 + number}"
            )
        if name in catalog:
            raise ValueError(f"duplicate canonical asteroid name: {name!r}")
        folded = unicodedata.normalize("NFKC", name).casefold()
        if folded in seen_casefold_names:
            raise ValueError(
                f"case-insensitive asteroid-name collision: "
                f"{seen_casefold_names[folded]!r} and {name!r}"
            )
        if naif_id in seen_ids:
            raise ValueError(f"duplicate asteroid NAIF ID: {naif_id}")
        catalog[name] = naif_id
        seen_casefold_names[folded] = name
        seen_ids.add(naif_id)

    master_map = {str(name): int(naif_id) for name, naif_id in master["naif_map"].items()}
    if catalog != master_map:
        raise ValueError("unified master naif_map does not match its ordered records")

    manifest_ids = [
        int(naif_id)
        for shard in manifest["shards"]
        for naif_id in shard["bodies"]
    ]
    if len(manifest_ids) != expected_count or set(manifest_ids) != seen_ids:
        raise ValueError("release shard identities do not match the unified master")

    catalog_bytes = (
        json.dumps(catalog, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    catalog_sha256 = _sha256_bytes(catalog_bytes)

    metadata = {
        "schema_version": 1,
        "catalog_id": manifest["catalog_id"],
        "catalog_version": manifest["catalog_version"],
        "identity_product": "canonical_asteroid_name_to_naif_id",
        "identity_policy": {
            "name_source": "JPL Horizons target identity captured by the Moira release build",
            "number_source": "MPC catalog number admitted by the release target list",
            "naif_convention": "2000000_plus_mpc_catalog_number",
            "canonicalization": "exact released name; NFC; unique under NFKC casefold",
            "placeholder_policy": "released canonical names replace prior numeric placeholders",
        },
        "source": {
            "release_manifest": "manifest.json",
            "release_manifest_sha256": manifest_sha256,
            "release_source": manifest["source"],
            "release_source_revision": manifest["release"]["source_revision"],
            "released_utc": manifest["release"]["released_utc"],
            "unified_master": "unified_master.json",
            "unified_master_sha256": _sha256_file(master_path),
            "admitted_targets": "moira_public_asteroid_targets.json",
            "admitted_targets_sha256": _sha256_file(targets_path),
            "trajectory_source": manifest["provenance"]["trajectory_source"],
            "horizons_api": manifest["provenance"]["horizons_api"],
        },
        "artifact": {
            "path": "moira/data/asteroid_catalog_naif.json",
            "sha256": catalog_sha256,
            "canonical_name_count": len(catalog),
            "unique_naif_id_count": len(seen_ids),
        },
    }
    metadata_bytes = (
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    return catalog_bytes, metadata_bytes


def _write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def _check_exact(path: Path, expected: bytes) -> bool:
    try:
        actual = path.read_bytes()
    except OSError:
        return False
    return actual == expected


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("release_dir", type=Path)
    parser.add_argument(
        "--expected-manifest-sha256",
        help="Fail unless the finalized release manifest has this exact SHA-256.",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--metadata-output",
        type=Path,
        default=DEFAULT_METADATA_OUTPUT,
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify committed artifacts without rewriting them.",
    )
    args = parser.parse_args(argv)

    try:
        catalog_bytes, metadata_bytes = build_catalog(
            args.release_dir,
            expected_manifest_sha256=args.expected_manifest_sha256,
        )
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"Asteroid identity catalog build failed: {exc}", file=sys.stderr)
        return 1

    if args.check:
        failures = []
        if not _check_exact(args.output, catalog_bytes):
            failures.append(str(args.output))
        if not _check_exact(args.metadata_output, metadata_bytes):
            failures.append(str(args.metadata_output))
        if failures:
            print(
                "Asteroid identity catalog artifacts are stale: "
                + ", ".join(failures),
                file=sys.stderr,
            )
            return 1
        catalog_count = len(json.loads(catalog_bytes))
        print(
            "Asteroid identity catalog is current: "
            f"{catalog_count} canonical names."
        )
        return 0

    _write_atomic(args.output, catalog_bytes)
    _write_atomic(args.metadata_output, metadata_bytes)
    metadata = json.loads(metadata_bytes)
    print(
        json.dumps(
            {
                "catalog": str(args.output),
                "metadata": str(args.metadata_output),
                "catalog_version": metadata["catalog_version"],
                "canonical_name_count": metadata["artifact"]["canonical_name_count"],
                "sha256": metadata["artifact"]["sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
