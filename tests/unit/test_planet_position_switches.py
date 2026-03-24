"""
Unit tests for planet_at() position switches.

Covers:
    - apparent, aberration, grav_deflection, nutation, center, frame kwargs
    - CartesianPosition result type
    - sky_position_at correction switches
    - all_planets_at switch propagation

Tests marked @pytest.mark.requires_ephemeris need de441.bsp.
Tests without that mark are pure-unit (no kernel required).
"""
from __future__ import annotations

import math
import pytest

from moira.planets import CartesianPosition, PlanetData, planet_at, sky_position_at, all_planets_at
from moira.constants import Body

# J2000.0 epoch in UT — stable reference for all ephemeris tests.
_JD_J2000 = 2451545.0


# ---------------------------------------------------------------------------
# Pure-unit: input validation (no ephemeris required)
# ---------------------------------------------------------------------------

def test_planet_at_invalid_center_raises():
    with pytest.raises(ValueError, match="center"):
        planet_at(Body.MARS, _JD_J2000, center="heliocentric")


def test_planet_at_invalid_frame_raises():
    with pytest.raises(ValueError, match="frame"):
        planet_at(Body.MARS, _JD_J2000, frame="spherical")


def test_cartesian_position_repr():
    pos = CartesianPosition(name="Mars", x=1.0, y=2.0, z=3.0, center="geocentric")
    r = repr(pos)
    assert "Mars" in r
    assert "geocentric" in r
    assert "x=" in r


def test_cartesian_position_fields():
    pos = CartesianPosition(name="Venus", x=100.0, y=200.0, z=-50.0, center="barycentric")
    assert pos.name == "Venus"
    assert pos.x == 100.0
    assert pos.y == 200.0
    assert pos.z == -50.0
    assert pos.center == "barycentric"


# ---------------------------------------------------------------------------
# Ephemeris tests: default behaviour is unchanged
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_planet_at_default_matches_explicit_apparent_true():
    """Explicit all-default switches must produce identical results to the bare call."""
    default = planet_at(Body.MARS, _JD_J2000)
    explicit = planet_at(
        Body.MARS, _JD_J2000,
        apparent=True, aberration=True, grav_deflection=True, nutation=True,
        center="geocentric", frame="ecliptic",
    )
    assert isinstance(default, PlanetData)
    assert default.longitude == explicit.longitude
    assert default.latitude == explicit.latitude
    assert default.distance == explicit.distance


@pytest.mark.requires_ephemeris
def test_all_planets_at_default_matches_planet_at_loop():
    """all_planets_at must give the same result as calling planet_at per body."""
    bodies = [Body.SUN, Body.MOON, Body.MARS]
    bulk = all_planets_at(_JD_J2000, bodies=bodies)
    for body in bodies:
        single = planet_at(body, _JD_J2000)
        assert abs(bulk[body].longitude - single.longitude) < 1e-10
        assert abs(bulk[body].latitude - single.latitude) < 1e-10


# ---------------------------------------------------------------------------
# Ephemeris tests: aberration switch
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_aberration_false_changes_position():
    """Disabling aberration must produce a measurably different longitude."""
    with_ab = planet_at(Body.MARS, _JD_J2000, aberration=True)
    without = planet_at(Body.MARS, _JD_J2000, aberration=False)
    assert isinstance(with_ab, PlanetData)
    assert isinstance(without, PlanetData)
    # Annual aberration is ~20 arcseconds; 0.001° ≈ 3.6 arcseconds is a safe threshold.
    diff = abs(with_ab.longitude - without.longitude)
    assert diff > 1e-3, f"Expected >0.001° change from aberration, got {diff}"


@pytest.mark.requires_ephemeris
def test_aberration_false_ignored_when_apparent_false():
    """When apparent=False the aberration flag has no effect."""
    a = planet_at(Body.MARS, _JD_J2000, apparent=False, aberration=True)
    b = planet_at(Body.MARS, _JD_J2000, apparent=False, aberration=False)
    assert a.longitude == b.longitude
    assert a.latitude == b.latitude


