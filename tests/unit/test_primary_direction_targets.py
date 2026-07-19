from __future__ import annotations

import math

import pytest

import moira.primary_directions.targets as target_module
from moira.constants import Body
from moira.primary_directions.targets import (
    PrimaryDirectionTargetClass,
    PrimaryDirectionTargetConditionState,
    PrimaryDirectionTargetPolicy,
    PrimaryDirectionTargetRelationKind,
    classify_primary_direction_target,
    evaluate_primary_direction_target_condition,
    evaluate_primary_direction_target_relations,
    evaluate_primary_direction_targets_aggregate,
    evaluate_primary_direction_targets_network,
    primary_direction_target_truth,
    relate_primary_direction_target,
)


def test_primary_direction_target_truth_classifies_current_admitted_targets() -> None:
    assert primary_direction_target_truth(Body.SUN).target_class is PrimaryDirectionTargetClass.PLANET
    assert primary_direction_target_truth("North Node").target_class is PrimaryDirectionTargetClass.NODE
    assert primary_direction_target_truth(Body.TRUE_NODE).target_class is PrimaryDirectionTargetClass.NODE
    assert primary_direction_target_truth(Body.LILITH).target_class is PrimaryDirectionTargetClass.NODE
    assert primary_direction_target_truth("ASC").target_class is PrimaryDirectionTargetClass.ANGLE
    assert primary_direction_target_truth("H1").target_class is PrimaryDirectionTargetClass.HOUSE_CUSP
    aspect_truth = primary_direction_target_truth(f"{Body.MOON} Trine")
    assert aspect_truth.target_class is PrimaryDirectionTargetClass.ASPECTUAL_POINT
    assert aspect_truth.source_name == Body.MOON
    assert aspect_truth.aspect_name == "Trine"
    assert aspect_truth.aspect_angle == pytest.approx(120.0)
    dexter_truth = primary_direction_target_truth(f"{Body.MOON} Dexter Trine")
    assert dexter_truth.target_class is PrimaryDirectionTargetClass.ASPECTUAL_POINT
    assert dexter_truth.aspect_name == "Dexter Trine"
    assert dexter_truth.aspect_angle == pytest.approx(-120.0)
    opposition_truth = primary_direction_target_truth(f"{Body.MOON} Opposition")
    assert opposition_truth.target_class is PrimaryDirectionTargetClass.ASPECTUAL_POINT
    assert opposition_truth.aspect_angle == pytest.approx(180.0)


def test_primary_direction_target_classification_relation_and_condition_are_stable() -> None:
    truth = primary_direction_target_truth(Body.VENUS)
    classification = classify_primary_direction_target(truth)
    relation = relate_primary_direction_target(truth)
    relation_profile = evaluate_primary_direction_target_relations(truth)
    condition = evaluate_primary_direction_target_condition(truth)

    assert classification.admitted_as_significator is True
    assert classification.admitted_as_promissor is True
    assert relation.relation_kind is PrimaryDirectionTargetRelationKind.ADMITTED_AS_BOTH
    assert relation_profile.detected_relation == relation
    assert condition.state is PrimaryDirectionTargetConditionState.UNIVERSALLY_ADMITTED


def test_primary_direction_target_policy_can_restrict_classes() -> None:
    truth = primary_direction_target_truth("ASC")
    policy = PrimaryDirectionTargetPolicy(
        admitted_significator_classes=frozenset({PrimaryDirectionTargetClass.ANGLE}),
        admitted_promissor_classes=frozenset({PrimaryDirectionTargetClass.PLANET}),
    )
    classification = classify_primary_direction_target(truth, policy=policy)
    relation = relate_primary_direction_target(truth, policy=policy)

    assert classification.admitted_as_significator is True
    assert classification.admitted_as_promissor is False
    assert relation.relation_kind is PrimaryDirectionTargetRelationKind.ADMITTED_AS_SIGNIFICATOR_ONLY

    aspect_truth = primary_direction_target_truth(f"{Body.MOON} Trine")
    zodiacal_policy = PrimaryDirectionTargetPolicy(
        admitted_significator_classes=frozenset(
            {
                PrimaryDirectionTargetClass.PLANET,
                PrimaryDirectionTargetClass.NODE,
                PrimaryDirectionTargetClass.ANGLE,
            }
        ),
        admitted_promissor_classes=frozenset(
            {
                PrimaryDirectionTargetClass.PLANET,
                PrimaryDirectionTargetClass.NODE,
                PrimaryDirectionTargetClass.ANGLE,
                PrimaryDirectionTargetClass.ASPECTUAL_POINT,
            }
        ),
    )
    aspect_classification = classify_primary_direction_target(aspect_truth, policy=zodiacal_policy)
    assert aspect_classification.admitted_as_significator is False
    assert aspect_classification.admitted_as_promissor is True

    cusp_truth = primary_direction_target_truth("H10")
    cusp_policy = PrimaryDirectionTargetPolicy(
        admitted_significator_classes=frozenset({PrimaryDirectionTargetClass.HOUSE_CUSP}),
        admitted_promissor_classes=frozenset({PrimaryDirectionTargetClass.PLANET}),
    )
    cusp_classification = classify_primary_direction_target(cusp_truth, policy=cusp_policy)
    assert cusp_classification.admitted_as_significator is True
    assert cusp_classification.admitted_as_promissor is False


