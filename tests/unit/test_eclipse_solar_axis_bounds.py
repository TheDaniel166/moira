"""Conditional solar-axis enclosures against the actual serving calculation.

DE441 samples are regression evidence under the stated float/source premises,
not a proof of runtime attestation or eclipse-search completeness.
"""
from fractions import Fraction
import math
import random
import sys

import pytest

from moira import eclipse
from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_interval_roots import EnclosureUnavailable
from moira._eclipse_solar_serving import (
    EclipseSolarServingUnavailable,
    _three_term_sum_enclosure,
    bound_conditional_solar_serving_axis,
    bound_solar_shadow_axis_from_vectors,
)


_ASSUMPTIONS = dict(assume_builtin_sum_error=True, assume_correctly_rounded_sqrt=True)


def _point_vector(vector):
    return tuple(I.point(value) for value in vector)


@pytest.mark.parametrize("terms", [
    (1.0e16, 1.0, -1.0e16),
    (-1.0e16, -1.0, 1.0e16),
    (2.0**-1022, -(2.0**-1022), 2.0**-1074),
])
def test_sum_bound_covers_builtin_without_assuming_sequential_rounding(terms):
    enclosure = _three_term_sum_enclosure(tuple(I.point(value) for value in terms))
    assert enclosure.contains(sum(terms))


def _source_state(monkeypatch, sun, moon):
    monkeypatch.setattr(eclipse, "_eclipse_body_pair", lambda *_args, **_kwargs: (sun, moon))
    calc = object.__new__(eclipse.EclipseCalculator)
    calc._reader = None
    return calc._native_solar_shadow_axis_state_tt(2451545.0)


def _assert_state_enclosed(bounds, state):
    assert bounds.sun_to_moon_norm_km.contains(state.sun_moon_distance_km)
    assert all(box.contains(value) for box, value in zip(bounds.axis_unit, state.axis_unit_away_from_sun))
    assert bounds.axis_projection_km.contains(state.axis_projection_km)
    if math.isinf(state.axis_distance_km):
        assert bounds.status == "away"
        assert bounds.axis_distance_km is None
    else:
        assert bounds.status == "forward"
        assert bounds.axis_distance_km.contains(state.axis_distance_km)


def test_arithmetic_premises_are_explicit_and_missing_premises_fail_closed():
    sun, moon = _point_vector((150000000.0, 0.0, 0.0)), _point_vector((384000.0, 100.0, 0.0))
    with pytest.raises(EclipseSolarServingUnavailable, match="premises"):
        bound_solar_shadow_axis_from_vectors(sun, moon)
    with pytest.raises(EclipseSolarServingUnavailable, match="premises"):
        bound_solar_shadow_axis_from_vectors(sun, moon, assume_builtin_sum_error=True)
    with pytest.raises(TypeError, match="booleans"):
        bound_solar_shadow_axis_from_vectors(sun, moon, assume_builtin_sum_error=1,
                                             assume_correctly_rounded_sqrt=True)


@pytest.mark.parametrize("sun,moon", [
    ((150000000.0, 0.0, 0.0), (384000.0, 100.0, 30.0)),
    ((-150000000.0, 0.0, 0.0), (384000.0, 100.0, 30.0)),
    ((1.0e8, 1.0e8, 0.0), (384000.0, 384000.0, 12.0)),
])
def test_forward_and_away_axis_boxes_enclose_actual_source(monkeypatch, sun, moon):
    state = _source_state(monkeypatch, sun, moon)
    result = bound_solar_shadow_axis_from_vectors(_point_vector(sun), _point_vector(moon), **_ASSUMPTIONS)
    _assert_state_enclosed(result, state)
    assert result.successful_shadow_state_required
    assert not result.source_and_arithmetic_attested
    assert not result.earth_orientation_enclosed
    assert not result.eclipse_occurrence_certified
    assert not result.physical_accuracy_certified


def test_axis_degeneracy_and_projection_crossing_fail_closed():
    same = _point_vector((1.0, 2.0, 3.0))
    with pytest.raises(EclipseSolarServingUnavailable, match="norm"):
        bound_solar_shadow_axis_from_vectors(same, same, **_ASSUMPTIONS)
    sun = _point_vector((150000000.0, 0.0, 0.0))
    moon = (I(-100, 100), I.point(0), I.point(0))
    with pytest.raises(EclipseSolarServingUnavailable, match="projection"):
        bound_solar_shadow_axis_from_vectors(sun, moon, **_ASSUMPTIONS)


def test_overflowing_vector_difference_is_unavailable():
    huge = sys.float_info.max
    sun = _point_vector((huge, 0.0, 0.0))
    moon = _point_vector((-huge, 0.0, 0.0))
    with pytest.raises(EnclosureUnavailable):
        bound_solar_shadow_axis_from_vectors(sun, moon, **_ASSUMPTIONS)


def test_wide_vector_boxes_enclose_sampled_actual_source(monkeypatch):
    sun_center = (150000000.0, 30000.0, -10000.0)
    moon_center = (384000.0, 150.0, -40.0)
    width = Fraction(1, 4)
    sun_box = tuple(I.point(value) + I(-width, width) for value in sun_center)
    moon_box = tuple(I.point(value) + I(-width, width) for value in moon_center)
    bounds = bound_solar_shadow_axis_from_vectors(sun_box, moon_box, **_ASSUMPTIONS)
    rng = random.Random(19761116)
    for _ in range(40):
        sun = tuple(value + rng.uniform(-0.24, 0.24) for value in sun_center)
        moon = tuple(value + rng.uniform(-0.24, 0.24) for value in moon_center)
        assert all(box.contains(value) for box, value in zip(sun_box, sun))
        assert all(box.contains(value) for box, value in zip(moon_box, moon))
        _assert_state_enclosed(bounds, _source_state(monkeypatch, sun, moon))


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("tt", [1026285.7107341307, 2460409.263, 2688456.25])
def test_de441_interval_encloses_real_serving_axis(planetary_reader, tt):
    offsets = I(Fraction(-5, 86400), Fraction(5, 86400))
    receipt = bound_conditional_solar_serving_axis(planetary_reader, tt, offsets, **_ASSUMPTIONS)
    assert len(receipt.vectors.spk_usages) == 34
    assert receipt.vectors.split_serving_route_required
    assert not receipt.route_totality_established
    assert not receipt.live_source_attested
    calc = eclipse.EclipseCalculator(reader=planetary_reader)
    for seconds in (-4, 0, 4):
        sample_tt = tt + seconds / 86400
        assert offsets.contains(Fraction.from_float(sample_tt) - Fraction.from_float(tt))
        _assert_state_enclosed(receipt.axis, calc._native_solar_shadow_axis_state_tt(sample_tt))
