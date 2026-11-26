"""Regression and enclosure witnesses for bounded geocentric conjunctions."""

from types import SimpleNamespace

import pytest

from moira import phenomena
from moira._event_search.budgets import WorkMeter
from moira._event_search.intervals import Interval
from moira._event_search.isolation import Signal
from moira._geocentric_conjunctions import (
    GeocentricConjunctionBudgetError,
    _Limits,
    _resolve_crossings,
)


def test_sampled_range_recovers_same_cell_crossings(monkeypatch):
    roots = (100.75, 101.25)

    def separation(body1, body2, jd, reader, apparent=False):
        return (jd - roots[0]) * (jd - roots[1])

    monkeypatch.setattr(phenomena, "_conjunction_separation", separation)
    monkeypatch.setattr(phenomena, "planet_at", lambda *args, **kwargs: SimpleNamespace(longitude=0.0))
    events = phenomena.conjunctions_in_range("A", "B", 100.0, 103.0, reader=object())
    assert [event.jd_ut for event in events] == pytest.approx(roots, abs=1e-8, rel=0)


def _quadratic_signal(center, half_spacing, lift):
    def signal(a, b, coarse):
        x = Interval(a, b) - center
        middle = Interval.point((a + b) / 2.0) - center
        return Signal(x.square() - half_spacing**2 + lift, 2 * x, middle.square() - half_spacing**2 + lift)

    return signal


def _meter(**limits):
    return WorkMeter(
        _Limits(**limits),
        budget_error=GeocentricConjunctionBudgetError,
        kinds=("evaluations", "root_iterations", "subdivisions", "candidates"),
    )


@pytest.mark.parametrize(("half_spacing", "lift"), [(0.25, 0.0), (0.25, 360.0), (1 / 86400, 0.0)])
def test_interval_search_proves_both_crossings_in_one_coarse_cell(half_spacing, lift):
    epochs = (101.0 - half_spacing, 101.0 + half_spacing)

    def refine(witness):
        matches = [jd for jd in epochs if witness.lower_jd_ut1 < jd < witness.upper_jd_ut1]
        assert len(matches) == 1
        return phenomena.PhenomenonEvent("A-B", "Conjunction", matches[0], 0.0)

    events, gaps, excluded = _resolve_crossings(
        _quadratic_signal(101.0, half_spacing, lift), 100.0, 103.0, _meter(), refine,
    )
    assert [event.jd_ut for event, _ in events] == list(epochs)
    assert [witness.direction for _, witness in events] == [-1, 1]
    assert events[0][1].upper_jd_ut1 <= events[1][1].lower_jd_ut1
    assert not gaps
    assert excluded > 0


def test_interval_search_distinguishes_unresolved_touch_from_proved_empty():
    def unexpected_refinement(witness):
        pytest.fail(f"Unexpected crossing proof: {witness}")

    touch = _resolve_crossings(
        _quadratic_signal(101.0, 0.0, 0.0), 100.0, 103.0, _meter(), unexpected_refinement,
    )
    opposition = _resolve_crossings(
        _quadratic_signal(101.0, 0.25, 180.0), 100.0, 103.0, _meter(), unexpected_refinement,
    )
    assert not touch[0]
    assert any(gap.lower_jd_ut1 <= 101.0 <= gap.upper_jd_ut1 for gap in touch[1])
    assert opposition == ((), (), 2)


def test_interval_search_enforces_work_budget():
    with pytest.raises(GeocentricConjunctionBudgetError, match="evaluations"):
        _resolve_crossings(
            _quadratic_signal(101.0, 0.25, 0.0), 100.0, 103.0, _meter(max_evaluations=1),
            lambda witness: None,
        )


def test_de441_jupiter_saturn_crossing_receipt_and_inclusive_bounds(reader):
    epoch = 2459205.264318665
    broad = phenomena.conjunctions_in_range_with_truth(
        "Jupiter", "Saturn", 2459204.0, 2459207.0, reader, verify_intervals=True,
    )
    for start, end in [(epoch, 2459206.0), (2459204.0, epoch)]:
        edge = phenomena.conjunctions_in_range_with_truth(
            "Jupiter", "Saturn", start, end, reader, verify_intervals=True,
        )
        assert edge.events == broad.events
        assert not edge.resolution.unresolved

    event, = broad.events
    assert event.jd_ut == epoch
    first = phenomena.planet_at("Jupiter", event.jd_ut, reader=reader, apparent=True)
    second = phenomena.planet_at("Saturn", event.jd_ut, reader=reader, apparent=True)
    assert event.value == pytest.approx(first.longitude, abs=1e-9, rel=0)
    assert abs(first.longitude - second.longitude) < 1e-6
    witness, = broad.resolution.witnesses
    assert witness.lower_jd_ut1 < epoch < witness.upper_jd_ut1
    assert witness.lower_offset_deg[1] < 0.0 < witness.upper_offset_deg[0]
    assert witness.relative_rate_deg_per_day[0] > 0.0
    assert not broad.resolution.unresolved
    assert broad.resolution.planetary_ephemeris == "DE441"
    assert broad.resolution.source_sha256 and all(len(digest) == 64 for digest in broad.resolution.source_sha256)
