from dataclasses import replace

import pytest

from moira.aspects import AspectData
from moira.patterns import (
    AspectPattern,
    PatternAspectContribution,
    PatternAspectRoleKind,
    PatternChartConditionProfile,
    PatternConditionNetworkEdge,
    PatternConditionNetworkNode,
    PatternConditionNetworkProfile,
    PatternConditionProfile,
    PatternConditionState,
    PatternComputationPolicy,
    PatternBodyRoleClassification,
    PatternBodyRoleKind,
    PatternBodyRoleTruth,
    PatternClassification,
    PatternDetectionTruth,
    PatternSelectionPolicy,
    PatternSourceKind,
    PatternSymmetryKind,
    StelliumPolicy,
    all_pattern_contributions,
    find_all_patterns,
    pattern_chart_condition_profile,
    pattern_condition_network_profile,
    pattern_condition_profiles,
    pattern_contributions,
    find_stelliums,
    find_t_squares,
    find_yods,
)


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


def _opp(b1: str, b2: str) -> AspectData:
    return _make_aspect(b1, b2, "Opposition", 180.0, "O")


def _sq(b1: str, b2: str) -> AspectData:
    return _make_aspect(b1, b2, "Square", 90.0, "S")


def _sext(b1: str, b2: str) -> AspectData:
    return _make_aspect(b1, b2, "Sextile", 60.0, "X")


def _qcx(b1: str, b2: str) -> AspectData:
    return _make_aspect(b1, b2, "Quincunx", 150.0, "Q")


def _aspect_signature(aspect: AspectData) -> tuple[str, str, str, float, float, float]:
    bodies = tuple(sorted((aspect.body1, aspect.body2)))
    return (
        bodies[0],
        bodies[1],
        aspect.aspect,
        aspect.angle,
        aspect.orb,
        aspect.allowed_orb,
    )


def _profile_rank(profile: PatternConditionProfile) -> tuple[int, int, int, str, str]:
    state_rank = {
        PatternConditionState.REINFORCED: 2,
        PatternConditionState.MIXED: 1,
        PatternConditionState.WEAKENED: 0,
    }[profile.state]
    return (
        state_rank,
        profile.structured_contribution_count,
        profile.body_count,
        profile.pattern_name,
        profile.detector,
    )


def test_patterns_preserve_legacy_t_square_semantics_while_exposing_detection_truth() -> None:
    aspects = [_opp("Sun", "Moon"), _sq("Sun", "Mars"), _sq("Moon", "Mars")]

    patterns = find_t_squares(aspects)

    assert len(patterns) == 1
    pattern = patterns[0]
    assert pattern.name == "T-Square"
    assert frozenset(pattern.bodies) == {"Sun", "Moon", "Mars"}
    assert pattern.apex in pattern.bodies
    assert {
        (aspect.body1, aspect.body2, aspect.aspect, aspect.angle, aspect.orb)
        for aspect in pattern.aspects
    } == {
        (aspect.body1, aspect.body2, aspect.aspect, aspect.angle, aspect.orb)
        for aspect in aspects
    }

    assert pattern.detection_truth is not None
    assert pattern.classification is not None
    assert pattern.detection_truth.pattern_name == pattern.name
    assert pattern.detection_truth.detector == "find_t_squares"
    assert pattern.detection_truth.source_kind == "aspect"
    assert pattern.detection_truth.orb_factor == 1.0
    assert pattern.classification.pattern_name == pattern.name
    assert pattern.classification.detector == pattern.detection_truth.detector
    assert pattern.classification.source_kind is PatternSourceKind.ASPECT
    assert pattern.classification.symmetry is PatternSymmetryKind.APEX_BEARING
    assert pattern.classification.body_count == 3
    assert pattern.classification.has_apex is True
    body_roles = {role.body: role.role for role in pattern.detection_truth.body_roles}
    assert body_roles[pattern.apex] == "apex"
    assert {body for body, role in body_roles.items() if role == "base"} == (
        set(pattern.bodies) - {pattern.apex}
    )
    assert {
        role.body: role.role for role in pattern.classification.body_roles
    } == {
        role.body: PatternBodyRoleKind(role.role)
        for role in pattern.detection_truth.body_roles
    }


