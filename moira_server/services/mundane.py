"""Transport orchestration for the neutral Mundane event-chart profile."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from moira import Moira
from moira.constants import Body
from moira.cycles import great_conjunctions
from moira.eclipse import EclipseCalculator
from moira.julian import jd_from_datetime, utc_to_ut1
from moira.mundane import (
    CardinalIngress,
    CardinalIngressReceipt,
    CardinalIngressSelectionEvidence,
    CardinalIngressSelectionReceipt,
    CardinalIngressSelectionPolicy,
    EclipseEventReceipt,
    JupiterSaturnConjunctionSequenceReceipt,
    MundaneEpoch,
    MundaneEvaluationStatus,
    MundaneEventChartProfile,
    MundaneEventEvidence,
    MundaneLocationSelectionReceipt,
    MundaneNotEvaluable,
    MundaneNotEvaluableReason,
    MundaneProfileComponent,
    MundaneSearchInterval,
    MundaneTimescale,
    PrecedingSyzygyEvidence,
    PrecedingSyzygySelectionReceipt,
    assess_ramesey_ingress_cadence,
    build_mundane_local_projection,
    compose_mundane_event_chart_profile,
    select_cardinal_ingresses,
)

from ..models.mundane import (
    CardinalIngressProfileRequest,
    EclipseProfileRequest,
    JupiterSaturnProfileRequest,
    MundaneEventChartProfileRequest,
    MundaneEventProfileRequest,
    MundaneLocationRequest,
    PrimarySyzygyProfileRequest,
)


MundaneSelectionReceipt = (
    CardinalIngressSelectionReceipt
    | PrecedingSyzygySelectionReceipt
    | EclipseEventReceipt
    | JupiterSaturnConjunctionSequenceReceipt
)


@dataclass(frozen=True, slots=True)
class MundaneEventChartProfileComputation:
    """Engine profile plus the complete explicit event-selection context."""

    request: MundaneEventProfileRequest
    selection: MundaneSelectionReceipt
    profile: MundaneEventChartProfile


def _to_jd_ut1(value: datetime) -> float:
    return utc_to_ut1(jd_from_datetime(value.astimezone(timezone.utc)))


def _location_receipt(request: MundaneLocationRequest) -> MundaneLocationSelectionReceipt:
    valid_from = (
        MundaneEpoch(_to_jd_ut1(request.valid_from_utc), MundaneTimescale.UT1)
        if request.valid_from_utc is not None
        else None
    )
    valid_until = (
        MundaneEpoch(_to_jd_ut1(request.valid_until_utc), MundaneTimescale.UT1)
        if request.valid_until_utc is not None
        else None
    )
    return MundaneLocationSelectionReceipt(
        label=request.label,
        latitude_deg=request.latitude_deg,
        longitude_deg_east=request.longitude_deg_east,
        role=request.role,
        source_id=request.source_id,
        valid_from=valid_from,
        valid_until=valid_until,
    )


def _search_interval(request: MundaneEventProfileRequest) -> MundaneSearchInterval:
    return MundaneSearchInterval(
        start=MundaneEpoch(_to_jd_ut1(request.search_start_utc), MundaneTimescale.UT1),
        end=MundaneEpoch(_to_jd_ut1(request.search_end_utc), MundaneTimescale.UT1),
    )


def _not_applicable_cardinal_selection(event_type: str) -> CardinalIngressSelectionEvidence:
    return CardinalIngressSelectionEvidence(
        status=MundaneEvaluationStatus.NOT_EVALUABLE,
        selection=None,
        issue=MundaneNotEvaluable(
            component=MundaneProfileComponent.CARDINAL_INGRESS_SELECTION,
            reason=MundaneNotEvaluableReason.EVENT_SEMANTICS_MISMATCH,
            missing_inputs=("cardinal_ingress_anchor",),
            detail=(
                "Cardinal-ingress selection is not applicable when the explicit "
                f"profile anchor is {event_type}."
            ),
        ),
    )


def _not_applicable_preceding_syzygy(event_type: str) -> PrecedingSyzygyEvidence:
    return PrecedingSyzygyEvidence(
        status=MundaneEvaluationStatus.NOT_EVALUABLE,
        selection=None,
        issue=MundaneNotEvaluable(
            component=MundaneProfileComponent.PRECEDING_PRIMARY_SYZYGY,
            reason=MundaneNotEvaluableReason.EVENT_SEMANTICS_MISMATCH,
            missing_inputs=("cardinal_ingress_anchor",),
            detail=(
                "A primary-syzygy predecessor is evaluated only for a cardinal "
                f"ingress anchor, not for {event_type}."
            ),
        ),
    )


def _evaluated_anchor(receipt) -> MundaneEventEvidence:
    return MundaneEventEvidence(
        status=MundaneEvaluationStatus.EVALUATED,
        receipt=receipt,
        issue=None,
    )


def _cardinal_cycle(
    engine: Moira,
    interval: MundaneSearchInterval,
) -> tuple[
    tuple[CardinalIngressReceipt, ...],
    dict[CardinalIngress, MundaneEventEvidence],
]:
    """Enumerate and reader-revalidate exactly one of each cardinal root."""

    raw_events = engine.ingresses(Body.SUN, interval.start.jd, interval.end.jd)
    cardinal_signs = {item.value.capitalize() for item in CardinalIngress}
    evidences = tuple(
        engine.assess_transit_cardinal_ingress(event)
        for event in raw_events
        if getattr(event, "sign", None) in cardinal_signs
    )
    evaluated = tuple(
        evidence
        for evidence in evidences
        if evidence.status is MundaneEvaluationStatus.EVALUATED
        and type(evidence.receipt) is CardinalIngressReceipt
    )
    by_ingress = {
        evidence.receipt.ingress: evidence
        for evidence in evaluated
        if isinstance(evidence.receipt, CardinalIngressReceipt)
    }
    if len(evaluated) != 4 or len(by_ingress) != 4 or set(by_ingress) != set(CardinalIngress):
        raise ValueError(
            "The bounded search must contain exactly one reader-validated event "
            "for each of the four cardinal ingresses"
        )
    ordered = tuple(
        by_ingress[ingress].receipt
        for ingress in CardinalIngress
    )
    if any(type(receipt) is not CardinalIngressReceipt for receipt in ordered):
        raise TypeError("Cardinal ingress assessment did not retain typed receipts")
    return ordered, by_ingress


def _compute_cardinal_ingress(
    engine: Moira,
    request: CardinalIngressProfileRequest,
    interval: MundaneSearchInterval,
    location: MundaneLocationSelectionReceipt,
) -> MundaneEventChartProfileComputation:
    events, evidences = _cardinal_cycle(engine, interval)
    cadence = None
    if (
        request.selection_policy
        is CardinalIngressSelectionPolicy.RAMESEY_1653_ASCENDANT_MODALITY_V1
    ):
        cadence_evidence = assess_ramesey_ingress_cadence(events[0], location)
        if (
            cadence_evidence.status is not MundaneEvaluationStatus.EVALUATED
            or cadence_evidence.cadence is None
        ):
            reason = (
                cadence_evidence.issue.detail
                if cadence_evidence.issue is not None
                else "Ramesey cadence was not evaluated"
            )
            raise ValueError(reason)
        cadence = cadence_evidence.cadence
    selection_evidence = select_cardinal_ingresses(
        events,
        policy=request.selection_policy,
        search_interval=interval,
        ramesey_cadence=cadence,
    )
    if selection_evidence.selection is None:
        detail = (
            selection_evidence.issue.detail
            if selection_evidence.issue is not None
            else "Cardinal ingress selection was not evaluated"
        )
        raise ValueError(detail)
    selection = selection_evidence.selection
    anchor = next(
        (item for item in selection.selected_events if item.ingress is request.selected_ingress),
        None,
    )
    if anchor is None:
        raise ValueError(
            "selected_ingress is not admitted by the explicit ingress selection policy"
        )
    preceding = engine.assess_transit_primary_syzygy(anchor)
    local_projection = build_mundane_local_projection(
        anchor,
        location,
        request.house_system,
        chart_epoch_kind=None,
    )
    profile = compose_mundane_event_chart_profile(
        anchor_event=evidences[anchor.ingress],
        cardinal_ingress_selection=selection_evidence,
        preceding_syzygy=preceding,
        local_projection=local_projection,
    )
    return MundaneEventChartProfileComputation(request, selection, profile)


def _compute_primary_syzygy(
    engine: Moira,
    request: PrimarySyzygyProfileRequest,
    interval: MundaneSearchInterval,
    location: MundaneLocationSelectionReceipt,
) -> MundaneEventChartProfileComputation:
    events, _ = _cardinal_cycle(engine, interval)
    ingress = next(item for item in events if item.ingress is request.anchor_ingress)
    preceding = engine.assess_transit_primary_syzygy(ingress)
    if preceding.selection is None:
        detail = (
            preceding.issue.detail
            if preceding.issue is not None
            else "Primary syzygy selection was not evaluated"
        )
        raise ValueError(detail)
    selection = preceding.selection
    anchor = selection.selected
    local_projection = build_mundane_local_projection(
        anchor,
        location,
        request.house_system,
        chart_epoch_kind=None,
    )
    profile = compose_mundane_event_chart_profile(
        anchor_event=_evaluated_anchor(anchor),
        cardinal_ingress_selection=_not_applicable_cardinal_selection(
            "primary_syzygy"
        ),
        preceding_syzygy=_not_applicable_preceding_syzygy("primary_syzygy"),
        local_projection=local_projection,
    )
    return MundaneEventChartProfileComputation(request, selection, profile)


def _compute_eclipse(
    engine: Moira,
    request: EclipseProfileRequest,
    interval: MundaneSearchInterval,
    location: MundaneLocationSelectionReceipt,
) -> MundaneEventChartProfileComputation:
    calculator = EclipseCalculator(reader=getattr(engine, "_reader", None))
    raw_event = (
        calculator.next_solar_eclipse(interval.start.jd)
        if request.eclipse_kind.value == "solar"
        else calculator.next_lunar_eclipse(interval.start.jd)
    )
    if not interval.start.jd <= raw_event.jd_ut < interval.end.jd:
        raise ValueError("No requested eclipse lies within the explicit search interval")
    event = engine.eclipse_receipt_from_event(raw_event, eclipse_id=request.eclipse_id)
    if event.eclipse_kind is not request.eclipse_kind:
        raise ValueError("The revalidated eclipse family does not match eclipse_kind")
    local_projection = build_mundane_local_projection(
        event,
        location,
        request.house_system,
        chart_epoch_kind=request.chart_epoch_kind,
    )
    local_eclipse_issue = MundaneNotEvaluable(
        component=MundaneProfileComponent.LOCAL_ECLIPSE_CIRCUMSTANCES,
        reason=MundaneNotEvaluableReason.LOCAL_ECLIPSE_CIRCUMSTANCES_UNAVAILABLE,
        missing_inputs=("engine_owned_local_eclipse_circumstances_receipt",),
        detail=(
            "The Mundane v1 profile retains global eclipse truth and local house "
            "projection but does not yet compose observer-local eclipse circumstances."
        ),
    )
    profile = compose_mundane_event_chart_profile(
        anchor_event=_evaluated_anchor(event),
        cardinal_ingress_selection=_not_applicable_cardinal_selection("eclipse"),
        preceding_syzygy=_not_applicable_preceding_syzygy("eclipse"),
        local_projection=local_projection,
        additional_not_evaluable=(local_eclipse_issue,),
    )
    return MundaneEventChartProfileComputation(request, event, profile)


def _compute_jupiter_saturn(
    engine: Moira,
    request: JupiterSaturnProfileRequest,
    interval: MundaneSearchInterval,
    location: MundaneLocationSelectionReceipt,
) -> MundaneEventChartProfileComputation:
    raw_series = great_conjunctions(
        interval.start.jd,
        interval.end.jd,
        reader=getattr(engine, "_reader", None),
    )
    sequence = engine.jupiter_saturn_sequence_from_series(raw_series)
    if request.selected_root_index >= len(sequence.roots):
        raise ValueError(
            "selected_root_index does not identify a root in the complete sequence"
        )
    anchor = sequence.roots[request.selected_root_index]
    local_projection = build_mundane_local_projection(
        anchor,
        location,
        request.house_system,
        chart_epoch_kind=None,
    )
    profile = compose_mundane_event_chart_profile(
        anchor_event=_evaluated_anchor(anchor),
        cardinal_ingress_selection=_not_applicable_cardinal_selection(
            "jupiter_saturn_ecliptic_longitude_conjunction"
        ),
        preceding_syzygy=_not_applicable_preceding_syzygy(
            "jupiter_saturn_ecliptic_longitude_conjunction"
        ),
        local_projection=local_projection,
    )
    return MundaneEventChartProfileComputation(request, sequence, profile)


def compute_mundane_event_chart_profile(
    engine: Moira,
    request: MundaneEventChartProfileRequest,
) -> MundaneEventChartProfileComputation:
    """Compute one explicit event family and compose only engine-owned evidence."""

    event_request = request.root
    interval = _search_interval(event_request)
    location = _location_receipt(event_request.location)
    if type(event_request) is CardinalIngressProfileRequest:
        return _compute_cardinal_ingress(engine, event_request, interval, location)
    if type(event_request) is PrimarySyzygyProfileRequest:
        return _compute_primary_syzygy(engine, event_request, interval, location)
    if type(event_request) is EclipseProfileRequest:
        return _compute_eclipse(engine, event_request, interval, location)
    if type(event_request) is JupiterSaturnProfileRequest:
        return _compute_jupiter_saturn(engine, event_request, interval, location)
    raise TypeError("Unsupported typed Mundane event request")


__all__ = [
    "MundaneEventChartProfileComputation",
    "compute_mundane_event_chart_profile",
]
