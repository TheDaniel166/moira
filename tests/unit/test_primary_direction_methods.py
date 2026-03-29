from __future__ import annotations

import pytest

import moira.primary_direction_methods as method_module
from moira.primary_direction_methods import (
    PrimaryDirectionMethod,
    PrimaryDirectionMethodConditionState,
    PrimaryDirectionMethodKind,
    PrimaryDirectionMethodPolicy,
    PrimaryDirectionMethodRelationKind,
    classify_primary_direction_method,
    evaluate_primary_direction_method_condition,
    evaluate_primary_direction_method_relations,
    evaluate_primary_direction_methods_aggregate,
    evaluate_primary_direction_methods_network,
    primary_direction_method_truth,
    relate_primary_direction_method,
)


def test_primary_direction_method_truth_exposes_current_admitted_method() -> None:
    truth = primary_direction_method_truth()
    assert truth.method is PrimaryDirectionMethod.PLACIDUS_MUNDANE
    assert truth.kind is PrimaryDirectionMethodKind.PLACIDUS_MUNDANE
    assert truth.uses_semi_arcs is True
    assert truth.uses_world_frame_geometry is True
    assert truth.latitude_sensitive is True


def test_primary_direction_method_classification_relation_and_condition_are_stable() -> None:
    truth = primary_direction_method_truth()
    classification = classify_primary_direction_method(truth)
    relation = relate_primary_direction_method(truth)
    relation_profile = evaluate_primary_direction_method_relations(truth)
    condition = evaluate_primary_direction_method_condition(truth)

    assert classification.mundane is True
    assert classification.zodiacal is False
    assert classification.semi_arc_based is True
    assert relation.relation_kind is PrimaryDirectionMethodRelationKind.PLACIDIAN_MUNDANE_PERFECTION
    assert relation_profile.detected_relation == relation
    assert condition.state is PrimaryDirectionMethodConditionState.MUNDANE_SEMI_ARC_GROUNDED


def test_primary_direction_method_truth_admits_placidian_classic_branch() -> None:
    truth = primary_direction_method_truth(PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC)
    relation = relate_primary_direction_method(truth)
    condition = evaluate_primary_direction_method_condition(truth)

    assert truth.kind is PrimaryDirectionMethodKind.PLACIDIAN_CLASSIC_SEMI_ARC
    assert relation.relation_kind is (
        PrimaryDirectionMethodRelationKind.PLACIDIAN_CLASSIC_SEMI_ARC_PERFECTION
    )
    assert condition.state is PrimaryDirectionMethodConditionState.CLASSIC_SEMI_ARC_GROUNDED


def test_primary_direction_methods_aggregate_and_network_are_deterministic() -> None:
    truths = (
        primary_direction_method_truth(),
        primary_direction_method_truth(PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC),
    )
    aggregate = evaluate_primary_direction_methods_aggregate(truths)
    network = evaluate_primary_direction_methods_network(truths)

    assert aggregate.total_profiles == 2
    assert aggregate.mundane_count == 2
    assert aggregate.semi_arc_count == 2
    assert len(network.nodes) == 2
    assert {node.method for node in network.nodes} == {
        PrimaryDirectionMethod.PLACIDUS_MUNDANE,
        PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC,
    }


def test_primary_direction_methods_reject_invalid_requests() -> None:
    with pytest.raises(ValueError):
        PrimaryDirectionMethodPolicy("regiomontanus")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        evaluate_primary_direction_methods_aggregate([])
    with pytest.raises(ValueError):
        evaluate_primary_direction_methods_network([])


def test_primary_direction_methods_module_exports_curated_surface() -> None:
    expected = {
        "PrimaryDirectionMethod",
        "PrimaryDirectionMethodKind",
        "PrimaryDirectionMethodRelationKind",
        "PrimaryDirectionMethodConditionState",
        "PrimaryDirectionMethodPolicy",
        "PrimaryDirectionMethodTruth",
        "PrimaryDirectionMethodClassification",
        "PrimaryDirectionMethodRelation",
        "PrimaryDirectionMethodRelationProfile",
        "PrimaryDirectionMethodConditionProfile",
        "PrimaryDirectionMethodsAggregateProfile",
        "PrimaryDirectionMethodsNetworkNode",
        "PrimaryDirectionMethodsNetworkEdge",
        "PrimaryDirectionMethodsNetworkProfile",
        "primary_direction_method_truth",
        "classify_primary_direction_method",
        "relate_primary_direction_method",
        "evaluate_primary_direction_method_relations",
        "evaluate_primary_direction_method_condition",
        "evaluate_primary_direction_methods_aggregate",
        "evaluate_primary_direction_methods_network",
    }
    assert expected <= set(method_module.__all__)
