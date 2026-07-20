"""Serializers for first-class, source-scoped Pancha Pakshi vessels."""

from __future__ import annotations

from fractions import Fraction

from moira.pancha_pakshi import (
    PanchaPakshiConflictWitness,
    PanchaPakshiDirectedRelationship,
    PanchaPakshiFixedClockCell,
    PanchaPakshiFixedClockCurrentCellSelection,
    PanchaPakshiFixedClockCurrentCellSelectionPolicy,
    PanchaPakshiFixedClockMaterialization,
    PanchaPakshiFixedClockMaterializationPolicy,
    PanchaPakshiInitialVowelIdentity,
    PanchaPakshiLocalSolarContext,
    PanchaPakshiLocalSolarContextPolicy,
    PanchaPakshiOmission,
    PanchaPakshiProfileDescriptor,
    PanchaPakshiProfileInfo,
    PanchaPakshiProvenance,
    PanchaPakshiSchedule,
    PanchaPakshiScheduleCell,
    PanchaPakshiSource,
    PanchaPakshiSourceLocator,
)

from ..models.pancha_pakshi import (
    PanchaPakshiAksaraIdentityResponse,
    PanchaPakshiConflictWitnessResponse,
    PanchaPakshiDirectedRelationshipResponse,
    PanchaPakshiFixedClockCellResponse,
    PanchaPakshiFixedClockCurrentCellResponse,
    PanchaPakshiFixedClockCurrentCellSelectionPolicyResponse,
    PanchaPakshiFixedClockMaterializationPolicyResponse,
    PanchaPakshiFixedClockMaterializationResponse,
    PanchaPakshiFractionResponse,
    PanchaPakshiLocalSolarContextPolicyResponse,
    PanchaPakshiLocalSolarContextResponse,
    PanchaPakshiNominalScheduleResponse,
    PanchaPakshiOmissionResponse,
    PanchaPakshiProfileDescriptorResponse,
    PanchaPakshiProfileInfoResponse,
    PanchaPakshiProvenanceResponse,
    PanchaPakshiScheduleCellResponse,
    PanchaPakshiSourceLocatorResponse,
    PanchaPakshiSourceResponse,
)


def serialize_fraction(value: Fraction) -> PanchaPakshiFractionResponse:
    return PanchaPakshiFractionResponse(
        numerator=value.numerator,
        denominator=value.denominator,
    )


def serialize_source_locator(
    locator: PanchaPakshiSourceLocator,
) -> PanchaPakshiSourceLocatorResponse:
    return PanchaPakshiSourceLocatorResponse(
        locator_id=locator.locator_id,
        witness_id=locator.witness_id,
        label=locator.label,
        url=locator.url,
        evidence_role=locator.evidence_role,
    )


def serialize_source(source: PanchaPakshiSource) -> PanchaPakshiSourceResponse:
    return PanchaPakshiSourceResponse(
        witness_id=source.witness_id,
        title=source.title,
        traditional_attribution=source.traditional_attribution,
        authorship_status=source.authorship_status,
        publication_place=source.publication_place,
        publisher=source.publisher,
        publication_year=source.publication_year,
        language=source.language,
        archive_item_url=source.archive_item_url,
        archive_original_image_zip_name=source.archive_original_image_zip_name,
        archive_original_image_zip_source_status=source.archive_original_image_zip_source_status,
        archive_original_image_zip_md5=source.archive_original_image_zip_md5,
        archive_original_image_zip_sha1=source.archive_original_image_zip_sha1,
        archive_pdf_name=source.archive_pdf_name,
        archive_pdf_source_status=source.archive_pdf_source_status,
        archive_pdf_md5=source.archive_pdf_md5,
        archive_pdf_sha1=source.archive_pdf_sha1,
        locally_verified_pdf_sha256=source.locally_verified_pdf_sha256,
        catalogued_contributor_note=source.catalogued_contributor_note,
        artifact_distribution_status=source.artifact_distribution_status,
        redistribution_policy=source.redistribution_policy,
        license_scope=source.license_scope,
        artifact_distribution_note=source.artifact_distribution_note,
    )


def serialize_omission(omission: PanchaPakshiOmission) -> PanchaPakshiOmissionResponse:
    return PanchaPakshiOmissionResponse(
        feature=omission.feature,
        status=omission.status,
        reason=omission.reason,
    )


