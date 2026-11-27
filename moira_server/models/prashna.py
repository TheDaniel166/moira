"""Typed transport for the Raman Prasna Marga sphutas."""
from datetime import date
from typing import Annotated, Literal

from pydantic import Field

from moira.daily_panchanga import PanchangaSunriseDefinition

from ._vedic_inputs import CivilDateTime, FiniteNumber, KnownAyanamsa
from .common import _StrictModel
from .daily_panchanga import PanchangaMomentResponse

_CanonicalLongitude = Annotated[FiniteNumber, Field(ge=0, lt=360)]


class PrashnaRequest(_StrictModel):
    """The five canonical sidereal longitudes for the three sums."""

    lagna: _CanonicalLongitude
    moon: _CanonicalLongitude
    gulika: _CanonicalLongitude
    sun: _CanonicalLongitude
    rahu: _CanonicalLongitude


class PrashnaResponse(PrashnaRequest):
    """The input longitudes and the three reduced sphutas."""

    tri: float
    chatus: float
    pancha: float
    profile_id: Literal["prasna_marga_raman_1991"]
    source_reference: str


class PrashnaChartRequest(_StrictModel):
    """Question instant, observer, sunrise policy and explicit Rahu mode."""

    dt: CivilDateTime
    latitude: Annotated[FiniteNumber, Field(ge=-90, le=90)]
    longitude: Annotated[FiniteNumber, Field(ge=-180, le=180)]
    timezone: Annotated[str, Field(min_length=1, max_length=128)]
    ayanamsa_system: KnownAyanamsa = "Lahiri"
    sunrise_definition: PanchangaSunriseDefinition = PanchangaSunriseDefinition.RASHTRIYA_UPPER_LIMB
    rahu_mode: Literal["mean", "true"]


class PrashnaGulikaResponse(_StrictModel):
    """The Māndi-based Gulika arc, defining instant and sidereal ascendant."""

    sunrise_date: date
    period: Literal["day", "night"]
    arc_start: PanchangaMomentResponse
    arc_end: PanchangaMomentResponse
    defining_moment: PanchangaMomentResponse
    jd_tt: float
    tropical_lagna: float
    sidereal_longitude: float
    ayanamsa_degrees: float
    ayanamsa_path: str
    policy: Literal["raman_mandi_30_ghati_table"]


class PrashnaChartResponse(_StrictModel):
    """Question chart scope, evidence and availability."""

    question: PanchangaMomentResponse
    timezone: str
    latitude: float
    longitude: float
    ayanamsa_system: str
    rahu_mode: Literal["mean", "true"]
    sunrise_definition: PanchangaSunriseDefinition
    reader_binding: str
    status: Literal["available", "unavailable"]
    unavailable_reason: str | None
    gulika: PrashnaGulikaResponse | None
    result: PrashnaResponse | None
    jd_tt: float | None
    ayanamsa_degrees: float | None
    ayanamsa_path: str | None
    ephemeris_identity: str | None
    profile_id: Literal["prasna_marga_raman_1991"]
