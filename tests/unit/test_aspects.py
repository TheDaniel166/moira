from __future__ import annotations

import pytest

from moira.aspects import (
    CANONICAL_ASPECTS,
    AspectClassification,
    AspectData,
    AspectDomain,
    AspectFamily,
    AspectFamilyProfile,
    AspectGraph,
    AspectGraphNode,
    AspectHarmonicProfile,
    AspectPattern,
    AspectPatternKind,
    AspectPolicy,
    AspectStrength,
    AspectTier,
    DEFAULT_POLICY,
    DeclinationAspect,
    MotionState,
    aspect_harmonic_profile,
    aspect_motion_state,
    aspect_strength,
    aspects_between,
    aspects_to_point,
    build_aspect_graph,
    find_aspects,
    find_declination_aspects,
    find_patterns,
)


def test_find_aspects_detects_wraparound_conjunction() -> None:
    results = find_aspects(
        {
            "Sun": 359.0,
            "Moon": 1.0,
        },
        include_minor=False,
    )

    assert len(results) == 1
    aspect = results[0]
    assert aspect.aspect == "Conjunction"
    assert aspect.body1 == "Sun"
    assert aspect.body2 == "Moon"
    assert aspect.orb == 2.0


def test_aspect_data_repr_includes_applying_and_stationary_flags() -> None:
    aspect = AspectData(
        body1="Sun",
        body2="Moon",
        aspect="Conjunction",
        symbol="☌",
        angle=0.0,
        separation=0.5,
        orb=0.5,
        allowed_orb=8.0,
        applying=True,
        stationary=True,
    )

    rendered = repr(aspect)
    assert "Sun" in rendered
    assert "Moon" in rendered
    assert "applying" in rendered
    assert "[stationary]" in rendered


def test_find_aspects_tier_overrides_include_minor_flag() -> None:
    positions = {
        "Sun": 0.0,
        "Moon": 150.0,
    }

    major_only = find_aspects(positions, include_minor=True, tier=0)
    common_minor = find_aspects(positions, include_minor=False, tier=1)

    assert major_only == []
    assert len(common_minor) == 1
    assert common_minor[0].aspect == "Quincunx"


def test_find_aspects_invalid_tier_falls_back_to_major_only() -> None:
    results = find_aspects(
        {
            "Sun": 0.0,
            "Moon": 60.0,
            "Mars": 150.0,
        },
        tier=999,
        include_minor=True,
    )

    assert [aspect.aspect for aspect in results] == ["Sextile", "Square"]


def test_find_aspects_custom_orbs_override_orb_factor() -> None:
    results = find_aspects(
        {
            "Sun": 0.0,
            "Moon": 66.0,
        },
        orbs={60.0: 6.0},
        include_minor=False,
        orb_factor=0.1,
    )

    assert len(results) == 1
    assert results[0].aspect == "Sextile"
    assert results[0].orb == 6.0


def test_find_aspects_no_match_returns_empty_list() -> None:
    results = find_aspects(
        {
            "Sun": 0.0,
            "Moon": 13.0,
        },
        include_minor=False,
        orb_factor=0.1,
    )

    assert results == []


def test_find_aspects_returns_sorted_by_tightest_orb() -> None:
    results = find_aspects(
        {
            "Sun": 0.0,
            "Moon": 121.0,
            "Mercury": 200.0,
            "Venus": 262.0,
        },
        include_minor=False,
    )

    assert [aspect.aspect for aspect in results] == ["Trine", "Sextile"]
    assert [aspect.orb for aspect in results] == [1.0, 2.0]
    assert results[0].orb <= results[1].orb


def test_aspects_between_extended_minor_is_available_at_default_tier() -> None:
    results = aspects_between(
        "Sun",
        0.0,
        "Moon",
        36.0,
    )

    assert len(results) == 1
    assert results[0].aspect == "Decile"
    assert results[0].orb == 0.0


def test_aspects_between_invalid_tier_falls_back_to_all_aspects() -> None:
    results = aspects_between(
        "Sun",
        0.0,
        "Moon",
        36.0,
        tier=999,
    )

    assert len(results) == 1
    assert results[0].aspect == "Decile"


def test_aspects_between_applying_and_separating_respect_wraparound() -> None:
    applying = aspects_between(
        "Sun",
        359.0,
        "Moon",
        1.0,
        tier=0,
        speed_a=2.0,
        speed_b=1.0,
    )
    separating = aspects_between(
        "Sun",
        359.0,
        "Moon",
        1.0,
        tier=0,
        speed_a=1.0,
        speed_b=2.0,
    )

    assert len(applying) == 1
    assert applying[0].applying is True
    assert applying[0].stationary is False

    assert len(separating) == 1
    assert separating[0].applying is False
    assert separating[0].stationary is False


def test_aspects_between_partial_speed_information_yields_unknown_applying() -> None:
    results = aspects_between(
        "Sun",
        0.0,
        "Moon",
        60.0,
        tier=0,
        speed_a=1.0,
    )

    assert len(results) == 1
    assert results[0].applying is None
    assert results[0].stationary is False


def test_aspects_between_stationary_body_sets_stationary_and_unknown_applying() -> None:
    results = aspects_between(
        "Sun",
        0.0,
        "Moon",
        60.0,
        tier=0,
        speed_a=0.004,
        speed_b=1.0,
    )

    assert len(results) == 1
    assert results[0].aspect == "Sextile"
    assert results[0].applying is None
    assert results[0].stationary is True


def test_aspects_between_custom_orbs_override_orb_factor() -> None:
    results = aspects_between(
        "Sun",
        0.0,
        "Moon",
        66.0,
        tier=0,
        orbs={60.0: 6.0},
        orb_factor=0.1,
    )

    assert len(results) == 1
    assert results[0].aspect == "Sextile"
    assert results[0].orb == 6.0


def test_aspects_to_point_respects_point_name_and_sorting() -> None:
    results = aspects_to_point(
        120.0,
        {
            "Sun": 119.0,
            "Moon": 0.0,
            "Mercury": 271.0,
        },
        point_name="MC",
        include_minor=False,
    )

    assert [aspect.body2 for aspect in results] == ["MC", "MC"]
    assert [aspect.body1 for aspect in results] == ["Moon", "Sun"]
    assert [aspect.aspect for aspect in results] == ["Trine", "Conjunction"]
    assert [aspect.orb for aspect in results] == [0.0, 1.0]


def test_aspects_to_point_custom_orbs_and_invalid_tier_paths() -> None:
    results = aspects_to_point(
        60.0,
        {
            "Sun": 126.0,
            "Moon": 0.0,
        },
        point_name="Vertex",
        orbs={60.0: 6.0},
        tier=999,
        orb_factor=0.1,
    )

    assert len(results) == 2
    assert [aspect.body1 for aspect in results] == ["Moon", "Sun"]
    assert [aspect.body2 for aspect in results] == ["Vertex", "Vertex"]
    assert [aspect.aspect for aspect in results] == ["Sextile", "Sextile"]
    assert [aspect.orb for aspect in results] == [0.0, 6.0]


def test_aspects_to_point_no_match_returns_empty_list() -> None:
    results = aspects_to_point(
        120.0,
        {
            "Sun": 10.0,
        },
        include_minor=False,
        orb_factor=0.1,
    )

    assert results == []


def test_find_declination_aspects_detects_parallel() -> None:
    results = find_declination_aspects(
        {
            "Sun": 10.0,
            "Moon": 10.5,
        },
        orb=1.0,
    )

    assert len(results) == 1
    assert results[0].aspect == "Parallel"
    assert results[0].body1 == "Sun"
    assert results[0].body2 == "Moon"
    assert round(results[0].orb, 6) == 0.5


def test_find_declination_aspects_detects_contraparallel() -> None:
    results = find_declination_aspects(
        {
            "Sun": 10.0,
            "Mars": -10.2,
        },
        orb=1.0,
    )

    assert len(results) == 1
    assert results[0].aspect == "Contra-Parallel"
    assert results[0].body1 == "Sun"
    assert results[0].body2 == "Mars"
    assert round(results[0].orb, 6) == 0.2


def test_declination_aspect_repr_and_no_match_path() -> None:
    aspect = DeclinationAspect(
        body1="Sun",
        body2="Moon",
        aspect="Parallel",
        dec1=10.0,
        dec2=10.2,
        orb=0.2,
        allowed_orb=1.0,
    )

    rendered = repr(aspect)
    assert "Parallel" in rendered
    assert "Sun" in rendered
    assert "Moon" in rendered

    assert find_declination_aspects({"Sun": 10.0, "Moon": 25.0}, orb=1.0) == []


# ---------------------------------------------------------------------------
# Phase 1 — enriched truth preservation tests
# ---------------------------------------------------------------------------

def test_aspect_data_separation_consistent_with_orb_and_angle() -> None:
    """separation, orb, and angle satisfy the admission identity on every result."""
    results = find_aspects(
        {"Sun": 0.0, "Moon": 121.0, "Mercury": 200.0},
        include_minor=False,
    )
    assert results, "expected at least one aspect"
    for a in results:
        assert abs(abs(a.separation - a.angle) - a.orb) < 1e-9, (
            f"identity violation: sep={a.separation} angle={a.angle} orb={a.orb}"
        )


def test_aspect_data_orb_within_allowed_orb() -> None:
    """Every admitted aspect satisfies orb <= allowed_orb."""
    results = find_aspects(
        {"Sun": 0.0, "Moon": 58.0, "Mars": 121.0},
        include_minor=True,
    )
    assert results
    for a in results:
        assert a.orb <= a.allowed_orb + 1e-9, (
            f"admission gate violated: orb={a.orb} allowed={a.allowed_orb} for {a}"
        )


def test_aspect_data_allowed_orb_reflects_orb_factor() -> None:
    """allowed_orb is scaled by orb_factor when no custom orbs dict is supplied."""
    # Sextile default orb = 5°; Moon at 56° gives sep=56°, deviation=4°
    # orb_factor=1.0 → allowed=5.0 → 4.0 ≤ 5.0 admitted
    # orb_factor=0.5 → allowed=2.5 → 4.0 > 2.5 excluded
    results_full = find_aspects(
        {"Sun": 0.0, "Moon": 56.0},
        include_minor=False,
        orb_factor=1.0,
    )
    results_half = find_aspects(
        {"Sun": 0.0, "Moon": 56.0},
        include_minor=False,
        orb_factor=0.5,
    )
    assert results_full, "expected a sextile at orb_factor=1"
    assert results_half == [], "tight orb_factor=0.5 should exclude orb=4°"
    assert results_full[0].allowed_orb == pytest.approx(5.0)


def test_aspect_data_allowed_orb_reflects_custom_orbs_dict() -> None:
    """allowed_orb records the value from the custom orbs dict, not the default."""
    results = find_aspects(
        {"Sun": 0.0, "Moon": 66.0},
        orbs={60.0: 6.0},
        include_minor=False,
        orb_factor=0.1,
    )
    assert len(results) == 1
    assert results[0].allowed_orb == pytest.approx(6.0)
    assert results[0].orb == pytest.approx(6.0)


def test_aspects_between_enriched_fields_are_consistent() -> None:
    """aspects_between populates separation and allowed_orb correctly."""
    results = aspects_between("Sun", 0.0, "Moon", 120.0, tier=0)
    assert len(results) == 1
    a = results[0]
    assert a.separation == pytest.approx(120.0)
    assert a.angle == pytest.approx(120.0)
    assert a.orb == pytest.approx(0.0)
    assert a.allowed_orb == pytest.approx(7.0)
    assert abs(abs(a.separation - a.angle) - a.orb) < 1e-9


def test_aspects_to_point_enriched_fields_are_consistent() -> None:
    """aspects_to_point populates separation and allowed_orb correctly."""
    results = aspects_to_point(
        120.0,
        {"Sun": 119.0},
        point_name="MC",
        include_minor=False,
    )
    assert len(results) == 1
    a = results[0]
    assert a.separation == pytest.approx(1.0)
    assert a.angle == pytest.approx(0.0)
    assert a.orb == pytest.approx(1.0)
    assert a.allowed_orb == pytest.approx(8.0)
    assert a.applying is None
    assert abs(abs(a.separation - a.angle) - a.orb) < 1e-9


def test_declination_aspect_allowed_orb_matches_call_argument() -> None:
    """DeclinationAspect.allowed_orb equals the orb argument passed to the engine."""
    results = find_declination_aspects({"Sun": 10.0, "Moon": 10.5}, orb=0.8)
    assert len(results) == 1
    assert results[0].allowed_orb == pytest.approx(0.8)
    assert results[0].orb <= results[0].allowed_orb + 1e-9


def test_declination_aspect_orb_identity_parallel() -> None:
    """For a Parallel: orb == abs(dec1 - dec2)."""
    results = find_declination_aspects({"Sun": 12.0, "Mars": 12.3}, orb=1.0)
    assert len(results) == 1
    a = results[0]
    assert a.aspect == "Parallel"
    assert a.orb == pytest.approx(abs(a.dec1 - a.dec2))


def test_declination_aspect_orb_identity_contra_parallel() -> None:
    """For a Contra-Parallel: orb == abs(dec1 + dec2)."""
    results = find_declination_aspects({"Sun": 10.0, "Mars": -10.3}, orb=1.0)
    assert len(results) == 1
    a = results[0]
    assert a.aspect == "Contra-Parallel"
    assert a.orb == pytest.approx(abs(a.dec1 + a.dec2))


def test_enriched_fields_do_not_alter_detection_semantics() -> None:
    """Existing detection results are unchanged; only extra fields are added."""
    positions = {
        "Sun": 359.0,
        "Moon": 1.0,
    }
    results = find_aspects(positions, include_minor=False)
    assert len(results) == 1
    a = results[0]
    assert a.aspect == "Conjunction"
    assert a.body1 == "Sun"
    assert a.body2 == "Moon"
    assert a.orb == pytest.approx(2.0)
    assert a.separation == pytest.approx(2.0)
    assert a.angle == pytest.approx(0.0)
    assert a.allowed_orb == pytest.approx(8.0)


# ---------------------------------------------------------------------------
# Phase 2 — classification tests
# ---------------------------------------------------------------------------

def test_aspect_classification_is_present_on_find_aspects_results() -> None:
    """Every result from find_aspects carries a non-None classification."""
    results = find_aspects(
        {"Sun": 0.0, "Moon": 60.0, "Mars": 90.0, "Venus": 120.0},
        include_minor=True,
    )
    assert results
    for a in results:
        assert a.classification is not None


def test_zodiacal_aspects_have_zodiacal_domain() -> None:
    """All results from ecliptic detection have domain == ZODIACAL."""
    results = find_aspects(
        {"Sun": 0.0, "Moon": 60.0, "Mars": 120.0},
        include_minor=False,
    )
    assert results
    for a in results:
        assert a.classification.domain is AspectDomain.ZODIACAL


def test_declination_aspects_have_declination_domain() -> None:
    """All results from find_declination_aspects have domain == DECLINATION."""
    results = find_declination_aspects({"Sun": 10.0, "Moon": 10.4}, orb=1.0)
    assert results
    for a in results:
        assert a.classification.domain is AspectDomain.DECLINATION


def test_major_aspects_classified_as_major_tier() -> None:
    """Conjunction, Sextile, Square, Trine, Opposition → tier == MAJOR."""
    cases = [
        (0.0, 0.0),      # Conjunction
        (60.0, 60.0),    # Sextile
        (90.0, 90.0),    # Square
        (120.0, 120.0),  # Trine
        (180.0, 180.0),  # Opposition
    ]
    for lon2, _ in cases:
        results = aspects_between("Sun", 0.0, "Moon", lon2, tier=0)
        assert results, f"expected a major aspect at {lon2}°"
        assert results[0].classification.tier is AspectTier.MAJOR, (
            f"{results[0].aspect} should be MAJOR"
        )


def test_common_minor_aspects_classified_as_common_minor_tier() -> None:
    """Semisextile, Semisquare, Quincunx, Quintile, Biquintile, Sesquiquadrate → COMMON_MINOR."""
    common_minor_angles = [30.0, 45.0, 72.0, 135.0, 144.0, 150.0]
    for lon2 in common_minor_angles:
        results = aspects_between("Sun", 0.0, "Moon", lon2, tier=1)
        minor = [r for r in results if not r.classification.tier == AspectTier.MAJOR]
        assert minor, f"expected a common-minor aspect at {lon2}°"
        assert minor[0].classification.tier is AspectTier.COMMON_MINOR, (
            f"{minor[0].aspect} should be COMMON_MINOR"
        )


def test_extended_minor_aspects_classified_as_extended_minor_tier() -> None:
    """Novile (40°) and Decile (36°) are extended-minor."""
    for lon2 in (36.0, 40.0):
        results = aspects_between("Sun", 0.0, "Moon", lon2, tier=2)
        ext = [r for r in results
               if r.classification.tier is AspectTier.EXTENDED_MINOR]
        assert ext, f"expected an extended-minor aspect at {lon2}°"


