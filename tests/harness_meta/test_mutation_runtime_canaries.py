"""Runtime canaries for Phase 11 child containment and reporter integration."""

from __future__ import annotations

import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest

import support.mutation_assurance as mutation_assurance
from _pytest_plugins.evidence_schema import (
    canonical_python_ast_sha256,
    contract_sha256,
)
from evidence.contracts import CONTRACTS
from support.mutation_assurance import (
    FailureExpectation,
    MutantSpec,
    SOURCE_HASH_MODE,
    adjudicate_baseline,
    apply_exact_mutation,
    canonical_source_bytes,
    child_argv,
    child_environment,
    execute_child,
    python_source_code_sha256,
    sha256_bytes,
)
pytestmark = pytest.mark.parallel(reason="isolated_resources")


_ROOT = Path(__file__).resolve().parents[2]
_CLAIM_ID = "MOIRA-COORD-LONGITUDE-QUOTIENT-V1"
_NODEID = "tests/test_probe.py::test_declared_relation"
_OUTPUT_LIMIT_BYTES = 128 * 1024
_PROCESS_EXIT_POLL_SECONDS = 0.05


def test_child_environment_scrubs_pytest_plugin_injection(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("PYTEST_ADDOPTS", "-p hostile_plugin --collect-only")
    monkeypatch.setenv("PYTEST_PLUGINS", "hostile_plugin")
    monkeypatch.setenv("pYtEsT_aDdOpTs", "-p mixed_case_hostile")
    monkeypatch.setenv("PyTeSt_PlUgInS", "mixed_case_hostile")

    environment = child_environment(tmp_path, seed=11012)

    blocked = {"pytest_addopts", "pytest_plugins"}
    assert blocked.isdisjoint(name.casefold() for name in environment)
    assert environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] == "1"


def test_child_argv_disables_cache_before_loading_mutation_reporter(
    tmp_path: Path,
) -> None:
    spec = SimpleNamespace(
        intended_killer_nodeid=_NODEID,
        source_path="moira/probe.py",
        module_name="moira.probe",
        target_qualname="target",
    )

    argv = mutation_assurance._expected_child_argv(
        interpreter=sys.executable,
        control_root=tmp_path,
        spec=spec,
        execution_id="phase11-plugin-order-canary",
    )

    cache_disable = argv.index("no:cacheprovider")
    reporter = argv.index("tests.mutation_reporter")
    assert argv[cache_disable - 1] == "-p"
    assert argv[reporter - 1] == "-p"
    assert cache_disable < reporter


def _project_launcher_executable() -> str:
    """Return the exact project launcher without hashing the full runtime."""

    expected = (
        _ROOT / ".venv" / "Scripts" / "python.exe"
        if os.name == "nt"
        else _ROOT / ".venv" / "bin" / "python"
    )
    launcher, _raw = mutation_assurance._project_launcher_identity(
        expected,
        Path(sys.executable),
    )
    executable = launcher["path"]
    assert isinstance(executable, str)
    return executable


def _frozen_runner_environment() -> dict[str, str]:
    """Retain OS facilities while removing interpreter/plugin injection."""

    blocked_prefixes = (
        "COVERAGE",
        "COV_CORE",
        "HYPOTHESIS",
        "MOIRA_",
        "PYTEST",
        "PYTHON",
    )
    environment = {
        name: value
        for name, value in os.environ.items()
        if not name.upper().startswith(blocked_prefixes)
    }
    environment.update(
        {
            "MOIRA_NO_DOWNLOAD": "1",
            "MOIRA_STRICT_KNOWN_ISSUES": "1",
            "MOIRA_TEST_MODE": "1",
        }
    )
    return environment


def _standalone_parent_interpreter_identity() -> dict[str, object]:
    """Capture identity through the actual frozen stage-one runner."""

    runner = _ROOT / "scripts" / "run_scientific_mutations.py"
    completed = subprocess.run(
        [
            _project_launcher_executable(),
            os.fspath(runner),
            "--emit-interpreter-identity",
        ],
        cwd=_ROOT,
        env=_frozen_runner_environment(),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=300,
        check=False,
    )
    assert completed.returncode == 0, (
        "frozen parent identity action failed:\n"
        f"stdout:\n{completed.stdout!r}\nstderr:\n{completed.stderr!r}"
    )
    assert completed.stderr == b""
    identity = mutation_assurance.strict_json_bytes(
        completed.stdout,
        label="frozen parent interpreter identity",
    )
    assert isinstance(identity, dict)
    assert completed.stdout == mutation_assurance.canonical_json_bytes(identity)
    return identity


class _InjectedCaptureBaseException(BaseException):
    """Non-``Exception`` failure injected after the child tree exists."""


class _InjectedPopenBaseException(BaseException):
    """Failure injected after OS creation but before Popen returns to caller."""


@pytest.fixture(autouse=True)
def _isolated_parent_toolchain_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Give canary identity calls the runner's no-bytecode policy locally."""

    cache_prefix = (tmp_path / "parent-toolchain-pycache").resolve()
    monkeypatch.setattr(sys, "dont_write_bytecode", True)
    monkeypatch.setattr(sys, "pycache_prefix", str(cache_prefix))


def _write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


def _copy_repository_file(relative: str, snapshot_root: Path) -> None:
    source = _ROOT / Path(relative)
    _write(snapshot_root / Path(relative), source.read_bytes())


def _runtime_spec(source: bytes, *, ast_root: Path) -> MutantSpec:
    postimage = source.replace(b"return 41", b"return 42", 1)
    preimage_ast_path = ast_root / "preimage.py"
    postimage_ast_path = ast_root / "postimage.py"
    _write(preimage_ast_path, source)
    _write(postimage_ast_path, postimage)
    contract = CONTRACTS[_CLAIM_ID]
    return MutantSpec(
        mutant_id="P11-RUNTIME-REPORTER-CANARY",
        criticality="critical",
        fault_archetype="runtime reporter integration canary",
        operator="replace_exact_utf8_v1",
        source_path="moira/probe.py",
        target_qualname="target",
        preimage="def target():\n    return 41",
        replacement="def target():\n    return 42",
        occurrence_count=1,
        source_hash_mode=SOURCE_HASH_MODE,
        preimage_sha256=sha256_bytes(canonical_source_bytes(source)),
        postimage_sha256=sha256_bytes(canonical_source_bytes(postimage)),
        preimage_ast_sha256=canonical_python_ast_sha256(
            preimage_ast_path,
            ("target",),
        ),
        postimage_ast_sha256=canonical_python_ast_sha256(
            postimage_ast_path,
            ("target",),
        ),
        preimage_code_sha256=python_source_code_sha256(
            source,
            qualname="target",
        ),
        postimage_code_sha256=python_source_code_sha256(
            postimage,
            qualname="target",
        ),
        patch_sha256="0" * 64,
        intended_killer_nodeid=_NODEID,
        expected_claim_id=_CLAIM_ID,
        expected_contract_sha256=contract_sha256(contract),
        evidence_class=contract.evidence_class.value,
        expected_failure=FailureExpectation(
            exception_type="builtins.AssertionError",
            message_contains=(),
            longrepr_contains=(),
            metamorphic_witness=None,
        ),
        requires_native_backend=False,
        timeout_seconds=60,
        exclusions=("disposable reporter integration canary",),
    )


