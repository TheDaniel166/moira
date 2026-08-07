"""Black-box contracts for controller-owned ephemeral pytest receipts."""

from __future__ import annotations

import hashlib
import json
import math
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
    "MOIRA_KERNEL_PATH",
    "PYTEST_ADDOPTS",
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD",
    "COVERAGE_FILE",
    "COVERAGE_CORE",
    "COVERAGE_FORCE_CONFIG",
    "COVERAGE_PROCESS_CONFIG",
    "COVERAGE_PROCESS_START",
    "COVERAGE_RCFILE",
)
_RECEIPT_FILES = {
    "run.json",
    "collection.json",
    "resources.json",
    "reports.jsonl",
    "failures.json",
    "durations.json",
    "rerun-nodeids.json",
}


def _make_project(
    pytester: pytest.Pytester,
    files: dict[str, str],
    *,
    conftest_suffix: str = "",
) -> tuple[Path, Path]:
    root = pytester.path
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
    config.write_text(
        "[pytest]\n"
        "pythonpath = . tests\n"
        "addopts = -ra\n"
        "strict_config = true\n"
        "strict_markers = true\n",
        encoding="utf-8",
    )
    return root, config


def _run(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
    root: Path,
    config: Path,
    *arguments: str,
    run_id: str | None = None,
    coverage_file: str | None = None,
    coverage_core: str | None = None,
) -> pytest.RunResult:
    for name in _POLICY_ENVIRONMENT:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("MOIRA_TEST_MODE", "1")
    monkeypatch.setenv("MOIRA_NO_DOWNLOAD", "1")
    monkeypatch.setenv("MOIRA_STRICT_KNOWN_ISSUES", "1")
    monkeypatch.setenv("MOIRA_TEST_ARTIFACTS", "1")
    if run_id is not None:
        monkeypatch.setenv("MOIRA_TEST_RUN_ID", run_id)
    if coverage_file is not None:
        monkeypatch.setenv("COVERAGE_FILE", coverage_file)
    if coverage_core is not None:
        monkeypatch.setenv("COVERAGE_CORE", coverage_core)
    return pytester.runpytest_subprocess(
        "-c",
        str(config),
        str(root / "tests"),
        *arguments,
        "--color=no",
        "--tb=short",
        timeout=90,
    )


def _output(result: pytest.RunResult) -> str:
    return f"{result.stdout.str()}\n{result.stderr.str()}"


def _artifact_root(root: Path) -> Path:
    return root / ".pytest_cache" / "moira-artifacts"


