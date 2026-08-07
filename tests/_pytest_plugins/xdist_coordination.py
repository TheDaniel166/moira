"""Controller-owned pytest-xdist scheduling and receipt coordination."""

from __future__ import annotations

import os

import pytest

from ._state import (
    ROOT_DIR,
    _ARTIFACT_FINALIZATION_ERRORS_KEY,
    _CLASSIFICATION_RECEIPT_KEY,
    _COVERAGE_RUNTIME_IDENTITY_KEY,
    _EVIDENCE_SELECTED_RECEIPT_KEY,
    _HARNESS_CONFIG_KEY,
    _XDIST_CLASSIFICATION_EXPECTED_STATE_KEY,
    _XDIST_COVERAGE_RUNTIME_ERRORS_STATE_KEY,
    _XDIST_COVERAGE_RUNTIME_REPORT_STATE_KEY,
    _XDIST_EVIDENCE_EXPECTED_STATE_KEY,
    _XDIST_PLANETARY_RESOURCE_REPORT_STATE_KEY,
    _XDIST_SMALL_BODY_RESOURCE_REPORT_STATE_KEY,
    _XDIST_WORKER_CLASSIFICATION_VIOLATION_COUNT_STATE_KEY,
    _XDIST_WORKER_CLASSIFICATION_VIOLATIONS_STATE_KEY,
)
from .artifacts import (
    _XDIST_COVERAGE_RUNTIME_REPORT_KEY,
    _controller_collector,
    _emit_post_session_diagnostics,
    _finalize_artifact_receipt,
    _run_context,
    _seal_lifecycle_evidence,
)
from .classification import (
    _XDIST_CLASSIFICATION_REPORT_KEY,
    _XDIST_CLASSIFICATION_VIOLATIONS_KEY,
    _accept_xdist_classification_report,
    _assert_live_xdist_scheduler_mode,
    _finalize_xdist_classification,
    _serialize_classification_receipt,
    _xdist_mode,
)
from .lifecycle import _total_budget_observation
from .evidence import (
    _XDIST_EVIDENCE_REPORT_KEY,
    _accept_xdist_evidence_report,
    _finalize_xdist_evidence,
    _seal_evidence_report_bindings,
)
from .network_policy import reset_session_network_mode
from .resources import (
    _XDIST_PLANETARY_RESOURCE_REPORT_KEY,
    _XDIST_SMALL_BODY_RESOURCE_REPORT_KEY,
    _empty_planetary_resource_report,
    _empty_small_body_resource_report,
    _merge_planetary_resource_report,
    _merge_small_body_resource_report,
    _serialize_planetary_resource_report,
    _serialize_small_body_resource_report,
)


@pytest.hookimpl(trylast=True)
def pytest_configure(config) -> None:
    # xdist worker identity comes from the active plugin contract, never from
    # stale environment inherited by a nested local pytest subprocess.
    workerinput = getattr(config, "workerinput", None)
    worker_id = (
        str(workerinput.get("workerid", "gw0"))
        if isinstance(workerinput, dict)
        else ""
    )
    if worker_id:
        os.environ["MOIRA_WORKER_ID"] = worker_id
    else:
        for name in (
            "PYTEST_XDIST_WORKER",
            "PYTEST_XDIST_WORKER_COUNT",
            "MOIRA_WORKER_ID",
        ):
            os.environ.pop(name, None)


