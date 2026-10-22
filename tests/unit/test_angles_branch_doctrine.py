"""Branch-doctrine locks for the shared local-angle helper in ``moira._angles``.

``_asc_from_armc`` used to exist twice in Python, in ``moira.geodetic`` and
``moira.houses``, with the geodetic copy missing the terminal normalisation.
These tests pin the consolidated doctrine from the outside: the selected root
must sit on the horizon, and it must be the eastern one.  Neither check reuses
the branch selection under test — the horizon condition is assembled from the
Meeus Ch. 13 right-ascension conversion and the standard altitude equation.

Tolerance basis: the altitude covenant is a structural consequence of the
horizon definition, not an ephemeris accuracy claim.  The worst observed
residual over the sampled corpus is 1.3e-13 degrees, so 1e-6 degrees (the
``moira_approx`` angle tolerance) leaves five orders of margin without
weakening the invariant.
"""

from __future__ import annotations

import math

import pytest

from moira import _angles
from moira.geodetic import _asc_from_armc as geodetic_helper
from moira.geodetic import geodetic_asc
from moira.houses import _asc_from_armc as houses_helper

DEG2RAD = math.pi / 180.0
RAD2DEG = 180.0 / math.pi

# Obliquity range spanned by the current J2000 true value plus its secular drift.
OBLIQUITY_SAMPLES = (21.5, 23.4392966, 24.5)

# Full closed geographic domain, with near-pole samples on both sides.
LATITUDE_SAMPLES = (
    -90.0, -89.9999, -70.0, -66.0, -30.0, 0.0,
    30.0, 51.5, 66.0, 70.0, 89.9999, 90.0,
)
RISING_LATITUDE_SAMPLES = tuple(lat for lat in LATITUDE_SAMPLES if abs(lat) < 90.0)

ARMC_STEP_DEG = 1.0


def _right_ascension_of(ecliptic_longitude_deg: float, obliquity_deg: float) -> float:
    """Right ascension of an ecliptic point at latitude zero (Meeus Ch. 13)."""
    lam = ecliptic_longitude_deg * DEG2RAD
    eps = obliquity_deg * DEG2RAD
    return math.atan2(math.sin(lam) * math.cos(eps), math.cos(lam)) * RAD2DEG % 360.0


def _hour_angle_deg(asc: float, armc: float, obliquity_deg: float) -> float:
    return (armc - _right_ascension_of(asc, obliquity_deg)) % 360.0


def _altitude_deg(asc: float, armc: float, obliquity_deg: float, latitude_deg: float) -> float:
    ha = _hour_angle_deg(asc, armc, obliquity_deg) * DEG2RAD
    dec = math.asin(math.sin(obliquity_deg * DEG2RAD) * math.sin(asc * DEG2RAD))
    sin_altitude = (
        math.sin(latitude_deg * DEG2RAD) * math.sin(dec)
        + math.cos(latitude_deg * DEG2RAD) * math.cos(dec) * math.cos(ha)
    )
    return math.asin(max(-1.0, min(1.0, sin_altitude))) * RAD2DEG


def test_consumers_share_one_branch_doctrine() -> None:
    assert geodetic_helper is _angles._asc_from_armc
    assert houses_helper is _angles._asc_from_armc


@pytest.mark.parametrize("obliquity", OBLIQUITY_SAMPLES)
@pytest.mark.parametrize("latitude", LATITUDE_SAMPLES)
def test_selected_root_lies_on_the_horizon(obliquity: float, latitude: float) -> None:
    for armc in range(0, 360):
        asc = _angles._asc_from_armc(float(armc), obliquity, latitude)
        assert abs(_altitude_deg(asc, float(armc), obliquity, latitude)) < 1e-6, (
            f"selected root off the horizon: armc={armc}, "
            f"obliquity={obliquity}, lat={latitude}, asc={asc}"
        )


@pytest.mark.parametrize("obliquity", OBLIQUITY_SAMPLES)
@pytest.mark.parametrize("latitude", RISING_LATITUDE_SAMPLES)
def test_selected_root_is_the_eastern_intersection(obliquity: float, latitude: float) -> None:
    # The rising root has negative hour angle, expressed here as the circular
    # value above 180 deg. This includes near-polar cases where the former
    # ecliptic-longitude / right-ascension comparison chose the setting root.
    for armc in range(0, 360):
        asc = _angles._asc_from_armc(float(armc), obliquity, latitude)
        assert _hour_angle_deg(asc, float(armc), obliquity) > 180.0, (
            f"selected root is the setting intersection: armc={armc}, "
            f"obliquity={obliquity}, lat={latitude}, asc={asc}"
        )


@pytest.mark.parametrize("obliquity", OBLIQUITY_SAMPLES)
def test_result_is_a_half_open_circular_longitude(obliquity: float) -> None:
    for latitude in LATITUDE_SAMPLES:
        for armc in range(0, 360):
            asc = _angles._asc_from_armc(float(armc), obliquity, latitude)
            assert 0.0 <= asc < 360.0, (
                f"ASC escaped [0, 360): armc={armc}, obliquity={obliquity}, "
                f"lat={latitude}, asc={asc!r}"
            )


def test_polar_tie_selects_the_principal_root() -> None:
    # The shared helper keeps a deterministic value at the pole because some
    # house paths need one. At that latitude the rising-rate test is undefined;
    # the tie selects the principal root, normalized into [0, 360).
    assert _angles._asc_from_armc(0.0, 23.4392811111, 90.0) == 0.0


def test_geodetic_refuses_the_pole_instead_of_publishing_the_tie() -> None:
    # The algebraic tie above is not an astronomical answer, so the geodetic
    # surface refuses the domain rather than returning it.
    with pytest.raises(ValueError, match="geographic pole"):
        geodetic_asc(0.0, 90.0, 23.4392811111)
    with pytest.raises(ValueError, match="geographic pole"):
        geodetic_asc(0.0, -90.0, 23.4392811111)
