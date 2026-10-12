"""Generate the authoritative Light Box public-surface inventory.

The inventory answers a deliberately narrow question: which admitted Python
facade exports and REST operations exist in this source tree, what kind of
surface is each one, where is it owned, and which documentation/tests mention
it?  It does not claim that a calculation is correct, validated, or fully
Light-Box-conformant.  Those are later evidence-contract decisions.
"""

from __future__ import annotations

import argparse
import ast
import dataclasses
import hashlib
import importlib
import importlib.util
import inspect
import json
import os
import re
import sys
from collections import Counter, defaultdict
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = (
    REPO_ROOT
    / "wiki"
    / "03_validation"
    / "LIGHT_BOX_CALCULATION_INVENTORY.generated.json"
)
MARKDOWN_PATH = (
    REPO_ROOT
    / "wiki"
    / "03_validation"
    / "LIGHT_BOX_CALCULATION_INVENTORY.generated.md"
)
CONFORMANCE_MARKDOWN_PATH = (
    REPO_ROOT / "wiki" / "03_validation" / "LIGHT_BOX_CONFORMANCE_MANIFEST.generated.md"
)
GENERATOR_PATH = "scripts/generate_lightbox_calculation_inventory.py"
SCHEMA_VERSION = "moira.lightbox-calculation-inventory/v1"
CLASSIFICATION_VERSION = "moira.lightbox-surface-classification/v1"
HTTP_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD", "TRACE")

_IDENTIFIER_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")
_ROUTE_LITERAL_RE = re.compile(r"/(?:[A-Za-z0-9_.{}:-]+/?)+")

_REFERENCE_FUNCTION_PREFIXES = ("list_", "available_", "load_")
_REFERENCE_FUNCTION_SUFFIXES = (
    "_catalog",
    "_catalogue",
    "_options",
    "_presets",
    "_profile_info",
)
_COMPOSITION_FUNCTION_TOKENS = (
    "profile",
    "network",
    "packet",
    "bundle",
    "receipt",
    "context",
    "assessment",
    "judgement",
    "ranking",
)
_COMPOSITION_ROUTE_SEGMENTS = {
    "assessment",
    "bundle",
    "condition",
    "context",
    "judgement",
    "network",
    "packet",
    "profile",
    "ranking",
    "receipt",
}

# These are transport aliases with an already-admitted canonical reduction
# contract.  Keep this list explicit: path similarity alone is not authority to
# infer alias identity.
ROUTE_ALIASES: Mapping[tuple[str, str], tuple[str, str]] = {
    ("POST", "/v1/pipeline/chart"): ("POST", "/v1/chart/reduction"),
    ("POST", "/v1/pipeline/positions/planet"): (
        "POST",
        "/v1/positions/planet/reduction",
    ),
    ("POST", "/v1/pipeline/positions/sky"): (
        "POST",
        "/v1/positions/sky/reduction",
    ),
}


class LightBoxInventoryError(RuntimeError):
    """Raised when runtime/source truth cannot form a complete inventory."""


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify both committed generated artifacts without rewriting them.",
    )
    return parser.parse_args()


def _relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError as exc:
        raise LightBoxInventoryError(f"source path escapes repository: {path}") from exc


def _canonical_sha256(value: Any) -> str:
    data = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _source_definition_line(path: Path, name: str) -> int | None:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name == name:
                return node.lineno
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets: list[ast.expr]
            if isinstance(node, ast.Assign):
                targets = list(node.targets)
            else:
                targets = [node.target]
            for target in targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return node.lineno
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if (alias.asname or alias.name) == name:
                    return node.lineno
    return None


def _facade_import_map() -> dict[str, tuple[str, str, int]]:
    path = REPO_ROOT / "moira" / "facade.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    result: dict[str, tuple[str, str, int]] = {}
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom) or node.level != 1 or not node.module:
            continue
        module_name = f"moira.{node.module}"
        for alias in node.names:
            if alias.name == "*":
                raise LightBoxInventoryError(
                    "facade star-import prevents ownership audit"
                )
            result[alias.asname or alias.name] = (
                module_name,
                alias.name,
                node.lineno,
            )
    return result


def _module_path(module_name: str) -> Path:
    module = importlib.import_module(module_name)
    raw = inspect.getsourcefile(module)
    if not raw:
        raise LightBoxInventoryError(f"cannot resolve module source: {module_name}")
    return Path(raw)


