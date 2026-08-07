"""Adversarial contracts for Phase 11 mutation-runner primitives."""

from __future__ import annotations

import ast
import base64
from collections.abc import Callable
from copy import deepcopy
from dataclasses import replace
from functools import lru_cache
import hashlib
import importlib
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
from types import CodeType, FunctionType, ModuleType, SimpleNamespace

import pytest

from _pytest_plugins.evidence_schema import contract_sha256
from evidence.contracts import CONTRACTS
from support.mutation_assurance import (
    _canonical_ast_sha256,
    _expected_child_argv,
    _native_build_input_manifest,
    FailureExpectation,
    FileIdentity,
    GitExecutableIdentity,
    MutantSpec,
    MutationCatalogue,
    MutationAssuranceError,
    ProcessObservation,
    SnapshotInputs,
    adjudicate_baseline,
    adjudicate_mutant,
    apply_exact_mutation,
    atomically_apply_mutant,
    canonical_json_bytes,
    enumerate_snapshot_inputs,
    git_executable_identity,
    load_catalogue,
    mutation_patch_sha256,
    phase11_native_build_identity,
    pretty_json_bytes,
    python_source_code_sha256,
    seal_mutation_receipt,
    sha256_bytes,
    strict_json_bytes,
    structural_python_code_sha256,
    validate_mutation_receipt,
    verify_snapshot,
)


pytestmark = pytest.mark.parallel(reason="isolated_resources")


_CLAIM_ID = "MOIRA-COORD-LONGITUDE-QUOTIENT-V1"
_KILLER_NODEID = (
    "tests/metamorphic/test_coordinate_relations.py::"
    "test_longitude_quotient_relation"
)
_INTENDED_TEST_RELATIVE = "tests/metamorphic/test_coordinate_relations.py"
_INTENDED_TEST_MODULE = "tests.metamorphic.test_coordinate_relations"
_INTENDED_TEST_QUALNAME = "test_longitude_quotient_relation"
_INTENDED_TEST_SOURCE = (
    b"def test_longitude_quotient_relation():\n"
    b"    assert True\n"
)
_FORGED_INTENDED_TEST_SOURCE = _INTENDED_TEST_SOURCE.replace(
    b"assert True",
    b"assert None",
)
_SOURCE_LOADER = "_frozen_importlib_external.SourceFileLoader"
_EXTENSION_LOADER = "_frozen_importlib_external.ExtensionFileLoader"
_PYTEST_REWRITE_LOADER = "_pytest.assertion.rewrite.AssertionRewritingHook"
_ZERO_SHA256 = "0" * 64
_EXECUTION_ID = "phase11-synthetic-adjudication"
_METRIC = "canonical longitude upper bound"
_BASELINE_MUTANT_ID = "unmutated-production-observation"
_RECEIPT_RUN_ID = "phase11-synthetic-receipt"
_REPORT_AUTHORSHIP_BOUNDARY = (
    "same_process_intended_test_conftest_pytest_plugin_code_trusted_"
    "no_external_trace_authorship_proof"
)
_SYNTHETIC_LRU_WRAPPER_NAMES = ("synthetic._compile_pattern",)
_SYNTHETIC_LRU_WRAPPER_SHA256 = sha256_bytes(
    b'["synthetic._compile_pattern"]'
)

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
assert isinstance(_GIT_IDENTITY, GitExecutableIdentity)


def _bare_mutation_reporter(reporter_module: ModuleType, **fields: object):
    reporter = object.__new__(reporter_module._Reporter)
    for name, value in fields.items():
        setattr(reporter, name, value)
    return reporter


def test_reporter_addoption_registers_exact_immutable_identity_plugin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from _pytest.config import PytestPluginManager
    from _pytest.config.argparsing import Parser

    reporter_module = importlib.import_module("tests.mutation_reporter")
    pluginmanager = PytestPluginManager()
    parser = Parser(_ispytest=True)
    reporter_module.pytest_addoption(parser, pluginmanager)
    plugin = pluginmanager.get_plugin(
        "moira-phase11-early-pytest-lru-identity"
    )
    assert type(plugin) is reporter_module._EarlyPytestLruIdentityPlugin
    assert tuple.__len__(plugin) == 4
    assert tuple.__getitem__(plugin, 0) is pluginmanager
    wrapper = object.__getattribute__(pluginmanager, "__dict__")[
        "_get_directory"
    ]
    assert tuple.__getitem__(plugin, 1) is wrapper
    assert tuple.__getitem__(plugin, 2) is object.__getattribute__(
        wrapper,
        "__dict__",
    )["cache_parameters"]
    retained_configure = tuple.__getitem__(plugin, 3)
    assert retained_configure is reporter_module._configure_reporter
    assert not hasattr(plugin, "__dict__")
    with pytest.raises(TypeError):
        plugin[0] = object()
    with pytest.raises(AttributeError):
        object.__setattr__(plugin, "retained", object())

    def hostile_configure(config, retained_identity) -> None:
        raise AssertionError((config, retained_identity))

    monkeypatch.setattr(
        reporter_module,
        "_configure_reporter",
        hostile_configure,
    )
    assert tuple.__getitem__(plugin, 3) is retained_configure
    implementation = next(
        item
        for item in pluginmanager.hook.pytest_configure.get_hookimpls()
        if item.plugin is plugin
    )
    assert implementation.function.__self__ is plugin
    assert implementation.function.__func__ is type(plugin).pytest_configure
    assert implementation.argnames == ("config",)
    assert implementation.kwargnames == ()
    assert implementation.trylast is True
    forged = lru_cache(maxsize=256, typed=True)(
        object.__getattribute__(wrapper, "__dict__")["__wrapped__"]
    )
    object.__getattribute__(forged, "__dict__").update(
        object.__getattribute__(wrapper, "__dict__")
    )
    monkeypatch.setattr(pluginmanager, "_get_directory", forged)
    config = SimpleNamespace(pluginmanager=pluginmanager)
    pluginmanager._configured = True
    pluginmanager._name2plugin["pytestconfig"] = config
    with pytest.raises(
        pytest.UsageError,
        match="early pytest identity relationships changed",
    ):
        implementation.function(config)
    assert tuple(forged.cache_info()) == (0, 0, 256, 0)
    assert pluginmanager.get_plugin(
        "moira-phase11-early-pytest-lru-identity"
    ) is plugin
    assert not hasattr(reporter_module, "pytest_configure")
    assert not hasattr(reporter_module, "_read_early_pytest_lru_identity")
    assert not hasattr(reporter_module, "_retain_early_pytest_lru_identity")
    for value in vars(reporter_module).values():
        if type(value) is not FunctionType:
            continue
        assert value.__defaults__ is None or pluginmanager not in value.__defaults__
        for cell in value.__closure__ or ():
            assert cell.cell_contents is not pluginmanager


def test_reporter_early_identity_uses_one_immutable_temporary_plugin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from _pytest.config import PytestPluginManager

    reporter_module = importlib.import_module("tests.mutation_reporter")
    pluginmanager = PytestPluginManager()
    early_identity = reporter_module._early_pytest_lru_identity(pluginmanager)
    observed: list[tuple[object, tuple[object, object, object], bool]] = []

    def configure_stub(config, retained_identity) -> None:
        observed.append(
            (
                config,
                retained_identity,
                pluginmanager.get_plugin(
                    "moira-phase11-early-pytest-lru-identity"
                )
                is None,
            )
        )

    assert type(configure_stub) is FunctionType
    plugin = tuple.__new__(
        reporter_module._EarlyPytestLruIdentityPlugin,
        (*early_identity, configure_stub),
    )
    assert type(plugin) is reporter_module._EarlyPytestLruIdentityPlugin
    assert tuple.__len__(plugin) == 4
    assert not hasattr(plugin, "__dict__")
    with pytest.raises(TypeError):
        plugin[0] = object()
    with pytest.raises(AttributeError):
        object.__setattr__(plugin, "retained", object())

    def hostile_configure(config, retained_identity) -> None:
        raise AssertionError((config, retained_identity))

    monkeypatch.setattr(
        reporter_module,
        "_configure_reporter",
        hostile_configure,
    )
    assert tuple.__getitem__(plugin, 3) is configure_stub
    registered = pluginmanager.register(
        plugin,
        name="moira-phase11-early-pytest-lru-identity",
    )
    assert registered == "moira-phase11-early-pytest-lru-identity"
    implementation = next(
        item
        for item in pluginmanager.hook.pytest_configure.get_hookimpls()
        if item.plugin is plugin
    )
    assert implementation.function.__self__ is plugin
    assert implementation.function.__func__ is type(plugin).pytest_configure
    assert implementation.argnames == ("config",)
    assert implementation.kwargnames == ()
    assert implementation.trylast is True

    config = SimpleNamespace(pluginmanager=pluginmanager)
    pluginmanager._configured = True
    pluginmanager._name2plugin["pytestconfig"] = config
    implementation.function(config)

    assert observed == [(config, early_identity, True)]
    assert pluginmanager.get_plugin(
        "moira-phase11-early-pytest-lru-identity"
    ) is None
    assert all(
        item.plugin is not plugin
        for item in pluginmanager.hook.pytest_configure.get_hookimpls()
    )


def test_reporter_early_identity_proves_live_lru_typed_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from _pytest.config import PytestPluginManager

    reporter_module = importlib.import_module("tests.mutation_reporter")
    pluginmanager = PytestPluginManager()
    honest = pluginmanager._get_directory
    honest_namespace = object.__getattribute__(honest, "__dict__")
    honest_parameters = honest_namespace["cache_parameters"]
    forged = lru_cache(maxsize=256, typed=True)(
        honest_namespace["__wrapped__"]
    )
    forged_namespace = object.__getattribute__(forged, "__dict__")
    forged_namespace.clear()
    forged_namespace.update(honest_namespace)
    assert forged.cache_parameters() == {"maxsize": 256, "typed": False}
    monkeypatch.setattr(pluginmanager, "_get_directory", forged)
    callbacks: list[str] = []

    def configure_stub(config, retained_identity) -> None:
        callbacks.append(f"{config!r}:{retained_identity!r}")

    plugin = tuple.__new__(
        reporter_module._EarlyPytestLruIdentityPlugin,
        (pluginmanager, forged, honest_parameters, configure_stub),
    )
    pluginmanager.register(
        plugin,
        name="moira-phase11-early-pytest-lru-identity",
    )
    implementation = next(
        item
        for item in pluginmanager.hook.pytest_configure.get_hookimpls()
        if item.plugin is plugin
    )
    config = SimpleNamespace(pluginmanager=pluginmanager)
    pluginmanager._configured = True
    pluginmanager._name2plugin["pytestconfig"] = config

    with pytest.raises(
        pytest.UsageError,
        match="pytest LRU behavior probe failed",
    ):
        implementation.function(config)

    assert callbacks == []
    assert tuple(forged.cache_info()) == (0, 0, 256, 0)
    assert pluginmanager.get_plugin(
        "moira-phase11-early-pytest-lru-identity"
    ) is plugin


def _current_pytest_lru_identity(
    config: pytest.Config,
) -> dict[str, object]:
    config_namespace = object.__getattribute__(config, "__dict__")
    manager = dict.__getitem__(config_namespace, "pluginmanager")
    manager_namespace = object.__getattribute__(manager, "__dict__")
    wrapper = dict.__getitem__(manager_namespace, "_get_directory")
    wrapper_namespace = object.__getattribute__(wrapper, "__dict__")
    return {
        "expected_plugin_manager": manager,
        "expected_get_directory_wrapper": wrapper,
        "expected_cache_parameters": dict.__getitem__(
            wrapper_namespace,
            "cache_parameters",
        ),
    }


def _frozen_identity_environment() -> dict[str, str]:
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


def _artifact_tree_signature(root: Path) -> tuple[object, ...]:
    try:
        root.lstat()
    except FileNotFoundError:
        return (False,)

    def entry_signature(path: Path, relative: str) -> tuple[object, ...]:
        metadata = path.lstat()
        mode = metadata.st_mode
        if stat.S_ISREG(mode):
            payload = hashlib.sha256(path.read_bytes()).hexdigest()
        elif stat.S_ISLNK(mode):
            payload = os.readlink(path)
        else:
            payload = None
        return (
            relative,
            metadata.st_dev,
            metadata.st_ino,
            mode,
            metadata.st_nlink,
            metadata.st_size,
            getattr(metadata, "st_ctime_ns", None),
            getattr(metadata, "st_mtime_ns", None),
            payload,
        )

    values = [entry_signature(root, ".")]
    values.extend(
        entry_signature(path, path.relative_to(root).as_posix())
        for path in sorted(root.rglob("*"), key=lambda value: value.as_posix())
    )
    return True, tuple(values)


def _phase11_temp_signature() -> tuple[object, ...]:
    temporary_root = Path(tempfile.gettempdir())
    prefixes = (
        "moira-phase11-parent-pycache-*",
        "moira-phase11-runner-*",
    )
    return tuple(
        (
            path.name,
            _artifact_tree_signature(path),
        )
        for path in sorted(
            {
                path
                for prefix in prefixes
                for path in temporary_root.glob(prefix)
            },
            key=lambda value: value.name,
        )
    )


def test_artifact_tree_signature_detects_same_size_timestamp_rewrite(
    tmp_path: Path,
) -> None:
    artifact = tmp_path / "artifact.bin"
    artifact.write_bytes(b"AAAA")
    retained_timestamp = artifact.stat().st_mtime_ns
    before = _artifact_tree_signature(tmp_path)

    artifact.write_bytes(b"BBBB")
    os.utime(artifact, ns=(retained_timestamp, retained_timestamp))

    assert _artifact_tree_signature(tmp_path) != before


def test_artifact_tree_signature_binds_root_metadata(tmp_path: Path) -> None:
    (tmp_path / "artifact.bin").write_bytes(b"sealed")
    before = _artifact_tree_signature(tmp_path)
    metadata = tmp_path.stat()

    os.utime(
        tmp_path,
        ns=(
            metadata.st_atime_ns,
            metadata.st_mtime_ns + 2_000_000_000,
        ),
    )

    assert _artifact_tree_signature(tmp_path) != before


def test_artifact_tree_signature_detects_same_content_root_replacement(
    tmp_path: Path,
) -> None:
    root = tmp_path / "artifact-root.bin"
    root.write_bytes(b"same-content")
    retained_timestamp = root.stat().st_mtime_ns
    before = _artifact_tree_signature(root)

    root.unlink()
    root.write_bytes(b"same-content")
    os.utime(root, ns=(retained_timestamp, retained_timestamp))

    assert _artifact_tree_signature(root) != before


def test_phase11_temp_signature_covers_both_runner_families(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = tmp_path / "moira-phase11-runner-canary"
    parent_pycache = tmp_path / "moira-phase11-parent-pycache-canary"
    unrelated = tmp_path / "moira-phase11-unrelated-canary"
    for directory in (runner, parent_pycache, unrelated):
        directory.mkdir()
        (directory / "payload.bin").write_bytes(directory.name.encode("ascii"))
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))

    signature = _phase11_temp_signature()

    assert [entry[0] for entry in signature] == [
        parent_pycache.name,
        runner.name,
    ]


def test_interpreter_identity_requires_the_exact_frozen_startup_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import support.mutation_assurance as mutation_assurance

    admitted = ("phase11-stdlib", "phase11-site-packages")
    callbacks: list[str] = []

    class HostileTuple(tuple):
        def __iter__(self):
            callbacks.append("tuple-iter")
            return super().__iter__()

    class HostileList(list):
        def __iter__(self):
            callbacks.append("list-iter")
            return super().__iter__()

    monkeypatch.setattr(sys, "path", list(admitted))
    with pytest.raises(
        MutationAssuranceError,
        match="startup import path proof is required",
    ):
        mutation_assurance._require_exact_startup_import_path(None)
    with pytest.raises(
        MutationAssuranceError,
        match="startup import path proof is not exact",
    ):
        mutation_assurance._require_exact_startup_import_path(
            HostileTuple(admitted)
        )
    assert callbacks == []
    mutation_assurance._require_exact_startup_import_path(admitted)
    monkeypatch.setattr(sys, "path", HostileList(admitted))
    with pytest.raises(
        MutationAssuranceError,
        match="active sys.path is not exact",
    ):
        mutation_assurance._require_exact_startup_import_path(admitted)
    assert callbacks == []
    monkeypatch.setattr(sys, "path", list(admitted))
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    with pytest.raises(
        MutationAssuranceError,
        match="sys.path changed after clean startup capture",
    ):
        mutation_assurance._require_exact_startup_import_path(admitted)


