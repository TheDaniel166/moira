"""Evidence terminal presentation policy."""

from __future__ import annotations

import json
import hashlib
import importlib
import os
from pathlib import Path

import pytest

from _pytest_plugins._state import (
    ROOT_DIR,
    TEST_DIR,
    _EVIDENCE_ITEM_BINDING_KEY,
    _EVIDENCE_ITEM_VIOLATION_KEY,
    _EVIDENCE_PAYLOAD_KEY,
    _EVIDENCE_SELECTED_RECEIPT_KEY,
    _HARNESS_CONFIG_KEY,
    _XDIST_EVIDENCE_ERRORS_STATE_KEY,
    _XDIST_EVIDENCE_EXPECTED_STATE_KEY,
    _XDIST_EVIDENCE_REPORTED_STATE_KEY,
    _XDIST_EVIDENCE_REPORT_STATE_KEY,
)
from _pytest_plugins.artifacts import (
    _controller_collector,
    _seal_lifecycle_evidence,
)
from _pytest_plugins.classification import (
    _classification_errors,
    _classification_receipt_for_summary,
    _is_xdist_worker,
)
from _pytest_plugins.evidence_schema import (
    EVIDENCE_SCHEMA_VERSION,
    canonical_json_bytes,
    contract_payload,
    contract_sha256,
    validate_registry,
)
from _pytest_plugins.network_policy import (
    write_terminal_summary as _write_network_terminal_summary,
)
from _pytest_plugins.resources import (
    write_terminal_summary as _write_resource_terminal_summary,
)


_VALIDATION_MARKER = "validation_contract"
_XDIST_EVIDENCE_REPORT_KEY = "moira_validation_evidence_v1"
_MAX_EVIDENCE_RECEIPT_BYTES = 4 * 1024 * 1024
_MAX_EVIDENCE_BINDINGS = 100_000
_CLAIM_PROPERTY = "moira_validation_claim_id"
_DIGEST_PROPERTY = "moira_validation_contract_sha256"


def _registry_path() -> Path:
    return TEST_DIR / "evidence" / "contracts.py"


def _load_contract_registry():
    path = _registry_path()
    if not path.is_file():
        return None
    module = importlib.import_module("evidence.contracts")
    module_path = Path(getattr(module, "__file__", "")).resolve()
    if module_path != path.resolve():
        raise ValueError(
            "evidence.contracts resolved outside the active tests tree: "
            f"{module_path}"
        )
    registry = getattr(module, "CONTRACTS", None)
    validate_registry(registry, root=ROOT_DIR, verify_assets=True)
    return registry


def _base_nodeid_matches(nodeid: str, base_nodeid: str) -> bool:
    return nodeid == base_nodeid or nodeid.startswith(base_nodeid + "[")


def _marker_claim_id(item) -> tuple[str | None, list[str]]:
    markers = tuple(item.iter_markers(name=_VALIDATION_MARKER))
    if not markers:
        return None, []
    if len(markers) != 1:
        return None, [
            f"{item.nodeid}: validation_contract requires exactly one "
            "effective marker"
        ]
    marker = markers[0]
    if len(marker.args) != 1 or marker.kwargs:
        return None, [
            f"{item.nodeid}: validation_contract requires exactly one "
            "positional claim ID and no keyword arguments"
        ]
    claim_id = marker.args[0]
    if not isinstance(claim_id, str) or not claim_id:
        return None, [
            f"{item.nodeid}: validation_contract requires exactly one "
            "non-empty text claim ID"
        ]
    return claim_id, []


def _has_explicit_hypothesis_settings(item) -> bool:
    """Return whether a Hypothesis test weakens the receipted profile locally."""

    function = getattr(item, "function", None)
    return bool(
        function is not None
        and getattr(
            function,
            "_hypothesis_internal_settings_applied",
            False,
        )
    )


