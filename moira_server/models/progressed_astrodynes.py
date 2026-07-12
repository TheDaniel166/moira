"""Strict transport contracts for Church of Light progressed Astrodynes."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator, model_validator

from moira.astrodynes import ASTRODYNE_PLANETS, ASTRODYNE_POINTS, ASTRODYNE_SIGNS

from .common import _StrictModel
from .astrodynes import AstrodynesCalculationResponse


_BODIES = frozenset((*ASTRODYNE_PLANETS, *ASTRODYNE_POINTS))


def _finite(value: float) -> float:
    if not math.isfinite(value):
        raise ValueError("value must be finite")
    return value


class ProgressedAstrodynePolicyResponse(_StrictModel):
    major_carry_factor: float
    major_moon_carry_divisor: float
    minor_carry_divisor: float
    transit_carry_divisor: float
    aspect_percentage_per_orb_degree: float
    major_moon_aspect_divisor: float
    minor_aspect_divisor: float
    transit_aspect_divisor: float
    effective_orb_arcmin: float
    orb_limit_fraction: float
    major_mutual_reception_bonus_each: float
    total_influence_average_factor: float
    manual_rounding_digits: int


class ProgressedAstrodynesDoctrineResponse(_StrictModel):
    doctrine: Literal["church_of_light_progressed_astrodynes"]
    parity_status: Literal["doctrinal_parity_with_published_anomalies"]
    kernel_required: Literal[False]
    policy: ProgressedAstrodynePolicyResponse
    tiers: tuple[str, ...]
    terminal_kinds: tuple[str, ...]
    source_anomalies: tuple[str, ...]


class ProgressedAstrodynesChartRequest(_StrictModel):
    natal_dt: datetime
    target_dt: datetime
    observer_lat: float = Field(ge=-90.0, le=90.0)
    observer_lon: float = Field(ge=-180.0, le=180.0)
    house_system: str = "P"
    allow_house_fallback: bool = False

    @field_validator("natal_dt", "target_dt")
    @classmethod
    def _aware_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("datetime must be timezone-aware")
        return value

    @field_validator("observer_lat", "observer_lon")
    @classmethod
    def _finite_observer(cls, value: float) -> float:
        return _finite(value)

    @field_validator("house_system")
    @classmethod
    def _house_system(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("house_system must be non-empty")
        return value

    @model_validator(mode="after")
    def _ordered_dates(self) -> "ProgressedAstrodynesChartRequest":
        if self.target_dt < self.natal_dt:
            raise ValueError("target_dt must not precede natal_dt")
        return self


class ProgressedContactQueryRequest(_StrictModel):
    body_a: str
    kind_a: Literal["radical", "major_progressed", "minor_progressed", "transit"]
    body_b: str
    kind_b: Literal["radical", "major_progressed", "minor_progressed", "transit"]
    aspect: str = Field(min_length=1)

    @field_validator("body_a", "body_b")
    @classmethod
    def _body(cls, value: str) -> str:
        if value not in _BODIES:
            raise ValueError(f"unsupported Astrodyne body: {value!r}")
        return value


class ProgressedContactSearchRequest(_StrictModel):
    natal_dt: datetime
    start_dt: datetime
    end_dt: datetime
    observer_lat: float = Field(ge=-90.0, le=90.0)
    observer_lon: float = Field(ge=-180.0, le=180.0)
    query: ProgressedContactQueryRequest
    reenforces_major: ProgressedContactQueryRequest | None = None
    house_system: str = "P"
    allow_house_fallback: bool = False
    coarse_step_hours: float | None = Field(default=None, gt=0.0)
    boundary_tolerance_seconds: float = Field(default=1.0, gt=0.0)
    perfection_tolerance_seconds: float = Field(default=1.0, gt=0.0)
    perfection_distance_tolerance_arcmin: float = Field(default=0.01, gt=0.0)
    max_samples: int = Field(default=50_000, ge=3, le=200_000)

    @field_validator("natal_dt", "start_dt", "end_dt")
    @classmethod
    def _aware_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("datetime must be timezone-aware")
        return value

    @field_validator("observer_lat", "observer_lon")
    @classmethod
    def _finite_observer(cls, value: float) -> float:
        return _finite(value)

    @field_validator("house_system")
    @classmethod
    def _house_system(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("house_system must be non-empty")
        return value

    @model_validator(mode="after")
    def _ordered_dates(self) -> "ProgressedContactSearchRequest":
        if self.start_dt < self.natal_dt:
            raise ValueError("start_dt must not precede natal_dt")
        if self.end_dt <= self.start_dt:
            raise ValueError("end_dt must be later than start_dt")
        return self


class ProgressedInfluenceIntegrationRequest(_StrictModel):
    natal_dt: datetime
    start_dt: datetime
    end_dt: datetime
    observer_lat: float = Field(ge=-90.0, le=90.0)
    observer_lon: float = Field(ge=-180.0, le=180.0)
    query: ProgressedContactQueryRequest
    house_system: str = "P"
    allow_house_fallback: bool = False
    max_step_hours: float = Field(default=6.0, gt=0.0)
    max_samples: int = Field(default=50_000, ge=2, le=200_000)

    @field_validator("natal_dt", "start_dt", "end_dt")
    @classmethod
    def _aware_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("datetime must be timezone-aware")
        return value

    @field_validator("observer_lat", "observer_lon")
    @classmethod
    def _finite_observer(cls, value: float) -> float:
        return _finite(value)

    @field_validator("house_system")
    @classmethod
    def _house_system(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("house_system must be non-empty")
        return value

    @model_validator(mode="after")
    def _ordered_dates(self) -> "ProgressedInfluenceIntegrationRequest":
        if self.start_dt < self.natal_dt:
            raise ValueError("start_dt must not precede natal_dt")
        if self.end_dt <= self.start_dt:
            raise ValueError("end_dt must be later than start_dt")
        return self


class ProgressedContactSearchPolicyResponse(_StrictModel):
    coarse_step_hours: float
    boundary_tolerance_seconds: float
    perfection_tolerance_seconds: float
    perfection_distance_tolerance_arcmin: float
    max_samples: int


class ProgressedContactMomentResponse(_StrictModel):
    event: str
    dt: datetime
    jd_ut: float
    distance_arcmin: float
    power: float
    harmony: float
    discord: float
    relation_id: str
    reenforcement_power: float | None
    reenforced_major_power: float | None


class ProgressedContactWindowResponse(_StrictModel):
    entry: ProgressedContactMomentResponse
    closest_approaches: tuple[ProgressedContactMomentResponse, ...]
    exit: ProgressedContactMomentResponse
    entry_clipped: bool
    exit_clipped: bool


class ProgressedContactSearchResponse(_StrictModel):
    query: ProgressedContactQueryRequest
    start_dt: datetime
    end_dt: datetime
    policy: ProgressedContactSearchPolicyResponse
    sample_count: int
    windows: tuple[ProgressedContactWindowResponse, ...]
    reenforces_major: ProgressedContactQueryRequest | None
    provenance: Literal["church_of_light_one_degree_band_moira_bounded_search"]


class ProgressedVariableInfluenceResponse(_StrictModel):
    query: ProgressedContactQueryRequest
    start_dt: datetime
    end_dt: datetime
    duration_days: float
    method: Literal["composite_trapezoid_actual_ephemeris"]
    max_step_hours: float
    sample_count: int
    total_power_days: float
    total_harmony_days: float
    total_discord_days: float
    average_power: float
    average_harmony: float
    average_discord: float
    coarse_total_power_days: float
    power_error_estimate_days: float
    constant_rate_comparator_power_days: float | None
    constant_rate_difference_days: float | None
    provenance: Literal["source_instantaneous_curve_moira_composite_trapezoid"]


class ChurchOfLightSymbolicDateResponse(_StrictModel):
    year: int
    month: int
    day: float


class ChurchOfLightProgressionTimeResponse(_StrictModel):
    natal_jd_ut: float
    target_jd_ut: float
    greenwich_noon_jd_ut: float
    egmt_interval_hours: float
    limiting_date: ChurchOfLightSymbolicDateResponse
    major_completed_years: int
    major_calendar_offset_days: float
    major_egmt_interval_hours: float
    major_ephemeris_jd_ut: float
    major_ephemeris_datetime: datetime
    minor_approximate_jd_ut: float
    minor_ephemeris_jd_ut: float
    minor_ephemeris_datetime: datetime
    transit_jd_ut: float
    solar_constant_deg: float
    minor_moon_target_longitude_deg: float
    midheaven_constant_deg: float


class ProgressedChartTerminalResponse(_StrictModel):
    terminal_id: str
    body: str
    kind: str
    longitude_deg: float
    declination_deg: float
    sign: str
    house: int
    house_class: str


class ProgressedChartGeometryResponse(_StrictModel):
    natal_dt: datetime
    target_dt: datetime
    observer_lat: float
    observer_lon: float
    requested_house_system: str
    effective_house_system: str
    house_fallback: bool
    house_fallback_reason: str | None
    natal_cusps: tuple[float, ...]
    time_truth: ChurchOfLightProgressionTimeResponse
    natal_terminals: tuple[ProgressedChartTerminalResponse, ...]
    major_terminals: tuple[ProgressedChartTerminalResponse, ...]
    minor_terminals: tuple[ProgressedChartTerminalResponse, ...]
    transit_terminals: tuple[ProgressedChartTerminalResponse, ...]


class ProgressedChartProvenanceResponse(_StrictModel):
    doctrine: Literal["church_of_light_progressed_astrodynes"]
    engine_entrypoint: str
    kernel_required: Literal[True]
    planetary_frame: Literal["geocentric_apparent"]
    major_time_key: str
    minor_time_key: str
    angle_method: str
    natal_house_frame: str


class ProgressedAstrodynesChartResponse(_StrictModel):
    geometry: ProgressedChartGeometryResponse
    natal: AstrodynesCalculationResponse
    normal: ProgressedNormalResponse
    major_relations: tuple[ProgressedRelationResponse, ...]
    minor_relations: tuple[ProgressedRelationResponse, ...]
    transit_relations: tuple[ProgressedRelationResponse, ...]
    reenforcements: tuple[ProgressedReenforcementResponse, ...]
    practical: ProgressedPracticalResponse
    provenance: ProgressedChartProvenanceResponse


class ProgressedBaselineRequest(_StrictModel):
    power: float = Field(ge=0.0)
    harmony: float = Field(ge=0.0)
    discord: float = Field(ge=0.0)

    @field_validator("power", "harmony", "discord")
    @classmethod
    def _finite_values(cls, value: float) -> float:
        return _finite(value)


class ProgressedNatalBodyRequest(ProgressedBaselineRequest):
    body: str

    @field_validator("body")
    @classmethod
    def _body(cls, value: str) -> str:
        if value not in _BODIES:
            raise ValueError(f"unsupported Astrodyne body: {value!r}")
        return value


class ProgressedPlacementRequest(_StrictModel):
    body: str
    longitude_deg: float
    house: int = Field(ge=1, le=12)

    @field_validator("body")
    @classmethod
    def _body(cls, value: str) -> str:
        if value not in _BODIES:
            raise ValueError(f"unsupported Astrodyne body: {value!r}")
        return value

    @field_validator("longitude_deg")
    @classmethod
    def _longitude(cls, value: float) -> float:
        return _finite(value)


class ProgressedNormalRequest(_StrictModel):
    birth_bodies: tuple[ProgressedNatalBodyRequest, ...]
    birth_signs: dict[str, ProgressedBaselineRequest]
    birth_houses: dict[int, ProgressedBaselineRequest]
    placements: tuple[ProgressedPlacementRequest, ...]

    @model_validator(mode="after")
    def _complete(self) -> "ProgressedNormalRequest":
        bodies = [item.body for item in self.birth_bodies]
        placements = [item.body for item in self.placements]
        if len(bodies) != len(set(bodies)) or frozenset(bodies) != _BODIES:
            raise ValueError("birth_bodies must contain every Astrodyne body exactly once")
        if len(placements) != len(set(placements)) or frozenset(placements) != _BODIES:
            raise ValueError("placements must contain every Astrodyne body exactly once")
        if set(self.birth_signs) != set(ASTRODYNE_SIGNS):
            raise ValueError("birth_signs must contain all twelve zodiac signs")
        if set(self.birth_houses) != set(range(1, 13)):
            raise ValueError("birth_houses must contain houses 1-12")
        return self


class ProgressedCarryResponse(_StrictModel):
    tier: str
    carry_factor: float
    carried_power: float
    carried_harmony: float
    carried_discord: float
    dignity_harmony: float
    dignity_discord: float
    manual_carried_power: float
    manual_total_harmony: float
    manual_total_discord: float


class ProgressedNormalBodyResponse(_StrictModel):
    body: str
    longitude_deg: float
    sign: str
    sign_degree: float
    house: int
    natal: ProgressedBaselineRequest
    dignity_delta: float
    carry: ProgressedCarryResponse


class ProgressedNormalAggregateResponse(_StrictModel):
    name: str
    baseline: ProgressedBaselineRequest
    occupants: tuple[str, ...]
    added_power: float
    added_harmony: float
    added_discord: float
    total_power: float
    total_harmony: float
    total_discord: float
    net_harmony: float


class ProgressedNormalResponse(_StrictModel):
    profiles: tuple[ProgressedNormalBodyResponse, ...]
    signs: tuple[ProgressedNormalAggregateResponse, ...]
    houses: tuple[ProgressedNormalAggregateResponse, ...]
    total_sign_power: float
    total_house_power: float
    total_sign_harmony: float
    total_house_harmony: float
    checksums_pass: bool


class ProgressedDatedAspectRequest(_StrictModel):
    relation_id: str = Field(min_length=1)
    body_a: str
    body_b: str
    aspect: str = Field(min_length=1)
    direct_terminal_ids: tuple[str, ...] = Field(min_length=1)
    indirect_terminal_ids: tuple[str, ...] = ()
    peak_power: float = Field(ge=0.0)
    distance_arcmin: float = Field(ge=0.0, le=60.0)

    @field_validator("body_a", "body_b")
    @classmethod
    def _body(cls, value: str) -> str:
        if value not in _BODIES:
            raise ValueError(f"unsupported Astrodyne body: {value!r}")
        return value

    @field_validator("peak_power", "distance_arcmin")
    @classmethod
    def _finite_values(cls, value: float) -> float:
        return _finite(value)


class ProgressedDatedAspectResponse(_StrictModel):
    relation_id: str
    body_a: str
    body_b: str
    aspect: str
    direct_terminal_ids: tuple[str, ...]
    indirect_terminal_ids: tuple[str, ...]
    peak_power: float
    distance_arcmin: float
    power: float
    harmony: float
    discord: float
    net_harmony: float


class ProgressedTerminalRequest(_StrictModel):
    body: str
    kind: Literal["radical", "major_progressed", "minor_progressed", "transit"]
    longitude_deg: float
    house_class: Literal["angular", "succedent", "cadent"]
    declination_deg: float | None = None

    @field_validator("body")
    @classmethod
    def _body(cls, value: str) -> str:
        if value not in _BODIES:
            raise ValueError(f"unsupported Astrodyne body: {value!r}")
        return value

    @field_validator("longitude_deg")
    @classmethod
    def _longitude(cls, value: float) -> float:
        return _finite(value)

    @field_validator("declination_deg")
    @classmethod
    def _declination(cls, value: float | None) -> float | None:
        if value is None:
            return None
        value = _finite(value)
        if not -90.0 <= value <= 90.0:
            raise ValueError("declination_deg must lie in [-90, 90]")
        return value


class ProgressedMajorRelationRequest(_StrictModel):
    direct_a: ProgressedTerminalRequest
    direct_b: ProgressedTerminalRequest
    counterpart_a: ProgressedTerminalRequest | None = None
    counterpart_b: ProgressedTerminalRequest | None = None
    natal_a: ProgressedNatalBodyRequest
    natal_b: ProgressedNatalBodyRequest
    aspect: str = Field(min_length=1)


class ProgressedAccessoryRelationRequest(_StrictModel):
    moving_terminal: ProgressedTerminalRequest
    target_terminal: ProgressedTerminalRequest
    target_counterpart: ProgressedTerminalRequest
    natal_moving: ProgressedNatalBodyRequest
    natal_target: ProgressedNatalBodyRequest
    aspect: str = Field(min_length=1)


class ProgressedRelationResponse(_StrictModel):
    relation_id: str
    aspect: str
    tier: str
    direct_terminal_ids: tuple[str, ...]
    indirect_terminal_ids: tuple[str, ...]
    distance_arcmin: float
    progressed_percentage: float
    peak_power: float
    manual_peak_power: float
    power: float
    manual_power: float
    harmony: float
    discord: float
    net_harmony: float
    detected: bool
    admitted: bool
    scored: bool


class ProgressedReenforcementRequest(_StrictModel):
    major: ProgressedMajorRelationRequest
    minor: ProgressedAccessoryRelationRequest


class ProgressedReenforcementResponse(_StrictModel):
    major_relation_id: str
    minor_relation_id: str
    target_terminal_id: str
    target_is_direct: bool
    terminal_factor: float
    progressed_percentage: float
    peak_power: float
    manual_peak_power: float
    reenforcement_power: float
    manual_reenforcement_power: float
    unreenforced_power: float
    reenforced_power: float
    manual_unreenforced_power: float
    manual_reenforced_power: float
    harmony_unchanged: float
    discord_unchanged: float


class ProgressedTerminalLocationRequest(_StrictModel):
    terminal_id: str
    sign: str
    house: int = Field(ge=1, le=12)

    @field_validator("sign")
    @classmethod
    def _sign(cls, value: str) -> str:
        if value not in ASTRODYNE_SIGNS:
            raise ValueError(f"unsupported sign: {value!r}")
        return value


class ProgressedMutualReceptionRequest(_StrictModel):
    allocation_id: str = Field(min_length=1)
    body: str
    direct_terminal_ids: tuple[str, ...]
    indirect_terminal_ids: tuple[str, ...]
    harmony: float = Field(default=2.5, ge=0.0)

    @field_validator("body")
    @classmethod
    def _planet(cls, value: str) -> str:
        if value not in ASTRODYNE_PLANETS:
            raise ValueError("mutual reception body must be a planet")
        return value

    @field_validator("harmony")
    @classmethod
    def _finite_harmony(cls, value: float) -> float:
        return _finite(value)


class ProgressedPracticalRequest(_StrictModel):
    normal: ProgressedNormalRequest
    aspects: tuple[ProgressedDatedAspectRequest, ...]
    terminal_locations: tuple[ProgressedTerminalLocationRequest, ...]
    house_cusp_signs: dict[int, str]
    intercepted_signs: dict[int, tuple[str, ...]] = Field(default_factory=dict)
    mutual_receptions: tuple[ProgressedMutualReceptionRequest, ...] = ()

    @model_validator(mode="after")
    def _figure(self) -> "ProgressedPracticalRequest":
        if set(self.house_cusp_signs) != set(range(1, 13)):
            raise ValueError("house_cusp_signs must contain houses 1-12")
        if any(sign not in ASTRODYNE_SIGNS for sign in self.house_cusp_signs.values()):
            raise ValueError("house_cusp_signs contains an unsupported sign")
        return self


class ProgressedPracticalContributionResponse(_StrictModel):
    source_id: str
    body: str
    channel: str
    factor: float
    power: float
    harmony: float
    discord: float
    net_harmony: float


class ProgressedPracticalAggregateResponse(_StrictModel):
    name: str
    normal_power: float
    normal_harmony: float
    normal_discord: float
    contributions: tuple[ProgressedPracticalContributionResponse, ...]
    added_power: float
    added_harmony: float
    added_discord: float
    total_power: float
    total_harmony: float
    total_discord: float
    net_harmony: float


class ProgressedPracticalResponse(_StrictModel):
    signs: tuple[ProgressedPracticalAggregateResponse, ...]
    houses: tuple[ProgressedPracticalAggregateResponse, ...]
    doctrine: Literal["church_of_light_progressed_astrodynes"]
    parity_status: Literal["doctrinal_parity_with_published_anomalies"]
    source_anomalies: tuple[str, ...]


class ProgressedTotalInfluenceRequest(_StrictModel):
    peak_power: float = Field(ge=0.0)
    peak_harmony: float = Field(ge=0.0)
    peak_discord: float = Field(ge=0.0)
    duration: float = Field(ge=0.0)
    unit: Literal["day", "month", "year"]

    @field_validator("peak_power", "peak_harmony", "peak_discord", "duration")
    @classmethod
    def _finite_values(cls, value: float) -> float:
        return _finite(value)


class ProgressedTotalInfluenceResponse(_StrictModel):
    unit: str
    duration: float
    average_factor: float
    peak_power: float
    peak_harmony: float
    peak_discord: float
    average_power: float
    average_harmony: float
    average_discord: float
    total_power: float
    total_harmony: float
    total_discord: float
    manual_average_power: float
    manual_average_harmony: float
    manual_average_discord: float
    manual_total_power: float
    manual_total_harmony: float
    manual_total_discord: float


class ProgressedCompoundDurationRequest(_StrictModel):
    years: int = Field(default=0, ge=0)
    months: int = Field(default=0, ge=0)
    days: float = Field(default=0.0, ge=0.0)

    @field_validator("days")
    @classmethod
    def _finite_days(cls, value: float) -> float:
        return _finite(value)


class ProgressedCompoundInfluenceRequest(_StrictModel):
    peak_power: float = Field(ge=0.0)
    peak_harmony: float = Field(ge=0.0)
    peak_discord: float = Field(ge=0.0)
    duration: ProgressedCompoundDurationRequest

    @field_validator("peak_power", "peak_harmony", "peak_discord")
    @classmethod
    def _finite_values(cls, value: float) -> float:
        return _finite(value)


class ProgressedCompoundQuantityResponse(_StrictModel):
    years: int
    months: int
    days: float


class ProgressedCompoundInfluenceResponse(_StrictModel):
    duration: ProgressedCompoundDurationRequest
    average_factor: float
    manual_average_power: float
    manual_average_harmony: float
    manual_average_discord: float
    power: ProgressedCompoundQuantityResponse
    harmony: ProgressedCompoundQuantityResponse
    discord: ProgressedCompoundQuantityResponse


__all__ = [name for name in globals() if name.startswith("Progressed")]
