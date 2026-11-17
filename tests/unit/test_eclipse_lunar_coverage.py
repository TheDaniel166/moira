"""Whole-domain exclusion, narrow positives, seams and safe chronological queries."""
from dataclasses import replace
from fractions import Fraction as F

import pytest

from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_interval_roots import EnclosureUnavailable
from moira._eclipse_lunar_coverage import (
    LunarCoverageCell, LunarReferenceCoverage, bound_lunar_exclusion_chord,
    cover_lunar_reference_interval, first_reference_overlap,
)
from tests.unit.test_eclipse_continuous_lunar_contacts import _affine


RADII = dict(earth_radius_km=2, sun_radius_km=4, moon_radius_km=F(1, 2))


def _cover(result):
    assert result.cells[0].domain.lo == result.domain.lo
    assert result.cells[-1].domain.hi == result.domain.hi
    assert all(a.domain.hi == b.domain.lo for a, b in zip(result.cells, result.cells[1:]))
    assert result.evaluations <= result.max_evaluations
    assert not result.eclipse_absence_certified and not result.serving_route_totality_proved


@pytest.mark.parametrize('policy', ['danjon_angular', 'static_finite_cone'])
def test_closed_domain_exclusions_and_overlap_cells(policy):
    result = cover_lunar_reference_interval(
        I(-8, 8), _affine, policy=policy, tolerance=F(1, 100), max_evaluations=2000, **RADII,
    )
    _cover(result)
    assert {cell.status for cell in result.cells} == {'overlap', 'excluded', 'unresolved'}
    for cell in result.cells:
        if cell.reason == 'whole_interval_chord_exclusion':
            assert cell.chord_lower > cell.threshold_upper
        if cell.status == 'unresolved':
            assert cell.domain.width <= F(1, 100)


def test_angular_chord_excludes_sunward_month_portion_without_full_moon_filter():
    def vectors(box):
        return replace(_affine(box, speed=0, z=-10), continuous_on_domain=False,
                       differentiable_on_domain=False)

    result = cover_lunar_reference_interval(
        I(-15, 15), vectors, policy='danjon_angular', tolerance=F(1, 100), **RADII,
    )
    _cover(result)
    assert len(result.cells) == 1 and result.cells[0].status == 'excluded'
    assert result.cells[0].reason == 'whole_interval_chord_exclusion'


def test_short_peak_between_samples_is_never_excluded():
    center = F(1, 3)

    def vectors(box):
        return _affine(box, speed=60_000_000, center=center)

    result = cover_lunar_reference_interval(
        I(0, 1), vectors, policy='static_finite_cone', tolerance=F(1, 10**9),
        max_evaluations=3000, **RADII,
    )
    _cover(result)
    owners = [cell for cell in result.cells if cell.domain.contains(center)]
    assert owners and all(cell.status == 'overlap' for cell in owners)


@pytest.mark.parametrize('budget', [0, 1, 9])
def test_budget_preserves_all_requested_time(budget):
    result = cover_lunar_reference_interval(
        I(-8, 8), _affine, policy='danjon_angular', tolerance=F(1, 100),
        max_evaluations=budget, **RADII,
    )
    _cover(result)
    assert any(cell.status == 'unresolved' for cell in result.cells)


def test_unproved_seams_and_cone_domains_stay_bounded_and_explicit():
    def unavailable(box):
        raise EnclosureUnavailable('retarded emission seam unproved')

    result = cover_lunar_reference_interval(
        I(-1, 1), unavailable, policy='danjon_angular', tolerance=F(1, 4),
        max_evaluations=32, **RADII,
    )
    _cover(result)
    assert all(cell.status == 'unresolved' and 'emission seam' in cell.reason for cell in result.cells)
    with pytest.raises(EnclosureUnavailable, match='downstream'):
        bound_lunar_exclusion_chord(_affine(I.point(0), z=-10), policy='static_finite_cone', **RADII)


def test_nearest_component_cannot_step_past_unresolved_time():
    cells = (LunarCoverageCell(I(-3, -2), 'excluded', 'proof'),
             LunarCoverageCell(I(-2, -1), 'unresolved', 'seam'),
             LunarCoverageCell(I(-1, 0), 'overlap', 'proof'))
    result = LunarReferenceCoverage(I(-3, 0), 'danjon_angular', 'rad', cells, 3, 3)
    assert first_reference_overlap(result).status == 'unresolved'
    assert first_reference_overlap(result, direction=-1).status == 'overlap'


def test_unexpected_provider_error_is_not_a_negative_finding():
    def broken(box):
        raise RuntimeError('provider defect')

    with pytest.raises(RuntimeError, match='provider defect'):
        cover_lunar_reference_interval(I(-1, 1), broken, policy='danjon_angular',
                                       tolerance=F(1, 10), **RADII)
