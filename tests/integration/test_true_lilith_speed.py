from __future__ import annotations

import pytest

from moira.julian import tt_to_ut
from moira.nodes import mean_lilith, true_lilith


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize(
    "jd_tt",
    [
        pytest.param(2451545.0, id="j2000"),
        pytest.param(2461199.9375, id="2026"),
    ],
)
def test_true_lilith_speed_matches_longitude_finite_difference(reader, jd_tt: float) -> None:
    step = 0.002
    jd_ut = tt_to_ut(jd_tt)
    before = true_lilith(tt_to_ut(jd_tt - step), reader=reader).longitude
    after = true_lilith(tt_to_ut(jd_tt + step), reader=reader).longitude
    expected = ((after - before + 180.0) % 360.0 - 180.0) / (2.0 * step)
    actual = true_lilith(jd_ut, reader=reader)
    assert actual.speed == pytest.approx(expected, abs=2.0e-6)


@pytest.mark.requires_ephemeris
def test_true_lilith_speed_is_not_the_mean_lilith_rate(reader) -> None:
    jd_ut = tt_to_ut(2461199.9375)
    true_speed = true_lilith(jd_ut, reader=reader).speed
    mean_speed = mean_lilith(jd_ut, nutation=False).speed
    assert true_speed != pytest.approx(mean_speed, abs=1.0e-6)
