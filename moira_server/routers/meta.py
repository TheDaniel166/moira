"""Versioned REST route discovery surface."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request
from fastapi.routing import APIRoute

from ..models.meta import (
    RouteCatalogFiltersResponse,
    RouteCatalogResponse,
    RouteFamilySummaryResponse,
    RouteSummaryResponse,
)
from ..openapi import FAMILY_LABELS, family_for_tags


router = APIRouter(prefix="/v1/meta", tags=["meta"])


def _normalized_summary(route: APIRoute) -> str | None:
    if route.summary:
        return route.summary
    if route.name:
        return route.name.replace("_", " ").strip().capitalize()
    return None


def _route_summary(route: APIRoute) -> RouteSummaryResponse:
    tags = list(route.tags or [])
    family, family_label = family_for_tags(tags)
    return RouteSummaryResponse(
        path=route.path,
        methods=sorted(route.methods or []),
        name=route.name,
        summary=_normalized_summary(route),
        operation_id=route.operation_id or route.unique_id,
        tags=tags,
        family=family,
        family_label=family_label,
        include_in_schema=route.include_in_schema,
    )


def _matches_filters(
    route: RouteSummaryResponse,
    *,
    family: str | None,
    tag: str | None,
    method: str | None,
    path_contains: str | None,
) -> bool:
    if family:
        family_key = family.casefold()
        family_label = route.family_label.casefold()
        if route.family.casefold() != family_key and family_label != family_key:
            return False
    if tag:
        tag_key = tag.casefold()
        if not any(route_tag.casefold() == tag_key for route_tag in route.tags):
            return False
    if method:
        method_key = method.upper()
        if method_key not in route.methods:
            return False
    if path_contains and path_contains.casefold() not in route.path.casefold():
        return False
    return True


def _family_summaries(routes: list[RouteSummaryResponse]) -> list[RouteFamilySummaryResponse]:
    families: dict[str, dict[str, object]] = {}
    for route in routes:
        entry = families.setdefault(
            route.family,
            {
                "family_label": route.family_label,
                "route_count": 0,
                "tags": set(),
            },
        )
        entry["route_count"] = int(entry["route_count"]) + 1
        entry["tags"].update(route.tags)  # type: ignore[union-attr]

    def family_order(item: tuple[str, dict[str, object]]) -> tuple[int, str]:
        family, entry = item
        known = list(FAMILY_LABELS).index(family) if family in FAMILY_LABELS else 999
        return known, str(entry["family_label"])

    return [
        RouteFamilySummaryResponse(
            family=family,
            family_label=str(entry["family_label"]),
            route_count=int(entry["route_count"]),
            tags=sorted(str(tag) for tag in entry["tags"]),  # type: ignore[arg-type]
        )
        for family, entry in sorted(families.items(), key=family_order)
    ]


@router.get(
    "/routes",
    response_model=RouteCatalogResponse,
    summary="Summarize REST routes",
)
def route_catalog(
    request: Request,
    family: str | None = Query(
        None,
        description="Filter by discoverability family slug or family label.",
    ),
    tag: str | None = Query(None, description="Filter by exact OpenAPI tag."),
    method: str | None = Query(None, description="Filter by HTTP method."),
    path_contains: str | None = Query(None, description="Filter by path substring."),
    include_hidden: bool = Query(
        False,
        description="Include APIRoute entries that are hidden from the OpenAPI schema.",
    ),
) -> RouteCatalogResponse:
    """Return a filterable summary of the live FastAPI route table."""

    route_summaries = [
        _route_summary(route)
        for route in request.app.routes
        if isinstance(route, APIRoute)
        and (include_hidden or route.include_in_schema)
    ]
    route_summaries.sort(key=lambda route: (route.path, route.methods, route.name))

    filtered = [
        route
        for route in route_summaries
        if _matches_filters(
            route,
            family=family,
            tag=tag,
            method=method,
            path_contains=path_contains,
        )
    ]

    return RouteCatalogResponse(
        total_count=len(route_summaries),
        count=len(filtered),
        filters=RouteCatalogFiltersResponse(
            family=family,
            tag=tag,
            method=method.upper() if method else None,
            path_contains=path_contains,
            include_hidden=include_hidden,
        ),
        available_families=_family_summaries(route_summaries),
        available_tags=sorted(
            {tag for route in route_summaries for tag in route.tags}
        ),
        routes=filtered,
    )
