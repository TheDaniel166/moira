"""Conditional Earth-fixed shadow vector bounds and source-order controls."""
from fractions import Fraction
import math

import pytest

from moira._eclipse_earth_fixed_bounds import (
    EclipseEarthFixedBoundsUnavailable,
    _cross,
    _dot,
    _matmul,
    _unit,
    bound_conditional_earth_fixed_solar_vectors,
)
from moira._eclipse_interval import RationalInterval as I
from moira.eclipse import EclipseCalculator, _earth_fixed_solar_shadow


_PREMISES = {
    "assume_ieee_arithmetic": True,
    "assume_correctly_rounded_integer_powers": True,
    "assume_finite_unit_trig_within_one_ulp": True,
    "assume_registered_nutation_tables_match": True,
    "assume_builtin_sum_error": True,
    "assume_correctly_rounded_sqrt": True,
}


def _points(*values):
    return tuple(I.point(value) for value in values)


def test_exact_analytic_vector_and_matrix_controls():
    x, y, z = _points(1, 0, 0), _points(0, 1, 0), _points(0, 0, 1)
    assert all(box.contains(value) for box, value in zip(_cross(x, y), (0, 0, 1)))
    assert _dot(x, y).contains(0)
    identity = (x, y, z)
    assert all(_matmul(identity, identity)[i][j].contains(int(i == j))
               for i in range(3) for j in range(3))
    assert all(box.contains(value) for box, value in zip(_unit(_points(3, 4, 0)), (0.6, 0.8, 0)))
    with pytest.raises(EclipseEarthFixedBoundsUnavailable, match="norm"):
        _unit(_points(0, 0, 0))
    with pytest.raises(EclipseEarthFixedBoundsUnavailable, match="norm"):
        _unit((I(-1, 1), I(-1, 1), I(-1, 1)))


def test_all_arithmetic_premises_must_be_explicit():
    with pytest.raises(EclipseEarthFixedBoundsUnavailable, match="premises"):
        bound_conditional_earth_fixed_solar_vectors(None, 2451545.0, I.point(0), 2451545.0, I.point(0))
    kwargs = dict(_PREMISES)
    kwargs["assume_ieee_arithmetic"] = 1
    with pytest.raises(TypeError):
        bound_conditional_earth_fixed_solar_vectors(None, 2451545.0, I.point(0), 2451545.0, I.point(0), **kwargs)


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("seed", [991000.0, 2457986.0, 2460409.0])
def test_de441_actual_shadow_vectors_are_enclosed_for_independent_time_pairs(planetary_reader, seed):
    """Exercise source frame order against represented BCE/modern samples.

    Sampling is a regression check, not a proof of physical eclipse accuracy,
    live source attestation, time conversion or complete event geometry.
    """
    calc = EclipseCalculator(reader=planetary_reader)
    ut = calc.next_solar_eclipse(seed).jd_ut
    tt = calc._jd_tt_from_ut(ut)
    span = I(Fraction(-2, 86400), Fraction(2, 86400))
    bound = bound_conditional_earth_fixed_solar_vectors(
        planetary_reader, ut, span, tt, span, **_PREMISES,
    )
    fields = (
        ("axis_unit_away_from_sun", "axis_unit_away_from_sun"),
        ("sun_xyz_itrf_km", "sun_xyz_from_earth_itrf_km"),
        ("fundamental_plane_point_xyz_km", "fundamental_plane_point_xyz_km"),
        ("fundamental_east_unit_itrf", "fundamental_east_unit_itrf"),
        ("fundamental_north_unit_itrf", "fundamental_north_unit_itrf"),
    )
    # Independent combinations deliberately exercise the Cartesian-domain
    # contract; the helper does not claim that TT derives from UT1.
    for actual_ut, actual_tt in ((ut, tt), (math.nextafter(ut, -math.inf), tt),
                                 (ut, math.nextafter(tt, math.inf))):
        assert span.contains(Fraction.from_float(actual_ut) - Fraction.from_float(ut))
        assert span.contains(Fraction.from_float(actual_tt) - Fraction.from_float(tt))
        actual = _earth_fixed_solar_shadow(calc, actual_ut, jd_tt=actual_tt)
        assert actual is not None
        for bound_field, actual_field in fields:
            assert all(box.contains(value) for box, value in
                       zip(getattr(bound, bound_field), getattr(actual, actual_field)))
    assert not bound.source_and_arithmetic_attested
    assert not bound.ut1_tt_correspondence_proved
    assert not bound.source_route_totality_proved
    assert not bound.eclipse_occurrence_certified
    assert not bound.event_wide_path_certified
    assert not bound.physical_accuracy_certified
