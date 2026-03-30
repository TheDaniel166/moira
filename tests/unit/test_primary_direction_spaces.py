from __future__ import annotations

import pytest

import moira.primary_directions.spaces as space_module
from moira.primary_directions.spaces import (
    PrimaryDirectionLatitudeMode,
    PrimaryDirectionSpace,
    PrimaryDirectionSpaceConditionState,
    PrimaryDirectionSpaceKind,
    PrimaryDirectionSpacePolicy,
    PrimaryDirectionSpaceRelationKind,
    classify_primary_direction_space,
    evaluate_primary_direction_space_condition,
    evaluate_primary_direction_space_relations,
    evaluate_primary_direction_spaces_aggregate,
    evaluate_primary_direction_spaces_network,
    primary_direction_space_truth,
    relate_primary_direction_space,
)


def test_primary_direction_space_truth_exposes_current_admitted_spaces() -> None:
    truth = primary_direction_space_truth()
    assert truth.space is PrimaryDirectionSpace.IN_MUNDO
    assert truth.kind is PrimaryDirectionSpaceKind.WORLD_FRAME
    assert truth.latitude_mode is PrimaryDirectionLatitudeMode.PRESERVED
    assert truth.relation_domain == "world_frame"
    assert truth.aspectual_points_native is False

    zodiacal_truth = primary_direction_space_truth(PrimaryDirectionSpace.IN_ZODIACO)
    assert zodiacal_truth.space is PrimaryDirectionSpace.IN_ZODIACO
    assert zodiacal_truth.kind is PrimaryDirectionSpaceKind.ZODIACAL
    assert zodiacal_truth.latitude_mode is PrimaryDirectionLatitudeMode.SUPPRESSED
    assert zodiacal_truth.relation_domain == "zodiacal_longitude"
    assert zodiacal_truth.aspectual_points_native is False

    projected_truth = primary_direction_space_truth(
        policy=PrimaryDirectionSpacePolicy(
            PrimaryDirectionSpace.IN_ZODIACO,
            latitude_mode=PrimaryDirectionLatitudeMode.PRESERVED,
        )
    )
    assert projected_truth.space is PrimaryDirectionSpace.IN_ZODIACO
    assert projected_truth.kind is PrimaryDirectionSpaceKind.ZODIACAL
    assert projected_truth.latitude_mode is PrimaryDirectionLatitudeMode.PRESERVED
    assert projected_truth.relation_domain == "zodiacal_projected"


def test_primary_direction_space_classification_and_condition_are_stable() -> None:
    truth = primary_direction_space_truth()
    classification = classify_primary_direction_space(truth)
    relation = relate_primary_direction_space(truth)
    relation_profile = evaluate_primary_direction_space_relations(truth)
    condition = evaluate_primary_direction_space_condition(truth)

    assert classification.bodily is True
    assert classification.zodiacal is False
    assert classification.hybrid is False
    assert relation.relation_kind is PrimaryDirectionSpaceRelationKind.WORLD_FRAME_PERFECTION
    assert relation_profile.detected_relation == relation
    assert condition.state is PrimaryDirectionSpaceConditionState.WORLD_FRAMED

    zodiacal_truth = primary_direction_space_truth(PrimaryDirectionSpace.IN_ZODIACO)
    zodiacal_classification = classify_primary_direction_space(zodiacal_truth)
    zodiacal_relation = relate_primary_direction_space(zodiacal_truth)
    zodiacal_condition = evaluate_primary_direction_space_condition(zodiacal_truth)

    assert zodiacal_classification.bodily is False
    assert zodiacal_classification.zodiacal is True
    assert zodiacal_classification.hybrid is False
    assert (
        zodiacal_relation.relation_kind
        is PrimaryDirectionSpaceRelationKind.ZODIACAL_LONGITUDE_PERFECTION
    )
    assert zodiacal_condition.state is PrimaryDirectionSpaceConditionState.ZODIACALLY_FRAMED

    projected_truth = primary_direction_space_truth(
        policy=PrimaryDirectionSpacePolicy(
            PrimaryDirectionSpace.IN_ZODIACO,
            latitude_mode=PrimaryDirectionLatitudeMode.PRESERVED,
        )
    )
    projected_relation = relate_primary_direction_space(projected_truth)
    projected_condition = evaluate_primary_direction_space_condition(projected_truth)
    assert (
        projected_relation.relation_kind
        is PrimaryDirectionSpaceRelationKind.ZODIACAL_PROJECTED_PERFECTION
    )
    assert projected_condition.state is PrimaryDirectionSpaceConditionState.ZODIACALLY_PROJECTED


def test_primary_direction_spaces_aggregate_and_network_are_deterministic() -> None:
    truths = (
        primary_direction_space_truth(),
        primary_direction_space_truth(PrimaryDirectionSpace.IN_ZODIACO),
        primary_direction_space_truth(
            policy=PrimaryDirectionSpacePolicy(
                PrimaryDirectionSpace.IN_ZODIACO,
                latitude_mode=PrimaryDirectionLatitudeMode.PRESERVED,
            )
        ),
        primary_direction_space_truth(),
    )
    aggregate = evaluate_primary_direction_spaces_aggregate(truths)
    network = evaluate_primary_direction_spaces_network(truths)

    assert aggregate.total_profiles == 4
    assert aggregate.world_frame_count == 2
    assert aggregate.preserves_latitude_count == 3
    assert len(network.nodes) == 2
    assert {node.space for node in network.nodes} == {
        PrimaryDirectionSpace.IN_MUNDO,
        PrimaryDirectionSpace.IN_ZODIACO,
    }
    assert len(network.edges) == 2
    assert network.dominant_space is PrimaryDirectionSpace.IN_ZODIACO
    assert network.isolated_spaces == ()


def test_primary_direction_spaces_reject_invalid_requests() -> None:
    with pytest.raises(ValueError):
        PrimaryDirectionSpacePolicy("field_plane")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        PrimaryDirectionSpacePolicy(
            PrimaryDirectionSpace.IN_MUNDO,
            latitude_mode=PrimaryDirectionLatitudeMode.SUPPRESSED,
        )
    with pytest.raises(ValueError):
        evaluate_primary_direction_spaces_aggregate([])
    with pytest.raises(ValueError):
        evaluate_primary_direction_spaces_network([])


def test_primary_direction_spaces_module_exports_curated_surface() -> None:
    expected = {
        "PrimaryDirectionSpace",
        "PrimaryDirectionSpaceKind",
        "PrimaryDirectionLatitudeMode",
        "PrimaryDirectionSpaceRelationKind",
        "PrimaryDirectionSpaceConditionState",
        "PrimaryDirectionSpacePolicy",
        "PrimaryDirectionSpaceTruth",
        "PrimaryDirectionSpaceClassification",
        "PrimaryDirectionSpaceRelation",
        "PrimaryDirectionSpaceRelationProfile",
        "PrimaryDirectionSpaceConditionProfile",
        "PrimaryDirectionSpacesAggregateProfile",
        "PrimaryDirectionSpacesNetworkNode",
        "PrimaryDirectionSpacesNetworkEdge",
        "PrimaryDirectionSpacesNetworkProfile",
        "primary_direction_space_truth",
        "classify_primary_direction_space",
        "relate_primary_direction_space",
        "evaluate_primary_direction_space_relations",
        "evaluate_primary_direction_space_condition",
        "evaluate_primary_direction_spaces_aggregate",
        "evaluate_primary_direction_spaces_network",
    }
    assert expected <= set(space_module.__all__)
