"""Fail-closed primitives for curated scientific source mutation assurance.

This module deliberately separates mutation evidence from ordinary pytest run
receipts.  A red pytest process is not a mutation kill by itself: the parent
runner must prove the exact postimage was loaded, the declared callable ran,
and the intended evidence item alone failed during its call phase.

The isolation here protects the user's checkout from accidental mutation.  It
is not a hostile-code sandbox, hostile same-user filesystem isolation, or a
defense against transient unadmitted runtime-directory membership injection,
and it does not replace runner-level egress denial.
"""

from __future__ import annotations

import ast
import base64
import binascii
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
from importlib.machinery import (
    EXTENSION_SUFFIXES,
    ExtensionFileLoader,
    SourceFileLoader,
)
import json
import marshal
import math
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import secrets
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
from types import CodeType, MappingProxyType
from typing import Any, Callable, Mapping, Sequence


CATALOGUE_SCHEMA_VERSION = 1
CHILD_REPORT_SCHEMA_VERSION = 3
RECEIPT_SCHEMA_VERSION = 3
INTERPRETER_IDENTITY_SCHEMA_VERSION = 2
SOURCE_HASH_MODE = "utf8_lf_v1"
INTENDED_TEST_CODE_DIGEST_ALGORITHM = "python_code_structural_v1"

OUTCOMES = (
    "killed_intended",
    "survived",
    "wrong_killer",
    "invalid_execution",
    "timed_out",
    "blocked_baseline",
)

_MUTANT_ID_RE = re.compile(r"P11-[A-Z0-9][A-Z0-9-]{2,94}")
_CLAIM_ID_RE = re.compile(r"[A-Z0-9][A-Z0-9_.-]{2,95}")
_RUN_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")
_QUALNAME_RE = re.compile(
    r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*"
)
_TEST_SELECTOR_RE = re.compile(
    r"(?P<qualname>[A-Za-z_][A-Za-z0-9_]*)(?:\[[^\[\]\r\n]+\])?"
)
_SOURCE_LOADER_NAME = (
    f"{SourceFileLoader.__module__}.{SourceFileLoader.__qualname__}"
)
_EXTENSION_LOADER_NAME = (
    f"{ExtensionFileLoader.__module__}.{ExtensionFileLoader.__qualname__}"
)
_PYTEST_REWRITE_LOADER_NAME = (
    "_pytest.assertion.rewrite.AssertionRewritingHook"
)
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_WINDOWS_REPARSE_POINT = getattr(
    stat,
    "FILE_ATTRIBUTE_REPARSE_POINT",
    0x400,
)
_WINDOWS_RESERVED = frozenset(
    {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{index}" for index in range(1, 10)),
        *(f"LPT{index}" for index in range(1, 10)),
    }
)
_MAX_JSON_BYTES = 8 * 1024 * 1024
_MAX_MUTATION_SOURCE_BYTES = 512 * 1024
_MAX_RUNTIME_FILE_BYTES = 128 * 1024 * 1024
_MAX_RUNTIME_TOTAL_BYTES = 256 * 1024 * 1024
_MAX_RUNTIME_FILES = 10_000
_RUNTIME_IDENTITY_SCOPE = (
    "venv_config_base_executable_core_runtime_stdlib_plain_files_v1"
)
_REPORT_AUTHORSHIP_BOUNDARY = (
    "same_process_intended_test_conftest_pytest_plugin_code_trusted_"
    "no_external_trace_authorship_proof"
)
_MAX_JSON_DEPTH = 64
_MAX_JSON_NODES = 500_000
_MAX_TEXT = 128 * 1024
_SNAPSHOT_SCOPES = (
    "conftest.py",
    "pyproject.toml",
    "CMakeLists.txt",
    "setup.py",
    "scripts/run_scientific_mutations.py",
    "moira",
    "moira_server",
    "tests",
    "src/native",
)
_SNAPSHOT_UNTRACKED_EXCLUDE_POLICY = (
    "__pycache__/",
    "*.py[cod]",
    "tests/artifacts/kernels/",
)
_NATIVE_BUILD_EXACT_INPUTS = (
    "CMakeLists.txt",
    "moira/_native_build_provenance.py",
    "setup.py",
)
_NATIVE_BUILD_SUFFIXES = frozenset(
    {
        ".c",
        ".cc",
        ".cmake",
        ".cpp",
        ".cxx",
        ".h",
        ".hh",
        ".hpp",
        ".hxx",
        ".in",
        ".inc",
        ".inl",
        ".ipp",
        ".ixx",
        ".tpp",
    }
)
_NATIVE_BUILD_PYPROJECT_SECTIONS = frozenset(
    {
        "build-system",
        "tool.setuptools",
        "tool.setuptools.package-data",
    }
)
_NATIVE_BUILD_TOML_TABLE_RE = re.compile(
    r"^\s*\[([A-Za-z0-9_.-]+)\]\s*(?:#.*)?$"
)
_NATIVE_BINARY_PROVENANCE_MARKER_RE = re.compile(
    rb"MOIRA_NATIVE_BUILD_INPUT_MANIFEST_SHA256=([0-9a-f]{64})"
)


class MutationAssuranceError(RuntimeError):
    """A mutation catalogue, execution, or receipt failed closed."""


class _DuplicateKeyError(ValueError):
    """Strict JSON encountered a duplicate object key."""


@dataclass(frozen=True, slots=True)
class FailureExpectation:
    exception_type: str
    message_contains: tuple[str, ...]
    longrepr_contains: tuple[str, ...]
    metamorphic_witness: Mapping[str, str] | None


@dataclass(frozen=True, slots=True)
class MutantSpec:
    mutant_id: str
    criticality: str
    fault_archetype: str
    operator: str
    source_path: str
    target_qualname: str
    preimage: str
    replacement: str
    occurrence_count: int
    source_hash_mode: str
    preimage_sha256: str
    postimage_sha256: str
    preimage_ast_sha256: str
    postimage_ast_sha256: str
    preimage_code_sha256: str
    postimage_code_sha256: str
    patch_sha256: str
    intended_killer_nodeid: str
    expected_claim_id: str
    expected_contract_sha256: str
    evidence_class: str
    expected_failure: FailureExpectation
    requires_native_backend: bool
    timeout_seconds: int
    exclusions: tuple[str, ...]

    @property
    def module_name(self) -> str:
        return self.source_path[:-3].replace("/", ".")


@dataclass(frozen=True, slots=True)
class MutationCatalogue:
    path: Path
    sha256: str
    policy: Mapping[str, object]
    mutants: tuple[MutantSpec, ...]


@dataclass(frozen=True, slots=True)
class FileIdentity:
    path: str
    bytes: int
    sha256: str


@dataclass(frozen=True, slots=True)
class GitExecutableIdentity:
    path: str
    bytes: int
    sha256: str
    runtime_files: tuple[FileIdentity, ...]
    runtime_manifest_sha256: str


@dataclass(frozen=True, slots=True)
class SnapshotInputs:
    files: tuple[FileIdentity, ...]
    deleted_tracked: tuple[str, ...]
    native_backend_path: str
    git_executable: GitExecutableIdentity
    untracked_exclude_policy: tuple[str, ...]
    manifest_sha256: str

    @property
    def by_path(self) -> Mapping[str, FileIdentity]:
        return MappingProxyType({item.path: item for item in self.files})


@dataclass(frozen=True, slots=True)
class ProcessObservation:
    argv: tuple[str, ...]
    returncode: int | None
    timed_out: bool
    duration_ns: int
    stdout: str
    stderr: str
    stdout_sha256: str
    stderr_sha256: str
    output_truncated: bool
    report: Mapping[str, object] | None
    report_sha256: str | None
    report_error: str | None


@dataclass(frozen=True, slots=True)
class _ReceiptPublicationOwnership:
    token: str
    directory_device: int
    directory_inode: int
    marker_device: int
    marker_inode: int
    complete_raw: bytes


@dataclass(frozen=True, slots=True)
class _ReceiptRunClaim:
    path: Path
    token: str
    device: int
    inode: int
    raw: bytes


def canonical_json_bytes(value: object) -> bytes:
    """Return the one admitted ASCII JSON representation."""

    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("ascii")
        + b"\n"
    )


