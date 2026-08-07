"""Run Moira's curated Phase 11 mutants in disposable current-state copies."""

from __future__ import annotations

import atexit
import argparse
from datetime import UTC, datetime
import hashlib
import importlib
import importlib.util
import os
from pathlib import Path
import signal
import stat
import sys
import tempfile
from types import FunctionType, ModuleType


_FROZEN_RUNNER_DIGEST_ENV = "MOIRA_PHASE11_FROZEN_RUNNER_SHA256"
_FROZEN_RUNNER_ORIGINAL_ENV = "MOIRA_PHASE11_FROZEN_RUNNER_ORIGINAL"
_FROZEN_RUNNER_ROOT_ENV = "MOIRA_PHASE11_FROZEN_RUNNER_ROOT"
_FROZEN_RUNNER_DIRECTORY_ENV = "MOIRA_PHASE11_FROZEN_RUNNER_DIRECTORY"


def _plain_lexical_path(
    path: Path,
    *,
    label: str,
    kind: str,
    require_single_link: bool = True,
) -> Path:
    """Validate every lexical component before any resolve or open."""

    if kind not in {"directory", "file"}:
        raise RuntimeError(f"Phase 11 internal path kind is invalid: {kind}")
    try:
        absolute = Path(os.path.abspath(os.fspath(path)))
    except (OSError, TypeError, ValueError) as exc:
        raise RuntimeError(f"Phase 11 {label} path is invalid: {exc}") from exc
    if not absolute.is_absolute() or not absolute.anchor:
        raise RuntimeError(f"Phase 11 {label} path is not absolute")
    current = Path(absolute.anchor)
    parts = absolute.parts[1:]
    if not parts:
        raise RuntimeError(f"Phase 11 {label} path names a filesystem root")
    for index, part in enumerate(parts):
        current = current / part
        try:
            metadata = current.lstat()
        except OSError as exc:
            raise RuntimeError(
                f"Phase 11 {label} path component is unavailable: {current}: {exc}"
            ) from exc
        if (
            stat.S_ISLNK(metadata.st_mode)
            or getattr(metadata, "st_file_attributes", 0) & 0x400
        ):
            raise RuntimeError(
                f"Phase 11 {label} crosses a link or reparse point: {current}"
            )
        final = index == len(parts) - 1
        if not final and not stat.S_ISDIR(metadata.st_mode):
            raise RuntimeError(
                f"Phase 11 {label} parent is not a directory: {current}"
            )
        if final and kind == "directory" and not stat.S_ISDIR(metadata.st_mode):
            raise RuntimeError(f"Phase 11 {label} is not a directory: {current}")
        if final and kind == "file":
            if not stat.S_ISREG(metadata.st_mode):
                raise RuntimeError(
                    f"Phase 11 {label} is not a regular file: {current}"
                )
            if require_single_link and metadata.st_nlink != 1:
                raise RuntimeError(
                    f"Phase 11 {label} must not be hard-linked: {current}"
                )
    try:
        resolved = absolute.resolve(strict=True)
    except OSError as exc:
        raise RuntimeError(f"Phase 11 {label} cannot be resolved: {exc}") from exc
    if resolved != absolute:
        raise RuntimeError(
            f"Phase 11 {label} lexical and resolved paths differ: {absolute}"
        )
    return absolute


def _stable_preimport_source(
    path: Path,
    *,
    require_single_link: bool = True,
) -> bytes:
    """Freeze one plain source before its standard loader can execute it."""

    path = _plain_lexical_path(
        path,
        label="import source",
        kind="file",
        require_single_link=require_single_link,
    )
    before = path.lstat()
    if (
        not stat.S_ISREG(before.st_mode)
        or stat.S_ISLNK(before.st_mode)
        or getattr(before, "st_file_attributes", 0) & 0x400
        or (require_single_link and before.st_nlink != 1)
    ):
        raise RuntimeError(f"Phase 11 import source is not plain: {path}")
    with path.open("rb") as stream:
        opened_before = os.fstat(stream.fileno())
        raw = stream.read()
        opened_after = os.fstat(stream.fileno())
    after = path.lstat()
    signatures = {
        (
            value.st_dev,
            value.st_ino,
            value.st_nlink,
            value.st_size,
            getattr(
                value,
                "st_mtime_ns",
                int(value.st_mtime * 1_000_000_000),
            ),
        )
        for value in (before, opened_before, opened_after, after)
    }
    if len(signatures) != 1 or len(raw) != after.st_size:
        raise RuntimeError(f"Phase 11 import source changed while read: {path}")
    return raw


def _windows_known_folder_path(folder_id: str, *, label: str) -> Path:
    """Resolve one OS-owned known folder without ambient environment state."""

    if os.name != "nt":
        raise RuntimeError(f"Phase 11 {label} is Windows-only")
    import ctypes
    from ctypes import wintypes
    import uuid

    class _Guid(ctypes.Structure):
        _fields_ = (
            ("data1", ctypes.c_uint32),
            ("data2", ctypes.c_uint16),
            ("data3", ctypes.c_uint16),
            ("data4", ctypes.c_ubyte * 8),
        )

    parsed = uuid.UUID(folder_id)
    guid = _Guid(
        parsed.time_low,
        parsed.time_mid,
        parsed.time_hi_version,
        (ctypes.c_ubyte * 8)(
            parsed.clock_seq_hi_variant,
            parsed.clock_seq_low,
            *parsed.node.to_bytes(6, "big"),
        ),
    )
    shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    known_folder = shell32.SHGetKnownFolderPath
    known_folder.argtypes = (
        ctypes.POINTER(_Guid),
        wintypes.DWORD,
        wintypes.HANDLE,
        ctypes.POINTER(ctypes.c_void_p),
    )
    known_folder.restype = ctypes.c_long
    allocated = ctypes.c_void_p()
    result = known_folder(ctypes.byref(guid), 0, None, ctypes.byref(allocated))
    if result != 0 or not allocated.value:
        raise RuntimeError(
            f"Phase 11 {label} known-folder lookup failed: HRESULT "
            f"0x{result & 0xFFFFFFFF:08x}"
        )
    ole32 = ctypes.WinDLL("ole32", use_last_error=True)
    free_memory = ole32.CoTaskMemFree
    free_memory.argtypes = (ctypes.c_void_p,)
    free_memory.restype = None
    try:
        value = ctypes.wstring_at(allocated.value)
    finally:
        free_memory(allocated)
    if not value:
        raise RuntimeError(f"Phase 11 {label} known folder is empty")
    return Path(value)


def _reviewed_git_candidates() -> tuple[Path, ...]:
    """Return fixed real-engine locations without consulting PATH or startup.

    POSIX intentionally admits only these plain canonical paths.  Symlinked
    Homebrew installs, custom layouts, and the executable's shared-library
    closure are not privately resolved here; those remain an explicit
    cooperative-host boundary rather than a hostile-filesystem guarantee.
    """

    if os.name == "nt":
        program_files = _windows_known_folder_path(
            "905e63b6-c1bf-494e-b29c-65b732d3d21a",
            label="Program Files",
        )
        program_files_x86 = _windows_known_folder_path(
            "7c5a40ef-a0fb-4bfc-874a-c0f2e0b9fa8e",
            label="Program Files (x86)",
        )
        roots = (program_files, program_files_x86)
        layouts = ("mingw64", "mingw32")
        return tuple(
            root / "Git" / layout / "libexec" / "git-core" / "git.exe"
            for root in roots
            for layout in layouts
        )
    return (
        Path("/usr/bin/git"),
        Path("/usr/local/bin/git"),
        Path("/opt/homebrew/bin/git"),
    )