def _seal_xdist_worker_receipts(session) -> bool:
    workeroutput = getattr(session.config, "workeroutput", None)
    if not isinstance(workeroutput, dict):
        return False

    classification_violations = session.config.stash.get(
        _XDIST_WORKER_CLASSIFICATION_VIOLATIONS_STATE_KEY,
        (),
    )
    if classification_violations:
        violation_payload = list(classification_violations)
        violation_count = session.config.stash.get(
            _XDIST_WORKER_CLASSIFICATION_VIOLATION_COUNT_STATE_KEY,
            len(violation_payload),
        )
        omitted = violation_count - len(violation_payload)
        if omitted > 0:
            violation_payload.append(
                f"... and {omitted} additional violation(s) omitted"
            )
        workeroutput[_XDIST_CLASSIFICATION_VIOLATIONS_KEY] = (
            violation_payload
        )
    else:
        workeroutput.pop(_XDIST_CLASSIFICATION_VIOLATIONS_KEY, None)

    classification_receipt = session.config.stash.get(
        _CLASSIFICATION_RECEIPT_KEY,
        None,
    )
    if classification_receipt is None:
        workeroutput.pop(_XDIST_CLASSIFICATION_REPORT_KEY, None)
    else:
        workeroutput[_XDIST_CLASSIFICATION_REPORT_KEY] = (
            _serialize_classification_receipt(classification_receipt)
        )
    workeroutput[_XDIST_PLANETARY_RESOURCE_REPORT_KEY] = (
        _serialize_planetary_resource_report(session.config)
    )
    workeroutput[_XDIST_SMALL_BODY_RESOURCE_REPORT_KEY] = (
        _serialize_small_body_resource_report(session.config)
    )
    workeroutput[_XDIST_EVIDENCE_REPORT_KEY] = session.config.stash.get(
        _EVIDENCE_SELECTED_RECEIPT_KEY,
        None,
    )
    coverage_identity = session.config.stash.get(
        _COVERAGE_RUNTIME_IDENTITY_KEY,
        None,
    )
    if isinstance(coverage_identity, dict):
        coverage_identity = dict(coverage_identity)
        coverage_identity["final_run_context"] = _run_context(ROOT_DIR)
    workeroutput[_XDIST_COVERAGE_RUNTIME_REPORT_KEY] = coverage_identity
    return True


@pytest.hookimpl(
    wrapper=True,
    trylast=True,
    specname="pytest_sessionfinish",
)
def pytest_sessionfinish_worker_receipt_seal(session, exitstatus):
    """Reseal worker evidence after inner plugins and before xdist sends it."""
    result = yield
    _seal_xdist_worker_receipts(session)
    return result


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_sessionfinish(session, exitstatus):
    reset_session_network_mode()
    if _seal_xdist_worker_receipts(session):
        result = yield
        return result

    result = yield
    _finalize_xdist_classification(session)
    reconciliation_errors = _finalize_xdist_evidence(session)
    report_binding_errors = _seal_evidence_report_bindings(
        session.config,
        _controller_collector(session.config),
    )
    evidence_policy_errors = (
        *reconciliation_errors,
        *report_binding_errors,
    )
    _lifecycle, evidence_errors = _seal_lifecycle_evidence(
        session.config
    )
    total_budget = _total_budget_observation(session)
    prospective_exitstatus = session.exitstatus
    if (
        total_budget["exceeded"]
        and prospective_exitstatus == pytest.ExitCode.OK
    ):
        prospective_exitstatus = pytest.ExitCode.TESTS_FAILED
    if (
        evidence_errors
        and prospective_exitstatus == pytest.ExitCode.OK
    ):
        prospective_exitstatus = pytest.ExitCode.TESTS_FAILED
    if (
        evidence_policy_errors
        and prospective_exitstatus == pytest.ExitCode.OK
    ):
        prospective_exitstatus = pytest.ExitCode.TESTS_FAILED

    artifact_errors = _finalize_artifact_receipt(
        session,
        total_budget=total_budget,
        prospective_exitstatus=prospective_exitstatus,
    )
    session.config.stash[_ARTIFACT_FINALIZATION_ERRORS_KEY] = artifact_errors
    diagnostic_evidence_errors = tuple(
        dict.fromkeys((*evidence_errors, *evidence_policy_errors))
    )
    _emit_post_session_diagnostics(
        session.config,
        total_budget=total_budget,
        evidence_errors=diagnostic_evidence_errors,
        artifact_errors=artifact_errors,
    )
    if (
        artifact_errors
        and prospective_exitstatus == pytest.ExitCode.OK
    ):
        prospective_exitstatus = pytest.ExitCode.TESTS_FAILED
    session.exitstatus = prospective_exitstatus
    return result


