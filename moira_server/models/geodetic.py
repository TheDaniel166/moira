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
from .relationship import AspectDataResponse, _OptionalAspectSetsRequest


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


# -- P10-03b analysis products: overlay, comparison, loci, chart houses -------
# docs/architecture/P10-03B_GEODETIC_ANALYSIS_TRANSPORT_DESIGN.md

GEODETIC_MAX_COMPARE_PLACES = 24
GEODETIC_LOCI_MAX_EVALUATIONS = 20000
GEODETIC_ANGLES = ("MC", "IC", "ASC", "DSC")
GeodeticAngleName = Literal["MC", "IC", "ASC", "DSC"]
ErrorPolicyName = Literal["raise", "collect"]


def _unique_angles(value: list[str]) -> list[str]:
    if not value:
        raise ValueError("angles must be non-empty")
    if len(set(value)) != len(value):
        raise ValueError("angles must be unique")
    return value


def _validate_bodies(value: list[str] | None) -> list[str] | None:
    if value is None:
        return value
    if not value:
        raise ValueError("bodies must be non-empty when supplied")
    if len(value) > GEODETIC_MAX_BODIES:
        raise ValueError(f"bodies may contain at most {GEODETIC_MAX_BODIES} entries")
    if any(not body or body != body.strip() for body in value):
        raise ValueError("bodies must be non-empty trimmed names")
    return value


def _chart_zodiac_policy(zodiac: str, ayanamsa_system: str | None) -> None:
    if zodiac == "sidereal" and ayanamsa_system is None:
        raise ValueError("sidereal zodiac requires ayanamsa_system")
    if zodiac == "tropical" and ayanamsa_system is not None:
        raise ValueError("tropical zodiac must not carry ayanamsa_system")


class GeodeticAspectPolicyModel(_OptionalAspectSetsRequest):
    """Same shape and law as AspectsFromLongitudesRequest's policy fields."""

    tier: Literal[0, 1, 2] = 1
    orb_factor: float = Field(default=1.0, gt=0.0, le=10.0)


class _GeodeticHouseFigureFields(_StrictModel):
    system: str = Field(min_length=1)
    # Absent means HousePolicy.strict(), the Geodetic owner's default.
    house_policy: HousePolicyRequest | None = None
    sun_longitude: float | None = None

    @field_validator("sun_longitude")
    @classmethod
    def _finite_sun(cls, value: float | None) -> float | None:
        return _finite(value, "sun_longitude")


class GeodeticPlaceModel(_StrictModel):
    location_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.:-]+$")
    geo_latitude: float = Field(gt=-_POLAR_LIMIT_DEG, lt=_POLAR_LIMIT_DEG)
    geo_longitude: float = Field(ge=-180.0, le=180.0)
    display_name: str | None = Field(default=None, min_length=1, max_length=128)

    @field_validator("geo_latitude", "geo_longitude")
    @classmethod
    def _finite_coordinates(cls, value: float) -> float:
        return _finite(value, "geographic coordinates")


class GeodeticCurvePolicyModel(_StrictModel):
    latitude_step_deg: float = Field(default=2.0, ge=0.5, le=10.0)
    max_evaluations: int = Field(
        default=GEODETIC_LOCI_MAX_EVALUATIONS, ge=1, le=GEODETIC_LOCI_MAX_EVALUATIONS, strict=True,
    )
    round_trip_tolerance_deg: float = Field(default=1e-7, gt=0.0, le=1e-3)


