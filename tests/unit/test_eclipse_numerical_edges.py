from __future__ import annotations

import math

import pytest

from moira.eclipse_contacts import _find_roots, find_lunar_contacts
from moira.eclipse_geometry import angular_separation


def test_angular_separation_resolves_tiny_longitude_offset() -> None:
    assert angular_separation(0.0, 0.0, 1.0e-8, 0.0) == pytest.approx(
        1.0e-8,
        rel=1.0e-12,
    )


def test_angular_separation_is_zero_for_coincident_points() -> None:
    assert angular_separation(123.456, -42.25, 123.456, -42.25) == 0.0


def test_angular_separation_resolves_tiny_latitude_offset() -> None:
    assert angular_separation(123.0, 37.0, 123.0, 37.0 + 1.0e-8) == pytest.approx(
        1.0e-8,
        rel=1.0e-6,
    )


def test_angular_separation_resolves_near_antipodal_offset() -> None:
    expected = 180.0 - 1.0e-8
    assert angular_separation(0.0, 0.0, expected, 0.0) == pytest.approx(
        expected,
        abs=1.0e-12,
    )


def test_angular_separation_handles_exact_antipodes() -> None:
    assert angular_separation(42.0, 23.0, 222.0, -23.0) == pytest.approx(
        180.0,
        abs=1.0e-12,
    )


def test_root_scan_deduplicates_an_exact_grid_root() -> None:
    assert _find_roots(lambda value: value - 1.0, 0.0, 2.0, 1.0) == [1.0]


def test_root_scan_clamps_final_interval_to_end() -> None:
    evaluated: list[float] = []

    def objective(value: float) -> float:
        evaluated.append(value)
        return value - 1.1

    roots = _find_roots(objective, 0.0, 1.0, 0.6)
    assert roots == []
    assert evaluated[-1] == 1.0
    assert all(0.0 <= value <= 1.0 for value in evaluated)


def test_root_scan_finds_root_in_clamped_final_interval() -> None:
    roots = _find_roots(lambda value: value - 0.9, 0.0, 1.0, 0.6)
    assert roots == pytest.approx([0.9], abs=1.0e-15)
    assert all(0.0 <= root <= 1.0 for root in roots)


@pytest.mark.parametrize(
    ("start", "end", "step_days", "message"),
    [
        (math.nan, 1.0, 0.1, "finite"),
        (0.0, math.inf, 0.1, "finite"),
        (0.0, 1.0, math.nan, "finite"),
        (0.0, 1.0, math.inf, "finite"),
        (1.0, 1.0, 0.1, "greater than start"),
        (2.0, 1.0, 0.1, "greater than start"),
        (0.0, 1.0, 0.0, "greater than zero"),
        (0.0, 1.0, -0.1, "greater than zero"),
    ],
)
def test_root_scan_rejects_invalid_window_or_step(
    start: float,
    end: float,
    step_days: float,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        _find_roots(lambda value: value, start, end, step_days)


def test_root_scan_rejects_a_step_too_small_to_advance() -> None:
    with pytest.raises(ValueError, match="too small to advance"):
        _find_roots(lambda value: value, 2_451_545.0, 2_451_546.0, 1.0e-20)


@pytest.mark.parametrize("non_finite", [math.nan, math.inf, -math.inf])
def test_root_scan_rejects_non_finite_function_values(non_finite: float) -> None:
    with pytest.raises(ValueError, match="function returned a non-finite value"):
        _find_roots(lambda _value: non_finite, 0.0, 1.0, 0.1)


class _UncalledCalculator:
    def calculate_jd(self, _jd: float):
        raise AssertionError("invalid public input reached the calculator")


@pytest.mark.parametrize(
    ("center_jd", "window_days", "coarse_step_seconds", "message"),
    [
        (math.nan, 0.2, 60.0, "center_jd must be finite"),
        (math.inf, 0.2, 60.0, "center_jd must be finite"),
        (2_451_545.0, math.nan, 60.0, "window_days must be finite"),
        (2_451_545.0, math.inf, 60.0, "window_days must be finite"),
        (2_451_545.0, 0.0, 60.0, "window_days must be finite"),
        (2_451_545.0, -0.2, 60.0, "window_days must be finite"),
        (2_451_545.0, 0.2, math.nan, "coarse_step_seconds must be finite"),
        (2_451_545.0, 0.2, math.inf, "coarse_step_seconds must be finite"),
        (2_451_545.0, 0.2, 0.0, "coarse_step_seconds must be finite"),
        (2_451_545.0, 0.2, -1.0, "coarse_step_seconds must be finite"),
    ],
)
def test_public_contact_solver_rejects_invalid_inputs_before_computation(
    center_jd: float,
    window_days: float,
    coarse_step_seconds: float,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        find_lunar_contacts(
            _UncalledCalculator(),
            center_jd,
            window_days=window_days,
            coarse_step_seconds=coarse_step_seconds,
        )


def test_public_contact_solver_rejects_a_collapsed_finite_window() -> None:
    with pytest.raises(ValueError, match="finite ordered bounds"):
        find_lunar_contacts(
            _UncalledCalculator(),
            1.0e16,
            window_days=0.5,
            coarse_step_seconds=60.0,
        )
