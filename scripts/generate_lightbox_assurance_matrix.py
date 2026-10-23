"""Generate the Light Box assurance matrix from contracts and receipts."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACTS_PATH = REPO_ROOT / "tests" / "evidence" / "lightbox" / "contracts.json"
RECEIPTS_PATH = (
    REPO_ROOT / "tests" / "evidence" / "lightbox" / "receipts" / "local.generated.json"
)
MANIFEST_PATH = (
    REPO_ROOT
    / "wiki"
    / "03_validation"
    / "LIGHT_BOX_CONFORMANCE_MANIFEST.generated.json"
)
JSON_PATH = (
    REPO_ROOT / "wiki" / "03_validation" / "LIGHT_BOX_ASSURANCE_MATRIX.generated.json"
)
MARKDOWN_PATH = (
    REPO_ROOT / "wiki" / "03_validation" / "LIGHT_BOX_ASSURANCE_MATRIX.generated.md"
)
GENERATOR_PATH = "scripts/generate_lightbox_assurance_matrix.py"
SCHEMA_VERSION = "moira.lightbox-assurance-matrix/v2"
EVIDENCE_CLASSES = (
    "authority",
    "corroboration",
    "invariant",
    "doctrine_source",
    "regression",
    "native_parity",
    "harness",
    "performance",
    "release",
)


class AssuranceMatrixError(RuntimeError):
    """Raised when evidence contracts and receipts cannot form a matrix."""


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
        raise AssuranceMatrixError(f"cannot load {_display_path(path)}") from exc
    if not isinstance(value, dict):
        raise AssuranceMatrixError(
            f"JSON root must be an object: {_display_path(path)}"
        )
    return value


def _sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
    ).hexdigest()


def build_matrix(
    contracts: Mapping[str, Any],
    receipts: Mapping[str, Any],
    manifest: Mapping[str, Any],
    *,
    receipts_path: Path = RECEIPTS_PATH,
) -> dict[str, Any]:
    if contracts.get("schema_version") != "moira.lightbox-evidence-contracts/v1":
        raise AssuranceMatrixError("unsupported contracts schema")
    if receipts.get("schema_version") != "moira.lightbox-evidence-receipts/v2":
        raise AssuranceMatrixError("unsupported receipts schema")
    if manifest.get("schema_version") != "moira.lightbox-conformance-manifest/v2":
        raise AssuranceMatrixError("unsupported manifest schema")
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from scripts.replay_lightbox_receipts import ReceiptReplayError, validate_receipt_binding
    try:
        validate_receipt_binding(receipts, str(manifest["inventory_fingerprint_sha256"]))
    except ReceiptReplayError as exc:
        raise AssuranceMatrixError(str(exc)) from exc
    if receipts.get("contracts_sha256") != _sha(contracts):
        raise AssuranceMatrixError("receipt set was produced from different contracts")
    if receipts.get("inventory_fingerprint_sha256") != manifest.get(
        "inventory_fingerprint_sha256"
    ):
        raise AssuranceMatrixError("receipt and manifest inventory identities disagree")
    contract_by_claim = {str(row["claim_id"]): row for row in contracts["contracts"]}
    receipt_by_claim = {str(row["claim_id"]): row for row in receipts["receipts"]}
    if set(contract_by_claim) != set(receipt_by_claim) or len(receipt_by_claim) != len(receipts["receipts"]):
        raise AssuranceMatrixError(
            "every evidence contract must have exactly one receipt"
        )
    for claim_id, contract in contract_by_claim.items():
        if receipt_by_claim[claim_id].get("contract_sha256") != _sha(contract):
            raise AssuranceMatrixError(f"individual receipt contract drift: {claim_id}")
    surface_claims: dict[str, list[str]] = {}
    for claim_id, contract in contract_by_claim.items():
        for surface_id in contract["surface_ids"]:
            surface_claims.setdefault(str(surface_id), []).append(claim_id)
    canonical = [row for row in manifest["entries"] if row["entry_role"] == "canonical"]
    rows: list[dict[str, Any]] = []
    for entry in canonical:
        surface_id = str(entry["surface_id"])
        claim_ids = sorted(surface_claims.get(surface_id, []))
        cells: dict[str, dict[str, Any]] = {}
        for evidence_class in EVIDENCE_CLASSES:
            matching = [
                claim_id
                for claim_id in claim_ids
                if evidence_class in contract_by_claim[claim_id]["evidence_classes"]
            ]
            statuses = [receipt_by_claim[claim_id]["status"] for claim_id in matching]
            if not matching:
                status = "not_run"
            elif all(value == "passed" for value in statuses):
                status = (
                    "passed_exact_source"
                    if receipts.get("artifact_status") == "exact_source_revision"
                    else "passed_local"
                )
            else:
                status = "failed"
            cells[evidence_class] = {
                "status": status,
                "claim_ids": matching,
                "receipt_ids": [
                    receipt_by_claim[claim_id]["receipt_id"] for claim_id in matching
                ],
            }
        rows.append(
            {
                "surface_id": surface_id,
                "conformance_status": entry["conformance_status"],
                "claim_ids": claim_ids,
                "evidence": cells,
            }
        )
    class_summary = {}
    for evidence_class in EVIDENCE_CLASSES:
        counts = Counter(row["evidence"][evidence_class]["status"] for row in rows)
        class_summary[evidence_class] = {
            status: counts.get(status, 0)
            for status in (
                "passed_local",
                "passed_exact_source",
                "failed",
                "not_run",
            )
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "engine_version": manifest["engine_version"],
        "inventory_fingerprint_sha256": manifest["inventory_fingerprint_sha256"],
        "generated_by": GENERATOR_PATH,
        "contracts_path": _display_path(CONTRACTS_PATH),
        "receipts_path": _display_path(receipts_path),
        "receipt_source_revision": receipts["source_revision"],
        "receipt_artifact_status": receipts["artifact_status"],
        "boundary": "Passed-local means the bounded contract replay passed in an unreleased worktree. Passed-exact-source means it passed from the clean recorded source revision. Neither status is external truth, complete family coverage, package-publication evidence, or deployment evidence.",
        "summary": {
            "canonical_surfaces": len(rows),
            "surfaces_with_contracts": sum(bool(row["claim_ids"]) for row in rows),
            "surfaces_without_contracts": sum(not row["claim_ids"] for row in rows),
            "contracts": len(contract_by_claim),
            "contracts_passed_local": sum(
                row["status"] == "passed" for row in receipts["receipts"]
            )
            if receipts.get("artifact_status") != "exact_source_revision"
            else 0,
            "contracts_passed_exact_source": sum(
                row["status"] == "passed" for row in receipts["receipts"]
            )
            if receipts.get("artifact_status") == "exact_source_revision"
            else 0,
            "contracts_failed": sum(
                row["status"] != "passed" for row in receipts["receipts"]
            ),
            "evidence_classes": class_summary,
        },
        "contracts": [
            {
                "claim_id": claim_id,
                "surface_ids": contract_by_claim[claim_id]["surface_ids"],
                "evidence_classes": contract_by_claim[claim_id]["evidence_classes"],
                "claim_scope": contract_by_claim[claim_id]["claim_scope"],
                "exclusions": contract_by_claim[claim_id]["exclusions"],
                "receipt_id": receipt_by_claim[claim_id]["receipt_id"],
                "status": receipt_by_claim[claim_id]["status"],
                "passed_tests": receipt_by_claim[claim_id]["passed_tests"],
                "artifact_status": receipt_by_claim[claim_id]["artifact_status"],
            }
            for claim_id in sorted(contract_by_claim)
        ],
        "surfaces": rows,
    }


def validate_matrix(
    matrix: Mapping[str, Any], manifest: Mapping[str, Any]
) -> list[str]:
    errors: list[str] = []
    expected = {
        str(row["surface_id"])
        for row in manifest["entries"]
        if row["entry_role"] == "canonical"
    }
    rows = matrix.get("surfaces")
    if not isinstance(rows, list):
        return ["$.surfaces: must be an array"]
    ids = [row.get("surface_id") for row in rows if isinstance(row, dict)]
    if len(ids) != len(set(ids)) or set(ids) != expected:
        errors.append("$.surfaces: must cover every canonical surface exactly once")
    for index, row in enumerate(rows):
        if set(row.get("evidence", {})) != set(EVIDENCE_CLASSES):
            errors.append(
                f"$.surfaces[{index}].evidence: incomplete evidence vocabulary"
            )
    summary = matrix.get("summary", {})
    if summary.get("canonical_surfaces") != len(expected):
        errors.append("$.summary.canonical_surfaces: denominator drift")
    if summary.get("contracts_failed") != 0:
        errors.append("$.summary.contracts_failed: evidence replay failed")
    return errors


def render_json(matrix: Mapping[str, Any]) -> str:
    return json.dumps(matrix, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def render_markdown(matrix: Mapping[str, Any]) -> str:
    summary = matrix["summary"]
    lines = [
        "# Light Box Assurance Matrix",
        "",
        f"> Generated by `{GENERATOR_PATH}`. Do not edit by hand.",
        "",
        f"- Engine version: `{matrix['engine_version']}`",
        f"- Inventory structural fingerprint: `{matrix['inventory_fingerprint_sha256']}`",
        f"- Receipt source revision: `{matrix['receipt_source_revision']}`",
        f"- Receipt artifact status: `{matrix['receipt_artifact_status']}`",
        f"- Canonical surfaces: {summary['canonical_surfaces']}",
        f"- Surfaces with replay contracts: {summary['surfaces_with_contracts']}",
        f"- Surfaces without replay contracts: {summary['surfaces_without_contracts']}",
        "",
        "## Boundary",
        "",
        matrix["boundary"],
        "",
        "The matrix keeps `not_run` cells visible. A passed regression or invariant cell does not satisfy authority, doctrine/source, performance, release, or any other evidence class.",
        "",
        "## Evidence-class coverage",
        "",
        "| Evidence class | Passed local | Passed exact source | Failed | Not run |",
        "|---|---:|---:|---:|---:|",
    ]
    for evidence_class, counts in summary["evidence_classes"].items():
        lines.append(
            f"| `{evidence_class}` | {counts['passed_local']} | "
            f"{counts['passed_exact_source']} | {counts['failed']} | "
            f"{counts['not_run']} |"
        )
    lines.extend(
        [
            "",
            "## Replayed contracts",
            "",
            "| Claim | Surfaces | Evidence classes | Tests passed | Status | Artifact |",
            "|---|---:|---|---:|---|---|",
        ]
    )
    for contract in matrix["contracts"]:
        lines.append(
            f"| `{contract['claim_id']}` | {len(contract['surface_ids'])} | "
            f"`{','.join(contract['evidence_classes'])}` | {contract['passed_tests']} | "
            f"`{contract['status']}` | `{contract['artifact_status']}` |"
        )
    lines.extend(
        [
            "",
            "## Release interpretation",
            "",
            (
                "These receipts prove bounded replays from the clean exact source revision. "
                "They are source-candidate evidence, not package-publication or deployment evidence; "
                "the conformance manifest correctly remains partial/unresolved."
                if matrix["receipt_artifact_status"] == "exact_source_revision"
                else "These receipts prove local bounded replays. They are not exact-source, "
                "package-publication, or deployment evidence; the conformance manifest correctly "
                "remains partial/unresolved."
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
    parser.add_argument("--receipts", type=Path, default=RECEIPTS_PATH)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    try:
        receipts_path = args.receipts.resolve()
        output_dir = args.output_dir.resolve() if args.output_dir else None
        json_path = output_dir / JSON_PATH.name if output_dir is not None else JSON_PATH
        markdown_path = (
            output_dir / MARKDOWN_PATH.name if output_dir is not None else MARKDOWN_PATH
        )
        contracts = _load(CONTRACTS_PATH)
        receipts = _load(receipts_path)
        manifest = _load(MANIFEST_PATH)
        matrix = build_matrix(
            contracts, receipts, manifest, receipts_path=receipts_path
        )
        errors = validate_matrix(matrix, manifest)
        if errors:
            raise AssuranceMatrixError(
                "matrix validation failed:\n- " + "\n- ".join(errors[:25])
            )
        outputs = (
            (json_path, render_json(matrix)),
            (markdown_path, render_markdown(matrix)),
        )
        if args.check:
            stale = [
                _display_path(path)
                for path, expected in outputs
                if not path.is_file() or path.read_text(encoding="utf-8") != expected
            ]
            if stale:
                raise AssuranceMatrixError(
                    "assurance matrix is stale: " + ", ".join(stale)
                )
            print("Light Box assurance matrix is current.")
            return 0
        for path, text in outputs:
            path.parent.mkdir(parents=True, exist_ok=True)
            _write(path, text)
            print(f"Generated {_display_path(path)}.")
        return 0
    except AssuranceMatrixError as exc:
        print(f"Light Box assurance matrix failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
