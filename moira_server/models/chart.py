"""Transport models for chart and houses endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from moira.houses import PolarFallbackPolicy, UnknownSystemPolicy

from .positions import PlanetPositionResponse, PositionObserverContextResponse


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NodePositionResponse(_StrictModel):
    name: str
    longitude: float
    speed: float
    sign: str
    sign_symbol: str
    sign_degree: float


class ChartRequest(_StrictModel):
    dt: datetime
    bodies: list[str] | None = None
    include_nodes: bool = True
    observer_lat: float | None = None
    observer_lon: float | None = None
    observer_elev_m: float = 0.0


class CalendarDateTimeResponse(_StrictModel):
    """BCE-safe structured calendar representation (astronomical year numbering)."""
    year: int
    month: int
    day: int
    hour: int
    minute: int
    second: int
    microsecond: int = 0
    tzname: str = "UTC"


class ChartResponse(_StrictModel):
    jd_ut: float
    datetime_utc: str
    calendar_utc: CalendarDateTimeResponse | None = None
    obliquity: float
    delta_t: float
    planets: dict[str, PlanetPositionResponse]
    nodes: dict[str, NodePositionResponse]


class ChartPlanetReductionSummaryResponse(_StrictModel):
    source_vessel: str
    selection_surface: str
    apparent: bool
    aberration: bool
    grav_deflection: bool
    nutation: bool
    frame: str
    center: str
    topocentric_applied: bool
    stage_sequence: list[str]


class ChartNodeReductionSummaryResponse(_StrictModel):
    source_vessel: str
    source_surface: str
    stage_sequence: list[str]


class ChartReductionTruthResponse(_StrictModel):
    engine_surface: str
    source_vessel: str
    requested_datetime: str
    normalized_datetime_utc: str
    jd_ut: float
    jd_ut1: float
    jd_tt: float
    delta_t_seconds: float
    obliquity_deg: float
    requested_bodies: list[str] | None = None
    returned_bodies: list[str]
    include_nodes_requested: bool
    include_nodes_returned: bool
    topocentric_requested: bool
    observer: PositionObserverContextResponse
    stage_sequence: list[str]
    planet_reductions: dict[str, ChartPlanetReductionSummaryResponse]
    node_reductions: dict[str, ChartNodeReductionSummaryResponse]


class ChartReductionResponse(_StrictModel):
    result: ChartResponse
    reduction: ChartReductionTruthResponse


class HousePolicyRequest(_StrictModel):
    """Input doctrine for unknown-system and polar fallback.
    Uses Moira's full rich enums so that all options (including EXPERIMENTAL_SEARCH,
    FALLBACK_TO_EQUAL, FALLBACK_TO_WHOLE_SIGN, RAISE, etc.) are first-class and validated.
    Defaults match HousePolicy.default().
    """
    unknown_system: UnknownSystemPolicy = UnknownSystemPolicy.FALLBACK_TO_PLACIDUS
    polar_fallback: PolarFallbackPolicy = PolarFallbackPolicy.FALLBACK_TO_PORPHYRY


class HousesRequest(_StrictModel):
    dt: datetime
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    system: str | None = None
    policy: HousePolicyRequest | None = None


class HousePolicyResponse(_StrictModel):
    """Governing doctrine for unknown-system and polar-latitude fallback resolution.
    Uses the full Moira enums (no artificial limits on polar fallback options).
    """
    unknown_system: UnknownSystemPolicy
    polar_fallback: PolarFallbackPolicy


class HousesResponse(_StrictModel):
    system: str
    effective_system: str
    fallback: bool
    fallback_reason: str | None = None
    classification_family: str | None = None
    classification_cusp_basis: str | None = None
    classification_latitude_sensitive: bool | None = None
    classification_polar_capable: bool | None = None
    policy: HousePolicyResponse
    asc: float
    mc: float
    armc: float
    dsc: float
    ic: float
    east_point: float | None = None
    vertex: float | None = None
    anti_vertex: float | None = None
    cusps: list[float]


class HouseSystemClassificationResponse(_StrictModel):
    """Doctrinal classification of the (effective) house system.
    Mirrors the engine's HouseSystemClassification for nested schema exposure in reduction truth.
    """
    family: str
    cusp_basis: str
    latitude_sensitive: bool
    polar_capable: bool


class HousesReductionTruthResponse(_StrictModel):
    """Reduction truth for houses: the doctrine and computation path that produced the result.

    This now exposes the *full* HousePolicy object shape as a proper nested schema
    (using the canonical Moira enums for unknown_system and the rich polar_fallback options
    including EXPERIMENTAL_SEARCH, FALLBACK_TO_EQUAL, FALLBACK_TO_WHOLE_SIGN, etc.).

    Additional fields beyond the compact HousesResponse capture the complete governance:
    - requested vs applied policy
    - full classification as nested object
    - explicit fallback provenance
    """
    engine_surface: str
    source_vessel: str
    requested_datetime: str
    normalized_jd_ut: float
    requested_system: str | None
    effective_system: str
    requested_policy: HousePolicyResponse | None = None
    applied_policy: HousePolicyResponse
    fallback: bool
    fallback_reason: str | None = None
    classification: HouseSystemClassificationResponse | None = None


class HousesReductionResponse(_StrictModel):
    result: HousesResponse
    reduction: HousesReductionTruthResponse


__all__ = [
    "CalendarDateTimeResponse",
    "ChartPlanetReductionSummaryResponse",
    "ChartReductionResponse",
    "ChartReductionTruthResponse",
    "ChartRequest",
    "ChartResponse",
    "ChartNodeReductionSummaryResponse",
    "HousePolicyRequest",
    "HousePolicyResponse",
    "HouseSystemClassificationResponse",
    "HousesReductionResponse",
    "HousesReductionTruthResponse",
    "HousesRequest",
    "HousesResponse",
    "NodePositionResponse",
]

# Rebuild for forward references (Pydantic v2 + string annotations in unions/optionals)
HousesRequest.model_rebuild()
HousesResponse.model_rebuild()
HousesReductionResponse.model_rebuild()