def test_quintile_and_biquintile_share_quintile_family() -> None:
    """72° and 144° both belong to the QUINTILE family."""
    r72  = aspects_between("Sun", 0.0, "Moon",  72.0, tier=1)
    r144 = aspects_between("Sun", 0.0, "Moon", 144.0, tier=1)
    assert r72  and r72[0].aspect  == "Quintile"
    assert r144 and r144[0].aspect == "Biquintile"
    assert r72[0].classification.family  is AspectFamily.QUINTILE
    assert r144[0].classification.family is AspectFamily.QUINTILE


def test_septile_series_shares_septile_family() -> None:
    """Septile, Biseptile, Triseptile all classify as AspectFamily.SEPTILE."""
    angles = [360 / 7, 720 / 7, 1080 / 7]
    for lon2 in angles:
        results = aspects_between("Sun", 0.0, "Moon", lon2, tier=2)
        sept = [r for r in results if r.classification.family is AspectFamily.SEPTILE]
        assert sept, f"expected a SEPTILE-family aspect at {lon2:.4f}°"


def test_novile_series_shares_novile_family() -> None:
    """Novile (40°), Binovile (80°), Quadnovile (160°) all → AspectFamily.NOVILE."""
    for lon2 in (40.0, 80.0, 160.0):
        results = aspects_between("Sun", 0.0, "Moon", lon2, tier=2)
        novile = [r for r in results if r.classification.family is AspectFamily.NOVILE]
        assert novile, f"expected a NOVILE-family aspect at {lon2}°"


def test_decile_and_tredecile_share_decile_family() -> None:
    """Decile (36°) and Tredecile (108°) both classify as AspectFamily.DECILE."""
    r36  = aspects_between("Sun", 0.0, "Moon",  36.0, tier=2)
    r108 = aspects_between("Sun", 0.0, "Moon", 108.0, tier=2)
    decile_36  = [r for r in r36  if r.classification.family is AspectFamily.DECILE]
    decile_108 = [r for r in r108 if r.classification.family is AspectFamily.DECILE]
    assert decile_36,  "expected Decile at 36°"
    assert decile_108, "expected Tredecile at 108°"


def test_declination_aspects_have_declination_family() -> None:
    """Both Parallel and Contra-Parallel classify with AspectFamily.DECLINATION."""
    parallel   = find_declination_aspects({"Sun": 10.0, "Moon": 10.3}, orb=1.0)
    contra     = find_declination_aspects({"Sun": 10.0, "Mars": -10.3}, orb=1.0)
    assert parallel and parallel[0].classification.family is AspectFamily.DECLINATION
    assert contra   and contra[0].classification.family   is AspectFamily.DECLINATION


def test_classification_is_deterministic_across_calls() -> None:
    """Calling the engine twice with identical input yields identical classifications."""
    positions = {"Sun": 0.0, "Moon": 120.0}
    first  = find_aspects(positions, include_minor=False)
    second = find_aspects(positions, include_minor=False)
    assert first[0].classification == second[0].classification


def test_aspects_between_carries_classification() -> None:
    """aspects_between attaches a non-None classification to every result."""
    results = aspects_between("Sun", 0.0, "Moon", 90.0, tier=0)
    assert results
    assert results[0].classification is not None
    assert results[0].classification.domain is AspectDomain.ZODIACAL
    assert results[0].classification.tier   is AspectTier.MAJOR
    assert results[0].classification.family is AspectFamily.SQUARE


def test_aspects_to_point_carries_classification() -> None:
    """aspects_to_point attaches a non-None classification to every result."""
    results = aspects_to_point(
        120.0, {"Sun": 0.0}, point_name="MC", include_minor=False
    )
    assert results
    assert results[0].classification is not None
    assert results[0].classification.domain is AspectDomain.ZODIACAL
    assert results[0].classification.tier   is AspectTier.MAJOR
    assert results[0].classification.family is AspectFamily.TRINE


def test_classification_does_not_change_detection_outcome() -> None:
    """The same aspects are admitted regardless of the classification layer."""
    positions = {"Sun": 0.0, "Moon": 121.0, "Mars": 61.0}
    results = find_aspects(positions, include_minor=False)
    names = [r.aspect for r in results]
    assert "Trine" in names
    assert "Sextile" in names
    for r in results:
        assert r.classification is not None


# ---------------------------------------------------------------------------
# Phase 3 — inspectability and invariant hardening
# ---------------------------------------------------------------------------

def test_orb_surplus_is_non_negative_for_all_admitted_aspects() -> None:
    """orb_surplus >= 0 for every admitted aspect (admission gate invariant)."""
    results = find_aspects(
        {"Sun": 0.0, "Moon": 58.0, "Mars": 121.0, "Venus": 91.0},
        include_minor=True,
    )
    assert results
    for a in results:
        assert a.orb_surplus >= 0.0, (
            f"orb_surplus negative for {a}: orb={a.orb} allowed={a.allowed_orb}"
        )


def test_orb_surplus_equals_allowed_orb_minus_orb() -> None:
    """orb_surplus is exactly allowed_orb - orb (derived, no hidden logic)."""
    results = find_aspects(
        {"Sun": 0.0, "Moon": 119.0},
        include_minor=False,
    )
    assert results
    a = results[0]
    assert a.orb_surplus == pytest.approx(a.allowed_orb - a.orb)


def test_is_major_consistent_with_classification_tier() -> None:
    """is_major is True iff classification.tier is AspectTier.MAJOR."""
    results = find_aspects(
        {"Sun": 0.0, "Moon": 120.0, "Mars": 72.0},
        include_minor=True,
    )
    assert results
    for a in results:
        assert a.is_major == (a.classification.tier is AspectTier.MAJOR), (
            f"is_major mismatch for {a.aspect}"
        )


def test_is_minor_is_complement_of_is_major() -> None:
    """is_minor == not is_major for every admitted aspect."""
    results = find_aspects(
        {"Sun": 0.0, "Moon": 90.0, "Mars": 72.0},
        include_minor=True,
    )
    assert results
    for a in results:
        assert a.is_minor == (not a.is_major)


def test_is_zodiacal_always_true_for_aspect_data() -> None:
    """is_zodiacal is always True for AspectData (ecliptic domain)."""
    results = find_aspects(
        {"Sun": 0.0, "Moon": 60.0},
        include_minor=False,
    )
    assert results
    for a in results:
        assert a.is_zodiacal is True


def test_is_applying_and_is_separating_are_mutually_exclusive() -> None:
    """is_applying and is_separating cannot both be True simultaneously."""
    applying_result = aspects_between(
        "Sun", 359.0, "Moon", 1.0, tier=0,
        speed_a=2.0, speed_b=1.0,
    )
    separating_result = aspects_between(
        "Sun", 359.0, "Moon", 1.0, tier=0,
        speed_a=1.0, speed_b=2.0,
    )
    unknown_result = aspects_between(
        "Sun", 0.0, "Moon", 60.0, tier=0,
    )
    assert applying_result[0].is_applying   is True
    assert applying_result[0].is_separating is False
    assert separating_result[0].is_applying   is False
    assert separating_result[0].is_separating is True
    assert unknown_result[0].is_applying   is False
    assert unknown_result[0].is_separating is False


def test_is_applying_false_when_applying_is_none() -> None:
    """is_applying returns False (not None) when applying is None."""
    results = aspects_between("Sun", 0.0, "Moon", 60.0, tier=0)
    assert results
    assert results[0].applying is None
    assert results[0].is_applying is False


def test_is_separating_false_when_applying_is_none() -> None:
    """is_separating returns False (not None) when applying is None."""
    results = aspects_between("Sun", 0.0, "Moon", 60.0, tier=0)
    assert results
    assert results[0].applying is None
    assert results[0].is_separating is False


def test_declination_is_parallel_and_is_contra_parallel_are_mutually_exclusive() -> None:
    """is_parallel and is_contra_parallel cannot both be True simultaneously."""
    par   = find_declination_aspects({"Sun": 10.0, "Moon": 10.3}, orb=1.0)
    contra = find_declination_aspects({"Sun": 10.0, "Mars": -10.3}, orb=1.0)
    assert par[0].is_parallel          is True
    assert par[0].is_contra_parallel   is False
    assert contra[0].is_parallel       is False
    assert contra[0].is_contra_parallel is True


def test_declination_orb_surplus_is_non_negative() -> None:
    """orb_surplus >= 0 for every admitted DeclinationAspect."""
    results = find_declination_aspects(
        {"Sun": 10.0, "Moon": 10.5, "Mars": -10.2},
        orb=1.0,
    )
    assert results
    for a in results:
        assert a.orb_surplus >= 0.0
        assert a.orb_surplus == pytest.approx(a.allowed_orb - a.orb)


def test_properties_produce_no_state_change() -> None:
    """Calling properties twice returns the same value (pure derivation)."""
    results = find_aspects(
        {"Sun": 0.0, "Moon": 120.0},
        include_minor=False,
    )
    a = results[0]
    assert a.is_major == a.is_major
    assert a.is_minor == a.is_minor
    assert a.is_zodiacal == a.is_zodiacal
    assert a.is_applying == a.is_applying
    assert a.is_separating == a.is_separating
    assert a.orb_surplus == a.orb_surplus


def test_all_admitted_aspects_have_complete_classification() -> None:
    """Every result from find_aspects has non-None classification with all three fields set."""
    results = find_aspects(
        {"Sun": 0.0, "Moon": 60.0, "Mars": 90.0, "Venus": 120.0,
         "Jupiter": 180.0, "Saturn": 72.0},
        include_minor=True,
    )
    assert results
    for a in results:
        assert a.classification is not None
        assert isinstance(a.classification.domain, AspectDomain)
        assert isinstance(a.classification.tier, AspectTier)
        assert isinstance(a.classification.family, AspectFamily)


# ---------------------------------------------------------------------------
# Phase 4 — policy surface tests
# ---------------------------------------------------------------------------

def test_default_policy_matches_find_aspects_defaults() -> None:
    """AspectPolicy() reproduces find_aspects default behaviour exactly."""
    positions = {"Sun": 0.0, "Moon": 60.0, "Mars": 72.0, "Venus": 121.0}
    without_policy = find_aspects(positions)
    with_policy    = find_aspects(positions, policy=DEFAULT_POLICY)
    assert [(a.aspect, a.orb) for a in without_policy] == [
        (a.aspect, a.orb) for a in with_policy
    ]


def test_default_policy_matches_aspects_between_all_tiers() -> None:
    """DEFAULT_POLICY via policy= in aspects_between uses include_minor=True (major+common_minor)."""
    with_p = aspects_between("Sun", 0.0, "Moon", 36.0, policy=DEFAULT_POLICY)
    assert with_p == [], "Decile (36°) is extended-minor; DEFAULT_POLICY excludes it"

    r_sextile = aspects_between("Sun", 0.0, "Moon", 60.0, policy=DEFAULT_POLICY)
    assert r_sextile and r_sextile[0].aspect == "Sextile", "Major aspect should be admitted"


def test_default_policy_matches_aspects_to_point_defaults() -> None:
    """DEFAULT_POLICY via policy= reproduces aspects_to_point default behaviour."""
    without = aspects_to_point(120.0, {"Sun": 119.0, "Moon": 0.0}, include_minor=True)
    with_p  = aspects_to_point(120.0, {"Sun": 119.0, "Moon": 0.0}, policy=DEFAULT_POLICY)
    assert [(a.aspect, a.orb) for a in without] == [
        (a.aspect, a.orb) for a in with_p
    ]


def test_default_policy_matches_find_declination_aspects_defaults() -> None:
    """DEFAULT_POLICY via policy= reproduces find_declination_aspects default behaviour."""
    without = find_declination_aspects({"Sun": 10.0, "Moon": 10.5})
    with_p  = find_declination_aspects({"Sun": 10.0, "Moon": 10.5}, policy=DEFAULT_POLICY)
    assert [(a.aspect, a.orb) for a in without] == [
        (a.aspect, a.orb) for a in with_p
    ]


def test_policy_major_only_excludes_minor_aspects() -> None:
    """AspectPolicy(tier=0) admits only the five Ptolemaic major aspects."""
    major_policy = AspectPolicy(tier=0)
    positions = {"Sun": 0.0, "Moon": 150.0}
    results = find_aspects(positions, policy=major_policy)
    assert results == [], "Quincunx (150°) is not a major aspect"

    positions2 = {"Sun": 0.0, "Moon": 120.0}
    results2 = find_aspects(positions2, policy=major_policy)
    assert results2 and results2[0].is_major


def test_policy_tight_orb_factor_reduces_admissions() -> None:
    """AspectPolicy(orb_factor=0.5) excludes aspects that the default orb admits."""
    positions = {"Sun": 0.0, "Moon": 56.0}
    loose = find_aspects(positions, policy=AspectPolicy(orb_factor=1.0, include_minor=False))
    tight = find_aspects(positions, policy=AspectPolicy(orb_factor=0.5, include_minor=False))
    assert loose, "expected Sextile at orb_factor=1.0"
    assert tight == [], "orb=4° should exceed allowed_orb=2.5° with orb_factor=0.5"


def test_policy_custom_orbs_override_orb_factor() -> None:
    """AspectPolicy(orbs={60.0: 6.0}, orb_factor=0.1) uses the custom table."""
    policy = AspectPolicy(orbs={60.0: 6.0}, orb_factor=0.1, include_minor=False)
    results = find_aspects({"Sun": 0.0, "Moon": 66.0}, policy=policy)
    assert len(results) == 1
    assert results[0].aspect == "Sextile"
    assert results[0].allowed_orb == pytest.approx(6.0)


def test_policy_overrides_individual_parameters_in_find_aspects() -> None:
    """When policy is supplied, it takes precedence over individual parameters."""
    positions = {"Sun": 0.0, "Moon": 150.0}
    major_policy = AspectPolicy(tier=0)
    results = find_aspects(
        positions,
        include_minor=True,
        tier=2,
        policy=major_policy,
    )
    assert results == [], "policy(tier=0) should override the explicit tier=2 argument"


def test_policy_overrides_individual_parameters_in_aspects_between() -> None:
    """When policy is supplied, it takes precedence over the tier kwarg in aspects_between."""
    major_policy = AspectPolicy(tier=0)
    results = aspects_between("Sun", 0.0, "Moon", 150.0, tier=2, policy=major_policy)
    assert results == [], "Quincunx is not major; policy(tier=0) should exclude it"


def test_policy_overrides_individual_parameters_in_aspects_to_point() -> None:
    """When policy is supplied, it takes precedence over individual params in aspects_to_point."""
    major_policy = AspectPolicy(tier=0)
    results = aspects_to_point(
        150.0, {"Sun": 0.0}, include_minor=True, tier=2, policy=major_policy
    )
    assert results == [], "Quincunx at 150° is not major; policy(tier=0) should exclude it"


def test_policy_declination_orb_controls_find_declination_aspects() -> None:
    """AspectPolicy(declination_orb=0.3) narrows the parallel/contra-parallel window."""
    bodies = {"Sun": 10.0, "Moon": 10.5}
    wide   = find_declination_aspects(bodies, policy=AspectPolicy(declination_orb=1.0))
    narrow = find_declination_aspects(bodies, policy=AspectPolicy(declination_orb=0.3))
    assert len(wide)   == 1, "orb=0.5 is within 1.0°"
    assert len(narrow) == 0, "orb=0.5 exceeds 0.3°"


def test_policy_overrides_orb_in_find_declination_aspects() -> None:
    """policy.declination_orb overrides the explicit orb= argument."""
    bodies = {"Sun": 10.0, "Moon": 10.5}
    results = find_declination_aspects(
        bodies, orb=1.0, policy=AspectPolicy(declination_orb=0.3)
    )
    assert results == [], "policy.declination_orb=0.3 should override orb=1.0"


def test_aspect_policy_is_immutable() -> None:
    """AspectPolicy is frozen — attribute assignment raises FrozenInstanceError."""
    policy = AspectPolicy(orb_factor=0.5)
    with pytest.raises(Exception):
        policy.orb_factor = 1.0  # type: ignore[misc]


def test_default_policy_is_singleton_identity() -> None:
    """DEFAULT_POLICY equals a freshly constructed AspectPolicy() by value."""
    assert DEFAULT_POLICY == AspectPolicy()


# ---------------------------------------------------------------------------
# Phase 5 — geometric strength tests
# ---------------------------------------------------------------------------

def test_aspect_strength_exact_aspect_has_exactness_one() -> None:
    """An aspect with orb=0 has exactness=1.0."""
    results = aspects_between("Sun", 0.0, "Moon", 120.0, tier=0)
    assert results and results[0].orb == pytest.approx(0.0)
    s = aspect_strength(results[0])
    assert s.exactness == pytest.approx(1.0)


