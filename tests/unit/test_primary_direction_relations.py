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

    opposition = primary_direction_relational_truth(PrimaryDirectionRelationalKind.OPPOSITION)
    assert opposition.mode is PrimaryDirectionRelationalMode.POSITIONAL
    assert opposition.derived_point_realizable is True

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
    policy = PrimaryDirectionRelationPolicy(
        frozenset({PrimaryDirectionRelationalKind.CONTRA_PARALLEL})
    )
    classification = classify_primary_direction_relation(truth)
    relation = relate_primary_direction_relation(truth)
    relation_profile = evaluate_primary_direction_relation_relations(
        truth,
        policy=policy,
    )
    condition = evaluate_primary_direction_relation_condition(truth, policy=policy)

    assert classification.positional is False
    assert classification.declinational is True
    assert relation.relation_kind is PrimaryDirectionRelationalKind.CONTRA_PARALLEL
    assert relation_profile.detected_relation == relation
    assert condition.state is PrimaryDirectionRelationalConditionState.DECLINATIONAL_ADMITTED

    rejected_profile = evaluate_primary_direction_relation_relations(truth)
    rejected_condition = evaluate_primary_direction_relation_condition(truth)
    assert rejected_profile.detected_relation == relation
    assert rejected_profile.admitted_relations == ()
    assert rejected_profile.scored_relations == ()
    assert rejected_condition.state is PrimaryDirectionRelationalConditionState.DECLINATIONAL_REJECTED


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
    assert aggregate.admitted_count == 2
    assert aggregate.rejected_count == 2
    assert len(network.nodes) == 4
    assert network.dominant_kind is PrimaryDirectionRelationalKind.ZODIACAL_ASPECT


def test_primary_direction_relations_reject_invalid_requests() -> None:
    with pytest.raises(ValueError):
        PrimaryDirectionRelationPolicy(frozenset())
    with pytest.raises(ValueError):
        evaluate_primary_direction_relations_aggregate([])
    with pytest.raises(ValueError):
        evaluate_primary_direction_relations_network([])
    with pytest.raises(ValueError):
        primary_direction_relational_truth("conjunction")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        PrimaryDirectionRelationPolicy({"conjunction"})  # type: ignore[arg-type]


def test_primary_direction_relation_collections_are_defensive_and_strict() -> None:
    admitted = {PrimaryDirectionRelationalKind.CONJUNCTION}
    policy = PrimaryDirectionRelationPolicy(admitted)  # type: ignore[arg-type]
    admitted.clear()
    assert policy.admitted_kinds == frozenset({PrimaryDirectionRelationalKind.CONJUNCTION})

    truth = primary_direction_relational_truth()
    relation = relate_primary_direction_relation(truth)
    admitted_relations = [relation]
    scored_relations = [relation]
    profile = relation_module.PrimaryDirectionRelationalRelationProfile(
        truth=truth,
        detected_relation=relation,
        admitted_relations=admitted_relations,  # type: ignore[arg-type]
        scored_relations=scored_relations,  # type: ignore[arg-type]
    )
    admitted_relations.clear()
    scored_relations.clear()
    assert profile.admitted_relations == (relation,)
    assert profile.scored_relations == (relation,)

    classification = classify_primary_direction_relation(truth)
    with pytest.raises(ValueError):
        relation_module.PrimaryDirectionRelationalConditionProfile(
            truth=truth,
            classification=classification,
            relation_profile=profile,
            state=PrimaryDirectionRelationalConditionState.POSITIONAL_REJECTED,
        )


def test_primary_direction_relations_aggregate_and_network_validate_complete_invariants() -> None:
    truths = (
        primary_direction_relational_truth(PrimaryDirectionRelationalKind.CONJUNCTION),
        primary_direction_relational_truth(PrimaryDirectionRelationalKind.OPPOSITION),
        primary_direction_relational_truth(PrimaryDirectionRelationalKind.ZODIACAL_ASPECT),
    )
    aggregate = evaluate_primary_direction_relations_aggregate(truths)
    profiles = list(aggregate.profiles)
    defensive_aggregate = relation_module.PrimaryDirectionRelationsAggregateProfile(
        profiles=profiles,  # type: ignore[arg-type]
        total_profiles=3,
        positional_count=3,
        declinational_count=0,
    )
    profiles.clear()
    assert defensive_aggregate.total_profiles == 3
    with pytest.raises(ValueError):
        relation_module.PrimaryDirectionRelationsAggregateProfile(
            profiles=aggregate.profiles,
            total_profiles=3,
            positional_count=2,
            declinational_count=1,
        )

    network = evaluate_primary_direction_relations_network(truths)
    nodes = list(network.nodes)
    edges = list(network.edges)
    isolated = list(network.isolated_kinds)
    defensive_network = relation_module.PrimaryDirectionRelationsNetworkProfile(
        nodes=nodes,  # type: ignore[arg-type]
        edges=edges,  # type: ignore[arg-type]
        dominant_kind=network.dominant_kind,
        isolated_kinds=isolated,  # type: ignore[arg-type]
    )
    nodes.clear()
    edges.clear()
    isolated.clear()
    assert defensive_network == network

    dangling = relation_module.PrimaryDirectionRelationsNetworkEdge(
        from_kind=PrimaryDirectionRelationalKind.CONJUNCTION,
        to_kind=PrimaryDirectionRelationalKind.PARALLEL,
        count=1,
    )
    with pytest.raises(ValueError):
        relation_module.PrimaryDirectionRelationsNetworkProfile(
            nodes=network.nodes,
            edges=(dangling,),
            dominant_kind=network.dominant_kind,
            isolated_kinds=(),
        )
    with pytest.raises(ValueError):
        relation_module.PrimaryDirectionRelationsNetworkNode(
            kind=PrimaryDirectionRelationalKind.CONJUNCTION,
            count=True,  # type: ignore[arg-type]
        )

    with pytest.raises(ValueError, match="transition degrees"):
        relation_module.PrimaryDirectionRelationsNetworkProfile(
            nodes=tuple(
                relation_module.PrimaryDirectionRelationsNetworkNode(kind=item, count=1)
                for item in (
                    PrimaryDirectionRelationalKind.CONJUNCTION,
                    PrimaryDirectionRelationalKind.OPPOSITION,
                    PrimaryDirectionRelationalKind.ZODIACAL_ASPECT,
                )
            ),
            edges=(
                relation_module.PrimaryDirectionRelationsNetworkEdge(
                    PrimaryDirectionRelationalKind.CONJUNCTION,
                    PrimaryDirectionRelationalKind.OPPOSITION,
                    1,
                ),
                relation_module.PrimaryDirectionRelationsNetworkEdge(
                    PrimaryDirectionRelationalKind.CONJUNCTION,
                    PrimaryDirectionRelationalKind.ZODIACAL_ASPECT,
                    1,
                ),
            ),
            dominant_kind=PrimaryDirectionRelationalKind.CONJUNCTION,
            isolated_kinds=(),
        )

    reversed_network = evaluate_primary_direction_relations_network(reversed(truths))
    assert {(edge.from_kind, edge.to_kind) for edge in network.edges} != {
        (edge.from_kind, edge.to_kind) for edge in reversed_network.edges
    }


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
