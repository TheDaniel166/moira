"""Projection services for the bounded Sothic REST surface."""

from __future__ import annotations

from moira import Moira
from moira.sothic import (
    CENSORINUS_139_ANCHOR,
    EgyptianDate,
    SothicCalendarPolicy,
    SothicComputationPolicy,
    SothicHeliacalPolicy,
    SothicEntry,
    egyptian_civil_date,
    predict_sothic_epoch,
    sothic_rising_series,
)
from moira.spk_reader import use_reader_override

from ..models.sothic import (
    MAX_SOTHIC_RANGE_YEARS,
    EgyptianDateRequest,
    EgyptianDateResponse,
    EgyptianDateValueResponse,
    SothicAnchorResponse,
    SothicEntryResponse,
    SothicHeliacalEventResponse,
    SothicPredictionRequest,
    SothicPredictionResponse,
    SothicProvenanceResponse,
    SothicRisingRequest,
    SothicRisingResponse,
    SothicYearOutcomeResponse,
)


def _anchor_response(epoch_jd: float) -> SothicAnchorResponse:
    if epoch_jd == CENSORINUS_139_ANCHOR.jd:
        anchor = CENSORINUS_139_ANCHOR
        return SothicAnchorResponse(
            anchor_id=anchor.anchor_id,
            jd=anchor.jd,
            astronomical_year=anchor.astronomical_year,
            historical_year_label=anchor.historical_year_label,
            julian_calendar_date=anchor.julian_calendar_date,
            proleptic_gregorian_date=anchor.proleptic_gregorian_date,
            year_numbering="astronomical",
            evidence_kind="primary_text_calendar_anchor",
            source_title=anchor.source_title,
            source_locator=anchor.source_locator,
            source_url=anchor.source_url,
        )
    return SothicAnchorResponse(
        anchor_id="caller_supplied_epoch_jd",
        jd=epoch_jd,
        evidence_kind="caller_supplied_calendar_anchor",
    )


def _egyptian_date_response(value: EgyptianDate) -> EgyptianDateValueResponse:
    return EgyptianDateValueResponse(
        month_name=value.month_name,
        month_number=value.month_number,
        day=value.day,
        season=value.season,
        day_of_year=value.day_of_year,
        epagomenal_birth=value.epagomenal_birth,
    )


def _entry_response(entry: SothicEntry) -> SothicEntryResponse:
    return SothicEntryResponse(
        year=entry.year,
        jd_rising=entry.jd_rising,
        date_utc=entry.date_utc.isoformat() if entry.date_utc is not None else None,
        calendar_year=entry.calendar_year,
        calendar_month=entry.calendar_month,
        calendar_day=entry.calendar_day,
        day_of_year=entry.day_of_year,
        drift_days=entry.drift_days,
        cycle_position=entry.cycle_position,
        egyptian_date=_egyptian_date_response(entry.egyptian_date),
    )


def _event_response(event) -> SothicHeliacalEventResponse:
    truth = event.computation_truth
    classification = event.classification
    if truth is None or classification is None:
        raise RuntimeError("Sothic heliacal event is missing required truth layers")
    return SothicHeliacalEventResponse(
        event_kind=event.event_kind,
        star_name=event.star_name,
        is_found=event.is_found,
        jd_ut=event.jd_ut,
        jd_start=truth.jd_start,
        search_days=truth.search_days,
        arcus_visionis_deg=truth.arcus_visionis,
        qualifying_day_offset=truth.qualifying_day_offset,
        qualifying_elongation_deg=truth.qualifying_elongation,
        qualifying_sun_altitude_deg=truth.qualifying_sun_altitude,
        visibility_state=classification.visibility_state,
    )


def compute_egyptian_date(request: EgyptianDateRequest) -> EgyptianDateResponse:
    epoch_jd = (
        CENSORINUS_139_ANCHOR.jd
        if request.epoch_jd is None
        else request.epoch_jd
    )
    value = egyptian_civil_date(request.jd, epoch_jd=epoch_jd)
    return EgyptianDateResponse(
        jd=request.jd,
        anchor=_anchor_response(epoch_jd),
        date=_egyptian_date_response(value),
        provenance=SothicProvenanceResponse(
            engine_entrypoint="egyptian_civil_date",
            stage_sequence=[
                "validate_julian_day",
                "resolve_calendar_anchor",
                "modulo_365_civil_calendar",
                "serialize_egyptian_date",
            ],
        ),
    )


def compute_sothic_prediction(
    request: SothicPredictionRequest,
) -> SothicPredictionResponse:
    value = predict_sothic_epoch(
        request.known_epoch_year,
        request.n_cycles,
        cycle_length_years=request.cycle_length_years,
    )
    return SothicPredictionResponse(
        known_epoch_year=value.known_epoch_year,
        n_cycles=value.n_cycles,
        cycle_length_years=value.cycle_length_years,
        predicted_astronomical_year=value.predicted_astronomical_year,
        year_numbering="astronomical",
        model=value.model.value,
        evidence_kind="schematic_projection",
        provenance=SothicProvenanceResponse(
            engine_entrypoint="predict_sothic_epoch",
            cycle_model=value.model.value,
            stage_sequence=[
                "validate_astronomical_year_inputs",
                "apply_fixed_cycle_interval",
                "label_schematic_projection",
            ],
        ),
    )


def compute_sothic_rising(
    engine: Moira,
    request: SothicRisingRequest,
) -> SothicRisingResponse:
    epoch_jd = (
        CENSORINUS_139_ANCHOR.jd
        if request.epoch_jd is None
        else request.epoch_jd
    )
    policy = SothicComputationPolicy(
        calendar=SothicCalendarPolicy(epoch_jd=epoch_jd),
        heliacal=SothicHeliacalPolicy(
            arcus_visionis=request.arcus_visionis_deg,
            search_days=400,
        ),
    )
    with use_reader_override(getattr(engine, "_reader", None)):
        result = sothic_rising_series(
            request.latitude_deg,
            request.longitude_deg,
            request.year_start,
            request.year_end,
            policy=policy,
        )

    outcomes = [
        SothicYearOutcomeResponse(
            year=outcome.year,
            status=outcome.status.value,
            jd_start=outcome.jd_start,
            event=_event_response(outcome.heliacal_event),
            entry=(
                _entry_response(outcome.entry)
                if outcome.entry is not None
                else None
            ),
        )
        for outcome in result.outcomes
    ]
    return SothicRisingResponse(
        latitude_deg=result.latitude,
        longitude_deg=result.longitude,
        year_start=result.year_start,
        year_end=result.year_end,
        requested_year_count=len(result.outcomes),
        epoch_jd=result.epoch_jd,
        arcus_visionis_deg=result.arcus_visionis,
        search_days_per_year=result.search_days,
        found_count=result.found_count,
        not_found_within_window_count=result.not_found_within_window_count,
        outcomes=outcomes,
        anchor=_anchor_response(result.epoch_jd),
        provenance=SothicProvenanceResponse(
            engine_entrypoint="sothic_rising_series",
            delegated_source="moira.stars.heliacal_rising_event",
            cycle_model="schematic_1460_julian_year_cycle_position_only",
            route_max_years=MAX_SOTHIC_RANGE_YEARS,
            stage_sequence=[
                "validate_bounded_year_range",
                "resolve_calendar_and_visibility_policy",
                "search_each_astronomical_year",
                "preserve_found_or_not_found_within_window",
                "project_egyptian_civil_date",
                "serialize_truth_preserving_outcomes",
            ],
        ),
    )


__all__ = [
    "compute_egyptian_date",
    "compute_sothic_prediction",
    "compute_sothic_rising",
]
