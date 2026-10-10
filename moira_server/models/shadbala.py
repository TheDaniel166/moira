"""Transport models for Phase-9 Shadbala route family (P9-02)."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator

from moira.constants import HouseSystem

from .common import _StrictModel
from ._vedic_inputs import CivilDateTime, FiniteNumber, KnownAyanamsa, KnownHouseSystem


_SEVEN_PLANETS = frozenset(
    {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"}
)


class ShadbalaPolicyRequest(_StrictModel):
    """Explicit Shadbala computation policy."""

    ayanamsa_system: KnownAyanamsa = "Lahiri"
    saptavargaja_profile: Literal['raman_1996', 'bphs_santhanam_27'] = 'raman_1996'

    @field_validator("ayanamsa_system")
    @classmethod
    def _non_empty_ayanamsa(cls, value: str) -> str:
        if not value:
            raise ValueError("ayanamsa_system must be non-empty")
        return value


class ShadbalaChartRequest(_StrictModel):
    """Chart-backed Shadbala request deriving support truth through Moira."""

    dt: CivilDateTime
    observer_lat: FiniteNumber = Field(ge=-90.0, le=90.0)
    observer_lon: FiniteNumber = Field(ge=-180.0, le=180.0)
    observer_elev_m: FiniteNumber = 0.0
    house_system: KnownHouseSystem = HouseSystem.PLACIDUS
    ayanamsa_system: KnownAyanamsa = "Lahiri"
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


class ShadbalaAppliedPolicyResponse(_StrictModel):
    requested_ayanamsa_system: str
    policy_ayanamsa_system: str | None
    applied_ayanamsa_system: str
    ayanamsa_precedence: Literal["policy", "request"]
    requested_house_system: str
    resolved_house_system: str
    effective_house_system: str
    polar_fallback_applied: bool
    hora_lord: str | None
    saptavargaja_profile: str = 'raman_1996'
    kala_components: str = 'raman_1996_apparent_time_actual_declination'
    amvh_convention: str = 'moira_ingress_year_month_jd_weekday_optional_hora'
    paksha_nature: str = 'moira_same_sign_mercury_tithi8_start_moon_v1'
    war_policy: str = 'moira_simultaneous_raman_raw_pairs_v1'
    threshold_convention: str = 'moira_retained_required_rupas'


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
    tied: bool = False
    rule: str = 'raman_1996_lesser_longitude'
    adjustment_component: str = 'kala_yuddha'


class ShadbalaContextResponse(_StrictModel):
    jd: float
    ayanamsa_system: str
    sidereal_longitudes: tuple[tuple[str, float], ...]
    declinations: tuple[tuple[str, float], ...]
    chesta_values: tuple[tuple[str, float], ...]
    local_apparent_day_fraction: float
    sunrise_jd: float | None
    sunset_jd: float | None
    next_sunrise_jd: float | None
    abda_lord: str
    masa_lord: str
    vara_lord: str
    hora_lord: str | None
    provenance: str
    observer_latitude: float | None
    observer_longitude: float | None
    longitude_frame: str
    declination_frame: str
    mercury_nature: str
    vara_basis: str = 'supplied'
    vara_jd_utc: float | None = None


class SaptavargajaEntryResponse(_StrictModel):
    division: int
    sign_index: int
    lord: str
    dignity: str
    shashtiamsas: float


class WarResolutionResponse(_StrictModel):
    pairs: list[GrahaYuddhaResponse]
    raw_aggregates: tuple[tuple[str, float], ...]
    raw_totals: tuple[tuple[str, float], ...]
    raw_chesta: tuple[tuple[str, float], ...]
    credits: tuple[tuple[str, float], ...]
    debits: tuple[tuple[str, float], ...]
    adjustments: tuple[tuple[str, float], ...]
    policy: str
    source: str


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
    policy_receipt: ShadbalaAppliedPolicyResponse | None = None
    jd: float
    ayanamsa_system: str
    ayanamsa_degrees: float
    planets: dict[str, PlanetShadbalaResponse]
    context: ShadbalaContextResponse | None = None
    war_resolution: WarResolutionResponse | None = None
    saptavargaja_profile: str | None = None
    saptavargaja_evidence: dict[str, list[SaptavargajaEntryResponse]] = Field(default_factory=dict)


class ShadbalaConditionProfileResponse(_StrictModel):
    policy_receipt: ShadbalaAppliedPolicyResponse | None = None
    planet: str
    tier: str
    total_rupas: float
    required_rupas: float
    strength_ratio: float
    is_sufficient: bool


class ShadbalaChartProfileResponse(_StrictModel):
    policy_receipt: ShadbalaAppliedPolicyResponse | None = None
    sufficient_count: int
    insufficient_count: int
    strongest_planet: str
    weakest_planet: str
    planet_tiers: dict[str, str]
    strength_ratios: dict[str, float]
    ayanamsa_system: str


class ShadbalaNetworkProfileResponse(_StrictModel):
    policy_receipt: ShadbalaAppliedPolicyResponse | None = None
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

    policy_receipt: ShadbalaAppliedPolicyResponse | None = None

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

    policy_receipt: ShadbalaAppliedPolicyResponse | None = None
    chart: ShadbalaResultResponse
    profile: ShadbalaChartProfileResponse
    network: ShadbalaNetworkProfileResponse
    bhava: BhavaBalaResultResponse


__all__ = [
    "ShadbalaAppliedPolicyResponse",
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
