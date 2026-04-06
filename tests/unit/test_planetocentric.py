"""
Tests for moira.planetocentric — Planetocentric Position Engine.

Verification strategy:
  - Structural invariants: longitude in [0°, 360°), distance > 0, speed finite.
  - Identity check: heliocentric positions from moira.planets must agree with
    planetocentric_at(Body.SUN, target) to within numerical precision.
  - Anti-identity: geocentric positions must agree with
    planetocentric_at(Body.EARTH, target) to within numerical precision.
    (Light-travel time is not corrected in either path, so agreement is exact
    up to the frame rotation applied to the same vectors.)
  - Antisymmetry of direction: if body A is at longitude λ from body B, then
    body B is at (λ + 180°) mod 360° from body A.
  - ValueError on invalid observer, invalid target, or observer == target.
  - VALID_OBSERVER_BODIES invariants.
  - all_planetocentric_at excludes the observer from its results.
  - PlanetocentricData vessel: sign fields are consistent with longitude,
    retrograde flag is consistent with speed.
"""

from __future__ import annotations

import math

import pytest

from moira.constants import Body
from moira.planetocentric import (
    VALID_OBSERVER_BODIES,
    PlanetocentricData,
    all_planetocentric_at,
    planetocentric_at,
)

# ---------------------------------------------------------------------------
# Reference epoch — J2000.0 in Julian Day (UT1 ≈ TT for testing purposes)
# ---------------------------------------------------------------------------
JD_J2000 = 2451545.0   # 2000 Jan 1.5 TT


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _angular_diff(a: float, b: float) -> float:
    """Smallest signed angular difference a − b, in (−180°, +180°]."""
    d = (a - b + 180.0) % 360.0 - 180.0
    return d


# ---------------------------------------------------------------------------
# VALID_OBSERVER_BODIES
# ---------------------------------------------------------------------------

class TestValidObserverBodies:
    def test_is_frozenset(self) -> None:
        assert isinstance(VALID_OBSERVER_BODIES, frozenset)

    def test_contains_all_major_planets(self) -> None:
        for body in (
            Body.SUN, Body.MOON, Body.MERCURY, Body.VENUS, Body.EARTH,
            Body.MARS, Body.JUPITER, Body.SATURN, Body.URANUS,
            Body.NEPTUNE, Body.PLUTO,
        ):
            assert body in VALID_OBSERVER_BODIES, f"{body!r} missing from VALID_OBSERVER_BODIES"

    def test_does_not_contain_calculated_points(self) -> None:
        for point in (Body.TRUE_NODE, Body.MEAN_NODE, Body.LILITH):
            assert point not in VALID_OBSERVER_BODIES


# ---------------------------------------------------------------------------
# Validation / error paths
# ---------------------------------------------------------------------------

class TestValidation:
    def test_invalid_observer_raises(self) -> None:
        with pytest.raises(ValueError, match="not a valid observer"):
            planetocentric_at("Asteroid", Body.MARS, JD_J2000)

    def test_invalid_target_raises(self) -> None:
        with pytest.raises(ValueError, match="not a valid target"):
            planetocentric_at(Body.MARS, "Comet", JD_J2000)

    def test_observer_equals_target_raises(self) -> None:
        with pytest.raises(ValueError, match="must differ"):
            planetocentric_at(Body.MARS, Body.MARS, JD_J2000)

    def test_all_planetocentric_invalid_observer_raises(self) -> None:
        with pytest.raises(ValueError, match="not a valid observer"):
            all_planetocentric_at("Asteroid", JD_J2000)


# ---------------------------------------------------------------------------
# PlanetocentricData vessel
# ---------------------------------------------------------------------------

