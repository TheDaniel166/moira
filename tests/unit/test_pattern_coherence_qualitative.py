"""
Moira — Aspect Pattern Qualitative Scoring Test Suite
=====================================================

Policy identifier: moira.pattern_coherence.qualitative.v1-draft

Tests all 8 acceptance requirements and Section 7 synthetic configurations
stipulated in `docs/architecture/ASPECT_PATTERN_QUALITATIVE_SCORING_V1_DRAFT.md`.
"""

import math
from itertools import permutations

import pytest

from moira.aspects import (
    AspectClassification,
    AspectData,
    AspectDomain,
    AspectFamily,
    AspectMotionState,
    AspectTier,
    MotionState,
)
from moira.pattern_coherence import (
    FROZEN_REFERENCE_ORBS,
    POLICY_ID,
    PatternCoherenceBand,
    PatternCoherenceResult,
    PatternMotionQualifier,
    PatternRequiredAspectLedger,
    evaluate_pattern_coherence,
)
from moira.patterns import (
    AspectPattern,
    find_grand_crosses,
    find_grand_trines,
    find_kites,
    find_mystic_rectangles,
    find_t_squares,
    find_yods,
)


# ---------------------------------------------------------------------------
# Test Helpers
# ---------------------------------------------------------------------------

def _make_aspect(
    b1: str,
    b2: str,
    name: str,
    angle: float,
    orb: float = 0.0,
    allowed_orb: float = 8.0,
    applying: bool | None = None,
    stationary: bool = False,
    domain: AspectDomain = AspectDomain.ZODIACAL,
) -> AspectData:
    tier = AspectTier.MAJOR if name in ("Conjunction", "Sextile", "Square", "Trine", "Opposition") else AspectTier.COMMON_MINOR
    family = getattr(AspectFamily, name.upper(), AspectFamily.UNKNOWN)
    classification = AspectClassification(
        domain=domain,
        tier=tier,
        family=family,
    )
    return AspectData(
        body1=b1,
        body2=b2,
        aspect=name,
        symbol="*",
        angle=angle,
        separation=angle + orb,
        orb=orb,
        allowed_orb=allowed_orb,
        applying=applying,
        stationary=stationary,
        classification=classification,
    )


def _make_t_square(
    p1: str,
    p2: str,
    apex: str,
    opp_orb: float,
    sq1_orb: float,
    sq2_orb: float,
    allowed_orb: float = 8.0,
    opp_applying: bool | None = None,
    sq1_applying: bool | None = None,
    sq2_applying: bool | None = None,
    opp_stat: bool = False,
    sq1_stat: bool = False,
    sq2_stat: bool = False,
) -> AspectPattern:
    opp = _make_aspect(p1, p2, "Opposition", 180.0, opp_orb, allowed_orb, opp_applying, opp_stat)
    sq1 = _make_aspect(p1, apex, "Square", 90.0, sq1_orb, allowed_orb, sq1_applying, sq1_stat)
    sq2 = _make_aspect(p2, apex, "Square", 90.0, sq2_orb, allowed_orb, sq2_applying, sq2_stat)
    return AspectPattern(
        name="T-Square",
        bodies=(p1, p2, apex),
        aspects=(opp, sq1, sq2),
        apex=apex,
    )


# ---------------------------------------------------------------------------
# 1. Section 7 Source-Grounded Synthetic Configurations
# ---------------------------------------------------------------------------

