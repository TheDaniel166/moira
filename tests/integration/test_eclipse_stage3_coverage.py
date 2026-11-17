"""Real-resource checks with explicit reference/source acceptance boundaries."""
from fractions import Fraction as F

import pytest

from moira._eclipse_angular_contacts import isolate_continuous_angular_contacts
from moira._eclipse_continuous_lunar import build_continuous_lunar_reference
from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_lunar_coverage import cover_lunar_tt_reference
from moira._eclipse_solar_source_coverage import cover_conditional_solar_source, cover_native_solar_source
from moira.eclipse import _solve_solar_central_interval


PREMISES = {
    'assume_ieee_arithmetic': True,
    'assume_correctly_rounded_integer_powers': True,
    'assume_finite_unit_trig_within_one_ulp': True,
    'assume_registered_nutation_tables_match': True,
    'assume_builtin_sum_error': True,
    'assume_correctly_rounded_sqrt': True,
}


@pytest.mark.requires_ephemeris
def test_complete_month_cover_does_not_assume_full_moon_neighbourhood(planetary_reader):
    anchor = 2459891.96
    domain = I(-16, 18)
    result = cover_lunar_tt_reference(
        planetary_reader, anchor, domain, policy='danjon_angular',
        tolerance=F(1, 24), max_evaluations=512,
    )
    assert result.domain_covered and result.evaluations <= 512
    assert result.cells[0].domain.lo == -16 and result.cells[-1].domain.hi == 18
    assert all(a.domain.hi == b.domain.lo for a, b in zip(result.cells, result.cells[1:]))
    assert any(cell.status == 'overlap' and cell.domain.contains(0) for cell in result.cells)
    # The independently specified new-moon epoch is far outside the old
    # +/-event window, and must be explicitly covered by an exclusion.
    new_offset = F.from_float(2459907.46)-F.from_float(anchor)
    new_cells = [cell for cell in result.cells if cell.domain.contains(new_offset)]
    assert new_cells and all(cell.status == 'excluded' for cell in new_cells)
    # Every non-excluded region in this particular complete month lies in
    # the separately tested eight-hour reference contact domain. This is a
    # complementary-domain check, not an assumption that a full-moon window
    # contains all events for every requested interval or policy.
    assert all(cell.status == 'excluded' or
               (F(-1, 6) <= cell.domain.lo <= cell.domain.hi <= F(1, 6))
               for cell in result.cells)
    assert not result.eclipse_absence_certified and not result.serving_route_totality_proved


@pytest.mark.requires_ephemeris
def test_2022_angular_reference_isolates_all_six_contacts(planetary_reader, record_testsuite_property):
    domain = I(F(-1, 6), F(1, 6))
    model = build_continuous_lunar_reference(planetary_reader, 2459891.96, domain)
    result = isolate_continuous_angular_contacts(
        model, domain, tolerance=F(1, 864000), max_evaluations=2000,
    )
    assert result.margin_unit == 'rad' and result.model_policy == 'danjon_angular_reference'
    record_testsuite_property('angular_reference_callbacks', result.evaluations)
    record_testsuite_property('angular_reference_vectors', result.vector_evaluations)
    contacts = []
    for partition in (result.penumbral, result.umbral, result.total):
        assert partition.complete and partition.resolution_reached
        contacts.append([cell.interval for cell in partition.cells if cell.status == 'unique'])
        assert len(contacts[-1]) == 2
    assert contacts[0][0].hi < contacts[1][0].lo < contacts[2][0].lo
    assert contacts[2][1].hi < contacts[1][1].lo < contacts[0][1].lo
    assert not result.serving_evaluator_enclosed and not result.eclipse_absence_certified


@pytest.mark.requires_ephemeris
def test_de441_solar_point_does_not_manufacture_continuous_path_acceptance(eclipse_calculator):
    calc = eclipse_calculator
    ut = 2460054.678318233
    tt = calc._jd_tt_from_ut(ut)
    result = cover_conditional_solar_source(
        calc._reader, ut, I.point(0), tt_anchor_jd=tt,
        tt_enclosure=lambda box: I.point(0), tolerance=F(1, 86400000),
        arithmetic_premises=PREMISES, max_evaluations=8,
    )
    assert result.cells and result.evaluations <= 8
    assert result.subtype is None and not result.event_interval_enclosed
    assert not result.serving_route_totality_proved


def test_unattested_source_premises_stay_unresolved():
    result = cover_conditional_solar_source(
        None, 2451545., I.point(0), tt_anchor_jd=2451545.,
        tt_enclosure=lambda box: I.point(0), tolerance=F(1, 86400),
        arithmetic_premises={}, max_evaluations=1,
    )
    assert result.cells[0].kind == 'unresolved' and result.subtype is None
    assert 'premises' in result.cells[0].reason


@pytest.mark.requires_ephemeris
def test_native_clock_is_enclosed_without_silently_identifying_ut1_and_tt(eclipse_calculator):
    result = cover_native_solar_source(
        eclipse_calculator._reader, 2460054.678318233, I.point(0),
        tolerance=F(1, 86400000), arithmetic_premises=PREMISES,
        require_clock_totality=True, max_evaluations=8,
    )
    assert result.status == 'total_on_domain'
    assert result.subtype is None and not result.event_interval_enclosed
    assert not result.serving_route_totality_proved


@pytest.mark.requires_ephemeris
def test_minus_500_short_axis_interval_is_preserved_as_a_control(eclipse_calculator):
    # Fresh native solve for the historical 92-case fixture, not a proof that
    # no other axis component exists in a larger advertised time domain.
    left, right = _solve_solar_central_interval(eclipse_calculator, 1538582.2449649798)
    duration = (right.jd_ut-left.jd_ut)*86400
    assert 10 < duration < 12
