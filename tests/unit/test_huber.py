"""
tests/unit/test_huber.py

Unit tests for the Huber Astrological Psychology Engine (moira.huber).

Scope: Age Point, golden-section house zones, Dynamic Intensity Curve,
       planet intensity scoring, and result vessel invariants.
"""

import math
import pytest

from moira.huber import (
    # Enums
    HouseZone,
    # Constants
    PHI,
    PHI_COMPLEMENT,
    CYCLE_YEARS,
    YEARS_PER_HOUSE,
    # Result vessels
    HouseZoneProfile,
    AgePointPosition,
    DynamicIntensity,
    PlanetIntensityScore,
    ChartIntensityProfile,
    # Functions
    house_zones,
    age_point,
    age_point_contacts,
    dynamic_intensity,
    intensity_at,
    chart_intensity_profile,
)
from moira.houses import calculate_houses


# ===========================================================================
# CONSTANTS
# ===========================================================================

class TestConstants:
    def test_phi_is_golden_ratio(self):
        expected = (1.0 + math.sqrt(5.0)) / 2.0 - 1.0
        assert abs(PHI - expected) < 1e-12

    def test_phi_complement_sums_to_one(self):
        assert abs(PHI + PHI_COMPLEMENT - 1.0) < 1e-12

    def test_cycle_is_72_years(self):
        assert CYCLE_YEARS == 72.0

    def test_years_per_house_is_6(self):
        assert YEARS_PER_HOUSE == 6.0

    def test_12_houses_times_6_equals_72(self):
        assert 12 * YEARS_PER_HOUSE == CYCLE_YEARS


# ===========================================================================
# HOUSE ZONE ENUM
# ===========================================================================

class TestHouseZoneEnum:
    def test_three_members(self):
        assert len(HouseZone) == 3

    def test_values(self):
        assert HouseZone.CARDINAL == "cardinal"
        assert HouseZone.FIXED == "fixed"
        assert HouseZone.MUTABLE == "mutable"


# ===========================================================================
# HOUSE ZONES (golden-section division)
# ===========================================================================

@pytest.mark.requires_ephemeris
class TestHouseZones:
    @pytest.fixture
    def koch_cusps(self):
        return calculate_houses(2451545.0, 40.7128, -74.0060, system="K")

    def test_twelve_profiles(self, koch_cusps):
        zones = house_zones(koch_cusps)
        assert len(zones) == 12

    def test_house_numbers_1_through_12(self, koch_cusps):
        zones = house_zones(koch_cusps)
        assert [z.house for z in zones] == list(range(1, 13))

    def test_balance_point_fraction_is_phi_complement(self, koch_cusps):
        zones = house_zones(koch_cusps)
        for z in zones:
            assert abs(z.balance_point_fraction - PHI_COMPLEMENT) < 1e-10

    def test_low_point_fraction_is_phi(self, koch_cusps):
        zones = house_zones(koch_cusps)
        for z in zones:
            assert abs(z.low_point_fraction - PHI) < 1e-10

    def test_balance_point_before_low_point(self, koch_cusps):
        """Balance Point must be closer to the cusp than the Low Point."""
        zones = house_zones(koch_cusps)
        for z in zones:
            bp_offset = (z.balance_point_longitude - z.cusp_longitude) % 360.0
            lp_offset = (z.low_point_longitude - z.cusp_longitude) % 360.0
            assert bp_offset < lp_offset

    def test_house_sizes_are_positive(self, koch_cusps):
        zones = house_zones(koch_cusps)
        for z in zones:
            assert z.house_size > 0.0

    def test_house_sizes_sum_to_360(self, koch_cusps):
        zones = house_zones(koch_cusps)
        total = sum(z.house_size for z in zones)
        assert abs(total - 360.0) < 0.01

    def test_profiles_are_frozen(self, koch_cusps):
        zones = house_zones(koch_cusps)
        with pytest.raises(AttributeError):
            zones[0].house = 99


