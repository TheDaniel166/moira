from __future__ import annotations

import pytest

import moira.primary_directions.perfections as perfection_module
from moira.primary_directions.perfections import (
    PrimaryDirectionPerfectionConditionState,
    PrimaryDirectionPerfectionKind,
    PrimaryDirectionPerfectionMode,
    PrimaryDirectionPerfectionPolicy,
    classify_primary_direction_perfection,
    evaluate_primary_direction_perfection_condition,
    evaluate_primary_direction_perfection_relations,
    evaluate_primary_direction_perfections_aggregate,
    evaluate_primary_direction_perfections_network,
    primary_direction_perfection_truth,
    relate_primary_direction_perfection,
)


def test_primary_direction_perfection_truth_exposes_current_admitted_kinds() -> None:
    truth = primary_direction_perfection_truth()
    assert truth.kind is PrimaryDirectionPerfectionKind.MUNDANE_POSITION_PERFECTION
    assert truth.mode is PrimaryDirectionPerfectionMode.POSITIONAL
    assert truth.uses_significator_mundane_fraction is True
    assert truth.world_frame_based is True

    zodiacal_truth = primary_direction_perfection_truth(
        PrimaryDirectionPerfectionKind.ZODIACAL_LONGITUDE_PERFECTION
    )
    assert zodiacal_truth.kind is PrimaryDirectionPerfectionKind.ZODIACAL_LONGITUDE_PERFECTION
    assert zodiacal_truth.mode is PrimaryDirectionPerfectionMode.POSITIONAL
    assert zodiacal_truth.uses_significator_mundane_fraction is False
    assert zodiacal_truth.world_frame_based is False

    projected_truth = primary_direction_perfection_truth(
        PrimaryDirectionPerfectionKind.ZODIACAL_PROJECTED_PERFECTION
    )
    assert projected_truth.kind is PrimaryDirectionPerfectionKind.ZODIACAL_PROJECTED_PERFECTION
    assert projected_truth.mode is PrimaryDirectionPerfectionMode.POSITIONAL
    assert projected_truth.uses_significator_mundane_fraction is False
    assert projected_truth.world_frame_based is False


def test_primary_direction_perfection_classification_relation_and_condition_are_stable() -> None:
    truth = primary_direction_perfection_truth()
    classification = classify_primary_direction_perfection(truth)
    relation = relate_primary_direction_perfection(truth)
    relation_profile = evaluate_primary_direction_perfection_relations(truth)
    condition = evaluate_primary_direction_perfection_condition(truth)

    assert classification.positional is True
    assert classification.aspectual is False
    assert relation.relation_kind is PrimaryDirectionPerfectionKind.MUNDANE_POSITION_PERFECTION
    assert relation_profile.detected_relation == relation
    assert condition.state is PrimaryDirectionPerfectionConditionState.MUNDANE_POSITIONAL

    zodiacal_truth = primary_direction_perfection_truth(
        PrimaryDirectionPerfectionKind.ZODIACAL_LONGITUDE_PERFECTION
    )
    zodiacal_relation = relate_primary_direction_perfection(zodiacal_truth)
    zodiacal_condition = evaluate_primary_direction_perfection_condition(zodiacal_truth)
    assert (
        zodiacal_relation.relation_kind
        is PrimaryDirectionPerfectionKind.ZODIACAL_LONGITUDE_PERFECTION
    )
    assert zodiacal_condition.state is PrimaryDirectionPerfectionConditionState.ZODIACAL_POSITIONAL

    projected_truth = primary_direction_perfection_truth(
        PrimaryDirectionPerfectionKind.ZODIACAL_PROJECTED_PERFECTION
    )
    projected_relation = relate_primary_direction_perfection(projected_truth)
    projected_condition = evaluate_primary_direction_perfection_condition(projected_truth)
    assert (
        projected_relation.relation_kind
        is PrimaryDirectionPerfectionKind.ZODIACAL_PROJECTED_PERFECTION
    )
    assert projected_condition.state is PrimaryDirectionPerfectionConditionState.ZODIACAL_PROJECTED


def test_primary_direction_perfections_aggregate_and_network_are_deterministic() -> None:
    truths = (
        primary_direction_perfection_truth(),
        primary_direction_perfection_truth(
            PrimaryDirectionPerfectionKind.ZODIACAL_LONGITUDE_PERFECTION
        ),
        primary_direction_perfection_truth(
            PrimaryDirectionPerfectionKind.ZODIACAL_PROJECTED_PERFECTION
        ),
        primary_direction_perfection_truth(),
    )
    aggregate = evaluate_primary_direction_perfections_aggregate(truths)
    network = evaluate_primary_direction_perfections_network(truths)

    assert aggregate.total_profiles == 4
    assert aggregate.positional_count == 4
    assert aggregate.world_frame_count == 2
    assert len(network.nodes) == 3
    assert {node.kind for node in network.nodes} == {
        PrimaryDirectionPerfectionKind.MUNDANE_POSITION_PERFECTION,
        PrimaryDirectionPerfectionKind.ZODIACAL_LONGITUDE_PERFECTION,
        PrimaryDirectionPerfectionKind.ZODIACAL_PROJECTED_PERFECTION,
    }
    assert len(network.edges) == 3
    assert network.dominant_kind is PrimaryDirectionPerfectionKind.MUNDANE_POSITION_PERFECTION
    assert network.isolated_kinds == ()


def test_primary_direction_perfections_reject_invalid_requests() -> None:
    with pytest.raises(ValueError):
        PrimaryDirectionPerfectionPolicy("field_plane")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        evaluate_primary_direction_perfections_aggregate([])
    with pytest.raises(ValueError):
        evaluate_primary_direction_perfections_network([])


def test_primary_direction_perfections_module_exports_curated_surface() -> None:
    expected = {
        "PrimaryDirectionPerfectionKind",
        "PrimaryDirectionPerfectionMode",
        "PrimaryDirectionPerfectionConditionState",
        "PrimaryDirectionPerfectionPolicy",
        "PrimaryDirectionPerfectionTruth",
        "PrimaryDirectionPerfectionClassification",
        "PrimaryDirectionPerfectionRelation",
        "PrimaryDirectionPerfectionRelationProfile",
        "PrimaryDirectionPerfectionConditionProfile",
        "PrimaryDirectionPerfectionsAggregateProfile",
        "PrimaryDirectionPerfectionsNetworkNode",
        "PrimaryDirectionPerfectionsNetworkEdge",
        "PrimaryDirectionPerfectionsNetworkProfile",
        "primary_direction_perfection_truth",
        "classify_primary_direction_perfection",
        "relate_primary_direction_perfection",
        "evaluate_primary_direction_perfection_relations",
        "evaluate_primary_direction_perfection_condition",
        "evaluate_primary_direction_perfections_aggregate",
        "evaluate_primary_direction_perfections_network",
    }
    assert expected <= set(perfection_module.__all__)
