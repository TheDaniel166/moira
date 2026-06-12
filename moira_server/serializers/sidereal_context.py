"""Serializers for request-scoped sidereal chart derivation contexts."""

from __future__ import annotations

from ..models.sidereal_context import (
    SiderealChartContextResponse,
    SiderealChartProvenanceResponse,
    SiderealHouseContextResponse,
    SiderealObserverResponse,
)
from ..services.sidereal_context import (
    SiderealChartContext,
    SiderealHouseContext,
    SiderealObserverContext,
)


def serialize_sidereal_observer_context(
    observer: SiderealObserverContext | None,
) -> SiderealObserverResponse | None:
    if observer is None:
        return None
    return SiderealObserverResponse(
        latitude=observer.latitude,
        longitude=observer.longitude,
        elevation_m=observer.elevation_m,
    )


def serialize_sidereal_house_context(
    houses: SiderealHouseContext | None,
) -> SiderealHouseContextResponse | None:
    if houses is None:
        return None
    return SiderealHouseContextResponse(
        system=houses.system,
        effective_system=houses.effective_system,
        ascendant=houses.ascendant,
        midheaven=houses.midheaven,
        cusps=list(houses.cusps),
    )


def serialize_sidereal_chart_provenance(
    context: SiderealChartContext,
) -> SiderealChartProvenanceResponse:
    return SiderealChartProvenanceResponse(
        requested_datetime=context.requested_datetime,
        normalized_datetime_utc=context.normalized_datetime_utc,
        jd_ut=context.jd_ut,
        ayanamsa_system=context.ayanamsa_system,
        ayanamsa_offset=context.ayanamsa_offset,
        requested_bodies=list(context.requested_bodies),
        returned_bodies=list(context.returned_bodies),
        observer=serialize_sidereal_observer_context(context.observer),
        sidereal_longitudes=dict(context.sidereal_longitudes),
        tropical_lagna=context.tropical_lagna,
        sidereal_lagna=context.sidereal_lagna,
        sidereal_lagna_sign_index=context.sidereal_lagna_sign_index,
        house_system=(context.houses.effective_system if context.houses is not None else None),
        stage_sequence=list(context.stage_sequence),
    )


def serialize_sidereal_chart_context(
    context: SiderealChartContext,
) -> SiderealChartContextResponse:
    provenance = serialize_sidereal_chart_provenance(context)
    return SiderealChartContextResponse(
        **provenance.model_dump(),
        tropical_longitudes=dict(context.tropical_longitudes),
        sidereal_sign_indices=dict(context.sidereal_sign_indices),
        speeds=(dict(context.speeds) if context.speeds is not None else None),
        houses=serialize_sidereal_house_context(context.houses),
    )


__all__ = [
    "serialize_sidereal_chart_context",
    "serialize_sidereal_chart_provenance",
    "serialize_sidereal_house_context",
    "serialize_sidereal_observer_context",
]
