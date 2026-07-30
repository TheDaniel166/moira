"""Black-box contracts for collection-time Hypothesis configuration."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest


_TESTS_DIR = Path(__file__).resolve().parents[1]
_HARNESS_SOURCE = (_TESTS_DIR / "conftest.py").read_text(encoding="utf-8")
_NETWORK_POLICY_SOURCE = (
    _TESTS_DIR / "support" / "network_policy.py"
).read_text(encoding="utf-8")
_NETWORK_BOOTSTRAP_SOURCE = (
    _TESTS_DIR / "support" / "network_bootstrap" / "sitecustomize.py"
).read_text(encoding="utf-8")
_PYTEST_CONFIG = """\
[pytest]
markers =
    parallel: tests admitted for parallel execution
    property: property-based tests
"""
_NO_KERNEL_BOOTSTRAP = """

@pytest.fixture(scope="session", autouse=True)
def _bootstrap_kernel_singleton():
    \"\"\"Keep the Hypothesis-policy mini-project independent of local kernels.\"\"\"
    yield
"""


def _clear_hypothesis_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
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
        "HYPOTHESIS_PROFILE",
    ):
        monkeypatch.delenv(name, raising=False)


def _make_hypothesis_project(
    pytester: pytest.Pytester,
    *,
    expected_examples: int,
    database_is_none: bool,
    derandomize: bool,
    deadline_is_none: bool | None = None,
    expected_deadline_ms: int | None = None,
    expected_verbosity: str | None = None,
) -> None:
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
    mini_tests.joinpath("test_bare_hypothesis_profile.py").write_text(
        dedent(
            """
            from hypothesis import given, settings, strategies as st


            PROFILE_AT_IMPORT = (
                settings.default.max_examples,
                settings.default.database is None,
                settings.default.derandomize,
                settings.default.deadline is None,
                (
                    None
                    if settings.default.deadline is None
                    else int(settings.default.deadline.total_seconds() * 1000)
                ),
                settings.default.verbosity.name,
            )
            OBSERVED_EXAMPLES = []


            def test_profile_was_loaded_before_module_collection():
                (
                    max_examples,
                    database_is_none,
                    derandomize,
                    deadline_is_none,
                    deadline_ms,
                    verbosity,
                ) = PROFILE_AT_IMPORT
                assert max_examples == {expected_examples}
                assert database_is_none is {database_is_none}
                assert derandomize is {derandomize}
                expected_deadline_is_none = {deadline_is_none}
                if expected_deadline_is_none is not None:
                    assert deadline_is_none is expected_deadline_is_none
                expected_deadline_ms = {expected_deadline_ms!r}
                if expected_deadline_ms is not None:
                    assert deadline_ms == expected_deadline_ms
                expected_verbosity = {expected_verbosity!r}
                if expected_verbosity is not None:
                    assert verbosity == expected_verbosity


            @given(st.binary(min_size=16, max_size=16))
            def test_bare_given_uses_test_mode_profile(value):
                OBSERVED_EXAMPLES.append(value)


            def teardown_module():
                assert len(OBSERVED_EXAMPLES) == {expected_examples}
            """
        ).format(
            expected_examples=expected_examples,
            database_is_none=database_is_none,
            derandomize=derandomize,
            deadline_is_none=deadline_is_none,
            expected_deadline_ms=expected_deadline_ms,
            expected_verbosity=expected_verbosity,
        ),
        encoding="utf-8",
    )


def _assert_two_tests_passed(result: pytest.RunResult) -> None:
    output = f"{result.stdout.str()}\n{result.stderr.str()}"
    assert result.ret == pytest.ExitCode.OK, output
    result.assert_outcomes(passed=2)


def test_test_mode_profile_is_active_before_collection(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_hypothesis_environment(monkeypatch)
    monkeypatch.setenv("MOIRA_TEST_MODE", "1")
    _make_hypothesis_project(
        pytester,
        expected_examples=50,
        database_is_none=True,
        derandomize=True,
    )

    result = pytester.runpytest_subprocess(
        "tests",
        "-q",
        "--tb=short",
        timeout=30,
    )

    _assert_two_tests_passed(result)


def test_local_profile_is_active_before_collection_without_test_mode(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_hypothesis_environment(monkeypatch)
    _make_hypothesis_project(
        pytester,
        expected_examples=100,
        database_is_none=False,
        derandomize=False,
        deadline_is_none=False,
        expected_deadline_ms=1000,
    )

    result = pytester.runpytest_subprocess(
        "tests",
        "-q",
        "--tb=short",
        timeout=30,
    )

    _assert_two_tests_passed(result)
    output = f"{result.stdout.str()}\n{result.stderr.str()}"
    assert "profile=moira-local" in output


def test_explicit_nightly_profile_takes_precedence_before_collection(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_hypothesis_environment(monkeypatch)
    monkeypatch.setenv("MOIRA_TEST_MODE", "1")
    _make_hypothesis_project(
        pytester,
        expected_examples=1000,
        database_is_none=False,
        derandomize=False,
        deadline_is_none=True,
    )

    result = pytester.runpytest_subprocess(
        "tests",
        "-q",
        "--tb=short",
        "--hypothesis-profile=moira-nightly",
        timeout=30,
    )

    _assert_two_tests_passed(result)


def test_cli_verbosity_override_is_reflected_in_effective_receipt(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_hypothesis_environment(monkeypatch)
    monkeypatch.setenv("MOIRA_TEST_MODE", "1")
    _make_hypothesis_project(
        pytester,
        expected_examples=50,
        database_is_none=True,
        derandomize=True,
        expected_verbosity="debug",
    )

    result = pytester.runpytest_subprocess(
        "tests",
        "-q",
        "--tb=short",
        "--hypothesis-verbosity=debug",
        timeout=30,
    )

    _assert_two_tests_passed(result)
    output = f"{result.stdout.str()}\n{result.stderr.str()}"
    assert "profile=moira-ci-with-debug-verbosity" in output
