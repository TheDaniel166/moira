"""
Tests for moira.geodetic — Geodetic Astrology Engine.

Verification strategy:
  - Exact known values for the trivially checkable equatorial (lat=0) case.
  - Structural / invariant checks for the full latitude range.
  - Sidereal path consistency: sidereal MC + ayanamsa = tropical MC.
  - Round-trip: geodetic_equivalents inverts geodetic_mc.
  - Vessel integrity: GeodeticChart holds the values produced by the functions.
"""

from __future__ import annotations

import math

import pytest

import moira.geodetic as geo


# ---------------------------------------------------------------------------
# Reference obliquity (J2000 approximate, adequate for unit tests)
# ---------------------------------------------------------------------------

OBL_J2000 = 23.4392911  # degrees — IAU 2006 mean obliquity at J2000.0


# ---------------------------------------------------------------------------
# geodetic_mc
# ---------------------------------------------------------------------------

class TestGeodeticMc:
    def test_zero_longitude_gives_zero_tropical_mc(self) -> None:
        assert geo.geodetic_mc(0.0) == pytest.approx(0.0)

    def test_positive_longitude_maps_directly(self) -> None:
        assert geo.geodetic_mc(45.0) == pytest.approx(45.0)

    def test_full_circle_wraps_to_zero(self) -> None:
        assert geo.geodetic_mc(360.0) == pytest.approx(0.0)

    def test_negative_longitude_wraps_correctly(self) -> None:
        # −30° W longitude → (−30) % 360 = 330°
        assert geo.geodetic_mc(-30.0) == pytest.approx(330.0)

    def test_overlarge_longitude_wraps(self) -> None:
        assert geo.geodetic_mc(400.0) == pytest.approx(40.0)

    def test_result_always_in_0_360(self) -> None:
        for lon in range(-360, 361, 15):
            mc = geo.geodetic_mc(float(lon))
            assert 0.0 <= mc < 360.0

    # Sidereal path
    def test_sidereal_mc_subtracts_ayanamsa(self) -> None:
        ayan = 23.0
        assert geo.geodetic_mc(0.0, ayanamsa_deg=ayan) == pytest.approx((360.0 - ayan) % 360.0)

    def test_sidereal_mc_at_location_equal_to_ayanamsa(self) -> None:
        # Where tropical MC = ayanamsa, sidereal MC = 0
        ayan = 23.85
        assert geo.geodetic_mc(ayan, ayanamsa_deg=ayan) == pytest.approx(0.0)

    def test_sidereal_mc_plus_ayanamsa_equals_tropical(self) -> None:
        ayan = 23.85
        for lon in range(0, 360, 30):
            tropical_mc = geo.geodetic_mc(float(lon))
            sidereal_mc = geo.geodetic_mc(float(lon), ayanamsa_deg=ayan)
            # sidereal + ayanamsa = tropical (mod 360)
            recovered = (sidereal_mc + ayan) % 360.0
            assert recovered == pytest.approx(tropical_mc % 360.0, abs=1e-9)


# ---------------------------------------------------------------------------
# geodetic_asc
# ---------------------------------------------------------------------------

class TestGeodeticAsc:
    def test_result_always_in_0_360(self) -> None:
        for lon in range(-180, 181, 30):
            for lat in range(-80, 81, 20):
                asc = geo.geodetic_asc(float(lon), float(lat), OBL_J2000)
                assert 0.0 <= asc < 360.0, (
                    f"ASC out of range for lon={lon}, lat={lat}: {asc}"
                )

    def test_equatorial_zero_longitude_asc_is_90(self) -> None:
        # At lat=0, lon=0 (MC=0° Aries), the horizon is perpendicular to the
        # meridian.  The equatorial ASC formula gives:
        #   y = −cos(0°) = −1,  x = sin(0°)·cos(ε) + tan(0°)·sin(ε) = 0
        #   raw = atan2(−1, 0) = 270°;  alt = 90°
        #   expected = 0° + 90° = 90°  →  alt is chosen
        # Result: ASC = 90° (0° Cancer).
        asc = geo.geodetic_asc(0.0, 0.0, OBL_J2000)
        assert asc == pytest.approx(90.0, abs=1e-6)

    def test_equatorial_asc_leads_mc_by_roughly_90_degrees(self) -> None:
        # At lat=0 the ASC is always ~90° ahead of the MC (the ecliptic equals
        # the celestial equator projected horizon at equatorial latitudes).
        # This is approximate: the exact offset varies with obliquity and MC.
        for lon in range(0, 360, 45):
            mc  = geo.geodetic_mc(float(lon))
            asc = geo.geodetic_asc(float(lon), 0.0, OBL_J2000)
            diff = (asc - mc) % 360.0
            # Within ±30° of 90° — obliquity effects shift the exact value.
            assert 60.0 <= diff <= 120.0, (
                f"ASC not ~90° ahead of MC at equator: lon={lon}, MC={mc}, ASC={asc}"
            )

    def test_northern_latitude_asc_is_consistent_with_obliquity(self) -> None:
        # London-like location (lon≈0°, lat≈51.5°) — verify we get a stable,
        # in-range result without asserting a specific degree (no oracle here).
        asc = geo.geodetic_asc(0.0, 51.5, OBL_J2000)
        # Published sources place the London geodetic ASC near 26°–27° Cancer
        # (i.e., ~116°–117°) for MC=0° Aries.
        assert asc == pytest.approx(116.5, abs=1.0)

    def test_symmetric_hemispheres(self) -> None:
        # ASC for +lat and −lat at the same longitude should be different
        # and both in range.  Use lon=45° — lon=90° (MC=Cancer) is degenerate:
        # the ASC collapses to 180° for all latitudes at that MC.
        asc_north = geo.geodetic_asc(45.0, 40.0, OBL_J2000)
        asc_south = geo.geodetic_asc(45.0, -40.0, OBL_J2000)
        assert asc_north != pytest.approx(asc_south)
        for asc in (asc_north, asc_south):
            assert 0.0 <= asc < 360.0

    def test_sidereal_asc_differs_from_tropical(self) -> None:
        ayan = 23.85
        asc_tropical  = geo.geodetic_asc(45.0, 40.0, OBL_J2000, ayanamsa_deg=0.0)
        asc_sidereal  = geo.geodetic_asc(45.0, 40.0, OBL_J2000, ayanamsa_deg=ayan)
        assert asc_tropical != pytest.approx(asc_sidereal)
        assert 0.0 <= asc_sidereal < 360.0


