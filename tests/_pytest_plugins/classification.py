"""Execution classification and frozen-lane policy."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re

import pytest
from _pytest.compat import NOTSET

from ._state import (
    TEST_DIR,
    _CLASSIFICATION_RECEIPT_KEY,
    _COLLECTED_EXECUTION_ITEMS_KEY,
    _EXECUTION_CLASSIFICATION_FROZEN_KEY,
    _EXECUTION_CLASSIFICATION_IDENTITY_ITEM_KEY,
    _HARNESS_CONFIG_KEY,
    _PRIMARY_CLASS_ITEM_KEY,
    _XDIST_CLASSIFICATION_ERRORS_STATE_KEY,
    _XDIST_CLASSIFICATION_EXPECTED_STATE_KEY,
    _XDIST_CLASSIFICATION_REPORTED_STATE_KEY,
    _XDIST_CLASSIFICATION_REPORT_STATE_KEY,
    _XDIST_MODE_KEY,
    _XDIST_WORKER_CLASSIFICATION_VIOLATION_COUNT_STATE_KEY,
    _XDIST_WORKER_CLASSIFICATION_VIOLATIONS_STATE_KEY,
    _XDIST_WORKER_ACTIVE_KEY,
    _ExecutionClassificationReceipt,
)
from .determinism import mark_property_test
from .network_policy import (
    prepare_item as _prepare_network_item,
    validate_marker_law as _validate_network_marker_law,
)
from .resources import prepare_item as _prepare_resource_item


_PRIMARY_CLASSES = (
    "legacy_root",
    "governance",
    "harness",
    "integration",
    "metamorphic",
    "oracle",
    "server",
    "stress",
    "unit",
)


_PRIMARY_DIRECTORY_CLASSES = {
    "export_governance": "governance",
    "harness_meta": "harness",
    "integration": "integration",
    "metamorphic": "metamorphic",
    "oracle": "oracle",
    "server": "server",
    "stress": "stress",
    "unit": "unit",
}


_CONCURRENCY_CLASSES = ("local_only", "parallel", "serial")


_PARALLEL_REASONS = frozenset(
    {
        "isolated_resources",
        "read_only",
        "worker_isolated",
    }
)


_SERIAL_REASONS = frozenset(
    {
        "external_rate_limit",
        "filesystem_lock",
        "global_state",
        "lane_canary",
        "nested_runner",
        "resource_mutation",
        "shared_cache",
        "singleton",
    }
)


_CLASSIFICATION_SCHEMA_VERSION = 1


_XDIST_CLASSIFICATION_REPORT_KEY = "moira_execution_classification_v1"


_XDIST_CLASSIFICATION_VIOLATIONS_KEY = (
    "moira_execution_classification_violations_v1"
)


_MAX_XDIST_CLASSIFICATION_VIOLATION_DETAILS = 20


_MARKER_REGISTRATIONS = (
    "legacy_root: primary path class for legacy tests directly under tests/",
    "governance: primary class for export-governance tests",
    "harness: primary class for pytest-harness policy tests",
    "integration: primary class for multi-module or resource-bound tests",
    "metamorphic: primary class for reviewed invariant and relation tests",
    "oracle: primary class for external-authority comparison tests",
    "server: primary class for optional server-transport tests",
    "stress: primary class for explicitly bounded stress tests",
    "unit: primary class for isolated unit tests",
    "required_enumeration: parametrized source is required to contain at least one case",
    "optional_enumeration(reason=...): parametrized source may be empty for the stated reason",
    "parallel(reason=...): explicitly admitted to pytest-xdist execution",
    "serial(reason=...): must execute in the local pytest -n 0 lane",
    "validation_contract(claim_id): bind a selected validation test to one reviewed machine-checkable evidence contract",
    "loopback: numeric loopback or AF_UNIX local IPC capability",
    "external_network: explicit external access capability",
    "network: forbidden legacy network marker",
    "slow: test takes more than approximately five seconds",
    "requires_ephemeris: typed planetary-kernel capability",
    "property: property-based test",
    "lola: LOLA lunar-topography substrate test",
    "numpy_free_lunar_limb: native or standard-library lunar-limb path",
    "template: opt-in template test",
    "experimental: opt-in experimental test",
    "ui: test requires a Qt application instance",
)


def _register_harness_markers(config) -> None:
    """Register constitutional markers before strict collection begins."""

    for registration in _MARKER_REGISTRATIONS:
        config.addinivalue_line("markers", registration)


def _enforce_strict_pytest_configuration(config) -> None:
    """Make strict markers/configuration non-optional for harness consumers."""

    weakened: list[str] = []
    for override in tuple(getattr(config.option, "override_ini", ()) or ()):
        name, separator, raw_value = str(override).partition("=")
        if (
            separator
            and name.strip() in {"strict_config", "strict_markers"}
            and raw_value.strip().casefold() in {"", "0", "false", "no", "off"}
        ):
            weakened.append(str(override))
    if weakened:
        raise pytest.UsageError(
            "Moira pytest strictness cannot be weakened with -o: "
            + ", ".join(weakened)
        )

    missing_strictness: list[str] = []
    for name in ("strict_config", "strict_markers"):
        value = config.getini(name)
        if value is None:
            value = config.getini("strict")
        if value is not True:
            missing_strictness.append(name)
    if missing_strictness:
        raise pytest.UsageError(
            "Moira pytest configuration requires effective "
            + "=true and ".join(missing_strictness)
            + "=true"
        )

    known_ini = set(getattr(config._parser, "_inidict", {}))
    unknown_ini = sorted(set(config.inicfg) - known_ini)
    if unknown_ini:
        raise pytest.UsageError(
            "Unknown pytest configuration option(s): "
            + ", ".join(unknown_ini)
        )


@pytest.hookimpl
def pytest_configure(config) -> None:
    """Establish immutable execution-lane state before collection."""

    workerinput = getattr(config, "workerinput", None)
    is_xdist_worker = isinstance(workerinput, dict)
    config.stash[_XDIST_WORKER_ACTIVE_KEY] = is_xdist_worker
    config.stash[_XDIST_MODE_KEY] = (
        str(workerinput.get("moira_xdist_mode", "load"))
        if is_xdist_worker
        else str(getattr(config.option, "dist", "no") or "no")
    )
    _register_harness_markers(config)
    _enforce_strict_pytest_configuration(config)
    if not is_xdist_worker and config.stash[_XDIST_MODE_KEY] == "each":
        raise pytest.UsageError(
            "--dist=each duplicates selected tests and is not admitted by "
            "the Phase 6 execution receipt"
        )


def _registered_marker_violations(config, items) -> list[str]:
    registered = {
        line.split(":", 1)[0].split("(", 1)[0].strip()
        for line in config.getini("markers")
    }
    violations: list[str] = []
    for item in items:
        unknown = sorted(
            {
                marker.name
                for marker in item.iter_markers()
                if marker.name not in registered
            }
        )
        if unknown:
            violations.append(
                f"{item.nodeid}: unregistered marker(s) "
                + ", ".join(unknown)
            )
    return violations


def _validate_registered_marker_law(config, items) -> None:
    """Reject unknown markers even if another plugin mutates items late."""

    _raise_collection_policy_violations(
        "Strict marker policy violations",
        _registered_marker_violations(config, items),
    )


def _raise_collection_policy_violations(
    title: str,
    violations: list[str],
) -> None:
    if not violations:
        return
    preview = violations[:20]
    if len(violations) > len(preview):
        preview.append(
            f"... and {len(violations) - len(preview)} more violation(s)"
        )
    raise pytest.UsageError(title + ":\n- " + "\n- ".join(preview))


def _relative_test_path(item) -> Path:
    """Resolve an item's source beneath ``tests/`` without parent-name leaks."""

    try:
        tests_root = TEST_DIR.resolve(strict=True)
        item_path = Path(str(item.path)).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ValueError(f"source path cannot be resolved: {exc}") from exc
    try:
        return item_path.relative_to(tests_root)
    except ValueError as exc:
        raise ValueError(
            f"source path escapes tests/: {item_path}"
        ) from exc


