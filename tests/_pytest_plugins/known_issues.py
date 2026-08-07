"""Secure schema and expiry policy for ``tests/KNOWN_ISSUES.yml``."""

from __future__ import annotations

from datetime import date, datetime
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import stat

import pytest

from ._common import _is_name_surrogate_reparse, _metadata_signature
from ._state import (
    TEST_DIR,
    _EXACT_DATE_RE,
    _HARNESS_CONFIG_KEY,
    _KNOWN_ISSUES_KEY,
    _KNOWN_ISSUE_FIELDS,
    _KNOWN_ISSUE_ID_RE,
    _MAX_KNOWN_ISSUES_ALIASES,
    _MAX_KNOWN_ISSUES_BYTES,
    _MAX_KNOWN_ISSUES_DEPTH,
    _MAX_KNOWN_ISSUES_NODES,
    _KnownIssue,
)


def _known_issue_error(index: int, issue_id: object, message: str) -> pytest.UsageError:
    identity = issue_id if isinstance(issue_id, str) and issue_id.strip() else "<unknown>"
    return pytest.UsageError(
        f"KNOWN_ISSUES.yml known_issues[{index}] (id {identity!r}): {message}"
    )


def _read_stable_known_issues_bytes(
    path: Path,
    expected_metadata,
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
                raise pytest.UsageError(
                    "KNOWN_ISSUES.yml changed during secure open."
                )
            raw_bytes = stream.read(_MAX_KNOWN_ISSUES_BYTES + 1)
            final_metadata = os.fstat(stream.fileno())
    except OSError as exc:
        raise pytest.UsageError(f"Could not read KNOWN_ISSUES.yml: {exc}") from exc
    if _metadata_signature(final_metadata) != _metadata_signature(opened_metadata):
        raise pytest.UsageError("KNOWN_ISSUES.yml changed while being read.")
    return raw_bytes


def _load_known_issues(path: Path) -> tuple[_KnownIssue, ...]:
    try:
        policy_metadata = path.lstat()
    except OSError as exc:
        raise pytest.UsageError(
            f"KNOWN_ISSUES.yml is missing or unresolvable: {path}"
        ) from exc
    if (
        stat.S_ISLNK(policy_metadata.st_mode)
        or _is_name_surrogate_reparse(policy_metadata)
        or not stat.S_ISREG(policy_metadata.st_mode)
    ):
        raise pytest.UsageError(
            f"KNOWN_ISSUES.yml is missing or is not a regular file: {path}"
        )

    raw_bytes = _read_stable_known_issues_bytes(path, policy_metadata)
    if len(raw_bytes) > _MAX_KNOWN_ISSUES_BYTES:
        raise pytest.UsageError(
            "KNOWN_ISSUES.yml exceeds the "
            f"{_MAX_KNOWN_ISSUES_BYTES}-byte policy limit."
        )
    try:
        raw_text = raw_bytes.decode("utf-8")
    except UnicodeError as exc:
        raise pytest.UsageError(
            f"KNOWN_ISSUES.yml must be valid UTF-8: {exc}"
        ) from exc

    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError as exc:
        raise pytest.UsageError(
            "PyYAML is required to validate KNOWN_ISSUES.yml; install the declared "
            "development dependencies."
        ) from exc

    class _UniqueKeySafeLoader(yaml.SafeLoader):
        def __init__(self, stream):
            super().__init__(stream)
            self._moira_depth = 0
            self._moira_nodes = 0
            self._moira_aliases = 0

        def compose_node(self, parent, index):
            self._moira_nodes += 1
            if self._moira_nodes > _MAX_KNOWN_ISSUES_NODES:
                event = self.peek_event()
                raise yaml.composer.ComposerError(
                    "while composing KNOWN_ISSUES.yml",
                    event.start_mark,
                    f"document exceeds {_MAX_KNOWN_ISSUES_NODES} YAML nodes",
                    event.start_mark,
                )

            if self.check_event(yaml.events.AliasEvent):
                self._moira_aliases += 1
                if self._moira_aliases > _MAX_KNOWN_ISSUES_ALIASES:
                    event = self.peek_event()
                    raise yaml.composer.ComposerError(
                        "while composing KNOWN_ISSUES.yml",
                        event.start_mark,
                        "YAML aliases are not permitted by policy",
                        event.start_mark,
                    )

            self._moira_depth += 1
            if self._moira_depth > _MAX_KNOWN_ISSUES_DEPTH:
                event = self.peek_event()
                self._moira_depth -= 1
                raise yaml.composer.ComposerError(
                    "while composing KNOWN_ISSUES.yml",
                    event.start_mark,
                    f"document exceeds nesting depth {_MAX_KNOWN_ISSUES_DEPTH}",
                    event.start_mark,
                )
            try:
                return super().compose_node(parent, index)
            finally:
                self._moira_depth -= 1

    def _construct_unique_mapping(loader, node, deep=False):
        loader.flatten_mapping(node)
        seen: set[object] = set()
        for key_node, _ in node.value:
            key = loader.construct_object(key_node, deep=deep)
            try:
                duplicate = key in seen
            except TypeError as exc:
                raise yaml.constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    "mapping keys must be hashable",
                    key_node.start_mark,
                ) from exc
            if duplicate:
                raise yaml.constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    f"duplicate mapping key {key!r}",
                    key_node.start_mark,
                )
            seen.add(key)
        return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)

    _UniqueKeySafeLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        _construct_unique_mapping,
    )

    try:
        data = yaml.load(raw_text, Loader=_UniqueKeySafeLoader)
    except (yaml.YAMLError, ValueError, RecursionError) as exc:
        raise pytest.UsageError(f"KNOWN_ISSUES.yml is invalid YAML: {exc}") from exc

    if type(data) is not dict:
        raise pytest.UsageError(
            "KNOWN_ISSUES.yml top-level document must be a mapping containing "
            "exactly the 'known_issues' key."
        )
    root_keys = set(data)
    if root_keys != {"known_issues"}:
        missing = sorted({"known_issues"} - root_keys)
        unexpected = sorted(root_keys - {"known_issues"}, key=str)
        raise pytest.UsageError(
            "KNOWN_ISSUES.yml top-level mapping must contain exactly the "
            f"'known_issues' key; missing={missing}, unexpected={unexpected}."
        )

    raw_issues = data["known_issues"]
    if type(raw_issues) is not list:
        raise pytest.UsageError(
            "KNOWN_ISSUES.yml field 'known_issues' must be a list of mappings."
        )

    try:
        tests_root = TEST_DIR.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise pytest.UsageError(
            f"Could not resolve the tests directory for KNOWN_ISSUES.yml: {exc}"
        ) from exc
    if not tests_root.is_dir():
        raise pytest.UsageError(
            f"KNOWN_ISSUES.yml tests root is not a directory: {tests_root}"
        )

    issues: list[_KnownIssue] = []
    seen_ids: set[str] = set()
    for index, raw_issue in enumerate(raw_issues):
        if type(raw_issue) is not dict:
            raise _known_issue_error(
                index,
                None,
                "each issue entry must be a mapping.",
            )

        issue_id = raw_issue.get("id")
        issue_keys = set(raw_issue)
        if issue_keys != _KNOWN_ISSUE_FIELDS:
            missing = sorted(_KNOWN_ISSUE_FIELDS - issue_keys)
            unexpected = sorted(issue_keys - _KNOWN_ISSUE_FIELDS, key=str)
            raise _known_issue_error(
                index,
                issue_id,
                f"field set is invalid; missing={missing}, unexpected={unexpected}.",
            )

        parsed_strings: dict[str, str] = {}
        for field in ("id", "path", "reason", "owner"):
            value = raw_issue[field]
            if type(value) is not str:
                raise _known_issue_error(
                    index,
                    issue_id,
                    f"field {field!r} must be a nonempty string.",
                )
            if not value.strip():
                raise _known_issue_error(
                    index,
                    issue_id,
                    f"field {field!r} must be a nonempty string and cannot be blank.",
                )
            parsed_strings[field] = value

        issue_id = parsed_strings["id"]
        if _KNOWN_ISSUE_ID_RE.fullmatch(issue_id) is None:
            raise _known_issue_error(
                index,
                issue_id,
                "field 'id' must be a safe 1-64 character ASCII slug using "
                "letters, digits, underscores, periods, or hyphens.",
            )
        if issue_id in seen_ids:
            raise _known_issue_error(
                index,
                issue_id,
                f"duplicate issue id {issue_id!r}; IDs must be unique.",
            )
        seen_ids.add(issue_id)

        raw_expiry = raw_issue["expires"]
        if type(raw_expiry) is str and not raw_expiry.strip():
            raise _known_issue_error(
                index,
                issue_id,
                "field 'expires' must be nonempty and cannot be blank.",
            )
        if isinstance(raw_expiry, datetime):
            raise _known_issue_error(
                index,
                issue_id,
                "field 'expires' must be a date, not a timestamp.",
            )
        if type(raw_expiry) is date:
            expiry = raw_expiry
        elif type(raw_expiry) is str and _EXACT_DATE_RE.fullmatch(raw_expiry):
            try:
                expiry = date.fromisoformat(raw_expiry)
            except ValueError as exc:
                raise _known_issue_error(
                    index,
                    issue_id,
                    "field 'expires' must be a real YYYY-MM-DD calendar date.",
                ) from exc
        else:
            raise _known_issue_error(
                index,
                issue_id,
                "field 'expires' must be an exact YYYY-MM-DD string or YAML date.",
            )

        raw_relative_path = parsed_strings["path"]
        if "\x00" in raw_relative_path:
            raise _known_issue_error(
                index,
                issue_id,
                "field 'path' must not contain NUL characters.",
            )

        windows_path = PureWindowsPath(raw_relative_path)
        posix_path = PurePosixPath(raw_relative_path)
        if (
            windows_path.drive
            or windows_path.root
            or windows_path.is_absolute()
            or posix_path.is_absolute()
        ):
            raise _known_issue_error(
                index,
                issue_id,
                "field 'path' must be relative; rooted, absolute, drive-relative, "
                "and UNC paths are forbidden.",
            )
        if ".." in windows_path.parts or ".." in posix_path.parts:
            raise _known_issue_error(
                index,
                issue_id,
                "field 'path' must not contain parent traversal ('..').",
            )

        unresolved = tests_root.joinpath(*windows_path.parts)
        current = tests_root
        for part in windows_path.parts:
            current /= part
            try:
                metadata = current.lstat()
            except OSError as exc:
                raise _known_issue_error(
                    index,
                    issue_id,
                    f"field 'path' is missing or unresolvable: "
                    f"{raw_relative_path!r}.",
                ) from exc
            if stat.S_ISLNK(metadata.st_mode) or _is_name_surrogate_reparse(
                metadata
            ):
                raise _known_issue_error(
                    index,
                    issue_id,
                    "field 'path' must not traverse a symbolic link or Windows "
                    f"name-surrogate reparse point: {raw_relative_path!r}.",
                )

        try:
            resolved = unresolved.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise _known_issue_error(
                index,
                issue_id,
                f"field 'path' is missing or unresolvable: {raw_relative_path!r}.",
            ) from exc
        try:
            resolved.relative_to(tests_root)
        except ValueError as exc:
            raise _known_issue_error(
                index,
                issue_id,
                f"field 'path' escapes the tests directory: {raw_relative_path!r}.",
            ) from exc
        if not resolved.is_file():
            raise _known_issue_error(
                index,
                issue_id,
                f"field 'path' must resolve to a regular file: {raw_relative_path!r}.",
            )

        issues.append(
            _KnownIssue(
                id=issue_id,
                relative_path=raw_relative_path,
                resolved_path=resolved,
                reason=parsed_strings["reason"],
                owner=parsed_strings["owner"],
                expires=expiry,
            )
        )

    return tuple(issues)


@pytest.hookimpl
def pytest_configure(config) -> None:
    issues = _load_known_issues(TEST_DIR / "KNOWN_ISSUES.yml")
    config.stash[_KNOWN_ISSUES_KEY] = issues
    today = date.today()
    expired = tuple(issue for issue in issues if issue.expires < today)
    if not expired:
        return
    details = ", ".join(
        f"{issue.id} {issue.relative_path} "
        f"(expired {issue.expires.isoformat()})"
        for issue in expired
    )
    policy = config.stash[_HARNESS_CONFIG_KEY]
    if policy.strict_known_issues:
        raise pytest.UsageError(
            f"KNOWN_ISSUES.yml has expired entries: {details}"
        )
    config.issue_config_time_warning(
        pytest.PytestConfigWarning(
            f"KNOWN_ISSUES.yml has expired entries: {details}"
        ),
        stacklevel=2,
    )
