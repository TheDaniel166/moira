"""Conditional serving-polar-motion bounds with explicit source premises."""
from fractions import Fraction
import math

import pytest

from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_polar_motion_bounds import (
    EclipsePolarMotionUnavailable,
    bound_conditional_polar_motion,
)
from moira.polar_motion import PolarMotionRegistry, polar_motion_matrix


def _set_rows(monkeypatch, rows):
    monkeypatch.setattr(PolarMotionRegistry, "_data", rows)
    monkeypatch.setattr(PolarMotionRegistry, "_mjds", tuple(row[0] for row in rows))


def _assert_enclosed(result, jd):
    x, y = PolarMotionRegistry.polar_motion_at(jd)
    matrix = polar_motion_matrix(x, y)
    assert result.x_arcsec.contains(x)
    assert result.y_arcsec.contains(y)
    assert all(result.matrix[i][j].contains(matrix[i][j])
               for i in range(3) for j in range(3))


def test_real_table_interval_and_adjacent_knot_samples():
    PolarMotionRegistry.polar_motion_at(2460409.0)
    rows = PolarMotionRegistry._data
    assert rows
    knot = next(row[0] for row in rows if 60000 < row[0] < 61000) + 2400000.5
    start, end = knot - 0.1, knot + 0.1
    offsets = I(0, Fraction.from_float(end) - Fraction.from_float(start))
    result = bound_conditional_polar_motion(start, offsets)
    for jd in (start, math.nextafter(knot, -math.inf), knot,
               math.nextafter(knot, math.inf), end):
        assert offsets.contains(Fraction.from_float(jd) - Fraction.from_float(start))
        _assert_enclosed(result, jd)
    assert len(result.table_sha256) == 64
    assert not result.source_and_arithmetic_attested
    assert not result.full_earth_orientation_enclosed
    assert not result.physical_accuracy_certified


def test_clamped_duplicate_and_interpolated_branches(monkeypatch):
    rows = ((10.0, 0.2, -0.3), (11.0, 0.1, 0.4),
            (11.0, -0.5, 0.6), (12.0, 0.3, -0.2))
    _set_rows(monkeypatch, rows)
    anchor = 2400010.0
    result = bound_conditional_polar_motion(anchor, I(0, 4))
    for jd in (anchor, 2400010.5, 2400011.0, 2400011.5,
               math.nextafter(2400011.5, math.inf), 2400012.0,
               2400012.5, 2400013.0, 2400014.0):
        _assert_enclosed(result, jd)
    assert result.segments_examined == 2
    assert not result.zero_table_fallback


def test_empty_table_returns_the_source_zero_fallback(monkeypatch):
    _set_rows(monkeypatch, ())
    result = bound_conditional_polar_motion(2451545.0, I(-1, 1))
    assert result.zero_table_fallback
    assert result.x_arcsec == result.y_arcsec == I.point(0)
    _assert_enclosed(result, 2451545.0)


def test_exact_midpoint_has_independently_known_polar_values(monkeypatch):
    # All row values and the half-day interpolation fraction are exact in
    # binary64: x=0, y=1/4 arcsec at the midpoint. This analytic result does
    # not derive its expected coordinates from the registry implementation.
    _set_rows(monkeypatch, ((10.0, 0.5, -0.25), (11.0, -0.5, 0.75)))
    midpoint = 2400011.0
    result = bound_conditional_polar_motion(midpoint, I.point(0))
    assert result.x_arcsec.contains(0)
    assert result.y_arcsec.contains(Fraction(1, 4))
    assert result.matrix[0][0].contains(1)
    assert result.matrix[0][1].contains(0)
    assert result.matrix[0][2].contains(0)
    assert result.matrix[1][0].contains(0)
    assert result.matrix[2][0].contains(0)


def test_budget_and_invalid_registry_fail_closed(monkeypatch):
    rows = tuple((float(i), 0.01 * i, 0.02 * i) for i in range(5))
    _set_rows(monkeypatch, rows)
    with pytest.raises(EclipsePolarMotionUnavailable, match="budget"):
        bound_conditional_polar_motion(2400000.5, I(0, 4), max_segments=1)
    monkeypatch.setattr(PolarMotionRegistry, "_mjds", (0.0,))
    with pytest.raises(EclipsePolarMotionUnavailable, match="inconsistent"):
        bound_conditional_polar_motion(2400000.5, I(0, 1))
    _set_rows(monkeypatch, ((float("nan"), 0.0, 0.0),))
    with pytest.raises(EclipsePolarMotionUnavailable, match="invalid"):
        bound_conditional_polar_motion(2400000.5, I.point(0))


@pytest.mark.parametrize("anchor", [float("nan"), float("inf"), True, 10**400])
def test_invalid_anchor_rejected(anchor):
    with pytest.raises(ValueError):
        bound_conditional_polar_motion(anchor, I.point(0))