def test_runner_rejects_startup_path_helper_rebind_before_callback() -> None:
    runner = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "run_scientific_mutations.py"
    )
    probe = f"""
import importlib.util
from pathlib import Path

runner_path = Path({str(runner)!r})
specification = importlib.util.spec_from_file_location(
    "phase11_runner_startup_path_rebind_probe",
    runner_path,
)
assert specification is not None and specification.loader is not None
runner = importlib.util.module_from_spec(specification)
specification.loader.exec_module(runner)

calls = []
def hostile_startup_path_policy(value):
    calls.append(value)

runner._ASSURANCE_MODULE.__dict__["_require_exact_startup_import_path"] = (
    hostile_startup_path_policy
)
try:
    runner._assert_frozen_live_bindings("startup-path helper rebind probe")
except RuntimeError as exc:
    assert "_require_exact_startup_import_path" in str(exc)
else:
    raise AssertionError("startup-path helper rebind was admitted")
assert calls == []
"""

    completed = subprocess.run(
        [sys.executable, "-I", "-P", "-B", "-S", "-c", probe],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert completed.returncode == 0, (
        "startup-path helper rebind escaped the frozen binding gate; "
        f"stdout={completed.stdout!r}; stderr={completed.stderr!r}"
    )


def test_reporter_lru_context_seal_rejects_hostile_property_without_callbacks(
    pytestconfig: pytest.Config,
) -> None:
    reporter_module = importlib.import_module("mutation_reporter")
    import support.mutation_toolchain as mutation_toolchain

    retained = mutation_toolchain.capture_active_pytest_lru_runtime_context(
        pytestconfig,
        **_current_pytest_lru_identity(pytestconfig),
    )
    reporter = _bare_mutation_reporter(
        reporter_module,
        lru_runtime_context=retained,
        lru_runtime_context_identity=id(retained),
    )
    calls: list[str] = []

    class HostileContext:
        @property
        def config(self) -> object:
            calls.append("config")
            raise AssertionError("hostile context descriptor executed")

    reporter.lru_runtime_context = HostileContext()
    with pytest.raises(ValueError, match="context identity changed"):
        reporter._active_lru_runtime_context()
    assert calls == []


def test_reporter_lru_context_seal_rejects_fresh_valid_replacement(
    pytestconfig: pytest.Config,
) -> None:
    reporter_module = importlib.import_module("mutation_reporter")
    import support.mutation_toolchain as mutation_toolchain

    retained = mutation_toolchain.capture_active_pytest_lru_runtime_context(
        pytestconfig,
        **_current_pytest_lru_identity(pytestconfig),
    )
    replacement = mutation_toolchain.capture_active_pytest_lru_runtime_context(
        pytestconfig,
        **_current_pytest_lru_identity(pytestconfig),
    )
    assert replacement is not retained
    reporter = _bare_mutation_reporter(
        reporter_module,
        lru_runtime_context=replacement,
        lru_runtime_context_identity=id(retained),
    )
    with pytest.raises(ValueError, match="context identity changed"):
        reporter._active_lru_runtime_context()


def _compiled_probe_module(
    *,
    name: str,
    path: Path,
    source: str,
) -> ModuleType:
    path.write_text(source, encoding="utf-8", newline="\n")
    module = ModuleType(name)
    module.__file__ = str(path.resolve(strict=True))
    exec(
        compile(source, str(path.resolve(strict=True)), "exec"),
        module.__dict__,
    )
    return module


def _intended_test_structural_sha256(
    source: bytes,
    *,
    filename: str,
) -> str:
    from _pytest.assertion.rewrite import rewrite_asserts

    tree = ast.parse(source, filename=filename)
    rewrite_asserts(tree, source, filename, None)
    module_code = compile(
        tree,
        filename,
        "exec",
        dont_inherit=True,
        optimize=0,
    )
    matches: list[CodeType] = []
    pending = [module_code]
    while pending:
        code = pending.pop()
        if code.co_qualname == _INTENDED_TEST_QUALNAME:
            matches.append(code)
        pending.extend(
            value for value in code.co_consts if isinstance(value, CodeType)
        )
    assert len(matches) == 1
    return structural_python_code_sha256(matches[0])


def _synthetic_intended_test_source_receipt(
    source: bytes = _INTENDED_TEST_SOURCE,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "source_path": _INTENDED_TEST_RELATIVE,
        "module_name": _INTENDED_TEST_MODULE,
        "qualname": _INTENDED_TEST_QUALNAME,
        "source_bytes": len(source),
        "source_sha256": sha256_bytes(source),
        "source_base64": base64.b64encode(source).decode("ascii"),
        "rewrite_policy": "pytest_assertion_rewrite_disabled",
        "code_algorithm": "python_code_structural_v1",
        "code_sha256": _intended_test_structural_sha256(
            source,
            filename=_INTENDED_TEST_RELATIVE,
        ),
    }


def _spec(
    *,
    source_path: str = "moira/probe.py",
    preimage: str = "return 1",
    replacement: str = "return 2",
    occurrence_count: int = 1,
    preimage_sha256: str = _ZERO_SHA256,
    postimage_sha256: str = _ZERO_SHA256,
) -> MutantSpec:
    return MutantSpec(
        mutant_id="P11-SYNTHETIC-EXACT-REPLACEMENT",
        criticality="supplemental",
        fault_archetype="synthetic exact replacement",
        operator="replace_exact_utf8_v1",
        source_path=source_path,
        target_qualname="target",
        preimage=preimage,
        replacement=replacement,
        occurrence_count=occurrence_count,
        source_hash_mode="utf8_lf_v1",
        preimage_sha256=preimage_sha256,
        postimage_sha256=postimage_sha256,
        preimage_ast_sha256=_ZERO_SHA256,
        postimage_ast_sha256=_ZERO_SHA256,
        preimage_code_sha256=_ZERO_SHA256,
        postimage_code_sha256=_ZERO_SHA256,
        patch_sha256=_ZERO_SHA256,
        intended_killer_nodeid=_KILLER_NODEID,
        expected_claim_id=_CLAIM_ID,
        expected_contract_sha256=_ZERO_SHA256,
        evidence_class="invariant",
        expected_failure=FailureExpectation(
            exception_type="builtins.AssertionError",
            message_contains=(),
            longrepr_contains=(),
            metamorphic_witness=None,
        ),
        requires_native_backend=False,
        timeout_seconds=30,
        exclusions=("synthetic policy probe",),
    )


def _snapshot(
    root: Path,
    files: dict[str, bytes],
) -> SnapshotInputs:
    identities: list[FileIdentity] = []
    for relative, raw in sorted(files.items()):
        path = root / Path(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        identities.append(
            FileIdentity(
                path=relative,
                bytes=len(raw),
                sha256=sha256_bytes(raw),
            )
        )
    files_tuple = tuple(identities)
    native_backend_path = "moira/_moira_native.synthetic.pyd"
    manifest_sha256 = sha256_bytes(
        canonical_json_bytes(
            {
                "deleted_tracked": [],
                "files": [
                    {
                        "bytes": item.bytes,
                        "path": item.path,
                        "sha256": item.sha256,
                    }
                    for item in files_tuple
                ],
                "git_executable": {
                    "path": _GIT_IDENTITY.path,
                    "bytes": _GIT_IDENTITY.bytes,
                    "sha256": _GIT_IDENTITY.sha256,
                    "runtime_files": [
                        {
                            "bytes": item.bytes,
                            "path": item.path,
                            "sha256": item.sha256,
                        }
                        for item in _GIT_IDENTITY.runtime_files
                    ],
                    "runtime_manifest_sha256": (
                        _GIT_IDENTITY.runtime_manifest_sha256
                    ),
                },
                "native_backend_path": native_backend_path,
                "schema_version": 3,
                "untracked_exclude_policy": [
                    "__pycache__/",
                    "*.py[cod]",
                    "tests/artifacts/kernels/",
                ],
            }
        )
    )
    return SnapshotInputs(
        files=files_tuple,
        deleted_tracked=(),
        native_backend_path=native_backend_path,
        git_executable=_GIT_IDENTITY,
        untracked_exclude_policy=(
            "__pycache__/",
            "*.py[cod]",
            "tests/artifacts/kernels/",
        ),
        manifest_sha256=manifest_sha256,
    )


def _catalogue_payload(
    *,
    source_path: str,
    target_qualname: str = "normalize_degrees",
) -> dict[str, object]:
    contract = CONTRACTS[_CLAIM_ID]
    preimage = "return angle % 360.0"
    replacement = "return angle % 361.0"
    return {
        "schema_version": 1,
        "policy": {
            "accepted_outcome": "killed_intended",
            "aggregate_gate": "all_declared_mutants_no_percentage",
            "isolation": "fresh_plain_file_snapshot_per_mutant",
            "network_boundary": (
                "cooperative_cpython_deny_not_security_sandbox"
            ),
            "source_scope": "moira_python_only",
        },
        "mutants": [
            {
                "mutant_id": "P11-SYNTHETIC-CATALOGUE-PATH",
                "criticality": "critical",
                "fault_archetype": "synthetic path admission probe",
                "operator": "replace_exact_utf8_v1",
                "source_path": source_path,
                "target_qualname": target_qualname,
                "preimage": preimage,
                "replacement": replacement,
                "occurrence_count": 1,
                "source_hash_mode": "utf8_lf_v1",
                "preimage_sha256": _ZERO_SHA256,
                "postimage_sha256": _ZERO_SHA256,
                "preimage_ast_sha256": _ZERO_SHA256,
                "postimage_ast_sha256": _ZERO_SHA256,
                "preimage_code_sha256": _ZERO_SHA256,
                "postimage_code_sha256": _ZERO_SHA256,
                "patch_sha256": mutation_patch_sha256(
                    source_path=source_path,
                    operator="replace_exact_utf8_v1",
                    preimage=preimage,
                    replacement=replacement,
                ),
                "intended_killer_nodeid": _KILLER_NODEID,
                "expected_claim_id": _CLAIM_ID,
                "expected_contract_sha256": contract_sha256(contract),
                "evidence_class": contract.evidence_class.value,
                "expected_failure": {
                    "exception_type": (
                        "support.metamorphic.MetamorphicViolation"
                    ),
                    "message_contains": [],
                    "longrepr_contains": [],
                    "metamorphic_witness": {
                        "relation_id": _CLAIM_ID,
                        "mutant_id": "unmutated-production-observation",
                        "metric": "canonical longitude upper bound",
                    },
                },
                "requires_native_backend": False,
                "timeout_seconds": 30,
                "exclusions": ["synthetic catalogue parsing probe"],
            }
        ],
    }


def _load_synthetic_catalogue(
    tmp_path: Path,
    *,
    source_path: str,
) -> None:
    path = tmp_path / "catalogue.json"
    path.write_bytes(pretty_json_bytes(_catalogue_payload(source_path=source_path)))
    load_catalogue(
        path,
        root=tmp_path,
        contracts=CONTRACTS,
        verify_sources=False,
    )


def test_strict_json_rejects_duplicate_object_keys() -> None:
    with pytest.raises(MutationAssuranceError, match="duplicate object key"):
        strict_json_bytes(b'{"identity": 1, "identity": 2}', label="probe")


@pytest.mark.parametrize(
    "constant",
    (b"NaN", b"Infinity", b"-Infinity"),
)
def test_strict_json_rejects_nonfinite_constants(constant: bytes) -> None:
    with pytest.raises(MutationAssuranceError, match="non-finite"):
        strict_json_bytes(b'{"value":' + constant + b"}", label="probe")


def test_python_code_v1_ignores_filename_but_not_semantics() -> None:
    baseline = b"def target(value):\n    return value + 1\n"
    changed = b"def target(value):\n    return value - 1\n"

    first = python_source_code_sha256(
        baseline,
        qualname="target",
        filename="first-checkout/moira/probe.py",
    )
    second = python_source_code_sha256(
        baseline,
        qualname="target",
        filename="another-checkout/moira/probe.py",
    )
    semantic_change = python_source_code_sha256(
        changed,
        qualname="target",
        filename="first-checkout/moira/probe.py",
    )

    assert first == second
    assert semantic_change != first


@pytest.mark.parametrize("target_shape", ("callable_proxy", "wrapped_function"))
def test_reporter_prepare_target_rejects_nonexact_or_wrapped_bindings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    target_shape: str,
) -> None:
    reporter_module = importlib.import_module("mutation_reporter")
    module_name = f"_phase11_prepare_target_{target_shape}"
    source_path = tmp_path / f"{module_name}.py"
    module = _compiled_probe_module(
        name=module_name,
        path=source_path,
        source="def target():\n    return 1\n",
    )
    exact_target = module.target

    if target_shape == "callable_proxy":

        class CallableProxy:
            __wrapped__ = exact_target

            def __call__(self):
                return exact_target()

        module.target = CallableProxy()
    else:
        exact_target.__wrapped__ = lambda: 0

    monkeypatch.setitem(sys.modules, module_name, module)
    reporter = _bare_mutation_reporter(
        reporter_module,
        module_name=module_name,
        source_path=source_path.resolve(strict=True),
        source_relative_path=source_path.name,
        target_qualname="target",
    )

    with pytest.raises(
        TypeError,
        match="exact unwrapped Python function binding",
    ):
        reporter._prepare_target()


def test_reporter_prepare_target_rejects_detached_sys_modules_binding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reporter_module = importlib.import_module("mutation_reporter")
    module_name = "_phase11_detached_target_probe"
    source_path = tmp_path / f"{module_name}.py"
    captured_module = _compiled_probe_module(
        name=module_name,
        path=source_path,
        source="def target():\n    return 1\n",
    )
    monkeypatch.setitem(sys.modules, module_name, ModuleType(module_name))
    original_import_module = reporter_module.importlib.import_module
    monkeypatch.setattr(
        reporter_module.importlib,
        "import_module",
        lambda requested: captured_module
        if requested == module_name
        else original_import_module(requested),
    )
    reporter = _bare_mutation_reporter(
        reporter_module,
        module_name=module_name,
        source_path=source_path.resolve(strict=True),
        source_relative_path=source_path.name,
        target_qualname="target",
    )

    with pytest.raises(ValueError, match="exact live sys.modules binding"):
        reporter._prepare_target()


def test_reporter_intended_callable_rejects_detached_sys_modules_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reporter_module = importlib.import_module("mutation_reporter")
    module = sys.modules[__name__]
    qualname = "test_strict_json_rejects_duplicate_object_keys"
    nodeid = f"tests/harness_meta/test_mutation_runner_policy.py::{qualname}"
    item = SimpleNamespace(
        nodeid=nodeid,
        originalname=qualname,
        module=module,
        obj=getattr(module, qualname),
    )
    monkeypatch.setitem(sys.modules, __name__, ModuleType(__name__))

    with pytest.raises(ValueError, match="exact live sys.modules binding"):
        reporter_module._callable_identity(
            item,
            root=Path(__file__).resolve().parents[2],
            intended_nodeid=nodeid,
        )


def test_reporter_trace_requires_live_bindings_and_exact_test_ancestry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reporter_module = importlib.import_module("mutation_reporter")
    target_name = "_phase11_trace_target_probe"
    test_name = "_phase11_trace_intended_probe"
    target_path = tmp_path / f"{target_name}.py"
    test_path = tmp_path / f"{test_name}.py"
    target_module = _compiled_probe_module(
        name=target_name,
        path=target_path,
        source=(
            "import sys\n"
            "target_frames = []\n"
            "def target():\n"
            "    target_frames.append(sys._getframe())\n"
        ),
    )
    monkeypatch.setitem(sys.modules, target_name, target_module)
    test_module = _compiled_probe_module(
        name=test_name,
        path=test_path,
        source=(
            "import sys\n"
            f"from {target_name} import target\n"
            "test_frames = []\n"
            "def intended_test():\n"
            "    test_frames.append(sys._getframe())\n"
            "    target()\n"
            "def pytest_runtest_call_out_of_band():\n"
            "    target()\n"
        ),
    )
    monkeypatch.setitem(sys.modules, test_name, test_module)

    reporter = _bare_mutation_reporter(
        reporter_module,
        module_name=target_name,
        source_path=target_path.resolve(strict=True),
        target_qualname="target",
        target_module=target_module,
        target_function=target_module.target,
        target_code=target_module.target.__code__,
        target_binding_stable=True,
        intended_test_module=test_module,
        intended_test_function=test_module.intended_test,
        intended_test_code=test_module.intended_test.__code__,
        initial_intended_test_callable={
            "module": test_name,
            "qualname": "intended_test",
            "code": {"filename": str(test_path.resolve(strict=True))},
        },
        trace_call_count=0,
        trace_frame_filenames=set(),
        trace_code_sha256=set(),
        intended_test_trace_call_count=0,
        intended_test_trace_frame_filenames=set(),
        intended_test_trace_code_sha256=set(),
        internal_errors=[],
    )

    test_module.intended_test()
    test_module.pytest_runtest_call_out_of_band()
    intended_frame = test_module.test_frames[0]
    causal_target_frame, out_of_band_target_frame = target_module.target_frames

    assert reporter._matches_intended_test_frame(intended_frame) is True
    assert reporter._matches_target_frame(causal_target_frame) is True
    assert (
        reporter._target_call_has_intended_test_ancestor(causal_target_frame)
        is True
    )
    assert (
        reporter._target_call_has_intended_test_ancestor(out_of_band_target_frame)
        is False
    )

    trace_errors: list[str] = []
    reporter._observe_trace_call(intended_frame, trace_errors)
    reporter._observe_trace_call(causal_target_frame, trace_errors)
    reporter._observe_trace_call(out_of_band_target_frame, trace_errors)
    assert reporter.intended_test_trace_call_count == 1
    assert reporter.trace_call_count == 1
    assert trace_errors == [
        "declared mutation target was called outside the exact intended-test "
        "frame ancestry"
    ]

    monkeypatch.setitem(sys.modules, target_name, ModuleType(target_name))
    assert reporter._matches_target_frame(causal_target_frame) is False
    assert reporter._target_identity_is_stable() is False

    monkeypatch.setitem(sys.modules, target_name, target_module)
    monkeypatch.setitem(sys.modules, test_name, ModuleType(test_name))
    assert reporter._matches_intended_test_frame(intended_frame) is False
    assert (
        reporter._target_call_has_intended_test_ancestor(causal_target_frame)
        is False
    )


@pytest.mark.parametrize(
    ("source", "spec", "diagnostic"),
    (
        (
            b"def target():\n    return 3\n",
            _spec(),
            "observed 0",
        ),
        (
            b"def target():\n    return 1\n    # return 1\n",
            _spec(),
            "observed 2",
        ),
        (
            b"def target():\n    return 1\n",
            _spec(replacement="return 1"),
            "no-op",
        ),
    ),
)
def test_exact_mutation_rejects_zero_multiple_and_noop_replacements(
    source: bytes,
    spec: MutantSpec,
    diagnostic: str,
) -> None:
    with pytest.raises(MutationAssuranceError, match=diagnostic):
        apply_exact_mutation(spec, source)


@pytest.mark.parametrize(
    "source_path",
    (
        "../escape.py",
        "/absolute.py",
        "moira/../tests/probe.py",
        r"moira\probe.py",
        "tests/probe.py",
        "src/native/probe.cpp",
    ),
)
def test_catalogue_rejects_escaping_test_and_native_source_targets(
    tmp_path: Path,
    source_path: str,
) -> None:
    with pytest.raises(
        MutationAssuranceError,
        match=r"(?:escapes|exact POSIX path|Python engine source)",
    ):
        _load_synthetic_catalogue(tmp_path, source_path=source_path)


def test_catalogue_rejects_an_escaping_intended_test_path(tmp_path: Path) -> None:
    payload = _catalogue_payload(source_path="moira/probe.py")
    mutant = payload["mutants"][0]
    assert isinstance(mutant, dict)
    mutant["intended_killer_nodeid"] = "../outside.py::test_probe"
    path = tmp_path / "catalogue.json"
    path.write_bytes(pretty_json_bytes(payload))

    with pytest.raises(MutationAssuranceError, match="escapes"):
        load_catalogue(
            path,
            root=tmp_path,
            contracts=CONTRACTS,
            verify_sources=False,
        )


@pytest.mark.parametrize(
    ("source_path", "target_qualname"),
    (
        ("moira/probe.py", "normalize_degrees"),
        ("moira/coordinates.py", "unrelated_target"),
    ),
    ids=("foreign-source", "foreign-qualname"),
)
def test_catalogue_target_must_be_declared_by_the_bound_contract(
    tmp_path: Path,
    source_path: str,
    target_qualname: str,
) -> None:
    payload = _catalogue_payload(
        source_path=source_path,
        target_qualname=target_qualname,
    )
    path = tmp_path / "catalogue.json"
    path.write_bytes(pretty_json_bytes(payload))

    with pytest.raises(MutationAssuranceError):
        load_catalogue(
            path,
            root=tmp_path,
            contracts=CONTRACTS,
            verify_sources=False,
        )


def test_verify_snapshot_accepts_only_the_exact_file_set_and_hashes(
    tmp_path: Path,
) -> None:
    root = tmp_path / "snapshot"
    root.mkdir()
    inputs = _snapshot(
        root,
        {
            "moira/probe.py": b"VALUE = 1\n",
            "tests/probe.txt": b"immutable test protocol\n",
        },
    )

    verify_snapshot(root, inputs)

    extra = root / "unexpected.txt"
    extra.write_bytes(b"unexpected\n")
    with pytest.raises(MutationAssuranceError, match="file set changed"):
        verify_snapshot(root, inputs)
    extra.unlink()

    missing = root / "tests" / "probe.txt"
    original = missing.read_bytes()
    missing.unlink()
    with pytest.raises(MutationAssuranceError, match="file set changed"):
        verify_snapshot(root, inputs)
    missing.write_bytes(original)

    target = root / "moira" / "probe.py"
    target.write_bytes(b"VALUE = 2\n")
    with pytest.raises(MutationAssuranceError, match="digest changed"):
        verify_snapshot(root, inputs)


def test_atomic_mutation_changes_only_the_declared_target(tmp_path: Path) -> None:
    root = tmp_path / "snapshot"
    root.mkdir()
    source_path = "moira/probe.py"
    source = b"def target():\n    return 1\n"
    postimage = b"def target():\n    return 2\n"
    files = {
        source_path: source,
        "tests/probe.txt": b"immutable test protocol\n",
    }
    inputs = _snapshot(root, files)
    spec = _spec(
        source_path=source_path,
        preimage_sha256=sha256_bytes(source),
        postimage_sha256=sha256_bytes(postimage),
    )
    before = {
        relative: (root / Path(relative)).read_bytes()
        for relative in files
    }

    returned = atomically_apply_mutant(root, inputs, spec)
    after = {
        relative: (root / Path(relative)).read_bytes()
        for relative in files
    }

    assert returned == postimage
    assert after[source_path] == postimage
    assert {
        relative
        for relative in files
        if before[relative] != after[relative]
    } == {source_path}
    assert not any(path.name.endswith(".tmp") for path in root.rglob("*"))
    verify_snapshot(
        root,
        inputs,
        overrides={source_path: sha256_bytes(postimage)},
    )


def test_atomic_mutation_rejects_target_drift_without_a_second_write(
    tmp_path: Path,
) -> None:
    root = tmp_path / "snapshot"
    root.mkdir()
    source_path = "moira/probe.py"
    source = b"def target():\n    return 1\n"
    drifted = b"def target():\n    return 9\n"
    inputs = _snapshot(
        root,
        {
            source_path: source,
            "tests/probe.txt": b"immutable test protocol\n",
        },
    )
    spec = _spec(
        source_path=source_path,
        preimage_sha256=sha256_bytes(source),
        postimage_sha256=sha256_bytes(
            b"def target():\n    return 2\n"
        ),
    )
    target = root / Path(source_path)
    target.write_bytes(drifted)

    with pytest.raises(MutationAssuranceError, match="target drifted"):
        atomically_apply_mutant(root, inputs, spec)

    assert target.read_bytes() == drifted
    assert (root / "tests" / "probe.txt").read_bytes() == (
        b"immutable test protocol\n"
    )


def test_atomic_mutation_rejects_a_stale_postimage_without_writing(
    tmp_path: Path,
) -> None:
    root = tmp_path / "snapshot"
    root.mkdir()
    source_path = "moira/probe.py"
    source = b"def target():\n    return 1\n"
    inputs = _snapshot(root, {source_path: source})
    spec = _spec(
        source_path=source_path,
        preimage_sha256=sha256_bytes(source),
        postimage_sha256=_ZERO_SHA256,
    )

    with pytest.raises(MutationAssuranceError, match="postimage digest mismatch"):
        atomically_apply_mutant(root, inputs, spec)

    assert (root / Path(source_path)).read_bytes() == source


def _receipt_file(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    return {
        "path": str(path.resolve(strict=True)),
        "path_truncated": False,
        "bytes": len(raw),
        "sha256": sha256_bytes(raw),
    }


def _module_receipt(
    path: Path,
    *,
    name: str,
    loader: str,
    loader_policy: str,
) -> dict[str, object]:
    return {
        "available": True,
        "name": name,
        "name_truncated": False,
        "file": _receipt_file(path),
        "file_error": None,
        "file_error_truncated": False,
        "spec": {
            "name": name,
            "name_truncated": False,
            "origin": str(path.resolve(strict=True)),
            "origin_truncated": False,
            "loader": loader,
            "loader_truncated": False,
            "loader_policy": loader_policy,
        },
    }


def _adjudication_spec(
    *,
    preimage: bytes,
    postimage: bytes,
) -> MutantSpec:
    contract = CONTRACTS[_CLAIM_ID]
    return MutantSpec(
        mutant_id="P11-SYNTHETIC-TYPED-KILL",
        criticality="critical",
        fault_archetype="synthetic typed adjudication",
        operator="replace_exact_utf8_v1",
        source_path="moira/probe.py",
        target_qualname="target",
        preimage="return 1",
        replacement="return 2",
        occurrence_count=1,
        source_hash_mode="utf8_lf_v1",
        preimage_sha256=sha256_bytes(preimage),
        postimage_sha256=sha256_bytes(postimage),
        preimage_ast_sha256=_canonical_ast_sha256(
            preimage,
            qualname="target",
        ),
        postimage_ast_sha256=_canonical_ast_sha256(
            postimage,
            qualname="target",
        ),
        preimage_code_sha256=python_source_code_sha256(
            preimage,
            qualname="target",
        ),
        postimage_code_sha256=python_source_code_sha256(
            postimage,
            qualname="target",
        ),
        patch_sha256=_ZERO_SHA256,
        intended_killer_nodeid=_KILLER_NODEID,
        expected_claim_id=_CLAIM_ID,
        expected_contract_sha256=contract_sha256(contract),
        evidence_class=contract.evidence_class.value,
        expected_failure=FailureExpectation(
            exception_type="support.metamorphic.MetamorphicViolation",
            message_contains=(_CLAIM_ID, _METRIC),
            longrepr_contains=(_CLAIM_ID, _METRIC),
            metamorphic_witness={
                "relation_id": _CLAIM_ID,
                "mutant_id": _BASELINE_MUTANT_ID,
                "metric": _METRIC,
            },
        ),
        requires_native_backend=False,
        timeout_seconds=30,
        exclusions=("synthetic adjudication probe",),
    )


def _evidence_properties(spec: MutantSpec) -> list[dict[str, object]]:
    return [
        {
            "name": "moira_validation_claim_id",
            "name_truncated": False,
            "value": spec.expected_claim_id,
            "value_truncated": False,
        },
        {
            "name": "moira_validation_contract_sha256",
            "name_truncated": False,
            "value": spec.expected_contract_sha256,
            "value_truncated": False,
        },
    ]


def _typed_exception() -> dict[str, object]:
    return {
        "type": "support.metamorphic.MetamorphicViolation",
        "type_truncated": False,
        "message": (
            f"{_CLAIM_ID} [{_BASELINE_MUTANT_ID}]: {_METRIC} "
            "observed=360, limit=359.99999999999994"
        ),
        "message_truncated": False,
        "metamorphic_violation": {
            "relation_id": _CLAIM_ID,
            "relation_id_truncated": False,
            "mutant_id": _BASELINE_MUTANT_ID,
            "mutant_id_truncated": False,
            "metric": _METRIC,
            "metric_truncated": False,
            "observed": 360.0,
            "limit": 359.99999999999994,
        },
    }


def _phase_report(
    spec: MutantSpec,
    *,
    sequence: int,
    phase: str,
    outcome: str,
) -> dict[str, object]:
    failed_call = phase == "call" and outcome == "failed"
    return {
        "sequence": sequence,
        "nodeid": spec.intended_killer_nodeid,
        "nodeid_truncated": False,
        "phase": phase,
        "outcome": outcome,
        "outcome_truncated": False,
        "duration_s": 0.001,
        "wasxfail": None,
        "wasxfail_truncated": False,
        "exception": _typed_exception() if failed_call else None,
        "evidence_user_properties": _evidence_properties(spec),
        "longrepr": (
            f"{_CLAIM_ID}: {_METRIC}" if failed_call else ""
        ),
        "longrepr_truncated": False,
        "rerun": False,
        "rerun_index": None,
    }


def _deterministic_mutation_seed(spec: MutantSpec) -> int:
    return int.from_bytes(
        hashlib.sha256(spec.mutant_id.encode("ascii")).digest()[:8],
        "big",
    )


def _role_execution_id(spec: MutantSpec, role: str) -> str:
    assert role in {"baseline", "mutant"}
    short = hashlib.sha256(spec.mutant_id.encode("ascii")).hexdigest()[:12]
    return f"{role}-{short}"


def _policy_environment(*, seed: int = 1337) -> dict[str, object]:
    values = {
        "MOIRA_TEST_MODE": "1",
        "MOIRA_NO_DOWNLOAD": "1",
        "MOIRA_STRICT_KNOWN_ISSUES": "1",
        "MOIRA_TEST_NETWORK_POLICY": "deny",
        "MOIRA_TEST_ARTIFACTS": "0",
        "MOIRA_TEST_SEED": str(seed),
        "MOIRA_TEST_BUDGET_TOTAL_S": "0",
        "MOIRA_TEST_BUDGET_CASE_S": "0",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
        "PYTHONNOUSERSITE": "1",
        "PYTHONOPTIMIZE": "0",
    }
    return {
        name: {"value": value, "truncated": False}
        for name, value in values.items()
    }


def _synthetic_test_toolchain(prefix: Path) -> dict[str, object]:
    distributions = [
        {
            "name": "hypothesis",
            "version": "0.synthetic",
            "import_paths": [
                "_hypothesis_ftz_detector.py",
                "_hypothesis_globals.py",
                "_hypothesis_pytestplugin.py",
                "hypothesis",
            ],
            "dist_info_path": (
                "Lib/site-packages/hypothesis-0.synthetic.dist-info"
            ),
            "file_count": 1,
            "bytes": 10,
            "sha256": sha256_bytes(b"synthetic hypothesis distribution\n"),
        },
        {
            "name": "pytest",
            "version": "0.synthetic",
            "import_paths": ["_pytest", "py.py", "pytest"],
            "dist_info_path": "Lib/site-packages/pytest-0.synthetic.dist-info",
            "file_count": 1,
            "bytes": 11,
            "sha256": sha256_bytes(b"synthetic pytest distribution\n"),
        },
        {
            "name": "pyyaml",
            "version": "0.synthetic",
            "import_paths": ["_yaml", "yaml"],
            "dist_info_path": "Lib/site-packages/pyyaml-0.synthetic.dist-info",
            "file_count": 1,
            "bytes": 12,
            "sha256": sha256_bytes(b"synthetic pyyaml distribution\n"),
        },
    ]
    for name, import_paths, byte_count in (
        ("anyio", ["anyio"], 13),
        ("execnet", ["execnet"], 14),
        ("pytest-cov", ["pytest_cov"], 15),
        ("pytest-xdist", ["xdist"], 16),
        ("typing-extensions", ["typing_extensions.py"], 17),
    ):
        distributions.append(
            {
                "name": name,
                "version": "0.synthetic",
                "import_paths": import_paths,
                "dist_info_path": (
                    f"Lib/site-packages/{name}-0.synthetic.dist-info"
                ),
                "file_count": 1,
                "bytes": byte_count,
                "sha256": sha256_bytes(
                    f"synthetic {name} distribution\n".encode("ascii")
                ),
            }
        )
    distributions.sort(key=lambda value: str(value["name"]))
    code_manifest = {
        "schema_version": 1,
        "object_count": 1,
        "binding_count": 1,
        "variants": {
            variant: {
                "object_count": 1,
                "sha256": sha256_bytes(
                    f"synthetic pytest {variant} code\n".encode("ascii")
                ),
                "binding_sha256": sha256_bytes(
                    f"synthetic pytest {variant} bindings\n".encode(
                        "ascii"
                    )
                ),
            }
            for variant in (
                "raw",
                "pytest_rewrite_disabled",
                "pytest_rewrite_enabled",
            )
        },
    }
    modules = [
        {
            "distribution": "pytest",
            "module": "pytest",
            "path": "Lib/site-packages/pytest/__init__.py",
            "loader_kind": "source",
            "bytes": 7,
            "sha256": sha256_bytes(b"synthetic pytest module\n"),
            "code_manifest": code_manifest,
        }
    ]
    startup_unsigned: dict[str, object] = {
        "scope": "active_prefix_site_startup_files_and_loaded_modules_v1",
        "import_roots": [],
        "module_names": [],
        "files": [],
        "file_count": 0,
        "bytes": 0,
    }
    startup = {
        **startup_unsigned,
        "sha256": sha256_bytes(canonical_json_bytes(startup_unsigned)),
    }
    unsigned: dict[str, object] = {
        "schema_version": 3,
        "roots": ["hypothesis", "pytest", "pyyaml"],
        "dependency_closure": ["hypothesis", "pytest", "pyyaml"],
        "host_roots": [
            "anyio",
            "execnet",
            "pytest-cov",
            "pytest-xdist",
            "typing-extensions",
        ],
        "host_dependency_closure": [
            "anyio",
            "execnet",
            "pytest-cov",
            "pytest-xdist",
            "typing-extensions",
        ],
        "byte_scope": (
            "plain_declared_import_and_dist_info_trees_no_ambient_bytecode_v1"
        ),
        "bytecode_policy": "isolated_pycache_prefix_and_no_write_v1",
        "prefix": str(prefix.resolve(strict=True)),
        "distributions": distributions,
        "startup": startup,
        "modules": modules,
        "module_manifest_sha256": sha256_bytes(canonical_json_bytes(modules)),
        "code_manifest_sha256": sha256_bytes(
            canonical_json_bytes(
                [
                    {
                        "module": module["module"],
                        "code_manifest": module["code_manifest"],
                    }
                    for module in modules
                ]
            )
        ),
        "file_count": sum(
            int(distribution["file_count"])
            for distribution in distributions
        ),
        "bytes": sum(
            int(distribution["bytes"])
            for distribution in distributions
        ),
    }
    return {
        **unsigned,
        "manifest_sha256": sha256_bytes(canonical_json_bytes(unsigned)),
    }


def _synthetic_loaded_test_toolchain(
    toolchain: dict[str, object],
) -> dict[str, object]:
    modules = toolchain["modules"]
    assert isinstance(modules, list)
    return {
        "schema_version": toolchain["schema_version"],
        "manifest_sha256": toolchain["manifest_sha256"],
        "module_manifest_sha256": toolchain["module_manifest_sha256"],
        "code_manifest_sha256": toolchain["code_manifest_sha256"],
        "module_count": len(modules),
        "code_object_count": sum(
            int(module["code_manifest"]["object_count"])
            for module in modules
            if isinstance(module, dict)
            and isinstance(module.get("code_manifest"), dict)
        ),
        "all_modules_match": True,
        "all_captured_modules_match": True,
        "normalized_lru_wrapper_names": list(_SYNTHETIC_LRU_WRAPPER_NAMES),
        "normalized_lru_wrapper_count": len(_SYNTHETIC_LRU_WRAPPER_NAMES),
        "normalized_lru_wrapper_sha256": _SYNTHETIC_LRU_WRAPPER_SHA256,
        "all_normalized_lru_wrappers_empty": True,
    }


def _child_report(
    *,
    spec: MutantSpec,
    snapshot_root: Path,
    interpreter_path: Path,
    native_backend_path: Path,
    expected_source_sha256: str,
    expected_code_sha256: str,
    outcomes: tuple[str, str, str],
    child_exit_code: int,
    execution_id: str = _EXECUTION_ID,
    seed: int = 1337,
) -> dict[str, object]:
    source = snapshot_root / Path(spec.source_path)
    intended_test = snapshot_root / Path(_INTENDED_TEST_RELATIVE)
    assert spec.intended_killer_nodeid == (
        f"{_INTENDED_TEST_RELATIVE}::{_INTENDED_TEST_QUALNAME}"
    )
    intended_test_code_sha256 = _intended_test_structural_sha256(
        intended_test.read_bytes(),
        filename=str(intended_test.resolve(strict=True)),
    )
    test_toolchain = _synthetic_test_toolchain(interpreter_path.parent)
    loaded_toolchain = _synthetic_loaded_test_toolchain(test_toolchain)
    modules = {
        "target_module": _module_receipt(
            source,
            name=spec.module_name,
            loader=_SOURCE_LOADER,
            loader_policy="source",
        ),
        "intended_test": _module_receipt(
            intended_test,
            name=_INTENDED_TEST_MODULE,
            loader=_PYTEST_REWRITE_LOADER,
            loader_policy="pytest_assertion_rewrite_disabled",
        ),
        "moira": _module_receipt(
            snapshot_root / "moira" / "__init__.py",
            name="moira",
            loader=_SOURCE_LOADER,
            loader_policy="source",
        ),
        "reporter": _module_receipt(
            snapshot_root / "tests" / "mutation_reporter.py",
            name="tests.mutation_reporter",
            loader=_PYTEST_REWRITE_LOADER,
            loader_policy="pytest_assertion_rewrite_disabled",
        ),
        "sitecustomize": _module_receipt(
            snapshot_root
            / "tests"
            / "support"
            / "network_bootstrap"
            / "sitecustomize.py",
            name="sitecustomize",
            loader=_SOURCE_LOADER,
            loader_policy="source",
        ),
        "toolchain": _module_receipt(
            snapshot_root / "tests" / "support" / "mutation_toolchain.py",
            name="support.mutation_toolchain",
            loader=_SOURCE_LOADER,
            loader_policy="source",
        ),
        "native_backend": _module_receipt(
            native_backend_path,
            name="moira._moira_native",
            loader=_EXTENSION_LOADER,
            loader_policy="extension",
        ),
    }
    return {
        "schema_version": 3,
        "execution_id": execution_id,
        "intended": {
            "nodeid": spec.intended_killer_nodeid,
            "source_relative_path": spec.source_path,
            "module_name": spec.module_name,
            "target_qualname": spec.target_qualname,
            "test_source_relative_path": _INTENDED_TEST_RELATIVE,
            "test_module_name": _INTENDED_TEST_MODULE,
            "test_qualname": _INTENDED_TEST_QUALNAME,
        },
        "selection": {
            "selected_nodeids": [
                {"nodeid": spec.intended_killer_nodeid, "truncated": False}
            ],
            "selected_count": 1,
            "intended_selected_count": 1,
            "only_intended_selected": True,
        },
        "errors": {"collection": [], "internal": []},
        "reports": [
            _phase_report(
                spec,
                sequence=index,
                phase=phase,
                outcome=outcome,
            )
            for index, (phase, outcome) in enumerate(
                zip(("setup", "call", "teardown"), outcomes),
                start=1,
            )
        ],
        "trace": {
            "algorithm": "python_code_v1",
            "attempted": True,
            "preexisting_tracer": False,
            "call_count": 1,
            "frame_filenames": [str(source.resolve(strict=True))],
            "code_sha256": [expected_code_sha256],
            "resolved_target_code_sha256": expected_code_sha256,
            "target_binding_exact": True,
            "intended_test_call_count": 1,
            "intended_test_frame_filenames": [
                str(intended_test.resolve(strict=True))
            ],
            "intended_test_code_sha256": [intended_test_code_sha256],
            "resolved_intended_test_code_sha256": (
                intended_test_code_sha256
            ),
        },
        "identity": {
            "interpreter": {
                "executable": _receipt_file(interpreter_path),
                "implementation": "CPython",
                "version": "3.14.3",
                "cache_tag": "cpython-314",
                "pycache_prefix": str(
                    (
                        snapshot_root.parent
                        / "control"
                        / f"pycache-{execution_id}"
                    ).resolve()
                ),
                "prefix": str(interpreter_path.parent.resolve(strict=True)),
                "base_prefix": str(
                    interpreter_path.parent.parent.resolve(strict=True)
                ),
                "flags": {
                    "safe_path": True,
                    "optimize": 0,
                    "dont_write_bytecode": True,
                    "no_user_site": True,
                },
            },
            "cwd": str(snapshot_root.resolve(strict=True)),
            "cwd_truncated": False,
            "root": str(snapshot_root.resolve(strict=True)),
            "root_truncated": False,
            "source": {
                **_receipt_file(source),
                "sha256": expected_source_sha256,
            },
            "modules": modules,
            "intended_test_callable": {
                "available": True,
                "type": "builtins.function",
                "module": _INTENDED_TEST_MODULE,
                "name": _INTENDED_TEST_QUALNAME,
                "qualname": _INTENDED_TEST_QUALNAME,
                "module_binding_exact": True,
                "wrapped": False,
                "code": {
                    "algorithm": "python_code_structural_v1",
                    "filename": str(intended_test.resolve(strict=True)),
                    "filename_truncated": False,
                    "qualname": _INTENDED_TEST_QUALNAME,
                    "sha256": intended_test_code_sha256,
                },
                "stable_during_execution": True,
            },
            "policy_environment": _policy_environment(seed=seed),
            "test_toolchain": {
                "schema_version": test_toolchain["schema_version"],
                "initial_manifest_sha256": (
                    test_toolchain["manifest_sha256"]
                ),
                "final_manifest_sha256": test_toolchain["manifest_sha256"],
                "module_manifest_sha256": (
                    loaded_toolchain["module_manifest_sha256"]
                ),
                "code_manifest_sha256": (
                    loaded_toolchain["code_manifest_sha256"]
                ),
                "module_count": loaded_toolchain["module_count"],
                "code_object_count": loaded_toolchain[
                    "code_object_count"
                ],
                "stable_during_execution": True,
                "all_modules_match": True,
                "all_captured_modules_match": True,
                "normalized_lru_wrapper_names": loaded_toolchain[
                    "normalized_lru_wrapper_names"
                ],
                "normalized_lru_wrapper_count": loaded_toolchain[
                    "normalized_lru_wrapper_count"
                ],
                "normalized_lru_wrapper_sha256": loaded_toolchain[
                    "normalized_lru_wrapper_sha256"
                ],
                "all_normalized_lru_wrappers_empty": loaded_toolchain[
                    "all_normalized_lru_wrappers_empty"
                ],
            },
            "network": {
                "available": True,
                "audit_hook_installed": True,
                "audit_canary_seen": True,
                "socket_method_guards_installed": True,
                "asyncio_method_guards_installed": True,
                "active_mode": "deny",
                "active_nodeid": "<session-finish>",
                "active_nodeid_truncated": False,
                "environment_mode": "deny",
            },
        },
        "pytest": {
            "exitstatus": {
                "code": child_exit_code,
                "name": "OK" if child_exit_code == 0 else "TESTS_FAILED",
            }
        },
    }


def _observation(
    spec: MutantSpec,
    report: dict[str, object],
    *,
    returncode: int,
) -> ProcessObservation:
    raw = pretty_json_bytes(report)
    identity = report["identity"]
    assert isinstance(identity, dict)
    snapshot_root = Path(str(identity["root"]))
    child_interpreter = identity["interpreter"]
    assert isinstance(child_interpreter, dict)
    executable = child_interpreter["executable"]
    assert isinstance(executable, dict)
    execution_id = report["execution_id"]
    assert isinstance(execution_id, str)
    return ProcessObservation(
        argv=_expected_child_argv(
            interpreter=str(executable["path"]),
            control_root=snapshot_root.parent / "control",
            spec=spec,
            execution_id=execution_id,
        ),
        returncode=returncode,
        timed_out=False,
        duration_ns=1_000_000,
        stdout="",
        stderr="",
        stdout_sha256=sha256_bytes(b""),
        stderr_sha256=sha256_bytes(b""),
        output_truncated=False,
        report=report,
        report_sha256=sha256_bytes(raw),
        report_error=None,
    )


def _adjudication_fixture(
    tmp_path: Path,
    *,
    mutated: bool,
    outcomes: tuple[str, str, str],
    parent_returncode: int,
    child_exit_code: int,
) -> tuple[
    MutantSpec,
    dict[str, object],
    ProcessObservation,
    dict[str, object],
]:
    snapshot_root = tmp_path / "snapshot"
    snapshot_root.mkdir()
    (tmp_path / "control" / "reports").mkdir(parents=True)
    preimage = b"def target():\n    return 1\n"
    postimage = b"def target():\n    return 2\n"
    spec = _adjudication_spec(preimage=preimage, postimage=postimage)
    active_source = postimage if mutated else preimage
    files = {
        spec.source_path: active_source,
        "moira/__init__.py": b"# synthetic package\n",
        "moira/_moira_native.synthetic.pyd": b"synthetic-native-backend\n",
        "tests/mutation_reporter.py": b"# synthetic reporter\n",
        _INTENDED_TEST_RELATIVE: _INTENDED_TEST_SOURCE,
        "tests/support/network_bootstrap/sitecustomize.py": (
            b"# synthetic sitecustomize\n"
        ),
        "tests/support/mutation_toolchain.py": (
            b"# synthetic mutation toolchain\n"
        ),
    }
    _snapshot(snapshot_root, files)
    interpreter_path = tmp_path / "runtime" / "python.exe"
    interpreter_path.parent.mkdir()
    interpreter_path.write_bytes(b"synthetic-project-interpreter\n")
    native_backend_path = (
        snapshot_root / "moira" / "_moira_native.synthetic.pyd"
    )
    expected_source_sha256 = (
        spec.postimage_sha256 if mutated else spec.preimage_sha256
    )
    expected_code_sha256 = (
        spec.postimage_code_sha256 if mutated else spec.preimage_code_sha256
    )
    report = _child_report(
        spec=spec,
        snapshot_root=snapshot_root,
        interpreter_path=interpreter_path,
        native_backend_path=native_backend_path,
        expected_source_sha256=expected_source_sha256,
        expected_code_sha256=expected_code_sha256,
        outcomes=outcomes,
        child_exit_code=child_exit_code,
    )
    observation = _observation(
        spec,
        report,
        returncode=parent_returncode,
    )
    common = {
        "execution_id": _EXECUTION_ID,
        "snapshot_root": snapshot_root,
        "interpreter": {
            "executable": str(interpreter_path.resolve(strict=True)),
            "sha256": sha256_bytes(interpreter_path.read_bytes()),
            "prefix": str(interpreter_path.parent.resolve(strict=True)),
            "base_prefix": str(
                interpreter_path.parent.parent.resolve(strict=True)
            ),
        },
        "native_backend_path": native_backend_path,
        "native_backend_sha256": sha256_bytes(
            native_backend_path.read_bytes()
        ),
    }
    return spec, report, observation, common


def _mutant_result(
    spec: MutantSpec,
    observation: ProcessObservation,
    common: dict[str, object],
) -> dict[str, object]:
    return adjudicate_mutant(
        spec=spec,
        observation=observation,
        **common,
    )


def test_adjudication_grants_credit_only_to_the_intended_typed_kill(
    tmp_path: Path,
) -> None:
    spec, report, observation, common = _adjudication_fixture(
        tmp_path,
        mutated=True,
        outcomes=("passed", "failed", "passed"),
        parent_returncode=1,
        child_exit_code=1,
    )

    result = _mutant_result(spec, observation, common)

    assert result["outcome"] == "killed_intended", result["reasons"]
    assert result["gate_credit"] is True
    assert result["reasons"] == []
    trace = report["trace"]
    assert isinstance(trace, dict)
    assert result["actual_killing_test"] == {
        "nodeid": spec.intended_killer_nodeid,
        "phase": "call",
        "claim_id": spec.expected_claim_id,
        "contract_sha256": spec.expected_contract_sha256,
        "test_source_relative_path": _INTENDED_TEST_RELATIVE,
        "test_module_name": _INTENDED_TEST_MODULE,
        "test_qualname": _INTENDED_TEST_QUALNAME,
        "test_code_sha256": trace[
            "resolved_intended_test_code_sha256"
        ],
        "exception": _typed_exception(),
    }


def test_adjudication_reports_a_clean_survivor_without_credit(
    tmp_path: Path,
) -> None:
    spec, _report, observation, common = _adjudication_fixture(
        tmp_path,
        mutated=True,
        outcomes=("passed", "passed", "passed"),
        parent_returncode=0,
        child_exit_code=0,
    )

    result = _mutant_result(spec, observation, common)

    assert result["outcome"] == "survived"
    assert result["gate_credit"] is False
    assert result["actual_killing_test"] is None


@pytest.mark.parametrize("corruption", ("exception_type", "witness"))
def test_adjudication_rejects_the_wrong_exception_or_witness(
    tmp_path: Path,
    corruption: str,
) -> None:
    spec, report, _observation_value, common = _adjudication_fixture(
        tmp_path,
        mutated=True,
        outcomes=("passed", "failed", "passed"),
        parent_returncode=1,
        child_exit_code=1,
    )
    call = report["reports"][1]
    assert isinstance(call, dict)
    exception = call["exception"]
    assert isinstance(exception, dict)
    if corruption == "exception_type":
        exception["type"] = "builtins.AssertionError"
    else:
        witness = exception["metamorphic_violation"]
        assert isinstance(witness, dict)
        witness["metric"] = "unrelated predicate"

    result = _mutant_result(
        spec,
        _observation(spec, report, returncode=1),
        common,
    )

    assert result["outcome"] == "wrong_killer"
    assert result["gate_credit"] is False
    assert result["actual_killing_test"] is None


@pytest.mark.parametrize("error_class", ("collection", "internal"))
def test_adjudication_rejects_collection_and_internal_errors(
    tmp_path: Path,
    error_class: str,
) -> None:
    spec, report, _observation_value, common = _adjudication_fixture(
        tmp_path,
        mutated=True,
        outcomes=("passed", "failed", "passed"),
        parent_returncode=1,
        child_exit_code=1,
    )
    errors = report["errors"]
    assert isinstance(errors, dict)
    errors[error_class] = [
        {
            "message": "synthetic reporter failure",
            "message_truncated": False,
        }
    ]

    result = _mutant_result(
        spec,
        _observation(spec, report, returncode=1),
        common,
    )

    assert result["outcome"] == "invalid_execution"
    assert result["gate_credit"] is False


@pytest.mark.parametrize(
    "outcomes",
    (
        ("failed", "passed", "passed"),
        ("passed", "passed", "failed"),
        ("passed", "failed", "failed"),
    ),
)
def test_adjudication_rejects_setup_or_teardown_failures(
    tmp_path: Path,
    outcomes: tuple[str, str, str],
) -> None:
    spec, _report, observation, common = _adjudication_fixture(
        tmp_path,
        mutated=True,
        outcomes=outcomes,
        parent_returncode=1,
        child_exit_code=1,
    )

    result = _mutant_result(spec, observation, common)

    assert result["outcome"] == "invalid_execution"
    assert result["gate_credit"] is False


@pytest.mark.parametrize("phase_index", (0, 2))
def test_adjudication_rejects_exception_on_a_passing_non_call_phase(
    tmp_path: Path,
    phase_index: int,
) -> None:
    spec, report, _observation_value, common = _adjudication_fixture(
        tmp_path,
        mutated=True,
        outcomes=("passed", "failed", "passed"),
        parent_returncode=1,
        child_exit_code=1,
    )
    phase = report["reports"][phase_index]
    assert isinstance(phase, dict)
    phase["exception"] = _typed_exception()

    result = _mutant_result(
        spec,
        _observation(spec, report, returncode=1),
        common,
    )

    assert result["outcome"] == "invalid_execution"
    assert result["gate_credit"] is False
    assert result["actual_killing_test"] is None


@pytest.mark.parametrize("corruption", ("wrong_phase_node", "extra_selection"))
def test_adjudication_rejects_wrong_or_additional_selected_nodes(
    tmp_path: Path,
    corruption: str,
) -> None:
    spec, report, _observation_value, common = _adjudication_fixture(
        tmp_path,
        mutated=True,
        outcomes=("passed", "failed", "passed"),
        parent_returncode=1,
        child_exit_code=1,
    )
    wrong = "tests/metamorphic/test_probe.py::test_unrelated"
    if corruption == "wrong_phase_node":
        call = report["reports"][1]
        assert isinstance(call, dict)
        call["nodeid"] = wrong
    else:
        selection = report["selection"]
        assert isinstance(selection, dict)
        selected = selection["selected_nodeids"]
        assert isinstance(selected, list)
        selected.append({"nodeid": wrong, "truncated": False})
        selection["selected_count"] = 2
        selection["only_intended_selected"] = False

    result = _mutant_result(
        spec,
        _observation(spec, report, returncode=1),
        common,
    )

    assert result["outcome"] == "invalid_execution"
    assert result["gate_credit"] is False


def test_malformed_child_report_is_observed_but_never_admitted(
    tmp_path: Path,
) -> None:
    spec, report, _observation_value, common = _adjudication_fixture(
        tmp_path,
        mutated=True,
        outcomes=("passed", "failed", "passed"),
        parent_returncode=1,
        child_exit_code=1,
    )
    selection = report["selection"]
    assert isinstance(selection, dict)
    selection["selected_count"] = 2
    observation = _observation(spec, report, returncode=1)

    result = _mutant_result(spec, observation, common)

    assert result["outcome"] == "invalid_execution"
    assert result["gate_credit"] is False
    assert result["child_report"] is None
    process = result["process"]
    assert isinstance(process, dict)
    assert process["observed_child_report"] == report
    assert process["report_sha256"] == observation.report_sha256


@pytest.mark.parametrize(
    ("outcomes", "parent_returncode", "child_exit_code"),
    (
        (("passed", "passed", "passed"), 1, 0),
        (("passed", "failed", "passed"), 0, 1),
        (("passed", "failed", "passed"), 1, 0),
    ),
)
def test_adjudication_rejects_parent_and_child_exit_mismatches(
    tmp_path: Path,
    outcomes: tuple[str, str, str],
    parent_returncode: int,
    child_exit_code: int,
) -> None:
    spec, _report, observation, common = _adjudication_fixture(
        tmp_path,
        mutated=True,
        outcomes=outcomes,
        parent_returncode=parent_returncode,
        child_exit_code=child_exit_code,
    )

    result = _mutant_result(spec, observation, common)

    assert result["outcome"] == "invalid_execution"
    assert result["gate_credit"] is False


def test_adjudication_never_counts_a_timeout_as_a_kill(tmp_path: Path) -> None:
    spec, _report, observation, common = _adjudication_fixture(
        tmp_path,
        mutated=True,
        outcomes=("passed", "failed", "passed"),
        parent_returncode=1,
        child_exit_code=1,
    )

    result = _mutant_result(
        spec,
        replace(observation, timed_out=True),
        common,
    )

    assert result["outcome"] == "timed_out"
    assert result["gate_credit"] is False
    assert result["actual_killing_test"] is None


def test_adjudication_rejects_truncated_kill_evidence(tmp_path: Path) -> None:
    spec, report, _observation_value, common = _adjudication_fixture(
        tmp_path,
        mutated=True,
        outcomes=("passed", "failed", "passed"),
        parent_returncode=1,
        child_exit_code=1,
    )
    call = report["reports"][1]
    assert isinstance(call, dict)
    call["longrepr_truncated"] = True

    result = _mutant_result(
        spec,
        _observation(spec, report, returncode=1),
        common,
    )

    assert result["outcome"] == "invalid_execution"
    assert result["gate_credit"] is False


@pytest.mark.parametrize(
    "corruption",
    ("missing_trace", "foreign_source", "wrong_code_digest"),
)
def test_adjudication_requires_exact_loaded_target_trace(
    tmp_path: Path,
    corruption: str,
) -> None:
    spec, report, _observation_value, common = _adjudication_fixture(
        tmp_path,
        mutated=True,
        outcomes=("passed", "failed", "passed"),
        parent_returncode=1,
        child_exit_code=1,
    )
    trace = report["trace"]
    assert isinstance(trace, dict)
    if corruption == "missing_trace":
        trace["call_count"] = 0
    elif corruption == "foreign_source":
        snapshot_root = common["snapshot_root"]
        assert isinstance(snapshot_root, Path)
        foreign = snapshot_root / "moira" / "foreign.py"
        foreign.write_bytes(b"# foreign target\n")
        trace["frame_filenames"] = [str(foreign.resolve(strict=True))]
    else:
        trace["code_sha256"] = [_ZERO_SHA256]

    result = _mutant_result(
        spec,
        _observation(spec, report, returncode=1),
        common,
    )

    assert result["outcome"] == "invalid_execution"
    assert result["gate_credit"] is False


@pytest.mark.parametrize("corruption", ("xfail", "rerun"))
def test_adjudication_rejects_xfail_and_rerun_evidence(
    tmp_path: Path,
    corruption: str,
) -> None:
    spec, report, _observation_value, common = _adjudication_fixture(
        tmp_path,
        mutated=True,
        outcomes=("passed", "failed", "passed"),
        parent_returncode=1,
        child_exit_code=1,
    )
    call = report["reports"][1]
    assert isinstance(call, dict)
    if corruption == "xfail":
        call["wasxfail"] = "known failure"
    else:
        call["rerun"] = True
        call["rerun_index"] = 1

    result = _mutant_result(
        spec,
        _observation(spec, report, returncode=1),
        common,
    )

    assert result["outcome"] == "invalid_execution"
    assert result["gate_credit"] is False


def test_baseline_failure_blocks_mutation_credit(tmp_path: Path) -> None:
    spec, _report, observation, common = _adjudication_fixture(
        tmp_path,
        mutated=False,
        outcomes=("passed", "failed", "passed"),
        parent_returncode=1,
        child_exit_code=1,
    )

    result = adjudicate_baseline(
        spec=spec,
        observation=observation,
        **common,
    )

    assert result["outcome"] == "blocked_baseline"
    assert result["gate_credit"] is False
    assert result["reasons"]


def _synthetic_receipt_inputs(
    tmp_path: Path,
    *,
    mutant_outcome: str = "killed_intended",
    evidence_class: str | None = None,
    requires_native_backend: bool = False,
) -> tuple[
    MutationCatalogue,
    SnapshotInputs,
    list[dict[str, object]],
    list[dict[str, object]],
]:
    execution_root = tmp_path / "receipt-execution"
    snapshot_root = execution_root / "snapshot"
    snapshot_root.mkdir(parents=True)
    (execution_root / "control" / "reports").mkdir(parents=True)
    preimage = b"def target():\n    return 1\n"
    postimage = b"def target():\n    return 2\n"
    spec = _adjudication_spec(preimage=preimage, postimage=postimage)
    spec = replace(
        spec,
        evidence_class=evidence_class or spec.evidence_class,
        requires_native_backend=requires_native_backend,
    )
    snapshot = _snapshot(
        snapshot_root,
        {
            spec.source_path: preimage,
            "moira/__init__.py": b"# synthetic package\n",
            "moira/_moira_native.synthetic.pyd": (
                b"synthetic-native-backend\n"
            ),
            "tests/mutation_reporter.py": b"# synthetic reporter\n",
            "conftest.py": b"# synthetic root conftest\n",
            "scripts/run_scientific_mutations.py": b"# synthetic runner\n",
            _INTENDED_TEST_RELATIVE: _INTENDED_TEST_SOURCE,
            "tests/evidence/__init__.py": b"# synthetic evidence package\n",
            "tests/evidence/contracts.py": b"# synthetic contracts\n",
            "tests/_pytest_plugins/__init__.py": (
                b"# synthetic pytest plugin package\n"
            ),
            "tests/support/mutation_assurance.py": (
                b"# synthetic adjudicator\n"
            ),
            "tests/_pytest_plugins/evidence_schema.py": (
                b"# synthetic evidence schema\n"
            ),
            "tests/support/network_bootstrap/sitecustomize.py": (
                b"# synthetic sitecustomize\n"
            ),
            "tests/support/mutation_toolchain.py": (
                b"# synthetic mutation toolchain\n"
            ),
            "tests/support/__init__.py": b"# synthetic support package\n",
        },
    )
    interpreter_path = tmp_path / "runtime" / "python.exe"
    interpreter_path.parent.mkdir()
    interpreter_path.write_bytes(b"synthetic-project-interpreter\n")
    native_backend_path = (
        snapshot_root / "moira" / "_moira_native.synthetic.pyd"
    )
    interpreter = {
        "executable": str(interpreter_path.resolve(strict=True)),
        "sha256": sha256_bytes(interpreter_path.read_bytes()),
        "prefix": str(interpreter_path.parent.resolve(strict=True)),
        "base_prefix": str(
            interpreter_path.parent.parent.resolve(strict=True)
        ),
    }
    common = {
        "snapshot_root": snapshot_root,
        "interpreter": interpreter,
        "native_backend_path": native_backend_path,
        "native_backend_sha256": sha256_bytes(
            native_backend_path.read_bytes()
        ),
    }
    seed = _deterministic_mutation_seed(spec)
    baseline_execution_id = _role_execution_id(spec, "baseline")
    mutant_execution_id = _role_execution_id(spec, "mutant")
    baseline_report = _child_report(
        spec=spec,
        snapshot_root=snapshot_root,
        interpreter_path=interpreter_path,
        native_backend_path=native_backend_path,
        expected_source_sha256=spec.preimage_sha256,
        expected_code_sha256=spec.preimage_code_sha256,
        outcomes=("passed", "passed", "passed"),
        child_exit_code=0,
        execution_id=baseline_execution_id,
        seed=seed,
    )
    baseline = adjudicate_baseline(
        spec=spec,
        observation=_observation(
            spec,
            baseline_report,
            returncode=0,
        ),
        execution_id=baseline_execution_id,
        **common,
    )

    (snapshot_root / Path(spec.source_path)).write_bytes(postimage)
    if mutant_outcome == "killed_intended":
        outcomes = ("passed", "failed", "passed")
        exit_code = 1
    elif mutant_outcome == "survived":
        outcomes = ("passed", "passed", "passed")
        exit_code = 0
    else:
        raise AssertionError(f"unsupported synthetic outcome {mutant_outcome}")
    mutant_report = _child_report(
        spec=spec,
        snapshot_root=snapshot_root,
        interpreter_path=interpreter_path,
        native_backend_path=native_backend_path,
        expected_source_sha256=spec.postimage_sha256,
        expected_code_sha256=spec.postimage_code_sha256,
        outcomes=outcomes,
        child_exit_code=exit_code,
        execution_id=mutant_execution_id,
        seed=seed,
    )
    mutant = adjudicate_mutant(
        spec=spec,
        observation=_observation(
            spec,
            mutant_report,
            returncode=exit_code,
        ),
        execution_id=mutant_execution_id,
        **common,
    )
    assert baseline["outcome"] == "baseline_passed", baseline["reasons"]
    assert mutant["outcome"] == mutant_outcome, mutant["reasons"]

    catalogue_path = tmp_path / "synthetic-catalogue.json"
    catalogue_raw = pretty_json_bytes(
        {
            "schema_version": 1,
            "synthetic": True,
            "mutant_ids": [spec.mutant_id],
        }
    )
    catalogue_path.write_bytes(catalogue_raw)
    catalogue = MutationCatalogue(
        path=catalogue_path,
        sha256=sha256_bytes(catalogue_raw),
        policy={"aggregate_gate": "all_declared_mutants_no_percentage"},
        mutants=(spec,),
    )
    return catalogue, snapshot, [baseline], [mutant]


def _synthetic_interpreter(
    baselines: list[dict[str, object]],
) -> dict[str, object]:
    baseline_report = baselines[0].get("child_report")
    if isinstance(baseline_report, dict):
        identity = baseline_report["identity"]
        assert isinstance(identity, dict)
        child_interpreter = identity["interpreter"]
        assert isinstance(child_interpreter, dict)
        executable = child_interpreter["executable"]
        assert isinstance(executable, dict)
        prefix = Path(str(child_interpreter["prefix"]))
        executable_path = str(executable["path"])
        toolchain = _synthetic_test_toolchain(prefix)
        return {
            "schema_version": 2,
            "executable": executable_path,
            "executable_resolved": executable_path,
            "sha256": executable["sha256"],
            "bytes": executable["bytes"],
            "prefix": child_interpreter["prefix"],
            "base_prefix": child_interpreter["base_prefix"],
            "implementation": "cpython",
            "version": [3, 14, 3],
            "launcher": {
                "schema_version": 1,
                "path": executable_path,
                "resolved_path": executable_path,
                "directory_resolved": str(prefix),
                "symlinks": [],
            },
            "runtime": {
                "schema_version": 1,
                "scope": (
                    "venv_config_base_executable_core_runtime_stdlib_"
                    "plain_files_v1"
                ),
                "roots": {
                    "venv_config": str(prefix / "pyvenv.cfg"),
                    "base_executable": executable_path,
                    "stdlib": str(prefix / "Lib"),
                    "auxiliary_trees": [],
                    "core_files": [],
                    "startup_control_files": [],
                    "startup_import_path": [
                        {
                            "index": 0,
                            "path": str(prefix / "Lib"),
                            "resolved": str(prefix / "Lib"),
                            "state": "directory",
                            "scope": "runtime_tree",
                        }
                    ],
                },
                "file_count": 1,
                "bytes": 1,
                "manifest_sha256": sha256_bytes(
                    b"synthetic interpreter runtime manifest\n"
                ),
            },
            "test_toolchain": toolchain,
            "loaded_test_toolchain": _synthetic_loaded_test_toolchain(
                toolchain
            ),
        }
    return {"implementation": "cpython", "synthetic": True}


def _synthetic_native_build(
    catalogue: MutationCatalogue,
    snapshot: SnapshotInputs,
    *,
    manifest_sha256: str | None = None,
) -> dict[str, object]:
    backend = snapshot.by_path[snapshot.native_backend_path]
    manifest = manifest_sha256 or sha256_bytes(
        b"synthetic native build input manifest\n"
    )
    return {
        "schema_version": 1,
        "required_mutant_ids": [
            spec.mutant_id
            for spec in catalogue.mutants
            if spec.requires_native_backend
        ],
        "backend_path": snapshot.native_backend_path,
        "backend_bytes": backend.bytes,
        "backend_sha256": backend.sha256,
        "embedded_input_sha256": manifest,
        "build_input_manifest_sha256": manifest,
        "build_input_count": 4,
        "matches_current_inputs": True,
    }


def _seal_synthetic_receipt(
    *,
    artifact_root: Path,
    run_id: str,
    catalogue: MutationCatalogue,
    snapshot: SnapshotInputs,
    baselines: list[dict[str, object]],
    mutants: list[dict[str, object]],
    started_utc: str = "2026-08-01T12:00:00Z",
    finished_utc: str = "2026-08-01T12:00:01Z",
    native_build: dict[str, object] | None = None,
    interpreter_override: dict[str, object] | None = None,
    pre_publish_check: Callable[[], None] | None = None,
) -> Path:
    interpreter = interpreter_override or _synthetic_interpreter(baselines)
    parent_modules: list[dict[str, object]] = []
    for role, module_name, relative in (
        ("runner", "__main__", "scripts/run_scientific_mutations.py"),
        (
            "evidence_package",
            "evidence",
            "tests/evidence/__init__.py",
        ),
        (
            "plugin_package",
            "_pytest_plugins",
            "tests/_pytest_plugins/__init__.py",
        ),
        (
            "evidence_schema",
            "_pytest_plugins.evidence_schema",
            "tests/_pytest_plugins/evidence_schema.py",
        ),
        ("contracts", "evidence.contracts", "tests/evidence/contracts.py"),
        (
            "support_package",
            "support",
            "tests/support/__init__.py",
        ),
        (
            "adjudicator",
            "support.mutation_assurance",
            "tests/support/mutation_assurance.py",
        ),
        (
            "toolchain",
            "support.mutation_toolchain",
            "tests/support/mutation_toolchain.py",
        ),
    ):
        source = snapshot.by_path[relative]
        parent_modules.append(
            {
                "role": role,
                "module_name": module_name,
                "path": relative,
                "bytes": source.bytes,
                "sha256": source.sha256,
            }
        )
    parent_runtime = {
        "module_import_policy": (
            "frozen_stage_one_no_preload_isolated_empty_pycache_no_write"
        ),
        "modules": parent_modules,
    }
    return seal_mutation_receipt(
        artifact_root=artifact_root,
        run_id=run_id,
        catalogue=catalogue,
        snapshot=snapshot,
        interpreter=interpreter,
        parent_runtime=parent_runtime,
        baselines=baselines,
        mutants=mutants,
        started_utc=started_utc,
        finished_utc=finished_utc,
        native_build=native_build,
        pre_publish_check=pre_publish_check,
    )


def _resign_adjudication_record(
    record: dict[str, object],
) -> dict[str, object]:
    resigned = deepcopy(record)
    resigned.pop("adjudication_sha256", None)
    resigned["adjudication_sha256"] = sha256_bytes(
        canonical_json_bytes(resigned)
    )
    return resigned


def _admitted_and_observed_reports(
    record: dict[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    admitted = record["child_report"]
    process = record["process"]
    assert isinstance(admitted, dict)
    assert isinstance(process, dict)
    observed = process["observed_child_report"]
    assert isinstance(observed, dict)
    return admitted, observed


def _rewrite_adjudication_interpreter_paths(
    original: dict[str, object],
    *,
    argv_executable: str,
    child_executable: str,
) -> dict[str, object]:
    record = deepcopy(original)
    process = record["process"]
    assert isinstance(process, dict)
    argv = process["argv"]
    assert isinstance(argv, list)
    argv[0] = argv_executable

    admitted, observed = _admitted_and_observed_reports(record)
    for report in (admitted, observed):
        identity = report["identity"]
        assert isinstance(identity, dict)
        child_interpreter = identity["interpreter"]
        assert isinstance(child_interpreter, dict)
        executable = child_interpreter["executable"]
        assert isinstance(executable, dict)
        executable["path"] = child_executable

    process["report_sha256"] = sha256_bytes(pretty_json_bytes(observed))
    return _resign_adjudication_record(record)


def _corrupt_green_mutant(
    original: dict[str, object],
    *,
    corruption: str,
    baseline: dict[str, object] | None = None,
) -> dict[str, object]:
    record = deepcopy(original)
    if corruption == "adjudication_digest":
        record["adjudication_sha256"] = _ZERO_SHA256
        return record

    process = record["process"]
    assert isinstance(process, dict)
    admitted, observed = _admitted_and_observed_reports(record)
    reports = (admitted, observed)
    if corruption == "argv":
        argv = process["argv"]
        assert isinstance(argv, list)
        argv.insert(4, "--collect-only")
    elif corruption == "selection":
        wrong = "tests/metamorphic/test_probe.py::test_unrelated"
        for report in reports:
            selection = report["selection"]
            assert isinstance(selection, dict)
            selected = selection["selected_nodeids"]
            assert isinstance(selected, list)
            selected.append({"nodeid": wrong, "truncated": False})
            selection["selected_count"] = 2
            selection["only_intended_selected"] = False
    elif corruption == "phase":
        for report in reports:
            phases = report["reports"]
            assert isinstance(phases, list)
            call = phases[1]
            assert isinstance(call, dict)
            call["outcome"] = "passed"
    elif corruption == "passed_phase_exception":
        for report in reports:
            phases = report["reports"]
            assert isinstance(phases, list)
            setup = phases[0]
            assert isinstance(setup, dict)
            setup["exception"] = _typed_exception()
    elif corruption == "source":
        for report in reports:
            identity = report["identity"]
            assert isinstance(identity, dict)
            source = identity["source"]
            modules = identity["modules"]
            assert isinstance(source, dict)
            assert isinstance(modules, dict)
            target_module = modules["target_module"]
            assert isinstance(target_module, dict)
            target_file = target_module["file"]
            assert isinstance(target_file, dict)
            source["sha256"] = _ZERO_SHA256
            target_file["sha256"] = _ZERO_SHA256
    elif corruption == "foreign_root":
        old_root: str | None = None
        new_root: str | None = None
        for report in reports:
            identity = report["identity"]
            trace = report["trace"]
            assert isinstance(identity, dict)
            assert isinstance(trace, dict)
            observed_root = identity["root"]
            assert isinstance(observed_root, str)
            if old_root is None:
                old_root = observed_root
                root_path = Path(observed_root)
                new_root = str(
                    root_path.parent.parent
                    / "foreign-execution"
                    / "snapshot"
                )
            assert old_root is not None and new_root is not None
            identity["root"] = new_root
            identity["cwd"] = new_root
            source = identity["source"]
            modules = identity["modules"]
            assert isinstance(source, dict)
            assert isinstance(modules, dict)
            source["path"] = str(source["path"]).replace(
                old_root,
                new_root,
                1,
            )
            for module in modules.values():
                assert isinstance(module, dict)
                module_file = module["file"]
                module_spec = module["spec"]
                assert isinstance(module_file, dict)
                assert isinstance(module_spec, dict)
                module_file["path"] = str(module_file["path"]).replace(
                    old_root,
                    new_root,
                    1,
                )
                module_spec["origin"] = str(
                    module_spec["origin"]
                ).replace(old_root, new_root, 1)
            filenames = trace["frame_filenames"]
            assert isinstance(filenames, list)
            trace["frame_filenames"] = [
                str(value).replace(old_root, new_root, 1)
                for value in filenames
            ]
        assert old_root is not None and new_root is not None
        old_control = str(Path(old_root).parent / "control")
        new_control = str(Path(new_root).parent / "control")
        argv = process["argv"]
        assert isinstance(argv, list)
        process["argv"] = [
            str(value).replace(old_control, new_control, 1)
            for value in argv
        ]
    elif corruption == "foreign_source_path":
        for report in reports:
            identity = report["identity"]
            trace = report["trace"]
            assert isinstance(identity, dict)
            assert isinstance(trace, dict)
            root = Path(str(identity["root"]))
            foreign = str(root / "moira" / "foreign.py")
            source = identity["source"]
            modules = identity["modules"]
            assert isinstance(source, dict)
            assert isinstance(modules, dict)
            target_module = modules["target_module"]
            assert isinstance(target_module, dict)
            target_file = target_module["file"]
            target_spec = target_module["spec"]
            assert isinstance(target_file, dict)
            assert isinstance(target_spec, dict)
            source["path"] = foreign
            target_file["path"] = foreign
            target_spec["origin"] = foreign
            trace["frame_filenames"] = [foreign]
    elif corruption == "foreign_module_path":
        for report in reports:
            identity = report["identity"]
            assert isinstance(identity, dict)
            root = Path(str(identity["root"]))
            foreign = str(root / "foreign" / "mutation_reporter.py")
            modules = identity["modules"]
            assert isinstance(modules, dict)
            reporter = modules["reporter"]
            assert isinstance(reporter, dict)
            reporter_file = reporter["file"]
            reporter_spec = reporter["spec"]
            assert isinstance(reporter_file, dict)
            assert isinstance(reporter_spec, dict)
            reporter_file["path"] = foreign
            reporter_spec["origin"] = foreign
    elif corruption == "intended_loader_policy":
        for report in reports:
            identity = report["identity"]
            assert isinstance(identity, dict)
            modules = identity["modules"]
            assert isinstance(modules, dict)
            intended_test = modules["intended_test"]
            assert isinstance(intended_test, dict)
            specification = intended_test["spec"]
            assert isinstance(specification, dict)
            specification["loader_policy"] = "source"
    elif corruption == "intended_callable_digest":
        for report in reports:
            identity = report["identity"]
            assert isinstance(identity, dict)
            intended_callable = identity["intended_test_callable"]
            assert isinstance(intended_callable, dict)
            code = intended_callable["code"]
            assert isinstance(code, dict)
            code["sha256"] = _ZERO_SHA256
    elif corruption == "intended_source_base64":
        test_source = record["intended_test_source"]
        assert isinstance(test_source, dict)
        test_source["source_base64"] = base64.b64encode(
            _FORGED_INTENDED_TEST_SOURCE
        ).decode("ascii")
    elif corruption == "intended_source_synchronized":
        forged = _synthetic_intended_test_source_receipt(
            _FORGED_INTENDED_TEST_SOURCE
        )
        record["intended_test_source"] = forged
        forged_sha256 = forged["source_sha256"]
        forged_code_sha256 = forged["code_sha256"]
        for report in reports:
            identity = report["identity"]
            trace = report["trace"]
            assert isinstance(identity, dict)
            assert isinstance(trace, dict)
            modules = identity["modules"]
            intended_callable = identity["intended_test_callable"]
            assert isinstance(modules, dict)
            assert isinstance(intended_callable, dict)
            intended_module = modules["intended_test"]
            callable_code = intended_callable["code"]
            assert isinstance(intended_module, dict)
            assert isinstance(callable_code, dict)
            module_file = intended_module["file"]
            assert isinstance(module_file, dict)
            module_file["bytes"] = len(_FORGED_INTENDED_TEST_SOURCE)
            module_file["sha256"] = forged_sha256
            callable_code["sha256"] = forged_code_sha256
            trace["intended_test_code_sha256"] = [forged_code_sha256]
            trace["resolved_intended_test_code_sha256"] = (
                forged_code_sha256
            )
        actual = record["actual_killing_test"]
        assert isinstance(actual, dict)
        actual["test_code_sha256"] = forged_code_sha256
    elif corruption == "baseline_runtime_digest":
        assert baseline is not None
        baseline_source = baseline["source_identity"]
        mutation = record["source_mutation"]
        assert isinstance(baseline_source, dict)
        assert isinstance(mutation, dict)
        baseline_digest = baseline_source["runtime_source_sha256"]
        assert isinstance(baseline_digest, str)
        mutation["runtime_source_sha256"] = baseline_digest
        for report in reports:
            identity = report["identity"]
            assert isinstance(identity, dict)
            source = identity["source"]
            modules = identity["modules"]
            assert isinstance(source, dict)
            assert isinstance(modules, dict)
            target_module = modules["target_module"]
            assert isinstance(target_module, dict)
            target_file = target_module["file"]
            assert isinstance(target_file, dict)
            source["sha256"] = baseline_digest
            target_file["sha256"] = baseline_digest
    elif corruption == "source_bytes":
        for report in reports:
            identity = report["identity"]
            assert isinstance(identity, dict)
            source = identity["source"]
            modules = identity["modules"]
            assert isinstance(source, dict)
            assert isinstance(modules, dict)
            target_module = modules["target_module"]
            assert isinstance(target_module, dict)
            target_file = target_module["file"]
            assert isinstance(target_file, dict)
            source["bytes"] = 999_991
            target_file["bytes"] = 999_991
    elif corruption == "module_bytes":
        for report in reports:
            identity = report["identity"]
            assert isinstance(identity, dict)
            modules = identity["modules"]
            assert isinstance(modules, dict)
            reporter = modules["reporter"]
            assert isinstance(reporter, dict)
            reporter_file = reporter["file"]
            assert isinstance(reporter_file, dict)
            reporter_file["bytes"] = 999_992
    elif corruption == "interpreter_bytes":
        for report in reports:
            identity = report["identity"]
            assert isinstance(identity, dict)
            child_interpreter = identity["interpreter"]
            assert isinstance(child_interpreter, dict)
            executable = child_interpreter["executable"]
            assert isinstance(executable, dict)
            executable["bytes"] = 999_993
    elif corruption in {
        "child_implementation",
        "child_version",
        "child_cache_tag",
    }:
        key, forged = {
            "child_implementation": ("implementation", "PyPy"),
            "child_version": ("version", "9.9.9"),
            "child_cache_tag": ("cache_tag", "cpython-999"),
        }[corruption]
        for report in reports:
            identity = report["identity"]
            assert isinstance(identity, dict)
            child_interpreter = identity["interpreter"]
            assert isinstance(child_interpreter, dict)
            child_interpreter[key] = forged
    elif corruption in {
        "child_toolchain_initial",
        "child_toolchain_final",
        "child_toolchain_unstable",
        "child_toolchain_lru_names",
        "child_toolchain_lru_count",
        "child_toolchain_lru_digest",
        "child_toolchain_lru_nonempty",
    }:
        for report in reports:
            identity = report["identity"]
            assert isinstance(identity, dict)
            toolchain = identity["test_toolchain"]
            assert isinstance(toolchain, dict)
            if corruption == "child_toolchain_initial":
                toolchain["initial_manifest_sha256"] = _ZERO_SHA256
            elif corruption == "child_toolchain_final":
                toolchain["final_manifest_sha256"] = _ZERO_SHA256
            elif corruption == "child_toolchain_lru_names":
                toolchain["normalized_lru_wrapper_names"] = [
                    *toolchain["normalized_lru_wrapper_names"],
                    "synthetic.zzz",
                ]
            elif corruption == "child_toolchain_lru_count":
                toolchain["normalized_lru_wrapper_count"] = (
                    int(toolchain["normalized_lru_wrapper_count"]) + 1
                )
            elif corruption == "child_toolchain_lru_digest":
                toolchain["normalized_lru_wrapper_sha256"] = _ZERO_SHA256
            elif corruption == "child_toolchain_lru_nonempty":
                toolchain["all_normalized_lru_wrappers_empty"] = False
            else:
                toolchain["stable_during_execution"] = False
    elif corruption == "mutant_execution_id":
        admitted_execution_id = admitted["execution_id"]
        assert isinstance(admitted_execution_id, str)
        forged_execution_id = "mutant-000000000000"
        for report in reports:
            report["execution_id"] = forged_execution_id
        argv = process["argv"]
        assert isinstance(argv, list)
        process["argv"] = [
            str(value).replace(
                admitted_execution_id,
                forged_execution_id,
            )
            for value in argv
        ]
    elif corruption == "mutation_seed":
        for report in reports:
            identity = report["identity"]
            assert isinstance(identity, dict)
            environment = identity["policy_environment"]
            assert isinstance(environment, dict)
            seed = environment["MOIRA_TEST_SEED"]
            assert isinstance(seed, dict)
            seed["value"] = "42"
    elif corruption == "code":
        for report in reports:
            trace = report["trace"]
            assert isinstance(trace, dict)
            trace["code_sha256"] = [_ZERO_SHA256]
            trace["resolved_target_code_sha256"] = _ZERO_SHA256
    elif corruption == "intended_trace_digest":
        test_source = record["intended_test_source"]
        assert isinstance(test_source, dict)
        test_source["code_sha256"] = _ZERO_SHA256
        for report in reports:
            identity = report["identity"]
            trace = report["trace"]
            assert isinstance(identity, dict)
            assert isinstance(trace, dict)
            intended_callable = identity["intended_test_callable"]
            assert isinstance(intended_callable, dict)
            callable_code = intended_callable["code"]
            assert isinstance(callable_code, dict)
            callable_code["sha256"] = _ZERO_SHA256
            trace["intended_test_code_sha256"] = [_ZERO_SHA256]
            trace["resolved_intended_test_code_sha256"] = _ZERO_SHA256
        actual = record["actual_killing_test"]
        assert isinstance(actual, dict)
        actual["test_code_sha256"] = _ZERO_SHA256
    elif corruption == "exception":
        for report in reports:
            phases = report["reports"]
            assert isinstance(phases, list)
            call = phases[1]
            assert isinstance(call, dict)
            exception = call["exception"]
            assert isinstance(exception, dict)
            exception["type"] = "builtins.AssertionError"
        actual = record["actual_killing_test"]
        assert isinstance(actual, dict)
        actual_exception = actual["exception"]
        assert isinstance(actual_exception, dict)
        actual_exception["type"] = "builtins.AssertionError"
    elif corruption == "process":
        process["returncode"] = 0
    elif corruption == "report_digest":
        process["report_sha256"] = _ZERO_SHA256
    else:
        raise AssertionError(f"unsupported corruption {corruption}")

    if corruption not in {"process", "report_digest"}:
        process["report_sha256"] = sha256_bytes(pretty_json_bytes(observed))
    return _resign_adjudication_record(record)


def _replace_mutant_and_reseal_envelope(
    receipt: Path,
    mutant: dict[str, object],
) -> None:
    mutants_path = receipt / "mutants.json"
    mutants_doc = strict_json_bytes(
        mutants_path.read_bytes(),
        label="synthetic mutation results",
    )
    assert isinstance(mutants_doc, dict)
    mutants_doc["mutants"] = [mutant]
    mutants_path.write_bytes(pretty_json_bytes(mutants_doc))

    _reseal_receipt_envelope(receipt)


def _replace_baseline_and_reseal_envelope(
    receipt: Path,
    baseline: dict[str, object],
) -> None:
    baselines_path = receipt / "baselines.json"
    baselines_doc = strict_json_bytes(
        baselines_path.read_bytes(),
        label="synthetic mutation baselines",
    )
    assert isinstance(baselines_doc, dict)
    baselines_doc["baselines"] = [baseline]
    baselines_path.write_bytes(pretty_json_bytes(baselines_doc))

    _reseal_receipt_envelope(receipt)


def _forge_baseline_execution_id(
    original: dict[str, object],
) -> dict[str, object]:
    record = deepcopy(original)
    admitted, observed = _admitted_and_observed_reports(record)
    old_execution_id = record["execution_id"]
    assert isinstance(old_execution_id, str)
    forged_execution_id = "baseline-000000000000"
    record["execution_id"] = forged_execution_id
    admitted["execution_id"] = forged_execution_id
    observed["execution_id"] = forged_execution_id
    process = record["process"]
    assert isinstance(process, dict)
    argv = process["argv"]
    assert isinstance(argv, list)
    process["argv"] = [
        str(value).replace(old_execution_id, forged_execution_id)
        for value in argv
    ]
    process["report_sha256"] = sha256_bytes(pretty_json_bytes(observed))
    return _resign_adjudication_record(record)


def _reseal_receipt_envelope(receipt: Path) -> None:
    """Re-sign the unkeyed outer envelope after an adversarial rewrite."""

    complete_path = receipt / "COMPLETE"
    complete = strict_json_bytes(
        complete_path.read_bytes(),
        label="synthetic mutation COMPLETE",
    )
    assert isinstance(complete, dict)
    files = complete["files"]
    assert isinstance(files, list)
    for identity in files:
        assert isinstance(identity, dict)
        name = identity["path"]
        assert isinstance(name, str)
        raw = (receipt / name).read_bytes()
        identity["bytes"] = len(raw)
        identity["sha256"] = sha256_bytes(raw)
    unsigned = dict(complete)
    unsigned.pop("manifest_sha256")
    complete["manifest_sha256"] = sha256_bytes(
        canonical_json_bytes(unsigned)
    )
    complete_path.write_bytes(pretty_json_bytes(complete))


def _replace_native_build_and_reseal_envelope(
    receipt: Path,
    native_build: dict[str, object] | None,
) -> None:
    run_path = receipt / "run.json"
    run = strict_json_bytes(
        run_path.read_bytes(),
        label="synthetic mutation run",
    )
    assert isinstance(run, dict)
    run["native_build"] = native_build
    run_path.write_bytes(pretty_json_bytes(run))
    _reseal_receipt_envelope(receipt)


def _replace_interpreter_and_reseal_envelope(
    receipt: Path,
    interpreter: dict[str, object],
) -> None:
    run_path = receipt / "run.json"
    run = strict_json_bytes(
        run_path.read_bytes(),
        label="synthetic mutation run",
    )
    assert isinstance(run, dict)
    run["interpreter"] = interpreter
    run_path.write_bytes(pretty_json_bytes(run))
    _reseal_receipt_envelope(receipt)


def _replace_boundaries_and_reseal_envelope(
    receipt: Path,
    boundaries: dict[str, object],
) -> None:
    run_path = receipt / "run.json"
    run = strict_json_bytes(
        run_path.read_bytes(),
        label="synthetic mutation run",
    )
    assert isinstance(run, dict)
    run["boundaries"] = boundaries
    run_path.write_bytes(pretty_json_bytes(run))
    _reseal_receipt_envelope(receipt)


def _drift_parent_toolchain_distribution(
    interpreter: dict[str, object],
) -> dict[str, object]:
    drifted = deepcopy(interpreter)
    toolchain = drifted["test_toolchain"]
    loaded = drifted["loaded_test_toolchain"]
    assert isinstance(toolchain, dict)
    assert isinstance(loaded, dict)
    distributions = toolchain["distributions"]
    assert isinstance(distributions, list)
    distribution = distributions[0]
    assert isinstance(distribution, dict)
    distribution["bytes"] = int(distribution["bytes"]) + 1
    toolchain["bytes"] = int(toolchain["bytes"]) + 1
    unsigned = dict(toolchain)
    unsigned.pop("manifest_sha256")
    manifest = sha256_bytes(canonical_json_bytes(unsigned))
    toolchain["manifest_sha256"] = manifest
    loaded["manifest_sha256"] = manifest
    return drifted


def _drift_snapshot(
    snapshot: SnapshotInputs,
    *,
    relative: str,
) -> SnapshotInputs:
    changed = False
    files: list[FileIdentity] = []
    for identity in snapshot.files:
        if identity.path == relative:
            changed = True
            identity = replace(
                identity,
                bytes=identity.bytes + 1,
                sha256=sha256_bytes(
                    f"drift:{relative}".encode("utf-8")
                ),
            )
        files.append(identity)
    assert changed, relative
    file_tuple = tuple(files)
    manifest_sha256 = sha256_bytes(
        canonical_json_bytes(
            {
                "deleted_tracked": list(snapshot.deleted_tracked),
                "files": [
                    {
                        "bytes": item.bytes,
                        "path": item.path,
                        "sha256": item.sha256,
                    }
                    for item in file_tuple
                ],
                "git_executable": {
                    "path": snapshot.git_executable.path,
                    "bytes": snapshot.git_executable.bytes,
                    "sha256": snapshot.git_executable.sha256,
                    "runtime_files": [
                        {
                            "bytes": item.bytes,
                            "path": item.path,
                            "sha256": item.sha256,
                        }
                        for item in snapshot.git_executable.runtime_files
                    ],
                    "runtime_manifest_sha256": (
                        snapshot.git_executable.runtime_manifest_sha256
                    ),
                },
                "native_backend_path": snapshot.native_backend_path,
                "schema_version": 3,
                "untracked_exclude_policy": list(
                    snapshot.untracked_exclude_policy
                ),
            }
        )
    )
    return SnapshotInputs(
        files=file_tuple,
        deleted_tracked=snapshot.deleted_tracked,
        native_backend_path=snapshot.native_backend_path,
        git_executable=snapshot.git_executable,
        untracked_exclude_policy=snapshot.untracked_exclude_policy,
        manifest_sha256=manifest_sha256,
    )


def test_native_parity_catalogue_cannot_disable_the_backend_requirement(
    tmp_path: Path,
) -> None:
    catalogue, snapshot, baselines, mutants = _synthetic_receipt_inputs(
        tmp_path,
        evidence_class="native_parity",
        requires_native_backend=False,
    )

    with pytest.raises(MutationAssuranceError, match="native-parity"):
        _seal_synthetic_receipt(
            artifact_root=tmp_path / "artifacts",
            run_id=_RECEIPT_RUN_ID,
            catalogue=catalogue,
            snapshot=snapshot,
            baselines=baselines,
            mutants=mutants,
        )


def test_catalogue_loader_rejects_native_parity_without_backend_requirement(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    source = root / "tests" / "mutations" / "catalogue.json"
    payload = strict_json_bytes(
        source.read_bytes(),
        label="adversarial native-parity catalogue",
    )
    assert isinstance(payload, dict)
    mutants = payload["mutants"]
    assert isinstance(mutants, list)
    native = next(
        value
        for value in mutants
        if isinstance(value, dict)
        and value.get("evidence_class") == "native_parity"
    )
    assert native["requires_native_backend"] is True
    native["requires_native_backend"] = False
    path = tmp_path / "catalogue.json"
    path.write_bytes(pretty_json_bytes(payload))

    with pytest.raises(
        MutationAssuranceError,
        match="native-parity evidence must require the backend",
    ):
        load_catalogue(
            path,
            root=root,
            contracts=CONTRACTS,
            verify_sources=False,
        )


def _current_native_assurance_inputs(
) -> tuple[Path, MutationCatalogue, SnapshotInputs]:
    root = Path(__file__).resolve().parents[2]
    catalogue = load_catalogue(
        root / "tests" / "mutations" / "catalogue.json",
        root=root,
        contracts=CONTRACTS,
        verify_sources=True,
    )
    return root, catalogue, enumerate_snapshot_inputs(
        root,
        git_executable=_GIT_IDENTITY,
    )


def test_phase11_native_build_identity_accepts_the_current_real_build(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MOIRA_NO_DOWNLOAD", "1")
    root, catalogue, snapshot = _current_native_assurance_inputs()

    identity = phase11_native_build_identity(root, snapshot, catalogue)

    assert identity is not None
    required = [
        spec.mutant_id
        for spec in catalogue.mutants
        if spec.requires_native_backend
    ]
    backend = snapshot.by_path[snapshot.native_backend_path]
    assert identity["required_mutant_ids"] == required
    assert identity["backend_path"] == snapshot.native_backend_path
    assert identity["backend_bytes"] == backend.bytes
    assert identity["backend_sha256"] == backend.sha256
    assert identity["embedded_input_sha256"] == (
        identity["build_input_manifest_sha256"]
    )
    assert identity["build_input_count"] > 0
    assert identity["matches_current_inputs"] is True


def test_phase11_native_build_identity_rejects_static_build_input_drift(
    tmp_path: Path,
) -> None:
    root, catalogue, snapshot = _current_native_assurance_inputs()
    manifest = _native_build_input_manifest(root, snapshot=snapshot)
    synthetic = tmp_path / "stale-native-build"
    synthetic.mkdir()
    subprocess.run(
        ("git", "init", "--quiet", str(synthetic)),
        check=True,
        capture_output=True,
        timeout=15,
    )
    inputs = manifest["inputs"]
    assert isinstance(inputs, list)
    for item in inputs:
        assert isinstance(item, dict)
        relative = item["path"]
        assert isinstance(relative, str)
        destination = synthetic / Path(relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((root / Path(relative)).read_bytes())
    backend = synthetic / Path(snapshot.native_backend_path)
    backend.parent.mkdir(parents=True, exist_ok=True)
    backend.write_bytes(
        (root / Path(snapshot.native_backend_path)).read_bytes()
    )
    cmake = synthetic / "CMakeLists.txt"
    cmake.write_bytes(cmake.read_bytes() + b"\n# adversarial stale input\n")
    stale_snapshot = enumerate_snapshot_inputs(
        synthetic,
        git_executable=_GIT_IDENTITY,
    )
    before_modules = {
        name
        for name in sys.modules
        if name == "moira" or name.startswith("moira.")
    }

    with pytest.raises(
        MutationAssuranceError,
        match="not built from the current admitted inputs",
    ):
        phase11_native_build_identity(synthetic, stale_snapshot, catalogue)
    after_modules = {
        name
        for name in sys.modules
        if name == "moira" or name.startswith("moira.")
    }
    assert after_modules == before_modules


@pytest.mark.parametrize("boundary", ("seal", "validate"))
def test_native_required_catalogue_rejects_a_missing_build_payload(
    tmp_path: Path,
    boundary: str,
) -> None:
    catalogue, snapshot, baselines, mutants = _synthetic_receipt_inputs(
        tmp_path,
        evidence_class="native_parity",
        requires_native_backend=True,
    )
    if boundary == "seal":
        with pytest.raises(MutationAssuranceError):
            _seal_synthetic_receipt(
                artifact_root=tmp_path / "artifacts",
                run_id=_RECEIPT_RUN_ID,
                catalogue=catalogue,
                snapshot=snapshot,
                baselines=baselines,
                mutants=mutants,
                native_build=None,
            )
        return

    native_build = _synthetic_native_build(catalogue, snapshot)
    receipt = _seal_synthetic_receipt(
        artifact_root=tmp_path / "artifacts",
        run_id=_RECEIPT_RUN_ID,
        catalogue=catalogue,
        snapshot=snapshot,
        baselines=baselines,
        mutants=mutants,
        native_build=native_build,
    )
    _replace_native_build_and_reseal_envelope(receipt, None)
    with pytest.raises(MutationAssuranceError):
        validate_mutation_receipt(
            receipt,
            current_catalogue=catalogue,
            require_green=False,
        )


@pytest.mark.parametrize("boundary", ("seal", "validate"))
@pytest.mark.parametrize("field", ("backend_bytes", "backend_sha256"))
def test_native_build_backend_identity_must_match_the_snapshot(
    tmp_path: Path,
    boundary: str,
    field: str,
) -> None:
    catalogue, snapshot, baselines, mutants = _synthetic_receipt_inputs(
        tmp_path,
        evidence_class="native_parity",
        requires_native_backend=True,
    )
    native_build = _synthetic_native_build(catalogue, snapshot)
    corrupted = deepcopy(native_build)
    if field == "backend_bytes":
        corrupted[field] = int(corrupted[field]) + 1
    else:
        corrupted[field] = _ZERO_SHA256

    if boundary == "seal":
        with pytest.raises(MutationAssuranceError):
            _seal_synthetic_receipt(
                artifact_root=tmp_path / "artifacts",
                run_id=_RECEIPT_RUN_ID,
                catalogue=catalogue,
                snapshot=snapshot,
                baselines=baselines,
                mutants=mutants,
                native_build=corrupted,
            )
        return

    receipt = _seal_synthetic_receipt(
        artifact_root=tmp_path / "artifacts",
        run_id=_RECEIPT_RUN_ID,
        catalogue=catalogue,
        snapshot=snapshot,
        baselines=baselines,
        mutants=mutants,
        native_build=native_build,
    )
    _replace_native_build_and_reseal_envelope(receipt, corrupted)
    with pytest.raises(MutationAssuranceError):
        validate_mutation_receipt(
            receipt,
            current_catalogue=catalogue,
            require_green=False,
        )


@pytest.mark.parametrize("boundary", ("seal", "validate"))
def test_native_embedded_and_build_manifest_digests_must_agree(
    tmp_path: Path,
    boundary: str,
) -> None:
    catalogue, snapshot, baselines, mutants = _synthetic_receipt_inputs(
        tmp_path,
        evidence_class="native_parity",
        requires_native_backend=True,
    )
    native_build = _synthetic_native_build(catalogue, snapshot)
    corrupted = deepcopy(native_build)
    corrupted["embedded_input_sha256"] = _ZERO_SHA256

    if boundary == "seal":
        with pytest.raises(MutationAssuranceError, match="stale"):
            _seal_synthetic_receipt(
                artifact_root=tmp_path / "artifacts",
                run_id=_RECEIPT_RUN_ID,
                catalogue=catalogue,
                snapshot=snapshot,
                baselines=baselines,
                mutants=mutants,
                native_build=corrupted,
            )
        return

    receipt = _seal_synthetic_receipt(
        artifact_root=tmp_path / "artifacts",
        run_id=_RECEIPT_RUN_ID,
        catalogue=catalogue,
        snapshot=snapshot,
        baselines=baselines,
        mutants=mutants,
        native_build=native_build,
    )
    _replace_native_build_and_reseal_envelope(receipt, corrupted)
    with pytest.raises(MutationAssuranceError, match="stale"):
        validate_mutation_receipt(
            receipt,
            current_catalogue=catalogue,
            require_green=False,
        )


def test_green_native_receipt_rejects_current_native_identity_drift(
    tmp_path: Path,
) -> None:
    catalogue, snapshot, baselines, mutants = _synthetic_receipt_inputs(
        tmp_path,
        evidence_class="native_parity",
        requires_native_backend=True,
    )
    native_build = _synthetic_native_build(catalogue, snapshot)
    receipt = _seal_synthetic_receipt(
        artifact_root=tmp_path / "artifacts",
        run_id=_RECEIPT_RUN_ID,
        catalogue=catalogue,
        snapshot=snapshot,
        baselines=baselines,
        mutants=mutants,
        native_build=native_build,
    )
    current = validate_mutation_receipt(
        receipt,
        current_catalogue=catalogue,
        current_snapshot=snapshot,
        current_interpreter=_synthetic_interpreter(baselines),
        current_native_build=native_build,
        require_green=True,
    )
    assert current["status"] == "passed"

    drifted = _synthetic_native_build(
        catalogue,
        snapshot,
        manifest_sha256=sha256_bytes(b"drifted native build inputs\n"),
    )
    with pytest.raises(MutationAssuranceError, match="stale"):
        validate_mutation_receipt(
            receipt,
            current_catalogue=catalogue,
            current_snapshot=snapshot,
            current_interpreter=_synthetic_interpreter(baselines),
            current_native_build=drifted,
            require_green=True,
        )


def test_green_native_receipt_requires_a_current_native_identity(
    tmp_path: Path,
) -> None:
    catalogue, snapshot, baselines, mutants = _synthetic_receipt_inputs(
        tmp_path,
        evidence_class="native_parity",
        requires_native_backend=True,
    )
    native_build = _synthetic_native_build(catalogue, snapshot)
    receipt = _seal_synthetic_receipt(
        artifact_root=tmp_path / "artifacts",
        run_id=_RECEIPT_RUN_ID,
        catalogue=catalogue,
        snapshot=snapshot,
        baselines=baselines,
        mutants=mutants,
        native_build=native_build,
    )

    with pytest.raises(MutationAssuranceError, match="current identities"):
        validate_mutation_receipt(
            receipt,
            current_catalogue=catalogue,
            current_snapshot=snapshot,
            current_interpreter=_synthetic_interpreter(baselines),
            require_green=True,
        )


@pytest.mark.parametrize("boundary", ("seal", "validate"))
@pytest.mark.parametrize(
    "corruption",
    (
        "module_manifest_sha256",
        "code_manifest_sha256",
        "module_count",
        "code_object_count",
        "all_modules_match",
        "all_captured_modules_match",
        "normalized_lru_wrapper_names",
        "normalized_lru_wrapper_count",
        "normalized_lru_wrapper_sha256",
        "all_normalized_lru_wrappers_empty",
    ),
)
def test_loaded_toolchain_attestation_cannot_be_re_signed_into_a_receipt(
    tmp_path: Path,
    boundary: str,
    corruption: str,
) -> None:
    catalogue, snapshot, baselines, mutants = _synthetic_receipt_inputs(
        tmp_path
    )
    interpreter = _synthetic_interpreter(baselines)
    tampered = deepcopy(interpreter)
    loaded = tampered["loaded_test_toolchain"]
    assert isinstance(loaded, dict)
    if corruption in {
        "module_manifest_sha256",
        "code_manifest_sha256",
        "normalized_lru_wrapper_sha256",
    }:
        loaded[corruption] = _ZERO_SHA256
    elif corruption in {
        "module_count",
        "code_object_count",
        "normalized_lru_wrapper_count",
    }:
        loaded[corruption] = int(loaded[corruption]) + 1
    elif corruption == "normalized_lru_wrapper_names":
        loaded[corruption] = [*loaded[corruption], "synthetic.zzz"]
    else:
        loaded[corruption] = False

    if boundary == "seal":
        with pytest.raises(MutationAssuranceError):
            _seal_synthetic_receipt(
                artifact_root=tmp_path / "artifacts",
                run_id=_RECEIPT_RUN_ID,
                catalogue=catalogue,
                snapshot=snapshot,
                baselines=baselines,
                mutants=mutants,
                interpreter_override=tampered,
            )
        return

    receipt = _seal_synthetic_receipt(
        artifact_root=tmp_path / "artifacts",
        run_id=_RECEIPT_RUN_ID,
        catalogue=catalogue,
        snapshot=snapshot,
        baselines=baselines,
        mutants=mutants,
    )
    _replace_interpreter_and_reseal_envelope(receipt, tampered)
    with pytest.raises(MutationAssuranceError):
        validate_mutation_receipt(
            receipt,
            current_catalogue=catalogue,
            require_green=False,
        )


@pytest.mark.parametrize("boundary", ("seal", "validate"))
@pytest.mark.parametrize("corruption", ("manifest", "distribution_bytes"))
def test_parent_toolchain_rewrite_cannot_cross_a_receipt_boundary(
    tmp_path: Path,
    boundary: str,
    corruption: str,
) -> None:
    catalogue, snapshot, baselines, mutants = _synthetic_receipt_inputs(
        tmp_path
    )
    interpreter = _synthetic_interpreter(baselines)
    if corruption == "distribution_bytes":
        tampered = _drift_parent_toolchain_distribution(interpreter)
    else:
        tampered = deepcopy(interpreter)
        toolchain = tampered["test_toolchain"]
        loaded = tampered["loaded_test_toolchain"]
        assert isinstance(toolchain, dict)
        assert isinstance(loaded, dict)
        toolchain["manifest_sha256"] = _ZERO_SHA256
        loaded["manifest_sha256"] = _ZERO_SHA256

    if boundary == "seal":
        with pytest.raises(MutationAssuranceError):
            _seal_synthetic_receipt(
                artifact_root=tmp_path / "artifacts",
                run_id=_RECEIPT_RUN_ID,
                catalogue=catalogue,
                snapshot=snapshot,
                baselines=baselines,
                mutants=mutants,
                interpreter_override=tampered,
            )
        return

    receipt = _seal_synthetic_receipt(
        artifact_root=tmp_path / "artifacts",
        run_id=_RECEIPT_RUN_ID,
        catalogue=catalogue,
        snapshot=snapshot,
        baselines=baselines,
        mutants=mutants,
    )
    _replace_interpreter_and_reseal_envelope(receipt, tampered)
    with pytest.raises(MutationAssuranceError):
        validate_mutation_receipt(
            receipt,
            current_catalogue=catalogue,
            require_green=False,
        )


def test_green_receipt_rejects_current_test_toolchain_drift(
    tmp_path: Path,
) -> None:
    catalogue, snapshot, baselines, mutants = _synthetic_receipt_inputs(
        tmp_path
    )
    receipt = _seal_synthetic_receipt(
        artifact_root=tmp_path / "artifacts",
        run_id=_RECEIPT_RUN_ID,
        catalogue=catalogue,
        snapshot=snapshot,
        baselines=baselines,
        mutants=mutants,
    )
    current_interpreter = _synthetic_interpreter(baselines)
    drifted = _drift_parent_toolchain_distribution(current_interpreter)

    with pytest.raises(MutationAssuranceError, match="interpreter is stale"):
        validate_mutation_receipt(
            receipt,
            current_catalogue=catalogue,
            current_snapshot=snapshot,
            current_interpreter=drifted,
            require_green=True,
        )


@pytest.mark.parametrize("tamper", ("missing", "changed"))
def test_report_authorship_boundary_is_sealed_exactly_and_tamper_rejected(
    tmp_path: Path,
    tamper: str,
) -> None:
    catalogue, snapshot, baselines, mutants = _synthetic_receipt_inputs(
        tmp_path
    )
    receipt = _seal_synthetic_receipt(
        artifact_root=tmp_path / "artifacts",
        run_id=_RECEIPT_RUN_ID,
        catalogue=catalogue,
        snapshot=snapshot,
        baselines=baselines,
        mutants=mutants,
    )
    run = validate_mutation_receipt(
        receipt,
        current_catalogue=catalogue,
        current_snapshot=snapshot,
        current_interpreter=_synthetic_interpreter(baselines),
        require_green=True,
    )
    boundaries = run["boundaries"]
    assert isinstance(boundaries, dict)
    assert boundaries["report_authorship"] == _REPORT_AUTHORSHIP_BOUNDARY

    corrupted = deepcopy(boundaries)
    if tamper == "missing":
        corrupted.pop("report_authorship")
    else:
        corrupted["report_authorship"] = (
            "same_process_report_authorship_externally_proven"
        )
    _replace_boundaries_and_reseal_envelope(receipt, corrupted)

    with pytest.raises(
        MutationAssuranceError,
        match="mutation run boundaries are not admitted",
    ):
        validate_mutation_receipt(
            receipt,
            current_catalogue=catalogue,
            require_green=False,
        )


@pytest.mark.parametrize("tamper", ("missing", "changed"))
def test_filesystem_concurrency_boundary_is_sealed_and_tamper_rejected(
    tmp_path: Path,
    tamper: str,
) -> None:
    catalogue, snapshot, baselines, mutants = _synthetic_receipt_inputs(
        tmp_path
    )
    receipt = _seal_synthetic_receipt(
        artifact_root=tmp_path / "artifacts",
        run_id=_RECEIPT_RUN_ID,
        catalogue=catalogue,
        snapshot=snapshot,
        baselines=baselines,
        mutants=mutants,
    )
    run = validate_mutation_receipt(
        receipt,
        current_catalogue=catalogue,
        current_snapshot=snapshot,
        current_interpreter=_synthetic_interpreter(baselines),
        require_green=True,
    )
    boundaries = run["boundaries"]
    assert isinstance(boundaries, dict)
    assert boundaries["filesystem_concurrency"] == (
        "cooperative_claim_exclusion_and_existing_windows_runtime_file_locks_"
        "not_hostile_same_user_path_swap_or_transient_runtime_membership_"
        "injection_isolation"
    )

    corrupted = deepcopy(boundaries)
    if tamper == "missing":
        corrupted.pop("filesystem_concurrency")
    else:
        corrupted["filesystem_concurrency"] = (
            "hostile_same_user_filesystem_isolation"
        )
    _replace_boundaries_and_reseal_envelope(receipt, corrupted)

    with pytest.raises(
        MutationAssuranceError,
        match="mutation run boundaries are not admitted",
    ):
        validate_mutation_receipt(
            receipt,
            current_catalogue=catalogue,
            require_green=False,
        )


def test_green_mutation_receipt_seals_and_validates_exactly(
    tmp_path: Path,
) -> None:
    catalogue, snapshot, baselines, mutants = _synthetic_receipt_inputs(
        tmp_path
    )

    receipt = _seal_synthetic_receipt(
        artifact_root=tmp_path / "artifacts",
        run_id=_RECEIPT_RUN_ID,
        catalogue=catalogue,
        snapshot=snapshot,
        baselines=baselines,
        mutants=mutants,
    )
    run = validate_mutation_receipt(
        receipt,
        current_catalogue=catalogue,
        current_snapshot=snapshot,
        current_interpreter=_synthetic_interpreter(baselines),
        require_green=True,
    )

    assert run["run_id"] == _RECEIPT_RUN_ID
    assert run["status"] == "passed"
    assert run["summary"] == {
        "baseline_passed": 1,
        "declared": 1,
        "gate": "all_declared_mutants_no_percentage",
        "gate_passed": True,
        "killed_intended": 1,
    }
    assert run["boundaries"] == {
        "source_mutations": "disposable_plain_file_snapshots_only",
        "filesystem_concurrency": (
            "cooperative_claim_exclusion_and_existing_windows_runtime_file_"
            "locks_not_hostile_same_user_path_swap_or_transient_runtime_"
            "membership_injection_isolation"
        ),
        "network": "cooperative_cpython_deny_not_security_sandbox",
        "integrity": "sha256_tamper_evidence_not_signed_authenticity",
        "native": "unchanged_copied_backend_only_no_native_mutation",
        "report_authorship": _REPORT_AUTHORSHIP_BOUNDARY,
    }
    spec = catalogue.mutants[0]
    baseline_report = baselines[0]["child_report"]
    mutant_report = mutants[0]["child_report"]
    assert isinstance(baseline_report, dict)
    assert isinstance(mutant_report, dict)
    assert baselines[0]["execution_id"] == _role_execution_id(
        spec,
        "baseline",
    )
    assert baseline_report["execution_id"] == _role_execution_id(
        spec,
        "baseline",
    )
    assert mutant_report["execution_id"] == _role_execution_id(
        spec,
        "mutant",
    )
    expected_test_source = _synthetic_intended_test_source_receipt()
    assert baselines[0]["intended_test_source"] == expected_test_source
    assert mutants[0]["intended_test_source"] == expected_test_source
    expected_seed = str(_deterministic_mutation_seed(spec))
    for report in (baseline_report, mutant_report):
        identity = report["identity"]
        assert isinstance(identity, dict)
        environment = identity["policy_environment"]
        assert isinstance(environment, dict)
        seed = environment["MOIRA_TEST_SEED"]
        assert isinstance(seed, dict)
        assert seed["value"] == expected_seed


def test_posix_lexical_interpreter_symlink_uses_resolved_child_executable(
    tmp_path: Path,
) -> None:
    catalogue, snapshot, baselines, mutants = _synthetic_receipt_inputs(
        tmp_path
    )
    lexical = "/opt/moira/.venv/bin/python"
    resolved = "/opt/python/bin/python3.14"
    interpreter = _synthetic_interpreter(baselines)
    interpreter["executable"] = lexical
    interpreter["executable_resolved"] = resolved
    launcher = interpreter["launcher"]
    assert isinstance(launcher, dict)
    launcher["path"] = lexical
    launcher["resolved_path"] = resolved
    launcher["directory_resolved"] = "/opt/python/bin"
    launcher["symlinks"] = [{"path": lexical, "target": resolved}]

    rewritten_baselines = [
        _rewrite_adjudication_interpreter_paths(
            baselines[0],
            argv_executable=lexical,
            child_executable=resolved,
        )
    ]
    rewritten_mutants = [
        _rewrite_adjudication_interpreter_paths(
            mutants[0],
            argv_executable=lexical,
            child_executable=resolved,
        )
    ]
    receipt = _seal_synthetic_receipt(
        artifact_root=tmp_path / "artifacts",
        run_id=_RECEIPT_RUN_ID,
        catalogue=catalogue,
        snapshot=snapshot,
        baselines=rewritten_baselines,
        mutants=rewritten_mutants,
        interpreter_override=interpreter,
    )
    run = validate_mutation_receipt(
        receipt,
        current_catalogue=catalogue,
        current_snapshot=snapshot,
        current_interpreter=interpreter,
        require_green=True,
    )

    run_interpreter = run["interpreter"]
    assert isinstance(run_interpreter, dict)
    assert run_interpreter["executable"] == lexical
    assert run_interpreter["executable_resolved"] == resolved
    for record in (*rewritten_baselines, *rewritten_mutants):
        admitted, observed = _admitted_and_observed_reports(record)
        for report in (admitted, observed):
            identity = report["identity"]
            assert isinstance(identity, dict)
            child_interpreter = identity["interpreter"]
            assert isinstance(child_interpreter, dict)
            executable = child_interpreter["executable"]
            assert isinstance(executable, dict)
            assert executable["path"] == resolved

    invalid_baselines = [
        _rewrite_adjudication_interpreter_paths(
            baselines[0],
            argv_executable=lexical,
            child_executable=lexical,
        )
    ]
    invalid_mutants = [
        _rewrite_adjudication_interpreter_paths(
            mutants[0],
            argv_executable=lexical,
            child_executable=lexical,
        )
    ]
    with pytest.raises(
        MutationAssuranceError,
        match="child interpreter path is wrong",
    ):
        _seal_synthetic_receipt(
            artifact_root=tmp_path / "invalid-artifacts",
            run_id=_RECEIPT_RUN_ID,
            catalogue=catalogue,
            snapshot=snapshot,
            baselines=invalid_baselines,
            mutants=invalid_mutants,
            interpreter_override=interpreter,
        )


def test_internally_valid_incomplete_candidate_cannot_validate_publicly(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import support.mutation_assurance as mutation_assurance

    catalogue, snapshot, baselines, mutants = _synthetic_receipt_inputs(
        tmp_path
    )
    artifact_root = tmp_path / "artifacts"
    internal_validations: list[Path] = []
    real_private_validator = mutation_assurance._validate_mutation_receipt

    def observe_private_validation(
        path: Path,
        **kwargs: object,
    ) -> dict[str, object]:
        result = real_private_validator(path, **kwargs)
        internal_validations.append(path)
        return result

    monkeypatch.setattr(
        mutation_assurance,
        "_validate_mutation_receipt",
        observe_private_validation,
    )

    checks = 0

    def reject_first_check() -> None:
        nonlocal checks
        checks += 1
        raise MutationAssuranceError("forced first pre-publication rejection")

    with pytest.raises(
        MutationAssuranceError,
        match="forced first pre-publication rejection",
    ):
        _seal_synthetic_receipt(
            artifact_root=artifact_root,
            run_id=_RECEIPT_RUN_ID,
            catalogue=catalogue,
            snapshot=snapshot,
            baselines=baselines,
            mutants=mutants,
            pre_publish_check=reject_first_check,
        )

    final = artifact_root / _RECEIPT_RUN_ID
    incomplete = artifact_root / f".incomplete-{_RECEIPT_RUN_ID}"
    candidate = incomplete / _RECEIPT_RUN_ID
    assert checks == 1
    assert internal_validations == [candidate]
    assert not final.exists()
    assert candidate.is_dir()
    assert {path.name for path in candidate.iterdir()} == {
        "baselines.json",
        "catalogue.json",
        "claim.json",
        "mutants.json",
        "run.json",
        "snapshot.json",
    }
    assert not tuple(incomplete.rglob("COMPLETE"))

    with pytest.raises(
        MutationAssuranceError,
        match="below an incomplete or revoked container",
    ):
        validate_mutation_receipt(
            candidate,
            current_catalogue=catalogue,
            require_green=False,
        )

    revoked = artifact_root / f".revoked-{_RECEIPT_RUN_ID}"
    incomplete.rename(revoked)
    revoked_candidate = revoked / _RECEIPT_RUN_ID
    with pytest.raises(
        MutationAssuranceError,
        match="below an incomplete or revoked container",
    ):
        validate_mutation_receipt(
            revoked_candidate,
            current_catalogue=catalogue,
            require_green=False,
        )


@pytest.mark.parametrize("failure_call", (2, 3))
def test_late_prepublication_failure_leaves_no_committed_receipt(
    tmp_path: Path,
    failure_call: int,
) -> None:
    catalogue, snapshot, baselines, mutants = _synthetic_receipt_inputs(
        tmp_path
    )
    artifact_root = tmp_path / "artifacts"
    checks = 0

    def reject_selected_check() -> None:
        nonlocal checks
        checks += 1
        if checks == failure_call:
            raise MutationAssuranceError(
                f"forced pre-publication rejection {failure_call}"
            )

    with pytest.raises(
        MutationAssuranceError,
        match=rf"forced pre-publication rejection {failure_call}",
    ):
        _seal_synthetic_receipt(
            artifact_root=artifact_root,
            run_id=_RECEIPT_RUN_ID,
            catalogue=catalogue,
            snapshot=snapshot,
            baselines=baselines,
            mutants=mutants,
            pre_publish_check=reject_selected_check,
        )

    final = artifact_root / _RECEIPT_RUN_ID
    incomplete = artifact_root / f".incomplete-{_RECEIPT_RUN_ID}"
    candidate = incomplete / _RECEIPT_RUN_ID
    assert checks == failure_call
    assert not final.exists()
    assert candidate.is_dir()
    assert not tuple(incomplete.rglob("COMPLETE"))
    assert (candidate / "COMPLETE.pending").is_file()


def test_final_precommit_validation_failure_leaves_no_public_complete(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import support.mutation_assurance as mutation_assurance

    catalogue, snapshot, baselines, mutants = _synthetic_receipt_inputs(
        tmp_path
    )
    artifact_root = tmp_path / "artifacts"
    real_validate = mutation_assurance._validate_mutation_receipt
    internal_validations: list[tuple[Path, object]] = []

    def reject_final_precommit_validation(
        path: Path,
        **kwargs: object,
    ) -> dict[str, object]:
        internal_validations.append(
            (path, kwargs.get("candidate_complete_name"))
        )
        if len(internal_validations) == 3:
            raise MutationAssuranceError(
                "forced final pre-commit validation rejection"
            )
        return real_validate(path, **kwargs)

    monkeypatch.setattr(
        mutation_assurance,
        "_validate_mutation_receipt",
        reject_final_precommit_validation,
    )

    with pytest.raises(
        MutationAssuranceError,
        match="forced final pre-commit validation rejection",
    ):
        _seal_synthetic_receipt(
            artifact_root=artifact_root,
            run_id=_RECEIPT_RUN_ID,
            catalogue=catalogue,
            snapshot=snapshot,
            baselines=baselines,
            mutants=mutants,
        )

    final = artifact_root / _RECEIPT_RUN_ID
    incomplete = artifact_root / f".incomplete-{_RECEIPT_RUN_ID}"
    candidate = incomplete / _RECEIPT_RUN_ID
    assert internal_validations == [
        (candidate, None),
        (final, "COMPLETE.pending"),
        (final, "COMPLETE.pending"),
    ]
    assert not final.exists()
    assert candidate.is_dir()
    assert (candidate / "COMPLETE.pending").is_file()
    assert not tuple(incomplete.rglob("COMPLETE"))


def test_same_run_race_loser_never_revokes_a_foreign_winner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import support.mutation_assurance as mutation_assurance

    catalogue, snapshot, baselines, mutants = _synthetic_receipt_inputs(
        tmp_path
    )
    winner = _seal_synthetic_receipt(
        artifact_root=tmp_path / "winner-artifacts",
        run_id=_RECEIPT_RUN_ID,
        catalogue=catalogue,
        snapshot=snapshot,
        baselines=baselines,
        mutants=mutants,
    )
    winner_complete = (winner / "COMPLETE").read_bytes()
    artifact_root = tmp_path / "race-artifacts"
    final = artifact_root / _RECEIPT_RUN_ID
    incomplete = artifact_root / f".incomplete-{_RECEIPT_RUN_ID}"
    candidate = incomplete / _RECEIPT_RUN_ID
    real_replace = mutation_assurance.os.replace
    winner_directory_identity: tuple[int, int] | None = None
    injected = False

    def install_winner_before_loser_publish(
        source: object,
        destination: object,
    ) -> None:
        nonlocal injected, winner_directory_identity
        source_path = Path(source)
        destination_path = Path(destination)
        if not injected and source_path == candidate and destination_path == final:
            injected = True
            real_replace(winner, final)
            metadata = final.lstat()
            winner_directory_identity = (metadata.st_dev, metadata.st_ino)
        real_replace(source, destination)

    monkeypatch.setattr(
        mutation_assurance.os,
        "replace",
        install_winner_before_loser_publish,
    )

    with pytest.raises(OSError):
        _seal_synthetic_receipt(
            artifact_root=artifact_root,
            run_id=_RECEIPT_RUN_ID,
            catalogue=catalogue,
            snapshot=snapshot,
            baselines=baselines,
            mutants=mutants,
        )

    metadata = final.lstat()
    assert injected is True
    assert (metadata.st_dev, metadata.st_ino) == winner_directory_identity
    assert (final / "COMPLETE").read_bytes() == winner_complete
    assert not tuple(incomplete.rglob("COMPLETE.revoked"))


def test_atomic_run_claim_rejects_same_run_loser_without_writes(
    tmp_path: Path,
) -> None:
    catalogue, snapshot, baselines, mutants = _synthetic_receipt_inputs(
        tmp_path
    )
    artifact_root = tmp_path / "claimed-run-artifacts"
    challenged = False

    def artifact_state() -> tuple[tuple[str, int, int, bytes | None], ...]:
        values: list[tuple[str, int, int, bytes | None]] = []
        for path in sorted(artifact_root.rglob("*"), key=lambda item: str(item)):
            metadata = path.lstat()
            values.append(
                (
                    path.relative_to(artifact_root).as_posix(),
                    metadata.st_dev,
                    metadata.st_ino,
                    path.read_bytes() if path.is_file() else None,
                )
            )
        return tuple(values)

    def challenge_with_same_run_loser() -> None:
        nonlocal challenged
        if challenged:
            return
        challenged = True
        before = artifact_state()
        with pytest.raises(
            MutationAssuranceError,
            match="run ID already exists",
        ):
            _seal_synthetic_receipt(
                artifact_root=artifact_root,
                run_id=_RECEIPT_RUN_ID,
                catalogue=catalogue,
                snapshot=snapshot,
                baselines=baselines,
                mutants=mutants,
            )
        assert artifact_state() == before

    receipt = _seal_synthetic_receipt(
        artifact_root=artifact_root,
        run_id=_RECEIPT_RUN_ID,
        catalogue=catalogue,
        snapshot=snapshot,
        baselines=baselines,
        mutants=mutants,
        pre_publish_check=challenge_with_same_run_loser,
    )

    assert challenged is True
    claim = artifact_root / f".claim-{_RECEIPT_RUN_ID}.json"
    assert claim.read_bytes() == (receipt / "claim.json").read_bytes()
    assert (receipt / "COMPLETE").is_file()


def test_preexisting_run_claim_fails_closed_without_touching_paths(
    tmp_path: Path,
) -> None:
    catalogue, snapshot, baselines, mutants = _synthetic_receipt_inputs(
        tmp_path
    )
    artifact_root = tmp_path / "preclaimed-artifacts"
    artifact_root.mkdir()
    claim = artifact_root / f".claim-{_RECEIPT_RUN_ID}.json"
    claim.write_bytes(b"foreign single-use claim\n")
    metadata = claim.lstat()

    with pytest.raises(
        MutationAssuranceError,
        match="run ID already exists",
    ):
        _seal_synthetic_receipt(
            artifact_root=artifact_root,
            run_id=_RECEIPT_RUN_ID,
            catalogue=catalogue,
            snapshot=snapshot,
            baselines=baselines,
            mutants=mutants,
        )

    replay = claim.lstat()
    assert (replay.st_dev, replay.st_ino) == (metadata.st_dev, metadata.st_ino)
    assert claim.read_bytes() == b"foreign single-use claim\n"
    assert {path.name for path in artifact_root.iterdir()} == {claim.name}


def test_committed_receipt_claim_remains_verifiable_after_offline_move(
    tmp_path: Path,
) -> None:
    catalogue, snapshot, baselines, mutants = _synthetic_receipt_inputs(
        tmp_path
    )
    receipt = _seal_synthetic_receipt(
        artifact_root=tmp_path / "source-artifacts",
        run_id=_RECEIPT_RUN_ID,
        catalogue=catalogue,
        snapshot=snapshot,
        baselines=baselines,
        mutants=mutants,
    )
    offline_root = tmp_path / "offline-replay"
    offline_root.mkdir()
    moved = offline_root / receipt.name
    receipt.rename(moved)

    run = validate_mutation_receipt(
        moved,
        current_catalogue=catalogue,
        current_snapshot=snapshot,
        current_interpreter=_synthetic_interpreter(baselines),
        require_green=True,
    )

    assert run["run_id"] == _RECEIPT_RUN_ID
    assert (moved / "claim.json").is_file()


def test_preexisting_symlink_run_claim_fails_closed(
    tmp_path: Path,
) -> None:
    catalogue, snapshot, baselines, mutants = _synthetic_receipt_inputs(
        tmp_path
    )
    artifact_root = tmp_path / "symlink-preclaimed-artifacts"
    artifact_root.mkdir()
    target = tmp_path / "foreign-claim-target.json"
    target.write_bytes(b"foreign symlink target\n")
    claim = artifact_root / f".claim-{_RECEIPT_RUN_ID}.json"
    try:
        claim.symlink_to(target)
    except OSError as exc:
        pytest.skip(f"symlink creation is unavailable: {exc}")

    with pytest.raises(
        MutationAssuranceError,
        match="run ID already exists",
    ):
        _seal_synthetic_receipt(
            artifact_root=artifact_root,
            run_id=_RECEIPT_RUN_ID,
            catalogue=catalogue,
            snapshot=snapshot,
            baselines=baselines,
            mutants=mutants,
        )

    assert claim.is_symlink()
    assert target.read_bytes() == b"foreign symlink target\n"
    assert {path.name for path in artifact_root.iterdir()} == {claim.name}


def test_preexisting_hardlink_run_claim_fails_closed(
    tmp_path: Path,
) -> None:
    catalogue, snapshot, baselines, mutants = _synthetic_receipt_inputs(
        tmp_path
    )
    artifact_root = tmp_path / "hardlink-preclaimed-artifacts"
    artifact_root.mkdir()
    target = tmp_path / "foreign-hardlink-claim.json"
    target.write_bytes(b"foreign hardlink target\n")
    claim = artifact_root / f".claim-{_RECEIPT_RUN_ID}.json"
    os.link(target, claim)
    before = claim.lstat()
    assert before.st_nlink == 2

    with pytest.raises(
        MutationAssuranceError,
        match="run ID already exists",
    ):
        _seal_synthetic_receipt(
            artifact_root=artifact_root,
            run_id=_RECEIPT_RUN_ID,
            catalogue=catalogue,
            snapshot=snapshot,
            baselines=baselines,
            mutants=mutants,
        )

    after = claim.lstat()
    assert (after.st_dev, after.st_ino, after.st_nlink) == (
        before.st_dev,
        before.st_ino,
        before.st_nlink,
    )
    assert target.read_bytes() == b"foreign hardlink target\n"
    assert claim.read_bytes() == target.read_bytes()
    assert {path.name for path in artifact_root.iterdir()} == {claim.name}


def test_publish_replace_success_then_raise_rolls_back_owned_candidate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import support.mutation_assurance as mutation_assurance

    catalogue, snapshot, baselines, mutants = _synthetic_receipt_inputs(
        tmp_path
    )
    artifact_root = tmp_path / "post-replace-error-artifacts"
    final = artifact_root / _RECEIPT_RUN_ID
    incomplete = artifact_root / f".incomplete-{_RECEIPT_RUN_ID}"
    candidate = incomplete / _RECEIPT_RUN_ID
    real_replace = mutation_assurance.os.replace
    injected = False

    def publish_then_raise(source: object, destination: object) -> None:
        nonlocal injected
        source_path = Path(source)
        destination_path = Path(destination)
        if not injected and source_path == candidate and destination_path == final:
            injected = True
            real_replace(source, destination)
            raise OSError("forced error after successful candidate publication")
        real_replace(source, destination)

    monkeypatch.setattr(
        mutation_assurance.os,
        "replace",
        publish_then_raise,
    )

    with pytest.raises(
        OSError,
        match="forced error after successful candidate publication",
    ):
        _seal_synthetic_receipt(
            artifact_root=artifact_root,
            run_id=_RECEIPT_RUN_ID,
            catalogue=catalogue,
            snapshot=snapshot,
            baselines=baselines,
            mutants=mutants,
        )

    assert injected is True
    assert not final.exists()
    assert candidate.is_dir()
    assert (candidate / "COMPLETE.pending").is_file()
    claim = artifact_root / f".claim-{_RECEIPT_RUN_ID}.json"
    assert claim.read_bytes() == (candidate / "claim.json").read_bytes()


def test_complete_replace_success_then_raise_revokes_owned_commitment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import support.mutation_assurance as mutation_assurance

    catalogue, snapshot, baselines, mutants = _synthetic_receipt_inputs(
        tmp_path
    )
    artifact_root = tmp_path / "post-complete-replace-error-artifacts"
    final = artifact_root / _RECEIPT_RUN_ID
    incomplete = artifact_root / f".incomplete-{_RECEIPT_RUN_ID}"
    candidate = incomplete / _RECEIPT_RUN_ID
    revoked = incomplete / "COMPLETE.revoked"
    real_replace = mutation_assurance.os.replace
    injected = False

    def commit_then_raise(source: object, destination: object) -> None:
        nonlocal injected
        source_path = Path(source)
        destination_path = Path(destination)
        if (
            not injected
            and source_path == final / "COMPLETE.pending"
            and destination_path == final / "COMPLETE"
        ):
            injected = True
            real_replace(source, destination)
            raise OSError("forced error after successful COMPLETE publication")
        real_replace(source, destination)

    monkeypatch.setattr(
        mutation_assurance.os,
        "replace",
        commit_then_raise,
    )

    with pytest.raises(
        OSError,
        match="forced error after successful COMPLETE publication",
    ):
        _seal_synthetic_receipt(
            artifact_root=artifact_root,
            run_id=_RECEIPT_RUN_ID,
            catalogue=catalogue,
            snapshot=snapshot,
            baselines=baselines,
            mutants=mutants,
        )

    assert injected is True
    assert not final.exists()
    assert candidate.is_dir()
    assert not (candidate / "COMPLETE").exists()
    assert not (candidate / "COMPLETE.pending").exists()
    assert revoked.is_file()
    claim = artifact_root / f".claim-{_RECEIPT_RUN_ID}.json"
    assert claim.read_bytes() == (candidate / "claim.json").read_bytes()


def test_complete_marker_is_the_last_atomic_publication_event(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import support.mutation_assurance as mutation_assurance

    catalogue, snapshot, baselines, mutants = _synthetic_receipt_inputs(
        tmp_path
    )
    artifact_root = tmp_path / "artifacts"
    final = artifact_root / _RECEIPT_RUN_ID
    real_replace = mutation_assurance.os.replace
    real_rmdir = Path.rmdir
    real_validate = mutation_assurance._validate_mutation_receipt
    events: list[dict[str, object]] = []

    def observe_replace(source: object, destination: object) -> None:
        source_path = Path(source)
        destination_path = Path(destination)
        artifact_root_resolved = artifact_root.resolve()

        def belongs_to_artifact_root(path: Path) -> bool:
            try:
                path.resolve().relative_to(artifact_root_resolved)
            except ValueError:
                return False
            return True

        relevant = belongs_to_artifact_root(
            source_path
        ) or belongs_to_artifact_root(destination_path)
        complete_before = (final / "COMPLETE").exists()
        real_replace(source, destination)
        if relevant:
            events.append(
                {
                    "kind": "replace",
                    "source": source_path,
                    "destination": destination_path,
                    "complete_before": complete_before,
                    "complete_after": (final / "COMPLETE").exists(),
                }
            )

    def observe_rmdir(path: Path) -> None:
        real_rmdir(path)
        if path == artifact_root / f".incomplete-{_RECEIPT_RUN_ID}":
            events.append({"kind": "rmdir", "path": path})

    def observe_validation(
        path: Path,
        **kwargs: object,
    ) -> dict[str, object]:
        events.append(
            {
                "kind": "validation",
                "path": path,
                "candidate_complete_name": kwargs.get(
                    "candidate_complete_name"
                ),
            }
        )
        return real_validate(path, **kwargs)

    def observe_currentness() -> None:
        events.append({"kind": "currentness"})

    monkeypatch.setattr(mutation_assurance.os, "replace", observe_replace)
    monkeypatch.setattr(Path, "rmdir", observe_rmdir)
    monkeypatch.setattr(
        mutation_assurance,
        "_validate_mutation_receipt",
        observe_validation,
    )

    receipt = _seal_synthetic_receipt(
        artifact_root=artifact_root,
        run_id=_RECEIPT_RUN_ID,
        catalogue=catalogue,
        snapshot=snapshot,
        baselines=baselines,
        mutants=mutants,
        pre_publish_check=observe_currentness,
    )

    incomplete = artifact_root / f".incomplete-{_RECEIPT_RUN_ID}"
    assert receipt == final
    replace_events = [event for event in events if event["kind"] == "replace"]
    assert [event["destination"] for event in replace_events] == [
        final,
        final / "COMPLETE",
    ]
    assert replace_events[0]["source"] == incomplete / _RECEIPT_RUN_ID
    assert replace_events[0]["complete_before"] is False
    assert replace_events[0]["complete_after"] is False
    assert events[-1]["kind"] == "replace"
    assert events[-1]["source"] == final / "COMPLETE.pending"
    assert events[-1]["complete_before"] is False
    assert events[-1]["complete_after"] is True
    assert [event["kind"] for event in events[:-1]].count("validation") == 3
    assert [event["kind"] for event in events[:-1]].count("currentness") == 3
    assert [event["kind"] for event in events[:-1]].count("rmdir") == 1
    assert (final / "COMPLETE").is_file()


def test_receipt_swap_after_initial_read_is_detected_at_final_replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import support.mutation_assurance as mutation_assurance

    catalogue, snapshot, baselines, mutants = _synthetic_receipt_inputs(
        tmp_path
    )
    receipt = _seal_synthetic_receipt(
        artifact_root=tmp_path / "artifacts",
        run_id=_RECEIPT_RUN_ID,
        catalogue=catalogue,
        snapshot=snapshot,
        baselines=baselines,
        mutants=mutants,
    )
    run_path = receipt / "run.json"
    manifested_raw = run_path.read_bytes()
    swapped_raw = b'{"attacker_controlled_second_read":true}\n'
    real_stable_file_bytes = mutation_assurance.stable_file_bytes
    labels: list[str] = []
    swapped = False

    def swap_after_first_read(
        path: Path,
        *,
        maximum_bytes: int | None,
        label: str,
    ) -> bytes:
        nonlocal swapped
        raw = real_stable_file_bytes(
            path,
            maximum_bytes=maximum_bytes,
            label=label,
        )
        if path == run_path:
            labels.append(label)
            if not swapped:
                assert raw == manifested_raw
                run_path.write_bytes(swapped_raw)
                swapped = True
        return raw

    monkeypatch.setattr(
        mutation_assurance,
        "stable_file_bytes",
        swap_after_first_read,
    )

    with pytest.raises(
        MutationAssuranceError,
        match="mutation receipt run.json changed during validation",
    ):
        validate_mutation_receipt(
            receipt,
            current_catalogue=catalogue,
            require_green=False,
        )

    assert swapped is True
    assert labels == [
        "mutation receipt run.json",
        "mutation receipt replay run.json",
    ]
    assert run_path.read_bytes() == swapped_raw


@pytest.mark.parametrize(
    "relative",
    (
        "tests/metamorphic/test_coordinate_relations.py",
        "tests/mutation_reporter.py",
        "conftest.py",
        "tests/evidence/contracts.py",
        "tests/_pytest_plugins/evidence_schema.py",
    ),
    ids=("killer", "reporter", "conftest", "contracts", "evidence-plugin"),
)
def test_green_receipt_rejects_current_snapshot_drift(
    tmp_path: Path,
    relative: str,
) -> None:
    catalogue, snapshot, baselines, mutants = _synthetic_receipt_inputs(
        tmp_path
    )
    receipt = _seal_synthetic_receipt(
        artifact_root=tmp_path / "artifacts",
        run_id=_RECEIPT_RUN_ID,
        catalogue=catalogue,
        snapshot=snapshot,
        baselines=baselines,
        mutants=mutants,
    )

    with pytest.raises(MutationAssuranceError, match="snapshot is stale"):
        validate_mutation_receipt(
            receipt,
            current_catalogue=catalogue,
            current_snapshot=_drift_snapshot(
                snapshot,
                relative=relative,
            ),
            current_interpreter=_synthetic_interpreter(baselines),
            require_green=True,
        )


def test_imported_nonfrozen_verify_action_fails_before_repository_access(
    tmp_path: Path,
) -> None:
    runner = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "run_scientific_mutations.py"
    )
    receipt = tmp_path / "receipt"
    receipt.mkdir()
    probe = f"""
import argparse
import importlib.util
from pathlib import Path

runner_path = Path({str(runner)!r})
specification = importlib.util.spec_from_file_location(
    "phase11_runner_stability_probe",
    runner_path,
)
assert specification is not None and specification.loader is not None
runner = importlib.util.module_from_spec(specification)
specification.loader.exec_module(runner)

try:
    runner._run(argparse.Namespace(
        check_catalogue=False,
        emit_interpreter_identity=False,
        verify_receipt=Path({str(receipt)!r}),
        run_id=None,
    ))
except RuntimeError as exc:
    assert "requires exact frozen stage-one execution" in str(exc)
else:
    raise AssertionError("imported verify action reached repository inputs")
"""

    completed = subprocess.run(
        [sys.executable, "-I", "-P", "-B", "-S", "-c", probe],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert completed.returncode == 0, (
        "imported verification action was admitted; "
        f"stdout={completed.stdout!r}; stderr={completed.stderr!r}"
    )


def test_imported_nonfrozen_identity_action_fails_before_repository_access(
) -> None:
    runner = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "run_scientific_mutations.py"
    )
    probe = f"""
import argparse
import importlib.util
from pathlib import Path

runner_path = Path({str(runner)!r})
specification = importlib.util.spec_from_file_location(
    "phase11_runner_identity_probe",
    runner_path,
)
assert specification is not None and specification.loader is not None
runner = importlib.util.module_from_spec(specification)
specification.loader.exec_module(runner)

try:
    runner._run(argparse.Namespace(
        check_catalogue=False,
        emit_interpreter_identity=True,
        verify_receipt=None,
        run_id=None,
    ))
except RuntimeError as exc:
    assert "requires exact frozen stage-one execution" in str(exc)
else:
    raise AssertionError("imported identity action reached repository inputs")
"""

    completed = subprocess.run(
        [sys.executable, "-I", "-P", "-B", "-S", "-c", probe],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert completed.returncode == 0, (
        "imported identity action was admitted; "
        f"stdout={completed.stdout!r}; stderr={completed.stderr!r}"
    )


def test_real_frozen_identity_action_is_canonical_and_artifact_free() -> None:
    root = Path(__file__).resolve().parents[2]
    runner = root / "scripts" / "run_scientific_mutations.py"
    artifact_root = root / ".pytest_cache" / "moira-mutation-artifacts"
    before = _artifact_tree_signature(artifact_root)
    before_temporary = _phase11_temp_signature()

    completed = subprocess.run(
        [sys.executable, str(runner), "--emit-interpreter-identity"],
        check=False,
        capture_output=True,
        env=_frozen_identity_environment(),
        timeout=300,
    )

    assert completed.returncode == 0, (
        "frozen identity action failed; "
        f"stdout={completed.stdout!r}; stderr={completed.stderr!r}"
    )
    assert completed.stderr == b""
    identity = strict_json_bytes(
        completed.stdout,
        label="frozen interpreter identity action",
    )
    assert completed.stdout == canonical_json_bytes(identity)
    assert isinstance(identity, dict)
    assert identity["schema_version"] == 2
    assert os.path.samefile(identity["executable"], sys.executable)
    loaded_toolchain = identity["loaded_test_toolchain"]
    assert isinstance(loaded_toolchain, dict)
    assert loaded_toolchain["all_normalized_lru_wrappers_empty"] is True
    assert _artifact_tree_signature(artifact_root) == before
    assert _phase11_temp_signature() == before_temporary


def test_frozen_identity_action_rejects_receipt_run_id_without_artifacts(
) -> None:
    root = Path(__file__).resolve().parents[2]
    runner = root / "scripts" / "run_scientific_mutations.py"
    artifact_root = root / ".pytest_cache" / "moira-mutation-artifacts"
    before = _artifact_tree_signature(artifact_root)
    before_temporary = _phase11_temp_signature()

    completed = subprocess.run(
        [
            sys.executable,
            str(runner),
            "--emit-interpreter-identity",
            "--run-id",
            "phase11-identity-action-forbidden",
        ],
        check=False,
        capture_output=True,
        env=_frozen_identity_environment(),
        timeout=300,
    )

    assert completed.returncode == 2
    assert completed.stdout == b""
    assert b"identity-only action forbids a mutation receipt run ID" in (
        completed.stderr
    )
    assert _artifact_tree_signature(artifact_root) == before
    assert _phase11_temp_signature() == before_temporary


def test_real_runner_freezes_no_site_stage_one_and_rejects_imported_receipt(
    tmp_path: Path,
) -> None:
    runner = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "run_scientific_mutations.py"
    )
    environment = dict(os.environ)
    environment.update(
        {
            "_ARGCOMPLETE": "1",
            "MOIRA_NO_DOWNLOAD": "1",
            "MOIRA_PHASE11_PTH_CANARY": str(tmp_path / "pth-executed"),
            "MOIRA_STRICT_KNOWN_ISSUES": "1",
            "MOIRA_TEST_MODE": "1",
        }
    )
    site_packages = (
        Path(sys.prefix) / "Lib" / "site-packages"
        if os.name == "nt"
        else Path(sys.prefix)
        / "lib"
        / f"python{sys.version_info[0]}.{sys.version_info[1]}"
        / "site-packages"
    )
    pth_canary = site_packages / (
        "moira_phase11_stage_one_canary_"
        + hashlib.sha256(str(tmp_path).encode("utf-8")).hexdigest()[:12]
        + ".pth"
    )
    pth_canary.write_text(
        "import os,pathlib; "
        "os.environ.get('MOIRA_PHASE11_FROZEN_RUNNER_SHA256') and "
        "os.environ.get('MOIRA_PHASE11_PTH_CANARY') and "
        "pathlib.Path(os.environ['MOIRA_PHASE11_PTH_CANARY']).write_text('executed')\n",
        encoding="utf-8",
    )
    try:
        stage_zero = subprocess.run(
            [sys.executable, str(runner), "--check-catalogue"],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
            timeout=60,
        )
    finally:
        pth_canary.unlink(missing_ok=True)
    assert stage_zero.returncode == 0, (
        f"stage zero failed; stdout={stage_zero.stdout!r}; "
        f"stderr={stage_zero.stderr!r}"
    )
    assert "catalogue ok:" in stage_zero.stdout
    assert not (tmp_path / "pth-executed").exists()

    frozen_directory = tmp_path / "moira-phase11-runner-policy-probe"
    frozen_directory.mkdir()
    frozen_runner = frozen_directory / runner.name
    frozen_raw = runner.read_bytes()
    frozen_runner.write_bytes(frozen_raw)
    stage_one_environment = dict(environment)
    stage_one_environment.pop("_ARGCOMPLETE")
    stage_one_environment.update(
        {
            "MOIRA_PHASE11_FROZEN_RUNNER_SHA256": sha256_bytes(frozen_raw),
            "MOIRA_PHASE11_FROZEN_RUNNER_ORIGINAL": str(runner),
            "MOIRA_PHASE11_FROZEN_RUNNER_ROOT": str(runner.parents[1]),
            "MOIRA_PHASE11_FROZEN_RUNNER_DIRECTORY": str(
                frozen_directory
            ),
        }
    )
    stage_one = subprocess.run(
        [
            sys.executable,
            "-I",
            "-P",
            "-B",
            "-S",
            "-X",
            f"pycache_prefix={frozen_directory / 'pycache'}",
            str(frozen_runner),
            "--check-catalogue",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=stage_one_environment,
        timeout=60,
    )
    assert stage_one.returncode == 0, (
        f"private stage one failed; stdout={stage_one.stdout!r}; "
        f"stderr={stage_one.stderr!r}"
    )
    assert "catalogue ok:" in stage_one.stdout
    assert not frozen_runner.exists()
    assert not frozen_directory.exists()

    probe = f"""
import importlib.util
from pathlib import Path

runner_path = Path({str(runner)!r}).resolve(strict=True)
specification = importlib.util.spec_from_file_location(
    "phase11_runner_parent_receipt_probe",
    runner_path,
)
assert specification is not None and specification.loader is not None
runner = importlib.util.module_from_spec(specification)
specification.loader.exec_module(runner)

try:
    runner._parent_runtime_receipt()
except RuntimeError as exc:
    assert "requires exact frozen stage-one execution" in str(exc)
else:
    raise AssertionError("import-only runner was allowed to seal a receipt")
"""
    parent_receipt = subprocess.run(
        [sys.executable, "-I", "-P", "-B", "-S", "-c", probe],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert parent_receipt.returncode == 0, (
        f"parent receipt probe failed; stdout={parent_receipt.stdout!r}; "
        f"stderr={parent_receipt.stderr!r}"
    )


def test_imported_nonfrozen_catalogue_action_fails_before_repository_access(
) -> None:
    runner = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "run_scientific_mutations.py"
    )
    probe = f"""
import argparse
import importlib.util
from pathlib import Path

runner_path = Path({str(runner)!r})
specification = importlib.util.spec_from_file_location(
    "phase11_runner_publish_probe",
    runner_path,
)
assert specification is not None and specification.loader is not None
runner = importlib.util.module_from_spec(specification)
specification.loader.exec_module(runner)

try:
    runner._run(argparse.Namespace(
        check_catalogue=True,
        emit_interpreter_identity=False,
        verify_receipt=None,
        run_id=None,
    ))
except RuntimeError as exc:
    assert "requires exact frozen stage-one execution" in str(exc)
else:
    raise AssertionError("imported catalogue action reached repository inputs")

"""

    completed = subprocess.run(
        [sys.executable, "-I", "-P", "-B", "-S", "-c", probe],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert completed.returncode == 0, (
        "imported catalogue action was admitted; "
        f"stdout={completed.stdout!r}; stderr={completed.stderr!r}"
    )


@pytest.mark.parametrize("boundary", ("seal", "validate"))
@pytest.mark.parametrize("corruption", ("noncanonical", "reversed"))
def test_mutation_receipt_rejects_invalid_run_timestamps(
    tmp_path: Path,
    boundary: str,
    corruption: str,
) -> None:
    catalogue, snapshot, baselines, mutants = _synthetic_receipt_inputs(
        tmp_path
    )
    if corruption == "noncanonical":
        started_utc = "2026-08-01T12:00:00.000Z"
        finished_utc = "2026-08-01T12:00:01Z"
    else:
        started_utc = "2026-08-01T12:00:02Z"
        finished_utc = "2026-08-01T12:00:01Z"

    if boundary == "seal":
        artifact_root = tmp_path / "artifacts"
        with pytest.raises(MutationAssuranceError):
            _seal_synthetic_receipt(
                artifact_root=artifact_root,
                run_id=_RECEIPT_RUN_ID,
                catalogue=catalogue,
                snapshot=snapshot,
                baselines=baselines,
                mutants=mutants,
                started_utc=started_utc,
                finished_utc=finished_utc,
            )
        assert not (artifact_root / _RECEIPT_RUN_ID).exists()
        if artifact_root.exists():
            assert not tuple(artifact_root.rglob("COMPLETE"))
        return

    receipt = _seal_synthetic_receipt(
        artifact_root=tmp_path / "artifacts",
        run_id=_RECEIPT_RUN_ID,
        catalogue=catalogue,
        snapshot=snapshot,
        baselines=baselines,
        mutants=mutants,
    )
    run_path = receipt / "run.json"
    run = strict_json_bytes(
        run_path.read_bytes(),
        label="synthetic mutation run",
    )
    assert isinstance(run, dict)
    run["started_utc"] = started_utc
    run["finished_utc"] = finished_utc
    run_path.write_bytes(pretty_json_bytes(run))
    _reseal_receipt_envelope(receipt)

    with pytest.raises(MutationAssuranceError):
        validate_mutation_receipt(
            receipt,
            current_catalogue=catalogue,
            current_snapshot=snapshot,
            current_interpreter=_synthetic_interpreter(baselines),
            require_green=True,
        )


@pytest.mark.parametrize("boundary", ("seal", "validate"))
def test_label_only_green_records_cannot_cross_a_receipt_boundary(
    tmp_path: Path,
    boundary: str,
) -> None:
    catalogue, snapshot, baselines, mutants = _synthetic_receipt_inputs(
        tmp_path
    )
    fake_baselines = [
        {
            "mutant_id": catalogue.mutants[0].mutant_id,
            "outcome": "baseline_passed",
            "gate_credit": False,
        }
    ]
    fake_mutants = [
        {
            "mutant_id": catalogue.mutants[0].mutant_id,
            "outcome": "killed_intended",
            "gate_credit": True,
        }
    ]
    if boundary == "seal":
        with pytest.raises(MutationAssuranceError):
            _seal_synthetic_receipt(
                artifact_root=tmp_path / "artifacts",
                run_id=_RECEIPT_RUN_ID,
                catalogue=catalogue,
                snapshot=snapshot,
                baselines=fake_baselines,
                mutants=fake_mutants,
            )
        return

    receipt = _seal_synthetic_receipt(
        artifact_root=tmp_path / "artifacts",
        run_id=_RECEIPT_RUN_ID,
        catalogue=catalogue,
        snapshot=snapshot,
        baselines=baselines,
        mutants=mutants,
    )
    _replace_mutant_and_reseal_envelope(receipt, fake_mutants[0])
    with pytest.raises(MutationAssuranceError):
        validate_mutation_receipt(
            receipt,
            current_catalogue=catalogue,
            current_snapshot=snapshot,
            current_interpreter=_synthetic_interpreter(baselines),
            require_green=True,
        )


@pytest.mark.parametrize("boundary", ("seal", "validate"))
@pytest.mark.parametrize(
    "corruption",
    (
        "selection",
        "argv",
        "phase",
        "passed_phase_exception",
        "source",
        "foreign_root",
        "foreign_source_path",
        "foreign_module_path",
        "intended_loader_policy",
        "intended_callable_digest",
        "intended_source_base64",
        "intended_source_synchronized",
        "baseline_runtime_digest",
        "source_bytes",
        "module_bytes",
        "interpreter_bytes",
        "child_implementation",
        "child_version",
        "child_cache_tag",
        "child_toolchain_initial",
        "child_toolchain_final",
        "child_toolchain_unstable",
        "child_toolchain_lru_names",
        "child_toolchain_lru_count",
        "child_toolchain_lru_digest",
        "child_toolchain_lru_nonempty",
        "mutant_execution_id",
        "mutation_seed",
        "code",
        "intended_trace_digest",
        "exception",
        "process",
        "report_digest",
        "adjudication_digest",
    ),
)
def test_tampered_green_adjudication_cannot_cross_a_receipt_boundary(
    tmp_path: Path,
    boundary: str,
    corruption: str,
) -> None:
    catalogue, snapshot, baselines, mutants = _synthetic_receipt_inputs(
        tmp_path
    )
    tampered = _corrupt_green_mutant(
        mutants[0],
        corruption=corruption,
        baseline=baselines[0],
    )
    if boundary == "seal":
        with pytest.raises(MutationAssuranceError):
            _seal_synthetic_receipt(
                artifact_root=tmp_path / "artifacts",
                run_id=_RECEIPT_RUN_ID,
                catalogue=catalogue,
                snapshot=snapshot,
                baselines=baselines,
                mutants=[tampered],
            )
        return

    receipt = _seal_synthetic_receipt(
        artifact_root=tmp_path / "artifacts",
        run_id=_RECEIPT_RUN_ID,
        catalogue=catalogue,
        snapshot=snapshot,
        baselines=baselines,
        mutants=mutants,
    )
    _replace_mutant_and_reseal_envelope(receipt, tampered)
    with pytest.raises(MutationAssuranceError):
        validate_mutation_receipt(
            receipt,
            current_catalogue=catalogue,
            current_snapshot=snapshot,
            current_interpreter=_synthetic_interpreter(baselines),
            require_green=True,
        )


@pytest.mark.parametrize("boundary", ("seal", "validate"))
def test_baseline_execution_id_is_role_specific_and_deterministic(
    tmp_path: Path,
    boundary: str,
) -> None:
    catalogue, snapshot, baselines, mutants = _synthetic_receipt_inputs(
        tmp_path
    )
    forged = _forge_baseline_execution_id(baselines[0])
    if boundary == "seal":
        with pytest.raises(MutationAssuranceError):
            _seal_synthetic_receipt(
                artifact_root=tmp_path / "artifacts",
                run_id=_RECEIPT_RUN_ID,
                catalogue=catalogue,
                snapshot=snapshot,
                baselines=[forged],
                mutants=mutants,
            )
        return

    receipt = _seal_synthetic_receipt(
        artifact_root=tmp_path / "artifacts",
        run_id=_RECEIPT_RUN_ID,
        catalogue=catalogue,
        snapshot=snapshot,
        baselines=baselines,
        mutants=mutants,
    )
    _replace_baseline_and_reseal_envelope(receipt, forged)
    with pytest.raises(MutationAssuranceError):
        validate_mutation_receipt(
            receipt,
            current_catalogue=catalogue,
            current_snapshot=snapshot,
            current_interpreter=_synthetic_interpreter(baselines),
            require_green=True,
        )


def test_complete_red_mutation_receipt_is_valid_but_never_green(
    tmp_path: Path,
) -> None:
    catalogue, snapshot, baselines, mutants = _synthetic_receipt_inputs(
        tmp_path,
        mutant_outcome="survived",
    )
    receipt = _seal_synthetic_receipt(
        artifact_root=tmp_path / "artifacts",
        run_id=_RECEIPT_RUN_ID,
        catalogue=catalogue,
        snapshot=snapshot,
        baselines=baselines,
        mutants=mutants,
    )

    run = validate_mutation_receipt(
        receipt,
        current_catalogue=catalogue,
        require_green=False,
    )
    assert run["status"] == "failed"
    assert run["summary"]["gate_passed"] is False

    with pytest.raises(
        MutationAssuranceError,
        match="complete but not green",
    ):
        validate_mutation_receipt(
            receipt,
            current_catalogue=catalogue,
            current_snapshot=snapshot,
            current_interpreter=_synthetic_interpreter(baselines),
            require_green=True,
        )


@pytest.mark.parametrize("corruption", ("data", "declared_hash"))
def test_mutation_receipt_rejects_tampered_data_or_hash(
    tmp_path: Path,
    corruption: str,
) -> None:
    catalogue, snapshot, baselines, mutants = _synthetic_receipt_inputs(
        tmp_path
    )
    receipt = _seal_synthetic_receipt(
        artifact_root=tmp_path / "artifacts",
        run_id=_RECEIPT_RUN_ID,
        catalogue=catalogue,
        snapshot=snapshot,
        baselines=baselines,
        mutants=mutants,
    )
    if corruption == "data":
        mutants_path = receipt / "mutants.json"
        mutants_path.write_bytes(mutants_path.read_bytes() + b" ")
    else:
        complete_path = receipt / "COMPLETE"
        complete = strict_json_bytes(
            complete_path.read_bytes(),
            label="synthetic mutation COMPLETE",
        )
        assert isinstance(complete, dict)
        files = complete["files"]
        assert isinstance(files, list)
        mutants_identity = next(
            value
            for value in files
            if isinstance(value, dict) and value.get("path") == "mutants.json"
        )
        mutants_identity["sha256"] = _ZERO_SHA256
        unsigned = dict(complete)
        unsigned.pop("manifest_sha256")
        complete["manifest_sha256"] = sha256_bytes(
            canonical_json_bytes(unsigned)
        )
        complete_path.write_bytes(pretty_json_bytes(complete))

    with pytest.raises(MutationAssuranceError, match="digest is invalid"):
        validate_mutation_receipt(
            receipt,
            current_catalogue=catalogue,
            current_snapshot=snapshot,
            current_interpreter=_synthetic_interpreter(baselines),
            require_green=True,
        )


@pytest.mark.parametrize(
    "corruption",
    ("missing_data", "extra_file", "missing_complete"),
)
def test_mutation_receipt_requires_the_exact_complete_file_set(
    tmp_path: Path,
    corruption: str,
) -> None:
    catalogue, snapshot, baselines, mutants = _synthetic_receipt_inputs(
        tmp_path
    )
    receipt = _seal_synthetic_receipt(
        artifact_root=tmp_path / "artifacts",
        run_id=_RECEIPT_RUN_ID,
        catalogue=catalogue,
        snapshot=snapshot,
        baselines=baselines,
        mutants=mutants,
    )
    if corruption == "missing_data":
        (receipt / "mutants.json").unlink()
    elif corruption == "extra_file":
        (receipt / "unexpected.json").write_bytes(b"{}\n")
    else:
        (receipt / "COMPLETE").unlink()

    with pytest.raises(MutationAssuranceError, match="file set is not exact"):
        validate_mutation_receipt(
            receipt,
            current_catalogue=catalogue,
            current_snapshot=snapshot,
            current_interpreter=_synthetic_interpreter(baselines),
            require_green=True,
        )


@pytest.mark.parametrize("occupied", ("final", "incomplete"))
def test_mutation_receipt_run_id_is_single_use_even_after_incomplete_state(
    tmp_path: Path,
    occupied: str,
) -> None:
    catalogue, snapshot, baselines, mutants = _synthetic_receipt_inputs(
        tmp_path
    )
    artifact_root = tmp_path / "artifacts"
    if occupied == "final":
        _seal_synthetic_receipt(
            artifact_root=artifact_root,
            run_id=_RECEIPT_RUN_ID,
            catalogue=catalogue,
            snapshot=snapshot,
            baselines=baselines,
            mutants=mutants,
        )
    else:
        artifact_root.mkdir()
        (artifact_root / f".incomplete-{_RECEIPT_RUN_ID}").mkdir()

    with pytest.raises(MutationAssuranceError, match="run ID already exists"):
        _seal_synthetic_receipt(
            artifact_root=artifact_root,
            run_id=_RECEIPT_RUN_ID,
            catalogue=catalogue,
            snapshot=snapshot,
            baselines=baselines,
            mutants=mutants,
        )
