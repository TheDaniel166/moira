"""
tests/unit/test_chart_shape.py

Validates the Jones whole-chart shape classification engine.

Scope
-----
- Public API import resolution (moira package and moira.chart_shape module).
- All seven Jones temperament types: Bundle, Bowl, Bucket, Locomotive,
  Seesaw, Splay, Splash.
- ChartShape result-vessel field contracts.
- Boundary / edge-case detection logic.
- Internal helpers remain accessible but absent from __all__.

No ephemeris kernel is required; all tests work with synthetic planet dicts.
"""

import pytest
import moira
import moira.chart_shape as _cs_module
from moira.chart_shape import (
    ChartShapeType,
    ChartShape,
    classify_chart_shape,
)


# ---------------------------------------------------------------------------
# Canonical test fixtures
# ---------------------------------------------------------------------------

# Bundle: all 10 planets within 85 degrees
_BUNDLE = {
    "Sun": 0, "Moon": 10, "Mercury": 20, "Venus": 30, "Mars": 40,
    "Jupiter": 50, "Saturn": 60, "Uranus": 70, "Neptune": 80, "Pluto": 85,
}

# Bowl: all 10 within 170 degrees (no isolated handle)
_BOWL = {
    "Sun": 0, "Moon": 20, "Mercury": 40, "Venus": 60, "Mars": 80,
    "Jupiter": 100, "Saturn": 120, "Uranus": 140, "Neptune": 160, "Pluto": 170,
}

# Bucket: 9 planets within 120 degrees + 1 handle (Pluto in the opposite hemisphere)
_BUCKET = {
    "Sun": 0, "Moon": 15, "Mercury": 30, "Venus": 45, "Mars": 60,
    "Jupiter": 75, "Saturn": 90, "Uranus": 105, "Neptune": 120, "Pluto": 240,
}

# Two-eight Seesaw with a close Neptune/Pluto group.  Earlier Moira releases
# treated the pair as a Bucket handle, but Jones's Bucket is explicitly one-nine.
_BUCKET_PAIR = {
    "Sun": 0, "Moon": 15, "Mercury": 30, "Venus": 45, "Mars": 60,
    "Jupiter": 75, "Saturn": 90, "Uranus": 105,
    "Neptune": 250, "Pluto": 256,
}

# Locomotive: 10 planets in 230 degrees (one defining 130-degree trine gap)
_LOCOMOTIVE = {
    "Sun": 0, "Moon": 25, "Mercury": 50, "Venus": 75, "Mars": 100,
    "Jupiter": 125, "Saturn": 150, "Uranus": 175, "Neptune": 200, "Pluto": 230,
}

# Seesaw: two opposing clusters each 5 planets, two 140-degree gaps
_SEESAW = {
    "Sun": 10, "Moon": 20, "Mercury": 30, "Venus": 40, "Mars": 50,
    "Jupiter": 190, "Saturn": 200, "Uranus": 210, "Neptune": 220, "Pluto": 230,
}

# Splay: three distinct groups of 3-4 planets in a tripod arrangement
_SPLAY = {
    "Sun": 0, "Moon": 10, "Mercury": 20, "Pluto": 5,
    "Venus": 120, "Mars": 130, "Jupiter": 140,
    "Saturn": 240, "Uranus": 250, "Neptune": 260,
}

# Splash: 10 planets evenly spaced every 36 degrees (no gap > 60)
_SPLASH = {
    "Sun": 0, "Moon": 36, "Mercury": 72, "Venus": 108, "Mars": 144,
    "Jupiter": 180, "Saturn": 216, "Uranus": 252, "Neptune": 288, "Pluto": 324,
}


# ---------------------------------------------------------------------------
# Public API import tests
# ---------------------------------------------------------------------------

