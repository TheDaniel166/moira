"""Canonical typed state shared by Moira pytest plugins."""

from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
from datetime import date
from pathlib import Path
import re

import pytest


ROOT_DIR = Path(__file__).resolve().parents[2]


TEST_DIR  = ROOT_DIR / "tests"


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
    artifacts_enabled: bool
    run_id: str
    hypothesis: _HypothesisPolicy


@dataclass(frozen=True, slots=True)
class _KnownIssue:
    id: str
    relative_path: str
    resolved_path: Path
    reason: str
    owner: str
    expires: date


@dataclass(frozen=True, slots=True)
class _ExecutionClassificationReceipt:
    schema_version: int
    collected: int
    selected: int
    deselected: int
    primary_collected: tuple[tuple[str, int], ...]
    primary_selected: tuple[tuple[str, int], ...]
    concurrency_selected: tuple[tuple[str, int], ...]
    optional_empty_collected: int
    optional_empty_selected: int
    collected_digest: str
    selected_digest: str


@dataclass(slots=True)
class _CaseLifecycleState:
    reports: dict[str, object] = dataclass_field(default_factory=dict)


_HARNESS_CONFIG_KEY: pytest.StashKey[_HarnessConfig] = pytest.StashKey()


_KNOWN_ISSUES_KEY: pytest.StashKey[tuple[_KnownIssue, ...]] = pytest.StashKey()
_EXTERNAL_NETWORK_SELECTED_KEY: pytest.StashKey[int] = pytest.StashKey()
_RESOURCE_RESOLVER_KEY: pytest.StashKey[object] = pytest.StashKey()
_RESOURCE_RECEIPTS_KEY: pytest.StashKey[dict[str, object]] = pytest.StashKey()
_RESOURCE_ITEM_REQUIREMENT_KEY: pytest.StashKey[object] = pytest.StashKey()
_RESOURCE_ITEM_RECEIPT_KEY: pytest.StashKey[object] = pytest.StashKey()
_SMALL_BODY_RESOURCE_RECEIPTS_KEY: pytest.StashKey[
    dict[str, object]
] = pytest.StashKey()
_PRIMARY_CLASS_ITEM_KEY: pytest.StashKey[str] = pytest.StashKey()
_EXECUTION_CLASSIFICATION_IDENTITY_ITEM_KEY: pytest.StashKey[
    tuple[object, ...]
] = pytest.StashKey()
_COLLECTED_EXECUTION_ITEMS_KEY: pytest.StashKey[
    tuple[object, ...]
] = pytest.StashKey()
_EXECUTION_CLASSIFICATION_FROZEN_KEY: pytest.StashKey[bool] = (
    pytest.StashKey()
)
_XDIST_WORKER_ACTIVE_KEY: pytest.StashKey[bool] = pytest.StashKey()
_XDIST_MODE_KEY: pytest.StashKey[str] = pytest.StashKey()
_CLASSIFICATION_RECEIPT_KEY: pytest.StashKey[
    _ExecutionClassificationReceipt
] = pytest.StashKey()
_CASE_LIFECYCLE_KEY: pytest.StashKey[_CaseLifecycleState] = pytest.StashKey()
_LIFECYCLE_PAYLOAD_KEY: pytest.StashKey[dict[str, object]] = (
    pytest.StashKey()
)
_CONTROLLER_EVIDENCE_ERRORS_KEY: pytest.StashKey[tuple[str, ...]] = (
    pytest.StashKey()
)
_EVIDENCE_ITEM_BINDING_KEY: pytest.StashKey[tuple[str, str]] = (
    pytest.StashKey()
)
_EVIDENCE_ITEM_VIOLATION_KEY: pytest.StashKey[bool] = pytest.StashKey()
_EVIDENCE_SELECTED_RECEIPT_KEY: pytest.StashKey[dict[str, object]] = (
    pytest.StashKey()
)
_EVIDENCE_PAYLOAD_KEY: pytest.StashKey[dict[str, object]] = (
    pytest.StashKey()
)
_SESSION_PERF_START_KEY: pytest.StashKey[float] = pytest.StashKey()
_SESSION_UTC_START_KEY: pytest.StashKey[str] = pytest.StashKey()
_SESSION_TOTAL_BUDGET_KEY: pytest.StashKey[dict[str, object]] = (
    pytest.StashKey()
)
_ARTIFACT_ITEM_SECRET_VALUES_KEY: pytest.StashKey[tuple[str, ...]] = (
    pytest.StashKey()
)
_RECEIPT_COLLECTOR_KEY: pytest.StashKey[object] = pytest.StashKey()
_ARTIFACT_DIR_KEY: pytest.StashKey[Path] = pytest.StashKey()
_ARTIFACT_START_CONTEXT_KEY: pytest.StashKey[dict[str, object]] = (
    pytest.StashKey()
)
_COVERAGE_RUNTIME_IDENTITY_KEY: pytest.StashKey[dict[str, object]] = (
    pytest.StashKey()
)
_ARTIFACT_FINALIZATION_ERRORS_KEY: pytest.StashKey[list[str]] = (
    pytest.StashKey()
)
_XDIST_CLASSIFICATION_REPORT_STATE_KEY: pytest.StashKey[
    _ExecutionClassificationReceipt
] = pytest.StashKey()
_XDIST_CLASSIFICATION_ERRORS_STATE_KEY: pytest.StashKey[list[str]] = (
    pytest.StashKey()
)
_XDIST_CLASSIFICATION_EXPECTED_STATE_KEY: pytest.StashKey[set[str]] = (
    pytest.StashKey()
)
_XDIST_CLASSIFICATION_REPORTED_STATE_KEY: pytest.StashKey[set[str]] = (
    pytest.StashKey()
)
_XDIST_WORKER_CLASSIFICATION_VIOLATIONS_STATE_KEY: pytest.StashKey[
    list[str]
] = pytest.StashKey()
_XDIST_WORKER_CLASSIFICATION_VIOLATION_COUNT_STATE_KEY: pytest.StashKey[
    int
] = pytest.StashKey()
_XDIST_PLANETARY_RESOURCE_REPORT_STATE_KEY: pytest.StashKey[
    dict[str, object]
] = pytest.StashKey()
_XDIST_SMALL_BODY_RESOURCE_REPORT_STATE_KEY: pytest.StashKey[
    dict[str, object]
] = pytest.StashKey()
_XDIST_EVIDENCE_REPORT_STATE_KEY: pytest.StashKey[dict[str, object]] = (
    pytest.StashKey()
)
_XDIST_EVIDENCE_ERRORS_STATE_KEY: pytest.StashKey[list[str]] = (
    pytest.StashKey()
)
_XDIST_EVIDENCE_EXPECTED_STATE_KEY: pytest.StashKey[set[str]] = (
    pytest.StashKey()
)
_XDIST_EVIDENCE_REPORTED_STATE_KEY: pytest.StashKey[set[str]] = (
    pytest.StashKey()
)
_XDIST_COVERAGE_RUNTIME_REPORT_STATE_KEY: pytest.StashKey[
    dict[str, dict[str, object]]
] = pytest.StashKey()
_XDIST_COVERAGE_RUNTIME_ERRORS_STATE_KEY: pytest.StashKey[list[str]] = (
    pytest.StashKey()
)


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


_ARTIFACT_RUN_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")


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
