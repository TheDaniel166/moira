"""Serializers for planetary and sky-position vessels."""

from __future__ import annotations

from moira import PlanetData, SkyPosition

from ..models.positions import PlanetPositionResponse, SkyPositionResponse


def serialize_planet(planet: PlanetData) -> PlanetPositionResponse:
    """Serialize a canonical PlanetData vessel into transport form."""

    return PlanetPositionResponse(
        name=planet.name,
        longitude=planet.longitude,
        latitude=planet.latitude,
        distance=planet.distance,
        speed=planet.speed,
        retrograde=planet.retrograde,
        is_topocentric=planet.is_topocentric,
        sign=planet.sign,
        sign_symbol=planet.sign_symbol,
        sign_degree=planet.sign_degree,
        distance_au=planet.distance_au,
    )


def serialize_sky_position(position: SkyPosition) -> SkyPositionResponse:
    """Serialize a canonical SkyPosition vessel into transport form."""

    return SkyPositionResponse(
        name=position.name,
        right_ascension=position.right_ascension,
        declination=position.declination,
        azimuth=position.azimuth,
        altitude=position.altitude,
        distance=position.distance,
    )
