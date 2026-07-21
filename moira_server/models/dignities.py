"""Transport models for Phase-9 Classical Dignities route family (P9-04)."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any

from pydantic import Field, field_validator, model_validator

from moira.constants import HouseSystem
from moira.dignities_types import (
    EssentialDignityDoctrine,
    MercurySectModel,
)

from .common import _StrictModel


_SEVEN_PLANETS = frozenset(
    {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"}
)
_MODERN_DIGNITY_PLANETS = _SEVEN_PLANETS | frozenset({"Uranus", "Neptune", "Pluto"})


class EssentialDignityPolicyRequest(_StrictModel):
    doctrine: EssentialDignityDoctrine = EssentialDignityDoctrine.TRADITIONAL_CLASSIC_7


class SolarConditionPolicyRequest(_StrictModel):
    include_cazimi: bool = True
    include_combust: bool = True
    include_under_sunbeams: bool = True
    include_for_luminaries: bool = False


class MutualReceptionPolicyRequest(_StrictModel):
    include_domicile: bool = True
    include_exaltation: bool = True


class SectHayzPolicyRequest(_StrictModel):
    mercury_sect_model: MercurySectModel = MercurySectModel.LONGITUDE_HEURISTIC
    include_hayz: bool = True


class AccidentalDignityPolicyRequest(_StrictModel):
    include_house_strength: bool = True
    include_motion: bool = True
    solar: SolarConditionPolicyRequest = Field(default_factory=SolarConditionPolicyRequest)
    mutual_reception: MutualReceptionPolicyRequest = Field(default_factory=MutualReceptionPolicyRequest)
    sect: SectHayzPolicyRequest = Field(default_factory=SectHayzPolicyRequest)


class DignityComputationPolicyRequest(_StrictModel):
    essential: EssentialDignityPolicyRequest = Field(default_factory=EssentialDignityPolicyRequest)
    accidental: AccidentalDignityPolicyRequest = Field(default_factory=AccidentalDignityPolicyRequest)


class DignitiesChartRequest(_StrictModel):
    """Chart-backed dignity request deriving chart truth through Moira."""

    dt: datetime
    observer_lat: float = Field(ge=-90.0, le=90.0)
    observer_lon: float = Field(ge=-180.0, le=180.0)
    observer_elev_m: float = 0.0
    house_system: str = HouseSystem.PLACIDUS
    policy: DignityComputationPolicyRequest | None = None

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

    @field_validator("house_system")
    @classmethod
    def _non_empty_house_system(cls, value: str) -> str:
        if not value:
            raise ValueError("house_system must be non-empty")
        return value


class DignitiesConditionChartRequest(DignitiesChartRequest):
    """Chart-backed dignity condition request for one classical planet."""

    planet: str

    @field_validator("planet")
    @classmethod
    def _valid_condition_planet(cls, value: str) -> str:
        if value not in _MODERN_DIGNITY_PLANETS:
            supported = ", ".join(sorted(_MODERN_DIGNITY_PLANETS))
            raise ValueError(f"planet must be one of: {supported}")
        return value

    @model_validator(mode="after")
    def _planet_supported_by_policy(self) -> "DignitiesConditionChartRequest":
        doctrine = (
            EssentialDignityDoctrine.TRADITIONAL_CLASSIC_7
            if self.policy is None
            else self.policy.essential.doctrine
        )
        if self.planet not in _SEVEN_PLANETS and doctrine is not EssentialDignityDoctrine.MODERN_CO_RULERS:
            raise ValueError("outer-planet dignity conditions require policy.essential.doctrine='modern_co_rulers'")
        return self


class PlanetaryReceptionResponse(_StrictModel):
    receiving_planet: str
    host_planet: str
    basis: str
    mode: str
    receiving_sign: str
    host_sign: str
    host_matching_signs: tuple[str, ...]
    is_mutual: bool


class PlanetaryConditionProfileResponse(_StrictModel):
    planet: str
    essential_truth: dict[str, Any] | None
    essential_classification: dict[str, Any] | None
    accidental_truth: dict[str, Any]
    accidental_classification: dict[str, Any]
    sect_truth: dict[str, Any] | None
    sect_classification: dict[str, Any] | None
    solar_truth: dict[str, Any]
    solar_classification: dict[str, Any]
    all_receptions: tuple[PlanetaryReceptionResponse, ...]
    admitted_receptions: tuple[PlanetaryReceptionResponse, ...]
    scored_receptions: tuple[PlanetaryReceptionResponse, ...]
    mutual_reception_truth: tuple[dict[str, Any], ...]
    reception_classification: tuple[dict[str, Any], ...]
    strengthening_count: int
    weakening_count: int
    neutral_count: int
    state: str


class PlanetaryDignityResponse(_StrictModel):
    planet: str
    sign: str
    degree: float
    house: int
    essential_dignity: str
    essential_score: int
    accidental_dignities: tuple[str, ...]
    accidental_score: int
    total_score: int
    is_retrograde: bool
    essential_truth: dict[str, Any] | None
    accidental_truth: dict[str, Any]
    sect_truth: dict[str, Any] | None
    solar_truth: dict[str, Any]
    all_receptions: tuple[PlanetaryReceptionResponse, ...]
    admitted_receptions: tuple[PlanetaryReceptionResponse, ...]
    scored_receptions: tuple[PlanetaryReceptionResponse, ...]
    mutual_reception_truth: tuple[dict[str, Any], ...]
    essential_classification: dict[str, Any] | None
    accidental_classification: dict[str, Any]
    sect_classification: dict[str, Any] | None
    solar_classification: dict[str, Any]
    reception_classification: tuple[dict[str, Any], ...]
    condition_profile: PlanetaryConditionProfileResponse | None


class DignitiesResultResponse(_StrictModel):
    dignities: tuple[PlanetaryDignityResponse, ...]


class ChartConditionProfileResponse(_StrictModel):
    profiles: tuple[PlanetaryConditionProfileResponse, ...]
    reinforced_count: int
    mixed_count: int
    weakened_count: int
    strengthening_total: int
    weakening_total: int
    neutral_total: int
    strongest_planets: tuple[str, ...]
    weakest_planets: tuple[str, ...]
    essential_strengthening_total: int
    essential_weakening_total: int
    accidental_strengthening_total: int
    accidental_weakening_total: int
    reception_participation_total: int
    strongest_count: int
    weakest_count: int


class ConditionNetworkNodeResponse(_StrictModel):
    planet: str
    profile: PlanetaryConditionProfileResponse
    incoming_count: int
    outgoing_count: int
    mutual_count: int
    total_degree: int
    is_isolated: bool


class ConditionNetworkEdgeResponse(_StrictModel):
    source_planet: str
    target_planet: str
    basis: str
    mode: str
    is_mutual: bool


class ConditionNetworkProfileResponse(_StrictModel):
    nodes: tuple[ConditionNetworkNodeResponse, ...]
    edges: tuple[ConditionNetworkEdgeResponse, ...]
    isolated_planets: tuple[str, ...]
    most_connected_planets: tuple[str, ...]
    mutual_edge_count: int
    unilateral_edge_count: int
    node_count: int
    edge_count: int


class DignitiesReceptionsResponse(_StrictModel):
    receptions: tuple[PlanetaryReceptionResponse, ...]


class DignitiesConditionsResponse(_StrictModel):
    profiles: tuple[PlanetaryConditionProfileResponse, ...]


__all__ = [
    "AccidentalDignityPolicyRequest",
    "ChartConditionProfileResponse",
    "ConditionNetworkEdgeResponse",
    "ConditionNetworkNodeResponse",
    "ConditionNetworkProfileResponse",
    "DignitiesChartRequest",
    "DignitiesConditionChartRequest",
    "DignitiesConditionsResponse",
    "DignitiesReceptionsResponse",
    "DignitiesResultResponse",
    "DignityComputationPolicyRequest",
    "EssentialDignityPolicyRequest",
    "MutualReceptionPolicyRequest",
    "PlanetaryConditionProfileResponse",
    "PlanetaryDignityResponse",
    "PlanetaryReceptionResponse",
    "SectHayzPolicyRequest",
    "SolarConditionPolicyRequest",
]