def serialize_conflict_witness(
    witness: PanchaPakshiConflictWitness,
) -> PanchaPakshiConflictWitnessResponse:
    return PanchaPakshiConflictWitnessResponse(
        witness_id=witness.witness_id,
        bibliographic_label=witness.bibliographic_label,
        record_url=witness.record_url,
        record_identity=witness.record_identity,
        conflict_locators=list(witness.conflict_locators),
        evidence_status=witness.evidence_status,
        runtime_status=witness.runtime_status,
    )


def serialize_profile_descriptor(
    descriptor: PanchaPakshiProfileDescriptor,
) -> PanchaPakshiProfileDescriptorResponse:
    return PanchaPakshiProfileDescriptorResponse(
        profile_id=descriptor.profile_id,
        admission_status=descriptor.admission_status,
        product_kind=descriptor.product_kind,
        default_selection_allowed=descriptor.default_selection_allowed,
        capabilities=list(descriptor.capabilities),
        admission_decision_id=descriptor.admission_decision_id,
    )


def serialize_provenance(
    provenance: PanchaPakshiProvenance,
) -> PanchaPakshiProvenanceResponse:
    return PanchaPakshiProvenanceResponse(
        profile_id=provenance.profile_id,
        admission_status=provenance.admission_status,
        product_kind=provenance.product_kind,
        default_selection_allowed=provenance.default_selection_allowed,
        capabilities=list(provenance.capabilities),
        admission_decision_id=provenance.admission_decision_id,
        derivation_status=provenance.derivation_status,
        assembly_policy=provenance.assembly_policy,
        astronomical_routing_status=provenance.astronomical_routing_status,
        source=serialize_source(provenance.source),
        declared_omissions=[
            serialize_omission(omission) for omission in provenance.declared_omissions
        ],
    )


def serialize_profile_info(info: PanchaPakshiProfileInfo) -> PanchaPakshiProfileInfoResponse:
    return PanchaPakshiProfileInfoResponse(
        title=info.title,
        provenance=serialize_provenance(info.provenance),
        source_locators=[serialize_source_locator(locator) for locator in info.source_locators],
        known_conflict_witnesses=[
            serialize_conflict_witness(witness)
            for witness in info.known_conflict_witnesses
        ],
    )


def serialize_aksara_identity(
    identity: PanchaPakshiInitialVowelIdentity,
) -> PanchaPakshiAksaraIdentityResponse:
    return PanchaPakshiAksaraIdentityResponse(
        profile_id=identity.profile_id,
        identity_kind=identity.identity_kind,
        input_symbol=identity.input_symbol,
        normalized_symbol=identity.normalized_symbol,
        bird=identity.bird,
        is_natal_moon_identity=identity.is_natal_moon_identity,
        source_locators=[
            serialize_source_locator(locator) for locator in identity.source_locators
        ],
        provenance=serialize_provenance(identity.provenance),
    )


def serialize_directed_relationship(
    relationship: PanchaPakshiDirectedRelationship,
) -> PanchaPakshiDirectedRelationshipResponse:
    return PanchaPakshiDirectedRelationshipResponse(
        profile_id=relationship.profile_id,
        model_kind=relationship.model_kind,
        subject=relationship.subject,
        target=relationship.target,
        relation=relationship.relation,
        is_reciprocal_inference=relationship.is_reciprocal_inference,
        source_locators=[
            serialize_source_locator(locator) for locator in relationship.source_locators
        ],
        provenance=serialize_provenance(relationship.provenance),
    )


def serialize_schedule_cell(cell: PanchaPakshiScheduleCell) -> PanchaPakshiScheduleCellResponse:
    return PanchaPakshiScheduleCellResponse(
        samam_index=cell.samam_index,
        sequence_index=cell.sequence_index,
        bird=cell.bird,
        activity=cell.activity,
        start_nazhigai=serialize_fraction(cell.start_nazhigai),
        end_nazhigai=serialize_fraction(cell.end_nazhigai),
        duration_nazhigai=serialize_fraction(cell.duration_nazhigai),
        derivation_status=cell.derivation_status,
        assembly_policy=cell.assembly_policy,
        source_locators=[serialize_source_locator(locator) for locator in cell.source_locators],
    )


