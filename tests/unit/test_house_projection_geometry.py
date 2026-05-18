"""
House projection geometry covenant tests.

These are primary proof tests for the Moira-owned house substrate. They verify
the governing geometry directly and do not depend on an external software oracle.
"""

from __future__ import annotations

import math

import pytest

from moira.houses import (
    _dot3,
    _ecliptic_longitude_from_equatorial_vector,
    _ecliptic_north_vector,
    _equatorial_ecliptic_direction,
    _project_ra_with_pole,
    _ra_pole_plane_normal,
)


@pytest.mark.parametrize(
    ("ra_deg", "pole_height_deg", "obliquity_deg"),
    [
        (0.0, 0.0, 23.4392911),
        (15.0, 12.5, 23.4392911),
        (90.0, -18.0, 23.4392911),
        (179.75, 45.0, 23.4392911),
        (245.0, -52.5, 23.4392911),
        (315.0, 80.0, 23.4392911),
    ],
)
def test_project_ra_with_pole_matches_closed_form(
    ra_deg: float,
    pole_height_deg: float,
    obliquity_deg: float,
    moira_approx,
    assert_longitude,
) -> None:
    projected = _project_ra_with_pole(ra_deg, pole_height_deg, obliquity_deg)
    assert_longitude(projected, label="projected longitude")

    ra_r = math.radians(ra_deg)
    pole_r = math.radians(pole_height_deg)
    eps_r = math.radians(obliquity_deg)
    expected = math.degrees(
        math.atan2(
            math.sin(ra_r),
            math.cos(ra_r) * math.cos(eps_r) - math.tan(pole_r) * math.sin(eps_r),
        )
    ) % 360.0

    assert projected == moira_approx(expected, kind="longitude")


@pytest.mark.parametrize(
    ("ra_deg", "pole_height_deg", "obliquity_deg"),
    [
        (12.0, -55.0, 23.4392911),
        (77.0, 0.0, 23.4),
        (123.456, 28.0, 23.7),
        (271.0, -35.0, 22.8),
        (359.0, 72.0, 24.1),
    ],
)
def test_projected_direction_lies_on_both_governing_planes(
    ra_deg: float,
    pole_height_deg: float,
    obliquity_deg: float,
) -> None:
    projected = _project_ra_with_pole(ra_deg, pole_height_deg, obliquity_deg)
    direction = _equatorial_ecliptic_direction(projected, obliquity_deg)
    plane_normal = _ra_pole_plane_normal(ra_deg, pole_height_deg)
    ecliptic_north = _ecliptic_north_vector(obliquity_deg)

    assert _dot3(direction, plane_normal) == pytest.approx(0.0, abs=1e-12)
    assert _dot3(direction, ecliptic_north) == pytest.approx(0.0, abs=1e-12)


@pytest.mark.parametrize("obliquity_deg", [22.0, 23.4392911, 24.5])
@pytest.mark.parametrize("longitude_deg", [0.0, 17.5, 90.0, 183.25, 359.9])
def test_equatorial_ecliptic_round_trip(
    obliquity_deg: float,
    longitude_deg: float,
    moira_approx,
    assert_longitude,
) -> None:
    direction = _equatorial_ecliptic_direction(longitude_deg, obliquity_deg)
    recovered = _ecliptic_longitude_from_equatorial_vector(direction, obliquity_deg)

    assert_longitude(recovered, label="recovered longitude")
    assert recovered == moira_approx(longitude_deg % 360.0, kind="longitude")
