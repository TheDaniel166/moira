"""Exact fixed-pole phase observables and conditional root proofs."""

from fractions import Fraction

import pytest

from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_interval_roots import EnclosureUnavailable
from moira._eclipse_reference_phase import (
    ReferencePhaseVectors,
    bound_reference_phase,
    isolate_reference_phase_roots,
)


def vec(x, y, z):
    return tuple(item if isinstance(item, I) else I.point(item) for item in (x, y, z))


POLE = vec(0, 0, 1)


@pytest.mark.parametrize("branch,moon_x", [("new", 1), ("full", -1)])
def test_continuous_linear_model_proves_unique_phase_root(branch, moon_x):
    def provider(t):
        return ReferencePhaseVectors(vec(1, 0, 0), vec(moon_x, t, 0), vec(0, 0, 0), vec(0, 1, 0))

    result = isolate_reference_phase_roots(
        I(Fraction(-1, 10), Fraction(2, 10)), provider, pole=POLE, phase=branch,
        tolerance=Fraction(1, 32), continuity_assumed=True, derivative_enclosed=True,
    )
    assert result.complete
    assert any(cell.status == "unique" and cell.interval.contains(0) for cell in result.cells)
    assert all(cell.status in ("unique", "excluded") for cell in result.cells)


def test_derivative_formula_and_exact_pole_projection():
    result = bound_reference_phase(
        ReferencePhaseVectors(vec(2, 3, 4), vec(5, 7, 11), vec(3, 2, 1), vec(0, -1, 2)),
        vec(1, 2, 3),
    )
    assert result.determinant == I.point(-2)
    assert result.projected_dot == I.point(10)
    assert result.derivative == I.point(-12)


def test_ambiguous_branch_or_seam_never_becomes_root_proof():
    def branch_ambiguous(t):
        return ReferencePhaseVectors(vec(1, 0, 0), vec(t, t, 0), vec(0, 0, 0), vec(1, 1, 0))

    result = isolate_reference_phase_roots(
        I(-1, 1), branch_ambiguous, pole=POLE, phase="new", tolerance=Fraction(1, 10),
        continuity_assumed=True, derivative_enclosed=True,
    )
    assert len(result.cells) == 1 and result.cells[0].status == "unresolved"
    assert not result.complete

    def seam(t):
        raise EnclosureUnavailable("record seam")

    result = isolate_reference_phase_roots(
        I(-1, 1), seam, pole=POLE, phase="full", tolerance=Fraction(1, 10),
        continuity_assumed=True,
    )
    assert result.cells[0].status == "unresolved"
    assert "record seam" in result.cells[0].reason


def test_no_implicit_continuity_or_derivative_claims():
    def provider(t):
        return ReferencePhaseVectors(vec(1, 0, 0), vec(1, t, 0))

    result = isolate_reference_phase_roots(
        I(Fraction(-1, 10), Fraction(2, 10)), provider, pole=POLE, phase="new",
        tolerance=1, continuity_assumed=False,
    )
    assert result.cells[0].status == "unresolved"
    result = isolate_reference_phase_roots(
        I(Fraction(-1, 10), Fraction(2, 10)), provider, pole=POLE, phase="new",
        tolerance=1, continuity_assumed=True, derivative_enclosed=True,
    )
    assert result.cells[0].status == "unresolved"
    assert "derivatives unavailable" in result.cells[0].reason


def test_tangent_root_is_not_invented_from_same_sign_endpoints():
    def provider(t):
        return ReferencePhaseVectors(vec(1, 0, 0), vec(1, t.square(), 0),
                                     vec(0, 0, 0), vec(0, 2 * t, 0))

    result = isolate_reference_phase_roots(
        I(-1, 1), provider, pole=POLE, phase="new", tolerance=Fraction(1, 8),
        continuity_assumed=True, derivative_enclosed=True,
    )
    assert not result.complete
    assert not any(cell.status == "unique" for cell in result.cells)


def test_requires_exact_nonzero_pole_and_both_rates():
    vectors = ReferencePhaseVectors(vec(1, 0, 0), vec(1, 0, 0))
    with pytest.raises(ValueError, match="fixed nonzero"):
        bound_reference_phase(vectors, vec(0, 0, 0))
    with pytest.raises(ValueError, match="fixed nonzero"):
        bound_reference_phase(vectors, vec(0, 0, I(1, 2)))
    with pytest.raises(ValueError, match="both vector derivatives"):
        bound_reference_phase(ReferencePhaseVectors(vectors.sun, vectors.moon, vec(0, 0, 0)), POLE)
