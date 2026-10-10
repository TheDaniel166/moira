from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import pytest

from scripts import audit_comet_solution_freshness as audit


def _master(path: Path, records: list[dict[str, object]]) -> Path:
    path.write_text(json.dumps({"records": records}), encoding="utf-8")
    return path


def _raw(solution: str, number: int = 1) -> str:
    return f"""JPL/HORIZONS
Target body name: {number}P/Test {{source: {solution}}}
Center body name: Sun (10) {{source: DE441}}
"""


def test_parse_current_solution_from_vector_source_header() -> None:
    assert audit.parse_current_solution(_raw("JPL#K273/19", 2)) == "JPL#K273/19"


def test_legacy_database_source_is_compared_in_the_same_namespace() -> None:
    assert audit.parse_current_solution(_raw("DASTCOM", 35)) == "DASTCOM"


def test_catalog_audit_is_fail_closed_on_drift_and_error(tmp_path: Path) -> None:
    master = _master(
        tmp_path / "master.json",
        [
            {"number": 1, "name": "1P/Test", "target_solution": "JPL#1"},
            {"number": 2, "name": "2P/Test", "target_solution": "JPL#2"},
            {"number": 3, "name": "3P/Test", "target_solution": "JPL#3"},
        ],
    )

    def fetch(number: int) -> str:
        if number == 3:
            raise RuntimeError("synthetic authority failure")
        return _raw("JPL#1" if number == 1 else "JPL#9", number)

    report = audit.audit_catalog(
        master,
        tmp_path / "audit.json",
        fetch=fetch,
        throttle_seconds=0,
    )

    assert report["completed"] is True
    assert report["summary"] == {
        "catalog_records": 3,
        "checked_records": 3,
        "match": 1,
        "stale": 1,
        "error": 1,
        "passed": False,
    }


def test_recent_checkpoint_resumes_only_completed_queries(tmp_path: Path) -> None:
    master = _master(
        tmp_path / "master.json",
        [
            {"number": 1, "target_solution": "JPL#1"},
            {"number": 2, "target_solution": "JPL#2"},
        ],
    )
    output = tmp_path / "audit.json"
    current = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
    first_calls: list[int] = []

    def interrupted_fetch(number: int) -> str:
        first_calls.append(number)
        if number == 2:
            raise KeyboardInterrupt
        return _raw("JPL#1", number)

    with pytest.raises(KeyboardInterrupt):
        audit.audit_catalog(
            master,
            output,
            fetch=interrupted_fetch,
            throttle_seconds=0,
            now=lambda: current,
        )
    assert first_calls == [1, 2]

    resumed_calls: list[int] = []
    report = audit.audit_catalog(
        master,
        output,
        fetch=lambda number: resumed_calls.append(number) or _raw("JPL#2", number),
        throttle_seconds=0,
        now=lambda: current + timedelta(minutes=5),
    )

    assert resumed_calls == [2]
    assert report["summary"]["passed"] is True


def test_expired_checkpoint_is_not_reused(tmp_path: Path) -> None:
    master = _master(
        tmp_path / "master.json",
        [{"number": 1, "target_solution": "JPL#1"}],
    )
    output = tmp_path / "audit.json"
    start = datetime(2026, 10, 1, 0, tzinfo=timezone.utc)
    audit.audit_catalog(
        master,
        output,
        fetch=lambda _number: _raw("JPL#1"),
        throttle_seconds=0,
        now=lambda: start,
    )
    calls: list[int] = []

    audit.audit_catalog(
        master,
        output,
        fetch=lambda number: calls.append(number) or _raw("JPL#1"),
        throttle_seconds=0,
        resume_max_age_hours=6,
        now=lambda: start + timedelta(hours=7),
    )

    assert calls == [1]


def test_catalog_audit_can_emit_a_receipted_numbered_delta(tmp_path: Path) -> None:
    master = _master(
        tmp_path / "master.json",
        [
            {"number": 1, "target_solution": "JPL#1"},
            {"number": 2, "target_solution": "JPL#OLD"},
        ],
    )
    calls: list[int] = []

    report = audit.audit_catalog(
        master,
        tmp_path / "delta.json",
        numbers={2},
        fetch=lambda number: calls.append(number) or _raw("JPL#NEW", number),
        throttle_seconds=0,
    )

    assert calls == [2]
    assert report["selected_numbers"] == [2]
    assert report["summary"] == {
        "catalog_records": 2,
        "checked_records": 1,
        "match": 0,
        "stale": 1,
        "error": 0,
        "passed": False,
    }


def test_catalog_rejects_missing_solution_and_duplicate_numbers(tmp_path: Path) -> None:
    missing = _master(tmp_path / "missing.json", [{"number": 1}])
    with pytest.raises(ValueError, match="lack target_solution"):
        audit.audit_catalog(missing, tmp_path / "missing-audit.json")

    duplicate = _master(
        tmp_path / "duplicate.json",
        [
            {"number": 1, "target_solution": "JPL#1"},
            {"number": 1, "target_solution": "JPL#1"},
        ],
    )
    with pytest.raises(ValueError, match="duplicate"):
        audit.audit_catalog(duplicate, tmp_path / "duplicate-audit.json")
