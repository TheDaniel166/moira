"""Lossless typed serializer for Mundane event-chart profile evidence."""

from __future__ import annotations

from moira.mundane import (
    CardinalIngressReceipt,
    CardinalIngressSelectionEvidence,
    CardinalIngressSelectionReceipt,
    EclipseContactEpochReceipt,
    EclipseEventReceipt,
    EclipseNamedEpochReceipt,
    JupiterSaturnConjunctionReceipt,
    JupiterSaturnConjunctionSequenceReceipt,
    MundaneAngularRootToleranceReceipt,
    MundaneEpoch,
    MundaneEventChartProfile,
    MundaneEventClockReceipt,
    MundaneEventEvidence,
    MundaneEventProvenance,
    MundaneLocalProjectionEvidence,
    MundaneLocalProjectionReceipt,
    MundaneLocationSelectionReceipt,
    MundaneNotEvaluable,
    MundaneRootSearchReceipt,
    MundaneSearchInterval,
    PrecedingSyzygyEvidence,
    PrecedingSyzygySelectionReceipt,
    PrimarySyzygyReceipt,
    RameseyIngressCadenceReceipt,
)

from ..models.chart import HousePolicyResponse
from ..models.mundane import (
    CardinalIngressProfileRequest,
    CardinalIngressReceiptResponse,
    CardinalIngressSelectionContextResponse,
    CardinalIngressSelectionEvidenceResponse,
    CardinalIngressSelectionReceiptResponse,
    EclipseContactEpochResponse,
    EclipseEventReceiptResponse,
    EclipseNamedEpochResponse,
    EclipseProfileRequest,
    EclipseSelectionContextResponse,
    JupiterSaturnConjunctionReceiptResponse,
    JupiterSaturnProfileRequest,
    JupiterSaturnSelectionContextResponse,
    JupiterSaturnSequenceResponse,
    MundaneAngularRootToleranceResponse,
    MundaneAscendantResponse,
    MundaneEpochResponse,
    MundaneEventChartProfileResponse,
    MundaneEventClockResponse,
    MundaneEventEvidenceResponse,
    MundaneEventProvenanceResponse,
    MundaneHouseComputationResponse,
    MundaneLocalProjectionEvidenceResponse,
    MundaneLocalProjectionReceiptResponse,
    MundaneLocationResponse,
    MundaneNotEvaluableResponse,
    MundaneProfileProvenanceResponse,
    MundaneProfileResponse,
    MundaneRootSearchResponse,
    MundaneSearchIntervalResponse,
    PrecedingSyzygyEvidenceResponse,
    PrecedingSyzygySelectionReceiptResponse,
    PrimarySyzygyProfileRequest,
    PrimarySyzygyReceiptResponse,
    PrimarySyzygySelectionContextResponse,
    RameseyIngressCadenceResponse,
    VerifiedReaderIdentityResponse,
)
from ..services.mundane import MundaneEventChartProfileComputation
from .chart import serialize_houses


def _reader_identity(identity) -> VerifiedReaderIdentityResponse:
    return VerifiedReaderIdentityResponse(
        summary_label=identity.summary_label,
        planetary_ephemeris=identity.planetary_ephemeris,
        lunar_ephemeris=identity.lunar_ephemeris,
        verification_basis=identity.verification_basis,
    )


def _epoch(epoch: MundaneEpoch) -> MundaneEpochResponse:
    return MundaneEpochResponse(jd=epoch.jd, timescale=epoch.timescale)


def _interval(interval: MundaneSearchInterval) -> MundaneSearchIntervalResponse:
    return MundaneSearchIntervalResponse(
        start=_epoch(interval.start),
        end=_epoch(interval.end),
    )


def _root_search(receipt: MundaneRootSearchReceipt | None) -> MundaneRootSearchResponse | None:
    if receipt is None:
        return None
    return MundaneRootSearchResponse(
        search_interval=_interval(receipt.search_interval),
        bracket_start=_epoch(receipt.bracket_start),
        bracket_end=_epoch(receipt.bracket_end),
        root_epoch=_epoch(receipt.root_epoch),
        step_days=receipt.step_days,
        solver_tolerance_days=receipt.solver_tolerance_days,
        target_angle_deg=receipt.target_angle_deg,
        root_residual_deg=receipt.root_residual_deg,
        bracket_start_residual_deg=receipt.bracket_start_residual_deg,
        bracket_end_residual_deg=receipt.bracket_end_residual_deg,
        search_kind=receipt.search_kind,
        solver_method_id=receipt.solver_method_id,
        verified_reader_identity=_reader_identity(receipt.verified_reader_identity),
    )