def test_patterns_preserve_stellium_position_truth_without_changing_detection_semantics() -> None:
    positions = {
        "Sun": 10.0,
        "Moon": 12.0,
        "Mars": 14.0,
        "Venus": 80.0,
    }

    patterns = find_stelliums(positions)

    assert len(patterns) == 1
    pattern = patterns[0]
    assert pattern.name == "Stellium"
    assert pattern.bodies == ("Mars", "Moon", "Sun")
    assert pattern.aspects == ()
    assert pattern.apex is None

    assert pattern.detection_truth is not None
    assert pattern.classification is not None
    assert pattern.detection_truth.detector == "find_stelliums"
    assert pattern.detection_truth.source_kind == "position"
    assert pattern.detection_truth.centroid_longitude is not None
    assert pattern.detection_truth.max_body_distance is not None
    assert pattern.detection_truth.orb_limit == pytest.approx(8.0)
    assert pattern.detection_truth.max_body_distance <= pattern.detection_truth.orb_limit
    assert all(role.role == "cluster_member" for role in pattern.detection_truth.body_roles)
    assert pattern.classification.source_kind is PatternSourceKind.POSITION
    assert pattern.classification.symmetry is PatternSymmetryKind.SYMMETRIC
    assert pattern.classification.has_apex is False
    assert all(role.role is PatternBodyRoleKind.CLUSTER_MEMBER for role in pattern.classification.body_roles)


def test_patterns_find_all_patterns_is_deterministic_and_truth_is_internally_consistent() -> None:
    positions = {
        "Sun": 0.0,
        "Moon": 180.0,
        "Mars": 90.0,
    }
    aspects = [_opp("Sun", "Moon"), _sq("Sun", "Mars"), _sq("Moon", "Mars")]

    first = find_all_patterns(positions, aspects=aspects)
    second = find_all_patterns(positions, aspects=aspects)

    assert [
        (
            pattern.name,
            pattern.bodies,
            pattern.apex,
            pattern.detection_truth.detector if pattern.detection_truth else None,
            pattern.classification,
        )
        for pattern in first
    ] == [
        (
            pattern.name,
            pattern.bodies,
            pattern.apex,
            pattern.detection_truth.detector if pattern.detection_truth else None,
            pattern.classification,
        )
        for pattern in second
    ]

    yods = find_yods([_sext("Moon", "Mars"), _qcx("Sun", "Moon"), _qcx("Sun", "Mars")])
    assert len(yods) == 1
    yod = yods[0]
    assert yod.detection_truth is not None
    assert yod.classification is not None
    assert yod.detection_truth.detector == "find_yods"
    assert yod.classification.detector == "find_yods"
    assert yod.classification.source_kind is PatternSourceKind.ASPECT
    assert any(role.role == "apex" and role.body == "Sun" for role in yod.detection_truth.body_roles)
    assert any(role.role is PatternBodyRoleKind.APEX and role.body == "Sun" for role in yod.classification.body_roles)


