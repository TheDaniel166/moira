from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

import pytest

from moira.constants import Body
from moira.julian import jd_from_datetime, local_sidereal_time, utc_to_tt, utc_to_ut1
from moira.light_cone import received_light_at
from moira.nutation_2000a import nutation_2000a
from moira.obliquity import true_obliquity
from moira.planetocentric import planetocentric_at
from moira.planets import (
    all_planets_at,
    heliocentric_planet_at,
    planet_at,
    planet_reduction_breakdown_at,
)
from moira.ssb import ssb_position_at


def _longitude_delta_deg(a: float, b: float) -> float:
    return (a - b + 180.0) % 360.0 - 180.0


def _finite_difference_speed(position_at, jd_ut: float, step_days: float = 1.0e-3) -> float:
    before = position_at(jd_ut - step_days).longitude
    after = position_at(jd_ut + step_days).longitude
    return _longitude_delta_deg(after, before) / (2.0 * step_days)


@pytest.mark.requires_ephemeris
def test_received_light_compares_same_true_of_date_frame(reader) -> None:
    jd_ut = utc_to_ut1(
        jd_from_datetime(datetime(2100, 1, 1, tzinfo=timezone.utc))
    )

    result = received_light_at(Body.PLUTO, jd_ut, reader=reader)
    geometric = planet_at(Body.PLUTO, jd_ut, reader=reader, apparent=False)

    assert result.geometric_longitude == pytest.approx(geometric.longitude, abs=1.0e-12)
    assert abs(result.longitude_displacement) < 0.05


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize(
    "position_at",
    [
        lambda jd, reader: heliocentric_planet_at(Body.MARS, jd, reader=reader),
        lambda jd, reader: ssb_position_at(Body.JUPITER, jd, reader=reader),
        lambda jd, reader: planetocentric_at(Body.JUPITER, Body.MARS, jd, reader=reader),
    ],
)
def test_true_of_date_speed_is_derivative_of_returned_longitude(reader, position_at) -> None:
    jd_ut = utc_to_ut1(
        jd_from_datetime(datetime(2026, 7, 16, 12, tzinfo=timezone.utc))
    )
    result = position_at(jd_ut, reader)
    finite_difference = _finite_difference_speed(lambda jd: position_at(jd, reader), jd_ut)

    assert result.speed == pytest.approx(finite_difference, abs=2.0e-6)


@pytest.mark.requires_ephemeris
def test_topocentric_reduction_ends_at_returned_longitude(reader) -> None:
    jd_utc = jd_from_datetime(datetime(1900, 1, 1, tzinfo=timezone.utc))
    jd_ut = utc_to_ut1(jd_utc)
    jd_tt = utc_to_tt(jd_utc)
    dpsi_deg, _ = nutation_2000a(jd_tt)
    longitude = -74.0
    latitude = 40.7
    lst_deg = local_sidereal_time(
        jd_ut,
        longitude,
        dpsi_deg,
        true_obliquity(jd_tt),
    )

    result = planet_at(
        Body.MOON,
        jd_ut,
        reader=reader,
        observer_lat=latitude,
        observer_lon=longitude,
        lst_deg=lst_deg,
    )
    reduction = planet_reduction_breakdown_at(
        Body.MOON,
        jd_ut,
        reader=reader,
        observer_lat=latitude,
        observer_lon=longitude,
        lst_deg=lst_deg,
    )

    assert reduction.stages[-1].name == "Topocentric diurnal aberration"
    assert reduction.stage_longitudes["topocentric"] == pytest.approx(
        result.longitude,
        abs=1.0e-6,
    )


@pytest.mark.requires_ephemeris
def test_planetary_modes_reject_ambiguous_observer_and_center(reader) -> None:
    with pytest.raises(ValueError, match="observer_lat, observer_lon, and lst_deg"):
        planet_at(
            Body.MARS,
            2451545.0,
            reader=reader,
            observer_lat=51.5,
            lst_deg=10.0,
        )

    with pytest.raises(ValueError, match="center must be"):
        all_planets_at(
            2451545.0,
            bodies=[Body.MARS],
            reader=reader,
            center="banana",
        )


@pytest.mark.requires_ephemeris
def test_frame_position_vessels_are_immutable(reader) -> None:
    jd_ut = 2451545.0
    vessels = (
        (received_light_at(Body.MARS, jd_ut, reader=reader), "apparent_longitude"),
        (ssb_position_at(Body.JUPITER, jd_ut, reader=reader), "longitude"),
        (planetocentric_at(Body.JUPITER, Body.MARS, jd_ut, reader=reader), "longitude"),
    )

    for vessel, field_name in vessels:
        with pytest.raises(FrozenInstanceError):
            setattr(vessel, field_name, 0.0)
