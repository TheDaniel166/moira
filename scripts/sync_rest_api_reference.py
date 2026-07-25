"""Synchronize the generated route inventory in the REST API reference."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_PATH = REPO_ROOT / "wiki" / "02_services" / "REST_API_REFERENCE.md"

SUMMARY_START = "<!-- BEGIN GENERATED REST SURFACE SUMMARY -->"
SUMMARY_END = "<!-- END GENERATED REST SURFACE SUMMARY -->"
INVENTORY_START = "<!-- BEGIN GENERATED REST ROUTE INVENTORY -->"
INVENTORY_END = "<!-- END GENERATED REST ROUTE INVENTORY -->"
HTTP_METHODS = ("get", "post", "put", "patch", "delete", "options", "head", "trace")


class RestReferenceError(ValueError):
    """Raised when the generated REST reference block cannot be synchronized."""


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the committed generated blocks without rewriting them.",
    )
    return parser.parse_args()


def _replace_block(text: str, start: str, end: str, body: str) -> str:
    pattern = re.compile(
        rf"{re.escape(start)}.*?{re.escape(end)}",
        flags=re.DOTALL,
    )
    if len(pattern.findall(text)) != 1:
        raise RestReferenceError(f"expected exactly one generated block: {start}")
    return pattern.sub(f"{start}\n{body.rstrip()}\n{end}", text)


def _escape_table_cell(value: Any) -> str:
    return str(value or "—").replace("|", r"\|").replace("\n", " ").strip()


def _surface(app: Any) -> tuple[str, str]:
    schema = app.openapi()
    paths = schema.get("paths")
    if not isinstance(paths, dict) or not paths:
        raise RestReferenceError("FastAPI OpenAPI schema has no paths")

    operations: list[tuple[str, str, dict[str, Any]]] = []
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method in HTTP_METHODS:
            operation = path_item.get(method)
            if isinstance(operation, dict):
                operations.append((path, method.upper(), operation))

    ordered_paths = sorted(paths)
    versioned_paths = [path for path in ordered_paths if path.startswith("/v1")]
    operational_paths = [path for path in ordered_paths if not path.startswith("/v1")]

    method_counts: dict[str, int] = {}
    for _path, method, _operation in operations:
        method_counts[method] = method_counts.get(method, 0) + 1
    method_summary = ", ".join(
        f"{method} {method_counts[method]}"
        for method in (value.upper() for value in HTTP_METHODS)
        if method in method_counts
    )

    summary = "\n".join(
        [
            f"- Application: `{app.title}` `{app.version}`",
            f"- Registered OpenAPI paths: {len(ordered_paths)}",
            f"- Registered OpenAPI operations: {len(operations)} ({method_summary})",
            f"- Operational/meta paths: {len(operational_paths)}",
            f"- Versioned `/v1` paths: {len(versioned_paths)}",
            "- OpenAPI path, when enabled by server configuration: `/openapi.json`",
            "- Interactive docs, when enabled by server configuration: `/docs` and `/redoc`",
            "- Generation source: `moira_server.app.create_app().openapi()` via "
            "`scripts/sync_rest_api_reference.py`",
        ]
    )

    rows = [
        "## Generated Registered Route Inventory",
        "",
        "This exact-path inventory is generated from the current FastAPI OpenAPI "
        "registry. Narrative sections above explain admission boundaries; this "
        "table is the completeness check for registered transport paths.",
        "",
        "| Method | Path | Tags | Operation ID |",
        "|---|---|---|---|",
    ]
    for path, method, operation in sorted(
        operations,
        key=lambda item: (item[0], HTTP_METHODS.index(item[1].lower())),
    ):
        tags = ", ".join(operation.get("tags", []))
        operation_id = operation.get("operationId", "—")
        rows.append(
            "| "
            f"`{method}` | `{_escape_table_cell(path)}` | "
            f"{_escape_table_cell(tags)} | `{_escape_table_cell(operation_id)}` |"
        )
    return summary, "\n".join(rows)


def render() -> str:
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))

    from moira_server.app import create_app

    summary, inventory = _surface(create_app())
    text = REFERENCE_PATH.read_text(encoding="utf-8")
    text = _replace_block(text, SUMMARY_START, SUMMARY_END, summary)
    return _replace_block(text, INVENTORY_START, INVENTORY_END, inventory)


def main() -> int:
    args = _parse_args()
    try:
        rendered = render()
    except (ImportError, OSError, RestReferenceError) as exc:
        print(f"REST API reference synchronization failed: {exc}", file=sys.stderr)
        return 1

    existing = REFERENCE_PATH.read_text(encoding="utf-8")
    if args.check:
        if existing != rendered:
            print(
                "REST API reference route inventory is stale; run "
                "python scripts/sync_rest_api_reference.py",
                file=sys.stderr,
            )
            return 1
        print("REST API reference route inventory is current.")
        return 0

    REFERENCE_PATH.write_text(rendered, encoding="utf-8", newline="\n")
    print(f"Synchronized {REFERENCE_PATH.relative_to(REPO_ROOT)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
