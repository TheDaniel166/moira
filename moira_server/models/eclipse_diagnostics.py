"""Strict transport contracts for opt-in eclipse evidence products.

All public Julian-day request and response epochs are explicitly UT1, except
fields explicitly named ``jd_tt``. No UTC conversion is implied. Incomplete
diagnostics retain their native status and never convert unresolved to absence.
"""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DiagnosticModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


JdUt1 = Annotated[float, Field(ge=-5_000_000, le=10_000_000)]
Latitude = Annotated[float, Field(ge=-90, le=90)]
Longitude = Annotated[float, Field(ge=-180, le=180)]
AngularTolerance = Annotated[float, Field(ge=1e-12, lt=0.1)]
Vector3 = tuple[float, float, float]
JdPair = Annotated[list[JdUt1], Field(min_length=2, max_length=2)]
LatitudePair = Annotated[list[Latitude], Field(min_length=2, max_length=2)]
LongitudePair = Annotated[list[Longitude], Field(min_length=2, max_length=2)]


class HybridDiagnosticRequest(DiagnosticModel):
    jd_start_ut1: JdUt1
    backward: bool = False
    max_evaluations: int = Field(default=512, ge=1, le=2048)


class HybridAxisWitnessResponse(DiagnosticModel):
    jd_ut1: float
    latitude_deg: float
    longitude_deg: float
    signed_radius_km: float
    sun_altitude_deg: float
    angular_radius_ratio_minus_one: float


class HybridTransitionResponse(DiagnosticModel):
    start_jd_ut1: float
    end_jd_ut1: float
    direction: Literal["annular_to_total", "total_to_annular"]
    width_seconds: float


class HybridDiagnosticResponse(DiagnosticModel):
    status: Literal["hybrid", "unresolved"]
    subtype: None = None
    reason: str
    event_jd_ut1: float
    instantaneous_type: str
    ephemeris_at_epoch: str
    ephemeris_reference_jd_ut1: float
    axis_interval_ut1: tuple[float, float] | None
    annular_witness: HybridAxisWitnessResponse | None
    total_witness: HybridAxisWitnessResponse | None
    transitions: list[HybridTransitionResponse]
    evaluation_count: int
    budget_exhausted: bool
    surface_policy: str = "zero-elevation WGS-84 ellipsoid"
    horizon_policy: str = "geometric Sun-center horizon without refraction"
    cone_policy: str = "native physical central cone, spherical limbs"
    transition_coverage_complete: Literal[False] = False
    time_scale: Literal["UT1"] = "UT1"

    @model_validator(mode="after")
    def validate_witnesses(self) -> HybridDiagnosticResponse:
        annular, total = self.annular_witness, self.total_witness
        if annular is not None and not (annular.signed_radius_km < 0 and annular.angular_radius_ratio_minus_one < 0):
            raise ValueError("annular witness must have both annular signs")
        if total is not None and not (total.signed_radius_km > 0 and total.angular_radius_ratio_minus_one > 0):
            raise ValueError("total witness must have both total signs")
        if (self.status == "hybrid") != (annular is not None and total is not None):
            raise ValueError("hybrid status requires, and unresolved cannot contain, both witnesses")
        return self


class LunarShadowCandidateRequest(DiagnosticModel):
    center_jd_ut1: JdUt1
    policy: Literal["danjon_angular", "static_finite_cone"]
    earth_radius_scale: float = Field(default=1.0, gt=0, le=10)
    window_days: float = Field(default=0.3, gt=0, le=1)
    coarse_step_seconds: float = Field(default=120, ge=10, le=3600)

    @model_validator(mode="after")
    def validate_policy_and_budget(self) -> LunarShadowCandidateRequest:
        if self.policy == "danjon_angular" and self.earth_radius_scale != 1.0:
            raise ValueError("earth_radius_scale applies only to static_finite_cone")
        if 2 * self.window_days * 86400 / self.coarse_step_seconds > 10_000:
            raise ValueError("contact window exceeds the 10000-cell request limit")
        return self


class LunarShadowGeometryResponse(DiagnosticModel):
    policy: Literal["danjon_angular", "static_finite_cone"]
    margin_unit: Literal["rad", "km"]
    axis_distance_km: float
    gamma: float
    separation_rad: float
    penumbral_margin: float
    umbral_margin: float
    total_margin: float
    penumbral_magnitude: float | None
    umbral_magnitude: float | None


class LunarContactsResponse(DiagnosticModel):
    p1_jd_ut1: float | None
    u1_jd_ut1: float | None
    u2_jd_ut1: float | None
    greatest_jd_ut1: float
    u3_jd_ut1: float | None
    u4_jd_ut1: float | None
    p4_jd_ut1: float | None


