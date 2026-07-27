from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

import moira.profections as _profections_module
from moira.profections import (
    LeapDayAnniversaryPolicy,
    MonthlyProfectionInterval,
    MonthlyProfectionIntervalPolicy,
    ProfectionAmbiguousTimePolicy,
    ProfectionActivationBodyTruth,
    ProfectionActivationStatus,
    ProfectionActivationTruth,
    ProfectionChronology,
    ProfectionChronologyMethod,
    ProfectionIntervalBoundarySemantics,
    annual_profection,
    monthly_profection,
    profection_activation_truth,
    profection_chronology,
    profection_schedule,
)


_PROFECTIONS_PUBLIC_NAMES = (
    "DOMICILE_RULERS",
    "LeapDayAnniversaryPolicy",
    "MonthlyProfectionIntervalPolicy",
    "ProfectionAmbiguousTimePolicy",
    "ProfectionChronologyMethod",
    "ProfectionIntervalBoundarySemantics",
    "ProfectionActivationStatus",
    "ProfectionActivationBodyTruth",
    "ProfectionActivationTruth",
    "MonthlyProfectionInterval",
    "ProfectionChronology",
    "ProfectionResult",
    "profection_activation_truth",
    "profection_chronology",
    "annual_profection",
    "monthly_profection",
    "profection_schedule",
)


def test_schedule_uses_civil_anniversary_not_fractional_julian_year() -> None:
    natal = datetime(2000, 7, 1, 12, 0, tzinfo=timezone.utc)
    current = datetime(2001, 7, 1, 12, 0, tzinfo=timezone.utc)

    result = profection_schedule(0.0, natal, current)

    assert result.age_years == 1
    assert result.age_basis == "civil_anniversary"
    assert result.chronology is not None


def test_chronology_partitions_exact_anniversary_year_without_gaps() -> None:
    natal = datetime(2000, 7, 1, 12, 34, 56, 789012, tzinfo=timezone.utc)
    current = datetime(2024, 12, 1, 0, 0, tzinfo=timezone.utc)

    chronology = profection_chronology(
        17.5,
        natal,
        current,
        civil_timezone="America/New_York",
    )

    assert chronology.age_years == 24
    assert isinstance(chronology, ProfectionChronology)
    assert all(
        isinstance(interval, MonthlyProfectionInterval)
        for interval in chronology.intervals
    )
    assert chronology.civil_timezone == "America/New_York"
    assert chronology.timezone_data_source == "stdlib_zoneinfo"
    assert chronology.timezone_data_version is None
    assert chronology.interval_policy is (
        MonthlyProfectionIntervalPolicy.EQUAL_TWELFTHS_OF_CIVIL_ANNIVERSARY_YEAR
    )
    assert chronology.ambiguous_time_policy is None
    assert chronology.ambiguous_time_resolution_applied is False
    assert chronology.method is ProfectionChronologyMethod.COMPUTATIONAL_PROJECTION
    assert chronology.boundary_semantics is (
        ProfectionIntervalBoundarySemantics.START_INCLUSIVE_END_EXCLUSIVE
    )
    assert len(chronology.intervals) == 12
    assert chronology.intervals[0].start_utc == chronology.annual_start_utc
    assert chronology.intervals[-1].end_utc == chronology.annual_end_utc
    assert all(
        left.end_utc == right.start_utc
        for left, right in zip(
            chronology.intervals,
            chronology.intervals[1:],
        )
    )
    durations = [
        interval.end_utc - interval.start_utc
        for interval in chronology.intervals
    ]
    assert max(durations) - min(durations) <= timedelta(microseconds=1)
    assert tuple(interval.month_index for interval in chronology.intervals) == (
        tuple(range(12))
    )
    assert sum(interval.active for interval in chronology.intervals) == 1
    active = chronology.intervals[chronology.active_month_index]
    assert active.start_utc <= chronology.query_utc < active.end_utc


def test_chronology_preserves_monthly_sign_and_lord_sequence() -> None:
    chronology = profection_chronology(
        17.5,
        datetime(2000, 7, 1, 12, tzinfo=timezone.utc),
        datetime(2024, 12, 1, tzinfo=timezone.utc),
    )
    annual = annual_profection(17.5, chronology.age_years)

    assert [item.lord_of_month for item in chronology.intervals] == (
        annual.monthly_lords
    )
    assert [
        item.profected_longitude for item in chronology.intervals
    ] == pytest.approx(
        [
            (annual.profected_asc_lon + index * 30.0) % 360.0
            for index in range(12)
        ]
    )


