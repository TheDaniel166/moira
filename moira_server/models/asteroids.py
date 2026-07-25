"""Transport models for asteroid/comet endpoints (Phase 11 small-body surfaces).

These are designed for high-performance website use:
- Leverage native Type 13 + sovereign small-body kernels for speed when available.
- Support single and bulk queries.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from moira.asteroid_families import ASTEROID_FAMILY_CATALOG_SOURCE

from .relationship import AspectDataResponse


ASTEROIDS_BULK_MAX_ITEMS = 500
ASTEROID_FAMILY_MEMBER_MAX_ITEMS = 500
ASTEROID_FAMILIES_CHART_MAX_ITEMS = 500
ASTEROID_FAMILY_RESONANCE_NETWORK_MAX_ITEMS = 500
SMALL_BODY_NAIF_OFFSET = 2_000_000


class AsteroidSubsetSlug(StrEnum):
    classical = "classical"
    main_belt = "main_belt"
    centaurs = "centaurs"
    tnos = "tnos"


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AsteroidPositionRequest(_StrictModel):
    """Request for a single asteroid geocentric ecliptic position."""
    dt: datetime
    body: str | int  # name or NAIF ID
    # Future: observer for topocentric, but start simple for website

    @field_validator("dt")
    @classmethod
    def _aware_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("dt must be timezone-aware")
        return value

    @field_validator("body")
    @classmethod
    def _valid_body(cls, value: str | int) -> str | int:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("body must be non-empty")
            return stripped
        return value


class AsteroidPositionProvenanceResponse(_StrictModel):
    requested_datetime: str
    normalized_datetime_utc: str
    jd_ut: float
    coordinate_source: str = "asteroid_at_geocentric_tropical_ecliptic"
    kernel_source: str
    known_catalog_entry: bool
    loaded_kernel_available: bool
    requested_body: str
    returned_body: str
    returned_naif_id: int
    naif_convention: str = "small_body_naif_id_2000000_plus_catalog_number"
    frame: str = "geocentric_tropical_ecliptic"
    stage_sequence: list[str]


class AsteroidPositionResponse(_StrictModel):
    name: str
    naif_id: int
    longitude: float
    latitude: float
    distance: float
    speed: float
    retrograde: bool
    sign: str
    sign_symbol: str
    sign_degree: float
    is_sovereign: bool = False   # True if served from an explicitly loaded small-body reader
    provenance: AsteroidPositionProvenanceResponse

    # Additional fields for website (proper motion approximation from velocity)
    velocity_x: float | None = None  # km/s (ecliptic)
    velocity_y: float | None = None
    velocity_z: float | None = None
    # Note: Magnitude (V) requires additional catalog data (H/G params) and is not
    #       currently computed by the basic position functions.


class AsteroidsBulkRequest(_StrictModel):
    """Fast bulk request for many asteroids at the same time (website-friendly)."""
    dt: datetime
    bodies: list[str | int] = Field(min_length=1, max_length=ASTEROIDS_BULK_MAX_ITEMS)
    skip_missing: bool = True

    @field_validator("dt")
    @classmethod
    def _aware_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("dt must be timezone-aware")
        return value

    @field_validator("bodies")
    @classmethod
    def _valid_bodies(cls, value: list[str | int]) -> list[str | int]:
        cleaned: list[str | int] = []
        for body in value:
            if isinstance(body, str):
                stripped = body.strip()
                if not stripped:
                    raise ValueError("bodies entries must be non-empty")
                cleaned.append(stripped)
            else:
                cleaned.append(body)
        return cleaned


class AsteroidsBulkProvenanceResponse(_StrictModel):
    requested_datetime: str
    normalized_datetime_utc: str
    jd_ut: float
    coordinate_source: str = "asteroid_at_geocentric_tropical_ecliptic"
    kernel_source: str
    requested_bodies: list[str]
    returned_bodies: list[str]
    missing_bodies: list[str]
    loaded_kernel_available: bool
    stage_sequence: list[str]


class AsteroidsBulkResponse(_StrictModel):
    dt: datetime
    results: dict[str, AsteroidPositionResponse]  # keyed by requested name/naif
    missing: list[str] = []
    sovereign_used: bool = False
    provenance: AsteroidsBulkProvenanceResponse


class AsteroidListItem(_StrictModel):
    name: str
    naif_id: int


class AsteroidListResponse(_StrictModel):
    bodies: list[AsteroidListItem]
    total: int
    provenance: "AsteroidListProvenanceResponse"


class AsteroidListProvenanceResponse(_StrictModel):
    catalog_source: str = "ASTEROID_NAIF"
    catalog_scope: str = "known_asteroid_identity_mapping"
    availability_source: str
    loaded_kernel_available: bool
    requested_query: str | None = None
    limit: int
    returned_count: int
    stage_sequence: list[str]


class AsteroidSubsetCatalogItem(_StrictModel):
    name: str
    naif_id: int
    loaded_kernel_available: bool = False


class AsteroidSubsetSummaryResponse(_StrictModel):
    subset: AsteroidSubsetSlug
    label: str
    catalog_source: str
    member_count: int


class AsteroidSubsetListProvenanceResponse(_StrictModel):
    catalog_source: str
    subset_source_module: str
    availability_source: str
    loaded_kernel_available: bool
    requested_query: str | None = None
    limit: int
    returned_count: int
    stage_sequence: list[str]


class AsteroidSubsetsResponse(_StrictModel):
    subsets: list[AsteroidSubsetSummaryResponse]
    total: int
    stage_sequence: list[str]


class AsteroidSubsetListResponse(_StrictModel):
    subset: AsteroidSubsetSlug
    label: str
    bodies: list[AsteroidSubsetCatalogItem]
    total: int
    provenance: AsteroidSubsetListProvenanceResponse


class AsteroidSubsetPositionsRequest(_StrictModel):
    dt: datetime
    bodies: list[str | int] | None = Field(
        default=None,
        min_length=1,
        max_length=ASTEROIDS_BULK_MAX_ITEMS,
    )
    skip_missing: bool = True

    @field_validator("dt")
    @classmethod
    def _aware_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("dt must be timezone-aware")
        return value

    @field_validator("bodies")
    @classmethod
    def _valid_bodies(cls, value: list[str | int] | None) -> list[str | int] | None:
        if value is None:
            return value
        cleaned: list[str | int] = []
        for body in value:
            if isinstance(body, str):
                stripped = body.strip()
                if not stripped:
                    raise ValueError("bodies entries must be non-empty")
                cleaned.append(stripped)
            else:
                cleaned.append(body)
        return cleaned


class AsteroidSubsetPositionsProvenanceResponse(_StrictModel):
    subset: AsteroidSubsetSlug
    subset_source_module: str
    requested_datetime: str
    normalized_datetime_utc: str
    requested_bodies: list[str]
    resolved_subset_bodies: list[str]
    returned_bodies: list[str]
    missing_bodies: list[str]
    loaded_kernel_available: bool
    stage_sequence: list[str]


class AsteroidSubsetPositionsResponse(_StrictModel):
    subset: AsteroidSubsetSlug
    label: str
    dt: datetime
    results: dict[str, AsteroidPositionResponse]
    missing: list[str] = []
    sovereign_used: bool = False
    provenance: AsteroidSubsetPositionsProvenanceResponse


class AsteroidFamilyLookupProvenanceResponse(_StrictModel):
    catalog_source: str = ASTEROID_FAMILY_CATALOG_SOURCE
    number_system: str = "MPC_catalog_number"
    lookup_source_module: str = "moira.asteroid_families"
    requested_number: int
    stage_sequence: list[str]


class AsteroidFamilyLookupResponse(_StrictModel):
    number: int
    family_name: str | None
    family_names: list[str]
    provenance: AsteroidFamilyLookupProvenanceResponse


class AsteroidFamilyMembersProvenanceResponse(_StrictModel):
    catalog_source: str = ASTEROID_FAMILY_CATALOG_SOURCE
    number_system: str = "MPC_catalog_number"
    lookup_source_module: str = "moira.asteroid_families"
    requested_family_name: str
    offset: int
    limit: int
    total_available: int
    returned_count: int
    stage_sequence: list[str]


class AsteroidFamilyMembersResponse(_StrictModel):
    family_name: str
    members: list[int]
    total_available: int
    returned_count: int
    provenance: AsteroidFamilyMembersProvenanceResponse


class AsteroidFamiliesInChartRequest(_StrictModel):
    numbers: list[int] = Field(
        min_length=1,
        max_length=ASTEROID_FAMILIES_CHART_MAX_ITEMS,
    )

    @field_validator("numbers")
    @classmethod
    def _valid_numbers(cls, value: list[int]) -> list[int]:
        for number in value:
            if number <= 0:
                raise ValueError("numbers entries must be positive MPC catalog numbers")
        return value


class AsteroidFamiliesInChartProvenanceResponse(_StrictModel):
    catalog_source: str = ASTEROID_FAMILY_CATALOG_SOURCE
    number_system: str = "MPC_catalog_number"
    lookup_source_module: str = "moira.asteroid_families"
    requested_count: int
    grouped_count: int
    ungrouped_count: int
    stage_sequence: list[str]


class AsteroidFamiliesInChartResponse(_StrictModel):
    groups: dict[str, list[int]]
    ungrouped_numbers: list[int]
    provenance: AsteroidFamiliesInChartProvenanceResponse


class AsteroidFamilyResonanceNetworkRequest(_StrictModel):
    dt: datetime
    bodies: list[str | int] | None = Field(
        default=None,
        min_length=2,
        max_length=ASTEROID_FAMILY_RESONANCE_NETWORK_MAX_ITEMS,
    )
    numbers: list[int] | None = Field(
        default=None,
        min_length=2,
        max_length=ASTEROID_FAMILY_RESONANCE_NETWORK_MAX_ITEMS,
    )
    skip_missing: bool = True
    aspect_tier: int | None = 0
    include_minor: bool = True
    orb_factor: float = Field(default=1.0, gt=0.0)

    @field_validator("dt")
    @classmethod
    def _aware_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("dt must be timezone-aware")
        return value

    @field_validator("bodies")
    @classmethod
    def _valid_bodies(cls, value: list[str | int] | None) -> list[str | int] | None:
        if value is None:
            return value
        cleaned: list[str | int] = []
        seen: set[str] = set()
        for body in value:
            if isinstance(body, str):
                stripped = body.strip()
                if not stripped:
                    raise ValueError("bodies entries must be non-empty")
                if stripped.isdecimal() and int(stripped) <= SMALL_BODY_NAIF_OFFSET:
                    raise ValueError(
                        "numeric bodies must use small-body NAIF IDs; use numbers for MPC catalog numbers"
                    )
                key = stripped.casefold()
                cleaned.append(stripped)
            else:
                if body <= SMALL_BODY_NAIF_OFFSET:
                    raise ValueError(
                        "integer bodies must use small-body NAIF IDs; use numbers for MPC catalog numbers"
                    )
                key = str(body)
                cleaned.append(body)
            if key in seen:
                raise ValueError("bodies entries must be unique")
            seen.add(key)
        return cleaned

    @field_validator("numbers")
    @classmethod
    def _valid_numbers(cls, value: list[int] | None) -> list[int] | None:
        if value is None:
            return value
        seen: set[int] = set()
        for number in value:
            if number <= 0:
                raise ValueError("numbers entries must be positive MPC catalog numbers")
            if number in seen:
                raise ValueError("numbers entries must be unique")
            seen.add(number)
        return value

    @field_validator("aspect_tier")
    @classmethod
    def _valid_aspect_tier(cls, value: int | None) -> int | None:
        if value is not None and value not in (0, 1, 2):
            raise ValueError("aspect_tier must be 0, 1, 2, or null")
        return value

    @model_validator(mode="after")
    def _exactly_one_identity_source(self) -> "AsteroidFamilyResonanceNetworkRequest":
        if (self.bodies is None) == (self.numbers is None):
            raise ValueError("provide exactly one of bodies or numbers")
        return self


class AsteroidFamilyResonanceNodeResponse(_StrictModel):
    body: str
    requested_body: str
    naif_id: int
    mpc_number: int
    family_name: str | None
    family_names: list[str]
    longitude: float
    latitude: float
    speed: float
    retrograde: bool
    is_sovereign: bool = False


class AsteroidFamilyResonanceEdgeResponse(_StrictModel):
    source: str
    target: str
    family_name: str
    body1_number: int
    body2_number: int
    aspect: AspectDataResponse


class AsteroidFamilyResonanceNetworkProvenanceResponse(_StrictModel):
    catalog_source: str = ASTEROID_FAMILY_CATALOG_SOURCE
    number_system: str = "MPC_catalog_number"
    lookup_source_module: str = "moira.asteroid_families"
    aspect_source_module: str = "moira.aspects"
    coordinate_source: str = "asteroid_at_geocentric_tropical_ecliptic"
    requested_datetime: str
    normalized_datetime_utc: str
    jd_ut: float
    identity_source: str
    requested_bodies: list[str]
    resolved_bodies: list[str]
    missing_bodies: list[str]
    loaded_kernel_available: bool
    aspect_tier: int | None
    include_minor: bool
    orb_factor: float
    stage_sequence: list[str]


class AsteroidFamilyResonanceNetworkResponse(_StrictModel):
    dt: datetime
    nodes: list[AsteroidFamilyResonanceNodeResponse]
    edges: list[AsteroidFamilyResonanceEdgeResponse]
    network: dict[str, list[AsteroidFamilyResonanceEdgeResponse]]
    families: list[str]
    missing: list[str] = []
    total_aspects: int
    resonant_aspect_count: int
    sovereign_used: bool = False
    provenance: AsteroidFamilyResonanceNetworkProvenanceResponse