def _raise_evidence_collection_errors(errors: list[str]) -> None:
    if not errors:
        return
    displayed = errors[:20]
    omitted = len(errors) - len(displayed)
    detail = "\n- ".join(displayed)
    if omitted:
        detail += f"\n- ... and {omitted} additional violation(s)"
    raise pytest.UsageError(
        "Validation evidence contract violations:\n- " + detail
    )


def _bind_collected_items(items) -> None:
    errors: list[str] = []
    classified: list[tuple[object, str | None]] = []
    for item in items:
        claim_id, marker_errors = _marker_claim_id(item)
        errors.extend(marker_errors)
        classified.append((item, claim_id))
    try:
        registry = _load_contract_registry()
    except Exception as exc:
        errors.append(
            "validation contract registry is invalid: "
            f"{type(exc).__name__}: {exc}"
        )
        registry = None
    if registry is None:
        if any(claim_id is not None for _item, claim_id in classified):
            errors.append(
                "validation contract registry is unavailable at "
                f"{_registry_path()}"
            )
        _raise_evidence_collection_errors(errors)
        return

    for item, claim_id in classified:
        admitted_claims = [
            admitted_claim_id
            for admitted_claim_id, admitted_contract in registry.items()
            if any(
                _base_nodeid_matches(item.nodeid, base_nodeid)
                for base_nodeid in admitted_contract.nodeids
            )
        ]
        if claim_id is None:
            if admitted_claims:
                errors.append(
                    f"{item.nodeid}: reviewed validation surface requires "
                    f"validation_contract({admitted_claims[0]!r})"
                )
            continue
        contract = registry.get(claim_id)
        if contract is None:
            errors.append(
                f"{item.nodeid}: unknown validation contract {claim_id!r}"
            )
            continue
        if not any(
            _base_nodeid_matches(item.nodeid, base_nodeid)
            for base_nodeid in contract.nodeids
        ):
            errors.append(
                f"{item.nodeid}: validation contract {claim_id!r} does "
                "not admit this base nodeid"
            )
            continue
        if _has_explicit_hypothesis_settings(item):
            errors.append(
                f"{item.nodeid}: contract-bound Hypothesis tests must "
                "inherit the receipted harness profile; explicit "
                "@settings(...) is forbidden"
            )
            continue
        digest = contract_sha256(contract)
        item.stash[_EVIDENCE_ITEM_BINDING_KEY] = (claim_id, digest)
    _raise_evidence_collection_errors(errors)


def _build_selected_receipt(items) -> dict[str, object]:
    registry = None
    bindings: list[dict[str, str]] = []
    selected_claim_ids: set[str] = set()
    errors: list[str] = []
    for item in items:
        claim_id, marker_errors = _marker_claim_id(item)
        errors.extend(marker_errors)
        frozen = item.stash.get(_EVIDENCE_ITEM_BINDING_KEY, None)
        if claim_id is None:
            if frozen is not None:
                errors.append(
                    f"{item.nodeid}: validation_contract was removed after "
                    "initial evidence classification"
                )
            continue
        if frozen is None:
            errors.append(
                f"{item.nodeid}: validation_contract was added or changed "
                "after initial evidence classification"
            )
            continue
        frozen_claim_id, digest = frozen
        if claim_id != frozen_claim_id:
            errors.append(
                f"{item.nodeid}: validation_contract changed after initial "
                "evidence classification"
            )
            continue
        selected_claim_ids.add(claim_id)
        bindings.append(
            {
                "nodeid": item.nodeid,
                "claim_id": claim_id,
                "contract_sha256": digest,
            }
        )
        existing_pairs = [
            (str(name), value)
            for name, value in item.user_properties
            if name in {_CLAIM_PROPERTY, _DIGEST_PROPERTY}
        ]
        expected_properties = {
            _CLAIM_PROPERTY: claim_id,
            _DIGEST_PROPERTY: digest,
        }
        if existing_pairs and (
            len(existing_pairs) != 2
            or dict(existing_pairs) != expected_properties
        ):
            errors.append(
                f"{item.nodeid}: conflicting validation evidence user properties"
            )
            continue
        if not existing_pairs:
            item.user_properties.extend(expected_properties.items())
    if selected_claim_ids:
        try:
            registry = _load_contract_registry()
        except Exception as exc:
            errors.append(
                "validation contract registry changed during collection: "
                f"{type(exc).__name__}: {exc}"
            )
    contracts: list[dict[str, object]] = []
    class_counts: dict[str, int] = {}
    if registry is not None:
        for claim_id in sorted(selected_claim_ids):
            contract = registry[claim_id]
            payload = contract_payload(contract)
            digest = contract_sha256(contract)
            contracts.append(
                {
                    "claim_id": claim_id,
                    "contract_sha256": digest,
                    "contract": payload,
                }
            )
            evidence_class = contract.evidence_class.value
            class_counts[evidence_class] = class_counts.get(evidence_class, 0) + 1
    _raise_evidence_collection_errors(errors)
    body: dict[str, object] = {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "contracts": contracts,
        "bindings": sorted(bindings, key=lambda value: value["nodeid"]),
        "class_counts": [
            [name, count]
            for name, count in sorted(class_counts.items())
        ],
        "selected_contracts": len(contracts),
        "selected_items": len(bindings),
    }
    body["manifest_sha256"] = hashlib.sha256(
        canonical_json_bytes(body)
    ).hexdigest()
    return body


