"""Typed transport for the Sirohi Choghadiya profile."""
from datetime import date
from typing import Annotated, Literal

from pydantic import Field

from moira.daily_panchanga import PanchangaSunriseDefinition

from ._vedic_inputs import CivilDate, FiniteNumber
from .common import _StrictModel
from .daily_panchanga import PanchangaMomentResponse


class ChoghadiyaSolarRequest(_StrictModel):
    """A sunrise weekday and the three ordered UT1 anchors."""

    weekday: Annotated[int, Field(strict=True, ge=0, le=6, description="Monday=0, Sunday=6")]
    sunrise_jd_ut1: FiniteNumber
    sunset_jd_ut1: FiniteNumber
    next_sunrise_jd_ut1: FiniteNumber


class ChoghadiyaDayRequest(_StrictModel):
    """A local date, observer and solar crossing policy."""

    local_date: CivilDate
    timezone: Annotated[str, Field(min_length=1, max_length=128)]
    latitude: Annotated[FiniteNumber, Field(ge=-90, le=90)]
    longitude: Annotated[FiniteNumber, Field(ge=-180, le=180)]
    sunrise_definition: PanchangaSunriseDefinition = PanchangaSunriseDefinition.RASHTRIYA_UPPER_LIMB


class ChoghadiyaIntervalResponse(_StrictModel):
    """One named half-open eighth of a solar arc."""

    period: Literal["day", "night"]
    ordinal: int
    name: str
    start_jd_ut1: float
    end_jd_ut1: float


class ChoghadiyaResponse(_StrictModel):
    """The daylight and nighttime arrays for the sunrise weekday."""

    weekday: int
    sunrise_jd_ut1: float
    sunset_jd_ut1: float
    next_sunrise_jd_ut1: float
    day: tuple[ChoghadiyaIntervalResponse, ...]
    night: tuple[ChoghadiyaIntervalResponse, ...]
    profile_id: Literal["sirohi_1916"]
    source_reference: str


class ChoghadiyaDayResponse(_StrictModel):
    """Reader-derived solar anchors and the civil display of the schedule."""

    local_date: date
    timezone: str
    latitude: float
    longitude: float
    sunrise_definition: PanchangaSunriseDefinition
    reader_binding: str
    status: Literal["available", "unavailable"]
    unavailable_reason: str | None
    sunrise: PanchangaMomentResponse | None
    sunset: PanchangaMomentResponse | None
    next_sunrise: PanchangaMomentResponse | None
    schedule: ChoghadiyaResponse | None
    boundaries: tuple[PanchangaMomentResponse, ...]
    profile_id: Literal["sirohi_1916"]