class TestPublicAPIResolution:
    _PUBLIC_NAMES = ["ChartShapeType", "ChartShape", "classify_chart_shape"]

    def test_all_names_on_moira_package(self):
        for name in self._PUBLIC_NAMES:
            assert name not in moira.__all__, f"moira.__all__ should stay thin; found {name!r}"

    def test_all_names_on_chart_shape_module(self):
        for name in self._PUBLIC_NAMES:
            assert hasattr(_cs_module, name), f"moira.chart_shape.{name} not found"

    def test_module_all_exists_and_matches(self):
        assert hasattr(_cs_module, "__all__")
        assert set(_cs_module.__all__) == set(self._PUBLIC_NAMES)

    def test_internals_absent_from_all(self):
        internals = [
            "_BUNDLE_MAX_ARC", "_BOWL_MAX_ARC", "_JONES_BODIES",
            "_SUN_ASPECT_ORB", "_MOON_ASPECT_ORB", "_PLANET_ASPECT_ORB",
            "_sorted_longitudes", "_compute_gaps",
            "_group_separating_gaps", "_split_at_gaps", "_detect_bundle", "_detect_bowl",
            "_detect_bucket", "_detect_locomotive", "_detect_seesaw",
            "_detect_splay", "_detect_splash",
        ]
        for name in internals:
            assert name not in _cs_module.__all__, f"{name!r} leaked into __all__"


class TestJonesGapDoctrine:
    @pytest.mark.parametrize(
        ("body1", "body2", "expected"),
        [
            ("Sun", "Saturn", 17.0),
            ("Moon", "Saturn", 12.5),
            ("Mercury", "Saturn", 10.0),
        ],
    )
    def test_body_dependent_major_aspect_orbs(
        self,
        body1: str,
        body2: str,
        expected: float,
    ) -> None:
        assert _cs_module._jones_aspect_orb(body1, body2) == expected

    @pytest.mark.parametrize(
        ("gap_degrees", "expected"),
        [
            (49.999, False),
            (50.0, True),
            (70.0, True),
            (70.001, True),
        ],
    )
    def test_non_luminary_group_separation_boundaries(
        self,
        gap_degrees: float,
        expected: bool,
    ) -> None:
        sorted_lons = [(0.0, "Mercury"), (gap_degrees, "Saturn")]
        gap = (gap_degrees, 0, 1)
        assert _cs_module._is_group_separating_gap(gap, sorted_lons) is expected


# ---------------------------------------------------------------------------
# Detection: all seven shapes
# ---------------------------------------------------------------------------

class TestBundleDetection:
    def test_bundle_detected(self):
        result = classify_chart_shape(_BUNDLE)
        assert result.shape == ChartShapeType.BUNDLE

    def test_bundle_occupied_arc(self):
        result = classify_chart_shape(_BUNDLE)
        assert result.occupied_arc == pytest.approx(85.0, abs=0.5)

    def test_bundle_largest_gap(self):
        result = classify_chart_shape(_BUNDLE)
        assert result.largest_gap == pytest.approx(275.0, abs=0.5)

    def test_bundle_no_leading_or_handle(self):
        result = classify_chart_shape(_BUNDLE)
        assert result.leading_planet is None
        assert result.handle_planet is None

    def test_bundle_one_cluster_all_bodies(self):
        result = classify_chart_shape(_BUNDLE)
        assert len(result.clusters) == 1
        assert result.clusters[0] == frozenset(_BUNDLE.keys())


