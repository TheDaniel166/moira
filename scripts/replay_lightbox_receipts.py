"""Replay bounded Light Box evidence contracts and write machine receipts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACTS_PATH = REPO_ROOT / "tests" / "evidence" / "lightbox" / "contracts.json"
INVENTORY_PATH = (
    REPO_ROOT
    / "wiki"
    / "03_validation"
    / "LIGHT_BOX_CALCULATION_INVENTORY.generated.json"
)
DEFAULT_RECEIPT_PATH = (
    REPO_ROOT / "tests" / "evidence" / "lightbox" / "receipts" / "local.generated.json"
)
SCHEMA_VERSION = "moira.lightbox-evidence-receipts/v2"
PYTEST_SUMMARY_RE = re.compile(r"(?:^|\s)(\d+) passed(?:,|\s|$)")


class ReceiptReplayError(RuntimeError):
    """Raised when evidence contracts or replay arguments are invalid."""


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ReceiptReplayError(f"JSON root must be an object: {path}")
    return value


def _sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
    ).hexdigest()


def _git(args: Sequence[str]) -> str:
    process = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if process.returncode:
        raise ReceiptReplayError(f"git {' '.join(args)} failed")
    return process.stdout.strip()


def _source_snapshot() -> tuple[str, bool]:
    """Return the current revision and whether the tracked source tree is clean."""

    return (
        _git(["rev-parse", "HEAD"]),
        not bool(_git(["status", "--porcelain", "--untracked-files=all"])),
    )


def load_contracts(
    contracts_path: Path = CONTRACTS_PATH,
    inventory_path: Path = INVENTORY_PATH,
) -> tuple[dict[str, Any], dict[str, Any]]:
    contracts = _load(contracts_path)
    inventory = _load(inventory_path)
    if inventory.get("schema_version") != "moira.lightbox-calculation-inventory/v2":
        raise ReceiptReplayError("unsupported inventory schema; regenerate before replay")
    if inventory.get("structural_fingerprint_version") != "moira.lightbox-structural-fingerprint/v1":
        raise ReceiptReplayError("unsupported structural fingerprint version")
    if contracts.get("schema_version") != "moira.lightbox-evidence-contracts/v1":
        raise ReceiptReplayError("unsupported evidence-contract schema")
    known = {
        str(row["surface_id"])
        for collection in ("python_exports", "rest_operations")
        for row in inventory[collection]
        if row["in_lightbox_calculation_scope"]
    }
    claim_ids: set[str] = set()
    for contract in contracts.get("contracts", []):
        claim_id = str(contract.get("claim_id", ""))
        if not re.fullmatch(r"LB-[A-Z0-9-]+", claim_id) or claim_id in claim_ids:
            raise ReceiptReplayError(f"invalid or duplicate claim ID: {claim_id!r}")
        claim_ids.add(claim_id)
        surface_ids = contract.get("surface_ids")
        if (
            not isinstance(surface_ids, list)
            or not surface_ids
            or not set(surface_ids) <= known
        ):
            raise ReceiptReplayError(f"contract has invalid surface IDs: {claim_id}")
        targets = contract.get("pytest_targets")
        if not isinstance(targets, list) or not targets:
            raise ReceiptReplayError(f"contract has no pytest targets: {claim_id}")
        for target in targets:
            target_path = REPO_ROOT / str(target).split("::", 1)[0]
            if not target_path.is_file():
                raise ReceiptReplayError(f"contract target does not exist: {target}")
    return contracts, inventory


def _passed_count(output: str) -> int:
    matches = PYTEST_SUMMARY_RE.findall(output)
    if matches:
        return int(matches[-1])
    progress_counts = [
        line.count(".")
        for line in output.splitlines()
        if "[100%]" in line
        and set(line.split("[100%]", 1)[0].strip()) <= {".", "s", "x", "X"}
    ]
    return progress_counts[-1] if progress_counts else 0


def validate_receipt_binding(receipt_set: Mapping[str, Any], fingerprint: str) -> None:
    """Reject mixed bindings and retain an auditable legacy migration boundary."""
    if receipt_set.get("schema_version") != SCHEMA_VERSION:
        raise ReceiptReplayError("unsupported receipts schema; legacy receipts require explicit migration")
    if receipt_set.get("inventory_fingerprint_sha256") != fingerprint:
        raise ReceiptReplayError("receipt structural inventory drift; replay after reviewing API changes")
    row_fingerprint = fingerprint
    migration = receipt_set.get("binding_migration")
    if migration is not None:
        if not isinstance(migration, dict) or migration.get("schema_version") != "moira.lightbox-receipt-binding-migration/v1":
            raise ReceiptReplayError("unsupported receipt binding migration")
        header = migration.get("legacy_header", {})
        if not isinstance(header, dict) or header.get("schema_version") != "moira.lightbox-evidence-receipts/v1":
            raise ReceiptReplayError("invalid legacy receipt header")
        if migration.get("legacy_inventory_fingerprint_sha256") != header.get("inventory_fingerprint_sha256"):
            raise ReceiptReplayError("legacy inventory migration identities disagree")
        original = {**header, "receipts": receipt_set.get("receipts", [])}
        if _sha(original) != migration.get("legacy_receipt_set_sha256"):
            raise ReceiptReplayError("legacy receipt execution records changed after migration")
        for key, value in header.items():
            if key not in {"schema_version", "inventory_fingerprint_sha256"} and receipt_set.get(key) != value:
                raise ReceiptReplayError(f"legacy receipt header changed after migration: {key}")
        if receipt_set.get("artifact_status") != "local_unreleased_worktree":
            raise ReceiptReplayError("migrated legacy receipts cannot establish exact-source evidence")
        row_fingerprint = header.get("inventory_fingerprint_sha256")
    for row in receipt_set.get("receipts", []):
        if row.get("inventory_fingerprint_sha256") != row_fingerprint:
            raise ReceiptReplayError("individual receipt inventory binding differs from its set")
        if row.get("receipt_id") != _sha({key: value for key, value in row.items() if key != "receipt_id"}):
            raise ReceiptReplayError("individual receipt digest mismatch")


def migrate_legacy_binding(receipt_set: Mapping[str, Any], legacy_inventory: Mapping[str, Any]) -> dict[str, Any]:
    """Bind historical local results to reviewed API metadata without replaying them."""
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from scripts.generate_lightbox_calculation_inventory import _canonical_sha256, structural_payload

    contracts, inventory = load_contracts()
    if receipt_set.get("schema_version") != "moira.lightbox-evidence-receipts/v1":
        raise ReceiptReplayError("migration requires legacy v1 receipts")
    if legacy_inventory.get("schema_version") != "moira.lightbox-calculation-inventory/v1":
        raise ReceiptReplayError("migration requires the retained v1 inventory")
    old_fingerprint = legacy_inventory.get("surface_fingerprint_sha256")
    if old_fingerprint != _canonical_sha256({key: value for key, value in legacy_inventory.items() if key != "surface_fingerprint_sha256"}):
        raise ReceiptReplayError("legacy inventory digest mismatch")
    if receipt_set.get("inventory_fingerprint_sha256") != old_fingerprint:
        raise ReceiptReplayError("legacy inventory does not match retained receipts")
    if receipt_set.get("contracts_sha256") != _sha(contracts):
        raise ReceiptReplayError("legacy receipts were produced from different contracts")
    if structural_payload(legacy_inventory, legacy=True) != structural_payload(inventory, legacy=True):
        raise ReceiptReplayError("legacy and current public API ownership/classification differ; review and replay")
    if receipt_set.get("artifact_status") != "local_unreleased_worktree" or any(
        row.get("artifact_status") != "local_unreleased_worktree" for row in receipt_set.get("receipts", [])
    ):
        raise ReceiptReplayError("exact-source legacy receipts require a fresh replay under v2")
    updated = dict(receipt_set)
    updated["schema_version"] = SCHEMA_VERSION
    updated["inventory_fingerprint_sha256"] = inventory["structural_fingerprint_sha256"]
    updated["binding_migration"] = {
        "schema_version": "moira.lightbox-receipt-binding-migration/v1",
        "legacy_inventory_fingerprint_sha256": old_fingerprint,
        "legacy_receipt_set_sha256": _sha(receipt_set),
        "legacy_header": {key: value for key, value in receipt_set.items() if key != "receipts"},
        "boundary": "Reviewed current structural binding only. Legacy execution did not record Python declarations or REST schema shapes. Original receipts remain unchanged; this is not a replay or exact-source evidence.",
    }
    validate_receipt_binding(updated, str(inventory["structural_fingerprint_sha256"]))
    return updated


def reclassify_existing(receipt_set: Mapping[str, Any]) -> dict[str, Any]:
    _, inventory = load_contracts()
    validate_receipt_binding(receipt_set, str(inventory["structural_fingerprint_sha256"]))
    if "binding_migration" in receipt_set:
        return dict(receipt_set)  # The retained legacy records are immutable.
    updated = dict(receipt_set)
    receipts: list[dict[str, Any]] = []
    for raw in receipt_set.get("receipts", []):
        receipt = dict(raw)
        passed = _passed_count("\n".join(map(str, receipt.get("output_tail", []))))
        receipt["passed_tests"] = passed
        receipt["status"] = (
            "passed"
            if receipt.get("exit_code") == 0
            and passed >= int(receipt.get("minimum_tests", 1))
            else "failed"
        )
        receipt.pop("receipt_id", None)
        receipt = {"receipt_id": _sha(receipt), **receipt}
        receipts.append(receipt)
    updated["receipts"] = receipts
    updated["summary"] = {
        "contracts_run": len(receipts),
        "passed": sum(row["status"] == "passed" for row in receipts),
        "failed": sum(row["status"] == "failed" for row in receipts),
        "tests_passed": sum(int(row["passed_tests"]) for row in receipts),
    }
    return updated


def replay_contract(
    contract: Mapping[str, Any],
    *,
    inventory: Mapping[str, Any],
    source_revision: str,
    working_tree_clean: bool,
) -> dict[str, Any]:
    command = [
        sys.executable,
        "-m",
        "pytest",
        *map(str, contract["pytest_targets"]),
        "-q",
    ]
    environment = os.environ.copy()
    environment.update(
        {
            "MOIRA_TEST_MODE": "1",
            "MOIRA_STRICT_KNOWN_ISSUES": "1",
            "MOIRA_NO_DOWNLOAD": "1",
        }
    )
    started = datetime.now(timezone.utc)
    process = subprocess.run(
        command,
        cwd=REPO_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    completed = datetime.now(timezone.utc)
    combined = process.stdout + ("\n" + process.stderr if process.stderr else "")
    passed = _passed_count(combined)
    minimum = int(contract["minimum_tests"])
    status = "passed" if process.returncode == 0 and passed >= minimum else "failed"
    receipt_core = {
        "claim_id": contract["claim_id"],
        "surface_ids": list(contract["surface_ids"]),
        "evidence_classes": list(contract["evidence_classes"]),
        "claim_scope": contract["claim_scope"],
        "exclusions": list(contract["exclusions"]),
        "contract_sha256": _sha(contract),
        "engine_version": inventory["engine_version"],
        "inventory_fingerprint_sha256": inventory["structural_fingerprint_sha256"],
        "source_revision": source_revision,
        "working_tree_clean": working_tree_clean,
        "artifact_status": "exact_source_revision"
        if working_tree_clean
        else "local_unreleased_worktree",
        "executed_at_utc": completed.isoformat().replace("+00:00", "Z"),
        "duration_seconds": round((completed - started).total_seconds(), 3),
        "python_version": platform.python_version(),
        "network_policy": "MOIRA_NO_DOWNLOAD=1; harness default deny",
        "command": [
            "python",
            "-m",
            "pytest",
            *map(str, contract["pytest_targets"]),
            "-q",
        ],
        "exit_code": process.returncode,
        "passed_tests": passed,
        "minimum_tests": minimum,
        "status": status,
        "output_sha256": hashlib.sha256(combined.encode("utf-8")).hexdigest(),
        "output_tail": combined.splitlines()[-80:],
    }
    return {"receipt_id": _sha(receipt_core), **receipt_core}


def build_receipt_set(
    selected_claim_ids: set[str] | None = None,
    *,
    require_exact_source: bool = False,
) -> dict[str, Any]:
    contracts, inventory = load_contracts()
    source_revision, source_clean_at_start = _source_snapshot()
    if require_exact_source and not source_clean_at_start:
        raise ReceiptReplayError(
            "exact-source replay requires a clean worktree before execution"
        )
    available = {contract["claim_id"]: contract for contract in contracts["contracts"]}
    selected = set(available) if selected_claim_ids is None else selected_claim_ids
    unknown = selected - set(available)
    if unknown:
        raise ReceiptReplayError(f"unknown claim IDs: {sorted(unknown)}")
    receipts = [
        replay_contract(
            available[claim_id],
            inventory=inventory,
            source_revision=source_revision,
            working_tree_clean=source_clean_at_start,
        )
        for claim_id in sorted(selected)
    ]
    final_revision, source_clean_at_end = _source_snapshot()
    exact_source = (
        source_clean_at_start
        and source_clean_at_end
        and final_revision == source_revision
    )
    if require_exact_source and not exact_source:
        reasons: list[str] = []
        if final_revision != source_revision:
            reasons.append("HEAD changed during replay")
        if not source_clean_at_end:
            reasons.append("the worktree changed during replay")
        if not reasons:
            reasons.append("the source snapshot was not stable")
        raise ReceiptReplayError(
            "exact-source replay lost its source boundary: " + "; ".join(reasons)
        )
    artifact_status = (
        "exact_source_revision" if exact_source else "local_unreleased_worktree"
    )
    rebound_receipts: list[dict[str, Any]] = []
    for receipt in receipts:
        receipt_core = dict(receipt)
        receipt_core.pop("receipt_id", None)
        receipt_core["working_tree_clean"] = exact_source
        receipt_core["artifact_status"] = artifact_status
        rebound_receipts.append({"receipt_id": _sha(receipt_core), **receipt_core})
    receipts = rebound_receipts
    return {
        "schema_version": SCHEMA_VERSION,
        "contracts_path": CONTRACTS_PATH.relative_to(REPO_ROOT).as_posix(),
        "contracts_sha256": _sha(contracts),
        "engine_version": inventory["engine_version"],
        "inventory_fingerprint_sha256": inventory["structural_fingerprint_sha256"],
        "source_revision": source_revision,
        "working_tree_clean": exact_source,
        "artifact_status": artifact_status,
        "summary": {
            "contracts_run": len(receipts),
            "passed": sum(row["status"] == "passed" for row in receipts),
            "failed": sum(row["status"] == "failed" for row in receipts),
            "tests_passed": sum(int(row["passed_tests"]) for row in receipts),
        },
        "receipts": receipts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claim", action="append", default=[])
    parser.add_argument("--output", type=Path, default=DEFAULT_RECEIPT_PATH)
    parser.add_argument(
        "--migrate-legacy-inventory", type=Path,
        help="explicitly migrate retained v1 local receipts using their matching v1 inventory; never runs tests",
    )
    parser.add_argument(
        "--reclassify-existing",
        action="store_true",
        help="re-evaluate a saved receipt set without rerunning its retained pytest output",
    )
    parser.add_argument(
        "--require-exact-source",
        action="store_true",
        help=(
            "refuse to write receipts unless HEAD and the clean worktree remain "
            "unchanged for the entire replay"
        ),
    )
    args = parser.parse_args()
    try:
        if args.migrate_legacy_inventory and (args.reclassify_existing or args.require_exact_source or args.claim):
            raise ReceiptReplayError("legacy migration cannot be combined with replay or reclassification options")
        if args.reclassify_existing and args.require_exact_source:
            raise ReceiptReplayError(
                "--require-exact-source cannot be combined with --reclassify-existing"
            )
        output = args.output.resolve()
        receipt_set = (
            migrate_legacy_binding(_load(output), _load(args.migrate_legacy_inventory))
            if args.migrate_legacy_inventory
            else reclassify_existing(_load(output))
            if args.reclassify_existing
            else build_receipt_set(
                set(args.claim) or None,
                require_exact_source=args.require_exact_source,
            )
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix(output.suffix + ".tmp")
        temporary.write_text(
            json.dumps(receipt_set, indent=2, ensure_ascii=False, sort_keys=True)
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
        temporary.replace(output)
        summary = receipt_set["summary"]
        action = "Migrated" if args.migrate_legacy_inventory else "Reclassified" if args.reclassify_existing else "Replayed"
        print(
            f"{action} {summary['contracts_run']} Light Box contract(s): "
            f"{summary['passed']} passed, {summary['failed']} failed."
        )
        return 0 if summary["failed"] == 0 else 1
    except (OSError, ReceiptReplayError, subprocess.SubprocessError) as exc:
        print(f"Light Box receipt replay failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
