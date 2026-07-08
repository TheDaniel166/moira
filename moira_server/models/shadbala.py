"""Transport models for Phase-9 Shadbala route family (P9-02)."""

from __future__ import annotations

import math
from datetime import datetime

from pydantic import Field, field_validator

from moira.constants import HouseSystem

from .common import _StrictModel


_SEVEN_PLANETS = frozenset(
    {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"}
)


class ShadbalaPolicyRequest(_StrictModel):
    """Explicit Shadbala computation policy."""

    ayanamsa_system: str = "Lahiri"

    @field_validator("ayanamsa_system")
    @classmethod
    def _non_empty_ayanamsa(cls, value: str) -> str:
        if not value:
            raise ValueError("ayanamsa_system must be non-empty")
        return value


class ShadbalaChartRequest(_StrictModel):
    """Chart-backed Shadbala request deriving support truth through Moira."""

    dt: datetime
    observer_lat: float = Field(ge=-90.0, le=90.0)
    observer_lon: float = Field(ge=-180.0, le=180.0)
    observer_elev_m: float = 0.0
    house_system: str = HouseSystem.PLACIDUS
    ayanamsa_system: str = "Lahiri"
    hora_lord: str | None = None
    policy: ShadbalaPolicyRequest | None = None

    @field_validator("dt")
    @classmethod
    def _aware_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("dt must be timezone-aware")
        return value

    @field_validator("observer_lat", "observer_lon", "observer_elev_m")
    @classmethod
    def _finite_observer_input(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("observer inputs must be finite")
        return value

    @field_validator("house_system", "ayanamsa_system")
    @classmethod
    def _non_empty_string_input(cls, value: str) -> str:
        if not value:
            raise ValueError("house_system and ayanamsa_system must be non-empty")
        return value

    @field_validator("hora_lord")
    @classmethod
    def _valid_hora_lord(cls, value: str | None) -> str | None:
        if value is not None and value not in _SEVEN_PLANETS:
            supported = ", ".join(sorted(_SEVEN_PLANETS))
            raise ValueError(f"hora_lord must be one of: {supported}")
        return value


class ShadbalaConditionChartRequest(ShadbalaChartRequest):
    """Chart-backed Shadbala condition request for one classical planet."""

    planet: str

    @field_validator("planet")
    @classmethod
    def _valid_condition_planet(cls, value: str) -> str:
        if value not in _SEVEN_PLANETS:
            supported = ", ".join(sorted(_SEVEN_PLANETS))
            raise ValueError(f"planet must be one of: {supported}")
        return value


class SthanaBalaResponse(_StrictModel):
    uchcha: float
    saptavargaja: float
    ojayugma: float
    kendradi: float
    drekkana: float
    total: float


class KalaBalaResponse(_StrictModel):
    nathonnatha: float
    paksha: float
    tribhaga: float
    abda_masa_vara_hora: float
    ayana: float
    yuddha: float
    total: float


class GrahaYuddhaResponse(_StrictModel):
    victor: str
    loser: str
    separation_deg: float
    shashtiamsas_transferred: float | None = None


class PlanetShadbalaResponse(_StrictModel):
    planet: str
    sthana_bala: SthanaBalaResponse
    dig_bala: float
    kala_bala: KalaBalaResponse
    chesta_bala: float
    naisargika_bala: float
    drig_bala: float
    ishta_phala: float
    kashta_phala: float
    total_shashtiamsas: float
    total_rupas: float
    required_rupas: float
    strength_ratio: float
    is_sufficient: bool


class ShadbalaResultResponse(_StrictModel):
    jd: float
    ayanamsa_system: str
    ayanamsa_degrees: float
    planets: dict[str, PlanetShadbalaResponse]


class ShadbalaConditionProfileResponse(_StrictModel):
    planet: str
    tier: str
    total_rupas: float
    required_rupas: float
    strength_ratio: float
    is_sufficient: bool


class ShadbalaChartProfileResponse(_StrictModel):
    sufficient_count: int
    insufficient_count: int
    strongest_planet: str
    weakest_planet: str
    planet_tiers: dict[str, str]
    strength_ratios: dict[str, float]
    ayanamsa_system: str


class ShadbalaNetworkProfileResponse(_StrictModel):
    ayanamsa_system: str
    strength_ranking: tuple[str, ...]
    dominant_planet: str
    recessive_planet: str
    active_wars: tuple[GrahaYuddhaResponse, ...]
    war_victors: frozenset[str]
    war_losers: frozenset[str]


class BhavaBalaResponse(_StrictModel):
    """One house's Bhava Bala (Raman Part II)."""

    house: int
    madhya_sidereal_lon: float
    rasi_index: int
    rasi_class: str
    lord: str
    bhavadhipati_bala: float
    bhava_dig_bala: float
    bhava_drishti_bala: float
    total_shashtiamsas: float
    total_rupas: float
    rank: int


class BhavaBalaResultResponse(_StrictModel):
    """Twelve-house Bhava Bala result."""

    jd: float
    ayanamsa_system: str
    ayanamsa_degrees: float
    houses: dict[int, BhavaBalaResponse]
    strongest_house: int
    weakest_house: int


class ShadbalaFullResponse(_StrictModel):
    """Single-call envelope: chart + profile + network + bhava.

    One support-truth derivation feeds all four surfaces, so every number
    is mutually consistent (same jd, ayanamsa, houses, panchanga).
    """

    chart: ShadbalaResultResponse
    profile: ShadbalaChartProfileResponse
    network: ShadbalaNetworkProfileResponse
    bhava: BhavaBalaResultResponse


__all__ = [
    "BhavaBalaResponse",
    "BhavaBalaResultResponse",
    "ShadbalaFullResponse",
    "GrahaYuddhaResponse",
    "KalaBalaResponse",
    "PlanetShadbalaResponse",
    "ShadbalaChartProfileResponse",
    "ShadbalaChartRequest",
    "ShadbalaConditionChartRequest",
    "ShadbalaConditionProfileResponse",
    "ShadbalaNetworkProfileResponse",
    "ShadbalaPolicyRequest",
    "ShadbalaResultResponse",
    "SthanaBalaResponse",
]