def _artifact_runs(root: Path) -> list[Path]:
    artifact_root = _artifact_root(root)
    if not artifact_root.exists():
        return []
    return sorted(path for path in artifact_root.iterdir() if path.is_dir())


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_reports(run_dir: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in (run_dir / "reports.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]


def _tree_bytes(root: Path) -> dict[str, bytes]:
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _assert_complete_receipt(run_dir: Path, *, run_id: str) -> None:
    names = {path.name for path in run_dir.iterdir()}
    assert names == _RECEIPT_FILES | {"COMPLETE"}
    assert "INCOMPLETE" not in names
    assert not any(path.name.endswith(".tmp") for path in run_dir.rglob("*"))

    run_path = run_dir / "run.json"
    run_receipt = _load_json(run_path)
    assert isinstance(run_receipt, dict)
    assert run_receipt["schema_version"] == 1
    assert run_receipt["run_id"] == run_id

    manifest = run_receipt["artifacts"]
    assert isinstance(manifest, dict)
    assert set(manifest) == _RECEIPT_FILES - {"run.json"}
    for relative_name, identity in manifest.items():
        assert isinstance(relative_name, str)
        assert isinstance(identity, dict)
        artifact = run_dir / relative_name
        assert identity == {
            "bytes": artifact.stat().st_size,
            "sha256": _sha256(artifact),
        }

    complete = _load_json(run_dir / "COMPLETE")
    assert isinstance(complete, dict)
    assert complete == {
        "schema_version": 1,
        "run_id": run_id,
        "status": "complete",
        "run_json": {
            "bytes": run_path.stat().st_size,
            "sha256": _sha256(run_path),
        },
    }


def _assert_incomplete_receipt(run_dir: Path, *, run_id: str) -> dict[str, object]:
    assert run_dir.is_dir()
    assert not (run_dir / "COMPLETE").exists()
    incomplete = _load_json(run_dir / "INCOMPLETE")
    assert isinstance(incomplete, dict)
    assert incomplete["schema_version"] == 1
    assert incomplete["run_id"] == run_id
    assert incomplete["status"] == "incomplete"
    assert isinstance(incomplete["finalization_errors"], list)
    return incomplete


@pytest.mark.parametrize(
    "run_id",
    (
        ".",
        "..",
        "../escape",
        r"..\escape",
        "/absolute",
        r"C:\absolute",
        "nested/component",
        "drive:relative",
        "NUL",
        "unicod\u00e9",
    ),
)
def test_run_id_rejects_nonportable_or_escaping_components(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
    run_id: str,
) -> None:
    root, config = _make_project(
        pytester,
        {
            "unit/test_probe.py": """
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
        "-q",
        run_id=run_id,
    )
    output = _output(result)
    assert result.ret != pytest.ExitCode.OK, output
    assert re.search(
        r"MOIRA_TEST_RUN_ID.*(?:portable|path component|reserved)",
        output,
        re.IGNORECASE | re.DOTALL,
    ), output
    assert _artifact_runs(root) == []
    assert not (root / "tests" / "artifacts").exists()


def test_run_id_collision_is_fail_closed_and_preserves_first_receipt(
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
    )
    first = _run(
        pytester,
        monkeypatch,
        root,
        config,
        "-q",
        run_id="collision_canary",
    )
    assert first.ret == pytest.ExitCode.OK, _output(first)
    run_dir = _artifact_root(root) / "collision_canary"
    _assert_complete_receipt(run_dir, run_id="collision_canary")
    before = _tree_bytes(run_dir)

    second = _run(
        pytester,
        monkeypatch,
        root,
        config,
        "-q",
        run_id="collision_canary",
    )
    output = _output(second)
    assert second.ret != pytest.ExitCode.OK, output
    assert re.search(r"collid|refus.*(?:resume|overwrite)", output, re.IGNORECASE)
    assert _tree_bytes(run_dir) == before
    assert _artifact_runs(root) == [run_dir]


def test_default_uuid_receipt_is_ephemeral_fixed_and_hash_bound(
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
    )
    protected_tree = root / "tests" / "artifacts"
    before = _tree_bytes(protected_tree)
    result = _run(pytester, monkeypatch, root, config, "-q")
    assert result.ret == pytest.ExitCode.OK, _output(result)

    runs = _artifact_runs(root)
    assert len(runs) == 1
    run_dir = runs[0]
    assert re.fullmatch(r"[0-9a-f]{32}", run_dir.name)
    assert run_dir.resolve().is_relative_to(
        (root / ".pytest_cache" / "moira-artifacts").resolve()
    )
    _assert_complete_receipt(run_dir, run_id=run_dir.name)
    assert _tree_bytes(protected_tree) == before
    assert not protected_tree.exists()


def test_reports_preserve_setup_call_and_teardown_outcomes(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, config = _make_project(
        pytester,
        {
            "unit/test_lifecycle.py": """
                def test_passes_all_phases():
                    pass

                def test_fails_in_call():
                    raise AssertionError("call-phase-canary")
            """,
        },
    )
    result = _run(
        pytester,
        monkeypatch,
        root,
        config,
        "-q",
        run_id="lifecycle_receipt",
    )
    assert result.ret == pytest.ExitCode.TESTS_FAILED, _output(result)
    run_dir = _artifact_root(root) / "lifecycle_receipt"
    _assert_complete_receipt(run_dir, run_id="lifecycle_receipt")
    reports = _load_reports(run_dir)

    def phases_for(test_name: str) -> list[tuple[str, str]]:
        return [
            (str(report["phase"]), str(report["outcome"]))
            for report in reports
            if report["kind"] == "test"
            and str(report["nodeid"]).endswith(f"::{test_name}")
        ]

    assert phases_for("test_passes_all_phases") == [
        ("setup", "passed"),
        ("call", "passed"),
        ("teardown", "passed"),
    ]
    assert phases_for("test_fails_in_call") == [
        ("setup", "passed"),
        ("call", "failed"),
        ("teardown", "passed"),
    ]
    sequences = [report["sequence"] for report in reports]
    assert sequences == list(range(1, len(reports) + 1))
    for report in reports:
        duration = report["duration_s"]
        assert isinstance(duration, (int, float))
        assert math.isfinite(duration)
        assert duration >= 0


def test_retry_attempts_preserve_phase_ownership_after_setup_failure(
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
        conftest_suffix="""
            from types import SimpleNamespace as _Phase7Report
            from _pytest_plugins import artifacts as _phase8_artifacts


            @pytest.hookimpl(
                trylast=True,
                specname="pytest_sessionfinish",
            )
            def pytest_sessionfinish_phase7_retry_probe(session, exitstatus):
                collector = _phase8_artifacts._controller_collector(
                    session.config
                )
                assert collector is not None
                nodeid = "tests/unit/test_synthetic_retry.py::test_retry"

                def record(phase, outcome):
                    collector._record(
                        _Phase7Report(
                            nodeid=nodeid,
                            duration=0.01,
                            outcome=outcome,
                            worker_id="controller",
                            longrepr=(
                                "synthetic setup failure"
                                if outcome == "failed"
                                else ""
                            ),
                            sections=(),
                            user_properties=(),
                        ),
                        kind="test",
                        phase=phase,
                    )

                record("setup", "failed")
                record("teardown", "passed")
                record("setup", "passed")
                record("call", "passed")
                record("teardown", "passed")

                nodeid = (
                    "tests/unit/test_synthetic_retry.py::"
                    "test_retry_then_skip"
                )
                record("setup", "failed")
                record("teardown", "passed")
                record("setup", "skipped")
                record("teardown", "passed")
        """,
    )
    result = _run(
        pytester,
        monkeypatch,
        root,
        config,
        "-q",
        run_id="retry_phase_ownership",
    )
    assert result.ret == pytest.ExitCode.OK, _output(result)
    run_dir = _artifact_root(root) / "retry_phase_ownership"
    _assert_complete_receipt(run_dir, run_id="retry_phase_ownership")

    durations = _load_json(run_dir / "durations.json")
    assert isinstance(durations, dict)
    retry_cases = [
        case
        for case in durations["cases"]
        if case["nodeid"].endswith("::test_retry")
    ]
    assert [case["attempt"] for case in retry_cases] == [1, 2]
    first, second = retry_cases
    assert first["phases"]["setup"]["outcome"] == "failed"
    assert first["phases"]["call"]["status"] == "not_run"
    assert first["phases"]["teardown"]["outcome"] == "passed"
    assert second["phases"]["setup"]["outcome"] == "passed"
    assert second["phases"]["call"]["outcome"] == "passed"
    assert second["phases"]["teardown"]["outcome"] == "passed"
    skipped_cases = [
        case
        for case in durations["cases"]
        if case["nodeid"].endswith("::test_retry_then_skip")
    ]
    assert [case["attempt"] for case in skipped_cases] == [1, 2]
    assert skipped_cases[1]["phases"]["setup"]["outcome"] == "skipped"
    assert skipped_cases[1]["phases"]["call"]["status"] == "not_run"

    failures = _load_json(run_dir / "failures.json")
    assert isinstance(failures, dict)
    assert failures["flakes"] == [
        {
            "nodeid": "tests/unit/test_synthetic_retry.py::test_retry",
            "failed_attempt": 1,
            "passing_attempt": 2,
        }
    ]


def test_planetary_resource_receipt_binds_candidate_content_sha256(
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
        conftest_suffix="""
            from _pytest_plugins import artifacts as _phase8_artifacts


            @pytest.hookimpl(
                trylast=True,
                specname="pytest_sessionfinish",
            )
            def pytest_sessionfinish_phase7_resource_probe(
                session,
                exitstatus,
            ):
                kernel = ROOT_DIR / "phase7-kernel.bsp"
                metadata = kernel.stat()
                has_file_identity = (
                    type(metadata.st_ino) is int
                    and metadata.st_ino > 0
                    and type(metadata.st_dev) is int
                    and metadata.st_dev >= 0
                )
                fingerprint = {
                    "resolved_path": str(kernel.resolve(strict=True)),
                    "size": metadata.st_size,
                    "mtime_ns": metadata.st_mtime_ns,
                    "device_id": (
                        metadata.st_dev if has_file_identity else None
                    ),
                    "file_id": (
                        metadata.st_ino if has_file_identity else None
                    ),
                }
                report = {
                    "version": 1,
                    "summary": {
                        "receipts": 1,
                        "run": 1,
                        "skip": 0,
                        "failure": 0,
                        "identities": ["PHASE7"],
                    },
                    "details": {
                        "tests/unit/test_probe.py::test_probe": {
                            "disposition": "run",
                            "rendered": "phase7 planetary content canary",
                            "candidate": {
                                "fingerprint": fingerprint,
                            },
                        },
                    },
                    "probe_count": 1,
                }
                _phase8_artifacts._combined_planetary_resource_report = (
                    lambda config: report
                )
        """,
    )
    kernel = root / "phase7-kernel.bsp"
    content = b"phase7-planetary-content-canary"
    kernel.write_bytes(content)

    result = _run(
        pytester,
        monkeypatch,
        root,
        config,
        "-q",
        run_id="planetary_content_binding",
    )
    assert result.ret == pytest.ExitCode.OK, _output(result)
    run_dir = _artifact_root(root) / "planetary_content_binding"
    _assert_complete_receipt(
        run_dir,
        run_id="planetary_content_binding",
    )
    resources = _load_json(run_dir / "resources.json")
    assert isinstance(resources, dict)
    fingerprint = resources["planetary"]["details"][
        "tests/unit/test_probe.py::test_probe"
    ]["candidate"]["fingerprint"]
    assert fingerprint["content_sha256"] == hashlib.sha256(
        content
    ).hexdigest()


def test_collection_failure_is_a_structured_controller_report(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, config = _make_project(
        pytester,
        {
            "unit/test_collection_failure.py": """
                raise RuntimeError("collection-phase-canary")
            """,
        },
    )
    result = _run(
        pytester,
        monkeypatch,
        root,
        config,
        "-q",
        run_id="collection_failure",
    )
    assert result.ret != pytest.ExitCode.OK, _output(result)
    run_dir = _artifact_root(root) / "collection_failure"
    _assert_complete_receipt(run_dir, run_id="collection_failure")
    failures = [
        report
        for report in _load_reports(run_dir)
        if report["kind"] == "collection" and report["outcome"] == "failed"
    ]
    assert len(failures) == 1
    failure = failures[0]
    assert failure["phase"] == "collect"
    assert str(failure["nodeid"]).endswith(
        "unit/test_collection_failure.py"
    )
    assert "collection-phase-canary" in str(failure["longrepr"])


def test_secret_values_and_request_headers_never_reach_artifact_bytes(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment_secret = "phase7-environment-secret-9f43"
    header_only_secret = "phase7-header-only-secret-71b2"
    monkeypatch.setenv("MOIRA_PHASE7_SECRET", environment_secret)
    root, config = _make_project(
        pytester,
        {
            "unit/test_secret_output.py": f"""
                import os
                import sys

                def test_secret_output_is_redacted():
                    secret = os.environ["MOIRA_PHASE7_SECRET"]
                    print("Authorization: Bearer " + secret)
                    print("X-API-Key: {header_only_secret}", file=sys.stderr)
                    raise AssertionError(
                        "Cookie: session={header_only_secret}; token=" + secret
                    )
            """,
        },
    )
    result = _run(
        pytester,
        monkeypatch,
        root,
        config,
        "-q",
        run_id="redaction_receipt",
    )
    assert result.ret == pytest.ExitCode.TESTS_FAILED, _output(result)
    run_dir = _artifact_root(root) / "redaction_receipt"
    _assert_complete_receipt(run_dir, run_id="redaction_receipt")

    forbidden = (
        environment_secret.encode("utf-8"),
        header_only_secret.encode("utf-8"),
    )
    files = [path for path in run_dir.rglob("*") if path.is_file()]
    assert files
    for path in files:
        content = path.read_bytes()
        for secret in forbidden:
            assert secret not in content, (
                f"raw secret reached artifact {path.relative_to(run_dir)}"
            )
    assert not any(".tmp" in path.name for path in files)


def test_xdist_runtime_fixture_secret_is_redacted_before_worker_shutdown(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime_secret = "phase7-worker-runtime-secret-8d51"
    root, config = _make_project(
        pytester,
        {
            "unit/test_runtime_secret.py": f"""
                import os
                import pytest

                pytestmark = pytest.mark.parallel(reason="worker_isolated")


                @pytest.fixture
                def runtime_token():
                    os.environ["PHASE7_RUNTIME_API_TOKEN"] = (
                        "{runtime_secret}"
                    )
                    try:
                        yield "{runtime_secret}"
                    finally:
                        os.environ.pop(
                            "PHASE7_RUNTIME_API_TOKEN",
                            None,
                        )


                def test_runtime_secret(runtime_token):
                    print(runtime_token)
                    raise AssertionError(runtime_token)
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
        run_id="runtime_secret_redaction",
    )
    assert result.ret == pytest.ExitCode.TESTS_FAILED, _output(result)
    run_dir = _artifact_root(root) / "runtime_secret_redaction"
    _assert_complete_receipt(
        run_dir,
        run_id="runtime_secret_redaction",
    )
    artifact_bytes = b"".join(
        path.read_bytes()
        for path in sorted(run_dir.iterdir())
        if path.is_file()
    )
    assert runtime_secret.encode("utf-8") not in artifact_bytes
    assert b"[REDACTED]" in artifact_bytes


def test_prior_item_secret_cannot_corrupt_a_later_exact_nodeid(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, config = _make_project(
        pytester,
        {
            "unit/test_secret_lifetime.py": """
                import os
                import pytest


                @pytest.fixture
                def transient_secret():
                    os.environ["PHASE9_TRANSIENT_API_TOKEN"] = "future_node"
                    try:
                        yield
                    finally:
                        os.environ.pop("PHASE9_TRANSIENT_API_TOKEN", None)


                def test_a_capture_secret(transient_secret):
                    pass


                def test_future_node_is_exact():
                    pass
            """,
        },
    )
    result = _run(
        pytester,
        monkeypatch,
        root,
        config,
        "-q",
        run_id="secret_lifetime",
    )
    assert result.ret == pytest.ExitCode.OK, _output(result)
    run_dir = _artifact_root(root) / "secret_lifetime"
    _assert_complete_receipt(run_dir, run_id="secret_lifetime")
    report_nodeids = {
        str(report["nodeid"])
        for report in _load_reports(run_dir)
        if report["kind"] == "test"
    }
    assert any(
        nodeid.endswith("test_future_node_is_exact")
        for nodeid in report_nodeids
    )
    assert all("[NON-REPLAYABLE NODEID]" not in nodeid for nodeid in report_nodeids)


def test_xdist_workers_feed_one_controller_owned_artifact_tree(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, config = _make_project(
        pytester,
        {
            "unit/test_workers.py": """
                import pytest

                pytestmark = pytest.mark.parallel(reason="read_only")

                def test_worker_one():
                    pass

                def test_worker_two():
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
        "-m",
        "parallel",
        "-q",
        run_id="xdist_controller",
    )
    assert result.ret == pytest.ExitCode.OK, _output(result)
    runs = _artifact_runs(root)
    assert runs == [_artifact_root(root) / "xdist_controller"]
    run_dir = runs[0]
    _assert_complete_receipt(run_dir, run_id="xdist_controller")
    assert not any(
        path.is_dir() and path.name.startswith("worker_")
        for path in run_dir.rglob("*")
    )

    test_reports = [
        report
        for report in _load_reports(run_dir)
        if report["kind"] == "test"
    ]
    nodeids = {
        str(report["nodeid"])
        for report in test_reports
        if report["phase"] == "call"
    }
    assert any(nodeid.endswith("::test_worker_one") for nodeid in nodeids)
    assert any(nodeid.endswith("::test_worker_two") for nodeid in nodeids)
    worker_ids = {
        str(report["worker_id"])
        for report in test_reports
        if report["phase"] == "call"
    }
    assert worker_ids
    assert all(re.fullmatch(r"gw[0-9]+", worker) for worker in worker_ids)


def test_atomic_final_write_failure_is_nonzero_and_retains_incomplete(
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
        conftest_suffix="""
            from _pytest_plugins import artifacts as _phase8_artifacts


            _phase7_original_atomic_write_bytes = (
                _phase8_artifacts._atomic_write_bytes
            )

            def _phase7_atomic_write_bytes(path, data):
                if path.name == "run.json":
                    raise OSError("phase7 injected final-write failure")
                return _phase7_original_atomic_write_bytes(path, data)


            _phase8_artifacts._atomic_write_bytes = (
                _phase7_atomic_write_bytes
            )
        """,
    )
    result = _run(
        pytester,
        monkeypatch,
        root,
        config,
        "-q",
        run_id="atomic_failure",
    )
    output = _output(result)
    assert result.ret == pytest.ExitCode.TESTS_FAILED, output
    assert "phase7 injected final-write failure" in output
    assert "INCOMPLETE receipt retained" in output

    run_dir = _artifact_root(root) / "atomic_failure"
    assert (run_dir / "INCOMPLETE").is_file()
    assert not (run_dir / "COMPLETE").exists()
    assert not (run_dir / "run.json").exists()
    assert not any(path.name.endswith(".tmp") for path in run_dir.rglob("*"))


def test_total_run_size_limit_fails_closed(
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
        conftest_suffix="""
            from _pytest_plugins import artifacts as _phase8_artifacts


            _phase8_artifacts._MAX_ARTIFACT_RUN_BYTES = 256
        """,
    )
    result = _run(
        pytester,
        monkeypatch,
        root,
        config,
        "-q",
        run_id="total_limit",
    )
    output = _output(result)
    assert result.ret == pytest.ExitCode.TESTS_FAILED, output
    assert re.search(
        r"(?:total run limit|receipt exceeds.*limit)",
        output,
        re.IGNORECASE | re.DOTALL,
    ), output

    run_dir = _artifact_root(root) / "total_limit"
    assert (run_dir / "INCOMPLETE").is_file()
    assert not (run_dir / "COMPLETE").exists()
    assert not (run_dir / "run.json").exists()
    assert not any(path.name.endswith(".tmp") for path in run_dir.rglob("*"))


def test_per_record_limit_is_explicitly_truncated_and_still_complete(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, config = _make_project(
        pytester,
        {
            "unit/test_large_failure.py": """
                def test_large_failure():
                    raise AssertionError("Z" * 8192)
            """,
        },
        conftest_suffix="""
            from _pytest_plugins import artifacts as _phase8_artifacts


            _phase8_artifacts._MAX_ARTIFACT_RECORD_BYTES = 1024
        """,
    )
    result = _run(
        pytester,
        monkeypatch,
        root,
        config,
        "-q",
        run_id="record_limit",
    )
    assert result.ret == pytest.ExitCode.TESTS_FAILED, _output(result)
    run_dir = _artifact_root(root) / "record_limit"
    _assert_complete_receipt(run_dir, run_id="record_limit")

    reports = _load_reports(run_dir)
    call_report = next(
        report
        for report in reports
        if report["kind"] == "test"
        and report["phase"] == "call"
        and str(report["nodeid"]).endswith("::test_large_failure")
    )
    assert call_report["outcome"] == "failed"
    truncation = call_report["truncation"]
    assert isinstance(truncation, dict)
    assert truncation["applied"] is True
    assert truncation["limit_bytes"] == 1024
    assert isinstance(truncation["original_bytes"], int)
    assert truncation["original_bytes"] > 1024
    assert call_report["longrepr"] == (
        "[TRUNCATED: per-record artifact limit]"
    )
    assert len(
        json.dumps(
            call_report,
            allow_nan=False,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ) <= 1024


def test_xdist_worker_crash_is_receipted_by_the_controller(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, config = _make_project(
        pytester,
        {
            "unit/test_worker_crash.py": """
                import os
                import pytest

                pytestmark = pytest.mark.parallel(reason="read_only")

                def test_worker_crashes():
                    os._exit(7)

                def test_other_worker_can_report():
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
        "--max-worker-restart=0",
        "-m",
        "parallel",
        "-q",
        run_id="worker_crash",
    )
    assert result.ret != pytest.ExitCode.OK, _output(result)
    runs = _artifact_runs(root)
    assert runs == [_artifact_root(root) / "worker_crash"]
    run_dir = runs[0]
    _assert_complete_receipt(run_dir, run_id="worker_crash")
    collection = _load_json(run_dir / "collection.json")
    assert isinstance(collection, dict)
    assert any(
        "terminated before evidence reconciliation" in error
        for error in collection["evidence_errors"]
    )
    assert not any(
        path.is_dir() and path.name.startswith("worker_")
        for path in run_dir.rglob("*")
    )

    reports = _load_reports(run_dir)
    crashes = [
        report
        for report in reports
        if report["kind"] == "xdist_crash"
        and report["phase"] == "crash"
        and report["outcome"] == "failed"
    ]
    assert len(crashes) == 1
    failures = _load_json(run_dir / "failures.json")
    assert isinstance(failures, dict)
    assert failures["worker_crash_report_sequences"] == [
        crashes[0]["sequence"]
    ]
    rerun = _load_json(run_dir / "rerun-nodeids.json")
    assert isinstance(rerun, dict)
    assert rerun["nodeids"] == [
        "tests/unit/test_worker_crash.py::test_worker_crashes"
    ]
    run_receipt = _load_json(run_dir / "run.json")
    assert isinstance(run_receipt, dict)
    shutdown = run_receipt["xdist"]["worker_shutdown"]
    assert isinstance(shutdown, list)
    assert any(
        worker["error"] is not None and worker["finalized"] is False
        for worker in shutdown
    )


def test_obsolete_coverage_options_are_rejected_but_pytest_cov_succeeds(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, config = _make_project(
        pytester,
        {
            "unit/test_cov_target.py": """
                def covered_value():
                    return 42

                def test_covered_value():
                    assert covered_value() == 42
            """,
        },
    )
    obsolete = _run(
        pytester,
        monkeypatch,
        root,
        config,
        "--moira-cover-source=unit",
        "-q",
        run_id="obsolete_coverage",
    )
    obsolete_output = _output(obsolete)
    assert obsolete.ret != pytest.ExitCode.OK, obsolete_output
    assert re.search(
        r"unrecognized arguments?.*--moira-cover-source",
        obsolete_output,
        re.IGNORECASE | re.DOTALL,
    ), obsolete_output
    assert not (_artifact_root(root) / "obsolete_coverage").exists()

    covered = _run(
        pytester,
        monkeypatch,
        root,
        config,
        "--cov=.",
        "--cov-report=term",
        "-q",
        run_id="pytest_cov",
    )
    covered_output = _output(covered)
    assert covered.ret == pytest.ExitCode.OK, covered_output
    assert "TOTAL" in covered_output
    assert "test_cov_target.py" in covered_output
    _assert_complete_receipt(
        _artifact_root(root) / "pytest_cov",
        run_id="pytest_cov",
    )


def test_explicit_coverage_data_file_identity_is_sealed_after_pytest_cov(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, config = _make_project(
        pytester,
        {
            "unit/test_coverage_identity.py": """
                def covered_value():
                    return 42


                def test_covered_value():
                    assert covered_value() == 42
            """,
        },
    )
    coverage_file = root / ".coverage-phase9-artifact-canary"
    result = _run(
        pytester,
        monkeypatch,
        root,
        config,
        "--cov=.",
        "--cov-config=pytest.ini",
        "--cov-report=",
        "-q",
        run_id="coverage_identity",
        coverage_file=str(coverage_file),
        coverage_core="ctrace",
    )
    assert result.ret == pytest.ExitCode.OK, _output(result)
    run_dir = _artifact_root(root) / "coverage_identity"
    _assert_complete_receipt(run_dir, run_id="coverage_identity")

    receipt = _load_json(run_dir / "run.json")
    assert isinstance(receipt, dict)
    assert receipt["coverage"]["runtime"]["controller"].pop(
        "assurance_runtime"
    ) == receipt["assurance_runtime"]
    assert receipt["coverage"]["runtime"]["controller"].pop(
        "run_context"
    ) == {
        field: receipt[field]
        for field in (
            "assurance_runtime",
            "repository",
            "interpreter",
            "native",
            "execution_switches",
        )
    }
    assert receipt["coverage"]["runtime"]["controller"].pop(
        "final_run_context"
    ) == {
        field: receipt[field]
        for field in (
            "assurance_runtime",
            "repository",
            "interpreter",
            "native",
            "execution_switches",
        )
    }
    assert receipt["coverage"] == {
        "data_file": {
            "path": coverage_file.relative_to(root).as_posix(),
            "path_policy": "repository_relative",
            "resolved_path": str(coverage_file.resolve(strict=True)),
            "bytes": coverage_file.stat().st_size,
            "sha256": _sha256(coverage_file),
            "mtime_ns": coverage_file.stat().st_mtime_ns,
        },
        "core": {
            "environment": "ctrace",
            "policy": "explicit_environment",
            "is_ctrace": True,
        },
        "pytest_cov": {
            "append": False,
            "branch": None,
            "config": "pytest.ini",
            "context": None,
            "no_cov": False,
            "source": ["."],
        },
        "runtime": {
            "controller": {
                "active": True,
                "actual_core": "CTracer",
                "config_files": [
                    {
                        "bytes": config.stat().st_size,
                        "path": "pytest.ini",
                        "path_policy": "repository_relative",
                        "resolved_path": str(config.resolve(strict=True)),
                        "sha256": _sha256(config),
                    }
                ],
                "controller": "pytest_cov.engine.Central",
                "coverage_data_file": str(coverage_file.resolve(strict=True)),
                "effective_config": {
                    "branch": False,
                    "concurrency": [],
                    "core": "ctrace",
                    "dynamic_context": None,
                    "parallel": True,
                    "plugins": [],
                    "relative_files": False,
                    "source": ["."],
                    "static_context": None,
                    "timid": False,
                },
                "environment": {
                    "COVERAGE_CORE": "ctrace",
                    "COVERAGE_FILE": str(coverage_file.resolve(strict=True)),
                    "COVERAGE_FORCE_CONFIG": None,
                    "COVERAGE_PROCESS_CONFIG": None,
                    "COVERAGE_PROCESS_START": None,
                    "COVERAGE_RCFILE": None,
                },
            },
            "workers": {},
        },
    }


def test_missing_explicit_coverage_data_file_refuses_complete_receipt(
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
    )
    coverage_file = root / ".coverage-does-not-exist"
    result = _run(
        pytester,
        monkeypatch,
        root,
        config,
        "-q",
        run_id="missing_coverage",
        coverage_file=str(coverage_file),
        coverage_core="ctrace",
    )
    output = _output(result)
    assert result.ret == pytest.ExitCode.TESTS_FAILED, output
    assert "coverage data file requested by COVERAGE_FILE" in output
    incomplete = _assert_incomplete_receipt(
        _artifact_root(root) / "missing_coverage",
        run_id="missing_coverage",
    )
    assert any(
        "coverage data file requested by COVERAGE_FILE" in str(error)
        for error in incomplete["finalization_errors"]
    )


def test_evidence_redaction_refuses_stale_contract_hashes(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evidence_secret = "phase9-evidence-secret-41f8"
    monkeypatch.setenv("MOIRA_PHASE9_EVIDENCE_SECRET", evidence_secret)
    root, config = _make_project(
        pytester,
        {
            "evidence/__init__.py": "",
            "evidence/contracts.py": """
                from dataclasses import replace
                import os

                from _pytest_plugins.evidence_schema import (
                    freeze_registry,
                    synthetic_registry,
                )


                _BASE = next(iter(synthetic_registry().values()))
                CONTRACTS = freeze_registry(
                    (
                        replace(
                            _BASE,
                            product_surface=os.environ[
                                "MOIRA_PHASE9_EVIDENCE_SECRET"
                            ],
                        ),
                    )
                )
            """,
            "unit/test_probe.py": """
                import pytest


                @pytest.mark.validation_contract("MOIRA-TEST-CLAIM-V1")
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
        "-q",
        run_id="evidence_redaction",
    )
    output = _output(result)
    assert result.ret == pytest.ExitCode.TESTS_FAILED, output
    assert "artifact redaction would mutate sealed validation evidence" in output
    run_dir = _artifact_root(root) / "evidence_redaction"
    incomplete = _assert_incomplete_receipt(
        run_dir,
        run_id="evidence_redaction",
    )
    assert evidence_secret.encode("utf-8") not in b"".join(
        path.read_bytes() for path in run_dir.iterdir() if path.is_file()
    )
    assert any(
        "artifact redaction would mutate sealed validation evidence"
        in str(error)
        for error in incomplete["finalization_errors"]
    )


@pytest.mark.parametrize(
    "property_name",
    (
        "moira_validation_claim_id",
        "moira_validation_contract_sha256",
    ),
)
def test_duplicate_validation_identity_property_refuses_complete_receipt(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
    property_name: str,
) -> None:
    root, config = _make_project(
        pytester,
        {
            "unit/test_duplicate_identity.py": f"""
                def test_duplicate_identity(request):
                    request.node.user_properties.extend(
                        [
                            ({property_name!r}, "first"),
                            ({property_name!r}, "second"),
                        ]
                    )
            """,
        },
    )
    run_id = "duplicate_" + property_name.removeprefix("moira_validation_")
    result = _run(
        pytester,
        monkeypatch,
        root,
        config,
        "-q",
        run_id=run_id,
    )
    output = _output(result)
    assert result.ret == pytest.ExitCode.TESTS_FAILED, output
    assert f"repeats the {property_name} user property" in output
    incomplete = _assert_incomplete_receipt(
        _artifact_root(root) / run_id,
        run_id=run_id,
    )
    assert any(
        f"repeats the {property_name} user property" in str(error)
        for error in incomplete["finalization_errors"]
    )
