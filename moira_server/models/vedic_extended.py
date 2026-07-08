"""Transport models for the Vedic Phase-2 deepening routes:
upagrahas, avasthas, and the Jaimini extended techniques."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Literal

from pydantic import field_validator

from .common import _StrictModel


_SEVEN_PLANETS = frozenset(
    {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"}
)


def _validate_seven(value: dict[str, float]) -> dict[str, float]:
    missing = _SEVEN_PLANETS - set(value)
    if missing:
        raise ValueError(
            f"sidereal_longitudes must include all seven classical "
            f"planets; missing: {sorted(missing)}"
        )
    for name, lon in value.items():
        if not math.isfinite(lon):
            raise ValueError(f"longitude for {name} must be finite")
    return value


# --- Upagrahas --------------------------------------------------------------

class SunBasedUpagrahasRequest(_StrictModel):
    sun_sidereal_lon: float

    @field_validator("sun_sidereal_lon")
    @classmethod
    def _finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("sun_sidereal_lon must be finite")
        return value


class SunBasedUpagrahasResponse(_StrictModel):
    sun_longitude: float
    dhuma: float
    vyatipata: float
    parivesha: float
    indrachapa: float
    upaketu: float


class KalavelaRequest(_StrictModel):
    dt: datetime
    latitude: float
    longitude: float
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
    sidereal_longitudes: dict[str, float]
    lagna_sidereal_lon: float
    deeptadi_source: Literal[
        "bphs_9", "saravali_9", "jataka_parijata_10", "phaladeepika_11"
    ] = "bphs_9"
    relationship_scheme: Literal["compound", "natural"] = "compound"
    node_longitudes: dict[str, float] | None = None

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
    planets: dict[str, PlanetAvasthasResponse]


# --- Jaimini extended -------------------------------------------------------

class ArudhaRequest(_StrictModel):
    sidereal_longitudes: dict[str, float]
    lagna_sidereal_lon: float
    arudha_exception: Literal["rath_tenth", "none"] = "rath_tenth"
    arudha_lords: Literal[
        "classical_seven", "jaimini_co_lords"
    ] = "classical_seven"
    node_longitudes: dict[str, float] | None = None

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
    sidereal_longitudes: dict[str, float]
    lagna_sidereal_lon: float
    node_longitudes: dict[str, float] | None = None

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
    sidereal_longitudes: dict[str, float]
    lagna_sidereal_lon: float | None = None
    scheme: int = 7

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
    sidereal_longitudes: dict[str, float]
    lagna_sidereal_lon: float
    birth_jd: float
    node_longitudes: dict[str, float] | None = None

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