def test_pattern_vessel_invariants_fail_loudly_on_internal_truth_drift() -> None:
    pattern = find_t_squares([_opp("Sun", "Moon"), _sq("Sun", "Mars"), _sq("Moon", "Mars")])[0]
    assert pattern.detection_truth is not None

    with pytest.raises(ValueError, match="pattern_name must match name"):
        replace(
            pattern,
            detection_truth=replace(pattern.detection_truth, pattern_name="Yod"),
        )

    with pytest.raises(ValueError, match="must preserve an apex body role"):
        replace(
            pattern,
            detection_truth=replace(
                pattern.detection_truth,
                body_roles=(
                    PatternBodyRoleTruth("Moon", "base"),
                    PatternBodyRoleTruth("Sun", "base"),
                    PatternBodyRoleTruth("Mars", "member"),
                ),
            ),
        )

    with pytest.raises(ValueError, match="position-based truth must preserve centroid and spread"):
        PatternDetectionTruth(
            pattern_name="Stellium",
            detector="find_stelliums",
            source_kind="position",
            orb_factor=1.0,
            body_roles=(PatternBodyRoleTruth("Sun", "cluster_member"),),
        )

    with pytest.raises(ValueError, match="apex must be one of bodies"):
        AspectPattern(
            name="T-Square",
            bodies=("Moon", "Sun"),
            aspects=tuple(),
            apex="Mars",
        )

    with pytest.raises(ValueError, match="classification detector must match detection truth"):
        replace(
            pattern,
            classification=replace(pattern.classification, detector="find_yods"),
        )

    with pytest.raises(ValueError, match="has_apex must match body roles"):
        PatternClassification(
            pattern_name="T-Square",
            detector="find_t_squares",
            source_kind=PatternSourceKind.ASPECT,
            symmetry=PatternSymmetryKind.APEX_BEARING,
            body_count=1,
            has_apex=True,
            body_roles=(PatternBodyRoleClassification("Sun", PatternBodyRoleKind.BASE),),
        )


def test_patterns_expose_read_only_inspectability_properties() -> None:
    t_square = find_t_squares([_opp("Sun", "Moon"), _sq("Sun", "Mars"), _sq("Moon", "Mars")])[0]
    stellium = find_stelliums({"Sun": 10.0, "Moon": 12.0, "Mars": 14.0, "Venus": 80.0})[0]

    assert t_square.detector == "find_t_squares"
    assert t_square.source_kind is PatternSourceKind.ASPECT
    assert t_square.symmetry_kind is PatternSymmetryKind.APEX_BEARING
    assert t_square.is_apex_bearing is True
    assert t_square.is_position_based is False
    assert set(t_square.body_role_kinds) == {PatternBodyRoleKind.BASE, PatternBodyRoleKind.APEX}

    assert stellium.detector == "find_stelliums"
    assert stellium.source_kind is PatternSourceKind.POSITION
    assert stellium.symmetry_kind is PatternSymmetryKind.SYMMETRIC
    assert stellium.is_apex_bearing is False
    assert stellium.is_position_based is True
    assert set(stellium.body_role_kinds) == {PatternBodyRoleKind.CLUSTER_MEMBER}

    with pytest.raises((AttributeError, TypeError)):
        setattr(t_square, "detector", "find_yods")


def test_pattern_role_vessels_fail_loudly_on_duplicate_body_roles() -> None:
    with pytest.raises(ValueError, match="body_roles must not repeat bodies"):
        PatternDetectionTruth(
            pattern_name="T-Square",
            detector="find_t_squares",
            source_kind="aspect",
            orb_factor=1.0,
            body_roles=(
                PatternBodyRoleTruth("Sun", "base"),
                PatternBodyRoleTruth("Sun", "apex"),
            ),
        )

    with pytest.raises(ValueError, match="body_roles must not repeat bodies"):
        PatternClassification(
            pattern_name="T-Square",
            detector="find_t_squares",
            source_kind=PatternSourceKind.ASPECT,
            symmetry=PatternSymmetryKind.APEX_BEARING,
            body_count=2,
            has_apex=True,
            body_roles=(
                PatternBodyRoleClassification("Sun", PatternBodyRoleKind.BASE),
                PatternBodyRoleClassification("Sun", PatternBodyRoleKind.APEX),
            ),
        )


def test_patterns_default_policy_preserves_current_behavior() -> None:
    positions = {
        "Sun": 0.0,
        "Moon": 180.0,
        "Mars": 90.0,
        "Venus": 92.0,
    }
    aspects = [_opp("Sun", "Moon"), _sq("Sun", "Mars"), _sq("Moon", "Mars")]

    without_policy = find_all_patterns(positions, aspects=aspects)
    with_default_policy = find_all_patterns(
        positions,
        aspects=aspects,
        policy=PatternComputationPolicy(),
    )

    assert [
        (pattern.name, pattern.bodies, pattern.apex, pattern.classification)
        for pattern in without_policy
    ] == [
        (pattern.name, pattern.bodies, pattern.apex, pattern.classification)
        for pattern in with_default_policy
    ]


