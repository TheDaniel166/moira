"""Phase-2 chart and houses routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from moira import Moira

from ..cache import ChartLRUCache
from ..dependencies import get_engine
from ..models.chart import (
    ChartReductionResponse,
    ChartRequest,
    ChartResponse,
    HouseDynamicsRequest,
    HouseDynamicsResponse,
    HousesReductionResponse,
    HousesRequest,
    HousesResponse,
    PolarAdmissibilityRequest,
    PolarAdmissibilityResponse,
    PolarHouseWindowResponse,
)
from ..serializers.chart import (
    serialize_chart,
    serialize_chart_with_reduction,
    serialize_house_dynamics,
    serialize_houses,
    serialize_houses_with_reduction,
)
from ..services.chart import (
    compute_chart,
    compute_chart_with_reduction,
    compute_house_dynamics,
    compute_houses,
    compute_houses_with_reduction,
)


router = APIRouter(prefix="/v1", tags=["chart"])


def _get_cache(request: Request) -> ChartLRUCache | None:
    """Return the per-process chart cache, or None if not initialised."""
    return getattr(request.app.state, "chart_cache", None)


@router.post("/chart", response_model=ChartResponse)
def chart_route(
    request: ChartRequest,
    http_request: Request,
    engine: Moira = Depends(get_engine),
) -> ChartResponse:
    """Serialize a canonical chart result for transport."""

    cache = _get_cache(http_request)
    if cache is not None:
        key = ChartLRUCache.make_chart_key(
            request.dt.isoformat(),
            request.bodies,
            request.include_nodes,
            request.observer_lat,
            request.observer_lon,
            request.observer_elev_m,
        )
        cached = cache.get(key + "|chart")
        if cached is not None:
            return cached
        result = serialize_chart(compute_chart(engine, request))
        cache.set(key + "|chart", result)
        return result

    return serialize_chart(compute_chart(engine, request))


@router.post("/chart/reduction", response_model=ChartReductionResponse)
def chart_reduction_route(
    request: ChartRequest,
    http_request: Request,
    engine: Moira = Depends(get_engine),
) -> ChartReductionResponse:
    """Serialize a chart together with its reduction truth."""

    cache = _get_cache(http_request)
    if cache is not None:
        key = ChartLRUCache.make_chart_key(
            request.dt.isoformat(),
            request.bodies,
            request.include_nodes,
            request.observer_lat,
            request.observer_lon,
            request.observer_elev_m,
        )
        cached = cache.get(key + "|reduction")
        if cached is not None:
            return cached
        chart, reduction = compute_chart_with_reduction(engine, request)
        result = serialize_chart_with_reduction(chart, reduction)
        cache.set(key + "|reduction", result)
        return result

    chart, reduction = compute_chart_with_reduction(engine, request)
    return serialize_chart_with_reduction(chart, reduction)


@router.post("/houses", response_model=HousesResponse)
def houses_route(
    request: HousesRequest,
    engine: Moira = Depends(get_engine),
) -> HousesResponse:
    """Serialize a canonical houses result for transport."""

    return serialize_houses(compute_houses(engine, request))


@router.post("/houses/reduction", response_model=HousesReductionResponse)
def houses_reduction_route(
    request: HousesRequest,
    engine: Moira = Depends(get_engine),
) -> HousesReductionResponse:
    """Serialize houses result together with the governing doctrine and computation path (reduction truth)."""
    houses, reduction = compute_houses_with_reduction(engine, request)
    return serialize_houses_with_reduction(houses, reduction)


@router.post("/houses/dynamics", response_model=HouseDynamicsResponse)
def house_dynamics_route(
    request: HouseDynamicsRequest,
    engine: Moira = Depends(get_engine),
) -> HouseDynamicsResponse:
    """Compute instantaneous house cusp and angle speeds."""
    dynamics = compute_house_dynamics(engine, request)
    return serialize_house_dynamics(dynamics)


_POLAR_SCAN_MODULES = {
    "P": ("experimental_placidus", "scan_experimental_placidus_admissibility"),
    "C": ("experimental_campanus", "scan_experimental_campanus_admissibility"),
    "R": ("experimental_regiomontanus", "scan_experimental_regiomontanus_admissibility"),
    "T": ("experimental_topocentric", "scan_experimental_topocentric_admissibility"),
    "K": ("experimental_koch", "scan_experimental_koch_admissibility"),
    "B": ("experimental_alcabitius", "scan_experimental_alcabitius_admissibility"),
}


@router.post("/houses/polar-admissibility", response_model=PolarAdmissibilityResponse)
def houses_polar_admissibility_route(
    request: PolarAdmissibilityRequest,
) -> PolarAdmissibilityResponse:
    """Scan and return the polar ARMC admissibility windows and quality metrics for a house system."""
    import importlib
    from moira.constants import HouseSystem
    from moira.julian import jd_from_datetime, utc_to_tt
    from moira.obliquity import true_obliquity

    # Resolve system code
    sys_code = request.system.upper()
    resolved_code = getattr(HouseSystem, sys_code, None) or request.system
    if resolved_code not in _POLAR_SCAN_MODULES:
        # Check by single-letter code directly
        if request.system not in _POLAR_SCAN_MODULES:
            raise HTTPException(
                status_code=400,
                detail=f"No polar admissibility scanner available for house system {request.system!r}",
            )
        resolved_code = request.system

    # Resolve obliquity
    if request.obliquity is not None:
        obliquity = request.obliquity
    elif request.dt is not None:
        jd_tt = utc_to_tt(jd_from_datetime(request.dt))
        obliquity = true_obliquity(jd_tt)
    else:
        obliquity = true_obliquity(2451545.0)

    mod_name, fn_name = _POLAR_SCAN_MODULES[resolved_code]
    mod = importlib.import_module(f"moira.{mod_name}")
    scanner = getattr(mod, fn_name)

    admissibility = scanner(
        latitude=request.latitude,
        obliquity=obliquity,
        armc_start=request.armc_start,
        armc_end=request.armc_end,
        armc_step=request.armc_step,
        rho_max=request.rho_max,
        stability_radius=request.stability_radius,
    )

    return PolarAdmissibilityResponse(
        latitude=request.latitude,
        obliquity=obliquity,
        system=resolved_code,
        total_samples=admissibility.total_samples,
        valid_fraction=admissibility.valid_fraction,
        has_any_window=admissibility.has_any_window,
        windows=[
            PolarHouseWindowResponse(
                start_armc=w.start_armc,
                end_armc=w.end_armc,
                sample_count=w.sample_count,
            )
            for w in admissibility.windows
        ],
        practical_windows=[
            PolarHouseWindowResponse(
                start_armc=w.start_armc,
                end_armc=w.end_armc,
                sample_count=w.sample_count,
            )
            for w in getattr(admissibility, "practical_windows", ())
        ],
        stable_practical_windows=[
            PolarHouseWindowResponse(
                start_armc=w.start_armc,
                end_armc=w.end_armc,
                sample_count=w.sample_count,
            )
            for w in getattr(admissibility, "stable_practical_windows", ())
        ],
    )