# ===========================================================================
# AGE POINT
# ===========================================================================

@pytest.mark.requires_ephemeris
class TestAgePoint:
    @pytest.fixture
    def koch_cusps(self):
        return calculate_houses(2451545.0, 40.7128, -74.0060, system="K")

    def test_age_zero_at_ascendant(self, koch_cusps):
        ap = age_point(0.0, koch_cusps)
        assert ap.house == 1
        assert abs(ap.longitude - koch_cusps.asc) < 0.01
        assert ap.fraction_through_house == 0.0
        assert ap.cycle == 1

    def test_age_18_at_ic(self, koch_cusps):
        """Age 18: 3 houses elapsed -> cusp of house 4 (IC)."""
        ap = age_point(18.0, koch_cusps)
        assert ap.house == 4
        assert abs(ap.fraction_through_house) < 0.01

    def test_age_36_at_descendant(self, koch_cusps):
        """Age 36: 6 houses elapsed -> cusp of house 7 (DSC)."""
        ap = age_point(36.0, koch_cusps)
        assert ap.house == 7
        assert abs(ap.longitude - koch_cusps.dsc) < 0.5

    def test_age_54_at_mc(self, koch_cusps):
        """Age 54: 9 houses elapsed -> cusp of house 10 (MC)."""
        ap = age_point(54.0, koch_cusps)
        assert ap.house == 10
        assert abs(ap.longitude - koch_cusps.mc) < 0.5

    def test_age_72_returns_to_ascendant(self, koch_cusps):
        ap = age_point(72.0, koch_cusps)
        assert ap.house == 1
        assert abs(ap.longitude - koch_cusps.asc) < 0.01
        assert ap.cycle == 2  # second cycle

    def test_intensity_at_cusp_is_maximum(self, koch_cusps):
        ap = age_point(0.0, koch_cusps)
        assert abs(ap.intensity - 1.0) < 0.01

    def test_intensity_at_low_point_is_minimum(self, koch_cusps):
        """At PHI of house (3.708 years in), intensity should be ~0."""
        age_at_lp = PHI * YEARS_PER_HOUSE  # ~3.708 years
        ap = age_point(age_at_lp, koch_cusps)
        assert ap.intensity < 0.01

    def test_zone_cardinal_at_cusp(self, koch_cusps):
        ap = age_point(0.5, koch_cusps)  # just inside house 1
        assert ap.zone is HouseZone.CARDINAL

    def test_zone_fixed_at_midpoint(self, koch_cusps):
        age_at_bp = PHI_COMPLEMENT * YEARS_PER_HOUSE + 0.3  # just past BP
        ap = age_point(age_at_bp, koch_cusps)
        assert ap.zone is HouseZone.FIXED

    def test_zone_mutable_near_end(self, koch_cusps):
        age_near_end = PHI * YEARS_PER_HOUSE + 0.5  # past LP
        ap = age_point(age_near_end, koch_cusps)
        assert ap.zone is HouseZone.MUTABLE

    def test_negative_age_rejected(self, koch_cusps):
        with pytest.raises(ValueError, match="non-negative"):
            age_point(-1.0, koch_cusps)

    def test_beyond_72_wraps_to_cycle_2(self, koch_cusps):
        ap = age_point(78.0, koch_cusps)  # 72 + 6 = second house in cycle 2
        assert ap.cycle == 2
        assert ap.house == 2

    def test_age_point_is_frozen(self, koch_cusps):
        ap = age_point(30.0, koch_cusps)
        with pytest.raises(AttributeError):
            ap.longitude = 0.0

    def test_years_into_house_matches_fraction(self, koch_cusps):
        ap = age_point(15.5, koch_cusps)
        expected_fraction = ap.years_into_house / YEARS_PER_HOUSE
        assert abs(ap.fraction_through_house - expected_fraction) < 1e-10


# ===========================================================================
# DYNAMIC INTENSITY CURVE
# ===========================================================================

