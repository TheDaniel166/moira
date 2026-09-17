"""Transport models for planetary and small-body node endpoints."""

from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict, Field, field_validator

from moira._strenum import StrEnum

from .orbits import (
    OrbitalFrameConstructionResponse,
    OrbitalGravityResponse,
    OrbitalStateSourceResponse,
    OrbitTimeResponse,
)


MEAN_PLANETARY_NODE_MAX_ITEMS = 8


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NodeComputationMethod(StrEnum):
    mean_elements = "mean_elements"
    geometric_osculating = "geometric_osculating"


class OrbitalNodeResponse(_StrictModel):
    body: str
    ascending_node: float
    descending_node: float
    perihelion: float
    aphelion: float
    inclination: float
    eccentricity: float
    semi_major_axis: float


class MeanPlanetaryNodeRequest(_StrictModel):
    planet: str
    jd: float

    @field_validator("planet")
    @classmethod
    def _valid_planet(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("planet must be non-empty")
        return stripped

    @field_validator("jd")
    @classmethod
    def _finite_jd(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("jd must be finite")
        return value

    @field_validator("jd", mode="before")
    @classmethod
    def _jd_is_not_boolean(cls, value):
        if isinstance(value, bool):
            raise ValueError("jd must be a real number, not a Boolean")
        return value


class MeanPlanetaryNodesBulkRequest(_StrictModel):
    jd: float
    planets: list[str] | None = Field(
        default=None,
        min_length=1,
        max_length=MEAN_PLANETARY_NODE_MAX_ITEMS,
    )

    @field_validator("jd")
    @classmethod
    def _finite_jd(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("jd must be finite")
        return value

    @field_validator("jd", mode="before")
    @classmethod
    def _jd_is_not_boolean(cls, value):
        if isinstance(value, bool):
            raise ValueError("jd must be a real number, not a Boolean")
        return value

    @field_validator("planets")
    @classmethod
    def _valid_planets(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        cleaned: list[str] = []
        for planet in value:
            stripped = planet.strip()
            if not stripped:
                raise ValueError("planets entries must be non-empty")
            cleaned.append(stripped)
        return cleaned


class GeometricNodeRequest(_StrictModel):
    body: str
    jd_ut: float

    @field_validator("body")
    @classmethod
    def _valid_body(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("body must be non-empty")
        return stripped

    @field_validator("jd_ut")
    @classmethod
    def _finite_jd_ut(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("jd_ut must be finite")
        return value

    @field_validator("jd_ut", mode="before")
    @classmethod
    def _jd_ut_is_not_boolean(cls, value):
        if isinstance(value, bool):
            raise ValueError("jd_ut must be a real number, not a Boolean")
        return value


class NodeCatalogItemResponse(_StrictModel):
    name: str
    methods: list[NodeComputationMethod]
    mean_requires_kernel: bool | None = None
    geometric_requires_kernel: bool | None = None
    notes: list[str]


class NodeCatalogProvenanceResponse(_StrictModel):
    catalog_scope: str = "admitted_planetary_node_transport"
    mean_element_source: str = "moira.planetary_nodes mean Meeus/Simon element table"
    geometric_source: str = (
        "moira.orbits strict Sun-centered true-date osculating core, "
        "adapted by moira.planetary_nodes"
    )
    stage_sequence: list[str]


class NodeCatalogResponse(_StrictModel):
    bodies: list[NodeCatalogItemResponse]
    total: int
    provenance: NodeCatalogProvenanceResponse


class NodeProvenanceResponse(_StrictModel):
    method: NodeComputationMethod
    requested_body: str
    returned_body: str
    jd: float
    jd_scale: str
    frame: str
    coordinate_basis: str
    kernel_required: bool
    kernel_source: str
    validity_note: str
    source_module: str = "moira.planetary_nodes"
    stage_sequence: list[str]


class NodeResponse(_StrictModel):
    node: OrbitalNodeResponse
    provenance: NodeProvenanceResponse


class GeometricNodeProvenanceResponse(NodeProvenanceResponse):
    """Allowlisted strict-core receipt for one geometric node."""

    center: str
    body_naif_id: int
    body_kind: str
    time: OrbitTimeResponse
    gravity: OrbitalGravityResponse
    frame_construction: OrbitalFrameConstructionResponse
    state_source: OrbitalStateSourceResponse
    singularity_policy: str
    undefined_element_policy: str


class GeometricNodeResponse(_StrictModel):
    node: OrbitalNodeResponse
    provenance: GeometricNodeProvenanceResponse


class MeanPlanetaryNodesBulkProvenanceResponse(_StrictModel):
    method: NodeComputationMethod = NodeComputationMethod.mean_elements
    requested_planets: list[str]
    returned_planets: list[str]
    jd: float
    jd_scale: str = "TT_or_UT_negligible_for_slow_mean_elements"
    frame: str = "heliocentric_tropical_ecliptic"
    coordinate_basis: str = "Meeus_Simon_mean_orbital_elements"
    kernel_required: bool = False
    validity_note: str = "Mean element table is documented by the engine as approximately valid from 2000 BCE to 3000 CE."
    stage_sequence: list[str]


class MeanPlanetaryNodesBulkResponse(_StrictModel):
    nodes: dict[str, OrbitalNodeResponse]
    total: int
    provenance: MeanPlanetaryNodesBulkProvenanceResponse