def _empty_selected_receipt() -> dict[str, object]:
    return _build_selected_receipt(())


@pytest.hookimpl(wrapper=True, trylast=True)
def pytest_collection_modifyitems(config, items):
    """Bind contracts before selection and seal selected evidence afterward."""

    collected_items = tuple(items)
    _bind_collected_items(collected_items)
    yield
    receipt = _build_selected_receipt(tuple(items))
    config.stash[_EVIDENCE_SELECTED_RECEIPT_KEY] = receipt
    if not _is_xdist_worker(config):
        config.stash[_EVIDENCE_PAYLOAD_KEY] = receipt


def _assert_runtime_binding(item) -> None:
    """Reject evidence-marker or property mutation at every test phase."""

    if item.stash.get(_EVIDENCE_ITEM_VIOLATION_KEY, False):
        return
    claim_id, errors = _marker_claim_id(item)
    frozen = item.stash.get(_EVIDENCE_ITEM_BINDING_KEY, None)
    if claim_id is None and frozen is None and not errors:
        return
    if errors or frozen is None or claim_id != frozen[0]:
        item.stash[_EVIDENCE_ITEM_VIOLATION_KEY] = True
        pytest.fail(
            "validation evidence binding changed after collection",
            pytrace=False,
        )
    expected = {
        _CLAIM_PROPERTY: frozen[0],
        _DIGEST_PROPERTY: frozen[1],
    }
    actual_pairs = [
        (str(name), value)
        for name, value in item.user_properties
        if name in expected
    ]
    if len(actual_pairs) != 2 or dict(actual_pairs) != expected:
        item.stash[_EVIDENCE_ITEM_VIOLATION_KEY] = True
        pytest.fail(
            "validation evidence user properties changed after collection",
            pytrace=False,
        )


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_setup(item):
    """Seal evidence identity across fixture setup."""

    _assert_runtime_binding(item)
    try:
        result = yield
    finally:
        _assert_runtime_binding(item)
    return result


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_call(item):
    """Seal evidence identity across the test call."""

    _assert_runtime_binding(item)
    try:
        result = yield
    finally:
        _assert_runtime_binding(item)
    return result


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_teardown(item):
    """Seal evidence identity across fixture teardown."""

    _assert_runtime_binding(item)
    try:
        result = yield
    finally:
        _assert_runtime_binding(item)
    return result


