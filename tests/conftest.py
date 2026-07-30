"""
Pytest configuration and shared fixtures for Moira tests.

Automatically loaded by pytest before running tests. Provides:
  - Moira-specific session fixtures (engine, test charts)
  - Network safety (deny by default; explicit loopback/external capabilities)
  - KNOWN_ISSUES.yml validation with expiry and path checking
  - Per-test and total runtime budgets
  - Snapshot / golden-value assertion fixtures
  - Hypothesis configuration
  - pytest-xdist parallel support
  - Optional artifact recording (MOIRA_TEST_ARTIFACTS=1)
  - Domain fixtures: moira_approx and assert_longitude
"""
from __future__ import annotations

import ast
import json
import io
import importlib
import math
import os
import random
import re
import stat
import tokenize
from dataclasses import dataclass, replace
from datetime import date, datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath
import pytest

from support.network_policy import (
    NetworkMode,
    activate_network_mode,
    install_network_audit_hook,
    reset_network_mode,
)


# ---------------------------------------------------------------------------
# Directory constants
# ---------------------------------------------------------------------------

ROOT_DIR  = Path(__file__).resolve().parents[1]   # project root
TEST_DIR  = ROOT_DIR / "tests"


# ---------------------------------------------------------------------------
# Typed harness policy
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class _HypothesisPolicy:
    profile: str
    max_examples: int
    database_policy: str
    derandomize: bool


@dataclass(frozen=True, slots=True)
class _HarnessConfig:
    test_mode: bool
    no_download: bool
    strict_known_issues: bool
    external_network_enabled: bool
    seed: int
    budget_total_s: float
    budget_case_s: float
    hypothesis: _HypothesisPolicy


@dataclass(frozen=True, slots=True)
class _KnownIssue:
    id: str
    relative_path: str
    resolved_path: Path
    reason: str
    owner: str
    expires: date


_HARNESS_CONFIG_KEY: pytest.StashKey[_HarnessConfig] = pytest.StashKey()
_KNOWN_ISSUES_KEY: pytest.StashKey[tuple[_KnownIssue, ...]] = pytest.StashKey()
_EXTERNAL_NETWORK_SELECTED_KEY: pytest.StashKey[int] = pytest.StashKey()

_KNOWN_ISSUE_FIELDS = {"id", "path", "reason", "owner", "expires"}
_MAX_TEST_SEED = (1 << 64) - 1
_LEGACY_BASELINE_UPDATE_ENVIRONMENTS = (
    "MOIRA_SNAPSHOT_UPDATE",
    "MOIRA_GOLDEN_UPDATE",
)
_EXACT_DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_KNOWN_ISSUE_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}")
_MAX_KNOWN_ISSUES_BYTES = 256 * 1024
_MAX_KNOWN_ISSUES_DEPTH = 64
_MAX_KNOWN_ISSUES_NODES = 10_000
_MAX_KNOWN_ISSUES_ALIASES = 0
_WINDOWS_REPARSE_POINT_ATTRIBUTE = getattr(
    stat,
    "FILE_ATTRIBUTE_REPARSE_POINT",
    0x400,
)
# Windows IsReparseTagNameSurrogate() tests this bit in a reparse tag.
_WINDOWS_NAME_SURROGATE_TAG_BIT = 0x20000000
_EXTERNAL_NETWORK_SKIP_REASON = (
    "external network test requires the explicit --run-external-network option"
)


def _prepend_child_policy_import_path() -> None:
    """Expose only the cooperative child-policy bootstrap on ``PYTHONPATH``."""

    bootstrap_entry = str(
        TEST_DIR / "support" / "network_bootstrap"
    )
    existing = os.environ.get("PYTHONPATH", "")
    entries = [entry for entry in existing.split(os.pathsep) if entry]
    normalized_bootstrap = os.path.normcase(os.path.abspath(bootstrap_entry))
    normalized_entries = {
        os.path.normcase(os.path.abspath(entry))
        for entry in entries
    }
    if normalized_bootstrap not in normalized_entries:
        os.environ["PYTHONPATH"] = os.pathsep.join(
            [bootstrap_entry, *entries]
        )


_prepend_child_policy_import_path()
install_network_audit_hook()
reset_network_mode(nodeid="<collection>")


def _register_hypothesis_profiles() -> bool:
    try:
        from hypothesis import settings, Verbosity
    except ImportError:
        return False

    parent = settings.get_profile("default")
    settings.register_profile(
        "moira-ci",
        parent=parent,
        max_examples=50,
        verbosity=Verbosity.quiet,
        database=None,
        derandomize=True,
        deadline=1000,
    )
    settings.register_profile(
        "moira-local",
        parent=parent,
        max_examples=100,
        verbosity=Verbosity.normal,
        derandomize=False,
        deadline=1000,
    )
    settings.register_profile(
        "moira-nightly",
        parent=parent,
        max_examples=1000,
        verbosity=Verbosity.normal,
        derandomize=False,
        deadline=None,
    )
    return True