def _process_is_alive(pid: int) -> bool:
    if pid <= 0:
        raise ValueError("process ID must be positive")
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = (
            wintypes.DWORD,
            wintypes.BOOL,
            wintypes.DWORD,
        )
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.WaitForSingleObject.argtypes = (
            wintypes.HANDLE,
            wintypes.DWORD,
        )
        kernel32.WaitForSingleObject.restype = wintypes.DWORD
        kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
        kernel32.CloseHandle.restype = wintypes.BOOL
        handle = kernel32.OpenProcess(0x00100000, False, pid)
        if not handle:
            error = ctypes.get_last_error()
            if error in {2, 3, 87, 1168}:
                return False
            if error == 5:
                return True
            raise OSError(error, f"cannot inspect descendant PID {pid}")
        try:
            return kernel32.WaitForSingleObject(handle, 0) == 0x00000102
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    proc_stat = Path(f"/proc/{pid}/stat")
    if proc_stat.exists():
        try:
            fields = proc_stat.read_text(encoding="ascii").split()
        except OSError:
            return False
        if len(fields) > 2 and fields[2] == "Z":
            return False
    return True


def _wait_for_process_exit(pid: int, *, timeout_seconds: float) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if not _process_is_alive(pid):
            return True
        time.sleep(_PROCESS_EXIT_POLL_SECONDS)
    return not _process_is_alive(pid)


def _wait_for_processes_exit(
    pids: tuple[int, ...],
    *,
    timeout_seconds: float,
) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if all(not _process_is_alive(pid) for pid in pids):
            return True
        time.sleep(_PROCESS_EXIT_POLL_SECONDS)
    return all(not _process_is_alive(pid) for pid in pids)


def _force_terminate_process(pid: int) -> None:
    if not _process_is_alive(pid):
        return
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = (
            wintypes.DWORD,
            wintypes.BOOL,
            wintypes.DWORD,
        )
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.TerminateProcess.argtypes = (
            wintypes.HANDLE,
            wintypes.UINT,
        )
        kernel32.TerminateProcess.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
        kernel32.CloseHandle.restype = wintypes.BOOL
        handle = kernel32.OpenProcess(0x0001, False, pid)
        if not handle:
            return
        try:
            kernel32.TerminateProcess(handle, 1)
        finally:
            kernel32.CloseHandle(handle)
        return
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def _published_pid(path: Path) -> int | None:
    if not path.exists():
        return None
    try:
        pid = int(path.read_text(encoding="ascii"))
    except (OSError, ValueError):
        return None
    return pid if pid > 0 else None


def _bounded_tree_cleanup(
    *,
    stop_path: Path,
    pid_paths: tuple[Path, ...],
) -> None:
    stop_path.write_bytes(b"stop\n")
    pids = tuple(
        pid
        for pid in (_published_pid(path) for path in pid_paths)
        if pid is not None
    )
    if _wait_for_processes_exit(pids, timeout_seconds=3.0):
        return
    for pid in reversed(pids):
        _force_terminate_process(pid)
    _wait_for_processes_exit(pids, timeout_seconds=3.0)


@pytest.mark.parametrize(
    "failure_type",
    (_InjectedCaptureBaseException, RuntimeError),
    ids=("base-exception", "thread-start-runtime-error"),
)
def test_execute_child_cleans_tree_when_capture_start_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[BaseException],
) -> None:
    """Post-``Popen`` failures cannot bypass whole-tree containment."""

    interpreter = _project_launcher_executable()
    report_path = (
        tmp_path / "control" / "reports" / "capture-start-failure.json"
    ).resolve()
    report_path.parent.mkdir(parents=True)
    parent_pid_path = (tmp_path / "capture-parent.pid").resolve()
    descendant_pid_path = (tmp_path / "capture-descendant.pid").resolve()
    stop_path = (tmp_path / "capture-stop").resolve()
    descendant_script = (
        "import os, time\n"
        "from pathlib import Path\n"
        f"pid_path = Path({str(descendant_pid_path)!r})\n"
        f"stop = Path({str(stop_path)!r})\n"
        "pid_path.write_text(str(os.getpid()), encoding='ascii')\n"
        "deadline = time.monotonic() + 120.0\n"
        "while not stop.exists() and time.monotonic() < deadline:\n"
        "    time.sleep(0.05)\n"
    )
    parent_script = (
        "import os, subprocess, time\n"
        "from pathlib import Path\n"
        f"parent_pid_path = Path({str(parent_pid_path)!r})\n"
        f"descendant_pid_path = Path({str(descendant_pid_path)!r})\n"
        f"stop = Path({str(stop_path)!r})\n"
        "parent_pid_path.write_text(str(os.getpid()), encoding='ascii')\n"
        "subprocess.Popen(\n"
        f"    [{interpreter!r}, '-P', '-c', "
        f"{descendant_script!r}],\n"
        "    stdin=subprocess.DEVNULL,\n"
        "    stdout=subprocess.DEVNULL,\n"
        "    stderr=subprocess.DEVNULL,\n"
        ")\n"
        "deadline = time.monotonic() + 5.0\n"
        "while not descendant_pid_path.exists() and time.monotonic() < deadline:\n"
        "    time.sleep(0.01)\n"
        "if not descendant_pid_path.exists():\n"
        "    raise RuntimeError('descendant did not publish its identity')\n"
        "deadline = time.monotonic() + 120.0\n"
        "while not stop.exists() and time.monotonic() < deadline:\n"
        "    time.sleep(0.05)\n"
    )
    original_start = mutation_assurance._BoundedPipeCapture.start
    start_calls = 0

    def fail_second_capture_start(
        capture: mutation_assurance._BoundedPipeCapture,
    ) -> None:
        nonlocal start_calls
        start_calls += 1
        if start_calls == 1:
            original_start(capture)
            return
        deadline = time.monotonic() + 5.0
        while (
            _published_pid(descendant_pid_path) is None
            and time.monotonic() < deadline
        ):
            time.sleep(0.01)
        raise failure_type("injected capture-thread start failure")

    monkeypatch.setattr(
        mutation_assurance._BoundedPipeCapture,
        "start",
        fail_second_capture_start,
    )
    pids: tuple[int, ...] = ()
    alive_after_execute: tuple[int, ...] = ()
    try:
        with pytest.raises(
            failure_type,
            match="injected capture-thread start failure",
        ):
            execute_child(
                argv=(
                    interpreter,
                    "-P",
                    "-c",
                    parent_script,
                ),
                cwd=tmp_path,
                environment=child_environment(tmp_path, seed=11004),
                timeout_seconds=10,
                report_path=report_path,
            )
        parent_pid = _published_pid(parent_pid_path)
        descendant_pid = _published_pid(descendant_pid_path)
        assert parent_pid is not None
        assert descendant_pid is not None
        pids = (parent_pid, descendant_pid)
        _wait_for_processes_exit(pids, timeout_seconds=2.0)
        alive_after_execute = tuple(
            pid for pid in pids if _process_is_alive(pid)
        )
    finally:
        _bounded_tree_cleanup(
            stop_path=stop_path,
            pid_paths=(parent_pid_path, descendant_pid_path),
        )

    assert start_calls == 2
    assert alive_after_execute == (), (
        "execute_child leaked processes after capture start failure: "
        f"{alive_after_execute}"
    )
    assert all(not _process_is_alive(pid) for pid in pids)


