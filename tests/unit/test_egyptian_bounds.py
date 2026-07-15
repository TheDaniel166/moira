import pytest

from moira.egyptian_bounds import (
    BOUNDS_SOURCE_CITATIONS,
    BOUND_RULERS,
    BoundHostNature,
    CHALDEAN_DAY_BOUNDS,
    CHALDEAN_NIGHT_BOUNDS,
    EGYPTIAN_BOUNDS,
    PTOLEMAIC_BOUNDS,
    EgyptianBoundClassification,
    EgyptianBoundConditionProfile,
    EgyptianBoundConditionState,
    EgyptianBoundsDoctrine,
    EgyptianBoundsPolicy,
    EgyptianBoundsAggregateProfile,
    EgyptianBoundNetworkMode,
    EgyptianBoundsNetworkEdge,
    EgyptianBoundsNetworkNode,
    EgyptianBoundsNetworkProfile,
    EgyptianBoundRelation,
    EgyptianBoundRelationKind,
    EgyptianBoundRelationProfile,
    EgyptianBoundSegment,
    EgyptianBoundTruth,
    bound_ruler,
    classify_egyptian_bound,
    egyptian_bound_of,
    evaluate_egyptian_bound_condition,
    evaluate_egyptian_bounds_aggregate,
    evaluate_egyptian_bounds_network,
    evaluate_egyptian_bound_relations,
    is_in_own_egyptian_bound,
    relate_planet_to_egyptian_bound,
)


def test_bound_table_has_twelve_signs():
    assert len(EGYPTIAN_BOUNDS) == 12


def test_each_sign_has_five_contiguous_segments_covering_thirty_degrees():
    for sign, bounds in EGYPTIAN_BOUNDS.items():
        assert len(bounds) == 5, sign
        assert sum(end - start for _, start, end in bounds) == 30, sign
        for index, (ruler, start, end) in enumerate(bounds):
            assert ruler in BOUND_RULERS, (sign, ruler)
            assert start < end, (sign, start, end)
            if index == 0:
                assert start == 0, sign
            else:
                assert bounds[index - 1][2] == start, sign
        assert bounds[-1][2] == 30, sign


def test_all_admitted_bounds_tables_cover_each_sign_without_gaps():
    for doctrine, table in (
        (EgyptianBoundsDoctrine.EGYPTIAN, EGYPTIAN_BOUNDS),
        (EgyptianBoundsDoctrine.PTOLEMAIC, PTOLEMAIC_BOUNDS),
        (EgyptianBoundsDoctrine.CHALDEAN_DAY, CHALDEAN_DAY_BOUNDS),
        (EgyptianBoundsDoctrine.CHALDEAN_NIGHT, CHALDEAN_NIGHT_BOUNDS),
    ):
        assert set(table) == set(EGYPTIAN_BOUNDS), doctrine
        for sign, bounds in table.items():
            assert len(bounds) == 5, (doctrine, sign)
            assert bounds[0][1] == 0, (doctrine, sign)
            assert bounds[-1][2] == 30, (doctrine, sign)
            assert all(
                previous[2] == current[1]
                for previous, current in zip(bounds, bounds[1:])
            ), (doctrine, sign)


def test_ptolemaic_table_matches_robbins_transmitted_table():
    assert PTOLEMAIC_BOUNDS == {
        "Aries": [("Jupiter", 0, 6), ("Venus", 6, 14), ("Mercury", 14, 21), ("Mars", 21, 26), ("Saturn", 26, 30)],
        "Taurus": [("Venus", 0, 8), ("Mercury", 8, 15), ("Jupiter", 15, 22), ("Saturn", 22, 24), ("Mars", 24, 30)],
        "Gemini": [("Mercury", 0, 7), ("Jupiter", 7, 13), ("Venus", 13, 20), ("Mars", 20, 26), ("Saturn", 26, 30)],
        "Cancer": [("Mars", 0, 6), ("Jupiter", 6, 13), ("Mercury", 13, 20), ("Venus", 20, 27), ("Saturn", 27, 30)],
        "Leo": [("Jupiter", 0, 6), ("Mercury", 6, 13), ("Saturn", 13, 19), ("Venus", 19, 25), ("Mars", 25, 30)],
        "Virgo": [("Mercury", 0, 7), ("Venus", 7, 13), ("Jupiter", 13, 18), ("Saturn", 18, 24), ("Mars", 24, 30)],
        "Libra": [("Saturn", 0, 6), ("Venus", 6, 11), ("Mercury", 11, 16), ("Jupiter", 16, 24), ("Mars", 24, 30)],
        "Scorpio": [("Mars", 0, 6), ("Venus", 6, 13), ("Jupiter", 13, 21), ("Mercury", 21, 27), ("Saturn", 27, 30)],
        "Sagittarius": [("Jupiter", 0, 8), ("Venus", 8, 14), ("Mercury", 14, 19), ("Saturn", 19, 25), ("Mars", 25, 30)],
        "Capricorn": [("Venus", 0, 6), ("Mercury", 6, 12), ("Jupiter", 12, 19), ("Saturn", 19, 25), ("Mars", 25, 30)],
        "Aquarius": [("Saturn", 0, 6), ("Mercury", 6, 12), ("Venus", 12, 20), ("Jupiter", 20, 25), ("Mars", 25, 30)],
        "Pisces": [("Venus", 0, 8), ("Jupiter", 8, 14), ("Mercury", 14, 20), ("Mars", 20, 25), ("Saturn", 25, 30)],
    }
    assert PTOLEMAIC_BOUNDS != EGYPTIAN_BOUNDS


