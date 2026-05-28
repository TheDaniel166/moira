"""Transport models for phase-8 profection and timelord route families."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from .common import _StrictModel


class TimelordNativityRequest(_StrictModel):
    dt: datetime
    latitude: float
    longitude: float
    house_system: str | None = None
    bodies: list[str] | None = None
    include_nodes: bool = False
    observer_lat: float | None = None
    observer_lon: float | None = None
    observer_elev_m: float = 0.0
    activation_orb: float = Field(default=5.0, ge=0.0)


class AnnualProfectionRequest(_StrictModel):
    natal: TimelordNativityRequest
    age_years: int = Field(ge=0)


class MonthlyProfectionRequest(_StrictModel):
    natal: TimelordNativityRequest
    age_years: int = Field(ge=0)
    month_index: int = Field(ge=0, le=11)


class ProfectionScheduleRequest(_StrictModel):
    natal: TimelordNativityRequest
    current_dt: datetime


class ProfectionResultResponse(_StrictModel):
    age_years: int
    profected_house: int
    profected_asc_lon: float
    profected_sign: str
    lord_of_year: str
    activated_planets: list[str]
    monthly_lords: list[str]


class MonthlyProfectionResponse(_StrictModel):
    profected_longitude: float
    sign: str
    lord_of_month: str


__all__ = [
    "AnnualProfectionRequest",
    "MonthlyProfectionRequest",
    "MonthlyProfectionResponse",
    "ProfectionResultResponse",
    "ProfectionScheduleRequest",
    "TimelordNativityRequest",
]
