"""Fail-closed, read-only policy shared by snapshot and golden assertions."""

from __future__ import annotations

import json
import math
import os
import re
import stat
from pathlib import Path
from typing import Any


_SAFE_SLUG = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z")
_WINDOWS_RESERVED_STEMS = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}
_READ_ONLY_GUIDANCE = (
    "Ordinary pytest baseline access is read-only; candidate generation and "
    "reviewed promotion are separate operations."
)
_MAX_BASELINE_BYTES = 16 * 1024 * 1024
_WINDOWS_REPARSE_POINT_ATTRIBUTE = getattr(
    stat,
    "FILE_ATTRIBUTE_REPARSE_POINT",
    0x400,
)
# Windows IsReparseTagNameSurrogate() tests this bit in a reparse tag.
_WINDOWS_NAME_SURROGATE_TAG_BIT = 0x20000000


class _DuplicateKeyError(ValueError):
    """Raised when strict JSON parsing encounters an ambiguous object."""


def _validate_name(name: object) -> str:
    if not isinstance(name, str):
        raise TypeError("baseline name must be a string safe slug.")
    if (
        _SAFE_SLUG.fullmatch(name) is None
        or name.upper() in _WINDOWS_RESERVED_STEMS
    ):
        raise ValueError(
            "baseline name must be a safe slug: 1-128 ASCII letters, digits, "
            "underscores, or hyphens; Windows device names are forbidden."
        )
    return name


def _reject_legacy_update_request(environment_name: str) -> None:
    raw = os.environ.get(environment_name)
    if raw is None or raw == "0":
        return
    raise AssertionError(f"{environment_name}={raw!r} is forbidden. {_READ_ONLY_GUIDANCE}")


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
        getattr(metadata, "st_mtime_ns", int(metadata.st_mtime * 1_000_000_000)),
    )


def _directory_identity(metadata: os.stat_result) -> tuple[int, int]:
    return metadata.st_dev, metadata.st_ino


def _assert_stable_root(
    directory: Path,
    expected_identity: tuple[int, int],
    *,
    channel: str,
) -> None:
    try:
        current_metadata = directory.lstat()
    except OSError as exc:
        raise AssertionError(
            f"{channel} baseline root changed during validation: {directory}."
        ) from exc
    if (
        stat.S_ISLNK(current_metadata.st_mode)
        or _is_name_surrogate_reparse(current_metadata)
        or not stat.S_ISDIR(current_metadata.st_mode)
        or _directory_identity(current_metadata) != expected_identity
    ):
        raise AssertionError(
            f"{channel} baseline root changed during validation: {directory}."
        )


def _resolve_path(
    directory: Path,
    approved_parent: Path,
    name: str,
    *,
    channel: str,
) -> tuple[Path, os.stat_result]:
    directory_path = Path(directory)
    try:
        root_metadata = directory_path.lstat()
    except OSError as exc:
        raise AssertionError(
            f"{channel} baseline directory is unavailable. {_READ_ONLY_GUIDANCE}"
        ) from exc
    if (
        stat.S_ISLNK(root_metadata.st_mode)
        or _is_name_surrogate_reparse(root_metadata)
        or not stat.S_ISDIR(root_metadata.st_mode)
    ):
        raise AssertionError(
            f"{channel} baseline root must be an approved regular directory, "
            f"not a symbolic link or name-surrogate reparse point: {directory_path}."
        )
    root_identity = _directory_identity(root_metadata)

    try:
        trusted_root = Path(approved_parent).resolve(strict=True)
        root = directory_path.resolve(strict=True)
        root_relative = root.relative_to(trusted_root)
    except (OSError, RuntimeError, ValueError) as exc:
        raise AssertionError(
            f"{channel} baseline root escapes its approved parent: {directory_path}."
        ) from exc
    _assert_stable_root(directory_path, root_identity, channel=channel)
    if len(root_relative.parts) != 1:
        raise AssertionError(
            f"{channel} baseline root must be a direct child of its approved "
            f"parent: {directory_path}."
        )

    candidate = directory_path / f"{name}.json"
    try:
        candidate_metadata = candidate.lstat()
    except OSError as exc:
        raise AssertionError(
            f"{channel} baseline is missing: {candidate}. {_READ_ONLY_GUIDANCE}"
        ) from exc
    if (
        stat.S_ISLNK(candidate_metadata.st_mode)
        or _is_name_surrogate_reparse(candidate_metadata)
    ):
        raise AssertionError(
            f"{channel} baseline must not be a symbolic link or name-surrogate "
            f"reparse point: {candidate}."
        )
    if not stat.S_ISREG(candidate_metadata.st_mode):
        raise AssertionError(
            f"{channel} baseline is not a regular file: {candidate}."
        )

    try:
        resolved = candidate.resolve(strict=True)
        relative = resolved.relative_to(root)
    except (OSError, RuntimeError, ValueError) as exc:
        raise AssertionError(
            f"{channel} baseline path escapes its approved directory: {candidate}."
        ) from exc
    _assert_stable_root(directory_path, root_identity, channel=channel)
    if len(relative.parts) != 1 or relative.name != f"{name}.json":
        raise AssertionError(
            f"{channel} baseline path is not a direct child of its approved "
            f"directory: {candidate}."
        )
    return candidate, candidate_metadata


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKeyError(f"duplicate object key {key!r}")
        result[key] = value
    return result


