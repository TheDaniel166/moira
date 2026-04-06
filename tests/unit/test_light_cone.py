"""
Tests for moira.light_cone — Received-Light Chart Engine.

Verification strategy
---------------------
  - RECEIVED_LIGHT_BODIES: frozenset, contains major planets, excludes
    computed points (True Node, Lilith).
  - ReceivedLightPosition vessel: structural invariants, sign consistency
    with apparent_longitude, properties (light_travel_minutes,
    longitude_displacement, distance_au), __repr__.
  - received_light_at: ValueError on unknown body; results for every body
    in RECEIVED_LIGHT_BODIES pass structural invariants.
  - Physical invariants:
      - emission_jd < jd_ut for all bodies.
      - light_travel_days > 0 for all bodies.
      - Moon light travel time ≈ 1.3 s (≈ 0.000015 days).
      - Sun light travel time ≈ 8.3 min (≈ 0.00576 days).
      - Outer planet light travel times are larger (Neptune > Saturn > Jupiter).
  - Apparent vs geometric:
      - For slow outer planets, apparent and geometric longitudes differ by
        at most the expected light-cone displacement.
      - Moon displacement is near-zero (< 0.001°).
  - Fixed identity: apparent_longitude matches planet_at(apparent=True).
  - all_received_light_at: returns all requested bodies, custom list respected.
  - Retrograde consistency: retrograde == (speed < 0).
"""

from __future__ import annotations

import math

import pytest

from moira.constants import Body
from moira.light_cone import (
    RECEIVED_LIGHT_BODIES,
    ReceivedLightPosition,
    all_received_light_at,
    received_light_at,
)

# ---------------------------------------------------------------------------
# Reference epoch — J2000.0
# ---------------------------------------------------------------------------
JD_J2000 = 2451545.0   # 2000 Jan 1.5 TT

# Speed of light: 299792.458 km/s → km/day
_C_KM_PER_DAY = 299_792.458 * 86_400.0


# ---------------------------------------------------------------------------
# RECEIVED_LIGHT_BODIES invariants
# ---------------------------------------------------------------------------

class TestReceivedLightBodies:
    def test_is_frozenset(self) -> None:
        assert isinstance(RECEIVED_LIGHT_BODIES, frozenset)

    def test_contains_all_major_planets(self) -> None:
        for body in Body.ALL_PLANETS:
            assert body in RECEIVED_LIGHT_BODIES, f"{body!r} missing"

    def test_excludes_computed_points(self) -> None:
        for point in (Body.TRUE_NODE, Body.MEAN_NODE, Body.LILITH):
            assert point not in RECEIVED_LIGHT_BODIES

    def test_contains_moon(self) -> None:
        assert Body.MOON in RECEIVED_LIGHT_BODIES

    def test_contains_sun(self) -> None:
        assert Body.SUN in RECEIVED_LIGHT_BODIES


# ---------------------------------------------------------------------------
# Validation / error paths
# ---------------------------------------------------------------------------

class TestValidation:
    def test_unknown_body_raises(self) -> None:
        with pytest.raises(ValueError, match="RECEIVED_LIGHT_BODIES"):
            received_light_at("Comet_X", JD_J2000)

    def test_node_raises(self) -> None:
        with pytest.raises(ValueError, match="RECEIVED_LIGHT_BODIES"):
            received_light_at(Body.TRUE_NODE, JD_J2000)

    def test_lilith_raises(self) -> None:
        with pytest.raises(ValueError, match="RECEIVED_LIGHT_BODIES"):
            received_light_at(Body.LILITH, JD_J2000)


# ---------------------------------------------------------------------------
# ReceivedLightPosition vessel
# ---------------------------------------------------------------------------