def _resolve_imported_symbol(
    module_name: str,
    symbol_name: str,
    *,
    seen: frozenset[tuple[str, str]] = frozenset(),
) -> tuple[str, str, Path, int, str] | None:
    """Resolve a public symbol through package re-exports to its definition."""
    key = (module_name, symbol_name)
    if key in seen:
        return None
    next_seen = seen | {key}
    path = _module_path(module_name)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name == symbol_name:
                return module_name, symbol_name, path, node.lineno, "symbol-definition"
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = (
                list(node.targets) if isinstance(node, ast.Assign) else [node.target]
            )
            if any(
                isinstance(target, ast.Name) and target.id == symbol_name
                for target in targets
            ):
                return module_name, symbol_name, path, node.lineno, "symbol-definition"

    package_name = module_name.rpartition(".")[0]
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        for alias in node.names:
            if (alias.asname or alias.name) != symbol_name:
                continue
            if node.level:
                relative_name = "." * node.level + (node.module or "")
                imported_module = importlib.util.resolve_name(
                    relative_name, package_name
                )
            elif node.module:
                imported_module = node.module
            else:
                return None
            resolved = _resolve_imported_symbol(
                imported_module,
                alias.name,
                seen=next_seen,
            )
            if resolved is not None:
                return resolved
            return (
                imported_module,
                alias.name,
                path,
                node.lineno,
                "symbol-import-fallback",
            )
    return None


def _source_owner(
    public_name: str,
    value: Any,
    facade_imports: Mapping[str, tuple[str, str, int]],
) -> dict[str, Any]:
    if inspect.isfunction(value) or inspect.isclass(value):
        raw_path = inspect.getsourcefile(value)
        if not raw_path:
            raise LightBoxInventoryError(
                f"cannot resolve source file for facade export: {public_name}"
            )
        try:
            line = inspect.getsourcelines(value)[1]
        except (OSError, TypeError):
            imported = facade_imports.get(public_name)
            if imported:
                module_name, original_name, _facade_line = imported
                resolved = _resolve_imported_symbol(module_name, original_name)
                if resolved is not None:
                    owner_module, owner_name, path, line, resolution = resolved
                    return {
                        "owner_module": owner_module,
                        "owner_qualname": owner_name,
                        "source_path": _relative(path),
                        "source_line": line,
                        "owner_resolution": resolution,
                    }
            raise LightBoxInventoryError(
                f"cannot resolve source line for facade export: {public_name}"
            )
        return {
            "owner_module": getattr(value, "__module__", "moira.facade"),
            "owner_qualname": getattr(value, "__qualname__", public_name),
            "source_path": _relative(Path(raw_path)),
            "source_line": line,
            "owner_resolution": "runtime-object",
        }

    imported = facade_imports.get(public_name)
    if imported:
        module_name, original_name, facade_line = imported
        resolved = _resolve_imported_symbol(module_name, original_name)
        if resolved is not None:
            owner_module, owner_name, path, line, resolution = resolved
            return {
                "owner_module": owner_module,
                "owner_qualname": owner_name,
                "source_path": _relative(path),
                "source_line": line,
                "owner_resolution": resolution,
            }
        return {
            "owner_module": module_name,
            "owner_qualname": original_name,
            "source_path": "moira/facade.py",
            "source_line": facade_line,
            "owner_resolution": "facade-import-fallback",
        }

    facade_path = REPO_ROOT / "moira" / "facade.py"
    line = _source_definition_line(facade_path, public_name)
    if line is None:
        raise LightBoxInventoryError(
            f"cannot resolve source ownership for facade export: {public_name}"
        )
    return {
        "owner_module": "moira.facade",
        "owner_qualname": public_name,
        "source_path": "moira/facade.py",
        "source_line": line,
        "owner_resolution": "facade-local-definition",
    }


def _export_kind(value: Any) -> str:
    if inspect.isfunction(value):
        return "function"
    if inspect.isclass(value):
        if issubclass(value, BaseException):
            return "exception"
        if issubclass(value, Enum):
            return "enum"
        if dataclasses.is_dataclass(value):
            return "dataclass"
        return "class"
    return "value"


