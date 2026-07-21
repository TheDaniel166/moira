"""Source-scoped Pancha Pakshi transport orchestration."""

from __future__ import annotations

from fractions import Fraction

from moira import Moira
from moira.pancha_pakshi import (
    PanchaPakshiSookshmaSelectorPolicyId,
    available_pancha_pakshi_profiles,
    pancha_pakshi_directed_relationship,
    pancha_pakshi_first_eat_bird_mapping,
    pancha_pakshi_identity_from_initial_vowel,
    pancha_pakshi_padu_bird_mapping,
    pancha_pakshi_profile_info,
    pancha_pakshi_schedule,
    pancha_pakshi_schedule_sookshma_temporal_selection,
    pancha_pakshi_sookshma_temporal_selection,
)

from ..models.pancha_pakshi import (
    PanchaPakshiAksaraIdentityRequest,
    PanchaPakshiAstronomicalPakshaRequest,
    PanchaPakshiDirectedRelationshipRequest,
    PanchaPakshiFixedClockCurrentCellRequest,
    PanchaPakshiFixedClockMaterializationRequest,
    PanchaPakshiFirstEatBirdMappingRequest,
    PanchaPakshiLocalSolarContextRequest,
    PanchaPakshiNatalMoonIdentityRequest,
    PanchaPakshiNominalScheduleRequest,
    PanchaPakshiPaduBirdMappingRequest,
    PanchaPakshiProfilesResponse,
    PanchaPakshiSolarProportionalCurrentCellRequest,
    PanchaPakshiSolarProportionalMaterializationRequest,
    PanchaPakshiScheduleSookshmaSelectionRequest,
    PanchaPakshiSookshmaSelectionRequest,
)
from ..serializers.pancha_pakshi import serialize_profile_descriptor


def list_pancha_pakshi_profiles() -> PanchaPakshiProfilesResponse:
    profiles = available_pancha_pakshi_profiles()
    return PanchaPakshiProfilesResponse(
        profiles=[serialize_profile_descriptor(profile) for profile in profiles],
        total=len(profiles),
    )


def pancha_pakshi_profile(profile_id: str):
    return pancha_pakshi_profile_info(profile_id)


def compute_aksara_identity(request: PanchaPakshiAksaraIdentityRequest):
    return pancha_pakshi_identity_from_initial_vowel(
        request.profile_id,
        request.initial_vowel,
    )


def compute_nominal_schedule(request: PanchaPakshiNominalScheduleRequest):
    return pancha_pakshi_schedule(
        request.profile_id,
        paksha=request.paksha,
        half=request.half,
        weekday=request.weekday,
    )


def compute_first_eat_bird_mapping(
    request: PanchaPakshiFirstEatBirdMappingRequest,
):
    """Return one pure source-generator first-samam Eat-bird lookup."""

    return pancha_pakshi_first_eat_bird_mapping(
        request.profile_id,
        profile_paksha=request.profile_paksha,
        half=request.half,
        weekday=request.weekday,
    )


def compute_padu_bird_mapping(request: PanchaPakshiPaduBirdMappingRequest):
    """Return one pure Paksha-and-weekday source-table lookup."""

    return pancha_pakshi_padu_bird_mapping(
        request.profile_id,
        profile_paksha=request.profile_paksha,
        weekday=request.weekday,
    )


def compute_sookshma_temporal_selection(
    request: PanchaPakshiSookshmaSelectionRequest,
):
    """Select one exact interval without clock, astronomy, or outcomes."""

    return pancha_pakshi_sookshma_temporal_selection(
        request.profile_id,
        policy_id=PanchaPakshiSookshmaSelectorPolicyId(request.policy_id),
        parent_activity=request.parent_activity,
        elapsed_nazhigai=Fraction(
            request.elapsed_nazhigai.numerator,
            request.elapsed_nazhigai.denominator,
        ),
    )


def compute_schedule_sookshma_temporal_selection(
    request: PanchaPakshiScheduleSookshmaSelectionRequest,
):
    """Compose explicit schedule axes without routing a clock or outcomes."""

    return pancha_pakshi_schedule_sookshma_temporal_selection(
        request.schedule_profile_id,
        request.selector_profile_id,
        profile_paksha=request.profile_paksha,
        half=request.half,
        weekday=request.weekday,
        samam_index=request.samam_index,
        subject_bird=request.subject_bird,
        selector_policy_id=PanchaPakshiSookshmaSelectorPolicyId(
            request.selector_policy_id
        ),
        elapsed_nazhigai=Fraction(
            request.elapsed_nazhigai.numerator,
            request.elapsed_nazhigai.denominator,
        ),
    )


def compute_astronomical_paksha(
    engine: Moira,
    request: PanchaPakshiAstronomicalPakshaRequest,
):
    """Delegate the sole admitted lunar-paksha policy through the facade."""

    return engine.pancha_pakshi_astronomical_paksha(
        request.profile_id,
        request.dt,
    )


def compute_natal_moon_identity(
    engine: Moira,
    request: PanchaPakshiNatalMoonIdentityRequest,
):
    """Delegate the fixed modern natal-Moon composition through the facade."""

    return engine.pancha_pakshi_natal_moon_identity(
        request.profile_id,
        request.dt,
    )


def compute_local_solar_context(
    engine: Moira,
    request: PanchaPakshiLocalSolarContextRequest,
):
    """Delegate UTC normalization and UT1 routing through the public facade."""

    return engine.pancha_pakshi_local_solar_context(
        request.profile_id,
        request.dt,
        request.latitude,
        request.longitude,
        paksha=request.paksha,
    )


def compute_fixed_clock_materialization(
    engine: Moira,
    request: PanchaPakshiFixedClockMaterializationRequest,
):
    """Delegate fixed-clock materialization through the public facade."""

    return engine.pancha_pakshi_fixed_clock_materialization(
        request.profile_id,
        request.dt,
        request.latitude,
        request.longitude,
        paksha=request.paksha,
    )


def compute_fixed_clock_current_cell(
    engine: Moira,
    request: PanchaPakshiFixedClockCurrentCellRequest,
):
    """Delegate bounded current-cell selection through the public facade."""

    return engine.pancha_pakshi_fixed_clock_current_cell(
        request.profile_id,
        request.dt,
        request.latitude,
        request.longitude,
        paksha=request.paksha,
    )


def compute_solar_proportional_materialization(
    engine: Moira,
    request: PanchaPakshiSolarProportionalMaterializationRequest,
):
    """Delegate proportional solar-half materialization through the facade."""

    return engine.pancha_pakshi_solar_proportional_materialization(
        request.profile_id,
        request.dt,
        request.latitude,
        request.longitude,
        paksha=request.paksha,
    )


def compute_solar_proportional_current_cell(
    engine: Moira,
    request: PanchaPakshiSolarProportionalCurrentCellRequest,
):
    """Delegate proportional current-cell selection through the facade."""

    return engine.pancha_pakshi_solar_proportional_current_cell(
        request.profile_id,
        request.dt,
        request.latitude,
        request.longitude,
        paksha=request.paksha,
    )


def compute_directed_relationship(request: PanchaPakshiDirectedRelationshipRequest):
    return pancha_pakshi_directed_relationship(
        request.profile_id,
        request.subject,
        request.target,
    )
