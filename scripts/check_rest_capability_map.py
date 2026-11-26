"""Check reviewed REST capability bindings and detect changes to the unmapped baseline."""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib
import inspect
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MAP = REPO_ROOT / "docs" / "architecture" / "rest-capability-map.json"


def _callable_id(value):
    return f"{value.__module__}:{value.__qualname__}"


def _load_callable(identifier):
    module, _, name = identifier.partition(":")
    value = importlib.import_module(module)
    for part in name.split("."):
        value = getattr(value, part)
    if not inspect.isroutine(value):
        raise ValueError(f"{identifier} must identify a callable")
    return value


def public_capabilities(direct_modules):
    """Collect owning callable IDs from the reviewed discovery sources."""

    import moira.facade as facade
    from scripts.generate_lightbox_calculation_inventory import _function_classification

    ids = {
        _callable_id(getattr(facade, name)) for name in facade.__all__
        if inspect.isfunction(getattr(facade, name)) and _function_classification(name)[1]
    }
    classes = [facade.Moira]
    for specification in direct_modules:
        module = importlib.import_module(specification["module"])
        ids.update(
            _callable_id(value) for name, value in inspect.getmembers(module, inspect.isfunction)
            if not name.startswith("_") and value.__module__ == module.__name__
        )
        classes.extend(getattr(module, name) for name in specification.get("classes", ()))
    for cls in classes:
        ids.update(
            _callable_id(value) for name, value in inspect.getmembers(cls, inspect.isroutine)
            if not name.startswith("_")
        )
    return ids


def unmapped_capabilities(ledger):
    """Return discovered capability IDs without a reviewed mapping."""

    reviewed = {
        _callable_id(_load_callable(identifier))
        for row in ledger["capabilities"] for identifier in row["engine"]
    }
    return sorted(public_capabilities(ledger["direct_modules"]) - reviewed)


def capability_fingerprint(ids):
    return hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()


def _schema_terms(value, schema):
    """Check reachable references and collect property and selector names."""

    terms = set()
    pending = [value]
    seen = set()
    while pending:
        current = pending.pop()
        if isinstance(current, list):
            pending.extend(current)
        if not isinstance(current, dict):
            continue
        reference = current.get("$ref")
        if reference is not None and reference not in seen:
            try:
                component = schema["components"]["schemas"][reference.removeprefix("#/components/schemas/")]
            except KeyError as exc:
                raise ValueError(f"unresolved schema link {reference}") from exc
            pending.append(component)
            seen.add(reference)
        terms.update(current.get("properties", ()))
        terms.update(item for item in current.get("enum", ()) if isinstance(item, str))
        for key in ("const", "default"):
            if isinstance(current.get(key), str):
                terms.add(current[key])
        if "in" in current and "name" in current:
            terms.add(current["name"])
        pending.extend(current.values())
    return terms


def _check_witness(witness):
    path, _, name = witness.partition("::")
    tree = ast.parse((REPO_ROOT / path).read_text(encoding="utf-8"), filename=path)
    if not any(isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == name for item in ast.walk(tree)):
        raise ValueError(f"missing test witness {witness}")


def check_bindings(ledger, schema):
    """Require the registered method, request variants, response, and named witness."""

    seen = set()
    for row in ledger["capabilities"]:
        label = row["capability"]
        if label in seen or not row["engine"]:
            raise ValueError(f"duplicate or empty capability {label}")
        seen.add(label)
        if "engine_only_reason" in row:
            if not row["engine_only_reason"].strip() or row.get("routes"):
                raise ValueError(f"invalid engine-only boundary for {label}")
            continue
        if not row["routes"] or not row["witness"]:
            raise ValueError(f"missing route or witness for {label}")
        _check_witness(row["witness"])
        for route in row["routes"]:
            method, path = route["operation"].split(maxsplit=1)
            try:
                operation = schema["paths"][path][method.lower()]
            except KeyError as exc:
                raise ValueError(f"{label}: missing {method} {path}") from exc
            request = (operation.get("requestBody"), operation.get("parameters"))
            request_terms = _schema_terms(list(request), schema)
            response_terms = _schema_terms(operation["responses"][route.get("status", "200")], schema)
            for terms, name in ((request_terms, "request"), (response_terms, "response")):
                missing = set(route.get(name, ())) - terms
                if missing:
                    raise ValueError(f"{label}: {method} {path} lacks {name} terms {sorted(missing)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list-unmapped", action="store_true", help="List the current baseline without reviewed bindings.")
    args = parser.parse_args()
    sys.path.insert(0, str(REPO_ROOT))
    from moira_server.app import create_app

    try:
        ledger = json.loads(MAP.read_text(encoding="utf-8"))
        unmapped = unmapped_capabilities(ledger)
        if args.list_unmapped:
            print("\n".join(unmapped))
            return 0
        check_bindings(ledger, create_app().openapi())
        if capability_fingerprint(unmapped) != ledger["unmapped_baseline_sha256"]:
            raise ValueError("the unmapped public surface changed; review the capability map before updating its baseline")
    except (AttributeError, ImportError, KeyError, OSError, ValueError) as exc:
        print(f"REST capability map check failed: {exc}", file=sys.stderr)
        return 1
    print(f"Verified {len(ledger['capabilities'])} capability decisions; {len(unmapped)} baseline IDs await mapping.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
