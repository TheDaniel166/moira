"""Strict transport models for Church of Light natal Astrodynes."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator, model_validator

from moira.astrodynes import ASTRODYNE_PLANETS, ASTRODYNE_POINTS
from moira.constants import HouseSystem

from .common import _StrictModel


_PLANET_SET = frozenset(ASTRODYNE_PLANETS)
_BODY_SET = frozenset((*ASTRODYNE_PLANETS, *ASTRODYNE_POINTS))


def _require_finite_mapping(name: str, value: dict[str, float]) -> dict[str, float]:
    invalid = sorted(key for key, item in value.items() if not math.isfinite(item))
    if invalid:
        raise ValueError(f"{name} values must be finite; invalid={invalid}")
    return value


class AstrodynesGeometryRequest(_StrictModel):
    """Complete tropical geometry accepted by the kernel-free route."""

    planet_longitudes: dict[str, float]
    declinations: dict[str, float]
    cusp_longitudes: tuple[float, ...] = Field(min_length=12, max_length=12)
    mc_longitude: float
    asc_longitude: float

    @field_validator("planet_longitudes")
    @classmethod
    def _planet_map(cls, value: dict[str, float]) -> dict[str, float]:
        if frozenset(value) != _PLANET_SET:
            missing = sorted(_PLANET_SET - frozenset(value))
            extra = sorted(frozenset(value) - _PLANET_SET)
            raise ValueError(
                "planet_longitudes must contain exactly the ten Astrodyne planets; "
                f"missing={missing}, extra={extra}"
            )
        return _require_finite_mapping("planet_longitudes", value)

    @field_validator("declinations")
    @classmethod
    def _declination_map(cls, value: dict[str, float]) -> dict[str, float]:
        if frozenset(value) != _BODY_SET:
            missing = sorted(_BODY_SET - frozenset(value))
            extra = sorted(frozenset(value) - _BODY_SET)
            raise ValueError(
                "declinations must contain ten planets plus M.C. and Asc.; "
                f"missing={missing}, extra={extra}"
            )
        _require_finite_mapping("declinations", value)
        invalid = sorted(key for key, item in value.items() if not -90.0 <= item <= 90.0)
        if invalid:
            raise ValueError(f"declinations must lie in [-90, 90]; invalid={invalid}")
        return value

    @field_validator("cusp_longitudes")
    @classmethod
    def _finite_cusps(cls, value: tuple[float, ...]) -> tuple[float, ...]:
        if not all(math.isfinite(item) for item in value):
            raise ValueError("cusp_longitudes must be finite")
        return value

    @field_validator("mc_longitude", "asc_longitude")
    @classmethod
    def _finite_angle(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("angle longitudes must be finite")
        return value

    @model_validator(mode="after")
    def _ordered_figure(self) -> "AstrodynesGeometryRequest":
        cusps = tuple(item % 360.0 for item in self.cusp_longitudes)
        spans = tuple(
            (cusps[(index + 1) % 12] - cusp) % 360.0
            for index, cusp in enumerate(cusps)
        )
        if any(span <= 1e-12 for span in spans) or abs(sum(spans) - 360.0) > 1e-9:
            raise ValueError("cusp_longitudes must form one ordered zodiacal circuit")

        def separation(first: float, second: float) -> float:
            return abs((first - second + 180.0) % 360.0 - 180.0)

        if separation(self.asc_longitude, cusps[0]) > 1e-9:
            raise ValueError("asc_longitude must equal cusp_longitudes[0]")
        if separation(self.mc_longitude, cusps[9]) > 1e-9:
            raise ValueError("mc_longitude must equal cusp_longitudes[9]")
        return self


class AstrodynesChartRequest(_StrictModel):
    """Chart-backed request with explicit location and house doctrine."""

    dt: datetime
    observer_lat: float = Field(ge=-90.0, le=90.0)
    observer_lon: float = Field(ge=-180.0, le=180.0)
    house_system: str = HouseSystem.PLACIDUS
    allow_house_fallback: bool = False

    @field_validator("dt")
    @classmethod
    def _aware_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("dt must be timezone-aware")
        return value

    @field_validator("observer_lat", "observer_lon")
    @classmethod
    def _finite_observer(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("observer coordinates must be finite")
        return value

    @field_validator("house_system")
    @classmethod
    def _house_system_nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("house_system must be non-empty")
        return value


class AstrodynePolicyResponse(_StrictModel):
    degree_emphasis_orb_deg: float
    parallel_orb_arcmin: float
    parallel_geometry: str
    mercury_orb_rule: str
    mutual_reception_bonus: float


class AstrodyneDignityRowResponse(_StrictModel):
    planet: str
    home_signs: tuple[str, ...]
    detriment_signs: tuple[str, ...]
    exaltation_sign: str
    exaltation_degree: float
    fall_sign: str
    fall_degree: float
    harmony_sign: str
    inharmony_sign: str


class AstrodyneHousePowerRowResponse(_StrictModel):
    house: int
    weaker_cusp_power: float
    stronger_cusp_power: float
    variation: float


class AstrodyneAspectOrbRowResponse(_StrictModel):
    aspect: str
    exact_angle_deg: float
    succedent_planet_deg: float
    succedent_luminary_deg: float
    angular_planet_deg: float
    angular_luminary_deg: float
    cadent_planet_deg: float
    cadent_luminary_deg: float


class AstrodyneSummaryGroupResponse(_StrictModel):
    family: str
    name: str
    houses: tuple[int, ...] = ()
    signs: tuple[str, ...] = ()


class AstrodynesDoctrineResponse(_StrictModel):
    doctrine: Literal["church_of_light_natal_astrodynes"]
    planets: tuple[str, ...]
    points: tuple[str, ...]
    signs: tuple[str, ...]
    house_classes: tuple[str, ...]
    policy: AstrodynePolicyResponse
    dignity_rows: tuple[AstrodyneDignityRowResponse, ...]
    house_power_rows: tuple[AstrodyneHousePowerRowResponse, ...]
    aspect_orb_rows: tuple[AstrodyneAspectOrbRowResponse, ...]
    summary_groups: tuple[AstrodyneSummaryGroupResponse, ...]


class AstrodynesGeometryResponse(_StrictModel):
    source_mode: Literal["explicit_geometry", "chart_backed"]
    dt: datetime | None = None
    observer_lat: float | None = None
    observer_lon: float | None = None
    jd_ut: float | None = None
    obliquity_deg: float | None = None
    planet_longitudes: dict[str, float]
    declinations: dict[str, float]
    cusp_longitudes: tuple[float, ...]
    mc_longitude: float
    asc_longitude: float
    requested_house_system: str | None = None
    effective_house_system: str | None = None
    house_fallback: bool = False
    house_fallback_reason: str | None = None


class AstrodyneBodyInputResponse(_StrictModel):
    body: str
    body_kind: str
    longitude_deg: float
    sign: str
    sign_degree: float
    house: int
    house_class: str
    distance_from_weaker_cusp_deg: float | None
    house_size_deg: float | None
    declination_deg: float | None


class AstrodyneContributionResponse(_StrictModel):
    source: str
    label: str
    power: float
    harmony: float
    discord: float


class AstrodyneHousePositionTruthResponse(_StrictModel):
    house: int
    distance_from_weaker_cusp_deg: float
    house_size_deg: float
    weaker_cusp_power: float
    stronger_cusp_power: float
    variation: float
    interpolation_fraction: float
    astrodyne_power: float


class AstrodyneEssentialDignityTruthResponse(_StrictModel):
    planet: str
    sign: str
    sign_degree: float
    source_row: AstrodyneDignityRowResponse
    condition: str | None
    exact_degree: float | None
    distance_from_exact_degree: float | None
    degree_emphasis_applied: bool
    harmony_delta: float


class AstrodyneZodiacalAspectTruthResponse(_StrictModel):
    body_a: str
    body_b: str
    longitude_a_deg: float
    longitude_b_deg: float
    house_class_a: str
    house_class_b: str
    aspect: str
    exact_angle_deg: float
    separation_deg: float
    distance_from_perfect_deg: float
    presence_orb_a_deg: float
    presence_orb_b_deg: float
    admitted_presence_orb_deg: float
    scoring_orb_a_deg: float
    scoring_orb_b_deg: float
    admitted_scoring_orb_deg: float
    within_orb: bool
    astrodyne_power: float


class AstrodyneParallelAspectTruthResponse(_StrictModel):
    body_a: str
    body_b: str
    declination_a_deg: float
    declination_b_deg: float
    house_class_a: str
    house_class_b: str
    magnitude_separation_arcmin: float
    orb_limit_arcmin: float
    perfect_conjunction_power_a: float
    perfect_conjunction_power_b: float
    scale_fraction: float
    scaled_power_a: float
    scaled_power_b: float
    within_orb: bool
    astrodyne_power: float


class AstrodyneNatureContributionResponse(_StrictModel):
    body: str
    fraction: float
    harmony: float
    discord: float


class AstrodyneAspectHarmonyTruthResponse(_StrictModel):
    body_a: str
    body_b: str
    aspect: str
    family: str
    astrodyne_power: float
    base_harmony: float
    base_discord: float
    nature_contributions: tuple[AstrodyneNatureContributionResponse, ...]
    total_harmony: float
    total_discord: float
    net_harmony: float


class AstrodyneMutualReceptionTruthResponse(_StrictModel):
    kind: str
    planet_a: str
    sign_a: str
    qualifying_signs_a: tuple[str, ...]
    planet_b: str
    sign_b: str
    qualifying_signs_b: tuple[str, ...]
    a_occupies_b_dignity: bool
    b_occupies_a_dignity: bool
    bonus_each: float


class AstrodyneRelationResponse(_StrictModel):
    relation_id: str
    kind: str
    body_a: str
    body_b: str
    label: str
    power: float
    harmony: float
    discord: float
    net_harmony: float
    detected: bool
    admitted: bool
    scored: bool
    power_truth: (
        AstrodyneZodiacalAspectTruthResponse
        | AstrodyneParallelAspectTruthResponse
        | None
    )
    harmony_truth: AstrodyneAspectHarmonyTruthResponse | None
    mutual_reception_truth: AstrodyneMutualReceptionTruthResponse | None


class AstrodyneBodyProfileResponse(_StrictModel):
    body: str
    body_kind: str
    sign: str
    house: int
    input: AstrodyneBodyInputResponse
    house_position_truth: AstrodyneHousePositionTruthResponse | None
    dignity_truth: AstrodyneEssentialDignityTruthResponse | None
    relation_ids: tuple[str, ...]
    contributions: tuple[AstrodyneContributionResponse, ...]
    total_power: float
    total_harmony: float
    total_discord: float
    net_harmony: float


class AstrodyneSignAggregateResponse(_StrictModel):
    sign: str
    rulers: tuple[str, ...]
    cusp_count: int
    intercepted_houses: tuple[int, ...]
    ruler_fraction: float
    occupants: tuple[str, ...]
    ruler_power: float
    occupant_power: float
    total_power: float
    total_harmony: float
    total_discord: float
    net_harmony: float


class AstrodyneHouseAggregateResponse(_StrictModel):
    house: int
    cusp_sign: str
    intercepted_signs: tuple[str, ...]
    occupants: tuple[str, ...]
    ruler_power: float
    occupant_power: float
    total_power: float
    total_harmony: float
    total_discord: float
    net_harmony: float


class AstrodyneAggregateResponse(_StrictModel):
    signs: tuple[AstrodyneSignAggregateResponse, ...]
    houses: tuple[AstrodyneHouseAggregateResponse, ...]
    total_body_power: float
    total_sign_power: float
    total_house_power: float
    total_sign_harmony: float
    total_house_harmony: float
    power_checksum_delta: float
    harmony_checksum_delta: float
    checksums_pass: bool


class AstrodyneSummaryEntryResponse(_StrictModel):
    family: str
    name: str
    houses: tuple[int, ...]
    signs: tuple[str, ...]
    power: float
    percentage: float
    total_harmony: float
    total_discord: float
    net_harmony: float


class AstrodyneSummaryResponse(_StrictModel):
    societies: tuple[AstrodyneSummaryEntryResponse, ...]
    trinities: tuple[AstrodyneSummaryEntryResponse, ...]
    elements: tuple[AstrodyneSummaryEntryResponse, ...]
    qualities: tuple[AstrodyneSummaryEntryResponse, ...]
    total_power: float


class AstrodyneNetworkNodeResponse(_StrictModel):
    body: str
    sign: str
    house: int
    power: float
    net_harmony: float


class AstrodyneNetworkEdgeResponse(_StrictModel):
    kind: str
    body_a: str
    body_b: str
    label: str
    power: float
    net_harmony: float
    scored: bool


class AstrodyneNetworkResponse(_StrictModel):
    nodes: tuple[AstrodyneNetworkNodeResponse, ...]
    edges: tuple[AstrodyneNetworkEdgeResponse, ...]


class AstrodynesProvenanceResponse(_StrictModel):
    doctrine: Literal["church_of_light_natal_astrodynes"]
    engine_entrypoint: str
    source_mode: Literal["explicit_geometry", "chart_backed"]
    planetary_frame: Literal["caller_supplied", "geocentric_apparent"]
    kernel_required: bool
    stage_sequence: tuple[str, ...]


class AstrodynesCalculationResponse(_StrictModel):
    geometry: AstrodynesGeometryResponse
    policy: AstrodynePolicyResponse
    inputs: tuple[AstrodyneBodyInputResponse, ...]
    relations: tuple[AstrodyneRelationResponse, ...]
    admitted_relation_count: int
    scored_relation_count: int
    profiles: tuple[AstrodyneBodyProfileResponse, ...]
    aggregate: AstrodyneAggregateResponse
    summary: AstrodyneSummaryResponse
    network: AstrodyneNetworkResponse
    validation_failures: tuple[str, ...]
    provenance: AstrodynesProvenanceResponse


__all__ = [
    "AstrodyneAggregateResponse",
    "AstrodyneAspectOrbRowResponse",
    "AstrodyneAspectHarmonyTruthResponse",
    "AstrodyneBodyInputResponse",
    "AstrodyneBodyProfileResponse",
    "AstrodyneContributionResponse",
    "AstrodyneDignityRowResponse",
    "AstrodyneEssentialDignityTruthResponse",
    "AstrodyneHouseAggregateResponse",
    "AstrodyneHousePowerRowResponse",
    "AstrodyneHousePositionTruthResponse",
    "AstrodyneMutualReceptionTruthResponse",
    "AstrodyneNatureContributionResponse",
    "AstrodyneNetworkEdgeResponse",
    "AstrodyneNetworkNodeResponse",
    "AstrodyneNetworkResponse",
    "AstrodynePolicyResponse",
    "AstrodyneParallelAspectTruthResponse",
    "AstrodyneRelationResponse",
    "AstrodyneSignAggregateResponse",
    "AstrodyneSummaryEntryResponse",
    "AstrodyneSummaryGroupResponse",
    "AstrodyneSummaryResponse",
    "AstrodyneZodiacalAspectTruthResponse",
    "AstrodynesCalculationResponse",
    "AstrodynesChartRequest",
    "AstrodynesDoctrineResponse",
    "AstrodynesGeometryRequest",
    "AstrodynesGeometryResponse",
    "AstrodynesProvenanceResponse",
]
