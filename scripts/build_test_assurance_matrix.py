"""Build and verify Moira's reviewed test-assurance matrix."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
for candidate in (str(TESTS), str(ROOT)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from evidence.contracts import (  # noqa: E402
    CONTRACTS,
    contract_payload,
    contract_sha256,
    validate_registry,
)
from evidence.receipts import (  # noqa: E402
    AssuranceReceiptError,
    evaluate_runtime_assurance,
    load_assurance_requirements,
    validate_requirements_against_contracts,
)


REQUIREMENTS_PATH = TESTS / "evidence" / "assurance_requirements.json"
MATRIX_JSON_PATH = TESTS / "evidence" / "assurance_matrix.json"
MATRIX_MARKDOWN_PATH = TESTS / "evidence" / "assurance_matrix.md"


def _pretty_json_bytes(payload: object) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=True,
            allow_nan=False,
            sort_keys=True,
            indent=2,
        ).encode("ascii")
        + b"\n"
    )


def _matrix_payload(requirements: dict[str, object]) -> dict[str, object]:
    cells = requirements["cells"]
    assert isinstance(cells, list)
    rows: list[dict[str, object]] = []
    for cell in sorted(cells, key=lambda value: str(value["cell_id"])):
        claim_id = str(cell["required_claim_id"])
        contract = CONTRACTS[claim_id]
        payload = contract_payload(contract)
        rows.append(
            {
                "cell_id": cell["cell_id"],
                "product_surface": cell["product_surface"],
                "evidence_class": cell["evidence_class"],
                "claim_id": claim_id,
                "contract_sha256": contract_sha256(contract),
                "expected_bindings": cell["expected_bindings"],
                "coverage_targets": cell["targets"],
                "proves": payload["proves"],
                "does_not_prove": payload["does_not_prove"],
                "required_status": "declared",
            }
        )
    return {
        "schema_version": 1,
        "policy": requirements["policy"],
        "cells": rows,
        "summary": {
            "required_cells": len(rows),
            "evidence_classes": sorted(
                {str(row["evidence_class"]) for row in rows}
            ),
            "global_percentage_gate": None,
        },
    }


def _escape(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _matrix_markdown(payload: dict[str, object]) -> bytes:
    lines = [
        "# Moira test assurance matrix",
        "",
        (
            "This is a generated review surface. It gates declared evidence "
            "cells and exact coverage contexts; it does not treat line or "
            "branch coverage percentage as scientific proof."
        ),
        "",
        "| Cell | Product surface | Evidence | Claim | Expected items | Targets |",
        "|---|---|---|---|---:|---|",
    ]
    cells = payload["cells"]
    assert isinstance(cells, list)
    for cell in cells:
        expected = sum(
            len(binding["nodeids"])
            for binding in cell["expected_bindings"]
        )
        targets = "<br>".join(
            f"{target['path']}::{target['qualname']} "
            f"({'/'.join(target['phases'])})"
            for target in cell["coverage_targets"]
        )
        lines.append(
            "| "
            + " | ".join(
                (
                    _escape(cell["cell_id"]),
                    _escape(cell["product_surface"]),
                    _escape(cell["evidence_class"]),
                    _escape(cell["claim_id"]),
                    str(expected),
                    _escape(targets),
                )
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Claim boundaries",
            "",
        ]
    )
    for cell in cells:
        lines.extend(
            [
                f"### {_escape(cell['cell_id'])}",
                "",
                "Proves:",
                "",
                *[f"- {_escape(value)}" for value in cell["proves"]],
                "",
                "Does not prove:",
                "",
                *[
                    f"- {_escape(value)}"
                    for value in cell["does_not_prove"]
                ],
                "",
            ]
        )
    return ("\n".join(lines).rstrip() + "\n").encode("utf-8")


def _check_exact(path: Path, expected: bytes) -> None:
    try:
        actual = path.read_bytes()
    except OSError as exc:
        raise AssuranceReceiptError(f"generated matrix file is missing: {path}") from exc
    if actual != expected:
        raise AssuranceReceiptError(
            f"generated matrix drifted: {path}; run this script with --write"
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build or check the reviewed assurance matrix, optionally joining "
            "a complete run receipt with pytest-cov test contexts."
        )
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--check",
        action="store_true",
        help="check static policy and require a sealed runtime receipt",
    )
    mode.add_argument(
        "--check-static",
        action="store_true",
        help="check only deterministic generated policy files",
    )
    mode.add_argument("--write", action="store_true")
    parser.add_argument("--receipt-dir", type=Path)
    parser.add_argument("--coverage-file", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        validate_registry(CONTRACTS, root=ROOT, verify_assets=True)
        requirements = load_assurance_requirements(REQUIREMENTS_PATH)
        validate_requirements_against_contracts(requirements, CONTRACTS)
        payload = _matrix_payload(requirements)
        json_bytes = _pretty_json_bytes(payload)
        markdown_bytes = _matrix_markdown(payload)
        if args.write:
            if args.receipt_dir is not None or args.coverage_file is not None:
                raise AssuranceReceiptError(
                    "runtime inputs are not admitted while writing static policy"
                )
            MATRIX_JSON_PATH.write_bytes(json_bytes)
            MATRIX_MARKDOWN_PATH.write_bytes(markdown_bytes)
            print(
                f"wrote {MATRIX_JSON_PATH.relative_to(ROOT)} and "
                f"{MATRIX_MARKDOWN_PATH.relative_to(ROOT)}"
            )
            return 0
        _check_exact(MATRIX_JSON_PATH, json_bytes)
        _check_exact(MATRIX_MARKDOWN_PATH, markdown_bytes)
        if (args.receipt_dir is None) != (args.coverage_file is None):
            raise AssuranceReceiptError(
                "--receipt-dir and --coverage-file must be supplied together"
            )
        if args.check_static and args.receipt_dir is not None:
            raise AssuranceReceiptError(
                "runtime inputs are not admitted with --check-static"
            )
        if args.check and args.receipt_dir is None:
            raise AssuranceReceiptError(
                "--check requires --receipt-dir and --coverage-file; "
                "use --check-static only for generated-file drift"
            )
        if args.check:
            runtime = evaluate_runtime_assurance(
                root=ROOT,
                requirements=requirements,
                contracts=CONTRACTS,
                receipt_dir=args.receipt_dir,
                coverage_file=args.coverage_file,
            )
            print(
                "runtime assurance: "
                f"{len(runtime['cells'])} required cells filled; "
                f"coverage_sha256={runtime['coverage_sha256']}"
            )
            if runtime["regression_only_protected_targets"]:
                print("protected targets reached only by regression evidence:")
                for target in runtime["regression_only_protected_targets"]:
                    print(f"  {target}")
            print(
                "unattributed coverage contexts: "
                f"{len(runtime['unattributed_contexts'])}"
            )
        print(
            f"assurance matrix check passed: {len(payload['cells'])} required cells"
        )
        return 0
    except AssuranceReceiptError as exc:
        print(f"assurance matrix check failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
