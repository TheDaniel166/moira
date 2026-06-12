"""Serializers for Phase-9 Varga vessels (P9-11)."""

from __future__ import annotations

from moira.varga import VargaPoint

from ..models.varga import (
    VargaChartNamedResponse,
    VargaChartShodashvargaBatchResponse,
    VargaChartShodashvargaResponse,
    VargaNamedBatchResponse,
    VargaPointResponse,
    VargaShodashvargaBatchResponse,
    VargaShodashvargaResponse,
)
from .sidereal_context import serialize_sidereal_chart_provenance


def serialize_varga_point(point: VargaPoint) -> VargaPointResponse:
    return VargaPointResponse(
        varga_name=point.varga_name,
        varga_number=point.varga_number,
        longitude=point.longitude,
        varga_longitude=point.varga_longitude,
        sign=point.sign,
        sign_symbol=point.sign_symbol,
        sign_degree=point.sign_degree,
    )


def serialize_varga_shodashvarga(
    *,
    sidereal_longitude: float,
    vargas: dict[str, VargaPoint],
) -> VargaShodashvargaResponse:
    return VargaShodashvargaResponse(
        sidereal_longitude=sidereal_longitude,
        vargas={
            selector: serialize_varga_point(point)
            for selector, point in vargas.items()
        },
    )


def serialize_varga_named_batch(
    *,
    varga: str,
    results: dict[str, VargaPoint],
) -> VargaNamedBatchResponse:
    return VargaNamedBatchResponse(
        varga=varga,
        results={
            key: serialize_varga_point(point)
            for key, point in results.items()
        },
    )


def serialize_varga_shodashvarga_batch(
    results: dict[str, dict[str, VargaPoint]],
) -> VargaShodashvargaBatchResponse:
    return VargaShodashvargaBatchResponse(
        results={
            key: {
                selector: serialize_varga_point(point)
                for selector, point in vargas.items()
            }
            for key, vargas in results.items()
        },
    )


def serialize_varga_chart_named(
    *,
    body: str,
    varga: str,
    result: VargaPoint,
    context,
) -> VargaChartNamedResponse:
    return VargaChartNamedResponse(
        body=body,
        varga=varga,
        result=serialize_varga_point(result),
        provenance=serialize_sidereal_chart_provenance(context),
    )


def serialize_varga_chart_shodashvarga(
    *,
    body: str,
    results: dict[str, VargaPoint],
    context,
) -> VargaChartShodashvargaResponse:
    return VargaChartShodashvargaResponse(
        body=body,
        result=serialize_varga_shodashvarga(
            sidereal_longitude=context.sidereal_longitudes[body],
            vargas=results,
        ),
        provenance=serialize_sidereal_chart_provenance(context),
    )


def serialize_varga_chart_shodashvarga_batch(
    *,
    results: dict[str, dict[str, VargaPoint]],
    context,
) -> VargaChartShodashvargaBatchResponse:
    return VargaChartShodashvargaBatchResponse(
        results={
            body: {
                selector: serialize_varga_point(point)
                for selector, point in vargas.items()
            }
            for body, vargas in results.items()
        },
        provenance=serialize_sidereal_chart_provenance(context),
    )


__all__ = [
    "serialize_varga_chart_named",
    "serialize_varga_chart_shodashvarga",
    "serialize_varga_chart_shodashvarga_batch",
    "serialize_varga_named_batch",
    "serialize_varga_point",
    "serialize_varga_shodashvarga",
    "serialize_varga_shodashvarga_batch",
]