def _validate_receipt_payload(payload: object) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise ValueError("evidence receipt must be an object")
    if len(canonical_json_bytes(payload)) > _MAX_EVIDENCE_RECEIPT_BYTES:
        raise ValueError("evidence receipt exceeds the size limit")
    required = {
        "schema_version",
        "contracts",
        "bindings",
        "class_counts",
        "selected_contracts",
        "selected_items",
        "manifest_sha256",
    }
    if set(payload) != required:
        raise ValueError("evidence receipt fields are not exact")
    if payload["schema_version"] != EVIDENCE_SCHEMA_VERSION:
        raise ValueError("evidence receipt schema is unsupported")
    contracts = payload["contracts"]
    bindings = payload["bindings"]
    class_counts = payload["class_counts"]
    if not isinstance(contracts, list) or not isinstance(bindings, list):
        raise ValueError("evidence contracts and bindings must be lists")
    if len(bindings) > _MAX_EVIDENCE_BINDINGS:
        raise ValueError("evidence receipt contains too many bindings")
    if payload["selected_contracts"] != len(contracts):
        raise ValueError("selected_contracts contradicts the contract list")
    if payload["selected_items"] != len(bindings):
        raise ValueError("selected_items contradicts the binding list")
    contract_digests: dict[str, str] = {}
    calculated_counts: dict[str, int] = {}
    previous_claim_id = ""
    for entry in contracts:
        if not isinstance(entry, dict) or set(entry) != {
            "claim_id",
            "contract_sha256",
            "contract",
        }:
            raise ValueError("evidence contract entry is malformed")
        claim_id = entry["claim_id"]
        digest = entry["contract_sha256"]
        contract = entry["contract"]
        if (
            not isinstance(claim_id, str)
            or claim_id <= previous_claim_id
            or not isinstance(digest, str)
            or not isinstance(contract, dict)
            or contract.get("claim_id") != claim_id
        ):
            raise ValueError("evidence contract identity or order is invalid")
        calculated = hashlib.sha256(canonical_json_bytes(contract)).hexdigest()
        if calculated != digest:
            raise ValueError("evidence contract digest is invalid")
        evidence_class = contract.get("evidence_class")
        if not isinstance(evidence_class, str):
            raise ValueError("evidence class is invalid")
        calculated_counts[evidence_class] = (
            calculated_counts.get(evidence_class, 0) + 1
        )
        contract_digests[claim_id] = digest
        previous_claim_id = claim_id
    previous_nodeid = ""
    seen_nodeids: set[str] = set()
    for binding in bindings:
        if not isinstance(binding, dict) or set(binding) != {
            "nodeid",
            "claim_id",
            "contract_sha256",
        }:
            raise ValueError("evidence binding entry is malformed")
        nodeid = binding["nodeid"]
        claim_id = binding["claim_id"]
        digest = binding["contract_sha256"]
        if (
            not isinstance(nodeid, str)
            or nodeid <= previous_nodeid
            or nodeid in seen_nodeids
            or contract_digests.get(claim_id) != digest
        ):
            raise ValueError("evidence binding identity or order is invalid")
        previous_nodeid = nodeid
        seen_nodeids.add(nodeid)
    expected_counts = [
        [name, count] for name, count in sorted(calculated_counts.items())
    ]
    if class_counts != expected_counts:
        raise ValueError("evidence class counts are inconsistent")
    unsigned = dict(payload)
    manifest_sha256 = unsigned.pop("manifest_sha256")
    calculated_manifest = hashlib.sha256(
        canonical_json_bytes(unsigned)
    ).hexdigest()
    if manifest_sha256 != calculated_manifest:
        raise ValueError("evidence manifest digest is invalid")
    return payload


