"""Bind supplied coordinate requests to the canonical geometry reducers."""

from __future__ import annotations

from moira.coordinates import horizontal_to_equatorial_with_truth, transform_ecliptic_equatorial_with_truth

from ..models.coordinates import (
    CoordinateTransformRequest,
    CoordinateTransformResponse,
    EclipticToEquatorialRequest,
    EquatorialToEclipticRequest,
)


def transform_coordinates(request: CoordinateTransformRequest) -> CoordinateTransformResponse:
    """Return the engine's direction, frame and singularity truth."""

    if isinstance(request, EclipticToEquatorialRequest):
        return transform_ecliptic_equatorial_with_truth(
            request.ecliptic_longitude_deg,
            request.ecliptic_latitude_deg,
            request.obliquity_deg,
            transform=request.transform,
        )
    if isinstance(request, EquatorialToEclipticRequest):
        return transform_ecliptic_equatorial_with_truth(
            request.right_ascension_deg,
            request.declination_deg,
            request.obliquity_deg,
            transform=request.transform,
        )
    return horizontal_to_equatorial_with_truth(
        request.azimuth_deg,
        request.altitude_deg,
        request.local_sidereal_time_deg,
        request.observer_latitude_deg,
    )
