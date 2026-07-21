"""Port compliance checks for moira/ source files."""

from __future__ import annotations

import ast
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
    No moira source file may depend on forbidden application-layer imports.

    Moira supports Python 3.10 through 3.14, so compatible ``typing`` names
    and ``from __future__ import annotations`` remain lawful engine syntax.
    """
    source = path.read_text(encoding="utf-8-sig")

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