def _derived_primary_class(relative_path: Path) -> str:
    if len(relative_path.parts) == 1:
        return "legacy_root"
    primary = _PRIMARY_DIRECTORY_CLASSES.get(
        relative_path.parts[0].casefold()
    )
    if primary is None:
        raise ValueError(
            "unmapped tests/ top-level directory "
            f"{relative_path.parts[0]!r}"
        )
    return primary


def _validate_primary_class(
    item,
    *,
    add_missing: bool,
    violations: list[str],
) -> Path | None:
    try:
        relative_path = _relative_test_path(item)
        derived = _derived_primary_class(relative_path)
    except ValueError as exc:
        violations.append(f"{item.nodeid}: {exc}")
        return None

    declared: list[str] = []
    for marker_name in _PRIMARY_CLASSES:
        for marker in item.iter_markers(name=marker_name):
            if marker.args or marker.kwargs:
                violations.append(
                    f"{item.nodeid}: primary marker {marker_name!r} "
                    "takes no arguments"
                )
            declared.append(marker_name)

    distinct = set(declared)
    if len(distinct) > 1:
        violations.append(
            f"{item.nodeid}: conflicting primary classes "
            + ", ".join(sorted(distinct))
        )
    elif distinct and distinct != {derived}:
        violations.append(
            f"{item.nodeid}: primary class {next(iter(distinct))!r} "
            f"contradicts tests/-relative class {derived!r}"
        )
    elif not distinct:
        if add_missing:
            item.add_marker(getattr(pytest.mark, derived))
        else:
            violations.append(
                f"{item.nodeid}: primary class marker disappeared after "
                "initial classification"
            )

    stored = item.stash.get(_PRIMARY_CLASS_ITEM_KEY, None)
    if stored is not None and stored != derived:
        violations.append(
            f"{item.nodeid}: primary class changed from {stored!r} "
            f"to {derived!r}"
        )
    item.stash[_PRIMARY_CLASS_ITEM_KEY] = derived
    return relative_path


