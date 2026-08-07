"""Adversarial black-box contracts for execution classification and xdist."""

from __future__ import annotations

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


def _make_project(
    pytester: pytest.Pytester,
    files: dict[str, str],
    *,
    parent: str | None = None,
    ini_extra: str = "",
    conftest_suffix: str = "",
    strict: bool = True,
) -> tuple[Path, Path]:
    root = pytester.path
    if parent is not None:
        root = root / parent / "project"
    tests_dir = root / "tests"
    tests_dir.mkdir(parents=True)
    shutil.copytree(_SOURCE_TESTS / "support", tests_dir / "support")
    shutil.copytree(
        _SOURCE_TESTS / "_pytest_plugins",
        tests_dir / "_pytest_plugins",
    )
    (tests_dir / "conftest.py").write_text(
        _HARNESS_SOURCE + dedent(conftest_suffix),
        encoding="utf-8",
    )
    (tests_dir / "KNOWN_ISSUES.yml").write_text(
        "known_issues: []\n",
        encoding="utf-8",
    )
    for relative_name, source in files.items():
        target = tests_dir / relative_name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(dedent(source), encoding="utf-8")
    config = root / "pytest.ini"
    strict_config = (
        "strict_config = true\nstrict_markers = true\n"
        if strict
        else ""
    )
    config.write_text(
        "[pytest]\n"
        "pythonpath = . tests\n"
        "addopts = -ra\n"
        + strict_config
        + dedent(ini_extra),
        encoding="utf-8",
    )
    return root, config


def _run(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
    root: Path,
    config: Path,
    *arguments: str,
) -> pytest.RunResult:
    for name in _POLICY_ENVIRONMENT:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("MOIRA_TEST_MODE", "1")
    monkeypatch.setenv("MOIRA_NO_DOWNLOAD", "1")
    monkeypatch.setenv("MOIRA_STRICT_KNOWN_ISSUES", "1")
    return pytester.runpytest_subprocess(
        "-c",
        str(config),
        str(root / "tests"),
        *arguments,
        "--color=no",
        "--tb=short",
        timeout=60,
    )


def _output(result: pytest.RunResult) -> str:
    return f"{result.stdout.str()}\n{result.stderr.str()}"


def _assert_rejected(
    result: pytest.RunResult,
    *diagnostic_patterns: str,
) -> None:
    output = _output(result)
    assert result.ret != pytest.ExitCode.OK, output
    for pattern in diagnostic_patterns:
        assert re.search(pattern, output, re.IGNORECASE | re.DOTALL), (
            f"missing diagnostic {pattern!r}\n{output}"
        )


def _summary_lines(
    result: pytest.RunResult,
    prefix: str,
) -> list[str]:
    return [
        line.strip()
        for line in _output(result).splitlines()
        if line.strip().startswith(prefix)
    ]


def _semantic_receipt_lines(result: pytest.RunResult) -> list[str]:
    prefixes = (
        "Execution classification:",
        "Primary collected:",
        "Primary selected:",
        "Concurrency selected:",
        "Classification manifest:",
        "Optional empty enumerations:",
    )
    return [
        line.strip()
        for line in _output(result).splitlines()
        if line.strip().startswith(prefixes)
    ]