_HYPOTHESIS_AVAILABLE = _register_hypothesis_profiles()


def _display_env_value(raw: str, *, limit: int = 80) -> str:
    if len(raw) <= limit:
        return repr(raw)
    return f"{raw[:limit]!r}... ({len(raw)} characters)"


def _parse_bool_env(name: str, *, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    if raw not in {"0", "1"}:
        raise pytest.UsageError(
            f"{name} must be exactly '0' or '1'; got {_display_env_value(raw)}."
        )
    return raw == "1"


def _parse_seed_env(name: str, *, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    if len(raw) > 20 or re.fullmatch(r"[0-9]+", raw) is None:
        raise pytest.UsageError(
            f"{name} must be an integer from 0 through {_MAX_TEST_SEED}; "
            f"got {_display_env_value(raw)}."
        )
    try:
        value = int(raw)
    except ValueError as exc:
        raise pytest.UsageError(
            f"{name} must be an integer from 0 through {_MAX_TEST_SEED}; "
            f"got {_display_env_value(raw)}."
        ) from exc
    if value > _MAX_TEST_SEED:
        raise pytest.UsageError(
            f"{name} must be an integer from 0 through {_MAX_TEST_SEED}; "
            f"got {_display_env_value(raw)}."
        )
    return value


def _parse_nonnegative_finite_float_env(name: str, *, default: float = 0.0) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise pytest.UsageError(
            f"{name} must be a finite nonnegative number; "
            f"got {_display_env_value(raw)}."
        ) from exc
    if not math.isfinite(value) or value < 0:
        raise pytest.UsageError(
            f"{name} must be a finite nonnegative number; "
            f"got {_display_env_value(raw)}."
        )
    return value


def _activate_hypothesis_policy(config, *, test_mode: bool) -> _HypothesisPolicy:
    if not _HYPOTHESIS_AVAILABLE:
        raise pytest.UsageError(
            "Hypothesis is required by the Moira test harness; install the declared "
            "development dependencies."
        )

    from hypothesis import errors, settings

    explicit_profile = config.getoption("--hypothesis-profile", default=None)
    selected_profile = explicit_profile or ("moira-ci" if test_mode else "moira-local")
    try:
        settings.load_profile(selected_profile)
    except (errors.InvalidArgument, KeyError) as exc:
        raise pytest.UsageError(
            f"Unknown or invalid Hypothesis profile {selected_profile!r}."
        ) from exc

    return _snapshot_hypothesis_policy()


def _snapshot_hypothesis_policy() -> _HypothesisPolicy:
    from hypothesis import settings

    active = settings.default
    database_policy = (
        "disabled"
        if active.database is None
        else f"enabled:{type(active.database).__name__}"
    )
    return _HypothesisPolicy(
        profile=settings.get_current_profile_name(),
        max_examples=active.max_examples,
        database_policy=database_policy,
        derandomize=active.derandomize,
    )


def _parse_harness_config(config) -> _HarnessConfig:
    for environment_name in _LEGACY_BASELINE_UPDATE_ENVIRONMENTS:
        if _parse_bool_env(environment_name):
            raise pytest.UsageError(
                f"{environment_name}=1 is forbidden: ordinary pytest baseline "
                "access is read-only. Generate candidates separately and promote "
                "protected evidence only after review."
            )

    test_mode = _parse_bool_env("MOIRA_TEST_MODE")
    no_download_is_explicit = "MOIRA_NO_DOWNLOAD" in os.environ
    no_download = _parse_bool_env(
        "MOIRA_NO_DOWNLOAD",
        default=test_mode,
    )
    if test_mode and no_download_is_explicit and not no_download:
        raise pytest.UsageError(
            "MOIRA_TEST_MODE=1 requires MOIRA_NO_DOWNLOAD=1; the explicit "
            "MOIRA_NO_DOWNLOAD=0 override would weaken deterministic test mode."
        )

    policy = _HarnessConfig(
        test_mode=test_mode,
        no_download=no_download,
        strict_known_issues=_parse_bool_env("MOIRA_STRICT_KNOWN_ISSUES"),
        external_network_enabled=bool(
            config.getoption("--run-external-network")
        ),
        seed=_parse_seed_env("MOIRA_TEST_SEED", default=1337),
        budget_total_s=_parse_nonnegative_finite_float_env(
            "MOIRA_TEST_BUDGET_TOTAL_S"
        ),
        budget_case_s=_parse_nonnegative_finite_float_env(
            "MOIRA_TEST_BUDGET_CASE_S"
        ),
        hypothesis=_activate_hypothesis_policy(config, test_mode=test_mode),
    )

    if test_mode and not no_download_is_explicit:
        # Engine acquisition code consumes this environment boundary directly.
        os.environ["MOIRA_NO_DOWNLOAD"] = "1"
    return policy




# ---------------------------------------------------------------------------
# KNOWN_ISSUES loader
# ---------------------------------------------------------------------------

def _known_issue_error(index: int, issue_id: object, message: str) -> pytest.UsageError:
    identity = issue_id if isinstance(issue_id, str) and issue_id.strip() else "<unknown>"
    return pytest.UsageError(
        f"KNOWN_ISSUES.yml known_issues[{index}] (id {identity!r}): {message}"
    )


def _is_name_surrogate_reparse(metadata) -> bool:
    has_reparse_flag = bool(
        getattr(metadata, "st_file_attributes", 0)
        & _WINDOWS_REPARSE_POINT_ATTRIBUTE
    )
    reparse_tag = getattr(metadata, "st_reparse_tag", None)
    return has_reparse_flag and (
        reparse_tag is None
        or bool(reparse_tag & _WINDOWS_NAME_SURROGATE_TAG_BIT)
    )


def _metadata_signature(metadata) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        getattr(metadata, "st_mtime_ns", int(metadata.st_mtime * 1_000_000_000)),
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


# ---------------------------------------------------------------------------
# Ephemeris detection
# ---------------------------------------------------------------------------

def _has_ephemeris() -> bool:
    from moira._kernel_paths import find_planetary_kernel
    return find_planetary_kernel() is not None


def _legacy_network_marker_locations(tests_root: Path) -> tuple[str, ...]:
    """Find executable ``pytest.mark.network`` syntax, even in skipped modules."""

    locations: list[str] = []
    for path in sorted(tests_root.rglob("*.py")):
        try:
            with tokenize.open(path) as stream:
                source = stream.read()
            tree = ast.parse(source, filename=str(path))
        except (OSError, UnicodeError, SyntaxError) as exc:
            relative = path.relative_to(tests_root).as_posix()
            raise pytest.UsageError(
                "Legacy network-marker scan could not inspect "
                f"{relative!r}; refusing to continue with an incomplete "
                f"migration check: {exc}"
            ) from exc
        pytest_names = {"pytest"}
        mark_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "pytest":
                        pytest_names.add(alias.asname or alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module == "pytest":
                for alias in node.names:
                    if alias.name == "mark":
                        mark_names.add(alias.asname or alias.name)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Attribute) or node.attr != "network":
                continue
            direct_mark_alias = (
                isinstance(node.value, ast.Name)
                and node.value.id in mark_names
            )
            pytest_mark_attribute = (
                isinstance(node.value, ast.Attribute)
                and node.value.attr == "mark"
                and isinstance(node.value.value, ast.Name)
                and node.value.value.id in pytest_names
            )
            if not direct_mark_alias and not pytest_mark_attribute:
                continue
            relative = path.relative_to(tests_root).as_posix()
            locations.append(f"{relative}:{node.lineno}")
    return tuple(locations)


# ---------------------------------------------------------------------------
# Optional coverage integration
# ---------------------------------------------------------------------------

def pytest_addoption(parser) -> None:
    network_group = parser.getgroup("moira-network")
    network_group.addoption(
        "--run-external-network",
        action="store_true",
        default=False,
        help=(
            "Permit tests marked external_network to use external network "
            "destinations. The marker, this option, and an external-only "
            "selected item set are all required."
        ),
    )

    group = parser.getgroup("moira-coverage")
    group.addoption(
        "--moira-cover-source",
        action="append",
        default=[],
        help="Coverage source package/path. Repeatable.",
    )
    group.addoption(
        "--moira-cover-include",
        action="append",
        default=[],
        help="Coverage report include pattern. Repeatable.",
    )
    group.addoption(
        "--moira-cover-preimport",
        action="append",
        default=[],
        help="Module to import before starting coverage. Repeatable.",
    )


def _finalize_session_coverage(config) -> None:
    cov = getattr(config, "_moira_coverage", None)
    if cov is None or getattr(config, "_moira_coverage_finalized", False):
        return
    cov.stop()
    cov.save()
    config._moira_coverage_finalized = True


# ---------------------------------------------------------------------------
# pytest_configure
# ---------------------------------------------------------------------------

@pytest.hookimpl(tryfirst=True)
def pytest_configure(config) -> None:
    policy = _parse_harness_config(config)
    config.stash[_HARNESS_CONFIG_KEY] = policy
    random.seed(policy.seed)

    legacy_network_markers = (
        ()
        if os.getenv("PYTEST_XDIST_WORKER")
        else _legacy_network_marker_locations(TEST_DIR)
    )
    if legacy_network_markers:
        preview = list(legacy_network_markers[:20])
        if len(legacy_network_markers) > len(preview):
            preview.append(
                "... and "
                f"{len(legacy_network_markers) - len(preview)} more occurrence(s)"
            )
        raise pytest.UsageError(
            "Legacy pytest.mark.network syntax is forbidden:\n- "
            + "\n- ".join(preview)
        )

    issues = _load_known_issues(TEST_DIR / "KNOWN_ISSUES.yml")
    config.stash[_KNOWN_ISSUES_KEY] = issues
    today = date.today()
    expired = tuple(issue for issue in issues if issue.expires < today)
    if expired:
        details = ", ".join(
            f"{issue.id} {issue.relative_path} (expired {issue.expires.isoformat()})"
            for issue in expired
        )
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

    config._moira_run_start = datetime.now()

    # xdist worker ID
    worker_id = os.getenv("PYTEST_XDIST_WORKER", "")
    if worker_id:
        os.environ["MOIRA_WORKER_ID"] = worker_id

    run_id = os.environ.setdefault(
        "MOIRA_TEST_RUN_ID",
        config._moira_run_start.strftime("%Y%m%d-%H%M%S"),
    )

    if os.getenv("MOIRA_TEST_ARTIFACTS", "0") == "1":
        artifact_base = TEST_DIR / "artifacts" / run_id
        config._moira_artifact_dir = (
            artifact_base / f"worker_{worker_id}" if worker_id else artifact_base
        )

    # Optional coverage integration for targeted module reports.
    cover_sources   = list(config.getoption("--moira-cover-source")    or [])
    cover_includes  = list(config.getoption("--moira-cover-include")   or [])
    cover_preimports = list(config.getoption("--moira-cover-preimport") or [])
    if cover_sources or cover_includes or cover_preimports:
        try:
            import coverage
        except ImportError as exc:
            raise RuntimeError(
                "Coverage support requested, but coverage.py is not installed in the active environment."
            ) from exc

        for module_name in cover_preimports:
            importlib.import_module(module_name)

        config._moira_coverage = coverage.Coverage(source=cover_sources or None)
        config._moira_coverage_includes = cover_includes
        config._moira_coverage_finalized = False
        config._moira_coverage.start()


@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart(session) -> None:
    """Receipt Hypothesis' effective policy after every configure hook ran."""
    initial_policy = session.config.stash[_HARNESS_CONFIG_KEY]
    session.config.stash[_HARNESS_CONFIG_KEY] = replace(
        initial_policy,
        hypothesis=_snapshot_hypothesis_policy(),
    )


# Ignore legacy/ folder if it ever appears
collect_ignore = ["legacy"]


# ---------------------------------------------------------------------------
# pytest_collection_modifyitems — auto-markers
# ---------------------------------------------------------------------------

# Fixtures that imply ephemeris access — auto-apply requires_ephemeris
_EPHEMERIS_FIXTURES = {"moira_engine", "natal_chart", "natal_houses"}


def _validate_network_marker_law(items) -> None:
    violations: list[str] = []
    for item in items:
        legacy_markers = tuple(item.iter_markers(name="network"))
        loopback_markers = tuple(item.iter_markers(name="loopback"))
        external_markers = tuple(item.iter_markers(name="external_network"))
        if legacy_markers:
            violations.append(
                f"{item.nodeid}: legacy @pytest.mark.network is forbidden; "
                "classify the test as loopback or external_network"
            )
        if loopback_markers and external_markers:
            violations.append(
                f"{item.nodeid}: conflicting loopback and external_network markers"
            )
        for marker in (*loopback_markers, *external_markers):
            if marker.args or marker.kwargs:
                violations.append(
                    f"{item.nodeid}: network capability markers take no arguments"
                )
    if violations:
        preview = violations[:20]
        if len(violations) > len(preview):
            preview.append(
                f"... and {len(violations) - len(preview)} more violation(s)"
            )
        raise pytest.UsageError(
            "Network marker policy violations:\n- " + "\n- ".join(preview)
        )


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config, items):
    policy = config.stash[_HARNESS_CONFIG_KEY]
    _validate_network_marker_law(items)
    for item in items:
        item_path  = Path(str(item.fspath))
        dir_parts  = {p.lower() for p in item_path.parts}

        if "ui" in dir_parts or item_path.name.startswith("test_ui_") or "qtbot" in item.fixturenames:
            item.add_marker(pytest.mark.ui)
        if "integration" in dir_parts:
            item.add_marker(pytest.mark.integration)
        if "unit" in dir_parts:
            item.add_marker(pytest.mark.unit)

        # Auto-apply requires_ephemeris when engine fixtures are used
        if not item.get_closest_marker("requires_ephemeris"):
            if _EPHEMERIS_FIXTURES & set(item.fixturenames):
                item.add_marker(pytest.mark.requires_ephemeris)

        # requires_ephemeris → skip when de441.bsp is absent and downloads disabled
        if item.get_closest_marker("requires_ephemeris"):
            no_dl = policy.no_download or policy.test_mode
            if no_dl and not _has_ephemeris():
                item.add_marker(pytest.mark.skip(reason="no planetary kernel installed and downloads disabled"))

        # slow → skip when MOIRA_SKIP_SLOW=1
        if item.get_closest_marker("slow"):
            if os.getenv("MOIRA_SKIP_SLOW", "0") == "1":
                item.add_marker(pytest.mark.skip(reason="slow tests skipped (MOIRA_SKIP_SLOW=1)"))

        # template / experimental → opt-in
        if item.get_closest_marker("template"):
            if os.getenv("MOIRA_RUN_TEMPLATES", "0") != "1":
                item.add_marker(pytest.mark.skip(reason="template tests are opt-in"))
        if item.get_closest_marker("experimental"):
            if os.getenv("MOIRA_RUN_EXPERIMENTAL", "0") != "1":
                item.add_marker(pytest.mark.skip(reason="experimental tests are opt-in"))

        if (
            item.get_closest_marker("external_network")
            and not policy.external_network_enabled
        ):
            item.add_marker(
                pytest.mark.skip(reason=_EXTERNAL_NETWORK_SKIP_REASON),
                append=False,
            )

        # Hypothesis auto-marker
        if not item.get_closest_marker("property") and hasattr(item, "function"):
            func = item.function
            if hasattr(func, "hypothesis") or hasattr(func, "hypothesis_explicit_examples"):
                item.add_marker(pytest.mark.property)

        # parallel / serial auto-detection
        if not item.get_closest_marker("parallel") and not item.get_closest_marker("serial"):
            serial_dirs = {"database", "singleton", "global_state", "file_lock", "mutex"}
            if dir_parts & serial_dirs:
                item.add_marker(pytest.mark.serial)
            else:
                item.add_marker(pytest.mark.parallel)


@pytest.hookimpl(
    trylast=True,
    specname="pytest_collection_modifyitems",
)
def pytest_collection_modifyitems_external_network_isolation(config, items):
    """Never mix external-capable and denied items in one Python process."""

    policy = config.stash[_HARNESS_CONFIG_KEY]
    config.stash[_EXTERNAL_NETWORK_SELECTED_KEY] = sum(
        bool(item.get_closest_marker("external_network"))
        for item in items
    )
    if not policy.external_network_enabled:
        return
    non_external_items = [
        item.nodeid
        for item in items
        if not item.get_closest_marker("external_network")
    ]
    if not non_external_items:
        return
    preview = non_external_items[:20]
    if len(non_external_items) > len(preview):
        preview.append(
            f"... and {len(non_external_items) - len(preview)} more item(s)"
        )
    raise pytest.UsageError(
        "--run-external-network requires an external-only pytest process. "
        "Select only explicitly marked cases, normally with "
        "'-m external_network' or exact external node IDs. "
        "Non-external selected items:\n- "
        + "\n- ".join(preview)
    )


# ---------------------------------------------------------------------------
# Safety: deny / loopback / explicitly authorized external network
# ---------------------------------------------------------------------------

def _network_mode_for_item(item) -> NetworkMode:
    policy = item.config.stash[_HARNESS_CONFIG_KEY]
    if item.get_closest_marker("external_network"):
        if policy.external_network_enabled:
            return NetworkMode.EXTERNAL
        return NetworkMode.DENY
    if item.get_closest_marker("loopback"):
        return NetworkMode.LOOPBACK
    return NetworkMode.DENY


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_protocol(item):
    """Apply one capability across fixture setup, call, and fixture teardown."""

    activate_network_mode(
        _network_mode_for_item(item),
        nodeid=item.nodeid,
    )
    try:
        yield
    finally:
        reset_network_mode()


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def _seed_test_random(request):
    """Reset Python's RNG after collection so test execution starts reproducibly."""
    random.seed(request.config.stash[_HARNESS_CONFIG_KEY].seed)


# ---------------------------------------------------------------------------
# Kernel singleton bootstrap
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def _bootstrap_kernel_singleton() -> None:
    """Configure the global SpkReader singleton once per test session.

    When a planetary kernel is available, calling set_kernel_path() here ensures
    that module-level functions (phase.apparent_magnitude, etc.) which call
    get_reader() directly can reuse the same initialized singleton without each
    test needing to go through the Moira facade.

    No-ops when no kernel is installed; requires_ephemeris tests skip naturally.
    """
    from moira._kernel_paths import find_planetary_kernel
    from moira.spk_reader import set_kernel_path

    kernel = find_planetary_kernel()
    if kernel is not None:
        set_kernel_path(str(kernel))


# ---------------------------------------------------------------------------
# Moira engine fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def moira_engine():
    """
    Session-scoped Moira engine (loads planetary kernel once for the whole run).

    Skips gracefully when no planetary kernel is present rather than crashing.
    Mark tests that use this fixture with @pytest.mark.requires_ephemeris,
    or rely on the auto-marker in pytest_collection_modifyitems.
    """
    if not _has_ephemeris():
        pytest.skip("no planetary kernel found — skipping ephemeris-dependent test")
    from moira import Moira
    return Moira()


@pytest.fixture(scope="session")
def reader(moira_engine):
    """Session-scoped SpkReader instance from the Moira engine."""
    return moira_engine._reader


@pytest.fixture(scope="session")
def eclipse_calculator(reader):
    """Session-scoped EclipseCalculator instance."""
    from moira.eclipse import EclipseCalculator
    return EclipseCalculator(reader=reader)


@pytest.fixture(scope="session")
def jd_j2000() -> float:
    """Julian Day of J2000.0 epoch (2000-Jan-1.5 TT ≈ 2000-Jan-1 12:00 UTC)."""
    return 2451545.0


@pytest.fixture(scope="session")
def natal_chart(moira_engine):
    """
    A fixed test chart: 2000-01-01 12:00:00 UTC.

    Used as a stable reference for aspect, dignity, and lot tests.
    """
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    return moira_engine.chart(dt)


@pytest.fixture(scope="session")
def natal_houses(moira_engine):
    """
    House cusps for the test chart: London (51.5°N, 0.1°W), Placidus.
    """
    from moira.constants import HouseSystem
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    return moira_engine.houses(dt, latitude=51.5, longitude=-0.1, system=HouseSystem.PLACIDUS)


# ---------------------------------------------------------------------------
# Snapshot and golden-value fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def snapshot():
    """
    Read-only comparison against an approved JSON regression witness.

    Usage::

        def test_output(snapshot):
            snapshot("my_test_name", some_result)

    Ordinary pytest cannot create or update snapshots. Candidate generation and
    reviewed promotion are separate protected-evidence operations. A snapshot
    detects implementation drift; it does not establish external truth.
    """
    from tools.snapshots import assert_snapshot
    return assert_snapshot


@pytest.fixture
def golden():
    """
    Read-only comparison against an approved golden storage record.

    Usage::

        def test_golden(golden):
            golden("my_golden_name", some_result)

    Ordinary pytest cannot create or update goldens. A golden file is only a
    storage channel; its authority comes from adjacent provenance, declared
    product semantics, and the producing validation record.
    """
    from tools.golden import assert_golden
    return assert_golden


@pytest.fixture
def ritual(snapshot, golden, request):
    """
    Generative Ritual fixture — three-phase test object.

    Separates summoning (calling the engine), witnessing (comparing a serialized
    observation with approved regression or provenance-governed storage), and
    covenanting (asserting structural and relational invariants). Witnessing
    alone does not establish scientific truth.

    Methods:
        witness(name, value, *, as_golden=False) → value
            Compare summoned output with approved storage. Returns value for
            chaining. ``as_golden=True`` selects the golden storage channel; it
            does not itself confer external authority.

        cross_witness(a, b, *, keys=None, abs_tol=None, label="")
            Assert two independently summoned values agree.
            Use for parity or invariant evidence, not external truth.

        temporal_covenant(sequence, predicate, *, label="")
            Assert predicate(a, b) holds for every consecutive pair in a sequence.
            Use for continuity, monotonicity, and bounded-step invariants over time.

    Example — single summon::

        def test_chart_is_self_consistent(moira_engine, jd_j2000, ritual, assert_longitude):
            chart = ritual.witness("chart_j2000", moira_engine.chart(jd_j2000))
            for body, pos in chart.positions.items():
                assert_longitude(pos.longitude, label=body)

    Example — cross-witness::

        def test_aspect_symmetry(moira_engine, jd_j2000, ritual):
            pos = moira_engine.positions(jd_j2000)
            ab = moira_engine.aspect(pos["Sun"], pos["Moon"])
            ba = moira_engine.aspect(pos["Moon"], pos["Sun"])
            ritual.witness("sun_moon_aspect_j2000", ab)
            ritual.cross_witness(ab, ba, keys=["orb", "angle"], label="aspect symmetry")

    Example — temporal covenant::

        def test_sun_moves_forward(moira_engine, ritual):
            jds = [2451545.0 + i for i in range(30)]
            lons = [moira_engine.planet(jd, "Sun").longitude for jd in jds]
            ritual.witness("sun_longitude_30day", lons)
            ritual.temporal_covenant(
                lons,
                lambda a, b: (b - a) % 360 < 2.0,
                label="Sun moves less than 2 degrees per day",
            )
    """
    from tools.ritual import Ritual
    return Ritual(snapshot, golden, request.node.nodeid)


# ---------------------------------------------------------------------------
# Domain fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def moira_approx():
    """
    Legacy approximate comparison fixture pending product-by-product migration.

    This wrapper is not unit-safe and treats longitude linearly. New tests must
    use named contracts from ``support.numeric_assertions``. Existing consumers
    remain until each product's units, semantics, and tolerance basis are
    reviewed; do not mechanically translate them.

    Kinds and tolerances:
        longitude  — 1e-6 degrees  (~3.6 mas, sub-arcsecond)
        distance   — 1e-9 AU       (sub-kilometre)
        angle      — 1e-4 degrees  (fine enough for aspects/orbs)
        time       — 1e-8 days     (~1 ms)
        ratio      — 1e-9          (dimensionless fractions)

    Example::

        def test_sun_longitude(moira_engine, jd_j2000, moira_approx):
            pos = moira_engine.planet(jd_j2000, "Sun")
            assert pos.longitude == moira_approx(280.459, kind="longitude")
    """
    _tolerances = {
        "longitude": 1e-6,
        "distance":  1e-9,
        "angle":     1e-4,
        "time":      1e-8,
        "ratio":     1e-9,
    }

    def _approx(value, kind: str = "longitude"):
        tol = _tolerances.get(kind)
        if tol is None:
            raise ValueError(
                f"Unknown moira_approx kind {kind!r}. "
                f"Valid kinds: {list(_tolerances)}"
            )
        return pytest.approx(value, abs=tol)

    return _approx


@pytest.fixture
def assert_longitude():
    """
    Assert that a value is a valid ecliptic longitude: in [0, 360).

    The single most common structural invariant in this codebase. Use instead
    of writing ``assert 0 <= lon < 360`` in every test.

    Example::

        def test_cusp_range(natal_houses, assert_longitude):
            for cusp in natal_houses.cusps:
                assert_longitude(cusp)
    """
    from support.numeric_assertions import assert_canonical_longitude_degrees

    def _check(value: float, label: str = "longitude") -> None:
        assert_canonical_longitude_degrees(value, label=label)

    return _check


# ---------------------------------------------------------------------------
# Pytest hooks: per-test budget, artifacts, terminal summary
# ---------------------------------------------------------------------------

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report  = outcome.get_result()
    if report.when != "call":
        return

    # Per-test budget
    case_budget = item.config.stash[_HARNESS_CONFIG_KEY].budget_case_s
    if case_budget and report.duration > case_budget:
        report.outcome  = "failed"
        report.longrepr = (
            f"Test exceeded per-test budget: {report.duration:.3f}s > {case_budget:.3f}s"
        )

    # Accumulate durations
    durations = getattr(item.config, "_moira_durations", None)
    if durations is None:
        durations = {}
        item.config._moira_durations = durations
    durations[report.nodeid] = report.duration

    # Track flakes
    if report.failed:
        flakes = getattr(item.config, "_moira_flake_counts", None)
        if flakes is None:
            flakes = {}
            item.config._moira_flake_counts = flakes
        flakes[report.nodeid] = flakes.get(report.nodeid, 0) + 1

    # Artifact recording
    artifact_dir = getattr(item.config, "_moira_artifact_dir", None)
    if artifact_dir and report.failed:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        with (artifact_dir / "failures.txt").open("a", encoding="utf-8") as f:
            f.write(f"{report.nodeid}\n{report.longrepr}\n{'-'*60}\n")


def pytest_sessionfinish(session, exitstatus):
    reset_network_mode(nodeid="<session-finish>")
    _finalize_session_coverage(session.config)

    # Total budget check
    budget_total = session.config.stash[_HARNESS_CONFIG_KEY].budget_total_s
    if budget_total:
        elapsed = (datetime.now() - session.config._moira_run_start).total_seconds()
        if elapsed > budget_total:
            pytest.exit(
                f"Test session exceeded total budget: {elapsed:.1f}s > {budget_total:.1f}s",
                returncode=1,
            )

    artifact_dir = getattr(session.config, "_moira_artifact_dir", None)
    if not artifact_dir:
        return

    # Flush durations
    durations = getattr(session.config, "_moira_durations", None)
    if durations:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        (artifact_dir / "durations.json").write_text(
            json.dumps(durations, indent=2, sort_keys=True), encoding="utf-8"
        )

    # Flush flakes
    flakes = getattr(session.config, "_moira_flake_counts", None)
    if flakes:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        (artifact_dir / "flake_report.json").write_text(
            json.dumps({"tests": flakes, "run_id": os.getenv("MOIRA_TEST_RUN_ID", "")},
                       indent=2, sort_keys=True),
            encoding="utf-8",
        )

    # Merge worker artifacts (main process only)
    if not os.getenv("PYTEST_XDIST_WORKER"):
        try:
            worker_dirs = [
                d for d in artifact_dir.parent.iterdir()
                if d.is_dir() and d.name.startswith("worker_")
            ]
        except FileNotFoundError:
            worker_dirs = []
        if worker_dirs:
            try:
                from tools.merge_worker_artifacts import merge_durations, merge_failures
                md = merge_durations(artifact_dir.parent)
                mf = merge_failures(artifact_dir.parent)
                if md:
                    (artifact_dir / "durations.json").write_text(
                        json.dumps(md, indent=2, sort_keys=True), encoding="utf-8"
                    )
                if mf:
                    (artifact_dir / "failures.txt").write_text(
                        "\n".join(mf) + "\n", encoding="utf-8"
                    )
            except Exception:
                pass

    # Write PowerShell rerun helper for failures
    failures_path = artifact_dir / "failures.txt"
    if not failures_path.exists():
        return
    nodeids = []
    for raw in failures_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("-"):
            continue
        if line.startswith("tests"):
            nodeids.append(line.split()[0])
    seen: set[str] = set()
    unique = [n for n in nodeids if n not in seen and not seen.add(n)]  # type: ignore[func-returns-value]
    if not unique:
        return
    invoked_cmd = "pytest " + " ".join(session.config.invocation_params.args)
    timestamp   = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# Generated: {timestamp}",
        f"# From: {invoked_cmd}",
        '$ErrorActionPreference = "Stop"',
        '$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\\..\\..")',
        '$python = "py" "-3.14"',
        "$nodeids = @(",
        *[f'  "{n}"' for n in unique],
        ")",
        "& $python -m pytest @nodeids",
    ]
    (artifact_dir / "rerun.ps1").write_text("\n".join(lines) + "\n", encoding="utf-8")


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Print slowest tests and performance regressions."""
    _finalize_session_coverage(config)

    policy = config.stash.get(_HARNESS_CONFIG_KEY, None)
    if policy is not None:
        terminalreporter.section("Moira: harness policy receipt")
        terminalreporter.write_line(
            "  Hypothesis: "
            f"profile={policy.hypothesis.profile}, "
            f"max_examples={policy.hypothesis.max_examples}, "
            f"database={policy.hypothesis.database_policy}, "
            f"derandomize={policy.hypothesis.derandomize}"
        )
        terminalreporter.write_line(
            "  Network: default=deny, loopback=marked-only, "
            "external="
            + (
                "enabled by --run-external-network"
                if policy.external_network_enabled
                else "disabled"
            )
        )
        external_count = config.stash.get(
            _EXTERNAL_NETWORK_SELECTED_KEY,
            0,
        )
        if external_count and not policy.external_network_enabled:
            terminalreporter.write_line(
                "  External network: "
                f"{external_count} marked item(s) held in deny mode and "
                f"skipped: {_EXTERNAL_NETWORK_SKIP_REASON}"
            )
        elif policy.external_network_enabled:
            terminalreporter.write_line(
                "  External network: authorized in an isolated "
                "external_network-only process"
            )

    durations = getattr(config, "_moira_durations", None)
    if durations:
        n_slow     = 5
        sorted_dur = sorted(durations.items(), key=lambda kv: kv[1], reverse=True)
        if sorted_dur:
            terminalreporter.section("Moira: slowest tests")
            for nodeid, dur in sorted_dur[:n_slow]:
                terminalreporter.write_line(f"  {dur:7.3f}s  {nodeid}")

        baseline_path = TEST_DIR / "artifacts" / "durations_baseline.json"
        if baseline_path.exists():
            try:
                baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
            except Exception:
                baseline = None
            if baseline:
                threshold   = float(os.getenv("MOIRA_REGRESSION_PCT", "50")) / 100.0
                regressions = [
                    (nodeid, base, cur)
                    for nodeid, cur in durations.items()
                    if (base := baseline.get(nodeid)) and base > 0 and (cur - base) / base >= threshold
                ]
                if regressions:
                    terminalreporter.section("Moira: performance regressions")
                    for nodeid, base, cur in sorted(regressions, key=lambda r: r[2] - r[1], reverse=True):
                        pct = (cur - base) / base * 100
                        terminalreporter.write_line(f"  {nodeid}:  {base:.3f}s -> {cur:.3f}s  (+{pct:.0f}%)")

    cov = getattr(config, "_moira_coverage", None)
    includes = getattr(config, "_moira_coverage_includes", None)
    if cov is not None:
        buffer = io.StringIO()
        try:
            cov.report(include=includes or None, file=buffer)
        except Exception as exc:
            terminalreporter.section("Moira: coverage")
            terminalreporter.write_line(f"  coverage report failed: {exc}")
        else:
            terminalreporter.section("Moira: coverage")
            for line in buffer.getvalue().splitlines():
                terminalreporter.write_line(f"  {line}")


# ---------------------------------------------------------------------------
# pytest-xdist node configuration (only registered when installed)
# ---------------------------------------------------------------------------

try:
    import xdist  # noqa: F401

    @pytest.hookimpl(optionalhook=True)
    def pytest_configure_node(node):
        policy = node.config.stash[_HARNESS_CONFIG_KEY]
        node.workerinput["moira_test_seed"] = str(policy.seed)
        node.workerinput["moira_test_mode"] = "1" if policy.test_mode else "0"
        node.workerinput["workerid"] = node.workerinput.get("workerid", "gw0")

except ImportError:
    pass