class LunarShadowEventResponse(DiagnosticModel):
    policy: Literal["danjon_angular", "static_finite_cone"]
    candidate_type: Literal["penumbral", "partial", "total"]
    greatest_jd_ut1: float
    axis_distance_minimum_jd_ut1: float
    angular_opposition_minimum_jd_ut1: float
    umbral_maximum_jd_ut1: float
    total_maximum_jd_ut1: float
    contacts: LunarContactsResponse
    geometry_at_greatest: LunarShadowGeometryResponse
    earth_radius_scale: float
    threshold_status: Literal["outside_tolerance", "numerical_tangency"]
    completeness_certified: Literal[False] = False


class LunarShadowCandidateResponse(DiagnosticModel):
    status: Literal["detected", "unresolved"]
    event: LunarShadowEventResponse | None
    reason: str | None
    ephemeris_at_epoch: str
    ephemeris_reference_jd_ut1: float
    vector_policy: str
    maximum_policy: str
    complete: Literal[False] = False
    time_scale: Literal["UT1"] = "UT1"

    @model_validator(mode="after")
    def validate_candidate(self) -> LunarShadowCandidateResponse:
        if self.status == "detected":
            if self.event is None or self.reason is not None:
                raise ValueError("detected candidate requires an event and no reason")
        elif self.event is not None or self.reason is None:
            raise ValueError("unresolved candidate requires no event and an explanatory reason")
        return self


class SolarVisibilitySiteRequest(DiagnosticModel):
    jd_ut1: JdUt1
    latitude_deg: Latitude
    longitude_deg: Longitude
    lunation: int | None = None
    tolerance_rad: AngularTolerance = 1e-12


class SolarDiscVisibilityResponse(DiagnosticModel):
    status: Literal["visible", "hidden", "disjoint", "tangent", "indeterminate"]
    maximum_altitude_rad: float | None
    maximum_direction: Vector3 | None
    witness_direction: Vector3 | None
    separation_margin_rad: float
    tolerance_rad: float
    margin_unit: Literal["rad"] = "rad"

    @model_validator(mode="after")
    def validate_witness(self) -> SolarDiscVisibilityResponse:
        if (self.status == "visible") != (self.witness_direction is not None):
            raise ValueError("only a visible result carries a strict common-ray witness")
        return self


class SolarVisibilitySiteResponse(DiagnosticModel):
    jd_ut1: float
    jd_tt: float
    latitude_deg: float
    longitude_deg: float
    lunation: int | None
    ephemeris: str
    surface_policy: str
    vector_policy: str
    horizon_policy: str
    sun_distance_km: float
    moon_distance_km: float
    geometry: SolarDiscVisibilityResponse
    time_scale: Literal["UT1"] = "UT1"


class SolarVisibilitySeed(DiagnosticModel):
    jd_ut1: JdUt1
    latitude_deg: Latitude
    longitude_deg: Longitude


class SolarVisibilityRefinementRequest(DiagnosticModel):
    seed: SolarVisibilitySeed
    time_bounds_ut1: JdPair
    latitude_bounds_deg: LatitudePair
    longitude_bounds_deg: LongitudePair
    max_iterations: int = Field(default=80, ge=1, le=256)
    time_tolerance_seconds: float = Field(default=1, gt=0, le=3600)
    angular_tolerance_deg: float = Field(default=0.001, gt=0, le=10)
    tolerance_rad: AngularTolerance = 1e-12
    lunation: int | None = None

    @model_validator(mode="after")
    def validate_domain(self) -> SolarVisibilityRefinementRequest:
        values = (self.seed.jd_ut1, self.seed.latitude_deg, self.seed.longitude_deg)
        for value, bounds in zip(values, (self.time_bounds_ut1, self.latitude_bounds_deg, self.longitude_bounds_deg)):
            lo, hi = bounds
            if hi < lo or not lo <= value <= hi:
                raise ValueError("bounds must be ordered and contain the seed")
        return self


class SolarVisibilityRefinementResponse(DiagnosticModel):
    status: Literal["witness_found", "unresolved"]
    witness: SolarVisibilitySiteResponse | None
    best_candidate: SolarVisibilitySiteResponse
    domain: tuple[tuple[float, float], tuple[float, float], tuple[float, float]]
    iterations: int
    evaluations: int
    converged: bool
    final_step_seconds: float
    final_step_latitude_deg: float
    final_step_longitude_deg: float
    complete: Literal[False] = False
    time_scale: Literal["UT1"] = "UT1"

    @model_validator(mode="after")
    def validate_witness(self) -> SolarVisibilityRefinementResponse:
        if self.status == "witness_found":
            if self.witness is None or self.witness.geometry.status != "visible":
                raise ValueError("witness_found requires a visible site witness")
        elif self.witness is not None:
            raise ValueError("unresolved refinement cannot carry a witness")
        return self


