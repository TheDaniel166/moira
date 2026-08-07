"""Black-box contracts for Moira's pytest determinism policy."""

from __future__ import annotations

from pathlib import Path
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
    "MOIRA_TEST_ARTIFACTS",
    "MOIRA_TEST_RUN_ID",
    "PYTEST_ADDOPTS",
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD",
)


def _make_project(pytester: pytest.Pytester) -> tuple[Path, Path]:
    root = pytester.path
    tests_dir = root / "tests"
    tests_dir.mkdir()
    shutil.copytree(_SOURCE_TESTS / "support", tests_dir / "support")
    plugin_dir = _SOURCE_TESTS / "_pytest_plugins"
    if plugin_dir.is_dir():
        shutil.copytree(plugin_dir, tests_dir / "_pytest_plugins")
    (tests_dir / "conftest.py").write_text(
        _HARNESS_SOURCE,
        encoding="utf-8",
    )
    (tests_dir / "KNOWN_ISSUES.yml").write_text(
        "known_issues: []\n",
        encoding="utf-8",
    )
    (root / "rng_consumer.py").write_text(
        dedent(
            """
            import random

            def pytest_sessionstart(session):
                for _ in range(19):
                    random.random()

            def pytest_collection_modifyitems(config, items):
                for _ in range(23):
                    random.random()
            """
        ),
        encoding="utf-8",
    )
    (tests_dir / "test_probe.py").write_text(
        dedent(
            """
            import os
            import random

            _expected = random.Random(int(os.environ["MOIRA_TEST_SEED"]))

            def test_first_execution_draw_starts_at_declared_seed():
                assert random.random() == _expected.random()

            def test_second_execution_draw_continues_same_stream():
                assert random.random() == _expected.random()
            """
        ),
        encoding="utf-8",
    )
    config = root / "pytest.ini"
    config.write_text(
        "[pytest]\n"
        "pythonpath = . tests\n"
        "strict_config = true\n"
        "strict_markers = true\n",
        encoding="utf-8",
    )
    return root, config


def _run(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
    *,
    seed: int,
) -> pytest.RunResult:
    for name in _POLICY_ENVIRONMENT:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("MOIRA_TEST_MODE", "1")
    monkeypatch.setenv("MOIRA_NO_DOWNLOAD", "1")
    monkeypatch.setenv("MOIRA_STRICT_KNOWN_ISSUES", "1")
    monkeypatch.setenv("MOIRA_TEST_SEED", str(seed))
    root, config = _make_project(pytester)
    return pytester.runpytest_subprocess(
        "-c",
        str(config),
        "-p",
        "rng_consumer",
        str(root / "tests"),
        "-q",
        "--color=no",
        timeout=60,
    )


@pytest.mark.parametrize("seed", (0, 1337, (1 << 64) - 1))
def test_execution_rng_is_reset_after_hostile_session_and_collection_hooks(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
    seed: int,
) -> None:
    result = _run(pytester, monkeypatch, seed=seed)

    result.assert_outcomes(passed=2)
