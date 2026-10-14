"""Enforce the source and exact-release Light Box governance gates."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATION_DIR = REPO_ROOT / "wiki" / "03_validation"
BASELINE_PATH = VALIDATION_DIR / "LIGHT_BOX_RELEASE_BASELINE.json"
INVENTORY_PATH = VALIDATION_DIR / "LIGHT_BOX_CALCULATION_INVENTORY.generated.json"
MANIFEST_PATH = VALIDATION_DIR / "LIGHT_BOX_CONFORMANCE_MANIFEST.generated.json"
REGISTER_PATH = VALIDATION_DIR / "LIGHT_BOX_FAMILY_REGISTER.generated.json"
ASSESSMENT_PATH = VALIDATION_DIR / "LIGHT_BOX_FAMILY_ASSESSMENT.generated.json"
MATRIX_PATH = VALIDATION_DIR / "LIGHT_BOX_ASSURANCE_MATRIX.generated.json"
RECEIPTS_PATH = (
    REPO_ROOT / "tests" / "evidence" / "lightbox" / "receipts" / "local.generated.json"
)
EVIDENCE_PATHS = frozenset(
    {
        "tests/evidence/lightbox/receipts/local.generated.json",
        "wiki/03_validation/LIGHT_BOX_ASSURANCE_MATRIX.generated.json",
        "wiki/03_validation/LIGHT_BOX_ASSURANCE_MATRIX.generated.md",
        "wiki/03_validation/LIGHT_BOX_CURRENT_STATUS.generated.json",
        "wiki/03_validation/LIGHT_BOX_CURRENT_STATUS.generated.md",
    }
)
WIKI_GITLINK_PATH = "moira.wiki"
ATTESTATION_PATHS = EVIDENCE_PATHS | {WIKI_GITLINK_PATH}
NESTED_WIKI_ATTESTATION_PATHS = frozenset(
    {
        "LIGHT_BOX_ASSURANCE_MATRIX.generated.md",
        "LIGHT_BOX_CURRENT_STATUS.generated.md",
    }
)


class LightBoxReleaseGateError(RuntimeError):
    """Raised when release-facing Light Box evidence regresses or drifts."""


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LightBoxReleaseGateError(f"cannot load {path}") from exc
    if not isinstance(value, dict):
        raise LightBoxReleaseGateError(f"JSON root must be an object: {path}")
    return value


def _git(args: Sequence[str], *, cwd: Path = REPO_ROOT) -> str:
    process = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    if process.returncode:
        raise LightBoxReleaseGateError(f"git {' '.join(args)} failed in {cwd}")
    return process.stdout.strip()


def _git_head() -> str:
    return _git(["rev-parse", "HEAD"])


def _nul_paths(value: str) -> frozenset[str]:
    return frozenset(path for path in value.split("\0") if path)


def _worktree_paths() -> frozenset[str]:
    tracked = _nul_paths(_git(["diff", "--name-only", "-z", "HEAD", "--"]))
    untracked = _nul_paths(_git(["ls-files", "--others", "--exclude-standard", "-z"]))
    return tracked | untracked


def _git_parents(revision: str) -> tuple[str, ...]:
    fields = _git(["rev-list", "--parents", "-n", "1", revision]).split()
    return tuple(fields[1:])


def _commit_paths(parent: str, revision: str) -> frozenset[str]:
    return _nul_paths(_git(["diff", "--name-only", "-z", parent, revision, "--"]))


def _gitlink_revision(revision: str) -> str:
    return _git(["rev-parse", f"{revision}:{WIKI_GITLINK_PATH}"])


def _nested_wiki_errors(old_revision: str, new_revision: str) -> list[str]:
    wiki_root = REPO_ROOT / WIKI_GITLINK_PATH
    errors: list[str] = []
    if _git(["rev-parse", "HEAD"], cwd=wiki_root) != new_revision:
        errors.append(
            "exact release: nested wiki checkout does not match the attested gitlink"
        )
    nested_paths = _nul_paths(
        _git(
            ["diff", "--name-only", "-z", old_revision, new_revision, "--"],
            cwd=wiki_root,
        )
    )
    if nested_paths != NESTED_WIKI_ATTESTATION_PATHS:
        errors.append(
            "exact release: nested wiki attestation paths are not the two generated Light Box reports"
        )
    nested_dirty = _git(
        ["status", "--porcelain", "--untracked-files=all"], cwd=wiki_root
    )
    if nested_dirty:
        errors.append("exact release: nested wiki worktree is not clean")
    return errors


def _receipt_errors(receipts: dict[str, Any], matrix: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    source_revision = receipts.get("source_revision")
    if receipts.get("artifact_status") != "exact_source_revision":
        errors.append(
            "exact release: receipt set is not bound to a clean exact source revision"
        )
    if receipts.get("working_tree_clean") is not True:
        errors.append(
            "exact release: receipt set does not record a stable clean replay"
        )
    if matrix.get("receipt_source_revision") != source_revision:
        errors.append("exact release: matrix and receipt source revisions differ")
    if matrix.get("receipt_artifact_status") != receipts.get("artifact_status"):
        errors.append("exact release: matrix and receipt artifact statuses differ")
    rows = receipts.get("receipts")
    if not isinstance(rows, list) or not rows:
        errors.append("exact release: receipt set is empty")
        rows = []
    for row in rows:
        if (
            row.get("source_revision") != source_revision
            or row.get("artifact_status") != "exact_source_revision"
            or row.get("working_tree_clean") is not True
        ):
            errors.append(
                "exact release: an individual receipt has a stale source binding"
            )
            break
        if row.get("status") != "passed":
            errors.append("exact release: an individual replay contract did not pass")
            break
    summary = receipts.get("summary", {})
    passed = sum(row.get("status") == "passed" for row in rows)
    failed = sum(row.get("status") != "passed" for row in rows)
    if (
        summary.get("contracts_run") != len(rows)
        or summary.get("passed") != passed
        or summary.get("failed") != failed
        or failed
    ):
        errors.append(
            "exact release: receipt summary does not describe an all-pass replay"
        )
    return errors


def _exact_binding_errors(source_revision: str) -> list[str]:
    errors: list[str] = []
    head = _git_head()
    changed = _worktree_paths()
    if source_revision == head:
        if changed == EVIDENCE_PATHS:
            return errors
        if changed == ATTESTATION_PATHS:
            old_wiki_revision = _gitlink_revision(source_revision)
            new_wiki_revision = _git(
                ["rev-parse", "HEAD"], cwd=REPO_ROOT / WIKI_GITLINK_PATH
            )
            errors.extend(_nested_wiki_errors(old_wiki_revision, new_wiki_revision))
            return errors
        errors.append(
            "exact release: pre-attestation worktree must contain exactly the five generated evidence files, optionally plus the nested wiki gitlink"
        )
        return errors

    parents = _git_parents(head)
    if len(parents) != 1:
        errors.append("exact release: attestation commit must have exactly one parent")
        return errors
    if parents[0] != source_revision:
        errors.append(
            "exact release: receipt source revision is not the sole parent of the attestation commit"
        )
        return errors
    if changed:
        errors.append("exact release: post-attestation worktree is not clean")
    committed_paths = _commit_paths(source_revision, head)
    if committed_paths != ATTESTATION_PATHS:
        errors.append(
            "exact release: attestation commit does not contain exactly the approved evidence paths and nested wiki gitlink"
        )
        return errors
    errors.extend(
        _nested_wiki_errors(
            _gitlink_revision(source_revision),
            _gitlink_revision(head),
        )
    )
    return errors


def evaluate(
    *,
    exact_release: bool = False,
    matrix_path: Path = MATRIX_PATH,
    receipts_path: Path = RECEIPTS_PATH,
) -> list[str]:
    baseline = _load(BASELINE_PATH)
    inventory = _load(INVENTORY_PATH)
    manifest = _load(MANIFEST_PATH)
    register = _load(REGISTER_PATH)
    assessment = _load(ASSESSMENT_PATH)
    matrix = _load(matrix_path)
    errors: list[str] = []
    fingerprint = inventory.get("surface_fingerprint_sha256")
    for label, artifact in (
        ("manifest", manifest),
        ("family register", register),
        ("family assessment", assessment),
        ("assurance matrix", matrix),
    ):
        if artifact.get("inventory_fingerprint_sha256") != fingerprint:
            errors.append(f"{label}: inventory fingerprint drift")
    if baseline.get("inventory_fingerprint_sha256") != fingerprint:
        errors.append(
            "release baseline: public calculation surface changed; regenerate and review the baseline deliberately"
        )
    canonical = [row for row in manifest["entries"] if row["entry_role"] == "canonical"]
    status_counts = Counter(str(row["conformance_status"]) for row in canonical)
    if len(canonical) != baseline.get("canonical_entries"):
        errors.append("manifest: canonical calculation denominator changed")
    if status_counts["partial"] < int(baseline["minimum_partial"]):
        errors.append("manifest: partial admissions regressed")
    if status_counts["unresolved"] > int(baseline["maximum_unresolved"]):
        errors.append("manifest: unresolved calculations increased")
    manifest_by_id = {str(row["surface_id"]): row for row in canonical}
    p0 = [
        row
        for row in register["entries"]
        if row["entry_role"] == "canonical" and row["priority"] == "P0"
    ]
    p0_statuses = Counter(
        str(manifest_by_id[str(row["surface_id"])]["conformance_status"]) for row in p0
    )
    if len(p0) != baseline.get("production_user_entries"):
        errors.append("family register: production-user denominator changed")
    if p0_statuses["unresolved"] > int(baseline["maximum_production_user_unresolved"]):
        errors.append("manifest: unresolved production-user calculations increased")
    if assessment["summary"].get("reviewed_families") != baseline.get(
        "reviewed_families"
    ):
        errors.append("family assessment: reviewed family coverage changed")
    if matrix["summary"].get("contracts_failed") != 0:
        errors.append("assurance matrix: one or more replay contracts failed")
    replayed_contracts_passed = matrix["summary"].get(
        "contracts_passed_local", 0
    ) + matrix["summary"].get("contracts_passed_exact_source", 0)
    if replayed_contracts_passed < int(baseline["minimum_replayed_contracts"]):
        errors.append("assurance matrix: replayed contract coverage regressed")
    if exact_release:
        receipts = _load(receipts_path)
        errors.extend(_receipt_errors(receipts, matrix))
        release_cells = matrix["summary"]["evidence_classes"]["release"]
        if release_cells.get("passed_exact_source", 0) == 0:
            errors.append("exact release: no release evidence cell has passed")
        source_revision = receipts.get("source_revision")
        if not isinstance(source_revision, str) or not source_revision:
            errors.append("exact release: receipt source revision is missing")
        else:
            errors.extend(_exact_binding_errors(source_revision))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--exact-release",
        action="store_true",
        help="also require receipts from a clean exact source revision and release evidence",
    )
    parser.add_argument("--matrix", type=Path, default=MATRIX_PATH)
    parser.add_argument("--receipts", type=Path, default=RECEIPTS_PATH)
    args = parser.parse_args()
    try:
        errors = evaluate(
            exact_release=args.exact_release,
            matrix_path=args.matrix.resolve(),
            receipts_path=args.receipts.resolve(),
        )
        if errors:
            raise LightBoxReleaseGateError(
                "Light Box gate failed:\n- " + "\n- ".join(errors)
            )
        mode = "exact-release" if args.exact_release else "source"
        print(f"Light Box {mode} gate passed.")
        return 0
    except LightBoxReleaseGateError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