def _resolve_reviewed_git_runtime(
) -> tuple[Path, bytes, tuple[tuple[Path, bytes], ...]]:
    """Freeze exactly one reviewed real engine and its adjacent DLL scope."""

    admitted: list[Path] = []
    invalid: list[str] = []
    for candidate in _reviewed_git_candidates():
        try:
            candidate.lstat()
        except FileNotFoundError:
            continue
        except OSError as exc:
            invalid.append(f"{candidate}: {exc}")
            continue
        try:
            validated = _plain_lexical_path(
                candidate,
                label="reviewed Git engine",
                kind="file",
            )
        except RuntimeError as exc:
            invalid.append(str(exc))
            continue
        if not os.access(validated, os.X_OK):
            invalid.append(f"reviewed Git engine is not executable: {validated}")
            continue
        if not any(os.path.samefile(validated, prior) for prior in admitted):
            admitted.append(validated)
    if invalid:
        raise RuntimeError(
            "Phase 11 reviewed Git candidate is invalid: " + "; ".join(invalid)
        )
    if len(admitted) != 1:
        raise RuntimeError(
            "Phase 11 requires exactly one reviewed real Git engine at a "
            "supported canonical layout; "
            f"found {len(admitted)}"
        )
    executable = admitted[0]
    engine_raw = _stable_preimport_source(executable)
    helpers: list[tuple[Path, bytes]] = []
    if os.name == "nt":
        try:
            with os.scandir(executable.parent) as entries:
                helper_paths = sorted(
                    (
                        Path(entry.path)
                        for entry in entries
                        if entry.name.casefold().endswith(".dll")
                    ),
                    key=lambda path: path.name.casefold(),
                )
        except OSError as exc:
            raise RuntimeError(
                f"Phase 11 Git runtime cannot be enumerated: {exc}"
            ) from exc
        folded: dict[str, str] = {}
        for helper in helper_paths:
            validated = _plain_lexical_path(
                helper,
                label="reviewed Git runtime helper",
                kind="file",
                require_single_link=False,
            )
            prior = folded.get(validated.name.casefold())
            if prior is not None and prior != validated.name:
                raise RuntimeError(
                    "Phase 11 Git helper filenames collide by case"
                )
            folded[validated.name.casefold()] = validated.name
            helpers.append(
                (
                    validated,
                    _stable_preimport_source(
                        validated,
                        require_single_link=False,
                    ),
                )
            )
    return executable, engine_raw, tuple(helpers)


