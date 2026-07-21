"""REST routes for named, source-scoped Pancha Pakshi computation."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path

from moira import Moira

from ..dependencies import get_engine
from ..models.pancha_pakshi import (
    PanchaPakshiAksaraIdentityRequest,
    PanchaPakshiAksaraIdentityResponse,
    PanchaPakshiAstronomicalPakshaRequest,
    PanchaPakshiAstronomicalPakshaResponse,
    PanchaPakshiCivilTimeSookshmaSelectionRequest,
    PanchaPakshiCivilTimeSookshmaSelectionResponse,
    PanchaPakshiDirectedRelationshipRequest,
    PanchaPakshiDirectedRelationshipResponse,
    PanchaPakshiFixedClockCurrentCellRequest,
    PanchaPakshiFixedClockCurrentCellResponse,
    PanchaPakshiFixedClockMaterializationRequest,
    PanchaPakshiFixedClockMaterializationResponse,
    PanchaPakshiFirstEatBirdMappingRequest,
    PanchaPakshiFirstEatBirdMappingResponse,
    PanchaPakshiLocalSolarContextRequest,
    PanchaPakshiLocalSolarContextResponse,
    PanchaPakshiNatalMoonIdentityRequest,
    PanchaPakshiNatalMoonIdentityResponse,
    PanchaPakshiNominalScheduleRequest,
    PanchaPakshiNominalScheduleResponse,
    PanchaPakshiPaduBirdMappingRequest,
    PanchaPakshiPaduBirdMappingResponse,
    PanchaPakshiProfileInfoResponse,
    PanchaPakshiProfilesResponse,
    PanchaPakshiSolarProportionalCurrentCellRequest,
    PanchaPakshiSolarProportionalCurrentCellResponse,
    PanchaPakshiSolarProportionalMaterializationRequest,
    PanchaPakshiSolarProportionalMaterializationResponse,
    PanchaPakshiScheduleSookshmaSelectionRequest,
    PanchaPakshiScheduleSookshmaSelectionResponse,
    PanchaPakshiSookshmaSelectionRequest,
    PanchaPakshiSookshmaSelectionResponse,
)
from ..serializers.pancha_pakshi import (
    serialize_aksara_identity,
    serialize_astronomical_paksha,
    serialize_civil_time_sookshma_selection,
    serialize_directed_relationship,
    serialize_fixed_clock_current_cell,
    serialize_fixed_clock_materialization,
    serialize_first_eat_bird_mapping,
    serialize_local_solar_context,
    serialize_natal_moon_identity,
    serialize_nominal_schedule,
    serialize_padu_bird_mapping,
    serialize_profile_info,
    serialize_solar_proportional_current_cell,
    serialize_solar_proportional_materialization,
    serialize_schedule_sookshma_temporal_selection,
    serialize_sookshma_temporal_selection,
)
from ..services.pancha_pakshi import (
    compute_aksara_identity,
    compute_astronomical_paksha,
    compute_civil_time_sookshma_selection,
    compute_directed_relationship,
    compute_fixed_clock_current_cell,
    compute_fixed_clock_materialization,
    compute_first_eat_bird_mapping,
    compute_local_solar_context,
    compute_natal_moon_identity,
    compute_nominal_schedule,
    compute_padu_bird_mapping,
    compute_solar_proportional_current_cell,
    compute_solar_proportional_materialization,
    compute_schedule_sookshma_temporal_selection,
    compute_sookshma_temporal_selection,
    list_pancha_pakshi_profiles,
    pancha_pakshi_profile,
)


router = APIRouter(prefix="/v1/pancha-pakshi", tags=["pancha-pakshi"])


@router.get("/profiles", response_model=PanchaPakshiProfilesResponse)
def pancha_pakshi_profiles_route() -> PanchaPakshiProfilesResponse:
    """List explicitly registered profiles without selecting a default."""
    return list_pancha_pakshi_profiles()


@router.get("/profiles/{profile_id}", response_model=PanchaPakshiProfileInfoResponse)
def pancha_pakshi_profile_route(
    profile_id: str = Path(..., min_length=1),
) -> PanchaPakshiProfileInfoResponse:
    """Return provenance, omissions, and witness metadata for one profile."""
    return serialize_profile_info(pancha_pakshi_profile(profile_id))


@router.post("/identity/aksara", response_model=PanchaPakshiAksaraIdentityResponse)
def pancha_pakshi_aksara_identity_route(
    request: PanchaPakshiAksaraIdentityRequest,
) -> PanchaPakshiAksaraIdentityResponse:
    """Resolve a named profile's explicit aksara query/name-initial mapping."""
    return serialize_aksara_identity(compute_aksara_identity(request))


