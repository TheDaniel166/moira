"""Typed transport for supplied spherical and horizon directions."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from moira.coordinates import EclipticEquatorialTransformTruth, HorizontalToEquatorialTruth

from .common import _StrictModel


_Angle = Annotated[float, Field(strict=True, allow_inf_nan=False)]
_Latitude = Annotated[_Angle, Field(ge=-90.0, le=90.0)]


class _ObliquityRequest(_StrictModel):
    """Caller-supplied axial tilt for a rotation about the common equinox."""

    obliquity_deg: Annotated[_Angle, Field(ge=0.0, le=180.0)]


class EclipticToEquatorialRequest(_ObliquityRequest):
    """Rotate supplied ecliptic spherical coordinates to the equator."""

    transform: Literal["ecliptic_to_equatorial"]
    ecliptic_longitude_deg: _Angle | None = Field(
        default=None, description="Required away from either ecliptic pole.",
    )
    ecliptic_latitude_deg: _Latitude


class EquatorialToEclipticRequest(_ObliquityRequest):
    """Rotate supplied equatorial spherical coordinates to the ecliptic."""

    transform: Literal["equatorial_to_ecliptic"]
    right_ascension_deg: _Angle | None = Field(
        default=None, description="Required away from either celestial pole.",
    )
    declination_deg: _Latitude


class HorizontalToEquatorialRequest(_StrictModel):
    """Invert a geometric horizon direction at the supplied sidereal meridian."""

    transform: Literal["horizontal_to_equatorial"]
    azimuth_deg: _Angle | None = Field(
        default=None, description="Clockwise from north. Required away from zenith and nadir.",
    )
    altitude_deg: _Latitude
    local_sidereal_time_deg: _Angle
    observer_latitude_deg: _Latitude


CoordinateTransformRequest = Annotated[
    EclipticToEquatorialRequest | EquatorialToEclipticRequest | HorizontalToEquatorialRequest,
    Field(discriminator="transform"),
]

CoordinateTransformResponse = Annotated[
    EclipticEquatorialTransformTruth | HorizontalToEquatorialTruth,
    Field(discriminator="transform"),
]