def _function_classification(name: str) -> tuple[str, bool, str, str | None]:
    if name.startswith("validate_"):
        return (
            "validation_helper",
            False,
            "explicit validate_* helper; verifies an existing result rather than producing an admitted calculation",
            "validation-helper-prefix",
        )
    if name.startswith(_REFERENCE_FUNCTION_PREFIXES) or name.endswith(
        _REFERENCE_FUNCTION_SUFFIXES
    ):
        return (
            "reference_query",
            False,
            "explicit list/availability/catalog/options surface; reference discovery rather than a calculation",
            "reference-query-name",
        )
    if any(token in name for token in _COMPOSITION_FUNCTION_TOKENS):
        return (
            "composition_profile",
            True,
            "assembles a typed profile, network, context, assessment, judgement, ranking, packet, bundle, or receipt",
            "composition-name",
        )
    return (
        "calculation",
        True,
        "conservative default for an admitted public callable; later conformance work may refine its stage/evidence contract",
        "conservative-callable-default",
    )


def _route_classification(
    method: str,
    path: str,
    tags: Sequence[str],
) -> tuple[str, bool, str, str]:
    if not path.startswith("/v1/") or path.startswith("/v1/meta/"):
        return (
            "operational_meta",
            False,
            "health, readiness, version, kernel, or route-registry metadata",
            "operational-path",
        )
    if method == "GET":
        return (
            "reference_query",
            False,
            "GET reference/catalog/discovery surface; explicitly outside the calculation denominator",
            "get-reference-route",
        )
    if path.startswith("/v1/pipeline/") or any(
        tag.startswith("website-") for tag in tags
    ):
        return (
            "transport_adapter",
            True,
            "website/support transport over an admitted calculation or inspection contract",
            "website-transport-route",
        )
    segments = {segment for segment in path.split("/") if segment}
    if segments & _COMPOSITION_ROUTE_SEGMENTS:
        return (
            "composition_profile",
            True,
            "typed composition/profile/network/context/receipt result",
            "composition-route-segment",
        )
    return (
        "calculation",
        True,
        "conservative default for a versioned non-GET operation",
        "conservative-operation-default",
    )


def _documentation_paths() -> tuple[Path, ...]:
    paths: set[Path] = set()
    for root_name in ("wiki", "docs"):
        root = REPO_ROOT / root_name
        if root.is_dir():
            paths.update(path for path in root.rglob("*.md") if path.is_file())
    for name in ("README.md", "PROVENANCE.md", "CHANGELOG.md"):
        path = REPO_ROOT / name
        if path.is_file():
            paths.add(path)
    # Derived Light Box reports cannot count as independent documentation of
    # the surfaces from which they were generated.
    paths.difference_update({MARKDOWN_PATH, CONFORMANCE_MARKDOWN_PATH})
    paths.difference_update(
        path
        for path in tuple(paths)
        if path.name.startswith("LIGHT_BOX_") and path.name.endswith(".generated.md")
    )
    return tuple(sorted(paths))


def _test_paths() -> tuple[Path, ...]:
    root = REPO_ROOT / "tests"
    return tuple(
        sorted(
            path
            for path in root.rglob("*.py")
            if path.is_file() and not path.name.startswith("test_lightbox_")
        )
    )


def _read_texts(paths: Iterable[Path]) -> tuple[tuple[str, str], ...]:
    rows: list[tuple[str, str]] = []
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise LightBoxInventoryError(f"non-UTF-8 audit source: {path}") from exc
        rows.append((_relative(path), text))
    return tuple(rows)


def _identifier_reference_index(
    names: set[str],
    texts: Sequence[tuple[str, str]],
) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {name: [] for name in names}
    for relative_path, text in texts:
        mentioned = set(_IDENTIFIER_RE.findall(text)) & names
        for name in mentioned:
            result[name].append(relative_path)
    return {name: sorted(set(paths)) for name, paths in result.items()}


