"""Local verification must execute the CI selections and preserve failures."""

from __future__ import annotations

import os
import subprocess
import sys
from zoneinfo import ZoneInfoNotFoundError

import pytest
import yaml

from scripts import check_ci


def test_local_plan_includes_every_current_runtime_verification_step(tmp_path):
    environment = {**os.environ, "RUNNER_TEMP": str(tmp_path)}
    checks, ci_only = check_ci.load_plan(check_ci.ROOT, environment)
    expected = []
    for filename in check_ci.WORKFLOWS:
        workflow = yaml.safe_load((check_ci.ROOT / ".github/workflows" / filename).read_text(encoding="utf-8"))
        for job_id, job in workflow["jobs"].items():
            if job_id == "python-310-server-compatibility":
                continue
            expected.extend(
                f"{filename}/{job_id}: {step['name']}"
                for step in job["steps"]
                if "run" in step and "pip install" not in step["run"]
            )
    assert [check.label for check in checks] == expected
    assert len(ci_only) == 1
    assert "python-310-server-compatibility (Python 3.10;" in ci_only[0]
    lightbox = next(check for check in checks if "conformance governance regression" in check.label)
    targets = lightbox.commands[0]
    assert "tests/unit/test_lightbox_assurance_matrix.py" in targets
    assert set(check_ci.ROOT.glob("tests/unit/test_lightbox_*.py")) == {
        check_ci.ROOT / target for target in targets if target.startswith("tests/")
    }
    assert all(check.environment["MOIRA_NO_DOWNLOAD"] == "1" for check in checks)
    assert all(command[0] == sys.executable for check in checks for command in check.commands)
    assert not any("pip" in command for check in checks for command in check.commands)


def test_glob_discovers_new_tests_without_changing_a_target_list(tmp_path):
    (tmp_path / "test_lightbox_assurance.py").touch()
    (tmp_path / "test_lightbox_future.py").touch()
    commands = check_ci.commands_for_run("python -m pytest test_lightbox_*.py -q", tmp_path, {})
    assert commands == ((sys.executable, "-m", "pytest", "test_lightbox_assurance.py", "test_lightbox_future.py", "-q"),)


def test_multiline_quotes_environment_and_ruff_use_no_shell(tmp_path):
    commands = check_ci.commands_for_run(
        'python -m pytest \\\n tests/a.py -m "not requires_ephemeris" -q\n'
        'python scripts/build.py --output "$RUNNER_TEMP/output.json"\n'
        'ruff check moira --select F401,F821 --no-fix',
        tmp_path, {"RUNNER_TEMP": "temporary folder"},
    )
    assert commands == (
        (sys.executable, "-m", "pytest", "tests/a.py", "-m", "not requires_ephemeris", "-q"),
        (sys.executable, "scripts/build.py", "--output", "temporary folder/output.json"),
        (sys.executable, "-m", "ruff", "check", "moira", "--select", "F401,F821", "--no-fix"),
    )


@pytest.mark.parametrize("command", [
    "python -m pytest test_missing_*.py", "python check.py && python ignored.py",
    "python check.py > output", "echo unsupported", "# nothing to run",
])
def test_unsupported_or_empty_commands_fail_closed(tmp_path, command):
    with pytest.raises(ValueError):
        check_ci.commands_for_run(command, tmp_path, {})


def test_unknown_environment_variable_fails_closed(tmp_path):
    with pytest.raises(KeyError):
        check_ci.commands_for_run('python check.py "$UNKNOWN"', tmp_path, {})


def test_child_failure_stops_remaining_checks_and_preserves_exit_status(tmp_path, monkeypatch):
    calls = []

    def execute(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 7)

    monkeypatch.setattr(check_ci.subprocess, "run", execute)
    first = check_ci.Check("first", ((sys.executable, "first.py"),), {"TEST": "value"})
    later = check_ci.Check("must not run", ((sys.executable, "later.py"),), {})
    assert check_ci.run_plan([first, later], tmp_path) == 7
    assert calls == [(first.commands[0], {"cwd": tmp_path, "env": first.environment, "check": False})]


def test_listing_runs_no_children(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Listing must not execute a child")

    monkeypatch.setattr(check_ci.subprocess, "run", forbidden)
    check = check_ci.Check("list", ((sys.executable, "check.py"),), {})
    assert check_ci.run_plan([check], tmp_path, list_only=True) == 0


def test_missing_timezone_data_fails_with_the_declared_dependency_repair(monkeypatch):
    def missing_zone(key):
        raise ZoneInfoNotFoundError(key)

    monkeypatch.setattr(check_ci, "ZoneInfo", missing_zone)
    with pytest.raises(ValueError, match="dev extra.*tzdata on Windows"):
        check_ci.check_timezone_data()


def test_ci_timezone_data_is_available():
    check_ci.check_timezone_data()


@pytest.mark.parametrize("change", ["conditional", "optional", "action", "dependency", "version"])
def test_unsupported_workflow_changes_fail_before_execution(tmp_path, change):
    workflow_dir = tmp_path / ".github/workflows"
    workflow_dir.mkdir(parents=True)
    job = {
        "steps": [
            {"uses": "actions/setup-python@v5", "with": {"python-version": "3.14"}},
            {"name": "Check", "run": "python scripts/check.py"},
        ],
    }
    if change == "conditional":
        job["steps"][1]["if"] = "false"
    elif change == "optional":
        job["continue-on-error"] = True
    elif change == "action":
        job["steps"].append({"uses": "custom/verification@v1"})
    elif change == "dependency":
        job["needs"] = ["unverified"]
    else:
        job["steps"].pop(0)
    for filename in check_ci.WORKFLOWS:
        (workflow_dir / filename).write_text(yaml.safe_dump({"jobs": {"gate": job}}), encoding="utf-8")
    with pytest.raises(ValueError):
        check_ci.load_plan(tmp_path, {})
