import math

import pytest

from moira.constants import Body
from moira.coordinates import ecliptic_to_equatorial, equatorial_to_ecliptic
from moira.julian import DeltaTPolicy, local_sidereal_time, tt_to_ut
from moira.obliquity import mean_obliquity, nutation
from moira.planets import planet_at, sky_position_at
from moira.spk_reader import get_reader

_EPOCHS_TT = {
    "1000_bce": 1355818.0,
    "j2000": 2451545.0,
    "jupiter_saturn_2020": 2459205.25,
    "3000_ad": 2816788.0,
}
_OBSERVERS = {
    "greenwich": (51.5, -0.1),
    "equator": (0.0, -78.5),
    "sydney": (-33.8688, 151.2093),
    "reykjavik": (64.1466, -21.9426),
}
_PUBLIC_BODIES = (
    Body.SUN,
    Body.MOON,
    Body.MERCURY,
    Body.VENUS,
    Body.MARS,
    Body.JUPITER,
    Body.SATURN,
    Body.URANUS,
    Body.NEPTUNE,
    Body.PLUTO,
)
_ONE_SECOND_JD = 1.0 / 86400.0
_ROUTE_AGREEMENT_TOLERANCE_DEG = 1e-9
_ROUND_TRIP_TOLERANCE_DEG = 1e-10
_SMOOTHNESS_ABS_TOLERANCE_DEG = 5e-7
_SMOOTHNESS_REL_TOLERANCE = 0.01


def _signed_angle_delta(start_deg: float, end_deg: float) -> float:
    return ((end_deg - start_deg + 180.0) % 360.0) - 180.0


def _tt_pinned_epoch(jd_tt: float, longitude_deg: float) -> tuple[float, DeltaTPolicy, float, float]:
    jd_ut = tt_to_ut(jd_tt)
    delta_t_seconds = (jd_tt - jd_ut) * 86400.0
    policy = DeltaTPolicy(model="fixed", fixed_delta_t=delta_t_seconds)
    dpsi_deg, deps_deg = nutation(jd_tt)
    obliquity_deg = mean_obliquity(jd_tt) + deps_deg
    lst_deg = local_sidereal_time(jd_ut, longitude_deg, dpsi_deg, obliquity_deg)
    return jd_ut, policy, obliquity_deg, lst_deg


@pytest.mark.requires_ephemeris
def test_topocentric_route_agreement_holds_across_breadth_matrix() -> None:
    reader = get_reader()

    for epoch_name, jd_tt in _EPOCHS_TT.items():
        for observer_name, (latitude_deg, longitude_deg) in _OBSERVERS.items():
            jd_ut, policy, obliquity_deg, lst_deg = _tt_pinned_epoch(jd_tt, longitude_deg)

            for body in _PUBLIC_BODIES:
                direct = sky_position_at(
                    body,
                    jd_ut,
                    latitude_deg,
                    longitude_deg,
                    reader=reader,
                    delta_t_policy=policy,
                )
                routed = planet_at(
                    body,
                    jd_ut,
                    reader=reader,
                    observer_lat=latitude_deg,
                    observer_lon=longitude_deg,
                    lst_deg=lst_deg,
                    delta_t_policy=policy,
                )
                route_ra_deg, route_dec_deg = ecliptic_to_equatorial(
                    routed.longitude,
                    routed.latitude,
                    obliquity_deg,
                )

                assert abs(_signed_angle_delta(direct.right_ascension, route_ra_deg)) < _ROUTE_AGREEMENT_TOLERANCE_DEG, (
                    epoch_name,
                    observer_name,
                    body,
                )
                assert abs(route_dec_deg - direct.declination) < _ROUTE_AGREEMENT_TOLERANCE_DEG, (
                    epoch_name,
                    observer_name,
                    body,
                )


@pytest.mark.requires_ephemeris
def test_topocentric_coordinate_round_trip_holds_across_breadth_matrix() -> None:
    reader = get_reader()

    for epoch_name, jd_tt in _EPOCHS_TT.items():
        for observer_name, (latitude_deg, longitude_deg) in _OBSERVERS.items():
            jd_ut, policy, obliquity_deg, _lst_deg = _tt_pinned_epoch(jd_tt, longitude_deg)

            for body in _PUBLIC_BODIES:
                direct = sky_position_at(
                    body,
                    jd_ut,
                    latitude_deg,
                    longitude_deg,
                    reader=reader,
                    delta_t_policy=policy,
                )
                lon_deg, lat_deg = equatorial_to_ecliptic(
                    direct.right_ascension,
                    direct.declination,
                    obliquity_deg,
                )
                round_trip_ra_deg, round_trip_dec_deg = ecliptic_to_equatorial(
                    lon_deg,
                    lat_deg,
                    obliquity_deg,
                )

                assert abs(_signed_angle_delta(direct.right_ascension, round_trip_ra_deg)) < _ROUND_TRIP_TOLERANCE_DEG, (
                    epoch_name,
                    observer_name,
                    body,
                )
                assert abs(round_trip_dec_deg - direct.declination) < _ROUND_TRIP_TOLERANCE_DEG, (
                    epoch_name,
                    observer_name,
                    body,
                )


@pytest.mark.requires_ephemeris
def test_topocentric_sky_motion_remains_smooth_across_breadth_matrix() -> None:
    reader = get_reader()

    for epoch_name, jd_tt in _EPOCHS_TT.items():
        for observer_name, (latitude_deg, longitude_deg) in _OBSERVERS.items():
            for body in _PUBLIC_BODIES:
                positions = []

                for sample_tt in (jd_tt - _ONE_SECOND_JD, jd_tt, jd_tt + _ONE_SECOND_JD):
                    sample_ut, sample_policy, _obliquity_deg, _lst_deg = _tt_pinned_epoch(sample_tt, longitude_deg)
                    positions.append(
                        sky_position_at(
                            body,
                            sample_ut,
                            latitude_deg,
                            longitude_deg,
                            reader=reader,
                            delta_t_policy=sample_policy,
                        )
                    )

                ra_step_before_deg = _signed_angle_delta(positions[0].right_ascension, positions[1].right_ascension)
                ra_step_after_deg = _signed_angle_delta(positions[1].right_ascension, positions[2].right_ascension)
                dec_step_before_deg = positions[1].declination - positions[0].declination
                dec_step_after_deg = positions[2].declination - positions[1].declination

                mismatch_deg = max(
                    abs(ra_step_after_deg - ra_step_before_deg),
                    abs(dec_step_after_deg - dec_step_before_deg),
                )
                scale_deg = max(
                    abs(ra_step_before_deg),
                    abs(ra_step_after_deg),
                    abs(dec_step_before_deg),
                    abs(dec_step_after_deg),
                    1e-16,
                )

                assert math.isfinite(mismatch_deg), (epoch_name, observer_name, body)
                assert mismatch_deg < _SMOOTHNESS_ABS_TOLERANCE_DEG, (epoch_name, observer_name, body, mismatch_deg)
                assert mismatch_deg / scale_deg < _SMOOTHNESS_REL_TOLERANCE, (
                    epoch_name,
                    observer_name,
                    body,
                    mismatch_deg,
                    scale_deg,
                )