def pretty_json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            sort_keys=True,
            indent=2,
        ).encode("ascii")
        + b"\n"
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_source_bytes(source: bytes) -> bytes:
    """Return the portable ``utf8_lf_v1`` scientific-source identity."""

    try:
        text = source.decode("utf-8")
    except UnicodeError as exc:
        raise MutationAssuranceError("mutation source is not strict UTF-8") from exc
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKeyError(f"duplicate object key {key!r}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise ValueError(f"non-finite JSON constant {value!r}")


def _validate_json_shape(value: object, *, label: str) -> None:
    count = 0
    pending: list[tuple[object, int]] = [(value, 1)]
    while pending:
        current, depth = pending.pop()
        count += 1
        if count > _MAX_JSON_NODES:
            raise MutationAssuranceError(f"{label} contains too many values")
        if depth > _MAX_JSON_DEPTH:
            raise MutationAssuranceError(f"{label} is nested too deeply")
        if isinstance(current, dict):
            pending.extend((item, depth + 1) for item in current.values())
        elif isinstance(current, list):
            pending.extend((item, depth + 1) for item in current)
        elif isinstance(current, float) and not math.isfinite(current):
            raise MutationAssuranceError(f"{label} contains a non-finite number")
        elif not isinstance(current, (str, int, float, bool, type(None))):
            raise MutationAssuranceError(f"{label} contains an unsupported value")


def strict_json_bytes(raw: bytes, *, label: str) -> object:
    if len(raw) > _MAX_JSON_BYTES:
        raise MutationAssuranceError(f"{label} exceeds the byte limit")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except (UnicodeError, ValueError, _DuplicateKeyError) as exc:
        raise MutationAssuranceError(f"{label} is not strict JSON: {exc}") from exc
    _validate_json_shape(value, label=label)
    return value


def strict_json_file(path: Path, *, label: str) -> object:
    raw = stable_file_bytes(path, maximum_bytes=_MAX_JSON_BYTES, label=label)
    return strict_json_bytes(raw, label=label)


def _safe_relative_path(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 4096:
        raise MutationAssuranceError(f"{label} must be nonblank text")
    if "\\" in value or any(character in value for character in "*?[]\0"):
        raise MutationAssuranceError(f"{label} must be an exact POSIX path")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise MutationAssuranceError(f"{label} escapes the repository")
    for part in path.parts:
        stem = part.rstrip(" .").split(".", 1)[0].upper()
        if stem in _WINDOWS_RESERVED or part.endswith((" ", ".")):
            raise MutationAssuranceError(f"{label} is unsafe on Windows")
    return path.as_posix()


def _intended_test_coordinates(nodeid: str) -> tuple[str, str, str]:
    components = nodeid.split("::")
    if len(components) != 2:
        raise MutationAssuranceError(
            "intended killer must be one top-level pytest function"
        )
    relative = _safe_relative_path(
        components[0],
        label="intended killer source path",
    )
    path = PurePosixPath(relative)
    match = _TEST_SELECTOR_RE.fullmatch(components[1])
    if (
        match is None
        or not path.parts
        or path.parts[0] != "tests"
        or path.suffix != ".py"
        or any(
            not part.isidentifier()
            for part in (*path.parts[:-1], path.stem)
        )
    ):
        raise MutationAssuranceError(
            "intended killer is not an admitted top-level test function"
        )
    module_name = ".".join((*path.parts[:-1], path.stem))
    return relative, module_name, match.group("qualname")


def _plain_text(value: object, *, label: str, maximum: int = 16_384) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > maximum
        or "\0" in value
    ):
        raise MutationAssuranceError(f"{label} must be bounded nonblank text")
    return value


def _text_tuple(
    value: object,
    *,
    label: str,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    if not isinstance(value, list) or (not value and not allow_empty):
        raise MutationAssuranceError(f"{label} must be a JSON list")
    result = tuple(
        _plain_text(item, label=f"{label}[{index}]")
        for index, item in enumerate(value)
    )
    if len(set(result)) != len(result):
        raise MutationAssuranceError(f"{label} contains duplicates")
    return result


def _sha256(value: object, *, label: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise MutationAssuranceError(f"{label} must be a lowercase SHA-256")
    return value


def _metadata_signature(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        getattr(metadata, "st_mtime_ns", int(metadata.st_mtime * 1_000_000_000)),
    )


def _is_reparse(metadata: os.stat_result) -> bool:
    return bool(
        getattr(metadata, "st_file_attributes", 0)
        & _WINDOWS_REPARSE_POINT
    )


def stable_file_bytes(
    path: Path,
    *,
    maximum_bytes: int | None,
    label: str,
    require_single_link: bool = True,
) -> bytes:
    """Read one unchanged, real, single-link regular file."""

    try:
        before = path.lstat()
    except OSError as exc:
        raise MutationAssuranceError(f"{label} is unavailable: {path}: {exc}") from exc
    if (
        not stat.S_ISREG(before.st_mode)
        or stat.S_ISLNK(before.st_mode)
        or _is_reparse(before)
    ):
        raise MutationAssuranceError(f"{label} is not a plain regular file: {path}")
    if require_single_link and before.st_nlink != 1:
        raise MutationAssuranceError(f"{label} must not be hard-linked: {path}")
    if maximum_bytes is not None and before.st_size > maximum_bytes:
        raise MutationAssuranceError(f"{label} exceeds its byte limit: {path}")
    try:
        with path.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            if _metadata_signature(opened) != _metadata_signature(before):
                raise MutationAssuranceError(f"{label} changed during secure open")
            raw = stream.read(
                -1 if maximum_bytes is None else maximum_bytes + 1
            )
            after_open = os.fstat(stream.fileno())
        after_path = path.lstat()
    except MutationAssuranceError:
        raise
    except OSError as exc:
        raise MutationAssuranceError(f"{label} could not be read: {path}: {exc}") from exc
    if maximum_bytes is not None and len(raw) > maximum_bytes:
        raise MutationAssuranceError(f"{label} exceeds its byte limit: {path}")
    if (
        _metadata_signature(after_open) != _metadata_signature(opened)
        or _metadata_signature(after_path) != _metadata_signature(before)
    ):
        raise MutationAssuranceError(f"{label} changed while being read: {path}")
    return raw


def git_executable_identity(path: Path) -> GitExecutableIdentity:
    """Bind one absolute Git engine and its adjacent Windows runtime files."""

    try:
        absolute = Path(os.path.abspath(os.fspath(path)))
    except (OSError, TypeError, ValueError) as exc:
        raise MutationAssuranceError(
            f"Git executable path is invalid: {exc}"
        ) from exc
    if not path.is_absolute() or not absolute.is_absolute() or not absolute.anchor:
        raise MutationAssuranceError("Git executable path must be absolute")
    current = Path(absolute.anchor)
    parts = absolute.parts[1:]
    if not parts:
        raise MutationAssuranceError("Git executable path names a filesystem root")
    for index, part in enumerate(parts):
        current = current / part
        try:
            metadata = current.lstat()
        except OSError as exc:
            raise MutationAssuranceError(
                f"Git executable path component is unavailable: {current}: {exc}"
            ) from exc
        if stat.S_ISLNK(metadata.st_mode) or _is_reparse(metadata):
            raise MutationAssuranceError(
                f"Git executable path crosses a link or reparse point: {current}"
            )
        final = index == len(parts) - 1
        if not final and not stat.S_ISDIR(metadata.st_mode):
            raise MutationAssuranceError(
                f"Git executable parent is not a directory: {current}"
            )
        if final and not stat.S_ISREG(metadata.st_mode):
            raise MutationAssuranceError(
                f"Git executable is not a plain regular file: {current}"
            )
    try:
        resolved = absolute.resolve(strict=True)
    except OSError as exc:
        raise MutationAssuranceError(
            f"Git executable cannot be resolved: {exc}"
        ) from exc
    if os.path.normcase(os.fspath(resolved)) != os.path.normcase(
        os.fspath(absolute)
    ):
        raise MutationAssuranceError(
            "Git executable lexical and resolved paths differ"
        )
    if not os.access(absolute, os.X_OK):
        raise MutationAssuranceError("Git executable is not executable")
    raw = stable_file_bytes(
        absolute,
        maximum_bytes=_MAX_RUNTIME_FILE_BYTES,
        label="Git executable",
        require_single_link=True,
    )
    runtime_paths = [absolute]
    if os.name == "nt":
        try:
            with os.scandir(absolute.parent) as entries:
                runtime_paths.extend(
                    Path(entry.path)
                    for entry in entries
                    if entry.name.casefold().endswith(".dll")
                )
        except OSError as exc:
            raise MutationAssuranceError(
                f"Git runtime directory cannot be enumerated: {exc}"
            ) from exc
    runtime_identities: list[FileIdentity] = []
    folded_names: dict[str, str] = {}
    for runtime_path in sorted(runtime_paths, key=lambda value: value.name.casefold()):
        name = runtime_path.name
        if (
            not name
            or name in {".", ".."}
            or "/" in name
            or "\\" in name
            or "\0" in name
        ):
            raise MutationAssuranceError("Git runtime filename is invalid")
        folded = name.casefold()
        prior = folded_names.get(folded)
        if prior is not None and prior != name:
            raise MutationAssuranceError(
                f"Git runtime filenames collide by case: {prior!r}, {name!r}"
            )
        folded_names[folded] = name
        runtime_raw = stable_file_bytes(
            runtime_path,
            maximum_bytes=_MAX_RUNTIME_FILE_BYTES,
            label=f"Git runtime file {name}",
            require_single_link=runtime_path == absolute,
        )
        runtime_identities.append(
            FileIdentity(
                path=name,
                bytes=len(runtime_raw),
                sha256=sha256_bytes(runtime_raw),
            )
        )
    runtime_files = tuple(runtime_identities)
    runtime_manifest = {
        "files": [
            {
                "bytes": item.bytes,
                "path": item.path,
                "sha256": item.sha256,
            }
            for item in runtime_files
        ],
        "schema_version": 1,
        "source_path": str(absolute),
    }
    return GitExecutableIdentity(
        path=str(absolute),
        bytes=len(raw),
        sha256=sha256_bytes(raw),
        runtime_files=runtime_files,
        runtime_manifest_sha256=sha256_bytes(
            canonical_json_bytes(runtime_manifest)
        ),
    )


def _git_executable_payload(
    identity: GitExecutableIdentity,
) -> dict[str, object]:
    return {
        "path": identity.path,
        "bytes": identity.bytes,
        "sha256": identity.sha256,
        "runtime_files": [
            {
                "bytes": item.bytes,
                "path": item.path,
                "sha256": item.sha256,
            }
            for item in identity.runtime_files
        ],
        "runtime_manifest_sha256": identity.runtime_manifest_sha256,
    }


def _git_executable_from_payload(value: object) -> GitExecutableIdentity:
    payload = _object(value, label="snapshot Git executable")
    _exact_fields(
        payload,
        {
            "path",
            "bytes",
            "sha256",
            "runtime_files",
            "runtime_manifest_sha256",
        },
        label="snapshot Git executable",
    )
    path = payload["path"]
    byte_count = payload["bytes"]
    if (
        not isinstance(path, str)
        or not path
        or not Path(path).is_absolute()
        or isinstance(byte_count, bool)
        or not isinstance(byte_count, int)
        or byte_count <= 0
    ):
        raise MutationAssuranceError("snapshot Git executable identity is invalid")
    runtime_files: list[FileIdentity] = []
    for index, raw_identity in enumerate(
        _list(payload["runtime_files"], label="snapshot Git runtime files")
    ):
        identity = _object(
            raw_identity,
            label=f"snapshot Git runtime files[{index}]",
        )
        _exact_fields(
            identity,
            {"path", "bytes", "sha256"},
            label=f"snapshot Git runtime files[{index}]",
        )
        name = _safe_relative_path(
            identity["path"],
            label=f"snapshot Git runtime files[{index}].path",
        )
        if "/" in name:
            raise MutationAssuranceError(
                "snapshot Git runtime file must be one leaf name"
            )
        runtime_bytes = identity["bytes"]
        if (
            isinstance(runtime_bytes, bool)
            or not isinstance(runtime_bytes, int)
            or runtime_bytes <= 0
        ):
            raise MutationAssuranceError(
                "snapshot Git runtime byte count is invalid"
            )
        runtime_files.append(
            FileIdentity(
                path=name,
                bytes=runtime_bytes,
                sha256=_sha256(
                    identity["sha256"],
                    label=f"snapshot Git runtime files[{index}].sha256",
                ),
            )
        )
    runtime_tuple = tuple(runtime_files)
    runtime_names = tuple(item.path for item in runtime_tuple)
    if (
        not runtime_tuple
        or runtime_names != tuple(sorted(set(runtime_names), key=str.casefold))
        or Path(path).name not in runtime_names
    ):
        raise MutationAssuranceError(
            "snapshot Git runtime files are not exact, unique, and sorted"
        )
    runtime_manifest = {
        "files": [
            {
                "bytes": item.bytes,
                "path": item.path,
                "sha256": item.sha256,
            }
            for item in runtime_tuple
        ],
        "schema_version": 1,
        "source_path": path,
    }
    runtime_manifest_sha256 = _sha256(
        payload["runtime_manifest_sha256"],
        label="snapshot Git runtime manifest sha256",
    )
    if runtime_manifest_sha256 != sha256_bytes(
        canonical_json_bytes(runtime_manifest)
    ):
        raise MutationAssuranceError(
            "snapshot Git runtime manifest digest is invalid"
        )
    engine = next(item for item in runtime_tuple if item.path == Path(path).name)
    executable_sha256 = _sha256(
        payload["sha256"],
        label="snapshot Git executable sha256",
    )
    if engine.bytes != byte_count or engine.sha256 != executable_sha256:
        raise MutationAssuranceError(
            "snapshot Git engine contradicts its runtime manifest"
        )
    return GitExecutableIdentity(
        path=path,
        bytes=byte_count,
        sha256=executable_sha256,
        runtime_files=runtime_tuple,
        runtime_manifest_sha256=runtime_manifest_sha256,
    )


def git_runtime_copy_state(
    executable: Path,
    identity: GitExecutableIdentity,
    *,
    private_copy: bool = True,
) -> str:
    """Validate one private single-link runtime copy and bind its live state."""

    if not executable.is_absolute() or executable.name != Path(identity.path).name:
        raise MutationAssuranceError(
            "private Git executable path is not absolute and source-named"
        )
    directory = executable.parent
    current = Path(directory.anchor)
    for part in directory.parts[1:]:
        current = current / part
        try:
            metadata = current.lstat()
        except OSError as exc:
            raise MutationAssuranceError(
                f"private Git runtime path is unavailable: {current}: {exc}"
            ) from exc
        if stat.S_ISLNK(metadata.st_mode) or _is_reparse(metadata):
            raise MutationAssuranceError(
                f"private Git runtime crosses a link or reparse point: {current}"
            )
        if not stat.S_ISDIR(metadata.st_mode):
            raise MutationAssuranceError(
                f"private Git runtime parent is not a directory: {current}"
            )
    try:
        directory_metadata = directory.lstat()
        with os.scandir(directory) as entries:
            observed = sorted(entries, key=lambda entry: entry.name.casefold())
    except OSError as exc:
        raise MutationAssuranceError(
            f"private Git runtime cannot be enumerated: {exc}"
        ) from exc
    expected_names = tuple(item.path for item in identity.runtime_files)
    observed_by_name = {entry.name: entry for entry in observed}
    if len(observed_by_name) != len(observed):
        raise MutationAssuranceError("Git runtime filenames are not unique")
    if private_copy and tuple(entry.name for entry in observed) != expected_names:
        raise MutationAssuranceError("private Git runtime file set is not exact")
    if any(name not in observed_by_name for name in expected_names):
        raise MutationAssuranceError("Git runtime omits an admitted file")
    state_files: list[dict[str, object]] = []
    for expected in identity.runtime_files:
        entry = observed_by_name[expected.path]
        path = Path(entry.path)
        try:
            metadata = path.lstat()
        except OSError as exc:
            raise MutationAssuranceError(
                f"private Git runtime file is unavailable: {path}: {exc}"
            ) from exc
        if (
            not stat.S_ISREG(metadata.st_mode)
            or stat.S_ISLNK(metadata.st_mode)
            or _is_reparse(metadata)
            or (
                metadata.st_nlink != 1
                and (private_copy or path == executable)
            )
        ):
            raise MutationAssuranceError(
                f"private Git runtime file is not plain and single-link: {path}"
            )
        raw = stable_file_bytes(
            path,
            maximum_bytes=_MAX_RUNTIME_FILE_BYTES,
            label=f"private Git runtime file {expected.path}",
            require_single_link=private_copy or path == executable,
        )
        if len(raw) != expected.bytes or sha256_bytes(raw) != expected.sha256:
            raise MutationAssuranceError(
                f"private Git runtime file differs from admission: {expected.path}"
            )
        state_files.append(
            {
                "metadata": [*_metadata_signature(metadata), metadata.st_nlink],
                "path": expected.path,
            }
        )
    return sha256_bytes(
        canonical_json_bytes(
            {
                "directory_metadata": [
                    *_metadata_signature(directory_metadata),
                    directory_metadata.st_nlink,
                ],
                "files": state_files,
                "runtime_manifest_sha256": identity.runtime_manifest_sha256,
                "schema_version": 1,
            }
        )
    )


def lock_git_runtime_for_execution(
    executable: Path,
    identity: GitExecutableIdentity,
    *,
    private_copy: bool,
) -> tuple[int, ...]:
    """Deny Windows write/delete access to the admitted runtime during exec.

    Metadata replay detects ordinary replacement, but an adversary able to
    restore timestamps can defeat that observation.  On Windows these handles
    keep the runtime directory and every admitted engine/DLL file open with
    read sharing only until the subprocess and its post-execution replay are
    complete.  The directory handle prevents renaming that directory; Windows
    does not make it a membership lock.  A hostile same-user process can still
    add and remove transient, previously unadmitted DLL/helper names without
    changing the final replayed directory state.

    POSIX execution retains the documented cooperative-host-filesystem
    boundary.  Python does not expose a portable execute-by-pinned-descriptor
    primitive for this subprocess path.
    """

    git_runtime_copy_state(
        executable,
        identity,
        private_copy=private_copy,
    )
    if os.name != "nt":
        return ()

    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_file = kernel32.CreateFileW
    create_file.argtypes = (
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    )
    create_file.restype = wintypes.HANDLE
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = (wintypes.HANDLE,)
    close_handle.restype = wintypes.BOOL

    generic_read = 0x80000000
    file_read_attributes = 0x00000080
    file_share_read = 0x00000001
    open_existing = 3
    file_flag_backup_semantics = 0x02000000
    invalid_handle = ctypes.c_void_p(-1).value
    targets = (
        (executable.parent, file_read_attributes, file_flag_backup_semantics),
        *(
            (executable.parent / item.path, generic_read, 0)
            for item in identity.runtime_files
        ),
    )
    handles: list[int] = []
    try:
        for path, access, flags in targets:
            handle = create_file(
                str(path),
                access,
                file_share_read,
                None,
                open_existing,
                flags,
                None,
            )
            if handle in {None, invalid_handle}:
                error = ctypes.get_last_error()
                raise MutationAssuranceError(
                    "Git runtime execution lock failed for "
                    f"{path}: [{error}] {ctypes.FormatError(error)}"
                )
            handles.append(int(handle))
    except BaseException:
        for handle in reversed(handles):
            close_handle(handle)
        raise
    return tuple(handles)


def unlock_git_runtime_for_execution(handles: Sequence[int]) -> None:
    """Release every handle returned by ``lock_git_runtime_for_execution``."""

    if os.name != "nt":
        if tuple(handles):
            raise MutationAssuranceError(
                "non-Windows Git runtime lock set is not empty"
            )
        return

    import ctypes
    from ctypes import wintypes

    values = tuple(handles)
    if (
        len(set(values)) != len(values)
        or any(isinstance(value, bool) or not isinstance(value, int) or value <= 0 for value in values)
    ):
        raise MutationAssuranceError("Git runtime execution lock set is invalid")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = (wintypes.HANDLE,)
    close_handle.restype = wintypes.BOOL
    errors: list[str] = []
    for handle in reversed(values):
        if not close_handle(handle):
            error = ctypes.get_last_error()
            errors.append(f"[{error}] {ctypes.FormatError(error)}")
    if errors:
        raise MutationAssuranceError(
            "Git runtime execution lock release failed: " + "; ".join(errors)
        )


def windows_directory_path() -> Path:
    """Resolve the OS Windows directory without drive or environment guesses."""

    if os.name != "nt":
        raise MutationAssuranceError("Windows directory lookup is Windows-only")
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    get_windows_directory = kernel32.GetWindowsDirectoryW
    get_windows_directory.argtypes = (wintypes.LPWSTR, wintypes.UINT)
    get_windows_directory.restype = wintypes.UINT
    size = 260
    while True:
        buffer = ctypes.create_unicode_buffer(size)
        copied = get_windows_directory(buffer, size)
        if copied == 0:
            error = ctypes.get_last_error()
            raise MutationAssuranceError(
                "Windows directory lookup failed: "
                f"[{error}] {ctypes.FormatError(error)}"
            )
        if copied < size:
            value = buffer.value
            break
        size = copied + 1
        if size > 32_768:
            raise MutationAssuranceError("Windows directory path is too long")

    absolute = Path(os.path.abspath(value))
    if not absolute.is_absolute() or not absolute.anchor:
        raise MutationAssuranceError("Windows directory path is not absolute")
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current = current / part
        try:
            metadata = current.lstat()
        except OSError as exc:
            raise MutationAssuranceError(
                f"Windows directory path is unavailable: {current}: {exc}"
            ) from exc
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or stat.S_ISLNK(metadata.st_mode)
            or _is_reparse(metadata)
        ):
            raise MutationAssuranceError(
                f"Windows directory path is not plain: {current}"
            )
    try:
        resolved = absolute.resolve(strict=True)
    except OSError as exc:
        raise MutationAssuranceError(
            f"Windows directory cannot be resolved: {exc}"
        ) from exc
    if os.path.normcase(os.fspath(resolved)) != os.path.normcase(
        os.fspath(absolute)
    ):
        raise MutationAssuranceError(
            "Windows directory lexical and resolved paths differ"
        )
    return absolute


def _git_subprocess_environment() -> dict[str, str]:
    """Return Git's complete environment; no ambient Git/user policy survives."""

    environment = {
        "GIT_ATTR_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_TERMINAL_PROMPT": "0",
        "LANG": "C",
        "LC_ALL": "C",
    }
    if os.name == "nt":
        windows = str(windows_directory_path())
        environment["SYSTEMROOT"] = windows
        environment["WINDIR"] = windows
    return environment


def _run_git_command(
    command: Sequence[str],
    *,
    root: Path,
    git_executable: Path,
    git_identity: GitExecutableIdentity,
    private_runtime: bool,
    text: bool,
    timeout: int,
) -> subprocess.CompletedProcess[Any]:
    if not command or command[0] != str(git_executable):
        raise MutationAssuranceError(
            "Git command does not invoke the admitted absolute executable"
        )
    before = git_runtime_copy_state(
        git_executable,
        git_identity,
        private_copy=private_runtime,
    )
    handles = lock_git_runtime_for_execution(
        git_executable,
        git_identity,
        private_copy=private_runtime,
    )
    try:
        locked = git_runtime_copy_state(
            git_executable,
            git_identity,
            private_copy=private_runtime,
        )
        if locked != before:
            raise MutationAssuranceError(
                "private Git runtime changed while acquiring execution locks"
            )
        try:
            completed = subprocess.run(
                command,
                cwd=root,
                check=False,
                capture_output=True,
                text=text,
                shell=False,
                timeout=timeout,
                env=_git_subprocess_environment(),
            )
        finally:
            after = git_runtime_copy_state(
                git_executable,
                git_identity,
                private_copy=private_runtime,
            )
            if after != locked:
                raise MutationAssuranceError(
                    "private Git runtime changed during command execution"
                )
    finally:
        unlock_git_runtime_for_execution(handles)
    return completed


def _normalized_code(code: CodeType) -> CodeType:
    constants = tuple(
        _normalized_code(value) if isinstance(value, CodeType) else value
        for value in code.co_consts
    )
    return code.replace(
        co_consts=constants,
        co_filename="",
        co_firstlineno=1,
    )


def python_code_sha256(code: CodeType) -> str:
    """Return the filename-independent ``python_code_v1`` digest."""

    return sha256_bytes(marshal.dumps(_normalized_code(code)))


def structural_python_code_sha256(code: CodeType) -> str:
    """Return the canonical structural digest owned by the toolchain sealer."""

    from support.mutation_toolchain import (
        PYTHON_CODE_STRUCTURAL_ALGORITHM,
        structural_python_code_sha256 as digest,
    )

    if PYTHON_CODE_STRUCTURAL_ALGORITHM != INTENDED_TEST_CODE_DIGEST_ALGORITHM:
        raise MutationAssuranceError(
            "test toolchain structural code algorithm changed"
        )
    try:
        return digest(code)
    except Exception as exc:
        raise MutationAssuranceError(
            f"structural Python code identity failed: {exc}"
        ) from exc


def _qualified_code_sha256(module_code: CodeType, *, qualname: str) -> str:
    matches: list[CodeType] = []
    pending = [module_code]
    while pending:
        code = pending.pop()
        if code.co_qualname == qualname:
            matches.append(code)
        pending.extend(
            value for value in code.co_consts if isinstance(value, CodeType)
        )
    if len(matches) != 1:
        raise MutationAssuranceError(
            f"target qualname {qualname!r} resolved to {len(matches)} code objects"
        )
    return python_code_sha256(matches[0])


def python_source_code_sha256(
    source: bytes,
    *,
    qualname: str,
    filename: str = "<mutation-source>",
) -> str:
    """Compile bytes and hash the one exact qualified code object."""

    try:
        module_code = compile(source, filename, "exec", dont_inherit=True, optimize=0)
    except (SyntaxError, ValueError) as exc:
        raise MutationAssuranceError(f"mutation source cannot compile: {exc}") from exc
    return _qualified_code_sha256(module_code, qualname=qualname)


def pytest_rewritten_source_code_sha256(
    source: bytes,
    *,
    qualname: str,
    filename: str,
) -> str:
    """Hash the exact assertion-rewritten test function admitted by Phase 11."""

    try:
        tree = ast.parse(source, filename=filename)
        from _pytest.assertion.rewrite import rewrite_asserts

        # Phase 11 admits only the disabled assertion-pass-hook policy.  Passing
        # no Config is pytest's explicit false-policy path and avoids ambient
        # configuration while preserving ordinary assertion rewriting.
        rewrite_asserts(tree, source, filename, None)
        module_code = compile(
            tree,
            filename,
            "exec",
            dont_inherit=True,
            optimize=0,
        )
    except (SyntaxError, TypeError, ValueError) as exc:
        raise MutationAssuranceError(
            f"intended test source cannot be assertion-rewritten: {exc}"
        ) from exc
    matches: list[CodeType] = []
    pending = [module_code]
    while pending:
        code = pending.pop()
        if code.co_qualname == qualname:
            matches.append(code)
        pending.extend(
            value for value in code.co_consts if isinstance(value, CodeType)
        )
    if len(matches) != 1:
        raise MutationAssuranceError(
            f"target qualname {qualname!r} resolved to {len(matches)} code objects"
        )
    return structural_python_code_sha256(matches[0])


def apply_exact_mutation(spec: MutantSpec, source: bytes) -> bytes:
    """Apply one reviewed UTF-8 mutation while preserving checkout EOLs."""

    if spec.operator != "replace_exact_utf8_v1":
        raise MutationAssuranceError("mutation operator is not admitted")
    if spec.source_hash_mode != SOURCE_HASH_MODE:
        raise MutationAssuranceError("mutation source hash mode is not admitted")
    canonical_source_bytes(source)
    try:
        canonical_preimage = spec.preimage.encode("utf-8")
        canonical_replacement = spec.replacement.encode("utf-8")
    except UnicodeError as exc:
        raise MutationAssuranceError("mutation text is not UTF-8") from exc
    candidates = [(canonical_preimage, canonical_replacement)]
    crlf_preimage = canonical_preimage.replace(b"\n", b"\r\n")
    if crlf_preimage != canonical_preimage:
        candidates.append(
            (
                crlf_preimage,
                canonical_replacement.replace(b"\n", b"\r\n"),
            )
        )
    cr_preimage = canonical_preimage.replace(b"\n", b"\r")
    if cr_preimage not in {candidate[0] for candidate in candidates}:
        candidates.append(
            (
                cr_preimage,
                canonical_replacement.replace(b"\n", b"\r"),
            )
        )
    matches = [
        (preimage, replacement, source.count(preimage))
        for preimage, replacement in candidates
    ]
    occurrences = sum(count for _preimage, _replacement, count in matches)
    if occurrences != spec.occurrence_count or occurrences != 1:
        raise MutationAssuranceError(
            f"{spec.mutant_id}: expected one preimage occurrence, observed {occurrences}"
        )
    preimage, replacement, _count = next(
        match for match in matches if match[2] == 1
    )
    if preimage == replacement:
        raise MutationAssuranceError(f"{spec.mutant_id}: mutation is a no-op")
    mutated = source.replace(preimage, replacement, 1)
    if mutated == source:
        raise MutationAssuranceError(f"{spec.mutant_id}: mutation made no change")
    return mutated


def mutation_patch_sha256(
    *,
    source_path: str,
    operator: str,
    preimage: str,
    replacement: str,
) -> str:
    return sha256_bytes(
        canonical_json_bytes(
            {
                "operator": operator,
                "preimage": preimage,
                "replacement": replacement,
                "source_path": source_path,
            }
        )
    )


def deterministic_mutation_seed(mutant_id: str) -> int:
    """Derive the one admitted baseline/mutant seed from the mutant identity."""

    if _MUTANT_ID_RE.fullmatch(mutant_id) is None:
        raise MutationAssuranceError("mutation seed requires a valid Phase 11 ID")
    return int.from_bytes(
        hashlib.sha256(mutant_id.encode("ascii")).digest()[:8],
        "big",
    )


def mutation_execution_id(spec: MutantSpec, role: str) -> str:
    """Return the role-separated, replayable child execution identity."""

    if role not in {"baseline", "mutant"}:
        raise MutationAssuranceError("mutation execution role is invalid")
    short = hashlib.sha256(spec.mutant_id.encode("ascii")).hexdigest()[:12]
    return f"{role}-{short}"


def _canonical_ast_sha256(source: bytes, *, qualname: str) -> str:
    from _pytest_plugins.evidence_schema import canonical_python_ast_sha256

    with tempfile.TemporaryDirectory(prefix="moira-mutation-ast-") as directory:
        path = Path(directory) / "source.py"
        path.write_bytes(source)
        try:
            return canonical_python_ast_sha256(path, (qualname,))
        except (OSError, SyntaxError, ValueError) as exc:
            raise MutationAssuranceError(
                f"canonical target AST cannot be derived: {exc}"
            ) from exc


def _base_nodeid_matches(nodeid: str, base: str) -> bool:
    return nodeid == base or nodeid.startswith(base + "[")


def _parse_failure_expectation(value: object, *, label: str) -> FailureExpectation:
    if not isinstance(value, dict) or set(value) != {
        "exception_type",
        "message_contains",
        "longrepr_contains",
        "metamorphic_witness",
    }:
        raise MutationAssuranceError(f"{label} fields are not exact")
    exception_type = _plain_text(value["exception_type"], label=f"{label}.exception_type")
    if _QUALNAME_RE.fullmatch(exception_type) is None:
        raise MutationAssuranceError(f"{label}.exception_type is not qualified")
    messages = _text_tuple(
        value["message_contains"],
        label=f"{label}.message_contains",
        allow_empty=True,
    )
    longrepr = _text_tuple(
        value["longrepr_contains"],
        label=f"{label}.longrepr_contains",
        allow_empty=True,
    )
    raw_witness = value["metamorphic_witness"]
    witness: Mapping[str, str] | None
    if raw_witness is None:
        witness = None
    elif isinstance(raw_witness, dict) and set(raw_witness) == {
        "relation_id",
        "mutant_id",
        "metric",
    }:
        witness = MappingProxyType(
            {
                key: _plain_text(raw_witness[key], label=f"{label}.{key}")
                for key in ("relation_id", "mutant_id", "metric")
            }
        )
    else:
        raise MutationAssuranceError(f"{label}.metamorphic_witness is malformed")
    if witness is not None and exception_type != "support.metamorphic.MetamorphicViolation":
        raise MutationAssuranceError(
            f"{label} has a metamorphic witness for the wrong exception type"
        )
    return FailureExpectation(
        exception_type=exception_type,
        message_contains=messages,
        longrepr_contains=longrepr,
        metamorphic_witness=witness,
    )


def _parse_mutant(
    value: object,
    *,
    index: int,
    root: Path,
    contracts: Mapping[str, object],
    verify_sources: bool,
) -> MutantSpec:
    label = f"mutants[{index}]"
    expected_fields = {
        "mutant_id",
        "criticality",
        "fault_archetype",
        "operator",
        "source_path",
        "target_qualname",
        "preimage",
        "replacement",
        "occurrence_count",
        "source_hash_mode",
        "preimage_sha256",
        "postimage_sha256",
        "preimage_ast_sha256",
        "postimage_ast_sha256",
        "preimage_code_sha256",
        "postimage_code_sha256",
        "patch_sha256",
        "intended_killer_nodeid",
        "expected_claim_id",
        "expected_contract_sha256",
        "evidence_class",
        "expected_failure",
        "requires_native_backend",
        "timeout_seconds",
        "exclusions",
    }
    if not isinstance(value, dict) or set(value) != expected_fields:
        raise MutationAssuranceError(f"{label} fields are not exact")
    mutant_id = _plain_text(value["mutant_id"], label=f"{label}.mutant_id")
    if _MUTANT_ID_RE.fullmatch(mutant_id) is None:
        raise MutationAssuranceError(f"{label}.mutant_id is not a Phase 11 ID")
    criticality = value["criticality"]
    if criticality not in {"critical", "supplemental"}:
        raise MutationAssuranceError(f"{label}.criticality is invalid")
    operator = value["operator"]
    if operator != "replace_exact_utf8_v1":
        raise MutationAssuranceError(f"{label}.operator is not admitted")
    source_path = _safe_relative_path(value["source_path"], label=f"{label}.source_path")
    if not source_path.startswith("moira/") or not source_path.endswith(".py"):
        raise MutationAssuranceError(
            f"{label}.source_path must be a Python engine source under moira/"
        )
    target_qualname = _plain_text(
        value["target_qualname"], label=f"{label}.target_qualname"
    )
    if _QUALNAME_RE.fullmatch(target_qualname) is None:
        raise MutationAssuranceError(f"{label}.target_qualname is invalid")
    preimage = _plain_text(value["preimage"], label=f"{label}.preimage")
    replacement = _plain_text(value["replacement"], label=f"{label}.replacement")
    if "\r" in preimage or "\r" in replacement:
        raise MutationAssuranceError(
            f"{label} mutation text must use canonical LF line endings"
        )
    source_hash_mode = value["source_hash_mode"]
    if source_hash_mode != SOURCE_HASH_MODE:
        raise MutationAssuranceError(f"{label}.source_hash_mode is not admitted")
    if value["occurrence_count"] != 1:
        raise MutationAssuranceError(f"{label}.occurrence_count must be exactly one")
    nodeid = _plain_text(
        value["intended_killer_nodeid"],
        label=f"{label}.intended_killer_nodeid",
    )
    try:
        _intended_test_coordinates(nodeid)
    except MutationAssuranceError as exc:
        raise MutationAssuranceError(
            f"{label}.intended_killer_nodeid is invalid: {exc}"
        ) from exc
    claim_id = _plain_text(value["expected_claim_id"], label=f"{label}.expected_claim_id")
    if _CLAIM_ID_RE.fullmatch(claim_id) is None or claim_id not in contracts:
        raise MutationAssuranceError(f"{label}.expected_claim_id is unknown")
    from _pytest_plugins.evidence_schema import contract_sha256

    contract = contracts[claim_id]
    contract_digest = contract_sha256(contract)
    expected_contract_digest = _sha256(
        value["expected_contract_sha256"],
        label=f"{label}.expected_contract_sha256",
    )
    if expected_contract_digest != contract_digest:
        raise MutationAssuranceError(f"{label} carries a stale contract digest")
    admitted_nodeids = getattr(contract, "nodeids", ())
    if not any(_base_nodeid_matches(nodeid, base) for base in admitted_nodeids):
        raise MutationAssuranceError(f"{label} intended killer is not contract-bound")
    coverage_targets = getattr(contract, "coverage_targets", ())
    if not any(
        getattr(target, "path", None) == source_path
        and getattr(target, "qualname", None) == target_qualname
        for target in coverage_targets
    ):
        raise MutationAssuranceError(
            f"{label} mutation target is not bound to the claim coverage target"
        )
    evidence_class = value["evidence_class"]
    actual_class = getattr(getattr(contract, "evidence_class", None), "value", None)
    if evidence_class != actual_class:
        raise MutationAssuranceError(f"{label} evidence class contradicts its claim")
    timeout = value["timeout_seconds"]
    if isinstance(timeout, bool) or not isinstance(timeout, int) or not 5 <= timeout <= 300:
        raise MutationAssuranceError(f"{label}.timeout_seconds is outside [5, 300]")
    requires_native = value["requires_native_backend"]
    if type(requires_native) is not bool:
        raise MutationAssuranceError(f"{label}.requires_native_backend must be boolean")
    spec = MutantSpec(
        mutant_id=mutant_id,
        criticality=str(criticality),
        fault_archetype=_plain_text(value["fault_archetype"], label=f"{label}.fault_archetype"),
        operator=str(operator),
        source_path=source_path,
        target_qualname=target_qualname,
        preimage=preimage,
        replacement=replacement,
        occurrence_count=1,
        source_hash_mode=str(source_hash_mode),
        preimage_sha256=_sha256(value["preimage_sha256"], label=f"{label}.preimage_sha256"),
        postimage_sha256=_sha256(value["postimage_sha256"], label=f"{label}.postimage_sha256"),
        preimage_ast_sha256=_sha256(value["preimage_ast_sha256"], label=f"{label}.preimage_ast_sha256"),
        postimage_ast_sha256=_sha256(value["postimage_ast_sha256"], label=f"{label}.postimage_ast_sha256"),
        preimage_code_sha256=_sha256(value["preimage_code_sha256"], label=f"{label}.preimage_code_sha256"),
        postimage_code_sha256=_sha256(value["postimage_code_sha256"], label=f"{label}.postimage_code_sha256"),
        patch_sha256=_sha256(value["patch_sha256"], label=f"{label}.patch_sha256"),
        intended_killer_nodeid=nodeid,
        expected_claim_id=claim_id,
        expected_contract_sha256=expected_contract_digest,
        evidence_class=str(evidence_class),
        expected_failure=_parse_failure_expectation(value["expected_failure"], label=f"{label}.expected_failure"),
        requires_native_backend=requires_native,
        timeout_seconds=timeout,
        exclusions=_text_tuple(value["exclusions"], label=f"{label}.exclusions"),
    )
    if spec.criticality == "critical" and spec.expected_failure.metamorphic_witness is None:
        raise MutationAssuranceError(f"{label} critical mutant lacks a typed witness")
    calculated_patch = mutation_patch_sha256(
        source_path=source_path,
        operator=spec.operator,
        preimage=preimage,
        replacement=replacement,
    )
    if spec.patch_sha256 != calculated_patch:
        raise MutationAssuranceError(f"{label} patch digest is stale")
    if verify_sources:
        source_file = root / Path(source_path)
        source = stable_file_bytes(
            source_file,
            maximum_bytes=_MAX_MUTATION_SOURCE_BYTES,
            label=f"{label} source",
        )
        canonical_source = canonical_source_bytes(source)
        if sha256_bytes(canonical_source) != spec.preimage_sha256:
            raise MutationAssuranceError(f"{label} source preimage digest is stale")
        mutated = apply_exact_mutation(spec, source)
        canonical_mutated = canonical_source_bytes(mutated)
        if sha256_bytes(canonical_mutated) != spec.postimage_sha256:
            raise MutationAssuranceError(f"{label} source postimage digest is stale")
        if _canonical_ast_sha256(canonical_source, qualname=target_qualname) != spec.preimage_ast_sha256:
            raise MutationAssuranceError(f"{label} target preimage AST digest is stale")
        if _canonical_ast_sha256(canonical_mutated, qualname=target_qualname) != spec.postimage_ast_sha256:
            raise MutationAssuranceError(f"{label} target postimage AST digest is stale")
        if python_source_code_sha256(canonical_source, qualname=target_qualname) != spec.preimage_code_sha256:
            raise MutationAssuranceError(f"{label} target preimage code digest is stale")
        if python_source_code_sha256(canonical_mutated, qualname=target_qualname) != spec.postimage_code_sha256:
            raise MutationAssuranceError(f"{label} target postimage code digest is stale")
    return spec


def _load_catalogue_bytes(
    raw: bytes,
    *,
    path: Path,
    root: Path,
    contracts: Mapping[str, object],
    verify_sources: bool,
) -> MutationCatalogue:
    """Parse one already-stabilized catalogue byte sequence."""

    payload = strict_json_bytes(raw, label="mutation catalogue")
    if not isinstance(payload, dict) or set(payload) != {
        "schema_version",
        "policy",
        "mutants",
    }:
        raise MutationAssuranceError("mutation catalogue fields are not exact")
    if payload["schema_version"] != CATALOGUE_SCHEMA_VERSION:
        raise MutationAssuranceError("mutation catalogue schema is unsupported")
    policy = payload["policy"]
    if not isinstance(policy, dict) or set(policy) != {
        "accepted_outcome",
        "aggregate_gate",
        "isolation",
        "network_boundary",
        "source_scope",
    }:
        raise MutationAssuranceError("mutation catalogue policy fields are not exact")
    expected_policy = {
        "accepted_outcome": "killed_intended",
        "aggregate_gate": "all_declared_mutants_no_percentage",
        "isolation": "fresh_plain_file_snapshot_per_mutant",
        "network_boundary": "cooperative_cpython_deny_not_security_sandbox",
        "source_scope": "moira_python_only",
    }
    if policy != expected_policy:
        raise MutationAssuranceError("mutation catalogue policy is not admitted")
    raw_mutants = payload["mutants"]
    if not isinstance(raw_mutants, list) or not raw_mutants:
        raise MutationAssuranceError("mutation catalogue must declare mutants")
    mutants = tuple(
        _parse_mutant(
            value,
            index=index,
            root=root,
            contracts=contracts,
            verify_sources=verify_sources,
        )
        for index, value in enumerate(raw_mutants)
    )
    ids = tuple(spec.mutant_id for spec in mutants)
    if ids != tuple(sorted(ids)) or len(set(ids)) != len(ids):
        raise MutationAssuranceError("mutant IDs must be unique and sorted")
    patch_ids = tuple(spec.patch_sha256 for spec in mutants)
    if len(set(patch_ids)) != len(patch_ids):
        raise MutationAssuranceError("mutation patches must be unique")
    for spec in mutants:
        if spec.evidence_class == "native_parity" and not spec.requires_native_backend:
            raise MutationAssuranceError(
                f"{spec.mutant_id}: native-parity evidence must require the backend"
            )
    return MutationCatalogue(
        path=path,
        sha256=sha256_bytes(raw),
        policy=MappingProxyType(dict(policy)),
        mutants=mutants,
    )


def load_catalogue(
    path: Path,
    *,
    root: Path,
    contracts: Mapping[str, object],
    verify_sources: bool = True,
) -> MutationCatalogue:
    """Load and bind the reviewed catalogue to live source and contracts."""

    raw = stable_file_bytes(path, maximum_bytes=_MAX_JSON_BYTES, label="mutation catalogue")
    return _load_catalogue_bytes(
        raw,
        path=path.resolve(strict=True),
        root=root,
        contracts=contracts,
        verify_sources=verify_sources,
    )


def _plain_repository_path(
    root: Path,
    relative: str,
    *,
    label: str,
) -> Path:
    """Resolve a repository path without following a link or reparse point."""

    current = root
    try:
        root_status = current.lstat()
    except OSError as exc:
        raise MutationAssuranceError(f"repository root is unavailable: {exc}") from exc
    if (
        not stat.S_ISDIR(root_status.st_mode)
        or stat.S_ISLNK(root_status.st_mode)
        or _is_reparse(root_status)
    ):
        raise MutationAssuranceError("repository root is not a plain directory")
    for part in PurePosixPath(relative).parts:
        current = current / part
        try:
            metadata = current.lstat()
        except OSError as exc:
            raise MutationAssuranceError(f"{label} is unavailable: {current}: {exc}") from exc
        if stat.S_ISLNK(metadata.st_mode) or _is_reparse(metadata):
            raise MutationAssuranceError(f"{label} crosses a link or reparse point: {current}")
    try:
        current.resolve(strict=True).relative_to(root.resolve(strict=True))
    except (OSError, ValueError) as exc:
        raise MutationAssuranceError(f"{label} escapes the repository: {current}") from exc
    return current


def _git_paths(
    root: Path,
    *,
    deleted: bool,
    git_executable: Path,
    git_identity: GitExecutableIdentity,
    private_runtime: bool,
) -> tuple[str, ...]:
    command = [
        str(git_executable),
        "ls-files",
        "--deleted" if deleted else "--cached",
    ]
    if not deleted:
        command.append("--others")
        command.extend(
            f"--exclude={pattern}"
            for pattern in _SNAPSHOT_UNTRACKED_EXCLUDE_POLICY
        )
    command.extend(("-z", "--", *_SNAPSHOT_SCOPES))
    try:
        completed = _run_git_command(
            command,
            root=root,
            git_executable=git_executable,
            git_identity=git_identity,
            private_runtime=private_runtime,
            text=False,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise MutationAssuranceError(f"Git snapshot enumeration failed: {exc}") from exc
    if completed.returncode != 0:
        error = completed.stderr.decode("utf-8", "replace")[:4096]
        raise MutationAssuranceError(
            f"Git snapshot enumeration exited {completed.returncode}: {error}"
        )
    try:
        decoded = completed.stdout.decode("utf-8")
    except UnicodeError as exc:
        raise MutationAssuranceError("Git emitted a non-UTF-8 snapshot path") from exc
    paths = tuple(part for part in decoded.split("\0") if part)
    normalized = tuple(
        _safe_relative_path(path, label="Git snapshot path") for path in paths
    )
    if len(set(normalized)) != len(normalized):
        raise MutationAssuranceError("Git snapshot enumeration contains duplicates")
    return normalized


def _native_extension_suffixes() -> tuple[str, ...]:
    """Return the exact, non-ambiguous extension suffix policy of this CPython."""

    suffixes = tuple(EXTENSION_SUFFIXES)
    if (
        not suffixes
        or len(set(suffixes)) != len(suffixes)
        or any(
            not isinstance(suffix, str)
            or not suffix.startswith(".")
            or "/" in suffix
            or "\\" in suffix
            or "\0" in suffix
            for suffix in suffixes
        )
    ):
        raise MutationAssuranceError(
            "current interpreter extension suffix policy is not admitted"
        )
    folded: dict[str, str] = {}
    for suffix in suffixes:
        prior = folded.get(suffix.casefold())
        if prior is not None and prior != suffix:
            raise MutationAssuranceError(
                "current interpreter extension suffixes collide by case"
            )
        folded[suffix.casefold()] = suffix
    return suffixes


def _native_backend_relative_path(root: Path) -> str:
    """Resolve one checkout extension without importing the ``moira`` package."""

    resolved_root = root.resolve(strict=True)
    package = _plain_repository_path(
        resolved_root,
        "moira",
        label="native backend package",
    )
    try:
        package_status = package.lstat()
    except OSError as exc:
        raise MutationAssuranceError(
            f"native backend package is unavailable: {exc}"
        ) from exc
    if not stat.S_ISDIR(package_status.st_mode):
        raise MutationAssuranceError("native backend package is not a directory")

    allowed_names = tuple(
        f"_moira_native{suffix}" for suffix in _native_extension_suffixes()
    )
    allowed_by_fold: dict[str, str] = {}
    for name in allowed_names:
        folded = name.casefold()
        prior = allowed_by_fold.get(folded)
        if prior is not None and prior != name:
            raise MutationAssuranceError(
                "native backend candidate names collide by case"
            )
        allowed_by_fold[folded] = name

    try:
        with os.scandir(package) as entries:
            children = sorted(entries, key=lambda entry: entry.name)
    except OSError as exc:
        raise MutationAssuranceError(
            f"native backend package cannot be enumerated: {exc}"
        ) from exc

    candidates: list[str] = []
    observed_case: dict[str, str] = {}
    for entry in children:
        expected_name = allowed_by_fold.get(entry.name.casefold())
        if expected_name is None:
            continue
        prior = observed_case.get(entry.name.casefold())
        if prior is not None and prior != entry.name:
            raise MutationAssuranceError(
                "native backend candidates collide by case"
            )
        observed_case[entry.name.casefold()] = entry.name
        if entry.name != expected_name:
            raise MutationAssuranceError(
                "native backend candidate has non-canonical case"
            )
        try:
            metadata = Path(entry.path).lstat()
        except OSError as exc:
            raise MutationAssuranceError(
                f"native backend candidate cannot be inspected: {entry.path}: {exc}"
            ) from exc
        if (
            not stat.S_ISREG(metadata.st_mode)
            or stat.S_ISLNK(metadata.st_mode)
            or _is_reparse(metadata)
            or metadata.st_nlink != 1
        ):
            raise MutationAssuranceError(
                f"native backend candidate is not a plain unique file: {entry.path}"
            )
        candidates.append(entry.name)
    if len(candidates) != 1:
        raise MutationAssuranceError(
            "checkout must contain exactly one current-interpreter native backend; "
            f"found {len(candidates)}"
        )
    relative = f"moira/{candidates[0]}"
    path = _plain_repository_path(
        resolved_root,
        relative,
        label="native backend",
    )
    stable_file_bytes(path, maximum_bytes=None, label="native backend")
    return relative


def _native_build_tree_paths(root: Path) -> tuple[str, ...]:
    """Enumerate the exact native-source inputs without executing build code."""

    resolved_root = root.resolve(strict=True)
    native_root = _plain_repository_path(
        resolved_root,
        "src/native",
        label="native build source root",
    )
    try:
        native_status = native_root.lstat()
    except OSError as exc:
        raise MutationAssuranceError(
            f"native build source root is unavailable: {exc}"
        ) from exc
    if not stat.S_ISDIR(native_status.st_mode):
        raise MutationAssuranceError("native build source root is not a directory")

    result: list[str] = []
    pending = [native_root]
    while pending:
        directory = pending.pop()
        try:
            with os.scandir(directory) as entries:
                children = sorted(entries, key=lambda entry: entry.name)
        except OSError as exc:
            raise MutationAssuranceError(
                f"native build directory cannot be inspected: {directory}: {exc}"
            ) from exc
        folded_names: dict[str, str] = {}
        for entry in children:
            folded = entry.name.casefold()
            prior = folded_names.get(folded)
            if prior is not None and prior != entry.name:
                raise MutationAssuranceError(
                    "native build paths collide by case: "
                    f"{prior!r}, {entry.name!r}"
                )
            folded_names[folded] = entry.name
            path = Path(entry.path)
            try:
                metadata = entry.stat(follow_symlinks=False)
            except OSError as exc:
                raise MutationAssuranceError(
                    f"native build input cannot be inspected: {path}: {exc}"
                ) from exc
            if stat.S_ISLNK(metadata.st_mode) or _is_reparse(metadata):
                raise MutationAssuranceError(
                    f"native build tree contains a link or reparse point: {path}"
                )
            if stat.S_ISDIR(metadata.st_mode):
                pending.append(path)
                continue
            if not stat.S_ISREG(metadata.st_mode):
                raise MutationAssuranceError(
                    f"native build tree contains an unsupported entry: {path}"
                )
            if path.suffix.casefold() not in _NATIVE_BUILD_SUFFIXES:
                continue
            try:
                relative = path.relative_to(resolved_root).as_posix()
            except ValueError as exc:
                raise MutationAssuranceError(
                    f"native build input escapes the repository: {path}"
                ) from exc
            result.append(
                _safe_relative_path(relative, label="native build input path")
            )
    if len(set(result)) != len(result):
        raise MutationAssuranceError("native build input paths are not unique")
    return tuple(sorted(result))


def _native_build_pyproject_bytes(raw: bytes) -> bytes:
    try:
        source = raw.decode("utf-8")
    except UnicodeError as exc:
        raise MutationAssuranceError(
            "pyproject.toml cannot be read as UTF-8"
        ) from exc
    sections: dict[str, list[str]] = {
        name: [] for name in _NATIVE_BUILD_PYPROJECT_SECTIONS
    }
    current: str | None = None
    seen: set[str] = set()
    for raw_line in source.splitlines():
        stripped = raw_line.strip()
        table = _NATIVE_BUILD_TOML_TABLE_RE.fullmatch(raw_line)
        if stripped.startswith("["):
            current = table.group(1) if table is not None else None
            if current in sections:
                if current in seen:
                    raise MutationAssuranceError(
                        f"pyproject.toml repeats build table [{current}]"
                    )
                seen.add(current)
                sections[current].append(f"[{current}]")
            continue
        if current in sections and stripped and not stripped.startswith("#"):
            sections[current].append(raw_line.rstrip())
    missing = sorted(_NATIVE_BUILD_PYPROJECT_SECTIONS - seen)
    if missing:
        raise MutationAssuranceError(
            "pyproject.toml omits required native build tables: "
            + ", ".join(missing)
        )
    canonical_lines: list[str] = []
    for section in sorted(sections):
        canonical_lines.extend(sections[section])
    return ("\n".join(canonical_lines) + "\n").encode("utf-8")


def _native_build_input_manifest(
    root: Path,
    *,
    snapshot: SnapshotInputs | None = None,
) -> dict[str, object]:
    """Independently derive the build manifest declared by the native build."""

    resolved_root = root.resolve(strict=True)
    relatives = tuple(
        sorted(
            (
                *_NATIVE_BUILD_EXACT_INPUTS,
                "pyproject.toml",
                *_native_build_tree_paths(resolved_root),
            )
        )
    )
    if len(set(relatives)) != len(relatives):
        raise MutationAssuranceError("native build inputs are not unique")
    folded: dict[str, str] = {}
    inputs: list[dict[str, object]] = []
    for relative in relatives:
        folded_relative = relative.casefold()
        prior = folded.get(folded_relative)
        if prior is not None and prior != relative:
            raise MutationAssuranceError(
                f"native build inputs collide by case: {prior!r}, {relative!r}"
            )
        folded[folded_relative] = relative
        path = _plain_repository_path(
            resolved_root,
            relative,
            label="native build input",
        )
        raw = stable_file_bytes(
            path,
            maximum_bytes=None,
            label="native build input",
        )
        if snapshot is not None:
            expected = snapshot.by_path.get(relative)
            if (
                expected is None
                or expected.bytes != len(raw)
                or expected.sha256 != sha256_bytes(raw)
            ):
                raise MutationAssuranceError(
                    "native build input differs from the frozen snapshot: "
                    f"{relative}"
                )
        if relative == "pyproject.toml":
            payload = _native_build_pyproject_bytes(raw)
            hash_mode = "toml_build_sections_v1"
        else:
            payload = raw
            hash_mode = "raw_bytes"
        inputs.append(
            {
                "bytes": len(payload),
                "hash_mode": hash_mode,
                "path": relative,
                "sha256": sha256_bytes(payload),
            }
        )
    unsigned = {"schema_version": 2, "inputs": inputs}
    return {
        **unsigned,
        "sha256": sha256_bytes(canonical_json_bytes(unsigned)),
    }


def _snapshot_manifest_sha256(
    files: Sequence[FileIdentity],
    *,
    deleted_tracked: Sequence[str],
    native_backend_path: str,
    git_executable: GitExecutableIdentity,
    untracked_exclude_policy: Sequence[str],
) -> str:
    return sha256_bytes(
        canonical_json_bytes(
            {
                "deleted_tracked": list(deleted_tracked),
                "files": [
                    {
                        "bytes": item.bytes,
                        "path": item.path,
                        "sha256": item.sha256,
                    }
                    for item in files
                ],
                "git_executable": _git_executable_payload(git_executable),
                "native_backend_path": native_backend_path,
                "schema_version": 3,
                "untracked_exclude_policy": list(untracked_exclude_policy),
            }
        )
    )


def enumerate_snapshot_inputs(
    root: Path,
    *,
    git_executable: GitExecutableIdentity,
    git_invocation_path: Path | None = None,
) -> SnapshotInputs:
    """Freeze current tracked, untracked, and loaded-backend input identities."""

    resolved_root = root.resolve(strict=True)
    current_git = git_executable_identity(Path(git_executable.path))
    if current_git != git_executable:
        raise MutationAssuranceError(
            "Git executable changed before snapshot enumeration"
        )
    git_path = (
        Path(current_git.path)
        if git_invocation_path is None
        else git_invocation_path
    )
    private_runtime = git_invocation_path is not None
    source_state = git_runtime_copy_state(
        git_path,
        current_git,
        private_copy=private_runtime,
    )
    try:
        top = _run_git_command(
            (str(git_path), "rev-parse", "--show-toplevel"),
            root=resolved_root,
            git_executable=git_path,
            git_identity=current_git,
            private_runtime=private_runtime,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise MutationAssuranceError(f"Git root verification failed: {exc}") from exc
    if top.returncode != 0:
        raise MutationAssuranceError("snapshot source is not a Git checkout")
    try:
        git_root = Path(top.stdout.strip()).resolve(strict=True)
    except OSError as exc:
        raise MutationAssuranceError("Git root is unavailable") from exc
    if git_root != resolved_root:
        raise MutationAssuranceError("runner root is not the exact Git toplevel")

    live_paths = set(
        _git_paths(
            resolved_root,
            deleted=False,
            git_executable=git_path,
            git_identity=current_git,
            private_runtime=private_runtime,
        )
    )
    deleted = tuple(
        sorted(
            set(
                _git_paths(
                    resolved_root,
                    deleted=True,
                    git_executable=git_path,
                    git_identity=current_git,
                    private_runtime=private_runtime,
                )
            )
        )
    )
    live_paths.difference_update(deleted)
    backend = _native_backend_relative_path(resolved_root)
    live_paths.add(backend)

    casefolded: dict[str, str] = {}
    identities: list[FileIdentity] = []
    for relative in sorted(live_paths):
        folded = relative.casefold()
        prior = casefolded.get(folded)
        if prior is not None and prior != relative:
            raise MutationAssuranceError(
                f"snapshot paths collide by case: {prior!r}, {relative!r}"
            )
        casefolded[folded] = relative
        path = _plain_repository_path(
            resolved_root,
            relative,
            label="snapshot input",
        )
        raw = stable_file_bytes(path, maximum_bytes=None, label="snapshot input")
        identities.append(
            FileIdentity(
                path=relative,
                bytes=len(raw),
                sha256=sha256_bytes(raw),
            )
        )
    files = tuple(identities)
    if git_runtime_copy_state(
        git_path,
        current_git,
        private_copy=private_runtime,
    ) != source_state:
        raise MutationAssuranceError(
            "private Git runtime changed during snapshot enumeration"
        )
    if git_executable_identity(Path(current_git.path)) != current_git:
        raise MutationAssuranceError(
            "Git source runtime changed during snapshot enumeration"
        )
    return SnapshotInputs(
        files=files,
        deleted_tracked=deleted,
        native_backend_path=backend,
        git_executable=current_git,
        untracked_exclude_policy=_SNAPSHOT_UNTRACKED_EXCLUDE_POLICY,
        manifest_sha256=_snapshot_manifest_sha256(
            files,
            deleted_tracked=deleted,
            native_backend_path=backend,
            git_executable=current_git,
            untracked_exclude_policy=_SNAPSHOT_UNTRACKED_EXCLUDE_POLICY,
        ),
    )


def phase11_native_build_identity(
    root: Path,
    snapshot: SnapshotInputs,
    catalogue: MutationCatalogue,
) -> dict[str, object] | None:
    """Bind native credit to static binary and current build-input evidence."""

    required = [
        spec.mutant_id for spec in catalogue.mutants if spec.requires_native_backend
    ]
    for spec in catalogue.mutants:
        if spec.evidence_class == "native_parity" and not spec.requires_native_backend:
            raise MutationAssuranceError(
                f"{spec.mutant_id}: native-parity evidence must require the backend"
            )
    if not required:
        return None
    relative = _native_backend_relative_path(root)
    expected_backend = snapshot.by_path.get(snapshot.native_backend_path)
    if expected_backend is None or relative != snapshot.native_backend_path:
        raise MutationAssuranceError(
            "static native backend is absent from the frozen snapshot"
        )
    backend_path = _plain_repository_path(
        root.resolve(strict=True),
        relative,
        label="native backend",
    )
    backend_raw = stable_file_bytes(
        backend_path,
        maximum_bytes=None,
        label="native backend",
    )
    if (
        len(backend_raw) != expected_backend.bytes
        or sha256_bytes(backend_raw) != expected_backend.sha256
    ):
        raise MutationAssuranceError(
            "static native backend differs from the frozen snapshot"
        )
    marker_matches = _NATIVE_BINARY_PROVENANCE_MARKER_RE.findall(backend_raw)
    if len(marker_matches) != 1:
        raise MutationAssuranceError(
            "native backend must contain exactly one build-provenance marker"
        )
    embedded_input_sha256 = marker_matches[0].decode("ascii")
    current_manifest = _native_build_input_manifest(root, snapshot=snapshot)
    current_inputs = current_manifest.get("inputs")
    if (
        current_manifest.get("schema_version") != 2
        or not isinstance(current_inputs, list)
        or not current_inputs
        or embedded_input_sha256 != current_manifest.get("sha256")
    ):
        raise MutationAssuranceError(
            "native backend was not built from the current admitted inputs"
        )
    return {
        "schema_version": 1,
        "required_mutant_ids": required,
        "backend_path": relative,
        "backend_bytes": expected_backend.bytes,
        "backend_sha256": expected_backend.sha256,
        "embedded_input_sha256": embedded_input_sha256,
        "build_input_manifest_sha256": current_manifest["sha256"],
        "build_input_count": len(current_inputs),
        "matches_current_inputs": True,
    }


def snapshot_manifest_payload(inputs: SnapshotInputs) -> dict[str, object]:
    return {
        "schema_version": 3,
        "manifest_sha256": inputs.manifest_sha256,
        "native_backend_path": inputs.native_backend_path,
        "git_executable": _git_executable_payload(inputs.git_executable),
        "untracked_exclude_policy": list(inputs.untracked_exclude_policy),
        "deleted_tracked": list(inputs.deleted_tracked),
        "files": [
            {
                "path": item.path,
                "bytes": item.bytes,
                "sha256": item.sha256,
            }
            for item in inputs.files
        ],
    }


def _write_new_file(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as exc:
        raise MutationAssuranceError(f"snapshot file could not be created: {path}: {exc}") from exc


def materialize_snapshot(
    root: Path,
    destination: Path,
    inputs: SnapshotInputs,
) -> None:
    """Plain-copy and twice verify one immutable current-state snapshot."""

    resolved_root = root.resolve(strict=True)
    if destination.exists():
        raise MutationAssuranceError("snapshot destination must not already exist")
    destination.mkdir(parents=True)
    for identity in inputs.files:
        source = _plain_repository_path(
            resolved_root,
            identity.path,
            label="snapshot input",
        )
        raw = stable_file_bytes(source, maximum_bytes=None, label="snapshot input")
        if len(raw) != identity.bytes or sha256_bytes(raw) != identity.sha256:
            raise MutationAssuranceError(
                f"snapshot input changed before copy: {identity.path}"
            )
        target = destination / Path(identity.path)
        _write_new_file(target, raw)
        copied = stable_file_bytes(target, maximum_bytes=None, label="snapshot copy")
        if copied != raw:
            raise MutationAssuranceError(f"snapshot copy differs: {identity.path}")
        try:
            if os.path.samefile(source, target):
                raise MutationAssuranceError(
                    f"snapshot copy reuses source identity: {identity.path}"
                )
        except OSError as exc:
            raise MutationAssuranceError(
                f"snapshot copy identity cannot be verified: {identity.path}: {exc}"
            ) from exc

    # A second pass closes the copy-time race window in the live checkout.
    for identity in inputs.files:
        source = _plain_repository_path(
            resolved_root,
            identity.path,
            label="snapshot input",
        )
        raw = stable_file_bytes(source, maximum_bytes=None, label="snapshot input")
        if len(raw) != identity.bytes or sha256_bytes(raw) != identity.sha256:
            raise MutationAssuranceError(
                f"snapshot input changed during materialization: {identity.path}"
            )
    verify_snapshot(destination, inputs)


def _walk_snapshot_files(root: Path) -> tuple[str, ...]:
    pending = [root]
    files: list[str] = []
    folded: dict[str, str] = {}
    while pending:
        directory = pending.pop()
        try:
            with os.scandir(directory) as entries:
                children = sorted(entries, key=lambda entry: entry.name)
        except OSError as exc:
            raise MutationAssuranceError(
                f"snapshot directory cannot be enumerated: {directory}: {exc}"
            ) from exc
        for entry in children:
            path = Path(entry.path)
            try:
                # On Windows/Python 3.14, DirEntry.stat(follow_symlinks=False)
                # can report zero link/device/inode fields for ordinary NTFS
                # files. Path.lstat() preserves the real link count needed by
                # the plain-copy covenant.
                metadata = path.lstat()
            except OSError as exc:
                raise MutationAssuranceError(
                    f"snapshot entry cannot be inspected: {path}: {exc}"
                ) from exc
            if stat.S_ISLNK(metadata.st_mode) or _is_reparse(metadata):
                raise MutationAssuranceError(
                    f"snapshot contains a link or reparse point: {path}"
                )
            if stat.S_ISDIR(metadata.st_mode):
                pending.append(path)
                continue
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
                raise MutationAssuranceError(
                    f"snapshot contains a non-plain file: {path}"
                )
            try:
                relative = path.relative_to(root).as_posix()
            except ValueError as exc:
                raise MutationAssuranceError("snapshot entry escapes its root") from exc
            key = relative.casefold()
            prior = folded.get(key)
            if prior is not None and prior != relative:
                raise MutationAssuranceError(
                    f"snapshot paths collide by case: {prior!r}, {relative!r}"
                )
            folded[key] = relative
            files.append(relative)
    return tuple(sorted(files))


def verify_snapshot(
    root: Path,
    inputs: SnapshotInputs,
    *,
    overrides: Mapping[str, str] | None = None,
) -> None:
    """Require the exact staged file set and hashes, with bounded overrides."""

    overrides = {} if overrides is None else dict(overrides)
    expected = {item.path: item for item in inputs.files}
    if not set(overrides).issubset(expected):
        raise MutationAssuranceError("snapshot hash override names an unknown path")
    observed_paths = _walk_snapshot_files(root)
    if set(observed_paths) != set(expected):
        missing = sorted(set(expected) - set(observed_paths))[:20]
        extra = sorted(set(observed_paths) - set(expected))[:20]
        raise MutationAssuranceError(
            f"snapshot file set changed; missing={missing!r}, extra={extra!r}"
        )
    for relative in observed_paths:
        identity = expected[relative]
        raw = stable_file_bytes(
            root / Path(relative),
            maximum_bytes=None,
            label="snapshot verification file",
        )
        digest = sha256_bytes(raw)
        wanted = overrides.get(relative, identity.sha256)
        if digest != wanted:
            raise MutationAssuranceError(
                f"snapshot file digest changed unexpectedly: {relative}"
            )
        if relative not in overrides and len(raw) != identity.bytes:
            raise MutationAssuranceError(
                f"snapshot file size changed unexpectedly: {relative}"
            )


def atomically_apply_mutant(
    snapshot_root: Path,
    inputs: SnapshotInputs,
    spec: MutantSpec,
) -> bytes:
    """Materialize the reviewed postimage inside one disposable snapshot."""

    identity = inputs.by_path.get(spec.source_path)
    if identity is None:
        raise MutationAssuranceError(
            f"{spec.mutant_id}: snapshot does not contain the admitted preimage"
        )
    path = snapshot_root / Path(spec.source_path)
    source = stable_file_bytes(path, maximum_bytes=None, label="mutation target")
    if sha256_bytes(source) != identity.sha256:
        raise MutationAssuranceError(f"{spec.mutant_id}: mutation target drifted")
    if sha256_bytes(canonical_source_bytes(source)) != spec.preimage_sha256:
        raise MutationAssuranceError(
            f"{spec.mutant_id}: canonical mutation preimage drifted"
        )
    mutated = apply_exact_mutation(spec, source)
    if sha256_bytes(canonical_source_bytes(mutated)) != spec.postimage_sha256:
        raise MutationAssuranceError(f"{spec.mutant_id}: postimage digest mismatch")
    temporary = path.with_name(f".{path.name}.{spec.mutant_id}.tmp")
    if temporary.exists():
        raise MutationAssuranceError("mutation temporary path already exists")
    _write_new_file(temporary, mutated)
    try:
        os.replace(temporary, path)
    except OSError as exc:
        raise MutationAssuranceError(
            f"{spec.mutant_id}: atomic mutation replacement failed: {exc}"
        ) from exc
    finally:
        if temporary.exists():
            try:
                temporary.unlink()
            except OSError:
                pass
    verify_snapshot(
        snapshot_root,
        inputs,
        overrides={spec.source_path: sha256_bytes(mutated)},
    )
    return mutated


def _absolute_lexical_path(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _project_launcher_identity(
    expected: Path,
    observed: Path,
) -> tuple[dict[str, object], bytes]:
    """Bind the lexical venv launcher and its ordinary symlink chain."""

    lexical = _absolute_lexical_path(expected)
    try:
        if not os.path.samefile(lexical, observed):
            raise MutationAssuranceError(
                "mutation runner must use the project .venv interpreter"
            )
    except OSError as exc:
        raise MutationAssuranceError(
            f"project .venv interpreter identity is unavailable: {exc}"
        ) from exc

    links: list[dict[str, str]] = []
    visited: set[str] = set()
    current = lexical
    for _index in range(64):
        try:
            metadata = current.lstat()
        except OSError as exc:
            raise MutationAssuranceError(
                f"project interpreter launcher is unavailable: {current}: {exc}"
            ) from exc
        marker = os.path.normcase(os.fspath(current))
        if marker in visited:
            raise MutationAssuranceError(
                "project interpreter launcher contains a symlink cycle"
            )
        visited.add(marker)
        if stat.S_ISLNK(metadata.st_mode):
            try:
                target = os.readlink(current)
            except OSError as exc:
                raise MutationAssuranceError(
                    f"project interpreter symlink cannot be read: {current}: {exc}"
                ) from exc
            if not target or "\x00" in target:
                raise MutationAssuranceError(
                    "project interpreter symlink target is invalid"
                )
            links.append({"path": str(current), "target": target})
            target_path = Path(target)
            current = _absolute_lexical_path(
                target_path if target_path.is_absolute() else current.parent / target_path
            )
            continue
        if _is_reparse(metadata):
            raise MutationAssuranceError(
                "project interpreter launcher uses an unsupported reparse point"
            )
        if not stat.S_ISREG(metadata.st_mode):
            raise MutationAssuranceError(
                "project interpreter launcher does not resolve to a regular file"
            )
        break
    else:
        raise MutationAssuranceError(
            "project interpreter launcher symlink chain is too deep"
        )

    resolved = lexical.resolve(strict=True)
    if current.resolve(strict=True) != resolved:
        raise MutationAssuranceError(
            "project interpreter launcher resolution is inconsistent"
        )
    raw = stable_file_bytes(
        resolved,
        maximum_bytes=_MAX_RUNTIME_FILE_BYTES,
        label="resolved project interpreter",
    )
    return (
        {
            "schema_version": 1,
            "path": str(lexical),
            "resolved_path": str(resolved),
            "directory_resolved": str(lexical.parent.resolve(strict=True)),
            "symlinks": links,
        },
        raw,
    )


def _enumerate_runtime_tree(
    root: Path,
    *,
    role: str,
) -> tuple[tuple[str, Path], ...]:
    """Enumerate one link-free interpreter tree without ambient bytecode."""

    resolved_root = root.resolve(strict=True)
    try:
        root_metadata = resolved_root.lstat()
    except OSError as exc:
        raise MutationAssuranceError(
            f"interpreter runtime tree is unavailable: {root}: {exc}"
        ) from exc
    if (
        not stat.S_ISDIR(root_metadata.st_mode)
        or stat.S_ISLNK(root_metadata.st_mode)
        or _is_reparse(root_metadata)
    ):
        raise MutationAssuranceError(
            f"interpreter runtime tree is not a plain directory: {root}"
        )

    pending = [resolved_root]
    files: list[tuple[str, Path]] = []
    folded: dict[str, str] = {}
    while pending:
        directory = pending.pop()
        try:
            with os.scandir(directory) as entries:
                children = sorted(entries, key=lambda entry: entry.name)
        except OSError as exc:
            raise MutationAssuranceError(
                f"interpreter runtime tree cannot be enumerated: {directory}: {exc}"
            ) from exc
        for entry in children:
            path = Path(entry.path)
            try:
                metadata = path.lstat()
            except OSError as exc:
                raise MutationAssuranceError(
                    f"interpreter runtime entry is unavailable: {path}: {exc}"
                ) from exc
            if stat.S_ISLNK(metadata.st_mode) or _is_reparse(metadata):
                raise MutationAssuranceError(
                    f"interpreter runtime tree contains a link: {path}"
                )
            if stat.S_ISDIR(metadata.st_mode):
                if entry.name.casefold() in {"__pycache__", "site-packages"}:
                    continue
                pending.append(path)
                continue
            if not stat.S_ISREG(metadata.st_mode):
                raise MutationAssuranceError(
                    f"interpreter runtime tree contains a special file: {path}"
                )
            if path.suffix.casefold() in {".pyc", ".pyo"}:
                raise MutationAssuranceError(
                    "interpreter runtime tree contains importable legacy bytecode: "
                    f"{path}"
                )
            relative = path.relative_to(resolved_root).as_posix()
            key = f"{role}/{relative}"
            collision = folded.setdefault(key.casefold(), key)
            if collision != key:
                raise MutationAssuranceError(
                    "interpreter runtime tree contains a case-colliding path"
                )
            files.append((key, path))
            if len(files) > _MAX_RUNTIME_FILES:
                raise MutationAssuranceError(
                    "interpreter runtime identity exceeds its file-count limit"
                )
    return tuple(sorted(files, key=lambda item: item[0]))


def _enumerate_importable_runtime_root(
    root: Path,
    *,
    role: str,
    excluded_roots: Sequence[Path] = (),
) -> tuple[tuple[str, Path], ...]:
    """Bind code reachable through a broad prefix-root sys.path entry."""

    from importlib.machinery import EXTENSION_SUFFIXES

    resolved_root = root.resolve(strict=True)
    excluded = {path.resolve(strict=True) for path in excluded_roots}
    extension_suffixes = tuple(value.casefold() for value in EXTENSION_SUFFIXES)
    pending = [resolved_root]
    files: list[tuple[str, Path]] = []
    while pending:
        directory = pending.pop()
        try:
            with os.scandir(directory) as entries:
                children = sorted(entries, key=lambda entry: entry.name)
        except OSError as exc:
            raise MutationAssuranceError(
                f"interpreter import root cannot be enumerated: {directory}: {exc}"
            ) from exc
        for entry in children:
            path = Path(entry.path)
            try:
                metadata = path.lstat()
            except OSError as exc:
                raise MutationAssuranceError(
                    f"interpreter import-root entry is unavailable: {path}: {exc}"
                ) from exc
            if stat.S_ISLNK(metadata.st_mode) or _is_reparse(metadata):
                raise MutationAssuranceError(
                    f"interpreter import root contains a link: {path}"
                )
            if stat.S_ISDIR(metadata.st_mode):
                if (
                    entry.name.casefold() in {"__pycache__", "site-packages"}
                    or path.resolve(strict=True) in excluded
                ):
                    continue
                pending.append(path)
                continue
            if not stat.S_ISREG(metadata.st_mode):
                raise MutationAssuranceError(
                    f"interpreter import root contains a special file: {path}"
                )
            lowered = path.name.casefold()
            if path.suffix.casefold() in {".pyc", ".pyo"}:
                raise MutationAssuranceError(
                    "interpreter import root contains legacy bytecode: "
                    f"{path}"
                )
            if path.suffix.casefold() != ".py" and not lowered.endswith(
                extension_suffixes
            ):
                continue
            relative = path.relative_to(resolved_root).as_posix()
            files.append((f"{role}/{relative}", path))
            if len(files) > _MAX_RUNTIME_FILES:
                raise MutationAssuranceError(
                    "interpreter import-root identity exceeds its file limit"
                )
    return tuple(sorted(files, key=lambda item: item[0]))


def _venv_disables_system_site_packages(config: Path) -> None:
    raw = stable_file_bytes(
        config,
        maximum_bytes=64 * 1024,
        label="project pyvenv.cfg",
    )
    try:
        text = raw.decode("utf-8")
    except UnicodeError as exc:
        raise MutationAssuranceError("project pyvenv.cfg is not UTF-8") from exc
    values: list[str] = []
    for line in text.splitlines():
        key, separator, value = line.partition("=")
        if separator and key.strip().casefold() == "include-system-site-packages":
            values.append(value.strip().casefold())
    if values != ["false"]:
        raise MutationAssuranceError(
            "project pyvenv.cfg must disable system site packages exactly"
        )


def _startup_import_path_identity(
    root: Path,
    observed: Sequence[str] | None,
) -> tuple[dict[str, object], ...]:
    """Validate the clean interpreter's import roots before runner injection."""

    import sysconfig

    prefix = Path(sys.prefix).resolve(strict=True)
    base_prefix = Path(sys.base_prefix).resolve(strict=True)
    stdlib = Path(str(sysconfig.get_path("stdlib"))).resolve(strict=True)
    candidates = tuple(sys.path if observed is None else observed)
    result: list[dict[str, object]] = []
    seen: set[str] = set()
    for index, raw_path in enumerate(candidates):
        if not isinstance(raw_path, str) or not raw_path:
            if observed is not None:
                raise MutationAssuranceError(
                    "clean interpreter sys.path contains a relative entry"
                )
            continue
        lexical = _absolute_lexical_path(Path(raw_path))
        lexical_folded = os.path.normcase(os.fspath(lexical))
        under_runtime = False
        for runtime_root in (prefix, base_prefix):
            try:
                lexical.relative_to(runtime_root)
            except ValueError:
                continue
            under_runtime = True
            break
        if not under_runtime:
            if observed is not None:
                raise MutationAssuranceError(
                    "clean interpreter sys.path escapes its base or venv prefix: "
                    f"{lexical}"
                )
            continue
        if lexical_folded in seen:
            raise MutationAssuranceError(
                "clean interpreter sys.path contains a duplicate entry"
            )
        seen.add(lexical_folded)
        if lexical.exists():
            resolved = lexical.resolve(strict=True)
            metadata = resolved.lstat()
            if stat.S_ISLNK(metadata.st_mode) or _is_reparse(metadata):
                raise MutationAssuranceError(
                    f"clean interpreter sys.path resolves to a link: {lexical}"
                )
            if stat.S_ISREG(metadata.st_mode):
                if lexical.suffix.casefold() != ".zip":
                    raise MutationAssuranceError(
                        f"clean interpreter sys.path file is not an archive: {lexical}"
                    )
                state = "archive"
                scope = "runtime_archive"
            elif stat.S_ISDIR(metadata.st_mode):
                lowered_parts = {part.casefold() for part in resolved.parts}
                if "site-packages" in lowered_parts:
                    try:
                        resolved.relative_to(prefix)
                    except ValueError as exc:
                        raise MutationAssuranceError(
                            "clean interpreter admits external system site-packages"
                        ) from exc
                    scope = "toolchain_site_packages"
                else:
                    allowed = resolved in {prefix, base_prefix, stdlib}
                    try:
                        resolved.relative_to(stdlib)
                    except ValueError:
                        pass
                    else:
                        allowed = True
                    if os.name == "nt" and resolved == base_prefix / "DLLs":
                        allowed = True
                    if not allowed:
                        raise MutationAssuranceError(
                            "clean interpreter sys.path contains an unbound directory: "
                            f"{lexical}"
                        )
                    scope = "runtime_tree"
                state = "directory"
            else:
                raise MutationAssuranceError(
                    f"clean interpreter sys.path is not file or directory: {lexical}"
                )
            resolved_text: str | None = str(resolved)
        else:
            expected_zip_names = {
                f"python{sys.version_info[0]}{sys.version_info[1]}.zip",
                f"python{sys.version_info[0]}.{sys.version_info[1]}.zip",
            }
            if lexical.name.casefold() not in {
                value.casefold() for value in expected_zip_names
            }:
                raise MutationAssuranceError(
                    f"clean interpreter sys.path contains an arbitrary missing path: {lexical}"
                )
            state = "missing"
            scope = "missing_stdlib_archive"
            resolved_text = None
        result.append(
            {
                "index": index,
                "path": str(lexical),
                "resolved": resolved_text,
                "state": state,
                "scope": scope,
            }
        )
    if observed is not None:
        derived = _startup_import_path_identity(root, None)
        observed_without_indexes = tuple(
            {**entry, "index": index}
            for index, entry in enumerate(result)
        )
        derived_without_indexes = tuple(
            {**entry, "index": index}
            for index, entry in enumerate(derived)
        )
        if observed_without_indexes != derived_without_indexes:
            raise MutationAssuranceError(
                "clean interpreter sys.path differs from the admitted runtime path"
            )
        return observed_without_indexes
    return tuple(
        {**entry, "index": index}
        for index, entry in enumerate(result)
    )


def _interpreter_runtime_candidates(
    root: Path,
    startup_import_path: Sequence[str] | None,
) -> tuple[tuple[tuple[str, Path], ...], dict[str, object]]:
    import sysconfig

    venv_config = (root / ".venv" / "pyvenv.cfg").resolve(strict=True)
    _venv_disables_system_site_packages(venv_config)
    base_executable_raw = getattr(sys, "_base_executable", None)
    if not isinstance(base_executable_raw, str) or not base_executable_raw:
        raise MutationAssuranceError("base interpreter executable is unavailable")
    base_executable = Path(base_executable_raw).resolve(strict=True)
    stdlib_raw = sysconfig.get_path("stdlib")
    if not isinstance(stdlib_raw, str) or not stdlib_raw:
        raise MutationAssuranceError("base interpreter stdlib is unavailable")
    stdlib = Path(stdlib_raw).resolve(strict=True)
    base_prefix = Path(sys.base_prefix).resolve(strict=True)

    candidates: list[tuple[str, Path]] = [
        ("venv/pyvenv.cfg", venv_config),
        ("base/executable", base_executable),
    ]
    core_files: list[Path] = []
    auxiliary_trees: list[Path] = []
    import_path = _startup_import_path_identity(root, startup_import_path)
    startup_control_files: list[dict[str, str]] = []
    if os.name == "nt":
        try:
            direct_children = sorted(base_prefix.iterdir(), key=lambda path: path.name)
        except OSError as exc:
            raise MutationAssuranceError(
                f"base interpreter prefix cannot be enumerated: {exc}"
            ) from exc
        for candidate in direct_children:
            if candidate.is_file() and candidate.suffix.casefold() in {
                ".dll",
                ".exe",
            }:
                core_files.append(candidate.resolve(strict=True))
        dlls = base_prefix / "DLLs"
        if dlls.exists():
            auxiliary_trees.append(dlls.resolve(strict=True))
        for name in (
            "python._pth",
            f"python{sys.version_info[0]}{sys.version_info[1]}._pth",
        ):
            control = base_prefix / name
            if control.exists():
                resolved_control = control.resolve(strict=True)
                candidates.append((f"startup-control/{name}", resolved_control))
                startup_control_files.append(
                    {"path": str(control), "state": "file"}
                )
            else:
                startup_control_files.append(
                    {"path": str(control), "state": "missing"}
                )
    else:
        library_name = sysconfig.get_config_var("LDLIBRARY")
        library_directory = sysconfig.get_config_var("LIBDIR")
        if isinstance(library_name, str) and library_name:
            search_roots = [base_prefix]
            if isinstance(library_directory, str) and library_directory:
                search_roots.insert(0, Path(library_directory))
            for search_root in search_roots:
                candidate = search_root / library_name
                if candidate.exists():
                    core_files.append(candidate.resolve(strict=True))
                    break

    for index, core_file in enumerate(sorted(set(core_files), key=str)):
        candidates.append((f"core/{index:04d}-{core_file.name}", core_file))
    candidates.extend(_enumerate_runtime_tree(stdlib, role="stdlib"))
    for index, auxiliary in enumerate(sorted(set(auxiliary_trees), key=str)):
        candidates.extend(
            _enumerate_runtime_tree(auxiliary, role=f"auxiliary-{index:04d}")
        )
    for entry in import_path:
        state = entry["state"]
        resolved_text = entry["resolved"]
        if state == "archive":
            assert isinstance(resolved_text, str)
            candidates.append(
                (f"import-archive/{entry['index']:04d}", Path(resolved_text))
            )
        elif state == "directory" and resolved_text in {
            str(base_prefix),
            str(Path(sys.prefix).resolve(strict=True)),
        }:
            assert isinstance(resolved_text, str)
            exclusions = [stdlib, *auxiliary_trees]
            candidates.extend(
                _enumerate_importable_runtime_root(
                    Path(resolved_text),
                    role=f"import-root-{entry['index']:04d}",
                    excluded_roots=exclusions,
                )
            )
    ordered = tuple(sorted(candidates, key=lambda item: item[0]))
    keys = [key for key, _path in ordered]
    if len(keys) != len(set(keys)):
        raise MutationAssuranceError("interpreter runtime identity contains duplicates")
    return ordered, {
        "venv_config": str(venv_config),
        "base_executable": str(base_executable),
        "stdlib": str(stdlib),
        "auxiliary_trees": [str(path) for path in auxiliary_trees],
        "core_files": [str(path) for path in sorted(set(core_files), key=str)],
        "startup_import_path": list(import_path),
        "startup_control_files": startup_control_files,
    }


def _project_interpreter_runtime_identity(
    root: Path,
    startup_import_path: Sequence[str] | None,
) -> dict[str, object]:
    first_candidates, roots = _interpreter_runtime_candidates(
        root,
        startup_import_path,
    )

    def identify(candidates: Sequence[tuple[str, Path]]) -> tuple[dict[str, object], ...]:
        identities: list[dict[str, object]] = []
        total_bytes = 0
        for key, path in candidates:
            raw = stable_file_bytes(
                path,
                maximum_bytes=_MAX_RUNTIME_FILE_BYTES,
                label=f"interpreter runtime {key}",
            )
            total_bytes += len(raw)
            if total_bytes > _MAX_RUNTIME_TOTAL_BYTES:
                raise MutationAssuranceError(
                    "interpreter runtime identity exceeds its total byte limit"
                )
            identities.append(
                {"path": key, "bytes": len(raw), "sha256": sha256_bytes(raw)}
            )
        return tuple(identities)

    first = identify(first_candidates)
    second_candidates, second_roots = _interpreter_runtime_candidates(
        root,
        startup_import_path,
    )
    if first_candidates != second_candidates or roots != second_roots:
        raise MutationAssuranceError(
            "interpreter runtime file set changed during admission"
        )
    second = identify(second_candidates)
    if first != second:
        raise MutationAssuranceError(
            "interpreter runtime bytes changed during admission"
        )
    return {
        "schema_version": 1,
        "scope": _RUNTIME_IDENTITY_SCOPE,
        "roots": roots,
        "file_count": len(first),
        "bytes": sum(int(item["bytes"]) for item in first),
        "manifest_sha256": sha256_bytes(canonical_json_bytes(list(first))),
    }


def _require_exact_startup_import_path(
    startup_import_path: Sequence[str] | None,
) -> None:
    if startup_import_path is None:
        raise MutationAssuranceError(
            "mutation runner startup import path proof is required"
        )
    if type(startup_import_path) is not tuple or any(
        type(item) is not str for item in startup_import_path
    ):
        raise MutationAssuranceError(
            "mutation runner startup import path proof is not exact"
        )
    active_path = sys.path
    if type(active_path) is not list or any(
        type(item) is not str for item in active_path
    ):
        raise MutationAssuranceError(
            "mutation runner active sys.path is not exact"
        )
    if tuple(active_path) != startup_import_path:
        raise MutationAssuranceError(
            "mutation runner sys.path changed after clean startup capture"
        )


def project_interpreter_identity(
    root: Path,
    *,
    startup_import_path: tuple[str, ...],
    lru_runtime_context: object,
) -> dict[str, object]:
    """Bind the runner to the checkout's one authoritative project runtime."""

    _require_exact_startup_import_path(startup_import_path)
    expected = (
        root / ".venv" / "Scripts" / "python.exe"
        if os.name == "nt"
        else root / ".venv" / "bin" / "python"
    )
    try:
        if not os.path.samefile(root / ".venv", sys.prefix):
            raise MutationAssuranceError(
                "mutation runner prefix is not the project .venv"
            )
    except OSError as exc:
        raise MutationAssuranceError(
            f"project .venv prefix identity is unavailable: {exc}"
        ) from exc
    launcher, raw = _project_launcher_identity(
        expected,
        Path(sys.executable),
    )
    runtime = _project_interpreter_runtime_identity(
        root,
        startup_import_path,
    )
    try:
        from support.mutation_toolchain import (
            loaded_test_toolchain_attestation,
            normalize_eager_lru_wrappers,
            project_test_toolchain_identity,
        )

        prebuild_lru_normalization = normalize_eager_lru_wrappers(
            lru_runtime_context
        )
        test_toolchain = project_test_toolchain_identity(
            root,
            lru_runtime_context=lru_runtime_context,
        )
        postbuild_lru_normalization = normalize_eager_lru_wrappers(
            lru_runtime_context
        )
        if prebuild_lru_normalization != postbuild_lru_normalization:
            raise MutationAssuranceError(
                "project test toolchain LRU registry changed while building identity"
            )
        loaded_toolchain = loaded_test_toolchain_attestation(
            test_toolchain,
            lru_runtime_context=lru_runtime_context,
        )
        for field, expected_value in postbuild_lru_normalization.items():
            if loaded_toolchain.get(field) != expected_value:
                raise MutationAssuranceError(
                    "project loaded test toolchain contradicts its LRU normalization"
                )
    except Exception as exc:
        raise MutationAssuranceError(
            f"project test toolchain identity is unavailable: "
            f"{type(exc).__name__}: {exc}"
        ) from exc
    return {
        "schema_version": INTERPRETER_IDENTITY_SCHEMA_VERSION,
        "executable": launcher["path"],
        "executable_resolved": launcher["resolved_path"],
        "sha256": sha256_bytes(raw),
        "bytes": len(raw),
        "prefix": str(Path(sys.prefix).resolve(strict=True)),
        "base_prefix": str(Path(sys.base_prefix).resolve(strict=True)),
        "implementation": sys.implementation.name,
        "version": list(sys.version_info[:3]),
        "launcher": launcher,
        "runtime": runtime,
        "test_toolchain": test_toolchain,
        "loaded_test_toolchain": loaded_toolchain,
    }


def _expected_child_interpreter_runtime(
    interpreter: Mapping[str, object],
) -> tuple[str, str, str]:
    implementation = interpreter.get("implementation")
    version = interpreter.get("version")
    if (
        not isinstance(implementation, str)
        or implementation.casefold() != "cpython"
        or not isinstance(version, (list, tuple))
        or len(version) != 3
        or not all(
            isinstance(item, int) and not isinstance(item, bool)
            for item in version
        )
    ):
        raise MutationAssuranceError(
            "mutation assurance requires an exact CPython runtime identity"
        )
    dotted = ".".join(str(item) for item in version)
    cache_tag = f"cpython-{version[0]}{version[1]}"
    return "CPython", dotted, cache_tag


def _validate_normalized_lru_wrapper_attestation(
    value: Mapping[str, object],
    *,
    label: str,
) -> tuple[str, ...]:
    names_raw = _list(
        value.get("normalized_lru_wrapper_names"),
        label=f"{label} normalized LRU wrapper names",
    )
    if (
        not names_raw
        or not all(isinstance(name, str) and name for name in names_raw)
    ):
        raise MutationAssuranceError(
            f"{label} normalized LRU wrapper names are invalid"
        )
    names = tuple(names_raw)
    if names != tuple(sorted(set(names))):
        raise MutationAssuranceError(
            f"{label} normalized LRU wrapper names are not sorted and unique"
        )
    count = value.get("normalized_lru_wrapper_count")
    if isinstance(count, bool) or not isinstance(count, int) or count != len(names):
        raise MutationAssuranceError(
            f"{label} normalized LRU wrapper count is invalid"
        )
    supplied_digest = _sha256(
        value.get("normalized_lru_wrapper_sha256"),
        label=f"{label} normalized LRU wrapper digest",
    )
    digest_preimage = json.dumps(
        list(names),
        allow_nan=False,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    if supplied_digest != sha256_bytes(digest_preimage):
        raise MutationAssuranceError(
            f"{label} normalized LRU wrapper digest is invalid"
        )
    if value.get("all_normalized_lru_wrappers_empty") is not True:
        raise MutationAssuranceError(
            f"{label} normalized LRU wrappers are not empty"
        )
    return names


def _validate_child_toolchain_attestation(
    value: object,
    *,
    interpreter: Mapping[str, object],
) -> None:
    from support.mutation_toolchain import TOOLCHAIN_SCHEMA_VERSION

    attestation = _object(value, label="child test toolchain")
    _exact_fields(
        attestation,
        {
            "schema_version",
            "initial_manifest_sha256",
            "final_manifest_sha256",
            "module_manifest_sha256",
            "code_manifest_sha256",
            "module_count",
            "code_object_count",
            "stable_during_execution",
            "all_modules_match",
            "all_captured_modules_match",
            "normalized_lru_wrapper_names",
            "normalized_lru_wrapper_count",
            "normalized_lru_wrapper_sha256",
            "all_normalized_lru_wrappers_empty",
        },
        label="child test toolchain",
    )
    for field in (
        "initial_manifest_sha256",
        "final_manifest_sha256",
        "module_manifest_sha256",
        "code_manifest_sha256",
    ):
        _sha256(attestation[field], label=f"child test toolchain {field}")
    if (
        attestation["schema_version"] != TOOLCHAIN_SCHEMA_VERSION
        or isinstance(attestation["module_count"], bool)
        or not isinstance(attestation["module_count"], int)
        or attestation["module_count"] <= 0
        or isinstance(attestation["code_object_count"], bool)
        or not isinstance(attestation["code_object_count"], int)
        or attestation["code_object_count"] <= 0
        or attestation["stable_during_execution"] is not True
        or attestation["all_modules_match"] is not True
        or attestation["all_captured_modules_match"] is not True
    ):
        raise MutationAssuranceError("child test toolchain attestation is invalid")
    _validate_normalized_lru_wrapper_attestation(
        attestation,
        label="child test toolchain",
    )
    if "test_toolchain" not in interpreter:
        return
    parent = _object(
        interpreter["test_toolchain"],
        label="parent test toolchain",
    )
    loaded = _object(
        interpreter["loaded_test_toolchain"],
        label="parent loaded test toolchain",
    )
    if (
        attestation["initial_manifest_sha256"] != parent["manifest_sha256"]
        or attestation["final_manifest_sha256"] != parent["manifest_sha256"]
        or attestation["module_manifest_sha256"]
        != loaded["module_manifest_sha256"]
        or attestation["code_manifest_sha256"]
        != loaded["code_manifest_sha256"]
        or attestation["module_count"] != loaded["module_count"]
        or attestation["code_object_count"] != loaded["code_object_count"]
        or attestation["normalized_lru_wrapper_names"]
        != loaded["normalized_lru_wrapper_names"]
        or attestation["normalized_lru_wrapper_count"]
        != loaded["normalized_lru_wrapper_count"]
        or attestation["normalized_lru_wrapper_sha256"]
        != loaded["normalized_lru_wrapper_sha256"]
        or attestation["all_normalized_lru_wrappers_empty"]
        != loaded["all_normalized_lru_wrappers_empty"]
    ):
        raise MutationAssuranceError(
            "child test toolchain differs from the parent admission"
        )


_CHILD_PARENT_ENVIRONMENT = frozenset(
    {
        "APPDATA",
        "COMSPEC",
        "HOME",
        "HOMEDRIVE",
        "HOMEPATH",
        "LANG",
        "LC_ALL",
        "LOCALAPPDATA",
        "NUMBER_OF_PROCESSORS",
        "OS",
        "PATH",
        "PATHEXT",
        "PROCESSOR_ARCHITECTURE",
        "PROGRAMDATA",
        "SYSTEMDRIVE",
        "SYSTEMROOT",
        "TEMP",
        "TMP",
        "TMPDIR",
        "USERPROFILE",
        "WINDIR",
    }
)


def child_environment(snapshot_root: Path, *, seed: int) -> dict[str, str]:
    """Construct a small deterministic child environment from an allowlist."""

    allowed = {name.casefold() for name in _CHILD_PARENT_ENVIRONMENT}
    environment = {
        name: value
        for name, value in os.environ.items()
        if name.casefold() in allowed
    }
    bootstrap = snapshot_root / "tests" / "support" / "network_bootstrap"
    tests = snapshot_root / "tests"
    environment.update(
        {
            "MOIRA_TEST_MODE": "1",
            "MOIRA_NO_DOWNLOAD": "1",
            "MOIRA_STRICT_KNOWN_ISSUES": "1",
            "MOIRA_TEST_NETWORK_POLICY": "deny",
            "MOIRA_TEST_ARTIFACTS": "0",
            "MOIRA_SNAPSHOT_UPDATE": "0",
            "MOIRA_GOLDEN_UPDATE": "0",
            "MOIRA_PYTEST_PLUGIN_AUTOLOAD": "0",
            "MOIRA_SKIP_SLOW": "0",
            "MOIRA_RUN_EXPERIMENTAL": "1",
            "MOIRA_RUN_TEMPLATES": "1",
            "MOIRA_TEST_BUDGET_CASE_S": "0",
            "MOIRA_TEST_BUDGET_TOTAL_S": "0",
            "MOIRA_TEST_SEED": str(seed),
            "MOIRA_TEST_RUN_ID": f"phase11-{seed:016x}"[:64],
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONNOUSERSITE": "1",
            "PYTHONOPTIMIZE": "0",
            "PYTHONSAFEPATH": "1",
            "PYTHONUTF8": "1",
            "PYTHONPATH": os.pathsep.join(
                (str(bootstrap), str(snapshot_root), str(tests))
            ),
        }
    )
    return environment


def _expected_child_argv(
    *,
    interpreter: str,
    control_root: Path | PurePosixPath | PureWindowsPath,
    spec: MutantSpec,
    execution_id: str,
) -> tuple[str, ...]:
    basetemp = control_root / f"pytest-{execution_id}"
    report_path = control_root / "reports" / f"{execution_id}.json"
    pycache_prefix = control_root / f"pycache-{execution_id}"
    return (
        interpreter,
        "-P",
        "-B",
        "-X",
        f"pycache_prefix={pycache_prefix}",
        "-m",
        "pytest",
        spec.intended_killer_nodeid,
        "-q",
        "--color=no",
        "--tb=short",
        "--maxfail=1",
        "-p",
        "no:cacheprovider",
        "-p",
        "tests.mutation_reporter",
        "--basetemp",
        str(basetemp),
        "--moira-mutation-report",
        str(report_path),
        "--moira-mutation-execution-id",
        execution_id,
        "--moira-mutation-intended-nodeid",
        spec.intended_killer_nodeid,
        "--moira-mutation-source-path",
        spec.source_path,
        "--moira-mutation-module",
        spec.module_name,
        "--moira-mutation-target-qualname",
        spec.target_qualname,
    )


def child_argv(
    *,
    interpreter: str,
    snapshot_root: Path,
    control_root: Path,
    spec: MutantSpec,
    execution_id: str,
    report_path: Path,
) -> tuple[str, ...]:
    if _RUN_ID_RE.fullmatch(execution_id) is None:
        raise MutationAssuranceError("child execution ID is invalid")
    if (
        snapshot_root.name != "snapshot"
        or control_root.resolve() != snapshot_root.resolve().parent / "control"
    ):
        raise MutationAssuranceError("child snapshot/control layout is not admitted")
    if not report_path.is_absolute():
        raise MutationAssuranceError("child report path must be absolute")
    expected_report = control_root / "reports" / f"{execution_id}.json"
    if report_path.resolve() != expected_report.resolve():
        raise MutationAssuranceError("child report path is not the admitted path")
    basetemp = control_root / f"pytest-{execution_id}"
    pycache_prefix = control_root / f"pycache-{execution_id}"
    if basetemp.exists() or pycache_prefix.exists():
        raise MutationAssuranceError("child temporary path already exists")
    return _expected_child_argv(
        interpreter=interpreter,
        control_root=control_root,
        spec=spec,
        execution_id=execution_id,
    )


class _WindowsJob:
    """Kill-on-close Job Object for one mutation child tree."""

    def __init__(self) -> None:
        if os.name != "nt":
            raise MutationAssuranceError("Windows job requested on a non-Windows host")
        import ctypes
        from ctypes import wintypes

        class _IoCounters(ctypes.Structure):
            _fields_ = [
                ("ReadOperationCount", ctypes.c_ulonglong),
                ("WriteOperationCount", ctypes.c_ulonglong),
                ("OtherOperationCount", ctypes.c_ulonglong),
                ("ReadTransferCount", ctypes.c_ulonglong),
                ("WriteTransferCount", ctypes.c_ulonglong),
                ("OtherTransferCount", ctypes.c_ulonglong),
            ]

        class _BasicLimitInformation(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_longlong),
                ("PerJobUserTimeLimit", ctypes.c_longlong),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class _ExtendedLimitInformation(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", _BasicLimitInformation),
                ("IoInfo", _IoCounters),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateJobObjectW.argtypes = (ctypes.c_void_p, wintypes.LPCWSTR)
        kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        kernel32.SetInformationJobObject.argtypes = (
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
        )
        kernel32.SetInformationJobObject.restype = wintypes.BOOL
        kernel32.AssignProcessToJobObject.argtypes = (
            wintypes.HANDLE,
            wintypes.HANDLE,
        )
        kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
        kernel32.TerminateJobObject.argtypes = (wintypes.HANDLE, wintypes.UINT)
        kernel32.TerminateJobObject.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
        kernel32.CloseHandle.restype = wintypes.BOOL
        ntdll = ctypes.WinDLL("ntdll")
        ntdll.NtResumeProcess.argtypes = (wintypes.HANDLE,)
        ntdll.NtResumeProcess.restype = wintypes.LONG

        handle = kernel32.CreateJobObjectW(None, None)
        if not handle:
            raise MutationAssuranceError(
                f"Windows child Job Object creation failed: {ctypes.get_last_error()}"
            )
        information = _ExtendedLimitInformation()
        information.BasicLimitInformation.LimitFlags = 0x00002000
        if not kernel32.SetInformationJobObject(
            handle,
            9,
            ctypes.byref(information),
            ctypes.sizeof(information),
        ):
            error = ctypes.get_last_error()
            kernel32.CloseHandle(handle)
            raise MutationAssuranceError(
                f"Windows child Job Object policy failed: {error}"
            )
        self._ctypes = ctypes
        self._kernel32 = kernel32
        self._ntdll = ntdll
        self._handle = handle
        self._assigned = False

    def assign(self, process: subprocess.Popen[bytes]) -> None:
        process_handle = getattr(process, "_handle", None)
        if process_handle is None or not self._kernel32.AssignProcessToJobObject(
            self._handle,
            process_handle,
        ):
            raise MutationAssuranceError(
                "Windows child could not enter its kill-on-close Job Object: "
                f"{self._ctypes.get_last_error()}"
            )
        self._assigned = True

    @property
    def assigned(self) -> bool:
        return self._assigned

    def resume(self, process: subprocess.Popen[bytes]) -> None:
        """Resume a child only after Job Object membership is established."""

        process_handle = getattr(process, "_handle", None)
        if process_handle is None:
            raise MutationAssuranceError("Windows child process handle is unavailable")
        status = self._ntdll.NtResumeProcess(process_handle)
        if status != 0:
            raise MutationAssuranceError(
                "Windows child could not resume inside its Job Object: "
                f"NTSTATUS 0x{status & 0xFFFFFFFF:08x}"
            )

    def terminate(self) -> None:
        if self._handle is None:
            return
        if not self._kernel32.TerminateJobObject(self._handle, 1):
            raise MutationAssuranceError(
                "Windows child Job Object termination failed: "
                f"{self._ctypes.get_last_error()}"
            )

    def close(self) -> None:
        handle = self._handle
        self._handle = None
        if handle is not None:
            self._kernel32.CloseHandle(handle)


_CHILD_EXECUTION_LOCK = threading.Lock()


def _windows_direct_children() -> set[int]:
    """Return the current process's direct Windows children via Toolhelp."""

    if os.name != "nt":
        raise MutationAssuranceError(
            "Windows child census requested on a non-Windows host"
        )
    import ctypes
    from ctypes import wintypes

    class _ProcessEntry32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.c_size_t),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", wintypes.LONG),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", wintypes.WCHAR * 260),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateToolhelp32Snapshot.argtypes = (wintypes.DWORD, wintypes.DWORD)
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel32.Process32FirstW.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(_ProcessEntry32W),
    )
    kernel32.Process32FirstW.restype = wintypes.BOOL
    kernel32.Process32NextW.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(_ProcessEntry32W),
    )
    kernel32.Process32NextW.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel32.CloseHandle.restype = wintypes.BOOL
    snapshot = kernel32.CreateToolhelp32Snapshot(0x00000002, 0)
    invalid_handle = ctypes.c_void_p(-1).value
    if not snapshot or int(snapshot) == invalid_handle:
        raise MutationAssuranceError(
            f"Windows child census failed: {ctypes.get_last_error()}"
        )
    entry = _ProcessEntry32W()
    entry.dwSize = ctypes.sizeof(entry)
    children: set[int] = set()
    try:
        if not kernel32.Process32FirstW(snapshot, ctypes.byref(entry)):
            error = ctypes.get_last_error()
            if error != 18:
                raise MutationAssuranceError(
                    f"Windows child census could not start: {error}"
                )
            return children
        while True:
            if entry.th32ParentProcessID == os.getpid():
                pid = int(entry.th32ProcessID)
                if pid > 0:
                    children.add(pid)
            if not kernel32.Process32NextW(snapshot, ctypes.byref(entry)):
                error = ctypes.get_last_error()
                if error != 18:
                    raise MutationAssuranceError(
                        f"Windows child census was interrupted: {error}"
                    )
                break
    finally:
        kernel32.CloseHandle(snapshot)
    return children


def _terminate_new_windows_children(
    preexisting: set[int],
    *,
    timeout_seconds: float = 5.0,
) -> None:
    """Boundedly terminate children created before Popen returned a handle."""

    if os.name != "nt":
        raise MutationAssuranceError(
            "Windows child recovery requested on a non-Windows host"
        )
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = (
        wintypes.DWORD,
        wintypes.BOOL,
        wintypes.DWORD,
    )
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.TerminateProcess.argtypes = (wintypes.HANDLE, wintypes.UINT)
    kernel32.TerminateProcess.restype = wintypes.BOOL
    kernel32.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel32.CloseHandle.restype = wintypes.BOOL
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        remaining = _windows_direct_children() - preexisting
        if not remaining:
            return
        for pid in remaining:
            handle = kernel32.OpenProcess(0x00100001, False, pid)
            if not handle:
                error = ctypes.get_last_error()
                if error == 87:
                    continue
                raise MutationAssuranceError(
                    f"Windows orphan child {pid} cannot be opened: {error}"
                )
            try:
                if not kernel32.TerminateProcess(handle, 1):
                    error = ctypes.get_last_error()
                    if error != 87:
                        raise MutationAssuranceError(
                            f"Windows orphan child {pid} cannot terminate: {error}"
                        )
                wait_ms = max(
                    1,
                    min(5000, int((deadline - time.monotonic()) * 1000)),
                )
                result = kernel32.WaitForSingleObject(handle, wait_ms)
                if result not in (0, 128):
                    if result == 258:
                        continue
                    raise MutationAssuranceError(
                        f"Windows orphan child {pid} wait failed: {result}"
                    )
            finally:
                kernel32.CloseHandle(handle)
    remaining = _windows_direct_children() - preexisting
    if remaining:
        raise MutationAssuranceError(
            f"Windows orphan children did not terminate: {sorted(remaining)}"
        )


def _linux_direct_children() -> set[int]:
    """Return every direct child attributed to any thread in this process."""

    task_root = Path("/proc/self/task")
    if not task_root.is_dir():
        raise MutationAssuranceError(
            "POSIX descendant containment requires Linux /proc task children"
        )
    children: set[int] = set()
    try:
        task_paths = tuple(task_root.iterdir())
    except OSError as exc:
        raise MutationAssuranceError(
            f"could not enumerate Linux task children: {exc}"
        ) from exc
    for task_path in task_paths:
        try:
            raw = (task_path / "children").read_text(
                encoding="ascii",
                errors="strict",
            )
        except FileNotFoundError:
            # Threads may disappear between the task-directory listing and read.
            continue
        except (OSError, UnicodeError) as exc:
            raise MutationAssuranceError(
                f"could not read Linux task children: {exc}"
            ) from exc
        for value in raw.split():
            if not value.isascii() or not value.isdecimal():
                raise MutationAssuranceError("Linux task children data is invalid")
            pid = int(value)
            if pid <= 0:
                raise MutationAssuranceError("Linux task child PID is invalid")
            children.add(pid)
    return children


class _PosixSubreaper:
    """Adopt and reap descendants that deliberately leave the child's session."""

    _PR_SET_CHILD_SUBREAPER = 36
    _PR_GET_CHILD_SUBREAPER = 37

    def __init__(self) -> None:
        if os.name == "nt" or not sys.platform.startswith("linux"):
            raise MutationAssuranceError(
                "POSIX mutation children require Linux subreaper containment"
            )
        import ctypes

        libc = ctypes.CDLL(None, use_errno=True)
        previous = ctypes.c_int()
        if libc.prctl(
            self._PR_GET_CHILD_SUBREAPER,
            ctypes.byref(previous),
            0,
            0,
            0,
        ) != 0:
            raise MutationAssuranceError(
                "could not read Linux child-subreaper policy: "
                f"errno {ctypes.get_errno()}"
            )
        if previous.value not in (0, 1):
            raise MutationAssuranceError("Linux child-subreaper policy is invalid")
        if previous.value == 0 and libc.prctl(
            self._PR_SET_CHILD_SUBREAPER,
            1,
            0,
            0,
            0,
        ) != 0:
            raise MutationAssuranceError(
                "could not enable Linux child-subreaper policy: "
                f"errno {ctypes.get_errno()}"
            )
        self._ctypes = ctypes
        self._libc = libc
        self._previous = previous.value
        self._closed = False
        try:
            self._preexisting_children = _linux_direct_children()
        except BaseException:
            self.close()
            raise

    def terminate_adopted(self, *, timeout_seconds: float = 5.0) -> None:
        """Kill and reap all newly adopted descendants within a fixed bound."""

        deadline = time.monotonic() + timeout_seconds
        quiet_passes = 0
        while time.monotonic() < deadline:
            remaining = _linux_direct_children() - self._preexisting_children
            if not remaining:
                quiet_passes += 1
                if quiet_passes >= 2:
                    return
                time.sleep(0.01)
                continue
            quiet_passes = 0
            for pid in remaining:
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                except OSError as exc:
                    raise MutationAssuranceError(
                        f"could not terminate adopted descendant {pid}: {exc}"
                    ) from exc
            for pid in remaining:
                try:
                    os.waitpid(pid, os.WNOHANG)
                except ChildProcessError:
                    pass
            time.sleep(0.01)
        remaining = _linux_direct_children() - self._preexisting_children
        if remaining:
            unresolved = sorted(remaining)
            raise MutationAssuranceError(
                f"adopted descendants did not terminate: {unresolved}"
            )

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._previous == 0 and self._libc.prctl(
            self._PR_SET_CHILD_SUBREAPER,
            0,
            0,
            0,
            0,
        ) != 0:
            raise MutationAssuranceError(
                "could not restore Linux child-subreaper policy: "
                f"errno {self._ctypes.get_errno()}"
            )


def _terminate_process_tree(
    process: subprocess.Popen[bytes],
    *,
    windows_job: _WindowsJob | None,
    posix_subreaper: _PosixSubreaper | None,
) -> None:
    """Request bounded tree termination without ever performing an open wait."""

    errors: list[str] = []
    if os.name == "nt":
        if windows_job is None:
            raise MutationAssuranceError("Windows child has no Job Object containment")
        try:
            windows_job.terminate()
        except MutationAssuranceError as exc:
            errors.append(str(exc))
            if process.poll() is None:
                process.kill()
        if not windows_job.assigned and process.poll() is None:
            process.kill()
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError:
            if process.poll() is None:
                process.kill()
    parent_stuck = False
    interrupted: BaseException | None = None
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        if process.poll() is None:
            process.kill()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            parent_stuck = True
        except BaseException as exc:
            interrupted = exc
    except BaseException as exc:
        interrupted = exc
        if process.poll() is None:
            try:
                process.kill()
            except OSError as kill_exc:
                errors.append(f"child fallback kill failed: {kill_exc}")
    if posix_subreaper is not None:
        try:
            posix_subreaper.terminate_adopted()
        except MutationAssuranceError as exc:
            errors.append(str(exc))
    if parent_stuck:
        errors.append("child process did not terminate within the cleanup bound")
    if interrupted is not None:
        if errors and hasattr(interrupted, "add_note"):
            interrupted.add_note("child cleanup: " + "; ".join(errors))
        raise interrupted
    if errors:
        raise MutationAssuranceError("; ".join(errors))


class _BoundedPipeCapture:
    """Drain a child pipe while retaining at most ``_MAX_TEXT`` bytes."""

    def __init__(self, stream: Any, *, label: str) -> None:
        self._stream = stream
        self._label = label
        self._buffer = bytearray()
        self._digest = hashlib.sha256()
        self._total = 0
        self._error: str | None = None
        self._forced_close = False
        self._started = False
        self._lock = threading.Lock()
        self._thread = threading.Thread(
            target=self._drain,
            name=f"moira-mutation-{label}",
            daemon=True,
        )

    def start(self) -> None:
        try:
            self._thread.start()
        finally:
            self._started = self._thread.ident is not None

    def _drain(self) -> None:
        try:
            while True:
                chunk = self._stream.read(64 * 1024)
                if not chunk:
                    break
                with self._lock:
                    self._digest.update(chunk)
                    self._total += len(chunk)
                    remaining = _MAX_TEXT - len(self._buffer)
                    if remaining > 0:
                        self._buffer.extend(chunk[:remaining])
        except (OSError, ValueError) as exc:
            with self._lock:
                if not self._forced_close:
                    self._error = f"{type(exc).__name__}: {exc}"
        finally:
            try:
                self._stream.close()
            except OSError:
                pass

    def finish(self, *, timeout_seconds: float) -> tuple[str, str, bool, str | None]:
        if self._started:
            self._thread.join(timeout_seconds)
        if self._started and self._thread.is_alive():
            with self._lock:
                self._forced_close = True
            try:
                self._stream.close()
            except (OSError, ValueError):
                pass
            self._thread.join(2.0)
        with self._lock:
            raw = bytes(self._buffer)
            digest = self._digest.hexdigest()
            truncated = (
                self._total > _MAX_TEXT
                or self._forced_close
                or self._error is not None
                or self._thread.is_alive()
            )
            error = self._error
        if self._started and self._thread.is_alive():
            error = error or f"{self._label} pipe did not close after termination"
        return raw.decode("utf-8", "replace"), digest, truncated, error

    def abort(self, *, timeout_seconds: float = 2.0) -> None:
        """Close a partially started capture without an unbounded join."""

        with self._lock:
            self._forced_close = True
        try:
            self._stream.close()
        except (OSError, ValueError):
            pass
        if self._started:
            self._thread.join(timeout_seconds)


def _cleanup_exceptional_child(
    *,
    process: subprocess.Popen[bytes],
    windows_job: _WindowsJob | None,
    posix_subreaper: _PosixSubreaper | None,
    captures: Sequence[_BoundedPipeCapture | None],
) -> list[str]:
    """Best-effort bounded cleanup that never masks the triggering exception."""

    errors: list[str] = []
    try:
        _terminate_process_tree(
            process,
            windows_job=windows_job,
            posix_subreaper=posix_subreaper,
        )
    except BaseException as exc:
        errors.append(f"{type(exc).__name__}: {exc}")
    for capture in captures:
        if capture is None:
            continue
        try:
            capture.abort()
        except BaseException as exc:
            errors.append(f"capture abort {type(exc).__name__}: {exc}")
    if windows_job is not None:
        try:
            windows_job.close()
        except BaseException as exc:
            errors.append(f"job close {type(exc).__name__}: {exc}")
    if posix_subreaper is not None:
        try:
            posix_subreaper.close()
        except BaseException as exc:
            errors.append(f"subreaper close {type(exc).__name__}: {exc}")
    return errors


def _execute_child_serial(
    *,
    argv: Sequence[str],
    cwd: Path,
    environment: Mapping[str, str],
    timeout_seconds: int,
    report_path: Path,
) -> ProcessObservation:
    """Run one bounded serial child and load its independent structured report."""

    if report_path.exists():
        raise MutationAssuranceError("child report path already exists")
    creationflags = (
        getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        | getattr(subprocess, "CREATE_SUSPENDED", 0x00000004)
        if os.name == "nt"
        else 0
    )
    windows_job: _WindowsJob | None = None
    preexisting_windows_children: set[int] | None = None
    posix_subreaper: _PosixSubreaper | None = None
    process: subprocess.Popen[bytes] | None = None
    stdout_capture: _BoundedPipeCapture | None = None
    stderr_capture: _BoundedPipeCapture | None = None
    started = time.monotonic_ns()
    try:
        windows_job = _WindowsJob() if os.name == "nt" else None
        preexisting_windows_children = (
            _windows_direct_children() if os.name == "nt" else None
        )
        posix_subreaper = _PosixSubreaper() if os.name != "nt" else None
        try:
            process = subprocess.Popen(
                tuple(argv),
                cwd=cwd,
                env=dict(environment),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
                bufsize=0,
                creationflags=creationflags,
                start_new_session=os.name != "nt",
            )
        except OSError as exc:
            raise MutationAssuranceError(
                f"child process could not start: {exc}"
            ) from exc
        if windows_job is not None:
            windows_job.assign(process)
            windows_job.resume(process)
        if process.stdout is None or process.stderr is None:
            raise MutationAssuranceError("child output pipes were not created")
        stdout_capture = _BoundedPipeCapture(process.stdout, label="stdout")
        stderr_capture = _BoundedPipeCapture(process.stderr, label="stderr")
        stdout_capture.start()
        stderr_capture.start()
        timed_out = False
        containment_error: str | None = None
        try:
            process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True

        # Cleanup is unconditional: a green pytest parent is not permission
        # for redirected descendants to survive the mutation execution.
        try:
            _terminate_process_tree(
                process,
                windows_job=windows_job,
                posix_subreaper=posix_subreaper,
            )
        except MutationAssuranceError as exc:
            containment_error = str(exc)
        if windows_job is not None:
            windows_job.close()
        if posix_subreaper is not None:
            try:
                posix_subreaper.close()
            except MutationAssuranceError as exc:
                existing = f"{containment_error}; " if containment_error else ""
                containment_error = existing + str(exc)
        if process.poll() is None:
            timed_out = True
            containment_error = (
                containment_error or "child process did not terminate"
            )
        duration = time.monotonic_ns() - started
        stdout, stdout_digest, stdout_truncated, stdout_error = (
            stdout_capture.finish(timeout_seconds=5.0)
        )
        stderr, stderr_digest, stderr_truncated, stderr_error = (
            stderr_capture.finish(timeout_seconds=5.0)
        )
        report: Mapping[str, object] | None = None
        report_digest: str | None = None
        report_error: str | None = None
        if (
            containment_error is not None
            or stdout_error is not None
            or stderr_error is not None
        ):
            report_error = "; ".join(
                value
                for value in (containment_error, stdout_error, stderr_error)
                if value is not None
            )
        if report_path.exists():
            try:
                report_raw = stable_file_bytes(
                    report_path,
                    maximum_bytes=_MAX_JSON_BYTES,
                    label="mutation child report",
                )
                parsed = strict_json_bytes(
                    report_raw,
                    label="mutation child report",
                )
                if not isinstance(parsed, dict):
                    raise MutationAssuranceError(
                        "mutation child report is not an object"
                    )
                report = MappingProxyType(parsed)
                report_digest = sha256_bytes(report_raw)
            except MutationAssuranceError as exc:
                existing = f"{report_error}; " if report_error else ""
                report_error = existing + str(exc)
        elif report_error is None:
            report_error = "mutation child report is missing"
        return ProcessObservation(
            argv=tuple(argv),
            returncode=process.returncode,
            timed_out=timed_out,
            duration_ns=duration,
            stdout=stdout,
            stderr=stderr,
            stdout_sha256=stdout_digest,
            stderr_sha256=stderr_digest,
            output_truncated=stdout_truncated or stderr_truncated,
            report=report,
            report_sha256=report_digest,
            report_error=report_error,
        )
    except BaseException as exc:
        if process is None:
            cleanup_errors: list[str] = []
            if preexisting_windows_children is not None:
                try:
                    _terminate_new_windows_children(
                        preexisting_windows_children
                    )
                except BaseException as cleanup_exc:
                    cleanup_errors.append(
                        "Windows pre-handle cleanup "
                        f"{type(cleanup_exc).__name__}: {cleanup_exc}"
                    )
            if windows_job is not None:
                try:
                    windows_job.close()
                except BaseException as cleanup_exc:
                    cleanup_errors.append(
                        "job close "
                        f"{type(cleanup_exc).__name__}: {cleanup_exc}"
                    )
            if posix_subreaper is not None:
                try:
                    posix_subreaper.terminate_adopted()
                except BaseException as cleanup_exc:
                    cleanup_errors.append(
                        "subreaper adoption cleanup "
                        f"{type(cleanup_exc).__name__}: {cleanup_exc}"
                    )
                try:
                    posix_subreaper.close()
                except BaseException as cleanup_exc:
                    cleanup_errors.append(
                        "subreaper close "
                        f"{type(cleanup_exc).__name__}: {cleanup_exc}"
                    )
        else:
            cleanup_errors = _cleanup_exceptional_child(
                process=process,
                windows_job=windows_job,
                posix_subreaper=posix_subreaper,
                captures=(stdout_capture, stderr_capture),
            )
        if cleanup_errors:
            raise MutationAssuranceError(
                "mutation child cleanup failed after "
                f"{type(exc).__name__}: {exc}: {'; '.join(cleanup_errors)}"
            ) from exc
        raise


def execute_child(
    *,
    argv: Sequence[str],
    cwd: Path,
    environment: Mapping[str, str],
    timeout_seconds: int,
    report_path: Path,
) -> ProcessObservation:
    """Run one child under process-wide serial descendant containment."""

    with _CHILD_EXECUTION_LOCK:
        return _execute_child_serial(
            argv=argv,
            cwd=cwd,
            environment=environment,
            timeout_seconds=timeout_seconds,
            report_path=report_path,
        )


def _object(value: object, *, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise MutationAssuranceError(f"{label} must be an object")
    return value


def _list(value: object, *, label: str) -> list[object]:
    if not isinstance(value, list):
        raise MutationAssuranceError(f"{label} must be a list")
    return value


def _exact_fields(value: Mapping[str, object], fields: set[str], *, label: str) -> None:
    if set(value) != fields:
        raise MutationAssuranceError(f"{label} fields are not exact")


def _reject_truncation(value: object, *, label: str = "child report") -> None:
    pending: list[tuple[object, str]] = [(value, label)]
    while pending:
        current, current_label = pending.pop()
        if isinstance(current, dict):
            for key, item in current.items():
                if key.endswith("_truncated") or key == "truncated":
                    if item is not False:
                        raise MutationAssuranceError(
                            f"{current_label}.{key} reports truncated evidence"
                        )
                pending.append((item, f"{current_label}.{key}"))
        elif isinstance(current, list):
            pending.extend(
                (item, f"{current_label}[{index}]")
                for index, item in enumerate(current)
            )


def _resolved_report_path(value: object, *, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise MutationAssuranceError(f"{label} is not a path")
    try:
        return Path(value).resolve(strict=True)
    except OSError as exc:
        raise MutationAssuranceError(f"{label} is unavailable: {exc}") from exc


def _pure_receipt_path(
    value: object,
    *,
    label: str,
) -> PurePosixPath | PureWindowsPath:
    if not isinstance(value, str) or not value:
        raise MutationAssuranceError(f"{label} is not a path")
    path: PurePosixPath | PureWindowsPath
    if "\\" in value or re.match(r"^[A-Za-z]:", value):
        path = PureWindowsPath(value)
    else:
        path = PurePosixPath(value)
    if not path.is_absolute() or any(part == ".." for part in path.parts):
        raise MutationAssuranceError(f"{label} is not an absolute normalized path")
    return path


def _validate_child_argv(
    argv: Sequence[object],
    *,
    spec: MutantSpec,
    execution_id: str,
    snapshot_root: object,
    interpreter: str,
) -> None:
    root = _pure_receipt_path(snapshot_root, label="child argv snapshot root")
    if root.name != "snapshot":
        raise MutationAssuranceError("child argv snapshot root has the wrong layout")
    control_root = root.parent / "control"
    expected = _expected_child_argv(
        interpreter=interpreter,
        control_root=control_root,
        spec=spec,
        execution_id=execution_id,
    )
    if tuple(argv) != expected:
        raise MutationAssuranceError("child argv is not the exact admitted invocation")


def _file_identity_matches(
    value: object,
    *,
    expected_path: Path,
    expected_sha256: str,
    label: str,
) -> None:
    identity = _object(value, label=label)
    required = {"path", "path_truncated", "bytes", "sha256"}
    _exact_fields(identity, required, label=label)
    if identity["path_truncated"] is not False:
        raise MutationAssuranceError(f"{label} path is truncated")
    observed_path = _resolved_report_path(identity["path"], label=f"{label}.path")
    if observed_path != expected_path.resolve(strict=True):
        raise MutationAssuranceError(f"{label} resolved outside the admitted path")
    if identity["sha256"] != expected_sha256:
        raise MutationAssuranceError(f"{label} digest is not the admitted digest")
    if identity["bytes"] != expected_path.stat().st_size:
        raise MutationAssuranceError(f"{label} byte count is inconsistent")


def _module_file(
    modules: Mapping[str, object],
    role: str,
    *,
    expected_name: str,
    expected_path: Path,
    expected_sha256: str,
    expected_loader: str,
    expected_loader_policy: str,
) -> None:
    module = _object(modules.get(role), label=f"identity.modules.{role}")
    _exact_fields(
        module,
        {
            "available",
            "name",
            "name_truncated",
            "file",
            "file_error",
            "file_error_truncated",
            "spec",
        },
        label=f"identity.modules.{role}",
    )
    if (
        module.get("available") is not True
        or module.get("name") != expected_name
        or module.get("name_truncated") is not False
        or module.get("file_error") is not None
        or module.get("file_error_truncated") is not False
    ):
        raise MutationAssuranceError(f"identity.modules.{role} is invalid")
    _file_identity_matches(
        module.get("file"),
        expected_path=expected_path,
        expected_sha256=expected_sha256,
        label=f"identity.modules.{role}.file",
    )
    specification = _object(
        module.get("spec"),
        label=f"identity.modules.{role}.spec",
    )
    _exact_fields(
        specification,
        {
            "name",
            "name_truncated",
            "origin",
            "origin_truncated",
            "loader",
            "loader_truncated",
            "loader_policy",
        },
        label=f"identity.modules.{role}.spec",
    )
    origin = specification["origin"]
    if (
        specification["name"] != expected_name
        or specification["name_truncated"] is not False
        or not isinstance(origin, str)
        or specification["origin_truncated"] is not False
        or specification["loader"] != expected_loader
        or specification["loader_truncated"] is not False
        or specification["loader_policy"] != expected_loader_policy
    ):
        raise MutationAssuranceError(
            f"identity.modules.{role}.spec is not the admitted loader identity"
        )
    if _resolved_report_path(origin, label=f"identity.modules.{role}.spec.origin") != expected_path.resolve(strict=True):
        raise MutationAssuranceError(f"identity.modules.{role} spec origin is foreign")


def _intended_test_callable(
    value: object,
    *,
    expected_module: str,
    expected_qualname: str,
    expected_path: Path,
    expected_code_sha256: str,
    label: str,
) -> dict[str, object]:
    identity = _object(value, label=label)
    _exact_fields(
        identity,
        {
            "available",
            "type",
            "module",
            "name",
            "qualname",
            "module_binding_exact",
            "wrapped",
            "code",
            "stable_during_execution",
        },
        label=label,
    )
    if (
        identity["available"] is not True
        or identity["type"] != "builtins.function"
        or identity["module"] != expected_module
        or identity["name"] != expected_qualname
        or identity["qualname"] != expected_qualname
        or identity["module_binding_exact"] is not True
        or identity["wrapped"] is not False
        or identity["stable_during_execution"] is not True
    ):
        raise MutationAssuranceError(f"{label} is not the exact stable function binding")
    code = _object(identity["code"], label=f"{label}.code")
    _exact_fields(
        code,
        {
            "algorithm",
            "filename",
            "filename_truncated",
            "qualname",
            "sha256",
        },
        label=f"{label}.code",
    )
    if (
        code["algorithm"] != INTENDED_TEST_CODE_DIGEST_ALGORITHM
        or code["filename_truncated"] is not False
        or code["qualname"] != expected_qualname
        or code["sha256"] != expected_code_sha256
        or _resolved_report_path(
            code["filename"],
            label=f"{label}.code.filename",
        )
        != expected_path.resolve(strict=True)
    ):
        raise MutationAssuranceError(f"{label} code is not the admitted test function")
    return identity


def _evidence_properties(
    report: Mapping[str, object],
    *,
    spec: MutantSpec,
) -> None:
    raw = _list(
        report.get("evidence_user_properties"),
        label="phase evidence properties",
    )
    observed: dict[str, str] = {}
    for index, item in enumerate(raw):
        entry = _object(item, label=f"phase evidence properties[{index}]")
        _exact_fields(
            entry,
            {"name", "name_truncated", "value", "value_truncated"},
            label=f"phase evidence properties[{index}]",
        )
        if entry["name_truncated"] is not False or entry["value_truncated"] is not False:
            raise MutationAssuranceError("phase evidence property is truncated")
        name = entry["name"]
        value = entry["value"]
        if not isinstance(name, str) or not isinstance(value, str) or name in observed:
            raise MutationAssuranceError("phase evidence properties are ambiguous")
        observed[name] = value
    expected = {
        "moira_validation_claim_id": spec.expected_claim_id,
        "moira_validation_contract_sha256": spec.expected_contract_sha256,
    }
    if observed != expected:
        raise MutationAssuranceError("phase evidence binding contradicts the catalogue")


def _validate_common_child_report(
    *,
    spec: MutantSpec,
    observation: ProcessObservation,
    execution_id: str,
    snapshot_root: Path,
    interpreter: Mapping[str, object],
    expected_source_sha256: str,
    expected_code_sha256: str,
    native_backend_path: Path,
    native_backend_sha256: str,
) -> tuple[dict[str, object], tuple[dict[str, object], ...]]:
    if observation.timed_out:
        raise MutationAssuranceError("child execution timed out")
    if observation.output_truncated:
        raise MutationAssuranceError("child stdout or stderr was truncated")
    if observation.report_error is not None or observation.report is None:
        raise MutationAssuranceError(
            observation.report_error or "child report is unavailable"
        )
    report = dict(observation.report)
    _exact_fields(
        report,
        {
            "schema_version",
            "execution_id",
            "intended",
            "selection",
            "errors",
            "reports",
            "trace",
            "identity",
            "pytest",
        },
        label="child report",
    )
    if report["schema_version"] != CHILD_REPORT_SCHEMA_VERSION:
        raise MutationAssuranceError("child report schema is unsupported")
    if report["execution_id"] != execution_id:
        raise MutationAssuranceError("child report execution ID is stale")
    _reject_truncation(report)

    test_relative, test_module_name, test_qualname = (
        _intended_test_coordinates(spec.intended_killer_nodeid)
    )
    expected_test_path = snapshot_root.joinpath(
        *PurePosixPath(test_relative).parts
    ).resolve(strict=True)
    expected_test_source = stable_file_bytes(
        expected_test_path,
        maximum_bytes=_MAX_MUTATION_SOURCE_BYTES,
        label="intended test source",
    )
    expected_test_source_sha256 = sha256_bytes(expected_test_source)
    expected_test_code_sha256 = pytest_rewritten_source_code_sha256(
        expected_test_source,
        qualname=test_qualname,
        filename=str(expected_test_path),
    )
    intended = _object(report["intended"], label="child report intended")
    expected_intended = {
        "nodeid": spec.intended_killer_nodeid,
        "source_relative_path": spec.source_path,
        "module_name": spec.module_name,
        "target_qualname": spec.target_qualname,
        "test_source_relative_path": test_relative,
        "test_module_name": test_module_name,
        "test_qualname": test_qualname,
    }
    if intended != expected_intended:
        raise MutationAssuranceError("child intended identity contradicts the catalogue")

    selection = _object(report["selection"], label="child report selection")
    _exact_fields(
        selection,
        {
            "selected_nodeids",
            "selected_count",
            "intended_selected_count",
            "only_intended_selected",
        },
        label="child report selection",
    )
    selected = _list(selection["selected_nodeids"], label="selected node IDs")
    if selected != [{"nodeid": spec.intended_killer_nodeid, "truncated": False}]:
        raise MutationAssuranceError("child selected an unexpected test item")
    if (
        selection["selected_count"] != 1
        or selection["intended_selected_count"] != 1
        or selection["only_intended_selected"] is not True
    ):
        raise MutationAssuranceError("child selection counters are inconsistent")

    errors = _object(report["errors"], label="child report errors")
    _exact_fields(errors, {"collection", "internal"}, label="child report errors")
    if errors["collection"] != [] or errors["internal"] != []:
        raise MutationAssuranceError("child reported collection or internal errors")

    raw_reports = _list(report["reports"], label="child phase reports")
    if len(raw_reports) != 3:
        raise MutationAssuranceError("child did not emit exactly three item phases")
    phase_reports: list[dict[str, object]] = []
    for index, raw_phase in enumerate(raw_reports):
        phase = _object(raw_phase, label=f"child phase reports[{index}]")
        required = {
            "sequence",
            "nodeid",
            "nodeid_truncated",
            "phase",
            "outcome",
            "outcome_truncated",
            "duration_s",
            "wasxfail",
            "wasxfail_truncated",
            "exception",
            "evidence_user_properties",
            "longrepr",
            "longrepr_truncated",
            "rerun",
            "rerun_index",
        }
        _exact_fields(phase, required, label=f"child phase reports[{index}]")
        if phase["sequence"] != index + 1:
            raise MutationAssuranceError("child phase sequence is inconsistent")
        if phase["nodeid"] != spec.intended_killer_nodeid:
            raise MutationAssuranceError("child phase belongs to an unexpected item")
        if phase["nodeid_truncated"] is not False or phase["outcome_truncated"] is not False:
            raise MutationAssuranceError("child phase identity is truncated")
        if phase["wasxfail"] is not None or phase["wasxfail_truncated"] is not False:
            raise MutationAssuranceError("xfail evidence cannot kill a mutant")
        if phase["rerun"] is not False or phase["rerun_index"] is not None:
            raise MutationAssuranceError("rerun evidence cannot kill a mutant")
        duration = phase["duration_s"]
        if not isinstance(duration, (int, float)) or isinstance(duration, bool) or not math.isfinite(float(duration)) or float(duration) < 0.0:
            raise MutationAssuranceError("child phase duration is invalid")
        _evidence_properties(phase, spec=spec)
        phase_reports.append(phase)
    if tuple(phase["phase"] for phase in phase_reports) != (
        "setup",
        "call",
        "teardown",
    ):
        raise MutationAssuranceError("child phase order is not setup/call/teardown")

    trace = _object(report["trace"], label="child target trace")
    _exact_fields(
        trace,
        {
            "algorithm",
            "attempted",
            "preexisting_tracer",
            "call_count",
            "frame_filenames",
            "code_sha256",
            "resolved_target_code_sha256",
            "target_binding_exact",
            "intended_test_call_count",
            "intended_test_frame_filenames",
            "intended_test_code_sha256",
            "resolved_intended_test_code_sha256",
        },
        label="child target trace",
    )
    if (
        trace["algorithm"] != "python_code_v1"
        or trace["attempted"] is not True
        or trace["preexisting_tracer"] is not False
        or not isinstance(trace["call_count"], int)
        or isinstance(trace["call_count"], bool)
        or trace["call_count"] < 1
        or trace["code_sha256"] != [expected_code_sha256]
        or trace["resolved_target_code_sha256"] != expected_code_sha256
        or trace["target_binding_exact"] is not True
        or trace["intended_test_call_count"] != 1
        or trace["intended_test_code_sha256"] != [expected_test_code_sha256]
        or trace["resolved_intended_test_code_sha256"]
        != expected_test_code_sha256
    ):
        raise MutationAssuranceError("child target trace does not prove the admitted code")
    expected_source_path = snapshot_root / Path(spec.source_path)
    filenames = trace["frame_filenames"]
    if not isinstance(filenames, list) or len(filenames) != 1:
        raise MutationAssuranceError("child target trace filename is ambiguous")
    if _resolved_report_path(filenames[0], label="trace frame filename") != expected_source_path.resolve(strict=True):
        raise MutationAssuranceError("child target trace came from a foreign source")
    test_filenames = trace["intended_test_frame_filenames"]
    if not isinstance(test_filenames, list) or len(test_filenames) != 1:
        raise MutationAssuranceError("child intended-test trace filename is ambiguous")
    if (
        _resolved_report_path(
            test_filenames[0],
            label="intended-test trace frame filename",
        )
        != expected_test_path
    ):
        raise MutationAssuranceError("child intended-test trace came from a foreign source")

    identity = _object(report["identity"], label="child identity")
    _exact_fields(
        identity,
        {
            "interpreter",
            "cwd",
            "cwd_truncated",
            "root",
            "root_truncated",
            "source",
            "modules",
            "intended_test_callable",
            "policy_environment",
            "network",
            "test_toolchain",
        },
        label="child identity",
    )
    _validate_child_toolchain_attestation(
        identity["test_toolchain"],
        interpreter=interpreter,
    )
    modules = _object(identity.get("modules"), label="child identity modules")
    expected_module_roles = {
        "target_module",
        "intended_test",
        "moira",
        "reporter",
        "sitecustomize",
        "native_backend",
        "toolchain",
    }
    if set(modules) != expected_module_roles:
        raise MutationAssuranceError("child identity module roles are not exact")
    expected_source_path = expected_source_path.resolve(strict=True)
    _file_identity_matches(
        identity.get("source"),
        expected_path=expected_source_path,
        expected_sha256=expected_source_sha256,
        label="child source identity",
    )
    _module_file(
        modules,
        "target_module",
        expected_name=spec.module_name,
        expected_path=expected_source_path,
        expected_sha256=expected_source_sha256,
        expected_loader=_SOURCE_LOADER_NAME,
        expected_loader_policy="source",
    )
    _module_file(
        modules,
        "intended_test",
        expected_name=test_module_name,
        expected_path=expected_test_path,
        expected_sha256=expected_test_source_sha256,
        expected_loader=_PYTEST_REWRITE_LOADER_NAME,
        expected_loader_policy="pytest_assertion_rewrite_disabled",
    )
    _intended_test_callable(
        identity["intended_test_callable"],
        expected_module=test_module_name,
        expected_qualname=test_qualname,
        expected_path=expected_test_path,
        expected_code_sha256=expected_test_code_sha256,
        label="child intended-test callable",
    )
    for role, module_name, relative, loader, loader_policy in (
        ("moira", "moira", "moira/__init__.py", _SOURCE_LOADER_NAME, "source"),
        (
            "reporter",
            "tests.mutation_reporter",
            "tests/mutation_reporter.py",
            _PYTEST_REWRITE_LOADER_NAME,
            "pytest_assertion_rewrite_disabled",
        ),
        (
            "sitecustomize",
            "sitecustomize",
            "tests/support/network_bootstrap/sitecustomize.py",
            _SOURCE_LOADER_NAME,
            "source",
        ),
        (
            "toolchain",
            "support.mutation_toolchain",
            "tests/support/mutation_toolchain.py",
            _SOURCE_LOADER_NAME,
            "source",
        ),
    ):
        expected_path = snapshot_root / Path(relative)
        raw = stable_file_bytes(expected_path, maximum_bytes=None, label=f"snapshot {role}")
        _module_file(
            modules,
            role,
            expected_name=module_name,
            expected_path=expected_path,
            expected_sha256=sha256_bytes(raw),
            expected_loader=loader,
            expected_loader_policy=loader_policy,
        )
    _module_file(
        modules,
        "native_backend",
        expected_name="moira._moira_native",
        expected_path=native_backend_path,
        expected_sha256=native_backend_sha256,
        expected_loader=_EXTENSION_LOADER_NAME,
        expected_loader_policy="extension",
    )
    cwd = identity.get("cwd")
    root_value = identity.get("root")
    if (
        _resolved_report_path(cwd, label="child cwd") != snapshot_root.resolve(strict=True)
        or _resolved_report_path(root_value, label="child root") != snapshot_root.resolve(strict=True)
    ):
        raise MutationAssuranceError("child cwd or pytest root escaped the snapshot")
    _validate_child_argv(
        observation.argv,
        spec=spec,
        execution_id=execution_id,
        snapshot_root=root_value,
        interpreter=str(interpreter["executable"]),
    )
    child_interpreter = _object(identity.get("interpreter"), label="child interpreter")
    if "implementation" in interpreter or "version" in interpreter:
        expected_implementation, expected_version, expected_cache_tag = (
            _expected_child_interpreter_runtime(interpreter)
        )
        if (
            child_interpreter.get("implementation") != expected_implementation
            or child_interpreter.get("version") != expected_version
            or child_interpreter.get("cache_tag") != expected_cache_tag
        ):
            raise MutationAssuranceError("child interpreter runtime identity changed")
    expected_pycache = (
        snapshot_root.parent / "control" / f"pycache-{execution_id}"
    ).resolve()
    observed_pycache = child_interpreter.get("pycache_prefix")
    if (
        not isinstance(observed_pycache, str)
        or Path(observed_pycache).resolve() != expected_pycache
    ):
        raise MutationAssuranceError("child interpreter pycache prefix is foreign")
    _file_identity_matches(
        child_interpreter.get("executable"),
        expected_path=Path(
            str(interpreter.get("executable_resolved", interpreter["executable"]))
        ),
        expected_sha256=str(interpreter["sha256"]),
        label="child interpreter executable",
    )
    if child_interpreter.get("prefix") != interpreter["prefix"]:
        raise MutationAssuranceError("child interpreter prefix changed")
    if child_interpreter.get("base_prefix") != interpreter["base_prefix"]:
        raise MutationAssuranceError("child interpreter base prefix changed")
    flags = _object(child_interpreter.get("flags"), label="child interpreter flags")
    if flags.get("safe_path") is not True:
        raise MutationAssuranceError("child interpreter did not honor -P safe path")
    if flags.get("optimize") != 0:
        raise MutationAssuranceError("child interpreter optimization is not zero")
    if flags.get("dont_write_bytecode") is not True:
        raise MutationAssuranceError("child interpreter may write stale bytecode")
    if flags.get("no_user_site") is not True:
        raise MutationAssuranceError("child interpreter did not disable user site")
    policy_environment = _object(
        identity.get("policy_environment"),
        label="child policy environment",
    )
    expected_environment = {
        "MOIRA_TEST_MODE": "1",
        "MOIRA_NO_DOWNLOAD": "1",
        "MOIRA_STRICT_KNOWN_ISSUES": "1",
        "MOIRA_TEST_NETWORK_POLICY": "deny",
        "MOIRA_TEST_ARTIFACTS": "0",
        "MOIRA_TEST_SEED": None,
        "MOIRA_TEST_BUDGET_TOTAL_S": "0",
        "MOIRA_TEST_BUDGET_CASE_S": "0",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
        "PYTHONNOUSERSITE": "1",
        "PYTHONOPTIMIZE": "0",
    }
    if set(policy_environment) != set(expected_environment):
        raise MutationAssuranceError("child policy environment is not admitted")
    for name, expected in expected_environment.items():
        entry = _object(
            policy_environment.get(name),
            label=f"child policy environment {name}",
        )
        if entry.get("truncated") is not False:
            raise MutationAssuranceError(f"child policy environment {name} is truncated")
        value = entry.get("value")
        if name == "MOIRA_TEST_SEED":
            if not isinstance(value, str) or not value.isdecimal():
                raise MutationAssuranceError("child mutation seed is invalid")
        elif value != expected:
            raise MutationAssuranceError(f"child policy environment {name} changed")
    network = _object(identity.get("network"), label="child network policy")
    if (
        network.get("available") is not True
        or network.get("audit_hook_installed") is not True
        or network.get("audit_canary_seen") is not True
        or network.get("socket_method_guards_installed") is not True
        or network.get("asyncio_method_guards_installed") is not True
        or network.get("active_mode") != "deny"
        or network.get("environment_mode") != "deny"
        or network.get("active_nodeid_truncated") is not False
    ):
        raise MutationAssuranceError("cooperative network audit hook was not installed")

    pytest_payload = _object(report["pytest"], label="child pytest identity")
    _exact_fields(pytest_payload, {"exitstatus"}, label="child pytest identity")
    return report, tuple(phase_reports)


def _exception_matches(
    exception: object,
    *,
    longrepr: object,
    spec: MutantSpec,
) -> None:
    payload = _object(exception, label="call exception")
    if payload.get("type") != spec.expected_failure.exception_type:
        raise MutationAssuranceError("call exception type is not the intended witness")
    if payload.get("type_truncated") is not False or payload.get("message_truncated") is not False:
        raise MutationAssuranceError("call exception witness is truncated")
    message = payload.get("message")
    if not isinstance(message, str) or any(
        expected not in message
        for expected in spec.expected_failure.message_contains
    ):
        raise MutationAssuranceError("call exception message is not the intended witness")
    if not isinstance(longrepr, str) or any(
        expected not in longrepr
        for expected in spec.expected_failure.longrepr_contains
    ):
        raise MutationAssuranceError("call longrepr is not the intended witness")
    expected_witness = spec.expected_failure.metamorphic_witness
    observed_witness = payload.get("metamorphic_violation")
    if expected_witness is None:
        if observed_witness is not None:
            raise MutationAssuranceError("unexpected metamorphic witness type")
        return
    witness = _object(observed_witness, label="metamorphic exception witness")
    for key, expected in expected_witness.items():
        if witness.get(key) != expected:
            raise MutationAssuranceError(f"metamorphic witness {key} is wrong")
        if witness.get(f"{key}_truncated") is not False:
            raise MutationAssuranceError(f"metamorphic witness {key} is truncated")
    observed = witness.get("observed")
    limit = witness.get("limit")
    if (
        isinstance(observed, bool)
        or not isinstance(observed, (int, float))
        or isinstance(limit, bool)
        or not isinstance(limit, (int, float))
        or not math.isfinite(float(observed))
        or not math.isfinite(float(limit))
        or float(observed) <= float(limit)
    ):
        raise MutationAssuranceError("metamorphic witness does not exceed its limit")


def process_observation_payload(observation: ProcessObservation) -> dict[str, object]:
    return {
        "argv": list(observation.argv),
        "returncode": observation.returncode,
        "timed_out": observation.timed_out,
        "duration_ns": observation.duration_ns,
        "stdout": observation.stdout,
        "stderr": observation.stderr,
        "stdout_sha256": observation.stdout_sha256,
        "stderr_sha256": observation.stderr_sha256,
        "output_truncated": observation.output_truncated,
        "report_sha256": observation.report_sha256,
        "report_error": observation.report_error,
        "observed_child_report": (
            dict(observation.report) if observation.report is not None else None
        ),
    }


def seal_adjudication_record(value: Mapping[str, object]) -> dict[str, object]:
    """Bind one exact adjudication payload to all of its structured evidence."""

    if "adjudication_sha256" in value:
        raise MutationAssuranceError("adjudication record is already sealed")
    result = dict(value)
    result["adjudication_sha256"] = sha256_bytes(canonical_json_bytes(result))
    return result


def _runtime_source_identity(
    *,
    spec: MutantSpec,
    snapshot_root: Path,
    canonical_sha256: str,
    ast_sha256: str,
    code_sha256: str,
) -> tuple[dict[str, object], str]:
    source_path = snapshot_root / Path(spec.source_path)
    source = stable_file_bytes(
        source_path,
        maximum_bytes=_MAX_MUTATION_SOURCE_BYTES,
        label="adjudication source",
    )
    canonical = canonical_source_bytes(source)
    if sha256_bytes(canonical) != canonical_sha256:
        raise MutationAssuranceError("parent canonical source identity is wrong")
    if _canonical_ast_sha256(canonical, qualname=spec.target_qualname) != ast_sha256:
        raise MutationAssuranceError("parent target AST identity is wrong")
    if python_source_code_sha256(canonical, qualname=spec.target_qualname) != code_sha256:
        raise MutationAssuranceError("parent target code identity is wrong")
    runtime_sha256 = sha256_bytes(source)
    return (
        {
            "source_path": spec.source_path,
            "target_qualname": spec.target_qualname,
            "source_hash_mode": spec.source_hash_mode,
            "canonical_source_sha256": canonical_sha256,
            "runtime_source_sha256": runtime_sha256,
            "runtime_source_base64": base64.b64encode(source).decode("ascii"),
            "ast_sha256": ast_sha256,
            "code_sha256": code_sha256,
        },
        runtime_sha256,
    )


def _intended_test_source_identity(
    *,
    spec: MutantSpec,
    snapshot_root: Path,
) -> dict[str, object]:
    relative, module_name, qualname = _intended_test_coordinates(
        spec.intended_killer_nodeid
    )
    source_path = snapshot_root.joinpath(*PurePosixPath(relative).parts)
    source = stable_file_bytes(
        source_path,
        maximum_bytes=_MAX_MUTATION_SOURCE_BYTES,
        label="intended test source evidence",
    )
    return {
        "schema_version": 1,
        "source_path": relative,
        "module_name": module_name,
        "qualname": qualname,
        "source_bytes": len(source),
        "source_sha256": sha256_bytes(source),
        "source_base64": base64.b64encode(source).decode("ascii"),
        "rewrite_policy": "pytest_assertion_rewrite_disabled",
        "code_algorithm": INTENDED_TEST_CODE_DIGEST_ALGORITHM,
        "code_sha256": pytest_rewritten_source_code_sha256(
            source,
            qualname=qualname,
            filename=str(source_path.resolve(strict=True)),
        ),
    }


def adjudicate_baseline(
    *,
    spec: MutantSpec,
    observation: ProcessObservation,
    execution_id: str,
    snapshot_root: Path,
    interpreter: Mapping[str, object],
    native_backend_path: Path,
    native_backend_sha256: str,
) -> dict[str, object]:
    """Admit only one exact green baseline with target execution proof."""

    reasons: list[str] = []
    phases: tuple[dict[str, object], ...] = ()
    report: dict[str, object] | None = None
    source_identity: dict[str, object] | None = None
    intended_test_source: dict[str, object] | None = None
    runtime_source_sha256: str | None = None
    try:
        source_identity, runtime_source_sha256 = _runtime_source_identity(
            spec=spec,
            snapshot_root=snapshot_root,
            canonical_sha256=spec.preimage_sha256,
            ast_sha256=spec.preimage_ast_sha256,
            code_sha256=spec.preimage_code_sha256,
        )
    except MutationAssuranceError as exc:
        reasons.append(str(exc))
    try:
        intended_test_source = _intended_test_source_identity(
            spec=spec,
            snapshot_root=snapshot_root,
        )
    except MutationAssuranceError as exc:
        reasons.append(str(exc))
    if observation.timed_out:
        reasons.append("baseline timed out")
    elif runtime_source_sha256 is not None:
        try:
            report, phases = _validate_common_child_report(
                spec=spec,
                observation=observation,
                execution_id=execution_id,
                snapshot_root=snapshot_root,
                interpreter=interpreter,
                expected_source_sha256=runtime_source_sha256,
                expected_code_sha256=spec.preimage_code_sha256,
                native_backend_path=native_backend_path,
                native_backend_sha256=native_backend_sha256,
            )
        except MutationAssuranceError as exc:
            reasons.append(str(exc))
    if report is not None:
        exitstatus = _object(report["pytest"], label="pytest")["exitstatus"]
        exit_payload = _object(exitstatus, label="pytest exitstatus")
        if observation.returncode != 0 or exit_payload.get("code") != 0 or exit_payload.get("name") != "OK":
            reasons.append("baseline process or child exit status is not green")
        if tuple(phase["outcome"] for phase in phases) != (
            "passed",
            "passed",
            "passed",
        ):
            reasons.append("baseline did not pass setup/call/teardown")
        if any(phase["exception"] is not None for phase in phases):
            reasons.append("baseline carried an unexpected exception")
    return seal_adjudication_record({
        "execution_id": execution_id,
        "mutant_id": spec.mutant_id,
        "outcome": "baseline_passed" if not reasons else "blocked_baseline",
        "gate_credit": False,
        "reasons": reasons,
        "source_identity": source_identity,
        "intended_test_source": intended_test_source,
        "process": process_observation_payload(observation),
        "child_report": report,
    })


def adjudicate_mutant(
    *,
    spec: MutantSpec,
    observation: ProcessObservation,
    execution_id: str,
    snapshot_root: Path,
    interpreter: Mapping[str, object],
    native_backend_path: Path,
    native_backend_sha256: str,
) -> dict[str, object]:
    """Grant credit only to the intended, structured, call-phase killer."""

    source_identity: dict[str, object] | None = None
    intended_test_source: dict[str, object] | None = None
    runtime_source_sha256: str | None = None
    source_reasons: list[str] = []
    try:
        source_identity, runtime_source_sha256 = _runtime_source_identity(
            spec=spec,
            snapshot_root=snapshot_root,
            canonical_sha256=spec.postimage_sha256,
            ast_sha256=spec.postimage_ast_sha256,
            code_sha256=spec.postimage_code_sha256,
        )
    except MutationAssuranceError as exc:
        source_reasons.append(str(exc))
    try:
        intended_test_source = _intended_test_source_identity(
            spec=spec,
            snapshot_root=snapshot_root,
        )
    except MutationAssuranceError as exc:
        source_reasons.append(str(exc))
    if observation.timed_out:
        outcome = "timed_out"
        reasons = [*source_reasons, "mutant execution timed out"]
        report = None
        phases: tuple[dict[str, object], ...] = ()
    else:
        reasons = list(source_reasons)
        report = None
        phases = ()
        try:
            if runtime_source_sha256 is None:
                raise MutationAssuranceError("mutant runtime source identity is unavailable")
            report, phases = _validate_common_child_report(
                spec=spec,
                observation=observation,
                execution_id=execution_id,
                snapshot_root=snapshot_root,
                interpreter=interpreter,
                expected_source_sha256=runtime_source_sha256,
                expected_code_sha256=spec.postimage_code_sha256,
                native_backend_path=native_backend_path,
                native_backend_sha256=native_backend_sha256,
            )
        except MutationAssuranceError as exc:
            reasons.append(str(exc))
        outcome = "invalid_execution" if reasons else "wrong_killer"

    actual_killer: dict[str, object] | None = None
    if report is not None:
        setup, call, teardown = phases
        exit_payload = _object(
            _object(report["pytest"], label="pytest")["exitstatus"],
            label="pytest exitstatus",
        )
        phase_outcomes = (
            setup["outcome"],
            call["outcome"],
            teardown["outcome"],
        )
        if setup["exception"] is not None or teardown["exception"] is not None:
            outcome = "invalid_execution"
            reasons.append("passed setup or teardown carried an exception")
        elif phase_outcomes == ("passed", "passed", "passed"):
            if call["exception"] is not None:
                outcome = "invalid_execution"
                reasons.append("passed call carried an exception")
            elif observation.returncode == 0 and exit_payload.get("code") == 0:
                outcome = "survived"
                reasons.append("mutated target passed its intended killer")
            else:
                outcome = "invalid_execution"
                reasons.append("surviving call contradicts process exit status")
        elif phase_outcomes != ("passed", "failed", "passed"):
            outcome = "invalid_execution"
            reasons.append("failure did not occur solely in the intended call phase")
        elif (
            observation.returncode != 1
            or exit_payload.get("code") != 1
            or exit_payload.get("name") != "TESTS_FAILED"
        ):
            outcome = "invalid_execution"
            reasons.append("call failure contradicts parent or child exit status")
        else:
            try:
                _exception_matches(
                    call["exception"],
                    longrepr=call["longrepr"],
                    spec=spec,
                )
            except MutationAssuranceError as exc:
                outcome = "wrong_killer"
                reasons.append(str(exc))
            else:
                outcome = "killed_intended"
                reasons = []
                test_relative, test_module_name, test_qualname = (
                    _intended_test_coordinates(spec.intended_killer_nodeid)
                )
                trace = _object(report["trace"], label="credited child trace")
                actual_killer = {
                    "nodeid": spec.intended_killer_nodeid,
                    "phase": "call",
                    "claim_id": spec.expected_claim_id,
                    "contract_sha256": spec.expected_contract_sha256,
                    "test_source_relative_path": test_relative,
                    "test_module_name": test_module_name,
                    "test_qualname": test_qualname,
                    "test_code_sha256": trace[
                        "resolved_intended_test_code_sha256"
                    ],
                    "exception": call["exception"],
                }

    return seal_adjudication_record({
        "fault_archetype": spec.fault_archetype,
        "mutant_id": spec.mutant_id,
        "criticality": spec.criticality,
        "expected_killing_test_claim": {
            "nodeid": spec.intended_killer_nodeid,
            "claim_id": spec.expected_claim_id,
            "contract_sha256": spec.expected_contract_sha256,
        },
        "actual_killing_test": actual_killer,
        "evidence_class": spec.evidence_class,
        "outcome": outcome,
        "gate_credit": outcome == "killed_intended",
        "reasons": reasons,
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
            "runtime_source_sha256": (
                source_identity["runtime_source_sha256"]
                if source_identity is not None
                else None
            ),
        },
        "intended_test_source": intended_test_source,
        "process": process_observation_payload(observation),
        "child_report": report,
        "exclusions": list(spec.exclusions),
    })


_RECEIPT_DATA_FILES = (
    "baselines.json",
    "catalogue.json",
    "claim.json",
    "mutants.json",
    "run.json",
    "snapshot.json",
)
_RECEIPT_FILES = frozenset((*_RECEIPT_DATA_FILES, "COMPLETE"))
_UNCOMMITTED_RECEIPT_FILES = frozenset(_RECEIPT_DATA_FILES)
_FORBIDDEN_RECEIPT_ANCESTOR_PREFIXES = (
    ".incomplete-",
    ".revoked-",
    ".invalidated-",
)

_BASELINE_RESULT_FIELDS = {
    "execution_id",
    "mutant_id",
    "outcome",
    "gate_credit",
    "reasons",
    "source_identity",
    "intended_test_source",
    "process",
    "child_report",
    "adjudication_sha256",
}
_MUTANT_RESULT_FIELDS = {
    "fault_archetype",
    "mutant_id",
    "criticality",
    "expected_killing_test_claim",
    "actual_killing_test",
    "evidence_class",
    "outcome",
    "gate_credit",
    "reasons",
    "source_mutation",
    "intended_test_source",
    "process",
    "child_report",
    "exclusions",
    "adjudication_sha256",
}
_PROCESS_FIELDS = {
    "argv",
    "returncode",
    "timed_out",
    "duration_ns",
    "stdout",
    "stderr",
    "stdout_sha256",
    "stderr_sha256",
    "output_truncated",
    "report_sha256",
    "report_error",
    "observed_child_report",
}


def _snapshot_inputs_from_payload(value: object) -> SnapshotInputs:
    payload = _object(value, label="mutation snapshot")
    _exact_fields(
        payload,
        {
            "schema_version",
            "manifest_sha256",
            "native_backend_path",
            "git_executable",
            "untracked_exclude_policy",
            "deleted_tracked",
            "files",
        },
        label="mutation snapshot",
    )
    if payload["schema_version"] != 3:
        raise MutationAssuranceError("mutation snapshot schema is unsupported")
    git_executable = _git_executable_from_payload(payload["git_executable"])
    untracked_exclude_policy = _text_tuple(
        payload["untracked_exclude_policy"],
        label="mutation snapshot untracked exclude policy",
    )
    if untracked_exclude_policy != _SNAPSHOT_UNTRACKED_EXCLUDE_POLICY:
        raise MutationAssuranceError(
            "mutation snapshot untracked exclude policy is unsupported"
        )
    native_path = _safe_relative_path(
        payload["native_backend_path"],
        label="mutation snapshot native backend",
    )
    deleted = tuple(
        _safe_relative_path(item, label="mutation snapshot deleted path")
        for item in _list(payload["deleted_tracked"], label="mutation snapshot deleted")
    )
    if deleted != tuple(sorted(set(deleted))):
        raise MutationAssuranceError("mutation snapshot deleted paths are not sorted")
    identities: list[FileIdentity] = []
    for index, raw_identity in enumerate(
        _list(payload["files"], label="mutation snapshot files")
    ):
        identity = _object(raw_identity, label=f"mutation snapshot files[{index}]")
        _exact_fields(
            identity,
            {"path", "bytes", "sha256"},
            label=f"mutation snapshot files[{index}]",
        )
        relative = _safe_relative_path(
            identity["path"],
            label=f"mutation snapshot files[{index}].path",
        )
        byte_count = identity["bytes"]
        if isinstance(byte_count, bool) or not isinstance(byte_count, int) or byte_count < 0:
            raise MutationAssuranceError("mutation snapshot byte count is invalid")
        identities.append(
            FileIdentity(
                path=relative,
                bytes=byte_count,
                sha256=_sha256(
                    identity["sha256"],
                    label=f"mutation snapshot files[{index}].sha256",
                ),
            )
        )
    files = tuple(identities)
    paths = tuple(item.path for item in files)
    if paths != tuple(sorted(set(paths))):
        raise MutationAssuranceError("mutation snapshot files are not unique and sorted")
    if native_path not in paths:
        raise MutationAssuranceError("mutation snapshot omits its native backend")
    expected_manifest = _snapshot_manifest_sha256(
        files,
        deleted_tracked=deleted,
        native_backend_path=native_path,
        git_executable=git_executable,
        untracked_exclude_policy=untracked_exclude_policy,
    )
    if payload["manifest_sha256"] != expected_manifest:
        raise MutationAssuranceError("mutation snapshot manifest digest is invalid")
    return SnapshotInputs(
        files=files,
        deleted_tracked=deleted,
        native_backend_path=native_path,
        git_executable=git_executable,
        untracked_exclude_policy=untracked_exclude_policy,
        manifest_sha256=expected_manifest,
    )


def _adjudication_digest_is_valid(
    value: Mapping[str, object],
    *,
    label: str,
) -> None:
    supplied = _sha256(
        value.get("adjudication_sha256"),
        label=f"{label}.adjudication_sha256",
    )
    unsigned = dict(value)
    unsigned.pop("adjudication_sha256", None)
    if supplied != sha256_bytes(canonical_json_bytes(unsigned)):
        raise MutationAssuranceError(f"{label} adjudication digest is invalid")


def _embedded_file_identity(
    value: object,
    *,
    expected_sha256: str,
    expected_bytes: int,
    label: str,
) -> dict[str, object]:
    identity = _object(value, label=label)
    _exact_fields(
        identity,
        {"path", "path_truncated", "bytes", "sha256"},
        label=label,
    )
    if identity["path_truncated"] is not False:
        raise MutationAssuranceError(f"{label} path is truncated")
    if not isinstance(identity["path"], str) or not identity["path"]:
        raise MutationAssuranceError(f"{label} path is invalid")
    byte_count = identity["bytes"]
    if byte_count != expected_bytes:
        raise MutationAssuranceError(f"{label} byte count is wrong")
    if identity["sha256"] != expected_sha256:
        raise MutationAssuranceError(f"{label} digest is wrong")
    return identity


def _embedded_module_identity(
    modules: Mapping[str, object],
    *,
    role: str,
    expected_name: str,
    expected_sha256: str,
    expected_bytes: int,
    expected_loader: str,
    expected_loader_policy: str,
) -> dict[str, object]:
    module = _object(modules.get(role), label=f"embedded module {role}")
    _exact_fields(
        module,
        {
            "available",
            "name",
            "name_truncated",
            "file",
            "file_error",
            "file_error_truncated",
            "spec",
        },
        label=f"embedded module {role}",
    )
    if (
        module["available"] is not True
        or module["name"] != expected_name
        or module["name_truncated"] is not False
        or module["file_error"] is not None
        or module["file_error_truncated"] is not False
    ):
        raise MutationAssuranceError(f"embedded module {role} identity is invalid")
    file_identity = _embedded_file_identity(
        module["file"],
        expected_sha256=expected_sha256,
        expected_bytes=expected_bytes,
        label=f"embedded module {role} file",
    )
    specification = _object(module["spec"], label=f"embedded module {role} spec")
    _exact_fields(
        specification,
        {
            "name",
            "name_truncated",
            "origin",
            "origin_truncated",
            "loader",
            "loader_truncated",
            "loader_policy",
        },
        label=f"embedded module {role} spec",
    )
    if (
        specification["name"] != expected_name
        or specification["name_truncated"] is not False
        or specification["origin"] != file_identity["path"]
        or specification["origin_truncated"] is not False
        or specification["loader"] != expected_loader
        or specification["loader_truncated"] is not False
        or specification["loader_policy"] != expected_loader_policy
    ):
        raise MutationAssuranceError(f"embedded module {role} spec is invalid")
    return file_identity


def _embedded_intended_test_callable(
    value: object,
    *,
    expected_module: str,
    expected_qualname: str,
    expected_path: PurePosixPath | PureWindowsPath,
    expected_code_sha256: str,
) -> dict[str, object]:
    identity = _object(value, label="embedded intended-test callable")
    _exact_fields(
        identity,
        {
            "available",
            "type",
            "module",
            "name",
            "qualname",
            "module_binding_exact",
            "wrapped",
            "code",
            "stable_during_execution",
        },
        label="embedded intended-test callable",
    )
    if (
        identity["available"] is not True
        or identity["type"] != "builtins.function"
        or identity["module"] != expected_module
        or identity["name"] != expected_qualname
        or identity["qualname"] != expected_qualname
        or identity["module_binding_exact"] is not True
        or identity["wrapped"] is not False
        or identity["stable_during_execution"] is not True
    ):
        raise MutationAssuranceError(
            "embedded intended-test callable binding is invalid"
        )
    code = _object(identity["code"], label="embedded intended-test callable code")
    _exact_fields(
        code,
        {
            "algorithm",
            "filename",
            "filename_truncated",
            "qualname",
            "sha256",
        },
        label="embedded intended-test callable code",
    )
    if (
        code["algorithm"] != INTENDED_TEST_CODE_DIGEST_ALGORITHM
        or code["filename_truncated"] is not False
        or code["qualname"] != expected_qualname
        or code["sha256"] != expected_code_sha256
        or _pure_receipt_path(
            code["filename"],
            label="embedded intended-test callable filename",
        )
        != expected_path
    ):
        raise MutationAssuranceError(
            "embedded intended-test callable code is invalid"
        )
    return identity


def _snapshot_identity(inputs: SnapshotInputs, relative: str) -> FileIdentity:
    identity = inputs.by_path.get(relative)
    if identity is None:
        raise MutationAssuranceError(
            f"mutation snapshot omits required receipt input {relative}"
        )
    return identity


def _validate_intended_test_source_receipt(
    value: object,
    *,
    spec: MutantSpec,
    snapshot: SnapshotInputs,
) -> dict[str, object]:
    identity = _object(value, label="intended test source receipt")
    _exact_fields(
        identity,
        {
            "schema_version",
            "source_path",
            "module_name",
            "qualname",
            "source_bytes",
            "source_sha256",
            "source_base64",
            "rewrite_policy",
            "code_algorithm",
            "code_sha256",
        },
        label="intended test source receipt",
    )
    relative, module_name, qualname = _intended_test_coordinates(
        spec.intended_killer_nodeid
    )
    expected_source = _snapshot_identity(snapshot, relative)
    byte_count = identity["source_bytes"]
    if (
        identity["schema_version"] != 1
        or identity["source_path"] != relative
        or identity["module_name"] != module_name
        or identity["qualname"] != qualname
        or isinstance(byte_count, bool)
        or byte_count != expected_source.bytes
        or identity["source_sha256"] != expected_source.sha256
        or identity["rewrite_policy"]
        != "pytest_assertion_rewrite_disabled"
        or identity["code_algorithm"]
        != INTENDED_TEST_CODE_DIGEST_ALGORITHM
    ):
        raise MutationAssuranceError("intended test source receipt is inconsistent")
    _sha256(identity["code_sha256"], label="intended test code digest")
    encoded = identity["source_base64"]
    if not isinstance(encoded, str):
        raise MutationAssuranceError("intended test source bytes are malformed")
    try:
        source = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise MutationAssuranceError(
            "intended test source bytes are not canonical base64"
        ) from exc
    if (
        len(source) != expected_source.bytes
        or len(source) > _MAX_MUTATION_SOURCE_BYTES
        or base64.b64encode(source).decode("ascii") != encoded
        or sha256_bytes(source) != expected_source.sha256
    ):
        raise MutationAssuranceError("intended test source bytes are wrong")
    derived = pytest_rewritten_source_code_sha256(
        source,
        qualname=qualname,
        filename=relative,
    )
    if identity["code_sha256"] != derived:
        raise MutationAssuranceError(
            "intended test code digest is not derived from its source"
        )
    return identity


def _validate_embedded_child_evidence(
    *,
    spec: MutantSpec,
    process_value: object,
    child_value: object,
    execution_id: str,
    expected_returncode: int,
    expected_phase_outcomes: tuple[str, str, str],
    runtime_source_sha256: str,
    runtime_source_bytes: int,
    expected_code_sha256: str,
    expected_test_code_sha256: str,
    snapshot: SnapshotInputs,
    interpreter: Mapping[str, object],
) -> tuple[dict[str, object], ...]:
    process = _object(process_value, label="adjudication process")
    _exact_fields(process, _PROCESS_FIELDS, label="adjudication process")
    argv = _list(process["argv"], label="adjudication process argv")
    if not argv or not all(isinstance(value, str) and value for value in argv):
        raise MutationAssuranceError("adjudication process argv is invalid")
    if process["returncode"] != expected_returncode:
        raise MutationAssuranceError("adjudication process return code is wrong")
    duration = process["duration_ns"]
    if (
        process["timed_out"] is not False
        or process["output_truncated"] is not False
        or isinstance(duration, bool)
        or not isinstance(duration, int)
        or duration < 0
        or process["report_error"] is not None
    ):
        raise MutationAssuranceError("adjudication process is not an admitted execution")
    stdout = process["stdout"]
    stderr = process["stderr"]
    if not isinstance(stdout, str) or not isinstance(stderr, str):
        raise MutationAssuranceError("adjudication process output is malformed")
    if process["stdout_sha256"] != sha256_bytes(stdout.encode("utf-8")):
        raise MutationAssuranceError("adjudication stdout digest is inconsistent")
    if process["stderr_sha256"] != sha256_bytes(stderr.encode("utf-8")):
        raise MutationAssuranceError("adjudication stderr digest is inconsistent")

    child = _object(child_value, label="admitted child report")
    if process["observed_child_report"] != child:
        raise MutationAssuranceError("admitted and observed child reports differ")
    if process["report_sha256"] != sha256_bytes(pretty_json_bytes(child)):
        raise MutationAssuranceError("adjudication child report digest is inconsistent")
    _exact_fields(
        child,
        {
            "schema_version",
            "execution_id",
            "intended",
            "selection",
            "errors",
            "reports",
            "trace",
            "identity",
            "pytest",
        },
        label="admitted child report",
    )
    if child["schema_version"] != CHILD_REPORT_SCHEMA_VERSION:
        raise MutationAssuranceError("admitted child report schema is unsupported")
    if child["execution_id"] != execution_id:
        raise MutationAssuranceError("admitted child execution ID is wrong")
    _reject_truncation(child, label="admitted child report")
    test_relative, test_module_name, test_qualname = (
        _intended_test_coordinates(spec.intended_killer_nodeid)
    )
    if child["intended"] != {
        "nodeid": spec.intended_killer_nodeid,
        "source_relative_path": spec.source_path,
        "module_name": spec.module_name,
        "target_qualname": spec.target_qualname,
        "test_source_relative_path": test_relative,
        "test_module_name": test_module_name,
        "test_qualname": test_qualname,
    }:
        raise MutationAssuranceError("admitted child intended identity is wrong")
    selection = _object(child["selection"], label="admitted child selection")
    _exact_fields(
        selection,
        {
            "selected_nodeids",
            "selected_count",
            "intended_selected_count",
            "only_intended_selected",
        },
        label="admitted child selection",
    )
    if (
        selection["selected_nodeids"]
        != [{"nodeid": spec.intended_killer_nodeid, "truncated": False}]
        or selection["selected_count"] != 1
        or selection["intended_selected_count"] != 1
        or selection["only_intended_selected"] is not True
    ):
        raise MutationAssuranceError("admitted child selection is not exact")
    errors = _object(child["errors"], label="admitted child errors")
    if set(errors) != {"collection", "internal"} or errors != {
        "collection": [],
        "internal": [],
    }:
        raise MutationAssuranceError("admitted child contains collection/internal errors")

    raw_phases = _list(child["reports"], label="admitted child phases")
    if len(raw_phases) != 3:
        raise MutationAssuranceError("admitted child phase count is wrong")
    phases: list[dict[str, object]] = []
    expected_phase_names = ("setup", "call", "teardown")
    phase_fields = {
        "sequence",
        "nodeid",
        "nodeid_truncated",
        "phase",
        "outcome",
        "outcome_truncated",
        "duration_s",
        "wasxfail",
        "wasxfail_truncated",
        "exception",
        "evidence_user_properties",
        "longrepr",
        "longrepr_truncated",
        "rerun",
        "rerun_index",
    }
    for index, raw_phase in enumerate(raw_phases):
        phase = _object(raw_phase, label=f"admitted child phase[{index}]")
        _exact_fields(phase, phase_fields, label=f"admitted child phase[{index}]")
        duration_s = phase["duration_s"]
        if (
            phase["sequence"] != index + 1
            or phase["nodeid"] != spec.intended_killer_nodeid
            or phase["nodeid_truncated"] is not False
            or phase["phase"] != expected_phase_names[index]
            or phase["outcome"] != expected_phase_outcomes[index]
            or phase["outcome_truncated"] is not False
            or isinstance(duration_s, bool)
            or not isinstance(duration_s, (int, float))
            or not math.isfinite(float(duration_s))
            or float(duration_s) < 0
            or phase["wasxfail"] is not None
            or phase["wasxfail_truncated"] is not False
            or phase["longrepr_truncated"] is not False
            or phase["rerun"] is not False
            or phase["rerun_index"] is not None
        ):
            raise MutationAssuranceError("admitted child phase evidence is invalid")
        _evidence_properties(phase, spec=spec)
        if phase["outcome"] == "passed" and phase["exception"] is not None:
            raise MutationAssuranceError(
                "admitted child passed phase carries an exception"
            )
        phases.append(phase)

    trace = _object(child["trace"], label="admitted child trace")
    _exact_fields(
        trace,
        {
            "algorithm",
            "attempted",
            "preexisting_tracer",
            "call_count",
            "frame_filenames",
            "code_sha256",
            "resolved_target_code_sha256",
            "target_binding_exact",
            "intended_test_call_count",
            "intended_test_frame_filenames",
            "intended_test_code_sha256",
            "resolved_intended_test_code_sha256",
        },
        label="admitted child trace",
    )
    filenames = trace["frame_filenames"]
    intended_test_code_sha256 = _sha256(
        trace["resolved_intended_test_code_sha256"],
        label="admitted intended-test code digest",
    )
    intended_test_filenames = trace["intended_test_frame_filenames"]
    if (
        trace["algorithm"] != "python_code_v1"
        or trace["attempted"] is not True
        or trace["preexisting_tracer"] is not False
        or isinstance(trace["call_count"], bool)
        or not isinstance(trace["call_count"], int)
        or trace["call_count"] < 1
        or trace["code_sha256"] != [expected_code_sha256]
        or trace["resolved_target_code_sha256"] != expected_code_sha256
        or trace["target_binding_exact"] is not True
        or trace["intended_test_call_count"] != 1
        or trace["intended_test_code_sha256"]
        != [intended_test_code_sha256]
        or intended_test_code_sha256 != expected_test_code_sha256
        or not isinstance(filenames, list)
        or len(filenames) != 1
        or not isinstance(filenames[0], str)
        or not isinstance(intended_test_filenames, list)
        or len(intended_test_filenames) != 1
        or not isinstance(intended_test_filenames[0], str)
    ):
        raise MutationAssuranceError("admitted child trace is invalid")

    identity = _object(child["identity"], label="admitted child identity")
    _exact_fields(
        identity,
        {
            "interpreter",
            "cwd",
            "cwd_truncated",
            "root",
            "root_truncated",
            "source",
            "modules",
            "intended_test_callable",
            "policy_environment",
            "network",
            "test_toolchain",
        },
        label="admitted child identity",
    )
    if identity["cwd"] != identity["root"]:
        raise MutationAssuranceError("admitted child cwd and root differ")
    _validate_child_toolchain_attestation(
        identity["test_toolchain"],
        interpreter=interpreter,
    )
    root_path = _pure_receipt_path(identity["root"], label="admitted child root")
    expected_source_path = root_path.joinpath(*PurePosixPath(spec.source_path).parts)
    expected_test_path = root_path.joinpath(*PurePosixPath(test_relative).parts)
    expected_test_source = _snapshot_identity(snapshot, test_relative)
    modules = _object(identity.get("modules"), label="admitted child modules")
    expected_module_roles = {
        "target_module",
        "intended_test",
        "moira",
        "reporter",
        "sitecustomize",
        "native_backend",
        "toolchain",
    }
    if set(modules) != expected_module_roles:
        raise MutationAssuranceError("admitted child module roles are not exact")
    source_file = _embedded_file_identity(
        identity.get("source"),
        expected_sha256=runtime_source_sha256,
        expected_bytes=runtime_source_bytes,
        label="admitted child source",
    )
    target_file = _embedded_module_identity(
        modules,
        role="target_module",
        expected_name=spec.module_name,
        expected_sha256=runtime_source_sha256,
        expected_bytes=runtime_source_bytes,
        expected_loader=_SOURCE_LOADER_NAME,
        expected_loader_policy="source",
    )
    if (
        target_file != source_file
        or filenames != [source_file["path"]]
        or _pure_receipt_path(
            source_file["path"], label="admitted child source path"
        )
        != expected_source_path
    ):
        raise MutationAssuranceError("admitted child source/module/trace paths differ")
    intended_test_file = _embedded_module_identity(
        modules,
        role="intended_test",
        expected_name=test_module_name,
        expected_sha256=expected_test_source.sha256,
        expected_bytes=expected_test_source.bytes,
        expected_loader=_PYTEST_REWRITE_LOADER_NAME,
        expected_loader_policy="pytest_assertion_rewrite_disabled",
    )
    if (
        _pure_receipt_path(
            intended_test_file["path"],
            label="admitted child intended-test path",
        )
        != expected_test_path
        or _pure_receipt_path(
            intended_test_filenames[0],
            label="admitted child intended-test trace path",
        )
        != expected_test_path
    ):
        raise MutationAssuranceError(
            "admitted child intended-test module/trace paths differ"
        )
    _embedded_intended_test_callable(
        identity["intended_test_callable"],
        expected_module=test_module_name,
        expected_qualname=test_qualname,
        expected_path=expected_test_path,
        expected_code_sha256=intended_test_code_sha256,
    )
    expected_modules = (
        (
            "moira",
            "moira",
            "moira/__init__.py",
            _SOURCE_LOADER_NAME,
            "source",
        ),
        (
            "reporter",
            "tests.mutation_reporter",
            "tests/mutation_reporter.py",
            _PYTEST_REWRITE_LOADER_NAME,
            "pytest_assertion_rewrite_disabled",
        ),
        (
            "sitecustomize",
            "sitecustomize",
            "tests/support/network_bootstrap/sitecustomize.py",
            _SOURCE_LOADER_NAME,
            "source",
        ),
        (
            "native_backend",
            "moira._moira_native",
            snapshot.native_backend_path,
            _EXTENSION_LOADER_NAME,
            "extension",
        ),
        (
            "toolchain",
            "support.mutation_toolchain",
            "tests/support/mutation_toolchain.py",
            _SOURCE_LOADER_NAME,
            "source",
        ),
    )
    for role, module_name, relative, loader, loader_policy in expected_modules:
        expected_identity = _snapshot_identity(snapshot, relative)
        module_file = _embedded_module_identity(
            modules,
            role=role,
            expected_name=module_name,
            expected_sha256=expected_identity.sha256,
            expected_bytes=expected_identity.bytes,
            expected_loader=loader,
            expected_loader_policy=loader_policy,
        )
        expected_path = root_path.joinpath(*PurePosixPath(relative).parts)
        if _pure_receipt_path(
            module_file["path"], label=f"admitted child {role} path"
        ) != expected_path:
            raise MutationAssuranceError(f"admitted child {role} path is foreign")

    child_interpreter = _object(
        identity.get("interpreter"), label="admitted child interpreter"
    )
    _exact_fields(
        child_interpreter,
        {
            "executable",
            "implementation",
            "version",
            "cache_tag",
            "pycache_prefix",
            "prefix",
            "base_prefix",
            "flags",
        },
        label="admitted child interpreter",
    )
    expected_implementation, expected_version, expected_cache_tag = (
        _expected_child_interpreter_runtime(interpreter)
    )
    if (
        child_interpreter["implementation"] != expected_implementation
        or child_interpreter["version"] != expected_version
        or child_interpreter["cache_tag"] != expected_cache_tag
    ):
        raise MutationAssuranceError(
            "admitted child interpreter runtime identity is wrong"
        )
    expected_pycache = root_path.parent / "control" / f"pycache-{execution_id}"
    if _pure_receipt_path(
        child_interpreter["pycache_prefix"],
        label="admitted child pycache prefix",
    ) != expected_pycache:
        raise MutationAssuranceError(
            "admitted child interpreter pycache prefix is foreign"
        )
    executable = _embedded_file_identity(
        child_interpreter.get("executable"),
        expected_sha256=str(interpreter["sha256"]),
        expected_bytes=int(interpreter["bytes"]),
        label="admitted child interpreter executable",
    )
    if executable["path"] != interpreter["executable_resolved"]:
        raise MutationAssuranceError("admitted child interpreter path is wrong")
    if (
        child_interpreter.get("prefix") != interpreter["prefix"]
        or child_interpreter.get("base_prefix") != interpreter["base_prefix"]
    ):
        raise MutationAssuranceError("admitted child interpreter prefixes are wrong")
    flags = _object(child_interpreter.get("flags"), label="admitted child flags")
    _exact_fields(
        flags,
        {"safe_path", "optimize", "dont_write_bytecode", "no_user_site"},
        label="admitted child flags",
    )
    if (
        flags.get("safe_path") is not True
        or flags.get("optimize") != 0
        or flags.get("dont_write_bytecode") is not True
        or flags.get("no_user_site") is not True
    ):
        raise MutationAssuranceError("admitted child interpreter flags are wrong")
    _validate_child_argv(
        argv,
        spec=spec,
        execution_id=execution_id,
        snapshot_root=identity["root"],
        interpreter=str(interpreter["executable"]),
    )

    # Reuse the live adjudicator's exact environment and network semantics by
    # validating them through a report-shaped copy with no filesystem access.
    policy_environment = _object(
        identity.get("policy_environment"),
        label="admitted child policy environment",
    )
    expected_environment = {
        "MOIRA_TEST_MODE": "1",
        "MOIRA_NO_DOWNLOAD": "1",
        "MOIRA_STRICT_KNOWN_ISSUES": "1",
        "MOIRA_TEST_NETWORK_POLICY": "deny",
        "MOIRA_TEST_ARTIFACTS": "0",
        "MOIRA_TEST_SEED": None,
        "MOIRA_TEST_BUDGET_TOTAL_S": "0",
        "MOIRA_TEST_BUDGET_CASE_S": "0",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
        "PYTHONNOUSERSITE": "1",
        "PYTHONOPTIMIZE": "0",
    }
    if set(policy_environment) != set(expected_environment):
        raise MutationAssuranceError("admitted child environment fields are wrong")
    for name, expected in expected_environment.items():
        entry = _object(policy_environment[name], label=f"admitted child env {name}")
        if set(entry) != {"value", "truncated"} or entry["truncated"] is not False:
            raise MutationAssuranceError("admitted child environment entry is invalid")
        if name == "MOIRA_TEST_SEED":
            expected_seed = str(deterministic_mutation_seed(spec.mutant_id))
            if entry["value"] != expected_seed:
                raise MutationAssuranceError(
                    "admitted child seed is not deterministically derived"
                )
        elif entry["value"] != expected:
            raise MutationAssuranceError(f"admitted child environment {name} is wrong")
    network = _object(identity.get("network"), label="admitted child network")
    _exact_fields(
        network,
        {
            "available",
            "audit_hook_installed",
            "audit_canary_seen",
            "socket_method_guards_installed",
            "asyncio_method_guards_installed",
            "active_mode",
            "active_nodeid",
            "active_nodeid_truncated",
            "environment_mode",
        },
        label="admitted child network",
    )
    if (
        network.get("available") is not True
        or network.get("audit_hook_installed") is not True
        or network.get("audit_canary_seen") is not True
        or network.get("socket_method_guards_installed") is not True
        or network.get("asyncio_method_guards_installed") is not True
        or network.get("active_mode") != "deny"
        or network.get("environment_mode") != "deny"
        or network.get("active_nodeid") != "<session-finish>"
        or network.get("active_nodeid_truncated") is not False
    ):
        raise MutationAssuranceError("admitted child network policy is wrong")

    pytest_payload = _object(child["pytest"], label="admitted child pytest")
    if set(pytest_payload) != {"exitstatus"}:
        raise MutationAssuranceError("admitted child pytest fields are wrong")
    exitstatus = _object(pytest_payload["exitstatus"], label="admitted child exit")
    expected_exit = {
        "code": expected_returncode,
        "name": "OK" if expected_returncode == 0 else "TESTS_FAILED",
    }
    if exitstatus != expected_exit:
        raise MutationAssuranceError("admitted child exit status is wrong")
    return tuple(phases)


def _plain_directory(path: Path, *, label: str) -> None:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise MutationAssuranceError(f"{label} is unavailable: {path}: {exc}") from exc
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or stat.S_ISLNK(metadata.st_mode)
        or _is_reparse(metadata)
    ):
        raise MutationAssuranceError(f"{label} is not a plain directory: {path}")


def _validate_interpreter_receipt(value: object) -> dict[str, object]:
    interpreter = _object(value, label="mutation parent interpreter")
    _exact_fields(
        interpreter,
        {
            "schema_version",
            "executable",
            "executable_resolved",
            "sha256",
            "bytes",
            "prefix",
            "base_prefix",
            "implementation",
            "version",
            "launcher",
            "runtime",
            "test_toolchain",
            "loaded_test_toolchain",
        },
        label="mutation parent interpreter",
    )
    if interpreter["schema_version"] != INTERPRETER_IDENTITY_SCHEMA_VERSION:
        raise MutationAssuranceError(
            "mutation parent interpreter schema is unsupported"
        )
    if not all(
        isinstance(interpreter[key], str) and interpreter[key]
        for key in (
            "executable",
            "executable_resolved",
            "prefix",
            "base_prefix",
            "implementation",
        )
    ):
        raise MutationAssuranceError("mutation parent interpreter paths are invalid")
    for key in ("executable", "executable_resolved", "prefix", "base_prefix"):
        _pure_receipt_path(
            interpreter[key],
            label=f"mutation parent interpreter {key}",
        )
    _sha256(interpreter["sha256"], label="mutation parent interpreter sha256")
    byte_count = interpreter["bytes"]
    version = interpreter["version"]
    if (
        isinstance(byte_count, bool)
        or not isinstance(byte_count, int)
        or byte_count <= 0
        or not isinstance(version, list)
        or len(version) != 3
        or not all(isinstance(item, int) and not isinstance(item, bool) for item in version)
    ):
        raise MutationAssuranceError("mutation parent interpreter identity is invalid")
    launcher = _object(
        interpreter["launcher"],
        label="mutation parent interpreter launcher",
    )
    _exact_fields(
        launcher,
        {
            "schema_version",
            "path",
            "resolved_path",
            "directory_resolved",
            "symlinks",
        },
        label="mutation parent interpreter launcher",
    )
    if (
        launcher["schema_version"] != 1
        or launcher["path"] != interpreter["executable"]
        or launcher["resolved_path"] != interpreter["executable_resolved"]
        or not isinstance(launcher["directory_resolved"], str)
        or not launcher["directory_resolved"]
    ):
        raise MutationAssuranceError(
            "mutation parent interpreter launcher is inconsistent"
        )
    _pure_receipt_path(
        launcher["directory_resolved"],
        label="mutation parent interpreter launcher directory",
    )
    symlinks = _list(
        launcher["symlinks"],
        label="mutation parent interpreter launcher symlinks",
    )
    link_paths: list[str] = []
    for index, raw_link in enumerate(symlinks):
        link = _object(
            raw_link,
            label=f"mutation parent interpreter launcher symlinks[{index}]",
        )
        _exact_fields(
            link,
            {"path", "target"},
            label=f"mutation parent interpreter launcher symlinks[{index}]",
        )
        if (
            not isinstance(link["path"], str)
            or not link["path"]
            or not isinstance(link["target"], str)
            or not link["target"]
            or "\x00" in link["target"]
        ):
            raise MutationAssuranceError(
                "mutation parent interpreter launcher symlink is invalid"
            )
        _pure_receipt_path(
            link["path"],
            label=f"mutation parent interpreter launcher symlinks[{index}].path",
        )
        link_paths.append(link["path"])
    if len(link_paths) != len(set(link_paths)):
        raise MutationAssuranceError(
            "mutation parent interpreter launcher symlinks are duplicated"
        )

    runtime = _object(
        interpreter["runtime"],
        label="mutation parent interpreter runtime",
    )
    _exact_fields(
        runtime,
        {
            "schema_version",
            "scope",
            "roots",
            "file_count",
            "bytes",
            "manifest_sha256",
        },
        label="mutation parent interpreter runtime",
    )
    if (
        runtime["schema_version"] != 1
        or runtime["scope"] != _RUNTIME_IDENTITY_SCOPE
        or isinstance(runtime["file_count"], bool)
        or not isinstance(runtime["file_count"], int)
        or runtime["file_count"] <= 0
        or runtime["file_count"] > _MAX_RUNTIME_FILES
        or isinstance(runtime["bytes"], bool)
        or not isinstance(runtime["bytes"], int)
        or runtime["bytes"] <= 0
        or runtime["bytes"] > _MAX_RUNTIME_TOTAL_BYTES
    ):
        raise MutationAssuranceError(
            "mutation parent interpreter runtime identity is invalid"
        )
    _sha256(
        runtime["manifest_sha256"],
        label="mutation parent interpreter runtime manifest",
    )
    runtime_roots = _object(
        runtime["roots"],
        label="mutation parent interpreter runtime roots",
    )
    _exact_fields(
        runtime_roots,
        {
            "venv_config",
            "base_executable",
            "stdlib",
            "auxiliary_trees",
            "core_files",
            "startup_import_path",
            "startup_control_files",
        },
        label="mutation parent interpreter runtime roots",
    )
    for key in ("venv_config", "base_executable", "stdlib"):
        _pure_receipt_path(
            runtime_roots[key],
            label=f"mutation parent interpreter runtime roots {key}",
        )
    for key in ("auxiliary_trees", "core_files"):
        paths = _list(
            runtime_roots[key],
            label=f"mutation parent interpreter runtime roots {key}",
        )
        checked_paths: list[str] = []
        for index, path in enumerate(paths):
            if not isinstance(path, str) or not path:
                raise MutationAssuranceError(
                    "mutation parent interpreter runtime path is invalid"
                )
            _pure_receipt_path(
                path,
                label=(
                    f"mutation parent interpreter runtime roots {key}[{index}]"
                ),
            )
            checked_paths.append(path)
        if checked_paths != sorted(set(checked_paths)):
            raise MutationAssuranceError(
                "mutation parent interpreter runtime paths are not sorted and unique"
            )
    startup_entries = _list(
        runtime_roots["startup_import_path"],
        label="mutation parent interpreter runtime startup import path",
    )
    if not startup_entries:
        raise MutationAssuranceError(
            "mutation parent interpreter runtime startup import path is empty"
        )
    startup_paths: list[str] = []
    for index, raw_entry in enumerate(startup_entries):
        entry = _object(
            raw_entry,
            label=f"mutation parent interpreter startup import path[{index}]",
        )
        _exact_fields(
            entry,
            {"index", "path", "resolved", "state", "scope"},
            label=f"mutation parent interpreter startup import path[{index}]",
        )
        if entry["index"] != index:
            raise MutationAssuranceError(
                "mutation parent interpreter startup import indexes are invalid"
            )
        if not isinstance(entry["path"], str) or not entry["path"]:
            raise MutationAssuranceError(
                "mutation parent interpreter startup import path is invalid"
            )
        _pure_receipt_path(
            entry["path"],
            label=f"mutation parent interpreter startup import path[{index}].path",
        )
        state = entry["state"]
        scope = entry["scope"]
        if state == "missing":
            if entry["resolved"] is not None or scope != "missing_stdlib_archive":
                raise MutationAssuranceError(
                    "mutation parent interpreter missing import path is invalid"
                )
        else:
            if state not in {"archive", "directory"}:
                raise MutationAssuranceError(
                    "mutation parent interpreter startup import state is invalid"
                )
            if scope not in {
                "runtime_archive",
                "runtime_tree",
                "toolchain_site_packages",
            }:
                raise MutationAssuranceError(
                    "mutation parent interpreter startup import scope is invalid"
                )
            if not isinstance(entry["resolved"], str) or not entry["resolved"]:
                raise MutationAssuranceError(
                    "mutation parent interpreter startup resolved path is invalid"
                )
            _pure_receipt_path(
                entry["resolved"],
                label=(
                    f"mutation parent interpreter startup import path[{index}].resolved"
                ),
            )
        startup_paths.append(entry["path"])
    if len(startup_paths) != len(set(startup_paths)):
        raise MutationAssuranceError(
            "mutation parent interpreter startup import paths are duplicated"
        )
    control_entries = _list(
        runtime_roots["startup_control_files"],
        label="mutation parent interpreter startup control files",
    )
    control_paths: list[str] = []
    for index, raw_entry in enumerate(control_entries):
        entry = _object(
            raw_entry,
            label=f"mutation parent interpreter startup control files[{index}]",
        )
        _exact_fields(
            entry,
            {"path", "state"},
            label=f"mutation parent interpreter startup control files[{index}]",
        )
        if (
            not isinstance(entry["path"], str)
            or not entry["path"]
            or entry["state"] not in {"file", "missing"}
        ):
            raise MutationAssuranceError(
                "mutation parent interpreter startup control file is invalid"
            )
        _pure_receipt_path(
            entry["path"],
            label=f"mutation parent interpreter startup control files[{index}].path",
        )
        control_paths.append(entry["path"])
    if control_paths != sorted(set(control_paths)):
        raise MutationAssuranceError(
            "mutation parent interpreter startup control files are not sorted"
        )
    try:
        from support.mutation_toolchain import validate_test_toolchain_identity

        toolchain = validate_test_toolchain_identity(interpreter["test_toolchain"])
    except Exception as exc:
        raise MutationAssuranceError(
            f"mutation parent test toolchain identity is invalid: {exc}"
        ) from exc
    loaded = _object(
        interpreter["loaded_test_toolchain"],
        label="mutation parent loaded test toolchain",
    )
    expected_code_object_count = sum(
        int(module["code_manifest"]["object_count"])
        for module in toolchain["modules"]
        if module["loader_kind"] == "source"
    )
    _exact_fields(
        loaded,
        {
            "schema_version",
            "manifest_sha256",
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
        },
        label="mutation parent loaded test toolchain",
    )
    _validate_normalized_lru_wrapper_attestation(
        loaded,
        label="mutation parent loaded test toolchain",
    )
    if (
        loaded["schema_version"] != toolchain["schema_version"]
        or loaded["manifest_sha256"] != toolchain["manifest_sha256"]
        or loaded["module_manifest_sha256"]
        != toolchain["module_manifest_sha256"]
        or loaded["code_manifest_sha256"]
        != toolchain["code_manifest_sha256"]
        or loaded["module_count"] != len(toolchain["modules"])
        or isinstance(loaded["code_object_count"], bool)
        or not isinstance(loaded["code_object_count"], int)
        or loaded["code_object_count"] != expected_code_object_count
        or loaded["all_modules_match"] is not True
        or loaded["all_captured_modules_match"] is not True
    ):
        raise MutationAssuranceError(
            "mutation parent loaded test toolchain is inconsistent"
        )
    return interpreter


def _validate_native_build_receipt(
    value: object,
    *,
    catalogue: MutationCatalogue,
    snapshot: SnapshotInputs,
) -> dict[str, object] | None:
    required = [
        spec.mutant_id for spec in catalogue.mutants if spec.requires_native_backend
    ]
    for spec in catalogue.mutants:
        if spec.evidence_class == "native_parity" and not spec.requires_native_backend:
            raise MutationAssuranceError(
                "native-parity catalogue entry does not require the native backend"
            )
    if not required:
        if value is not None:
            raise MutationAssuranceError(
                "mutation run carries unnecessary native-build admission"
            )
        return None
    payload = _object(value, label="mutation native build")
    _exact_fields(
        payload,
        {
            "schema_version",
            "required_mutant_ids",
            "backend_path",
            "backend_bytes",
            "backend_sha256",
            "embedded_input_sha256",
            "build_input_manifest_sha256",
            "build_input_count",
            "matches_current_inputs",
        },
        label="mutation native build",
    )
    backend = _snapshot_identity(snapshot, snapshot.native_backend_path)
    if (
        payload["schema_version"] != 1
        or payload["required_mutant_ids"] != required
        or payload["backend_path"] != snapshot.native_backend_path
        or payload["backend_bytes"] != backend.bytes
        or payload["backend_sha256"] != backend.sha256
        or payload["matches_current_inputs"] is not True
        or isinstance(payload["build_input_count"], bool)
        or not isinstance(payload["build_input_count"], int)
        or payload["build_input_count"] <= 0
    ):
        raise MutationAssuranceError("mutation native-build identity is inconsistent")
    embedded = _sha256(
        payload["embedded_input_sha256"],
        label="mutation native embedded input sha256",
    )
    manifest = _sha256(
        payload["build_input_manifest_sha256"],
        label="mutation native build manifest sha256",
    )
    if embedded != manifest:
        raise MutationAssuranceError(
            "mutation native backend is stale for its build inputs"
        )
    return payload


def _validate_parent_runtime_receipt(
    value: object,
    *,
    snapshot: SnapshotInputs,
) -> dict[str, object]:
    parent = _object(value, label="mutation parent runtime")
    _exact_fields(
        parent,
        {"module_import_policy", "modules"},
        label="mutation parent runtime",
    )
    if parent["module_import_policy"] != (
        "frozen_stage_one_no_preload_isolated_empty_pycache_no_write"
    ):
        raise MutationAssuranceError("mutation parent import policy is not admitted")
    expected = (
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
    )
    raw_modules = _list(parent["modules"], label="mutation parent modules")
    if len(raw_modules) != len(expected):
        raise MutationAssuranceError("mutation parent module count is wrong")
    for index, (raw_module, expected_values) in enumerate(zip(raw_modules, expected)):
        module = _object(raw_module, label=f"mutation parent modules[{index}]")
        _exact_fields(
            module,
            {"role", "module_name", "path", "bytes", "sha256"},
            label=f"mutation parent modules[{index}]",
        )
        role, module_name, relative = expected_values
        source_identity = _snapshot_identity(snapshot, relative)
        if module != {
            "role": role,
            "module_name": module_name,
            "path": relative,
            "bytes": source_identity.bytes,
            "sha256": source_identity.sha256,
        }:
            raise MutationAssuranceError("mutation parent module identity is wrong")
    return parent


def _receipt_complete_payload(
    run_id: str,
    files: Sequence[FileIdentity],
    *,
    publication_token: str,
) -> dict[str, object]:
    body: dict[str, object] = {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "run_id": run_id,
        "files": [
            {
                "path": item.path,
                "bytes": item.bytes,
                "sha256": item.sha256,
            }
            for item in files
        ],
        "integrity_boundary": (
            "sha256_tamper_evidence_not_signed_authenticity"
        ),
        "publication_token": publication_token,
    }
    body["manifest_sha256"] = sha256_bytes(canonical_json_bytes(body))
    return body


def _receipt_run_claim_payload(run_id: str, token: str) -> dict[str, object]:
    body: dict[str, object] = {
        "schema_version": 1,
        "run_id": run_id,
        "publication_token": token,
        "purpose": "exclusive_single_use_mutation_receipt_claim",
        "integrity_boundary": "sha256_tamper_evidence_not_signed_authenticity",
    }
    body["manifest_sha256"] = sha256_bytes(canonical_json_bytes(body))
    return body


def _validate_receipt_run_claim_payload(
    raw: bytes,
    *,
    run_id: str,
    token: str,
) -> None:
    claim = _object(
        strict_json_bytes(raw, label="mutation receipt run claim"),
        label="mutation receipt run claim",
    )
    _exact_fields(
        claim,
        {
            "schema_version",
            "run_id",
            "publication_token",
            "purpose",
            "integrity_boundary",
            "manifest_sha256",
        },
        label="mutation receipt run claim",
    )
    if (
        claim["schema_version"] != 1
        or claim["run_id"] != run_id
        or claim["publication_token"] != token
        or claim["purpose"]
        != "exclusive_single_use_mutation_receipt_claim"
        or claim["integrity_boundary"]
        != "sha256_tamper_evidence_not_signed_authenticity"
    ):
        raise MutationAssuranceError("mutation receipt run claim is inconsistent")
    unsigned = dict(claim)
    manifest = unsigned.pop("manifest_sha256")
    if manifest != sha256_bytes(canonical_json_bytes(unsigned)):
        raise MutationAssuranceError(
            "mutation receipt run claim manifest digest is invalid"
        )


def _create_receipt_run_claim(
    artifact_root: Path,
    *,
    run_id: str,
    token: str,
) -> _ReceiptRunClaim:
    """Atomically reserve one run ID; the sidecar intentionally remains."""

    raw = pretty_json_bytes(_receipt_run_claim_payload(run_id, token))
    path = artifact_root / f".claim-{run_id}.json"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_BINARY", 0) | getattr(os, "O_NOINHERIT", 0)
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError as exc:
        raise MutationAssuranceError(
            f"mutation receipt run ID already exists; claim is held: {run_id}"
        ) from exc
    except OSError as exc:
        raise MutationAssuranceError(
            f"mutation receipt run claim could not be created: {exc}"
        ) from exc

    descriptor_metadata: os.stat_result | None = None
    write_error: BaseException | None = None
    try:
        view = memoryview(raw)
        written = 0
        while written < len(view):
            count = os.write(descriptor, view[written:])
            if count <= 0:
                raise OSError("run claim write made no progress")
            written += count
        os.fsync(descriptor)
        descriptor_metadata = os.fstat(descriptor)
    except BaseException as exc:
        write_error = exc
    finally:
        try:
            os.close(descriptor)
        except OSError as exc:
            if write_error is None:
                write_error = exc
    if write_error is not None or descriptor_metadata is None:
        raise MutationAssuranceError(
            "mutation receipt run claim creation failed closed; the reserved "
            f"sidecar remains at {path}: {write_error}"
        ) from write_error
    try:
        path_metadata = path.lstat()
    except OSError as exc:
        raise MutationAssuranceError(
            "mutation receipt run claim disappeared after creation"
        ) from exc
    if (
        not stat.S_ISREG(descriptor_metadata.st_mode)
        or not stat.S_ISREG(path_metadata.st_mode)
        or stat.S_ISLNK(path_metadata.st_mode)
        or _is_reparse(path_metadata)
        or descriptor_metadata.st_nlink != 1
        or path_metadata.st_nlink != 1
        or descriptor_metadata.st_dev != path_metadata.st_dev
        or descriptor_metadata.st_ino != path_metadata.st_ino
        or stable_file_bytes(
            path,
            maximum_bytes=_MAX_JSON_BYTES,
            label="mutation receipt run claim",
        )
        != raw
    ):
        raise MutationAssuranceError(
            "mutation receipt run claim cannot establish exclusive ownership"
        )
    return _ReceiptRunClaim(
        path=path,
        token=token,
        device=path_metadata.st_dev,
        inode=path_metadata.st_ino,
        raw=raw,
    )


def _receipt_run_claim_is_current(claim: _ReceiptRunClaim) -> bool:
    try:
        metadata = claim.path.lstat()
        raw = stable_file_bytes(
            claim.path,
            maximum_bytes=_MAX_JSON_BYTES,
            label="mutation receipt run claim replay",
        )
    except (OSError, MutationAssuranceError):
        return False
    return (
        stat.S_ISREG(metadata.st_mode)
        and not stat.S_ISLNK(metadata.st_mode)
        and not _is_reparse(metadata)
        and metadata.st_nlink == 1
        and metadata.st_dev == claim.device
        and metadata.st_ino == claim.inode
        and raw == claim.raw
    )


def _require_current_receipt_run_claim(
    claim: _ReceiptRunClaim,
    *,
    stage: str,
) -> None:
    if not _receipt_run_claim_is_current(claim):
        raise MutationAssuranceError(
            f"mutation receipt run claim changed {stage}; publication fails closed"
        )


def _capture_receipt_publication_ownership(
    candidate: Path,
    marker: Path,
    *,
    token: str,
    complete_raw: bytes,
) -> _ReceiptPublicationOwnership:
    _plain_directory(candidate, label="mutation publication candidate")
    directory_metadata = candidate.lstat()
    marker_metadata = marker.lstat()
    if (
        not stat.S_ISREG(marker_metadata.st_mode)
        or stat.S_ISLNK(marker_metadata.st_mode)
        or _is_reparse(marker_metadata)
        or marker_metadata.st_nlink != 1
        or stable_file_bytes(
            marker,
            maximum_bytes=_MAX_JSON_BYTES,
            label="mutation publication ownership marker",
        )
        != complete_raw
    ):
        raise MutationAssuranceError(
            "mutation publication marker cannot establish ownership"
        )
    return _ReceiptPublicationOwnership(
        token=token,
        directory_device=directory_metadata.st_dev,
        directory_inode=directory_metadata.st_ino,
        marker_device=marker_metadata.st_dev,
        marker_inode=marker_metadata.st_ino,
        complete_raw=complete_raw,
    )


def _owned_receipt_marker_name(
    candidate: Path,
    ownership: _ReceiptPublicationOwnership,
) -> str | None:
    """Read-only proof that a public candidate is exactly this transaction's."""

    try:
        candidate_metadata = candidate.lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise MutationAssuranceError(
            f"mutation publication ownership cannot inspect candidate: {exc}"
        ) from exc
    if (
        not stat.S_ISDIR(candidate_metadata.st_mode)
        or stat.S_ISLNK(candidate_metadata.st_mode)
        or _is_reparse(candidate_metadata)
        or candidate_metadata.st_dev != ownership.directory_device
        or candidate_metadata.st_ino != ownership.directory_inode
    ):
        return None
    observed: list[str] = []
    for name in ("COMPLETE.pending", "COMPLETE"):
        path = candidate / name
        try:
            metadata = path.lstat()
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise MutationAssuranceError(
                f"mutation publication ownership cannot inspect marker: {exc}"
            ) from exc
        if (
            not stat.S_ISREG(metadata.st_mode)
            or stat.S_ISLNK(metadata.st_mode)
            or _is_reparse(metadata)
            or metadata.st_nlink != 1
            or metadata.st_dev != ownership.marker_device
            or metadata.st_ino != ownership.marker_inode
            or stable_file_bytes(
                path,
                maximum_bytes=_MAX_JSON_BYTES,
                label="mutation publication ownership marker replay",
            )
            != ownership.complete_raw
        ):
            return None
        observed.append(name)
    if len(observed) != 1:
        return None
    complete = strict_json_bytes(
        ownership.complete_raw,
        label="mutation publication ownership COMPLETE",
    )
    if (
        not isinstance(complete, dict)
        or complete.get("publication_token") != ownership.token
    ):
        return None
    return observed[0]


def _validated_run_timestamps(
    started_utc: object,
    finished_utc: object,
) -> tuple[str, str]:
    timestamps: dict[str, datetime] = {}
    for field, value in (
        ("started_utc", started_utc),
        ("finished_utc", finished_utc),
    ):
        if not isinstance(value, str) or not value.endswith("Z"):
            raise MutationAssuranceError(f"mutation run {field} is invalid")
        try:
            parsed = datetime.fromisoformat(value[:-1] + "+00:00")
        except ValueError as exc:
            raise MutationAssuranceError(f"mutation run {field} is invalid") from exc
        if (
            parsed.tzinfo != UTC
            or parsed.isoformat(timespec="seconds").replace("+00:00", "Z")
            != value
        ):
            raise MutationAssuranceError(
                f"mutation run {field} is not canonical UTC"
            )
        timestamps[field] = parsed
    if timestamps["finished_utc"] < timestamps["started_utc"]:
        raise MutationAssuranceError("mutation run finished before it started")
    return str(started_utc), str(finished_utc)


def _assert_result_sets(
    catalogue: MutationCatalogue,
    snapshot: SnapshotInputs,
    interpreter: Mapping[str, object],
    baselines: Sequence[Mapping[str, object]],
    mutants: Sequence[Mapping[str, object]],
) -> None:
    expected = [spec.mutant_id for spec in catalogue.mutants]
    baseline_ids = [value.get("mutant_id") for value in baselines]
    mutant_ids = [value.get("mutant_id") for value in mutants]
    if baseline_ids != expected or mutant_ids != expected:
        raise MutationAssuranceError(
            "receipt result IDs do not exactly match the sorted catalogue"
        )
    if len(baselines) != len(catalogue.mutants) or len(mutants) != len(catalogue.mutants):
        raise MutationAssuranceError("receipt result counts do not match the catalogue")
    derived_postimage_sha256: dict[str, str] = {}
    derived_postimage_bytes: dict[str, int] = {}
    baseline_roots: dict[str, PurePosixPath | PureWindowsPath] = {}
    baseline_test_code_sha256: dict[str, str] = {}
    baseline_test_sources: dict[str, dict[str, object]] = {}
    for spec, value in zip(catalogue.mutants, baselines):
        _exact_fields(value, _BASELINE_RESULT_FIELDS, label="baseline adjudication")
        _adjudication_digest_is_valid(value, label="baseline adjudication")
        outcome = value.get("outcome")
        if outcome not in {"baseline_passed", "blocked_baseline"}:
            raise MutationAssuranceError("receipt contains an invalid baseline outcome")
        if value.get("gate_credit") is not False:
            raise MutationAssuranceError("baseline must never receive mutation credit")
        expected_baseline_id = mutation_execution_id(spec, "baseline")
        if value.get("execution_id") != expected_baseline_id:
            raise MutationAssuranceError(
                "baseline execution ID is not role-specific and deterministic"
            )
        reasons = value.get("reasons")
        if not isinstance(reasons, list) or not all(isinstance(item, str) for item in reasons):
            raise MutationAssuranceError("baseline reasons are malformed")
        raw_test_source = value.get("intended_test_source")
        test_source = (
            None
            if raw_test_source is None
            else _validate_intended_test_source_receipt(
                raw_test_source,
                spec=spec,
                snapshot=snapshot,
            )
        )
        source_identity = value.get("source_identity")
        if outcome == "baseline_passed":
            if reasons != []:
                raise MutationAssuranceError("green baseline carries rejection reasons")
            if test_source is None:
                raise MutationAssuranceError(
                    "green baseline omits intended-test source evidence"
                )
            baseline_test_sources[spec.mutant_id] = test_source
            source = _object(source_identity, label="green baseline source identity")
            _exact_fields(
                source,
                {
                    "source_path",
                    "target_qualname",
                    "source_hash_mode",
                    "canonical_source_sha256",
                    "runtime_source_sha256",
                    "runtime_source_base64",
                    "ast_sha256",
                    "code_sha256",
                },
                label="green baseline source identity",
            )
            expected_source = _snapshot_identity(snapshot, spec.source_path)
            expected_identity = {
                "source_path": spec.source_path,
                "target_qualname": spec.target_qualname,
                "source_hash_mode": spec.source_hash_mode,
                "canonical_source_sha256": spec.preimage_sha256,
                "runtime_source_sha256": expected_source.sha256,
                "ast_sha256": spec.preimage_ast_sha256,
                "code_sha256": spec.preimage_code_sha256,
            }
            if {
                key: source[key] for key in expected_identity
            } != expected_identity:
                raise MutationAssuranceError("green baseline source identity is wrong")
            encoded_source = source["runtime_source_base64"]
            if not isinstance(encoded_source, str):
                raise MutationAssuranceError("green baseline source evidence is malformed")
            try:
                runtime_source = base64.b64decode(encoded_source, validate=True)
            except (binascii.Error, ValueError) as exc:
                raise MutationAssuranceError(
                    "green baseline source evidence is not canonical base64"
                ) from exc
            if (
                len(runtime_source) > _MAX_MUTATION_SOURCE_BYTES
                or base64.b64encode(runtime_source).decode("ascii") != encoded_source
                or sha256_bytes(runtime_source) != expected_source.sha256
            ):
                raise MutationAssuranceError("green baseline source bytes are wrong")
            canonical_runtime_source = canonical_source_bytes(runtime_source)
            if (
                sha256_bytes(canonical_runtime_source) != spec.preimage_sha256
                or _canonical_ast_sha256(
                    canonical_runtime_source,
                    qualname=spec.target_qualname,
                )
                != spec.preimage_ast_sha256
                or python_source_code_sha256(
                    canonical_runtime_source,
                    qualname=spec.target_qualname,
                )
                != spec.preimage_code_sha256
            ):
                raise MutationAssuranceError("green baseline source derivation is wrong")
            runtime_postimage = apply_exact_mutation(spec, runtime_source)
            canonical_postimage = canonical_source_bytes(runtime_postimage)
            if (
                sha256_bytes(canonical_postimage) != spec.postimage_sha256
                or _canonical_ast_sha256(
                    canonical_postimage,
                    qualname=spec.target_qualname,
                )
                != spec.postimage_ast_sha256
                or python_source_code_sha256(
                    canonical_postimage,
                    qualname=spec.target_qualname,
                )
                != spec.postimage_code_sha256
            ):
                raise MutationAssuranceError("mutant postimage derivation is wrong")
            derived_postimage_sha256[spec.mutant_id] = sha256_bytes(runtime_postimage)
            derived_postimage_bytes[spec.mutant_id] = len(runtime_postimage)
            phases = _validate_embedded_child_evidence(
                spec=spec,
                process_value=value["process"],
                child_value=value["child_report"],
                execution_id=str(value["execution_id"]),
                expected_returncode=0,
                expected_phase_outcomes=("passed", "passed", "passed"),
                runtime_source_sha256=expected_source.sha256,
                runtime_source_bytes=expected_source.bytes,
                expected_code_sha256=spec.preimage_code_sha256,
                expected_test_code_sha256=str(test_source["code_sha256"]),
                snapshot=snapshot,
                interpreter=interpreter,
            )
            if any(phase["exception"] is not None for phase in phases):
                raise MutationAssuranceError("green baseline contains an exception")
            baseline_report = _object(
                value["child_report"], label="green baseline child report"
            )
            baseline_identity = _object(
                baseline_report["identity"], label="green baseline child identity"
            )
            baseline_trace = _object(
                baseline_report["trace"], label="green baseline child trace"
            )
            baseline_test_code_sha256[spec.mutant_id] = _sha256(
                baseline_trace["resolved_intended_test_code_sha256"],
                label="green baseline intended-test code digest",
            )
            baseline_roots[spec.mutant_id] = _pure_receipt_path(
                baseline_identity["root"], label="green baseline root"
            )

    for spec, baseline, value in zip(catalogue.mutants, baselines, mutants):
        _exact_fields(value, _MUTANT_RESULT_FIELDS, label="mutant adjudication")
        _adjudication_digest_is_valid(value, label="mutant adjudication")
        outcome = value.get("outcome")
        if outcome not in OUTCOMES:
            raise MutationAssuranceError("receipt contains an invalid mutant outcome")
        if value.get("gate_credit") is not (outcome == "killed_intended"):
            raise MutationAssuranceError("mutant gate credit contradicts its outcome")
        if (
            value.get("fault_archetype") != spec.fault_archetype
            or value.get("criticality") != spec.criticality
            or value.get("evidence_class") != spec.evidence_class
            or value.get("exclusions") != list(spec.exclusions)
        ):
            raise MutationAssuranceError("mutant metadata contradicts the catalogue")
        expected_claim = {
            "nodeid": spec.intended_killer_nodeid,
            "claim_id": spec.expected_claim_id,
            "contract_sha256": spec.expected_contract_sha256,
        }
        if value.get("expected_killing_test_claim") != expected_claim:
            raise MutationAssuranceError("mutant expected claim contradicts the catalogue")
        reasons = value.get("reasons")
        if not isinstance(reasons, list) or not all(isinstance(item, str) for item in reasons):
            raise MutationAssuranceError("mutant reasons are malformed")
        raw_test_source = value.get("intended_test_source")
        test_source = (
            None
            if raw_test_source is None
            else _validate_intended_test_source_receipt(
                raw_test_source,
                spec=spec,
                snapshot=snapshot,
            )
        )
        source_mutation = _object(value.get("source_mutation"), label="source mutation")
        _exact_fields(
            source_mutation,
            {
                "source_path",
                "target_qualname",
                "operator",
                "source_hash_mode",
                "preimage_sha256",
                "postimage_sha256",
                "preimage_ast_sha256",
                "postimage_ast_sha256",
                "preimage_code_sha256",
                "postimage_code_sha256",
                "patch_sha256",
                "runtime_source_sha256",
            },
            label="source mutation",
        )
        expected_mutation = {
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
        }
        if {
            key: source_mutation[key] for key in expected_mutation
        } != expected_mutation:
            raise MutationAssuranceError("source mutation contradicts the catalogue")
        if outcome == "killed_intended":
            runtime_source_sha256 = _sha256(
                source_mutation["runtime_source_sha256"],
                label="mutant runtime source digest",
            )
            if runtime_source_sha256 != derived_postimage_sha256.get(spec.mutant_id):
                raise MutationAssuranceError(
                    "mutant runtime source digest is not the derived postimage"
                )
            if baseline["outcome"] != "baseline_passed":
                raise MutationAssuranceError("mutant received credit without a green baseline")
            if (
                test_source is None
                or test_source != baseline_test_sources.get(spec.mutant_id)
            ):
                raise MutationAssuranceError(
                    "baseline and mutant intended-test source evidence differs"
                )
            if reasons != []:
                raise MutationAssuranceError("credited mutant carries rejection reasons")
            phases = _validate_embedded_child_evidence(
                spec=spec,
                process_value=value["process"],
                child_value=value["child_report"],
                execution_id=mutation_execution_id(spec, "mutant"),
                expected_returncode=1,
                expected_phase_outcomes=("passed", "failed", "passed"),
                runtime_source_sha256=runtime_source_sha256,
                runtime_source_bytes=derived_postimage_bytes[spec.mutant_id],
                expected_code_sha256=spec.postimage_code_sha256,
                expected_test_code_sha256=str(test_source["code_sha256"]),
                snapshot=snapshot,
                interpreter=interpreter,
            )
            call = phases[1]
            mutant_report = _object(
                value["child_report"], label="credited child report"
            )
            mutant_identity = _object(
                mutant_report["identity"], label="credited child identity"
            )
            mutant_trace = _object(
                mutant_report["trace"], label="credited child trace"
            )
            if (
                mutant_trace["resolved_intended_test_code_sha256"]
                != baseline_test_code_sha256.get(spec.mutant_id)
            ):
                raise MutationAssuranceError(
                    "baseline and mutant executed different intended-test code"
                )
            if _pure_receipt_path(
                mutant_identity["root"], label="credited child root"
            ) != baseline_roots.get(spec.mutant_id):
                raise MutationAssuranceError(
                    "baseline and mutant did not use the same snapshot root"
                )
            _exception_matches(call["exception"], longrepr=call["longrepr"], spec=spec)
            actual = _object(value.get("actual_killing_test"), label="actual killer")
            test_relative, test_module_name, test_qualname = (
                _intended_test_coordinates(spec.intended_killer_nodeid)
            )
            _exact_fields(
                actual,
                {
                    "nodeid",
                    "phase",
                    "claim_id",
                    "contract_sha256",
                    "test_source_relative_path",
                    "test_module_name",
                    "test_qualname",
                    "test_code_sha256",
                    "exception",
                },
                label="actual killer",
            )
            if actual != {
                "nodeid": spec.intended_killer_nodeid,
                "phase": "call",
                "claim_id": spec.expected_claim_id,
                "contract_sha256": spec.expected_contract_sha256,
                "test_source_relative_path": test_relative,
                "test_module_name": test_module_name,
                "test_qualname": test_qualname,
                "test_code_sha256": mutant_trace[
                    "resolved_intended_test_code_sha256"
                ],
                "exception": call["exception"],
            }:
                raise MutationAssuranceError("actual killer evidence is inconsistent")
        else:
            if value.get("actual_killing_test") is not None:
                raise MutationAssuranceError("non-credited mutant names an actual killer")
            if outcome == "blocked_baseline":
                if value.get("process") is not None or value.get("child_report") is not None:
                    raise MutationAssuranceError("baseline-blocked mutant contains execution evidence")
                if source_mutation["runtime_source_sha256"] is not None:
                    raise MutationAssuranceError("baseline-blocked mutant claims a postimage")


def seal_mutation_receipt(
    *,
    artifact_root: Path,
    run_id: str,
    catalogue: MutationCatalogue,
    snapshot: SnapshotInputs,
    interpreter: Mapping[str, object],
    parent_runtime: Mapping[str, object],
    baselines: Sequence[Mapping[str, object]],
    mutants: Sequence[Mapping[str, object]],
    started_utc: str,
    finished_utc: str,
    native_build: Mapping[str, object] | None = None,
    pre_publish_check: Callable[[], None] | None = None,
) -> Path:
    """Atomically seal a structurally complete green or red mutation run.

    A root-level ``O_CREAT|O_EXCL`` claim reserves the run ID before staging
    begins.  It deliberately remains after success or failure, making crash
    recovery and run-ID reuse explicit rather than racy.  Its exact portable
    payload is also copied into and bound by the receipt as ``claim.json``.
    This excludes cooperative sealers; it is not hostile same-user filesystem
    isolation.  An actor that swaps receipt paths after an ownership replay or
    transiently injects then removes new Git-runtime DLL/helper names remains
    outside this Python transaction boundary.

    The data directory is moved into its final location without a commitment
    marker.  Every candidate replay, caller-owned current-state check, and
    staging cleanup completes before ``COMPLETE`` appears through one atomic
    rename.  That rename is the transaction's final fallible filesystem
    operation, so no rejected candidate can strand a public completion marker.
    Atomic visibility does not claim power-loss durability on filesystems that
    require a post-rename parent-directory flush.
    """

    if _RUN_ID_RE.fullmatch(run_id) is None:
        raise MutationAssuranceError("mutation receipt run ID is invalid")
    if pre_publish_check is not None and not callable(pre_publish_check):
        raise MutationAssuranceError("mutation pre-publication check is invalid")
    started_utc, finished_utc = _validated_run_timestamps(
        started_utc,
        finished_utc,
    )
    snapshot = _snapshot_inputs_from_payload(snapshot_manifest_payload(snapshot))
    checked_interpreter = _validate_interpreter_receipt(interpreter)
    checked_parent_runtime = _validate_parent_runtime_receipt(
        parent_runtime,
        snapshot=snapshot,
    )
    checked_native_build = _validate_native_build_receipt(
        native_build,
        catalogue=catalogue,
        snapshot=snapshot,
    )
    _assert_result_sets(
        catalogue,
        snapshot,
        checked_interpreter,
        baselines,
        mutants,
    )
    all_killed = all(value["outcome"] == "killed_intended" for value in mutants)
    all_baselines = all(value["outcome"] == "baseline_passed" for value in baselines)
    status = "passed" if all_killed and all_baselines else "failed"

    if artifact_root.exists():
        _plain_directory(artifact_root, label="mutation artifact root")
    else:
        artifact_root.mkdir(parents=True)
        _plain_directory(artifact_root, label="mutation artifact root")
    publication_token = secrets.token_hex(32)
    run_claim = _create_receipt_run_claim(
        artifact_root,
        run_id=run_id,
        token=publication_token,
    )
    final = artifact_root / run_id
    staging_container = artifact_root / f".incomplete-{run_id}"
    staging = staging_container / run_id
    if final.exists() or staging_container.exists():
        raise MutationAssuranceError("mutation receipt run ID already exists")
    _require_current_receipt_run_claim(
        run_claim,
        stage="before staging creation",
    )
    staging.mkdir(parents=True)
    pending_complete = staging / "COMPLETE.pending"
    publication_ownership: _ReceiptPublicationOwnership | None = None
    try:
        catalogue_raw = stable_file_bytes(
            catalogue.path,
            maximum_bytes=_MAX_JSON_BYTES,
            label="mutation catalogue",
        )
        if sha256_bytes(catalogue_raw) != catalogue.sha256:
            raise MutationAssuranceError("mutation catalogue changed before sealing")
        payloads: dict[str, bytes] = {
            "catalogue.json": catalogue_raw,
            "claim.json": run_claim.raw,
            "snapshot.json": pretty_json_bytes(snapshot_manifest_payload(snapshot)),
            "baselines.json": pretty_json_bytes(
                {"schema_version": 1, "baselines": list(baselines)}
            ),
            "mutants.json": pretty_json_bytes(
                {"schema_version": 1, "mutants": list(mutants)}
            ),
            "run.json": pretty_json_bytes(
                {
                    "schema_version": RECEIPT_SCHEMA_VERSION,
                    "run_id": run_id,
                    "status": status,
                    "started_utc": started_utc,
                    "finished_utc": finished_utc,
                    "catalogue_sha256": catalogue.sha256,
                    "snapshot_manifest_sha256": snapshot.manifest_sha256,
                    "interpreter": dict(checked_interpreter),
                    "parent_runtime": dict(checked_parent_runtime),
                    "native_build": (
                        dict(checked_native_build)
                        if checked_native_build is not None
                        else None
                    ),
                    "mutant_ids": [
                        spec.mutant_id for spec in catalogue.mutants
                    ],
                    "summary": {
                        "declared": len(catalogue.mutants),
                        "baseline_passed": sum(
                            value["outcome"] == "baseline_passed"
                            for value in baselines
                        ),
                        "killed_intended": sum(
                            value["outcome"] == "killed_intended"
                            for value in mutants
                        ),
                        "gate": "all_declared_mutants_no_percentage",
                        "gate_passed": status == "passed",
                    },
                    "boundaries": {
                        "source_mutations": "disposable_plain_file_snapshots_only",
                        "filesystem_concurrency": (
                            "cooperative_claim_exclusion_and_existing_windows_"
                            "runtime_file_locks_not_hostile_same_user_path_swap_"
                            "or_transient_runtime_membership_injection_isolation"
                        ),
                        "network": (
                            "cooperative_cpython_deny_not_security_sandbox"
                        ),
                        "integrity": (
                            "sha256_tamper_evidence_not_signed_authenticity"
                        ),
                        "native": (
                            "unchanged_copied_backend_only_no_native_mutation"
                        ),
                        "report_authorship": _REPORT_AUTHORSHIP_BOUNDARY,
                    },
                }
            ),
        }
        identities: list[FileIdentity] = []
        for name in _RECEIPT_DATA_FILES:
            raw = payloads[name]
            _write_new_file(staging / name, raw)
            identities.append(
                FileIdentity(path=name, bytes=len(raw), sha256=sha256_bytes(raw))
            )
        complete = _receipt_complete_payload(
            run_id,
            identities,
            publication_token=publication_token,
        )
        complete_raw = pretty_json_bytes(complete)
        _validate_mutation_receipt(
            staging,
            current_catalogue=catalogue,
            current_snapshot=snapshot,
            current_interpreter=checked_interpreter,
            current_native_build=checked_native_build,
            require_green=False,
            candidate_complete_raw=complete_raw,
            allow_uncommitted=True,
        )
        if pre_publish_check is not None:
            pre_publish_check()
        _write_new_file(pending_complete, complete_raw)
        publication_ownership = _capture_receipt_publication_ownership(
            staging,
            pending_complete,
            token=publication_token,
            complete_raw=complete_raw,
        )
        _require_current_receipt_run_claim(
            run_claim,
            stage="before candidate publication",
        )
        os.replace(staging, final)
        _validate_mutation_receipt(
            final,
            current_catalogue=catalogue,
            current_snapshot=snapshot,
            current_interpreter=checked_interpreter,
            current_native_build=checked_native_build,
            require_green=False,
            candidate_complete_raw=complete_raw,
            candidate_complete_name="COMPLETE.pending",
            allow_uncommitted=True,
        )
        if pre_publish_check is not None:
            pre_publish_check()
        _require_current_receipt_run_claim(
            run_claim,
            stage="before incomplete-container cleanup",
        )
        staging_container.rmdir()
        _validate_mutation_receipt(
            final,
            current_catalogue=catalogue,
            current_snapshot=snapshot,
            current_interpreter=checked_interpreter,
            current_native_build=checked_native_build,
            require_green=False,
            candidate_complete_raw=complete_raw,
            candidate_complete_name="COMPLETE.pending",
            allow_uncommitted=True,
        )
        if pre_publish_check is not None:
            pre_publish_check()
        _require_current_receipt_run_claim(
            run_claim,
            stage="before commitment",
        )
        # Deliberately last: after this atomic visibility boundary there is no
        # validation, callback, cleanup, or other fallible filesystem action.
        os.replace(final / "COMPLETE.pending", final / "COMPLETE")
    except BaseException as exc:
        deferred_handlers: list[tuple[int, Any]] = []
        for interrupt_signal in (
            signal.SIGINT,
            getattr(signal, "SIGBREAK", None),
        ):
            if interrupt_signal is None:
                continue
            try:
                previous_handler = signal.getsignal(interrupt_signal)
                signal.signal(interrupt_signal, signal.SIG_IGN)
            except (OSError, ValueError):
                continue
            deferred_handlers.append((interrupt_signal, previous_handler))
        rollback_errors: list[str] = []
        try:
            claim_current = _receipt_run_claim_is_current(run_claim)
            if publication_ownership is not None and not claim_current:
                rollback_errors.append(
                    "run claim ownership was lost; rollback made no writes"
                )
            owned_marker = (
                _owned_receipt_marker_name(final, publication_ownership)
                if publication_ownership is not None and claim_current
                else None
            )
            if owned_marker is not None:
                rollback_container_ready = False
                try:
                    if not staging_container.exists():
                        staging_container.mkdir()
                    _plain_directory(
                        staging_container,
                        label="mutation rollback container",
                    )
                    rollback_container_ready = True
                except (OSError, MutationAssuranceError) as rollback_exc:
                    rollback_errors.append(
                        "incomplete-container restoration failed: "
                        f"{rollback_exc}"
                    )
                if rollback_container_ready:
                    try:
                        if staging.exists():
                            raise MutationAssuranceError(
                                "owned candidate rollback destination exists"
                            )
                        os.replace(final, staging)
                        if (
                            _owned_receipt_marker_name(
                                staging,
                                publication_ownership,
                            )
                            != owned_marker
                        ):
                            raise MutationAssuranceError(
                                "rolled-back candidate lost its ownership proof"
                            )
                        if owned_marker == "COMPLETE":
                            os.replace(
                                staging / "COMPLETE",
                                staging_container / "COMPLETE.revoked",
                            )
                    except (OSError, MutationAssuranceError) as rollback_exc:
                        rollback_errors.append(
                            f"candidate rollback failed: {rollback_exc}"
                        )
        finally:
            for interrupt_signal, previous_handler in reversed(
                deferred_handlers
            ):
                try:
                    signal.signal(interrupt_signal, previous_handler)
                except (OSError, ValueError):
                    rollback_errors.append(
                        "interrupt handler restoration failed for "
                        f"signal {interrupt_signal}"
                    )
        if rollback_errors:
            raise MutationAssuranceError(
                "mutation receipt rollback failed; a commitment may remain at "
                f"{final}: {'; '.join(rollback_errors)}; triggering "
                f"{type(exc).__name__}: {exc}"
            ) from exc
        # Preserve an explicitly incomplete, categorically non-verifiable
        # diagnostic directory.  A rollback error is surfaced on the original
        # exception because it can mean a commitment marker remains visible.
        raise
    return final


def _validate_mutation_receipt(
    path: Path,
    *,
    current_catalogue: MutationCatalogue | None,
    current_snapshot: SnapshotInputs | None = None,
    current_interpreter: Mapping[str, object] | None = None,
    current_native_build: Mapping[str, object] | None = None,
    require_green: bool,
    candidate_complete_raw: bytes | None = None,
    candidate_complete_name: str | None = None,
    allow_uncommitted: bool = False,
) -> dict[str, object]:
    """Validate a committed receipt or one private uncommitted candidate."""

    _plain_directory(path, label="mutation receipt")
    path = path.resolve(strict=True)
    if not allow_uncommitted and any(
        parent.name.casefold().startswith(
            _FORBIDDEN_RECEIPT_ANCESTOR_PREFIXES
        )
        for parent in path.parents
    ):
        raise MutationAssuranceError(
            "mutation receipt is below an incomplete or revoked container"
        )
    if (candidate_complete_raw is None) != (not allow_uncommitted):
        raise MutationAssuranceError(
            "mutation candidate validation mode is inconsistent"
        )
    if candidate_complete_name not in {None, "COMPLETE.pending"}:
        raise MutationAssuranceError(
            "mutation candidate completion filename is invalid"
        )
    if not allow_uncommitted and candidate_complete_name is not None:
        raise MutationAssuranceError(
            "committed mutation receipt names a pending completion marker"
        )
    expected_files = _RECEIPT_FILES
    if allow_uncommitted:
        expected_files = _UNCOMMITTED_RECEIPT_FILES | (
            frozenset({candidate_complete_name})
            if candidate_complete_name is not None
            else frozenset()
        )
    observed_files = set(_walk_snapshot_files(path))
    if observed_files != expected_files:
        raise MutationAssuranceError("mutation receipt file set is not exact")
    if candidate_complete_raw is None:
        complete_raw = stable_file_bytes(
            path / "COMPLETE",
            maximum_bytes=_MAX_JSON_BYTES,
            label="mutation COMPLETE",
        )
    else:
        if len(candidate_complete_raw) > _MAX_JSON_BYTES:
            raise MutationAssuranceError(
                "mutation candidate COMPLETE exceeds its byte limit"
            )
        complete_raw = candidate_complete_raw
        if candidate_complete_name is not None and stable_file_bytes(
            path / candidate_complete_name,
            maximum_bytes=_MAX_JSON_BYTES,
            label="mutation pending COMPLETE",
        ) != complete_raw:
            raise MutationAssuranceError(
                "mutation pending COMPLETE differs from its candidate bytes"
            )
    complete = strict_json_bytes(complete_raw, label="mutation COMPLETE")
    complete_obj = _object(complete, label="mutation COMPLETE")
    _exact_fields(
        complete_obj,
        {
            "schema_version",
            "run_id",
            "files",
            "integrity_boundary",
            "publication_token",
            "manifest_sha256",
        },
        label="mutation COMPLETE",
    )
    if complete_obj["schema_version"] != RECEIPT_SCHEMA_VERSION:
        raise MutationAssuranceError("mutation receipt schema is unsupported")
    if complete_obj["integrity_boundary"] != "sha256_tamper_evidence_not_signed_authenticity":
        raise MutationAssuranceError("mutation receipt integrity boundary is wrong")
    publication_token = _sha256(
        complete_obj["publication_token"],
        label="mutation receipt publication token",
    )
    complete_run_id = complete_obj["run_id"]
    if (
        not isinstance(complete_run_id, str)
        or _RUN_ID_RE.fullmatch(complete_run_id) is None
    ):
        raise MutationAssuranceError("mutation receipt run ID is invalid")
    unsigned = dict(complete_obj)
    manifest = unsigned.pop("manifest_sha256")
    if manifest != sha256_bytes(canonical_json_bytes(unsigned)):
        raise MutationAssuranceError("mutation COMPLETE manifest digest is invalid")
    raw_files = _list(complete_obj["files"], label="mutation COMPLETE files")
    if len(raw_files) != len(_RECEIPT_DATA_FILES):
        raise MutationAssuranceError("mutation COMPLETE file count is invalid")
    names: list[str] = []
    receipt_raw: dict[str, bytes] = {}
    for index, raw_identity in enumerate(raw_files):
        identity = _object(raw_identity, label=f"mutation COMPLETE files[{index}]")
        _exact_fields(
            identity,
            {"path", "bytes", "sha256"},
            label=f"mutation COMPLETE files[{index}]",
        )
        name = identity["path"]
        if not isinstance(name, str) or name not in _RECEIPT_DATA_FILES:
            raise MutationAssuranceError("mutation COMPLETE names an invalid file")
        names.append(name)
        raw = stable_file_bytes(
            path / name,
            maximum_bytes=_MAX_JSON_BYTES,
            label=f"mutation receipt {name}",
        )
        if identity["bytes"] != len(raw) or identity["sha256"] != sha256_bytes(raw):
            raise MutationAssuranceError(f"mutation receipt {name} digest is invalid")
        receipt_raw[name] = raw
    if names != list(_RECEIPT_DATA_FILES) or len(set(names)) != len(names):
        raise MutationAssuranceError("mutation COMPLETE file order is invalid")
    _validate_receipt_run_claim_payload(
        receipt_raw["claim.json"],
        run_id=complete_run_id,
        token=publication_token,
    )

    run = _object(
        strict_json_bytes(receipt_raw["run.json"], label="mutation run"),
        label="mutation run",
    )
    _exact_fields(
        run,
        {
            "schema_version",
            "run_id",
            "status",
            "started_utc",
            "finished_utc",
            "catalogue_sha256",
            "snapshot_manifest_sha256",
            "interpreter",
            "parent_runtime",
            "native_build",
            "mutant_ids",
            "summary",
            "boundaries",
        },
        label="mutation run",
    )
    if run["schema_version"] != RECEIPT_SCHEMA_VERSION:
        raise MutationAssuranceError("mutation run schema is unsupported")
    if run.get("run_id") != complete_obj["run_id"] or path.name != run.get("run_id"):
        raise MutationAssuranceError("mutation receipt run ID is inconsistent")
    catalogue_raw = receipt_raw["catalogue.json"]
    catalogue_digest = sha256_bytes(catalogue_raw)
    if run.get("catalogue_sha256") != catalogue_digest:
        raise MutationAssuranceError("mutation run catalogue digest is inconsistent")
    if current_catalogue is not None and catalogue_digest != current_catalogue.sha256:
        raise MutationAssuranceError("mutation receipt catalogue is stale")
    if current_catalogue is None:
        from evidence.contracts import CONTRACTS

        receipted_catalogue = _load_catalogue_bytes(
            catalogue_raw,
            path=(path / "catalogue.json").resolve(strict=True),
            root=path,
            contracts=CONTRACTS,
            verify_sources=False,
        )
    else:
        receipted_catalogue = current_catalogue
    snapshot_payload = strict_json_bytes(
        receipt_raw["snapshot.json"], label="mutation snapshot"
    )
    snapshot = _snapshot_inputs_from_payload(snapshot_payload)
    if run.get("snapshot_manifest_sha256") != snapshot.manifest_sha256:
        raise MutationAssuranceError("mutation snapshot manifest is inconsistent")
    interpreter = _validate_interpreter_receipt(run["interpreter"])
    native_required = any(
        spec.requires_native_backend for spec in receipted_catalogue.mutants
    )
    if require_green and (
        current_catalogue is None
        or current_snapshot is None
        or current_interpreter is None
        or (native_required and current_native_build is None)
    ):
        raise MutationAssuranceError(
            "current-checkout green verification requires all current identities"
        )
    if current_snapshot is not None:
        checked_current_snapshot = _snapshot_inputs_from_payload(
            snapshot_manifest_payload(current_snapshot)
        )
        if checked_current_snapshot != snapshot:
            raise MutationAssuranceError(
                "mutation receipt snapshot is stale for the current checkout"
            )
    if current_interpreter is not None:
        checked_current_interpreter = _validate_interpreter_receipt(
            current_interpreter
        )
        if checked_current_interpreter != interpreter:
            raise MutationAssuranceError(
                "mutation receipt interpreter is stale for the current checkout"
            )
    receipted_native_build = _validate_native_build_receipt(
        run["native_build"],
        catalogue=receipted_catalogue,
        snapshot=snapshot,
    )
    if current_native_build is not None:
        checked_current_native_build = _validate_native_build_receipt(
            current_native_build,
            catalogue=receipted_catalogue,
            snapshot=snapshot,
        )
        if checked_current_native_build != receipted_native_build:
            raise MutationAssuranceError(
                "mutation native-build receipt is stale for the current checkout"
            )
    _validate_parent_runtime_receipt(run["parent_runtime"], snapshot=snapshot)
    baselines_doc = _object(
        strict_json_bytes(
            receipt_raw["baselines.json"],
            label="mutation baselines",
        ),
        label="mutation baselines",
    )
    mutants_doc = _object(
        strict_json_bytes(
            receipt_raw["mutants.json"],
            label="mutation results",
        ),
        label="mutation results",
    )
    _exact_fields(
        baselines_doc,
        {"schema_version", "baselines"},
        label="mutation baselines",
    )
    _exact_fields(
        mutants_doc,
        {"schema_version", "mutants"},
        label="mutation results",
    )
    if baselines_doc["schema_version"] != 1 or mutants_doc["schema_version"] != 1:
        raise MutationAssuranceError("mutation result document schema is unsupported")
    baselines = [
        _object(value, label=f"mutation baselines[{index}]")
        for index, value in enumerate(
            _list(baselines_doc["baselines"], label="mutation baselines")
        )
    ]
    mutants = [
        _object(value, label=f"mutation results[{index}]")
        for index, value in enumerate(
            _list(mutants_doc["mutants"], label="mutation results")
        )
    ]
    expected_ids = run.get("mutant_ids")
    if not isinstance(expected_ids, list) or not all(
        isinstance(value, str) for value in expected_ids
    ):
        raise MutationAssuranceError("mutation run IDs are malformed")
    catalogue_ids = [spec.mutant_id for spec in receipted_catalogue.mutants]
    if expected_ids != catalogue_ids:
        raise MutationAssuranceError("mutation run IDs contradict the catalogue")
    _assert_result_sets(
        receipted_catalogue,
        snapshot,
        interpreter,
        baselines,
        mutants,
    )
    green = all(
        isinstance(value, dict)
        and value.get("outcome") == "killed_intended"
        and value.get("gate_credit") is True
        for value in mutants
    ) and all(
        isinstance(value, dict)
        and value.get("outcome") == "baseline_passed"
        and value.get("gate_credit") is False
        for value in baselines
    )
    if run.get("status") != ("passed" if green else "failed"):
        raise MutationAssuranceError("mutation run status contradicts its results")
    summary = _object(run.get("summary"), label="mutation run summary")
    _exact_fields(
        summary,
        {
            "declared",
            "baseline_passed",
            "killed_intended",
            "gate",
            "gate_passed",
        },
        label="mutation run summary",
    )
    if (
        summary.get("declared") != len(expected_ids)
        or summary.get("baseline_passed")
        != sum(
            isinstance(value, dict) and value.get("outcome") == "baseline_passed"
            for value in baselines
        )
        or summary.get("killed_intended")
        != sum(
            isinstance(value, dict) and value.get("outcome") == "killed_intended"
            for value in mutants
        )
        or summary.get("gate_passed") is not green
        or summary.get("gate") != "all_declared_mutants_no_percentage"
    ):
        raise MutationAssuranceError("mutation run summary contradicts its results")
    boundaries = _object(run.get("boundaries"), label="mutation run boundaries")
    if boundaries != {
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
    }:
        raise MutationAssuranceError("mutation run boundaries are not admitted")
    _validated_run_timestamps(run["started_utc"], run["finished_utc"])
    if require_green and not green:
        raise MutationAssuranceError("mutation receipt is complete but not green")
    if set(_walk_snapshot_files(path)) != expected_files:
        raise MutationAssuranceError(
            "mutation receipt file set changed during validation"
        )
    if candidate_complete_raw is None:
        if stable_file_bytes(
            path / "COMPLETE",
            maximum_bytes=_MAX_JSON_BYTES,
            label="mutation COMPLETE replay",
        ) != complete_raw:
            raise MutationAssuranceError(
                "mutation COMPLETE changed during validation"
            )
    for name in _RECEIPT_DATA_FILES:
        if stable_file_bytes(
            path / name,
            maximum_bytes=_MAX_JSON_BYTES,
            label=f"mutation receipt replay {name}",
        ) != receipt_raw[name]:
            raise MutationAssuranceError(
                f"mutation receipt {name} changed during validation"
            )
    if candidate_complete_name is not None and stable_file_bytes(
        path / candidate_complete_name,
        maximum_bytes=_MAX_JSON_BYTES,
        label="mutation pending COMPLETE replay",
    ) != complete_raw:
        raise MutationAssuranceError(
            "mutation pending COMPLETE changed during validation"
        )
    return run


def validate_mutation_receipt(
    path: Path,
    *,
    current_catalogue: MutationCatalogue | None,
    current_snapshot: SnapshotInputs | None = None,
    current_interpreter: Mapping[str, object] | None = None,
    current_native_build: Mapping[str, object] | None = None,
    require_green: bool,
) -> dict[str, object]:
    """Validate one public committed Phase 11 receipt."""

    return _validate_mutation_receipt(
        path,
        current_catalogue=current_catalogue,
        current_snapshot=current_snapshot,
        current_interpreter=current_interpreter,
        current_native_build=current_native_build,
        require_green=require_green,
    )
