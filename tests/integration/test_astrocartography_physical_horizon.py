"""DE441-backed lunar horizon validation independent of the ACG root solver.

The forward oracle is the canonical sky-position pipeline followed by ERFA
hd2ae at the returned geographic location. This is a geometric covenant, not
an external lunar ephemeris comparison. All angles use true equator/equinox
of date, UT1 epochs and the declared constant centre-altitude horizon.
"""
import math
from datetime import datetime, timezone

import erfa
import pytest

from moira.astrocartography import acg_lines
from moira.julian import apparent_sidereal_time, ut_to_tt
from moira.obliquity import nutation, true_obliquity
from moira.planets import planet_at, sky_position_at


@pytest.mark.parametrize("day", [16, 21, 29])
@pytest.mark.parametrize("refraction", [False, True])
def test_actual_lunar_samples_and_cutoff_match_forward_sky(moira_engine, day, refraction):
    utc = datetime(2026, 6, day, 12, tzinfo=timezone.utc)
    jd_ut = utc.timestamp() / 86400 + 2440587.5
    jd_tt = ut_to_tt(jd_ut)
    gast = apparent_sidereal_time(jd_ut, nutation(jd_tt)[0], true_obliquity(jd_tt))
    reader = moira_engine._reader
    moon = planet_at("Moon", jd_ut, reader=reader, frame="cartesian")
    ra = math.degrees(math.atan2(moon.y, moon.x)) % 360
    dec = math.degrees(math.atan2(moon.z, math.hypot(moon.x, moon.y)))
    horizon = -0.5667 if refraction else 0.0
    curves = [line for line in acg_lines({"Moon": (ra, dec)}, gast, lat_step=1, jd_ut=jd_ut, reader=reader, refraction=refraction) if line.line_type in ("ASC", "DSC")]

    def forward(lat, lon):
        sky = sky_position_at("Moon", jd_ut, lat, lon, reader=reader, refraction=False)
        hour_angle = math.radians(gast + lon - sky.right_ascension)
        return math.degrees(erfa.hd2ae(hour_angle, math.radians(sky.declination), math.radians(lat))[1])

    expected = set()
    for lat in range(-89, 90):
        extrema = [forward(lat, ra - gast + offset) for offset in (0, 180)]
        if min(extrema) <= horizon <= max(extrema):
            expected.add(float(lat))
    for curve in curves:
        assert {lat for lat, _ in curve.points} == expected
        for lat, lon in curve.points:
            assert forward(lat, lon) == pytest.approx(horizon, abs=1e-8)
    if refraction and day == 16:
        assert 64.0 in expected
    if refraction and day == 29:
        assert 62.0 not in expected
