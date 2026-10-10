"""Bind the server-owned reader to the public daily Panchanga facade."""
from moira import Moira
from moira.daily_panchanga import DailyPanchangaPolicy, DailyPanchangaResult
from ..models.daily_panchanga import DailyPanchangaRequest


def compute_daily_panchanga(engine: Moira, request: DailyPanchangaRequest) -> DailyPanchangaResult:
    return engine.daily_panchanga(
        request.local_date, request.latitude, request.longitude,
        timezone=request.timezone, policy=DailyPanchangaPolicy(**request.policy.model_dump()),
    )
