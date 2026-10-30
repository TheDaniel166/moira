from __future__ import annotations

from datetime import datetime, timezone

import pytest

import moira.eclipse as eclipse


def test_eclipse_datetime_input_crosses_utc_to_ut1_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: list[float] = []
    calculator = object.__new__(eclipse.EclipseCalculator)

    monkeypatch.setattr(eclipse, "jd_from_datetime", lambda _dt: 100.0)
    monkeypatch.setattr(eclipse, "utc_to_ut1", lambda jd: jd + 0.25)
    monkeypatch.setattr(
        eclipse.EclipseCalculator,
        "calculate_jd",
        lambda _self, jd: received.append(jd) or object(),
    )

    calculator.calculate(datetime(2026, 7, 17, 12, tzinfo=timezone.utc))

    assert received == [100.25]


def test_eclipse_event_datetime_converts_ut1_back_to_utc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: list[float] = []
    expected = datetime(2026, 7, 17, 12, tzinfo=timezone.utc)

    # The event hands its UT1 value to the leap-second-aware UT1 -> UTC helper; it never decodes
    # a UT1 Julian Day as if it were already UTC.
    monkeypatch.setattr(
        eclipse,
        "utc_datetime_from_ut1",
        lambda jd: received.append(jd) or expected,
    )

    event = eclipse.EclipseEvent(jd_ut=100.25, data=None)  # type: ignore[arg-type]

    assert event.datetime_utc is expected
    assert received == [100.25]