def test_ptolemaic_global_totals_match_robbins_table_totals():
    totals = {ruler: 0 for ruler in BOUND_RULERS}
    for bounds in PTOLEMAIC_BOUNDS.values():
        for ruler, start, end in bounds:
            totals[ruler] += end - start
    assert totals == {
        "Saturn": 57,
        "Jupiter": 79,
        "Mars": 66,
        "Venus": 82,
        "Mercury": 76,
    }


def test_chaldaean_tables_preserve_sect_order_and_source_totals():
    expected_totals = {
        EgyptianBoundsDoctrine.CHALDEAN_DAY: {
            "Saturn": 78, "Jupiter": 72, "Mars": 69, "Venus": 75, "Mercury": 66,
        },
        EgyptianBoundsDoctrine.CHALDEAN_NIGHT: {
            "Saturn": 66, "Jupiter": 72, "Mars": 69, "Venus": 75, "Mercury": 78,
        },
    }
    for doctrine, table in (
        (EgyptianBoundsDoctrine.CHALDEAN_DAY, CHALDEAN_DAY_BOUNDS),
        (EgyptianBoundsDoctrine.CHALDEAN_NIGHT, CHALDEAN_NIGHT_BOUNDS),
    ):
        totals = {ruler: 0 for ruler in BOUND_RULERS}
        for bounds in table.values():
            assert [end - start for _, start, end in bounds] == [8, 7, 6, 5, 4]
            for ruler, start, end in bounds:
                totals[ruler] += end - start
        assert totals == expected_totals[doctrine]

    assert CHALDEAN_DAY_BOUNDS["Aries"][2][0] == "Saturn"
    assert CHALDEAN_NIGHT_BOUNDS["Aries"][2][0] == "Mercury"


def test_chaldaean_triplicity_orders_match_ptolemys_rotation_rule():
    expected_orders = {
        EgyptianBoundsDoctrine.CHALDEAN_DAY: (
            ("Jupiter", "Venus", "Saturn", "Mercury", "Mars"),
            ("Venus", "Saturn", "Mercury", "Mars", "Jupiter"),
            ("Saturn", "Mercury", "Mars", "Jupiter", "Venus"),
            ("Mars", "Jupiter", "Venus", "Saturn", "Mercury"),
        ),
        EgyptianBoundsDoctrine.CHALDEAN_NIGHT: (
            ("Jupiter", "Venus", "Mercury", "Saturn", "Mars"),
            ("Venus", "Mercury", "Saturn", "Mars", "Jupiter"),
            ("Mercury", "Saturn", "Mars", "Jupiter", "Venus"),
            ("Mars", "Jupiter", "Venus", "Mercury", "Saturn"),
        ),
    }
    triplicities = (
        ("Aries", "Leo", "Sagittarius"),
        ("Taurus", "Virgo", "Capricorn"),
        ("Gemini", "Libra", "Aquarius"),
        ("Cancer", "Scorpio", "Pisces"),
    )
    for doctrine, table in (
        (EgyptianBoundsDoctrine.CHALDEAN_DAY, CHALDEAN_DAY_BOUNDS),
        (EgyptianBoundsDoctrine.CHALDEAN_NIGHT, CHALDEAN_NIGHT_BOUNDS),
    ):
        for signs, expected_order in zip(triplicities, expected_orders[doctrine]):
            for sign in signs:
                assert tuple(ruler for ruler, _, _ in table[sign]) == expected_order


