from __future__ import annotations

import math

import pytest

from moira.constants import Body
from moira.coordinates import ecliptic_to_equatorial
from moira.julian import julian_day
from moira.obliquity import true_obliquity
from moira.planets import planet_at
from tests.tools.horizons import observer_apparent_position


AU_KM = 149_597_870.700
ANGULAR_THRESHOLD_ARCSEC = 0.75
DISTANCE_THRESHOLD_KM = 1750.0

BODIES: list[tuple[str, str]] = [
    (Body.SUN, "10"),
    (Body.MOON, "301"),
    (Body.MERCURY, "199"),
    (Body.VENUS, "299"),
    (Body.MARS, "499"),
    (Body.JUPITER, "599"),
    (Body.SATURN, "699"),
    (Body.URANUS, "799"),
    (Body.NEPTUNE, "899"),
    (Body.PLUTO, "999"),
]

EPOCHS: list[tuple[str, str, str, float]] = [
    ("1900-01-01", "1900-Jan-01 12:00", "1900-Jan-01 13:00", julian_day(1900, 1, 1, 12)),
    ("1918-11-11", "1918-Nov-11 11:00", "1918-Nov-11 12:00", julian_day(1918, 11, 11, 11)),
    ("1933-03-15", "1933-Mar-15 12:00", "1933-Mar-15 13:00", julian_day(1933, 3, 15, 12)),
    ("1950-06-15", "1950-Jun-15 12:00", "1950-Jun-15 13:00", julian_day(1950, 6, 15, 12)),
    ("1969-07-20", "1969-Jul-20 20:00", "1969-Jul-20 21:00", julian_day(1969, 7, 20, 20)),
    ("1987-09-23", "1987-Sep-23 00:00", "1987-Sep-23 01:00", julian_day(1987, 9, 23, 0)),
    ("2000-01-01", "2000-Jan-01 12:00", "2000-Jan-01 13:00", julian_day(2000, 1, 1, 12)),
    ("2010-07-01", "2010-Jul-01 12:00", "2010-Jul-01 13:00", julian_day(2010, 7, 1, 12)),
    ("2017-08-21", "2017-Aug-21 18:00", "2017-Aug-21 19:00", julian_day(2017, 8, 21, 18)),
    ("2020-01-01", "2020-Jan-01 12:00", "2020-Jan-01 13:00", julian_day(2020, 1, 1, 12)),
    ("2024-04-08", "2024-Apr-08 18:00", "2024-Apr-08 19:00", julian_day(2024, 4, 8, 18)),
    ("2025-09-01", "2025-Sep-01 12:00", "2025-Sep-01 13:00", julian_day(2025, 9, 1, 12)),
]


def _angular_sep_arcsec(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    r1, d1 = math.radians(ra1), math.radians(dec1)
    r2, d2 = math.radians(ra2), math.radians(dec2)
    cos_sep = (
        math.sin(d1) * math.sin(d2)
        + math.cos(d1) * math.cos(d2) * math.cos(r1 - r2)
    )
    cos_sep = max(-1.0, min(1.0, cos_sep))
    return math.degrees(math.acos(cos_sep)) * 3600.0


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.requires_ephemeris
@pytest.mark.slow
@pytest.mark.parametrize(
    ("body", "command"),
    BODIES,
    ids=[body for body, _ in BODIES],
)
@pytest.mark.parametrize(
    ("label", "start_utc", "stop_utc", "jd_ut"),
    EPOCHS,
    ids=[label for label, *_ in EPOCHS],
)
def test_planet_at_apparent_positions_match_horizons(
    body: str,
    command: str,
    label: str,
    start_utc: str,
    stop_utc: str,
    jd_ut: float,
) -> None:
    moira = planet_at(body, jd_ut)
    eps = true_obliquity(jd_ut)
    moira_ra, moira_dec = ecliptic_to_equatorial(moira.longitude, moira.latitude, eps)
    moira_dist_au = moira.distance / AU_KM

    ref = observer_apparent_position(command, start_utc, stop_utc)

    angular_error_arcsec = _angular_sep_arcsec(
        moira_ra % 360.0,
        moira_dec,
        ref.right_ascension,
        ref.declination,
    )
    distance_error_km = abs(moira_dist_au - ref.distance_au) * AU_KM

    assert angular_error_arcsec <= ANGULAR_THRESHOLD_ARCSEC, (
        f"{body} {label}: apparent angular error {angular_error_arcsec:.6f} arcsec "
        f"exceeds {ANGULAR_THRESHOLD_ARCSEC:.3f}"
    )
    assert distance_error_km <= DISTANCE_THRESHOLD_KM, (
        f"{body} {label}: apparent distance error {distance_error_km:.6f} km "
        f"exceeds {DISTANCE_THRESHOLD_KM:.3f}"
    )