def serialize_nominal_schedule(schedule: PanchaPakshiSchedule) -> PanchaPakshiNominalScheduleResponse:
    return PanchaPakshiNominalScheduleResponse(
        profile_id=schedule.profile_id,
        admission_status=schedule.admission_status,
        product_kind=schedule.product_kind,
        generator_id=schedule.generator_id,
        paksha=schedule.paksha,
        half=schedule.half,
        weekday=schedule.weekday,
        first_eat_bird=schedule.first_eat_bird,
        temporal_model_kind=schedule.temporal_model_kind,
        span_nazhigai=serialize_fraction(schedule.span_nazhigai),
        samam_span_nazhigai=serialize_fraction(schedule.samam_span_nazhigai),
        cells=[serialize_schedule_cell(cell) for cell in schedule.cells],
        provenance=serialize_provenance(schedule.provenance),
    )


def serialize_local_solar_context_policy(
    policy: PanchaPakshiLocalSolarContextPolicy,
) -> PanchaPakshiLocalSolarContextPolicyResponse:
    return PanchaPakshiLocalSolarContextPolicyResponse(
        policy_id=policy.policy_id,
        paksha_basis=policy.paksha_basis,
        solar_day_basis=policy.solar_day_basis,
        solar_event_altitude_deg=policy.solar_event_altitude_deg,
        observer_elevation_m=policy.observer_elevation_m,
        solar_altitude_refraction_mode=policy.solar_altitude_refraction_mode,
        half_basis=policy.half_basis,
        weekday_basis=policy.weekday_basis,
        offset_materialization_status=policy.offset_materialization_status,
    )


def serialize_local_solar_context(
    context: PanchaPakshiLocalSolarContext,
) -> PanchaPakshiLocalSolarContextResponse:
    return PanchaPakshiLocalSolarContextResponse(
        profile_id=context.profile_id,
        requested_jd_ut1=context.requested_jd_ut1,
        latitude=context.latitude,
        longitude=context.longitude,
        sunrise_jd_ut1=context.sunrise_jd_ut1,
        sunset_jd_ut1=context.sunset_jd_ut1,
        next_sunrise_jd_ut1=context.next_sunrise_jd_ut1,
        paksha=context.paksha,
        half=context.half,
        weekday=context.weekday,
        policy=serialize_local_solar_context_policy(context.policy),
        nominal_schedule=serialize_nominal_schedule(context.nominal_schedule),
        provenance=serialize_provenance(context.provenance),
    )


def serialize_fixed_clock_materialization_policy(
    policy: PanchaPakshiFixedClockMaterializationPolicy,
) -> PanchaPakshiFixedClockMaterializationPolicyResponse:
    return PanchaPakshiFixedClockMaterializationPolicyResponse(
        policy_id=policy.policy_id,
        paksha_basis=policy.paksha_basis,
        solar_context_basis=policy.solar_context_basis,
        day_anchor=policy.day_anchor,
        night_anchor=policy.night_anchor,
        nazhigai_seconds=policy.nazhigai_seconds,
        half_span_nazhigai=policy.half_span_nazhigai,
        half_span_seconds=policy.half_span_seconds,
        offset_arithmetic_time_scale=policy.offset_arithmetic_time_scale,
        published_endpoint_time_scale=policy.published_endpoint_time_scale,
        interval_ownership=policy.interval_ownership,
        solar_end_clipping=policy.solar_end_clipping,
        topology_metric=policy.topology_metric,
        topology_coalescence_seconds=policy.topology_coalescence_seconds,
        current_cell_status=policy.current_cell_status,
        solar_proportional_scaling_status=policy.solar_proportional_scaling_status,
    )


def serialize_fixed_clock_cell(
    cell: PanchaPakshiFixedClockCell,
) -> PanchaPakshiFixedClockCellResponse:
    return PanchaPakshiFixedClockCellResponse(
        schedule_cell_index=cell.schedule_cell_index,
        nominal_cell=serialize_schedule_cell(cell.nominal_cell),
        start_jd_tt=cell.start_jd_tt,
        end_jd_tt=cell.end_jd_tt,
        start_jd_ut1=cell.start_jd_ut1,
        end_jd_ut1=cell.end_jd_ut1,
        duration_seconds=serialize_fraction(cell.duration_seconds),
        solar_half_relation=cell.solar_half_relation,
    )


