"""Synthetic contracts for phase/max ordering, budgets and coverage failures."""
import math
from types import SimpleNamespace

import pytest

import moira.eclipse as eclipse
from moira.spk_reader import OutOfRangeError


def _calculator(monkeypatch, *, adjacent_phase, adjacent_maximum, requested_kind="any"):
    """Supply isolated phase and event behavior, without an ephemeris oracle."""
    calculator = eclipse.EclipseCalculator(reader=object())
    calls = []

    def crossing(_name, left, right, _reader):
        if right - left < 0.01:
            return left + (right - left) / 2
        return adjacent_phase if left <= adjacent_phase <= right else None

    def near(phase, *, kind_key):
        calls.append((phase, kind_key))
        if abs(phase - adjacent_phase) < 1e-5:
            if kind_key != requested_kind:
                return None
            return SimpleNamespace(jd_ut=adjacent_maximum)
        return SimpleNamespace(jd_ut=1030.01)

    monkeypatch.setattr(eclipse, "_phase_crossing_in_window", crossing)
    monkeypatch.setattr(calculator, "_solar_eclipse_near_syzygy", near)
    monkeypatch.setattr(eclipse, "next_moon_phase", lambda *_a, **_k: SimpleNamespace(jd_ut=1030.0))
    return calculator, calls


@pytest.mark.parametrize("phase", [1000.0 - 0.125, math.nextafter(1000.0 - 0.125, math.inf)])
def test_opposite_phase_inside_optimizer_boundary_can_supply_future_maximum(monkeypatch, phase):
    calculator, calls = _calculator(
        monkeypatch, adjacent_phase=phase, adjacent_maximum=math.nextafter(1000.0, math.inf),
    )
    event = calculator._search_solar_eclipse(1000.0, kind="any", backward=False, max_lunations=1)
    assert event.jd_ut == math.nextafter(1000.0, math.inf)
    assert len(calls) == 1


def test_opposite_candidate_on_wrong_side_does_not_consume_directional_budget(monkeypatch):
    calculator, calls = _calculator(monkeypatch, adjacent_phase=999.9, adjacent_maximum=999.99)
    event = calculator._search_solar_eclipse(1000.0, kind="any", backward=False, max_lunations=1)
    assert event.jd_ut == 1030.01
    assert len(calls) == 2
    assert calculator._search_solar_eclipse(1000.0, kind="any", backward=False, max_lunations=1) is event
    assert len(calls) == 2  # second call was a cache hit


def test_nonmatching_opposite_phase_does_not_override_kind(monkeypatch):
    calculator, calls = _calculator(
        monkeypatch, adjacent_phase=999.9, adjacent_maximum=1000.01, requested_kind="partial",
    )
    event = calculator._search_solar_eclipse(1000.0, kind="total", backward=False, max_lunations=1)
    assert event.jd_ut == 1030.01
    assert all(kind == "total" for _, kind in calls)


def test_coverage_failure_is_not_misreported_as_no_eclipse(monkeypatch):
    calculator = eclipse.EclipseCalculator(reader=object())

    def fail(*_args, **_kwargs):
        raise OutOfRangeError("phase window outside kernel", True)

    monkeypatch.setattr(eclipse, "_phase_crossing_in_window", fail)
    with pytest.raises(OutOfRangeError, match="outside kernel"):
        calculator.next_solar_eclipse(1000.0)


