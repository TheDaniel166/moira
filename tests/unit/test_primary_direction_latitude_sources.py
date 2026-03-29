from __future__ import annotations

import pytest

import moira.primary_direction_latitude_sources as latitude_source_module
from moira.primary_direction_latitude_sources import (
    PrimaryDirectionLatitudeSource,
    PrimaryDirectionLatitudeSourceConditionState,
    PrimaryDirectionLatitudeSourcePolicy,
    PrimaryDirectionLatitudeSourceRelationKind,
    classify_primary_direction_latitude_source,
    evaluate_primary_direction_latitude_source_aggregate,
    evaluate_primary_direction_latitude_source_condition,
    evaluate_primary_direction_latitude_source_network,
    evaluate_primary_direction_latitude_source_relations,
    primary_direction_latitude_source_truth,
    relate_primary_direction_latitude_source,
)


def test_primary_direction_latitude_source_truth_exposes_current_sources() -> None:
    native = primary_direction_latitude_source_truth(PrimaryDirectionLatitudeSource.PROMISSOR_NATIVE)
    zero = primary_direction_latitude_source_truth(PrimaryDirectionLatitudeSource.ASSIGNED_ZERO)
    inherited = primary_direction_latitude_source_truth(PrimaryDirectionLatitudeSource.ASPECT_INHERITED)
    significator = primary_direction_latitude_source_truth(
        PrimaryDirectionLatitudeSource.SIGNIFICATOR_NATIVE
    )

    assert native.derives_from_body is True
    assert native.assigns_zero is False
    assert zero.derives_from_body is False
    assert zero.assigns_zero is True
    assert inherited.derives_from_body is False
    assert inherited.assigns_zero is False
    assert significator.derives_from_body is False
    assert significator.assigns_zero is False


def test_primary_direction_latitude_source_classification_relation_and_condition_are_stable() -> None:
    truth = primary_direction_latitude_source_truth()
    classification = classify_primary_direction_latitude_source(truth)
    relation = relate_primary_direction_latitude_source(truth)
    relation_profile = evaluate_primary_direction_latitude_source_relations(truth)
    condition = evaluate_primary_direction_latitude_source_condition(truth)

    assert classification.body_derived is True
    assert classification.zero_assigned is False
    assert classification.aspect_inherited is False
    assert relation.relation_kind is PrimaryDirectionLatitudeSourceRelationKind.NATIVE_BODY_LATITUDE
    assert relation_profile.detected_relation == relation
    assert condition.state is PrimaryDirectionLatitudeSourceConditionState.BODY_DERIVED

    inherited_truth = primary_direction_latitude_source_truth(
        PrimaryDirectionLatitudeSource.ASPECT_INHERITED
    )
    inherited_relation = relate_primary_direction_latitude_source(inherited_truth)
    inherited_classification = classify_primary_direction_latitude_source(inherited_truth)
    inherited_condition = evaluate_primary_direction_latitude_source_condition(inherited_truth)
    assert inherited_classification.body_derived is False
    assert inherited_classification.zero_assigned is False
    assert inherited_classification.aspect_inherited is True
    assert inherited_classification.significator_derived is False
    assert (
        inherited_relation.relation_kind
        is PrimaryDirectionLatitudeSourceRelationKind.ASPECT_LATITUDE_INHERITED
    )
    assert inherited_condition.state is PrimaryDirectionLatitudeSourceConditionState.ASPECT_DERIVED

    significator_truth = primary_direction_latitude_source_truth(
        PrimaryDirectionLatitudeSource.SIGNIFICATOR_NATIVE
    )
    significator_relation = relate_primary_direction_latitude_source(significator_truth)
    significator_classification = classify_primary_direction_latitude_source(significator_truth)
    significator_condition = evaluate_primary_direction_latitude_source_condition(significator_truth)
    assert significator_classification.body_derived is False
    assert significator_classification.zero_assigned is False
    assert significator_classification.aspect_inherited is False
    assert significator_classification.significator_derived is True
    assert (
        significator_relation.relation_kind
        is PrimaryDirectionLatitudeSourceRelationKind.SIGNIFICATOR_LATITUDE_NATIVE
    )
    assert (
        significator_condition.state
        is PrimaryDirectionLatitudeSourceConditionState.SIGNIFICATOR_DERIVED
    )


def test_primary_direction_latitude_source_aggregate_and_network_are_deterministic() -> None:
    truths = (
        primary_direction_latitude_source_truth(PrimaryDirectionLatitudeSource.PROMISSOR_NATIVE),
        primary_direction_latitude_source_truth(PrimaryDirectionLatitudeSource.ASSIGNED_ZERO),
        primary_direction_latitude_source_truth(PrimaryDirectionLatitudeSource.ASPECT_INHERITED),
        primary_direction_latitude_source_truth(PrimaryDirectionLatitudeSource.SIGNIFICATOR_NATIVE),
        primary_direction_latitude_source_truth(PrimaryDirectionLatitudeSource.ASSIGNED_ZERO),
    )
    aggregate = evaluate_primary_direction_latitude_source_aggregate(truths)
    network = evaluate_primary_direction_latitude_source_network(truths)

    assert aggregate.total_profiles == 5
    assert aggregate.body_derived_count == 1
    assert aggregate.zero_assigned_count == 2
    assert len(network.nodes) == 4
    assert network.dominant_source is PrimaryDirectionLatitudeSource.ASSIGNED_ZERO


def test_primary_direction_latitude_source_rejects_invalid_requests() -> None:
    with pytest.raises(ValueError):
        PrimaryDirectionLatitudeSourcePolicy("aspect_inherited")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        evaluate_primary_direction_latitude_source_aggregate([])
    with pytest.raises(ValueError):
        evaluate_primary_direction_latitude_source_network([])


def test_primary_direction_latitude_source_module_exports_curated_surface() -> None:
    expected = {
        "PrimaryDirectionLatitudeSource",
        "PrimaryDirectionLatitudeSourceRelationKind",
        "PrimaryDirectionLatitudeSourceConditionState",
        "PrimaryDirectionLatitudeSourcePolicy",
        "PrimaryDirectionLatitudeSourceTruth",
        "PrimaryDirectionLatitudeSourceClassification",
        "PrimaryDirectionLatitudeSourceRelation",
        "PrimaryDirectionLatitudeSourceRelationProfile",
        "PrimaryDirectionLatitudeSourceConditionProfile",
        "PrimaryDirectionLatitudeSourceAggregateProfile",
        "PrimaryDirectionLatitudeSourceNetworkNode",
        "PrimaryDirectionLatitudeSourceNetworkEdge",
        "PrimaryDirectionLatitudeSourceNetworkProfile",
        "primary_direction_latitude_source_truth",
        "classify_primary_direction_latitude_source",
        "relate_primary_direction_latitude_source",
        "evaluate_primary_direction_latitude_source_relations",
        "evaluate_primary_direction_latitude_source_condition",
        "evaluate_primary_direction_latitude_source_aggregate",
        "evaluate_primary_direction_latitude_source_network",
    }
    assert expected <= set(latitude_source_module.__all__)
