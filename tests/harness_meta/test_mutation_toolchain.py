"""Adversarial contracts for the compact Phase 11 test-toolchain identity."""

from __future__ import annotations

import annotationlib
import ast
import builtins
from copy import deepcopy
from dataclasses import replace
import datetime
import errno
import functools
from importlib import import_module, metadata
from importlib.machinery import ModuleSpec, PathFinder, SourceFileLoader
from importlib.util import spec_from_loader
import json
import inspect
import os
from pathlib import Path, PurePath, PurePosixPath
import platform
import subprocess
import sys
import typing
from types import (
    CellType,
    CodeType,
    FunctionType,
    MappingProxyType,
    MethodType,
    ModuleType,
)
import warnings

import pytest
from hypothesis.errors import HypothesisDeprecationWarning

import support.mutation_toolchain as mutation_toolchain
from support.mutation_toolchain import (
    HOST_AUXILIARY_ROOTS,
    MutationToolchainError,
    TEST_TOOLCHAIN_ROOTS,
    loaded_test_toolchain_attestation,
    project_test_toolchain_identity,
    validate_test_toolchain_identity,
)


pytestmark = pytest.mark.parallel(reason="isolated_resources")


_ROOT = Path(__file__).resolve().parents[2]
_CURRENT_IDENTITY_CACHE: dict[str, object] | None = None
_SUBPROCESS_TIMEOUT_SECONDS = 120
_ACTIVE_LRU_RUNTIME_CONTEXT: object | None = None
_REQUIRES_IMPORTED_ASYNCIO_RUNNER = pytest.mark.skipif(
    sys.version_info < (3, 11),
    reason="asyncio.Runner is imported only on Python 3.11+",
)
_REQUIRES_WINDOWS_COLORAMA = pytest.mark.skipif(
    sys.platform != "win32",
    reason="the reviewed Colorama msvcrt branch is Windows-specific",
)


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


@pytest.fixture(scope="module", autouse=True)
def _bind_active_lru_runtime_context(
    pytestconfig: pytest.Config,
):
    global _ACTIVE_LRU_RUNTIME_CONTEXT

    context = (
        mutation_toolchain.capture_active_pytest_lru_runtime_context(
            pytestconfig,
            **_current_pytest_lru_identity(pytestconfig),
        )
    )
    _ACTIVE_LRU_RUNTIME_CONTEXT = context
    try:
        yield
    finally:
        _ACTIVE_LRU_RUNTIME_CONTEXT = None


def _active_lru_runtime_context() -> object:
    context = _ACTIVE_LRU_RUNTIME_CONTEXT
    if context is None:
        raise AssertionError("active LRU runtime context is unavailable")
    return context


def _normalize_eager_lru_wrappers() -> dict[str, object]:
    return mutation_toolchain.normalize_eager_lru_wrappers(
        _active_lru_runtime_context()
    )


def _attest_eager_lru_wrappers_empty() -> dict[str, object]:
    return mutation_toolchain._attest_eager_lru_wrappers_empty(
        _active_lru_runtime_context()
    )


def _loaded_test_toolchain_attestation(
    identity: object,
) -> dict[str, object]:
    return loaded_test_toolchain_attestation(
        identity,
        lru_runtime_context=_active_lru_runtime_context(),
    )


def _write_fake_distribution(
    site_packages: Path,
    *,
    name: str,
    scope: mutation_toolchain._DistributionScope,
    version: str = "1.0",
    requirements: tuple[str, ...] = (),
    metadata_tag: str | None = None,
) -> None:
    files: list[str] = []
    for raw_path in scope.import_paths:
        relative = PurePosixPath(raw_path)
        path = site_packages.joinpath(*relative.parts)
        if path.suffix:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"VALUE = {raw_path!r}\n", encoding="utf-8")
            files.append(relative.as_posix())
        else:
            path.mkdir(parents=True, exist_ok=True)
            package_file = path / "__init__.py"
            package_file.write_text(f"VALUE = {raw_path!r}\n", encoding="utf-8")
            files.append((relative / "__init__.py").as_posix())

    tag = metadata_tag or name.replace("-", "_")
    info_name = f"{tag}-{version}.dist-info"
    info = site_packages / info_name
    info.mkdir(parents=True)
    metadata_lines = [
        "Metadata-Version: 2.1",
        f"Name: {name}",
        f"Version: {version}",
        *[f"Requires-Dist: {requirement}" for requirement in requirements],
        "",
    ]
    (info / "METADATA").write_text("\n".join(metadata_lines), encoding="utf-8")
    files.append(f"{info_name}/METADATA")
    files.append(f"{info_name}/RECORD")
    (info / "RECORD").write_text(
        "".join(f"{relative},,\n" for relative in sorted(files)),
        encoding="utf-8",
    )


def _fake_toolchain(
    tmp_path: Path,
    *,
    requirements: tuple[str, ...] = (),
    registry: dict[str, mutation_toolchain._DistributionScope] | None = None,
) -> tuple[dict[str, object], Path, Path]:
    prefix = tmp_path / "venv"
    site_packages = prefix / "Lib" / "site-packages"
    site_packages.mkdir(parents=True)
    scope = mutation_toolchain._DistributionScope(
        import_paths=("pytest",),
        source_modules=(("pytest", "pytest/__init__.py"),),
    )
    _write_fake_distribution(
        site_packages,
        name="pytest",
        scope=scope,
        requirements=requirements,
    )
    selected_registry = registry or {"pytest": scope}
    identity = mutation_toolchain._build_test_toolchain_identity(
        prefix=prefix,
        search_paths=(site_packages,),
        roots=("pytest",),
        registry=selected_registry,
    )
    return identity, prefix, site_packages


def _fresh_current_identity() -> dict[str, object]:
    prefix = Path(sys.prefix).resolve(strict=True)
    return mutation_toolchain._build_test_toolchain_identity(
        prefix=prefix,
        search_paths=mutation_toolchain._distribution_search_paths(prefix),
        roots=TEST_TOOLCHAIN_ROOTS,
        registry=mutation_toolchain._ADMITTED_DISTRIBUTIONS,
        host_roots=HOST_AUXILIARY_ROOTS,
        host_registry=mutation_toolchain._HOST_AUXILIARY_DISTRIBUTIONS,
        lru_runtime_context=_active_lru_runtime_context(),
    )


def _current_identity() -> dict[str, object]:
    global _CURRENT_IDENTITY_CACHE
    if _CURRENT_IDENTITY_CACHE is None:
        _CURRENT_IDENTITY_CACHE = _fresh_current_identity()
    return deepcopy(_CURRENT_IDENTITY_CACHE)


def _selected_binding_evidence(
    module_name: str,
    path: str,
    *,
    admitted_module_names: tuple[str, ...],
) -> tuple[
    ModuleType,
    dict[str, object],
    frozenset[tuple[object, object, object, object]],
    frozenset[str],
    mutation_toolchain._SourceCodePolicy,
]:
    admitted_modules = tuple(
        import_module(name) for name in admitted_module_names
    )
    module = import_module(module_name)
    assert isinstance(module, ModuleType)
    assert all(isinstance(item, ModuleType) for item in admitted_modules)
    source_path = Path(str(module.__file__)).resolve(strict=True)
    loader = module.__spec__.loader
    variant = mutation_toolchain._source_loader_variant(
        loader,
        module_name=module_name,
        rewrite_module_is_attested=True,
    )
    entries, policy, bindings = mutation_toolchain._sealed_source_variant_payload(
        source_path.read_bytes(),
        source_path=source_path,
        variant=variant,
    )
    selected = [binding for binding in bindings if binding["path"] == path]
    assert len(selected) == 1
    attested = frozenset(
        (
            entry["qualname"],
            entry["firstlineno"],
            entry["firstcol"],
            entry["sha256"],
        )
        for entry in entries
    )
    admitted_paths = frozenset(
        os.path.normcase(
            os.fspath(Path(str(item.__file__)).resolve(strict=True))
        )
        for item in admitted_modules
    )
    return module, selected[0], attested, admitted_paths, policy


def _verify_selected_binding(
    module_name: str,
    path: str,
    *,
    admitted_module_names: tuple[str, ...],
    _inactive_source_reader: FunctionType = (
        mutation_toolchain._exact_inactive_source_import_expected_value
    ),
) -> None:
    if (
        mutation_toolchain._exact_inactive_source_import_expected_value
        is not _inactive_source_reader
    ):
        raise MutationToolchainError("inactive source reader changed")
    module, binding, attested, admitted_paths, policy = _selected_binding_evidence(
        module_name,
        path,
        admitted_module_names=admitted_module_names,
    )
    mutation_toolchain._verify_loaded_bindings(
        module,
        bindings=[binding],
        attested_code_identities=attested,
        admitted_source_paths=admitted_paths,
        admitted_class_ids=frozenset(),
        policy=policy,
        _inactive_source_reader=_inactive_source_reader,
    )


def _loaded_source_policy(module: ModuleType) -> mutation_toolchain._SourceCodePolicy:
    source_path = Path(str(module.__file__)).resolve(strict=True)
    variant = mutation_toolchain._source_loader_variant(
        module.__spec__.loader,
        module_name=module.__name__,
        rewrite_module_is_attested=True,
    )
    _entries, policy, _bindings = (
        mutation_toolchain._sealed_source_variant_payload(
            source_path.read_bytes(),
            source_path=source_path,
            variant=variant,
        )
    )
    return policy


def _colorama_winterm_source_evidence() -> tuple[
    ModuleType,
    ModuleType,
    mutation_toolchain._SourceCodePolicy,
    mutation_toolchain._SourceBinding,
    mutation_toolchain._SourceReviewedTryGuard,
]:
    module = import_module("colorama.winterm")
    provider = import_module("msvcrt")
    policy = _loaded_source_policy(module)
    source_bindings = tuple(
        binding
        for binding in policy.bindings
        if binding.path == ("get_osfhandle",)
        and binding.kind == "function"
        and binding.accessor == "direct"
    )
    assert len(source_bindings) == 1
    source_binding = source_bindings[0]
    assert len(source_binding.candidates) == 1
    candidate = source_binding.candidates[0]
    assert len(candidate.guards) == 1
    guard = candidate.guards[0]
    assert type(guard) is mutation_toolchain._SourceReviewedTryGuard
    return module, provider, policy, source_binding, guard


def _execnet_debug_source_evidence() -> tuple[
    ModuleType,
    mutation_toolchain._SourceCodePolicy,
    mutation_toolchain._SourceBinding,
    mutation_toolchain._EagerExecnetDebugOutcome,
]:
    module = import_module("execnet.gateway_base")
    policy = _loaded_source_policy(module)
    source_bindings = tuple(
        binding
        for binding in policy.bindings
        if binding.path == ("trace",)
        and binding.kind == "function"
        and binding.accessor == "direct"
    )
    assert len(source_bindings) == 1
    record = mutation_toolchain._exact_eager_execnet_debug_outcome()
    return module, policy, source_bindings[0], record


def _hypothesis_settings_classdict_evidence() -> tuple[
    ModuleType,
    mutation_toolchain._SourceCodePolicy,
    mutation_toolchain._EagerDirectSourceClassdictCellBinding,
]:
    module = import_module("hypothesis._settings")
    policy = _loaded_source_policy(module)
    record = (
        mutation_toolchain._exact_eager_hypothesis_settings_classdict_cell()
    )
    assert module is record.source_module
    assert policy.source_ast_sha256 == record.source_ast_sha256
    return module, policy, record


def _iniconfig_parsed_line_classdict_evidence() -> tuple[
    ModuleType,
    mutation_toolchain._SourceCodePolicy,
    mutation_toolchain._EagerSourceClassdictCellBinding,
]:
    module = import_module("iniconfig._parse")
    policy = _loaded_source_policy(module)
    record = (
        mutation_toolchain._EAGER_INICONFIG_PARSED_LINE_CLASSDICT_CELL_BINDING
    )
    records = (
        mutation_toolchain._exact_eager_reviewed_source_classdict_cell_bindings()
    )
    assert module is record.source_module
    assert vars(module)["ParsedLine"] is record.source_class
    assert type(records) is tuple
    assert sum(candidate is record for candidate in records) == 1
    return module, policy, record


def _hypothesis_profile_registry_evidence() -> tuple[
    ModuleType,
    mutation_toolchain._SourceCodePolicy,
    mutation_toolchain._EagerHypothesisProfileRegistryBinding,
]:
    module = import_module("hypothesis._settings")
    policy = _loaded_source_policy(module)
    record = mutation_toolchain._exact_eager_hypothesis_profile_registry()
    assert module is record.settings_binding.source_module
    assert record.mode == "moira-harness"
    return module, policy, record


def _hypothesis_compat_stdlib_alias_evidence(
    name: str,
) -> tuple[
    ModuleType,
    mutation_toolchain._SourceCodePolicy,
    mutation_toolchain._SourceBinding,
    ModuleType,
    object,
]:
    module = import_module("hypothesis.internal.compat")
    policy = _loaded_source_policy(module)
    bindings = tuple(
        binding for binding in policy.bindings if binding.path == (name,)
    )
    assert len(bindings) == 1
    if name == "dataclass_asdict":
        provider = import_module("dataclasses")
        provider_value = vars(provider)["asdict"]
    elif name == "batched":
        provider = import_module("itertools")
        provider_value = vars(provider)["batched"]
    else:
        raise AssertionError(name)
    assert vars(module)[name] is provider_value
    return module, policy, bindings[0], provider, provider_value


def _hypothesis_coverage_source_evidence() -> tuple[
    ModuleType,
    mutation_toolchain._SourceCodePolicy,
    dict[str, mutation_toolchain._SourceBinding],
    mutation_toolchain._EagerHypothesisCoverageDisabledOutcome,
]:
    module = import_module("hypothesis.internal.coverage")
    policy = _loaded_source_policy(module)
    record = (
        mutation_toolchain._exact_eager_hypothesis_coverage_disabled_outcome()
    )
    bindings = {
        binding.path[0]: binding
        for binding in policy.bindings
        if len(binding.path) == 1
    }
    assert module is record.module
    assert record.mode == "moira-harness"
    assert policy.source_ast_sha256 == record.source_ast_sha256
    assert set(bindings) == {
        "check",
        "check_block",
        "check_function",
        "pretty_file_name",
        "record_branch",
    }
    return module, policy, bindings, record


def _hypothesis_text_lazy_default_evidence() -> dict[str, object]:
    module_name = "hypothesis.strategies._internal.core"
    module, binding, attested, _paths, policy = _selected_binding_evidence(
        module_name,
        "text",
        admitted_module_names=(
            module_name,
            "hypothesis.strategies._internal.utils",
        ),
    )
    public = vars(module)["text"]
    assert type(public) is FunctionType
    wrapper = vars(public).get("__wrapped__")
    assert type(wrapper) is FunctionType
    source = vars(wrapper).get("__wrapped__")
    assert type(source) is FunctionType
    public_defaults = object.__getattribute__(public, "__defaults__")
    wrapper_defaults = object.__getattribute__(wrapper, "__defaults__")
    source_defaults = object.__getattribute__(source, "__defaults__")
    public_kwdefaults = object.__getattribute__(public, "__kwdefaults__")
    wrapper_kwdefaults = object.__getattribute__(wrapper, "__kwdefaults__")
    source_kwdefaults = object.__getattribute__(source, "__kwdefaults__")
    assert type(public_defaults) is tuple and len(public_defaults) == 1
    assert type(wrapper_defaults) is tuple and len(wrapper_defaults) == 1
    assert type(source_defaults) is tuple and len(source_defaults) == 1
    default = tuple.__getitem__(public_defaults, 0)
    assert tuple.__getitem__(wrapper_defaults, 0) is default
    assert tuple.__getitem__(source_defaults, 0) is default
    assert public_defaults is not wrapper_defaults
    assert public_defaults is not source_defaults
    assert wrapper_defaults is not source_defaults
    assert type(public_kwdefaults) is dict
    assert type(wrapper_kwdefaults) is dict
    assert type(source_kwdefaults) is dict
    assert public_kwdefaults is not wrapper_kwdefaults
    assert public_kwdefaults is not source_kwdefaults
    assert wrapper_kwdefaults is not source_kwdefaults
    lazy_type = type(default)
    assert type(lazy_type) is type
    default_namespace = object.__getattribute__(default, "__dict__")
    assert type(default_namespace) is dict
    characters_source = dict.__getitem__(default_namespace, "function")
    assert type(characters_source) is FunctionType
    characters_public = vars(module)["characters"]
    assert type(characters_public) is FunctionType
    characters_wrapper = vars(characters_public).get("__wrapped__")
    assert type(characters_wrapper) is FunctionType
    assert vars(characters_wrapper).get("__wrapped__") is characters_source
    descriptor = mutation_toolchain._EXACT_CALLABLE_CELL_CONTENTS_DESCRIPTOR
    public_closure = object.__getattribute__(public, "__closure__")
    wrapper_closure = object.__getattribute__(wrapper, "__closure__")
    assert type(public_closure) is tuple and len(public_closure) == 1
    assert type(wrapper_closure) is tuple and len(wrapper_closure) == 1
    cached_delegate = descriptor.__get__(public_closure[0], CellType)
    defines_delegate = descriptor.__get__(wrapper_closure[0], CellType)
    assert type(cached_delegate) is FunctionType
    assert type(defines_delegate) is FunctionType
    characters_public_closure = object.__getattribute__(
        characters_public,
        "__closure__",
    )
    characters_wrapper_closure = object.__getattribute__(
        characters_wrapper,
        "__closure__",
    )
    assert (
        type(characters_public_closure) is tuple
        and len(characters_public_closure) == 1
    )
    assert (
        type(characters_wrapper_closure) is tuple
        and len(characters_wrapper_closure) == 1
    )
    characters_cached_delegate = descriptor.__get__(
        characters_public_closure[0],
        CellType,
    )
    characters_defines_delegate = descriptor.__get__(
        characters_wrapper_closure[0],
        CellType,
    )
    assert type(characters_cached_delegate) is FunctionType
    assert type(characters_defines_delegate) is FunctionType
    source_binding = mutation_toolchain._source_binding_for_manifest(
        policy,
        binding,
    )
    assert len(source_binding.candidates) == 1
    candidate = source_binding.candidates[0]
    assert candidate.function_semantics is not None
    return {
        "module": module,
        "binding": binding,
        "source_binding": source_binding,
        "policy": policy,
        "attested": attested,
        "candidate": candidate,
        "public": public,
        "wrapper": wrapper,
        "source": source,
        "public_defaults": public_defaults,
        "wrapper_defaults": wrapper_defaults,
        "source_defaults": source_defaults,
        "public_kwdefaults": public_kwdefaults,
        "wrapper_kwdefaults": wrapper_kwdefaults,
        "source_kwdefaults": source_kwdefaults,
        "default": default,
        "lazy_type": lazy_type,
        "default_namespace": default_namespace,
        "cached_delegate": cached_delegate,
        "defines_delegate": defines_delegate,
        "characters_public": characters_public,
        "characters_wrapper": characters_wrapper,
        "characters_source": characters_source,
        "characters_cached_delegate": characters_cached_delegate,
        "characters_defines_delegate": characters_defines_delegate,
    }


def _hypothesis_text_runtime_codes(
    evidence: dict[str, object],
) -> tuple[CodeType, ...]:
    functions = tuple(
        evidence[name]
        for name in (
            "public",
            "wrapper",
            "source",
            "cached_delegate",
            "defines_delegate",
            "characters_public",
            "characters_wrapper",
            "characters_source",
            "characters_cached_delegate",
            "characters_defines_delegate",
        )
    )
    assert all(type(function) is FunctionType for function in functions)
    codes = tuple(
        object.__getattribute__(function, "__code__") for function in functions
    )
    lazy_entries = mutation_toolchain._EAGER_HYPOTHESIS_LAZY_STRATEGY_CALLABLE_CODES
    assert type(lazy_entries) is tuple
    for entry in lazy_entries:
        assert type(entry) is tuple and len(entry) == 5
        code = tuple.__getitem__(entry, 4)
        assert type(code) is CodeType
        if not any(code is existing for existing in codes):
            codes += (code,)
    for fingerprints in (
        mutation_toolchain._EAGER_HYPOTHESIS_LAZY_CALLABLE_FINGERPRINTS,
        mutation_toolchain._EAGER_HYPOTHESIS_SEARCH_STRATEGY_CALLABLE_FINGERPRINTS,
    ):
        assert type(fingerprints) is tuple
        for fingerprint in fingerprints:
            assert type(fingerprint) is tuple and len(fingerprint) == 19
            code = tuple.__getitem__(fingerprint, 2)
            assert type(code) is CodeType
            if not any(code is existing for existing in codes):
                codes += (code,)
    return codes


def _hypothesis_text_runtime_code_ids(
    evidence: dict[str, object],
    *extra_codes: CodeType,
) -> frozenset[int]:
    codes = _hypothesis_text_runtime_codes(evidence) + extra_codes
    assert all(type(code) is CodeType for code in codes)
    return frozenset(id(code) for code in codes)


def _verify_hypothesis_text_default_binding() -> None:
    module_name = "hypothesis.strategies._internal.core"
    _verify_selected_binding(
        module_name,
        "text",
        admitted_module_names=(
            module_name,
            "hypothesis.strategies._internal.utils",
        ),
    )


def _hypothesis_core_type_checking_guard_evidence(
    member_name: str = "composite",
) -> dict[str, object]:
    assert member_name in {"composite", "functions"}
    module = import_module("hypothesis.strategies._internal.core")
    policy = _loaded_source_policy(module)
    bindings = tuple(
        binding
        for binding in policy.bindings
        if binding.path == (member_name,)
        and binding.kind == "function"
        and binding.accessor == "direct"
    )
    assert len(bindings) == 1
    binding = bindings[0]
    candidates = binding.candidates
    expected_branches = (True, False)
    assert type(candidates) is tuple
    assert len(candidates) == len(expected_branches)

    type_checking_reference = mutation_toolchain._SourceExpression(
        kind="reference",
        payload=("typing", "TYPE_CHECKING"),
        ast_shape=(
            "Attribute(value=Name(id='typing', ctx=Load()), "
            "attr='TYPE_CHECKING', ctx=Load())"
        ),
    )
    paramspec_reference = mutation_toolchain._SourceExpression(
        kind="reference",
        payload=("ParamSpec",),
        ast_shape="Name(id='ParamSpec', ctx=Load())",
    )
    none_literal = mutation_toolchain._SourceExpression(
        kind="literal",
        payload=["NoneType"],
        ast_shape="Constant(value=None)",
    )
    paramspec_is_not_none = mutation_toolchain._SourceExpression(
        kind="compare",
        payload=(paramspec_reference, (("is-not", none_literal),)),
        ast_shape=(
            "Compare(left=Name(id='ParamSpec', ctx=Load()), "
            "ops=[IsNot()], comparators=[Constant(value=None)])"
        ),
    )
    guard_expression = mutation_toolchain._SourceExpression(
        kind="or",
        payload=(type_checking_reference, paramspec_is_not_none),
        ast_shape=(
            "BoolOp(op=Or(), values=[Attribute(value=Name(id='typing', "
            "ctx=Load()), attr='TYPE_CHECKING', ctx=Load()), "
            "Compare(left=Name(id='ParamSpec', ctx=Load()), "
            "ops=[IsNot()], comparators=[Constant(value=None)])])"
        ),
    )
    expected_guards = tuple(
        mutation_toolchain._SourceExpressionGuard(
            expression=guard_expression,
            branch=branch,
        )
        for branch in expected_branches
    )
    assert all(candidate.guards_complete is True for candidate in candidates)
    assert tuple(candidate.guards for candidate in candidates) == tuple(
        (guard,) for guard in expected_guards
    )

    typing_module = sys.modules["typing"]
    assert type(typing_module) is ModuleType
    assert typing_module is typing
    assert vars(module)["typing"] is typing_module
    paramspec = vars(typing_module)["ParamSpec"]
    assert type(paramspec) is type
    assert vars(module)["ParamSpec"] is paramspec
    assert vars(typing_module)["TYPE_CHECKING"] is False
    active = mutation_toolchain._active_source_binding_candidate(
        module,
        policy=policy,
        binding=binding,
    )
    expected_active_index = 0
    assert active is candidates[expected_active_index]
    return {
        "module": module,
        "policy": policy,
        "binding": binding,
        "candidates": candidates,
        "guard_expression": guard_expression,
        "typing_module": typing_module,
        "paramspec": paramspec,
        "active": active,
        "expected_active_index": expected_active_index,
    }


def _select_hypothesis_core_composite_candidate(
    evidence: dict[str, object],
) -> mutation_toolchain._SourceBindingCandidate | None:
    module = evidence["module"]
    policy = evidence["policy"]
    binding = evidence["binding"]
    assert type(module) is ModuleType
    assert type(policy) is mutation_toolchain._SourceCodePolicy
    assert type(binding) is mutation_toolchain._SourceBinding
    return mutation_toolchain._active_source_binding_candidate(
        module,
        policy=policy,
        binding=binding,
    )


def _restore_exact_mapping_items(
    mapping: dict[object, object],
    items: tuple[tuple[object, object], ...],
) -> None:
    dict.clear(mapping)
    for key, value in items:
        dict.__setitem__(mapping, key, value)


def _mapping_items_are_identical(
    mapping: dict[object, object],
    expected: tuple[tuple[object, object], ...],
) -> bool:
    current = tuple(dict.items(mapping))
    return len(current) == len(expected) and all(
        current_key is expected_key and current_value is expected_value
        for (current_key, current_value), (expected_key, expected_value) in zip(
            current,
            expected,
            strict=True,
        )
    )


def _verify_hypothesis_coverage_surface(
    module: ModuleType,
    policy: mutation_toolchain._SourceCodePolicy,
) -> mutation_toolchain._EagerHypothesisCoverageDisabledOutcome:
    record = (
        mutation_toolchain._verify_eager_hypothesis_coverage_disabled_outcome(
            policy=policy,
        )
    )
    for path in (
        "check",
        "check_block",
        "check_function",
        "pretty_file_name",
        "record_branch",
    ):
        _verify_selected_binding(
            "hypothesis.internal.coverage",
            path,
            admitted_module_names=("contextlib",),
        )
    mutation_toolchain._verify_runtime_source_bindings(module, policy=policy)
    namespace = vars(module)
    assert namespace["IN_COVERAGE_TESTS"] is False
    assert all(
        name not in namespace
        for name in ("written", "record_branch", "check_block")
    )
    return record


def _hypothesis_entropy_randomlike_evidence() -> tuple[
    ModuleType,
    mutation_toolchain._SourceCodePolicy,
    dict[str, mutation_toolchain._SourceBinding],
    mutation_toolchain._EagerHypothesisEntropyRandomLikeProvider,
]:
    module = import_module("hypothesis.internal.entropy")
    policy = _loaded_source_policy(module)
    record = (
        mutation_toolchain._exact_eager_hypothesis_entropy_randomlike_provider()
    )
    bindings = {
        ".".join(binding.path): binding
        for binding in policy.bindings
        if binding.path and binding.path[0] == "RandomLike"
    }
    assert module is record.module
    assert record.mode == "moira-harness"
    assert policy.source_ast_sha256 == record.source_ast_sha256
    assert set(bindings) == {
        "RandomLike",
        "RandomLike.seed",
        "RandomLike.getstate",
        "RandomLike.setstate",
    }
    return module, policy, bindings, record


def _hypothesis_entropy_compat_flags_evidence() -> tuple[
    ModuleType,
    mutation_toolchain._SourceCodePolicy,
    mutation_toolchain._SourceBinding,
    mutation_toolchain._EagerHypothesisEntropyRandomLikeProvider,
]:
    module, policy, _bindings, record = (
        _hypothesis_entropy_randomlike_evidence()
    )
    refcount_bindings = tuple(
        binding
        for binding in policy.bindings
        if binding.path == ("_get_platform_base_refcount",)
    )
    assert len(refcount_bindings) == 1
    binding = refcount_bindings[0]
    assert len(binding.candidates) == 1
    assert len(binding.candidates[0].guards) == 1
    assert type(binding.candidates[0].guards[0]) is (
        mutation_toolchain._SourceExpressionGuard
    )
    return module, policy, binding, record


def _verify_hypothesis_entropy_randomlike_surface(
    module: ModuleType,
    policy: mutation_toolchain._SourceCodePolicy,
) -> mutation_toolchain._EagerHypothesisEntropyRandomLikeProvider:
    record = (
        mutation_toolchain._verify_eager_hypothesis_entropy_randomlike_provider()
    )
    for path in (
        "RandomLike",
        "RandomLike.seed",
        "RandomLike.getstate",
        "RandomLike.setstate",
        "_get_platform_base_refcount",
    ):
        _verify_selected_binding(
            "hypothesis.internal.entropy",
            path,
            admitted_module_names=(),
        )
    mutation_toolchain._verify_runtime_source_bindings(module, policy=policy)
    return record


def _exact_function_clone(function: FunctionType) -> FunctionType:
    clone = FunctionType(
        function.__code__,
        function.__globals__,
        function.__name__,
        function.__defaults__,
        function.__closure__,
    )
    clone.__kwdefaults__ = function.__kwdefaults__
    clone.__dict__.update(function.__dict__)
    clone.__annotations__ = function.__annotations__
    clone.__module__ = function.__module__
    clone.__qualname__ = function.__qualname__
    clone.__doc__ = function.__doc__
    return clone


def _exact_function_clone_with_closure(
    function: FunctionType,
    closure: tuple[CellType, ...],
) -> FunctionType:
    clone = FunctionType(
        object.__getattribute__(function, "__code__"),
        object.__getattribute__(function, "__globals__"),
        object.__getattribute__(function, "__name__"),
        object.__getattribute__(function, "__defaults__"),
        closure,
    )
    clone.__kwdefaults__ = object.__getattribute__(function, "__kwdefaults__")
    clone.__dict__.update(object.__getattribute__(function, "__dict__"))
    clone.__module__ = object.__getattribute__(function, "__module__")
    clone.__qualname__ = object.__getattribute__(function, "__qualname__")
    clone.__doc__ = object.__getattribute__(function, "__doc__")
    return clone


def _iniconfig_parsed_line_classdict_shape(
    record: mutation_toolchain._EagerSourceClassdictCellBinding,
) -> object:
    return mutation_toolchain._reviewed_source_classdict_cell_shape(
        record.classdict_cell,
        depth=0,
        context=mutation_toolchain._RuntimeSnapshotContext(active={}),
    )


def _assert_iniconfig_parsed_line_graph_is_exact(
    record: mutation_toolchain._EagerSourceClassdictCellBinding,
) -> None:
    namespace = type.__getattribute__(record.source_class, "__dict__")
    current_items = tuple(dict.items(record.classdict))
    assert type(namespace) is MappingProxyType
    assert namespace["__annotate_func__"] is record.wrapper
    assert namespace["__classdictcell__"] is record.classdict_cell
    assert record.cell_contents_descriptor.__get__(
        record.wrapper_cell,
        record.cell_type,
    ) is record.original
    assert record.cell_contents_descriptor.__get__(
        record.classdict_cell,
        record.cell_type,
    ) is record.classdict
    assert len(current_items) == len(record.classdict_items)
    assert all(
        current_name == expected_name and current_value is expected_value
        for (current_name, current_value), (expected_name, expected_value) in zip(
            current_items,
            record.classdict_items,
            strict=True,
        )
    )
    assert dict.__getitem__(record.classdict, "__annotate_func__") is record.original
    assert (
        dict.__getitem__(record.classdict, "__classdictcell__")
        is record.classdict_cell
    )


def _assert_iniconfig_guard_rejects_without_annotation_execution(
    record: mutation_toolchain._EagerSourceClassdictCellBinding,
    operation: typing.Callable[[], object],
    *,
    additional_codes: tuple[CodeType, ...] = (),
) -> None:
    annotation_codes = (
        record.wrapper_code,
        record.original_code,
        *additional_codes,
    )
    calls: list[CodeType] = []

    def profiler(frame: object, event: str, _arg: object) -> None:
        if event == "call" and frame.f_code in annotation_codes:
            calls.append(frame.f_code)

    previous_profile = sys.getprofile()
    caught: BaseException | None = None
    try:
        sys.setprofile(profiler)
        try:
            operation()
        except BaseException as exc:
            caught = exc
    finally:
        sys.setprofile(previous_profile)
    assert isinstance(caught, MutationToolchainError)
    assert calls == []
    assert sys.getprofile() is previous_profile


def _unregistered_namedtuple_classdict_evidence() -> tuple[
    type[object],
    FunctionType,
    FunctionType,
    CellType,
]:
    namespace: dict[str, object] = {}
    code = compile(
        "import typing\n"
        "class UnregisteredNamedTuple(typing.NamedTuple):\n"
        "    value: int\n",
        "<unregistered-namedtuple-classdict-canary>",
        "exec",
        dont_inherit=True,
        optimize=sys.flags.optimize,
    )
    exec(code, namespace)
    owner = dict.__getitem__(namespace, "UnregisteredNamedTuple")
    assert type(owner) is type
    owner_namespace = type.__getattribute__(owner, "__dict__")
    wrapper = owner_namespace["__annotate_func__"]
    classdict_cell = owner_namespace["__classdictcell__"]
    assert type(wrapper) is FunctionType
    assert type(classdict_cell) is CellType
    classdict = classdict_cell.cell_contents
    assert type(classdict) is dict
    original = dict.__getitem__(classdict, "__annotate_func__")
    assert type(original) is FunctionType
    assert dict.__getitem__(classdict, "__classdictcell__") is classdict_cell
    assert original.__closure__ == (classdict_cell,)
    return owner, wrapper, original, classdict_cell


def _compiled_source_candidate_code(
    source: bytes,
    *,
    source_path: Path,
    qualname: str,
    first_line: int,
) -> CodeType:
    pending = [
        compile(
            source,
            str(source_path),
            "exec",
            dont_inherit=True,
            optimize=sys.flags.optimize,
        )
    ]
    matches: list[CodeType] = []
    while pending:
        current = pending.pop()
        for constant in current.co_consts:
            if type(constant) is not CodeType:
                continue
            pending.append(constant)
            if (
                constant.co_qualname == qualname
                and constant.co_firstlineno == first_line
            ):
                matches.append(constant)
    assert len(matches) == 1
    return matches[0]


def test_public_structural_code_digest_is_canonical() -> None:
    source = "def killer(value):\n    return value + 1\n"
    first = compile(source, "first-checkout.py", "exec", dont_inherit=True)
    second = compile(source, "second-checkout.py", "exec", dont_inherit=True)
    changed = compile(
        "def killer(value):\n    return value - 1\n",
        "first-checkout.py",
        "exec",
        dont_inherit=True,
    )

    assert (
        mutation_toolchain.PYTHON_CODE_STRUCTURAL_ALGORITHM
        == "python_code_structural_v1"
    )
    digest = mutation_toolchain.structural_python_code_sha256(first)
    assert digest == mutation_toolchain.structural_python_code_sha256(second)
    assert digest != mutation_toolchain.structural_python_code_sha256(changed)
    assert len(digest) == 64
    assert "structural_python_code_sha256" in mutation_toolchain.__all__


@pytest.mark.parametrize(
    "mutation",
    [
        "defaults",
        "kwdefaults",
        "annotations",
        "function_dict",
        "wrapped",
        "closure",
        "annotate",
        "type_params",
    ],
)
def test_runtime_function_snapshot_binds_all_mutable_semantics(
    mutation: str,
) -> None:
    closure_state = {"value": 1}

    def wrapped(value: object) -> object:
        return value

    def target(
        value: object = {"default": 1},
        *,
        option: object = {"keyword": 1},
    ) -> object:
        closure_state
        return value if option else wrapped(value)

    target.__annotate__ = None
    target.__annotations__ = {"return": int}
    target.semantic_state = {"dict": 1}
    target.__wrapped__ = wrapped
    baseline = mutation_toolchain._runtime_value_shape(target)

    if mutation == "defaults":
        assert target.__defaults__ is not None
        target.__defaults__[0]["default"] = 2
    elif mutation == "kwdefaults":
        assert target.__kwdefaults__ is not None
        target.__kwdefaults__["option"]["keyword"] = 2
    elif mutation == "annotations":
        target.__annotations__["return"] = str
    elif mutation == "function_dict":
        target.semantic_state["dict"] = 2
    elif mutation == "wrapped":
        target.__wrapped__ = len
    elif mutation == "closure":
        closure_state["value"] = 2
    elif mutation == "annotate":
        def annotate(format: object) -> dict[str, object]:
            return {"return": str, "format": format}

        target.__annotate__ = annotate
    elif mutation == "type_params":
        namespace: dict[str, object] = {}
        exec("def generic[T](value: T) -> T:\n    return value\n", namespace)
        generic = namespace["generic"]
        assert isinstance(generic, FunctionType)
        assert generic.__type_params__
        target.__type_params__ = generic.__type_params__
    else:  # pragma: no cover - the parameter list is closed above
        raise AssertionError(mutation)

    assert mutation_toolchain._runtime_value_shape(target) != baseline


def test_runtime_function_snapshot_does_not_execute_deferred_annotations() -> None:
    calls: list[str] = []
    namespace: dict[str, object] = {"calls": calls}
    exec(
        "def target(value: calls.append('executed')):\n"
        "    return value\n",
        namespace,
    )
    target = namespace["target"]
    assert isinstance(target, FunctionType)
    assert target.__annotate__ is not None

    mutation_toolchain._runtime_value_shape(target)

    assert calls == []


def test_hypothesis_file_root_is_one_exact_source_closure_path(
    tmp_path: Path,
) -> None:
    script = """
import json
import sys
from dataclasses import replace
from types import MappingProxyType, ModuleType

import support.mutation_toolchain as toolchain

binding = toolchain._EAGER_HYPOTHESIS_FILE_ROOT_BINDING
anchor = toolchain._EAGER_HYPOTHESIS_FILE_ROOT_ANCHOR
anchor_reader = toolchain._EAGER_HYPOTHESIS_FILE_ROOT_ANCHOR_READER
accessor = toolchain._eager_hypothesis_file_root_binding
source_attestor = toolchain._EAGER_HYPOTHESIS_FILE_ROOT_PATHLIB_SOURCE_ATTESTOR
owner = binding.owner
root = binding.value
root_cell = binding.root_cell
baseline = toolchain._runtime_value_shape(root)
owner_baseline = toolchain._runtime_value_shape(owner)
if baseline[:3] != [
    "reviewed-source-closure-path-v1",
    "hypothesis.internal.escalation.is_hypothesis_file.__closure__.root",
    "pathlib.WindowsPath",
]:
    raise SystemExit("genuine Hypothesis closure root was not narrowly admitted")


def assert_exact_restoration(label):
    if toolchain._EAGER_HYPOTHESIS_FILE_ROOT_BINDING is not binding:
        raise SystemExit(f"{label}: genuine binding was not restored")
    if toolchain._EAGER_HYPOTHESIS_FILE_ROOT_ANCHOR is not anchor:
        raise SystemExit(f"{label}: genuine anchor was not restored")
    if toolchain._EAGER_HYPOTHESIS_FILE_ROOT_ANCHOR_READER is not anchor_reader:
        raise SystemExit(f"{label}: genuine anchor reader was not restored")
    if toolchain._eager_hypothesis_file_root_binding is not accessor:
        raise SystemExit(f"{label}: genuine accessor was not restored")
    if (
        toolchain._EAGER_HYPOTHESIS_FILE_ROOT_PATHLIB_SOURCE_ATTESTOR
        is not source_attestor
    ):
        raise SystemExit(f"{label}: genuine source attestor was not restored")
    if root_cell.cell_contents is not root:
        raise SystemExit(f"{label}: genuine closure root was not restored")
    if toolchain._runtime_value_shape(root) != baseline:
        raise SystemExit(f"{label}: restored root changed logical shape")
    if toolchain._runtime_value_shape(owner) != owner_baseline:
        raise SystemExit(f"{label}: restored owner changed logical shape")


def expect_rejected(label, mutate, restore, fragment, value=root):
    mutation_error = None
    mutate()
    try:
        try:
            toolchain._runtime_value_shape(value)
        except toolchain.MutationToolchainError as exc:
            mutation_error = str(exc)
    finally:
        restore()
    if mutation_error is None or fragment not in mutation_error:
        raise SystemExit(
            f"{label}: mutation was not rejected by {fragment!r}: "
            f"{mutation_error!r}"
        )
    assert_exact_restoration(label)


# These are the three legitimate lazy-cache transitions supported by
# PurePath.  They must not change the logical closure-path shape.
object.__getattribute__(root, "_str_normcase")
object.__getattribute__(root, "_parts_normcase")
hash(root)
if toolchain._runtime_value_shape(root) != baseline:
    raise SystemExit("legitimate Hypothesis root lazy caches changed its shape")
if toolchain._runtime_value_shape(owner) != owner_baseline:
    raise SystemExit("legitimate Hypothesis root lazy caches changed owner shape")


def read_root_slot(name):
    descriptor = binding.slot_descriptors[name][1]
    try:
        return (
            True,
            toolchain._EAGER_MEMBER_DESCRIPTOR_GET(
                descriptor,
                root,
                binding.path_type,
            ),
        )
    except AttributeError:
        return (False, None)


def restore_root_slots(states):
    for name, (present, value) in states.items():
        try:
            object.__delattr__(root, name)
        except AttributeError:
            pass
        if present:
            object.__setattr__(root, name, value)


lazy_names = ("_str_normcase_cached", "_parts_normcase_cached", "_hash")
lazy_states = {name: read_root_slot(name) for name in lazy_names}


def install_hash_without_normcase():
    for name in lazy_names:
        try:
            object.__delattr__(root, name)
        except AttributeError:
            pass
    object.__setattr__(root, "_hash", binding.normalized_hash)


expect_rejected(
    "hash-without-normcase",
    install_hash_without_normcase,
    lambda: restore_root_slots(lazy_states),
    "lazy cache changed",
)

replacement = binding.path_type(binding.rendered)
if replacement is root or replacement != root:
    raise SystemExit("equal, distinct WindowsPath replacement was not constructed")
alias_name = "_phase11_hypothesis_root_alias"
alias_module = ModuleType(alias_name)
alias_module.value = replacement
sys.modules[alias_name] = alias_module
singleton_shape = toolchain._module_singleton_shape(replacement)
if singleton_shape is None or singleton_shape[0] != "module-singleton":
    raise SystemExit("replacement did not exercise module-singleton temptation")
try:
    expect_rejected(
        "equal-alias",
        lambda: None,
        lambda: None,
        "unregistered reviewed source closure path",
        replacement,
    )
    expect_rejected(
        "closure-cell-swap",
        lambda: setattr(root_cell, "cell_contents", replacement),
        lambda: setattr(root_cell, "cell_contents", root),
        "unregistered reviewed source closure path",
        owner,
    )
finally:
    sys.modules.pop(alias_name, None)

hostile_calls = []


class HostileMetadata:
    def __eq__(self, other):
        hostile_calls.append("eq")
        return True

    def __ne__(self, other):
        hostile_calls.append("ne")
        return False

    def __hash__(self):
        hostile_calls.append("hash")
        return 0

    def __repr__(self):
        hostile_calls.append("repr")
        return "<hostile>"


for label, target_module in (
    ("owner-module-name", binding.owner_module),
    ("package-module-name", binding.package_module),
    ("pathlib-module-name", binding.path_module),
    ("parser-module-name", binding.parser),
):
    namespace = vars(target_module)
    original = dict.__getitem__(namespace, "__name__")
    hostile = HostileMetadata()
    expect_rejected(
        label,
        lambda namespace=namespace, hostile=hostile: dict.__setitem__(
            namespace,
            "__name__",
            hostile,
        ),
        lambda namespace=namespace, original=original: dict.__setitem__(
            namespace,
            "__name__",
            original,
        ),
        "provenance changed",
    )

for label, target in (
    ("owner-function-module", binding.owner),
    ("factory-function-module", binding.factory),
):
    original = target.__module__
    hostile = HostileMetadata()
    expect_rejected(
        label,
        lambda target=target, hostile=hostile: setattr(target, "__module__", hostile),
        lambda target=target, original=original: setattr(
            target,
            "__module__",
            original,
        ),
        "owner provenance changed",
    )

if hostile_calls:
    raise SystemExit(f"hostile scalar callbacks executed: {hostile_calls!r}")

for label, target, attribute in (
    ("owner-module-equal-string", binding.owner, "__module__"),
    ("owner-name-equal-string", binding.owner, "__name__"),
    ("owner-qualname-equal-string", binding.owner, "__qualname__"),
    ("factory-module-equal-string", binding.factory, "__module__"),
    ("factory-name-equal-string", binding.factory, "__name__"),
    ("factory-qualname-equal-string", binding.factory, "__qualname__"),
):
    original = getattr(target, attribute)
    replacement_string = original.encode("utf-8").decode("utf-8")
    if replacement_string is original:
        replacement_string = (original + "!")[:-1]
    if replacement_string != original or replacement_string is original:
        raise SystemExit(f"{label}: exact equal string was not constructed")
    expect_rejected(
        label,
        lambda target=target, attribute=attribute, replacement_string=replacement_string: setattr(
            target,
            attribute,
            replacement_string,
        ),
        lambda target=target, attribute=attribute, original=original: setattr(
            target,
            attribute,
            original,
        ),
        "owner provenance changed",
    )

owner_namespace = vars(binding.owner_module)
original_owner_path = dict.__getitem__(owner_namespace, "Path")
expect_rejected(
    "owner-Path-rebind",
    lambda: dict.__setitem__(owner_namespace, "Path", object()),
    lambda: dict.__setitem__(owner_namespace, "Path", original_owner_path),
    "owner provenance changed",
)
original_file_cache = dict.__getitem__(owner_namespace, "FILE_CACHE")
replacement_file_cache = {binding.package_module: binding.cache}
expect_rejected(
    "outer-FILE_CACHE-replacement",
    lambda: dict.__setitem__(owner_namespace, "FILE_CACHE", replacement_file_cache),
    lambda: dict.__setitem__(owner_namespace, "FILE_CACHE", original_file_cache),
    "owner provenance changed",
)


def replacement_resolve(self, strict=False):
    return self


for label, target_class, attribute, replacement_member in (
    ("Path.resolve", binding.path_factory, "resolve", replacement_resolve),
    (
        "PurePath.relative_to",
        binding.pure_path_type,
        "relative_to",
        replacement_resolve,
    ),
    (
        "PurePath._str_normcase",
        binding.pure_path_type,
        "_str_normcase",
        property(lambda self: "forged"),
    ),
):
    original = vars(target_class).get(attribute)
    expect_rejected(
        label,
        lambda target_class=target_class, attribute=attribute, replacement_member=replacement_member: setattr(
            target_class,
            attribute,
            replacement_member,
        ),
        lambda target_class=target_class, attribute=attribute, original=original: setattr(
            target_class,
            attribute,
            original,
        ),
        "executable provenance changed",
    )

original_resolve_code = binding.path_resolve.__code__
expect_rejected(
    "Path.resolve-code",
    lambda: setattr(binding.path_resolve, "__code__", replacement_resolve.__code__),
    lambda: setattr(binding.path_resolve, "__code__", original_resolve_code),
    "executable provenance changed",
)

pure_path_eq = vars(binding.pure_path_type).get("__eq__")
original_eq_code = pure_path_eq.__code__
outside_key = r"Z:\\definitely-outside-moira-phase11\\x.py"
binding.cache.pop(outside_key, None)
before_eq_mutation = owner(outside_key)
binding.cache.pop(outside_key, None)


def hostile_eq(self, other):
    return True


pure_path_eq.__code__ = hostile_eq.__code__
try:
    after_eq_mutation = owner(outside_key)
    binding.cache.pop(outside_key, None)
    if before_eq_mutation or not after_eq_mutation:
        raise SystemExit(
            "PurePath.__eq__ mutation did not falsify the owner decision"
        )
    try:
        toolchain._runtime_value_shape(root)
    except toolchain.MutationToolchainError as exc:
        if "pathlib.PurePath.__eq__" not in str(exc):
            raise SystemExit(
                "PurePath.__eq__ mutation reached the wrong rejection: "
                f"{exc}"
            )
    else:
        raise SystemExit("PurePath.__eq__ mutation bypassed sealed source")
finally:
    pure_path_eq.__code__ = original_eq_code
    binding.cache.pop(outside_key, None)
assert_exact_restoration("PurePath.__eq__-source-attestation")

str(replacement)


def read_replacement_slot(name):
    descriptor = binding.slot_descriptors[name][1]
    try:
        return toolchain._EAGER_MEMBER_DESCRIPTOR_GET(
            descriptor,
            replacement,
            binding.path_type,
        )
    except AttributeError:
        return toolchain._EAGER_ATTRIBUTE_MISSING


replacement_raw_paths = read_replacement_slot("_raw_paths")
replacement_drive = read_replacement_slot("_drv")
replacement_root = read_replacement_slot("_root")
replacement_tail = read_replacement_slot("_tail_cached")
replacement_rendered = read_replacement_slot("_str")
replacement_normalized = toolchain._EAGER_STR_LOWER_DESCRIPTOR(
    replacement_rendered
)
replacement_parts = tuple(
    toolchain._EAGER_STR_SPLIT_DESCRIPTOR(
        replacement_normalized,
        binding.parser_separator,
    )
)
replacement_hash = toolchain._EAGER_STR_HASH_DESCRIPTOR(replacement_normalized)
for name in lazy_names:
    try:
        object.__delattr__(replacement, name)
    except AttributeError:
        pass
forged_binding = replace(
    binding,
    value=replacement,
    raw_paths=replacement_raw_paths,
    raw_path_values=tuple(replacement_raw_paths),
    drive=replacement_drive,
    root=replacement_root,
    tail=replacement_tail,
    tail_values=tuple(replacement_tail),
    rendered=replacement_rendered,
    normalized_rendered=replacement_normalized,
    normalized_parts=replacement_parts,
    normalized_hash=replacement_hash,
)
forged_anchor = MappingProxyType(
    {toolchain._HYPOTHESIS_FILE_ROOT_ANCHOR_KEY: forged_binding}
)

for name in type(binding).__slots__:
    descriptor = vars(type(binding)).get(name)
    original_field_value = toolchain._EAGER_MEMBER_DESCRIPTOR_GET(
        descriptor,
        binding,
        type(binding),
    )
    object.__setattr__(binding, name, object())
    try:
        try:
            toolchain._runtime_value_shape(root)
        except toolchain.MutationToolchainError as exc:
            if "binding fingerprint changed" not in str(exc):
                raise SystemExit(
                    f"binding-slot-{name}: wrong rejection: {exc}"
                )
        else:
            raise SystemExit(f"binding-slot-{name}: in-place mutation was accepted")
    finally:
        object.__setattr__(binding, name, original_field_value)
assert_exact_restoration("binding-slot-fingerprint")


def install_coordinated_forgery():
    root_cell.cell_contents = replacement
    toolchain._EAGER_HYPOTHESIS_FILE_ROOT_BINDING = forged_binding
    toolchain._EAGER_HYPOTHESIS_FILE_ROOT_ANCHOR = forged_anchor


def restore_coordinated_forgery():
    root_cell.cell_contents = root
    toolchain._EAGER_HYPOTHESIS_FILE_ROOT_BINDING = binding
    toolchain._EAGER_HYPOTHESIS_FILE_ROOT_ANCHOR = anchor


expect_rejected(
    "coordinated-cell-binding-anchor-forgery",
    install_coordinated_forgery,
    restore_coordinated_forgery,
    "genuine-binding anchor changed",
    replacement,
)
expect_rejected(
    "global-accessor-forgery",
    lambda: (
        setattr(root_cell, "cell_contents", replacement),
        setattr(
            toolchain,
            "_eager_hypothesis_file_root_binding",
            lambda: forged_binding,
        ),
    ),
    lambda: (
        setattr(root_cell, "cell_contents", root),
        setattr(toolchain, "_eager_hypothesis_file_root_binding", accessor),
    ),
    "accessor changed",
    replacement,
)
expect_rejected(
    "anchor-reader-rebind",
    lambda: setattr(
        toolchain,
        "_EAGER_HYPOTHESIS_FILE_ROOT_ANCHOR_READER",
        lambda: forged_binding,
    ),
    lambda: setattr(
        toolchain,
        "_EAGER_HYPOTHESIS_FILE_ROOT_ANCHOR_READER",
        anchor_reader,
    ),
    "anchor reader provider changed",
)

assert_exact_restoration("final")
print(json.dumps({
    "anchor_forgery_rejected": True,
    "anchor_reader_rejected": True,
    "binding_slot_fingerprint_rejected": True,
    "callback_free_metadata_rejected": True,
    "category": baseline[0],
    "closure_swap_rejected": True,
    "equal_alias_rejected": True,
    "equal_metadata_rejected": True,
    "exact_restoration": True,
    "label": baseline[1],
    "lazy_cache_invalid_rejected": True,
    "lazy_cache_stable": True,
    "owner_globals_rejected": True,
    "pathlib_eq_source_rejected": True,
    "pathlib_executable_rejected": True,
    "reader_replacement_rejected": True,
}, sort_keys=True, separators=(",", ":")))
"""
    environment = os.environ.copy()
    environment.pop("PYTEST_CURRENT_TEST", None)
    environment["PYTHONPATH"] = os.fspath(_ROOT / "tests")
    environment["PYTHONPYCACHEPREFIX"] = os.fspath(
        tmp_path / "hypothesis-root-pycache"
    )
    completed = subprocess.run(
        [sys.executable, "-B", "-c", script],
        cwd=_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=_SUBPROCESS_TIMEOUT_SECONDS,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    result = json.loads(completed.stdout.strip().splitlines()[-1])
    assert result == {
        "anchor_forgery_rejected": True,
        "anchor_reader_rejected": True,
        "binding_slot_fingerprint_rejected": True,
        "callback_free_metadata_rejected": True,
        "category": "reviewed-source-closure-path-v1",
        "closure_swap_rejected": True,
        "equal_alias_rejected": True,
        "equal_metadata_rejected": True,
        "exact_restoration": True,
        "label": (
            "hypothesis.internal.escalation.is_hypothesis_file."
            "__closure__.root"
        ),
        "lazy_cache_invalid_rejected": True,
        "lazy_cache_stable": True,
        "owner_globals_rejected": True,
        "pathlib_eq_source_rejected": True,
        "pathlib_executable_rejected": True,
        "reader_replacement_rejected": True,
    }


def test_hypothesis_file_root_pathlib_source_rejects_preseal_eq_mutation(
    tmp_path: Path,
) -> None:
    script = r'''
import json
import pathlib

pure_path_eq = vars(pathlib.PurePath)["__eq__"]
original_code = pure_path_eq.__code__


def hostile_eq(self, other):
    if str(self) == r"Z:\definitely-outside-moira-phase11\x.py":
        return True
    if not isinstance(other, PurePath):
        return NotImplemented
    return self._str_normcase == other._str_normcase and self.parser is other.parser


pure_path_eq.__code__ = hostile_eq.__code__.replace(
    co_filename=original_code.co_filename,
    co_firstlineno=original_code.co_firstlineno,
    co_name=original_code.co_name,
    co_qualname=original_code.co_qualname,
)
try:
    try:
        import support.mutation_toolchain as toolchain
        toolchain._runtime_value_shape(
            toolchain._EAGER_HYPOTHESIS_FILE_ROOT_BINDING.value
        )
    except Exception as exc:
        error_type = type(exc).__name__
        error = str(exc)
    else:
        raise SystemExit("preseal PurePath.__eq__ mutation was accepted")
finally:
    pure_path_eq.__code__ = original_code

if error_type != "MutationToolchainError":
    raise SystemExit(f"wrong preseal rejection type: {error_type}: {error}")
if "pathlib" not in error or not any(
    fragment in error
    for fragment in (
        "loaded code differs from sealed source",
        "callable binding changed",
    )
):
    raise SystemExit(f"wrong preseal rejection: {error}")
print(json.dumps({"preseal_pathlib_source_rejected": True}, sort_keys=True))
'''
    environment = os.environ.copy()
    environment.pop("PYTEST_CURRENT_TEST", None)
    environment["PYTHONPATH"] = os.fspath(_ROOT / "tests")
    environment["PYTHONPYCACHEPREFIX"] = os.fspath(
        tmp_path / "hypothesis-root-preseal-pycache"
    )
    completed = subprocess.run(
        [sys.executable, "-B", "-c", script],
        cwd=_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=_SUBPROCESS_TIMEOUT_SECONDS,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert json.loads(completed.stdout.strip().splitlines()[-1]) == {
        "preseal_pathlib_source_rejected": True,
    }


def test_hypothesis_file_root_capture_rejects_hostile_slots_without_callbacks(
    tmp_path: Path,
) -> None:
    script = """
import json
import pathlib

calls = []


class HostileSlotName:
    def __init__(self, expected):
        self.expected = expected

    def __eq__(self, other):
        calls.append("eq")
        return other == self.expected

    def __ne__(self, other):
        calls.append("ne")
        return other != self.expected

    def __hash__(self):
        calls.append("hash")
        return 0

    def __repr__(self):
        calls.append("repr")
        return "<hostile-slot-name>"


original_layout = pathlib.PurePath.__slots__
expected_layout = (
    "_raw_paths",
    "_drv",
    "_root",
    "_tail_cached",
    "_str",
    "_str_normcase_cached",
    "_parts_normcase_cached",
    "_hash",
)
pathlib.PurePath.__slots__ = tuple(
    HostileSlotName(name) for name in expected_layout
)
error_type = None
error_message = None
try:
    try:
        import support.mutation_toolchain  # noqa: F401
    except Exception as exc:
        error_type = type(exc).__name__
        error_message = str(exc)
finally:
    pathlib.PurePath.__slots__ = original_layout
if error_type != "MutationToolchainError":
    raise SystemExit(f"hostile slot layout was not rejected: {error_type}")
if "pathlib layout changed" not in error_message:
    raise SystemExit(f"hostile slot rejection was not specific: {error_message}")
if calls:
    raise SystemExit(f"hostile slot callbacks executed: {calls!r}")
if pathlib.PurePath.__slots__ is not original_layout:
    raise SystemExit("PurePath slot layout was not restored exactly")
print(json.dumps({
    "callback_count": len(calls),
    "exact_restoration": True,
    "hostile_slots_rejected": True,
}, sort_keys=True, separators=(",", ":")))
"""
    environment = os.environ.copy()
    environment.pop("PYTEST_CURRENT_TEST", None)
    environment["PYTHONPATH"] = os.fspath(_ROOT / "tests")
    environment["PYTHONPYCACHEPREFIX"] = os.fspath(
        tmp_path / "hypothesis-hostile-slots-pycache"
    )
    completed = subprocess.run(
        [sys.executable, "-B", "-c", script],
        cwd=_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=_SUBPROCESS_TIMEOUT_SECONDS,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    result = json.loads(completed.stdout.strip().splitlines()[-1])
    assert result == {
        "callback_count": 0,
        "exact_restoration": True,
        "hostile_slots_rejected": True,
    }


def test_hypothesis_constructive_predicate_classdict_cell_is_exact_preseal_cycle(
    tmp_path: Path,
) -> None:
    script = """
import json
from types import MappingProxyType

import support.mutation_toolchain as toolchain

if toolchain._RUNTIME_SOURCE_SENTINELS:
    raise SystemExit("runtime source sentinels were populated before the canary")

binding = (
    toolchain._EAGER_HYPOTHESIS_CONSTRUCTIVE_PREDICATE_CLASSDICT_CELL_BINDING
)
cell = binding.classdict_cell
classdict = binding.classdict
forged = dict(classdict)
forged["__classdictcell__"] = cell
rejection = None
cell.cell_contents = forged
try:
    try:
        toolchain._runtime_value_shape(binding.wrapper)
    except toolchain.MutationToolchainError as exc:
        rejection = str(exc)
finally:
    cell.cell_contents = classdict

expected_rejection = "reviewed source classdict cell contents changed"
if rejection != expected_rejection:
    raise SystemExit(
        f"pre-seal classdict-cell tamper was not rejected exactly: {rejection!r}"
    )
if toolchain._RUNTIME_SOURCE_SENTINELS:
    raise SystemExit("classdict-cell canary populated a runtime source sentinel")

source_namespace = type.__getattribute__(binding.source_class, "__dict__")
if type(source_namespace) is not MappingProxyType:
    raise SystemExit("source class namespace is not a fresh mapping proxy")
if cell.cell_contents is not classdict:
    raise SystemExit("classdict cell did not restore the exact source dictionary")
if classdict["__classdictcell__"] is not cell:
    raise SystemExit("source dictionary did not retain its exact cell backreference")
if source_namespace["__classdictcell__"] is not cell:
    raise SystemExit("source class did not retain its exact cell binding")
if source_namespace["__annotate_func__"] is not binding.wrapper:
    raise SystemExit("source class did not retain its exact annotate wrapper")

genuine = toolchain._runtime_value_shape(cell)
if genuine[:2] != [
    "reviewed-source-classdict-cell-v1",
    (
        "hypothesis.internal.filtering.ConstructivePredicate.__annotate_func__."
        "__closure__.original_annotate.__closure__.__classdict__."
        "__classdictcell__"
    ),
]:
    raise SystemExit("genuine classdict cell did not receive its narrow shape")

print(json.dumps({
    "category": genuine[0],
    "exact_restoration": True,
    "label": genuine[1],
    "preseal_tamper_rejected": True,
    "source_cycle_restored": True,
}, sort_keys=True, separators=(",", ":")))
"""
    environment = os.environ.copy()
    environment.pop("PYTEST_CURRENT_TEST", None)
    environment["PYTHONPATH"] = os.fspath(_ROOT / "tests")
    environment["PYTHONPYCACHEPREFIX"] = os.fspath(
        tmp_path / "hypothesis-classdict-cell-pycache"
    )
    completed = subprocess.run(
        [sys.executable, "-B", "-c", script],
        cwd=_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=_SUBPROCESS_TIMEOUT_SECONDS,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    result = json.loads(completed.stdout.strip().splitlines()[-1])
    assert result == {
        "category": "reviewed-source-classdict-cell-v1",
        "exact_restoration": True,
        "label": (
            "hypothesis.internal.filtering.ConstructivePredicate."
            "__annotate_func__.__closure__.original_annotate.__closure__."
            "__classdict__.__classdictcell__"
        ),
        "preseal_tamper_rejected": True,
        "source_cycle_restored": True,
    }


def test_iniconfig_parsed_line_classdict_cell_is_exact_repeated_and_never_executes_annotations(
) -> None:
    module, policy, record = _iniconfig_parsed_line_classdict_evidence()
    namespace = type.__getattribute__(record.source_class, "__dict__")
    expected_namespace_keys = (
        "__doc__",
        "__slots__",
        "_fields",
        "_field_defaults",
        "__new__",
        "_make",
        "__replace__",
        "_replace",
        "__repr__",
        "_asdict",
        "__getnewargs__",
        "__match_args__",
        "lineno",
        "section",
        "name",
        "value",
        "__module__",
        "__annotate_func__",
        "__firstlineno__",
        "__static_attributes__",
        "__classdictcell__",
        "__orig_bases__",
    )
    expected_hidden_keys = (
        "__module__",
        "__qualname__",
        "__firstlineno__",
        "__annotate_func__",
        "__static_attributes__",
        "__classdictcell__",
        "__orig_bases__",
    )
    expected_label = (
        "iniconfig._parse.ParsedLine.__annotate_func__.__closure__."
        "original_annotate.__closure__.__classdict__.__classdictcell__"
    )
    assert type(namespace) is MappingProxyType
    assert tuple(namespace) == expected_namespace_keys
    assert tuple(name for name, _value in record.classdict_items) == (
        expected_hidden_keys
    )
    assert record.label == expected_label
    assert record.wrapper_closure == (record.wrapper_cell,)
    assert record.original_closure == (record.classdict_cell,)
    assert record.wrapper_code.co_freevars == ("original_annotate",)
    assert record.original_code.co_freevars == ("__classdict__",)
    assert record.original_code.co_names == ("int", "str")
    assert record.wrapper.__defaults__ is None
    assert record.wrapper.__kwdefaults__ is None
    assert record.original.__defaults__ is None
    assert record.original.__kwdefaults__ is None
    assert record.wrapper.__globals__ is vars(record.typing_module)
    assert record.original.__globals__ is vars(module)
    assert record.wrapper.__builtins__ is vars(builtins)
    assert record.original.__builtins__ is vars(builtins)
    assert "__annotations__" not in namespace
    assert "__annotations_cache__" not in namespace
    assert "__annotations__" not in record.classdict
    assert "__annotations_cache__" not in record.classdict
    _assert_iniconfig_parsed_line_graph_is_exact(record)

    calls: list[CodeType] = []

    def profiler(frame: object, event: str, _arg: object) -> None:
        if event == "call" and frame.f_code in {
            record.wrapper_code,
            record.original_code,
        }:
            calls.append(frame.f_code)

    previous_profile = sys.getprofile()
    first_shape: object = None
    second_shape: object = None
    try:
        sys.setprofile(profiler)
        first_shape = _iniconfig_parsed_line_classdict_shape(record)
        second_shape = _iniconfig_parsed_line_classdict_shape(record)
        member_shape = mutation_toolchain._runtime_source_class_member_shape(
            module,
            record.source_class,
            path="ParsedLine",
            name="__annotate_func__",
            member=record.wrapper,
        )
        mutation_toolchain._verify_runtime_source_bindings(module, policy=policy)
        mutation_toolchain._verify_runtime_source_bindings(module, policy=policy)
    finally:
        sys.setprofile(previous_profile)

    assert first_shape == second_shape
    assert first_shape[:2] == ["reviewed-source-classdict-cell-v1", expected_label]
    assert member_shape[0] == "function"
    assert calls == []
    assert sys.getprofile() is previous_profile
    assert "__annotations__" not in namespace
    assert "__annotations_cache__" not in namespace
    assert "__annotations__" not in record.classdict
    assert "__annotations_cache__" not in record.classdict
    _assert_iniconfig_parsed_line_graph_is_exact(record)


@pytest.mark.parametrize(
    "attack_kind",
    (
        "cell_contents_clone",
        "cell_backref_clone",
        "classdict_reordered",
        "classdict_extra",
        "classdict_annotate_clone",
        "exposed_wrapper_clone",
        "exposed_cell_clone",
        "module_class_replacement",
        "wrapper_code_clone",
        "original_code_clone",
        "wrapper_closure_clone",
        "original_closure_clone",
        "registry_clone",
        "record_clone",
        "record_field_mutation",
    ),
)
def test_iniconfig_parsed_line_classdict_rejects_adversarial_identity_attacks_without_execution(
    attack_kind: str,
) -> None:
    module, _policy, record = _iniconfig_parsed_line_classdict_evidence()
    original_items = tuple(dict.items(record.classdict))
    def restore() -> None:
        return None

    if attack_kind == "cell_contents_clone":
        clone = dict(record.classdict)
        record.cell_contents_descriptor.__set__(record.classdict_cell, clone)

        def restore_cell_contents() -> None:
            record.cell_contents_descriptor.__set__(
                record.classdict_cell,
                record.classdict,
            )

        restore = restore_cell_contents
        assert record.classdict_cell.cell_contents is clone
    elif attack_kind == "cell_backref_clone":
        clone = CellType(record.classdict)
        dict.__setitem__(record.classdict, "__classdictcell__", clone)
        def restore() -> None:
            dict.__setitem__(
                record.classdict,
                "__classdictcell__",
                record.classdict_cell,
            )
        assert dict.__getitem__(record.classdict, "__classdictcell__") is clone
    elif attack_kind == "classdict_reordered":
        dict.clear(record.classdict)
        for name, value in reversed(original_items):
            dict.__setitem__(record.classdict, name, value)

        def restore_items() -> None:
            dict.clear(record.classdict)
            for name, value in original_items:
                dict.__setitem__(record.classdict, name, value)

        restore = restore_items
        assert tuple(dict.items(record.classdict)) != original_items
    elif attack_kind == "classdict_extra":
        forged = object()
        dict.__setitem__(record.classdict, "phase11_forged", forged)
        def restore() -> None:
            dict.__delitem__(record.classdict, "phase11_forged")
        assert dict.__getitem__(record.classdict, "phase11_forged") is forged
    elif attack_kind == "classdict_annotate_clone":
        clone = _exact_function_clone_with_closure(
            record.original,
            record.original_closure,
        )
        dict.__setitem__(record.classdict, "__annotate_func__", clone)
        def restore() -> None:
            dict.__setitem__(
                record.classdict,
                "__annotate_func__",
                record.original,
            )
        assert dict.__getitem__(record.classdict, "__annotate_func__") is clone
    elif attack_kind == "exposed_wrapper_clone":
        clone = _exact_function_clone_with_closure(
            record.wrapper,
            record.wrapper_closure,
        )
        type.__setattr__(record.source_class, "__annotate_func__", clone)
        def restore() -> None:
            type.__setattr__(
                record.source_class,
                "__annotate_func__",
                record.wrapper,
            )
        assert vars(record.source_class)["__annotate_func__"] is clone
    elif attack_kind == "exposed_cell_clone":
        clone = CellType(record.classdict)
        type.__setattr__(record.source_class, "__classdictcell__", clone)
        def restore() -> None:
            type.__setattr__(
                record.source_class,
                "__classdictcell__",
                record.classdict_cell,
            )
        assert vars(record.source_class)["__classdictcell__"] is clone
    elif attack_kind == "module_class_replacement":
        clone = type(
            "ParsedLine",
            (),
            {"__module__": record.source_module_name},
        )
        dict.__setitem__(vars(module), "ParsedLine", clone)
        def restore() -> None:
            dict.__setitem__(
                vars(module),
                "ParsedLine",
                record.source_class,
            )
        assert vars(module)["ParsedLine"] is clone
    elif attack_kind in {"wrapper_code_clone", "original_code_clone"}:
        function = (
            record.wrapper
            if attack_kind == "wrapper_code_clone"
            else record.original
        )
        original_code = object.__getattribute__(function, "__code__")
        clone = original_code.replace()
        function.__code__ = clone
        def restore() -> None:
            setattr(function, "__code__", original_code)
        assert function.__code__ is clone
    elif attack_kind == "wrapper_closure_clone":
        clone_cell = CellType(record.original)
        clone = _exact_function_clone_with_closure(record.wrapper, (clone_cell,))
        type.__setattr__(record.source_class, "__annotate_func__", clone)
        def restore() -> None:
            type.__setattr__(
                record.source_class,
                "__annotate_func__",
                record.wrapper,
            )
        assert clone.__closure__ == (clone_cell,)
    elif attack_kind == "original_closure_clone":
        clone_cell = CellType(record.classdict)
        clone = _exact_function_clone_with_closure(record.original, (clone_cell,))
        record.cell_contents_descriptor.__set__(record.wrapper_cell, clone)
        dict.__setitem__(record.classdict, "__annotate_func__", clone)

        def restore_original_closure() -> None:
            record.cell_contents_descriptor.__set__(
                record.wrapper_cell,
                record.original,
            )
            dict.__setitem__(
                record.classdict,
                "__annotate_func__",
                record.original,
            )

        restore = restore_original_closure
        assert record.wrapper_cell.cell_contents is clone
        assert dict.__getitem__(record.classdict, "__annotate_func__") is clone
    elif attack_kind == "registry_clone":
        original_registry = (
            mutation_toolchain._EAGER_REVIEWED_SOURCE_CLASSDICT_CELL_BINDINGS
        )
        clone = tuple([*original_registry])
        mutation_toolchain._EAGER_REVIEWED_SOURCE_CLASSDICT_CELL_BINDINGS = clone
        def restore() -> None:
            setattr(
                mutation_toolchain,
                "_EAGER_REVIEWED_SOURCE_CLASSDICT_CELL_BINDINGS",
                original_registry,
            )
        assert clone is not original_registry
    elif attack_kind == "record_clone":
        clone = replace(record)
        mutation_toolchain._EAGER_INICONFIG_PARSED_LINE_CLASSDICT_CELL_BINDING = clone
        def restore() -> None:
            setattr(
                mutation_toolchain,
                "_EAGER_INICONFIG_PARSED_LINE_CLASSDICT_CELL_BINDING",
                record,
            )
        assert clone is not record
    elif attack_kind == "record_field_mutation":
        original_label = record.label
        object.__setattr__(record, "label", f"{original_label}.forged")
        def restore() -> None:
            object.__setattr__(record, "label", original_label)
        assert record.label != original_label
    else:
        raise AssertionError(f"unknown attack kind: {attack_kind}")

    try:
        _assert_iniconfig_guard_rejects_without_annotation_execution(
            record,
            lambda: _iniconfig_parsed_line_classdict_shape(record),
        )
    finally:
        restore()

    _assert_iniconfig_parsed_line_graph_is_exact(record)
    assert tuple(dict.items(record.classdict)) == original_items
    first_shape = _iniconfig_parsed_line_classdict_shape(record)
    assert _iniconfig_parsed_line_classdict_shape(record) == first_shape


def test_unrelated_namedtuple_classdict_cell_remains_unregistered_without_annotation_execution(
) -> None:
    _module, _policy, record = _iniconfig_parsed_line_classdict_evidence()
    owner, wrapper, original, unregistered_cell = (
        _unregistered_namedtuple_classdict_evidence()
    )
    namespace = type.__getattribute__(owner, "__dict__")
    assert unregistered_cell is not record.classdict_cell
    assert "__annotations__" not in namespace
    assert "__annotations_cache__" not in namespace

    _assert_iniconfig_guard_rejects_without_annotation_execution(
        record,
        lambda: mutation_toolchain._reviewed_source_classdict_cell_shape(
            unregistered_cell,
            depth=0,
            context=mutation_toolchain._RuntimeSnapshotContext(active={}),
        ),
        additional_codes=(
            object.__getattribute__(wrapper, "__code__"),
            object.__getattribute__(original, "__code__"),
        ),
    )
    assert "__annotations__" not in namespace
    assert "__annotations_cache__" not in namespace


def test_runtime_value_shape_rejects_classdict_shape_helper_replacement_before_execution(
) -> None:
    _module, _policy, record = _iniconfig_parsed_line_classdict_evidence()
    owner, wrapper, original, unregistered_cell = (
        _unregistered_namedtuple_classdict_evidence()
    )
    namespace = type.__getattribute__(owner, "__dict__")
    assert unregistered_cell is not record.classdict_cell
    assert "__annotations__" not in namespace
    assert "__annotations_cache__" not in namespace

    original_shape_helper = (
        mutation_toolchain._reviewed_source_classdict_cell_shape
    )
    forged_calls = {"count": 0}
    annotation_calls: list[CodeType] = []
    annotation_codes = (
        object.__getattribute__(wrapper, "__code__"),
        object.__getattribute__(original, "__code__"),
    )

    def forged_shape_helper(
        _value: object,
        *,
        depth: int,
        context: object,
    ) -> object:
        forged_calls["count"] += 1
        return ["forged-cell", depth, context]

    def profiler(frame: object, event: str, _arg: object) -> None:
        if event == "call" and frame.f_code in annotation_codes:
            annotation_calls.append(frame.f_code)

    previous_profile = sys.getprofile()
    caught: BaseException | None = None
    try:
        mutation_toolchain._reviewed_source_classdict_cell_shape = (
            forged_shape_helper
        )
        sys.setprofile(profiler)
        try:
            mutation_toolchain._runtime_value_shape(unregistered_cell)
        except BaseException as exc:
            caught = exc
    finally:
        sys.setprofile(previous_profile)
        mutation_toolchain._reviewed_source_classdict_cell_shape = (
            original_shape_helper
        )

    assert isinstance(caught, MutationToolchainError)
    assert forged_calls == {"count": 0}
    assert annotation_calls == []
    assert sys.getprofile() is previous_profile
    assert (
        mutation_toolchain._reviewed_source_classdict_cell_shape
        is original_shape_helper
    )
    assert "__annotations__" not in namespace
    assert "__annotations_cache__" not in namespace

    first_shape = mutation_toolchain._runtime_value_shape(record.classdict_cell)
    second_shape = mutation_toolchain._runtime_value_shape(record.classdict_cell)
    assert first_shape == second_shape
    assert first_shape[:2] == ["reviewed-source-classdict-cell-v1", record.label]
    _assert_iniconfig_parsed_line_graph_is_exact(record)


def test_iniconfig_parsed_line_classdict_rejects_hostile_sys_modules_key_without_callbacks(
) -> None:
    module, _policy, record = _iniconfig_parsed_line_classdict_evidence()
    original_items = tuple(dict.items(sys.modules))
    callbacks: list[str] = []
    armed = {"value": False}

    class HostileModuleKey(str):
        def __hash__(self) -> int:
            if armed["value"]:
                callbacks.append("hash")
            return str.__hash__(self)

        def __eq__(self, other: object) -> bool:
            if armed["value"]:
                callbacks.append("eq")
            return str.__eq__(self, other)

        def __repr__(self) -> str:
            if armed["value"]:
                callbacks.append("repr")
            return "<hostile-iniconfig-module-key>"

    hostile_key = HostileModuleKey("iniconfig._parse")
    replaced = False
    hostile_items: list[tuple[object, object]] = []
    for name, value in original_items:
        if type(name) is str and name == "iniconfig._parse":
            if replaced or value is not module:
                raise AssertionError("iniconfig._parse module route is not exact")
            hostile_items.append((hostile_key, value))
            replaced = True
        else:
            hostile_items.append((name, value))
    if not replaced:
        raise AssertionError("iniconfig._parse module route is missing")

    caught: BaseException | None = None
    dict.clear(sys.modules)
    for name, value in hostile_items:
        dict.__setitem__(sys.modules, name, value)
    callbacks.clear()
    armed["value"] = True
    try:
        try:
            _iniconfig_parsed_line_classdict_shape(record)
        except BaseException as exc:
            caught = exc
    finally:
        armed["value"] = False
        dict.clear(sys.modules)
        for name, value in original_items:
            dict.__setitem__(sys.modules, name, value)

    restored_items = tuple(dict.items(sys.modules))
    assert isinstance(caught, MutationToolchainError)
    assert callbacks == []
    assert len(restored_items) == len(original_items)
    assert all(
        current_name is expected_name and current_value is expected_value
        for (current_name, current_value), (expected_name, expected_value) in zip(
            restored_items,
            original_items,
            strict=True,
        )
    )
    first_shape = _iniconfig_parsed_line_classdict_shape(record)
    second_shape = _iniconfig_parsed_line_classdict_shape(record)
    assert first_shape == second_shape
    assert first_shape[:2] == ["reviewed-source-classdict-cell-v1", record.label]


def test_runtime_forward_ref_snapshot_binds_slots_without_evaluation() -> None:
    calls: list[str] = []

    def forbidden() -> object:
        calls.append("evaluated")
        return object()

    reference = annotationlib.ForwardRef("forbidden()")
    reference.__globals__ = {"forbidden": forbidden}
    baseline = mutation_toolchain._runtime_value_shape(reference)

    assert baseline[0] == "annotationlib.ForwardRef"
    assert calls == []

    reference.__arg__ = "changed()"
    assert mutation_toolchain._runtime_value_shape(reference) != baseline
    assert calls == []


def test_runtime_forward_ref_snapshot_rejects_descriptor_tamper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reference = annotationlib.ForwardRef("Target")
    monkeypatch.setattr(annotationlib.ForwardRef, "__arg__", "forged")

    with pytest.raises(
        MutationToolchainError,
        match="ForwardRef slot descriptor changed: __arg__",
    ):
        mutation_toolchain._runtime_value_shape(reference)


def test_runtime_forward_ref_snapshot_fails_closed_without_callbacks() -> None:
    calls: list[str] = []

    class Hostile:
        def __eq__(self, other: object) -> bool:
            calls.append("eq")
            return self is other

        def __hash__(self) -> int:
            calls.append("hash")
            return object.__hash__(self)

        def __repr__(self) -> str:
            calls.append("repr")
            return "hostile"

    reference = annotationlib.ForwardRef("Target", owner=Hostile())
    with pytest.raises(MutationToolchainError, match="unsupported opaque payload"):
        mutation_toolchain._runtime_value_shape(reference)

    assert calls == []


def test_runtime_partial_snapshot_binds_nested_args_and_keywords() -> None:
    positional = {"position": 1}
    keyword = {"keyword": 1}
    value = functools.partial(pow, positional, option=keyword)
    baseline = mutation_toolchain._runtime_value_shape(value)

    positional["position"] = 2
    assert mutation_toolchain._runtime_value_shape(value) != baseline

    positional["position"] = 1
    keyword["keyword"] = 2
    assert mutation_toolchain._runtime_value_shape(value) != baseline


@pytest.mark.parametrize(
    "descriptor_factory",
    [property, staticmethod, classmethod, functools.cached_property],
)
def test_runtime_descriptor_snapshot_binds_nested_function_payload(
    descriptor_factory: object,
) -> None:
    def target(self: object) -> int:
        return 1

    target.__annotate__ = None
    target.__annotations__ = {"return": int}
    target.semantic_state = {"value": 1}
    descriptor = descriptor_factory(target)
    baseline = mutation_toolchain._runtime_value_shape(descriptor)

    target.semantic_state["value"] = 2

    assert mutation_toolchain._runtime_value_shape(descriptor) != baseline


def test_runtime_class_snapshot_binds_member_callable_state() -> None:
    class Probe:
        def method(self) -> int:
            return 1

    Probe.method.__annotate__ = None
    Probe.method.__annotations__ = {"return": int}
    baseline = mutation_toolchain._runtime_value_shape(Probe)

    Probe.method.__annotations__["return"] = str

    assert mutation_toolchain._runtime_value_shape(Probe) != baseline


def test_runtime_method_snapshot_binds_function_and_class_self() -> None:
    class Provider:
        @classmethod
        def method(cls) -> int:
            return 1

    bound = Provider.method
    assert type(bound) is MethodType
    baseline = mutation_toolchain._runtime_value_shape(bound)
    assert baseline[0] == "method"
    assert mutation_toolchain._runtime_value_shape(PathFinder.find_spec)[0] == "method"

    bound.__func__.semantic_state = {"value": 1}
    changed = mutation_toolchain._runtime_value_shape(bound)
    assert changed != baseline


def test_runtime_method_snapshot_fails_closed_without_instance_hooks() -> None:
    hook_calls: list[str] = []

    class Hostile:
        def __eq__(self, other: object) -> bool:
            hook_calls.append("eq")
            return self is other

        def __hash__(self) -> int:
            hook_calls.append("hash")
            return object.__hash__(self)

        def __repr__(self) -> str:
            hook_calls.append("repr")
            return "hostile"

    def method(self: object) -> int:
        return 1

    bound = MethodType(method, Hostile())
    with pytest.raises(MutationToolchainError, match="unsupported opaque payload"):
        mutation_toolchain._runtime_value_shape(bound)
    assert hook_calls == []


def test_runtime_tuplegetter_snapshot_binds_provider_without_attacker_callbacks() -> None:
    collections_module = import_module("collections")
    probe_type = collections_module.namedtuple("TupleGetterProbe", "value")
    descriptor = vars(probe_type)["value"]
    assert mutation_toolchain._runtime_value_shape(descriptor) == [
        "collections._tuplegetter",
        "0",
        "Alias for field number 0",
    ]
    hook_calls: list[str] = []

    class HostileMeta(type):
        def __getattribute__(cls, name: str) -> object:
            hook_calls.append(f"get:{name}")
            return type.__getattribute__(cls, name)

        def __eq__(cls, other: object) -> bool:
            hook_calls.append("eq")
            return cls is other

        def __hash__(cls) -> int:
            hook_calls.append("hash")
            return type.__hash__(cls)

        def __repr__(cls) -> str:
            hook_calls.append("repr")
            return "hostile-tuplegetter"

    class HostileTupleGetter(metaclass=HostileMeta):
        pass

    module_namespace = vars(collections_module)
    original = dict.__getitem__(module_namespace, "_tuplegetter")
    hook_calls.clear()
    dict.__setitem__(module_namespace, "_tuplegetter", HostileTupleGetter)
    try:
        assert hook_calls == []
        with pytest.raises(
            MutationToolchainError,
            match=r"collections\._tuplegetter provider changed",
        ):
            mutation_toolchain._runtime_value_shape(descriptor)
    finally:
        dict.__setitem__(module_namespace, "_tuplegetter", original)

    assert hook_calls == []


def test_runtime_pytest_fixture_proxy_binds_containment_without_callbacks() -> None:
    legacy_module = import_module("_pytest.legacypath")
    owner = vars(legacy_module)["LegacyTestdirPlugin"]
    container = vars(owner)["testdir"]
    assert type(container) is staticmethod
    fixture_proxy = container.__func__
    assert type(fixture_proxy) is (
        mutation_toolchain._EAGER_FIXTURE_FUNCTION_DEFINITION_TYPE
    )
    baseline = mutation_toolchain._runtime_value_shape(fixture_proxy)
    assert baseline[:4] == [
        "pytest-fixture-function-definition",
        "testdir",
        "_pytest.legacypath",
        "LegacyTestdirPlugin.testdir",
    ]
    hook_calls: list[str] = []

    class Hostile:
        def __getattribute__(self, name: str) -> object:
            hook_calls.append(f"get:{name}")
            return object.__getattribute__(self, name)

        def __eq__(self, other: object) -> bool:
            hook_calls.append("eq")
            return self is other

        def __hash__(self) -> int:
            hook_calls.append("hash")
            return object.__hash__(self)

        def __repr__(self) -> str:
            hook_calls.append("repr")
            return "hostile-fixture-marker"

    hostile = Hostile()
    proxy_namespace = object.__getattribute__(fixture_proxy, "__dict__")
    original_marker = dict.__getitem__(
        proxy_namespace,
        "_fixture_function_marker",
    )
    hook_calls.clear()
    dict.__setitem__(proxy_namespace, "_fixture_function_marker", hostile)
    try:
        with pytest.raises(
            MutationToolchainError,
            match="pytest fixture definition semantic state changed",
        ):
            mutation_toolchain._runtime_value_shape(fixture_proxy)
    finally:
        dict.__setitem__(
            proxy_namespace,
            "_fixture_function_marker",
            original_marker,
        )

    assert hook_calls == []


def test_runtime_snapshot_fails_closed_without_user_equality() -> None:
    equality_calls: list[object] = []

    class Opaque:
        def __eq__(self, other: object) -> bool:
            equality_calls.append(other)
            return True

    with pytest.raises(
        MutationToolchainError,
        match="unsupported opaque payload",
    ):
        mutation_toolchain._runtime_value_shape(Opaque())

    assert equality_calls == []


def test_runtime_snapshot_does_not_invoke_custom_metaclass_hooks() -> None:
    hook_calls: list[str] = []

    class HostileMeta(type):
        def __getattribute__(cls, name: str) -> object:
            if name in {"__module__", "__qualname__"}:
                hook_calls.append(f"get:{name}")
            return type.__getattribute__(cls, name)

        def __hash__(cls) -> int:
            hook_calls.append("hash")
            return type.__hash__(cls)

        def __eq__(cls, other: object) -> bool:
            hook_calls.append("eq")
            return cls is other

    class Opaque(metaclass=HostileMeta):
        pass

    with pytest.raises(MutationToolchainError, match="unsupported opaque payload"):
        mutation_toolchain._runtime_value_shape(Opaque())

    assert hook_calls == []


def test_source_class_namespace_snapshot_bypasses_metaclass_hooks() -> None:
    hook_calls: list[str] = []

    class HostileMeta(type):
        def __getattribute__(cls, name: str) -> object:
            if name in {"__dict__", "__module__", "__qualname__"}:
                hook_calls.append(f"get:{name}")
            return type.__getattribute__(cls, name)

        def __hash__(cls) -> int:
            hook_calls.append("hash")
            return type.__hash__(cls)

        def __eq__(cls, other: object) -> bool:
            hook_calls.append("eq")
            return cls is other

    class Probe(metaclass=HostileMeta):
        def method(self) -> int:
            return 1

    namespace = type.__getattribute__(Probe, "__dict__")
    qualname = type.__getattribute__(Probe, "__qualname__")
    method = namespace["method"]
    hook_calls.clear()

    shape = mutation_toolchain._runtime_source_class_member_shape(
        sys.modules[__name__],
        Probe,
        path=qualname,
        name="method",
        member=method,
    )

    assert shape[0] == "function"
    assert hook_calls == []


def test_runtime_signature_snapshot_never_formats_user_payloads() -> None:
    repr_calls: list[str] = []

    class Hostile:
        def __repr__(self) -> str:
            repr_calls.append("repr")
            return "hostile"

    payload = Hostile()
    parameter = inspect.Parameter(
        "value",
        inspect.Parameter.POSITIONAL_ONLY,
        annotation=payload,
    )
    signature = inspect.Signature(
        (parameter,),
        return_annotation=payload,
    )
    repr_calls.clear()

    with pytest.raises(MutationToolchainError, match="unsupported opaque payload"):
        mutation_toolchain._runtime_value_shape(signature)

    assert repr_calls == []


def test_direct_forwarder_reference_identity_is_uncached_and_isolated() -> None:
    function = mutation_toolchain._direct_forwarder_reference_identity
    assert type(function) is FunctionType
    arguments = (("left",), ("right",), ("named",), "items", "options")

    baseline = function(*arguments)
    second = function(*arguments)
    assert second == baseline
    assert second is not baseline

    baseline["consts"] = ["tampered"]
    assert function(*arguments) == second
    assert _normalize_eager_lru_wrappers()[
        "all_normalized_lru_wrappers_empty"
    ] is True


def test_runtime_dataclass_params_and_typing_alias_shapes_are_semantic() -> None:
    @mutation_toolchain.dataclass
    class Probe:
        value: typing.ClassVar[int] = 1

    params = Probe.__dataclass_params__
    params_baseline = mutation_toolchain._runtime_value_shape(params)
    original_init = params.init
    params.init = not original_init
    try:
        assert mutation_toolchain._runtime_value_shape(params) != params_baseline
    finally:
        params.init = original_init

    alias = typing.ClassVar[int]
    alias_baseline = mutation_toolchain._runtime_value_shape(alias)
    original_name = vars(alias)["_name"]
    vars(alias)["_name"] = "Phase11Tamper"
    try:
        assert mutation_toolchain._runtime_value_shape(alias) != alias_baseline
    finally:
        vars(alias)["_name"] = original_name


def test_runtime_snapshot_has_deterministic_cycle_depth_and_size_bounds() -> None:
    cyclic: list[object] = []
    cyclic.append(cyclic)
    assert mutation_toolchain._runtime_value_shape(cyclic) == [
        "list",
        [["cycle", 0]],
    ]

    too_deep: object = None
    for _index in range(14):
        too_deep = [too_deep]
    with pytest.raises(MutationToolchainError, match="bounded depth"):
        mutation_toolchain._runtime_value_shape(too_deep)

    with pytest.raises(MutationToolchainError, match="bounded container size"):
        mutation_toolchain._runtime_value_shape([None] * 4097)


def test_eager_lru_normalizer_clears_every_exact_wrapper_and_attests_names() -> None:
    fnmatch_module = import_module("fnmatch")
    fnmatch_module._compile_pattern("*.py")
    assert fnmatch_module._compile_pattern.cache_info().currsize > 0

    receipt = _normalize_eager_lru_wrappers()
    names = receipt["normalized_lru_wrapper_names"]
    assert type(names) is list
    assert names == sorted(set(names))
    assert names
    assert receipt == {
        "normalized_lru_wrapper_names": names,
        "normalized_lru_wrapper_count": len(names),
        "normalized_lru_wrapper_sha256": mutation_toolchain._sha256_bytes(
            mutation_toolchain._compact_canonical_json_bytes(names)
        ),
        "all_normalized_lru_wrappers_empty": True,
    }
    for binding in mutation_toolchain._EAGER_LRU_WRAPPER_BINDINGS:
        info = mutation_toolchain._EAGER_LRU_CACHE_INFO_DESCRIPTOR(
            binding.value
        )
        assert tuple.__getitem__(info, 0) == 0
        assert tuple.__getitem__(info, 1) == 0
        assert tuple.__getitem__(info, 3) == 0


def test_lru_runtime_context_is_required_for_every_transition() -> None:
    with pytest.raises(TypeError):
        mutation_toolchain.normalize_eager_lru_wrappers()
    with pytest.raises(TypeError):
        mutation_toolchain._attest_eager_lru_wrappers_empty()
    with pytest.raises(TypeError):
        loaded_test_toolchain_attestation({})
    with pytest.raises(TypeError):
        project_test_toolchain_identity(Path.cwd())


@pytest.mark.parametrize(
    ("version", "expected"),
    (
        ((3, 10), (False, False)),
        ((3, 11), (False, False)),
        ((3, 12), (False, True)),
        ((3, 13), (False, True)),
        ((3, 14), (True, True)),
    ),
)
def test_lru_cache_parameters_metadata_policy_covers_supported_python(
    version: tuple[int, int],
    expected: tuple[bool, bool],
) -> None:
    assert (
        mutation_toolchain._pytest_cache_parameters_version_policy(version)
        == expected
    )


def test_lru_cache_parameters_policy_rebind_fails_before_callback() -> None:
    calls: list[object] = []
    original = mutation_toolchain._pytest_cache_parameters_version_policy

    def hostile_policy(version: object) -> tuple[bool, bool]:
        calls.append(version)
        return True, True

    mutation_toolchain._pytest_cache_parameters_version_policy = hostile_policy
    try:
        with pytest.raises(
            MutationToolchainError,
            match="metadata policy binding changed",
        ):
            _normalize_eager_lru_wrappers()
        assert calls == []
    finally:
        mutation_toolchain._pytest_cache_parameters_version_policy = original
    _normalize_eager_lru_wrappers()


def test_lru_context_mode_rejects_hostile_equality_without_callbacks() -> None:
    calls: list[str] = []

    class HostileMode:
        def __eq__(self, _other: object) -> bool:
            calls.append("eq")
            return True

        def __ne__(self, _other: object) -> bool:
            calls.append("ne")
            return False

    context = _active_lru_runtime_context()
    original = object.__getattribute__(context, "mode")
    object.__setattr__(context, "mode", HostileMode())
    try:
        with pytest.raises(
            MutationToolchainError,
            match="context mode is not exact",
        ):
            _normalize_eager_lru_wrappers()
        assert calls == []
    finally:
        object.__setattr__(context, "mode", original)
    _normalize_eager_lru_wrappers()


def test_lru_context_slot_rebind_fails_before_descriptor_callback() -> None:
    calls: list[str] = []
    context_type = mutation_toolchain._LruRuntimeContext
    namespace = type.__getattribute__(context_type, "__dict__")
    original = namespace["mode"]

    def hostile_mode(_context: object) -> str:
        calls.append("mode")
        return "active-pytest"

    type.__setattr__(context_type, "mode", property(hostile_mode))
    try:
        with pytest.raises(
            MutationToolchainError,
            match="context provider changed",
        ):
            _normalize_eager_lru_wrappers()
        assert calls == []
    finally:
        type.__setattr__(context_type, "mode", original)
    _normalize_eager_lru_wrappers()


def test_lru_context_class_rebind_fails_before_descriptor_callback() -> None:
    calls: list[str] = []
    original = mutation_toolchain._LruRuntimeContext

    class HostileContext:
        @property
        def mode(self) -> str:
            calls.append("mode")
            return "active-pytest"

    mutation_toolchain._LruRuntimeContext = HostileContext
    try:
        with pytest.raises(
            MutationToolchainError,
            match="context provider changed",
        ):
            _normalize_eager_lru_wrappers()
        assert calls == []
    finally:
        mutation_toolchain._LruRuntimeContext = original
    _normalize_eager_lru_wrappers()


def test_lru_context_init_rebind_fails_before_constructor_callback(
    pytestconfig: pytest.Config,
) -> None:
    calls: list[str] = []
    context_type = mutation_toolchain._LruRuntimeContext
    namespace = type.__getattribute__(context_type, "__dict__")
    original = namespace["__init__"]

    def hostile_init(_context: object, **_fields: object) -> None:
        calls.append("init")

    type.__setattr__(context_type, "__init__", hostile_init)
    try:
        with pytest.raises(
            MutationToolchainError,
            match="context provider changed",
        ):
            mutation_toolchain.capture_active_pytest_lru_runtime_context(
                pytestconfig,
                **_current_pytest_lru_identity(pytestconfig),
            )
        assert calls == []
    finally:
        type.__setattr__(context_type, "__init__", original)
    _normalize_eager_lru_wrappers()


def test_lru_context_new_rebind_fails_before_constructor_callback(
    pytestconfig: pytest.Config,
) -> None:
    calls: list[str] = []
    context_type = mutation_toolchain._LruRuntimeContext

    def hostile_new(context_class: type[object], *_args: object, **_kwargs: object):
        calls.append("new")
        return object.__new__(context_class)

    type.__setattr__(context_type, "__new__", staticmethod(hostile_new))
    try:
        with pytest.raises(
            MutationToolchainError,
            match="context provider changed",
        ):
            mutation_toolchain.capture_active_pytest_lru_runtime_context(
                pytestconfig,
                **_current_pytest_lru_identity(pytestconfig),
            )
        assert calls == []
    finally:
        type.__delattr__(context_type, "__new__")
    _normalize_eager_lru_wrappers()


def test_active_pytest_plugin_manager_lru_normalizes_and_attests() -> None:
    context = _active_lru_runtime_context()
    wrapper = object.__getattribute__(context, "get_directory_wrapper")
    wrapper(Path(__file__).resolve(strict=True))
    before = mutation_toolchain._exact_lru_cache_info(
        wrapper,
        label=mutation_toolchain._PYTEST_PLUGIN_MANAGER_LRU_FAMILY_NAME,
    )
    assert before[2] == 256 and before[3] > 0

    receipt = _normalize_eager_lru_wrappers()
    assert receipt["normalized_lru_wrapper_count"] == 47
    assert receipt["normalized_lru_wrapper_sha256"] == (
        "c7d5b01efce5222f262f26da4341281cf5a50ab92af5b45d28242c2686d56ded"
    )
    assert (
        mutation_toolchain._PYTEST_PLUGIN_MANAGER_LRU_FAMILY_NAME
        in receipt["normalized_lru_wrapper_names"]
    )
    assert mutation_toolchain._exact_lru_cache_info(
        wrapper,
        label=mutation_toolchain._PYTEST_PLUGIN_MANAGER_LRU_FAMILY_NAME,
    ) == (0, 0, 256, 0)
    assert _attest_eager_lru_wrappers_empty() == receipt


def test_active_pytest_plugin_manager_attester_is_non_mutating() -> None:
    context = _active_lru_runtime_context()
    wrapper = object.__getattribute__(context, "get_directory_wrapper")
    _normalize_eager_lru_wrappers()
    wrapper(Path(__file__).resolve(strict=True))
    before = mutation_toolchain._exact_lru_cache_info(
        wrapper,
        label=mutation_toolchain._PYTEST_PLUGIN_MANAGER_LRU_FAMILY_NAME,
    )
    try:
        with pytest.raises(
            MutationToolchainError,
            match="active pytest plugin-manager LRU wrapper is not empty",
        ):
            _attest_eager_lru_wrappers_empty()
        assert mutation_toolchain._exact_lru_cache_info(
            wrapper,
            label=mutation_toolchain._PYTEST_PLUGIN_MANAGER_LRU_FAMILY_NAME,
        ) == before
    finally:
        _normalize_eager_lru_wrappers()


def test_active_pytest_plugin_manager_rejects_owner_and_backref_tamper() -> None:
    context = _active_lru_runtime_context()
    config = object.__getattribute__(context, "config")
    manager = object.__getattribute__(context, "plugin_manager")
    config_namespace = object.__getattribute__(config, "__dict__")
    manager_namespace = object.__getattribute__(manager, "__dict__")
    name_to_plugin = dict.get(manager_namespace, "_name2plugin")
    assert type(name_to_plugin) is dict
    cases = (
        (config_namespace, "pluginmanager", manager, object()),
        (config_namespace, "_configured", True, False),
        (manager_namespace, "_configured", True, False),
        (name_to_plugin, "pytestconfig", config, object()),
    )
    for namespace, key, expected, replacement in cases:
        assert dict.get(namespace, key) is expected
        dict.__setitem__(namespace, key, replacement)
        try:
            with pytest.raises(MutationToolchainError):
                _normalize_eager_lru_wrappers()
        finally:
            dict.__setitem__(namespace, key, expected)
    _normalize_eager_lru_wrappers()


def test_pytest_pdb_lifecycle_uses_exact_active_runtime_references() -> None:
    context = _active_lru_runtime_context()
    references = mutation_toolchain._active_pytest_runtime_context_references(
        context
    )
    assert references is not None
    mode, config, manager = references
    assert mode == "active-pytest"
    module = import_module("_pytest.debugging")
    owner = vars(module)["pytestPDB"]
    namespace = vars(owner)
    assert namespace["_config"] is config
    assert namespace["_pluginmanager"] is manager

    assert mutation_toolchain._runtime_source_class_member_shape(
        module,
        owner,
        path="pytestPDB",
        name="_config",
        member=config,
        lru_runtime_context=context,
    ) == ["pytest-runtime-reference", "active-pytest", "Config"]
    assert mutation_toolchain._runtime_source_class_member_shape(
        module,
        owner,
        path="pytestPDB",
        name="_pluginmanager",
        member=manager,
        lru_runtime_context=context,
    ) == ["pytest-runtime-reference", "active-pytest", "PytestPluginManager"]


def test_pytest_pdb_lifecycle_rejects_missing_or_standalone_context() -> None:
    module = import_module("_pytest.debugging")
    owner = vars(module)["pytestPDB"]
    manager = vars(owner)["_pluginmanager"]
    with pytest.raises(
        MutationToolchainError,
        match="requires an exact pytest lifecycle context",
    ):
        mutation_toolchain._runtime_source_class_member_shape(
            module,
            owner,
            path="pytestPDB",
            name="_pluginmanager",
            member=manager,
        )

    standalone = mutation_toolchain.standalone_lru_runtime_context()
    references = mutation_toolchain._active_pytest_runtime_context_references(
        standalone
    )
    assert references == ("standalone-parent", None, None)
    with pytest.raises(MutationToolchainError, match="lifecycle ownership changed"):
        mutation_toolchain._runtime_source_class_member_shape(
            module,
            owner,
            path="pytestPDB",
            name="_pluginmanager",
            member=manager,
            lru_runtime_context=standalone,
        )


def test_pytest_pdb_lifecycle_rejects_rebound_consumer_class(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _active_lru_runtime_context()
    references = mutation_toolchain._active_pytest_runtime_context_references(
        context
    )
    assert references is not None
    _mode, config, manager = references
    module = import_module("_pytest.debugging")
    forged_owner = type(
        "pytestPDB",
        (),
        {
            "__module__": "_pytest.debugging",
            "__qualname__": "pytestPDB",
            "_config": config,
            "_pluginmanager": manager,
        },
    )
    monkeypatch.setattr(module, "pytestPDB", forged_owner)

    with pytest.raises(
        MutationToolchainError,
        match="lifecycle consumer changed",
    ):
        mutation_toolchain._runtime_source_class_member_shape(
            module,
            forged_owner,
            path="pytestPDB",
            name="_pluginmanager",
            member=manager,
            lru_runtime_context=context,
        )


def test_pytest_pdb_lifecycle_rejects_forged_context_and_member() -> None:
    context = _active_lru_runtime_context()
    forged_context = replace(context, plugin_manager=object())
    with pytest.raises(MutationToolchainError, match="active pytest"):
        mutation_toolchain._active_pytest_runtime_context_references(
            forged_context
        )

    references = mutation_toolchain._active_pytest_runtime_context_references(
        context
    )
    assert references is not None
    module = import_module("_pytest.debugging")
    owner = vars(module)["pytestPDB"]
    with pytest.raises(
        MutationToolchainError,
        match="lifecycle reference changed",
    ):
        mutation_toolchain._runtime_source_class_member_shape(
            module,
            owner,
            path="pytestPDB",
            name="_pluginmanager",
            member=object(),
            lru_runtime_context=context,
        )


def test_pytest_pdb_lifecycle_standalone_parent_defaults_are_exact() -> None:
    script = r'''
import sys
from importlib import import_module
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "tests"))
from support import mutation_toolchain as toolchain

context = toolchain.standalone_lru_runtime_context()
module = import_module("_pytest.debugging")
owner = vars(module)["pytestPDB"]
assert vars(owner)["_config"] is None
assert vars(owner)["_pluginmanager"] is None
assert toolchain._runtime_source_class_member_shape(
    module,
    owner,
    path="pytestPDB",
    name="_config",
    member=None,
    lru_runtime_context=context,
) == ["pytest-runtime-reference", "standalone-parent", "Config"]
assert toolchain._runtime_source_class_member_shape(
    module,
    owner,
    path="pytestPDB",
    name="_pluginmanager",
    member=None,
    lru_runtime_context=context,
) == ["pytest-runtime-reference", "standalone-parent", "PytestPluginManager"]
'''
    completed = subprocess.run(
        [sys.executable, "-B", "-c", script],
        cwd=_ROOT,
        capture_output=True,
        text=True,
        timeout=_SUBPROCESS_TIMEOUT_SECONDS,
        check=False,
    )
    assert completed.returncode == 0, (
        f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
    )


def test_active_pytest_plugin_manager_rejects_hostile_backref_key_without_callback(
) -> None:
    context = _active_lru_runtime_context()
    config = object.__getattribute__(context, "config")
    manager = object.__getattribute__(context, "plugin_manager")
    manager_namespace = object.__getattribute__(manager, "__dict__")
    original = dict.__getitem__(manager_namespace, "_name2plugin")
    assert type(original) is dict
    hostile_mapping = dict(original)
    dict.__delitem__(hostile_mapping, "pytestconfig")
    calls: list[str] = []

    class HostileKey(str):
        def __hash__(self) -> int:
            return str.__hash__("pytestconfig")

        def __eq__(self, other: object) -> bool:
            calls.append("eq")
            return str.__eq__(self, other)

    dict.__setitem__(hostile_mapping, HostileKey("pytestconfig"), config)
    dict.__setitem__(manager_namespace, "_name2plugin", hostile_mapping)
    try:
        with pytest.raises(
            MutationToolchainError,
            match="Config back-reference changed",
        ):
            _normalize_eager_lru_wrappers()
        assert calls == []
    finally:
        dict.__setitem__(manager_namespace, "_name2plugin", original)
    _normalize_eager_lru_wrappers()


@pytest.mark.parametrize(
    "typed",
    (False, True),
    ids=("hostile-update-wrapper", "typed-wrapper-with-false-metadata"),
)
def test_active_pytest_capture_requires_early_wrapper_identity_without_calling(
    typed: bool,
) -> None:
    context = _active_lru_runtime_context()
    config = object.__getattribute__(context, "config")
    manager = object.__getattribute__(context, "plugin_manager")
    manager_namespace = object.__getattribute__(manager, "__dict__")
    original = object.__getattribute__(context, "get_directory_wrapper")
    early_identity = _current_pytest_lru_identity(config)
    calls: list[str] = []

    def hostile(*_args: object, **_kwargs: object) -> object:
        calls.append("hostile")
        return object()

    replacement = functools.lru_cache(maxsize=256, typed=typed)(hostile)
    functools.update_wrapper(
        replacement,
        mutation_toolchain._EAGER_PYTEST_GET_DIRECTORY_FUNCTION,
    )
    if typed:
        replacement_namespace = object.__getattribute__(
            replacement,
            "__dict__",
        )
        dict.__setitem__(
            replacement_namespace,
            "cache_parameters",
            early_identity["expected_cache_parameters"],
        )
    dict.__setitem__(manager_namespace, "_get_directory", replacement)
    try:
        with pytest.raises(
            MutationToolchainError,
            match="LRU wrapper differs from early reporter identity",
        ):
            mutation_toolchain.capture_active_pytest_lru_runtime_context(
                config,
                **early_identity,
            )
        assert calls == []
    finally:
        dict.__setitem__(manager_namespace, "_get_directory", original)
        mutation_toolchain._EAGER_LRU_CACHE_CLEAR_DESCRIPTOR(replacement)
    _normalize_eager_lru_wrappers()


def test_active_pytest_plugin_manager_rejects_same_semantic_wrapper_swap() -> None:
    context = _active_lru_runtime_context()
    manager = object.__getattribute__(context, "plugin_manager")
    manager_namespace = object.__getattribute__(manager, "__dict__")
    original = object.__getattribute__(context, "get_directory_wrapper")
    replacement = functools.lru_cache(256)(
        mutation_toolchain._EAGER_PYTEST_GET_DIRECTORY_FUNCTION
    )
    assert type(replacement) is type(original)
    dict.__setitem__(manager_namespace, "_get_directory", replacement)
    try:
        with pytest.raises(
            MutationToolchainError,
            match="ownership changed",
        ):
            _normalize_eager_lru_wrappers()
    finally:
        dict.__setitem__(manager_namespace, "_get_directory", original)
        mutation_toolchain._EAGER_LRU_CACHE_CLEAR_DESCRIPTOR(replacement)
    _normalize_eager_lru_wrappers()


@pytest.mark.parametrize(
    ("maxsize", "typed"),
    (
        (257, False),
        (256, True),
    ),
)
def test_active_pytest_plugin_manager_rejects_cache_policy_tamper(
    maxsize: int,
    typed: bool,
) -> None:
    context = _active_lru_runtime_context()
    config = object.__getattribute__(context, "config")
    manager = object.__getattribute__(context, "plugin_manager")
    manager_namespace = object.__getattribute__(manager, "__dict__")
    original = object.__getattribute__(context, "get_directory_wrapper")
    early_identity = _current_pytest_lru_identity(config)
    replacement = functools.lru_cache(maxsize, typed=typed)(
        mutation_toolchain._EAGER_PYTEST_GET_DIRECTORY_FUNCTION
    )
    dict.__setitem__(manager_namespace, "_get_directory", replacement)
    try:
        with pytest.raises(
            MutationToolchainError,
            match="differs from early reporter identity",
        ):
            mutation_toolchain.capture_active_pytest_lru_runtime_context(
                config,
                **early_identity,
            )
    finally:
        dict.__setitem__(manager_namespace, "_get_directory", original)
        mutation_toolchain._EAGER_LRU_CACHE_CLEAR_DESCRIPTOR(replacement)
    _normalize_eager_lru_wrappers()


def test_active_pytest_plugin_manager_rejects_tamper_without_callbacks() -> None:
    calls: list[str] = []

    class HostileConfig:
        def __getattribute__(self, name: str) -> object:
            calls.append(name)
            raise AssertionError("hostile Config callback invoked")

    with pytest.raises(MutationToolchainError, match="Config is not exact"):
        mutation_toolchain.capture_active_pytest_lru_runtime_context(
            HostileConfig(),
            expected_plugin_manager=object(),
            expected_get_directory_wrapper=object(),
            expected_cache_parameters=object(),
        )
    assert calls == []

    context = _active_lru_runtime_context()
    wrapper = object.__getattribute__(context, "get_directory_wrapper")
    wrapper_namespace = object.__getattribute__(wrapper, "__dict__")
    original = dict.get(wrapper_namespace, "cache_parameters")

    def hostile_cache_parameters() -> dict[str, object]:
        calls.append("cache_parameters")
        raise AssertionError("hostile cache_parameters callback invoked")

    dict.__setitem__(
        wrapper_namespace,
        "cache_parameters",
        hostile_cache_parameters,
    )
    try:
        with pytest.raises(
            MutationToolchainError,
            match="wrapper metadata changed",
        ):
            _normalize_eager_lru_wrappers()
        assert calls == []
    finally:
        dict.__setitem__(wrapper_namespace, "cache_parameters", original)
    _normalize_eager_lru_wrappers()


def test_lru_cache_parameters_reject_hostile_metadata_without_callbacks() -> None:
    calls: list[str] = []

    class HostileScalar:
        def __eq__(self, _other: object) -> bool:
            calls.append("eq")
            return True

        def __ne__(self, _other: object) -> bool:
            calls.append("ne")
            return False

    context = _active_lru_runtime_context()
    cache_parameters = object.__getattribute__(context, "cache_parameters")
    original = object.__getattribute__(cache_parameters, "__module__")
    object.__setattr__(cache_parameters, "__module__", HostileScalar())
    try:
        with pytest.raises(
            MutationToolchainError,
            match="cache parameters changed",
        ):
            _normalize_eager_lru_wrappers()
        assert calls == []
    finally:
        object.__setattr__(cache_parameters, "__module__", original)
    _normalize_eager_lru_wrappers()


def test_active_pytest_plugin_manager_finalizer_repopulation_is_rejected() -> None:
    fnmatch_module = import_module("fnmatch")
    context = _active_lru_runtime_context()
    wrapper = object.__getattribute__(context, "get_directory_wrapper")
    _normalize_eager_lru_wrappers()
    concrete_path_type = type(Path())

    class RefillPath(concrete_path_type):
        def is_file(self) -> bool:
            return False

        def __del__(self) -> None:
            fnmatch_module._compile_pattern("phase11-pytest-finalizer")

    payload = RefillPath("phase11-pytest-cache-key")
    assert wrapper(payload) is payload
    del payload
    try:
        with pytest.raises(MutationToolchainError, match="repopulated"):
            _normalize_eager_lru_wrappers()
    finally:
        mutation_toolchain._EAGER_LRU_CACHE_CLEAR_DESCRIPTOR(
            fnmatch_module._compile_pattern
        )
        mutation_toolchain._EAGER_LRU_CACHE_CLEAR_DESCRIPTOR(wrapper)
        _normalize_eager_lru_wrappers()


def test_real_pytest_child_lru_receipt_bridge() -> None:
    receipt = _normalize_eager_lru_wrappers()
    receipt_path = os.environ.get("MOIRA_PHASE11_LRU_RECEIPT_PATH")
    if receipt_path is not None:
        Path(receipt_path).write_text(
            json.dumps(receipt, sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
        )
    if sys.version_info[:2] == (3, 14):
        assert receipt["normalized_lru_wrapper_count"] == 47
        assert receipt["normalized_lru_wrapper_sha256"] == (
            "c7d5b01efce5222f262f26da4341281cf5a50ab92af5b45d28242c2686d56ded"
        )


def test_standalone_parent_matches_real_pytest_child_lru_receipt(
    tmp_path: Path,
) -> None:
    child_receipt = tmp_path / "child-lru-receipt.json"
    parent_script = f"""
import json
import os
from pathlib import Path
import subprocess
import sys
from support.mutation_toolchain import (
    normalize_eager_lru_wrappers,
    standalone_lru_runtime_context,
)

parent_receipt = normalize_eager_lru_wrappers(
    standalone_lru_runtime_context()
)
child_receipt = Path({os.fspath(child_receipt)!r})
child_environment = os.environ.copy()
child_environment["MOIRA_PHASE11_LRU_RECEIPT_PATH"] = str(child_receipt)
try:
    completed = subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "pytest",
            "tests/harness_meta/test_mutation_toolchain.py::test_real_pytest_child_lru_receipt_bridge",
            "-q",
        ],
        cwd={os.fspath(_ROOT)!r},
        env=child_environment,
        capture_output=True,
        text=True,
        check=False,
        timeout={_SUBPROCESS_TIMEOUT_SECONDS!r},
    )
except subprocess.TimeoutExpired as exc:
    raise SystemExit(
        f"real pytest child LRU receipt timed out after {{exc.timeout}} seconds"
    ) from exc
if completed.returncode != 0:
    raise SystemExit(completed.stdout + completed.stderr)
child = json.loads(child_receipt.read_text(encoding="utf-8"))
if child != parent_receipt:
    raise SystemExit(
        "standalone parent and real pytest child LRU receipts differ: "
        + json.dumps({{"parent": parent_receipt, "child": child}}, sort_keys=True)
    )
print(json.dumps(parent_receipt, sort_keys=True))
"""
    environment = os.environ.copy()
    environment.pop("PYTEST_CURRENT_TEST", None)
    environment["PYTHONPATH"] = os.fspath(_ROOT / "tests")
    environment["PYTHONPYCACHEPREFIX"] = os.fspath(
        tmp_path / "standalone-parent-pycache"
    )
    try:
        completed = subprocess.run(
            [sys.executable, "-B", "-c", parent_script],
            cwd=_ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=_SUBPROCESS_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        pytest.fail(
            "standalone parent LRU receipt bridge timed out after "
            f"{exc.timeout} seconds"
        )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    receipt = json.loads(completed.stdout.strip().splitlines()[-1])
    assert receipt["normalized_lru_wrapper_count"] == 47
    assert receipt["normalized_lru_wrapper_sha256"] == (
        "c7d5b01efce5222f262f26da4341281cf5a50ab92af5b45d28242c2686d56ded"
    )


def test_standalone_parent_has_zero_physical_pytest_manager_family(
    tmp_path: Path,
) -> None:
    script = """
import gc
import json
import support.mutation_toolchain as toolchain

context = toolchain.standalone_lru_runtime_context()
receipt = toolchain.normalize_eager_lru_wrappers(context)
gc.collect()
managers = [
    value
    for value in gc.get_objects()
    if type(value) is toolchain._EAGER_PYTEST_PLUGIN_MANAGER_TYPE
]
wrappers = [
    value
    for value in gc.get_objects()
    if type(value) is toolchain._EAGER_LRU_WRAPPER_TYPE
]
registered = {
    id(binding.value)
    for binding in toolchain._EAGER_LRU_WRAPPER_BINDINGS
}
if managers:
    raise SystemExit(f"standalone parent retained managers: {len(managers)}")
if {id(value) for value in wrappers} != registered:
    raise SystemExit("standalone parent retained an unclassified LRU wrapper")
print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
"""
    environment = os.environ.copy()
    environment.pop("PYTEST_CURRENT_TEST", None)
    environment["PYTHONPATH"] = os.fspath(_ROOT / "tests")
    environment["PYTHONPYCACHEPREFIX"] = os.fspath(
        tmp_path / "standalone-zero-family-pycache"
    )
    completed = subprocess.run(
        [sys.executable, "-B", "-c", script],
        cwd=_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=_SUBPROCESS_TIMEOUT_SECONDS,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    receipt = json.loads(completed.stdout.strip().splitlines()[-1])
    assert receipt["normalized_lru_wrapper_count"] == 47
    assert receipt["normalized_lru_wrapper_sha256"] == (
        "c7d5b01efce5222f262f26da4341281cf5a50ab92af5b45d28242c2686d56ded"
    )


def test_eager_lru_normalizer_rejects_unregistered_local_wrapper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    @functools.lru_cache(maxsize=None)
    def unregistered(value: str) -> dict[str, str]:
        return {"value": value}

    unregistered("filled")
    assert unregistered.cache_info().currsize == 1
    monkeypatch.setattr(
        mutation_toolchain,
        "_phase11_unregistered_local_cache",
        unregistered,
        raising=False,
    )

    with pytest.raises(
        MutationToolchainError,
        match="unregistered local functools LRU wrapper",
    ):
        _normalize_eager_lru_wrappers()
    assert unregistered.cache_info().currsize == 1


def test_eager_lru_normalizer_rejects_binding_semantic_and_descriptor_tamper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    binding = next(
        item
        for item in mutation_toolchain._EAGER_LRU_WRAPPER_BINDINGS
        if item.name == "re._compile_template"
    )
    _label, module, attribute = binding.aliases[0]
    monkeypatch.setattr(module, attribute, lambda: None)
    with pytest.raises(MutationToolchainError, match="binding changed"):
        _normalize_eager_lru_wrappers()
    monkeypatch.undo()

    wrapped = vars(binding.value)["__wrapped__"]
    vars(wrapped)["_phase11_semantic_tamper"] = True
    try:
        with pytest.raises(MutationToolchainError, match="binding changed"):
            _normalize_eager_lru_wrappers()
    finally:
        vars(wrapped).pop("_phase11_semantic_tamper", None)

    original_descriptor = (
        mutation_toolchain._EAGER_LRU_CACHE_CLEAR_DESCRIPTOR
    )
    mutation_toolchain._EAGER_LRU_CACHE_CLEAR_DESCRIPTOR = lambda _value: None
    try:
        with pytest.raises(
            MutationToolchainError,
            match="control identity changed",
        ):
            _normalize_eager_lru_wrappers()
    finally:
        mutation_toolchain._EAGER_LRU_CACHE_CLEAR_DESCRIPTOR = (
            original_descriptor
        )


def test_eager_lru_loaded_attester_is_non_mutating() -> None:
    fnmatch_module = import_module("fnmatch")
    _normalize_eager_lru_wrappers()
    fnmatch_module._compile_pattern("phase11-*.py")
    before = fnmatch_module._compile_pattern.cache_info()
    assert before.currsize == 1

    try:
        with pytest.raises(
            MutationToolchainError,
            match="not empty at the attested transition",
        ):
            _attest_eager_lru_wrappers_empty()
        assert fnmatch_module._compile_pattern.cache_info() == before
    finally:
        _normalize_eager_lru_wrappers()


def test_eager_lru_capture_deduplicates_objects_but_retains_all_aliases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = dict(
        mutation_toolchain._RAW_MODULE_NAMESPACES_AFTER_DETERMINISTIC_IMPORTS
    )
    module, namespace = raw["re"]
    wrapper = module._compile_template
    alias = "_phase11_compile_template_alias"
    monkeypatch.setattr(module, alias, wrapper, raising=False)
    raw["re"] = (
        module,
        (*namespace, (alias, wrapper, None)),
    )
    monkeypatch.setattr(
        mutation_toolchain,
        "_RAW_MODULE_NAMESPACES_AFTER_DETERMINISTIC_IMPORTS",
        MappingProxyType(raw),
    )

    *_controls, bindings = (
        mutation_toolchain._capture_eager_lru_wrapper_bindings()
    )
    selected = [item for item in bindings if item.value is wrapper]
    assert len(selected) == 1
    assert [item[0] for item in selected[0].aliases] == [
        "re._compile_template",
        f"re.{alias}",
    ]


def test_eager_lru_nonmodule_paths_reject_typing_and_path_false_greens() -> None:
    _normalize_eager_lru_wrappers()
    typing_module = import_module("typing")
    caches = vars(typing_module)["_caches"]
    key, original = next(iter(dict.items(caches)))
    replacement = functools.lru_cache(maxsize=None)(key)
    dict.__setitem__(caches, key, replacement)
    try:
        with pytest.raises(MutationToolchainError, match="path changed"):
            _normalize_eager_lru_wrappers()
    finally:
        dict.__setitem__(caches, key, original)
        replacement.cache_clear()

    binding = next(
        item
        for item in mutation_toolchain._EAGER_LRU_WRAPPER_BINDINGS
        if item.name == "ipaddress.IPv4Address.is_private.fget"
    )
    path = binding.paths[0]
    original_label = path.label
    object.__setattr__(path, "label", "forged.path")
    try:
        with pytest.raises(MutationToolchainError, match="path changed"):
            _normalize_eager_lru_wrappers()
    finally:
        object.__setattr__(path, "label", original_label)
        _normalize_eager_lru_wrappers()


def test_fastpath_family_attester_rejects_extra_root_without_mutation() -> None:
    _normalize_eager_lru_wrappers()
    foreign = mutation_toolchain._EAGER_FASTPATH_TYPE(
        "phase11-foreign-fastpath-root"
    )
    before = mutation_toolchain._exact_lru_cache_info(
        mutation_toolchain._EAGER_FASTPATH_NEW_WRAPPER,
        label="importlib.metadata.FastPath.__new__",
    )
    assert before[3] == 1
    try:
        with pytest.raises(MutationToolchainError, match="root cache is not empty"):
            _attest_eager_lru_wrappers_empty()
        assert mutation_toolchain._exact_lru_cache_info(
            mutation_toolchain._EAGER_FASTPATH_NEW_WRAPPER,
            label="importlib.metadata.FastPath.__new__",
        ) == before
    finally:
        namespace = vars(foreign)
        wrapper = dict.get(namespace, "lookup")
        if type(wrapper) is mutation_toolchain._EAGER_LRU_WRAPPER_TYPE:
            mutation_toolchain._EAGER_LRU_CACHE_CLEAR_DESCRIPTOR(wrapper)
            object.__delattr__(foreign, "lookup")
        mutation_toolchain._EAGER_LRU_CACHE_CLEAR_DESCRIPTOR(
            mutation_toolchain._EAGER_FASTPATH_NEW_WRAPPER
        )
        _normalize_eager_lru_wrappers()


def test_eager_lru_final_global_pass_detects_destructor_repopulation() -> None:
    fnmatch_module = import_module("fnmatch")
    _normalize_eager_lru_wrappers()

    class Refill(bytes):
        def __del__(self) -> None:
            fnmatch_module._compile_pattern("phase11-repopulated")

    payload = Refill(b"phase11")
    fnmatch_module._re_escape(payload)
    del payload
    try:
        with pytest.raises(MutationToolchainError, match="repopulated"):
            _normalize_eager_lru_wrappers()
    finally:
        mutation_toolchain._EAGER_LRU_CACHE_CLEAR_DESCRIPTOR(
            fnmatch_module._compile_pattern
        )
        mutation_toolchain._EAGER_LRU_CACHE_CLEAR_DESCRIPTOR(
            fnmatch_module._re_escape
        )
        _normalize_eager_lru_wrappers()


def test_eager_lru_gc_completeness_has_no_unclassified_exact_wrapper() -> None:
    import gc

    _normalize_eager_lru_wrappers()
    gc.collect()
    live = [
        value
        for value in gc.get_objects()
        if type(value) is mutation_toolchain._EAGER_LRU_WRAPPER_TYPE
    ]
    registered_ids = {
        id(binding.value)
        for binding in mutation_toolchain._EAGER_LRU_WRAPPER_BINDINGS
    }
    active_wrapper = object.__getattribute__(
        _active_lru_runtime_context(),
        "get_directory_wrapper",
    )
    extra = [value for value in live if id(value) not in registered_ids]
    extra_labels = []
    for value in extra:
        wrapped = dict.get(vars(value), "__wrapped__")
        extra_labels.append(
            (
                type(wrapped).__module__,
                type(wrapped).__qualname__,
                getattr(wrapped, "__module__", None),
                getattr(wrapped, "__qualname__", None),
            )
        )
    assert len(extra) == 1 and extra[0] is active_wrapper, extra_labels
    assert {id(value) for value in live} == {
        *registered_ids,
        id(active_wrapper),
    }
    assert len(live) == 46
    _attest_eager_lru_wrappers_empty()


def test_eager_lru_rejects_hostile_sys_modules_key_without_callbacks() -> None:
    calls: list[str] = []

    class HostileName(str):
        def startswith(self, *_args: object, **_kwargs: object) -> bool:
            calls.append("startswith")
            raise AssertionError("hostile startswith callback invoked")

        def __lt__(self, _other: object) -> bool:
            calls.append("lt")
            raise AssertionError("hostile ordering callback invoked")

    key = HostileName("phase11.hostile.module")
    dict.__setitem__(sys.modules, key, ModuleType(str(key)))
    calls.clear()
    try:
        with pytest.raises(MutationToolchainError, match="non-exact module name"):
            _normalize_eager_lru_wrappers()
        assert calls == []
    finally:
        dict.__delitem__(sys.modules, key)
        _normalize_eager_lru_wrappers()


def test_eager_anyio_reexport_rejects_same_qualname_clone_before_and_after_seal() -> None:
    module = import_module("anyio.abc._eventloop")
    public_module = import_module("anyio.abc")
    original = module.AsyncBackend
    record = mutation_toolchain._EAGER_REEXPORTED_CLASS_BINDINGS[
        (module.__name__, "AsyncBackend")
    ]
    assert record.value is original
    assert record.defining_module is module
    assert record.original_module_name == "anyio.abc._eventloop"
    assert record.public_module is public_module
    assert record.public_module_name == "anyio.abc"
    assert vars(public_module)[record.public_alias] is original

    source_path = Path(str(module.__file__)).resolve(strict=True)
    source = source_path.read_bytes()
    variant = mutation_toolchain._source_loader_variant(
        module.__spec__.loader,
        module_name=module.__name__,
        rewrite_module_is_attested=True,
    )
    _entries, policy, _bindings = (
        mutation_toolchain._sealed_source_variant_payload(
            source,
            source_path=source_path,
            variant=variant,
        )
    )

    clone_namespace = {
        name: value
        for name, value in vars(original).items()
        if name
        not in {
            "__abstractmethods__",
            "__dict__",
            "__weakref__",
            "_abc_impl",
        }
    }
    clone = type(original)(original.__name__, original.__bases__, clone_namespace)
    clone.__module__ = "anyio.abc"
    clone.__qualname__ = original.__qualname__
    sentinel_key = id(module)
    mutation_toolchain._RUNTIME_SOURCE_SENTINELS.pop(sentinel_key, None)

    def bind(value: type[object]) -> None:
        module.AsyncBackend = value
        public_module.AsyncBackend = value

    try:
        bind(clone)
        with pytest.raises(
            MutationToolchainError,
            match="loaded source class binding changed",
        ):
            mutation_toolchain._verify_runtime_source_bindings(
                module,
                policy=policy,
            )

        bind(original)
        mutation_toolchain._verify_runtime_source_bindings(module, policy=policy)

        bind(clone)
        with pytest.raises(
            MutationToolchainError,
            match="loaded source class binding changed",
        ):
            mutation_toolchain._verify_runtime_source_bindings(
                module,
                policy=policy,
            )
    finally:
        bind(original)
        mutation_toolchain._RUNTIME_SOURCE_SENTINELS.pop(sentinel_key, None)


def test_eager_anyio_reexport_does_not_classify_none_as_typed_attribute() -> None:
    module = import_module("anyio.abc._sockets")
    owner = module.UNIXSocketStream
    record = mutation_toolchain._EAGER_REEXPORTED_CLASS_BINDINGS[
        (module.__name__, "UNIXSocketStream")
    ]
    member, shape_sha256 = {
        name: (value, shape)
        for name, value, shape in record.members
    }["__doc__"]

    assert member is None
    assert shape_sha256 != mutation_toolchain._ANYIO_TYPED_ATTRIBUTE_MEMBER_MARKER
    assert shape_sha256 == mutation_toolchain._sha256_bytes(
        mutation_toolchain._canonical_json_bytes(
            mutation_toolchain._runtime_value_shape(member)
        )
    )
    assert mutation_toolchain._exact_reexported_class_module(
        module,
        owner,
        source_shape=next(
            shape
            for shape in _loaded_source_policy(module).classes
            if shape.path == ("UNIXSocketStream",)
        ),
    )


@pytest.mark.parametrize(
    ("mode", "accepted"),
    (
        ("cache-only", True),
        ("register", False),
        ("abc-impl", False),
        ("get-dump-provider", False),
    ),
)
def test_eager_anyio_reexport_abc_registry_is_exact_before_first_seal(
    tmp_path: Path,
    mode: str,
    accepted: bool,
) -> None:
    script = f'''
import json
from importlib import import_module
from pathlib import Path

import support.mutation_toolchain as toolchain

mode = {mode!r}
module = import_module("anyio.abc._eventloop")
owner = module.AsyncBackend
record = toolchain._EAGER_REEXPORTED_CLASS_BINDINGS[
    ("anyio.abc._eventloop", "AsyncBackend")
]
if record.abc_registry is None:
    raise SystemExit("captured AsyncBackend has no eager ABC registry evidence")
source_path = Path(str(module.__file__)).resolve(strict=True)
variant = toolchain._source_loader_variant(
    module.__spec__.loader,
    module_name=module.__name__,
    rewrite_module_is_attested=True,
)
_entries, policy, _bindings = toolchain._sealed_source_variant_payload(
    source_path.read_bytes(),
    source_path=source_path,
    variant=variant,
)
toolchain._RUNTIME_SOURCE_SENTINELS.pop(id(module), None)
restore = None

class Foreign:
    pass

try:
    if mode == "cache-only":
        class Child(owner):
            pass

        if not issubclass(Child, owner) or issubclass(Foreign, owner):
            raise SystemExit("ABC cache canary did not exercise both cache paths")
    elif mode == "register":
        owner.register(Foreign)
    elif mode == "abc-impl":
        namespace = type.__getattribute__(owner, "__dict__")
        original = namespace["_abc_impl"]
        owner._abc_impl = object()
        restore = lambda: setattr(owner, "_abc_impl", original)
    elif mode == "get-dump-provider":
        provider_module = toolchain._EAGER_NATIVE_ABC_MODULE
        original = vars(provider_module)["_get_dump"]
        provider_module._get_dump = lambda _owner: (set(), set(), set(), 0)
        restore = lambda: setattr(provider_module, "_get_dump", original)
    else:
        raise SystemExit(f"unknown mode: {{mode}}")

    rejected = False
    try:
        toolchain._verify_runtime_source_bindings(module, policy=policy)
        toolchain._verify_runtime_source_bindings(module, policy=policy)
    except toolchain.MutationToolchainError:
        rejected = True
finally:
    if restore is not None:
        restore()

print(json.dumps({{"accepted": not rejected, "mode": mode}}, sort_keys=True))
'''
    environment = os.environ.copy()
    environment.pop("PYTEST_CURRENT_TEST", None)
    environment["PYTHONPATH"] = os.fspath(_ROOT / "tests")
    environment["PYTHONPYCACHEPREFIX"] = os.fspath(
        tmp_path / f"anyio-abc-{mode}-pycache"
    )
    completed = subprocess.run(
        [sys.executable, "-B", "-c", script],
        cwd=_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=_SUBPROCESS_TIMEOUT_SECONDS,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert json.loads(completed.stdout.strip().splitlines()[-1]) == {
        "accepted": accepted,
        "mode": mode,
    }


def _async_backend_reexport_evidence() -> tuple[
    ModuleType,
    type[object],
    object,
    object,
]:
    module = import_module("anyio.abc._eventloop")
    owner = module.AsyncBackend
    record = mutation_toolchain._EAGER_REEXPORTED_CLASS_BINDINGS[
        (module.__name__, "AsyncBackend")
    ]
    source_shape = next(
        shape
        for shape in _loaded_source_policy(module).classes
        if shape.path == ("AsyncBackend",)
    )
    return module, owner, record, source_shape


@pytest.mark.parametrize("scope", ("defining", "public"))
@pytest.mark.parametrize("field", ("__name__", "__file__", "origin"))
def test_eager_anyio_reexport_rejects_hostile_module_metadata_without_callbacks(
    scope: str,
    field: str,
) -> None:
    module, owner, record, source_shape = _async_backend_reexport_evidence()
    target = module if scope == "defining" else record.public_module
    calls: list[str] = []

    class HostileString(str):
        def __hash__(self) -> int:
            calls.append("hash")
            raise AssertionError("hostile metadata hash invoked")

        def __eq__(self, _other: object) -> bool:
            calls.append("eq")
            raise AssertionError("hostile metadata equality invoked")

        def __str__(self) -> str:
            calls.append("str")
            raise AssertionError("hostile metadata string conversion invoked")

        def __fspath__(self) -> str:
            calls.append("fspath")
            raise AssertionError("hostile metadata path conversion invoked")

    if field == "origin":
        container = vars(vars(target)["__spec__"])
        key = "origin"
    else:
        container = vars(target)
        key = field
    original = container[key]
    container[key] = HostileString(str.__str__(original))
    calls.clear()
    try:
        assert not mutation_toolchain._exact_reexported_class_module(
            module,
            owner,
            source_shape=source_shape,
        )
        assert calls == []
    finally:
        container[key] = original


@pytest.mark.parametrize("scope", ("defining", "public"))
@pytest.mark.parametrize("field", ("__name__", "__file__", "origin"))
def test_eager_anyio_reexport_rejects_equal_distinct_module_metadata(
    scope: str,
    field: str,
) -> None:
    module, owner, record, source_shape = _async_backend_reexport_evidence()
    target = module if scope == "defining" else record.public_module
    if field == "origin":
        container = vars(vars(target)["__spec__"])
        key = "origin"
    else:
        container = vars(target)
        key = field
    original = container[key]
    replacement = (original + "\0")[:-1]
    assert type(replacement) is str
    assert replacement == original
    assert replacement is not original
    container[key] = replacement
    try:
        assert not mutation_toolchain._exact_reexported_class_module(
            module,
            owner,
            source_shape=source_shape,
        )
    finally:
        container[key] = original


def test_eager_anyio_reexport_metadata_positive_does_not_require_key_identity() -> None:
    _module, _owner, record, _source_shape = _async_backend_reexport_evidence()
    for (
        module,
        module_name,
        module_name_value,
        module_file,
        specification,
        origin,
        loader,
    ) in (
        (
            record.defining_module,
            record.defining_module_name,
            record.defining_module_name_value,
            record.defining_file,
            record.defining_specification,
            record.defining_origin,
            record.defining_loader,
        ),
        (
            record.public_module,
            record.public_module_name,
            record.public_module_name_value,
            record.public_file,
            record.public_specification,
            record.public_origin,
            record.public_loader,
        ),
    ):
        assert mutation_toolchain._captured_module_metadata_matches(
            module,
            module_name=module_name,
            module_name_value=module_name_value,
            module_file=module_file,
            specification=specification,
            origin=origin,
            loader=loader,
        )


_EXACT_ANYIO_REEXPORT_LOOP = (
    "for __value in list(locals().values()):\n"
    "    if getattr(__value, '__module__', '').startswith('pkg.'):\n"
    "        __value.__module__ = __name__\n"
)


def _synthetic_reexport_source_is_exact(source: str) -> tuple[int | None, bool]:
    tree = ast.parse(source)
    rewrite_index = mutation_toolchain._exact_reexport_rewrite_index(
        tree,
        public_module_name="pkg",
    )
    public_module = ModuleType("pkg")
    public_module.__package__ = "pkg"
    policy = mutation_toolchain._source_code_policy(tree)
    direct_import = (
        rewrite_index is not None
        and mutation_toolchain._exact_direct_public_import(
            public_module,
            tree=tree,
            before_index=rewrite_index,
            policy=policy,
            class_name="Probe",
            defining_module_name="pkg.private",
        )
    )
    return rewrite_index, direct_import


def test_anyio_reexport_rewrite_requires_import_before_unique_exact_loop() -> None:
    rewrite_index, direct_import = _synthetic_reexport_source_is_exact(
        "from .private import Probe\n" + _EXACT_ANYIO_REEXPORT_LOOP
    )
    assert rewrite_index == 1
    assert direct_import

    rewrite_index, direct_import = _synthetic_reexport_source_is_exact(
        _EXACT_ANYIO_REEXPORT_LOOP + "from .private import Probe\n"
    )
    assert rewrite_index == 0
    assert not direct_import


@pytest.mark.parametrize(
    "extra_source",
    (
        "Probe.__module__ = __name__\n",
        "del Probe.__module__\n",
        "setattr(Probe, '__module__', __name__)\n",
        (
            "for other in list(locals().values()):\n"
            "    if getattr(other, '__module__', '').startswith('pkg.'):\n"
            "        other.__module__ = __name__\n"
        ),
        _EXACT_ANYIO_REEXPORT_LOOP,
    ),
)
def test_anyio_reexport_rewrite_rejects_every_competing_module_write(
    extra_source: str,
) -> None:
    rewrite_index, direct_import = _synthetic_reexport_source_is_exact(
        "from .private import Probe\n"
        + _EXACT_ANYIO_REEXPORT_LOOP
        + extra_source
    )
    assert rewrite_index is None
    assert not direct_import


_ANYIO_TYPED_ATTRIBUTE_CASES = (
    (
        "anyio.abc._sockets",
        "SocketAttribute",
        (
            "family",
            "local_address",
            "local_port",
            "raw_socket",
            "remote_address",
            "remote_port",
        ),
    ),
    (
        "anyio.streams.file",
        "FileStreamAttribute",
        ("file", "fileno", "path"),
    ),
    (
        "anyio.streams.tls",
        "TLSAttribute",
        (
            "alpn_protocol",
            "channel_binding_tls_unique",
            "cipher",
            "peer_certificate",
            "peer_certificate_binary",
            "server_side",
            "shared_ciphers",
            "ssl_object",
            "standard_compatible",
            "tls_version",
        ),
    ),
)


def _assert_anyio_typed_attribute_mutation_rejected(
    module: ModuleType,
    replacements: tuple[tuple[type[object], str, object], ...],
) -> None:
    policy = _loaded_source_policy(module)
    sentinel_key = id(module)
    originals = tuple(
        (
            owner,
            name,
            type.__getattribute__(owner, "__dict__")[name],
        )
        for owner, name, _replacement in replacements
    )
    mutation_toolchain._RUNTIME_SOURCE_SENTINELS.pop(sentinel_key, None)
    try:
        for owner, name, replacement in replacements:
            setattr(owner, name, replacement)
        with pytest.raises(MutationToolchainError):
            mutation_toolchain._verify_runtime_source_bindings(
                module,
                policy=policy,
            )
    finally:
        for owner, name, original in reversed(originals):
            setattr(owner, name, original)
        mutation_toolchain._RUNTIME_SOURCE_SENTINELS.pop(sentinel_key, None)


@pytest.mark.parametrize(
    ("module_name", "class_name", "member_names"),
    _ANYIO_TYPED_ATTRIBUTE_CASES,
)
def test_eager_anyio_typed_attribute_registry_is_source_owned(
    module_name: str,
    class_name: str,
    member_names: tuple[str, ...],
) -> None:
    module = import_module(module_name)
    source_path = Path(str(module.__file__)).resolve(strict=True)
    policy = _loaded_source_policy(module)
    source_shape = next(
        shape for shape in policy.classes if shape.path == (class_name,)
    )
    record = mutation_toolchain._EAGER_ANYIO_TYPED_ATTRIBUTE_CLASS_BINDINGS[
        (module_name, class_name)
    ]

    manifest = mutation_toolchain._source_code_manifest(
        source_path.read_bytes(),
        source_path=source_path,
    )
    assert manifest["schema_version"] == 3
    assert tuple(
        member.name for member in source_shape.zero_arg_call_members
    ) == member_names
    assert all(
        type(member) is mutation_toolchain._SourceZeroArgCallMember
        and member.reference == ("typed_attribute",)
        and member.assignment_kind == "annassign"
        and type(member.annotation) is str
        and member.annotation
        and member.simple == 1
        for member in source_shape.zero_arg_call_members
    )
    assert record.source_shape_sha256 == (
        mutation_toolchain._source_class_shape_sha256(source_shape)
    )
    assert record.module is module
    assert record.value is vars(module)[class_name]
    assert tuple(name for name, _value in record.members) == member_names
    assert all(
        type(value) is object
        and type.__getattribute__(record.value, "__dict__")[name] is value
        for name, value in record.members
    )


@pytest.mark.parametrize(
    ("module_name", "class_name", "member_names"),
    _ANYIO_TYPED_ATTRIBUTE_CASES,
)
def test_eager_anyio_typed_attribute_classes_verify_repeatedly(
    module_name: str,
    class_name: str,
    member_names: tuple[str, ...],
) -> None:
    module = import_module(module_name)
    record = mutation_toolchain._EAGER_ANYIO_TYPED_ATTRIBUTE_CLASS_BINDINGS[
        (module_name, class_name)
    ]
    assert tuple(name for name, _value in record.members) == member_names
    policy = _loaded_source_policy(module)
    sentinel_key = id(module)
    mutation_toolchain._RUNTIME_SOURCE_SENTINELS.pop(sentinel_key, None)
    try:
        mutation_toolchain._verify_runtime_source_bindings(
            module,
            policy=policy,
        )
        mutation_toolchain._verify_runtime_source_bindings(
            module,
            policy=policy,
        )
    finally:
        mutation_toolchain._RUNTIME_SOURCE_SENTINELS.pop(sentinel_key, None)


def test_eager_anyio_typed_attribute_rejects_token_replacement_before_and_after_seal(
) -> None:
    module = import_module("anyio.abc._sockets")
    owner = module.SocketAttribute
    name = "family"
    original = type.__getattribute__(owner, "__dict__")[name]
    policy = _loaded_source_policy(module)
    sentinel_key = id(module)
    mutation_toolchain._RUNTIME_SOURCE_SENTINELS.pop(sentinel_key, None)

    try:
        setattr(owner, name, object())
        with pytest.raises(MutationToolchainError):
            mutation_toolchain._verify_runtime_source_bindings(
                module,
                policy=policy,
            )

        setattr(owner, name, original)
        mutation_toolchain._verify_runtime_source_bindings(
            module,
            policy=policy,
        )
        mutation_toolchain._verify_runtime_source_bindings(
            module,
            policy=policy,
        )

        setattr(owner, name, object())
        with pytest.raises(MutationToolchainError):
            mutation_toolchain._verify_runtime_source_bindings(
                module,
                policy=policy,
            )
    finally:
        setattr(owner, name, original)
        mutation_toolchain._RUNTIME_SOURCE_SENTINELS.pop(sentinel_key, None)


def test_eager_anyio_typed_attribute_rejects_same_class_token_swap() -> None:
    module = import_module("anyio.abc._sockets")
    owner = module.SocketAttribute
    namespace = type.__getattribute__(owner, "__dict__")
    family = namespace["family"]
    local_address = namespace["local_address"]
    _assert_anyio_typed_attribute_mutation_rejected(
        module,
        (
            (owner, "family", local_address),
            (owner, "local_address", family),
        ),
    )


def test_eager_anyio_typed_attribute_rejects_same_class_token_alias() -> None:
    module = import_module("anyio.abc._sockets")
    owner = module.SocketAttribute
    family = type.__getattribute__(owner, "__dict__")["family"]
    _assert_anyio_typed_attribute_mutation_rejected(
        module,
        ((owner, "local_address", family),),
    )


def test_eager_anyio_typed_attribute_rejects_cross_class_token_alias() -> None:
    socket_module = import_module("anyio.abc._sockets")
    file_module = import_module("anyio.streams.file")
    socket_family = type.__getattribute__(
        socket_module.SocketAttribute,
        "__dict__",
    )["family"]
    _assert_anyio_typed_attribute_mutation_rejected(
        file_module,
        ((file_module.FileStreamAttribute, "file", socket_family),),
    )


def test_eager_anyio_typed_attribute_rejects_hostile_owner_qualname_without_callbacks(
) -> None:
    calls: list[str] = []

    class HostileName(str):
        def __hash__(self) -> int:
            calls.append("hash")
            raise AssertionError("hostile qualname hash callback invoked")

        def __eq__(self, _other: object) -> bool:
            calls.append("eq")
            raise AssertionError("hostile qualname equality callback invoked")

        def __ne__(self, _other: object) -> bool:
            calls.append("ne")
            raise AssertionError("hostile qualname inequality callback invoked")

    module = import_module("anyio.streams.file")
    owner = module.FileStreamAttribute
    original = type.__getattribute__(owner, "__qualname__")
    policy = _loaded_source_policy(module)
    sentinel_key = id(module)
    mutation_toolchain._RUNTIME_SOURCE_SENTINELS.pop(sentinel_key, None)
    type.__setattr__(owner, "__qualname__", HostileName(original))
    calls.clear()

    try:
        with pytest.raises(MutationToolchainError):
            mutation_toolchain._verify_runtime_source_bindings(
                module,
                policy=policy,
            )
        assert calls == []
    finally:
        type.__setattr__(owner, "__qualname__", original)
        mutation_toolchain._RUNTIME_SOURCE_SENTINELS.pop(sentinel_key, None)


def test_eager_anyio_typed_attribute_rejects_provider_code_replacement() -> None:
    module = import_module("anyio.streams.tls")
    provider = mutation_toolchain._EAGER_ANYIO_TYPED_ATTRIBUTE
    original_code = provider.__code__
    policy = _loaded_source_policy(module)
    sentinel_key = id(module)
    mutation_toolchain._RUNTIME_SOURCE_SENTINELS.pop(sentinel_key, None)

    try:
        provider.__code__ = original_code.replace(
            co_consts=(*original_code.co_consts, "phase11-unused-constant"),
        )
        with pytest.raises(MutationToolchainError):
            mutation_toolchain._verify_runtime_source_bindings(
                module,
                policy=policy,
            )
    finally:
        provider.__code__ = original_code
        mutation_toolchain._RUNTIME_SOURCE_SENTINELS.pop(sentinel_key, None)


def test_eager_anyio_typed_attribute_rejects_provider_global_object_injection(
) -> None:
    module = import_module("anyio.streams.tls")
    provider_module = mutation_toolchain._EAGER_ANYIO_TYPED_ATTRIBUTE_MODULE
    assert "object" not in vars(provider_module)
    policy = _loaded_source_policy(module)
    sentinel_key = id(module)
    mutation_toolchain._RUNTIME_SOURCE_SENTINELS.pop(sentinel_key, None)

    try:
        provider_module.object = object
        with pytest.raises(MutationToolchainError):
            mutation_toolchain._verify_runtime_source_bindings(
                module,
                policy=policy,
            )
    finally:
        del provider_module.object
        mutation_toolchain._RUNTIME_SOURCE_SENTINELS.pop(sentinel_key, None)


@pytest.mark.parametrize(
    ("route", "consumer_name"),
    (
        ("public", "anyio.abc._sockets"),
        ("core", "anyio.streams.tls"),
    ),
)
def test_eager_anyio_typed_attribute_rejects_public_core_route_split(
    route: str,
    consumer_name: str,
) -> None:
    public_module = import_module("anyio")
    core_module = mutation_toolchain._EAGER_ANYIO_TYPED_ATTRIBUTE_MODULE
    consumer = import_module(consumer_name)
    provider = mutation_toolchain._EAGER_ANYIO_TYPED_ATTRIBUTE
    clone = FunctionType(
        provider.__code__,
        provider.__globals__,
        provider.__name__,
        provider.__defaults__,
        provider.__closure__,
    )
    clone.__annotations__ = dict(provider.__annotations__)
    clone.__dict__.update(provider.__dict__)
    clone.__kwdefaults__ = provider.__kwdefaults__
    clone.__module__ = provider.__module__
    clone.__qualname__ = provider.__qualname__
    target = public_module if route == "public" else core_module
    original = vars(target)["typed_attribute"]
    policy = _loaded_source_policy(consumer)
    sentinel_key = id(consumer)
    mutation_toolchain._RUNTIME_SOURCE_SENTINELS.pop(sentinel_key, None)

    try:
        target.typed_attribute = clone
        with pytest.raises(MutationToolchainError):
            mutation_toolchain._verify_runtime_source_bindings(
                consumer,
                policy=policy,
            )
    finally:
        target.typed_attribute = original
        mutation_toolchain._RUNTIME_SOURCE_SENTINELS.pop(sentinel_key, None)


def test_builtin_fallback_rejects_injected_global_before_and_after_seal() -> None:
    module = import_module("hypothesis.core")
    policy = _loaded_source_policy(module)
    sentinel_key = id(module)
    original_present = "len" in vars(module)
    original = vars(module).get("len")
    mutation_toolchain._RUNTIME_SOURCE_SENTINELS.pop(sentinel_key, None)

    try:
        module.len = sum
        with pytest.raises(
            MutationToolchainError,
            match="loaded source builtin fallback changed: hypothesis.core.len",
        ):
            mutation_toolchain._verify_runtime_source_bindings(
                module,
                policy=policy,
            )

        del module.len
        mutation_toolchain._verify_runtime_source_bindings(module, policy=policy)
        module.len = sum
        with pytest.raises(
            MutationToolchainError,
            match="loaded source builtin fallback changed: hypothesis.core.len",
        ):
            mutation_toolchain._verify_runtime_source_bindings(
                module,
                policy=policy,
            )
    finally:
        if original_present:
            module.len = original
        elif "len" in vars(module):
            del module.len
        mutation_toolchain._RUNTIME_SOURCE_SENTINELS.pop(sentinel_key, None)


def test_first_import_attestation_rejects_simultaneous_provider_consumer_tamper() -> None:
    functools_module = import_module("functools")
    module = import_module("_pytest.python")
    policy = _loaded_source_policy(module)
    original_provider = functools_module.partial
    original_consumer = module.partial
    sentinel_key = id(module)
    mutation_toolchain._RUNTIME_SOURCE_SENTINELS.pop(sentinel_key, None)

    try:
        functools_module.partial = sum
        module.partial = sum
        with pytest.raises(
            MutationToolchainError,
            match="loaded source import provider changed: functools.partial",
        ):
            mutation_toolchain._verify_runtime_source_bindings(
                module,
                policy=policy,
            )
    finally:
        functools_module.partial = original_provider
        module.partial = original_consumer
        mutation_toolchain._RUNTIME_SOURCE_SENTINELS.pop(sentinel_key, None)


def test_late_typing_provider_rejects_wrong_cached_alias_defaults() -> None:
    missing = object()
    original_module = sys.modules.get("typing_extensions", missing)
    typing_module = import_module("typing")
    module = import_module("typing_extensions")
    policy = _loaded_source_policy(module)
    alias = typing_module.AsyncContextManager
    assert module.AsyncContextManager is alias
    original_defaults = alias._defaults
    sentinel_key = id(module)
    mutation_toolchain._RUNTIME_SOURCE_SENTINELS.pop(sentinel_key, None)

    try:
        alias._defaults = (int,)
        with pytest.raises(
            MutationToolchainError,
            match=(
                "loaded source import provider changed: "
                "typing.AsyncContextManager"
            ),
        ):
            mutation_toolchain._verify_runtime_source_bindings(
                module,
                policy=policy,
            )
    finally:
        alias._defaults = original_defaults
        mutation_toolchain._RUNTIME_SOURCE_SENTINELS.pop(sentinel_key, None)
        if original_module is missing:
            sys.modules.pop("typing_extensions", None)
        else:
            sys.modules["typing_extensions"] = original_module


def test_public_attestation_rejects_preseal_lazy_alias_provider_method_swap(
) -> None:
    typing_module = import_module("typing")
    assert "AsyncContextManager" not in vars(typing_module)
    provider = typing_module._SpecialGenericAlias
    original = vars(provider)["__getitem__"]
    hostile_calls: list[object] = []
    modules_before = dict(sys.modules)
    source_sentinels_before = dict(
        mutation_toolchain._RUNTIME_SOURCE_SENTINELS
    )
    prefix_sentinels_before = dict(
        mutation_toolchain._RUNTIME_PREFIX_SENTINELS
    )
    mutation_toolchain._RUNTIME_SOURCE_SENTINELS.clear()

    def hostile(self: object, parameters: object) -> tuple[str, object]:
        hostile_calls.append(parameters)
        return "hostile", parameters

    rejected: MutationToolchainError | None = None
    provider.__getitem__ = hostile
    try:
        try:
            identity = _current_identity()
            _loaded_test_toolchain_attestation(identity)
        except MutationToolchainError as exc:
            rejected = exc
        if rejected is None:
            typing_module.AsyncContextManager[int]
        added_prefix_modules = sorted(
            name
            for name, module in sys.modules.items()
            if name not in modules_before
            and isinstance(module, ModuleType)
            and isinstance(getattr(module, "__file__", None), str)
            and Path(str(module.__file__)).resolve().is_relative_to(
                mutation_toolchain._DETERMINISTIC_IMPORT_PREFIX
            )
        )
        assert rejected is not None, (
            "loaded attestation accepted a replaced lazy-alias provider method; "
            f"hostile_calls={hostile_calls!r}; "
            f"added_prefix_modules={added_prefix_modules!r}"
        )
        assert not hostile_calls
    finally:
        provider.__getitem__ = original
        vars(typing_module).pop("AsyncContextManager", None)
        for name in set(sys.modules) - modules_before.keys():
            sys.modules.pop(name, None)
        for name, module in modules_before.items():
            sys.modules[name] = module
        mutation_toolchain._RUNTIME_SOURCE_SENTINELS.clear()
        mutation_toolchain._RUNTIME_SOURCE_SENTINELS.update(
            source_sentinels_before
        )
        mutation_toolchain._RUNTIME_PREFIX_SENTINELS.clear()
        mutation_toolchain._RUNTIME_PREFIX_SENTINELS.update(
            prefix_sentinels_before
        )


def test_public_attestation_rejects_preseal_provider_function_code_swap() -> None:
    contextlib_module = import_module("contextlib")
    contextmanager = contextlib_module.contextmanager
    original_code = contextmanager.__code__
    modules_before = dict(sys.modules)
    source_sentinels_before = dict(
        mutation_toolchain._RUNTIME_SOURCE_SENTINELS
    )
    prefix_sentinels_before = dict(
        mutation_toolchain._RUNTIME_PREFIX_SENTINELS
    )
    mutation_toolchain._RUNTIME_SOURCE_SENTINELS.clear()

    original_name = "_phase11_original_contextmanager"
    assert original_name not in vars(contextlib_module)
    original_clone = FunctionType(
        original_code,
        contextmanager.__globals__,
        contextmanager.__name__,
        contextmanager.__defaults__,
        contextmanager.__closure__,
    )
    original_clone.__kwdefaults__ = contextmanager.__kwdefaults__
    original_clone.__annotations__ = dict(contextmanager.__annotations__)
    original_clone.__dict__.update(contextmanager.__dict__)
    setattr(contextlib_module, original_name, original_clone)

    def hostile(function: object) -> object:
        if getattr(function, "__name__", "") == "__phase11_probe__":
            return "phase11-hostile-contextmanager"
        return _phase11_original_contextmanager(function)  # noqa: F821

    def __phase11_probe__() -> object:
        yield None

    forged_code = hostile.__code__.replace(
        co_filename=original_code.co_filename,
        co_firstlineno=original_code.co_firstlineno,
        co_name=original_code.co_name,
        co_qualname=original_code.co_qualname,
    )
    rejected: MutationToolchainError | None = None
    hostile_result: object | None = None
    contextmanager.__code__ = forged_code
    try:
        try:
            identity = _current_identity()
            _loaded_test_toolchain_attestation(identity)
        except MutationToolchainError as exc:
            rejected = exc
        if rejected is None:
            hostile_result = contextlib_module.contextmanager(__phase11_probe__)
        assert rejected is not None, (
            "loaded attestation accepted an in-place eager provider code swap; "
            f"hostile_result={hostile_result!r}"
        )
        assert "eager provider executable changed" in str(rejected), rejected
    finally:
        contextmanager.__code__ = original_code
        delattr(contextlib_module, original_name)
        for name in set(sys.modules) - modules_before.keys():
            sys.modules.pop(name, None)
        for name, module in modules_before.items():
            sys.modules[name] = module
        mutation_toolchain._RUNTIME_SOURCE_SENTINELS.clear()
        mutation_toolchain._RUNTIME_SOURCE_SENTINELS.update(
            source_sentinels_before
        )
        mutation_toolchain._RUNTIME_PREFIX_SENTINELS.clear()
        mutation_toolchain._RUNTIME_PREFIX_SENTINELS.update(
            prefix_sentinels_before
        )


def test_hypothesis_module_lifecycle_scalars_remain_semantically_bound() -> None:
    module = import_module("hypothesis.core")
    policy = _loaded_source_policy(module)
    original_seed = module.global_force_seed
    original_running = module.running_under_pytest
    sentinel_key = id(module)
    mutation_toolchain._RUNTIME_SOURCE_SENTINELS.pop(sentinel_key, None)

    try:
        mutation_toolchain._verify_runtime_source_bindings(module, policy=policy)

        module.global_force_seed = 837462
        with pytest.raises(
            MutationToolchainError,
            match=(
                "loaded source module policy changed: "
                "hypothesis.core.global_force_seed"
            ),
        ):
            mutation_toolchain._verify_runtime_source_bindings(
                module,
                policy=policy,
            )
        module.global_force_seed = original_seed

        module.running_under_pytest = not original_running
        with pytest.raises(
            MutationToolchainError,
            match=(
                "loaded source module policy changed: "
                "hypothesis.core.running_under_pytest"
            ),
        ):
            mutation_toolchain._verify_runtime_source_bindings(
                module,
                policy=policy,
            )
    finally:
        module.global_force_seed = original_seed
        module.running_under_pytest = original_running
        mutation_toolchain._RUNTIME_SOURCE_SENTINELS.pop(sentinel_key, None)


def test_first_class_attestation_rejects_enum_and_namespace_tamper() -> None:
    module = import_module("_pytest.config")
    policy = _loaded_source_policy(module)
    exit_ok = module.ExitCode.OK
    original_value = vars(exit_ok)["_value_"]
    rogue_name = "_phase11_preseal_rogue_state"
    sentinel_key = id(module)
    assert rogue_name not in vars(module.Config)

    try:
        mutation_toolchain._RUNTIME_SOURCE_SENTINELS.pop(sentinel_key, None)
        exit_ok._value_ = 73
        with pytest.raises(
            MutationToolchainError,
            match="loaded source Enum member changed: _pytest.config.ExitCode.OK",
        ):
            mutation_toolchain._verify_runtime_source_bindings(
                module,
                policy=policy,
            )

        exit_ok._value_ = original_value
        mutation_toolchain._RUNTIME_SOURCE_SENTINELS.pop(sentinel_key, None)
        setattr(module.Config, rogue_name, 73)
        with pytest.raises(
            MutationToolchainError,
            match="loaded source class namespace key set changed",
        ):
            mutation_toolchain._verify_runtime_source_bindings(
                module,
                policy=policy,
            )
    finally:
        exit_ok._value_ = original_value
        if rogue_name in vars(module.Config):
            delattr(module.Config, rogue_name)
        mutation_toolchain._RUNTIME_SOURCE_SENTINELS.pop(sentinel_key, None)


def _symlink_or_skip(link: Path, target: Path, *, target_is_directory: bool) -> None:
    try:
        link.symlink_to(target, target_is_directory=target_is_directory)
    except NotImplementedError:
        pytest.skip("this platform does not implement symbolic links")
    except OSError as exc:
        if exc.errno in {errno.EACCES, errno.EPERM} or getattr(
            exc, "winerror", None
        ) == 1314:
            pytest.skip("the current platform privilege cannot create a symlink")
        raise


def test_current_toolchain_closure_is_exact_compact_and_byte_bound() -> None:
    identity = _current_identity()
    expected = {
        "hypothesis",
        "iniconfig",
        "packaging",
        "pluggy",
        "pygments",
        "pytest",
        "pyyaml",
        "sortedcontainers",
    }
    if os.name == "nt":
        expected.add("colorama")
    if sys.version_info < (3, 11):
        expected.update({"exceptiongroup", "tomli"})
    expected_host = {
        "anyio",
        "coverage",
        "execnet",
        "idna",
        "pluggy",
        "pytest",
        "pytest-cov",
        "pytest-xdist",
        "typing-extensions",
    } | (expected - {"hypothesis", "pyyaml", "sortedcontainers"})

    assert identity["dependency_closure"] == sorted(expected)
    assert identity["host_dependency_closure"] == sorted(expected_host)
    all_distributions = expected | expected_host
    assert [item["name"] for item in identity["distributions"]] == sorted(
        all_distributions
    )
    assert {
        item["name"]: item["version"] for item in identity["distributions"]
    } == {name: metadata.version(name) for name in all_distributions}
    assert identity["file_count"] > len(expected)
    assert identity["bytes"] > 0
    assert (
        len(json.dumps(identity, sort_keys=True, separators=(",", ":")))
        < 24_576
    )
    prefix = Path(str(identity["prefix"]))
    expected_startup_scopes = {
        item.path
        for path in mutation_toolchain._startup_control_scopes(
            mutation_toolchain._distribution_search_paths(prefix)
        )
        for item in mutation_toolchain._walk_plain_tree(
            prefix,
            path,
            label="expected startup scope",
        )
    }
    observed_startup_files = {
        item["path"] for item in identity["startup"]["files"]
    }
    assert expected_startup_scopes.issubset(observed_startup_files)
    assert "_distutils_hack" in identity["startup"]["module_names"]
    assert any(
        name.startswith("__editable___moira_astro_")
        for name in identity["startup"]["module_names"]
    )


def test_same_version_byte_edit_and_unrecorded_injection_change_identity(
    tmp_path: Path,
) -> None:
    baseline, prefix, site_packages = _fake_toolchain(tmp_path)
    source = site_packages / "pytest" / "__init__.py"
    original = source.read_text(encoding="utf-8")
    source.write_text(original.replace("pytest", "pytests"), encoding="utf-8")
    changed = mutation_toolchain._build_test_toolchain_identity(
        prefix=prefix,
        search_paths=(site_packages,),
        roots=("pytest",),
        registry={
            "pytest": mutation_toolchain._DistributionScope(
                import_paths=("pytest",),
                source_modules=(("pytest", "pytest/__init__.py"),),
            )
        },
    )
    assert changed["distributions"][0]["version"] == baseline["distributions"][0][
        "version"
    ]
    assert changed["manifest_sha256"] != baseline["manifest_sha256"]

    injected = site_packages / "pytest" / "unrecorded_injection.py"
    injected.write_text("INJECTED = True\n", encoding="utf-8")
    with_injection = mutation_toolchain._build_test_toolchain_identity(
        prefix=prefix,
        search_paths=(site_packages,),
        roots=("pytest",),
        registry={
            "pytest": mutation_toolchain._DistributionScope(
                import_paths=("pytest",),
                source_modules=(("pytest", "pytest/__init__.py"),),
            )
        },
    )
    assert with_injection["file_count"] == changed["file_count"] + 1
    assert with_injection["manifest_sha256"] != changed["manifest_sha256"]


def test_unreviewed_active_dependency_fails_but_extra_dependency_is_inactive(
    tmp_path: Path,
) -> None:
    with pytest.raises(MutationToolchainError, match="not reviewed: pytest -> surprise"):
        _fake_toolchain(tmp_path / "active", requirements=("surprise>=1",))

    identity, _, _ = _fake_toolchain(
        tmp_path / "extra",
        requirements=('surprise>=1; extra == "dev"',),
    )
    assert identity["dependency_closure"] == ["pytest"]


def test_reviewed_but_missing_active_dependency_fails_closed(tmp_path: Path) -> None:
    pytest_scope = mutation_toolchain._DistributionScope(
        import_paths=("pytest",),
        source_modules=(("pytest", "pytest/__init__.py"),),
    )
    missing_scope = mutation_toolchain._DistributionScope(
        import_paths=("missing_dep",),
        source_modules=(("missing_dep", "missing_dep/__init__.py"),),
    )
    with pytest.raises(
        MutationToolchainError,
        match="distribution is not installed exactly once: missing-dep",
    ):
        _fake_toolchain(
            tmp_path,
            requirements=("missing-dep>=1",),
            registry={"pytest": pytest_scope, "missing-dep": missing_scope},
        )


def test_duplicate_distribution_metadata_fails_closed(tmp_path: Path) -> None:
    prefix = tmp_path / "venv"
    site_packages = prefix / "Lib" / "site-packages"
    site_packages.mkdir(parents=True)
    scope = mutation_toolchain._DistributionScope(
        import_paths=("pytest",),
        source_modules=(("pytest", "pytest/__init__.py"),),
    )
    _write_fake_distribution(site_packages, name="pytest", scope=scope)
    _write_fake_distribution(
        site_packages,
        name="pytest",
        scope=scope,
        version="2.0",
        metadata_tag="pytest_second",
    )
    with pytest.raises(MutationToolchainError, match="installed more than once"):
        mutation_toolchain._build_test_toolchain_identity(
            prefix=prefix,
            search_paths=(site_packages,),
            roots=("pytest",),
            registry={"pytest": scope},
        )


def test_distribution_identity_does_not_call_ambient_metadata_enumerator(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected, prefix, site_packages = _fake_toolchain(tmp_path)
    scope = mutation_toolchain._DistributionScope(
        import_paths=("pytest",),
        source_modules=(("pytest", "pytest/__init__.py"),),
    )

    def forbidden(**_kwargs: object) -> object:
        raise AssertionError("ambient metadata enumerator was invoked")

    monkeypatch.setattr(
        mutation_toolchain.metadata,
        "distributions",
        forbidden,
    )
    assert mutation_toolchain._build_test_toolchain_identity(
        prefix=prefix,
        search_paths=(site_packages,),
        roots=("pytest",),
        registry={"pytest": scope},
    ) == expected


def test_metadata_scope_uses_discovered_path_not_record_self_selection(
    tmp_path: Path,
) -> None:
    _, prefix, site_packages = _fake_toolchain(tmp_path)
    info = site_packages / "pytest-1.0.dist-info"
    decoy = site_packages / "record-selected-1.0.dist-info"
    decoy.mkdir()
    (decoy / "sentinel.txt").write_text("not pytest metadata\n", encoding="utf-8")
    (info / "RECORD").write_text(
        "record-selected-1.0.dist-info/sentinel.txt,,\n",
        encoding="utf-8",
    )
    distribution = next(
        item
        for item in metadata.distributions(path=[str(site_packages)])
        if item.metadata["Name"] == "pytest"
    )

    assert mutation_toolchain._metadata_directory(
        distribution,
        prefix=prefix,
    ) == info.resolve(strict=True)

    class AlternateDistribution(metadata.Distribution):
        def read_text(self, filename: str) -> str | None:
            return None

        def locate_file(self, path: str | os.PathLike[str]) -> Path:
            return prefix / Path(path)

    with pytest.raises(MutationToolchainError, match="exact PathDistribution"):
        mutation_toolchain._metadata_directory(
            AlternateDistribution(),
            prefix=prefix,
        )


def test_prefix_startup_files_are_hashed_and_path_injection_fails(
    tmp_path: Path,
) -> None:
    baseline, prefix, site_packages = _fake_toolchain(tmp_path / "sealed")
    (site_packages / "bootstrap.pth").write_text("import os\n", encoding="utf-8")
    (site_packages / "legacy.egg-link").write_text(
        "C:/reviewed/editable/source\n",
        encoding="utf-8",
    )
    (site_packages / "sitecustomize.py").write_text(
        "STARTUP = True\n",
        encoding="utf-8",
    )
    changed = mutation_toolchain._build_test_toolchain_identity(
        prefix=prefix,
        search_paths=(site_packages,),
        roots=("pytest",),
        registry={
            "pytest": mutation_toolchain._DistributionScope(
                import_paths=("pytest",),
                source_modules=(("pytest", "pytest/__init__.py"),),
            )
        },
    )
    startup_names = {Path(item["path"]).name for item in changed["startup"]["files"]}
    assert {"bootstrap.pth", "legacy.egg-link", "sitecustomize.py"}.issubset(
        startup_names
    )
    assert changed["startup"]["import_roots"] == ["os", "sitecustomize"]
    assert changed["manifest_sha256"] != baseline["manifest_sha256"]

    poisoned_prefix = tmp_path / "poisoned" / "venv"
    poisoned_site = poisoned_prefix / "Lib" / "site-packages"
    poisoned_site.mkdir(parents=True)
    scope = mutation_toolchain._DistributionScope(
        import_paths=("pytest",),
        source_modules=(("pytest", "pytest/__init__.py"),),
    )
    _write_fake_distribution(poisoned_site, name="pytest", scope=scope)
    (poisoned_site / "escape.pth").write_text(
        "C:/foreign/toolchain\n",
        encoding="utf-8",
    )
    with pytest.raises(MutationToolchainError, match="path injection is not admitted"):
        mutation_toolchain._build_test_toolchain_identity(
            prefix=poisoned_prefix,
            search_paths=(poisoned_site,),
            roots=("pytest",),
            registry={"pytest": scope},
        )


def test_scope_escape_and_reparse_state_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    escaping = mutation_toolchain._DistributionScope(
        import_paths=("../escape",),
        source_modules=(),
    )
    with pytest.raises(MutationToolchainError, match="safe relative path"):
        _fake_toolchain(tmp_path / "escape", registry={"pytest": escaping})

    _, prefix, site_packages = _fake_toolchain(tmp_path / "reparse")
    monkeypatch.setattr(mutation_toolchain, "_is_reparse", lambda _metadata: True)
    with pytest.raises(MutationToolchainError, match="plain directory"):
        mutation_toolchain._build_test_toolchain_identity(
            prefix=prefix,
            search_paths=(site_packages,),
            roots=("pytest",),
            registry={
                "pytest": mutation_toolchain._DistributionScope(
                    import_paths=("pytest",),
                    source_modules=(("pytest", "pytest/__init__.py"),),
                )
            },
        )


def test_casefold_collisions_fail_within_one_distribution() -> None:
    claims: dict[str, tuple[str, str]] = {}
    mutation_toolchain._claim_unique_toolchain_path(
        claims,
        distribution_name="pytest",
        relative="Lib/site-packages/pytest/CaseProbe.py",
    )
    with pytest.raises(MutationToolchainError, match="collide case-insensitively"):
        mutation_toolchain._claim_unique_toolchain_path(
            claims,
            distribution_name="pytest",
            relative="Lib/site-packages/pytest/caseprobe.py",
        )


def test_in_prefix_symlink_cannot_disappear_during_resolution(
    tmp_path: Path,
) -> None:
    prefix = tmp_path / "prefix"
    prefix.mkdir()
    target = prefix / "target.txt"
    target.write_text("sealed\n", encoding="utf-8")
    alias = prefix / "alias.txt"
    _symlink_or_skip(alias, target, target_is_directory=False)

    with pytest.raises(MutationToolchainError, match="link or reparse point"):
        mutation_toolchain._plain_existing_under(
            prefix,
            alias,
            label="in-prefix symlink canary",
        )


def test_public_identity_rejects_a_sys_path_alias_into_the_venv(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prefix = Path(sys.prefix).resolve(strict=True)
    site_packages = next(
        path
        for path in mutation_toolchain._distribution_search_paths(prefix)
        if path.name.casefold() == "site-packages"
    )
    alias = tmp_path / "aliased-site-packages"
    _symlink_or_skip(alias, site_packages, target_is_directory=True)
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    monkeypatch.setattr(sys, "dont_write_bytecode", True)
    monkeypatch.setattr(sys, "pycache_prefix", str(tmp_path / "isolated-pycache"))
    monkeypatch.setattr(sys, "path", [str(alias), *sys.path])

    with pytest.raises(MutationToolchainError, match="sys.path alias crosses"):
        project_test_toolchain_identity(
            snapshot,
            lru_runtime_context=_active_lru_runtime_context(),
        )


def test_public_identity_rejects_an_aliased_sys_prefix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = tmp_path / "aliased-project"
    project.mkdir()
    alias = project / ".venv"
    _symlink_or_skip(
        alias,
        Path(sys.prefix).resolve(strict=True),
        target_is_directory=True,
    )
    monkeypatch.setattr(sys, "prefix", str(alias))
    monkeypatch.setattr(sys, "dont_write_bytecode", True)
    monkeypatch.setattr(sys, "pycache_prefix", str(tmp_path / "isolated-pycache"))

    with pytest.raises(MutationToolchainError, match="prefix is not a plain directory"):
        project_test_toolchain_identity(
            project,
            lru_runtime_context=_active_lru_runtime_context(),
        )


def test_hard_linked_toolchain_file_fails_closed(tmp_path: Path) -> None:
    prefix = tmp_path / "prefix"
    prefix.mkdir()
    source = prefix / "source.py"
    source.write_text("SEALED = True\n", encoding="utf-8")
    alias = prefix / "alias.py"
    try:
        os.link(source, alias)
    except OSError as exc:
        unsupported = {
            errno.EACCES,
            errno.EPERM,
            getattr(errno, "ENOTSUP", -1),
            getattr(errno, "EOPNOTSUPP", -1),
        }
        if exc.errno in unsupported:
            pytest.skip("the current filesystem cannot create a hard link")
        raise

    with pytest.raises(MutationToolchainError, match="must not be hard-linked"):
        mutation_toolchain._stable_file_identity(
            prefix,
            source,
            label="hard-link canary",
        )


def test_ambient_or_venv_local_pycache_policy_is_refused(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prefix = Path(sys.prefix).resolve(strict=True)
    monkeypatch.setattr(sys, "dont_write_bytecode", False)
    with pytest.raises(MutationToolchainError, match="writes to be disabled"):
        mutation_toolchain._require_isolated_bytecode(prefix)

    monkeypatch.setattr(sys, "dont_write_bytecode", True)
    monkeypatch.setattr(
        sys,
        "pycache_prefix",
        str(prefix / "Lib" / "site-packages" / "ambient-cache"),
    )
    with pytest.raises(MutationToolchainError, match="outside the project .venv"):
        mutation_toolchain._require_isolated_bytecode(prefix)

    populated_cache = tmp_path / "populated-pycache"
    populated_cache.mkdir()
    (populated_cache / "poison.pyc").write_bytes(b"not trusted bytecode")
    monkeypatch.setattr(sys, "pycache_prefix", str(populated_cache))
    with pytest.raises(MutationToolchainError, match="absent or an empty plain"):
        mutation_toolchain._require_isolated_bytecode(prefix)

    empty_cache = tmp_path / "empty-pycache"
    empty_cache.mkdir()
    monkeypatch.setattr(sys, "pycache_prefix", str(empty_cache))
    mutation_toolchain._require_isolated_bytecode(prefix)


def test_snapshot_child_can_hash_the_external_project_venv(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    monkeypatch.setattr(sys, "dont_write_bytecode", True)
    monkeypatch.setattr(sys, "pycache_prefix", str(tmp_path / "isolated-pycache"))
    identity = project_test_toolchain_identity(
        snapshot,
        lru_runtime_context=_active_lru_runtime_context(),
    )
    assert identity["prefix"] == str(Path(sys.prefix).resolve(strict=True))
    assert [item["name"] for item in identity["distributions"]] == sorted(
        set(identity["dependency_closure"])
        | set(identity["host_dependency_closure"])
    )


def test_structural_validator_rejects_manifest_and_module_tampering() -> None:
    identity = _current_identity()
    assert validate_test_toolchain_identity(identity) is identity

    changed_distribution = deepcopy(identity)
    changed_distribution["distributions"][0]["sha256"] = "0" * 64
    with pytest.raises(MutationToolchainError, match="manifest digest is invalid"):
        validate_test_toolchain_identity(changed_distribution)

    changed_module = deepcopy(identity)
    changed_module["modules"][0]["path"] = "../foreign.py"
    with pytest.raises(MutationToolchainError, match="safe relative path"):
        validate_test_toolchain_identity(changed_module)

    changed_startup = deepcopy(identity)
    changed_startup["startup"]["files"][0]["sha256"] = "0" * 64
    with pytest.raises(MutationToolchainError, match="startup digest is invalid"):
        validate_test_toolchain_identity(changed_startup)


def test_loaded_module_attestation_rejects_foreign_shadow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identity = _current_identity()
    foreign_path = tmp_path / "yaml.py"
    foreign_path.write_text("FOREIGN = True\n", encoding="utf-8")
    foreign = ModuleType("yaml")
    foreign.__file__ = str(foreign_path)
    foreign.__spec__ = spec_from_loader(
        "yaml",
        SourceFileLoader("yaml", str(foreign_path)),
    )
    monkeypatch.setitem(sys.modules, "yaml", foreign)
    with pytest.raises(
        MutationToolchainError,
        match="captured prefix module binding changed: yaml",
    ):
        _loaded_test_toolchain_attestation(identity)


def test_loaded_module_attestation_rejects_deleted_captured_module(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "pygments.lexers.diff"
    original = import_module(module_name)
    prefix = tmp_path.resolve(strict=True)
    monkeypatch.setattr(mutation_toolchain, "_RUNTIME_PREFIX_SENTINELS", {})
    mutation_toolchain._verify_or_seal_prefix_runtime(
        prefix,
        attestation_context={"runtime_modules": ((module_name, original),)},
    )

    with pytest.raises(MutationToolchainError, match="module set changed"):
        mutation_toolchain._verify_or_seal_prefix_runtime(
            prefix,
            attestation_context={"runtime_modules": ()},
        )

    clone = ModuleType(original.__name__)
    vars(clone).update(vars(original))
    monkeypatch.setitem(sys.modules, module_name, clone)
    with pytest.raises(MutationToolchainError, match="module binding changed"):
        mutation_toolchain._verify_or_seal_prefix_runtime(
            prefix,
            attestation_context={"runtime_modules": ((module_name, clone),)},
        )
    monkeypatch.setitem(sys.modules, module_name, original)

    alias = "phase11_late_prefix_alias"
    assert alias not in sys.modules
    monkeypatch.setitem(sys.modules, alias, original)
    with pytest.raises(MutationToolchainError, match="module set changed"):
        mutation_toolchain._verify_or_seal_prefix_runtime(
            prefix,
            attestation_context={
                "runtime_modules": (
                    (alias, original),
                    (module_name, original),
                )
            },
        )


def test_eager_prefix_baseline_rejects_changes_before_first_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prefix = mutation_toolchain._DETERMINISTIC_IMPORT_PREFIX
    modules = mutation_toolchain._PREFIX_MODULES_AFTER_DETERMINISTIC_IMPORTS
    assert modules
    assert any(name == "packaging" for name, _module in modules)
    monkeypatch.setattr(mutation_toolchain, "_RUNTIME_PREFIX_SENTINELS", {})

    mutation_toolchain._verify_or_seal_prefix_runtime(
        prefix,
        attestation_context={"runtime_modules": modules},
    )

    original_name, original = modules[0]
    alias = "phase11_preseal_prefix_alias"
    assert alias not in sys.modules
    monkeypatch.setitem(sys.modules, alias, original)
    mutation_toolchain._RUNTIME_PREFIX_SENTINELS.clear()
    with pytest.raises(MutationToolchainError, match="module set changed"):
        mutation_toolchain._verify_or_seal_prefix_runtime(
            prefix,
            attestation_context={
                "runtime_modules": tuple(
                    sorted((*modules, (alias, original)), key=lambda item: item[0])
                )
            },
        )

    mutation_toolchain._RUNTIME_PREFIX_SENTINELS.clear()
    with pytest.raises(MutationToolchainError, match="module set changed"):
        mutation_toolchain._verify_or_seal_prefix_runtime(
            prefix,
            attestation_context={"runtime_modules": modules[1:]},
        )

    clone = ModuleType(original.__name__)
    vars(clone).update(vars(original))
    monkeypatch.setitem(sys.modules, original_name, clone)
    rebound = tuple(
        (name, clone if name == original_name else module)
        for name, module in modules
    )
    mutation_toolchain._RUNTIME_PREFIX_SENTINELS.clear()
    with pytest.raises(MutationToolchainError, match="module binding changed"):
        mutation_toolchain._verify_or_seal_prefix_runtime(
            prefix,
            attestation_context={"runtime_modules": rebound},
        )


def test_source_import_manifest_rejects_exact_provider_edge_swaps(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "import_binding_probe.py"
    source_path.write_text(
        "import pathlib as paths\n"
        "from pathlib import Path as PathAlias\n"
        "def marker():\n"
        "    return 1\n",
        encoding="utf-8",
    )
    source = source_path.read_bytes()
    module = ModuleType("import_binding_probe")
    module.__file__ = str(source_path)
    module.__package__ = ""
    module.__spec__ = spec_from_loader(
        module.__name__,
        SourceFileLoader(module.__name__, str(source_path)),
    )
    exec(
        compile(
            source,
            str(source_path),
            "exec",
            dont_inherit=True,
            optimize=sys.flags.optimize,
        ),
        vars(module),
    )
    expected = mutation_toolchain._source_code_manifest(
        source,
        source_path=source_path,
    )
    mutation_toolchain._verify_loaded_source_code(
        module,
        source=source,
        source_path=source_path,
        variant="raw",
        expected_manifest=expected,
    )

    original_paths = module.paths
    try:
        module.paths = sys
        with pytest.raises(
            MutationToolchainError,
            match="loaded source import binding changed",
        ):
            mutation_toolchain._verify_loaded_source_code(
                module,
                source=source,
                source_path=source_path,
                variant="raw",
                expected_manifest=expected,
            )
    finally:
        module.paths = original_paths

    original_path_alias = module.PathAlias
    try:
        module.PathAlias = PurePath
        with pytest.raises(
            MutationToolchainError,
            match="loaded source import binding changed",
        ):
            mutation_toolchain._verify_loaded_source_code(
                module,
                source=source,
                source_path=source_path,
                variant="raw",
                expected_manifest=expected,
            )
    finally:
        module.PathAlias = original_path_alias


def test_source_class_manifest_rejects_same_qualname_shape_clone(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "class_binding_probe.py"
    source_path.write_text(
        "class Probe:\n"
        "    state = 1\n"
        "    def method(self):\n"
        "        return 1\n"
        "    @property\n"
        "    def value(self):\n"
        "        return 1\n",
        encoding="utf-8",
    )
    source = source_path.read_bytes()
    module = ModuleType("class_binding_probe")
    module.__file__ = str(source_path)
    module.__package__ = ""
    module.__spec__ = spec_from_loader(
        module.__name__,
        SourceFileLoader(module.__name__, str(source_path)),
    )
    exec(
        compile(
            source,
            str(source_path),
            "exec",
            dont_inherit=True,
            optimize=sys.flags.optimize,
        ),
        vars(module),
    )
    expected = mutation_toolchain._source_code_manifest(
        source,
        source_path=source_path,
    )
    mutation_toolchain._verify_loaded_source_code(
        module,
        source=source,
        source_path=source_path,
        variant="raw",
        expected_manifest=expected,
    )

    original = module.Probe

    class EvilMeta(type):
        pass

    namespace = {
        name: value
        for name, value in vars(original).items()
        if name not in {"__dict__", "__weakref__"}
    }
    namespace["state"] = 2
    namespace["value"] = property(original.value.fget, doc="changed descriptor")
    evil = EvilMeta("Probe", (dict,), namespace)
    evil.__module__ = module.__name__
    evil.__qualname__ = "Probe"
    try:
        module.Probe = evil
        with pytest.raises(
            MutationToolchainError,
            match=(
                "loaded source class "
                "(binding|hierarchy|metaclass|data|descriptor|namespace) changed"
            ),
        ):
            mutation_toolchain._verify_loaded_source_code(
                module,
                source=source,
                source_path=source_path,
                variant="raw",
                expected_manifest=expected,
                require_complete=False,
            )
    finally:
        module.Probe = original


def test_first_loaded_attestation_rejects_same_qualname_class_tamper(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_path = tmp_path / "preseal_class_probe.py"
    source_path.write_text(
        "class Probe:\n"
        "    state = 1\n"
        "    def method(self):\n"
        "        return 1\n"
        "    @property\n"
        "    def value(self):\n"
        "        return 1\n",
        encoding="utf-8",
    )
    source = source_path.read_bytes()
    module = ModuleType("preseal_class_probe")
    module.__file__ = str(source_path)
    module.__package__ = ""
    module.__spec__ = spec_from_loader(
        module.__name__,
        SourceFileLoader(module.__name__, str(source_path)),
    )
    exec(
        compile(
            source,
            str(source_path),
            "exec",
            dont_inherit=True,
            optimize=sys.flags.optimize,
        ),
        vars(module),
    )
    original = module.Probe

    class EvilMeta(type):
        pass

    namespace = {
        name: value
        for name, value in vars(original).items()
        if name not in {"__dict__", "__weakref__"}
    }
    namespace["state"] = 2
    namespace["value"] = property(original.value.fget, doc="changed descriptor")
    evil = EvilMeta("Probe", (dict,), namespace)
    evil.__module__ = module.__name__
    evil.__qualname__ = "Probe"
    module.Probe = evil
    monkeypatch.setattr(mutation_toolchain, "_RUNTIME_SOURCE_SENTINELS", {})

    with pytest.raises(
        MutationToolchainError,
        match="loaded source class (hierarchy|metaclass|data|descriptor) changed",
    ):
        mutation_toolchain._verify_loaded_source_code(
            module,
            source=source,
            source_path=source_path,
            variant="raw",
            expected_manifest=mutation_toolchain._source_code_manifest(
                source,
                source_path=source_path,
            ),
            require_complete=False,
        )


def test_class_policy_excludes_control_flow_mutation_but_binds_direct_scalar(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "class_control_flow_policy.py"
    source_path.write_text(
        "class Probe:\n"
        "    stable = 7\n"
        "    reassigned = 1\n"
        "    if True:\n"
        "        reassigned = 2\n"
        "    multiplied = 2.0\n"
        "    while multiplied < 16.0:\n"
        "        multiplied *= multiplied\n"
        "    collected = []\n"
        "    if True:\n"
        "        collected.append('value')\n"
        "    def values(self):\n"
        "        return self.stable, self.reassigned, self.multiplied\n",
        encoding="utf-8",
    )
    source = source_path.read_bytes()
    module = ModuleType("class_control_flow_policy")
    module.__file__ = str(source_path)
    module.__package__ = ""
    module.__spec__ = spec_from_loader(
        module.__name__,
        SourceFileLoader(module.__name__, str(source_path)),
    )
    exec(
        compile(
            source,
            str(source_path),
            "exec",
            dont_inherit=True,
            optimize=sys.flags.optimize,
        ),
        vars(module),
    )
    _entries, policy, _bindings = (
        mutation_toolchain._sealed_source_variant_payload(
            source,
            source_path=source_path,
            variant="raw",
        )
    )
    shape = next(item for item in policy.classes if item.path == ("Probe",))
    assert {name for name, _value in shape.literal_members} == {"stable"}

    expected = mutation_toolchain._source_code_manifest(
        source,
        source_path=source_path,
    )
    mutation_toolchain._verify_loaded_source_code(
        module,
        source=source,
        source_path=source_path,
        variant="raw",
        expected_manifest=expected,
    )
    module.Probe.stable = 8
    with pytest.raises(
        MutationToolchainError,
        match="loaded source class data changed",
    ):
        mutation_toolchain._verify_loaded_source_code(
            module,
            source=source,
            source_path=source_path,
            variant="raw",
            expected_manifest=expected,
        )


@pytest.mark.parametrize("require_complete", [True, False])
def test_conditional_class_candidate_uses_its_own_source_shape(
    tmp_path: Path,
    require_complete: bool,
) -> None:
    source_path = tmp_path / "conditional_class_candidate.py"
    active_platform = sys.platform
    inactive_platform = "__phase11_inactive_platform__"
    source = (
        "import sys\n"
        f"if sys.platform == {active_platform!r}:\n"
        "    class Probe:\n"
        "        marker = 'active'\n"
        "        active_only = 1\n"
        "else:\n"
        "    class Probe:\n"
        "        marker = 'inactive'\n"
        "        inactive_only = 2\n"
    ).encode("utf-8")
    source_path.write_bytes(source)
    module = ModuleType("conditional_class_candidate")
    module.__file__ = str(source_path)
    module.__package__ = ""
    module.__spec__ = spec_from_loader(
        module.__name__,
        SourceFileLoader(module.__name__, str(source_path)),
    )
    exec(
        compile(
            source,
            str(source_path),
            "exec",
            dont_inherit=True,
            optimize=sys.flags.optimize,
        ),
        vars(module),
    )
    expected = mutation_toolchain._source_code_manifest(
        source,
        source_path=source_path,
    )
    mutation_toolchain._verify_loaded_source_code(
        module,
        source=source,
        source_path=source_path,
        variant="raw",
        expected_manifest=expected,
        require_complete=require_complete,
    )

    inactive_namespace: dict[str, object] = {
        "__name__": module.__name__,
        "__file__": str(source_path),
        "__package__": "",
        "__spec__": module.__spec__,
    }
    original_platform = sys.platform
    try:
        sys.platform = inactive_platform
        exec(
            compile(
                source,
                str(source_path),
                "exec",
                dont_inherit=True,
                optimize=sys.flags.optimize,
            ),
            inactive_namespace,
        )
    finally:
        sys.platform = original_platform
    inactive = inactive_namespace["Probe"]
    assert inspect.isclass(inactive)
    assert vars(inactive)["marker"] == "inactive"
    active = module.Probe
    module.Probe = inactive
    try:
        with pytest.raises(
            MutationToolchainError,
            match="loaded source class (namespace key set|data) changed",
        ):
            mutation_toolchain._verify_loaded_source_code(
                module,
                source=source,
                source_path=source_path,
                variant="raw",
                expected_manifest=expected,
                require_complete=require_complete,
            )
    finally:
        module.Probe = active


def test_class_namespace_derives_executed_version_branch_and_rejects_rogue_key(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "class_version_branch_policy.py"
    source_path.write_text(
        "import sys\n"
        "class Probe:\n"
        "    if sys.version_info >= (3, 10):\n"
        "        def admitted(self):\n"
        "            return True\n"
        "    if sys.version_info < (3, 0):\n"
        "        def unavailable(self):\n"
        "            return False\n",
        encoding="utf-8",
    )
    source = source_path.read_bytes()
    module = ModuleType("class_version_branch_policy")
    module.__file__ = str(source_path)
    module.__package__ = ""
    module.__spec__ = spec_from_loader(
        module.__name__,
        SourceFileLoader(module.__name__, str(source_path)),
    )
    exec(
        compile(
            source,
            str(source_path),
            "exec",
            dont_inherit=True,
            optimize=sys.flags.optimize,
        ),
        vars(module),
    )
    _entries, policy, _bindings = (
        mutation_toolchain._sealed_source_variant_payload(
            source,
            source_path=source_path,
            variant="raw",
        )
    )
    shape = next(item for item in policy.classes if item.path == ("Probe",))
    assert shape.conditional_namespace_complete
    assert {member.name for member in shape.conditional_members} == {
        "admitted",
        "unavailable",
    }

    expected = mutation_toolchain._source_code_manifest(
        source,
        source_path=source_path,
    )
    mutation_toolchain._verify_loaded_source_code(
        module,
        source=source,
        source_path=source_path,
        variant="raw",
        expected_manifest=expected,
        require_complete=False,
    )

    module.Probe._phase11_rogue_key = 73
    try:
        with pytest.raises(
            MutationToolchainError,
            match="loaded source class namespace key set changed",
        ):
            mutation_toolchain._verify_loaded_source_code(
                module,
                source=source,
                source_path=source_path,
                variant="raw",
                expected_manifest=expected,
                require_complete=False,
            )
    finally:
        del module.Probe._phase11_rogue_key

    module.Probe.unavailable = module.Probe.admitted
    try:
        with pytest.raises(
            MutationToolchainError,
            match=(
                "(?:loaded source class namespace key set changed|"
                "inactive source binding is unexpectedly present)"
            ),
        ):
            mutation_toolchain._verify_loaded_source_code(
                module,
                source=source,
                source_path=source_path,
                variant="raw",
                expected_manifest=expected,
                require_complete=False,
            )
    finally:
        del module.Probe.unavailable


def test_class_namespace_derives_exact_sys_platform_branch(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "class_platform_branch_policy.py"
    source_path.write_text(
        "import sys\n"
        "class Probe:\n"
        "    if sys.platform == 'win32':\n"
        "        def windows_member(self):\n"
        "            return True\n"
        "    if sys.platform != 'win32':\n"
        "        def non_windows_member(self):\n"
        "            return True\n",
        encoding="utf-8",
    )
    source = source_path.read_bytes()
    module = ModuleType("class_platform_branch_policy")
    module.__file__ = str(source_path)
    module.__package__ = ""
    module.__spec__ = spec_from_loader(
        module.__name__,
        SourceFileLoader(module.__name__, str(source_path)),
    )
    exec(
        compile(
            source,
            str(source_path),
            "exec",
            dont_inherit=True,
            optimize=sys.flags.optimize,
        ),
        vars(module),
    )
    _entries, policy, _bindings = (
        mutation_toolchain._sealed_source_variant_payload(
            source,
            source_path=source_path,
            variant="raw",
        )
    )
    shape = next(item for item in policy.classes if item.path == ("Probe",))
    assert shape.conditional_namespace_complete
    assert {member.name for member in shape.conditional_members} == {
        "non_windows_member",
        "windows_member",
    }

    expected = mutation_toolchain._source_code_manifest(
        source,
        source_path=source_path,
    )
    mutation_toolchain._verify_loaded_source_code(
        module,
        source=source,
        source_path=source_path,
        variant="raw",
        expected_manifest=expected,
        require_complete=False,
    )

    original_sys = module.sys
    module.sys = ModuleType("sys")
    try:
        with pytest.raises(
            MutationToolchainError,
            match="loaded source (class platform provider|import binding) changed",
        ):
            mutation_toolchain._verify_loaded_source_code(
                module,
                source=source,
                source_path=source_path,
                variant="raw",
                expected_manifest=expected,
                require_complete=False,
            )
    finally:
        module.sys = original_sys


def test_pytest_pathlib_is_same_uses_exact_platform_prefix_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "_pytest.pathlib"
    module = import_module(module_name)
    policy = _loaded_source_policy(module)
    binding = next(
        item for item in policy.bindings if item.path == ("_is_same",)
    )
    assert len(binding.candidates) == 2
    assert tuple(
        (candidate.guards_complete, candidate.guards)
        for candidate in binding.candidates
    ) == (
        (
            True,
            (
                mutation_toolchain._SourcePlatformGuard(
                    "startswith",
                    "win",
                    True,
                ),
            ),
        ),
        (
            True,
            (
                mutation_toolchain._SourcePlatformGuard(
                    "startswith",
                    "win",
                    False,
                ),
            ),
        ),
    )

    active = mutation_toolchain._active_source_binding_candidate(
        module,
        policy=policy,
        binding=binding,
    )
    assert active is not None
    assert active.first_line == vars(module)["_is_same"].__code__.co_firstlineno

    monkeypatch.setattr(mutation_toolchain, "_RUNTIME_SOURCE_SENTINELS", {})
    _verify_selected_binding(
        module_name,
        "_is_same",
        admitted_module_names=(module_name,),
    )
    assert mutation_toolchain._RUNTIME_SOURCE_SENTINELS == {}


def test_pytest_pathlib_platform_prefix_rejects_copied_sys_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = import_module("_pytest.pathlib")
    policy = _loaded_source_policy(module)
    binding = next(
        item for item in policy.bindings if item.path == ("_is_same",)
    )
    copied_sys = ModuleType("sys")
    vars(copied_sys).update(vars(sys))
    monkeypatch.setattr(module, "sys", copied_sys)
    monkeypatch.setitem(sys.modules, "sys", copied_sys)

    with pytest.raises(MutationToolchainError, match="platform provider changed"):
        mutation_toolchain._active_source_binding_candidate(
            module,
            policy=policy,
            binding=binding,
        )


def test_pytest_pathlib_platform_prefix_rejects_coordinated_sys_copy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = import_module("_pytest.pathlib")
    policy = _loaded_source_policy(module)
    binding = next(
        item for item in policy.bindings if item.path == ("_is_same",)
    )
    copied_sys = ModuleType("sys")
    vars(copied_sys).update(vars(sys))
    monkeypatch.setattr(module, "sys", copied_sys)
    monkeypatch.setattr(mutation_toolchain, "sys", copied_sys)
    monkeypatch.setitem(sys.modules, "sys", copied_sys)

    with pytest.raises(
        MutationToolchainError,
        match="source import provider module changed: sys",
    ):
        mutation_toolchain._active_source_binding_candidate(
            module,
            policy=policy,
            binding=binding,
        )


def test_pytest_pathlib_platform_prefix_rejects_equal_distinct_platform(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = import_module("_pytest.pathlib")
    policy = _loaded_source_policy(module)
    binding = next(
        item for item in policy.bindings if item.path == ("_is_same",)
    )
    original_platform = sys.platform
    equal_distinct_platform = (original_platform + "\0")[:-1]
    assert equal_distinct_platform == original_platform
    assert equal_distinct_platform is not original_platform
    monkeypatch.setattr(sys, "platform", equal_distinct_platform)

    with pytest.raises(MutationToolchainError, match=r"sys\.platform"):
        mutation_toolchain._active_source_binding_candidate(
            module,
            policy=policy,
            binding=binding,
        )


def test_pytest_pathlib_platform_prefix_rejects_hostile_callback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = import_module("_pytest.pathlib")
    policy = _loaded_source_policy(module)
    binding = next(
        item for item in policy.bindings if item.path == ("_is_same",)
    )
    callbacks: list[str] = []

    class HostilePlatform(str):
        def startswith(self, *_args: object, **_kwargs: object) -> bool:
            callbacks.append("startswith")
            raise AssertionError("hostile platform callback invoked")

    monkeypatch.setattr(sys, "platform", HostilePlatform(sys.platform))

    with pytest.raises(MutationToolchainError, match=r"sys\.platform"):
        mutation_toolchain._active_source_binding_candidate(
            module,
            policy=policy,
            binding=binding,
        )
    assert callbacks == []


@pytest.mark.parametrize(
    ("prelude", "condition"),
    (
        ("import sys", 'sys.platform.endswith("win")'),
        ("import sys", 'sys.platform.startswith(("win",))'),
        ("import sys", 'sys.platform.startswith("win", 0)'),
        ("import sys", 'sys.platform.startswith(prefix="win")'),
        ("import sys\nplatform = sys.platform", 'platform.startswith("win")'),
        ("import sys as system", 'system.platform.startswith("win")'),
        ("from sys import platform", 'platform.startswith("win")'),
        (
            "import sys\nprefix_check = sys.platform.startswith",
            'prefix_check("win")',
        ),
    ),
)
def test_source_platform_prefix_variants_remain_unsupported(
    tmp_path: Path,
    prelude: str,
    condition: str,
) -> None:
    source_path = tmp_path / "platform_prefix_guard_variant.py"
    source = (
        f"{prelude}\n"
        f"if {condition}:\n"
        "    def target():\n"
        "        return True\n"
        "else:\n"
        "    def target():\n"
        "        return False\n"
    ).encode("utf-8")
    source_path.write_bytes(source)
    _entries, _policy, bindings = (
        mutation_toolchain._sealed_source_variant_payload(
            source,
            source_path=source_path,
            variant="raw",
        )
    )
    binding = next(item for item in bindings if item["path"] == "target")
    assert len(binding["candidates"]) == 2
    assert all(
        candidate["guards_complete"] is False
        and candidate["guards"][0]["expression"]["kind"] == "unsupported"
        for candidate in binding["candidates"]
    )


def test_source_negated_platform_prefix_remains_fail_closed(tmp_path: Path) -> None:
    source_path = tmp_path / "negated_platform_prefix_guard.py"
    source = (
        "import sys\n"
        'if not sys.platform.startswith("win"):\n'
        "    def target():\n"
        "        return True\n"
        "else:\n"
        "    def target():\n"
        "        return False\n"
    ).encode("utf-8")
    source_path.write_bytes(source)
    module = ModuleType("negated_platform_prefix_guard")
    module.__file__ = str(source_path)
    module.__package__ = ""
    module.__spec__ = spec_from_loader(
        module.__name__,
        SourceFileLoader(module.__name__, str(source_path)),
    )
    exec(
        compile(
            source,
            str(source_path),
            "exec",
            dont_inherit=True,
            optimize=sys.flags.optimize,
        ),
        vars(module),
    )
    _entries, policy, _bindings = (
        mutation_toolchain._sealed_source_variant_payload(
            source,
            source_path=source_path,
            variant="raw",
        )
    )
    binding = next(item for item in policy.bindings if item.path == ("target",))
    guard = binding.candidates[0].guards[0]
    assert type(guard) is mutation_toolchain._SourceExpressionGuard
    assert guard.expression.kind == "not"
    assert guard.expression.payload.kind == "unsupported"

    with pytest.raises(
        MutationToolchainError,
        match="sealed source conditional expression is unsupported",
    ):
        mutation_toolchain._active_source_binding_candidate(
            module,
            policy=policy,
            binding=binding,
        )


def test_pytest_pathlib_platform_prefix_rejects_inactive_candidate_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "_pytest.pathlib"
    module = import_module(module_name)
    source_path = Path(str(module.__file__)).resolve(strict=True)
    source = source_path.read_bytes()
    policy = _loaded_source_policy(module)
    binding = next(
        item for item in policy.bindings if item.path == ("_is_same",)
    )
    active = vars(module)["_is_same"]
    inactive = next(
        candidate
        for candidate in binding.candidates
        if candidate.first_line != active.__code__.co_firstlineno
    )
    inactive_code = _compiled_source_candidate_code(
        source,
        source_path=source_path,
        qualname=inactive.qualname,
        first_line=inactive.first_line,
    )
    monkeypatch.setattr(mutation_toolchain, "_RUNTIME_SOURCE_SENTINELS", {})
    _verify_selected_binding(
        module_name,
        "_is_same",
        admitted_module_names=(module_name,),
    )
    monkeypatch.setattr(active, "__code__", inactive_code)

    with pytest.raises(MutationToolchainError, match="callable binding changed"):
        _verify_selected_binding(
            module_name,
            "_is_same",
            admitted_module_names=(module_name,),
        )
    assert mutation_toolchain._RUNTIME_SOURCE_SENTINELS == {}


@pytest.mark.parametrize(
    ("guard_import", "guard_expression", "binding_name"),
    [
        ("from typing import TYPE_CHECKING", "TYPE_CHECKING", "TYPE_CHECKING"),
        ("import typing", "typing.TYPE_CHECKING", "typing"),
    ],
)
def test_class_namespace_derives_exact_typing_only_branch(
    tmp_path: Path,
    guard_import: str,
    guard_expression: str,
    binding_name: str,
) -> None:
    source_path = tmp_path / f"class_type_checking_{binding_name}.py"
    source_path.write_text(
        f"{guard_import}\n"
        "class Probe:\n"
        f"    if {guard_expression}:\n"
        "        def unavailable(self):\n"
        "            return True\n"
        "    def admitted(self):\n"
        "        return True\n",
        encoding="utf-8",
    )
    source = source_path.read_bytes()
    module = ModuleType(f"class_type_checking_{binding_name}")
    module.__file__ = str(source_path)
    module.__package__ = ""
    module.__spec__ = spec_from_loader(
        module.__name__,
        SourceFileLoader(module.__name__, str(source_path)),
    )
    exec(
        compile(
            source,
            str(source_path),
            "exec",
            dont_inherit=True,
            optimize=sys.flags.optimize,
        ),
        vars(module),
    )
    _entries, policy, _bindings = (
        mutation_toolchain._sealed_source_variant_payload(
            source,
            source_path=source_path,
            variant="raw",
        )
    )
    shape = next(item for item in policy.classes if item.path == ("Probe",))
    assert shape.conditional_namespace_complete
    assert {member.name for member in shape.conditional_members} == {
        "unavailable"
    }

    expected = mutation_toolchain._source_code_manifest(
        source,
        source_path=source_path,
    )
    mutation_toolchain._verify_loaded_source_code(
        module,
        source=source,
        source_path=source_path,
        variant="raw",
        expected_manifest=expected,
        require_complete=False,
    )

    original_binding = vars(module)[binding_name]
    vars(module)[binding_name] = (
        True if binding_name == "TYPE_CHECKING" else ModuleType("typing")
    )
    try:
        with pytest.raises(
            MutationToolchainError,
            match=(
                "loaded source (class TYPE_CHECKING(?: import provider)?|"
                "import binding) changed"
            ),
        ):
            mutation_toolchain._verify_loaded_source_code(
                module,
                source=source,
                source_path=source_path,
                variant="raw",
                expected_manifest=expected,
                require_complete=False,
            )
    finally:
        vars(module)[binding_name] = original_binding


def test_class_namespace_unknown_new_conditional_member_fails_closed(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "class_unknown_branch_policy.py"
    source_path.write_text(
        "class Probe:\n"
        "    if True:\n"
        "        def dynamic_member(self):\n"
        "            return True\n",
        encoding="utf-8",
    )
    source = source_path.read_bytes()
    module = ModuleType("class_unknown_branch_policy")
    module.__file__ = str(source_path)
    module.__package__ = ""
    module.__spec__ = spec_from_loader(
        module.__name__,
        SourceFileLoader(module.__name__, str(source_path)),
    )
    exec(
        compile(
            source,
            str(source_path),
            "exec",
            dont_inherit=True,
            optimize=sys.flags.optimize,
        ),
        vars(module),
    )
    _entries, policy, _bindings = (
        mutation_toolchain._sealed_source_variant_payload(
            source,
            source_path=source_path,
            variant="raw",
        )
    )
    shape = next(item for item in policy.classes if item.path == ("Probe",))
    assert not shape.conditional_namespace_complete

    with pytest.raises(
        MutationToolchainError,
        match="loaded source class namespace cannot be derived from sealed source",
    ):
        mutation_toolchain._verify_loaded_source_code(
            module,
            source=source,
            source_path=source_path,
            variant="raw",
            expected_manifest=mutation_toolchain._source_code_manifest(
                source,
                source_path=source_path,
            ),
            require_complete=False,
        )


def test_source_abc_registry_shape_is_bound_without_user_callbacks(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "source_abc_policy.py"
    source_path.write_text(
        "from abc import ABC, abstractmethod\n"
        "class Probe(ABC):\n"
        "    @abstractmethod\n"
        "    def value(self):\n"
        "        raise NotImplementedError\n",
        encoding="utf-8",
    )
    source = source_path.read_bytes()
    module = ModuleType("source_abc_policy")
    module.__file__ = str(source_path)
    module.__package__ = ""
    module.__spec__ = spec_from_loader(
        module.__name__,
        SourceFileLoader(module.__name__, str(source_path)),
    )
    exec(
        compile(
            source,
            str(source_path),
            "exec",
            dont_inherit=True,
            optimize=sys.flags.optimize,
        ),
        vars(module),
    )
    expected = mutation_toolchain._source_code_manifest(
        source,
        source_path=source_path,
    )
    mutation_toolchain._verify_loaded_source_code(
        module,
        source=source,
        source_path=source_path,
        variant="raw",
        expected_manifest=expected,
        require_complete=False,
    )

    callbacks = {"eq": 0, "hash": 0, "repr": 0}

    class NoisyMeta(type):
        def __eq__(cls, other: object) -> bool:
            callbacks["eq"] += 1
            return cls is other

        def __hash__(cls) -> int:
            callbacks["hash"] += 1
            return type.__hash__(cls)

        def __repr__(cls) -> str:
            callbacks["repr"] += 1
            return type.__repr__(cls)

    class Virtual(metaclass=NoisyMeta):
        pass

    module.Probe.register(Virtual)
    callbacks.update(eq=0, hash=0, repr=0)
    with pytest.raises(
        MutationToolchainError,
        match=r"loaded source class namespace changed: .*Probe\._abc_impl",
    ):
        mutation_toolchain._verify_loaded_source_code(
            module,
            source=source,
            source_path=source_path,
            variant="raw",
            expected_manifest=expected,
            require_complete=False,
        )
    assert callbacks == {"eq": 0, "hash": 0, "repr": 0}


def test_source_abc_cache_only_transition_is_visible(tmp_path: Path) -> None:
    source_path = tmp_path / "source_abc_cache_policy.py"
    source_path.write_text(
        "from abc import ABC\n"
        "class Probe(ABC):\n"
        "    pass\n",
        encoding="utf-8",
    )
    source = source_path.read_bytes()
    module = ModuleType("source_abc_cache_policy")
    module.__file__ = str(source_path)
    module.__package__ = ""
    module.__spec__ = spec_from_loader(
        module.__name__,
        SourceFileLoader(module.__name__, str(source_path)),
    )
    exec(
        compile(
            source,
            str(source_path),
            "exec",
            dont_inherit=True,
            optimize=sys.flags.optimize,
        ),
        vars(module),
    )
    expected = mutation_toolchain._source_code_manifest(
        source,
        source_path=source_path,
    )
    mutation_toolchain._verify_loaded_source_code(
        module,
        source=source,
        source_path=source_path,
        variant="raw",
        expected_manifest=expected,
        require_complete=False,
    )

    native_abc = import_module("_abc")
    before = native_abc._get_dump(module.Probe)

    class Unrelated:
        pass

    assert not issubclass(Unrelated, module.Probe)
    after = native_abc._get_dump(module.Probe)
    assert len(before[0]) == len(after[0]) == 0
    assert len(before[1]) == len(after[1]) == 0
    assert len(before[2]) == 0
    assert len(after[2]) == 1
    with pytest.raises(
        MutationToolchainError,
        match=r"loaded source class namespace changed: .*Probe\._abc_impl",
    ):
        mutation_toolchain._verify_loaded_source_code(
            module,
            source=source,
            source_path=source_path,
            variant="raw",
            expected_manifest=expected,
            require_complete=False,
        )


def test_abc_payload_accepts_exact_abcmeta_derived_protocol_metaclass() -> None:
    class RuntimeProtocol(typing.Protocol):
        pass

    member = vars(RuntimeProtocol)["_abc_impl"]
    shape = mutation_toolchain._runtime_source_class_member_shape(
        sys.modules[__name__],
        RuntimeProtocol,
        path=RuntimeProtocol.__qualname__,
        name="_abc_impl",
        member=member,
    )
    assert shape[0] == "_abc._abc_data"
    assert mutation_toolchain._has_exact_abcmeta_derived_metaclass(
        RuntimeProtocol
    )


def test_source_direct_protocol_generated_state_is_exact(tmp_path: Path) -> None:
    source_path = tmp_path / "source_protocol_policy.py"
    source_path.write_text(
        "from typing import Protocol\n"
        "class Probe(Protocol):\n"
        "    def value(self) -> int:\n"
        "        ...\n",
        encoding="utf-8",
    )
    source = source_path.read_bytes()
    module = ModuleType("source_protocol_policy")
    module.__file__ = str(source_path)
    module.__package__ = ""
    module.__spec__ = spec_from_loader(
        module.__name__,
        SourceFileLoader(module.__name__, str(source_path)),
    )
    exec(
        compile(
            source,
            str(source_path),
            "exec",
            dont_inherit=True,
            optimize=sys.flags.optimize,
        ),
        vars(module),
    )
    expected = mutation_toolchain._source_code_manifest(
        source,
        source_path=source_path,
    )
    mutation_toolchain._verify_loaded_source_code(
        module,
        source=source,
        source_path=source_path,
        variant="raw",
        expected_manifest=expected,
        require_complete=False,
    )

    method = vars(module.Probe)["value"]
    annotate = object.__getattribute__(method, "__annotate__")
    assert type(annotate) is FunctionType
    closure = object.__getattribute__(annotate, "__closure__")
    assert type(closure) is tuple and len(closure) == 1
    annotation_namespace = closure[0].cell_contents

    class OtherProtocol(typing.Protocol):
        pass

    tampered_annotation_namespace = dict(annotation_namespace)
    tampered_annotation_namespace["_abc_impl"] = vars(OtherProtocol)["_abc_impl"]
    closure[0].cell_contents = tampered_annotation_namespace
    try:
        with pytest.raises(
            MutationToolchainError,
            match="runtime source class annotation namespace changed",
        ):
            mutation_toolchain._verify_loaded_source_code(
                module,
                source=source,
                source_path=source_path,
                variant="raw",
                expected_manifest=expected,
                require_complete=False,
            )
    finally:
        closure[0].cell_contents = annotation_namespace

    mutation_toolchain._verify_loaded_source_code(
        module,
        source=source,
        source_path=source_path,
        variant="raw",
        expected_manifest=expected,
        require_complete=False,
    )
    vars(module.Probe)["__protocol_attrs__"].add("rogue")
    with pytest.raises(
        MutationToolchainError,
        match="loaded source Protocol generated state changed",
    ):
        mutation_toolchain._verify_loaded_source_code(
            module,
            source=source,
            source_path=source_path,
            variant="raw",
            expected_manifest=expected,
            require_complete=False,
        )


def test_abc_payload_rejects_unrelated_metaclass_with_forged_name() -> None:
    class ForgedMeta(type):
        pass

    ForgedMeta.__module__ = "abc"
    ForgedMeta.__qualname__ = "ABCMeta"

    class Forged(metaclass=ForgedMeta):
        pass

    Forged._abc_impl = vars(typing.Protocol)["_abc_impl"]
    with pytest.raises(
        MutationToolchainError,
        match="loaded source ABC runtime binding changed",
    ):
        mutation_toolchain._runtime_source_class_member_shape(
            sys.modules[__name__],
            Forged,
            path="Forged",
            name="_abc_impl",
            member=Forged._abc_impl,
        )


def test_source_version_tuple_comparisons_are_boundary_exact() -> None:
    compare = mutation_toolchain._compare_source_version_tuple
    assert compare((3, 10), "ge", (3, 10))
    assert not compare((3, 9, 99), "ge", (3, 10))
    assert compare((3, 10), "lt", (3, 11))
    assert not compare((3, 11), "lt", (3, 11))
    assert compare((3, 14, 0, "beta"), "ge", (3, 14, 0, "beta"))
    with pytest.raises(
        MutationToolchainError,
        match="version comparison is unsupported",
    ):
        compare((3, 14), "contains", (3, 10))


@pytest.mark.parametrize(
    ("slots_literal", "runtime_names"),
    [
        ("'single'", ("single",)),
        ("('alpha', '__private')", ("alpha", "_Probe__private")),
        ("['alpha', '__private']", ("alpha", "_Probe__private")),
    ],
)
def test_literal_slots_bind_exact_generated_descriptors_and_reject_rogue_key(
    tmp_path: Path,
    slots_literal: str,
    runtime_names: tuple[str, ...],
) -> None:
    source_path = tmp_path / "literal_slots_policy.py"
    source_path.write_text(
        f"class Probe:\n    __slots__ = {slots_literal}\n",
        encoding="utf-8",
    )
    source = source_path.read_bytes()
    module = ModuleType("literal_slots_policy")
    module.__file__ = str(source_path)
    module.__package__ = ""
    module.__spec__ = spec_from_loader(
        module.__name__,
        SourceFileLoader(module.__name__, str(source_path)),
    )
    exec(
        compile(
            source,
            str(source_path),
            "exec",
            dont_inherit=True,
            optimize=sys.flags.optimize,
        ),
        vars(module),
    )
    assert all(name in vars(module.Probe) for name in runtime_names)
    expected = mutation_toolchain._source_code_manifest(
        source,
        source_path=source_path,
    )

    first_name = runtime_names[0]
    original_descriptor = vars(module.Probe)[first_name]
    setattr(module.Probe, first_name, 73)
    try:
        with pytest.raises(
            MutationToolchainError,
            match="loaded source slot descriptor changed",
        ):
            mutation_toolchain._verify_loaded_source_code(
                module,
                source=source,
                source_path=source_path,
                variant="raw",
                expected_manifest=expected,
            )
    finally:
        setattr(module.Probe, first_name, original_descriptor)

    mutation_toolchain._verify_loaded_source_code(
        module,
        source=source,
        source_path=source_path,
        variant="raw",
        expected_manifest=expected,
    )
    module.Probe._phase11_rogue_slot = original_descriptor
    try:
        with pytest.raises(
            MutationToolchainError,
            match="loaded source class namespace key set changed",
        ):
            mutation_toolchain._verify_loaded_source_code(
                module,
                source=source,
                source_path=source_path,
                variant="raw",
                expected_manifest=expected,
            )
    finally:
        del module.Probe._phase11_rogue_slot


def test_dynamic_slots_fail_closed_before_first_attestation(tmp_path: Path) -> None:
    source_path = tmp_path / "dynamic_slots_policy.py"
    source_path.write_text(
        "SLOTS = ('alpha',)\nclass Probe:\n    __slots__ = SLOTS\n",
        encoding="utf-8",
    )
    source = source_path.read_bytes()
    module = ModuleType("dynamic_slots_policy")
    module.__file__ = str(source_path)
    module.__package__ = ""
    module.__spec__ = spec_from_loader(
        module.__name__,
        SourceFileLoader(module.__name__, str(source_path)),
    )
    exec(
        compile(
            source,
            str(source_path),
            "exec",
            dont_inherit=True,
            optimize=sys.flags.optimize,
        ),
        vars(module),
    )
    with pytest.raises(
        MutationToolchainError,
        match="loaded source class slots are not an exact literal",
    ):
        mutation_toolchain._verify_loaded_source_code(
            module,
            source=source,
            source_path=source_path,
            variant="raw",
            expected_manifest=mutation_toolchain._source_code_manifest(
                source,
                source_path=source_path,
            ),
        )


def test_first_loaded_attestation_rejects_required_class_foreign_module(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_path = tmp_path / "preseal_foreign_class_probe.py"
    source_path.write_text("class Probe:\n    pass\n", encoding="utf-8")
    source = source_path.read_bytes()
    module = ModuleType("preseal_foreign_class_probe")
    module.__file__ = str(source_path)
    module.__package__ = ""
    module.__spec__ = spec_from_loader(
        module.__name__,
        SourceFileLoader(module.__name__, str(source_path)),
    )
    exec(
        compile(
            source,
            str(source_path),
            "exec",
            dont_inherit=True,
            optimize=sys.flags.optimize,
        ),
        vars(module),
    )
    module.Probe.__module__ = "foreign_preseal_owner"
    monkeypatch.setattr(mutation_toolchain, "_RUNTIME_SOURCE_SENTINELS", {})

    with pytest.raises(
        MutationToolchainError,
        match="loaded source class binding changed",
    ):
        mutation_toolchain._verify_loaded_source_code(
            module,
            source=source,
            source_path=source_path,
            variant="raw",
            expected_manifest=mutation_toolchain._source_code_manifest(
                source,
                source_path=source_path,
            ),
            require_complete=False,
        )


def test_first_loaded_attestation_rejects_unproved_import_overwrite(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_path = tmp_path / "preseal_import_probe.py"
    source_path.write_text(
        "import pathlib as paths\n"
        "if False:\n"
        "    paths = None\n"
        "def marker():\n"
        "    return 1\n",
        encoding="utf-8",
    )
    source = source_path.read_bytes()
    module = ModuleType("preseal_import_probe")
    module.__file__ = str(source_path)
    module.__package__ = ""
    module.__spec__ = spec_from_loader(
        module.__name__,
        SourceFileLoader(module.__name__, str(source_path)),
    )
    exec(
        compile(
            source,
            str(source_path),
            "exec",
            dont_inherit=True,
            optimize=sys.flags.optimize,
        ),
        vars(module),
    )
    module.paths = sys
    monkeypatch.setattr(mutation_toolchain, "_RUNTIME_SOURCE_SENTINELS", {})

    with pytest.raises(
        MutationToolchainError,
        match="loaded source import binding changed",
    ):
        mutation_toolchain._verify_loaded_source_code(
            module,
            source=source,
            source_path=source_path,
            variant="raw",
            expected_manifest=mutation_toolchain._source_code_manifest(
                source,
                source_path=source_path,
            ),
        )


def test_runtime_import_sentinel_pins_executed_conditional_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    active_name = "phase11_active_provider"
    inactive_name = "phase11_inactive_provider"
    shared = object()
    active = ModuleType(active_name)
    active.Shared = shared
    inactive = ModuleType(inactive_name)
    inactive.Shared = shared
    monkeypatch.setitem(sys.modules, active_name, active)
    monkeypatch.delitem(sys.modules, inactive_name, raising=False)

    source_path = tmp_path / "conditional_provider_probe.py"
    source_path.write_text(
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n"
        f"    from {inactive_name} import Shared as Alias\n"
        "else:\n"
        f"    from {active_name} import Shared as Alias\n",
        encoding="utf-8",
    )
    source = source_path.read_bytes()
    module = ModuleType("conditional_provider_probe")
    module.__file__ = str(source_path)
    module.__package__ = ""
    module.__spec__ = spec_from_loader(
        module.__name__,
        SourceFileLoader(module.__name__, str(source_path)),
    )
    exec(compile(source, str(source_path), "exec"), vars(module))
    _code, policy = mutation_toolchain._compile_sealed_source(
        source,
        source_path=source_path,
        assertion_pass_hook=None,
    )
    monkeypatch.setattr(mutation_toolchain, "_RUNTIME_SOURCE_SENTINELS", {})

    mutation_toolchain._verify_runtime_source_bindings(module, policy=policy)
    monkeypatch.setitem(sys.modules, inactive_name, inactive)
    mutation_toolchain._verify_runtime_source_bindings(module, policy=policy)
    sentinel = mutation_toolchain._RUNTIME_SOURCE_SENTINELS[id(module)]
    alias = next(item for item in sentinel.imports if item.name == "Alias")
    assert alias.provider_name == active_name
    assert alias.provider is active


def test_runtime_import_sentinel_proves_ten_loaded_nonprovider_fallbacks() -> None:
    # The reporter's loaded set has exactly ten non-provider final bindings:
    # six builtins.object type-only fallbacks, one literal None fallback, two
    # built-in exception classes, and one sealed source fallback function.
    expected = {
        "anyio._backends._asyncio": {
            "FileDescriptorLike": "builtin:object",
        },
        "anyio._core._eventloop": {"sniffio": "literal"},
        "anyio._core._fileio": {
            "OpenBinaryMode": "builtin:object",
            "OpenTextMode": "builtin:object",
            "ReadableBuffer": "builtin:object",
            "WriteableBuffer": "builtin:object",
        },
        "anyio._core._sockets": {
            "FileDescriptorLike": "builtin:object",
        },
        "hypothesis.internal.compat": {
            "BaseExceptionGroup": "builtin:BaseExceptionGroup",
            "ExceptionGroup": "builtin:ExceptionGroup",
        },
        "xdist.remote": {"setproctitle": "sealed-source-function"},
    }
    observed = 0
    for module_name, names in expected.items():
        module = import_module(module_name)
        source_path = Path(str(module.__file__)).resolve(strict=True)
        _code, policy = mutation_toolchain._compile_sealed_source(
            source_path.read_bytes(),
            source_path=source_path,
            assertion_pass_hook=None,
        )
        sentinels = {
            item.name: item
            for item in mutation_toolchain._runtime_import_sentinels(
                module,
                policy=policy,
            )
        }
        for name, source_kind in names.items():
            sentinel = sentinels[name]
            assert sentinel.provider_name is None
            assert sentinel.provider is None
            assert sentinel.provider_attribute == source_kind
            observed += 1
    assert observed == 10


def test_runtime_class_sentinel_detects_enum_member_value_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_module = import_module("_pytest.config")
    exit_code = config_module.ExitCode
    ok = exit_code.OK
    original_value = ok._value_
    source_path = Path(str(config_module.__file__)).resolve(strict=True)
    _code, policy = mutation_toolchain._compile_sealed_source(
        source_path.read_bytes(),
        source_path=source_path,
        assertion_pass_hook=None,
    )
    monkeypatch.setattr(mutation_toolchain, "_RUNTIME_SOURCE_SENTINELS", {})
    mutation_toolchain._verify_runtime_source_bindings(config_module, policy=policy)

    try:
        object.__setattr__(ok, "_value_", 73)
        with pytest.raises(
            MutationToolchainError,
            match="loaded source Enum member changed: _pytest.config.ExitCode.OK",
        ):
            mutation_toolchain._verify_runtime_source_bindings(
                config_module,
                policy=policy,
            )
    finally:
        object.__setattr__(ok, "_value_", original_value)


def test_runtime_source_sentinel_binds_read_only_literal_module_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    core_module = import_module("hypothesis.core")
    source_path = Path(str(core_module.__file__)).resolve(strict=True)
    _code, policy = mutation_toolchain._compile_sealed_source(
        source_path.read_bytes(),
        source_path=source_path,
        assertion_pass_hook=None,
    )
    original = core_module.pytest_shows_exceptiongroups
    assert original is True
    monkeypatch.setattr(mutation_toolchain, "_RUNTIME_SOURCE_SENTINELS", {})

    core_module.pytest_shows_exceptiongroups = False
    with pytest.raises(
        MutationToolchainError,
        match=(
            "loaded source module policy changed: "
            "hypothesis.core.pytest_shows_exceptiongroups"
        ),
    ):
        mutation_toolchain._verify_runtime_source_bindings(
            core_module,
            policy=policy,
        )
    core_module.pytest_shows_exceptiongroups = original
    mutation_toolchain._verify_runtime_source_bindings(core_module, policy=policy)

    try:
        core_module.pytest_shows_exceptiongroups = False
        with pytest.raises(
            MutationToolchainError,
            match=(
                "loaded source module policy changed: "
                "hypothesis.core.pytest_shows_exceptiongroups"
            ),
        ):
            mutation_toolchain._verify_runtime_source_bindings(
                core_module,
                policy=policy,
            )
    finally:
        core_module.pytest_shows_exceptiongroups = original


def test_module_policy_excludes_source_mutated_container_but_binds_scalar(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_path = tmp_path / "module_policy_probe.py"
    source_path.write_text(
        "cache = {}\n"
        "policy = True\n"
        "def mutate():\n"
        "    cache['key'] = 1\n"
        "    return policy\n",
        encoding="utf-8",
    )
    source = source_path.read_bytes()
    module = ModuleType("module_policy_probe")
    module.__file__ = str(source_path)
    module.__package__ = ""
    module.__spec__ = spec_from_loader(
        module.__name__,
        SourceFileLoader(module.__name__, str(source_path)),
    )
    exec(
        compile(
            source,
            str(source_path),
            "exec",
            dont_inherit=True,
            optimize=sys.flags.optimize,
        ),
        vars(module),
    )
    _code, policy = mutation_toolchain._compile_sealed_source(
        source,
        source_path=source_path,
        assertion_pass_hook=None,
    )
    assert [binding.name for binding in policy.module_data] == ["policy"]
    module.mutate()
    monkeypatch.setattr(mutation_toolchain, "_RUNTIME_SOURCE_SENTINELS", {})
    mutation_toolchain._verify_runtime_source_bindings(module, policy=policy)

    module.policy = False
    with pytest.raises(
        MutationToolchainError,
        match="loaded source module policy changed: module_policy_probe.policy",
    ):
        mutation_toolchain._verify_runtime_source_bindings(module, policy=policy)


def test_loaded_source_attestation_admits_only_exact_pytest_item_lifecycle_transitions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    python_module = import_module("_pytest.python")
    nodes_module = import_module("_pytest.nodes")
    function_class = python_module.Function
    function_definition_class = python_module.FunctionDefinition
    item_class = nodes_module.Item
    attr_name = "_pytest_diamond_inheritance_warning_shown"
    source_path = Path(str(python_module.__file__)).resolve(strict=True)
    source = source_path.read_bytes()
    variant = mutation_toolchain._source_loader_variant(
        python_module.__spec__.loader,
        module_name=python_module.__name__,
        rewrite_module_is_attested=True,
    )
    admitted_source_paths: set[str] = set()
    admitted_module_paths: set[str] = set()
    admitted_class_ids: set[int] = set()
    for loaded_module in tuple(sys.modules.values()):
        if not isinstance(loaded_module, ModuleType):
            continue
        module_file = getattr(loaded_module, "__file__", None)
        if isinstance(module_file, str):
            try:
                resolved = Path(module_file).resolve(strict=True)
            except OSError:
                pass
            else:
                folded = os.path.normcase(os.fspath(resolved))
                admitted_module_paths.add(folded)
                if resolved.suffix.casefold() in {".py", ".pyw"}:
                    admitted_source_paths.add(folded)
        admitted_class_ids.update(
            id(value)
            for value in vars(loaded_module).values()
            if isinstance(value, type)
        )
    verification = {
        "source": source,
        "source_path": source_path,
        "variant": variant,
        "admitted_source_paths": frozenset(admitted_source_paths),
        "admitted_module_paths": frozenset(admitted_module_paths),
        "admitted_class_ids": frozenset(admitted_class_ids),
        "require_complete": False,
    }
    lifecycle_classes = (function_definition_class, function_class)
    original_members = tuple(
        (
            lifecycle_class,
            attr_name in vars(lifecycle_class),
            vars(lifecycle_class).get(attr_name),
        )
        for lifecycle_class in lifecycle_classes
    )
    monkeypatch.setattr(mutation_toolchain, "_RUNTIME_SOURCE_SENTINELS", {})

    try:
        for lifecycle_class, present, _value in original_members:
            if present:
                delattr(lifecycle_class, attr_name)
        mutation_toolchain._verify_loaded_source_code(python_module, **verification)

        for lifecycle_class in lifecycle_classes:
            item = object.__new__(lifecycle_class)
            item_class._check_item_and_collector_diamond_inheritance(item)
            assert vars(lifecycle_class).get(attr_name) is True
        mutation_toolchain._verify_loaded_source_code(python_module, **verification)

        setattr(function_definition_class, attr_name, False)
        with pytest.raises(
            MutationToolchainError,
            match=(
                "loaded source class namespace key set changed: "
                "_pytest.python.FunctionDefinition"
            ),
        ):
            mutation_toolchain._verify_loaded_source_code(
                python_module,
                **verification,
            )

        setattr(function_definition_class, attr_name, True)
        rogue_name = "_phase11_unadmitted_lifecycle_state"
        setattr(function_class, rogue_name, True)
        try:
            with pytest.raises(
                MutationToolchainError,
                match="loaded source class namespace key set changed",
            ):
                mutation_toolchain._verify_loaded_source_code(
                    python_module,
                    **verification,
                )
        finally:
            delattr(function_class, rogue_name)

        delattr(function_class, attr_name)
        with pytest.raises(
            MutationToolchainError,
            match="loaded source class namespace key set changed",
        ):
            mutation_toolchain._verify_loaded_source_code(
                python_module,
                **verification,
            )
    finally:
        for lifecycle_class, present, value in original_members:
            if present:
                setattr(lifecycle_class, attr_name, value)
            elif attr_name in vars(lifecycle_class):
                delattr(lifecycle_class, attr_name)


def test_loaded_module_attestation_rejects_source_loader_subclasses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identity = _current_identity()
    expected = next(
        item for item in identity["modules"] if item["module"] == "yaml"
    )
    module_path = Path(str(identity["prefix"])).joinpath(
        *PurePosixPath(str(expected["path"])).parts
    )

    class ForeignSourceLoader(SourceFileLoader):
        pass

    foreign = ModuleType("yaml")
    foreign.__file__ = str(module_path)
    foreign.__spec__ = spec_from_loader(
        "yaml",
        ForeignSourceLoader("yaml", str(module_path)),
    )
    monkeypatch.setitem(sys.modules, "yaml", foreign)
    with pytest.raises(
        MutationToolchainError,
        match="captured prefix module binding changed: yaml",
    ):
        _loaded_test_toolchain_attestation(identity)


def test_loaded_module_attestation_rejects_foreign_startup_module(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identity = _current_identity()
    module_name = next(
        name
        for name in identity["startup"]["module_names"]
        if name.startswith("__editable___moira_astro_")
    )
    foreign_path = tmp_path / "editable_finder.py"
    foreign_path.write_text("FOREIGN = True\n", encoding="utf-8")
    foreign = ModuleType(module_name)
    foreign.__file__ = str(foreign_path)
    foreign.__spec__ = spec_from_loader(
        module_name,
        SourceFileLoader(module_name, str(foreign_path)),
    )
    monkeypatch.setitem(sys.modules, module_name, foreign)
    with pytest.raises(
        MutationToolchainError,
        match="startup import root contradicts its static prefix scope",
    ):
        _fresh_current_identity()
    with pytest.raises(
        MutationToolchainError,
        match="startup import root contradicts its static prefix scope",
    ):
        _loaded_test_toolchain_attestation(identity)


def test_deleted_transient_class_binding_is_required_absent(tmp_path: Path) -> None:
    source_path = tmp_path / "deleted_binding_probe.py"
    source_path.write_text(
        "class _Transient:\n"
        "    pass\n\n"
        "del _Transient\n\n"
        "class Stable:\n"
        "    pass\n",
        encoding="utf-8",
    )
    source = source_path.read_bytes()
    module = ModuleType("deleted_binding_probe")
    module.__file__ = str(source_path)
    module.__spec__ = spec_from_loader(
        module.__name__,
        SourceFileLoader(module.__name__, str(source_path)),
    )
    exec(
        compile(
            source,
            str(source_path),
            "exec",
            dont_inherit=True,
            optimize=sys.flags.optimize,
        ),
        vars(module),
    )
    expected = mutation_toolchain._source_code_manifest(
        source,
        source_path=source_path,
    )
    _entries, policy, _bindings = (
        mutation_toolchain._sealed_source_variant_payload(
            source,
            source_path=source_path,
            variant="raw",
        )
    )
    transient_binding = next(
        binding for binding in policy.bindings if binding.path == ("_Transient",)
    )
    assert transient_binding.required is False
    assert transient_binding.must_be_absent is True
    assert {
        sentinel.path
        for sentinel in mutation_toolchain._runtime_class_sentinels(
            module,
            policy=policy,
        )
    } == {"Stable"}

    mutation_toolchain._verify_loaded_source_code(
        module,
        source=source,
        source_path=source_path,
        variant="raw",
        expected_manifest=expected,
    )

    module._Transient = object()
    with pytest.raises(
        MutationToolchainError,
        match="deleted source class is unexpectedly present",
    ):
        mutation_toolchain._runtime_class_sentinels(module, policy=policy)
    del module._Transient

    transient = type("_Transient", (), {})
    transient.__module__ = module.__name__
    module._Transient = transient
    with pytest.raises(
        MutationToolchainError,
        match="deleted source class is unexpectedly present",
    ):
        mutation_toolchain._runtime_class_sentinels(module, policy=policy)
    with pytest.raises(
        MutationToolchainError,
        match="deleted source binding is unexpectedly present",
    ):
        mutation_toolchain._verify_loaded_source_code(
            module,
            source=source,
            source_path=source_path,
            variant="raw",
            expected_manifest=expected,
        )


def test_deleted_class_requires_an_executed_source_candidate(tmp_path: Path) -> None:
    source_path = tmp_path / "inactive_deleted_class.py"
    source = (
        "if False:\n"
        "    class _Transient:\n"
        "        pass\n"
        "del _Transient\n"
    ).encode("utf-8")
    source_path.write_bytes(source)
    module = ModuleType("inactive_deleted_class")
    module.__file__ = str(source_path)
    module.__spec__ = spec_from_loader(
        module.__name__,
        SourceFileLoader(module.__name__, str(source_path)),
    )
    _entries, policy, bindings = (
        mutation_toolchain._sealed_source_variant_payload(
            source,
            source_path=source_path,
            variant="raw",
        )
    )
    binding = next(
        item for item in policy.bindings if item.path == ("_Transient",)
    )
    assert binding.must_be_absent
    assert binding.candidates[0].guards_complete

    with pytest.raises(
        MutationToolchainError,
        match="deleted source binding has no active candidate",
    ):
        mutation_toolchain._verify_loaded_bindings(
            module,
            bindings=bindings,
            attested_code_identities=frozenset(),
            admitted_source_paths=frozenset(),
            admitted_class_ids=frozenset(),
            policy=policy,
        )
    with pytest.raises(
        MutationToolchainError,
        match="deleted source class has no active candidate",
    ):
        mutation_toolchain._runtime_class_sentinels(module, policy=policy)


def test_redefined_deleted_class_is_required_present(tmp_path: Path) -> None:
    source_path = tmp_path / "redefined_deleted_class.py"
    source = (
        "class Probe:\n"
        "    marker = 'first'\n"
        "del Probe\n"
        "class Probe:\n"
        "    marker = 'final'\n"
    ).encode("utf-8")
    source_path.write_bytes(source)
    module = ModuleType("redefined_deleted_class")
    module.__file__ = str(source_path)
    module.__spec__ = spec_from_loader(
        module.__name__,
        SourceFileLoader(module.__name__, str(source_path)),
    )
    exec(
        compile(
            source,
            str(source_path),
            "exec",
            dont_inherit=True,
            optimize=sys.flags.optimize,
        ),
        vars(module),
    )
    _entries, policy, _bindings = (
        mutation_toolchain._sealed_source_variant_payload(
            source,
            source_path=source_path,
            variant="raw",
        )
    )
    binding = next(item for item in policy.bindings if item.path == ("Probe",))
    assert binding.required
    assert not binding.must_be_absent
    assert len(binding.candidates) == 2
    assert vars(module)["Probe"].marker == "final"
    sentinels = mutation_toolchain._runtime_class_sentinels(module, policy=policy)
    assert [sentinel.path for sentinel in sentinels] == ["Probe"]
    assert sentinels[0].value is vars(module)["Probe"]


def test_pytest_python_empty_class_is_exact_transient_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "_pytest.python"
    module = import_module(module_name)
    policy = _loaded_source_policy(module)
    binding = next(
        item for item in policy.bindings if item.path == ("_EmptyClass",)
    )
    assert binding.required is False
    assert binding.must_be_absent is True
    assert len(binding.candidates) == 1
    assert binding.candidates[0].guards_complete
    assert binding.candidates[0].guards == ()
    assert "_EmptyClass" not in vars(module)
    monkeypatch.setattr(mutation_toolchain, "_RUNTIME_SOURCE_SENTINELS", {})

    _verify_selected_binding(
        module_name,
        "_EmptyClass",
        admitted_module_names=(module_name,),
    )
    assert mutation_toolchain._RUNTIME_SOURCE_SENTINELS == {}


def test_source_declared_descriptor_lineage_covers_multiple_bindings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_path = tmp_path / "descriptor_binding_probe.py"
    source_path.write_text(
        "class Probe:\n"
        "    def descriptor(fn):\n"
        "        def accept(self):\n"
        "            return fn(self)\n"
        "        return property(accept)\n\n"
        "    @descriptor\n"
        "    def derived(self):\n"
        "        return 41\n\n"
        "    @descriptor\n"
        "    def second_derived(self):\n"
        "        return 42\n\n"
        "    def alternate(self):\n"
        "        return 99\n",
        encoding="utf-8",
    )
    source = source_path.read_bytes()
    module = ModuleType("descriptor_binding_probe")
    module.__file__ = str(source_path)
    module.__spec__ = spec_from_loader(
        module.__name__,
        SourceFileLoader(module.__name__, str(source_path)),
    )
    exec(
        compile(
            source,
            str(source_path),
            "exec",
            dont_inherit=True,
            optimize=sys.flags.optimize,
        ),
        vars(module),
    )
    expected = mutation_toolchain._source_code_manifest(
        source,
        source_path=source_path,
    )
    monkeypatch.setattr(
        mutation_toolchain,
        "_ADMITTED_DESCRIPTOR_DECORATOR_TRANSFORMS",
        MappingProxyType(
            {
                (module.__name__, "Probe.descriptor"): (
                    "property",
                    "Probe.descriptor.<locals>.accept",
                    "fn",
                )
            }
        ),
    )

    mutation_toolchain._verify_loaded_source_code(
        module,
        source=source,
        source_path=source_path,
        variant="raw",
        expected_manifest=expected,
    )

    sealed_descriptor = vars(module.Probe)["second_derived"]
    module._saved_descriptor = sealed_descriptor
    module._saved_second_derived = sealed_descriptor.fget.__closure__[0].cell_contents
    module.Probe.second_derived = property(module.Probe.alternate)
    with pytest.raises(
        MutationToolchainError,
        match="loaded source descriptor binding changed",
    ):
        mutation_toolchain._verify_loaded_source_code(
            module,
            source=source,
            source_path=source_path,
            variant="raw",
            expected_manifest=expected,
        )


@pytest.mark.parametrize("path", ["_maybe_nil_uuids", "slices"])
def test_composite_binding_requires_exact_generated_alias_chain(
    path: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "hypothesis.strategies._internal.core"
    admitted = (
        module_name,
        "hypothesis.strategies._internal.utils",
    )
    _verify_selected_binding(
        module_name,
        path,
        admitted_module_names=admitted,
    )

    module = import_module(module_name)
    binding = vars(module)[path]
    inner = vars(binding)["__wrapped__"]
    monkeypatch.setattr(binding, "__wrapped_target", binding.__closure__[0].cell_contents)
    with pytest.raises(
        MutationToolchainError,
        match="callable-decorator binding changed",
    ):
        _verify_selected_binding(
            module_name,
            path,
            admitted_module_names=admitted,
        )
    monkeypatch.setattr(binding, "__wrapped_target", inner)


def test_composite_binding_rejects_exact_code_with_forged_closure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "hypothesis.strategies._internal.core"
    path = "_maybe_nil_uuids"
    admitted = (
        module_name,
        "hypothesis.strategies._internal.utils",
    )
    module = import_module(module_name)
    binding = vars(module)[path]
    inner = vars(binding)["__wrapped__"]

    def cell(value: object) -> object:
        def capture() -> object:
            return value

        assert capture.__closure__ is not None
        return capture.__closure__[0]

    forged = FunctionType(
        binding.__code__,
        binding.__globals__,
        binding.__name__,
        binding.__defaults__,
        (cell(inner),),
    )
    forged.__module__ = binding.__module__
    forged.__kwdefaults__ = binding.__kwdefaults__
    vars(forged).update(vars(binding))
    monkeypatch.setattr(module, path, forged)
    with pytest.raises(
        MutationToolchainError,
        match="callable-decorator binding changed",
    ):
        _verify_selected_binding(
            module_name,
            path,
            admitted_module_names=admitted,
        )


@pytest.mark.parametrize(
    ("module_name", "path"),
    [
        ("pygments.lexer", "Lexer.analyse_text"),
        ("pygments.lexers.diff", "DiffLexer.analyse_text"),
        ("pygments.lexers.python", "NumPyLexer.analyse_text"),
        ("pygments.lexers.python", "Python2Lexer.analyse_text"),
        ("pygments.lexers.python", "PythonLexer.analyse_text"),
    ],
)
def test_pygments_analyse_text_metaclass_chain_is_exact(
    module_name: str,
    path: str,
) -> None:
    _verify_selected_binding(
        module_name,
        path,
        admitted_module_names=(
            module_name,
            "pygments.lexer",
            "pygments.util",
        ),
    )


def test_pygments_metaclass_chain_rejects_reachable_original_swap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "pygments.lexers.diff"
    path = "DiffLexer.analyse_text"
    module = import_module(module_name)
    owner = vars(module)["DiffLexer"]
    descriptor = vars(owner)["analyse_text"]
    original = descriptor.__func__.__closure__[0].cell_contents
    monkeypatch.setattr(owner, "analyse_text", staticmethod(original))
    with pytest.raises(
        MutationToolchainError,
        match="metaclass binding changed",
    ):
        _verify_selected_binding(
            module_name,
            path,
            admitted_module_names=(
                module_name,
                "pygments.lexer",
                "pygments.util",
            ),
        )


def test_pygments_metaclass_chain_rejects_imported_factory_swap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "pygments.lexers.diff"
    lexer_module = import_module("pygments.lexer")
    monkeypatch.setattr(lexer_module, "make_analysator", lambda value: value)
    with pytest.raises(
        MutationToolchainError,
        match="metaclass binding changed",
    ):
        _verify_selected_binding(
            module_name,
            "DiffLexer.analyse_text",
            admitted_module_names=(
                module_name,
                "pygments.lexer",
                "pygments.util",
            ),
        )


def test_binding_attestation_rejects_swap_while_original_remains_reachable(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "binding_probe.py"
    source_path.write_text(
        "def _plain_path(value):\n"
        "    return value + 1\n\n"
        "def untouched(value):\n"
        "    return value - 1\n",
        encoding="utf-8",
    )
    loader = SourceFileLoader("binding_probe", str(source_path))
    module = ModuleType("binding_probe")
    module.__file__ = str(source_path)
    module.__spec__ = spec_from_loader("binding_probe", loader)
    exec(
        compile(
            source_path.read_bytes(),
            str(source_path),
            "exec",
            dont_inherit=True,
            optimize=sys.flags.optimize,
        ),
        vars(module),
    )
    source = source_path.read_bytes()
    expected = mutation_toolchain._source_code_manifest(
        source,
        source_path=source_path,
    )
    mutation_toolchain._verify_loaded_source_code(
        module,
        source=source,
        source_path=source_path,
        variant="raw",
        expected_manifest=expected,
    )

    module._saved_plain_path = module._plain_path
    module._plain_path = len
    with pytest.raises(MutationToolchainError, match="callable binding changed"):
        mutation_toolchain._verify_loaded_source_code(
            module,
            source=source,
            source_path=source_path,
            variant="raw",
            expected_manifest=expected,
        )

    class EvilProxy:
        def __init__(self, wrapped: object) -> None:
            self.__wrapped__ = wrapped

        def __call__(self, _value: object) -> int:
            return 999

    module._plain_path = EvilProxy(module._saved_plain_path)
    with pytest.raises(MutationToolchainError, match="arbitrary callable proxy"):
        mutation_toolchain._verify_loaded_source_code(
            module,
            source=source,
            source_path=source_path,
            variant="raw",
            expected_manifest=expected,
        )

    forged_namespace: dict[str, object] = {}
    exec(
        compile(
            "def factory(anchor):\n"
            "    def forged(value):\n"
            "        anchor\n"
            "        return 999\n"
            "    return forged\n",
            "<string>",
            "exec",
            dont_inherit=True,
            optimize=sys.flags.optimize,
        ),
        forged_namespace,
    )
    forged_factory = forged_namespace["factory"]
    assert callable(forged_factory)
    forged = forged_factory(Path.resolve)
    forged.__wrapped__ = module._saved_plain_path
    module._plain_path = forged
    with pytest.raises(
        MutationToolchainError,
        match="outside an admitted source scope|callable binding changed",
    ):
        mutation_toolchain._verify_loaded_source_code(
            module,
            source=source,
            source_path=source_path,
            variant="raw",
            expected_manifest=expected,
        )


def test_pathlib_active_windows_copy_from_file_rejects_inactive_candidate_before_first_seal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pathlib_module = import_module("pathlib")
    path_type = vars(pathlib_module)["Path"]
    active = vars(path_type)["_copy_from_file"]
    fallback = vars(path_type)["_copy_from_file_fallback"]
    assert active.__code__.co_firstlineno == 1147
    assert fallback.__code__.co_firstlineno == 1136
    monkeypatch.setattr(mutation_toolchain, "_RUNTIME_SOURCE_SENTINELS", {})
    _verify_selected_binding(
        "pathlib",
        "Path._copy_from_file",
        admitted_module_names=("pathlib",),
    )
    monkeypatch.setattr(active, "__code__", fallback.__code__)

    with pytest.raises(
        MutationToolchainError,
        match="callable binding changed",
    ):
        _verify_selected_binding(
            "pathlib",
            "Path._copy_from_file",
            admitted_module_names=("pathlib",),
        )
    assert mutation_toolchain._RUNTIME_SOURCE_SENTINELS == {}


def test_pathlib_active_windows_copy_from_symlink_is_required_before_first_seal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pathlib_module = import_module("pathlib")
    path_type = vars(pathlib_module)["Path"]
    active = vars(path_type)["_copy_from_symlink"]
    assert active.__code__.co_firstlineno == 1161
    monkeypatch.setattr(mutation_toolchain, "_RUNTIME_SOURCE_SENTINELS", {})
    _verify_selected_binding(
        "pathlib",
        "Path._copy_from_symlink",
        admitted_module_names=("pathlib",),
    )
    monkeypatch.delattr(path_type, "_copy_from_symlink")

    with pytest.raises(
        MutationToolchainError,
        match="binding is missing",
    ):
        _verify_selected_binding(
            "pathlib",
            "Path._copy_from_symlink",
            admitted_module_names=("pathlib",),
        )
    assert mutation_toolchain._RUNTIME_SOURCE_SENTINELS == {}


def test_pathlib_os_name_guard_rejects_coordinated_inactive_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pathlib_module = import_module("pathlib")
    source_path = Path(str(pathlib_module.__file__)).resolve(strict=True)
    source = source_path.read_bytes()
    path_type = vars(pathlib_module)["Path"]
    active = vars(path_type)["_copy_from_symlink"]
    inactive_code = _compiled_source_candidate_code(
        source,
        source_path=source_path,
        qualname="Path._copy_from_symlink",
        first_line=1166,
    )
    monkeypatch.setattr(mutation_toolchain, "_RUNTIME_SOURCE_SENTINELS", {})
    module, binding, attested, admitted_paths, policy = (
        _selected_binding_evidence(
            "pathlib",
            "Path._copy_from_symlink",
            admitted_module_names=("pathlib",),
        )
    )
    mutation_toolchain._verify_loaded_bindings(
        module,
        bindings=[binding],
        attested_code_identities=attested,
        admitted_source_paths=admitted_paths,
        admitted_class_ids=frozenset(),
        policy=policy,
    )
    monkeypatch.setattr(os, "name", "posix")
    monkeypatch.setattr(active, "__code__", inactive_code)

    with pytest.raises(
        MutationToolchainError,
        match="source guard os provider graph changed",
    ):
        mutation_toolchain._verify_loaded_bindings(
            module,
            bindings=[binding],
            attested_code_identities=attested,
            admitted_source_paths=admitted_paths,
            admitted_class_ids=frozenset(),
            policy=policy,
        )
    assert mutation_toolchain._RUNTIME_SOURCE_SENTINELS == {}


@pytest.mark.parametrize(
    ("attribute", "qualname", "fallback_line"),
    (
        ("readlink", "Path.readlink", 977),
        ("symlink", "Path.symlink_to", 1215),
        ("link", "Path.hardlink_to", 1232),
    ),
)
def test_pathlib_os_capability_guard_rejects_coordinated_fallback(
    monkeypatch: pytest.MonkeyPatch,
    attribute: str,
    qualname: str,
    fallback_line: int,
) -> None:
    pathlib_module = import_module("pathlib")
    source_path = Path(str(pathlib_module.__file__)).resolve(strict=True)
    source = source_path.read_bytes()
    path_type = vars(pathlib_module)["Path"]
    method_name = qualname.rsplit(".", 1)[-1]
    active = vars(path_type)[method_name]
    fallback_code = _compiled_source_candidate_code(
        source,
        source_path=source_path,
        qualname=qualname,
        first_line=fallback_line,
    )
    monkeypatch.setattr(mutation_toolchain, "_RUNTIME_SOURCE_SENTINELS", {})
    _verify_selected_binding(
        "pathlib",
        qualname,
        admitted_module_names=("pathlib",),
    )
    monkeypatch.delattr(os, attribute)
    monkeypatch.setattr(active, "__code__", fallback_code)

    with pytest.raises(
        MutationToolchainError,
        match=rf"source guard os attribute changed: {attribute}",
    ):
        _verify_selected_binding(
            "pathlib",
            qualname,
            admitted_module_names=("pathlib",),
        )
    assert mutation_toolchain._RUNTIME_SOURCE_SENTINELS == {}


@pytest.mark.parametrize(
    "replacement_kind",
    ("wrong_native_name", "python_function"),
)
def test_pathlib_os_guard_rejects_spoofed_native_capability(
    monkeypatch: pytest.MonkeyPatch,
    replacement_kind: str,
) -> None:
    native_os_module = object.__getattribute__(os.stat, "__self__")

    def python_symlink(*_args: object, **_kwargs: object) -> None:
        return None

    replacement = (
        os.link
        if replacement_kind == "wrong_native_name"
        else python_symlink
    )
    monkeypatch.setattr(mutation_toolchain, "_RUNTIME_SOURCE_SENTINELS", {})
    _verify_selected_binding(
        "pathlib",
        "Path.symlink_to",
        admitted_module_names=("pathlib",),
    )
    monkeypatch.setattr(os, "symlink", replacement)
    monkeypatch.setattr(native_os_module, "symlink", replacement)

    with pytest.raises(
        MutationToolchainError,
        match="source guard os attribute changed: symlink",
    ):
        _verify_selected_binding(
            "pathlib",
            "Path.symlink_to",
            admitted_module_names=("pathlib",),
        )
    assert mutation_toolchain._RUNTIME_SOURCE_SENTINELS == {}


def test_pathlib_os_guard_rejects_hostile_native_spec_without_callbacks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    native_os_module = object.__getattribute__(os.stat, "__self__")
    callbacks: list[str] = []

    class HostileSpec:
        @property
        def loader(self) -> object:
            callbacks.append("loader")
            return mutation_toolchain.BuiltinImporter

        @property
        def origin(self) -> str:
            callbacks.append("origin")
            return "built-in"

    monkeypatch.setattr(mutation_toolchain, "_RUNTIME_SOURCE_SENTINELS", {})
    _verify_selected_binding(
        "pathlib",
        "Path.symlink_to",
        admitted_module_names=("pathlib",),
    )
    monkeypatch.setattr(native_os_module, "__spec__", HostileSpec())

    with pytest.raises(
        MutationToolchainError,
        match="source guard os provider graph changed",
    ):
        _verify_selected_binding(
            "pathlib",
            "Path.symlink_to",
            admitted_module_names=("pathlib",),
        )
    assert callbacks == []
    assert mutation_toolchain._RUNTIME_SOURCE_SENTINELS == {}


def test_pathlib_guard_authority_rejects_in_place_self_blessing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pathlib_module = import_module("pathlib")
    source_path = Path(str(pathlib_module.__file__)).resolve(strict=True)
    source = source_path.read_bytes()
    path_type = vars(pathlib_module)["Path"]
    active = vars(path_type)["symlink_to"]
    original_code = active.__code__
    fallback_code = _compiled_source_candidate_code(
        source,
        source_path=source_path,
        qualname="Path.symlink_to",
        first_line=1215,
    )
    module, binding, attested, admitted_paths, policy = (
        _selected_binding_evidence(
            "pathlib",
            "Path.symlink_to",
            admitted_module_names=("pathlib",),
        )
    )
    mutation_toolchain._verify_loaded_bindings(
        module,
        bindings=[binding],
        attested_code_identities=attested,
        admitted_source_paths=admitted_paths,
        admitted_class_ids=frozenset(),
        policy=policy,
    )

    authority = mutation_toolchain._raw_source_attribute.__defaults__[0]
    assert authority is mutation_toolchain._SOURCE_GUARD_ATTRIBUTE_AUTHORITY
    native_os_module = authority.native_os_module
    original_os_symlink = vars(os)["symlink"]
    original_native_symlink = vars(native_os_module)["symlink"]
    original_entries = authority.native_os_entries
    forged_entries = tuple(
        (name, False, None) if name == "symlink" else entry
        for entry in original_entries
        for name in (entry[0],)
    )
    assert forged_entries != original_entries

    with monkeypatch.context() as attack:
        attack.delattr(os, "symlink")
        attack.delattr(native_os_module, "symlink")
        attack.setattr(active, "__code__", fallback_code)
        object.__setattr__(authority, "native_os_entries", forged_entries)
        try:
            with pytest.raises(
                MutationToolchainError,
                match="source guard os attribute changed: symlink",
            ):
                mutation_toolchain._verify_loaded_bindings(
                    module,
                    bindings=[binding],
                    attested_code_identities=attested,
                    admitted_source_paths=admitted_paths,
                    admitted_class_ids=frozenset(),
                    policy=policy,
                )
        finally:
            object.__setattr__(authority, "native_os_entries", original_entries)

    assert authority.native_os_entries is original_entries
    assert vars(os)["symlink"] is original_os_symlink
    assert vars(native_os_module)["symlink"] is original_native_symlink
    assert active.__code__ is original_code


def test_pathlib_os_guard_rejects_coordinated_fingerprint_self_blessing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(mutation_toolchain, "_RUNTIME_SOURCE_SENTINELS", {})
    pathlib_module = import_module("pathlib")
    source_path = Path(str(pathlib_module.__file__)).resolve(strict=True)
    source = source_path.read_bytes()
    path_type = vars(pathlib_module)["Path"]
    active = vars(path_type)["symlink_to"]
    original_code = active.__code__
    fallback_code = _compiled_source_candidate_code(
        source,
        source_path=source_path,
        qualname="Path.symlink_to",
        first_line=1215,
    )
    module, binding, attested, admitted_paths, policy = (
        _selected_binding_evidence(
            "pathlib",
            "Path.symlink_to",
            admitted_module_names=("pathlib",),
        )
    )
    mutation_toolchain._verify_loaded_bindings(
        module,
        bindings=[binding],
        attested_code_identities=attested,
        admitted_source_paths=admitted_paths,
        admitted_class_ids=frozenset(),
        policy=policy,
    )

    raw_attribute = mutation_toolchain._raw_source_attribute
    original_defaults = raw_attribute.__defaults__
    assert original_defaults is not None
    authority = original_defaults[0]
    assert authority is mutation_toolchain._SOURCE_GUARD_ATTRIBUTE_AUTHORITY
    native_os_module = authority.native_os_module
    original_os_symlink = vars(os)["symlink"]
    original_native_symlink = vars(native_os_module)["symlink"]
    original_entries = authority.native_os_entries
    forged_entries = tuple(
        (name, False, None) if name == "symlink" else entry
        for entry in original_entries
        for name in (entry[0],)
    )
    assert forged_entries != original_entries

    with monkeypatch.context() as attack:
        attack.delattr(os, "symlink")
        attack.delattr(native_os_module, "symlink")
        attack.setattr(active, "__code__", fallback_code)
        object.__setattr__(authority, "native_os_entries", forged_entries)
        try:
            (
                forged_slots,
                forged_descriptor_get,
                forged_fingerprint,
            ) = mutation_toolchain._build_source_guard_attribute_authority_fingerprint(
                authority
            )
            attack.setattr(
                mutation_toolchain,
                "_SOURCE_GUARD_ATTRIBUTE_AUTHORITY_SLOTS",
                forged_slots,
            )
            attack.setattr(
                mutation_toolchain,
                "_SOURCE_GUARD_MEMBER_DESCRIPTOR_GET",
                forged_descriptor_get,
            )
            attack.setattr(
                mutation_toolchain,
                "_SOURCE_GUARD_ATTRIBUTE_AUTHORITY_FINGERPRINT",
                forged_fingerprint,
            )
            attack.setattr(
                raw_attribute,
                "__defaults__",
                (
                    authority,
                    forged_slots,
                    forged_descriptor_get,
                    forged_fingerprint,
                ),
            )

            with pytest.raises(
                MutationToolchainError,
                match="source guard os attribute changed: symlink",
            ):
                mutation_toolchain._verify_loaded_bindings(
                    module,
                    bindings=[binding],
                    attested_code_identities=attested,
                    admitted_source_paths=admitted_paths,
                    admitted_class_ids=frozenset(),
                    policy=policy,
                )
        finally:
            object.__setattr__(authority, "native_os_entries", original_entries)

    assert raw_attribute.__defaults__ is original_defaults
    assert authority.native_os_entries is original_entries
    assert vars(os)["symlink"] is original_os_symlink
    assert vars(native_os_module)["symlink"] is original_native_symlink
    assert active.__code__ is original_code
    assert mutation_toolchain._RUNTIME_SOURCE_SENTINELS == {}


def test_pathlib_os_guard_rejects_self_blessed_fake_native_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(mutation_toolchain, "_RUNTIME_SOURCE_SENTINELS", {})
    module, binding, attested, admitted_paths, policy = (
        _selected_binding_evidence(
            "pathlib",
            "Path.symlink_to",
            admitted_module_names=("pathlib",),
        )
    )
    mutation_toolchain._verify_loaded_bindings(
        module,
        bindings=[binding],
        attested_code_identities=attested,
        admitted_source_paths=admitted_paths,
        admitted_class_ids=frozenset(),
        policy=policy,
    )

    raw_attribute = mutation_toolchain._raw_source_attribute
    original_defaults = raw_attribute.__defaults__
    assert original_defaults is not None
    authority = original_defaults[0]
    assert authority is mutation_toolchain._SOURCE_GUARD_ATTRIBUTE_AUTHORITY
    native_os_name = authority.native_os_name
    native_os_module = authority.native_os_module
    fake_native_os_module = ModuleType(native_os_name)
    fake_native_namespace = vars(fake_native_os_module)
    fake_native_namespace["__spec__"] = authority.native_os_specification
    fake_native_namespace["__loader__"] = authority.native_os_loader
    for entry_name, present, expected in authority.native_os_entries:
        if present:
            fake_native_namespace[entry_name] = expected

    with monkeypatch.context() as attack:
        attack.setitem(sys.modules, native_os_name, fake_native_os_module)
        object.__setattr__(
            authority,
            "native_os_module",
            fake_native_os_module,
        )
        try:
            (
                forged_slots,
                forged_descriptor_get,
                forged_fingerprint,
            ) = mutation_toolchain._build_source_guard_attribute_authority_fingerprint(
                authority
            )
            attack.setattr(
                mutation_toolchain,
                "_SOURCE_GUARD_ATTRIBUTE_AUTHORITY_SLOTS",
                forged_slots,
            )
            attack.setattr(
                mutation_toolchain,
                "_SOURCE_GUARD_MEMBER_DESCRIPTOR_GET",
                forged_descriptor_get,
            )
            attack.setattr(
                mutation_toolchain,
                "_SOURCE_GUARD_ATTRIBUTE_AUTHORITY_FINGERPRINT",
                forged_fingerprint,
            )
            attack.setattr(
                raw_attribute,
                "__defaults__",
                (
                    authority,
                    forged_slots,
                    forged_descriptor_get,
                    forged_fingerprint,
                ),
            )

            with pytest.raises(
                MutationToolchainError,
                match="source guard os provider graph changed",
            ):
                mutation_toolchain._verify_loaded_bindings(
                    module,
                    bindings=[binding],
                    attested_code_identities=attested,
                    admitted_source_paths=admitted_paths,
                    admitted_class_ids=frozenset(),
                    policy=policy,
                )
        finally:
            object.__setattr__(
                authority,
                "native_os_module",
                native_os_module,
            )

    assert raw_attribute.__defaults__ is original_defaults
    assert authority.native_os_module is native_os_module
    assert sys.modules[native_os_name] is native_os_module
    assert mutation_toolchain._RUNTIME_SOURCE_SENTINELS == {}


def test_non_windows_copy_from_symlink_rejects_windows_candidate_before_first_seal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_path = tmp_path / "non_windows_pathlib_probe.py"
    source = (
        b'PLATFORM = "posix"\n'
        b"class Path:\n"
        b'    if PLATFORM == "nt":\n'
        b"        def _copy_from_symlink(self):\n"
        b'            return "nt"\n'
        b"    else:\n"
        b"        def _copy_from_symlink(self):\n"
        b'            return "posix"\n'
    )
    source_path.write_bytes(source)
    module = ModuleType("non_windows_pathlib_probe")
    module.__file__ = str(source_path)
    code = compile(
        source,
        str(source_path),
        "exec",
        dont_inherit=True,
        optimize=sys.flags.optimize,
    )
    exec(code, vars(module))
    entries, policy, bindings = mutation_toolchain._sealed_source_variant_payload(
        source,
        source_path=source_path,
        variant="raw",
    )
    binding = next(
        item
        for item in bindings
        if item["path"] == "Path._copy_from_symlink"
    )
    attested = frozenset(
        (
            entry["qualname"],
            entry["firstlineno"],
            entry["firstcol"],
            entry["sha256"],
        )
        for entry in entries
    )

    pending = [code]
    candidate_codes: list[CodeType] = []
    while pending:
        current = pending.pop()
        for constant in current.co_consts:
            if type(constant) is CodeType:
                pending.append(constant)
                if constant.co_qualname == "Path._copy_from_symlink":
                    candidate_codes.append(constant)
    windows_code = next(
        item for item in candidate_codes if item.co_firstlineno == 4
    )
    path_type = vars(module)["Path"]
    active = vars(path_type)["_copy_from_symlink"]
    assert active.__code__.co_firstlineno == 7
    monkeypatch.setattr(mutation_toolchain, "_RUNTIME_SOURCE_SENTINELS", {})
    mutation_toolchain._verify_loaded_bindings(
        module,
        bindings=[binding],
        attested_code_identities=attested,
        admitted_source_paths=frozenset(
            {os.path.normcase(os.fspath(source_path))}
        ),
        admitted_class_ids=frozenset(),
        policy=policy,
    )
    monkeypatch.setattr(active, "__code__", windows_code)

    with pytest.raises(
        MutationToolchainError,
        match="callable binding changed",
    ):
        mutation_toolchain._verify_loaded_bindings(
            module,
            bindings=[binding],
            attested_code_identities=attested,
            admitted_source_paths=frozenset(
                {os.path.normcase(os.fspath(source_path))}
            ),
            admitted_class_ids=frozenset(),
            policy=policy,
        )
    assert mutation_toolchain._RUNTIME_SOURCE_SENTINELS == {}


def test_source_default_ast_drift_changes_binding_manifest(tmp_path: Path) -> None:
    source_path = tmp_path / "source_default_probe.py"
    expected = (
        b"import datetime as dt\n"
        b"def dates(min_value=dt.date.min, max_value=dt.date.max):\n"
        b"    return min_value, max_value\n"
    )
    swapped = (
        b"import datetime as dt\n"
        b"def dates(min_value=dt.date.max, max_value=dt.date.min):\n"
        b"    return min_value, max_value\n"
    )
    source_path.write_bytes(expected)
    expected_entries, expected_policy, expected_bindings = (
        mutation_toolchain._sealed_source_variant_payload(
            expected,
            source_path=source_path,
            variant="raw",
        )
    )
    swapped_entries, swapped_policy, swapped_bindings = (
        mutation_toolchain._sealed_source_variant_payload(
            swapped,
            source_path=source_path,
            variant="raw",
        )
    )
    assert expected_entries == swapped_entries
    expected_topology = mutation_toolchain._binding_topology_payload(
        expected_policy,
        expected_bindings,
    )
    swapped_topology = mutation_toolchain._binding_topology_payload(
        swapped_policy,
        swapped_bindings,
    )
    assert expected_topology != swapped_topology
    assert mutation_toolchain._sha256_bytes(
        mutation_toolchain._canonical_json_bytes(expected_topology)
    ) != mutation_toolchain._sha256_bytes(
        mutation_toolchain._canonical_json_bytes(swapped_topology)
    )


def test_pytest_argcomplete_guard_is_explicit_non_completion_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "_pytest._argcomplete"
    module = import_module(module_name)
    source_path = Path(str(module.__file__)).resolve(strict=True)
    policy = _loaded_source_policy(module)
    binding = next(
        item
        for item in policy.bindings
        if item.path == ("try_argcomplete",)
    )
    assert len(binding.candidates) == 2
    assert all(candidate.guards_complete for candidate in binding.candidates)
    assert tuple(
        (
            candidate.first_line,
            candidate.guards[0].expression.kind,
            candidate.guards[0].expression.payload,
            candidate.guards[0].branch,
        )
        for candidate in binding.candidates
    ) == (
        (
            109,
            "pytest-argcomplete-mode",
            ("os", "environ", "get", "_ARGCOMPLETE", "disabled"),
            True,
        ),
        (
            114,
            "pytest-argcomplete-mode",
            ("os", "environ", "get", "_ARGCOMPLETE", "disabled"),
            False,
        ),
    )

    active = vars(module)["try_argcomplete"]
    assert active.__code__.co_firstlineno == 114
    completion_code = _compiled_source_candidate_code(
        source_path.read_bytes(),
        source_path=source_path,
        qualname="try_argcomplete",
        first_line=109,
    )
    callbacks: list[str] = []

    class HostileEnvironment(dict[str, str]):
        def get(self, key: str, default: object = None) -> object:
            callbacks.append(key)
            return super().get(key, default)

    hostile_environment = HostileEnvironment({"_ARGCOMPLETE": "1"})
    monkeypatch.setattr(mutation_toolchain, "_RUNTIME_SOURCE_SENTINELS", {})
    monkeypatch.setattr(os, "environ", hostile_environment)
    _verify_selected_binding(
        module_name,
        "try_argcomplete",
        admitted_module_names=(module_name,),
    )
    assert callbacks == []

    monkeypatch.setattr(active, "__code__", completion_code)
    with pytest.raises(MutationToolchainError, match="callable binding changed"):
        _verify_selected_binding(
            module_name,
            "try_argcomplete",
            admitted_module_names=(module_name,),
        )
    assert callbacks == []
    assert mutation_toolchain._RUNTIME_SOURCE_SENTINELS == {}


@pytest.mark.parametrize(
    "residue",
    ("argcomplete", "filescompleter"),
)
def test_pytest_argcomplete_false_branch_rejects_completion_residue(
    monkeypatch: pytest.MonkeyPatch,
    residue: str,
) -> None:
    module_name = "_pytest._argcomplete"
    module = import_module(module_name)
    monkeypatch.setattr(mutation_toolchain, "_RUNTIME_SOURCE_SENTINELS", {})
    _verify_selected_binding(
        module_name,
        "try_argcomplete",
        admitted_module_names=(module_name,),
    )
    monkeypatch.setattr(
        module,
        residue,
        ModuleType("argcomplete") if residue == "argcomplete" else object(),
        raising=False,
    )

    with pytest.raises(
        MutationToolchainError,
        match="pytest argcomplete non-completion policy changed",
    ):
        _verify_selected_binding(
            module_name,
            "try_argcomplete",
            admitted_module_names=(module_name,),
        )
    assert mutation_toolchain._RUNTIME_SOURCE_SENTINELS == {}


def test_pytest_argcomplete_guard_rejects_copied_os_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "_pytest._argcomplete"
    module = import_module(module_name)
    copied_os = ModuleType("os")
    vars(copied_os).update(vars(os))
    monkeypatch.setattr(mutation_toolchain, "_RUNTIME_SOURCE_SENTINELS", {})
    _verify_selected_binding(
        module_name,
        "try_argcomplete",
        admitted_module_names=(module_name,),
    )
    monkeypatch.setattr(module, "os", copied_os)

    with pytest.raises(
        MutationToolchainError,
        match="pytest argcomplete os provider changed",
    ):
        _verify_selected_binding(
            module_name,
            "try_argcomplete",
            admitted_module_names=(module_name,),
        )
    assert mutation_toolchain._RUNTIME_SOURCE_SENTINELS == {}


def test_pytest_argcomplete_guard_rejects_coordinated_copied_os_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "_pytest._argcomplete"
    module = import_module(module_name)
    copied_os = ModuleType("os")
    vars(copied_os).update(vars(os))
    captured_modules = dict(
        mutation_toolchain._MODULE_OBJECTS_BEFORE_TOOLCHAIN_IMPORT
    )
    captured_os = captured_modules["os"]
    captured_modules["os"] = (copied_os, *captured_os[1:])
    monkeypatch.setattr(mutation_toolchain, "_RUNTIME_SOURCE_SENTINELS", {})
    _verify_selected_binding(
        module_name,
        "try_argcomplete",
        admitted_module_names=(module_name,),
    )
    monkeypatch.setattr(module, "os", copied_os)
    monkeypatch.setitem(sys.modules, "os", copied_os)
    monkeypatch.setattr(
        mutation_toolchain,
        "_MODULE_OBJECTS_BEFORE_TOOLCHAIN_IMPORT",
        MappingProxyType(captured_modules),
    )

    with pytest.raises(
        MutationToolchainError,
        match="source guard os provider graph changed",
    ):
        _verify_selected_binding(
            module_name,
            "try_argcomplete",
            admitted_module_names=(module_name,),
        )
    assert mutation_toolchain._RUNTIME_SOURCE_SENTINELS == {}


def test_pytest_argcomplete_guard_rejects_cloned_os_function_graph(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "_pytest._argcomplete"
    module = import_module(module_name)
    copied_os = ModuleType("os")
    copied_namespace = vars(copied_os)
    copied_namespace.update(vars(os))

    def clone(function: FunctionType) -> FunctionType:
        cloned = FunctionType(
            function.__code__,
            copied_namespace,
            function.__name__,
            function.__defaults__,
            function.__closure__,
        )
        cloned.__kwdefaults__ = function.__kwdefaults__
        cloned.__module__ = function.__module__
        cloned.__qualname__ = function.__qualname__
        return cloned

    copied_namespace["getenv"] = clone(os.getenv)
    environ_type = vars(os)["_Environ"]
    environ_getitem = type.__getattribute__(environ_type, "__dict__")[
        "__getitem__"
    ]
    cloned_getitem = clone(environ_getitem)
    forged_environ_type = type(
        "_Environ",
        (),
        {
            "__getitem__": cloned_getitem,
            "__module__": "os",
            "__qualname__": "_Environ",
        },
    )
    copied_namespace["_Environ"] = forged_environ_type

    monkeypatch.setattr(mutation_toolchain, "_RUNTIME_SOURCE_SENTINELS", {})
    _verify_selected_binding(
        module_name,
        "try_argcomplete",
        admitted_module_names=(module_name,),
    )
    monkeypatch.setattr(module, "os", copied_os)
    monkeypatch.setitem(sys.modules, "os", copied_os)

    with pytest.raises(
        MutationToolchainError,
        match="source guard os provider graph changed",
    ):
        _verify_selected_binding(
            module_name,
            "try_argcomplete",
            admitted_module_names=(module_name,),
        )
    assert mutation_toolchain._RUNTIME_SOURCE_SENTINELS == {}


@pytest.mark.parametrize(
    ("prelude", "condition"),
    (
        ("import os", 'os.environ.get("OTHER")'),
        ("import os", 'os.environ.get("_ARGCOMPLETE", "1")'),
        ("import os", 'os.environ.get(key="_ARGCOMPLETE")'),
        ("import os", 'os.getenv("_ARGCOMPLETE")'),
        ("import os as platform_os", 'platform_os.environ.get("_ARGCOMPLETE")'),
        ("mapping = {}", 'mapping.get("_ARGCOMPLETE")'),
    ),
)
def test_source_environment_method_call_variants_remain_unsupported(
    tmp_path: Path,
    prelude: str,
    condition: str,
) -> None:
    source_path = tmp_path / "environment_guard_variant.py"
    source = (
        f"{prelude}\n"
        f"if {condition}:\n"
        "    def target():\n"
        "        return True\n"
        "else:\n"
        "    def target():\n"
        "        return False\n"
    ).encode("utf-8")
    source_path.write_bytes(source)
    _entries, _policy, bindings = (
        mutation_toolchain._sealed_source_variant_payload(
            source,
            source_path=source_path,
            variant="raw",
        )
    )
    binding = next(item for item in bindings if item["path"] == "target")
    assert len(binding["candidates"]) == 2
    assert all(
        candidate["guards_complete"] is False
        and candidate["guards"][0]["expression"]["kind"] == "unsupported"
        for candidate in binding["candidates"]
    )


def test_pytest_capture_result_uses_exact_python_compatibility_guard() -> None:
    module = import_module("_pytest.capture")
    policy = _loaded_source_policy(module)
    binding = next(
        item for item in policy.bindings if item.path == ("CaptureResult",)
    )
    assert tuple(
        (
            candidate.first_line,
            candidate.guards_complete,
            candidate.guards,
        )
        for candidate in binding.candidates
    ) == (
        (
            610,
            True,
            (
                mutation_toolchain._SourceExpressionGuard(
                    expression=mutation_toolchain._SourceExpression(
                        kind="python-version-or-type-checking",
                        payload=("ge", (3, 11), "direct"),
                        ast_shape=(
                            "BoolOp(op=Or(), values=[Compare(left=Attribute("
                            "value=Name(id='sys', ctx=Load()), "
                            "attr='version_info', ctx=Load()), ops=[GtE()], "
                            "comparators=[Tuple(elts=[Constant(value=3), "
                            "Constant(value=11)], ctx=Load())]), "
                            "Name(id='TYPE_CHECKING', ctx=Load())])"
                        ),
                    ),
                    branch=True,
                ),
            ),
        ),
        (
            619,
            True,
            (
                mutation_toolchain._SourceExpressionGuard(
                    expression=mutation_toolchain._SourceExpression(
                        kind="python-version-or-type-checking",
                        payload=("ge", (3, 11), "direct"),
                        ast_shape=(
                            "BoolOp(op=Or(), values=[Compare(left=Attribute("
                            "value=Name(id='sys', ctx=Load()), "
                            "attr='version_info', ctx=Load()), ops=[GtE()], "
                            "comparators=[Tuple(elts=[Constant(value=3), "
                            "Constant(value=11)], ctx=Load())]), "
                            "Name(id='TYPE_CHECKING', ctx=Load())])"
                        ),
                    ),
                    branch=False,
                ),
            ),
        ),
    )

    active = mutation_toolchain._active_source_binding_candidate(
        module,
        policy=policy,
        binding=binding,
    )
    assert active is not None
    assert active.first_line == 610


def test_pytest_capture_compatibility_guard_rejects_copied_sys_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = import_module("_pytest.capture")
    policy = _loaded_source_policy(module)
    binding = next(
        item for item in policy.bindings if item.path == ("CaptureResult",)
    )
    copied_sys = ModuleType("sys")
    vars(copied_sys).update(vars(sys))
    monkeypatch.setattr(module, "sys", copied_sys)
    monkeypatch.setitem(sys.modules, "sys", copied_sys)

    with pytest.raises(
        MutationToolchainError,
        match="class version provider changed",
    ):
        mutation_toolchain._active_source_binding_candidate(
            module,
            policy=policy,
            binding=binding,
        )


def test_pytest_capture_compatibility_guard_rejects_equal_distinct_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = import_module("_pytest.capture")
    policy = _loaded_source_policy(module)
    binding = next(
        item for item in policy.bindings if item.path == ("CaptureResult",)
    )
    monkeypatch.setattr(sys, "version_info", tuple(sys.version_info))

    with pytest.raises(MutationToolchainError, match="sys.version_info"):
        mutation_toolchain._active_source_binding_candidate(
            module,
            policy=policy,
            binding=binding,
        )


def test_pytest_capture_compatibility_guard_validates_type_checking_eagerly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = import_module("_pytest.capture")
    policy = _loaded_source_policy(module)
    binding = next(
        item for item in policy.bindings if item.path == ("CaptureResult",)
    )
    assert sys.version_info >= (3, 11)
    monkeypatch.setattr(typing, "TYPE_CHECKING", True)
    monkeypatch.setattr(module, "TYPE_CHECKING", True)

    with pytest.raises(MutationToolchainError, match="TYPE_CHECKING"):
        mutation_toolchain._active_source_binding_candidate(
            module,
            policy=policy,
            binding=binding,
        )


@pytest.mark.parametrize(
    ("member_name", "first_lines"),
    (
        ("glob", (489, 495, 507)),
        ("rglob", (685, 691, 700)),
    ),
)
def test_anyio_path_uses_exact_half_open_python_version_range(
    monkeypatch: pytest.MonkeyPatch,
    member_name: str,
    first_lines: tuple[int, int, int],
) -> None:
    module_name = "anyio._core._fileio"
    module = import_module(module_name)
    policy = _loaded_source_policy(module)
    binding = next(
        item for item in policy.bindings if item.path == ("Path", member_name)
    )
    assert tuple(candidate.first_line for candidate in binding.candidates) == (
        first_lines
    )
    assert tuple(candidate.guards_complete for candidate in binding.candidates) == (
        True,
        True,
        True,
    )
    assert tuple(candidate.guards for candidate in binding.candidates) == (
        (
            mutation_toolchain._SourceVersionGuard("lt", (3, 12), True),
        ),
        (
            mutation_toolchain._SourceVersionGuard("lt", (3, 12), False),
            mutation_toolchain._SourceVersionRangeGuard(
                (3, 12),
                (3, 13),
                True,
            ),
        ),
        (
            mutation_toolchain._SourceVersionGuard("lt", (3, 12), False),
            mutation_toolchain._SourceVersionRangeGuard(
                (3, 12),
                (3, 13),
                False,
            ),
            mutation_toolchain._SourceVersionGuard("ge", (3, 13), True),
        ),
    )
    range_guard = binding.candidates[1].guards[1]
    assert mutation_toolchain._source_guard_manifest(range_guard) == {
        "kind": "version-range",
        "lower": [3, 12],
        "upper": [3, 13],
        "branch": True,
    }

    active = mutation_toolchain._active_source_binding_candidate(
        module,
        policy=policy,
        binding=binding,
    )
    assert active is not None
    runtime_member = vars(vars(module)["Path"])[member_name]
    assert active.first_line == runtime_member.__code__.co_firstlineno

    monkeypatch.setattr(mutation_toolchain, "_RUNTIME_SOURCE_SENTINELS", {})
    _verify_selected_binding(
        module_name,
        f"Path.{member_name}",
        admitted_module_names=(module_name,),
    )
    assert mutation_toolchain._RUNTIME_SOURCE_SENTINELS == {}


def test_anyio_path_version_range_rejects_copied_sys_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = import_module("anyio._core._fileio")
    policy = _loaded_source_policy(module)
    binding = next(
        item for item in policy.bindings if item.path == ("Path", "glob")
    )
    copied_sys = ModuleType("sys")
    vars(copied_sys).update(vars(sys))
    monkeypatch.setattr(module, "sys", copied_sys)

    with pytest.raises(MutationToolchainError, match="version provider changed"):
        mutation_toolchain._active_source_binding_candidate(
            module,
            policy=policy,
            binding=binding,
        )


def test_anyio_path_version_range_rejects_coordinated_sys_copy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = import_module("anyio._core._fileio")
    policy = _loaded_source_policy(module)
    binding = next(
        item for item in policy.bindings if item.path == ("Path", "glob")
    )
    copied_sys = ModuleType("sys")
    vars(copied_sys).update(vars(sys))
    monkeypatch.setattr(module, "sys", copied_sys)
    monkeypatch.setattr(mutation_toolchain, "sys", copied_sys)
    monkeypatch.setitem(sys.modules, "sys", copied_sys)

    with pytest.raises(
        MutationToolchainError,
        match="source import provider module changed: sys",
    ):
        mutation_toolchain._active_source_binding_candidate(
            module,
            policy=policy,
            binding=binding,
        )


def test_anyio_path_version_range_rejects_equal_distinct_version_info(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = import_module("anyio._core._fileio")
    policy = _loaded_source_policy(module)
    binding = next(
        item for item in policy.bindings if item.path == ("Path", "glob")
    )
    monkeypatch.setattr(sys, "version_info", tuple(sys.version_info))

    with pytest.raises(MutationToolchainError, match=r"sys\.version_info"):
        mutation_toolchain._active_source_binding_candidate(
            module,
            policy=policy,
            binding=binding,
        )


def test_anyio_path_version_range_rejects_hostile_tuple_without_callback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = import_module("anyio._core._fileio")
    policy = _loaded_source_policy(module)
    binding = next(
        item for item in policy.bindings if item.path == ("Path", "glob")
    )
    callbacks: list[object] = []

    def hostile_tuple(value: object) -> tuple[int, int]:
        callbacks.append(value)
        return (3, 12)

    original_tuple = builtins.tuple
    monkeypatch.setattr(builtins, "tuple", hostile_tuple)
    try:
        try:
            mutation_toolchain._active_source_binding_candidate(
                module,
                policy=policy,
                binding=binding,
            )
        except MutationToolchainError as exc:
            error = str(exc)
        else:
            error = ""
        callback_count = len(callbacks)
    finally:
        builtins.tuple = original_tuple

    assert "version tuple provider changed" in error
    assert callback_count == 0


def test_anyio_path_version_range_rejects_inactive_candidate_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "anyio._core._fileio"
    module = import_module(module_name)
    source_path = Path(str(module.__file__)).resolve(strict=True)
    source = source_path.read_bytes()
    policy = _loaded_source_policy(module)
    binding = next(
        item for item in policy.bindings if item.path == ("Path", "glob")
    )
    active = vars(vars(module)["Path"])["glob"]
    inactive = next(
        candidate
        for candidate in binding.candidates
        if candidate.first_line == 495
    )
    inactive_code = _compiled_source_candidate_code(
        source,
        source_path=source_path,
        qualname=inactive.qualname,
        first_line=inactive.first_line,
    )
    monkeypatch.setattr(mutation_toolchain, "_RUNTIME_SOURCE_SENTINELS", {})
    _verify_selected_binding(
        module_name,
        "Path.glob",
        admitted_module_names=(module_name,),
    )
    monkeypatch.setattr(active, "__code__", inactive_code)

    with pytest.raises(MutationToolchainError, match="callable binding changed"):
        _verify_selected_binding(
            module_name,
            "Path.glob",
            admitted_module_names=(module_name,),
        )
    assert mutation_toolchain._RUNTIME_SOURCE_SENTINELS == {}


@pytest.mark.parametrize(
    ("prelude", "condition"),
    (
        ("import sys", "(3, 12) < sys.version_info <= (3, 15)"),
        (
            "import sys",
            "sys.version_info >= (3, 12) and sys.version_info < (3, 15)",
        ),
        ("import sys as system", "(3, 12) <= system.version_info < (3, 15)"),
        ("from sys import version_info", "(3, 12) <= version_info < (3, 15)"),
        (
            "import sys\nlower = (3, 12)",
            "lower <= sys.version_info < (3, 15)",
        ),
        ("import sys", "(3, 15) > sys.version_info >= (3, 12)"),
        ("import sys", "not ((3, 15) <= sys.version_info < (3, 20))"),
        ("import sys", "sys.version_info[:2] >= (3, 12)"),
    ),
)
def test_source_python_version_range_variants_remain_fail_closed(
    tmp_path: Path,
    prelude: str,
    condition: str,
) -> None:
    source_path = tmp_path / "python_version_range_variant.py"
    source = (
        f"{prelude}\n"
        f"if {condition}:\n"
        "    def target():\n"
        "        return True\n"
        "else:\n"
        "    def target():\n"
        "        return False\n"
    ).encode("utf-8")
    source_path.write_bytes(source)
    module = ModuleType("python_version_range_variant")
    module.__file__ = str(source_path)
    module.__package__ = ""
    module.__spec__ = spec_from_loader(
        module.__name__,
        SourceFileLoader(module.__name__, str(source_path)),
    )
    exec(
        compile(
            source,
            str(source_path),
            "exec",
            dont_inherit=True,
            optimize=sys.flags.optimize,
        ),
        vars(module),
    )
    _entries, policy, _bindings = (
        mutation_toolchain._sealed_source_variant_payload(
            source,
            source_path=source_path,
            variant="raw",
        )
    )
    binding = next(item for item in policy.bindings if item.path == ("target",))
    assert not any(
        type(guard) is mutation_toolchain._SourceVersionRangeGuard
        for candidate in binding.candidates
        for guard in candidate.guards
    )

    with pytest.raises(MutationToolchainError):
        mutation_toolchain._active_source_binding_candidate(
            module,
            policy=policy,
            binding=binding,
        )


@pytest.mark.parametrize(
    "condition",
    (
        "(3, True) <= sys.version_info < (3, 15)",
        '(3, "12") <= sys.version_info < (3, 15)',
        "() <= sys.version_info < (3, 15)",
        "(3, -1) <= sys.version_info < (3, 15)",
        "(3, 12) <= sys.version_info < upper",
        "(3, 12) <= sys.version_info < (3, 15, patch)",
        "(3, 12) <= sys.version_info < (3, 15) < (3, 20)",
    ),
)
def test_source_python_version_range_nonliteral_bounds_are_not_admitted(
    tmp_path: Path,
    condition: str,
) -> None:
    source_path = tmp_path / "python_version_range_nonliteral.py"
    source = (
        "import sys\n"
        "upper = (3, 15)\n"
        "patch = 0\n"
        f"if {condition}:\n"
        "    def target():\n"
        "        return True\n"
        "else:\n"
        "    def target():\n"
        "        return False\n"
    ).encode("utf-8")
    source_path.write_bytes(source)
    _entries, policy, _bindings = (
        mutation_toolchain._sealed_source_variant_payload(
            source,
            source_path=source_path,
            variant="raw",
        )
    )
    binding = next(item for item in policy.bindings if item.path == ("target",))
    assert not any(
        type(guard) is mutation_toolchain._SourceVersionRangeGuard
        for candidate in binding.candidates
        for guard in candidate.guards
    )


def test_pytest_compat_assert_never_admits_exact_guarded_import(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "_pytest.compat"
    module = import_module(module_name)
    policy = _loaded_source_policy(module)
    source_binding = next(
        item for item in policy.bindings if item.path == ("assert_never",)
    )
    import_binding = next(
        item for item in policy.imports if item.name == "assert_never"
    )
    assert source_binding.candidates[0].guards == (
        mutation_toolchain._SourceVersionGuard("ge", (3, 11), False),
    )
    assert import_binding == mutation_toolchain._SourceImportBinding(
        name="assert_never",
        required=False,
        may_be_overwritten=True,
        candidates=(
            mutation_toolchain._SourceImportCandidate(
                module="typing",
                level=0,
                attribute="assert_never",
                star=False,
            ),
        ),
        overwrite_candidates=(),
    )
    assert vars(module)["assert_never"] is typing.assert_never
    monkeypatch.setattr(mutation_toolchain, "_RUNTIME_SOURCE_SENTINELS", {})

    _verify_selected_binding(
        module_name,
        "assert_never",
        admitted_module_names=(module_name,),
    )
    assert mutation_toolchain._RUNTIME_SOURCE_SENTINELS == {}


def test_pytest_compat_assert_never_rejects_copied_consumer_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "_pytest.compat"
    module = import_module(module_name)
    copied_module = ModuleType(module_name)
    vars(copied_module).update(vars(module))
    monkeypatch.setattr(mutation_toolchain, "_RUNTIME_SOURCE_SENTINELS", {})
    monkeypatch.setitem(sys.modules, module_name, copied_module)

    with pytest.raises(
        MutationToolchainError,
        match="inactive source binding is unexpectedly present",
    ):
        _verify_selected_binding(
            module_name,
            "assert_never",
            admitted_module_names=(module_name,),
        )
    assert mutation_toolchain._RUNTIME_SOURCE_SENTINELS == {}


def test_pytest_compat_assert_never_rejects_consumer_only_clone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "_pytest.compat"
    module = import_module(module_name)
    provider = typing.assert_never
    cloned = FunctionType(
        provider.__code__,
        provider.__globals__,
        provider.__name__,
        provider.__defaults__,
        provider.__closure__,
    )
    cloned.__annotations__ = dict(provider.__annotations__)
    cloned.__kwdefaults__ = provider.__kwdefaults__
    cloned.__module__ = provider.__module__
    cloned.__qualname__ = provider.__qualname__
    monkeypatch.setattr(mutation_toolchain, "_RUNTIME_SOURCE_SENTINELS", {})
    monkeypatch.setattr(module, "assert_never", cloned)

    with pytest.raises(
        MutationToolchainError,
        match="inactive source binding is unexpectedly present",
    ):
        _verify_selected_binding(
            module_name,
            "assert_never",
            admitted_module_names=(module_name,),
        )
    assert mutation_toolchain._RUNTIME_SOURCE_SENTINELS == {}


def test_pytest_compat_assert_never_rejects_missing_active_import(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "_pytest.compat"
    module = import_module(module_name)
    monkeypatch.delattr(module, "assert_never")

    with pytest.raises(
        MutationToolchainError,
        match="loaded source imported alternative is missing",
    ):
        _verify_selected_binding(
            module_name,
            "assert_never",
            admitted_module_names=(module_name,),
        )


def test_pytest_compat_assert_never_rejects_coordinated_provider_clone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "_pytest.compat"
    module = import_module(module_name)
    provider = typing.assert_never
    cloned = FunctionType(
        provider.__code__,
        provider.__globals__,
        provider.__name__,
        provider.__defaults__,
        provider.__closure__,
    )
    cloned.__annotations__ = dict(provider.__annotations__)
    cloned.__kwdefaults__ = provider.__kwdefaults__
    cloned.__module__ = provider.__module__
    cloned.__qualname__ = provider.__qualname__
    monkeypatch.setattr(mutation_toolchain, "_RUNTIME_SOURCE_SENTINELS", {})
    monkeypatch.setattr(typing, "assert_never", cloned)
    monkeypatch.setattr(module, "assert_never", cloned)

    with pytest.raises(
        MutationToolchainError,
        match=r"typing\.assert_never",
    ):
        _verify_selected_binding(
            module_name,
            "assert_never",
            admitted_module_names=(module_name,),
        )
    assert mutation_toolchain._RUNTIME_SOURCE_SENTINELS == {}


def test_pytest_compat_assert_never_rejects_equal_distinct_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "_pytest.compat"
    monkeypatch.setattr(mutation_toolchain, "_RUNTIME_SOURCE_SENTINELS", {})
    monkeypatch.setattr(sys, "version_info", tuple(sys.version_info))

    with pytest.raises(MutationToolchainError, match="sys.version_info"):
        _verify_selected_binding(
            module_name,
            "assert_never",
            admitted_module_names=(module_name,),
        )
    assert mutation_toolchain._RUNTIME_SOURCE_SENTINELS == {}


def test_pytest_compat_assert_never_admission_rejects_policy_shape_drift() -> None:
    module = import_module("_pytest.compat")
    policy = _loaded_source_policy(module)
    source_binding = next(
        item for item in policy.bindings if item.path == ("assert_never",)
    )
    fallback = source_binding.candidates[0]
    forged_source_binding = replace(
        source_binding,
        candidates=(
            replace(
                fallback,
                guards=(
                    mutation_toolchain._SourceVersionGuard(
                        "ge",
                        (3, 11),
                        True,
                    ),
                ),
            ),
        ),
    )
    import_binding = next(
        item for item in policy.imports if item.name == "assert_never"
    )
    forged_import_binding = replace(
        import_binding,
        candidates=(
            mutation_toolchain._SourceImportCandidate(
                module="collections",
                level=0,
                attribute="namedtuple",
                star=False,
            ),
        ),
    )
    forged_policy = replace(
        policy,
        imports=tuple(
            forged_import_binding if item is import_binding else item
            for item in policy.imports
        ),
    )
    value = vars(module)["assert_never"]

    assert not mutation_toolchain._exact_inactive_source_import_binding(
        module,
        policy=policy,
        source_binding=forged_source_binding,
        value=value,
    )
    assert not mutation_toolchain._exact_inactive_source_import_binding(
        module,
        policy=forged_policy,
        source_binding=source_binding,
        value=value,
    )


@_REQUIRES_IMPORTED_ASYNCIO_RUNNER
def test_anyio_runner_admits_exact_version_selected_asyncio_import(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "anyio._backends._asyncio"
    module = import_module(module_name)
    asyncio_module = import_module("asyncio")
    runners_module = import_module("asyncio.runners")
    policy = _loaded_source_policy(module)
    source_binding = next(
        item for item in policy.bindings if item.path == ("Runner",)
    )
    import_binding = next(
        item for item in policy.imports if item.name == "Runner"
    )
    assert source_binding == mutation_toolchain._SourceBinding(
        path=("Runner",),
        kind="class",
        accessor="direct",
        required=False,
        must_be_absent=False,
        candidates=(
            mutation_toolchain._SourceBindingCandidate(
                qualname="Runner",
                first_line=128,
                definition_line=128,
                decorators=(),
                function_semantics=None,
                guards=(
                    mutation_toolchain._SourceVersionGuard(
                        "ge",
                        (3, 11),
                        False,
                    ),
                ),
                guards_complete=True,
            ),
        ),
    )
    assert import_binding == mutation_toolchain._SourceImportBinding(
        name="Runner",
        required=False,
        may_be_overwritten=True,
        candidates=(
            mutation_toolchain._SourceImportCandidate(
                module="asyncio",
                level=0,
                attribute="Runner",
                star=False,
            ),
        ),
        overwrite_candidates=(),
    )
    assert vars(module)["Runner"] is vars(asyncio_module)["Runner"]
    assert vars(module)["Runner"] is vars(runners_module)["Runner"]
    monkeypatch.setattr(mutation_toolchain, "_RUNTIME_SOURCE_SENTINELS", {})

    _verify_selected_binding(
        module_name,
        "Runner",
        admitted_module_names=(module_name,),
    )
    assert mutation_toolchain._RUNTIME_SOURCE_SENTINELS == {}


@_REQUIRES_IMPORTED_ASYNCIO_RUNNER
@pytest.mark.parametrize(
    "member",
    (
        "__enter__",
        "__exit__",
        "__init__",
        "_lazy_init",
        "_on_sigint",
        "close",
        "get_loop",
        "run",
    ),
)
def test_anyio_runner_import_shadows_exact_fallback_member(member: str) -> None:
    module_name = "anyio._backends._asyncio"
    module = import_module(module_name)
    runners_module = import_module("asyncio.runners")
    provider = vars(runners_module)["Runner"]
    assert vars(module)["Runner"] is provider
    assert member in vars(provider)

    _verify_selected_binding(
        module_name,
        f"Runner.{member}",
        admitted_module_names=(module_name,),
    )


@_REQUIRES_IMPORTED_ASYNCIO_RUNNER
def test_anyio_runner_rejects_in_place_provider_member_rebind(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "anyio._backends._asyncio"
    runners_module = import_module("asyncio.runners")
    provider = vars(runners_module)["Runner"]

    def forged_enter(_self: object) -> object:
        return _self

    monkeypatch.setattr(provider, "__enter__", forged_enter)

    with pytest.raises(
        MutationToolchainError,
        match="inactive source binding is unexpectedly present",
    ):
        _verify_selected_binding(
            module_name,
            "Runner.__enter__",
            admitted_module_names=(module_name,),
        )


@_REQUIRES_IMPORTED_ASYNCIO_RUNNER
def test_anyio_runner_rejects_in_place_provider_member_code_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "anyio._backends._asyncio"
    runners_module = import_module("asyncio.runners")
    provider = vars(runners_module)["Runner"]
    original_enter = vars(provider)["__enter__"]

    def forged_enter(_self: object) -> object:
        return _self

    monkeypatch.setattr(original_enter, "__code__", forged_enter.__code__)

    with pytest.raises(
        MutationToolchainError,
        match="inactive source binding is unexpectedly present",
    ):
        _verify_selected_binding(
            module_name,
            "Runner.__enter__",
            admitted_module_names=(module_name,),
        )


@_REQUIRES_IMPORTED_ASYNCIO_RUNNER
def test_anyio_runner_rejects_missing_active_import(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "anyio._backends._asyncio"
    module = import_module(module_name)
    monkeypatch.delattr(module, "Runner")

    with pytest.raises(
        MutationToolchainError,
        match="loaded source imported alternative is missing",
    ):
        _verify_selected_binding(
            module_name,
            "Runner",
            admitted_module_names=(module_name,),
        )


@_REQUIRES_IMPORTED_ASYNCIO_RUNNER
def test_anyio_runner_rejects_consumer_asyncio_link_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "anyio._backends._asyncio"
    module = import_module(module_name)
    asyncio_module = import_module("asyncio")
    copied_asyncio = ModuleType("asyncio")
    vars(copied_asyncio).update(vars(asyncio_module))
    monkeypatch.setattr(module, "asyncio", copied_asyncio)

    with pytest.raises(
        MutationToolchainError,
        match="inactive source binding is unexpectedly present",
    ):
        _verify_selected_binding(
            module_name,
            "Runner",
            admitted_module_names=(module_name,),
        )


@_REQUIRES_IMPORTED_ASYNCIO_RUNNER
def test_anyio_runner_rejects_copied_consumer_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "anyio._backends._asyncio"
    module = import_module(module_name)
    copied_module = ModuleType(module_name)
    vars(copied_module).update(vars(module))
    monkeypatch.setitem(sys.modules, module_name, copied_module)

    with pytest.raises(
        MutationToolchainError,
        match="inactive source binding is unexpectedly present",
    ):
        _verify_selected_binding(
            module_name,
            "Runner",
            admitted_module_names=(module_name,),
        )


@_REQUIRES_IMPORTED_ASYNCIO_RUNNER
def test_anyio_runner_rejects_consumer_only_class_clone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "anyio._backends._asyncio"
    module = import_module(module_name)
    cloned = type("Runner", (object,), {})
    cloned.__module__ = "asyncio.runners"
    cloned.__qualname__ = "Runner"
    monkeypatch.setattr(module, "Runner", cloned)

    with pytest.raises(
        MutationToolchainError,
        match="inactive source binding is unexpectedly present",
    ):
        _verify_selected_binding(
            module_name,
            "Runner",
            admitted_module_names=(module_name,),
        )


@_REQUIRES_IMPORTED_ASYNCIO_RUNNER
def test_anyio_runner_rejects_coordinated_provider_clone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "anyio._backends._asyncio"
    module = import_module(module_name)
    asyncio_module = import_module("asyncio")
    runners_module = import_module("asyncio.runners")
    cloned = type("Runner", (object,), {})
    cloned.__module__ = "asyncio.runners"
    cloned.__qualname__ = "Runner"
    monkeypatch.setattr(module, "Runner", cloned)
    monkeypatch.setattr(asyncio_module, "Runner", cloned)
    monkeypatch.setattr(runners_module, "Runner", cloned)

    with pytest.raises(
        MutationToolchainError,
        match=r"asyncio(?:\.runners)?\.Runner",
    ):
        _verify_selected_binding(
            module_name,
            "Runner",
            admitted_module_names=(module_name,),
        )


@_REQUIRES_IMPORTED_ASYNCIO_RUNNER
def test_anyio_runner_rejects_split_provider_reexport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "anyio._backends._asyncio"
    runners_module = import_module("asyncio.runners")
    cloned = type("Runner", (object,), {})
    cloned.__module__ = "asyncio.runners"
    cloned.__qualname__ = "Runner"
    monkeypatch.setattr(runners_module, "Runner", cloned)

    with pytest.raises(MutationToolchainError, match=r"asyncio\.runners\.Runner"):
        _verify_selected_binding(
            module_name,
            "Runner",
            admitted_module_names=(module_name,),
        )


@_REQUIRES_IMPORTED_ASYNCIO_RUNNER
def test_anyio_runner_rejects_equal_distinct_version_info(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "anyio._backends._asyncio"
    monkeypatch.setattr(sys, "version_info", tuple(sys.version_info))

    with pytest.raises(MutationToolchainError, match="sys.version_info"):
        _verify_selected_binding(
            module_name,
            "Runner",
            admitted_module_names=(module_name,),
        )


@_REQUIRES_IMPORTED_ASYNCIO_RUNNER
def test_anyio_runner_admission_rejects_policy_shape_drift() -> None:
    module = import_module("anyio._backends._asyncio")
    policy = _loaded_source_policy(module)
    source_binding = next(
        item for item in policy.bindings if item.path == ("Runner",)
    )
    fallback = source_binding.candidates[0]
    forged_source_binding = replace(
        source_binding,
        candidates=(
            replace(
                fallback,
                guards=(
                    mutation_toolchain._SourceVersionGuard(
                        "ge",
                        (3, 12),
                        False,
                    ),
                ),
            ),
        ),
    )
    import_binding = next(
        item for item in policy.imports if item.name == "Runner"
    )
    forged_import_binding = replace(
        import_binding,
        candidates=(
            mutation_toolchain._SourceImportCandidate(
                module="asyncio.runners",
                level=0,
                attribute="Runner",
                star=False,
            ),
        ),
    )
    forged_policy = replace(
        policy,
        imports=tuple(
            forged_import_binding if item is import_binding else item
            for item in policy.imports
        ),
    )
    nested_binding = next(
        item for item in policy.bindings if item.path == ("Runner", "__enter__")
    )
    nested_candidate = nested_binding.candidates[0]
    forged_nested_binding = replace(
        nested_binding,
        candidates=(
            replace(
                nested_candidate,
                first_line=nested_candidate.first_line + 1,
            ),
        ),
    )
    forged_nested_policy = replace(
        policy,
        bindings=tuple(
            forged_nested_binding if item is nested_binding else item
            for item in policy.bindings
        ),
    )
    runner_shape = next(
        item for item in policy.classes if item.path == ("Runner",)
    )
    forged_class_policy = replace(
        policy,
        classes=tuple(
            replace(
                runner_shape,
                literal_members=(("injected", ["int", "1"]),),
            )
            if item is runner_shape
            else item
            for item in policy.classes
        ),
    )
    injected_binding = replace(
        nested_binding,
        path=("Runner", "injected"),
        candidates=(
            replace(
                nested_candidate,
                qualname="Runner.injected",
            ),
        ),
    )
    forged_subtree_policy = replace(
        policy,
        bindings=(*policy.bindings, injected_binding),
    )
    value = vars(module)["Runner"]

    assert not mutation_toolchain._exact_inactive_source_import_binding(
        module,
        policy=policy,
        source_binding=forged_source_binding,
        value=value,
    )
    assert not mutation_toolchain._exact_inactive_source_import_binding(
        module,
        policy=forged_policy,
        source_binding=source_binding,
        value=value,
    )
    assert not mutation_toolchain._exact_inactive_source_import_binding(
        module,
        policy=forged_nested_policy,
        source_binding=forged_nested_binding,
        value=vars(value)["__enter__"],
    )
    assert not mutation_toolchain._exact_inactive_source_import_binding(
        module,
        policy=forged_class_policy,
        source_binding=source_binding,
        value=value,
    )
    assert not mutation_toolchain._exact_inactive_source_import_binding(
        module,
        policy=forged_subtree_policy,
        source_binding=source_binding,
        value=value,
    )


def test_hypothesis_pytest_option_uses_exact_source_version_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "_hypothesis_pytestplugin"
    module = import_module(module_name)
    policy = _loaded_source_policy(module)
    binding = next(
        item
        for item in policy.bindings
        if item.path == ("_any_hypothesis_option",)
    )
    assert len(binding.candidates) == 1
    candidate = binding.candidates[0]
    assert candidate.guards_complete
    assert candidate.guards == (
        mutation_toolchain._SourcePytestVersionGuard(
            operator="lt",
            version=(4, 6),
            branch=False,
        ),
    )
    ignore_binding = next(
        item
        for item in policy.bindings
        if item.path == ("pytest_ignore_collect",)
    )
    assert len(ignore_binding.candidates) == 1
    assert ignore_binding.candidates[0].guards == (
        mutation_toolchain._SourcePytestVersionGuard(
            operator="lt",
            version=(4, 6),
            branch=False,
        ),
        mutation_toolchain._SourcePytestVersionGuard(
            operator="ge",
            version=(7,),
            branch=True,
        ),
    )
    _verify_selected_binding(
        module_name,
        "_any_hypothesis_option",
        admitted_module_names=(module_name,),
    )

    pytest_module = import_module("pytest")
    monkeypatch.setattr(pytest_module, "__version__", "3.0")
    with pytest.raises(
        MutationToolchainError,
        match=r"pytest(?:\.__version__| version)",
    ):
        _verify_selected_binding(
            module_name,
            "_any_hypothesis_option",
            admitted_module_names=(module_name,),
        )


@pytest.mark.parametrize("mutation", ["swapped", "duplicate", "fresh_equal"])
def test_hypothesis_dates_source_defaults_reject_coordinated_preseal_mutation(
    mutation: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert not hasattr(
        mutation_toolchain,
        "_ADMITTED_SOURCE_DEFAULT_SINGLETONS",
    )
    module_name = "hypothesis.strategies._internal.datetime"
    module = import_module(module_name)
    public = vars(module)["dates"]
    source = vars(public)["__wrapped__"]
    if mutation == "swapped":
        defaults = (datetime.date.max, datetime.date.min)
    elif mutation == "duplicate":
        defaults = (datetime.date.min, datetime.date.min)
    else:
        fresh_min = datetime.date(1, 1, 1)
        assert fresh_min == datetime.date.min
        assert fresh_min is not datetime.date.min
        defaults = (fresh_min, datetime.date.max)
    monkeypatch.setattr(mutation_toolchain, "_RUNTIME_SOURCE_SENTINELS", {})
    _verify_selected_binding(
        module_name,
        "dates",
        admitted_module_names=(
            module_name,
            "hypothesis.strategies._internal.utils",
        ),
    )
    monkeypatch.setattr(public, "__defaults__", defaults)
    monkeypatch.setattr(source, "__defaults__", defaults)

    with pytest.raises(
        MutationToolchainError,
        match="default tuple changed",
    ):
        _verify_selected_binding(
            module_name,
            "dates",
            admitted_module_names=(
                module_name,
                "hypothesis.strategies._internal.utils",
            ),
        )
    assert mutation_toolchain._RUNTIME_SOURCE_SENTINELS == {}


def test_hypothesis_dates_ignore_injected_default_dispatch_global(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "hypothesis.strategies._internal.datetime"
    module = import_module(module_name)
    public = vars(module)["dates"]
    source = vars(public)["__wrapped__"]
    monkeypatch.setattr(
        mutation_toolchain,
        "_ADMITTED_SOURCE_DEFAULT_SINGLETONS",
        MappingProxyType({}),
        raising=False,
    )
    monkeypatch.setattr(
        public,
        "__defaults__",
        (datetime.date.max, datetime.date.min),
    )
    monkeypatch.setattr(
        source,
        "__defaults__",
        (datetime.date.max, datetime.date.min),
    )

    with pytest.raises(
        MutationToolchainError,
        match="default tuple changed",
    ):
        _verify_selected_binding(
            module_name,
            "dates",
            admitted_module_names=(
                module_name,
                "hypothesis.strategies._internal.utils",
            ),
        )


def test_hypothesis_temporal_defaults_reject_fresh_datetime_provider_aliases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "hypothesis.strategies._internal.datetime"
    module = import_module(module_name)
    original_datetime = sys.modules["datetime"]
    original_builtin_datetime = sys.modules["_datetime"]
    fresh_datetime = ModuleType("datetime")
    vars(fresh_datetime).update(vars(original_datetime))
    fresh_builtin_datetime = ModuleType("_datetime")
    vars(fresh_builtin_datetime).update(vars(original_builtin_datetime))
    assert fresh_datetime is not original_datetime
    assert fresh_builtin_datetime is not original_builtin_datetime
    assert vars(fresh_datetime)["date"] is datetime.date
    assert vars(fresh_builtin_datetime)["date"] is datetime.date
    assert vars(fresh_datetime)["datetime"] is datetime.datetime
    assert vars(fresh_builtin_datetime)["datetime"] is datetime.datetime

    monkeypatch.setitem(sys.modules, "datetime", fresh_datetime)
    monkeypatch.setitem(sys.modules, "_datetime", fresh_builtin_datetime)
    monkeypatch.setattr(module, "dt", fresh_datetime)
    monkeypatch.setattr(
        mutation_toolchain,
        "_EAGER_DATETIME_MODULE",
        fresh_datetime,
    )
    monkeypatch.setattr(
        mutation_toolchain,
        "_EAGER_BUILTIN_DATETIME_MODULE",
        fresh_builtin_datetime,
    )

    with pytest.raises(
        MutationToolchainError,
        match="datetime temporal provider binding changed",
    ):
        _verify_selected_binding(
            module_name,
            "dates",
            admitted_module_names=(
                module_name,
                "hypothesis.strategies._internal.utils",
            ),
        )
    with pytest.raises(
        MutationToolchainError,
        match="datetime temporal provider binding changed",
    ):
        _verify_selected_binding(
            module_name,
            "times",
            admitted_module_names=(
                module_name,
                "hypothesis.strategies._internal.utils",
            ),
        )
    with pytest.raises(
        MutationToolchainError,
        match="datetime temporal provider binding changed",
    ):
        _verify_selected_binding(
            module_name,
            "datetimes",
            admitted_module_names=(
                module_name,
                "hypothesis.strategies._internal.utils",
            ),
        )


def test_hypothesis_dates_reject_coordinated_annotation_provider_replacement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "hypothesis.strategies._internal.datetime"
    module = import_module(module_name)
    public = vars(module)["dates"]
    source = vars(public)["__wrapped__"]
    callbacks = {"count": 0}

    def hostile_annotate(_format: object) -> dict[str, object]:
        callbacks["count"] += 1
        return {}

    monkeypatch.setattr(public, "__annotate__", hostile_annotate)
    monkeypatch.setattr(source, "__annotate__", hostile_annotate)
    with pytest.raises(
        MutationToolchainError,
        match="annotation provider changed",
    ):
        _verify_selected_binding(
            module_name,
            "dates",
            admitted_module_names=(
                module_name,
                "hypothesis.strategies._internal.utils",
            ),
        )
    assert callbacks == {"count": 0}


def test_datetime_date_source_default_singletons_reject_impostors_without_callbacks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert mutation_toolchain._runtime_value_shape(datetime.date.min) == [
        "reviewed-source-default-singleton-v1",
        "datetime.date.min",
    ]
    assert mutation_toolchain._runtime_value_shape(datetime.date.max) == [
        "reviewed-source-default-singleton-v1",
        "datetime.date.max",
    ]
    equal_distinct = datetime.date(1, 1, 1)
    with pytest.raises(MutationToolchainError, match="unsupported datetime.date"):
        mutation_toolchain._runtime_value_shape(equal_distinct)

    callbacks = {"count": 0}

    class HostileDate(datetime.date):
        def __getattribute__(self, name: str) -> object:
            callbacks["count"] += 1
            return super().__getattribute__(name)

        def __eq__(self, other: object) -> bool:
            callbacks["count"] += 1
            return True

        def __hash__(self) -> int:
            callbacks["count"] += 1
            return 0

        def __reduce__(self) -> object:
            callbacks["count"] += 1
            return (datetime.date, (1, 1, 1))

        def __repr__(self) -> str:
            callbacks["count"] += 1
            return "datetime.date(1, 1, 1)"

    HostileDate.__module__ = "datetime"
    HostileDate.__qualname__ = "date"
    hostile = HostileDate(1, 1, 1)
    callbacks["count"] = 0
    alias = ModuleType("hostile_datetime_date_alias")
    alias.endpoint = hostile
    monkeypatch.setitem(sys.modules, alias.__name__, alias)
    with pytest.raises(MutationToolchainError, match="datetime.date impostor"):
        mutation_toolchain._runtime_value_shape(hostile)
    assert callbacks == {"count": 0}


def test_hypothesis_emails_lazy_default_is_exact_and_verifies_twice() -> None:
    module_name = "hypothesis.strategies._internal.core"
    module = import_module(module_name)
    public = vars(module)["emails"]
    source = vars(public)["__wrapped__"]
    public_kwdefaults = public.__kwdefaults__
    source_kwdefaults = source.__kwdefaults__
    expected = mutation_toolchain._EAGER_HYPOTHESIS_EMAILS_DOMAINS_DEFAULT

    assert public.__defaults__ == ()
    assert source.__defaults__ is None
    assert public_kwdefaults is not source_kwdefaults
    assert public_kwdefaults is not None
    assert source_kwdefaults is not None
    assert tuple(public_kwdefaults) == ("domains",)
    assert tuple(source_kwdefaults) == ("domains",)
    assert public_kwdefaults["domains"] is expected
    assert source_kwdefaults["domains"] is expected
    assert mutation_toolchain._runtime_value_shape(expected) == [
        "reviewed-source-default-reference-v1",
        "hypothesis.strategies._internal.core.emails.domains",
    ]

    for _ in range(2):
        _verify_selected_binding(
            module_name,
            "emails",
            admitted_module_names=(
                module_name,
                "hypothesis.strategies._internal.utils",
            ),
        )


def test_hypothesis_emails_lazy_default_rejects_fresh_exact_instance_even_when_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lazy_type = mutation_toolchain._EAGER_HYPOTHESIS_LAZY_STRATEGY_TYPE
    fresh = lazy_type(
        mutation_toolchain._EAGER_HYPOTHESIS_DOMAINS_FUNCTION,
        (),
        {},
    )
    assert type(fresh) is lazy_type
    assert fresh is not mutation_toolchain._EAGER_HYPOTHESIS_EMAILS_DOMAINS_DEFAULT
    alias = ModuleType("hostile_hypothesis_emails_lazy_alias")
    alias.endpoint = fresh
    monkeypatch.setitem(sys.modules, alias.__name__, alias)

    with pytest.raises(
        MutationToolchainError,
        match="unsupported Hypothesis LazyStrategy value",
    ):
        mutation_toolchain._runtime_value_shape(fresh)


def test_hypothesis_emails_lazy_default_rejects_impostors_without_callbacks() -> None:
    lazy_type = mutation_toolchain._EAGER_HYPOTHESIS_LAZY_STRATEGY_TYPE
    callbacks = {"count": 0}

    class HostileLazyStrategy(lazy_type):
        def __getattribute__(self, name: str) -> object:
            callbacks["count"] += 1
            return super().__getattribute__(name)

        def __eq__(self, other: object) -> bool:
            callbacks["count"] += 1
            return True

        def __hash__(self) -> int:
            callbacks["count"] += 1
            return 0

        def __repr__(self) -> str:
            callbacks["count"] += 1
            return "LazyStrategy(domains, (), {})"

    hostile_subclass = object.__new__(HostileLazyStrategy)

    class HostileMetadata:
        def __getattribute__(self, name: str) -> object:
            callbacks["count"] += 1
            return super().__getattribute__(name)

        def __eq__(self, other: object) -> bool:
            callbacks["count"] += 1
            return True

        def __hash__(self) -> int:
            callbacks["count"] += 1
            return 0

        def __repr__(self) -> str:
            callbacks["count"] += 1
            return "LazyStrategy(domains, (), {})"

    HostileMetadata.__module__ = "hypothesis.strategies._internal.lazy"
    HostileMetadata.__qualname__ = "LazyStrategy"
    hostile_metadata = HostileMetadata()
    callbacks["count"] = 0

    for hostile in (hostile_subclass, hostile_metadata):
        with pytest.raises(
            MutationToolchainError,
            match="unsupported Hypothesis LazyStrategy impostor",
        ):
            mutation_toolchain._runtime_value_shape(hostile)
        assert callbacks == {"count": 0}


@pytest.mark.parametrize(
    "mutation",
    ("fresh_mapping", "fresh_strategy", "unrelated", "extra"),
)
def test_hypothesis_emails_rejects_coordinated_keyword_default_replacement(
    mutation: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "hypothesis.strategies._internal.core"
    module = import_module(module_name)
    public = vars(module)["emails"]
    source = vars(public)["__wrapped__"]
    expected = mutation_toolchain._EAGER_HYPOTHESIS_EMAILS_DOMAINS_DEFAULT
    if mutation == "fresh_strategy":
        replacement = mutation_toolchain._EAGER_HYPOTHESIS_LAZY_STRATEGY_TYPE(
            mutation_toolchain._EAGER_HYPOTHESIS_DOMAINS_FUNCTION,
            (),
            {},
        )
        changed = {"domains": replacement}
    elif mutation == "unrelated":
        changed = {"domains": object()}
    elif mutation == "extra":
        changed = {"domains": expected, "extra": None}
    else:
        changed = {"domains": expected}
    monkeypatch.setattr(public, "__kwdefaults__", dict(changed))
    monkeypatch.setattr(source, "__kwdefaults__", dict(changed))

    with pytest.raises(
        MutationToolchainError,
        match="(?:exact callable metadata changed|LazyStrategy default graph changed)",
    ):
        _verify_selected_binding(
            module_name,
            "emails",
            admitted_module_names=(
                module_name,
                "hypothesis.strategies._internal.utils",
            ),
        )


@pytest.mark.parametrize(
    "field",
    (
        "validate_called",
        "_LazyStrategy__wrapped_strategy",
        "_LazyStrategy__representation",
        "function",
        "_LazyStrategy__args",
        "_LazyStrategy__kwargs",
        "_transformations",
        "extra",
    ),
)
def test_hypothesis_emails_lazy_default_rejects_mutable_state_drift(
    field: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = mutation_toolchain._EAGER_HYPOTHESIS_EMAILS_DOMAINS_DEFAULT
    namespace = object.__getattribute__(expected, "__dict__")

    def replacement_function() -> None:
        return None

    if field == "validate_called":
        replacement: object = {"hostile": True}
    elif field == "function":
        replacement = replacement_function
    elif field in {"_LazyStrategy__args", "_transformations"}:
        replacement = (object(),)
    elif field == "_LazyStrategy__kwargs":
        replacement = {"hostile": object()}
    else:
        replacement = object()

    with monkeypatch.context() as attack:
        attack.setitem(namespace, field, replacement)
        with pytest.raises(
            MutationToolchainError,
            match="LazyStrategy pristine state changed",
        ):
            mutation_toolchain._runtime_value_shape(expected)

    mutation_toolchain._verify_eager_hypothesis_emails_lazy_default()


@pytest.mark.parametrize(
    "target",
    ("domains", "repr", "wrapped_strategy"),
)
def test_hypothesis_emails_rejects_same_object_provider_code_mutation(
    target: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lazy_namespace = type.__getattribute__(
        mutation_toolchain._EAGER_HYPOTHESIS_LAZY_STRATEGY_TYPE,
        "__dict__",
    )
    if target == "domains":
        provider = mutation_toolchain._EAGER_HYPOTHESIS_DOMAINS_FUNCTION
    elif target == "repr":
        provider = lazy_namespace["__repr__"]
    else:
        descriptor = lazy_namespace["wrapped_strategy"]
        assert type(descriptor) is property
        provider = descriptor.fget
    assert type(provider) is FunctionType

    def hostile_provider(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("mutated LazyStrategy provider executed")

    with monkeypatch.context() as attack:
        attack.setattr(provider, "__code__", hostile_provider.__code__)
        with pytest.raises(
            MutationToolchainError,
            match=(
                "(?:exact callable metadata changed|"
                "LazyStrategy executable (?:shape|provider) changed)"
            ),
        ):
            mutation_toolchain._verify_eager_hypothesis_emails_lazy_default()

    mutation_toolchain._verify_eager_hypothesis_emails_lazy_default()


def test_hypothesis_emails_runtime_rejects_verifier_code_mutation_before_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = mutation_toolchain._verify_eager_hypothesis_emails_lazy_default
    expected = mutation_toolchain._EAGER_HYPOTHESIS_EMAILS_DOMAINS_DEFAULT

    def hostile_provider() -> None:
        raise AssertionError("mutated emails verifier executed")

    with monkeypatch.context() as attack:
        attack.setattr(provider, "__code__", hostile_provider.__code__)
        with pytest.raises(
            MutationToolchainError,
            match="LazyStrategy runtime verifier binding changed",
        ):
            mutation_toolchain._runtime_value_shape(expected)

    mutation_toolchain._verify_eager_hypothesis_emails_lazy_default()


@pytest.mark.parametrize("attack", ("rebound", "same_object_code"))
def test_hypothesis_emails_rejects_source_helper_replacement_before_execution(
    attack: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "hypothesis.strategies._internal.core"
    callbacks = {"count": 0}

    def hostile_verifier(*_args: object, **_kwargs: object) -> None:
        callbacks["count"] += 1

    def hostile_code(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("mutated emails source verifier executed")

    with monkeypatch.context() as patch:
        if attack == "rebound":
            patch.setattr(
                mutation_toolchain,
                "_verify_source_declared_hypothesis_emails_default",
                hostile_verifier,
            )
        else:
            helper = (
                mutation_toolchain
                ._verify_source_declared_hypothesis_emails_default
            )
            patch.setattr(helper, "__code__", hostile_code.__code__)
        with pytest.raises(
            MutationToolchainError,
            match="loaded source verifier binding changed",
        ):
            _verify_selected_binding(
                module_name,
                "emails",
                admitted_module_names=(
                    module_name,
                    "hypothesis.strategies._internal.utils",
                ),
            )
        assert callbacks == {"count": 0}

    _verify_selected_binding(
        module_name,
        "emails",
        admitted_module_names=(
            module_name,
            "hypothesis.strategies._internal.utils",
        ),
    )


@pytest.mark.parametrize("attack", ("builtins_vars", "toolchain_sys"))
def test_hypothesis_emails_rejects_hostile_verifier_dependencies_without_callbacks(
    attack: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    callbacks = {"count": 0}

    def hostile_vars(*_args: object, **_kwargs: object) -> dict[str, object]:
        callbacks["count"] += 1
        return {}

    class HostileSys:
        def __getattribute__(self, name: str) -> object:
            callbacks["count"] += 1
            return super().__getattribute__(name)

    with monkeypatch.context() as patch:
        if attack == "builtins_vars":
            patch.setattr(builtins, "vars", hostile_vars)
        else:
            patch.setattr(mutation_toolchain, "sys", HostileSys())
            callbacks["count"] = 0
        with pytest.raises(
            MutationToolchainError,
            match="LazyStrategy verifier dependency changed",
        ):
            mutation_toolchain._verify_eager_hypothesis_emails_lazy_default()
        assert callbacks == {"count": 0}

    mutation_toolchain._verify_eager_hypothesis_emails_lazy_default()


def test_hypothesis_emails_rejects_public_wrapper_closure_replacement_without_callbacks() -> None:
    public = mutation_toolchain._EAGER_HYPOTHESIS_EMAILS_PUBLIC
    closure = object.__getattribute__(public, "__closure__")
    assert closure is not None
    assert len(closure) == 1
    cell = closure[0]
    descriptor = mutation_toolchain._EXACT_CALLABLE_CELL_CONTENTS_DESCRIPTOR
    original = descriptor.__get__(cell, CellType)
    callbacks = {"count": 0}

    def hostile_delegate(*_args: object, **_kwargs: object) -> object:
        callbacks["count"] += 1
        return object()

    cell.cell_contents = hostile_delegate
    try:
        with pytest.raises(
            MutationToolchainError,
            match="exact callable closure changed: emails.public",
        ):
            mutation_toolchain._verify_eager_hypothesis_emails_lazy_default()
    finally:
        cell.cell_contents = original
    assert callbacks == {"count": 0}
    mutation_toolchain._verify_eager_hypothesis_emails_lazy_default()


@pytest.mark.parametrize(
    "cell_name",
    ("eager", "force_reusable_values", "strategy_definition"),
)
def test_hypothesis_emails_rejects_hidden_delegate_policy_cell_replacement(
    cell_name: str,
) -> None:
    delegate = mutation_toolchain._EAGER_HYPOTHESIS_EMAILS_ACCEPT
    closure = object.__getattribute__(delegate, "__closure__")
    assert closure is not None
    names = object.__getattribute__(delegate, "__code__").co_freevars
    index = names.index(cell_name)
    cell = closure[index]
    descriptor = mutation_toolchain._EXACT_CALLABLE_CELL_CONTENTS_DESCRIPTOR
    original = descriptor.__get__(cell, CellType)

    def hostile_source(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("mutated emails delegate executed")

    replacement: object
    if cell_name == "eager":
        replacement = True
    elif cell_name == "force_reusable_values":
        replacement = False
    else:
        replacement = hostile_source
    cell.cell_contents = replacement
    try:
        with pytest.raises(
            MutationToolchainError,
            match="exact callable closure changed: emails.accept",
        ):
            mutation_toolchain._verify_eager_hypothesis_emails_lazy_default()
    finally:
        cell.cell_contents = original
    mutation_toolchain._verify_eager_hypothesis_emails_lazy_default()


@pytest.mark.parametrize("field", ("transforms", "force_repr"))
def test_hypothesis_emails_rejects_lazy_init_keyword_default_state_drift(
    field: str,
) -> None:
    lazy_namespace = type.__getattribute__(
        mutation_toolchain._EAGER_HYPOTHESIS_LAZY_STRATEGY_TYPE,
        "__dict__",
    )
    initializer = lazy_namespace["__init__"]
    kwdefaults = object.__getattribute__(initializer, "__kwdefaults__")
    assert kwdefaults is not None
    original = dict.__getitem__(kwdefaults, field)
    replacement: object = (object(),) if field == "transforms" else "hostile"
    dict.__setitem__(kwdefaults, field, replacement)
    try:
        with pytest.raises(
            MutationToolchainError,
            match="exact callable keyword defaults changed",
        ):
            mutation_toolchain._verify_eager_hypothesis_emails_lazy_default()
    finally:
        dict.__setitem__(kwdefaults, field, original)
    mutation_toolchain._verify_eager_hypothesis_emails_lazy_default()


@pytest.mark.parametrize("owner", ("lazy_init", "search_annotation"))
def test_hypothesis_emails_rejects_class_closure_cell_replacement(
    owner: str,
) -> None:
    if owner == "lazy_init":
        function = mutation_toolchain._EAGER_HYPOTHESIS_LAZY_INIT
    else:
        function = mutation_toolchain._EAGER_HYPOTHESIS_SEARCH_VALIDATE_ANNOTATE
    closure = object.__getattribute__(function, "__closure__")
    assert closure is not None
    assert len(closure) == 1
    cell = closure[0]
    descriptor = mutation_toolchain._EXACT_CALLABLE_CELL_CONTENTS_DESCRIPTOR
    original = descriptor.__get__(cell, CellType)
    cell.cell_contents = object()
    try:
        with pytest.raises(
            MutationToolchainError,
            match="exact callable closure changed",
        ):
            mutation_toolchain._verify_eager_hypothesis_emails_lazy_default()
    finally:
        cell.cell_contents = original
    mutation_toolchain._verify_eager_hypothesis_emails_lazy_default()


@pytest.mark.parametrize("owner", ("lazy", "search"))
def test_hypothesis_emails_rejects_annotation_classdict_in_place_drift(
    owner: str,
) -> None:
    record = (
        mutation_toolchain._EAGER_HYPOTHESIS_LAZY_ANNOTATION_CLASSDICT
        if owner == "lazy"
        else mutation_toolchain._EAGER_HYPOTHESIS_SEARCH_ANNOTATION_CLASSDICT
    )
    assert record is not None
    classdict = record[1]
    original = dict.__getitem__(classdict, "__module__")
    dict.__setitem__(classdict, "__module__", f"hostile.{owner}")
    try:
        with pytest.raises(
            MutationToolchainError,
            match=(
                f"{owner.capitalize()}Strategy "
                "(?:class shape|annotation classdict) changed"
            ),
        ):
            mutation_toolchain._verify_eager_hypothesis_emails_lazy_default()
    finally:
        dict.__setitem__(classdict, "__module__", original)
    mutation_toolchain._verify_eager_hypothesis_emails_lazy_default()


def test_hypothesis_emails_rejects_search_strategy_label_cache_drift() -> None:
    labels = mutation_toolchain._EAGER_HYPOTHESIS_SEARCH_LABELS
    marker = object()
    dict.__setitem__(labels, marker, marker)
    try:
        with pytest.raises(
            MutationToolchainError,
            match="SearchStrategy label cache changed",
        ):
            mutation_toolchain._verify_eager_hypothesis_emails_lazy_default()
    finally:
        dict.__delitem__(labels, marker)
    mutation_toolchain._verify_eager_hypothesis_emails_lazy_default()


@pytest.mark.parametrize("target", ("lazy_annotation", "search_validate"))
def test_hypothesis_emails_rejects_base_callable_code_drift(
    target: str,
) -> None:
    if target == "lazy_annotation":
        function = object.__getattribute__(
            mutation_toolchain._EAGER_HYPOTHESIS_LAZY_INIT,
            "__annotate__",
        )

        def hostile_factory(anchor: object) -> FunctionType:
            def hostile(_format: object) -> object:
                _ = anchor
                raise AssertionError("mutated annotation provider executed")

            return hostile

        hostile_code = hostile_factory(object()).__code__
    else:
        function = mutation_toolchain._EAGER_HYPOTHESIS_SEARCH_VALIDATE

        def hostile_search(*_args: object, **_kwargs: object) -> object:
            raise AssertionError("mutated SearchStrategy method executed")

        hostile_code = hostile_search.__code__
    original = object.__getattribute__(function, "__code__")
    function.__code__ = hostile_code
    try:
        with pytest.raises(
            MutationToolchainError,
            match="exact callable metadata changed",
        ):
            mutation_toolchain._verify_eager_hypothesis_emails_lazy_default()
    finally:
        function.__code__ = original
    mutation_toolchain._verify_eager_hypothesis_emails_lazy_default()


@pytest.mark.parametrize(
    "binding",
    ("string", "text", "builds", "SearchStrategy", "ascii_letters", "digits"),
)
def test_hypothesis_emails_rejects_true_body_global_drift(
    binding: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    core = mutation_toolchain._EAGER_HYPOTHESIS_CORE_MODULE
    string_module = mutation_toolchain._EAGER_HYPOTHESIS_CORE_STRING_MODULE
    with monkeypatch.context() as attack:
        if binding in {"ascii_letters", "digits"}:
            attack.setattr(string_module, binding, f"hostile-{binding}")
        else:
            attack.setattr(core, binding, object())
        with pytest.raises(
            MutationToolchainError,
            match="LazyStrategy provider binding changed",
        ):
            mutation_toolchain._verify_eager_hypothesis_emails_lazy_default()
    mutation_toolchain._verify_eager_hypothesis_emails_lazy_default()


@pytest.mark.parametrize("attack", ("registry", "package", "both"))
def test_hypothesis_emails_rejects_preseeded_provisional_route(
    attack: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = mutation_toolchain._EAGER_HYPOTHESIS_ROOT_MODULE
    fake = ModuleType("hypothesis.provisional")
    with monkeypatch.context() as patch:
        if attack in {"registry", "both"}:
            patch.setitem(sys.modules, "hypothesis.provisional", fake)
        if attack in {"package", "both"}:
            patch.setattr(root, "provisional", fake, raising=False)
        with pytest.raises(
            MutationToolchainError,
            match="LazyStrategy provider binding changed",
        ):
            mutation_toolchain._verify_eager_hypothesis_emails_lazy_default()
    assert "hypothesis.provisional" not in sys.modules
    assert "provisional" not in vars(root)
    mutation_toolchain._verify_eager_hypothesis_emails_lazy_default()


@pytest.mark.parametrize(
    ("target", "attribute"),
    (
        ("public", "__module__"),
        ("public", "__name__"),
        ("public", "__qualname__"),
        ("source", "__module__"),
        ("source", "__name__"),
        ("source", "__qualname__"),
        ("domains", "__module__"),
        ("domains", "__name__"),
        ("domains", "__qualname__"),
    ),
)
def test_hypothesis_emails_rejects_callable_owner_metadata_drift(
    target: str,
    attribute: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    function = {
        "public": mutation_toolchain._EAGER_HYPOTHESIS_EMAILS_PUBLIC,
        "source": mutation_toolchain._EAGER_HYPOTHESIS_EMAILS_SOURCE,
        "domains": mutation_toolchain._EAGER_HYPOTHESIS_DOMAINS_FUNCTION,
    }[target]
    with monkeypatch.context() as attack:
        attack.setattr(function, attribute, "forged")
        with pytest.raises(
            MutationToolchainError,
            match="exact callable metadata changed",
        ):
            mutation_toolchain._verify_eager_hypothesis_emails_lazy_default()
    mutation_toolchain._verify_eager_hypothesis_emails_lazy_default()


def test_hypothesis_emails_rejects_lazy_class_name_drift() -> None:
    lazy_type = mutation_toolchain._EAGER_HYPOTHESIS_LAZY_STRATEGY_TYPE
    original = type.__getattribute__(lazy_type, "__name__")
    type.__setattr__(lazy_type, "__name__", "Forged")
    try:
        with pytest.raises(
            MutationToolchainError,
            match="LazyStrategy class shape changed",
        ):
            mutation_toolchain._verify_eager_hypothesis_emails_lazy_default()
    finally:
        type.__setattr__(lazy_type, "__name__", original)
    mutation_toolchain._verify_eager_hypothesis_emails_lazy_default()


def test_hypothesis_emails_rejects_hostile_builtin_type_without_callbacks() -> None:
    original_type = builtins.type
    callbacks = {"count": 0}
    caught: BaseException | None = None

    def hostile_type(*args: object, **kwargs: object) -> object:
        callbacks["count"] += 1
        return original_type(*args, **kwargs)

    builtins.type = hostile_type
    try:
        try:
            mutation_toolchain._verify_eager_hypothesis_emails_lazy_default()
        except BaseException as exc:
            caught = exc
    finally:
        builtins.type = original_type
    assert isinstance(caught, MutationToolchainError)
    assert "verifier dependency changed" in str(caught)
    assert callbacks == {"count": 0}
    mutation_toolchain._verify_eager_hypothesis_emails_lazy_default()


def test_hypothesis_emails_rejects_callable_verifier_code_drift_before_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verifier = mutation_toolchain._verify_exact_callable_fingerprint

    def hostile_verifier(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("mutated callable verifier executed")

    with monkeypatch.context() as attack:
        attack.setattr(verifier, "__code__", hostile_verifier.__code__)
        with pytest.raises(
            MutationToolchainError,
            match="LazyStrategy verifier dependency changed",
        ):
            mutation_toolchain._verify_eager_hypothesis_emails_lazy_default()
    mutation_toolchain._verify_eager_hypothesis_emails_lazy_default()


@pytest.mark.parametrize(
    ("owner", "field"),
    (
        ("core", "name"),
        ("core", "package"),
        ("core", "file"),
        ("core", "spec_name"),
        ("core", "origin"),
        ("core", "module_loader"),
        ("core", "spec_loader"),
        ("lazy", "name"),
        ("lazy", "package"),
        ("lazy", "file"),
        ("lazy", "spec_name"),
        ("lazy", "origin"),
        ("lazy", "module_loader"),
        ("lazy", "spec_loader"),
    ),
)
def test_hypothesis_emails_rejects_provider_module_metadata_drift(
    owner: str,
    field: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = (
        mutation_toolchain._EAGER_HYPOTHESIS_CORE_MODULE
        if owner == "core"
        else mutation_toolchain._EAGER_HYPOTHESIS_LAZY_MODULE
    )
    specification = vars(module)["__spec__"]

    with monkeypatch.context() as attack:
        if field == "name":
            attack.setattr(module, "__name__", f"hostile.{owner}")
        elif field == "package":
            attack.setattr(module, "__package__", f"hostile.{owner}")
        elif field == "file":
            attack.setattr(module, "__file__", f"hostile-{owner}.py")
        elif field == "spec_name":
            attack.setattr(specification, "name", f"hostile.{owner}")
        elif field == "origin":
            attack.setattr(specification, "origin", f"hostile-{owner}.py")
        elif field == "module_loader":
            attack.setattr(module, "__loader__", object())
        else:
            attack.setattr(specification, "loader", object())
        with pytest.raises(
            MutationToolchainError,
            match="LazyStrategy provider graph changed",
        ):
            mutation_toolchain._verify_eager_hypothesis_emails_lazy_default()

    mutation_toolchain._verify_eager_hypothesis_emails_lazy_default()


@pytest.mark.parametrize(
    "attack",
    ("default", "domains_annotation", "return_annotation"),
)
def test_hypothesis_emails_rejects_forged_source_semantics(
    attack: str,
) -> None:
    module_name = "hypothesis.strategies._internal.core"
    module, binding, attested, _paths, policy = _selected_binding_evidence(
        module_name,
        "emails",
        admitted_module_names=(
            module_name,
            "hypothesis.strategies._internal.utils",
        ),
    )
    source_binding = mutation_toolchain._source_binding_for_manifest(
        policy,
        binding,
    )
    assert len(source_binding.candidates) == 1
    candidate = source_binding.candidates[0]
    semantics = candidate.function_semantics
    assert semantics is not None
    if attack == "default":
        default = semantics.defaults[0]
        changed_expression = replace(
            default.expression,
            ast_shape=ast.dump(
                ast.parse(
                    "LazyStrategy(domains, (None,), {})",
                    mode="eval",
                ).body,
                include_attributes=False,
            ),
        )
        changed_semantics = replace(
            semantics,
            defaults=(replace(default, expression=changed_expression),),
        )
        expected_error = "sealed source default expression changed"
    else:
        annotations = list(semantics.annotations)
        index = 0 if attack == "domains_annotation" else 1
        name, kind, expression = annotations[index]
        annotations[index] = (
            name,
            kind,
            replace(
                expression,
                ast_shape=ast.dump(
                    ast.parse(
                        "SearchStrategy[bytes]",
                        mode="eval",
                    ).body,
                    include_attributes=False,
                ),
            ),
        )
        changed_semantics = replace(
            semantics,
            annotations=tuple(annotations),
        )
        expected_error = "sealed source annotation semantics changed"
    changed_candidate = replace(
        candidate,
        function_semantics=changed_semantics,
    )
    public = vars(module)["emails"]
    source = vars(public)["__wrapped__"]

    with pytest.raises(MutationToolchainError, match=expected_error):
        mutation_toolchain._verify_source_declared_hypothesis_emails_default(
            module,
            path="emails",
            candidate=changed_candidate,
            public_value=public,
            bound_functions=(public, source),
            matched_function=source,
            policy=policy,
            import_sentinels={},
            attested_code_identities=attested,
        )


def test_hypothesis_emails_rejects_hostile_source_record_without_callbacks() -> None:
    module_name = "hypothesis.strategies._internal.core"
    module, binding, attested, _paths, policy = _selected_binding_evidence(
        module_name,
        "emails",
        admitted_module_names=(
            module_name,
            "hypothesis.strategies._internal.utils",
        ),
    )
    source_binding = mutation_toolchain._source_binding_for_manifest(
        policy,
        binding,
    )
    assert len(source_binding.candidates) == 1
    public = vars(module)["emails"]
    source = vars(public)["__wrapped__"]
    callbacks = {"count": 0}

    class HostileRecord:
        def __getattribute__(self, name: str) -> object:
            callbacks["count"] += 1
            return super().__getattribute__(name)

        def __repr__(self) -> str:
            callbacks["count"] += 1
            return "forged source record"

    hostile = HostileRecord()
    callbacks["count"] = 0
    with pytest.raises(
        MutationToolchainError,
        match="source policy record type changed",
    ):
        mutation_toolchain._verify_source_declared_hypothesis_emails_default(
            module,
            path="emails",
            candidate=hostile,
            public_value=public,
            bound_functions=(public, source),
            matched_function=source,
            policy=policy,
            import_sentinels={},
            attested_code_identities=attested,
        )
    assert callbacks == {"count": 0}


def test_hypothesis_text_lazy_default_is_exact_and_verifies_twice() -> None:
    evidence = _hypothesis_text_lazy_default_evidence()
    public = evidence["public"]
    wrapper = evidence["wrapper"]
    source = evidence["source"]
    default = evidence["default"]
    public_defaults = evidence["public_defaults"]
    wrapper_defaults = evidence["wrapper_defaults"]
    source_defaults = evidence["source_defaults"]
    public_kwdefaults = evidence["public_kwdefaults"]
    wrapper_kwdefaults = evidence["wrapper_kwdefaults"]
    source_kwdefaults = evidence["source_kwdefaults"]
    namespace = evidence["default_namespace"]
    cached_delegate = evidence["cached_delegate"]
    defines_delegate = evidence["defines_delegate"]
    characters_public = evidence["characters_public"]
    characters_wrapper = evidence["characters_wrapper"]
    characters_source = evidence["characters_source"]
    characters_cached_delegate = evidence["characters_cached_delegate"]
    characters_defines_delegate = evidence["characters_defines_delegate"]
    candidate = evidence["candidate"]
    assert type(public) is FunctionType
    assert type(wrapper) is FunctionType
    assert type(source) is FunctionType
    assert type(public_defaults) is tuple
    assert type(wrapper_defaults) is tuple
    assert type(source_defaults) is tuple
    assert type(public_kwdefaults) is dict
    assert type(wrapper_kwdefaults) is dict
    assert type(source_kwdefaults) is dict
    assert type(namespace) is dict
    assert type(cached_delegate) is FunctionType
    assert type(defines_delegate) is FunctionType
    assert type(characters_public) is FunctionType
    assert type(characters_wrapper) is FunctionType
    assert type(characters_source) is FunctionType
    assert type(characters_cached_delegate) is FunctionType
    assert type(characters_defines_delegate) is FunctionType
    assert public is mutation_toolchain._EAGER_HYPOTHESIS_TEXT_PUBLIC
    assert wrapper is mutation_toolchain._EAGER_HYPOTHESIS_TEXT_WRAPPER
    assert source is mutation_toolchain._EAGER_HYPOTHESIS_TEXT_SOURCE
    assert default is mutation_toolchain._EAGER_HYPOTHESIS_TEXT_ALPHABET_DEFAULT
    assert (
        cached_delegate
        is mutation_toolchain._EAGER_HYPOTHESIS_TEXT_CACHED_DELEGATE
    )
    assert (
        defines_delegate
        is mutation_toolchain._EAGER_HYPOTHESIS_TEXT_DEFINES_DELEGATE
    )
    assert (
        characters_source
        is mutation_toolchain._EAGER_HYPOTHESIS_CHARACTERS_SOURCE
    )
    assert (
        characters_public
        is mutation_toolchain._EAGER_HYPOTHESIS_CHARACTERS_PUBLIC
    )
    assert (
        characters_wrapper
        is mutation_toolchain._EAGER_HYPOTHESIS_CHARACTERS_WRAPPER
    )
    assert (
        characters_cached_delegate
        is mutation_toolchain._EAGER_HYPOTHESIS_CHARACTERS_CACHED_DELEGATE
    )
    assert (
        characters_defines_delegate
        is mutation_toolchain._EAGER_HYPOTHESIS_CHARACTERS_DEFINES_DELEGATE
    )
    assert tuple.__getitem__(public_defaults, 0) is default
    assert tuple.__getitem__(wrapper_defaults, 0) is default
    assert tuple.__getitem__(source_defaults, 0) is default
    assert public_defaults is not wrapper_defaults
    assert public_defaults is not source_defaults
    assert wrapper_defaults is not source_defaults
    assert (
        public_kwdefaults
        is mutation_toolchain._EAGER_HYPOTHESIS_TEXT_PUBLIC_KWDEFAULTS
    )
    assert (
        wrapper_kwdefaults
        is mutation_toolchain._EAGER_HYPOTHESIS_TEXT_WRAPPER_KWDEFAULTS
    )
    assert (
        source_kwdefaults
        is mutation_toolchain._EAGER_HYPOTHESIS_TEXT_SOURCE_KWDEFAULTS
    )
    assert public_kwdefaults is not wrapper_kwdefaults
    assert public_kwdefaults is not source_kwdefaults
    assert wrapper_kwdefaults is not source_kwdefaults
    for kwdefaults, expected_items in zip(
        (public_kwdefaults, wrapper_kwdefaults, source_kwdefaults),
        (
            mutation_toolchain._EAGER_HYPOTHESIS_TEXT_PUBLIC_KWDEFAULT_ITEMS,
            mutation_toolchain._EAGER_HYPOTHESIS_TEXT_WRAPPER_KWDEFAULT_ITEMS,
            mutation_toolchain._EAGER_HYPOTHESIS_TEXT_SOURCE_KWDEFAULT_ITEMS,
        ),
        strict=True,
    ):
        kwdefault_items = tuple(dict.items(kwdefaults))
        assert tuple(name for name, _value in kwdefault_items) == (
            "min_size",
            "max_size",
        )
        assert tuple(value for _name, value in kwdefault_items) == (0, None)
        assert len(kwdefault_items) == len(expected_items)
        assert all(
            current_name is expected_name and current_value is expected_value
            for (current_name, current_value), (expected_name, expected_value) in zip(
                kwdefault_items,
                expected_items,
                strict=True,
            )
        )
    assert namespace is mutation_toolchain._EAGER_HYPOTHESIS_TEXT_LAZY_NAMESPACE
    namespace_items = tuple(dict.items(namespace))
    expected_namespace_items = (
        mutation_toolchain._EAGER_HYPOTHESIS_TEXT_LAZY_NAMESPACE_ITEMS
    )
    assert len(namespace_items) == len(expected_namespace_items)
    assert all(
        current_name is expected_name and current_value is expected_value
        for (current_name, current_value), (expected_name, expected_value) in zip(
            namespace_items,
            expected_namespace_items,
            strict=True,
        )
    )
    assert tuple(dict.keys(namespace)) == (
        "validate_called",
        "_LazyStrategy__wrapped_strategy",
        "_LazyStrategy__representation",
        "function",
        "_LazyStrategy__args",
        "_LazyStrategy__kwargs",
        "_transformations",
        "force_has_reusable_values",
        "cached_is_cacheable",
    )
    assert dict.__getitem__(namespace, "_LazyStrategy__wrapped_strategy") is None
    assert dict.__getitem__(namespace, "_LazyStrategy__representation") is None
    assert dict.__getitem__(namespace, "function") is characters_source
    assert dict.__getitem__(namespace, "force_has_reusable_values") is True
    assert dict.__getitem__(namespace, "cached_is_cacheable") is True
    validate_state = dict.__getitem__(namespace, "validate_called")
    assert validate_state is mutation_toolchain._EAGER_HYPOTHESIS_TEXT_VALIDATE_STATE
    assert type(validate_state) is dict
    assert len(validate_state) == 0
    lazy_args = dict.__getitem__(namespace, "_LazyStrategy__args")
    transformations = dict.__getitem__(namespace, "_transformations")
    assert lazy_args is mutation_toolchain._EAGER_HYPOTHESIS_TEXT_LAZY_ARGS
    assert (
        transformations
        is mutation_toolchain._EAGER_HYPOTHESIS_TEXT_LAZY_TRANSFORMATIONS
    )
    assert type(lazy_args) is tuple and len(lazy_args) == 0
    assert transformations is lazy_args
    kwargs = dict.__getitem__(namespace, "_LazyStrategy__kwargs")
    assert type(kwargs) is dict
    assert kwargs is mutation_toolchain._EAGER_HYPOTHESIS_TEXT_LAZY_KWARGS
    assert tuple(dict.keys(kwargs)) == (
        "codec",
        "min_codepoint",
        "max_codepoint",
        "categories",
        "exclude_categories",
        "exclude_characters",
        "include_characters",
        "blacklist_categories",
        "whitelist_categories",
        "blacklist_characters",
        "whitelist_characters",
    )
    expected_kwarg_items = mutation_toolchain._EAGER_HYPOTHESIS_TEXT_LAZY_KWARG_ITEMS
    current_kwarg_items = tuple(dict.items(kwargs))
    assert len(current_kwarg_items) == len(expected_kwarg_items)
    assert all(
        current_name is expected_name and current_value is expected_value
        for (current_name, current_value), (expected_name, expected_value) in zip(
            current_kwarg_items,
            expected_kwarg_items,
            strict=True,
        )
    )
    codec = dict.__getitem__(kwargs, "codec")
    assert codec is mutation_toolchain._EAGER_HYPOTHESIS_TEXT_CODEC
    assert type(codec) is str and str.__eq__(codec, "utf-8")
    assert all(value is None for _name, value in tuple(dict.items(kwargs))[1:])
    semantics = candidate.function_semantics
    assert semantics is not None
    assert len(semantics.defaults) == 3
    assert len(semantics.annotations) == 4
    alphabet_default = semantics.defaults[0]
    assert alphabet_default.parameter == "alphabet"
    assert alphabet_default.parameter_kind == "positional_or_keyword"
    assert alphabet_default.expression.kind == "unsupported"
    assert alphabet_default.expression.payload is None
    expected_ast_shape = ast.dump(
        ast.parse("characters(codec='utf-8')", mode="eval").body,
        include_attributes=False,
    )
    assert alphabet_default.expression.ast_shape == expected_ast_shape
    assert (
        expected_ast_shape
        == mutation_toolchain._EAGER_HYPOTHESIS_TEXT_DEFAULT_AST_SHAPE
    )
    assert tuple(
        (default_semantics.parameter, default_semantics.parameter_kind)
        for default_semantics in semantics.defaults
    ) == (
        ("alphabet", "positional_or_keyword"),
        ("min_size", "keyword_only"),
        ("max_size", "keyword_only"),
    )
    assert tuple(
        default_semantics.expression.ast_shape
        for default_semantics in semantics.defaults
    ) == (
        expected_ast_shape,
        ast.dump(ast.parse("0", mode="eval").body, include_attributes=False),
        ast.dump(ast.parse("None", mode="eval").body, include_attributes=False),
    )
    assert tuple(
        default_semantics.expression.kind
        for default_semantics in semantics.defaults
    ) == ("unsupported", "literal", "literal")
    assert semantics.defaults[0].expression.payload is None
    assert semantics.defaults[1].expression.payload == ["int", "0"]
    assert semantics.defaults[2].expression.payload == ["NoneType"]
    assert tuple(
        (name, kind, expression.kind)
        for name, kind, expression in semantics.annotations
    ) == (
        ("alphabet", "positional_or_keyword", "unsupported"),
        ("min_size", "keyword_only", "reference"),
        ("max_size", "keyword_only", "unsupported"),
        ("return", "return", "unsupported"),
    )
    assert tuple(
        expression.ast_shape for _name, _kind, expression in semantics.annotations
    ) == mutation_toolchain._EAGER_HYPOTHESIS_TEXT_ANNOTATION_AST_SHAPES
    runtime_code_ids = _hypothesis_text_runtime_code_ids(evidence)
    callbacks = {"runtime_profile": 0}

    def profiler(frame: object, event: str, _arg: object) -> None:
        if event == "call" and id(frame.f_code) in runtime_code_ids:
            callbacks["runtime_profile"] += 1

    previous_profile = sys.getprofile()
    runtime_shape: object = None
    try:
        sys.setprofile(profiler)
        runtime_shape = mutation_toolchain._runtime_value_shape(default)
        for _attempt in range(2):
            mutation_toolchain._verify_eager_hypothesis_text_lazy_default()
            _verify_hypothesis_text_default_binding()
    finally:
        sys.setprofile(previous_profile)
    assert runtime_shape == [
        "reviewed-source-default-reference-v1",
        "hypothesis.strategies._internal.core.text.alphabet",
    ]
    assert callbacks == {"runtime_profile": 0}
    assert sys.getprofile() is previous_profile


@pytest.mark.parametrize(
    "attack",
    (
        "alphabet_default",
        "min_size_default",
        "max_size_default",
        "alphabet_annotation",
        "return_annotation",
    ),
)
def test_hypothesis_text_rejects_forged_source_semantics_without_runtime_execution(
    attack: str,
) -> None:
    evidence = _hypothesis_text_lazy_default_evidence()
    module = evidence["module"]
    policy = evidence["policy"]
    attested = evidence["attested"]
    candidate = evidence["candidate"]
    source_binding = evidence["source_binding"]
    public = evidence["public"]
    wrapper = evidence["wrapper"]
    source = evidence["source"]
    assert type(module) is ModuleType
    assert type(public) is FunctionType
    assert type(wrapper) is FunctionType
    assert type(source) is FunctionType
    semantics = candidate.function_semantics
    assert semantics is not None
    if attack.endswith("_default"):
        default_index = {
            "alphabet_default": 0,
            "min_size_default": 1,
            "max_size_default": 2,
        }[attack]
        changed_source = {
            "alphabet_default": "characters(codec='ascii')",
            "min_size_default": "1",
            "max_size_default": "0",
        }[attack]
        defaults = list(semantics.defaults)
        default = defaults[default_index]
        defaults[default_index] = replace(
            default,
            expression=replace(
                default.expression,
                ast_shape=ast.dump(
                    ast.parse(changed_source, mode="eval").body,
                    include_attributes=False,
                ),
            ),
        )
        changed_semantics = replace(semantics, defaults=tuple(defaults))
        expected_error = "sealed source text default expression changed"
    else:
        annotations = list(semantics.annotations)
        annotation_index = 0 if attack == "alphabet_annotation" else 3
        name, kind, expression = annotations[annotation_index]
        annotations[annotation_index] = (
            name,
            kind,
            replace(
                expression,
                ast_shape=ast.dump(
                    ast.parse("SearchStrategy[bytes]", mode="eval").body,
                    include_attributes=False,
                ),
            ),
        )
        changed_semantics = replace(
            semantics,
            annotations=tuple(annotations),
        )
        expected_error = "sealed source text annotation semantics changed"
    changed_candidate = replace(
        candidate,
        function_semantics=changed_semantics,
    )
    changed_binding = replace(
        source_binding,
        candidates=(changed_candidate,),
    )
    changed_policy = replace(
        policy,
        bindings=tuple(
            changed_binding if current is source_binding else current
            for current in policy.bindings
        ),
    )
    provider = mutation_toolchain._verify_eager_hypothesis_text_lazy_default
    provider_code = object.__getattribute__(provider, "__code__")
    runtime_code_ids = _hypothesis_text_runtime_code_ids(evidence)
    callbacks = {"provider_profile": 0, "runtime_profile": 0}

    def profiler(frame: object, event: str, _arg: object) -> None:
        if event != "call":
            return
        if frame.f_code is provider_code:
            callbacks["provider_profile"] += 1
        if id(frame.f_code) in runtime_code_ids:
            callbacks["runtime_profile"] += 1

    previous_profile = sys.getprofile()
    caught: BaseException | None = None
    try:
        sys.setprofile(profiler)
        try:
            mutation_toolchain._verify_source_declared_hypothesis_text_default(
                module,
                path="text",
                candidate=changed_candidate,
                public_value=public,
                bound_functions=(public, wrapper, source),
                matched_function=source,
                policy=changed_policy,
                attested_code_identities=attested,
            )
        except BaseException as exc:
            caught = exc
    finally:
        sys.setprofile(previous_profile)

    assert isinstance(caught, MutationToolchainError)
    assert expected_error in str(caught)
    assert callbacks == {"provider_profile": 1, "runtime_profile": 0}
    assert sys.getprofile() is previous_profile
    _verify_hypothesis_text_default_binding()


def test_hypothesis_text_rejects_hostile_source_record_without_callbacks() -> None:
    evidence = _hypothesis_text_lazy_default_evidence()
    module = evidence["module"]
    policy = evidence["policy"]
    attested = evidence["attested"]
    source_binding = evidence["source_binding"]
    public = evidence["public"]
    wrapper = evidence["wrapper"]
    source = evidence["source"]
    assert type(module) is ModuleType
    assert type(public) is FunctionType
    assert type(wrapper) is FunctionType
    assert type(source) is FunctionType
    callbacks = {
        "getattribute": 0,
        "repr": 0,
        "provider_profile": 0,
        "runtime_profile": 0,
    }

    class HostileRecord:
        def __getattribute__(self, name: str) -> object:
            callbacks["getattribute"] += 1
            return super().__getattribute__(name)

        def __repr__(self) -> str:
            callbacks["repr"] += 1
            return "forged text source record"

    hostile = HostileRecord()
    callbacks.update(getattribute=0, repr=0)
    changed_binding = replace(source_binding, candidates=(hostile,))
    changed_policy = replace(
        policy,
        bindings=tuple(
            changed_binding if current is source_binding else current
            for current in policy.bindings
        ),
    )
    provider_code = object.__getattribute__(
        mutation_toolchain._verify_eager_hypothesis_text_lazy_default,
        "__code__",
    )
    runtime_code_ids = _hypothesis_text_runtime_code_ids(evidence)

    def profiler(frame: object, event: str, _arg: object) -> None:
        if event != "call":
            return
        if frame.f_code is provider_code:
            callbacks["provider_profile"] += 1
        if id(frame.f_code) in runtime_code_ids:
            callbacks["runtime_profile"] += 1

    previous_profile = sys.getprofile()
    caught: BaseException | None = None
    try:
        sys.setprofile(profiler)
        try:
            mutation_toolchain._verify_source_declared_hypothesis_text_default(
                module,
                path="text",
                candidate=hostile,
                public_value=public,
                bound_functions=(public, wrapper, source),
                matched_function=source,
                policy=changed_policy,
                attested_code_identities=attested,
            )
        except BaseException as exc:
            caught = exc
    finally:
        sys.setprofile(previous_profile)

    assert isinstance(caught, MutationToolchainError)
    assert "source policy record type changed" in str(caught)
    assert callbacks == {
        "getattribute": 0,
        "repr": 0,
        "provider_profile": 1,
        "runtime_profile": 0,
    }
    assert sys.getprofile() is previous_profile
    _verify_hypothesis_text_default_binding()


def test_hypothesis_text_rejects_source_verifier_code_clone_before_execution() -> None:
    evidence = _hypothesis_text_lazy_default_evidence()
    verifier = mutation_toolchain._verify_source_declared_hypothesis_text_default
    assert type(verifier) is FunctionType
    original_code = object.__getattribute__(verifier, "__code__")
    changed_code = original_code.replace()
    assert changed_code is not original_code
    callbacks = {"verifier_profile": 0, "runtime_profile": 0}
    runtime_code_ids = _hypothesis_text_runtime_code_ids(evidence)

    def profiler(frame: object, event: str, _arg: object) -> None:
        if event != "call":
            return
        if frame.f_code is changed_code:
            callbacks["verifier_profile"] += 1
        if id(frame.f_code) in runtime_code_ids:
            callbacks["runtime_profile"] += 1

    previous_profile = sys.getprofile()
    caught: BaseException | None = None
    try:
        verifier.__code__ = changed_code
        sys.setprofile(profiler)
        try:
            _verify_hypothesis_text_default_binding()
        except BaseException as exc:
            caught = exc
    finally:
        sys.setprofile(previous_profile)
        verifier.__code__ = original_code

    assert isinstance(caught, MutationToolchainError)
    assert "loaded source verifier binding changed" in str(caught)
    assert callbacks == {"verifier_profile": 0, "runtime_profile": 0}
    assert object.__getattribute__(verifier, "__code__") is original_code
    assert sys.getprofile() is previous_profile
    _verify_hypothesis_text_default_binding()


@pytest.mark.parametrize(
    "attack",
    (
        "public_clone",
        "wrapper_clone",
        "source_clone",
        "shared_clone",
        "all_clones",
        "rotate",
    ),
)
def test_hypothesis_text_rejects_exact_positional_default_tuple_identity_drift(
    attack: str,
) -> None:
    evidence = _hypothesis_text_lazy_default_evidence()
    public = evidence["public"]
    wrapper = evidence["wrapper"]
    source = evidence["source"]
    default = evidence["default"]
    assert type(public) is FunctionType
    assert type(wrapper) is FunctionType
    assert type(source) is FunctionType
    functions = (public, wrapper, source)
    original_defaults = tuple(
        object.__getattribute__(function, "__defaults__")
        for function in functions
    )
    assert all(type(item) is tuple and len(item) == 1 for item in original_defaults)
    changed_defaults = tuple(tuple([default]) for _function in functions)
    assert all(
        changed is not original
        for changed, original in zip(
            changed_defaults,
            original_defaults,
            strict=True,
        )
    )
    callbacks = {"verifier_profile": 0, "runtime_profile": 0}
    verifier_code = object.__getattribute__(
        mutation_toolchain._verify_eager_hypothesis_text_lazy_default,
        "__code__",
    )
    runtime_code_ids = _hypothesis_text_runtime_code_ids(evidence)

    def profiler(frame: object, event: str, _arg: object) -> None:
        if event != "call":
            return
        if frame.f_code is verifier_code:
            callbacks["verifier_profile"] += 1
        if id(frame.f_code) in runtime_code_ids:
            callbacks["runtime_profile"] += 1

    previous_profile = sys.getprofile()
    caught: BaseException | None = None
    try:
        if attack == "public_clone":
            public.__defaults__ = changed_defaults[0]
        elif attack == "wrapper_clone":
            wrapper.__defaults__ = changed_defaults[1]
        elif attack == "source_clone":
            source.__defaults__ = changed_defaults[2]
        elif attack in {"shared_clone", "all_clones"}:
            replacements = (
                (changed_defaults[0],) * len(functions)
                if attack == "shared_clone"
                else changed_defaults
            )
            for function, changed in zip(
                functions,
                replacements,
                strict=True,
            ):
                function.__defaults__ = changed
        else:
            for function, changed in zip(
                functions,
                original_defaults[1:] + original_defaults[:1],
                strict=True,
            ):
                function.__defaults__ = changed
        sys.setprofile(profiler)
        try:
            _verify_hypothesis_text_default_binding()
        except BaseException as exc:
            caught = exc
    finally:
        sys.setprofile(previous_profile)
        for function, original in zip(
            functions,
            original_defaults,
            strict=True,
        ):
            function.__defaults__ = original

    assert isinstance(caught, MutationToolchainError)
    assert "text" in str(caught).lower()
    assert callbacks == {"verifier_profile": 1, "runtime_profile": 0}
    assert sys.getprofile() is previous_profile
    assert all(
        object.__getattribute__(function, "__defaults__") is original
        for function, original in zip(
            functions,
            original_defaults,
            strict=True,
        )
    )
    _verify_hypothesis_text_default_binding()


@pytest.mark.parametrize("level", ("public", "wrapper", "source", "all"))
@pytest.mark.parametrize(
    "attack",
    (
        "container_clone",
        "shared_container_clone",
        "min_size_value",
        "max_size_value",
        "exact_rekey",
        "reorder",
        "subclass_key",
    ),
)
def test_hypothesis_text_rejects_keyword_default_drift_without_callbacks(
    level: str,
    attack: str,
) -> None:
    evidence = _hypothesis_text_lazy_default_evidence()
    functions = tuple(
        evidence[name] for name in ("public", "wrapper", "source")
    )
    assert all(type(function) is FunctionType for function in functions)
    original_mappings = tuple(
        object.__getattribute__(function, "__kwdefaults__")
        for function in functions
    )
    assert all(type(mapping) is dict for mapping in original_mappings)
    original_items = tuple(
        tuple(dict.items(mapping)) for mapping in original_mappings
    )
    target_indices = (0, 1, 2) if level == "all" else (
        ("public", "wrapper", "source").index(level),
    )
    callbacks = {
        "eq": 0,
        "hash": 0,
        "repr": 0,
        "verifier_profile": 0,
        "runtime_profile": 0,
    }

    class HostileKey(str):
        def __eq__(self, other: object) -> bool:
            callbacks["eq"] += 1
            return str.__eq__(self, other)

        def __hash__(self) -> int:
            callbacks["hash"] += 1
            return str.__hash__(self)

        def __repr__(self) -> str:
            callbacks["repr"] += 1
            return "hostile-text-kwdefault-key"

    verifier_code = object.__getattribute__(
        mutation_toolchain._verify_eager_hypothesis_text_lazy_default,
        "__code__",
    )
    runtime_code_ids = _hypothesis_text_runtime_code_ids(evidence)

    def profiler(frame: object, event: str, _arg: object) -> None:
        if event != "call":
            return
        if frame.f_code is verifier_code:
            callbacks["verifier_profile"] += 1
        if id(frame.f_code) in runtime_code_ids:
            callbacks["runtime_profile"] += 1

    previous_profile = sys.getprofile()
    replacements: list[dict[object, object]] = []
    shared_replacement: dict[object, object] | None = None
    caught: BaseException | None = None
    try:
        for index in target_indices:
            function = tuple.__getitem__(functions, index)
            mapping = tuple.__getitem__(original_mappings, index)
            items = tuple.__getitem__(original_items, index)
            assert type(function) is FunctionType
            assert type(mapping) is dict
            if attack in {"container_clone", "shared_container_clone"}:
                if attack == "shared_container_clone":
                    if shared_replacement is None:
                        shared_replacement = dict(items)
                    replacement = shared_replacement
                else:
                    replacement = dict(items)
                assert replacement is not mapping
                function.__kwdefaults__ = replacement
                if not any(replacement is current for current in replacements):
                    replacements.append(replacement)
            elif attack == "min_size_value":
                dict.__setitem__(mapping, "min_size", 1)
            elif attack == "max_size_value":
                dict.__setitem__(mapping, "max_size", 1)
            elif attack in {"exact_rekey", "subclass_key"}:
                original_key = tuple.__getitem__(tuple.__getitem__(items, 0), 0)
                assert type(original_key) is str
                assert str.__eq__(original_key, "min_size")
                replacement_key: str
                if attack == "exact_rekey":
                    replacement_key = b"min_size".decode("ascii")
                    assert type(replacement_key) is str
                    assert str.__eq__(replacement_key, "min_size")
                    assert replacement_key is not original_key
                else:
                    replacement_key = HostileKey("min_size")
                dict.clear(mapping)
                for name, value in items:
                    dict.__setitem__(
                        mapping,
                        replacement_key
                        if type(name) is str and str.__eq__(name, "min_size")
                        else name,
                        value,
                    )
            else:
                dict.clear(mapping)
                for name, value in reversed(items):
                    dict.__setitem__(mapping, name, value)
        callbacks.update(
            eq=0,
            hash=0,
            repr=0,
            verifier_profile=0,
            runtime_profile=0,
        )
        sys.setprofile(profiler)
        try:
            _verify_hypothesis_text_default_binding()
        except BaseException as exc:
            caught = exc
    finally:
        sys.setprofile(previous_profile)
        for mapping, items in zip(
            original_mappings,
            original_items,
            strict=True,
        ):
            assert type(mapping) is dict
            dict.clear(mapping)
            for name, value in items:
                dict.__setitem__(mapping, name, value)
        for function, mapping in zip(
            functions,
            original_mappings,
            strict=True,
        ):
            assert type(function) is FunctionType
            function.__kwdefaults__ = mapping
        for replacement in replacements:
            dict.clear(replacement)

    assert isinstance(caught, MutationToolchainError)
    assert "text" in str(caught).lower()
    assert callbacks == {
        "eq": 0,
        "hash": 0,
        "repr": 0,
        "verifier_profile": 1,
        "runtime_profile": 0,
    }
    assert sys.getprofile() is previous_profile
    assert all(
        object.__getattribute__(function, "__kwdefaults__") is mapping
        for function, mapping in zip(
            functions,
            original_mappings,
            strict=True,
        )
    )
    for mapping, items in zip(original_mappings, original_items, strict=True):
        restored = tuple(dict.items(mapping))
        assert len(restored) == len(items)
        assert all(
            current_name is expected_name and current_value is expected_value
            for (current_name, current_value), (expected_name, expected_value) in zip(
                restored,
                items,
                strict=True,
            )
        )
    _verify_hypothesis_text_default_binding()


@pytest.mark.parametrize(
    "target_name",
    ("cached_delegate", "defines_delegate", "characters_source"),
)
def test_hypothesis_text_rejects_provider_code_clone_before_execution(
    target_name: str,
) -> None:
    evidence = _hypothesis_text_lazy_default_evidence()
    target = evidence[target_name]
    assert type(target) is FunctionType
    provider = mutation_toolchain._verify_eager_hypothesis_text_lazy_default
    provider_code = object.__getattribute__(provider, "__code__")
    original_code = object.__getattribute__(target, "__code__")
    changed_code = original_code.replace()
    assert changed_code is not original_code
    runtime_code_ids = _hypothesis_text_runtime_code_ids(evidence, changed_code)
    callbacks = {"verifier_profile": 0, "runtime_profile": 0}

    def profiler(frame: object, event: str, _arg: object) -> None:
        if event != "call":
            return
        if frame.f_code is provider_code:
            callbacks["verifier_profile"] += 1
        if id(frame.f_code) in runtime_code_ids:
            callbacks["runtime_profile"] += 1

    previous_profile = sys.getprofile()
    caught: BaseException | None = None
    try:
        target.__code__ = changed_code
        sys.setprofile(profiler)
        try:
            _verify_hypothesis_text_default_binding()
        except BaseException as exc:
            caught = exc
    finally:
        sys.setprofile(previous_profile)
        target.__code__ = original_code

    assert isinstance(caught, MutationToolchainError)
    assert "text" in str(caught).lower()
    assert callbacks == {"verifier_profile": 1, "runtime_profile": 0}
    assert sys.getprofile() is previous_profile
    assert object.__getattribute__(target, "__code__") is original_code
    _verify_hypothesis_text_default_binding()


@pytest.mark.parametrize("boundary", ("loaded_binding", "runtime_shape"))
def test_hypothesis_text_rejects_lazy_verifier_code_clone_before_execution(
    boundary: str,
) -> None:
    evidence = _hypothesis_text_lazy_default_evidence()
    default = evidence["default"]
    provider = mutation_toolchain._verify_eager_hypothesis_text_lazy_default
    original_code = object.__getattribute__(provider, "__code__")
    changed_code = original_code.replace()
    assert changed_code is not original_code
    callbacks = {"provider_profile": 0, "runtime_profile": 0}
    runtime_code_ids = _hypothesis_text_runtime_code_ids(evidence)

    def profiler(frame: object, event: str, _arg: object) -> None:
        if event != "call":
            return
        if frame.f_code is changed_code:
            callbacks["provider_profile"] += 1
        if id(frame.f_code) in runtime_code_ids:
            callbacks["runtime_profile"] += 1

    previous_profile = sys.getprofile()
    caught: BaseException | None = None
    try:
        provider.__code__ = changed_code
        sys.setprofile(profiler)
        try:
            if boundary == "runtime_shape":
                mutation_toolchain._runtime_value_shape(default)
            else:
                _verify_hypothesis_text_default_binding()
        except BaseException as exc:
            caught = exc
    finally:
        sys.setprofile(previous_profile)
        provider.__code__ = original_code

    assert isinstance(caught, MutationToolchainError)
    assert "text" in str(caught).lower()
    assert callbacks == {"provider_profile": 0, "runtime_profile": 0}
    assert object.__getattribute__(provider, "__code__") is original_code
    assert sys.getprofile() is previous_profile
    assert mutation_toolchain._runtime_value_shape(default) == [
        "reviewed-source-default-reference-v1",
        "hypothesis.strategies._internal.core.text.alphabet",
    ]
    _verify_hypothesis_text_default_binding()


@pytest.mark.parametrize("boundary", ("loaded_binding", "runtime_shape"))
@pytest.mark.parametrize(
    "attack",
    ("container_clone", "value_replacement", "exact_rekey", "reorder"),
)
def test_hypothesis_text_rejects_lazy_verifier_kwdefault_drift_before_execution(
    boundary: str,
    attack: str,
) -> None:
    evidence = _hypothesis_text_lazy_default_evidence()
    default = evidence["default"]
    provider = mutation_toolchain._verify_eager_hypothesis_text_lazy_default
    provider_code = object.__getattribute__(provider, "__code__")
    original = object.__getattribute__(provider, "__kwdefaults__")
    assert type(original) is dict
    original_items = tuple(dict.items(original))
    assert len(original_items) > 0
    callbacks = {"provider_profile": 0, "runtime_profile": 0}
    runtime_code_ids = _hypothesis_text_runtime_code_ids(evidence)

    def profiler(frame: object, event: str, _arg: object) -> None:
        if event != "call":
            return
        if frame.f_code is provider_code:
            callbacks["provider_profile"] += 1
        if id(frame.f_code) in runtime_code_ids:
            callbacks["runtime_profile"] += 1

    previous_profile = sys.getprofile()
    replacement: dict[object, object] | None = None
    caught: BaseException | None = None
    try:
        first_key = tuple.__getitem__(tuple.__getitem__(original_items, 0), 0)
        assert type(first_key) is str
        if attack == "container_clone":
            replacement = dict(original_items)
            assert replacement is not original
            provider.__kwdefaults__ = replacement
        elif attack == "value_replacement":
            dict.__setitem__(original, first_key, object())
        elif attack == "exact_rekey":
            replacement_key = bytearray(first_key, "utf-8").decode("utf-8")
            assert type(replacement_key) is str
            assert str.__eq__(replacement_key, first_key)
            assert replacement_key is not first_key
            dict.clear(original)
            for name, value in original_items:
                dict.__setitem__(
                    original,
                    replacement_key if name is first_key else name,
                    value,
                )
        else:
            dict.clear(original)
            for name, value in reversed(original_items):
                dict.__setitem__(original, name, value)
        sys.setprofile(profiler)
        try:
            if boundary == "runtime_shape":
                mutation_toolchain._runtime_value_shape(default)
            else:
                _verify_hypothesis_text_default_binding()
        except BaseException as exc:
            caught = exc
    finally:
        sys.setprofile(previous_profile)
        dict.clear(original)
        for name, value in original_items:
            dict.__setitem__(original, name, value)
        provider.__kwdefaults__ = original
        if replacement is not None:
            dict.clear(replacement)

    assert isinstance(caught, MutationToolchainError)
    assert "text" in str(caught).lower()
    assert callbacks == {"provider_profile": 0, "runtime_profile": 0}
    assert object.__getattribute__(provider, "__kwdefaults__") is original
    restored_items = tuple(dict.items(original))
    assert len(restored_items) == len(original_items)
    assert all(
        current_name is expected_name and current_value is expected_value
        for (current_name, current_value), (expected_name, expected_value) in zip(
            restored_items,
            original_items,
            strict=True,
        )
    )
    assert sys.getprofile() is previous_profile
    assert mutation_toolchain._runtime_value_shape(default) == [
        "reviewed-source-default-reference-v1",
        "hypothesis.strategies._internal.core.text.alphabet",
    ]
    _verify_hypothesis_text_default_binding()


@pytest.mark.parametrize(
    "attack",
    (
        "public_default_clone",
        "codec_equal_clone",
        "namespace_exact_rekey",
        "function_clone",
    ),
)
def test_hypothesis_text_runtime_shape_rejects_default_graph_drift_without_execution(
    attack: str,
) -> None:
    evidence = _hypothesis_text_lazy_default_evidence()
    public = evidence["public"]
    default = evidence["default"]
    namespace = evidence["default_namespace"]
    characters_source = evidence["characters_source"]
    assert type(public) is FunctionType
    assert type(namespace) is dict
    assert type(characters_source) is FunctionType
    original_defaults = object.__getattribute__(public, "__defaults__")
    assert type(original_defaults) is tuple
    namespace_items = tuple(dict.items(namespace))
    kwargs = dict.__getitem__(namespace, "_LazyStrategy__kwargs")
    assert type(kwargs) is dict
    kwargs_items = tuple(dict.items(kwargs))
    provider_code = object.__getattribute__(
        mutation_toolchain._verify_eager_hypothesis_text_lazy_default,
        "__code__",
    )
    runtime_code_ids = _hypothesis_text_runtime_code_ids(evidence)
    callbacks = {"provider_profile": 0, "runtime_profile": 0}

    def profiler(frame: object, event: str, _arg: object) -> None:
        if event != "call":
            return
        if frame.f_code is provider_code:
            callbacks["provider_profile"] += 1
        if id(frame.f_code) in runtime_code_ids:
            callbacks["runtime_profile"] += 1

    previous_profile = sys.getprofile()
    caught: BaseException | None = None
    active_namespace = namespace
    try:
        if attack == "public_default_clone":
            changed_defaults = tuple([default])
            assert changed_defaults is not original_defaults
            public.__defaults__ = changed_defaults
        elif attack == "codec_equal_clone":
            codec_key, original_codec = tuple.__getitem__(kwargs_items, 0)
            codec_clone = bytearray(b"utf-8").decode("ascii")
            assert type(original_codec) is str
            assert str.__eq__(codec_clone, original_codec)
            assert codec_clone is not original_codec
            dict.__setitem__(kwargs, codec_key, codec_clone)
        elif attack == "namespace_exact_rekey":
            original_key = tuple.__getitem__(tuple.__getitem__(namespace_items, 0), 0)
            replacement_key = bytearray(original_key, "utf-8").decode("utf-8")
            assert type(original_key) is str
            assert type(replacement_key) is str
            assert str.__eq__(replacement_key, original_key)
            assert replacement_key is not original_key
            active_namespace = {}
            for name, value in namespace_items:
                dict.__setitem__(
                    active_namespace,
                    replacement_key if name is original_key else name,
                    value,
                )
            assert tuple.__getitem__(tuple(dict.items(active_namespace)), 0)[0] is (
                replacement_key
            )
            object.__setattr__(default, "__dict__", active_namespace)
        else:
            function_clone = _exact_function_clone(characters_source)
            assert function_clone is not characters_source
            dict.__setitem__(namespace, "function", function_clone)
        sys.setprofile(profiler)
        try:
            mutation_toolchain._runtime_value_shape(default)
        except BaseException as exc:
            caught = exc
    finally:
        sys.setprofile(previous_profile)
        public.__defaults__ = original_defaults
        object.__setattr__(default, "__dict__", namespace)
        dict.clear(namespace)
        for name, value in namespace_items:
            dict.__setitem__(namespace, name, value)
        dict.clear(kwargs)
        for name, value in kwargs_items:
            dict.__setitem__(kwargs, name, value)
        if active_namespace is not namespace:
            dict.clear(active_namespace)

    assert isinstance(caught, MutationToolchainError)
    assert "text" in str(caught).lower()
    assert callbacks == {"provider_profile": 1, "runtime_profile": 0}
    assert sys.getprofile() is previous_profile
    assert object.__getattribute__(public, "__defaults__") is original_defaults
    assert mutation_toolchain._runtime_value_shape(default) == [
        "reviewed-source-default-reference-v1",
        "hypothesis.strategies._internal.core.text.alphabet",
    ]
    _verify_hypothesis_text_default_binding()


@pytest.mark.parametrize(
    "owner_name",
    (
        "public",
        "wrapper",
        "characters_public",
        "characters_wrapper",
    ),
)
def test_hypothesis_text_rejects_wrapper_closure_replacement_without_execution(
    owner_name: str,
) -> None:
    evidence = _hypothesis_text_lazy_default_evidence()
    owner = evidence[owner_name]
    assert type(owner) is FunctionType
    closure = object.__getattribute__(owner, "__closure__")
    assert type(closure) is tuple and len(closure) == 1
    cell = tuple.__getitem__(closure, 0)
    assert type(cell) is CellType
    descriptor = mutation_toolchain._EXACT_CALLABLE_CELL_CONTENTS_DESCRIPTOR
    original = descriptor.__get__(cell, CellType)
    callbacks = {
        "hostile": 0,
        "verifier_profile": 0,
        "runtime_profile": 0,
    }

    def hostile_delegate(*_args: object, **_kwargs: object) -> object:
        callbacks["hostile"] += 1
        return object()

    verifier_code = object.__getattribute__(
        mutation_toolchain._verify_eager_hypothesis_text_lazy_default,
        "__code__",
    )
    hostile_code = object.__getattribute__(hostile_delegate, "__code__")
    runtime_code_ids = _hypothesis_text_runtime_code_ids(evidence, hostile_code)

    def profiler(frame: object, event: str, _arg: object) -> None:
        if event != "call":
            return
        if frame.f_code is verifier_code:
            callbacks["verifier_profile"] += 1
        if id(frame.f_code) in runtime_code_ids:
            callbacks["runtime_profile"] += 1

    previous_profile = sys.getprofile()
    caught: BaseException | None = None
    try:
        cell.cell_contents = hostile_delegate
        sys.setprofile(profiler)
        try:
            _verify_hypothesis_text_default_binding()
        except BaseException as exc:
            caught = exc
    finally:
        sys.setprofile(previous_profile)
        cell.cell_contents = original

    assert isinstance(caught, MutationToolchainError)
    assert "text" in str(caught).lower() or "characters" in str(caught).lower()
    assert callbacks == {
        "hostile": 0,
        "verifier_profile": 1,
        "runtime_profile": 0,
    }
    assert descriptor.__get__(cell, CellType) is original
    assert sys.getprofile() is previous_profile
    _verify_hypothesis_text_default_binding()


@pytest.mark.parametrize(
    ("delegate_name", "cell_name"),
    (
        ("cached_delegate", "SearchStrategy"),
        ("cached_delegate", "_current_build_context"),
        ("cached_delegate", "fn"),
        ("defines_delegate", "eager"),
        ("defines_delegate", "force_reusable_values"),
        ("defines_delegate", "strategy_definition"),
        ("characters_cached_delegate", "SearchStrategy"),
        ("characters_cached_delegate", "_current_build_context"),
        ("characters_cached_delegate", "fn"),
        ("characters_defines_delegate", "eager"),
        ("characters_defines_delegate", "force_reusable_values"),
        ("characters_defines_delegate", "strategy_definition"),
    ),
)
def test_hypothesis_text_rejects_delegate_closure_cell_drift_without_execution(
    delegate_name: str,
    cell_name: str,
) -> None:
    evidence = _hypothesis_text_lazy_default_evidence()
    delegate = evidence[delegate_name]
    assert type(delegate) is FunctionType
    closure = object.__getattribute__(delegate, "__closure__")
    freevars = object.__getattribute__(delegate, "__code__").co_freevars
    assert type(closure) is tuple
    assert type(freevars) is tuple
    assert len(closure) == len(freevars)
    index = freevars.index(cell_name)
    cell = tuple.__getitem__(closure, index)
    assert type(cell) is CellType
    descriptor = mutation_toolchain._EXACT_CALLABLE_CELL_CONTENTS_DESCRIPTOR
    original = descriptor.__get__(cell, CellType)
    callbacks = {
        "hostile": 0,
        "verifier_profile": 0,
        "runtime_profile": 0,
    }

    def hostile_delegate(*_args: object, **_kwargs: object) -> object:
        callbacks["hostile"] += 1
        return object()

    if type(original) is bool:
        replacement: object = not original
    elif type(original) is FunctionType:
        replacement = hostile_delegate
    else:
        replacement = object()
    verifier_code = object.__getattribute__(
        mutation_toolchain._verify_eager_hypothesis_text_lazy_default,
        "__code__",
    )
    hostile_code = object.__getattribute__(hostile_delegate, "__code__")
    runtime_code_ids = _hypothesis_text_runtime_code_ids(evidence, hostile_code)

    def profiler(frame: object, event: str, _arg: object) -> None:
        if event != "call":
            return
        if frame.f_code is verifier_code:
            callbacks["verifier_profile"] += 1
        if id(frame.f_code) in runtime_code_ids:
            callbacks["runtime_profile"] += 1

    previous_profile = sys.getprofile()
    caught: BaseException | None = None
    try:
        cell.cell_contents = replacement
        sys.setprofile(profiler)
        try:
            _verify_hypothesis_text_default_binding()
        except BaseException as exc:
            caught = exc
    finally:
        sys.setprofile(previous_profile)
        cell.cell_contents = original

    assert isinstance(caught, MutationToolchainError)
    assert "text" in str(caught).lower() or "characters" in str(caught).lower()
    assert callbacks == {
        "hostile": 0,
        "verifier_profile": 1,
        "runtime_profile": 0,
    }
    assert descriptor.__get__(cell, CellType) is original
    assert sys.getprofile() is previous_profile
    _verify_hypothesis_text_default_binding()


@pytest.mark.parametrize(
    "attack",
    (
        "codec_value",
        "codec_equal_clone",
        "mapping_clone",
        "exact_rekey",
        "reorder",
        "subclass_key",
    ),
)
def test_hypothesis_text_rejects_lazy_kwargs_topology_drift_without_callbacks(
    attack: str,
) -> None:
    evidence = _hypothesis_text_lazy_default_evidence()
    namespace = evidence["default_namespace"]
    assert type(namespace) is dict
    namespace_items = tuple(dict.items(namespace))
    kwargs = dict.__getitem__(namespace, "_LazyStrategy__kwargs")
    assert type(kwargs) is dict
    kwargs_items = tuple(dict.items(kwargs))
    callbacks = {
        "eq": 0,
        "hash": 0,
        "repr": 0,
        "verifier_profile": 0,
        "runtime_profile": 0,
    }

    class HostileKey(str):
        def __eq__(self, other: object) -> bool:
            callbacks["eq"] += 1
            return str.__eq__(self, other)

        def __hash__(self) -> int:
            callbacks["hash"] += 1
            return str.__hash__(self)

        def __repr__(self) -> str:
            callbacks["repr"] += 1
            return "hostile-codec-key"

    provider = mutation_toolchain._verify_eager_hypothesis_text_lazy_default
    provider_code = object.__getattribute__(provider, "__code__")
    runtime_code_ids = _hypothesis_text_runtime_code_ids(evidence)

    def profiler(frame: object, event: str, _arg: object) -> None:
        if event != "call":
            return
        if frame.f_code is provider_code:
            callbacks["verifier_profile"] += 1
        if id(frame.f_code) in runtime_code_ids:
            callbacks["runtime_profile"] += 1

    previous_profile = sys.getprofile()
    caught: BaseException | None = None
    replacement_mapping: dict[object, object] | None = None
    try:
        target = tuple.__getitem__(tuple.__getitem__(kwargs_items, 0), 0)
        assert type(target) is str and str.__eq__(target, "codec")
        if attack == "mapping_clone":
            replacement_mapping = dict(kwargs_items)
            assert replacement_mapping is not kwargs
            dict.__setitem__(
                namespace,
                "_LazyStrategy__kwargs",
                replacement_mapping,
            )
        elif attack in {"exact_rekey", "subclass_key"}:
            replacement_key: str
            if attack == "exact_rekey":
                replacement_key = b"codec".decode("ascii")
                assert type(replacement_key) is str
                assert str.__eq__(replacement_key, target)
                assert replacement_key is not target
            else:
                replacement_key = HostileKey(target)
            replacement_items = tuple(
                (
                    replacement_key
                    if type(name) is str and str.__eq__(name, target)
                    else name,
                    value,
                )
                for name, value in kwargs_items
            )
            dict.clear(kwargs)
            for name, value in replacement_items:
                dict.__setitem__(kwargs, name, value)
        elif attack == "reorder":
            dict.clear(kwargs)
            for name, value in reversed(kwargs_items):
                dict.__setitem__(kwargs, name, value)
        elif attack == "codec_value":
            dict.__setitem__(kwargs, target, "ascii")
        else:
            original_codec = tuple.__getitem__(tuple.__getitem__(kwargs_items, 0), 1)
            codec_clone = bytearray(b"utf-8").decode("ascii")
            assert type(original_codec) is str
            assert type(codec_clone) is str
            assert str.__eq__(codec_clone, original_codec)
            assert codec_clone is not original_codec
            dict.__setitem__(kwargs, target, codec_clone)
        callbacks.update(
            eq=0,
            hash=0,
            repr=0,
            verifier_profile=0,
            runtime_profile=0,
        )
        sys.setprofile(profiler)
        try:
            _verify_hypothesis_text_default_binding()
        except BaseException as exc:
            caught = exc
    finally:
        sys.setprofile(previous_profile)
        dict.clear(namespace)
        for name, value in namespace_items:
            dict.__setitem__(namespace, name, value)
        dict.clear(kwargs)
        for name, value in kwargs_items:
            dict.__setitem__(kwargs, name, value)
        if replacement_mapping is not None:
            dict.clear(replacement_mapping)

    assert isinstance(caught, MutationToolchainError)
    assert "text" in str(caught).lower()
    assert callbacks == {
        "eq": 0,
        "hash": 0,
        "repr": 0,
        "verifier_profile": 1,
        "runtime_profile": 0,
    }
    assert sys.getprofile() is previous_profile
    _verify_hypothesis_text_default_binding()
    restored_namespace_items = tuple(dict.items(namespace))
    assert len(restored_namespace_items) == len(namespace_items)
    assert all(
        current_name is expected_name and current_value is expected_value
        for (current_name, current_value), (expected_name, expected_value) in zip(
            restored_namespace_items,
            namespace_items,
            strict=True,
        )
    )
    restored_kwargs_items = tuple(dict.items(kwargs))
    assert len(restored_kwargs_items) == len(kwargs_items)
    assert all(
        current_name is expected_name and current_value is expected_value
        for (current_name, current_value), (expected_name, expected_value) in zip(
            restored_kwargs_items,
            kwargs_items,
            strict=True,
        )
    )


@pytest.mark.parametrize(
    "attack",
    (
        "namespace_clone",
        "namespace_reorder",
        "namespace_exact_rekey",
        "namespace_subclass_key",
        "validate_clone",
        "validate_nonempty",
        "wrapped_strategy",
        "representation",
        "force_flag",
        "force_int_flag",
        "cache_flag",
        "cache_int_flag",
        "args_subclass",
        "transformations_subclass",
        "args_nonempty",
        "transformations_nonempty",
        "shared_nonempty_tuple",
        "split_equal_nonempty_tuples",
        "function_decorated",
        "function_clone",
    ),
)
def test_hypothesis_text_rejects_lazy_instance_state_drift_without_callbacks(
    attack: str,
) -> None:
    evidence = _hypothesis_text_lazy_default_evidence()
    default = evidence["default"]
    namespace = evidence["default_namespace"]
    characters_public = evidence["characters_public"]
    characters_source = evidence["characters_source"]
    assert type(namespace) is dict
    assert type(characters_public) is FunctionType
    assert type(characters_source) is FunctionType
    namespace_items = tuple(dict.items(namespace))
    validate_state = dict.__getitem__(namespace, "validate_called")
    assert type(validate_state) is dict
    validate_items = tuple(dict.items(validate_state))
    callbacks = {
        "eq": 0,
        "hash": 0,
        "repr": 0,
        "iter": 0,
        "len": 0,
        "getitem": 0,
        "provider_profile": 0,
        "runtime_profile": 0,
    }

    class HostileKey(str):
        def __eq__(self, other: object) -> bool:
            callbacks["eq"] += 1
            return str.__eq__(self, other)

        def __hash__(self) -> int:
            callbacks["hash"] += 1
            return str.__hash__(self)

        def __repr__(self) -> str:
            callbacks["repr"] += 1
            return "hostile-lazy-state-key"

    class HostileTuple(tuple):
        def __iter__(self) -> object:
            callbacks["iter"] += 1
            return tuple.__iter__(self)

        def __len__(self) -> int:
            callbacks["len"] += 1
            return tuple.__len__(self)

        def __getitem__(self, index: object) -> object:
            callbacks["getitem"] += 1
            return tuple.__getitem__(self, index)

        def __eq__(self, other: object) -> bool:
            callbacks["eq"] += 1
            return tuple.__eq__(self, other)

        def __hash__(self) -> int:
            callbacks["hash"] += 1
            return tuple.__hash__(self)

        def __repr__(self) -> str:
            callbacks["repr"] += 1
            return "hostile-empty-tuple"

    provider = mutation_toolchain._verify_eager_hypothesis_text_lazy_default
    provider_code = object.__getattribute__(provider, "__code__")
    runtime_code_ids = _hypothesis_text_runtime_code_ids(evidence)

    def profiler(frame: object, event: str, _arg: object) -> None:
        if event != "call":
            return
        if frame.f_code is provider_code:
            callbacks["provider_profile"] += 1
        if id(frame.f_code) in runtime_code_ids:
            callbacks["runtime_profile"] += 1

    previous_profile = sys.getprofile()
    caught: BaseException | None = None
    active_namespace = namespace
    callbacks.update(
        eq=0,
        hash=0,
        repr=0,
        iter=0,
        len=0,
        getitem=0,
        provider_profile=0,
        runtime_profile=0,
    )
    try:
        if attack == "namespace_clone":
            active_namespace = dict(namespace_items)
            object.__setattr__(default, "__dict__", active_namespace)
        elif attack == "namespace_reorder":
            dict.clear(namespace)
            for name, value in reversed(namespace_items):
                dict.__setitem__(namespace, name, value)
        elif attack in {"namespace_exact_rekey", "namespace_subclass_key"}:
            original_key = tuple.__getitem__(tuple.__getitem__(namespace_items, 0), 0)
            assert type(original_key) is str
            assert str.__eq__(original_key, "validate_called")
            if attack == "namespace_exact_rekey":
                replacement_key = bytearray(b"validate_called").decode("ascii")
                assert type(replacement_key) is str
                assert str.__eq__(replacement_key, original_key)
                assert replacement_key is not original_key
            else:
                replacement_key = HostileKey("validate_called")
            replacement_items = tuple(
                (
                    replacement_key
                    if type(name) is str and str.__eq__(name, "validate_called")
                    else name,
                    value,
                )
                for name, value in namespace_items
            )
            active_namespace = {}
            for name, value in replacement_items:
                dict.__setitem__(active_namespace, name, value)
            assert tuple.__getitem__(
                tuple(dict.items(active_namespace)),
                0,
            )[0] is replacement_key
            object.__setattr__(default, "__dict__", active_namespace)
        elif attack == "validate_clone":
            dict.__setitem__(namespace, "validate_called", dict(validate_items))
        elif attack == "validate_nonempty":
            dict.__setitem__(validate_state, object(), object())
        elif attack == "wrapped_strategy":
            dict.__setitem__(
                namespace,
                "_LazyStrategy__wrapped_strategy",
                object(),
            )
        elif attack == "representation":
            dict.__setitem__(
                namespace,
                "_LazyStrategy__representation",
                "characters(codec='utf-8')",
            )
        elif attack == "force_flag":
            dict.__setitem__(namespace, "force_has_reusable_values", False)
        elif attack == "force_int_flag":
            dict.__setitem__(namespace, "force_has_reusable_values", 1)
        elif attack == "cache_flag":
            dict.__setitem__(namespace, "cached_is_cacheable", False)
        elif attack == "cache_int_flag":
            dict.__setitem__(namespace, "cached_is_cacheable", 1)
        elif attack == "args_subclass":
            dict.__setitem__(namespace, "_LazyStrategy__args", HostileTuple())
        elif attack == "transformations_subclass":
            dict.__setitem__(namespace, "_transformations", HostileTuple())
        elif attack == "args_nonempty":
            dict.__setitem__(namespace, "_LazyStrategy__args", (object(),))
        elif attack == "transformations_nonempty":
            dict.__setitem__(namespace, "_transformations", (object(),))
        elif attack == "shared_nonempty_tuple":
            shared_nonempty = (object(),)
            dict.__setitem__(namespace, "_LazyStrategy__args", shared_nonempty)
            dict.__setitem__(namespace, "_transformations", shared_nonempty)
        elif attack == "split_equal_nonempty_tuples":
            marker = object()
            args_nonempty = (marker,)
            transformations_nonempty = tuple([marker])
            assert transformations_nonempty is not args_nonempty
            dict.__setitem__(namespace, "_LazyStrategy__args", args_nonempty)
            dict.__setitem__(
                namespace,
                "_transformations",
                transformations_nonempty,
            )
        elif attack == "function_decorated":
            dict.__setitem__(namespace, "function", characters_public)
        else:
            function_clone = _exact_function_clone(characters_source)
            assert function_clone is not characters_source
            dict.__setitem__(namespace, "function", function_clone)
        callbacks.update(
            eq=0,
            hash=0,
            repr=0,
            iter=0,
            len=0,
            getitem=0,
            provider_profile=0,
            runtime_profile=0,
        )
        sys.setprofile(profiler)
        try:
            _verify_hypothesis_text_default_binding()
        except BaseException as exc:
            caught = exc
    finally:
        sys.setprofile(previous_profile)
        object.__setattr__(default, "__dict__", namespace)
        dict.clear(namespace)
        for name, value in namespace_items:
            dict.__setitem__(namespace, name, value)
        dict.clear(validate_state)
        for name, value in validate_items:
            dict.__setitem__(validate_state, name, value)
        if active_namespace is not namespace:
            dict.clear(active_namespace)

    assert isinstance(caught, MutationToolchainError)
    assert "text" in str(caught).lower()
    assert callbacks == {
        "eq": 0,
        "hash": 0,
        "repr": 0,
        "iter": 0,
        "len": 0,
        "getitem": 0,
        "provider_profile": 1,
        "runtime_profile": 0,
    }
    assert sys.getprofile() is previous_profile
    assert object.__getattribute__(default, "__dict__") is namespace
    _verify_hypothesis_text_default_binding()
    restored_namespace_items = tuple(dict.items(namespace))
    assert len(restored_namespace_items) == len(namespace_items)
    assert all(
        current_name is expected_name and current_value is expected_value
        for (current_name, current_value), (expected_name, expected_value) in zip(
            restored_namespace_items,
            namespace_items,
            strict=True,
        )
    )
    restored_validate_items = tuple(dict.items(validate_state))
    assert len(restored_validate_items) == len(validate_items)
    assert all(
        current_name is expected_name and current_value is expected_value
        for (current_name, current_value), (expected_name, expected_value) in zip(
            restored_validate_items,
            validate_items,
            strict=True,
        )
    )


@pytest.mark.parametrize("mode", ("shared_clone", "split_clones"))
def test_hypothesis_text_rejects_coordinated_fresh_equal_state_lazy_default_clone(
    mode: str,
) -> None:
    evidence = _hypothesis_text_lazy_default_evidence()
    public = evidence["public"]
    wrapper = evidence["wrapper"]
    source = evidence["source"]
    default = evidence["default"]
    lazy_type = evidence["lazy_type"]
    namespace = evidence["default_namespace"]
    assert type(public) is FunctionType
    assert type(wrapper) is FunctionType
    assert type(source) is FunctionType
    assert type(lazy_type) is type
    assert type(namespace) is dict
    functions = (public, wrapper, source)
    original_defaults = tuple(
        object.__getattribute__(function, "__defaults__")
        for function in functions
    )
    namespace_items = tuple(dict.items(namespace))

    def exact_state_clone() -> object:
        clone = object.__new__(lazy_type)
        clone_namespace = object.__getattribute__(clone, "__dict__")
        assert type(clone_namespace) is dict
        for name, value in namespace_items:
            if type(value) is dict:
                changed_value = dict(dict.items(value))
                assert changed_value is not value
            else:
                changed_value = value
            dict.__setitem__(clone_namespace, name, changed_value)
        assert type(clone) is lazy_type
        assert clone is not default
        assert tuple(dict.keys(clone_namespace)) == tuple(dict.keys(namespace))
        return clone

    if mode == "shared_clone":
        shared_clone = exact_state_clone()
        clones = (shared_clone, shared_clone, shared_clone)
    else:
        clones = tuple(exact_state_clone() for _function in functions)
        assert all(
            current is not other
            for index, current in enumerate(clones)
            for other in clones[index + 1 :]
        )
    changed_defaults = tuple(tuple([clone]) for clone in clones)
    assert all(
        changed is not original
        for changed, original in zip(
            changed_defaults,
            original_defaults,
            strict=True,
        )
    )
    callbacks = {"verifier_profile": 0, "runtime_profile": 0}
    verifier_code = object.__getattribute__(
        mutation_toolchain._verify_eager_hypothesis_text_lazy_default,
        "__code__",
    )
    runtime_code_ids = _hypothesis_text_runtime_code_ids(evidence)

    def profiler(frame: object, event: str, _arg: object) -> None:
        if event != "call":
            return
        if frame.f_code is verifier_code:
            callbacks["verifier_profile"] += 1
        if id(frame.f_code) in runtime_code_ids:
            callbacks["runtime_profile"] += 1

    previous_profile = sys.getprofile()
    caught: BaseException | None = None
    try:
        for function, changed in zip(
            functions,
            changed_defaults,
            strict=True,
        ):
            function.__defaults__ = changed
        sys.setprofile(profiler)
        try:
            _verify_hypothesis_text_default_binding()
        except BaseException as exc:
            caught = exc
    finally:
        sys.setprofile(previous_profile)
        for function, original in zip(
            functions,
            original_defaults,
            strict=True,
        ):
            function.__defaults__ = original

    assert isinstance(caught, MutationToolchainError)
    assert "text" in str(caught).lower()
    assert callbacks == {"verifier_profile": 1, "runtime_profile": 0}
    assert sys.getprofile() is previous_profile
    assert all(
        object.__getattribute__(function, "__defaults__") is original
        for function, original in zip(
            functions,
            original_defaults,
            strict=True,
        )
    )
    _verify_hypothesis_text_default_binding()


@pytest.mark.parametrize("member_name", ("composite", "functions"))
def test_hypothesis_core_typing_or_guard_selects_exact_first_candidate_twice(
    member_name: str,
) -> None:
    module_name = "hypothesis.strategies._internal.core"
    for _attempt in range(2):
        evidence = _hypothesis_core_type_checking_guard_evidence(member_name)
        candidates = evidence["candidates"]
        assert type(candidates) is tuple
        active_index = evidence["expected_active_index"]
        assert type(active_index) is int
        assert evidence["active"] is tuple.__getitem__(
            candidates,
            active_index,
        )
        _verify_selected_binding(
            module_name,
            member_name,
            admitted_module_names=(
                module_name,
                "hypothesis.strategies._internal.utils",
            ),
        )


def test_hypothesis_core_typing_attribute_admission_is_exact() -> None:
    evidence = _hypothesis_core_type_checking_guard_evidence()
    typing_module = evidence["typing_module"]
    paramspec = evidence["paramspec"]
    assert type(typing_module) is ModuleType
    assert type(paramspec) is type
    raw_attribute = mutation_toolchain._raw_source_attribute
    defaults = object.__getattribute__(raw_attribute, "__defaults__")
    assert type(defaults) is tuple and len(defaults) >= 1
    authority = tuple.__getitem__(defaults, 0)
    assert authority is mutation_toolchain._SOURCE_GUARD_ATTRIBUTE_AUTHORITY
    assert authority.typing_module is typing_module
    assert authority.typing_paramspec is paramspec
    assert tuple(
        key
        for key, _value in authority.typing_entries
        if key in {"TYPE_CHECKING", "ParamSpec"}
    ) == ("TYPE_CHECKING", "ParamSpec")
    assert raw_attribute(
        typing_module,
        "TYPE_CHECKING",
        _source_provider_name="typing",
    ) is False
    assert raw_attribute(
        typing_module,
        "ParamSpec",
        _source_provider_name="typing",
    ) is paramspec
    with pytest.raises(
        MutationToolchainError,
        match="source guard typing attribute is unsupported: Any",
    ):
        raw_attribute(
            typing_module,
            "Any",
            _source_provider_name="typing",
        )
    assert (
        _hypothesis_core_type_checking_guard_evidence()["active"]
        == evidence["active"]
    )


@pytest.mark.parametrize(
    "attack_kind",
    (
        "owner_binding",
        "registry_value",
        "coherent_module_clone",
        "registry_container",
        "module_name",
        "specification_clone",
        "loader_clone",
        "coherent_provenance_clone",
        "origin_clone",
        "file_clone",
        "loader_path_clone",
    ),
)
def test_hypothesis_core_typing_provider_graph_rejects_coherent_drift(
    attack_kind: str,
) -> None:
    evidence = _hypothesis_core_type_checking_guard_evidence()
    module = evidence["module"]
    typing_module = evidence["typing_module"]
    assert type(module) is ModuleType
    assert type(typing_module) is ModuleType
    module_namespace = vars(module)
    typing_namespace = vars(typing_module)
    specification = dict.__getitem__(typing_namespace, "__spec__")
    loader = dict.__getitem__(typing_namespace, "__loader__")
    assert type(specification) is ModuleSpec
    assert type(loader) is SourceFileLoader
    specification_namespace = vars(specification)
    loader_namespace = vars(loader)
    module_items = tuple(dict.items(module_namespace))
    typing_items = tuple(dict.items(typing_namespace))
    specification_items = tuple(dict.items(specification_namespace))
    loader_items = tuple(dict.items(loader_namespace))
    original_registry = sys.modules
    original_typing_registry_value = dict.__getitem__(
        original_registry,
        "typing",
    )
    assert original_typing_registry_value is typing_module

    copied_typing = ModuleType("typing")
    _restore_exact_mapping_items(
        vars(copied_typing),
        tuple(dict.items(typing_namespace)),
    )
    original_name = dict.__getitem__(typing_namespace, "__name__")
    original_origin = dict.__getitem__(specification_namespace, "origin")
    original_file = dict.__getitem__(typing_namespace, "__file__")
    original_loader_path = dict.__getitem__(loader_namespace, "path")
    assert all(
        type(value) is str
        for value in (
            original_name,
            original_origin,
            original_file,
            original_loader_path,
        )
    )

    def fresh_equal(value: str) -> str:
        changed = (" " + value)[1:]
        assert changed == value and changed is not value
        return changed

    caught: BaseException | None = None
    try:
        if attack_kind == "owner_binding":
            dict.__setitem__(module_namespace, "typing", copied_typing)
        elif attack_kind == "registry_value":
            dict.__setitem__(original_registry, "typing", copied_typing)
        elif attack_kind == "coherent_module_clone":
            dict.__setitem__(module_namespace, "typing", copied_typing)
            dict.__setitem__(original_registry, "typing", copied_typing)
        elif attack_kind == "registry_container":
            sys.modules = dict(dict.items(original_registry))
            assert sys.modules is not original_registry
        elif attack_kind == "module_name":
            dict.__setitem__(
                typing_namespace,
                "__name__",
                fresh_equal(original_name),
            )
        elif attack_kind == "specification_clone":
            copied_specification = ModuleSpec(
                original_name,
                loader,
                origin=original_origin,
            )
            _restore_exact_mapping_items(
                vars(copied_specification),
                specification_items,
            )
            dict.__setitem__(
                typing_namespace,
                "__spec__",
                copied_specification,
            )
        elif attack_kind == "loader_clone":
            copied_loader = SourceFileLoader(original_name, original_file)
            _restore_exact_mapping_items(vars(copied_loader), loader_items)
            dict.__setitem__(typing_namespace, "__loader__", copied_loader)
            dict.__setitem__(
                specification_namespace,
                "loader",
                copied_loader,
            )
        elif attack_kind == "coherent_provenance_clone":
            fresh_path = fresh_equal(original_file)
            copied_loader = SourceFileLoader(original_name, fresh_path)
            _restore_exact_mapping_items(vars(copied_loader), loader_items)
            dict.__setitem__(vars(copied_loader), "path", fresh_path)
            copied_specification = ModuleSpec(
                original_name,
                copied_loader,
                origin=fresh_path,
            )
            _restore_exact_mapping_items(
                vars(copied_specification),
                specification_items,
            )
            dict.__setitem__(
                vars(copied_specification),
                "loader",
                copied_loader,
            )
            dict.__setitem__(
                vars(copied_specification),
                "origin",
                fresh_path,
            )
            dict.__setitem__(
                typing_namespace,
                "__spec__",
                copied_specification,
            )
            dict.__setitem__(typing_namespace, "__loader__", copied_loader)
            dict.__setitem__(typing_namespace, "__file__", fresh_path)
        elif attack_kind == "origin_clone":
            dict.__setitem__(
                specification_namespace,
                "origin",
                fresh_equal(original_origin),
            )
        elif attack_kind == "file_clone":
            dict.__setitem__(
                typing_namespace,
                "__file__",
                fresh_equal(original_file),
            )
        elif attack_kind == "loader_path_clone":
            dict.__setitem__(
                loader_namespace,
                "path",
                fresh_equal(original_loader_path),
            )
        else:
            raise AssertionError(attack_kind)
        try:
            _select_hypothesis_core_composite_candidate(evidence)
        except BaseException as exc:
            caught = exc
    finally:
        sys.modules = original_registry
        dict.__setitem__(original_registry, "typing", typing_module)
        _restore_exact_mapping_items(loader_namespace, loader_items)
        _restore_exact_mapping_items(
            specification_namespace,
            specification_items,
        )
        _restore_exact_mapping_items(typing_namespace, typing_items)
        _restore_exact_mapping_items(module_namespace, module_items)

    assert isinstance(caught, MutationToolchainError)
    expected_error = (
        "source guard attribute reader binding changed"
        if attack_kind == "registry_container"
        else "typing"
    )
    assert expected_error in str(caught)
    assert sys.modules is original_registry
    assert dict.__getitem__(original_registry, "typing") is typing_module
    assert _mapping_items_are_identical(module_namespace, module_items)
    assert _mapping_items_are_identical(typing_namespace, typing_items)
    assert _mapping_items_are_identical(
        specification_namespace,
        specification_items,
    )
    assert _mapping_items_are_identical(loader_namespace, loader_items)
    assert (
        _hypothesis_core_type_checking_guard_evidence()["active"]
        == evidence["active"]
    )


@pytest.mark.parametrize("changed_value", (True, 0))
def test_hypothesis_core_type_checking_requires_exact_false(
    changed_value: object,
) -> None:
    evidence = _hypothesis_core_type_checking_guard_evidence()
    typing_module = evidence["typing_module"]
    assert type(typing_module) is ModuleType
    namespace = vars(typing_module)
    original_items = tuple(dict.items(namespace))
    raw_code = object.__getattribute__(
        mutation_toolchain._raw_source_attribute,
        "__code__",
    )
    callbacks = {"raw_profile": 0}

    def profiler(frame: object, event: str, _arg: object) -> None:
        if event == "call" and frame.f_code is raw_code:
            callbacks["raw_profile"] += 1

    previous_profile = sys.getprofile()
    caught: BaseException | None = None
    try:
        dict.__setitem__(namespace, "TYPE_CHECKING", changed_value)
        sys.setprofile(profiler)
        try:
            _select_hypothesis_core_composite_candidate(evidence)
        except BaseException as exc:
            caught = exc
    finally:
        sys.setprofile(previous_profile)
        _restore_exact_mapping_items(namespace, original_items)

    assert isinstance(caught, MutationToolchainError)
    assert "source guard typing provider graph changed" in str(caught)
    assert callbacks == {"raw_profile": 1}
    assert sys.getprofile() is previous_profile
    assert _mapping_items_are_identical(namespace, original_items)
    assert (
        _hypothesis_core_type_checking_guard_evidence()["active"]
        == evidence["active"]
    )


@pytest.mark.parametrize(
    ("attack_kind", "expect_failure"),
    (
        ("missing", True),
        ("reordered_exact", False),
        ("fresh_equal", True),
        ("hostile_subclass", True),
    ),
)
def test_hypothesis_core_type_checking_selected_key_identity_is_exact(
    attack_kind: str,
    expect_failure: bool,
) -> None:
    evidence = _hypothesis_core_type_checking_guard_evidence()
    typing_module = evidence["typing_module"]
    assert type(typing_module) is ModuleType
    namespace = vars(typing_module)
    original_items = tuple(dict.items(namespace))
    matching = tuple(
        (index, key, value)
        for index, (key, value) in enumerate(original_items)
        if type(key) is str and str.__eq__(key, "TYPE_CHECKING")
    )
    assert len(matching) == 1
    target_index, target_key, target_value = matching[0]
    assert target_value is False
    callbacks = {"eq": 0, "hash": 0, "repr": 0}

    class HostileKey(str):
        def __eq__(self, other: object) -> bool:
            callbacks["eq"] += 1
            return str.__eq__(self, other)

        def __hash__(self) -> int:
            callbacks["hash"] += 1
            return str.__hash__(self)

        def __repr__(self) -> str:
            callbacks["repr"] += 1
            return "hostile-type-checking-key"

    replacement_items = list(original_items)
    if attack_kind == "missing":
        replacement_items.pop(target_index)
    elif attack_kind == "reordered_exact":
        paramspec_index = next(
            index
            for index, (key, _value) in enumerate(replacement_items)
            if type(key) is str and str.__eq__(key, "ParamSpec")
        )
        replacement_items[target_index], replacement_items[paramspec_index] = (
            replacement_items[paramspec_index],
            replacement_items[target_index],
        )
    elif attack_kind == "fresh_equal":
        fresh_key = bytearray(target_key, "ascii").decode("ascii")
        assert fresh_key == target_key and fresh_key is not target_key
        replacement_items[target_index] = (fresh_key, target_value)
    elif attack_kind == "hostile_subclass":
        replacement_items[target_index] = (
            HostileKey("TYPE_CHECKING"),
            target_value,
        )
    else:
        raise AssertionError(attack_kind)

    caught: BaseException | None = None
    selected: object | None = None
    try:
        _restore_exact_mapping_items(namespace, tuple(replacement_items))
        callbacks.update(eq=0, hash=0, repr=0)
        try:
            selected = _select_hypothesis_core_composite_candidate(evidence)
        except BaseException as exc:
            caught = exc
    finally:
        _restore_exact_mapping_items(namespace, original_items)

    if expect_failure:
        assert isinstance(caught, MutationToolchainError)
        assert selected is None
    else:
        assert caught is None
        assert selected is evidence["active"]
    assert callbacks == {"eq": 0, "hash": 0, "repr": 0}
    assert _mapping_items_are_identical(namespace, original_items)
    assert (
        _hypothesis_core_type_checking_guard_evidence()["active"]
        == evidence["active"]
    )


@pytest.mark.parametrize(
    "attack_kind",
    ("none", "replacement", "coherent_hostile_impostor"),
)
def test_hypothesis_core_paramspec_requires_exact_typing_provider(
    attack_kind: str,
) -> None:
    evidence = _hypothesis_core_type_checking_guard_evidence()
    module = evidence["module"]
    typing_module = evidence["typing_module"]
    paramspec = evidence["paramspec"]
    assert type(module) is ModuleType
    assert type(typing_module) is ModuleType
    assert type(paramspec) is type
    module_namespace = vars(module)
    typing_namespace = vars(typing_module)
    module_items = tuple(dict.items(module_namespace))
    typing_items = tuple(dict.items(typing_namespace))
    callbacks = {"getattribute": 0, "eq": 0, "hash": 0, "repr": 0}

    class HostileParamSpecMeta(type):
        def __getattribute__(self, name: str) -> object:
            callbacks["getattribute"] += 1
            return type.__getattribute__(self, name)

        def __eq__(self, _other: object) -> bool:
            callbacks["eq"] += 1
            return True

        def __hash__(self) -> int:
            callbacks["hash"] += 1
            return type.__hash__(self)

        def __repr__(self) -> str:
            callbacks["repr"] += 1
            return "typing.ParamSpec"

    if attack_kind == "none":
        replacement: object = None
    elif attack_kind == "replacement":
        replacement = object()
    elif attack_kind == "coherent_hostile_impostor":
        replacement = HostileParamSpecMeta(
            "ParamSpec",
            (),
            {"__module__": "typing", "__qualname__": "ParamSpec"},
        )
    else:
        raise AssertionError(attack_kind)

    caught: BaseException | None = None
    try:
        dict.__setitem__(typing_namespace, "ParamSpec", replacement)
        dict.__setitem__(module_namespace, "ParamSpec", replacement)
        callbacks.update(getattribute=0, eq=0, hash=0, repr=0)
        try:
            _select_hypothesis_core_composite_candidate(evidence)
        except BaseException as exc:
            caught = exc
    finally:
        _restore_exact_mapping_items(typing_namespace, typing_items)
        _restore_exact_mapping_items(module_namespace, module_items)

    assert isinstance(caught, MutationToolchainError)
    assert "source guard typing" in str(caught)
    assert callbacks == {"getattribute": 0, "eq": 0, "hash": 0, "repr": 0}
    assert _mapping_items_are_identical(module_namespace, module_items)
    assert _mapping_items_are_identical(typing_namespace, typing_items)
    assert vars(typing_module)["ParamSpec"] is paramspec
    assert vars(module)["ParamSpec"] is paramspec
    assert (
        _hypothesis_core_type_checking_guard_evidence()["active"]
        == evidence["active"]
    )


@pytest.mark.parametrize(
    ("attack_kind", "expect_failure"),
    (
        ("unrelated_exact_string", False),
        ("unrelated_hostile_string", True),
        ("unrelated_non_string", True),
    ),
)
def test_hypothesis_core_typing_namespace_allows_only_safe_unrelated_keys(
    attack_kind: str,
    expect_failure: bool,
) -> None:
    evidence = _hypothesis_core_type_checking_guard_evidence()
    typing_module = evidence["typing_module"]
    assert type(typing_module) is ModuleType
    namespace = vars(typing_module)
    original_items = tuple(dict.items(namespace))
    callbacks = {"eq": 0, "hash": 0, "repr": 0}

    class HostileKey(str):
        def __eq__(self, other: object) -> bool:
            callbacks["eq"] += 1
            return str.__eq__(self, other)

        def __hash__(self) -> int:
            callbacks["hash"] += 1
            return str.__hash__(self)

        def __repr__(self) -> str:
            callbacks["repr"] += 1
            return "hostile-unrelated-typing-key"

    if attack_kind == "unrelated_exact_string":
        key: object = "_phase11_unrelated_typing_canary"
    elif attack_kind == "unrelated_hostile_string":
        key = HostileKey("_phase11_unrelated_typing_canary")
    elif attack_kind == "unrelated_non_string":
        key = object()
    else:
        raise AssertionError(attack_kind)

    caught: BaseException | None = None
    selected: object | None = None
    try:
        dict.__setitem__(namespace, key, object())
        callbacks.update(eq=0, hash=0, repr=0)
        try:
            selected = _select_hypothesis_core_composite_candidate(evidence)
        except BaseException as exc:
            caught = exc
    finally:
        _restore_exact_mapping_items(namespace, original_items)

    if expect_failure:
        assert isinstance(caught, MutationToolchainError)
        assert selected is None
    else:
        assert caught is None
        assert selected is evidence["active"]
    assert callbacks == {"eq": 0, "hash": 0, "repr": 0}
    assert _mapping_items_are_identical(namespace, original_items)
    assert (
        _hypothesis_core_type_checking_guard_evidence()["active"]
        == evidence["active"]
    )


@pytest.mark.parametrize(
    "reader_name",
    (
        "_raw_source_attribute",
        "_closed_source_reference",
        "_closed_source_expression_value",
        "_closed_source_truth",
        "_closed_source_compare",
        "_active_source_binding_candidate",
    ),
)
@pytest.mark.parametrize(
    "attack_kind",
    ("code_clone", "defaults_clone", "kwdefault_hostile_key"),
)
def test_hypothesis_core_guard_caller_chain_rejects_reader_drift_before_execution(
    reader_name: str,
    attack_kind: str,
) -> None:
    evidence = _hypothesis_core_type_checking_guard_evidence()
    reader = vars(mutation_toolchain)[reader_name]
    assert type(reader) is FunctionType
    original_code = object.__getattribute__(reader, "__code__")
    original_defaults = object.__getattribute__(reader, "__defaults__")
    original_kwdefaults = object.__getattribute__(reader, "__kwdefaults__")
    original_kwdefault_items = (
        tuple(dict.items(original_kwdefaults))
        if type(original_kwdefaults) is dict
        else ()
    )
    callbacks = {"eq": 0, "hash": 0, "repr": 0, "profile": 0}

    class HostileKey(str):
        def __eq__(self, other: object) -> bool:
            callbacks["eq"] += 1
            return str.__eq__(self, other)

        def __hash__(self) -> int:
            callbacks["hash"] += 1
            return str.__hash__(self)

        def __repr__(self) -> str:
            callbacks["repr"] += 1
            return f"hostile-{reader_name}-kwdefault-key"

    changed_code = original_code
    changed_kwdefaults: dict[object, object] | None = None
    changed_kwdefault_items: tuple[tuple[object, object], ...] | None = None
    if attack_kind == "code_clone":
        changed_code = original_code.replace()
        assert changed_code is not original_code
    elif attack_kind == "defaults_clone":
        if type(original_defaults) is tuple:
            changed_defaults: object = tuple(list(original_defaults))
            assert changed_defaults is not original_defaults
        else:
            assert original_defaults is None
            changed_defaults = ()
    elif attack_kind == "kwdefault_hostile_key":
        if original_kwdefault_items:
            target_key, target_value = original_kwdefault_items[0]
            assert type(target_key) is str
            changed_kwdefault_items = (
                (HostileKey(target_key), target_value),
                *original_kwdefault_items[1:],
            )
        else:
            changed_kwdefault_items = (
                (HostileKey("_phase11_hostile"), object()),
            )
        changed_kwdefaults = (
            original_kwdefaults
            if type(original_kwdefaults) is dict
            else dict(changed_kwdefault_items)
        )
    else:
        raise AssertionError(attack_kind)

    target_code_ids = {id(original_code), id(changed_code)}

    def profiler(frame: object, event: str, _arg: object) -> None:
        if event == "call" and id(frame.f_code) in target_code_ids:
            callbacks["profile"] += 1

    def invoke() -> None:
        module_name = "hypothesis.strategies._internal.core"
        _verify_selected_binding(
            module_name,
            "composite",
            admitted_module_names=(
                module_name,
                "hypothesis.strategies._internal.utils",
            ),
        )

    previous_profile = sys.getprofile()
    caught: BaseException | None = None
    try:
        if attack_kind == "code_clone":
            reader.__code__ = changed_code
        elif attack_kind == "defaults_clone":
            reader.__defaults__ = changed_defaults
        else:
            assert changed_kwdefaults is not None
            assert changed_kwdefault_items is not None
            if type(original_kwdefaults) is dict:
                _restore_exact_mapping_items(
                    original_kwdefaults,
                    changed_kwdefault_items,
                )
            else:
                reader.__kwdefaults__ = changed_kwdefaults
        callbacks.update(eq=0, hash=0, repr=0, profile=0)
        sys.setprofile(profiler)
        try:
            invoke()
        except BaseException as exc:
            caught = exc
    finally:
        sys.setprofile(previous_profile)
        reader.__code__ = original_code
        reader.__defaults__ = original_defaults
        reader.__kwdefaults__ = original_kwdefaults
        if type(original_kwdefaults) is dict:
            _restore_exact_mapping_items(
                original_kwdefaults,
                original_kwdefault_items,
            )

    assert isinstance(caught, MutationToolchainError)
    assert callbacks == {"eq": 0, "hash": 0, "repr": 0, "profile": 0}
    assert sys.getprofile() is previous_profile
    assert object.__getattribute__(reader, "__code__") is original_code
    assert object.__getattribute__(reader, "__defaults__") is original_defaults
    assert (
        object.__getattribute__(reader, "__kwdefaults__")
        is original_kwdefaults
    )
    if type(original_kwdefaults) is dict:
        assert _mapping_items_are_identical(
            original_kwdefaults,
            original_kwdefault_items,
        )
    invoke()
    assert (
        _hypothesis_core_type_checking_guard_evidence()["active"]
        == evidence["active"]
    )


def test_hypothesis_core_guard_rejects_captured_typing_authority_drift_before_raw_execution() -> None:
    evidence = _hypothesis_core_type_checking_guard_evidence()
    raw_attribute = mutation_toolchain._raw_source_attribute
    raw_code = object.__getattribute__(raw_attribute, "__code__")
    defaults = object.__getattribute__(raw_attribute, "__defaults__")
    assert type(defaults) is tuple and defaults
    authority = tuple.__getitem__(defaults, 0)
    original_typing_module = authority.typing_module
    assert original_typing_module is evidence["typing_module"]
    copied_typing = ModuleType("typing")
    _restore_exact_mapping_items(
        vars(copied_typing),
        tuple(dict.items(vars(original_typing_module))),
    )
    callbacks = {"raw_profile": 0}

    def profiler(frame: object, event: str, _arg: object) -> None:
        if event == "call" and frame.f_code is raw_code:
            callbacks["raw_profile"] += 1

    previous_profile = sys.getprofile()
    caught: BaseException | None = None
    try:
        object.__setattr__(authority, "typing_module", copied_typing)
        sys.setprofile(profiler)
        try:
            _select_hypothesis_core_composite_candidate(evidence)
        except BaseException as exc:
            caught = exc
    finally:
        sys.setprofile(previous_profile)
        object.__setattr__(authority, "typing_module", original_typing_module)

    assert isinstance(caught, MutationToolchainError)
    assert callbacks == {"raw_profile": 0}
    assert sys.getprofile() is previous_profile
    assert authority.typing_module is original_typing_module
    assert (
        _hypothesis_core_type_checking_guard_evidence()["active"]
        == evidence["active"]
    )


@pytest.mark.parametrize("member_name", ("composite", "functions"))
def test_hypothesis_core_typing_guard_selection_never_executes_runtime_callables(
    member_name: str,
) -> None:
    evidence = _hypothesis_core_type_checking_guard_evidence(member_name)
    module = evidence["module"]
    assert type(module) is ModuleType
    pending = [vars(module)[member_name], vars(module)[f"_{member_name}"]]
    visited: set[int] = set()
    runtime_codes: set[int] = set()
    descriptor = mutation_toolchain._EXACT_CALLABLE_CELL_CONTENTS_DESCRIPTOR
    while pending:
        current = pending.pop()
        if type(current) is not FunctionType or id(current) in visited:
            continue
        visited.add(id(current))
        runtime_codes.add(id(object.__getattribute__(current, "__code__")))
        wrapped = dict.get(vars(current), "__wrapped__")
        if type(wrapped) is FunctionType:
            pending.append(wrapped)
        closure = object.__getattribute__(current, "__closure__")
        if type(closure) is tuple:
            for cell in closure:
                captured = descriptor.__get__(cell, CellType)
                if type(captured) is FunctionType:
                    pending.append(captured)
    assert runtime_codes
    callbacks = {"runtime_profile": 0}

    def profiler(frame: object, event: str, _arg: object) -> None:
        if event == "call" and id(frame.f_code) in runtime_codes:
            callbacks["runtime_profile"] += 1

    previous_profile = sys.getprofile()
    selected: object | None = None
    try:
        sys.setprofile(profiler)
        selected = _select_hypothesis_core_composite_candidate(evidence)
    finally:
        sys.setprofile(previous_profile)

    assert selected is evidence["active"]
    assert callbacks == {"runtime_profile": 0}
    assert sys.getprofile() is previous_profile
    assert vars(module)["ParamSpec"] is evidence["paramspec"]
    assert vars(module)["P"] is not None


@pytest.mark.parametrize(
    "attack_kind",
    ("and", "not_equal", "swapped", "extra_operand"),
)
def test_hypothesis_core_typing_or_guard_rejects_shape_forgery(
    attack_kind: str,
) -> None:
    evidence = _hypothesis_core_type_checking_guard_evidence()
    module = evidence["module"]
    policy = evidence["policy"]
    binding = evidence["binding"]
    candidates = evidence["candidates"]
    assert type(module) is ModuleType
    assert type(policy) is mutation_toolchain._SourceCodePolicy
    assert type(binding) is mutation_toolchain._SourceBinding
    assert type(candidates) is tuple
    guard = tuple.__getitem__(tuple.__getitem__(candidates, 0).guards, 0)
    expression = guard.expression
    payload = object.__getattribute__(expression, "payload")
    assert type(payload) is tuple and len(payload) == 2
    comparison = tuple.__getitem__(payload, 1)
    assert type(comparison) is mutation_toolchain._SourceExpression
    original_expression_ast = object.__getattribute__(expression, "ast_shape")
    original_comparison_payload = object.__getattribute__(comparison, "payload")
    original_comparison_ast = object.__getattribute__(comparison, "ast_shape")

    if attack_kind == "and":
        forged_expression = replace(
            expression,
            kind="and",
            ast_shape=original_expression_ast.replace("op=Or()", "op=And()"),
        )
    elif attack_kind == "not_equal":
        assert type(original_comparison_payload) is tuple
        left = tuple.__getitem__(original_comparison_payload, 0)
        operations = tuple.__getitem__(original_comparison_payload, 1)
        right = tuple.__getitem__(tuple.__getitem__(operations, 0), 1)
        forged_comparison = replace(
            comparison,
            payload=(left, (("ne", right),)),
            ast_shape=original_comparison_ast.replace("IsNot", "NotEq"),
        )
        forged_expression = replace(
            expression,
            payload=(tuple.__getitem__(payload, 0), forged_comparison),
        )
    elif attack_kind == "swapped":
        forged_expression = replace(
            expression,
            payload=tuple(reversed(payload)),
            ast_shape=(
                "BoolOp(op=Or(), values=[Compare(left=Name(id='ParamSpec', "
                "ctx=Load()), ops=[IsNot()], comparators=[Constant(value=None)]), "
                "Attribute(value=Name(id='typing', ctx=Load()), "
                "attr='TYPE_CHECKING', ctx=Load())])"
            ),
        )
    elif attack_kind == "extra_operand":
        extra = mutation_toolchain._SourceExpression(
            kind="literal",
            payload=["bool", False],
            ast_shape="Constant(value=False)",
        )
        forged_expression = replace(
            expression,
            payload=(*payload, extra),
            ast_shape=(
                original_expression_ast[:-2] + ", Constant(value=False)])"
            ),
        )
    else:
        raise AssertionError(attack_kind)
    forged_guard = replace(guard, expression=forged_expression)
    forged_candidate = replace(
        tuple.__getitem__(candidates, 0),
        guards=(forged_guard,),
    )
    forged_binding = replace(
        binding,
        candidates=(forged_candidate, *candidates[1:]),
    )
    assert forged_binding is not binding
    assert any(item is binding for item in policy.bindings)
    assert all(item is not forged_binding for item in policy.bindings)

    caught: BaseException | None = None
    try:
        mutation_toolchain._active_source_binding_candidate(
            module,
            policy=policy,
            binding=forged_binding,
        )
    except BaseException as exc:
        caught = exc

    assert isinstance(caught, MutationToolchainError)
    assert (
        _hypothesis_core_type_checking_guard_evidence()["active"]
        == evidence["active"]
    )


@pytest.mark.parametrize(
    ("record_type_name", "field_name"),
    (
        ("_SourceImportBinding", "name"),
        ("_SourceImportCandidate", "attribute"),
    ),
)
def test_hypothesis_core_typing_guard_rejects_hostile_import_descriptor_before_callback(
    record_type_name: str,
    field_name: str,
) -> None:
    evidence = _hypothesis_core_type_checking_guard_evidence()
    record_type = vars(mutation_toolchain)[record_type_name]
    namespace = type.__getattribute__(record_type, "__dict__")
    original_descriptor = namespace[field_name]
    callbacks: list[str] = []

    def hostile_field(_record: object) -> str:
        callbacks.append(field_name)
        return field_name

    caught: BaseException | None = None
    try:
        type.__setattr__(record_type, field_name, property(hostile_field))
        try:
            _select_hypothesis_core_composite_candidate(evidence)
        except BaseException as exc:
            caught = exc
    finally:
        type.__setattr__(record_type, field_name, original_descriptor)

    assert isinstance(caught, MutationToolchainError)
    assert "descriptor changed" in str(caught)
    assert callbacks == []
    assert (
        type.__getattribute__(record_type, "__dict__")[field_name]
        is original_descriptor
    )
    assert (
        _hypothesis_core_type_checking_guard_evidence()["active"]
        == evidence["active"]
    )


def test_hypothesis_core_typing_guard_reseals_truth_after_raw_return() -> None:
    evidence = _hypothesis_core_type_checking_guard_evidence()
    raw_attribute = mutation_toolchain._raw_source_attribute
    truth_reader = mutation_toolchain._closed_source_truth
    raw_code = object.__getattribute__(raw_attribute, "__code__")
    truth_code = object.__getattribute__(truth_reader, "__code__")
    changed_truth_code = truth_code.replace()
    assert changed_truth_code is not truth_code
    truth_code_ids = {id(truth_code), id(changed_truth_code)}
    callbacks = {"raw_profile": 0, "truth_profile": 0, "mutation": 0}

    def profiler(frame: object, event: str, _arg: object) -> None:
        if frame.f_code is raw_code:
            if event == "call":
                callbacks["raw_profile"] += 1
            elif event == "return" and callbacks["mutation"] == 0:
                callbacks["mutation"] += 1
                truth_reader.__code__ = changed_truth_code
        elif event == "call" and id(frame.f_code) in truth_code_ids:
            callbacks["truth_profile"] += 1

    previous_profile = sys.getprofile()
    caught: BaseException | None = None
    try:
        sys.setprofile(profiler)
        try:
            _select_hypothesis_core_composite_candidate(evidence)
        except BaseException as exc:
            caught = exc
    finally:
        sys.setprofile(previous_profile)
        truth_reader.__code__ = truth_code

    assert isinstance(caught, MutationToolchainError)
    assert callbacks == {
        "raw_profile": 1,
        "truth_profile": 0,
        "mutation": 1,
    }
    assert sys.getprofile() is previous_profile
    assert object.__getattribute__(truth_reader, "__code__") is truth_code
    assert (
        _hypothesis_core_type_checking_guard_evidence()["active"]
        == evidence["active"]
    )


def test_hypothesis_datetimes_source_defaults_are_exact_and_verify_twice() -> None:
    module_name = "hypothesis.strategies._internal.datetime"
    module = import_module(module_name)
    public = vars(module)["datetimes"]
    source = vars(public)["__wrapped__"]
    public_defaults = public.__defaults__
    source_defaults = source.__defaults__
    public_kwdefaults = public.__kwdefaults__
    source_kwdefaults = source.__kwdefaults__

    assert public_defaults is not source_defaults
    assert public_defaults == source_defaults
    assert public_defaults is not None
    assert public_defaults[0] is datetime.datetime.min
    assert public_defaults[1] is datetime.datetime.max
    assert public_kwdefaults is not source_kwdefaults
    assert public_kwdefaults is not None
    assert source_kwdefaults is not None
    assert tuple(public_kwdefaults) == ("timezones", "allow_imaginary")
    assert tuple(source_kwdefaults) == ("timezones", "allow_imaginary")
    assert public_kwdefaults["timezones"] is source_kwdefaults["timezones"]
    assert public_kwdefaults["allow_imaginary"] is True
    assert source_kwdefaults["allow_imaginary"] is True

    for _ in range(2):
        _verify_selected_binding(
            module_name,
            "datetimes",
            admitted_module_names=(
                module_name,
                "hypothesis.strategies._internal.utils",
            ),
        )


@pytest.mark.parametrize("mutation", ["swapped", "duplicate", "fresh_equal"])
def test_hypothesis_datetimes_source_defaults_reject_coordinated_mutation(
    mutation: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "hypothesis.strategies._internal.datetime"
    module = import_module(module_name)
    public = vars(module)["datetimes"]
    source = vars(public)["__wrapped__"]
    if mutation == "swapped":
        defaults = (datetime.datetime.max, datetime.datetime.min)
    elif mutation == "duplicate":
        defaults = (datetime.datetime.min, datetime.datetime.min)
    else:
        fresh_min = datetime.datetime(1, 1, 1)
        assert fresh_min == datetime.datetime.min
        assert fresh_min is not datetime.datetime.min
        defaults = (fresh_min, datetime.datetime.max)
    monkeypatch.setattr(mutation_toolchain, "_RUNTIME_SOURCE_SENTINELS", {})
    monkeypatch.setattr(public, "__defaults__", defaults)
    monkeypatch.setattr(source, "__defaults__", defaults)

    with pytest.raises(
        MutationToolchainError,
        match=r"Hypothesis temporal none\(\) default graph changed",
    ):
        _verify_selected_binding(
            module_name,
            "datetimes",
            admitted_module_names=(
                module_name,
                "hypothesis.strategies._internal.utils",
            ),
        )
    assert mutation_toolchain._RUNTIME_SOURCE_SENTINELS == {}


@pytest.mark.parametrize(
    "mutation",
    ["timezone", "false_flag", "integer_flag", "extra", "reordered"],
)
def test_hypothesis_datetimes_reject_coordinated_keyword_default_mutation(
    mutation: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "hypothesis.strategies._internal.datetime"
    module = import_module(module_name)
    public = vars(module)["datetimes"]
    source = vars(public)["__wrapped__"]
    original = source.__kwdefaults__
    assert original is not None
    changed = dict(original)
    if mutation == "timezone":
        changed["timezones"] = object()
    elif mutation == "false_flag":
        changed["allow_imaginary"] = False
    elif mutation == "integer_flag":
        changed["allow_imaginary"] = 1
    elif mutation == "extra":
        changed["extra"] = None
    else:
        changed = {
            "allow_imaginary": original["allow_imaginary"],
            "timezones": original["timezones"],
        }
    monkeypatch.setattr(public, "__kwdefaults__", dict(changed))
    monkeypatch.setattr(source, "__kwdefaults__", dict(changed))

    with pytest.raises(
        MutationToolchainError,
        match=r"Hypothesis temporal none\(\) default graph changed",
    ):
        _verify_selected_binding(
            module_name,
            "datetimes",
            admitted_module_names=(
                module_name,
                "hypothesis.strategies._internal.utils",
            ),
        )


def test_hypothesis_datetimes_reject_annotation_provider_replacement_without_callbacks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "hypothesis.strategies._internal.datetime"
    module = import_module(module_name)
    public = vars(module)["datetimes"]
    source = vars(public)["__wrapped__"]
    callbacks = {"count": 0}

    def hostile_annotate(_format: object) -> dict[str, object]:
        callbacks["count"] += 1
        return {}

    monkeypatch.setattr(public, "__annotate__", hostile_annotate)
    monkeypatch.setattr(source, "__annotate__", hostile_annotate)
    with pytest.raises(
        MutationToolchainError,
        match=r"Hypothesis temporal none\(\) provider binding changed",
    ):
        _verify_selected_binding(
            module_name,
            "datetimes",
            admitted_module_names=(
                module_name,
                "hypothesis.strategies._internal.utils",
            ),
        )
    assert callbacks == {"count": 0}


@pytest.mark.parametrize("attack", ["rebound", "same_object_code"])
def test_hypothesis_datetimes_reject_source_default_helper_replacement_without_callbacks(
    attack: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "hypothesis.strategies._internal.datetime"
    module = import_module(module_name)
    public = vars(module)["datetimes"]
    source = vars(public)["__wrapped__"]
    callbacks = {"count": 0}

    def hostile_verifier(*_args: object, **_kwargs: object) -> None:
        callbacks["count"] += 1

    def hostile_code(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("mutated datetime-default verifier executed")

    _verify_selected_binding(
        module_name,
        "datetimes",
        admitted_module_names=(
            module_name,
            "hypothesis.strategies._internal.utils",
        ),
    )
    with monkeypatch.context() as patch:
        patch.setattr(
            public,
            "__defaults__",
            (datetime.datetime.max, datetime.datetime.min),
        )
        patch.setattr(
            source,
            "__defaults__",
            (datetime.datetime.max, datetime.datetime.min),
        )
        if attack == "rebound":
            patch.setattr(
                mutation_toolchain,
                "_verify_source_declared_datetime_defaults",
                hostile_verifier,
            )
        else:
            helper = mutation_toolchain._verify_source_declared_datetime_defaults
            patch.setattr(helper, "__code__", hostile_code.__code__)
        with pytest.raises(
            MutationToolchainError,
            match="loaded source verifier binding changed",
        ):
            _verify_selected_binding(
                module_name,
                "datetimes",
                admitted_module_names=(
                    module_name,
                    "hypothesis.strategies._internal.utils",
                ),
            )
        assert callbacks == {"count": 0}
    _verify_selected_binding(
        module_name,
        "datetimes",
        admitted_module_names=(
            module_name,
            "hypothesis.strategies._internal.utils",
        ),
    )


@pytest.mark.parametrize(
    "dependency_name",
    ["_closed_source_expression_value", "_normalized_code_sha256"],
)
def test_hypothesis_datetimes_reject_source_default_dependency_replacement_without_callbacks(
    dependency_name: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "hypothesis.strategies._internal.datetime"
    module, binding, attested, _admitted_paths, policy = _selected_binding_evidence(
        module_name,
        "datetimes",
        admitted_module_names=(
            module_name,
            "hypothesis.strategies._internal.utils",
        ),
    )
    source_binding = mutation_toolchain._source_binding_for_manifest(
        policy,
        binding,
    )
    assert len(source_binding.candidates) == 1
    candidate = source_binding.candidates[0]
    public = vars(module)["datetimes"]
    source = vars(public)["__wrapped__"]
    verifier = mutation_toolchain._verify_source_declared_datetime_defaults
    callbacks = {"count": 0}

    def hostile_dependency(*_args: object, **_kwargs: object) -> object:
        callbacks["count"] += 1
        return None

    monkeypatch.setattr(
        mutation_toolchain,
        dependency_name,
        hostile_dependency,
    )
    with pytest.raises(
        MutationToolchainError,
        match="source-default verifier dependency changed",
    ):
        verifier(
            module,
            path="datetimes",
            candidate=candidate,
            public_value=public,
            bound_functions=(public, source),
            matched_function=source,
            policy=policy,
            import_sentinels={},
            attested_code_identities=attested,
        )
    assert callbacks == {"count": 0}


def test_datetime_datetime_source_default_singletons_reject_impostors_without_callbacks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert mutation_toolchain._runtime_value_shape(datetime.datetime.min) == [
        "reviewed-source-default-singleton-v1",
        "datetime.datetime.min",
    ]
    assert mutation_toolchain._runtime_value_shape(datetime.datetime.max) == [
        "reviewed-source-default-singleton-v1",
        "datetime.datetime.max",
    ]
    for equal_distinct in (
        datetime.datetime(1, 1, 1),
        datetime.datetime(9999, 12, 31, 23, 59, 59, 999999),
    ):
        with pytest.raises(
            MutationToolchainError,
            match="unsupported datetime.datetime value",
        ):
            mutation_toolchain._runtime_value_shape(equal_distinct)

    callbacks = {"count": 0}

    class HostileDateTime(datetime.datetime):
        def __getattribute__(self, name: str) -> object:
            callbacks["count"] += 1
            return super().__getattribute__(name)

        def __eq__(self, other: object) -> bool:
            callbacks["count"] += 1
            return True

        def __hash__(self) -> int:
            callbacks["count"] += 1
            return 0

        def __reduce__(self) -> object:
            callbacks["count"] += 1
            return (datetime.datetime, (1, 1, 1))

        def __repr__(self) -> str:
            callbacks["count"] += 1
            return "datetime.datetime(1, 1, 1)"

    HostileDateTime.__module__ = "datetime"
    HostileDateTime.__qualname__ = "datetime"
    hostile_subclass = HostileDateTime(1, 1, 1)

    class HostileMetadata:
        def __getattribute__(self, name: str) -> object:
            callbacks["count"] += 1
            return super().__getattribute__(name)

        def __eq__(self, other: object) -> bool:
            callbacks["count"] += 1
            return True

        def __hash__(self) -> int:
            callbacks["count"] += 1
            return 0

        def __reduce__(self) -> object:
            callbacks["count"] += 1
            return (object, ())

        def __repr__(self) -> str:
            callbacks["count"] += 1
            return "datetime.datetime(1, 1, 1)"

    HostileMetadata.__module__ = "datetime"
    HostileMetadata.__qualname__ = "datetime"
    hostile_metadata = HostileMetadata()
    callbacks["count"] = 0
    for hostile in (hostile_subclass, hostile_metadata):
        alias = ModuleType(f"hostile_datetime_alias_{id(hostile)}")
        alias.endpoint = hostile
        monkeypatch.setitem(sys.modules, alias.__name__, alias)
        with pytest.raises(
            MutationToolchainError,
            match="datetime.datetime impostor",
        ):
            mutation_toolchain._runtime_value_shape(hostile)
        assert callbacks == {"count": 0}


def test_datetime_runtime_shape_rejects_provider_verifier_code_mutation_without_callbacks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = mutation_toolchain._verify_eager_datetime_date_provider
    def hostile_provider() -> None:
        raise AssertionError("mutated datetime provider verifier executed")

    monkeypatch.setattr(provider, "__code__", hostile_provider.__code__)
    with pytest.raises(
        MutationToolchainError,
        match="datetime runtime-shape verifier binding changed",
    ):
        mutation_toolchain._runtime_value_shape(datetime.datetime.min)


@pytest.mark.parametrize(
    (
        "path",
        "expected_public_defaults",
        "expected_source_defaults",
        "expected_timezone_default",
        "expected_endpoints",
        "expected_tag",
    ),
    (
        (
            "datetimes",
            mutation_toolchain._EAGER_HYPOTHESIS_DATETIMES_PUBLIC_DEFAULTS,
            mutation_toolchain._EAGER_HYPOTHESIS_DATETIMES_SOURCE_DEFAULTS,
            mutation_toolchain._EAGER_HYPOTHESIS_DATETIMES_TIMEZONES_DEFAULT,
            (datetime.datetime.min, datetime.datetime.max),
            "hypothesis.strategies._internal.datetime.datetimes.timezones",
        ),
        (
            "times",
            mutation_toolchain._EAGER_HYPOTHESIS_TIMES_PUBLIC_DEFAULTS,
            mutation_toolchain._EAGER_HYPOTHESIS_TIMES_SOURCE_DEFAULTS,
            mutation_toolchain._EAGER_HYPOTHESIS_TIMES_TIMEZONES_DEFAULT,
            (datetime.time.min, datetime.time.max),
            "hypothesis.strategies._internal.datetime.times.timezones",
        ),
    ),
)
def test_hypothesis_temporal_timezone_defaults_are_path_exact_and_verify_twice(
    path: str,
    expected_public_defaults: tuple[object, ...],
    expected_source_defaults: tuple[object, ...],
    expected_timezone_default: object,
    expected_endpoints: tuple[object, object],
    expected_tag: str,
) -> None:
    module_name = "hypothesis.strategies._internal.datetime"
    module = import_module(module_name)
    public = vars(module)[path]
    source = vars(public)["__wrapped__"]
    public_kwdefaults = public.__kwdefaults__
    source_kwdefaults = source.__kwdefaults__

    assert public.__defaults__ is expected_public_defaults
    assert source.__defaults__ is expected_source_defaults
    assert expected_public_defaults is not expected_source_defaults
    assert expected_public_defaults == expected_endpoints
    assert expected_source_defaults == expected_endpoints
    assert public_kwdefaults is not source_kwdefaults
    assert public_kwdefaults is not None
    assert source_kwdefaults is not None
    assert public_kwdefaults["timezones"] is expected_timezone_default
    assert source_kwdefaults["timezones"] is expected_timezone_default
    assert mutation_toolchain._runtime_value_shape(expected_timezone_default) == [
        "reviewed-source-default-reference-v1",
        expected_tag,
    ]

    for _ in range(2):
        _verify_selected_binding(
            module_name,
            path,
            admitted_module_names=(
                module_name,
                "hypothesis.strategies._internal.utils",
            ),
        )


def test_hypothesis_temporal_timezone_defaults_have_distinct_mutable_state() -> None:
    datetimes_default = (
        mutation_toolchain._EAGER_HYPOTHESIS_DATETIMES_TIMEZONES_DEFAULT
    )
    times_default = mutation_toolchain._EAGER_HYPOTHESIS_TIMES_TIMEZONES_DEFAULT
    datetimes_namespace = object.__getattribute__(datetimes_default, "__dict__")
    times_namespace = object.__getattribute__(times_default, "__dict__")

    assert datetimes_default is not times_default
    assert datetimes_namespace is not times_namespace
    assert datetimes_namespace["validate_called"] is not times_namespace[
        "validate_called"
    ]
    assert datetimes_namespace["_LazyStrategy__kwargs"] is not times_namespace[
        "_LazyStrategy__kwargs"
    ]
    assert datetimes_namespace["function"] is times_namespace["function"]
    assert datetimes_namespace["function"] is (
        mutation_toolchain._EAGER_HYPOTHESIS_NONE_SOURCE
    )
    mutation_toolchain._verify_eager_hypothesis_temporal_none_defaults()


def test_datetime_time_source_default_singletons_reject_impostors_without_callbacks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert mutation_toolchain._runtime_value_shape(datetime.time.min) == [
        "reviewed-source-default-singleton-v1",
        "datetime.time.min",
    ]
    assert mutation_toolchain._runtime_value_shape(datetime.time.max) == [
        "reviewed-source-default-singleton-v1",
        "datetime.time.max",
    ]
    for equal_distinct in (
        datetime.time(0, 0),
        datetime.time(23, 59, 59, 999999),
    ):
        with pytest.raises(
            MutationToolchainError,
            match="unsupported datetime.time value",
        ):
            mutation_toolchain._runtime_value_shape(equal_distinct)

    callbacks = {"count": 0}

    class HostileTime(datetime.time):
        def __getattribute__(self, name: str) -> object:
            callbacks["count"] += 1
            return super().__getattribute__(name)

        def __eq__(self, other: object) -> bool:
            callbacks["count"] += 1
            return True

        def __hash__(self) -> int:
            callbacks["count"] += 1
            return 0

        def __reduce__(self) -> object:
            callbacks["count"] += 1
            return (datetime.time, (0, 0))

        def __repr__(self) -> str:
            callbacks["count"] += 1
            return "datetime.time(0, 0)"

    HostileTime.__module__ = "datetime"
    HostileTime.__qualname__ = "time"
    hostile_subclass = HostileTime(0, 0)

    class HostileMetadata:
        def __getattribute__(self, name: str) -> object:
            callbacks["count"] += 1
            return super().__getattribute__(name)

        def __eq__(self, other: object) -> bool:
            callbacks["count"] += 1
            return True

        def __hash__(self) -> int:
            callbacks["count"] += 1
            return 0

        def __reduce__(self) -> object:
            callbacks["count"] += 1
            return (object, ())

        def __repr__(self) -> str:
            callbacks["count"] += 1
            return "datetime.time(0, 0)"

    HostileMetadata.__module__ = "datetime"
    HostileMetadata.__qualname__ = "time"
    hostile_metadata = HostileMetadata()
    callbacks["count"] = 0
    for hostile in (hostile_subclass, hostile_metadata):
        alias = ModuleType(f"hostile_datetime_time_alias_{id(hostile)}")
        alias.endpoint = hostile
        monkeypatch.setitem(sys.modules, alias.__name__, alias)
        with pytest.raises(
            MutationToolchainError,
            match="datetime.time impostor",
        ):
            mutation_toolchain._runtime_value_shape(hostile)
        assert callbacks == {"count": 0}


@pytest.mark.parametrize(
    ("path", "expected_min", "expected_max"),
    (
        ("datetimes", datetime.datetime.min, datetime.datetime.max),
        ("times", datetime.time.min, datetime.time.max),
    ),
)
@pytest.mark.parametrize("attack", ("swapped", "same_object", "clone"))
def test_hypothesis_temporal_rejects_coordinated_positional_default_attacks(
    path: str,
    expected_min: object,
    expected_max: object,
    attack: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = mutation_toolchain._EAGER_HYPOTHESIS_DATETIME_MODULE
    public = vars(module)[path]
    source = vars(public)["__wrapped__"]
    public_defaults = public.__defaults__
    source_defaults = source.__defaults__
    assert public_defaults is not None
    assert source_defaults is not None
    assert public_defaults is not source_defaults

    if attack == "swapped":
        changed_public = tuple([expected_max, expected_min])
        changed_source = tuple([expected_max, expected_min])
    elif attack == "same_object":
        changed_public = public_defaults
        changed_source = public_defaults
    else:
        changed_public = tuple(list(public_defaults))
        changed_source = tuple(list(source_defaults))
        assert changed_public is not public_defaults
        assert changed_source is not source_defaults
        assert changed_public is not changed_source

    with monkeypatch.context() as mutation:
        mutation.setattr(public, "__defaults__", changed_public)
        mutation.setattr(source, "__defaults__", changed_source)
        with pytest.raises(
            MutationToolchainError,
            match="Hypothesis temporal none\\(\\) default graph changed",
        ):
            mutation_toolchain._verify_eager_hypothesis_temporal_none_defaults()

    mutation_toolchain._verify_eager_hypothesis_temporal_none_defaults()


@pytest.mark.parametrize(
    ("path", "attack"),
    (
        ("datetimes", "same_object"),
        ("datetimes", "clone"),
        ("datetimes", "fresh_lazy"),
        ("datetimes", "cross_path"),
        ("datetimes", "unrelated"),
        ("datetimes", "extra"),
        ("datetimes", "reordered"),
        ("times", "same_object"),
        ("times", "clone"),
        ("times", "fresh_lazy"),
        ("times", "cross_path"),
        ("times", "unrelated"),
        ("times", "extra"),
    ),
)
def test_hypothesis_temporal_rejects_coordinated_keyword_default_attacks(
    path: str,
    attack: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = mutation_toolchain._EAGER_HYPOTHESIS_DATETIME_MODULE
    public = vars(module)[path]
    source = vars(public)["__wrapped__"]
    public_kwdefaults = public.__kwdefaults__
    source_kwdefaults = source.__kwdefaults__
    assert public_kwdefaults is not None
    assert source_kwdefaults is not None
    assert public_kwdefaults is not source_kwdefaults
    public_items = tuple(dict.items(public_kwdefaults))
    source_items = tuple(dict.items(source_kwdefaults))
    expected = (
        mutation_toolchain._EAGER_HYPOTHESIS_DATETIMES_TIMEZONES_DEFAULT
        if path == "datetimes"
        else mutation_toolchain._EAGER_HYPOTHESIS_TIMES_TIMEZONES_DEFAULT
    )
    other = (
        mutation_toolchain._EAGER_HYPOTHESIS_TIMES_TIMEZONES_DEFAULT
        if path == "datetimes"
        else mutation_toolchain._EAGER_HYPOTHESIS_DATETIMES_TIMEZONES_DEFAULT
    )
    callbacks = {"count": 0}

    class Hostile:
        def __getattribute__(self, name: str) -> object:
            callbacks["count"] += 1
            return super().__getattribute__(name)

        def __eq__(self, other_value: object) -> bool:
            callbacks["count"] += 1
            return True

        def __hash__(self) -> int:
            callbacks["count"] += 1
            return 0

        def __repr__(self) -> str:
            callbacks["count"] += 1
            return "none()"

    hostile = Hostile()

    def restore(mapping: dict[str, object], items: tuple[tuple[str, object], ...]) -> None:
        dict.clear(mapping)
        for key, value in items:
            dict.__setitem__(mapping, key, value)

    with monkeypatch.context() as mutation:
        try:
            if attack == "same_object":
                mutation.setattr(public, "__kwdefaults__", public_kwdefaults)
                mutation.setattr(source, "__kwdefaults__", public_kwdefaults)
            elif attack == "clone":
                mutation.setattr(public, "__kwdefaults__", dict(public_items))
                mutation.setattr(source, "__kwdefaults__", dict(source_items))
            elif attack == "fresh_lazy":
                fresh = mutation_toolchain._EAGER_HYPOTHESIS_LAZY_STRATEGY_TYPE(
                    mutation_toolchain._EAGER_HYPOTHESIS_NONE_SOURCE,
                    (),
                    {},
                )
                assert fresh is not expected
                dict.__setitem__(public_kwdefaults, "timezones", fresh)
                dict.__setitem__(source_kwdefaults, "timezones", fresh)
            elif attack == "cross_path":
                dict.__setitem__(public_kwdefaults, "timezones", other)
                dict.__setitem__(source_kwdefaults, "timezones", other)
            elif attack == "unrelated":
                dict.__setitem__(public_kwdefaults, "timezones", hostile)
                dict.__setitem__(source_kwdefaults, "timezones", hostile)
            elif attack == "extra":
                dict.__setitem__(public_kwdefaults, "extra", hostile)
                dict.__setitem__(source_kwdefaults, "extra", hostile)
            else:
                assert path == "datetimes"
                restore(public_kwdefaults, tuple(reversed(public_items)))
                restore(source_kwdefaults, tuple(reversed(source_items)))
            callbacks["count"] = 0
            with pytest.raises(
                MutationToolchainError,
                match="Hypothesis temporal none\\(\\) default graph changed",
            ):
                mutation_toolchain._verify_eager_hypothesis_temporal_none_defaults()
            assert callbacks == {"count": 0}
        finally:
            restore(public_kwdefaults, public_items)
            restore(source_kwdefaults, source_items)

    mutation_toolchain._verify_eager_hypothesis_temporal_none_defaults()


def test_hypothesis_temporal_default_paths_reject_coordinated_cross_swap() -> None:
    datetimes_public = mutation_toolchain._EAGER_HYPOTHESIS_DATETIMES_PUBLIC_KWDEFAULTS
    datetimes_source = mutation_toolchain._EAGER_HYPOTHESIS_DATETIMES_SOURCE_KWDEFAULTS
    times_public = mutation_toolchain._EAGER_HYPOTHESIS_TIMES_PUBLIC_KWDEFAULTS
    times_source = mutation_toolchain._EAGER_HYPOTHESIS_TIMES_SOURCE_KWDEFAULTS
    datetimes_default = (
        mutation_toolchain._EAGER_HYPOTHESIS_DATETIMES_TIMEZONES_DEFAULT
    )
    times_default = mutation_toolchain._EAGER_HYPOTHESIS_TIMES_TIMEZONES_DEFAULT

    for mapping in (datetimes_public, datetimes_source):
        dict.__setitem__(mapping, "timezones", times_default)
    for mapping in (times_public, times_source):
        dict.__setitem__(mapping, "timezones", datetimes_default)
    try:
        with pytest.raises(
            MutationToolchainError,
            match="Hypothesis temporal none\\(\\) default graph changed",
        ):
            mutation_toolchain._verify_eager_hypothesis_temporal_none_defaults()
    finally:
        for mapping in (datetimes_public, datetimes_source):
            dict.__setitem__(mapping, "timezones", datetimes_default)
        for mapping in (times_public, times_source):
            dict.__setitem__(mapping, "timezones", times_default)

    mutation_toolchain._verify_eager_hypothesis_temporal_none_defaults()


@pytest.mark.parametrize("path", ("datetimes", "times"))
@pytest.mark.parametrize(
    "field",
    (
        "validate_called",
        "_LazyStrategy__wrapped_strategy",
        "_LazyStrategy__representation",
        "function",
        "_LazyStrategy__args",
        "_LazyStrategy__kwargs",
        "_transformations",
        "force_has_reusable_values",
        "extra",
    ),
)
def test_hypothesis_temporal_lazy_defaults_reject_every_mutable_field_without_callbacks(
    path: str,
    field: str,
) -> None:
    default = (
        mutation_toolchain._EAGER_HYPOTHESIS_DATETIMES_TIMEZONES_DEFAULT
        if path == "datetimes"
        else mutation_toolchain._EAGER_HYPOTHESIS_TIMES_TIMEZONES_DEFAULT
    )
    namespace = object.__getattribute__(default, "__dict__")
    callbacks = {"count": 0}

    class Hostile:
        def __getattribute__(self, name: str) -> object:
            callbacks["count"] += 1
            return super().__getattribute__(name)

        def __eq__(self, other: object) -> bool:
            callbacks["count"] += 1
            return True

        def __hash__(self) -> int:
            callbacks["count"] += 1
            return 0

        def __repr__(self) -> str:
            callbacks["count"] += 1
            return "none()"

    hostile = Hostile()

    def hostile_function() -> object:
        callbacks["count"] += 1
        return hostile

    nested: dict[object, object] | None = None
    original: object | None = None
    if field in {"validate_called", "_LazyStrategy__kwargs"}:
        nested = namespace[field]
        assert type(nested) is dict
        dict.__setitem__(nested, "hostile", hostile)
    else:
        if field != "extra":
            original = namespace[field]
        if field == "function":
            replacement: object = hostile_function
        elif field in {"_LazyStrategy__args", "_transformations"}:
            replacement = (hostile,)
        elif field == "force_has_reusable_values":
            replacement = False
        else:
            replacement = hostile
        dict.__setitem__(namespace, field, replacement)
    callbacks["count"] = 0
    try:
        with pytest.raises(
            MutationToolchainError,
            match="Hypothesis temporal none\\(\\) pristine state changed",
        ):
            mutation_toolchain._verify_eager_hypothesis_temporal_none_defaults()
    finally:
        if nested is not None:
            dict.__delitem__(nested, "hostile")
        elif field == "extra":
            dict.__delitem__(namespace, field)
        else:
            dict.__setitem__(namespace, field, original)
    assert callbacks == {"count": 0}
    mutation_toolchain._verify_eager_hypothesis_temporal_none_defaults()


@pytest.mark.parametrize("target", ("public", "source", "accept"))
def test_hypothesis_temporal_none_rejects_same_object_callable_code_attacks(
    target: str,
) -> None:
    if target == "public":
        function = mutation_toolchain._EAGER_HYPOTHESIS_NONE_PUBLIC

        def hostile_factory(anchor: object) -> FunctionType:
            def hostile(*_args: object, **_kwargs: object) -> object:
                _ = anchor
                raise AssertionError("mutated temporal none wrapper executed")

            return hostile

        hostile_code = hostile_factory(object()).__code__
    elif target == "source":
        function = mutation_toolchain._EAGER_HYPOTHESIS_NONE_SOURCE

        def hostile_source(*_args: object, **_kwargs: object) -> object:
            raise AssertionError("mutated temporal none source executed")

        hostile_code = hostile_source.__code__
    else:
        function = mutation_toolchain._EAGER_HYPOTHESIS_NONE_ACCEPT

        def hostile_factory(
            first: object,
            second: object,
            third: object,
        ) -> FunctionType:
            def hostile(*_args: object, **_kwargs: object) -> object:
                _ = (first, second, third)
                raise AssertionError("mutated temporal none delegate executed")

            return hostile

        hostile_code = hostile_factory(object(), object(), object()).__code__

    original = object.__getattribute__(function, "__code__")
    function.__code__ = hostile_code
    try:
        with pytest.raises(
            MutationToolchainError,
            match="Hypothesis temporal none\\(\\) provider binding changed",
        ):
            mutation_toolchain._verify_eager_hypothesis_temporal_none_defaults()
    finally:
        function.__code__ = original
    mutation_toolchain._verify_eager_hypothesis_temporal_none_defaults()


@pytest.mark.parametrize(
    ("target", "attribute"),
    (
        ("public", "__module__"),
        ("public", "__name__"),
        ("public", "__qualname__"),
        ("source", "__module__"),
        ("source", "__name__"),
        ("source", "__qualname__"),
        ("accept", "__module__"),
        ("accept", "__name__"),
        ("accept", "__qualname__"),
    ),
)
def test_hypothesis_temporal_none_rejects_callable_metadata_attacks(
    target: str,
    attribute: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    function = {
        "public": mutation_toolchain._EAGER_HYPOTHESIS_NONE_PUBLIC,
        "source": mutation_toolchain._EAGER_HYPOTHESIS_NONE_SOURCE,
        "accept": mutation_toolchain._EAGER_HYPOTHESIS_NONE_ACCEPT,
    }[target]
    with monkeypatch.context() as mutation:
        mutation.setattr(function, attribute, "forged")
        with pytest.raises(
            MutationToolchainError,
            match="Hypothesis temporal none\\(\\) provider binding changed",
        ):
            mutation_toolchain._verify_eager_hypothesis_temporal_none_defaults()
    mutation_toolchain._verify_eager_hypothesis_temporal_none_defaults()


@pytest.mark.parametrize("attack", ("datetime_binding", "misc_binding", "wrapped"))
def test_hypothesis_temporal_none_rejects_callable_binding_attacks_without_callbacks(
    attack: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    callbacks = {"count": 0}

    def hostile(*_args: object, **_kwargs: object) -> object:
        callbacks["count"] += 1
        return object()

    public = mutation_toolchain._EAGER_HYPOTHESIS_NONE_PUBLIC
    with monkeypatch.context() as mutation:
        if attack == "datetime_binding":
            mutation.setattr(
                mutation_toolchain._EAGER_HYPOTHESIS_DATETIME_MODULE,
                "none",
                hostile,
            )
        elif attack == "misc_binding":
            mutation.setattr(
                mutation_toolchain._EAGER_HYPOTHESIS_MISC_MODULE,
                "none",
                hostile,
            )
        else:
            mutation.setattr(public, "__wrapped__", hostile)
        with pytest.raises(
            MutationToolchainError,
            match="Hypothesis temporal none\\(\\) provider binding changed",
        ):
            mutation_toolchain._verify_eager_hypothesis_temporal_none_defaults()
        assert callbacks == {"count": 0}
    mutation_toolchain._verify_eager_hypothesis_temporal_none_defaults()


def test_hypothesis_temporal_none_rejects_public_wrapper_closure_attack_without_callbacks() -> None:
    public = mutation_toolchain._EAGER_HYPOTHESIS_NONE_PUBLIC
    closure = object.__getattribute__(public, "__closure__")
    assert closure is not None
    assert len(closure) == 1
    cell = closure[0]
    descriptor = mutation_toolchain._EXACT_CALLABLE_CELL_CONTENTS_DESCRIPTOR
    original = descriptor.__get__(cell, CellType)
    callbacks = {"count": 0}

    def hostile_delegate(*_args: object, **_kwargs: object) -> object:
        callbacks["count"] += 1
        return object()

    cell.cell_contents = hostile_delegate
    try:
        with pytest.raises(
            MutationToolchainError,
            match="Hypothesis temporal none\\(\\) provider binding changed",
        ):
            mutation_toolchain._verify_eager_hypothesis_temporal_none_defaults()
    finally:
        cell.cell_contents = original
    assert callbacks == {"count": 0}
    mutation_toolchain._verify_eager_hypothesis_temporal_none_defaults()


@pytest.mark.parametrize(
    "cell_name",
    ("eager", "force_reusable_values", "strategy_definition"),
)
def test_hypothesis_temporal_none_rejects_hidden_delegate_closure_attacks(
    cell_name: str,
) -> None:
    accept = mutation_toolchain._EAGER_HYPOTHESIS_NONE_ACCEPT
    closure = object.__getattribute__(accept, "__closure__")
    assert closure is not None
    names = object.__getattribute__(accept, "__code__").co_freevars
    index = names.index(cell_name)
    cell = closure[index]
    descriptor = mutation_toolchain._EXACT_CALLABLE_CELL_CONTENTS_DESCRIPTOR
    original = descriptor.__get__(cell, CellType)

    def hostile_source(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("mutated temporal none closure executed")

    if cell_name == "eager":
        replacement: object = True
    elif cell_name == "force_reusable_values":
        replacement = False
    else:
        replacement = hostile_source
    cell.cell_contents = replacement
    try:
        with pytest.raises(
            MutationToolchainError,
            match="Hypothesis temporal none\\(\\) provider binding changed",
        ):
            mutation_toolchain._verify_eager_hypothesis_temporal_none_defaults()
    finally:
        cell.cell_contents = original
    mutation_toolchain._verify_eager_hypothesis_temporal_none_defaults()


def test_hypothesis_temporal_runtime_rejects_provider_verifier_code_mutation_before_execution() -> None:
    provider = mutation_toolchain._verify_eager_hypothesis_temporal_none_defaults
    default = mutation_toolchain._EAGER_HYPOTHESIS_DATETIMES_TIMEZONES_DEFAULT

    def hostile_provider() -> None:
        raise AssertionError("mutated temporal provider verifier executed")

    original = object.__getattribute__(provider, "__code__")
    provider.__code__ = hostile_provider.__code__
    try:
        with pytest.raises(
            MutationToolchainError,
            match="Hypothesis temporal none\\(\\) runtime verifier binding changed",
        ):
            mutation_toolchain._runtime_value_shape(default)
    finally:
        provider.__code__ = original
    mutation_toolchain._verify_eager_hypothesis_temporal_none_defaults()


def test_hypothesis_times_rejects_annotation_provider_replacement_without_callbacks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "hypothesis.strategies._internal.datetime"
    module = import_module(module_name)
    public = vars(module)["times"]
    source = vars(public)["__wrapped__"]
    callbacks = {"count": 0}

    def hostile_annotate(_format: object) -> dict[str, object]:
        callbacks["count"] += 1
        return {}

    with monkeypatch.context() as mutation:
        mutation.setattr(public, "__annotate__", hostile_annotate)
        mutation.setattr(source, "__annotate__", hostile_annotate)
        with pytest.raises(
            MutationToolchainError,
            match=(
                "(?:Hypothesis temporal none\\(\\) provider binding changed|"
                "Hypothesis times annotation provider changed)"
            ),
        ):
            _verify_selected_binding(
                module_name,
                "times",
                admitted_module_names=(
                    module_name,
                    "hypothesis.strategies._internal.utils",
                ),
            )
        assert callbacks == {"count": 0}

    mutation_toolchain._verify_eager_hypothesis_temporal_none_defaults()


@pytest.mark.parametrize("path", ("datetimes", "times"))
@pytest.mark.parametrize(
    "attack",
    (
        "endpoint_default",
        "timezone_default",
        "timezone_annotation",
        "return_annotation",
    ),
)
def test_hypothesis_temporal_rejects_forged_source_default_and_annotation_semantics(
    path: str,
    attack: str,
) -> None:
    module_name = "hypothesis.strategies._internal.datetime"
    module, binding, attested, _admitted_paths, policy = (
        _selected_binding_evidence(
            module_name,
            path,
            admitted_module_names=(
                module_name,
                "hypothesis.strategies._internal.utils",
            ),
        )
    )
    source_binding = mutation_toolchain._source_binding_for_manifest(
        policy,
        binding,
    )
    assert len(source_binding.candidates) == 1
    candidate = source_binding.candidates[0]
    semantics = candidate.function_semantics
    assert semantics is not None

    if attack == "endpoint_default":
        defaults = list(semantics.defaults)
        default = defaults[0]
        owner = "datetime" if path == "datetimes" else "time"
        changed_expression = replace(
            default.expression,
            payload=("dt", owner, "max"),
            ast_shape=ast.dump(
                ast.parse(f"dt.{owner}.max", mode="eval").body,
                include_attributes=False,
            ),
        )
        defaults[0] = replace(default, expression=changed_expression)
        changed_semantics = replace(semantics, defaults=tuple(defaults))
        expected_error = "sealed source default expression changed"
    elif attack == "timezone_default":
        defaults = list(semantics.defaults)
        index = next(
            index
            for index, default in enumerate(defaults)
            if default.parameter == "timezones"
        )
        default = defaults[index]
        changed_expression = replace(
            default.expression,
            ast_shape=ast.dump(
                ast.parse("none(1)", mode="eval").body,
                include_attributes=False,
            ),
        )
        defaults[index] = replace(default, expression=changed_expression)
        changed_semantics = replace(semantics, defaults=tuple(defaults))
        expected_error = "sealed source keyword-default semantics changed"
    else:
        annotations = list(semantics.annotations)
        expected_name = "timezones" if attack == "timezone_annotation" else "return"
        index = next(
            index
            for index, annotation in enumerate(annotations)
            if annotation[0] == expected_name
        )
        name, kind, expression = annotations[index]
        annotations[index] = (
            name,
            kind,
            replace(
                expression,
                ast_shape=ast.dump(
                    ast.parse(
                        "SearchStrategy[bytes]",
                        mode="eval",
                    ).body,
                    include_attributes=False,
                ),
            ),
        )
        changed_semantics = replace(
            semantics,
            annotations=tuple(annotations),
        )
        expected_error = "sealed source annotation semantics changed"
    changed_candidate = replace(
        candidate,
        function_semantics=changed_semantics,
    )
    public = vars(module)[path]
    source = vars(public)["__wrapped__"]

    with pytest.raises(MutationToolchainError, match=expected_error):
        mutation_toolchain._verify_source_declared_datetime_defaults(
            module,
            path=path,
            candidate=changed_candidate,
            public_value=public,
            bound_functions=(public, source),
            matched_function=source,
            policy=policy,
            import_sentinels={},
            attested_code_identities=attested,
        )


@pytest.mark.parametrize("attack", ("rebound", "same_object_code"))
def test_hypothesis_times_rejects_source_verifier_replacement_before_execution(
    attack: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "hypothesis.strategies._internal.datetime"
    module = import_module(module_name)
    public = vars(module)["times"]
    source = vars(public)["__wrapped__"]
    callbacks = {"count": 0}

    def hostile_verifier(*_args: object, **_kwargs: object) -> None:
        callbacks["count"] += 1

    def hostile_code(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("mutated temporal source verifier executed")

    _verify_selected_binding(
        module_name,
        "times",
        admitted_module_names=(
            module_name,
            "hypothesis.strategies._internal.utils",
        ),
    )
    with monkeypatch.context() as mutation:
        mutation.setattr(
            public,
            "__defaults__",
            (datetime.time.max, datetime.time.min),
        )
        mutation.setattr(
            source,
            "__defaults__",
            (datetime.time.max, datetime.time.min),
        )
        if attack == "rebound":
            mutation.setattr(
                mutation_toolchain,
                "_verify_source_declared_datetime_defaults",
                hostile_verifier,
            )
        else:
            verifier = mutation_toolchain._verify_source_declared_datetime_defaults
            mutation.setattr(verifier, "__code__", hostile_code.__code__)
        with pytest.raises(
            MutationToolchainError,
            match="loaded source verifier binding changed",
        ):
            _verify_selected_binding(
                module_name,
                "times",
                admitted_module_names=(
                    module_name,
                    "hypothesis.strategies._internal.utils",
                ),
            )
        assert callbacks == {"count": 0}

    _verify_selected_binding(
        module_name,
        "times",
        admitted_module_names=(
            module_name,
            "hypothesis.strategies._internal.utils",
        ),
    )


@pytest.mark.parametrize(
    "surface",
    (
        "datetimes_public_kwdefaults",
        "datetimes_source_kwdefaults",
        "times_public_kwdefaults",
        "times_source_kwdefaults",
        "sys_modules",
        "datetime_namespace",
        "misc_namespace",
        "module_spec",
        "function_namespace",
        "provider_global_capture",
        "provider_global_verifier",
    ),
)
def test_hypothesis_temporal_provider_rejects_hash_colliding_keys_without_callbacks(
    surface: str,
) -> None:
    callbacks = {"eq": 0, "hash": 0, "repr": 0}

    class HostileKey(str):
        def __eq__(self, other: object) -> bool:
            callbacks["eq"] += 1
            return str.__eq__(self, other)

        def __hash__(self) -> int:
            callbacks["hash"] += 1
            return str.__hash__(self)

        def __repr__(self) -> str:
            callbacks["repr"] += 1
            return "hostile-temporal-key"

    module_records = mutation_toolchain._EAGER_HYPOTHESIS_TEMPORAL_MODULE_RECORDS
    if surface == "datetimes_public_kwdefaults":
        mapping = mutation_toolchain._EAGER_HYPOTHESIS_DATETIMES_PUBLIC_KWDEFAULTS
        target = "timezones"
    elif surface == "datetimes_source_kwdefaults":
        mapping = mutation_toolchain._EAGER_HYPOTHESIS_DATETIMES_SOURCE_KWDEFAULTS
        target = "timezones"
    elif surface == "times_public_kwdefaults":
        mapping = mutation_toolchain._EAGER_HYPOTHESIS_TIMES_PUBLIC_KWDEFAULTS
        target = "timezones"
    elif surface == "times_source_kwdefaults":
        mapping = mutation_toolchain._EAGER_HYPOTHESIS_TIMES_SOURCE_KWDEFAULTS
        target = "timezones"
    elif surface == "sys_modules":
        mapping = sys.modules
        target = "hypothesis.strategies._internal.datetime"
    elif surface == "datetime_namespace":
        mapping = vars(mutation_toolchain._EAGER_HYPOTHESIS_DATETIME_MODULE)
        target = "none"
    elif surface == "misc_namespace":
        mapping = vars(mutation_toolchain._EAGER_HYPOTHESIS_MISC_MODULE)
        target = "none"
    elif surface == "module_spec":
        specification = module_records[0][5]
        mapping = vars(specification)
        target = "name"
    elif surface == "function_namespace":
        mapping = vars(mutation_toolchain._EAGER_HYPOTHESIS_NONE_PUBLIC)
        target = "__wrapped__"
    elif surface == "provider_global_capture":
        mapping = vars(mutation_toolchain)
        target = "_EAGER_HYPOTHESIS_TEMPORAL_CALLABLE_FINGERPRINTS"
    else:
        mapping = vars(mutation_toolchain)
        target = "_verify_exact_callable_fingerprint"

    assert type(mapping) is dict
    original_items = tuple(dict.items(mapping))
    assert sum(
        type(name) is str and str.__eq__(name, target)
        for name, _value in original_items
    ) == 1
    hostile_key = HostileKey(target)
    replacement_items = tuple(
        (
            hostile_key
            if type(name) is str and str.__eq__(name, target)
            else name,
            value,
        )
        for name, value in original_items
    )
    provider = mutation_toolchain._verify_eager_hypothesis_temporal_none_defaults
    caught: BaseException | None = None
    try:
        dict.clear(mapping)
        for name, value in replacement_items:
            dict.__setitem__(mapping, name, value)
        callbacks.update(eq=0, hash=0, repr=0)
        try:
            provider()
        except BaseException as exc:
            caught = exc
    finally:
        dict.clear(mapping)
        for name, value in original_items:
            dict.__setitem__(mapping, name, value)
    assert isinstance(caught, MutationToolchainError)
    assert "Hypothesis temporal none()" in str(caught)
    assert callbacks == {"eq": 0, "hash": 0, "repr": 0}
    mutation_toolchain._verify_eager_hypothesis_temporal_none_defaults()


def test_hypothesis_temporal_provider_rejects_hash_colliding_source_loader_key_without_callbacks() -> None:
    code = r'''
import os
from importlib.machinery import SourceFileLoader

from hypothesis import settings
from tests._pytest_plugins import determinism

settings.load_profile("moira-ci")
determinism.snapshot_hypothesis_policy()
from tests.support import mutation_toolchain as toolchain

callbacks = {"eq": 0, "hash": 0, "repr": 0}

class HostileKey(str):
    def __eq__(self, other):
        callbacks["eq"] += 1
        return str.__eq__(self, other)
    def __hash__(self):
        callbacks["hash"] += 1
        return str.__hash__(self)
    def __repr__(self):
        callbacks["repr"] += 1
        return "hostile-source-loader-key"

loader = next(
    record[8]
    for record in toolchain._EAGER_HYPOTHESIS_TEMPORAL_MODULE_RECORDS
    if type(record[8]) is SourceFileLoader
)
mapping = vars(loader)
target = "name"
original_items = tuple(dict.items(mapping))
assert sum(
    type(name) is str and str.__eq__(name, target)
    for name, _value in original_items
) == 1
hostile_key = HostileKey(target)
replacement_items = tuple(
    (
        hostile_key if type(name) is str and str.__eq__(name, target) else name,
        value,
    )
    for name, value in original_items
)
provider = toolchain._verify_eager_hypothesis_temporal_none_defaults
caught = None
try:
    dict.clear(mapping)
    for name, value in replacement_items:
        dict.__setitem__(mapping, name, value)
    callbacks.update(eq=0, hash=0, repr=0)
    try:
        provider()
    except BaseException as exc:
        caught = exc
finally:
    dict.clear(mapping)
    for name, value in original_items:
        dict.__setitem__(mapping, name, value)

assert type(caught) is toolchain.MutationToolchainError
assert "Hypothesis temporal none()" in str(caught)
assert callbacks == {"eq": 0, "hash": 0, "repr": 0}
provider()
'''
    environment = os.environ.copy()
    environment.pop("PYTEST_CURRENT_TEST", None)
    environment["MOIRA_NO_DOWNLOAD"] = "1"
    environment["MOIRA_TEST_ARTIFACTS"] = "0"
    completed = subprocess.run(
        [sys.executable, "-B", "-c", code],
        cwd=_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=_SUBPROCESS_TIMEOUT_SECONDS,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def _hypothesis_times_source_default_evidence() -> tuple[
    ModuleType,
    mutation_toolchain._SourceBindingCandidate,
    FunctionType,
    FunctionType,
    mutation_toolchain._SourceCodePolicy,
    frozenset[tuple[object, object, object, object]],
]:
    module_name = "hypothesis.strategies._internal.datetime"
    module, binding, attested, _admitted_paths, policy = (
        _selected_binding_evidence(
            module_name,
            "times",
            admitted_module_names=(
                module_name,
                "hypothesis.strategies._internal.utils",
            ),
        )
    )
    source_binding = mutation_toolchain._source_binding_for_manifest(
        policy,
        binding,
    )
    assert len(source_binding.candidates) == 1
    candidate = source_binding.candidates[0]
    public = vars(module)["times"]
    source = vars(public)["__wrapped__"]
    assert type(public) is FunctionType
    assert type(source) is FunctionType
    return module, candidate, public, source, policy, attested


@pytest.mark.parametrize("builtin_name", ("all", "type", "len", "zip"))
def test_hypothesis_times_source_verifier_rejects_hostile_builtins_without_callbacks(
    builtin_name: str,
) -> None:
    module, candidate, public, source, policy, attested = (
        _hypothesis_times_source_default_evidence()
    )
    verifier = mutation_toolchain._verify_source_declared_datetime_defaults
    original = vars(builtins)[builtin_name]
    callbacks = {"count": 0}
    caught: BaseException | None = None

    def hostile_builtin(*args: object, **kwargs: object) -> object:
        callbacks["count"] += 1
        if builtin_name == "all":
            return True
        return original(*args, **kwargs)

    try:
        setattr(builtins, builtin_name, hostile_builtin)
        try:
            verifier(
                module,
                path="times",
                candidate=candidate,
                public_value=public,
                bound_functions=(public, source),
                matched_function=source,
                policy=policy,
                import_sentinels={},
                attested_code_identities=attested,
            )
        except BaseException as exc:
            caught = exc
    finally:
        setattr(builtins, builtin_name, original)

    assert isinstance(caught, MutationToolchainError)
    assert str(caught) == "datetime source-default verifier dependency changed"
    assert callbacks == {"count": 0}
    verifier(
        module,
        path="times",
        candidate=candidate,
        public_value=public,
        bound_functions=(public, source),
        matched_function=source,
        policy=policy,
        import_sentinels={},
        attested_code_identities=attested,
    )


def test_hypothesis_times_forged_annotation_payload_cannot_hide_behind_hostile_all() -> None:
    module, candidate, public, source, policy, attested = (
        _hypothesis_times_source_default_evidence()
    )
    semantics = candidate.function_semantics
    assert semantics is not None
    annotations = list(semantics.annotations)
    annotation_name, annotation_kind, expression = annotations[0]
    annotations[0] = (
        annotation_name,
        annotation_kind,
        replace(expression, payload=("forged", "payload")),
    )
    changed_candidate = replace(
        candidate,
        function_semantics=replace(
            semantics,
            annotations=tuple(annotations),
        ),
    )
    verifier = mutation_toolchain._verify_source_declared_datetime_defaults
    with pytest.raises(
        MutationToolchainError,
        match="sealed source annotation semantics changed",
    ):
        verifier(
            module,
            path="times",
            candidate=changed_candidate,
            public_value=public,
            bound_functions=(public, source),
            matched_function=source,
            policy=policy,
            import_sentinels={},
            attested_code_identities=attested,
        )

    original_all = builtins.all
    callbacks = {"count": 0}
    caught: BaseException | None = None

    def hostile_all(_values: object) -> bool:
        callbacks["count"] += 1
        return True

    try:
        builtins.all = hostile_all
        try:
            verifier(
                module,
                path="times",
                candidate=changed_candidate,
                public_value=public,
                bound_functions=(public, source),
                matched_function=source,
                policy=policy,
                import_sentinels={},
                attested_code_identities=attested,
            )
        except BaseException as exc:
            caught = exc
    finally:
        builtins.all = original_all

    assert isinstance(caught, MutationToolchainError)
    assert str(caught) == "datetime source-default verifier dependency changed"
    assert callbacks == {"count": 0}
    verifier(
        module,
        path="times",
        candidate=candidate,
        public_value=public,
        bound_functions=(public, source),
        matched_function=source,
        policy=policy,
        import_sentinels={},
        attested_code_identities=attested,
    )


def test_hypothesis_temporal_provider_rejects_equal_defaults_clone_direct_and_runtime() -> None:
    provider = mutation_toolchain._verify_eager_hypothesis_temporal_none_defaults
    original_defaults = object.__getattribute__(provider, "__defaults__")
    assert type(original_defaults) is tuple
    cloned_defaults = tuple(list(original_defaults))
    assert cloned_defaults is not original_defaults
    default = mutation_toolchain._EAGER_HYPOTHESIS_DATETIMES_TIMEZONES_DEFAULT
    caught_direct: BaseException | None = None
    caught_runtime: BaseException | None = None
    caught_selected: BaseException | None = None
    module_name = "hypothesis.strategies._internal.datetime"

    try:
        provider.__defaults__ = cloned_defaults
        try:
            provider()
        except BaseException as exc:
            caught_direct = exc
        try:
            mutation_toolchain._runtime_value_shape(default)
        except BaseException as exc:
            caught_runtime = exc
        try:
            _verify_selected_binding(
                module_name,
                "times",
                admitted_module_names=(
                    module_name,
                    "hypothesis.strategies._internal.utils",
                ),
            )
        except BaseException as exc:
            caught_selected = exc
    finally:
        provider.__defaults__ = original_defaults

    assert isinstance(caught_direct, MutationToolchainError)
    assert str(caught_direct) == "Hypothesis temporal none() provider binding changed"
    assert isinstance(caught_runtime, MutationToolchainError)
    assert (
        str(caught_runtime)
        == "Hypothesis temporal none() runtime verifier binding changed"
    )
    assert isinstance(caught_selected, MutationToolchainError)
    assert (
        str(caught_selected)
        == "datetime source-default verifier dependency changed"
    )
    provider()
    mutation_toolchain._runtime_value_shape(default)
    _verify_selected_binding(
        module_name,
        "times",
        admitted_module_names=(
            module_name,
            "hypothesis.strategies._internal.utils",
        ),
    )


def test_hypothesis_times_selected_binding_rejects_equal_source_verifier_kwdefaults_clone() -> None:
    module_name = "hypothesis.strategies._internal.datetime"
    verifier = mutation_toolchain._verify_source_declared_datetime_defaults
    original_kwdefaults = object.__getattribute__(verifier, "__kwdefaults__")
    assert type(original_kwdefaults) is dict
    cloned_kwdefaults = dict(original_kwdefaults)
    assert cloned_kwdefaults is not original_kwdefaults
    caught: BaseException | None = None

    try:
        verifier.__kwdefaults__ = cloned_kwdefaults
        try:
            _verify_selected_binding(
                module_name,
                "times",
                admitted_module_names=(
                    module_name,
                    "hypothesis.strategies._internal.utils",
                ),
            )
        except BaseException as exc:
            caught = exc
    finally:
        verifier.__kwdefaults__ = original_kwdefaults

    assert isinstance(caught, MutationToolchainError)
    assert str(caught) == "loaded source verifier binding changed"
    _verify_selected_binding(
        module_name,
        "times",
        admitted_module_names=(
            module_name,
            "hypothesis.strategies._internal.utils",
        ),
    )


def test_hypothesis_times_selected_binding_rejects_hash_colliding_source_verifier_kwdefault_key_without_callbacks() -> None:
    module_name = "hypothesis.strategies._internal.datetime"
    verifier = mutation_toolchain._verify_source_declared_datetime_defaults
    kwdefaults = object.__getattribute__(verifier, "__kwdefaults__")
    assert type(kwdefaults) is dict
    original_items = tuple(dict.items(kwdefaults))
    target = "_provider_verifier"
    assert sum(
        type(name) is str and str.__eq__(name, target)
        for name, _value in original_items
    ) == 1
    callbacks = {"eq": 0, "hash": 0, "repr": 0}

    class HostileKey(str):
        def __eq__(self, other: object) -> bool:
            callbacks["eq"] += 1
            return str.__eq__(self, other)

        def __hash__(self) -> int:
            callbacks["hash"] += 1
            return str.__hash__(self)

        def __repr__(self) -> str:
            callbacks["repr"] += 1
            return "hostile-source-verifier-key"

    hostile_key = HostileKey(target)
    replacement_items = tuple(
        (
            hostile_key
            if type(name) is str and str.__eq__(name, target)
            else name,
            value,
        )
        for name, value in original_items
    )
    caught: BaseException | None = None
    try:
        dict.clear(kwdefaults)
        for name, value in replacement_items:
            dict.__setitem__(kwdefaults, name, value)
        callbacks.update(eq=0, hash=0, repr=0)
        try:
            _verify_selected_binding(
                module_name,
                "times",
                admitted_module_names=(
                    module_name,
                    "hypothesis.strategies._internal.utils",
                ),
            )
        except BaseException as exc:
            caught = exc
    finally:
        dict.clear(kwdefaults)
        for name, value in original_items:
            dict.__setitem__(kwdefaults, name, value)

    assert isinstance(caught, MutationToolchainError)
    assert str(caught) == "loaded source verifier binding changed"
    assert callbacks == {"eq": 0, "hash": 0, "repr": 0}
    _verify_selected_binding(
        module_name,
        "times",
        admitted_module_names=(
            module_name,
            "hypothesis.strategies._internal.utils",
        ),
    )


@pytest.mark.parametrize("attack", ("clone", "mutate", "rekey"))
def test_hypothesis_temporal_provider_rejects_callable_verifier_kwdefault_drift_before_execution(
    attack: str,
) -> None:
    provider = mutation_toolchain._verify_eager_hypothesis_temporal_none_defaults
    verifier = mutation_toolchain._verify_exact_callable_fingerprint
    verifier_code = object.__getattribute__(verifier, "__code__")
    kwdefaults = object.__getattribute__(verifier, "__kwdefaults__")
    assert type(kwdefaults) is dict
    original_items = tuple(dict.items(kwdefaults))
    target = "_builtin_type"
    assert sum(
        type(name) is str and str.__eq__(name, target)
        for name, _value in original_items
    ) == 1
    callbacks = {"eq": 0, "hash": 0, "repr": 0, "call": 0, "profile": 0}

    class HostileKey(str):
        def __eq__(self, other: object) -> bool:
            callbacks["eq"] += 1
            return str.__eq__(self, other)

        def __hash__(self) -> int:
            callbacks["hash"] += 1
            return str.__hash__(self)

        def __repr__(self) -> str:
            callbacks["repr"] += 1
            return "hostile-callable-verifier-key"

    def hostile_default(*_args: object, **_kwargs: object) -> object:
        callbacks["call"] += 1
        return object()

    def profiler(frame: object, event: str, _arg: object) -> None:
        if event == "call" and frame.f_code is verifier_code:
            callbacks["profile"] += 1

    previous_profile = sys.getprofile()
    caught: BaseException | None = None
    try:
        if attack == "clone":
            verifier.__kwdefaults__ = dict(original_items)
        elif attack == "mutate":
            dict.__setitem__(kwdefaults, target, hostile_default)
        else:
            hostile_key = HostileKey(target)
            replacement_items = tuple(
                (
                    hostile_key
                    if type(name) is str and str.__eq__(name, target)
                    else name,
                    value,
                )
                for name, value in original_items
            )
            dict.clear(kwdefaults)
            for name, value in replacement_items:
                dict.__setitem__(kwdefaults, name, value)
        callbacks.update(eq=0, hash=0, repr=0, call=0, profile=0)
        sys.setprofile(profiler)
        try:
            provider()
        except BaseException as exc:
            caught = exc
    finally:
        sys.setprofile(previous_profile)
        verifier.__kwdefaults__ = kwdefaults
        dict.clear(kwdefaults)
        for name, value in original_items:
            dict.__setitem__(kwdefaults, name, value)

    assert isinstance(caught, MutationToolchainError)
    assert str(caught) == "Hypothesis temporal none() verifier dependency changed"
    assert callbacks == {
        "eq": 0,
        "hash": 0,
        "repr": 0,
        "call": 0,
        "profile": 0,
    }
    provider()


def test_hypothesis_times_selected_binding_rejects_hash_colliding_expression_resolver_kwdefault_key_without_callbacks() -> None:
    module_name = "hypothesis.strategies._internal.datetime"
    resolver = mutation_toolchain._closed_source_expression_value
    kwdefaults = object.__getattribute__(resolver, "__kwdefaults__")
    assert type(kwdefaults) is dict
    original_items = tuple(dict.items(kwdefaults))
    target = "_attribute_reader"
    assert sum(
        type(name) is str and str.__eq__(name, target)
        for name, _value in original_items
    ) == 1
    callbacks = {"eq": 0, "hash": 0, "repr": 0}

    class HostileKey(str):
        def __eq__(self, other: object) -> bool:
            callbacks["eq"] += 1
            return str.__eq__(self, other)

        def __hash__(self) -> int:
            callbacks["hash"] += 1
            return str.__hash__(self)

        def __repr__(self) -> str:
            callbacks["repr"] += 1
            return "hostile-expression-resolver-key"

    hostile_key = HostileKey(target)
    replacement_items = tuple(
        (
            hostile_key
            if type(name) is str and str.__eq__(name, target)
            else name,
            value,
        )
        for name, value in original_items
    )
    caught: BaseException | None = None
    try:
        dict.clear(kwdefaults)
        for name, value in replacement_items:
            dict.__setitem__(kwdefaults, name, value)
        callbacks.update(eq=0, hash=0, repr=0)
        try:
            _verify_selected_binding(
                module_name,
                "times",
                admitted_module_names=(
                    module_name,
                    "hypothesis.strategies._internal.utils",
                ),
            )
        except BaseException as exc:
            caught = exc
    finally:
        dict.clear(kwdefaults)
        for name, value in original_items:
            dict.__setitem__(kwdefaults, name, value)

    assert isinstance(caught, MutationToolchainError)
    assert str(caught) == "sealed source conditional dispatcher changed"
    assert callbacks == {"eq": 0, "hash": 0, "repr": 0}
    _verify_selected_binding(
        module_name,
        "times",
        admitted_module_names=(
            module_name,
            "hypothesis.strategies._internal.utils",
        ),
    )


@pytest.mark.parametrize("caller", ("loaded_source_code", "pathlib_attestor"))
@pytest.mark.parametrize(
    "verifier_name",
    ("loaded_bindings", "callable_fingerprint"),
)
def test_loaded_source_callers_reject_hash_colliding_verifier_kwdefault_key_before_execution(
    caller: str,
    verifier_name: str,
    tmp_path: Path,
) -> None:
    loaded_bindings_verifier = mutation_toolchain._verify_loaded_bindings
    callable_verifier = mutation_toolchain._verify_exact_callable_fingerprint
    loaded_bindings_code = object.__getattribute__(
        loaded_bindings_verifier,
        "__code__",
    )
    callable_verifier_code = object.__getattribute__(
        callable_verifier,
        "__code__",
    )
    if verifier_name == "loaded_bindings":
        verifier = loaded_bindings_verifier
        target = "_inactive_source_reader"
    else:
        verifier = callable_verifier
        target = "_builtin_type"
    kwdefaults = object.__getattribute__(verifier, "__kwdefaults__")
    assert type(kwdefaults) is dict
    original_items = tuple(dict.items(kwdefaults))
    assert sum(
        type(name) is str and str.__eq__(name, target)
        for name, _value in original_items
    ) == 1
    runtime_sentinels = mutation_toolchain._RUNTIME_SOURCE_SENTINELS
    sentinel_items = tuple(dict.items(runtime_sentinels))
    callbacks = {
        "eq": 0,
        "hash": 0,
        "repr": 0,
        "loaded_bindings_profile": 0,
        "callable_verifier_profile": 0,
    }

    class HostileKey(str):
        def __eq__(self, other: object) -> bool:
            callbacks["eq"] += 1
            return str.__eq__(self, other)

        def __hash__(self) -> int:
            callbacks["hash"] += 1
            return str.__hash__(self)

        def __repr__(self) -> str:
            callbacks["repr"] += 1
            return "hostile-loaded-source-verifier-key"

    if caller == "loaded_source_code":
        source_path = tmp_path / "loaded_bindings_caller_probe.py"
        source = b"def probe(value):\n    return value\n"
        source_path.write_bytes(source)
        module = ModuleType("loaded_bindings_caller_probe")
        loader = SourceFileLoader(module.__name__, str(source_path))
        module.__file__ = str(source_path)
        module.__loader__ = loader
        module.__spec__ = spec_from_loader(module.__name__, loader)
        exec(
            compile(source, str(source_path), "exec", dont_inherit=True),
            vars(module),
        )
        expected_manifest = mutation_toolchain._source_code_manifest(
            source,
            source_path=source_path,
        )

        def invoke() -> object:
            return mutation_toolchain._verify_loaded_source_code(
                module,
                source=source,
                source_path=source_path,
                variant="raw",
                expected_manifest=expected_manifest,
            )

        expected_error = "loaded source verifier binding changed"
    else:
        attestor = (
            mutation_toolchain._build_eager_hypothesis_file_root_pathlib_source_attestor(
                mutation_toolchain._EAGER_HYPOTHESIS_FILE_ROOT_BINDING,
            )
        )

        def invoke() -> object:
            return attestor()

        expected_error = (
            "reviewed source closure pathlib exact callable verifier changed"
            if verifier_name == "callable_fingerprint"
            else "reviewed source closure pathlib loaded bindings verifier changed"
        )

    hostile_key = HostileKey(target)
    replacement_items = tuple(
        (
            hostile_key
            if type(name) is str and str.__eq__(name, target)
            else name,
            value,
        )
        for name, value in original_items
    )

    def profiler(frame: object, event: str, _arg: object) -> None:
        if event != "call":
            return
        if frame.f_code is loaded_bindings_code:
            callbacks["loaded_bindings_profile"] += 1
        if frame.f_code is callable_verifier_code:
            callbacks["callable_verifier_profile"] += 1

    previous_profile = sys.getprofile()
    caught: BaseException | None = None
    clean_result: object | None = None
    try:
        try:
            dict.clear(kwdefaults)
            for name, value in replacement_items:
                dict.__setitem__(kwdefaults, name, value)
            callbacks.update(
                eq=0,
                hash=0,
                repr=0,
                loaded_bindings_profile=0,
                callable_verifier_profile=0,
            )
            sys.setprofile(profiler)
            try:
                invoke()
            except BaseException as exc:
                caught = exc
        finally:
            sys.setprofile(previous_profile)
            dict.clear(kwdefaults)
            for name, value in original_items:
                dict.__setitem__(kwdefaults, name, value)
        clean_result = invoke()
    finally:
        sys.setprofile(previous_profile)
        dict.clear(kwdefaults)
        for name, value in original_items:
            dict.__setitem__(kwdefaults, name, value)
        dict.clear(runtime_sentinels)
        for name, value in sentinel_items:
            dict.__setitem__(runtime_sentinels, name, value)

    assert isinstance(caught, MutationToolchainError)
    assert str(caught) == expected_error
    expected_callable_verifier_profile = (
        1 if verifier_name == "loaded_bindings" else 0
    )
    assert callbacks == {
        "eq": 0,
        "hash": 0,
        "repr": 0,
        "loaded_bindings_profile": 0,
        "callable_verifier_profile": expected_callable_verifier_profile,
    }
    assert sys.getprofile() is previous_profile
    restored_items = tuple(dict.items(kwdefaults))
    assert len(restored_items) == len(original_items)
    assert all(
        current_name is expected_name and current_value is expected_value
        for (current_name, current_value), (expected_name, expected_value) in zip(
            restored_items,
            original_items,
            strict=True,
        )
    )
    restored_sentinels = tuple(dict.items(runtime_sentinels))
    assert len(restored_sentinels) == len(sentinel_items)
    assert all(
        current_name is expected_name and current_value is expected_value
        for (current_name, current_value), (expected_name, expected_value) in zip(
            restored_sentinels,
            sentinel_items,
            strict=True,
        )
    )
    if caller == "pathlib_attestor":
        assert clean_result == "sealed-pathlib-source-callable-inventory-v1"
    else:
        assert type(clean_result) is dict


def test_loaded_source_code_reseals_loaded_bindings_after_attested_identity_materialization(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "loaded_bindings_materialization_probe.py"
    source = b"def probe(value):\n    return value\n"
    source_path.write_bytes(source)
    module = ModuleType("loaded_bindings_materialization_probe")
    loader = SourceFileLoader(module.__name__, str(source_path))
    module.__file__ = str(source_path)
    module.__loader__ = loader
    module.__spec__ = spec_from_loader(module.__name__, loader)
    exec(
        compile(source, str(source_path), "exec", dont_inherit=True),
        vars(module),
    )
    expected_manifest = mutation_toolchain._source_code_manifest(
        source,
        source_path=source_path,
    )
    loaded_source_verifier = mutation_toolchain._verify_loaded_source_code
    loaded_source_code = object.__getattribute__(
        loaded_source_verifier,
        "__code__",
    )
    loaded_bindings_verifier = mutation_toolchain._verify_loaded_bindings
    loaded_bindings_code = object.__getattribute__(
        loaded_bindings_verifier,
        "__code__",
    )
    verifier_kwdefaults = object.__getattribute__(
        loaded_bindings_verifier,
        "__kwdefaults__",
    )
    assert type(verifier_kwdefaults) is dict
    verifier_items = tuple(dict.items(verifier_kwdefaults))
    builtins_mapping = object.__getattribute__(
        loaded_source_verifier,
        "__builtins__",
    )
    assert type(builtins_mapping) is dict
    builtins_items = tuple(dict.items(builtins_mapping))
    original_frozenset = dict.get(builtins_mapping, "frozenset")
    assert original_frozenset is frozenset
    runtime_sentinels = mutation_toolchain._RUNTIME_SOURCE_SENTINELS
    sentinel_items = tuple(dict.items(runtime_sentinels))
    callbacks = {
        "frozenset_calls": 0,
        "target_calls": 0,
        "mutation": 0,
        "loaded_bindings_profile": 0,
    }

    def hostile_frozenset(iterable: object = ()) -> frozenset[object]:
        callbacks["frozenset_calls"] += 1
        if sys._getframe(1).f_code is loaded_source_code:
            callbacks["target_calls"] += 1
            if callbacks["mutation"] == 0:
                callbacks["mutation"] += 1
                loaded_bindings_verifier.__kwdefaults__ = dict(verifier_items)
        return original_frozenset(iterable)

    def invoke() -> object:
        return loaded_source_verifier(
            module,
            source=source,
            source_path=source_path,
            variant="raw",
            expected_manifest=expected_manifest,
        )

    def profiler(frame: object, event: str, _arg: object) -> None:
        if event == "call" and frame.f_code is loaded_bindings_code:
            callbacks["loaded_bindings_profile"] += 1

    previous_profile = sys.getprofile()
    caught: BaseException | None = None
    clean_result: object | None = None
    try:
        dict.__setitem__(builtins_mapping, "frozenset", hostile_frozenset)
        callbacks.update(
            frozenset_calls=0,
            target_calls=0,
            mutation=0,
            loaded_bindings_profile=0,
        )
        sys.setprofile(profiler)
        try:
            invoke()
        except BaseException as exc:
            caught = exc
    finally:
        sys.setprofile(previous_profile)
        loaded_bindings_verifier.__kwdefaults__ = verifier_kwdefaults
        dict.clear(verifier_kwdefaults)
        for name, value in verifier_items:
            dict.__setitem__(verifier_kwdefaults, name, value)
        dict.__setitem__(builtins_mapping, "frozenset", original_frozenset)
        dict.clear(runtime_sentinels)
        for name, value in sentinel_items:
            dict.__setitem__(runtime_sentinels, name, value)

    assert isinstance(caught, MutationToolchainError)
    assert str(caught) == "loaded source verifier binding changed"
    assert callbacks["frozenset_calls"] >= 1
    assert callbacks["target_calls"] == 1
    assert callbacks["mutation"] == 1
    assert callbacks["loaded_bindings_profile"] == 0
    assert sys.getprofile() is previous_profile
    try:
        clean_result = invoke()
    finally:
        loaded_bindings_verifier.__kwdefaults__ = verifier_kwdefaults
        dict.clear(verifier_kwdefaults)
        for name, value in verifier_items:
            dict.__setitem__(verifier_kwdefaults, name, value)
        dict.__setitem__(builtins_mapping, "frozenset", original_frozenset)
        dict.clear(runtime_sentinels)
        for name, value in sentinel_items:
            dict.__setitem__(runtime_sentinels, name, value)
    assert type(clean_result) is dict
    assert (
        object.__getattribute__(loaded_bindings_verifier, "__kwdefaults__")
        is verifier_kwdefaults
    )
    restored_verifier_items = tuple(dict.items(verifier_kwdefaults))
    assert len(restored_verifier_items) == len(verifier_items)
    assert all(
        current_name is expected_name and current_value is expected_value
        for (current_name, current_value), (expected_name, expected_value) in zip(
            restored_verifier_items,
            verifier_items,
            strict=True,
        )
    )
    restored_builtins_items = tuple(dict.items(builtins_mapping))
    assert len(restored_builtins_items) == len(builtins_items)
    assert all(
        current_name is expected_name and current_value is expected_value
        for (current_name, current_value), (expected_name, expected_value) in zip(
            restored_builtins_items,
            builtins_items,
            strict=True,
        )
    )
    restored_sentinels = tuple(dict.items(runtime_sentinels))
    assert len(restored_sentinels) == len(sentinel_items)
    assert all(
        current_name is expected_name and current_value is expected_value
        for (current_name, current_value), (expected_name, expected_value) in zip(
            restored_sentinels,
            sentinel_items,
            strict=True,
        )
    )


@pytest.mark.parametrize("attack", ("clone", "mutation"))
@pytest.mark.parametrize(
    "caller",
    ("selected_source", "runtime_datetime", "runtime_date", "runtime_time"),
)
def test_datetime_provider_callers_reject_defaults_drift_before_execution(
    caller: str,
    attack: str,
) -> None:
    provider = mutation_toolchain._verify_eager_datetime_date_provider
    provider_code = object.__getattribute__(provider, "__code__")
    original_defaults = object.__getattribute__(provider, "__defaults__")
    assert type(original_defaults) is tuple
    callbacks = {
        "getattribute": 0,
        "eq": 0,
        "hash": 0,
        "repr": 0,
        "profile": 0,
    }

    class HostileDefault:
        def __getattribute__(self, name: str) -> object:
            callbacks["getattribute"] += 1
            return object.__getattribute__(self, name)

        def __eq__(self, other: object) -> bool:
            callbacks["eq"] += 1
            return True

        def __hash__(self) -> int:
            callbacks["hash"] += 1
            return 0

        def __repr__(self) -> str:
            callbacks["repr"] += 1
            return "hostile-datetime-provider-default"

    if attack == "clone":
        changed_defaults = tuple(list(original_defaults))
        assert changed_defaults is not original_defaults
    else:
        changed_items = list(original_defaults)
        changed_items[0] = HostileDefault()
        changed_defaults = tuple(changed_items)

    module_name = "hypothesis.strategies._internal.datetime"
    if caller == "selected_source":

        def invoke() -> object:
            _verify_selected_binding(
                module_name,
                "times",
                admitted_module_names=(
                    module_name,
                    "hypothesis.strategies._internal.utils",
                ),
            )
            return None

        expected_error = "datetime source-default verifier dependency changed"
    else:
        value = {
            "runtime_datetime": datetime.datetime.min,
            "runtime_date": datetime.date.min,
            "runtime_time": datetime.time.min,
        }[caller]

        def invoke() -> object:
            return mutation_toolchain._runtime_value_shape(value)

        expected_error = "datetime runtime-shape verifier binding changed"

    def profiler(frame: object, event: str, _arg: object) -> None:
        if event == "call" and frame.f_code is provider_code:
            callbacks["profile"] += 1

    previous_profile = sys.getprofile()
    caught: BaseException | None = None
    try:
        provider.__defaults__ = changed_defaults
        callbacks.update(
            getattribute=0,
            eq=0,
            hash=0,
            repr=0,
            profile=0,
        )
        sys.setprofile(profiler)
        try:
            invoke()
        except BaseException as exc:
            caught = exc
    finally:
        sys.setprofile(previous_profile)
        provider.__defaults__ = original_defaults

    assert isinstance(caught, MutationToolchainError)
    assert str(caught) == expected_error
    assert callbacks == {
        "getattribute": 0,
        "eq": 0,
        "hash": 0,
        "repr": 0,
        "profile": 0,
    }
    invoke()
    provider()


def test_active_source_binding_candidate_rejects_hash_colliding_expression_resolver_kwdefault_key_before_execution() -> None:
    module, policy, binding, _record = (
        _hypothesis_entropy_compat_flags_evidence()
    )
    guard = binding.candidates[0].guards[0]
    assert type(guard) is mutation_toolchain._SourceExpressionGuard
    expected_candidate = mutation_toolchain._active_source_binding_candidate(
        module,
        policy=policy,
        binding=binding,
    )
    resolver = mutation_toolchain._closed_source_expression_value
    resolver_code = object.__getattribute__(resolver, "__code__")
    kwdefaults = object.__getattribute__(resolver, "__kwdefaults__")
    assert type(kwdefaults) is dict
    original_items = tuple(dict.items(kwdefaults))
    target = "_attribute_reader"
    assert sum(
        type(name) is str and str.__eq__(name, target)
        for name, _value in original_items
    ) == 1
    callbacks = {"eq": 0, "hash": 0, "repr": 0, "profile": 0}

    class HostileKey(str):
        def __eq__(self, other: object) -> bool:
            callbacks["eq"] += 1
            return str.__eq__(self, other)

        def __hash__(self) -> int:
            callbacks["hash"] += 1
            return str.__hash__(self)

        def __repr__(self) -> str:
            callbacks["repr"] += 1
            return "hostile-active-candidate-resolver-key"

    hostile_key = HostileKey(target)
    replacement_items = tuple(
        (
            hostile_key
            if type(name) is str and str.__eq__(name, target)
            else name,
            value,
        )
        for name, value in original_items
    )

    def profiler(frame: object, event: str, _arg: object) -> None:
        if event == "call" and frame.f_code is resolver_code:
            callbacks["profile"] += 1

    previous_profile = sys.getprofile()
    caught: BaseException | None = None
    try:
        dict.clear(kwdefaults)
        for name, value in replacement_items:
            dict.__setitem__(kwdefaults, name, value)
        callbacks.update(eq=0, hash=0, repr=0, profile=0)
        sys.setprofile(profiler)
        try:
            mutation_toolchain._active_source_binding_candidate(
                module,
                policy=policy,
                binding=binding,
            )
        except BaseException as exc:
            caught = exc
    finally:
        sys.setprofile(previous_profile)
        dict.clear(kwdefaults)
        for name, value in original_items:
            dict.__setitem__(kwdefaults, name, value)

    assert isinstance(caught, MutationToolchainError)
    assert str(caught) == "sealed source conditional dispatcher changed"
    assert callbacks == {"eq": 0, "hash": 0, "repr": 0, "profile": 0}
    assert sys.getprofile() is previous_profile
    restored_items = tuple(dict.items(kwdefaults))
    assert len(restored_items) == len(original_items)
    assert all(
        current_name is expected_name and current_value is expected_value
        for (current_name, current_value), (expected_name, expected_value) in zip(
            restored_items,
            original_items,
            strict=True,
        )
    )
    assert (
        mutation_toolchain._active_source_binding_candidate(
            module,
            policy=policy,
            binding=binding,
        )
        is expected_candidate
    )


def test_active_source_binding_candidate_reseals_expression_resolver_after_module_name_lookup() -> None:
    module, policy, binding, _record = (
        _hypothesis_entropy_compat_flags_evidence()
    )
    guard = binding.candidates[0].guards[0]
    assert type(guard) is mutation_toolchain._SourceExpressionGuard
    expected_candidate = mutation_toolchain._active_source_binding_candidate(
        module,
        policy=policy,
        binding=binding,
    )
    resolver = mutation_toolchain._closed_source_expression_value
    resolver_code = object.__getattribute__(resolver, "__code__")
    resolver_kwdefaults = object.__getattribute__(resolver, "__kwdefaults__")
    assert type(resolver_kwdefaults) is dict
    resolver_items = tuple(dict.items(resolver_kwdefaults))
    module_namespace = vars(module)
    module_items = tuple(dict.items(module_namespace))
    target = "__name__"
    assert sum(
        type(name) is str and str.__eq__(name, target)
        for name, _value in module_items
    ) == 1
    callbacks = {
        "key_eq": 0,
        "key_hash": 0,
        "key_repr": 0,
        "mutation": 0,
        "resolver_profile": 0,
    }

    class HostileModuleNameKey(str):
        def __eq__(self, other: object) -> bool:
            callbacks["key_eq"] += 1
            if callbacks["mutation"] == 0:
                callbacks["mutation"] += 1
                resolver.__kwdefaults__ = dict(resolver_items)
            return str.__eq__(self, other)

        def __hash__(self) -> int:
            callbacks["key_hash"] += 1
            return str.__hash__(self)

        def __repr__(self) -> str:
            callbacks["key_repr"] += 1
            return "hostile-module-name-key"

    hostile_key = HostileModuleNameKey(target)
    replacement_items = tuple(
        (
            hostile_key
            if type(name) is str and str.__eq__(name, target)
            else name,
            value,
        )
        for name, value in module_items
    )

    def profiler(frame: object, event: str, _arg: object) -> None:
        if event == "call" and frame.f_code is resolver_code:
            callbacks["resolver_profile"] += 1

    previous_profile = sys.getprofile()
    caught: BaseException | None = None
    try:
        dict.clear(module_namespace)
        for name, value in replacement_items:
            dict.__setitem__(module_namespace, name, value)
        callbacks.update(
            key_eq=0,
            key_hash=0,
            key_repr=0,
            mutation=0,
            resolver_profile=0,
        )
        sys.setprofile(profiler)
        try:
            mutation_toolchain._active_source_binding_candidate(
                module,
                policy=policy,
                binding=binding,
            )
        except BaseException as exc:
            caught = exc
    finally:
        sys.setprofile(previous_profile)
        resolver.__kwdefaults__ = resolver_kwdefaults
        dict.clear(resolver_kwdefaults)
        for name, value in resolver_items:
            dict.__setitem__(resolver_kwdefaults, name, value)
        dict.clear(module_namespace)
        for name, value in module_items:
            dict.__setitem__(module_namespace, name, value)

    assert isinstance(caught, MutationToolchainError)
    assert str(caught) == (
        "sealed source conditional guard failed: "
        "hypothesis.internal.entropy._get_platform_base_refcount: "
        "sealed source conditional dispatcher changed"
    )
    assert callbacks == {
        "key_eq": 1,
        "key_hash": 0,
        "key_repr": 0,
        "mutation": 1,
        "resolver_profile": 0,
    }
    assert sys.getprofile() is previous_profile
    assert object.__getattribute__(resolver, "__kwdefaults__") is resolver_kwdefaults
    restored_resolver_items = tuple(dict.items(resolver_kwdefaults))
    assert len(restored_resolver_items) == len(resolver_items)
    assert all(
        current_name is expected_name and current_value is expected_value
        for (current_name, current_value), (expected_name, expected_value) in zip(
            restored_resolver_items,
            resolver_items,
            strict=True,
        )
    )
    restored_module_items = tuple(dict.items(module_namespace))
    assert len(restored_module_items) == len(module_items)
    assert all(
        current_name is expected_name and current_value is expected_value
        for (current_name, current_value), (expected_name, expected_value) in zip(
            restored_module_items,
            module_items,
            strict=True,
        )
    )
    assert (
        mutation_toolchain._active_source_binding_candidate(
            module,
            policy=policy,
            binding=binding,
        )
        is expected_candidate
    )


def test_closed_source_expression_resolver_reseals_recursive_edge_after_hasattr_namespace_lookup() -> None:
    module = import_module("typing_extensions")
    policy = _loaded_source_policy(module)
    bindings = tuple(
        binding
        for binding in policy.bindings
        if binding.path == ("disjoint_base",)
    )
    assert len(bindings) == 1
    guards = tuple(
        guard
        for candidate in bindings[0].candidates
        for guard in candidate.guards
        if (
            type(guard) is mutation_toolchain._SourceExpressionGuard
            and guard.expression.kind == "hasattr"
        )
    )
    assert len(guards) == 1
    expression = guards[0].expression
    resolver = mutation_toolchain._closed_source_expression_value
    resolver_code = object.__getattribute__(resolver, "__code__")
    resolver_defaults = object.__getattribute__(resolver, "__defaults__")
    resolver_kwdefaults = object.__getattribute__(resolver, "__kwdefaults__")
    resolver_globals = object.__getattribute__(resolver, "__globals__")
    resolver_builtins = object.__getattribute__(resolver, "__builtins__")
    resolver_closure = object.__getattribute__(resolver, "__closure__")
    assert type(resolver_kwdefaults) is dict
    assert resolver_globals is vars(mutation_toolchain)
    resolver_items = tuple(dict.items(resolver_kwdefaults))
    toolchain_items = tuple(dict.items(resolver_globals))
    resolver_global_items = tuple(
        (index, name, value)
        for index, (name, value) in enumerate(toolchain_items)
        if (
            type(name) is str
            and str.__eq__(name, "_closed_source_expression_value")
        )
    )
    assert len(resolver_global_items) == 1
    _resolver_global_index, resolver_global_key, resolver_global_value = (
        resolver_global_items[0]
    )
    assert resolver_global_value is resolver
    module_namespace = vars(module)
    module_items = tuple(dict.items(module_namespace))
    target = "hasattr"
    assert sum(
        type(name) is str and str.__eq__(name, target)
        for name, _value in module_items
    ) == 0
    clean_sentinels: dict[str, tuple[object, str | None]] = {}
    expected_result = resolver(
        module,
        policy=policy,
        expression=expression,
        import_sentinels=clean_sentinels,
    )
    assert expected_result is mutation_toolchain._SOURCE_EXPRESSION_UNRESOLVED
    callbacks = {
        "key_eq": 0,
        "key_hash": 0,
        "key_repr": 0,
        "mutation": 0,
        "resolver_profile": 0,
        "forged_profile": 0,
        "forged_call": 0,
    }

    def forged_resolver(*_args: object, **_kwargs: object) -> object:
        callbacks["forged_call"] += 1
        return mutation_toolchain._SOURCE_EXPRESSION_UNRESOLVED

    forged_code = object.__getattribute__(forged_resolver, "__code__")

    class HostileHasattrKey(str):
        def __eq__(self, _other: object) -> bool:
            callbacks["key_eq"] += 1
            if callbacks["mutation"] == 0:
                callbacks["mutation"] += 1
                resolver.__kwdefaults__ = dict(resolver_items)
                dict.__setitem__(
                    resolver_globals,
                    resolver_global_key,
                    forged_resolver,
                )
            return False

        def __hash__(self) -> int:
            callbacks["key_hash"] += 1
            return str.__hash__(self)

        def __repr__(self) -> str:
            callbacks["key_repr"] += 1
            return "hostile-hasattr-key"

    hostile_key = HostileHasattrKey(target)

    def profiler(frame: object, event: str, _arg: object) -> None:
        if event != "call":
            return
        if frame.f_code is resolver_code:
            callbacks["resolver_profile"] += 1
        if frame.f_code is forged_code:
            callbacks["forged_profile"] += 1

    previous_profile = sys.getprofile()
    caught: BaseException | None = None
    attack_sentinels: dict[str, tuple[object, str | None]] = {}
    try:
        dict.__setitem__(module_namespace, hostile_key, object())
        callbacks.update(
            key_eq=0,
            key_hash=0,
            key_repr=0,
            mutation=0,
            resolver_profile=0,
            forged_profile=0,
            forged_call=0,
        )
        sys.setprofile(profiler)
        try:
            resolver(
                module,
                policy=policy,
                expression=expression,
                import_sentinels=attack_sentinels,
            )
        except BaseException as exc:
            caught = exc
    finally:
        sys.setprofile(previous_profile)
        dict.__setitem__(
            resolver_globals,
            resolver_global_key,
            resolver_global_value,
        )
        resolver.__kwdefaults__ = resolver_kwdefaults
        dict.clear(resolver_kwdefaults)
        for name, value in resolver_items:
            dict.__setitem__(resolver_kwdefaults, name, value)
        dict.clear(module_namespace)
        for name, value in module_items:
            dict.__setitem__(module_namespace, name, value)

    assert isinstance(caught, MutationToolchainError)
    assert str(caught) == "source guard recursive resolver changed"
    assert callbacks == {
        "key_eq": 1,
        "key_hash": 0,
        "key_repr": 0,
        "mutation": 1,
        "resolver_profile": 1,
        "forged_profile": 0,
        "forged_call": 0,
    }
    assert attack_sentinels == {}
    assert sys.getprofile() is previous_profile
    assert object.__getattribute__(resolver, "__code__") is resolver_code
    assert object.__getattribute__(resolver, "__defaults__") is resolver_defaults
    assert (
        object.__getattribute__(resolver, "__kwdefaults__")
        is resolver_kwdefaults
    )
    assert object.__getattribute__(resolver, "__globals__") is resolver_globals
    assert object.__getattribute__(resolver, "__builtins__") is resolver_builtins
    assert object.__getattribute__(resolver, "__closure__") is resolver_closure
    restored_resolver_items = tuple(dict.items(resolver_kwdefaults))
    assert len(restored_resolver_items) == len(resolver_items)
    assert all(
        current_name is expected_name and current_value is expected_value
        for (current_name, current_value), (expected_name, expected_value) in zip(
            restored_resolver_items,
            resolver_items,
            strict=True,
        )
    )
    restored_toolchain_items = tuple(dict.items(resolver_globals))
    assert len(restored_toolchain_items) == len(toolchain_items)
    assert all(
        current_name is expected_name and current_value is expected_value
        for (current_name, current_value), (expected_name, expected_value) in zip(
            restored_toolchain_items,
            toolchain_items,
            strict=True,
        )
    )
    restored_module_items = tuple(dict.items(module_namespace))
    assert len(restored_module_items) == len(module_items)
    assert all(
        current_name is expected_name and current_value is expected_value
        for (current_name, current_value), (expected_name, expected_value) in zip(
            restored_module_items,
            module_items,
            strict=True,
        )
    )
    clean_result = resolver(
        module,
        policy=policy,
        expression=expression,
        import_sentinels={},
    )
    assert clean_result is expected_result


def test_loaded_binding_rejects_hash_colliding_active_candidate_kwdefault_key_before_execution() -> None:
    module_name = "hypothesis.strategies._internal.datetime"
    admitted_module_names = (
        module_name,
        "hypothesis.strategies._internal.utils",
    )
    _verify_selected_binding(
        module_name,
        "times",
        admitted_module_names=admitted_module_names,
    )
    active_candidate = mutation_toolchain._active_source_binding_candidate
    active_candidate_code = object.__getattribute__(
        active_candidate,
        "__code__",
    )
    kwdefaults = object.__getattribute__(active_candidate, "__kwdefaults__")
    assert type(kwdefaults) is dict
    original_items = tuple(dict.items(kwdefaults))
    target = "_field_reader"
    assert sum(
        type(name) is str and str.__eq__(name, target)
        for name, _value in original_items
    ) == 1
    runtime_sentinels = mutation_toolchain._RUNTIME_SOURCE_SENTINELS
    sentinel_items = tuple(dict.items(runtime_sentinels))
    callbacks = {"eq": 0, "hash": 0, "repr": 0, "profile": 0}

    class HostileKey(str):
        def __eq__(self, other: object) -> bool:
            callbacks["eq"] += 1
            return str.__eq__(self, other)

        def __hash__(self) -> int:
            callbacks["hash"] += 1
            return str.__hash__(self)

        def __repr__(self) -> str:
            callbacks["repr"] += 1
            return "hostile-active-candidate-key"

    hostile_key = HostileKey(target)
    replacement_items = tuple(
        (
            hostile_key
            if type(name) is str and str.__eq__(name, target)
            else name,
            value,
        )
        for name, value in original_items
    )

    def profiler(frame: object, event: str, _arg: object) -> None:
        if event == "call" and frame.f_code is active_candidate_code:
            callbacks["profile"] += 1

    def invoke() -> None:
        _verify_selected_binding(
            module_name,
            "times",
            admitted_module_names=admitted_module_names,
        )

    previous_profile = sys.getprofile()
    caught: BaseException | None = None
    try:
        dict.clear(kwdefaults)
        for name, value in replacement_items:
            dict.__setitem__(kwdefaults, name, value)
        callbacks.update(eq=0, hash=0, repr=0, profile=0)
        sys.setprofile(profiler)
        try:
            invoke()
        except BaseException as exc:
            caught = exc
    finally:
        sys.setprofile(previous_profile)
        dict.clear(kwdefaults)
        for name, value in original_items:
            dict.__setitem__(kwdefaults, name, value)
        dict.clear(runtime_sentinels)
        for name, value in sentinel_items:
            dict.__setitem__(runtime_sentinels, name, value)

    assert isinstance(caught, MutationToolchainError)
    assert str(caught) == "loaded source verifier binding changed"
    assert callbacks == {"eq": 0, "hash": 0, "repr": 0, "profile": 0}
    assert sys.getprofile() is previous_profile
    try:
        invoke()
    finally:
        dict.clear(kwdefaults)
        for name, value in original_items:
            dict.__setitem__(kwdefaults, name, value)
        dict.clear(runtime_sentinels)
        for name, value in sentinel_items:
            dict.__setitem__(runtime_sentinels, name, value)
    restored_items = tuple(dict.items(kwdefaults))
    assert len(restored_items) == len(original_items)
    assert all(
        current_name is expected_name and current_value is expected_value
        for (current_name, current_value), (expected_name, expected_value) in zip(
            restored_items,
            original_items,
            strict=True,
        )
    )
    restored_sentinels = tuple(dict.items(runtime_sentinels))
    assert len(restored_sentinels) == len(sentinel_items)
    assert all(
        current_name is expected_name and current_value is expected_value
        for (current_name, current_value), (expected_name, expected_value) in zip(
            restored_sentinels,
            sentinel_items,
            strict=True,
        )
    )


def test_loaded_binding_reseals_active_candidate_after_binding_metadata_lookup() -> None:
    module_name = "hypothesis.strategies._internal.datetime"
    admitted_module_names = (
        module_name,
        "hypothesis.strategies._internal.utils",
    )
    module, binding, attested, admitted_paths, policy = (
        _selected_binding_evidence(
            module_name,
            "times",
            admitted_module_names=admitted_module_names,
        )
    )
    active_candidate = mutation_toolchain._active_source_binding_candidate
    active_candidate_code = object.__getattribute__(
        active_candidate,
        "__code__",
    )
    active_candidate_kwdefaults = object.__getattribute__(
        active_candidate,
        "__kwdefaults__",
    )
    assert type(active_candidate_kwdefaults) is dict
    active_candidate_items = tuple(dict.items(active_candidate_kwdefaults))
    binding_items = tuple(dict.items(binding))
    target = "must_be_absent"
    assert sum(
        type(name) is str and str.__eq__(name, target)
        for name, _value in binding_items
    ) == 1
    runtime_sentinels = mutation_toolchain._RUNTIME_SOURCE_SENTINELS
    sentinel_items = tuple(dict.items(runtime_sentinels))
    callbacks = {
        "key_eq": 0,
        "key_hash": 0,
        "key_repr": 0,
        "mutation": 0,
        "active_candidate_profile": 0,
    }

    class HostileBindingKey(str):
        def __eq__(self, other: object) -> bool:
            callbacks["key_eq"] += 1
            if callbacks["mutation"] == 0:
                callbacks["mutation"] += 1
                active_candidate.__kwdefaults__ = dict(active_candidate_items)
            return str.__eq__(self, other)

        def __hash__(self) -> int:
            callbacks["key_hash"] += 1
            return str.__hash__(self)

        def __repr__(self) -> str:
            callbacks["key_repr"] += 1
            return "hostile-binding-absence-key"

    hostile_key = HostileBindingKey(target)
    replacement_items = tuple(
        (
            hostile_key
            if type(name) is str and str.__eq__(name, target)
            else name,
            value,
        )
        for name, value in binding_items
    )

    def invoke() -> None:
        mutation_toolchain._verify_loaded_bindings(
            module,
            bindings=[binding],
            attested_code_identities=attested,
            admitted_source_paths=admitted_paths,
            admitted_class_ids=frozenset(),
            policy=policy,
        )

    invoke()

    def profiler(frame: object, event: str, _arg: object) -> None:
        if event == "call" and frame.f_code is active_candidate_code:
            callbacks["active_candidate_profile"] += 1

    previous_profile = sys.getprofile()
    caught: BaseException | None = None
    try:
        dict.clear(binding)
        for name, value in replacement_items:
            dict.__setitem__(binding, name, value)
        callbacks.update(
            key_eq=0,
            key_hash=0,
            key_repr=0,
            mutation=0,
            active_candidate_profile=0,
        )
        sys.setprofile(profiler)
        try:
            invoke()
        except BaseException as exc:
            caught = exc
    finally:
        sys.setprofile(previous_profile)
        active_candidate.__kwdefaults__ = active_candidate_kwdefaults
        dict.clear(active_candidate_kwdefaults)
        for name, value in active_candidate_items:
            dict.__setitem__(active_candidate_kwdefaults, name, value)
        dict.clear(binding)
        for name, value in binding_items:
            dict.__setitem__(binding, name, value)
        dict.clear(runtime_sentinels)
        for name, value in sentinel_items:
            dict.__setitem__(runtime_sentinels, name, value)

    assert isinstance(caught, MutationToolchainError)
    assert str(caught) == "loaded source verifier binding changed"
    assert callbacks == {
        "key_eq": 1,
        "key_hash": 0,
        "key_repr": 0,
        "mutation": 1,
        "active_candidate_profile": 0,
    }
    assert sys.getprofile() is previous_profile
    try:
        invoke()
    finally:
        active_candidate.__kwdefaults__ = active_candidate_kwdefaults
        dict.clear(active_candidate_kwdefaults)
        for name, value in active_candidate_items:
            dict.__setitem__(active_candidate_kwdefaults, name, value)
        dict.clear(binding)
        for name, value in binding_items:
            dict.__setitem__(binding, name, value)
        dict.clear(runtime_sentinels)
        for name, value in sentinel_items:
            dict.__setitem__(runtime_sentinels, name, value)
    assert (
        object.__getattribute__(active_candidate, "__kwdefaults__")
        is active_candidate_kwdefaults
    )
    restored_active_candidate_items = tuple(
        dict.items(active_candidate_kwdefaults)
    )
    assert len(restored_active_candidate_items) == len(active_candidate_items)
    assert all(
        current_name is expected_name and current_value is expected_value
        for (current_name, current_value), (expected_name, expected_value) in zip(
            restored_active_candidate_items,
            active_candidate_items,
            strict=True,
        )
    )
    restored_binding_items = tuple(dict.items(binding))
    assert len(restored_binding_items) == len(binding_items)
    assert all(
        current_name is expected_name and current_value is expected_value
        for (current_name, current_value), (expected_name, expected_value) in zip(
            restored_binding_items,
            binding_items,
            strict=True,
        )
    )
    restored_sentinels = tuple(dict.items(runtime_sentinels))
    assert len(restored_sentinels) == len(sentinel_items)
    assert all(
        current_name is expected_name and current_value is expected_value
        for (current_name, current_value), (expected_name, expected_value) in zip(
            restored_sentinels,
            sentinel_items,
            strict=True,
        )
    )


@pytest.mark.parametrize(
    "attack",
    (
        "record_subclass",
        "payload_element_subclass",
        "payload_container_subclass",
    ),
)
def test_hypothesis_times_source_verifier_preserves_exact_record_and_payload_types(
    attack: str,
) -> None:
    module, candidate, public, source, policy, attested = (
        _hypothesis_times_source_default_evidence()
    )
    callbacks = {
        "getattribute": 0,
        "eq": 0,
        "hash": 0,
        "repr": 0,
        "iter": 0,
        "len": 0,
        "getitem": 0,
    }

    class HostileCandidate(mutation_toolchain._SourceBindingCandidate):
        def __getattribute__(self, name: str) -> object:
            callbacks["getattribute"] += 1
            return object.__getattribute__(self, name)

        def __eq__(self, other: object) -> bool:
            callbacks["eq"] += 1
            return True

        def __hash__(self) -> int:
            callbacks["hash"] += 1
            return 0

        def __repr__(self) -> str:
            callbacks["repr"] += 1
            return "hostile-source-candidate"

    class HostileString(str):
        def __eq__(self, other: object) -> bool:
            callbacks["eq"] += 1
            return True

        def __hash__(self) -> int:
            callbacks["hash"] += 1
            return str.__hash__(self)

        def __repr__(self) -> str:
            callbacks["repr"] += 1
            return "hostile-source-payload"

    class HostileTuple(tuple):
        def __iter__(self) -> object:
            callbacks["iter"] += 1
            return tuple.__iter__(self)

        def __len__(self) -> int:
            callbacks["len"] += 1
            return tuple.__len__(self)

        def __getitem__(self, index: object) -> object:
            callbacks["getitem"] += 1
            return tuple.__getitem__(self, index)

        def __eq__(self, other: object) -> bool:
            callbacks["eq"] += 1
            return True

        def __hash__(self) -> int:
            callbacks["hash"] += 1
            return tuple.__hash__(self)

        def __repr__(self) -> str:
            callbacks["repr"] += 1
            return "hostile-source-payload"

    if attack == "record_subclass":
        changed_candidate: object = HostileCandidate(
            qualname=candidate.qualname,
            first_line=candidate.first_line,
            definition_line=candidate.definition_line,
            decorators=candidate.decorators,
            function_semantics=candidate.function_semantics,
            guards=candidate.guards,
            guards_complete=candidate.guards_complete,
        )
        expected_error = "source policy record type changed"
    else:
        semantics = candidate.function_semantics
        assert semantics is not None
        annotations = list(semantics.annotations)
        annotation_name, annotation_kind, expression = annotations[0]
        payload: object
        if attack == "payload_element_subclass":
            payload = (HostileString("dt"), "time")
        else:
            payload = HostileTuple(("dt", "time"))
        annotations[0] = (
            annotation_name,
            annotation_kind,
            replace(expression, payload=payload),
        )
        changed_candidate = replace(
            candidate,
            function_semantics=replace(
                semantics,
                annotations=tuple(annotations),
            ),
        )
        expected_error = "sealed source annotation semantics changed"

    callbacks.update(
        getattribute=0,
        eq=0,
        hash=0,
        repr=0,
        iter=0,
        len=0,
        getitem=0,
    )
    caught: BaseException | None = None
    try:
        mutation_toolchain._verify_source_declared_datetime_defaults(
            module,
            path="times",
            candidate=changed_candidate,
            public_value=public,
            bound_functions=(public, source),
            matched_function=source,
            policy=policy,
            import_sentinels={},
            attested_code_identities=attested,
        )
    except BaseException as exc:
        caught = exc

    assert isinstance(caught, MutationToolchainError)
    assert expected_error in str(caught)
    assert callbacks == {
        "getattribute": 0,
        "eq": 0,
        "hash": 0,
        "repr": 0,
        "iter": 0,
        "len": 0,
        "getitem": 0,
    }
    mutation_toolchain._verify_source_declared_datetime_defaults(
        module,
        path="times",
        candidate=candidate,
        public_value=public,
        bound_functions=(public, source),
        matched_function=source,
        policy=policy,
        import_sentinels={},
        attested_code_identities=attested,
    )


def test_import_then_edit_rejects_stale_loaded_callable(tmp_path: Path) -> None:
    source_path = tmp_path / "stale_probe.py"
    source_path.write_text("def probe():\n    return 41\n", encoding="utf-8")
    module = ModuleType("stale_probe")
    module.__file__ = str(source_path)
    module.__spec__ = spec_from_loader(
        "stale_probe",
        SourceFileLoader("stale_probe", str(source_path)),
    )
    exec(
        compile(
            source_path.read_bytes(),
            str(source_path),
            "exec",
            dont_inherit=True,
            optimize=sys.flags.optimize,
        ),
        vars(module),
    )

    source_path.write_text("def probe():\n    return 42\n", encoding="utf-8")
    sealed_source = source_path.read_bytes()
    with pytest.raises(MutationToolchainError, match="code objects differ"):
        mutation_toolchain._verify_loaded_source_code(
            module,
            source=sealed_source,
            source_path=source_path,
            variant="raw",
            expected_manifest=mutation_toolchain._source_code_manifest(
                sealed_source,
                source_path=source_path,
            ),
        )


def test_exact_assertion_rewrite_variant_matches_loaded_code(tmp_path: Path) -> None:
    source_path = tmp_path / "rewritten_probe.py"
    source_path.write_text(
        "def probe(value):\n"
        "    assert value\n"
        "    return value\n",
        encoding="utf-8",
    )
    rewrite_module = sys.modules["_pytest.assertion.rewrite"]
    rewrite_loader_type = rewrite_module.AssertionRewritingHook
    rewrite_loader = next(
        module.__spec__.loader
        for module in sys.modules.values()
        if isinstance(module, ModuleType)
        and getattr(module, "__spec__", None) is not None
        and type(module.__spec__.loader) is rewrite_loader_type
    )
    variant = mutation_toolchain._source_loader_variant(
        rewrite_loader,
        module_name="rewritten_probe",
        rewrite_module_is_attested=True,
    )
    assertion_pass_hook = variant == "pytest_rewrite_enabled"
    source = source_path.read_bytes()
    code, _policy = mutation_toolchain._compile_sealed_source(
        source,
        source_path=source_path,
        assertion_pass_hook=assertion_pass_hook,
    )
    module = ModuleType("rewritten_probe")
    module.__file__ = str(source_path)
    module.__spec__ = ModuleSpec(
        "rewritten_probe",
        rewrite_loader,
        origin=str(source_path),
    )
    exec(code, vars(module))
    mutation_toolchain._verify_loaded_source_code(
        module,
        source=source,
        source_path=source_path,
        variant=variant,
        expected_manifest=mutation_toolchain._source_code_manifest(
            source,
            source_path=source_path,
        ),
    )


def test_captured_unscoped_prefix_module_fails_but_scoped_alias_passes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, prefix, site_packages = _fake_toolchain(tmp_path)
    scope = mutation_toolchain._DistributionScope(
        import_paths=("pytest",),
        source_modules=(("pytest", "pytest/__init__.py"),),
    )
    package_path = site_packages / "pytest" / "__init__.py"
    package = ModuleType("pytest")
    package.__file__ = str(package_path)
    package.__spec__ = spec_from_loader(
        "pytest",
        SourceFileLoader("pytest", str(package_path)),
    )
    exec(compile(package_path.read_bytes(), str(package_path), "exec"), vars(package))
    monkeypatch.setitem(sys.modules, "sealed_pytest_alias", package)
    monkeypatch.setattr(
        mutation_toolchain,
        "_MODULE_NAMES_BEFORE_TOOLCHAIN_IMPORT",
        frozenset({"sealed_pytest_alias"}),
    )
    mutation_toolchain._build_test_toolchain_identity(
        prefix=prefix,
        search_paths=(site_packages,),
        roots=("pytest",),
        registry={"pytest": scope},
    )

    rogue_path = site_packages / "rogue_plugin.py"
    rogue_path.write_text("def injected():\n    return True\n", encoding="utf-8")
    rogue = ModuleType("rogue_plugin")
    rogue.__file__ = str(rogue_path)
    rogue.__spec__ = spec_from_loader(
        "rogue_plugin",
        SourceFileLoader("rogue_plugin", str(rogue_path)),
    )
    exec(compile(rogue_path.read_bytes(), str(rogue_path), "exec"), vars(rogue))
    monkeypatch.setitem(sys.modules, "rogue_plugin", rogue)
    monkeypatch.setattr(
        mutation_toolchain,
        "_MODULE_NAMES_BEFORE_TOOLCHAIN_IMPORT",
        frozenset({"rogue_plugin"}),
    )
    with pytest.raises(MutationToolchainError, match="static reviewed byte scope"):
        mutation_toolchain._build_test_toolchain_identity(
            prefix=prefix,
            search_paths=(site_packages,),
            roots=("pytest",),
            registry={"pytest": scope},
        )


def test_pth_inferred_foreign_stdlib_name_is_not_trusted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, prefix, site_packages = _fake_toolchain(tmp_path)
    (site_packages / "foreign-json.pth").write_text(
        "import json\n",
        encoding="utf-8",
    )
    foreign_path = tmp_path / "foreign" / "json.py"
    foreign_path.parent.mkdir()
    foreign_path.write_text("FOREIGN = True\n", encoding="utf-8")
    foreign = ModuleType("json")
    foreign.__file__ = str(foreign_path)
    foreign.__spec__ = spec_from_loader(
        "json",
        SourceFileLoader("json", str(foreign_path)),
    )
    monkeypatch.setitem(sys.modules, "json", foreign)
    scope = mutation_toolchain._DistributionScope(
        import_paths=("pytest",),
        source_modules=(("pytest", "pytest/__init__.py"),),
    )
    with pytest.raises(MutationToolchainError, match="outside the admitted project"):
        mutation_toolchain._build_test_toolchain_identity(
            prefix=prefix,
            search_paths=(site_packages,),
            roots=("pytest",),
            registry={"pytest": scope},
        )


@_REQUIRES_WINDOWS_COLORAMA
def test_colorama_winterm_msvcrt_branch_is_exact_and_seals_twice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module, provider, policy, source_binding, guard = (
        _colorama_winterm_source_evidence()
    )
    imports = tuple(
        binding
        for binding in policy.imports
        if binding.name == "get_osfhandle"
    )
    assert len(imports) == 1
    source_import = imports[0]
    assert source_import.required is False
    assert source_import.may_be_overwritten is True
    assert source_import.overwrite_candidates == ()
    assert len(source_import.candidates) == 1
    import_candidate = source_import.candidates[0]
    assert (
        import_candidate.module,
        import_candidate.level,
        import_candidate.attribute,
        import_candidate.star,
    ) == ("msvcrt", 0, "get_osfhandle", False)

    fallback = source_binding.candidates[0]
    assert source_binding.required is False
    assert source_binding.must_be_absent is False
    assert (fallback.first_line, fallback.definition_line) == (5, 5)
    assert fallback.guards == (guard,)
    assert fallback.guards_complete is True
    assert guard == mutation_toolchain._SourceReviewedTryGuard(
        mutation_toolchain._COLORAMA_WINTERM_MSVCRT_TRY_POLICY,
        policy.source_ast_sha256,
        False,
    )
    assert (
        mutation_toolchain._active_source_binding_candidate(
            module,
            policy=policy,
            binding=source_binding,
        )
        is None
    )

    value = vars(provider)["get_osfhandle"]
    assert vars(module)["get_osfhandle"] is value
    assert type(value) is mutation_toolchain.BuiltinFunctionType
    assert object.__getattribute__(value, "__self__") is provider
    assert object.__getattribute__(value, "__name__") == "get_osfhandle"
    assert object.__getattribute__(value, "__qualname__") == "get_osfhandle"
    assert object.__getattribute__(value, "__module__") == "msvcrt"
    assert "__file__" not in vars(provider)
    assert provider.__spec__.origin == "built-in"
    assert provider.__spec__.loader is mutation_toolchain.BuiltinImporter

    monkeypatch.setattr(mutation_toolchain, "_RUNTIME_SOURCE_SENTINELS", {})
    _verify_selected_binding(
        "colorama.winterm",
        "get_osfhandle",
        admitted_module_names=("colorama.winterm",),
    )
    mutation_toolchain._verify_runtime_source_bindings(module, policy=policy)
    sealed = mutation_toolchain._RUNTIME_SOURCE_SENTINELS[id(module)]
    _verify_selected_binding(
        "colorama.winterm",
        "get_osfhandle",
        admitted_module_names=("colorama.winterm",),
    )
    mutation_toolchain._verify_runtime_source_bindings(module, policy=policy)
    assert mutation_toolchain._RUNTIME_SOURCE_SENTINELS[id(module)] is sealed


@_REQUIRES_WINDOWS_COLORAMA
@pytest.mark.parametrize(
    "attack_kind",
    (
        "consumer_replacement",
        "provider_replacement",
        "coordinated_replacement",
        "consumer_missing",
        "provider_missing",
        "provider_route_copy",
        "consumer_route_copy",
    ),
)
def test_colorama_winterm_rejects_identity_attacks_before_and_after_seal(
    monkeypatch: pytest.MonkeyPatch,
    attack_kind: str,
) -> None:
    module, provider, policy, _source_binding, _guard = (
        _colorama_winterm_source_evidence()
    )
    replacement = vars(provider)["open_osfhandle"]
    monkeypatch.setattr(mutation_toolchain, "_RUNTIME_SOURCE_SENTINELS", {})

    def verify() -> None:
        _verify_selected_binding(
            "colorama.winterm",
            "get_osfhandle",
            admitted_module_names=("colorama.winterm",),
        )
        mutation_toolchain._verify_runtime_source_bindings(
            module,
            policy=policy,
        )

    def attack(context: pytest.MonkeyPatch) -> None:
        if attack_kind in {"consumer_replacement", "coordinated_replacement"}:
            context.setattr(module, "get_osfhandle", replacement)
        if attack_kind in {"provider_replacement", "coordinated_replacement"}:
            context.setattr(provider, "get_osfhandle", replacement)
        if attack_kind == "consumer_missing":
            context.delattr(module, "get_osfhandle")
        if attack_kind == "provider_missing":
            context.delattr(provider, "get_osfhandle")
        if attack_kind == "provider_route_copy":
            copied_provider = ModuleType("msvcrt")
            vars(copied_provider).update(vars(provider))
            context.setitem(sys.modules, "msvcrt", copied_provider)
        if attack_kind == "consumer_route_copy":
            copied_consumer = ModuleType("colorama.winterm")
            vars(copied_consumer).update(vars(module))
            context.setitem(sys.modules, "colorama.winterm", copied_consumer)

    with monkeypatch.context() as first_attack:
        attack(first_attack)
        with pytest.raises(MutationToolchainError):
            verify()
        assert mutation_toolchain._RUNTIME_SOURCE_SENTINELS == {}

    verify()
    verify()
    sealed = mutation_toolchain._RUNTIME_SOURCE_SENTINELS[id(module)]
    with monkeypatch.context() as second_attack:
        attack(second_attack)
        with pytest.raises(MutationToolchainError):
            verify()
        assert mutation_toolchain._RUNTIME_SOURCE_SENTINELS[id(module)] is sealed


@_REQUIRES_WINDOWS_COLORAMA
@pytest.mark.parametrize("coordinated", (False, True))
def test_colorama_winterm_rejects_inactive_fallback_clone(
    monkeypatch: pytest.MonkeyPatch,
    coordinated: bool,
) -> None:
    module, provider, _policy, _source_binding, _guard = (
        _colorama_winterm_source_evidence()
    )
    source_path = Path(str(module.__file__)).resolve(strict=True)
    fallback_code = _compiled_source_candidate_code(
        source_path.read_bytes(),
        source_path=source_path,
        qualname="get_osfhandle",
        first_line=5,
    )
    fallback = FunctionType(fallback_code, vars(module), "get_osfhandle")
    monkeypatch.setattr(module, "get_osfhandle", fallback)
    if coordinated:
        monkeypatch.setattr(provider, "get_osfhandle", fallback)

    with pytest.raises(MutationToolchainError):
        _verify_selected_binding(
            "colorama.winterm",
            "get_osfhandle",
            admitted_module_names=("colorama.winterm",),
        )


@pytest.mark.parametrize(
    "source",
    (
        "try:\n    from msvcrt import get_osfhandle as handle\n"
        "except ImportError:\n    def get_osfhandle(_):\n"
        "        raise OSError(\"This isn't windows!\")\n",
        "try:\n    from msvcrt import get_osfhandle\n    marker = 1\n"
        "except ImportError:\n    def get_osfhandle(_):\n"
        "        raise OSError(\"This isn't windows!\")\n",
        "try:\n    from msvcrt import get_osfhandle\n"
        "except (ImportError, AttributeError):\n    def get_osfhandle(_):\n"
        "        raise OSError(\"This isn't windows!\")\n",
        "try:\n    from msvcrt import get_osfhandle\n"
        "except Exception:\n    def get_osfhandle(_):\n"
        "        raise OSError(\"This isn't windows!\")\n",
        "try:\n    from msvcrt import get_osfhandle\n"
        "except ImportError as error:\n    def get_osfhandle(_):\n"
        "        raise OSError(\"This isn't windows!\")\n",
        "try:\n    from msvcrt import get_osfhandle\n"
        "except ImportError:\n    def get_osfhandle(_):\n"
        "        raise OSError(\"changed\")\n",
        "try:\n    from msvcrt import get_osfhandle\n"
        "except ImportError:\n    def get_osfhandle(_, extra=None):\n"
        "        raise OSError(\"This isn't windows!\")\n",
        "try:\n    from msvcrt import get_osfhandle\n"
        "except ImportError:\n    def get_osfhandle(_):\n"
        "        raise OSError(\"This isn't windows!\")\n"
        "else:\n    marker = 1\n",
        "try:\n    from msvcrt import get_osfhandle\n"
        "except ImportError:\n    def get_osfhandle(_):\n"
        "        raise OSError(\"This isn't windows!\")\n"
        "finally:\n    marker = 1\n",
    ),
)
def test_colorama_winterm_try_topology_variants_remain_unreviewed(
    source: str,
) -> None:
    policy = mutation_toolchain._source_code_policy(ast.parse(source))
    reviewed = tuple(
        guard
        for binding in policy.bindings
        for candidate in binding.candidates
        for guard in candidate.guards
        if type(guard) is mutation_toolchain._SourceReviewedTryGuard
        and guard.policy
        == mutation_toolchain._COLORAMA_WINTERM_MSVCRT_TRY_POLICY
    )
    assert reviewed == ()


@_REQUIRES_WINDOWS_COLORAMA
def test_colorama_winterm_full_ast_drift_rejects_reviewed_try() -> None:
    module, _provider, _policy, _source_binding, _guard = (
        _colorama_winterm_source_evidence()
    )
    source = (
        "try:\n"
        "    from msvcrt import get_osfhandle\n"
        "except ImportError:\n"
        "    def get_osfhandle(_):\n"
        "        raise OSError(\"This isn't windows!\")\n"
        "UNRELATED_DRIFT = True\n"
    )
    drifted_policy = mutation_toolchain._source_code_policy(ast.parse(source))
    drifted_binding = next(
        binding
        for binding in drifted_policy.bindings
        if binding.path == ("get_osfhandle",)
    )
    drifted_guard = drifted_binding.candidates[0].guards[0]
    assert type(drifted_guard) is mutation_toolchain._SourceReviewedTryGuard
    with pytest.raises(
        MutationToolchainError,
        match="try guard is unavailable",
    ):
        mutation_toolchain._exact_source_reviewed_try_guard(
            module,
            policy=drifted_policy,
            guard=drifted_guard,
        )


@_REQUIRES_WINDOWS_COLORAMA
@pytest.mark.parametrize("mutation", ("policy", "topology", "branch"))
def test_colorama_winterm_rejects_reviewed_guard_mutation(
    mutation: str,
) -> None:
    module, _provider, policy, _source_binding, guard = (
        _colorama_winterm_source_evidence()
    )
    changed = {
        "policy": replace(guard, policy="forged-policy"),
        "topology": replace(guard, topology_sha256="0" * 64),
        "branch": replace(guard, branch=True),
    }[mutation]
    with pytest.raises(MutationToolchainError):
        mutation_toolchain._exact_source_reviewed_try_guard(
            module,
            policy=policy,
            guard=changed,
        )


@_REQUIRES_WINDOWS_COLORAMA
def test_colorama_winterm_rejects_record_and_reader_self_blessing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module, _provider, policy, _source_binding, guard = (
        _colorama_winterm_source_evidence()
    )
    record = mutation_toolchain._EAGER_COLORAMA_WINTERM_TRY_OUTCOME
    assert type(record) is mutation_toolchain._EagerColoramaWintermTryOutcome
    with monkeypatch.context() as attack:
        attack.setattr(
            mutation_toolchain,
            "_EAGER_COLORAMA_WINTERM_TRY_OUTCOME",
            replace(record),
        )
        with pytest.raises(MutationToolchainError, match="anchor changed"):
            mutation_toolchain._exact_source_reviewed_try_guard(
                module,
                policy=policy,
                guard=guard,
            )
    with monkeypatch.context() as attack:
        attack.setattr(
            mutation_toolchain,
            "_exact_eager_colorama_winterm_try_outcome",
            lambda: record,
        )
        with pytest.raises(MutationToolchainError, match="reader changed"):
            mutation_toolchain._exact_source_reviewed_try_guard(
                module,
                policy=policy,
                guard=guard,
            )

    original_topology = record.topology_sha256
    object.__setattr__(record, "topology_sha256", "f" * 64)
    try:
        with pytest.raises(MutationToolchainError, match="fingerprint changed"):
            mutation_toolchain._exact_source_reviewed_try_guard(
                module,
                policy=policy,
                guard=guard,
            )
    finally:
        object.__setattr__(record, "topology_sha256", original_topology)


@_REQUIRES_WINDOWS_COLORAMA
def test_colorama_winterm_rejects_hostile_binding_without_callbacks(
) -> None:
    module, provider, policy, _source_binding, guard = (
        _colorama_winterm_source_evidence()
    )
    callbacks: list[str] = []

    class Hostile:
        def __getattribute__(self, name: str) -> object:
            callbacks.append(name)
            raise AssertionError("hostile callback executed")

        def __eq__(self, _other: object) -> bool:
            callbacks.append("eq")
            return True

        def __bool__(self) -> bool:
            callbacks.append("bool")
            return True

        def __repr__(self) -> str:
            callbacks.append("repr")
            return "hostile"

    hostile = Hostile()
    module_namespace = vars(module)
    provider_namespace = vars(provider)
    original_module_value = module_namespace["get_osfhandle"]
    original_provider_value = provider_namespace["get_osfhandle"]
    module_namespace["get_osfhandle"] = hostile
    provider_namespace["get_osfhandle"] = hostile
    try:
        with pytest.raises(MutationToolchainError):
            mutation_toolchain._exact_source_reviewed_try_guard(
                module,
                policy=policy,
                guard=guard,
            )
    finally:
        module_namespace["get_osfhandle"] = original_module_value
        provider_namespace["get_osfhandle"] = original_provider_value
    assert callbacks == []


def test_execnet_debug_disabled_outcome_is_exact_and_seals_twice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module, policy, source_binding, record = _execnet_debug_source_evidence()
    source_path = Path(str(module.__file__)).resolve(strict=True)
    assert mutation_toolchain._exact_execnet_debug_source_topology(
        ast.parse(source_path.read_bytes())
    )
    assert record.policy == mutation_toolchain._EXECNET_DEBUG_DISABLED_POLICY
    assert record.topology_sha256 == policy.source_ast_sha256
    assert record.debug is None
    assert type(record.pid) is int
    assert vars(module)["trace"] is vars(module)["notrace"] is record.trace
    assert type(record.trace) is FunctionType
    assert record.trace.__code__ is record.trace_code
    assert record.trace.__code__.co_firstlineno == 508
    assert record.trace.__globals__ is vars(module)
    assert record.trace.__closure__ is None
    assert record.trace.__defaults__ is None
    assert record.trace.__kwdefaults__ is None
    assert tuple(
        (candidate.first_line, candidate.definition_line)
        for candidate in source_binding.candidates
    ) == ((480, 480), (496, 496))
    assert all(
        candidate.guards_complete for candidate in source_binding.candidates
    )
    assert (
        mutation_toolchain._active_source_binding_candidate(
            module,
            policy=policy,
            binding=source_binding,
        )
        is None
    )

    monkeypatch.setattr(mutation_toolchain, "_RUNTIME_SOURCE_SENTINELS", {})
    _verify_selected_binding(
        "execnet.gateway_base",
        "trace",
        admitted_module_names=("execnet.gateway_base",),
    )
    mutation_toolchain._verify_runtime_source_bindings(module, policy=policy)
    sealed = mutation_toolchain._RUNTIME_SOURCE_SENTINELS[id(module)]
    _verify_selected_binding(
        "execnet.gateway_base",
        "trace",
        admitted_module_names=("execnet.gateway_base",),
    )
    mutation_toolchain._verify_runtime_source_bindings(module, policy=policy)
    assert mutation_toolchain._RUNTIME_SOURCE_SENTINELS[id(module)] is sealed


def test_execnet_debug_guard_does_not_reread_current_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module, policy, _source_binding, _record = _execnet_debug_source_evidence()
    assert "EXECNET_DEBUG" not in os.environ
    monkeypatch.setenv("EXECNET_DEBUG", "2")
    assert vars(module)["DEBUG"] is None
    _verify_selected_binding(
        "execnet.gateway_base",
        "trace",
        admitted_module_names=("execnet.gateway_base",),
    )
    mutation_toolchain._verify_runtime_source_bindings(module, policy=policy)


@pytest.mark.parametrize(
    "attack_kind",
    (
        "stderr_branch",
        "file_branch",
        "lambda_clone",
        "split_alias",
        "missing_notrace",
        "fresh_equal_pid",
        "tempfile_residue",
        "fn_residue",
        "debugfile_residue",
        "consumer_os_copy",
        "provider_os_copy",
        "environ_replacement",
    ),
)
def test_execnet_debug_rejects_state_attacks_before_and_after_seal(
    monkeypatch: pytest.MonkeyPatch,
    attack_kind: str,
) -> None:
    module, policy, _source_binding, record = _execnet_debug_source_evidence()
    source_path = Path(str(module.__file__)).resolve(strict=True)
    source = source_path.read_bytes()
    stderr_code = _compiled_source_candidate_code(
        source,
        source_path=source_path,
        qualname="trace",
        first_line=480,
    )
    file_code = _compiled_source_candidate_code(
        source,
        source_path=source_path,
        qualname="trace",
        first_line=496,
    )
    monkeypatch.setattr(mutation_toolchain, "_RUNTIME_SOURCE_SENTINELS", {})

    def verify() -> None:
        _verify_selected_binding(
            "execnet.gateway_base",
            "trace",
            admitted_module_names=("execnet.gateway_base",),
        )
        mutation_toolchain._verify_runtime_source_bindings(
            module,
            policy=policy,
        )

    def attack(context: pytest.MonkeyPatch) -> None:
        if attack_kind == "stderr_branch":
            context.setattr(module, "DEBUG", "2")
            context.setattr(
                module,
                "trace",
                FunctionType(stderr_code, vars(module), "trace"),
            )
        elif attack_kind == "file_branch":
            context.setattr(module, "DEBUG", "1")
            context.setattr(
                module,
                "trace",
                FunctionType(file_code, vars(module), "trace"),
            )
        elif attack_kind in {"lambda_clone", "split_alias"}:
            clone = FunctionType(record.trace_code, vars(module), "<lambda>")
            context.setattr(module, "trace", clone)
            if attack_kind == "lambda_clone":
                context.setattr(module, "notrace", clone)
        elif attack_kind == "missing_notrace":
            context.delattr(module, "notrace")
        elif attack_kind == "fresh_equal_pid":
            fresh_pid = int(str(record.pid))
            assert fresh_pid == record.pid
            assert fresh_pid is not record.pid
            context.setattr(module, "pid", fresh_pid)
        elif attack_kind == "tempfile_residue":
            context.setattr(module, "tempfile", import_module("tempfile"), raising=False)
        elif attack_kind == "fn_residue":
            context.setattr(module, "fn", "inactive-debug-path", raising=False)
        elif attack_kind == "debugfile_residue":
            context.setattr(module, "debugfile", object(), raising=False)
        elif attack_kind == "consumer_os_copy":
            copied_os = ModuleType("os")
            vars(copied_os).update(vars(os))
            context.setattr(module, "os", copied_os)
        elif attack_kind == "provider_os_copy":
            copied_os = ModuleType("os")
            vars(copied_os).update(vars(os))
            context.setitem(sys.modules, "os", copied_os)
        elif attack_kind == "environ_replacement":
            context.setattr(os, "environ", {})

    with monkeypatch.context() as first_attack:
        attack(first_attack)
        with pytest.raises(MutationToolchainError):
            verify()
        assert mutation_toolchain._RUNTIME_SOURCE_SENTINELS == {}

    verify()
    verify()
    sealed = mutation_toolchain._RUNTIME_SOURCE_SENTINELS[id(module)]
    with monkeypatch.context() as second_attack:
        attack(second_attack)
        with pytest.raises(MutationToolchainError):
            verify()
        assert mutation_toolchain._RUNTIME_SOURCE_SENTINELS[id(module)] is sealed


@pytest.mark.parametrize(
    ("old", "new"),
    (
        ('os.environ.get("EXECNET_DEBUG")', 'os.getenv("EXECNET_DEBUG")'),
        ('os.environ.get("EXECNET_DEBUG")', 'os.environ["EXECNET_DEBUG"]'),
        ('"EXECNET_DEBUG"', '"OTHER_DEBUG"'),
        ('if DEBUG == "2":', 'if "2" == DEBUG:'),
        ('if DEBUG == "2":', 'if DEBUG != "2":'),
        ("elif DEBUG:", "elif bool(DEBUG):"),
        ("notrace = trace = lambda *msg: None", "trace = notrace = lambda *msg: False"),
    ),
)
def test_execnet_debug_source_topology_variants_remain_unreviewed(
    old: str,
    new: str,
) -> None:
    module = import_module("execnet.gateway_base")
    source = Path(str(module.__file__)).read_text(encoding="utf-8")
    assert source.count(old) == 1
    changed = source.replace(old, new)
    assert not mutation_toolchain._exact_execnet_debug_source_topology(
        ast.parse(changed)
    )


@pytest.mark.parametrize("extra", ("DEBUG = None\n", "trace = notrace\n"))
def test_execnet_debug_competing_writes_remain_unreviewed(extra: str) -> None:
    module = import_module("execnet.gateway_base")
    source = Path(str(module.__file__)).read_text(encoding="utf-8") + extra
    assert not mutation_toolchain._exact_execnet_debug_source_topology(
        ast.parse(source)
    )


def test_execnet_debug_full_ast_drift_rejects_eager_outcome() -> None:
    module, policy, _source_binding, _record = _execnet_debug_source_evidence()
    drifted_policy = replace(policy, source_ast_sha256="0" * 64)
    with pytest.raises(MutationToolchainError, match="outcome is unavailable"):
        mutation_toolchain._exact_execnet_debug_disabled_outcome(
            module,
            policy=drifted_policy,
        )


def test_execnet_debug_rejects_record_and_reader_self_blessing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module, policy, _source_binding, record = _execnet_debug_source_evidence()
    with monkeypatch.context() as attack:
        attack.setattr(
            mutation_toolchain,
            "_EAGER_EXECNET_DEBUG_OUTCOME",
            replace(record),
        )
        with pytest.raises(MutationToolchainError, match="anchor changed"):
            mutation_toolchain._exact_execnet_debug_disabled_outcome(
                module,
                policy=policy,
            )
    with monkeypatch.context() as attack:
        attack.setattr(
            mutation_toolchain,
            "_exact_eager_execnet_debug_outcome",
            lambda: record,
        )
        with pytest.raises(MutationToolchainError, match="reader changed"):
            mutation_toolchain._exact_execnet_debug_disabled_outcome(
                module,
                policy=policy,
            )

    original_topology = record.topology_sha256
    object.__setattr__(record, "topology_sha256", "f" * 64)
    try:
        with pytest.raises(MutationToolchainError, match="fingerprint changed"):
            mutation_toolchain._exact_execnet_debug_disabled_outcome(
                module,
                policy=policy,
            )
    finally:
        object.__setattr__(record, "topology_sha256", original_topology)


@pytest.mark.parametrize("target", ("debug", "environ", "trace"))
def test_execnet_debug_rejects_hostile_values_without_callbacks(
    target: str,
) -> None:
    module, policy, _source_binding, _record = _execnet_debug_source_evidence()
    callbacks: list[str] = []

    class Hostile:
        def __getattribute__(self, name: str) -> object:
            callbacks.append(name)
            raise AssertionError("hostile callback executed")

        def __eq__(self, _other: object) -> bool:
            callbacks.append("eq")
            return True

        def __bool__(self) -> bool:
            callbacks.append("bool")
            return True

        def __repr__(self) -> str:
            callbacks.append("repr")
            return "hostile"

    hostile = Hostile()
    module_namespace = vars(module)
    os_namespace = vars(os)
    namespace, name = {
        "debug": (module_namespace, "DEBUG"),
        "environ": (os_namespace, "environ"),
        "trace": (module_namespace, "trace"),
    }[target]
    original = namespace[name]
    namespace[name] = hostile
    try:
        with pytest.raises(MutationToolchainError):
            mutation_toolchain._exact_execnet_debug_disabled_outcome(
                module,
                policy=policy,
            )
    finally:
        namespace[name] = original
    assert callbacks == []


def test_hypothesis_settings_classdict_cell_is_exact_and_seals_twice() -> None:
    module, policy, record = _hypothesis_settings_classdict_evidence()
    namespace = type.__getattribute__(record.source_class, "__dict__")
    assert type(namespace) is MappingProxyType
    assert tuple(namespace) == record.source_namespace_keys
    assert tuple(dict.items(record.classdict)) == record.classdict_items
    assert record.classdict_items[-1] == (
        "__annotations_cache__",
        record.annotation_cache,
    )
    assert "__annotations__" not in namespace
    assert namespace["__annotations_cache__"] is record.annotation_cache
    assert type.__getattribute__(record.source_class, "__annotations__") is (
        record.annotation_cache
    )
    assert tuple(name for name, _value in record.annotation_items) == (
        "_profiles",
        "_current_profile",
    )
    assert vars(module)["settings"] is record.source_class
    assert namespace["__annotate_func__"] is record.annotate
    assert record.annotate.__code__ is record.annotate_code
    assert record.annotate.__globals__ is record.module_globals
    assert record.annotate.__builtins__ is record.annotate_builtins
    assert record.annotate.__closure__ is record.annotate_closure
    assert record.annotate_closure == (record.classdict_cell,)

    expected_marker = [
        "reviewed-direct-source-classdict-cell-v1",
        record.label,
        list(record.source_namespace_keys),
        ["_profiles", "_current_profile"],
    ]
    assert mutation_toolchain._reviewed_hypothesis_settings_classdict_cell_shape(
        record.classdict_cell,
        depth=0,
        context=mutation_toolchain._RuntimeSnapshotContext(active={}),
    ) == expected_marker
    mutation_toolchain._verify_eager_hypothesis_settings_classdict_cell(
        record.classdict_cell,
        policy=policy,
    )
    mutation_toolchain._verify_eager_hypothesis_settings_classdict_cell(
        record.classdict_cell,
        policy=policy,
    )
    function_shape = mutation_toolchain._runtime_value_shape(record.annotate)
    assert expected_marker in function_shape[10]


@pytest.mark.parametrize("when", ("before_verification", "after_verification"))
@pytest.mark.parametrize(
    "attack_kind",
    (
        "classdict_copy",
        "annotate_clone",
        "annotate_fresh_globals",
        "module_class_replacement",
        "classvar_replacement",
        "classvar_shadow",
        "dict_shadow",
        "str_shadow",
        "annotation_cache_copy",
        "annotation_cache_value",
        "annotation_cache_extra",
        "annotation_cache_reordered",
        "typing_route_copy",
        "source_module_route_copy",
    ),
)
def test_hypothesis_settings_classdict_rejects_identity_attacks_before_and_after_verification(
    monkeypatch: pytest.MonkeyPatch,
    when: str,
    attack_kind: str,
) -> None:
    module, policy, record = _hypothesis_settings_classdict_evidence()

    def verify() -> None:
        mutation_toolchain._verify_eager_hypothesis_settings_classdict_cell(
            record.classdict_cell,
            policy=policy,
        )
        mutation_toolchain._runtime_value_shape(record.annotate)

    if when == "after_verification":
        verify()
        verify()

    def restore() -> None:
        return None

    with monkeypatch.context() as attack:
        if attack_kind == "classdict_copy":
            record.cell_contents_descriptor.__set__(
                record.classdict_cell,
                dict(record.classdict),
            )
            def restore_classdict() -> None:
                record.cell_contents_descriptor.__set__(
                    record.classdict_cell,
                    record.classdict,
                )

            restore = restore_classdict
        elif attack_kind in {"annotate_clone", "annotate_fresh_globals"}:
            clone_globals = (
                dict(record.module_globals)
                if attack_kind == "annotate_fresh_globals"
                else record.module_globals
            )
            clone = FunctionType(
                record.annotate_code,
                clone_globals,
                "__annotate__",
                None,
                record.annotate_closure,
            )
            clone.__module__ = record.source_module_name
            clone.__qualname__ = "settings.__annotate__"
            type.__setattr__(record.source_class, "__annotate_func__", clone)
            def restore_annotate() -> None:
                type.__setattr__(
                    record.source_class,
                    "__annotate_func__",
                    record.annotate,
                )

            restore = restore_annotate
        elif attack_kind == "module_class_replacement":
            impostor = type(
                "settings",
                (),
                {"__module__": record.source_module_name},
            )
            attack.setattr(module, "settings", impostor)
        elif attack_kind == "classvar_replacement":
            attack.setattr(module, "ClassVar", object())
        elif attack_kind in {"classvar_shadow", "dict_shadow", "str_shadow"}:
            shadow_name = {
                "classvar_shadow": "ClassVar",
                "dict_shadow": "dict",
                "str_shadow": "str",
            }[attack_kind]
            type.__setattr__(record.source_class, shadow_name, object())
            def restore_shadow() -> None:
                type.__delattr__(record.source_class, shadow_name)

            restore = restore_shadow
        elif attack_kind == "annotation_cache_copy":
            type.__setattr__(
                record.source_class,
                "__annotations_cache__",
                dict(record.annotation_cache),
            )
            def restore_annotation_cache() -> None:
                type.__setattr__(
                    record.source_class,
                    "__annotations_cache__",
                    record.annotation_cache,
                )

            restore = restore_annotation_cache
        elif attack_kind in {
            "annotation_cache_value",
            "annotation_cache_extra",
            "annotation_cache_reordered",
        }:
            original_items = tuple(dict.items(record.annotation_cache))
            if attack_kind == "annotation_cache_value":
                dict.__setitem__(record.annotation_cache, "_profiles", object())
            elif attack_kind == "annotation_cache_extra":
                dict.__setitem__(record.annotation_cache, "forged", object())
            else:
                dict.clear(record.annotation_cache)
                for name, value in reversed(original_items):
                    dict.__setitem__(record.annotation_cache, name, value)

            def restore_cache() -> None:
                dict.clear(record.annotation_cache)
                for name, value in original_items:
                    dict.__setitem__(record.annotation_cache, name, value)

            restore = restore_cache
        elif attack_kind == "typing_route_copy":
            copied_typing = ModuleType("typing")
            vars(copied_typing).update(vars(record.typing_module))
            attack.setitem(sys.modules, "typing", copied_typing)
        elif attack_kind == "source_module_route_copy":
            copied_source = ModuleType(record.source_module_name)
            vars(copied_source).update(vars(module))
            attack.setitem(sys.modules, record.source_module_name, copied_source)
        else:
            raise AssertionError(f"unknown attack kind: {attack_kind}")

        try:
            with pytest.raises(MutationToolchainError):
                verify()
        finally:
            restore()
    verify()


def test_hypothesis_settings_classdict_rejects_source_policy_drift() -> None:
    _module, policy, record = _hypothesis_settings_classdict_evidence()
    with pytest.raises(
        MutationToolchainError,
        match="source policy changed",
    ):
        mutation_toolchain._verify_eager_hypothesis_settings_classdict_cell(
            record.classdict_cell,
            policy=replace(policy, source_ast_sha256="0" * 64),
        )


def test_hypothesis_settings_classdict_rejects_record_and_reader_self_blessing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _module, policy, record = _hypothesis_settings_classdict_evidence()
    with monkeypatch.context() as attack:
        attack.setattr(
            mutation_toolchain,
            "_EAGER_HYPOTHESIS_SETTINGS_CLASSDICT_CELL_BINDING",
            replace(record),
        )
        with pytest.raises(MutationToolchainError, match="anchor changed"):
            mutation_toolchain._verify_eager_hypothesis_settings_classdict_cell(
                record.classdict_cell,
                policy=policy,
            )
    with monkeypatch.context() as attack:
        attack.setattr(
            mutation_toolchain,
            "_exact_eager_hypothesis_settings_classdict_cell",
            lambda: record,
        )
        with pytest.raises(MutationToolchainError, match="verifier changed"):
            mutation_toolchain._verify_eager_hypothesis_settings_classdict_cell(
                record.classdict_cell,
                policy=policy,
            )

    original_hash = record.source_ast_sha256
    object.__setattr__(record, "source_ast_sha256", "f" * 64)
    try:
        with pytest.raises(MutationToolchainError, match="fingerprint changed"):
            mutation_toolchain._verify_eager_hypothesis_settings_classdict_cell(
                record.classdict_cell,
                policy=policy,
            )
    finally:
        object.__setattr__(record, "source_ast_sha256", original_hash)


def test_hypothesis_settings_classdict_rejects_hostile_cache_without_callbacks(
) -> None:
    _module, policy, record = _hypothesis_settings_classdict_evidence()
    callbacks: list[str] = []

    class Hostile:
        def __getattribute__(self, name: str) -> object:
            callbacks.append(name)
            raise AssertionError("hostile callback executed")

        def __eq__(self, _other: object) -> bool:
            callbacks.append("eq")
            return True

        def __bool__(self) -> bool:
            callbacks.append("bool")
            return True

        def __repr__(self) -> str:
            callbacks.append("repr")
            return "hostile"

    original = dict.__getitem__(record.annotation_cache, "_profiles")
    dict.__setitem__(record.annotation_cache, "_profiles", Hostile())
    callbacks.clear()
    try:
        with pytest.raises(MutationToolchainError):
            mutation_toolchain._verify_eager_hypothesis_settings_classdict_cell(
                record.classdict_cell,
                policy=policy,
            )
    finally:
        dict.__setitem__(record.annotation_cache, "_profiles", original)
    assert callbacks == []


def test_hypothesis_profile_registry_is_exact_and_seals_twice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module, policy, record = _hypothesis_profile_registry_evidence()
    assert tuple(name for name, _profile in record.registry_items) == (
        "default",
        "ci",
        "moira-ci",
        "moira-local",
        "moira-nightly",
    )
    assert record.current_profile == "moira-ci"
    assert record.registry["moira-ci"] is record.registry_items[2][1]
    assert tuple(profile[0] for profile in record.normalized_profiles) == (
        "default",
        "ci",
        "moira-ci",
        "moira-local",
        "moira-nightly",
    )
    expected_shape = [
        "reviewed-hypothesis-profile-registry-v1",
        "moira-harness",
        "moira-ci",
        [list(profile) for profile in record.normalized_profiles],
    ]
    assert mutation_toolchain._reviewed_hypothesis_profile_registry_member_shape(
        module,
        record.settings_binding.source_class,
        path="settings",
        name="_profiles",
        member=record.registry,
    ) == expected_shape
    assert mutation_toolchain._verify_eager_hypothesis_profile_registry() is record
    assert mutation_toolchain._verify_eager_hypothesis_profile_registry() is record

    monkeypatch.setattr(mutation_toolchain, "_RUNTIME_SOURCE_SENTINELS", {})
    mutation_toolchain._verify_runtime_source_bindings(module, policy=policy)
    sealed = mutation_toolchain._RUNTIME_SOURCE_SENTINELS[id(module)]
    mutation_toolchain._verify_runtime_source_bindings(module, policy=policy)
    assert mutation_toolchain._RUNTIME_SOURCE_SENTINELS[id(module)] is sealed


@pytest.mark.parametrize("when", ("before_verification", "after_verification"))
@pytest.mark.parametrize(
    "attack_kind",
    (
        "registry_copy",
        "registry_missing",
        "registry_extra",
        "registry_reordered",
        "registry_swap",
        "fresh_profile",
        "profile_namespace_copy",
        "max_examples",
        "fallback",
        "database_policy",
        "verbosity",
        "phases",
        "deadline_copy",
        "backend",
        "cache_injection",
        "current_profile",
        "effective_profile",
        "default_variable_default",
        "default_variable_data",
        "default_variable_namespace_extra",
        "thread_namespace_extra",
        "generic_alias_name",
        "typing_union_provider_binding",
        "generic_alias_provider_binding",
        "thread_local_info_binding",
        "reregister",
        "registration_clone",
        "registration_registrar_copy",
        "registration_runtime_providers_copy",
        "registration_route_copy",
        "alternate_registration_alias_same_module",
        "alternate_registration_alias_copy",
        "alternate_registration_alias_nonmodule",
        "public_settings_replacement",
        "coordinated_verbosity_replacement",
    ),
)
def test_hypothesis_profile_registry_rejects_attacks_before_and_after_verification(
    monkeypatch: pytest.MonkeyPatch,
    when: str,
    attack_kind: str,
) -> None:
    module, _policy, record = _hypothesis_profile_registry_evidence()
    source_class = record.settings_binding.source_class

    def verify() -> None:
        mutation_toolchain._verify_eager_hypothesis_profile_registry()
        mutation_toolchain._reviewed_hypothesis_profile_registry_member_shape(
            module,
            source_class,
            path="settings",
            name="_profiles",
            member=record.registry,
        )

    if when == "after_verification":
        verify()
        verify()

    def restore() -> None:
        return None

    with monkeypatch.context() as attack:
        if attack_kind == "registry_copy":
            type.__setattr__(source_class, "_profiles", dict(record.registry))

            def restore_registry_binding() -> None:
                type.__setattr__(source_class, "_profiles", record.registry)

            restore = restore_registry_binding
        elif attack_kind in {
            "registry_missing",
            "registry_extra",
            "registry_reordered",
            "registry_swap",
            "fresh_profile",
            "reregister",
        }:
            original_items = tuple(dict.items(record.registry))
            if attack_kind == "registry_missing":
                dict.__delitem__(record.registry, "moira-nightly")
            elif attack_kind == "registry_extra":
                dict.__setitem__(record.registry, "forged", object())
            elif attack_kind == "registry_reordered":
                dict.clear(record.registry)
                for name, profile in reversed(original_items):
                    dict.__setitem__(record.registry, name, profile)
            elif attack_kind == "registry_swap":
                dict.__setitem__(
                    record.registry,
                    "moira-ci",
                    dict.__getitem__(record.registry, "moira-local"),
                )
            elif attack_kind == "fresh_profile":
                original_profile = dict.__getitem__(record.registry, "moira-ci")
                clone = object.__new__(source_class)
                object.__setattr__(
                    clone,
                    "__dict__",
                    dict(object.__getattribute__(original_profile, "__dict__")),
                )
                dict.__setitem__(record.registry, "moira-ci", clone)
            else:
                assert record.registration_function is not None
                with warnings.catch_warnings():
                    warnings.simplefilter("error")
                    warnings.filterwarnings(
                        "ignore",
                        message=(
                            "Cannot register a settings profile when the current "
                            "settings differ from the current profile.*"
                        ),
                        category=HypothesisDeprecationWarning,
                    )
                    assert record.registration_function() is True

            def restore_registry_contents() -> None:
                dict.clear(record.registry)
                for name, profile in original_items:
                    dict.__setitem__(record.registry, name, profile)
                if attack_kind == "reregister":
                    type.__setattr__(
                        source_class,
                        "_current_profile",
                        record.current_profile,
                    )
                    dict.__setitem__(
                        record.default_thread_namespace,
                        "value",
                        record.active_profile,
                    )

            restore = restore_registry_contents
        elif attack_kind == "profile_namespace_copy":
            profile = dict.__getitem__(record.registry, "moira-ci")
            original_namespace = object.__getattribute__(profile, "__dict__")
            object.__setattr__(profile, "__dict__", dict(original_namespace))

            def restore_profile_namespace() -> None:
                object.__setattr__(profile, "__dict__", original_namespace)

            restore = restore_profile_namespace
        elif attack_kind in {
            "max_examples",
            "fallback",
            "database_policy",
            "verbosity",
            "phases",
            "deadline_copy",
            "backend",
            "cache_injection",
        }:
            profile_name = (
                "moira-local" if attack_kind == "database_policy" else "moira-ci"
            )
            profile = dict.__getitem__(record.registry, profile_name)
            namespace = object.__getattribute__(profile, "__dict__")
            field, replacement = {
                "max_examples": ("_max_examples", 51),
                "fallback": ("_fallback", object()),
                "database_policy": ("_database", None),
                "verbosity": ("_verbosity", record.verbosity_normal),
                "phases": ("_phases", tuple(list(record.phases))),
                "deadline_copy": (
                    "_deadline",
                    record.duration_type(milliseconds=1000),
                ),
                "backend": ("_backend", "forged"),
                "cache_injection": ("_cached_database", object()),
            }[attack_kind]
            original = dict.__getitem__(namespace, field)
            if attack_kind == "deadline_copy":
                assert replacement == original
                assert replacement is not original
            dict.__setitem__(namespace, field, replacement)

            def restore_profile_field() -> None:
                dict.__setitem__(namespace, field, original)

            restore = restore_profile_field
        elif attack_kind == "current_profile":
            type.__setattr__(source_class, "_current_profile", "moira-local")

            def restore_current_profile() -> None:
                type.__setattr__(
                    source_class,
                    "_current_profile",
                    record.current_profile,
                )

            restore = restore_current_profile
        elif attack_kind == "effective_profile":
            original = dict.__getitem__(
                record.default_thread_namespace,
                "value",
            )
            dict.__setitem__(
                record.default_thread_namespace,
                "value",
                dict.__getitem__(record.registry, "moira-local"),
            )

            def restore_effective_profile() -> None:
                dict.__setitem__(
                    record.default_thread_namespace,
                    "value",
                    original,
                )

            restore = restore_effective_profile
        elif attack_kind == "default_variable_default":
            original = dict.__getitem__(record.default_variable_namespace, "default")
            dict.__setitem__(record.default_variable_namespace, "default", object())

            def restore_default_variable_default() -> None:
                dict.__setitem__(
                    record.default_variable_namespace,
                    "default",
                    original,
                )

            restore = restore_default_variable_default
        elif attack_kind == "default_variable_data":
            original = dict.__getitem__(record.default_variable_namespace, "data")
            dict.__setitem__(
                record.default_variable_namespace,
                "data",
                record.thread_local_type(),
            )

            def restore_default_variable_data() -> None:
                dict.__setitem__(
                    record.default_variable_namespace,
                    "data",
                    original,
                )

            restore = restore_default_variable_data
        elif attack_kind == "default_variable_namespace_extra":
            dict.__setitem__(record.default_variable_namespace, "forged", object())

            def restore_default_variable_namespace_extra() -> None:
                dict.__delitem__(record.default_variable_namespace, "forged")

            restore = restore_default_variable_namespace_extra
        elif attack_kind == "thread_namespace_extra":
            dict.__setitem__(record.default_thread_namespace, "forged", object())

            def restore_thread_namespace_extra() -> None:
                dict.__delitem__(record.default_thread_namespace, "forged")

            restore = restore_thread_namespace_extra
        elif attack_kind == "generic_alias_name":
            original = dict.__getitem__(
                record.default_orig_class_namespace,
                "_name",
            )
            dict.__setitem__(
                record.default_orig_class_namespace,
                "_name",
                "Forged",
            )

            def restore_generic_alias_name() -> None:
                dict.__setitem__(
                    record.default_orig_class_namespace,
                    "_name",
                    original,
                )

            restore = restore_generic_alias_name
        elif attack_kind == "typing_union_provider_binding":
            attack.setattr(
                record.type_providers.typing_module,
                "Union",
                object(),
            )
        elif attack_kind == "generic_alias_provider_binding":
            attack.setattr(
                record.type_providers.typing_module,
                "_GenericAlias",
                object(),
            )
        elif attack_kind == "thread_local_info_binding":
            attack.setattr(
                record.threading_module,
                "_thread_local_info",
                record.thread_local_type(),
            )
        elif attack_kind == "registration_clone":
            assert record.registration_function is not None
            assert record.registration_code is not None
            assert record.registration_globals is not None
            assert record.registration_module is not None
            clone = FunctionType(
                record.registration_code,
                record.registration_globals,
                "_register_hypothesis_profiles",
            )
            clone.__module__ = record.registration_module_name
            clone.__qualname__ = "_register_hypothesis_profiles"
            attack.setattr(
                record.registration_module,
                "_register_hypothesis_profiles",
                clone,
            )
        elif attack_kind == "registration_registrar_copy":
            assert record.registration_module is not None
            assert record.registration_registrar is not None
            attack.setattr(
                record.registration_module,
                "_HYPOTHESIS_PROFILE_REGISTRAR",
                tuple(list(record.registration_registrar)),
            )
        elif attack_kind == "registration_runtime_providers_copy":
            assert record.registration_module is not None
            assert record.registration_runtime_providers is not None
            attack.setattr(
                record.registration_module,
                "_HYPOTHESIS_PROFILE_RUNTIME_PROVIDERS",
                tuple(list(record.registration_runtime_providers)),
            )
        elif attack_kind == "registration_route_copy":
            assert record.registration_module_name is not None
            assert record.registration_module is not None
            copied_registration = ModuleType(record.registration_module_name)
            vars(copied_registration).update(vars(record.registration_module))
            attack.setitem(
                sys.modules,
                record.registration_module_name,
                copied_registration,
            )
        elif attack_kind.startswith("alternate_registration_alias_"):
            assert record.registration_module_name is not None
            assert record.registration_module is not None
            alternate_name = (
                "tests._pytest_plugins.determinism"
                if record.registration_module_name
                == "_pytest_plugins.determinism"
                else "_pytest_plugins.determinism"
            )
            if attack_kind == "alternate_registration_alias_same_module":
                alternate_value: object = record.registration_module
            elif attack_kind == "alternate_registration_alias_copy":
                alternate_value = ModuleType(alternate_name)
                vars(alternate_value).update(vars(record.registration_module))
            else:
                alternate_value = object()
            attack.setitem(sys.modules, alternate_name, alternate_value)
        elif attack_kind == "public_settings_replacement":
            attack.setattr(record.public_module, "settings", object())
        elif attack_kind == "coordinated_verbosity_replacement":
            replacement = object()
            attack.setattr(record.public_module, "Verbosity", replacement)
            attack.setattr(module, "Verbosity", replacement)
        else:
            raise AssertionError(f"unknown attack kind: {attack_kind}")

        try:
            with pytest.raises(MutationToolchainError):
                verify()
        finally:
            restore()
    verify()


def test_hypothesis_profile_registry_rejects_record_and_reader_self_blessing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _module, _policy, record = _hypothesis_profile_registry_evidence()
    type_providers = record.type_providers
    with monkeypatch.context() as attack:
        attack.setattr(
            mutation_toolchain,
            "_EAGER_HYPOTHESIS_PROFILE_TYPE_PROVIDERS",
            replace(type_providers),
        )
        with pytest.raises(MutationToolchainError, match="anchor changed"):
            mutation_toolchain._verify_eager_hypothesis_profile_registry()
    with monkeypatch.context() as attack:
        attack.setattr(
            mutation_toolchain,
            "_verify_eager_hypothesis_profile_type_providers",
            lambda: type_providers,
        )
        with pytest.raises(MutationToolchainError, match="verifier changed"):
            mutation_toolchain._verify_eager_hypothesis_profile_registry()
    with monkeypatch.context() as attack:
        attack.setattr(
            mutation_toolchain,
            "_EAGER_HYPOTHESIS_PROFILE_REGISTRY_BINDING",
            replace(record),
        )
        with pytest.raises(MutationToolchainError, match="anchor changed"):
            mutation_toolchain._verify_eager_hypothesis_profile_registry()
    with monkeypatch.context() as attack:
        attack.setattr(
            mutation_toolchain,
            "_exact_eager_hypothesis_profile_registry",
            lambda: record,
        )
        with pytest.raises(MutationToolchainError, match="verifier changed"):
            mutation_toolchain._verify_eager_hypothesis_profile_registry()
    with monkeypatch.context() as attack:
        attack.setattr(
            mutation_toolchain,
            "_verify_eager_hypothesis_profile_registry",
            lambda: record,
        )
        with pytest.raises(MutationToolchainError, match="shape verifier changed"):
            mutation_toolchain._reviewed_hypothesis_profile_registry_member_shape(
                record.settings_binding.source_module,
                record.settings_binding.source_class,
                path="settings",
                name="_profiles",
                member=record.registry,
            )

    original_mode = record.mode
    object.__setattr__(record, "mode", "forged")
    try:
        with pytest.raises(MutationToolchainError, match="fingerprint changed"):
            mutation_toolchain._verify_eager_hypothesis_profile_registry()
    finally:
        object.__setattr__(record, "mode", original_mode)

    original_provider_label = type_providers.label
    object.__setattr__(type_providers, "label", "forged")
    try:
        with pytest.raises(MutationToolchainError, match="fingerprint changed"):
            mutation_toolchain._verify_eager_hypothesis_profile_registry()
    finally:
        object.__setattr__(
            type_providers,
            "label",
            original_provider_label,
        )


def test_hypothesis_profile_registry_rejects_hostile_value_without_callbacks(
) -> None:
    _module, _policy, record = _hypothesis_profile_registry_evidence()
    callbacks: list[str] = []

    class Hostile:
        def __getattribute__(self, name: str) -> object:
            callbacks.append(name)
            raise AssertionError("hostile callback executed")

        def __eq__(self, _other: object) -> bool:
            callbacks.append("eq")
            return True

        def __hash__(self) -> int:
            callbacks.append("hash")
            return 0

        def __repr__(self) -> str:
            callbacks.append("repr")
            return "hostile"

    original = dict.__getitem__(record.registry, "moira-ci")
    dict.__setitem__(record.registry, "moira-ci", Hostile())
    callbacks.clear()
    try:
        with pytest.raises(MutationToolchainError):
            mutation_toolchain._verify_eager_hypothesis_profile_registry()
    finally:
        dict.__setitem__(record.registry, "moira-ci", original)
    assert callbacks == []


@pytest.mark.parametrize("field", ("path", "name"))
def test_hypothesis_profile_registry_shape_rejects_hostile_strings_without_callbacks(
    field: str,
) -> None:
    module, _policy, record = _hypothesis_profile_registry_evidence()
    callbacks: list[str] = []

    class HostileString(str):
        def __eq__(self, _other: object) -> bool:
            callbacks.append("eq")
            return True

        def __hash__(self) -> int:
            callbacks.append("hash")
            return str.__hash__(self)

        def __repr__(self) -> str:
            callbacks.append("repr")
            return "hostile"

    values: dict[str, object] = {
        "path": "settings",
        "name": "_profiles",
    }
    values[field] = HostileString(str(values[field]))
    callbacks.clear()
    assert (
        mutation_toolchain._reviewed_hypothesis_profile_registry_member_shape(
            module,
            record.settings_binding.source_class,
            path=values["path"],
            name=values["name"],
            member=record.registry,
        )
        is mutation_toolchain._EAGER_ATTRIBUTE_MISSING
    )
    assert callbacks == []


def test_hypothesis_profile_registry_effective_profile_drift_fails_full_runtime_seal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module, policy, record = _hypothesis_profile_registry_evidence()
    monkeypatch.setattr(mutation_toolchain, "_RUNTIME_SOURCE_SENTINELS", {})
    mutation_toolchain._verify_runtime_source_bindings(module, policy=policy)
    original = dict.__getitem__(record.default_thread_namespace, "value")
    dict.__setitem__(
        record.default_thread_namespace,
        "value",
        dict.__getitem__(record.registry, "moira-local"),
    )
    try:
        with pytest.raises(MutationToolchainError):
            mutation_toolchain._verify_runtime_source_bindings(
                module,
                policy=policy,
            )
    finally:
        dict.__setitem__(record.default_thread_namespace, "value", original)


@pytest.mark.parametrize(
    "attack_source",
    (
        """
profile = settings._profiles["moira-ci"]
vars(profile)["_deadline"] = type(vars(profile)["_deadline"])(
    microseconds=1_000_001
)
""",
        """
profile = settings._profiles["moira-ci"]
vars(profile)["_stateful_step_count"] = 50.0
""",
        """
class Hostile:
    def __eq__(self, _other):
        callbacks.append("eq")
        return True
    def __hash__(self):
        callbacks.append("hash")
        return 0
    def __repr__(self):
        callbacks.append("repr")
        return "hostile"
profile = settings._profiles["moira-ci"]
vars(profile)["_backend"] = Hostile()
""",
        """
class HostileKey(str):
    def __eq__(self, other):
        callbacks.append("eq")
        return str.__eq__(self, other)
    def __hash__(self):
        callbacks.append("hash")
        return str.__hash__(self)
profile = settings._profiles["moira-ci"]
namespace = vars(profile)
value = dict.pop(namespace, "_backend")
dict.__setitem__(namespace, HostileKey("_backend"), value)
""",
        """
import hypothesis._settings as hypothesis_settings
vars(hypothesis_settings.default_variable)["default"] = object()
""",
        """
import hypothesis._settings as hypothesis_settings
vars(vars(hypothesis_settings.default_variable)["data"])["value"] = (
    settings._profiles["moira-local"]
)
""",
        """
import hypothesis._settings as hypothesis_settings
vars(hypothesis_settings.default_variable)["forged"] = object()
""",
        """
for name in ("moira-ci", "moira-local", "moira-nightly"):
    dict.__delitem__(settings._profiles, name)
""",
        """
determinism._HYPOTHESIS_AVAILABLE = False
""",
        """
import hypothesis._settings as hypothesis_settings
import typing
real_union = typing.Union
generic = vars(hypothesis_settings.default_variable)["__orig_class__"]
real_optional = vars(generic)["__args__"][0]
real_optional_args = object.__getattribute__(real_optional, "__args__")
class Union:
    __module__ = "typing"
    @classmethod
    def __class_getitem__(cls, item):
        return real_union[item]
    @property
    def __args__(self):
        callbacks.append("union-args")
        return real_optional_args
vars(generic)["__args__"] = (Union(),)
typing.Union = Union
""",
        """
import hypothesis._settings as hypothesis_settings
import typing
real_generic_alias = typing._GenericAlias
class AliasMeta(type):
    def __call__(cls, *args, **kwargs):
        return real_generic_alias(*args, **kwargs)
class _GenericAlias(metaclass=AliasMeta):
    __module__ = "typing"
    @property
    def __dict__(self):
        callbacks.append("generic-alias-dict")
        raise AssertionError("hostile generic metadata executed")
fake_generic_alias = object.__new__(_GenericAlias)
typing._GenericAlias = _GenericAlias
vars(hypothesis_settings.default_variable)["__orig_class__"] = (
    fake_generic_alias
)
""",
        """
import _thread
import hypothesis._settings as hypothesis_settings
import threading
class CounterfeitLocal:
    def __getattribute__(self, name):
        callbacks.append("local:" + name)
        raise AssertionError("hostile thread-local callback executed")
CounterfeitLocal.__module__ = "_thread"
CounterfeitLocal.__name__ = "_local"
CounterfeitLocal.__qualname__ = "_local"
active = object.__new__(CounterfeitLocal)
object.__setattr__(active, "value", settings._profiles["moira-ci"])
info = object.__new__(CounterfeitLocal)
_thread._local = CounterfeitLocal
threading.local = CounterfeitLocal
threading._thread_local_info = info
vars(hypothesis_settings.default_variable)["data"] = active
""",
        """
from types import FunctionType
registration = determinism._register_hypothesis_profiles
clone = FunctionType(
    registration.__code__,
    registration.__globals__,
    registration.__name__,
    registration.__defaults__,
    registration.__closure__,
)
clone.__module__ = registration.__module__
clone.__qualname__ = registration.__qualname__
determinism._register_hypothesis_profiles = clone
""",
    ),
    ids=(
        "fractional_millisecond_deadline",
        "float_stateful_step_count",
        "hostile_backend",
        "hostile_profile_key",
        "forged_dynamic_default",
        "divergent_effective_profile",
        "extra_dynamic_state",
        "loaded_owner_missing_profiles",
        "false_hypothesis_availability",
        "coordinated_typing_union_provider",
        "coordinated_generic_alias_provider",
        "coordinated_thread_local_provider",
        "cloned_registration_function",
    ),
)
def test_hypothesis_profile_registry_rejects_preimport_self_blessing(
    attack_source: str,
) -> None:
    code = f"""
from tests._pytest_plugins import determinism
from hypothesis import settings
settings.load_profile("moira-ci")
determinism.snapshot_hypothesis_policy()
callbacks = []
{attack_source}
callbacks.clear()
try:
    from tests.support import mutation_toolchain as toolchain
except Exception as exc:
    assert type(exc).__name__ == "MutationToolchainError", type(exc).__name__
else:
    raise AssertionError(toolchain)
assert callbacks == [], callbacks
"""
    completed = subprocess.run(
        [sys.executable, "-B", "-c", code],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=_SUBPROCESS_TIMEOUT_SECONDS,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_hypothesis_profile_registry_rejects_exact_preimport_forward_ref_clone_without_callbacks(
) -> None:
    code = """
callbacks = []
class Hostile:
    def __getattribute__(self, name):
        if name != "_record":
            callbacks.append("get:" + name)
        raise AssertionError("hostile callback executed")
    def __eq__(self, _other):
        callbacks.append("eq")
        return True
    def __hash__(self):
        callbacks.append("hash")
        return 0
    def __repr__(self):
        callbacks.append("repr")
        return "hostile"

from tests._pytest_plugins import determinism
from hypothesis import settings
settings.load_profile("moira-ci")
determinism.snapshot_hypothesis_policy()
import annotationlib
import hypothesis._settings as hypothesis_settings
import typing

original_forward_ref = annotationlib.ForwardRef
typing_had_forward_ref = "ForwardRef" in vars(typing)
original_typing_forward_ref = vars(typing).get("ForwardRef")
original_orig_class = vars(hypothesis_settings.default_variable)[
    "__orig_class__"
]
original_namespace = vars(original_forward_ref)
slots = original_namespace["__slots__"]
excluded = set(slots) | {"__weakref__", "__dict__"}
clone_namespace = {}
for name, member in original_namespace.items():
    if name == "__slots__":
        clone_namespace[name] = slots
    elif name not in excluded:
        clone_namespace[name] = member
counterfeit_forward_ref = type("ForwardRef", (object,), clone_namespace)
assert tuple(vars(counterfeit_forward_ref)) == tuple(original_namespace)
assert counterfeit_forward_ref is not original_forward_ref

annotationlib.ForwardRef = counterfeit_forward_ref
vars(typing).pop("ForwardRef", None)
counterfeit_ref = counterfeit_forward_ref("settings", owner=Hostile())
counterfeit_optional = typing.Union[counterfeit_ref, None]
counterfeit_outer = original_orig_class.copy_with((counterfeit_optional,))
vars(hypothesis_settings.default_variable)["__orig_class__"] = (
    counterfeit_outer
)
callbacks.clear()
rejected = None
try:
    from tests.support import mutation_toolchain as toolchain
except Exception as exc:
    rejected = exc
finally:
    vars(hypothesis_settings.default_variable)["__orig_class__"] = (
        original_orig_class
    )
    annotationlib.ForwardRef = original_forward_ref
    if typing_had_forward_ref:
        vars(typing)["ForwardRef"] = original_typing_forward_ref
    else:
        vars(typing).pop("ForwardRef", None)
assert rejected is not None
assert type(rejected).__name__ == "MutationToolchainError"
assert "runtime anchor changed" in str(rejected)
assert callbacks == [], callbacks
"""
    completed = subprocess.run(
        [sys.executable, "-B", "-c", code],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=_SUBPROCESS_TIMEOUT_SECONDS,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_hypothesis_profile_registry_rejects_hostile_forward_ref_property_without_callbacks(
) -> None:
    callbacks: list[str] = []
    forward_ref_type = annotationlib.ForwardRef
    original = vars(forward_ref_type)["__forward_arg__"]

    def hostile_forward_arg(_self: object) -> str:
        callbacks.append("forward-arg")
        return "settings"

    type.__setattr__(
        forward_ref_type,
        "__forward_arg__",
        property(hostile_forward_arg),
    )
    callbacks.clear()
    try:
        with pytest.raises(
            MutationToolchainError,
            match="annotationlib.ForwardRef provider changed",
        ):
            mutation_toolchain._verify_eager_hypothesis_profile_registry()
    finally:
        type.__setattr__(forward_ref_type, "__forward_arg__", original)
    assert callbacks == []
    mutation_toolchain._verify_eager_hypothesis_profile_registry()


@pytest.mark.parametrize(
    "attack_kind",
    (
        "typing_spec_origin",
        "union_module_name",
        "generic_alias_function_module",
        "forward_ref_slots",
    ),
)
def test_hypothesis_profile_type_providers_reject_hostile_scalars_without_callbacks(
    monkeypatch: pytest.MonkeyPatch,
    attack_kind: str,
) -> None:
    callbacks: list[str] = []

    class HostileString(str):
        def __eq__(self, _other: object) -> bool:
            callbacks.append("eq")
            return True

        def __ne__(self, _other: object) -> bool:
            callbacks.append("ne")
            return False

        def __hash__(self) -> int:
            callbacks.append("hash")
            return str.__hash__(self)

        def __repr__(self) -> str:
            callbacks.append("repr")
            return "hostile"

    class HostileTuple(tuple):
        def __eq__(self, _other: object) -> bool:
            callbacks.append("tuple-eq")
            return True

        def __ne__(self, _other: object) -> bool:
            callbacks.append("tuple-ne")
            return False

    with monkeypatch.context() as attack:
        if attack_kind == "typing_spec_origin":
            attack.setattr(
                typing.__spec__,
                "origin",
                HostileString(str(typing.__spec__.origin)),
            )
        elif attack_kind == "union_module_name":
            class CounterfeitUnion:
                pass

            type.__setattr__(
                CounterfeitUnion,
                "__module__",
                HostileString("typing"),
            )
            attack.setattr(typing, "Union", CounterfeitUnion)
        elif attack_kind == "generic_alias_function_module":
            function = vars(typing._GenericAlias)["__eq__"]
            attack.setattr(function, "__module__", HostileString("typing"))
        elif attack_kind == "forward_ref_slots":
            attack.setattr(
                annotationlib.ForwardRef,
                "__slots__",
                HostileTuple(vars(annotationlib.ForwardRef)["__slots__"]),
            )
        else:
            raise AssertionError(attack_kind)
        callbacks.clear()
        with pytest.raises(MutationToolchainError):
            mutation_toolchain._verify_eager_hypothesis_profile_registry()
    assert callbacks == []
    mutation_toolchain._verify_eager_hypothesis_profile_registry()


@pytest.mark.parametrize(
    "alternate_kind",
    ("same_module", "copied_module", "none", "hostile"),
)
def test_hypothesis_profile_registry_rejects_preimport_alternate_owner_alias(
    alternate_kind: str,
) -> None:
    code = f"""
import sys
from types import ModuleType
from tests._pytest_plugins import determinism
from hypothesis import settings
settings.load_profile("moira-ci")
determinism.snapshot_hypothesis_policy()
callbacks = []
class Hostile:
    def __getattribute__(self, name):
        callbacks.append("get:" + name)
        raise AssertionError("hostile callback executed")
    def __eq__(self, _other):
        callbacks.append("eq")
        return True
    def __hash__(self):
        callbacks.append("hash")
        return 0
    def __repr__(self):
        callbacks.append("repr")
        return "hostile"
if {alternate_kind!r} == "same_module":
    alternate = determinism
elif {alternate_kind!r} == "copied_module":
    alternate = ModuleType("_pytest_plugins.determinism")
    vars(alternate).update(vars(determinism))
elif {alternate_kind!r} == "none":
    alternate = None
else:
    alternate = Hostile()
dict.__setitem__(sys.modules, "_pytest_plugins.determinism", alternate)
callbacks.clear()
try:
    from tests.support import mutation_toolchain as toolchain
except Exception as exc:
    assert type(exc).__name__ == "MutationToolchainError", type(exc).__name__
else:
    raise AssertionError(toolchain)
assert callbacks == [], callbacks
"""
    completed = subprocess.run(
        [sys.executable, "-B", "-c", code],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=_SUBPROCESS_TIMEOUT_SECONDS,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_hypothesis_profile_registry_supports_exact_mutation_child_bootstrap(
) -> None:
    code = """
from tests._pytest_plugins import determinism
from hypothesis import settings
settings.load_profile("moira-ci")
determinism.snapshot_hypothesis_policy()
from tests.support import mutation_toolchain as toolchain
record = toolchain._verify_eager_hypothesis_profile_registry()
assert record.mode == "moira-harness"
assert record.current_profile == "moira-ci"
assert record.cached_database_bindings == ()
assert toolchain._verify_eager_hypothesis_profile_registry() is record
"""
    completed = subprocess.run(
        [sys.executable, "-B", "-c", code],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=_SUBPROCESS_TIMEOUT_SECONDS,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


@pytest.mark.parametrize("profile", ("moira-local", "moira-nightly"))
def test_hypothesis_profile_registry_rejects_database_enabled_mutation_children(
    profile: str,
) -> None:
    code = f"""
from tests._pytest_plugins import determinism
from hypothesis import settings
settings.load_profile({profile!r})
determinism.snapshot_hypothesis_policy()
try:
    from tests.support import mutation_toolchain as toolchain
except Exception as exc:
    assert type(exc).__name__ == "MutationToolchainError", type(exc).__name__
    assert "owner topology changed" in str(exc)
else:
    raise AssertionError(toolchain)
"""
    completed = subprocess.run(
        [sys.executable, "-B", "-c", code],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=_SUBPROCESS_TIMEOUT_SECONDS,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


@pytest.mark.parametrize(
    ("ci_value", "expected_profile"),
    ((None, "default"), ("true", "ci")),
)
def test_hypothesis_profile_registry_supports_clean_builtin_parent_modes(
    ci_value: str | None,
    expected_profile: str,
) -> None:
    environment = os.environ.copy()
    for name in (
        "CI",
        "__TOX_ENVIRONMENT_VARIABLE_ORIGINAL_CI",
        "TF_BUILD",
        "bamboo.buildKey",
        "BUILDKITE",
        "CIRCLECI",
        "CIRRUS_CI",
        "CODEBUILD_BUILD_ID",
        "GITHUB_ACTIONS",
        "GITLAB_CI",
        "HEROKU_TEST_RUN_ID",
        "TEAMCITY_VERSION",
    ):
        environment.pop(name, None)
    if ci_value is not None:
        environment["CI"] = ci_value
    code = f"""
from tests.support import mutation_toolchain as toolchain
record = toolchain._verify_eager_hypothesis_profile_registry()
assert record.mode == "builtin-only"
assert record.current_profile == {expected_profile!r}
assert record.cached_database_bindings == ()
assert toolchain._verify_eager_hypothesis_profile_registry() is record
"""
    completed = subprocess.run(
        [sys.executable, "-B", "-c", code],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=_SUBPROCESS_TIMEOUT_SECONDS,
        env=environment,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


@pytest.mark.parametrize(
    ("name", "provider_name", "provider_attribute"),
    (
        ("dataclass_asdict", "dataclasses", "asdict"),
        ("batched", "itertools", "batched"),
    ),
)
def test_hypothesis_compat_stdlib_alias_is_exact_and_seals_twice(
    name: str,
    provider_name: str,
    provider_attribute: str,
) -> None:
    module, policy, binding, provider, provider_value = (
        _hypothesis_compat_stdlib_alias_evidence(name)
    )
    stdlib_record = (
        mutation_toolchain._verify_eager_hypothesis_compat_stdlib_providers()
    )
    assert (
        mutation_toolchain._verify_eager_hypothesis_compat_stdlib_providers()
        is stdlib_record
    )
    if name == "dataclass_asdict":
        provider_record = (
            mutation_toolchain._verify_eager_hypothesis_compat_dataclasses_provider()
        )
        assert (
            mutation_toolchain._verify_eager_hypothesis_compat_dataclasses_provider()
            is provider_record
        )
        assert provider_record.module is provider
    else:
        provider_record = (
            mutation_toolchain._verify_eager_hypothesis_compat_batched_provider()
        )
        assert (
            mutation_toolchain._verify_eager_hypothesis_compat_batched_provider()
            is provider_record
        )
        assert provider_record.module is provider
        assert provider_record.value is provider_value
    for _attempt in range(2):
        assert (
            mutation_toolchain._exact_hypothesis_compat_inactive_stdlib_alias_expected_value(
                module,
                policy=policy,
                source_binding=binding,
            )
            is provider_value
        )
        assert (
            mutation_toolchain._exact_inactive_source_import_expected_value(
                module,
                policy=policy,
                source_binding=binding,
            )
            is provider_value
        )
        _verify_selected_binding(
            "hypothesis.internal.compat",
            name,
            admitted_module_names=(),
    )
    assert provider.__name__ == provider_name
    assert vars(provider)[provider_attribute] is provider_value


@pytest.mark.parametrize(
    ("name", "record_name", "verifier_name"),
    (
        (
            "dataclass_asdict",
            "_EAGER_HYPOTHESIS_COMPAT_STDLIB_PROVIDERS",
            "_verify_eager_hypothesis_compat_stdlib_providers",
        ),
        (
            "dataclass_asdict",
            "_EAGER_HYPOTHESIS_COMPAT_DATACLASSES_PROVIDER",
            "_verify_eager_hypothesis_compat_dataclasses_provider",
        ),
        (
            "batched",
            "_EAGER_HYPOTHESIS_COMPAT_BATCHED_PROVIDER",
            "_verify_eager_hypothesis_compat_batched_provider",
        ),
    ),
)
def test_hypothesis_compat_provider_records_reject_self_blessing(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    record_name: str,
    verifier_name: str,
) -> None:
    module, policy, binding, _provider, _provider_value = (
        _hypothesis_compat_stdlib_alias_evidence(name)
    )
    verifier = getattr(mutation_toolchain, verifier_name)
    record = verifier()
    with monkeypatch.context() as attack:
        attack.setattr(mutation_toolchain, record_name, replace(record))
        with pytest.raises(MutationToolchainError):
            verifier()

    callbacks: list[str] = []

    def forged_verifier() -> object:
        callbacks.append("verifier")
        return record

    with monkeypatch.context() as attack:
        attack.setattr(mutation_toolchain, verifier_name, forged_verifier)
        callbacks.clear()
        with pytest.raises(MutationToolchainError):
            mutation_toolchain._exact_hypothesis_compat_inactive_stdlib_alias_expected_value(
                module,
                policy=policy,
                source_binding=binding,
            )
    assert callbacks == []


def test_hypothesis_compat_dispatchers_reject_replacement_without_callbacks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module, policy, binding, _provider, provider_value = (
        _hypothesis_compat_stdlib_alias_evidence("dataclass_asdict")
    )
    callbacks: list[str] = []

    def forged_alias_reader(
        _module: ModuleType,
        *,
        policy: object,
        source_binding: object,
    ) -> object:
        callbacks.extend(("alias", repr(policy), repr(source_binding)))
        return provider_value

    with monkeypatch.context() as attack:
        attack.setattr(
            mutation_toolchain,
            "_exact_hypothesis_compat_inactive_stdlib_alias_expected_value",
            forged_alias_reader,
        )
        callbacks.clear()
        with pytest.raises(MutationToolchainError, match="dispatcher changed"):
            mutation_toolchain._exact_inactive_source_import_expected_value(
                module,
                policy=policy,
                source_binding=binding,
            )
    assert callbacks == []

    original_router = (
        mutation_toolchain._exact_inactive_source_import_expected_value
    )

    def forged_router(
        _module: ModuleType,
        *,
        policy: object,
        source_binding: object,
    ) -> object:
        callbacks.extend(("router", repr(policy), repr(source_binding)))
        return provider_value

    source_path = Path(str(module.__file__)).resolve(strict=True)
    with monkeypatch.context() as attack:
        attack.setattr(
            mutation_toolchain,
            "_exact_inactive_source_import_expected_value",
            forged_router,
        )
        callbacks.clear()
        with pytest.raises(MutationToolchainError, match="verifier binding changed"):
            mutation_toolchain._verify_loaded_source_code(
                module,
                source=b"",
                source_path=source_path,
                variant="raw",
            )
    assert callbacks == []
    assert (
        mutation_toolchain._exact_inactive_source_import_expected_value
        is original_router
    )


@pytest.mark.parametrize("name", ("dataclass_asdict", "batched"))
@pytest.mark.parametrize(
    "attack_kind",
    (
        "binding_path",
        "candidate_qualname",
        "guard_operator",
        "default_parameter",
        "expression_payload",
        "policy_hash",
        "import_name",
        "import_candidate_module",
    ),
)
def test_hypothesis_compat_alias_rejects_hostile_metadata_without_callbacks(
    name: str,
    attack_kind: str,
) -> None:
    module, policy, binding, _provider, provider_value = (
        _hypothesis_compat_stdlib_alias_evidence(name)
    )
    callbacks: list[str] = []

    class HostileString(str):
        def __eq__(self, _other: object) -> bool:
            callbacks.append("eq")
            return True

        def __ne__(self, _other: object) -> bool:
            callbacks.append("ne")
            return False

        def __hash__(self) -> int:
            callbacks.append("hash")
            return str.__hash__(self)

        def __bool__(self) -> bool:
            callbacks.append("bool")
            return True

        def __repr__(self) -> str:
            callbacks.append("repr")
            return "hostile"

    class HostileTuple(tuple):
        def __iter__(self):
            callbacks.append("iter")
            return tuple.__iter__(self)

        def __getitem__(self, index: object) -> object:
            callbacks.append("getitem")
            return tuple.__getitem__(self, index)

        def __len__(self) -> int:
            callbacks.append("len")
            return tuple.__len__(self)

        def __eq__(self, _other: object) -> bool:
            callbacks.append("eq")
            return True

        def __hash__(self) -> int:
            callbacks.append("hash")
            return tuple.__hash__(self)

        def __repr__(self) -> str:
            callbacks.append("repr")
            return "hostile"

    class HostileList(list):
        def __iter__(self):
            callbacks.append("iter")
            return list.__iter__(self)

        def __getitem__(self, index: object) -> object:
            callbacks.append("getitem")
            return list.__getitem__(self, index)

        def __len__(self) -> int:
            callbacks.append("len")
            return list.__len__(self)

        def __eq__(self, _other: object) -> bool:
            callbacks.append("eq")
            return True

        def __repr__(self) -> str:
            callbacks.append("repr")
            return "hostile"

    candidate = binding.candidates[0]
    guard = candidate.guards[0]
    semantics = candidate.function_semantics
    assert semantics is not None
    default = semantics.defaults[0]
    expression = default.expression
    provider_name = "dataclasses" if name == "dataclass_asdict" else "itertools"
    import_binding = next(
        item for item in policy.imports if item.name == provider_name
    )
    import_candidate = import_binding.candidates[0]
    if attack_kind == "binding_path":
        target, field, replacement = binding, "path", HostileTuple(binding.path)
    elif attack_kind == "candidate_qualname":
        target, field, replacement = (
            candidate,
            "qualname",
            HostileString(candidate.qualname),
        )
    elif attack_kind == "guard_operator":
        target, field, replacement = (
            guard,
            "operator",
            HostileString(guard.operator),
        )
    elif attack_kind == "default_parameter":
        target, field, replacement = (
            default,
            "parameter",
            HostileString(default.parameter),
        )
    elif attack_kind == "expression_payload":
        replacement = (
            HostileTuple(expression.payload)
            if type(expression.payload) is tuple
            else HostileList(expression.payload)
        )
        target, field = expression, "payload"
    elif attack_kind == "policy_hash":
        target, field, replacement = (
            policy,
            "source_ast_sha256",
            HostileString(policy.source_ast_sha256),
        )
    elif attack_kind == "import_name":
        target, field, replacement = (
            import_binding,
            "name",
            HostileString(import_binding.name),
        )
    elif attack_kind == "import_candidate_module":
        assert import_candidate.module is not None
        target, field, replacement = (
            import_candidate,
            "module",
            HostileString(import_candidate.module),
        )
    else:
        raise AssertionError(attack_kind)
    original = object.__getattribute__(target, field)
    object.__setattr__(target, field, replacement)
    callbacks.clear()
    try:
        with pytest.raises(MutationToolchainError):
            mutation_toolchain._exact_hypothesis_compat_inactive_stdlib_alias_expected_value(
                module,
                policy=policy,
                source_binding=binding,
            )
    finally:
        object.__setattr__(target, field, original)
    assert callbacks == []
    assert (
        mutation_toolchain._exact_hypothesis_compat_inactive_stdlib_alias_expected_value(
            module,
            policy=policy,
            source_binding=binding,
        )
        is provider_value
    )


def test_hypothesis_compat_alias_rejects_slot_descriptor_replacement_without_callbacks(
) -> None:
    module, policy, binding, _provider, provider_value = (
        _hypothesis_compat_stdlib_alias_evidence("dataclass_asdict")
    )
    callbacks: list[str] = []
    binding_type = mutation_toolchain._SourceBinding
    original = vars(binding_type)["path"]

    def hostile_path(_binding: object) -> tuple[str, ...]:
        callbacks.append("path")
        return ("dataclass_asdict",)

    type.__setattr__(binding_type, "path", property(hostile_path))
    callbacks.clear()
    try:
        with pytest.raises(MutationToolchainError, match="descriptor changed"):
            mutation_toolchain._exact_hypothesis_compat_inactive_stdlib_alias_expected_value(
                module,
                policy=policy,
                source_binding=binding,
            )
    finally:
        type.__setattr__(binding_type, "path", original)
    assert callbacks == []
    assert (
        mutation_toolchain._exact_hypothesis_compat_inactive_stdlib_alias_expected_value(
            module,
            policy=policy,
            source_binding=binding,
        )
        is provider_value
    )


@pytest.mark.parametrize(
    "attack_source",
    (
        """
original = dataclasses.asdict
def counterfeit(*args, **kwargs):
    callbacks.append("asdict")
    return original(*args, **kwargs)
counterfeit.__module__ = "dataclasses"
counterfeit.__name__ = "asdict"
counterfeit.__qualname__ = "asdict"
dataclasses.asdict = counterfeit
compat.dataclass_asdict = counterfeit
""",
        """
from types import FunctionType
original = dataclasses.asdict
counterfeit = FunctionType(
    original.__code__,
    original.__globals__,
    original.__name__,
    original.__defaults__,
    original.__closure__,
)
counterfeit.__kwdefaults__ = original.__kwdefaults__
counterfeit.__dict__.update(original.__dict__)
counterfeit.__annotations__ = original.__annotations__
dataclasses.asdict = counterfeit
compat.dataclass_asdict = counterfeit
""",
        """
from types import ModuleType
counterfeit = ModuleType("dataclasses")
vars(counterfeit).update(vars(dataclasses))
sys.modules["dataclasses"] = counterfeit
compat.dataclasses = counterfeit
compat.dataclass_asdict = counterfeit.asdict
""",
        """
class counterfeit_batched:
    __module__ = "itertools"
    __qualname__ = "batched"
    def __new__(cls, *args, **kwargs):
        callbacks.append("batched")
        return object.__new__(cls)
itertools.batched = counterfeit_batched
compat.batched = counterfeit_batched
""",
        """
from types import ModuleType
counterfeit = ModuleType("itertools")
vars(counterfeit).update(vars(itertools))
sys.modules["itertools"] = counterfeit
compat.itertools = counterfeit
compat.batched = counterfeit.batched
""",
    ),
    ids=(
        "hostile_asdict",
        "exact_asdict_clone",
        "copied_dataclasses_module",
        "python_batched",
        "copied_itertools_module",
    ),
)
def test_hypothesis_compat_alias_rejects_preimport_provider_self_blessing(
    attack_source: str,
) -> None:
    code = f"""
from tests._pytest_plugins import determinism
from hypothesis import settings
settings.load_profile("moira-ci")
determinism.snapshot_hypothesis_policy()
import dataclasses
import hypothesis.internal.compat as compat
import itertools
import sys
callbacks = []
{attack_source}
callbacks.clear()
try:
    from tests.support import mutation_toolchain as toolchain
except Exception as exc:
    assert type(exc).__name__ == "MutationToolchainError", type(exc).__name__
else:
    raise AssertionError(toolchain)
assert callbacks == [], callbacks
"""
    completed = subprocess.run(
        [sys.executable, "-B", "-c", code],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=_SUBPROCESS_TIMEOUT_SECONDS,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_hypothesis_coverage_disabled_outcome_is_exact_and_seals_twice(
) -> None:
    module, policy, bindings, record = _hypothesis_coverage_source_evidence()
    assert record.source_sha256 == (
        "d504ab82b968411933a5872b4fb5277fa35322f2e449d336906c800c23606a74"
    )
    assert record.source_ast_sha256 == (
        "93e41c4daf55340d9b8e2c4ddd3bb145a90af32dc96e27afbce8604b75acfff0"
    )
    assert isinstance(record.owner_anchor, tuple)
    assert len(record.owner_anchor) == 14
    assert len(record.function_fingerprints) == 4
    assert record.owner_anchor[0] is module
    assert record.owner_anchor[1] is False
    assert record.owner_anchor[3] is record.getenv
    assert record.owner_anchor[4] is record.getenv_code
    assert record.owner_anchor[6] is record.check_function
    assert record.owner_anchor[7] is record.check_function_code
    assert record.owner_anchor[8] is record.check
    assert record.owner_anchor[9] is record.check_code
    assert record.owner_anchor[10] is record.raw_check
    assert record.owner_anchor[11] is record.raw_check_code
    assert record.owner_anchor[12] is record.check_closure
    assert vars(record.check)["__wrapped__"] is record.raw_check
    assert len(record.check_closure) == 1
    assert type(record.check_closure[0]) is CellType
    assert record.check_closure[0].cell_contents is record.raw_check
    assert (
        mutation_toolchain._active_source_binding_candidate(
            module,
            policy=policy,
            binding=bindings["check"],
        )
        is bindings["check"].candidates[1]
    )
    assert (
        mutation_toolchain._active_source_binding_candidate(
            module,
            policy=policy,
            binding=bindings["check_function"],
        )
        is bindings["check_function"].candidates[1]
    )
    assert (
        mutation_toolchain._active_source_binding_candidate(
            module,
            policy=policy,
            binding=bindings["check_block"],
        )
        is None
    )
    assert (
        mutation_toolchain._active_source_binding_candidate(
            module,
            policy=policy,
            binding=bindings["record_branch"],
        )
        is None
    )
    for _attempt in range(2):
        assert _verify_hypothesis_coverage_surface(module, policy) is record


def test_hypothesis_coverage_guard_does_not_reread_post_import_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module, policy, _bindings, record = _hypothesis_coverage_source_evidence()
    monkeypatch.setenv("HYPOTHESIS_INTERNAL_COVERAGE", "true")
    assert os.environ["HYPOTHESIS_INTERNAL_COVERAGE"] == "true"
    assert _verify_hypothesis_coverage_surface(module, policy) is record
    assert record.flag is False


def test_hypothesis_coverage_rejects_coordinated_raw_check_clone_before_and_after_seal(
) -> None:
    module, policy, _bindings, record = _hypothesis_coverage_source_evidence()
    for attempt in range(2):
        if attempt:
            assert _verify_hypothesis_coverage_surface(module, policy) is record
        clone = _exact_function_clone(record.raw_check)
        function_namespace = vars(record.check)
        closure_cell = record.check_closure[0]
        original_wrapped = function_namespace["__wrapped__"]
        original_contents = closure_cell.cell_contents
        function_namespace["__wrapped__"] = clone
        closure_cell.cell_contents = clone
        try:
            with pytest.raises(MutationToolchainError):
                mutation_toolchain._verify_eager_hypothesis_coverage_disabled_outcome(
                    policy=policy,
                )
        finally:
            function_namespace["__wrapped__"] = original_wrapped
            closure_cell.cell_contents = original_contents
        assert _verify_hypothesis_coverage_surface(module, policy) is record


def test_hypothesis_coverage_guard_dispatchers_reject_replacement_without_callbacks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module, policy, bindings, _record = _hypothesis_coverage_source_evidence()
    guard = bindings["check_function"].candidates[1].guards[0]
    assert type(guard) is mutation_toolchain._SourceExpressionGuard
    callbacks: list[str] = []

    def forged(*_args: object, **_kwargs: object) -> object:
        callbacks.append("forged")
        return False

    with monkeypatch.context() as attack:
        attack.setattr(mutation_toolchain, "_closed_source_reference", forged)
        callbacks.clear()
        with pytest.raises(MutationToolchainError):
            mutation_toolchain._closed_source_expression_value(
                module,
                policy=policy,
                expression=guard.expression,
                import_sentinels={},
            )
    assert callbacks == []

    with monkeypatch.context() as attack:
        attack.setattr(
            mutation_toolchain,
            "_closed_source_expression_value",
            forged,
        )
        callbacks.clear()
        with pytest.raises(MutationToolchainError):
            mutation_toolchain._active_source_binding_candidate(
                module,
                policy=policy,
                binding=bindings["check_function"],
            )
    assert callbacks == []

    with monkeypatch.context() as attack:
        attack.setattr(
            mutation_toolchain,
            "_active_source_binding_candidate",
            forged,
        )
        callbacks.clear()
        with pytest.raises(MutationToolchainError):
            _verify_selected_binding(
                "hypothesis.internal.coverage",
                "check_function",
                admitted_module_names=("contextlib",),
            )
    assert callbacks == []

    with monkeypatch.context() as attack:
        attack.setattr(
            mutation_toolchain,
            "_verify_eager_hypothesis_coverage_disabled_outcome",
            forged,
        )
        callbacks.clear()
        with pytest.raises(MutationToolchainError):
            mutation_toolchain._closed_source_reference(
                module,
                policy=policy,
                reference=("IN_COVERAGE_TESTS",),
                import_sentinels={},
            )
    assert callbacks == []


@pytest.mark.parametrize(
    "attack_kind",
    (
        "getenv_code",
        "check_function_code",
        "check_code",
        "raw_check_code",
        "check_wrapped",
        "check_closure",
    ),
)
def test_hypothesis_coverage_rejects_function_and_closure_drift_before_and_after_seal(
    attack_kind: str,
) -> None:
    module, policy, _bindings, record = _hypothesis_coverage_source_evidence()
    for attempt in range(2):
        if attempt:
            assert _verify_hypothesis_coverage_surface(module, policy) is record
        function: FunctionType | None = None
        original_code: CodeType | None = None
        check_namespace = vars(record.check)
        closure_cell = record.check_closure[0]
        original_wrapped = check_namespace["__wrapped__"]
        original_contents = closure_cell.cell_contents
        if attack_kind == "getenv_code":
            function = record.getenv
        elif attack_kind == "check_function_code":
            function = record.check_function
        elif attack_kind == "check_code":
            function = record.check
        elif attack_kind == "raw_check_code":
            function = record.raw_check
        elif attack_kind == "check_wrapped":
            check_namespace["__wrapped__"] = _exact_function_clone(
                record.raw_check
            )
        elif attack_kind == "check_closure":
            closure_cell.cell_contents = _exact_function_clone(record.raw_check)
        else:
            raise AssertionError(attack_kind)
        if function is not None:
            original_code = function.__code__
            function.__code__ = original_code.replace()
        try:
            with pytest.raises(MutationToolchainError):
                mutation_toolchain._verify_eager_hypothesis_coverage_disabled_outcome(
                    policy=policy,
                )
        finally:
            if function is not None and original_code is not None:
                function.__code__ = original_code
            check_namespace["__wrapped__"] = original_wrapped
            closure_cell.cell_contents = original_contents
        assert _verify_hypothesis_coverage_surface(module, policy) is record


@pytest.mark.parametrize(
    ("attack_kind", "replacement"),
    (
        ("flag", True),
        ("flag", 0),
        ("written", object()),
        ("record_branch", object()),
        ("check_block", object()),
    ),
    ids=(
        "flag_true",
        "flag_zero",
        "written",
        "record_branch",
        "check_block",
    ),
)
def test_hypothesis_coverage_rejects_enabled_residue_before_and_after_seal(
    attack_kind: str,
    replacement: object,
) -> None:
    module, policy, _bindings, record = _hypothesis_coverage_source_evidence()
    namespace = vars(module)
    for attempt in range(2):
        if attempt:
            assert _verify_hypothesis_coverage_surface(module, policy) is record
        name = "IN_COVERAGE_TESTS" if attack_kind == "flag" else attack_kind
        present = name in namespace
        original = namespace.get(name)
        namespace[name] = replacement
        try:
            with pytest.raises(MutationToolchainError):
                mutation_toolchain._verify_eager_hypothesis_coverage_disabled_outcome(
                    policy=policy,
                )
        finally:
            if present:
                namespace[name] = original
            else:
                namespace.pop(name, None)
        assert _verify_hypothesis_coverage_surface(module, policy) is record


@pytest.mark.parametrize(
    "consumer_name",
    (
        "hypothesis.internal.validation",
        "hypothesis.strategies._internal.strategies",
    ),
)
def test_hypothesis_coverage_rejects_consumer_drift_before_and_after_seal(
    consumer_name: str,
) -> None:
    module, policy, _bindings, record = _hypothesis_coverage_source_evidence()
    consumer = import_module(consumer_name)
    namespace = vars(consumer)
    original = namespace["check_function"]
    assert original is record.check_function
    for attempt in range(2):
        if attempt:
            assert _verify_hypothesis_coverage_surface(module, policy) is record
        namespace["check_function"] = _exact_function_clone(
            record.check_function
        )
        try:
            with pytest.raises(MutationToolchainError):
                mutation_toolchain._verify_eager_hypothesis_coverage_disabled_outcome(
                    policy=policy,
                )
        finally:
            namespace["check_function"] = original
        assert _verify_hypothesis_coverage_surface(module, policy) is record


def test_hypothesis_coverage_rejects_record_and_helper_self_blessing_without_callbacks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _module, policy, _bindings, record = _hypothesis_coverage_source_evidence()
    with monkeypatch.context() as attack:
        attack.setattr(
            mutation_toolchain,
            "_EAGER_HYPOTHESIS_COVERAGE_DISABLED_OUTCOME",
            replace(record),
        )
        with pytest.raises(MutationToolchainError):
            mutation_toolchain._exact_eager_hypothesis_coverage_disabled_outcome()

    callbacks: list[str] = []

    def forged(*_args: object, **_kwargs: object) -> object:
        callbacks.append("forged")
        return record

    for helper_name in (
        "_exact_eager_hypothesis_coverage_disabled_outcome",
        "_verify_hypothesis_coverage_function_fingerprint",
        "_verify_hypothesis_coverage_source_policy",
        "_exact_source_record_field",
        "_stable_policy_bytes",
        "_sha256_bytes",
        "_source_ast_sha256",
        "_normalized_code_sha256",
    ):
        with monkeypatch.context() as attack:
            attack.setattr(mutation_toolchain, helper_name, forged)
            callbacks.clear()
            with pytest.raises(MutationToolchainError):
                mutation_toolchain._verify_eager_hypothesis_coverage_disabled_outcome(
                    policy=policy,
                )
        assert callbacks == [], helper_name


@pytest.mark.parametrize(
    "attack_kind",
    (
        "module_name",
        "getenv_module",
        "policy_hash",
        "binding_path",
        "expression_kind",
        "expression_payload",
        "record_source_hash",
    ),
)
def test_hypothesis_coverage_rejects_hostile_metadata_without_callbacks(
    attack_kind: str,
) -> None:
    module, policy, bindings, record = _hypothesis_coverage_source_evidence()
    callbacks: list[str] = []

    class HostileString(str):
        def __eq__(self, _other: object) -> bool:
            callbacks.append("eq")
            return True

        def __ne__(self, _other: object) -> bool:
            callbacks.append("ne")
            return False

        def __hash__(self) -> int:
            callbacks.append("hash")
            return str.__hash__(self)

        def __bool__(self) -> bool:
            callbacks.append("bool")
            return True

        def __repr__(self) -> str:
            callbacks.append("repr")
            return "hostile"

    class HostileTuple(tuple):
        def __iter__(self):
            callbacks.append("iter")
            return tuple.__iter__(self)

        def __getitem__(self, index: object) -> object:
            callbacks.append("getitem")
            return tuple.__getitem__(self, index)

        def __len__(self) -> int:
            callbacks.append("len")
            return tuple.__len__(self)

        def __eq__(self, _other: object) -> bool:
            callbacks.append("eq")
            return True

        def __hash__(self) -> int:
            callbacks.append("hash")
            return tuple.__hash__(self)

        def __repr__(self) -> str:
            callbacks.append("repr")
            return "hostile"

    guard = bindings["check_function"].candidates[1].guards[0]
    assert type(guard) is mutation_toolchain._SourceExpressionGuard
    expression = guard.expression
    restore_mapping: dict[str, object] | None = None
    restore_object: object | None = None
    if attack_kind == "module_name":
        restore_mapping = vars(module)
        field = "__name__"
        original = restore_mapping[field]
        restore_mapping[field] = HostileString(module.__name__)
    elif attack_kind == "getenv_module":
        restore_object, field = record.getenv, "__module__"
        original = object.__getattribute__(restore_object, field)
        object.__setattr__(restore_object, field, HostileString(original))
    elif attack_kind == "policy_hash":
        restore_object, field = policy, "source_ast_sha256"
        original = object.__getattribute__(restore_object, field)
        object.__setattr__(restore_object, field, HostileString(original))
    elif attack_kind == "binding_path":
        restore_object, field = bindings["check_function"], "path"
        original = object.__getattribute__(restore_object, field)
        object.__setattr__(restore_object, field, HostileTuple(original))
    elif attack_kind == "expression_kind":
        restore_object, field = expression, "kind"
        original = object.__getattribute__(restore_object, field)
        object.__setattr__(restore_object, field, HostileString(original))
    elif attack_kind == "expression_payload":
        restore_object, field = expression, "payload"
        original = object.__getattribute__(restore_object, field)
        object.__setattr__(restore_object, field, HostileTuple(original))
    elif attack_kind == "record_source_hash":
        restore_object, field = record, "source_sha256"
        original = object.__getattribute__(restore_object, field)
        object.__setattr__(restore_object, field, HostileString(original))
    else:
        raise AssertionError(attack_kind)
    callbacks.clear()
    try:
        with pytest.raises(MutationToolchainError):
            mutation_toolchain._verify_eager_hypothesis_coverage_disabled_outcome(
                policy=policy,
            )
    finally:
        if restore_mapping is not None:
            dict.__setitem__(restore_mapping, field, original)
        elif restore_object is not None:
            object.__setattr__(restore_object, field, original)
    assert callbacks == []
    assert _verify_hypothesis_coverage_surface(module, policy) is record


def test_hypothesis_coverage_rejects_source_descriptor_replacement_without_callbacks(
) -> None:
    _module, policy, bindings, record = _hypothesis_coverage_source_evidence()
    guard = bindings["check_function"].candidates[1].guards[0]
    assert type(guard) is mutation_toolchain._SourceExpressionGuard
    expression_type = mutation_toolchain._SourceExpression
    original_descriptor = vars(expression_type)["kind"]
    callbacks: list[str] = []

    def hostile_kind(_expression: object) -> str:
        callbacks.append("kind")
        return "reference"

    type.__setattr__(expression_type, "kind", property(hostile_kind))
    callbacks.clear()
    try:
        with pytest.raises(MutationToolchainError, match="descriptor changed"):
            mutation_toolchain._verify_eager_hypothesis_coverage_disabled_outcome(
                policy=policy,
            )
    finally:
        type.__setattr__(expression_type, "kind", original_descriptor)
    assert callbacks == []
    assert (
        mutation_toolchain._verify_eager_hypothesis_coverage_disabled_outcome(
            policy=policy,
        )
        is record
    )


@pytest.mark.parametrize(
    "attack_source",
    (
        """
from types import FunctionType
public_check = coverage.check
raw_check = vars(public_check)["__wrapped__"]
clone = FunctionType(
    raw_check.__code__,
    raw_check.__globals__,
    raw_check.__name__,
    raw_check.__defaults__,
    raw_check.__closure__,
)
clone.__kwdefaults__ = raw_check.__kwdefaults__
clone.__dict__.update(raw_check.__dict__)
clone.__module__ = raw_check.__module__
clone.__qualname__ = raw_check.__qualname__
vars(public_check)["__wrapped__"] = clone
public_check.__closure__[0].cell_contents = clone
""",
        """
from types import FunctionType
original = os.getenv
clone = FunctionType(
    original.__code__,
    original.__globals__,
    original.__name__,
    original.__defaults__,
    original.__closure__,
)
clone.__kwdefaults__ = original.__kwdefaults__
clone.__dict__.update(original.__dict__)
clone.__module__ = original.__module__
clone.__qualname__ = original.__qualname__
os.getenv = clone
""",
        """
class HostileString(str):
    def __eq__(self, other):
        callbacks.append("eq")
        return True
    def __hash__(self):
        callbacks.append("hash")
        return str.__hash__(self)
    def __repr__(self):
        callbacks.append("repr")
        return "hostile"
os.getenv.__module__ = HostileString("os")
""",
        """
from types import FunctionType
public_check = coverage.check
raw_check = vars(public_check)["__wrapped__"]
clone = FunctionType(
    raw_check.__code__,
    raw_check.__globals__,
    raw_check.__name__,
    raw_check.__defaults__,
    raw_check.__closure__,
)
clone.__kwdefaults__ = raw_check.__kwdefaults__
clone.__dict__.update(raw_check.__dict__)
clone.__module__ = raw_check.__module__
clone.__qualname__ = raw_check.__qualname__
vars(public_check)["__wrapped__"] = clone
public_check.__closure__[0].cell_contents = clone
determinism._HYPOTHESIS_COVERAGE_DISABLED_OUTCOME = (
    determinism._capture_hypothesis_coverage_disabled_outcome()
)
""",
    ),
    ids=(
        "raw_check_clone",
        "getenv_clone",
        "getenv_hostile_metadata",
        "anchor_recapture",
    ),
)
def test_hypothesis_coverage_rejects_preimport_self_blessing_without_callbacks(
    attack_source: str,
) -> None:
    environment = os.environ.copy()
    environment.pop("HYPOTHESIS_INTERNAL_COVERAGE", None)
    code = f"""
from tests._pytest_plugins import determinism
from hypothesis import settings
settings.load_profile("moira-ci")
determinism.snapshot_hypothesis_policy()
from hypothesis.internal import coverage
import os
callbacks = []
{attack_source}
callbacks.clear()
try:
    from tests.support import mutation_toolchain as toolchain
except Exception as exc:
    assert type(exc).__name__ == "MutationToolchainError", type(exc).__name__
else:
    raise AssertionError(toolchain)
assert callbacks == [], callbacks
"""
    completed = subprocess.run(
        [sys.executable, "-B", "-c", code],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=_SUBPROCESS_TIMEOUT_SECONDS,
        env=environment,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_hypothesis_coverage_rejects_enabled_preimport_mode() -> None:
    environment = os.environ.copy()
    environment["HYPOTHESIS_INTERNAL_COVERAGE"] = "true"
    code = """
try:
    from tests._pytest_plugins import determinism
except Exception as exc:
    assert type(exc).__name__ == "RuntimeError", type(exc).__name__
else:
    raise AssertionError(determinism)
"""
    completed = subprocess.run(
        [sys.executable, "-B", "-c", code],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=_SUBPROCESS_TIMEOUT_SECONDS,
        env=environment,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_hypothesis_coverage_supports_clean_builtin_parent_mode() -> None:
    environment = os.environ.copy()
    environment.pop("HYPOTHESIS_INTERNAL_COVERAGE", None)
    code = """
from tests.support import mutation_toolchain as toolchain
record = toolchain._verify_eager_hypothesis_coverage_disabled_outcome()
assert record.mode == "builtin-only"
assert record.flag is False
assert len(record.function_fingerprints) == 4
assert toolchain._verify_eager_hypothesis_coverage_disabled_outcome() is record
"""
    completed = subprocess.run(
        [sys.executable, "-B", "-c", code],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=_SUBPROCESS_TIMEOUT_SECONDS,
        env=environment,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_hypothesis_entropy_randomlike_alias_is_exact_and_seals_twice() -> None:
    module, policy, bindings, record = (
        _hypothesis_entropy_randomlike_evidence()
    )
    expected = {
        "RandomLike": record.random_class,
        **{
            f"RandomLike.{fingerprint[0]}": fingerprint[1]
            for fingerprint in record.random_method_fingerprints
        },
    }
    for _attempt in range(2):
        assert (
            _verify_hypothesis_entropy_randomlike_surface(module, policy)
            is record
        )
        for path, source_binding in bindings.items():
            assert (
                mutation_toolchain._exact_hypothesis_entropy_randomlike_expected_value(
                    module,
                    policy=policy,
                    source_binding=source_binding,
                )
                is expected[path]
            )
            assert (
                mutation_toolchain._exact_inactive_source_import_expected_value(
                    module,
                    policy=policy,
                    source_binding=source_binding,
                )
                is expected[path]
            )


def test_hypothesis_entropy_compat_flags_are_exact_and_select_refcount_branch_twice() -> None:
    module, policy, binding, record = (
        _hypothesis_entropy_compat_flags_evidence()
    )
    expected = {"PYPY": record.pypy, "GRAALPY": record.graalpy}
    for _attempt in range(2):
        assert (
            _verify_hypothesis_entropy_randomlike_surface(module, policy)
            is record
        )
        assert (
            mutation_toolchain._active_source_binding_candidate(
                module,
                policy=policy,
                binding=binding,
            )
            is binding.candidates[0]
        )
        sentinels: dict[str, tuple[object, str | None]] = {}
        for name, value in expected.items():
            assert value is False
            assert (
                mutation_toolchain._exact_hypothesis_entropy_compat_flag_expected_value(
                    module,
                    policy=policy,
                    root_name=name,
                    provider=record.compat_module,
                    attribute=name,
                )
                is value
            )
            for _seal in range(2):
                assert (
                    mutation_toolchain._closed_source_reference(
                        module,
                        policy=policy,
                        reference=(name,),
                        import_sentinels=sentinels,
                    )
                    is value
                )
            assert sentinels[name][0] is value
            assert sentinels[name][1] is None
        refcount = record.refcount_outcome
        assert type(refcount) is tuple
        assert len(refcount) == 18
        assert refcount[0] is vars(module)["_get_platform_base_refcount"]
        assert type(refcount[8]) is tuple
        assert len(refcount[8]) == 12
        assert refcount[8][0] is object.__getattribute__(
            refcount[0],
            "__annotate__",
        )
        assert type(refcount[16]) is tuple
        assert refcount[16][0] is sys.getrefcount
        assert refcount[16][1] is sys
        assert type(refcount[17]) is int
        assert refcount[17] == 1
        assert type(record.python_implementation_source_path) is type(_ROOT)
        for digest in (
            record.python_implementation_source_sha256,
            record.python_implementation_source_ast_sha256,
            record.python_implementation_source_code_sha256,
            record.refcount_source_code_sha256,
        ):
            assert type(digest) is str
            assert len(digest) == 64
            assert all(character in "0123456789abcdef" for character in digest)


@pytest.mark.parametrize("flag_name", ("PYPY", "GRAALPY"))
@pytest.mark.parametrize(
    "attack_scope",
    ("provider", "consumer", "coordinated"),
)
def test_hypothesis_entropy_compat_flags_reject_provider_consumer_drift_before_and_after_seal(
    flag_name: str,
    attack_scope: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module, policy, _binding, record = (
        _hypothesis_entropy_compat_flags_evidence()
    )
    for attempt in range(2):
        if attempt:
            assert (
                _verify_hypothesis_entropy_randomlike_surface(module, policy)
                is record
            )
        with monkeypatch.context() as attack:
            if attack_scope in {"provider", "coordinated"}:
                attack.setitem(vars(record.compat_module), flag_name, 0)
            if attack_scope in {"consumer", "coordinated"}:
                attack.setitem(vars(module), flag_name, 0)
            with pytest.raises(MutationToolchainError):
                mutation_toolchain._verify_eager_hypothesis_entropy_randomlike_provider()
        assert (
            _verify_hypothesis_entropy_randomlike_surface(module, policy)
            is record
        )


@pytest.mark.parametrize(
    ("attack_kind", "replacement"),
    (
        ("scalar", 0),
        ("scalar", -1),
        ("scalar", True),
        ("scalar", 2**31),
        ("function_clone", None),
        ("function_code", None),
        ("annotate", None),
        ("entropy_sys", None),
        ("sys_getrefcount", None),
    ),
    ids=(
        "scalar_zero",
        "scalar_negative_one",
        "scalar_bool",
        "scalar_large",
        "function_clone",
        "function_code",
        "annotate",
        "entropy_sys",
        "sys_getrefcount",
    ),
)
def test_hypothesis_entropy_refcount_rejects_drift_before_and_after_seal_without_callbacks(
    attack_kind: str,
    replacement: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module, policy, _binding, record = (
        _hypothesis_entropy_compat_flags_evidence()
    )
    function = record.refcount_outcome[0]
    assert type(function) is FunctionType
    callbacks: list[str] = []

    def forged_annotate(_format: int, /) -> dict[str, object]:
        callbacks.append("annotate")
        return {"r": typing.Any, "return": int}

    for attempt in range(2):
        if attempt:
            assert (
                _verify_hypothesis_entropy_randomlike_surface(module, policy)
                is record
            )
        with monkeypatch.context() as attack:
            if attack_kind == "scalar":
                attack.setitem(
                    vars(module),
                    "_PLATFORM_REF_COUNT",
                    replacement,
                )
            elif attack_kind == "function_clone":
                attack.setitem(
                    vars(module),
                    "_get_platform_base_refcount",
                    _exact_function_clone(function),
                )
            elif attack_kind == "function_code":
                attack.setattr(function, "__code__", function.__code__.replace())
            elif attack_kind == "annotate":
                attack.setattr(function, "__annotate__", forged_annotate)
            elif attack_kind == "entropy_sys":
                attack.setitem(vars(module), "sys", ModuleType("sys"))
            elif attack_kind == "sys_getrefcount":
                attack.setattr(sys, "getrefcount", sys.getsizeof)
            else:
                raise AssertionError(attack_kind)
            callbacks.clear()
            with pytest.raises(MutationToolchainError):
                mutation_toolchain._verify_eager_hypothesis_entropy_randomlike_provider()
            assert callbacks == []
        assert (
            _verify_hypothesis_entropy_randomlike_surface(module, policy)
            is record
        )


@pytest.mark.parametrize(
    "attack_kind",
    ("hostile", "clone", "code"),
)
def test_hypothesis_entropy_compat_flags_reject_python_implementation_drift_without_callbacks(
    attack_kind: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module, policy, _binding, record = (
        _hypothesis_entropy_compat_flags_evidence()
    )
    function = record.python_implementation_provider[1]
    assert type(function) is FunctionType
    callbacks: list[str] = []

    def forged() -> str:
        callbacks.append("python_implementation")
        return "CPython"

    with monkeypatch.context() as attack:
        if attack_kind == "hostile":
            attack.setattr(platform, "python_implementation", forged)
        elif attack_kind == "clone":
            attack.setattr(
                platform,
                "python_implementation",
                _exact_function_clone(function),
            )
        elif attack_kind == "code":
            attack.setattr(function, "__code__", function.__code__.replace())
        else:
            raise AssertionError(attack_kind)
        callbacks.clear()
        with pytest.raises(MutationToolchainError):
            mutation_toolchain._verify_eager_hypothesis_entropy_randomlike_provider()
        assert callbacks == []
    assert _verify_hypothesis_entropy_randomlike_surface(module, policy) is record


def test_hypothesis_entropy_compat_flag_dispatchers_reject_replacement_without_callbacks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module, policy, binding, record = (
        _hypothesis_entropy_compat_flags_evidence()
    )
    callbacks: list[str] = []

    def forged(*_args: object, **_kwargs: object) -> object:
        callbacks.append("forged")
        return record

    for helper_name in (
        "_capture_hypothesis_python_implementation_provider",
        "_hypothesis_python_implementation_providers_are_identical",
        "_capture_hypothesis_python_implementation_source_seal",
        "_capture_hypothesis_free_threaded_provider",
        "_hypothesis_free_threaded_providers_are_identical",
        "_capture_hypothesis_entropy_refcount_outcome",
        "_hypothesis_entropy_refcount_outcomes_are_identical",
        "_compiled_named_source_codes",
        "_normalized_code_sha256",
        "_verify_hypothesis_entropy_randomlike_source_topology",
        "_verify_hypothesis_compat_interpreter_flag_topology",
    ):
        with monkeypatch.context() as attack:
            attack.setattr(mutation_toolchain, helper_name, forged)
            callbacks.clear()
            with pytest.raises(MutationToolchainError):
                mutation_toolchain._verify_eager_hypothesis_entropy_randomlike_provider()
        assert callbacks == [], helper_name

    with monkeypatch.context() as attack:
        attack.setattr(
            mutation_toolchain,
            "_exact_hypothesis_entropy_compat_flag_expected_value",
            forged,
        )
        callbacks.clear()
        with pytest.raises(MutationToolchainError):
            mutation_toolchain._closed_source_reference(
                module,
                policy=policy,
                reference=("PYPY",),
                import_sentinels={},
            )
    assert callbacks == []

    guard = binding.candidates[0].guards[0]
    assert type(guard) is mutation_toolchain._SourceExpressionGuard
    with monkeypatch.context() as attack:
        attack.setattr(mutation_toolchain, "_closed_source_reference", forged)
        callbacks.clear()
        with pytest.raises(MutationToolchainError):
            mutation_toolchain._closed_source_expression_value(
                module,
                policy=policy,
                expression=guard.expression,
                import_sentinels={},
            )
    assert callbacks == []

    with monkeypatch.context() as attack:
        attack.setattr(builtins, "vars", forged)
        callbacks.clear()
        with pytest.raises(MutationToolchainError):
            mutation_toolchain._closed_source_reference(
                module,
                policy=policy,
                reference=("PYPY",),
                import_sentinels={},
            )
    assert callbacks == []
    assert _verify_hypothesis_entropy_randomlike_surface(module, policy) is record


@pytest.mark.parametrize(
    "helper_name",
    (
        "_capture_hypothesis_python_implementation_provider",
        "_capture_hypothesis_python_implementation_source_seal",
        "_capture_hypothesis_free_threaded_provider",
        "_capture_hypothesis_entropy_refcount_outcome",
        "_compiled_named_source_codes",
        "_normalized_code_sha256",
    ),
)
def test_hypothesis_entropy_verifier_rejects_in_place_helper_code_mutation_without_callbacks(
    helper_name: str,
) -> None:
    module, policy, _binding, record = (
        _hypothesis_entropy_compat_flags_evidence()
    )
    helper = vars(mutation_toolchain)[helper_name]
    assert type(helper) is FunctionType
    original_code = object.__getattribute__(helper, "__code__")
    callbacks: list[str] = []

    def callback() -> None:
        callbacks.append(helper_name)

    def forged(*_args: object, **_kwargs: object) -> object:
        globals()["_PHASE11_ENTROPY_HELPER_CALLBACK"]()
        return None

    namespace = vars(mutation_toolchain)
    namespace["_PHASE11_ENTROPY_HELPER_CALLBACK"] = callback
    object.__setattr__(helper, "__code__", forged.__code__)
    callbacks.clear()
    try:
        with pytest.raises(
            MutationToolchainError,
            match="eager Hypothesis entropy provider verifier changed",
        ):
            mutation_toolchain._verify_eager_hypothesis_entropy_randomlike_provider()
    finally:
        object.__setattr__(helper, "__code__", original_code)
        dict.__delitem__(namespace, "_PHASE11_ENTROPY_HELPER_CALLBACK")
    assert callbacks == []
    assert _verify_hypothesis_entropy_randomlike_surface(module, policy) is record


def test_hypothesis_entropy_rejects_owner_registry_removal() -> None:
    module, policy, _binding, record = (
        _hypothesis_entropy_compat_flags_evidence()
    )
    assert record.mode == "moira-harness"
    assert type(record.owner_registry) is tuple
    assert record.owner_registry
    for owner_name, owner in record.owner_registry:
        assert sys.modules[owner_name] is owner
        removed = sys.modules.pop(owner_name)
        try:
            with pytest.raises(
                MutationToolchainError,
                match="eager Hypothesis entropy bootstrap anchor changed",
            ):
                mutation_toolchain._verify_eager_hypothesis_entropy_randomlike_provider()
        finally:
            sys.modules[owner_name] = removed
        assert removed is owner
        assert _verify_hypothesis_entropy_randomlike_surface(module, policy) is record


def test_hypothesis_entropy_owner_accessor_code_is_checked_before_use() -> None:
    module, policy, _binding, record = (
        _hypothesis_entropy_compat_flags_evidence()
    )
    accessor = record.owner_accessor
    assert type(accessor) is FunctionType
    assert type(record.owner_module) is ModuleType
    original_code = object.__getattribute__(accessor, "__code__")
    callbacks: list[str] = []

    def callback() -> None:
        callbacks.append("owner_accessor")

    def forged(_anchor: object, _capture: object, _namespace: object) -> object:
        globals()["_PHASE11_OWNER_ACCESSOR_CALLBACK"]()
        return _anchor

    owner_namespace = vars(record.owner_module)
    owner_namespace["_PHASE11_OWNER_ACCESSOR_CALLBACK"] = callback
    object.__setattr__(accessor, "__code__", forged.__code__)
    callbacks.clear()
    try:
        with pytest.raises(
            MutationToolchainError,
            match="eager Hypothesis entropy bootstrap anchor changed",
        ):
            mutation_toolchain._verify_eager_hypothesis_entropy_randomlike_provider()
    finally:
        object.__setattr__(accessor, "__code__", original_code)
        dict.__delitem__(owner_namespace, "_PHASE11_OWNER_ACCESSOR_CALLBACK")
    assert callbacks == []
    assert _verify_hypothesis_entropy_randomlike_surface(module, policy) is record


def test_hypothesis_entropy_record_accessor_code_is_checked_before_use() -> None:
    module, policy, _binding, record = (
        _hypothesis_entropy_compat_flags_evidence()
    )
    accessor = mutation_toolchain._exact_eager_hypothesis_entropy_randomlike_provider
    assert type(accessor) is FunctionType
    original_code = object.__getattribute__(accessor, "__code__")
    callbacks: list[str] = []

    def callback() -> None:
        callbacks.append("record_accessor")

    def forged(
        _record: object,
        _record_type: object,
        _slots: object,
        _fingerprint: object,
    ) -> object:
        globals()["_PHASE11_RECORD_ACCESSOR_CALLBACK"]()
        return _record

    namespace = vars(mutation_toolchain)
    namespace["_PHASE11_RECORD_ACCESSOR_CALLBACK"] = callback
    object.__setattr__(accessor, "__code__", forged.__code__)
    callbacks.clear()
    try:
        with pytest.raises(
            MutationToolchainError,
            match="eager Hypothesis entropy provider verifier changed",
        ):
            mutation_toolchain._verify_eager_hypothesis_entropy_randomlike_provider()
    finally:
        object.__setattr__(accessor, "__code__", original_code)
        dict.__delitem__(namespace, "_PHASE11_RECORD_ACCESSOR_CALLBACK")
    assert callbacks == []
    assert _verify_hypothesis_entropy_randomlike_surface(module, policy) is record


def test_hypothesis_entropy_free_threaded_provider_rejects_coordinated_drift() -> None:
    module, policy, _binding, record = (
        _hypothesis_entropy_compat_flags_evidence()
    )
    sysconfig_module, config_vars, raw_value, expected = (
        record.free_threaded_provider
    )
    assert type(sysconfig_module) is ModuleType
    assert type(config_vars) is dict
    assert expected is record.free_threaded_cpython
    replacement = 0 if raw_value == 1 else 1
    sentinel = object()
    original = dict.get(config_vars, "Py_GIL_DISABLED", sentinel)
    config_vars["Py_GIL_DISABLED"] = replacement
    vars(record.compat_module)["FREE_THREADED_CPYTHON"] = bool(replacement)
    vars(module)["FREE_THREADED_CPYTHON"] = bool(replacement)
    try:
        with pytest.raises(MutationToolchainError):
            mutation_toolchain._verify_eager_hypothesis_entropy_randomlike_provider()
    finally:
        if original is sentinel:
            dict.__delitem__(config_vars, "Py_GIL_DISABLED")
        else:
            config_vars["Py_GIL_DISABLED"] = original
        vars(record.compat_module)["FREE_THREADED_CPYTHON"] = expected
        vars(module)["FREE_THREADED_CPYTHON"] = expected
    assert _verify_hypothesis_entropy_randomlike_surface(module, policy) is record


@pytest.mark.parametrize(
    ("record_type_name", "field_name"),
    (
        ("_SourceImportBinding", "name"),
        ("_SourceImportCandidate", "attribute"),
    ),
)
def test_hypothesis_entropy_compat_flags_reject_source_descriptor_replacement_without_callbacks(
    record_type_name: str,
    field_name: str,
) -> None:
    module, policy, _binding, record = (
        _hypothesis_entropy_compat_flags_evidence()
    )
    record_type = vars(mutation_toolchain)[record_type_name]
    original_descriptor = vars(record_type)[field_name]
    callbacks: list[str] = []

    def hostile_field(_record: object) -> str:
        callbacks.append(field_name)
        return field_name

    type.__setattr__(record_type, field_name, property(hostile_field))
    callbacks.clear()
    try:
        with pytest.raises(MutationToolchainError, match="descriptor changed"):
            mutation_toolchain._closed_source_reference(
                module,
                policy=policy,
                reference=("PYPY",),
                import_sentinels={},
            )
    finally:
        type.__setattr__(record_type, field_name, original_descriptor)
    assert callbacks == []
    assert _verify_hypothesis_entropy_randomlike_surface(module, policy) is record


@pytest.mark.parametrize(
    "attack_kind",
    (
        "entropy_alias",
        "entropy_random_alias",
        "entropy_random_class_alias",
        "typing_flag",
        "entropy_flag",
        "protocol_residue",
        "random_method_clone",
        "random_method_code",
        "coordinated_random_class",
        "random_module_clone",
        "typing_module_clone",
    ),
)
def test_hypothesis_entropy_randomlike_rejects_provider_drift_before_and_after_seal(
    attack_kind: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module, policy, _bindings, record = (
        _hypothesis_entropy_randomlike_evidence()
    )
    for attempt in range(2):
        if attempt:
            assert (
                _verify_hypothesis_entropy_randomlike_surface(module, policy)
                is record
            )
        with monkeypatch.context() as attack:
            if attack_kind == "entropy_alias":
                attack.setitem(vars(module), "RandomLike", object())
            elif attack_kind == "entropy_random_alias":
                attack.setitem(vars(module), "random", ModuleType("random"))
            elif attack_kind == "entropy_random_class_alias":
                attack.setitem(vars(module), "Random", object())
            elif attack_kind == "typing_flag":
                attack.setitem(vars(record.typing_module), "TYPE_CHECKING", 0)
            elif attack_kind == "entropy_flag":
                attack.setitem(vars(module), "TYPE_CHECKING", 0)
            elif attack_kind == "protocol_residue":
                attack.setitem(vars(module), "Protocol", object())
            elif attack_kind == "random_method_clone":
                attack.setattr(
                    record.random_class,
                    "seed",
                    _exact_function_clone(vars(record.random_class)["seed"]),
                )
            elif attack_kind == "random_method_code":
                method = vars(record.random_class)["seed"]
                attack.setattr(method, "__code__", method.__code__.replace())
            elif attack_kind == "coordinated_random_class":
                forged = type("Random", (record.random_class,), {})
                forged.__module__ = "random"
                attack.setitem(vars(record.random_module), "Random", forged)
                attack.setitem(vars(module), "Random", forged)
                attack.setitem(vars(module), "RandomLike", forged)
            elif attack_kind == "random_module_clone":
                forged_module = ModuleType("random")
                vars(forged_module).update(vars(record.random_module))
                attack.setitem(sys.modules, "random", forged_module)
                attack.setitem(vars(module), "random", forged_module)
            elif attack_kind == "typing_module_clone":
                forged_module = ModuleType("typing")
                vars(forged_module).update(vars(record.typing_module))
                attack.setitem(sys.modules, "typing", forged_module)
            else:
                raise AssertionError(attack_kind)
            with pytest.raises(MutationToolchainError):
                mutation_toolchain._verify_eager_hypothesis_entropy_randomlike_provider()
        assert (
            _verify_hypothesis_entropy_randomlike_surface(module, policy)
            is record
        )


def test_hypothesis_entropy_randomlike_dispatchers_reject_replacement_without_callbacks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module, policy, bindings, record = (
        _hypothesis_entropy_randomlike_evidence()
    )
    source_binding = bindings["RandomLike"]
    callbacks: list[str] = []

    def forged(*_args: object, **_kwargs: object) -> object:
        callbacks.append("forged")
        return record.random_class

    for helper_name in (
        "_exact_eager_hypothesis_entropy_randomlike_provider",
        "_verify_eager_hypothesis_entropy_randomlike_provider",
        "_exact_source_record_field",
        "_exact_active_source_type_checking_guard",
        "_capture_hypothesis_entropy_random_method_fingerprints",
        "_hypothesis_entropy_method_fingerprints_are_identical",
        "_hypothesis_entropy_class_items_are_identical",
        "_verify_hypothesis_entropy_randomlike_source_topology",
        "_stable_policy_bytes",
        "_sha256_bytes",
        "_source_ast_sha256",
    ):
        with monkeypatch.context() as attack:
            attack.setattr(mutation_toolchain, helper_name, forged)
            callbacks.clear()
            with pytest.raises(MutationToolchainError):
                mutation_toolchain._exact_hypothesis_entropy_randomlike_expected_value(
                    module,
                    policy=policy,
                    source_binding=source_binding,
                )
        assert callbacks == [], helper_name

    with monkeypatch.context() as attack:
        attack.setattr(
            mutation_toolchain,
            "_exact_hypothesis_entropy_randomlike_expected_value",
            forged,
        )
        callbacks.clear()
        with pytest.raises(MutationToolchainError):
            mutation_toolchain._exact_inactive_source_import_expected_value(
                module,
                policy=policy,
                source_binding=source_binding,
            )
    assert callbacks == []

    with monkeypatch.context() as attack:
        attack.setattr(mutation_toolchain, "_exact_source_class_guard", forged)
        callbacks.clear()
        assert (
            mutation_toolchain._active_source_binding_candidate(
                module,
                policy=policy,
                binding=source_binding,
            )
            is None
        )
    assert callbacks == []

    with monkeypatch.context() as attack:
        attack.setattr(
            mutation_toolchain,
            "_exact_active_source_type_checking_guard",
            forged,
        )
        callbacks.clear()
        with pytest.raises(MutationToolchainError):
            mutation_toolchain._active_source_binding_candidate(
                module,
                policy=policy,
                binding=source_binding,
            )
    assert callbacks == []


def test_hypothesis_entropy_randomlike_rejects_record_self_blessing() -> None:
    _module, _policy, _bindings, record = (
        _hypothesis_entropy_randomlike_evidence()
    )
    original = mutation_toolchain._EAGER_HYPOTHESIS_ENTROPY_RANDOMLIKE_PROVIDER
    mutation_toolchain._EAGER_HYPOTHESIS_ENTROPY_RANDOMLIKE_PROVIDER = replace(
        record
    )
    try:
        with pytest.raises(MutationToolchainError):
            mutation_toolchain._exact_eager_hypothesis_entropy_randomlike_provider()
    finally:
        mutation_toolchain._EAGER_HYPOTHESIS_ENTROPY_RANDOMLIKE_PROVIDER = (
            original
        )
    assert (
        mutation_toolchain._exact_eager_hypothesis_entropy_randomlike_provider()
        is record
    )


@pytest.mark.parametrize(
    "attack_kind",
    (
        "module_name",
        "binding_path",
        "guard_reference",
        "policy_hash",
        "record_hash",
    ),
)
def test_hypothesis_entropy_randomlike_rejects_hostile_metadata_without_callbacks(
    attack_kind: str,
) -> None:
    module, policy, bindings, record = (
        _hypothesis_entropy_randomlike_evidence()
    )
    source_binding = bindings["RandomLike"]
    guard = source_binding.candidates[0].guards[0]
    callbacks: list[str] = []

    class HostileString(str):
        def __eq__(self, _other: object) -> bool:
            callbacks.append("eq")
            return True

        def __hash__(self) -> int:
            callbacks.append("hash")
            return str.__hash__(self)

        def __repr__(self) -> str:
            callbacks.append("repr")
            return "hostile"

    class HostileTuple(tuple):
        def __iter__(self):
            callbacks.append("iter")
            return tuple.__iter__(self)

        def __len__(self) -> int:
            callbacks.append("len")
            return tuple.__len__(self)

        def __getitem__(self, index: object) -> object:
            callbacks.append("getitem")
            return tuple.__getitem__(self, index)

    restore_mapping: dict[str, object] | None = None
    restore_object: object | None = None
    if attack_kind == "module_name":
        restore_mapping = vars(module)
        field = "__name__"
        original = restore_mapping[field]
        restore_mapping[field] = HostileString(original)
    elif attack_kind == "binding_path":
        restore_object, field = source_binding, "path"
        original = object.__getattribute__(restore_object, field)
        object.__setattr__(restore_object, field, HostileTuple(original))
    elif attack_kind == "guard_reference":
        restore_object, field = guard, "reference"
        original = object.__getattribute__(restore_object, field)
        object.__setattr__(restore_object, field, HostileString(original))
    elif attack_kind == "policy_hash":
        restore_object, field = policy, "source_ast_sha256"
        original = object.__getattribute__(restore_object, field)
        object.__setattr__(restore_object, field, HostileString(original))
    elif attack_kind == "record_hash":
        restore_object, field = record, "source_sha256"
        original = object.__getattribute__(restore_object, field)
        object.__setattr__(restore_object, field, HostileString(original))
    else:
        raise AssertionError(attack_kind)
    callbacks.clear()
    try:
        with pytest.raises(MutationToolchainError):
            mutation_toolchain._exact_hypothesis_entropy_randomlike_expected_value(
                module,
                policy=policy,
                source_binding=source_binding,
            )
    finally:
        if restore_mapping is not None:
            dict.__setitem__(restore_mapping, field, original)
        elif restore_object is not None:
            object.__setattr__(restore_object, field, original)
    assert callbacks == []
    assert (
        _verify_hypothesis_entropy_randomlike_surface(module, policy) is record
    )


@pytest.mark.parametrize(
    "provider_name",
    ("ast.parse", "builtins.compile", "os.fspath", "vars"),
)
def test_hypothesis_entropy_randomlike_rejects_runtime_provider_replacement_without_callbacks(
    provider_name: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _module, _policy, _bindings, record = (
        _hypothesis_entropy_randomlike_evidence()
    )
    callbacks: list[str] = []
    original_vars = vars

    def forged(*args: object, **kwargs: object) -> object:
        callbacks.append(provider_name)
        if provider_name == "ast.parse":
            return record
        if provider_name == "builtins.compile":
            return record
        if provider_name == "os.fspath":
            return str(record.source_path)
        return original_vars(*args, **kwargs)

    with monkeypatch.context() as attack:
        if provider_name == "ast.parse":
            attack.setattr(ast, "parse", forged)
        elif provider_name == "builtins.compile":
            attack.setattr(builtins, "compile", forged)
        elif provider_name == "os.fspath":
            attack.setattr(os, "fspath", forged)
        else:
            attack.setattr(builtins, "vars", forged)
        callbacks.clear()
        with pytest.raises(MutationToolchainError):
            mutation_toolchain._verify_eager_hypothesis_entropy_randomlike_provider()
    assert callbacks == []
    assert (
        mutation_toolchain._verify_eager_hypothesis_entropy_randomlike_provider()
        is record
    )


def test_hypothesis_entropy_randomlike_rejects_source_descriptor_replacement_without_callbacks(
) -> None:
    module, policy, bindings, record = (
        _hypothesis_entropy_randomlike_evidence()
    )
    source_binding = bindings["RandomLike"]
    guard_type = mutation_toolchain._SourceTypeCheckingGuard
    original_descriptor = vars(guard_type)["reference"]
    callbacks: list[str] = []

    def hostile_reference(_guard: object) -> str:
        callbacks.append("reference")
        return "direct"

    type.__setattr__(guard_type, "reference", property(hostile_reference))
    callbacks.clear()
    try:
        with pytest.raises(MutationToolchainError, match="descriptor changed"):
            mutation_toolchain._exact_hypothesis_entropy_randomlike_expected_value(
                module,
                policy=policy,
                source_binding=source_binding,
            )
    finally:
        type.__setattr__(guard_type, "reference", original_descriptor)
    assert callbacks == []
    assert (
        _verify_hypothesis_entropy_randomlike_surface(module, policy) is record
    )


@pytest.mark.parametrize(
    "attack_source",
    (
        """
method = vars(random.Random)["seed"]
method.__code__ = method.__code__.replace()
""",
        """
method = vars(random.Random)["seed"]
clone = FunctionType(
    method.__code__,
    method.__globals__,
    method.__name__,
    method.__defaults__,
    method.__closure__,
)
clone.__kwdefaults__ = method.__kwdefaults__
clone.__module__ = method.__module__
clone.__qualname__ = method.__qualname__
random.Random.seed = clone
""",
        """
method = vars(random.Random)["seed"]
clone = FunctionType(
    method.__code__,
    method.__globals__,
    method.__name__,
    method.__defaults__,
    method.__closure__,
)
clone.__kwdefaults__ = method.__kwdefaults__
clone.__module__ = method.__module__
clone.__qualname__ = method.__qualname__
random.Random.seed = clone
determinism._HYPOTHESIS_ENTROPY_RANDOMLIKE_PROVIDER = (
    determinism._capture_hypothesis_entropy_randomlike_provider()
)
""",
    ),
    ids=("method_code", "method_clone", "anchor_recapture"),
)
def test_hypothesis_entropy_randomlike_rejects_pretoolchain_provider_drift(
    attack_source: str,
) -> None:
    environment = os.environ.copy()
    environment.pop("HYPOTHESIS_INTERNAL_COVERAGE", None)
    code = f"""
from types import FunctionType
from tests._pytest_plugins import determinism
from hypothesis import settings
settings.load_profile("moira-ci")
determinism.snapshot_hypothesis_policy()
import random
{attack_source}
try:
    from tests.support import mutation_toolchain as toolchain
except Exception as exc:
    assert type(exc).__name__ == "MutationToolchainError", type(exc).__name__
else:
    raise AssertionError(toolchain)
"""
    completed = subprocess.run(
        [sys.executable, "-B", "-c", code],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=_SUBPROCESS_TIMEOUT_SECONDS,
        env=environment,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


@pytest.mark.parametrize(
    "attack_source",
    (
        "vars(compat)['PYPY'] = 0\nvars(entropy)['PYPY'] = 0",
        "vars(compat)['GRAALPY'] = 0\nvars(entropy)['GRAALPY'] = 0",
        """
def forged_implementation():
    callbacks.append("python_implementation")
    return "CPython"
platform.python_implementation = forged_implementation
""",
        """
def forged_annotate(format, /):
    callbacks.append("annotate")
    return {"r": object, "return": int}
entropy._get_platform_base_refcount.__annotate__ = forged_annotate
""",
        "entropy._PLATFORM_REF_COUNT = 0",
    ),
    ids=(
        "pypy_zero",
        "graalpy_zero",
        "python_implementation",
        "refcount_annotate",
        "refcount_scalar",
    ),
)
def test_hypothesis_entropy_compat_flags_reject_pretoolchain_drift_without_callbacks(
    attack_source: str,
) -> None:
    environment = os.environ.copy()
    environment.pop("HYPOTHESIS_INTERNAL_COVERAGE", None)
    code = f"""
from tests._pytest_plugins import determinism
from hypothesis import settings
settings.load_profile("moira-ci")
determinism.snapshot_hypothesis_policy()
from hypothesis.internal import compat, entropy
import platform
callbacks = []
{attack_source}
callbacks.clear()
try:
    from tests.support import mutation_toolchain as toolchain
except Exception as exc:
    assert type(exc).__name__ == "MutationToolchainError", type(exc).__name__
else:
    raise AssertionError(toolchain)
assert callbacks == [], callbacks
"""
    completed = subprocess.run(
        [sys.executable, "-B", "-c", code],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=_SUBPROCESS_TIMEOUT_SECONDS,
        env=environment,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_hypothesis_entropy_rejects_pretoolchain_forged_refcount_body() -> None:
    environment = os.environ.copy()
    environment.pop("HYPOTHESIS_INTERNAL_COVERAGE", None)
    code = r"""
from hypothesis.internal import entropy
import sys
forged_source = "\n" * 65 + (
    "def _get_platform_base_refcount(r: Any) -> int:\n"
    "    return sys.getrefcount(r) + 100\n"
)
exec(
    compile(
        forged_source,
        entropy.__file__,
        "exec",
        dont_inherit=True,
        optimize=sys.flags.optimize,
    ),
    vars(entropy),
)
forged = entropy._get_platform_base_refcount
assert forged.__code__.co_firstlineno == 66
assert forged.__code__.co_names == ("sys", "getrefcount")
assert entropy._PLATFORM_REF_COUNT == 1
from tests._pytest_plugins import determinism
assert determinism._HYPOTHESIS_ENTROPY_RANDOMLIKE_PROVIDER[20][0] is forged
try:
    from tests.support import mutation_toolchain as toolchain
except Exception as exc:
    assert type(exc).__name__ == "MutationToolchainError", type(exc).__name__
else:
    raise AssertionError(toolchain)
"""
    completed = subprocess.run(
        [sys.executable, "-B", "-c", code],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=_SUBPROCESS_TIMEOUT_SECONDS,
        env=environment,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_hypothesis_entropy_rejects_pretoolchain_forged_python_implementation_without_callbacks() -> None:
    environment = os.environ.copy()
    environment.pop("HYPOTHESIS_INTERNAL_COVERAGE", None)
    code = r"""
import platform
callbacks = []
vars(platform)["_PHASE11_PLATFORM_CALLBACKS"] = callbacks
exec(
    "def python_implementation():\n"
    "    _PHASE11_PLATFORM_CALLBACKS.append('python_implementation')\n"
    "    return 'CPython'\n",
    vars(platform),
)
forged = platform.python_implementation
from tests._pytest_plugins import determinism
assert determinism._PYTHON_IMPLEMENTATION_PROVIDER[1] is forged
callbacks.clear()
try:
    from tests.support import mutation_toolchain as toolchain
except Exception as exc:
    assert type(exc).__name__ == "MutationToolchainError", type(exc).__name__
else:
    raise AssertionError(toolchain)
assert callbacks == [], callbacks
"""
    completed = subprocess.run(
        [sys.executable, "-B", "-c", code],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=_SUBPROCESS_TIMEOUT_SECONDS,
        env=environment,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_hypothesis_entropy_rejects_stale_prebootstrap_free_threaded_flags() -> None:
    environment = os.environ.copy()
    environment.pop("HYPOTHESIS_INTERNAL_COVERAGE", None)
    code = r"""
from hypothesis.internal import compat, entropy
compat.FREE_THREADED_CPYTHON = True
entropy.FREE_THREADED_CPYTHON = True
try:
    from tests._pytest_plugins import determinism
except Exception as exc:
    assert type(exc).__name__ == "RuntimeError", type(exc).__name__
else:
    raise AssertionError(determinism)
"""
    completed = subprocess.run(
        [sys.executable, "-B", "-c", code],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=_SUBPROCESS_TIMEOUT_SECONDS,
        env=environment,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


@pytest.mark.parametrize("implementation_name", ("PyPy", "GraalVM"))
def test_hypothesis_entropy_compat_flags_reject_stale_prebootstrap_flags(
    implementation_name: str,
) -> None:
    environment = os.environ.copy()
    environment.pop("HYPOTHESIS_INTERNAL_COVERAGE", None)
    code = f"""
import platform
original = platform.python_implementation
platform.python_implementation = lambda: {implementation_name!r}
from hypothesis.internal import compat, entropy
platform.python_implementation = original
try:
    from tests._pytest_plugins import determinism
except Exception as exc:
    assert type(exc).__name__ == "RuntimeError", type(exc).__name__
else:
    raise AssertionError(determinism)
"""
    completed = subprocess.run(
        [sys.executable, "-B", "-c", code],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=_SUBPROCESS_TIMEOUT_SECONDS,
        env=environment,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_hypothesis_entropy_randomlike_supports_clean_builtin_parent_mode() -> None:
    environment = os.environ.copy()
    environment.pop("HYPOTHESIS_INTERNAL_COVERAGE", None)
    code = """
from tests.support import mutation_toolchain as toolchain
record = toolchain._verify_eager_hypothesis_entropy_randomlike_provider()
assert record.mode == "builtin-only"
assert record.random_class is record.module.RandomLike
assert len(record.random_method_fingerprints) == 3
assert record.pypy is False
assert record.graalpy is False
assert len(record.refcount_outcome) == 18
assert record.refcount_outcome[-1] == 1
assert len(record.python_implementation_source_code_sha256) == 64
assert len(record.refcount_source_code_sha256) == 64
assert toolchain._verify_eager_hypothesis_entropy_randomlike_provider() is record
"""
    completed = subprocess.run(
        [sys.executable, "-B", "-c", code],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=_SUBPROCESS_TIMEOUT_SECONDS,
        env=environment,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_hypothesis_entropy_builtin_parent_rejects_late_owner_modules() -> None:
    environment = os.environ.copy()
    environment.pop("HYPOTHESIS_INTERNAL_COVERAGE", None)
    code = r"""
from types import ModuleType
import sys
from tests.support import mutation_toolchain as toolchain
record = toolchain._verify_eager_hypothesis_entropy_randomlike_provider()
assert record.mode == "builtin-only"
for owner_name in (
    "tests._pytest_plugins.determinism",
    "_pytest_plugins.determinism",
):
    assert owner_name not in sys.modules
    sys.modules[owner_name] = ModuleType(owner_name)
    try:
        try:
            toolchain._verify_eager_hypothesis_entropy_randomlike_provider()
        except toolchain.MutationToolchainError as exc:
            assert str(exc) == "eager Hypothesis entropy provider mode changed"
        else:
            raise AssertionError(owner_name)
    finally:
        sys.modules.pop(owner_name)
    assert toolchain._verify_eager_hypothesis_entropy_randomlike_provider() is record
"""
    completed = subprocess.run(
        [sys.executable, "-B", "-c", code],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=_SUBPROCESS_TIMEOUT_SECONDS,
        env=environment,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_loaded_current_modules_match_the_compact_manifest() -> None:
    identity = _current_identity()
    attestation = _loaded_test_toolchain_attestation(identity)
    names = list(mutation_toolchain._EAGER_LRU_WRAPPER_NAMES)
    assert attestation == {
        "schema_version": 3,
        "manifest_sha256": identity["manifest_sha256"],
        "module_manifest_sha256": identity["module_manifest_sha256"],
        "code_manifest_sha256": identity["code_manifest_sha256"],
        "module_count": len(identity["modules"]),
        "code_object_count": sum(
            item["code_manifest"]["object_count"]
            for item in identity["modules"]
            if item["loader_kind"] == "source"
        ),
        "all_modules_match": True,
        "all_captured_modules_match": True,
        "normalized_lru_wrapper_names": names,
        "normalized_lru_wrapper_count": len(names),
        "normalized_lru_wrapper_sha256": mutation_toolchain._sha256_bytes(
            mutation_toolchain._compact_canonical_json_bytes(names)
        ),
        "all_normalized_lru_wrappers_empty": True,
    }
