"""
Moira — test_docstring_governance.py
Compliance checker and self-tests for Moira's AGENTS.md docstring contracts.

Boundary: owns static analysis of moira/ docstrings via AST. Delegates nothing.
Does not import any moira module at test time.

Public surface:
    test_module_docstrings, test_class_docstring_structure,
    test_machine_contract_validity,
    check_module_docstrings, check_class_docstrings, check_machine_contracts, main

Direct execution is a stdlib-only static preflight. It reports all module,
class, and machine-contract violations without invoking pytest or Moira.

Import-time side effects: None

External dependency assumptions:
    - stdlib only for the checker and command-line preflight
    - pytest for test discovery and assertion
    - PyYAML only inside the workflow-wiring self-test
"""

import argparse
import ast
import json
import re
import sys
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
CONCURRENCY_PROFILES = {
    "pure_computation": "safe_read_only",
    "request_local": "forbidden",
}

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

def _get_flexible_docstring(node: ast.AST) -> str | None:
    """
    Retrieve a docstring from a node even if it's not the first statement.
    Scans the body for the first expression that consists of a string constant.
    """
    if not hasattr(node, "body") or not isinstance(node.body, list):
        return None
    for item in node.body:
        # Ignore imports and future statements
        if isinstance(item, (ast.Import, ast.ImportFrom)):
            continue
        # Check for the first Expr that is a constant string
        if isinstance(item, ast.Expr) and isinstance(item.value, ast.Constant) and isinstance(item.value.value, str):
            return item.value.value
        # If we hit logic before a docstring, there is no docstring
        break
    return None


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
    
    # Try standard discovery first, then flexible discovery
    docstring = ast.get_docstring(tree) or _get_flexible_docstring(tree)
    
    if not docstring or not docstring.strip():
        violations.append(Violation(
            file=str(path),
            entity="<module>",
            rule="MOD-001",
            detail="Module has no top-level docstring or docstring is empty.",
        ))
    return violations


def _is_vessel_class(node: ast.ClassDef) -> bool:
    """
    Determine if a class is a passive 'Vessel' (data only) rather than an 'Actor'.
    Vessels are decorated with @dataclass, or inherit from NamedTuple/Enum/StrEnum,
    and typically lack custom methods beyond lifecycle helpers.
    """
    # 1. Check decorators
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Name) and decorator.id == "dataclass":
            return True
        if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name) and decorator.func.id == "dataclass":
            return True
            
    # 2. Check base classes
    for base in node.bases:
        if isinstance(base, ast.Name) and base.id in {
            "NamedTuple",
            "Enum",
            "StrEnum",
            "Protocol",
        }:
            return True
            
    # 3. Check for behavioral methods (Actors have logic)
    methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
    behavioral_methods = [
        m for m in methods 
        if m.name not in {
            "__init__",
            "__post_init__",
            "__repr__",
            "__str__",
            "__eq__",
            "__reduce__",
            "__reduce_ex__",
        }
    ]
    if not behavioral_methods:
        return True
        
    return False


def _has_split_class_docstring(node: ast.ClassDef) -> bool:
    """Return whether a class begins with two independent string expressions."""

    if len(node.body) < 2:
        return False

    return all(
        isinstance(item, ast.Expr)
        and isinstance(item.value, ast.Constant)
        and isinstance(item.value.value, str)
        for item in node.body[:2]
    )


