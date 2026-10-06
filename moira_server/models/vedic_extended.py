"""Transport models for the Vedic Phase-2 deepening routes:
upagrahas, avasthas, and the Jaimini extended techniques."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from .common import _StrictModel
from ._vedic_inputs import ClassicalPlanet, NodePlanet, FiniteNumber, require_classical


def _validate_seven(value: dict[str, float]) -> dict[str, float]:
    return require_classical(value)


# --- Upagrahas --------------------------------------------------------------

class SunBasedUpagrahasRequest(_StrictModel):
    sun_sidereal_lon: FiniteNumber


class SunBasedUpagrahasResponse(_StrictModel):
    sun_longitude: float
    dhuma: float
    vyatipata: float
    parivesha: float
    indrachapa: float
    upaketu: float


class KalavelaRequest(_StrictModel):
    dt: datetime
    latitude: FiniteNumber = Field(ge=-90, le=90)
    longitude: FiniteNumber = Field(ge=-180, le=180)
    ayanamsa_system: str = "Lahiri"
    portion_point: Literal["beginning", "middle", "end"] = "beginning"
    mandi_mode: Literal[
        "alias_of_gulika", "distinct_kalidasa_table"
    ] = "alias_of_gulika"
    lord_sequence: Literal[
        "contiguous", "lordless_after_saturn"
    ] = "contiguous"

    @field_validator("dt")
    @classmethod
    def _aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("dt must be timezone-aware")
        return value


class KalavelaUpagrahaResponse(_StrictModel):
    name: str
    portion_planet: str | None
    part_index: int | None
    defining_jd: float
    sidereal_longitude: float
    tropical_longitude: float


class KalavelaResponse(_StrictModel):
    is_day_birth: bool
    weekday_index: int
    arc_start_jd: float
    arc_end_jd: float
    ayanamsa_system: str
    upagrahas: dict[str, KalavelaUpagrahaResponse]


# --- Avasthas ---------------------------------------------------------------

class AvasthaRequest(_StrictModel):
    sidereal_longitudes: dict[ClassicalPlanet, FiniteNumber]
    lagna_sidereal_lon: FiniteNumber
    deeptadi_source: Literal[
        "bphs_9", "saravali_9", "jataka_parijata_10", "phaladeepika_11"
    ] = "bphs_9"
    relationship_scheme: Literal["compound", "natural"] = "compound"
    node_longitudes: dict[NodePlanet, FiniteNumber] | None = None
    vriddha_fraction: FiniteNumber | None = Field(default=None, ge=0, le=1)

    @field_validator("sidereal_longitudes")
    @classmethod
    def _seven(cls, value: dict[str, float]) -> dict[str, float]:
        return _validate_seven(value)


class LajjitadiStateResponse(_StrictModel):
    state: str
    applies: bool
    evidence: str


class PlanetAvasthasResponse(_StrictModel):
    planet: str
    baladi_state: str
    baladi_effect_fraction: float | None
    baladi_effect_label: str
    jagradadi_state: str
    jagradadi_reason: str
    jagradadi_effect_fraction: float
    deeptadi_state: str
    deeptadi_source: str
    deeptadi_reason: str
    deeptadi_citation: str
    lajjitadi: tuple[LajjitadiStateResponse, ...]
    lajjitadi_active: tuple[str, ...]
    lajjitadi_notes: str


class AvasthaChartResponse(_StrictModel):
    deeptadi_source: str
    relationship_scheme: Literal["compound", "natural"] = "compound"
    vriddha_fraction: float | None = None
    planets: dict[str, PlanetAvasthasResponse]


# --- Jaimini extended -------------------------------------------------------

class ArudhaRequest(_StrictModel):
    sidereal_longitudes: dict[ClassicalPlanet, FiniteNumber]
    lagna_sidereal_lon: FiniteNumber
    arudha_exception: Literal["rath_tenth", "none"] = "rath_tenth"
    arudha_lords: Literal[
        "classical_seven", "jaimini_co_lords"
    ] = "classical_seven"
    node_longitudes: dict[NodePlanet, FiniteNumber] | None = None

    @model_validator(mode="after")
    def _co_lord_inputs(self) -> "ArudhaRequest":
        if self.arudha_lords == "jaimini_co_lords" and set(self.node_longitudes or {}) != {"Rahu", "Ketu"}:
            raise ValueError("jaimini_co_lords requires both Rahu and Ketu longitudes")
        return self

    @field_validator("sidereal_longitudes")
    @classmethod
    def _seven(cls, value: dict[str, float]) -> dict[str, float]:
        return _validate_seven(value)


class ArudhaPadaResponse(_StrictModel):
    house: int
    label: str
    house_sign: int
    lord: str
    lord_sign: int
    computed_sign: int
    pada_sign: int
    exception_applied: bool


class ArudhaResponse(_StrictModel):
    lagna_sign: int
    padas: dict[int, ArudhaPadaResponse]
    arudha_lagna_sign: int
    upapada_lagna_sign: int
    lineage: str


class ArgalaRequest(_StrictModel):
    sidereal_longitudes: dict[ClassicalPlanet, FiniteNumber]
    lagna_sidereal_lon: FiniteNumber
    node_longitudes: dict[NodePlanet, FiniteNumber] | None = None

    @field_validator("sidereal_longitudes")
    @classmethod
    def _seven(cls, value: dict[str, float]) -> dict[str, float]:
        return _validate_seven(value)


class ArgalaHouseResponse(_StrictModel):
    reference_sign: int
    reversed_by_ketu: bool
    argalas: dict[int, tuple[str, ...]]
    obstructors: dict[int, tuple[str, ...]]
    unobstructed: dict[int, bool]
    malefic_third_argala: tuple[str, ...]


class ArgalaResponse(_StrictModel):
    lagna_sign: int
    houses: dict[int, ArgalaHouseResponse]
    lineage: str


class KarakamsaRequest(_StrictModel):
    sidereal_longitudes: dict[Literal["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu"], FiniteNumber]
    lagna_sidereal_lon: FiniteNumber | None = None
    scheme: Annotated[int, Field(strict=True, ge=7, le=8)] = 7

    @model_validator(mode="after")
    def _rahu_for_eight(self) -> "KarakamsaRequest":
        if self.scheme == 8 and "Rahu" not in self.sidereal_longitudes:
            raise ValueError("eight-karaka scheme requires Rahu in sidereal_longitudes")
        return self

    @field_validator("sidereal_longitudes")
    @classmethod
    def _seven(cls, value: dict[str, float]) -> dict[str, float]:
        return _validate_seven(value)


class KarakamsaResponse(_StrictModel):
    atmakaraka: str
    karakamsa_sign: int
    d9_reading: str
    d1_reading: str
    svamsa_sign: int | None


class CharaDashaRequest(_StrictModel):
    sidereal_longitudes: dict[ClassicalPlanet, FiniteNumber]
    lagna_sidereal_lon: FiniteNumber
    birth_jd: FiniteNumber
    node_longitudes: dict[NodePlanet, FiniteNumber] | None = None

    @field_validator("sidereal_longitudes")
    @classmethod
    def _seven(cls, value: dict[str, float]) -> dict[str, float]:
        return _validate_seven(value)


class CharaDashaPeriodResponse(_StrictModel):
    sign: int
    years: int
    start_jd: float
    end_jd: float
    lord: str
    lord_note: str
    antardasha_signs: tuple[int, ...]
    antardasha_starts: tuple[float, ...]


class CharaDashaResponse(_StrictModel):
    lagna_sign: int
    direction: int
    birth_jd: float
    periods: tuple[CharaDashaPeriodResponse, ...]
    lineage: str


__all__ = [
    "ArgalaHouseResponse", "ArgalaRequest", "ArgalaResponse",
    "ArudhaPadaResponse", "ArudhaRequest", "ArudhaResponse",
    "AvasthaChartResponse", "AvasthaRequest",
    "CharaDashaPeriodResponse", "CharaDashaRequest", "CharaDashaResponse",
    "KalavelaRequest", "KalavelaResponse", "KalavelaUpagrahaResponse",
    "KarakamsaRequest", "KarakamsaResponse",
    "LajjitadiStateResponse", "PlanetAvasthasResponse",
    "SunBasedUpagrahasRequest", "SunBasedUpagrahasResponse",
]