def test_execute_child_cleans_tree_when_parent_wait_is_interrupted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A non-``Exception`` wait interruption cannot strand the child tree."""

    interpreter = _project_launcher_executable()
    report_path = (
        tmp_path / "control" / "reports" / "wait-interruption.json"
    ).resolve()
    report_path.parent.mkdir(parents=True)
    parent_pid_path = (tmp_path / "wait-parent.pid").resolve()
    descendant_pid_path = (tmp_path / "wait-descendant.pid").resolve()
    stop_path = (tmp_path / "wait-stop").resolve()
    descendant_script = (
        "import os, time\n"
        "from pathlib import Path\n"
        f"pid_path = Path({str(descendant_pid_path)!r})\n"
        f"stop = Path({str(stop_path)!r})\n"
        "pid_path.write_text(str(os.getpid()), encoding='ascii')\n"
        "deadline = time.monotonic() + 120.0\n"
        "while not stop.exists() and time.monotonic() < deadline:\n"
        "    time.sleep(0.05)\n"
    )
    parent_script = (
        "import os, subprocess, time\n"
        "from pathlib import Path\n"
        f"parent_pid_path = Path({str(parent_pid_path)!r})\n"
        f"descendant_pid_path = Path({str(descendant_pid_path)!r})\n"
        f"stop = Path({str(stop_path)!r})\n"
        "parent_pid_path.write_text(str(os.getpid()), encoding='ascii')\n"
        "subprocess.Popen(\n"
        f"    [{interpreter!r}, '-P', '-c', "
        f"{descendant_script!r}],\n"
        "    stdin=subprocess.DEVNULL,\n"
        "    stdout=subprocess.DEVNULL,\n"
        "    stderr=subprocess.DEVNULL,\n"
        ")\n"
        "deadline = time.monotonic() + 5.0\n"
        "while not descendant_pid_path.exists() and time.monotonic() < deadline:\n"
        "    time.sleep(0.01)\n"
        "if not descendant_pid_path.exists():\n"
        "    raise RuntimeError('descendant did not publish its identity')\n"
        "deadline = time.monotonic() + 120.0\n"
        "while not stop.exists() and time.monotonic() < deadline:\n"
        "    time.sleep(0.05)\n"
    )
    original_popen = mutation_assurance.subprocess.Popen

    class InterruptingWaitProcess:
        def __init__(self, process: object) -> None:
            self._process = process
            self._interrupted = False

        def __getattr__(self, name: str) -> object:
            return getattr(self._process, name)

        def wait(self, timeout: float | None = None) -> int:
            if not self._interrupted:
                self._interrupted = True
                deadline = time.monotonic() + 5.0
                while (
                    _published_pid(descendant_pid_path) is None
                    and time.monotonic() < deadline
                ):
                    time.sleep(0.01)
                raise _InjectedCaptureBaseException(
                    "injected parent-wait interruption"
                )
            return self._process.wait(timeout=timeout)

    processes: list[InterruptingWaitProcess] = []

    def popen_with_interrupted_wait(
        *args: object,
        **kwargs: object,
    ) -> InterruptingWaitProcess:
        process = InterruptingWaitProcess(original_popen(*args, **kwargs))
        processes.append(process)
        return process

    monkeypatch.setattr(
        mutation_assurance.subprocess,
        "Popen",
        popen_with_interrupted_wait,
    )
    pids: tuple[int, ...] = ()
    alive_after_execute: tuple[int, ...] = ()
    try:
        with pytest.raises(
            _InjectedCaptureBaseException,
            match="injected parent-wait interruption",
        ):
            execute_child(
                argv=(
                    interpreter,
                    "-P",
                    "-c",
                    parent_script,
                ),
                cwd=tmp_path,
                environment=child_environment(tmp_path, seed=11007),
                timeout_seconds=10,
                report_path=report_path,
            )
        parent_pid = _published_pid(parent_pid_path)
        descendant_pid = _published_pid(descendant_pid_path)
        assert parent_pid is not None
        assert descendant_pid is not None
        pids = (parent_pid, descendant_pid)
        _wait_for_processes_exit(pids, timeout_seconds=2.0)
        alive_after_execute = tuple(
            pid for pid in pids if _process_is_alive(pid)
        )
    finally:
        _bounded_tree_cleanup(
            stop_path=stop_path,
            pid_paths=(parent_pid_path, descendant_pid_path),
        )

    assert len(processes) == 1
    assert processes[0]._interrupted is True
    assert alive_after_execute == (), (
        "execute_child leaked processes after parent wait interruption: "
        f"{alive_after_execute}"
    )
    assert all(not _process_is_alive(pid) for pid in pids)


@pytest.mark.skipif(
    not sys.platform.startswith("linux"),
    reason="Linux subreaper containment requires Linux /proc and prctl",
)
def test_execute_child_terminates_setsid_descendant_after_parent_exit(
    tmp_path: Path,
) -> None:
    """A DEVNULL/setsid grandchild cannot escape the mutation boundary."""

    interpreter = _project_launcher_executable()
    report_path = (
        tmp_path / "control" / "reports" / "setsid-descendant.json"
    ).resolve()
    report_path.parent.mkdir(parents=True)
    descendant_pid_path = (tmp_path / "setsid-descendant.pid").resolve()
    stop_path = (tmp_path / "setsid-stop").resolve()
    descendant_script = (
        "import os, time\n"
        "from pathlib import Path\n"
        f"pid_path = Path({str(descendant_pid_path)!r})\n"
        f"stop = Path({str(stop_path)!r})\n"
        "pid_path.write_text(str(os.getpid()), encoding='ascii')\n"
        "deadline = time.monotonic() + 120.0\n"
        "while not stop.exists() and time.monotonic() < deadline:\n"
        "    time.sleep(0.05)\n"
    )
    parent_script = (
        "import subprocess, time\n"
        "from pathlib import Path\n"
        f"pid_path = Path({str(descendant_pid_path)!r})\n"
        "subprocess.Popen(\n"
        f"    [{interpreter!r}, '-P', '-c', "
        f"{descendant_script!r}],\n"
        "    stdin=subprocess.DEVNULL,\n"
        "    stdout=subprocess.DEVNULL,\n"
        "    stderr=subprocess.DEVNULL,\n"
        "    start_new_session=True,\n"
        ")\n"
        "deadline = time.monotonic() + 5.0\n"
        "while not pid_path.exists() and time.monotonic() < deadline:\n"
        "    time.sleep(0.01)\n"
        "if not pid_path.exists():\n"
        "    raise RuntimeError('setsid descendant did not publish identity')\n"
    )
    descendant_pid: int | None = None
    observation = None
    alive_after_execute = False
    try:
        observation = execute_child(
            argv=(
                interpreter,
                "-P",
                "-c",
                parent_script,
            ),
            cwd=tmp_path,
            environment=child_environment(tmp_path, seed=11005),
            timeout_seconds=10,
            report_path=report_path,
        )
        descendant_pid = _published_pid(descendant_pid_path)
        assert descendant_pid is not None
        _wait_for_process_exit(descendant_pid, timeout_seconds=2.0)
        alive_after_execute = _process_is_alive(descendant_pid)
    finally:
        _bounded_tree_cleanup(
            stop_path=stop_path,
            pid_paths=(descendant_pid_path,),
        )

    assert observation is not None
    assert observation.returncode == 0, (
        f"stdout:\n{observation.stdout}\nstderr:\n{observation.stderr}"
    )
    assert observation.timed_out is False
    assert alive_after_execute is False
    assert descendant_pid is not None
    assert _process_is_alive(descendant_pid) is False


def test_non_linux_posix_containment_refuses_explicitly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A non-Linux POSIX host cannot silently run without a subreaper."""

    monkeypatch.setattr(
        mutation_assurance,
        "os",
        SimpleNamespace(name="posix"),
    )
    monkeypatch.setattr(
        mutation_assurance,
        "sys",
        SimpleNamespace(platform="darwin"),
    )

    with pytest.raises(
        mutation_assurance.MutationAssuranceError,
        match="require Linux subreaper containment",
    ):
        mutation_assurance._PosixSubreaper()


