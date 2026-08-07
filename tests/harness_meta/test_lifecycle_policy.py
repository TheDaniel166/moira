"""Black-box contracts for full pytest lifecycle and budget handling."""

from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
from textwrap import dedent

import pytest


pytestmark = pytest.mark.parallel(reason="isolated_resources")


_SOURCE_TESTS = Path(__file__).resolve().parents[1]
_HARNESS_SOURCE = (_SOURCE_TESTS / "conftest.py").read_text(encoding="utf-8")
_POLICY_ENVIRONMENT = (
    "MOIRA_TEST_MODE",
    "MOIRA_NO_DOWNLOAD",
    "MOIRA_STRICT_KNOWN_ISSUES",
    "MOIRA_TEST_SEED",
    "MOIRA_TEST_BUDGET_TOTAL_S",
    "MOIRA_TEST_BUDGET_CASE_S",
    "MOIRA_TEST_ARTIFACTS",
    "MOIRA_TEST_RUN_ID",
    "MOIRA_SNAPSHOT_UPDATE",
    "MOIRA_GOLDEN_UPDATE",
    "MOIRA_TEST_NETWORK_POLICY",
    "PYTEST_ADDOPTS",
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD",
)
_PYTEST_CONFIG = """\
[pytest]
pythonpath = . tests
addopts = -ra
strict_config = true
strict_markers = true
"""


def _phase_probe_suffix(
    *,
    setup_s: float,
    call_s: float,
    teardown_s: float,
    session_evidence_probe: bool = False,
) -> str:
    evidence_hook = (
        """

@pytest.hookimpl(trylast=True, specname="pytest_sessionfinish")
def pytest_sessionfinish_phase7_evidence_probe(session, exitstatus):
    print(f"PHASE7_EVIDENCE_FINALIZED::{int(session.exitstatus)}")
"""
        if session_evidence_probe
        else ""
    )
    return (
        f"""

_PHASE7_SYNTHETIC_DURATIONS = {{
    "setup": {setup_s!r},
    "call": {call_s!r},
    "teardown": {teardown_s!r},
}}


@pytest.hookimpl(wrapper=True, trylast=True, specname="pytest_runtest_makereport")
def pytest_runtest_makereport_phase7_duration_probe(item, call):
    report = yield
    if report.when in _PHASE7_SYNTHETIC_DURATIONS:
        report.duration = _PHASE7_SYNTHETIC_DURATIONS[report.when]
    return report


@pytest.hookimpl(trylast=True, specname="pytest_runtest_logreport")
def pytest_runtest_logreport_phase7_probe(report):
    if report.when in _PHASE7_SYNTHETIC_DURATIONS:
        print(
            "PHASE7_REPORT::"
            f"{{report.when}}::{{report.outcome}}::{{report.duration:.3f}}"
        )
"""
        + evidence_hook
    )


def _make_project(
    pytester: pytest.Pytester,
    *,
    test_source: str,
    setup_s: float = 0.01,
    call_s: float = 0.01,
    teardown_s: float = 0.01,
    session_evidence_probe: bool = False,
    conftest_suffix: str = "",
) -> tuple[Path, Path, Path]:
    root = pytester.path
    tests_dir = root / "tests"
    tests_dir.mkdir()
    shutil.copytree(_SOURCE_TESTS / "support", tests_dir / "support")
    shutil.copytree(
        _SOURCE_TESTS / "_pytest_plugins",
        tests_dir / "_pytest_plugins",
    )
    (tests_dir / "conftest.py").write_text(
        _HARNESS_SOURCE
        + _phase_probe_suffix(
            setup_s=setup_s,
            call_s=call_s,
            teardown_s=teardown_s,
            session_evidence_probe=session_evidence_probe,
        )
        + conftest_suffix,
        encoding="utf-8",
    )
    (tests_dir / "KNOWN_ISSUES.yml").write_text(
        "known_issues: []\n",
        encoding="utf-8",
    )
    unit_dir = tests_dir / "unit"
    unit_dir.mkdir()
    test_path = unit_dir / "test_probe.py"
    test_path.write_text(dedent(test_source), encoding="utf-8")
    config = root / "pytest.ini"
    config.write_text(_PYTEST_CONFIG, encoding="utf-8")
    return root, config, test_path


