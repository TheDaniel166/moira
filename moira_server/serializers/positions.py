"""Serializers for planetary and sky-position vessels."""

from __future__ import annotations

from moira import PlanetData, SkyPosition

from ..models.positions import (
    PlanetPositionReductionResponse,
    PlanetPositionReductionTruthResponse,
    PlanetPositionResponse,
    PlanetReductionStageResponse,
    PositionObserverContextResponse,
    SkyPositionReductionResponse,
    SkyPositionReductionTruthResponse,
    SkyPositionResponse,
)
from ..services.positions import PlanetPositionReductionContext, SkyPositionReductionContext


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


def _serialize_observer_context(context) -> PositionObserverContextResponse:
    return PositionObserverContextResponse(
        latitude=context.latitude,
        longitude=context.longitude,
        elevation_m=context.elevation_m,
        local_sidereal_time_deg=context.local_sidereal_time_deg,
    )


def _serialize_planet_reduction_stages(
    breakdown,
) -> list[PlanetReductionStageResponse] | None:
    if breakdown is None:
        return None
    return [
        PlanetReductionStageResponse(
            num=stage.num,
            name=stage.name,
            note=stage.note,
            delta=stage.delta,
            enabled=stage.enabled,
            ref_pos=stage.ref_pos,
        )
        for stage in breakdown.stages
    ]


def serialize_planet_with_reduction(
    planet: PlanetData,
    reduction: PlanetPositionReductionContext,
) -> PlanetPositionReductionResponse:
    """Serialize a planetary position with its reduction truth (using actual requested/applied from context)."""

    return PlanetPositionReductionResponse(
        result=serialize_planet(planet),
        reduction=PlanetPositionReductionTruthResponse(
            engine_surface="Moira.planet_at",
            source_vessel="PlanetData",
            requested_datetime=reduction.requested_datetime,
            normalized_datetime_utc=reduction.normalized_datetime_utc,
            jd_ut=reduction.jd_ut,
            jd_tt=reduction.jd_tt,
            delta_t_seconds=reduction.delta_t_seconds,
            body=planet.name,
            observer=_serialize_observer_context(reduction.observer),
            stage_sequence=reduction.stage_sequence,
            selection_surface="planet_at",
            include_nodes=False,
            apparent=reduction.apparent,
            aberration=reduction.aberration,
            grav_deflection=reduction.grav_deflection,
            nutation=reduction.nutation,
            frame="ecliptic",
            center="geocentric",
            obliquity_deg=reduction.obliquity_deg,
            topocentric_requested=reduction.topocentric_requested,
            topocentric_applied=reduction.topocentric_applied,
            stages=_serialize_planet_reduction_stages(reduction.breakdown),
            total_delta_arcsec=(
                reduction.breakdown.total_delta_arcsec if reduction.breakdown is not None else None
            ),
            stage_longitudes=(
                dict(reduction.breakdown.stage_longitudes) if reduction.breakdown is not None else None
            ),
            geocentric_longitude=(
                reduction.breakdown.geocentric_longitude if reduction.breakdown is not None else None
            ),
        ),
    )


def serialize_sky_position_with_reduction(
    position: SkyPosition,
    reduction: SkyPositionReductionContext,
) -> SkyPositionReductionResponse:
    """Serialize a sky position with its reduction truth (using actual from context, no hardcodes)."""

    return SkyPositionReductionResponse(
        result=serialize_sky_position(position),
        reduction=SkyPositionReductionTruthResponse(
            engine_surface="Moira.sky_position",
            source_vessel="SkyPosition",
            requested_datetime=reduction.requested_datetime,
            normalized_datetime_utc=reduction.normalized_datetime_utc,
            jd_ut=reduction.jd_ut,
            jd_tt=reduction.jd_tt,
            delta_t_seconds=reduction.delta_t_seconds,
            body=position.name,
            observer=_serialize_observer_context(reduction.observer),
            stage_sequence=reduction.stage_sequence,
            apparent=reduction.aberration,  # note: for sky the 'apparent' in truth aligns to the first corrections
            aberration=reduction.aberration,
            grav_deflection=reduction.grav_deflection,
            nutation=reduction.nutation,
            refraction=reduction.refraction,
            pressure_mbar=reduction.pressure_mbar,
            temperature_c=reduction.temperature_c,
            relative_humidity=reduction.relative_humidity,
            obliquity_deg=reduction.obliquity_deg,
            coordinate_frames=["equatorial", "horizontal"],
        ),
    )