class ClippedCentralBoundaryRequest(DiagnosticModel):
    jd_ut1: JdUt1
    arc_samples: int = Field(default=65, ge=3, le=2049)


class ClippedBoundaryPointResponse(DiagnosticModel):
    latitude_deg: float
    longitude_deg: float
    xyz_itrf_km: Vector3


class ClippedCentralBoundaryGeometryResponse(DiagnosticModel):
    jd_ut1: float
    cone_arc: list[ClippedBoundaryPointResponse]
    horizon_arc: list[ClippedBoundaryPointResponse]
    horizon_model: str
    surface_model: str
    scope: str
    cone_model: str
    topology: str


class ClippedCentralBoundaryResponse(DiagnosticModel):
    status: Literal["candidate", "unresolved"]
    boundary: ClippedCentralBoundaryGeometryResponse | None
    reason: str | None
    complete: Literal[False] = False
    jd_ut1: float | None
    time_scale: Literal["UT1"] = "UT1"
    engine_version: str | None
    ephemeris_filename: str | None
    earth_equatorial_radius_km: float
    earth_polar_radius_km: float
    sun_radius_km: float
    moon_radius_km: float

    @model_validator(mode="after")
    def validate_candidate(self) -> ClippedCentralBoundaryResponse:
        if self.status == "candidate":
            if self.boundary is None or self.reason is not None:
                raise ValueError("candidate requires a boundary and no reason")
        elif self.boundary is not None or self.reason is None:
            raise ValueError("unresolved clipping requires no boundary and an explanatory reason")
        return self


class SweptCentralInteriorRequest(DiagnosticModel):
    latitude_deg: Latitude
    longitude_deg: Longitude
    times_ut1: list[JdUt1] = Field(min_length=1, max_length=1024)
    interval_ut1: JdPair
    lunation: int | None = None
    tolerance_rad: AngularTolerance = 1e-12

    @model_validator(mode="after")
    def validate_interval(self) -> SweptCentralInteriorRequest:
        lo, hi = self.interval_ut1
        if hi < lo or any(not lo <= t <= hi for t in self.times_ut1):
            raise ValueError("closed interval must be ordered and contain all sample times")
        return self


class CentralShadowInteriorResponse(DiagnosticModel):
    status: Literal["interior_witness", "unresolved"]
    phase: Literal["total", "annular"] | None
    central_margin_rad: float
    sun_altitude_rad: float
    separation_rad: float
    sun_radius_rad: float
    moon_radius_rad: float
    tolerance_rad: float

    @model_validator(mode="after")
    def validate_phase(self) -> CentralShadowInteriorResponse:
        if self.status == "interior_witness":
            if (self.phase is None or self.central_margin_rad <= self.tolerance_rad
                    or self.sun_altitude_rad <= self.tolerance_rad):
                raise ValueError("interior witness requires a phase and strict central/daylight margins")
        elif self.phase is not None:
            raise ValueError("unresolved geometry cannot identify a witnessed central phase")
        return self


class CentralShadowSnapshotResponse(DiagnosticModel):
    jd_ut1: float
    jd_tt: float
    ephemeris: str
    geometry: CentralShadowInteriorResponse


class SweptCentralInteriorResponse(DiagnosticModel):
    status: Literal["interior_witness", "unresolved"]
    witness: CentralShadowSnapshotResponse | None
    samples: list[CentralShadowSnapshotResponse]
    interval_ut1: tuple[float, float]
    latitude_deg: float
    longitude_deg: float
    lunation: int | None
    surface_policy: str
    vector_policy: str
    horizon_policy: str
    complete: Literal[False] = False
    time_scale: Literal["UT1"] = "UT1"

    @model_validator(mode="after")
    def validate_witness(self) -> SweptCentralInteriorResponse:
        if self.status == "interior_witness":
            if (self.witness is None or self.witness.geometry.status != "interior_witness"
                    or self.witness not in self.samples
                    or not self.interval_ut1[0] <= self.witness.jd_ut1 <= self.interval_ut1[1]):
                raise ValueError("interior status requires an included in-interval witness")
        elif self.witness is not None:
            raise ValueError("unresolved swept result cannot carry a witness")
        return self