def _run(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
    root: Path,
    config: Path,
    test_path: Path,
    *,
    environment: dict[str, str] | None = None,
) -> pytest.RunResult:
    for name in _POLICY_ENVIRONMENT:
        monkeypatch.delenv(name, raising=False)
    selected_environment = {
        "MOIRA_TEST_MODE": "1",
        "MOIRA_NO_DOWNLOAD": "1",
        "MOIRA_STRICT_KNOWN_ISSUES": "1",
        **(environment or {}),
    }
    for name, value in selected_environment.items():
        monkeypatch.setenv(name, value)
    return pytester.runpytest_subprocess(
        "-c",
        str(config),
        str(test_path),
        "-q",
        "-s",
        "--color=no",
        "--tb=short",
        timeout=60,
    )


def _output(result: pytest.RunResult) -> str:
    return f"{result.stdout.str()}\n{result.stderr.str()}"


def _assert_phase_duration(
    output: str,
    phase: str,
    duration_s: float,
) -> None:
    assert re.search(
        rf"\b{re.escape(phase)}\s*=\s*{duration_s:.3f}\s*s?\b",
        output,
        re.IGNORECASE,
    ), output


def _assert_total_duration(output: str, duration_s: float) -> None:
    assert re.search(
        rf"\btotal\s*=\s*{duration_s:.3f}\s*s?\b",
        output,
        re.IGNORECASE,
    ), output


