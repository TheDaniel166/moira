"""Transport models for Phase-9 alternate dasha routes (P9-10)."""

from __future__ import annotations

import math
from typing import Literal

from pydantic import Field, StrictBool, field_validator, model_validator

from moira.dasha_systems import ASHTOTTARI_SEQUENCE, YOGINI_SEQUENCE

from .common import _StrictModel
from ._vedic_inputs import FiniteNumber, KnownAyanamsa, SignIndex
from .sidereal_context import VedicSiderealChartRequest, SiderealChartProvenanceResponse


YearBasis = Literal[
    "julian_365.25",
    "savana_360",
    "tropical_365.2422",
    "sidereal_365.2564",
]
AlternateDashaSystemName = Literal["ashtottari", "yogini"]
# Same Julian-day interval tolerance as validate_alternate_dasha_output.
# Generated child endpoints accumulate binary64 rounding; never snap inputs.
ALTERNATE_PERIOD_INTERVAL_TOLERANCE_DAYS = 1e-6


class AshtottariPolicyRequest(_StrictModel):
    year_basis: YearBasis = "julian_365.25"
    ayanamsa_system: KnownAyanamsa = "Lahiri"
    bypass_eligibility: StrictBool = True
    lagna_sign_index: SignIndex | None = None

    @field_validator("ayanamsa_system")
    @classmethod
    def _non_empty_ayanamsa_system(cls, value: str) -> str:
        if not value:
            raise ValueError("ayanamsa_system must be non-empty")
        return value


class YoginiPolicyRequest(_StrictModel):
    year_basis: YearBasis = "julian_365.25"
    ayanamsa_system: KnownAyanamsa = "Lahiri"

    @field_validator("ayanamsa_system")
    @classmethod
    def _non_empty_ayanamsa_system(cls, value: str) -> str:
        if not value:
            raise ValueError("ayanamsa_system must be non-empty")
        return value


class AshtottariSequenceRequest(_StrictModel):
    moon_tropical_lon: FiniteNumber
    natal_jd: FiniteNumber
    levels: int = Field(default=2, strict=True, ge=1, le=4)
    policy: AshtottariPolicyRequest | None = None

    @field_validator("moon_tropical_lon", "natal_jd")
    @classmethod
    def _finite_inputs(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("moon_tropical_lon and natal_jd must be finite")
        return value


class YoginiSequenceRequest(_StrictModel):
    moon_tropical_lon: FiniteNumber
    natal_jd: FiniteNumber
    levels: int = Field(default=2, strict=True, ge=1, le=4)
    policy: YoginiPolicyRequest | None = None

    @field_validator("moon_tropical_lon", "natal_jd")
    @classmethod
    def _finite_inputs(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("moon_tropical_lon and natal_jd must be finite")
        return value


class AshtottariChartSequenceRequest(VedicSiderealChartRequest):
    levels: int = Field(default=2, strict=True, ge=1, le=4)
    policy: AshtottariPolicyRequest | None = None

    @model_validator(mode="after")
    def _policy_matches_chart_ayanamsa(self) -> "AshtottariChartSequenceRequest":
        if (
            self.policy is not None
            and self.policy.ayanamsa_system != self.ayanamsa_system
        ):
            raise ValueError("policy ayanamsa_system must match ayanamsa_system")
        return self


class YoginiChartSequenceRequest(VedicSiderealChartRequest):
    levels: int = Field(default=2, strict=True, ge=1, le=4)
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
    level: int = Field(strict=True, ge=1, le=4)
    lord: str
    start_jd: FiniteNumber
    end_jd: FiniteNumber
    full_start_jd: FiniteNumber | None = None
    full_end_jd: FiniteNumber | None = None
    year_days: FiniteNumber | None = None
    year_basis: str | None = None
    # Both admitted systems have eight lords per subdivision cycle.
    sub: list[AlternateDashaPeriodRequest] = Field(default_factory=list, max_length=8)

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

    @model_validator(mode="after")
    def _admitted_period_tree(self) -> "AlternateDashaPeriodRequest":
        from moira.dasha_systems import _validate_alternate_children
        lords = ASHTOTTARI_SEQUENCE if self.system == "ashtottari" else YOGINI_SEQUENCE
        if self.lord not in lords:
            raise ValueError(f"unrecognized {self.system} lord: {self.lord!r}")
        if self.start_jd >= self.end_jd:
            raise ValueError("start_jd must be < end_jd")
        if not math.isfinite(self.end_jd - self.start_jd):
            raise ValueError("period duration must be finite")
        _validate_alternate_children(self.to_engine(), require_complete=False)
        return self

    def to_engine(self):
        """Reconstruct once through the same owner used for tree admission."""
        from moira.dasha_systems import AlternateDashaPeriod

        return AlternateDashaPeriod(self.system, self.level, self.lord,
            self.start_jd, self.end_jd, [child.to_engine() for child in self.sub],
            self.full_start_jd, self.full_end_jd, self.year_days, self.year_basis)


AlternateDashaPeriodRequest.model_rebuild()


class AlternateDashaPeriodResponse(_StrictModel):
    system: str
    level: int
    lord: str
    start_jd: float
    end_jd: float
    full_start_jd: float | None = None
    full_end_jd: float | None = None
    year_days: float | None = None
    year_basis: str | None = None
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
