"""Serializers for Phase-9 decans/decanates vessels (P9-12)."""

from __future__ import annotations

from moira.decanates import DecanatePosition

from ..models.decans import (
    DecanateChartPositionResponse,
    DecanateChartSetResponse,
    DecanatePositionResponse,
    DecanateSetResponse,
)
from ..services.decans import DecanateChartPositionResult, DecanateChartSetResult
from .sidereal_context import serialize_sidereal_chart_provenance


def serialize_decanate_position(position: DecanatePosition) -> DecanatePositionResponse:
    return DecanatePositionResponse(
        system=position.system,
        decan_number=position.decan_number,
        ruling_planet=position.ruling_planet,
        ruling_sign=position.ruling_sign,
        sign=position.sign,
        sign_symbol=position.sign_symbol,
        degree_in_decan=position.degree_in_decan,
        longitude_used=position.longitude_used,
    )


def serialize_decanate_set(
    positions: dict[str, DecanatePosition],
) -> DecanateSetResponse:
    return DecanateSetResponse(
        chaldean_face=serialize_decanate_position(positions["chaldean_face"]),
        triplicity=serialize_decanate_position(positions["triplicity"]),
        vedic_drekkana=serialize_decanate_position(positions["vedic_drekkana"]),
    )


def serialize_decanate_chart_position(
    result: DecanateChartPositionResult,
) -> DecanateChartPositionResponse:
    return DecanateChartPositionResponse(
        body=result.body,
        result=serialize_decanate_position(result.position),
        tropical_longitude=result.context.tropical_longitudes[result.body],
        jd=result.context.jd_ut,
        provenance=serialize_sidereal_chart_provenance(result.context),
    )


def serialize_decanate_chart_set(
    result: DecanateChartSetResult,
) -> DecanateChartSetResponse:
    return DecanateChartSetResponse(
        body=result.body,
        result=serialize_decanate_set(result.positions),
        tropical_longitude=result.context.tropical_longitudes[result.body],
        jd=result.context.jd_ut,
        provenance=serialize_sidereal_chart_provenance(result.context),
    )


__all__ = [
    "serialize_decanate_chart_position",
    "serialize_decanate_chart_set",
    "serialize_decanate_position",
    "serialize_decanate_set",
]