def test_case_budget_uses_full_lifecycle_and_fails_at_teardown(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, config, test_path = _make_project(
        pytester,
        test_source="""
            def test_probe():
                pass
        """,
        setup_s=0.2,
        call_s=0.1,
        teardown_s=0.3,
    )

    result = _run(
        pytester,
        monkeypatch,
        root,
        config,
        test_path,
        environment={"MOIRA_TEST_BUDGET_CASE_S": "0.5"},
    )
    output = _output(result)

    assert result.ret == pytest.ExitCode.TESTS_FAILED, output
    assert "PHASE7_REPORT::setup::passed::0.200" in output
    assert "PHASE7_REPORT::call::passed::0.100" in output
    assert "PHASE7_REPORT::teardown::failed::0.300" in output
    assert "Moira case budget" in output
    _assert_phase_duration(output, "setup", 0.2)
    _assert_phase_duration(output, "call", 0.1)
    _assert_phase_duration(output, "teardown", 0.3)
    _assert_total_duration(output, 0.6)


@pytest.mark.parametrize("failure_phase", ("setup", "call", "teardown"))
def test_case_budget_preserves_original_phase_failure_and_adds_section(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
    failure_phase: str,
) -> None:
    root, config, test_path = _make_project(
        pytester,
        test_source=f"""
            import pytest


            @pytest.fixture
            def phase_fixture():
                if {failure_phase!r} == "setup":
                    raise RuntimeError("ORIGINAL SETUP FAILURE")
                yield
                if {failure_phase!r} == "teardown":
                    raise RuntimeError("ORIGINAL TEARDOWN FAILURE")


            def test_probe(phase_fixture):
                if {failure_phase!r} == "call":
                    raise RuntimeError("ORIGINAL CALL FAILURE")
        """,
        setup_s=0.3,
        call_s=0.1,
        teardown_s=0.3,
    )

    result = _run(
        pytester,
        monkeypatch,
        root,
        config,
        test_path,
        environment={"MOIRA_TEST_BUDGET_CASE_S": "0.5"},
    )
    output = _output(result)

    assert result.ret == pytest.ExitCode.TESTS_FAILED, output
    assert f"ORIGINAL {failure_phase.upper()} FAILURE" in output
    assert "Moira case budget" in output
    _assert_phase_duration(output, "setup", 0.3)
    _assert_phase_duration(output, "teardown", 0.3)
    if failure_phase == "setup":
        assert "PHASE7_REPORT::call::" not in output
        assert re.search(
            r"\bcall\s*=\s*not[_ -]?run\b",
            output,
            re.IGNORECASE,
        ), output
        _assert_total_duration(output, 0.6)
    else:
        _assert_phase_duration(output, "call", 0.1)
        _assert_total_duration(output, 0.7)

    expected_failed_report = (
        "PHASE7_REPORT::"
        f"{failure_phase}::failed::"
        f"{0.1 if failure_phase == 'call' else 0.3:.3f}"
    )
    assert expected_failed_report in output
    if failure_phase != "teardown":
        assert "PHASE7_REPORT::teardown::passed::0.300" in output


def test_ordinary_failure_artifacts_do_not_call_the_failure_a_flake(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, config, test_path = _make_project(
        pytester,
        test_source="""
            def test_deterministic_failure():
                raise RuntimeError("ONE DETERMINISTIC FAILURE")
        """,
    )

    result = _run(
        pytester,
        monkeypatch,
        root,
        config,
        test_path,
        environment={
            "MOIRA_TEST_ARTIFACTS": "1",
            "MOIRA_TEST_RUN_ID": "phase7-deterministic-failure",
        },
    )
    output = _output(result)

    assert result.ret == pytest.ExitCode.TESTS_FAILED, output
    assert "ONE DETERMINISTIC FAILURE" in output
    artifact_roots = (
        root / ".pytest_cache" / "moira-artifacts",
        root / "tests" / "artifacts",
    )
    artifact_files = [
        path
        for artifact_root in artifact_roots
        if artifact_root.exists()
        for path in artifact_root.rglob("*")
        if path.is_file()
    ]
    assert artifact_files, output
    flake_named = [
        path
        for path in artifact_files
        if "flake" in path.name.casefold()
    ]
    assert flake_named == [], (
        "A single deterministic failure is not evidence of a flake: "
        + ", ".join(str(path) for path in flake_named)
    )


def test_total_budget_finalizes_evidence_before_elevating_success(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, config, test_path = _make_project(
        pytester,
        test_source="""
            def test_probe():
                pass
        """,
        session_evidence_probe=True,
    )

    result = _run(
        pytester,
        monkeypatch,
        root,
        config,
        test_path,
        environment={"MOIRA_TEST_BUDGET_TOTAL_S": "0.000000001"},
    )
    output = _output(result)

    assert result.ret == pytest.ExitCode.TESTS_FAILED, output
    assert "PHASE7_EVIDENCE_FINALIZED::0" in output
    assert "total budget" in output.casefold()
    assert "exceeded" in output.casefold()


def test_lifecycle_contradiction_fails_without_artifact_output(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, config, test_path = _make_project(
        pytester,
        test_source="""
            def test_probe():
                pass
        """,
        conftest_suffix="""

from _pytest_plugins import artifacts as _phase8_artifacts


@pytest.hookimpl(trylast=True, specname="pytest_sessionfinish")
def pytest_sessionfinish_duplicate_lifecycle_probe(session, exitstatus):
    collector = _phase8_artifacts._controller_collector(session.config)
    assert collector is not None
    call_record = next(
        record
        for record in collector.records
        if record["kind"] == "test" and record["phase"] == "call"
    )
    collector.records.append(dict(call_record))
""",
    )

    result = _run(
        pytester,
        monkeypatch,
        root,
        config,
        test_path,
        environment={"MOIRA_TEST_ARTIFACTS": "0"},
    )
    output = _output(result)

    assert result.ret == pytest.ExitCode.TESTS_FAILED, output
    assert "Moira: controller evidence validation" in output
    assert "emitted duplicate call reports" in output
    assert not (root / ".pytest_cache" / "moira-artifacts").exists()


def test_presealed_collector_error_fails_without_artifact_output(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, config, test_path = _make_project(
        pytester,
        test_source="""
            def test_probe():
                pass
        """,
        conftest_suffix="""

from _pytest_plugins import artifacts as _phase8_artifacts


@pytest.hookimpl(trylast=True, specname="pytest_sessionfinish")
def pytest_sessionfinish_presealed_error_probe(session, exitstatus):
    collector = _phase8_artifacts._controller_collector(session.config)
    assert collector is not None
    collector.errors.append("SYNTHETIC PRE-SEAL EVIDENCE FAILURE")
""",
    )

    result = _run(
        pytester,
        monkeypatch,
        root,
        config,
        test_path,
        environment={"MOIRA_TEST_ARTIFACTS": "0"},
    )
    output = _output(result)

    assert result.ret == pytest.ExitCode.TESTS_FAILED, output
    assert "Moira: controller evidence validation" in output
    assert "SYNTHETIC PRE-SEAL EVIDENCE FAILURE" in output
    assert not (root / ".pytest_cache" / "moira-artifacts").exists()


def test_total_budget_receipt_records_the_prospective_failure_status(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, config, test_path = _make_project(
        pytester,
        test_source="""
            def test_probe():
                pass
        """,
        session_evidence_probe=True,
    )

    result = _run(
        pytester,
        monkeypatch,
        root,
        config,
        test_path,
        environment={
            "MOIRA_TEST_BUDGET_TOTAL_S": "0.000000001",
            "MOIRA_TEST_ARTIFACTS": "1",
            "MOIRA_TEST_RUN_ID": "total-budget-receipt",
        },
    )
    output = _output(result)
    run_dir = (
        root
        / ".pytest_cache"
        / "moira-artifacts"
        / "total-budget-receipt"
    )

    assert result.ret == pytest.ExitCode.TESTS_FAILED, output
    assert (run_dir / "COMPLETE").is_file()
    assert not (run_dir / "INCOMPLETE").exists()
    run = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    assert run["pytest"]["exitstatus"] == {
        "code": int(pytest.ExitCode.TESTS_FAILED),
        "name": "TESTS_FAILED",
    }
    assert run["pytest"]["total_budget"]["exceeded"] is True


def test_total_budget_preserves_existing_failure_diagnostic(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, config, test_path = _make_project(
        pytester,
        test_source="""
            def test_probe():
                raise RuntimeError("ORIGINAL TEST FAILURE")
        """,
        session_evidence_probe=True,
    )

    result = _run(
        pytester,
        monkeypatch,
        root,
        config,
        test_path,
        environment={"MOIRA_TEST_BUDGET_TOTAL_S": "0.000000001"},
    )
    output = _output(result)

    assert result.ret == pytest.ExitCode.TESTS_FAILED, output
    assert "ORIGINAL TEST FAILURE" in output
    assert "PHASE7_EVIDENCE_FINALIZED::1" in output
    assert "total budget" in output.casefold()


def test_total_budget_does_not_downgrade_keyboard_interrupt(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, config, test_path = _make_project(
        pytester,
        test_source="""
            def test_probe():
                raise KeyboardInterrupt("ORIGINAL INTERRUPT")
        """,
        session_evidence_probe=True,
    )

    result = _run(
        pytester,
        monkeypatch,
        root,
        config,
        test_path,
        environment={"MOIRA_TEST_BUDGET_TOTAL_S": "0.000000001"},
    )
    output = _output(result)

    assert result.ret == pytest.ExitCode.INTERRUPTED, output
    assert "ORIGINAL INTERRUPT" in output
    assert "PHASE7_EVIDENCE_FINALIZED::2" in output
    assert "total budget" in output.casefold()