@router.post(
    "/identity/natal-moon",
    response_model=PanchaPakshiNatalMoonIdentityResponse,
)
def pancha_pakshi_natal_moon_identity_route(
    request: PanchaPakshiNatalMoonIdentityRequest,
    engine: Annotated[Moira, Depends(get_engine)],
) -> PanchaPakshiNatalMoonIdentityResponse:
    """Apply a named source table through the fixed modern natal-Moon policy."""

    return serialize_natal_moon_identity(
        compute_natal_moon_identity(engine, request)
    )


@router.post("/schedule/nominal", response_model=PanchaPakshiNominalScheduleResponse)
def pancha_pakshi_nominal_schedule_route(
    request: PanchaPakshiNominalScheduleRequest,
) -> PanchaPakshiNominalScheduleResponse:
    """Generate an exact fixed-clock nominal schedule; no astronomy is routed."""
    return serialize_nominal_schedule(compute_nominal_schedule(request))


@router.post(
    "/schedule/first-eat-bird",
    response_model=PanchaPakshiFirstEatBirdMappingResponse,
)
def pancha_pakshi_first_eat_bird_mapping_route(
    request: PanchaPakshiFirstEatBirdMappingRequest,
) -> PanchaPakshiFirstEatBirdMappingResponse:
    """Return one source-attested first-samam Eat seed; route no astronomy."""

    return serialize_first_eat_bird_mapping(
        compute_first_eat_bird_mapping(request)
    )


@router.post(
    "/roles/padu",
    response_model=PanchaPakshiPaduBirdMappingResponse,
)
def pancha_pakshi_padu_bird_mapping_route(
    request: PanchaPakshiPaduBirdMappingRequest,
) -> PanchaPakshiPaduBirdMappingResponse:
    """Return one source-attested Padu bird; perform no temporal routing."""

    return serialize_padu_bird_mapping(compute_padu_bird_mapping(request))


@router.post(
    "/sookshma/select",
    response_model=PanchaPakshiSookshmaSelectionResponse,
)
def pancha_pakshi_sookshma_temporal_selection_route(
    request: PanchaPakshiSookshmaSelectionRequest,
) -> PanchaPakshiSookshmaSelectionResponse:
    """Select one exact Sookshma interval under an explicit policy."""

    return serialize_sookshma_temporal_selection(
        compute_sookshma_temporal_selection(request)
    )


@router.post(
    "/sookshma/schedule-select",
    response_model=PanchaPakshiScheduleSookshmaSelectionResponse,
)
def pancha_pakshi_schedule_sookshma_temporal_selection_route(
    request: PanchaPakshiScheduleSookshmaSelectionRequest,
) -> PanchaPakshiScheduleSookshmaSelectionResponse:
    """Compose explicit schedule axes with one explicit Sookshma policy."""

    return serialize_schedule_sookshma_temporal_selection(
        compute_schedule_sookshma_temporal_selection(request)
    )


@router.post(
    "/sookshma/civil-time-select",
    response_model=PanchaPakshiCivilTimeSookshmaSelectionResponse,
)
def pancha_pakshi_civil_time_sookshma_selection_route(
    request: PanchaPakshiCivilTimeSookshmaSelectionRequest,
    engine: Annotated[Moira, Depends(get_engine)],
) -> PanchaPakshiCivilTimeSookshmaSelectionResponse:
    """Route civil time under explicit timing and Sookshma policies."""

    return serialize_civil_time_sookshma_selection(
        compute_civil_time_sookshma_selection(engine, request)
    )


