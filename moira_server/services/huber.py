"""Service layer for P12-07 direct Huber routes."""

from __future__ import annotations

from moira.constants import HouseSystem
from moira.houses import HouseCusps, classify_house_system
from moira.huber import (
    AgePointPosition,
    ChartIntensityProfile,
    DynamicIntensity,
    HouseZoneProfile,
    PlanetIntensityScore,
    age_point,
    age_point_contacts,
    chart_intensity_profile,
    dynamic_intensity,
    house_zones,
    intensity_at,
)

from ..models.huber import (
    HuberAgePointContactResponse,
    HuberAgePointContactsRequest,
    HuberAgePointContactsResponse,
    HuberAgePointRequest,
    HuberAgePointResponse,
    HuberChartIntensityProfileRequest,
    HuberChartIntensityProfileResponse,
    HuberDirectHouseFrameRequest,
    HuberDynamicIntensityRequest,
    HuberDynamicIntensityResponse,
    HuberHouseFrameProvenanceResponse,
    HuberHouseFrameRequest,
    HuberHouseFrameResponse,
    HuberHouseZoneResponse,
    HuberHouseZonesRequest,
    HuberHouseZonesResponse,
    HuberIntensityAtRequest,
    HuberIntensityAtResponse,
    HuberPlanetIntensityScoreResponse,
    HuberProvenanceResponse,
    HuberScanBoundsResponse,
)


def _house_cusps_from_direct_frame(frame: HuberDirectHouseFrameRequest) -> HouseCusps:
    effective_system = frame.effective_system or frame.system
    classification = classify_house_system(effective_system)
    return HouseCusps(
        system=frame.system,
        cusps=tuple(frame.cusps),
        asc=frame.asc,
        mc=frame.mc,
        armc=frame.armc,
        effective_system=effective_system,
        fallback=frame.fallback,
        fallback_reason=frame.fallback_reason,
        classification=classification,
    )


def _direct_frame(request: HuberHouseFrameRequest) -> HuberDirectHouseFrameRequest:
    return request.direct


def _house_frame_response(frame: HuberDirectHouseFrameRequest) -> HuberHouseFrameResponse:
    return HuberHouseFrameResponse(
        source="direct_cusps",
        cusps=list(frame.cusps),
        asc=frame.asc,
        mc=frame.mc,
        armc=frame.armc,
        system=frame.system,
        effective_system=frame.effective_system or frame.system,
        fallback=frame.fallback,
        fallback_reason=frame.fallback_reason,
    )


def _house_frame_provenance(
    frame: HuberDirectHouseFrameRequest,
) -> HuberHouseFrameProvenanceResponse:
    effective_system = frame.effective_system or frame.system
    is_koch = effective_system == HouseSystem.KOCH
    note = (
        "Caller supplied a Koch house frame; Huber transport did not derive cusps."
        if is_koch
        else "Caller supplied a non-Koch house frame; computation is allowed but not doctrinally complete Huber house fidelity."
    )
    return HuberHouseFrameProvenanceResponse(
        house_frame_source="caller_supplied",
        cusp_derivation_owner="caller_supplied",
        system=frame.system,
        requested_system=frame.system,
        effective_system=effective_system,
        fallback=frame.fallback,
        fallback_reason=frame.fallback_reason,
        is_koch_effective=is_koch,
        note=note,
    )


def _provenance(engine_entrypoint: str, stage_sequence: list[str]) -> HuberProvenanceResponse:
    return HuberProvenanceResponse(
        engine_entrypoint=engine_entrypoint,
        stage_sequence=stage_sequence,
    )


def _serialize_dynamic_intensity(
    value: DynamicIntensity,
    *,
    requested_fraction: float,
    engine_entrypoint: str,
    stage_sequence: list[str],
) -> HuberDynamicIntensityResponse:
    return HuberDynamicIntensityResponse(
        house=value.house,
        requested_fraction=requested_fraction,
        effective_fraction=value.fraction,
        intensity=value.intensity,
        zone=value.zone.value,
        curve_basis="piecewise_half_cosine_reconstruction",
        provenance=_provenance(engine_entrypoint, stage_sequence),
    )


def _serialize_zone(zone: HouseZoneProfile) -> HuberHouseZoneResponse:
    return HuberHouseZoneResponse(
        house=zone.house,
        cusp_longitude=zone.cusp_longitude,
        next_cusp_longitude=zone.next_cusp_longitude,
        house_size=zone.house_size,
        balance_point_longitude=zone.balance_point_longitude,
        low_point_longitude=zone.low_point_longitude,
        balance_point_fraction=zone.balance_point_fraction,
        low_point_fraction=zone.low_point_fraction,
    )


def _serialize_age_point(
    value: AgePointPosition,
    *,
    frame: HuberDirectHouseFrameRequest,
) -> HuberAgePointResponse:
    return HuberAgePointResponse(
        age_years=value.age_years,
        cycle=value.cycle,
        house=value.house,
        fraction_through_house=value.fraction_through_house,
        longitude=value.longitude,
        zone=value.zone.value,
        years_into_house=value.years_into_house,
        intensity=value.intensity,
        house_frame_provenance=_house_frame_provenance(frame),
        provenance=_provenance(
            "age_point",
            [
                "input_validation",
                "direct_house_frame_binding",
                "age_point_engine_computation",
                "age_point_response_serialization",
            ],
        ),
    )


