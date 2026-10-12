"""Capture a revision-bound product-usage snapshot for Light Box priority P0.

The scanner is intentionally conservative.  It admits exact REST path literals
and explicit imports from ``moira`` or ``moira.facade`` in product source.  It
does not guess dynamic routes, method calls on engine objects, or usage from
documentation/tests/generated copies.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = (
    REPO_ROOT
    / "wiki"
    / "03_validation"
    / "LIGHT_BOX_CALCULATION_INVENTORY.generated.json"
)
OUTPUT_PATH = (
    REPO_ROOT / "wiki" / "03_validation" / "LIGHT_BOX_PRODUCT_USAGE_SNAPSHOT.json"
)
SCHEMA_VERSION = "moira.lightbox-product-usage/v1"
SOURCE_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx"}
EXCLUDED_PARTS = {
    ".git",
    ".next",
    ".pytest_cache",
    ".venv",
    "build",
    "coverage",
    "dist",
    "docs",
    "docs-content",
    "node_modules",
    "scratch",
    "tests",
    "wiki",
}


class ProductUsageError(RuntimeError):
    """Raised when a bounded product-usage snapshot cannot be produced."""


def _parse_root(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("root must use NAME=PATH")
    name, raw_path = value.split("=", 1)
    name = name.strip()
    path = Path(raw_path.strip()).resolve()
    if not name or not path.is_dir():
        raise argparse.ArgumentTypeError(f"invalid product root: {value}")
    return name, path


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", action="append", type=_parse_root, required=True)
    parser.add_argument("--audit-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    return parser.parse_args()


def _load_inventory() -> dict[str, Any]:
    value = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ProductUsageError("inventory root must be an object")
    return value


def _git_revision(root: Path) -> str:
    process = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    revision = process.stdout.strip()
    if process.returncode or re.fullmatch(r"[0-9a-f]{40}", revision) is None:
        raise ProductUsageError(f"cannot resolve Git revision for {root}")
    return revision


def _source_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SOURCE_EXTENSIONS:
            continue
        relative = path.relative_to(root)
        lowered = {part.lower() for part in relative.parts}
        if lowered & EXCLUDED_PARTS:
            continue
        name = path.name.lower()
        if (
            ".test." in name
            or ".spec." in name
            or name.endswith("_test.py")
            or name.startswith("test_")
        ):
            continue
        # The website Workspace subtree is a generated copy of MoiraWeb source.
        parts = tuple(part.lower() for part in relative.parts)
        if parts[:3] == ("client", "src", "workspace"):
            continue
        yield path


def _add_callsite(
    result: dict[str, list[dict[str, Any]]],
    surface_id: str,
    *,
    product: str,
    revision: str,
    relative_path: str,
    line: int,
    detection: str,
) -> None:
    result[surface_id].append(
        {
            "product": product,
            "source_revision": revision,
            "source_path": relative_path,
            "source_line": line,
            "detection": detection,
        }
    )


def _contains_exact_route_literal(line: str, route_path: str) -> bool:
    start = line.find(route_path)
    while start >= 0:
        end = start + len(route_path)
        if (
            end == len(line)
            or line[end]
            not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_{}./-"
        ):
            return True
        start = line.find(route_path, start + 1)
    return False


def _scan_python_imports(
    text: str,
    *,
    public_names: Mapping[str, str],
) -> list[tuple[str, int]]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    found: list[tuple[str, int]] = []
    module_aliases: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module in {
            "moira",
            "moira.facade",
        }:
            for alias in node.names:
                surface_id = public_names.get(alias.name)
                if surface_id is not None:
                    found.append((surface_id, node.lineno))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in {"moira", "moira.facade"}:
                    module_aliases.add(alias.asname or alias.name.split(".")[0])
    if module_aliases:
        for node in ast.walk(tree):
            if not isinstance(node, ast.Attribute) or not isinstance(
                node.value, ast.Name
            ):
                continue
            if node.value.id not in module_aliases:
                continue
            surface_id = public_names.get(node.attr)
            if surface_id is not None:
                found.append((surface_id, node.lineno))
    return sorted(set(found))


def build_snapshot(
    inventory: Mapping[str, Any],
    roots: Sequence[tuple[str, Path]],
    *,
    audit_date: str,
) -> dict[str, Any]:
    if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", audit_date) is None:
        raise ProductUsageError("audit date must use YYYY-MM-DD")
    rest_rows = {
        str(row["surface_id"]): row
        for row in inventory["rest_operations"]
        if row["in_lightbox_calculation_scope"]
    }
    paths: dict[str, list[str]] = defaultdict(list)
    for surface_id, row in rest_rows.items():
        paths[str(row["path"])].append(surface_id)
    python_names = {
        str(row["public_name"]): str(row["surface_id"])
        for row in inventory["python_exports"]
        if row["in_lightbox_calculation_scope"] and row["alias_of"] is None
    }
    callsites: dict[str, list[dict[str, Any]]] = defaultdict(list)
    root_records: list[dict[str, Any]] = []
    for product, root in roots:
        revision = _git_revision(root)
        scanned = 0
        for path in _source_files(root):
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError as exc:
                raise ProductUsageError(f"non-UTF-8 source: {path}") from exc
            scanned += 1
            relative = path.relative_to(root).as_posix()
            lines = text.splitlines()
            for line_number, line in enumerate(lines, start=1):
                stripped = line.lstrip()
                if stripped.startswith(("//", "#", "*")) or "/v1/" not in line:
                    continue
                for route_path, surface_ids in paths.items():
                    if not _contains_exact_route_literal(line, route_path):
                        continue
                    for surface_id in surface_ids:
                        _add_callsite(
                            callsites,
                            surface_id,
                            product=product,
                            revision=revision,
                            relative_path=relative,
                            line=line_number,
                            detection="exact_rest_path_literal",
                        )
            if path.suffix.lower() == ".py":
                for surface_id, line_number in _scan_python_imports(
                    text,
                    public_names=python_names,
                ):
                    _add_callsite(
                        callsites,
                        surface_id,
                        product=product,
                        revision=revision,
                        relative_path=relative,
                        line=line_number,
                        detection="explicit_public_python_import",
                    )
        root_records.append(
            {
                "product": product,
                "source_revision": revision,
                "files_scanned": scanned,
                "root_record": "Local path deliberately omitted; product name and Git revision are the portable identity.",
            }
        )
    inventory_rows = {
        str(row["surface_id"]): row
        for collection in ("python_exports", "rest_operations")
        for row in inventory[collection]
        if row["in_lightbox_calculation_scope"]
    }
    entries = []
    for surface_id in sorted(callsites):
        row = inventory_rows[surface_id]
        deduped = {
            json.dumps(item, sort_keys=True): item for item in callsites[surface_id]
        }
        entries.append(
            {
                "surface_id": surface_id,
                "canonical_surface_id": row["canonical_id"],
                "transport": "rest" if surface_id.startswith("rest:") else "python",
                "callsites": sorted(
                    deduped.values(),
                    key=lambda item: (
                        item["product"],
                        item["source_path"],
                        item["source_line"],
                    ),
                ),
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "audit_date": audit_date,
        "engine_version": inventory["engine_version"],
        "inventory_fingerprint_sha256": inventory["surface_fingerprint_sha256"],
        "detection_policy": "Exact REST path literals plus explicit imports from moira or moira.facade in non-test, non-documentation, non-generated product source.",
        "limitations": [
            "Dynamic route construction and calls through engine-object methods require separate human review and are not guessed.",
            "A source callsite proves product use, not runtime reachability, correctness, frequency, or conformance.",
            "Generated website Workspace source is excluded so MoiraWeb remains the sole Workspace authoring source.",
        ],
        "roots": sorted(root_records, key=lambda row: row["product"]),
        "summary": {
            "production_user_surfaces": len(entries),
            "rest_surfaces": sum(row["transport"] == "rest" for row in entries),
            "python_surfaces": sum(row["transport"] == "python" for row in entries),
            "callsites": sum(len(row["callsites"]) for row in entries),
        },
        "entries": entries,
    }


def validate_snapshot(
    snapshot: Mapping[str, Any], inventory: Mapping[str, Any]
) -> list[str]:
    errors: list[str] = []
    known = {
        str(row["surface_id"]): row
        for collection in ("python_exports", "rest_operations")
        for row in inventory[collection]
        if row["in_lightbox_calculation_scope"]
    }
    if snapshot.get("schema_version") != SCHEMA_VERSION:
        errors.append("$.schema_version: unsupported")
    if snapshot.get("inventory_fingerprint_sha256") != inventory.get(
        "surface_fingerprint_sha256"
    ):
        errors.append("$.inventory_fingerprint_sha256: inventory drift")
    entries = snapshot.get("entries")
    if not isinstance(entries, list):
        return [*errors, "$.entries: must be an array"]
    ids = [row.get("surface_id") for row in entries if isinstance(row, dict)]
    if len(ids) != len(set(ids)):
        errors.append("$.entries: duplicate surface IDs")
    for index, row in enumerate(entries):
        if not isinstance(row, dict):
            errors.append(f"$.entries[{index}]: must be an object")
            continue
        surface_id = row.get("surface_id")
        source = known.get(str(surface_id))
        if source is None:
            errors.append(f"$.entries[{index}].surface_id: outside current inventory")
            continue
        if row.get("canonical_surface_id") != source["canonical_id"]:
            errors.append(f"$.entries[{index}].canonical_surface_id: inventory drift")
        if not row.get("callsites"):
            errors.append(f"$.entries[{index}].callsites: empty")
    return errors


def main() -> int:
    args = _args()
    try:
        inventory = _load_inventory()
        snapshot = build_snapshot(inventory, args.root, audit_date=args.audit_date)
        errors = validate_snapshot(snapshot, inventory)
        if errors:
            raise ProductUsageError(
                "snapshot validation failed:\n- " + "\n- ".join(errors[:25])
            )
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix(output.suffix + ".tmp")
        temporary.write_text(
            json.dumps(snapshot, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        temporary.replace(output)
        print(
            f"Captured {snapshot['summary']['production_user_surfaces']} product-used surfaces in {output}."
        )
        return 0
    except (OSError, ProductUsageError, subprocess.SubprocessError) as exc:
        print(f"Light Box product-usage audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