def _route_reference_index(
    rows: Sequence[Mapping[str, Any]],
    texts: Sequence[tuple[str, str]],
) -> dict[str, list[str]]:
    """Index exact route, operation-id, and distinctive handler mentions once."""
    route_ids: dict[str, set[str]] = defaultdict(set)
    parameterized_routes: list[tuple[tuple[str, ...], str]] = []
    identifier_ids: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        surface_id = str(row["surface_id"])
        route = str(row["path"])
        route_ids[route].add(surface_id)
        if "{" in route:
            parameterized_routes.append(
                (tuple(route.strip("/").split("/")), surface_id)
            )
        operation_id = str(row["operation_id"])
        identifier_ids[operation_id].add(surface_id)
        handler_name = str(row["handler_qualname"]).rsplit(".", 1)[-1]
        if len(handler_name) >= 8:
            identifier_ids[handler_name].add(surface_id)

    result: dict[str, list[str]] = {str(row["surface_id"]): [] for row in rows}
    for relative_path, text in texts:
        mentioned_ids: set[str] = set()
        route_literals = set(_ROUTE_LITERAL_RE.findall(text))
        for route in route_literals & route_ids.keys():
            mentioned_ids.update(route_ids[route])
        for literal in route_literals:
            literal_parts = tuple(literal.strip("/").split("/"))
            for template_parts, surface_id in parameterized_routes:
                if len(template_parts) != len(literal_parts):
                    continue
                if all(
                    template.startswith("{")
                    and template.endswith("}")
                    or template == actual
                    for template, actual in zip(template_parts, literal_parts)
                ):
                    mentioned_ids.add(surface_id)
        for identifier in set(_IDENTIFIER_RE.findall(text)) & identifier_ids.keys():
            mentioned_ids.update(identifier_ids[identifier])
        for surface_id in mentioned_ids:
            result[surface_id].append(relative_path)
    return {surface_id: sorted(set(paths)) for surface_id, paths in result.items()}


def _schema_name(schema: Any) -> str:
    if not isinstance(schema, dict):
        return "none"
    reference = schema.get("$ref")
    if isinstance(reference, str):
        return reference.rsplit("/", 1)[-1]
    alternatives = schema.get("oneOf") or schema.get("anyOf")
    if isinstance(alternatives, list):
        return " | ".join(_schema_name(item) for item in alternatives)
    if schema.get("type") == "array":
        return f"array[{_schema_name(schema.get('items'))}]"
    return str(schema.get("type", "inline"))


def _request_schema(operation: Mapping[str, Any]) -> str:
    request_body = operation.get("requestBody", {})
    content = request_body.get("content", {}) if isinstance(request_body, dict) else {}
    media = content.get("application/json", {}) if isinstance(content, dict) else {}
    return _schema_name(media.get("schema") if isinstance(media, dict) else None)


def _response_schema(operation: Mapping[str, Any]) -> str:
    responses = operation.get("responses", {})
    if not isinstance(responses, dict):
        return "none"
    for code in ("200", "201", "202", "default"):
        response = responses.get(code)
        if not isinstance(response, dict):
            continue
        content = response.get("content", {})
        if not isinstance(content, dict):
            continue
        media = content.get("application/json")
        if isinstance(media, dict):
            return _schema_name(media.get("schema"))
        if content:
            first = next(iter(content.values()))
            if isinstance(first, dict):
                return _schema_name(first.get("schema"))
    return "none"


def _python_id(name: str) -> str:
    return f"python:moira.facade:{name}"


def _rest_id(method: str, path: str) -> str:
    return f"rest:{method}:{path}"


