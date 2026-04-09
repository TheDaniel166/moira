from __future__ import annotations

import pytest

from moira.constants import Body
from moira.julian import DeltaTPolicy, tt_to_ut
from moira.planets import sky_position_at
from moira.spk_reader import get_reader
from tools.horizons import observer_sky_position

_JD_TT = 2459205.25
_OBSERVER_LAT = 51.5
_OBSERVER_LON = -0.1
_EXTERNAL_TOLERANCE_DEG = 1e-3


def _signed_angle_delta(start_deg: float, end_deg: float) -> float:
    return ((end_deg - start_deg + 180.0) % 360.0) - 180.0


def _direct_topocentric_sky_position(body: str):
    jd_ut = tt_to_ut(_JD_TT)
    delta_t_seconds = (_JD_TT - jd_ut) * 86400.0
    policy = DeltaTPolicy(model="fixed", fixed_delta_t=delta_t_seconds)
    return sky_position_at(
        body,
        jd_ut,
        observer_lat=_OBSERVER_LAT,
        observer_lon=_OBSERVER_LON,
        observer_elev_m=0.0,
        reader=get_reader(),
        delta_t_policy=policy,
    )


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.requires_ephemeris
@pytest.mark.slow
def test_jupiter_saturn_topocentric_direct_path_matches_horizons_tt_anchor() -> None:
    offsets: list[tuple[str, float, float]] = []

    for body, command in ((Body.JUPITER, "599"), (Body.SATURN, "699")):
        moira = _direct_topocentric_sky_position(body)
        ref = observer_sky_position(
            command,
            _JD_TT,
            longitude_deg=_OBSERVER_LON,
            latitude_deg=_OBSERVER_LAT,
            elevation_km=0.0,
            time_type="TT",
        )

        ra_delta_deg = _signed_angle_delta(moira.right_ascension, ref.right_ascension)
        dec_delta_deg = ref.declination - moira.declination
        offsets.append((body, ra_delta_deg, dec_delta_deg))

        assert abs(ra_delta_deg) < _EXTERNAL_TOLERANCE_DEG, (
            body,
            ra_delta_deg,
            ref.right_ascension,
            moira.right_ascension,
        )
        assert abs(dec_delta_deg) < _EXTERNAL_TOLERANCE_DEG, (
            body,
            dec_delta_deg,
            ref.declination,
            moira.declination,
        )

    assert offsets[0][1] * offsets[1][1] > 0.0, offsets
    assert offsets[0][2] * offsets[1][2] > 0.0, offsets