"""Adversarial canaries for the Phase 11 trusted-parent engine boundary."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest

from support.mutation_assurance import (
    MutationAssuranceError,
    _native_backend_relative_path,
    _native_build_input_manifest,
    _native_extension_suffixes,
    enumerate_snapshot_inputs,
    git_executable_identity,
    phase11_native_build_identity,
)


pytestmark = pytest.mark.parallel(reason="isolated_resources")


_ROOT = Path(__file__).resolve().parents[2]
_RUNNER = _ROOT / "scripts" / "run_scientific_mutations.py"
if os.name == "nt":
    _GIT_CANDIDATES = (
        Path(Path(sys.executable).anchor)
        / "Program Files"
        / "Git"
        / "mingw64"
        / "libexec"
        / "git-core"
        / "git.exe",
        Path(Path(sys.executable).anchor)
        / "Program Files (x86)"
        / "Git"
        / "mingw64"
        / "libexec"
        / "git-core"
        / "git.exe",
    )
else:
    _GIT_CANDIDATES = (
        Path("/usr/bin/git"),
        Path("/usr/local/bin/git"),
        Path("/opt/homebrew/bin/git"),
    )
_PRESENT_GIT_CANDIDATES = tuple(
    path for path in _GIT_CANDIDATES if path.is_file()
)
assert len(_PRESENT_GIT_CANDIDATES) == 1
_GIT_IDENTITY = git_executable_identity(_PRESENT_GIT_CANDIDATES[0])


def _write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


def _native_catalogue() -> SimpleNamespace:
    return SimpleNamespace(
        mutants=(
            SimpleNamespace(
                mutant_id="P11-PARENT-ISOLATION-CANARY",
                evidence_class="native_parity",
                requires_native_backend=True,
            ),
        )
    )


def _synthetic_repository(
    root: Path,
    *,
    package_source: bytes,
    provenance_source: bytes,
    marker_copies: int = 1,
) -> tuple[Path, str]:
    subprocess.run(
        ("git", "init", "--quiet", str(root)),
        check=True,
        capture_output=True,
        timeout=15,
    )
    _write(root / "CMakeLists.txt", b"project(parent_isolation LANGUAGES CXX)\n")
    _write(root / "setup.py", b"# synthetic native build driver\n")
    _write(
        root / "pyproject.toml",
        b"[build-system]\n"
        b"requires = []\n"
        b"build-backend = \"synthetic\"\n\n"
        b"[tool.setuptools]\n"
        b"packages = [\"moira\"]\n\n"
        b"[tool.setuptools.package-data]\n"
        b"moira = [\"*.pyd\", \"*.so\"]\n",
    )
    _write(root / "scripts" / "run_scientific_mutations.py", b"# runner\n")
    _write(root / "moira" / "__init__.py", package_source)
    _write(
        root / "moira" / "_native_build_provenance.py",
        provenance_source,
    )
    _write(root / "src" / "native" / "include" / "probe.hpp", b"// input\n")
    manifest = _native_build_input_manifest(root)
    digest = str(manifest["sha256"])
    marker = (
        b"MOIRA_NATIVE_BUILD_INPUT_MANIFEST_SHA256="
        + digest.encode("ascii")
    )
    suffix = _native_extension_suffixes()[0]
    relative = f"moira/_moira_native{suffix}"
    _write(
        root / Path(relative),
        b"synthetic-native-prefix\0"
        + b"\0".join(marker for _ in range(marker_copies))
        + b"\0synthetic-native-suffix",
    )
    return root, relative


def test_snapshot_enumeration_ignores_a_hostile_path_git_shim(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "hostile-path-repository"
    repository.mkdir()
    _synthetic_repository(
        repository,
        package_source=b"# inert package\n",
        provenance_source=b"# inert provenance declaration\n",
    )
    shim_directory = tmp_path / "hostile-path"
    shim_directory.mkdir()
    shim = shim_directory / ("git.exe" if os.name == "nt" else "git")
    shutil.copyfile(sys.executable, shim)
    shim.chmod(0o755)
    monkeypatch.setenv(
        "PATH",
        str(shim_directory) + os.pathsep + os.environ.get("PATH", ""),
    )

    snapshot = enumerate_snapshot_inputs(
        repository,
        git_executable=_GIT_IDENTITY,
    )

    assert snapshot.git_executable == _GIT_IDENTITY
    assert "moira/__init__.py" in snapshot.by_path


def test_snapshot_enumeration_ignores_ambient_git_exclude_policy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "hostile-git-config-repository"
    repository.mkdir()
    _synthetic_repository(
        repository,
        package_source=b"# inert package\n",
        provenance_source=b"# inert provenance declaration\n",
    )
    hidden = repository / "moira" / "hidden.py"
    hidden.write_bytes(b"# must remain in the frozen snapshot\n")
    excludes = tmp_path / "ambient-global-excludes"
    excludes.write_text("moira/hidden.py\n", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.excludesFile")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", str(excludes))
    monkeypatch.setenv("HOME", str(tmp_path / "hostile-home"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "hostile-xdg"))

    snapshot = enumerate_snapshot_inputs(
        repository,
        git_executable=_GIT_IDENTITY,
    )

    assert "moira/hidden.py" in snapshot.by_path


def test_stage_zero_git_selection_ignores_a_hostile_path_shim(
    tmp_path: Path,
) -> None:
    shim_directory = tmp_path / "hostile-stage-zero-path"
    shim_directory.mkdir()
    shim = shim_directory / ("git.exe" if os.name == "nt" else "git")
    shutil.copyfile(sys.executable, shim)
    shim.chmod(0o755)
    probe = f"""
