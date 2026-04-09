import pytest

from moira.constants import Body
from moira.coordinates import (
    ecliptic_to_equatorial,
    equatorial_to_ecliptic,
    icrf_to_equatorial,
    mat_vec_mul,
    nutation_matrix_equatorial,
    precession_matrix_equatorial,
)
from moira.corrections import (
    SCHWARZSCHILD_RADII,
    apply_aberration,
    apply_deflection,
    apply_frame_bias,
    apply_light_time,
    topocentric_correction,
)
from moira.julian import DeltaTPolicy, local_sidereal_time, tt_to_ut
from moira.obliquity import mean_obliquity, nutation
from moira.planets import (
    _barycentric,
    _earth_barycentric_state,
    _geocentric,
    planet_at,
    sky_position_at,
)
from moira.spk_reader import get_reader

_JD_TT = 2459205.25
_ONE_SECOND_JD = 1.0 / 86400.0
_OBSERVER_LAT = 51.5
_OBSERVER_LON = -0.1
_OBSERVER_ELEV_M = 0.0
_BODIES = (Body.JUPITER, Body.SATURN)
_INTERNAL_PATH_TOLERANCE_DEG = 1e-9
_ROUND_TRIP_TOLERANCE_DEG = 1e-10
_SEPARATION_STEP_MISMATCH_TOLERANCE_DEG = 1e-9


def _signed_angle_delta(start_deg: float, end_deg: float) -> float:
    return ((end_deg - start_deg + 180.0) % 360.0) - 180.0


def _tt_pinned_epoch(jd_tt: float) -> tuple[float, DeltaTPolicy, float, float]:
    jd_ut = tt_to_ut(jd_tt)
    delta_t_seconds = (jd_tt - jd_ut) * 86400.0
    policy = DeltaTPolicy(model="fixed", fixed_delta_t=delta_t_seconds)
    dpsi_deg, deps_deg = nutation(jd_tt)
    obliquity_deg = mean_obliquity(jd_tt) + deps_deg
    lst_deg = local_sidereal_time(jd_ut, _OBSERVER_LON, dpsi_deg, obliquity_deg)
    return jd_ut, policy, obliquity_deg, lst_deg


def _direct_topocentric_ra_dec(body: str, jd_tt: float, reader) -> tuple[float, float]:
    jd_ut, policy, _obliquity_deg, _lst_deg = _tt_pinned_epoch(jd_tt)
    sky = sky_position_at(
        body,
        jd_ut,
        _OBSERVER_LAT,
        _OBSERVER_LON,
        _OBSERVER_ELEV_M,
        reader=reader,
        delta_t_policy=policy,
    )
    return sky.right_ascension, sky.declination


def _manual_chain_topocentric_ra_dec(body: str, jd_tt: float, reader) -> tuple[float, float]:
    _jd_ut, _policy, _obliquity_deg, lst_deg = _tt_pinned_epoch(jd_tt)
    earth_ssb, earth_vel = _earth_barycentric_state(jd_tt, reader)
    xyz, _light_time_days = apply_light_time(body, jd_tt, reader, earth_ssb, _barycentric)

    if body not in (Body.SUN, Body.MOON):
        sun_geo = _geocentric(Body.SUN, jd_tt, reader)
        deflectors = [(sun_geo, SCHWARZSCHILD_RADII["Sun"])]
        if body != Body.JUPITER:
            deflectors.append((_geocentric(Body.JUPITER, jd_tt, reader), SCHWARZSCHILD_RADII["Jupiter"]))
        if body != Body.SATURN:
            deflectors.append((_geocentric(Body.SATURN, jd_tt, reader), SCHWARZSCHILD_RADII["Saturn"]))
        xyz = apply_deflection(xyz, deflectors)

    xyz = apply_aberration(xyz, earth_vel)
    xyz = apply_frame_bias(xyz)
    xyz = mat_vec_mul(precession_matrix_equatorial(jd_tt), xyz)
    xyz = mat_vec_mul(nutation_matrix_equatorial(jd_tt), xyz)
    xyz = topocentric_correction(xyz, _OBSERVER_LAT, _OBSERVER_LON, lst_deg, _OBSERVER_ELEV_M)

    ra_deg, dec_deg, _distance_km = icrf_to_equatorial(xyz)
    return ra_deg, dec_deg