def _validate_receipt_against_registry(
    payload: dict[str, object],
) -> None:
    """Re-derive every worker claim and binding from controller truth."""

    registry = _load_contract_registry()
    contracts = payload["contracts"]
    bindings = payload["bindings"]
    assert isinstance(contracts, list)
    assert isinstance(bindings, list)
    if registry is None:
        if contracts or bindings:
            raise ValueError(
                "worker supplied validation evidence without a controller registry"
            )
        return

    received_claims: set[str] = set()
    for entry in contracts:
        assert isinstance(entry, dict)
        claim_id = str(entry["claim_id"])
        contract = registry.get(claim_id)
        if contract is None:
            raise ValueError(f"worker supplied unknown claim {claim_id!r}")
        if entry["contract"] != contract_payload(contract):
            raise ValueError(f"worker contract contradicts registry: {claim_id}")
        if entry["contract_sha256"] != contract_sha256(contract):
            raise ValueError(f"worker contract digest contradicts registry: {claim_id}")
        received_claims.add(claim_id)

    bound_claims: set[str] = set()
    for binding in bindings:
        assert isinstance(binding, dict)
        claim_id = str(binding["claim_id"])
        contract = registry.get(claim_id)
        if contract is None or claim_id not in received_claims:
            raise ValueError("worker binding references an unsealed claim")
        if binding["contract_sha256"] != contract_sha256(contract):
            raise ValueError("worker binding digest contradicts controller truth")
        nodeid = str(binding["nodeid"])
        if not any(
            _base_nodeid_matches(nodeid, base_nodeid)
            for base_nodeid in contract.nodeids
        ):
            raise ValueError(
                f"worker binding is not admitted by {claim_id}: {nodeid}"
            )
        bound_claims.add(claim_id)
    if bound_claims != received_claims:
        raise ValueError("worker receipt contains an unbound contract")


def _accept_xdist_evidence_report(
    config,
    *,
    worker_id: str,
    payload: object,
    worker_error: object,
) -> None:
    reported = config.stash.get(_XDIST_EVIDENCE_REPORTED_STATE_KEY, None)
    if reported is None:
        reported = set()
        config.stash[_XDIST_EVIDENCE_REPORTED_STATE_KEY] = reported
    errors = config.stash.get(_XDIST_EVIDENCE_ERRORS_STATE_KEY, None)
    if errors is None:
        errors = []
        config.stash[_XDIST_EVIDENCE_ERRORS_STATE_KEY] = errors
    if worker_id in reported:
        errors.append(f"xdist worker {worker_id} reported evidence twice")
        return
    reported.add(worker_id)
    if worker_error is not None:
        errors.append(
            f"xdist worker {worker_id} terminated before evidence reconciliation"
        )
    try:
        validated = _validate_receipt_payload(payload)
        _validate_receipt_against_registry(validated)
    except Exception as exc:
        errors.append(
            f"xdist worker {worker_id} evidence receipt is invalid: "
            f"{type(exc).__name__}: {exc}"
        )
        return
    canonical = config.stash.get(_XDIST_EVIDENCE_REPORT_STATE_KEY, None)
    if canonical is None:
        config.stash[_XDIST_EVIDENCE_REPORT_STATE_KEY] = validated
    elif canonical != validated:
        errors.append(
            f"xdist worker {worker_id} evidence manifest contradicts its peers"
        )


def _finalize_xdist_evidence(session) -> tuple[str, ...]:
    config = session.config
    expected = config.stash.get(_XDIST_EVIDENCE_EXPECTED_STATE_KEY, set())
    reported = config.stash.get(_XDIST_EVIDENCE_REPORTED_STATE_KEY, set())
    errors = config.stash.get(_XDIST_EVIDENCE_ERRORS_STATE_KEY, None)
    if errors is None:
        errors = []
        config.stash[_XDIST_EVIDENCE_ERRORS_STATE_KEY] = errors
    for worker_id in sorted(expected - reported):
        errors.append(f"xdist worker {worker_id} supplied no evidence receipt")
    payload = config.stash.get(_XDIST_EVIDENCE_REPORT_STATE_KEY, None)
    if expected and payload is None:
        errors.append("no canonical xdist evidence manifest was available")
    if payload is not None:
        config.stash[_EVIDENCE_PAYLOAD_KEY] = payload
    elif not expected:
        config.stash[_EVIDENCE_PAYLOAD_KEY] = config.stash.get(
            _EVIDENCE_SELECTED_RECEIPT_KEY,
            _empty_selected_receipt(),
        )
    return tuple(errors)


