"""Phase-2 chart and houses service helpers."""

from __future__ import annotations

from moira import Moira

from ..models.chart import ChartRequest, HousesRequest
from ._shared import (
    build_chart_context,
    build_houses_context,
    require_aware_datetime as _require_aware_datetime,
    require_supported_chart_bodies as _require_supported_chart_bodies,
)


def compute_chart(engine: Moira, request: ChartRequest):
    """Compute a chart from a transport request."""

    return build_chart_context(engine, request)


def compute_houses(engine: Moira, request: HousesRequest):
    """Compute houses from a transport request."""

    return build_houses_context(engine, request)
