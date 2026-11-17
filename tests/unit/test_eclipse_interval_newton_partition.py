"""Optional interval Newton within the closed-cell root partitioner."""

import pytest

from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_interval_roots import isolate_roots


def _search(function, derivative, **kwargs):
    return isolate_roots(I(0, 1), function, derivative=derivative, continuous=True,
                         continuously_differentiable=True, interval_newton=True,
                         tolerance=1, unit="day", **kwargs)


def test_interior_inclusion_proves_a_unique_root_despite_loose_endpoint_bounds():
    def value(x):
        return I.point(x.lo - 1/2) if x.lo == x.hi == 1/2 else I(-1, 1)
    result = _search(value, lambda _: I.point(1))
    assert result.interval_newton_enabled
    assert result.cells[0].status == "unique"
    assert result.cells[0].reason == "newton_image_strictly_inside"
    assert result.evaluations == 4


def test_disjoint_image_excludes_the_entire_closed_cell():
    def value(x):
        return I.point(x.lo + 1) if x.lo == x.hi == 1/2 else I(-1, 3)
    result = _search(value, lambda _: I.point(1))
    assert result.cells[0].status == "excluded"
    assert result.cells[0].reason == "newton_image_disjoint"


def test_shared_endpoint_roots_are_not_excluded():
    result = isolate_roots(I(-1, 1), lambda x: x, derivative=lambda x: I.point(1),
                           continuous=True, continuously_differentiable=True,
                           interval_newton=True, tolerance=1, unit="day")
    relevant = [cell for cell in result.cells if cell.interval.contains(0)]
    assert len(relevant) == 2
    assert all(cell.status == "unique" for cell in relevant)
    assert result.cells[0].interval.lo == result.domain.lo
    assert result.cells[-1].interval.hi == result.domain.hi


@pytest.mark.parametrize("budget", range(4))
def test_newton_uses_the_shared_budget_without_losing_coverage(budget):
    result = _search(lambda x: x - 1/2, lambda _: I.point(1), max_evaluations=budget)
    assert result.evaluations == budget
    assert len(result.cells) == 1
    assert result.cells[0].interval == result.domain
    assert result.cells[0].status == "unresolved"


def test_no_newton_without_explicit_model_and_derivative_contract():
    with pytest.raises(ValueError, match="continuous differentiability"):
        isolate_roots(I(-1, 1), lambda x: x, derivative=lambda x: I.point(1),
                      continuous=True, interval_newton=True, tolerance=1, unit="day")


def test_tangent_is_never_labeled_unique_or_excluded():
    result = _search(lambda x: (x - 1/2).square(), lambda x: 2*x - 1)
    assert result.cells[0].status == "unresolved"