def test_patterns_narrow_policy_explicitly_limits_selection_and_stellium_doctrine() -> None:
    positions = {
        "Sun": 10.0,
        "Moon": 12.0,
        "Mars": 14.0,
        "Venus": 80.0,
    }

    default_patterns = find_all_patterns(positions)
    narrow_policy = PatternComputationPolicy(
        selection=PatternSelectionPolicy(include=("Stellium",)),
        stellium=StelliumPolicy(min_bodies=4, orb=8.0),
    )
    narrow_patterns = find_all_patterns(positions, policy=narrow_policy)

    assert any(pattern.name == "Stellium" for pattern in default_patterns)
    assert narrow_patterns == []

    three_body_policy = PatternComputationPolicy(
        selection=PatternSelectionPolicy(include=("Stellium",)),
        stellium=StelliumPolicy(min_bodies=3, orb=8.0),
    )
    three_body_patterns = find_all_patterns(positions, policy=three_body_policy)
    assert [pattern.name for pattern in three_body_patterns] == ["Stellium"]


def test_patterns_policy_surface_is_deterministic_and_validated() -> None:
    positions = {"Sun": 10.0, "Moon": 12.0, "Mars": 14.0}

    first = find_all_patterns(positions, policy=PatternComputationPolicy())
    second = find_all_patterns(positions, policy=PatternComputationPolicy())
    assert first == second

    with pytest.raises(ValueError, match="Pattern orb_factor must be positive"):
        find_all_patterns(positions, policy=PatternComputationPolicy(orb_factor=0.0))

    with pytest.raises(ValueError, match="Pattern stellium min_bodies must be at least 3"):
        find_all_patterns(
            positions,
            policy=PatternComputationPolicy(stellium=StelliumPolicy(min_bodies=2)),
        )

    with pytest.raises(ValueError, match="Unsupported pattern selection policy"):
        find_all_patterns(
            positions,
            policy=replace(PatternComputationPolicy(), selection="invalid"),  # type: ignore[arg-type]
        )

    with pytest.raises(ValueError, match="Pattern selection include must not repeat names"):
        find_all_patterns(
            positions,
            policy=PatternComputationPolicy(
                selection=PatternSelectionPolicy(include=("Stellium", "Stellium")),
            ),
        )

    with pytest.raises(ValueError, match="Unsupported pattern names in selection include"):
        find_all_patterns(
            positions,
            policy=PatternComputationPolicy(
                selection=PatternSelectionPolicy(include=("Unknown Pattern",)),
            ),
        )


def test_patterns_fail_clearly_on_malformed_inputs() -> None:
    with pytest.raises(ValueError, match="Pattern positions must use non-empty body names"):
        find_all_patterns({"": 0.0})

    with pytest.raises(ValueError, match="Pattern positions must use finite longitudes"):
        find_all_patterns({"Sun": float("nan")})

    with pytest.raises(ValueError, match="Pattern aspects must connect two distinct bodies"):
        find_all_patterns(
            {"Sun": 0.0},
            aspects=[_make_aspect("Sun", "Sun", "Conjunction", 0.0, "C")],
        )

    with pytest.raises(ValueError, match="Pattern stellium min_bodies must be at least 3"):
        find_stelliums({"Sun": 0.0, "Moon": 1.0, "Mars": 2.0}, min_bodies=2)