def _write_frozen_runtime_file(path: Path, raw: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    if _stable_preimport_source(path) != raw:
        raise RuntimeError(f"Phase 11 frozen Git runtime copy changed: {path}")


def _freeze_reviewed_git_runtime(
    directory: Path,
) -> tuple[Path, Path, bytes]:
    source, engine_raw, helpers = _resolve_reviewed_git_runtime()
    runtime = directory / "git-runtime"
    runtime.mkdir()
    _plain_lexical_path(
        runtime,
        label="private Git runtime",
        kind="directory",
    )
    private_executable = runtime / source.name
    _write_frozen_runtime_file(private_executable, engine_raw)
    for helper, raw in helpers:
        _write_frozen_runtime_file(runtime / helper.name, raw)
    expected = tuple(
        sorted((source.name, *(path.name for path, _raw in helpers)), key=str.casefold)
    )
    try:
        with os.scandir(runtime) as entries:
            observed = tuple(
                entry.name
                for entry in sorted(entries, key=lambda entry: entry.name.casefold())
            )
    except OSError as exc:
        raise RuntimeError(
            f"Phase 11 private Git runtime cannot be replayed: {exc}"
        ) from exc
    if observed != expected:
        raise RuntimeError("Phase 11 private Git runtime file set is not exact")
    return source, private_executable, engine_raw


def _remove_staged_runner(directory: Path, staged: Path) -> None:
    """Remove only the exact private files created by stage zero."""

    runtime = directory / "git-runtime"
    if runtime.exists():
        try:
            _plain_lexical_path(
                runtime,
                label="private Git cleanup directory",
                kind="directory",
            )
            with os.scandir(runtime) as entries:
                runtime_files = tuple(Path(entry.path) for entry in entries)
            for path in runtime_files:
                _plain_lexical_path(
                    path,
                    label="private Git cleanup file",
                    kind="file",
                )
            for path in runtime_files:
                path.unlink()
            runtime.rmdir()
        except (OSError, RuntimeError):
            return
    try:
        staged.unlink(missing_ok=True)
    except OSError:
        return
    pycache = directory / "pycache"
    try:
        pycache.rmdir()
    except OSError:
        pass
    try:
        directory.rmdir()
    except OSError:
        pass


def _stage_runner_and_exec(original: Path) -> None:
    """Re-exec exact frozen runner bytes before loading repository modules."""

    original = _plain_lexical_path(
        original,
        label="stage-zero runner",
        kind="file",
    )
    raw = _stable_preimport_source(original)
    digest = hashlib.sha256(raw).hexdigest()
    root = _plain_lexical_path(
        original.parents[1],
        label="stage-zero repository",
        kind="directory",
    )
    expected = _plain_lexical_path(
        root / ".venv" / "Scripts" / "python.exe"
        if os.name == "nt"
        else root / ".venv" / "bin" / "python",
        label="stage-zero interpreter",
        kind="file",
    )
    try:
        if not os.path.samefile(expected, sys.executable):
            raise RuntimeError(
                "Phase 11 stage zero must use the project .venv interpreter"
            )
    except OSError as exc:
        raise RuntimeError(
            f"Phase 11 project interpreter is unavailable: {exc}"
        ) from exc
    directory = Path(tempfile.mkdtemp(prefix="moira-phase11-runner-"))
    staged = directory / original.name
    try:
        with staged.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        if _stable_preimport_source(staged) != raw:
            raise RuntimeError("Phase 11 frozen runner copy is inconsistent")
        environment = dict(os.environ)
        # Pytest's completion module selects executable module state while it
        # imports.  Phase 11 is an ordinary test run, never a shell-completion
        # process, so remove that mode before the frozen stage imports pytest.
        environment.pop("_ARGCOMPLETE", None)
        environment.update(
            {
                _FROZEN_RUNNER_DIGEST_ENV: digest,
                _FROZEN_RUNNER_ORIGINAL_ENV: str(original),
                _FROZEN_RUNNER_ROOT_ENV: str(root),
                _FROZEN_RUNNER_DIRECTORY_ENV: str(directory),
            }
        )
        argv = [
            str(expected),
            "-I",
            "-P",
            "-B",
            "-S",
            "-X",
            f"pycache_prefix={directory / 'pycache'}",
            str(staged),
            *sys.argv[1:],
        ]
        if os.name != "nt":
            os.execve(str(expected), argv, environment)
            raise RuntimeError("Phase 11 runner exec returned unexpectedly")

        # CPython's Windows ``os.execve`` is not reliable for this venv/path,
        # while ``subprocess.run`` may hard-kill stage one after Ctrl+C.  A
        # dedicated process group plus this non-killing wait loop lets stage
        # one own rollback.  Ctrl+C is forwarded as Ctrl+Break, whose handler
        # below raises KeyboardInterrupt inside stage one.
        import subprocess

        process = subprocess.Popen(
            argv,
            env=environment,
            stdin=None,
            stdout=None,
            stderr=None,
            creationflags=getattr(
                subprocess,
                "CREATE_NEW_PROCESS_GROUP",
                0x00000200,
            ),
        )
        interrupt_forwarded = False
        while True:
            try:
                returncode = process.wait(timeout=0.25)
                raise SystemExit(returncode)
            except subprocess.TimeoutExpired:
                continue
            except KeyboardInterrupt:
                if interrupt_forwarded:
                    continue
                interrupt_forwarded = True
                try:
                    process.send_signal(signal.CTRL_BREAK_EVENT)
                except (OSError, ProcessLookupError):
                    if process.poll() is not None:
                        raise SystemExit(process.returncode)
                continue
    finally:
        # Stage one also attempts this exact cleanup at exit.  Repeating it is
        # harmless and covers a stage-one crash before its atexit registration.
        _remove_staged_runner(directory, staged)


def _admit_executed_runner(
) -> tuple[Path, Path, bytes, bool, Path, Path, bytes]:
    executed = _plain_lexical_path(
        Path(__file__),
        label="executed runner",
        kind="file",
    )
    digest = os.environ.pop(_FROZEN_RUNNER_DIGEST_ENV, None)
    original_text = os.environ.pop(_FROZEN_RUNNER_ORIGINAL_ENV, None)
    root_text = os.environ.pop(_FROZEN_RUNNER_ROOT_ENV, None)
    directory_text = os.environ.pop(_FROZEN_RUNNER_DIRECTORY_ENV, None)
    staged_values = (
        digest,
        original_text,
        root_text,
        directory_text,
    )
    if all(value is None for value in staged_values):
        if __name__ == "__main__":
            _stage_runner_and_exec(executed)
            raise RuntimeError("Phase 11 runner re-exec returned unexpectedly")
        # Import-only policy tests never seal a receipt.  They still bind the
        # exact source bytes they imported before loading local dependencies.
        git_source, git_raw, _helpers = _resolve_reviewed_git_runtime()
        return (
            executed,
            _plain_lexical_path(
                executed.parents[1],
                label="import-only repository",
                kind="directory",
            ),
            _stable_preimport_source(executed),
            False,
            git_source,
            git_source,
            git_raw,
        )
    if not all(isinstance(value, str) and value for value in staged_values):
        raise RuntimeError("Phase 11 frozen-runner admission is incomplete")
    if __name__ != "__main__":
        raise RuntimeError("Phase 11 frozen-runner sentinel reached an import")
    assert isinstance(digest, str)
    assert isinstance(original_text, str)
    assert isinstance(root_text, str)
    assert isinstance(directory_text, str)
    if len(digest) != 64 or any(value not in "0123456789abcdef" for value in digest):
        raise RuntimeError("Phase 11 frozen-runner digest is invalid")
    directory = _plain_lexical_path(
        Path(directory_text),
        label="frozen runner directory",
        kind="directory",
    )
    original = _plain_lexical_path(
        Path(original_text),
        label="logical runner",
        kind="file",
    )
    root = _plain_lexical_path(
        Path(root_text),
        label="frozen repository",
        kind="directory",
    )
    if (
        not directory.name.startswith("moira-phase11-runner-")
        or executed.parent != directory
        or executed.name != original.name
        or original != root / "scripts" / "run_scientific_mutations.py"
    ):
        raise RuntimeError("Phase 11 frozen-runner paths are inconsistent")
    def _interrupt_stage_one_once(
        _signum: int,
        _frame: object,
    ) -> None:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        if hasattr(signal, "SIGBREAK"):
            signal.signal(signal.SIGBREAK, signal.SIG_IGN)
        raise KeyboardInterrupt

    signal.signal(signal.SIGINT, _interrupt_stage_one_once)
    if os.name == "nt" and hasattr(signal, "SIGBREAK"):
        def _interrupt_stage_one(
            _signum: int,
            _frame: object,
        ) -> None:
            signal.signal(signal.SIGBREAK, signal.SIG_IGN)
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            raise KeyboardInterrupt

        signal.signal(signal.SIGBREAK, _interrupt_stage_one)
    directory_metadata = directory.lstat()
    if (
        not stat.S_ISDIR(directory_metadata.st_mode)
        or stat.S_ISLNK(directory_metadata.st_mode)
        or getattr(directory_metadata, "st_file_attributes", 0) & 0x400
    ):
        raise RuntimeError("Phase 11 frozen-runner directory is not plain")
    staged_raw = _stable_preimport_source(executed)
    if hashlib.sha256(staged_raw).hexdigest() != digest:
        raise RuntimeError("Phase 11 executed runner differs from its frozen digest")
    if _stable_preimport_source(original) != staged_raw:
        raise RuntimeError("Phase 11 live runner differs from its executed bytes")
    expected = _plain_lexical_path(
        root / ".venv" / "Scripts" / "python.exe"
        if os.name == "nt"
        else root / ".venv" / "bin" / "python",
        label="frozen interpreter",
        kind="file",
    )
    try:
        if not os.path.samefile(expected, sys.executable):
            raise RuntimeError(
                "Phase 11 frozen runner used a foreign interpreter"
            )
    except OSError as exc:
        raise RuntimeError(
            f"Phase 11 frozen interpreter is unavailable: {exc}"
        ) from exc
    git_source, git_executable, git_raw = _freeze_reviewed_git_runtime(
        directory
    )
    atexit.register(_remove_staged_runner, directory, executed)
    return (
        original,
        root,
        staged_raw,
        True,
        git_source,
        git_executable,
        git_raw,
    )


(
    SCRIPT_PATH,
    ROOT,
    _EXECUTED_RUNNER_BYTES,
    _RUNNER_FROZEN_STAGE_ONE,
    _FROZEN_GIT_SOURCE_EXECUTABLE,
    _FROZEN_GIT_EXECUTABLE,
    _FROZEN_GIT_BYTES,
) = _admit_executed_runner()
TESTS = ROOT / "tests"


def _admitted_parent_import_path(root: Path) -> tuple[str, ...]:
    """Construct the parent path without ``site`` or ``.pth`` processing."""

    import sysconfig

    expected_prefix = _plain_lexical_path(
        root / ".venv",
        label="project venv prefix",
        kind="directory",
    )
    observed_prefix = _plain_lexical_path(
        Path(sys.prefix),
        label="active venv prefix",
        kind="directory",
    )
    if observed_prefix != expected_prefix:
        raise RuntimeError("Phase 11 stage one used a foreign venv prefix")
    base_prefix = _plain_lexical_path(
        Path(sys.base_prefix),
        label="base interpreter prefix",
        kind="directory",
    )
    stdlib_text = sysconfig.get_path("stdlib")
    if not isinstance(stdlib_text, str) or not stdlib_text:
        raise RuntimeError("Phase 11 base stdlib path is unavailable")
    stdlib = _plain_lexical_path(
        Path(stdlib_text),
        label="base stdlib",
        kind="directory",
    )
    try:
        stdlib.relative_to(base_prefix)
    except ValueError as exc:
        raise RuntimeError("Phase 11 base stdlib escapes its prefix") from exc

    allowed_directories = {base_prefix, stdlib}
    if os.name == "nt":
        dlls = base_prefix / "DLLs"
        if dlls.exists():
            allowed_directories.add(
                _plain_lexical_path(
                    dlls,
                    label="base DLL import directory",
                    kind="directory",
                )
            )
    else:
        dynamic = stdlib / "lib-dynload"
        if dynamic.exists():
            allowed_directories.add(
                _plain_lexical_path(
                    dynamic,
                    label="base dynamic import directory",
                    kind="directory",
                )
            )
    expected_zip_names = {
        f"python{sys.version_info[0]}{sys.version_info[1]}.zip",
        f"python{sys.version_info[0]}.{sys.version_info[1]}.zip",
    }
    base_entries: list[str] = []
    seen: set[str] = set()
    for raw_entry in tuple(sys.path):
        if not isinstance(raw_entry, str) or not raw_entry:
            continue
        lexical = Path(os.path.abspath(raw_entry))
        admitted: Path | None = None
        if lexical in allowed_directories:
            admitted = _plain_lexical_path(
                lexical,
                label="base runtime import directory",
                kind="directory",
            )
        elif lexical.name in expected_zip_names and lexical.exists():
            try:
                lexical.relative_to(base_prefix)
            except ValueError:
                continue
            admitted = _plain_lexical_path(
                lexical,
                label="base runtime import archive",
                kind="file",
            )
        if admitted is None:
            continue
        folded = os.path.normcase(os.fspath(admitted))
        if folded in seen:
            raise RuntimeError(
                "Phase 11 base runtime import path contains duplicates"
            )
        seen.add(folded)
        base_entries.append(str(admitted))
    if str(stdlib) not in base_entries:
        raise RuntimeError("Phase 11 base stdlib is absent from sys.path")

    site_packages = _plain_lexical_path(
        (
            expected_prefix / "Lib" / "site-packages"
            if os.name == "nt"
            else expected_prefix
            / "lib"
            / f"python{sys.version_info[0]}.{sys.version_info[1]}"
            / "site-packages"
        ),
        label="project venv site-packages",
        kind="directory",
    )
    if site_packages in allowed_directories:
        raise RuntimeError("Phase 11 venv site-packages aliases the base runtime")
    return (*base_entries, str(site_packages))


sys.path[:] = _admitted_parent_import_path(ROOT)
_CLEAN_STARTUP_IMPORT_PATH = tuple(sys.path)
_PYCACHE_GUARD = tempfile.TemporaryDirectory(prefix="moira-phase11-parent-pycache-")
sys.dont_write_bytecode = True
sys.pycache_prefix = _PYCACHE_GUARD.name
_CRITICAL_MODULE_PREFIXES = (
    "evidence",
    "moira",
    "support",
    "_pytest_plugins",
)
_PRELOADED = sorted(
    name
    for name in sys.modules
    if any(
        name == prefix or name.startswith(prefix + ".")
        for prefix in _CRITICAL_MODULE_PREFIXES
    )
)
if _PRELOADED:
    raise RuntimeError(
        "Phase 11 parent modules were preloaded before local provenance binding: "
        + ", ".join(_PRELOADED)
    )


def _assert_no_moira_parent_modules(stage: str) -> None:
    loaded = sorted(
        name
        for name in sys.modules
        if name == "moira" or name.startswith("moira.")
    )
    if loaded:
        raise RuntimeError(
            "Phase 11 trusted parent loaded forbidden engine modules "
            f"{stage}: " + ", ".join(loaded)
        )


class _MoiraDenyFinder:
    """Permanently deny engine imports inside the trusted parent."""

    @staticmethod
    def find_spec(
        fullname: str,
        _path: object = None,
        _target: object = None,
    ) -> None:
        if fullname == "moira" or fullname.startswith("moira."):
            raise ImportError(
                f"Phase 11 trusted parent denies engine import: {fullname}"
            )
        return None


_MOIRA_DENY_FINDER = _MoiraDenyFinder()
_MOIRA_DENY_FIND_SPEC_CODE = _MoiraDenyFinder.find_spec.__code__
sys.meta_path.insert(0, _MOIRA_DENY_FINDER)


def _assert_moira_deny_finder(stage: str) -> None:
    if (
        not sys.meta_path
        or sys.meta_path[0] is not _MOIRA_DENY_FINDER
        or type(_MOIRA_DENY_FINDER) is not _MoiraDenyFinder
        or _MoiraDenyFinder.find_spec.__code__ is not _MOIRA_DENY_FIND_SPEC_CODE
    ):
        raise RuntimeError(
            f"Phase 11 parent engine-import deny finder changed {stage}"
        )


_CRITICAL_SOURCE_PATHS = {
    "runner": SCRIPT_PATH,
    "evidence_package": TESTS / "evidence" / "__init__.py",
    "plugin_package": TESTS / "_pytest_plugins" / "__init__.py",
    "evidence_schema": TESTS / "_pytest_plugins" / "evidence_schema.py",
    "contracts": TESTS / "evidence" / "contracts.py",
    "support_package": TESTS / "support" / "__init__.py",
    "adjudicator": TESTS / "support" / "mutation_assurance.py",
    "toolchain": TESTS / "support" / "mutation_toolchain.py",
}
_CRITICAL_SOURCE_PATHS = {
    role: _plain_lexical_path(
        path,
        label=f"critical {role} source",
        kind="file",
    )
    for role, path in _CRITICAL_SOURCE_PATHS.items()
}
_PREIMPORT_SOURCE = {
    role: _stable_preimport_source(path)
    for role, path in _CRITICAL_SOURCE_PATHS.items()
}
if _PREIMPORT_SOURCE["runner"] != _EXECUTED_RUNNER_BYTES:
    raise RuntimeError("Phase 11 runner changed before local imports")


class _FrozenSourceLoader:
    """Execute one pre-admitted local source payload without rereading disk."""

    def __init__(
        self,
        *,
        role: str,
        module_name: str,
        source_path: Path,
        source: bytes,
        is_package: bool,
    ) -> None:
        self.role = role
        self.module_name = module_name
        self.source_path = _plain_lexical_path(
            source_path,
            label=f"frozen {role} source",
            kind="file",
        )
        self.source = source
        self._is_package = is_package
        self.loaded_module: ModuleType | None = None

    def create_module(self, _spec: object) -> None:
        return None

    def exec_module(self, module: object) -> None:
        if type(module) is not ModuleType or self.loaded_module is not None:
            raise RuntimeError(
                f"Phase 11 frozen module object is invalid: {self.module_name}"
            )
        self.loaded_module = module
        namespace = getattr(module, "__dict__", None)
        if not isinstance(namespace, dict):
            raise RuntimeError(
                f"Phase 11 frozen module has no namespace: {self.module_name}"
            )
        namespace["__file__"] = str(self.source_path)
        namespace["__cached__"] = None
        if self._is_package:
            # Known children are resolved only by the frozen finder below.
            namespace["__path__"] = []
        code = compile(
            self.source,
            str(self.source_path),
            "exec",
            dont_inherit=True,
            optimize=0,
        )
        exec(code, namespace)

    def get_filename(self, fullname: str) -> str:
        if fullname != self.module_name:
            raise ImportError(f"foreign frozen module request: {fullname}")
        return str(self.source_path)

    def is_package(self, fullname: str) -> bool:
        if fullname != self.module_name:
            raise ImportError(f"foreign frozen package request: {fullname}")
        return self._is_package


class _FrozenLocalFinder:
    def __init__(self, loaders: dict[str, _FrozenSourceLoader]) -> None:
        self.loaders = loaders

    def find_spec(
        self,
        fullname: str,
        _path: object = None,
        _target: object = None,
    ) -> object | None:
        loader = self.loaders.get(fullname)
        if loader is None:
            return None
        return importlib.util.spec_from_loader(
            fullname,
            loader,
            origin=str(loader.source_path),
            is_package=loader.is_package(fullname),
        )


_FROZEN_MODULES = (
    ("evidence_package", "evidence", True),
    ("plugin_package", "_pytest_plugins", True),
    ("evidence_schema", "_pytest_plugins.evidence_schema", False),
    ("contracts", "evidence.contracts", False),
    ("support_package", "support", True),
    ("adjudicator", "support.mutation_assurance", False),
    ("toolchain", "support.mutation_toolchain", False),
)
_FROZEN_LOADERS_BY_ROLE: dict[str, _FrozenSourceLoader] = {}
_FROZEN_LOADERS_BY_NAME: dict[str, _FrozenSourceLoader] = {}
for _role, _module_name, _is_package in _FROZEN_MODULES:
    _loader = _FrozenSourceLoader(
        role=_role,
        module_name=_module_name,
        source_path=_CRITICAL_SOURCE_PATHS[_role],
        source=_PREIMPORT_SOURCE[_role],
        is_package=_is_package,
    )
    _FROZEN_LOADERS_BY_ROLE[_role] = _loader
    _FROZEN_LOADERS_BY_NAME[_module_name] = _loader
_FROZEN_FINDER = _FrozenLocalFinder(_FROZEN_LOADERS_BY_NAME)
sys.meta_path.insert(1, _FROZEN_FINDER)
_FROZEN_IMPORT_RESULTS: dict[str, ModuleType] = {}
try:
    for _imported_name in (
        "evidence.contracts",
        "support.mutation_assurance",
        "_pytest_plugins.evidence_schema",
        "support.mutation_toolchain",
    ):
        _imported_module = importlib.import_module(_imported_name)
        if type(_imported_module) is not ModuleType:
            raise RuntimeError(
                f"Phase 11 frozen import returned a non-module: {_imported_name}"
            )
        _FROZEN_IMPORT_RESULTS[_imported_name] = _imported_module
finally:
    try:
        sys.meta_path.remove(_FROZEN_FINDER)
    except ValueError as exc:
        raise RuntimeError("Phase 11 frozen finder was removed early") from exc
_assert_no_moira_parent_modules("while binding its frozen support closure")
_assert_moira_deny_finder("after binding the frozen support closure")


def _captured_frozen_module(role: str, module_name: str) -> ModuleType:
    loader = _FROZEN_LOADERS_BY_ROLE[role]
    module = loader.loaded_module
    if (
        type(module) is not ModuleType
        or sys.modules.get(module_name) is not module
        or getattr(module, "__name__", None) != module_name
    ):
        raise RuntimeError(
            f"Phase 11 frozen module lost its exact live binding: {module_name}"
        )
    imported = _FROZEN_IMPORT_RESULTS.get(module_name)
    if imported is not None and imported is not module:
        raise RuntimeError(
            f"Phase 11 frozen import returned a replacement: {module_name}"
        )
    return module


_FROZEN_MODULE_OBJECTS_BY_ROLE = {
    role: _captured_frozen_module(role, module_name)
    for role, module_name, _is_package in _FROZEN_MODULES
}
_EVIDENCE_PACKAGE_MODULE = _FROZEN_MODULE_OBJECTS_BY_ROLE["evidence_package"]
_PLUGIN_PACKAGE_MODULE = _FROZEN_MODULE_OBJECTS_BY_ROLE["plugin_package"]
_SCHEMA_MODULE = _FROZEN_MODULE_OBJECTS_BY_ROLE["evidence_schema"]
_CONTRACTS_MODULE = _FROZEN_MODULE_OBJECTS_BY_ROLE["contracts"]
_SUPPORT_PACKAGE_MODULE = _FROZEN_MODULE_OBJECTS_BY_ROLE["support_package"]
_ASSURANCE_MODULE = _FROZEN_MODULE_OBJECTS_BY_ROLE["adjudicator"]
_TOOLCHAIN_MODULE = _FROZEN_MODULE_OBJECTS_BY_ROLE["toolchain"]


def _exact_frozen_function(module: ModuleType, name: str) -> FunctionType:
    value = module.__dict__.get(name)
    if (
        type(value) is not FunctionType
        or value.__module__ != module.__name__
        or value.__name__ != name
        or value.__qualname__ != name
        or value.__globals__ is not module.__dict__
        or hasattr(value, "__wrapped__")
    ):
        raise RuntimeError(
            f"Phase 11 frozen function binding is not exact: {module.__name__}.{name}"
        )
    return value


CONTRACTS = _CONTRACTS_MODULE.__dict__.get("CONTRACTS")
MutationAssuranceError = _ASSURANCE_MODULE.__dict__.get(
    "MutationAssuranceError"
)
GitExecutableIdentity = _ASSURANCE_MODULE.__dict__.get(
    "GitExecutableIdentity"
)
if (
    CONTRACTS is None
    or not isinstance(MutationAssuranceError, type)
    or MutationAssuranceError.__module__ != "support.mutation_assurance"
    or MutationAssuranceError.__name__ != "MutationAssuranceError"
    or not isinstance(GitExecutableIdentity, type)
    or GitExecutableIdentity.__module__ != "support.mutation_assurance"
    or GitExecutableIdentity.__name__ != "GitExecutableIdentity"
):
    raise RuntimeError("Phase 11 frozen scalar aliases are not exact")
_EXACT_CONTRACTS = CONTRACTS
_EXACT_MUTATION_ASSURANCE_ERROR = MutationAssuranceError
_EXACT_GIT_EXECUTABLE_IDENTITY = GitExecutableIdentity
adjudicate_baseline = _exact_frozen_function(
    _ASSURANCE_MODULE, "adjudicate_baseline"
)
adjudicate_mutant = _exact_frozen_function(_ASSURANCE_MODULE, "adjudicate_mutant")
atomically_apply_mutant = _exact_frozen_function(
    _ASSURANCE_MODULE, "atomically_apply_mutant"
)
canonical_json_bytes = _exact_frozen_function(
    _ASSURANCE_MODULE, "canonical_json_bytes"
)
child_argv = _exact_frozen_function(_ASSURANCE_MODULE, "child_argv")
child_environment = _exact_frozen_function(_ASSURANCE_MODULE, "child_environment")
deterministic_mutation_seed = _exact_frozen_function(
    _ASSURANCE_MODULE, "deterministic_mutation_seed"
)
enumerate_snapshot_inputs = _exact_frozen_function(
    _ASSURANCE_MODULE, "enumerate_snapshot_inputs"
)
git_executable_identity = _exact_frozen_function(
    _ASSURANCE_MODULE, "git_executable_identity"
)
git_runtime_copy_state = _exact_frozen_function(
    _ASSURANCE_MODULE, "git_runtime_copy_state"
)
lock_git_runtime_for_execution = _exact_frozen_function(
    _ASSURANCE_MODULE, "lock_git_runtime_for_execution"
)
unlock_git_runtime_for_execution = _exact_frozen_function(
    _ASSURANCE_MODULE, "unlock_git_runtime_for_execution"
)
windows_directory_path = _exact_frozen_function(
    _ASSURANCE_MODULE, "windows_directory_path"
)
execute_child = _exact_frozen_function(_ASSURANCE_MODULE, "execute_child")
load_catalogue = _exact_frozen_function(_ASSURANCE_MODULE, "load_catalogue")
materialize_snapshot = _exact_frozen_function(
    _ASSURANCE_MODULE, "materialize_snapshot"
)
mutation_execution_id = _exact_frozen_function(
    _ASSURANCE_MODULE, "mutation_execution_id"
)
phase11_native_build_identity = _exact_frozen_function(
    _ASSURANCE_MODULE, "phase11_native_build_identity"
)
_require_exact_startup_import_path = _exact_frozen_function(
    _ASSURANCE_MODULE, "_require_exact_startup_import_path"
)
project_interpreter_identity = _exact_frozen_function(
    _ASSURANCE_MODULE, "project_interpreter_identity"
)
standalone_lru_runtime_context = _exact_frozen_function(
    _TOOLCHAIN_MODULE, "standalone_lru_runtime_context"
)
seal_adjudication_record = _exact_frozen_function(
    _ASSURANCE_MODULE, "seal_adjudication_record"
)
seal_mutation_receipt = _exact_frozen_function(
    _ASSURANCE_MODULE, "seal_mutation_receipt"
)
validate_mutation_receipt = _exact_frozen_function(
    _ASSURANCE_MODULE, "validate_mutation_receipt"
)
verify_snapshot = _exact_frozen_function(_ASSURANCE_MODULE, "verify_snapshot")

_EXACT_ASSURANCE_ALIASES = {
    name: globals()[name]
    for name in (
        "adjudicate_baseline",
        "adjudicate_mutant",
        "atomically_apply_mutant",
        "canonical_json_bytes",
        "child_argv",
        "child_environment",
        "deterministic_mutation_seed",
        "enumerate_snapshot_inputs",
        "git_executable_identity",
        "git_runtime_copy_state",
        "lock_git_runtime_for_execution",
        "unlock_git_runtime_for_execution",
        "windows_directory_path",
        "execute_child",
        "load_catalogue",
        "materialize_snapshot",
        "mutation_execution_id",
        "phase11_native_build_identity",
        "_require_exact_startup_import_path",
        "project_interpreter_identity",
        "seal_adjudication_record",
        "seal_mutation_receipt",
        "validate_mutation_receipt",
        "verify_snapshot",
    )
}
_EXACT_ASSURANCE_CODES = {
    name: function.__code__
    for name, function in _EXACT_ASSURANCE_ALIASES.items()
}
_EXACT_TOOLCHAIN_ALIASES = {
    "standalone_lru_runtime_context": standalone_lru_runtime_context,
}
_EXACT_TOOLCHAIN_CODES = {
    name: function.__code__
    for name, function in _EXACT_TOOLCHAIN_ALIASES.items()
}
_FROZEN_STANDALONE_LRU_RUNTIME_CONTEXT = (
    standalone_lru_runtime_context()
)

_FROZEN_GIT_IDENTITY = git_executable_identity(
    _FROZEN_GIT_SOURCE_EXECUTABLE
)
if (
    type(_FROZEN_GIT_IDENTITY) is not GitExecutableIdentity
    or _FROZEN_GIT_IDENTITY.path != str(_FROZEN_GIT_SOURCE_EXECUTABLE)
    or _FROZEN_GIT_IDENTITY.bytes != len(_FROZEN_GIT_BYTES)
    or _FROZEN_GIT_IDENTITY.sha256
    != hashlib.sha256(_FROZEN_GIT_BYTES).hexdigest()
):
    raise RuntimeError("Phase 11 frozen Git identity is inconsistent")
_FROZEN_GIT_RUNTIME_STATE = git_runtime_copy_state(
    _FROZEN_GIT_EXECUTABLE,
    _FROZEN_GIT_IDENTITY,
    private_copy=_RUNNER_FROZEN_STAGE_ONE,
)


def _make_frozen_git_guard(
    source: Path,
    executable: Path,
    raw: bytes,
    identity: object,
    runtime_state: str,
    identity_function: FunctionType,
    runtime_state_function: FunctionType,
    stable_reader: FunctionType,
    private_copy: bool,
):
    """Capture Git admission objects outside mutable module aliases."""

    def guard(stage: str) -> None:
        if (
            globals().get("_FROZEN_GIT_SOURCE_EXECUTABLE") is not source
            or globals().get("_FROZEN_GIT_EXECUTABLE") is not executable
            or globals().get("_FROZEN_GIT_BYTES") is not raw
            or globals().get("_FROZEN_GIT_IDENTITY") is not identity
            or globals().get("_FROZEN_GIT_RUNTIME_STATE") is not runtime_state
            or globals().get("git_executable_identity") is not identity_function
            or globals().get("git_runtime_copy_state")
            is not runtime_state_function
        ):
            raise RuntimeError(
                f"Phase 11 frozen Git binding aliases changed {stage}"
            )
        if identity_function(source) != identity:
            raise RuntimeError(
                f"Phase 11 reviewed Git source changed {stage}"
            )
        if stable_reader(executable) != raw:
            raise RuntimeError(
                f"Phase 11 private Git executable changed {stage}"
            )
        if runtime_state_function(
            executable,
            identity,
            private_copy=private_copy,
        ) != runtime_state:
            raise RuntimeError(
                f"Phase 11 private Git runtime changed {stage}"
            )

    return guard


_FROZEN_GIT_GUARD = _make_frozen_git_guard(
    _FROZEN_GIT_SOURCE_EXECUTABLE,
    _FROZEN_GIT_EXECUTABLE,
    _FROZEN_GIT_BYTES,
    _FROZEN_GIT_IDENTITY,
    _FROZEN_GIT_RUNTIME_STATE,
    git_executable_identity,
    git_runtime_copy_state,
    _stable_preimport_source,
    _RUNNER_FROZEN_STAGE_ONE,
)


def _assert_frozen_live_bindings(
    stage: str,
    _git_guard=_FROZEN_GIT_GUARD,
) -> None:
    _assert_no_moira_parent_modules(stage)
    _assert_moira_deny_finder(stage)
    if tuple(sys.path) != _CLEAN_STARTUP_IMPORT_PATH:
        raise RuntimeError(f"Phase 11 parent import path changed {stage}")
    for role, module_name, _is_package in _FROZEN_MODULES:
        expected = _FROZEN_MODULE_OBJECTS_BY_ROLE[role]
        loader = _FROZEN_LOADERS_BY_ROLE[role]
        if (
            loader.loaded_module is not expected
            or sys.modules.get(module_name) is not expected
        ):
            raise RuntimeError(
                f"Phase 11 frozen module live binding changed {stage}: {module_name}"
            )
    package_children = (
        (_EVIDENCE_PACKAGE_MODULE, "contracts", _CONTRACTS_MODULE),
        (_PLUGIN_PACKAGE_MODULE, "evidence_schema", _SCHEMA_MODULE),
        (_SUPPORT_PACKAGE_MODULE, "mutation_assurance", _ASSURANCE_MODULE),
        (_SUPPORT_PACKAGE_MODULE, "mutation_toolchain", _TOOLCHAIN_MODULE),
    )
    for package, name, expected in package_children:
        if package.__dict__.get(name) is not expected:
            raise RuntimeError(
                f"Phase 11 frozen package child binding changed {stage}: {name}"
            )
    if (
        globals().get("CONTRACTS") is not _EXACT_CONTRACTS
        or _CONTRACTS_MODULE.__dict__.get("CONTRACTS") is not _EXACT_CONTRACTS
        or globals().get("MutationAssuranceError")
        is not _EXACT_MUTATION_ASSURANCE_ERROR
        or _ASSURANCE_MODULE.__dict__.get("MutationAssuranceError")
        is not _EXACT_MUTATION_ASSURANCE_ERROR
        or globals().get("GitExecutableIdentity")
        is not _EXACT_GIT_EXECUTABLE_IDENTITY
        or _ASSURANCE_MODULE.__dict__.get("GitExecutableIdentity")
        is not _EXACT_GIT_EXECUTABLE_IDENTITY
    ):
        raise RuntimeError(f"Phase 11 frozen scalar alias changed {stage}")
    for name, expected in _EXACT_ASSURANCE_ALIASES.items():
        if (
            globals().get(name) is not expected
            or _ASSURANCE_MODULE.__dict__.get(name) is not expected
            or type(expected) is not FunctionType
            or expected.__module__ != "support.mutation_assurance"
            or expected.__globals__ is not _ASSURANCE_MODULE.__dict__
            or expected.__code__ is not _EXACT_ASSURANCE_CODES[name]
            or hasattr(expected, "__wrapped__")
        ):
            raise RuntimeError(
                f"Phase 11 frozen callable binding changed {stage}: {name}"
            )
    for name, expected in _EXACT_TOOLCHAIN_ALIASES.items():
        if (
            globals().get(name) is not expected
            or _TOOLCHAIN_MODULE.__dict__.get(name) is not expected
            or type(expected) is not FunctionType
            or expected.__module__ != "support.mutation_toolchain"
            or expected.__globals__ is not _TOOLCHAIN_MODULE.__dict__
            or expected.__code__ is not _EXACT_TOOLCHAIN_CODES[name]
            or hasattr(expected, "__wrapped__")
            or expected() is not _FROZEN_STANDALONE_LRU_RUNTIME_CONTEXT
        ):
            raise RuntimeError(
                f"Phase 11 frozen toolchain callable changed {stage}: {name}"
            )
    _git_guard(stage)


_assert_frozen_live_bindings("after frozen alias binding")
_CAPTURED_RUNNER_MODULE = sys.modules.get(__name__)


def _admit_frozen_parent_action(action: str) -> None:
    if (
        not _RUNNER_FROZEN_STAGE_ONE
        or __name__ != "__main__"
        or type(_CAPTURED_RUNNER_MODULE) is not ModuleType
        or sys.modules.get("__main__") is not _CAPTURED_RUNNER_MODULE
    ):
        raise RuntimeError(
            f"Phase 11 {action} requires exact frozen stage-one execution"
        )
    if (
        sys.flags.isolated != 1
        or sys.flags.safe_path is not True
        or sys.flags.no_site != 1
        or sys.flags.no_user_site != 1
        or sys.flags.ignore_environment != 1
        or sys.flags.dont_write_bytecode != 1
        or sys.dont_write_bytecode is not True
    ):
        raise RuntimeError(
            f"Phase 11 {action} lacks isolated -I -P -B -S startup"
        )
    if "site" in sys.modules or "sitecustomize" in sys.modules or "usercustomize" in sys.modules:
        raise RuntimeError(
            f"Phase 11 {action} loaded a forbidden site startup module"
        )
    _assert_frozen_live_bindings(f"before {action}")
    if _stable_preimport_source(SCRIPT_PATH) != _EXECUTED_RUNNER_BYTES:
        raise RuntimeError(f"Phase 11 logical runner changed before {action}")
    executed = _plain_lexical_path(
        Path(__file__),
        label=f"executed runner before {action}",
        kind="file",
    )
    if _stable_preimport_source(executed) != _EXECUTED_RUNNER_BYTES:
        raise RuntimeError(f"Phase 11 executed runner changed before {action}")


CATALOGUE_PATH = TESTS / "mutations" / "catalogue.json"
ARTIFACT_ROOT = ROOT / ".pytest_cache" / "moira-mutation-artifacts"


def _parent_module_receipt(
    *,
    role: str,
    module_name: str,
    expected_path: Path,
    module: object | None,
) -> dict[str, object]:
    resolved = _plain_lexical_path(
        expected_path,
        label=f"parent {role} source",
        kind="file",
    )
    relative = resolved.relative_to(ROOT).as_posix()
    if module is not None:
        loaded_file = _plain_lexical_path(
            Path(str(getattr(module, "__file__", ""))),
            label=f"loaded parent {role} source",
            kind="file",
        )
        specification = getattr(module, "__spec__", None)
        origin = _plain_lexical_path(
            Path(str(getattr(specification, "origin", ""))),
            label=f"parent {role} module origin",
            kind="file",
        )
        loader = getattr(specification, "loader", None)
        module_loader = getattr(module, "__loader__", None)
        loader_path = getattr(loader, "path", None)
        try:
            loader_filename = loader.get_filename(module_name)
        except (AttributeError, ImportError, OSError, TypeError, ValueError) as exc:
            raise RuntimeError(
                f"Phase 11 parent {role} loader identity is unavailable"
            ) from exc
        if (
            loaded_file != resolved
            or origin != resolved
            or type(loader) is not _FrozenSourceLoader
            or module_loader is not loader
            or loader is not _FROZEN_LOADERS_BY_ROLE.get(role)
            or loader.role != role
            or loader.module_name != module_name
            or loader.source_path != resolved
            or loader.source != _PREIMPORT_SOURCE.get(role)
            or loader_path is not None
            or not isinstance(loader_filename, str)
            or _plain_lexical_path(
                Path(loader_filename),
                label=f"parent {role} loader filename",
                kind="file",
            )
            != resolved
        ):
            raise RuntimeError(f"Phase 11 parent {role} module is foreign")
        cached = getattr(module, "__cached__", None)
        if cached is not None:
            raise RuntimeError(
                f"Phase 11 frozen parent {role} unexpectedly names bytecode"
            )
    raw = _stable_preimport_source(resolved)
    if raw != _PREIMPORT_SOURCE.get(role):
        raise RuntimeError(
            f"Phase 11 parent {role} source changed across its import"
        )
    if role == "runner" and raw != _EXECUTED_RUNNER_BYTES:
        raise RuntimeError(
            "Phase 11 parent runner source differs from executed frozen bytes"
        )
    return {
        "role": role,
        "module_name": module_name,
        "path": relative,
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _parent_runtime_receipt() -> dict[str, object]:
    _admit_frozen_parent_action("parent runtime receipt")
    modules = [
        _parent_module_receipt(
            role="runner",
            module_name="__main__",
            expected_path=SCRIPT_PATH,
            module=None,
        ),
        _parent_module_receipt(
            role="evidence_package",
            module_name="evidence",
            expected_path=TESTS / "evidence" / "__init__.py",
            module=_EVIDENCE_PACKAGE_MODULE,
        ),
        _parent_module_receipt(
            role="plugin_package",
            module_name="_pytest_plugins",
            expected_path=TESTS / "_pytest_plugins" / "__init__.py",
            module=_PLUGIN_PACKAGE_MODULE,
        ),
        _parent_module_receipt(
            role="evidence_schema",
            module_name="_pytest_plugins.evidence_schema",
            expected_path=TESTS / "_pytest_plugins" / "evidence_schema.py",
            module=_SCHEMA_MODULE,
        ),
        _parent_module_receipt(
            role="contracts",
            module_name="evidence.contracts",
            expected_path=TESTS / "evidence" / "contracts.py",
            module=_CONTRACTS_MODULE,
        ),
        _parent_module_receipt(
            role="support_package",
            module_name="support",
            expected_path=TESTS / "support" / "__init__.py",
            module=_SUPPORT_PACKAGE_MODULE,
        ),
        _parent_module_receipt(
            role="adjudicator",
            module_name="support.mutation_assurance",
            expected_path=TESTS / "support" / "mutation_assurance.py",
            module=_ASSURANCE_MODULE,
        ),
        _parent_module_receipt(
            role="toolchain",
            module_name="support.mutation_toolchain",
            expected_path=TESTS / "support" / "mutation_toolchain.py",
            module=_TOOLCHAIN_MODULE,
        ),
    ]
    return {
        "module_import_policy": (
            "frozen_stage_one_no_preload_isolated_empty_pycache_no_write"
        ),
        "modules": modules,
    }


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _default_run_id() -> str:
    return datetime.now(UTC).strftime("phase11-%Y%m%dT%H%M%SZ")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the complete curated Phase 11 scientific mutation pack in "
            "fresh plain-file snapshots."
        )
    )
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument(
        "--check-catalogue",
        action="store_true",
        help="Validate catalogue, source, AST, code, and contract bindings only.",
    )
    actions.add_argument(
        "--verify-receipt",
        type=Path,
        help="Validate an existing receipt and require a green mutation gate.",
    )
    actions.add_argument(
        "--emit-interpreter-identity",
        action="store_true",
        help="Emit the frozen standalone interpreter identity as canonical JSON.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Portable receipt directory name; defaults to a UTC Phase 11 ID.",
    )
    return parser.parse_args(argv)


