"""Ordering regressions for observer-local solar eclipse searches."""
from __future__ import annotations

import math

import pytest

from moira import _eclipse_phase_window
from moira._eclipse_phase_window import _phase_crossing_in_window
from moira.spk_reader import OutOfRangeError


pytestmark = [pytest.mark.requires_ephemeris, pytest.mark.slow]


def test_solar_local_next_does_not_return_past_maximum(eclipse_calculator):
    """At 19 N, 100 W the 2024 local maximum precedes the new Moon."""
    query = 2460409.261365168
    try:
        result = eclipse_calculator.next_solar_eclipse_at_location(
            query, 19.0, -100.0, max_lunations=3
        )
    except RuntimeError as exc:
        assert "No solar eclipse" in str(exc)
    else:
        assert result.event.jd_ut > query


@pytest.mark.parametrize("kind", ["any", "total", "central"])
def test_solar_local_next_recovers_maximum_after_previous_phase(eclipse_calculator, kind):
    """Dallas local maximum follows the 2024 April 8 new Moon."""
    query = 2460409.272051111
    result = eclipse_calculator.next_solar_eclipse_at_location(
        query, 32.7767, -96.7970, kind=kind, max_lunations=1
    )
    assert result.event.jd_ut > query
    assert result.event.jd_ut == pytest.approx(2460409.27961734, abs=2e-6)
    assert result.topocentric_overlap
    assert result.sun.visible


def test_local_strict_maximum_and_adjacent_float_order(eclipse_calculator):
    """An event is returned before its maximum, but not at or after it."""
    calc = eclipse_calculator
    result = calc.next_solar_eclipse_at_location(
        2460390.0, 32.7767, -96.7970, max_lunations=3
    )
    greatest = result.event.jd_ut
    before = calc.next_solar_eclipse_at_location(
        math.nextafter(greatest, -math.inf), 32.7767, -96.7970, max_lunations=1
    )
    assert before.event.jd_ut == greatest
    for query in (greatest, math.nextafter(greatest, math.inf)):
        with pytest.raises(RuntimeError, match="No solar eclipse"):
            calc.next_solar_eclipse_at_location(
                query, 32.7767, -96.7970, max_lunations=1
            )


def test_local_exact_new_moon_and_adjacent_floats(eclipse_calculator):
    calc = eclipse_calculator
    phase = _phase_crossing_in_window(
        "New Moon", 2460409.1, 2460409.4, calc._reader
    )
    assert phase is not None
    results = [calc.next_solar_eclipse_at_location(
        query, 32.7767, -96.7970, max_lunations=1
    ).event.jd_ut for query in (math.nextafter(phase, -math.inf), phase,
                                math.nextafter(phase, math.inf))]
    assert results[0] == results[1] == results[2]
    assert results[0] > phase


def test_local_unknown_past_coverage_does_not_become_no_event(eclipse_calculator, monkeypatch):
    query = 2460409.272051111

    def outside_coverage(jd, reader):
        if jd < query:
            raise OutOfRangeError("lookback is not covered", out_of_range_times=True)
        return 1.0

    monkeypatch.setattr(_eclipse_phase_window, "_sun_moon_phase_angle", outside_coverage)
    with pytest.raises(OutOfRangeError, match="lookback is not covered"):
        eclipse_calculator.next_solar_eclipse_at_location(
            query, 32.7767, -96.7970, max_lunations=1
        )