import importlib.util
from pathlib import Path

specification = importlib.util.spec_from_file_location(
    "phase11_stage_zero_git_probe", Path({str(_RUNNER)!r})
)
assert specification is not None and specification.loader is not None
runner = importlib.util.module_from_spec(specification)
specification.loader.exec_module(runner)
assert Path(runner._FROZEN_GIT_IDENTITY.path) != Path({str(shim)!r})
"""
    environment = dict(os.environ)
    environment["PATH"] = str(shim_directory)

    completed = subprocess.run(
        [sys.executable, "-I", "-P", "-B", "-S", "-c", probe],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
        timeout=60,
    )

    assert completed.returncode == 0, (
        f"stage zero admitted PATH Git; stdout={completed.stdout!r}; "
        f"stderr={completed.stderr!r}"
    )


def test_frozen_git_triple_rebind_is_rejected(
    tmp_path: Path,
) -> None:
    forged = tmp_path / ("forged-git.exe" if os.name == "nt" else "forged-git")
    shutil.copyfile(sys.executable, forged)
    forged.chmod(0o755)
    probe = f"""
import importlib.util
from pathlib import Path

specification = importlib.util.spec_from_file_location(
    "phase11_forged_git_triple_probe", Path({str(_RUNNER)!r})
)
assert specification is not None and specification.loader is not None
runner = importlib.util.module_from_spec(specification)
specification.loader.exec_module(runner)
original = (
    runner._FROZEN_GIT_EXECUTABLE,
    runner._FROZEN_GIT_BYTES,
    runner._FROZEN_GIT_IDENTITY,
)
forged = Path({str(forged)!r})
runner._FROZEN_GIT_EXECUTABLE = forged
runner._FROZEN_GIT_BYTES = forged.read_bytes()
runner._FROZEN_GIT_IDENTITY = runner.git_executable_identity(forged)
try:
    runner._assert_frozen_live_bindings("forged Git triple canary")
except RuntimeError:
    pass
else:
    raise AssertionError("FORGED_GIT_TRIPLE_ACCEPTED")
finally:
    (
        runner._FROZEN_GIT_EXECUTABLE,
        runner._FROZEN_GIT_BYTES,
        runner._FROZEN_GIT_IDENTITY,
    ) = original
