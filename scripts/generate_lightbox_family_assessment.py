"""Generate the reviewed Light Box family assessment and gap queue."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = (
    REPO_ROOT
    / "wiki"
    / "03_validation"
    / "LIGHT_BOX_CALCULATION_INVENTORY.generated.json"
)
REGISTER_PATH = (
    REPO_ROOT / "wiki" / "03_validation" / "LIGHT_BOX_FAMILY_REGISTER.generated.json"
)
MANIFEST_PATH = (
    REPO_ROOT
    / "wiki"
    / "03_validation"
    / "LIGHT_BOX_CONFORMANCE_MANIFEST.generated.json"
)
POLICY_PATH = (
    REPO_ROOT / "wiki" / "03_validation" / "LIGHT_BOX_FAMILY_REVIEW_POLICY.json"
)
JSON_PATH = (
    REPO_ROOT / "wiki" / "03_validation" / "LIGHT_BOX_FAMILY_ASSESSMENT.generated.json"
)
MARKDOWN_PATH = (
    REPO_ROOT / "wiki" / "03_validation" / "LIGHT_BOX_FAMILY_ASSESSMENT.generated.md"
)
GENERATOR_PATH = "scripts/generate_lightbox_family_assessment.py"
SCHEMA_VERSION = "moira.lightbox-family-assessment/v1"
STATUSES = ("strong_exemplar", "partial", "mixed", "major_gap", "unresolved")
STAGES = (
    "stage_2_exemplars",
    "stage_3_product_use",
    "stage_4_phenomena_relationships",
    "stage_5_remaining_tail",
)


class FamilyAssessmentError(RuntimeError):
    """Raised when family review artifacts disagree."""


def _relative(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FamilyAssessmentError(f"cannot load {_relative(path)}") from exc
    if not isinstance(value, dict):
        raise FamilyAssessmentError(f"JSON root must be an object: {_relative(path)}")
    return value


def _complete(values: Sequence[str], vocabulary: Sequence[str]) -> dict[str, int]:
    counts = Counter(values)
    return {name: counts.get(name, 0) for name in vocabulary}


def _status_finding(status: str) -> str:
    return {
        "strong_exemplar": "Preserve the existing inspectability pattern; close exact-release and per-surface evidence gaps without weakening it.",
        "partial": "Retain the implemented calculation while mapping its missing stage, semantic, evidence, residual, or release fields.",
        "mixed": "Split the family by operation and reuse the strongest witness/receipt pattern for opaque siblings.",
        "major_gap": "Prioritize paired receipt or generated-documentation coverage; do not infer evidence from implementation depth alone.",
        "unresolved": "Perform a new source-and-runtime review before making a public capability claim.",
    }[status]


def build_assessment(
    inventory: Mapping[str, Any],
    register: Mapping[str, Any],
    manifest: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    fingerprints = {
        inventory.get("surface_fingerprint_sha256"),
        register.get("inventory_fingerprint_sha256"),
        manifest.get("inventory_fingerprint_sha256"),
    }
    if len(fingerprints) != 1:
        raise FamilyAssessmentError(
            "inventory, family register, and manifest fingerprints disagree"
        )
    inventory_rows = {
        str(row["surface_id"]): row
        for collection in ("python_exports", "rest_operations")
        for row in inventory[collection]
        if row["in_lightbox_calculation_scope"]
    }
    manifest_rows = {
        str(row["surface_id"]): row
        for row in manifest["entries"]
        if row["entry_role"] == "canonical"
    }
    by_family: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in register["entries"]:
        if row["entry_role"] == "canonical":
            by_family[str(row["family_id"])].append(row)
    families: list[dict[str, Any]] = []
    for family_id in sorted(by_family):
        rows = by_family[family_id]
        statuses = {str(row["assessment_status"]) for row in rows}
        if len(statuses) != 1:
            raise FamilyAssessmentError(f"family has conflicting status: {family_id}")
        status = statuses.pop()
        review_stages = sorted(
            {str(row["review_stage"]) for row in rows},
            key=STAGES.index,
        )
        source_rows = [inventory_rows[str(row["surface_id"])] for row in rows]
        docs = sorted(
            {path for row in source_rows for path in row.get("documentation_paths", [])}
        )
        tests = sorted(
            {path for row in source_rows for path in row.get("test_paths", [])}
        )
        source_paths = sorted({str(row["source_path"]) for row in source_rows})
        surface_manifest = [manifest_rows[str(row["surface_id"])] for row in rows]
        conformance_counts = _complete(
            [str(row["conformance_status"]) for row in surface_manifest],
            ("conformant", "partial", "not_applicable", "unresolved"),
        )
        missing_docs = [
            str(row["surface_id"])
            for row in source_rows
            if not row.get("documentation_paths")
        ]
        missing_tests = [
            str(row["surface_id"]) for row in source_rows if not row.get("test_paths")
        ]
        p0_ids = [str(row["surface_id"]) for row in rows if row["priority"] == "P0"]
        families.append(
            {
                "family_id": family_id,
                "family_label": rows[0]["family_label"],
                "domain_group": rows[0]["domain_group"],
                "review_state": "reviewed",
                "review_stages": review_stages,
                "assessment_status": status,
                "canonical_surface_count": len(rows),
                "python_surface_count": sum(
                    row["transport"] == "python" for row in rows
                ),
                "rest_surface_count": sum(row["transport"] == "rest" for row in rows),
                "production_user_surface_count": len(p0_ids),
                "production_user_surface_ids": sorted(p0_ids),
                "conformance_counts": conformance_counts,
                "ownership_sources": source_paths,
                "documentation_leads": docs,
                "test_leads": tests,
                "missing_documentation_surface_ids": sorted(missing_docs),
                "missing_test_surface_ids": sorted(missing_tests),
                "finding": _status_finding(status),
                "claim_boundary": (
                    "Reviewed is a structural gap disposition. Documentation/test paths are leads; "
                    "only per-surface manifest receipts can establish conformance."
                ),
            }
        )
    summary = {
        "family_count": len(families),
        "reviewed_families": sum(row["review_state"] == "reviewed" for row in families),
        "canonical_surface_count": sum(
            row["canonical_surface_count"] for row in families
        ),
        "production_user_surface_count": sum(
            row["production_user_surface_count"] for row in families
        ),
        "families_by_status": _complete(
            [row["assessment_status"] for row in families], STATUSES
        ),
        "families_by_review_stage": _complete(
            [stage for row in families for stage in row["review_stages"]],
            STAGES,
        ),
        "families_with_missing_documentation": sum(
            bool(row["missing_documentation_surface_ids"]) for row in families
        ),
        "families_with_missing_tests": sum(
            bool(row["missing_test_surface_ids"]) for row in families
        ),
        "surface_conformance_counts": _complete(
            [
                str(row["conformance_status"])
                for row in manifest["entries"]
                if row["entry_role"] == "canonical"
            ],
            ("conformant", "partial", "not_applicable", "unresolved"),
        ),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "engine_version": inventory["engine_version"],
        "inventory_fingerprint_sha256": inventory["surface_fingerprint_sha256"],
        "review_date": policy["review_date"],
        "generated_by": GENERATOR_PATH,
        "policy_path": _relative(POLICY_PATH),
        "program_path": "wiki/03_validation/LIGHT_BOX_CONFORMANCE_PROGRAM.md",
        "review_boundary": policy["review_boundary"],
        "limitations": [
            "Family status guides remediation and cannot be aggregated into an accuracy or conformance percentage.",
            "A family can be reviewed while every member remains unresolved in the per-surface manifest.",
            "Product usage is a static source snapshot, not telemetry or proof that a path executed in production.",
        ],
        "summary": summary,
        "families": families,
    }


def validate_assessment(
    assessment: Mapping[str, Any],
    register: Mapping[str, Any],
) -> list[str]:
    errors: list[str] = []
    expected_families = {
        str(row["family_id"])
        for row in register["entries"]
        if row["entry_role"] == "canonical"
    }
    rows = assessment.get("families")
    if not isinstance(rows, list):
        return ["$.families: must be an array"]
    ids = [row.get("family_id") for row in rows if isinstance(row, dict)]
    if len(ids) != len(set(ids)):
        errors.append("$.families: duplicate family IDs")
    if set(ids) != expected_families:
        errors.append("$.families: does not exactly cover the family register")
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"$.families[{index}]: must be an object")
            continue
        if row.get("review_state") != "reviewed":
            errors.append(f"$.families[{index}].review_state: must be reviewed")
        if row.get("assessment_status") not in STATUSES:
            errors.append(f"$.families[{index}].assessment_status: invalid")
        if not row.get("review_stages") or any(
            stage not in STAGES for stage in row["review_stages"]
        ):
            errors.append(f"$.families[{index}].review_stages: invalid")
        if row.get("canonical_surface_count", 0) < 1:
            errors.append(f"$.families[{index}].canonical_surface_count: invalid")
    summary = assessment.get("summary", {})
    if summary.get("reviewed_families") != len(expected_families):
        errors.append("$.summary.reviewed_families: incomplete")
    if (
        summary.get("canonical_surface_count")
        != register["summary"]["canonical_entries"]
    ):
        errors.append("$.summary.canonical_surface_count: denominator drift")
    return errors


def render_json(assessment: Mapping[str, Any]) -> str:
    return json.dumps(assessment, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def render_markdown(assessment: Mapping[str, Any]) -> str:
    summary = assessment["summary"]
    lines = [
        "# Light Box Family Assessment",
        "",
        f"> Generated by `{GENERATOR_PATH}`. Do not edit by hand.",
        "",
        f"- Engine version: `{assessment['engine_version']}`",
        f"- Inventory fingerprint: `{assessment['inventory_fingerprint_sha256']}`",
        f"- Review date: `{assessment['review_date']}`",
        f"- Reviewed families: {summary['reviewed_families']} / {summary['family_count']}",
        f"- Canonical surfaces: {summary['canonical_surface_count']}",
        f"- P0 production-source surfaces: {summary['production_user_surface_count']}",
        "",
        "## Boundary",
        "",
        assessment["review_boundary"],
        "",
        "A family disposition is not a conformance score. `Strong exemplar` means a pattern is worth preserving; `major gap` means the implementation lacks a complete public/evidence mapping, not that its mathematics is wrong.",
        "",
        "## Status summary",
        "",
        "| Family disposition | Families |",
        "|---|---:|",
    ]
    for status, count in summary["families_by_status"].items():
        lines.append(f"| `{status}` | {count} |")
    lines.extend(
        [
            "",
            "| Per-surface conformance | Canonical surfaces |",
            "|---|---:|",
        ]
    )
    for status, count in summary["surface_conformance_counts"].items():
        lines.append(f"| `{status}` | {count} |")
    lines.extend(
        [
            "",
            "## Reviewed queue",
            "",
            "| Family | Domain | Disposition | Stages | Canonical | P0 | Partial | Unresolved | Missing docs | Missing tests |",
            "|---|---|---|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in assessment["families"]:
        counts = row["conformance_counts"]
        lines.append(
            f"| `{row['family_id']}` | `{row['domain_group']}` | `{row['assessment_status']}` | "
            f"`{','.join(row['review_stages'])}` | {row['canonical_surface_count']} | "
            f"{row['production_user_surface_count']} | {counts['partial']} | {counts['unresolved']} | "
            f"{len(row['missing_documentation_surface_ids'])} | {len(row['missing_test_surface_ids'])} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "All families have a reviewed structural disposition, satisfying the audit-coverage gate. The per-surface manifest remains the authority for actual conformance. Unresolved rows stay visible and block a universal current-release claim.",
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
    args = parser.parse_args()
    try:
        inventory = _load(INVENTORY_PATH)
        register = _load(REGISTER_PATH)
        manifest = _load(MANIFEST_PATH)
        policy = _load(POLICY_PATH)
        assessment = build_assessment(inventory, register, manifest, policy)
        errors = validate_assessment(assessment, register)
        if errors:
            raise FamilyAssessmentError(
                "assessment validation failed:\n- " + "\n- ".join(errors[:25])
            )
        outputs = (
            (JSON_PATH, render_json(assessment)),
            (MARKDOWN_PATH, render_markdown(assessment)),
        )
        if args.check:
            stale = [
                _relative(path)
                for path, expected in outputs
                if not path.is_file() or path.read_text(encoding="utf-8") != expected
            ]
            if stale:
                raise FamilyAssessmentError(
                    "family assessment is stale: " + ", ".join(stale)
                )
            print("Light Box family assessment is current.")
            return 0
        for path, text in outputs:
            _write(path, text)
            print(f"Generated {_relative(path)}.")
        return 0
    except FamilyAssessmentError as exc:
        print(f"Light Box family assessment failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
