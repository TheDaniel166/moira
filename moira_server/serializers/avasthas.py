"""Canonical avastha values; no name, clock or state reconstruction."""
from moira.avasthas import AvasthaChartResult
from moira.sayanadi_dated import AvasthaBirthResult
from ..models.sayanadi import AvasthaBirthEvidenceResponse, SayanadiContextResponse, SayanadiResponse
from ..models.vedic_extended import (
    AvasthaBirthResponse, AvasthaChartResponse, LajjitadiStateResponse, PlanetAvasthasResponse,
)


def serialize_avastha_chart(result: AvasthaChartResult) -> AvasthaChartResponse:
    return AvasthaChartResponse(
        deeptadi_source=result.policy.deeptadi_source,
        relationship_scheme=result.policy.relationship_scheme,
        vriddha_fraction=result.policy.vriddha_fraction,
        planets={
            name: PlanetAvasthasResponse(
                planet=pa.planet, baladi_state=pa.baladi.state,
                baladi_effect_fraction=pa.baladi.effect_fraction, baladi_effect_label=pa.baladi.effect_label,
                jagradadi_state=pa.jagradadi.state, jagradadi_reason=pa.jagradadi.reason,
                jagradadi_effect_fraction=pa.jagradadi.effect_fraction,
                deeptadi_state=pa.deeptadi.state, deeptadi_source=pa.deeptadi.source,
                deeptadi_reason=pa.deeptadi.reason, deeptadi_citation=pa.deeptadi.citation,
                lajjitadi=tuple(LajjitadiStateResponse(state=s.state, applies=s.applies, evidence=s.evidence)
                               for s in pa.lajjitadi.states),
                lajjitadi_active=pa.lajjitadi.active, lajjitadi_notes=pa.lajjitadi.notes,
                sayanadi=SayanadiResponse.model_validate(pa.sayanadi) if pa.sayanadi is not None else None,
            ) for name, pa in result.planets.items()
        },
        sayanadi_status=result.sayanadi_status,
        sayanadi_context=SayanadiContextResponse.model_validate(result.sayanadi_context)
        if result.sayanadi_context is not None else None,
        sayanadi_nodes={key: SayanadiResponse.model_validate(value) for key, value in result.sayanadi_nodes.items()},
    )


def serialize_avastha_birth(result: AvasthaBirthResult) -> AvasthaBirthResponse:
    evidence = AvasthaBirthEvidenceResponse.model_validate(result)
    return AvasthaBirthResponse(**evidence.model_dump(),
                                chart=serialize_avastha_chart(result.chart) if result.chart is not None else None)
