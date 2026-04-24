"""
Moira — test_bug_condition_exploration.py
Bug condition exploration test for docstring governance violations bugfix.

**Validates: Requirements 2.1, 2.2, 2.3**

This test MUST FAIL on unfixed code to confirm the bug condition exists.
The test encodes the expected behavior and will validate the fix when it passes after implementation.

Purpose: Surface counterexamples that demonstrate governance violations exist in unfixed code.
Boundary: owns property-based testing of docstring governance bug condition. Delegates to existing governance checkers.
Import-time side effects: None
External dependency assumptions: pytest, hypothesis for property-based testing
Public surface: test_bug_condition_docstring_governance_violations
"""

import ast
import json
from pathlib import Path
from typing import NamedTuple

import pytest
from hypothesis import given, strategies as st, example, settings, HealthCheck

from tests.unit.test_docstring_governance import (
    check_module_docstrings,
    check_class_docstrings, 
    check_machine_contracts,
    Violation,
    MOIRA_ROOT,
)


class ViolationSummary(NamedTuple):
    """Summary of governance violations found during bug condition exploration."""
    mod_001_count: int
    cls_001_count: int
    mc_005_count: int
    mc_006_count: int
    total_violations: int
    sample_files: list[str]


def analyze_governance_violations() -> ViolationSummary:
    """
    Analyze the current state of docstring governance violations across moira package.
    
    Returns:
        ViolationSummary with counts and examples of violations found.
    """
    mod_violations = []
    cls_violations = []
    mc_violations = []
    
    for path in sorted(MOIRA_ROOT.rglob("*.py")):
        mod_violations.extend(check_module_docstrings(path))
        cls_violations.extend(check_class_docstrings(path))
        mc_violations.extend(check_machine_contracts(path))
    
    # Count MC-005 and MC-006 specifically
    mc_005_count = len([v for v in mc_violations if v.rule == "MC-005"])
    mc_006_count = len([v for v in mc_violations if v.rule == "MC-006"])
    
    # Get sample files with violations
    sample_files = list(set([
        str(Path(v.file).relative_to(Path.cwd())) for v in (mod_violations + cls_violations + mc_violations)[:10]
    ]))
    
    return ViolationSummary(
        mod_001_count=len(mod_violations),
        cls_001_count=len(cls_violations),
        mc_005_count=mc_005_count,
        mc_006_count=mc_006_count,
        total_violations=len(mod_violations) + len(cls_violations) + len(mc_violations),
        sample_files=sample_files,
    )


@given(st.sampled_from([
    "moira/bridges/harmograms.py",
    "moira/cycles.py", 
    "moira/_spk_body_kernel.py",
    "moira/synastry.py",
    "moira/heliacal.py",
]))
@example("moira/bridges/harmograms.py")  # Known MOD-001 violation
@example("moira/cycles.py")  # Known MC-005/006 violations
@example("moira/_spk_body_kernel.py")  # Known CLS-001 violations
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_bug_condition_docstring_governance_violations(sample_file: str) -> None:
    """
    Property 1: Bug Condition - Docstring Governance Violations Detection
    
    **Validates: Requirements 2.1, 2.2, 2.3**
    
    **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists.
    **DO NOT attempt to fix the test or the code when it fails.**
    **GOAL**: Surface counterexamples that demonstrate the governance violations exist.
    
    **Scoped PBT Approach**: Focus on the three main violation types:
    - MOD-001 (missing module docstrings)
    - CLS-001 (missing class governance markers) 
    - MC-005/006 (incorrect MACHINE_CONTRACT concurrency values)
    
    This test encodes the expected behavior - it will validate the fix when it passes after implementation.
    """
    path = Path(sample_file)
    if not path.exists():
        pytest.skip(f"Sample file {sample_file} does not exist")
    
    # Check for violations in the sample file
    mod_violations = check_module_docstrings(path)
    cls_violations = check_class_docstrings(path)
    mc_violations = check_machine_contracts(path)
    
    all_violations = mod_violations + cls_violations + mc_violations
    
    # The bug condition: files with governance violations should exist
    # This assertion will FAIL on unfixed code, confirming the bug exists
    assert len(all_violations) == 0, (
        f"Bug condition confirmed: Found {len(all_violations)} governance violations in {sample_file}:\n"
        + "\n".join([
            f"  [{v.rule}] {v.entity}: {v.detail}" 
            for v in all_violations[:10]  # Show first 10 violations
        ])
        + (f"\n  ... and {len(all_violations) - 10} more violations" if len(all_violations) > 10 else "")
    )


