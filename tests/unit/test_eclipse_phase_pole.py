"""Conditional FW pole enclosures, separate from actual apparent phase."""
from fractions import Fraction
import math

import pytest

from moira.constants import DEG2RAD
from moira.coordinates import mat_mul, rot_x_axis
from moira.obliquity import mean_obliquity
from moira.precession import precession_matrix
from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_interval_roots import EnclosureUnavailable
from moira._eclipse_phase_pole import (
    bound_fw_mean_ecliptic_pole,
    bound_mean_ecliptic_cross,
    bound_mean_ecliptic_projection,
)


@pytest.mark.parametrize("tt", [625296.0, 1026285.7107341307, 1721425.5,
                                2451545.0, 2459891.9582497696, 2688456.25, 4277794.0])
def test_fw_pole_contains_actual_p03_fw_matrix_samples(tt):
    offsets = I(Fraction(-5, 86400), Fraction(5, 86400))
    bounds = bound_fw_mean_ecliptic_pole(tt, offsets)
    assert not bounds.source_and_constants_attested
    assert not bounds.arithmetic_environment_attested
    assert not bounds.actual_nutation_enclosed
    assert not bounds.actual_phase_enclosed
    assert not bounds.ut1_enclosed
    for seconds in (-2, 0, 2):
        epoch = tt + seconds / 86400
        actual = mat_mul(rot_x_axis(mean_obliquity(epoch) * DEG2RAD), precession_matrix(epoch))
        assert all(box.contains(value) for boxes, row in zip(bounds.mean_matrix, actual)
                   for box, value in zip(boxes, row))
        assert all(box.contains(value) for box, value in zip(bounds.pole, actual[2]))


def test_fw_pole_cross_is_only_a_mathematical_direction_bound():
    bounds = bound_fw_mean_ecliptic_pole(2451545.0, I.point(0))
    sun = (I.point(1), I.point(0), I.point(0))
    moon = (I.point(0), I.point(1), I.point(0))
    cross = bound_mean_ecliptic_cross(bounds, sun, moon)
    assert cross.lo > 0
    assert not bounds.actual_phase_enclosed


def test_reference_projection_encloses_exact_matrix_vector_products():
    tt = 2459891.9582497696
    bounds = bound_fw_mean_ecliptic_pole(tt, I.point(0))
    vector = (123456.5, -98765.25, 43210.75)
    projected = bound_mean_ecliptic_projection(bounds, tuple(I.point(x) for x in vector))
    actual = mat_mul(rot_x_axis(mean_obliquity(tt) * DEG2RAD), precession_matrix(tt))
    for enclosure, row in zip(projected, actual):
        exact = sum((Fraction.from_float(a) * Fraction.from_float(b) for a, b in zip(row, vector)), Fraction(0))
        assert enclosure.contains(exact)


def test_fw_pole_covers_the_full_fw_branch_in_one_closed_box():
    anchor = 2451545.0
    bounds = bound_fw_mean_ecliptic_pole(anchor, I(-1826249, 1826249))
    for offset in (-1826249, -1000000, -1, 0, 1, 1000000, 1826249):
        epoch = anchor + offset
        actual = mat_mul(rot_x_axis(mean_obliquity(epoch) * DEG2RAD), precession_matrix(epoch))[2]
        assert all(box.contains(value) for box, value in zip(bounds.pole, actual))


@pytest.mark.parametrize("tt", [625294.0, 4277796.0, -1000000.0])
def test_vondrak_or_unproved_precession_branch_is_unavailable(tt):
    with pytest.raises(EnclosureUnavailable, match="FW/Vondrak"):
        bound_fw_mean_ecliptic_pole(tt, I.point(0))


def test_fw_boundary_and_invalid_values_are_unavailable_or_errors():
    boundary = 2451545.0 + 50 * 36525.0
    with pytest.raises(EnclosureUnavailable, match="branch"):
        bound_fw_mean_ecliptic_pole(boundary, I(-1, 1))
    for value in (float("nan"), float("inf"), True):
        with pytest.raises(ValueError):
            bound_fw_mean_ecliptic_pole(value, I.point(0))
    assert math.isfinite(boundary)