class TestSection7SyntheticExamples:
    """Validate all six T-Square geometry configurations from Section 7 of draft spec."""

    @pytest.mark.parametrize(
        ("mars_lon", "jup_lon", "sq_orbs", "opp_orb", "expected_r", "expected_band"),
        [
            (90.3, 180.6, (0.3, 0.3), 0.6, 0.075, PatternCoherenceBand.VERY_STRONG),
            (91.0, 182.0, (1.0, 1.0), 2.0, 0.25, PatternCoherenceBand.STRONG),
            (92.0, 184.0, (2.0, 2.0), 4.0, 0.50, PatternCoherenceBand.MODERATE),
            (93.0, 186.0, (3.0, 3.0), 6.0, 0.75, PatternCoherenceBand.LOOSE),
            (94.0, 188.0, (4.0, 4.0), 8.0, 1.00, PatternCoherenceBand.MARGINAL),
            (96.0, 180.0, (6.0, 6.0), 0.0, 6.0 / 7.0, PatternCoherenceBand.MARGINAL),
        ],
    )
    def test_section_7_t_square_bands(
        self, mars_lon, jup_lon, sq_orbs, opp_orb, expected_r, expected_band
    ) -> None:
        pattern = _make_t_square(
            "Sun", "Jupiter", "Mars",
            opp_orb=opp_orb,
            sq1_orb=sq_orbs[0],
            sq2_orb=sq_orbs[1],
        )
        res = evaluate_pattern_coherence(pattern)
        assert res.is_assessed
        assert res.band is expected_band
        assert res.weakest_link_ratio == pytest.approx(expected_r, rel=1e-12)

    def test_section_7_motion_qualifier_applying_and_separating(self) -> None:
        """Section 7: Mars 90.3, Jupiter 180.6 with Sun +1.0, Mars +0.5, Jupiter -0.1."""
        positions = {"Sun": 0.0, "Mars": 90.3, "Jupiter": 180.6}
        speeds = {"Sun": 1.0, "Mars": 0.5, "Jupiter": -0.1}

        pattern = _make_t_square(
            "Sun", "Jupiter", "Mars",
            opp_orb=0.6, sq1_orb=0.3, sq2_orb=0.3
        )
        res_app = evaluate_pattern_coherence(pattern, positions=positions, speeds=speeds)
        assert res_app.band is PatternCoherenceBand.VERY_STRONG
        assert res_app.motion_qualifier is PatternMotionQualifier.APPLYING
        assert res_app.motion_counts["applying"] == 3

        # Reflect offsets: Mars 89.7, Jupiter 179.4 with same speeds -> Separating
        positions_rev = {"Sun": 0.0, "Mars": 89.7, "Jupiter": 179.4}
        pattern_rev = _make_t_square(
            "Sun", "Jupiter", "Mars",
            opp_orb=0.6, sq1_orb=0.3, sq2_orb=0.3
        )
        res_sep = evaluate_pattern_coherence(pattern_rev, positions=positions_rev, speeds=speeds)
        assert res_sep.band is PatternCoherenceBand.VERY_STRONG
        assert res_sep.weakest_link_ratio == res_app.weakest_link_ratio
        assert res_sep.motion_qualifier is PatternMotionQualifier.SEPARATING
        assert res_sep.motion_counts["separating"] == 3


# ---------------------------------------------------------------------------
# 2. Acceptance Requirement 1: Boundaries, Epsilon Neighborhoods, Unrounded
# ---------------------------------------------------------------------------

class TestBandBoundariesAndPrecision:
    """Requirement 1: Test upper bounds, inclusion rules, and unrounded comparisons."""

    @pytest.mark.parametrize(
        ("ratio", "expected_band"),
        [
            (0.0, PatternCoherenceBand.VERY_STRONG),
            (0.05, PatternCoherenceBand.VERY_STRONG),
            (0.10, PatternCoherenceBand.VERY_STRONG),
            (0.10 + 1e-15, PatternCoherenceBand.STRONG),
            (0.10000001, PatternCoherenceBand.STRONG),
            (0.25, PatternCoherenceBand.STRONG),
            (0.25 + 1e-15, PatternCoherenceBand.MODERATE),
            (0.50, PatternCoherenceBand.MODERATE),
            (0.50 + 1e-15, PatternCoherenceBand.LOOSE),
            (0.75, PatternCoherenceBand.LOOSE),
            (0.75 + 1e-15, PatternCoherenceBand.MARGINAL),
            (1.00, PatternCoherenceBand.MARGINAL),
            (1.50, PatternCoherenceBand.MARGINAL),
        ],
    )
    def test_band_boundaries_exact(self, ratio: float, expected_band: PatternCoherenceBand) -> None:
        # Create a Grand Trine where one trine has orb = ratio * 7.0 (ref is 7.0)
        orb = ratio * 7.0
        t1 = _make_aspect("A", "B", "Trine", 120.0, orb=orb)
        t2 = _make_aspect("B", "C", "Trine", 120.0, orb=0.0)
        t3 = _make_aspect("A", "C", "Trine", 120.0, orb=0.0)
        pattern = AspectPattern(name="Grand Trine", bodies=("A", "B", "C"), aspects=(t1, t2, t3))
        res = evaluate_pattern_coherence(pattern)
        assert res.band is expected_band
        assert res.weakest_link_ratio == pytest.approx(ratio, rel=1e-12)

    def test_unrounded_boundary_not_demoted_or_promoted(self) -> None:
        """Adjacent representable floats across 0.10 boundary follow inclusion rule."""
        target_r_above = math.nextafter(0.10, 1.0)
        orb_above = target_r_above * 7.0
        p_above = _make_t_square("A", "B", "C", opp_orb=0.0, sq1_orb=orb_above, sq2_orb=0.0)
        res_above = evaluate_pattern_coherence(p_above)
        assert res_above.band is PatternCoherenceBand.STRONG
        assert res_above.weakest_link_ratio > 0.10

        target_r_at = 0.10
        orb_at = target_r_at * 7.0
        p_at = _make_t_square("A", "B", "C", opp_orb=0.0, sq1_orb=orb_at, sq2_orb=0.0)
        res_at = evaluate_pattern_coherence(p_at)
        assert res_at.band is PatternCoherenceBand.VERY_STRONG
        assert res_at.weakest_link_ratio == 0.10


