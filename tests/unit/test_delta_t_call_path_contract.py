"""Source-level guardrails for JD-aware Delta-T call paths."""

from __future__ import annotations

import ast
from pathlib import Path


_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_MOIRA_ROOT = _REPOSITORY_ROOT / "moira"


def _dotted_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _dotted_name(node.value)
        if parent is not None:
            return f"{parent}.{node.attr}"
    return None


def _generic_ut_to_tt_symbols(tree: ast.AST) -> tuple[set[str], set[str]]:
    """Return directly imported names and imported module paths for ut_to_tt."""

    direct_names: set[str] = set()
    module_names: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module in {"julian", "moira.julian"}:
                for imported in node.names:
                    if imported.name == "ut_to_tt":
                        direct_names.add(imported.asname or imported.name)
            elif node.module in {None, "moira"}:
                for imported in node.names:
                    if imported.name == "julian":
                        module_names.add(imported.asname or imported.name)
        elif isinstance(node, ast.Import):
            for imported in node.names:
                if imported.name == "moira.julian":
                    module_names.add(imported.asname or imported.name)

    return direct_names, module_names


def test_live_moira_callers_leave_generic_ut_to_tt_year_derivation_to_policy() -> None:
    """Runtime callers must not inject a discontinuous calendar-month year hint.

    The explicit ``year`` parameter remains part of the public compatibility
    surface and may be exercised by public tests and documentation.  This
    invariant deliberately scans only live ``moira`` source: astronomy callers
    must supply the UT1 JD and, when needed, a named policy.  The conversion
    layer then selects its continuous Julian-date year coordinate.  NASA's
    published month-midpoint convention is reserved for explicit catalog
    compatibility adapters.
    """

    inspected: list[tuple[str, int]] = []
    violations: list[str] = []

    for path in sorted(_MOIRA_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        direct_names, module_names = _generic_ut_to_tt_symbols(tree)

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            called_name = _dotted_name(node.func)
            is_generic_call = called_name in direct_names or any(
                called_name == f"{module_name}.ut_to_tt"
                for module_name in module_names
            )
            if not is_generic_call:
                continue

            relative_path = path.relative_to(_REPOSITORY_ROOT).as_posix()
            inspected.append((relative_path, node.lineno))
            has_positional_year = len(node.args) > 1
            has_starred_positionals = any(
                isinstance(argument, ast.Starred) for argument in node.args
            )
            has_year_keyword = any(keyword.arg == "year" for keyword in node.keywords)
            has_uninspectable_keywords = any(
                keyword.arg is None for keyword in node.keywords
            )
            if (
                has_positional_year
                or has_starred_positionals
                or has_year_keyword
                or has_uninspectable_keywords
            ):
                violations.append(
                    f"{relative_path}:{node.lineno}: {ast.unparse(node)}"
                )

    inspected_paths = {path for path, _line in inspected}
    assert {"moira/houses.py", "moira/stars.py"} <= inspected_paths
    assert not violations, (
        "Live astronomy callers must not override generic ut_to_tt year "
        "derivation; use a named delta_t_policy or ut_to_tt_nasa_canon instead:\n"
        + "\n".join(violations)
    )


_READER_BOUND_CLOCK_MODULES = (
    "_solar.py",
    "asteroids.py",
    "astrocartography.py",
    "chart.py",
    "comets.py",
    "eclipse.py",
    "occultations.py",
    "orbits.py",
    "phase.py",
    "phenomena.py",
    "planetary_nodes.py",
    "planetocentric.py",
    "planets.py",
    "progressions.py",
    "ssb.py",
    "transits.py",
    "transits_aspects.py",
    "transits_equatorial.py",
)


def test_reader_bound_modules_do_not_bypass_ephemeris_clock_binding() -> None:
    """Reader-backed computation must not call the generic UT1-to-TT path."""

    violations: list[str] = []
    for filename in _READER_BOUND_CLOCK_MODULES:
        path = _MOIRA_ROOT / filename
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        direct_names, module_names = _generic_ut_to_tt_symbols(tree)

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            called_name = _dotted_name(node.func)
            if called_name in direct_names or any(
                called_name == f"{module_name}.ut_to_tt"
                for module_name in module_names
            ):
                violations.append(
                    f"moira/{filename}:{node.lineno}: {ast.unparse(node)}"
                )

    assert not violations, (
        "Reader-bound modules must use _ut1_to_ephemeris_tt so historical "
        "Delta-T is bound to the content-identified kernel basis:\n"
        + "\n".join(violations)
    )
