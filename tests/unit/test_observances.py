"""Independent interval examples for the Dharmasindhu date precedence."""
from datetime import date, timezone

import pytest

from moira.observances import (
    ObservanceDateResult,
    ObservanceFastingContext,
    ObservanceNight,
    _boundary,
    _Bracket,
    _coverage,
    _interval,
    _parana,
    _prefer_later,
    _sunrise_tithi,
)

_BASE = 2461087.5


@pytest.mark.parametrize(("tithi", "expected"), [
    ((5, 25), ("full", "none")),
    ((15, 35), ("partial", "partial")),
    ((15, 45), ("partial", "full")),
    ((5, 35), ("full", "partial")),
    ((5, 45), ("full", "full")),
    ((21, 29), ("none", "none")),
    ((20, 30), ("none", "none")),
    ((10, 20), ("full", "none")),
    ((12, 18), ("partial", "none")),
    ((24, 35), ("none", "partial")),
])
def test_date_precedence_for_half_open_intervals(tithi, expected):
    start, end = (_Bracket(value, value) for value in tithi)
    first = _coverage(start, end, _Bracket(10, 10), _Bracket(20, 20))
    second = _coverage(start, end, _Bracket(30, 30), _Bracket(40, 40))
    assert (first, second) == tuple((value,) for value in expected)


@pytest.mark.parametrize(("first", "second", "winner", "reason"), [
    ("full", "none", 0, "only_covered_night"),
    ("none", "partial", 1, "only_covered_night"),
    ("full", "partial", 0, "full_over_partial"),
    ("partial", "full", 1, "full_over_partial"),
    ("full", "full", 1, "later_equal_coverage"),
    ("partial", "partial", 1, "later_equal_coverage"),
    ("none", "none", 1, "later_no_coverage"),
])
def test_source_winner_and_reason(first, second, winner, reason):
    assert _prefer_later((first,), (second,)) == (winner, reason)


def test_uncertain_contact_only_blocks_a_decision_it_can_change():
    first = _coverage(_Bracket(5, 5), _Bracket(19, 21), _Bracket(10, 10), _Bracket(20, 20))
    assert first == ("partial", "full")
    assert _prefer_later(first, ("full",)) == (1, "winner_stable_across_brackets")
    assert _prefer_later(first, ("partial",)) == (None, "boundary_brackets_can_change_date")


@pytest.mark.parametrize(("rise", "phase"), [
    ((-0.2, -0.1), "before_caturdashi"),
    ((-0.1, 0.1), "boundary_ambiguous"),
    ((0, 0), "caturdashi"),
    ((0.25, 0.25), "caturdashi"),
    ((0.9, 1.1), "boundary_ambiguous"),
    ((1, 1), "after_caturdashi"),
])
def test_selected_morning_tithi_keeps_half_open_boundary_evidence(rise, phase):
    utc = timezone.utc
    tithi = _interval(_Bracket(_BASE, _BASE), _Bracket(_BASE + 1, _BASE + 1), utc)
    sunrise = _boundary(_Bracket(_BASE + rise[0], _BASE + rise[1]), utc)
    assert _sunrise_tithi(sunrise, tithi) == phase


@pytest.mark.parametrize(("end_width", "status", "reason", "mode"), [
    (0, "selected", "insufficient_time_after_daily_rites", "at_tithi_end"),
    (0.000001, "ambiguous", "parana_boundary_brackets_overlap", None),
])
def test_exact_readiness_at_tithi_end_and_uncertainty(end_width, status, reason, mode):
    end = _BASE + 0.65
    utc = timezone.utc
    sunrise = _boundary(_Bracket(_BASE + 0.25, _BASE + 0.25), utc)
    tithi = _interval(_Bracket(_BASE - 0.4, _BASE - 0.4), _Bracket(end, end + end_width), utc)
    day = date(2026, 2, 15)
    night = ObservanceNight(day, None, None, sunrise, None, ("full",))
    decision = ObservanceDateResult("selected", "only_covered_night", day, tithi=tithi, nights=(night,))
    parana = _parana(decision, ObservanceFastingContext(False, end), utc)
    assert (parana.status, parana.reason, parana.mode) == (status, reason, mode)
    assert parana.interval is None


def test_date_boundary_is_identical_across_public_surfaces():
    import moira
    import moira.facade
    import moira.vedic

    assert moira.evaluate_observance is moira.facade.evaluate_observance
    assert moira.evaluate_observance is moira.vedic.evaluate_observance
    catalogue = moira.observance_catalogue()
    assert len(catalogue) == 1
    assert catalogue[0].date_admission == "ordinary_month_admitted"
    assert catalogue[0].fasting_admission == "conditional_ordinary_parana_admitted"
    result = moira.evaluate_observance(
        catalogue[0].rule_id, date(2011, 12, 30), -13.83, -171.75, timezone="Pacific/Apia",
    )
    assert result.date_result.status == "unavailable"
    assert result.date_result.reason == "civil_date_skipped"