def test_aspect_strength_boundary_aspect_has_exactness_zero() -> None:
    """An aspect admitted exactly at the boundary (orb == allowed_orb) has exactness=0.0."""
    results = find_aspects({"Sun": 0.0, "Moon": 66.0}, orbs={60.0: 6.0}, include_minor=False)
    assert results and results[0].orb == pytest.approx(6.0)
    assert results[0].allowed_orb == pytest.approx(6.0)
    s = aspect_strength(results[0])
    assert s.exactness == pytest.approx(0.0)


def test_aspect_strength_tighter_orb_yields_higher_exactness() -> None:
    """Monotonic: smaller orb → higher exactness under the same allowed_orb."""
    tight  = find_aspects({"Sun": 0.0, "Moon": 121.0}, include_minor=False)
    loose  = find_aspects({"Sun": 0.0, "Moon": 125.0}, include_minor=False)
    assert tight and tight[0].aspect  == "Trine"
    assert loose and loose[0].aspect  == "Trine"
    assert tight[0].orb < loose[0].orb
    assert aspect_strength(tight[0]).exactness > aspect_strength(loose[0]).exactness


def test_aspect_strength_equal_orb_equal_allowed_orb_yields_equal_exactness() -> None:
    """Same orb and allowed_orb in different vessels produce identical exactness."""
    r1 = find_aspects({"Sun": 0.0, "Moon": 121.0}, include_minor=False)
    r2 = find_aspects({"Mars": 0.0, "Venus": 121.0}, include_minor=False)
    assert r1 and r2
    assert r1[0].orb        == pytest.approx(r2[0].orb)
    assert r1[0].allowed_orb == pytest.approx(r2[0].allowed_orb)
    assert aspect_strength(r1[0]).exactness == pytest.approx(aspect_strength(r2[0]).exactness)


def test_aspect_strength_fields_are_arithmetically_consistent() -> None:
    """surplus == allowed_orb - orb and exactness == 1 - orb/allowed_orb."""
    results = find_aspects(
        {"Sun": 0.0, "Moon": 119.0, "Mars": 58.0},
        include_minor=True,
    )
    assert results
    for a in results:
        s = aspect_strength(a)
        assert s.orb         == pytest.approx(a.orb)
        assert s.allowed_orb == pytest.approx(a.allowed_orb)
        assert s.surplus     == pytest.approx(a.allowed_orb - a.orb)
        assert s.exactness   == pytest.approx(1.0 - a.orb / a.allowed_orb)


def test_aspect_strength_exactness_in_unit_interval() -> None:
    """exactness is always in [0.0, 1.0] for every admitted aspect."""
    results = find_aspects(
        {"Sun": 0.0, "Moon": 58.0, "Mars": 121.0, "Venus": 91.0, "Jupiter": 180.0},
        include_minor=True,
    )
    assert results
    for a in results:
        s = aspect_strength(a)
        assert 0.0 <= s.exactness <= 1.0 + 1e-9, (
            f"exactness out of range for {a}: {s.exactness}"
        )


def test_aspect_strength_works_on_declination_aspect() -> None:
    """aspect_strength accepts DeclinationAspect and returns correct components."""
    results = find_declination_aspects({"Sun": 10.0, "Moon": 10.5}, orb=1.0)
    assert results
    a = results[0]
    s = aspect_strength(a)
    assert s.orb         == pytest.approx(a.orb)
    assert s.allowed_orb == pytest.approx(a.allowed_orb)
    assert s.surplus     == pytest.approx(a.allowed_orb - a.orb)
    assert s.exactness   == pytest.approx(1.0 - a.orb / a.allowed_orb)


def test_aspect_strength_declination_tighter_orb_higher_exactness() -> None:
    """Monotonic property holds for DeclinationAspect too."""
    close  = find_declination_aspects({"Sun": 10.0, "Moon": 10.1}, orb=1.0)
    far    = find_declination_aspects({"Sun": 10.0, "Mars": 10.8}, orb=1.0)
    assert close and far
    assert aspect_strength(close[0]).exactness > aspect_strength(far[0]).exactness


def test_aspect_strength_is_immutable() -> None:
    """AspectStrength is frozen — assignment raises an exception."""
    results = find_aspects({"Sun": 0.0, "Moon": 120.0}, include_minor=False)
    s = aspect_strength(results[0])
    with pytest.raises(Exception):
        s.exactness = 0.5  # type: ignore[misc]


def test_aspect_strength_does_not_alter_detection_outcome() -> None:
    """Calling aspect_strength does not change any field on the source vessel."""
    results = find_aspects({"Sun": 0.0, "Moon": 121.0}, include_minor=False)
    a = results[0]
    orb_before = a.orb
    allowed_before = a.allowed_orb
    _ = aspect_strength(a)
    assert a.orb         == pytest.approx(orb_before)
    assert a.allowed_orb == pytest.approx(allowed_before)


def test_aspect_strength_surplus_non_negative_for_all_admitted() -> None:
    """surplus >= 0 for every admitted aspect (mirrors orb_surplus invariant)."""
    results = find_aspects(
        {"Sun": 0.0, "Moon": 58.0, "Mars": 121.0, "Venus": 150.0},
        include_minor=True,
    )
    assert results
    for a in results:
        s = aspect_strength(a)
        assert s.surplus >= 0.0


# ---------------------------------------------------------------------------
# Phase 6 — temporal-state tests
# ---------------------------------------------------------------------------

def test_motion_state_applying_when_applying_true_and_not_stationary() -> None:
    """APPLYING when applying=True and stationary=False."""
    results = aspects_between(
        "Sun", 359.0, "Moon", 1.0, tier=0,
        speed_a=2.0, speed_b=1.0,
    )
    assert results and results[0].applying is True
    assert results[0].stationary is False
    assert aspect_motion_state(results[0]) is MotionState.APPLYING


def test_motion_state_separating_when_applying_false_and_not_stationary() -> None:
    """SEPARATING when applying=False and stationary=False."""
    results = aspects_between(
        "Sun", 359.0, "Moon", 1.0, tier=0,
        speed_a=1.0, speed_b=2.0,
    )
    assert results and results[0].applying is False
    assert results[0].stationary is False
    assert aspect_motion_state(results[0]) is MotionState.SEPARATING


def test_motion_state_stationary_when_stationary_flag_is_true() -> None:
    """STATIONARY when stationary=True regardless of applying value."""
    results = aspects_between(
        "Sun", 0.0, "Moon", 60.0, tier=0,
        speed_a=0.004, speed_b=1.0,
    )
    assert results and results[0].stationary is True
    assert aspect_motion_state(results[0]) is MotionState.STATIONARY


def test_motion_state_stationary_overrides_applying_none() -> None:
    """STATIONARY takes precedence; applying is None when stationary is True."""
    results = aspects_between(
        "Sun", 0.0, "Moon", 60.0, tier=0,
        speed_a=0.004, speed_b=1.0,
    )
    assert results
    a = results[0]
    assert a.stationary is True
    assert a.applying is None
    assert aspect_motion_state(a) is MotionState.STATIONARY


def test_motion_state_indeterminate_when_no_speeds_supplied() -> None:
    """INDETERMINATE when speeds were not passed to the detection function."""
    results = aspects_between("Sun", 0.0, "Moon", 60.0, tier=0)
    assert results
    a = results[0]
    assert a.applying is None
    assert a.stationary is False
    assert aspect_motion_state(a) is MotionState.INDETERMINATE


def test_motion_state_indeterminate_when_partial_speeds() -> None:
    """INDETERMINATE when only one body's speed is supplied."""
    results = aspects_between(
        "Sun", 0.0, "Moon", 60.0, tier=0,
        speed_a=1.0,
    )
    assert results
    assert results[0].applying is None
    assert aspect_motion_state(results[0]) is MotionState.INDETERMINATE


def test_motion_state_none_for_declination_aspect() -> None:
    """MotionState.NONE for DeclinationAspect — no motion data available."""
    results = find_declination_aspects({"Sun": 10.0, "Moon": 10.4}, orb=1.0)
    assert results
    assert aspect_motion_state(results[0]) is MotionState.NONE


def test_motion_state_none_for_manually_constructed_declination_aspect() -> None:
    """MotionState.NONE for a DeclinationAspect regardless of field values."""
    d = DeclinationAspect(
        body1="Sun", body2="Moon",
        aspect="Parallel",
        dec1=10.0, dec2=10.2,
        orb=0.2, allowed_orb=1.0,
    )
    assert aspect_motion_state(d) is MotionState.NONE


def test_motion_state_applying_from_find_aspects_with_speeds() -> None:
    """aspect_motion_state works correctly on find_aspects results with speeds."""
    positions = {"Sun": 359.0, "Moon": 1.0}
    speeds    = {"Sun": 2.0,   "Moon": 1.0}
    results = find_aspects(positions, speeds=speeds, include_minor=False)
    assert results
    assert aspect_motion_state(results[0]) is MotionState.APPLYING


def test_motion_state_indeterminate_from_aspects_to_point() -> None:
    """aspects_to_point never supplies speeds, so every result is INDETERMINATE."""
    results = aspects_to_point(120.0, {"Sun": 119.0}, include_minor=False)
    assert results
    assert results[0].applying is None
    assert aspect_motion_state(results[0]) is MotionState.INDETERMINATE


def test_motion_state_exhaustive_coverage() -> None:
    """Every MotionState value is reachable and maps to exactly the right vessel state."""
    applying_r = aspects_between(
        "Sun", 359.0, "Moon", 1.0, tier=0, speed_a=2.0, speed_b=1.0,
    )
    separating_r = aspects_between(
        "Sun", 359.0, "Moon", 1.0, tier=0, speed_a=1.0, speed_b=2.0,
    )
    stationary_r = aspects_between(
        "Sun", 0.0, "Moon", 60.0, tier=0, speed_a=0.004, speed_b=1.0,
    )
    indeterminate_r = aspects_between("Sun", 0.0, "Moon", 60.0, tier=0)
    declination_r   = find_declination_aspects({"Sun": 10.0, "Moon": 10.3}, orb=1.0)

    assert aspect_motion_state(applying_r[0])     is MotionState.APPLYING
    assert aspect_motion_state(separating_r[0])   is MotionState.SEPARATING
    assert aspect_motion_state(stationary_r[0])   is MotionState.STATIONARY
    assert aspect_motion_state(indeterminate_r[0]) is MotionState.INDETERMINATE
    assert aspect_motion_state(declination_r[0])  is MotionState.NONE


def test_motion_state_does_not_alter_vessel_fields() -> None:
    """Calling aspect_motion_state does not mutate the source vessel."""
    results = aspects_between(
        "Sun", 359.0, "Moon", 1.0, tier=0, speed_a=2.0, speed_b=1.0,
    )
    a = results[0]
    applying_before    = a.applying
    stationary_before  = a.stationary
    _ = aspect_motion_state(a)
    assert a.applying   == applying_before
    assert a.stationary == stationary_before


def test_motion_state_is_deterministic_across_calls() -> None:
    """Same vessel produces the same MotionState on repeated calls."""
    results = aspects_between(
        "Sun", 359.0, "Moon", 1.0, tier=0, speed_a=2.0, speed_b=1.0,
    )
    a = results[0]
    assert aspect_motion_state(a) is aspect_motion_state(a)


def test_motion_state_detection_semantics_unchanged() -> None:
    """Detection results are identical with or without calling aspect_motion_state."""
    positions = {"Sun": 359.0, "Moon": 1.0, "Mars": 120.0}
    speeds    = {"Sun": 1.0, "Moon": 13.0, "Mars": 0.5}
    results = find_aspects(positions, speeds=speeds, include_minor=False)
    aspects_names = [r.aspect for r in results]
    orbs          = [r.orb    for r in results]
    _ = [aspect_motion_state(r) for r in results]
    assert [r.aspect for r in results] == aspects_names
    assert [r.orb    for r in results] == orbs


# ---------------------------------------------------------------------------
# Phase 7 — canonical configuration tests
# ---------------------------------------------------------------------------

def test_canonical_aspects_has_exactly_24_members() -> None:
    """CANONICAL_ASPECTS declares exactly 24 aspect names."""
    assert len(CANONICAL_ASPECTS) == 24


def test_canonical_aspects_contains_all_five_major_aspects() -> None:
    """All five Ptolemaic major aspects are present in CANONICAL_ASPECTS."""
    for name in ("Conjunction", "Sextile", "Square", "Trine", "Opposition"):
        assert name in CANONICAL_ASPECTS, f"{name} missing from CANONICAL_ASPECTS"


def test_canonical_aspects_contains_all_six_common_minor_aspects() -> None:
    """All six common-minor aspects are present in CANONICAL_ASPECTS."""
    for name in ("Semisextile", "Semisquare", "Sesquiquadrate", "Quincunx",
                 "Quintile", "Biquintile"):
        assert name in CANONICAL_ASPECTS, f"{name} missing from CANONICAL_ASPECTS"


def test_canonical_aspects_contains_all_eleven_extended_minor_aspects() -> None:
    """All eleven extended-minor aspects are present in CANONICAL_ASPECTS."""
    for name in ("Septile", "Biseptile", "Triseptile",
                 "Novile", "Binovile", "Quadnovile",
                 "Decile", "Tredecile",
                 "Undecile", "Quindecile", "Vigintile"):
        assert name in CANONICAL_ASPECTS, f"{name} missing from CANONICAL_ASPECTS"


def test_canonical_aspects_contains_both_declination_aspects() -> None:
    """Both declination aspect names are present in CANONICAL_ASPECTS."""
    assert "Parallel" in CANONICAL_ASPECTS
    assert "Contra-Parallel" in CANONICAL_ASPECTS


def test_canonical_aspects_has_no_duplicates() -> None:
    """CANONICAL_ASPECTS contains no duplicate names."""
    assert len(CANONICAL_ASPECTS) == len(set(CANONICAL_ASPECTS))


def test_canonical_aspects_is_immutable() -> None:
    """CANONICAL_ASPECTS is a tuple (immutable)."""
    assert isinstance(CANONICAL_ASPECTS, tuple)


# --- Detection round-trip for each extended-minor aspect -------------------
# These tests prove that every extended-minor aspect in the canonical set
# is reachable through the detection engine with exact-angle input.

def test_canonical_detection_biseptile() -> None:
    """Biseptile (720/7°) is detected at exact angle."""
    results = aspects_between("Sun", 0.0, "Moon", 720 / 7, tier=2)
    bisept = [r for r in results if r.aspect == "Biseptile"]
    assert bisept, "Biseptile not detected at exact angle"
    assert bisept[0].orb == pytest.approx(0.0, abs=1e-9)
    assert bisept[0].classification.family is AspectFamily.SEPTILE


def test_canonical_detection_triseptile() -> None:
    """Triseptile (1080/7°) is detected at exact angle."""
    results = aspects_between("Sun", 0.0, "Moon", 1080 / 7, tier=2)
    trisept = [r for r in results if r.aspect == "Triseptile"]
    assert trisept, "Triseptile not detected at exact angle"
    assert trisept[0].orb == pytest.approx(0.0, abs=1e-9)
    assert trisept[0].classification.family is AspectFamily.SEPTILE


def test_canonical_detection_binovile() -> None:
    """Binovile (80°) is detected at exact angle."""
    results = aspects_between("Sun", 0.0, "Moon", 80.0, tier=2)
    binovile = [r for r in results if r.aspect == "Binovile"]
    assert binovile, "Binovile not detected at exact angle"
    assert binovile[0].orb == pytest.approx(0.0)
    assert binovile[0].classification.family is AspectFamily.NOVILE


def test_canonical_detection_quadnovile() -> None:
    """Quadnovile (160°) is detected at exact angle."""
    results = aspects_between("Sun", 0.0, "Moon", 160.0, tier=2)
    quadnovile = [r for r in results if r.aspect == "Quadnovile"]
    assert quadnovile, "Quadnovile not detected at exact angle"
    assert quadnovile[0].orb == pytest.approx(0.0)
    assert quadnovile[0].classification.family is AspectFamily.NOVILE


def test_canonical_detection_undecile() -> None:
    """Undecile (360/11°) is detected at exact angle."""
    results = aspects_between("Sun", 0.0, "Moon", 360 / 11, tier=2)
    undecile = [r for r in results if r.aspect == "Undecile"]
    assert undecile, "Undecile not detected at exact angle"
    assert undecile[0].orb == pytest.approx(0.0, abs=1e-9)
    assert undecile[0].classification.family is AspectFamily.UNDECILE


def test_canonical_detection_quindecile() -> None:
    """Quindecile (24°) is detected at exact angle."""
    results = aspects_between("Sun", 0.0, "Moon", 24.0, tier=2)
    quindecile = [r for r in results if r.aspect == "Quindecile"]
    assert quindecile, "Quindecile not detected at exact angle"
    assert quindecile[0].orb == pytest.approx(0.0)
    assert quindecile[0].classification.family is AspectFamily.QUINDECILE


