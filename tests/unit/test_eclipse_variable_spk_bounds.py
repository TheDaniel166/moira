"""Two varying TDB inputs retain their native operation order."""
import math
from dataclasses import replace
from fractions import Fraction

import pytest

from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_spk_bounds import EclipseSpkBoundsUnavailable
from moira._eclipse_native_spk_bounds import _coverage_class, _coverage_signs, _native_record_argument
from moira._eclipse_variable_spk_bounds import (
    _round_nearest_even, conditional_variable_anchor_type2_bounds, guarded_variable_scalar_snapshot_evaluate,
)


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("anchor", [1026285.7107341307, 2451545.25, 2460409.262])
@pytest.mark.parametrize("pair", [(0, 3), (0, 10), (3, 301), (3, 399)])
@pytest.mark.parametrize("offsets", [(-.0002, -.0001), (0., 0.)])
def test_variable_parts_enclose_actual_native_samples(planetary_reader, anchor, pair, offsets):
    lower = math.nextafter(anchor, -math.inf)
    upper = math.nextafter(anchor, math.inf)
    bound = conditional_variable_anchor_type2_bounds(planetary_reader, *pair, I(lower, upper), I(*offsets))
    for jd in (lower, anchor, upper):
        if offsets == (0., 0.):
            single_position = planetary_reader.position_tdb(*pair, jd)
            single_state = planetary_reader.position_and_velocity_tdb(*pair, jd)
            assert all(box.contains(value) for box, value in zip(bound.position_km, single_position))
            assert all(box.contains(value) for box, value in zip(bound.position_km, single_state[0]))
            assert all(box.contains(value) for box, value in zip(bound.velocity_km_per_day, single_state[1]))
        for offset in (offsets[0], sum(offsets) / 2, offsets[1]):
            position, velocity = planetary_reader._position_and_velocity_tdb_offset(*pair, jd, offset)
            assert all(box.contains(value) for box, value in zip(bound.position_km, position))
            assert all(box.contains(value) for box, value in zip(bound.velocity_km_per_day, velocity))
            result = guarded_variable_scalar_snapshot_evaluate(bound, jd, offset)
            assert all(abs(value - reference) < 1e-6 for value, reference in zip(result.position_km, position))
    assert not bound.native_environment_attested
    assert not bound.loaded_image_verified
    assert not bound.legacy_mapped_evaluator_certified


@pytest.mark.requires_ephemeris
def test_anchor_day_or_split_day_boundary_is_unavailable(planetary_reader):
    with pytest.raises(EclipseSpkBoundsUnavailable, match="anchor day"):
        conditional_variable_anchor_type2_bounds(planetary_reader, 0, 3, I(2451544.99, 2451545.01), I.point(0))
    with pytest.raises(EclipseSpkBoundsUnavailable, match="split day"):
        conditional_variable_anchor_type2_bounds(planetary_reader, 0, 3, I.point(2451545.25), I(-.001, .001))


@pytest.mark.requires_ephemeris
def test_variable_snapshot_tampering_and_outside_domain_fail(planetary_reader):
    bounds = conditional_variable_anchor_type2_bounds(planetary_reader, 0, 3, I(2451545.2, 2451545.3), I(-.001, -.0001))
    with pytest.raises(ValueError, match="outside"):
        guarded_variable_scalar_snapshot_evaluate(bounds, 2451545.4, -.0005)
    with pytest.raises(ValueError, match="identity"):
        guarded_variable_scalar_snapshot_evaluate(replace(bounds, anchor_days=I(2451545.2, 2451545.4)), 2451545.25, -.0005)


def test_variable_anchor_descriptor_and_record_seams_fail_closed():
    py_start, py_end, native_start, native_end = _coverage_signs(0., 86400., I(2451545.0, 2451545.001), I.point(0))
    assert _coverage_class(py_start, py_end) == "unknown"
    assert _coverage_class(native_start, native_end) == "inside"
    with pytest.raises(EclipseSpkBoundsUnavailable, match="record carry"):
        _native_record_argument(I(2451545.4999, 2451545.5001), I.point(.5), 0., 86400., 2)


def test_negative_large_anchor_descriptor_coverage_is_bounded():
    py_start, py_end, native_start, native_end = _coverage_signs(
        -4e11, -1e11, I(-1000000.25, -1000000.24), I.point(.1),
    )
    assert _coverage_class(py_start, py_end) == "inside"
    assert _coverage_class(native_start, native_end) == "inside"


@pytest.mark.parametrize("sign", [-1, 1])
def test_exact_binary64_ties_round_to_even_including_subnormals(sign):
    half_ulp = Fraction(1, 2**53)
    assert _round_nearest_even(sign * (1 + half_ulp)) == sign
    tiny = Fraction(1, 2**1074)
    assert _round_nearest_even(sign * tiny / 2) == 0
    assert _round_nearest_even(sign * 3 * tiny / 2) == sign * 2 * tiny