def test_non_egyptian_lookup_boundaries_and_source_citations_are_explicit():
    ptolemaic = EgyptianBoundsPolicy(EgyptianBoundsDoctrine.PTOLEMAIC)
    chaldaean_day = EgyptianBoundsPolicy(EgyptianBoundsDoctrine.CHALDEAN_DAY)
    chaldaean_night = EgyptianBoundsPolicy(EgyptianBoundsDoctrine.CHALDEAN_NIGHT)

    assert bound_ruler(13.999999, policy=ptolemaic) == "Venus"
    assert bound_ruler(14.0, policy=ptolemaic) == "Mercury"
    assert bound_ruler(15.0, policy=chaldaean_day) == "Saturn"
    assert bound_ruler(15.0, policy=chaldaean_night) == "Mercury"
    assert egyptian_bound_of(15.0, policy=ptolemaic).source_citation == (
        BOUNDS_SOURCE_CITATIONS[EgyptianBoundsDoctrine.PTOLEMAIC]
    )


def test_lookup_respects_left_closed_right_open_boundaries():
    assert bound_ruler(0.0) == "Jupiter"
    assert bound_ruler(11.999999) == "Venus"
    assert bound_ruler(12.0) == "Mercury"
    assert bound_ruler(359.999999) == "Saturn"


def test_lookup_wraps_longitude_mod_360():
    assert egyptian_bound_of(-0.5).sign == "Pisces"
    assert egyptian_bound_of(360.0).sign == "Aries"
    assert bound_ruler(390.0) == "Venus"


def test_truth_preserves_segment_geometry():
    truth = egyptian_bound_of(219.5)  # 9.5 Scorpio
    assert truth.doctrine is EgyptianBoundsDoctrine.EGYPTIAN
    assert truth.sign == "Scorpio"
    assert truth.degree_in_sign == 9.5
    assert truth.ruler == "Venus"
    assert truth.segment_start_degree == 7
    assert truth.segment_end_degree == 11
    assert truth.segment_width == 4
    assert truth.segment_range == (7, 11)


def test_classification_reports_own_bound_and_host_nature():
    own = classify_egyptian_bound("Venus", 10.0)
    assert own.own_bound is True
    assert own.host_nature is BoundHostNature.BENEFIC
    assert own.hosted_by_benefic is True
    assert own.hosted_by_malefic is False
    assert is_in_own_egyptian_bound("Venus", 10.0) is True

    foreign = classify_egyptian_bound("Venus", 234.0)
    assert foreign.truth.sign == "Scorpio"
    assert foreign.truth.ruler == "Saturn"
    assert foreign.own_bound is False
    assert foreign.host_nature is BoundHostNature.MALEFIC
    assert foreign.hosted_by_malefic is True


def test_classification_can_report_host_sect():
    saturn_day = classify_egyptian_bound("Moon", 180.0, is_day_chart=True)
    saturn_night = classify_egyptian_bound("Moon", 180.0, is_day_chart=False)
    assert saturn_day.truth.ruler == "Saturn"
    assert saturn_day.host_in_sect is True
    assert saturn_night.host_in_sect is False


def test_explicit_policy_matches_default_policy():
    explicit = EgyptianBoundsPolicy(doctrine=EgyptianBoundsDoctrine.EGYPTIAN)
    default_truth = egyptian_bound_of(95.25)
    explicit_truth = egyptian_bound_of(95.25, policy=explicit)
    assert explicit_truth == default_truth
    assert bound_ruler(95.25, policy=explicit) == bound_ruler(95.25)
    classified = classify_egyptian_bound("Mars", 95.25, policy=explicit)
    assert classified.truth.doctrine is EgyptianBoundsDoctrine.EGYPTIAN


def test_relation_formalizes_guest_host_structure():
    own = relate_planet_to_egyptian_bound("Venus", 10.0)
    assert own.host_ruler == "Venus"
    assert own.relation_kind is EgyptianBoundRelationKind.SELF_HOSTED
    assert own.own_bound is True

    benefic = relate_planet_to_egyptian_bound("Mars", 109.25)
    assert benefic.host_ruler == "Jupiter"
    assert benefic.relation_kind is EgyptianBoundRelationKind.HOSTED_BY_BENEFIC
    assert benefic.hosted_by_benefic is True

    neutral = relate_planet_to_egyptian_bound("Venus", 15.0)
    assert neutral.host_ruler == "Mercury"
    assert neutral.relation_kind is EgyptianBoundRelationKind.HOSTED_BY_NEUTRAL
    assert neutral.hosted_by_neutral is True

    malefic = relate_planet_to_egyptian_bound("Venus", 234.0, is_day_chart=False)
    assert malefic.host_ruler == "Saturn"
    assert malefic.relation_kind is EgyptianBoundRelationKind.HOSTED_BY_MALEFIC
    assert malefic.hosted_by_malefic is True
    assert malefic.host_in_sect is False