def _build_python_exports(
    documentation: Sequence[tuple[str, str]],
    tests: Sequence[tuple[str, str]],
) -> list[dict[str, Any]]:
    import moira.facade as facade

    names = list(facade.__all__)
    if len(names) != len(set(names)):
        duplicates = sorted(name for name, count in Counter(names).items() if count > 1)
        raise LightBoxInventoryError(f"duplicate facade exports: {duplicates}")

    doc_index = _identifier_reference_index(set(names), documentation)
    test_index = _identifier_reference_index(set(names), tests)
    import_map = _facade_import_map()

    function_groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    for name in names:
        value = getattr(facade, name)
        if inspect.isfunction(value):
            function_groups[(value.__module__, value.__qualname__)].append(name)
    canonical_function_names = {
        key: sorted(group)[0] for key, group in function_groups.items()
    }

    rows: list[dict[str, Any]] = []
    for name in sorted(names):
        value = getattr(facade, name)
        export_kind = _export_kind(value)
        owner = _source_owner(name, value, import_map)
        if export_kind == "function":
            surface_kind, in_scope, rationale, basis = _function_classification(name)
            canonical_name = canonical_function_names[
                (value.__module__, value.__qualname__)
            ]
            canonical_id = _python_id(canonical_name)
            alias_of = canonical_id if canonical_name != name else None
            exclusion_reason = None if in_scope else rationale
        else:
            surface_kind = (
                "excluded_type" if export_kind != "value" else "excluded_value"
            )
            in_scope = False
            rationale = (
                "public type/exception/enum/dataclass declaration; not an executable calculation"
                if export_kind != "value"
                else "public constant or immutable value; not an executable calculation"
            )
            basis = "non-callable-export"
            canonical_id = _python_id(name)
            alias_of = None
            exclusion_reason = rationale

        rows.append(
            {
                "surface_id": _python_id(name),
                "canonical_id": canonical_id,
                "alias_of": alias_of,
                "public_name": name,
                "export_kind": export_kind,
                "surface_kind": surface_kind,
                "in_lightbox_calculation_scope": in_scope,
                "classification_basis": basis,
                "classification_rationale": rationale,
                "exclusion_reason": exclusion_reason,
                **owner,
                "documentation_paths": doc_index[name],
                "test_paths": test_index[name],
            }
        )
    return rows


def _route_endpoint_map(app: Any) -> dict[tuple[str, str], Any]:
    from fastapi.routing import APIRoute

    result: dict[tuple[str, str], Any] = {}
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        for method in route.methods or set():
            upper = method.upper()
            if upper not in HTTP_METHODS:
                continue
            key = (upper, route.path)
            if key in result:
                raise LightBoxInventoryError(f"duplicate FastAPI operation: {key}")
            result[key] = route.endpoint
    return result


def _build_rest_operations(
    documentation: Sequence[tuple[str, str]],
    tests: Sequence[tuple[str, str]],
) -> list[dict[str, Any]]:
    from moira_server.app import create_app

    app = create_app()
    schema = app.openapi()
    endpoint_map = _route_endpoint_map(app)
    rows: list[dict[str, Any]] = []

    for path, path_item in schema.get("paths", {}).items():
        if not isinstance(path_item, dict):
            continue
        for method_lower, operation in path_item.items():
            method = method_lower.upper()
            if method not in HTTP_METHODS or not isinstance(operation, dict):
                continue
            key = (method, path)
            endpoint = endpoint_map.get(key)
            if endpoint is None:
                raise LightBoxInventoryError(
                    f"OpenAPI operation has no FastAPI endpoint owner: {method} {path}"
                )
            raw_path = inspect.getsourcefile(endpoint)
            if not raw_path:
                raise LightBoxInventoryError(
                    f"cannot resolve endpoint source: {method} {path}"
                )
            try:
                source_line = inspect.getsourcelines(endpoint)[1]
            except (OSError, TypeError) as exc:
                raise LightBoxInventoryError(
                    f"cannot resolve endpoint line: {method} {path}"
                ) from exc

            tags = tuple(str(tag) for tag in operation.get("tags", ()))
            operation_id = str(operation.get("operationId") or "")
            if not operation_id:
                raise LightBoxInventoryError(
                    f"OpenAPI operation lacks operationId: {method} {path}"
                )
            surface_kind, in_scope, rationale, basis = _route_classification(
                method,
                path,
                tags,
            )
            alias_target = ROUTE_ALIASES.get(key)
            alias_of = _rest_id(*alias_target) if alias_target else None
            canonical_id = alias_of or _rest_id(method, path)
            handler_name = getattr(endpoint, "__name__", operation_id)
            rows.append(
                {
                    "surface_id": _rest_id(method, path),
                    "canonical_id": canonical_id,
                    "alias_of": alias_of,
                    "method": method,
                    "path": path,
                    "tags": list(tags),
                    "operation_id": operation_id,
                    "request_schema": _request_schema(operation),
                    "response_schema": _response_schema(operation),
                    "surface_kind": surface_kind,
                    "in_lightbox_calculation_scope": in_scope,
                    "classification_basis": basis,
                    "classification_rationale": rationale,
                    "exclusion_reason": None if in_scope else rationale,
                    "handler_module": getattr(endpoint, "__module__", ""),
                    "handler_qualname": getattr(endpoint, "__qualname__", handler_name),
                    "source_path": _relative(Path(raw_path)),
                    "source_line": source_line,
                    "documentation_paths": [],
                    "test_paths": [],
                }
            )

    rows.sort(key=lambda row: (row["path"], HTTP_METHODS.index(row["method"])))
    documentation_index = _route_reference_index(rows, documentation)
    test_index = _route_reference_index(rows, tests)
    for row in rows:
        surface_id = row["surface_id"]
        row["documentation_paths"] = documentation_index[surface_id]
        row["test_paths"] = test_index[surface_id]
    ids = {row["surface_id"] for row in rows}
    if len(ids) != len(rows):
        raise LightBoxInventoryError("duplicate REST surface IDs")
    for source, target in ROUTE_ALIASES.items():
        source_id = _rest_id(*source)
        target_id = _rest_id(*target)
        if source_id not in ids:
            raise LightBoxInventoryError(f"declared REST alias is absent: {source_id}")
        if target_id not in ids:
            raise LightBoxInventoryError(
                f"declared REST alias target is absent: {target_id}"
            )
    return rows


