from __future__ import annotations

import pytest

import moira.primary_directions.converse as converse_module
from moira.primary_directions.converse import (
    SIGNED_PRIMARY_MOTION_TOLERANCE_DEG,
    PrimaryDirectionConverseConditionState,
    PrimaryDirectionConverseDoctrine,
    PrimaryDirectionConversePolicy,
    PrimaryDirectionConverseRelationKind,
    PrimaryDirectionMotion,
    PrimaryDirectionSignedMotionResolution,
    classify_primary_direction_converse,
    evaluate_primary_direction_converse_aggregate,
    evaluate_primary_direction_converse_condition,
    evaluate_primary_direction_converse_network,
    evaluate_primary_direction_converse_relations,
    primary_direction_converse_truth,
    relate_primary_direction_converse,
    resolve_signed_primary_motion,
)


def test_primary_direction_converse_truth_exposes_current_doctrines() -> None:
    direct_only = primary_direction_converse_truth(PrimaryDirectionConverseDoctrine.DIRECT_ONLY)
    traditional = primary_direction_converse_truth(
        PrimaryDirectionConverseDoctrine.TRADITIONAL_CONVERSE
    )
    signed = primary_direction_converse_truth(
        PrimaryDirectionConverseDoctrine.SIGNED_PRIMARY_MOTION
    )

    assert direct_only.includes_direct is True
    assert direct_only.includes_converse is False
    assert direct_only.motion_count == 1
    assert traditional.includes_direct is True
    assert traditional.includes_converse is True
    assert traditional.motion_count == 2
    assert signed.includes_direct is True
    assert signed.includes_converse is True
    assert signed.motion_count == 2


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


def test_signed_primary_motion_has_distinct_relation_and_condition_truth() -> None:
    truth = primary_direction_converse_truth(
        PrimaryDirectionConverseDoctrine.SIGNED_PRIMARY_MOTION
    )
    relation = relate_primary_direction_converse(truth)
    condition = evaluate_primary_direction_converse_condition(truth)

    assert relation.relation_kind is PrimaryDirectionConverseRelationKind.SIGNED_PRIMARY_MOTION
    assert relation.admitted_motions == ("direct", "converse")
    assert condition.state is PrimaryDirectionConverseConditionState.SIGNED_DIRECT_OR_CONVERSE


def test_signed_primary_motion_resolves_positive_negative_and_zero_arcs() -> None:
    direct = resolve_signed_primary_motion(12.5)
    converse = resolve_signed_primary_motion(354.63)
    zero_inputs = (
        0.0,
        SIGNED_PRIMARY_MOTION_TOLERANCE_DEG / 2.0,
        -SIGNED_PRIMARY_MOTION_TOLERANCE_DEG,
        360.0 - SIGNED_PRIMARY_MOTION_TOLERANCE_DEG / 2.0,
        720.0,
    )

    assert direct == PrimaryDirectionSignedMotionResolution(
        signed_arc=12.5,
        magnitude=12.5,
        motion=PrimaryDirectionMotion.DIRECT,
    )
    assert converse.signed_arc == pytest.approx(-5.37)
    assert converse.magnitude == pytest.approx(5.37)
    assert converse.motion is PrimaryDirectionMotion.CONVERSE
    for raw_arc in zero_inputs:
        assert resolve_signed_primary_motion(raw_arc) == (
            PrimaryDirectionSignedMotionResolution(
                signed_arc=0.0,
                magnitude=0.0,
                motion=None,
            )
        )
    assert resolve_signed_primary_motion(372.5) == direct
    assert resolve_signed_primary_motion(-5.37).motion is PrimaryDirectionMotion.CONVERSE


def test_signed_primary_motion_fails_closed_at_antipode_and_invalid_inputs() -> None:
    for raw_arc in (
        180.0,
        -180.0,
        180.0 - SIGNED_PRIMARY_MOTION_TOLERANCE_DEG / 2.0,
        180.0 + SIGNED_PRIMARY_MOTION_TOLERANCE_DEG / 2.0,
        540.0,
    ):
        with pytest.raises(ValueError, match="directionally ambiguous"):
            resolve_signed_primary_motion(raw_arc)
    for raw_arc in (True, float("nan"), float("inf"), "5"):
        with pytest.raises(ValueError, match="finite real"):
            resolve_signed_primary_motion(raw_arc)  # type: ignore[arg-type]


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
    with pytest.raises(ValueError, match="Unsupported primary direction converse doctrine"):
        converse_module.PrimaryDirectionConverseTruth(
            doctrine="bogus",  # type: ignore[arg-type]
            includes_direct=True,
            includes_converse=True,
            motion_count=2,
        )
    with pytest.raises(ValueError):
        evaluate_primary_direction_converse_aggregate([])
    with pytest.raises(ValueError):
        evaluate_primary_direction_converse_network([])


def test_primary_direction_converse_module_exports_curated_surface() -> None:
    expected = {
        "PrimaryDirectionConverseDoctrine",
        "PrimaryDirectionMotion",
        "PrimaryDirectionConverseRelationKind",
        "PrimaryDirectionConverseConditionState",
        "PrimaryDirectionSignedMotionResolution",
        "SIGNED_PRIMARY_MOTION_TOLERANCE_DEG",
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
        "resolve_signed_primary_motion",
    }
    assert expected <= set(converse_module.__all__)