def _clock(receipt: MundaneEventClockReceipt | None) -> MundaneEventClockResponse | None:
    if receipt is None:
        return None
    return MundaneEventClockResponse(
        ut1=_epoch(receipt.ut1),
        tt=_epoch(receipt.tt),
        delta_t_seconds=receipt.delta_t_seconds,
        delta_t_source_product=receipt.delta_t_source_product,
        delta_t_retarget_mode=receipt.delta_t_retarget_mode,
        delta_t_correction_seconds=receipt.delta_t_correction_seconds,
        delta_t_tidal_source_products=receipt.delta_t_tidal_source_products,
        delta_t_target_reader_identity=receipt.delta_t_target_reader_identity,
        utc=_epoch(receipt.utc) if receipt.utc is not None else None,
        utc_realization_status=receipt.utc_realization_status,
        utc_realization_detail=receipt.utc_realization_detail,
        verified_reader_identity=_reader_identity(receipt.verified_reader_identity),
    )


def _tolerance(
    receipt: MundaneAngularRootToleranceReceipt,
) -> MundaneAngularRootToleranceResponse:
    return MundaneAngularRootToleranceResponse(
        maximum_abs_residual_deg=receipt.maximum_abs_residual_deg,
        basis=receipt.basis,
    )


def _provenance(receipt: MundaneEventProvenance) -> MundaneEventProvenanceResponse:
    return MundaneEventProvenanceResponse(
        mode=receipt.mode,
        source_id=receipt.source_id,
        method_id=receipt.method_id,
        provenance_family_id=receipt.provenance_family_id,
        longitude_product_id=receipt.longitude_product_id,
        reference_frame=receipt.reference_frame,
        correction_regime=receipt.correction_regime,
        solver_semantics=receipt.solver_semantics,
        source_refs=receipt.source_refs,
        verified_reader_identity=(
            _reader_identity(receipt.verified_reader_identity)
            if receipt.verified_reader_identity is not None
            else None
        ),
        caller_asserted_artifact_id=receipt.caller_asserted_artifact_id,
        caller_asserted_artifact_sha256=receipt.caller_asserted_artifact_sha256,
    )


def _issue(issue: MundaneNotEvaluable | None) -> MundaneNotEvaluableResponse | None:
    if issue is None:
        return None
    return MundaneNotEvaluableResponse(
        component=issue.component,
        reason=issue.reason,
        missing_inputs=issue.missing_inputs,
        detail=issue.detail,
    )


def _cardinal(receipt: CardinalIngressReceipt) -> CardinalIngressReceiptResponse:
    return CardinalIngressReceiptResponse(
        event_type=receipt.event_type.value,
        ingress=receipt.ingress,
        epoch=_epoch(receipt.epoch),
        sun_longitude_deg=receipt.sun_longitude_deg,
        root_residual_deg=receipt.root_residual_deg,
        solver_tolerance_days=receipt.solver_tolerance_days,
        angular_root_tolerance=_tolerance(receipt.angular_root_tolerance),
        provenance=_provenance(receipt.provenance),
        clock=_clock(receipt.clock),
        search_truth=_root_search(receipt.search_truth),
        longitude_definition=receipt.longitude_definition,
        root_direction=receipt.root_direction,
    )


def _syzygy(receipt: PrimarySyzygyReceipt) -> PrimarySyzygyReceiptResponse:
    return PrimarySyzygyReceiptResponse(
        event_type=receipt.event_type.value,
        phase=receipt.phase,
        epoch=_epoch(receipt.epoch),
        sun_longitude_deg=receipt.sun_longitude_deg,
        moon_longitude_deg=receipt.moon_longitude_deg,
        root_residual_deg=receipt.root_residual_deg,
        solver_tolerance_days=receipt.solver_tolerance_days,
        angular_root_tolerance=_tolerance(receipt.angular_root_tolerance),
        provenance=_provenance(receipt.provenance),
        clock=_clock(receipt.clock),
        search_truth=_root_search(receipt.search_truth),
        longitude_definition=receipt.longitude_definition,
    )


def _named_epoch(receipt: EclipseNamedEpochReceipt) -> EclipseNamedEpochResponse:
    return EclipseNamedEpochResponse(
        eclipse_id=receipt.eclipse_id,
        eclipse_kind=receipt.eclipse_kind,
        epoch_kind=receipt.epoch_kind,
        epoch=_epoch(receipt.epoch),
        provenance=_provenance(receipt.provenance),
    )


def _contact(receipt: EclipseContactEpochReceipt) -> EclipseContactEpochResponse:
    return EclipseContactEpochResponse(
        eclipse_id=receipt.eclipse_id,
        eclipse_kind=receipt.eclipse_kind,
        contact=receipt.contact,
        epoch=_epoch(receipt.epoch),
        provenance=_provenance(receipt.provenance),
    )