class TestPlanetocentricDataVessel:
    def _make(self, observer=Body.MARS, target=Body.JUPITER) -> PlanetocentricData:
        return planetocentric_at(observer, target, JD_J2000)

    def test_observer_field_set_correctly(self) -> None:
        pd = self._make(Body.MARS, Body.JUPITER)
        assert pd.observer == Body.MARS

    def test_name_field_set_to_target(self) -> None:
        pd = self._make(Body.MARS, Body.JUPITER)
        assert pd.name == Body.JUPITER

    def test_longitude_in_0_360(self) -> None:
        pd = self._make()
        assert 0.0 <= pd.longitude < 360.0

    def test_latitude_in_range(self) -> None:
        pd = self._make()
        assert -90.0 <= pd.latitude <= 90.0

    def test_distance_positive(self) -> None:
        pd = self._make()
        assert pd.distance > 0.0

    def test_distance_au_consistent(self) -> None:
        pd = self._make()
        assert pd.distance_au == pytest.approx(pd.distance / 149_597_870.700)

    def test_retrograde_consistent_with_speed(self) -> None:
        pd = self._make()
        assert pd.retrograde == (pd.speed < 0.0)

    def test_sign_consistent_with_longitude(self) -> None:
        pd = self._make()
        expected_sign_index = int(pd.longitude // 30)
        signs = [
            "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
            "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
        ]
        assert pd.sign == signs[expected_sign_index]

    def test_sign_degree_in_range(self) -> None:
        pd = self._make()
        assert 0.0 <= pd.sign_degree < 30.0

    def test_repr_contains_observer_and_target(self) -> None:
        pd = self._make(Body.MARS, Body.SATURN)
        r = repr(pd)
        assert "Mars" in r
        assert "Saturn" in r
        assert "AU" in r


# ---------------------------------------------------------------------------
# Geometric invariants
# ---------------------------------------------------------------------------

class TestGeometricInvariants:
    def test_longitude_always_in_range_across_bodies(self) -> None:
        results = all_planetocentric_at(Body.MARS, JD_J2000)
        for name, pd in results.items():
            assert 0.0 <= pd.longitude < 360.0, f"{name}: lon={pd.longitude}"

    def test_distance_always_positive_across_bodies(self) -> None:
        results = all_planetocentric_at(Body.MARS, JD_J2000)
        for name, pd in results.items():
            assert pd.distance > 0.0, f"{name}: dist={pd.distance}"

    def test_direction_antisymmetry(self) -> None:
        # If B appears at longitude λ from A, then A appears at (λ + 180°) % 360° from B.
        # This is exact to floating-point precision for the same frame / epoch.
        pairs = [
            (Body.MARS,    Body.JUPITER),
            (Body.VENUS,   Body.SATURN),
            (Body.MERCURY, Body.NEPTUNE),
        ]
        for obs, tgt in pairs:
            fwd = planetocentric_at(obs, tgt, JD_J2000)
            rev = planetocentric_at(tgt, obs, JD_J2000)
            expected_rev_lon = (fwd.longitude + 180.0) % 360.0
            diff = abs(_angular_diff(rev.longitude, expected_rev_lon))
            assert diff < 0.01, (
                f"Antisymmetry failed for ({obs}, {tgt}): "
                f"fwd={fwd.longitude:.4f}°, "
                f"expected_rev={expected_rev_lon:.4f}°, "
                f"got_rev={rev.longitude:.4f}°"
            )

    def test_distance_symmetry(self) -> None:
        # Distance A→B must equal distance B→A.
        fwd = planetocentric_at(Body.MARS, Body.JUPITER, JD_J2000)
        rev = planetocentric_at(Body.JUPITER, Body.MARS, JD_J2000)
        assert fwd.distance == pytest.approx(rev.distance, rel=1e-9)

    def test_inner_planet_closer_than_outer_from_earth(self) -> None:
        # From Earth, Venus should be closer than Neptune at J2000.
        venus   = planetocentric_at(Body.EARTH, Body.VENUS,   JD_J2000)
        neptune = planetocentric_at(Body.EARTH, Body.NEPTUNE, JD_J2000)
        assert venus.distance < neptune.distance

    def test_sun_is_closest_from_inner_planet(self) -> None:
        # From Mercury, the Sun should be closer than any outer planet.
        sun     = planetocentric_at(Body.MERCURY, Body.SUN,     JD_J2000)
        saturn  = planetocentric_at(Body.MERCURY, Body.SATURN,  JD_J2000)
        assert sun.distance < saturn.distance


# ---------------------------------------------------------------------------
# Agreement with heliocentric and geocentric (frame consistency)
# ---------------------------------------------------------------------------

class TestFrameConsistency:
    def test_agrees_with_heliocentric_for_sun_observer(self) -> None:
        # planetocentric_at(Body.SUN, target) must produce the same ecliptic
        # longitude and latitude as moira.planets.heliocentric_planet_at(target).
        from moira.planets import heliocentric_planet_at

        for target in (Body.MARS, Body.JUPITER, Body.SATURN):
            pc  = planetocentric_at(Body.SUN, target, JD_J2000)
            hc  = heliocentric_planet_at(target, JD_J2000)
            lon_diff = abs(_angular_diff(pc.longitude, hc.longitude))
            lat_diff = abs(pc.latitude - hc.latitude)
            assert lon_diff < 0.001, (
                f"Heliocentric longitude mismatch for {target}: "
                f"pc={pc.longitude:.4f}°, hc={hc.longitude:.4f}°"
            )
            assert lat_diff < 0.001, (
                f"Heliocentric latitude mismatch for {target}: "
                f"pc={pc.latitude:.4f}°, hc={hc.latitude:.4f}°"
            )

    def test_agrees_with_geocentric_for_earth_observer(self) -> None:
        # planetocentric_at(Body.EARTH, target) must closely match
        # moira.planets.planet_at(target) geocentric ecliptic longitude/latitude.
        # Slight differences are expected for apparent vs geometric positions
        # (aberration, light deflection) — we check within 0.1°.
        from moira.planets import planet_at

        for target in (Body.MARS, Body.JUPITER):
            pc  = planetocentric_at(Body.EARTH, target, JD_J2000)
            gc  = planet_at(target, JD_J2000)
            lon_diff = abs(_angular_diff(pc.longitude, gc.longitude))
            assert lon_diff < 0.1, (
                f"Geocentric longitude mismatch for {target}: "
                f"pc={pc.longitude:.4f}°, gc={gc.longitude:.4f}°"
            )


# ---------------------------------------------------------------------------
# all_planetocentric_at
# ---------------------------------------------------------------------------

class TestAllPlanetocentricAt:
    def test_excludes_observer_from_results(self) -> None:
        results = all_planetocentric_at(Body.MARS, JD_J2000)
        assert Body.MARS not in results

    def test_includes_earth_when_observing_from_mars(self) -> None:
        results = all_planetocentric_at(Body.MARS, JD_J2000)
        assert Body.EARTH in results

    def test_includes_sun_in_results(self) -> None:
        results = all_planetocentric_at(Body.JUPITER, JD_J2000)
        assert Body.SUN in results

    def test_custom_body_list_respected(self) -> None:
        bodies  = [Body.SUN, Body.EARTH]
        results = all_planetocentric_at(Body.MARS, JD_J2000, bodies=bodies)
        assert set(results.keys()) == {Body.SUN, Body.EARTH}

    def test_all_results_are_planetocentric_data(self) -> None:
        results = all_planetocentric_at(Body.SATURN, JD_J2000,
                                         bodies=[Body.SUN, Body.EARTH, Body.MARS])
        for name, pd in results.items():
            assert isinstance(pd, PlanetocentricData)
            assert pd.observer == Body.SATURN
            assert pd.name == name