class TestDynamicIntensityCurve:
    def test_cusp_intensity_is_one(self):
        di = dynamic_intensity(1, 0.0)
        assert abs(di.intensity - 1.0) < 1e-10

    def test_next_cusp_intensity_is_one(self):
        di = dynamic_intensity(1, 1.0)
        assert abs(di.intensity - 1.0) < 1e-10

    def test_low_point_intensity_is_zero(self):
        di = dynamic_intensity(1, PHI)
        assert abs(di.intensity) < 1e-10

    def test_monotonic_descent_cusp_to_low_point(self):
        """Intensity must decrease monotonically from cusp (0) to Low Point (PHI)."""
        prev = 1.0
        for i in range(1, 100):
            f = PHI * i / 100.0
            di = dynamic_intensity(1, f)
            assert di.intensity <= prev + 1e-10
            prev = di.intensity

    def test_monotonic_ascent_low_point_to_next_cusp(self):
        """Intensity must increase monotonically from Low Point (PHI) to next cusp (1)."""
        prev = 0.0
        for i in range(1, 100):
            f = PHI + (1.0 - PHI) * i / 100.0
            di = dynamic_intensity(1, f)
            assert di.intensity >= prev - 1e-10
            prev = di.intensity

    def test_curve_is_smooth(self):
        """No large jumps between adjacent samples."""
        prev = dynamic_intensity(1, 0.0).intensity
        for i in range(1, 1001):
            f = i / 1000.0
            curr = dynamic_intensity(1, f).intensity
            assert abs(curr - prev) < 0.02  # < 2% change per 0.1% step
            prev = curr

    def test_asymmetry(self):
        """
        The curve should be asymmetric: intensity at 0.3 (before LP)
        should differ from intensity at 0.7 (after LP).
        """
        i_before = dynamic_intensity(1, 0.3).intensity
        i_after = dynamic_intensity(1, 0.7).intensity
        assert i_before != i_after

    def test_balance_point_intensity(self):
        """At the Balance Point (0.382), intensity should be moderate."""
        di = dynamic_intensity(1, PHI_COMPLEMENT)
        assert 0.0 < di.intensity < 1.0

    def test_zone_classification(self):
        assert dynamic_intensity(1, 0.1).zone is HouseZone.CARDINAL
        assert dynamic_intensity(1, 0.5).zone is HouseZone.FIXED
        assert dynamic_intensity(1, 0.9).zone is HouseZone.MUTABLE

    def test_invalid_house_rejected(self):
        with pytest.raises(ValueError, match="house must be 1--12"):
            dynamic_intensity(0, 0.5)

    def test_fraction_clamped_to_bounds(self):
        """Fractions outside [0, 1] should be clamped, not crash."""
        di_low = dynamic_intensity(1, -0.1)
        di_high = dynamic_intensity(1, 1.1)
        assert abs(di_low.intensity - 1.0) < 1e-10  # clamped to 0.0
        assert abs(di_high.intensity - 1.0) < 1e-10  # clamped to 1.0


# ===========================================================================
# INTENSITY AT LONGITUDE
# ===========================================================================

@pytest.mark.requires_ephemeris
class TestIntensityAtLongitude:
    @pytest.fixture
    def koch_cusps(self):
        return calculate_houses(2451545.0, 40.7128, -74.0060, system="K")

    def test_cusp_longitude_gives_high_intensity(self, koch_cusps):
        """A longitude exactly at a house cusp should have near-maximum intensity."""
        di = intensity_at(koch_cusps.cusps[0], koch_cusps)
        assert di.intensity > 0.95

    def test_returns_valid_house(self, koch_cusps):
        di = intensity_at(100.0, koch_cusps)
        assert 1 <= di.house <= 12

    def test_fraction_in_range(self, koch_cusps):
        di = intensity_at(200.0, koch_cusps)
        assert 0.0 <= di.fraction <= 1.0


# ===========================================================================
# CHART INTENSITY PROFILE
# ===========================================================================