def _route_topocentric_ra_dec(body: str, jd_tt: float, reader) -> tuple[float, float]:
    jd_ut, policy, obliquity_deg, lst_deg = _tt_pinned_epoch(jd_tt)
    topocentric = planet_at(
        body,
        jd_ut,
        reader=reader,
        observer_lat=_OBSERVER_LAT,
        observer_lon=_OBSERVER_LON,
        observer_elev_m=_OBSERVER_ELEV_M,
        lst_deg=lst_deg,
        delta_t_policy=policy,
    )
    return ecliptic_to_equatorial(topocentric.longitude, topocentric.latitude, obliquity_deg)


def _topocentric_longitude(body: str, jd_tt: float, reader) -> float:
    jd_ut, policy, _obliquity_deg, lst_deg = _tt_pinned_epoch(jd_tt)
    topocentric = planet_at(
        body,
        jd_ut,
        reader=reader,
        observer_lat=_OBSERVER_LAT,
        observer_lon=_OBSERVER_LON,
        observer_elev_m=_OBSERVER_ELEV_M,
        lst_deg=lst_deg,
        delta_t_policy=policy,
    )
    return topocentric.longitude


@pytest.mark.requires_ephemeris
def test_topocentric_ra_dec_agree_across_direct_chain_and_route() -> None:
    reader = get_reader()

    for body in _BODIES:
        direct_ra_deg, direct_dec_deg = _direct_topocentric_ra_dec(body, _JD_TT, reader)
        chain_ra_deg, chain_dec_deg = _manual_chain_topocentric_ra_dec(body, _JD_TT, reader)
        route_ra_deg, route_dec_deg = _route_topocentric_ra_dec(body, _JD_TT, reader)

        assert abs(_signed_angle_delta(direct_ra_deg, chain_ra_deg)) < _INTERNAL_PATH_TOLERANCE_DEG, body
        assert abs(chain_dec_deg - direct_dec_deg) < _INTERNAL_PATH_TOLERANCE_DEG, body

        assert abs(_signed_angle_delta(direct_ra_deg, route_ra_deg)) < _INTERNAL_PATH_TOLERANCE_DEG, body
        assert abs(route_dec_deg - direct_dec_deg) < _INTERNAL_PATH_TOLERANCE_DEG, body

        assert abs(_signed_angle_delta(chain_ra_deg, route_ra_deg)) < _INTERNAL_PATH_TOLERANCE_DEG, body
        assert abs(route_dec_deg - chain_dec_deg) < _INTERNAL_PATH_TOLERANCE_DEG, body


@pytest.mark.requires_ephemeris
def test_topocentric_ra_dec_round_trip_is_stable_at_machine_scale() -> None:
    reader = get_reader()
    _jd_ut, _policy, obliquity_deg, _lst_deg = _tt_pinned_epoch(_JD_TT)

    for body in _BODIES:
        direct_ra_deg, direct_dec_deg = _direct_topocentric_ra_dec(body, _JD_TT, reader)
        lon_deg, lat_deg = equatorial_to_ecliptic(direct_ra_deg, direct_dec_deg, obliquity_deg)
        round_trip_ra_deg, round_trip_dec_deg = ecliptic_to_equatorial(lon_deg, lat_deg, obliquity_deg)

        assert abs(_signed_angle_delta(direct_ra_deg, round_trip_ra_deg)) < _ROUND_TRIP_TOLERANCE_DEG, body
        assert abs(round_trip_dec_deg - direct_dec_deg) < _ROUND_TRIP_TOLERANCE_DEG, body


@pytest.mark.requires_ephemeris
def test_jupiter_saturn_topocentric_longitude_progression_is_smooth_across_one_second_tt() -> None:
    reader = get_reader()

    separation_minus_deg = _signed_angle_delta(
        _topocentric_longitude(Body.SATURN, _JD_TT - _ONE_SECOND_JD, reader),
        _topocentric_longitude(Body.JUPITER, _JD_TT - _ONE_SECOND_JD, reader),
    )
    separation_deg = _signed_angle_delta(
        _topocentric_longitude(Body.SATURN, _JD_TT, reader),
        _topocentric_longitude(Body.JUPITER, _JD_TT, reader),
    )
    separation_plus_deg = _signed_angle_delta(
        _topocentric_longitude(Body.SATURN, _JD_TT + _ONE_SECOND_JD, reader),
        _topocentric_longitude(Body.JUPITER, _JD_TT + _ONE_SECOND_JD, reader),
    )

    step_before_deg = separation_deg - separation_minus_deg
    step_after_deg = separation_plus_deg - separation_deg

    assert separation_minus_deg < separation_deg < separation_plus_deg
    assert separation_minus_deg < 0.0
    assert separation_deg < 0.0
    assert separation_plus_deg < 0.0
    assert abs(step_after_deg - step_before_deg) < _SEPARATION_STEP_MISMATCH_TOLERANCE_DEG