# ---------------------------------------------------------------------------
# 3. Acceptance Requirement 2: Frozen References Under Orb Settings
# ---------------------------------------------------------------------------

class TestFrozenReferencesUnderOrbSettings:
    """Requirement 2: Reference orbs do not track detector allowed_orb or orb_factor."""

    def test_detector_orb_factor_does_not_alter_scoring_references(self) -> None:
        # Opposition with orb 4.0, but allowed_orb set to 16.0 (e.g. orb_factor 2.0)
        pattern_wide = _make_t_square("A", "B", "C", opp_orb=4.0, sq1_orb=1.0, sq2_orb=1.0, allowed_orb=16.0)
        res_wide = evaluate_pattern_coherence(pattern_wide)
        # Ratio for opposition must be 4.0 / 8.0 = 0.50 (ref is frozen 8.0, NOT 16.0!)
        assert res_wide.weakest_link_ratio == pytest.approx(0.50)
        assert res_wide.band is PatternCoherenceBand.MODERATE

        # Normal allowed_orb=8.0
        pattern_norm = _make_t_square("A", "B", "C", opp_orb=4.0, sq1_orb=1.0, sq2_orb=1.0, allowed_orb=8.0)
        res_norm = evaluate_pattern_coherence(pattern_norm)
        assert res_norm.weakest_link_ratio == res_wide.weakest_link_ratio
        assert res_norm.band == res_wide.band

    def test_admitted_aspect_exceeding_reference_marked_marginal(self) -> None:
        # Opposition admitted at 9.0 degrees (e.g. under widened detector orb)
        pattern = _make_t_square("A", "B", "C", opp_orb=9.0, sq1_orb=1.0, sq2_orb=1.0, allowed_orb=10.0)
        res = evaluate_pattern_coherence(pattern)
        assert res.band is PatternCoherenceBand.MARGINAL
        assert res.weakest_link_ratio == pytest.approx(9.0 / 8.0)
        assert res.limiting_aspects[0].exceeds_reference is True
        assert "exceeds its fixed scoring reference" in res.plain_language_summary


# ---------------------------------------------------------------------------
# 4. Acceptance Requirement 3: All Six Admitted Templates
# ---------------------------------------------------------------------------

