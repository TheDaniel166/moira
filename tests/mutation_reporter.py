"""Opt-in child-process reporter for curated scientific source mutations.

This module is loaded explicitly with ``-p mutation_reporter``.  It is not a
member of Moira's required global pytest plugin manifest.  The parent mutation
runner owns isolation and interprets this report; this plugin only records the
exact child-process observations needed to distinguish an intended semantic
kill from an import, collection, or harness failure.

The in-process LRU reset below is deterministic state normalization for the
cooperative CPython test toolchain.  It is not containment against hostile
native code, ``ctypes``, or callables captured before the toolchain bootstrap;
the parent runner remains the security boundary for those cases.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import importlib
from importlib.machinery import ExtensionFileLoader, SourceFileLoader
import json
import marshal
import math
import os
from pathlib import Path, PurePosixPath
import platform
import re
import stat
import sys
from types import (
    CodeType,
    FunctionType,
    MappingProxyType,
    MethodDescriptorType,
    ModuleType,
)
from typing import Any

import pytest


_SCHEMA_VERSION = 3
_CODE_DIGEST_ALGORITHM = "python_code_v1"
_INTENDED_TEST_CODE_DIGEST_ALGORITHM = "python_code_structural_v1"
_PLUGIN_NAME = "moira-phase11-mutation-reporter"
_MAX_TEXT_CHARS = 16 * 1024
_MAX_NODEID_CHARS = 16 * 1024
_MAX_REPORTS = 128
_MAX_ERRORS = 128
_MAX_USER_PROPERTIES = 256
_EXECUTION_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")
_DOTTED_NAME_RE = re.compile(
    r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*"
)
_TEST_SELECTOR_RE = re.compile(
    r"(?P<qualname>[A-Za-z_][A-Za-z0-9_]*)(?:\[[^\[\]\r\n]+\])?"
)
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_LRU_NORMALIZATION_FIELDS = (
    "normalized_lru_wrapper_names",
    "normalized_lru_wrapper_count",
    "normalized_lru_wrapper_sha256",
    "all_normalized_lru_wrappers_empty",
)
_WINDOWS_RESERVED_COMPONENTS = frozenset(
    {
        "AUX",
        "CON",
        "NUL",
        "PRN",
        *(f"COM{index}" for index in range(1, 10)),
        *(f"LPT{index}" for index in range(1, 10)),
    }
)
_WINDOWS_REPARSE_POINT_ATTRIBUTE = getattr(
    stat,
    "FILE_ATTRIBUTE_REPARSE_POINT",
    0x400,
)
_WINDOWS_NAME_SURROGATE_TAG_BIT = 0x20000000
_EVIDENCE_PROPERTY_NAMES = frozenset(
    {
        "moira_validation_claim_id",
        "moira_validation_contract_sha256",
    }
)
_POLICY_ENVIRONMENT_NAMES = (
    "MOIRA_TEST_MODE",
    "MOIRA_NO_DOWNLOAD",
    "MOIRA_STRICT_KNOWN_ISSUES",
    "MOIRA_TEST_NETWORK_POLICY",
    "MOIRA_TEST_ARTIFACTS",
    "MOIRA_TEST_SEED",
    "MOIRA_TEST_BUDGET_TOTAL_S",
    "MOIRA_TEST_BUDGET_CASE_S",
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD",
    "PYTHONNOUSERSITE",
    "PYTHONDONTWRITEBYTECODE",
    "PYTHONHASHSEED",
    "PYTHONOPTIMIZE",
)


def _early_pytest_lru_identity(
    pluginmanager: object,
) -> tuple[object, object, object]:
    """Return the exact pytest-owned LRU identities before conftests load."""

    manager_type = type(pluginmanager)
    if (
        type(manager_type) is not type
        or type.__getattribute__(manager_type, "__module__") != "_pytest.config"
        or type.__getattribute__(manager_type, "__qualname__")
        != "PytestPluginManager"
    ):
        raise pytest.UsageError(
            "Phase 11 mutation reporter requires the exact pytest plugin manager"
        )
    manager_namespace = object.__getattribute__(pluginmanager, "__dict__")
    if type(manager_namespace) is not dict or any(
        type(key) is not str for key in dict.keys(manager_namespace)
    ):
        raise pytest.UsageError(
            "Phase 11 mutation reporter plugin manager namespace is not exact"
        )
    name_to_plugin = dict.get(manager_namespace, "_name2plugin")
    if (
        dict.get(manager_namespace, "_configured") is not False
        or type(name_to_plugin) is not dict
        or any(type(key) is not str for key in dict.keys(name_to_plugin))
        or dict.get(name_to_plugin, "moira-phase11-early-pytest-lru-identity")
        is not None
    ):
        raise pytest.UsageError(
            "Phase 11 mutation reporter loaded after pytest configuration began"
        )

    wrapper = dict.get(manager_namespace, "_get_directory")
    wrapper_type = type(wrapper)
    if (
        type(wrapper_type) is not type
        or type.__getattribute__(wrapper_type, "__module__") != "functools"
        or type.__getattribute__(wrapper_type, "__qualname__")
        != "_lru_cache_wrapper"
    ):
        raise pytest.UsageError(
            "Phase 11 mutation reporter pytest LRU wrapper is not exact"
        )
    wrapper_namespace = object.__getattribute__(wrapper, "__dict__")
    if type(wrapper_namespace) is not dict or any(
        type(key) is not str for key in dict.keys(wrapper_namespace)
    ):
        raise pytest.UsageError(
            "Phase 11 mutation reporter pytest LRU namespace is not exact"
        )
    cache_parameters = dict.get(wrapper_namespace, "cache_parameters")
    if type(cache_parameters) is not FunctionType:
        raise pytest.UsageError(
            "Phase 11 mutation reporter pytest cache policy callable is not exact"
        )
    return pluginmanager, wrapper, cache_parameters


class _EarlyPytestLruIdentityPlugin(tuple):
    """One-shot immutable bridge from early plugin load to configuration."""

    __slots__ = ()

    @pytest.hookimpl(trylast=True)
    def pytest_configure(self, config) -> None:
        if tuple.__len__(self) != 4:
            raise pytest.UsageError(
                "Phase 11 early pytest identity tuple is not exact"
            )
        manager = tuple.__getitem__(self, 0)
        wrapper = tuple.__getitem__(self, 1)
        cache_parameters = tuple.__getitem__(self, 2)
        configure_reporter = tuple.__getitem__(self, 3)
        config_namespace = object.__getattribute__(config, "__dict__")
        manager_namespace = object.__getattribute__(manager, "__dict__")
        wrapper_namespace = object.__getattribute__(wrapper, "__dict__")
        if (
            type(config_namespace) is not dict
            or type(manager_namespace) is not dict
            or type(wrapper_namespace) is not dict
            or any(type(key) is not str for key in dict.keys(config_namespace))
            or any(type(key) is not str for key in dict.keys(manager_namespace))
            or any(type(key) is not str for key in dict.keys(wrapper_namespace))
            or dict.get(config_namespace, "pluginmanager") is not manager
            or dict.get(manager_namespace, "_configured") is not True
            or dict.get(manager_namespace, "_get_directory") is not wrapper
            or dict.get(wrapper_namespace, "cache_parameters")
            is not cache_parameters
            or type(configure_reporter) is not FunctionType
        ):
            raise pytest.UsageError(
                "Phase 11 early pytest identity relationships changed"
            )
        name_to_plugin = dict.get(manager_namespace, "_name2plugin")
        if (
            type(name_to_plugin) is not dict
            or any(type(key) is not str for key in dict.keys(name_to_plugin))
            or dict.get(name_to_plugin, "pytestconfig") is not config
            or dict.get(
                name_to_plugin,
                "moira-phase11-early-pytest-lru-identity",
            )
            is not self
        ):
            raise pytest.UsageError(
                "Phase 11 early pytest identity registry changed"
            )

        wrapper_type = type(wrapper)
        wrapper_type_namespace = type.__getattribute__(wrapper_type, "__dict__")
        cache_info_descriptor = wrapper_type_namespace.get("cache_info")
        cache_clear_descriptor = wrapper_type_namespace.get("cache_clear")
        if (
            type(wrapper_type_namespace) is not MappingProxyType
            or type(cache_info_descriptor) is not MethodDescriptorType
            or type(cache_clear_descriptor) is not MethodDescriptorType
        ):
            raise pytest.UsageError(
                "Phase 11 pytest LRU behavior descriptors changed"
            )

        class FirstProbe(str):
            __slots__ = ()

            def is_file(self) -> bool:
                return False

        class SecondProbe(str):
            __slots__ = ()

            def is_file(self) -> bool:
                return False

        first = FirstProbe("moira-phase11-lru-typed-policy-probe")
        second = SecondProbe("moira-phase11-lru-typed-policy-probe")
        before = cache_info_descriptor(wrapper)
        probe_failure: BaseException | str | None = None
        try:
            first_result = wrapper(first)
            second_result = wrapper(second)
            after = cache_info_descriptor(wrapper)
            if (
                not isinstance(before, tuple)
                or not isinstance(after, tuple)
                or tuple.__len__(before) != 4
                or tuple.__len__(after) != 4
                or any(
                    type(tuple.__getitem__(info, index)) is not int
                    for info in (before, after)
                    for index in range(4)
                )
                or tuple.__getitem__(before, 2) != 256
                or tuple.__getitem__(after, 2) != 256
                or tuple.__getitem__(after, 0)
                != tuple.__getitem__(before, 0) + 1
                or tuple.__getitem__(after, 1)
                != tuple.__getitem__(before, 1) + 1
                or tuple.__getitem__(after, 3)
                != min(tuple.__getitem__(before, 3) + 1, 256)
                or first_result is not first
                or second_result is not first
            ):
                probe_failure = "typed=False behavior was not observed"
        except BaseException as exc:
            probe_failure = exc
        finally:
            cache_clear_descriptor(wrapper)

        cleared = cache_info_descriptor(wrapper)
        if (
            not isinstance(cleared, tuple)
            or tuple.__len__(cleared) != 4
            or tuple(cleared) != (0, 0, 256, 0)
            or dict.get(config_namespace, "pluginmanager") is not manager
            or dict.get(manager_namespace, "_get_directory") is not wrapper
            or dict.get(wrapper_namespace, "cache_parameters")
            is not cache_parameters
            or dict.get(
                name_to_plugin,
                "moira-phase11-early-pytest-lru-identity",
            )
            is not self
        ):
            raise pytest.UsageError(
                "Phase 11 pytest LRU behavior cleanup changed identity"
            )
        if probe_failure is not None:
            if isinstance(probe_failure, BaseException):
                raise pytest.UsageError(
                    "Phase 11 pytest LRU behavior probe failed"
                ) from probe_failure
            raise pytest.UsageError(
                f"Phase 11 pytest LRU behavior probe failed: {probe_failure}"
            )

        removed = manager.unregister(
            plugin=self,
            name="moira-phase11-early-pytest-lru-identity",
        )
        if (
            removed is not self
            or dict.get(
                name_to_plugin,
                "moira-phase11-early-pytest-lru-identity",
            )
            is not None
            or any(
                implementation.plugin is self
                for implementation in manager.hook.pytest_configure.get_hookimpls()
            )
        ):
            raise pytest.UsageError(
                "Phase 11 early pytest identity plugin was not removed exactly"
            )
        configure_reporter(
            config,
            (manager, wrapper, cache_parameters),
        )


def _lru_normalization_receipt(
    value: object,
    *,
    label: str,
) -> dict[str, object]:
    if type(value) is not dict or set(value) != set(_LRU_NORMALIZATION_FIELDS):
        raise ValueError(f"{label} fields are not exact")
    receipt = value
    names = receipt["normalized_lru_wrapper_names"]
    count = receipt["normalized_lru_wrapper_count"]
    digest = receipt["normalized_lru_wrapper_sha256"]
    if (
        type(names) is not list
        or not names
        or any(type(name) is not str or not name for name in names)
        or names != sorted(set(names))
        or type(count) is not int
        or count != len(names)
        or type(digest) is not str
        or _SHA256_RE.fullmatch(digest) is None
        or receipt["all_normalized_lru_wrappers_empty"] is not True
    ):
        raise ValueError(f"{label} is invalid or reports a nonempty cache")
    return {
        "normalized_lru_wrapper_names": list(names),
        "normalized_lru_wrapper_count": count,
        "normalized_lru_wrapper_sha256": digest,
        "all_normalized_lru_wrappers_empty": True,
    }


def _lru_normalization_from_attestation(
    value: object,
    *,
    label: str,
) -> dict[str, object]:
    if type(value) is not dict:
        raise ValueError(f"{label} is not an exact object")
    try:
        receipt = {field: value[field] for field in _LRU_NORMALIZATION_FIELDS}
    except KeyError as exc:
        raise ValueError(f"{label} omitted LRU normalization evidence") from exc
    return _lru_normalization_receipt(receipt, label=label)


def _is_name_surrogate_reparse(metadata: os.stat_result) -> bool:
    has_reparse_flag = bool(
        getattr(metadata, "st_file_attributes", 0)
        & _WINDOWS_REPARSE_POINT_ATTRIBUTE
    )
    reparse_tag = getattr(metadata, "st_reparse_tag", None)
    return has_reparse_flag and (
        reparse_tag is None
        or bool(reparse_tag & _WINDOWS_NAME_SURROGATE_TAG_BIT)
    )


def _metadata_signature(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        getattr(
            metadata,
            "st_mtime_ns",
            int(metadata.st_mtime * 1_000_000_000),
        ),
    )


def _directory_identity(metadata: os.stat_result) -> tuple[int, int]:
    return metadata.st_dev, metadata.st_ino


def _bounded_text(value: object, *, limit: int = _MAX_TEXT_CHARS) -> tuple[str, bool]:
    text = str(value)
    if len(text) <= limit:
        return text, False
    omitted = len(text) - limit
    suffix = f"...[TRUNCATED {omitted} CHARACTERS]"
    retained = max(0, limit - len(suffix))
    return text[:retained] + suffix, True


def _safe_source_path(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise pytest.UsageError(
            "--moira-mutation-source-path must be a nonblank POSIX path"
        )
    if (
        len(value) > _MAX_TEXT_CHARS
        or "\\" in value
        or "\x00" in value
        or any(character in value for character in "*?[]")
    ):
        raise pytest.UsageError(
            "--moira-mutation-source-path must be one exact bounded POSIX path"
        )
    candidate = PurePosixPath(value)
    if (
        candidate.is_absolute()
        or not candidate.parts
        or any(part in {"", ".", ".."} for part in candidate.parts)
    ):
        raise pytest.UsageError(
            "--moira-mutation-source-path must stay inside the pytest root"
        )
    for component in candidate.parts:
        if (
            component.rstrip(" .") != component
            or ":" in component
            or component.split(".", 1)[0].upper()
            in _WINDOWS_RESERVED_COMPONENTS
        ):
            raise pytest.UsageError(
                "--moira-mutation-source-path is not portable on Windows"
            )
    return candidate.as_posix()


def _safe_execution_id(value: object) -> str:
    if (
        not isinstance(value, str)
        or _EXECUTION_ID_RE.fullmatch(value) is None
        or value.upper() in _WINDOWS_RESERVED_COMPONENTS
    ):
        raise pytest.UsageError(
            "--moira-mutation-execution-id must be one portable ASCII "
            "component matching [A-Za-z0-9][A-Za-z0-9_-]{0,63}"
        )
    return value


def _safe_dotted_name(value: object, *, option: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) > 512
        or _DOTTED_NAME_RE.fullmatch(value) is None
    ):
        raise pytest.UsageError(
            f"{option} must be a bounded dotted Python identifier"
        )
    return value


def _safe_nodeid(value: object) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > _MAX_NODEID_CHARS
        or "\\" in value
        or any(ord(character) < 0x20 or ord(character) > 0x7E for character in value)
    ):
        raise pytest.UsageError(
            "--moira-mutation-intended-nodeid must be bounded printable ASCII "
            "using POSIX separators"
        )
    path_text = value.split("::", 1)[0]
    path = PurePosixPath(path_text)
    if (
        path.is_absolute()
        or len(path.parts) < 2
        or path.parts[0] != "tests"
        or path.suffix != ".py"
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise pytest.UsageError(
            "--moira-mutation-intended-nodeid must identify one tests/*.py item"
        )
    return value


def _directory_metadata(path: Path, *, label: str) -> os.stat_result:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise pytest.UsageError(f"{label} is unavailable: {path}: {exc}") from exc
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or stat.S_ISLNK(metadata.st_mode)
        or _is_name_surrogate_reparse(metadata)
    ):
        raise pytest.UsageError(
            f"{label} must be a real directory, not a link or reparse point: {path}"
        )
    return metadata


def _report_path(value: object) -> tuple[Path, tuple[int, int]]:
    if not isinstance(value, str) or not value or len(value) > _MAX_TEXT_CHARS:
        raise pytest.UsageError(
            "--moira-mutation-report must be one bounded absolute path"
        )
    path = Path(value)
    if not path.is_absolute():
        raise pytest.UsageError("--moira-mutation-report must be absolute")
    if path.name in {"", ".", ".."}:
        raise pytest.UsageError("--moira-mutation-report must name a file")
    try:
        path.lstat()
    except FileNotFoundError:
        pass
    except OSError as exc:
        raise pytest.UsageError(
            f"cannot inspect --moira-mutation-report: {exc}"
        ) from exc
    else:
        raise pytest.UsageError(
            "--moira-mutation-report already exists; refusing to overwrite it"
        )
    parent = path.parent.resolve(strict=True)
    parent_metadata = _directory_metadata(
        parent,
        label="mutation report parent",
    )
    return parent / path.name, _directory_identity(parent_metadata)


def _strict_file_identity(path: Path) -> dict[str, object]:
    lexical = path.absolute()
    entry_metadata = lexical.lstat()
    if (
        not stat.S_ISREG(entry_metadata.st_mode)
        or stat.S_ISLNK(entry_metadata.st_mode)
        or _is_name_surrogate_reparse(entry_metadata)
    ):
        raise ValueError(f"identity path is not a plain regular file: {lexical}")
    resolved = lexical.resolve(strict=True)
    metadata = resolved.lstat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or stat.S_ISLNK(metadata.st_mode)
        or _is_name_surrogate_reparse(metadata)
    ):
        raise ValueError(f"identity path is not a plain regular file: {resolved}")
    digest = hashlib.sha256()
    size = 0
    with resolved.open("rb") as source:
        opened_before = os.fstat(source.fileno())
        if not stat.S_ISREG(opened_before.st_mode):
            raise ValueError(f"identity path changed before opening: {resolved}")
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            size += len(chunk)
            digest.update(chunk)
        opened_after = os.fstat(source.fileno())
    final_metadata = resolved.lstat()
    signatures = {
        _metadata_signature(metadata),
        _metadata_signature(opened_before),
        _metadata_signature(opened_after),
        _metadata_signature(final_metadata),
    }
    if len(signatures) != 1 or size != final_metadata.st_size:
        raise ValueError(f"identity path changed while hashing: {resolved}")
    path_text, path_truncated = _bounded_text(resolved)
    return {
        "path": path_text,
        "path_truncated": path_truncated,
        "bytes": size,
        "sha256": digest.hexdigest(),
    }


def _loader_identity(loader: object) -> tuple[str, str]:
    loader_name = f"{type(loader).__module__}.{type(loader).__qualname__}"
    if type(loader) is SourceFileLoader:
        return loader_name, "source"
    if type(loader) is ExtensionFileLoader:
        return loader_name, "extension"

    rewrite_module = sys.modules.get("_pytest.assertion.rewrite")
    rewrite_type = (
        getattr(rewrite_module, "AssertionRewritingHook", None)
        if isinstance(rewrite_module, ModuleType)
        else None
    )
    if rewrite_type is None or type(loader) is not rewrite_type:
        raise TypeError(f"unsupported module loader: {loader_name}")
    config = getattr(loader, "config", None)
    getini = getattr(config, "getini", None)
    if not callable(getini):
        raise TypeError("pytest assertion rewrite loader has no exact config policy")
    assertion_pass = getini("enable_assertion_pass_hook")
    if type(assertion_pass) is not bool:
        raise TypeError("pytest assertion rewrite policy is not Boolean")
    return (
        loader_name,
        (
            "pytest_assertion_rewrite_enabled"
            if assertion_pass
            else "pytest_assertion_rewrite_disabled"
        ),
    )


def _module_identity(module: ModuleType) -> dict[str, object]:
    module_name, module_name_truncated = _bounded_text(
        getattr(module, "__name__", "<unknown>"),
        limit=512,
    )
    module_file = getattr(module, "__file__", None)
    spec = getattr(module, "__spec__", None)
    spec_name, spec_name_truncated = _bounded_text(
        getattr(spec, "name", "") if spec is not None else "",
        limit=512,
    )
    spec_origin, spec_origin_truncated = _bounded_text(
        getattr(spec, "origin", "") if spec is not None else ""
    )
    loader = getattr(spec, "loader", None) if spec is not None else None
    loader_name, loader_policy = _loader_identity(loader)
    loader_text, loader_truncated = _bounded_text(loader_name, limit=512)
    file_identity: dict[str, object] | None = None
    file_error: str | None = None
    file_error_truncated = False
    if isinstance(module_file, str) and module_file:
        try:
            file_identity = _strict_file_identity(Path(module_file))
        except Exception as exc:
            file_error, file_error_truncated = _bounded_text(
                f"{type(exc).__name__}: {exc}"
            )
    return {
        "name": module_name,
        "name_truncated": module_name_truncated,
        "file": file_identity,
        "file_error": file_error,
        "file_error_truncated": file_error_truncated,
        "spec": {
            "name": spec_name,
            "name_truncated": spec_name_truncated,
            "origin": spec_origin,
            "origin_truncated": spec_origin_truncated,
            "loader": loader_text,
            "loader_truncated": loader_truncated,
            "loader_policy": loader_policy,
        },
    }


def _live_module_binding_is_exact(
    module_name: str,
    module: ModuleType | None,
) -> bool:
    return (
        isinstance(module, ModuleType)
        and module.__name__ == module_name
        and sys.modules.get(module_name) is module
    )


def _normalize_code_object(code: CodeType) -> CodeType:
    normalized_constants = tuple(
        _normalize_code_object(value) if isinstance(value, CodeType) else value
        for value in code.co_consts
    )
    return code.replace(
        co_consts=normalized_constants,
        co_filename="",
        co_firstlineno=1,
    )


def _python_code_v1_sha256(code: CodeType) -> str:
    normalized = _normalize_code_object(code)
    return hashlib.sha256(marshal.dumps(normalized)).hexdigest()


def _structural_python_code_sha256(code: CodeType) -> str:
    from support.mutation_toolchain import (
        PYTHON_CODE_STRUCTURAL_ALGORITHM,
        structural_python_code_sha256,
    )

    if PYTHON_CODE_STRUCTURAL_ALGORITHM != _INTENDED_TEST_CODE_DIGEST_ALGORITHM:
        raise RuntimeError("test toolchain structural code algorithm changed")
    return structural_python_code_sha256(code)


def _resolve_qualname(module: ModuleType, qualname: str) -> object:
    current: object = module
    for component in qualname.split("."):
        current = getattr(current, component)
    return current


def _intended_test_coordinates(nodeid: str) -> tuple[str, str, str]:
    components = nodeid.split("::")
    if len(components) != 2:
        raise ValueError("intended killer must be one top-level pytest function")
    relative_text, selector = components
    match = _TEST_SELECTOR_RE.fullmatch(selector)
    if match is None:
        raise ValueError("intended killer selector is not an admitted function leaf")
    relative = PurePosixPath(relative_text)
    if (
        relative.is_absolute()
        or not relative.parts
        or relative.parts[0] != "tests"
        or relative.suffix != ".py"
        or any(
            part in {"", ".", ".."} or not part.isidentifier()
            for part in (*relative.parts[:-1], relative.stem)
        )
    ):
        raise ValueError("intended killer source path is not an admitted test module")
    module_name = ".".join((*relative.parts[:-1], relative.stem))
    return relative.as_posix(), module_name, match.group("qualname")


def _callable_identity(
    item: object,
    *,
    root: Path,
    intended_nodeid: str,
) -> tuple[ModuleType, dict[str, object]]:
    relative, module_name, qualname = _intended_test_coordinates(intended_nodeid)
    if getattr(item, "nodeid", None) != intended_nodeid:
        raise ValueError("collected item is not the exact intended killer")
    if getattr(item, "originalname", None) != qualname:
        raise ValueError("collected item original name contradicts its node ID")
    module = getattr(item, "module", None)
    if not isinstance(module, ModuleType) or module.__name__ != module_name:
        raise TypeError("intended killer module identity is wrong")
    if not _live_module_binding_is_exact(module_name, module):
        raise ValueError(
            "intended killer module is not its exact live sys.modules binding"
        )
    expected_path = root.joinpath(*PurePosixPath(relative).parts).resolve(strict=True)
    module_file = getattr(module, "__file__", None)
    if not isinstance(module_file, str) or not Path(module_file).samefile(expected_path):
        raise ValueError("intended killer module resolved outside its snapshot source")
    module_identity = _module_identity(module)
    specification = module_identity["spec"]
    if (
        not isinstance(specification, dict)
        or specification.get("loader_policy")
        != "pytest_assertion_rewrite_disabled"
    ):
        raise TypeError("intended killer did not use the admitted pytest rewrite policy")

    function = getattr(item, "obj", None)
    if type(function) is not FunctionType:
        raise TypeError("intended killer is not an exact Python function")
    if hasattr(function, "__wrapped__"):
        raise TypeError("wrapped intended killers require a separately admitted policy")
    if (
        getattr(function, "__module__", None) != module_name
        or getattr(function, "__name__", None) != qualname
        or getattr(function, "__qualname__", None) != qualname
        or getattr(module, qualname, None) is not function
    ):
        raise ValueError("intended killer callable is not its exact module binding")
    code = function.__code__
    if code.co_qualname != qualname or not Path(code.co_filename).samefile(expected_path):
        raise ValueError("intended killer code object is foreign")
    filename, filename_truncated = _bounded_text(code.co_filename)
    return module, {
        "type": "builtins.function",
        "module": module_name,
        "name": qualname,
        "qualname": qualname,
        "module_binding_exact": True,
        "wrapped": False,
        "code": {
            "algorithm": _INTENDED_TEST_CODE_DIGEST_ALGORITHM,
            "filename": filename,
            "filename_truncated": filename_truncated,
            "qualname": code.co_qualname,
            "sha256": _structural_python_code_sha256(code),
        },
    }


def _exception_payload(excinfo: Any) -> dict[str, object] | None:
    if excinfo is None:
        return None
    value = getattr(excinfo, "value", None)
    if value is None:
        return None
    exception_type = type(value)
    type_name, type_name_truncated = _bounded_text(
        f"{exception_type.__module__}.{exception_type.__qualname__}",
        limit=512,
    )
    message, message_truncated = _bounded_text(value)
    metamorphic: dict[str, object] | None = None
    try:
        from support.metamorphic import MetamorphicViolation
    except Exception:
        MetamorphicViolation = None  # type: ignore[assignment,misc]
    if MetamorphicViolation is not None and isinstance(value, MetamorphicViolation):
        relation_id, relation_truncated = _bounded_text(value.relation_id, limit=512)
        mutant_id, mutant_truncated = _bounded_text(value.mutant_id, limit=512)
        metric, metric_truncated = _bounded_text(value.metric, limit=1024)
        metamorphic = {
            "relation_id": relation_id,
            "relation_id_truncated": relation_truncated,
            "mutant_id": mutant_id,
            "mutant_id_truncated": mutant_truncated,
            "metric": metric,
            "metric_truncated": metric_truncated,
            "observed": float(value.observed),
            "limit": float(value.limit),
        }
    return {
        "type": type_name,
        "type_truncated": type_name_truncated,
        "message": message,
        "message_truncated": message_truncated,
        "metamorphic_violation": metamorphic,
    }


def _evidence_user_properties(report: Any) -> list[dict[str, object]]:
    properties: list[dict[str, object]] = []
    for raw_pair in getattr(report, "user_properties", ()) or ():
        if len(properties) >= _MAX_USER_PROPERTIES:
            break
        try:
            raw_name, raw_value = raw_pair
        except (TypeError, ValueError):
            continue
        if raw_name not in _EVIDENCE_PROPERTY_NAMES:
            continue
        name, name_truncated = _bounded_text(raw_name, limit=256)
        value, value_truncated = _bounded_text(raw_value)
        properties.append(
            {
                "name": name,
                "name_truncated": name_truncated,
                "value": value,
                "value_truncated": value_truncated,
            }
        )
    return properties


def _exit_status_payload(exitstatus: object) -> dict[str, object]:
    try:
        status = pytest.ExitCode(int(exitstatus))
    except (TypeError, ValueError):
        raw, truncated = _bounded_text(exitstatus, limit=256)
        return {"code": None, "name": "UNKNOWN", "raw": raw, "raw_truncated": truncated}
    return {"code": int(status), "name": status.name}


def _json_bytes(payload: object) -> bytes:
    return (
        json.dumps(
            payload,
            allow_nan=False,
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


@dataclass(slots=True, eq=False)
class _Reporter:
    config: Any
    report_path: Path
    report_parent_signature: tuple[int, int]
    execution_id: str
    intended_nodeid: str
    source_relative_path: str
    module_name: str
    target_qualname: str
    early_pytest_lru_identity: tuple[object, object, object]
    root: Path = field(init=False)
    source_path: Path = field(init=False)
    selected_nodeids: list[str] = field(default_factory=list)
    collect_errors: list[dict[str, object]] = field(default_factory=list)
    internal_errors: list[dict[str, object]] = field(default_factory=list)
    reports: list[dict[str, object]] = field(default_factory=list)
    trace_attempted: bool = False
    preexisting_tracer: bool = False
    trace_call_count: int = 0
    trace_frame_filenames: set[str] = field(default_factory=set)
    trace_code_sha256: set[str] = field(default_factory=set)
    intended_test_trace_call_count: int = 0
    intended_test_trace_frame_filenames: set[str] = field(default_factory=set)
    intended_test_trace_code_sha256: set[str] = field(default_factory=set)
    resolved_target_code_sha256: str | None = None
    target_binding_stable: bool = False
    intended_test_module: ModuleType | None = None
    intended_test_item: object | None = None
    intended_test_function: FunctionType | None = None
    intended_test_code: CodeType | None = None
    initial_intended_test_callable: dict[str, object] | None = None
    target_module: ModuleType | None = None
    target_function: FunctionType | None = None
    target_code: CodeType | None = None
    initial_test_toolchain: dict[str, object] = field(init=False)
    initial_loaded_toolchain: dict[str, object] = field(init=False)
    initial_lru_normalization: dict[str, object] = field(init=False)
    precall_lru_normalization: dict[str, object] | None = None
    lru_runtime_context: object = field(init=False)
    lru_runtime_context_identity: int = field(init=False)

    def __post_init__(self) -> None:
        self.root = Path(self.config.rootpath).resolve(strict=True)
        relative = PurePosixPath(self.source_relative_path)
        candidate = self.root.joinpath(*relative.parts)
        try:
            self.source_path = candidate.resolve(strict=True)
        except OSError as exc:
            raise pytest.UsageError(
                f"mutation source path is unavailable: {candidate}: {exc}"
            ) from exc
        if not self.source_path.is_relative_to(self.root):
            raise pytest.UsageError("mutation source path escapes the pytest root")
        _strict_file_identity(self.source_path)
        try:
            from support.mutation_toolchain import (
                capture_active_pytest_lru_runtime_context,
                loaded_test_toolchain_attestation,
                normalize_eager_lru_wrappers,
                project_test_toolchain_identity,
            )

            (
                expected_plugin_manager,
                expected_get_directory_wrapper,
                expected_cache_parameters,
            ) = self.early_pytest_lru_identity
            context = capture_active_pytest_lru_runtime_context(
                self.config,
                expected_plugin_manager=expected_plugin_manager,
                expected_get_directory_wrapper=expected_get_directory_wrapper,
                expected_cache_parameters=expected_cache_parameters,
            )
            self.lru_runtime_context = context
            self.lru_runtime_context_identity = id(context)
            startup_prebuild_lru_normalization = _lru_normalization_receipt(
                normalize_eager_lru_wrappers(
                    self._active_lru_runtime_context()
                ),
                label="startup pre-build LRU normalization",
            )
            self.initial_test_toolchain = project_test_toolchain_identity(
                self.root,
                lru_runtime_context=self._active_lru_runtime_context(),
            )
            self.initial_lru_normalization = _lru_normalization_receipt(
                normalize_eager_lru_wrappers(
                    self._active_lru_runtime_context()
                ),
                label="startup post-build LRU normalization",
            )
            if (
                startup_prebuild_lru_normalization
                != self.initial_lru_normalization
            ):
                raise ValueError(
                    "startup LRU registry changed while building identity"
                )
            self.initial_loaded_toolchain = (
                loaded_test_toolchain_attestation(
                    self.initial_test_toolchain,
                    lru_runtime_context=self._active_lru_runtime_context(),
                )
            )
            if self.initial_lru_normalization != (
                _lru_normalization_from_attestation(
                    self.initial_loaded_toolchain,
                    label="initial loaded toolchain LRU attestation",
                )
            ):
                raise ValueError(
                    "initial LRU normalization differs from loaded attestation"
                )
        except Exception as exc:
            raise pytest.UsageError(
                "mutation test toolchain cannot be attested at startup: "
                f"{type(exc).__name__}: {exc}"
            ) from exc

    def _active_lru_runtime_context(self) -> object:
        context = self.lru_runtime_context
        identity = self.lru_runtime_context_identity
        if type(identity) is not int or id(context) != identity:
            raise ValueError(
                "mutation reporter LRU runtime context identity changed"
            )
        return context

    def _internal_error(self, stage: str, message: object) -> None:
        if len(self.internal_errors) >= _MAX_ERRORS:
            return
        safe_stage, stage_truncated = _bounded_text(stage, limit=128)
        safe_message, message_truncated = _bounded_text(message)
        self.internal_errors.append(
            {
                "stage": safe_stage,
                "stage_truncated": stage_truncated,
                "message": safe_message,
                "message_truncated": message_truncated,
            }
        )

    def _prepare_target(self) -> CodeType:
        module = importlib.import_module(self.module_name)
        if not _live_module_binding_is_exact(self.module_name, module):
            raise ValueError(
                "mutation target module is not its exact live sys.modules binding"
            )
        module_file = getattr(module, "__file__", None)
        if not isinstance(module_file, str) or not Path(module_file).samefile(
            self.source_path
        ):
            raise ValueError(
                f"target module {self.module_name} did not resolve to "
                f"{self.source_relative_path}"
            )
        target = _resolve_qualname(module, self.target_qualname)
        if type(target) is not FunctionType or hasattr(target, "__wrapped__"):
            raise TypeError(
                "mutation target must be an exact unwrapped Python function binding"
            )
        if getattr(target, "__module__", None) != self.module_name:
            raise ValueError("mutation target is owned by a foreign module")
        code = getattr(target, "__code__", None)
        if not isinstance(code, CodeType):
            raise TypeError(
                f"target {self.module_name}.{self.target_qualname} has no Python code object"
            )
        if not Path(code.co_filename).samefile(self.source_path):
            raise ValueError("target code object resolved outside the declared source file")
        if code.co_qualname != self.target_qualname:
            raise ValueError(
                "target code qualname contradicts --moira-mutation-target-qualname"
            )
        self.target_module = module
        self.target_function = target
        self.target_code = code
        self.resolved_target_code_sha256 = _python_code_v1_sha256(code)
        self.target_binding_stable = True
        return code

    def _target_identity_is_stable(self) -> bool:
        try:
            current = (
                _resolve_qualname(self.target_module, self.target_qualname)
                if self.target_module is not None
                else None
            )
        except Exception as exc:
            self.target_binding_stable = False
            self._internal_error(
                "target_identity",
                f"{type(exc).__name__}: {exc}",
            )
            return False
        stable = (
            _live_module_binding_is_exact(self.module_name, self.target_module)
            and type(current) is FunctionType
            and current is self.target_function
            and current.__code__ is self.target_code
            and current.__module__ == self.module_name
            and not hasattr(current, "__wrapped__")
        )
        if not stable:
            self.target_binding_stable = False
            self._internal_error(
                "target_identity",
                "mutation target binding changed during intended-test execution",
            )
        return stable

    def _matches_target_frame(self, frame: Any) -> bool:
        code = frame.f_code
        if (
            self.target_code is None
            or self.target_module is None
            or not _live_module_binding_is_exact(
                self.module_name,
                self.target_module,
            )
            or code is not self.target_code
            or frame.f_globals is not self.target_module.__dict__
            or frame.f_globals.get("__name__") != self.module_name
        ):
            return False
        if code.co_qualname != self.target_qualname:
            return False
        try:
            return Path(code.co_filename).samefile(self.source_path)
        except OSError:
            return False

    def pytest_collection_finish(self, session) -> None:
        self.selected_nodeids = [item.nodeid for item in session.items]
        if len(set(self.selected_nodeids)) != len(self.selected_nodeids):
            self._internal_error("selection", "selected node IDs are not unique")
        if self.selected_nodeids.count(self.intended_nodeid) != 1:
            self._internal_error(
                "selection",
                "the exact intended node ID was not selected exactly once",
            )
            return
        intended_item = next(
            item for item in session.items if item.nodeid == self.intended_nodeid
        )
        try:
            module, callable_identity = _callable_identity(
                intended_item,
                root=self.root,
                intended_nodeid=self.intended_nodeid,
            )
        except Exception as exc:
            self._internal_error(
                "intended_test_identity",
                f"{type(exc).__name__}: {exc}",
            )
            return
        self.intended_test_module = module
        self.intended_test_item = intended_item
        self.intended_test_function = intended_item.obj
        self.intended_test_code = intended_item.obj.__code__
        self.initial_intended_test_callable = callable_identity

    def _intended_test_identity_is_stable(self, item: object) -> bool:
        try:
            module, callable_identity = _callable_identity(
                item,
                root=self.root,
                intended_nodeid=self.intended_nodeid,
            )
        except Exception as exc:
            self._internal_error(
                "intended_test_identity",
                f"{type(exc).__name__}: {exc}",
            )
            return False
        stable = (
            item is self.intended_test_item
            and module is self.intended_test_module
            and getattr(item, "obj", None) is self.intended_test_function
            and self.intended_test_function is not None
            and self.intended_test_code is not None
            and self.intended_test_function.__code__ is self.intended_test_code
            and callable_identity == self.initial_intended_test_callable
        )
        if not stable:
            self._internal_error(
                "intended_test_identity",
                "intended killer callable changed after collection",
            )
        return stable

    def _matches_intended_test_frame(self, frame: Any) -> bool:
        identity = self.initial_intended_test_callable
        if identity is None:
            return False
        code_identity = identity.get("code")
        if not isinstance(code_identity, dict):
            return False
        code = frame.f_code
        if (
            self.intended_test_function is None
            or self.intended_test_code is None
            or self.intended_test_module is None
            or not _live_module_binding_is_exact(
                str(identity.get("module", "")),
                self.intended_test_module,
            )
            or code is not self.intended_test_code
            or frame.f_globals is not self.intended_test_module.__dict__
            or frame.f_globals.get("__name__") != identity.get("module")
        ):
            return False
        if code.co_qualname != identity.get("qualname"):
            return False
        try:
            return Path(code.co_filename).samefile(code_identity["filename"])
        except (KeyError, OSError, TypeError):
            return False

    def _target_call_has_intended_test_ancestor(self, frame: Any) -> bool:
        ancestor = frame.f_back
        while ancestor is not None:
            if self._matches_intended_test_frame(ancestor):
                return True
            ancestor = ancestor.f_back
        return False

    def _observe_trace_call(
        self,
        frame: Any,
        trace_errors: list[str],
    ) -> None:
        if self._matches_intended_test_frame(frame):
            digest = _structural_python_code_sha256(frame.f_code)
            filename, _truncated = _bounded_text(frame.f_code.co_filename)
            self.intended_test_trace_call_count += 1
            self.intended_test_trace_code_sha256.add(digest)
            self.intended_test_trace_frame_filenames.add(filename)
        if not self._matches_target_frame(frame):
            return
        if not self._target_call_has_intended_test_ancestor(frame):
            if len(trace_errors) < _MAX_ERRORS:
                trace_errors.append(
                    "declared mutation target was called outside the exact "
                    "intended-test frame ancestry"
                )
            return
        digest = _python_code_v1_sha256(frame.f_code)
        filename, _truncated = _bounded_text(frame.f_code.co_filename)
        self.trace_call_count += 1
        self.trace_code_sha256.add(digest)
        self.trace_frame_filenames.add(filename)

    def pytest_collectreport(self, report) -> None:
        if getattr(report, "outcome", None) != "failed":
            return
        if len(self.collect_errors) >= _MAX_ERRORS:
            return
        nodeid, nodeid_truncated = _bounded_text(
            getattr(report, "nodeid", ""),
            limit=_MAX_NODEID_CHARS,
        )
        message, message_truncated = _bounded_text(
            getattr(report, "longrepr", "")
        )
        self.collect_errors.append(
            {
                "nodeid": nodeid,
                "nodeid_truncated": nodeid_truncated,
                "outcome": "failed",
                "message": message,
                "message_truncated": message_truncated,
            }
        )

    def pytest_internalerror(self, excrepr, excinfo) -> None:
        value = getattr(excinfo, "value", None)
        detail = excrepr if value is None else f"{type(value).__name__}: {value}"
        self._internal_error("pytest_internalerror", detail)

    @pytest.hookimpl(wrapper=True, tryfirst=True)
    def pytest_runtest_call(self, item):
        if item.nodeid != self.intended_nodeid:
            return (yield)

        self.trace_attempted = True
        if not self._intended_test_identity_is_stable(item):
            try:
                result = yield
            except BaseException:
                raise
            pytest.fail(
                "Phase 11 mutation reporter rejected intended-test identity drift",
                pytrace=False,
            )
            return result
        existing_trace = sys.gettrace()
        if existing_trace is not None:
            self.preexisting_tracer = True
            self._internal_error(
                "trace",
                "a preexisting sys.settrace callback prevented mutation target tracing: "
                f"{type(existing_trace).__module__}.{type(existing_trace).__qualname__}",
            )
            try:
                result = yield
            except BaseException:
                raise
            pytest.fail(
                "Phase 11 mutation reporter refuses a preexisting sys.settrace callback",
                pytrace=False,
            )
            return result

        try:
            self._prepare_target()
        except Exception as exc:
            self._internal_error(
                "target_resolution",
                f"{type(exc).__name__}: {exc}",
            )
            try:
                result = yield
            except BaseException:
                raise
            pytest.fail(
                "Phase 11 mutation reporter could not resolve the declared target",
                pytrace=False,
            )
            return result

        try:
            from support.mutation_toolchain import normalize_eager_lru_wrappers

            # This is the last deterministic reset before cooperative test code
            # runs.  Parent-process containment remains the security boundary.
            self.precall_lru_normalization = _lru_normalization_receipt(
                normalize_eager_lru_wrappers(
                    self._active_lru_runtime_context()
                ),
                label="pre-call LRU normalization",
            )
            if self.precall_lru_normalization != self.initial_lru_normalization:
                raise ValueError(
                    "pre-call LRU normalization differs from startup"
                )
        except Exception as exc:
            self._internal_error(
                "test_toolchain_lru_normalization",
                f"pre-call: {type(exc).__name__}: {exc}",
            )
            pytest.fail(
                "Phase 11 mutation reporter could not normalize the test "
                "toolchain before the intended call",
                pytrace=False,
            )

        trace_errors: list[str] = []

        def trace_target(frame, event, arg):
            del arg
            if event != "call":
                return trace_target
            try:
                self._observe_trace_call(frame, trace_errors)
            except Exception as exc:
                if len(trace_errors) < _MAX_ERRORS:
                    trace_errors.append(f"{type(exc).__name__}: {exc}")
            return trace_target

        sys.settrace(trace_target)
        trace_changed = False
        try:
            result = yield
        finally:
            active_trace = sys.gettrace()
            trace_changed = active_trace is not trace_target
            sys.settrace(None)
            if trace_changed:
                self._internal_error(
                    "trace",
                    "the sys.settrace callback changed during the intended test call",
                )
            self._target_identity_is_stable()
            self._intended_test_identity_is_stable(item)
            for error in trace_errors:
                self._internal_error("trace", error)

        if (
            trace_changed
            or trace_errors
            or self.trace_call_count == 0
            or self.intended_test_trace_call_count == 0
        ):
            if self.trace_call_count == 0:
                self._internal_error(
                    "trace",
                    "the intended test did not call the declared target",
                )
            if self.intended_test_trace_call_count == 0:
                self._internal_error(
                    "trace",
                    "pytest did not execute the attested intended-test callable",
                )
            pytest.fail(
                "Phase 11 mutation target tracing was incomplete",
                pytrace=False,
            )
        return result

    @pytest.hookimpl(wrapper=True, tryfirst=True)
    def pytest_runtest_makereport(self, item, call):
        report = yield
        if len(self.reports) >= _MAX_REPORTS:
            self._internal_error("reports", "test report limit exceeded")
            return report
        phase = str(getattr(report, "when", "unknown"))
        nodeid, nodeid_truncated = _bounded_text(
            getattr(report, "nodeid", item.nodeid),
            limit=_MAX_NODEID_CHARS,
        )
        outcome, outcome_truncated = _bounded_text(
            getattr(report, "outcome", "unknown"),
            limit=128,
        )
        raw_duration = getattr(report, "duration", 0.0)
        try:
            duration = float(raw_duration)
        except (TypeError, ValueError):
            duration = math.nan
        if not math.isfinite(duration) or duration < 0.0:
            self._internal_error(
                "reports",
                f"{nodeid}: {phase} report has invalid duration {raw_duration!r}",
            )
            duration_value: float | None = None
        else:
            duration_value = duration
        wasxfail = getattr(report, "wasxfail", None)
        if wasxfail is None:
            wasxfail_text = None
            wasxfail_truncated = False
        else:
            wasxfail_text, wasxfail_truncated = _bounded_text(wasxfail)
        longrepr, longrepr_truncated = _bounded_text(
            getattr(report, "longrepr", "")
        )
        raw_rerun = getattr(report, "rerun", None)
        if isinstance(raw_rerun, int) and not isinstance(raw_rerun, bool):
            rerun_index: int | None = raw_rerun
        else:
            rerun_index = None
        self.reports.append(
            {
                "sequence": len(self.reports) + 1,
                "nodeid": nodeid,
                "nodeid_truncated": nodeid_truncated,
                "phase": phase,
                "outcome": outcome,
                "outcome_truncated": outcome_truncated,
                "duration_s": duration_value,
                "wasxfail": wasxfail_text,
                "wasxfail_truncated": wasxfail_truncated,
                "longrepr": longrepr,
                "longrepr_truncated": longrepr_truncated,
                "rerun": outcome == "rerun" or rerun_index is not None,
                "rerun_index": rerun_index,
                "exception": _exception_payload(getattr(call, "excinfo", None)),
                "evidence_user_properties": _evidence_user_properties(report),
            }
        )
        return report

    def _identity(self) -> dict[str, object]:
        modules: dict[str, object] = {}
        if self.target_function is not None:
            self._target_identity_is_stable()
        _test_relative, intended_test_module_name, _test_qualname = (
            _intended_test_coordinates(self.intended_nodeid)
        )
        for role, module_name in (
            ("sitecustomize", "sitecustomize"),
            ("target_module", self.module_name),
            ("intended_test", intended_test_module_name),
            ("moira", "moira"),
            ("native_backend", "moira._moira_native"),
            ("reporter", __name__),
            ("toolchain", "support.mutation_toolchain"),
        ):
            try:
                if role == "target_module":
                    module = self.target_module
                    if not _live_module_binding_is_exact(module_name, module):
                        raise RuntimeError(
                            "captured target module lost its exact live "
                            "sys.modules binding"
                        )
                elif role == "intended_test":
                    module = self.intended_test_module
                    if not _live_module_binding_is_exact(module_name, module):
                        raise RuntimeError(
                            "captured intended-test module lost its exact live "
                            "sys.modules binding"
                        )
                elif role == "sitecustomize":
                    module = sys.modules.get(module_name)
                    if not isinstance(module, ModuleType):
                        raise RuntimeError(
                            "sitecustomize was not loaded during interpreter startup"
                        )
                else:
                    module = importlib.import_module(module_name)
                modules[role] = {"available": True, **_module_identity(module)}
            except Exception as exc:
                message, truncated = _bounded_text(f"{type(exc).__name__}: {exc}")
                modules[role] = {
                    "available": False,
                    "error": message,
                    "error_truncated": truncated,
                }
                if role != "native_backend":
                    self._internal_error("identity", f"{role}: {message}")

        intended_test_callable: dict[str, object]
        if self.intended_test_item is None or self.initial_intended_test_callable is None:
            intended_test_callable = {"available": False}
            self._internal_error(
                "identity",
                "intended-test callable identity was unavailable after collection",
            )
        else:
            stable = self._intended_test_identity_is_stable(self.intended_test_item)
            intended_test_callable = {
                "available": True,
                **self.initial_intended_test_callable,
                "stable_during_execution": stable,
            }

        try:
            # Standard POSIX virtual environments expose ``bin/python`` as a
            # symlink.  The parent receipts the lexical launcher chain, while
            # this child attests the plain resolved executable bytes it ran.
            executable = _strict_file_identity(
                Path(sys.executable).resolve(strict=True)
            )
        except Exception as exc:
            message, truncated = _bounded_text(f"{type(exc).__name__}: {exc}")
            executable = {
                "error": message,
                "error_truncated": truncated,
            }
            self._internal_error("identity", f"interpreter: {message}")

        cwd, cwd_truncated = _bounded_text(Path.cwd().resolve(strict=True))
        root, root_truncated = _bounded_text(self.root)
        try:
            source_identity = _strict_file_identity(self.source_path)
        except Exception as exc:
            message, truncated = _bounded_text(f"{type(exc).__name__}: {exc}")
            source_identity = {
                "error": message,
                "error_truncated": truncated,
            }
            self._internal_error("identity", f"source: {message}")
        policy_environment: dict[str, object] = {}
        for name in _POLICY_ENVIRONMENT_NAMES:
            raw_value = os.environ.get(name)
            if raw_value is None:
                policy_environment[name] = None
            else:
                safe_value, truncated = _bounded_text(raw_value, limit=1024)
                policy_environment[name] = {
                    "value": safe_value,
                    "truncated": truncated,
                }

        network_attestation: dict[str, object]
        try:
            from support import network_policy

            active_mode, active_nodeid = network_policy._policy_snapshot()
            safe_nodeid, safe_nodeid_truncated = _bounded_text(
                active_nodeid,
                limit=_MAX_NODEID_CHARS,
            )
            network_attestation = {
                "available": True,
                "audit_hook_installed": bool(
                    network_policy._AUDIT_HOOK_INSTALLED
                ),
                "audit_canary_seen": bool(network_policy._AUDIT_CANARY_SEEN),
                "socket_method_guards_installed": bool(
                    network_policy._SOCKET_METHOD_GUARDS_INSTALLED
                ),
                "asyncio_method_guards_installed": bool(
                    network_policy._ASYNCIO_METHOD_GUARDS_INSTALLED
                ),
                "active_mode": active_mode.value,
                "active_nodeid": safe_nodeid,
                "active_nodeid_truncated": safe_nodeid_truncated,
                "environment_mode": os.environ.get(
                    network_policy.NETWORK_POLICY_ENVIRONMENT
                ),
            }
        except Exception as exc:
            message, truncated = _bounded_text(f"{type(exc).__name__}: {exc}")
            network_attestation = {
                "available": False,
                "error": message,
                "error_truncated": truncated,
            }
            self._internal_error("identity", f"network_policy: {message}")
        try:
            from support.mutation_toolchain import (
                loaded_test_toolchain_attestation,
                normalize_eager_lru_wrappers,
                project_test_toolchain_identity,
            )

            final_prebuild_lru_normalization = _lru_normalization_receipt(
                normalize_eager_lru_wrappers(
                    self._active_lru_runtime_context()
                ),
                label="final pre-build LRU normalization",
            )
            if self.precall_lru_normalization is None:
                raise ValueError("pre-call LRU normalization is missing")
            if final_prebuild_lru_normalization != (
                self.initial_lru_normalization
            ):
                raise ValueError(
                    "LRU normalization changed between reporter transitions"
                )
            final_toolchain = project_test_toolchain_identity(
                self.root,
                lru_runtime_context=self._active_lru_runtime_context(),
            )
            final_lru_normalization = _lru_normalization_receipt(
                normalize_eager_lru_wrappers(
                    self._active_lru_runtime_context()
                ),
                label="final post-build LRU normalization",
            )
            if final_lru_normalization != final_prebuild_lru_normalization:
                raise ValueError(
                    "final LRU registry changed while building identity"
                )
            final_loaded = loaded_test_toolchain_attestation(
                final_toolchain,
                lru_runtime_context=self._active_lru_runtime_context(),
            )
            final_lru_attestation = _lru_normalization_from_attestation(
                final_loaded,
                label="final loaded toolchain LRU attestation",
            )
            if final_lru_normalization != final_lru_attestation:
                raise ValueError(
                    "final LRU normalization differs from loaded attestation"
                )
            stable = final_toolchain == self.initial_test_toolchain
            loaded_stable = final_loaded == self.initial_loaded_toolchain
            test_toolchain = {
                "schema_version": self.initial_test_toolchain[
                    "schema_version"
                ],
                "initial_manifest_sha256": self.initial_test_toolchain[
                    "manifest_sha256"
                ],
                "final_manifest_sha256": final_toolchain["manifest_sha256"],
                "module_manifest_sha256": final_loaded[
                    "module_manifest_sha256"
                ],
                "code_manifest_sha256": final_loaded[
                    "code_manifest_sha256"
                ],
                "module_count": final_loaded["module_count"],
                "code_object_count": final_loaded["code_object_count"],
                "stable_during_execution": stable and loaded_stable,
                "all_modules_match": (
                    self.initial_loaded_toolchain["all_modules_match"] is True
                    and final_loaded["all_modules_match"] is True
                ),
                "all_captured_modules_match": (
                    self.initial_loaded_toolchain[
                        "all_captured_modules_match"
                    ]
                    is True
                    and final_loaded["all_captured_modules_match"] is True
                ),
                **final_lru_attestation,
            }
            if not stable or not loaded_stable:
                self._internal_error(
                    "identity",
                    "test toolchain changed during mutation execution",
                )
        except Exception as exc:
            message, truncated = _bounded_text(
                f"{type(exc).__name__}: {exc}"
            )
            test_toolchain = {
                "available": False,
                "error": message,
                "error_truncated": truncated,
            }
            self._internal_error("identity", f"test_toolchain: {message}")
        return {
            "interpreter": {
                "executable": executable,
                "implementation": platform.python_implementation(),
                "version": platform.python_version(),
                "cache_tag": sys.implementation.cache_tag,
                "pycache_prefix": (
                    _bounded_text(Path(sys.pycache_prefix).resolve())[0]
                    if sys.pycache_prefix is not None
                    else None
                ),
                "prefix": _bounded_text(Path(sys.prefix).resolve(strict=True))[0],
                "base_prefix": _bounded_text(
                    Path(sys.base_prefix).resolve(strict=True)
                )[0],
                "flags": {
                    "safe_path": bool(sys.flags.safe_path),
                    "optimize": int(sys.flags.optimize),
                    "dont_write_bytecode": bool(sys.dont_write_bytecode),
                    "no_user_site": bool(sys.flags.no_user_site),
                },
            },
            "cwd": cwd,
            "cwd_truncated": cwd_truncated,
            "root": root,
            "root_truncated": root_truncated,
            "source": source_identity,
            "modules": modules,
            "intended_test_callable": intended_test_callable,
            "policy_environment": policy_environment,
            "network": network_attestation,
            "test_toolchain": test_toolchain,
        }

    def _payload(self, exitstatus: object) -> dict[str, object]:
        identity = self._identity()
        test_relative, test_module_name, test_qualname = (
            _intended_test_coordinates(self.intended_nodeid)
        )
        intended_count = self.selected_nodeids.count(self.intended_nodeid)
        selected = []
        for nodeid in self.selected_nodeids:
            safe, truncated = _bounded_text(nodeid, limit=_MAX_NODEID_CHARS)
            selected.append({"nodeid": safe, "truncated": truncated})
        return {
            "schema_version": _SCHEMA_VERSION,
            "execution_id": self.execution_id,
            "intended": {
                "nodeid": self.intended_nodeid,
                "source_relative_path": self.source_relative_path,
                "module_name": self.module_name,
                "target_qualname": self.target_qualname,
                "test_source_relative_path": test_relative,
                "test_module_name": test_module_name,
                "test_qualname": test_qualname,
            },
            "selection": {
                "selected_nodeids": selected,
                "selected_count": len(selected),
                "intended_selected_count": intended_count,
                "only_intended_selected": (
                    len(self.selected_nodeids) == 1 and intended_count == 1
                ),
            },
            "errors": {
                "collection": self.collect_errors,
                "internal": self.internal_errors,
            },
            "reports": self.reports,
            "trace": {
                "algorithm": _CODE_DIGEST_ALGORITHM,
                "attempted": self.trace_attempted,
                "preexisting_tracer": self.preexisting_tracer,
                "call_count": self.trace_call_count,
                "frame_filenames": sorted(self.trace_frame_filenames),
                "code_sha256": sorted(self.trace_code_sha256),
                "resolved_target_code_sha256": self.resolved_target_code_sha256,
                "target_binding_exact": self.target_binding_stable,
                "intended_test_call_count": self.intended_test_trace_call_count,
                "intended_test_frame_filenames": sorted(
                    self.intended_test_trace_frame_filenames
                ),
                "intended_test_code_sha256": sorted(
                    self.intended_test_trace_code_sha256
                ),
                "resolved_intended_test_code_sha256": (
                    self.initial_intended_test_callable["code"]["sha256"]
                    if self.initial_intended_test_callable is not None
                    else None
                ),
            },
            "identity": identity,
            "pytest": {"exitstatus": _exit_status_payload(exitstatus)},
        }

    def _write_report(self, payload: object) -> None:
        parent_metadata = _directory_metadata(
            self.report_path.parent,
            label="mutation report parent",
        )
        if _directory_identity(parent_metadata) != self.report_parent_signature:
            raise RuntimeError("mutation report parent changed during pytest execution")
        try:
            self.report_path.lstat()
        except FileNotFoundError:
            pass
        else:
            raise RuntimeError("mutation report path appeared during pytest execution")

        data = _json_bytes(payload)
        temporary = self.report_path.parent / (
            f".{self.report_path.name}.{self.execution_id}.tmp"
        )
        descriptor: int | None = None
        try:
            descriptor = os.open(
                temporary,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
            )
            with os.fdopen(descriptor, "wb") as output:
                descriptor = None
                output.write(data)
                output.flush()
                os.fsync(output.fileno())
            if self.report_path.exists():
                raise RuntimeError(
                    "mutation report path appeared before atomic publication"
                )
            os.replace(temporary, self.report_path)
        finally:
            if descriptor is not None:
                os.close(descriptor)
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass

    @pytest.hookimpl(trylast=True)
    def pytest_sessionfinish(self, session, exitstatus) -> None:
        del session
        self._write_report(self._payload(exitstatus))


def pytest_addoption(parser, pluginmanager) -> None:
    early_identity = _early_pytest_lru_identity(pluginmanager)
    group = parser.getgroup("moira-mutation-reporter")
    group.addoption(
        "--moira-mutation-report",
        action="store",
        default=None,
        help="Absolute path for the atomic Phase 11 child report.",
    )
    group.addoption(
        "--moira-mutation-execution-id",
        action="store",
        default=None,
        help="Portable identity for this baseline or mutant execution.",
    )
    group.addoption(
        "--moira-mutation-intended-nodeid",
        action="store",
        default=None,
        help="Exact pytest node ID intended to kill the curated mutant.",
    )
    group.addoption(
        "--moira-mutation-source-path",
        action="store",
        default=None,
        help="POSIX path of the mutated Python source relative to pytest root.",
    )
    group.addoption(
        "--moira-mutation-module",
        action="store",
        default=None,
        help="Dotted module name owning the mutation target.",
    )
    group.addoption(
        "--moira-mutation-target-qualname",
        action="store",
        default=None,
        help="Dotted Python qualname of the callable mutation target.",
    )
    identity_plugin = tuple.__new__(
        _EarlyPytestLruIdentityPlugin,
        (*early_identity, _configure_reporter),
    )
    registered_name = pluginmanager.register(
        identity_plugin,
        name="moira-phase11-early-pytest-lru-identity",
    )
    if registered_name != "moira-phase11-early-pytest-lru-identity":
        raise pytest.UsageError(
            "Phase 11 early pytest identity plugin was not registered exactly"
        )


def _configure_reporter(
    config,
    early_pytest_lru_identity: tuple[object, object, object],
) -> None:
    if hasattr(config, "workerinput"):
        raise pytest.UsageError(
            "Phase 11 mutation reporter is controller-only and forbids xdist workers"
        )
    option_names = (
        "moira_mutation_report",
        "moira_mutation_execution_id",
        "moira_mutation_intended_nodeid",
        "moira_mutation_source_path",
        "moira_mutation_module",
        "moira_mutation_target_qualname",
    )
    values = {name: getattr(config.option, name, None) for name in option_names}
    missing = [name for name, value in values.items() if value is None]
    if missing:
        raise pytest.UsageError(
            "explicit Phase 11 mutation reporter requires every reporter option; "
            "missing: " + ", ".join(sorted(missing))
        )
    report_path, parent_signature = _report_path(values["moira_mutation_report"])
    reporter = _Reporter(
        config=config,
        report_path=report_path,
        report_parent_signature=parent_signature,
        execution_id=_safe_execution_id(
            values["moira_mutation_execution_id"]
        ),
        intended_nodeid=_safe_nodeid(
            values["moira_mutation_intended_nodeid"]
        ),
        source_relative_path=_safe_source_path(
            values["moira_mutation_source_path"]
        ),
        module_name=_safe_dotted_name(
            values["moira_mutation_module"],
            option="--moira-mutation-module",
        ),
        target_qualname=_safe_dotted_name(
            values["moira_mutation_target_qualname"],
            option="--moira-mutation-target-qualname",
        ),
        early_pytest_lru_identity=early_pytest_lru_identity,
    )
    if config.pluginmanager.get_plugin(_PLUGIN_NAME) is not None:
        raise pytest.UsageError("Phase 11 mutation reporter was registered twice")
    config.pluginmanager.register(reporter, name=_PLUGIN_NAME)


__all__ = ["pytest_addoption"]