# ---------------------------------------------------------------------------
# Ephemeris tests: grav_deflection switch
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_grav_deflection_false_changes_position():
    """Disabling gravitational deflection must shift the position measurably."""
    with_gd = planet_at(Body.MARS, _JD_J2000, grav_deflection=True)
    without = planet_at(Body.MARS, _JD_J2000, grav_deflection=False)
    diff = abs(with_gd.longitude - without.longitude)
    # Deflection near the Sun is ~1 arcsec; away from it it's ~0.001 arcsec.
    # A non-zero difference at any level is sufficient to confirm the switch works.
    assert diff != 0.0 or abs(with_gd.latitude - without.latitude) != 0.0, (
        "grav_deflection=False produced identical result to True"
    )


@pytest.mark.requires_ephemeris
def test_grav_deflection_not_applied_to_sun():
    """Deflection is never applied to the Sun regardless of the switch."""
    with_gd = planet_at(Body.SUN, _JD_J2000, grav_deflection=True)
    without = planet_at(Body.SUN, _JD_J2000, grav_deflection=False)
    assert with_gd.longitude == without.longitude
    assert with_gd.latitude == without.latitude


@pytest.mark.requires_ephemeris
def test_grav_deflection_false_ignored_when_apparent_false():
    a = planet_at(Body.MARS, _JD_J2000, apparent=False, grav_deflection=True)
    b = planet_at(Body.MARS, _JD_J2000, apparent=False, grav_deflection=False)
    assert a.longitude == b.longitude


# ---------------------------------------------------------------------------
# Ephemeris tests: nutation switch
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_nutation_false_changes_position():
    """Disabling nutation must produce a different longitude."""
    with_nut = planet_at(Body.MARS, _JD_J2000, nutation=True)
    without  = planet_at(Body.MARS, _JD_J2000, nutation=False)
    diff = abs(with_nut.longitude - without.longitude)
    # Nutation in longitude is ~17 arcseconds peak-to-peak.
    assert diff > 1e-4, f"Expected nutation effect > 0.0001°, got {diff}"


@pytest.mark.requires_ephemeris
def test_nutation_false_ignored_when_apparent_false():
    a = planet_at(Body.MARS, _JD_J2000, apparent=False, nutation=True)
    b = planet_at(Body.MARS, _JD_J2000, apparent=False, nutation=False)
    assert a.longitude == b.longitude


# ---------------------------------------------------------------------------
# Ephemeris tests: center switch
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_barycentric_center_returns_planet_data():
    result = planet_at(Body.MARS, _JD_J2000, center="barycentric")
    assert isinstance(result, PlanetData)


@pytest.mark.requires_ephemeris
def test_barycentric_differs_from_geocentric():
    """Barycentric and geocentric positions must differ by a measurable amount."""
    geo  = planet_at(Body.MARS, _JD_J2000, center="geocentric")
    bary = planet_at(Body.MARS, _JD_J2000, center="barycentric")
    diff = abs(geo.longitude - bary.longitude)
    # Earth–SSB offset is ~450 km; this shifts Mars by several arcseconds.
    assert diff > 1e-4, f"Expected >0.0001° barycentric offset, got {diff}"


@pytest.mark.requires_ephemeris
def test_barycentric_astrometric_differs_from_geocentric_astrometric():
    geo  = planet_at(Body.MARS, _JD_J2000, apparent=False, center="geocentric")
    bary = planet_at(Body.MARS, _JD_J2000, apparent=False, center="barycentric")
    diff = abs(geo.longitude - bary.longitude)
    assert diff > 1e-4


@pytest.mark.requires_ephemeris
def test_barycentric_topocentric_correction_not_applied():
    """Topocentric correction is silently ignored for barycentric output."""
    bary_plain = planet_at(Body.MARS, _JD_J2000, center="barycentric")
    bary_topo  = planet_at(
        Body.MARS, _JD_J2000, center="barycentric",
        observer_lat=51.5, observer_lon=-0.1, lst_deg=100.0,
    )
    assert bary_plain.longitude == bary_topo.longitude


# ---------------------------------------------------------------------------
# Ephemeris tests: frame='cartesian'
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_cartesian_frame_returns_cartesian_position():
    result = planet_at(Body.MARS, _JD_J2000, frame="cartesian")
    assert isinstance(result, CartesianPosition)
    assert result.name == Body.MARS
    assert result.center == "geocentric"