def _seal_evidence_report_bindings(config, collector) -> tuple[str, ...]:
    payload = config.stash.get(_EVIDENCE_PAYLOAD_KEY, None)
    if payload is None or collector is None:
        return ()
    bindings = {
        binding["nodeid"]: (
            binding["claim_id"],
            binding["contract_sha256"],
        )
        for binding in payload["bindings"]
    }
    errors: list[str] = []
    reported_bound_nodeids: set[str] = set()
    for record in collector.records:
        if record.get("kind") != "test":
            continue
        nodeid = str(record.get("nodeid"))
        properties = record.get("user_properties", {})
        if not isinstance(properties, dict):
            errors.append(f"{nodeid}: evidence user properties are malformed")
            continue
        expected = bindings.get(nodeid)
        actual_claim = properties.get(_CLAIM_PROPERTY)
        actual_digest = properties.get(_DIGEST_PROPERTY)
        if expected is None:
            if actual_claim is not None or actual_digest is not None:
                errors.append(
                    f"{nodeid}: unbound test emitted validation evidence identity"
                )
            continue
        reported_bound_nodeids.add(nodeid)
        if (actual_claim, actual_digest) != expected:
            errors.append(
                f"{nodeid}: report evidence identity contradicts the selected manifest"
            )
    if not config.option.collectonly:
        for nodeid in sorted(set(bindings) - reported_bound_nodeids):
            errors.append(
                f"{nodeid}: selected validation binding produced no test report"
            )
    if errors:
        policy_errors = config.stash.get(
            _XDIST_EVIDENCE_ERRORS_STATE_KEY,
            None,
        )
        if policy_errors is None:
            policy_errors = []
            config.stash[_XDIST_EVIDENCE_ERRORS_STATE_KEY] = policy_errors
        policy_errors.extend(errors)
    return tuple(errors)


def _evidence_payload(config) -> dict[str, object]:
    payload = config.stash.get(_EVIDENCE_PAYLOAD_KEY, None)
    if payload is None:
        payload = config.stash.get(_XDIST_EVIDENCE_REPORT_STATE_KEY, None)
    return payload if payload is not None else _empty_selected_receipt()


