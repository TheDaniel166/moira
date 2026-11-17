"""Conditional long-term precession/mean-ecliptic interval enclosures."""
from fractions import Fraction

import pytest

from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_interval_roots import EnclosureUnavailable
from moira._eclipse_vondrak_bounds import bound_vondrak_mean_ecliptic_pole
from moira._eclipse_strict_vondrak import strict_vondrak_precession_matrix
from moira.constants import DEG2RAD
from moira.coordinates import mat_mul, rot_x_axis
from moira.obliquity import mean_obliquity
from moira.precession import precession_matrix


@pytest.mark.parametrize("centuries", [-199, -151, -116, -51, 51, 151, 199])
def test_vondrak_intervals_contain_actual_matrix_and_pole(centuries):
    tt = 2451545.0 + centuries * 36525.0 + 0.25
    bounds = bound_vondrak_mean_ecliptic_pole(tt, I(Fraction(-5, 86400), Fraction(5, 86400)))
    assert not bounds.source_and_constants_attested
    assert not bounds.actual_phase_enclosed
    for seconds in (-4.99, 0, 4.99):
        epoch = tt + seconds / 86400
        actual = precession_matrix(epoch)
        mean = mat_mul(rot_x_axis(mean_obliquity(epoch) * DEG2RAD), actual)
        for boxes, values in ((bounds.precession_matrix, actual), (bounds.mean_matrix, mean)):
            assert all(box.contains(value) for row_boxes, row in zip(boxes, values)
                       for box, value in zip(row_boxes, row))
        strict = strict_vondrak_precession_matrix(epoch)
        assert all(box.contains(value) for row_boxes, row in zip(bounds.precession_matrix, strict)
                   for box, value in zip(row_boxes, row))


@pytest.mark.parametrize("centuries", [-201, -50, 0, 50, 201])
def test_vondrak_outside_branch_and_domain_is_unavailable(centuries):
    tt = 2451545.0 + centuries * 36525.0
    with pytest.raises(EnclosureUnavailable):
        bound_vondrak_mean_ecliptic_pole(tt, I.point(0))


@pytest.mark.parametrize("centuries", [-50, 50])
def test_crossing_precession_branch_is_unavailable(centuries):
    tt = 2451545.0 + centuries * 36525.0
    with pytest.raises(EnclosureUnavailable, match="branch"):
        bound_vondrak_mean_ecliptic_pole(tt, I(-1, 1))