class TestBowlDetection:
    def test_bowl_detected(self):
        result = classify_chart_shape(_BOWL)
        assert result.shape == ChartShapeType.BOWL

    def test_bowl_occupied_arc(self):
        result = classify_chart_shape(_BOWL)
        assert result.occupied_arc == pytest.approx(170.0, abs=0.5)

    def test_bowl_largest_gap(self):
        result = classify_chart_shape(_BOWL)
        assert result.largest_gap == pytest.approx(190.0, abs=0.5)

    def test_bowl_leading_planet_is_rim_planet(self):
        result = classify_chart_shape(_BOWL)
        assert result.leading_planet in _BOWL

    def test_bowl_no_handle(self):
        result = classify_chart_shape(_BOWL)
        assert result.handle_planet is None

    def test_bowl_one_cluster_all_bodies(self):
        result = classify_chart_shape(_BOWL)
        assert len(result.clusters) == 1
        assert result.clusters[0] == frozenset(_BOWL.keys())

    def test_bowl_exact_180_boundary(self):
        pos = {
            body: index * 20.0
            for index, body in enumerate(
                ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter",
                 "Saturn", "Uranus", "Neptune", "Pluto")
            )
        }
        result = classify_chart_shape(pos)
        assert result.shape == ChartShapeType.BOWL


class TestBucketDetection:
    def test_bucket_detected(self):
        result = classify_chart_shape(_BUCKET)
        assert result.shape == ChartShapeType.BUCKET

    def test_bucket_handle_is_pluto(self):
        result = classify_chart_shape(_BUCKET)
        assert result.handle_planet == "Pluto"
        assert result.leading_planet == "Pluto"

    def test_bucket_bowl_arc(self):
        result = classify_chart_shape(_BUCKET)
        assert result.occupied_arc == pytest.approx(120.0, abs=0.5)

    def test_bucket_two_clusters(self):
        result = classify_chart_shape(_BUCKET)
        assert len(result.clusters) == 2

    def test_bucket_handle_in_second_cluster(self):
        result = classify_chart_shape(_BUCKET)
        assert "Pluto" not in result.clusters[0]
        assert "Pluto" in result.clusters[1]

    def test_bucket_handle_bodies_singleton(self):
        # RULE-10: handle_bodies is the authoritative handle identity and is a
        # non-empty subset of clusters[1], disjoint from clusters[0].
        result = classify_chart_shape(_BUCKET)
        assert result.handle_bodies == frozenset({"Pluto"})
        assert result.handle_bodies <= result.clusters[1]
        assert not (result.handle_bodies & result.clusters[0])

    def test_conjunction_pair_is_not_a_jones_bucket(self):
        result = classify_chart_shape(_BUCKET_PAIR)
        assert result.shape is ChartShapeType.SEESAW
        assert result.handle_planet is None
        assert result.handle_bodies == frozenset()

    def test_bucket_handle_at_60_from_rim_is_bucket(self):
        pos = {
            "Sun": 0, "Moon": 20, "Mercury": 40, "Venus": 60, "Mars": 80,
            "Jupiter": 100, "Saturn": 120, "Uranus": 140, "Neptune": 170,
            "Pluto": 230,
        }
        result = classify_chart_shape(pos)
        assert result.shape is ChartShapeType.BUCKET
        assert result.handle_planet == "Pluto"

    def test_bowl_interior_planet_does_not_trigger_bucket(self):
        pos = {
            "Sun": 0, "Moon": 20, "Mercury": 40, "Venus": 60, "Mars": 80,
            "Jupiter": 100, "Saturn": 120, "Uranus": 140, "Neptune": 160,
            "Pluto": 170,
        }
        result = classify_chart_shape(pos)
        assert result.shape == ChartShapeType.BOWL


