"""Strict source-policy contracts for opt-in hypothetical constructions."""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

from moira.hypothetical import ConventionClock, ProserpinaRule
from moira.orbits import OrbitalFrame
from .derived_points import FiniteNumber


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class ArtaInputsRequest(_StrictModel):
    lunar_node: FiniteNumber
    lunar_apogee: FiniteNumber
    solar_apogee: FiniteNumber
    input_model: Annotated[str, Field(min_length=1, max_length=200)]
    frame: Annotated[str, Field(min_length=1, max_length=200)]


class ArtaOsculatingRequest(_StrictModel):
    jd_ut: FiniteNumber
    frame: OrbitalFrame


class SelenaRequest(_StrictModel):
    epoch_jd: FiniteNumber
    anchor_jd: FiniteNumber
    anchor_longitude: FiniteNumber
    year_days: Annotated[float, Field(strict=True, ge=365, le=366)]
    timescale: ConventionClock
    frame: Annotated[str, Field(min_length=1, max_length=200)]


class ProserpinaRequest(_StrictModel):
    epoch_jd: FiniteNumber
    rule: ProserpinaRule
    timescale: ConventionClock
    frame: Annotated[str, Field(min_length=1, max_length=200)]


class PlanetNineScenarioRequest(_StrictModel):
    true_anomaly_deg: FiniteNumber
    source_equinox_jd_tt: FiniteNumber


class HistoricalPolicyRequest(_StrictModel):
    source_equinox_jd_tt: FiniteNumber
    timescale: ConventionClock
    epoch_hour: Annotated[float, Field(strict=True, ge=0, lt=24)]
    year_days: Annotated[float, Field(strict=True, ge=365, le=366)]


class _OrbitRequest(_StrictModel):
    epoch_jd: FiniteNumber
    frame: OrbitalFrame


class WaldemathRequest(_OrbitRequest):
    model: Literal["waldemath_koch_quoted_2006"]
    source_equinox_jd_tt: FiniteNumber
    berlin_local_minus_ut1_hours: Annotated[float, Field(strict=True, gt=-24, lt=24)]


class WestonRequest(_OrbitRequest):
    model: Literal["weston_stahl_1968"]
    source_equinox_jd_tt: FiniteNumber
    year_days: Annotated[float, Field(strict=True, ge=365, le=366)]


class HarringtonRequest(_OrbitRequest):
    model: Literal["harrington_1988"]
    policy: HistoricalPolicyRequest


class AdamsRequest(_OrbitRequest):
    model: Literal["adams_1846_second_hypothesis"]
    policy: HistoricalPolicyRequest
    uranus_semimajor_axis_au: Annotated[float, Field(strict=True, gt=0, allow_inf_nan=False)]
    uranus_sidereal_period_days: Annotated[float, Field(strict=True, gt=0, allow_inf_nan=False)]


class LeverrierRequest(_OrbitRequest):
    model: Literal["leverrier_1846_gould_1850"]
    policy: HistoricalPolicyRequest


HypotheticalOrbitRequest = Annotated[
    Union[WaldemathRequest, WestonRequest, HarringtonRequest, AdamsRequest, LeverrierRequest],
    Field(discriminator="model"),
]
