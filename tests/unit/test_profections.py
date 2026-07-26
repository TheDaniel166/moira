from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

import moira.profections as _profections_module
from moira.profections import (
    LeapDayAnniversaryPolicy,
    ProfectionActivationBodyTruth,
    ProfectionActivationStatus,
    ProfectionActivationTruth,
    annual_profection,
    profection_activation_truth,
    profection_schedule,
)


_PROFECTIONS_PUBLIC_NAMES = (
    "DOMICILE_RULERS",
    "LeapDayAnniversaryPolicy",
    "ProfectionActivationStatus",
    "ProfectionActivationBodyTruth",
    "ProfectionActivationTruth",
    "ProfectionResult",
    "profection_activation_truth",
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


def test_profections_public_surface_is_explicit_and_duplicate_free() -> None:
    assert tuple(_profections_module.__all__) == _PROFECTIONS_PUBLIC_NAMES
    assert len(_profections_module.__all__) == len(
        set(_profections_module.__all__)
    )
