"""
Tests for moira.geodetic — Geodetic Astrology Engine.

Verification strategy:
  - Exact known values for the trivially checkable equatorial (lat=0) case.
  - Structural / invariant checks for the full latitude range.
  - Sidereal path consistency: sidereal MC + ayanamsa = tropical MC.
  - Lane policy: the tropical lane refuses any ayanamsa, in either form.
  - Round-trip: geodetic_equivalents inverts geodetic_mc.
  - Vessel integrity: GeodeticChart holds the values produced by the functions.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from dataclasses import replace
from types import SimpleNamespace

import pytest

import moira.geodetic as geo
from support.numeric_assertions import (
    NumericSemantics,
    ToleranceContract,
    Unit,
    assert_circular_degrees,
)


# ---------------------------------------------------------------------------
# Reference obliquity (J2000 approximate, adequate for unit tests)
# ---------------------------------------------------------------------------

OBL_J2000 = 23.4392911  # degrees — IAU 2006 mean obliquity at J2000.0


def _reference_ascendant_from_horizon(
    longitude_deg: float,
    latitude_deg: float,
    obliquity_deg: float,
) -> float:
    """Independent root search using the spherical altitude equation.

    This deliberately does not use Moira's tangent-form Ascendant calculation
    or its branch selector. It scans for zero-altitude ecliptic intersections,
    bisects each crossing, and selects the root whose local hour angle is
    advancing through the eastern horizon. The altitude relation follows the
    USNO local-hour-angle equation: https://aa.usno.navy.mil/faq/alt_az.
    """
    eps = math.radians(obliquity_deg)
    phi = math.radians(latitude_deg)
    mc = math.radians(longitude_deg % 360.0)
    armc = math.atan2(math.sin(mc) * math.cos(eps), math.cos(mc))

    def altitude_sine(longitude: float) -> float:
        lam = math.radians(longitude)
        ra = math.atan2(math.sin(lam) * math.cos(eps), math.cos(lam))
        dec = math.asin(math.sin(eps) * math.sin(lam))
        hour_angle = armc - ra
        return (
            math.sin(phi) * math.sin(dec)
            + math.cos(phi) * math.cos(dec) * math.cos(hour_angle)
        )

    crossings: list[float] = []
    steps = 1440
    previous_lon = 0.0
    previous_value = altitude_sine(previous_lon)
    for index in range(1, steps + 1):
        current_lon = 360.0 * index / steps
        current_value = altitude_sine(current_lon)
        if previous_value * current_value < 0.0:
            lo, hi = previous_lon, current_lon
            lo_value = previous_value
            for _ in range(64):
                mid = (lo + hi) / 2.0
                mid_value = altitude_sine(mid)
                if lo_value * mid_value <= 0.0:
                    hi = mid
                else:
                    lo = mid
                    lo_value = mid_value
            crossings.append((lo + hi) / 2.0 % 360.0)
        previous_lon, previous_value = current_lon, current_value

    rising = []
    for longitude in crossings:
        lam = math.radians(longitude)
        ra = math.atan2(math.sin(lam) * math.cos(eps), math.cos(lam))
        if math.sin(armc - ra) < 0.0:
            rising.append(longitude)
    assert len(rising) == 1, f"expected one rising horizon root, got {rising!r}"
    return rising[0]

_GEOGRAPHIC_ANCHOR = ToleranceContract(
    name="geodetic_geographic_anchor",
    semantics=NumericSemantics.CIRCULAR,
    unit=Unit.DEGREES,
    absolute=1e-12,
    basis=(
        "A geographic meridian is zodiac-independent, so every lane must "
        "return the same anchor; 1e-12 deg bounds only the subtract-then-"
        "re-add round-off of the ayanamsa in binary64."
    ),
)


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
    @pytest.mark.parametrize(
        ("longitude", "latitude"),
        [
            (-74.0060, 40.7128),
            (151.2093, -33.8688),
            (18.4241, -33.9249),
            (179.9, 66.5),
            (-179.9, 66.5),
            (0.13, 89.999),
        ],
    )
    def test_matches_independent_horizon_root(self, longitude: float, latitude: float) -> None:
        expected = _reference_ascendant_from_horizon(longitude, latitude, OBL_J2000)
        actual = geo.geodetic_asc(longitude, latitude, OBL_J2000)
        assert_circular_degrees(
            actual,
            expected,
            tolerance=ToleranceContract(
                name="independent_geodetic_asc_horizon_root",
                semantics=NumericSemantics.CIRCULAR,
                unit=Unit.DEGREES,
                absolute=1e-8,
                basis="Independent altitude-equation root search with bisection.",
            ),
        )

    def test_reference_grid_across_obliquity_longitude_and_hemispheres(self) -> None:
        longitudes = (-173.1, -121.7, -37.3, 7.1, 46.9, 103.7, 177.3)
        latitudes = (-89.0, -72.5, -31.25, 0.0, 28.75, 68.5, 89.0)
        for obliquity in (22.0, OBL_J2000, 25.0):
            for longitude in longitudes:
                for latitude in latitudes:
                    expected = _reference_ascendant_from_horizon(
                        longitude, latitude, obliquity
                    )
                    actual = geo.geodetic_asc(longitude, latitude, obliquity)
                    assert_circular_degrees(
                        actual,
                        expected,
                        tolerance=ToleranceContract(
                            name="geodetic_asc_reference_grid",
                            semantics=NumericSemantics.CIRCULAR,
                            unit=Unit.DEGREES,
                            absolute=1e-8,
                            basis=(
                                "Independent zero-altitude root search across the "
                                "admitted obliquity range and both hemispheres."
                            ),
                        ),
                    )

    def test_longitude_turns_are_metamorphically_invariant(self) -> None:
        for longitude in (-179.7, -73.4, 0.1, 88.2, 179.8):
            expected = geo.geodetic_asc(longitude, 42.0, OBL_J2000)
            for turns in (-3, -1, 1, 4):
                actual = geo.geodetic_asc(
                    longitude + turns * 360.0, 42.0, OBL_J2000
                )
                assert_circular_degrees(
                    actual,
                    expected,
                    tolerance=ToleranceContract(
                        name="geodetic_longitude_turn_invariance",
                        semantics=NumericSemantics.CIRCULAR,
                        unit=Unit.DEGREES,
                        absolute=1e-12,
                        basis="Longitude is a circular coordinate with 360-degree turns.",
                    ),
                )

    def test_result_always_in_0_360(self) -> None:
        # Swept to +/-89 deg: the admitted latitude domain, one degree inside
        # each pole.  The poles themselves are refused (see
        # test_polar_latitude_is_refused) because the two tangent roots become
        # exactly equidistant there.
        for lon in range(-180, 181, 30):
            for lat in range(-89, 90):
                asc = geo.geodetic_asc(float(lon), float(lat), OBL_J2000)
                assert 0.0 <= asc < 360.0, (
                    f"ASC out of range for lon={lon}, lat={lat}: {asc}"
                )

    def test_polar_latitude_is_refused(self) -> None:
        for lat in (90.0, -90.0, 89.9999999, -89.9999999):
            with pytest.raises(ValueError, match="geographic pole"):
                geo.geodetic_asc(0.0, lat, OBL_J2000)
            with pytest.raises(ValueError, match="geographic pole"):
                geo.geodetic_chart(0.0, lat, OBL_J2000)

    def test_latitude_beyond_the_pole_is_refused_as_out_of_range(self) -> None:
        for lat in (90.5, -90.5):
            with pytest.raises(ValueError, match=r"\[-90, 90\]"):
                geo.geodetic_asc(0.0, lat, OBL_J2000)

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
        assert asc_sidereal == pytest.approx((asc_tropical - ayan) % 360.0, abs=1e-12)
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
        assert chart.provenance is not None
        assert chart.provenance.calculation_source == "direct_inputs"
        assert chart.provenance.latitude_convention == (
            "caller_supplied_geographic_latitude_no_conversion"
        )

    def test_sidereal_zodiac_recorded(self) -> None:
        ayan = 23.85
        chart = geo.geodetic_chart(45.0, 40.0, OBL_J2000, ayanamsa_deg=ayan, zodiac="sidereal")
        assert chart.zodiac == "sidereal"
        assert chart.ayanamsa_deg == pytest.approx(ayan)

    def test_sidereal_ascendant_is_tropical_ascendant_reduced_by_offset(self) -> None:
        ayan = 23.85
        tropical = geo.geodetic_chart(45.0, 40.0, OBL_J2000)
        sidereal = geo.geodetic_chart(
            45.0, 40.0, OBL_J2000, ayanamsa_deg=ayan, zodiac="sidereal"
        )
        assert sidereal.asc == pytest.approx((tropical.asc - ayan) % 360.0, abs=1e-12)
        assert sidereal.mc == pytest.approx((tropical.mc - ayan) % 360.0, abs=1e-12)

    def test_sidereal_zodiac_requires_an_explicit_offset(self) -> None:
        with pytest.raises(ValueError, match="ayanamsa_deg is required"):
            geo.geodetic_chart(45.0, 40.0, OBL_J2000, zodiac="sidereal")

    def test_explicit_zero_is_a_valid_sidereal_offset(self) -> None:
        chart = geo.geodetic_chart(
            45.0, 40.0, OBL_J2000, ayanamsa_deg=0.0, zodiac="sidereal"
        )
        assert chart.zodiac == "sidereal"
        assert chart.ayanamsa_deg == 0.0

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

    def test_direct_vessel_construction_enforces_structural_invariants(self) -> None:
        chart = geo.geodetic_chart(45.0, 40.0, OBL_J2000)
        with pytest.raises(ValueError, match=r"mc must be in \[0, 360\)"):
            replace(chart, mc=360.0)
        with pytest.raises(ValueError, match="geo_longitude must be wrapped"):
            replace(chart, geo_longitude=200.0)
        with pytest.raises(ValueError, match=r"Earth obliquity must be in \[22, 25\]"):
            replace(chart, obliquity=91.0)
        with pytest.raises(ValueError, match="tropical zodiac must not carry"):
            replace(chart, ayanamsa_deg=1.0)


class TestGeodeticLocation:
    @pytest.mark.parametrize("latitude_kind", ["unspecified", "geodetic", "astronomical"])
    def test_typed_location_preserves_numeric_latitude_and_metadata(
        self, latitude_kind: str
    ) -> None:
        location = geo.GeodeticLocation(
            latitude_deg=40.7128,
            longitude_deg=-74.006,
            latitude_kind=latitude_kind,
            datum="WGS84",
            coordinate_epoch=2026.5,
            ellipsoidal_height_m=11.0,
            source="test fixture",
        )
        typed = geo.geodetic_chart_at_location(location, OBL_J2000)
        legacy = geo.geodetic_chart(-74.006, 40.7128, OBL_J2000)

        assert typed.geo_latitude == legacy.geo_latitude
        assert typed.geo_longitude == legacy.geo_longitude
        assert typed.mc == legacy.mc
        assert typed.asc == legacy.asc
        assert typed.provenance is not None
        assert typed.provenance.location == location
        with pytest.raises((AttributeError, TypeError)):
            location.latitude_deg = 1.0  # type: ignore[misc]

    def test_geocentric_latitude_requires_an_explicit_conversion(self) -> None:
        location = geo.GeodeticLocation(40.0, -70.0, latitude_kind="geocentric")
        with pytest.raises(ValueError, match="geocentric latitude requires an explicit conversion"):
            geo.geodetic_chart_at_location(location, OBL_J2000)

    def test_location_metadata_validates_bounds_and_height_reference(self) -> None:
        with pytest.raises(ValueError, match="latitude_deg"):
            geo.GeodeticLocation(91.0, 0.0)
        with pytest.raises(ValueError, match="longitude_deg"):
            geo.GeodeticLocation(0.0, 181.0)
        with pytest.raises(ValueError, match="requires an explicit datum or reference_frame"):
            geo.GeodeticLocation(0.0, 0.0, ellipsoidal_height_m=5.0)


class TestGeodeticSensitivity:
    def test_analytic_ascendant_derivatives_match_centered_differences(self) -> None:
        longitude, latitude, obliquity = 45.2, 35.0, 23.4
        chart = geo.geodetic_chart(longitude, latitude, obliquity)
        result = geo.geodetic_chart_sensitivity(
            chart,
            geo.GeodeticInputUncertainty(0.01, 0.01, 0.01),
        )
        step = 1e-4

        def centered(plus: float, minus: float) -> float:
            return ((plus - minus + 180.0) % 360.0 - 180.0) / (2.0 * step)

        by_longitude = centered(
            geo.geodetic_asc(longitude + step, latitude, obliquity),
            geo.geodetic_asc(longitude - step, latitude, obliquity),
        )
        by_latitude = centered(
            geo.geodetic_asc(longitude, latitude + step, obliquity),
            geo.geodetic_asc(longitude, latitude - step, obliquity),
        )
        by_obliquity = centered(
            geo.geodetic_asc(longitude, latitude, obliquity + step),
            geo.geodetic_asc(longitude, latitude, obliquity - step),
        )

        assert result.asc_derivatives.geo_longitude_deg == pytest.approx(by_longitude, abs=1e-6)
        assert result.asc_derivatives.geo_latitude_deg == pytest.approx(by_latitude, abs=1e-6)
        assert result.asc_derivatives.obliquity_deg == pytest.approx(by_obliquity, abs=1e-6)
        assert result.mc_derivatives == geo.GeodeticAngleDerivatives(1.0, 0.0, 0.0)
        assert result.mc_linearized_radius_deg == pytest.approx(0.01)
        assert result.interpretation == "first_order_local_not_a_bound"
        assert result.latitude_margin_to_pole_deg == pytest.approx(55.0)

    def test_uncertainty_cannot_cross_calculation_domain_boundaries(self) -> None:
        ordinary = geo.geodetic_chart(10.0, 40.0, OBL_J2000)
        with pytest.raises(ValueError, match="polar refusal boundary"):
            geo.geodetic_chart_sensitivity(
                ordinary,
                geo.GeodeticInputUncertainty(latitude_deg=51.0),
            )
        with pytest.raises(ValueError, match="obliquity uncertainty"):
            geo.geodetic_chart_sensitivity(
                ordinary,
                geo.GeodeticInputUncertainty(obliquity_deg=1.5),
            )

    def test_tangent_horizon_has_no_local_sensitivity(self) -> None:
        obliquity = OBL_J2000
        with pytest.raises(ValueError, match="coincident_planes"):
            geo.geodetic_chart(90.0, obliquity - 90.0, obliquity)


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


class TestGeodeticInputValidation:
    def test_geodetic_mc_rejects_non_finite_inputs(self) -> None:
        with pytest.raises(ValueError, match="geo_longitude"):
            geo.geodetic_mc(float("nan"))
        with pytest.raises(ValueError, match="ayanamsa_deg"):
            geo.geodetic_mc(0.0, ayanamsa_deg=float("nan"))

    @pytest.mark.parametrize(
        ("longitude", "latitude", "obliquity", "ayanamsa", "message"),
        [
            (float("nan"), 0.0, OBL_J2000, 0.0, "geo_longitude"),
            (0.0, float("nan"), OBL_J2000, 0.0, "geo_latitude"),
            (0.0, 91.0, OBL_J2000, 0.0, "geo_latitude"),
            (0.0, 0.0, float("nan"), 0.0, "obliquity"),
            (0.0, 0.0, 21.99, 0.0, "Earth obliquity must be in"),
            (0.0, 0.0, 25.01, 0.0, "Earth obliquity must be in"),
            (0.0, 0.0, OBL_J2000, float("nan"), "ayanamsa_deg"),
        ],
    )
    def test_geodetic_asc_rejects_invalid_inputs(
        self,
        longitude: float,
        latitude: float,
        obliquity: float,
        ayanamsa: float,
        message: str,
    ) -> None:
        with pytest.raises(ValueError, match=message):
            geo.geodetic_asc(longitude, latitude, obliquity, ayanamsa_deg=ayanamsa)

    def test_geodetic_chart_rejects_invalid_zodiac(self) -> None:
        with pytest.raises(ValueError, match="zodiac"):
            geo.geodetic_chart(0.0, 51.5, OBL_J2000, zodiac="invented")

    def test_geodetic_chart_rejects_tropical_with_ayanamsa_offset(self) -> None:
        with pytest.raises(ValueError, match="tropical zodiac must not carry an ayanamsa offset"):
            geo.geodetic_chart(0.0, 51.5, OBL_J2000, ayanamsa_deg=23.85, zodiac="tropical")

    def test_geodetic_chart_admits_tropical_with_explicit_zero_ayanamsa(self) -> None:
        # The direct API accepts explicit zero as equivalent to an omitted
        # tropical offset; nonzero offsets contradict the tropical lane.
        chart = geo.geodetic_chart(0.0, 51.5, OBL_J2000, ayanamsa_deg=0.0, zodiac="tropical")
        assert chart.ayanamsa_deg == 0.0

    @pytest.mark.parametrize("obliquity", [22.0, 25.0])
    def test_geodetic_chart_admits_earth_obliquity_envelope_boundaries(
        self, obliquity: float
    ) -> None:
        result = geo.geodetic_chart(0.0, 40.0, obliquity)
        assert result.obliquity == obliquity

    def test_geodetic_from_chart_wrappers_reject_tropical_with_ayanamsa_system(self) -> None:
        # Both wrappers check lane policy before reading the chart, so a bare
        # stand-in proves the refusal without an ephemeris.
        chart = SimpleNamespace()
        with pytest.raises(ValueError, match="tropical zodiac must not carry an ayanamsa_system"):
            geo.geodetic_chart_from_chart(chart, zodiac="tropical", ayanamsa_system="Lahiri")
        with pytest.raises(ValueError, match="tropical zodiac must not carry an ayanamsa_system"):
            geo.geodetic_equivalents_from_chart(chart, zodiac="tropical", ayanamsa_system="Lahiri")

    def test_geodetic_from_chart_wrappers_still_require_sidereal_ayanamsa_system(self) -> None:
        chart = SimpleNamespace()
        with pytest.raises(ValueError, match="ayanamsa_system is required"):
            geo.geodetic_chart_from_chart(chart, zodiac="sidereal")
        with pytest.raises(ValueError, match="ayanamsa_system is required"):
            geo.geodetic_equivalents_from_chart(chart, zodiac="sidereal")

    def test_geodetic_equivalents_rejects_invalid_inputs(self) -> None:
        with pytest.raises(ValueError, match="body names"):
            geo.geodetic_equivalents({"": 30.0})
        with pytest.raises(ValueError, match="longitude"):
            geo.geodetic_equivalents({"Sun": float("nan")})
        with pytest.raises(ValueError, match="ayanamsa_deg"):
            geo.geodetic_equivalents({"Sun": 30.0}, ayanamsa_deg=float("nan"))


# ---------------------------------------------------------------------------
# ChartContext wrappers: epoch and lane resolution
# ---------------------------------------------------------------------------

class TestGeodeticChartProvenance:
    def test_chart_context_provenance_records_epochs_models_and_lane(self) -> None:
        from moira.obliquity import true_obliquity_with_truth

        context = SimpleNamespace(
            jd_ut=2451545.0,
            jd_tt=2451545.0007,
            latitude=40.7128,
            longitude=-74.0060,
        )
        result = geo.geodetic_chart_from_chart(
            context, zodiac="sidereal", ayanamsa_system="Lahiri"
        )
        provenance = result.provenance
        truth = true_obliquity_with_truth(context.jd_tt)

        assert provenance is not None
        assert provenance.calculation_source == "chart_context"
        assert provenance.chart_jd_ut == context.jd_ut
        assert provenance.chart_jd_tt == context.jd_tt
        assert provenance.obliquity_timescale == "TT"
        assert provenance.mean_obliquity_model == truth.mean_model
        assert provenance.nutation_model == truth.nutation_model
        assert provenance.ayanamsa_system == "Lahiri"
        assert provenance.ayanamsa_timescale == "UT"


@pytest.mark.requires_ephemeris
class TestGeodeticChartFromChartEpoch:
    """``ayanamsa`` is contracted for UT; the vessel's TT must not be fed to it."""

    def test_ayanamsa_resolves_on_the_ut_scale(self, moira_engine) -> None:
        from moira.sidereal import ayanamsa

        ctx = moira_engine.relocated_chart(
            datetime(100, 1, 1, 12, tzinfo=timezone.utc), 51.5, -0.13, bodies=["Sun"]
        )
        chart = geo.geodetic_chart_from_chart(
            ctx, zodiac="sidereal", ayanamsa_system="Lahiri"
        )

        assert chart.ayanamsa_deg == pytest.approx(
            ayanamsa(ctx.jd_ut, "Lahiri"), abs=0.0
        )

    def test_the_tt_scale_would_cross_the_longitude_covenant(self, moira_engine) -> None:
        # ΔT is hours at this epoch, so the duplicate UT→TT shift is not a
        # sub-arcsecond curiosity — it exceeds the 1e-6 deg longitude covenant.
        from moira.sidereal import ayanamsa

        ctx = moira_engine.relocated_chart(
            datetime(100, 1, 1, 12, tzinfo=timezone.utc), 51.5, -0.13, bodies=["Sun"]
        )
        residual = abs(ayanamsa(ctx.jd_tt, "Lahiri") - ayanamsa(ctx.jd_ut, "Lahiri"))
        assert residual > 1e-6

    def test_obliquity_still_resolves_on_the_tt_scale(self, moira_engine) -> None:
        from moira.obliquity import true_obliquity

        ctx = moira_engine.relocated_chart(
            datetime(2000, 1, 1, 12, tzinfo=timezone.utc), 51.5, -0.13, bodies=["Sun"]
        )
        chart = geo.geodetic_chart_from_chart(ctx)
        assert chart.obliquity == pytest.approx(true_obliquity(ctx.jd_tt), abs=0.0)

