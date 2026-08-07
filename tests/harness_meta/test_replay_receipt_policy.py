"""Adversarial contracts for replaying completed pytest receipts as data."""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import platform
from types import SimpleNamespace
from typing import Any

import pytest

from scripts import replay_test_receipt as replay


pytestmark = pytest.mark.parallel(reason="isolated_resources")

_SIDECAR_NAMES = (
    "collection.json",
    "resources.json",
    "reports.jsonl",
    "failures.json",
    "durations.json",
    "rerun-nodeids.json",
)
_DEFAULT_NODEID = "tests/unit/test_replay_canary.py::test_replay_canary"


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def _binding(raw: bytes) -> dict[str, object]:
    return {
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _identity_bundle(root: Path) -> dict[str, object]:
    root = root.resolve(strict=False)
    executable = root / ".venv" / "Scripts" / "python.exe"
    return {
        "repository": {
            "root": str(root),
            "git": {
                "available": True,
                "repository_root": str(root),
                "head": "a" * 40,
                "tracked_diff_sha256": "b" * 64,
                "untracked_content_sha256": "c" * 64,
                "untracked_count": 0,
            },
        },
        "interpreter": {
            "executable": str(executable),
            "prefix": str(root / ".venv"),
            "implementation": platform.python_implementation(),
            "version": platform.python_version(),
            "project_venv_executable": str(executable),
            "is_project_venv": True,
        },
        "native": {
            "available": True,
            "moira_version": "phase7-test",
            "package_path": str(root / "moira" / "__init__.py"),
            "package_under_repository": True,
            "backend_path": str(root / "moira" / "_phase7_native.pyd"),
            "backend_under_repository": True,
            "backend_size": 4096,
            "backend_sha256": "d" * 64,
        },
    }


def _empty_resources() -> dict[str, object]:
    return {
        "schema_version": 1,
        "planetary": {
            "version": 1,
            "summary": {
                "receipts": 0,
                "run": 0,
                "skip": 0,
                "failure": 0,
                "identities": [],
            },
            "details": {},
            "probe_count": 0,
        },
        "small_body": {
            "version": 1,
            "summary": {
                "receipts": 0,
                "run": 0,
                "skip": 0,
                "failure": 0,
                "terminal": 0,
                "identities": [],
                "manifests": 0,
                "shards": 0,
                "bodies": 0,
            },
            "details": {},
        },
    }


def _sidecar_bytes(nodeids: list[str]) -> dict[str, bytes]:
    return {
        "collection.json": _json_bytes(
            {
                "schema_version": 1,
                "classification": None,
                "classification_errors": [],
                "collection_error_report_sequences": [],
            }
        ),
        "resources.json": _json_bytes(_empty_resources()),
        "reports.jsonl": b"",
        "failures.json": _json_bytes(
            {
                "schema_version": 1,
                "failure_report_sequences": [],
                "failed_cases": [],
                "collection_failure_report_sequences": [],
                "worker_crash_report_sequences": [],
                "budget_violations": [],
                "flakes": [],
            }
        ),
        "durations.json": _json_bytes(
            {"schema_version": 1, "cases": []}
        ),
        "rerun-nodeids.json": _json_bytes(
            {"schema_version": 1, "nodeids": nodeids}
        ),
    }


def _seal_receipt(
    run_dir: Path,
    run_document: dict[str, object],
) -> None:
    artifacts = {
        name: _binding((run_dir / name).read_bytes())
        for name in _SIDECAR_NAMES
    }
    run_document["artifacts"] = artifacts
    run_raw = _json_bytes(run_document)
    (run_dir / "run.json").write_bytes(run_raw)
    complete = {
        "schema_version": 1,
        "run_id": run_document["run_id"],
        "status": "complete",
        "run_json": _binding(run_raw),
    }
    (run_dir / "COMPLETE").write_bytes(_json_bytes(complete))


def _write_receipt(
    tmp_path: Path,
    *,
    recorded_root: Path | None = None,
    nodeids: list[str] | None = None,
) -> tuple[Path, dict[str, object]]:
    run_dir = tmp_path / "receipt"
    run_dir.mkdir()
    for name, raw in _sidecar_bytes(
        list(nodeids) if nodeids is not None else [_DEFAULT_NODEID]
    ).items():
        (run_dir / name).write_bytes(raw)

    identities = _identity_bundle(
        recorded_root or replay.REPOSITORY_ROOT
    )
    execution_switches = {
        name: False
        for name in replay._EXECUTION_SWITCH_NAMES
    }
    run_document: dict[str, object] = {
        "schema_version": 1,
        "run_id": "phase7-replay-test",
        **identities,
        "execution_switches": execution_switches,
        "final_context": {
            **deepcopy(identities),
            "execution_switches": deepcopy(execution_switches),
        },
        "invocation": {
            "arguments": ["tests"],
            "arguments_are_evidence_only": True,
            "redacted": False,
        },
        "policy": {"seed": 731},
        "timing": {
            "started_utc": "2026-07-30T00:00:00+00:00",
            "finished_utc": "2026-07-30T00:00:01+00:00",
            "elapsed_monotonic_s": 1.0,
            "clock": "time.perf_counter",
        },
        "pytest": {
            "exitstatus": {"code": 1, "name": "TESTS_FAILED"},
            "total_budget": {
                "clock": "time.perf_counter",
                "elapsed_s": 1.0,
                "budget_s": 0.0,
                "exceeded": False,
            },
        },
        "xdist": {"mode": "local", "worker_shutdown": []},
    }
    _seal_receipt(run_dir, run_document)
    return run_dir / "run.json", run_document


def _mutate_same_length(path: Path, before: bytes, after: bytes) -> None:
    assert len(before) == len(after)
    raw = path.read_bytes()
    assert before in raw
    path.write_bytes(raw.replace(before, after, 1))


def _current_identities() -> dict[str, object]:
    return _identity_bundle(replay.REPOSITORY_ROOT)


def _patch_matching_preflight(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in replay._EXECUTION_SWITCH_NAMES:
        monkeypatch.delenv(name, raising=False)
    current = _current_identities()
    monkeypatch.setattr(
        replay,
        "_verify_current_interpreter",
        lambda root: Path(current["interpreter"]["executable"]),
    )
    monkeypatch.setattr(replay, "_verify_git_root", lambda root: None)
    monkeypatch.setattr(
        replay,
        "_ensure_repository_import_path",
        lambda root: None,
    )
    monkeypatch.setattr(
        replay,
        "_current_git_identity",
        lambda root: deepcopy(current["repository"]["git"]),
    )
    monkeypatch.setattr(
        replay,
        "_current_interpreter_identity",
        lambda root: deepcopy(current["interpreter"]),
    )
    monkeypatch.setattr(
        replay,
        "_current_native_identity",
        lambda root: deepcopy(current["native"]),
    )
    monkeypatch.setattr(
        replay,
        "_compare_resources",
        lambda resources, *, recorded_root, current_root: [],
    )


def _args(
    run_path: Path,
    *,
    allow_repository_mismatch: bool = False,
    allow_state_mismatch: bool = False,
    check_only: bool = False,
) -> argparse.Namespace:
    return argparse.Namespace(
        run_json=run_path,
        allow_repository_mismatch=allow_repository_mismatch,
        allow_state_mismatch=allow_state_mismatch,
        check_only=check_only,
    )


@pytest.mark.parametrize(
    "target",
    (
        "COMPLETE",
        "run.json",
        "collection.json",
        "resources.json",
        "reports.jsonl",
        "failures.json",
        "durations.json",
        "rerun-nodeids.json",
    ),
)
def test_every_v1_binding_rejects_same_length_tampering(
    tmp_path: Path,
    target: str,
) -> None:
    run_path, _ = _write_receipt(tmp_path)
    path = run_path.parent / target
    if target == "COMPLETE":
        complete = json.loads(path.read_text(encoding="utf-8"))
        digest = complete["run_json"]["sha256"]
        complete["run_json"]["sha256"] = (
            ("0" if digest[0] != "0" else "1") + digest[1:]
        )
        path.write_bytes(_json_bytes(complete))
    elif target == "run.json":
        _mutate_same_length(path, b'"seed":731', b'"seed":732')
    elif target == "reports.jsonl":
        path.write_bytes(b"x")
    else:
        _mutate_same_length(
            path,
            b'"schema_version":1',
            b'"schema_version":2',
        )

    with pytest.raises(
        replay.ReplayContractError,
        match=r"(?:SHA-256|byte length|binding|manifest)",
    ):
        replay._load_receipt_set(run_path)


def test_complete_requires_exact_completed_state_and_run_identity(
    tmp_path: Path,
) -> None:
    run_path, _ = _write_receipt(tmp_path)
    complete_path = run_path.parent / "COMPLETE"
    complete = json.loads(complete_path.read_text(encoding="utf-8"))

    for field, replacement in (
        ("status", "incomplete"),
        ("run_id", "different-run"),
    ):
        altered = deepcopy(complete)
        altered[field] = replacement
        complete_path.write_bytes(_json_bytes(altered))
        with pytest.raises(
            replay.ReplayContractError,
            match=r"(?:COMPLETE|status|run_id|identity)",
        ):
            replay._load_receipt_set(run_path)


@pytest.mark.parametrize(
    ("raw", "diagnostic"),
    (
        (
            b'{"schema_version":1,"schema_version":1,'
            b'"planetary":{},"small_body":{}}\n',
            "duplicate",
        ),
        (
            b'{"schema_version":1,"planetary":{},'
            b'"small_body":{},"poison":NaN}\n',
            "non-finite",
        ),
    ),
)
def test_bound_json_rejects_duplicate_keys_and_nonfinite_values(
    tmp_path: Path,
    raw: bytes,
    diagnostic: str,
) -> None:
    run_path, run_document = _write_receipt(tmp_path)
    (run_path.parent / "resources.json").write_bytes(raw)
    _seal_receipt(run_path.parent, run_document)

    with pytest.raises(replay.ReplayContractError, match=diagnostic):
        replay._load_receipt_set(run_path)


def test_bound_json_rejects_oversize_input_before_parsing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_path, _ = _write_receipt(tmp_path)
    resource_size = (run_path.parent / "resources.json").stat().st_size
    monkeypatch.setattr(
        replay,
        "_MAX_RESOURCES_JSON_BYTES",
        resource_size - 1,
    )

    with pytest.raises(replay.ReplayContractError, match="exceeds"):
        replay._load_receipt_set(run_path)


def test_bound_sidecar_symlink_substitution_is_rejected(
    tmp_path: Path,
) -> None:
    run_path, _ = _write_receipt(tmp_path)
    sidecar = run_path.parent / "resources.json"
    real_sidecar = tmp_path / "real-resources.json"
    sidecar.replace(real_sidecar)
    try:
        sidecar.symlink_to(real_sidecar)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"symlink creation is unavailable: {exc}")

    with pytest.raises(
        replay.ReplayContractError,
        match=r"(?:symlink|reparse|regular file)",
    ):
        replay._load_receipt_set(run_path)


def test_wrong_repository_is_blocked_until_explicitly_acknowledged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    wrong_root = tmp_path / "another-checkout"
    run_path, _ = _write_receipt(
        tmp_path,
        recorded_root=wrong_root,
    )
    _patch_matching_preflight(monkeypatch)

    refused = replay._main(_args(run_path, check_only=True))
    assert refused == 3
    refused_output = capsys.readouterr()
    assert "Repository: MISMATCH" in refused_output.out
    assert "allow-repository-mismatch" in refused_output.err

    allowed = replay._main(
        _args(
            run_path,
            allow_repository_mismatch=True,
            check_only=True,
        )
    )
    assert allowed == 0
    allowed_output = capsys.readouterr()
    assert "check-only" in allowed_output.out


def test_wrong_project_interpreter_is_rejected_before_receipt_use(
    tmp_path: Path,
) -> None:
    fake_python = tmp_path / ".venv" / "Scripts" / "python.exe"
    fake_python.parent.mkdir(parents=True)
    fake_python.write_bytes(b"not-the-running-interpreter")

    with pytest.raises(
        replay.ReplayContractError,
        match=r"(?:project|repository).*\.venv interpreter",
    ):
        replay._verify_current_interpreter(tmp_path)


def test_all_state_mismatches_are_diagnosed_before_pytest_launch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    run_path, _ = _write_receipt(tmp_path)
    _patch_matching_preflight(monkeypatch)
    current = _current_identities()

    changed_git = deepcopy(current["repository"]["git"])
    changed_git["head"] = "e" * 40
    changed_interpreter = deepcopy(current["interpreter"])
    changed_interpreter["version"] = "0.0-phase7"
    changed_native = deepcopy(current["native"])
    changed_native["backend_sha256"] = "f" * 64
    monkeypatch.setattr(
        replay,
        "_current_git_identity",
        lambda root: changed_git,
    )
    monkeypatch.setattr(
        replay,
        "_current_interpreter_identity",
        lambda root: changed_interpreter,
    )
    monkeypatch.setattr(
        replay,
        "_current_native_identity",
        lambda root: changed_native,
    )
    monkeypatch.setattr(
        replay,
        "_compare_resources",
        lambda resources, *, recorded_root, current_root: [
            "resource identity changed"
        ],
    )

    def forbidden_launch(*args: Any, **kwargs: Any) -> int:
        raise AssertionError("pytest launched before mismatch admission")

    monkeypatch.setattr(replay, "_run_replay", forbidden_launch)
    result = replay._main(_args(run_path))
    output = capsys.readouterr()

    assert result == 3
    for label in ("Interpreter", "Git", "Native", "Resources"):
        assert f"{label}: MISMATCH" in output.out
    assert "allow-state-mismatch" in output.err


def test_resource_state_is_resealed_immediately_before_launch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_path, _ = _write_receipt(tmp_path)
    _patch_matching_preflight(monkeypatch)
    comparisons = iter(([], ["planetary content changed"]))
    monkeypatch.setattr(
        replay,
        "_compare_resources",
        lambda resources, *, recorded_root, current_root: next(
            comparisons
        ),
    )

    def forbidden_launch(*args: Any, **kwargs: Any) -> int:
        raise AssertionError("pytest launched after resource drift")

    monkeypatch.setattr(replay, "_run_replay", forbidden_launch)
    with pytest.raises(
        replay.ReplayContractError,
        match=r"state changed.*resources",
    ):
        replay._main(_args(run_path))


@pytest.mark.parametrize(
    "nodeid",
    (
        "-k",
        "../tests/unit/test_probe.py::test_probe",
        "/tests/unit/test_probe.py::test_probe",
        r"tests\unit\test_probe.py::test_probe",
        "tests/../unit/test_probe.py::test_probe",
        "tests/unit/not-a-python-test.txt::test_probe",
        "tests//unit/test_probe.py::test_probe",
        "tests/unit/test_probe.py\n::test_probe",
    ),
)
def test_hostile_or_noncanonical_nodeids_are_rejected(
    nodeid: str,
) -> None:
    with pytest.raises(replay.ReplayContractError):
        replay._validate_nodeids([nodeid])


def test_hostile_parameter_text_is_one_data_argument_and_never_shell_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hostile = (
        "tests/unit/test_probe.py::test_probe"
        "[value; $(whoami); `touch phase7-owned`; --maxfail=1]"
    )
    assert replay._validate_nodeids([hostile]) == (hostile,)
    captured: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs: object) -> object:
        captured["command"] = command
        captured.update(kwargs)
        return SimpleNamespace(returncode=17)

    monkeypatch.setattr(replay.subprocess, "run", fake_run)
    result = replay._run_replay(
        Path(os.sys.executable),
        (hostile,),
        seed=991,
        execution_switches={
            name: False
            for name in replay._EXECUTION_SWITCH_NAMES
        },
    )

    assert result == 17
    assert captured["command"] == [
        os.sys.executable,
        "-m",
        "pytest",
        "--",
        hostile,
    ]
    assert captured["cwd"] == replay.REPOSITORY_ROOT
    assert captured["shell"] is False
    assert captured["check"] is False