@pytest.mark.requires_ephemeris
def test_cartesian_frame_barycentric_label():
    result = planet_at(Body.MARS, _JD_J2000, frame="cartesian", center="barycentric")
    assert isinstance(result, CartesianPosition)
    assert result.center == "barycentric"


@pytest.mark.requires_ephemeris
def test_cartesian_distance_consistent_with_ecliptic():
    """Distance computed from XYZ must match the PlanetData distance."""
    ecliptic = planet_at(Body.MARS, _JD_J2000, frame="ecliptic")
    cartesian = planet_at(Body.MARS, _JD_J2000, frame="cartesian")
    assert isinstance(ecliptic, PlanetData)
    assert isinstance(cartesian, CartesianPosition)

    xyz_dist = math.sqrt(cartesian.x**2 + cartesian.y**2 + cartesian.z**2)
    # Distances should agree to within 1 km (numerical precision of transforms).
    assert abs(xyz_dist - ecliptic.distance) < 1.0, (
        f"Cartesian distance {xyz_dist:.3f} km vs PlanetData {ecliptic.distance:.3f} km"
    )


@pytest.mark.requires_ephemeris
def test_cartesian_astrometric_frame():
    """frame='cartesian' must also work when apparent=False."""
    result = planet_at(Body.MARS, _JD_J2000, apparent=False, frame="cartesian")
    assert isinstance(result, CartesianPosition)
    assert math.isfinite(result.x)
    assert math.isfinite(result.y)
    assert math.isfinite(result.z)


# ---------------------------------------------------------------------------
# Ephemeris tests: sky_position_at correction switches
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_sky_position_aberration_false_changes_ra():
    lat, lon = 51.5, -0.1
    with_ab  = sky_position_at(Body.MARS, _JD_J2000, lat, lon, aberration=True)
    without  = sky_position_at(Body.MARS, _JD_J2000, lat, lon, aberration=False)
    diff = abs(with_ab.right_ascension - without.right_ascension)
    assert diff > 1e-3, f"Expected >0.001° RA change from aberration, got {diff}"


@pytest.mark.requires_ephemeris
def test_sky_position_nutation_false_changes_dec():
    lat, lon = 51.5, -0.1
    with_nut = sky_position_at(Body.MARS, _JD_J2000, lat, lon, nutation=True)
    without  = sky_position_at(Body.MARS, _JD_J2000, lat, lon, nutation=False)
    diff = abs(with_nut.declination - without.declination)
    assert diff > 1e-4, f"Expected nutation effect in Dec > 0.0001°, got {diff}"


@pytest.mark.requires_ephemeris
def test_sky_position_default_matches_explicit_switches():
    """Explicit all-default switches must match the bare sky_position_at call."""
    lat, lon = 51.5, -0.1
    default  = sky_position_at(Body.MARS, _JD_J2000, lat, lon)
    explicit = sky_position_at(
        Body.MARS, _JD_J2000, lat, lon,
        aberration=True, grav_deflection=True, nutation=True,
    )
    assert default.right_ascension == explicit.right_ascension
    assert default.declination == explicit.declination
    assert default.altitude == explicit.altitude


# ---------------------------------------------------------------------------
# Ephemeris tests: all_planets_at switch propagation
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_all_planets_at_aberration_false_propagates():
    """all_planets_at(aberration=False) must differ from the default for all bodies."""
    bodies = [Body.MARS, Body.VENUS, Body.JUPITER]
    default  = all_planets_at(_JD_J2000, bodies=bodies)
    no_aberr = all_planets_at(_JD_J2000, bodies=bodies, aberration=False)
    for body in bodies:
        assert default[body].longitude != no_aberr[body].longitude, (
            f"aberration=False had no effect on {body}"
        )


@pytest.mark.requires_ephemeris
def test_all_planets_at_apparent_false_matches_planet_at_loop():
    """all_planets_at(apparent=False) must match planet_at(apparent=False) per body."""
    bodies = [Body.MARS, Body.VENUS]
    bulk = all_planets_at(_JD_J2000, bodies=bodies, apparent=False)
    for body in bodies:
        single = planet_at(body, _JD_J2000, apparent=False)
        assert abs(bulk[body].longitude - single.longitude) < 1e-10
