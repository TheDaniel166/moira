"""Service helpers for Phase-9 decans/decanates routes (P9-12)."""

from __future__ import annotations

from moira.decanates import (
    DecanatePosition,
    chaldean_face,
    triplicity_decan,
    vedic_drekkana,
)
from moira.hermetic_decans import (
    DECAN_RULING_STARS,
    DecanHoursNight,
    decan_at,
    decan_for_longitude,
    decan_hours,
    decan_index,
    list_decans,
)

from ..models.decans import (
    DecanateLongitudeRequest,
    DecanateSetRequest,
    HermeticLocationRequest,
    HermeticLongitudeRequest,
    VedicDrekkanaRequest,
)


def compute_chaldean_face(request: DecanateLongitudeRequest) -> DecanatePosition:
    return chaldean_face(request.longitude)


def compute_triplicity_decan(request: DecanateLongitudeRequest) -> DecanatePosition:
    return triplicity_decan(request.longitude)


def compute_vedic_drekkana(request: VedicDrekkanaRequest) -> DecanatePosition:
    return vedic_drekkana(
        request.longitude,
        request.jd,
        ayanamsa_system=request.ayanamsa_system,
    )


def compute_decanate_set(
    request: DecanateSetRequest,
) -> dict[str, DecanatePosition]:
    return {
        "chaldean_face": chaldean_face(request.longitude),
        "triplicity": triplicity_decan(request.longitude),
        "vedic_drekkana": vedic_drekkana(
            request.longitude,
            request.jd,
            ayanamsa_system=request.ayanamsa_system,
        ),
    }


def list_hermetic_decan_catalog() -> list[tuple[int, str, str]]:
    return [
        (index, name, DECAN_RULING_STARS[name])
        for index, name in enumerate(list_decans())
    ]


def compute_hermetic_decan_longitude(
    request: HermeticLongitudeRequest,
) -> tuple[str, int, str]:
    name = decan_for_longitude(request.longitude)
    return name, decan_index(name), DECAN_RULING_STARS[name]


def compute_hermetic_rising_decan(
    request: HermeticLocationRequest,
) -> tuple[str, int, str]:
    name = decan_at(request.jd, request.latitude, request.longitude)
    return name, decan_index(name), DECAN_RULING_STARS[name]


def compute_hermetic_decan_night_hours(
    request: HermeticLocationRequest,
) -> DecanHoursNight:
    return decan_hours(request.jd, request.latitude, request.longitude)


__all__ = [
    "compute_chaldean_face",
    "compute_decanate_set",
    "compute_hermetic_decan_longitude",
    "compute_hermetic_decan_night_hours",
    "compute_hermetic_rising_decan",
    "compute_triplicity_decan",
    "compute_vedic_drekkana",
    "list_hermetic_decan_catalog",
]
