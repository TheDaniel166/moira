"""Coverage and evidence contracts for rational root isolation."""
from fractions import Fraction as F

import pytest

from moira._eclipse_interval import IntervalBudgetError, RationalInterval as I
from moira._eclipse_interval_roots import EnclosureUnavailable, isolate_roots


def assert_covers_domain(partition):
    cells = partition.cells
    assert cells[0].interval.lo == partition.domain.lo
    end = cells[0].interval.hi
    for cell in cells[1:]:
        assert cell.interval.lo <= end
        end = max(end, cell.interval.hi)
    assert end == partition.domain.hi


def test_two_roots_are_not_silently_excluded():
    result = isolate_roots(I(-2, 2), lambda x: x.square() - 1,
                           derivative=lambda x: 2*x, continuous=True,
                           tolerance=F(1, 128), unit="days", time_scale="TDB")
    assert_covers_domain(result)
    for root in (-1, 1):
        relevant = [c for c in result.cells if c.interval.contains(root)]
        assert relevant
        assert all(c.status != "excluded" for c in relevant)
        assert any(c.status == "unique" for c in relevant)
    assert result.complete
    assert result.time_scale == "TDB"


def test_two_roots_inside_one_coarse_cell_and_endpoint_crossings():
    a, b = F(3, 100), F(8, 100)
    result = isolate_roots(I(0, 1), lambda x: (x-a)*(x-b),
                           derivative=lambda x: 2*x-(a+b), continuous=True,
                           tolerance=F(1, 10000), unit="seconds")
    assert_covers_domain(result)
    for root in (a, b):
        assert any(c.status == "unique" and c.interval.contains(root) for c in result.cells)
        assert all(c.status != "excluded" for c in result.cells if c.interval.contains(root))


def test_narrow_lunar_like_valley_and_tangent_are_not_lost():
    center, radius = F(37), F(139, 20)  # duration 13.9 seconds
    def f(x):
        return (x-center).square() - radius*radius
    result = isolate_roots(I(0, 100), f, derivative=lambda x: 2*(x-center),
                           continuous=True, tolerance=F(1, 100), unit="seconds")
    for root in (center-radius, center+radius):
        assert any(c.interval.contains(root) and c.status == "unique" for c in result.cells)
    tangent = isolate_roots(I(0, 1), lambda x: (x-F(1, 2)).square(),
                            derivative=lambda x: 2*(x-F(1, 2)), continuous=True,
                            tolerance=F(1, 16), unit="seconds")
    assert not tangent.complete
    assert all(c.status != "excluded" for c in tangent.cells if c.interval.contains(F(1, 2)))


def test_exhausted_budget_retains_unprocessed_coverage():
    result = isolate_roots(I(0, 1), lambda x: x-I(F(1, 3), F(2, 3)),
                           tolerance=F(1, 1000), unit="seconds", max_evaluations=4)
    assert_covers_domain(result)
    assert not result.complete
    assert any(c.reason == "evaluation_budget_exhausted" for c in result.cells)
    zero = isolate_roots(I(0, 1), lambda x: x, tolerance=F(1, 10), unit="seconds", max_evaluations=0)
    assert len(zero.cells) == 1 and zero.cells[0].interval == I(0, 1)
    assert zero.cells[0].status == "unresolved"


def test_no_continuity_or_unproved_zero_does_not_prove_presence():
    def discontinuous(x):
        return I(-1, -1) if x.hi < F(1, 2) else I(1, 1) if x.lo > F(1, 2) else I(-1, 1)
    result = isolate_roots(I(0, 1), discontinuous, continuous=False,
                           tolerance=F(1, 10), unit="seconds")
    assert all(c.status not in ("unique", "present") for c in result.cells)
    uncertain_point = isolate_roots(I(1, 1), lambda x: I(-1, 1),
                                    tolerance=1, unit="seconds")
    assert uncertain_point.cells[0].status == "unresolved"
    exact = isolate_roots(I(1, 1), lambda x: I.point(0), tolerance=1, unit="seconds")
    assert exact.cells[0].status == "present"


def test_constant_plateau_and_strict_near_miss():
    plateau = isolate_roots(I(0, 1), lambda x: I.point(0),
                            tolerance=F(1, 16), unit="seconds", max_depth=2)
    assert_covers_domain(plateau)
    assert not plateau.complete
    assert all(c.status == "present" for c in plateau.cells)
    # A root just outside the closed domain cannot appear in it.
    near_miss = isolate_roots(I(0, 1), lambda x: x + F(1, 10**9),
                              tolerance=F(1, 100), unit="seconds")
    assert len(near_miss.cells) == 1
    assert near_miss.cells[0].status == "excluded"


def test_shared_root_is_not_claimed_as_two_distinct_roots():
    result = isolate_roots(I(-1, 1), lambda x: x, derivative=lambda x: I.point(1),
                           continuous=True, tolerance=F(1, 8), unit="seconds")
    touching = [c for c in result.cells if c.status == "unique" and c.interval.contains(0)]
    assert len(touching) == 2
    assert touching[0].interval.hi == touching[1].interval.lo == 0
    assert_covers_domain(result)


def test_unique_root_does_not_imply_requested_time_resolution():
    result = isolate_roots(I(-1, 1), lambda x: x, derivative=lambda x: I.point(1),
                           continuous=True, tolerance=F(1, 10**9), unit="seconds", max_depth=0)
    assert result.complete
    assert result.cells[0].status == "unique"
    assert not result.resolution_reached


def test_unavailable_and_budget_fail_closed_unexpected_errors_propagate():
    def unavailable(_):
        raise EnclosureUnavailable("unsupported_model")
    result = isolate_roots(I(0, 1), unavailable, tolerance=1, unit="seconds")
    assert result.cells[0].status == "unresolved"
    def budget(_):
        raise IntervalBudgetError("too large")
    result = isolate_roots(I(0, 1), budget, tolerance=1, unit="seconds")
    assert result.cells[0].status == "unresolved"
    def bad(_):
        raise RuntimeError("bad provider")
    with pytest.raises(RuntimeError, match="bad provider"):
        isolate_roots(I(0, 1), bad, tolerance=1, unit="seconds")
    with pytest.raises(TypeError, match="RationalInterval"):
        isolate_roots(I(0, 1), lambda _: 1, tolerance=1, unit="seconds")
