from __future__ import annotations

import pytest

from moira.constants import Body
from moira.julian import DeltaTPolicy, tt_to_ut
from moira.planets import sky_position_at
from moira.spk_reader import get_reader
from tools.horizons import observer_sky_position

_CASES = (
    ("sun_j2000_greenwich", Body.SUN, "10", 2451545.0, 51.5, -0.1),
    ("moon_j2000_newyork", Body.MOON, "301", 2451545.0, 40.7128, -74.0060),
    ("mars_j2000_sydney", Body.MARS, "499", 2451545.0, -33.8688, 151.2093),
    ("mercury_2020_equator", Body.MERCURY, "199", 2459205.25, 0.0, -78.5),
    ("venus_2020_equator", Body.VENUS, "299", 2459205.25, 0.0, -78.5),
    ("jupiter_2020_greenwich", Body.JUPITER, "599", 2459205.25, 51.5, -0.1),
    ("saturn_2020_reykjavik", Body.SATURN, "699", 2459205.25, 64.1466, -21.9426),
    ("uranus_2020_reykjavik", Body.URANUS, "799", 2459205.25, 64.1466, -21.9426),
    ("neptune_2020_sydney", Body.NEPTUNE, "899", 2459205.25, -33.8688, 151.2093),
    ("pluto_2020_greenwich", Body.PLUTO, "999", 2459205.25, 51.5, -0.1),
)
_EXTERNAL_TOLERANCE_DEG = 1e-4


def _signed_angle_delta(start_deg: float, end_deg: float) -> float:
    return ((end_deg - start_deg + 180.0) % 360.0) - 180.0


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.requires_ephemeris
@pytest.mark.slow
@pytest.mark.parametrize(
    ("label", "body", "command", "jd_tt", "latitude_deg", "longitude_deg"),
    _CASES,
    ids=[case[0] for case in _CASES],
)
def test_direct_topocentric_positions_match_horizons_across_breadth_gauntlet(
    label: str,
    body: str,
    command: str,
    jd_tt: float,
    latitude_deg: float,
    longitude_deg: float,
) -> None:
    reader = get_reader()
    jd_ut = tt_to_ut(jd_tt)
    delta_t_seconds = (jd_tt - jd_ut) * 86400.0
    policy = DeltaTPolicy(model="fixed", fixed_delta_t=delta_t_seconds)

    moira = sky_position_at(
        body,
        jd_ut,
        observer_lat=latitude_deg,
        observer_lon=longitude_deg,
        observer_elev_m=0.0,
        reader=reader,
        delta_t_policy=policy,
    )
    ref = observer_sky_position(
        command,
        jd_tt,
        longitude_deg=longitude_deg,
        latitude_deg=latitude_deg,
        elevation_km=0.0,
        time_type="TT",
    )

    ra_delta_deg = _signed_angle_delta(moira.right_ascension, ref.right_ascension)
    dec_delta_deg = ref.declination - moira.declination

    assert abs(ra_delta_deg) < _EXTERNAL_TOLERANCE_DEG, (label, ra_delta_deg)
    assert abs(dec_delta_deg) < _EXTERNAL_TOLERANCE_DEG, (label, dec_delta_deg)