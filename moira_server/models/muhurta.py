"""Transport models for P-GAP-02 Muhurta routes."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator, model_validator

from .common import _StrictModel
from .panchanga import PanchangaPolicyRequest, PanchangaResultResponse


MuhurtaLabel = Literal["auspicious", "neutral", "inauspicious"]
MuhurtaPanchangaSource = Literal["direct_inputs", "chart_backed"]
MuhurtaScoreScale = Literal["engine_raw_unbounded"]
MuhurtaScoreDirection = Literal["higher_is_more_favorable_under_policy"]


class MuhurtaPolicyRequest(_StrictModel):
    weight_tithi: float = Field(default=1.0, strict=True)
    weight_vara: float = Field(default=1.0, strict=True)
    weight_nakshatra: float = Field(default=1.0, strict=True)
    weight_yoga: float = Field(default=1.5, strict=True)
    weight_karana: float = Field(default=0.8, strict=True)
    weight_tara: float = Field(default=1.0, strict=True)
    weight_chandra: float = Field(default=1.0, strict=True)

    @field_validator("weight_tithi", "weight_vara", "weight_nakshatra", "weight_yoga", "weight_karana", "weight_tara", "weight_chandra")
    @classmethod
    def _finite_non_negative_weight(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("Muhurta policy weights must be finite")
        if value < 0.0:
            raise ValueError("Muhurta policy weights must be non-negative")
        return value

    @model_validator(mode="after")
    def _engine_policy(self):
        from moira.muhurta import MuhurtaPolicy
        MuhurtaPolicy(**self.model_dump())
        return self


class MuhurtaDirectRequest(_StrictModel):
    sun_tropical_lon: float = Field(strict=True)
    moon_tropical_lon: float = Field(strict=True)
    jd: float = Field(strict=True)
    ayanamsa_system: str = "Lahiri"
    panchanga_policy: PanchangaPolicyRequest | None = None
    muhurta_policy: MuhurtaPolicyRequest | None = None

    @field_validator("sun_tropical_lon", "moon_tropical_lon", "jd")
    @classmethod
    def _finite_numeric_input(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("numeric Muhurta direct inputs must be finite")
        return value

    @field_validator("ayanamsa_system")
    @classmethod
    def _non_empty_ayanamsa(cls, value: str) -> str:
        if not value:
            raise ValueError("ayanamsa_system must be non-empty")
        return value


class MuhurtaChartRequest(_StrictModel):
    dt: datetime
    observer_lat: float | None = Field(default=None, strict=True, ge=-90.0, le=90.0)
    observer_lon: float | None = Field(default=None, strict=True, ge=-180.0, le=180.0)
    observer_elev_m: float = Field(default=0.0, strict=True)
    ayanamsa_system: str = "Lahiri"
    panchanga_policy: PanchangaPolicyRequest | None = None
    muhurta_policy: MuhurtaPolicyRequest | None = None

    @field_validator("dt", mode="before")
    @classmethod
    def _civil_datetime(cls, value):
        if not isinstance(value, (str, datetime)):
            raise ValueError("dt must be a timezone-aware civil datetime, not a numeric timestamp")
        return value

    @field_validator("dt")
    @classmethod
    def _aware_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("dt must be timezone-aware")
        return value

    @field_validator("observer_lat", "observer_lon", "observer_elev_m")
    @classmethod
    def _finite_observer_input(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("observer inputs must be finite")
        return value

    @field_validator("ayanamsa_system")
    @classmethod
    def _non_empty_ayanamsa(cls, value: str) -> str:
        if not value:
            raise ValueError("ayanamsa_system must be non-empty")
        return value

    @model_validator(mode="after")
    def _observer_pair_complete(self) -> "MuhurtaChartRequest":
        if (self.observer_lat is None) != (self.observer_lon is None):
            raise ValueError("observer_lat and observer_lon must be supplied together")
        return self


class MuhurtaRequestEchoResponse(_StrictModel):
    source: MuhurtaPanchangaSource
    dt: str | None = None
    sun_tropical_lon: float | None = None
    moon_tropical_lon: float | None = None
    jd: float | None = None
    observer_lat: float | None = None
    observer_lon: float | None = None
    observer_elev_m: float | None = None
    ayanamsa_system: str


class MuhurtaPolicyResponse(_StrictModel):
    rule_profile: Literal["moira.muhurta.existing_weighted_profile.v1"]
    weight_tithi: float
    weight_vara: float
    weight_nakshatra: float
    weight_yoga: float
    weight_karana: float
    weight_tara: float
    weight_chandra: float
    use_classical_ashubha_yoga: Literal[True] = True
    exposed_policy_fields: list[str]
    omitted_policy_fields: list[str]
    applied_policy_fields: list[str]
    reserved_policy_fields: list[str]


class MuhurtaClassificationResponse(_StrictModel):
    overall: MuhurtaLabel
    tithi: MuhurtaLabel
    vara: MuhurtaLabel
    nakshatra: MuhurtaLabel
    yoga: MuhurtaLabel
    karana: MuhurtaLabel
    reasons: list[str]


class MuhurtaScoreResponse(_StrictModel):
    total: float
    breakdown: dict[str, float]
    classification: MuhurtaClassificationResponse
    score_scale: MuhurtaScoreScale
    score_direction: MuhurtaScoreDirection

    @field_validator("total")
    @classmethod
    def _finite_total(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("Muhurta score total must be finite")
        return value

    @field_validator("breakdown")
    @classmethod
    def _finite_breakdown(cls, value: dict[str, float]) -> dict[str, float]:
        if any(not math.isfinite(score) for score in value.values()):
            raise ValueError("Muhurta score breakdown values must be finite")
        return value


class MuhurtaProvenanceResponse(_StrictModel):
    source_module: str
    engine_entrypoint: str
    panchanga_source: MuhurtaPanchangaSource
    panchanga_module: str
    chart_construction: str
    reader_owner: str
    western_electional_doctrine: Literal["not_admitted"]
    search_semantics: Literal["not_admitted"]
    activity_guidance: Literal["not_admitted"]
    score_scale: str
    vara_basis: Literal["jd_weekday", "civil_utc_weekday"]
    stage_sequence: list[str]


class MuhurtaClassificationEnvelopeResponse(_StrictModel):
    request: MuhurtaRequestEchoResponse
    panchanga: PanchangaResultResponse
    policy: MuhurtaPolicyResponse
    classification: MuhurtaClassificationResponse
    provenance: MuhurtaProvenanceResponse


class MuhurtaScoreEnvelopeResponse(_StrictModel):
    request: MuhurtaRequestEchoResponse
    panchanga: PanchangaResultResponse
    policy: MuhurtaPolicyResponse
    classification: MuhurtaClassificationResponse
    score: MuhurtaScoreResponse
    provenance: MuhurtaProvenanceResponse


class MuhurtaPersonalRequest(MuhurtaDirectRequest):
    """Direct Muhurta request personalized by the native's Moon.

    The transit Moon comes from ``moon_tropical_lon`` (converted sidereal);
    ``janma_moon_sidereal_lon`` supplies the natal Moon (janma nakshatra
    and rashi source).
    """

    janma_moon_sidereal_lon: float = Field(strict=True)

    @field_validator("janma_moon_sidereal_lon")
    @classmethod
    def _finite_janma_moon(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("janma_moon_sidereal_lon must be finite")
        return value


class TaraBalaResponse(_StrictModel):
    janma_nakshatra_index: int
    target_nakshatra_index: int
    count: int
    tara_number: int
    tara_name: str
    polarity: str
    favorable: bool


class ChandraBalaResponse(_StrictModel):
    janma_rashi_index: int
    transit_rashi_index: int
    house_from_moon: int
    polarity: str
    favorable: bool
    is_chandrashtama: bool


class MuhurtaPersonalScoreResponse(MuhurtaScoreResponse):
    """Natal-personalized score: generic score + tara/chandra overlays."""

    tara: TaraBalaResponse
    chandra: ChandraBalaResponse
    policy: MuhurtaPolicyResponse
    panchanga: PanchangaResultResponse
    janma_moon_sidereal_lon: float
    transit_moon_sidereal_lon: float
    provenance: MuhurtaProvenanceResponse


__all__ = [
    "ChandraBalaResponse",
    "MuhurtaPersonalRequest",
    "MuhurtaPersonalScoreResponse",
    "TaraBalaResponse",
    "MuhurtaChartRequest",
    "MuhurtaClassificationEnvelopeResponse",
    "MuhurtaClassificationResponse",
    "MuhurtaDirectRequest",
    "MuhurtaPolicyRequest",
    "MuhurtaPolicyResponse",
    "MuhurtaProvenanceResponse",
    "MuhurtaRequestEchoResponse",
    "MuhurtaScoreEnvelopeResponse",
    "MuhurtaScoreResponse",
]
