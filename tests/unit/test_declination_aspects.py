"""First-class declination aspect and motion doctrine tests."""

from dataclasses import FrozenInstanceError

import pytest

import moira
import moira.aspects as legacy_aspects
from moira.declination_aspects import (
    DeclinationAspect,
    DeclinationAspectKind,
    DeclinationAspectPolicy,
    DeclinationMotionState,
    declination_aspect_motion_witness,
    find_declination_aspects,
)


FRAME = "geocentric_equatorial_of_date"
TIMESCALE = "TT"


def _witness(**overrides):
    values = {
        "body1": "A",
        "declination1_deg": 10.0,
        "body2": "B",
        "declination2_deg": 10.5,
        "aspect": "Parallel",
        "speed1_deg_per_day": 0.2,
        "speed2_deg_per_day": -0.1,
        "reference_frame": FRAME,
        "timescale": TIMESCALE,
    }
    values.update(overrides)
    return declination_aspect_motion_witness(**values)


def test_declination_module_owns_vessel_with_legacy_identity_preserved() -> None:
    assert DeclinationAspect.__module__ == "moira.declination_aspects"
    assert legacy_aspects.DeclinationAspect is DeclinationAspect
    assert moira.DeclinationAspect is DeclinationAspect
    assert (
        legacy_aspects.find_declination_aspects({"A": 10.0, "B": 10.2})
        == find_declination_aspects({"A": 10.0, "B": 10.2})
    )


def test_declination_policy_is_explicit_frozen_and_validated() -> None:
    policy = DeclinationAspectPolicy(
        orb=0.75,
        exact_tolerance_deg=1e-8,
        rate_tolerance_deg_per_day=1e-10,
    )
    assert policy.orb == 0.75
    assert policy.hemisphere_policy.value.startswith("parallel_same")
    assert policy.equator_policy.value.startswith("two_equatorial")
    with pytest.raises(FrozenInstanceError):
        policy.orb = 2.0  # type: ignore[misc]
    with pytest.raises(ValueError, match="orb must be non-negative"):
        DeclinationAspectPolicy(orb=-0.1)
    with pytest.raises(ValueError, match="finite"):
        DeclinationAspectPolicy(rate_tolerance_deg_per_day=float("nan"))


def test_parallel_motion_uses_signed_declination_difference() -> None:
    witness = _witness()
    assert witness.aspect is DeclinationAspectKind.PARALLEL
    assert witness.signed_error_deg == pytest.approx(-0.5)
    assert witness.relative_speed_deg_per_day == pytest.approx(0.3)
    assert witness.orb_rate_deg_per_day == pytest.approx(-0.3)
    assert witness.state is DeclinationMotionState.APPLYING
    assert witness.within_orb is True

    separating = _witness(
        speed1_deg_per_day=-0.2,
        speed2_deg_per_day=0.1,
    )
    assert separating.orb_rate_deg_per_day == pytest.approx(0.3)
    assert separating.state is DeclinationMotionState.SEPARATING


def test_contra_parallel_motion_uses_signed_declination_sum() -> None:
    applying = _witness(
        declination2_deg=-10.5,
        aspect="Contra-Parallel",
        speed1_deg_per_day=0.2,
        speed2_deg_per_day=0.1,
    )
    assert applying.aspect is DeclinationAspectKind.CONTRA_PARALLEL
    assert applying.signed_error_deg == pytest.approx(-0.5)
    assert applying.relative_speed_deg_per_day == pytest.approx(0.3)
    assert applying.orb_rate_deg_per_day == pytest.approx(-0.3)
    assert applying.state is DeclinationMotionState.APPLYING

    separating = _witness(
        declination2_deg=-10.5,
        aspect="Contra-Parallel",
        speed1_deg_per_day=-0.2,
        speed2_deg_per_day=-0.1,
    )
    assert separating.orb_rate_deg_per_day == pytest.approx(0.3)
    assert separating.state is DeclinationMotionState.SEPARATING


def test_exact_missing_and_relative_stall_states_are_distinct() -> None:
    exact = _witness(
        declination2_deg=10.0,
        speed1_deg_per_day=None,
        speed2_deg_per_day=None,
    )
    assert exact.state is DeclinationMotionState.EXACT
    assert exact.orb_rate_deg_per_day is None

    indeterminate = _witness(
        speed1_deg_per_day=None,
        speed2_deg_per_day=None,
    )
    assert indeterminate.state is DeclinationMotionState.INDETERMINATE
    assert indeterminate.relative_motion_stalled is None

    stalled = _witness(speed1_deg_per_day=0.2, speed2_deg_per_day=0.2)
    assert stalled.state is DeclinationMotionState.STATIONARY
    assert stalled.relative_motion_stalled is True


def test_individual_zero_declination_speed_does_not_force_stationary() -> None:
    witness = _witness(speed1_deg_per_day=0.0, speed2_deg_per_day=-0.1)
    assert witness.relative_speed_deg_per_day == pytest.approx(0.1)
    assert witness.state is DeclinationMotionState.APPLYING


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"body2": "A"}, "distinct"),
        ({"declination1_deg": 91.0}, "declination1_deg"),
        ({"speed1_deg_per_day": float("inf")}, "finite"),
        ({"aspect": "Square"}, "Parallel"),
        ({"declination2_deg": -10.5}, "not eligible"),
        ({"reference_frame": " frame"}, "trimmed"),
    ],
)
def test_motion_witness_rejects_invalid_or_unowned_geometry(
    overrides,
    message,
) -> None:
    with pytest.raises(ValueError, match=message):
        _witness(**overrides)


def test_facade_admits_first_class_declination_motion() -> None:
    witness = moira.Moira(
        kernel_path="missing-test-kernel.bsp"
    ).declination_aspect_motion_witness(
        "A",
        10.0,
        "B",
        10.5,
        "Parallel",
        speed1_deg_per_day=0.2,
        speed2_deg_per_day=-0.1,
        reference_frame=FRAME,
        timescale=TIMESCALE,
    )
    assert witness.state is DeclinationMotionState.APPLYING
    assert witness.reference_frame == FRAME
    assert witness.timescale == TIMESCALE