@pytest.mark.requires_ephemeris
class TestGeodeticEquivalentsLaneParity:
    """The ayanamsa must not be applied twice when inverting a chart vessel."""

    def test_both_lanes_return_the_same_geographic_anchor(self, moira_engine) -> None:
        ctx = moira_engine.relocated_chart(
            datetime(2000, 1, 1, 12, tzinfo=timezone.utc), 51.5, -0.13,
            bodies=["Sun", "Moon"],
        )
        tropical = geo.geodetic_equivalents_from_chart(ctx, bodies=["Sun", "Moon"])
        sidereal = geo.geodetic_equivalents_from_chart(
            ctx, bodies=["Sun", "Moon"], zodiac="sidereal", ayanamsa_system="Lahiri"
        )
        for body in ("Sun", "Moon"):
            assert_circular_degrees(
                sidereal[body], tropical[body], tolerance=_GEOGRAPHIC_ANCHOR
            )

    def test_anchor_is_the_tropical_longitude_wrapped(self, moira_engine) -> None:
        from moira.geoutils import wrap_longitude_deg

        ctx = moira_engine.relocated_chart(
            datetime(2000, 1, 1, 12, tzinfo=timezone.utc), 51.5, -0.13,
            bodies=["Sun", "Moon"],
        )
        for zodiac, system in (("tropical", None), ("sidereal", "Lahiri")):
            equivalents = geo.geodetic_equivalents_from_chart(
                ctx, bodies=["Sun"], zodiac=zodiac, ayanamsa_system=system
            )
            assert_circular_degrees(
                equivalents["Sun"],
                wrap_longitude_deg(ctx.planets["Sun"].longitude),
                tolerance=_GEOGRAPHIC_ANCHOR,
            )