def test_relation_profile_distinguishes_detected_admitted_and_scored():
    own = evaluate_egyptian_bound_relations("Venus", 10.0)
    assert own.detected_relation.own_bound is True
    assert own.has_detected_relation is True
    assert own.has_admitted_relation is True
    assert own.has_scored_relation is True
    assert own.detected_relation_kind is EgyptianBoundRelationKind.SELF_HOSTED
    assert own.admitted_relation_kinds == (EgyptianBoundRelationKind.SELF_HOSTED,)
    assert own.scored_relation_kinds == (EgyptianBoundRelationKind.SELF_HOSTED,)

    foreign = evaluate_egyptian_bound_relations("Venus", 234.0)
    assert foreign.detected_relation.relation_kind is EgyptianBoundRelationKind.HOSTED_BY_MALEFIC
    assert foreign.has_detected_relation is True
    assert foreign.has_admitted_relation is True
    assert foreign.has_scored_relation is False
    assert foreign.admitted_relation_kinds == (EgyptianBoundRelationKind.HOSTED_BY_MALEFIC,)
    assert foreign.scored_relation_kinds == ()


def test_condition_profile_integrates_local_bound_state():
    self_governed = evaluate_egyptian_bound_condition("Venus", 10.0)
    assert self_governed.state is EgyptianBoundConditionState.SELF_GOVERNED
    assert self_governed.is_self_governed is True
    assert self_governed.strengthening_count == 1
    assert self_governed.weakening_count == 0
    assert self_governed.neutral_count == 0

    supported = evaluate_egyptian_bound_condition("Mars", 109.25)
    assert supported.state is EgyptianBoundConditionState.SUPPORTED
    assert supported.is_supported is True

    mediated = evaluate_egyptian_bound_condition("Venus", 15.0)
    assert mediated.state is EgyptianBoundConditionState.MEDIATED
    assert mediated.is_mediated is True
    assert mediated.neutral_count == 1

    constrained = evaluate_egyptian_bound_condition("Venus", 234.0)
    assert constrained.state is EgyptianBoundConditionState.CONSTRAINED
    assert constrained.is_constrained is True
    assert constrained.weakening_count == 1


def test_aggregate_profile_summarizes_local_bound_conditions():
    profiles = [
        evaluate_egyptian_bound_condition("Mars", 109.25),
        evaluate_egyptian_bound_condition("Venus", 10.0),
        evaluate_egyptian_bound_condition("Moon", 180.0),
        evaluate_egyptian_bound_condition("Sun", 15.0),
    ]
    aggregate = evaluate_egyptian_bounds_aggregate(profiles)
    assert tuple(profile.planet for profile in aggregate.profiles) == ("Sun", "Moon", "Venus", "Mars")
    assert aggregate.self_governed_count == 1
    assert aggregate.supported_count == 1
    assert aggregate.mediated_count == 1
    assert aggregate.constrained_count == 1
    assert aggregate.strengthening_total == 2
    assert aggregate.weakening_total == 1
    assert aggregate.neutral_total == 1
    assert aggregate.strongest_planets == ("Venus",)
    assert aggregate.weakest_planets == ("Moon",)
    assert aggregate.strongest_count == 1
    assert aggregate.weakest_count == 1


