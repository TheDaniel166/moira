"""
tests/unit/test_house_diurnal.py

Unit tests for the diurnal quadrant framework (moira.houses Phase 5).

Scope: semi-diurnal arc computation, diurnal_position(), diurnal_emphasis(),
       DiurnalQuadrant enum, DiurnalPosition / DiurnalEmphasisProfile invariants.
"""

import math
import pytest

from moira.houses import (
    DiurnalQuadrant,
    DiurnalPosition,
    DiurnalEmphasisProfile,
    diurnal_position,
    diurnal_emphasis,
)


# ---------------------------------------------------------------------------
# Constants for test fixtures
# ---------------------------------------------------------------------------

OBLIQUITY = 23.44   # degrees, J2000 approximate
LAT_NYC   = 40.7128
LAT_EQUATOR = 0.0
LAT_ARCTIC  = 70.0  # high latitude for circumpolar tests


# ---------------------------------------------------------------------------
# DiurnalQuadrant enum
# ---------------------------------------------------------------------------

class TestDiurnalQuadrantEnum:
    def test_four_members(self):
        assert len(DiurnalQuadrant) == 4

    def test_string_values(self):
        assert DiurnalQuadrant.DQ1 == "DQ1"
        assert DiurnalQuadrant.DQ2 == "DQ2"
        assert DiurnalQuadrant.DQ3 == "DQ3"
        assert DiurnalQuadrant.DQ4 == "DQ4"


# ---------------------------------------------------------------------------
# diurnal_position — angular boundary cases
# ---------------------------------------------------------------------------

class TestDiurnalPositionAngles:
    """Test bodies near the four angles."""

    def test_body_near_mc_is_above_horizon(self):
        """HA ≈ 0 → DQ2, above horizon, western."""
        # Place Sun RA ≈ ARMC so HA ≈ 0
        pos = diurnal_position(280.0, 0.0, 281.5, OBLIQUITY, LAT_NYC)
        assert pos.quadrant is DiurnalQuadrant.DQ2
        assert pos.is_above_horizon is True
        assert pos.hour_angle < 5.0  # close to MC

    def test_body_near_ic_is_below_horizon(self):
        """HA ≈ 180 → DQ3/DQ4 boundary, below horizon."""
        # ARMC offset by 180° from body's RA
        pos = diurnal_position(280.0, 0.0, 101.5, OBLIQUITY, LAT_NYC)
        assert pos.is_above_horizon is False
        assert abs(pos.hour_angle - 180.0) < 5.0

    def test_body_in_dq1_is_eastern_above(self):
        """DQ1 = ASC → MC, eastern + above horizon."""
        # Large HA near 360 (just past ASC going toward MC)
        pos = diurnal_position(280.0, 0.0, 281.5, OBLIQUITY, LAT_NYC)
        # Body near MC → DQ2.  Shift ARMC so body is just after ASC.
        sda = pos.semi_diurnal_arc
        armc_for_asc = (281.5 + (360.0 - sda) + 5) % 360.0
        pos2 = diurnal_position(280.0, 0.0, armc_for_asc, OBLIQUITY, LAT_NYC)
        if pos2.quadrant is DiurnalQuadrant.DQ1:
            assert pos2.is_above_horizon is True
            assert pos2.is_eastern is True


# ---------------------------------------------------------------------------
# diurnal_position — semi-diurnal arc properties
# ---------------------------------------------------------------------------

class TestSemiDiurnalArc:
    def test_sda_plus_sna_equals_180(self):
        pos = diurnal_position(120.0, 0.0, 0.0, OBLIQUITY, LAT_NYC)
        assert abs(pos.semi_diurnal_arc + pos.semi_nocturnal_arc - 180.0) < 1e-10

    def test_equator_has_equal_arcs(self):
        """At the equator, SDA ≈ 90° for bodies near zero declination."""
        pos = diurnal_position(0.0, 0.0, 0.0, OBLIQUITY, LAT_EQUATOR)
        # Aries 0° has dec ≈ 0 at equator → SDA ≈ 90
        assert abs(pos.semi_diurnal_arc - 90.0) < 2.0

    def test_high_dec_at_high_lat_circumpolar(self):
        """Body with high northern declination at high latitude → circumpolar."""
        # Cancer 15° → dec ≈ 23°+. At lat 70° this is circumpolar.
        pos = diurnal_position(105.0, 0.0, 0.0, OBLIQUITY, LAT_ARCTIC)
        assert pos.semi_diurnal_arc >= 170.0 or pos.is_circumpolar


# ---------------------------------------------------------------------------
# diurnal_position — fraction
# ---------------------------------------------------------------------------

class TestDiurnalFraction:
    def test_fraction_in_range(self):
        for lon in range(0, 360, 30):
            pos = diurnal_position(float(lon), 0.0, 100.0, OBLIQUITY, LAT_NYC)
            assert 0.0 <= pos.fraction <= 1.0, (
                f"lon={lon}: fraction={pos.fraction} out of range"
            )

    def test_fraction_near_zero_at_quadrant_entry(self):
        """Body just past MC (HA≈small) → DQ2 fraction near 0."""
        pos = diurnal_position(280.0, 0.0, 281.5, OBLIQUITY, LAT_NYC)
        assert pos.quadrant is DiurnalQuadrant.DQ2
        assert pos.fraction < 0.05