def test_bug_condition_comprehensive_violation_analysis() -> None:
    """
    Comprehensive analysis of docstring governance violations across the entire moira package.
    
    **CRITICAL**: This test MUST FAIL on unfixed code with expected violation counts.
    **EXPECTED OUTCOME**: Test FAILS with 3,735 total violations (13 MOD-001, 3674 CLS-001, 48 MC violations).
    
    Documents counterexamples found: specific files and violation patterns.
    Analyzes violation distribution across moira package modules.
    """
    summary = analyze_governance_violations()
    
    # Document the counterexamples found
    print(f"\n=== BUG CONDITION EXPLORATION RESULTS ===")
    print(f"Total violations found: {summary.total_violations}")
    print(f"MOD-001 (missing module docstrings): {summary.mod_001_count}")
    print(f"CLS-001 (missing class governance markers): {summary.cls_001_count}")
    print(f"MC-005 (incorrect thread concurrency): {summary.mc_005_count}")
    print(f"MC-006 (incorrect cross_thread_calls): {summary.mc_006_count}")
    print(f"Sample files with violations: {summary.sample_files[:5]}")
    print("=== END BUG CONDITION EXPLORATION ===\n")
    
    # The bug condition: systematic governance violations should exist
    # This assertion will FAIL on unfixed code, confirming the bug exists
    assert summary.total_violations == 0, (
        f"Bug condition confirmed: Found {summary.total_violations} total governance violations across moira package.\n"
        f"Breakdown:\n"
        f"  - MOD-001 (missing module docstrings): {summary.mod_001_count} files\n"
        f"  - CLS-001 (missing class governance markers): {summary.cls_001_count} violations\n"
        f"  - MC-005 (incorrect thread concurrency): {summary.mc_005_count} violations\n"
        f"  - MC-006 (incorrect cross_thread_calls): {summary.mc_006_count} violations\n"
        f"Sample affected files: {summary.sample_files[:5]}\n"
        f"This confirms the hypothesized root cause: historical development without governance standard."
    )


def test_specific_violation_patterns() -> None:
    """
    Test specific violation patterns mentioned in the design document.
    
    **CRITICAL**: This test MUST FAIL on unfixed code, documenting specific counterexamples.
    """
    # Test MOD-001 example from design
    harmograms_path = Path("moira/bridges/harmograms.py")
    if harmograms_path.exists():
        mod_violations = check_module_docstrings(harmograms_path)
        assert len(mod_violations) == 0, (
            f"MOD-001 counterexample: {harmograms_path} has no module docstring, "
            f"causing governance audit failure: {mod_violations[0].detail if mod_violations else 'No violations'}"
        )
    
    # Test CLS-001 example from design  
    spk_path = Path("moira/_spk_body_kernel.py")
    if spk_path.exists():
        cls_violations = check_class_docstrings(spk_path)
        type13_violations = [v for v in cls_violations if v.entity == "_Type13Segment"]
        assert len(type13_violations) == 0, (
            f"CLS-001 counterexample: _Type13Segment class lacks RITE/THEOREM structure "
            f"and MACHINE_CONTRACT block: {len(type13_violations)} violations found"
        )
    
    # Test MC-005/006 examples from design
    cycles_path = Path("moira/cycles.py")
    if cycles_path.exists():
        mc_violations = check_machine_contracts(cycles_path)
        return_event_violations = [v for v in mc_violations if v.entity == "ReturnEvent"]
        assert len(return_event_violations) == 0, (
            f"MC-005/006 counterexamples: ReturnEvent has incorrect concurrency values: "
            f"{len(return_event_violations)} violations found. "
            f"Expected 'pure_computation' and 'safe_read_only' but found different values."
        )


if __name__ == "__main__":
    # Run the comprehensive analysis when executed directly
    summary = analyze_governance_violations()
    print(f"Bug condition exploration complete:")
    print(f"Total violations: {summary.total_violations}")
    print(f"MOD-001: {summary.mod_001_count}, CLS-001: {summary.cls_001_count}")
    print(f"MC-005: {summary.mc_005_count}, MC-006: {summary.mc_006_count}")