@pytest.mark.skipif(
    os.name != "nt",
    reason="Windows Job Object containment canary",
)
def test_windows_job_contains_new_process_group_devnull_descendant(
    tmp_path: Path,
) -> None:
    """A Windows process-group boundary cannot escape the assigned Job."""

    interpreter = _project_launcher_executable()
    report_path = (
        tmp_path / "control" / "reports" / "windows-job-descendant.json"
    ).resolve()
    report_path.parent.mkdir(parents=True)
    descendant_pid_path = (tmp_path / "windows-job-descendant.pid").resolve()
    stop_path = (tmp_path / "windows-job-stop").resolve()
    descendant_script = (
        "import os, time\n"
        "from pathlib import Path\n"
        f"pid_path = Path({str(descendant_pid_path)!r})\n"
        f"stop = Path({str(stop_path)!r})\n"
        "pid_path.write_text(str(os.getpid()), encoding='ascii')\n"
        "deadline = time.monotonic() + 120.0\n"
        "while not stop.exists() and time.monotonic() < deadline:\n"
        "    time.sleep(0.05)\n"
    )
    parent_script = (
        "import subprocess, time\n"
        "from pathlib import Path\n"
        f"pid_path = Path({str(descendant_pid_path)!r})\n"
        "subprocess.Popen(\n"
        f"    [{interpreter!r}, '-P', '-c', "
        f"{descendant_script!r}],\n"
        "    stdin=subprocess.DEVNULL,\n"
        "    stdout=subprocess.DEVNULL,\n"
        "    stderr=subprocess.DEVNULL,\n"
        "    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,\n"
        ")\n"
        "deadline = time.monotonic() + 5.0\n"
        "while not pid_path.exists() and time.monotonic() < deadline:\n"
        "    time.sleep(0.01)\n"
        "if not pid_path.exists():\n"
        "    raise RuntimeError('Windows descendant did not publish identity')\n"
    )
    descendant_pid: int | None = None
    observation = None
    alive_after_execute = False
    try:
        observation = execute_child(
            argv=(
                interpreter,
                "-P",
                "-c",
                parent_script,
            ),
            cwd=tmp_path,
            environment=child_environment(tmp_path, seed=11006),
            timeout_seconds=10,
            report_path=report_path,
        )
        descendant_pid = _published_pid(descendant_pid_path)
        assert descendant_pid is not None
        _wait_for_process_exit(descendant_pid, timeout_seconds=2.0)
        alive_after_execute = _process_is_alive(descendant_pid)
    finally:
        _bounded_tree_cleanup(
            stop_path=stop_path,
            pid_paths=(descendant_pid_path,),
        )

    assert observation is not None
    assert observation.returncode == 0, observation.stderr
    assert observation.timed_out is False
    assert alive_after_execute is False
    assert descendant_pid is not None
    assert _process_is_alive(descendant_pid) is False


@pytest.mark.skipif(
    os.name != "nt",
    reason="Windows suspended-process ordering canary",
)
def test_windows_child_is_suspended_until_job_assignment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The child cannot execute user code before entering its Job Object."""

    interpreter = _project_launcher_executable()
    report_path = (
        tmp_path / "control" / "reports" / "windows-suspend-order.json"
    ).resolve()
    report_path.parent.mkdir(parents=True)
    ran_path = (tmp_path / "windows-suspended-child-ran.txt").resolve()
    script = (
        "from pathlib import Path\n"
        f"Path({str(ran_path)!r}).write_bytes(b'ran\\n')\n"
    )
    original_popen = mutation_assurance.subprocess.Popen
    original_assign = mutation_assurance._WindowsJob.assign
    original_resume = mutation_assurance._WindowsJob.resume
    events: list[str] = []
    observed_creationflags: list[int] = []

    def recording_popen(*args: object, **kwargs: object) -> object:
        flags = kwargs.get("creationflags")
        assert isinstance(flags, int)
        observed_creationflags.append(flags)
        events.append("popen")
        return original_popen(*args, **kwargs)

    def recording_assign(
        job: mutation_assurance._WindowsJob,
        process: object,
    ) -> None:
        events.append("assign")
        assert not ran_path.exists()
        original_assign(job, process)

    def recording_resume(
        job: mutation_assurance._WindowsJob,
        process: object,
    ) -> None:
        events.append("resume")
        assert not ran_path.exists()
        original_resume(job, process)

    monkeypatch.setattr(
        mutation_assurance.subprocess,
        "Popen",
        recording_popen,
    )
    monkeypatch.setattr(
        mutation_assurance._WindowsJob,
        "assign",
        recording_assign,
    )
    monkeypatch.setattr(
        mutation_assurance._WindowsJob,
        "resume",
        recording_resume,
    )

    observation = execute_child(
        argv=(interpreter, "-P", "-c", script),
        cwd=tmp_path,
        environment=child_environment(tmp_path, seed=11008),
        timeout_seconds=10,
        report_path=report_path,
    )

    assert observation.returncode == 0, observation.stderr
    assert observation.timed_out is False
    assert ran_path.read_bytes() == b"ran\n"
    assert events == ["popen", "assign", "resume"]
    assert len(observed_creationflags) == 1
    assert observed_creationflags[0] & 0x00000004
    assert observed_creationflags[0] & (
        getattr(mutation_assurance.subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    )


@pytest.mark.skipif(
    os.name != "nt",
    reason="Windows suspended-process failure canary",
)
def test_windows_resume_failure_terminates_suspended_child(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed resume closes the Job without running suspended user code."""

    interpreter = _project_launcher_executable()
    report_path = (
        tmp_path / "control" / "reports" / "windows-resume-failure.json"
    ).resolve()
    report_path.parent.mkdir(parents=True)
    ran_path = (tmp_path / "windows-resume-failure-ran.txt").resolve()
    script = (
        "from pathlib import Path\n"
        f"Path({str(ran_path)!r}).write_bytes(b'ran\\n')\n"
    )
    original_popen = mutation_assurance.subprocess.Popen
    processes: list[object] = []

    def recording_popen(*args: object, **kwargs: object) -> object:
        process = original_popen(*args, **kwargs)
        processes.append(process)
        return process

    def fail_resume(
        _job: mutation_assurance._WindowsJob,
        _process: object,
    ) -> None:
        raise mutation_assurance.MutationAssuranceError(
            "injected Windows resume failure"
        )

    monkeypatch.setattr(
        mutation_assurance.subprocess,
        "Popen",
        recording_popen,
    )
    monkeypatch.setattr(
        mutation_assurance._WindowsJob,
        "resume",
        fail_resume,
    )

    with pytest.raises(
        mutation_assurance.MutationAssuranceError,
        match="injected Windows resume failure",
    ):
        execute_child(
            argv=(interpreter, "-P", "-c", script),
            cwd=tmp_path,
            environment=child_environment(tmp_path, seed=11009),
            timeout_seconds=10,
            report_path=report_path,
        )

    assert len(processes) == 1
    process = processes[0]
    assert process.poll() is not None
    assert not ran_path.exists()