class TestAllAdmittedTemplates:
    """Requirement 3: Explicit mapping for T-Square, Grand Trine, Grand Cross, Yod, Mystic Rectangle, Kite."""

    def test_t_square_exact_links(self) -> None:
        p = _make_t_square("Sun", "Moon", "Mars", opp_orb=0.4, sq1_orb=0.35, sq2_orb=0.35)
        res = evaluate_pattern_coherence(p)
        assert res.is_assessed
        assert len(res.required_aspects) == 3
        assert res.band is PatternCoherenceBand.VERY_STRONG  # max(0.4/8=0.05, 0.35/7=0.05) = 0.05

    def test_grand_trine_exact_links(self) -> None:
        t1 = _make_aspect("A", "B", "Trine", 120.0, orb=0.7)
        t2 = _make_aspect("B", "C", "Trine", 120.0, orb=0.7)
        t3 = _make_aspect("A", "C", "Trine", 120.0, orb=0.7)
        p = AspectPattern(name="Grand Trine", bodies=("A", "B", "C"), aspects=(t1, t2, t3))
        res = evaluate_pattern_coherence(p)
        assert res.is_assessed
        assert len(res.required_aspects) == 3
        assert res.weakest_link_ratio == pytest.approx(0.10)
        assert res.band is PatternCoherenceBand.VERY_STRONG

    def test_grand_cross_exact_links(self) -> None:
        # Bodies: A, B, C, D. Oppositions: (A, C), (B, D). Squares: (A, B), (B, C), (C, D), (D, A).
        o1 = _make_aspect("A", "C", "Opposition", 180.0, orb=0.8)  # 0.8/8 = 0.10
        o2 = _make_aspect("B", "D", "Opposition", 180.0, orb=0.8)  # 0.8/8 = 0.10
        s1 = _make_aspect("A", "B", "Square", 90.0, orb=0.7)       # 0.7/7 = 0.10
        s2 = _make_aspect("B", "C", "Square", 90.0, orb=0.7)
        s3 = _make_aspect("C", "D", "Square", 90.0, orb=0.7)
        s4 = _make_aspect("D", "A", "Square", 90.0, orb=0.7)
        p = AspectPattern(name="Grand Cross", bodies=("A", "B", "C", "D"), aspects=(o1, o2, s1, s2, s3, s4))
        res = evaluate_pattern_coherence(p)
        assert res.is_assessed
        assert len(res.required_aspects) == 6
        assert res.weakest_link_ratio == pytest.approx(0.10)
        assert res.band is PatternCoherenceBand.VERY_STRONG

    def test_yod_exact_links(self) -> None:
        # Base A, B (Sextile), Apex C (Quincunx A-C, B-C)
        s = _make_aspect("A", "B", "Sextile", 60.0, orb=0.5)      # 0.5/5 = 0.10
        q1 = _make_aspect("A", "C", "Quincunx", 150.0, orb=0.3)   # 0.3/3 = 0.10
        q2 = _make_aspect("B", "C", "Quincunx", 150.0, orb=0.3)   # 0.3/3 = 0.10
        p = AspectPattern(name="Yod", bodies=("A", "B", "C"), aspects=(s, q1, q2), apex="C")
        res = evaluate_pattern_coherence(p)
        assert res.is_assessed
        assert len(res.required_aspects) == 3
        assert res.weakest_link_ratio == pytest.approx(0.10)
        assert res.band is PatternCoherenceBand.VERY_STRONG

    def test_mystic_rectangle_exact_links(self) -> None:
        # Oppositions (A, C), (B, D). Trines (A, B), (C, D). Sextiles (B, C), (D, A).
        o1 = _make_aspect("A", "C", "Opposition", 180.0, orb=0.8)
        o2 = _make_aspect("B", "D", "Opposition", 180.0, orb=0.8)
        t1 = _make_aspect("A", "B", "Trine", 120.0, orb=0.7)
        t2 = _make_aspect("C", "D", "Trine", 120.0, orb=0.7)
        s1 = _make_aspect("B", "C", "Sextile", 60.0, orb=0.5)
        s2 = _make_aspect("D", "A", "Sextile", 60.0, orb=0.5)
        p = AspectPattern(name="Mystic Rectangle", bodies=("A", "B", "C", "D"), aspects=(o1, o2, t1, t2, s1, s2))
        res = evaluate_pattern_coherence(p)
        assert res.is_assessed
        assert len(res.required_aspects) == 6
        assert res.weakest_link_ratio == pytest.approx(0.10)
        assert res.band is PatternCoherenceBand.VERY_STRONG

    def test_kite_exact_links(self) -> None:
        # Grand Trine: X, Y, Apex. Tail: opposes Apex, sextiles X and Y.
        t_xy = _make_aspect("X", "Y", "Trine", 120.0, orb=0.7)
        t_xa = _make_aspect("X", "Apex", "Trine", 120.0, orb=0.7)
        t_ya = _make_aspect("Y", "Apex", "Trine", 120.0, orb=0.7)
        opp = _make_aspect("Tail", "Apex", "Opposition", 180.0, orb=0.8)
        s_tx = _make_aspect("Tail", "X", "Sextile", 60.0, orb=0.5)
        s_ty = _make_aspect("Tail", "Y", "Sextile", 60.0, orb=0.5)
        p = AspectPattern(
            name="Kite",
            bodies=("Apex", "Tail", "X", "Y"),
            aspects=(t_xy, t_xa, t_ya, opp, s_tx, s_ty),
            apex="Apex",
        )
        res = evaluate_pattern_coherence(p)
        assert res.is_assessed
        assert len(res.required_aspects) == 6
        assert res.weakest_link_ratio == pytest.approx(0.10)
        assert res.band is PatternCoherenceBand.VERY_STRONG

    def test_unsupported_template_reported_not_assessed(self) -> None:
        # Stellium or Thor's Hammer should be Not assessed
        s1 = _make_aspect("A", "B", "Square", 90.0)
        p = AspectPattern(name="Stellium", bodies=("A", "B", "C"), aspects=(s1,))
        res = evaluate_pattern_coherence(p)
        assert not res.is_assessed
        assert res.band is PatternCoherenceBand.NOT_ASSESSED
        assert "Unsupported pattern template" in res.assessment_reason

    def test_supplemental_aspect_does_not_affect_band(self) -> None:
        # Grand Trine with an extra irrelevant Square passed in aspects
        t1 = _make_aspect("A", "B", "Trine", 120.0, orb=0.7)
        t2 = _make_aspect("B", "C", "Trine", 120.0, orb=0.7)
        t3 = _make_aspect("A", "C", "Trine", 120.0, orb=0.7)
        extra_sq = _make_aspect("A", "B", "Square", 90.0, orb=6.0)
        p = AspectPattern(name="Grand Trine", bodies=("A", "B", "C"), aspects=(t1, t2, t3, extra_sq))
        res = evaluate_pattern_coherence(p)
        assert res.is_assessed
        assert len(res.required_aspects) == 3
        assert len(res.supplemental_aspects) == 1
        assert res.band is PatternCoherenceBand.VERY_STRONG
        assert res.weakest_link_ratio == pytest.approx(0.10)