def _serialize_score(score: PlanetIntensityScore) -> HuberPlanetIntensityScoreResponse:
    return HuberPlanetIntensityScoreResponse(
        name=score.name,
        longitude=score.longitude,
        house=score.house,
        fraction=score.fraction,
        intensity=score.intensity,
        zone=score.zone.value,
        near_cusp=score.near_cusp,
        near_low_point=score.near_low_point,
    )


def compute_huber_dynamic_intensity(
    request: HuberDynamicIntensityRequest,
) -> HuberDynamicIntensityResponse:
    value = dynamic_intensity(request.house, request.fraction)
    return _serialize_dynamic_intensity(
        value,
        requested_fraction=request.fraction,
        engine_entrypoint="dynamic_intensity",
        stage_sequence=[
            "input_validation",
            "dynamic_intensity_engine_computation",
            "dynamic_intensity_response_serialization",
        ],
    )


def compute_huber_house_zones(request: HuberHouseZonesRequest) -> HuberHouseZonesResponse:
    frame = _direct_frame(request.house_frame)
    cusps = _house_cusps_from_direct_frame(frame)
    zones = house_zones(cusps)
    return HuberHouseZonesResponse(
        zones=[_serialize_zone(zone) for zone in zones],
        house_frame=_house_frame_response(frame),
        house_frame_provenance=_house_frame_provenance(frame),
        huber_doctrine="Koch houses are preferred by Huber doctrine; direct cusp derivation is caller-owned.",
        provenance=_provenance(
            "house_zones",
            [
                "input_validation",
                "direct_house_frame_binding",
                "house_zone_engine_computation",
                "house_zone_response_serialization",
            ],
        ),
    )


def compute_huber_age_point(request: HuberAgePointRequest) -> HuberAgePointResponse:
    frame = _direct_frame(request.house_frame)
    cusps = _house_cusps_from_direct_frame(frame)
    return _serialize_age_point(age_point(request.age_years, cusps), frame=frame)


def compute_huber_intensity_at(request: HuberIntensityAtRequest) -> HuberIntensityAtResponse:
    frame = _direct_frame(request.house_frame)
    cusps = _house_cusps_from_direct_frame(frame)
    value = intensity_at(request.longitude, cusps)
    return HuberIntensityAtResponse(
        longitude=request.longitude,
        house=value.house,
        fraction=value.fraction,
        intensity=value.intensity,
        zone=value.zone.value,
        house_frame_provenance=_house_frame_provenance(frame),
        provenance=_provenance(
            "intensity_at",
            [
                "input_validation",
                "direct_house_frame_binding",
                "intensity_at_engine_computation",
                "intensity_at_response_serialization",
            ],
        ),
    )


def compute_huber_chart_intensity_profile(
    request: HuberChartIntensityProfileRequest,
) -> HuberChartIntensityProfileResponse:
    frame = _direct_frame(request.house_frame)
    cusps = _house_cusps_from_direct_frame(frame)
    profile: ChartIntensityProfile = chart_intensity_profile(request.points, cusps)
    return HuberChartIntensityProfileResponse(
        scores=[_serialize_score(score) for score in profile.scores],
        high_intensity=[_serialize_score(score) for score in profile.high_intensity],
        low_intensity=[_serialize_score(score) for score in profile.low_intensity],
        mean_intensity=profile.mean_intensity,
        point_count=len(profile.scores),
        house_frame_provenance=_house_frame_provenance(frame),
        provenance=_provenance(
            "chart_intensity_profile",
            [
                "input_validation",
                "direct_house_frame_binding",
                "point_map_validation",
                "chart_intensity_profile_engine_computation",
                "chart_intensity_profile_response_serialization",
            ],
        ),
    )


def compute_huber_age_point_contacts(
    request: HuberAgePointContactsRequest,
) -> HuberAgePointContactsResponse:
    frame = _direct_frame(request.house_frame)
    cusps = _house_cusps_from_direct_frame(frame)
    contacts = age_point_contacts(
        cusps,
        request.points,
        orb=request.orb,
        start_age=request.start_age,
        end_age=request.end_age,
        step_years=request.step_years,
    )
    return HuberAgePointContactsResponse(
        contacts=[
            HuberAgePointContactResponse(
                age_years=age,
                point_name=point_name,
                separation_degrees=separation,
            )
            for age, point_name, separation in contacts
        ],
        orb=request.orb,
        start_age=request.start_age,
        end_age=request.end_age,
        step_years=request.step_years,
        scan_bounds=HuberScanBoundsResponse(point_count=len(request.points)),
        house_frame_provenance=_house_frame_provenance(frame),
        provenance=_provenance(
            "age_point_contacts",
            [
                "input_validation",
                "direct_house_frame_binding",
                "point_map_validation",
                "contact_scan_bounds_validation",
                "age_point_contacts_engine_computation",
                "age_point_contacts_response_serialization",
            ],
        ),
    )
