"""Joint event coverage against independent polynomial observables."""
from fractions import Fraction as F
from dataclasses import replace

import pytest

import moira._eclipse_lunar_event_reference as subject
from moira._eclipse_continuous_lunar import ContinuousLunarReference
from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_interval_roots import EnclosureUnavailable
from moira._eclipse_lunar_extrema import LunarObservableJets
from moira._eclipse_lunar_acceleration import LunarReferenceAccelerationBounds
from tests.unit.test_eclipse_continuous_lunar_contacts import _affine


def _model():
    return ContinuousLunarReference(2451545., I(-1, 1), F(1, 100), 128, ())


def _polynomials(monkeypatch, *, tangent=False, unavailable=False):
    calls = []

    def vectors(model, box):
        calls.append(box)
        return box

    def jets(box, acceleration, **kwargs):
        if unavailable and box.contains_zero:
            raise EnclosureUnavailable('singular domain')
        shifts = (F(1, 17), F(1, 19), F(1, 23), F(1, 29), F(1, 31))
        values, rates, curvatures = [], [], []
        for index, shift in enumerate(shifts):
            offset = box-shift
            if index < 2:
                values.append(offset.square()+index+1)
                rates.append(2*offset)
                curvatures.append(I.point(2))
            else:
                height = F(0) if tangent and index == 2 else F(1, 4*index)
                values.append(height-offset.square())
                rates.append(-2*offset)
                curvatures.append(I.point(-2))
        return LunarObservableJets(box, (), tuple(values), tuple(rates), tuple(curvatures))

    monkeypatch.setattr(subject, 'bound_lunar_reference_accelerations', lambda model: None)
    monkeypatch.setattr(subject, 'enclose_continuous_lunar_reference', vectors)
    monkeypatch.setattr(subject, '_taylor_vectors', lambda anchor, box, acceleration: box)
    monkeypatch.setattr(subject, 'bound_lunar_observable_jets', jets)
    return calls


@pytest.mark.parametrize('policy', ['danjon_angular', 'static_finite_cone'])
def test_all_contacts_and_distinct_extrema_have_complete_complements(monkeypatch, policy):
    calls = _polynomials(monkeypatch)
    result = subject.isolate_lunar_reference_event(_model(), I(-1, 1), policy=policy,
        tolerance=F(1, 100000), max_vector_evaluations=1500)
    assert result.complete and len(result.partitions) == 8
    assert result.vector_evaluations == len(calls) == len(set(calls))
    for partition in result.partitions:
        assert partition.resolution_reached
        assert partition.root_function_unit == (partition.value_unit if partition.kind == 'contact'
                                                else partition.value_unit+' per TT day')
        assert partition.cells[0].interval.lo == -1 and partition.cells[-1].interval.hi == 1
        assert all(a.interval.hi == b.interval.lo for a, b in zip(partition.cells, partition.cells[1:]))
        roots = [cell for cell in partition.cells if cell.status == 'unique']
        assert len(roots) == (2 if partition.kind == 'contact' else 1)
    stationary = [part for part in result.partitions if part.kind == 'stationary']
    intervals = [next(cell.interval for cell in part.cells if cell.status == 'unique') for part in stationary]
    assert all(a.intersect(b) is None for i, a in enumerate(intervals) for b in intervals[i+1:])
    assert not result.serving_evaluator_enclosed and not result.physical_accuracy_certified


@pytest.mark.parametrize('budget', [0, 1, 12])
def test_one_budget_covers_all_eight_partitions(monkeypatch, budget):
    calls = _polynomials(monkeypatch)
    result = subject.isolate_lunar_reference_event(_model(), I(-1, 1), policy='danjon_angular',
        tolerance=F(1, 10000), max_vector_evaluations=budget)
    assert not result.complete and result.vector_evaluations == len(calls) == budget
    assert len(result.partitions) == 8
    assert all(part.cells[0].interval.lo == -1 and part.cells[-1].interval.hi == 1
               for part in result.partitions)


@pytest.mark.parametrize('mode', ['tangent', 'unavailable'])
def test_degenerate_or_unsupported_time_is_retained(monkeypatch, mode):
    _polynomials(monkeypatch, **{mode: True})
    result = subject.isolate_lunar_reference_event(_model(), I(-1, 1), policy='danjon_angular',
        tolerance=F(1, 1000), max_vector_evaluations=2000)
    assert not result.complete
    assert any(cell.status not in ('excluded', 'unique') for part in result.partitions for cell in part.cells)


def test_acceleration_failure_covers_every_objective(monkeypatch):
    def fail(model):
        raise EnclosureUnavailable('source seam')
    monkeypatch.setattr(subject, 'bound_lunar_reference_accelerations', fail)
    result = subject.isolate_lunar_reference_event(_model(), I(-1, 1), policy='danjon_angular', tolerance=1)
    assert result.vector_evaluations == 0 and not result.complete
    assert all(len(part.cells) == 1 and part.cells[0].interval == I(-1, 1) for part in result.partitions)


@pytest.mark.parametrize('box', [I(-1, 0), I(0, 1), I(F(-1, 3), F(2, 3))])
def test_taylor_translation_encloses_independent_quadratic_vectors(box):
    point = replace(_affine(I.point(0)),
        moon_geocentric_km=(I.point(10), I.point(20), I.point(30)),
        moon_derivative_km_per_tt_day=(I.point(1), I.point(2), I.point(3)),
        sun_derivative_km_per_tt_day=(I.point(0),)*3)
    acceleration = LunarReferenceAccelerationBounds((F(0),)*3, (F(2), F(4), F(6)),
                                                     I(-1, 1), F(1), F(0))
    result = subject._taylor_vectors(point, box, acceleration)
    for t in (box.lo, box.midpoint, box.hi):
        for scale, value, rate in zip((1, 2, 3), result.moon_geocentric_km,
                                     result.moon_derivative_km_per_tt_day):
            assert value.contains(scale*(10+t+t*t))
            assert rate.contains(scale*(1+2*t))


@pytest.mark.parametrize('kwargs', [{'policy': 'other'}, {'tolerance': 0},
    {'max_vector_evaluations': True}, {'max_depth': -1}, {'earth_radius_km': -1}])
def test_invalid_requests_fail_explicitly(kwargs):
    request = dict(policy='danjon_angular', tolerance=F(1, 100))
    request.update(kwargs)
    with pytest.raises((TypeError, ValueError)):
        subject.isolate_lunar_reference_event(_model(), I(-1, 1), **request)
