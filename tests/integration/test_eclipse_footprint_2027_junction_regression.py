from __future__ import annotations

import pytest

from moira.eclipse import (
    SolarEclipseFootprintBoundaryKind,
    _footprint_points_coincide,
)
from moira.julian import julian_day


pytestmark = [pytest.mark.requires_ephemeris, pytest.mark.slow]

_AUGUST_2027_SEED_JD = julian_day(2027, 8, 1)
_PENUMBRAL_KINDS = (
    SolarEclipseFootprintBoundaryKind.PENUMBRAL_NORTH,
    SolarEclipseFootprintBoundaryKind.PENUMBRAL_SOUTH,
)


@pytest.mark.parametrize("sample_count", [9, 181, 721])
def test_august_2027_fold_retains_both_horizon_incidences(
    eclipse_calculator,
    sample_count: int,
) -> None:
    """Pin the close-root sunrise junction that 5.1.1 left open."""

    footprint = eclipse_calculator.solar_eclipse_footprint(
        _AUGUST_2027_SEED_JD,
        kind="total",
        sample_count=sample_count,
    )

    assert footprint.event.datetime_utc.year == 2027
    assert footprint.event.datetime_utc.month == 8
    assert footprint.event.datetime_utc.day == 2

    horizon_points = tuple(
        point
        for track in footprint.tracks
        if track.kind
        in {
            SolarEclipseFootprintBoundaryKind.SUNRISE,
            SolarEclipseFootprintBoundaryKind.SUNSET,
        }
        for point in track.points
    )
    for kind in _PENUMBRAL_KINDS:
        tracks = tuple(track for track in footprint.tracks if track.kind is kind)
        incidences = []
        for track in tracks:
            for endpoint in (track.points[0], track.points[-1]):
                if not any(
                    _footprint_points_coincide(endpoint, horizon_point)
                    for horizon_point in horizon_points
                ):
                    continue
                if not any(
                    _footprint_points_coincide(endpoint, admitted)
                    for admitted in incidences
                ):
                    incidences.append(endpoint)
        assert len(incidences) == 2