class _GeodeticDirectPositionsFields(_GeodeticZodiacPolicyRequest):
    """Caller-supplied TROPICAL longitudes in a declared frame; no ephemeris."""

    longitudes: dict[str, float]
    source_frame: str = Field(min_length=1, max_length=128)
    correction_regime: str = Field(default="caller_declared_unspecified", min_length=1, max_length=128)
    obliquity: float
    jd_ut1: float | None = None
    jd_tt: float | None = None

    @field_validator("longitudes")
    @classmethod
    def _bounded_longitudes(cls, value: dict[str, float]) -> dict[str, float]:
        _validate_longitude_map(value)
        return value

    @field_validator("obliquity")
    @classmethod
    def _earth_obliquity_envelope(cls, value: float) -> float:
        if not math.isfinite(value) or not _EARTH_OBLIQUITY_MIN_DEG <= value <= _EARTH_OBLIQUITY_MAX_DEG:
            raise ValueError("Earth obliquity must be finite and in [22, 25] degrees")
        return value

    @field_validator("jd_ut1", "jd_tt")
    @classmethod
    def _finite_epochs(cls, value: float | None) -> float | None:
        return _finite(value, "epochs")


class _GeodeticNatalFields(_StrictModel):
    """Chart-backed natal positions: engine reader at an aware datetime."""

    dt: datetime
    bodies: list[str] | None = None
    zodiac: ZodiacName = "tropical"
    ayanamsa_system: str | None = Field(default=None, min_length=1)
    body_error_policy: ErrorPolicyName = "raise"

    @field_validator("dt")
    @classmethod
    def _aware_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("dt must be timezone-aware")
        return value

    @field_validator("bodies")
    @classmethod
    def _bounded_bodies(cls, value: list[str] | None) -> list[str] | None:
        return _validate_bodies(value)

    @model_validator(mode="after")
    def _natal_zodiac_policy(self):
        _chart_zodiac_policy(self.zodiac, self.ayanamsa_system)
        return self


class _GeodeticOverlayFields(_GeodeticHouseFigureFields):
    geo_latitude: float = Field(gt=-_POLAR_LIMIT_DEG, lt=_POLAR_LIMIT_DEG)
    geo_longitude: float = Field(ge=-180.0, le=180.0)
    aspect_policy: GeodeticAspectPolicyModel
    angles: list[GeodeticAngleName] = Field(default_factory=lambda: list(GEODETIC_ANGLES))
    include_cusps: bool = False

    @field_validator("geo_latitude", "geo_longitude")
    @classmethod
    def _finite_place(cls, value: float) -> float:
        return _finite(value, "geographic coordinates")

    @field_validator("angles")
    @classmethod
    def _angles(cls, value: list[str]) -> list[str]:
        return _unique_angles(value)


class _GeodeticCompareFields(_GeodeticHouseFigureFields):
    places: list[GeodeticPlaceModel] = Field(min_length=1, max_length=GEODETIC_MAX_COMPARE_PLACES)
    aspect_policy: GeodeticAspectPolicyModel
    order_by: Literal["input", "minimum_contact_orb"] = "input"
    # Batch isolation (route admission checklist 4.2): one failing place never
    # masks the others unless the caller asks for raise.
    place_error_policy: ErrorPolicyName = "collect"

    @field_validator("places")
    @classmethod
    def _unique_places(cls, value: list[GeodeticPlaceModel]) -> list[GeodeticPlaceModel]:
        ids = [place.location_id for place in value]
        if len(set(ids)) != len(ids):
            raise ValueError("location_id values must be unique")
        return value


class _GeodeticLociFields(_StrictModel):
    angles: list[GeodeticAngleName] = Field(default_factory=lambda: list(GEODETIC_ANGLES))
    curve_policy: GeodeticCurvePolicyModel = Field(default_factory=GeodeticCurvePolicyModel)

    @field_validator("angles")
    @classmethod
    def _angles(cls, value: list[str]) -> list[str]:
        return _unique_angles(value)