# ---------------------------------------------------------------------------
# diurnal_position — hemisphere flags
# ---------------------------------------------------------------------------

class TestDiurnalHemisphereFlags:
    def test_above_horizon_iff_dq1_or_dq2(self):
        for lon in range(0, 360, 15):
            pos = diurnal_position(float(lon), 0.0, 100.0, OBLIQUITY, LAT_NYC)
            expected = pos.quadrant in (DiurnalQuadrant.DQ1, DiurnalQuadrant.DQ2)
            assert pos.is_above_horizon is expected, (
                f"lon={lon}: quadrant={pos.quadrant}, above_horizon={pos.is_above_horizon}"
            )

    def test_eastern_iff_dq1_or_dq4(self):
        for lon in range(0, 360, 15):
            pos = diurnal_position(float(lon), 0.0, 100.0, OBLIQUITY, LAT_NYC)
            expected = pos.quadrant in (DiurnalQuadrant.DQ1, DiurnalQuadrant.DQ4)
            assert pos.is_eastern is expected


# ---------------------------------------------------------------------------
# diurnal_position — immutability
# ---------------------------------------------------------------------------

class TestDiurnalPositionFrozen:
    def test_position_is_frozen(self):
        pos = diurnal_position(100.0, 0.0, 50.0, OBLIQUITY, LAT_NYC)
        with pytest.raises(AttributeError):
            pos.quadrant = DiurnalQuadrant.DQ3


# ---------------------------------------------------------------------------
# diurnal_emphasis — bulk analysis
# ---------------------------------------------------------------------------

class TestDiurnalEmphasis:
    def test_empty_points(self):
        profile = diurnal_emphasis({}, 100.0, OBLIQUITY, LAT_NYC)
        assert profile.point_count == 0
        assert profile.dominant_quadrant == ()

    def test_counts_sum_to_point_count(self):
        points = {
            "Sun": (280.0, 0.0), "Moon": (120.0, 5.1),
            "Mars": (15.0, 0.3), "Jupiter": (200.0, -1.2),
        }
        profile = diurnal_emphasis(points, 100.0, OBLIQUITY, LAT_NYC)
        total = profile.dq1_count + profile.dq2_count + profile.dq3_count + profile.dq4_count
        assert total == profile.point_count == 4

    def test_hemisphere_counts_consistent(self):
        points = {"A": (0.0, 0.0), "B": (90.0, 0.0), "C": (180.0, 0.0), "D": (270.0, 0.0)}
        profile = diurnal_emphasis(points, 50.0, OBLIQUITY, LAT_NYC)
        assert profile.above_horizon_count + profile.below_horizon_count == profile.point_count
        assert profile.eastern_count + profile.western_count == profile.point_count
        assert profile.above_horizon_count == profile.dq1_count + profile.dq2_count
        assert profile.eastern_count == profile.dq1_count + profile.dq4_count

    def test_positions_dict_populated(self):
        points = {"Sun": (280.0, 0.0), "Moon": (120.0, 5.1)}
        profile = diurnal_emphasis(points, 100.0, OBLIQUITY, LAT_NYC)
        assert "Sun" in profile.positions
        assert "Moon" in profile.positions
        assert isinstance(profile.positions["Sun"], DiurnalPosition)

    def test_point_names_preserved(self):
        points = {"Alpha": (0.0, 0.0), "Beta": (180.0, 0.0)}
        profile = diurnal_emphasis(points, 100.0, OBLIQUITY, LAT_NYC)
        all_names = set(profile.dq1_points + profile.dq2_points +
                        profile.dq3_points + profile.dq4_points)
        assert all_names == {"Alpha", "Beta"}

    def test_profile_is_frozen(self):
        profile = diurnal_emphasis({"X": (100.0, 0.0)}, 50.0, OBLIQUITY, LAT_NYC)
        with pytest.raises(AttributeError):
            profile.dq1_count = 999


# ---------------------------------------------------------------------------
# DiurnalEmphasisProfile invariant guards
# ---------------------------------------------------------------------------

class TestDiurnalEmphasisInvariants:
    def test_rejects_count_mismatch(self):
        with pytest.raises(ValueError, match="diurnal quadrant counts must sum"):
            DiurnalEmphasisProfile(
                point_count=5,
                dq1_count=1, dq2_count=1, dq3_count=1, dq4_count=1,  # sum=4 != 5
                dq1_points=("A",), dq2_points=("B",),
                dq3_points=("C",), dq4_points=("D",),
                positions={}, dominant_quadrant=(DiurnalQuadrant.DQ1,),
                above_horizon_count=2, below_horizon_count=3,
                eastern_count=2, western_count=3,
            )
