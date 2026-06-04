from __future__ import annotations

import math

import pytest

from moira._house_quality import (
    HouseDistortionProfile,
    house_cycle_verdict,
    house_distortion_profile,
    practically_admissible_cusp_cycle,
    stable_true_flags,
    strictly_ordered_cusp_cycle,
)


def test_strictly_ordered_cusp_cycle_accepts_equal_30_degree_cycle() -> None:
    cusps = tuple(float(i * 30) for i in range(12))

    assert strictly_ordered_cusp_cycle(cusps) is True


def test_strictly_ordered_cusp_cycle_rejects_reversal() -> None:
    cusps = (
        0.0,
        40.0,
        20.0,
        90.0,
        120.0,
        150.0,
        180.0,
        210.0,
        240.0,
        270.0,
        300.0,
        330.0,
    )

    assert strictly_ordered_cusp_cycle(cusps) is False


def test_strictly_ordered_cusp_cycle_rejects_closure_gap_below_tolerance() -> None:
    cusps = (
        0.0,
        30.0,
        60.0,
        90.0,
        120.0,
        150.0,
        180.0,
        210.0,
        240.0,
        270.0,
        300.0,
        359.999999999,
    )

    assert strictly_ordered_cusp_cycle(cusps, ordering_tolerance=1e-7) is False


def test_strictly_ordered_cusp_cycle_rejects_wrong_cusp_count() -> None:
    with pytest.raises(ValueError, match="exactly 12"):
        strictly_ordered_cusp_cycle((0.0,) * 11)


def test_house_distortion_profile_reports_uniform_cycle() -> None:
    profile = house_distortion_profile(tuple(float(i * 30) for i in range(12)))

    assert isinstance(profile, HouseDistortionProfile)
    assert profile.widths == pytest.approx((30.0,) * 12, abs=1e-12)
    assert profile.min_width == pytest.approx(30.0, abs=1e-12)
    assert profile.max_width == pytest.approx(30.0, abs=1e-12)
    assert profile.distortion_ratio == pytest.approx(1.0, abs=1e-12)
    assert profile.narrow_houses == tuple(range(1, 13))
    assert profile.wide_houses == tuple(range(1, 13))


def test_house_distortion_profile_reports_balloon_and_crush() -> None:
    cusps = (
        0.0,
        10.0,
        30.0,
        60.0,
        90.0,
        120.0,
        180.0,
        190.0,
        210.0,
        240.0,
        270.0,
        300.0,
    )

    profile = house_distortion_profile(cusps)

    assert profile.widths == pytest.approx(
        (10.0, 20.0, 30.0, 30.0, 30.0, 60.0, 10.0, 20.0, 30.0, 30.0, 30.0, 60.0),
        abs=1e-12,
    )
    assert profile.min_width == pytest.approx(10.0, abs=1e-12)
    assert profile.max_width == pytest.approx(60.0, abs=1e-12)
    assert profile.distortion_ratio == pytest.approx(6.0, abs=1e-12)
    assert profile.narrow_houses == (1, 7)
    assert profile.wide_houses == (6, 12)


def test_house_distortion_profile_returns_infinite_ratio_for_collapsed_house() -> None:
    cusps = (
        0.0,
        0.0,
        30.0,
        60.0,
        90.0,
        120.0,
        180.0,
        210.0,
        240.0,
        270.0,
        300.0,
        330.0,
    )

    profile = house_distortion_profile(cusps)

    assert profile.min_width == pytest.approx(0.0, abs=1e-12)
    assert math.isinf(profile.distortion_ratio)


def test_practically_admissible_cusp_cycle_uses_ratio_ceiling() -> None:
    cusps = (
        0.0,
        10.0,
        30.0,
        60.0,
        90.0,
        120.0,
        180.0,
        190.0,
        210.0,
        240.0,
        270.0,
        300.0,
    )

    admissible_loose, profile_loose = practically_admissible_cusp_cycle(cusps, rho_max=6.0)
    admissible_tight, profile_tight = practically_admissible_cusp_cycle(cusps, rho_max=3.4)

    assert admissible_loose is True
    assert admissible_tight is False
    assert profile_loose == profile_tight
    assert profile_loose.distortion_ratio == pytest.approx(6.0, abs=1e-12)


def test_practically_admissible_cusp_cycle_rejects_invalid_rho_ceiling() -> None:
    with pytest.raises(ValueError, match="rho_max must be >= 1.0"):
        practically_admissible_cusp_cycle(tuple(float(i * 30) for i in range(12)), rho_max=0.999)


def test_house_cycle_verdict_reports_unordered_without_profile() -> None:
    cusps = (
        0.0,
        40.0,
        20.0,
        90.0,
        120.0,
        150.0,
        180.0,
        210.0,
        240.0,
        270.0,
        300.0,
        330.0,
    )

    verdict, profile = house_cycle_verdict(cusps, rho_max=6.0)

    assert verdict == "unordered"
    assert profile is None


def test_house_cycle_verdict_reports_ordered_but_impractical() -> None:
    cusps = (
        0.0,
        10.0,
        30.0,
        60.0,
        90.0,
        120.0,
        180.0,
        190.0,
        210.0,
        240.0,
        270.0,
        300.0,
    )

    verdict, profile = house_cycle_verdict(cusps, rho_max=3.4)

    assert verdict == "ordered_but_impractical"
    assert profile is not None
    assert profile.distortion_ratio == pytest.approx(6.0, abs=1e-12)


def test_house_cycle_verdict_reports_practically_admissible() -> None:
    cusps = tuple(float(i * 30) for i in range(12))

    verdict, profile = house_cycle_verdict(cusps, rho_max=1.1)

    assert verdict == "practically_admissible"
    assert profile is not None
    assert profile.distortion_ratio == pytest.approx(1.0, abs=1e-12)


def test_stable_true_flags_requires_full_true_neighborhood() -> None:
    flags = (False, True, True, True, False, True, True)

    assert stable_true_flags(flags, radius=0) == flags
    assert stable_true_flags(flags, radius=1) == (False, False, True, False, False, False, False)


def test_stable_true_flags_rejects_negative_radius() -> None:
    with pytest.raises(ValueError, match="radius must be >= 0"):
        stable_true_flags((True, True), radius=-1)