def test_canonical_detection_vigintile() -> None:
    """Vigintile (18°) is detected at exact angle."""
    results = aspects_between("Sun", 0.0, "Moon", 18.0, tier=2)
    vigintile = [r for r in results if r.aspect == "Vigintile"]
    assert vigintile, "Vigintile not detected at exact angle"
    assert vigintile[0].orb == pytest.approx(0.0)
    assert vigintile[0].classification.family is AspectFamily.VIGINTILE


# --- All 22 zodiacal aspects detectable via Aspect.ALL (tier=2) ------------

def test_all_22_zodiacal_canonical_aspects_are_detectable() -> None:
    """Every zodiacal name in CANONICAL_ASPECTS is detectable via aspects_between(tier=2)."""
    from moira.constants import Aspect as _Aspect
    angle_by_name = {adef.name: adef.angle for adef in _Aspect.ALL}
    zodiacal_names = [n for n in CANONICAL_ASPECTS
                      if n not in ("Parallel", "Contra-Parallel")]
    assert len(zodiacal_names) == 22
    for name in zodiacal_names:
        angle = angle_by_name[name]
        results = aspects_between("Sun", 0.0, "Moon", angle, tier=2)
        match = [r for r in results if r.aspect == name]
        assert match, f"{name} not detected at exact angle {angle:.4f}°"
        assert match[0].orb == pytest.approx(0.0, abs=1e-9), (
            f"{name}: expected orb≈0 at exact angle, got {match[0].orb}"
        )


def test_all_canonical_zodiacal_aspects_carry_zodiacal_domain() -> None:
    """Every detected zodiacal canonical aspect has domain=ZODIACAL."""
    from moira.constants import Aspect as _Aspect
    angle_by_name = {adef.name: adef.angle for adef in _Aspect.ALL}
    for name in CANONICAL_ASPECTS:
        if name in ("Parallel", "Contra-Parallel"):
            continue
        angle = angle_by_name[name]
        results = aspects_between("Sun", 0.0, "Moon", angle, tier=2)
        match = [r for r in results if r.aspect == name]
        assert match and match[0].classification.domain is AspectDomain.ZODIACAL, (
            f"{name}: expected ZODIACAL domain"
        )


def test_both_declination_canonical_aspects_are_detectable() -> None:
    """Parallel and Contra-Parallel are detectable via find_declination_aspects."""
    parallel = find_declination_aspects({"Sun": 10.0, "Moon": 10.0}, orb=1.0)
    assert any(a.aspect == "Parallel" for a in parallel), "Parallel not detected"

    contra = find_declination_aspects({"Sun": 10.0, "Moon": -10.0}, orb=1.0)
    assert any(a.aspect == "Contra-Parallel" for a in contra), "Contra-Parallel not detected"


# --- Near-miss rejection tests -------------------------------------------

def test_extended_minor_near_miss_biseptile_rejected_outside_orb() -> None:
    """A separation 2° beyond Biseptile's orb (1.5°) is not admitted."""
    angle = 720 / 7
    results = aspects_between("Sun", 0.0, "Moon", angle + 2.0, tier=2)
    bisept = [r for r in results if r.aspect == "Biseptile"]
    assert not bisept, "Biseptile should not be admitted 2° beyond its orb"


def test_extended_minor_near_miss_vigintile_rejected_outside_orb() -> None:
    """A separation 2° beyond Vigintile's orb (1.0°) is not admitted."""
    results = aspects_between("Sun", 0.0, "Moon", 18.0 + 2.0, tier=2)
    vig = [r for r in results if r.aspect == "Vigintile"]
    assert not vig, "Vigintile should not be admitted 2° beyond its orb"


def test_near_miss_parallel_rejected_outside_declination_orb() -> None:
    """A declination difference of 1.5° is rejected when orb=1.0°."""
    results = find_declination_aspects({"Sun": 10.0, "Moon": 11.5}, orb=1.0)
    assert results == [], "Parallel should not be admitted at 1.5° with orb=1.0°"


# --- Determinism tests ---------------------------------------------------

def test_canonical_detection_is_deterministic_across_calls() -> None:
    """Repeated calls with identical input yield identical canonical detection results."""
    from moira.constants import Aspect as _Aspect
    angle_by_name = {adef.name: adef.angle for adef in _Aspect.ALL}
    positions = {
        "Sun":   0.0,
        "Moon":  angle_by_name["Trine"],
        "Mars":  angle_by_name["Quintile"],
        "Venus": angle_by_name["Biseptile"],
    }
    first  = find_aspects(positions, tier=2, include_minor=True)
    second = find_aspects(positions, tier=2, include_minor=True)
    assert [(a.aspect, a.orb) for a in first] == [(a.aspect, a.orb) for a in second]


def test_canonical_aspects_detection_does_not_alter_pairwise_semantics() -> None:
    """Pairwise detection results (names, orbs) are unchanged by CANONICAL_ASPECTS import."""
    results = find_aspects({"Sun": 0.0, "Moon": 120.0}, include_minor=False)
    assert len(results) == 1
    assert results[0].aspect == "Trine"
    assert results[0].orb == pytest.approx(0.0)


# ===========================================================================
# Phase 8 — Multi-body pattern detection
# ===========================================================================

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_aspect(b1: str, b2: str, name: str, angle: float, symbol: str = "?") -> AspectData:
    return AspectData(
        body1=b1,
        body2=b2,
        aspect=name,
        symbol=symbol,
        angle=angle,
        separation=angle,
        orb=0.0,
        allowed_orb=8.0,
        applying=None,
        stationary=False,
    )


def _conj(b1: str, b2: str) -> AspectData:
    return _make_aspect(b1, b2, "Conjunction", 0.0, "☌")


def _opp(b1: str, b2: str) -> AspectData:
    return _make_aspect(b1, b2, "Opposition", 180.0, "☍")


def _sq(b1: str, b2: str) -> AspectData:
    return _make_aspect(b1, b2, "Square", 90.0, "□")


def _trine(b1: str, b2: str) -> AspectData:
    return _make_aspect(b1, b2, "Trine", 120.0, "△")


def _sext(b1: str, b2: str) -> AspectData:
    return _make_aspect(b1, b2, "Sextile", 60.0, "⚹")


def _qcx(b1: str, b2: str) -> AspectData:
    return _make_aspect(b1, b2, "Quincunx", 150.0, "⚻")


# ---------------------------------------------------------------------------
# find_patterns — empty input
# ---------------------------------------------------------------------------

def test_find_patterns_empty_list_returns_empty() -> None:
    assert find_patterns([]) == []


# ---------------------------------------------------------------------------
# Stellium
# ---------------------------------------------------------------------------

def test_find_patterns_stellium_3_bodies() -> None:
    """Three bodies in mutual Conjunction → one STELLIUM with 3 bodies."""
    aspects = [_conj("Sun", "Moon"), _conj("Sun", "Mars"), _conj("Moon", "Mars")]
    patterns = find_patterns(aspects)
    stellia = [p for p in patterns if p.kind == AspectPatternKind.STELLIUM]
    assert len(stellia) == 1
    assert stellia[0].bodies == frozenset({"Sun", "Moon", "Mars"})
    assert len(stellia[0].aspects) == 3


def test_find_patterns_stellium_4_bodies() -> None:
    """Four bodies in mutual Conjunction → one STELLIUM with 4 bodies, 6 conjunction edges."""
    bodies = ["Sun", "Moon", "Mars", "Venus"]
    from itertools import combinations
    aspects = [_conj(a, b) for a, b in combinations(bodies, 2)]
    patterns = find_patterns(aspects)
    stellia = [p for p in patterns if p.kind == AspectPatternKind.STELLIUM]
    assert len(stellia) == 1
    assert stellia[0].bodies == frozenset(bodies)
    assert len(stellia[0].aspects) == 6


def test_find_patterns_stellium_requires_3_bodies_minimum() -> None:
    """Two bodies in Conjunction alone do not form a Stellium."""
    aspects = [_conj("Sun", "Moon")]
    patterns = find_patterns(aspects)
    assert not any(p.kind == AspectPatternKind.STELLIUM for p in patterns)


def test_find_patterns_stellium_requires_mutual_conjunction() -> None:
    """Three bodies where one pair is not conjoined do not form a Stellium."""
    aspects = [_conj("Sun", "Moon"), _conj("Sun", "Mars")]
    patterns = find_patterns(aspects)
    assert not any(p.kind == AspectPatternKind.STELLIUM for p in patterns)


# ---------------------------------------------------------------------------
# T-Square
# ---------------------------------------------------------------------------

def test_find_patterns_t_square_detected() -> None:
    """A opposes B, C squares A and C squares B → T_SQUARE with apex C."""
    aspects = [_opp("Sun", "Moon"), _sq("Sun", "Mars"), _sq("Moon", "Mars")]
    patterns = find_patterns(aspects)
    tsqs = [p for p in patterns if p.kind == AspectPatternKind.T_SQUARE]
    assert len(tsqs) == 1
    assert tsqs[0].bodies == frozenset({"Sun", "Moon", "Mars"})
    assert len(tsqs[0].aspects) == 3


def test_find_patterns_t_square_missing_square_rejected() -> None:
    """Opposition + only one Square does not satisfy T-Square structure."""
    aspects = [_opp("Sun", "Moon"), _sq("Sun", "Mars")]
    patterns = find_patterns(aspects)
    assert not any(p.kind == AspectPatternKind.T_SQUARE for p in patterns)


def test_find_patterns_t_square_missing_opposition_rejected() -> None:
    """Two Squares with no Opposition do not form a T-Square."""
    aspects = [_sq("Sun", "Mars"), _sq("Moon", "Mars")]
    patterns = find_patterns(aspects)
    assert not any(p.kind == AspectPatternKind.T_SQUARE for p in patterns)


# ---------------------------------------------------------------------------
# Grand Trine
# ---------------------------------------------------------------------------

def test_find_patterns_grand_trine_detected() -> None:
    """Three bodies each trining the other two → GRAND_TRINE."""
    aspects = [_trine("Sun", "Moon"), _trine("Moon", "Mars"), _trine("Sun", "Mars")]
    patterns = find_patterns(aspects)
    gts = [p for p in patterns if p.kind == AspectPatternKind.GRAND_TRINE]
    assert len(gts) == 1
    assert gts[0].bodies == frozenset({"Sun", "Moon", "Mars"})
    assert len(gts[0].aspects) == 3


def test_find_patterns_grand_trine_two_trines_rejected() -> None:
    """Only two Trines (third missing) do not form a Grand Trine."""
    aspects = [_trine("Sun", "Moon"), _trine("Moon", "Mars")]
    patterns = find_patterns(aspects)
    assert not any(p.kind == AspectPatternKind.GRAND_TRINE for p in patterns)


# ---------------------------------------------------------------------------
# Grand Cross
# ---------------------------------------------------------------------------

def test_find_patterns_grand_cross_detected() -> None:
    """Four bodies: A–B opp, C–D opp, A–C sq, A–D sq, B–C sq, B–D sq → GRAND_CROSS."""
    aspects = [
        _opp("Sun", "Moon"),
        _opp("Mars", "Venus"),
        _sq("Sun", "Mars"),
        _sq("Sun", "Venus"),
        _sq("Moon", "Mars"),
        _sq("Moon", "Venus"),
    ]
    patterns = find_patterns(aspects)
    gcs = [p for p in patterns if p.kind == AspectPatternKind.GRAND_CROSS]
    assert len(gcs) == 1
    assert gcs[0].bodies == frozenset({"Sun", "Moon", "Mars", "Venus"})
    assert len(gcs[0].aspects) == 6


def test_find_patterns_grand_cross_missing_square_rejected() -> None:
    """Grand Cross structure with one Square removed is not detected."""
    aspects = [
        _opp("Sun", "Moon"),
        _opp("Mars", "Venus"),
        _sq("Sun", "Mars"),
        _sq("Sun", "Venus"),
        _sq("Moon", "Mars"),
    ]
    patterns = find_patterns(aspects)
    assert not any(p.kind == AspectPatternKind.GRAND_CROSS for p in patterns)


# ---------------------------------------------------------------------------
# Yod
# ---------------------------------------------------------------------------

def test_find_patterns_yod_detected() -> None:
    """B–C Sextile, A quincunx B, A quincunx C → YOD with apex A."""
    aspects = [_sext("Moon", "Mars"), _qcx("Sun", "Moon"), _qcx("Sun", "Mars")]
    patterns = find_patterns(aspects)
    yods = [p for p in patterns if p.kind == AspectPatternKind.YOD]
    assert len(yods) == 1
    assert yods[0].bodies == frozenset({"Sun", "Moon", "Mars"})
    assert len(yods[0].aspects) == 3


def test_find_patterns_yod_missing_sextile_rejected() -> None:
    """Two Quincunxes sharing an apex but no Sextile at the base do not form a Yod."""
    aspects = [_qcx("Sun", "Moon"), _qcx("Sun", "Mars")]
    patterns = find_patterns(aspects)
    assert not any(p.kind == AspectPatternKind.YOD for p in patterns)


def test_find_patterns_yod_missing_quincunx_rejected() -> None:
    """Sextile base + only one Quincunx do not form a Yod."""
    aspects = [_sext("Moon", "Mars"), _qcx("Sun", "Moon")]
    patterns = find_patterns(aspects)
    assert not any(p.kind == AspectPatternKind.YOD for p in patterns)


# ---------------------------------------------------------------------------
# Grand Cross also contains two T-Squares — both reported independently
# ---------------------------------------------------------------------------

def test_find_patterns_grand_cross_also_yields_t_squares() -> None:
    """A Grand Cross contains four embedded T-Squares; all should be reported."""
    aspects = [
        _opp("Sun", "Moon"),
        _opp("Mars", "Venus"),
        _sq("Sun", "Mars"),
        _sq("Sun", "Venus"),
        _sq("Moon", "Mars"),
        _sq("Moon", "Venus"),
    ]
    patterns = find_patterns(aspects)
    assert any(p.kind == AspectPatternKind.GRAND_CROSS for p in patterns)
    tsqs = [p for p in patterns if p.kind == AspectPatternKind.T_SQUARE]
    assert len(tsqs) == 4


# ---------------------------------------------------------------------------
# Determinism and no-mutation
# ---------------------------------------------------------------------------

def test_find_patterns_is_deterministic() -> None:
    """Repeated calls with identical input return identical output."""
    aspects = [_conj("Sun", "Moon"), _conj("Sun", "Mars"), _conj("Moon", "Mars")]
    first  = find_patterns(aspects)
    second = find_patterns(aspects)
    assert [(p.kind, p.bodies) for p in first] == [(p.kind, p.bodies) for p in second]


def test_find_patterns_does_not_mutate_input_list() -> None:
    """find_patterns must not alter the supplied aspect list."""
    aspects = [_conj("Sun", "Moon"), _conj("Sun", "Mars"), _conj("Moon", "Mars")]
    original_ids = [id(a) for a in aspects]
    original_len = len(aspects)
    find_patterns(aspects)
    assert len(aspects) == original_len
    assert [id(a) for a in aspects] == original_ids


def test_find_patterns_does_not_alter_pairwise_aspect_fields() -> None:
    """Pairwise aspect field values are unchanged after pattern detection."""
    a = _opp("Sun", "Moon")
    b = _sq("Sun", "Mars")
    c = _sq("Moon", "Mars")
    before = [(x.body1, x.body2, x.aspect, x.orb) for x in (a, b, c)]
    find_patterns([a, b, c])
    after = [(x.body1, x.body2, x.aspect, x.orb) for x in (a, b, c)]
    assert before == after


# ---------------------------------------------------------------------------
# AspectPattern vessel invariants
# ---------------------------------------------------------------------------

def test_aspect_pattern_is_immutable() -> None:
    """AspectPattern is a frozen dataclass and must reject attribute assignment."""
    p = find_patterns([_conj("Sun", "Moon"), _conj("Sun", "Mars"), _conj("Moon", "Mars")])[0]
    with pytest.raises((AttributeError, TypeError)):
        p.kind = AspectPatternKind.YOD  # type: ignore[misc]


def test_aspect_pattern_bodies_is_frozenset() -> None:
    """bodies field must be a frozenset."""
    aspects = [_conj("Sun", "Moon"), _conj("Sun", "Mars"), _conj("Moon", "Mars")]
    p = find_patterns(aspects)[0]
    assert isinstance(p.bodies, frozenset)


def test_aspect_pattern_aspects_is_tuple() -> None:
    """aspects field must be a tuple."""
    aspects = [_conj("Sun", "Moon"), _conj("Sun", "Mars"), _conj("Moon", "Mars")]
    p = find_patterns(aspects)[0]
    assert isinstance(p.aspects, tuple)