@pytest.hookimpl
def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Present immutable harness, lifecycle, and duration evidence."""

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
        _write_network_terminal_summary(terminalreporter, config, policy)

        classification_receipt = _classification_receipt_for_summary(config)
        if classification_receipt is not None:
            semantic_skipped = {
                report.nodeid
                for report in terminalreporter.stats.get("skipped", ())
                if (
                    getattr(report, "when", None)
                    in {"collect", "setup", "call", "teardown"}
                    and isinstance(getattr(report, "nodeid", None), str)
                )
            }
            terminalreporter.write_line(
                "  Execution classification: "
                f"collected={classification_receipt.collected}, "
                f"selected={classification_receipt.selected}, "
                f"deselected={classification_receipt.deselected}, "
                f"skipped={len(semantic_skipped)}"
            )
            terminalreporter.write_line(
                "  Primary collected: "
                + ", ".join(
                    f"{name}={count}"
                    for name, count
                    in classification_receipt.primary_collected
                )
            )
            terminalreporter.write_line(
                "  Primary selected: "
                + ", ".join(
                    f"{name}={count}"
                    for name, count
                    in classification_receipt.primary_selected
                )
            )
            terminalreporter.write_line(
                "  Concurrency selected: "
                + ", ".join(
                    f"{name}={count}"
                    for name, count
                    in classification_receipt.concurrency_selected
                )
            )
            terminalreporter.write_line(
                "  Classification manifest: "
                f"schema={classification_receipt.schema_version}, "
                "collected_sha256="
                f"{classification_receipt.collected_digest}, "
                "selected_sha256="
                f"{classification_receipt.selected_digest}"
            )
            if classification_receipt.optional_empty_collected:
                terminalreporter.write_line(
                    "  Optional empty enumerations: "
                    f"collected={classification_receipt.optional_empty_collected}, "
                    f"selected={classification_receipt.optional_empty_selected}"
                )

        classification_errors = _classification_errors(config)
        if classification_errors:
            terminalreporter.write_line(
                "  Xdist classification finalization: FAILED"
            )
            for error in classification_errors[:10]:
                terminalreporter.write_line(f"    {error}")

        _write_resource_terminal_summary(terminalreporter, config)

        evidence_payload = _evidence_payload(config)
        if evidence_payload["selected_contracts"]:
            terminalreporter.write_line(
                "  Validation evidence: "
                f"contracts={evidence_payload['selected_contracts']}, "
                f"items={evidence_payload['selected_items']}, "
                f"manifest_sha256={evidence_payload['manifest_sha256']}"
            )
            terminalreporter.write_line(
                "  Evidence classes: "
                + ", ".join(
                    f"{name}={count}"
                    for name, count in evidence_payload["class_counts"]
                )
            )
        evidence_errors = config.stash.get(
            _XDIST_EVIDENCE_ERRORS_STATE_KEY,
            (),
        )
        if evidence_errors:
            terminalreporter.write_line(
                "  Xdist evidence finalization: FAILED"
            )
            for error in evidence_errors[:10]:
                terminalreporter.write_line(f"    {error}")

    collector = _controller_collector(config)
    lifecycle, _evidence_errors = _seal_lifecycle_evidence(
        config,
        collector,
    )
    budget_violations = [
        case
        for case in lifecycle["cases"]
        if case["case_budget_exceeded"]
    ]
    if budget_violations:
        terminalreporter.section("Moira: case budget violations")
        for case in budget_violations[:10]:
            terminalreporter.write_line(
                f"  {case['nodeid']} [attempt {case['attempt']}]: "
                f"{float(case['total_duration_s']):.3f}s > "
                f"{float(case['case_budget_s']):.3f}s"
            )
    incomplete_cases = [
        case
        for case in lifecycle["cases"]
        if not case["complete"]
    ]
    if incomplete_cases:
        terminalreporter.section("Moira: incomplete test lifecycles")
        for case in incomplete_cases[:10]:
            terminalreporter.write_line(
                f"  {case['nodeid']} [attempt {case['attempt']}]"
            )
    durations = {
        f"{case['nodeid']} [attempt {case['attempt']}]": float(
            case["total_duration_s"]
        )
        for case in lifecycle["cases"]
    }
    if durations:
        n_slow = 5
        sorted_durations = sorted(
            durations.items(),
            key=lambda item: item[1],
            reverse=True,
        )
        if sorted_durations:
            terminalreporter.section("Moira: slowest tests")
            for nodeid, duration in sorted_durations[:n_slow]:
                terminalreporter.write_line(
                    f"  {duration:7.3f}s  {nodeid}"
                )

        baseline_path = TEST_DIR / "artifacts" / "durations_baseline.json"
        if baseline_path.exists():
            try:
                baseline = json.loads(
                    baseline_path.read_text(encoding="utf-8")
                )
            except Exception:
                baseline = None
            if baseline:
                threshold = (
                    float(os.getenv("MOIRA_REGRESSION_PCT", "50"))
                    / 100.0
                )
                regressions = [
                    (nodeid, base, current)
                    for nodeid, current in durations.items()
                    if (
                        (base := baseline.get(nodeid))
                        and base > 0
                        and (current - base) / base >= threshold
                    )
                ]
                if regressions:
                    terminalreporter.section(
                        "Moira: performance regressions"
                    )
                    for nodeid, base, current in sorted(
                        regressions,
                        key=lambda row: row[2] - row[1],
                        reverse=True,
                    ):
                        percent = (current - base) / base * 100
                        terminalreporter.write_line(
                            f"  {nodeid}:  {base:.3f}s -> "
                            f"{current:.3f}s  (+{percent:.0f}%)"
                        )
