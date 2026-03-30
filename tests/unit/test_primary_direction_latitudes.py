from __future__ import annotations

import pytest

import moira.primary_directions.latitudes as latitude_module
from moira.primary_directions.latitudes import (
    PrimaryDirectionLatitudeConditionState,
    PrimaryDirectionLatitudeDoctrine,
    PrimaryDirectionLatitudePolicy,
    PrimaryDirectionLatitudeRelationKind,
    classify_primary_direction_latitude,
    evaluate_primary_direction_latitude_aggregate,
    evaluate_primary_direction_latitude_condition,
    evaluate_primary_direction_latitude_network,
    evaluate_primary_direction_latitude_relations,
    primary_direction_latitude_truth,
    relate_primary_direction_latitude,
)


def test_primary_direction_latitude_truth_exposes_current_doctrines() -> None:
    mundane = primary_direction_latitude_truth(PrimaryDirectionLatitudeDoctrine.MUNDANE_PRESERVED)
    zodiacal = primary_direction_latitude_truth(PrimaryDirectionLatitudeDoctrine.ZODIACAL_SUPPRESSED)
    retained = primary_direction_latitude_truth(
        PrimaryDirectionLatitudeDoctrine.ZODIACAL_PROMISSOR_RETAINED
    )
    conditioned = primary_direction_latitude_truth(
        PrimaryDirectionLatitudeDoctrine.ZODIACAL_SIGNIFICATOR_CONDITIONED
    )

    assert mundane.preserves_latitude is True
    assert mundane.zodiacal is False
    assert zodiacal.preserves_latitude is False
    assert zodiacal.zodiacal is True
    assert retained.preserves_latitude is True
    assert retained.zodiacal is True
    assert conditioned.preserves_latitude is True
    assert conditioned.zodiacal is True


def test_primary_direction_latitude_classification_relation_and_condition_are_stable() -> None:
    truth = primary_direction_latitude_truth()
    classification = classify_primary_direction_latitude(truth)
    relation = relate_primary_direction_latitude(truth)
    relation_profile = evaluate_primary_direction_latitude_relations(truth)
    condition = evaluate_primary_direction_latitude_condition(truth)

    assert classification.preserving is True
    assert classification.suppressing is False
    assert relation.relation_kind is PrimaryDirectionLatitudeRelationKind.BODY_LATITUDE_PRESERVED
    assert relation_profile.detected_relation == relation
    assert condition.state is PrimaryDirectionLatitudeConditionState.PRESERVING

    retained_truth = primary_direction_latitude_truth(
        PrimaryDirectionLatitudeDoctrine.ZODIACAL_PROMISSOR_RETAINED
    )
    retained_relation = relate_primary_direction_latitude(retained_truth)
    retained_condition = evaluate_primary_direction_latitude_condition(retained_truth)
    assert retained_relation.relation_kind is PrimaryDirectionLatitudeRelationKind.PROMISSOR_LATITUDE_RETAINED
    assert (
        retained_condition.state
        is PrimaryDirectionLatitudeConditionState.RETAINING_PROMISSOR_LATITUDE
    )

    conditioned_truth = primary_direction_latitude_truth(
        PrimaryDirectionLatitudeDoctrine.ZODIACAL_SIGNIFICATOR_CONDITIONED
    )
    conditioned_relation = relate_primary_direction_latitude(conditioned_truth)
    conditioned_condition = evaluate_primary_direction_latitude_condition(conditioned_truth)
    assert (
        conditioned_relation.relation_kind
        is PrimaryDirectionLatitudeRelationKind.SIGNIFICATOR_LATITUDE_CONDITIONED
    )
    assert (
        conditioned_condition.state
        is PrimaryDirectionLatitudeConditionState.CONDITIONING_ON_SIGNIFICATOR
    )


def test_primary_direction_latitude_aggregate_and_network_are_deterministic() -> None:
    truths = (
        primary_direction_latitude_truth(PrimaryDirectionLatitudeDoctrine.MUNDANE_PRESERVED),
        primary_direction_latitude_truth(PrimaryDirectionLatitudeDoctrine.ZODIACAL_SUPPRESSED),
        primary_direction_latitude_truth(PrimaryDirectionLatitudeDoctrine.ZODIACAL_PROMISSOR_RETAINED),
        primary_direction_latitude_truth(
            PrimaryDirectionLatitudeDoctrine.ZODIACAL_SIGNIFICATOR_CONDITIONED
        ),
        primary_direction_latitude_truth(PrimaryDirectionLatitudeDoctrine.ZODIACAL_SUPPRESSED),
    )
    aggregate = evaluate_primary_direction_latitude_aggregate(truths)
    network = evaluate_primary_direction_latitude_network(truths)

    assert aggregate.total_profiles == 5
    assert aggregate.preserving_count == 3
    assert aggregate.suppressing_count == 2
    assert len(network.nodes) == 4
    assert network.dominant_doctrine is PrimaryDirectionLatitudeDoctrine.ZODIACAL_SUPPRESSED


def test_primary_direction_latitude_rejects_invalid_requests() -> None:
    with pytest.raises(ValueError):
        PrimaryDirectionLatitudePolicy("retained_zodiacal")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        evaluate_primary_direction_latitude_aggregate([])
    with pytest.raises(ValueError):
        evaluate_primary_direction_latitude_network([])


def test_primary_direction_latitude_module_exports_curated_surface() -> None:
    expected = {
        "PrimaryDirectionLatitudeDoctrine",
        "PrimaryDirectionLatitudeRelationKind",
        "PrimaryDirectionLatitudeConditionState",
        "PrimaryDirectionLatitudePolicy",
        "PrimaryDirectionLatitudeTruth",
        "PrimaryDirectionLatitudeClassification",
        "PrimaryDirectionLatitudeRelation",
        "PrimaryDirectionLatitudeRelationProfile",
        "PrimaryDirectionLatitudeConditionProfile",
        "PrimaryDirectionLatitudeAggregateProfile",
        "PrimaryDirectionLatitudeNetworkNode",
        "PrimaryDirectionLatitudeNetworkEdge",
        "PrimaryDirectionLatitudeNetworkProfile",
        "primary_direction_latitude_truth",
        "classify_primary_direction_latitude",
        "relate_primary_direction_latitude",
        "evaluate_primary_direction_latitude_relations",
        "evaluate_primary_direction_latitude_condition",
        "evaluate_primary_direction_latitude_aggregate",
        "evaluate_primary_direction_latitude_network",
    }
    assert expected <= set(latitude_module.__all__)
