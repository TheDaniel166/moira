from __future__ import annotations

import pytest

import moira.primary_direction_targets as target_module
from moira.constants import Body
from moira.primary_direction_targets import (
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
    assert primary_direction_target_truth("ASC").target_class is PrimaryDirectionTargetClass.ANGLE


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


def test_primary_direction_targets_aggregate_and_network_are_deterministic() -> None:
    truths = (
        primary_direction_target_truth(Body.SUN),
        primary_direction_target_truth("North Node"),
        primary_direction_target_truth("ASC"),
    )
    aggregate = evaluate_primary_direction_targets_aggregate(truths)
    network = evaluate_primary_direction_targets_network(truths)

    assert aggregate.total_profiles == 3
    assert aggregate.planet_count == 1
    assert aggregate.node_count == 1
    assert aggregate.angle_count == 1
    assert aggregate.universally_admitted_count == 3
    assert network.dominant_class in {
        PrimaryDirectionTargetClass.PLANET,
        PrimaryDirectionTargetClass.NODE,
        PrimaryDirectionTargetClass.ANGLE,
    }


def test_primary_direction_targets_reject_invalid_requests() -> None:
    with pytest.raises(ValueError):
        PrimaryDirectionTargetPolicy(admitted_significator_classes=frozenset())
    with pytest.raises(ValueError):
        primary_direction_target_truth("Spica")
    with pytest.raises(ValueError):
        evaluate_primary_direction_targets_aggregate([])
    with pytest.raises(ValueError):
        evaluate_primary_direction_targets_network([])


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