def test_chronology_vessels_reject_shifted_sequence_or_result_origin() -> None:
    chronology = profection_chronology(
        17.5,
        datetime(2000, 7, 1, 12, tzinfo=timezone.utc),
        datetime(2024, 12, 1, tzinfo=timezone.utc),
    )
    intervals = list(chronology.intervals)
    intervals[4] = replace(
        intervals[4],
        profected_longitude=intervals[4].profected_longitude + 1.0,
    )
    with pytest.raises(ValueError, match="advance one sign"):
        replace(chronology, intervals=tuple(intervals))

    shifted = replace(
        chronology,
        intervals=tuple(
            replace(
                interval,
                profected_longitude=(interval.profected_longitude + 1.0) % 360.0,
            )
            for interval in chronology.intervals
        ),
    )
    annual = annual_profection(17.5, chronology.age_years)
    with pytest.raises(ValueError, match="begin at profected_asc_lon"):
        replace(
            annual,
            age_basis="civil_anniversary",
            chronology=shifted,
        )


def test_chronology_uses_explicit_iana_zone_after_utc_transport() -> None:
    natal_utc = datetime(2006, 3, 12, 7, 30, tzinfo=timezone.utc)
    query_utc = datetime(2007, 3, 12, 7, 0, tzinfo=timezone.utc)

    utc_result = profection_schedule(0.0, natal_utc, query_utc)
    local_result = profection_schedule(
        0.0,
        natal_utc,
        query_utc,
        civil_timezone="America/New_York",
    )

    assert utc_result.age_years == 0
    assert local_result.age_years == 1
    assert local_result.chronology is not None
    assert local_result.chronology.annual_start_utc == datetime(
        2007,
        3,
        12,
        6,
        30,
        tzinfo=timezone.utc,
    )


def test_chronology_boundary_membership_is_half_open() -> None:
    natal = datetime(2000, 1, 1, 12, tzinfo=timezone.utc)
    initial = profection_chronology(
        0.0,
        natal,
        datetime(2024, 2, 1, tzinfo=timezone.utc),
    )
    exact_boundary = initial.intervals[3].end_utc

    at_boundary = profection_chronology(
        0.0,
        natal,
        exact_boundary,
    )

    assert at_boundary.active_month_index == 4
    assert at_boundary.intervals[4].start_utc == exact_boundary
    assert at_boundary.intervals[4].active is True


def test_chronology_rejects_invalid_zone_policy_and_dst_gap() -> None:
    natal = datetime(2007, 3, 10, 7, 30, tzinfo=timezone.utc)
    current = datetime(2013, 3, 10, 8, 0, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="recognized IANA"):
        profection_chronology(
            0.0,
            natal,
            current,
            civil_timezone="Not/AZone",
        )
    with pytest.raises(ValueError, match="interval_policy"):
        profection_chronology(
            0.0,
            natal,
            current,
            interval_policy="fixed_30_day_months",
        )
    with pytest.raises(ValueError, match="nonexistent local time"):
        profection_chronology(
            0.0,
            natal,
            current,
            civil_timezone="America/New_York",
        )


def test_chronology_requires_explicit_policy_for_repeated_dst_wall_time() -> None:
    natal = datetime(2000, 11, 5, 6, 30, tzinfo=timezone.utc)
    current = datetime(2023, 11, 5, 12, 0, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="ambiguous_time_policy is required"):
        profection_chronology(
            0.0,
            natal,
            current,
            civil_timezone="America/New_York",
        )

    earlier = profection_chronology(
        0.0,
        natal,
        current,
        civil_timezone="America/New_York",
        ambiguous_time_policy=(
            ProfectionAmbiguousTimePolicy.EARLIER_OCCURRENCE
        ),
    )
    later = profection_chronology(
        0.0,
        natal,
        current,
        civil_timezone="America/New_York",
        ambiguous_time_policy=(
            ProfectionAmbiguousTimePolicy.LATER_OCCURRENCE
        ),
    )

    assert earlier.age_years == later.age_years == 23
    assert earlier.annual_start_utc == datetime(
        2023, 11, 5, 5, 30, tzinfo=timezone.utc
    )
    assert later.annual_start_utc == datetime(
        2023, 11, 5, 6, 30, tzinfo=timezone.utc
    )
    assert earlier.ambiguous_time_resolution_applied is True
    assert later.ambiguous_time_resolution_applied is True


