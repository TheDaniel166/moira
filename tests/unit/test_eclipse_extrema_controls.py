"""Analytic extremum controls for the bounded root-search foundation.

The exact quadratic is a synthetic numerical control, not an eclipse model or
evidence about the duration or completeness of a real event.
"""

from fractions import Fraction as F

import pytest

from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_interval_roots import isolate_roots


@pytest.mark.parametrize("offset", [F(1, 10000), F(0), -F(1, 10000)])
def test_stationary_search_distinguishes_a_miss_tangent_and_short_valley(offset):
    """A derivative search must preserve the analytically known minimum."""
    center = F(1, 3)
    domain = I(0, 1)

    def margin(box):
        return (box - center).square() + offset

    def slope(box):
        return 2 * (box - center)

    extrema = isolate_roots(
        domain, slope, derivative=lambda _: I.point(2), continuous=True,
        tolerance=F(1, 4096), unit="seconds",
    )
    assert extrema.complete
    assert extrema.resolution_reached
    containing = [cell for cell in extrema.cells if cell.interval.contains(center)]
    assert len(containing) == 1
    assert containing[0].status == "unique"
    assert margin(containing[0].interval).contains(offset)

    roots = isolate_roots(
        domain, margin, derivative=slope, continuous=True,
        tolerance=F(1, 4096), unit="seconds",
    )
    if offset > 0:
        assert roots.complete
        assert all(cell.status == "excluded" for cell in roots.cells)
    elif offset == 0:
        # An even-multiplicity zero need not have an endpoint sign change;
        # retaining it as unresolved is safer than inventing an exclusion.
        assert not roots.complete
        assert all(cell.status != "excluded" for cell in roots.cells
                   if cell.interval.contains(center))
    else:
        for root in (center - F(1, 100), center + F(1, 100)):
            assert any(cell.status == "unique" and cell.interval.contains(root)
                       for cell in roots.cells)
            assert all(cell.status != "excluded" for cell in roots.cells
                       if cell.interval.contains(root))
