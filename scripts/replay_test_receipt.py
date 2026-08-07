"""Replay failed pytest node IDs from one completed Moira run receipt.

The receipt is data, never executable input.  This script owns the repository,
interpreter, working directory, environment policy, and pytest command.  It
does not reuse a recorded command line, environment, executable, or working
directory.
"""

from __future__ import annotations

import argparse
import hashlib
from importlib import import_module
import json
import math
import os
import platform
import re
import stat
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any


SCHEMA_VERSION = 1
SCRIPT_PATH = Path(__file__).resolve(strict=True)
REPOSITORY_ROOT = SCRIPT_PATH.parents[1]

_ARTIFACT_FILENAMES = (
    "collection.json",
    "resources.json",
    "reports.jsonl",
    "failures.json",
    "durations.json",
    "rerun-nodeids.json",
)
_COMPLETED_RECEIPT_FILENAMES = frozenset(
    (*_ARTIFACT_FILENAMES, "run.json", "COMPLETE")
)
_MAX_COMPLETE_BYTES = 64 * 1024
_MAX_RUN_JSON_BYTES = 16 * 1024 * 1024
_MAX_ARTIFACT_SIDECAR_BYTES = 16 * 1024 * 1024
_MAX_COMPLETED_RECEIPT_BYTES = 16 * 1024 * 1024
_MAX_RESOURCES_JSON_BYTES = 16 * 1024 * 1024
_MAX_RERUN_NODEIDS_BYTES = 16 * 1024 * 1024
_MAX_JSON_DEPTH = 64
_MAX_JSON_NODES = 1_000_000
_MAX_NODEIDS = 10_000
_MAX_NODEID_CHARS = 16 * 1024
_MAX_RESOURCE_REQUIREMENTS = 10_000
_MAX_DISTINCT_RESOURCE_REQUIREMENTS = 256
_MAX_TEST_SEED = (1 << 64) - 1
_RUN_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")
_WINDOWS_RESERVED_COMPONENTS = frozenset(
    {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{index}" for index in range(1, 10)),
        *(f"LPT{index}" for index in range(1, 10)),
    }
)
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_GIT_OBJECT_RE = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")
_WINDOWS_REPARSE_POINT_ATTRIBUTE = getattr(
    stat,
    "FILE_ATTRIBUTE_REPARSE_POINT",
    0x400,
)
_WINDOWS_NAME_SURROGATE_TAG_BIT = 0x20000000
_EXECUTION_SWITCH_NAMES = (
    "MOIRA_ACCELERATE",
    "MOIRA_FORCE_PYTHON_TYPE13",
    "MOIRA_FORCE_PYTHON_CHEBYSHEV",
)

_REPLAY_ENVIRONMENT_REMOVE = (
    "COVERAGE_FILE",
    "COVERAGE_PROCESS_START",
    "COV_CORE_BRANCH",
    "COV_CORE_CONFIG",
    "COV_CORE_DATAFILE",
    "COV_CORE_SOURCE",
    "MOIRA_REGRESSION_PCT",
    "MOIRA_PYTEST_PLUGIN_AUTOLOAD",
    "MOIRA_RUN_EXPERIMENTAL",
    "MOIRA_RUN_TEMPLATES",
    "MOIRA_SKIP_SLOW",
    *_EXECUTION_SWITCH_NAMES,
    "MOIRA_TEST_BUDGET_CASE_S",
    "MOIRA_TEST_BUDGET_TOTAL_S",
    "PYTEST_ADDOPTS",
    "PYTEST_DEBUG",
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD",
    "PYTEST_PLUGINS",
    "PYTEST_THEME",
    "PYTEST_THEME_MODE",
    "PYTEST_CURRENT_TEST",
    "PYTEST_XDIST_AUTO_NUM_WORKERS",
    "PYTEST_XDIST_TESTRUNUID",
    "PYTEST_XDIST_WORKER",
    "PYTEST_XDIST_WORKER_COUNT",
    "MOIRA_WORKER_ID",
    "MOIRA_TEST_RUN_ID",
    "PYTHONBREAKPOINT",
    "PYTHONASYNCIODEBUG",
    "PYTHONCASEOK",
    "PYTHONDEVMODE",
    "PYTHONHOME",
    "PYTHONHASHSEED",
    "PYTHONINSPECT",
    "PYTHONINTMAXSTRDIGITS",
    "PYTHONNOUSERSITE",
    "PYTHONOPTIMIZE",
    "PYTHONPATH",
    "PYTHONPYCACHEPREFIX",
    "PYTHONSAFEPATH",
    "PYTHONSTARTUP",
    "PYTHONUSERBASE",
    "PYTHONWARNINGS",
)
_REPLAY_ENVIRONMENT_SET = {
    "MOIRA_TEST_MODE": "1",
    "MOIRA_NO_DOWNLOAD": "1",
    "MOIRA_STRICT_KNOWN_ISSUES": "1",
    "MOIRA_TEST_ARTIFACTS": "0",
    "MOIRA_SNAPSHOT_UPDATE": "0",
    "MOIRA_GOLDEN_UPDATE": "0",
    "MOIRA_TEST_NETWORK_POLICY": "deny",
    "MOIRA_PYTEST_PLUGIN_AUTOLOAD": "0",
    "MOIRA_SKIP_SLOW": "0",
    "MOIRA_RUN_EXPERIMENTAL": "1",
    "MOIRA_RUN_TEMPLATES": "1",
    "MOIRA_TEST_BUDGET_CASE_S": "0",
    "MOIRA_TEST_BUDGET_TOTAL_S": "0",
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
    "PYTHONNOUSERSITE": "1",
    "PYTHONOPTIMIZE": "0",
}


class ReplayContractError(RuntimeError):
    """A run receipt or local replay prerequisite is invalid."""


class _DuplicateKeyError(ValueError):
    """Strict JSON encountered an ambiguous duplicate object key."""


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Replay exact failed node IDs from a completed Moira pytest "
            "controller receipt."
        )
    )
    parser.add_argument("run_json", type=Path, help="Path to completed run.json")
    parser.add_argument(
        "--allow-repository-mismatch",
        action="store_true",
        help=(
            "Explicitly permit replay in this script's repository when the "
            "receipt records a different repository root."
        ),
    )
    parser.add_argument(
        "--allow-state-mismatch",
        action="store_true",
        help=(
            "Explicitly permit replay after reported interpreter, Git, native, "
            "or resource state mismatches."
        ),
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Validate the receipt and current state without launching pytest.",
    )
    return parser.parse_args(argv)


def _is_name_surrogate_reparse(metadata: os.stat_result) -> bool:
    has_reparse_attribute = bool(
        getattr(metadata, "st_file_attributes", 0)
        & _WINDOWS_REPARSE_POINT_ATTRIBUTE
    )
    reparse_tag = getattr(metadata, "st_reparse_tag", None)
    return has_reparse_attribute and (
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


def _directory_metadata(path: Path, *, label: str) -> os.stat_result:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise ReplayContractError(f"{label} is unavailable: {path}: {exc}") from exc
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or stat.S_ISLNK(metadata.st_mode)
        or _is_name_surrogate_reparse(metadata)
    ):
        raise ReplayContractError(
            f"{label} must be a real directory, not a symlink or "
            f"name-surrogate reparse point: {path}"
        )
    return metadata


def _assert_directory_unchanged(
    path: Path,
    expected: os.stat_result,
    *,
    label: str,
) -> None:
    observed = _directory_metadata(path, label=label)
    if _directory_identity(observed) != _directory_identity(expected):
        raise ReplayContractError(f"{label} changed during receipt validation")


def _assert_completed_receipt_file_set(path: Path) -> None:
    try:
        with os.scandir(path) as entries:
            observed = {entry.name for entry in entries}
    except OSError as exc:
        raise ReplayContractError(
            f"cannot enumerate completed artifact run directory {path}: {exc}"
        ) from exc
    if observed != _COMPLETED_RECEIPT_FILENAMES:
        missing = sorted(_COMPLETED_RECEIPT_FILENAMES - observed)
        extra = sorted(observed - _COMPLETED_RECEIPT_FILENAMES)
        raise ReplayContractError(
            "completed artifact run must contain exactly the fixed receipt "
            f"set; missing={missing!r}, extra={extra!r}"
        )


def _path_entry_exists(path: Path) -> bool:
    try:
        path.lstat()
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise ReplayContractError(f"cannot inspect artifact entry {path}: {exc}") from exc
    return True


def _stable_file_bytes(
    path: Path,
    *,
    maximum_bytes: int,
    label: str,
) -> bytes:
    try:
        path_metadata = path.lstat()
    except OSError as exc:
        raise ReplayContractError(f"{label} is unavailable: {path}: {exc}") from exc
    if (
        not stat.S_ISREG(path_metadata.st_mode)
        or stat.S_ISLNK(path_metadata.st_mode)
        or _is_name_surrogate_reparse(path_metadata)
    ):
        raise ReplayContractError(
            f"{label} must be a real regular file, not a symlink or "
            f"name-surrogate reparse point: {path}"
        )
    if path_metadata.st_size > maximum_bytes:
        raise ReplayContractError(
            f"{label} exceeds the {maximum_bytes}-byte replay limit: {path}"
        )

    try:
        with path.open("rb") as stream:
            opened_metadata = os.fstat(stream.fileno())
            if (
                not stat.S_ISREG(opened_metadata.st_mode)
                or _is_name_surrogate_reparse(opened_metadata)
                or _metadata_signature(opened_metadata)
                != _metadata_signature(path_metadata)
            ):
                raise ReplayContractError(
                    f"{label} changed during secure open: {path}"
                )
            raw = stream.read(maximum_bytes + 1)
            final_metadata = os.fstat(stream.fileno())
    except ReplayContractError:
        raise
    except OSError as exc:
        raise ReplayContractError(f"{label} could not be read: {path}: {exc}") from exc

    if len(raw) > maximum_bytes:
        raise ReplayContractError(
            f"{label} exceeds the {maximum_bytes}-byte replay limit: {path}"
        )
    if _metadata_signature(final_metadata) != _metadata_signature(opened_metadata):
        raise ReplayContractError(f"{label} changed while being read: {path}")
    return raw


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKeyError(f"duplicate object key {key!r}")
        result[key] = value
    return result


def _reject_nonfinite_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant {value!r}")


def _validate_json_shape(document: Any, *, label: str) -> None:
    nodes = 0
    stack: list[tuple[Any, int]] = [(document, 1)]
    while stack:
        value, depth = stack.pop()
        nodes += 1
        if nodes > _MAX_JSON_NODES:
            raise ReplayContractError(
                f"{label} exceeds the {_MAX_JSON_NODES}-node JSON limit"
            )
        if depth > _MAX_JSON_DEPTH:
            raise ReplayContractError(
                f"{label} exceeds the {_MAX_JSON_DEPTH}-level JSON depth limit"
            )
        if isinstance(value, float) and not math.isfinite(value):
            raise ReplayContractError(f"{label} contains a non-finite number")
        if isinstance(value, dict):
            stack.extend((item, depth + 1) for item in value.values())
        elif isinstance(value, list):
            stack.extend((item, depth + 1) for item in value)


