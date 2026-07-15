"""First-class signed longitude-aspect motion witnesses."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

import moira
from moira.aspects import (
    AspectMotionBranch,
    AspectMotionOrbPolicy,
    AspectMotionState,
    AspectMotionStationaryReason,
    AspectMotionWitness,
    aspect_motion_witness,
)


_PROVENANCE = {
    "reference_frame": "geocentric_ecliptic_of_date",
    "timescale": "TT",
}


def _witness(**overrides) -> AspectMotionWitness:
    arguments = {
        "body1": "Sun",
        "longitude1_deg": 359.0,
        "body2": "Moon",
        "longitude2_deg": 1.0,
        "aspect": "Conjunction",
        "speed1_deg_per_day": 2.0,
        "speed2_deg_per_day": 1.0,
        **_PROVENANCE,
    }
    arguments.update(overrides)
    return aspect_motion_witness(**arguments)


def test_wraparound_branch_exposes_signed_error_rate_and_applying_state() -> None:
    result = _witness()

    assert result.directed_separation_deg == pytest.approx(2.0, abs=1e-12)
    assert result.target_directed_separation_deg == 0.0
    assert result.directed_error_deg == pytest.approx(2.0, abs=1e-12)
    assert result.relative_speed_deg_per_day == -1.0
    assert result.orb_rate_deg_per_day == -1.0
    assert result.state is AspectMotionState.APPLYING
    assert result.within_orb is True
    assert result.orb_policy is AspectMotionOrbPolicy.CANONICAL_DEFAULT_SCALED


def test_reversed_relative_motion_is_separating() -> None:
    result = _witness(speed1_deg_per_day=1.0, speed2_deg_per_day=2.0)

    assert result.orb_rate_deg_per_day == 1.0
    assert result.state is AspectMotionState.SEPARATING


def test_negative_aspect_branch_is_selected_without_losing_direction() -> None:
    result = _witness(
        longitude1_deg=1.0,
        longitude2_deg=359.0,
        speed1_deg_per_day=1.0,
        speed2_deg_per_day=2.0,
    )

    assert result.directed_separation_deg == pytest.approx(-2.0, abs=1e-12)
    assert result.directed_error_deg == pytest.approx(-2.0, abs=1e-12)
    assert result.relative_speed_deg_per_day == 1.0
    assert result.orb_rate_deg_per_day == -1.0
    assert result.state is AspectMotionState.APPLYING


@pytest.mark.parametrize(
    ("longitude2", "aspect", "target"),
    [(60.0, "Sextile", 60.0), (180.0, "Opposition", -180.0)],
)
def test_exactness_is_geometric_even_without_speed_data(
    longitude2: float,
    aspect: str,
    target: float,
) -> None:
    result = _witness(
        longitude1_deg=0.0,
        longitude2_deg=longitude2,
        aspect=aspect,
        speed1_deg_per_day=None,
        speed2_deg_per_day=None,
    )

    assert result.target_directed_separation_deg == target
    assert result.orb_deg == pytest.approx(0.0, abs=1e-12)
    assert result.state is AspectMotionState.EXACT
    assert result.relative_speed_deg_per_day is None
    assert result.orb_rate_deg_per_day is None


def test_exact_tolerance_is_explicit_and_caller_owned() -> None:
    result = _witness(
        longitude1_deg=0.0,
        longitude2_deg=60.0005,
        aspect="Sextile",
        exact_tolerance_deg=0.001,
    )

    assert result.orb_deg == pytest.approx(0.0005, abs=1e-12)
    assert result.exact_tolerance_deg == 0.001
    assert result.state is AspectMotionState.EXACT


def test_missing_one_speed_is_indeterminate_not_fabricated() -> None:
    result = _witness(speed2_deg_per_day=None)

    assert result.state is AspectMotionState.INDETERMINATE
    assert result.relative_speed_deg_per_day is None
    assert result.relative_motion_stalled is None
    assert result.body1_stationary is False
    assert result.body2_stationary is None


def test_equidistant_nonconjunction_branches_remain_indeterminate() -> None:
    result = _witness(
        longitude1_deg=15.0,
        longitude2_deg=15.0,
        aspect="Square",
    )

    assert result.branch_selection is AspectMotionBranch.AMBIGUOUS_AT_ZERO_SEPARATION
    assert result.target_directed_separation_deg is None
    assert result.directed_error_deg is None
    assert result.orb_deg == 90.0
    assert result.orb_rate_deg_per_day is None
    assert result.state is AspectMotionState.INDETERMINATE


def test_body_station_and_relative_standstill_have_visible_reasons() -> None:
    body_station = _witness(speed1_deg_per_day=0.0, speed2_deg_per_day=1.0)
    relative_standstill = _witness(speed1_deg_per_day=1.0, speed2_deg_per_day=1.0)

    assert body_station.state is AspectMotionState.STATIONARY
    assert body_station.stationary_reasons == (
        AspectMotionStationaryReason.BODY1_BELOW_THRESHOLD,
    )
    assert body_station.body1_stationary_threshold_deg_per_day > 0.0

    assert relative_standstill.state is AspectMotionState.STATIONARY
    assert relative_standstill.relative_motion_stalled is True
    assert relative_standstill.stationary_reasons == (
        AspectMotionStationaryReason.RELATIVE_RATE_WITHIN_TOLERANCE,
    )


def test_orb_policy_reports_admission_without_suppressing_motion_truth() -> None:
    result = _witness(
        longitude1_deg=0.0,
        longitude2_deg=70.0,
        aspect="Sextile",
        orb_factor=0.5,
    )

    assert result.orb_deg == 10.0
    assert result.allowed_orb_deg == 2.5
    assert result.within_orb is False
    assert result.state is AspectMotionState.APPLYING


def test_witness_is_immutable_and_preserves_declared_provenance() -> None:
    result = _witness()

    assert result.reference_frame == "geocentric_ecliptic_of_date"
    assert result.timescale == "TT"
    assert result.evaluation_scope == "instantaneous_no_event_search"
    with pytest.raises(FrozenInstanceError):
        result.state = AspectMotionState.EXACT  # type: ignore[misc]


def test_witness_is_public_through_root_and_facade() -> None:
    assert moira.AspectMotionBranch is AspectMotionBranch
    assert moira.AspectMotionOrbPolicy is AspectMotionOrbPolicy
    assert moira.AspectMotionState is AspectMotionState
    assert moira.AspectMotionStationaryReason is AspectMotionStationaryReason
    assert moira.AspectMotionWitness is AspectMotionWitness
    assert moira.aspect_motion_witness is aspect_motion_witness

    result = moira.Moira().aspect_motion_witness(
        "Sun",
        359.0,
        "Moon",
        1.0,
        "Conjunction",
        speed1_deg_per_day=2.0,
        speed2_deg_per_day=1.0,
        **_PROVENANCE,
    )

    assert result.state is AspectMotionState.APPLYING


@pytest.mark.parametrize(
    "overrides",
    [
        {"body1": ""},
        {"body2": "Sun"},
        {"longitude1_deg": float("nan")},
        {"speed1_deg_per_day": float("inf")},
        {"aspect": "Not an aspect"},
        {"orb_factor": 0.0},
        {"exact_tolerance_deg": -1.0},
        {"rate_tolerance_deg_per_day": -1.0},
        {"reference_frame": ""},
        {"timescale": " TT"},
    ],
)
def test_invalid_or_ambiguous_inputs_are_rejected(overrides) -> None:
    with pytest.raises(ValueError):
        _witness(**overrides)