# ---------------------------------------------------------------------------
# geodetic_chart
# ---------------------------------------------------------------------------

class TestGeodeticChart:
    def test_vessel_holds_expected_mc(self) -> None:
        chart = geo.geodetic_chart(45.0, 40.0, OBL_J2000)
        assert chart.mc == pytest.approx(geo.geodetic_mc(45.0))

    def test_vessel_holds_expected_asc(self) -> None:
        chart = geo.geodetic_chart(45.0, 40.0, OBL_J2000)
        assert chart.asc == pytest.approx(geo.geodetic_asc(45.0, 40.0, OBL_J2000))

    def test_tropical_zodiac_default(self) -> None:
        chart = geo.geodetic_chart(45.0, 40.0, OBL_J2000)
        assert chart.zodiac == "tropical"
        assert chart.ayanamsa_deg == pytest.approx(0.0)

    def test_sidereal_zodiac_recorded(self) -> None:
        ayan = 23.85
        chart = geo.geodetic_chart(45.0, 40.0, OBL_J2000, ayanamsa_deg=ayan, zodiac="sidereal")
        assert chart.zodiac == "sidereal"
        assert chart.ayanamsa_deg == pytest.approx(ayan)

    def test_geo_longitude_stored_wrapped(self) -> None:
        # 200° should be stored as −160°
        chart = geo.geodetic_chart(200.0, 40.0, OBL_J2000)
        assert chart.geo_longitude == pytest.approx(-160.0)

    def test_mc_and_asc_always_in_range(self) -> None:
        for lon in range(-180, 181, 30):
            for lat in range(-70, 71, 20):
                chart = geo.geodetic_chart(float(lon), float(lat), OBL_J2000)
                assert 0.0 <= chart.mc  < 360.0
                assert 0.0 <= chart.asc < 360.0

    def test_repr_contains_key_fields(self) -> None:
        chart = geo.geodetic_chart(0.0, 51.5, OBL_J2000)
        r = repr(chart)
        assert "GeodeticChart" in r
        assert "MC=" in r
        assert "ASC=" in r


# ---------------------------------------------------------------------------
# geodetic_equivalents
# ---------------------------------------------------------------------------

class TestGeodeticEquivalents:
    def test_tropical_planet_maps_to_its_own_longitude(self) -> None:
        equiv = geo.geodetic_equivalents({"Sun": 45.0, "Moon": 200.0})
        assert equiv["Sun"]  == pytest.approx(45.0)
        # 200° wraps to −160°
        assert equiv["Moon"] == pytest.approx(-160.0)

    def test_zero_degree_planet_maps_to_greenwich(self) -> None:
        equiv = geo.geodetic_equivalents({"Sun": 0.0})
        assert equiv["Sun"] == pytest.approx(0.0)

    def test_output_wrapped_to_minus180_plus180(self) -> None:
        for lon in range(0, 360, 15):
            eq = geo.geodetic_equivalents({"P": float(lon)})
            geo_lon = eq["P"]
            assert -180.0 <= geo_lon <= 180.0, f"geo_lon out of range for planet at {lon}°: {geo_lon}"

    def test_round_trip_geodetic_mc_and_equivalents(self) -> None:
        # Forward: geo_lon → MC (tropical).  Inverse: MC → same geo_lon.
        for lon in range(-170, 181, 10):
            mc  = geo.geodetic_mc(float(lon))
            inv = geo.geodetic_equivalents({"P": mc})["P"]
            # Recover the original longitude (mod 360, then wrap to [-180, 180]).
            expected = lon if lon <= 180 else lon - 360
            assert inv == pytest.approx(float(expected), abs=1e-9)

    def test_sidereal_equivalents_add_ayanamsa(self) -> None:
        ayan = 23.85
        # Planet at 22° sidereal → geographic = 22 + 23.85 = 45.85°
        equiv = geo.geodetic_equivalents({"Sun": 22.0}, ayanamsa_deg=ayan)
        assert equiv["Sun"] == pytest.approx(45.85)

    def test_sidereal_equivalents_wrap_correctly(self) -> None:
        ayan = 23.85
        # Planet at 350° sidereal → geographic = (350 + 23.85) % 360 = 13.85°
        equiv = geo.geodetic_equivalents({"Sun": 350.0}, ayanamsa_deg=ayan)
        assert equiv["Sun"] == pytest.approx(13.85)

    def test_empty_input_returns_empty(self) -> None:
        assert geo.geodetic_equivalents({}) == {}

    def test_multiple_bodies(self) -> None:
        planets = {"Sun": 30.0, "Moon": 120.0, "Mercury": 270.0}
        equiv = geo.geodetic_equivalents(planets)
        assert set(equiv.keys()) == set(planets.keys())
        assert equiv["Sun"]     == pytest.approx(30.0)
        assert equiv["Moon"]    == pytest.approx(120.0)
        assert equiv["Mercury"] == pytest.approx(-90.0)  # 270° → −90°
