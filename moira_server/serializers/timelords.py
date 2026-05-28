"""Serializers for phase-8 profection and timelord vessels."""

from __future__ import annotations

from moira.profections import ProfectionResult

from ..models.timelords import MonthlyProfectionResponse, ProfectionResultResponse


def serialize_profection_result(result: ProfectionResult) -> ProfectionResultResponse:
    return ProfectionResultResponse(
        age_years=result.age_years,
        profected_house=result.profected_house,
        profected_asc_lon=result.profected_asc_lon,
        profected_sign=result.profected_sign,
        lord_of_year=result.lord_of_year,
        activated_planets=list(result.activated_planets),
        monthly_lords=list(result.monthly_lords),
    )


def serialize_monthly_profection(result: tuple[float, str, str]) -> MonthlyProfectionResponse:
    longitude, sign, lord = result
    return MonthlyProfectionResponse(
        profected_longitude=longitude,
        sign=sign,
        lord_of_month=lord,
    )


__all__ = [
    "serialize_monthly_profection",
    "serialize_profection_result",
]
