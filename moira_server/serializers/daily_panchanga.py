"""Copy canonical daily Panchanga truth without recomputing astronomy."""
from moira.daily_panchanga import DailyPanchangaResult
from ..models.daily_panchanga import DailyPanchangaResponse


def serialize_daily_panchanga(result: DailyPanchangaResult) -> DailyPanchangaResponse:
    return DailyPanchangaResponse.model_validate(result, from_attributes=True)