def _strict_json(raw: bytes, *, label: str) -> Any:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ReplayContractError(f"{label} is not strict UTF-8: {exc}") from exc
    try:
        document = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite_constant,
        )
    except (
        json.JSONDecodeError,
        _DuplicateKeyError,
        RecursionError,
        ValueError,
    ) as exc:
        raise ReplayContractError(f"{label} is not strict JSON: {exc}") from exc
    _validate_json_shape(document, label=label)
    return document


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _planetary_fingerprint_metadata(
    metadata: os.stat_result,
) -> tuple[int, int, int | None, int | None]:
    raw_file_id = getattr(metadata, "st_ino", None)
    raw_device_id = getattr(metadata, "st_dev", None)
    if (
        type(raw_file_id) is int
        and raw_file_id > 0
        and type(raw_device_id) is int
        and raw_device_id >= 0
    ):
        file_id = raw_file_id
        device_id = raw_device_id
    else:
        file_id = None
        device_id = None
    return (
        metadata.st_size,
        metadata.st_mtime_ns,
        device_id,
        file_id,
    )


def _planetary_content_sha256(fingerprint: Any) -> str:
    path = Path(fingerprint.resolved_path)
    expected_metadata = (
        fingerprint.size,
        fingerprint.mtime_ns,
        fingerprint.device_id,
        fingerprint.file_id,
    )
    try:
        resolved = path.resolve(strict=True)
        metadata = resolved.lstat()
    except (OSError, RuntimeError) as exc:
        raise ReplayContractError(
            f"cannot content-bind current planetary resource {path}: {exc}"
        ) from exc
    if (
        not stat.S_ISREG(metadata.st_mode)
        or stat.S_ISLNK(metadata.st_mode)
        or _is_name_surrogate_reparse(metadata)
    ):
        raise ReplayContractError(
            "current planetary resource must be a real regular file: "
            f"{resolved}"
        )
    if (
        os.path.normcase(str(resolved))
        != os.path.normcase(str(path))
        or _planetary_fingerprint_metadata(metadata) != expected_metadata
    ):
        raise ReplayContractError(
            "current planetary resource changed before content hashing: "
            f"{resolved}"
        )

    digest = hashlib.sha256()
    try:
        with resolved.open("rb") as stream:
            opened_metadata = os.fstat(stream.fileno())
            if (
                not stat.S_ISREG(opened_metadata.st_mode)
                or _is_name_surrogate_reparse(opened_metadata)
                or _planetary_fingerprint_metadata(opened_metadata)
                != expected_metadata
            ):
                raise ReplayContractError(
                    "current planetary resource changed during secure open: "
                    f"{resolved}"
                )
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
            final_metadata = os.fstat(stream.fileno())
    except ReplayContractError:
        raise
    except OSError as exc:
        raise ReplayContractError(
            f"cannot hash current planetary resource {resolved}: {exc}"
        ) from exc
    try:
        path_metadata = resolved.lstat()
    except OSError as exc:
        raise ReplayContractError(
            "current planetary resource disappeared after content hashing: "
            f"{resolved}: {exc}"
        ) from exc
    if (
        _planetary_fingerprint_metadata(final_metadata)
        != expected_metadata
        or _planetary_fingerprint_metadata(path_metadata)
        != expected_metadata
    ):
        raise ReplayContractError(
            "current planetary resource changed during content hashing: "
            f"{resolved}"
        )
    return digest.hexdigest()


