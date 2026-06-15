"""Service layer for P-GAP-05 sidereal and Nakshatra utility routes."""

from __future__ import annotations

import moira.sidereal as sidereal_module
from moira.sidereal import (
    Ayanamsa,
    NAKSHATRA_SPAN,
    PADA_SPAN,
    NakshatraPosition,
    all_nakshatras_at,
    ayanamsa,
    list_ayanamsa_systems,
    nakshatra_of,
    sidereal_to_tropical,
    tropical_to_sidereal,
)

from ..models.sidereal import (
    AyanamsaSystemResponse,
    AyanamsaSystemsEnvelopeResponse,
    SiderealAyanamsaRequest,
    SiderealAyanamsaResponse,
    SiderealConversionRequest,
    SiderealConversionResponse,
    SiderealNakshatraBulkEnvelopeResponse,
    SiderealNakshatraBulkRequest,
    SiderealNakshatraPositionEnvelopeResponse,
    SiderealNakshatraPositionRequest,
    SiderealNakshatraPositionResponse,
    SiderealUtilityProvenanceResponse,
)


_LONGITUDE_RANGE = [0.0, "360_exclusive"]


def _star_anchored_systems() -> set[str]:
    return set(getattr(sidereal_module, "_STAR_ANCHORED", {}).keys())


def _registry_provenance() -> SiderealUtilityProvenanceResponse:
    return SiderealUtilityProvenanceResponse(
        engine_entrypoint="list_ayanamsa_systems",
        product_kind="ayanamsa_system_registry",
        registry_owner="moira.sidereal.Ayanamsa",
        reference_epoch="J2000",
        user_defined_ayanamsa="not_admitted",
        stage_sequence=[
            "registry_lookup",
            "system_serialization",
            "provenance_serialization",
        ],
    )


def _ayanamsa_provenance(
    *,
    engine_entrypoint: str,
    product_kind: str,
    ayanamsa_system: str,
    mode: str,
    stage_sequence: list[str],
    conversion_direction: str | None = None,
) -> SiderealUtilityProvenanceResponse:
    return SiderealUtilityProvenanceResponse(
        engine_entrypoint=engine_entrypoint,
        product_kind=product_kind,
        ayanamsa_system=ayanamsa_system,
        ayanamsa_mode=mode,
        jd_policy="caller_supplied_UT_JD",
        mode_policy="true_or_mean_only",
        star_anchor_policy="engine_owned_for_true_star_anchored_systems",
        longitude_input_policy=(
            "finite_input_normalized_by_engine_modulo"
            if conversion_direction is not None
            else None
        ),
        conversion_direction=conversion_direction,
        stage_sequence=stage_sequence,
    )


def _nakshatra_provenance(
    *,
    engine_entrypoint: str,
    ayanamsa_system: str,
    stage_sequence: list[str],
) -> SiderealUtilityProvenanceResponse:
    return SiderealUtilityProvenanceResponse(
        engine_entrypoint=engine_entrypoint,
        product_kind="nakshatra_position_lookup",
        ayanamsa_system=ayanamsa_system,
        ayanamsa_mode="true",
        jd_policy="caller_supplied_UT_JD",
        taxonomy="twenty_seven_equal_nakshatras",
        span_deg=NAKSHATRA_SPAN,
        pada_span_deg=PADA_SPAN,
        interpretation="not_returned",
        panchanga_judgement="not_returned",
        stage_sequence=stage_sequence,
    )


def _serialize_nakshatra_position(
    position: NakshatraPosition,
    *,
    tropical_longitude_deg: float,
    jd_ut: float,
    ayanamsa_system: str,
    name: str | None = None,
) -> SiderealNakshatraPositionResponse:
    return SiderealNakshatraPositionResponse(
        name=name,
        tropical_longitude_deg=tropical_longitude_deg,
        jd_ut=jd_ut,
        ayanamsa_system=ayanamsa_system,
        nakshatra=position.nakshatra,
        nakshatra_index=position.nakshatra_index,
        nakshatra_number=position.nakshatra_index + 1,
        nakshatra_lord=position.nakshatra_lord,
        pada=position.pada,
        degrees_in=position.degrees_in,
        degrees_remaining=NAKSHATRA_SPAN - position.degrees_in,
        sidereal_longitude_deg=position.sidereal_lon,
    )


def list_sidereal_ayanamsa_systems() -> AyanamsaSystemsEnvelopeResponse:
    reference_values = list_ayanamsa_systems()
    star_anchored = _star_anchored_systems()
    systems = [
        AyanamsaSystemResponse(
            system=system,
            reference_value_j2000_deg=reference_values[system],
            is_star_anchored=system in star_anchored,
            supported_modes=["true", "mean"],
        )
        for system in Ayanamsa.ALL
    ]
    return AyanamsaSystemsEnvelopeResponse(
        systems=systems,
        total=len(systems),
        provenance=_registry_provenance(),
    )