def test_planetary_content_digest_detects_same_metadata_mutation(
    tmp_path: Path,
) -> None:
    kernel = tmp_path / "phase7-kernel.bsp"
    kernel.write_bytes(b"original-coefficients")
    metadata = kernel.stat()
    has_file_identity = (
        type(metadata.st_ino) is int
        and metadata.st_ino > 0
        and type(metadata.st_dev) is int
        and metadata.st_dev >= 0
    )
    fingerprint = SimpleNamespace(
        resolved_path=kernel.resolve(strict=True),
        size=metadata.st_size,
        mtime_ns=metadata.st_mtime_ns,
        device_id=metadata.st_dev if has_file_identity else None,
        file_id=metadata.st_ino if has_file_identity else None,
    )
    candidate = SimpleNamespace(
        path=kernel,
        explicit=True,
        source="phase7-test",
        fingerprint=fingerprint,
    )
    recorded = replay._serialize_current_candidate(
        candidate,
        repository_root=tmp_path,
        content_digests={},
    )
    assert recorded is not None
    recorded_signature = replay._candidate_signature(
        recorded,
        repository_root=str(tmp_path),
    )

    kernel.write_bytes(b"mutated--coefficients")
    os.utime(
        kernel,
        ns=(metadata.st_atime_ns, metadata.st_mtime_ns),
    )
    current_metadata = kernel.stat()
    assert current_metadata.st_size == metadata.st_size
    assert current_metadata.st_mtime_ns == metadata.st_mtime_ns
    current = replay._serialize_current_candidate(
        candidate,
        repository_root=tmp_path,
        content_digests={},
    )
    assert current is not None
    current_signature = replay._candidate_signature(
        current,
        repository_root=str(tmp_path),
    )

    assert (
        recorded["fingerprint"]["content_sha256"]
        != current["fingerprint"]["content_sha256"]
    )
    assert recorded_signature != current_signature


