"""
House projection geometry covenant tests.

These are primary proof tests for the Moira-owned house substrate. They verify
the governing geometry directly and do not depend on an external software oracle.
"""

from __future__ import annotations

import math

import pytest

import moira.houses as houses_module
from moira.constants import HouseSystem
from moira.houses import (
    HousePolicy,
    _LocalAngles,
    _asc_from_armc,
    _dot3,
    _ecliptic_longitude_from_equatorial_vector,
    _ecliptic_north_vector,
    _equatorial_ecliptic_direction,
    _local_angles_at,
    _mc_from_armc,
    _project_ra_with_pole,
    _ra_pole_plane_normal,
    calculate_houses,
    houses_from_armc,
)
from moira.julian import local_sidereal_time, ut_to_tt
from moira.obliquity import nutation, true_obliquity
from support.numeric_assertions import (
    NumericSemantics,
    ToleranceContract,
    Unit,
    assert_canonical_longitude_degrees,
    assert_circular_degrees,
)


_EQUATORIAL_ECLIPTIC_ROUND_TRIP = ToleranceContract(
    name="house_equatorial_ecliptic_round_trip",
    semantics=NumericSemantics.CIRCULAR,
    unit=Unit.DEGREES,
    absolute=1e-12,
    basis=(
        "Binary64 forward/inverse rotation of normalized unit directions; "
        "the tolerance bounds accumulated trigonometric round-off."
    ),
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
) -> None:
    direction = _equatorial_ecliptic_direction(longitude_deg, obliquity_deg)
    recovered = _ecliptic_longitude_from_equatorial_vector(direction, obliquity_deg)

    assert_canonical_longitude_degrees(recovered, label="recovered longitude")
    assert_circular_degrees(
        recovered,
        longitude_deg,
        tolerance=_EQUATORIAL_ECLIPTIC_ROUND_TRIP,
    )


@pytest.mark.parametrize(
    ("jd_ut", "latitude", "longitude"),
    [
        (2451545.0, 51.5, -0.1),
        (2460409.25, -33.8688, 151.2093),
        (2460676.5, 78.2232, 15.6469),
    ],
)
def test_local_angles_at_matches_the_declared_time_and_geometry_reduction(
    jd_ut: float,
    latitude: float,
    longitude: float,
) -> None:
    angles = _local_angles_at(jd_ut, latitude, longitude)

    expected_jd_tt = ut_to_tt(jd_ut)
    expected_obliquity = true_obliquity(expected_jd_tt)
    expected_dpsi, _ = nutation(expected_jd_tt)
    expected_armc = local_sidereal_time(
        jd_ut,
        longitude,
        expected_dpsi,
        expected_obliquity,
    )

    assert isinstance(angles, _LocalAngles)
    assert angles.jd_ut == jd_ut
    assert angles.jd_tt == expected_jd_tt
    assert angles.latitude == latitude
    assert angles.longitude == longitude
    assert angles.obliquity == expected_obliquity
    assert angles.dpsi == expected_dpsi
    assert angles.armc == expected_armc
    assert angles.mc == _mc_from_armc(expected_armc, expected_obliquity, latitude)
    assert angles.asc == _asc_from_armc(expected_armc, expected_obliquity, latitude)
    assert 0.0 <= angles.armc < 360.0
    assert 0.0 <= angles.mc < 360.0
    assert 0.0 <= angles.asc < 360.0

    with pytest.raises(AttributeError):
        angles.armc = 0.0  # type: ignore[misc]


@pytest.mark.parametrize(
    ("jd_ut", "latitude", "longitude"),
    [
        (2451545.0, 35.6895, 139.6917),
        (2460676.5, 78.2232, 15.6469),
    ],
)
def test_calculate_houses_is_identical_to_direct_local_angle_projection(
    jd_ut: float,
    latitude: float,
    longitude: float,
) -> None:
    angles = _local_angles_at(jd_ut, latitude, longitude)
    from_epoch = calculate_houses(
        jd_ut,
        latitude,
        longitude,
        HouseSystem.WHOLE_SIGN,
        policy=HousePolicy.strict(),
    )
    from_angles = houses_from_armc(
        angles.armc,
        angles.obliquity,
        latitude,
        HouseSystem.WHOLE_SIGN,
        policy=HousePolicy.strict(),
    )

    assert from_epoch == from_angles


def test_local_angles_helper_does_not_select_or_compute_a_house_system(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _forbidden_house_computation(*args: object, **kwargs: object) -> object:
        raise AssertionError("local angle reduction must not compute house cusps")

    monkeypatch.setattr(houses_module, "houses_from_armc", _forbidden_house_computation)
    monkeypatch.setattr(houses_module, "_whole_sign", _forbidden_house_computation)

    angles = _local_angles_at(2451545.0, 78.2232, 15.6469)

    assert isinstance(angles, _LocalAngles)
    assert not hasattr(angles, "system")
    assert not hasattr(angles, "cusps")


@pytest.mark.parametrize(
    ("jd_ut", "latitude", "longitude", "message"),
    [
        (float("nan"), 0.0, 0.0, "jd_ut must be finite"),
        (2451545.0, 90.0001, 0.0, "latitude must be in"),
        (2451545.0, 0.0, 180.0001, "longitude must be in"),
    ],
)
def test_local_angles_at_rejects_invalid_epoch_or_location(
    jd_ut: float,
    latitude: float,
    longitude: float,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        _local_angles_at(jd_ut, latitude, longitude)