def _validate_reason_marker(
    item,
    *,
    marker_name: str,
    allowed_reasons: frozenset[str] | None,
    violations: list[str],
) -> tuple[object, ...]:
    markers = tuple(item.iter_markers(name=marker_name))
    reasons: list[str] = []
    for marker in markers:
        if marker.args or set(marker.kwargs) != {"reason"}:
            violations.append(
                f"{item.nodeid}: {marker_name} requires exactly one "
                "keyword argument, reason=..."
            )
            continue
        reason = marker.kwargs.get("reason")
        if (
            not isinstance(reason, str)
            or re.fullmatch(r"[a-z][a-z0-9_]{2,63}", reason) is None
        ):
            violations.append(
                f"{item.nodeid}: {marker_name} reason must be a stable "
                "lowercase slug"
            )
            continue
        if allowed_reasons is not None and reason not in allowed_reasons:
            violations.append(
                f"{item.nodeid}: unsupported {marker_name} reason "
                f"{reason!r}; expected one of "
                + ", ".join(sorted(allowed_reasons))
            )
        reasons.append(reason)
    if len(set(reasons)) > 1:
        violations.append(
            f"{item.nodeid}: inherited {marker_name} declarations disagree "
            "on their reason"
        )
    return markers


def _validate_no_argument_marker(
    item,
    marker_name: str,
    violations: list[str],
) -> tuple[object, ...]:
    markers = tuple(item.iter_markers(name=marker_name))
    for marker in markers:
        if marker.args or marker.kwargs:
            violations.append(
                f"{item.nodeid}: {marker_name} takes no arguments"
            )
    return markers


def _callspec_is_empty(item) -> bool:
    callspec = getattr(item, "callspec", None)
    if callspec is None:
        return False
    return any(value is NOTSET for value in callspec.params.values())


def _validate_enumeration_contract(item, violations: list[str]) -> None:
    required = _validate_no_argument_marker(
        item,
        "required_enumeration",
        violations,
    )
    optional = _validate_reason_marker(
        item,
        marker_name="optional_enumeration",
        allowed_reasons=None,
        violations=violations,
    )
    if required and optional:
        violations.append(
            f"{item.nodeid}: required_enumeration and "
            "optional_enumeration conflict"
        )

    callspec = getattr(item, "callspec", None)
    if (required or optional) and callspec is None:
        violations.append(
            f"{item.nodeid}: enumeration marker requires a parametrized case"
        )
        return

    empty = _callspec_is_empty(item)
    if empty and required:
        violations.append(
            f"{item.nodeid}: required enumeration produced an empty "
            "parameter set"
        )
    elif empty and not optional:
        violations.append(
            f"{item.nodeid}: empty parameter set must be classified with "
            "required_enumeration or optional_enumeration(reason=...)"
        )


