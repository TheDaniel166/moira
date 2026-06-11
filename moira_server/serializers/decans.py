"""Serializers for Phase-9 decans/decanates vessels (P9-12)."""

from __future__ import annotations

from moira.decanates import DecanatePosition
from moira.hermetic_decans import DecanHoursNight

from ..models.decans import (
    DecanatePositionResponse,
    DecanateSetResponse,
    HermeticDecanCatalogResponse,
    HermeticDecanEntryResponse,
    HermeticDecanHourResponse,
    HermeticDecanLookupResponse,
    HermeticDecanNightHoursResponse,
)


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


def serialize_hermetic_decan_catalog(
    entries: list[tuple[int, str, str]],
) -> HermeticDecanCatalogResponse:
    return HermeticDecanCatalogResponse(
        decans=[
            HermeticDecanEntryResponse(
                index=index,
                name=name,
                ruling_star=ruling_star,
            )
            for index, name, ruling_star in entries
        ]
    )


def serialize_hermetic_decan_lookup(
    *,
    name: str,
    index: int,
    ruling_star: str,
    longitude: float | None = None,
    jd: float | None = None,
    latitude: float | None = None,
    observer_longitude: float | None = None,
) -> HermeticDecanLookupResponse:
    normalized_longitude = longitude % 360.0 if longitude is not None else None
    return HermeticDecanLookupResponse(
        longitude=longitude,
        normalized_longitude=normalized_longitude,
        jd=jd,
        latitude=latitude,
        observer_longitude=observer_longitude,
        index=index,
        name=name,
        ruling_star=ruling_star,
    )


def serialize_hermetic_decan_night_hours(
    night: DecanHoursNight,
) -> HermeticDecanNightHoursResponse:
    return HermeticDecanNightHoursResponse(
        date_jd=night.date_jd,
        latitude=night.latitude,
        longitude=night.longitude,
        sunset_jd=night.sunset_jd,
        next_sunrise_jd=night.next_sunrise_jd,
        hours=[
            HermeticDecanHourResponse(
                hour_number=hour.hour_number,
                decan=hour.decan,
                ruling_star=hour.ruling_star,
                jd_start=hour.jd_start,
                jd_end=hour.jd_end,
            )
            for hour in night.hours
        ],
    )


__all__ = [
    "serialize_decanate_position",
    "serialize_decanate_set",
    "serialize_hermetic_decan_catalog",
    "serialize_hermetic_decan_lookup",
    "serialize_hermetic_decan_night_hours",
]