def test_primary_direction_target_policy_exposes_all_four_admission_states_truthfully() -> None:
    truth = primary_direction_target_truth("ASC")
    cases = (
        (
            PrimaryDirectionTargetPolicy(),
            PrimaryDirectionTargetRelationKind.ADMITTED_AS_BOTH,
            PrimaryDirectionTargetConditionState.UNIVERSALLY_ADMITTED,
        ),
        (
            PrimaryDirectionTargetPolicy(
                admitted_significator_classes={PrimaryDirectionTargetClass.ANGLE},  # type: ignore[arg-type]
                admitted_promissor_classes={PrimaryDirectionTargetClass.PLANET},  # type: ignore[arg-type]
            ),
            PrimaryDirectionTargetRelationKind.ADMITTED_AS_SIGNIFICATOR_ONLY,
            PrimaryDirectionTargetConditionState.SIGNIFICATOR_ONLY,
        ),
        (
            PrimaryDirectionTargetPolicy(
                admitted_significator_classes={PrimaryDirectionTargetClass.PLANET},  # type: ignore[arg-type]
                admitted_promissor_classes={PrimaryDirectionTargetClass.ANGLE},  # type: ignore[arg-type]
            ),
            PrimaryDirectionTargetRelationKind.ADMITTED_AS_PROMISSOR_ONLY,
            PrimaryDirectionTargetConditionState.PROMISSOR_ONLY,
        ),
        (
            PrimaryDirectionTargetPolicy(
                admitted_significator_classes={PrimaryDirectionTargetClass.PLANET},  # type: ignore[arg-type]
                admitted_promissor_classes={PrimaryDirectionTargetClass.NODE},  # type: ignore[arg-type]
            ),
            PrimaryDirectionTargetRelationKind.REJECTED,
            PrimaryDirectionTargetConditionState.NOT_ADMITTED,
        ),
    )
    for policy, expected_relation, expected_state in cases:
        relation_profile = evaluate_primary_direction_target_relations(truth, policy=policy)
        condition = evaluate_primary_direction_target_condition(truth, policy=policy)
        assert relation_profile.detected_relation.relation_kind is expected_relation
        assert condition.state is expected_state
        expected_admitted = () if expected_relation is PrimaryDirectionTargetRelationKind.REJECTED else (
            relation_profile.detected_relation,
        )
        assert relation_profile.admitted_relations == expected_admitted
        assert relation_profile.scored_relations == expected_admitted


def test_primary_direction_targets_aggregate_and_network_are_deterministic() -> None:
    truths = (
        primary_direction_target_truth(Body.SUN),
        primary_direction_target_truth("North Node"),
        primary_direction_target_truth("ASC"),
        primary_direction_target_truth("H1"),
        primary_direction_target_truth(f"{Body.MOON} Trine"),
    )
    aggregate = evaluate_primary_direction_targets_aggregate(truths)
    network = evaluate_primary_direction_targets_network(truths)

    assert aggregate.total_profiles == 5
    assert aggregate.planet_count == 1
    assert aggregate.node_count == 1
    assert aggregate.angle_count == 1
    assert aggregate.house_cusp_count == 1
    assert aggregate.aspect_count == 1
    assert aggregate.universally_admitted_count == 4
    assert aggregate.significator_only_count == 0
    assert aggregate.promissor_only_count == 0
    assert aggregate.not_admitted_count == 1
    assert network.dominant_class in {
        PrimaryDirectionTargetClass.PLANET,
        PrimaryDirectionTargetClass.NODE,
        PrimaryDirectionTargetClass.ANGLE,
        PrimaryDirectionTargetClass.HOUSE_CUSP,
        PrimaryDirectionTargetClass.ASPECTUAL_POINT,
    }


