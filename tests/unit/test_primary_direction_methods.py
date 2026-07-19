from __future__ import annotations

import pytest

import moira.primary_directions.methods as method_module
from moira.primary_directions.methods import (
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
    assert truth.under_pole_based is False


def test_primary_direction_method_classification_relation_and_condition_are_stable() -> None:
    truth = primary_direction_method_truth()
    classification = classify_primary_direction_method(truth)
    relation = relate_primary_direction_method(truth)
    relation_profile = evaluate_primary_direction_method_relations(truth)
    condition = evaluate_primary_direction_method_condition(truth)

    assert classification.mundane is True
    assert classification.zodiacal is False
    assert classification.semi_arc_based is True
    assert classification.under_pole_based is False
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


def test_primary_direction_method_truth_admits_ptolemaic_semi_arc_branch() -> None:
    truth = primary_direction_method_truth(PrimaryDirectionMethod.PTOLEMY_SEMI_ARC)
    classification = classify_primary_direction_method(truth)
    relation = relate_primary_direction_method(truth)
    condition = evaluate_primary_direction_method_condition(truth)

    assert truth.kind is PrimaryDirectionMethodKind.PTOLEMY_SEMI_ARC
    assert truth.uses_semi_arcs is True
    assert truth.under_pole_based is False
    assert classification.mundane is True
    assert classification.zodiacal is True
    assert classification.semi_arc_based is True
    assert relation.relation_kind is PrimaryDirectionMethodRelationKind.PTOLEMAIC_SEMI_ARC_PERFECTION
    assert condition.state is PrimaryDirectionMethodConditionState.PTOLEMAIC_SEMI_ARC_GROUNDED


def test_primary_direction_method_truth_admits_regiomontanus_branch() -> None:
    truth = primary_direction_method_truth(PrimaryDirectionMethod.REGIOMONTANUS)
    classification = classify_primary_direction_method(truth)
    relation = relate_primary_direction_method(truth)
    condition = evaluate_primary_direction_method_condition(truth)

    assert truth.kind is PrimaryDirectionMethodKind.REGIOMONTANUS
    assert truth.uses_semi_arcs is False
    assert truth.under_pole_based is True
    assert classification.mundane is True
    assert classification.zodiacal is True
    assert classification.under_pole_based is True
    assert (
        relation.relation_kind
        is PrimaryDirectionMethodRelationKind.REGIOMONTANIAN_UNDER_POLE_PERFECTION
    )
    assert condition.state is PrimaryDirectionMethodConditionState.UNDER_POLE_GROUNDED


def test_primary_direction_method_truth_admits_meridian_branch() -> None:
    truth = primary_direction_method_truth(PrimaryDirectionMethod.MERIDIAN)
    classification = classify_primary_direction_method(truth)
    relation = relate_primary_direction_method(truth)
    condition = evaluate_primary_direction_method_condition(truth)

    assert truth.kind is PrimaryDirectionMethodKind.MERIDIAN
    assert truth.uses_semi_arcs is False
    assert truth.under_pole_based is False
    assert classification.mundane is True
    assert classification.zodiacal is True
    assert classification.under_pole_based is False
    assert relation.relation_kind is PrimaryDirectionMethodRelationKind.MERIDIAN_EQUATORIAL_PERFECTION
    assert condition.state is PrimaryDirectionMethodConditionState.EQUATORIAL_GROUNDED


def test_primary_direction_method_truth_admits_morinus_branch() -> None:
    truth = primary_direction_method_truth(PrimaryDirectionMethod.MORINUS)
    classification = classify_primary_direction_method(truth)
    relation = relate_primary_direction_method(truth)
    condition = evaluate_primary_direction_method_condition(truth)

    assert truth.kind is PrimaryDirectionMethodKind.MORINUS
    assert truth.uses_semi_arcs is False
    assert truth.under_pole_based is True
    assert classification.mundane is True
    assert classification.zodiacal is True
    assert classification.under_pole_based is True
    assert relation.relation_kind is PrimaryDirectionMethodRelationKind.MORINIAN_UNDER_POLE_PERFECTION
    assert condition.state is PrimaryDirectionMethodConditionState.MORINIAN_UNDER_POLE_GROUNDED


def test_primary_direction_method_truth_admits_campanus_branch() -> None:
    truth = primary_direction_method_truth(PrimaryDirectionMethod.CAMPANUS)
    classification = classify_primary_direction_method(truth)
    relation = relate_primary_direction_method(truth)
    condition = evaluate_primary_direction_method_condition(truth)

    assert truth.kind is PrimaryDirectionMethodKind.CAMPANUS
    assert truth.uses_semi_arcs is False
    assert truth.under_pole_based is True
    assert classification.mundane is True
    assert classification.zodiacal is True
    assert classification.under_pole_based is True
    assert relation.relation_kind is PrimaryDirectionMethodRelationKind.CAMPANIAN_UNDER_POLE_PERFECTION
    assert condition.state is PrimaryDirectionMethodConditionState.PRIME_VERTICAL_UNDER_POLE_GROUNDED


def test_primary_direction_method_truth_admits_topocentric_branch() -> None:
    truth = primary_direction_method_truth(PrimaryDirectionMethod.TOPOCENTRIC)
    classification = classify_primary_direction_method(truth)
    relation = relate_primary_direction_method(truth)
    condition = evaluate_primary_direction_method_condition(truth)

    assert truth.kind is PrimaryDirectionMethodKind.TOPOCENTRIC
    assert truth.uses_semi_arcs is False
    assert truth.under_pole_based is True
    assert classification.mundane is True
    assert classification.zodiacal is True
    assert classification.under_pole_based is True
    assert relation.relation_kind is PrimaryDirectionMethodRelationKind.TOPOCENTRIC_UNDER_POLE_PERFECTION
    assert condition.state is PrimaryDirectionMethodConditionState.TOPOCENTRIC_UNDER_POLE_GROUNDED


def test_primary_direction_methods_aggregate_and_network_are_deterministic() -> None:
    truths = (
        primary_direction_method_truth(),
        primary_direction_method_truth(PrimaryDirectionMethod.PTOLEMY_SEMI_ARC),
        primary_direction_method_truth(PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC),
        primary_direction_method_truth(PrimaryDirectionMethod.MERIDIAN),
        primary_direction_method_truth(PrimaryDirectionMethod.MORINUS),
        primary_direction_method_truth(PrimaryDirectionMethod.REGIOMONTANUS),
        primary_direction_method_truth(PrimaryDirectionMethod.CAMPANUS),
        primary_direction_method_truth(PrimaryDirectionMethod.TOPOCENTRIC),
    )
    aggregate = evaluate_primary_direction_methods_aggregate(truths)
    network = evaluate_primary_direction_methods_network(truths)

    assert aggregate.total_profiles == 8
    assert aggregate.mundane_count == 8
    assert aggregate.semi_arc_count == 3
    assert aggregate.under_pole_count == 4
    assert aggregate.zodiacal_count == 6
    assert len(network.nodes) == 8
    assert {node.method for node in network.nodes} == {
        PrimaryDirectionMethod.PLACIDUS_MUNDANE,
        PrimaryDirectionMethod.PTOLEMY_SEMI_ARC,
        PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC,
        PrimaryDirectionMethod.MERIDIAN,
        PrimaryDirectionMethod.MORINUS,
        PrimaryDirectionMethod.REGIOMONTANUS,
        PrimaryDirectionMethod.CAMPANUS,
        PrimaryDirectionMethod.TOPOCENTRIC,
    }


def test_primary_direction_methods_reject_invalid_requests() -> None:
    with pytest.raises(ValueError):
        PrimaryDirectionMethodPolicy("regiomontanus")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        evaluate_primary_direction_methods_aggregate([])
    with pytest.raises(ValueError):
        evaluate_primary_direction_methods_network([])
    with pytest.raises(ValueError):
        primary_direction_method_truth("regiomontanus")  # type: ignore[arg-type]


def test_primary_direction_method_collections_are_defensive_and_strict() -> None:
    truth = primary_direction_method_truth()
    relation = relate_primary_direction_method(truth)
    admitted = [relation]
    scored = [relation]
    profile = method_module.PrimaryDirectionMethodRelationProfile(
        truth=truth,
        detected_relation=relation,
        admitted_relations=admitted,  # type: ignore[arg-type]
        scored_relations=scored,  # type: ignore[arg-type]
    )
    admitted.clear()
    scored.clear()
    assert profile.admitted_relations == (relation,)
    assert profile.scored_relations == (relation,)

    with pytest.raises(ValueError):
        method_module.PrimaryDirectionMethodTruth(
            method="placidus_mundane",  # type: ignore[arg-type]
            kind=PrimaryDirectionMethodKind.PLACIDUS_MUNDANE,
            uses_semi_arcs=True,
            uses_world_frame_geometry=True,
            latitude_sensitive=True,
            under_pole_based=False,
        )
    with pytest.raises(ValueError):
        method_module.PrimaryDirectionMethodClassification(
            truth=truth,
            mundane=1,  # type: ignore[arg-type]
            zodiacal=False,
            semi_arc_based=True,
            under_pole_based=False,
        )


def test_primary_direction_method_aggregate_and_network_reject_false_structure() -> None:
    truths = (
        primary_direction_method_truth(PrimaryDirectionMethod.PLACIDUS_MUNDANE),
        primary_direction_method_truth(PrimaryDirectionMethod.PTOLEMY_SEMI_ARC),
    )
    aggregate = evaluate_primary_direction_methods_aggregate(truths)
    profiles = list(aggregate.profiles)
    defensive_aggregate = method_module.PrimaryDirectionMethodsAggregateProfile(
        profiles=profiles,  # type: ignore[arg-type]
        total_profiles=2,
        mundane_count=2,
        semi_arc_count=2,
        under_pole_count=0,
    )
    profiles.clear()
    assert defensive_aggregate.total_profiles == 2
    with pytest.raises(ValueError):
        method_module.PrimaryDirectionMethodsAggregateProfile(
            profiles=aggregate.profiles,
            total_profiles=2,
            mundane_count=2,
            semi_arc_count=1,
            under_pole_count=0,
        )

    network = evaluate_primary_direction_methods_network(truths)
    nodes = list(network.nodes)
    edges = list(network.edges)
    isolated = list(network.isolated_methods)
    defensive_network = method_module.PrimaryDirectionMethodsNetworkProfile(
        nodes=nodes,  # type: ignore[arg-type]
        edges=edges,  # type: ignore[arg-type]
        dominant_method=network.dominant_method,
        isolated_methods=isolated,  # type: ignore[arg-type]
    )
    nodes.clear()
    edges.clear()
    isolated.clear()
    assert defensive_network == network

    dangling = method_module.PrimaryDirectionMethodsNetworkEdge(
        from_method=PrimaryDirectionMethod.PLACIDUS_MUNDANE,
        to_method=PrimaryDirectionMethod.CAMPANUS,
        count=1,
    )
    with pytest.raises(ValueError):
        method_module.PrimaryDirectionMethodsNetworkProfile(
            nodes=network.nodes,
            edges=(dangling,),
            dominant_method=network.dominant_method,
            isolated_methods=(),
        )
    with pytest.raises(ValueError):
        method_module.PrimaryDirectionMethodsNetworkNode(
            method=PrimaryDirectionMethod.PLACIDUS_MUNDANE,
            count=True,  # type: ignore[arg-type]
        )

    with pytest.raises(ValueError, match="transition degrees"):
        method_module.PrimaryDirectionMethodsNetworkProfile(
            nodes=tuple(
                method_module.PrimaryDirectionMethodsNetworkNode(method=item, count=1)
                for item in (
                    PrimaryDirectionMethod.PLACIDUS_MUNDANE,
                    PrimaryDirectionMethod.CAMPANUS,
                    PrimaryDirectionMethod.MERIDIAN,
                )
            ),
            edges=(
                method_module.PrimaryDirectionMethodsNetworkEdge(
                    PrimaryDirectionMethod.PLACIDUS_MUNDANE,
                    PrimaryDirectionMethod.CAMPANUS,
                    1,
                ),
                method_module.PrimaryDirectionMethodsNetworkEdge(
                    PrimaryDirectionMethod.PLACIDUS_MUNDANE,
                    PrimaryDirectionMethod.MERIDIAN,
                    1,
                ),
            ),
            dominant_method=PrimaryDirectionMethod.PLACIDUS_MUNDANE,
            isolated_methods=(),
        )


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