# ---------------------------------------------------------------------------
# 5. Acceptance Requirement 4: Weak-Link Limiting, Duplicate Invariance, No Body Bonus
# ---------------------------------------------------------------------------

class TestWeakLinkAndInvariance:
    """Requirement 4: Weak-link limiting, order and duplicate invariance, no body count bonus."""

    def test_weakest_link_cannot_be_rescued_by_exact_links(self) -> None:
        # T-Square: Squares are 0 orb, but Opposition has orb 6.0 (ratio 6/8 = 0.75 -> Loose)
        p = _make_t_square("A", "B", "C", opp_orb=6.0, sq1_orb=0.0, sq2_orb=0.0)
        res = evaluate_pattern_coherence(p)
        assert res.band is PatternCoherenceBand.LOOSE
        assert res.weakest_link_ratio == pytest.approx(0.75)
        assert len(res.limiting_aspects) == 1
        assert res.limiting_aspects[0].aspect == "Opposition"

    def test_duplicate_aspect_invariance(self) -> None:
        opp = _make_aspect("A", "B", "Opposition", 180.0, orb=2.0)
        sq1 = _make_aspect("A", "C", "Square", 90.0, orb=1.0)
        sq2 = _make_aspect("B", "C", "Square", 90.0, orb=1.0)
        # Duplicate sq1
        p_normal = AspectPattern(name="T-Square", bodies=("A", "B", "C"), aspects=(opp, sq1, sq2), apex="C")
        p_dup = AspectPattern(name="T-Square", bodies=("A", "B", "C"), aspects=(opp, sq1, sq2, sq1), apex="C")
        res_norm = evaluate_pattern_coherence(p_normal)
        res_dup = evaluate_pattern_coherence(p_dup)
        assert res_dup.band == res_norm.band
        assert res_dup.weakest_link_ratio == res_norm.weakest_link_ratio
        assert len(res_dup.required_aspects) == len(res_norm.required_aspects)

    def test_order_invariance(self) -> None:
        t1 = _make_aspect("A", "B", "Trine", 120.0, orb=0.7)
        t2 = _make_aspect("B", "C", "Trine", 120.0, orb=1.4)
        t3 = _make_aspect("A", "C", "Trine", 120.0, orb=2.1)
        base_res = evaluate_pattern_coherence(AspectPattern(name="Grand Trine", bodies=("A", "B", "C"), aspects=(t1, t2, t3)))

        for perm in permutations([t1, t2, t3]):
            p = AspectPattern(name="Grand Trine", bodies=("A", "B", "C"), aspects=perm)
            res = evaluate_pattern_coherence(p)
            assert res.band == base_res.band
            assert res.weakest_link_ratio == base_res.weakest_link_ratio

    def test_no_body_count_bonus(self) -> None:
        """Equal tight ratios produce same band regardless of 3-body vs 4-body."""
        # 3-body Grand Trine with ratio 0.05
        gt = AspectPattern(
            name="Grand Trine",
            bodies=("A", "B", "C"),
            aspects=(
                _make_aspect("A", "B", "Trine", 120.0, orb=0.35),
                _make_aspect("B", "C", "Trine", 120.0, orb=0.35),
                _make_aspect("A", "C", "Trine", 120.0, orb=0.35),
            ),
        )
        # 4-body Grand Cross with ratio 0.05
        gc = AspectPattern(
            name="Grand Cross",
            bodies=("A", "B", "C", "D"),
            aspects=(
                _make_aspect("A", "C", "Opposition", 180.0, orb=0.4),
                _make_aspect("B", "D", "Opposition", 180.0, orb=0.4),
                _make_aspect("A", "B", "Square", 90.0, orb=0.35),
                _make_aspect("B", "C", "Square", 90.0, orb=0.35),
                _make_aspect("C", "D", "Square", 90.0, orb=0.35),
                _make_aspect("D", "A", "Square", 90.0, orb=0.35),
            ),
        )
        res_gt = evaluate_pattern_coherence(gt)
        res_gc = evaluate_pattern_coherence(gc)
        assert res_gt.band is PatternCoherenceBand.VERY_STRONG
        assert res_gc.band is PatternCoherenceBand.VERY_STRONG
        assert res_gt.weakest_link_ratio == pytest.approx(res_gc.weakest_link_ratio)


