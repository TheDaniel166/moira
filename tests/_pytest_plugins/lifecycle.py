"""Per-case lifecycle timing and runtime-budget policy."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import math
import time

import pytest

from ._state import (
    _CASE_LIFECYCLE_KEY,
    _HARNESS_CONFIG_KEY,
    _SESSION_PERF_START_KEY,
    _SESSION_TOTAL_BUDGET_KEY,
    _SESSION_UTC_START_KEY,
    _CaseLifecycleState,
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart(session) -> None:
    """Start the controller's monotonic and wall-clock session receipts."""

    session.config.stash[_SESSION_PERF_START_KEY] = time.perf_counter()
    session.config.stash[_SESSION_UTC_START_KEY] = _utc_now_iso()


_CASE_PHASES = ("setup", "call", "teardown")


def _case_phase_payload(
    state: _CaseLifecycleState,
) -> tuple[dict[str, object], float]:
    phases: dict[str, object] = {}
    total = 0.0
    for phase in _CASE_PHASES:
        phase_report = state.reports.get(phase)
        if phase_report is None:
            phases[phase] = {
                "status": "not_run",
                "outcome": None,
                "duration_s": 0.0,
            }
            continue
        duration = float(getattr(phase_report, "duration", 0.0))
        if not math.isfinite(duration) or duration < 0:
            duration = 0.0
        total += duration
        phases[phase] = {
            "status": "reported",
            "outcome": str(getattr(phase_report, "outcome", "unknown")),
            "duration_s": duration,
        }
    return phases, total


def _case_budget_message(
    *,
    nodeid: str,
    phases: dict[str, object],
    total_s: float,
    budget_s: float,
) -> str:
    rendered_phases: list[str] = []
    for phase in _CASE_PHASES:
        detail = phases[phase]
        assert isinstance(detail, dict)
        if detail["status"] == "not_run":
            rendered_phases.append(f"{phase}=not_run")
        else:
            rendered_phases.append(
                f"{phase}={float(detail['duration_s']):.3f}s"
            )
    return (
        f"{nodeid} exceeded the Moira case budget: "
        + ", ".join(rendered_phases)
        + f", total={total_s:.3f}s, budget={budget_s:.3f}s"
    )


def _append_report_section(report, name: str, content: str) -> None:
    sections = getattr(report, "sections", None)
    if sections is None:
        sections = []
        report.sections = sections
    if (name, content) not in sections:
        sections.append((name, content))


def _total_budget_observation(session) -> dict[str, object]:
    started = session.config.stash.get(
        _SESSION_PERF_START_KEY,
        time.perf_counter(),
    )
    elapsed_s = max(0.0, time.perf_counter() - started)
    budget_s = session.config.stash[_HARNESS_CONFIG_KEY].budget_total_s
    observation = {
        "clock": "time.perf_counter",
        "elapsed_s": elapsed_s,
        "budget_s": budget_s,
        "exceeded": bool(budget_s and elapsed_s > budget_s),
    }
    session.config.stash[_SESSION_TOTAL_BUDGET_KEY] = observation
    return observation

@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    """Finalize lifecycle evidence before artifact redaction shadows it."""

    report = yield
    phase = str(getattr(report, "when", "unknown"))
    if phase == "setup":
        state = _CaseLifecycleState()
        item.stash[_CASE_LIFECYCLE_KEY] = state
    else:
        state = item.stash.get(
            _CASE_LIFECYCLE_KEY,
            _CaseLifecycleState(),
        )
        item.stash[_CASE_LIFECYCLE_KEY] = state
    if phase in _CASE_PHASES:
        state.reports[phase] = report
    if phase != "teardown":
        return report

    phases, total_s = _case_phase_payload(state)
    case_budget_s = item.config.stash[
        _HARNESS_CONFIG_KEY
    ].budget_case_s
    budget_exceeded = bool(
        case_budget_s and total_s > case_budget_s
    )
    phase_json = json.dumps(
        phases,
        allow_nan=False,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )
    properties = list(getattr(report, "user_properties", ()) or ())
    properties.extend(
        (
            ("moira_lifecycle_total_s", total_s),
            ("moira_phase_durations_json", phase_json),
            ("moira_case_budget_s", case_budget_s),
            ("moira_case_budget_exceeded", budget_exceeded),
        )
    )
    report.user_properties = properties

    if budget_exceeded:
        message = _case_budget_message(
            nodeid=str(getattr(report, "nodeid", item.nodeid)),
            phases=phases,
            total_s=total_s,
            budget_s=case_budget_s,
        )
        failed_reports = [
            phase_report
            for phase_report in state.reports.values()
            if getattr(phase_report, "outcome", None) == "failed"
        ]
        for phase_report in (*failed_reports, report):
            _append_report_section(
                phase_report,
                "Moira case budget",
                message,
            )
        if not failed_reports:
            report.outcome = "failed"
            report.longrepr = message
    return report
