"""Services for fixed stars (Phase 11 catalog + fast surfaces)."""

from __future__ import annotations

from datetime import datetime

from moira import Moira
from moira.julian import jd_from_datetime, ut_to_tt
from moira.multiple_stars import (
    components_at,
    is_resolvable,
    list_multiple_stars,
    multiple_star,
    multiple_stars_by_type,
)
from moira.stars import StarPosition, find_stars, list_stars, star_at
from moira.variable_stars import (
    VarStarPolicy,
    catalog_profile,
    list_variable_stars,
    maxima_in_range,
    minima_in_range,
    next_maximum,
    next_minimum,
    star_condition_profile,
    star_state_pair,
    variable_star,
    variable_stars_by_type,
)

from ..models.stars import (
    MultipleStarListResponse,
    MultipleStarStateRequest,
    MultipleStarStateResponse,
    MultipleStarSystemResponse,
    StarListResponse,
    StarPositionRequest,
    StarPositionResponse,
    StarsBulkRequest,
    StarsBulkResponse,
    VariableStarCatalogProfileRequest,
    VariableStarCatalogProfileResponse,
    VariableStarCatalogResponse,
    VariableStarPairRequest,
    VariableStarPairResponse,
    VariableStarRangeRequest,
    VariableStarRangeResponse,
    VariableStarStateRequest,
    VariableStarStateResponse,
)
from ..serializers.stars import (
    serialize_multiple_state,
    serialize_multiple_system,
    serialize_star,
    serialize_variable_catalog_profile,
    serialize_variable_pair,
    serialize_variable_star,
    serialize_variable_state,
)
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


def _policy(threshold: float | None) -> VarStarPolicy | None:
    if threshold is None:
        return None
    return VarStarPolicy(eclipse_threshold=threshold)


def get_variable_star(name: str) -> VariableStarCatalogResponse:
    """Catalog lookup for one variable star."""

    return serialize_variable_star(variable_star(name))


def list_variable_star_catalog(
    q: str | None = None,
    var_type: str | None = None,
    limit: int = 100,
) -> StarListResponse:
    """List variable stars by optional text or variability type."""

    if var_type:
        names = [star.name for star in variable_stars_by_type(var_type)]
    else:
        names = list_variable_stars()

    if q:
        needle = q.casefold().strip()
        names = [name for name in names if needle in name.casefold()]

    limited = names[:limit]
    return StarListResponse(stars=limited, total=len(limited))


def compute_variable_star_state(request: VariableStarStateRequest) -> VariableStarStateResponse:
    """Compute one variable-star condition state."""

    jd = jd_from_datetime(request.dt)
    star = variable_star(request.star)
    policy = _policy(request.eclipse_threshold)
    profile = star_condition_profile(star, jd, policy=policy)
    return serialize_variable_state(
        star,
        profile,
        next_minimum(star, jd),
        next_maximum(star, jd),
    )


def compute_variable_star_range(request: VariableStarRangeRequest) -> VariableStarRangeResponse:
    """Compute variable-star extrema in a bounded JD range."""

    if request.jd_end < request.jd_start:
        raise ValueError("jd_end must be greater than or equal to jd_start")
    star = variable_star(request.star)
    return VariableStarRangeResponse(
        star=star.name,
        minima_jd=minima_in_range(star, request.jd_start, request.jd_end),
        maxima_jd=maxima_in_range(star, request.jd_start, request.jd_end),
    )


def compute_variable_catalog_profile(
    request: VariableStarCatalogProfileRequest,
) -> VariableStarCatalogProfileResponse:
    """Compute the aggregate variable-star catalog profile."""

    jd = jd_from_datetime(request.dt)
    return serialize_variable_catalog_profile(catalog_profile(jd, policy=_policy(request.eclipse_threshold)))


def compute_variable_pair(request: VariableStarPairRequest) -> VariableStarPairResponse:
    """Compute a two-star variable-state relation."""

    jd = jd_from_datetime(request.dt)
    return serialize_variable_pair(
        star_state_pair(
            variable_star(request.primary),
            variable_star(request.secondary),
            jd,
            policy=_policy(request.eclipse_threshold),
        )
    )


def get_multiple_star_system(name: str) -> MultipleStarSystemResponse:
    """Catalog lookup for one multiple-star system."""

    return serialize_multiple_system(multiple_star(name))


def list_multiple_star_catalog(
    q: str | None = None,
    system_type: str | None = None,
    limit: int = 100,
) -> MultipleStarListResponse:
    """List multiple-star systems by optional text or system type."""

    if system_type:
        names = [system.name for system in multiple_stars_by_type(system_type)]
    else:
        names = list_multiple_stars()

    if q:
        needle = q.casefold().strip()
        names = [name for name in names if needle in name.casefold()]

    limited = names[:limit]
    return MultipleStarListResponse(systems=limited, total=len(limited))


def compute_multiple_star_state(request: MultipleStarStateRequest) -> MultipleStarStateResponse:
    """Compute multiple-star separation, position angle, and resolvability state."""

    require_aware_datetime(request.dt)
    if request.aperture_mm <= 0.0:
        raise ValueError("aperture_mm must be positive")

    jd = jd_from_datetime(request.dt)
    system = multiple_star(request.system)
    snapshot = components_at(system, jd)
    return serialize_multiple_state(
        system,
        snapshot,
        is_resolvable(system, jd, request.aperture_mm),
    )