def _reject_nonfinite_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant {value!r}")


def _read_stable_bytes(
    path: Path,
    expected_metadata: os.stat_result,
    *,
    channel: str,
) -> bytes:
    try:
        with path.open("rb") as stream:
            opened_metadata = os.fstat(stream.fileno())
            if (
                not stat.S_ISREG(opened_metadata.st_mode)
                or _is_name_surrogate_reparse(opened_metadata)
                or _metadata_signature(opened_metadata)
                != _metadata_signature(expected_metadata)
            ):
                raise AssertionError(
                    f"{channel} baseline changed during secure open: {path}."
                )
            raw = stream.read(_MAX_BASELINE_BYTES + 1)
            final_metadata = os.fstat(stream.fileno())
    except OSError as exc:
        raise AssertionError(
            f"{channel} baseline could not be read: {path}: {exc}"
        ) from exc
    if _metadata_signature(final_metadata) != _metadata_signature(opened_metadata):
        raise AssertionError(f"{channel} baseline changed while being read: {path}.")
    if len(raw) > _MAX_BASELINE_BYTES:
        raise AssertionError(
            f"{channel} baseline exceeds the {_MAX_BASELINE_BYTES}-byte limit: {path}."
        )
    return raw


def _load_document(
    path: Path,
    expected_metadata: os.stat_result,
    *,
    channel: str,
) -> dict[str, Any]:
    raw = _read_stable_bytes(path, expected_metadata, channel=channel)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AssertionError(
            f"{channel} baseline is not strict UTF-8: {path}: {exc}"
        ) from exc
    try:
        document = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite_constant,
        )
    except (json.JSONDecodeError, _DuplicateKeyError, ValueError) as exc:
        raise AssertionError(
            f"{channel} baseline is not valid strict JSON: {path}: {exc}"
        ) from exc
    if not isinstance(document, dict) or set(document) != {"value"}:
        raise AssertionError(
            f"{channel} baseline must contain exactly one top-level 'value' key: "
            f"{path}."
        )
    return document


def _json_model(value: Any, *, location: str = "value") -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{location} must not contain NaN or infinity.")
        return value
    if isinstance(value, (list, tuple)):
        return [
            _json_model(item, location=f"{location}[{index}]")
            for index, item in enumerate(value)
        ]
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{location} contains a non-string object key.")
            normalized[key] = _json_model(item, location=f"{location}.{key}")
    return normalized
    raise TypeError(
        f"{location} must be JSON-compatible; got {type(value).__name__}."
    )


def _json_values_equal(approved: Any, observed: Any) -> bool:
    if isinstance(approved, bool) or isinstance(observed, bool):
        return type(approved) is type(observed) and approved == observed
    if isinstance(approved, (int, float)) and isinstance(observed, (int, float)):
        return approved == observed
    if type(approved) is not type(observed):
        return False
    if isinstance(approved, list):
        return len(approved) == len(observed) and all(
            _json_values_equal(approved_item, observed_item)
            for approved_item, observed_item in zip(approved, observed, strict=True)
        )
    if isinstance(approved, dict):
        return approved.keys() == observed.keys() and all(
            _json_values_equal(approved[key], observed[key]) for key in approved
        )
    return approved == observed


def assert_approved_baseline(
    *,
    directory: Path,
    approved_parent: Path,
    name: object,
    value: Any,
    channel: str,
    legacy_update_environment: str,
) -> None:
    """Compare against one approved baseline without any mutation path."""

    safe_name = _validate_name(name)
    _reject_legacy_update_request(legacy_update_environment)
    path, metadata = _resolve_path(
        directory,
        approved_parent,
        safe_name,
        channel=channel,
    )
    existing = _load_document(path, metadata, channel=channel)
    expected = {"value": _json_model(value)}
    if not _json_values_equal(existing, expected):
        raise AssertionError(
            f"{channel} baseline mismatch for {safe_name!r}.\n"
            f"Expected approved: {existing!r}\n"
            f"Actual observed:  {expected!r}"
        )
