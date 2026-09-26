"""Public lunar libration and visible-disc orientation product."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

from ._lunar_apparent import LunarApparentGeometryError, lunar_apparent_context
from ._lunar_orientation_resources import (
    LunarOrientationCoverageError,
    LunarOrientationResourceError,
    LunarOrientationResourceIdentityError,
    LunarOrientationResourceMissingError,
    lunar_me_rotation,
    lunar_orientation_resources,
)
from .spk_reader import KernelReader, SpkReader, get_reader


def _finite(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a real number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


@dataclass(frozen=True, slots=True)
class LunarObserver:
    """WGS-84 geodetic observer used for topocentric lunar orientation."""

    latitude_deg: float
    longitude_deg: float
    elevation_m: float = 0.0

    def __post_init__(self) -> None:
        latitude = _finite("latitude_deg", self.latitude_deg)
        longitude = _finite("longitude_deg", self.longitude_deg)
        elevation = _finite("elevation_m", self.elevation_m)
        if not -90.0 <= latitude <= 90.0:
            raise ValueError("latitude_deg must be in [-90, 90]")
        if not -180.0 <= longitude <= 180.0:
            raise ValueError("longitude_deg must be in [-180, 180]")
        object.__setattr__(self, "latitude_deg", latitude)
        object.__setattr__(self, "longitude_deg", longitude)
        object.__setattr__(self, "elevation_m", elevation)


@dataclass(frozen=True, slots=True)
class LunarOrientationSource:
    """Exact translation, orientation, frame, and light-time provenance."""

    translation_model: str
    orientation_model: str
    body_fixed_frame: str
    pck_sha256: str
    frame_kernel_sha256: str
    coverage_start_jd_tdb: float
    coverage_end_jd_tdb: float
    light_time_model: str
    input_time_scale: str
    orientation_time_scale: str


@dataclass(frozen=True, slots=True)
class LunarOrientation:
    """Total apparent lunar libration and visible-disc orientation."""

    jd_ut1: float
    observer: LunarObserver | None
    sub_observer_longitude_east_deg: float
    sub_observer_latitude_deg: float
    sub_solar_longitude_east_deg: float
    sub_solar_latitude_deg: float
    axis_position_angle_deg: float
    bright_limb_position_angle_deg: float | None
    solar_colongitude_deg: float
    source: LunarOrientationSource

    @property
    def libration_longitude_deg(self) -> float:
        """Alias for east-positive total apparent sub-observer longitude."""

        return self.sub_observer_longitude_east_deg

    @property
    def libration_latitude_deg(self) -> float:
        """Alias for north-positive total apparent sub-observer latitude."""

        return self.sub_observer_latitude_deg


def _apply(
    matrix: Sequence[Sequence[float]], vector: Sequence[float]
) -> tuple[float, float, float]:
    return tuple(
        sum(matrix[row][column] * vector[column] for column in range(3))
        for row in range(3)
    )  # type: ignore[return-value]


def _transpose_apply(
    matrix: Sequence[Sequence[float]], vector: Sequence[float]
) -> tuple[float, float, float]:
    return tuple(
        sum(matrix[row][column] * vector[row] for row in range(3))
        for column in range(3)
    )  # type: ignore[return-value]


def _dot(left: Sequence[float], right: Sequence[float]) -> float:
    return sum(left[index] * right[index] for index in range(3))


def _lon_lat(vector: Sequence[float]) -> tuple[float, float]:
    radius = math.sqrt(sum(value * value for value in vector))
    if not math.isfinite(radius) or radius <= 0.0:
        raise LunarApparentGeometryError("lunar body-fixed direction is undefined")
    longitude = math.degrees(math.atan2(vector[1], vector[0]))
    longitude = ((longitude + 180.0) % 360.0) - 180.0
    latitude = math.degrees(math.asin(max(-1.0, min(1.0, vector[2] / radius))))
    return longitude, latitude


def _position_angle(
    direction_icrf: Sequence[float],
    sky_north_icrf: Sequence[float],
    sky_east_icrf: Sequence[float],
    *,
    allow_singular: bool,
) -> float | None:
    north = _dot(direction_icrf, sky_north_icrf)
    east = _dot(direction_icrf, sky_east_icrf)
    if math.hypot(north, east) <= 1.0e-15:
        if allow_singular:
            return None
        raise LunarApparentGeometryError(
            "lunar north-pole position angle is undefined"
        )
    return math.degrees(math.atan2(east, north)) % 360.0


def lunar_orientation_at(
    jd_ut1: float,
    *,
    observer: LunarObserver | None = None,
    reader: SpkReader | KernelReader | None = None,
) -> LunarOrientation:
    """Return total apparent lunar libration and disc orientation.

    Longitudes are east-positive in ``[-180, 180)``. Position angles are
    eastward/counter-clockwise from true-of-date celestial north in a
    north-up view. ``observer=None`` selects the geocentre.
    """

    epoch = _finite("jd_ut1", jd_ut1)
    if observer is not None and not isinstance(observer, LunarObserver):
        raise TypeError("observer must be LunarObserver or None")
    active_reader = get_reader() if reader is None else reader
    observer_tuple = None
    if observer is not None:
        observer_tuple = (
            observer.latitude_deg,
            observer.longitude_deg,
            observer.elevation_m,
        )
    apparent = lunar_apparent_context(
        epoch, observer=observer_tuple, reader=active_reader
    )
    resources = lunar_orientation_resources()
    j2000_to_me = lunar_me_rotation(apparent.jd_tdb_lunar_emission)
    if apparent.moon_to_sun_icrf is None:
        raise LunarApparentGeometryError(
            "lunar orientation requires an apparent Moon-to-Sun direction"
        )

    moon_to_observer_icrf = tuple(
        -value for value in apparent.observer_to_moon_icrf
    )
    moon_to_observer_me = _apply(j2000_to_me, moon_to_observer_icrf)
    moon_to_sun_me = _apply(j2000_to_me, apparent.moon_to_sun_icrf)
    subobserver_lon, subobserver_lat = _lon_lat(moon_to_observer_me)
    subsolar_lon, subsolar_lat = _lon_lat(moon_to_sun_me)

    lunar_north_icrf = _transpose_apply(j2000_to_me, (0.0, 0.0, 1.0))
    axis_pa = _position_angle(
        lunar_north_icrf,
        apparent.sky_north_icrf,
        apparent.sky_east_icrf,
        allow_singular=False,
    )
    bright_limb_pa = _position_angle(
        apparent.moon_to_sun_icrf,
        apparent.sky_north_icrf,
        apparent.sky_east_icrf,
        allow_singular=True,
    )

    source = LunarOrientationSource(
        translation_model=apparent.translation_label,
        orientation_model=resources.orientation_model,
        body_fixed_frame=resources.target_frame_name,
        pck_sha256=resources.pck_sha256,
        frame_kernel_sha256=resources.frame_kernel_sha256,
        coverage_start_jd_tdb=resources.coverage_start_jd_tdb,
        coverage_end_jd_tdb=resources.coverage_end_jd_tdb,
        light_time_model=(
            "DE441/LE441 physical down-leg observer reception; retarded "
            "Sun-to-Moon up-leg with lunar-velocity stellar aberration"
        ),
        input_time_scale="UT1",
        orientation_time_scale="TDB at retarded lunar emission",
    )
    return LunarOrientation(
        jd_ut1=epoch,
        observer=observer,
        sub_observer_longitude_east_deg=subobserver_lon,
        sub_observer_latitude_deg=subobserver_lat,
        sub_solar_longitude_east_deg=subsolar_lon,
        sub_solar_latitude_deg=subsolar_lat,
        axis_position_angle_deg=float(axis_pa),
        bright_limb_position_angle_deg=bright_limb_pa,
        solar_colongitude_deg=(90.0 - subsolar_lon) % 360.0,
        source=source,
    )


__all__ = [
    "LunarApparentGeometryError",
    "LunarObserver",
    "LunarOrientation",
    "LunarOrientationCoverageError",
    "LunarOrientationResourceError",
    "LunarOrientationResourceIdentityError",
    "LunarOrientationResourceMissingError",
    "LunarOrientationSource",
    "lunar_orientation_at",
]