@pytest.mark.requires_ephemeris
class TestChartIntensityProfile:
    @pytest.fixture
    def koch_cusps(self):
        return calculate_houses(2451545.0, 40.7128, -74.0060, system="K")

    def test_empty_points_yields_zero_mean(self, koch_cusps):
        profile = chart_intensity_profile({}, koch_cusps)
        assert profile.mean_intensity == 0.0
        assert len(profile.scores) == 0

    def test_scores_match_input_count(self, koch_cusps):
        points = {"Sun": 120.0, "Moon": 240.0, "Mars": 0.0}
        profile = chart_intensity_profile(points, koch_cusps)
        assert len(profile.scores) == 3

    def test_high_intensity_near_cusp(self, koch_cusps):
        """A planet right at a cusp should appear in high_intensity."""
        cusp_lon = koch_cusps.cusps[0]
        points = {"OnCusp": cusp_lon}
        profile = chart_intensity_profile(points, koch_cusps)
        assert len(profile.high_intensity) == 1
        assert profile.high_intensity[0].name == "OnCusp"

    def test_point_names_preserved(self, koch_cusps):
        points = {"Alpha": 50.0, "Beta": 150.0, "Gamma": 250.0}
        profile = chart_intensity_profile(points, koch_cusps)
        names = [s.name for s in profile.scores]
        assert names == ["Alpha", "Beta", "Gamma"]

    def test_near_cusp_and_near_low_point_flags(self, koch_cusps):
        profile = chart_intensity_profile({"X": 100.0}, koch_cusps)
        score = profile.scores[0]
        # near_cusp and near_low_point should be mutually exclusive
        # (can't be both >= 0.8 and <= 0.2)
        assert not (score.near_cusp and score.near_low_point)

    def test_mean_intensity_in_range(self, koch_cusps):
        points = {f"P{i}": i * 30.0 for i in range(12)}
        profile = chart_intensity_profile(points, koch_cusps)
        assert 0.0 <= profile.mean_intensity <= 1.0

    def test_profile_is_frozen(self, koch_cusps):
        profile = chart_intensity_profile({"X": 100.0}, koch_cusps)
        with pytest.raises(AttributeError):
            profile.mean_intensity = 0.0


# ===========================================================================
# AGE POINT CONTACTS
# ===========================================================================

@pytest.mark.requires_ephemeris
class TestAgePointContacts:
    @pytest.fixture
    def koch_cusps(self):
        return calculate_houses(2451545.0, 40.7128, -74.0060, system="K")

    def test_contact_with_planet_at_ascendant(self, koch_cusps):
        """A planet exactly at the ASC should produce a contact at age ~0."""
        contacts = age_point_contacts(
            koch_cusps,
            {"TestPlanet": koch_cusps.asc},
            orb=2.0,
        )
        assert len(contacts) > 0
        first_age = contacts[0][0]
        assert first_age < 1.0  # should be very near birth

    def test_contacts_sorted_by_age(self, koch_cusps):
        contacts = age_point_contacts(
            koch_cusps,
            {"Sun": 120.0, "Moon": 240.0},
            orb=3.0,
        )
        ages = [c[0] for c in contacts]
        assert ages == sorted(ages)

    def test_no_contacts_with_tight_orb(self, koch_cusps):
        """With a 0-degree orb, very few or no contacts."""
        contacts = age_point_contacts(
            koch_cusps,
            {"Sun": 120.0},
            orb=0.0,
        )
        # Zero orb means only exact hits, which are vanishingly unlikely
        # with discrete stepping
        assert len(contacts) <= 1


# ===========================================================================
# PUBLIC API CONTRACT
# ===========================================================================

class TestHuberPublicApi:
    def test_all_curated_names_resolve(self):
        import moira.huber as _mod
        for name in _mod.__all__:
            assert hasattr(_mod, name), f"moira.huber.{name} not found"

    def test_all_count(self):
        import moira.huber as _mod
        assert len(_mod.__all__) == 16