def check_class_docstrings(path: Path) -> list[Violation]:
    """Check that core logic classes have required structural markers."""
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
            
        docstring = ast.get_docstring(node) or _get_flexible_docstring(node) or ""
        is_vessel = _is_vessel_class(node)
        has_mc = "[MACHINE_CONTRACT" in docstring

        if _has_split_class_docstring(node):
            violations.append(Violation(
                file=str(path),
                entity=node.name,
                rule="CLS-003",
                detail=(
                    "Class begins with consecutive string literals; only the first "
                    "is the runtime docstring. Merge them into one docstring."
                ),
            ))
        
        # Policy: Mandatory high-ceremony markers for:
        # 1. Classes explicitly declaring a MACHINE_CONTRACT
        # 2. 'Actor' classes (those with logic/methods)
        # 3. Anything that isn't a simple 'Vessel'
        needs_ceremony = has_mc or not is_vessel
        
        if needs_ceremony:
            for marker in REQUIRED_CLASS_MARKERS:
                if marker not in docstring:
                    violations.append(Violation(
                        file=str(path),
                        entity=node.name,
                        rule="CLS-001",
                        detail=f"Architectural class docstring missing required marker: {marker!r}",
                    ))
        else:
            # For vessels, we only require a basic docstring exists
            if not docstring.strip():
                violations.append(Violation(
                    file=str(path),
                    entity=node.name,
                    rule="CLS-002",
                    detail="Data vessel class must have a basic docstring.",
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
            if "[MACHINE_CONTRACT" in docstring:
                violations.append(Violation(
                    file=str(path), entity=node.name, rule="MC-001",
                    detail="MACHINE_CONTRACT must contain a closed v1 JSON block.",
                ))
            continue  # complete absence already caught by check_class_docstrings
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
        if not isinstance(contract, dict):
            violations.append(Violation(
                file=rel, entity=node.name, rule="MC-001",
                detail="MACHINE_CONTRACT JSON must be an object.",
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
        if contract.get("risk") not in tuple(VALID_RISK_VALUES):
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
        # MC-005/006: explicit, paired concurrency profiles; never allow a
        # request-local actor to claim cross-thread read-only safety.
        conc = contract.get("concurrency", {})
        if not isinstance(conc, dict):
            violations.append(Violation(
                file=rel, entity=node.name, rule="MC-005",
                detail="concurrency must be an object declaring a supported profile.",
            ))
            continue
        thread = conc.get("thread")
        if thread not in tuple(CONCURRENCY_PROFILES):
            violations.append(Violation(
                file=rel,
                entity=node.name,
                rule="MC-005",
                detail=f"concurrency.thread must be one of {sorted(CONCURRENCY_PROFILES)}, got: {thread!r}",
            ))
        else:
            expected = CONCURRENCY_PROFILES[thread]
            if conc.get("cross_thread_calls") != expected:
                violations.append(Violation(
                    file=rel,
                    entity=node.name,
                    rule="MC-006",
                    detail=f"concurrency.cross_thread_calls must be {expected!r} for {thread!r}, got: {conc.get('cross_thread_calls')!r}",
                ))
        # MC-007: request confinement is meaningful only with named mutable
        # state ownership and an explicit prohibition on off-owner mutation.
        if thread == "request_local":
            state = contract.get("state", {})
            owners = state.get("owners") if isinstance(state, dict) else None
            if (not isinstance(state, dict) or state.get("mutable") is not True
                    or not isinstance(owners, list) or not owners
                    or not all(isinstance(owner, str) and owner.strip() for owner in owners)
                    or conc.get("owner_thread_only_mutation") is not True):
                violations.append(Violation(
                    file=rel, entity=node.name, rule="MC-007",
                    detail="request_local requires mutable state, named nonempty owners, and owner_thread_only_mutation: true.",
                ))
    return violations


def main(argv: list[str] | None = None) -> int:
    """Run the existing checkers without engine imports or test dependencies."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path,
                        help="Python files to check; default: the entire moira/ tree")
    args = parser.parse_args(argv)
    paths = args.paths or sorted(MOIRA_ROOT.rglob("*.py"))
    if not paths:
        parser.error("no engine Python files found; refusing an empty preflight")
    for path in paths:
        if path.suffix != ".py" or not path.is_file():
            parser.error(f"expected an existing Python file: {path}")

    violations: list[Violation] = []
    for path in paths:
        for checker in (check_module_docstrings, check_class_docstrings, check_machine_contracts):
            violations.extend(checker(path))
    if violations:
        print(_format_violations(violations), file=sys.stderr)
        return 1
    print(f"Engine docstring preflight passed: {len(paths)} Python files checked.")
    return 0


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


def test_checker_protocol_with_basic_contract_docstring_passes(tmp_path: Path) -> None:
    """Protocol interfaces are contracts, not stateful architectural actors."""
    source = (
        '"""Module docstring."""\n\n'
        "from typing import Protocol\n\n"
        "class SyntheticProtocol(Protocol):\n"
        '    """Side-effect-free callable interface."""\n\n'
        "    def __call__(self, value: float) -> float: ...\n"
    )
    path = _write_tmp(tmp_path, source)
    assert check_class_docstrings(path) == []


def test_checker_split_class_docstring_produces_cls003(tmp_path: Path) -> None:
    """Consecutive class string literals cannot hide governance content."""

    source = (
        '"""Module docstring."""\n\n'
        "class SplitVessel:\n"
        '    """Short runtime summary."""\n'
        '    """Documentation accidentally split from the runtime docstring."""\n'
    )
    path = _write_tmp(tmp_path, source)

    violations = check_class_docstrings(path)

    assert [violation.rule for violation in violations] == ["CLS-003"]
    assert violations[0].entity == "SplitVessel"


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


def _synthetic_contract() -> dict:
    """Return an independent contract object from the established fixture."""
    return json.loads(MC_PATTERN.search(_COMPLIANT_CLASS_BODY).group(1))


def _source_with_contract(contract: object) -> str:
    """Replace only the fixture's JSON block, retaining its class markers."""
    block = "[MACHINE_CONTRACT v1]\n" + json.dumps(contract) + "\n[/MACHINE_CONTRACT]"
    body = MC_PATTERN.sub(lambda _: block, _COMPLIANT_CLASS_BODY)
    return f'"""Module docstring."""\n\nclass SyntheticClass:\n{body}\n'


def _request_local_contract() -> dict:
    contract = _synthetic_contract()
    contract["state"] = {"mutable": True, "owners": ["one request"]}
    contract["concurrency"] = {
        "thread": "request_local",
        "cross_thread_calls": "forbidden",
        "owner_thread_only_mutation": True,
    }
    return contract


def test_checker_request_local_contract_passes(tmp_path: Path) -> None:
    """Honest request confinement does not need a false shared-safety claim."""
    path = _write_tmp(tmp_path, _source_with_contract(_request_local_contract()))
    assert check_class_docstrings(path) == []
    assert check_machine_contracts(path) == []


def test_checker_existing_computation_profile_still_passes(tmp_path: Path) -> None:
    """The established computation/read-only profile remains accepted."""
    path = _write_tmp(tmp_path, _source_with_contract(_synthetic_contract()))
    assert check_class_docstrings(path) == []
    assert check_machine_contracts(path) == []


def test_checker_concurrency_profiles_cannot_be_mixed(tmp_path: Path) -> None:
    """Both profiles retain a mandatory, matching cross-thread policy."""
    for thread, cross_thread in (("request_local", "safe_read_only"),
                                 ("pure_computation", "forbidden")):
        contract = _request_local_contract()
        contract["concurrency"].update(thread=thread, cross_thread_calls=cross_thread)
        path = _write_tmp(tmp_path, _source_with_contract(contract))
        assert any(v.rule == "MC-006" for v in check_machine_contracts(path))


def test_checker_request_local_requires_owned_mutation(tmp_path: Path) -> None:
    """Unowned, immutable, or off-owner state is not request confinement."""
    for state in (None, {}, {"mutable": False, "owners": ["one request"]},
                  {"mutable": True, "owners": []},
                  {"mutable": True, "owners": [""]},
                  {"mutable": True, "owners": [123]},
                  {"mutable": True, "owners": "one request"}):
        contract = _request_local_contract()
        contract["state"] = state
        path = _write_tmp(tmp_path, _source_with_contract(contract))
        assert any(v.rule == "MC-007" for v in check_machine_contracts(path))
    contract = _request_local_contract()
    contract["concurrency"].pop("owner_thread_only_mutation")
    path = _write_tmp(tmp_path, _source_with_contract(contract))
    assert any(v.rule == "MC-007" for v in check_machine_contracts(path))


def test_checker_all_class_markers_remain_required(tmp_path: Path) -> None:
    """The new profile never exempts actors from any of the six markers."""
    body = _COMPLIANT_CLASS_BODY.replace("    pass", "    def run(self):\n        return 1")
    for marker in REQUIRED_CLASS_MARKERS:
        source = f'"""Module."""\nclass Actor:\n{body.replace(marker, "REMOVED", 1)}'
        path = _write_tmp(tmp_path, source)
        assert any(v.rule == "CLS-001" and repr(marker) in v.detail
                   for v in check_class_docstrings(path))


def test_checker_unclosed_contract_is_rejected(tmp_path: Path) -> None:
    source = _source_with_contract(_synthetic_contract()).replace("[/MACHINE_CONTRACT]", "")
    path = _write_tmp(tmp_path, source)
    assert any(v.rule == "MC-001" for v in check_machine_contracts(path))


def test_checker_non_object_json_is_rejected(tmp_path: Path) -> None:
    for contract in (None, [], "not an object", 42):
        path = _write_tmp(tmp_path, _source_with_contract(contract))
        assert any(v.rule == "MC-001" for v in check_machine_contracts(path))


def test_checker_malformed_concurrency_is_rejected(tmp_path: Path) -> None:
    for concurrency in (None, [], "not a profile", {"thread": []}):
        contract = _synthetic_contract()
        contract["concurrency"] = concurrency
        path = _write_tmp(tmp_path, _source_with_contract(contract))
        assert any(v.rule == "MC-005" for v in check_machine_contracts(path))


def test_preflight_reports_all_rule_families(tmp_path: Path, capsys) -> None:
    """One preflight exposes concurrent omissions, not only the first file."""
    missing = _write_tmp(tmp_path, "class Actor:\n    def run(self): pass\n", "missing.py")
    contract = _synthetic_contract()
    contract["risk"] = "extreme"
    invalid = _write_tmp(tmp_path, _source_with_contract(contract), "invalid.py")
    assert main([str(missing), str(invalid)]) == 1
    errors = capsys.readouterr().err
    assert all(rule in errors for rule in ("MOD-001", "CLS-001", "MC-003"))
    assert str(missing) in errors and str(invalid) in errors


def test_preflight_default_checks_whole_tree(tmp_path: Path, monkeypatch, capsys) -> None:
    _write_tmp(tmp_path, '"""Valid module."""\n', "valid.py")
    nested = tmp_path / "nested"
    nested.mkdir()
    missing = _write_tmp(nested, "x = 1\n", "missing.py")
    monkeypatch.setitem(main.__globals__, "MOIRA_ROOT", tmp_path)
    assert main([]) == 1
    assert str(missing) in capsys.readouterr().err


def test_preflight_invalid_or_empty_scope_fails_closed(tmp_path: Path, monkeypatch) -> None:
    import pytest

    monkeypatch.setitem(main.__globals__, "MOIRA_ROOT", tmp_path)
    for paths in ([], [str(tmp_path / "absent.py")], [str(tmp_path)]):
        with pytest.raises(SystemExit) as exc:
            main(paths)
        assert exc.value.code == 2


def test_preflight_parse_error_is_a_failure(tmp_path: Path, capsys) -> None:
    path = _write_tmp(tmp_path, "def broken(\n")
    assert main([str(path)]) == 1
    assert "PARSE-001" in capsys.readouterr().err


def test_preflight_cli_is_stdlib_only_and_read_only(tmp_path: Path) -> None:
    """A -S child has no site packages, engine import, or resource prerequisite."""
    import subprocess

    path = _write_tmp(tmp_path, _source_with_contract(_request_local_contract()))
    before = path.read_bytes()
    code = (
        "import runpy, sys; checker = runpy.run_path(sys.argv[1]); "
        "result = checker['main'](sys.argv[2:]); "
        "assert not any(n == 'moira' or n.startswith('moira.') for n in sys.modules); "
        "assert 'pytest' not in sys.modules and 'yaml' not in sys.modules; sys.exit(result)"
    )
    result = subprocess.run(
        [sys.executable, "-S", "-c", code, str(Path(__file__).resolve()), str(path)],
        cwd=tmp_path, capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert "1 Python files checked" in result.stdout
    assert path.read_bytes() == before


def test_preflight_cli_exit_status(tmp_path: Path) -> None:
    """The actual script entrypoint, not only main(), must fail on violations."""
    import subprocess

    path = _write_tmp(tmp_path, "x = 1\n")
    before = path.read_bytes()
    result = subprocess.run(
        [sys.executable, "-S", str(Path(__file__).resolve()), str(path)],
        cwd=tmp_path, capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 1
    assert "MOD-001" in result.stderr
    assert path.read_bytes() == before


def test_preflight_ci_blocks_builds_and_does_not_repeat_scan() -> None:
    """All native builds wait for the dependency-free scan; self-tests remain."""
    import yaml

    root = Path(__file__).resolve().parents[2]
    workflow = yaml.safe_load((root / ".github/workflows/release-hardening.yml").read_text(encoding="utf-8"))
    jobs = workflow["jobs"]
    preflight = jobs["docstring-preflight"]
    commands = [step["run"] for step in preflight["steps"] if "run" in step]
    assert commands == ["python tests/unit/test_docstring_governance.py"]
    assert not preflight.get("continue-on-error")
    assert all(not step.get("continue-on-error") and "if" not in step for step in preflight["steps"])
    for job_name in ("generated-artifacts", "release-hardening", "python-310-server-compatibility"):
        needs = jobs[job_name]["needs"]
        dependencies = [needs] if isinstance(needs, str) else needs
        assert "docstring-preflight" in dependencies
        assert "if" not in jobs[job_name]
    self_tests = [step["run"] for step in jobs["release-hardening"]["steps"]
                  if "test_docstring_governance.py" in step.get("run", "")]
    assert self_tests == [
        'python -m pytest tests/unit/test_docstring_governance.py -k "test_checker or test_preflight" -q'
    ]
    instructions = (root / "AGENTS.md").read_text(encoding="utf-8")
    assert all(marker in instructions for marker in REQUIRED_CLASS_MARKERS)
    assert "tests\\unit\\test_docstring_governance.py" in instructions


if __name__ == "__main__":
    raise SystemExit(main())
