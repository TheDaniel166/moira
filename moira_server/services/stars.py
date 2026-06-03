"""Services for fixed stars (Phase 11 catalog + fast surfaces)."""

from __future__ import annotations

from datetime import datetime

from moira import Moira
from moira.julian import jd_from_datetime, ut_to_tt
from moira.stars import StarPosition, find_stars, list_stars, star_at

from ..models.stars import (
    StarListResponse,
    StarPositionRequest,
    StarPositionResponse,
    StarsBulkRequest,
    StarsBulkResponse,
)
from ..serializers.stars import serialize_star
from ._shared import require_aware_datetime


def _to_jd_tt(dt: datetime) -> float:
    require_aware_datetime(dt)
    return ut_to_tt(jd_from_datetime(dt))


def compute_star_position(engine: Moira, request: StarPositionRequest) -> StarPositionResponse:
    """Single star position using the sovereign star catalog."""
    data: StarPosition = star_at(request.star, _to_jd_tt(request.dt))
    return serialize_star(data)


def compute_stars_bulk(engine: Moira, request: StarsBulkRequest) -> StarsBulkResponse:
    """Bulk stars at one time; suited to website constellation rendering."""
    jd_tt = _to_jd_tt(request.dt)
    results = {}
    missing = []

    for name in request.stars:
        try:
            data = star_at(name, jd_tt)
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
    """Fast search or listing over the sovereign star catalog."""
    if q:
        found = find_stars(q, limit=limit)
        names = [s.get("name") or s.get("designation", "") for s in found]
        return StarListResponse(stars=names, total=len(names))

    all_names = list_stars()[:limit]
    return StarListResponse(stars=all_names, total=len(all_names))