class TestReceivedLightPositionVessel:
    def _make(self, body=Body.JUPITER) -> ReceivedLightPosition:
        return received_light_at(body, JD_J2000)

    def test_name_field_matches_body(self) -> None:
        pos = received_light_at(Body.SATURN, JD_J2000)
        assert pos.name == Body.SATURN

    def test_apparent_longitude_in_0_360(self) -> None:
        pos = self._make()
        assert 0.0 <= pos.apparent_longitude < 360.0

    def test_geometric_longitude_in_0_360(self) -> None:
        pos = self._make()
        assert 0.0 <= pos.geometric_longitude < 360.0

    def test_distance_km_positive(self) -> None:
        pos = self._make()
        assert pos.distance_km > 0.0

    def test_light_travel_days_positive(self) -> None:
        pos = self._make()
        assert pos.light_travel_days > 0.0

    def test_emission_jd_less_than_jd_ut(self) -> None:
        pos = self._make()
        assert pos.emission_jd < JD_J2000

    def test_emission_jd_consistent_with_light_travel(self) -> None:
        pos = self._make()
        assert pos.emission_jd == pytest.approx(JD_J2000 - pos.light_travel_days)

    def test_retrograde_consistent_with_speed(self) -> None:
        pos = self._make()
        assert pos.retrograde == (pos.speed < 0.0)

    def test_sign_consistent_with_apparent_longitude(self) -> None:
        pos = self._make()
        expected_index = int(pos.apparent_longitude // 30)
        signs = [
            "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
            "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
        ]
        assert pos.sign == signs[expected_index]

    def test_sign_degree_in_range(self) -> None:
        pos = self._make()
        assert 0.0 <= pos.sign_degree < 30.0

    def test_light_travel_minutes_consistent(self) -> None:
        pos = self._make()
        assert pos.light_travel_minutes == pytest.approx(pos.light_travel_days * 1440.0)

    def test_distance_au_consistent(self) -> None:
        pos = self._make()
        assert pos.distance_au == pytest.approx(pos.distance_km / 149_597_870.700)

    def test_longitude_displacement_in_range(self) -> None:
        pos = self._make()
        d = pos.longitude_displacement
        assert -180.0 < d <= 180.0

    def test_repr_contains_name_and_key_fields(self) -> None:
        pos = received_light_at(Body.MARS, JD_J2000)
        r = repr(pos)
        assert "Mars" in r
        assert "apparent=" in r
        assert "geometric=" in r
        assert "lt=" in r


# ---------------------------------------------------------------------------
# Physical light-travel time invariants
# ---------------------------------------------------------------------------

class TestLightTravelTimePhysics:
    def test_moon_light_travel_under_2_seconds(self) -> None:
        # Moon is ~384,400 km away → τ ≈ 1.28 s ≈ 0.0000148 days.
        moon = received_light_at(Body.MOON, JD_J2000)
        assert moon.light_travel_days < 2.0 / 86400.0  # < 2 seconds

    def test_sun_light_travel_around_8_minutes(self) -> None:
        # Sun is ~1 AU ≈ 149.6 million km → τ ≈ 8.317 min ≈ 0.00578 days.
        sun = received_light_at(Body.SUN, JD_J2000)
        assert 0.005 < sun.light_travel_days < 0.007

    def test_jupiter_light_travel_exceeds_sun(self) -> None:
        # Jupiter is ~5 AU away → τ > 5 × 8.3 min ≈ 41 min.
        jup = received_light_at(Body.JUPITER, JD_J2000)
        sun = received_light_at(Body.SUN, JD_J2000)
        assert jup.light_travel_days > sun.light_travel_days * 4.0

    def test_neptune_light_travel_exceeds_jupiter(self) -> None:
        nep = received_light_at(Body.NEPTUNE, JD_J2000)
        jup = received_light_at(Body.JUPITER, JD_J2000)
        assert nep.light_travel_days > jup.light_travel_days

    def test_light_travel_consistent_with_distance(self) -> None:
        # τ = distance / C should match the stored light_travel_days.
        for body in (Body.SUN, Body.MARS, Body.SATURN):
            pos = received_light_at(body, JD_J2000)
            expected_lt = pos.distance_km / _C_KM_PER_DAY
            assert pos.light_travel_days == pytest.approx(expected_lt, rel=1e-9)


# ---------------------------------------------------------------------------
# Apparent vs geometric agreement
# ---------------------------------------------------------------------------

class TestApparentVsGeometric:
    def test_moon_displacement_very_small(self) -> None:
        # Moon LTT ≈ 1.3 s.  The longitude_displacement includes LTT plus the
        # other apparent-position corrections (aberration, frame bias, etc.)
        # which the apparent pipeline applies.  For the Moon the total is
        # a few thousandths of a degree — well below 0.01°.
        moon = received_light_at(Body.MOON, JD_J2000)
        assert abs(moon.longitude_displacement) < 0.01

    def test_apparent_matches_planet_at_apparent(self) -> None:
        # apparent_longitude must match planet_at(apparent=True).
        from moira.planets import planet_at

        for body in (Body.MARS, Body.JUPITER, Body.SATURN):
            rl  = received_light_at(body, JD_J2000)
            geo = planet_at(body, JD_J2000, apparent=True)
            diff = abs((rl.apparent_longitude - geo.longitude + 180.0) % 360.0 - 180.0)
            assert diff < 1e-6, (
                f"apparent_longitude mismatch for {body}: "
                f"rl={rl.apparent_longitude:.6f}°, planet_at={geo.longitude:.6f}°"
            )

    def test_geometric_matches_planet_at_geometric(self) -> None:
        # geometric_longitude must match planet_at(apparent=False).
        from moira.planets import planet_at

        for body in (Body.MARS, Body.JUPITER):
            rl  = received_light_at(body, JD_J2000)
            geo = planet_at(body, JD_J2000, apparent=False)
            diff = abs((rl.geometric_longitude - geo.longitude + 180.0) % 360.0 - 180.0)
            assert diff < 1e-6, (
                f"geometric_longitude mismatch for {body}: "
                f"rl={rl.geometric_longitude:.6f}°, planet_at={geo.longitude:.6f}°"
            )

    def test_outer_planet_displacement_bounded(self) -> None:
        # At ~30 AU, Pluto moves ~1.4°/year ≈ 0.0038°/day.
        # Light takes ~5.3 h ≈ 0.22 days → expected displacement ≈ 0.001°.
        # Allow up to 0.5° for any body.
        for body in (Body.JUPITER, Body.SATURN, Body.NEPTUNE, Body.PLUTO):
            pos = received_light_at(body, JD_J2000)
            assert abs(pos.longitude_displacement) < 0.5, (
                f"Unexpectedly large displacement for {body}: "
                f"{pos.longitude_displacement:.4f}°"
            )

    def test_emission_jd_before_birth_jd(self) -> None:
        for body in Body.ALL_PLANETS:
            pos = received_light_at(body, JD_J2000)
            assert pos.emission_jd < JD_J2000, (
                f"emission_jd not before birth for {body}"
            )


# ---------------------------------------------------------------------------
# all_received_light_at
# ---------------------------------------------------------------------------

class TestAllReceivedLightAt:
    def test_default_returns_all_received_light_bodies(self) -> None:
        results = all_received_light_at(JD_J2000)
        assert set(results.keys()) == RECEIVED_LIGHT_BODIES

    def test_custom_body_list_respected(self) -> None:
        bodies = [Body.SUN, Body.MARS, Body.SATURN]
        results = all_received_light_at(JD_J2000, bodies=bodies)
        assert set(results.keys()) == set(bodies)

    def test_all_results_are_received_light_position_instances(self) -> None:
        results = all_received_light_at(
            JD_J2000,
            bodies=[Body.SUN, Body.MOON, Body.JUPITER],
        )
        for name, pos in results.items():
            assert isinstance(pos, ReceivedLightPosition)
            assert pos.name == name

    def test_single_body_list(self) -> None:
        results = all_received_light_at(JD_J2000, bodies=[Body.NEPTUNE])
        assert Body.NEPTUNE in results
        assert len(results) == 1