def test_primary_direction_targets_reject_invalid_requests() -> None:
    with pytest.raises(ValueError):
        PrimaryDirectionTargetPolicy(admitted_significator_classes=frozenset())
    with pytest.raises(ValueError):
        primary_direction_target_truth("Spica")
    with pytest.raises(ValueError):
        primary_direction_target_truth(f"{Body.SUN} Parallel")
    with pytest.raises(ValueError):
        primary_direction_target_truth(f"{Body.SUN} Contra-Parallel")
    with pytest.raises(ValueError):
        primary_direction_target_truth(f"{Body.MOON} Conjunction")
    with pytest.raises(ValueError):
        primary_direction_target_truth("Fraud Node")
    with pytest.raises(ValueError):
        primary_direction_target_truth("NotLilithAtAll")
    with pytest.raises(ValueError):
        primary_direction_target_truth("   ")
    with pytest.raises(ValueError):
        evaluate_primary_direction_targets_aggregate([])
    with pytest.raises(ValueError):
        evaluate_primary_direction_targets_network([])
    with pytest.raises(ValueError):
        PrimaryDirectionTargetPolicy(
            admitted_significator_classes={"planet"},  # type: ignore[arg-type]
            admitted_promissor_classes={PrimaryDirectionTargetClass.PLANET},  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("bad_angle", [math.nan, math.inf, -math.inf, "120", True])
def test_primary_direction_target_truth_rejects_forged_aspect_metadata(bad_angle: object) -> None:
    with pytest.raises(ValueError):
        target_module.PrimaryDirectionTargetTruth(
            name=f"{Body.MOON} Trine",
            target_class=PrimaryDirectionTargetClass.ASPECTUAL_POINT,
            source_name=Body.MOON,
            aspect_name="Trine",
            aspect_angle=bad_angle,  # type: ignore[arg-type]
        )


def test_primary_direction_target_truth_rejects_mismatched_identity_metadata() -> None:
    with pytest.raises(ValueError):
        target_module.PrimaryDirectionTargetTruth(
            name=f"{Body.MOON} Trine",
            target_class=PrimaryDirectionTargetClass.ASPECTUAL_POINT,
            source_name=Body.MOON,
            aspect_name="Trine",
            aspect_angle=90.0,
        )
    with pytest.raises(ValueError):
        target_module.PrimaryDirectionTargetTruth(
            name=f"{Body.SUN} Opposition",
            target_class=PrimaryDirectionTargetClass.ASPECTUAL_POINT,
            source_name=Body.SUN,
            aspect_name="Opposition",
            aspect_angle=90.0,
        )
    with pytest.raises(ValueError):
        target_module.PrimaryDirectionTargetTruth(
            name=f"{Body.SUN} Trine",
            target_class=PrimaryDirectionTargetClass.ASPECTUAL_POINT,
            source_name=Body.MOON,
            aspect_name="Trine",
            aspect_angle=120.0,
        )
    with pytest.raises(ValueError):
        target_module.PrimaryDirectionTargetTruth(
            name=Body.SUN,
            target_class="planet",  # type: ignore[arg-type]
        )


def test_primary_direction_target_collections_are_defensive_and_aggregate_is_complete() -> None:
    significators = {PrimaryDirectionTargetClass.PLANET}
    promissors = {PrimaryDirectionTargetClass.NODE}
    policy = PrimaryDirectionTargetPolicy(significators, promissors)  # type: ignore[arg-type]
    significators.clear()
    promissors.clear()
    assert policy.admitted_significator_classes == frozenset({PrimaryDirectionTargetClass.PLANET})
    assert policy.admitted_promissor_classes == frozenset({PrimaryDirectionTargetClass.NODE})

    truths = (
        primary_direction_target_truth(Body.SUN),
        primary_direction_target_truth("North Node"),
    )
    aggregate = evaluate_primary_direction_targets_aggregate(truths)
    profiles = list(aggregate.profiles)
    defensive = target_module.PrimaryDirectionTargetsAggregateProfile(
        profiles=profiles,  # type: ignore[arg-type]
        total_profiles=2,
        planet_count=1,
        node_count=1,
        angle_count=0,
        house_cusp_count=0,
        aspect_count=0,
        universally_admitted_count=2,
    )
    profiles.clear()
    assert defensive.total_profiles == 2
    with pytest.raises(ValueError):
        target_module.PrimaryDirectionTargetsAggregateProfile(
            profiles=aggregate.profiles,
            total_profiles=2,
            planet_count=1,
            node_count=1,
            angle_count=0,
            house_cusp_count=0,
            aspect_count=0,
            universally_admitted_count=999,
        )


def test_primary_direction_target_network_validates_topology_and_explicit_policy_gate() -> None:
    truths = (
        primary_direction_target_truth(Body.SUN),
        primary_direction_target_truth("North Node"),
        primary_direction_target_truth("ASC"),
    )
    network = evaluate_primary_direction_targets_network(truths)
    nodes = list(network.nodes)
    edges = list(network.edges)
    isolated = list(network.isolated_classes)
    defensive = target_module.PrimaryDirectionTargetsNetworkProfile(
        nodes=nodes,  # type: ignore[arg-type]
        edges=edges,  # type: ignore[arg-type]
        dominant_class=network.dominant_class,
        isolated_classes=isolated,  # type: ignore[arg-type]
    )
    nodes.clear()
    edges.clear()
    isolated.clear()
    assert defensive == network

    dangling = target_module.PrimaryDirectionTargetsNetworkEdge(
        from_class=PrimaryDirectionTargetClass.PLANET,
        to_class=PrimaryDirectionTargetClass.ASPECTUAL_POINT,
        count=1,
    )
    with pytest.raises(ValueError):
        target_module.PrimaryDirectionTargetsNetworkProfile(
            nodes=network.nodes,
            edges=(dangling,),
            dominant_class=network.dominant_class,
            isolated_classes=(),
        )
    with pytest.raises(ValueError):
        target_module.PrimaryDirectionTargetsNetworkNode(
            target_class=PrimaryDirectionTargetClass.PLANET,
            count=True,  # type: ignore[arg-type]
        )

    with pytest.raises(ValueError, match="transition degrees"):
        target_module.PrimaryDirectionTargetsNetworkProfile(
            nodes=tuple(
                target_module.PrimaryDirectionTargetsNetworkNode(
                    target_class=item,
                    count=1,
                )
                for item in (
                    PrimaryDirectionTargetClass.PLANET,
                    PrimaryDirectionTargetClass.NODE,
                    PrimaryDirectionTargetClass.ANGLE,
                )
            ),
            edges=(
                target_module.PrimaryDirectionTargetsNetworkEdge(
                    PrimaryDirectionTargetClass.PLANET,
                    PrimaryDirectionTargetClass.NODE,
                    1,
                ),
                target_module.PrimaryDirectionTargetsNetworkEdge(
                    PrimaryDirectionTargetClass.PLANET,
                    PrimaryDirectionTargetClass.ANGLE,
                    1,
                ),
            ),
            dominant_class=PrimaryDirectionTargetClass.PLANET,
            isolated_classes=(),
        )

    rejecting_policy = PrimaryDirectionTargetPolicy(
        admitted_significator_classes={PrimaryDirectionTargetClass.PLANET},  # type: ignore[arg-type]
        admitted_promissor_classes={PrimaryDirectionTargetClass.NODE},  # type: ignore[arg-type]
    )
    with pytest.raises(ValueError):
        evaluate_primary_direction_targets_network(truths, policy=rejecting_policy)


def test_primary_direction_targets_module_exports_curated_surface() -> None:
    expected = {
        "PrimaryDirectionTargetClass",
        "PrimaryDirectionTargetRelationKind",
        "PrimaryDirectionTargetConditionState",
        "PrimaryDirectionTargetPolicy",
        "PrimaryDirectionTargetTruth",
        "PrimaryDirectionTargetClassification",
        "PrimaryDirectionTargetRelation",
        "PrimaryDirectionTargetRelationProfile",
        "PrimaryDirectionTargetConditionProfile",
        "PrimaryDirectionTargetsAggregateProfile",
        "PrimaryDirectionTargetsNetworkNode",
        "PrimaryDirectionTargetsNetworkEdge",
        "PrimaryDirectionTargetsNetworkProfile",
        "primary_direction_target_truth",
        "classify_primary_direction_target",
        "relate_primary_direction_target",
        "evaluate_primary_direction_target_relations",
        "evaluate_primary_direction_target_condition",
        "evaluate_primary_direction_targets_aggregate",
        "evaluate_primary_direction_targets_network",
    }
    assert expected <= set(target_module.__all__)
