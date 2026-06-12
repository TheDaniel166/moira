"""Transport models for Phase-9 alternate dasha routes (P9-10)."""

from __future__ import annotations

import math
from typing import Literal

from pydantic import Field, field_validator, model_validator

from .common import _StrictModel
from .sidereal_context import SiderealChartBaseRequest, SiderealChartProvenanceResponse


YearBasis = Literal[
    "julian_365.25",
    "savana_360",
    "tropical_365.2422",
    "sidereal_365.2564",
]
AlternateDashaSystemName = Literal["ashtottari", "yogini"]


class AshtottariPolicyRequest(_StrictModel):
    year_basis: YearBasis = "julian_365.25"
    ayanamsa_system: str = "Lahiri"
    bypass_eligibility: bool = True
    lagna_sign_index: int | None = Field(default=None, ge=0, le=11)

    @field_validator("ayanamsa_system")
    @classmethod
    def _non_empty_ayanamsa_system(cls, value: str) -> str:
        if not value:
            raise ValueError("ayanamsa_system must be non-empty")
        return value


class YoginiPolicyRequest(_StrictModel):
    year_basis: YearBasis = "julian_365.25"
    ayanamsa_system: str = "Lahiri"

    @field_validator("ayanamsa_system")
    @classmethod
    def _non_empty_ayanamsa_system(cls, value: str) -> str:
        if not value:
            raise ValueError("ayanamsa_system must be non-empty")
        return value


class AshtottariSequenceRequest(_StrictModel):
    moon_tropical_lon: float
    natal_jd: float
    levels: int = Field(default=2, ge=1, le=4)
    policy: AshtottariPolicyRequest | None = None

    @field_validator("moon_tropical_lon", "natal_jd")
    @classmethod
    def _finite_inputs(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("moon_tropical_lon and natal_jd must be finite")
        return value


class YoginiSequenceRequest(_StrictModel):
    moon_tropical_lon: float
    natal_jd: float
    levels: int = Field(default=2, ge=1, le=4)
    policy: YoginiPolicyRequest | None = None

    @field_validator("moon_tropical_lon", "natal_jd")
    @classmethod
    def _finite_inputs(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("moon_tropical_lon and natal_jd must be finite")
        return value


class AshtottariChartSequenceRequest(SiderealChartBaseRequest):
    levels: int = Field(default=2, ge=1, le=4)
    policy: AshtottariPolicyRequest | None = None

    @model_validator(mode="after")
    def _policy_matches_chart_ayanamsa(self) -> "AshtottariChartSequenceRequest":
        if (
            self.policy is not None
            and self.policy.ayanamsa_system != self.ayanamsa_system
        ):
            raise ValueError("policy ayanamsa_system must match ayanamsa_system")
        return self


class YoginiChartSequenceRequest(SiderealChartBaseRequest):
    levels: int = Field(default=2, ge=1, le=4)
    policy: YoginiPolicyRequest | None = None

    @model_validator(mode="after")
    def _policy_matches_chart_ayanamsa(self) -> "YoginiChartSequenceRequest":
        if (
            self.policy is not None
            and self.policy.ayanamsa_system != self.ayanamsa_system
        ):
            raise ValueError("policy ayanamsa_system must match ayanamsa_system")
        return self


class AlternateDashaPeriodRequest(_StrictModel):
    system: AlternateDashaSystemName
    level: int = Field(ge=1)
    lord: str
    start_jd: float
    end_jd: float
    sub: list[AlternateDashaPeriodRequest] = Field(default_factory=list)

    @field_validator("lord")
    @classmethod
    def _non_empty_lord(cls, value: str) -> str:
        if not value:
            raise ValueError("lord must be non-empty")
        return value

    @field_validator("start_jd", "end_jd")
    @classmethod
    def _finite_jd(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("start_jd and end_jd must be finite")
        return value


AlternateDashaPeriodRequest.model_rebuild()


class AlternateDashaPeriodResponse(_StrictModel):
    system: str
    level: int
    lord: str
    start_jd: float
    end_jd: float
    years: float
    is_terminal: bool
    sub: list[AlternateDashaPeriodResponse] = Field(default_factory=list)


AlternateDashaPeriodResponse.model_rebuild()


class AlternatePeriodProfileResponse(_StrictModel):
    system: str
    level: int
    lord: str
    planet: str
    years: float
    is_node_lord: bool
    is_luminary_lord: bool


class AlternateDashaSequenceResponse(_StrictModel):
    system: str
    periods: list[AlternateDashaPeriodResponse]
    mahadasha_count: int
    levels_generated: int
    year_basis: str
    ayanamsa_system: str
    bypass_eligibility: bool | None = None
    lagna_sign_index: int | None = None


class AlternateDashaSequenceProfileResponse(_StrictModel):
    system: str
    total_years: int
    mahadasha_count: int
    profiles: list[AlternatePeriodProfileResponse]


class AlternateDashaProfileResponse(_StrictModel):
    sequence: AlternateDashaSequenceResponse
    profile: AlternateDashaSequenceProfileResponse


class AlternateDashaChartSequenceResponse(_StrictModel):
    result: AlternateDashaSequenceResponse
    moon_tropical_longitude: float
    natal_jd: float
    provenance: SiderealChartProvenanceResponse


class AlternateDashaChartProfileResponse(_StrictModel):
    result: AlternateDashaProfileResponse
    moon_tropical_longitude: float
    natal_jd: float
    provenance: SiderealChartProvenanceResponse


__all__ = [
    "AlternateDashaChartProfileResponse",
    "AlternateDashaChartSequenceResponse",
    "AlternateDashaPeriodRequest",
    "AlternateDashaPeriodResponse",
    "AlternateDashaProfileResponse",
    "AlternateDashaSequenceProfileResponse",
    "AlternateDashaSequenceResponse",
    "AlternateDashaSystemName",
    "AlternatePeriodProfileResponse",
    "AshtottariChartSequenceRequest",
    "AshtottariPolicyRequest",
    "AshtottariSequenceRequest",
    "YearBasis",
    "YoginiChartSequenceRequest",
    "YoginiPolicyRequest",
    "YoginiSequenceRequest",
]
