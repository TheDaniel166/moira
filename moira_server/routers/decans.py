"""Phase-9 decans/decanates routes (P9-12)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine

from ..models.decans import (
    DecanateChartBodyRequest,
    DecanateChartPositionResponse,
    DecanateChartSetResponse,
    DecanateLongitudeRequest,
    DecanatePositionResponse,
    DecanateSetRequest,
    DecanateSetResponse,
    HermeticDecanCatalogResponse,
    HermeticDecanLookupResponse,
    HermeticDecanNightHoursResponse,
    HermeticLocationRequest,
    HermeticLongitudeRequest,
    VedicDrekkanaRequest,
)
from ..serializers.decans import (
    serialize_decanate_chart_position,
    serialize_decanate_chart_set,
    serialize_decanate_position,
    serialize_decanate_set,
    serialize_hermetic_decan_catalog,
    serialize_hermetic_decan_lookup,
    serialize_hermetic_decan_night_hours,
)
from ..services.decans import (
    compute_chaldean_face,
    compute_decanate_set,
    compute_decanate_set_chart,
    compute_hermetic_decan_longitude,
    compute_hermetic_decan_night_hours,
    compute_hermetic_rising_decan,
    compute_triplicity_decan,
    compute_vedic_drekkana,
    compute_vedic_drekkana_chart,
    list_hermetic_decan_catalog,
)


decanates_router = APIRouter(prefix="/v1/decanates", tags=["decanates"])
hermetic_decans_router = APIRouter(
    prefix="/v1/hermetic-decans",
    tags=["hermetic-decans"],
)


@decanates_router.post("/chaldean-face", response_model=DecanatePositionResponse)
def chaldean_face_route(
    request: DecanateLongitudeRequest,
) -> DecanatePositionResponse:
    return serialize_decanate_position(compute_chaldean_face(request))


@decanates_router.post("/triplicity", response_model=DecanatePositionResponse)
def triplicity_decan_route(
    request: DecanateLongitudeRequest,
) -> DecanatePositionResponse:
    return serialize_decanate_position(compute_triplicity_decan(request))


@decanates_router.post("/vedic-drekkana", response_model=DecanatePositionResponse)
def vedic_drekkana_route(
    request: VedicDrekkanaRequest,
) -> DecanatePositionResponse:
    return serialize_decanate_position(compute_vedic_drekkana(request))


@decanates_router.post("/set", response_model=DecanateSetResponse)
def decanate_set_route(request: DecanateSetRequest) -> DecanateSetResponse:
    return serialize_decanate_set(compute_decanate_set(request))


@decanates_router.post(
    "/chart/vedic-drekkana",
    response_model=DecanateChartPositionResponse,
)
def vedic_drekkana_chart_route(
    request: DecanateChartBodyRequest,
    engine: Moira = Depends(get_engine),
) -> DecanateChartPositionResponse:
    return serialize_decanate_chart_position(
        compute_vedic_drekkana_chart(engine, request)
    )


@decanates_router.post("/chart/set", response_model=DecanateChartSetResponse)
def decanate_set_chart_route(
    request: DecanateChartBodyRequest,
    engine: Moira = Depends(get_engine),
) -> DecanateChartSetResponse:
    return serialize_decanate_chart_set(
        compute_decanate_set_chart(engine, request)
    )


@hermetic_decans_router.get("/catalog", response_model=HermeticDecanCatalogResponse)
def hermetic_decan_catalog_route() -> HermeticDecanCatalogResponse:
    return serialize_hermetic_decan_catalog(list_hermetic_decan_catalog())


@hermetic_decans_router.post("/longitude", response_model=HermeticDecanLookupResponse)
def hermetic_decan_longitude_route(
    request: HermeticLongitudeRequest,
) -> HermeticDecanLookupResponse:
    name, index, ruling_star = compute_hermetic_decan_longitude(request)
    return serialize_hermetic_decan_lookup(
        name=name,
        index=index,
        ruling_star=ruling_star,
        longitude=request.longitude,
    )


@hermetic_decans_router.post("/rising", response_model=HermeticDecanLookupResponse)
def hermetic_rising_decan_route(
    request: HermeticLocationRequest,
) -> HermeticDecanLookupResponse:
    name, index, ruling_star = compute_hermetic_rising_decan(request)
    return serialize_hermetic_decan_lookup(
        name=name,
        index=index,
        ruling_star=ruling_star,
        jd=request.jd,
        latitude=request.latitude,
        observer_longitude=request.longitude,
    )


@hermetic_decans_router.post(
    "/night-hours",
    response_model=HermeticDecanNightHoursResponse,
)
def hermetic_decan_night_hours_route(
    request: HermeticLocationRequest,
) -> HermeticDecanNightHoursResponse:
    return serialize_hermetic_decan_night_hours(
        compute_hermetic_decan_night_hours(request)
    )