@router.post(
    "/context/astronomical-paksha",
    response_model=PanchaPakshiAstronomicalPakshaResponse,
)
def pancha_pakshi_astronomical_paksha_route(
    request: PanchaPakshiAstronomicalPakshaRequest,
    engine: Annotated[Moira, Depends(get_engine)],
) -> PanchaPakshiAstronomicalPakshaResponse:
    """Infer the named profile paksha from geocentric lunar elongation."""

    return serialize_astronomical_paksha(
        compute_astronomical_paksha(engine, request)
    )


@router.post(
    "/schedule/fixed-clock",
    response_model=PanchaPakshiFixedClockMaterializationResponse,
)
def pancha_pakshi_fixed_clock_materialization_route(
    request: PanchaPakshiFixedClockMaterializationRequest,
    engine: Annotated[Moira, Depends(get_engine)],
) -> PanchaPakshiFixedClockMaterializationResponse:
    """Materialize fixed 24-minute nazhigai cells from the governing half start."""

    return serialize_fixed_clock_materialization(
        compute_fixed_clock_materialization(engine, request)
    )


@router.post(
    "/schedule/fixed-clock/current-cell",
    response_model=PanchaPakshiFixedClockCurrentCellResponse,
)
def pancha_pakshi_fixed_clock_current_cell_route(
    request: PanchaPakshiFixedClockCurrentCellRequest,
    engine: Annotated[Moira, Depends(get_engine)],
) -> PanchaPakshiFixedClockCurrentCellResponse:
    """Select at most one fixed-clock cell for the requested instant."""

    return serialize_fixed_clock_current_cell(
        compute_fixed_clock_current_cell(engine, request)
    )


@router.post(
    "/schedule/solar-proportional",
    response_model=PanchaPakshiSolarProportionalMaterializationResponse,
)
def pancha_pakshi_solar_proportional_materialization_route(
    request: PanchaPakshiSolarProportionalMaterializationRequest,
    engine: Annotated[Moira, Depends(get_engine)],
) -> PanchaPakshiSolarProportionalMaterializationResponse:
    """Materialize exact nominal fractions over the governing solar half."""

    return serialize_solar_proportional_materialization(
        compute_solar_proportional_materialization(engine, request)
    )


@router.post(
    "/schedule/solar-proportional/current-cell",
    response_model=PanchaPakshiSolarProportionalCurrentCellResponse,
)
def pancha_pakshi_solar_proportional_current_cell_route(
    request: PanchaPakshiSolarProportionalCurrentCellRequest,
    engine: Annotated[Moira, Depends(get_engine)],
) -> PanchaPakshiSolarProportionalCurrentCellResponse:
    """Select the unique proportional cell for the requested instant."""

    return serialize_solar_proportional_current_cell(
        compute_solar_proportional_current_cell(engine, request)
    )


@router.post(
    "/context/local-solar",
    response_model=PanchaPakshiLocalSolarContextResponse,
)
def pancha_pakshi_local_solar_context_route(
    request: PanchaPakshiLocalSolarContextRequest,
    engine: Annotated[Moira, Depends(get_engine)],
) -> PanchaPakshiLocalSolarContextResponse:
    """Resolve weekday and day/night while retaining caller-supplied paksha."""

    return serialize_local_solar_context(compute_local_solar_context(engine, request))


@router.post(
    "/relationships/directed",
    response_model=PanchaPakshiDirectedRelationshipResponse,
)
def pancha_pakshi_directed_relationship_route(
    request: PanchaPakshiDirectedRelationshipRequest,
) -> PanchaPakshiDirectedRelationshipResponse:
    """Return one explicit directed relation without reciprocal inference."""
    return serialize_directed_relationship(compute_directed_relationship(request))
