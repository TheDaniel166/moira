"""Typed timing and chart contracts for the two Vedic return methods."""
from typing import Annotated, Literal

from pydantic import Field

from ._vedic_inputs import CivilDateTime, FiniteNumber, KnownAyanamsa, KnownHouseSystem
from .common import _StrictModel
from .daily_panchanga import PanchangaMomentResponse
from .lunar_month import CalendarBoundaryResponse


class ReturnSiteRequest(_StrictModel):
    """Location, civil reference and house system for the return chart."""

    return_year: Annotated[int, Field(strict=True, ge=2, le=9997)]
    latitude: Annotated[FiniteNumber, Field(ge=-90, le=90)]
    longitude: Annotated[FiniteNumber, Field(ge=-180, le=180)]
    house_system: KnownHouseSystem = "P"


class TithiPraveshaRequest(ReturnSiteRequest):
    """Natal instant, source profile, and explicit Gregorian return-year timezone."""

    natal_dt: CivilDateTime
    profile: Literal["rao_2014_tropical", "rao_2014_sidereal_comparison"]
    timezone: Annotated[str, Field(min_length=1, max_length=128)]
    ayanamsa_system: KnownAyanamsa = "True Pushya"


class MonthlyTajikaRequest(ReturnSiteRequest):
    """Natal UT1, annual return year, and a one-based month number."""

    birth_jd_ut1: FiniteNumber
    month: Annotated[int, Field(strict=True, ge=1, le=12)]
    timezone: Annotated[str, Field(min_length=1, max_length=128)] = "UTC"
    ayanamsa_system: KnownAyanamsa = "Lahiri"


class VedicReturnCrossingResponse(_StrictModel):
    """Angular residual and the solved UT1 bracket."""

    jd_ut1: float
    lower_jd_ut1: float
    upper_jd_ut1: float
    target_degrees: float
    residual_degrees: float


class VedicReturnChartResponse(_StrictModel):
    """Apparent tropical positions and their explicit sidereal chart reduction."""

    jd_ut1: float
    jd_tt: float
    ayanamsa_system: str
    ayanamsa_degrees: float
    latitude: float
    longitude: float
    house_system: str
    effective_house_system: str
    tropical_ascendant: float
    sidereal_ascendant: float
    sidereal_cusps: tuple[float, ...]
    tropical_longitudes: dict[str, float]
    sidereal_longitudes: dict[str, float]


class TithiPraveshaCandidateResponse(_StrictModel):
    """A conjunction-bounded lunation and its candidate return."""

    conjunction: CalendarBoundaryResponse
    next_conjunction: CalendarBoundaryResponse
    conjunction_sign_index: int
    crossing: VedicReturnCrossingResponse
    time: PanchangaMomentResponse


class TithiPraveshaResponse(_StrictModel):
    """Eligible candidates and chart availability for the requested civil year."""

    profile_id: Literal["rao_2014_tropical", "rao_2014_sidereal_comparison"]
    source_reference: str
    return_year: int
    timezone: str
    year_start_jd_ut1: float
    year_end_jd_ut1: float
    natal_phase_degrees: float
    natal_conjunction: CalendarBoundaryResponse | None
    natal_conjunction_sign_index: int | None
    candidates: tuple[TithiPraveshaCandidateResponse, ...]
    status: Literal["available", "ambiguous", "unavailable"]
    reason: str | None
    chart: VedicReturnChartResponse | None


class MonthlyTajikaResponse(_StrictModel):
    """Annual anchors, monthly solar target, and a chart at the solved instant."""

    profile_id: Literal["hayanaratna_sidereal_ephemeris"]
    source_reference: str
    return_year: int
    month: int
    annual_return_jd_ut1: float
    next_annual_return_jd_ut1: float
    target_sidereal_sun_degrees: float
    time: PanchangaMomentResponse
    crossing: VedicReturnCrossingResponse | None
    chart: VedicReturnChartResponse
