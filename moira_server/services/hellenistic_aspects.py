"""Kernel-free service composition for whole-sign aspect relations."""

from __future__ import annotations

from moira.aspects import find_whole_sign_aspects, overcoming

from ..models.hellenistic_aspects import (
    HellenisticAspectClassificationResponse,
    HellenisticAspectProvenanceResponse,
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
                body1_overcomes_body2=overcoming(
                    request.positions[aspect.body1], request.positions[aspect.body2]
                ),
                body2_overcomes_body1=overcoming(
                    request.positions[aspect.body2], request.positions[aspect.body1]
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
            engine_entrypoint="find_whole_sign_aspects+overcoming",
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
    body1_overcomes = overcoming(request.longitude1, request.longitude2)
    body2_overcomes = overcoming(request.longitude2, request.longitude1)
    overcoming_body = (
        request.body1
        if body1_overcomes
        else request.body2
        if body2_overcomes
        else None
    )
    return OvercomingResponse(
        body1=request.body1,
        longitude1=request.longitude1 % 360.0,
        body2=request.body2,
        longitude2=request.longitude2 % 360.0,
        body1_overcomes_body2=body1_overcomes,
        body2_overcomes_body1=body2_overcomes,
        overcoming_body=overcoming_body,
        provenance=HellenisticAspectProvenanceResponse(
            engine_entrypoint="overcoming",
            doctrine="tenth_sign_overcoming",
            source_refs=_SOURCE_REFS,
            stage_sequence=[
                "caller_position_validation",
                "bidirectional_tenth_sign_relation",
                "lossless_response_serialization",
            ],
        ),
    )
