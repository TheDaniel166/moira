"""Kernel-free service composition for supporting Hellenistic atoms."""

from __future__ import annotations

from moira.hellenistic_relations import (
    HellenisticAssembleCondition,
    assemble_hellenistic_condition,
)
from moira.twelfth_parts import twelfth_part_of

from ..models.hellenistic_aspects import HellenisticAspectProvenanceResponse
from ..models.hellenistic_atoms import (
    HellenisticAdherenceTruthResponse,
    HellenisticAssembleConditionResponse,
    HellenisticConditionRequest,
    HellenisticPlanetOvercomingTruthResponse,
    HellenisticRayTruthResponse,
    HellenisticTestimonyTruthResponse,
    HellenisticTestimonyWitnessResponse,
    TwelfthPartResponse,
    TwelfthPartsRequest,
    TwelfthPartsResponse,
)
from ..serializers.dignities import serialize_besieging_truth
from .hellenistic_aspects import _serialize_superiority_truth


def compute_twelfth_parts(request: TwelfthPartsRequest) -> TwelfthPartsResponse:
    parts = [
        TwelfthPartResponse(
            body=name,
            occupied_sign=result.occupied_sign,
            occupied_sign_degree=result.occupied_sign_degree,
            slice_index=result.slice_index,
            twelfth_part_sign=result.twelfth_part_sign,
            projected_longitude=result.projected_longitude,
            source_longitude=result.source_longitude,
        )
        for name, longitude in request.positions.items()
        for result in (twelfth_part_of(longitude),)
    ]
    return TwelfthPartsResponse(
        parts=parts,
        count=len(parts),
        provenance=HellenisticAspectProvenanceResponse(
            source_module="moira.twelfth_parts",
            engine_entrypoint="twelfth_part_of",
            doctrine="natal_twelfth_parts_12x_projection",
            source_refs=["Ptolemy, Tetrabiblos I.22"],
            stage_sequence=[
                "caller_position_validation",
                "sign_degree_extraction",
                "twelve_times_projection",
                "lossless_response_serialization",
            ],
        ),
    )


def _serialize_condition(
    condition: HellenisticAssembleCondition,
) -> HellenisticAssembleConditionResponse:
    return HellenisticAssembleConditionResponse(
        subject=condition.subject,
        testimony=HellenisticTestimonyTruthResponse(
            status=condition.testimony.status,
            subject=condition.testimony.subject,
            witnesses=tuple(
                HellenisticTestimonyWitnessResponse(
                    body=item.body,
                    aspect=item.aspect,
                    angle_deg=item.angle_deg,
                    superiority=_serialize_superiority_truth(item.superiority),
                )
                for item in condition.testimony.witnesses
            ),
            averse_bodies=condition.testimony.averse_bodies,
            reason=condition.testimony.reason,
        ),
        overcoming=HellenisticPlanetOvercomingTruthResponse(
            status=condition.overcoming.status,
            subject=condition.overcoming.subject,
            overcame_by=condition.overcoming.overcame_by,
            overcomes=condition.overcoming.overcomes,
            receipts=tuple(
                _serialize_superiority_truth(item)
                for item in condition.overcoming.receipts
            ),
            reason=condition.overcoming.reason,
        ),
        enclosure=serialize_besieging_truth(condition.enclosure),
        adherence=HellenisticAdherenceTruthResponse(
            status=condition.adherence.status,
            subject=condition.adherence.subject,
            orb_deg=condition.adherence.orb_deg,
            adhered=condition.adherence.adhered,
            partner=condition.adherence.partner,
            distance_deg=condition.adherence.distance_deg,
            motion_state=condition.adherence.motion_state,
            reason=condition.adherence.reason,
        ),
        ray=HellenisticRayTruthResponse(
            status=condition.ray.status,
            subject=condition.ray.subject,
            reason=condition.ray.reason,
        ),
        provenance=HellenisticAspectProvenanceResponse(
            source_module="moira.hellenistic_relations",
            engine_entrypoint="assemble_hellenistic_condition",
            doctrine="score_free_assemble_condition",
            source_refs=[
                "Antiochus via Porphyry",
                "Vettius Valens, Anthologies",
            ],
            stage_sequence=[
                "caller_position_validation",
                "whole_sign_testimony",
                "tenth_sign_overcoming",
                "malefic_enclosure",
                "bodily_adherence",
                "ray_fail_closed",
                "lossless_response_serialization",
            ],
        ),
    )


def compute_hellenistic_condition(
    request: HellenisticConditionRequest,
) -> HellenisticAssembleConditionResponse:
    condition = assemble_hellenistic_condition(
        request.subject,
        request.positions,
        request.speeds,
        adherence_orb_deg=request.adherence_orb_deg,
        enclosure_orb_deg=request.enclosure_orb_deg,
    )
    return _serialize_condition(condition)


__all__ = [
    "compute_hellenistic_condition",
    "compute_twelfth_parts",
]
