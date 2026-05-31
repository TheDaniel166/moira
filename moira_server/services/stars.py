"""Services for fixed stars (Phase 11 catalog + fast surfaces)."""

from __future__ import annotations

from datetime import datetime

from moira import Moira
from moira.stars import star_at, all_stars_at, list_stars, find_stars, StarPosition

from ..models.stars import (
    StarPositionRequest,
    StarPositionResponse,
    StarsBulkRequest,
    StarsBulkResponse,
    StarListResponse,
)
from ..serializers.stars import serialize_star


def compute_star_position(engine: Moira, request: StarPositionRequest) -> StarPositionResponse:
    """Single star position using the sovereign star catalog."""
    # star_at accepts name or designation
    data: StarPosition = star_at(request.star, request.dt)
    return serialize_star(data)


def compute_stars_bulk(engine: Moira, request: StarsBulkRequest) -> StarsBulkResponse:
    """Bulk stars at one time — excellent for website constellation rendering."""
    results = {}
    missing = []

    for name in request.stars:
        try:
            data = star_at(name, request.dt)
            results[name] = data
        except Exception:
            if not request.skip_missing:
                raise
            missing.append(name)

    return StarsBulkResponse(
        dt=request.dt,
        results={k: serialize_star(v) for k, v in results.items()},
        missing=missing,
    )


def list_or_search_stars(engine: Moira, q: str | None = None, limit: int = 50) -> StarListResponse:
    """Fast search / listing over the sovereign star catalog."""
    if q:
        # Use the core find_stars which is designed for this
        found = find_stars(q, limit=limit)
        names = [s.get("name") or s.get("designation", "") for s in found]
        return StarListResponse(stars=names, total=len(names))
    else:
        all_names = list_stars()[:limit]
        return StarListResponse(stars=all_names, total=len(all_names))