class TestLocomotiveDetection:
    def test_locomotive_detected(self):
        result = classify_chart_shape(_LOCOMOTIVE)
        assert result.shape == ChartShapeType.LOCOMOTIVE

    def test_locomotive_occupied_arc(self):
        result = classify_chart_shape(_LOCOMOTIVE)
        assert result.occupied_arc == pytest.approx(230.0, abs=0.5)

    def test_locomotive_largest_gap(self):
        result = classify_chart_shape(_LOCOMOTIVE)
        assert result.largest_gap == pytest.approx(130.0, abs=0.5)

    def test_locomotive_leading_planet_is_set(self):
        result = classify_chart_shape(_LOCOMOTIVE)
        assert result.leading_planet in _LOCOMOTIVE

    def test_locomotive_no_handle(self):
        result = classify_chart_shape(_LOCOMOTIVE)
        assert result.handle_planet is None

    def test_locomotive_does_not_fire_on_seesaw(self):
        result = classify_chart_shape(_SEESAW)
        assert result.shape != ChartShapeType.LOCOMOTIVE

    def test_functioning_trine_orb_can_delimit_locomotive(self):
        # The 119-degree empty region is a functioning trine under Jones's
        # admitted aspect orb and must not fall through to Splash.
        positions = {
            "Sun": 0, "Moon": 27, "Mercury": 54, "Venus": 81, "Mars": 108,
            "Jupiter": 135, "Saturn": 162, "Uranus": 189,
            "Neptune": 216, "Pluto": 241,
        }
        result = classify_chart_shape(positions)
        assert result.shape is ChartShapeType.LOCOMOTIVE
        assert result.largest_gap == pytest.approx(119.0)

    def test_gap_outside_trine_orb_is_not_locomotive(self):
        positions = {
            "Sun": 0, "Moon": 25, "Mercury": 50, "Venus": 75, "Mars": 100,
            "Jupiter": 125, "Saturn": 150, "Uranus": 175,
            "Neptune": 200, "Pluto": 220,
        }
        result = classify_chart_shape(positions)
        assert result.largest_gap == pytest.approx(140.0)
        assert result.shape is not ChartShapeType.LOCOMOTIVE


class TestSeesawDetection:
    def test_seesaw_detected(self):
        result = classify_chart_shape(_SEESAW)
        assert result.shape == ChartShapeType.SEESAW

    def test_seesaw_two_clusters(self):
        result = classify_chart_shape(_SEESAW)
        assert len(result.clusters) == 2

    def test_seesaw_clusters_each_have_multiple_planets(self):
        result = classify_chart_shape(_SEESAW)
        for cluster in result.clusters:
            assert len(cluster) >= 2

    def test_seesaw_no_leading_or_handle(self):
        result = classify_chart_shape(_SEESAW)
        assert result.leading_planet is None
        assert result.handle_planet is None

    def test_seesaw_all_bodies_covered(self):
        result = classify_chart_shape(_SEESAW)
        all_in_clusters = set()
        for c in result.clusters:
            all_in_clusters |= c
        assert all_in_clusters == frozenset(_SEESAW.keys())

    def test_seesaw_cluster_crossing_zero_is_seesaw(self):
        # RULE-20: two clean five-body groups, one crossing the 0/360 seam.
        positions = {
            "Sun": 340.0, "Moon": 350.0, "Mercury": 0.0,
            "Venus": 10.0, "Mars": 20.0,
            "Jupiter": 150.0, "Saturn": 160.0, "Uranus": 170.0,
            "Neptune": 180.0, "Pluto": 190.0,
        }
        result = classify_chart_shape(positions)
        assert result.shape is ChartShapeType.SEESAW
        assert len(result.clusters) == 2
        covered = set()
        for c in result.clusters:
            covered |= c
        assert covered == frozenset(positions.keys())

    def test_seesaw_allows_30_degree_internal_gap(self):
        # Two 90-degree empty spaces define the two groups.  The 30-degree
        # spacing inside the first group is not a third Jones separation.
        positions = {
            "Sun": 0.0, "Moon": 10.0, "Mercury": 40.0, "Venus": 68.0,
            "Mars": 158.0, "Jupiter": 168.0, "Saturn": 197.0,
            "Uranus": 226.0, "Neptune": 255.0, "Pluto": 270.0,
        }
        result = classify_chart_shape(positions)
        assert result.shape is ChartShapeType.SEESAW
        assert sorted(len(cluster) for cluster in result.clusters) == [4, 6]


