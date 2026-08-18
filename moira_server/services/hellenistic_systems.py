"""Kernel-free composition for Hellenistic circumambulations, transmissions, and offices."""

from __future__ import annotations

from moira.circumambulations import circumambulate
from moira.egyptian_bounds import EgyptianBoundsPolicy
from moira.hellenistic_offices import hunt_hellenistic_offices
from moira.valens_transmissions import valens_transmission_graph

from ..models.hellenistic_aspects import HellenisticAspectProvenanceResponse
from ..models.hellenistic_systems import (
    CircumambulationPeriodResponse,
    CircumambulationsRequest,
    CircumambulationsResponse,
    HellenisticOfficeCandidateResponse,
    OfficesRequest,
    OfficesResponse,
    TransmissionEdgeResponse,
    TransmissionsRequest,
    TransmissionsResponse,
)


def compute_circumambulations(
    request: CircumambulationsRequest,
) -> CircumambulationsResponse:
    result = circumambulate(
        request.significator_longitude,
        request.start_jd,
        significator_name=request.significator_name,
        time_key=request.time_key,
        bounds_policy=EgyptianBoundsPolicy(doctrine=request.bounds_doctrine),
        year_days=request.year_days,
    )
    return CircumambulationsResponse(
        status=result.status,
        significator_name=result.significator_name,
        significator_longitude=result.significator_longitude,
        start_jd=result.start_jd,
        time_key=result.time_key,
        bounds_doctrine=result.bounds_doctrine,
        year_days=result.year_days,
        periods=tuple(
            CircumambulationPeriodResponse(
                index=period.index,
                lord=period.lord,
                sign=period.sign,
                start_longitude=period.start_longitude,
                end_longitude=period.end_longitude,
                span_deg=period.span_deg,
                bound_width_deg=period.bound_width_deg,
                years=period.years,
                start_jd=period.start_jd,
                end_jd=period.end_jd,
            )
            for period in result.periods
        ),
        reason=result.reason,
        provenance=HellenisticAspectProvenanceResponse(
            source_module="moira.circumambulations",
            engine_entrypoint="circumambulate",
            doctrine="egyptian_bound_aphesis",
            source_refs=[
                "Ptolemy, Tetrabiblos I.20/I.21 Egyptian bounds",
                "Valens planetary periods as bound-lord year key",
            ],
            stage_sequence=[
                "caller_significator_validation",
                "egyptian_bound_walk",
                "admitted_year_key_or_fail_closed",
                "lossless_response_serialization",
            ],
        ),
    )


def compute_transmissions(request: TransmissionsRequest) -> TransmissionsResponse:
    graph = valens_transmission_graph(
        positions=request.positions,
        lots=request.lots,
        asc_longitude=request.asc_longitude,
        profection_lord=request.profection_lord,
        profection_monthly_lords=request.profection_monthly_lords,
        decennial_l1=request.decennial_l1,
        decennial_l2=request.decennial_l2,
        zr_l1_sign=request.zr_l1_sign,
        zr_l2_sign=request.zr_l2_sign,
    )
    return TransmissionsResponse(
        status=graph.status,
        edges=tuple(
            TransmissionEdgeResponse(
                source=edge.source,
                source_kind=edge.source_kind,
                target=edge.target,
                target_kind=edge.target_kind,
                kind=edge.kind,
                period_ref=edge.period_ref,
                natal_ref=edge.natal_ref,
                status=edge.status,
                reason=edge.reason,
            )
            for edge in graph.edges
        ),
        reason=graph.reason,
        provenance=HellenisticAspectProvenanceResponse(
            source_module="moira.valens_transmissions",
            engine_entrypoint="valens_transmission_graph",
            doctrine="from_to_transmission_graph",
            source_refs=["Vettius Valens, Anthologies IV period handoff"],
            stage_sequence=[
                "caller_period_and_natal_validation",
                "from_to_edge_assembly",
                "no_effect_prose",
                "lossless_response_serialization",
            ],
        ),
    )


def compute_offices(request: OfficesRequest) -> OfficesResponse:
    hunt = hunt_hellenistic_offices(
        positions=request.positions,
        is_day_chart=request.is_day_chart,
        asc_longitude=request.asc_longitude,
        lots=request.lots,
    )
    return OfficesResponse(
        status=hunt.status,
        predominator=None,
        house_master=None,
        candidates=tuple(
            HellenisticOfficeCandidateResponse(
                name=item.name,
                kind=item.kind,
                longitude=item.longitude,
                house=item.house,
                is_sect_light=item.is_sect_light,
                is_angular=item.is_angular,
                reason=item.reason,
            )
            for item in hunt.candidates
        ),
        reason=hunt.reason,
        provenance=HellenisticAspectProvenanceResponse(
            source_module="moira.hellenistic_offices",
            engine_entrypoint="hunt_hellenistic_offices",
            doctrine="fail_closed_office_candidates",
            source_refs=[
                "Hellenistic predominator/oikodespotes as unselected candidates"
            ],
            stage_sequence=[
                "candidate_collection",
                "refuse_scored_hybrid",
                "lossless_response_serialization",
            ],
        ),
    )


__all__ = [
    "compute_circumambulations",
    "compute_offices",
    "compute_transmissions",
]