def _validate_concurrency_contract(item, violations: list[str]) -> str:
    parallel = _validate_reason_marker(
        item,
        marker_name="parallel",
        allowed_reasons=_PARALLEL_REASONS,
        violations=violations,
    )
    serial = _validate_reason_marker(
        item,
        marker_name="serial",
        allowed_reasons=_SERIAL_REASONS,
        violations=violations,
    )
    if parallel and serial:
        violations.append(
            f"{item.nodeid}: parallel and serial markers conflict"
        )
        return "conflict"
    if parallel:
        return "parallel"
    if serial:
        return "serial"
    return "local_only"


def _validate_execution_item(
    item,
    *,
    add_primary: bool,
    violations: list[str],
) -> Path | None:
    relative_path = _validate_primary_class(
        item,
        add_missing=add_primary,
        violations=violations,
    )
    _validate_concurrency_contract(item, violations)
    _validate_enumeration_contract(item, violations)
    return relative_path


def _execution_classification_identity(item) -> tuple[object, ...]:
    concurrency = _validate_concurrency_contract(item, [])
    primary_markers = tuple(
        sorted(
            marker_name
            for marker_name in _PRIMARY_CLASSES
            for _marker in item.iter_markers(name=marker_name)
        )
    )
    concurrency_reasons = tuple(
        sorted(
            (
                marker_name,
                str(marker.kwargs.get("reason")),
            )
            for marker_name in ("parallel", "serial")
            for marker in item.iter_markers(name=marker_name)
        )
    )
    optional_reasons = tuple(
        sorted(
            str(marker.kwargs.get("reason"))
            for marker in item.iter_markers(name="optional_enumeration")
        )
    )
    return (
        item.nodeid,
        item.stash.get(_PRIMARY_CLASS_ITEM_KEY, "<missing>"),
        primary_markers,
        concurrency,
        concurrency_reasons,
        len(tuple(item.iter_markers(name="required_enumeration"))),
        optional_reasons,
        _callspec_is_empty(item),
    )