def _require_object(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ReplayContractError(f"{label} must be a JSON object")
    return value


def _require_schema(document: dict[str, Any], *, label: str) -> None:
    version = document.get("schema_version")
    if type(version) is not int or version != SCHEMA_VERSION:
        raise ReplayContractError(
            f"{label} has unsupported schema_version "
            f"{version!r}"
        )


def _require_run_id(value: Any, *, label: str) -> str:
    if (
        type(value) is not str
        or _RUN_ID_RE.fullmatch(value) is None
        or value.upper() in _WINDOWS_RESERVED_COMPONENTS
    ):
        raise ReplayContractError(
            f"{label} must be a non-reserved portable run ID of 1..64 "
            "ASCII characters"
        )
    return value


def _require_text(
    value: Any,
    *,
    label: str,
    maximum: int = 32 * 1024,
) -> str:
    if type(value) is not str or not value or len(value) > maximum:
        raise ReplayContractError(
            f"{label} must be nonempty text of at most {maximum} characters"
        )
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ReplayContractError(f"{label} contains control characters")
    return value


def _require_digest(value: Any, *, label: str) -> str:
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        raise ReplayContractError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _require_nonnegative_integer(value: Any, *, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ReplayContractError(f"{label} must be a nonnegative integer")
    return value


def _file_receipt(value: Any, *, label: str) -> dict[str, Any]:
    receipt = _require_object(value, label=label)
    if set(receipt) != {"bytes", "sha256"}:
        raise ReplayContractError(
            f"{label} must contain exactly bytes and sha256"
        )
    _require_nonnegative_integer(receipt.get("bytes"), label=f"{label}.bytes")
    _require_digest(receipt.get("sha256"), label=f"{label}.sha256")
    return receipt


def _artifact_receipt(
    artifacts: dict[str, Any],
    *,
    filename: str,
) -> dict[str, Any]:
    if filename not in artifacts:
        raise ReplayContractError(
            f"run.json artifacts must bind the fixed key {filename!r}"
        )
    return _file_receipt(
        artifacts[filename],
        label=f"run.json artifact {filename}",
    )


def _verify_bound_bytes(
    raw: bytes,
    receipt: dict[str, Any],
    *,
    label: str,
) -> None:
    if len(raw) != receipt["bytes"]:
        raise ReplayContractError(
            f"{label} byte length mismatch: receipt={receipt['bytes']}, "
            f"observed={len(raw)}"
        )
    digest = _sha256_bytes(raw)
    if digest != receipt["sha256"]:
        raise ReplayContractError(
            f"{label} SHA-256 mismatch: receipt={receipt['sha256']}, "
            f"observed={digest}"
        )


def _load_receipt_set(
    run_path: Path,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    tuple[str, ...],
]:
    if run_path.name != "run.json":
        raise ReplayContractError("the receipt path must name run.json exactly")
    artifact_dir = run_path.parent
    artifact_metadata = _directory_metadata(
        artifact_dir,
        label="artifact run directory",
    )
    if _path_entry_exists(artifact_dir / "INCOMPLETE"):
        raise ReplayContractError(
            "artifact run is incomplete; INCOMPLETE is still present"
        )
    _assert_completed_receipt_file_set(artifact_dir)
    complete_path = artifact_dir / "COMPLETE"
    if not _path_entry_exists(complete_path):
        raise ReplayContractError(
            "artifact run has no COMPLETE finalization sentinel"
        )

    complete_raw = _stable_file_bytes(
        complete_path,
        maximum_bytes=_MAX_COMPLETE_BYTES,
        label="COMPLETE",
    )
    complete = _require_object(
        _strict_json(complete_raw, label="COMPLETE"),
        label="COMPLETE",
    )
    if set(complete) != {
        "schema_version",
        "run_id",
        "status",
        "run_json",
    }:
        raise ReplayContractError("COMPLETE has an invalid field set")
    _require_schema(complete, label="COMPLETE")
    complete_run_id = _require_run_id(
        complete.get("run_id"),
        label="COMPLETE.run_id",
    )
    if complete.get("status") != "complete":
        raise ReplayContractError("COMPLETE.status must be exactly 'complete'")
    run_binding = _file_receipt(
        complete.get("run_json"),
        label="COMPLETE.run_json",
    )

    run_raw = _stable_file_bytes(
        run_path,
        maximum_bytes=_MAX_RUN_JSON_BYTES,
        label="run.json",
    )
    _verify_bound_bytes(run_raw, run_binding, label="run.json")
    run = _require_object(
        _strict_json(run_raw, label="run.json"),
        label="run.json",
    )
    _require_schema(run, label="run.json")
    run_id = _require_run_id(run.get("run_id"), label="run.json.run_id")
    if complete_run_id != run_id:
        raise ReplayContractError(
            "COMPLETE.run_id contradicts run.json.run_id"
        )
    artifacts = _require_object(
        run.get("artifacts"),
        label="run.json.artifacts",
    )
    if set(artifacts) != set(_ARTIFACT_FILENAMES):
        missing = sorted(set(_ARTIFACT_FILENAMES) - set(artifacts))
        extra = sorted(set(artifacts) - set(_ARTIFACT_FILENAMES))
        raise ReplayContractError(
            "run.json.artifacts must contain exactly the fixed sidecar "
            f"keys; missing={missing!r}, extra={extra!r}"
        )

    sidecar_raw: dict[str, bytes] = {}
    for filename in _ARTIFACT_FILENAMES:
        binding = _artifact_receipt(
            artifacts,
            filename=filename,
        )
        maximum_bytes = {
            "resources.json": _MAX_RESOURCES_JSON_BYTES,
            "rerun-nodeids.json": _MAX_RERUN_NODEIDS_BYTES,
        }.get(filename, _MAX_ARTIFACT_SIDECAR_BYTES)
        raw = _stable_file_bytes(
            artifact_dir / filename,
            maximum_bytes=maximum_bytes,
            label=filename,
        )
        _verify_bound_bytes(raw, binding, label=filename)
        sidecar_raw[filename] = raw

    total_bytes = (
        len(complete_raw)
        + len(run_raw)
        + sum(len(raw) for raw in sidecar_raw.values())
    )
    if total_bytes > _MAX_COMPLETED_RECEIPT_BYTES:
        raise ReplayContractError(
            "completed receipt exceeds the "
            f"{_MAX_COMPLETED_RECEIPT_BYTES}-byte replay limit"
        )

    resources_raw = sidecar_raw["resources.json"]
    resources = _require_object(
        _strict_json(resources_raw, label="resources.json"),
        label="resources.json",
    )
    if set(resources) != {"schema_version", "planetary", "small_body"}:
        raise ReplayContractError("resources.json has an invalid field set")
    _require_schema(resources, label="resources.json")
    _require_object(
        resources.get("planetary"),
        label="resources.json.planetary",
    )
    _require_object(
        resources.get("small_body"),
        label="resources.json.small_body",
    )

    nodeids_raw = sidecar_raw["rerun-nodeids.json"]
    nodeids_document = _require_object(
        _strict_json(nodeids_raw, label="rerun-nodeids.json"),
        label="rerun-nodeids.json",
    )
    if set(nodeids_document) != {"schema_version", "nodeids"}:
        raise ReplayContractError(
            "rerun-nodeids.json must contain exactly schema_version and nodeids"
        )
    _require_schema(nodeids_document, label="rerun-nodeids.json")
    nodeids = _validate_nodeids(nodeids_document.get("nodeids"))

    _assert_directory_unchanged(
        artifact_dir,
        artifact_metadata,
        label="artifact run directory",
    )
    _assert_completed_receipt_file_set(artifact_dir)
    return run, resources, nodeids


def _validate_nodeids(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ReplayContractError("rerun-nodeids.json nodeids must be a list")
    if len(value) > _MAX_NODEIDS:
        raise ReplayContractError(
            f"rerun-nodeids.json exceeds the {_MAX_NODEIDS}-node limit"
        )
    validated: list[str] = []
    seen: set[str] = set()
    for index, raw_nodeid in enumerate(value):
        label = f"rerun-nodeids.json nodeids[{index}]"
        nodeid = _require_text(
            raw_nodeid,
            label=label,
            maximum=_MAX_NODEID_CHARS,
        )
        if any(ord(character) > 126 for character in nodeid):
            raise ReplayContractError(f"{label} must use printable ASCII")
        if nodeid in seen:
            raise ReplayContractError(f"{label} duplicates node ID {nodeid!r}")
        seen.add(nodeid)

        path_text = nodeid.split("::", 1)[0]
        if (
            not path_text
            or path_text.startswith("-")
            or "\\" in path_text
            or ":" in path_text
            or path_text.startswith("/")
            or path_text.endswith("/")
            or "//" in path_text
        ):
            raise ReplayContractError(
                f"{label} has an unsafe or noncanonical test path"
            )
        posix = PurePosixPath(path_text)
        if (
            posix.is_absolute()
            or not posix.parts
            or posix.parts[0] != "tests"
            or len(posix.parts) < 2
            or posix.suffix != ".py"
            or any(part in {"", ".", ".."} for part in posix.parts)
        ):
            raise ReplayContractError(
                f"{label} must identify a relative Python file beneath tests/"
            )
        validated.append(nodeid)
    return tuple(validated)


def _expected_project_python(root: Path) -> Path:
    candidates = (
        root / ".venv" / "Scripts" / "python.exe",
        root / ".venv" / "bin" / "python",
    )
    existing = [candidate for candidate in candidates if candidate.is_file()]
    if len(existing) != 1:
        raise ReplayContractError(
            "repository must contain exactly one platform-appropriate "
            f"project Python executable; found {existing!r}"
        )
    return existing[0].resolve(strict=True)


def _same_file(first: Path, second: Path) -> bool:
    try:
        return first.samefile(second)
    except OSError:
        return (
            os.path.normcase(str(first.resolve(strict=False)))
            == os.path.normcase(str(second.resolve(strict=False)))
        )


def _verify_current_interpreter(root: Path) -> Path:
    expected = _expected_project_python(root)
    try:
        executable = Path(sys.executable).resolve(strict=True)
        prefix = Path(sys.prefix).resolve(strict=True)
        venv_root = (root / ".venv").resolve(strict=True)
    except OSError as exc:
        raise ReplayContractError(
            f"cannot resolve the active project interpreter: {exc}"
        ) from exc
    if not _same_file(executable, expected):
        raise ReplayContractError(
            "replay must run through this repository's .venv interpreter: "
            f"expected {expected}, observed {executable}"
        )
    if not _same_file(prefix, venv_root):
        raise ReplayContractError(
            "active sys.prefix is not this repository's .venv: "
            f"expected {venv_root}, observed {prefix}"
        )
    return expected


def _git_bytes(root: Path, *arguments: str) -> bytes:
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), *arguments],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ReplayContractError(
            f"git {' '.join(arguments)} could not run: {exc}"
        ) from exc
    if completed.returncode != 0:
        diagnostic = completed.stderr.decode("utf-8", errors="replace").strip()
        raise ReplayContractError(
            f"git {' '.join(arguments)} failed with "
            f"{completed.returncode}: {diagnostic}"
        )
    return completed.stdout


def _verify_git_root(root: Path) -> None:
    try:
        observed = Path(
            _git_bytes(root, "rev-parse", "--show-toplevel")
            .decode("utf-8", errors="strict")
            .strip()
        ).resolve(strict=True)
    except (OSError, UnicodeDecodeError) as exc:
        raise ReplayContractError(
            f"cannot resolve the current Git repository root: {exc}"
        ) from exc
    if not _same_file(observed, root.resolve(strict=True)):
        raise ReplayContractError(
            "checked-in replay script is not running from its owning Git "
            f"repository: script={root}, git={observed}"
        )


def _untracked_content_digest(root: Path) -> tuple[str, int]:
    raw_paths = _git_bytes(
        root,
        "ls-files",
        "--others",
        "--exclude-standard",
        "-z",
    )
    try:
        relative_paths = sorted(
            path
            for path in raw_paths.decode("utf-8", errors="strict").split("\0")
            if path
        )
    except UnicodeDecodeError as exc:
        raise ReplayContractError(
            f"Git returned a non-UTF-8 untracked path: {exc}"
        ) from exc

    digest = hashlib.sha256()
    for relative in relative_paths:
        posix = PurePosixPath(relative)
        if (
            posix.is_absolute()
            or any(part in {"", ".", ".."} for part in posix.parts)
        ):
            raise ReplayContractError(
                f"Git returned unsafe untracked path {relative!r}"
            )
        path = root.joinpath(*posix.parts)
        try:
            metadata = path.lstat()
        except OSError as exc:
            raise ReplayContractError(
                f"cannot inspect untracked path {relative!r}: {exc}"
            ) from exc
        encoded_path = relative.encode("utf-8")
        digest.update(len(encoded_path).to_bytes(8, "big"))
        digest.update(encoded_path)
        if stat.S_ISLNK(metadata.st_mode):
            target = os.readlink(path).encode("utf-8")
            digest.update(b"symlink\0")
            digest.update(len(target).to_bytes(8, "big"))
            digest.update(target)
            final_metadata = path.lstat()
            if (
                final_metadata.st_size != metadata.st_size
                or final_metadata.st_mtime_ns != metadata.st_mtime_ns
                or final_metadata.st_dev != metadata.st_dev
                or final_metadata.st_ino != metadata.st_ino
            ):
                raise ReplayContractError(
                    f"untracked symlink changed while hashing: {relative}"
                )
        elif stat.S_ISREG(metadata.st_mode):
            digest.update(b"file\0")
            digest.update(metadata.st_size.to_bytes(8, "big"))
            with path.open("rb") as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(chunk)
                opened_metadata = os.fstat(source.fileno())
            if (
                opened_metadata.st_size != metadata.st_size
                or opened_metadata.st_mtime_ns != metadata.st_mtime_ns
                or opened_metadata.st_dev != metadata.st_dev
                or opened_metadata.st_ino != metadata.st_ino
            ):
                raise ReplayContractError(
                    f"untracked file changed while hashing: {relative}"
                )
        else:
            raise ReplayContractError(
                "untracked path is not a regular file or symlink: "
                f"{relative}"
            )
    return digest.hexdigest(), len(relative_paths)


def _current_git_identity(root: Path) -> dict[str, Any]:
    try:
        repository_root = Path(
            _git_bytes(root, "rev-parse", "--show-toplevel")
            .decode("utf-8", errors="strict")
            .strip()
        ).resolve(strict=True)
        head = (
            _git_bytes(root, "rev-parse", "HEAD")
            .decode("ascii", errors="strict")
            .strip()
        )
        tracked_diff = _git_bytes(
            root,
            "diff",
            "--binary",
            "--no-ext-diff",
            "--no-textconv",
            "HEAD",
            "--",
        )
        untracked_digest, untracked_count = _untracked_content_digest(root)
    except Exception as exc:
        return {
            "available": False,
            "error": f"{type(exc).__name__}: {exc}",
        }
    return {
        "available": True,
        "repository_root": str(repository_root),
        "head": head,
        "tracked_diff_sha256": _sha256_bytes(tracked_diff),
        "untracked_content_sha256": untracked_digest,
        "untracked_count": untracked_count,
    }


def _current_interpreter_identity(root: Path) -> dict[str, Any]:
    executable = Path(sys.executable).resolve(strict=True)
    prefix = Path(sys.prefix).resolve(strict=True)
    project_python = _expected_project_python(root)
    return {
        "executable": str(executable),
        "prefix": str(prefix),
        "implementation": platform.python_implementation(),
        "version": platform.python_version(),
        "project_venv_executable": str(project_python),
        "is_project_venv": _same_file(executable, project_python),
    }


def _ensure_repository_import_path(root: Path) -> None:
    root_text = str(root)
    tests_text = str(root / "tests")
    for entry in (root_text, tests_text):
        while entry in sys.path:
            sys.path.remove(entry)
    sys.path.insert(0, root_text)
    sys.path.insert(1, tests_text)
    for name, module in list(sys.modules.items()):
        if not (
            name == "moira"
            or name.startswith("moira.")
            or name == "support"
            or name.startswith("support.")
        ):
            continue
        module_file = getattr(module, "__file__", None)
        if module_file is None:
            sys.modules.pop(name, None)
            continue
        try:
            owned = Path(module_file).resolve(strict=True).is_relative_to(root)
        except (OSError, RuntimeError, TypeError, ValueError):
            owned = False
        if not owned:
            sys.modules.pop(name, None)


def _current_native_identity(root: Path) -> dict[str, Any]:
    try:
        _ensure_repository_import_path(root)
        import moira
        from moira._native_build_provenance import (
            native_backend_binary_identity,
            native_build_provenance_identity,
        )

        package_path = Path(moira.__file__).resolve(strict=True)
        binary_identity = native_backend_binary_identity(
            import_module("moira._moira_native")
        )
        embedded_sha256 = binary_identity.pop("embedded_input_sha256")
        backend_path = Path(str(binary_identity["backend_path"]))
        resolved_root = root.resolve(strict=True)
        return {
            "available": True,
            "moira_version": str(moira.__version__),
            "package_path": str(package_path),
            "package_under_repository": package_path.is_relative_to(
                resolved_root
            ),
            **binary_identity,
            "backend_under_repository": backend_path.is_relative_to(
                resolved_root
            ),
            "build_provenance": native_build_provenance_identity(
                resolved_root,
                embedded_sha256,
            ),
        }
    except Exception as exc:
        return {
            "available": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


def _lexical_path_key(value: str) -> str:
    return os.path.normcase(os.path.normpath(value))


def _path_comparison_key(path_value: Any, root_value: Any) -> str:
    path_text = _require_text(path_value, label="recorded path")
    root_text = _require_text(root_value, label="recorded repository root")
    path = Path(os.path.normpath(path_text))
    root = Path(os.path.normpath(root_text))
    try:
        relative = path.relative_to(root)
    except ValueError:
        return "absolute:" + _lexical_path_key(str(path))
    return "repository:" + relative.as_posix()


def _repository_matches(recorded_root: str, current_root: Path) -> bool:
    recorded = Path(recorded_root)
    if not recorded.is_absolute():
        raise ReplayContractError(
            "run.json repository.root must be an absolute path"
        )
    return _lexical_path_key(recorded_root) == _lexical_path_key(
        str(current_root)
    )


def _validate_recorded_git(value: Any) -> dict[str, Any]:
    git = _require_object(value, label="run.json.repository.git")
    available = git.get("available")
    if type(available) is not bool:
        raise ReplayContractError(
            "run.json.repository.git.available must be true or false"
        )
    if not available:
        _require_text(
            git.get("error"),
            label="run.json.repository.git.error",
        )
        return git
    _require_text(
        git.get("repository_root"),
        label="run.json.repository.git.repository_root",
    )
    head = git.get("head")
    if type(head) is not str or _GIT_OBJECT_RE.fullmatch(head) is None:
        raise ReplayContractError(
            "run.json.repository.git.head must be a full Git object ID"
        )
    _require_digest(
        git.get("tracked_diff_sha256"),
        label="run.json.repository.git.tracked_diff_sha256",
    )
    _require_digest(
        git.get("untracked_content_sha256"),
        label="run.json.repository.git.untracked_content_sha256",
    )
    _require_nonnegative_integer(
        git.get("untracked_count"),
        label="run.json.repository.git.untracked_count",
    )
    return git


def _compare_git(
    recorded: dict[str, Any],
    current: dict[str, Any],
    *,
    recorded_root: str,
    current_root: Path,
) -> list[str]:
    if not recorded.get("available"):
        return ["receipt Git identity was unavailable"]
    if not current.get("available"):
        return [f"current Git identity unavailable: {current.get('error')}"]
    differences: list[str] = []
    if recorded["head"] != current["head"]:
        differences.append(
            f"HEAD {recorded['head']} -> {current['head']}"
        )
    for field, label in (
        ("tracked_diff_sha256", "tracked diff"),
        ("untracked_content_sha256", "untracked content"),
        ("untracked_count", "untracked count"),
    ):
        if recorded[field] != current[field]:
            differences.append(
                f"{label} {recorded[field]} -> {current[field]}"
            )
    recorded_git_root = _path_comparison_key(
        recorded["repository_root"],
        recorded_root,
    )
    current_git_root = _path_comparison_key(
        current["repository_root"],
        str(current_root),
    )
    if recorded_git_root != current_git_root:
        differences.append(
            f"Git root {recorded_git_root} -> {current_git_root}"
        )
    return differences


def _validate_recorded_interpreter(value: Any) -> dict[str, Any]:
    interpreter = _require_object(value, label="run.json.interpreter")
    for field in (
        "executable",
        "prefix",
        "implementation",
        "version",
        "project_venv_executable",
    ):
        _require_text(
            interpreter.get(field),
            label=f"run.json.interpreter.{field}",
        )
    if type(interpreter.get("is_project_venv")) is not bool:
        raise ReplayContractError(
            "run.json.interpreter.is_project_venv must be true or false"
        )
    return interpreter


def _compare_interpreter(
    recorded: dict[str, Any],
    current: dict[str, Any],
    *,
    repository_matches: bool,
) -> list[str]:
    differences: list[str] = []
    if recorded["is_project_venv"] is not True:
        differences.append("receipt was not produced by its project .venv")
    for field in ("implementation", "version"):
        if recorded[field] != current[field]:
            differences.append(
                f"{field} {recorded[field]!r} -> {current[field]!r}"
            )
    if repository_matches:
        for field in ("executable", "prefix", "project_venv_executable"):
            recorded_path = _lexical_path_key(recorded[field])
            current_path = _lexical_path_key(current[field])
            if recorded_path != current_path:
                differences.append(
                    f"{field} {recorded[field]!r} -> {current[field]!r}"
                )
    return differences


def _validate_recorded_native(value: Any) -> dict[str, Any]:
    native = _require_object(value, label="run.json.native")
    available = native.get("available")
    if type(available) is not bool:
        raise ReplayContractError(
            "run.json.native.available must be true or false"
        )
    if not available:
        _require_text(native.get("error"), label="run.json.native.error")
        return native
    for field in ("moira_version", "package_path", "backend_path"):
        _require_text(native.get(field), label=f"run.json.native.{field}")
    if "backend_loader" in native or "backend_module" in native:
        for field in ("backend_loader", "backend_module"):
            _require_text(native.get(field), label=f"run.json.native.{field}")
    if "backend_loader_path" in native:
        _require_text(
            native.get("backend_loader_path"),
            label="run.json.native.backend_loader_path",
        )
        if native["backend_loader_path"] != native["backend_path"]:
            raise ReplayContractError(
                "run.json.native backend path is not loader-owned"
            )
    for field in ("package_under_repository", "backend_under_repository"):
        if type(native.get(field)) is not bool:
            raise ReplayContractError(
                f"run.json.native.{field} must be true or false"
            )
    _require_nonnegative_integer(
        native.get("backend_size"),
        label="run.json.native.backend_size",
    )
    _require_digest(
        native.get("backend_sha256"),
        label="run.json.native.backend_sha256",
    )
    if "build_provenance" in native:
        provenance = _require_object(
            native.get("build_provenance"),
            label="run.json.native.build_provenance",
        )
        if set(provenance) != {
            "current_input_manifest",
            "embedded_input_sha256",
            "error",
            "matches_current_inputs",
            "schema_version",
        }:
            raise ReplayContractError(
                "run.json.native.build_provenance fields are not exact"
            )
        if provenance.get("schema_version") not in {1, 2}:
            raise ReplayContractError(
                "run.json.native.build_provenance schema is unsupported"
            )
        embedded = provenance.get("embedded_input_sha256")
        if embedded is not None:
            _require_digest(
                embedded,
                label=(
                    "run.json.native.build_provenance."
                    "embedded_input_sha256"
                ),
            )
        if type(provenance.get("matches_current_inputs")) is not bool:
            raise ReplayContractError(
                "run.json.native.build_provenance match flag must be boolean"
            )
        error = provenance.get("error")
        if error is not None:
            _require_text(
                error,
                label="run.json.native.build_provenance.error",
            )
    return native


def _compare_native(
    recorded: dict[str, Any],
    current: dict[str, Any],
    *,
    recorded_root: str,
    current_root: Path,
) -> list[str]:
    if not recorded.get("available"):
        return ["receipt native identity was unavailable"]
    if not current.get("available"):
        return [f"current native identity unavailable: {current.get('error')}"]
    differences: list[str] = []
    for field, label in (
        ("moira_version", "Moira version"),
        ("backend_size", "backend size"),
        ("backend_sha256", "backend SHA-256"),
        ("package_under_repository", "package locality"),
        ("backend_under_repository", "backend locality"),
    ):
        if recorded[field] != current[field]:
            differences.append(
                f"{label} {recorded[field]!r} -> {current[field]!r}"
            )
    for field, label in (
        ("backend_loader", "backend loader"),
        ("backend_module", "backend module"),
    ):
        if field in recorded and recorded[field] != current.get(field):
            differences.append(
                f"{label} {recorded[field]!r} -> {current.get(field)!r}"
            )
    for field, label in (
        ("package_path", "package path"),
        ("backend_path", "backend path"),
        ("backend_loader_path", "backend loader path"),
    ):
        if field not in recorded:
            continue
        recorded_key = _path_comparison_key(recorded[field], recorded_root)
        current_key = _path_comparison_key(current[field], str(current_root))
        if recorded_key != current_key:
            differences.append(
                f"{label} {recorded_key!r} -> {current_key!r}"
            )
    if "build_provenance" in recorded and recorded["build_provenance"] != (
        current.get("build_provenance")
    ):
        differences.append("native build provenance changed")
    return differences


def _candidate_signature(
    candidate: Any,
    *,
    repository_root: str,
) -> dict[str, Any] | None:
    if candidate is None:
        return None
    value = _require_object(candidate, label="planetary candidate")
    if set(value) != {"path", "explicit", "source", "fingerprint"}:
        raise ReplayContractError(
            "planetary candidate must contain exactly path, explicit, "
            "source, and fingerprint"
        )
    signature: dict[str, Any] = {
        "path": _path_comparison_key(value.get("path"), repository_root),
        "source": _require_text(
            value.get("source"),
            label="planetary candidate source",
        ),
        "explicit": value.get("explicit"),
        "fingerprint": None,
    }
    if type(signature["explicit"]) is not bool:
        raise ReplayContractError(
            "planetary candidate explicit must be true or false"
        )
    fingerprint = value.get("fingerprint")
    if fingerprint is not None:
        fingerprint = _require_object(
            fingerprint,
            label="planetary candidate fingerprint",
        )
        if set(fingerprint) != {
            "resolved_path",
            "size",
            "mtime_ns",
            "device_id",
            "file_id",
            "content_sha256",
        }:
            raise ReplayContractError(
                "planetary candidate fingerprint has an invalid field set"
            )
        normalized: dict[str, Any] = {
            "resolved_path": _path_comparison_key(
                fingerprint.get("resolved_path"),
                repository_root,
            ),
        }
        for field in ("size", "mtime_ns"):
            normalized[field] = _require_nonnegative_integer(
                fingerprint.get(field),
                label=f"planetary candidate fingerprint {field}",
            )
        for field in ("device_id", "file_id"):
            raw = fingerprint.get(field)
            if raw is not None:
                raw = _require_nonnegative_integer(
                    raw,
                    label=f"planetary candidate fingerprint {field}",
                )
            normalized[field] = raw
        if (normalized["device_id"] is None) != (
            normalized["file_id"] is None
        ):
            raise ReplayContractError(
                "planetary candidate fingerprint device_id and file_id "
                "must be present together"
            )
        normalized["content_sha256"] = _require_digest(
            fingerprint.get("content_sha256"),
            label="planetary candidate fingerprint content_sha256",
        )
        signature["fingerprint"] = normalized
    return signature


def _capability_signature(capability: Any) -> dict[str, Any] | None:
    if capability is None:
        return None
    value = _require_object(capability, label="planetary capability")
    expected_fields = {
        "product",
        "content_identity",
        "summary_label",
        "planetary_ephemeris",
        "lunar_ephemeris",
        "segments",
        "bodies",
        "target_center_pairs",
        "frames",
        "segment_types",
        "native_capability",
    }
    if set(value) != expected_fields:
        raise ReplayContractError(
            "planetary capability has an invalid field set"
        )

    def optional_text(raw: Any, *, label: str) -> str | None:
        if raw is None:
            return None
        return _require_text(raw, label=label)

    def integer(raw: Any, *, label: str) -> int:
        if type(raw) is not int:
            raise ReplayContractError(f"{label} must be an integer")
        return raw

    def finite_number(raw: Any, *, label: str) -> int | float:
        if type(raw) not in {int, float} or not math.isfinite(raw):
            raise ReplayContractError(f"{label} must be a finite number")
        return raw

    segments_raw = value.get("segments")
    if not isinstance(segments_raw, list):
        raise ReplayContractError("planetary capability segments must be a list")
    if not segments_raw:
        raise ReplayContractError(
            "planetary capability segments must not be empty"
        )
    segments: list[dict[str, Any]] = []
    for index, raw_segment in enumerate(segments_raw):
        label = f"planetary capability segments[{index}]"
        segment = _require_object(raw_segment, label=label)
        if set(segment) != {
            "target_naif_id",
            "center_naif_id",
            "frame",
            "segment_type",
            "start_jd",
            "end_jd",
        }:
            raise ReplayContractError(f"{label} has an invalid field set")
        start_jd = finite_number(
            segment.get("start_jd"),
            label=f"{label}.start_jd",
        )
        end_jd = finite_number(
            segment.get("end_jd"),
            label=f"{label}.end_jd",
        )
        if end_jd < start_jd:
            raise ReplayContractError(
                f"{label}.end_jd must not precede start_jd"
            )
        segment_type = integer(
            segment.get("segment_type"),
            label=f"{label}.segment_type",
        )
        if segment_type <= 0:
            raise ReplayContractError(
                f"{label}.segment_type must be positive"
            )
        segments.append(
            {
                "target_naif_id": integer(
                    segment.get("target_naif_id"),
                    label=f"{label}.target_naif_id",
                ),
                "center_naif_id": integer(
                    segment.get("center_naif_id"),
                    label=f"{label}.center_naif_id",
                ),
                "frame": integer(
                    segment.get("frame"),
                    label=f"{label}.frame",
                ),
                "segment_type": segment_type,
                "start_jd": start_jd,
                "end_jd": end_jd,
            }
        )

    routes_raw = value.get("target_center_pairs")
    if not isinstance(routes_raw, list):
        raise ReplayContractError(
            "planetary capability target_center_pairs must be a list"
        )
    routes: list[dict[str, int]] = []
    for index, raw_route in enumerate(routes_raw):
        label = f"planetary capability target_center_pairs[{index}]"
        route = _require_object(raw_route, label=label)
        if set(route) != {"target_naif_id", "center_naif_id"}:
            raise ReplayContractError(f"{label} has an invalid field set")
        routes.append(
            {
                "target_naif_id": integer(
                    route.get("target_naif_id"),
                    label=f"{label}.target_naif_id",
                ),
                "center_naif_id": integer(
                    route.get("center_naif_id"),
                    label=f"{label}.center_naif_id",
                ),
            }
        )

    route_pairs = [
        (route["target_naif_id"], route["center_naif_id"])
        for route in routes
    ]
    if route_pairs != sorted(set(route_pairs)):
        raise ReplayContractError(
            "planetary capability target_center_pairs must be sorted "
            "and unique"
        )

    def integer_list(field: str, *, positive: bool = False) -> list[int]:
        raw_values = value.get(field)
        if not isinstance(raw_values, list):
            raise ReplayContractError(
                f"planetary capability {field} must be a list"
            )
        values = [
            integer(
                raw,
                label=f"planetary capability {field}[{index}]",
            )
            for index, raw in enumerate(raw_values)
        ]
        if positive and any(raw <= 0 for raw in values):
            raise ReplayContractError(
                f"planetary capability {field} must contain positive integers"
            )
        if values != sorted(set(values)):
            raise ReplayContractError(
                f"planetary capability {field} must be sorted and unique"
            )
        return values

    signature = {
        "product": _require_text(
            value.get("product"),
            label="planetary capability product",
        ),
        "content_identity": _require_text(
            value.get("content_identity"),
            label="planetary capability content identity",
        ),
        "summary_label": _require_text(
            value.get("summary_label"),
            label="planetary capability summary label",
        ),
        "planetary_ephemeris": optional_text(
            value.get("planetary_ephemeris"),
            label="planetary capability planetary ephemeris",
        ),
        "lunar_ephemeris": optional_text(
            value.get("lunar_ephemeris"),
            label="planetary capability lunar ephemeris",
        ),
        "segments": segments,
        "bodies": integer_list("bodies"),
        "target_center_pairs": routes,
        "frames": integer_list("frames"),
        "segment_types": integer_list("segment_types", positive=True),
        "native_capability": value.get("native_capability"),
    }
    if type(signature["native_capability"]) is not bool:
        raise ReplayContractError(
            "planetary capability native_capability must be true or false"
        )
    expected_identity = (
        signature["planetary_ephemeris"] or signature["summary_label"]
    )
    if signature["content_identity"] != expected_identity:
        raise ReplayContractError(
            "planetary capability content_identity contradicts its "
            "ephemeris or summary identity"
        )
    if signature["bodies"] != sorted(
        {segment["target_naif_id"] for segment in segments}
    ):
        raise ReplayContractError(
            "planetary capability bodies contradict segment descriptors"
        )
    if route_pairs != sorted(
        {
            (segment["target_naif_id"], segment["center_naif_id"])
            for segment in segments
        }
    ):
        raise ReplayContractError(
            "planetary capability routes contradict segment descriptors"
        )
    if signature["frames"] != sorted(
        {segment["frame"] for segment in segments}
    ):
        raise ReplayContractError(
            "planetary capability frames contradict segment descriptors"
        )
    if signature["segment_types"] != sorted(
        {segment["segment_type"] for segment in segments}
    ):
        raise ReplayContractError(
            "planetary capability segment_types contradict segment "
            "descriptors"
        )
    return signature


def _expected_planetary_signature(
    report: dict[str, Any],
    *,
    repository_root: str,
) -> dict[str, Any]:
    if set(report) != {"version", "summary", "details", "probe_count"}:
        raise ReplayContractError(
            "resources.json.planetary has an invalid field set"
        )
    if (
        type(report.get("version")) is not int
        or report.get("version") != SCHEMA_VERSION
    ):
        raise ReplayContractError(
            "resources.json.planetary has unsupported version"
        )
    _require_nonnegative_integer(
        report.get("probe_count"),
        label="resources.json.planetary.probe_count",
    )
    details = _require_object(
        report.get("details"),
        label="resources.json.planetary.details",
    )
    if len(details) > _MAX_RESOURCE_REQUIREMENTS:
        raise ReplayContractError(
            "resources.json declares too many planetary resource receipts"
        )
    summary = _require_object(
        report.get("summary"),
        label="resources.json.planetary.summary",
    )
    if set(summary) != {"receipts", "run", "skip", "failure", "identities"}:
        raise ReplayContractError(
            "resources.json.planetary.summary has an invalid field set"
        )
    receipt_count = _require_nonnegative_integer(
        summary.get("receipts"),
        label="resources.json.planetary.summary.receipts",
    )
    if receipt_count != len(details):
        raise ReplayContractError(
            "resources.json.planetary summary receipt count contradicts details"
        )
    identities_raw = summary.get("identities")
    if not isinstance(identities_raw, list) or any(
        type(identity) is not str for identity in identities_raw
    ):
        raise ReplayContractError(
            "resources.json.planetary.summary.identities must be a text list"
        )
    identities = sorted(set(identities_raw))
    if identities_raw != identities:
        raise ReplayContractError(
            "resources.json.planetary.summary.identities must be sorted "
            "and unique"
        )
    receipts: list[dict[str, Any]] = []
    derived_identities: set[str] = set()
    disposition_counts = {"run": 0, "skip": 0, "failure": 0}
    distinct_requirements: set[str] = set()
    for nodeid, raw_detail in sorted(details.items()):
        _require_text(nodeid, label="planetary detail node ID")
        detail = _require_object(
            raw_detail,
            label=f"planetary detail {nodeid}",
        )
        expected_detail_fields = {
            "disposition",
            "identity",
            "requirement",
            "candidate",
            "capability",
            "reason",
            "failure_type",
            "rendered",
        }
        if set(detail) != expected_detail_fields:
            raise ReplayContractError(
                f"planetary detail {nodeid} has an invalid field set"
            )
        disposition = detail.get("disposition")
        if disposition not in disposition_counts:
            raise ReplayContractError(
                f"planetary detail {nodeid} has an invalid disposition"
            )
        disposition_counts[disposition] += 1
        identity = detail.get("identity")
        if identity is not None:
            identity = _require_text(
                identity,
                label=f"planetary detail {nodeid} identity",
            )
            derived_identities.add(identity)
        requirement = _require_object(
            detail.get("requirement"),
            label=f"planetary detail {nodeid} requirement",
        )
        distinct_requirements.add(
            json.dumps(
                requirement,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        candidate = _candidate_signature(
            detail.get("candidate"),
            repository_root=repository_root,
        )
        capability = _capability_signature(detail.get("capability"))
        failure_type = detail.get("failure_type")
        if failure_type is not None:
            failure_type = _require_text(
                failure_type,
                label=f"planetary detail {nodeid} failure type",
            )
        _require_text(
            detail.get("reason"),
            label=f"planetary detail {nodeid} reason",
        )
        _require_text(
            detail.get("rendered"),
            label=f"planetary detail {nodeid} rendered evidence",
        )
        if disposition == "run" and (
            identity is None
            or candidate is None
            or candidate["fingerprint"] is None
            or capability is None
            or failure_type is not None
        ):
            raise ReplayContractError(
                f"planetary detail {nodeid} has incomplete run evidence"
            )
        if (capability is None) != (identity is None):
            raise ReplayContractError(
                f"planetary detail {nodeid} identity/capability presence "
                "contradicts"
            )
        if capability is not None and (
            candidate is None or candidate["fingerprint"] is None
        ):
            raise ReplayContractError(
                f"planetary detail {nodeid} capability lacks fingerprinted "
                "candidate"
            )
        if disposition == "skip" and failure_type is not None:
            raise ReplayContractError(
                f"planetary detail {nodeid} skip declares a failure type"
            )
        if disposition == "failure" and failure_type is None:
            raise ReplayContractError(
                f"planetary detail {nodeid} failure lacks a failure type"
            )
        if capability is not None and identity != capability["content_identity"]:
            raise ReplayContractError(
                f"planetary detail {nodeid} identity contradicts capability"
            )
        receipts.append(
            {
                "disposition": disposition,
                "identity": identity,
                "requirement": requirement,
                "candidate": candidate,
                "capability": capability,
                "failure_type": failure_type,
            }
        )
    if len(distinct_requirements) > _MAX_DISTINCT_RESOURCE_REQUIREMENTS:
        raise ReplayContractError(
            "resources.json declares too many distinct planetary requirements"
        )
    if identities != sorted(derived_identities):
        raise ReplayContractError(
            "resources.json.planetary summary identities contradict details"
        )
    for disposition, count in disposition_counts.items():
        if _require_nonnegative_integer(
            summary.get(disposition),
            label=f"resources.json.planetary.summary.{disposition}",
        ) != count:
            raise ReplayContractError(
                "resources.json.planetary summary disposition counts "
                "contradict details"
            )
    return {
        "used": receipt_count > 0,
        "receipts": receipts,
    }


def _serialize_current_candidate(
    candidate: Any,
    *,
    repository_root: Path,
    content_digests: dict[tuple[Any, ...], str],
) -> dict[str, Any] | None:
    if candidate is None:
        return None
    fingerprint = candidate.fingerprint
    fingerprint_key = (
        None
        if fingerprint is None
        else (
            str(fingerprint.resolved_path),
            fingerprint.size,
            fingerprint.mtime_ns,
            fingerprint.device_id,
            fingerprint.file_id,
        )
    )
    content_sha256 = None
    if fingerprint is not None:
        assert fingerprint_key is not None
        content_sha256 = content_digests.get(fingerprint_key)
        if content_sha256 is None:
            content_sha256 = _planetary_content_sha256(fingerprint)
            content_digests[fingerprint_key] = content_sha256
    return {
        "path": _path_comparison_key(
            str(candidate.path),
            str(repository_root),
        ),
        "source": str(candidate.source),
        "explicit": bool(candidate.explicit),
        "fingerprint": (
            None
            if fingerprint is None
            else {
                "resolved_path": _path_comparison_key(
                    str(fingerprint.resolved_path),
                    str(repository_root),
                ),
                "size": fingerprint.size,
                "mtime_ns": fingerprint.mtime_ns,
                "device_id": fingerprint.device_id,
                "file_id": fingerprint.file_id,
                "content_sha256": content_sha256,
            }
        ),
    }


def _serialize_current_capability(capability: Any) -> dict[str, Any] | None:
    if capability is None:
        return None
    return _capability_signature(
        {
            "product": capability.product,
            "content_identity": capability.content_identity,
            "summary_label": capability.summary_label,
            "planetary_ephemeris": capability.planetary_ephemeris,
            "lunar_ephemeris": capability.lunar_ephemeris,
            "segments": [
                {
                    "target_naif_id": segment.route.target_naif_id,
                    "center_naif_id": segment.route.center_naif_id,
                    "frame": segment.frame,
                    "segment_type": segment.segment_type,
                    "start_jd": segment.start_jd,
                    "end_jd": segment.end_jd,
                }
                for segment in capability.segments
            ],
            "bodies": sorted(capability.bodies),
            "target_center_pairs": [
                {
                    "target_naif_id": route.target_naif_id,
                    "center_naif_id": route.center_naif_id,
                }
                for route in sorted(capability.target_center_pairs)
            ],
            "frames": sorted(capability.frames),
            "segment_types": sorted(capability.segment_types),
            "native_capability": capability.native_capability,
        }
    )


def _requirement_reconstruction_mapping(
    serialized: dict[str, Any],
) -> dict[str, Any]:
    generic_shape = {
        "product": "planetary-spk",
        "content_identity": None,
        "interval": None,
        "bodies": [],
        "target_center_pairs": [],
        "frame": None,
        "segment_types": [],
        "native_capability": None,
    }
    if serialized == generic_shape:
        return {"generic": True}
    return serialized


def _current_planetary_signature(
    expected: dict[str, Any],
    *,
    repository_root: Path,
) -> dict[str, Any]:
    if not expected["used"]:
        return {
            "used": False,
            "receipts": [],
        }
    try:
        from support import resource_policy

        candidate = resource_policy.discover_planetary_kernel_candidate()
        resolver = resource_policy.PlanetaryResourceResolver(candidate)
        cached: dict[str, dict[str, Any]] = {}
        content_digests: dict[tuple[Any, ...], str] = {}
        receipts: list[dict[str, Any]] = []
        for expected_receipt in expected["receipts"]:
            requirement_mapping = expected_receipt["requirement"]
            key = json.dumps(
                requirement_mapping,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            current = cached.get(key)
            if current is None:
                requirement = (
                    resource_policy.PlanetaryKernelRequirement.from_mapping(
                        _requirement_reconstruction_mapping(
                            requirement_mapping
                        )
                    )
                )
                receipt = resolver.resolve(requirement)
                current_capability = _serialize_current_capability(
                    receipt.capability
                )
                current = {
                    "disposition": receipt.disposition.value,
                    "identity": (
                        None
                        if current_capability is None
                        else current_capability["content_identity"]
                    ),
                    "requirement": requirement_mapping,
                    "candidate": _serialize_current_candidate(
                        receipt.candidate,
                        repository_root=repository_root,
                        content_digests=content_digests,
                    ),
                    "capability": current_capability,
                    "failure_type": receipt.failure_type,
                }
                cached[key] = current
            receipts.append(current)
        return {
            "used": True,
            "receipts": receipts,
        }
    except Exception as exc:
        return {
            "used": True,
            "error": f"{type(exc).__name__}: {exc}",
        }


def _small_body_capability_signature(
    capability: Any,
    *,
    repository_root: str,
) -> dict[str, Any]:
    value = _require_object(capability, label="small-body capability")
    expected_fields = {
        "manifest_path",
        "manifest_sha256",
        "manifest_schema",
        "catalog_id",
        "catalog_version",
        "released_utc",
        "source_manifest_sha256",
        "source_revision",
        "integrity_algorithm",
        "integrity_receipt",
        "integrity_scope",
        "shard_count",
        "declared_body_count",
        "bodies",
        "coverage",
        "segment_types",
        "frames",
        "native_catalog",
        "native_segment_types",
        "identity",
    }
    if set(value) != expected_fields:
        raise ReplayContractError(
            "small-body capability has an invalid field set"
        )
    manifest_path = _require_text(
        value.get("manifest_path"),
        label="small-body manifest path",
    )
    manifest_sha256 = _require_digest(
        value.get("manifest_sha256"),
        label="small-body manifest SHA-256",
    )
    catalog_id = _require_text(
        value.get("catalog_id"),
        label="small-body catalog ID",
    )
    catalog_version = _require_text(
        value.get("catalog_version"),
        label="small-body catalog version",
    )
    identity = _require_text(
        value.get("identity"),
        label="small-body capability identity",
    )
    expected_identity = f"{catalog_id}@{catalog_version}:{manifest_sha256}"
    if identity != expected_identity:
        raise ReplayContractError(
            "small-body capability identity contradicts its manifest fields"
        )

    def positive_integer(raw: Any, *, label: str) -> int:
        if type(raw) is not int or raw < 1:
            raise ReplayContractError(f"{label} must be a positive integer")
        return raw

    def sorted_unique_positive_integers(
        raw: Any,
        *,
        label: str,
    ) -> list[int]:
        if not isinstance(raw, list):
            raise ReplayContractError(f"{label} must be a list")
        values = [
            positive_integer(item, label=f"{label}[{index}]")
            for index, item in enumerate(raw)
        ]
        if values != sorted(set(values)):
            raise ReplayContractError(f"{label} must be sorted and unique")
        return values

    shard_count = positive_integer(
        value.get("shard_count"),
        label="small-body capability shard_count",
    )
    declared_body_count = positive_integer(
        value.get("declared_body_count"),
        label="small-body capability declared_body_count",
    )
    bodies = sorted_unique_positive_integers(
        value.get("bodies"),
        label="small-body capability bodies",
    )
    if len(bodies) != declared_body_count:
        raise ReplayContractError(
            "small-body capability bodies contradict declared_body_count"
        )
    coverage_raw = value.get("coverage")
    if not isinstance(coverage_raw, list):
        raise ReplayContractError(
            "small-body capability coverage must be a list"
        )
    coverage: list[list[int | float]] = []
    for index, raw_interval in enumerate(coverage_raw):
        label = f"small-body capability coverage[{index}]"
        if not isinstance(raw_interval, list) or len(raw_interval) != 4:
            raise ReplayContractError(
                f"{label} must be [center, target, start_jd, end_jd]"
            )
        center, target, start_jd, end_jd = raw_interval
        if type(center) is not int:
            raise ReplayContractError(f"{label}[0] must be an integer")
        target = positive_integer(target, label=f"{label}[1]")
        if (
            type(start_jd) not in {int, float}
            or type(end_jd) not in {int, float}
            or not math.isfinite(start_jd)
            or not math.isfinite(end_jd)
            or end_jd < start_jd
        ):
            raise ReplayContractError(
                f"{label} must contain a finite ordered interval"
            )
        coverage.append([center, target, start_jd, end_jd])
    segment_types = sorted_unique_positive_integers(
        value.get("segment_types"),
        label="small-body capability segment_types",
    )
    frames = sorted_unique_positive_integers(
        value.get("frames"),
        label="small-body capability frames",
    )
    native_segment_types = sorted_unique_positive_integers(
        value.get("native_segment_types"),
        label="small-body capability native_segment_types",
    )
    if sorted({int(interval[1]) for interval in coverage}) != bodies:
        raise ReplayContractError(
            "small-body capability bodies contradict coverage descriptors"
        )
    native_catalog = value.get("native_catalog")
    if type(native_catalog) is not bool:
        raise ReplayContractError(
            "small-body capability native_catalog must be true or false"
        )
    return {
        "manifest_path": _path_comparison_key(
            manifest_path,
            repository_root,
        ),
        "manifest_sha256": manifest_sha256,
        "manifest_schema": _require_text(
            value.get("manifest_schema"),
            label="small-body manifest schema",
        ),
        "catalog_id": catalog_id,
        "catalog_version": catalog_version,
        "released_utc": _require_text(
            value.get("released_utc"),
            label="small-body release timestamp",
        ),
        "source_manifest_sha256": _require_digest(
            value.get("source_manifest_sha256"),
            label="small-body source manifest SHA-256",
        ),
        "source_revision": _require_text(
            value.get("source_revision"),
            label="small-body source revision",
        ),
        "integrity_algorithm": _require_text(
            value.get("integrity_algorithm"),
            label="small-body integrity algorithm",
        ),
        "integrity_receipt": _require_text(
            value.get("integrity_receipt"),
            label="small-body integrity receipt",
        ),
        "integrity_scope": _require_text(
            value.get("integrity_scope"),
            label="small-body integrity scope",
        ),
        "shard_count": shard_count,
        "declared_body_count": declared_body_count,
        "bodies": bodies,
        "coverage": coverage,
        "segment_types": segment_types,
        "frames": frames,
        "native_catalog": native_catalog,
        "native_segment_types": native_segment_types,
        "identity": identity,
    }


def _small_body_requirement_signature(
    requirement: Any,
    *,
    label: str,
) -> dict[str, Any]:
    value = _require_object(requirement, label=label)
    expected_fields = {
        "manifest_schema",
        "require_release_integrity",
        "allowed_segment_types",
        "require_native_catalog",
        "require_native_segments",
    }
    if set(value) != expected_fields:
        raise ReplayContractError(f"{label} has an invalid field set")
    segment_types_raw = value.get("allowed_segment_types")
    if not isinstance(segment_types_raw, list):
        raise ReplayContractError(
            f"{label}.allowed_segment_types must be a list"
        )
    segment_types: list[int] = []
    for index, raw in enumerate(segment_types_raw):
        if type(raw) is not int or raw <= 0:
            raise ReplayContractError(
                f"{label}.allowed_segment_types[{index}] must be a "
                "positive integer"
            )
        segment_types.append(raw)
    if not segment_types or segment_types != sorted(set(segment_types)):
        raise ReplayContractError(
            f"{label}.allowed_segment_types must be sorted and unique"
        )
    result: dict[str, Any] = {
        "manifest_schema": _require_text(
            value.get("manifest_schema"),
            label=f"{label}.manifest_schema",
        ),
        "allowed_segment_types": segment_types,
    }
    for field in (
        "require_release_integrity",
        "require_native_catalog",
        "require_native_segments",
    ):
        raw = value.get(field)
        if type(raw) is not bool:
            raise ReplayContractError(f"{label}.{field} must be true or false")
        result[field] = raw
    return result


def _expected_small_body_signature(
    report: dict[str, Any],
    *,
    repository_root: str,
) -> dict[str, Any]:
    if set(report) != {"version", "summary", "details"}:
        raise ReplayContractError(
            "resources.json.small_body has an invalid field set"
        )
    if (
        type(report.get("version")) is not int
        or report.get("version") != SCHEMA_VERSION
    ):
        raise ReplayContractError(
            "resources.json.small_body has unsupported version"
        )
    details = _require_object(
        report.get("details"),
        label="resources.json.small_body.details",
    )
    if len(details) > _MAX_RESOURCE_REQUIREMENTS:
        raise ReplayContractError(
            "resources.json declares too many small-body resource receipts"
        )
    summary = _require_object(
        report.get("summary"),
        label="resources.json.small_body.summary",
    )
    if set(summary) != {
        "receipts",
        "run",
        "skip",
        "failure",
        "terminal",
        "identities",
        "manifests",
        "shards",
        "bodies",
    }:
        raise ReplayContractError(
            "resources.json.small_body.summary has an invalid field set"
        )
    receipt_count = _require_nonnegative_integer(
        summary.get("receipts"),
        label="resources.json.small_body.summary.receipts",
    )
    if receipt_count != len(details):
        raise ReplayContractError(
            "resources.json.small_body summary receipt count contradicts "
            "details"
        )
    receipts: list[dict[str, Any]] = []
    disposition_counts = {"run": 0, "skip": 0, "failure": 0}
    terminal_count = 0
    derived_identities: set[str] = set()
    derived_manifest_paths: set[str] = set()
    derived_shard_count = 0
    derived_bodies: set[int] = set()
    distinct_requirements: set[str] = set()
    for nodeid, raw_detail in sorted(details.items()):
        _require_text(nodeid, label="small-body detail node ID")
        detail = _require_object(
            raw_detail,
            label=f"small-body detail {nodeid}",
        )
        if set(detail) != {
            "disposition",
            "terminal",
            "failure_type",
            "requirement",
            "identities",
            "capabilities",
            "rendered",
        }:
            raise ReplayContractError(
                f"small-body detail {nodeid} has an invalid field set"
            )
        disposition = detail.get("disposition")
        if disposition not in disposition_counts:
            raise ReplayContractError(
                f"small-body detail {nodeid} has an invalid disposition"
            )
        disposition_counts[disposition] += 1
        terminal = detail.get("terminal")
        if type(terminal) is not bool:
            raise ReplayContractError(
                f"small-body detail {nodeid} terminal must be true or false"
            )
        terminal_count += int(terminal)
        failure_type = detail.get("failure_type")
        if failure_type is not None:
            _require_text(
                failure_type,
                label=f"small-body detail {nodeid} failure type",
            )
        requirement = _small_body_requirement_signature(
            detail.get("requirement"),
            label=f"small-body detail {nodeid} requirement",
        )
        distinct_requirements.add(
            json.dumps(
                requirement,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        raw_identities = detail.get("identities")
        if not isinstance(raw_identities, list):
            raise ReplayContractError(
                f"small-body detail {nodeid} identities must be a list"
            )
        detail_identities = [
            _require_text(
                identity,
                label=f"small-body detail {nodeid} identity",
            )
            for identity in raw_identities
        ]
        if len(set(detail_identities)) != len(detail_identities):
            raise ReplayContractError(
                f"small-body detail {nodeid} identities must be unique"
            )
        derived_identities.update(detail_identities)
        _require_text(
            detail.get("rendered"),
            label=f"small-body detail {nodeid} rendered evidence",
        )
        raw_capabilities = detail.get("capabilities")
        if not isinstance(raw_capabilities, list):
            raise ReplayContractError(
                f"small-body detail {nodeid} capabilities must be a list"
            )
        capability_identities: list[str] = []
        capabilities: list[dict[str, Any]] = []
        for raw_capability in raw_capabilities:
            capability = _small_body_capability_signature(
                raw_capability,
                repository_root=repository_root,
            )
            if capability["manifest_schema"] != requirement["manifest_schema"]:
                raise ReplayContractError(
                    f"small-body detail {nodeid} capability schema "
                    "contradicts requirement"
                )
            if not set(capability["segment_types"]).issubset(
                requirement["allowed_segment_types"]
            ):
                raise ReplayContractError(
                    f"small-body detail {nodeid} capability segment types "
                    "contradict requirement"
                )
            if (
                requirement["require_native_catalog"]
                and not capability["native_catalog"]
            ):
                raise ReplayContractError(
                    f"small-body detail {nodeid} lacks required native catalog"
                )
            if (
                requirement["require_native_segments"]
                and not set(capability["segment_types"]).issubset(
                    capability["native_segment_types"]
                )
            ):
                raise ReplayContractError(
                    f"small-body detail {nodeid} lacks required native "
                    "segment types"
                )
            capability_identities.append(capability["identity"])
            capabilities.append(capability)
            derived_manifest_paths.add(capability["manifest_path"])
            derived_shard_count += capability["shard_count"]
            derived_bodies.update(capability["bodies"])
        if capability_identities != detail_identities:
            raise ReplayContractError(
                f"small-body detail {nodeid} identities contradict capabilities"
            )
        if disposition == "run" and (
            not capability_identities or failure_type is not None
        ):
            raise ReplayContractError(
                f"small-body detail {nodeid} has invalid run evidence"
            )
        if disposition == "skip" and (
            capability_identities
            or failure_type is not None
            or terminal is not True
        ):
            raise ReplayContractError(
                f"small-body detail {nodeid} has invalid skip evidence"
            )
        if disposition == "failure" and (
            failure_type is None or terminal is not True
        ):
            raise ReplayContractError(
                f"small-body detail {nodeid} has invalid failure evidence"
            )
        receipts.append(
            {
                "disposition": disposition,
                "terminal": terminal,
                "failure_type": failure_type,
                "requirement": requirement,
                "capabilities": capabilities,
            }
        )
    if len(distinct_requirements) > _MAX_DISTINCT_RESOURCE_REQUIREMENTS:
        raise ReplayContractError(
            "resources.json declares too many distinct small-body "
            "requirements"
        )
    summary_identities = summary.get("identities")
    if (
        not isinstance(summary_identities, list)
        or any(type(identity) is not str for identity in summary_identities)
        or summary_identities != sorted(set(summary_identities))
        or summary_identities != sorted(derived_identities)
    ):
        raise ReplayContractError(
            "resources.json.small_body summary identities contradict details"
        )
    for disposition, count in disposition_counts.items():
        if _require_nonnegative_integer(
            summary.get(disposition),
            label=f"resources.json.small_body.summary.{disposition}",
        ) != count:
            raise ReplayContractError(
                "resources.json.small_body summary disposition counts "
                "contradict details"
            )
    if _require_nonnegative_integer(
        summary.get("terminal"),
        label="resources.json.small_body.summary.terminal",
    ) != terminal_count:
        raise ReplayContractError(
            "resources.json.small_body summary terminal count contradicts "
            "details"
        )
    for field, expected_value in (
        ("manifests", len(derived_manifest_paths)),
        ("shards", derived_shard_count),
        ("bodies", len(derived_bodies)),
    ):
        if _require_nonnegative_integer(
            summary.get(field),
            label=f"resources.json.small_body.summary.{field}",
        ) != expected_value:
            raise ReplayContractError(
                f"resources.json.small_body summary {field} contradicts "
                "details"
            )
    return {
        "used": receipt_count > 0,
        "receipts": receipts,
    }


def _current_small_body_receipt_signature(
    receipt: Any,
    *,
    requirement: dict[str, Any],
    repository_root: Path,
) -> dict[str, Any]:
    capabilities = [
        _small_body_capability_signature(
            {
                "manifest_path": str(capability.manifest_path),
                "manifest_sha256": capability.manifest_sha256,
                "manifest_schema": capability.manifest_schema,
                "catalog_id": capability.catalog_id,
                "catalog_version": capability.catalog_version,
                "released_utc": capability.released_utc,
                "source_manifest_sha256": (
                    capability.source_manifest_sha256
                ),
                "source_revision": capability.source_revision,
                "integrity_algorithm": capability.integrity_algorithm,
                "integrity_receipt": capability.integrity_receipt,
                "integrity_scope": capability.integrity_scope,
                "shard_count": capability.shard_count,
                "declared_body_count": capability.declared_body_count,
                "bodies": list(capability.bodies),
                "coverage": [
                    [center, target, start_jd, end_jd]
                    for center, target, start_jd, end_jd
                    in capability.coverage
                ],
                "segment_types": sorted(capability.segment_types),
                "frames": sorted(capability.frames),
                "native_catalog": capability.native_catalog,
                "native_segment_types": sorted(
                    capability.native_segment_types
                ),
                "identity": capability.identity,
            },
            repository_root=str(repository_root),
        )
        for capability in receipt.capabilities
    ]
    return {
        "disposition": receipt.disposition.value,
        "terminal": receipt.terminal,
        "failure_type": receipt.failure_type,
        "requirement": requirement,
        "capabilities": capabilities,
    }


def _current_small_body_signature(
    expected: dict[str, Any],
    *,
    repository_root: Path,
) -> dict[str, Any]:
    if not expected["used"]:
        return {"used": False, "receipts": []}
    try:
        from moira._kernel_paths import find_all_small_body_manifests
        from moira import _spk_body_kernel
        from moira.small_body_catalog_release import verify_release
        from support import small_body_resource_policy as policy

        try:
            manifests = find_all_small_body_manifests()
            discovery_error: Exception | None = None
        except Exception as exc:
            manifests = []
            discovery_error = exc
        if len(manifests) > _MAX_RESOURCE_REQUIREMENTS:
            raise ReplayContractError(
                "current discovery returned too many small-body manifests"
            )
        native_segment_types: set[int] = set()
        if _spk_body_kernel._HAS_NATIVE_SEGMENTS:
            native_segment_types.update((2, 3))
        if _spk_body_kernel._HAS_NATIVE_TYPE13:
            native_segment_types.add(13)

        cached: dict[str, dict[str, Any]] = {}
        receipts: list[dict[str, Any]] = []
        for expected_receipt in expected["receipts"]:
            requirement_mapping = expected_receipt["requirement"]
            key = json.dumps(
                requirement_mapping,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            current = cached.get(key)
            if current is None:
                requirement = policy.SmallBodyManifestRequirement(
                    manifest_schema=requirement_mapping["manifest_schema"],
                    require_release_integrity=requirement_mapping[
                        "require_release_integrity"
                    ],
                    allowed_segment_types=frozenset(
                        requirement_mapping["allowed_segment_types"]
                    ),
                    require_native_catalog=requirement_mapping[
                        "require_native_catalog"
                    ],
                    require_native_segments=requirement_mapping[
                        "require_native_segments"
                    ],
                )
                if discovery_error is not None:
                    receipt = policy.SmallBodyResourceReceipt(
                        name="supplemental-small-body-pool",
                        disposition=(
                            policy.SmallBodyResourceDisposition.FAILURE
                        ),
                        requirement=requirement,
                        capabilities=(),
                        reason=(
                            "ambient manifest discovery failed: "
                            f"{discovery_error}"
                        ),
                        failure_type=type(discovery_error).__name__,
                        terminal=True,
                    )
                else:
                    admission = policy.admit_small_body_manifests(
                        manifests,
                        verify_release=verify_release,
                        reader_factory=_spk_body_kernel.SmallBodyKernel,
                        native_catalog_available=bool(
                            _spk_body_kernel._HAS_NATIVE_DAF
                        ),
                        native_segment_types=native_segment_types,
                        requirement=requirement,
                    )
                    receipt = admission.receipt
                    if (
                        receipt.disposition
                        is policy.SmallBodyResourceDisposition.RUN
                    ):
                        close_failures = policy.close_small_body_readers(
                            admission.readers
                        )
                        receipt = policy.terminalize_small_body_receipt(
                            receipt,
                            close_failures=close_failures,
                        )
                current = _current_small_body_receipt_signature(
                    receipt,
                    requirement=requirement_mapping,
                    repository_root=repository_root,
                )
                cached[key] = current
            receipts.append(current)
        return {
            "used": True,
            "receipts": receipts,
        }
    except Exception as exc:
        return {
            "used": True,
            "error": f"{type(exc).__name__}: {exc}",
        }


def _signature_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return _sha256_bytes(raw)


def _compare_resources(
    resources: dict[str, Any],
    *,
    recorded_root: str,
    current_root: Path,
) -> list[str]:
    planetary_report = _require_object(
        resources.get("planetary"),
        label="resources.json.planetary",
    )
    small_body_report = _require_object(
        resources.get("small_body"),
        label="resources.json.small_body",
    )
    expected_planetary = _expected_planetary_signature(
        planetary_report,
        repository_root=recorded_root,
    )
    current_planetary = _current_planetary_signature(
        expected_planetary,
        repository_root=current_root,
    )

    expected_small_body = _expected_small_body_signature(
        small_body_report,
        repository_root=recorded_root,
    )
    current_small_body = _current_small_body_signature(
        expected_small_body,
        repository_root=current_root,
    )

    differences: list[str] = []
    if expected_planetary != current_planetary:
        current_error = current_planetary.get("error")
        if current_error is not None:
            differences.append(
                f"planetary current discovery failed: {current_error}"
            )
        differences.append(
            "planetary signature "
            f"{_signature_digest(expected_planetary)} -> "
            f"{_signature_digest(current_planetary)}"
        )
    if expected_small_body != current_small_body:
        current_error = current_small_body.get("error")
        if current_error is not None:
            differences.append(
                f"small-body current discovery failed: {current_error}"
            )
        differences.append(
            "small-body signature "
            f"{_signature_digest(expected_small_body)} -> "
            f"{_signature_digest(current_small_body)}"
        )
    return differences


def _status_line(name: str, differences: list[str]) -> str:
    if not differences:
        return f"  {name}: MATCH"
    return f"  {name}: MISMATCH - " + "; ".join(differences)


def _validate_execution_switches(
    value: Any,
    *,
    label: str = "run.json.execution_switches",
) -> dict[str, bool]:
    switches = _require_object(
        value,
        label=label,
    )
    if set(switches) != set(_EXECUTION_SWITCH_NAMES) or any(
        type(switches[name]) is not bool
        for name in _EXECUTION_SWITCH_NAMES
    ):
        raise ReplayContractError(
            f"{label} must contain exactly the three "
            "boolean Moira execution switches"
        )
    return {
        name: switches[name]
        for name in _EXECUTION_SWITCH_NAMES
    }


def _apply_execution_switches(
    switches: dict[str, bool],
) -> None:
    for name in _EXECUTION_SWITCH_NAMES:
        os.environ[name] = "1" if switches[name] else "0"


def _sanitized_environment(
    seed: int,
    execution_switches: dict[str, bool],
) -> dict[str, str]:
    environment = dict(os.environ)
    for name in _REPLAY_ENVIRONMENT_REMOVE:
        environment.pop(name, None)
    environment.update(_REPLAY_ENVIRONMENT_SET)
    environment["MOIRA_TEST_SEED"] = str(seed)
    environment["PYTHONHASHSEED"] = str(seed % (1 << 32))
    for name in _EXECUTION_SWITCH_NAMES:
        environment[name] = (
            "1" if execution_switches[name] else "0"
        )
    return environment


def _run_replay(
    python: Path,
    nodeids: tuple[str, ...],
    *,
    seed: int,
    execution_switches: dict[str, bool],
) -> int:
    command = [str(python), "-m", "pytest", "--", *nodeids]
    print(
        f"Starting pytest replay for {len(nodeids)} exact node ID(s).",
        flush=True,
    )
    try:
        completed = subprocess.run(
            command,
            cwd=REPOSITORY_ROOT,
            env=_sanitized_environment(seed, execution_switches),
            check=False,
            shell=False,
        )
    except OSError as exc:
        raise ReplayContractError(f"pytest replay could not start: {exc}") from exc
    return completed.returncode


def _verify_launch_state_unchanged(
    root: Path,
    *,
    interpreter: dict[str, Any],
    git: dict[str, Any],
    native: dict[str, Any],
    resources: dict[str, Any],
    recorded_root: str,
    resource_differences: list[str],
) -> None:
    _verify_current_interpreter(root)
    changed: list[str] = []
    if _current_interpreter_identity(root) != interpreter:
        changed.append("interpreter")
    if _current_git_identity(root) != git:
        changed.append("Git")
    if _current_native_identity(root) != native:
        changed.append("native")
    if _compare_resources(
        resources,
        recorded_root=recorded_root,
        current_root=root,
    ) != resource_differences:
        changed.append("resources")
    if changed:
        raise ReplayContractError(
            "current state changed during replay preflight: "
            + ", ".join(changed)
        )


def _main(args: argparse.Namespace) -> int:
    current_root = REPOSITORY_ROOT.resolve(strict=True)
    project_python = _verify_current_interpreter(current_root)
    _verify_git_root(current_root)
    os.environ["MOIRA_NO_DOWNLOAD"] = "1"

    run_path = args.run_json
    if not run_path.is_absolute():
        run_path = Path.cwd() / run_path
    run, resources, nodeids = _load_receipt_set(run_path)
    execution_switches = _validate_execution_switches(
        run.get("execution_switches")
    )
    final_context = _require_object(
        run.get("final_context"),
        label="run.json.final_context",
    )
    final_execution_switches = _validate_execution_switches(
        final_context.get("execution_switches"),
        label="run.json.final_context.execution_switches",
    )
    if final_execution_switches != execution_switches:
        raise ReplayContractError(
            "run.json execution switches changed during the recorded run"
        )
    _apply_execution_switches(execution_switches)
    _ensure_repository_import_path(current_root)

    repository = _require_object(
        run.get("repository"),
        label="run.json.repository",
    )
    recorded_root = _require_text(
        repository.get("root"),
        label="run.json.repository.root",
    )
    same_repository = _repository_matches(recorded_root, current_root)
    repository_differences = (
        []
        if same_repository
        else [f"{recorded_root!r} -> {str(current_root)!r}"]
    )

    recorded_git = _validate_recorded_git(repository.get("git"))
    current_git = _current_git_identity(current_root)
    git_differences = _compare_git(
        recorded_git,
        current_git,
        recorded_root=recorded_root,
        current_root=current_root,
    )

    recorded_interpreter = _validate_recorded_interpreter(
        run.get("interpreter")
    )
    current_interpreter = _current_interpreter_identity(current_root)
    interpreter_differences = _compare_interpreter(
        recorded_interpreter,
        current_interpreter,
        repository_matches=same_repository,
    )

    recorded_native = _validate_recorded_native(run.get("native"))
    current_native = _current_native_identity(current_root)
    native_differences = _compare_native(
        recorded_native,
        current_native,
        recorded_root=recorded_root,
        current_root=current_root,
    )

    policy = _require_object(run.get("policy"), label="run.json.policy")
    seed = policy.get("seed")
    if type(seed) is not int or not 0 <= seed <= _MAX_TEST_SEED:
        raise ReplayContractError(
            f"run.json.policy.seed must be an integer in 0..{_MAX_TEST_SEED}"
        )

    resource_differences = _compare_resources(
        resources,
        recorded_root=recorded_root,
        current_root=current_root,
    )

    print("Moira replay preflight:", flush=True)
    print(
        _status_line("Repository", repository_differences),
        flush=True,
    )
    print(
        _status_line("Interpreter", interpreter_differences),
        flush=True,
    )
    print(_status_line("Git", git_differences), flush=True)
    print(_status_line("Native", native_differences), flush=True)
    print(_status_line("Resources", resource_differences), flush=True)

    blocked = False
    if repository_differences and not args.allow_repository_mismatch:
        print(
            "Repository mismatch blocks replay; pass "
            "--allow-repository-mismatch to acknowledge it explicitly.",
            file=sys.stderr,
            flush=True,
        )
        blocked = True
    state_differences = (
        interpreter_differences
        + git_differences
        + native_differences
        + resource_differences
    )
    if state_differences and not args.allow_state_mismatch:
        print(
            "Interpreter/Git/native/resource mismatch blocks replay; pass "
            "--allow-state-mismatch to acknowledge it explicitly.",
            file=sys.stderr,
            flush=True,
        )
        blocked = True
    if blocked:
        return 3

    if args.check_only:
        print(
            f"Receipt is replayable ({len(nodeids)} node ID(s)); check-only.",
            flush=True,
        )
        return 0
    if not nodeids:
        print("Receipt contains no failed node IDs; nothing to replay.", flush=True)
        return 0
    _verify_launch_state_unchanged(
        current_root,
        interpreter=current_interpreter,
        git=current_git,
        native=current_native,
        resources=resources,
        recorded_root=recorded_root,
        resource_differences=resource_differences,
    )
    return _run_replay(
        project_python,
        nodeids,
        seed=seed,
        execution_switches=execution_switches,
    )


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        return _main(args)
    except ReplayContractError as exc:
        print(f"Moira replay refused: {exc}", file=sys.stderr, flush=True)
        return 2
    except KeyboardInterrupt:
        print("Moira replay interrupted.", file=sys.stderr, flush=True)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
