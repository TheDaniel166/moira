"""Integration of exact fixed-pole phase roots and continuous DE441 vectors."""

from fractions import Fraction

import pytest

from moira._eclipse_continuous_lunar import build_continuous_lunar_reference
from moira._eclipse_continuous_lunar_phase import isolate_continuous_lunar_phase
from moira._eclipse_interval import RationalInterval as I


# Explicit fixed rational J2000-like plane for this reference model; this is
# not a claim that the model reproduces the date-dependent legacy ecliptic.
POLE = tuple(I.point(value) for value in (
    0, Fraction(-3977771559, 10**10), Fraction(9174820621, 10**10),
))


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("anchor,phase", [(2459891.96, "full"), (2459907.46, "new")])
def test_real_de441_reference_phase_root_and_surrounding_signs(planetary_reader, anchor, phase):
    domain = I(Fraction(-1, 12), Fraction(1, 12))
    model = build_continuous_lunar_reference(planetary_reader, anchor, domain)
    result = isolate_continuous_lunar_phase(
        model, domain, pole=POLE, phase=phase,
        tolerance=Fraction(1, 500), max_evaluations=200,
    )
    assert result.tt_anchor_jd == anchor
    assert result.roots.unit == "day offset from TT anchor"
    assert result.roots.time_scale == "TT"
    assert not result.source_and_kernel_attested
    assert not result.legacy_phase_evaluator_attested
    assert not result.physical_accuracy_certified
    assert result.roots.complete, [(cell.status, cell.reason, float(cell.interval.lo), float(cell.interval.hi))
                                   for cell in result.roots.cells if cell.status != "excluded"]
    assert result.roots.cells[0].interval.lo == domain.lo
    assert result.roots.cells[-1].interval.hi == domain.hi
    assert all(left.interval.hi == right.interval.lo
               for left, right in zip(result.roots.cells, result.roots.cells[1:]))
    unique = [cell for cell in result.roots.cells if cell.status == "unique"]
    assert len(unique) == 1
    signs = {"positive" if cell.value.lo > 0 else "negative"
             for cell in result.roots.cells if cell.status == "excluded" and
             not cell.value.contains_zero}
    assert signs == {"positive", "negative"}


@pytest.mark.requires_ephemeris
def test_budget_exhaustion_does_not_certify_real_reference_search(planetary_reader):
    anchor = 2459891.96
    domain = I(Fraction(-1, 12), Fraction(1, 12))
    model = build_continuous_lunar_reference(planetary_reader, anchor, domain)
    result = isolate_continuous_lunar_phase(
        model, domain, pole=POLE, phase="full", tolerance=Fraction(1, 500), max_evaluations=0,
    )
    assert not result.roots.complete
    assert result.roots.cells[0].status == "unresolved"