runner._assert_frozen_live_bindings("after forged Git triple restoration")
"""

    completed = subprocess.run(
        [sys.executable, "-I", "-P", "-B", "-S", "-c", probe],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert completed.returncode == 0, (
        f"forged Git triple was admitted; stdout={completed.stdout!r}; "
        f"stderr={completed.stderr!r}"
    )


@pytest.mark.skipif(os.name != "nt", reason="requires Windows share-mode locks")
def test_private_git_runtime_cannot_be_replaced_or_written_during_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import support.mutation_assurance as mutation_assurance

    repository = tmp_path / "git-replacement-repository"
    repository.mkdir()
    _synthetic_repository(
        repository,
        package_source=b"# inert package\n",
        provenance_source=b"# inert provenance declaration\n",
    )
    runtime = tmp_path / "private-git-runtime"
    runtime.mkdir()
    source_directory = Path(_GIT_IDENTITY.path).parent
    for identity in _GIT_IDENTITY.runtime_files:
        shutil.copyfile(
            source_directory / identity.path,
            runtime / identity.path,
        )
    private_git = runtime / Path(_GIT_IDENTITY.path).name
    backup = runtime / "git.admitted-backup"
    dll_identity = next(
        item for item in _GIT_IDENTITY.runtime_files if item.path.endswith(".dll")
    )
    private_dll = runtime / dll_identity.path
    dll_backup = tmp_path / f"{dll_identity.path}.admitted-backup"
    forged_dll = tmp_path / f"{dll_identity.path}.forged"
    forged_dll.write_bytes(b"forged DLL replacement\n")
    transient_source = tmp_path / "transient-unadmitted-source.dll"
    transient_source.write_bytes(b"transient unadmitted DLL\n")
    transient_file = runtime / "transient-new-entry.dll"
    transient_move = runtime / "transient-moved-entry.dll"
    transient_directory = runtime / "transient-new-directory"
    moved_runtime = tmp_path / "private-git-runtime-moved"
    real_run = mutation_assurance.subprocess.run
    attempted = False

    # Windows directory handles deny renaming the runtime itself, but they are
    # not membership locks.  Prove that exact residual while the locks are held,
    # then let enumeration establish its baseline after the transient entries
    # have been removed.
    handles = mutation_assurance.lock_git_runtime_for_execution(
        private_git,
        _GIT_IDENTITY,
        private_copy=True,
    )
    try:
        transient_file.write_bytes(b"transient new runtime member\n")
        transient_file.unlink()
        transient_directory.mkdir()
        transient_directory.rmdir()
        os.replace(transient_source, transient_move)
        os.replace(transient_move, transient_source)
    finally:
        mutation_assurance.unlock_git_runtime_for_execution(handles)

    def attack_locked_runtime_then_run_real_git(
        command: object,
        **kwargs: object,
    ) -> subprocess.CompletedProcess[object]:
        nonlocal attempted
        if not attempted:
            attempted = True
            with pytest.raises(OSError):
                os.replace(private_git, backup)
            with pytest.raises(OSError):
                descriptor = os.open(private_git, os.O_WRONLY)
                os.close(descriptor)
            with pytest.raises(OSError):
                os.replace(runtime, moved_runtime)
            with pytest.raises(OSError):
                descriptor = os.open(private_dll, os.O_WRONLY)
                os.close(descriptor)
            with pytest.raises(OSError):
                os.replace(private_dll, dll_backup)
            with pytest.raises(OSError):
                os.replace(forged_dll, private_dll)
        return real_run(command, **kwargs)

    monkeypatch.setattr(
        mutation_assurance.subprocess,
        "run",
        attack_locked_runtime_then_run_real_git,
    )

    snapshot = enumerate_snapshot_inputs(
        repository,
        git_executable=_GIT_IDENTITY,
        git_invocation_path=private_git,
    )
    assert attempted is True
    assert "moira/__init__.py" in snapshot.by_path
    assert forged_dll.read_bytes() == b"forged DLL replacement\n"
    assert transient_source.read_bytes() == b"transient unadmitted DLL\n"
    assert not dll_backup.exists()


def test_hostile_moira_package_never_executes_in_the_trusted_parent(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "hostile-repository"
    repository.mkdir()
    package_sentinel = tmp_path / "package-executed"
    provenance_sentinel = tmp_path / "provenance-executed"
    package_source = (
        "from pathlib import Path\n"
        f"Path({str(package_sentinel)!r}).write_text('executed')\n"
        "import __main__\n"
        "__main__.MOIRA_PACKAGE_EXECUTED = True\n"
    ).encode("utf-8")
    provenance_source = (
        "from pathlib import Path\n"
        f"Path({str(provenance_sentinel)!r}).write_text('executed')\n"
        "import __main__\n"
        "__main__.MOIRA_PROVENANCE_EXECUTED = True\n"
    ).encode("utf-8")
    _synthetic_repository(
        repository,
        package_source=package_source,
        provenance_source=provenance_source,
    )

    probe = f"""