def test_patterns_formalize_contributing_aspect_relations_deterministically() -> None:
    t_square = find_t_squares([_opp("Sun", "Moon"), _sq("Sun", "Mars"), _sq("Moon", "Mars")])[0]
    yod = find_yods([_sext("Moon", "Mars"), _qcx("Sun", "Moon"), _qcx("Sun", "Mars")])[0]
    stellium = find_stelliums({"Sun": 10.0, "Moon": 12.0, "Mars": 14.0, "Venus": 80.0})[0]

    assert len(t_square.contributions) == len(t_square.aspects) == 3
    assert len(t_square.all_contributions) == len(t_square.aspects) == 3
    assert set(t_square.contribution_roles) == {
        PatternAspectRoleKind.BASE_LINK,
        PatternAspectRoleKind.APEX_LINK,
    }
    assert len(yod.contributions) == len(yod.aspects) == 3
    assert set(yod.contribution_roles) == {
        PatternAspectRoleKind.BASE_LINK,
        PatternAspectRoleKind.APEX_LINK,
    }
    assert stellium.contributions == ()

    flat = pattern_contributions([yod, stellium, t_square])
    all_flat = all_pattern_contributions([yod, stellium, t_square])
    assert flat == pattern_contributions([yod, stellium, t_square])
    assert all_flat == all_pattern_contributions([yod, stellium, t_square])
    assert flat == all_flat
    assert [contribution.pattern_name for contribution in flat] == sorted(
        contribution.pattern_name for contribution in flat
    )


def test_pattern_contributions_align_with_source_pattern_truth() -> None:
    pattern = find_t_squares([_opp("Sun", "Moon"), _sq("Sun", "Mars"), _sq("Moon", "Mars")])[0]

    assert pattern.admitted_contributions == pattern.contributions
    assert pattern.all_contributions == pattern.contributions
    assert pattern.contribution_count == pattern.all_contribution_count == len(pattern.aspects)
    assert pattern.has_contributions is True
    assert all(contribution.pattern_name == pattern.name for contribution in pattern.contributions)
    assert {
        _aspect_signature(contribution.aspect)
        for contribution in pattern.contributions
    } == {
        _aspect_signature(aspect)
        for aspect in pattern.aspects
    }
    assert all(
        {contribution.body1, contribution.body2} <= set(pattern.bodies)
        for contribution in pattern.contributions
    )
    assert any(contribution.role is PatternAspectRoleKind.BASE_LINK for contribution in pattern.contributions)
    assert sum(contribution.role is PatternAspectRoleKind.APEX_LINK for contribution in pattern.contributions) == 2
    assert pattern.all_contribution_roles == pattern.contribution_roles

    stellium = find_stelliums({"Sun": 10.0, "Moon": 12.0, "Mars": 14.0, "Venus": 80.0})[0]
    assert stellium.admitted_contributions == ()
    assert stellium.all_contributions == ()
    assert stellium.contribution_count == 0
    assert stellium.all_contribution_count == 0
    assert stellium.has_contributions is False


def test_pattern_contribution_invariants_fail_loudly_on_internal_drift() -> None:
    pattern = find_t_squares([_opp("Sun", "Moon"), _sq("Sun", "Mars"), _sq("Moon", "Mars")])[0]
    contribution = pattern.contributions[0]

    with pytest.raises(ValueError, match="aspect_name must match aspect.aspect"):
        PatternAspectContribution(
            pattern_name=contribution.pattern_name,
            role=contribution.role,
            body1=contribution.body1,
            body2=contribution.body2,
            aspect_name="Trine",
            aspect_angle=contribution.aspect_angle,
            aspect=contribution.aspect,
        )

    with pytest.raises(ValueError, match="contributions must match all_contributions under current doctrine"):
        replace(
            pattern,
            contributions=pattern.contributions[:-1],
        )

    with pytest.raises(ValueError, match="all_contributions must match pattern aspects"):
        replace(
            pattern,
            all_contributions=pattern.all_contributions[:-1],
        )

    with pytest.raises(ValueError, match="all_contributions must not repeat aspects"):
        replace(
            pattern,
            all_contributions=pattern.all_contributions + pattern.all_contributions[:1],
        )


