"""
Moira — test_docstring_governance.py
Compliance checker and self-tests for the HermitiCalc Docstring Governance Standard.

Boundary: owns static analysis of moira/ docstrings via AST. Delegates nothing.
Does not import any moira module at test time.

Public surface:
    test_module_docstrings, test_class_docstring_structure,
    test_machine_contract_validity,
    check_module_docstrings, check_class_docstrings, check_machine_contracts

Import-time side effects: None

External dependency assumptions:
    - stdlib only: ast, json, re, pathlib
    - pytest for test discovery and assertion
"""

import ast
import json
import re
from pathlib import Path
from typing import NamedTuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MOIRA_ROOT = Path(__file__).parents[2] / "moira"

REQUIRED_CLASS_MARKERS = [
    "RITE:",
    "THEOREM:",
    "RITE OF PURPOSE:",
    "LAW OF OPERATION:",
    "[MACHINE_CONTRACT v1]",
    "Canon:",
]

REQUIRED_MC_KEYS = {
    "scope", "id", "risk", "api", "state", "effects",
    "concurrency", "failures", "succession", "agent",
}

VALID_RISK_VALUES = {"low", "medium", "high", "critical"}

MC_PATTERN = re.compile(
    r"\[MACHINE_CONTRACT v1\](.*?)\[/MACHINE_CONTRACT\]",
    re.DOTALL,
)


# ---------------------------------------------------------------------------
# Violation type
# ---------------------------------------------------------------------------