import __main__
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, {str(_ROOT / 'tests')!r})
from support.mutation_assurance import (
    enumerate_snapshot_inputs,
    git_executable_identity,
    phase11_native_build_identity,
)
sys.path.insert(0, {str(repository)!r})

def loaded_engine_modules():
    return sorted(
        name for name in sys.modules
        if name == "moira" or name.startswith("moira.")
    )

assert loaded_engine_modules() == []
git_identity = git_executable_identity(Path({_GIT_IDENTITY.path!r}))
snapshot = enumerate_snapshot_inputs(
    Path({str(repository)!r}),
    git_executable=git_identity,
)
assert loaded_engine_modules() == []
assert not Path({str(package_sentinel)!r}).exists()
catalogue = SimpleNamespace(
    mutants=(SimpleNamespace(
        mutant_id="P11-PARENT-ISOLATION-CANARY",
        evidence_class="native_parity",
        requires_native_backend=True,
    ),),
)
identity = phase11_native_build_identity(
    Path({str(repository)!r}), snapshot, catalogue
)
assert identity["matches_current_inputs"] is True
assert loaded_engine_modules() == []
assert not Path({str(package_sentinel)!r}).exists()
assert not Path({str(provenance_sentinel)!r}).exists()
assert not hasattr(__main__, "MOIRA_PACKAGE_EXECUTED")
assert not hasattr(__main__, "MOIRA_PROVENANCE_EXECUTED")
"""
    completed = subprocess.run(
        [sys.executable, "-I", "-P", "-B", "-c", probe],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert completed.returncode == 0, (
        f"trusted parent executed hostile engine code; stdout={completed.stdout!r}; "
        f"stderr={completed.stderr!r}"
    )
    assert not package_sentinel.exists()
    assert not provenance_sentinel.exists()


def test_native_backend_resolution_rejects_multiple_interpreter_candidates(
    tmp_path: Path,
) -> None:
    suffixes = _native_extension_suffixes()
    if len(suffixes) < 2:
        pytest.skip("interpreter exposes only one extension suffix")
    package = tmp_path / "moira"
    package.mkdir()
    _write(package / f"_moira_native{suffixes[0]}", b"first")
    _write(package / f"_moira_native{suffixes[1]}", b"second")

    with pytest.raises(
        MutationAssuranceError,
        match="exactly one current-interpreter native backend",
    ):
        _native_backend_relative_path(tmp_path)


def test_native_backend_resolution_rejects_a_hard_link(
    tmp_path: Path,
) -> None:
    package = tmp_path / "moira"
    package.mkdir()
    source = tmp_path / "shared-native-bytes"
    source.write_bytes(b"shared")
    candidate = package / f"_moira_native{_native_extension_suffixes()[0]}"
    try:
        os.link(source, candidate)
    except OSError as exc:
        pytest.skip(f"hard links unavailable for canary: {exc}")

    with pytest.raises(
        MutationAssuranceError,
        match="plain unique file|must not be hard-linked",
    ):
        _native_backend_relative_path(tmp_path)


def test_native_backend_resolution_rejects_a_symlink_or_reparse_point(
    tmp_path: Path,
) -> None:
    package = tmp_path / "moira"
    package.mkdir()
    source = tmp_path / "linked-native-bytes"
    source.write_bytes(b"linked")
    candidate = package / f"_moira_native{_native_extension_suffixes()[0]}"
    try:
        candidate.symlink_to(source)
    except OSError as exc:
        pytest.skip(f"symbolic links unavailable for canary: {exc}")

    with pytest.raises(
        MutationAssuranceError,
        match="plain unique file|link or reparse point",
    ):
        _native_backend_relative_path(tmp_path)


def test_native_build_identity_rejects_duplicate_binary_markers(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "duplicate-marker-repository"
    repository.mkdir()
    _synthetic_repository(
        repository,
        package_source=b"# inert package\n",
        provenance_source=b"# inert provenance declaration\n",
        marker_copies=2,
    )
    snapshot = enumerate_snapshot_inputs(
        repository,
        git_executable=_GIT_IDENTITY,
    )

    with pytest.raises(
        MutationAssuranceError,
        match="exactly one build-provenance marker",
    ):
        phase11_native_build_identity(
            repository,
            snapshot,
            _native_catalogue(),
        )


def test_frozen_loader_ignores_root_packaging_shadow_and_pth(
    tmp_path: Path,
) -> None:
    hostile = tmp_path / "hostile-import-root"
    packaging_sentinel = tmp_path / "packaging-executed"
    pth_sentinel = tmp_path / "pth-executed"
    _write(
        hostile / "packaging" / "__init__.py",
        (
            "from pathlib import Path\n"
            f"Path({str(packaging_sentinel)!r}).write_text('executed')\n"
        ).encode("utf-8"),
    )
    _write(
        hostile / "hostile-startup.pth",
        (
            "import pathlib; "
            f"pathlib.Path({str(pth_sentinel)!r}).write_text('executed')\n"
        ).encode("utf-8"),
    )
    probe = f"""
