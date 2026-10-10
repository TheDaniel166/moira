"""Lossless canonical projection; no Muhurta arithmetic."""
from dataclasses import asdict

from ..models.special_muhurta import SpecialMuhurtaSolarResponse, MuhurtaYogaResponse, SpecialMuhurtaDayResponse
from .named_muhurta import serialize_named_muhurta_day


def serialize_special_muhurta_solar(result):
    return SpecialMuhurtaSolarResponse(**asdict(result), status=result.status)


def serialize_muhurta_yogas(result):
    return MuhurtaYogaResponse(**asdict(result))


def serialize_special_muhurta_day(result):
    values = asdict(result)
    values["named"] = serialize_named_muhurta_day(result.named)
    return SpecialMuhurtaDayResponse(**values, status=result.status)
