"""Independent horizon and branch-boundary witnesses for Geodetic geometry."""

import math

import pytest

from moira.geodetic import geodetic_mc, geodetic_asc, geodetic_chart, geodetic_geometry

EPS = 23.4392911


@pytest.mark.parametrize("latitude", [-90, -89.9999999, 89.9999999, 90])
def test_detailed_geometry_reports_the_existing_polar_refusal(latitude):
    witness = geodetic_geometry(45, latitude, EPS)
    assert witness.status == "polar_refusal"
    assert not witness.is_defined


@pytest.mark.parametrize("value", [-1e-16, 0.0, -0.0, 360.0, -720.0, 1e308])
def test_scalar_mc_is_half_open_even_at_binary64_seam(value):
    mc = geodetic_mc(value)
    assert 0 <= mc < 360
    if abs(value) < 1e-15:
        assert mc == 0.0 and math.copysign(1, mc) == 1


def test_finite_large_displacements_do_not_overflow():
    assert math.isfinite(geodetic_mc(1e308, -1e308))
    assert geodetic_chart(-1e-16, 40.0, EPS).mc == 0.0


@pytest.mark.parametrize("longitude", [45.0, 90.0, 135.0, 225.0, 270.0, 315.0])
def test_nonpolar_meridional_ties_are_refused(longitude):
    declination = math.degrees(math.asin(math.sin(math.radians(EPS)) * math.sin(math.radians(longitude))))
    latitude = declination - math.copysign(90.0, declination)
    witness = geodetic_geometry(longitude, latitude, EPS)
    assert not witness.is_defined
    assert witness.status == ("coincident_planes" if longitude in (90, 270) else "rising_branch_tie")
    with pytest.raises(ValueError, match="undefined"):
        geodetic_asc(longitude, latitude, EPS)
    assert geodetic_mc(longitude) == longitude


@pytest.mark.parametrize("longitude,latitude", [(-74.0, 40.7), (151.0, -33.8), (7.0, 89.0), (45.0, -74.0)])
def test_defined_intersection_is_zero_altitude_and_eastward(longitude, latitude):
    witness = geodetic_geometry(longitude, latitude, EPS)
    lam, eps, phi = map(math.radians, (witness.asc_deg, EPS, latitude))
    mc = math.radians(longitude)
    armc = math.atan2(math.sin(mc) * math.cos(eps), math.cos(mc))
    ra = math.atan2(math.sin(lam) * math.cos(eps), math.cos(lam))
    dec = math.asin(math.sin(eps) * math.sin(lam))
    altitude_sine = math.sin(phi)*math.sin(dec) + math.cos(phi)*math.cos(dec)*math.cos(armc-ra)
    assert abs(altitude_sine) < 2e-14
    assert -math.cos(phi)*math.cos(dec)*math.sin(armc-ra) > 0


def test_branch_transition_is_not_mistaken_for_a_continuous_derivative():
    declination = math.degrees(math.asin(math.sin(math.radians(EPS)) / math.sqrt(2)))
    boundary = declination - 90
    before = geodetic_asc(45.0, boundary-1e-6, EPS)
    after = geodetic_asc(45.0, boundary+1e-6, EPS)
    assert abs(abs((before-after+180) % 360-180)-180) < 1e-4