def _classification_digest(items) -> str:
    rows = [_execution_classification_identity(item) for item in items]
    encoded = json.dumps(
        sorted(rows),
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _class_counts(items) -> tuple[tuple[str, int], ...]:
    counts = Counter(
        item.stash.get(_PRIMARY_CLASS_ITEM_KEY, "<missing>")
        for item in items
    )
    return tuple((name, counts[name]) for name in _PRIMARY_CLASSES)


def _concurrency_counts(items) -> tuple[tuple[str, int], ...]:
    counts = Counter(_validate_concurrency_contract(item, []) for item in items)
    return tuple((name, counts[name]) for name in _CONCURRENCY_CLASSES)


def _build_classification_receipt(
    collected_items: tuple[object, ...],
    selected_items: tuple[object, ...],
) -> _ExecutionClassificationReceipt:
    collected_nodeids = [item.nodeid for item in collected_items]
    selected_nodeids = [item.nodeid for item in selected_items]
    if len(set(collected_nodeids)) != len(collected_nodeids):
        raise pytest.UsageError(
            "Execution classification cannot receipt duplicate collected "
            "node IDs."
        )
    if len(set(selected_nodeids)) != len(selected_nodeids):
        raise pytest.UsageError(
            "Execution classification cannot receipt duplicate selected "
            "node IDs."
        )
    collected_object_ids = {id(item) for item in collected_items}
    foreign_selected = [
        item.nodeid
        for item in selected_items
        if id(item) not in collected_object_ids
    ]
    if foreign_selected:
        raise pytest.UsageError(
            "A collection plugin replaced or added selected items after "
            "Moira's initial classification: "
            + ", ".join(foreign_selected[:20])
        )
    unknown_selected = sorted(set(selected_nodeids) - set(collected_nodeids))
    if unknown_selected:
        raise pytest.UsageError(
            "A collection plugin added selected items after Moira's initial "
            "classification: "
            + ", ".join(unknown_selected[:20])
        )

    return _ExecutionClassificationReceipt(
        schema_version=_CLASSIFICATION_SCHEMA_VERSION,
        collected=len(collected_items),
        selected=len(selected_items),
        deselected=len(collected_items) - len(selected_items),
        primary_collected=_class_counts(collected_items),
        primary_selected=_class_counts(selected_items),
        concurrency_selected=_concurrency_counts(selected_items),
        optional_empty_collected=sum(
            _callspec_is_empty(item)
            and bool(item.get_closest_marker("optional_enumeration"))
            for item in collected_items
        ),
        optional_empty_selected=sum(
            _callspec_is_empty(item)
            and bool(item.get_closest_marker("optional_enumeration"))
            for item in selected_items
        ),
        collected_digest=_classification_digest(collected_items),
        selected_digest=_classification_digest(selected_items),
    )


def _xdist_mode(config) -> str:
    return config.stash.get(
        _XDIST_MODE_KEY,
        str(getattr(config.option, "dist", "no") or "no"),
    )


def _assert_live_xdist_scheduler_mode(config, *, boundary: str) -> None:
    """Reject scheduler-policy mutation after Moira's configure-time admission."""
    admitted_mode = _xdist_mode(config)
    live_mode = str(getattr(config.option, "dist", "no") or "no")
    if live_mode != admitted_mode:
        raise pytest.UsageError(
            "pytest-xdist scheduler mode changed after Moira admission "
            f"at {boundary}: admitted={admitted_mode!r}, live={live_mode!r}"
        )
    if live_mode == "each":
        raise pytest.UsageError(
            "--dist=each duplicates selected tests and is not admitted by "
            "the Phase 6 execution receipt"
        )


def _is_xdist_worker(config) -> bool:
    return config.stash.get(
        _XDIST_WORKER_ACTIVE_KEY,
        isinstance(getattr(config, "workerinput", None), dict),
    )


def _xdist_active(config) -> bool:
    return _is_xdist_worker(config) or _xdist_mode(config) != "no"


def _xdist_admission_violations(config, items) -> list[str]:
    mode = _xdist_mode(config)
    if not _xdist_active(config):
        return []
    violations: list[str] = []
    if mode == "each":
        violations.append(
            "--dist=each duplicates selected tests and is not admitted by "
            "the Phase 6 execution receipt"
        )
    for item in items:
        concurrency = _validate_concurrency_contract(item, [])
        if concurrency != "parallel":
            violations.append(
                f"{item.nodeid}: xdist selected a {concurrency} item; "
                "distributed execution requires "
                "@pytest.mark.parallel(reason=...)"
            )
    return violations


def _quarantine_xdist_worker_items(
    config,
    items,
    violations: list[str],
) -> None:
    """Prevent invalid worker selections from becoming xdist internal errors."""

    existing = config.stash.get(
        _XDIST_WORKER_CLASSIFICATION_VIOLATIONS_STATE_KEY,
        None,
    )
    if existing is None:
        existing = []
        config.stash[
            _XDIST_WORKER_CLASSIFICATION_VIOLATIONS_STATE_KEY
        ] = existing
    total = config.stash.get(
        _XDIST_WORKER_CLASSIFICATION_VIOLATION_COUNT_STATE_KEY,
        0,
    )
    config.stash[
        _XDIST_WORKER_CLASSIFICATION_VIOLATION_COUNT_STATE_KEY
    ] = total + len(violations)
    remaining = max(
        0,
        _MAX_XDIST_CLASSIFICATION_VIOLATION_DETAILS - len(existing),
    )
    existing.extend(violations[:remaining])
    items[:] = []


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_collection_modifyitems(config, items):
    policy = config.stash[_HARNESS_CONFIG_KEY]
    _validate_network_marker_law(items)
    _validate_registered_marker_law(config, items)
    collected_items = tuple(items)
    config.stash[_COLLECTED_EXECUTION_ITEMS_KEY] = collected_items
    config.stash[_EXECUTION_CLASSIFICATION_FROZEN_KEY] = False
    violations: list[str] = []

    for item in items:
        relative_path = _validate_execution_item(
            item,
            add_primary=True,
            violations=violations,
        )
        relative_parts = (
            {part.casefold() for part in relative_path.parts}
            if relative_path is not None
            else set()
        )

        if (
            "ui" in relative_parts
            or Path(str(item.path)).name.startswith("test_ui_")
            or "qtbot" in item.fixturenames
        ):
            item.add_marker(pytest.mark.ui)

        _prepare_resource_item(item)

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

        _prepare_network_item(item, policy)

        mark_property_test(item)

    if violations:
        if _is_xdist_worker(config):
            _quarantine_xdist_worker_items(config, items, violations)
            yield
            return
        _raise_collection_policy_violations(
            "Execution classification policy violations",
            violations,
        )

    for item in collected_items:
        item.stash[_EXECUTION_CLASSIFICATION_IDENTITY_ITEM_KEY] = (
            _execution_classification_identity(item)
        )
    config.stash[_EXECUTION_CLASSIFICATION_FROZEN_KEY] = True

    yield

    post_selection_violations = _frozen_classification_violations(
        config,
        collected_items,
    )
    if post_selection_violations:
        if _is_xdist_worker(config):
            _quarantine_xdist_worker_items(
                config,
                items,
                post_selection_violations,
            )
            return
        _raise_collection_policy_violations(
            "Post-selection execution classification policy violations",
            post_selection_violations,
        )

    receipt = _build_classification_receipt(
        collected_items,
        tuple(items),
    )
    config.stash[_CLASSIFICATION_RECEIPT_KEY] = receipt
    admission_violations = _xdist_admission_violations(config, items)
    if admission_violations:
        if _is_xdist_worker(config):
            _quarantine_xdist_worker_items(
                config,
                items,
                admission_violations,
            )
            return
        _raise_collection_policy_violations(
            "Pytest-xdist execution admission violations",
            admission_violations,
        )


def _frozen_classification_violations(config, items) -> list[str]:
    violations = _registered_marker_violations(config, items)
    for item in items:
        _validate_execution_item(
            item,
            add_primary=False,
            violations=violations,
        )
        frozen = item.stash.get(
            _EXECUTION_CLASSIFICATION_IDENTITY_ITEM_KEY,
            None,
        )
        current = _execution_classification_identity(item)
        if frozen is None:
            violations.append(
                f"{item.nodeid}: no frozen execution classification exists"
            )
        elif current != frozen:
            violations.append(
                f"{item.nodeid}: execution classification changed after "
                "initial classification"
            )
    return violations


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_collection_finish(session):
    """Reject marker mutation after the final selection hook has returned."""

    yield
    if not session.config.stash.get(
        _EXECUTION_CLASSIFICATION_FROZEN_KEY,
        False,
    ):
        return
    collected_items = session.config.stash.get(
        _COLLECTED_EXECUTION_ITEMS_KEY,
        None,
    )
    if collected_items is None:
        return
    violations = _frozen_classification_violations(
        session.config,
        collected_items,
    )
    if not violations:
        return
    if _is_xdist_worker(session.config):
        _quarantine_xdist_worker_items(
            session.config,
            [],
            violations,
        )
        return
    _raise_collection_policy_violations(
        "Frozen execution classification policy violations",
        violations,
    )


@pytest.hookimpl(
    tryfirst=True,
    specname="pytest_runtest_setup",
)
def pytest_runtest_setup_execution_classification(item):
    """Fail before fixture setup if a plugin mutates the admitted test lane."""

    violations = _frozen_classification_violations(item.config, (item,))
    if not violations and _is_xdist_worker(item.config):
        if _validate_concurrency_contract(item, []) != "parallel":
            violations.append(
                f"{item.nodeid}: xdist runtime admission is not parallel"
            )
    if violations:
        pytest.fail(
            "Frozen execution classification policy violations:\n- "
            + "\n- ".join(violations[:20]),
            pytrace=False,
        )


def _serialize_classification_receipt(
    receipt: _ExecutionClassificationReceipt,
) -> dict[str, object]:
    return {
        "schema_version": receipt.schema_version,
        "collected": receipt.collected,
        "selected": receipt.selected,
        "deselected": receipt.deselected,
        "primary_collected": [list(pair) for pair in receipt.primary_collected],
        "primary_selected": [list(pair) for pair in receipt.primary_selected],
        "concurrency_selected": [
            list(pair) for pair in receipt.concurrency_selected
        ],
        "optional_empty_collected": receipt.optional_empty_collected,
        "optional_empty_selected": receipt.optional_empty_selected,
        "collected_digest": receipt.collected_digest,
        "selected_digest": receipt.selected_digest,
    }


def _classification_count_pairs(
    raw: object,
    *,
    expected_names: tuple[str, ...],
    label: str,
) -> tuple[tuple[str, int], ...]:
    if not isinstance(raw, list) or len(raw) != len(expected_names):
        raise ValueError(
            f"{label} must contain exactly {len(expected_names)} entries"
        )
    parsed: list[tuple[str, int]] = []
    for index, expected_name in enumerate(expected_names):
        pair = raw[index]
        if (
            not isinstance(pair, list)
            or len(pair) != 2
            or pair[0] != expected_name
            or type(pair[1]) is not int
            or pair[1] < 0
        ):
            raise ValueError(
                f"{label}[{index}] must be "
                f"[{expected_name!r}, nonnegative integer]"
            )
        parsed.append((expected_name, pair[1]))
    return tuple(parsed)


def _deserialize_classification_receipt(
    payload: object,
    *,
    source: str,
) -> _ExecutionClassificationReceipt:
    fields = {
        "schema_version",
        "collected",
        "selected",
        "deselected",
        "primary_collected",
        "primary_selected",
        "concurrency_selected",
        "optional_empty_collected",
        "optional_empty_selected",
        "collected_digest",
        "selected_digest",
    }
    if not isinstance(payload, dict) or set(payload) != fields:
        raise ValueError(
            f"{source} classification receipt has an invalid field set"
        )

    integer_fields = (
        "schema_version",
        "collected",
        "selected",
        "deselected",
        "optional_empty_collected",
        "optional_empty_selected",
    )
    for field in integer_fields:
        value = payload[field]
        if type(value) is not int or value < 0:
            raise ValueError(
                f"{source} classification receipt field {field!r} "
                "must be a nonnegative integer"
            )
    if payload["schema_version"] != _CLASSIFICATION_SCHEMA_VERSION:
        raise ValueError(
            f"{source} classification receipt has unsupported schema "
            f"{payload['schema_version']!r}"
        )

    primary_collected = _classification_count_pairs(
        payload["primary_collected"],
        expected_names=_PRIMARY_CLASSES,
        label=f"{source} primary_collected",
    )
    primary_selected = _classification_count_pairs(
        payload["primary_selected"],
        expected_names=_PRIMARY_CLASSES,
        label=f"{source} primary_selected",
    )
    concurrency_selected = _classification_count_pairs(
        payload["concurrency_selected"],
        expected_names=_CONCURRENCY_CLASSES,
        label=f"{source} concurrency_selected",
    )

    for field in ("collected_digest", "selected_digest"):
        value = payload[field]
        if (
            not isinstance(value, str)
            or re.fullmatch(r"[0-9a-f]{64}", value) is None
        ):
            raise ValueError(
                f"{source} classification receipt field {field!r} "
                "must be a SHA-256 hex digest"
            )

    receipt = _ExecutionClassificationReceipt(
        schema_version=payload["schema_version"],
        collected=payload["collected"],
        selected=payload["selected"],
        deselected=payload["deselected"],
        primary_collected=primary_collected,
        primary_selected=primary_selected,
        concurrency_selected=concurrency_selected,
        optional_empty_collected=payload["optional_empty_collected"],
        optional_empty_selected=payload["optional_empty_selected"],
        collected_digest=payload["collected_digest"],
        selected_digest=payload["selected_digest"],
    )
    if receipt.collected != sum(value for _, value in primary_collected):
        raise ValueError(
            f"{source} classification receipt collected total contradicts "
            "its primary counts"
        )
    if receipt.selected != sum(value for _, value in primary_selected):
        raise ValueError(
            f"{source} classification receipt selected total contradicts "
            "its primary counts"
        )
    if receipt.selected != sum(value for _, value in concurrency_selected):
        raise ValueError(
            f"{source} classification receipt selected total contradicts "
            "its concurrency counts"
        )
    if receipt.deselected != receipt.collected - receipt.selected:
        raise ValueError(
            f"{source} classification receipt deselection arithmetic "
            "is contradictory"
        )
    if (
        receipt.optional_empty_collected > receipt.collected
        or receipt.optional_empty_selected > receipt.selected
        or receipt.optional_empty_selected > receipt.optional_empty_collected
    ):
        raise ValueError(
            f"{source} classification receipt optional-empty counts "
            "are contradictory"
        )
    return receipt


def _classification_errors(config) -> list[str]:
    errors = config.stash.get(
        _XDIST_CLASSIFICATION_ERRORS_STATE_KEY,
        None,
    )
    if errors is None:
        errors = []
        config.stash[_XDIST_CLASSIFICATION_ERRORS_STATE_KEY] = errors
    return errors


def _accept_xdist_classification_report(
    config,
    *,
    worker_id: str,
    payload: object,
    violations_payload: object,
    worker_error: object,
) -> None:
    reported = config.stash.get(
        _XDIST_CLASSIFICATION_REPORTED_STATE_KEY,
        None,
    )
    if reported is None:
        reported = set()
        config.stash[_XDIST_CLASSIFICATION_REPORTED_STATE_KEY] = reported
    reported.add(worker_id)

    errors = _classification_errors(config)
    if worker_error is not None:
        errors.append(
            f"xdist worker {worker_id} terminated with {worker_error!r}"
        )
    if violations_payload is not None:
        if not isinstance(violations_payload, list) or any(
            not isinstance(violation, str) or not violation
            for violation in violations_payload
        ):
            errors.append(
                f"xdist worker {worker_id} emitted malformed execution "
                "classification violations"
            )
        else:
            errors.extend(
                f"xdist worker {worker_id}: {violation}"
                for violation in violations_payload
            )
    if payload is None:
        errors.append(
            f"xdist worker {worker_id} emitted no execution "
            "classification receipt"
        )
        return
    try:
        receipt = _deserialize_classification_receipt(
            payload,
            source=f"xdist worker {worker_id}",
        )
    except ValueError as exc:
        errors.append(str(exc))
        return

    concurrency = dict(receipt.concurrency_selected)
    if (
        concurrency["local_only"] != 0
        or concurrency["serial"] != 0
        or concurrency["parallel"] != receipt.selected
    ):
        errors.append(
            f"xdist worker {worker_id} receipt is not parallel-only: "
            f"selected={receipt.selected}, "
            f"local_only={concurrency['local_only']}, "
            f"parallel={concurrency['parallel']}, "
            f"serial={concurrency['serial']}"
        )

    canonical = config.stash.get(
        _XDIST_CLASSIFICATION_REPORT_STATE_KEY,
        None,
    )
    if canonical is None:
        config.stash[_XDIST_CLASSIFICATION_REPORT_STATE_KEY] = receipt
    elif canonical != receipt:
        errors.append(
            f"xdist worker {worker_id} classification receipt contradicts "
            "the canonical worker manifest"
        )


def _finalize_xdist_classification(session) -> None:
    config = session.config
    if _is_xdist_worker(config):
        return
    if _xdist_mode(config) == "no":
        return

    expected = set(
        config.stash.get(_XDIST_CLASSIFICATION_EXPECTED_STATE_KEY, set())
    )
    reported = set(
        config.stash.get(_XDIST_CLASSIFICATION_REPORTED_STATE_KEY, set())
    )
    missing = sorted(expected - reported)
    errors = _classification_errors(config)
    for worker_id in missing:
        errors.append(
            f"xdist worker {worker_id} never reached receipt finalization"
        )
    if (
        config.stash.get(_XDIST_CLASSIFICATION_REPORT_STATE_KEY, None)
        is None
    ):
        errors.append("xdist produced no canonical execution classification receipt")
    if errors and session.exitstatus in {
        pytest.ExitCode.OK,
        pytest.ExitCode.NO_TESTS_COLLECTED,
    }:
        session.exitstatus = pytest.ExitCode.TESTS_FAILED


def _classification_receipt_for_summary(
    config,
) -> _ExecutionClassificationReceipt | None:
    local = config.stash.get(_CLASSIFICATION_RECEIPT_KEY, None)
    if local is not None:
        return local
    return config.stash.get(_XDIST_CLASSIFICATION_REPORT_STATE_KEY, None)