class GeodeticChartBackedHousesRequest(_GeodeticHouseFigureFields):
    dt: datetime
    geo_latitude: float = Field(gt=-_POLAR_LIMIT_DEG, lt=_POLAR_LIMIT_DEG)
    geo_longitude: float = Field(ge=-180.0, le=180.0)
    zodiac: ZodiacName = "tropical"
    ayanamsa_system: str | None = Field(default=None, min_length=1)

    @field_validator("dt")
    @classmethod
    def _aware_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("dt must be timezone-aware")
        return value

    @field_validator("geo_latitude", "geo_longitude")
    @classmethod
    def _finite_place(cls, value: float) -> float:
        return _finite(value, "geographic coordinates")

    @model_validator(mode="after")
    def _houses_zodiac_policy(self):
        _chart_zodiac_policy(self.zodiac, self.ayanamsa_system)
        return self


class GeodeticChartBackedOverlayRequest(_GeodeticNatalFields, _GeodeticOverlayFields):
    pass


class GeodeticDirectOverlayRequest(_GeodeticDirectPositionsFields, _GeodeticOverlayFields):
    pass


class GeodeticChartBackedCompareRequest(_GeodeticNatalFields, _GeodeticCompareFields):
    pass


class GeodeticDirectCompareRequest(_GeodeticDirectPositionsFields, _GeodeticCompareFields):
    pass


class GeodeticChartBackedLociRequest(_GeodeticNatalFields, _GeodeticLociFields):
    pass


class GeodeticDirectLociRequest(_GeodeticDirectPositionsFields, _GeodeticLociFields):
    pass


# Responses


class GeodeticSmallBodyIdentityResponse(_StrictModel):
    family: str
    canonical_name: str
    naif_id: int
    matched_name: str
    is_alias: bool


class GeodeticBodyPositionResponse(_StrictModel):
    body_id: str
    requested_name: str
    display_name: str
    tropical_longitude_deg: float
    selected_longitude_deg: float
    identity: GeodeticSmallBodyIdentityResponse | None
    ecliptic_latitude_deg: float | None
    speed_deg_per_day: float | None


class GeodeticBodyFailureResponse(_StrictModel):
    requested_name: str
    body_id: str
    failure_type: str
    reason: str


class GeodeticSnapshotResponse(_StrictModel):
    positions: list[GeodeticBodyPositionResponse]
    failures: list[GeodeticBodyFailureResponse]
    source_kind: str
    source_frame: str
    correction_regime: str
    zodiac: ZodiacName
    ayanamsa_deg: float
    ayanamsa_system: str | None
    jd_ut1: float | None
    jd_tt: float | None
    resource_receipt_status: str
    complete: bool


class GeodeticHouseFigureResponse(_StrictModel):
    chart: GeodeticChartResponse
    targets: GeodeticAngleTargetsResponse
    houses: HousesResponse
    source_frame: str
    jd_ut1: float | None
    jd_tt: float | None
    ayanamsa_system: str | None


class GeodeticChartBackedHousesResponse(_StrictModel):
    figure: GeodeticHouseFigureResponse


class GeodeticPlacementResponse(_StrictModel):
    body_id: str
    house: int
    longitude: float
    exact_on_cusp: bool
    cusp_longitude: float


class GeodeticNamedLongitudeResponse(_StrictModel):
    name: str
    longitude: float


class GeodeticOverlayBodyResponse(_StrictModel):
    """Overlay without its snapshot (compare shares one snapshot)."""

    figure: GeodeticHouseFigureResponse
    placements: list[GeodeticPlacementResponse]
    contacts: list[AspectDataResponse]
    aspect_policy: GeodeticAspectPolicyModel
    target_longitudes: list[GeodeticNamedLongitudeResponse]
    coincident_targets: list[list[str]]
    placement_semantics: str
    complete: bool


class GeodeticOverlayResponse(_StrictModel):
    snapshot: GeodeticSnapshotResponse
    overlay: GeodeticOverlayBodyResponse


class GeodeticHouseChangeResponse(_StrictModel):
    body_id: str
    baseline_house: int
    house: int


class GeodeticContactKeyResponse(_StrictModel):
    body: str
    target: str
    aspect_angle_deg: float


