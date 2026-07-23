from __future__ import annotations

import pytest

from moira.eclipse import SolarEclipseFootprintBoundaryKind
from moira.julian import julian_day


pytestmark = [pytest.mark.requires_ephemeris, pytest.mark.slow]


def _track_structure(footprint):
    return tuple(
        sorted(
            (
                track.kind.value,
                track.component_id,
                track.segment_id,
            )
            for track in footprint.tracks
        )
    )


def test_2049_hybrid_near_singular_horizon_junction_is_not_lost(
    eclipse_calculator,
) -> None:
    sparse = eclipse_calculator.solar_eclipse_footprint(
        julian_day(2048, 1, 1),
        kind="hybrid",
        sample_count=9,
    )
    dense = eclipse_calculator.solar_eclipse_footprint(
        julian_day(2048, 1, 1),
        kind="hybrid",
        sample_count=181,
    )

    assert _track_structure(sparse) == _track_structure(dense)
    north_tracks = tuple(
        track
        for track in sparse.tracks
        if track.kind is SolarEclipseFootprintBoundaryKind.PENUMBRAL_NORTH
    )
    assert len(north_tracks) == 2
    assert {track.component_id for track in north_tracks} == {0}

    horizon_points = tuple(
        point
        for track in sparse.tracks
        if track.kind
        in {
            SolarEclipseFootprintBoundaryKind.SUNRISE,
            SolarEclipseFootprintBoundaryKind.SUNSET,
        }
        for point in track.points
    )
    incidences = {
        (
            round(endpoint.jd_ut, 10),
            round(endpoint.latitude_deg, 8),
            round(endpoint.longitude_deg, 8),
        )
        for track in north_tracks
        for endpoint in (track.points[0], track.points[-1])
        if any(endpoint == horizon_point for horizon_point in horizon_points)
    }
    assert len(incidences) == 2