def serialize_fixed_clock_materialization(
    materialization: PanchaPakshiFixedClockMaterialization,
) -> PanchaPakshiFixedClockMaterializationResponse:
    return PanchaPakshiFixedClockMaterializationResponse(
        local_solar_context=serialize_local_solar_context(materialization.context),
        policy=serialize_fixed_clock_materialization_policy(materialization.policy),
        anchor_jd_tt=materialization.anchor_jd_tt,
        anchor_jd_ut1=materialization.anchor_jd_ut1,
        governing_solar_half_end_jd_tt=(
            materialization.governing_solar_half_end_jd_tt
        ),
        governing_solar_half_end_jd_ut1=(
            materialization.governing_solar_half_end_jd_ut1
        ),
        fixed_end_jd_tt=materialization.fixed_end_jd_tt,
        fixed_end_jd_ut1=materialization.fixed_end_jd_ut1,
        signed_fixed_end_minus_solar_end_seconds_tt=(
            materialization.signed_fixed_end_minus_solar_end_seconds_tt
        ),
        solar_boundary_relation=materialization.solar_boundary_relation,
        cells=[
            serialize_fixed_clock_cell(cell) for cell in materialization.cells
        ],
        provenance=serialize_provenance(materialization.provenance),
    )


def serialize_fixed_clock_current_cell_selection_policy(
    policy: PanchaPakshiFixedClockCurrentCellSelectionPolicy,
) -> PanchaPakshiFixedClockCurrentCellSelectionPolicyResponse:
    return PanchaPakshiFixedClockCurrentCellSelectionPolicyResponse(
        policy_id=policy.policy_id,
        materialization_policy_id=policy.materialization_policy_id,
        paksha_basis=policy.paksha_basis,
        selection_time_scale=policy.selection_time_scale,
        interval_ownership=policy.interval_ownership,
        solar_half_precedence=policy.solar_half_precedence,
        membership_tolerance_seconds=policy.membership_tolerance_seconds,
        unmaterialized_solar_half_tail=policy.unmaterialized_solar_half_tail,
        solar_end_clipping=policy.solar_end_clipping,
        fixed_span_wrap=policy.fixed_span_wrap,
        fixed_span_repeat=policy.fixed_span_repeat,
        solar_proportional_scaling_status=(
            policy.solar_proportional_scaling_status
        ),
        astronomical_paksha_inference_status=(
            policy.astronomical_paksha_inference_status
        ),
    )


def serialize_fixed_clock_current_cell(
    selection: PanchaPakshiFixedClockCurrentCellSelection,
) -> PanchaPakshiFixedClockCurrentCellResponse:
    materialization = selection.materialization
    context = materialization.context
    return PanchaPakshiFixedClockCurrentCellResponse(
        profile_id=context.profile_id,
        requested_jd_ut1=context.requested_jd_ut1,
        requested_jd_tt=selection.requested_jd_tt,
        latitude=context.latitude,
        longitude=context.longitude,
        paksha=context.paksha,
        half=context.half,
        weekday=context.weekday,
        policy=serialize_fixed_clock_current_cell_selection_policy(
            selection.policy
        ),
        anchor_jd_tt=materialization.anchor_jd_tt,
        anchor_jd_ut1=materialization.anchor_jd_ut1,
        governing_solar_half_end_jd_tt=(
            materialization.governing_solar_half_end_jd_tt
        ),
        governing_solar_half_end_jd_ut1=(
            materialization.governing_solar_half_end_jd_ut1
        ),
        fixed_end_jd_tt=materialization.fixed_end_jd_tt,
        fixed_end_jd_ut1=materialization.fixed_end_jd_ut1,
        signed_fixed_end_minus_solar_end_seconds_tt=(
            materialization.signed_fixed_end_minus_solar_end_seconds_tt
        ),
        solar_boundary_relation=materialization.solar_boundary_relation,
        selection_status=selection.selection_status,
        current_cell=(
            None
            if selection.current_cell is None
            else serialize_fixed_clock_cell(selection.current_cell)
        ),
        provenance=serialize_provenance(selection.provenance),
    )
