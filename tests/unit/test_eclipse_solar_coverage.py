"""Analytic complete hybrid sequences, multiple components and uncertainty."""
from fractions import Fraction as F

import pytest

from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_solar_coverage import SolarAxisFunctionBounds, cover_solar_central_path


def _functions(box, kind='H1'):
    d, dr = 1-box.square(), -2*box
    if kind == 'H1':
        k, kr = F(1, 4)-box.square(), -2*box
    elif kind == 'H2':
        k, kr = -box, I.point(-1)
    elif kind == 'H3':
        k, kr = box, I.point(1)
    else:
        k, kr = box.square(), 2*box
    return SolarAxisFunctionBounds(box, d, k, I.point(1), I.point(1), dr, kr,
                                   real_continuous_model=True)


def _cover(result):
    assert result.cells[0].domain.lo == result.domain.lo
    assert result.cells[-1].domain.hi == result.domain.hi
    assert all(a.domain.hi == b.domain.lo for a, b in zip(result.cells, result.cells[1:]))
    assert result.evaluations <= result.max_evaluations
    assert not result.serving_route_totality_proved and not result.physical_accuracy_certified


@pytest.mark.parametrize('subtype,sequence', [
    ('H1', ('annular', 'total', 'annular')), ('H2', ('total', 'annular')),
    ('H3', ('annular', 'total')),
])
def test_complete_sequences_require_all_endpoint_and_transition_proofs(subtype, sequence):
    result = cover_solar_central_path(
        I(-2, 2), lambda box: _functions(box, subtype), tolerance=F(1, 1024),
        continuity_assumed=True,
    )
    _cover(result)
    assert result.coverage_complete and result.event_interval_enclosed
    assert result.status == 'hybrid' and result.subtype == subtype
    assert result.sequence == sequence
    assert len(result.central_intervals) == 1
    assert len([root for root in result.roots if root.function == 'axis']) == 2
    assert all(root.domain.width <= F(1, 1024) for root in result.roots)


def test_short_component_away_from_greatest_seed_is_not_missed():
    center, half = F(3, 10), F(1, 200)

    def functions(box):
        t = box-center
        return SolarAxisFunctionBounds(box, half*half-t.square(), t, I.point(1), I.point(1),
                                       -2*t, I.point(1), real_continuous_model=True)

    result = cover_solar_central_path(
        I(-1, 1), functions, tolerance=F(1, 100000), continuity_assumed=True,
    )
    _cover(result)
    assert result.subtype == 'H3'
    entry, exit = result.central_intervals[0]
    assert entry.contains(center-half) and exit.contains(center+half)
    assert exit.hi-entry.lo < F(1, 10)


@pytest.mark.parametrize('tolerance_seconds', [F(1, 1000), F(1, 10)])
def test_eighty_millisecond_ingress_transition_uses_explicit_day_units(tolerance_seconds):
    entry, duration = F(1, 3*86400), F(2, 5*86400)
    center, half = entry+duration/2, duration/2
    switch = entry+F(8, 100*86400)

    def functions(box):
        shifted = box-center
        return SolarAxisFunctionBounds(box, half*half-shifted.square(), box-switch,
            I.point(1), I.point(1), -2*shifted, I.point(1), real_continuous_model=True)

    result = cover_solar_central_path(I(F(-1, 86400), F(1, 86400)), functions,
        tolerance=tolerance_seconds/86400, continuity_assumed=True)
    _cover(result)
    if tolerance_seconds == F(1, 1000):
        assert result.coverage_complete and result.subtype == 'H3'
        assert result.sequence == ('annular', 'total')
        roots = result.roots
        assert len(roots) == 3
        assert roots[0].domain.contains(entry) and roots[1].domain.contains(switch)
        assert roots[2].domain.contains(entry+duration)
        assert roots[0].domain.hi < roots[1].domain.lo < roots[2].domain.lo
    else:
        assert not result.coverage_complete and result.subtype is None


