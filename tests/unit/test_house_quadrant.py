"""
tests/unit/test_house_quadrant.py

Unit tests for Rudhyar quadrant emphasis analysis (moira.houses Phase 4).

Scope: quadrant_of(), quadrant_emphasis(), Quadrant enum,
       QuadrantEmphasisProfile invariants.
"""

import pytest

from moira.houses import (
    Quadrant,
    QuadrantEmphasisProfile,
    quadrant_of,
    quadrant_emphasis,
    calculate_houses,
)


# ---------------------------------------------------------------------------
# quadrant_of — house-to-quadrant mapping
# ---------------------------------------------------------------------------

class TestQuadrantOf:
    @pytest.mark.parametrize("house,expected", [
        (1, Quadrant.Q1), (2, Quadrant.Q1), (3, Quadrant.Q1),
        (4, Quadrant.Q2), (5, Quadrant.Q2), (6, Quadrant.Q2),
        (7, Quadrant.Q3), (8, Quadrant.Q3), (9, Quadrant.Q3),
        (10, Quadrant.Q4), (11, Quadrant.Q4), (12, Quadrant.Q4),
    ])
    def test_all_twelve_houses_map_correctly(self, house, expected):
        assert quadrant_of(house) is expected

    def test_rejects_house_zero(self):
        with pytest.raises(ValueError, match="house must be 1–12"):
            quadrant_of(0)

    def test_rejects_house_thirteen(self):
        with pytest.raises(ValueError, match="house must be 1–12"):
            quadrant_of(13)

    def test_rejects_negative_house(self):
        with pytest.raises(ValueError, match="house must be 1–12"):
            quadrant_of(-1)


# ---------------------------------------------------------------------------
# Quadrant enum
# ---------------------------------------------------------------------------

class TestQuadrantEnum:
    def test_four_members(self):
        assert len(Quadrant) == 4

    def test_string_values(self):
        assert Quadrant.Q1 == "Q1"
        assert Quadrant.Q2 == "Q2"
        assert Quadrant.Q3 == "Q3"
        assert Quadrant.Q4 == "Q4"

    def test_iteration_order(self):
        assert list(Quadrant) == [Quadrant.Q1, Quadrant.Q2, Quadrant.Q3, Quadrant.Q4]


# ---------------------------------------------------------------------------
# quadrant_emphasis — integration with house placement
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
class TestQuadrantEmphasis:
    @pytest.fixture
    def cusps(self):
        """Placidus cusps for a fixed moment and location."""
        return calculate_houses(2451545.0, 40.7128, -74.0060)

    def test_empty_points_yields_zero_profile(self, cusps):
        profile = quadrant_emphasis({}, cusps)
        assert profile.point_count == 0
        assert profile.q1_count == 0
        assert profile.q2_count == 0
        assert profile.q3_count == 0
        assert profile.q4_count == 0
        assert profile.dominant_quadrant == ()
        assert profile.eastern_count == 0
        assert profile.western_count == 0
        assert profile.northern_count == 0
        assert profile.southern_count == 0

    def test_counts_sum_to_point_count(self, cusps):
        points = {
            "Sun": 280.0, "Moon": 120.0, "Mercury": 295.0,
            "Venus": 30.0, "Mars": 180.0, "Jupiter": 45.0,
            "Saturn": 210.0,
        }
        profile = quadrant_emphasis(points, cusps)
        assert profile.point_count == 7
        total = profile.q1_count + profile.q2_count + profile.q3_count + profile.q4_count
        assert total == 7

    def test_hemisphere_counts_consistent(self, cusps):
        points = {"A": 0.0, "B": 90.0, "C": 180.0, "D": 270.0}
        profile = quadrant_emphasis(points, cusps)
        assert profile.eastern_count + profile.western_count == profile.point_count
        assert profile.northern_count + profile.southern_count == profile.point_count
        assert profile.eastern_count == profile.q1_count + profile.q4_count
        assert profile.western_count == profile.q2_count + profile.q3_count
        assert profile.northern_count == profile.q1_count + profile.q2_count
        assert profile.southern_count == profile.q3_count + profile.q4_count

    def test_dominant_quadrant_identifies_maximum(self, cusps):
        # Cluster 5 points in house 1 region (Q1), 1 elsewhere
        asc = cusps.asc
        points = {
            "A": (asc + 1) % 360, "B": (asc + 5) % 360, "C": (asc + 10) % 360,
            "D": (asc + 15) % 360, "E": (asc + 20) % 360,
            "F": (asc + 180) % 360,
        }
        profile = quadrant_emphasis(points, cusps)
        assert Quadrant.Q1 in profile.dominant_quadrant

    def test_point_names_preserved_in_order(self, cusps):
        asc = cusps.asc
        points = {"Alpha": (asc + 1) % 360, "Beta": (asc + 5) % 360}
        profile = quadrant_emphasis(points, cusps)
        # Both should land in Q1 (just past ASC)
        assert "Alpha" in profile.q1_points
        assert "Beta" in profile.q1_points

    def test_profile_is_frozen(self, cusps):
        profile = quadrant_emphasis({"X": 100.0}, cusps)
        with pytest.raises(AttributeError):
            profile.q1_count = 999


# ---------------------------------------------------------------------------
# QuadrantEmphasisProfile invariant guards
# ---------------------------------------------------------------------------

class TestQuadrantEmphasisProfileInvariants:
    def test_rejects_quadrant_count_mismatch(self):
        """Quadrant counts must sum to point_count."""
        with pytest.raises(ValueError, match="quadrant counts must sum"):
            QuadrantEmphasisProfile(
                house_cusps=None,  # type: ignore[arg-type]
                point_count=5,
                q1_count=1, q2_count=1, q3_count=1, q4_count=1,  # sum=4 != 5
                q1_points=("A",), q2_points=("B",), q3_points=("C",), q4_points=("D",),
                dominant_quadrant=(Quadrant.Q1,),
                eastern_count=2, western_count=3,
                northern_count=2, southern_count=3,
            )

    def test_rejects_hemisphere_mismatch(self):
        """Hemisphere counts must sum to point_count."""
        with pytest.raises(ValueError, match="hemisphere counts must sum"):
            QuadrantEmphasisProfile(
                house_cusps=None,  # type: ignore[arg-type]
                point_count=4,
                q1_count=1, q2_count=1, q3_count=1, q4_count=1,
                q1_points=("A",), q2_points=("B",), q3_points=("C",), q4_points=("D",),
                dominant_quadrant=(Quadrant.Q1,),
                eastern_count=1, western_count=1,  # sum=2 != 4
                northern_count=2, southern_count=2,
            )
