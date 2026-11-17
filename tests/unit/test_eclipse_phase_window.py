"""Bounded phase-window ordering tests using the existing phase observable."""
from __future__ import annotations

import math

import pytest

from moira import _eclipse_phase_window as phase_window
from moira.spk_reader import OutOfRangeError


@pytest.mark.parametrize("target,name", [(0.0, "New Moon"), (180.0, "Full Moon")])
def test_phase_crossing_is_stable_for_overlapping_brackets(monkeypatch, target, name):
    root = 2459891.95983
    monkeypatch.setattr(
        phase_window, "_sun_moon_phase_angle",
        lambda jd, reader: (target + (jd - root) * 13.0) % 360.0,
    )
    first = phase_window._phase_crossing_in_window(name, root - 0.2, root + 0.1, None)
    second = phase_window._phase_crossing_in_window(name, root - 0.1, root + 0.2, None)
    assert first == second
    assert abs(first - root) <= 2 * math.ulp(root)


def test_window_rejects_phase_opposition_wrap(monkeypatch):
    monkeypatch.setattr(
        phase_window, "_sun_moon_phase_angle",
        lambda jd, reader: 179.0 if jd < 0.5 else 181.0,
    )
    assert phase_window._phase_crossing_in_window("New Moon", 0.0, 1.0, None) is None


def test_endpoint_and_ephemeris_errors_propagate(monkeypatch):
    monkeypatch.setattr(phase_window, "_sun_moon_phase_angle", lambda jd, reader: jd)
    assert phase_window._phase_crossing_in_window("New Moon", 0.0, 1.0, None) > 0.0

    def fail(jd, reader):
        raise ArithmeticError("provider failure")

    monkeypatch.setattr(phase_window, "_sun_moon_phase_angle", fail)
    with pytest.raises(ArithmeticError, match="provider failure"):
        phase_window._phase_crossing_in_window("New Moon", 0.0, 1.0, None)


def test_zero_plateau_is_not_claimed_resolved_at_upper_endpoint(monkeypatch):
    def angle(jd, reader):
        return (0.0 if 0.4 <= jd <= 0.6 else jd - 0.5) % 360.0

    monkeypatch.setattr(phase_window, "_sun_moon_phase_angle", angle)
    crossing = phase_window._phase_crossing_in_window("New Moon", 0.3, 0.8, None)
    assert crossing == phase_window._phase_crossing_in_window("New Moon", 0.5, 0.8, None)
    with pytest.raises(phase_window.PhaseWindowUnresolved):
        phase_window._phase_crossing_in_window("New Moon", 0.3, 0.5, None)


def test_coverage_error_is_not_treated_as_no_phase(monkeypatch):
    def angle(jd, reader):
        if jd < 10.0:
            raise OutOfRangeError("kernel coverage ended", out_of_range_times=True)
        return 3.0

    monkeypatch.setattr(phase_window, "_sun_moon_phase_angle", angle)
    with pytest.raises(OutOfRangeError, match="kernel coverage ended"):
        phase_window._phase_crossing_in_window("New Moon", 9.9, 10.1, None)


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("name,root", [("New Moon", 2460409.26448), ("Full Moon", 2460394.79189)])
def test_de441_phase_crossing_stability_under_bracket_changes(eclipse_calculator, name, root):
    reader = eclipse_calculator._reader
    first = phase_window._phase_crossing_in_window(name, root - 0.2, root + 0.1, reader)
    second = phase_window._phase_crossing_in_window(name, root - 0.1, root + 0.2, reader)
    assert first is not None and first == second