def test_patterns_expose_integrated_condition_profiles_deterministically() -> None:
    t_square = find_t_squares([_opp("Sun", "Moon"), _sq("Sun", "Mars"), _sq("Moon", "Mars")])[0]
    grand_trine_aspects = [
        _make_aspect("Sun", "Moon", "Trine", 120.0, "T"),
        _make_aspect("Sun", "Mars", "Trine", 120.0, "T"),
        _make_aspect("Moon", "Mars", "Trine", 120.0, "T"),
    ]
    grand_trine = find_all_patterns(
        {"Sun": 0.0, "Moon": 120.0, "Mars": 240.0},
        aspects=grand_trine_aspects,
        include=["Grand Trine"],
    )[0]
    stellium = find_stelliums({"Sun": 10.0, "Moon": 12.0, "Mars": 14.0, "Venus": 80.0})[0]

    assert t_square.condition_profile is not None
    assert grand_trine.condition_profile is not None
    assert stellium.condition_profile is not None

    assert t_square.condition_state is PatternConditionState.REINFORCED
    assert grand_trine.condition_state is PatternConditionState.MIXED
    assert stellium.condition_state is PatternConditionState.WEAKENED

    profiles = pattern_condition_profiles([grand_trine, stellium, t_square])
    assert profiles == pattern_condition_profiles([grand_trine, stellium, t_square])
    assert [profile.pattern_name for profile in profiles] == sorted(
        profile.pattern_name for profile in profiles
    )


def test_pattern_condition_profiles_align_with_source_pattern_truth() -> None:
    pattern = find_t_squares([_opp("Sun", "Moon"), _sq("Sun", "Mars"), _sq("Moon", "Mars")])[0]

    assert pattern.condition_profile is not None
    assert pattern.condition_profile.pattern_name == pattern.name
    assert pattern.condition_profile.detector == pattern.classification.detector
    assert pattern.condition_profile.source_kind is pattern.classification.source_kind
    assert pattern.condition_profile.symmetry is pattern.classification.symmetry
    assert pattern.condition_profile.body_count == len(pattern.bodies)
    assert pattern.condition_profile.has_apex is True
    assert pattern.condition_profile.contribution_count == pattern.contribution_count
    assert pattern.condition_profile.all_contribution_count == pattern.all_contribution_count
    assert pattern.condition_profile.structured_contribution_count == 3
    assert pattern.condition_profile.generic_contribution_count == 0

    stellium = find_stelliums({"Sun": 10.0, "Moon": 12.0, "Mars": 14.0, "Venus": 80.0})[0]
    assert stellium.condition_profile is not None
    assert stellium.condition_profile.contribution_count == 0
    assert stellium.condition_profile.all_contribution_count == 0
    assert stellium.condition_profile.structured_contribution_count == 0
    assert stellium.condition_profile.generic_contribution_count == 0
    assert stellium.condition_profile.state is PatternConditionState.WEAKENED


def test_pattern_condition_profile_invariants_fail_loudly_on_internal_drift() -> None:
    pattern = find_t_squares([_opp("Sun", "Moon"), _sq("Sun", "Mars"), _sq("Moon", "Mars")])[0]
    assert pattern.condition_profile is not None

    with pytest.raises(ValueError, match="condition_profile detector must match classification"):
        replace(
            pattern,
            condition_profile=replace(pattern.condition_profile, detector="find_yods"),
        )

    with pytest.raises(ValueError, match="condition_profile structured_contribution_count must match contributions"):
        replace(
            pattern,
            condition_profile=replace(pattern.condition_profile, structured_contribution_count=1, generic_contribution_count=2),
        )

    with pytest.raises(ValueError, match="contribution role counts must cover all_contributions"):
        PatternConditionProfile(
            pattern_name="Stellium",
            detector="find_stelliums",
            source_kind=PatternSourceKind.POSITION,
            symmetry=PatternSymmetryKind.SYMMETRIC,
            body_count=3,
            has_apex=False,
            contribution_count=0,
            all_contribution_count=1,
            structured_contribution_count=0,
            generic_contribution_count=0,
            state=PatternConditionState.WEAKENED,
        )


