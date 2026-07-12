"""Kernel-backed acceptance tests for progressed contact search and integration."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

import moira
from moira.progressed_astrodynes import ProgressedTerminalKind
from moira.progressed_astrodynes_search import (
    ProgressedContactQuery,
    integrate_progressed_influence,
    search_progressed_contacts,
)


pytestmark = pytest.mark.requires_ephemeris


NATAL = datetime(1882, 12, 12, 12, 11, 26, tzinfo=timezone.utc)
LATITUDE = 41 + 37 / 60
LONGITUDE = -94.0


def _moon_mc_query() -> ProgressedContactQuery:
    return ProgressedContactQuery(
        "Moon", "transit", "M.C.", "radical", "sextile"
    )


def test_transit_search_finds_entry_perfection_and_exit_with_visible_brackets(
    moira_engine,
) -> None:
    start = datetime(1949, 8, 29, 8, tzinfo=timezone.utc)
    result = moira_engine.search_progressed_astrodyne_contacts(
        NATAL,
        start,
        start + timedelta(hours=8),
        LATITUDE,
        LONGITUDE,
        _moon_mc_query(),
    )

    assert result.sample_count == 9
    assert len(result.windows) == 1
    window = result.windows[0]
    assert window.entry_clipped is False
    assert window.exit_clipped is False
    assert window.entry.dt < window.closest_approaches[0].dt < window.exit.dt
    assert window.entry.distance_arcmin == pytest.approx(60.0, abs=0.01)
    assert window.exit.distance_arcmin == pytest.approx(60.0, abs=0.01)
    perfection = window.closest_approaches[0]
    assert perfection.event == "perfection"
    assert abs(
        (
            perfection.dt
            - datetime(1949, 8, 29, 12, 16, 22, tzinfo=timezone.utc)
        ).total_seconds()
    ) < 2.0
    assert perfection.distance_arcmin <= result.policy.perfection_distance_tolerance_arcmin
    assert perfection.power > window.entry.power
    assert perfection.harmony == pytest.approx(perfection.power)
    assert perfection.discord == 0.0


def test_variable_rate_integral_converges_and_keeps_constant_rule_as_comparator(
    moira_engine,
) -> None:
    start = datetime(1949, 8, 29, 10, 34, 32, tzinfo=timezone.utc)
    end = datetime(1949, 8, 29, 13, 58, 23, tzinfo=timezone.utc)
    coarse = moira_engine.integrate_progressed_astrodyne_influence(
        NATAL,
        start,
        end,
        LATITUDE,
        LONGITUDE,
        _moon_mc_query(),
        max_step_hours=0.25,
    )
    fine = moira_engine.integrate_progressed_astrodyne_influence(
        NATAL,
        start,
        end,
        LATITUDE,
        LONGITUDE,
        _moon_mc_query(),
        max_step_hours=0.125,
    )

    assert fine.method == "composite_trapezoid_actual_ephemeris"
    assert fine.provenance == "source_instantaneous_curve_moira_composite_trapezoid"
    assert fine.total_power_days > 0.0
    assert fine.total_harmony_days == pytest.approx(fine.total_power_days)
    assert fine.total_discord_days == 0.0
    assert fine.average_power == pytest.approx(
        fine.total_power_days / fine.duration_days
    )
    assert abs(fine.total_power_days - coarse.total_power_days) < 2e-4
    assert fine.constant_rate_comparator_power_days > 0.0
    assert abs(fine.constant_rate_difference_days) < abs(
        coarse.constant_rate_difference_days
    )
    assert fine.constant_rate_difference_days == pytest.approx(
        fine.total_power_days - fine.constant_rate_comparator_power_days
    )


def test_minor_search_reports_reenforcement_peak_against_named_major_relation(
    moira_engine,
) -> None:
    minor = ProgressedContactQuery(
        "Mercury", "minor_progressed", "Jupiter", "radical", "inconjunct"
    )
    major = ProgressedContactQuery(
        "Jupiter", "major_progressed", "Saturn", "radical", "semi-sextile"
    )
    start = datetime(1949, 8, 23, tzinfo=timezone.utc)
    result = moira_engine.search_progressed_astrodyne_contacts(
        NATAL,
        start,
        datetime(1949, 9, 7, tzinfo=timezone.utc),
        LATITUDE,
        LONGITUDE,
        minor,
        coarse_step_hours=24,
        reenforces_major=major,
    )

    assert len(result.windows) == 1
    perfection = result.windows[0].closest_approaches[0]
    assert perfection.event == "perfection"
    assert perfection.dt.date().isoformat() == "1949-09-05"
    assert perfection.reenforcement_power is not None
    assert perfection.reenforcement_power > 0.0
    assert perfection.reenforced_major_power is not None


def test_search_boundaries_and_query_ontology_fail_explicitly(moira_engine) -> None:
    with pytest.raises(ValueError, match="requires a major-progressed"):
        ProgressedContactQuery("Sun", "radical", "Moon", "radical", "square")
    with pytest.raises(ValueError, match="target a radical/major"):
        ProgressedContactQuery("Moon", "transit", "Sun", "transit", "square")
    with pytest.raises(ValueError, match="max_samples"):
        moira_engine.search_progressed_astrodyne_contacts(
            NATAL,
            datetime(1949, 1, 1, tzinfo=timezone.utc),
            datetime(1950, 1, 1, tzinfo=timezone.utc),
            LATITUDE,
            LONGITUDE,
            _moon_mc_query(),
            max_samples=10,
        )
    with pytest.raises(ValueError, match="later than"):
        moira_engine.integrate_progressed_astrodyne_influence(
            NATAL,
            NATAL,
            NATAL,
            LATITUDE,
            LONGITUDE,
            _moon_mc_query(),
        )
    partial = moira_engine.integrate_progressed_astrodyne_influence(
        NATAL,
        datetime(1949, 8, 29, 12, tzinfo=timezone.utc),
        datetime(1949, 8, 29, 13, tzinfo=timezone.utc),
        LATITUDE,
        LONGITUDE,
        _moon_mc_query(),
        max_step_hours=0.25,
    )
    assert partial.constant_rate_comparator_power_days is None
    assert partial.constant_rate_difference_days is None


def test_search_exports_are_curated() -> None:
    assert moira.ProgressedContactQuery is ProgressedContactQuery
    assert moira.ProgressedTerminalKind is ProgressedTerminalKind
    assert moira.search_progressed_contacts is search_progressed_contacts
    assert moira.integrate_progressed_influence is integrate_progressed_influence