def test_multiple_axis_components_do_not_invent_a_single_path_subtype():
    def functions(box):
        t2 = box.square()
        return SolarAxisFunctionBounds(box, -(t2-1)*(t2-4), box,
                                       I.point(1), I.point(1), -4*(box**3)+10*box,
                                       I.point(1), real_continuous_model=True)

    result = cover_solar_central_path(
        I(-3, 3), functions, tolerance=F(1, 1024), continuity_assumed=True,
    )
    _cover(result)
    assert result.coverage_complete and len(result.central_intervals) == 2
    assert result.status == 'hybrid' and result.subtype is None


def test_tangent_and_clipped_domains_cannot_receive_a_subtype():
    tangent = cover_solar_central_path(
        I(-2, 2), lambda box: _functions(box, 'tangent'),
        tolerance=F(1, 1024), continuity_assumed=True,
    )
    _cover(tangent)
    assert not tangent.coverage_complete and tangent.subtype is None
    assert any(cell.kind == 'unresolved' and cell.domain.contains(0) for cell in tangent.cells)
    clipped = cover_solar_central_path(
        I(F(-1, 2), F(1, 2)), lambda box: _functions(box, 'H3'),
        tolerance=F(1, 1024), continuity_assumed=True,
    )
    assert not clipped.event_interval_enclosed and clipped.subtype is None


@pytest.mark.parametrize('budget', [0, 1, 7])
def test_solar_budget_retains_every_domain_cell(budget):
    result = cover_solar_central_path(
        I(-2, 2), _functions, tolerance=F(1, 1024), continuity_assumed=True,
        max_evaluations=budget,
    )
    _cover(result)
    assert not result.coverage_complete and result.subtype is None


def test_successful_output_bounds_are_not_a_continuous_source_attestation():
    def conditional(box):
        value = _functions(box, 'H3')
        return SolarAxisFunctionBounds(box, value.axis_margin, value.signed_radius,
                                       value.forward_margin, value.daylight_margin)

    result = cover_solar_central_path(I(-2, 2), conditional, tolerance=F(1, 128),
                                      continuity_assumed=False)
    _cover(result)
    assert result.status == 'hybrid'  # positive whole-interval evidence survives
    assert not result.coverage_complete and result.subtype is None


@pytest.mark.parametrize('forward,daylight', [(I(-2, -1), I.point(1)),
                                            (I.point(1), I(-1, 0))])
def test_illegal_or_nighttime_axis_is_excluded_without_inventing_an_eclipse(forward, daylight):
    def functions(box):
        return SolarAxisFunctionBounds(box, I.point(1), I.point(1), forward, daylight,
                                       real_continuous_model=True)

    result = cover_solar_central_path(I(-1, 1), functions, tolerance=F(1, 100),
                                      continuity_assumed=True)
    assert result.status == 'no_legal_axis_on_domain' and result.subtype is None
    assert all(cell.kind == 'excluded' for cell in result.cells)


def test_exact_axis_tangency_is_not_given_a_crossing_or_subtype():
    def functions(box):
        return SolarAxisFunctionBounds(box, box.square(), I.point(1), I.point(1), I.point(1),
                                       2*box, I.point(0), real_continuous_model=True)

    result = cover_solar_central_path(I(-1, 1), functions, tolerance=F(1, 1000),
                                      continuity_assumed=True)
    assert not result.coverage_complete and result.subtype is None
    assert any(cell.kind == 'unresolved' and cell.domain.contains(0) for cell in result.cells)


def test_unexpected_solar_provider_defects_propagate():
    def broken(box):
        raise RuntimeError('unexpected solar provider defect')

    with pytest.raises(RuntimeError, match='provider defect'):
        cover_solar_central_path(I(-1, 1), broken, tolerance=F(1, 100), continuity_assumed=True)


@pytest.mark.parametrize('flag', [1, 'yes'])
def test_truthy_values_are_not_continuity_proof_declarations(flag):
    def functions(box):
        return SolarAxisFunctionBounds(box, I.point(1), I.point(1), I.point(1), I.point(1),
                                       real_continuous_model=flag)

    with pytest.raises(TypeError, match='proof declarations'):
        cover_solar_central_path(I(-1, 1), functions, tolerance=F(1, 100), continuity_assumed=True)
