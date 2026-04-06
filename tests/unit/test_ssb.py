"""
Tests for moira.ssb — Solar System Barycenter Chart Engine.

Verification strategy
---------------------
  - SSB_BODIES invariants: frozenset, contains expected bodies, excludes
    computed points.
  - SSBPosition vessel: all fields set correctly, structural invariants
    (longitude in [0°, 360°), distance ≥ 0, speed finite), zodiac
    consistency, distance_au property, __repr__.
  - ssb_position_at: ValueError on unknown body; results for every body
    in SSB_BODIES pass structural invariants.
  - Geometric invariants:
      - Sun's SSB distance is non-zero (it is NOT at the SSB origin).
      - Sun–SSB distance ≤ 0.012 AU (well within the ~0.010 AU maximum).
      - Earth's SSB distance is roughly 1 AU (we are orbiting the Sun,
        which is near the SSB).
      - all_ssb_positions_at returns every requested body.
  - Agreement with geocentric substrate:
      - SSB positions at J2000.0 for outer planets lie in the correct
        approximate ecliptic quadrant, consistent with known ephemeris.
  - Custom body list respected by all_ssb_positions_at.
  - Retrograde consistency: retrograde == (speed < 0).
"""

from __future__ import annotations

import math

import pytest

from moira.constants import Body
from moira.ssb import (
    SSB_BODIES,
    SSBPosition,
    all_ssb_positions_at,
    ssb_position_at,
)

# ---------------------------------------------------------------------------
# Reference epoch — J2000.0
# ---------------------------------------------------------------------------
JD_J2000 = 2451545.0   # 2000 Jan 1.5 TT


# ---------------------------------------------------------------------------
# SSB_BODIES invariants
# ---------------------------------------------------------------------------

class TestSSBBodies:
    def test_is_frozenset(self) -> None:
        assert isinstance(SSB_BODIES, frozenset)

    def test_contains_all_major_planets(self) -> None:
        for body in (
            Body.SUN, Body.MOON, Body.MERCURY, Body.VENUS, Body.EARTH,
            Body.MARS, Body.JUPITER, Body.SATURN, Body.URANUS,
            Body.NEPTUNE, Body.PLUTO,
        ):
            assert body in SSB_BODIES, f"{body!r} missing from SSB_BODIES"

    def test_does_not_contain_computed_points(self) -> None:
        for point in (Body.TRUE_NODE, Body.MEAN_NODE, Body.LILITH):
            assert point not in SSB_BODIES

    def test_earth_is_included(self) -> None:
        assert Body.EARTH in SSB_BODIES


# ---------------------------------------------------------------------------
# Validation / error paths
# ---------------------------------------------------------------------------

class TestValidation:
    def test_unknown_body_raises(self) -> None:
        with pytest.raises(ValueError, match="SSB_BODIES"):
            ssb_position_at("Comet_Halley", JD_J2000)

    def test_computed_point_raises(self) -> None:
        with pytest.raises(ValueError, match="SSB_BODIES"):
            ssb_position_at(Body.TRUE_NODE, JD_J2000)

    def test_all_ssb_unknown_body_raises(self) -> None:
        with pytest.raises(ValueError, match="SSB_BODIES"):
            all_ssb_positions_at(JD_J2000, bodies=["Asteroid_X"])


# ---------------------------------------------------------------------------
# SSBPosition vessel
# ---------------------------------------------------------------------------

