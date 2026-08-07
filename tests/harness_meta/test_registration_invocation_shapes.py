"""Real-checkout canaries for every supported pytest discovery shape."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest


pytestmark = pytest.mark.serial(reason="nested_runner")


_ROOT = Path(__file__).resolve().parents[2]
_TARGET_FUNCTION = (
    "test_required_plugin_manifest_is_exact_complete_and_local"
)
_TARGET_MODULE = (
    "tests/harness_meta/test_plugin_architecture_policy.py"
)
_TARGET_NODE = f"{_TARGET_MODULE}::{_TARGET_FUNCTION}"
_POLICY_ENVIRONMENT = (
    "MOIRA_TEST_MODE",
    "MOIRA_NO_DOWNLOAD",
    "MOIRA_TEST_SEED",
    "MOIRA_TEST_BUDGET_TOTAL_S",
    "MOIRA_TEST_BUDGET_CASE_S",
    "MOIRA_STRICT_KNOWN_ISSUES",
    "MOIRA_SNAPSHOT_UPDATE",
    "MOIRA_GOLDEN_UPDATE",
    "MOIRA_TEST_NETWORK_POLICY",
    "MOIRA_TEST_ARTIFACTS",
    "MOIRA_TEST_RUN_ID",
    "MOIRA_REGRESSION_PCT",
    "PYTEST_XDIST_WORKER",
    "PYTEST_XDIST_WORKER_COUNT",
    "MOIRA_WORKER_ID",
    "PYTEST_ADDOPTS",
    "PYTEST_PLUGINS",
    "PYTHONPATH",
    "_MOIRA_ROOT_HARNESS_BOOTSTRAP",
)


def _child_environment() -> dict[str, str]:
    environment = os.environ.copy()
    for name in _POLICY_ENVIRONMENT:
        environment.pop(name, None)
    environment.update(
        {
            "MOIRA_TEST_MODE": "1",
            "MOIRA_NO_DOWNLOAD": "1",
            "MOIRA_STRICT_KNOWN_ISSUES": "1",
            "MOIRA_TEST_ARTIFACTS": "0",
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    return environment


def _run_checkout_pytest(arguments: tuple[str, ...]) -> str:
    completed = subprocess.run(
        (
            sys.executable,
            "-m",
            "pytest",
            *arguments,
            "-p",
            "no:cacheprovider",
            "--color=no",
            "-q",
            "-rA",
        ),
        cwd=_ROOT,
        env=_child_environment(),
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    output = f"{completed.stdout}\n{completed.stderr}"
    assert completed.returncode == pytest.ExitCode.OK, output
    assert output.count("Moira: harness policy receipt") == 1
    assert "selected=1" in output
    normalized_output = output.replace("\\", "/")
    assert normalized_output.count(f"PASSED {_TARGET_NODE}") == 1
    for forbidden_outcome in ("SKIPPED ", "XFAIL ", "XPASS "):
        assert forbidden_outcome not in normalized_output
    return output


@pytest.mark.parametrize(
    "path_arguments",
    (
        pytest.param((), id="no-positional"),
        pytest.param(("tests",), id="tests"),
        pytest.param((".",), id="dot"),
        pytest.param((_TARGET_NODE,), id="exact-node"),
    ),
)
def test_required_plugins_load_under_checkout_invocation_shape(
    path_arguments: tuple[str, ...],
) -> None:
    _run_checkout_pytest(
        (
            *path_arguments,
            "-o",
            "python_files=test_plugin_architecture_policy.py",
            "-k",
            _TARGET_FUNCTION,
        )
    )


def test_required_plugins_load_with_alternate_config(
    tmp_path: Path,
) -> None:
    config = tmp_path / "alternate.ini"
    config.write_text(
        """\
[pytest]
strict_config = true
strict_markers = true
""",
        encoding="utf-8",
    )

    _run_checkout_pytest(
        (
            "-c",
            str(config),
            "--rootdir",
            str(_ROOT),
            "--import-mode=importlib",
            _TARGET_NODE,
        )
    )
