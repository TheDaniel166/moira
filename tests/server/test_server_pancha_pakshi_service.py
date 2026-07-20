"""Service and serialization parity for source-scoped Pancha Pakshi routes."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from fractions import Fraction

import pytest

import moira_server.models as public_models
from moira.pancha_pakshi import (
    PanchaPakshiBird,
    PanchaPakshiFixedClockCell,
    PanchaPakshiFixedClockCurrentCellSelectionPolicy,
    PanchaPakshiFixedClockMaterializationPolicy,
    PanchaPakshiHalf,
    PanchaPakshiMaterializedCellRelation,
    PanchaPakshiPaksha,
    PanchaPakshiSolarProportionalCell,
    PanchaPakshiSolarProportionalCurrentCellSelectionPolicy,
    PanchaPakshiSolarProportionalMaterializationPolicy,
    PanchaPakshiWeekday,
    pancha_pakshi_directed_relationship,
    pancha_pakshi_identity_from_initial_vowel,
    pancha_pakshi_profile_info,
    pancha_pakshi_schedule,
)
from moira_server.models.pancha_pakshi import (
    PanchaPakshiAksaraIdentityRequest,
    PanchaPakshiDirectedRelationshipRequest,
    PanchaPakshiFixedClockCurrentCellRequest,
    PanchaPakshiFixedClockMaterializationRequest,
    PanchaPakshiLocalSolarContextRequest,
    PanchaPakshiNominalScheduleRequest,
    PanchaPakshiSolarProportionalCurrentCellRequest,
    PanchaPakshiSolarProportionalMaterializationRequest,
)
from moira_server.serializers.pancha_pakshi import (
    serialize_aksara_identity,
    serialize_directed_relationship,
    serialize_fixed_clock_cell,
    serialize_fixed_clock_current_cell_selection_policy,
    serialize_fixed_clock_materialization_policy,
    serialize_nominal_schedule,
    serialize_profile_info,
    serialize_solar_proportional_cell,
    serialize_solar_proportional_current_cell_selection_policy,
    serialize_solar_proportional_materialization_policy,
)
from moira_server.services.pancha_pakshi import (
    compute_aksara_identity,
    compute_directed_relationship,
    compute_fixed_clock_current_cell,
    compute_fixed_clock_materialization,
    compute_local_solar_context,
    compute_nominal_schedule,
    compute_solar_proportional_current_cell,
    compute_solar_proportional_materialization,
    list_pancha_pakshi_profiles,
    pancha_pakshi_profile,
)


pytestmark = pytest.mark.network

_PROFILE_ID = "agastya_madras_1879_akshara_fixed_clock"


def test_fixed_clock_current_cell_transport_models_are_public() -> None:
    expected = {
        "PanchaPakshiFixedClockCurrentCellRequest",
        "PanchaPakshiFixedClockCurrentCellResponse",
        "PanchaPakshiFixedClockCurrentCellSelectionPolicyResponse",
        "PanchaPakshiSolarProportionalMaterializationRequest",
        "PanchaPakshiSolarProportionalCellResponse",
        "PanchaPakshiSolarProportionalMaterializationPolicyResponse",
        "PanchaPakshiSolarProportionalMaterializationResponse",
        "PanchaPakshiSolarProportionalCurrentCellRequest",
        "PanchaPakshiSolarProportionalCurrentCellResponse",
        "PanchaPakshiSolarProportionalCurrentCellSelectionPolicyResponse",
        "PanchaPakshiNakshatraBirdMappingResponse",
        "PanchaPakshiNatalMoonIdentityPolicyResponse",
        "PanchaPakshiNatalMoonIdentityRequest",
        "PanchaPakshiNatalMoonIdentityResponse",
    }
    assert expected <= set(public_models.__all__)
    for name in expected:
        assert getattr(public_models, name).__module__ == (
            "moira_server.models.pancha_pakshi"
        )


def test_profile_catalog_and_info_service_preserve_no_default_policy() -> None:
    catalog = list_pancha_pakshi_profiles()
    info = pancha_pakshi_profile(_PROFILE_ID)

    assert catalog.default_profile_selected is False
    assert catalog.total == 3
    assert any(profile.profile_id == _PROFILE_ID for profile in catalog.profiles)
    assert info == pancha_pakshi_profile_info(_PROFILE_ID)
    serialized = serialize_profile_info(info)
    assert serialized.provenance.profile_id == _PROFILE_ID
    assert serialized.provenance.astronomical_routing_status == "not_performed"


def test_identity_relationship_and_schedule_services_delegate_to_public_engine() -> None:
    identity_request = PanchaPakshiAksaraIdentityRequest(
        profile_id=_PROFILE_ID,
        initial_vowel="A",
    )
    relation_request = PanchaPakshiDirectedRelationshipRequest(
        profile_id=_PROFILE_ID,
        subject="owl",
        target="peacock",
    )
    schedule_request = PanchaPakshiNominalScheduleRequest(
        profile_id=_PROFILE_ID,
        paksha="purva",
        half="day",
        weekday="sunday",
    )

    identity = compute_aksara_identity(identity_request)
    relationship = compute_directed_relationship(relation_request)
    schedule = compute_nominal_schedule(schedule_request)

    assert identity == pancha_pakshi_identity_from_initial_vowel(_PROFILE_ID, "A")
    assert relationship == pancha_pakshi_directed_relationship(
        _PROFILE_ID,
        PanchaPakshiBird.OWL,
        PanchaPakshiBird.PEACOCK,
    )
    assert schedule == pancha_pakshi_schedule(
        _PROFILE_ID,
        paksha=PanchaPakshiPaksha.PURVA,
        half=PanchaPakshiHalf.DAY,
        weekday=PanchaPakshiWeekday.SUNDAY,
    )

    assert serialize_aksara_identity(identity).bird == "vulture"
    assert serialize_directed_relationship(relationship).relation == "friend"
    serialized_schedule = serialize_nominal_schedule(schedule)
    assert serialized_schedule.cells[0].duration_nazhigai.numerator == 5
    assert serialized_schedule.cells[0].duration_nazhigai.denominator == 4


def test_local_solar_context_service_delegates_through_facade_with_normalized_utc() -> None:
    sentinel = object()
    calls = []

    class FacadeStub:
        def pancha_pakshi_local_solar_context(
            self,
            profile_id,
            dt,
            latitude,
            longitude,
            *,
            paksha,
        ):
            calls.append((profile_id, dt, latitude, longitude, paksha))
            return sentinel

    request = PanchaPakshiLocalSolarContextRequest(
        profile_id=_PROFILE_ID,
        dt=datetime(
            2026,
            7,
            20,
            12,
            tzinfo=timezone(timedelta(hours=-4)),
        ),
        latitude=13.0827,
        longitude=80.2707,
        paksha="purva",
        policy_id="local_solar_day_explicit_paksha_v1",
    )

    assert compute_local_solar_context(FacadeStub(), request) is sentinel
    assert calls == [
        (
            _PROFILE_ID,
            datetime(2026, 7, 20, 16, tzinfo=timezone.utc),
            13.0827,
            80.2707,
            PanchaPakshiPaksha.PURVA,
        )
    ]


def test_fixed_clock_materialization_service_delegates_through_facade_with_normalized_utc() -> None:
    sentinel = object()
    calls = []

    class FacadeStub:
        def pancha_pakshi_fixed_clock_materialization(
            self,
            profile_id,
            dt,
            latitude,
            longitude,
            *,
            paksha,
        ):
            calls.append((profile_id, dt, latitude, longitude, paksha))
            return sentinel

    request = PanchaPakshiFixedClockMaterializationRequest(
        profile_id=_PROFILE_ID,
        dt=datetime(
            2026,
            7,
            20,
            12,
            tzinfo=timezone(timedelta(hours=-4)),
        ),
        latitude=13.0827,
        longitude=80.2707,
        paksha="purva",
        policy_id="fixed_24_minute_nazhigai_from_local_solar_half_start_v1",
    )

    assert compute_fixed_clock_materialization(FacadeStub(), request) is sentinel
    assert calls == [
        (
            _PROFILE_ID,
            datetime(2026, 7, 20, 16, tzinfo=timezone.utc),
            13.0827,
            80.2707,
            PanchaPakshiPaksha.PURVA,
        )
    ]


def test_fixed_clock_current_cell_service_delegates_through_facade_with_normalized_utc() -> None:
    sentinel = object()
    calls = []

    class FacadeStub:
        def pancha_pakshi_fixed_clock_current_cell(
            self,
            profile_id,
            dt,
            latitude,
            longitude,
            *,
            paksha,
        ):
            calls.append((profile_id, dt, latitude, longitude, paksha))
            return sentinel

    request = PanchaPakshiFixedClockCurrentCellRequest(
        profile_id=_PROFILE_ID,
        dt=datetime(
            2026,
            7,
            20,
            12,
            tzinfo=timezone(timedelta(hours=-4)),
        ),
        latitude=13.0827,
        longitude=80.2707,
        paksha="purva",
        policy_id="fixed_clock_current_cell_half_open_solar_precedence_v1",
    )

    assert compute_fixed_clock_current_cell(FacadeStub(), request) is sentinel
    assert calls == [
        (
            _PROFILE_ID,
            datetime(2026, 7, 20, 16, tzinfo=timezone.utc),
            13.0827,
            80.2707,
            PanchaPakshiPaksha.PURVA,
        )
    ]


def test_solar_proportional_service_delegates_through_facade_with_normalized_utc() -> None:
    sentinel = object()
    calls = []

    class FacadeStub:
        def pancha_pakshi_solar_proportional_materialization(
            self,
            profile_id,
            dt,
            latitude,
            longitude,
            *,
            paksha,
        ):
            calls.append((profile_id, dt, latitude, longitude, paksha))
            return sentinel

    request = PanchaPakshiSolarProportionalMaterializationRequest(
        profile_id=_PROFILE_ID,
        dt=datetime(
            2026,
            7,
            20,
            12,
            tzinfo=timezone(timedelta(hours=-4)),
        ),
        latitude=13.0827,
        longitude=80.2707,
        paksha="purva",
        policy_id=(
            "solar_proportional_nominal_offsets_over_governing_half_tt_v1"
        ),
    )

    assert compute_solar_proportional_materialization(
        FacadeStub(), request
    ) is sentinel
    assert calls == [
        (
            _PROFILE_ID,
            datetime(2026, 7, 20, 16, tzinfo=timezone.utc),
            13.0827,
            80.2707,
            PanchaPakshiPaksha.PURVA,
        )
    ]


def test_solar_proportional_current_cell_service_delegates_with_normalized_utc() -> None:
    sentinel = object()
    calls = []

    class FacadeStub:
        def pancha_pakshi_solar_proportional_current_cell(
            self,
            profile_id,
            dt,
            latitude,
            longitude,
            *,
            paksha,
        ):
            calls.append((profile_id, dt, latitude, longitude, paksha))
            return sentinel

    request = PanchaPakshiSolarProportionalCurrentCellRequest(
        profile_id=_PROFILE_ID,
        dt=datetime(
            2026,
            7,
            20,
            12,
            tzinfo=timezone(timedelta(hours=-4)),
        ),
        latitude=13.0827,
        longitude=80.2707,
        paksha="purva",
        policy_id=(
            "solar_proportional_current_cell_half_open_solar_precedence_v1"
        ),
    )

    assert compute_solar_proportional_current_cell(
        FacadeStub(), request
    ) is sentinel
    assert calls == [
        (
            _PROFILE_ID,
            datetime(2026, 7, 20, 16, tzinfo=timezone.utc),
            13.0827,
            80.2707,
            PanchaPakshiPaksha.PURVA,
        )
    ]


def test_fixed_clock_policy_and_cell_serializers_match_engine_contract() -> None:
    schedule = pancha_pakshi_schedule(
        _PROFILE_ID,
        paksha=PanchaPakshiPaksha.PURVA,
        half=PanchaPakshiHalf.DAY,
        weekday=PanchaPakshiWeekday.SUNDAY,
    )
    policy = serialize_fixed_clock_materialization_policy(
        PanchaPakshiFixedClockMaterializationPolicy()
    )
    cell = serialize_fixed_clock_cell(
        PanchaPakshiFixedClockCell(
            schedule_cell_index=0,
            nominal_cell=schedule.cells[0],
            start_jd_tt=2461242.0,
            end_jd_tt=2461242.0208333335,
            start_jd_ut1=2461241.9992,
            end_jd_ut1=2461242.0200333335,
            duration_seconds=Fraction(1800),
            solar_half_relation=(
                PanchaPakshiMaterializedCellRelation.WITHIN_GOVERNING_SOLAR_HALF
            ),
        )
    )

    assert policy.model_dump() == {
        "policy_id": "fixed_24_minute_nazhigai_from_local_solar_half_start_v1",
        "paksha_basis": "caller_supplied_source_label",
        "solar_context_basis": "topocentric_sunrise_to_next_sunrise",
        "day_anchor": "governing_topocentric_sunrise",
        "night_anchor": "governing_topocentric_sunset",
        "nazhigai_seconds": 1440,
        "half_span_nazhigai": 30,
        "half_span_seconds": 43200,
        "offset_arithmetic_time_scale": "reader_bound_tt",
        "published_endpoint_time_scale": "ut1",
        "interval_ownership": "half_open",
        "solar_end_clipping": "none",
        "topology_metric": "fixed_end_jd_tt_minus_solar_end_jd_tt",
        "topology_coalescence_seconds": 0.0001,
        "current_cell_status": "not_performed",
        "solar_proportional_scaling_status": "not_performed",
    }
    assert cell.schedule_cell_index == 0
    assert cell.nominal_cell.duration_nazhigai.model_dump() == {
        "numerator": 5,
        "denominator": 4,
    }
    assert cell.duration_seconds.model_dump() == {
        "numerator": 1800,
        "denominator": 1,
    }
    assert cell.solar_half_relation == "within_governing_solar_half"


def test_fixed_clock_current_cell_policy_serializer_is_exhaustive() -> None:
    policy = serialize_fixed_clock_current_cell_selection_policy(
        PanchaPakshiFixedClockCurrentCellSelectionPolicy()
    )

    assert policy.model_dump() == {
        "policy_id": "fixed_clock_current_cell_half_open_solar_precedence_v1",
        "materialization_policy_id": (
            "fixed_24_minute_nazhigai_from_local_solar_half_start_v1"
        ),
        "paksha_basis": "caller_supplied_source_label",
        "selection_time_scale": "reader_bound_tt",
        "interval_ownership": "half_open",
        "solar_half_precedence": (
            "resolve_governing_solar_half_before_selection"
        ),
        "membership_tolerance_seconds": 0.0,
        "unmaterialized_solar_half_tail": "explicit_no_current_cell",
        "solar_end_clipping": "none",
        "fixed_span_wrap": "none",
        "fixed_span_repeat": "none",
        "solar_proportional_scaling_status": "not_performed",
        "astronomical_paksha_inference_status": "not_performed",
    }


def test_solar_proportional_policy_and_cell_serializers_are_exhaustive() -> None:
    schedule = pancha_pakshi_schedule(
        _PROFILE_ID,
        paksha=PanchaPakshiPaksha.PURVA,
        half=PanchaPakshiHalf.DAY,
        weekday=PanchaPakshiWeekday.SUNDAY,
    )
    nominal_cell = schedule.cells[0]
    policy = serialize_solar_proportional_materialization_policy(
        PanchaPakshiSolarProportionalMaterializationPolicy()
    )
    start_jd_tt = 2461242.0
    end_jd_tt = start_jd_tt + 1650.0 / 86400.0
    duration_seconds_tt = (end_jd_tt - start_jd_tt) * 86400.0
    cell = serialize_solar_proportional_cell(
        PanchaPakshiSolarProportionalCell(
            schedule_cell_index=0,
            nominal_cell=nominal_cell,
            start_offset_fraction=Fraction(0),
            end_offset_fraction=Fraction(1, 24),
            span_fraction=Fraction(1, 24),
            start_jd_tt=start_jd_tt,
            end_jd_tt=end_jd_tt,
            start_jd_ut1=2461241.9992,
            end_jd_ut1=2461241.9992 + 1650.0 / 86400.0,
            duration_seconds_tt=duration_seconds_tt,
        )
    )

    assert policy.model_dump() == {
        "policy_id": (
            "solar_proportional_nominal_offsets_over_governing_half_tt_v1"
        ),
        "paksha_basis": "caller_supplied_source_label",
        "solar_context_basis": "topocentric_sunrise_to_next_sunrise",
        "day_anchor": "governing_topocentric_sunrise",
        "night_anchor": "governing_topocentric_sunset",
        "nominal_offset_basis": "exact_fraction_of_nominal_schedule_span",
        "mapping_time_scale": "reader_bound_tt",
        "published_endpoint_time_scale": "ut1",
        "endpoint_mapping": (
            "independent_anchor_plus_fraction_of_governing_solar_half"
        ),
        "endpoint_closure": "exact_anchor_and_governing_solar_half_end",
        "interval_ownership": "half_open",
        "solar_end_clipping": "none",
        "solar_half_wrap": "none",
        "solar_half_repeat": "none",
        "fixed_nazhigai_seconds_status": "not_used",
        "current_cell_status": "not_performed",
        "astronomical_paksha_inference_status": "not_performed",
    }
    assert cell.schedule_cell_index == 0
    assert cell.start_offset_fraction.model_dump() == {
        "numerator": 0,
        "denominator": 1,
    }
    assert cell.end_offset_fraction.model_dump() == {
        "numerator": 1,
        "denominator": 24,
    }
    assert cell.span_fraction == cell.end_offset_fraction
    assert cell.duration_seconds_tt == duration_seconds_tt


def test_solar_proportional_current_cell_policy_serializer_is_exhaustive() -> None:
    policy = serialize_solar_proportional_current_cell_selection_policy(
        PanchaPakshiSolarProportionalCurrentCellSelectionPolicy()
    )

    assert policy.model_dump() == {
        "policy_id": (
            "solar_proportional_current_cell_half_open_solar_precedence_v1"
        ),
        "materialization_policy_id": (
            "solar_proportional_nominal_offsets_over_governing_half_tt_v1"
        ),
        "paksha_basis": "caller_supplied_source_label",
        "selection_time_scale": "reader_bound_tt",
        "interval_ownership": "half_open",
        "solar_half_precedence": (
            "resolve_governing_solar_half_before_selection"
        ),
        "membership_tolerance_seconds": 0.0,
        "coverage_requirement": "complete_governing_solar_half",
        "required_match_count": 1,
        "unmaterialized_solar_half_tail_status": "not_applicable",
        "invalid_match_policy": "fail_closed",
        "fixed_clock_mixing_status": "not_performed",
        "astronomical_paksha_inference_status": "not_performed",
    }
