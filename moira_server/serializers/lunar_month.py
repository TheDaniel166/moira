"""Retain all canonical month evidence through typed response fields."""
from moira.lunar_month import LunarMonthResult
from ..models.lunar_month import LunarMonthResponse


def serialize_lunar_month(result: LunarMonthResult) -> LunarMonthResponse:
    return LunarMonthResponse.model_validate(result, from_attributes=True)