import importlib.util
from pathlib import Path
import sys

hostile = {str(hostile)!r}
sys.path.insert(0, hostile)
specification = importlib.util.spec_from_file_location(
    "phase11_root_shadow_probe", Path({str(_RUNNER)!r})
)
assert specification is not None and specification.loader is not None
runner = importlib.util.module_from_spec(specification)
specification.loader.exec_module(runner)
assert hostile not in sys.path
assert str(runner.ROOT) not in sys.path
assert str(runner.TESTS) not in sys.path
assert "site" not in sys.modules
packaging = sys.modules["packaging"]
packaging_file = Path(packaging.__file__).resolve(strict=True)
site_packages = Path(runner._CLEAN_STARTUP_IMPORT_PATH[-1])
packaging_file.relative_to(site_packages)
assert not Path({str(packaging_sentinel)!r}).exists()
assert not Path({str(pth_sentinel)!r}).exists()
"""
    completed = subprocess.run(
        [sys.executable, "-I", "-P", "-B", "-S", "-c", probe],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert completed.returncode == 0, (
        f"root shadow or pth reached the parent; stdout={completed.stdout!r}; "
        f"stderr={completed.stderr!r}"
    )
    assert not packaging_sentinel.exists()
    assert not pth_sentinel.exists()


def test_frozen_support_sys_modules_swap_is_rejected(tmp_path: Path) -> None:
    probe = f"""
import importlib.util
from pathlib import Path
import sys
from types import ModuleType

specification = importlib.util.spec_from_file_location(
    "phase11_support_swap_probe", Path({str(_RUNNER)!r})
)
assert specification is not None and specification.loader is not None
runner = importlib.util.module_from_spec(specification)
specification.loader.exec_module(runner)
name = "support.mutation_assurance"
original = sys.modules[name]
sys.modules[name] = ModuleType(name)
try:
    runner._assert_frozen_live_bindings("support swap canary")
except RuntimeError as exc:
    assert "live binding changed" in str(exc)
else:
    raise AssertionError("replacement support module was admitted")
finally:
    sys.modules[name] = original
runner._assert_frozen_live_bindings("after support swap restoration")
original_alias = runner.load_catalogue
runner.load_catalogue = lambda *_args, **_kwargs: None
try:
    runner._assert_frozen_live_bindings("callable alias swap canary")
except RuntimeError as exc:
    assert "callable binding changed" in str(exc)
else:
    raise AssertionError("replacement parent callable alias was admitted")
finally:
    runner.load_catalogue = original_alias