def test_aspect_pattern_kind_enum_values() -> None:
    """AspectPatternKind has exactly the five documented string members."""
    members = {m.value for m in AspectPatternKind}
    assert members == {"stellium", "t_square", "grand_trine", "grand_cross", "yod"}


def test_aspect_pattern_all_bodies_appear_in_contributing_aspects() -> None:
    """Every body name in bodies must appear in at least one contributing aspect."""
    aspects = [_trine("Sun", "Moon"), _trine("Moon", "Mars"), _trine("Sun", "Mars")]
    p = find_patterns(aspects)[0]
    bodies_in_aspects: set[str] = set()
    for a in p.aspects:
        bodies_in_aspects.add(a.body1)
        bodies_in_aspects.add(a.body2)
    assert p.bodies <= bodies_in_aspects


# ===========================================================================
# Phase 9 — Pattern hardening and invariant doctrine
# ===========================================================================

# ---------------------------------------------------------------------------
# Determinism: input list order must not affect output
# ---------------------------------------------------------------------------

def test_find_patterns_input_permutation_same_stellium() -> None:
    """Reversing the input list produces the same Stellium body-set and aspects tuple."""
    import itertools as _it
    aspects = [_conj("Sun", "Moon"), _conj("Sun", "Mars"), _conj("Moon", "Mars")]
    ref = find_patterns(aspects)
    for perm in _it.permutations(aspects):
        result = find_patterns(list(perm))
        assert len(result) == len(ref)
        assert result[0].bodies == ref[0].bodies
        assert result[0].aspects == ref[0].aspects


def test_find_patterns_input_permutation_same_t_square() -> None:
    """Any ordering of T-Square input aspects produces the same pattern output."""
    import itertools as _it
    aspects = [_opp("Sun", "Moon"), _sq("Sun", "Mars"), _sq("Moon", "Mars")]
    ref = find_patterns(aspects)
    for perm in _it.permutations(aspects):
        result = find_patterns(list(perm))
        tsqs = [p for p in result if p.kind == AspectPatternKind.T_SQUARE]
        assert len(tsqs) == 1
        assert tsqs[0].bodies == ref[0].bodies
        assert tsqs[0].aspects == ref[0].aspects


def test_find_patterns_input_permutation_same_grand_trine() -> None:
    """Any ordering of Grand Trine input aspects produces the same pattern output."""
    import itertools as _it
    aspects = [_trine("Sun", "Moon"), _trine("Moon", "Mars"), _trine("Sun", "Mars")]
    ref = find_patterns(aspects)
    for perm in _it.permutations(aspects):
        result = find_patterns(list(perm))
        gts = [p for p in result if p.kind == AspectPatternKind.GRAND_TRINE]
        assert len(gts) == 1
        assert gts[0].aspects == ref[0].aspects


def test_find_patterns_input_permutation_same_yod() -> None:
    """Any ordering of Yod input aspects produces the same pattern output."""
    import itertools as _it
    aspects = [_sext("Moon", "Mars"), _qcx("Sun", "Moon"), _qcx("Sun", "Mars")]
    ref = find_patterns(aspects)
    for perm in _it.permutations(aspects):
        result = find_patterns(list(perm))
        yods = [p for p in result if p.kind == AspectPatternKind.YOD]
        assert len(yods) == 1
        assert yods[0].aspects == ref[0].aspects


def test_find_patterns_input_permutation_same_grand_cross() -> None:
    """Any ordering of Grand Cross input aspects produces the same pattern output."""
    import itertools as _it
    aspects = [
        _opp("Sun", "Moon"),
        _opp("Mars", "Venus"),
        _sq("Sun", "Mars"),
        _sq("Sun", "Venus"),
        _sq("Moon", "Mars"),
        _sq("Moon", "Venus"),
    ]
    ref = find_patterns(aspects)
    ref_gc = [p for p in ref if p.kind == AspectPatternKind.GRAND_CROSS]
    assert len(ref_gc) == 1
    for perm in _it.permutations(aspects):
        result = find_patterns(list(perm))
        gcs = [p for p in result if p.kind == AspectPatternKind.GRAND_CROSS]
        assert len(gcs) == 1
        assert gcs[0].aspects == ref_gc[0].aspects


# ---------------------------------------------------------------------------
# Duplicate suppression: no pattern body-set emitted twice
# ---------------------------------------------------------------------------

def test_find_patterns_no_duplicate_stellium_body_sets() -> None:
    """find_patterns never emits two Stellia with the same body-set."""
    from itertools import combinations as _comb
    bodies = ["Sun", "Moon", "Mars", "Venus"]
    aspects = [_conj(a, b) for a, b in _comb(bodies, 2)]
    patterns = find_patterns(aspects)
    stellia = [p for p in patterns if p.kind == AspectPatternKind.STELLIUM]
    body_sets = [p.bodies for p in stellia]
    assert len(body_sets) == len(set(body_sets))


def test_find_patterns_no_duplicate_t_square_body_sets() -> None:
    """find_patterns never emits two T-Squares with the same body-set."""
    aspects = [_opp("Sun", "Moon"), _sq("Sun", "Mars"), _sq("Moon", "Mars")]
    patterns = find_patterns(aspects)
    tsqs = [p for p in patterns if p.kind == AspectPatternKind.T_SQUARE]
    body_sets = [p.bodies for p in tsqs]
    assert len(body_sets) == len(set(body_sets))


def test_find_patterns_no_duplicate_grand_trine_body_sets() -> None:
    """find_patterns never emits two Grand Trines with the same body-set."""
    aspects = [_trine("Sun", "Moon"), _trine("Moon", "Mars"), _trine("Sun", "Mars")]
    patterns = find_patterns(aspects)
    gts = [p for p in patterns if p.kind == AspectPatternKind.GRAND_TRINE]
    body_sets = [p.bodies for p in gts]
    assert len(body_sets) == len(set(body_sets))


def test_find_patterns_no_duplicate_grand_cross_body_sets() -> None:
    """find_patterns never emits two Grand Crosses with the same body-set."""
    aspects = [
        _opp("Sun", "Moon"),
        _opp("Mars", "Venus"),
        _sq("Sun", "Mars"),
        _sq("Sun", "Venus"),
        _sq("Moon", "Mars"),
        _sq("Moon", "Venus"),
    ]
    patterns = find_patterns(aspects)
    gcs = [p for p in patterns if p.kind == AspectPatternKind.GRAND_CROSS]
    body_sets = [p.bodies for p in gcs]
    assert len(body_sets) == len(set(body_sets))


def test_find_patterns_no_duplicate_yod_body_sets() -> None:
    """find_patterns never emits two Yods with the same body-set."""
    aspects = [_sext("Moon", "Mars"), _qcx("Sun", "Moon"), _qcx("Sun", "Mars")]
    patterns = find_patterns(aspects)
    yods = [p for p in patterns if p.kind == AspectPatternKind.YOD]
    body_sets = [p.bodies for p in yods]
    assert len(body_sets) == len(set(body_sets))


# ---------------------------------------------------------------------------
# Contributing aspects are sorted by (body1, body2, aspect)
# ---------------------------------------------------------------------------

def test_find_patterns_stellium_aspects_are_sorted() -> None:
    """Contributing aspects inside a Stellium are sorted by (body1, body2, aspect)."""
    aspects = [_conj("Sun", "Moon"), _conj("Sun", "Mars"), _conj("Moon", "Mars")]
    p = find_patterns(aspects)[0]
    keys = [(a.body1, a.body2, a.aspect) for a in p.aspects]
    assert keys == sorted(keys)


def test_find_patterns_t_square_aspects_are_sorted() -> None:
    """Contributing aspects inside a T-Square are sorted by (body1, body2, aspect)."""
    aspects = [_opp("Sun", "Moon"), _sq("Sun", "Mars"), _sq("Moon", "Mars")]
    p = [x for x in find_patterns(aspects) if x.kind == AspectPatternKind.T_SQUARE][0]
    keys = [(a.body1, a.body2, a.aspect) for a in p.aspects]
    assert keys == sorted(keys)


def test_find_patterns_grand_trine_aspects_are_sorted() -> None:
    """Contributing aspects inside a Grand Trine are sorted by (body1, body2, aspect)."""
    aspects = [_trine("Sun", "Moon"), _trine("Moon", "Mars"), _trine("Sun", "Mars")]
    p = find_patterns(aspects)[0]
    keys = [(a.body1, a.body2, a.aspect) for a in p.aspects]
    assert keys == sorted(keys)


def test_find_patterns_grand_cross_aspects_are_sorted() -> None:
    """Contributing aspects inside a Grand Cross are sorted by (body1, body2, aspect)."""
    aspects = [
        _opp("Sun", "Moon"),
        _opp("Mars", "Venus"),
        _sq("Sun", "Mars"),
        _sq("Sun", "Venus"),
        _sq("Moon", "Mars"),
        _sq("Moon", "Venus"),
    ]
    gcs = [p for p in find_patterns(aspects) if p.kind == AspectPatternKind.GRAND_CROSS]
    assert len(gcs) == 1
    keys = [(a.body1, a.body2, a.aspect) for a in gcs[0].aspects]
    assert keys == sorted(keys)


def test_find_patterns_yod_aspects_are_sorted() -> None:
    """Contributing aspects inside a Yod are sorted by (body1, body2, aspect)."""
    aspects = [_sext("Moon", "Mars"), _qcx("Sun", "Moon"), _qcx("Sun", "Mars")]
    yods = [p for p in find_patterns(aspects) if p.kind == AspectPatternKind.YOD]
    assert len(yods) == 1
    keys = [(a.body1, a.body2, a.aspect) for a in yods[0].aspects]
    assert keys == sorted(keys)


# ---------------------------------------------------------------------------
# Structural invariants (aspect count per kind)
# ---------------------------------------------------------------------------

def test_find_patterns_t_square_has_exactly_3_contributing_aspects() -> None:
    aspects = [_opp("Sun", "Moon"), _sq("Sun", "Mars"), _sq("Moon", "Mars")]
    tsqs = [p for p in find_patterns(aspects) if p.kind == AspectPatternKind.T_SQUARE]
    assert len(tsqs) == 1
    assert len(tsqs[0].aspects) == 3


def test_find_patterns_grand_trine_has_exactly_3_contributing_aspects() -> None:
    aspects = [_trine("Sun", "Moon"), _trine("Moon", "Mars"), _trine("Sun", "Mars")]
    gts = [p for p in find_patterns(aspects) if p.kind == AspectPatternKind.GRAND_TRINE]
    assert len(gts) == 1
    assert len(gts[0].aspects) == 3


def test_find_patterns_grand_cross_has_exactly_6_contributing_aspects() -> None:
    aspects = [
        _opp("Sun", "Moon"),
        _opp("Mars", "Venus"),
        _sq("Sun", "Mars"),
        _sq("Sun", "Venus"),
        _sq("Moon", "Mars"),
        _sq("Moon", "Venus"),
    ]
    gcs = [p for p in find_patterns(aspects) if p.kind == AspectPatternKind.GRAND_CROSS]
    assert len(gcs) == 1
    assert len(gcs[0].aspects) == 6


def test_find_patterns_yod_has_exactly_3_contributing_aspects() -> None:
    aspects = [_sext("Moon", "Mars"), _qcx("Sun", "Moon"), _qcx("Sun", "Mars")]
    yods = [p for p in find_patterns(aspects) if p.kind == AspectPatternKind.YOD]
    assert len(yods) == 1
    assert len(yods[0].aspects) == 3


def test_find_patterns_3_body_stellium_has_exactly_3_contributing_aspects() -> None:
    aspects = [_conj("Sun", "Moon"), _conj("Sun", "Mars"), _conj("Moon", "Mars")]
    stellia = [p for p in find_patterns(aspects) if p.kind == AspectPatternKind.STELLIUM]
    assert len(stellia) == 1
    assert len(stellia[0].aspects) == 3


def test_find_patterns_4_body_stellium_has_exactly_6_contributing_aspects() -> None:
    from itertools import combinations as _comb
    bodies = ["Sun", "Moon", "Mars", "Venus"]
    aspects = [_conj(a, b) for a, b in _comb(bodies, 2)]
    stellia = [p for p in find_patterns(aspects) if p.kind == AspectPatternKind.STELLIUM]
    assert len(stellia) == 1
    assert len(stellia[0].aspects) == 6


# ---------------------------------------------------------------------------
# Near-miss and extra-edge cases
# ---------------------------------------------------------------------------

def test_find_patterns_unrelated_extra_aspects_do_not_create_false_patterns() -> None:
    """Extra pairwise aspects that complete no pattern do not produce false positives."""
    aspects = [
        _opp("Sun", "Moon"),
        _sq("Sun", "Mars"),
        _trine("Moon", "Jupiter"),
        _sext("Mars", "Saturn"),
    ]
    patterns = find_patterns(aspects)
    assert patterns == []


def test_find_patterns_grand_cross_missing_both_oppositions_rejected() -> None:
    """Four squares without any opposition do not form a Grand Cross."""
    aspects = [
        _sq("Sun", "Mars"),
        _sq("Sun", "Venus"),
        _sq("Moon", "Mars"),
        _sq("Moon", "Venus"),
    ]
    assert not any(p.kind == AspectPatternKind.GRAND_CROSS for p in find_patterns(aspects))


def test_find_patterns_t_square_wrong_aspect_type_not_detected() -> None:
    """A Trine where a Square is required does not satisfy T-Square structure."""
    aspects = [_opp("Sun", "Moon"), _trine("Sun", "Mars"), _sq("Moon", "Mars")]
    assert not any(p.kind == AspectPatternKind.T_SQUARE for p in find_patterns(aspects))


def test_find_patterns_yod_sextile_replaced_by_square_rejected() -> None:
    """A Square at the base instead of a Sextile does not satisfy Yod structure."""
    aspects = [_sq("Moon", "Mars"), _qcx("Sun", "Moon"), _qcx("Sun", "Mars")]
    assert not any(p.kind == AspectPatternKind.YOD for p in find_patterns(aspects))


def test_find_patterns_grand_trine_with_one_opposition_not_a_trine() -> None:
    """Replacing one Trine with an Opposition kills the Grand Trine detection."""
    aspects = [_trine("Sun", "Moon"), _opp("Moon", "Mars"), _trine("Sun", "Mars")]
    assert not any(p.kind == AspectPatternKind.GRAND_TRINE for p in find_patterns(aspects))


# ---------------------------------------------------------------------------
# Overlap: independent pattern kinds reported together
# ---------------------------------------------------------------------------

def test_find_patterns_result_order_is_stellia_tsq_gt_gc_yod() -> None:
    """Output order: Stellia first, then T-Squares, Grand Trines, Grand Crosses, Yods."""
    from itertools import combinations as _comb
    stellium_bodies = ["Sun", "Moon", "Mars"]
    s_aspects = [_conj(a, b) for a, b in _comb(stellium_bodies, 2)]
    t_sq_aspects = [_opp("Jupiter", "Saturn"), _sq("Jupiter", "Pluto"), _sq("Saturn", "Pluto")]
    all_aspects = s_aspects + t_sq_aspects
    patterns = find_patterns(all_aspects)
    kinds = [p.kind for p in patterns]
    stellium_idx = kinds.index(AspectPatternKind.STELLIUM)
    tsq_idx = kinds.index(AspectPatternKind.T_SQUARE)
    assert stellium_idx < tsq_idx


def test_find_patterns_two_independent_grand_trines_both_detected() -> None:
    """Two disjoint Grand Trines in the same input are both detected."""
    aspects = [
        _trine("Sun", "Moon"),
        _trine("Moon", "Mars"),
        _trine("Sun", "Mars"),
        _trine("Jupiter", "Saturn"),
        _trine("Saturn", "Pluto"),
        _trine("Jupiter", "Pluto"),
    ]
    gts = [p for p in find_patterns(aspects) if p.kind == AspectPatternKind.GRAND_TRINE]
    assert len(gts) == 2
    body_sets = {p.bodies for p in gts}
    assert frozenset({"Sun", "Moon", "Mars"}) in body_sets
    assert frozenset({"Jupiter", "Saturn", "Pluto"}) in body_sets


# ===========================================================================
# Phase 10 — Relational graph / network layer
# ===========================================================================

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _graph_from(*pairs: tuple[str, str, str]) -> AspectGraph:
    """Build a graph from (body1, body2, aspect_name) triples using _make_aspect."""
    _ANGLES = {
        "Conjunction": 0.0, "Sextile": 60.0, "Square": 90.0,
        "Trine": 120.0, "Opposition": 180.0, "Quincunx": 150.0,
    }
    aspects = [_make_aspect(b1, b2, name, _ANGLES.get(name, 0.0))
               for b1, b2, name in pairs]
    return build_aspect_graph(aspects)


# ---------------------------------------------------------------------------
# Empty input
# ---------------------------------------------------------------------------

