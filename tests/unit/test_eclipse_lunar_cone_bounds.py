"""Conditional finite-cone margin bounds and serving-vector witnesses."""
from fractions import Fraction
import math
import random

import pytest

from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_interval_roots import EnclosureUnavailable
from moira._eclipse_lunar_cone_bounds import (
    _hypot_box, bound_conditional_lunar_cone_serving_margin, bound_lunar_cone_penumbral_margin,
)
from moira._eclipse_serving_astro import evaluate_lunar_snapshot_with_serving_kernel
from moira.eclipse import _eclipse_body_pair
from moira.lunar_shadow_models import spherical_cone_shadow


def _points(vector):
    return tuple(I.point(x) for x in vector)


@pytest.mark.parametrize("value", [2.0**-20, 2.0**20])
@pytest.mark.parametrize("sign", [-1, 1])
def test_hypot_one_ulp_enclosure_covers_both_sides_of_binade(value, sign):
    result = _hypot_box(_points((sign * value, 0.0, 0.0)))
    below = math.nextafter(math.nextafter(value, -math.inf), -math.inf)
    above = math.nextafter(value, math.inf)
    assert result.contains(below)
    assert result.contains(above)


@pytest.mark.parametrize("sun,moon,scale", [
    ((150000000.0, 0.0, 0.0), (-384000.0, 0.0, 0.0), 1.0),
    ((150000000.0, 0.0, 0.0), (-384000.0, 8000.0, 0.0), 1.0),
    ((150000000.0, 0.0, 0.0), (-384000.0, 12000.0, 0.0), 1.0),
    ((150000000.0, 0.0, 0.0), (-384000.0, 9000.0, 12.0), 1.01),
])
def test_point_bounds_include_actual_finite_cone_margin(sun, moon, scale):
    result = bound_lunar_cone_penumbral_margin(_points(sun), _points(moon), earth_radius_scale=scale)
    actual = spherical_cone_shadow(sun, moon, earth_radius_scale=scale)
    assert result.penumbral_margin_km.contains(actual.penumbral_margin)
    assert result.umbral_margin_km.contains(actual.umbral_margin)
    assert result.total_margin_km.contains(actual.total_margin)
    assert result.axis_distance_km.contains(actual.axis_distance_km)
    assert not result.arithmetic_environment_attested
    assert not result.eclipse_classification_certified
    assert not result.event_search_complete
    assert result.geometry_total_for_vector_box_under_premises
    assert not result.successful_full_cone_evaluation_required


def test_vector_boxes_enclose_sampled_serving_cone_values():
    rng = random.Random(137)
    sun = (I(149999990, 150000010), I(-10, 10), I(-10, 10))
    moon = (I(-384010, -383990), I(8000, 8020), I(-10, 10))
    bound = bound_lunar_cone_penumbral_margin(sun, moon)
    for _ in range(30):
        s = tuple(rng.uniform(float(v.lo), float(v.hi)) for v in sun)
        m = tuple(rng.uniform(float(v.lo), float(v.hi)) for v in moon)
        actual = spherical_cone_shadow(s, m)
        assert bound.penumbral_margin_km.contains(actual.penumbral_margin)
        assert bound.umbral_margin_km.contains(actual.umbral_margin)
        assert bound.total_margin_km.contains(actual.total_margin)
        assert bound.axis_distance_km.contains(actual.axis_distance_km)


@pytest.mark.parametrize("distance,branch", [(384000.0, "positive"), (2000000.0, "apex")])
def test_complete_geometry_handles_both_umbral_nappe_branches(distance, branch):
    sun, moon = (150000000.0, 0.0, 0.0), (-distance, 0.0, 0.0)
    result = bound_lunar_cone_penumbral_margin(_points(sun), _points(moon))
    actual = spherical_cone_shadow(sun, moon)
    assert result.umbral_nappe_branch == branch
    assert result.penumbral_margin_km.contains(actual.penumbral_margin)
    assert result.umbral_margin_km.contains(actual.umbral_margin)
    assert result.total_margin_km.contains(actual.total_margin)


def test_ambiguous_umbral_branch_and_overflow_fail_closed():
    sun = _points((150000000.0, 0.0, 0.0))
    with pytest.raises(EnclosureUnavailable, match="umbral cone nappe"):
        bound_lunar_cone_penumbral_margin(sun, (I(-2000000, -1000000), I.point(0), I.point(0)))
    with pytest.raises(EnclosureUnavailable):
        bound_lunar_cone_penumbral_margin(_points((1.7e308, 1.7e308, 0)), _points((-384000, 0, 0)))


def test_near_tangency_box_remains_ambiguous():
    sun = (150000000.0, 0.0, 0.0)
    low, high = 0.0, 15000.0
    for _ in range(50):
        middle = (low + high) / 2
        if spherical_cone_shadow(sun, (-384000.0, middle, 0.0)).penumbral_margin > 0:
            low = middle
        else:
            high = middle
    result = bound_lunar_cone_penumbral_margin(
        _points(sun), (I.point(-384000.0), I(low, high), I.point(0)),
    )
    assert result.penumbral_margin_km.contains_zero
    assert not result.eclipse_classification_certified
    for y in (math.nextafter(low, -math.inf), low, high, math.nextafter(high, math.inf)):
        moon = (-384000.0, y, 0.0)
        point = bound_lunar_cone_penumbral_margin(_points(sun), _points(moon))
        assert point.penumbral_margin_km.contains(spherical_cone_shadow(sun, moon).penumbral_margin)


