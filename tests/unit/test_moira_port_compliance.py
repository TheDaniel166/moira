"""Port compliance checks for moira/ source files."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

_MOIRA_ROOT = Path(__file__).parents[2] / "moira"


def _iter_python_sources(root: Path) -> list[Path]:
    """Return Python source files under *root*, excluding caches."""
    return sorted(
        path
        for path in root.rglob("*.py")
        if "__pycache__" not in path.parts
    )


_ALL_SOURCE_PY = _iter_python_sources(_MOIRA_ROOT)

assert _ALL_SOURCE_PY, f"No .py files found under {_MOIRA_ROOT}"


def _source_id(path: Path) -> str:
    """Return a short test ID relative to the moira root."""
    return str(path.relative_to(_MOIRA_ROOT))


_FORBIDDEN_IMPORT_ROOTS = {
    "PyQt6",
    "shared.ui",
    "shared.qt_sovereign",
}

_FORBIDDEN_TYPING_NAMES = {
    "Optional",
    "Union",
    "Dict",
    "List",
    "Tuple",
    "Set",
    "FrozenSet",
    "Type",
    "TypeVar",
    "Callable",
}

_FORBIDDEN_FUTURE_IMPORT = re.compile(
    r"from\s+__future__\s+import\s+annotations"
)


def _is_forbidden_import(module_name: str | None) -> bool:
    """Return True when *module_name* matches a forbidden import root."""
    if not module_name:
        return False
    return any(
        module_name == root or module_name.startswith(f"{root}.")
        for root in _FORBIDDEN_IMPORT_ROOTS
    )


@pytest.mark.parametrize("path", _ALL_SOURCE_PY, ids=_source_id)
def test_no_forbidden_port_patterns(path: Path) -> None:
    """
    No moira source file may use forbidden import roots or pre-3.14 typing
    patterns.
    """
    source = path.read_text(encoding="utf-8-sig")

    assert not _FORBIDDEN_FUTURE_IMPORT.search(source), (
        f"{_source_id(path)}: 'from __future__ import annotations' is forbidden in Python 3.14 "
        f"(PEP 563 is native - remove this import)"
    )

    tree = ast.parse(source, filename=str(path))

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _is_forbidden_import(alias.name):
                    pytest.fail(
                        f"{_source_id(path)}:{node.lineno} forbidden import "
                        f"'import {alias.name}'"
                    )

        if isinstance(node, ast.ImportFrom):
            if _is_forbidden_import(node.module):
                pytest.fail(
                    f"{_source_id(path)}:{node.lineno} forbidden import "
                    f"'from {node.module} import ...'"
                )

            if node.module == "typing":
                for alias in node.names:
                    assert alias.name not in _FORBIDDEN_TYPING_NAMES, (
                        f"{_source_id(path)}:{node.lineno} forbidden import "
                        f"'from typing import {alias.name}' - "
                        f"see python314-standards.md for the replacement"
                    )

            if node.module == "__future__":
                for alias in node.names:
                    if alias.name == "annotations":
                        pytest.fail(
                            f"{_source_id(path)}:{node.lineno} forbidden import "
                            "'from __future__ import annotations'"
                        )

        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "typing"
            and node.attr in _FORBIDDEN_TYPING_NAMES
        ):
            pytest.fail(
                f"{_source_id(path)}:{node.lineno} forbidden 'typing.{node.attr}' - "
                f"see python314-standards.md for the replacement"
            )
