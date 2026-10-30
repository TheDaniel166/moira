"""Service layer for P-GAP-05 sidereal and Nakshatra utility routes."""

from __future__ import annotations

from dataclasses import asdict

import moira.sidereal as sidereal_module
from moira.sidereal import (
    Ayanamsa,
    AyanamsaComputationTruth,
    NAKSHATRA_SPAN,
    PADA_SPAN,
    NakshatraComputationTruth,
    NakshatraPosition,
    SiderealLongitudeConversionTruth,
    all_nakshatras_at_with_truth,
    ayanamsa_doctrine,
    ayanamsa_with_truth,
    list_ayanamsa_systems,
    nakshatra_of_with_truth,
    sidereal_to_tropical_with_truth,
    tropical_to_sidereal_with_truth,
)

from ..models.sidereal import (
    AyanamsaComputationTruthResponse,
    AyanamsaDoctrineResponse,
    AyanamsaSystemResponse,
    AyanamsaSystemsEnvelopeResponse,
    NakshatraComputationTruthResponse,
    SiderealAyanamsaRequest,
    SiderealAyanamsaResponse,
    SiderealConversionRequest,
    SiderealConversionResponse,
    SiderealNakshatraBulkEnvelopeResponse,
    SiderealNakshatraBulkRequest,
    SiderealNakshatraPositionEnvelopeResponse,
    SiderealNakshatraPositionRequest,
    SiderealNakshatraPositionResponse,
    SiderealLongitudeConversionTruthResponse,
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
    truth: NakshatraComputationTruth,
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
        computation_truth=_serialize_nakshatra_truth(truth),
    )


def _truth_payload(truth) -> dict:
    """``asdict`` with every nested ayanamsa's ``doctrine_terms`` pairs as a mapping."""
    payload = asdict(truth)
    ayanamsa_payload = payload.get("ayanamsa", payload)
    ayanamsa_payload["doctrine_terms"] = dict(ayanamsa_payload["doctrine_terms"])
    return payload


def _serialize_ayanamsa_truth(
    truth: AyanamsaComputationTruth,
) -> AyanamsaComputationTruthResponse:
    return AyanamsaComputationTruthResponse.model_validate(_truth_payload(truth))


def _serialize_conversion_truth(
    truth: SiderealLongitudeConversionTruth,
) -> SiderealLongitudeConversionTruthResponse:
    return SiderealLongitudeConversionTruthResponse.model_validate(_truth_payload(truth))


def _serialize_nakshatra_truth(
    truth: NakshatraComputationTruth,
) -> NakshatraComputationTruthResponse:
    return NakshatraComputationTruthResponse.model_validate(_truth_payload(truth))


def _serialize_doctrine(system) -> AyanamsaDoctrineResponse:
    return AyanamsaDoctrineResponse.model_validate(asdict(ayanamsa_doctrine(system)))


def list_sidereal_ayanamsa_systems() -> AyanamsaSystemsEnvelopeResponse:
    reference_values = list_ayanamsa_systems()
    star_anchored = _star_anchored_systems()
    systems = [
        AyanamsaSystemResponse(
            system=system,
            reference_value_j2000_deg=reference_values[system],
            is_star_anchored=system in star_anchored,
            supported_modes=["true", "mean"],
            doctrine=_serialize_doctrine(system),
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
    system = request.engine_system()
    truth = ayanamsa_with_truth(
        request.jd_ut,
        system,
        request.mode,
    )
    return SiderealAyanamsaResponse(
        jd_ut=request.jd_ut,
        ayanamsa_system=request.system_name(),
        mode=request.mode,
        ayanamsa_deg=truth.ayanamsa_deg,
        value_range=_LONGITUDE_RANGE,
        provenance=_ayanamsa_provenance(
            engine_entrypoint="ayanamsa",
            product_kind="date_specific_ayanamsa_value",
            ayanamsa_system=request.system_name(),
            mode=request.mode,
            stage_sequence=[
                "input_validation",
                "ayanamsa_resolution",
                "ayanamsa_response_serialization",
                "provenance_serialization",
            ],
        ),
        computation_truth=_serialize_ayanamsa_truth(truth),
        doctrine=_serialize_doctrine(system),
    )


def convert_sidereal_longitude(
    request: SiderealConversionRequest,
) -> SiderealConversionResponse:
    if request.direction == "tropical_to_sidereal":
        truth = tropical_to_sidereal_with_truth(
            request.longitude_deg,
            request.jd_ut,
            system=request.engine_system(),
            mode=request.mode,
        )
        engine_entrypoint = "tropical_to_sidereal"
    else:
        truth = sidereal_to_tropical_with_truth(
            request.longitude_deg,
            request.jd_ut,
            system=request.engine_system(),
            mode=request.mode,
        )
        engine_entrypoint = "sidereal_to_tropical"

    return SiderealConversionResponse(
        direction=request.direction,
        jd_ut=request.jd_ut,
        ayanamsa_system=request.system_name(),
        mode=request.mode,
        input_longitude_deg=request.longitude_deg,
        output_longitude_deg=truth.output_longitude_deg,
        ayanamsa_deg=truth.ayanamsa.ayanamsa_deg,
        longitude_range=_LONGITUDE_RANGE,
        provenance=_ayanamsa_provenance(
            engine_entrypoint=engine_entrypoint,
            product_kind="sidereal_longitude_conversion",
            ayanamsa_system=request.system_name(),
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
        computation_truth=_serialize_conversion_truth(truth),
    )


def compute_nakshatra_position(
    request: SiderealNakshatraPositionRequest,
) -> SiderealNakshatraPositionEnvelopeResponse:
    resolved = nakshatra_of_with_truth(
        request.tropical_longitude_deg,
        request.jd_ut,
        request.engine_system(),
    )
    return SiderealNakshatraPositionEnvelopeResponse(
        request=request,
        position=_serialize_nakshatra_position(
            resolved.result,
            resolved.truth,
            tropical_longitude_deg=request.tropical_longitude_deg,
            jd_ut=request.jd_ut,
            ayanamsa_system=request.system_name(),
        ),
        provenance=_nakshatra_provenance(
            engine_entrypoint="nakshatra_of",
            ayanamsa_system=request.system_name(),
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
    resolved = all_nakshatras_at_with_truth(
        request.positions,
        request.jd_ut,
        request.engine_system(),
    )
    serialized = [
        _serialize_nakshatra_position(
            resolved.results[name],
            resolved.truths[name],
            name=name,
            tropical_longitude_deg=longitude,
            jd_ut=request.jd_ut,
            ayanamsa_system=request.system_name(),
        )
        for name, longitude in request.positions.items()
    ]
    return SiderealNakshatraBulkEnvelopeResponse(
        request=request,
        positions=serialized,
        total=len(serialized),
        provenance=_nakshatra_provenance(
            engine_entrypoint="all_nakshatras_at",
            ayanamsa_system=request.system_name(),
            stage_sequence=[
                "input_validation",
                "bulk_tropical_to_sidereal_conversion",
                "bulk_nakshatra_lookup",
                "nakshatra_bulk_response_serialization",
                "provenance_serialization",
            ],
        ),
    )
