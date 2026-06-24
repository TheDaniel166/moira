"""Transport models for REST discoverability metadata."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class _StrictModel(BaseModel):
    """Base response model with explicit strict extra-field policy."""

    model_config = ConfigDict(extra="forbid")


class RouteCatalogFiltersResponse(_StrictModel):
    family: str | None = None
    tag: str | None = None
    method: str | None = None
    path_contains: str | None = None
    include_hidden: bool = False


class RouteSummaryResponse(_StrictModel):
    path: str
    methods: list[str]
    name: str
    summary: str | None = None
    operation_id: str | None = None
    tags: list[str]
    family: str
    family_label: str
    include_in_schema: bool


class RouteFamilySummaryResponse(_StrictModel):
    family: str
    family_label: str
    route_count: int
    tags: list[str]


class RouteCatalogResponse(_StrictModel):
    total_count: int
    count: int
    filters: RouteCatalogFiltersResponse
    available_families: list[RouteFamilySummaryResponse]
    available_tags: list[str]
    routes: list[RouteSummaryResponse]


__all__ = [
    "RouteCatalogFiltersResponse",
    "RouteCatalogResponse",
    "RouteFamilySummaryResponse",
    "RouteSummaryResponse",
]
