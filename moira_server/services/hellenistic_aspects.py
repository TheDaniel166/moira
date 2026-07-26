"""Kernel-free service composition for whole-sign aspect relations."""

from __future__ import annotations

from moira.aspects import (
    HellenisticSuperiorityTruth,
    find_whole_sign_aspects,
    hellenistic_superiority_truth,
)

from ..models.hellenistic_aspects import (
    HellenisticAspectClassificationResponse,
    HellenisticDirectionTruthResponse,
    HellenisticOvercomingTruthResponse,
    HellenisticAspectProvenanceResponse,
    HellenisticSuperiorityTruthResponse,
    OvercomingRequest,
    OvercomingResponse,
    WholeSignAspectResponse,
    WholeSignAspectsRequest,
    WholeSignAspectsResponse,
)


_SOURCE_REFS = [
    "Ptolemy, Tetrabiblos I.13",
    "Vettius Valens, Anthologies",
]


def _serialize_superiority_truth(
    truth: HellenisticSuperiorityTruth,
) -> HellenisticSuperiorityTruthResponse:
    return HellenisticSuperiorityTruthResponse(
        body1=truth.body1,
        body2=truth.body2,
        longitude1=truth.longitude1,
        longitude2=truth.longitude2,
        direction_truth=HellenisticDirectionTruthResponse(
            status=truth.direction_truth.status,
            aspect_angle_deg=truth.direction_truth.aspect_angle_deg,
            forward_arc_body1_to_body2_deg=(
                truth.direction_truth.forward_arc_body1_to_body2_deg
            ),
            direction=truth.direction_truth.direction,
            reason=truth.direction_truth.reason,
        ),
        overcoming_truth=HellenisticOvercomingTruthResponse(
            status=truth.overcoming_truth.status,
            body1_sign_index=truth.overcoming_truth.body1_sign_index,
            body2_sign_index=truth.overcoming_truth.body2_sign_index,
            body1_place_from_body2=truth.overcoming_truth.body1_place_from_body2,
            body2_place_from_body1=truth.overcoming_truth.body2_place_from_body1,
            relation=truth.overcoming_truth.relation,
            reason=truth.overcoming_truth.reason,
        ),
    )


def compute_whole_sign_aspects(
    request: WholeSignAspectsRequest,
) -> WholeSignAspectsResponse:
    # Keep serialization pure for each request without retaining ambient state.
    aspects = find_whole_sign_aspects(request.positions)
    serialized: list[WholeSignAspectResponse] = []
    for aspect in aspects:
        classification = aspect.classification
        if classification is None:
            raise ValueError("whole-sign aspect must preserve its classification")
        if aspect.sign_degree1 is None or aspect.sign_degree2 is None:
            raise ValueError("whole-sign aspect must preserve both sign degrees")
        superiority_truth = aspect.hellenistic_superiority_truth
        if superiority_truth is None:
            raise ValueError("whole-sign aspect must preserve superiority truth")
        serialized.append(
            WholeSignAspectResponse(
                body1=aspect.body1,
                body2=aspect.body2,
                aspect=aspect.aspect,
                symbol=aspect.symbol,
                angle=aspect.angle,
                separation=aspect.separation,
                direction=aspect.direction.value if aspect.direction is not None else None,
                sign_degree1=aspect.sign_degree1,
                sign_degree2=aspect.sign_degree2,
                body1_overcomes_body2=superiority_truth.body1_overcomes_body2,
                body2_overcomes_body1=superiority_truth.body2_overcomes_body1,
                hellenistic_superiority_truth=_serialize_superiority_truth(
                    superiority_truth
                ),
                classification=HellenisticAspectClassificationResponse(
                    domain=classification.domain.value,
                    tier=classification.tier.value,
                    family=classification.family.value,
                ),
            )
        )

    return WholeSignAspectsResponse(
        aspects=serialized,
        count=len(serialized),
        provenance=HellenisticAspectProvenanceResponse(
            engine_entrypoint="find_whole_sign_aspects",
            doctrine="whole_sign_ptolemaic_aspects_with_direction_and_overcoming",
            source_refs=_SOURCE_REFS,
            stage_sequence=[
                "caller_position_validation",
                "whole_sign_relation_classification",
                "sinister_dexter_direction",
                "tenth_sign_overcoming_relation",
                "lossless_response_serialization",
            ],
        ),
    )


def compute_overcoming(request: OvercomingRequest) -> OvercomingResponse:
    truth = hellenistic_superiority_truth(
        request.longitude1,
        request.longitude2,
        body1=request.body1,
        body2=request.body2,
    )
    return OvercomingResponse(
        body1=truth.body1,
        longitude1=truth.longitude1,
        body2=truth.body2,
        longitude2=truth.longitude2,
        body1_overcomes_body2=truth.body1_overcomes_body2,
        body2_overcomes_body1=truth.body2_overcomes_body1,
        overcoming_body=truth.overcoming_body,
        hellenistic_superiority_truth=_serialize_superiority_truth(truth),
        provenance=HellenisticAspectProvenanceResponse(
            engine_entrypoint="hellenistic_superiority_truth",
            doctrine="tenth_sign_overcoming",
            source_refs=_SOURCE_REFS,
            stage_sequence=[
                "caller_position_validation",
                "bidirectional_tenth_sign_relation",
                "lossless_response_serialization",
            ],
        ),
    )


__all__ = [
    "compute_overcoming",
    "compute_whole_sign_aspects",
]
