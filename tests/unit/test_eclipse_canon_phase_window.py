"""Month-stepped UT window bounds for the existing lunar canon optimizer."""
import math

import pytest

from moira._eclipse_canon_window import (
    CanonPhaseOrderingUnsupported,
    _canon_ut_half_window,
    _month_delta_envelope,
)
from moira.julian import delta_t_nasa_canon, julian_day


class CoverageReader:
    def __init__(self, coverage):
        self._coverage = coverage

    def coverage(self):
        return self._coverage


def test_adjacent_month_delta_envelope_covers_year_and_policy_breaks():
    low, high, jump = _month_delta_envelope(1579, 1602)
    values = [delta_t_nasa_canon(year + (month - 0.5) / 12.0)
              for year in range(1579, 1603) for month in range(1, 13)]
    assert min(values) == low and max(values) == high
    assert all(abs(a - b) <= jump for a, b in zip(values, values[1:]))


@pytest.mark.parametrize("year,month,day", [(-1903, 2, 1), (1582, 10, 15),
                                              (1600, 1, 1), (2024, 1, 1), (3000, 12, 31)])
def test_canon_bound_covers_actual_neighboring_month_delta(year, month, day):
    reference = julian_day(year, month, day)
    # Reader envelope includes all test months and the calendar reform.
    reader = CoverageReader({(0, 3): (julian_day(-1999, 1, 1), julian_day(3001, 1, 1))})
    bound = _canon_ut_half_window(reader, reference)
    assert 0.2 < bound < 0.21
    low, high, jump = _month_delta_envelope(year - 1, year + 1)
    assert 0.2 + jump / 86400 <= bound
    assert math.isfinite(low) and math.isfinite(high)


def test_no_reader_coverage_capability_is_needed():
    assert 0.2 < _canon_ut_half_window(object(), 2451545.0) < 0.21
    assert _canon_ut_half_window(CoverageReader({}), 2451545.0) > 0.2
    with pytest.raises(ValueError):
        _canon_ut_half_window(CoverageReader({(0, 3): (1.0, 2.0)}), math.nan)


def test_unbounded_month_jump_does_not_emit_an_unsupported_bound(monkeypatch):
    monkeypatch.setattr("moira._eclipse_canon_window._month_delta_envelope", lambda *args: (0.0, 2_000_000.0, 2_000_000.0))
    with pytest.raises(CanonPhaseOrderingUnsupported, match="finite UT bound"):
        _canon_ut_half_window(CoverageReader({(0, 3): (2451540.0, 2451550.0)}), 2451545.0)