class TestSplayDetection:
    def test_splay_detected(self):
        result = classify_chart_shape(_SPLAY)
        assert result.shape == ChartShapeType.SPLAY

    def test_splay_has_exactly_three_groups(self):
        result = classify_chart_shape(_SPLAY)
        assert len(result.clusters) == 3

    def test_splay_allows_singleton_reins_group(self):
        positions = {
            "Sun": 0,
            "Moon": 80, "Mercury": 100, "Venus": 120,
            "Mars": 200, "Jupiter": 215, "Saturn": 230,
            "Uranus": 245, "Neptune": 260, "Pluto": 280,
        }
        result = classify_chart_shape(positions)
        assert result.shape is ChartShapeType.SPLAY
        assert sorted(len(cluster) for cluster in result.clusters) == [1, 3, 6]

    def test_splay_no_leading_or_handle(self):
        result = classify_chart_shape(_SPLAY)
        assert result.leading_planet is None
        assert result.handle_planet is None

    def test_splay_all_bodies_covered(self):
        result = classify_chart_shape(_SPLAY)
        all_in_clusters = set()
        for c in result.clusters:
            all_in_clusters |= c
        assert all_in_clusters == frozenset(_SPLAY.keys())


class TestSplashDetection:
    def test_splash_detected(self):
        result = classify_chart_shape(_SPLASH)
        assert result.shape == ChartShapeType.SPLASH

    def test_splash_no_leading_or_handle(self):
        result = classify_chart_shape(_SPLASH)
        assert result.leading_planet is None
        assert result.handle_planet is None

    def test_splash_all_bodies_in_one_cluster(self):
        result = classify_chart_shape(_SPLASH)
        assert len(result.clusters) == 1
        assert result.clusters[0] == frozenset(_SPLASH.keys())

    def test_splash_largest_gap_does_not_exceed_threshold(self):
        result = classify_chart_shape(_SPLASH)
        assert result.largest_gap <= 60.0


# ---------------------------------------------------------------------------
# ChartShape vessel contract
# ---------------------------------------------------------------------------

class TestChartShapeVessel:
    def test_frozen(self):
        result = classify_chart_shape(_BOWL)
        with pytest.raises((AttributeError, TypeError)):
            result.shape = ChartShapeType.BUNDLE

    def test_arc_plus_gap_equals_360(self):
        for pos in (_BUNDLE, _BOWL, _BUCKET, _LOCOMOTIVE, _SEESAW, _SPLAY, _SPLASH):
            result = classify_chart_shape(pos)
            assert result.occupied_arc + result.largest_gap == pytest.approx(360.0, abs=1e-9)

    def test_clusters_is_tuple_of_frozensets(self):
        for pos in (_BUNDLE, _BOWL, _BUCKET, _LOCOMOTIVE, _SEESAW, _SPLAY, _SPLASH):
            result = classify_chart_shape(pos)
            assert isinstance(result.clusters, tuple)
            for c in result.clusters:
                assert isinstance(c, frozenset)

    def test_repr_contains_shape_name(self):
        for shape_type, pos in [
            (ChartShapeType.BUNDLE, _BUNDLE),
            (ChartShapeType.BOWL, _BOWL),
            (ChartShapeType.BUCKET, _BUCKET),
            (ChartShapeType.LOCOMOTIVE, _LOCOMOTIVE),
            (ChartShapeType.SEESAW, _SEESAW),
            (ChartShapeType.SPLAY, _SPLAY),
            (ChartShapeType.SPLASH, _SPLASH),
        ]:
            result = classify_chart_shape(pos)
            assert shape_type.value in repr(result)


# ---------------------------------------------------------------------------
# Edge cases and guard conditions
# ---------------------------------------------------------------------------

