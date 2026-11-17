"""Conditional ERA enclosures against Moira's native and Python routes.

These checks verify represented UT1 outputs at sampled dates. They do not
attest the execution environment or establish GAST, ITRF or eclipse geometry.
"""
from fractions import Fraction
import math
import random

import pytest

from moira import julian, moira_native
from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_native_spk_bounds import _rounded
from moira._eclipse_wgs84_orientation import (
    EclipseWgs84OrientationUnavailable,
    bound_conditional_earth_rotation_angle,
)


@pytest.mark.parametrize("anchor", [
    -1200954.75, 0.0, 1026285.7107341307, 2457754.5,
    2460409.263, 2688456.25, 6104045.25,
])
def test_interval_encloses_python_and_native_era(anchor):
    offsets = I(Fraction(-5, 86400), Fraction(5, 86400))
    evidence = bound_conditional_earth_rotation_angle(anchor, offsets, assume_ieee_arithmetic=True)
    assert not evidence.source_and_arithmetic_attested
    assert not evidence.gast_enclosed
    assert not evidence.nutation_precession_or_polar_motion_enclosed
    assert not evidence.earth_fixed_shadow_certified
    rng = random.Random(int(anchor * 1024))
    samples = [anchor + seconds / 86400 for seconds in (-4, 0, 4)]
    samples.extend(anchor + rng.uniform(-4.5, 4.5) / 86400 for _ in range(30))
    samples.extend((math.nextafter(anchor, -math.inf), math.nextafter(anchor, math.inf)))
    for sample in samples:
        assert offsets.contains(Fraction.from_float(sample) - Fraction.from_float(anchor))
        assert evidence.angle_degrees.contains(julian.earth_rotation_angle.__wrapped__(sample))
        assert evidence.angle_degrees.contains(moira_native.earth_rotation_angle(sample))


def test_integer_day_and_modulo_seams_are_unresolved():
    with pytest.raises(EclipseWgs84OrientationUnavailable, match="integer-day"):
        bound_conditional_earth_rotation_angle(2451545.0, I(Fraction(-1, 86400), Fraction(1, 86400)),
                                               assume_ieee_arithmetic=True)
    with pytest.raises(EclipseWgs84OrientationUnavailable, match="integer-day"):
        bound_conditional_earth_rotation_angle(-1.0, I(Fraction(-1, 86400), Fraction(1, 86400)),
                                               assume_ieee_arithmetic=True)
    wrap = 2451545.0 + (1.0 - 0.7790572732640) / 1.00273781191135448
    with pytest.raises(EclipseWgs84OrientationUnavailable, match="modulo"):
        bound_conditional_earth_rotation_angle(wrap, I(Fraction(-10, 86400), Fraction(10, 86400)),
                                               assume_ieee_arithmetic=True)


def test_missing_premise_and_unsupported_domains_fail_closed():
    with pytest.raises(EclipseWgs84OrientationUnavailable, match="premise"):
        bound_conditional_earth_rotation_angle(2451545.5, I.point(0))
    with pytest.raises(TypeError, match="boolean"):
        bound_conditional_earth_rotation_angle(2451545.5, I.point(0), assume_ieee_arithmetic=1)
    with pytest.raises(EclipseWgs84OrientationUnavailable, match="domain"):
        bound_conditional_earth_rotation_angle(40000000.0, I(0, 1), assume_ieee_arithmetic=True)
    with pytest.raises(ValueError, match="finite"):
        bound_conditional_earth_rotation_angle(float("nan"), I.point(0), assume_ieee_arithmetic=True)


def test_negative_tiny_modulo_may_round_to_one():
    value = math.nextafter(0.0, -math.inf)
    python_remainder = value % 1.0
    native_floor_form = value - math.floor(value)
    assert python_remainder == native_floor_form == 1.0
    enclosed = _rounded(I.point(value) - I.point(math.floor(value)))
    assert enclosed.contains(python_remainder)