def _count_by(rows: Sequence[Mapping[str, Any]], key: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row[key]) for row in rows).items()))


def build_inventory() -> dict[str, Any]:
    os.environ.setdefault("MOIRA_NO_DOWNLOAD", "1")
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))

    import moira

    documentation = _read_texts(_documentation_paths())
    tests = _read_texts(_test_paths())
    python_exports = _build_python_exports(documentation, tests)
    rest_operations = _build_rest_operations(documentation, tests)

    python_in_scope = [
        row for row in python_exports if row["in_lightbox_calculation_scope"]
    ]
    rest_in_scope = [
        row for row in rest_operations if row["in_lightbox_calculation_scope"]
    ]
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "classification_version": CLASSIFICATION_VERSION,
        "generated_by": GENERATOR_PATH,
        "engine_version": moira.__version__,
        "authority": {
            "python": "moira.facade.__all__ plus runtime object/source ownership",
            "rest": "moira_server.app.create_app().openapi() plus FastAPI endpoint ownership",
            "documentation": "identifier/path mentions in repository Markdown; a mention is not validation evidence",
            "tests": "identifier/path mentions in repository tests; a mention is not proof of coverage",
        },
        "scope_rule": (
            "All admitted facade functions and versioned non-GET REST operations are "
            "conservatively in calculation scope unless an explicit classification "
            "rule records a reference, validation-helper, or operational exclusion."
        ),
        "limitations": [
            "Inventory membership is not a correctness or validation claim.",
            "Documentation and test links are lexical ownership leads, not evidence-class admissions.",
            "Composition/profile surfaces remain in calculation scope because they derive public results.",
            "Catalog/reference, validation-helper, type/value, and operational/meta exclusions remain explicit and reviewable.",
            "Runtime stage, residual, authority, tolerance, and release-conformance fields belong to later Light Box work packages.",
        ],
        "summary": {
            "python_exports": len(python_exports),
            "python_in_scope": len(python_in_scope),
            "python_aliases": sum(
                row["alias_of"] is not None for row in python_exports
            ),
            "python_by_export_kind": _count_by(python_exports, "export_kind"),
            "python_by_surface_kind": _count_by(python_exports, "surface_kind"),
            "python_in_scope_without_documentation_mentions": sum(
                not row["documentation_paths"] for row in python_in_scope
            ),
            "python_in_scope_without_test_mentions": sum(
                not row["test_paths"] for row in python_in_scope
            ),
            "rest_operations": len(rest_operations),
            "rest_in_scope": len(rest_in_scope),
            "rest_aliases": sum(row["alias_of"] is not None for row in rest_operations),
            "rest_by_surface_kind": _count_by(rest_operations, "surface_kind"),
            "rest_in_scope_without_documentation_mentions": sum(
                not row["documentation_paths"] for row in rest_in_scope
            ),
            "rest_in_scope_without_test_mentions": sum(
                not row["test_paths"] for row in rest_in_scope
            ),
        },
        "source_contract": {
            "python_surface_ids_sha256": _canonical_sha256(
                [row["surface_id"] for row in python_exports]
            ),
            "rest_surface_ids_sha256": _canonical_sha256(
                [row["surface_id"] for row in rest_operations]
            ),
        },
        "python_exports": python_exports,
        "rest_operations": rest_operations,
    }
    payload["surface_fingerprint_sha256"] = _canonical_sha256(payload)
    return payload


