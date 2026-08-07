"""Black-box contracts for fail-closed test-harness configuration."""

from __future__ import annotations

from pathlib import Path
import shutil
from textwrap import dedent

import pytest


pytestmark = pytest.mark.parallel(reason="isolated_resources")


_TESTS_DIR = Path(__file__).resolve().parents[1]
_HARNESS_SOURCE = (_TESTS_DIR / "conftest.py").read_text(encoding="utf-8")
_NETWORK_POLICY_SOURCE = (
    _TESTS_DIR / "support" / "network_policy.py"
).read_text(encoding="utf-8")
_NETWORK_BOOTSTRAP_SOURCE = (
    _TESTS_DIR / "support" / "network_bootstrap" / "sitecustomize.py"
).read_text(encoding="utf-8")
_POLICY_ENV_NAMES = (
    "MOIRA_TEST_MODE",
    "MOIRA_NO_DOWNLOAD",
    "MOIRA_TEST_SEED",
    "MOIRA_TEST_BUDGET_TOTAL_S",
    "MOIRA_TEST_BUDGET_CASE_S",
    "MOIRA_STRICT_KNOWN_ISSUES",
    "MOIRA_TEST_ARTIFACTS",
    "MOIRA_TEST_RUN_ID",
    "MOIRA_SNAPSHOT_UPDATE",
    "MOIRA_GOLDEN_UPDATE",
    "MOIRA_TEST_NETWORK_POLICY",
)
_PYTEST_CONFIG = """\
[pytest]
strict_config = true
strict_markers = true
markers =
    parallel: tests admitted for parallel execution
    property: property-based tests
"""
_NO_KERNEL_BOOTSTRAP = """

@pytest.fixture(scope="session", autouse=True)
def _bootstrap_kernel_singleton():
    \"\"\"Keep configuration-policy mini-projects independent of local kernels.\"\"\"
    yield
"""


def _make_policy_project(pytester: pytest.Pytester) -> None:
    """Install the real harness with only its unrelated kernel setup neutralized."""
    mini_tests = pytester.path / "tests"
    mini_tests.mkdir()
    mini_support = mini_tests / "support"
    mini_support.mkdir()
    mini_support.joinpath("__init__.py").write_text("", encoding="utf-8")
    mini_support.joinpath("network_policy.py").write_text(
        _NETWORK_POLICY_SOURCE,
        encoding="utf-8",
    )
    mini_bootstrap = mini_support / "network_bootstrap"
    mini_bootstrap.mkdir()
    mini_bootstrap.joinpath("sitecustomize.py").write_text(
        _NETWORK_BOOTSTRAP_SOURCE,
        encoding="utf-8",
    )
    shutil.copytree(
        _TESTS_DIR / "_pytest_plugins",
        mini_tests / "_pytest_plugins",
    )
    mini_tests.joinpath("conftest.py").write_text(
        _HARNESS_SOURCE + _NO_KERNEL_BOOTSTRAP,
        encoding="utf-8",
    )
    mini_tests.joinpath("KNOWN_ISSUES.yml").write_text(
        "known_issues: []\n",
        encoding="utf-8",
    )
    pytester.path.joinpath("pytest.ini").write_text(
        _PYTEST_CONFIG,
        encoding="utf-8",
    )
    mini_tests.joinpath("test_probe.py").write_text(
        dedent(
            """
            def test_configuration_was_accepted():
                pass
            """
        ),
        encoding="utf-8",
    )


def _clear_policy_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in _POLICY_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)


def _combined_output(result: pytest.RunResult) -> str:
    return f"{result.stdout.str()}\n{result.stderr.str()}"


def _assert_usage_error(result: pytest.RunResult, *diagnostic_tokens: str) -> None:
    output = _combined_output(result)
    assert result.ret == pytest.ExitCode.USAGE_ERROR, output
    normalized = output.casefold()
    for token in diagnostic_tokens:
        assert token.casefold() in normalized, output


@pytest.mark.parametrize(
    "budget_name",
    ("MOIRA_TEST_BUDGET_TOTAL_S", "MOIRA_TEST_BUDGET_CASE_S"),
)
@pytest.mark.parametrize(
    "invalid_value",
    ("", "not-a-number", "-0.001", "nan", "inf"),
    ids=("empty", "malformed", "negative", "nan", "infinity"),
)
def test_budget_rejects_non_finite_or_negative_values(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
    budget_name: str,
    invalid_value: str,
) -> None:
    _clear_policy_environment(monkeypatch)
    monkeypatch.setenv(budget_name, invalid_value)
    _make_policy_project(pytester)

    result = pytester.runpytest_subprocess(
        "tests",
        "-q",
        "--tb=short",
        timeout=30,
    )

    _assert_usage_error(result, budget_name)


