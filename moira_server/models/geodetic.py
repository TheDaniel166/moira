"""Transport models for Phase-10 Geodetic routes (P10-03)."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator, model_validator

from moira.geodetic import (
    _EARTH_OBLIQUITY_MAX_DEG,
    _EARTH_OBLIQUITY_MIN_DEG,
    _POLAR_REFUSAL_MARGIN_DEG,
)

from .chart import HousePolicyRequest, HousesResponse
from .common import _StrictModel


GEODETIC_MAX_BODIES = 12

# Derived from the engine's declared polar margin so transport admission and
# engine computation cannot diverge.
_POLAR_LIMIT_DEG = 90.0 - _POLAR_REFUSAL_MARGIN_DEG

ZodiacName = Literal["tropical", "sidereal"]
CoordinateSource = Literal[
    "direct_geographic_obliquity",
    "chart_epoch_obliquity",
    "direct_ecliptic_longitudes",
    "chart_tropical_longitudes",
    "chart_sidereal_longitudes",
]


class _GeodeticZodiacPolicyRequest(_StrictModel):
    zodiac: ZodiacName = "tropical"
    ayanamsa_deg: float | None = None

    @field_validator("ayanamsa_deg")
    @classmethod
    def _finite_ayanamsa(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("ayanamsa_deg must be finite")
        return value

    @model_validator(mode="after")
    def _complete_direct_zodiac_policy(self):
        if self.zodiac == "sidereal" and self.ayanamsa_deg is None:
            raise ValueError("sidereal zodiac requires ayanamsa_deg")
        # Transport has a true absent state (None), so supplying the offset at
        # all declares the sidereal lane — even 0.0.  The engine sees a float
        # and so refuses only a nonzero offset.
        if self.zodiac == "tropical" and self.ayanamsa_deg is not None:
            raise ValueError("tropical zodiac must not carry ayanamsa_deg")
        return self


class _GeodeticChartBackedPolicyRequest(_StrictModel):
    dt: datetime
    geo_longitude: float = Field(ge=-180.0, le=180.0)
    geo_latitude: float = Field(gt=-_POLAR_LIMIT_DEG, lt=_POLAR_LIMIT_DEG)
    zodiac: ZodiacName = "tropical"
    ayanamsa_system: str | None = None

    @field_validator("dt")
    @classmethod
    def _aware_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("dt must be timezone-aware")
        return value

    @field_validator("geo_longitude", "geo_latitude")
    @classmethod
    def _finite_coordinates(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("geographic coordinates must be finite")
        return value

    @field_validator("ayanamsa_system")
    @classmethod
    def _non_empty_ayanamsa_system(cls, value: str | None) -> str | None:
        if value is not None and not value:
            raise ValueError("ayanamsa_system must be non-empty when supplied")
        return value

    @model_validator(mode="after")
    def _complete_chart_zodiac_policy(self):
        if self.zodiac == "sidereal" and self.ayanamsa_system is None:
            raise ValueError("sidereal zodiac requires ayanamsa_system")
        if self.zodiac == "tropical" and self.ayanamsa_system is not None:
            raise ValueError("tropical zodiac must not carry ayanamsa_system")
        return self


class GeodeticDirectChartRequest(_GeodeticZodiacPolicyRequest):
    geo_longitude: float = Field(ge=-180.0, le=180.0)
    geo_latitude: float = Field(gt=-_POLAR_LIMIT_DEG, lt=_POLAR_LIMIT_DEG)
    obliquity: float

    @field_validator("geo_longitude", "geo_latitude", "obliquity")
    @classmethod
    def _finite_values(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("geodetic chart inputs must be finite")
        return value

    @field_validator("obliquity")
    @classmethod
    def _earth_obliquity_envelope(cls, value: float) -> float:
        if not _EARTH_OBLIQUITY_MIN_DEG <= value <= _EARTH_OBLIQUITY_MAX_DEG:
            raise ValueError("Earth obliquity must be in [22, 25] degrees")
        return value


class GeodeticChartBackedChartRequest(_GeodeticChartBackedPolicyRequest):
    pass


class GeodeticDirectEquivalentsRequest(_GeodeticZodiacPolicyRequest):
    longitudes: dict[str, float]

    @field_validator("longitudes")
    @classmethod
    def _valid_longitudes(cls, value: dict[str, float]) -> dict[str, float]:
        _validate_longitude_map(value)
        return value


class GeodeticChartBackedEquivalentsRequest(_GeodeticChartBackedPolicyRequest):
    bodies: list[str] | None = None

    @field_validator("bodies")
    @classmethod
    def _valid_bodies(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        if not value:
            raise ValueError("bodies must be non-empty when supplied")
        if len(value) > GEODETIC_MAX_BODIES:
            raise ValueError(f"bodies may contain at most {GEODETIC_MAX_BODIES} entries")
        if any(not body for body in value):
            raise ValueError("bodies entries must be non-empty")
        return value


class GeodeticChartResponse(_StrictModel):
    geo_latitude: float
    geo_longitude: float
    mc: float
    asc: float
    obliquity: float
    zodiac: ZodiacName
    ayanamsa_deg: float


class GeodeticEquivalentResponse(_StrictModel):
    body: str
    geographic_longitude: float


class GeodeticProvenanceResponse(_StrictModel):
    requested_datetime: str | None = None
    normalized_datetime_utc: str | None = None
    jd_ut: float | None = None
    jd_tt: float | None = None
    obliquity_deg: float | None = None
    zodiac: ZodiacName
    ayanamsa_system: str | None = None
    ayanamsa_deg: float
    requested_bodies: list[str] | None = None
    returned_bodies: list[str]
    coordinate_source: CoordinateSource
    stage_sequence: list[str]


class GeodeticChartEnvelopeResponse(_StrictModel):
    chart: GeodeticChartResponse
    provenance: GeodeticProvenanceResponse


class GeodeticEquivalentsResponse(_StrictModel):
    equivalents: list[GeodeticEquivalentResponse]
    provenance: GeodeticProvenanceResponse


def _validate_longitude_map(value: dict[str, float]) -> None:
    if not value:
        raise ValueError("longitudes must be non-empty")
    if len(value) > GEODETIC_MAX_BODIES:
        raise ValueError(f"longitudes may contain at most {GEODETIC_MAX_BODIES} entries")
    for body, longitude in value.items():
        if not body:
            raise ValueError("longitudes keys must be non-empty")
        if not math.isfinite(longitude):
            raise ValueError("longitude values must be finite")


# -- Kernel-free Geodetic analysis (moira.geodetic_analysis/_uncertainty) ----

# The engine's own default sampling budget is the transport ceiling.
GEODETIC_DIAGNOSTIC_MAX_EVALUATIONS = 4096


def _finite(value: float | None, name: str) -> float | None:
    if value is not None and not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


class GeodeticDirectHousesRequest(GeodeticDirectChartRequest):
    system: str = Field(min_length=1)
    # Absent means HousePolicy.strict(), the Geodetic owner's default; it is
    # not the chart routes' fallback default.
    policy: HousePolicyRequest | None = None
    sun_longitude: float | None = None

    @field_validator("sun_longitude")
    @classmethod
    def _finite_sun(cls, value: float | None) -> float | None:
        return _finite(value, "sun_longitude")


class GeodeticGeometryRequest(_StrictModel):
    # The full latitude range is admitted so the polar_refusal status is
    # observable; this route reports geometry rather than computing a chart.
    geo_longitude: float = Field(ge=-180.0, le=180.0)
    geo_latitude: float = Field(ge=-90.0, le=90.0)
    obliquity: float

    @field_validator("geo_longitude", "geo_latitude", "obliquity")
    @classmethod
    def _finite_values(cls, value: float) -> float:
        return _finite(value, "geometry inputs")

    @field_validator("obliquity")
    @classmethod
    def _earth_obliquity_envelope(cls, value: float) -> float:
        if not _EARTH_OBLIQUITY_MIN_DEG <= value <= _EARTH_OBLIQUITY_MAX_DEG:
            raise ValueError("Earth obliquity must be in [22, 25] degrees")
        return value


class GeodeticInputUncertaintyModel(_StrictModel):
    """Maximum absolute input deviations, in degrees."""

    longitude_deg: float = Field(default=0.0, ge=0.0)
    latitude_deg: float = Field(default=0.0, ge=0.0)
    obliquity_deg: float = Field(default=0.0, ge=0.0)

    @field_validator("longitude_deg", "latitude_deg", "obliquity_deg")
    @classmethod
    def _finite_deviation(cls, value: float) -> float:
        return _finite(value, "uncertainty deviations")


class GeodeticDiagnosticPolicyModel(_StrictModel):
    residual_tolerance_deg: float = Field(gt=0.0)
    max_evaluations: int = Field(
        default=GEODETIC_DIAGNOSTIC_MAX_EVALUATIONS,
        ge=1,
        le=GEODETIC_DIAGNOSTIC_MAX_EVALUATIONS,
        strict=True,
    )
    max_depth: int = Field(default=4, ge=0, le=12, strict=True)

    @field_validator("residual_tolerance_deg")
    @classmethod
    def _finite_tolerance(cls, value: float) -> float:
        return _finite(value, "residual_tolerance_deg")


class GeodeticSensitivityRequest(GeodeticDirectChartRequest):
    uncertainty: GeodeticInputUncertaintyModel


class GeodeticUncertaintyRequest(GeodeticDirectChartRequest):
    uncertainty: GeodeticInputUncertaintyModel
    policy: GeodeticDiagnosticPolicyModel


class GeodeticAngleTargetsResponse(_StrictModel):
    MC: float
    IC: float
    ASC: float
    DSC: float


class GeodeticHousesResponse(_StrictModel):
    chart: GeodeticChartResponse
    targets: GeodeticAngleTargetsResponse
    houses: HousesResponse
    source_frame: str
    provenance: GeodeticProvenanceResponse


class GeodeticGeometryResponse(_StrictModel):
    tropical_mc_deg: float
    armc_deg: float
    intersection_norm: float
    meridian_altitude_sine: float
    rising_rate: float | None
    asc_deg: float | None
    status: Literal[
        "regular", "ill_conditioned", "coincident_planes", "rising_branch_tie", "polar_refusal",
    ]
    policy: str
    roundoff_guard: float


class GeodeticAngleDerivativesResponse(_StrictModel):
    geo_longitude_deg: float
    geo_latitude_deg: float
    obliquity_deg: float


class GeodeticSensitivityResponse(_StrictModel):
    chart: GeodeticChartResponse
    uncertainty: GeodeticInputUncertaintyModel
    mc_derivatives: GeodeticAngleDerivativesResponse
    asc_derivatives: GeodeticAngleDerivativesResponse
    mc_linearized_radius_deg: float
    asc_linearized_radius_deg: float
    latitude_margin_to_pole_deg: float
    interpretation: Literal["first_order_local_not_a_bound"]


class GeodeticCircularArcResponse(_StrictModel):
    start_deg: float
    sweep_deg: float


class GeodeticUncertaintyResponse(_StrictModel):
    chart: GeodeticChartResponse
    uncertainty: GeodeticInputUncertaintyModel
    policy: GeodeticDiagnosticPolicyModel
    base_geometry: GeodeticGeometryResponse
    status: str
    reasons: list[str]
    linear_estimate: GeodeticSensitivityResponse | None
    sampled_max_deviation_deg: float | None
    sampled_max_residual_deg: float | None
    sampled_arc: GeodeticCircularArcResponse | None
    evaluations: int
    sampling_complete: bool
    interpretation: str
    sampling_scheme: str


__all__ = [
    "GEODETIC_DIAGNOSTIC_MAX_EVALUATIONS",
    "GEODETIC_MAX_BODIES",
    "CoordinateSource",
    "GeodeticAngleDerivativesResponse",
    "GeodeticAngleTargetsResponse",
    "GeodeticChartBackedChartRequest",
    "GeodeticChartBackedEquivalentsRequest",
    "GeodeticChartEnvelopeResponse",
    "GeodeticChartResponse",
    "GeodeticCircularArcResponse",
    "GeodeticDiagnosticPolicyModel",
    "GeodeticDirectChartRequest",
    "GeodeticDirectEquivalentsRequest",
    "GeodeticDirectHousesRequest",
    "GeodeticEquivalentResponse",
    "GeodeticEquivalentsResponse",
    "GeodeticGeometryRequest",
    "GeodeticGeometryResponse",
    "GeodeticHousesResponse",
    "GeodeticInputUncertaintyModel",
    "GeodeticProvenanceResponse",
    "GeodeticSensitivityRequest",
    "GeodeticSensitivityResponse",
    "GeodeticUncertaintyRequest",
    "GeodeticUncertaintyResponse",
    "ZodiacName",
]