def _eclipse(receipt: EclipseEventReceipt) -> EclipseEventReceiptResponse:
    return EclipseEventReceiptResponse(
        event_type=receipt.event_type.value,
        eclipse_id=receipt.eclipse_id,
        eclipse_kind=receipt.eclipse_kind,
        anchor_epoch_kind=receipt.anchor_epoch_kind,
        provenance=_provenance(receipt.provenance),
        named_epochs=tuple(_named_epoch(item) for item in receipt.named_epochs),
        global_contacts=tuple(_contact(item) for item in receipt.global_contacts),
        clock=_clock(receipt.clock),
    )


def _jupiter_saturn(
    receipt: JupiterSaturnConjunctionReceipt,
) -> JupiterSaturnConjunctionReceiptResponse:
    return JupiterSaturnConjunctionReceiptResponse(
        event_type=receipt.event_type.value,
        event_id=receipt.event_id,
        epoch=_epoch(receipt.epoch),
        jupiter_longitude_deg=receipt.jupiter_longitude_deg,
        saturn_longitude_deg=receipt.saturn_longitude_deg,
        root_residual_deg=receipt.root_residual_deg,
        jupiter_motion=receipt.jupiter_motion,
        saturn_motion=receipt.saturn_motion,
        solver_tolerance_days=receipt.solver_tolerance_days,
        angular_root_tolerance=_tolerance(receipt.angular_root_tolerance),
        provenance=_provenance(receipt.provenance),
        clock=_clock(receipt.clock),
        definition=receipt.definition,
        longitude_definition=receipt.longitude_definition,
    )


def _event(receipt):
    if type(receipt) is CardinalIngressReceipt:
        return _cardinal(receipt)
    if type(receipt) is PrimarySyzygyReceipt:
        return _syzygy(receipt)
    if type(receipt) is EclipseEventReceipt:
        return _eclipse(receipt)
    if type(receipt) is JupiterSaturnConjunctionReceipt:
        return _jupiter_saturn(receipt)
    raise TypeError("Unsupported typed Mundane event receipt")


def _location(receipt: MundaneLocationSelectionReceipt) -> MundaneLocationResponse:
    return MundaneLocationResponse(
        label=receipt.label,
        latitude_deg=receipt.latitude_deg,
        longitude_deg_east=receipt.longitude_deg_east,
        role=receipt.role,
        source_id=receipt.source_id,
        valid_from=_epoch(receipt.valid_from) if receipt.valid_from is not None else None,
        valid_until=_epoch(receipt.valid_until) if receipt.valid_until is not None else None,
    )


def _ramesey(receipt: RameseyIngressCadenceReceipt) -> RameseyIngressCadenceResponse:
    ascendant = receipt.ascendant
    return RameseyIngressCadenceResponse(
        aries_ingress=_cardinal(receipt.aries_ingress),
        ascendant=MundaneAscendantResponse(
            aries_ingress=_cardinal(ascendant.aries_ingress),
            location=_location(ascendant.location),
            clock=_clock(ascendant.clock),
            ascendant_longitude_deg=ascendant.ascendant_longitude_deg,
            ascendant_sign=ascendant.ascendant_sign,
            ascendant_modality=ascendant.ascendant_modality,
            local_angle_method_id=ascendant.local_angle_method_id,
        ),
        selected_ingresses=receipt.selected_ingresses,
        chart_count=receipt.chart_count,
        policy=receipt.policy,
        source_reference=receipt.source_reference,
    )


def _cardinal_selection(
    receipt: CardinalIngressSelectionReceipt,
) -> CardinalIngressSelectionReceiptResponse:
    return CardinalIngressSelectionReceiptResponse(
        policy=receipt.policy,
        search_interval=_interval(receipt.search_interval),
        all_events=tuple(_cardinal(item) for item in receipt.all_events),
        selected_events=tuple(_cardinal(item) for item in receipt.selected_events),
        source_reference=receipt.source_reference,
        ramesey_cadence=(
            _ramesey(receipt.ramesey_cadence)
            if receipt.ramesey_cadence is not None
            else None
        ),
    )


def _cardinal_evidence(
    evidence: CardinalIngressSelectionEvidence,
) -> CardinalIngressSelectionEvidenceResponse:
    return CardinalIngressSelectionEvidenceResponse(
        status=evidence.status,
        selection=(
            _cardinal_selection(evidence.selection)
            if evidence.selection is not None
            else None
        ),
        issue=_issue(evidence.issue),
    )


def _syzygy_selection(
    receipt: PrecedingSyzygySelectionReceipt,
) -> PrecedingSyzygySelectionReceiptResponse:
    return PrecedingSyzygySelectionReceiptResponse(
        anchor_event=_cardinal(receipt.anchor_event),
        candidates=tuple(_syzygy(item) for item in receipt.candidates),
        selected=_syzygy(receipt.selected),
        comparison_timescale=receipt.comparison_timescale,
        policy_id=receipt.policy_id,
    )


