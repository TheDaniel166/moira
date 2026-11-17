"""Independent curvature witnesses and distinct stationary-objective covers."""
from decimal import Decimal, localcontext
from fractions import Fraction as F
from types import SimpleNamespace

import pytest

from moira import _eclipse_lunar_extrema as extrema
from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_lunar_acceleration import LunarReferenceAccelerationBounds
from tests.unit.test_eclipse_continuous_lunar_contacts import _affine, _decimal_margins as cone_margins
from tests.unit.test_eclipse_angular_contacts import _asin, _atan


def _oracle(time, policy):
    radial = (time*time+Decimal(1)/9).sqrt()
    theta = _atan(radial/10)
    if policy == 'static_finite_cone':
        margins = cone_margins(time, sun_rate=0, z=10, z_rate=0, y=F(1, 3))
    else:
        distance = (time*time+Decimal(1)/9+100).sqrt()
        base = Decimal.from_float(1.01)*_asin(Decimal(2)/distance)+_asin(Decimal('0.1'))
        alpha, solar = _asin(Decimal('0.5')/distance), _asin(Decimal('0.2'))
        margins = base+solar+alpha-theta, base-solar+alpha-theta, base-solar-alpha-theta
    return radial, theta, *margins


@pytest.mark.parametrize('policy', ['danjon_angular', 'static_finite_cone'])
@pytest.mark.parametrize('time', [F(-1), F(1, 2), F(2)])
def test_second_derivatives_enclose_independent_decimal_curvature(policy, time):
    domain = I(-3, 3)
    acceleration = LunarReferenceAccelerationBounds((F(0),)*3, (F(0),)*3, domain, F(20), F(0))
    vectors = _affine(I.point(time), y=F(1, 3))
    jets = extrema.bound_lunar_observable_jets(
        vectors, acceleration, policy=policy, earth_radius_km=2, sun_radius_km=4,
        moon_radius_km=F(1, 2),
    )
    with localcontext() as context:
        context.prec = 110
        t = Decimal(time.numerator)/Decimal(time.denominator)
        h = Decimal('1e-22')
        center, left, right = _oracle(t, policy), _oracle(t-h, policy), _oracle(t+h, policy)
        for value, rate, curvature, middle, before, after in zip(
                jets.values, jets.rates, jets.curvatures, center, left, right):
            assert value.contains(F(middle))
            assert rate.contains(F((after-before)/(2*h)))
            assert curvature.contains(F((after-2*middle+before)/(h*h)))


@pytest.mark.parametrize('policy', ['danjon_angular', 'static_finite_cone'])
def test_smooth_synthetic_minima_and_overlap_maxima_are_not_interchanged(monkeypatch, policy):
    domain = I(-2, 2)
    model = SimpleNamespace(tt_offset_days=domain, precision_bits=128)
    acceleration = LunarReferenceAccelerationBounds((F(0),)*3, (F(0),)*3, domain, F(20), F(0))
    monkeypatch.setattr(extrema, 'bound_lunar_reference_accelerations', lambda model: acceleration)
    monkeypatch.setattr(extrema, 'enclose_continuous_lunar_reference',
                        lambda model, box: _affine(box, y=F(1, 3)))
    # The unit geometry is a true affine reference; radii are substituted in
    # the bound dependency, leaving the stationary solver unchanged.
    original = extrema.bound_lunar_observable_jets

    def geometry(vectors, acceleration, **kwargs):
        return original(vectors, acceleration, **(kwargs | dict(
            earth_radius_km=2, sun_radius_km=4, moon_radius_km=F(1, 2))))

    monkeypatch.setattr(extrema, 'bound_lunar_observable_jets', geometry)
    result = extrema.isolate_lunar_reference_extrema(
        model, domain, policy=policy, tolerance=F(1, 1000), max_evaluations=3000,
    )
    assert len(result.partitions) == 5
    for index, partition in enumerate(result.partitions):
        assert partition.complete
        roots = [cell for cell in partition.cells if cell.status == 'unique']
        assert roots and all(cell.interval.contains(0) for cell in roots)
        assert all((root.derivative.lo > 0 if index < 2 else root.derivative.hi < 0) for root in roots)
        assert partition.cells[0].interval.lo == -2 and partition.cells[-1].interval.hi == 2


def test_extrema_budget_keeps_the_entire_domain(monkeypatch):
    domain = I(-2, 2)
    model = SimpleNamespace(tt_offset_days=domain, precision_bits=128)
    acceleration = LunarReferenceAccelerationBounds((F(0),)*3, (F(0),)*3, domain, F(20), F(0))
    monkeypatch.setattr(extrema, 'bound_lunar_reference_accelerations', lambda model: acceleration)
    result = extrema.isolate_lunar_reference_extrema(model, domain, policy='danjon_angular',
                                                   tolerance=F(1, 100), max_evaluations=0)
    assert result.evaluations == 0
    assert all(not part.complete and part.cells[0].interval == domain for part in result.partitions)
