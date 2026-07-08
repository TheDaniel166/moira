"""Transport models for comet endpoints (Phase 11 small-body fast API)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


COMETS_BULK_MAX_ITEMS = 500


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CometPositionRequest(_StrictModel):
    dt: datetime
    body: str | int

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


class CometPositionProvenanceResponse(_StrictModel):
    requested_datetime: str
    normalized_datetime_utc: str
    jd_ut: float
    coordinate_source: str = "comet_at_geocentric_tropical_ecliptic"
    kernel_source: str
    known_catalog_entry: bool
    loaded_kernel_available: bool
    requested_body: str
    resolved_body: str
    returned_body: str
    returned_naif_id: int
    naif_convention: str = "periodic_comet_naif_id_1000000_plus_number"
    frame: str = "geocentric_tropical_ecliptic"
    stage_sequence: list[str]


class CometPositionResponse(_StrictModel):
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
    is_sovereign: bool = False
    provenance: CometPositionProvenanceResponse

    # Velocity for proper motion approximation
    velocity_x: float | None = None
    velocity_y: float | None = None
    velocity_z: float | None = None
    # Magnitude not available in basic comet position calls.


class CometsBulkRequest(_StrictModel):
    dt: datetime
    bodies: list[str | int] = Field(min_length=1, max_length=COMETS_BULK_MAX_ITEMS)
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


class CometsBulkProvenanceResponse(_StrictModel):
    requested_datetime: str
    normalized_datetime_utc: str
    jd_ut: float
    coordinate_source: str = "comet_at_geocentric_tropical_ecliptic"
    kernel_source: str
    requested_bodies: list[str]
    returned_bodies: list[str]
    missing_bodies: list[str]
    loaded_kernel_available: bool
    stage_sequence: list[str]


class CometsBulkResponse(_StrictModel):
    dt: datetime
    results: dict[str, CometPositionResponse]
    missing: list[str] = []
    sovereign_used: bool = False
    provenance: CometsBulkProvenanceResponse


class CometListItem(_StrictModel):
    name: str
    naif_id: int


class CometListResponse(_StrictModel):
    bodies: list[CometListItem]
    total: int
    provenance: "CometListProvenanceResponse"


class CometListProvenanceResponse(_StrictModel):
    catalog_source: str = "COMET_NAIF"
    catalog_scope: str = "numbered_periodic_comet_identity_mapping"
    availability_source: str
    loaded_kernel_available: bool
    requested_query: str | None = None
    limit: int
    returned_count: int
    stage_sequence: list[str]
