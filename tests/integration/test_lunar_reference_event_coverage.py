"""Independent Taylor witnesses and joint whole-neighborhood coverage."""
from decimal import Decimal, localcontext
from fractions import Fraction as F

import pytest

from moira._eclipse_continuous_lunar import (build_continuous_lunar_reference,
    certify_continuous_sun_light_time, enclose_continuous_lunar_reference,
    verify_continuous_lunar_record_words)
from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_lunar_acceleration import bound_lunar_reference_accelerations
from moira._eclipse_lunar_event_reference import _taylor_vectors, isolate_lunar_reference_event
from moira._eclipse_reference_clock import bound_continuous_reference_tdb
from moira._eclipse_spk_bounds import _raw_seconds
from tests.unit.test_eclipse_continuous_lunar import _decimal_model


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize('anchor', [1248813.457560655, 2459891.96, 2688456.25])
def test_taylor_boxes_include_independent_raw_decimal_vectors_and_rates(planetary_reader, anchor):
    domain = I(F(-5, 86400), F(5, 86400))
    model = build_continuous_lunar_reference(planetary_reader, anchor, domain)
    acceleration = bound_lunar_reference_accelerations(model)
    center = enclose_continuous_lunar_reference(model, I.point(0))
    boxes = _taylor_vectors(center, domain, acceleration)
    with localcontext() as context:
        context.prec = 100
        h = Decimal('1e-12')
        for offset in (domain.lo, F(0), domain.hi):
            time = Decimal.from_float(anchor)+Decimal(offset.numerator)/Decimal(offset.denominator)
            point = _decimal_model(model, time)
            left, right = _decimal_model(model, time-h), _decimal_model(model, time+h)
            for values, rates, actual, before, after in zip(
                (boxes.sun_geocentric_km, boxes.moon_geocentric_km),
                (boxes.sun_derivative_km_per_tt_day, boxes.moon_derivative_km_per_tt_day),
                point, left, right):
                assert all(value.contains(F(x)) for value, x in zip(values, actual))
                assert all(rate.contains(F((b-a)/(2*h))) for rate, a, b in zip(rates, before, after))


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize('policy', ['danjon_angular', 'static_finite_cone'])
def test_joint_2022_event_has_all_contacts_and_distinct_extrema(planetary_reader, policy,
                                                             record_testsuite_property):
    domain = I(F(-3, 10), F(3, 10))
    model = verify_continuous_lunar_record_words(planetary_reader,
        build_continuous_lunar_reference(planetary_reader, 2459891.96, domain))
    result = isolate_lunar_reference_event(model, domain, policy=policy,
        tolerance=F(1, 864000), max_vector_evaluations=1500)
    assert result.complete and len(result.partitions) == 8
    record_testsuite_property(policy+'_joint_event_vector_evaluations', result.vector_evaluations)
    stationary = []
    for part in result.partitions:
        assert part.resolution_reached
        assert part.cells[0].interval.lo == domain.lo and part.cells[-1].interval.hi == domain.hi
        assert all(a.interval.hi == b.interval.lo for a, b in zip(part.cells, part.cells[1:]))
        roots = [cell for cell in part.cells if cell.status == 'unique']
        assert len(roots) == (2 if part.kind == 'contact' else 1)
        if part.kind == 'stationary':
            stationary.append(roots[0].interval)
    assert stationary[0].intersect(stationary[1]) is None
    assert not result.serving_evaluator_enclosed and not result.physical_accuracy_certified


@pytest.mark.requires_ephemeris
def test_reception_moon_route_does_not_require_the_sun_emission_record(planetary_reader):
    anchor = 2459892.505
    # The geometric Moon stays after its 2459892.5 record seam. Only the
    # retarded Sun uses the earlier horizon, which crosses that Moon seam.
    domain = I(0, F(1, 1000))
    model = verify_continuous_lunar_record_words(planetary_reader,
        build_continuous_lunar_reference(planetary_reader, anchor, domain))
    assert len(model.records) == 4
    moon_record = next(record for record in model.records if (record.center,record.target)==(3,301))
    earlier = bound_continuous_reference_tdb(anchor,
        I(domain.lo-model.max_light_delay_days,domain.hi))
    assert (_raw_seconds(anchor,earlier.tdb_offset_days).lo < moon_record.record_start_seconds
            < moon_record.source.interval_seconds_tdb.lo)
    bounds = enclose_continuous_lunar_reference(model, domain)
    acceleration = bound_lunar_reference_accelerations(model)
    lighttime = certify_continuous_sun_light_time(model, domain)
    assert acceleration.domain == domain and lighttime.continuous_fixed_point_unique
    with localcontext() as context:
        context.prec = 100
        for offset in (domain.lo, domain.midpoint, domain.hi):
            time = Decimal.from_float(anchor)+Decimal(offset.numerator)/Decimal(offset.denominator)
            sun, moon = _decimal_model(model, time)
            assert all(box.contains(F(value)) for box,value in zip(bounds.sun_geocentric_km,sun))
            assert all(box.contains(F(value)) for box,value in zip(bounds.moon_geocentric_km,moon))