def render_json(payload: Mapping[str, Any] | None = None) -> str:
    current = dict(payload or build_inventory())
    return json.dumps(current, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _escape_cell(value: Any) -> str:
    return (
        str(value if value not in (None, "") else "—")
        .replace("|", r"\|")
        .replace("\n", " ")
    )


def _reference_summary(paths: Sequence[str]) -> str:
    if not paths:
        return "—"
    first = paths[0]
    if len(paths) == 1:
        return f"`{first}`"
    return f"`{first}` +{len(paths) - 1}"


def _summary_rows(values: Mapping[str, int]) -> list[str]:
    return [f"| `{key}` | {value} |" for key, value in values.items()]


def render_markdown(payload: Mapping[str, Any] | None = None) -> str:
    current = dict(payload or build_inventory())
    summary = current["summary"]
    python_rows = current["python_exports"]
    rest_rows = current["rest_operations"]
    lines = [
        "# Light Box Calculation Inventory",
        "",
        "> Generated by `scripts/generate_lightbox_calculation_inventory.py`. Do not edit by hand.",
        "",
        f"- Schema: `{current['schema_version']}`",
        f"- Classification: `{current['classification_version']}`",
        f"- Engine version: `{current['engine_version']}`",
        f"- Surface fingerprint: `{current['surface_fingerprint_sha256']}`",
        "- Python authority: `moira.facade.__all__` plus runtime source ownership",
        "- REST authority: `moira_server.app.create_app().openapi()` plus FastAPI endpoint ownership",
        "",
        "## Boundary",
        "",
        "This artifact inventories admitted public surfaces. It does **not** say that every listed calculation is correct, validated, documented, traced, or Light-Box-conformant. It makes the denominator explicit so later work can attach stage, documentation, residual/evidence, and release receipts without silently omitting a surface.",
        "",
        "Conservative rule: an ambiguous public callable remains in calculation scope. Types, constants, explicit catalog/reference queries, result validators, and operational metadata are excluded only with a recorded classification reason. Composition/profile surfaces remain in scope because they derive public results.",
        "",
        "## Summary",
        "",
        "| Surface | Total | In calculation scope | Explicit aliases | In-scope without documentation mention | In-scope without test mention |",
        "|---|---:|---:|---:|---:|---:|",
        "| Python facade | "
        f"{summary['python_exports']} | {summary['python_in_scope']} | "
        f"{summary['python_aliases']} | "
        f"{summary['python_in_scope_without_documentation_mentions']} | "
        f"{summary['python_in_scope_without_test_mentions']} |",
        "| REST operations | "
        f"{summary['rest_operations']} | {summary['rest_in_scope']} | "
        f"{summary['rest_aliases']} | "
        f"{summary['rest_in_scope_without_documentation_mentions']} | "
        f"{summary['rest_in_scope_without_test_mentions']} |",
        "",
        "### Python export kinds",
        "",
        "| Kind | Count |",
        "|---|---:|",
        *_summary_rows(summary["python_by_export_kind"]),
        "",
        "### Python surface classifications",
        "",
        "| Classification | Count |",
        "|---|---:|",
        *_summary_rows(summary["python_by_surface_kind"]),
        "",
        "### REST surface classifications",
        "",
        "| Classification | Count |",
        "|---|---:|",
        *_summary_rows(summary["rest_by_surface_kind"]),
        "",
        "## Classification semantics",
        "",
        "| Classification | Calculation denominator | Meaning |",
        "|---|---|---|",
        "| `calculation` | Yes | Conservative default for a public computation, search, transform, or derived result. |",
        "| `composition_profile` | Yes | Produces a derived profile, network, context, assessment, judgement, ranking, packet, bundle, or receipt. |",
        "| `transport_adapter` | Yes | Public transport alias over an admitted calculation or inspection contract. |",
        "| `reference_query` | No | Catalog, table, options, presets, availability, or discovery lookup. |",
        "| `validation_helper` | No | Validates an existing result shape/invariant rather than producing a domain calculation. |",
        "| `operational_meta` | No | Health, readiness, version, kernel, or route-registry metadata. |",
        "| `excluded_type` | No | Public class, dataclass, enum, or exception declaration. |",
        "| `excluded_value` | No | Public constant or immutable value. |",
        "",
        "## Python callable inventory",
        "",
        "All public facade functions appear exactly once. Non-callable exports are fully enumerated in the JSON artifact and summarized above.",
        "",
        "| Surface ID | Public name | Classification | Scope | Canonical/alias | Owner | Documentation | Tests |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in python_rows:
        if row["export_kind"] != "function":
            continue
        alias = row["alias_of"] or "canonical"
        lines.append(
            "| "
            f"`{_escape_cell(row['surface_id'])}` | `{_escape_cell(row['public_name'])}` | "
            f"`{_escape_cell(row['surface_kind'])}` | "
            f"{'yes' if row['in_lightbox_calculation_scope'] else 'no'} | "
            f"`{_escape_cell(alias)}` | "
            f"`{_escape_cell(row['source_path'])}:{row['source_line']}` | "
            f"{_reference_summary(row['documentation_paths'])} | "
            f"{_reference_summary(row['test_paths'])} |"
        )

    lines.extend(
        [
            "",
            "## REST operation inventory",
            "",
            "Every registered OpenAPI operation appears exactly once. Explicit pipeline aliases point to their canonical reduction operation.",
            "",
            "| Surface ID | Method | Path | Classification | Scope | Canonical/alias | Request → response | Owner | Documentation | Tests |",
            "|---|---|---|---|---|---|---|---|---|---|",
        ]
    )
    for row in rest_rows:
        alias = row["alias_of"] or "canonical"
        lines.append(
            "| "
            f"`{_escape_cell(row['surface_id'])}` | `{row['method']}` | "
            f"`{_escape_cell(row['path'])}` | `{_escape_cell(row['surface_kind'])}` | "
            f"{'yes' if row['in_lightbox_calculation_scope'] else 'no'} | "
            f"`{_escape_cell(alias)}` | "
            f"`{_escape_cell(row['request_schema'])}` → `{_escape_cell(row['response_schema'])}` | "
            f"`{_escape_cell(row['source_path'])}:{row['source_line']}` | "
            f"{_reference_summary(row['documentation_paths'])} | "
            f"{_reference_summary(row['test_paths'])} |"
        )

    lines.extend(
        [
            "",
            "## Reading the ownership links",
            "",
            "- `Owner` is resolved from the live imported object or FastAPI endpoint and is authoritative for this inventory revision.",
            "- `Documentation` and `Tests` are lexical repository mentions. They are leads for the next audit pass, not proof that the document or test governs the surface.",
            "- Empty mention columns are visible gaps. They are not silently filled by a generic report.",
            "- Alias rows remain explicit and retain their own public identity; their `canonical_id` prevents duplicate conformance claims later.",
            "",
            "## Next Light Box layer",
            "",
            "A later work package must attach to each in-scope canonical ID: stage/derivation manifest, input and policy semantics, documentation owner, evidence class, authority/comparator, corpus, metric/tolerance or invariant, residual disposition, exclusions, release identity, and reproducible receipt. This inventory deliberately does not infer those claims from names or test mentions.",
            "",
        ]
    )
    return "\n".join(lines)


def _write_atomic(path: Path, text: str) -> None:
    temporary = path.with_name(f"{path.name}.tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    temporary.replace(path)


def main() -> int:
    args = _parse_args()
    try:
        payload = build_inventory()
        json_text = render_json(payload)
        markdown_text = render_markdown(payload)
    except (ImportError, OSError, LightBoxInventoryError, ValueError) as exc:
        print(f"Light Box inventory generation failed: {exc}", file=sys.stderr)
        return 1

    expected = ((JSON_PATH, json_text), (MARKDOWN_PATH, markdown_text))
    if args.check:
        stale = [
            path
            for path, text in expected
            if not path.is_file() or path.read_text(encoding="utf-8") != text
        ]
        if stale:
            print(
                "Light Box calculation inventory is stale: "
                + ", ".join(_relative(path) for path in stale),
                file=sys.stderr,
            )
            print(
                "Run .\\.venv\\Scripts\\python.exe "
                "scripts\\generate_lightbox_calculation_inventory.py",
                file=sys.stderr,
            )
            return 1
        print("Light Box calculation inventory is current.")
        return 0

    for path, text in expected:
        _write_atomic(path, text)
        print(f"Generated {_relative(path)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