def test_network_profile_projects_guest_host_relations():
    aggregate = evaluate_egyptian_bounds_aggregate(
        [
            evaluate_egyptian_bound_condition("Mercury", 62.0),
            evaluate_egyptian_bound_condition("Venus", 211.0),
            evaluate_egyptian_bound_condition("Mars", 32.0),
            evaluate_egyptian_bound_condition("Moon", 180.0),
            evaluate_egyptian_bound_condition("Saturn", 32.0),
        ]
    )
    network = evaluate_egyptian_bounds_network(aggregate)
    assert network.node_count == 5
    assert network.edge_count == 4
    assert network.mutual_edge_count == 2
    assert network.unilateral_edge_count == 2
    assert network.isolated_planets == ("Mercury",)
    assert network.most_connected_planets == ("Venus",)

    edge_map = {(edge.source_planet, edge.target_planet): edge for edge in network.edges}
    assert edge_map[("Venus", "Mars")].mode is EgyptianBoundNetworkMode.MUTUAL
    assert edge_map[("Mars", "Venus")].mode is EgyptianBoundNetworkMode.MUTUAL
    assert edge_map[("Moon", "Saturn")].mode is EgyptianBoundNetworkMode.UNILATERAL
    assert edge_map[("Saturn", "Venus")].mode is EgyptianBoundNetworkMode.UNILATERAL

    node_map = {node.planet: node for node in network.nodes}
    assert node_map["Mercury"].is_isolated is True
    assert node_map["Venus"].incoming_count == 2
    assert node_map["Venus"].outgoing_count == 1
    assert node_map["Venus"].total_degree == 3


def test_segment_invariants_are_enforced():
    with pytest.raises(ValueError):
        EgyptianBoundSegment(sign="Ophiuchus", ruler="Venus", start_degree=0, end_degree=5)
    with pytest.raises(ValueError):
        EgyptianBoundSegment(sign="Aries", ruler="Sun", start_degree=0, end_degree=5)
    with pytest.raises(ValueError):
        EgyptianBoundSegment(sign="Aries", ruler="Venus", start_degree=8, end_degree=4)


def test_truth_invariants_are_enforced():
    segment = EgyptianBoundSegment(sign="Aries", ruler="Jupiter", start_degree=0, end_degree=6)
    with pytest.raises(ValueError):
        EgyptianBoundTruth(
            longitude=360.0,
            doctrine=EgyptianBoundsDoctrine.EGYPTIAN,
            sign="Aries",
            sign_index=0,
            degree_in_sign=1.0,
            segment=segment,
        )
    with pytest.raises(ValueError):
        EgyptianBoundTruth(
            longitude=1.0,
            doctrine=EgyptianBoundsDoctrine.EGYPTIAN,
            sign="Taurus",
            sign_index=0,
            degree_in_sign=1.0,
            segment=segment,
        )
    with pytest.raises(ValueError):
        EgyptianBoundTruth(
            longitude=1.0,
            doctrine=EgyptianBoundsDoctrine.EGYPTIAN,
            sign="Aries",
            sign_index=0,
            degree_in_sign=8.0,
            segment=segment,
        )


def test_classification_invariants_are_enforced():
    truth = egyptian_bound_of(10.0)
    with pytest.raises(ValueError):
        EgyptianBoundClassification(
            planet="Venus",
            truth=truth,
            own_bound=False,
            host_nature=BoundHostNature.BENEFIC,
            host_in_sect=None,
        )
    with pytest.raises(ValueError):
        EgyptianBoundClassification(
            planet="Venus",
            truth=truth,
            own_bound=True,
            host_nature=BoundHostNature.MALEFIC,
            host_in_sect=None,
        )


def test_relation_invariants_are_enforced():
    truth = egyptian_bound_of(10.0)
    with pytest.raises(ValueError):
        EgyptianBoundRelation(
            guest_planet="Venus",
            host_ruler="Mars",
            truth=truth,
            relation_kind=EgyptianBoundRelationKind.SELF_HOSTED,
            host_nature=BoundHostNature.BENEFIC,
            host_in_sect=None,
        )
    with pytest.raises(ValueError):
        EgyptianBoundRelation(
            guest_planet="Venus",
            host_ruler="Venus",
            truth=truth,
            relation_kind=EgyptianBoundRelationKind.HOSTED_BY_BENEFIC,
            host_nature=BoundHostNature.BENEFIC,
            host_in_sect=None,
        )


def test_relation_profile_invariants_are_enforced():
    relation = relate_planet_to_egyptian_bound("Venus", 10.0)
    with pytest.raises(ValueError):
        EgyptianBoundRelationProfile(
            planet="Mars",
            truth=relation.truth,
            detected_relation=relation,
            admitted_relations=(relation,),
            scored_relations=(relation,),
        )
    with pytest.raises(ValueError):
        EgyptianBoundRelationProfile(
            planet="Venus",
            truth=relation.truth,
            detected_relation=relation,
            admitted_relations=(),
            scored_relations=(relation,),
        )


