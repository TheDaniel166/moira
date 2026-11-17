"""Bulk eclipse candidates must use the phase and errors of the Python search."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

import moira.eclipse as eclipse
from moira._eclipse_phase_window import PhaseWindowUnresolved
from moira.spk_reader import OutOfRangeError


@pytest.mark.parametrize("family", ["solar", "lunar"])
def test_empty_bulk_candidate_list_returns_empty_without_phase_search(monkeypatch, family):
    calc = eclipse.EclipseCalculator(reader=object())

    def unexpected(*_args, **_kwargs):
        raise AssertionError("no phase is needed for an empty candidate list")

    monkeypatch.setattr(eclipse, "_phase_crossing_in_window", unexpected)
    assert calc._eclipses_from_syzygy_candidates(family, [], 999.0, 1001.0) == []


@pytest.mark.parametrize("family", ["solar", "lunar"])
@pytest.mark.parametrize("unresolved", [False, True])
def test_unbracketed_bulk_candidate_falls_back_to_python_range(monkeypatch, family, unresolved):
    calc = eclipse.EclipseCalculator(reader=object())
    expected = [SimpleNamespace(jd_ut=1000.0)]
    calls = []

    def crossing(*_args, **_kwargs):
        if unresolved:
            raise PhaseWindowUnresolved("phase bracket unresolved")
        return None

    def fallback(start, end):
        calls.append((start, end))
        return expected

    monkeypatch.setattr(eclipse, "_phase_crossing_in_window", crossing)
    monkeypatch.setattr(calc, f"_{family}_eclipses_in_range_python", fallback)
    result = calc._eclipses_from_syzygy_candidates(family, [1000.0], 999.0, 1001.0)
    assert result is expected
    assert calls == [(999.0, 1001.0)]


@pytest.mark.parametrize("family", ["solar", "lunar"])
def test_bulk_candidate_phase_coverage_error_is_not_suppressed(monkeypatch, family):
    calc = eclipse.EclipseCalculator(reader=object())

    def fail(*_args, **_kwargs):
        raise OutOfRangeError("phase bracket outside coverage", out_of_range_times=True)

    monkeypatch.setattr(eclipse, "_phase_crossing_in_window", fail)
    with pytest.raises(OutOfRangeError, match="outside coverage"):
        calc._eclipses_from_syzygy_candidates(family, [1000.0], 999.0, 1001.0)