class GeodeticPlaceDifferenceResponse(_StrictModel):
    baseline_id: str
    angle_deltas_deg: list[GeodeticNamedLongitudeResponse]
    house_changes: list[GeodeticHouseChangeResponse]
    added_contacts: list[GeodeticContactKeyResponse]
    removed_contacts: list[GeodeticContactKeyResponse]


class GeodeticPlaceResultResponse(_StrictModel):
    place: GeodeticPlaceModel
    overlay: GeodeticOverlayBodyResponse | None
    difference: GeodeticPlaceDifferenceResponse | None
    failure_type: str | None
    reason: str | None


class GeodeticCompareResponse(_StrictModel):
    snapshot: GeodeticSnapshotResponse
    results: list[GeodeticPlaceResultResponse]
    order_by: str
    baseline_id: str | None
    complete: bool


class GeodeticCurveVertexResponse(_StrictModel):
    latitude_deg: float
    longitude_deg: float
    residual_deg: float
    rising_rate: float | None
    boundary: str | None


class GeodeticCurveExclusionResponse(_StrictModel):
    latitude_deg: float
    reason: str


class GeodeticLocusResponse(_StrictModel):
    body_id: str
    angle: GeodeticAngleName
    tropical_target_deg: float
    selected_target_deg: float
    right_ascension_deg: float
    declination_deg: float
    segments: list[list[GeodeticCurveVertexResponse]]
    exclusions: list[GeodeticCurveExclusionResponse]
    analytic_definition: str
    complete: bool


class GeodeticLociResponse(_StrictModel):
    snapshot: GeodeticSnapshotResponse
    obliquity_deg: float
    curve_policy: GeodeticCurvePolicyModel
    loci: list[GeodeticLocusResponse]
    evaluations: int
    complete: bool
    semantics: str
    interpolation: str

# -- P10-03c timing: docs/architecture/P10-03C_GEODETIC_TIMING_TRANSPORT_DESIGN.md

GEODETIC_TIMING_MAX_SPAN_DAYS = 366
GEODETIC_TIMING_MAX_ASPECTS = 8
GEODETIC_TIMING_MAX_EVALUATIONS = 50000
GEODETIC_TIMING_MAX_SUBDIVISIONS = 10000
GEODETIC_TIMING_MAX_DEPTH = 12