def test_ambiguous_or_invalid_domains_do_not_produce_a_bound():
    with pytest.raises(EnclosureUnavailable):
        bound_lunar_cone_penumbral_margin(_points((150000000, 0, 0)), _points((384000, 0, 0)))
    with pytest.raises(EnclosureUnavailable):
        bound_lunar_cone_penumbral_margin(_points((0, 0, 0)), _points((-384000, 0, 0)))
    with pytest.raises(EnclosureUnavailable):
        bound_lunar_cone_penumbral_margin(_points((150000000, 0, 0)),
                                          (I(-384000, 384000), I.point(0), I.point(0)))
    with pytest.raises(ValueError):
        bound_lunar_cone_penumbral_margin(_points((150000000, 0, 0)), _points((-384000, 0, 0)),
                                          earth_radius_scale=float("nan"))


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("tt", [2459891.96, 2460394.796])
def test_conditional_split_de441_bounds_cover_actual_cone_margin(planetary_reader, tt):
    domain = I(Fraction(-5, 86400), Fraction(5, 86400))
    result = bound_conditional_lunar_cone_serving_margin(planetary_reader, tt, domain)
    assert result.split_body_pair_route_required
    assert not result.legacy_fallback_enclosed
    assert not result.ut1_enclosed
    assert not result.eclipse_classification_certified
    for seconds in (-4, 0, 4):
        epoch = tt + seconds / 86400
        sun, moon = _eclipse_body_pair(epoch, planetary_reader, sun_retarded=True, moon_retarded=False)
        try:
            actual = spherical_cone_shadow(sun, moon)
        except ValueError:
            # The finite-cone public function has no defined penumbral result
            # on the sunward side. Such a span must be unavailable, not used
            # to prove anything about an eclipse.
            pytest.fail("expected a successful downstream cone sample")
        assert result.cone.penumbral_margin_km.contains(actual.penumbral_margin)


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("tt", [2459891.96, 2460394.796])
def test_bounded_records_drive_complete_serving_cone_samples(planetary_reader, tt):
    """Exercise one record-bound route through all finite-cone margins.

    These point witnesses do not prove route totality or absence between samples.
    """
    domain = I(Fraction(-5, 86400), Fraction(5, 86400))
    result = bound_conditional_lunar_cone_serving_margin(planetary_reader, tt, domain)
    for seconds in (-4, 0, 4):
        sample_tt = tt + seconds / 86400
        relative = Fraction.from_float(sample_tt) - Fraction.from_float(tt)
        assert domain.contains(relative)
        sample = evaluate_lunar_snapshot_with_serving_kernel(planetary_reader, result.vectors, sample_tt)
        geometry = spherical_cone_shadow(sample.sun_retarded_km, sample.moon_geometric_km)
        assert result.cone.penumbral_margin_km.contains(geometry.penumbral_margin)
        assert result.cone.umbral_margin_km.contains(geometry.umbral_margin)
        assert result.cone.total_margin_km.contains(geometry.total_margin)
        assert not sample.source_and_kernel_attested
        assert not sample.complete_search_certified
    assert not result.eclipse_classification_certified


@pytest.mark.requires_ephemeris
def test_route_budget_exhaustion_never_returns_a_margin(planetary_reader):
    with pytest.raises(EnclosureUnavailable, match="budget"):
        bound_conditional_lunar_cone_serving_margin(
            planetary_reader, 2459891.96, I.point(0), max_route_calls=1,
        )


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("tt,scale,half_seconds", [
    # Same lunation as the separate 13.9-second native-contact control; the
    # finite-cone policy need not agree with the native model's classification.
    (1248813.457560655, 1.01, 1),
    (2459892.26, 1.0, 100),
])
def test_serving_bounds_cover_grazing_control_and_negative_window(planetary_reader, tt, scale, half_seconds):
    half = Fraction(half_seconds, 86400)
    result = bound_conditional_lunar_cone_serving_margin(
        planetary_reader, tt, I(-half, half), earth_radius_scale=scale,
    )
    for seconds in (-half_seconds, 0, half_seconds):
        sample_tt = tt + seconds / 86400
        assert I(-half, half).contains(Fraction.from_float(sample_tt) - Fraction.from_float(tt))
        sun, moon = _eclipse_body_pair(sample_tt, planetary_reader, sun_retarded=True, moon_retarded=False)
        margin = spherical_cone_shadow(sun, moon, earth_radius_scale=scale).penumbral_margin
        assert result.cone.penumbral_margin_km.contains(margin)
    if tt == 2459892.26:
        assert result.cone.penumbral_margin_km.hi < 0
    assert not result.eclipse_classification_certified


@pytest.mark.requires_ephemeris
def test_tight_norm_opt_in_encloses_serving_sample_and_reduces_uncertainty(planetary_reader):
    tt = 1248813.457560655
    ordinary = bound_conditional_lunar_cone_serving_margin(
        planetary_reader, tt, I.point(0), earth_radius_scale=1.01,
    )
    tight = bound_conditional_lunar_cone_serving_margin(
        planetary_reader, tt, I.point(0), earth_radius_scale=1.01, tight_norm=True,
    )
    assert not ordinary.vectors.tight_norm_assumptions_required
    assert tight.vectors.tight_norm_assumptions_required
    sun, moon = _eclipse_body_pair(tt, planetary_reader, sun_retarded=True, moon_retarded=False)
    margin = spherical_cone_shadow(sun, moon, earth_radius_scale=1.01).penumbral_margin
    assert tight.cone.penumbral_margin_km.contains(margin)
    assert tight.cone.penumbral_margin_km.width < ordinary.cone.penumbral_margin_km.width
