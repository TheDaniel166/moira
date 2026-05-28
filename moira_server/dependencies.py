"""Dependency providers for the Moira REST access surface."""

from __future__ import annotations

from fastapi import Request

from moira import Moira

from .config import ServerConfig


def get_engine(request: Request) -> Moira:
    """Return the stable startup-created engine instance."""

    return request.app.state.engine


def get_config(request: Request) -> ServerConfig:
    """Return the startup configuration object."""

    return request.app.state.server_config
