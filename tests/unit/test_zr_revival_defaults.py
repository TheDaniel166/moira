"""ZR default depth and revival peak-grade projection."""

from __future__ import annotations

from moira.timelords import (
    ZRAngularityClass,
    ZRPeakGrade,
    zodiacal_releasing,
    zr_peak_grade,
)


def test_omitted_zr_levels_generate_only_l1_l2() -> None:
    periods = zodiacal_releasing(0.0, 2451545.0)
    assert {period.level for period in periods} == {1, 2}


def test_explicit_zr_level_four_still_works() -> None:
    periods = zodiacal_releasing(0.0, 2451545.0, levels=4)
    assert {period.level for period in periods} == {1, 2, 3, 4}


def test_zr_peak_grade_projection() -> None:
    assert zr_peak_grade(ZRAngularityClass.ANGULAR) == ZRPeakGrade.PEAK
    assert zr_peak_grade(ZRAngularityClass.SUCCEDENT) == ZRPeakGrade.INTERMEDIATE
    assert zr_peak_grade(ZRAngularityClass.CADENT) == ZRPeakGrade.LOW
    assert zr_peak_grade(None) == ZRPeakGrade.NOT_EVALUABLE