def test_build_aspect_graph_empty_returns_empty_graph() -> None:
    g = build_aspect_graph([])
    assert g.nodes == ()
    assert g.edges == ()
    assert g.components == ()
    assert g.hubs == ()
    assert g.isolated == ()


def test_build_aspect_graph_empty_with_bodies_creates_isolated_nodes() -> None:
    g = build_aspect_graph([], bodies=["Sun", "Moon", "Mars"])
    assert len(g.nodes) == 3
    assert all(n.degree == 0 for n in g.nodes)
    names = [n.name for n in g.nodes]
    assert names == sorted(names)
    assert g.isolated == g.nodes


# ---------------------------------------------------------------------------
# Vessel types
# ---------------------------------------------------------------------------

def test_build_aspect_graph_returns_aspect_graph_instance() -> None:
    g = build_aspect_graph([_conj("Sun", "Moon")])
    assert isinstance(g, AspectGraph)


def test_build_aspect_graph_nodes_are_aspect_graph_node_instances() -> None:
    g = build_aspect_graph([_conj("Sun", "Moon")])
    assert all(isinstance(n, AspectGraphNode) for n in g.nodes)


def test_aspect_graph_is_immutable() -> None:
    g = build_aspect_graph([_conj("Sun", "Moon")])
    with pytest.raises((AttributeError, TypeError)):
        g.nodes = ()  # type: ignore[misc]


def test_aspect_graph_node_is_immutable() -> None:
    g = build_aspect_graph([_conj("Sun", "Moon")])
    with pytest.raises((AttributeError, TypeError)):
        g.nodes[0].degree = 99  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Node construction and degree
# ---------------------------------------------------------------------------

def test_build_aspect_graph_single_edge_two_nodes_degree_1() -> None:
    g = build_aspect_graph([_conj("Sun", "Moon")])
    assert len(g.nodes) == 2
    assert all(n.degree == 1 for n in g.nodes)


def test_build_aspect_graph_nodes_sorted_by_name() -> None:
    g = _graph_from(("Sun", "Moon", "Trine"), ("Mars", "Venus", "Square"))
    names = [n.name for n in g.nodes]
    assert names == sorted(names)


def test_build_aspect_graph_degree_correct_for_hub() -> None:
    """Sun aspects three other bodies → degree 3."""
    aspects = [_trine("Sun", "Moon"), _sq("Sun", "Mars"), _opp("Sun", "Venus")]
    g = build_aspect_graph(aspects)
    sun = next(n for n in g.nodes if n.name == "Sun")
    assert sun.degree == 3


def test_build_aspect_graph_degree_invariant_equals_len_edges() -> None:
    """degree == len(edges) for every node."""
    aspects = [_trine("Sun", "Moon"), _sq("Sun", "Mars"), _opp("Moon", "Mars")]
    g = build_aspect_graph(aspects)
    for node in g.nodes:
        assert node.degree == len(node.edges)


def test_build_aspect_graph_family_counts_sum_equals_degree() -> None:
    """sum(family_counts.values()) == degree for every node."""
    aspects = [_trine("Sun", "Moon"), _sq("Sun", "Mars"), _trine("Sun", "Venus")]
    g = build_aspect_graph(aspects)
    for node in g.nodes:
        assert sum(node.family_counts.values()) == node.degree


def test_build_aspect_graph_family_counts_content() -> None:
    """Sun has 2 Trines and 1 Square → family_counts matches."""
    aspects = [_trine("Sun", "Moon"), _sq("Sun", "Mars"), _trine("Sun", "Venus")]
    g = build_aspect_graph(aspects)
    sun = next(n for n in g.nodes if n.name == "Sun")
    assert sun.family_counts.get("Trine", 0) == 2
    assert sun.family_counts.get("Square", 0) == 1


def test_build_aspect_graph_node_edges_contain_only_incident_aspects() -> None:
    """Every edge in a node's edges tuple involves that node."""
    aspects = [_trine("Sun", "Moon"), _sq("Mars", "Venus"), _opp("Sun", "Mars")]
    g = build_aspect_graph(aspects)
    for node in g.nodes:
        for a in node.edges:
            assert node.name in (a.body1, a.body2)


def test_build_aspect_graph_node_edges_are_sorted() -> None:
    """Node edges are sorted by (body1, body2, aspect)."""
    aspects = [_trine("Sun", "Moon"), _sq("Sun", "Mars"), _opp("Sun", "Venus")]
    g = build_aspect_graph(aspects)
    for node in g.nodes:
        keys = [(a.body1, a.body2, a.aspect) for a in node.edges]
        assert keys == sorted(keys)


# ---------------------------------------------------------------------------
# Edges
# ---------------------------------------------------------------------------

def test_build_aspect_graph_edges_sorted() -> None:
    """Graph-level edges are sorted by (body1, body2, aspect)."""
    aspects = [_opp("Sun", "Venus"), _trine("Sun", "Moon"), _sq("Mars", "Saturn")]
    g = build_aspect_graph(aspects)
    keys = [(a.body1, a.body2, a.aspect) for a in g.edges]
    assert keys == sorted(keys)


def test_build_aspect_graph_edges_count_matches_input() -> None:
    """Number of graph edges equals the number of input aspects."""
    aspects = [_trine("Sun", "Moon"), _sq("Sun", "Mars"), _opp("Moon", "Mars")]
    g = build_aspect_graph(aspects)
    assert len(g.edges) == len(aspects)


# ---------------------------------------------------------------------------
# Connected components
# ---------------------------------------------------------------------------

def test_build_aspect_graph_single_edge_one_component() -> None:
    g = build_aspect_graph([_conj("Sun", "Moon")])
    assert len(g.components) == 1
    assert g.components[0] == frozenset({"Sun", "Moon"})


def test_build_aspect_graph_two_disjoint_pairs_two_components() -> None:
    aspects = [_conj("Sun", "Moon"), _trine("Mars", "Venus")]
    g = build_aspect_graph(aspects)
    assert len(g.components) == 2
    component_sets = set(g.components)
    assert frozenset({"Sun", "Moon"}) in component_sets
    assert frozenset({"Mars", "Venus"}) in component_sets


def test_build_aspect_graph_chain_forms_one_component() -> None:
    """Sun–Moon, Moon–Mars, Mars–Venus: all connected through the chain."""
    aspects = [_conj("Sun", "Moon"), _trine("Moon", "Mars"), _sq("Mars", "Venus")]
    g = build_aspect_graph(aspects)
    assert len(g.components) == 1
    assert g.components[0] == frozenset({"Sun", "Moon", "Mars", "Venus"})


def test_build_aspect_graph_isolated_body_is_singleton_component() -> None:
    """An isolated body (supplied via bodies=) forms its own singleton component."""
    g = build_aspect_graph([_conj("Sun", "Moon")], bodies=["Mars"])
    assert len(g.components) == 2
    component_sets = set(g.components)
    assert frozenset({"Mars"}) in component_sets


def test_build_aspect_graph_components_are_frozensets() -> None:
    g = build_aspect_graph([_conj("Sun", "Moon"), _trine("Mars", "Venus")])
    assert all(isinstance(c, frozenset) for c in g.components)


def test_build_aspect_graph_components_sorted_by_min_name_then_len() -> None:
    """Components sorted by (min(component), len(component)) ascending."""
    aspects = [_conj("Sun", "Moon"), _trine("Mars", "Venus")]
    g = build_aspect_graph(aspects)
    keys = [(min(c), len(c)) for c in g.components]
    assert keys == sorted(keys)


# ---------------------------------------------------------------------------
# Hub detection
# ---------------------------------------------------------------------------

def test_build_aspect_graph_hub_is_highest_degree_node() -> None:
    """Sun aspects three bodies; Sun should be the hub."""
    aspects = [_trine("Sun", "Moon"), _sq("Sun", "Mars"), _opp("Sun", "Venus")]
    g = build_aspect_graph(aspects)
    assert len(g.hubs) == 1
    assert g.hubs[0].name == "Sun"
    assert g.hubs[0].degree == 3


def test_build_aspect_graph_hub_tie_returns_all_tied_nodes() -> None:
    """Two bodies each with degree 2 → both returned as hubs."""
    aspects = [_conj("Sun", "Moon"), _trine("Sun", "Mars"), _sq("Moon", "Venus")]
    g = build_aspect_graph(aspects)
    hub_degrees = {n.degree for n in g.hubs}
    assert len(hub_degrees) == 1
    max_deg = max(n.degree for n in g.nodes)
    assert all(n.degree == max_deg for n in g.hubs)


def test_build_aspect_graph_no_edges_no_hubs() -> None:
    """With only isolated bodies, hubs is empty."""
    g = build_aspect_graph([], bodies=["Sun", "Moon"])
    assert g.hubs == ()


# ---------------------------------------------------------------------------
# Isolated nodes
# ---------------------------------------------------------------------------

def test_build_aspect_graph_isolated_only_when_bodies_supplied() -> None:
    """Without bodies=, no degree-0 nodes exist (every node has at least one edge)."""
    g = build_aspect_graph([_conj("Sun", "Moon")])
    assert g.isolated == ()


def test_build_aspect_graph_isolated_node_correct_fields() -> None:
    g = build_aspect_graph([], bodies=["Sun"])
    assert len(g.isolated) == 1
    n = g.isolated[0]
    assert n.name == "Sun"
    assert n.degree == 0
    assert n.edges == ()
    assert n.family_counts == {}


def test_build_aspect_graph_isolated_sorted_by_name() -> None:
    g = build_aspect_graph([], bodies=["Venus", "Sun", "Mars"])
    names = [n.name for n in g.isolated]
    assert names == sorted(names)


# ---------------------------------------------------------------------------
# bodies= parameter
# ---------------------------------------------------------------------------

def test_build_aspect_graph_bodies_does_not_duplicate_existing_nodes() -> None:
    """Supplying a body that already has edges does not create a duplicate node."""
    g = build_aspect_graph([_conj("Sun", "Moon")], bodies=["Sun", "Mars"])
    names = [n.name for n in g.nodes]
    assert len(names) == len(set(names))
    assert "Sun" in names
    assert "Mars" in names


def test_build_aspect_graph_bodies_only_nodes_are_isolated() -> None:
    g = build_aspect_graph([_conj("Sun", "Moon")], bodies=["Jupiter"])
    jupiter = next(n for n in g.nodes if n.name == "Jupiter")
    assert jupiter.degree == 0
    assert jupiter in g.isolated


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

def test_build_aspect_graph_deterministic_across_calls() -> None:
    """Same logical input always produces identical AspectGraph."""
    aspects = [_trine("Sun", "Moon"), _sq("Sun", "Mars"), _opp("Moon", "Venus")]
    g1 = build_aspect_graph(aspects)
    g2 = build_aspect_graph(aspects)
    assert g1.nodes == g2.nodes
    assert g1.edges == g2.edges
    assert g1.components == g2.components


def test_build_aspect_graph_input_permutation_invariant() -> None:
    """Any permutation of the input list produces identical output."""
    import itertools as _it
    aspects = [_trine("Sun", "Moon"), _sq("Sun", "Mars"), _opp("Moon", "Mars")]
    ref = build_aspect_graph(aspects)
    for perm in _it.permutations(aspects):
        g = build_aspect_graph(list(perm))
        assert g.nodes == ref.nodes
        assert g.edges == ref.edges
        assert g.components == ref.components


def test_build_aspect_graph_does_not_mutate_input_list() -> None:
    aspects = [_conj("Sun", "Moon"), _trine("Sun", "Mars")]
    original_ids = [id(a) for a in aspects]
    original_len = len(aspects)
    build_aspect_graph(aspects)
    assert len(aspects) == original_len
    assert [id(a) for a in aspects] == original_ids


def test_build_aspect_graph_does_not_alter_pairwise_aspect_fields() -> None:
    a1 = _trine("Sun", "Moon")
    a2 = _sq("Sun", "Mars")
    before = [(x.body1, x.body2, x.aspect, x.orb) for x in (a1, a2)]
    build_aspect_graph([a1, a2])
    after = [(x.body1, x.body2, x.aspect, x.orb) for x in (a1, a2)]
    assert before == after


# ---------------------------------------------------------------------------
# No semantic drift — existing pairwise and pattern semantics unchanged
# ---------------------------------------------------------------------------

def test_build_aspect_graph_does_not_affect_find_aspects() -> None:
    """Building a graph from an aspect list does not interfere with find_aspects."""
    results = find_aspects({"Sun": 0.0, "Moon": 120.0}, include_minor=False)
    g = build_aspect_graph(results)
    results2 = find_aspects({"Sun": 0.0, "Moon": 120.0}, include_minor=False)
    assert len(results) == len(results2)
    assert results[0].aspect == results2[0].aspect
    assert len(g.nodes) == 2


def test_build_aspect_graph_does_not_affect_find_patterns() -> None:
    """Building a graph does not interfere with find_patterns on the same list."""
    aspects = [_trine("Sun", "Moon"), _trine("Moon", "Mars"), _trine("Sun", "Mars")]
    patterns_before = find_patterns(aspects)
    build_aspect_graph(aspects)
    patterns_after = find_patterns(aspects)
    assert [(p.kind, p.bodies) for p in patterns_before] == \
           [(p.kind, p.bodies) for p in patterns_after]


# ===========================================================================
# Phase 11 — Harmonic / family intelligence layer
# ===========================================================================

# ---------------------------------------------------------------------------
# Empty input
# ---------------------------------------------------------------------------

def test_aspect_harmonic_profile_empty_returns_zero_profile() -> None:
    p = aspect_harmonic_profile([])
    assert p.chart.total == 0
    assert p.chart.counts == {}
    assert p.chart.proportions == {}
    assert p.chart.dominant == ()
    assert p.by_body == {}


# ---------------------------------------------------------------------------
# Vessel types and immutability
# ---------------------------------------------------------------------------

def test_aspect_harmonic_profile_returns_correct_types() -> None:
    p = aspect_harmonic_profile([_trine("Sun", "Moon")])
    assert isinstance(p, AspectHarmonicProfile)
    assert isinstance(p.chart, AspectFamilyProfile)
    for v in p.by_body.values():
        assert isinstance(v, AspectFamilyProfile)


def test_aspect_harmonic_profile_is_immutable() -> None:
    p = aspect_harmonic_profile([_trine("Sun", "Moon")])
    with pytest.raises((AttributeError, TypeError)):
        p.chart = p.chart  # type: ignore[misc]


def test_aspect_family_profile_is_immutable() -> None:
    p = aspect_harmonic_profile([_trine("Sun", "Moon")])
    with pytest.raises((AttributeError, TypeError)):
        p.chart.total = 0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Chart-level counts
# ---------------------------------------------------------------------------

def test_aspect_harmonic_profile_single_trine_counts() -> None:
    p = aspect_harmonic_profile([_trine("Sun", "Moon")])
    assert p.chart.total == 1
    assert p.chart.counts.get(AspectFamily.TRINE) == 1
    assert len(p.chart.counts) == 1


def test_aspect_harmonic_profile_mixed_families_counts() -> None:
    """2 Trines + 1 Square → correct counts per family."""
    aspects = [_trine("Sun", "Moon"), _trine("Moon", "Mars"), _sq("Sun", "Jupiter")]
    p = aspect_harmonic_profile(aspects)
    assert p.chart.total == 3
    assert p.chart.counts[AspectFamily.TRINE] == 2
    assert p.chart.counts[AspectFamily.SQUARE] == 1
    assert len(p.chart.counts) == 2


def test_aspect_harmonic_profile_biquintile_maps_to_quintile_family() -> None:
    """Biquintile belongs to the QUINTILE family."""
    a = _make_aspect("Sun", "Moon", "Biquintile", 144.0)
    p = aspect_harmonic_profile([a])
    assert p.chart.counts.get(AspectFamily.QUINTILE) == 1


def test_aspect_harmonic_profile_counts_sum_equals_total() -> None:
    aspects = [_trine("Sun", "Moon"), _sq("Sun", "Mars"), _opp("Moon", "Venus")]
    p = aspect_harmonic_profile(aspects)
    assert sum(p.chart.counts.values()) == p.chart.total


def test_aspect_harmonic_profile_only_present_families_in_counts() -> None:
    """counts must not include families with zero aspects."""
    aspects = [_trine("Sun", "Moon")]
    p = aspect_harmonic_profile(aspects)
    assert all(v > 0 for v in p.chart.counts.values())


def test_aspect_harmonic_profile_counts_keys_follow_family_enum_order() -> None:
    """counts keys must be in AspectFamily declaration order (subset of it)."""
    aspects = [_sq("Sun", "Moon"), _trine("Sun", "Mars"), _opp("Moon", "Jupiter")]
    p = aspect_harmonic_profile(aspects)
    all_families = list(AspectFamily)
    present = [f for f in all_families if f in p.chart.counts]
    assert list(p.chart.counts.keys()) == present


# ---------------------------------------------------------------------------
# Proportions
# ---------------------------------------------------------------------------

