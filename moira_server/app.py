"""FastAPI application factory for the Moira REST access surface."""

from __future__ import annotations

from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request

from .cache import ChartLRUCache
from .config import ServerConfig
from .errors import register_exception_handlers
from .lifecycle import create_engine
from .routers import (
    ashtakavarga_router,
    alternate_dashas_router,
    astrocartography_router,
    asteroids_router,
    comets_router,
    batch_router,
    chart_router,
    chart_wheel_router,
    dasha_router,
    decanates_router,
    dignities_router,
    egyptian_bounds_router,
    galactic_router,
    galactic_houses_router,
    gauquelin_router,
    geodetic_router,
    hermetic_decans_router,
    health_router,
    jaimini_router,
    local_space_router,
    locations_router,
    lots_router,
    panchanga_router,
    phenomena_router,
    pipeline_router,
    positions_router,
    primary_directions_router,
    progressions_router,
    relationship_router,
    returns_router,
    shadbala_router,
    stars_router,
    timelords_router,
    triplicity_router,
    transits_router,
    varshaphal_router,
    varga_router,
    vedic_dignities_router,
    visibility_router,
)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    config = app.state.server_config
    app.state.engine = create_engine(config)
    app.state.chart_cache = ChartLRUCache(maxsize=512)
    yield


def create_app(config: ServerConfig | None = None) -> FastAPI:
    """Create the phase-1 Moira server application."""

    resolved = config if config is not None else ServerConfig.from_env()
    docs_url = "/docs" if resolved.docs_enabled else None
    redoc_url = "/redoc" if resolved.docs_enabled else None
    openapi_url = "/openapi.json" if resolved.docs_enabled else None

    app = FastAPI(
        title="Moira Server",
        version="0.1.0",
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
        lifespan=_lifespan,
    )
    app.state.server_config = resolved

    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request.state.request_id = str(uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(chart_router)
    app.include_router(chart_wheel_router)  # Website-only chart-wheel drawing primitives
    app.include_router(positions_router)
    app.include_router(transits_router)
    app.include_router(returns_router)
    app.include_router(batch_router)
    app.include_router(visibility_router)
    app.include_router(phenomena_router)
    app.include_router(dasha_router)
    app.include_router(progressions_router)
    app.include_router(relationship_router)
    app.include_router(timelords_router)
    app.include_router(varshaphal_router)
    app.include_router(primary_directions_router)
    app.include_router(panchanga_router)    # Phase-9 Panchanga doctrine surface
    app.include_router(shadbala_router)     # Phase-9 Shadbala doctrine surface
    app.include_router(jaimini_router)      # Phase-9 Jaimini doctrine surface
    app.include_router(dignities_router)    # Phase-9 Classical Dignities doctrine surface
    app.include_router(lots_router)         # Phase-9 Classical Lots doctrine surface
    app.include_router(triplicity_router)   # Phase-9 Triplicity doctrine surface
    app.include_router(egyptian_bounds_router)  # Phase-9 Egyptian Bounds doctrine surface
    app.include_router(vedic_dignities_router)  # Phase-9 Vedic Dignities doctrine surface
    app.include_router(ashtakavarga_router)  # Phase-9 Ashtakavarga doctrine surface
    app.include_router(alternate_dashas_router)  # Phase-9 alternate dasha systems
    app.include_router(varga_router)  # Phase-9 Varga divisional chart surface
    app.include_router(decanates_router)  # Phase-9 decanate doctrine surface
    app.include_router(hermetic_decans_router)  # Phase-9 Hermetic decan surface
    app.include_router(astrocartography_router)  # Phase-10 bounded spatial line/point surface
    app.include_router(local_space_router)  # Phase-10 observer-local horizon surface
    app.include_router(geodetic_router)  # Phase-10 geodetic zodiac mapping surface
    app.include_router(galactic_router)  # Phase-10 galactic coordinate-frame surface
    app.include_router(galactic_houses_router)  # Phase-10 Galactic Porphyry house surface
    app.include_router(gauquelin_router)  # Phase-10 Gauquelin sector surface
    app.include_router(locations_router)   # City/timezone lookup for chart calculator
    app.include_router(asteroids_router)   # Fast small-body surfaces (website integration)
    app.include_router(comets_router)      # Symmetric fast comet surfaces
    app.include_router(stars_router)       # Fixed stars for the website / Manus AI
    app.include_router(pipeline_router)    # Reduction pipeline breakdown for planet positions
    return app