def test_primary_class_ignores_absolute_parent_names(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, config = _make_project(
        pytester,
        {
            "integration/test_probe.py": """
                def test_probe():
                    pass
            """,
        },
        parent="unit",
    )
    result = _run(
        pytester,
        monkeypatch,
        root,
        config,
        "--collect-only",
        "-m",
        "integration",
        "-q",
    )
    assert result.ret == pytest.ExitCode.OK, _output(result)
    line = _summary_lines(result, "Primary collected:")
    assert line == [
        "Primary collected: legacy_root=0, governance=0, harness=0, "
        "integration=1, metamorphic=0, oracle=0, server=0, stress=0, unit=0"
    ]


def test_metamorphic_directory_derives_selectable_primary_class(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, config = _make_project(
        pytester,
        {
            "metamorphic/test_probe.py": """
                def test_probe():
                    pass
            """,
        },
    )
    result = _run(
        pytester,
        monkeypatch,
        root,
        config,
        "--collect-only",
        "-m",
        "metamorphic",
        "-q",
    )
    assert result.ret == pytest.ExitCode.OK, _output(result)
    assert _summary_lines(result, "Primary collected:") == [
        "Primary collected: legacy_root=0, governance=0, harness=0, "
        "integration=0, metamorphic=1, oracle=0, server=0, stress=0, unit=0"
    ]
    assert _summary_lines(result, "Primary selected:") == [
        "Primary selected: legacy_root=0, governance=0, harness=0, "
        "integration=0, metamorphic=1, oracle=0, server=0, stress=0, unit=0"
    ]


@pytest.mark.parametrize(
    ("relative_name", "source", "diagnostic"),
    (
        (
            "integration/test_probe.py",
            """
            import pytest

            @pytest.mark.unit
            def test_probe():
                pass
            """,
            "contradicts.*integration",
        ),
        (
            "unknown/test_probe.py",
            """
            def test_probe():
                pass
            """,
            "unmapped.*unknown",
        ),
        (
            "unit/test_probe.py",
            """
            import pytest

            @pytest.mark.unit("argument")
            def test_probe():
                pass
            """,
            "primary marker.*takes no arguments",
        ),
    ),
    ids=("contradiction", "unknown-directory", "primary-arguments"),
)
def test_primary_class_policy_fails_closed(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
    relative_name: str,
    source: str,
    diagnostic: str,
) -> None:
    root, config = _make_project(pytester, {relative_name: source})
    result = _run(
        pytester,
        monkeypatch,
        root,
        config,
        "--collect-only",
        "-q",
    )
    _assert_rejected(result, diagnostic)


def test_primary_class_rejects_a_symlink_escape(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, config = _make_project(pytester, {})
    outside = root / "outside_test.py"
    outside.write_text("def test_escape():\n    pass\n", encoding="utf-8")
    link = root / "tests" / "unit" / "test_escape.py"
    link.parent.mkdir()
    try:
        link.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"test environment cannot create a file symlink: {exc}")

    result = _run(
        pytester,
        monkeypatch,
        root,
        config,
        "--collect-only",
        "-q",
    )
    _assert_rejected(result, "source path escapes tests")


@pytest.mark.parametrize(
    ("ini_extra", "arguments", "source", "diagnostic"),
    (
        (
            "",
            (),
            """
            import pytest

            @pytest.mark.unknown_capability
            def test_probe():
                pass
            """,
            "unknown_capability",
        ),
        (
            "unknown_policy_key = true\n",
            (),
            """
            def test_probe():
                pass
            """,
            "unknown_policy_key",
        ),
        (
            "",
            ("-o", "strict_markers=false"),
            """
            def test_probe():
                pass
            """,
            "cannot be weakened",
        ),
        (
            "",
            ("-o", "strict_config=off"),
            """
            def test_probe():
                pass
            """,
            "cannot be weakened",
        ),
    ),
    ids=(
        "unknown-marker",
        "unknown-config",
        "marker-override",
        "config-override",
    ),
)
def test_strictness_cannot_be_omitted_or_weakened(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
    ini_extra: str,
    arguments: tuple[str, ...],
    source: str,
    diagnostic: str,
) -> None:
    root, config = _make_project(
        pytester,
        {"test_probe.py": source},
        ini_extra=ini_extra,
    )
    result = _run(
        pytester,
        monkeypatch,
        root,
        config,
        *arguments,
        "--collect-only",
        "-q",
    )
    _assert_rejected(result, diagnostic)


def test_alternate_config_must_enable_native_strictness(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, config = _make_project(
        pytester,
        {
            "unit/test_probe.py": """
                import pytest

                @pytest.mark.unknown_helper_policy
                def helper():
                    pass

                def test_probe():
                    pass
            """,
        },
        strict=False,
    )
    result = _run(
        pytester,
        monkeypatch,
        root,
        config,
        "--collect-only",
        "-q",
    )
    _assert_rejected(result, "strict_config", "strict_markers")


def test_legacy_native_strict_flag_satisfies_effective_strictness(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, config = _make_project(
        pytester,
        {
            "unit/test_probe.py": """
                def test_probe():
                    pass
            """,
        },
        strict=False,
        ini_extra="strict = true\n",
    )
    result = _run(pytester, monkeypatch, root, config, "-q")
    result.assert_outcomes(passed=1)


def test_unmarked_tests_remain_local_only(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, config = _make_project(
        pytester,
        {
            "test_probe.py": """
                def test_probe():
                    pass
            """,
        },
    )
    result = _run(pytester, monkeypatch, root, config, "-q")
    result.assert_outcomes(passed=1)
    assert _summary_lines(result, "Concurrency selected:") == [
        "Concurrency selected: local_only=1, parallel=0, serial=0"
    ]


@pytest.mark.parametrize(
    ("marker_source", "diagnostic"),
    (
        (
            """
            pytestmark = [
                pytest.mark.parallel(reason="read_only"),
                pytest.mark.serial(reason="global_state"),
            ]
            """,
            "parallel and serial.*conflict",
        ),
        (
            'pytestmark = pytest.mark.parallel("read_only")',
            "parallel requires exactly one keyword",
        ),
        (
            'pytestmark = pytest.mark.serial(reason="invented_reason")',
            "unsupported serial reason",
        ),
    ),
    ids=("contradiction", "positional-reason", "unknown-reason"),
)
def test_concurrency_marker_law_fails_before_deselection(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
    marker_source: str,
    diagnostic: str,
) -> None:
    root, config = _make_project(
        pytester,
        {
            "test_probe.py": (
                "import pytest\n\n"
                + dedent(marker_source).strip()
                + "\n\n\ndef test_probe():\n    pass\n"
            ),
        },
    )
    result = _run(
        pytester,
        monkeypatch,
        root,
        config,
        "-m",
        "not serial",
        "--collect-only",
        "-q",
    )
    _assert_rejected(result, diagnostic)


def test_xdist_admits_only_selected_parallel_items_and_does_not_multiply_receipt(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("xdist")
    root, config = _make_project(
        pytester,
        {
            "test_probe.py": """
                import pytest

                @pytest.mark.parallel(reason="read_only")
                def test_parallel():
                    pass

                @pytest.mark.serial(reason="global_state")
                def test_serial():
                    raise AssertionError("serial item entered xdist")
            """,
        },
    )
    result = _run(
        pytester,
        monkeypatch,
        root,
        config,
        "-n",
        "2",
        "--dist=load",
        "-m",
        "parallel",
        "-q",
    )
    result.assert_outcomes(passed=1)
    assert _summary_lines(result, "Execution classification:") == [
        "Execution classification: collected=2, selected=1, "
        "deselected=1, skipped=0"
    ]
    assert _summary_lines(result, "Concurrency selected:") == [
        "Concurrency selected: local_only=0, parallel=1, serial=0"
    ]


@pytest.mark.parametrize(
    ("source", "arguments", "diagnostic"),
    (
        (
            """
            import pytest
            pytestmark = pytest.mark.serial(reason="global_state")

            def test_probe():
                raise AssertionError("unadmitted body executed")
            """,
            ("-n", "1"),
            "xdist selected a serial item",
        ),
        (
            """
            def test_probe():
                raise AssertionError("unadmitted body executed")
            """,
            ("-n", "2"),
            "xdist selected a local_only item",
        ),
        (
            """
            import pytest
            pytestmark = pytest.mark.parallel(reason="read_only")

            def test_probe():
                raise AssertionError("unadmitted body executed")
            """,
            ("-n", "2", "--dist=each"),
            "dist=each",
        ),
    ),
    ids=("serial", "local-only", "dist-each"),
)
def test_xdist_rejects_unadmitted_execution(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
    source: str,
    arguments: tuple[str, ...],
    diagnostic: str,
) -> None:
    pytest.importorskip("xdist")
    root, config = _make_project(pytester, {"test_probe.py": source})
    result = _run(
        pytester,
        monkeypatch,
        root,
        config,
        *arguments,
        "-q",
    )
    _assert_rejected(result, diagnostic)
    assert "unadmitted body executed" not in _output(result)


def test_xdist_worker_manifest_is_resealed_after_inner_plugin_mutation(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("xdist")
    root, config = _make_project(
        pytester,
        {
            "test_probe.py": """
                import pytest

                pytestmark = pytest.mark.parallel(reason="read_only")

                @pytest.mark.parametrize("index", range(4))
                def test_probe(index):
                    assert index in range(4)
            """,
        },
    )
    (root / "classification_corruptor.py").write_text(
        dedent(
            """
            import pytest

            @pytest.hookimpl(trylast=True)
            def pytest_sessionfinish(session, exitstatus):
                config = session.config
                workeroutput = getattr(config, "workeroutput", None)
                workerinput = getattr(config, "workerinput", None)
                if (
                    isinstance(workeroutput, dict)
                    and isinstance(workerinput, dict)
                    and workerinput.get("workerid") == "gw1"
                ):
                    receipt = workeroutput.get(
                        "moira_execution_classification_v1"
                    )
                    if isinstance(receipt, dict):
                        receipt["selected_digest"] = "0" * 64
            """
        ),
        encoding="utf-8",
    )
    result = _run(
        pytester,
        monkeypatch,
        root,
        config,
        "-p",
        "classification_corruptor",
        "-n",
        "2",
        "--dist=load",
        "-q",
    )
    result.assert_outcomes(passed=4)
    assert "contradicts the canonical worker manifest" not in _output(result)


def test_xdist_digest_includes_parallel_reason(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("xdist")
    root, config = _make_project(
        pytester,
        {
            "unit/test_probe.py": """
                import os
                import pytest

                reason = (
                    "worker_isolated"
                    if os.environ.get("PYTEST_XDIST_WORKER") == "gw1"
                    else "read_only"
                )
                pytestmark = pytest.mark.parallel(reason=reason)

                def test_probe():
                    pass
            """,
        },
    )
    result = _run(
        pytester,
        monkeypatch,
        root,
        config,
        "-n",
        "2",
        "--dist=load",
        "-q",
    )
    _assert_rejected(result, "contradicts the canonical worker manifest")




def test_serial_lane_is_admitted_only_without_xdist(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, config = _make_project(
        pytester,
        {
            "test_probe.py": """
                import os
                import pytest

                pytestmark = pytest.mark.serial(reason="lane_canary")

                def test_probe():
                    assert "PYTEST_XDIST_WORKER" not in os.environ
            """,
        },
    )
    result = _run(
        pytester,
        monkeypatch,
        root,
        config,
        "-n",
        "0",
        "-m",
        "serial",
        "-q",
    )
    result.assert_outcomes(passed=1)


def test_late_marker_mutation_cannot_bypass_post_selection_enforcement(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("xdist")
    root, config = _make_project(
        pytester,
        {
            "test_probe.py": """
                import pytest

                pytestmark = pytest.mark.parallel(reason="read_only")

                def test_probe():
                    pass
            """,
        },
        conftest_suffix="""
            @pytest.hookimpl(
                wrapper=True,
                trylast=True,
                specname="pytest_collection_modifyitems",
            )
            def pytest_collection_modifyitems_late_mutator(config, items):
                yield
                for item in items:
                    item.add_marker(
                        pytest.mark.serial(reason="global_state")
                    )
        """,
    )
    result = _run(
        pytester,
        monkeypatch,
        root,
        config,
        "-n",
        "1",
        "-q",
    )
    _assert_rejected(result, "parallel and serial.*conflict")


def test_late_valid_reason_mutation_is_rejected_as_classification_drift(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, config = _make_project(
        pytester,
        {
            "unit/test_probe.py": """
                import pytest

                pytestmark = pytest.mark.parallel(reason="read_only")

                def test_probe():
                    raise AssertionError("classification drift executed")
            """,
        },
        conftest_suffix="""
            @pytest.hookimpl(
                wrapper=True,
                trylast=True,
                specname="pytest_collection_modifyitems",
            )
            def pytest_collection_modifyitems_reason_mutator(config, items):
                yield
                for item in items:
                    marker = item.get_closest_marker("parallel")
                    marker.kwargs["reason"] = "worker_isolated"
        """,
    )
    result = _run(pytester, monkeypatch, root, config, "-n", "0", "-q")
    _assert_rejected(result, "classification changed after initial")
    assert "classification drift executed" not in _output(result)


def test_late_marker_mutation_is_checked_even_when_item_is_deselected(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, config = _make_project(
        pytester,
        {
            "unit/test_probe.py": """
                import pytest

                pytestmark = pytest.mark.parallel(reason="read_only")

                def test_keep():
                    pass

                def test_mutated_then_deselected():
                    raise AssertionError("deselected body executed")
            """,
        },
        conftest_suffix="""
            @pytest.hookimpl(
                wrapper=True,
                trylast=True,
                specname="pytest_collection_modifyitems",
            )
            def pytest_collection_modifyitems_mutate_and_deselect(
                config,
                items,
            ):
                yield
                victim = next(
                    item
                    for item in items
                    if "mutated_then_deselected" in item.nodeid
                )
                victim.add_marker(
                    pytest.mark.serial(reason="global_state")
                )
                items[:] = [item for item in items if item is not victim]
        """,
    )
    result = _run(pytester, monkeypatch, root, config, "-n", "0", "-q")
    _assert_rejected(result, "parallel and serial.*conflict")
    assert "deselected body executed" not in _output(result)


def test_collection_finish_marker_mutation_cannot_reopen_xdist_admission(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("xdist")
    root, config = _make_project(
        pytester,
        {
            "unit/test_probe.py": """
                import pytest

                pytestmark = pytest.mark.parallel(reason="read_only")

                def test_probe():
                    raise AssertionError("late-mutated body executed")
            """,
        },
        conftest_suffix="""
            @pytest.hookimpl(
                trylast=True,
                specname="pytest_collection_finish",
            )
            def pytest_collection_finish_late_mutator(session):
                for item in session.items:
                    item.add_marker(
                        pytest.mark.serial(reason="global_state")
                    )
        """,
    )
    result = _run(pytester, monkeypatch, root, config, "-n", "1", "-q")
    _assert_rejected(
        result,
        "Frozen execution classification",
        "parallel and serial.*conflict",
    )
    assert "late-mutated body executed" not in _output(result)


def test_mutable_workerinput_cannot_disable_xdist_admission(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("xdist")
    root, config = _make_project(
        pytester,
        {
            "unit/test_probe.py": """
                def test_probe():
                    raise AssertionError("workerinput bypass executed")
            """,
        },
        conftest_suffix="""
            @pytest.hookimpl(
                trylast=True,
                specname="pytest_sessionstart",
            )
            def pytest_sessionstart_workerinput_mutator(session):
                workerinput = getattr(session.config, "workerinput", None)
                if isinstance(workerinput, dict):
                    workerinput["moira_xdist_mode"] = "no"
        """,
    )
    result = _run(pytester, monkeypatch, root, config, "-n", "1", "-q")
    _assert_rejected(result, "xdist selected a local_only item")
    assert "workerinput bypass executed" not in _output(result)


def test_late_dist_mutation_cannot_switch_scheduler_to_each(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("xdist")
    root, config = _make_project(
        pytester,
        {
            "unit/test_probe.py": """
                import pytest

                pytestmark = pytest.mark.parallel(reason="read_only")

                def test_probe():
                    raise AssertionError("late scheduler mutation executed")
            """,
        },
        conftest_suffix="""
            @pytest.hookimpl(
                trylast=True,
                specname="pytest_sessionstart",
            )
            def pytest_sessionstart_dist_mutator(session):
                if not hasattr(session.config, "workerinput"):
                    session.config.option.dist = "each"
        """,
    )
    result = _run(
        pytester,
        monkeypatch,
        root,
        config,
        "-n",
        "2",
        "--dist=load",
        "-q",
    )
    _assert_rejected(
        result,
        "scheduler mode changed after Moira admission",
        "admitted='load'.*live='each'",
    )
    assert "late scheduler mutation executed" not in _output(result)


@pytest.mark.parametrize(
    "attack_suffix",
    (
        """
        @pytest.hookimpl(
            tryfirst=True,
            specname="pytest_xdist_make_scheduler",
        )
        def pytest_xdist_make_scheduler_override(config, log):
            from xdist.scheduler import EachScheduling
            return EachScheduling(config, log)
        """,
        """
        @pytest.hookimpl(
            wrapper=True,
            trylast=True,
            specname="pytest_xdist_make_scheduler",
        )
        def pytest_xdist_make_scheduler_mutator(config, log):
            admitted = config.option.dist
            config.option.dist = "each"
            scheduler = yield
            config.option.dist = admitted
            return scheduler
        """,
        """
        @pytest.hookimpl(
            wrapper=True,
            tryfirst=True,
            specname="pytest_xdist_make_scheduler",
        )
        def pytest_xdist_make_scheduler_outer(config, log):
            yield
            from xdist.scheduler import EachScheduling
            return EachScheduling(config, log)
        """,
    ),
    ids=("direct-each-override", "hidden-each-wrapper", "outer-each-wrapper"),
)
def test_scheduler_hook_cannot_substitute_each(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
    attack_suffix: str,
) -> None:
    pytest.importorskip("xdist")
    root, config = _make_project(
        pytester,
        {
            "unit/test_probe.py": """
                import pytest

                pytestmark = pytest.mark.parallel(reason="read_only")

                def test_probe():
                    raise AssertionError("substituted scheduler executed")
            """,
        },
        conftest_suffix=attack_suffix,
    )
    result = _run(
        pytester,
        monkeypatch,
        root,
        config,
        "-n",
        "2",
        "--dist=load",
        "-q",
    )
    _assert_rejected(
        result,
        "Unadmitted pytest_xdist_make_scheduler implementation",
    )
    assert "substituted scheduler executed" not in _output(result)


@pytest.mark.parametrize(
    ("marker", "values", "expected", "diagnostic"),
    (
        (
            "@pytest.mark.required_enumeration",
            "()",
            "rejected",
            "required enumeration produced an empty",
        ),
        (
            "",
            "()",
            "rejected",
            "empty parameter set must be classified",
        ),
        (
            '@pytest.mark.optional_enumeration(reason="feature_not_installed")',
            "()",
            "skipped",
            "",
        ),
        (
            "@pytest.mark.required_enumeration",
            "(1, 2)",
            "passed",
            "",
        ),
    ),
    ids=("required-empty", "unclassified-empty", "optional-empty", "required"),
)
def test_enumeration_policy_is_explicit(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
    marker: str,
    values: str,
    expected: str,
    diagnostic: str,
) -> None:
    root, config = _make_project(
        pytester,
        {
            "unit/test_probe.py": f"""
                import pytest

                {marker}
                @pytest.mark.parametrize("value", {values})
                def test_probe(value):
                    assert value in (1, 2)
            """,
        },
    )
    result = _run(pytester, monkeypatch, root, config, "-q")
    if expected == "rejected":
        _assert_rejected(result, diagnostic)
    elif expected == "skipped":
        result.assert_outcomes(skipped=1)
        assert _summary_lines(result, "Optional empty enumerations:") == [
            "Optional empty enumerations: collected=1, selected=1"
        ]
    else:
        result.assert_outcomes(passed=2)


def test_enumeration_marker_on_nonparametrized_test_is_rejected(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, config = _make_project(
        pytester,
        {
            "unit/test_probe.py": """
                import pytest

                @pytest.mark.required_enumeration
                def test_probe():
                    pass
            """,
        },
    )
    result = _run(pytester, monkeypatch, root, config, "-q")
    _assert_rejected(result, "enumeration marker requires a parametrized")


@pytest.mark.parametrize(
    ("markers", "diagnostic"),
    (
        (
            """
            @pytest.mark.required_enumeration
            @pytest.mark.optional_enumeration(reason="feature_not_installed")
            """,
            "required_enumeration and optional_enumeration conflict",
        ),
        (
            '@pytest.mark.optional_enumeration("feature_not_installed")',
            "optional_enumeration requires exactly one keyword",
        ),
        (
            '@pytest.mark.optional_enumeration(reason="INVALID")',
            "optional_enumeration reason must be a stable lowercase slug",
        ),
    ),
    ids=("required-optional-conflict", "optional-positional", "optional-reason"),
)
def test_enumeration_marker_schema_is_enforced(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
    markers: str,
    diagnostic: str,
) -> None:
    root, config = _make_project(
        pytester,
        {
            "unit/test_probe.py": (
                "import pytest\n\n"
                + dedent(markers).strip()
                + "\n@pytest.mark.parametrize(\"value\", (1,))\n"
                "def test_probe(value):\n"
                "    assert value == 1\n"
            ),
        },
    )
    result = _run(pytester, monkeypatch, root, config, "-q")
    _assert_rejected(result, diagnostic)


def test_optional_enumeration_on_nonparametrized_test_is_rejected(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, config = _make_project(
        pytester,
        {
            "unit/test_probe.py": """
                import pytest

                @pytest.mark.optional_enumeration(
                    reason="feature_not_installed"
                )
                def test_probe():
                    pass
            """,
        },
    )
    result = _run(pytester, monkeypatch, root, config, "-q")
    _assert_rejected(result, "enumeration marker requires a parametrized")


def test_inherited_optional_enumeration_reasons_must_agree(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, config = _make_project(
        pytester,
        {
            "unit/test_probe.py": """
                import pytest

                pytestmark = pytest.mark.optional_enumeration(
                    reason="feature_not_installed"
                )

                @pytest.mark.optional_enumeration(reason="no_admitted_cases")
                @pytest.mark.parametrize("value", ())
                def test_probe(value):
                    raise AssertionError("empty body executed")
            """,
        },
    )
    result = _run(pytester, monkeypatch, root, config, "-q")
    _assert_rejected(
        result,
        "inherited optional_enumeration declarations disagree",
    )


def test_receipt_counts_selection_and_runtime_skips_exactly_once(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, config = _make_project(
        pytester,
        {
            "unit/test_probe.py": """
                import pytest

                def test_keep():
                    pass

                @pytest.mark.skip(reason="receipt canary")
                def test_skip():
                    raise AssertionError("skip body executed")

                def test_drop():
                    raise AssertionError("deselected body executed")
            """,
        },
    )
    result = _run(
        pytester,
        monkeypatch,
        root,
        config,
        "-k",
        "keep or skip",
        "-q",
    )
    result.assert_outcomes(passed=1, skipped=1, deselected=1)
    assert _summary_lines(result, "Execution classification:") == [
        "Execution classification: collected=3, selected=2, "
        "deselected=1, skipped=1"
    ]
    assert _summary_lines(result, "Primary selected:") == [
        "Primary selected: legacy_root=0, governance=0, harness=0, "
        "integration=0, metamorphic=0, oracle=0, server=0, stress=0, unit=2"
    ]


def test_receipt_includes_collection_phase_skips(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, config = _make_project(
        pytester,
        {
            "unit/test_module_skip.py": """
                import pytest

                pytest.skip(
                    "collection skip canary",
                    allow_module_level=True,
                )

                def test_never_collected():
                    raise AssertionError("module skip body executed")
            """,
            "unit/test_keep.py": """
                def test_keep():
                    pass
            """,
        },
    )
    result = _run(pytester, monkeypatch, root, config, "-q")
    result.assert_outcomes(passed=1, skipped=1)
    assert _summary_lines(result, "Execution classification:") == [
        "Execution classification: collected=1, selected=1, "
        "deselected=0, skipped=1"
    ]


def test_serial_and_xdist_emit_the_same_semantic_receipt(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("xdist")
    root, config = _make_project(
        pytester,
        {
            "unit/test_probe.py": """
                import pytest

                pytestmark = pytest.mark.parallel(reason="read_only")

                @pytest.mark.parametrize("value", (1, 2))
                def test_probe(value):
                    assert value in (1, 2)
            """,
            "integration/test_optional.py": """
                import pytest

                pytestmark = [
                    pytest.mark.parallel(reason="read_only"),
                    pytest.mark.optional_enumeration(
                        reason="no_admitted_cases"
                    ),
                ]

                @pytest.mark.parametrize("value", ())
                def test_optional(value):
                    raise AssertionError("empty body executed")
            """,
        },
    )
    serial = _run(
        pytester,
        monkeypatch,
        root,
        config,
        "-n",
        "0",
        "-m",
        "parallel",
        "-q",
    )
    distributed = _run(
        pytester,
        monkeypatch,
        root,
        config,
        "-n",
        "2",
        "--dist=load",
        "-m",
        "parallel",
        "-q",
    )
    serial.assert_outcomes(passed=2, skipped=1)
    distributed.assert_outcomes(passed=2, skipped=1)
    assert _semantic_receipt_lines(distributed) == _semantic_receipt_lines(
        serial
    )
