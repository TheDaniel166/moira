"""Build Moira's packaged numbered-periodic-comet identity registry.

The input is one verified immutable comet release. Its finalized manifest,
master ledger, and release-bound compatibility-alias policy jointly define the
identity boundary. This script performs no network access and does not rebuild
ephemerides.

Canonical identities are numbered periodic-comet designations such as
``1P/Halley``. Short names are explicit, family-scoped compatibility aliases;
they never claim uniqueness across asteroid, star, point, or other namespaces.
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

from moira.small_body_catalog_release import verify_release


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "moira" / "data" / "comet_catalog_naif.json"
DEFAULT_METADATA_OUTPUT = (
    REPO_ROOT / "moira" / "data" / "comet_catalog_naif.metadata.json"
)
MASTER_RELEASE_PATH = "comet_master.json"
ALIASES_RELEASE_PATH = "identity/comet_catalog_aliases.json"
ALIASES_PACKAGE_PATH = "moira/data/comet_catalog_aliases.json"


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


def _release_file_spec(
    manifest: dict[str, Any],
    relative_path: str,
) -> dict[str, Any]:
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


def _normalized_name(name: str) -> str:
    return unicodedata.normalize("NFKC", name).casefold()


def _canonical_catalog(
    master: dict[str, Any],
    manifest: dict[str, Any],
) -> tuple[dict[str, int], set[int]]:
    records = master.get("records")
    if not isinstance(records, list):
        raise ValueError("comet master records must be a list")

    expected_count = int(manifest["body_count"])
    if len(records) != expected_count:
        raise ValueError(
            f"comet master has {len(records)} records, expected {expected_count}"
        )
    if int(master.get("requested", -1)) != expected_count:
        raise ValueError("comet master requested count does not match manifest")
    if int(master.get("built", -1)) != expected_count:
        raise ValueError("comet master built count does not match manifest")
    if int(master.get("failed", -1)) != 0:
        raise ValueError(f"comet master records failures: {master.get('failed')!r}")

    catalog: dict[str, int] = {}
    seen_ids: set[int] = set()
    seen_folded_names: dict[str, str] = {}
    for record in records:
        number = int(record["number"])
        naif_id = int(record["naif_id"])
        name = record["name"]
        if not isinstance(name, str) or not name or name != name.strip():
            raise ValueError(f"invalid canonical name for comet {number}: {name!r}")
        if unicodedata.normalize("NFC", name) != name:
            raise ValueError(f"canonical name is not NFC-normalized: {name!r}")
        if not name.startswith(f"{number}P/"):
            raise ValueError(
                f"canonical comet name {name!r} does not carry designation {number}P"
            )
        if naif_id != 1_000_000 + number:
            raise ValueError(
                f"comet {number} has NAIF ID {naif_id}, "
                f"expected {1_000_000 + number}"
            )
        if name in catalog:
            raise ValueError(f"duplicate canonical comet name: {name!r}")
        folded = _normalized_name(name)
        if folded in seen_folded_names:
            raise ValueError(
                "case-insensitive comet-name collision: "
                f"{seen_folded_names[folded]!r} and {name!r}"
            )
        if naif_id in seen_ids:
            raise ValueError(f"duplicate comet NAIF ID: {naif_id}")
        catalog[name] = naif_id
        seen_folded_names[folded] = name
        seen_ids.add(naif_id)

    master_map = {
        str(name): int(naif_id)
        for name, naif_id in master.get("naif_map", {}).items()
    }
    if catalog != master_map:
        raise ValueError("comet master naif_map does not match its ordered records")

    manifest_ids = [
        int(naif_id)
        for shard in manifest["shards"]
        for naif_id in shard["bodies"]
    ]
    if len(manifest_ids) != expected_count or set(manifest_ids) != seen_ids:
        raise ValueError("release shard identities do not match the comet master")
    return catalog, seen_ids


def _alias_receipt(
    aliases_payload: Any,
    catalog: dict[str, int],
) -> tuple[list[dict[str, str]], set[int]]:
    if not isinstance(aliases_payload, dict):
        raise ValueError("comet alias catalog must be an object")
    if aliases_payload.get("schema_version") != 1:
        raise ValueError("comet alias catalog schema_version must be 1")
    if aliases_payload.get("catalog_id") != "moira-comets":
        raise ValueError("comet alias catalog has the wrong catalog_id")
    policy = aliases_payload.get("policy")
    if not isinstance(policy, dict):
        raise ValueError("comet alias catalog must declare policy")
    if policy.get("global_namespace") != (
        "aliases are comet-family scoped and make no cross-family uniqueness claim"
    ):
        raise ValueError("comet alias catalog must preserve family-scoped resolution")

    raw_aliases = aliases_payload.get("aliases")
    if not isinstance(raw_aliases, list):
        raise ValueError("comet alias catalog aliases must be a list")

    aliases: list[dict[str, str]] = []
    seen_aliases: dict[str, str] = {}
    target_ids: set[int] = set()
    canonical_folded = {_normalized_name(name): name for name in catalog}
    for record in raw_aliases:
        if not isinstance(record, dict):
            raise ValueError("comet alias records must be objects")
        alias = record.get("alias")
        canonical_name = record.get("canonical_name")
        alias_kind = record.get("alias_kind")
        if not isinstance(alias, str) or not alias or alias != alias.strip():
            raise ValueError(f"invalid comet alias: {alias!r}")
        if unicodedata.normalize("NFC", alias) != alias:
            raise ValueError(f"comet alias is not NFC-normalized: {alias!r}")
        if canonical_name not in catalog:
            raise ValueError(
                f"comet alias {alias!r} has unknown target {canonical_name!r}"
            )
        if not isinstance(alias_kind, str) or not alias_kind:
            raise ValueError(f"comet alias {alias!r} has no alias_kind")
        folded = _normalized_name(alias)
        if folded in seen_aliases:
            raise ValueError(
                f"case-insensitive comet-alias collision: "
                f"{seen_aliases[folded]!r} and {alias!r}"
            )
        if folded in canonical_folded:
            raise ValueError(
                f"comet alias {alias!r} collides with canonical identity "
                f"{canonical_folded[folded]!r}"
            )
        aliases.append(
            {
                "alias": alias,
                "alias_kind": alias_kind,
                "canonical_name": str(canonical_name),
            }
        )
        seen_aliases[folded] = alias
        target_ids.add(catalog[str(canonical_name)])
    return aliases, target_ids


def build_catalog(
    release_dir: Path,
    *,
    expected_manifest_sha256: str | None = None,
) -> tuple[bytes, bytes]:
    """Return deterministic canonical-registry and provenance-metadata bytes."""
    release_dir = release_dir.resolve()
    verification = verify_release(release_dir)
    manifest_path = release_dir / "manifest.json"
    manifest_sha256 = verification.manifest_sha256
    if (
        expected_manifest_sha256 is not None
        and manifest_sha256 != expected_manifest_sha256.lower()
    ):
        raise ValueError(
            f"release manifest SHA-256 {manifest_sha256} != expected "
            f"{expected_manifest_sha256.lower()}"
        )

    manifest = _read_json(manifest_path)
    if manifest.get("catalog_id") != "moira-comets":
        raise ValueError(f"unexpected catalog_id: {manifest.get('catalog_id')!r}")
    source_revision = manifest.get("release", {}).get("source_revision")
    if not isinstance(source_revision, str) or not source_revision:
        raise ValueError("comet release must declare release.source_revision")

    master_path = _verify_bound_file(
        release_dir,
        manifest,
        MASTER_RELEASE_PATH,
    )
    aliases_path = _verify_bound_file(
        release_dir,
        manifest,
        ALIASES_RELEASE_PATH,
    )
    master = _read_json(master_path)
    aliases_payload = _read_json(aliases_path)
    catalog, seen_ids = _canonical_catalog(master, manifest)
    aliases, alias_target_ids = _alias_receipt(aliases_payload, catalog)

    catalog_bytes = (
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")
    catalog_sha256 = _sha256_bytes(catalog_bytes)
    aliases_sha256 = _sha256_file(aliases_path)
    provenance = manifest.get("provenance")
    if not isinstance(provenance, dict):
        raise ValueError("comet release must declare provenance")
    query_policy = provenance.get("query_policy")
    if not isinstance(query_policy, dict):
        raise ValueError("comet release provenance must declare query_policy")

    metadata = {
        "schema_version": 1,
        "catalog_id": manifest["catalog_id"],
        "catalog_version": manifest["catalog_version"],
        "identity_product": "canonical_numbered_periodic_comet_name_to_naif_id",
        "identity_policy": {
            "canonical_name_source": (
                "JPL Horizons target identity captured by the Moira release build"
            ),
            "number_source": "numbered periodic-comet designation",
            "naif_convention": "1000000_plus_periodic_comet_number",
            "canonicalization": (
                "exact released numbered designation; NFC; "
                "unique under NFKC casefold"
            ),
            "alias_source": "release-bound Moira compatibility alias catalog",
            "alias_scope": "comet_family_only",
            "global_collision_policy": (
                "aliases make no cross-family uniqueness claim; unified callers "
                "must provide family identity or reject ambiguous names"
            ),
        },
        "source": {
            "release_manifest": "manifest.json",
            "release_manifest_sha256": manifest_sha256,
            "release_source": manifest["source"],
            "release_source_revision": source_revision,
            "released_utc": manifest["release"]["released_utc"],
            "comet_master": MASTER_RELEASE_PATH,
            "comet_master_sha256": _sha256_file(master_path),
            "alias_catalog_release_path": ALIASES_RELEASE_PATH,
            "alias_catalog_sha256": aliases_sha256,
            "trajectory_source": provenance["trajectory_source"],
            "horizons_api": provenance["horizons_api"],
            "query_policy": query_policy,
        },
        "artifact": {
            "path": "moira/data/comet_catalog_naif.json",
            "sha256": catalog_sha256,
            "canonical_name_count": len(catalog),
            "unique_naif_id_count": len(seen_ids),
        },
        "aliases": {
            "path": ALIASES_PACKAGE_PATH,
            "sha256": aliases_sha256,
            "alias_count": len(aliases),
            "unique_target_count": len(alias_target_ids),
            "records": aliases,
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
        print(f"Comet identity catalog build failed: {exc}", file=sys.stderr)
        return 1

    if args.check:
        failures = []
        if not _check_exact(args.output, catalog_bytes):
            failures.append(str(args.output))
        if not _check_exact(args.metadata_output, metadata_bytes):
            failures.append(str(args.metadata_output))
        if failures:
            print(
                "Comet identity catalog artifacts are stale: "
                + ", ".join(failures),
                file=sys.stderr,
            )
            return 1
        catalog_count = len(json.loads(catalog_bytes))
        print(
            "Comet identity catalog is current: "
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
                "canonical_name_count": metadata["artifact"][
                    "canonical_name_count"
                ],
                "alias_count": metadata["aliases"]["alias_count"],
                "sha256": metadata["artifact"]["sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
