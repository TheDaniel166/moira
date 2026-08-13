from __future__ import annotations

import math

import pytest

from moira._ephemeris_time import _ut1_to_ephemeris_tt
from moira.constants import Body, NAIF_ROUTES
from moira.coordinates import icrf_to_equatorial
from moira.julian import julian_day
from moira.planets import CartesianPosition, planet_at
from tools.horizons import observer_apparent_position_tt


AU_KM = 149_597_870.700
ANGULAR_THRESHOLD_ARCSEC = 0.35
DISTANCE_THRESHOLD_KM = 0.1

HORIZONS_TARGETS: list[tuple[str, str, str]] = [
    (Body.SUN, "10", "Sun center"),
    (Body.MOON, "301", "Moon center"),
    (Body.MERCURY, "199", "Mercury center"),
    (Body.VENUS, "299", "Venus center"),
    (Body.MARS, "4", "Mars system barycenter"),
    (Body.JUPITER, "5", "Jupiter system barycenter"),
    (Body.SATURN, "6", "Saturn system barycenter"),
    (Body.URANUS, "7", "Uranus system barycenter"),
    (Body.NEPTUNE, "8", "Neptune system barycenter"),
    (Body.PLUTO, "9", "Pluto system barycenter"),
]

EPOCHS: list[tuple[str, float]] = [
    ("1900-01-01", julian_day(1900, 1, 1, 12)),
    ("1918-11-11", julian_day(1918, 11, 11, 11)),
    ("1933-03-15", julian_day(1933, 3, 15, 12)),
    ("1950-06-15", julian_day(1950, 6, 15, 12)),
    ("1969-07-20", julian_day(1969, 7, 20, 20)),
    ("1987-09-23", julian_day(1987, 9, 23, 0)),
    ("2000-01-01", julian_day(2000, 1, 1, 12)),
    ("2010-07-01", julian_day(2010, 7, 1, 12)),
    ("2017-08-21", julian_day(2017, 8, 21, 18)),
    ("2020-01-01", julian_day(2020, 1, 1, 12)),
    ("2024-04-08", julian_day(2024, 4, 8, 18)),
    ("2025-09-01", julian_day(2025, 9, 1, 12)),
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


def test_horizons_targets_match_moira_route_identities() -> None:
    """Keep every external oracle target identical to Moira's final SPK target."""
    assert [body for body, _command, _identity in HORIZONS_TARGETS] == list(
        Body.ALL_PLANETS
    )
    for body, command, identity in HORIZONS_TARGETS:
        assert int(command) == NAIF_ROUTES[body][-1][1], (
            f"{body}: Horizons target {command} ({identity}) does not match "
            f"Moira's final SPK target {NAIF_ROUTES[body][-1][1]}"
        )


@pytest.mark.integration
@pytest.mark.external_network
@pytest.mark.requires_ephemeris
@pytest.mark.slow
@pytest.mark.parametrize(
    ("body", "command", "target_identity"),
    HORIZONS_TARGETS,
    ids=[body for body, _command, _identity in HORIZONS_TARGETS],
)
@pytest.mark.parametrize(
    ("label", "jd_ut"),
    EPOCHS,
    ids=[label for label, _jd_ut in EPOCHS],
)
def test_planet_at_apparent_positions_match_horizons(
    body: str,
    command: str,
    target_identity: str,
    label: str,
    jd_ut: float,
    reader,
) -> None:
    """Compare the same target at the same TT epoch in each system.

    The remaining angular envelope is a declared frame-model comparison:
    Moira uses IAU 2006/2000A true-of-date while Horizons observer quantity 2
    uses its EOP-corrected IAU 1976/1980 true equator and equinox of date.
    """
    jd_tt = _ut1_to_ephemeris_tt(jd_ut, reader)
    moira = planet_at(body, jd_ut, reader=reader, frame="cartesian")
    assert isinstance(moira, CartesianPosition)
    moira_ra, moira_dec, moira_distance_km = icrf_to_equatorial(
        (moira.x, moira.y, moira.z)
    )
    moira_dist_au = moira_distance_km / AU_KM

    ref = observer_apparent_position_tt(command, jd_tt)

    angular_error_arcsec = _angular_sep_arcsec(
        moira_ra % 360.0,
        moira_dec,
        ref.right_ascension,
        ref.declination,
    )
    distance_error_km = abs(moira_dist_au - ref.distance_au) * AU_KM

    assert angular_error_arcsec <= ANGULAR_THRESHOLD_ARCSEC, (
        f"{body} ({target_identity}) {label}: apparent angular error "
        f"{angular_error_arcsec:.6f} arcsec "
        f"exceeds {ANGULAR_THRESHOLD_ARCSEC:.3f}"
    )
    assert distance_error_km <= DISTANCE_THRESHOLD_KM, (
        f"{body} ({target_identity}) {label}: apparent distance error "
        f"{distance_error_km:.6f} km "
        f"exceeds {DISTANCE_THRESHOLD_KM:.3f}"
    )
