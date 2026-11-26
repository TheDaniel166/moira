"""Adapt public Moira time transformations to typed HTTP results."""

from __future__ import annotations

from dataclasses import asdict

from moira.delta_t_physical import delta_t_breakdown, delta_t_distribution
from moira.julian import (
    calendar_datetime_from_jd,
    delta_t_from_jd_with_truth,
    jd_from_datetime_with_truth,
    julian_day,
    local_sidereal_time_with_truth,
    tdb_to_tt,
    tt_to_tdb,
    tt_to_ut,
    ut_to_tt,
    utc_to_tt_with_truth,
    utc_to_ut1_with_truth,
)

from ..models.chart import CalendarDateTimeResponse
from ..models.time import (
    CalendarTimeConversionRequest,
    DeltaTEstimateRequest,
    DeltaTRequest,
    DeltaTResponse,
    LocalSiderealTimeRequest,
    SiderealTimeRequest,
    SiderealTimeResponse,
    TimeConversionInput,
    TimeConversionResponse,
)


def convert_time(request: TimeConversionInput) -> TimeConversionResponse:
    """Call the exact directed conversion selected at the request boundary."""

    if isinstance(request, CalendarTimeConversionRequest):
        calendar = request.calendar
        hour = (
            calendar.hour + calendar.minute / 60.0 + calendar.second / 3600.0
            + calendar.microsecond / 3_600_000_000.0
        )
        jd = julian_day(calendar.year, calendar.month, calendar.day, hour)
        return TimeConversionResponse(request=request, jd=jd, model="UTC_coded_civil_JD")

    if request.dt is not None:
        truth = jd_from_datetime_with_truth(request.dt)
        return TimeConversionResponse(request=request, jd=truth.jd_utc, model=truth.target_scale, provenance=truth)

    jd = request.jd
    assert jd is not None
    direction = (request.source_scale, request.target_scale)
    match direction:
        case ("UTC", "civil_utc"):
            calendar = CalendarDateTimeResponse.model_validate(asdict(calendar_datetime_from_jd(jd)))
            return TimeConversionResponse(request=request, calendar_utc=calendar, model="proleptic Gregorian UTC")
        case ("UTC", "UT1"):
            truth = utc_to_ut1_with_truth(jd)
            return TimeConversionResponse(request=request, jd=truth.jd_ut1, model=truth.source_mode, provenance=truth)
        case ("UTC", "TT"):
            truth = utc_to_tt_with_truth(jd)
            return TimeConversionResponse(request=request, jd=truth.jd_tt, model=truth.conversion_mode, provenance=truth)
        case ("UT1", "TT") | ("TT", "UT1"):
            forward = direction == ("UT1", "TT")
            result = ut_to_tt(jd) if forward else tt_to_ut(jd)
            truth = delta_t_from_jd_with_truth(jd if forward else result)
            return TimeConversionResponse(request=request, jd=result, model=truth.source_product, provenance=truth)
        case ("TT", "TDB") | ("TDB", "TT"):
            result = tt_to_tdb(jd) if direction == ("TT", "TDB") else tdb_to_tt(jd)
            return TimeConversionResponse(request=request, jd=result, model="NAIF naif0012.tls")
        case _:
            raise ValueError("unsupported directed time conversion")


def compute_delta_t(request: DeltaTRequest) -> DeltaTResponse:
    """Return the requested Delta-T evidence without changing the engine policy."""

    if isinstance(request, DeltaTEstimateRequest):
        return DeltaTResponse(request=request, result=delta_t_from_jd_with_truth(request.jd_ut1))
    if request.kind == "breakdown":
        return DeltaTResponse(request=request, result=delta_t_breakdown(request.year))
    return DeltaTResponse(
        request=request, result=delta_t_distribution(request.year),
        uncertainty_interpretation="normal_approximation_with_model_policy_scale",
    )


def compute_sidereal_time(request: SiderealTimeRequest) -> SiderealTimeResponse:
    """Use the engine's two-scale reduction on the requested meridian."""

    longitude = request.longitude_deg_east if isinstance(request, LocalSiderealTimeRequest) else 0.0
    truth = local_sidereal_time_with_truth(
        request.jd_ut1, longitude, mode=request.mode, jd_tt=request.jd_tt,
    )
    return SiderealTimeResponse(
        request=request, sidereal_time_deg=truth.local_sidereal_time_deg, provenance=truth,
    )
