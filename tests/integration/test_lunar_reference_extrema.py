"""Independent DE441 curvature controls and separate reference extrema."""
from decimal import Decimal, localcontext
from fractions import Fraction as F

import pytest

from moira._eclipse_continuous_lunar import (build_continuous_lunar_reference,
                                            verify_continuous_lunar_record_words)
from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_lunar_acceleration import bound_lunar_reference_accelerations
from moira._eclipse_lunar_extrema import isolate_lunar_reference_extrema
from tests.unit.test_eclipse_continuous_lunar import _decimal_model


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize('anchor', [1248813.457560655, 2459891.96, 2688456.25])
def test_acceleration_bounds_enclose_independent_raw_decimal_samples(planetary_reader, anchor):
    model = build_continuous_lunar_reference(planetary_reader, anchor, I(F(-5, 86400), F(5, 86400)))
    bound = bound_lunar_reference_accelerations(model)
    assert bound.sun_distance_lower_km > 0
    assert not bound.serving_evaluator_enclosed
    with localcontext() as context:
        context.prec = 100
        t, h = Decimal.from_float(anchor), Decimal('1e-10')
        middle, left, right = _decimal_model(model, t), _decimal_model(model, t-h), _decimal_model(model, t+h)
        for bounded, before, center, after in zip((bound.sun, bound.moon), left, middle, right):
            for upper, x, y, z in zip(bounded, before, center, after):
                actual = abs((z-2*y+x)/(h*h))
                assert F(actual) <= upper


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize('policy', ['danjon_angular', 'static_finite_cone'])
def test_2022_objectives_have_separate_proved_reference_extrema(planetary_reader, policy,
                                                             record_testsuite_property):
    domain = I(F(-1, 12), F(1, 12))
    model = build_continuous_lunar_reference(planetary_reader, 2459891.96, domain)
    model = verify_continuous_lunar_record_words(planetary_reader, model)
    result = isolate_lunar_reference_extrema(
        model, domain, policy=policy, tolerance=F(1, 864000), max_evaluations=2000,
    )
    record_testsuite_property(policy+'_extrema_vector_calls', result.evaluations)
    assert len(result.partitions) == 5
    critical = []
    for index, partition in enumerate(result.partitions):
        assert partition.complete, [(cell.status, cell.reason) for cell in partition.cells
                                    if cell.status not in ('excluded', 'unique')][:5]
        assert partition.resolution_reached
        roots = [cell for cell in partition.cells if cell.status == 'unique']
        assert len(roots) == 1
        assert all((cell.derivative.lo > 0 if index < 2 else cell.derivative.hi < 0) for cell in roots)
        critical.append(roots[0].interval)
    # Axis minimum and angular opposition are different mathematical epochs.
    assert critical[0].intersect(critical[1]) is None
    assert not result.serving_evaluator_enclosed and not result.physical_accuracy_certified