runner._assert_frozen_live_bindings("after callable alias restoration")
"""
    completed = subprocess.run(
        [sys.executable, "-I", "-P", "-B", "-S", "-c", probe],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert completed.returncode == 0, (
        f"support swap was admitted; stdout={completed.stdout!r}; "
        f"stderr={completed.stderr!r}"
    )


def test_permanent_deny_blocks_execute_and_remove_moira(
    tmp_path: Path,
) -> None:
    hostile = tmp_path / "hostile-engine-root"
    sentinel = tmp_path / "moira-executed"
    _write(
        hostile / "moira" / "__init__.py",
        (
            "from pathlib import Path\n"
            "import sys\n"
            f"Path({str(sentinel)!r}).write_text('executed')\n"
            "sys.modules.pop(__name__, None)\n"
        ).encode("utf-8"),
    )
    probe = f"""
import importlib
import importlib.util
from pathlib import Path
import sys

specification = importlib.util.spec_from_file_location(
    "phase11_moira_deny_probe", Path({str(_RUNNER)!r})
)
assert specification is not None and specification.loader is not None
runner = importlib.util.module_from_spec(specification)
specification.loader.exec_module(runner)
original_path = tuple(sys.path)
sys.path.insert(0, {str(hostile)!r})
try:
    importlib.import_module("moira")
except ImportError as exc:
    assert "denies engine import" in str(exc)
else:
    raise AssertionError("hostile Moira package executed and removed itself")
finally:
    sys.path[:] = original_path
assert "moira" not in sys.modules
assert not Path({str(sentinel)!r}).exists()
finder = runner._MOIRA_DENY_FINDER
assert sys.meta_path[0] is finder
sys.meta_path.remove(finder)
try:
    runner._assert_moira_deny_finder("removal canary")
except RuntimeError as exc:
    assert "deny finder changed" in str(exc)
else:
    raise AssertionError("removed deny finder was admitted")
finally:
    sys.meta_path.insert(0, finder)
runner._assert_frozen_live_bindings("after deny restoration")
replacement = object()
sys.meta_path[0] = replacement
try:
    runner._assert_moira_deny_finder("replacement canary")
except RuntimeError as exc:
    assert "deny finder changed" in str(exc)
else:
    raise AssertionError("replacement deny finder was admitted")
finally:
    sys.meta_path[0] = finder
runner._assert_frozen_live_bindings("after deny replacement restoration")
"""
    completed = subprocess.run(
        [sys.executable, "-I", "-P", "-B", "-S", "-c", probe],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert completed.returncode == 0, (
        f"Moira deny boundary failed; stdout={completed.stdout!r}; "
        f"stderr={completed.stderr!r}"
    )
    assert not sentinel.exists()


def test_critical_source_symlink_and_hardlink_are_rejected_before_load(
    tmp_path: Path,
) -> None:
    sentinel = tmp_path / "critical-target-executed"
    target = tmp_path / "hostile_critical_target.py"
    target.write_text(
        "from pathlib import Path\n"
        f"Path({str(sentinel)!r}).write_text('executed')\n",
        encoding="utf-8",
    )
    symlink = tmp_path / "linked_critical_source.py"
    try:
        symlink.symlink_to(target)
    except OSError as exc:
        pytest.skip(f"symbolic links unavailable for canary: {exc}")
    hardlink = tmp_path / "hardlinked_critical_source.py"
    try:
        os.link(target, hardlink)
    except OSError as exc:
        pytest.skip(f"hard links unavailable for canary: {exc}")
    probe = f"""
import importlib.util
from pathlib import Path

specification = importlib.util.spec_from_file_location(
    "phase11_critical_link_probe", Path({str(_RUNNER)!r})
)
assert specification is not None and specification.loader is not None
runner = importlib.util.module_from_spec(specification)
specification.loader.exec_module(runner)
for candidate, expected in (
    (Path({str(symlink)!r}), "link or reparse point"),
    (Path({str(hardlink)!r}), "hard-linked"),
):
    try:
        runner._stable_preimport_source(candidate)
    except RuntimeError as exc:
        assert expected in str(exc)
    else:
        raise AssertionError(f"critical link admitted: {{candidate}}")
assert not Path({str(sentinel)!r}).exists()
"""
    completed = subprocess.run(
        [sys.executable, "-I", "-P", "-B", "-S", "-c", probe],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert completed.returncode == 0, (
        f"critical link reached execution; stdout={completed.stdout!r}; "
        f"stderr={completed.stderr!r}"
    )
    assert not sentinel.exists()