def test_patterns_expose_chart_condition_profile_deterministically() -> None:
    positions = {
        "Sun": 0.0,
        "Moon": 180.0,
        "Mars": 90.0,
        "Venus": 10.0,
        "Mercury": 12.0,
        "Jupiter": 14.0,
    }
    aspects = [_opp("Sun", "Moon"), _sq("Sun", "Mars"), _sq("Moon", "Mars")]
    patterns = find_all_patterns(positions, aspects=aspects)

    chart = pattern_chart_condition_profile(patterns)

    assert chart == pattern_chart_condition_profile(patterns)
    assert chart.profile_count == len(chart.profiles)
    assert chart.reinforced_count + chart.mixed_count + chart.weakened_count == chart.profile_count
    assert chart.profiles == tuple(sorted(chart.profiles, key=lambda profile: (profile.pattern_name, profile.detector, profile.body_count)))


def test_pattern_chart_condition_profile_aligns_with_source_profiles() -> None:
    positions = {
        "Sun": 0.0,
        "Moon": 180.0,
        "Mars": 90.0,
        "Venus": 10.0,
        "Mercury": 12.0,
        "Jupiter": 14.0,
    }
    aspects = [_opp("Sun", "Moon"), _sq("Sun", "Mars"), _sq("Moon", "Mars")]
    patterns = find_all_patterns(positions, aspects=aspects)
    chart = pattern_chart_condition_profile(patterns)

    assert chart.structured_contribution_total == sum(
        profile.structured_contribution_count
        for profile in chart.profiles
    )
    assert chart.generic_contribution_total == sum(
        profile.generic_contribution_count
        for profile in chart.profiles
    )
    strongest_rank = max(_profile_rank(profile) for profile in chart.profiles)
    weakest_rank = min(_profile_rank(profile) for profile in chart.profiles)
    assert chart.strongest_patterns == tuple(sorted(
        profile.pattern_name
        for profile in chart.profiles
        if _profile_rank(profile) == strongest_rank
    ))
    assert chart.weakest_patterns == tuple(sorted(
        profile.pattern_name
        for profile in chart.profiles
        if _profile_rank(profile) == weakest_rank
    ))
    assert chart.strongest_count == len(chart.strongest_patterns)
    assert chart.weakest_count == len(chart.weakest_patterns)


def test_pattern_chart_condition_profile_invariants_fail_loudly_on_internal_drift() -> None:
    positions = {
        "Sun": 0.0,
        "Moon": 180.0,
        "Mars": 90.0,
        "Venus": 10.0,
        "Mercury": 12.0,
        "Jupiter": 14.0,
    }
    aspects = [_opp("Sun", "Moon"), _sq("Sun", "Mars"), _sq("Moon", "Mars")]
    chart = pattern_chart_condition_profile(find_all_patterns(positions, aspects=aspects))

    with pytest.raises(ValueError, match="state counts must cover profiles"):
        PatternChartConditionProfile(
            profiles=chart.profiles,
            reinforced_count=chart.reinforced_count,
            mixed_count=chart.mixed_count,
            weakened_count=0,
            structured_contribution_total=chart.structured_contribution_total,
            generic_contribution_total=chart.generic_contribution_total,
            strongest_patterns=chart.strongest_patterns,
            weakest_patterns=chart.weakest_patterns,
        )

    with pytest.raises(ValueError, match="profiles must be deterministically ordered"):
        PatternChartConditionProfile(
            profiles=tuple(reversed(chart.profiles)),
            reinforced_count=chart.reinforced_count,
            mixed_count=chart.mixed_count,
            weakened_count=chart.weakened_count,
            structured_contribution_total=chart.structured_contribution_total,
            generic_contribution_total=chart.generic_contribution_total,
            strongest_patterns=chart.strongest_patterns,
            weakest_patterns=chart.weakest_patterns,
        )

    with pytest.raises(ValueError, match="strongest_patterns must match profiles"):
        PatternChartConditionProfile(
            profiles=chart.profiles,
            reinforced_count=chart.reinforced_count,
            mixed_count=chart.mixed_count,
            weakened_count=chart.weakened_count,
            structured_contribution_total=chart.structured_contribution_total,
            generic_contribution_total=chart.generic_contribution_total,
            strongest_patterns=("Stellium",),
            weakest_patterns=chart.weakest_patterns,
        )