def test_aspect_harmonic_profile_proportions_sum_to_one() -> None:
    aspects = [_trine("Sun", "Moon"), _sq("Sun", "Mars"), _opp("Moon", "Venus")]
    p = aspect_harmonic_profile(aspects)
    assert abs(sum(p.chart.proportions.values()) - 1.0) < 1e-9


def test_aspect_harmonic_profile_proportion_correct_value() -> None:
    """2 Trines out of 4 total → proportion 0.5."""
    aspects = [
        _trine("Sun", "Moon"), _trine("Moon", "Mars"),
        _sq("Sun", "Jupiter"), _opp("Mars", "Venus"),
    ]
    p = aspect_harmonic_profile(aspects)
    assert abs(p.chart.proportions[AspectFamily.TRINE] - 0.5) < 1e-9


def test_aspect_harmonic_profile_proportions_keys_match_counts_keys() -> None:
    aspects = [_trine("Sun", "Moon"), _sq("Sun", "Mars")]
    p = aspect_harmonic_profile(aspects)
    assert set(p.chart.proportions.keys()) == set(p.chart.counts.keys())


def test_aspect_harmonic_profile_all_proportions_in_unit_interval() -> None:
    aspects = [_trine("Sun", "Moon"), _sq("Sun", "Mars"), _opp("Moon", "Venus")]
    p = aspect_harmonic_profile(aspects)
    assert all(0.0 <= v <= 1.0 for v in p.chart.proportions.values())


def test_aspect_harmonic_profile_empty_proportions_when_total_zero() -> None:
    p = aspect_harmonic_profile([])
    assert p.chart.proportions == {}


# ---------------------------------------------------------------------------
# Dominant family detection
# ---------------------------------------------------------------------------

def test_aspect_harmonic_profile_dominant_single_winner() -> None:
    """3 Trines, 1 Square → Trine is dominant."""
    aspects = [
        _trine("Sun", "Moon"), _trine("Moon", "Mars"), _trine("Sun", "Mars"),
        _sq("Jupiter", "Saturn"),
    ]
    p = aspect_harmonic_profile(aspects)
    assert p.chart.dominant == (AspectFamily.TRINE,)


def test_aspect_harmonic_profile_dominant_tie_returns_all_sorted() -> None:
    """2 Trines, 2 Squares — tie → both in dominant, sorted by family value."""
    aspects = [
        _trine("Sun", "Moon"), _trine("Moon", "Mars"),
        _sq("Sun", "Jupiter"), _sq("Mars", "Venus"),
    ]
    p = aspect_harmonic_profile(aspects)
    assert len(p.chart.dominant) == 2
    values = [f.value for f in p.chart.dominant]
    assert values == sorted(values)
    assert AspectFamily.SQUARE in p.chart.dominant
    assert AspectFamily.TRINE in p.chart.dominant


def test_aspect_harmonic_profile_dominant_empty_when_total_zero() -> None:
    p = aspect_harmonic_profile([])
    assert p.chart.dominant == ()


def test_aspect_harmonic_profile_dominant_members_are_in_counts() -> None:
    aspects = [_trine("Sun", "Moon"), _sq("Sun", "Mars"), _opp("Moon", "Venus")]
    p = aspect_harmonic_profile(aspects)
    for fam in p.chart.dominant:
        assert fam in p.chart.counts


def test_aspect_harmonic_profile_dominant_is_tuple() -> None:
    p = aspect_harmonic_profile([_trine("Sun", "Moon")])
    assert isinstance(p.chart.dominant, tuple)


# ---------------------------------------------------------------------------
# Per-body profiles (by_body)
# ---------------------------------------------------------------------------

def test_aspect_harmonic_profile_by_body_keys_present() -> None:
    """Every body that appears in at least one aspect has an entry in by_body."""
    aspects = [_trine("Sun", "Moon"), _sq("Mars", "Venus")]
    p = aspect_harmonic_profile(aspects)
    assert set(p.by_body.keys()) == {"Sun", "Moon", "Mars", "Venus"}


def test_aspect_harmonic_profile_by_body_keys_sorted() -> None:
    aspects = [_trine("Sun", "Moon"), _sq("Mars", "Venus"), _opp("Jupiter", "Saturn")]
    p = aspect_harmonic_profile(aspects)
    keys = list(p.by_body.keys())
    assert keys == sorted(keys)


def test_aspect_harmonic_profile_by_body_degree_matches_total() -> None:
    """A body's by_body total equals the number of aspects it participates in."""
    aspects = [_trine("Sun", "Moon"), _sq("Sun", "Mars"), _opp("Sun", "Venus")]
    p = aspect_harmonic_profile(aspects)
    assert p.by_body["Sun"].total == 3
    assert p.by_body["Moon"].total == 1


def test_aspect_harmonic_profile_by_body_counts_correct() -> None:
    """Sun has 2 Trines and 1 Square in its incident aspects."""
    aspects = [_trine("Sun", "Moon"), _trine("Sun", "Mars"), _sq("Sun", "Jupiter")]
    p = aspect_harmonic_profile(aspects)
    sun = p.by_body["Sun"]
    assert sun.counts[AspectFamily.TRINE] == 2
    assert sun.counts[AspectFamily.SQUARE] == 1
    assert sun.total == 3


def test_aspect_harmonic_profile_by_body_proportions_sum_to_one() -> None:
    aspects = [_trine("Sun", "Moon"), _sq("Sun", "Mars"), _trine("Sun", "Venus")]
    p = aspect_harmonic_profile(aspects)
    sun = p.by_body["Sun"]
    assert abs(sum(sun.proportions.values()) - 1.0) < 1e-9


def test_aspect_harmonic_profile_by_body_dominant_correct() -> None:
    """Body with 2 Trines and 1 Square → Trine dominates."""
    aspects = [_trine("Sun", "Moon"), _trine("Sun", "Mars"), _sq("Sun", "Jupiter")]
    p = aspect_harmonic_profile(aspects)
    assert p.by_body["Sun"].dominant == (AspectFamily.TRINE,)


def test_aspect_harmonic_profile_by_body_isolated_body_absent() -> None:
    """A body with no aspects has no entry in by_body."""
    aspects = [_trine("Sun", "Moon")]
    p = aspect_harmonic_profile(aspects)
    assert "Mars" not in p.by_body


# ---------------------------------------------------------------------------
# AspectFamilyProfile structural invariants
# ---------------------------------------------------------------------------

def test_aspect_family_profile_counts_sum_equals_total_invariant() -> None:
    aspects = [_trine("Sun", "Moon"), _sq("Sun", "Mars"), _opp("Moon", "Venus"),
               _trine("Mars", "Jupiter")]
    p = aspect_harmonic_profile(aspects)
    assert sum(p.chart.counts.values()) == p.chart.total


def test_aspect_family_profile_proportions_len_equals_counts_len_invariant() -> None:
    aspects = [_trine("Sun", "Moon"), _sq("Sun", "Mars")]
    p = aspect_harmonic_profile(aspects)
    assert len(p.chart.proportions) == len(p.chart.counts)


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

def test_aspect_harmonic_profile_deterministic_across_calls() -> None:
    aspects = [_trine("Sun", "Moon"), _sq("Sun", "Mars"), _opp("Moon", "Venus")]
    p1 = aspect_harmonic_profile(aspects)
    p2 = aspect_harmonic_profile(aspects)
    assert p1.chart.counts == p2.chart.counts
    assert p1.chart.dominant == p2.chart.dominant
    assert p1.by_body.keys() == p2.by_body.keys()


def test_aspect_harmonic_profile_input_permutation_invariant() -> None:
    """Any permutation of the input list produces identical output."""
    import itertools as _it
    aspects = [_trine("Sun", "Moon"), _sq("Sun", "Mars"), _opp("Moon", "Venus")]
    ref = aspect_harmonic_profile(aspects)
    for perm in _it.permutations(aspects):
        p = aspect_harmonic_profile(list(perm))
        assert p.chart.counts == ref.chart.counts
        assert p.chart.proportions == ref.chart.proportions
        assert p.chart.dominant == ref.chart.dominant
        assert list(p.by_body.keys()) == list(ref.by_body.keys())


def test_aspect_harmonic_profile_does_not_mutate_input_list() -> None:
    aspects = [_trine("Sun", "Moon"), _sq("Sun", "Mars")]
    original_ids = [id(a) for a in aspects]
    original_len = len(aspects)
    aspect_harmonic_profile(aspects)
    assert len(aspects) == original_len
    assert [id(a) for a in aspects] == original_ids


def test_aspect_harmonic_profile_does_not_alter_pairwise_fields() -> None:
    a1 = _trine("Sun", "Moon")
    a2 = _sq("Sun", "Mars")
    before = [(x.body1, x.body2, x.aspect, x.orb) for x in (a1, a2)]
    aspect_harmonic_profile([a1, a2])
    after = [(x.body1, x.body2, x.aspect, x.orb) for x in (a1, a2)]
    assert before == after


# ---------------------------------------------------------------------------
# No semantic drift — existing layers unaffected
# ---------------------------------------------------------------------------

def test_aspect_harmonic_profile_does_not_affect_find_aspects() -> None:
    results = find_aspects({"Sun": 0.0, "Moon": 120.0}, include_minor=False)
    aspect_harmonic_profile(results)
    results2 = find_aspects({"Sun": 0.0, "Moon": 120.0}, include_minor=False)
    assert len(results) == len(results2)
    assert results[0].aspect == results2[0].aspect


def test_aspect_harmonic_profile_does_not_affect_find_patterns() -> None:
    aspects = [_trine("Sun", "Moon"), _trine("Moon", "Mars"), _trine("Sun", "Mars")]
    patterns_before = find_patterns(aspects)
    aspect_harmonic_profile(aspects)
    patterns_after = find_patterns(aspects)
    assert [(p.kind, p.bodies) for p in patterns_before] == \
           [(p.kind, p.bodies) for p in patterns_after]


def test_aspect_harmonic_profile_does_not_affect_build_aspect_graph() -> None:
    aspects = [_trine("Sun", "Moon"), _sq("Sun", "Mars")]
    g_before = build_aspect_graph(aspects)
    aspect_harmonic_profile(aspects)
    g_after = build_aspect_graph(aspects)
    assert g_before.nodes == g_after.nodes
    assert g_before.edges == g_after.edges


# ===========================================================================
# Phase 12 — Full-subsystem hardening
# ===========================================================================

# ---------------------------------------------------------------------------
# aspect_strength: failure behavior
# ---------------------------------------------------------------------------

def test_aspect_strength_raises_on_zero_allowed_orb() -> None:
    """allowed_orb=0.0 must raise ValueError, not ZeroDivisionError."""
    bad = AspectData(
        body1="Sun", body2="Moon", aspect="Conjunction", symbol="☌",
        angle=0.0, separation=0.0, orb=0.0, allowed_orb=0.0,
        applying=None, stationary=False,
    )
    with pytest.raises(ValueError, match="allowed_orb"):
        aspect_strength(bad)


def test_aspect_strength_raises_on_negative_allowed_orb() -> None:
    """allowed_orb < 0 must raise ValueError."""
    bad = AspectData(
        body1="Sun", body2="Moon", aspect="Conjunction", symbol="☌",
        angle=0.0, separation=0.0, orb=0.0, allowed_orb=-1.0,
        applying=None, stationary=False,
    )
    with pytest.raises(ValueError, match="allowed_orb"):
        aspect_strength(bad)


def test_aspect_strength_raises_on_orb_exceeding_allowed_orb() -> None:
    """orb > allowed_orb must raise ValueError (admission invariant violated)."""
    bad = AspectData(
        body1="Sun", body2="Moon", aspect="Trine", symbol="△",
        angle=120.0, separation=125.0, orb=5.0, allowed_orb=2.0,
        applying=None, stationary=False,
    )
    with pytest.raises(ValueError, match="orb"):
        aspect_strength(bad)


def test_aspect_strength_error_message_contains_values() -> None:
    """ValueError messages must include the offending field values."""
    bad = AspectData(
        body1="Sun", body2="Moon", aspect="Conjunction", symbol="☌",
        angle=0.0, separation=0.0, orb=0.0, allowed_orb=0.0,
        applying=None, stationary=False,
    )
    with pytest.raises(ValueError) as exc_info:
        aspect_strength(bad)
    assert "0.0" in str(exc_info.value) or "allowed_orb" in str(exc_info.value)


def test_aspect_strength_boundary_orb_equals_allowed_orb_does_not_raise() -> None:
    """orb == allowed_orb is valid (admitted at boundary); no error."""
    boundary = AspectData(
        body1="Sun", body2="Moon", aspect="Trine", symbol="△",
        angle=120.0, separation=124.0, orb=4.0, allowed_orb=4.0,
        applying=None, stationary=False,
    )
    s = aspect_strength(boundary)
    assert s.exactness == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# AspectPolicy: failure behavior
# ---------------------------------------------------------------------------

def test_aspect_policy_raises_on_zero_orb_factor() -> None:
    """orb_factor=0 must raise ValueError."""
    with pytest.raises(ValueError, match="orb_factor"):
        AspectPolicy(orb_factor=0.0)


def test_aspect_policy_raises_on_negative_orb_factor() -> None:
    """orb_factor < 0 must raise ValueError."""
    with pytest.raises(ValueError, match="orb_factor"):
        AspectPolicy(orb_factor=-0.5)


def test_aspect_policy_raises_on_negative_declination_orb() -> None:
    """declination_orb < 0 must raise ValueError."""
    with pytest.raises(ValueError, match="declination_orb"):
        AspectPolicy(declination_orb=-1.0)


def test_aspect_policy_zero_declination_orb_is_valid() -> None:
    """declination_orb=0.0 is valid (no declination aspects admitted)."""
    p = AspectPolicy(declination_orb=0.0)
    assert p.declination_orb == 0.0


def test_default_policy_is_valid() -> None:
    """DEFAULT_POLICY must not raise at construction."""
    p = DEFAULT_POLICY
    assert p.orb_factor == 1.0
    assert p.declination_orb == 1.0


# ---------------------------------------------------------------------------
# Cross-layer: classification consistency
# ---------------------------------------------------------------------------

def test_find_aspects_all_results_have_zodiacal_domain() -> None:
    """Every AspectData from find_aspects has classification.domain == ZODIACAL."""
    results = find_aspects({"Sun": 0.0, "Moon": 60.0, "Mars": 120.0,
                            "Venus": 90.0, "Jupiter": 180.0}, tier=2)
    for a in results:
        assert a.classification is not None
        assert a.classification.domain is AspectDomain.ZODIACAL


def test_find_aspects_all_results_classification_family_matches_name() -> None:
    """classification.family must match the known family for the aspect name."""
    from moira.aspects import _FAMILY_BY_NAME
    results = find_aspects({"Sun": 0.0, "Moon": 60.0, "Mars": 120.0,
                            "Venus": 90.0, "Jupiter": 180.0}, tier=2)
    for a in results:
        assert a.classification is not None
        assert a.classification.family is _FAMILY_BY_NAME[a.aspect]


def test_find_aspects_major_aspects_have_major_tier() -> None:
    """Major aspect names must carry AspectTier.MAJOR."""
    major_names = {"Conjunction", "Sextile", "Square", "Trine", "Opposition"}
    positions = {"Sun": 0.0, "Moon": 60.0, "Mars": 90.0,
                 "Venus": 120.0, "Jupiter": 180.0}
    results = find_aspects(positions, include_minor=False)
    for a in results:
        if a.aspect in major_names:
            assert a.classification is not None
            assert a.classification.tier is AspectTier.MAJOR


def test_find_declination_aspects_all_results_have_declination_domain() -> None:
    """Every DeclinationAspect has classification.domain == DECLINATION."""
    results = find_declination_aspects({"Sun": 10.0, "Moon": 10.0}, orb=1.0)
    for a in results:
        assert a.classification is not None
        assert a.classification.domain is AspectDomain.DECLINATION


def test_find_declination_aspects_family_is_declination() -> None:
    """Every DeclinationAspect has classification.family == DECLINATION."""
    results = find_declination_aspects({"Sun": 10.0, "Moon": 10.0}, orb=1.0)
    for a in results:
        assert a.classification is not None
        assert a.classification.family is AspectFamily.DECLINATION


# ---------------------------------------------------------------------------
# Cross-layer: strength invariants on real detection output
# ---------------------------------------------------------------------------

def test_aspect_strength_invariants_on_all_detected_aspects() -> None:
    """All four AspectStrength invariants hold for every admitted aspect."""
    results = find_aspects({"Sun": 0.0, "Moon": 58.0, "Mars": 123.0,
                            "Venus": 88.0, "Jupiter": 177.0}, tier=1)
    for a in results:
        s = aspect_strength(a)
        assert s.orb >= 0.0
        assert s.orb <= s.allowed_orb
        assert abs(s.surplus - (s.allowed_orb - s.orb)) < 1e-9
        assert 0.0 <= s.exactness <= 1.0
        assert abs(s.exactness - (1.0 - s.orb / s.allowed_orb)) < 1e-9


