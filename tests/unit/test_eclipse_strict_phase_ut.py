"""Conditional native UT clock and whole-domain strict phase schedule."""
from fractions import Fraction
import math

import pytest

from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_strict_phase_ut import bound_strict_ut_phase_interval, evaluate_bounded_strict_ut_phase


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("ut", [2451545.25 - 100 * 36525, 1026289.7107341307,
                                2459895.9582497696, 2688460.25, 2451545.25 + 100 * 36525])
def test_strict_ut_interval_encloses_its_clock_and_phase_samples(planetary_reader, ut):
    bounds = bound_strict_ut_phase_interval(planetary_reader, ut, I(Fraction(-5, 86400), Fraction(5, 86400)))
    assert bounds.unchanged_clock_source_data_and_reader_required
    assert not bounds.source_and_arithmetic_attested
    assert not bounds.continuous_root_proved
    assert not bounds.complete_search_certified
    for seconds in (-4.99, -2, 0, 2, 4.99):
        sample = evaluate_bounded_strict_ut_phase(bounds, ut + seconds / 86400)
        assert bounds.phase.cross_km2.contains(sample.cross_km2)
        assert bounds.phase.dot_km2.contains(sample.dot_km2)
        assert math.isfinite(sample.tt_jd)


@pytest.mark.requires_ephemeris
def test_strict_ut_interval_refuses_outside_samples(planetary_reader):
    ut = 2459895.9582497696
    bounds = bound_strict_ut_phase_interval(planetary_reader, ut, I.point(0))
    with pytest.raises(ValueError, match="outside"):
        evaluate_bounded_strict_ut_phase(bounds, ut + 1)
