"""Source-scoped Pancha Pakshi transport orchestration."""

from __future__ import annotations

from moira import Moira
from moira.pancha_pakshi import (
    available_pancha_pakshi_profiles,
    pancha_pakshi_directed_relationship,
    pancha_pakshi_identity_from_initial_vowel,
    pancha_pakshi_profile_info,
    pancha_pakshi_schedule,
)

from ..models.pancha_pakshi import (
    PanchaPakshiAksaraIdentityRequest,
    PanchaPakshiDirectedRelationshipRequest,
    PanchaPakshiFixedClockMaterializationRequest,
    PanchaPakshiLocalSolarContextRequest,
    PanchaPakshiNominalScheduleRequest,
    PanchaPakshiProfilesResponse,
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


def compute_directed_relationship(request: PanchaPakshiDirectedRelationshipRequest):
    return pancha_pakshi_directed_relationship(
        request.profile_id,
        request.subject,
        request.target,
    )
