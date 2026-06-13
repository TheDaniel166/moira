"""Services for Arabic lunar mansion (Manazil) transport."""

from __future__ import annotations

from moira.manazil import (
    MANSION_SPAN,
    MANSIONS,
    MansionInfo,
    MansionPosition,
    MansionTradition,
    mansion_of,
    mansion_of_sidereal,
    variant_nature,
    variant_signification,
)

from ..models.manazil import (
    MansionBulkRequest,
    MansionBulkResponse,
    MansionCatalogResponse,
    MansionComputationMode,
    MansionInfoResponse,
    MansionPositionEnvelopeResponse,
    MansionPositionRequest,
    MansionPositionResponse,
    MansionProvenanceResponse,
    MansionTraditionLookupResponse,
    MansionTraditionName,
)


def _engine_tradition(tradition: MansionTraditionName) -> MansionTradition:
    return MansionTradition(tradition.value)


def _serialize_info(info: MansionInfo) -> MansionInfoResponse:
    return MansionInfoResponse(
        index=info.index,
        arabic_name=info.arabic_name,
        latin_name=info.latin_name,
        ruling_star=info.ruling_star,
        nature=info.nature,
        signification=info.signification,
    )


def _serialize_position(
    position: MansionPosition,
    *,
    tradition: MansionTraditionName,
) -> MansionPositionResponse:
    engine_tradition = _engine_tradition(tradition)
    info = position.mansion
    if tradition is not MansionTraditionName.al_biruni:
        info = MansionInfo(
            index=position.mansion.index,
            arabic_name=position.mansion.arabic_name,
            latin_name=position.mansion.latin_name,
            ruling_star=position.mansion.ruling_star,
            nature=variant_nature(position.mansion.index, engine_tradition),
            signification=variant_signification(position.mansion.index, engine_tradition),
        )
    return MansionPositionResponse(
        mansion=_serialize_info(info),
        degrees_in=position.degrees_in,
        longitude=position.longitude,
        computation_longitude=((position.mansion.index - 1) * MANSION_SPAN + position.degrees_in) % 360.0,
    )


def _provenance(
    *,
    mode: MansionComputationMode,
    tradition: MansionTraditionName,
    requested_longitude: float,
    jd_ut: float | None,
    ayanamsa_system: str | None,
    ayanamsa_mode: str | None,
    stage_sequence: list[str],
) -> MansionProvenanceResponse:
    return MansionProvenanceResponse(
        mode=mode,
        tradition=tradition,
        requested_longitude=requested_longitude,
        normalized_longitude=requested_longitude % 360.0,
        jd_ut=jd_ut,
        ayanamsa_system=ayanamsa_system,
        ayanamsa_mode=ayanamsa_mode,
        stage_sequence=stage_sequence,
    )


def _compute_position(
    *,
    longitude: float,
    mode: MansionComputationMode,
    jd_ut: float | None,
    ayanamsa_system: str,
    ayanamsa_mode: str,
) -> MansionPosition:
    if mode is MansionComputationMode.sidereal:
        if jd_ut is None:
            raise ValueError("sidereal mansion computation requires jd_ut")
        return mansion_of_sidereal(longitude, jd_ut, ayanamsa_system, ayanamsa_mode)
    return mansion_of(longitude)


def manazil_catalog() -> MansionCatalogResponse:
    return MansionCatalogResponse(
        mansions=[_serialize_info(info) for info in MANSIONS],
        total=len(MANSIONS),
        span_degrees=MANSION_SPAN,
        traditions=[tradition for tradition in MansionTraditionName],
        provenance=_provenance(
            mode=MansionComputationMode.tropical,
            tradition=MansionTraditionName.al_biruni,
            requested_longitude=0.0,
            jd_ut=None,
            ayanamsa_system=None,
            ayanamsa_mode=None,
            stage_sequence=["mansion_catalog_serialization"],
        ),
    )


def compute_mansion_position(
    request: MansionPositionRequest,
) -> MansionPositionEnvelopeResponse:
    position = _compute_position(
        longitude=request.longitude,
        mode=request.mode,
        jd_ut=request.jd_ut,
        ayanamsa_system=request.ayanamsa_system,
        ayanamsa_mode=request.ayanamsa_mode,
    )
    return MansionPositionEnvelopeResponse(
        result=_serialize_position(position, tradition=request.tradition),
        provenance=_provenance(
            mode=request.mode,
            tradition=request.tradition,
            requested_longitude=request.longitude,
            jd_ut=request.jd_ut,
            ayanamsa_system=request.ayanamsa_system if request.mode is MansionComputationMode.sidereal else None,
            ayanamsa_mode=request.ayanamsa_mode if request.mode is MansionComputationMode.sidereal else None,
            stage_sequence=[
                "longitude_validation",
                "sidereal_conversion" if request.mode is MansionComputationMode.sidereal else "tropical_longitude_use",
                "equal_28_mansion_assignment",
                "tradition_attribution_selection",
                "mansion_response_serialization",
            ],
        ),
    )


def compute_mansion_bulk(request: MansionBulkRequest) -> MansionBulkResponse:
    results = {
        name: _serialize_position(
            _compute_position(
                longitude=longitude,
                mode=request.mode,
                jd_ut=request.jd_ut,
                ayanamsa_system=request.ayanamsa_system,
                ayanamsa_mode=request.ayanamsa_mode,
            ),
            tradition=request.tradition,
        )
        for name, longitude in request.positions.items()
    }
    return MansionBulkResponse(
        results=results,
        total=len(results),
        provenance=_provenance(
            mode=request.mode,
            tradition=request.tradition,
            requested_longitude=0.0,
            jd_ut=request.jd_ut,
            ayanamsa_system=request.ayanamsa_system if request.mode is MansionComputationMode.sidereal else None,
            ayanamsa_mode=request.ayanamsa_mode if request.mode is MansionComputationMode.sidereal else None,
            stage_sequence=[
                "bulk_longitude_validation",
                "sidereal_conversion" if request.mode is MansionComputationMode.sidereal else "tropical_longitude_use",
                "equal_28_mansion_assignment",
                "tradition_attribution_selection",
                "mansion_bulk_response_serialization",
            ],
        ),
    )


def lookup_mansion_tradition(
    mansion_index: int,
    tradition: MansionTraditionName,
) -> MansionTraditionLookupResponse:
    engine_tradition = _engine_tradition(tradition)
    return MansionTraditionLookupResponse(
        mansion_index=mansion_index,
        tradition=tradition,
        nature=variant_nature(mansion_index, engine_tradition),
        signification=variant_signification(mansion_index, engine_tradition),
        provenance=_provenance(
            mode=MansionComputationMode.tropical,
            tradition=tradition,
            requested_longitude=0.0,
            jd_ut=None,
            ayanamsa_system=None,
            ayanamsa_mode=None,
            stage_sequence=[
                "mansion_index_validation",
                "tradition_attribution_lookup",
                "tradition_response_serialization",
            ],
        ),
    )
