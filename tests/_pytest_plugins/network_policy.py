"""Deny-by-default pytest network capability policy."""

from __future__ import annotations

import ast
import os
from pathlib import Path
import tokenize

import pytest

from support.network_policy import (
    NetworkMode,
    activate_network_mode,
    install_network_audit_hook,
    reset_network_mode,
)

from ._state import (
    TEST_DIR,
    _EXTERNAL_NETWORK_SELECTED_KEY,
    _HARNESS_CONFIG_KEY,
)


EXTERNAL_NETWORK_SKIP_REASON = (
    "external network test requires the explicit --run-external-network option"
)


def _prepend_child_policy_import_path() -> None:
    """Expose only the cooperative child-policy bootstrap on ``PYTHONPATH``."""

    bootstrap_entry = str(TEST_DIR / "support" / "network_bootstrap")
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


def register_options(parser) -> None:
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


def _legacy_network_marker_locations(
    tests_root: Path,
) -> tuple[str, ...]:
    """Find executable ``pytest.mark.network`` syntax, even when uncollected."""

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


def validate_marker_law(items) -> None:
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
                f"{item.nodeid}: conflicting loopback and external_network "
                "markers"
            )
        for marker in (*loopback_markers, *external_markers):
            if marker.args or marker.kwargs:
                violations.append(
                    f"{item.nodeid}: network capability markers take no "
                    "arguments"
                )
    if not violations:
        return
    preview = violations[:20]
    if len(violations) > len(preview):
        preview.append(
            f"... and {len(violations) - len(preview)} more violation(s)"
        )
    raise pytest.UsageError(
        "Network marker policy violations:\n- " + "\n- ".join(preview)
    )


def prepare_item(item, policy) -> None:
    if (
        item.get_closest_marker("external_network")
        and not policy.external_network_enabled
    ):
        item.add_marker(
            pytest.mark.skip(reason=EXTERNAL_NETWORK_SKIP_REASON),
            append=False,
        )


def reset_session_network_mode() -> None:
    reset_network_mode(nodeid="<session-finish>")


def write_terminal_summary(terminalreporter, config, policy) -> None:
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
            f"skipped: {EXTERNAL_NETWORK_SKIP_REASON}"
        )
    elif policy.external_network_enabled:
        terminalreporter.write_line(
            "  External network: authorized in an isolated "
            "external_network-only process"
        )


@pytest.hookimpl
def pytest_configure(config) -> None:
    if getattr(config, "workerinput", None) is not None:
        return
    legacy_network_markers = _legacy_network_marker_locations(TEST_DIR)
    if not legacy_network_markers:
        return
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
    """Apply one capability across fixture setup, call, and teardown."""

    activate_network_mode(
        _network_mode_for_item(item),
        nodeid=item.nodeid,
    )
    try:
        yield
    finally:
        reset_network_mode()