class TestPlanetSetDoctrine:
    def test_empty_positions_raises(self):
        with pytest.raises(ValueError, match="exactly the ten Jones bodies"):
            classify_chart_shape({})

    def test_single_planet_raises(self):
        with pytest.raises(ValueError, match="missing="):
            classify_chart_shape({"Sun": 45.0})

    def test_node_is_rejected(self):
        positions = dict(_SPLASH)
        positions["True Node"] = 12.0
        with pytest.raises(ValueError, match=r"extra=\['True Node'\]"):
            classify_chart_shape(positions)

    def test_omitted_planet_is_rejected(self):
        positions = dict(_SPLASH)
        del positions["Pluto"]
        with pytest.raises(ValueError, match=r"missing=\['Pluto'\]"):
            classify_chart_shape(positions)


class TestEdgeCases:

    def test_longitudes_outside_0_360_are_normalised(self):
        pos_a = {"Sun": 0, "Moon": 10, "Mercury": 20, "Venus": 30, "Mars": 40,
                 "Jupiter": 50, "Saturn": 60, "Uranus": 70, "Neptune": 80, "Pluto": 85}
        pos_b = {"Sun": 360, "Moon": 370, "Mercury": 380, "Venus": 390, "Mars": 400,
                 "Jupiter": 410, "Saturn": 420, "Uranus": 430, "Neptune": 440, "Pluto": 445}
        assert classify_chart_shape(pos_a).shape == classify_chart_shape(pos_b).shape

    def test_bundle_at_exact_120_boundary(self):
        pos = {"Sun": 0, "Moon": 12, "Mercury": 24, "Venus": 36, "Mars": 48,
               "Jupiter": 60, "Saturn": 72, "Uranus": 84, "Neptune": 96, "Pluto": 120}
        result = classify_chart_shape(pos)
        assert result.shape == ChartShapeType.BUNDLE

    def test_just_over_bundle_is_not_bundle(self):
        pos = {"Sun": 0, "Moon": 12, "Mercury": 24, "Venus": 36, "Mars": 48,
               "Jupiter": 60, "Saturn": 72, "Uranus": 84, "Neptune": 96, "Pluto": 121}
        result = classify_chart_shape(pos)
        assert result.shape != ChartShapeType.BUNDLE


# ---------------------------------------------------------------------------
# Leading planet semantics
# ---------------------------------------------------------------------------

class TestLeadingPlanetSemantics:
    def test_bowl_leading_planet_is_last_before_gap(self):
        # Bowl: planets 0..170, gap runs 170->0 (190 deg clockwise).
        # Leading planet = last before the gap = Pluto at 170.
        result = classify_chart_shape(_BOWL)
        assert result.leading_planet == "Pluto"

    def test_locomotive_leading_planet_is_last_before_gap(self):
        # Locomotive: planets 0..220, gap runs 220->0 (140 deg clockwise).
        # Leading planet = last before the gap = Pluto at 220.
        result = classify_chart_shape(_LOCOMOTIVE)
        assert result.leading_planet == "Pluto"

    def test_bowl_leading_planet_in_clusters(self):
        result = classify_chart_shape(_BOWL)
        assert result.leading_planet in result.clusters[0]

    def test_locomotive_leading_planet_in_clusters(self):
        result = classify_chart_shape(_LOCOMOTIVE)
        assert result.leading_planet in result.clusters[0]


# ---------------------------------------------------------------------------
# __post_init__ structural invariant enforcement
# ---------------------------------------------------------------------------