class TestGeodeticEquivalentsResult:
    @staticmethod
    def _chart_context() -> SimpleNamespace:
        return SimpleNamespace(
            jd_ut=2451545.0,
            jd_tt=2451545.0007,
            planets={
                "Sun": SimpleNamespace(longitude=137.68),
                "Moon": SimpleNamespace(longitude=232.22),
            },
        )

    def test_tropical_result_keeps_order_values_and_chart_receipt(self) -> None:
        chart = self._chart_context()
        result = geo.geodetic_equivalents_result_from_chart(chart)
        expected = geo.geodetic_equivalents(
            {name: item.longitude for name, item in chart.planets.items()}
        )

        assert result.geographic_longitudes == expected
        assert geo.geodetic_equivalents_from_chart(chart) == expected
        assert [item.body for item in result.positions] == ["Sun", "Moon"]
        sun = result.positions[0]
        assert sun.source_tropical_longitude_deg == 137.68
        assert sun.selected_zodiac_longitude_deg == 137.68
        assert sun.geographic_longitude_deg == expected["Sun"]
        assert result.provenance.chart_jd_ut == chart.jd_ut
        assert result.provenance.chart_jd_tt == chart.jd_tt
        assert result.provenance.zodiac == "tropical"
        assert result.provenance.ayanamsa_deg == 0.0
        assert result.provenance.ayanamsa_timescale is None

    def test_sidereal_result_records_the_actual_ut_lane(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import moira.sidereal

        resolved_epochs: list[tuple[float, str]] = []

        def fixed_ayanamsa(jd: float, system: str) -> float:
            resolved_epochs.append((jd, system))
            return 24.0

        monkeypatch.setattr(moira.sidereal, "ayanamsa", fixed_ayanamsa)
        chart = self._chart_context()
        result = geo.geodetic_equivalents_result_from_chart(
            chart, bodies=["Moon", "Sun"], zodiac="sidereal", ayanamsa_system="Lahiri"
        )

        assert [item.body for item in result.positions] == ["Moon", "Sun"]
        expected_legacy = geo.geodetic_equivalents(
            {"Moon": (232.22 - 24.0) % 360.0, "Sun": (137.68 - 24.0) % 360.0},
            24.0,
        )
        assert result.geographic_longitudes == expected_legacy
        assert geo.geodetic_equivalents_from_chart(
            chart, bodies=["Moon", "Sun"], zodiac="sidereal", ayanamsa_system="Lahiri"
        ) == expected_legacy
        assert result.positions[0].selected_zodiac_longitude_deg == pytest.approx(208.22)
        assert result.positions[0].geographic_longitude_deg == pytest.approx(-127.78)
        assert result.provenance.ayanamsa_deg == 24.0
        assert result.provenance.ayanamsa_system == "Lahiri"
        assert result.provenance.ayanamsa_timescale == "UT"
        assert resolved_epochs == [(chart.jd_ut, "Lahiri"), (chart.jd_ut, "Lahiri")]

    def test_duplicate_body_selection_is_stably_collapsed(self) -> None:
        result = geo.geodetic_equivalents_result_from_chart(
            self._chart_context(), bodies=["Sun", "Moon", "Sun"]
        )
        assert [item.body for item in result.positions] == ["Sun", "Moon"]

    def test_detailed_result_refuses_duplicate_position_keys(self) -> None:
        position = geo.GeodeticEquivalentPosition("Sun", 10.0, 10.0, 10.0)
        provenance = geo.GeodeticEquivalentsProvenance(
            chart_jd_ut=2451545.0,
            chart_jd_tt=2451545.0,
        )
        with pytest.raises(ValueError, match="must be unique"):
            geo.GeodeticEquivalentsResult((position, position), provenance)