@pytest.mark.parametrize("family", ["solar", "lunar", "canon"])
@pytest.mark.parametrize("backward", [False, True])
@pytest.mark.parametrize("budget", [1, 2])
def test_exhausted_lunation_budget_never_fetches_an_extra_phase(
    monkeypatch, family, backward, budget,
):
    """A missing phase beyond the budget cannot mask the budget result."""
    calculator = eclipse.EclipseCalculator(reader=object())
    monkeypatch.setattr(eclipse, "_canon_ut_half_window", lambda *_: 0.125)

    def crossing(_name, left, right, _reader):
        return left + (right - left) / 2 if right - left < 0.01 else None

    calls = []

    def phase(*_args, **_kwargs):
        calls.append(None)
        if len(calls) > budget:
            raise OutOfRangeError("unneeded phase outside coverage", True)
        value = 1000.0 + (-30 if backward else 30) * len(calls)
        return value if backward else SimpleNamespace(jd_ut=value)

    monkeypatch.setattr(eclipse, "_phase_crossing_in_window", crossing)
    monkeypatch.setattr(eclipse, "next_moon_phase", phase)
    monkeypatch.setattr(eclipse, "last_new_moon", phase)
    monkeypatch.setattr(eclipse, "last_full_moon", phase)
    monkeypatch.setattr(calculator, "_solar_eclipse_near_syzygy", lambda *_a, **_k: None)
    monkeypatch.setattr(calculator, "_lunar_eclipse_near_syzygy", lambda *_a, **_k: None)
    with pytest.raises(RuntimeError, match="No (previous|next)"):
        if family == "solar":
            calculator._search_solar_eclipse(1000.0, kind="any", backward=backward, max_lunations=budget)
        else:
            calculator._search_lunar_eclipse(
                1000.0, kind="any", backward=backward,
                use_canon=family == "canon", max_lunations=budget,
            )
    assert len(calls) == budget


@pytest.mark.parametrize("family", ["solar", "lunar", "canon"])
@pytest.mark.parametrize("backward", [False, True])
def test_required_phase_coverage_failure_still_propagates(monkeypatch, family, backward):
    """The second phase is necessary when the scan budget includes it."""
    calculator = eclipse.EclipseCalculator(reader=object())
    monkeypatch.setattr(eclipse, "_canon_ut_half_window", lambda *_: 0.125)
    monkeypatch.setattr(
        eclipse, "_phase_crossing_in_window",
        lambda _n, left, right, _r: left + (right - left) / 2 if right - left < 0.01 else None,
    )
    calls = []

    def phase(*_args, **_kwargs):
        calls.append(None)
        if len(calls) == 2:
            raise OutOfRangeError("required phase outside coverage", True)
        return 970.0 if backward else SimpleNamespace(jd_ut=1030.0)

    monkeypatch.setattr(eclipse, "next_moon_phase", phase)
    monkeypatch.setattr(eclipse, "last_new_moon", phase)
    monkeypatch.setattr(eclipse, "last_full_moon", phase)
    monkeypatch.setattr(calculator, "_solar_eclipse_near_syzygy", lambda *_a, **_k: None)
    monkeypatch.setattr(calculator, "_lunar_eclipse_near_syzygy", lambda *_a, **_k: None)
    with pytest.raises(OutOfRangeError, match="required phase"):
        if family == "solar":
            calculator._search_solar_eclipse(1000.0, kind="any", backward=backward, max_lunations=2)
        else:
            calculator._search_lunar_eclipse(
                1000.0, kind="any", backward=backward,
                use_canon=family == "canon", max_lunations=2,
            )
    assert len(calls) == 2


@pytest.mark.parametrize("backward", [False, True])
def test_unbounded_solar_search_continues_until_provider_coverage_ends(monkeypatch, backward):
    """An absent solar budget must not become an implicit one-phase budget."""
    calculator = eclipse.EclipseCalculator(reader=object())
    monkeypatch.setattr(
        eclipse, "_phase_crossing_in_window",
        lambda _n, left, right, _r: left + (right - left) / 2 if right - left < 0.01 else None,
    )
    monkeypatch.setattr(calculator, "_solar_eclipse_near_syzygy", lambda *_a, **_k: None)
    calls = []

    def phase(*_args, **_kwargs):
        calls.append(None)
        if len(calls) == 2:
            raise OutOfRangeError("unbounded search reached kernel end", True)
        return 970.0 if backward else SimpleNamespace(jd_ut=1030.0)

    monkeypatch.setattr(eclipse, "next_moon_phase", phase)
    monkeypatch.setattr(eclipse, "last_new_moon", phase)
    with pytest.raises(OutOfRangeError, match="unbounded search reached kernel end"):
        calculator._search_solar_eclipse(1000.0, kind="any", backward=backward)
    assert len(calls) == 2