def _syzygy_evidence(
    evidence: PrecedingSyzygyEvidence,
) -> PrecedingSyzygyEvidenceResponse:
    return PrecedingSyzygyEvidenceResponse(
        status=evidence.status,
        selection=(
            _syzygy_selection(evidence.selection)
            if evidence.selection is not None
            else None
        ),
        issue=_issue(evidence.issue),
    )


def _event_evidence(evidence: MundaneEventEvidence) -> MundaneEventEvidenceResponse:
    return MundaneEventEvidenceResponse(
        status=evidence.status,
        receipt=_event(evidence.receipt) if evidence.receipt is not None else None,
        issue=_issue(evidence.issue),
    )


def _local_projection_receipt(
    receipt: MundaneLocalProjectionReceipt,
) -> MundaneLocalProjectionReceiptResponse:
    houses = receipt.house_computation
    return MundaneLocalProjectionReceiptResponse(
        anchor_event=_event(receipt.anchor_event),
        house_computation=MundaneHouseComputationResponse(
            event_epoch=_epoch(houses.event_epoch),
            location=_location(houses.location),
            requested_house_system=houses.requested_house_system,
            policy=HousePolicyResponse(
                unknown_system=houses.policy.unknown_system,
                polar_fallback=houses.policy.polar_fallback,
            ),
            houses=serialize_houses(houses.houses),
            calculator_id=houses.calculator_id,
        ),
        chart_epoch_kind=receipt.chart_epoch_kind,
    )


def _local_projection(
    evidence: MundaneLocalProjectionEvidence,
) -> MundaneLocalProjectionEvidenceResponse:
    return MundaneLocalProjectionEvidenceResponse(
        status=evidence.status,
        receipt=(
            _local_projection_receipt(evidence.receipt)
            if evidence.receipt is not None
            else None
        ),
        issue=_issue(evidence.issue),
    )


def _profile(profile: MundaneEventChartProfile) -> MundaneProfileResponse:
    return MundaneProfileResponse(
        status=profile.status,
        anchor_event=_event_evidence(profile.anchor_event),
        cardinal_ingress_selection=_cardinal_evidence(
            profile.cardinal_ingress_selection
        ),
        preceding_syzygy=_syzygy_evidence(profile.preceding_syzygy),
        local_projection=_local_projection(profile.local_projection),
        provenance=MundaneProfileProvenanceResponse(
            source_refs=profile.provenance.source_refs,
            engine_version=profile.provenance.engine_version,
            method_id=profile.provenance.method_id,
            derivation=profile.provenance.derivation,
        ),
        not_evaluable=tuple(_issue(item) for item in profile.not_evaluable),
        included_components=profile.included_components,
        excluded_components=profile.excluded_components,
    )


def _sequence(
    receipt: JupiterSaturnConjunctionSequenceReceipt,
) -> JupiterSaturnSequenceResponse:
    return JupiterSaturnSequenceResponse(
        search_interval=_interval(receipt.search_interval),
        roots=tuple(_jupiter_saturn(item) for item in receipt.roots),
    )


def serialize_mundane_event_chart_profile(
    computation: MundaneEventChartProfileComputation,
) -> MundaneEventChartProfileResponse:
    """Preserve full selection history beside the non-interpretive profile."""

    request = computation.request
    selection = computation.selection
    if (
        type(request) is CardinalIngressProfileRequest
        and type(selection) is CardinalIngressSelectionReceipt
    ):
        context = CardinalIngressSelectionContextResponse(
            event_type=request.event_type,
            explicit_selected_ingress=request.selected_ingress,
            selection=_cardinal_selection(selection),
        )
    elif (
        type(request) is PrimarySyzygyProfileRequest
        and type(selection) is PrecedingSyzygySelectionReceipt
    ):
        context = PrimarySyzygySelectionContextResponse(
            event_type=request.event_type,
            anchor_ingress=request.anchor_ingress,
            selection=_syzygy_selection(selection),
        )
    elif type(request) is EclipseProfileRequest and type(selection) is EclipseEventReceipt:
        context = EclipseSelectionContextResponse(
            event_type=request.event_type,
            eclipse_kind=request.eclipse_kind,
            chart_epoch_kind=request.chart_epoch_kind,
            event=_eclipse(selection),
        )
    elif (
        type(request) is JupiterSaturnProfileRequest
        and type(selection) is JupiterSaturnConjunctionSequenceReceipt
    ):
        context = JupiterSaturnSelectionContextResponse(
            event_type=request.event_type,
            selected_root_index=request.selected_root_index,
            sequence=_sequence(selection),
        )
    else:
        raise TypeError("Mundane request and event-selection receipt do not match")
    return MundaneEventChartProfileResponse(
        selection=context,
        profile=_profile(computation.profile),
    )


__all__ = ["serialize_mundane_event_chart_profile"]
