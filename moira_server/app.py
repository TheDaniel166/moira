"""FastAPI application factory for the Moira REST access surface."""

from __future__ import annotations

from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request

from .config import ServerConfig
from .errors import register_exception_handlers
from .lifecycle import create_engine
from .routers import (
    batch_router,
    chart_router,
    health_router,
    phenomena_router,
    positions_router,
    relationship_router,
    returns_router,
    timelords_router,
    transits_router,
    visibility_router,
)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    config = app.state.server_config
    app.state.engine = create_engine(config)
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
    app.include_router(positions_router)
    app.include_router(transits_router)
    app.include_router(returns_router)
    app.include_router(batch_router)
    app.include_router(visibility_router)
    app.include_router(phenomena_router)
    app.include_router(relationship_router)
    app.include_router(timelords_router)
    return app