@pytest.mark.skipif(
    os.name != "nt",
    reason="Windows suspended-process assignment failure canary",
)
def test_windows_job_assignment_failure_terminates_suspended_child(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed Job assignment cannot run or strand suspended user code."""

    interpreter = _project_launcher_executable()
    report_path = (
        tmp_path / "control" / "reports" / "windows-assign-failure.json"
    ).resolve()
    report_path.parent.mkdir(parents=True)
    ran_path = (tmp_path / "windows-assign-failure-ran.txt").resolve()
    script = (
        "from pathlib import Path\n"
        f"Path({str(ran_path)!r}).write_bytes(b'ran\\n')\n"
    )
    original_popen = mutation_assurance.subprocess.Popen
    processes: list[object] = []
    observed_creationflags: list[int] = []

    def recording_popen(*args: object, **kwargs: object) -> object:
        flags = kwargs.get("creationflags")
        assert isinstance(flags, int)
        observed_creationflags.append(flags)
        process = original_popen(*args, **kwargs)
        processes.append(process)
        return process

    def fail_assign(
        _job: mutation_assurance._WindowsJob,
        _process: object,
    ) -> None:
        raise mutation_assurance.MutationAssuranceError(
            "injected Windows Job assignment failure"
        )

    monkeypatch.setattr(
        mutation_assurance.subprocess,
        "Popen",
        recording_popen,
    )
    monkeypatch.setattr(
        mutation_assurance._WindowsJob,
        "assign",
        fail_assign,
    )

    with pytest.raises(
        mutation_assurance.MutationAssuranceError,
        match="injected Windows Job assignment failure",
    ):
        execute_child(
            argv=(interpreter, "-P", "-c", script),
            cwd=tmp_path,
            environment=child_environment(tmp_path, seed=11010),
            timeout_seconds=10,
            report_path=report_path,
        )

    assert len(processes) == 1
    assert len(observed_creationflags) == 1
    assert observed_creationflags[0] & 0x00000004
    process = processes[0]
    assert process.poll() is not None
    assert not ran_path.exists()


@pytest.mark.skipif(
    os.name != "nt" and not sys.platform.startswith("linux"),
    reason="pre-handle child recovery requires Windows or Linux containment",
)
def test_popen_baseexception_after_os_spawn_recovers_unreturned_child(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A child cannot survive if Popen raises after creating it internally."""

    expected_interpreter = (
        _ROOT / ".venv" / "Scripts" / "python.exe"
        if os.name == "nt"
        else _ROOT / ".venv" / "bin" / "python"
    )
    assert os.path.samefile(expected_interpreter, sys.executable)
    report_path = (
        tmp_path / "control" / "reports" / "popen-pre-handle-failure.json"
    ).resolve()
    report_path.parent.mkdir(parents=True)
    ran_path = (tmp_path / "popen-pre-handle-child-ran.txt").resolve()
    script = (
        "import time\n"
        "from pathlib import Path\n"
        "time.sleep(60)\n"
        f"Path({str(ran_path)!r}).write_bytes(b'ran\\n')\n"
    )
    original_popen = mutation_assurance.subprocess.Popen
    pids: list[int] = []

    def spawn_then_raise(*args: object, **kwargs: object) -> object:
        process = original_popen(*args, **kwargs)
        pids.append(process.pid)
        raise _InjectedPopenBaseException(
            "injected failure before Popen returned its handle"
        )

    monkeypatch.setattr(
        mutation_assurance.subprocess,
        "Popen",
        spawn_then_raise,
    )
    try:
        with pytest.raises(
            _InjectedPopenBaseException,
            match="before Popen returned",
        ):
            execute_child(
                argv=(str(expected_interpreter), "-P", "-c", script),
                cwd=tmp_path,
                environment=child_environment(tmp_path, seed=11011),
                timeout_seconds=10,
                report_path=report_path,
            )
        assert len(pids) == 1
        assert _wait_for_process_exit(pids[0], timeout_seconds=2.0)
        assert not ran_path.exists()
    finally:
        for pid in pids:
            _force_terminate_process(pid)


def test_runtime_tree_rejects_importable_legacy_bytecode(
    tmp_path: Path,
) -> None:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / "shadow.pyc").write_bytes(b"legacy-bytecode\n")

    with pytest.raises(
        mutation_assurance.MutationAssuranceError,
        match="importable legacy bytecode",
    ):
        mutation_assurance._enumerate_runtime_tree(runtime, role="probe")


def test_runtime_identity_requires_system_site_packages_disabled(
    tmp_path: Path,
) -> None:
    config = tmp_path / "pyvenv.cfg"
    config.write_text(
        "home = C:\\Python\ninclude-system-site-packages = true\n",
        encoding="utf-8",
    )

    with pytest.raises(
        mutation_assurance.MutationAssuranceError,
        match="must disable system site packages exactly",
    ):
        mutation_assurance._venv_disables_system_site_packages(config)


