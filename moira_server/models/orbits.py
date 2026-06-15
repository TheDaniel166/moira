"""Transport models for orbital-elements endpoints."""

from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict, field_validator

from moira.constants import Body


ADMITTED_ORBIT_BODIES = (
    Body.MERCURY,
    Body.VENUS,
    Body.EARTH,
    Body.MARS,
    Body.JUPITER,
    Body.SATURN,
    Body.URANUS,
    Body.NEPTUNE,
    Body.PLUTO,
)


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _OrbitBaseRequest(_StrictModel):
    body: str
    jd_ut: float

    @field_validator("body")
    @classmethod
    def _valid_body(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("body must be non-empty")
        if stripped not in ADMITTED_ORBIT_BODIES:
            supported = ", ".join(ADMITTED_ORBIT_BODIES)
            raise ValueError(f"body must be one of: {supported}")
        return stripped

    @field_validator("jd_ut")
    @classmethod
    def _finite_jd_ut(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("jd_ut must be finite")
        return value


class OrbitalElementsRequest(_OrbitBaseRequest):
    pass


class DistanceExtremesRequest(_OrbitBaseRequest):
    pass


class OrbitalElementsResponse(_StrictModel):
    name: str
    epoch_jd: float
    semi_major_axis_au: float
    eccentricity: float
    inclination_deg: float
    lon_ascending_node_deg: float
    arg_perihelion_deg: float
    mean_anomaly_deg: float
    mean_motion_deg_per_day: float
    orbital_period_days: float
    perihelion_distance_au: float
    aphelion_distance_au: float


class DistanceExtremesResponse(_StrictModel):
    name: str
    perihelion_jd: float
    perihelion_distance_au: float
    aphelion_jd: float
    aphelion_distance_au: float


class OrbitRequestEchoResponse(_StrictModel):
    body: str
    jd_ut: float


class OrbitTimeResponse(_StrictModel):
    input_time_scale: str = "UT_JD"
    state_evaluation_scale: str = "TT_internal"
    delta_t_policy: str = "engine_default"


class OrbitProvenanceResponse(_StrictModel):
    source_module: str = "moira.orbits"
    engine_entrypoint: str
    reader_owner: str
    center: str = "sun"
    frame: str = "J2000_ecliptic_and_equinox"
    orientation: str = "fixed_J2000_ecliptic"
    element_type: str = "osculating"
    state_source: str = "DE_series_kernel"
    position_basis: str = "heliocentric_state_vector"
    apparent_corrections: str = "not_applied"
    light_time_correction: str = "not_applied"
    mean_element_table: str = "not_used"
    event_basis: str | None = None
    search_direction: str | None = None
    search_owner: str | None = None
    perihelion_event: str | None = None
    aphelion_event: str | None = None
    chronological_order_forced: bool | None = None
    stage_sequence: list[str]


class OrbitalElementsEnvelopeResponse(_StrictModel):
    request: OrbitRequestEchoResponse
    time: OrbitTimeResponse
    elements: OrbitalElementsResponse
    provenance: OrbitProvenanceResponse


class DistanceExtremesEnvelopeResponse(_StrictModel):
    request: OrbitRequestEchoResponse
    time: OrbitTimeResponse
    distance_extremes: DistanceExtremesResponse
    provenance: OrbitProvenanceResponse