def test_patterns_expose_condition_network_profile_deterministically() -> None:
    positions = {
        "Sun": 0.0,
        "Moon": 180.0,
        "Mars": 90.0,
        "Venus": 10.0,
        "Mercury": 12.0,
        "Jupiter": 14.0,
    }
    aspects = [_opp("Sun", "Moon"), _sq("Sun", "Mars"), _sq("Moon", "Mars")]
    patterns = find_all_patterns(positions, aspects=aspects)

    network = pattern_condition_network_profile(patterns)

    assert network == pattern_condition_network_profile(patterns)
    assert network.node_count == len(network.nodes)
    assert network.edge_count == len(network.edges)
    assert network.nodes == tuple(sorted(network.nodes, key=lambda node: (node.kind, node.label, node.node_id)))
    assert network.edges == tuple(sorted(
        network.edges,
        key=lambda edge: (edge.pattern_name, edge.source_id, edge.target_id, edge.role.value),
    ))


def test_pattern_condition_network_aligns_with_source_pattern_truth() -> None:
    positions = {
        "Sun": 0.0,
        "Moon": 180.0,
        "Mars": 90.0,
        "Venus": 10.0,
        "Mercury": 12.0,
        "Jupiter": 14.0,
    }
    aspects = [_opp("Sun", "Moon"), _sq("Sun", "Mars"), _sq("Moon", "Mars")]
    patterns = find_all_patterns(positions, aspects=aspects)
    network = pattern_condition_network_profile(patterns)

    assert network.edge_count == sum(len(pattern.bodies) for pattern in patterns)
    assert network.node_count == len(patterns) + len({
        body
        for pattern in patterns
        for body in pattern.bodies
    })
    assert network.isolated_bodies == ()
    assert "Sun" in network.most_connected_nodes

    body_nodes = {node.label: node for node in network.nodes if node.kind == "body"}
    assert body_nodes["Sun"].incoming_count >= 1
    assert body_nodes["Sun"].outgoing_count == 0
    assert len({node.node_id for node in network.nodes}) == network.node_count


def test_pattern_condition_network_invariants_fail_loudly_on_internal_drift() -> None:
    node = PatternConditionNetworkNode(
        node_id="body:Sun",
        kind="body",
        label="Sun",
        incoming_count=1,
        outgoing_count=0,
        total_degree=1,
    )
    edge = PatternConditionNetworkEdge(
        source_id="pattern:T-Square",
        target_id="body:Sun",
        pattern_name="T-Square",
        role=PatternBodyRoleKind.APEX,
    )

    with pytest.raises(ValueError, match="kind must be 'pattern' or 'body'"):
        PatternConditionNetworkNode(
            node_id="x",
            kind="invalid",
            label="x",
            incoming_count=0,
            outgoing_count=0,
            total_degree=0,
        )

    with pytest.raises(ValueError, match="source_id and target_id must differ"):
        PatternConditionNetworkEdge(
            source_id="body:Sun",
            target_id="body:Sun",
            pattern_name="T-Square",
            role=PatternBodyRoleKind.APEX,
        )

    with pytest.raises(ValueError, match="nodes must be deterministically ordered"):
        PatternConditionNetworkProfile(
            nodes=(node, PatternConditionNetworkNode(
                node_id="body:Mars",
                kind="body",
                label="Mars",
                incoming_count=1,
                outgoing_count=0,
                total_degree=1,
            )),
            edges=(edge,),
            isolated_bodies=(),
            most_connected_nodes=("Sun",),
        )

    with pytest.raises(ValueError, match="node ids must be unique"):
        PatternConditionNetworkProfile(
            nodes=(replace(node, label="Sol"), node),
            edges=(),
            isolated_bodies=("Sol", "Sun"),
            most_connected_nodes=(),
        )

    with pytest.raises(ValueError, match="edges must reference existing nodes"):
        PatternConditionNetworkProfile(
            nodes=(node,),
            edges=(edge,),
            isolated_bodies=(),
            most_connected_nodes=("Sun",),
        )