def test_aspect_strength_exactly_matches_vessel_fields() -> None:
    """strength.orb and strength.allowed_orb are identical to vessel fields."""
    results = find_aspects({"Sun": 0.0, "Moon": 120.0}, include_minor=False)
    assert len(results) == 1
    s = aspect_strength(results[0])
    assert s.orb == results[0].orb
    assert s.allowed_orb == results[0].allowed_orb


# ---------------------------------------------------------------------------
# Cross-layer: motion-state consistency
# ---------------------------------------------------------------------------

def test_motion_state_and_is_applying_are_consistent() -> None:
    """When MotionState is APPLYING, is_applying must be True and is_separating False."""
    applying = AspectData(
        body1="Sun", body2="Moon", aspect="Trine", symbol="△",
        angle=120.0, separation=120.0, orb=0.0, allowed_orb=8.0,
        applying=True, stationary=False,
    )
    assert aspect_motion_state(applying) is MotionState.APPLYING
    assert applying.is_applying is True
    assert applying.is_separating is False


def test_motion_state_and_is_separating_are_consistent() -> None:
    """When MotionState is SEPARATING, is_separating must be True and is_applying False."""
    separating = AspectData(
        body1="Sun", body2="Moon", aspect="Trine", symbol="△",
        angle=120.0, separation=120.0, orb=0.0, allowed_orb=8.0,
        applying=False, stationary=False,
    )
    assert aspect_motion_state(separating) is MotionState.SEPARATING
    assert separating.is_separating is True
    assert separating.is_applying is False


def test_motion_state_stationary_overrides_applying_flag() -> None:
    """STATIONARY takes precedence regardless of the applying field."""
    for applying_val in (True, False, None):
        a = AspectData(
            body1="Sun", body2="Moon", aspect="Trine", symbol="△",
            angle=120.0, separation=120.0, orb=0.0, allowed_orb=8.0,
            applying=applying_val, stationary=True,
        )
        assert aspect_motion_state(a) is MotionState.STATIONARY


def test_motion_state_indeterminate_when_applying_is_none() -> None:
    """None applying with stationary=False → INDETERMINATE."""
    a = AspectData(
        body1="Sun", body2="Moon", aspect="Trine", symbol="△",
        angle=120.0, separation=120.0, orb=0.0, allowed_orb=8.0,
        applying=None, stationary=False,
    )
    assert aspect_motion_state(a) is MotionState.INDETERMINATE
    assert a.is_applying is False
    assert a.is_separating is False


def test_motion_state_none_for_declination_aspect() -> None:
    """DeclinationAspect always yields MotionState.NONE."""
    results = find_declination_aspects({"Sun": 10.0, "Moon": 10.0}, orb=1.0)
    assert len(results) >= 1
    for a in results:
        assert aspect_motion_state(a) is MotionState.NONE


# ---------------------------------------------------------------------------
# Cross-layer: graph degree matches pairwise aspect count
# ---------------------------------------------------------------------------

def test_graph_node_degree_matches_pairwise_count() -> None:
    """Each node's degree equals the number of pairwise aspects it appears in."""
    aspects = find_aspects(
        {"Sun": 0.0, "Moon": 60.0, "Mars": 120.0, "Venus": 180.0},
        include_minor=False,
    )
    g = build_aspect_graph(aspects)
    for node in g.nodes:
        manual_count = sum(
            1 for a in aspects if node.name in (a.body1, a.body2)
        )
        assert node.degree == manual_count


def test_graph_family_counts_consistent_with_harmonic_profile_by_body() -> None:
    """
    For each body, the sum of graph node.family_counts (keyed by aspect name)
    must equal that body's harmonic profile total.
    """
    aspects = [_trine("Sun", "Moon"), _trine("Sun", "Mars"),
               _sq("Moon", "Jupiter"), _opp("Mars", "Venus")]
    g = build_aspect_graph(aspects)
    hp = aspect_harmonic_profile(aspects)
    for node in g.nodes:
        assert sum(node.family_counts.values()) == hp.by_body[node.name].total


# ---------------------------------------------------------------------------
# Cross-layer: harmonic profile total vs aspect list length
# ---------------------------------------------------------------------------

def test_harmonic_profile_chart_total_equals_len_aspects() -> None:
    """chart.total must equal len(aspects) — every aspect is counted once."""
    aspects = [_trine("Sun", "Moon"), _sq("Sun", "Mars"), _opp("Moon", "Venus")]
    p = aspect_harmonic_profile(aspects)
    assert p.chart.total == len(aspects)


def test_harmonic_profile_by_body_total_each_body_correct() -> None:
    """Each body's by_body total equals the number of aspects it appears in."""
    aspects = find_aspects(
        {"Sun": 0.0, "Moon": 60.0, "Mars": 120.0, "Venus": 180.0},
        include_minor=False,
    )
    p = aspect_harmonic_profile(aspects)
    for name, profile in p.by_body.items():
        manual = sum(1 for a in aspects if name in (a.body1, a.body2))
        assert profile.total == manual


# ---------------------------------------------------------------------------
# Cross-layer: canonical aspects cover exactly the detection engine's set
# ---------------------------------------------------------------------------

def test_canonical_aspects_zodiacal_names_all_detectable_at_exact_angle() -> None:
    """Every zodiacal name in CANONICAL_ASPECTS can be detected at its exact angle."""
    from moira.constants import Aspect as _Aspect
    angle_by_name = {adef.name: adef.angle for adef in _Aspect.ALL}
    for name in CANONICAL_ASPECTS:
        if name in ("Parallel", "Contra-Parallel"):
            continue
        angle = angle_by_name[name]
        results = find_aspects({"A": 0.0, "B": angle}, tier=2, include_minor=True)
        names_found = {r.aspect for r in results}
        assert name in names_found, f"{name} not detectable at {angle}°"


def test_canonical_aspects_has_no_name_absent_from_family_lookup() -> None:
    """Every zodiacal canonical name must be in _FAMILY_BY_NAME."""
    from moira.aspects import _FAMILY_BY_NAME
    for name in CANONICAL_ASPECTS:
        if name in ("Parallel", "Contra-Parallel"):
            continue
        assert name in _FAMILY_BY_NAME, f"{name} missing from _FAMILY_BY_NAME"


# ---------------------------------------------------------------------------
# Cross-layer: orb_surplus consistency
# ---------------------------------------------------------------------------

def test_orb_surplus_equals_strength_surplus_for_detected_aspects() -> None:
    """AspectData.orb_surplus and AspectStrength.surplus are identical."""
    results = find_aspects({"Sun": 0.0, "Moon": 118.0}, include_minor=False)
    for a in results:
        s = aspect_strength(a)
        assert a.orb_surplus == pytest.approx(s.surplus)


def test_declination_orb_surplus_non_negative() -> None:
    """DeclinationAspect.orb_surplus is always non-negative for admitted aspects."""
    results = find_declination_aspects(
        {"Sun": 10.0, "Moon": 9.5, "Mars": -9.8}, orb=1.0
    )
    for a in results:
        assert a.orb_surplus >= 0.0


# ---------------------------------------------------------------------------
# Cross-layer: is_major / is_minor mutual exclusion
# ---------------------------------------------------------------------------

def test_is_major_and_is_minor_are_mutually_exclusive_on_detected_aspects() -> None:
    """For classified aspects, exactly one of is_major / is_minor is True."""
    results = find_aspects({"Sun": 0.0, "Moon": 60.0, "Mars": 90.0,
                            "Venus": 120.0, "Jupiter": 150.0}, tier=1)
    for a in results:
        assert a.classification is not None
        assert a.is_major != a.is_minor


def test_is_applying_and_is_separating_never_both_true() -> None:
    """is_applying and is_separating are mutually exclusive by construction."""
    for applying_val in (True, False, None):
        a = AspectData(
            body1="Sun", body2="Moon", aspect="Trine", symbol="△",
            angle=120.0, separation=120.0, orb=0.0, allowed_orb=8.0,
            applying=applying_val, stationary=False,
        )
        assert not (a.is_applying and a.is_separating)


# ===========================================================================
# Phase 14 — Public API exposure and surface curation
# ===========================================================================

import moira.aspects as _aspects_module
import moira as _moira_package


_EXPECTED_PUBLIC = {
    "CANONICAL_ASPECTS",
    "DEFAULT_POLICY",
    "AspectDomain",
    "AspectFamily",
    "AspectPatternKind",
    "AspectTier",
    "MotionState",
    "AspectClassification",
    "AspectData",
    "AspectFamilyProfile",
    "AspectGraph",
    "AspectGraphNode",
    "AspectHarmonicProfile",
    "AspectPattern",
    "AspectPolicy",
    "AspectStrength",
    "DeclinationAspect",
    "aspect_harmonic_profile",
    "aspect_motion_state",
    "aspect_strength",
    "aspects_between",
    "aspects_to_point",
    "build_aspect_graph",
    "find_aspects",
    "find_declination_aspects",
    "find_patterns",
}

_EXPECTED_INTERNAL = {
    "_resolve_aspects",
    "_applying",
    "_is_stationary",
    "_aspect_index",
    "_aspects_of_kind",
    "_find_stellia",
    "_find_t_squares",
    "_find_grand_trines",
    "_find_grand_crosses",
    "_find_yods",
    "_connected_components",
    "_build_family_profile",
    "_FAMILY_BY_NAME",
    "_ASPECT_CLASSIFICATION",
    "_PARALLEL_CLASSIFICATION",
    "_CONTRA_PARALLEL_CLASSIFICATION",
    "_EXTENDED_MINOR_NAMES",
    "_COMMON_MINOR_NAMES",
    "_tier_for",
    "_STATIONARY_THRESHOLD",
}


def test_aspects_module_has_dunder_all() -> None:
    assert hasattr(_aspects_module, "__all__"), "moira.aspects must define __all__"


def test_aspects_dunder_all_contains_all_curated_names() -> None:
    all_set = set(_aspects_module.__all__)
    missing = _EXPECTED_PUBLIC - all_set
    assert not missing, f"names missing from __all__: {sorted(missing)}"


def test_aspects_dunder_all_contains_no_internal_names() -> None:
    all_set = set(_aspects_module.__all__)
    leaked = _EXPECTED_INTERNAL & all_set
    assert not leaked, f"internal names leaked into __all__: {sorted(leaked)}"


def test_aspects_dunder_all_no_underscore_names() -> None:
    leaked = [n for n in _aspects_module.__all__ if n.startswith("_")]
    assert not leaked, f"underscore names in __all__: {leaked}"


def test_all_curated_names_importable_from_moira_aspects() -> None:
    for name in _EXPECTED_PUBLIC:
        assert hasattr(_aspects_module, name), f"moira.aspects missing: {name}"


def test_all_curated_names_importable_from_moira_package() -> None:
    for name in _EXPECTED_PUBLIC - {"AspectPattern"}:
        assert hasattr(_moira_package, name), f"moira package missing: {name}"


def test_moira_package_exports_canonical_aspects() -> None:
    from moira import CANONICAL_ASPECTS
    assert isinstance(CANONICAL_ASPECTS, tuple)
    assert len(CANONICAL_ASPECTS) == 24


def test_moira_package_exports_default_policy() -> None:
    from moira import DEFAULT_POLICY, AspectPolicy
    assert isinstance(DEFAULT_POLICY, AspectPolicy)


def test_moira_package_exports_aspect_domain() -> None:
    from moira import AspectDomain
    assert hasattr(AspectDomain, "ZODIACAL")
    assert hasattr(AspectDomain, "DECLINATION")


def test_moira_package_exports_aspect_tier() -> None:
    from moira import AspectTier
    assert hasattr(AspectTier, "MAJOR")
    assert hasattr(AspectTier, "COMMON_MINOR")
    assert hasattr(AspectTier, "EXTENDED_MINOR")


def test_moira_package_exports_aspect_family() -> None:
    from moira import AspectFamily
    assert hasattr(AspectFamily, "CONJUNCTION")
    assert hasattr(AspectFamily, "TRINE")


def test_moira_package_exports_motion_state() -> None:
    from moira import MotionState
    assert hasattr(MotionState, "APPLYING")
    assert hasattr(MotionState, "SEPARATING")
    assert hasattr(MotionState, "STATIONARY")
    assert hasattr(MotionState, "INDETERMINATE")
    assert hasattr(MotionState, "NONE")


def test_moira_package_exports_aspect_pattern_kind() -> None:
    from moira import AspectPatternKind
    assert hasattr(AspectPatternKind, "STELLIUM")
    assert hasattr(AspectPatternKind, "T_SQUARE")
    assert hasattr(AspectPatternKind, "GRAND_TRINE")
    assert hasattr(AspectPatternKind, "GRAND_CROSS")
    assert hasattr(AspectPatternKind, "YOD")


def test_moira_package_exports_find_aspects() -> None:
    from moira import find_aspects
    result = find_aspects({"Sun": 0.0, "Moon": 120.0}, include_minor=False)
    assert any(a.aspect == "Trine" for a in result)


def test_moira_package_exports_aspects_between() -> None:
    from moira import aspects_between
    result = aspects_between("Sun", 0.0, "Moon", 60.0)
    assert any(a.aspect == "Sextile" for a in result)


def test_moira_package_exports_aspects_to_point() -> None:
    from moira import aspects_to_point
    result = aspects_to_point(180.0, {"Sun": 0.0})
    assert any(a.aspect == "Opposition" for a in result)


def test_moira_package_exports_find_declination_aspects() -> None:
    from moira import find_declination_aspects
    result = find_declination_aspects({"Sun": 10.0, "Moon": 10.3})
    assert isinstance(result, list)


def test_moira_package_exports_aspect_strength() -> None:
    from moira import aspect_strength, AspectStrength
    a = AspectData(
        body1="Sun", body2="Moon", aspect="Trine", symbol="△",
        angle=120.0, separation=120.5, orb=0.5, allowed_orb=8.0,
        applying=True, stationary=False,
    )
    s = aspect_strength(a)
    assert isinstance(s, AspectStrength)
    assert s.exactness == pytest.approx(1.0 - 0.5 / 8.0)


def test_moira_package_exports_aspect_motion_state() -> None:
    from moira import aspect_motion_state, MotionState
    a = AspectData(
        body1="Sun", body2="Moon", aspect="Trine", symbol="△",
        angle=120.0, separation=120.5, orb=0.5, allowed_orb=8.0,
        applying=True, stationary=False,
    )
    assert aspect_motion_state(a) == MotionState.APPLYING


def test_moira_package_exports_find_patterns() -> None:
    from moira import find_patterns
    result = find_patterns([])
    assert result == []


def test_moira_package_exports_build_aspect_graph() -> None:
    from moira import build_aspect_graph, AspectGraph
    g = build_aspect_graph([])
    assert isinstance(g, AspectGraph)


def test_moira_package_exports_aspect_harmonic_profile() -> None:
    from moira import aspect_harmonic_profile, AspectHarmonicProfile
    p = aspect_harmonic_profile([])
    assert isinstance(p, AspectHarmonicProfile)


def test_moira_package_exports_aspect_classification() -> None:
    from moira import AspectClassification, AspectDomain, AspectTier, AspectFamily
    c = AspectClassification(
        domain=AspectDomain.ZODIACAL,
        tier=AspectTier.MAJOR,
        family=AspectFamily.TRINE,
    )
    assert c.domain == AspectDomain.ZODIACAL


def test_moira_package_exports_aspect_graph_node() -> None:
    from moira import AspectGraphNode
    n = AspectGraphNode(name="Sun", degree=0, edges=(), family_counts={})
    assert n.name == "Sun"
    assert n.degree == 0


def test_moira_package_exports_aspect_family_profile() -> None:
    from moira import AspectFamilyProfile, AspectFamily
    p = AspectFamilyProfile(counts={}, total=0, proportions={}, dominant=())
    assert p.total == 0


def test_moira_package_exports_declination_aspect() -> None:
    from moira import DeclinationAspect
    d = DeclinationAspect(
        body1="Sun", body2="Moon", aspect="Parallel",
        dec1=10.0, dec2=10.1,
        orb=0.1, allowed_orb=1.0,
    )
    assert d.is_parallel


def test_aspects_dunder_all_length() -> None:
    assert len(_aspects_module.__all__) == 26


def test_aspects_dunder_all_no_duplicates() -> None:
    names = _aspects_module.__all__
    assert len(names) == len(set(names)), "duplicate entries in __all__"


def test_internal_helpers_not_in_dunder_all() -> None:
    all_set = set(_aspects_module.__all__)
    for name in _EXPECTED_INTERNAL:
        if hasattr(_aspects_module, name):
            assert name not in all_set, f"{name!r} must not appear in __all__"
