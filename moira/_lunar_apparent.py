"""Shared reader-bound lunar reception and illumination geometry."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

from ._ephemeris_time import _reader_identity_at, _ut1_to_ephemeris_tt
from .corrections import _observer_position_icrf, apply_aberration
from .julian import local_sidereal_time, tt_to_tdb
from .obliquity import nutation, true_obliquity
from .planets import _apply_rotation_matrix, _compose_rotation_matrix
from .spk_reader import KernelReader


_LIGHT_SPEED_KM_S = 299_792.458
_SECONDS_PER_DAY = 86_400.0


class LunarApparentGeometryError(RuntimeError):
    """Raised when reader-bound lunar apparent geometry cannot be formed."""


@dataclass(frozen=True, slots=True)
class LunarApparentContext:
    jd_ut1_reception: float
    jd_tt_reception: float
    jd_tdb_reception: float
    jd_tt_lunar_emission: float
    jd_tdb_lunar_emission: float
    jd_tt_solar_emission: float
    observer_distance_km: float
    observer_ssb_icrf: tuple[float, float, float]
    observer_to_moon_icrf: tuple[float, float, float]
    moon_to_sun_icrf: tuple[float, float, float] | None
    sky_north_icrf: tuple[float, float, float]
    sky_east_icrf: tuple[float, float, float]
    icrf_to_true_of_date: tuple[tuple[float, float, float], ...]
    translation_label: str


def _finite(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a real number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _norm(vector: Sequence[float]) -> tuple[float, float, float]:
    magnitude = math.sqrt(sum(float(value) ** 2 for value in vector))
    if not math.isfinite(magnitude) or magnitude <= 0.0:
        raise LunarApparentGeometryError("lunar apparent direction is undefined")
    return tuple(float(value) / magnitude for value in vector)  # type: ignore[return-value]


def _matrix_columns_from_transform(transform) -> tuple[tuple[float, ...], ...]:
    columns = tuple(
        transform(axis)
        for axis in ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
    )
    return (
        (columns[0][0], columns[1][0], columns[2][0]),
        (columns[0][1], columns[1][1], columns[2][1]),
        (columns[0][2], columns[1][2], columns[2][2]),
    )


def _transpose_matrix_vector(
    matrix: Sequence[Sequence[float]],
    vector: Sequence[float],
) -> tuple[float, float, float]:
    return tuple(
        sum(matrix[row][column] * vector[row] for row in range(3))
        for column in range(3)
    )  # type: ignore[return-value]


def _true_of_date_sky_basis(
    observer_to_moon_icrf: Sequence[float],
    icrf_to_true_of_date: Sequence[Sequence[float]],
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    los_of_date = _norm(
        tuple(
            sum(icrf_to_true_of_date[row][column] * observer_to_moon_icrf[column] for column in range(3))
            for row in range(3)
        )
    )
    right_ascension = math.atan2(los_of_date[1], los_of_date[0])
    declination = math.asin(max(-1.0, min(1.0, los_of_date[2])))
    north_of_date = (
        -math.sin(declination) * math.cos(right_ascension),
        -math.sin(declination) * math.sin(right_ascension),
        math.cos(declination),
    )
    east_of_date = (-math.sin(right_ascension), math.cos(right_ascension), 0.0)
    return (
        _norm(_transpose_matrix_vector(icrf_to_true_of_date, north_of_date)),
        _norm(_transpose_matrix_vector(icrf_to_true_of_date, east_of_date)),
    )


def lunar_apparent_context(
    jd_ut1: float,
    *,
    observer: tuple[float, float, float] | None,
    reader: KernelReader,
    include_solar: bool = True,
) -> LunarApparentContext:
    """Solve a DE441/LE441 reception light cone and lunar illumination ray.

    The observer-to-Moon down-leg is evaluated at the retarded lunar emission
    epoch as a geometric physical ray. The Moon-to-Sun up-leg is evaluated
    with the Moon fixed at that event and the Sun retarded by its one-way light
    time, then stellar aberration from the Moon's barycentric velocity is
    applied for the observer-compatible apparent illumination direction.
    """

    epoch = _finite("jd_ut1", jd_ut1)
    jd_tt = _ut1_to_ephemeris_tt(epoch, reader)
    jd_tdb = tt_to_tdb(jd_tt)
    identity = _reader_identity_at(reader, jd_tdb)
    if (
        identity is None
        or identity.planetary_ephemeris != "DE441"
        or identity.lunar_ephemeris != "LE441"
    ):
        label = None if identity is None else identity.summary_label
        raise LunarApparentGeometryError(
            "lunar orientation requires a content-identified DE441/LE441 "
            f"reader; received {label!r}"
        )

    rotation = _compose_rotation_matrix(jd_tt, with_nutation=True)

    def icrf_to_true_of_date(vector: Sequence[float]) -> tuple[float, float, float]:
        rotated = _apply_rotation_matrix(
            rotation, (float(vector[0]), float(vector[1]), float(vector[2]))
        )
        return (float(rotated[0]), float(rotated[1]), float(rotated[2]))

    full_rotation = _matrix_columns_from_transform(icrf_to_true_of_date)
    ssb_emb_reception = reader.position(0, 3, jd_tt)
    emb_earth_reception = reader.position(3, 399, jd_tt)
    earth_ssb = tuple(
        float(ssb_emb_reception[index]) + float(emb_earth_reception[index])
        for index in range(3)
    )

    if observer is None:
        observer_icrf = (0.0, 0.0, 0.0)
    else:
        latitude, longitude, elevation_m = observer
        dpsi_deg, _ = nutation(jd_tt)
        lst_deg = local_sidereal_time(
            epoch, longitude, dpsi_deg, true_obliquity(jd_tt)
        )
        observer_true_of_date = _observer_position_icrf(
            latitude,
            longitude,
            lst_deg,
            elevation_m,
            jd_ut=epoch,
            observer_frame="equatorial_of_date",
        )
        observer_icrf = _transpose_matrix_vector(
            full_rotation, observer_true_of_date
        )
    observer_ssb = tuple(
        earth_ssb[index] + observer_icrf[index] for index in range(3)
    )

    light_time_days = 1.3 / _SECONDS_PER_DAY
    moon_ssb = (0.0, 0.0, 0.0)
    moon_to_observer = (0.0, 0.0, 0.0)
    emission_jd_tt = jd_tt - light_time_days
    for _iteration in range(16):
        emission_jd_tt = jd_tt - light_time_days
        ssb_emb_emission = reader.position(0, 3, emission_jd_tt)
        emb_moon_emission = reader.position(3, 301, emission_jd_tt)
        moon_ssb = tuple(
            float(ssb_emb_emission[index]) + float(emb_moon_emission[index])
            for index in range(3)
        )
        moon_to_observer = tuple(
            observer_ssb[index] - moon_ssb[index] for index in range(3)
        )
        distance_km = math.sqrt(sum(value * value for value in moon_to_observer))
        if not math.isfinite(distance_km) or distance_km <= 0.0:
            raise LunarApparentGeometryError(
                "DE441 lunar light-cone distance must be finite and positive"
            )
        next_light_time_days = distance_km / (_LIGHT_SPEED_KM_S * _SECONDS_PER_DAY)
        if abs(next_light_time_days - light_time_days) <= 1.0e-12:
            light_time_days = next_light_time_days
            break
        light_time_days = next_light_time_days
    else:
        raise LunarApparentGeometryError(
            "DE441 lunar light-cone iteration did not converge"
        )

    sun_emission_jd_tt = emission_jd_tt
    apparent_moon_to_sun = None
    if include_solar:
        _, ssb_emb_velocity = reader.position_and_velocity(0, 3, emission_jd_tt)
        _, emb_moon_velocity = reader.position_and_velocity(3, 301, emission_jd_tt)
        moon_velocity_ssb = tuple(
            float(ssb_emb_velocity[index]) + float(emb_moon_velocity[index])
            for index in range(3)
        )
        sun_light_time_days = 499.0 / _SECONDS_PER_DAY
        sun_emission_jd_tt = emission_jd_tt - sun_light_time_days
        moon_to_sun = (0.0, 0.0, 0.0)
        for _iteration in range(16):
            sun_emission_jd_tt = emission_jd_tt - sun_light_time_days
            sun_ssb = reader.position(0, 10, sun_emission_jd_tt)
            moon_to_sun = tuple(
                float(sun_ssb[index]) - moon_ssb[index] for index in range(3)
            )
            distance_sun_km = math.sqrt(sum(value * value for value in moon_to_sun))
            if not math.isfinite(distance_sun_km) or distance_sun_km <= 0.0:
                raise LunarApparentGeometryError(
                    "DE441 lunar-to-solar light-cone distance must be finite and positive"
                )
            next_light_time_days = distance_sun_km / (
                _LIGHT_SPEED_KM_S * _SECONDS_PER_DAY
            )
            if abs(next_light_time_days - sun_light_time_days) <= 1.0e-12:
                sun_light_time_days = next_light_time_days
                break
            sun_light_time_days = next_light_time_days
        else:
            raise LunarApparentGeometryError(
                "DE441 lunar-to-solar light-cone iteration did not converge"
            )
        apparent_moon_to_sun = _norm(
            apply_aberration(moon_to_sun, moon_velocity_ssb)
        )

    observer_to_moon = _norm(tuple(-value for value in moon_to_observer))
    sky_north, sky_east = _true_of_date_sky_basis(
        observer_to_moon, full_rotation
    )
    return LunarApparentContext(
        jd_ut1_reception=epoch,
        jd_tt_reception=jd_tt,
        jd_tdb_reception=jd_tdb,
        jd_tt_lunar_emission=emission_jd_tt,
        jd_tdb_lunar_emission=tt_to_tdb(emission_jd_tt),
        jd_tt_solar_emission=sun_emission_jd_tt,
        observer_distance_km=distance_km,
        observer_ssb_icrf=observer_ssb,
        observer_to_moon_icrf=observer_to_moon,
        moon_to_sun_icrf=apparent_moon_to_sun,
        sky_north_icrf=sky_north,
        sky_east_icrf=sky_east,
        icrf_to_true_of_date=full_rotation,
        translation_label=identity.summary_label,
    )


__all__ = ["LunarApparentContext", "LunarApparentGeometryError"]