def _blocked_mutant(spec, baseline: dict[str, object]) -> dict[str, object]:
    return seal_adjudication_record({
        "fault_archetype": spec.fault_archetype,
        "mutant_id": spec.mutant_id,
        "criticality": spec.criticality,
        "expected_killing_test_claim": {
            "nodeid": spec.intended_killer_nodeid,
            "claim_id": spec.expected_claim_id,
            "contract_sha256": spec.expected_contract_sha256,
        },
        "actual_killing_test": None,
        "evidence_class": spec.evidence_class,
        "outcome": "blocked_baseline",
        "gate_credit": False,
        "reasons": [
            "unmutated intended-killer baseline was not admitted",
            *[str(value) for value in baseline.get("reasons", [])],
        ],
        "source_mutation": {
            "source_path": spec.source_path,
            "target_qualname": spec.target_qualname,
            "operator": spec.operator,
            "source_hash_mode": spec.source_hash_mode,
            "preimage_sha256": spec.preimage_sha256,
            "postimage_sha256": spec.postimage_sha256,
            "preimage_ast_sha256": spec.preimage_ast_sha256,
            "postimage_ast_sha256": spec.postimage_ast_sha256,
            "preimage_code_sha256": spec.preimage_code_sha256,
            "postimage_code_sha256": spec.postimage_code_sha256,
            "patch_sha256": spec.patch_sha256,
            "runtime_source_sha256": None,
        },
        "intended_test_source": baseline.get("intended_test_source"),
        "process": None,
        "child_report": None,
        "exclusions": list(spec.exclusions),
    })


