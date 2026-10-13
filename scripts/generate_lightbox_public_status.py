"""Generate the release-facing Light Box status without changing the doctrine."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATION_DIR = REPO_ROOT / "wiki" / "03_validation"
MANIFEST_PATH = VALIDATION_DIR / "LIGHT_BOX_CONFORMANCE_MANIFEST.generated.json"
REGISTER_PATH = VALIDATION_DIR / "LIGHT_BOX_FAMILY_REGISTER.generated.json"
ASSESSMENT_PATH = VALIDATION_DIR / "LIGHT_BOX_FAMILY_ASSESSMENT.generated.json"
MATRIX_PATH = VALIDATION_DIR / "LIGHT_BOX_ASSURANCE_MATRIX.generated.json"
JSON_PATH = VALIDATION_DIR / "LIGHT_BOX_CURRENT_STATUS.generated.json"
MARKDOWN_PATH = VALIDATION_DIR / "LIGHT_BOX_CURRENT_STATUS.generated.md"
GENERATOR_PATH = "scripts/generate_lightbox_public_status.py"
SCHEMA_VERSION = "moira.lightbox-current-status/v1"


class PublicStatusError(RuntimeError):
    """Raised when the status inputs disagree."""


def _display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PublicStatusError(f"cannot load {_display_path(path)}") from exc
    if not isinstance(value, dict):
        raise PublicStatusError(f"JSON root must be an object: {_display_path(path)}")
    return value


def build_status(
    manifest: Mapping[str, Any],
    register: Mapping[str, Any],
    assessment: Mapping[str, Any],
    matrix: Mapping[str, Any],
    *,
    matrix_path: Path = MATRIX_PATH,
) -> dict[str, Any]:
    fingerprints = {
        manifest.get("inventory_fingerprint_sha256"),
        register.get("inventory_fingerprint_sha256"),
        assessment.get("inventory_fingerprint_sha256"),
        matrix.get("inventory_fingerprint_sha256"),
    }
    if len(fingerprints) != 1:
        raise PublicStatusError("status inputs disagree on inventory identity")
    canonical = [row for row in manifest["entries"] if row["entry_role"] == "canonical"]
    by_id = {str(row["surface_id"]): row for row in canonical}
    p0_ids = {
        str(row["surface_id"])
        for row in register["entries"]
        if row["entry_role"] == "canonical" and row["priority"] == "P0"
    }
    p0_counts = Counter(
        str(by_id[surface_id]["conformance_status"]) for surface_id in p0_ids
    )
    status_counts = Counter(str(row["conformance_status"]) for row in canonical)
    universal_supported = (
        status_counts["unresolved"] == 0
        and matrix["summary"]["surfaces_without_contracts"] == 0
        and matrix["receipt_artifact_status"] == "exact_source_revision"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATOR_PATH,
        "engine_version": manifest["engine_version"],
        "inventory_fingerprint_sha256": manifest["inventory_fingerprint_sha256"],
        "evidence_source_revision": matrix["receipt_source_revision"],
        "artifact_status": matrix["receipt_artifact_status"],
        "publication_disposition": (
            "exact_release_status"
            if matrix["receipt_artifact_status"] == "exact_source_revision"
            else "local_unreleased_status"
        ),
        "doctrine_text_changed": False,
        "universal_current_conformance_supported": universal_supported,
        "summary": {
            "canonical_calculations": len(canonical),
            "conformant": status_counts["conformant"],
            "partial": status_counts["partial"],
            "not_applicable": status_counts["not_applicable"],
            "unresolved": status_counts["unresolved"],
            "production_user_calculations": len(p0_ids),
            "production_user_by_status": {
                name: p0_counts[name]
                for name in ("conformant", "partial", "not_applicable", "unresolved")
            },
            "reviewed_families": assessment["summary"]["reviewed_families"],
            "family_dispositions": assessment["summary"]["families_by_status"],
            "replayed_contracts": matrix["summary"]["contracts"],
            "replayed_contracts_passed_local": matrix["summary"][
                "contracts_passed_local"
            ],
            "replayed_contracts_passed_exact_source": matrix["summary"].get(
                "contracts_passed_exact_source", 0
            ),
            "surfaces_with_replay_contracts": matrix["summary"][
                "surfaces_with_contracts"
            ],
            "surfaces_without_replay_contracts": matrix["summary"][
                "surfaces_without_contracts"
            ],
        },
        "claim_dispositions": [
            {
                "claim": "Transparency is the Primary Metric of Accuracy.",
                "class": "design_doctrine",
                "status": "preserved",
                "notes": "The canonical doctrine remains unchanged.",
            },
            {
                "claim": "Every calculation stage is inspectable, every reduction step is documented, and every residual is explained.",
                "class": "universal_current_capability",
                "status": "not_yet_supported"
                if not universal_supported
                else "supported_for_exact_release",
                "notes": "Use the generated counts and per-surface manifest; unresolved rows are visible and block a universal current-release claim.",
            },
            {
                "claim": "Every Calculation is Benchmarked.",
                "class": "universal_validation_claim",
                "status": "unsupported",
                "notes": "The assurance matrix intentionally contains not-run cells and multiple evidence classes.",
            },
            {
                "claim": "Every subsystem is validated against physical oracles.",
                "class": "universal_evidence_claim",
                "status": "unsupported",
                "notes": "Doctrine/source, invariant, regression, native-parity, harness, performance, authority, and release evidence are distinct.",
            },
        ],
        "links": {
            "manifest": _display_path(MANIFEST_PATH),
            "family_register": _display_path(REGISTER_PATH),
            "family_assessment": _display_path(ASSESSMENT_PATH),
            "assurance_matrix": _display_path(matrix_path),
            "program": "wiki/03_validation/LIGHT_BOX_CONFORMANCE_PROGRAM.md",
        },
        "limitations": [
            "This source-tree status is not a production deployment receipt.",
            f"Bounded replay contracts cover {matrix['summary']['surfaces_with_contracts']} calculations and do not generalize to their entire families.",
            f"All {len(canonical)} residual dispositions remain unresolved until the appropriate numeric, invariant, doctrine/source, regression/parity, or not-applicable receipt is admitted.",
        ],
    }


def validate_status(status: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    summary = status.get("summary", {})
    total = sum(
        int(summary.get(name, 0))
        for name in ("conformant", "partial", "not_applicable", "unresolved")
    )
    if total != summary.get("canonical_calculations"):
        errors.append("$.summary: status counts do not equal canonical denominator")
    if status.get("doctrine_text_changed") is not False:
        errors.append("$.doctrine_text_changed: doctrine must remain unchanged")
    if status.get("universal_current_conformance_supported") and summary.get(
        "unresolved"
    ):
        errors.append(
            "$.universal_current_conformance_supported: unresolved rows remain"
        )
    return errors


def render_json(status: Mapping[str, Any]) -> str:
    return json.dumps(status, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def render_markdown(status: Mapping[str, Any]) -> str:
    summary = status["summary"]
    p0 = summary["production_user_by_status"]
    lines = [
        "# Current Light Box Conformance Status",
        "",
        f"> Generated by `{GENERATOR_PATH}`. Do not edit by hand.",
        "",
        f"- Engine version: `{status['engine_version']}`",
        f"- Inventory fingerprint: `{status['inventory_fingerprint_sha256']}`",
        f"- Evidence source revision: `{status['evidence_source_revision']}`",
        f"- Artifact status: `{status['artifact_status']}`",
        f"- Publication disposition: `{status['publication_disposition']}`",
        "",
        "## Current answer",
        "",
        "The Light Box doctrine is preserved. Universal current-release conformance is **not yet supported** by the evidence: unresolved calculation and release cells remain visible. This is a status report, not a weakening of the doctrine and not an accuracy percentage.",
        "",
        "| Per-surface status | Canonical calculations | P0 product-source calculations |",
        "|---|---:|---:|",
        f"| Conformant | {summary['conformant']} | {p0['conformant']} |",
        f"| Partial | {summary['partial']} | {p0['partial']} |",
        f"| Not applicable | {summary['not_applicable']} | {p0['not_applicable']} |",
        f"| Unresolved | {summary['unresolved']} | {p0['unresolved']} |",
        "",
        f"All {summary['reviewed_families']} families have a structural review disposition. "
        f"{summary['replayed_contracts_passed_local']} bounded local contracts and "
        f"{summary['replayed_contracts_passed_exact_source']} exact-source contracts passed "
        f"across {summary['surfaces_with_replay_contracts']} calculations; "
        f"{summary['surfaces_without_replay_contracts']} calculations have no replay contract yet.",
        "",
        "## Claim disposition",
        "",
        "| Claim | Class | Current status |",
        "|---|---|---|",
    ]
    for claim in status["claim_dispositions"]:
        lines.append(f"| {claim['claim']} | `{claim['class']}` | `{claim['status']}` |")
    lines.extend(
        [
            "",
            "## Release boundary",
            "",
            (
                "This artifact is `exact_release_status` for the recorded clean source revision. "
                "It is source-candidate evidence, not package-publication or deployment evidence. "
                "No Website or Workspace source is changed by this artifact."
                if status["publication_disposition"] == "exact_release_status"
                else "This artifact is `local_unreleased_status`. It must be regenerated from "
                "a clean exact source revision and connected to release evidence before it can "
                "describe a release candidate. No Website or Workspace source is changed by this artifact."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _write(path: Path, text: str) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--matrix", type=Path, default=MATRIX_PATH)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    try:
        matrix_path = args.matrix.resolve()
        output_dir = args.output_dir.resolve() if args.output_dir else None
        json_path = output_dir / JSON_PATH.name if output_dir is not None else JSON_PATH
        markdown_path = (
            output_dir / MARKDOWN_PATH.name if output_dir is not None else MARKDOWN_PATH
        )
        status = build_status(
            _load(MANIFEST_PATH),
            _load(REGISTER_PATH),
            _load(ASSESSMENT_PATH),
            _load(matrix_path),
            matrix_path=matrix_path,
        )
        errors = validate_status(status)
        if errors:
            raise PublicStatusError(
                "status validation failed:\n- " + "\n- ".join(errors)
            )
        outputs = (
            (json_path, render_json(status)),
            (markdown_path, render_markdown(status)),
        )
        if args.check:
            stale = [
                _display_path(path)
                for path, expected in outputs
                if not path.is_file() or path.read_text(encoding="utf-8") != expected
            ]
            if stale:
                raise PublicStatusError("current status is stale: " + ", ".join(stale))
            print("Light Box current status is current.")
            return 0
        for path, text in outputs:
            path.parent.mkdir(parents=True, exist_ok=True)
            _write(path, text)
            print(f"Generated {_display_path(path)}.")
        return 0
    except PublicStatusError as exc:
        print(f"Light Box public status failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