@pytest.mark.parametrize(
    "civil_timezone",
    (
        "Africa/Abidjan",
        "America/St_Johns",
        "Asia/Kathmandu",
        "Australia/Adelaide",
        "Pacific/Chatham",
    ),
)
def test_chronology_timezone_matrix_preserves_all_interval_invariants(
    civil_timezone: str,
) -> None:
    chronology = profection_chronology(
        359.999999,
        datetime(1990, 5, 15, 12, 34, 56, tzinfo=timezone.utc),
        datetime(2024, 9, 1, 4, 5, 6, tzinfo=timezone.utc),
        civil_timezone=civil_timezone,
    )

    assert chronology.civil_timezone == civil_timezone
    assert chronology.timezone_data_source == "stdlib_zoneinfo"
    assert len(chronology.intervals) == 12
    assert sum(item.active for item in chronology.intervals) == 1
    assert chronology.intervals[0].start_utc == chronology.annual_start_utc
    assert chronology.intervals[-1].end_utc == chronology.annual_end_utc
    assert all(
        left.end_utc == right.start_utc
        and left.end_jd == right.start_jd
        for left, right in zip(
            chronology.intervals,
            chronology.intervals[1:],
        )
    )


def test_schedule_compares_the_anniversary_in_the_natal_timezone() -> None:
    natal_zone = timezone(timedelta(hours=-5))
    natal = datetime(2000, 7, 1, 23, 0, tzinfo=natal_zone)
    before_local_anniversary = datetime(
        2001,
        7,
        2,
        3,
        30,
        tzinfo=timezone.utc,
    )

    result = profection_schedule(0.0, natal, before_local_anniversary)

    assert result.age_years == 0


def test_schedule_preserves_the_requested_activation_orb() -> None:
    natal = datetime(2000, 7, 1, 12, 0, tzinfo=timezone.utc)
    current = datetime(2000, 7, 1, 12, 0, tzinfo=timezone.utc)

    result = profection_schedule(
        0.0,
        natal,
        current,
        natal_positions={"Sun": 0.5, "Moon": 1.5},
        activation_orb=0.75,
    )

    assert result.activation_truth is not None
    assert result.activation_truth.activation_orb_deg == 0.75
    assert result.activated_planets == ["Sun"]


def test_schedule_rejects_naive_or_prebirth_chronology() -> None:
    aware_natal = datetime(2000, 1, 1, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="timezone-aware"):
        profection_schedule(0.0, datetime(2000, 1, 1), aware_natal)
    with pytest.raises(ValueError, match="before natal"):
        profection_schedule(
            0.0,
            aware_natal,
            datetime(1999, 12, 31, 23, 59, tzinfo=timezone.utc),
        )


def test_february_29_anniversary_policy_is_explicit_and_divergent() -> None:
    natal = datetime(2000, 2, 29, 12, 0, tzinfo=timezone.utc)
    current = datetime(2001, 2, 28, 13, 0, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="leap_day_policy"):
        profection_schedule(0.0, natal, current)

    february_28 = profection_schedule(
        0.0,
        natal,
        current,
        leap_day_policy=LeapDayAnniversaryPolicy.FEBRUARY_28,
    )
    march_1 = profection_schedule(
        0.0,
        natal,
        current,
        leap_day_policy=LeapDayAnniversaryPolicy.MARCH_1,
    )

    assert february_28.age_years == 1
    assert march_1.age_years == 0
    assert (
        february_28.leap_day_policy
        == LeapDayAnniversaryPolicy.FEBRUARY_28
    )
    assert march_1.leap_day_policy == LeapDayAnniversaryPolicy.MARCH_1


def test_activation_truth_distinguishes_missing_from_evaluated_empty() -> None:
    missing = annual_profection(0.0, 0)
    explicit_empty = annual_profection(0.0, 0, natal_positions={})
    evaluated_absence = annual_profection(
        0.0,
        0,
        natal_positions={"Sun": 20.0, "Moon": 340.0},
        activation_orb=5.0,
    )

    assert missing.activated_planets == []
    assert missing.activation_truth is not None
    assert (
        missing.activation_truth.status
        is ProfectionActivationStatus.NOT_EVALUABLE
    )
    assert missing.activation_truth.reason == "natal_positions_not_supplied"

    assert explicit_empty.activated_planets == []
    assert explicit_empty.activation_truth is not None
    assert (
        explicit_empty.activation_truth.status
        is ProfectionActivationStatus.EVALUATED
    )
    assert explicit_empty.activation_truth.supplied_bodies == ()

    assert evaluated_absence.activated_planets == []
    assert evaluated_absence.activation_truth is not None
    assert (
        evaluated_absence.activation_truth.status
        is ProfectionActivationStatus.EVALUATED
    )
    assert evaluated_absence.activation_truth.supplied_bodies == (
        "Sun",
        "Moon",
    )