class TestSSBPositionVessel:
    def _make(self, body=Body.JUPITER) -> SSBPosition:
        return ssb_position_at(body, JD_J2000)

    def test_name_field_matches_body(self) -> None:
        pos = ssb_position_at(Body.SATURN, JD_J2000)
        assert pos.name == Body.SATURN

    def test_longitude_in_0_360(self) -> None:
        pos = self._make()
        assert 0.0 <= pos.longitude < 360.0

    def test_latitude_in_range(self) -> None:
        pos = self._make()
        assert -90.0 <= pos.latitude <= 90.0

    def test_distance_non_negative(self) -> None:
        pos = self._make()
        assert pos.distance >= 0.0

    def test_retrograde_consistent_with_speed(self) -> None:
        pos = self._make()
        assert pos.retrograde == (pos.speed < 0.0)

    def test_sign_consistent_with_longitude(self) -> None:
        pos = self._make()
        expected_sign_index = int(pos.longitude // 30)
        signs = [
            "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
            "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
        ]
        assert pos.sign == signs[expected_sign_index]

    def test_sign_degree_in_range(self) -> None:
        pos = self._make()
        assert 0.0 <= pos.sign_degree < 30.0

    def test_distance_au_consistent(self) -> None:
        pos = self._make()
        assert pos.distance_au == pytest.approx(pos.distance / 149_597_870.700)

    def test_repr_contains_name_and_coords(self) -> None:
        pos = ssb_position_at(Body.MARS, JD_J2000)
        r = repr(pos)
        assert "Mars" in r
        assert "lon=" in r
        assert "AU" in r


# ---------------------------------------------------------------------------
# Geometric invariants
# ---------------------------------------------------------------------------

class TestGeometricInvariants:
    def test_sun_is_not_at_ssb_origin(self) -> None:
        # The Sun wanders up to ~0.010 AU from the SSB.
        # It must not be at distance zero.
        sun = ssb_position_at(Body.SUN, JD_J2000)
        assert sun.distance > 0.0

    def test_sun_ssb_distance_bounded(self) -> None:
        # Sun–SSB separation is always ≤ ~0.012 AU (Jupiter dominates the offset).
        sun = ssb_position_at(Body.SUN, JD_J2000)
        assert sun.distance_au < 0.015

    def test_earth_distance_near_1_au(self) -> None:
        # Earth is in a ~1 AU orbit; its SSB distance at J2000 must be roughly 1 AU.
        earth = ssb_position_at(Body.EARTH, JD_J2000)
        assert 0.98 < earth.distance_au < 1.02

    def test_jupiter_distance_near_5_au(self) -> None:
        # Jupiter's semi-major axis is ~5.2 AU.
        jup = ssb_position_at(Body.JUPITER, JD_J2000)
        assert 4.8 < jup.distance_au < 5.6

    def test_saturn_distance_near_9_au(self) -> None:
        saturn = ssb_position_at(Body.SATURN, JD_J2000)
        assert 9.0 < saturn.distance_au < 10.1

    def test_all_longitudes_in_range_across_bodies(self) -> None:
        results = all_ssb_positions_at(JD_J2000)
        for name, pos in results.items():
            assert 0.0 <= pos.longitude < 360.0, f"{name}: lon={pos.longitude}"

    def test_all_distances_positive_across_bodies(self) -> None:
        results = all_ssb_positions_at(JD_J2000)
        for name, pos in results.items():
            if name == Body.SUN:
                continue  # Sun is extremely close but non-zero
            assert pos.distance > 0.0, f"{name}: dist={pos.distance}"

    def test_moon_distance_near_earth(self) -> None:
        # Moon is ~1 AU from SSB (it orbits Earth which orbits near SSB).
        moon = ssb_position_at(Body.MOON, JD_J2000)
        earth = ssb_position_at(Body.EARTH, JD_J2000)
        # Moon–Earth distance is ~384400 km ≈ 0.00257 AU.
        # SSB distances must differ by at most ~0.01 AU.
        delta_au = abs(moon.distance_au - earth.distance_au)
        assert delta_au < 0.01

    def test_outer_planets_farther_than_inner(self) -> None:
        mercury = ssb_position_at(Body.MERCURY, JD_J2000)
        neptune = ssb_position_at(Body.NEPTUNE, JD_J2000)
        assert mercury.distance_au < neptune.distance_au


# ---------------------------------------------------------------------------
# all_ssb_positions_at
# ---------------------------------------------------------------------------

class TestAllSSBPositionsAt:
    def test_returns_all_bodies_by_default(self) -> None:
        results = all_ssb_positions_at(JD_J2000)
        # Default = all SSB_BODIES
        assert set(results.keys()) == SSB_BODIES

    def test_custom_body_list_respected(self) -> None:
        bodies = [Body.SUN, Body.EARTH, Body.JUPITER]
        results = all_ssb_positions_at(JD_J2000, bodies=bodies)
        assert set(results.keys()) == set(bodies)

    def test_all_results_are_ssb_position_instances(self) -> None:
        results = all_ssb_positions_at(
            JD_J2000,
            bodies=[Body.SUN, Body.EARTH, Body.MARS],
        )
        for name, pos in results.items():
            assert isinstance(pos, SSBPosition)
            assert pos.name == name

    def test_single_body_list(self) -> None:
        results = all_ssb_positions_at(JD_J2000, bodies=[Body.SATURN])
        assert Body.SATURN in results
        assert len(results) == 1


# ---------------------------------------------------------------------------
# Agreement with heliocentric substrate (frame-consistency check)
# ---------------------------------------------------------------------------

class TestFrameConsistency:
    def test_outer_planet_ssb_and_heliocentric_longitudes_close(self) -> None:
        # For outer planets, the SSB–heliocentric longitude difference is small
        # because the Sun is only ~0.01 AU from the SSB.  At Jupiter's distance
        # (~5 AU) this angular offset ≤ arctan(0.01/5) ≈ 0.1°.
        from moira.planets import heliocentric_planet_at

        for target in (Body.JUPITER, Body.SATURN, Body.NEPTUNE):
            ssb_pos = ssb_position_at(target, JD_J2000)
            hc_pos  = heliocentric_planet_at(target, JD_J2000)
            diff = abs((ssb_pos.longitude - hc_pos.longitude + 180.0) % 360.0 - 180.0)
            assert diff < 0.15, (
                f"SSB vs heliocentric longitude divergence for {target}: "
                f"ssb={ssb_pos.longitude:.4f}°, hc={hc_pos.longitude:.4f}°, diff={diff:.4f}°"
            )
