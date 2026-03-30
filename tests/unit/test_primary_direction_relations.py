from __future__ import annotations

import pytest

import moira.primary_directions.relations as relation_module
from moira.primary_directions.relations import (
    PrimaryDirectionRelationPolicy,
    PrimaryDirectionRelationalConditionState,
    PrimaryDirectionRelationalKind,
    PrimaryDirectionRelationalMode,
    classify_primary_direction_relation,
    default_positional_relation_policy,
    antiscia_relation_policy,
    evaluate_primary_direction_relation_condition,
    evaluate_primary_direction_relation_relations,
    evaluate_primary_direction_relations_aggregate,
    evaluate_primary_direction_relations_network,
    placidian_rapt_parallel_relation_policy,
    ptolemaic_parallel_relation_policy,
    primary_direction_relational_truth,
    relate_primary_direction_relation,
    zodiacal_aspect_relation_policy,
)


def test_primary_direction_relational_truth_exposes_positional_and_declinational_families() -> None:
    conjunction = primary_direction_relational_truth()
    assert conjunction.kind is PrimaryDirectionRelationalKind.CONJUNCTION
    assert conjunction.mode is PrimaryDirectionRelationalMode.POSITIONAL
    assert conjunction.derived_point_realizable is False

    aspect = primary_direction_relational_truth(PrimaryDirectionRelationalKind.ZODIACAL_ASPECT)
    assert aspect.mode is PrimaryDirectionRelationalMode.POSITIONAL
    assert aspect.derived_point_realizable is True

    antiscion = primary_direction_relational_truth(PrimaryDirectionRelationalKind.ANTISCION)
    assert antiscion.mode is PrimaryDirectionRelationalMode.POSITIONAL
    assert antiscion.derived_point_realizable is True

    parallel = primary_direction_relational_truth(PrimaryDirectionRelationalKind.PARALLEL)
    assert parallel.mode is PrimaryDirectionRelationalMode.DECLINATIONAL
    assert parallel.derived_point_realizable is True

    rapt_parallel = primary_direction_relational_truth(PrimaryDirectionRelationalKind.RAPT_PARALLEL)
    assert rapt_parallel.mode is PrimaryDirectionRelationalMode.DECLINATIONAL
    assert rapt_parallel.derived_point_realizable is False


def test_primary_direction_relational_classification_relation_and_condition_are_stable() -> None:
    truth = primary_direction_relational_truth(PrimaryDirectionRelationalKind.CONTRA_PARALLEL)
    classification = classify_primary_direction_relation(truth)
    relation = relate_primary_direction_relation(truth)
    relation_profile = evaluate_primary_direction_relation_relations(
        truth,
        policy=PrimaryDirectionRelationPolicy(
            frozenset({PrimaryDirectionRelationalKind.CONTRA_PARALLEL})
        ),
    )
    condition = evaluate_primary_direction_relation_condition(truth)

    assert classification.positional is False
    assert classification.declinational is True
    assert relation.relation_kind is PrimaryDirectionRelationalKind.CONTRA_PARALLEL
    assert relation_profile.detected_relation == relation
    assert condition.state is PrimaryDirectionRelationalConditionState.DECLINATIONAL_ADMITTED


def test_primary_direction_relations_aggregate_and_network_are_deterministic() -> None:
    truths = (
        primary_direction_relational_truth(),
        primary_direction_relational_truth(PrimaryDirectionRelationalKind.ZODIACAL_ASPECT),
        primary_direction_relational_truth(PrimaryDirectionRelationalKind.PARALLEL),
        primary_direction_relational_truth(PrimaryDirectionRelationalKind.CONTRA_PARALLEL),
    )
    aggregate = evaluate_primary_direction_relations_aggregate(truths)
    network = evaluate_primary_direction_relations_network(truths)

    assert aggregate.total_profiles == 4
    assert aggregate.positional_count == 2
    assert aggregate.declinational_count == 2
    assert len(network.nodes) == 4
    assert network.dominant_kind is PrimaryDirectionRelationalKind.ZODIACAL_ASPECT


def test_primary_direction_relations_reject_invalid_requests() -> None:
    with pytest.raises(ValueError):
        PrimaryDirectionRelationPolicy(frozenset())
    with pytest.raises(ValueError):
        evaluate_primary_direction_relations_aggregate([])
    with pytest.raises(ValueError):
        evaluate_primary_direction_relations_network([])


def test_primary_direction_relations_module_exports_curated_surface() -> None:
    expected = {
        "PrimaryDirectionRelationalKind",
        "PrimaryDirectionRelationalMode",
        "PrimaryDirectionRelationalConditionState",
        "PrimaryDirectionRelationPolicy",
        "default_positional_relation_policy",
        "antiscia_relation_policy",
        "zodiacal_aspect_relation_policy",
        "ptolemaic_parallel_relation_policy",
        "placidian_rapt_parallel_relation_policy",
        "PrimaryDirectionRelationalTruth",
        "PrimaryDirectionRelationalClassification",
        "PrimaryDirectionRelationalRelation",
        "PrimaryDirectionRelationalRelationProfile",
        "PrimaryDirectionRelationalConditionProfile",
        "PrimaryDirectionRelationsAggregateProfile",
        "PrimaryDirectionRelationsNetworkNode",
        "PrimaryDirectionRelationsNetworkEdge",
        "PrimaryDirectionRelationsNetworkProfile",
        "primary_direction_relational_truth",
        "classify_primary_direction_relation",
        "relate_primary_direction_relation",
        "evaluate_primary_direction_relation_relations",
        "evaluate_primary_direction_relation_condition",
        "evaluate_primary_direction_relations_aggregate",
        "evaluate_primary_direction_relations_network",
    }
    assert expected <= set(relation_module.__all__)


def test_primary_direction_relation_policy_presets_are_explicit() -> None:
    assert default_positional_relation_policy().admitted_kinds == frozenset(
        {
            PrimaryDirectionRelationalKind.CONJUNCTION,
            PrimaryDirectionRelationalKind.OPPOSITION,
        }
    )
    assert zodiacal_aspect_relation_policy().admitted_kinds == frozenset(
        {
            PrimaryDirectionRelationalKind.CONJUNCTION,
            PrimaryDirectionRelationalKind.OPPOSITION,
            PrimaryDirectionRelationalKind.ZODIACAL_ASPECT,
        }
    )
    assert antiscia_relation_policy().admitted_kinds == frozenset(
        {
            PrimaryDirectionRelationalKind.CONJUNCTION,
            PrimaryDirectionRelationalKind.OPPOSITION,
            PrimaryDirectionRelationalKind.ANTISCION,
            PrimaryDirectionRelationalKind.CONTRA_ANTISCION,
        }
    )
    assert ptolemaic_parallel_relation_policy().admitted_kinds == frozenset(
        {
            PrimaryDirectionRelationalKind.CONJUNCTION,
            PrimaryDirectionRelationalKind.OPPOSITION,
            PrimaryDirectionRelationalKind.ZODIACAL_ASPECT,
            PrimaryDirectionRelationalKind.PARALLEL,
            PrimaryDirectionRelationalKind.CONTRA_PARALLEL,
        }
    )
    assert placidian_rapt_parallel_relation_policy().admitted_kinds == frozenset(
        {
            PrimaryDirectionRelationalKind.RAPT_PARALLEL,
        }
    )