def test_activation_truth_preserves_body_distances_and_projection_order() -> None:
    truth = profection_activation_truth(
        359.0,
        {
            "Mars": 1.0,
            "Sun": 10.0,
            "Moon": 354.0,
        },
        activation_orb=5.0,
    )

    assert truth.status is ProfectionActivationStatus.EVALUATED
    assert truth.supplied_bodies == ("Mars", "Sun", "Moon")
    assert truth.activated_planets == ("Mars", "Moon")
    assert [
        item.distance_from_profected_asc_deg for item in truth.body_truths
    ] == pytest.approx([2.0, 11.0, 5.0])


def test_activation_truth_vessels_reject_contradictory_or_missing_truth() -> None:
    body = ProfectionActivationBodyTruth(
        body="Mars",
        natal_longitude=1.0,
        distance_from_profected_asc_deg=2.0,
        activated=True,
    )
    with pytest.raises(ValueError, match="must match distance and orb"):
        ProfectionActivationTruth(
            status=ProfectionActivationStatus.EVALUATED,
            profected_asc_lon=359.0,
            activation_orb_deg=1.0,
            body_truths=(body,),
        )
    with pytest.raises(ValueError, match="no body truth"):
        ProfectionActivationTruth(
            status=ProfectionActivationStatus.NOT_EVALUABLE,
            profected_asc_lon=359.0,
            activation_orb_deg=5.0,
            body_truths=(body,),
            reason="natal_positions_not_supplied",
        )
    with pytest.raises(ValueError, match="body distance must match"):
        ProfectionActivationTruth(
            status=ProfectionActivationStatus.EVALUATED,
            profected_asc_lon=359.0,
            activation_orb_deg=5.0,
            body_truths=(
                ProfectionActivationBodyTruth(
                    body="Mars",
                    natal_longitude=1.0,
                    distance_from_profected_asc_deg=3.0,
                    activated=True,
                ),
            ),
        )
    with pytest.raises(ValueError, match="natal_positions_not_supplied"):
        ProfectionActivationTruth(
            status=ProfectionActivationStatus.NOT_EVALUABLE,
            profected_asc_lon=359.0,
            activation_orb_deg=5.0,
            reason="unknown",
        )


def test_direct_profection_entrypoints_reject_out_of_contract_inputs() -> None:
    for invalid_asc in (float("nan"), float("inf"), True):
        with pytest.raises((TypeError, ValueError), match="natal_asc"):
            annual_profection(invalid_asc, 0)
    for invalid_age in (-1, 1.5, True):
        with pytest.raises(ValueError, match="age_years"):
            annual_profection(0.0, invalid_age)  # type: ignore[arg-type]
    for invalid_month in (-1, 12, 1.5, True):
        with pytest.raises(ValueError, match="month_index"):
            monthly_profection(
                0.0,
                0,
                invalid_month,  # type: ignore[arg-type]
            )


def test_profection_result_vessel_rejects_contradictory_projections() -> None:
    result = annual_profection(
        0.0,
        12,
        natal_positions={"Sun": 0.0},
    )

    with pytest.raises(ValueError, match="profected_house"):
        replace(result, profected_house=2)
    with pytest.raises(ValueError, match="monthly_lords"):
        replace(
            result,
            monthly_lords=["Mars"] * 12,
        )
    with pytest.raises(ValueError, match="activation_truth"):
        replace(result, activation_truth=None)
    with pytest.raises(ValueError, match="civil-anniversary"):
        replace(result, age_basis="civil_anniversary")


def test_profections_public_surface_is_explicit_and_duplicate_free() -> None:
    assert tuple(_profections_module.__all__) == _PROFECTIONS_PUBLIC_NAMES
    assert len(_profections_module.__all__) == len(
        set(_profections_module.__all__)
    )
