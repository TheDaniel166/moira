"""Source-timed 2003 path point versus the native time-union interior."""
import pytest

from moira.julian import julian_day
from moira.solar_swept_witness import inspect_swept_central_interior

pytestmark = [pytest.mark.requires_ephemeris, pytest.mark.slow]


def test_2003_published_north_point_is_interior_later(eclipse_calculator):
    # NASA table 1.3, 04:08 UT, north point 64°01.6'N 28°00.0'W:
    # https://eclipse.gsfc.nasa.gov/SEpubs/20030000/tables/table_1.3.html
    # Coordinates are rounded and reference model/time policy is different.
    # This is an independent native-model interior witness, not NASA parity.
    t = julian_day(2003, 5, 31, 4 + 8/60)
    interval = (t, t + 120/86400)
    point = (64.02666666666667, -28.0)
    first = inspect_swept_central_interior(eclipse_calculator, *point, [t], interval_ut1=interval)
    assert first.status == 'unresolved'
    assert first.samples[0].geometry.sun_altitude_rad < 0
    result = inspect_swept_central_interior(eclipse_calculator, *point, [t, t + 60/86400], interval_ut1=interval)
    assert result.status == 'interior_witness' and not result.complete
    assert result.witness.jd_ut1 == t + 60/86400
    assert result.witness.ephemeris == 'DE-0441LE-0441'
    assert result.witness.geometry.phase == 'annular'
    assert result.witness.geometry.central_margin_rad > 1e-12
    assert result.witness.geometry.sun_altitude_rad > 1e-12
    assert result.interval_ut1 == interval