def test_linux_subreaper_uses_only_the_fresh_final_child_census(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A child gone at the deadline cannot survive through stale bookkeeping."""

    subreaper = object.__new__(mutation_assurance._PosixSubreaper)
    subreaper._preexisting_children = set()
    child_sets = iter(({42}, set()))
    monotonic_values = iter((0.0, 0.0, 1.0))
    monkeypatch.setattr(
        mutation_assurance,
        "_linux_direct_children",
        lambda: next(child_sets),
    )
    monkeypatch.setattr(
        mutation_assurance.time,
        "monotonic",
        lambda: next(monotonic_values),
    )
    monkeypatch.setattr(mutation_assurance.time, "sleep", lambda _value: None)
    monkeypatch.setattr(
        mutation_assurance.signal,
        "SIGKILL",
        9,
        raising=False,
    )
    monkeypatch.setattr(mutation_assurance.os, "kill", lambda _pid, _sig: None)
    monkeypatch.setattr(
        mutation_assurance.os,
        "WNOHANG",
        1,
        raising=False,
    )
    monkeypatch.setattr(
        mutation_assurance.os,
        "waitpid",
        lambda _pid, _flags: (0, 0),
    )

    subreaper.terminate_adopted(timeout_seconds=0.5)


@pytest.mark.skipif(os.name == "nt", reason="POSIX venv symlink canary")
def test_posix_project_launcher_binds_the_full_symlink_chain(
    tmp_path: Path,
) -> None:
    base = tmp_path / "base" / "python3.14"
    base.parent.mkdir()
    base.write_bytes(b"synthetic-posix-python\n")
    bin_directory = tmp_path / ".venv" / "bin"
    bin_directory.mkdir(parents=True)
    python3 = bin_directory / "python3"
    python = bin_directory / "python"
    python3.symlink_to(base)
    python.symlink_to("python3")

    identity, raw = mutation_assurance._project_launcher_identity(
        python,
        python,
    )

    assert raw == b"synthetic-posix-python\n"
    assert identity["path"] == str(python.absolute())
    assert identity["resolved_path"] == str(base.resolve(strict=True))
    assert identity["symlinks"] == [
        {"path": str(python.absolute()), "target": "python3"},
        {"path": str(python3.absolute()), "target": str(base)},
    ]


def test_execute_child_bounds_noisy_output_and_terminates_at_deadline(
    tmp_path: Path,
) -> None:
    """A chatty, sleeping child cannot retain unbounded output or wait forever."""

    interpreter = _project_launcher_executable()
    report_path = (
        tmp_path / "control" / "reports" / "noisy-timeout.json"
    ).resolve()
    report_path.parent.mkdir(parents=True)
    output_bytes = _OUTPUT_LIMIT_BYTES * 2
    script = (
        "import sys, time\n"
        f"sys.stdout.buffer.write(b'O' * {output_bytes})\n"
        "sys.stdout.buffer.flush()\n"
        f"sys.stderr.buffer.write(b'E' * {output_bytes})\n"
        "sys.stderr.buffer.flush()\n"
        "time.sleep(60)\n"
    )

    observation = execute_child(
        argv=(interpreter, "-P", "-c", script),
        cwd=tmp_path,
        environment=child_environment(tmp_path, seed=11001),
        timeout_seconds=1,
        report_path=report_path,
    )

    assert observation.timed_out is True
    assert observation.returncode not in {None, 0}
    assert observation.duration_ns < 20_000_000_000
    assert observation.output_truncated is True
    assert observation.stdout == "O" * _OUTPUT_LIMIT_BYTES
    assert observation.stderr == "E" * _OUTPUT_LIMIT_BYTES
    assert observation.stdout_sha256 == sha256_bytes(b"O" * output_bytes)
    assert observation.stderr_sha256 == sha256_bytes(b"E" * output_bytes)
    assert observation.report is None
    assert observation.report_sha256 is None
    assert observation.report_error == "mutation child report is missing"
    assert not report_path.exists()


@pytest.mark.parametrize(
    ("line_ending", "case_id"),
    (
        (b"\n", "lf"),
        (b"\r\n", "crlf"),
        (b"\r", "lone-cr"),
    ),
)
def test_exact_mutation_preserves_portable_source_line_endings(
    tmp_path: Path,
    line_ending: bytes,
    case_id: str,
) -> None:
    canonical = b"def target():\n    return 41\n"
    expected_canonical = b"def target():\n    return 42\n"
    spec = _runtime_spec(
        canonical,
        ast_root=tmp_path / f"ast-identities-{case_id}",
    )
    source = canonical.replace(b"\n", line_ending)

    mutated = apply_exact_mutation(spec, source)

    assert mutated == expected_canonical.replace(b"\n", line_ending)
    assert canonical_source_bytes(mutated) == expected_canonical
    assert sha256_bytes(canonical_source_bytes(source)) == (
        spec.preimage_sha256
    )
    assert sha256_bytes(canonical_source_bytes(mutated)) == (
        spec.postimage_sha256
    )


def test_execute_child_removes_redirected_descendant_after_green_parent_exit(
    tmp_path: Path,
) -> None:
    """A normally exiting parent cannot leave a pipe-owning child behind."""

    interpreter = _project_launcher_executable()
    control_root = tmp_path / "control"
    report_path = (
        control_root / "reports" / "green-parent-descendant.json"
    ).resolve()
    report_path.parent.mkdir(parents=True)
    ready_path = (tmp_path / "descendant-ready.txt").resolve()
    stop_path = (tmp_path / "descendant-stop").resolve()
    token = "phase11-green-parent-descendant"
    descendant_script = (
        "import os, sys, time\n"
        "from pathlib import Path\n"
        f"ready = Path({str(ready_path)!r})\n"
        f"stop = Path({str(stop_path)!r})\n"
        "ready.write_text(f'{os.getpid()}:{sys.argv[1]}', encoding='ascii')\n"
        "sys.stdout.write('DESCENDANT_READY\\n')\n"
        "sys.stdout.flush()\n"
        "deadline = time.monotonic() + 120.0\n"
        "while not stop.exists() and time.monotonic() < deadline:\n"
        "    time.sleep(0.05)\n"
    )
    parent_script = (
        "import subprocess, sys, time\n"
        "from pathlib import Path\n"
        f"ready = Path({str(ready_path)!r})\n"
        "child = subprocess.Popen(\n"
        f"    [{interpreter!r}, '-P', '-c', "
        f"{descendant_script!r}, {token!r}],\n"
        "    stdin=subprocess.DEVNULL,\n"
        "    stdout=sys.stdout,\n"
        "    stderr=sys.stderr,\n"
        ")\n"
        "deadline = time.monotonic() + 5.0\n"
        "while not ready.exists() and time.monotonic() < deadline:\n"
        "    time.sleep(0.01)\n"
        "if not ready.exists():\n"
        "    raise RuntimeError('descendant did not publish its identity')\n"
        "print(f'PARENT_EXIT:{child.pid}', flush=True)\n"
    )
    descendant_pid: int | None = None
    observation = None
    gone_when_execute_returned = False
    try:
        observation = execute_child(
            argv=(
                interpreter,
                "-P",
                "-c",
                parent_script,
            ),
            cwd=tmp_path,
            environment=child_environment(tmp_path, seed=11003),
            timeout_seconds=10,
            report_path=report_path,
        )
        identity = ready_path.read_text(encoding="ascii")
        pid_text, observed_token = identity.split(":", 1)
        assert observed_token == token
        descendant_pid = int(pid_text)
        assert descendant_pid > 0
        gone_when_execute_returned = not _process_is_alive(descendant_pid)
    finally:
        if descendant_pid is None and ready_path.exists():
            try:
                descendant_pid = int(
                    ready_path.read_text(encoding="ascii").split(":", 1)[0]
                )
            except (OSError, ValueError):
                descendant_pid = None
        if descendant_pid is not None and _process_is_alive(descendant_pid):
            stop_path.write_bytes(b"stop\n")
            if not _wait_for_process_exit(descendant_pid, timeout_seconds=5.0):
                _force_terminate_process(descendant_pid)
                _wait_for_process_exit(descendant_pid, timeout_seconds=5.0)

    assert observation is not None
    assert observation.returncode == 0, observation.stderr
    assert observation.timed_out is False
    assert observation.duration_ns < 10_000_000_000
    assert observation.output_truncated is False
    assert "DESCENDANT_READY" in observation.stdout
    assert "PARENT_EXIT:" in observation.stdout
    assert observation.report is None
    assert observation.report_error == "mutation child report is missing"
    assert gone_when_execute_returned is True
    assert descendant_pid is not None
    assert _process_is_alive(descendant_pid) is False


@pytest.mark.parametrize(
    "typed",
    (False, True),
    ids=("hostile-update-wrapper", "typed-wrapper-with-false-metadata"),
)
def test_real_reporter_rejects_post_addoption_pytest_lru_replacement_without_calling(
    tmp_path: Path,
    typed: bool,
) -> None:
    """The explicit reporter binds pytest's wrapper before conftest mutation."""

    snapshot_root = tmp_path / "snapshot"
    control_root = tmp_path / "control"
    snapshot_root.mkdir()
    control_root.mkdir()
    source = b"def target():\n    return 41\n"
    spec = _runtime_spec(source, ast_root=tmp_path / "ast-identities")
    from moira import moira_native

    native_source = Path(moira_native.__backend_file__).resolve(strict=True)
    native_path = snapshot_root / "moira" / native_source.name
    sentinel = control_root / "hostile-wrapper-called"

    _write(snapshot_root / "moira" / "__init__.py", b"# synthetic package\n")
    _write(snapshot_root / Path(spec.source_path), source)
    _write(native_path, native_source.read_bytes())
    _write(snapshot_root / "tests" / "__init__.py", b"")
    _copy_repository_file("tests/mutation_reporter.py", snapshot_root)
    _copy_repository_file("tests/support/__init__.py", snapshot_root)
    _copy_repository_file("tests/support/mutation_toolchain.py", snapshot_root)
    _copy_repository_file("tests/support/network_policy.py", snapshot_root)
    _copy_repository_file(
        "tests/support/network_bootstrap/sitecustomize.py",
        snapshot_root,
    )
    _write(
        snapshot_root / "tests" / "conftest.py",
        (
            "import functools\n"
            "from pathlib import Path\n\n"
            "import pytest\n\n"
            f"_SENTINEL = Path({os.fspath(sentinel)!r})\n"
            f"_TYPED = {typed!r}\n\n"
            "@pytest.hookimpl(tryfirst=True)\n"
            "def pytest_configure(config):\n"
            "    manager_namespace = object.__getattribute__(\n"
            "        config.pluginmanager, '__dict__'\n"
            "    )\n"
            "    original = dict.__getitem__(\n"
            "        manager_namespace, '_get_directory'\n"
            "    )\n"
            "    @functools.lru_cache(maxsize=256, typed=_TYPED)\n"
            "    def hostile(*args, **kwargs):\n"
            "        _SENTINEL.write_bytes(b'called\\n')\n"
            "        return original(*args, **kwargs)\n"
            "    functools.update_wrapper(hostile, original)\n"
            "    if _TYPED:\n"
            "        hostile_namespace = object.__getattribute__(\n"
            "            hostile, '__dict__'\n"
            "        )\n"
            "        original_namespace = object.__getattribute__(\n"
            "            original, '__dict__'\n"
            "        )\n"
            "        dict.__setitem__(\n"
            "            hostile_namespace,\n"
            "            'cache_parameters',\n"
            "            dict.__getitem__(original_namespace, 'cache_parameters'),\n"
            "        )\n"
            "    dict.__setitem__(manager_namespace, '_get_directory', hostile)\n"
        ).encode("utf-8"),
    )
    _write(
        snapshot_root / "tests" / "test_probe.py",
        b"from moira.probe import target\n\n"
        b"def test_declared_relation():\n"
        b"    assert target() == 41\n",
    )

    execution_id = f"phase11-hostile-pytest-lru-{int(typed)}"
    report_path = (control_root / "reports" / f"{execution_id}.json").resolve()
    report_path.parent.mkdir()
    interpreter = _standalone_parent_interpreter_identity()
    argv = child_argv(
        interpreter=str(interpreter["executable"]),
        snapshot_root=snapshot_root,
        control_root=control_root,
        spec=spec,
        execution_id=execution_id,
        report_path=report_path,
    )
    observation = execute_child(
        argv=argv,
        cwd=snapshot_root,
        environment=child_environment(snapshot_root, seed=11013 + int(typed)),
        timeout_seconds=spec.timeout_seconds,
        report_path=report_path,
    )

    assert observation.returncode != 0
    assert observation.timed_out is False
    assert observation.output_truncated is False
    assert "differs from early reporter identity" in observation.stderr
    assert observation.report is None
    assert observation.report_error == "mutation child report is missing"
    assert sentinel.exists() is False


def test_real_reporter_child_emits_atomic_exact_trace_receipt(
    tmp_path: Path,
) -> None:
    """The actual opt-in reporter survives a real isolated pytest subprocess."""

    snapshot_root = tmp_path / "snapshot"
    control_root = tmp_path / "control"
    snapshot_root.mkdir()
    control_root.mkdir()
    source = b"def target():\n    return 41\n"
    spec = _runtime_spec(source, ast_root=tmp_path / "ast-identities")
    from moira import moira_native

    native_source = Path(moira_native.__backend_file__).resolve(strict=True)
    native_relative = f"moira/{native_source.name}"
    native_path = snapshot_root / Path(native_relative)

    _write(snapshot_root / "moira" / "__init__.py", b"# synthetic package\n")
    _write(snapshot_root / Path(spec.source_path), source)
    _write(native_path, native_source.read_bytes())
    _write(snapshot_root / "tests" / "__init__.py", b"")
    _copy_repository_file("tests/mutation_reporter.py", snapshot_root)
    _copy_repository_file("tests/support/__init__.py", snapshot_root)
    _copy_repository_file(
        "tests/support/mutation_toolchain.py",
        snapshot_root,
    )
    _copy_repository_file("tests/support/network_policy.py", snapshot_root)
    _copy_repository_file(
        "tests/support/network_bootstrap/sitecustomize.py",
        snapshot_root,
    )
    _write(
        snapshot_root / "tests" / "conftest.py",
        (
            "import fnmatch\n"
            "from pathlib import Path\n\n"
            "import pytest\n\n"
            "class _AlwaysMatch:\n"
            "    def match(self, _value):\n"
            "        return True\n\n"
            "def _poison_fnmatch_cache():\n"
            "    original_compile = fnmatch.re.compile\n"
            "    try:\n"
            "        fnmatch._compile_pattern.cache_clear()\n"
            "        fnmatch.re.compile = lambda _pattern: _AlwaysMatch()\n"
            "        hostile = fnmatch._compile_pattern('phase11-never-match')\n"
            "        assert hostile('phase11-safe') is True\n"
            "    finally:\n"
            "        fnmatch.re.compile = original_compile\n"
            "    info = fnmatch._compile_pattern.cache_info()\n"
            "    assert (info.hits, info.misses, info.currsize) == (0, 1, 1)\n\n"
            "def _active_directory_wrapper(config):\n"
            "    manager = config.pluginmanager\n"
            "    wrapper = manager._get_directory\n"
            "    info = wrapper.cache_info()\n"
            "    assert info.maxsize == 256\n"
            "    return wrapper\n\n"
            "def pytest_collection_modifyitems(items):\n"
            "    for item in items:\n"
            "        item.user_properties.extend((\n"
            f"            ('moira_validation_claim_id', {_CLAIM_ID!r}),\n"
            "            ('moira_validation_contract_sha256', "
            f"{spec.expected_contract_sha256!r}),\n"
            "        ))\n"
            "\n"
            "def pytest_collection_finish(session):\n"
            "    del session\n"
            "    _poison_fnmatch_cache()\n"
            "\n"
            "def pytest_runtest_setup(item):\n"
            "    _poison_fnmatch_cache()\n"
            "    wrapper = _active_directory_wrapper(item.config)\n"
            "    wrapper.cache_clear()\n"
            "    directory = Path(__file__).resolve(strict=True).parent\n"
            "    assert wrapper(directory) == directory\n"
            "    assert tuple(wrapper.cache_info()) == (0, 1, 256, 1)\n"
            "\n"
            "@pytest.hookimpl(wrapper=True, trylast=True)\n"
            "def pytest_sessionfinish(session, exitstatus):\n"
            "    del exitstatus\n"
            "    wrapper = _active_directory_wrapper(session.config)\n"
            "    wrapper.cache_clear()\n"
            "    directory = Path(__file__).resolve(strict=True).parent\n"
            "    assert wrapper(directory) == directory\n"
            "    assert tuple(wrapper.cache_info()) == (0, 1, 256, 1)\n"
            "    result = yield\n"
            "    assert tuple(wrapper.cache_info()) == (0, 0, 256, 0)\n"
            "    return result\n"
        ).encode("utf-8"),
    )
    _write(
        snapshot_root / "tests" / "test_probe.py",
            (
                "import fnmatch\n"
                "from moira.probe import target\n\n"
                "def test_declared_relation(pytestconfig):\n"
                "    info = fnmatch._compile_pattern.cache_info()\n"
                "    assert (info.hits, info.misses, info.currsize) == (0, 0, 0)\n"
                "    wrapper = pytestconfig.pluginmanager._get_directory\n"
                "    assert tuple(wrapper.cache_info()) == (0, 0, 256, 0)\n"
                "    assert fnmatch.fnmatchcase('phase11-safe', "
            "'phase11-never-match') is False\n"
            "    assert target() == 41\n"
        ).encode("utf-8"),
    )

    execution_id = "phase11-runtime-reporter-canary"
    report_path = (
        control_root / "reports" / f"{execution_id}.json"
    ).resolve()
    report_path.parent.mkdir()
    interpreter = _standalone_parent_interpreter_identity()
    argv = child_argv(
        interpreter=str(interpreter["executable"]),
        snapshot_root=snapshot_root,
        control_root=control_root,
        spec=spec,
        execution_id=execution_id,
        report_path=report_path,
    )
    observation = execute_child(
        argv=argv,
        cwd=snapshot_root,
        environment=child_environment(snapshot_root, seed=11002),
        timeout_seconds=spec.timeout_seconds,
        report_path=report_path,
    )

    assert observation.returncode == 0, (
        f"stdout:\n{observation.stdout}\nstderr:\n{observation.stderr}"
    )
    assert observation.timed_out is False
    assert observation.output_truncated is False
    assert observation.report_error is None
    assert observation.report is not None
    assert observation.report_sha256 == sha256_bytes(report_path.read_bytes())
    assert not list(
        report_path.parent.glob(f".{report_path.name}.{execution_id}.tmp")
    )

    report = observation.report
    assert report["selection"] == {
        "selected_nodeids": [{"nodeid": _NODEID, "truncated": False}],
        "selected_count": 1,
        "intended_selected_count": 1,
        "only_intended_selected": True,
    }
    assert [phase["phase"] for phase in report["reports"]] == [
        "setup",
        "call",
        "teardown",
    ]
    assert [phase["outcome"] for phase in report["reports"]] == [
        "passed",
        "passed",
        "passed",
    ]
    assert report["errors"] == {"collection": [], "internal": []}
    assert report["trace"]["attempted"] is True
    assert report["trace"]["call_count"] == 1
    assert report["trace"]["code_sha256"] == [
        spec.preimage_code_sha256
    ]
    assert report["trace"]["resolved_target_code_sha256"] == (
        spec.preimage_code_sha256
    )
    toolchain = report["identity"]["test_toolchain"]
    lru_names = toolchain["normalized_lru_wrapper_names"]
    assert isinstance(lru_names, list) and lru_names
    assert lru_names == sorted(set(lru_names))
    assert any(name.endswith("fnmatch._compile_pattern") for name in lru_names)
    assert (
        "_pytest.config.PytestPluginManager._get_directory."
        "__instance_caches__"
    ) in lru_names
    assert toolchain["normalized_lru_wrapper_count"] == len(lru_names)
    if sys.version_info[:2] == (3, 14):
        assert toolchain["normalized_lru_wrapper_count"] == 47
        assert toolchain["normalized_lru_wrapper_sha256"] == (
            "c7d5b01efce5222f262f26da4341281cf5a50ab92af5b45d28242c2686d56ded"
        )
    assert toolchain["all_normalized_lru_wrappers_empty"] is True

    adjudication = adjudicate_baseline(
        spec=spec,
        observation=observation,
        execution_id=execution_id,
        snapshot_root=snapshot_root,
        interpreter=interpreter,
        native_backend_path=native_path,
        native_backend_sha256=sha256_bytes(native_path.read_bytes()),
    )
    assert adjudication["outcome"] == "baseline_passed", adjudication[
        "reasons"
    ]
    assert adjudication["child_report"] == report
    assert os.path.samefile(
        report["identity"]["source"]["path"],
        snapshot_root / Path(spec.source_path),
    )