class TestChartShapeInvariants:
    def test_arc_gap_sum_violation_raises(self):
        with pytest.raises(ValueError, match="occupied_arc"):
            ChartShape(
                shape=ChartShapeType.SPLASH,
                occupied_arc=200.0,
                largest_gap=200.0,   # 200 + 200 != 360
                leading_planet=None,
                handle_planet=None,
                clusters=(frozenset({"Sun"}),),
            )

    def test_empty_clusters_raises(self):
        with pytest.raises(ValueError, match="clusters"):
            ChartShape(
                shape=ChartShapeType.SPLASH,
                occupied_arc=300.0,
                largest_gap=60.0,
                leading_planet=None,
                handle_planet=None,
                clusters=(),
            )

    def test_bowl_without_leading_planet_raises(self):
        with pytest.raises(ValueError, match="leading_planet"):
            ChartShape(
                shape=ChartShapeType.BOWL,
                occupied_arc=180.0,
                largest_gap=180.0,
                leading_planet=None,
                handle_planet=None,
                clusters=(frozenset({"Sun", "Moon"}),),
            )

    def test_bowl_leading_planet_not_in_cluster_raises(self):
        with pytest.raises(ValueError, match="leading_planet"):
            ChartShape(
                shape=ChartShapeType.BOWL,
                occupied_arc=180.0,
                largest_gap=180.0,
                leading_planet="Saturn",
                handle_planet=None,
                clusters=(frozenset({"Sun", "Moon"}),),
            )

    def test_bucket_without_handle_raises(self):
        with pytest.raises(ValueError, match="handle_planet"):
            ChartShape(
                shape=ChartShapeType.BUCKET,
                occupied_arc=120.0,
                largest_gap=240.0,
                leading_planet=None,
                handle_planet=None,
                clusters=(frozenset({"Sun", "Moon"}), frozenset({"Pluto"})),
            )

    def test_bucket_without_handle_bodies_raises(self):
        with pytest.raises(ValueError, match="handle_bodies"):
            ChartShape(
                shape=ChartShapeType.BUCKET,
                occupied_arc=120.0,
                largest_gap=240.0,
                leading_planet="Pluto",
                handle_planet="Pluto",
                clusters=(frozenset({"Sun", "Moon"}), frozenset({"Pluto"})),
                handle_bodies=frozenset(),
            )

    def test_bucket_with_two_handle_bodies_raises(self):
        with pytest.raises(ValueError, match="exactly one handle body"):
            ChartShape(
                shape=ChartShapeType.BUCKET,
                occupied_arc=120.0,
                largest_gap=240.0,
                leading_planet="Neptune",
                handle_planet="Neptune",
                clusters=(
                    frozenset({"Sun", "Moon"}),
                    frozenset({"Neptune", "Pluto"}),
                ),
                handle_bodies=frozenset({"Neptune", "Pluto"}),
            )

    def test_bucket_handle_bodies_not_in_second_cluster_raises(self):
        with pytest.raises(ValueError, match="handle_bodies"):
            ChartShape(
                shape=ChartShapeType.BUCKET,
                occupied_arc=120.0,
                largest_gap=240.0,
                leading_planet="Pluto",
                handle_planet="Pluto",
                clusters=(frozenset({"Sun", "Moon"}), frozenset({"Mars"})),
                handle_bodies=frozenset({"Pluto"}),
            )

    def test_bucket_handle_bodies_in_first_cluster_raises(self):
        with pytest.raises(ValueError, match="handle_bodies"):
            ChartShape(
                shape=ChartShapeType.BUCKET,
                occupied_arc=120.0,
                largest_gap=240.0,
                leading_planet="Sun",
                handle_planet="Sun",
                clusters=(frozenset({"Sun", "Moon"}), frozenset({"Sun"})),
                handle_bodies=frozenset({"Sun"}),
            )

    def test_non_bucket_with_handle_bodies_raises(self):
        with pytest.raises(ValueError, match="handle_bodies"):
            ChartShape(
                shape=ChartShapeType.SPLASH,
                occupied_arc=324.0,
                largest_gap=36.0,
                leading_planet=None,
                handle_planet=None,
                clusters=(frozenset({"Sun", "Moon", "Mercury"}),),
                handle_bodies=frozenset({"Sun"}),
            )

    def test_valid_splash_does_not_raise(self):
        ChartShape(
            shape=ChartShapeType.SPLASH,
            occupied_arc=324.0,
            largest_gap=36.0,
            leading_planet=None,
            handle_planet=None,
            clusters=(frozenset({"Sun", "Moon", "Mercury"}),),
        )