# ---------------------------------------------------------------------------
# 6. Acceptance Requirement 5: All Seven Motion Qualifier Rules in Order
# ---------------------------------------------------------------------------

class TestMotionQualifierRulesInPrecedenceOrder:
    """Requirement 5: Test the 7 rules in exact precedence order."""

    def test_rule_1_all_indeterminate_yields_motion_unavailable(self) -> None:
        p = _make_t_square("A", "B", "C", opp_orb=1.0, sq1_orb=1.0, sq2_orb=1.0, opp_applying=None, sq1_applying=None, sq2_applying=None)
        res = evaluate_pattern_coherence(p)
        assert res.motion_qualifier is PatternMotionQualifier.MOTION_UNAVAILABLE
        assert res.motion_counts["indeterminate"] == 3

    def test_rule_2_some_indeterminate_yields_partial_motion(self) -> None:
        p = _make_t_square("A", "B", "C", opp_orb=1.0, sq1_orb=1.0, sq2_orb=1.0, opp_applying=None, sq1_applying=True, sq2_applying=True)
        res = evaluate_pattern_coherence(p)
        assert res.motion_qualifier is PatternMotionQualifier.PARTIAL_MOTION
        assert res.motion_counts["indeterminate"] == 1
        assert res.motion_counts["applying"] == 2

    def test_rule_3_any_stationary_yields_station_sensitive(self) -> None:
        # All known, one is stationary
        p = _make_t_square("A", "B", "C", opp_orb=1.0, sq1_orb=1.0, sq2_orb=1.0, opp_applying=True, sq1_applying=True, sq2_applying=True, opp_stat=True)
        res = evaluate_pattern_coherence(p)
        assert res.motion_qualifier is PatternMotionQualifier.STATION_SENSITIVE
        assert res.motion_counts["stationary"] == 1

    def test_rule_3_stationary_via_aspect_motion_witness(self) -> None:
        """Witness detects body below stationary threshold away from exactness."""
        positions = {"Mercury": 10.0, "Mars": 100.5, "Jupiter": 190.5}
        speeds = {"Mercury": 0.002, "Mars": 0.5, "Jupiter": -0.1}  # Mercury < 0.005 threshold
        p = _make_t_square("Mercury", "Jupiter", "Mars", opp_orb=0.5, sq1_orb=0.5, sq2_orb=0.0)
        res = evaluate_pattern_coherence(p, positions=positions, speeds=speeds)
        assert res.motion_qualifier is PatternMotionQualifier.STATION_SENSITIVE
        assert res.motion_counts["stationary"] >= 1

    def test_rule_3_relative_motion_stalled_yields_station_sensitive(self) -> None:
        """Witness detects stalled relative rate between two bodies."""
        positions = {"Sun": 10.0, "Mars": 100.5, "Jupiter": 190.5}
        speeds = {"Sun": 1.0, "Jupiter": 1.0, "Mars": 0.5}  # Sun & Jupiter relative rate == 0.0
        p = _make_t_square("Sun", "Jupiter", "Mars", opp_orb=0.5, sq1_orb=0.5, sq2_orb=0.0)
        res = evaluate_pattern_coherence(p, positions=positions, speeds=speeds)
        assert res.motion_qualifier is PatternMotionQualifier.STATION_SENSITIVE
        assert res.motion_counts["stationary"] >= 1

    def test_rule_4_all_exact_yields_exact(self) -> None:
        p = _make_t_square("A", "B", "C", opp_orb=0.0, sq1_orb=0.0, sq2_orb=0.0)
        res = evaluate_pattern_coherence(p)
        assert res.motion_qualifier is PatternMotionQualifier.EXACT
        assert res.motion_counts["exact"] == 3

    def test_rule_5_all_applying_yields_applying(self) -> None:
        p = _make_t_square("A", "B", "C", opp_orb=1.0, sq1_orb=1.0, sq2_orb=1.0, opp_applying=True, sq1_applying=True, sq2_applying=True)
        res = evaluate_pattern_coherence(p)
        assert res.motion_qualifier is PatternMotionQualifier.APPLYING
        assert res.motion_counts["applying"] == 3

    def test_rule_6_all_separating_yields_separating(self) -> None:
        p = _make_t_square("A", "B", "C", opp_orb=1.0, sq1_orb=1.0, sq2_orb=1.0, opp_applying=False, sq1_applying=False, sq2_applying=False)
        res = evaluate_pattern_coherence(p)
        assert res.motion_qualifier is PatternMotionQualifier.SEPARATING
        assert res.motion_counts["separating"] == 3

    def test_rule_7_mixed_motion_applying_and_separating(self) -> None:
        p = _make_t_square("A", "B", "C", opp_orb=1.0, sq1_orb=1.0, sq2_orb=1.0, opp_applying=True, sq1_applying=False, sq2_applying=False)
        res = evaluate_pattern_coherence(p)
        assert res.motion_qualifier is PatternMotionQualifier.MIXED_MOTION
        assert res.motion_counts["applying"] == 1
        assert res.motion_counts["separating"] == 2
        assert "1 applying · 2 separating" in res.plain_language_summary

    def test_rule_7_mixed_motion_applying_and_exact(self) -> None:
        # Opp exact (orb 0.0), two squares applying (orb 1.0)
        p = _make_t_square("A", "B", "C", opp_orb=0.0, sq1_orb=1.0, sq2_orb=1.0, sq1_applying=True, sq2_applying=True)
        res = evaluate_pattern_coherence(p)
        assert res.motion_qualifier is PatternMotionQualifier.MIXED_MOTION
        assert res.motion_counts["exact"] == 1
        assert res.motion_counts["applying"] == 2
        assert "2 applying · 1 exact" in res.plain_language_summary


