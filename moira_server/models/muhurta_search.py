"""Strict transport for the engine's bounded sampled Muhurta product."""
from math import isclose, ulp
from typing import Annotated, Literal

from pydantic import Field, model_validator

from moira.muhurta import MuhurtaPolicy
from moira.muhurta_search import MuhurtaSearchPolicy, _sample_grid
from moira.sidereal import Ayanamsa
from ._vedic_inputs import FiniteNumber
from .common import _StrictModel
from .muhurta import (
    MuhurtaPolicyRequest, MuhurtaPolicyResponse, MuhurtaScoreResponse,
    TaraBalaResponse, ChandraBalaResponse,
)
from .panchanga import PanchangaResultResponse


class MuhurtaSearchPolicyRequest(_StrictModel):
    ayanamsa_system: Literal[tuple(Ayanamsa.ALL)] = "Lahiri"
    muhurta_policy: MuhurtaPolicyRequest = Field(default_factory=MuhurtaPolicyRequest)
    step_minutes: Annotated[FiniteNumber, Field(ge=1, le=43200)] = 60.0
    min_score: FiniteNumber = 0.0
    max_results: Annotated[int, Field(strict=True, ge=1, le=128)] = 32

    def to_engine(self):
        return MuhurtaSearchPolicy(
            ayanamsa_system=self.ayanamsa_system,
            muhurta_policy=MuhurtaPolicy(**self.muhurta_policy.model_dump()),
            step_days=self.step_minutes / 1440,
            min_score=self.min_score, max_results=self.max_results,
        )


class MuhurtaSearchRequest(_StrictModel):
    start_jd_ut1: Annotated[FiniteNumber, Field(ge=-10_000_000, le=10_000_000)]
    end_jd_ut1: Annotated[FiniteNumber, Field(ge=-10_000_000, le=10_000_000)]
    janma_moon_sidereal_lon: FiniteNumber | None = None
    policy: MuhurtaSearchPolicyRequest = Field(default_factory=MuhurtaSearchPolicyRequest)
    include_samples: bool = Field(default=False, strict=True)

    @model_validator(mode="after")
    def _bounded_grid(self):
        policy = self.policy.to_engine()
        _sample_grid(self.start_jd_ut1, self.end_jd_ut1, policy.step_days)
        return self


class MuhurtaPrecomputedScoreRequest(_StrictModel):
    """Supply tropical chart geometry and explicitly separated UT1 and TT clocks."""

    jd_ut1: Annotated[FiniteNumber, Field(ge=-10_000_000, le=10_000_000)]
    jd_tt: Annotated[FiniteNumber, Field(ge=-10_000_000, le=10_000_000)]
    delta_t_seconds: FiniteNumber | None = None
    sun_tropical_longitude: FiniteNumber
    moon_tropical_longitude: FiniteNumber
    janma_moon_sidereal_lon: FiniteNumber | None = None
    ayanamsa_system: Literal[tuple(Ayanamsa.ALL)] = "Lahiri"
    muhurta_policy: MuhurtaPolicyRequest = Field(default_factory=MuhurtaPolicyRequest)

    @model_validator(mode="after")
    def _consistent_clock(self):
        if self.delta_t_seconds is not None:
            observed = (self.jd_tt - self.jd_ut1) * 86400
            precision = (ulp(self.jd_tt) + ulp(self.jd_ut1)) * 86400
            if not isclose(observed, self.delta_t_seconds, rel_tol=0.0, abs_tol=precision):
                raise ValueError("delta_t_seconds disagrees with the supplied UT1 and TT.")
        return self


class MuhurtaMomentResponse(_StrictModel):
    jd_ut1: float
    jd_tt: float
    jd_tdb: float | None
    delta_t_source: str
    clock_identity: str
    sun_tropical_longitude: float
    moon_tropical_longitude: float
    ayanamsa_degrees: float
    panchanga: PanchangaResultResponse
    score: MuhurtaScoreResponse
    tara: TaraBalaResponse | None
    chandra: ChandraBalaResponse | None


class MuhurtaSearchMomentResponse(MuhurtaMomentResponse):
    jd_tdb: float


class MuhurtaPrecomputedScoreResponse(MuhurtaMomentResponse):
    input_time_basis: Literal["supplied_ut1_tt"]
    delta_t_seconds: float
    janma_moon_sidereal_lon: float | None
    natal_mode: Literal["omitted", "tara_chandra"]
    policy: MuhurtaPolicyResponse


class MuhurtaSearchWindowResponse(_StrictModel):
    jd_start: float
    jd_end: float
    qualifying_jds: list[float]
    peak: MuhurtaSearchMomentResponse
    left_unqualified_jd: float | None
    right_unqualified_jd: float | None


class MuhurtaSearchPolicyResponse(_StrictModel):
    ayanamsa_system: str
    ayanamsa_mode: Literal["true"]
    muhurta_policy: MuhurtaPolicyResponse
    step_days: float
    min_score: float
    max_results: int
    max_samples: int
    max_span_days: float
    vara_basis: Literal["jd_weekday"]
    interval_semantics: Literal["consecutive_qualifying_samples"]


class MuhurtaSearchProvenanceResponse(_StrictModel):
    source_module: Literal["moira.muhurta_search"] = "moira.muhurta_search"
    engine_entrypoint: Literal["Moira.find_muhurta_windows"] = "Moira.find_muhurta_windows"
    judgment_module: Literal["moira.muhurta"] = "moira.muhurta"
    reader_owner: Literal["Moira engine instance"] = "Moira engine instance"
    longitude_origin: Literal["apparent_geocentric"] = "apparent_geocentric"
    longitude_frame: Literal["true_ecliptic_of_date"] = "true_ecliptic_of_date"
    range_endpoints: Literal["closed_samples"] = "closed_samples"
    rank_order: Literal["peak_score_descending_then_earlier_peak"] = "peak_score_descending_then_earlier_peak"
    exact_transitions: Literal["not_evaluated"] = "not_evaluated"
    local_sunrise_vara: Literal["not_evaluated"] = "not_evaluated"
    lagna_strength: Literal["not_evaluated"] = "not_evaluated"
    activity_guidance: Literal["not_admitted"] = "not_admitted"
    western_electional_doctrine: Literal["not_admitted"] = "not_admitted"
    score_scale: Literal["engine_raw_unbounded"] = "engine_raw_unbounded"


class MuhurtaSearchResponse(_StrictModel):
    start_jd_ut1: float
    end_jd_ut1: float
    janma_moon_sidereal_lon: float | None
    natal_mode: Literal["omitted", "tara_chandra"]
    policy: MuhurtaSearchPolicyResponse
    sample_count: int
    qualifying_sample_count: int
    observed_window_count: int
    returned_window_count: int
    truncated: bool
    windows: list[MuhurtaSearchWindowResponse]
    provenance: MuhurtaSearchProvenanceResponse


class MuhurtaSearchSampleResponse(_StrictModel):
    jd_ut1: float
    jd_tt: float
    jd_tdb: float
    clock_identity: str
    delta_t_source: str
    sun_tropical_longitude: float
    moon_tropical_longitude: float
    ayanamsa_degrees: float
    score_total: float


class MuhurtaSearchWithSamplesResponse(MuhurtaSearchResponse):
    samples: list[MuhurtaSearchSampleResponse]


__all__ = [
    "MuhurtaSearchPolicyRequest", "MuhurtaSearchRequest", "MuhurtaSearchMomentResponse",
    "MuhurtaSearchWindowResponse", "MuhurtaSearchPolicyResponse",
    "MuhurtaSearchProvenanceResponse", "MuhurtaSearchResponse",
]