def test_planetary_fingerprint_without_content_digest_is_rejected(
    tmp_path: Path,
) -> None:
    kernel = tmp_path / "phase7-kernel.bsp"
    kernel.write_bytes(b"content")
    metadata = kernel.stat()
    has_file_identity = (
        type(metadata.st_ino) is int
        and metadata.st_ino > 0
        and type(metadata.st_dev) is int
        and metadata.st_dev >= 0
    )
    candidate = {
        "path": str(kernel),
        "explicit": True,
        "source": "phase7-test",
        "fingerprint": {
            "resolved_path": str(kernel.resolve(strict=True)),
            "size": metadata.st_size,
            "mtime_ns": metadata.st_mtime_ns,
            "device_id": (
                metadata.st_dev if has_file_identity else None
            ),
            "file_id": (
                metadata.st_ino if has_file_identity else None
            ),
        },
    }
    with pytest.raises(
        replay.ReplayContractError,
        match="fingerprint.*field set",
    ):
        replay._candidate_signature(
            candidate,
            repository_root=str(tmp_path),
        )


def test_replay_environment_discards_ambient_execution_control(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hostile_environment = {
        "PYTEST_ADDOPTS": "--collect-only -p attacker",
        "PYTEST_PLUGINS": "attacker",
        "PYTEST_XDIST_WORKER": "gw99",
        "PYTEST_XDIST_WORKER_COUNT": "99",
        "PYTEST_XDIST_TESTRUNUID": "attacker-run",
        "MOIRA_WORKER_ID": "gw99",
        "MOIRA_TEST_RUN_ID": "attacker-receipt",
        "MOIRA_TEST_ARTIFACTS": "1",
        "MOIRA_SNAPSHOT_UPDATE": "1",
        "MOIRA_GOLDEN_UPDATE": "1",
        "MOIRA_TEST_NETWORK_POLICY": "external",
        "MOIRA_TEST_MODE": "0",
        "MOIRA_NO_DOWNLOAD": "0",
        "MOIRA_TEST_BUDGET_CASE_S": "999",
        "MOIRA_TEST_BUDGET_TOTAL_S": "999",
        "MOIRA_ACCELERATE": "1",
        "MOIRA_FORCE_PYTHON_TYPE13": "yes",
        "MOIRA_FORCE_PYTHON_CHEBYSHEV": "true",
    }
    for name, value in hostile_environment.items():
        monkeypatch.setenv(name, value)

    execution_switches = {
        name: False
        for name in replay._EXECUTION_SWITCH_NAMES
    }
    environment = replay._sanitized_environment(
        8128,
        execution_switches,
    )

    for name in (
        "PYTEST_ADDOPTS",
        "PYTEST_PLUGINS",
        "PYTEST_XDIST_WORKER",
        "PYTEST_XDIST_WORKER_COUNT",
        "PYTEST_XDIST_TESTRUNUID",
        "MOIRA_WORKER_ID",
        "MOIRA_TEST_RUN_ID",
    ):
        assert name not in environment
    assert environment["MOIRA_TEST_SEED"] == "8128"
    for name, value in replay._REPLAY_ENVIRONMENT_SET.items():
        assert environment[name] == value
    for name in replay._EXECUTION_SWITCH_NAMES:
        assert environment[name] == "0"


def test_recorded_invocation_and_environment_are_ignored(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    nodeid = "tests/unit/test_probe.py::test_exact_recorded_failure"
    run_path, run_document = _write_receipt(
        tmp_path,
        nodeids=[nodeid],
    )
    run_document["invocation"] = {
        "arguments": [
            "--collect-only",
            "-p",
            "attacker",
            "tests/unit/test_other.py",
        ],
        "arguments_are_evidence_only": True,
        "redacted": False,
    }
    run_document["environment"] = {
        "PYTEST_ADDOPTS": "--collect-only -p attacker",
        "MOIRA_TEST_NETWORK_POLICY": "external",
    }
    _seal_receipt(run_path.parent, run_document)
    _patch_matching_preflight(monkeypatch)
    launched: dict[str, object] = {}

    def capture_replay(
        python: Path,
        nodeids: tuple[str, ...],
        *,
        seed: int,
        execution_switches: dict[str, bool],
    ) -> int:
        launched.update(
            python=python,
            nodeids=nodeids,
            seed=seed,
            execution_switches=execution_switches,
        )
        return 23

    monkeypatch.setattr(replay, "_run_replay", capture_replay)
    result = replay._main(_args(run_path))

    assert result == 23
    assert launched["nodeids"] == (nodeid,)
    assert launched["seed"] == 731
    assert launched["execution_switches"] == {
        name: False
        for name in replay._EXECUTION_SWITCH_NAMES
    }
    assert "--collect-only" not in launched["nodeids"]
    assert "attacker" not in launched["nodeids"]


@pytest.mark.parametrize("mutation", ("missing", "changed"))
def test_recorded_execution_switch_contract_is_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    run_path, run_document = _write_receipt(tmp_path)
    if mutation == "missing":
        run_document.pop("execution_switches")
    else:
        run_document["final_context"]["execution_switches"][
            "MOIRA_ACCELERATE"
        ] = True
    _seal_receipt(run_path.parent, run_document)
    _patch_matching_preflight(monkeypatch)

    with pytest.raises(
        replay.ReplayContractError,
        match=r"execution switches|execution_switches",
    ):
        replay._main(_args(run_path, check_only=True))


def test_check_only_never_launches_pytest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    run_path, _ = _write_receipt(tmp_path)
    _patch_matching_preflight(monkeypatch)

    def forbidden_launch(*args: Any, **kwargs: Any) -> int:
        raise AssertionError("check-only launched pytest")

    monkeypatch.setattr(replay, "_run_replay", forbidden_launch)
    result = replay._main(_args(run_path, check_only=True))
    output = capsys.readouterr()

    assert result == 0
    assert "check-only" in output.out
