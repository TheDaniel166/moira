"""Transport models for the release-bound deep-sky catalog surfaces."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from moira.deep_sky import DeepSkyClass


DEEP_SKY_BULK_MAX_ITEMS = 60


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DeepSkyPositionRequest(_StrictModel):
    dt: datetime
    object: str = Field(min_length=1)

    @field_validator("dt")
    @classmethod
    def _aware_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("dt must be timezone-aware")
        return value

    @field_validator("object")
    @classmethod
    def _non_empty_object(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("object must be non-empty")
        return stripped


class DeepSkyBulkRequest(_StrictModel):
    dt: datetime
    objects: list[str] = Field(min_length=1, max_length=DEEP_SKY_BULK_MAX_ITEMS)
    skip_missing: bool = True

    @field_validator("dt")
    @classmethod
    def _aware_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("dt must be timezone-aware")
        return value

    @field_validator("objects")
    @classmethod
    def _valid_objects(cls, value: list[str]) -> list[str]:
        stripped = [item.strip() for item in value]
        if any(not item for item in stripped):
            raise ValueError("objects entries must be non-empty")
        return stripped


class DeepSkyCatalogItemResponse(_StrictModel):
    name: str
    designation: str
    aliases: list[str]
    object_class: DeepSkyClass
    is_extended: bool
    position_semantics: str
    simbad_main_id: str
    simbad_otype: str
    source_ra_deg: float
    source_dec_deg: float
    coordinate_bibcode: str
    coordinate_quality: str
    proper_motion_admitted: bool
    star_registry_name: str | None
    nasa_exoplanet_archive_hostname: str | None
    confirmed_planet_count: int | None
    catalog_version: str


class DeepSkyPositionProvenanceResponse(_StrictModel):
    requested_datetime: str
    normalized_datetime_utc: str
    jd_tt: float
    source_ra_deg: float
    source_dec_deg: float
    source_frame: str
    source_epoch_jd_tt: float
    position_semantics: str
    position_source: str
    proper_motion_applied: bool
    simbad_main_id: str
    coordinate_bibcode: str
    coordinate_quality: str
    catalog_version: str
    stage_sequence: list[str]


class DeepSkyPositionResponse(_StrictModel):
    name: str
    designation: str
    object_class: DeepSkyClass
    longitude: float
    latitude: float
    sign: str
    sign_symbol: str
    sign_degree: float
    provenance: DeepSkyPositionProvenanceResponse


class DeepSkyListResponse(_StrictModel):
    objects: list[DeepSkyCatalogItemResponse]
    total: int
    returned_count: int
    query: str | None
    object_class: DeepSkyClass | None
    catalog_version: str


class DeepSkyBulkResponse(_StrictModel):
    dt: datetime
    results: dict[str, DeepSkyPositionResponse]
    missing: list[str]
    catalog_version: str
