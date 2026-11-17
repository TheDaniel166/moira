"""Monotonicity exclusions in closed exact-real root cells."""

import pytest

from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_interval_roots import EnclosureUnavailable, isolate_roots


def _loose_linear(box):
    if box.lo == box.hi:
        return I.point(box.lo + 1)
    return I(-10, 10)


def _search(*, derivative, continuous=True, max_evaluations=10):
    return isolate_roots(
        I(0, 1), _loose_linear, tolerance=1, unit="day", continuous=continuous,
        derivative=derivative, max_evaluations=max_evaluations,
    )


def test_nonzero_derivative_and_strict_same_sign_endpoints_exclude_closed_cell():
    result = _search(derivative=lambda box: I.point(1))
    assert result.complete
    assert result.cells[0].status == "excluded"
    assert result.cells[0].reason == "nonzero_derivative_and_same_strict_endpoint_sign"


@pytest.mark.parametrize("intercept,slope", [(2, 1), (2, -1), (-2, 1), (-2, -1)])
def test_monotonic_exclusion_covers_both_signs_and_directions(intercept, slope):
    def enclosure(box):
        if box.lo == box.hi:
            return I.point(intercept + slope * box.lo)
        # A deliberately loose valid enclosure forces the derivative proof.
        return I(-10, 10)

    result = isolate_roots(
        I(0, 1), enclosure, derivative=lambda _: I.point(slope),
        continuous=True, tolerance=1, unit="day",
    )
    assert result.complete
    assert result.cells[0].reason == "nonzero_derivative_and_same_strict_endpoint_sign"


@pytest.mark.parametrize("endpoint", [0, 1])
def test_root_on_either_closed_endpoint_is_never_excluded(endpoint):
    def enclosure(box):
        if box.lo == box.hi:
            return I.point(box.lo - endpoint)
        return I(-1, 1)

    result = isolate_roots(
        I(0, 1), enclosure, derivative=lambda _: I.point(1),
        continuous=True, tolerance=1, unit="day",
    )
    assert result.cells[0].status == "unique"


@pytest.mark.parametrize("derivative,continuous", [
    (lambda box: I(-1, 1), True),
    (None, True),
    (lambda box: I.point(1), False),
])
def test_missing_or_unproved_monotonicity_is_unresolved(derivative, continuous):
    assert _search(derivative=derivative, continuous=continuous).cells[0].status == "unresolved"


def test_endpoint_zero_and_unsupported_derivative_are_not_excluded():
    def enclosure(box):
        return I.point(box.lo) if box.lo == box.hi else I(-1, 1)

    result = isolate_roots(I(0, 1), enclosure, tolerance=1, unit="day", continuous=True,
                           derivative=lambda box: I.point(1))
    assert result.cells[0].status == "unique"

    def unavailable(box):
        raise EnclosureUnavailable("no derivative")

    result = _search(derivative=unavailable)
    assert result.cells[0].status == "unresolved"
    assert "no derivative" in result.cells[0].reason


def test_derivative_evaluation_obeys_budget():
    result = _search(derivative=lambda box: I.point(1), max_evaluations=3)
    assert result.evaluations == 3
    assert result.cells[0].reason == "evaluation_budget_exhausted"
