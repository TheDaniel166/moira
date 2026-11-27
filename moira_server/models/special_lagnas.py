"""Typed transport for the two Special Lagna calculation inputs."""

from typing import Annotated, Literal

from pydantic import Field

from moira.daily_panchanga import PanchangaSunriseDefinition

from ._vedic_inputs import CivilDateTime, FiniteNumber, KnownAyanamsa
from .common import _StrictModel
from .daily_panchanga import PanchangaMomentResponse


class SpecialLagnaRequest(_StrictModel):
    sun_sidereal_longitude: Annotated[FiniteNumber, Field(ge=0, lt=360)]
    elapsed_seconds: Annotated[FiniteNumber, Field(ge=0)]


class SpecialLagnaBirthRequest(_StrictModel):
    dt: CivilDateTime
    latitude: Annotated[FiniteNumber, Field(ge=-90, le=90)]
    longitude: Annotated[FiniteNumber, Field(ge=-180, le=180)]
    timezone: Annotated[str, Field(min_length=1, max_length=128)]
    ayanamsa_system: KnownAyanamsa = "Lahiri"
    sunrise_definition: PanchangaSunriseDefinition = PanchangaSunriseDefinition.RASHTRIYA_UPPER_LIMB


class SpecialLagnaResponse(_StrictModel):
    sun_sidereal_longitude: float
    elapsed_seconds: float
    bhava_longitude: float
    hora_longitude: float
    ghati_longitude: float
    source_reference: str


class SpecialLagnaBirthResponse(_StrictModel):
    birth: PanchangaMomentResponse
    timezone: str
    latitude: float
    longitude: float
    ayanamsa_system: str
    sunrise_definition: PanchangaSunriseDefinition
    sunrise_altitude_degrees: float
    reader_binding: Literal["caller_owned_reader", "active_or_default_reader"]
    candidate_sunrises: tuple[PanchangaMomentResponse, ...]
    sunrise: PanchangaMomentResponse | None
    status: Literal["available", "unavailable"]
    unavailable_reason: Literal["sunrise_absent", "sunrise_ambiguous"] | None
    result: SpecialLagnaResponse | None
    source_reference: str
