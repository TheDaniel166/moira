"""Dependency providers for the Moira REST access surface."""

from __future__ import annotations

from collections.abc import Callable
import functools
import inspect
from typing import Any

from fastapi import Request

from moira import Moira
from moira.spk_reader import use_reader_override

from .config import ServerConfig


def get_engine(request: Request) -> Moira:
    """Return the stable startup-created engine instance."""

    return request.app.state.engine


def with_engine_reader(route: Callable[..., Any]) -> Callable[..., Any]:
    """Run a route with the engine's ephemeris as the active reader.

    For routes whose services call engine functions that resolve the reader
    from context instead of taking one. Without it those routes worked only
    when a global kernel path happened to be set (MOIRA_SERVER_KERNEL_PATH)
    and otherwise returned HTTP 500. The route must take ``engine`` from
    ``get_engine``; kernel-free routes must not use this.
    """

    @functools.wraps(route)
    def bound(*args: Any, **kwargs: Any) -> Any:
        # An engine without a reader of its own (a test double) leaves the
        # ambient context in charge, as before.
        reader = getattr(kwargs["engine"], "_reader", None)
        if reader is None:
            return route(*args, **kwargs)
        with use_reader_override(reader):
            return route(*args, **kwargs)

    # Resolve the route's annotations here so FastAPI reads concrete types
    # rather than strings it would evaluate in this module's namespace.
    bound.__signature__ = inspect.signature(route, eval_str=True)
    return bound


def get_config(request: Request) -> ServerConfig:
    """Return the startup configuration object."""

    return request.app.state.server_config
