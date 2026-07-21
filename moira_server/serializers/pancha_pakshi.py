"""Serializers for first-class, source-scoped Pancha Pakshi vessels."""

from __future__ import annotations

from fractions import Fraction

from moira.pancha_pakshi import (
    PanchaPakshiAstronomicalPakshaInference,
    PanchaPakshiAstronomicalPakshaInferencePolicy,
    PanchaPakshiConflictWitness,
    PanchaPakshiDirectedRelationship,
    PanchaPakshiFixedClockCell,
    PanchaPakshiFixedClockCurrentCellSelection,
    PanchaPakshiFixedClockCurrentCellSelectionPolicy,
    PanchaPakshiFixedClockMaterialization,
    PanchaPakshiFixedClockMaterializationPolicy,
    PanchaPakshiFirstEatBirdMapping,
    PanchaPakshiInitialVowelIdentity,
    PanchaPakshiLocalSolarContext,
    PanchaPakshiLocalSolarContextPolicy,
    PanchaPakshiNakshatraBirdMapping,
    PanchaPakshiNatalMoonIdentity,
    PanchaPakshiNatalMoonIdentityPolicy,
    PanchaPakshiOmission,
    PanchaPakshiPaduBirdMapping,
    PanchaPakshiProfileDescriptor,
    PanchaPakshiProfileInfo,
    PanchaPakshiProvenance,
    PanchaPakshiSchedule,
    PanchaPakshiScheduleCell,
    PanchaPakshiSolarProportionalCell,
    PanchaPakshiSolarProportionalCurrentCellSelection,
    PanchaPakshiSolarProportionalCurrentCellSelectionPolicy,
    PanchaPakshiSolarProportionalMaterialization,
    PanchaPakshiSolarProportionalMaterializationPolicy,
    PanchaPakshiSource,
    PanchaPakshiSourceLocator,
    PanchaPakshiScheduleSookshmaCompositionPolicy,
    PanchaPakshiScheduleSookshmaSelection,
    PanchaPakshiSookshmaInterval,
    PanchaPakshiSookshmaSelection,
    PanchaPakshiSookshmaSelectorPolicy,
)

