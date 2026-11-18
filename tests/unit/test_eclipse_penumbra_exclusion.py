"""Independent sphere/ellipsoid controls for the separating-plane proof."""

from dataclasses import replace
from fractions import Fraction
import math

from pytest import approx

from moira import _eclipse_interval_jets as j
from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_penumbra_exclusion import cover_penumbra_exclusion, penumbral_plane_gap
from moira._eclipse_solar_frame import SolarFrameBounds


def _frame(domain, y, z):
    rotation = tuple(tuple(j.constant(int(i == k)) for k in range(3)) for i in range(3))
    return SolarFrameBounds(domain, tuple(j.constant(c) for c in (150000000, 0, 0)),
                            tuple(j.constant(c) for c in (390000, y, z)), rotation, True)


def test_separates_all_earth_on_full_domain_and_bounds_the_support_gap():
    domain = I(-1, 1)
    frame = _frame(domain, 10000, 0)
    assert penumbral_plane_gap(frame)[0].lo > 0
    result = cover_penumbra_exclusion(domain, lambda box: replace(frame, domain=box))
    assert result.absence_proved and result.evaluations == 1
    assert result.cells[0].patch is None and result.cells[0].time == domain

    # In this exact 2D geometry the independently derived lower outer
    # tangent normal rotates from the centre-line bearing by asin(r/D).
    alpha = math.atan2(10000, 149610000)
    sine = (696340 + 1737.4) / math.hypot(149610000, 10000)
    angle = math.asin(sine) - alpha
    expected = 10000 * math.cos(angle) - 390000 * math.sin(angle) - 1737.4 - 6378.137
    value = result.cells[0].slack
    assert float(value.lo) == approx(expected, abs=1e-9)


def test_uses_oblate_support_and_retains_unknown_when_the_plane_cannot_exclude():
    domain = I.point(0)
    frame = _frame(domain, 0, 9950)
    sphere = penumbral_plane_gap(frame, polar=6378.137)[0]
    oblate = penumbral_plane_gap(frame)[0]
    assert oblate.lo > sphere.hi
    unknown = cover_penumbra_exclusion(domain, lambda box: _frame(box, 6000, 0))
    assert not unknown.absence_proved
    assert unknown.unresolved[0].slack.hi < 0
    exhausted = cover_penumbra_exclusion(I(-2, 3), lambda box: _frame(box, 6000, 0),
                                        max_evaluations=0, minimum_width=Fraction(1, 86400))
    assert exhausted.cells[0].time == I(-2, 3) and exhausted.unresolved
