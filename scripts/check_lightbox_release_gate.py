"""Enforce the source and exact-release Light Box governance gates."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATION_DIR = REPO_ROOT / "wiki" / "03_validation"
BASELINE_PATH = VALIDATION_DIR / "LIGHT_BOX_RELEASE_BASELINE.json"
INVENTORY_PATH = VALIDATION_DIR / "LIGHT_BOX_CALCULATION_INVENTORY.generated.json"
MANIFEST_PATH = VALIDATION_DIR / "LIGHT_BOX_CONFORMANCE_MANIFEST.generated.json"
REGISTER_PATH = VALIDATION_DIR / "LIGHT_BOX_FAMILY_REGISTER.generated.json"
ASSESSMENT_PATH = VALIDATION_DIR / "LIGHT_BOX_FAMILY_ASSESSMENT.generated.json"
MATRIX_PATH = VALIDATION_DIR / "LIGHT_BOX_ASSURANCE_MATRIX.generated.json"


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


def _git_head() -> str:
    process = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if process.returncode:
        raise LightBoxReleaseGateError("cannot resolve the current source revision")
    return process.stdout.strip()


def evaluate(
    *, exact_release: bool = False, matrix_path: Path = MATRIX_PATH
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
        if matrix.get("receipt_artifact_status") != "exact_source_revision":
            errors.append(
                "exact release: assurance receipts are not bound to a clean exact source revision"
            )
        if matrix.get("receipt_source_revision") != _git_head():
            errors.append(
                "exact release: assurance receipt revision does not match current HEAD"
            )
        release_cells = matrix["summary"]["evidence_classes"]["release"]
        if release_cells.get("passed_exact_source", 0) == 0:
            errors.append("exact release: no release evidence cell has passed")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--exact-release",
        action="store_true",
        help="also require receipts from a clean exact source revision and release evidence",
    )
    parser.add_argument("--matrix", type=Path, default=MATRIX_PATH)
    args = parser.parse_args()
    try:
        errors = evaluate(
            exact_release=args.exact_release,
            matrix_path=args.matrix.resolve(),
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
