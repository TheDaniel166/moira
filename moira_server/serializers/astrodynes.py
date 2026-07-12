"""Serializers for Church of Light natal Astrodynes vessels."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from enum import Enum
from typing import Any

from moira.astrodynes import (
    AstrodyneAspectRelation,
    AstrodyneBodyInput,
    AstrodyneChartResult,
    AstrodyneMutualReceptionRelation,
    AstrodynePolicy,
    validate_astrodynes_output,
)

from ..models.astrodynes import (
    AstrodyneAggregateResponse,
    AstrodyneBodyInputResponse,
    AstrodyneBodyProfileResponse,
    AstrodyneContributionResponse,
    AstrodyneNetworkResponse,
    AstrodynePolicyResponse,
    AstrodyneRelationResponse,
    AstrodyneSummaryResponse,
    AstrodynesCalculationResponse,
    AstrodynesDoctrineResponse,
    AstrodynesGeometryResponse,
    AstrodynesProvenanceResponse,
)
from ..services.astrodynes import (
    AstrodynesCalculationTruth,
    AstrodynesDoctrineTruth,
)


def _transport_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {
            field.name: _transport_value(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, dict):
        return {
            _transport_value(key): _transport_value(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_transport_value(item) for item in value]
    return value


def _policy_response(policy: AstrodynePolicy) -> AstrodynePolicyResponse:
    return AstrodynePolicyResponse(**_transport_value(policy))


def _relation_id(relation: object) -> str:
    return "::".join(str(_transport_value(item)) for item in relation.sort_key)


def _body_input_response(item: AstrodyneBodyInput) -> AstrodyneBodyInputResponse:
    return AstrodyneBodyInputResponse(
        body=item.body,
        body_kind=item.body_kind.value,
        longitude_deg=item.longitude_deg,
        sign=item.sign,
        sign_degree=item.sign_degree,
        house=item.house,
        house_class=item.house_class,
        distance_from_weaker_cusp_deg=item.distance_from_weaker_cusp_deg,
        house_size_deg=item.house_size_deg,
        declination_deg=item.declination_deg,
    )


def _relation_response(relation: object) -> AstrodyneRelationResponse:
    if isinstance(relation, AstrodyneAspectRelation):
        label = relation.aspect
        power_truth = _transport_value(relation.power_truth)
        harmony_truth = _transport_value(relation.harmony_truth)
        mutual_reception_truth = None
    elif isinstance(relation, AstrodyneMutualReceptionRelation):
        label = "mutual_reception"
        power_truth = None
        harmony_truth = None
        mutual_reception_truth = _transport_value(relation)
    else:  # pragma: no cover - guarded by the engine's closed union
        raise TypeError(f"unsupported Astrodyne relation {type(relation)!r}")
    return AstrodyneRelationResponse(
        relation_id=_relation_id(relation),
        kind=relation.kind.value,
        body_a=relation.body_a,
        body_b=relation.body_b,
        label=label,
        power=relation.power,
        harmony=relation.harmony,
        discord=relation.discord,
        net_harmony=relation.net_harmony,
        detected=relation.detected,
        admitted=relation.admitted,
        scored=relation.scored,
        power_truth=power_truth,
        harmony_truth=harmony_truth,
        mutual_reception_truth=mutual_reception_truth,
    )


def _profile_response(profile: object) -> AstrodyneBodyProfileResponse:
    return AstrodyneBodyProfileResponse(
        body=profile.body,
        body_kind=profile.input.body_kind.value,
        sign=profile.sign,
        house=profile.house,
        input=_body_input_response(profile.input),
        house_position_truth=_transport_value(profile.house_position),
        dignity_truth=_transport_value(profile.dignity),
        relation_ids=tuple(_relation_id(item) for item in profile.relations),
        contributions=tuple(
            AstrodyneContributionResponse(
                source=item.source.value,
                label=item.label,
                power=item.power,
                harmony=item.harmony,
                discord=item.discord,
            )
            for item in profile.contributions
        ),
        total_power=profile.total_power,
        total_harmony=profile.total_harmony,
        total_discord=profile.total_discord,
        net_harmony=profile.net_harmony,
    )


def _aggregate_response(result: AstrodyneChartResult) -> AstrodyneAggregateResponse:
    aggregate = result.aggregate
    return AstrodyneAggregateResponse(
        signs=tuple(_transport_value(item) for item in aggregate.signs),
        houses=tuple(_transport_value(item) for item in aggregate.houses),
        total_body_power=aggregate.total_body_power,
        total_sign_power=aggregate.total_sign_power,
        total_house_power=aggregate.total_house_power,
        total_sign_harmony=aggregate.total_sign_harmony,
        total_house_harmony=aggregate.total_house_harmony,
        power_checksum_delta=aggregate.power_checksum_delta,
        harmony_checksum_delta=aggregate.harmony_checksum_delta,
        checksums_pass=aggregate.checksums_pass,
    )


def _summary_response(result: AstrodyneChartResult) -> AstrodyneSummaryResponse:
    summary = result.summary
    return AstrodyneSummaryResponse(
        societies=tuple(_transport_value(item) for item in summary.societies),
        trinities=tuple(_transport_value(item) for item in summary.trinities),
        elements=tuple(_transport_value(item) for item in summary.elements),
        qualities=tuple(_transport_value(item) for item in summary.qualities),
        total_power=summary.total_power,
    )


def _network_response(result: AstrodyneChartResult) -> AstrodyneNetworkResponse:
    return AstrodyneNetworkResponse(
        nodes=tuple(_transport_value(item) for item in result.network.nodes),
        edges=tuple(_transport_value(item) for item in result.network.edges),
    )


def serialize_astrodynes_doctrine(
    truth: AstrodynesDoctrineTruth,
) -> AstrodynesDoctrineResponse:
    groups = []
    for family, name, members in truth.summary_groups:
        groups.append(
            {
                "family": family,
                "name": name,
                "houses": members if family in {"society", "trinity"} else (),
                "signs": members if family in {"element", "quality"} else (),
            }
        )
    return AstrodynesDoctrineResponse(
        doctrine="church_of_light_natal_astrodynes",
        planets=truth.planets,
        points=truth.points,
        signs=truth.signs,
        house_classes=truth.house_classes,
        policy=_policy_response(truth.policy),
        dignity_rows=tuple(_transport_value(item) for item in truth.dignity_rows),
        house_power_rows=tuple(
            {
                **_transport_value(item),
                "variation": item.variation,
            }
            for item in truth.house_power_rows
        ),
        aspect_orb_rows=tuple(
            _transport_value(item) for item in truth.aspect_orb_rows
        ),
        summary_groups=tuple(groups),
    )


def serialize_astrodynes_calculation(
    truth: AstrodynesCalculationTruth,
) -> AstrodynesCalculationResponse:
    result = truth.result
    return AstrodynesCalculationResponse(
        geometry=AstrodynesGeometryResponse(
            source_mode=truth.source_mode,
            dt=truth.dt,
            observer_lat=truth.observer_lat,
            observer_lon=truth.observer_lon,
            jd_ut=truth.jd_ut,
            obliquity_deg=truth.obliquity_deg,
            planet_longitudes=truth.planet_longitudes,
            declinations=truth.declinations,
            cusp_longitudes=truth.cusp_longitudes,
            mc_longitude=truth.mc_longitude,
            asc_longitude=truth.asc_longitude,
            requested_house_system=truth.requested_house_system,
            effective_house_system=truth.effective_house_system,
            house_fallback=truth.house_fallback,
            house_fallback_reason=truth.house_fallback_reason,
        ),
        policy=_policy_response(result.policy),
        inputs=tuple(_body_input_response(item) for item in result.inputs),
        relations=tuple(
            _relation_response(item) for item in result.relations.detected
        ),
        admitted_relation_count=len(result.relations.admitted),
        scored_relation_count=len(result.relations.scored),
        profiles=tuple(_profile_response(item) for item in result.profiles),
        aggregate=_aggregate_response(result),
        summary=_summary_response(result),
        network=_network_response(result),
        validation_failures=validate_astrodynes_output(result),
        provenance=AstrodynesProvenanceResponse(
            doctrine="church_of_light_natal_astrodynes",
            engine_entrypoint=truth.engine_entrypoint,
            source_mode=truth.source_mode,
            planetary_frame=truth.planetary_frame,
            kernel_required=truth.kernel_required,
            stage_sequence=truth.stage_sequence,
        ),
    )


__all__ = [
    "serialize_astrodynes_calculation",
    "serialize_astrodynes_doctrine",
]