def _aware(value: datetime, name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value


class GeodeticTimingAspectModel(_StrictModel):
    angle_deg: float = Field(ge=0.0, le=180.0)
    orb_deg: float = Field(ge=0.0, le=10.0)

    @field_validator("angle_deg", "orb_deg")
    @classmethod
    def _finite_aspect(cls, value: float) -> float:
        return _finite(value, "aspect values")


class GeodeticTimingPolicyModel(_StrictModel):
    step_days: float = Field(default=0.5, ge=0.25, le=5.0)
    max_evaluations: int = Field(
        default=GEODETIC_TIMING_MAX_EVALUATIONS, ge=1, le=GEODETIC_TIMING_MAX_EVALUATIONS, strict=True,
    )
    max_subdivisions: int = Field(
        default=GEODETIC_TIMING_MAX_SUBDIVISIONS, ge=1, le=GEODETIC_TIMING_MAX_SUBDIVISIONS, strict=True,
    )
    max_depth: int = Field(default=GEODETIC_TIMING_MAX_DEPTH, ge=1, le=GEODETIC_TIMING_MAX_DEPTH, strict=True)
    maximum_light_time_days: float = Field(default=1.0, gt=0.0, le=2.0)
    coverage_policy: Literal["require_full", "allow_partial"] = "require_full"

    @field_validator("step_days", "maximum_light_time_days")
    @classmethod
    def _finite_policy(cls, value: float) -> float:
        return _finite(value, "timing policy values")


class GeodeticChartBackedTransitsRequest(_StrictModel):
    geo_latitude: float = Field(gt=-_POLAR_LIMIT_DEG, lt=_POLAR_LIMIT_DEG)
    geo_longitude: float = Field(ge=-180.0, le=180.0)
    reference_dt: datetime
    mover: str = Field(min_length=1, max_length=64)
    start_dt: datetime
    end_dt: datetime
    aspects: list[GeodeticTimingAspectModel] = Field(min_length=1, max_length=GEODETIC_TIMING_MAX_ASPECTS)
    angles: list[GeodeticAngleName] = Field(default_factory=lambda: list(GEODETIC_ANGLES))
    zodiac: ZodiacName = "tropical"
    ayanamsa_system: str | None = Field(default=None, min_length=1)
    policy: GeodeticTimingPolicyModel = Field(default_factory=GeodeticTimingPolicyModel)

    @field_validator("geo_latitude", "geo_longitude")
    @classmethod
    def _finite_place(cls, value: float) -> float:
        return _finite(value, "geographic coordinates")

    @field_validator("reference_dt", "start_dt", "end_dt")
    @classmethod
    def _aware_datetimes(cls, value: datetime, info) -> datetime:
        return _aware(value, info.field_name)

    @field_validator("mover")
    @classmethod
    def _trimmed_mover(cls, value: str) -> str:
        if value != value.strip():
            raise ValueError("mover must be a trimmed name")
        return value

    @field_validator("aspects")
    @classmethod
    def _unique_aspects(cls, value: list[GeodeticTimingAspectModel]) -> list[GeodeticTimingAspectModel]:
        angles = [aspect.angle_deg for aspect in value]
        if len(set(angles)) != len(angles):
            raise ValueError("aspect angles must be unique")
        return value

    @field_validator("angles")
    @classmethod
    def _angles(cls, value: list[str]) -> list[str]:
        return _unique_angles(value)

    @model_validator(mode="after")
    def _span_and_lane(self):
        span = (self.end_dt - self.start_dt).total_seconds() / 86400.0
        if span <= 0:
            raise ValueError("end_dt must be after start_dt")
        if span > GEODETIC_TIMING_MAX_SPAN_DAYS:
            raise ValueError(f"timing span may be at most {GEODETIC_TIMING_MAX_SPAN_DAYS} days")
        _chart_zodiac_policy(self.zodiac, self.ayanamsa_system)
        return self


class GeodeticEpochResponse(_StrictModel):
    """A JD UT1 epoch (authoritative) with its UTC rendering."""

    jd_ut1: float
    datetime_utc: str


class GeodeticIntervalResponse(_StrictModel):
    start: GeodeticEpochResponse
    end: GeodeticEpochResponse


class GeodeticTimingReferenceResponse(_StrictModel):
    chart: GeodeticChartResponse
    selected_targets: list[GeodeticNamedLongitudeResponse]
    tropical_targets: list[GeodeticNamedLongitudeResponse]
    reference_jd_ut1: float
    reference_jd_tt: float | None
    angles: list[GeodeticAngleName]
    target_policy: str
    source_frame: str


class GeodeticTimingResourceResponse(_StrictModel):
    center: int
    target: int
    source_label: str
    source_sha256: str
    catalog_id: str | None
    catalog_version: str | None
    manifest_sha256: str | None
    intervals_tdb: list[list[float]]
    segment_boundaries_tdb: list[float]


class GeodeticTransitPassResponse(_StrictModel):
    body_id: str
    target: GeodeticAngleName
    aspect_angle_deg: float
    directed_angle_deg: float
    epoch: GeodeticEpochResponse
    motion: str
    residual_deg: float
    window_index: int | None


class GeodeticOrbWindowResponse(_StrictModel):
    body_id: str
    target: GeodeticAngleName
    aspect_angle_deg: float
    orb_deg: float
    covered: GeodeticIntervalResponse
    entry: GeodeticEpochResponse | None
    exit: GeodeticEpochResponse | None
    entry_status: str
    exit_status: str
    pass_indices: list[int]


class GeodeticEphemerisClockResponse(_StrictModel):
    jd_ut1: float
    epoch_tt: float
    epoch_tdb: float
    delta_t_seconds: float
    delta_t_correction_seconds: float
    tdb_minus_tt_seconds: float
    ephemeris_summary_label: str | None
    planetary_ephemeris: str | None
    lunar_ephemeris: str | None
    delta_t_source_product: str | None


class GeodeticTransitsResponse(_StrictModel):
    reference: GeodeticTimingReferenceResponse
    requested_mover: str
    body_id: str
    identity: GeodeticSmallBodyIdentityResponse | None
    policy: GeodeticTimingPolicyModel
    aspects: list[GeodeticTimingAspectModel]
    requested_interval: GeodeticIntervalResponse
    covered_intervals: list[GeodeticIntervalResponse]
    gaps: list[GeodeticIntervalResponse]
    scanned_intervals: list[GeodeticIntervalResponse]
    resources: list[GeodeticTimingResourceResponse]
    events: list[GeodeticTransitPassResponse]
    windows: list[GeodeticOrbWindowResponse]
    evaluations: int
    subdivisions: int
    complete: bool
    status: str
    reasons: list[str]
    ephemeris_clock: GeodeticEphemerisClockResponse
    timescale: str
    longitude_frame: str
    correction_regime: str
    completeness: str
    resource_semantics: str

__all__ = [
    "GEODETIC_TIMING_MAX_ASPECTS",
    "GEODETIC_TIMING_MAX_DEPTH",
    "GEODETIC_TIMING_MAX_EVALUATIONS",
    "GEODETIC_TIMING_MAX_SPAN_DAYS",
    "GEODETIC_TIMING_MAX_SUBDIVISIONS",
    "GeodeticChartBackedTransitsRequest",
    "GeodeticEphemerisClockResponse",
    "GeodeticEpochResponse",
    "GeodeticIntervalResponse",
    "GeodeticOrbWindowResponse",
    "GeodeticTimingAspectModel",
    "GeodeticTimingPolicyModel",
    "GeodeticTimingReferenceResponse",
    "GeodeticTimingResourceResponse",
    "GeodeticTransitPassResponse",
    "GeodeticTransitsResponse",
    "GEODETIC_ANGLES",
    "GEODETIC_LOCI_MAX_EVALUATIONS",
    "GEODETIC_MAX_COMPARE_PLACES",
    "GeodeticAspectPolicyModel",
    "GeodeticBodyFailureResponse",
    "GeodeticBodyPositionResponse",
    "GeodeticChartBackedCompareRequest",
    "GeodeticChartBackedHousesRequest",
    "GeodeticChartBackedHousesResponse",
    "GeodeticChartBackedLociRequest",
    "GeodeticChartBackedOverlayRequest",
    "GeodeticCompareResponse",
    "GeodeticContactKeyResponse",
    "GeodeticCurveExclusionResponse",
    "GeodeticCurvePolicyModel",
    "GeodeticCurveVertexResponse",
    "GeodeticDirectCompareRequest",
    "GeodeticDirectLociRequest",
    "GeodeticDirectOverlayRequest",
    "GeodeticHouseChangeResponse",
    "GeodeticHouseFigureResponse",
    "GeodeticLociResponse",
    "GeodeticLocusResponse",
    "GeodeticNamedLongitudeResponse",
    "GeodeticOverlayBodyResponse",
    "GeodeticOverlayResponse",
    "GeodeticPlaceDifferenceResponse",
    "GeodeticPlaceModel",
    "GeodeticPlaceResultResponse",
    "GeodeticPlacementResponse",
    "GeodeticSmallBodyIdentityResponse",
    "GeodeticSnapshotResponse",
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