from ..models.pancha_pakshi import (
    PanchaPakshiAksaraIdentityResponse,
    PanchaPakshiAstronomicalPakshaInferencePolicyResponse,
    PanchaPakshiAstronomicalPakshaResponse,
    PanchaPakshiConflictWitnessResponse,
    PanchaPakshiDirectedRelationshipResponse,
    PanchaPakshiFixedClockCellResponse,
    PanchaPakshiFixedClockCurrentCellResponse,
    PanchaPakshiFixedClockCurrentCellSelectionPolicyResponse,
    PanchaPakshiFixedClockMaterializationPolicyResponse,
    PanchaPakshiFixedClockMaterializationResponse,
    PanchaPakshiFirstEatBirdMappingResponse,
    PanchaPakshiFractionResponse,
    PanchaPakshiLocalSolarContextPolicyResponse,
    PanchaPakshiLocalSolarContextResponse,
    PanchaPakshiNakshatraBirdMappingResponse,
    PanchaPakshiNatalMoonIdentityPolicyResponse,
    PanchaPakshiNatalMoonIdentityResponse,
    PanchaPakshiNominalScheduleResponse,
    PanchaPakshiOmissionResponse,
    PanchaPakshiPaduBirdMappingResponse,
    PanchaPakshiProfileDescriptorResponse,
    PanchaPakshiProfileInfoResponse,
    PanchaPakshiProvenanceResponse,
    PanchaPakshiScheduleCellResponse,
    PanchaPakshiScheduleSookshmaCompositionPolicyResponse,
    PanchaPakshiScheduleSookshmaSelectionResponse,
    PanchaPakshiSolarProportionalCellResponse,
    PanchaPakshiSolarProportionalCurrentCellResponse,
    PanchaPakshiSolarProportionalCurrentCellSelectionPolicyResponse,
    PanchaPakshiSolarProportionalMaterializationPolicyResponse,
    PanchaPakshiSolarProportionalMaterializationResponse,
    PanchaPakshiSourceLocatorResponse,
    PanchaPakshiSourceResponse,
    PanchaPakshiSookshmaActivityDurationResponse,
    PanchaPakshiSookshmaIntervalResponse,
    PanchaPakshiSookshmaSelectionResponse,
    PanchaPakshiSookshmaSelectorPolicyResponse,
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


def serialize_astronomical_paksha_policy(
    policy: PanchaPakshiAstronomicalPakshaInferencePolicy,
) -> PanchaPakshiAstronomicalPakshaInferencePolicyResponse:
    return PanchaPakshiAstronomicalPakshaInferencePolicyResponse(
        policy_id=policy.policy_id,
        input_time_scale=policy.input_time_scale,
        ephemeris_time_scale=policy.ephemeris_time_scale,
        position_origin=policy.position_origin,
        position_frame=policy.position_frame,
        apparent=policy.apparent,
        aberration=policy.aberration,
        grav_deflection=policy.grav_deflection,
        nutation=policy.nutation,
        elongation_definition=policy.elongation_definition,
        elongation_domain=policy.elongation_domain,
        shukla_interval=policy.shukla_interval,
        krishna_interval=policy.krishna_interval,
        boundary_tolerance_degrees=policy.boundary_tolerance_degrees,
        ayanamsa_status=policy.ayanamsa_status,
        profile_mapping_basis=policy.profile_mapping_basis,
        purva_source_locator_id=policy.purva_source_locator_id,
        amara_source_locator_id=policy.amara_source_locator_id,
        schedule_selection_status=policy.schedule_selection_status,
        materialization_status=policy.materialization_status,
        natal_identity_status=policy.natal_identity_status,
    )


def serialize_astronomical_paksha(
    inference: PanchaPakshiAstronomicalPakshaInference,
) -> PanchaPakshiAstronomicalPakshaResponse:
    return PanchaPakshiAstronomicalPakshaResponse(
        profile_id=inference.profile_id,
        requested_jd_ut1=inference.requested_jd_ut1,
        requested_jd_tt=inference.requested_jd_tt,
        policy=serialize_astronomical_paksha_policy(inference.policy),
        sun_longitude_deg=inference.sun_longitude_deg,
        moon_longitude_deg=inference.moon_longitude_deg,
        moon_minus_sun_elongation_deg=(
            inference.moon_minus_sun_elongation_deg
        ),
        astronomical_paksha=inference.astronomical_paksha,
        profile_paksha=inference.profile_paksha,
        mapping_status=inference.mapping_status,
        mapping_source_locators=[
            serialize_source_locator(locator)
            for locator in inference.mapping_source_locators
        ],
        provenance=serialize_provenance(inference.provenance),
    )


def serialize_nakshatra_bird_mapping(
    mapping: PanchaPakshiNakshatraBirdMapping,
) -> PanchaPakshiNakshatraBirdMappingResponse:
    return PanchaPakshiNakshatraBirdMappingResponse(
        profile_id=mapping.profile_id,
        profile_paksha=mapping.profile_paksha,
        nakshatra_index=mapping.nakshatra_index,
        nakshatra=mapping.nakshatra,
        bird=mapping.bird,
        mapping_status=mapping.mapping_status,
        source_table_semantics=mapping.source_table_semantics,
        assembly_policy=mapping.assembly_policy,
        source_locators=[
            serialize_source_locator(locator) for locator in mapping.source_locators
        ],
        provenance=serialize_provenance(mapping.provenance),
    )


def serialize_padu_bird_mapping(
    mapping: PanchaPakshiPaduBirdMapping,
) -> PanchaPakshiPaduBirdMappingResponse:
    """Serialize one pure source-table Padu lookup without temporal fields."""

    return PanchaPakshiPaduBirdMappingResponse(
        profile_id=mapping.profile_id,
        profile_paksha=mapping.profile_paksha,
        weekday=mapping.weekday,
        bird=mapping.bird,
        mapping_status=mapping.mapping_status,
        source_table_semantics=mapping.source_table_semantics,
        assembly_policy=mapping.assembly_policy,
        source_locators=[
            serialize_source_locator(locator) for locator in mapping.source_locators
        ],
        provenance=serialize_provenance(mapping.provenance),
    )


def serialize_sookshma_selector_policy(
    policy: PanchaPakshiSookshmaSelectorPolicy,
) -> PanchaPakshiSookshmaSelectorPolicyResponse:
    return PanchaPakshiSookshmaSelectorPolicyResponse(
        policy_id=policy.policy_id.value,
        source_layer=policy.source_layer,
        partition_kind=policy.partition_kind,
        container_span_nazhigai=serialize_fraction(
            policy.container_span_nazhigai
        ),
        interval_count=policy.interval_count,
        interval_ownership=policy.interval_ownership,
        sequence_policy=policy.sequence_policy,
        activity_assignment_status=policy.activity_assignment_status,
        activity_durations_nazhigai=[
            PanchaPakshiSookshmaActivityDurationResponse(
                activity=activity,
                duration_nazhigai=serialize_fraction(duration),
            )
            for activity, duration in policy.activity_durations_nazhigai
        ],
        automatic_policy_selection=policy.automatic_policy_selection,
        uromarisi_composition_status=policy.uromarisi_composition_status,
        outcome_interpretation_status=policy.outcome_interpretation_status,
        source_locator_ids=list(policy.source_locator_ids),
    )


def serialize_sookshma_interval(
    interval: PanchaPakshiSookshmaInterval,
) -> PanchaPakshiSookshmaIntervalResponse:
    return PanchaPakshiSookshmaIntervalResponse(
        ordinal=interval.ordinal,
        activity=interval.activity,
        start_nazhigai=serialize_fraction(interval.start_nazhigai),
        end_nazhigai=serialize_fraction(interval.end_nazhigai),
        duration_nazhigai=serialize_fraction(interval.duration_nazhigai),
    )


def serialize_sookshma_temporal_selection(
    selection: PanchaPakshiSookshmaSelection,
) -> PanchaPakshiSookshmaSelectionResponse:
    return PanchaPakshiSookshmaSelectionResponse(
        profile_id=selection.profile_id,
        parent_activity=selection.parent_activity,
        elapsed_nazhigai=serialize_fraction(selection.elapsed_nazhigai),
        policy=serialize_sookshma_selector_policy(selection.policy),
        intervals=[
            serialize_sookshma_interval(interval)
            for interval in selection.intervals
        ],
        selected_ordinal=selection.selected_ordinal,
        selected_interval=serialize_sookshma_interval(
            selection.selected_interval
        ),
        source_locators=[
            serialize_source_locator(locator)
            for locator in selection.source_locators
        ],
        provenance=serialize_provenance(selection.provenance),
    )


def serialize_schedule_sookshma_composition_policy(
    policy: PanchaPakshiScheduleSookshmaCompositionPolicy,
) -> PanchaPakshiScheduleSookshmaCompositionPolicyResponse:
    return PanchaPakshiScheduleSookshmaCompositionPolicyResponse(
        policy_id=policy.policy_id,
        composition_status=policy.composition_status,
        schedule_selection_basis=policy.schedule_selection_basis,
        parent_activity_basis=policy.parent_activity_basis,
        selector_policy_basis=policy.selector_policy_basis,
        elapsed_offset_basis=policy.elapsed_offset_basis,
        clock_or_civil_time_routing_status=(
            policy.clock_or_civil_time_routing_status
        ),
        uromarisi_outcome_binding_status=(
            policy.uromarisi_outcome_binding_status
        ),
        outcome_interpretation_status=policy.outcome_interpretation_status,
    )


def serialize_schedule_sookshma_temporal_selection(
    selection: PanchaPakshiScheduleSookshmaSelection,
) -> PanchaPakshiScheduleSookshmaSelectionResponse:
    return PanchaPakshiScheduleSookshmaSelectionResponse(
        schedule_profile_id=selection.schedule_profile_id,
        selector_profile_id=selection.selector_profile_id,
        schedule=serialize_nominal_schedule(selection.schedule),
        samam_index=selection.samam_index,
        subject_bird=selection.subject_bird,
        parent_schedule_cell=serialize_schedule_cell(
            selection.parent_schedule_cell
        ),
        elapsed_nazhigai=serialize_fraction(selection.elapsed_nazhigai),
        composition_policy=serialize_schedule_sookshma_composition_policy(
            selection.composition_policy
        ),
        sookshma_selection=serialize_sookshma_temporal_selection(
            selection.sookshma_selection
        ),
    )


def serialize_first_eat_bird_mapping(
    mapping: PanchaPakshiFirstEatBirdMapping,
) -> PanchaPakshiFirstEatBirdMappingResponse:
    """Serialize one source-generator Eat seed without temporal inference."""

    return PanchaPakshiFirstEatBirdMappingResponse(
        profile_id=mapping.profile_id,
        generator_id=mapping.generator_id,
        profile_paksha=mapping.profile_paksha,
        half=mapping.half,
        weekday=mapping.weekday,
        first_eat_bird=mapping.first_eat_bird,
        mapping_status=mapping.mapping_status,
        source_table_semantics=mapping.source_table_semantics,
        source_locators=[
            serialize_source_locator(locator) for locator in mapping.source_locators
        ],
        provenance=serialize_provenance(mapping.provenance),
    )


def serialize_natal_moon_identity_policy(
    policy: PanchaPakshiNatalMoonIdentityPolicy,
) -> PanchaPakshiNatalMoonIdentityPolicyResponse:
    return PanchaPakshiNatalMoonIdentityPolicyResponse(
        policy_id=policy.policy_id,
        composition_status=policy.composition_status,
        source_table_semantics=policy.source_table_semantics,
        input_time_scale=policy.input_time_scale,
        ephemeris_time_scale=policy.ephemeris_time_scale,
        position_origin=policy.position_origin,
        position_frame=policy.position_frame,
        apparent=policy.apparent,
        aberration=policy.aberration,
        grav_deflection=policy.grav_deflection,
        nutation=policy.nutation,
        elongation_definition=policy.elongation_definition,
        shukla_interval=policy.shukla_interval,
        krishna_interval=policy.krishna_interval,
        phase_boundary_tolerance_degrees=(
            policy.phase_boundary_tolerance_degrees
        ),
        phase_to_profile_mapping=policy.phase_to_profile_mapping,
        phase_mapping_source_locator_id=(
            policy.phase_mapping_source_locator_id
        ),
        ayanamsa_system=policy.ayanamsa_system,
        ayanamsa_mode=policy.ayanamsa_mode,
        ayanamsa_status=policy.ayanamsa_status,
        nakshatra_partition=policy.nakshatra_partition,
        exact_internal_boundary_ownership=(
            policy.exact_internal_boundary_ownership
        ),
        binary_boundary_recovery=policy.binary_boundary_recovery,
        mapping_assembly_policy=policy.mapping_assembly_policy,
        schedule_selection_status=policy.schedule_selection_status,
        materialization_status=policy.materialization_status,
        current_cell_status=policy.current_cell_status,
        scoring_status=policy.scoring_status,
        forecast_status=policy.forecast_status,
    )


def serialize_natal_moon_identity(
    identity: PanchaPakshiNatalMoonIdentity,
) -> PanchaPakshiNatalMoonIdentityResponse:
    return PanchaPakshiNatalMoonIdentityResponse(
        profile_id=identity.profile_id,
        requested_jd_ut1=identity.requested_jd_ut1,
        requested_jd_tt=identity.requested_jd_tt,
        policy=serialize_natal_moon_identity_policy(identity.policy),
        sun_longitude_deg=identity.sun_longitude_deg,
        moon_tropical_longitude_deg=identity.moon_tropical_longitude_deg,
        moon_minus_sun_elongation_deg=(
            identity.moon_minus_sun_elongation_deg
        ),
        astronomical_paksha=identity.astronomical_paksha,
        profile_paksha=identity.profile_paksha,
        phase_mapping_source_locators=[
            serialize_source_locator(locator)
            for locator in identity.phase_mapping_source_locators
        ],
        ayanamsa_deg=identity.ayanamsa_deg,
        moon_sidereal_longitude_deg=identity.moon_sidereal_longitude_deg,
        nakshatra_index=identity.nakshatra_index,
        nakshatra=identity.nakshatra,
        degrees_in_nakshatra=identity.degrees_in_nakshatra,
        bird=identity.bird,
        bird_mapping=serialize_nakshatra_bird_mapping(identity.bird_mapping),
        provenance=serialize_provenance(identity.provenance),
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


def serialize_solar_proportional_materialization_policy(
    policy: PanchaPakshiSolarProportionalMaterializationPolicy,
) -> PanchaPakshiSolarProportionalMaterializationPolicyResponse:
    return PanchaPakshiSolarProportionalMaterializationPolicyResponse(
        policy_id=policy.policy_id,
        paksha_basis=policy.paksha_basis,
        solar_context_basis=policy.solar_context_basis,
        day_anchor=policy.day_anchor,
        night_anchor=policy.night_anchor,
        nominal_offset_basis=policy.nominal_offset_basis,
        mapping_time_scale=policy.mapping_time_scale,
        published_endpoint_time_scale=policy.published_endpoint_time_scale,
        endpoint_mapping=policy.endpoint_mapping,
        endpoint_closure=policy.endpoint_closure,
        interval_ownership=policy.interval_ownership,
        solar_end_clipping=policy.solar_end_clipping,
        solar_half_wrap=policy.solar_half_wrap,
        solar_half_repeat=policy.solar_half_repeat,
        fixed_nazhigai_seconds_status=policy.fixed_nazhigai_seconds_status,
        current_cell_status=policy.current_cell_status,
        astronomical_paksha_inference_status=(
            policy.astronomical_paksha_inference_status
        ),
    )


def serialize_solar_proportional_cell(
    cell: PanchaPakshiSolarProportionalCell,
) -> PanchaPakshiSolarProportionalCellResponse:
    return PanchaPakshiSolarProportionalCellResponse(
        schedule_cell_index=cell.schedule_cell_index,
        nominal_cell=serialize_schedule_cell(cell.nominal_cell),
        start_offset_fraction=serialize_fraction(cell.start_offset_fraction),
        end_offset_fraction=serialize_fraction(cell.end_offset_fraction),
        span_fraction=serialize_fraction(cell.span_fraction),
        start_jd_tt=cell.start_jd_tt,
        end_jd_tt=cell.end_jd_tt,
        start_jd_ut1=cell.start_jd_ut1,
        end_jd_ut1=cell.end_jd_ut1,
        duration_seconds_tt=cell.duration_seconds_tt,
    )


def serialize_solar_proportional_materialization(
    materialization: PanchaPakshiSolarProportionalMaterialization,
) -> PanchaPakshiSolarProportionalMaterializationResponse:
    return PanchaPakshiSolarProportionalMaterializationResponse(
        local_solar_context=serialize_local_solar_context(
            materialization.context
        ),
        policy=serialize_solar_proportional_materialization_policy(
            materialization.policy
        ),
        anchor_jd_tt=materialization.anchor_jd_tt,
        anchor_jd_ut1=materialization.anchor_jd_ut1,
        governing_solar_half_end_jd_tt=(
            materialization.governing_solar_half_end_jd_tt
        ),
        governing_solar_half_end_jd_ut1=(
            materialization.governing_solar_half_end_jd_ut1
        ),
        solar_half_duration_seconds_tt=(
            materialization.solar_half_duration_seconds_tt
        ),
        cells=[
            serialize_solar_proportional_cell(cell)
            for cell in materialization.cells
        ],
        provenance=serialize_provenance(materialization.provenance),
    )


def serialize_solar_proportional_current_cell_selection_policy(
    policy: PanchaPakshiSolarProportionalCurrentCellSelectionPolicy,
) -> PanchaPakshiSolarProportionalCurrentCellSelectionPolicyResponse:
    return PanchaPakshiSolarProportionalCurrentCellSelectionPolicyResponse(
        policy_id=policy.policy_id,
        materialization_policy_id=policy.materialization_policy_id,
        paksha_basis=policy.paksha_basis,
        selection_time_scale=policy.selection_time_scale,
        interval_ownership=policy.interval_ownership,
        solar_half_precedence=policy.solar_half_precedence,
        membership_tolerance_seconds=policy.membership_tolerance_seconds,
        coverage_requirement=policy.coverage_requirement,
        required_match_count=policy.required_match_count,
        unmaterialized_solar_half_tail_status=(
            policy.unmaterialized_solar_half_tail_status
        ),
        invalid_match_policy=policy.invalid_match_policy,
        fixed_clock_mixing_status=policy.fixed_clock_mixing_status,
        astronomical_paksha_inference_status=(
            policy.astronomical_paksha_inference_status
        ),
    )


def serialize_solar_proportional_current_cell(
    selection: PanchaPakshiSolarProportionalCurrentCellSelection,
) -> PanchaPakshiSolarProportionalCurrentCellResponse:
    materialization = selection.materialization
    context = materialization.context
    return PanchaPakshiSolarProportionalCurrentCellResponse(
        profile_id=context.profile_id,
        requested_jd_ut1=context.requested_jd_ut1,
        requested_jd_tt=selection.requested_jd_tt,
        latitude=context.latitude,
        longitude=context.longitude,
        paksha=context.paksha,
        half=context.half,
        weekday=context.weekday,
        policy=serialize_solar_proportional_current_cell_selection_policy(
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
        solar_half_duration_seconds_tt=(
            materialization.solar_half_duration_seconds_tt
        ),
        selection_status=selection.selection_status,
        current_cell=serialize_solar_proportional_cell(selection.current_cell),
        provenance=serialize_provenance(selection.provenance),
    )
