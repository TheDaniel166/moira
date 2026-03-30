from __future__ import annotations

import pytest

import moira.primary_directions.converse as converse_module
from moira.primary_directions.converse import (
    PrimaryDirectionConverseConditionState,
    PrimaryDirectionConverseDoctrine,
    PrimaryDirectionConversePolicy,
    PrimaryDirectionConverseRelationKind,
    classify_primary_direction_converse,
    evaluate_primary_direction_converse_aggregate,
    evaluate_primary_direction_converse_condition,
    evaluate_primary_direction_converse_network,
    evaluate_primary_direction_converse_relations,
    primary_direction_converse_truth,
    relate_primary_direction_converse,
)


def test_primary_direction_converse_truth_exposes_current_doctrines() -> None:
    direct_only = primary_direction_converse_truth(PrimaryDirectionConverseDoctrine.DIRECT_ONLY)
    traditional = primary_direction_converse_truth(
        PrimaryDirectionConverseDoctrine.TRADITIONAL_CONVERSE
    )

    assert direct_only.includes_direct is True
    assert direct_only.includes_converse is False
    assert direct_only.motion_count == 1
    assert traditional.includes_direct is True
    assert traditional.includes_converse is True
    assert traditional.motion_count == 2


def test_primary_direction_converse_classification_relation_and_condition_are_stable() -> None:
    truth = primary_direction_converse_truth()
    classification = classify_primary_direction_converse(truth)
    relation = relate_primary_direction_converse(truth)
    relation_profile = evaluate_primary_direction_converse_relations(truth)
    condition = evaluate_primary_direction_converse_condition(truth)

    assert classification.direct_only is False
    assert classification.admits_converse is True
    assert relation.relation_kind is PrimaryDirectionConverseRelationKind.DIRECT_AND_TRADITIONAL_CONVERSE
    assert relation.admitted_motions == ("direct", "converse")
    assert relation_profile.detected_relation == relation
    assert condition.state is PrimaryDirectionConverseConditionState.DIRECT_AND_CONVERSE


def test_primary_direction_converse_aggregate_and_network_are_deterministic() -> None:
    truths = (
        primary_direction_converse_truth(PrimaryDirectionConverseDoctrine.DIRECT_ONLY),
        primary_direction_converse_truth(PrimaryDirectionConverseDoctrine.TRADITIONAL_CONVERSE),
        primary_direction_converse_truth(PrimaryDirectionConverseDoctrine.TRADITIONAL_CONVERSE),
    )
    aggregate = evaluate_primary_direction_converse_aggregate(truths)
    network = evaluate_primary_direction_converse_network(truths)

    assert aggregate.total_profiles == 3
    assert aggregate.converse_enabled_count == 2
    assert aggregate.direct_only_count == 1
    assert len(network.nodes) == 2
    assert network.dominant_doctrine is PrimaryDirectionConverseDoctrine.TRADITIONAL_CONVERSE


def test_primary_direction_converse_rejects_invalid_requests() -> None:
    with pytest.raises(ValueError):
        PrimaryDirectionConversePolicy("neo_converse")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        evaluate_primary_direction_converse_aggregate([])
    with pytest.raises(ValueError):
        evaluate_primary_direction_converse_network([])


def test_primary_direction_converse_module_exports_curated_surface() -> None:
    expected = {
        "PrimaryDirectionConverseDoctrine",
        "PrimaryDirectionConverseRelationKind",
        "PrimaryDirectionConverseConditionState",
        "PrimaryDirectionConversePolicy",
        "PrimaryDirectionConverseTruth",
        "PrimaryDirectionConverseClassification",
        "PrimaryDirectionConverseRelation",
        "PrimaryDirectionConverseRelationProfile",
        "PrimaryDirectionConverseConditionProfile",
        "PrimaryDirectionConverseAggregateProfile",
        "PrimaryDirectionConverseNetworkNode",
        "PrimaryDirectionConverseNetworkEdge",
        "PrimaryDirectionConverseNetworkProfile",
        "primary_direction_converse_truth",
        "classify_primary_direction_converse",
        "relate_primary_direction_converse",
        "evaluate_primary_direction_converse_relations",
        "evaluate_primary_direction_converse_condition",
        "evaluate_primary_direction_converse_aggregate",
        "evaluate_primary_direction_converse_network",
    }
    assert expected <= set(converse_module.__all__)
