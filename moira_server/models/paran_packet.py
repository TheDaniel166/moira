"""Website-only paran and fixed-star packet transport models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .phenomena import (
    GeneralVisibilityEventResponse,
    NatalAngularContactsResponse,
    ParanSearchResponse,
    ParanStarCanonResponse,
)


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class ParanPacketRequest(_StrictModel):
    bodies: list[str] = Field(min_length=1)
    natal_jd: float
    lat: float = Field(ge=-90.0, le=90.0)
    lon: float = Field(ge=-180.0, le=180.0)
    orb_minutes: float = Field(default=4.0, ge=0.0)
    angular_orb_minutes: float = Field(default=2.0, ge=0.0)
    policy_preset: str = "permissive"
    canon_tiers: list[str] = Field(default_factory=list)
    include_crossing_inventory: bool = True
    include_angular_contacts: bool = True
    include_heliacal: bool = False
    heliacal_kind: str = "heliacal_rising"
    heliacal_search_window_days: int = Field(default=400, gt=0, le=3660)


class ParanPacketResponse(_StrictModel):
    canon: ParanStarCanonResponse
    parans: ParanSearchResponse
    angular_contacts: NatalAngularContactsResponse | None = None
    heliacal_events: list[GeneralVisibilityEventResponse]
    warnings: list[str]
    provenance: dict[str, str]


__all__ = ["ParanPacketRequest", "ParanPacketResponse"]
