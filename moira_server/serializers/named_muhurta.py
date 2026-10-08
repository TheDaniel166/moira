"""Lossless canonical projection; no interval or eligibility arithmetic."""
from dataclasses import asdict

from moira.named_muhurta import NamedMuhurtaDay, NamedMuhurtaResult
from ..models.named_muhurta import NamedMuhurtaDayResponse, NamedMuhurtaResponse


def serialize_named_muhurta(result: NamedMuhurtaResult) -> NamedMuhurtaResponse:
    return NamedMuhurtaResponse(**asdict(result), status=result.status)


def serialize_named_muhurta_day(day: NamedMuhurtaDay) -> NamedMuhurtaDayResponse:
    values = asdict(day)
    values["result"] = serialize_named_muhurta(day.result)
    return NamedMuhurtaDayResponse(**values)
