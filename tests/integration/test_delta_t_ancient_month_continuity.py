"""Kernel-backed continuity witness for the JD-aware Delta-T repair."""

from __future__ import annotations

import pytest

from moira.constants import Body
from moira.julian import DeltaTPolicy, julian_day
from moira.planets import planet_at


_ONE_SECOND_JD = 1.0 / 86400.0
_MAX_ONE_SECOND_MOON_STEP_ARCSEC = 1.0
_MAX_ADJACENT_STEP_MISMATCH_ARCSEC = 0.001


def _signed_angle_delta(start_deg: float, end_deg: float) -> float:
    return (end_deg - start_deg + 180.0) % 360.0 - 180.0


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize(
    "delta_t_policy",
    [None, DeltaTPolicy(model="physical")],
    ids=["hybrid", "physical"],
)
def test_moon_path_is_monotonic_across_ancient_month_boundary(
    reader,
    delta_t_policy: DeltaTPolicy | None,
) -> None:
    """The public planetary path must not inherit a calendar-month TT step.

    At the proleptic-Gregorian boundary -1000-02-01, the former NASA-style
    month-midpoint year hint made TT move backward across a one-second UT1
    interval.  The Moon is a sensitive end-to-end witness because
    ``planet_at`` performs the UT1-to-TT conversion before reading the
    admitted planetary kernel and applying the apparent-position reduction.
    """

    boundary_ut1 = julian_day(-1000, 2, 1, 0.0)
    sample_ut1 = (
        boundary_ut1 - _ONE_SECOND_JD,
        boundary_ut1,
        boundary_ut1 + _ONE_SECOND_JD,
    )
    longitudes = [
        planet_at(
            Body.MOON,
            jd_ut1,
            reader=reader,
            delta_t_policy=delta_t_policy,
        ).longitude
        for jd_ut1 in sample_ut1
    ]
    steps_arcsec = [
        _signed_angle_delta(start, end) * 3600.0
        for start, end in zip(longitudes, longitudes[1:])
    ]

    assert all(
        0.0 < step < _MAX_ONE_SECOND_MOON_STEP_ARCSEC
        for step in steps_arcsec
    ), f"non-monotonic or discontinuous Moon steps: {steps_arcsec!r} arcsec"
    assert abs(steps_arcsec[1] - steps_arcsec[0]) < _MAX_ADJACENT_STEP_MISMATCH_ARCSEC