try:
    import xdist  # noqa: F401
    from xdist.dsession import DSession
    from xdist.scheduler import (
        EachScheduling,
        LoadFileScheduling,
        LoadGroupScheduling,
        LoadScheduling,
        LoadScopeScheduling,
        WorkStealingScheduling,
    )

    _XDIST_SCHEDULER_TYPES = {
        "each": EachScheduling,
        "load": LoadScheduling,
        "loadfile": LoadFileScheduling,
        "loadgroup": LoadGroupScheduling,
        "loadscope": LoadScopeScheduling,
        "worksteal": WorkStealingScheduling,
    }

    def _assert_xdist_scheduler_hook_chain(config) -> None:
        admitted_functions = {
            pytest_xdist_make_scheduler,
            DSession.pytest_xdist_make_scheduler,
        }
        unadmitted: list[str] = []
        for hookimpl in (
            config.pluginmanager.hook.pytest_xdist_make_scheduler.get_hookimpls()
        ):
            function = getattr(hookimpl.function, "__func__", hookimpl.function)
            if function in admitted_functions:
                continue
            unadmitted.append(
                f"{hookimpl.plugin_name}:"
                f"{function.__module__}.{function.__qualname__}"
            )
        if unadmitted:
            raise pytest.UsageError(
                "Unadmitted pytest_xdist_make_scheduler implementation(s): "
                + ", ".join(sorted(unadmitted))
            )

    def _assert_xdist_scheduler_contract(config, scheduler) -> None:
        admitted_mode = _xdist_mode(config)
        expected_type = _XDIST_SCHEDULER_TYPES.get(admitted_mode)
        if expected_type is None:
            raise pytest.UsageError(
                "pytest-xdist scheduler mode is not admitted by Moira: "
                f"{admitted_mode!r}"
            )
        if type(scheduler) is not expected_type:
            raise pytest.UsageError(
                "pytest-xdist scheduler contract mismatch: "
                f"mode={admitted_mode!r}, expected={expected_type.__name__}, "
                f"actual={type(scheduler).__name__}"
            )

    @pytest.hookimpl(optionalhook=True, wrapper=True, tryfirst=True)
    def pytest_xdist_make_scheduler(config, log):
        """Guard xdist's live scheduler choice on both sides of its hook chain."""
        _assert_xdist_scheduler_hook_chain(config)
        _assert_live_xdist_scheduler_mode(
            config,
            boundary="pytest_xdist_make_scheduler entry",
        )
        scheduler = yield
        _assert_live_xdist_scheduler_mode(
            config,
            boundary="pytest_xdist_make_scheduler exit",
        )
        _assert_xdist_scheduler_contract(config, scheduler)
        return scheduler

    @pytest.hookimpl(optionalhook=True)
    def pytest_configure_node(node):
        policy = node.config.stash[_HARNESS_CONFIG_KEY]
        node.workerinput["moira_test_seed"] = str(policy.seed)
        node.workerinput["moira_test_mode"] = "1" if policy.test_mode else "0"
        if policy.artifacts_enabled:
            node.workerinput["moira_test_run_id"] = policy.run_id
        node.workerinput["workerid"] = node.workerinput.get("workerid", "gw0")
        node.workerinput["moira_xdist_mode"] = _xdist_mode(node.config)
        expected = node.config.stash.get(
            _XDIST_CLASSIFICATION_EXPECTED_STATE_KEY,
            None,
        )
        if expected is None:
            expected = set()
            node.config.stash[
                _XDIST_CLASSIFICATION_EXPECTED_STATE_KEY
            ] = expected
        expected.add(node.workerinput["workerid"])
        evidence_expected = node.config.stash.get(
            _XDIST_EVIDENCE_EXPECTED_STATE_KEY,
            None,
        )
        if evidence_expected is None:
            evidence_expected = set()
            node.config.stash[_XDIST_EVIDENCE_EXPECTED_STATE_KEY] = (
                evidence_expected
            )
        evidence_expected.add(node.workerinput["workerid"])

    @pytest.hookimpl(optionalhook=True)
    def pytest_testnodedown(node, error):
        workeroutput = getattr(node, "workeroutput", {})
        planetary_worker_report = workeroutput.get(
            _XDIST_PLANETARY_RESOURCE_REPORT_KEY
        )

        config = node.config
        worker_id = node.workerinput.get(
            "workerid",
            getattr(getattr(node, "gateway", None), "id", "worker"),
        )
        coverage_reports = config.stash.get(
            _XDIST_COVERAGE_RUNTIME_REPORT_STATE_KEY,
            None,
        )
        if coverage_reports is None:
            coverage_reports = {}
            config.stash[_XDIST_COVERAGE_RUNTIME_REPORT_STATE_KEY] = (
                coverage_reports
            )
        coverage_errors = config.stash.get(
            _XDIST_COVERAGE_RUNTIME_ERRORS_STATE_KEY,
            None,
        )
        if coverage_errors is None:
            coverage_errors = []
            config.stash[_XDIST_COVERAGE_RUNTIME_ERRORS_STATE_KEY] = (
                coverage_errors
            )
        coverage_payload = workeroutput.get(
            _XDIST_COVERAGE_RUNTIME_REPORT_KEY
        )
        if error is not None:
            coverage_errors.append(
                f"xdist worker {worker_id} could not attest coverage runtime"
            )
        elif not isinstance(coverage_payload, dict):
            coverage_errors.append(
                f"xdist worker {worker_id} omitted coverage runtime attestation"
            )
        elif str(worker_id) in coverage_reports:
            coverage_errors.append(
                f"xdist worker {worker_id} repeated coverage runtime attestation"
            )
        else:
            coverage_reports[str(worker_id)] = coverage_payload
        collector = _controller_collector(config)
        if collector is not None:
            collector.record_worker_shutdown(
                worker_id=str(worker_id),
                error=error,
                workeroutput=workeroutput,
            )
        _accept_xdist_classification_report(
            config,
            worker_id=str(worker_id),
            payload=workeroutput.get(_XDIST_CLASSIFICATION_REPORT_KEY),
            violations_payload=workeroutput.get(
                _XDIST_CLASSIFICATION_VIOLATIONS_KEY
            ),
            worker_error=error,
        )
        _accept_xdist_evidence_report(
            config,
            worker_id=str(worker_id),
            payload=workeroutput.get(_XDIST_EVIDENCE_REPORT_KEY),
            worker_error=error,
        )
        if planetary_worker_report is not None:
            merged = config.stash.get(
                _XDIST_PLANETARY_RESOURCE_REPORT_STATE_KEY,
                None,
            )
            if merged is None:
                merged = _empty_planetary_resource_report()
                config.stash[
                    _XDIST_PLANETARY_RESOURCE_REPORT_STATE_KEY
                ] = merged
            _merge_planetary_resource_report(
                merged,
                planetary_worker_report,
                source=f"xdist worker {worker_id}",
            )

        small_body_worker_report = workeroutput.get(
            _XDIST_SMALL_BODY_RESOURCE_REPORT_KEY
        )
        if small_body_worker_report is not None:
            merged = config.stash.get(
                _XDIST_SMALL_BODY_RESOURCE_REPORT_STATE_KEY,
                None,
            )
            if merged is None:
                merged = _empty_small_body_resource_report()
                config.stash[
                    _XDIST_SMALL_BODY_RESOURCE_REPORT_STATE_KEY
                ] = merged
            _merge_small_body_resource_report(
                merged,
                small_body_worker_report,
                source=f"xdist worker {worker_id}",
            )

except ImportError:
    pass