# ---------------------------------------------------------------------------
# 7. Acceptance Requirement 7: Degenerate, Adversarial & Invalid Inputs
# ---------------------------------------------------------------------------

class TestDegenerateAndAdversarialInputs:
    """Requirement 7: Incompatible frames, missing geometry, invalid values, empty edge sets."""

    def test_empty_aspects_returns_not_assessed(self) -> None:
        p = AspectPattern(name="Grand Trine", bodies=("A", "B", "C"), aspects=())
        res = evaluate_pattern_coherence(p)
        assert not res.is_assessed
        assert res.band is PatternCoherenceBand.NOT_ASSESSED

    def test_missing_required_edge_returns_not_assessed(self) -> None:
        # T-Square with only 2 aspects (missing one square)
        opp = _make_aspect("A", "B", "Opposition", 180.0)
        sq1 = _make_aspect("A", "C", "Square", 90.0)
        p = AspectPattern(name="T-Square", bodies=("A", "B", "C"), aspects=(opp, sq1), apex="C")
        res = evaluate_pattern_coherence(p)
        assert not res.is_assessed
        assert res.band is PatternCoherenceBand.NOT_ASSESSED
        assert "Missing required aspect links" in res.assessment_reason

    def test_categorical_whole_sign_aspects_rejected(self) -> None:
        t1 = _make_aspect("A", "B", "Trine", 120.0, domain=AspectDomain.WHOLE_SIGN)
        t2 = _make_aspect("B", "C", "Trine", 120.0)
        t3 = _make_aspect("A", "C", "Trine", 120.0)
        p = AspectPattern(name="Grand Trine", bodies=("A", "B", "C"), aspects=(t1, t2, t3))
        res = evaluate_pattern_coherence(p)
        assert not res.is_assessed
        assert "Categorical whole-sign aspects are not admitted" in res.assessment_reason

    def test_conflicting_aspect_duplicates_rejected(self) -> None:
        t1 = _make_aspect("A", "B", "Trine", 120.0, orb=0.5)
        t1_conflict = _make_aspect("A", "B", "Trine", 120.0, orb=1.5)  # conflicting orb!
        t2 = _make_aspect("B", "C", "Trine", 120.0, orb=0.5)
        t3 = _make_aspect("A", "C", "Trine", 120.0, orb=0.5)
        p = AspectPattern(name="Grand Trine", bodies=("A", "B", "C"), aspects=(t1, t1_conflict, t2, t3))
        res = evaluate_pattern_coherence(p)
        assert not res.is_assessed
        assert "Conflicting aspect definitions" in res.assessment_reason

    def test_non_finite_orb_rejected(self) -> None:
        t1 = _make_aspect("A", "B", "Trine", 120.0, orb=float("nan"))
        t2 = _make_aspect("B", "C", "Trine", 120.0, orb=0.5)
        t3 = _make_aspect("A", "C", "Trine", 120.0, orb=0.5)
        p = AspectPattern(name="Grand Trine", bodies=("A", "B", "C"), aspects=(t1, t2, t3))
        res = evaluate_pattern_coherence(p)
        assert not res.is_assessed
        assert "Non-finite" in res.assessment_reason

    def test_boolean_orb_rejected(self) -> None:
        # bool is an instance of int in Python, must be guarded against
        t1 = _make_aspect("A", "B", "Trine", 120.0, orb=True)  # type: ignore
        t2 = _make_aspect("B", "C", "Trine", 120.0, orb=0.5)
        t3 = _make_aspect("A", "C", "Trine", 120.0, orb=0.5)
        p = AspectPattern(name="Grand Trine", bodies=("A", "B", "C"), aspects=(t1, t2, t3))
        res = evaluate_pattern_coherence(p)
        assert not res.is_assessed
        assert "Boolean" in res.assessment_reason


# ---------------------------------------------------------------------------
# 8. AspectPattern Convenience Method
# ---------------------------------------------------------------------------

class TestAspectPatternConvenienceMethod:
    """Validate that AspectPattern.evaluate_coherence() delegates cleanly."""

    def test_aspect_pattern_method_matches_free_function(self) -> None:
        p = _make_t_square("Sun", "Moon", "Mars", opp_orb=0.4, sq1_orb=0.35, sq2_orb=0.35)
        res_fn = evaluate_pattern_coherence(p)
        res_method = p.evaluate_coherence()
        assert res_method == res_fn
        assert res_method.policy_id == POLICY_ID