def _run(args: argparse.Namespace) -> int:
    _admit_frozen_parent_action("mutation runner action")
    _assert_frozen_live_bindings("before catalogue validation")
    if args.emit_interpreter_identity:
        if args.run_id is not None:
            raise MutationAssuranceError(
                "identity-only action forbids a mutation receipt run ID"
            )
        interpreter = project_interpreter_identity(
            ROOT,
            startup_import_path=_CLEAN_STARTUP_IMPORT_PATH,
            lru_runtime_context=_FROZEN_STANDALONE_LRU_RUNTIME_CONTEXT,
        )
        _assert_frozen_live_bindings("after interpreter identity")
        raw_identity = canonical_json_bytes(interpreter)
        _assert_frozen_live_bindings("after interpreter identity serialization")
        sys.stdout.buffer.write(raw_identity)
        sys.stdout.buffer.flush()
        return 0
    catalogue = load_catalogue(
        CATALOGUE_PATH,
        root=ROOT,
        contracts=CONTRACTS,
        verify_sources=True,
    )
    _assert_frozen_live_bindings("after catalogue validation")
    if args.check_catalogue:
        print(
            f"catalogue ok: {len(catalogue.mutants)} mutants, "
            f"sha256={catalogue.sha256}"
        )
        return 0
    if args.verify_receipt is not None:
        receipt = args.verify_receipt
        if not receipt.is_absolute():
            receipt = ROOT / receipt
        current_interpreter = project_interpreter_identity(
            ROOT,
            startup_import_path=_CLEAN_STARTUP_IMPORT_PATH,
            lru_runtime_context=_FROZEN_STANDALONE_LRU_RUNTIME_CONTEXT,
        )
        current_snapshot = enumerate_snapshot_inputs(
            ROOT,
            git_executable=_FROZEN_GIT_IDENTITY,
            git_invocation_path=_FROZEN_GIT_EXECUTABLE,
        )
        _assert_frozen_live_bindings("after receipt snapshot enumeration")
        current_native_build = (
            phase11_native_build_identity(ROOT, current_snapshot, catalogue)
            if getattr(catalogue, "mutants", None) is not None
            else None
        )
        _assert_frozen_live_bindings("after receipt native-build admission")
        run = validate_mutation_receipt(
            receipt.resolve(strict=True),
            current_catalogue=catalogue,
            current_snapshot=current_snapshot,
            current_interpreter=current_interpreter,
            current_native_build=current_native_build,
            require_green=True,
        )
        _assert_frozen_live_bindings("after receipt validation")
        current_snapshot_after = enumerate_snapshot_inputs(
            ROOT,
            git_executable=_FROZEN_GIT_IDENTITY,
            git_invocation_path=_FROZEN_GIT_EXECUTABLE,
        )
        current_interpreter_after = project_interpreter_identity(
            ROOT,
            startup_import_path=_CLEAN_STARTUP_IMPORT_PATH,
            lru_runtime_context=_FROZEN_STANDALONE_LRU_RUNTIME_CONTEXT,
        )
        current_native_build_after = (
            phase11_native_build_identity(
                ROOT,
                current_snapshot_after,
                catalogue,
            )
            if getattr(catalogue, "mutants", None) is not None
            else None
        )
        _assert_frozen_live_bindings(
            "after post-validation identity enumeration"
        )
        if (
            current_snapshot_after != current_snapshot
            or current_interpreter_after != current_interpreter
            or current_native_build_after != current_native_build
        ):
            raise MutationAssuranceError(
                "current checkout identity changed during receipt verification"
            )
        print(
            f"mutation receipt green: {run['run_id']} "
            f"({run['summary']['killed_intended']}/"
            f"{run['summary']['declared']} killed intended)"
        )
        return 0

    interpreter = project_interpreter_identity(
        ROOT,
        startup_import_path=_CLEAN_STARTUP_IMPORT_PATH,
        lru_runtime_context=_FROZEN_STANDALONE_LRU_RUNTIME_CONTEXT,
    )
    parent_runtime = _parent_runtime_receipt()
    frozen_inputs = enumerate_snapshot_inputs(
        ROOT,
        git_executable=_FROZEN_GIT_IDENTITY,
        git_invocation_path=_FROZEN_GIT_EXECUTABLE,
    )
    _assert_frozen_live_bindings("after mutation snapshot enumeration")
    native_build = phase11_native_build_identity(
        ROOT,
        frozen_inputs,
        catalogue,
    )
    _assert_frozen_live_bindings("after mutation native-build admission")

    def require_current_identity(stage: str) -> None:
        _assert_frozen_live_bindings(f"before identity check {stage}")
        current_snapshot = enumerate_snapshot_inputs(
            ROOT,
            git_executable=_FROZEN_GIT_IDENTITY,
            git_invocation_path=_FROZEN_GIT_EXECUTABLE,
        )
        current_interpreter = project_interpreter_identity(
            ROOT,
            startup_import_path=_CLEAN_STARTUP_IMPORT_PATH,
            lru_runtime_context=_FROZEN_STANDALONE_LRU_RUNTIME_CONTEXT,
        )
        current_native_build = phase11_native_build_identity(
            ROOT,
            current_snapshot,
            catalogue,
        )
        if (
            current_snapshot != frozen_inputs
            or current_interpreter != interpreter
            or current_native_build != native_build
        ):
            raise MutationAssuranceError(
                f"current checkout identity changed {stage}"
            )
        _assert_frozen_live_bindings(f"after identity check {stage}")

    require_current_identity("during native-build admission")
    native_identity = frozen_inputs.by_path.get(
        frozen_inputs.native_backend_path
    )
    if native_identity is None:
        raise MutationAssuranceError(
            "loaded native backend is absent from the frozen snapshot"
        )
    run_id = args.run_id or _default_run_id()
    started = _utc_now()
    baselines: list[dict[str, object]] = []
    results: list[dict[str, object]] = []

    for spec in catalogue.mutants:
        seed = deterministic_mutation_seed(spec.mutant_id)
        short = hashlib.sha256(spec.mutant_id.encode("ascii")).hexdigest()[:12]
        with tempfile.TemporaryDirectory(
            prefix=f"moira-phase11-{short}-"
        ) as temporary_text:
            temporary = Path(temporary_text)
            snapshot = temporary / "snapshot"
            control = temporary / "control"
            reports = control / "reports"
            control.mkdir()
            reports.mkdir()
            materialize_snapshot(ROOT, snapshot, frozen_inputs)
            environment = child_environment(snapshot, seed=seed)
            native_path = snapshot / Path(frozen_inputs.native_backend_path)

            baseline_id = mutation_execution_id(spec, "baseline")
            baseline_report = reports / f"{baseline_id}.json"
            baseline_observation = execute_child(
                argv=child_argv(
                    interpreter=str(interpreter["executable"]),
                    snapshot_root=snapshot,
                    control_root=control,
                    spec=spec,
                    execution_id=baseline_id,
                    report_path=baseline_report,
                ),
                cwd=snapshot,
                environment=environment,
                timeout_seconds=spec.timeout_seconds,
                report_path=baseline_report,
            )
            verify_snapshot(snapshot, frozen_inputs)
            baseline = adjudicate_baseline(
                spec=spec,
                observation=baseline_observation,
                execution_id=baseline_id,
                snapshot_root=snapshot,
                interpreter=interpreter,
                native_backend_path=native_path,
                native_backend_sha256=native_identity.sha256,
            )
            baselines.append(baseline)
            if baseline["outcome"] != "baseline_passed":
                results.append(_blocked_mutant(spec, baseline))
                print(f"{spec.mutant_id}: blocked_baseline")
                continue

            mutated_source = atomically_apply_mutant(snapshot, frozen_inputs, spec)
            mutated_source_sha256 = hashlib.sha256(mutated_source).hexdigest()
            mutant_id = mutation_execution_id(spec, "mutant")
            mutant_report = reports / f"{mutant_id}.json"
            mutant_observation = execute_child(
                argv=child_argv(
                    interpreter=str(interpreter["executable"]),
                    snapshot_root=snapshot,
                    control_root=control,
                    spec=spec,
                    execution_id=mutant_id,
                    report_path=mutant_report,
                ),
                cwd=snapshot,
                environment=environment,
                timeout_seconds=spec.timeout_seconds,
                report_path=mutant_report,
            )
            verify_snapshot(
                snapshot,
                frozen_inputs,
                overrides={spec.source_path: mutated_source_sha256},
            )
            result = adjudicate_mutant(
                spec=spec,
                observation=mutant_observation,
                execution_id=mutant_id,
                snapshot_root=snapshot,
                interpreter=interpreter,
                native_backend_path=native_path,
                native_backend_sha256=native_identity.sha256,
            )
            results.append(result)
            print(f"{spec.mutant_id}: {result['outcome']}")

    # Refuse to seal if the live checkout changed while the pack was running.
    require_current_identity("during the mutation run")
    receipt = seal_mutation_receipt(
        artifact_root=ARTIFACT_ROOT,
        run_id=run_id,
        catalogue=catalogue,
        snapshot=frozen_inputs,
        interpreter=interpreter,
        parent_runtime=parent_runtime,
        baselines=baselines,
        mutants=results,
        started_utc=started,
        finished_utc=_utc_now(),
        native_build=native_build,
        pre_publish_check=lambda: require_current_identity(
            "before receipt publication"
        ),
    )
    green = all(result["outcome"] == "killed_intended" for result in results)
    print(f"receipt: {receipt}")
    print(f"gate: {'passed' if green else 'failed'} ({sum(r['outcome'] == 'killed_intended' for r in results)}/{len(results)})")
    return 0 if green else 1


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        return _run(args)
    except MutationAssuranceError as exc:
        print(f"Phase 11 mutation assurance failed closed: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print(
            "Phase 11 mutation assurance interrupted; no completion is claimed. "
            "Inspect the mutation artifact root for committed or incomplete state.",
            file=sys.stderr,
        )
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