def test_budget_accepts_finite_nonnegative_values(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_policy_environment(monkeypatch)
    monkeypatch.setenv("MOIRA_TEST_BUDGET_TOTAL_S", "1000.25")
    monkeypatch.setenv("MOIRA_TEST_BUDGET_CASE_S", "100.5")
    monkeypatch.setenv("MOIRA_TEST_SEED", "18446744073709551615")
    _make_policy_project(pytester)

    result = pytester.runpytest_subprocess(
        "tests",
        "-q",
        "--tb=short",
        timeout=30,
    )

    result.assert_outcomes(passed=1)


def test_test_mode_cannot_be_weakened_by_download_override(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_policy_environment(monkeypatch)
    monkeypatch.setenv("MOIRA_TEST_MODE", "1")
    monkeypatch.setenv("MOIRA_NO_DOWNLOAD", "0")
    _make_policy_project(pytester)

    result = pytester.runpytest_subprocess(
        "tests",
        "-q",
        "--tb=short",
        timeout=30,
    )

    _assert_usage_error(result, "MOIRA_TEST_MODE", "MOIRA_NO_DOWNLOAD")


def test_test_mode_derives_only_the_required_no_download_environment(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_policy_environment(monkeypatch)
    monkeypatch.setenv("MOIRA_TEST_MODE", "1")
    monkeypatch.setenv("MOIRA_UNRELATED_SENTINEL", "preserved")
    _make_policy_project(pytester)
    pytester.path.joinpath("tests", "test_probe.py").write_text(
        dedent(
            """
            import os


            def test_environment_mutation_is_bounded():
                assert os.environ["MOIRA_NO_DOWNLOAD"] == "1"
                assert "MOIRA_TEST_SEED" not in os.environ
                assert "MOIRA_TEST_BUDGET_TOTAL_S" not in os.environ
                assert "MOIRA_TEST_BUDGET_CASE_S" not in os.environ
                assert os.environ["MOIRA_UNRELATED_SENTINEL"] == "preserved"
            """
        ),
        encoding="utf-8",
    )

    result = pytester.runpytest_subprocess(
        "tests",
        "-q",
        "--tb=short",
        timeout=30,
    )

    result.assert_outcomes(passed=1)


@pytest.mark.parametrize(
    "boolean_name",
    (
        "MOIRA_TEST_MODE",
        "MOIRA_NO_DOWNLOAD",
        "MOIRA_STRICT_KNOWN_ISSUES",
        "MOIRA_SNAPSHOT_UPDATE",
        "MOIRA_GOLDEN_UPDATE",
    ),
)
@pytest.mark.parametrize(
    "invalid_value",
    ("", "truthy", "2"),
    ids=("empty", "malformed", "out-of-domain"),
)
def test_boolean_configuration_rejects_values_other_than_zero_or_one(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
    boolean_name: str,
    invalid_value: str,
) -> None:
    _clear_policy_environment(monkeypatch)
    monkeypatch.setenv(boolean_name, invalid_value)
    _make_policy_project(pytester)

    result = pytester.runpytest_subprocess(
        "tests",
        "-q",
        "--tb=short",
        timeout=30,
    )

    _assert_usage_error(result, boolean_name)


@pytest.mark.parametrize(
    "invalid_seed",
    (
        "",
        "3.14",
        "not-an-integer",
        "-1",
        "18446744073709551616",
        "9" * 5000,
    ),
    ids=(
        "empty",
        "fractional",
        "nonnumeric",
        "negative",
        "above-uint64",
        "digit-limit-abuse",
    ),
)
def test_seed_rejects_invalid_or_out_of_range_values(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
    invalid_seed: str,
) -> None:
    _clear_policy_environment(monkeypatch)
    monkeypatch.setenv("MOIRA_TEST_SEED", invalid_seed)
    _make_policy_project(pytester)

    result = pytester.runpytest_subprocess(
        "tests",
        "-q",
        "--tb=short",
        timeout=30,
    )

    _assert_usage_error(result, "MOIRA_TEST_SEED")


def test_strict_markers_reject_an_unknown_marker(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_policy_environment(monkeypatch)
    _make_policy_project(pytester)
    pytester.path.joinpath("tests", "test_probe.py").write_text(
        dedent(
            """
            import pytest


            @pytest.mark.paralell
            def test_marker_typo():
                pass
            """
        ),
        encoding="utf-8",
    )

    result = pytester.runpytest_subprocess(
        "tests",
        "--collect-only",
        "-q",
        "--strict-markers",
        timeout=30,
    )

    output = _combined_output(result)
    assert result.ret == pytest.ExitCode.INTERRUPTED, output
    assert "paralell" in output
    assert "not found in `markers` configuration option" in output


def test_strict_config_rejects_an_unknown_ini_option(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_policy_environment(monkeypatch)
    _make_policy_project(pytester)
    pytester.path.joinpath("pytest.ini").write_text(
        _PYTEST_CONFIG + "unknown_moira_option = true\n",
        encoding="utf-8",
    )

    result = pytester.runpytest_subprocess(
        "tests",
        "--collect-only",
        "-q",
        "--strict-config",
        timeout=30,
    )

    _assert_usage_error(result, "unknown_moira_option")