def test_condition_profile_invariants_are_enforced():
    classification = classify_egyptian_bound("Venus", 10.0)
    relation_profile = evaluate_egyptian_bound_relations("Venus", 10.0)
    with pytest.raises(ValueError):
        EgyptianBoundConditionProfile(
            planet="Mars",
            truth=classification.truth,
            classification=classification,
            relation_profile=relation_profile,
            strengthening_count=1,
            weakening_count=0,
            neutral_count=0,
            state=EgyptianBoundConditionState.SELF_GOVERNED,
        )
    with pytest.raises(ValueError):
        EgyptianBoundConditionProfile(
            planet="Venus",
            truth=classification.truth,
            classification=classification,
            relation_profile=relation_profile,
            strengthening_count=0,
            weakening_count=1,
            neutral_count=0,
            state=EgyptianBoundConditionState.SELF_GOVERNED,
        )


def test_aggregate_profile_invariants_are_enforced():
    venus = evaluate_egyptian_bound_condition("Venus", 10.0)
    mars = evaluate_egyptian_bound_condition("Mars", 95.25)
    with pytest.raises(ValueError):
        EgyptianBoundsAggregateProfile(
            profiles=(mars, venus),
            self_governed_count=1,
            supported_count=1,
            mediated_count=0,
            constrained_count=0,
            strengthening_total=2,
            weakening_total=0,
            neutral_total=0,
            strongest_planets=("Venus",),
            weakest_planets=("Mars",),
        )
    with pytest.raises(ValueError):
        EgyptianBoundsAggregateProfile(
            profiles=(venus, venus),
            self_governed_count=2,
            supported_count=0,
            mediated_count=0,
            constrained_count=0,
            strengthening_total=2,
            weakening_total=0,
            neutral_total=0,
            strongest_planets=("Venus",),
            weakest_planets=("Venus",),
        )
    with pytest.raises(ValueError):
        EgyptianBoundsAggregateProfile(
            profiles=(venus, mars),
            self_governed_count=1,
            supported_count=1,
            mediated_count=0,
            constrained_count=0,
            strengthening_total=2,
            weakening_total=0,
            neutral_total=0,
            strongest_planets=("Mars",),
            weakest_planets=("Venus",),
        )


def test_network_invariants_are_enforced():
    mercury = evaluate_egyptian_bound_condition("Mercury", 62.0)
    node = EgyptianBoundsNetworkNode(
        planet="Mercury",
        profile=mercury,
        incoming_count=0,
        outgoing_count=0,
        mutual_count=0,
        total_degree=0,
    )
    with pytest.raises(ValueError):
        EgyptianBoundsNetworkEdge(
            source_planet="Venus",
            target_planet="Venus",
            relation_kind=EgyptianBoundRelationKind.SELF_HOSTED,
            mode=EgyptianBoundNetworkMode.UNILATERAL,
        )
    with pytest.raises(ValueError):
        EgyptianBoundsNetworkProfile(
            nodes=(node,),
            edges=(),
            isolated_planets=(),
            most_connected_planets=(),
            mutual_edge_count=0,
            unilateral_edge_count=0,
        )
    with pytest.raises(ValueError):
        EgyptianBoundsNetworkProfile(
            nodes=(node, node),
            edges=(),
            isolated_planets=("Mercury", "Mercury"),
            most_connected_planets=(),
            mutual_edge_count=0,
            unilateral_edge_count=0,
        )
    edge = EgyptianBoundsNetworkEdge(
        source_planet="Moon",
        target_planet="Saturn",
        relation_kind=EgyptianBoundRelationKind.HOSTED_BY_MALEFIC,
        mode=EgyptianBoundNetworkMode.UNILATERAL,
    )
    with pytest.raises(ValueError):
        EgyptianBoundsNetworkProfile(
            nodes=(node,),
            edges=(edge,),
            isolated_planets=(),
            most_connected_planets=("Mercury",),
            mutual_edge_count=0,
            unilateral_edge_count=1,
        )


def test_policy_rejects_unsupported_doctrine_shape():
    with pytest.raises(ValueError):
        EgyptianBoundsPolicy(doctrine="ptolemaic")  # type: ignore[arg-type]
    venus = evaluate_egyptian_bound_condition("Venus", 10.0)
    mars = evaluate_egyptian_bound_condition("Mars", 109.25)
    with pytest.raises(ValueError):
        EgyptianBoundsAggregateProfile(
            profiles=(venus, mars),
            self_governed_count=0,
            supported_count=2,
            mediated_count=0,
            constrained_count=0,
            strengthening_total=2,
            weakening_total=0,
            neutral_total=0,
            strongest_planets=("Venus",),
            weakest_planets=("Mars",),
        )
