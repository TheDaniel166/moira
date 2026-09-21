"""
Unit tests for the Chronological Life Timeline Engine for Primary Directions.
"""

from __future__ import annotations

import math
import pytest

from datetime import datetime, timezone

from moira.constants import HouseSystem
from moira.julian import utc_to_ut1
from moira.primary_directions import (
    PrimaryDirectionKey,
    PrimaryDirectionsTimeline,
    PrimaryDirectionTimelineEvent,
    compute_primary_directions_timeline,
)
from moira.primary_directions.distributor import DistributorPeriod


def test_compute_primary_directions_timeline_basic(moira_engine) -> None:
    """Verify primary directions timeline computation, sorting, and period tracking."""
    dt = datetime(2000, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    chart = moira_engine.chart(dt)
    houses = moira_engine.houses(dt, 51.5, 0.0, system=HouseSystem.PLACIDUS)

    timeline = compute_primary_directions_timeline(
        chart=chart,
        houses=houses,
        geo_lat=51.5,
        max_age_years=60.0,
        reader=moira_engine._reader_obj,
    )

    assert isinstance(timeline, PrimaryDirectionsTimeline)
    assert timeline.max_age_years == 60.0
    assert timeline.key is PrimaryDirectionKey.NAIBOD
    assert len(timeline.events) > 0

    # Invariant: Strictly chronologically sorted and within [0, max_age_years]
    prev_age = 0.0
    for ev in timeline.events:
        assert isinstance(ev, PrimaryDirectionTimelineEvent)
        assert 0.0 < ev.age_years <= 60.0
        assert ev.age_years >= prev_age
        prev_age = ev.age_years
        assert ev.perfection_jd_ut > chart.jd_ut
        assert len(ev.perfection_iso) > 0

    # Verify distributor periods are present and enriched with ages and dates
    assert len(timeline.distributor_periods) > 0
    for p in timeline.distributor_periods:
        assert isinstance(p, DistributorPeriod)
        assert p.entry_age is not None
        assert p.exit_age is not None
        assert p.entry_date_utc is not None
        assert p.exit_date_utc is not None
        assert p.exit_age >= p.entry_age


def test_timeline_distributor_and_participator_tagging(moira_engine) -> None:
    """Verify that events inside a term window receive distributor and participator tags."""
    dt = datetime(2000, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    chart = moira_engine.chart(dt)
    houses = moira_engine.houses(dt, 51.5, 0.0, system=HouseSystem.PLACIDUS)

    timeline = compute_primary_directions_timeline(
        chart=chart,
        houses=houses,
        geo_lat=51.5,
        max_age_years=40.0,
        reader=moira_engine._reader_obj,
    )

    bound_entries = [ev for ev in timeline.events if ev.is_bound_boundary]
    assert len(bound_entries) > 0
    for b_ev in bound_entries:
        assert b_ev.distributor is not None
        assert b_ev.bound_name is not None
        assert b_ev.participator is None

    aspectual_events = [ev for ev in timeline.events if not ev.is_bound_boundary and ev.significator == "Ascendant"]
    if aspectual_events:
        for a_ev in aspectual_events:
            assert a_ev.participator == a_ev.promissor
            assert a_ev.distributor is not None


def test_timeline_with_dynamic_key(moira_engine) -> None:
    """Verify timeline execution with SOLAR_RA_DYNAMIC time-key."""
    dt = datetime(2000, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    chart = moira_engine.chart(dt)
    houses = moira_engine.houses(dt, 51.5, 0.0, system=HouseSystem.PLACIDUS)

    timeline = compute_primary_directions_timeline(
        chart=chart,
        houses=houses,
        geo_lat=51.5,
        key=PrimaryDirectionKey.SOLAR_RA_DYNAMIC,
        max_age_years=30.0,
        reader=moira_engine._reader_obj,
    )

    assert timeline.key is PrimaryDirectionKey.SOLAR_RA_DYNAMIC
    assert len(timeline.events) > 0
    for ev in timeline.events:
        assert 0.0 < ev.age_years <= 30.0
        assert math.isfinite(ev.perfection_jd_ut)


def test_timeline_input_invariants() -> None:
    """Verify defensive handling of invalid arguments."""
    with pytest.raises(ValueError, match="max_age_years must be a positive finite real"):
        compute_primary_directions_timeline(
            chart=None,
            houses=None,
            geo_lat=51.5,
            max_age_years=-10.0,
        )


def test_facade_primary_directions_timeline(moira_engine) -> None:
    """Verify that Moira facade delegates to primary_directions_timeline correctly."""
    dt = datetime(2000, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    chart = moira_engine.chart(dt)
    houses = moira_engine.houses(dt, 51.5, 0.0, system=HouseSystem.PLACIDUS)

    timeline = moira_engine.primary_directions_timeline(
        chart,
        houses,
        51.5,
        max_age_years=25.0,
    )
    assert isinstance(timeline, PrimaryDirectionsTimeline)
    assert timeline.max_age_years == 25.0
    assert len(timeline.events) > 0