def compute_sidereal_ayanamsa(
    request: SiderealAyanamsaRequest,
) -> SiderealAyanamsaResponse:
    value = ayanamsa(request.jd_ut, request.ayanamsa_system, request.mode)
    return SiderealAyanamsaResponse(
        jd_ut=request.jd_ut,
        ayanamsa_system=request.ayanamsa_system,
        mode=request.mode,
        ayanamsa_deg=value,
        value_range=_LONGITUDE_RANGE,
        provenance=_ayanamsa_provenance(
            engine_entrypoint="ayanamsa",
            product_kind="date_specific_ayanamsa_value",
            ayanamsa_system=request.ayanamsa_system,
            mode=request.mode,
            stage_sequence=[
                "input_validation",
                "ayanamsa_resolution",
                "ayanamsa_response_serialization",
                "provenance_serialization",
            ],
        ),
    )


def convert_sidereal_longitude(
    request: SiderealConversionRequest,
) -> SiderealConversionResponse:
    ayanamsa_deg = ayanamsa(request.jd_ut, request.ayanamsa_system, request.mode)
    if request.direction == "tropical_to_sidereal":
        output_longitude = tropical_to_sidereal(
            request.longitude_deg,
            request.jd_ut,
            system=request.ayanamsa_system,
            mode=request.mode,
        )
        engine_entrypoint = "tropical_to_sidereal"
    else:
        output_longitude = sidereal_to_tropical(
            request.longitude_deg,
            request.jd_ut,
            system=request.ayanamsa_system,
            mode=request.mode,
        )
        engine_entrypoint = "sidereal_to_tropical"

    return SiderealConversionResponse(
        direction=request.direction,
        jd_ut=request.jd_ut,
        ayanamsa_system=request.ayanamsa_system,
        mode=request.mode,
        input_longitude_deg=request.longitude_deg,
        output_longitude_deg=output_longitude,
        ayanamsa_deg=ayanamsa_deg,
        longitude_range=_LONGITUDE_RANGE,
        provenance=_ayanamsa_provenance(
            engine_entrypoint=engine_entrypoint,
            product_kind="sidereal_longitude_conversion",
            ayanamsa_system=request.ayanamsa_system,
            mode=request.mode,
            conversion_direction=request.direction,
            stage_sequence=[
                "input_validation",
                "ayanamsa_resolution",
                "longitude_conversion",
                "conversion_response_serialization",
                "provenance_serialization",
            ],
        ),
    )


def compute_nakshatra_position(
    request: SiderealNakshatraPositionRequest,
) -> SiderealNakshatraPositionEnvelopeResponse:
    position = nakshatra_of(
        request.tropical_longitude_deg,
        request.jd_ut,
        request.ayanamsa_system,
    )
    return SiderealNakshatraPositionEnvelopeResponse(
        request=request,
        position=_serialize_nakshatra_position(
            position,
            tropical_longitude_deg=request.tropical_longitude_deg,
            jd_ut=request.jd_ut,
            ayanamsa_system=request.ayanamsa_system,
        ),
        provenance=_nakshatra_provenance(
            engine_entrypoint="nakshatra_of",
            ayanamsa_system=request.ayanamsa_system,
            stage_sequence=[
                "input_validation",
                "tropical_to_sidereal_conversion",
                "nakshatra_lookup",
                "nakshatra_response_serialization",
                "provenance_serialization",
            ],
        ),
    )


def compute_nakshatra_bulk(
    request: SiderealNakshatraBulkRequest,
) -> SiderealNakshatraBulkEnvelopeResponse:
    results = all_nakshatras_at(
        request.positions,
        request.jd_ut,
        request.ayanamsa_system,
    )
    serialized = [
        _serialize_nakshatra_position(
            results[name],
            name=name,
            tropical_longitude_deg=longitude,
            jd_ut=request.jd_ut,
            ayanamsa_system=request.ayanamsa_system,
        )
        for name, longitude in request.positions.items()
    ]
    return SiderealNakshatraBulkEnvelopeResponse(
        request=request,
        positions=serialized,
        total=len(serialized),
        provenance=_nakshatra_provenance(
            engine_entrypoint="all_nakshatras_at",
            ayanamsa_system=request.ayanamsa_system,
            stage_sequence=[
                "input_validation",
                "bulk_tropical_to_sidereal_conversion",
                "bulk_nakshatra_lookup",
                "nakshatra_bulk_response_serialization",
                "provenance_serialization",
            ],
        ),
    )