class Violation(NamedTuple):
    file: str    # relative path from workspace root
    entity: str  # module, class name, or method name
    rule: str    # rule ID e.g. "MOD-001", "CLS-001", "MC-003"
    detail: str  # human-readable description of the violation


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _format_violations(violations: list[Violation]) -> str:
    lines = [f"\n{len(violations)} docstring governance violation(s) found:\n"]
    for v in violations:
        lines.append(f"  [{v.rule}] {v.file} :: {v.entity}")
        lines.append(f"    {v.detail}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Extracted checker helpers (importable, testable with tmp_path)
# ---------------------------------------------------------------------------

def check_module_docstrings(path: Path) -> list[Violation]:
    """Check that a single .py file has a non-empty module-level docstring."""
    violations: list[Violation] = []
    try:
        source = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        violations.append(Violation(
            file=str(path),
            entity="<module>",
            rule="IO-001",
            detail=f"Could not read file: {exc}",
        ))
        return violations
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        violations.append(Violation(
            file=str(path),
            entity="<module>",
            rule="PARSE-001",
            detail=f"AST parse error: {exc}",
        ))
        return violations
    docstring = ast.get_docstring(tree)
    if not docstring or not docstring.strip():
        violations.append(Violation(
            file=str(path),
            entity="<module>",
            rule="MOD-001",
            detail="Module has no top-level docstring or docstring is empty.",
        ))
    return violations


def check_class_docstrings(path: Path) -> list[Violation]:
    """Check that every class in a .py file has all required structural markers."""
    violations: list[Violation] = []
    try:
        source = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        violations.append(Violation(
            file=str(path),
            entity="<module>",
            rule="IO-001",
            detail=f"Could not read file: {exc}",
        ))
        return violations
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        violations.append(Violation(
            file=str(path),
            entity="<module>",
            rule="PARSE-001",
            detail=f"AST parse error: {exc}",
        ))
        return violations
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        docstring = ast.get_docstring(node) or ""
        for marker in REQUIRED_CLASS_MARKERS:
            if marker not in docstring:
                violations.append(Violation(
                    file=str(path),
                    entity=node.name,
                    rule="CLS-001",
                    detail=f"Class docstring missing required marker: {marker!r}",
                ))
    return violations


def check_machine_contracts(path: Path) -> list[Violation]:
    """Validate every MACHINE_CONTRACT block found in class docstrings of a .py file."""
    violations: list[Violation] = []
    try:
        source = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        violations.append(Violation(
            file=str(path),
            entity="<module>",
            rule="IO-001",
            detail=f"Could not read file: {exc}",
        ))
        return violations
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        violations.append(Violation(
            file=str(path),
            entity="<module>",
            rule="PARSE-001",
            detail=f"AST parse error: {exc}",
        ))
        return violations
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        docstring = ast.get_docstring(node) or ""
        match = MC_PATTERN.search(docstring)
        if not match:
            continue  # absence already caught by check_class_docstrings
        json_text = match.group(1).strip()
        rel = str(path)
        try:
            contract = json.loads(json_text)
        except json.JSONDecodeError as exc:
            violations.append(Violation(
                file=rel,
                entity=node.name,
                rule="MC-001",
                detail=f"MACHINE_CONTRACT JSON is malformed: {exc}",
            ))
            continue
        # MC-002: required keys
        missing = REQUIRED_MC_KEYS - set(contract.keys())
        if missing:
            violations.append(Violation(
                file=rel,
                entity=node.name,
                rule="MC-002",
                detail=f"MACHINE_CONTRACT missing required keys: {sorted(missing)}",
            ))
        # MC-003: risk value
        if contract.get("risk") not in VALID_RISK_VALUES:
            violations.append(Violation(
                file=rel,
                entity=node.name,
                rule="MC-003",
                detail=f"Invalid risk value: {contract.get('risk')!r}. Must be one of {sorted(VALID_RISK_VALUES)}.",
            ))
        # MC-004: id prefix
        if not str(contract.get("id", "")).startswith("moira."):
            violations.append(Violation(
                file=rel,
                entity=node.name,
                rule="MC-004",
                detail=f"id must start with 'moira.', got: {contract.get('id')!r}",
            ))
        # MC-005: concurrency.thread
        conc = contract.get("concurrency", {})
        if conc.get("thread") != "pure_computation":
            violations.append(Violation(
                file=rel,
                entity=node.name,
                rule="MC-005",
                detail=f"concurrency.thread must be 'pure_computation', got: {conc.get('thread')!r}",
            ))
        # MC-006: concurrency.cross_thread_calls
        if conc.get("cross_thread_calls") != "safe_read_only":
            violations.append(Violation(
                file=rel,
                entity=node.name,
                rule="MC-006",
                detail=f"concurrency.cross_thread_calls must be 'safe_read_only', got: {conc.get('cross_thread_calls')!r}",
            ))
    return violations


# ---------------------------------------------------------------------------
# Property tests — walk the real moira/ corpus
# ---------------------------------------------------------------------------

def test_module_docstrings() -> None:
    """
    Feature: moira-docstring-governance, Property 1: module docstrings exist

    Validates: Requirements 1.1, 8.1
    """
    violations: list[Violation] = []
    for path in sorted(MOIRA_ROOT.rglob("*.py")):
        violations.extend(check_module_docstrings(path))
    assert violations == [], _format_violations(violations)


def test_class_docstring_structure() -> None:
    """
    Feature: moira-docstring-governance, Property 2: class docstrings contain required markers

    Validates: Requirements 3.1, 3.2, 3.9, 4.1, 8.2, 8.3
    """
    violations: list[Violation] = []
    for path in sorted(MOIRA_ROOT.rglob("*.py")):
        violations.extend(check_class_docstrings(path))
    assert violations == [], _format_violations(violations)


def test_machine_contract_validity() -> None:
    """
    Feature: moira-docstring-governance, Property 3: MACHINE_CONTRACT blocks are valid

    Validates: Requirements 4.2, 4.3, 4.4, 4.5, 4.6, 8.4
    """
    violations: list[Violation] = []
    for path in sorted(MOIRA_ROOT.rglob("*.py")):
        violations.extend(check_machine_contracts(path))
    assert violations == [], _format_violations(violations)


# ---------------------------------------------------------------------------
# Unit tests — checker logic via inline synthetic sources (no real file I/O)
# ---------------------------------------------------------------------------

_COMPLIANT_CLASS_BODY = '''\
    """
    RITE: The Synthetic Oracle

    THEOREM: Governs synthetic test data for compliance verification.

    RITE OF PURPOSE:
        Exists solely to exercise the compliance checker in unit tests.
        Provides a minimal but fully compliant class docstring template.

    LAW OF OPERATION:
        Responsibilities:
            - Serve as a compliant fixture for checker unit tests
        Non-responsibilities:
            - Perform any real computation
        Dependencies:
            - None

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.synthetic.SyntheticClass",
      "risk": "low",
      "api": {"frozen": [], "internal": []},
      "state": {"mutable": false, "owners": []},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    pass
'''


def _write_tmp(tmp_path: "Path", source: str, name: str = "mod.py") -> "Path":
    p = tmp_path / name
    p.write_text(source, encoding="utf-8")
    return p


def test_checker_compliant_module_passes(tmp_path: Path) -> None:
    """Synthetic compliant source produces no MOD-001 violations."""
    source = '"""A compliant module docstring."""\n'
    path = _write_tmp(tmp_path, source)
    assert check_module_docstrings(path) == []


def test_checker_missing_module_docstring_produces_mod001(tmp_path: Path) -> None:
    """Missing module docstring produces exactly one MOD-001 violation."""
    source = "x = 1\n"
    path = _write_tmp(tmp_path, source)
    violations = check_module_docstrings(path)
    assert len(violations) == 1
    assert violations[0].rule == "MOD-001"
    assert violations[0].entity == "<module>"


def test_checker_compliant_class_passes(tmp_path: Path) -> None:
    """Class with all required markers produces no CLS-001 violations."""
    source = f'"""Module docstring."""\n\nclass SyntheticClass:\n{_COMPLIANT_CLASS_BODY}\n'
    path = _write_tmp(tmp_path, source)
    assert check_class_docstrings(path) == []


def test_checker_missing_rite_produces_cls001(tmp_path: Path) -> None:
    """Class docstring missing RITE: produces a CLS-001 violation for that marker."""
    body_without_rite = _COMPLIANT_CLASS_BODY.replace("RITE: The Synthetic Oracle", "IDENTITY: The Synthetic Oracle")
    source = f'"""Module docstring."""\n\nclass SyntheticClass:\n{body_without_rite}\n'
    path = _write_tmp(tmp_path, source)
    violations = check_class_docstrings(path)
    rules = [v.rule for v in violations]
    details = [v.detail for v in violations]
    assert "CLS-001" in rules
    assert any("RITE:" in d for d in details)


def test_checker_malformed_json_produces_mc001(tmp_path: Path) -> None:
    """Malformed MACHINE_CONTRACT JSON produces an MC-001 violation."""
    bad_body = _COMPLIANT_CLASS_BODY.replace(
        '"scope": "class"',
        '"scope": "class"  INVALID',
    )
    source = f'"""Module docstring."""\n\nclass SyntheticClass:\n{bad_body}\n'
    path = _write_tmp(tmp_path, source)
    violations = check_machine_contracts(path)
    assert any(v.rule == "MC-001" for v in violations)


def test_checker_missing_risk_key_produces_mc002(tmp_path: Path) -> None:
    """MACHINE_CONTRACT missing the risk key produces an MC-002 violation."""
    bad_body = _COMPLIANT_CLASS_BODY.replace(
        '"risk": "low",\n',
        "",
    )
    source = f'"""Module docstring."""\n\nclass SyntheticClass:\n{bad_body}\n'
    path = _write_tmp(tmp_path, source)
    violations = check_machine_contracts(path)
    assert any(v.rule == "MC-002" for v in violations)
    assert any("risk" in v.detail for v in violations if v.rule == "MC-002")


def test_checker_invalid_risk_value_produces_mc003(tmp_path: Path) -> None:
    """risk value of 'extreme' produces an MC-003 violation."""
    bad_body = _COMPLIANT_CLASS_BODY.replace('"risk": "low"', '"risk": "extreme"')
    source = f'"""Module docstring."""\n\nclass SyntheticClass:\n{bad_body}\n'
    path = _write_tmp(tmp_path, source)
    violations = check_machine_contracts(path)
    assert any(v.rule == "MC-003" for v in violations)
    assert any("extreme" in v.detail for v in violations if v.rule == "MC-003")


def test_checker_wrong_thread_produces_mc005(tmp_path: Path) -> None:
    """concurrency.thread set to 'main_qt' produces an MC-005 violation."""
    bad_body = _COMPLIANT_CLASS_BODY.replace(
        '"thread": "pure_computation"',
        '"thread": "main_qt"',
    )
    source = f'"""Module docstring."""\n\nclass SyntheticClass:\n{bad_body}\n'
    path = _write_tmp(tmp_path, source)
    violations = check_machine_contracts(path)
    assert any(v.rule == "MC-005" for v in violations)
    assert any("main_qt" in v.detail for v in violations if v.rule == "MC-005")
