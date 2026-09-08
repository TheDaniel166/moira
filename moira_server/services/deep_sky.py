"""Application services for the offline deep-sky catalog surface."""

from __future__ import annotations

from moira.deep_sky import (
    DeepSkyClass,
    deep_sky_at,
    deep_sky_object,
    find_deep_sky_objects,
    list_deep_sky_objects,
)
from moira.julian import jd_from_datetime, utc_to_tt

from ..models.deep_sky import (
    DeepSkyBulkRequest,
    DeepSkyBulkResponse,
    DeepSkyListResponse,
    DeepSkyPositionRequest,
    DeepSkyPositionResponse,
)
from ..serializers.deep_sky import (
    serialize_deep_sky_catalog_item,
    serialize_deep_sky_position,
)
from ._shared import require_aware_datetime


def compute_deep_sky_position(request: DeepSkyPositionRequest) -> DeepSkyPositionResponse:
    """Resolve and project one catalog anchor at the request's UTC instant."""

    require_aware_datetime(request.dt)
    jd_tt = utc_to_tt(jd_from_datetime(request.dt))
    return serialize_deep_sky_position(
        deep_sky_at(request.object, jd_tt),
        request.dt,
    )


def compute_deep_sky_bulk(request: DeepSkyBulkRequest) -> DeepSkyBulkResponse:
    """Project a bounded set of catalog anchors and report skipped identities."""

    require_aware_datetime(request.dt)
    jd_tt = utc_to_tt(jd_from_datetime(request.dt))
    results: dict[str, DeepSkyPositionResponse] = {}
    missing: list[str] = []
    for name in request.objects:
        try:
            position = deep_sky_at(name, jd_tt)
        except (KeyError, ValueError):
            if not request.skip_missing:
                raise
            missing.append(name)
            continue
        results[name] = serialize_deep_sky_position(position, request.dt)
    catalog_version = next(
        (item.provenance.catalog_version for item in results.values()),
        deep_sky_object(list_deep_sky_objects()[0]).catalog_version,
    )
    return DeepSkyBulkResponse(
        dt=request.dt,
        results=results,
        missing=missing,
        catalog_version=catalog_version,
    )


def list_deep_sky_catalog(
    *,
    query: str | None = None,
    object_class: DeepSkyClass | None = None,
    limit: int = 100,
) -> DeepSkyListResponse:
    """List or search catalog records with explicit total/limit semantics."""

    names = (
        find_deep_sky_objects(query, object_class)
        if query is not None and query.strip()
        else list_deep_sky_objects(object_class)
    )
    records = [deep_sky_object(name) for name in names[:limit]]
    catalog_version = deep_sky_object(list_deep_sky_objects()[0]).catalog_version
    return DeepSkyListResponse(
        objects=[serialize_deep_sky_catalog_item(record) for record in records],
        total=len(names),
        returned_count=len(records),
        query=query,
        object_class=object_class,
        catalog_version=catalog_version,
    )
