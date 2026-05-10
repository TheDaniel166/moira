import math

import pytest

from moira.corrections import _observer_position_icrf

try:
    from moira import moira_native
except ImportError:
    moira_native = None


pytestmark = [pytest.mark.unit]


@pytest.mark.skipif(moira_native is None, reason="Native backend not available")
@pytest.mark.parametrize(
    ("lon_deg", "lat_deg", "elev_m"),
    [
        (0.0, 0.0, 0.0),
        (45.0, 23.5, 100.0),
        (-73.9857, 40.7484, 15.0),
        (151.2093, -33.8688, 250.0),
        (0.0, 90.0, 0.0),
    ],
)
def test_geodetic_to_cartesian_wgs84_matches_python_observer_geometry(
    lon_deg: float,
    lat_deg: float,
    elev_m: float,
    moira_approx,
) -> None:
    native = moira_native.geodetic_to_cartesian_wgs84(lon_deg, lat_deg, elev_m)
    expected = _observer_position_icrf(lat_deg, 0.0, lon_deg, elev_m)

    assert native.x == moira_approx(expected[0], kind="distance")
    assert native.y == moira_approx(expected[1], kind="distance")
    assert native.z == moira_approx(expected[2], kind="distance")


@pytest.mark.skipif(moira_native is None, reason="Native backend not available")
@pytest.mark.parametrize(
    ("vector", "expected_lon", "expected_lat", "expected_radius"),
    [
        ((1.0, 0.0, 0.0), 0.0, 0.0, 1.0),
        ((0.0, 1.0, 0.0), 90.0, 0.0, 1.0),
        ((0.0, -1.0, 0.0), -90.0, 0.0, 1.0),
        ((-1.0, 0.0, 0.0), 180.0, 0.0, 1.0),
        ((0.0, 0.0, 2.0), 0.0, 90.0, 2.0),
    ],
)
def test_vec3_to_lonlat_signed_matches_reclat_semantics(
    vector: tuple[float, float, float],
    expected_lon: float,
    expected_lat: float,
    expected_radius: float,
    moira_approx,
) -> None:
    lon_deg, lat_deg, radius = moira_native.vec3_to_lonlat_signed(moira_native.Vec3(*vector))

    assert lon_deg == moira_approx(expected_lon, kind="angle")
    assert lat_deg == moira_approx(expected_lat, kind="angle")
    assert radius == moira_approx(expected_radius, kind="distance")


@pytest.mark.skipif(moira_native is None, reason="Native backend not available")
def test_rotation_matrix_apply_matches_python_matrix_vector_multiply(moira_approx) -> None:
    angle = math.radians(30.0)
    rotation = (
        (math.cos(angle), -math.sin(angle), 0.0),
        (math.sin(angle), math.cos(angle), 0.0),
        (0.0, 0.0, 1.0),
    )
    vector = (2.0, -1.0, 0.5)

    native = moira_native.rotation_matrix_apply(rotation, vector)
    expected = (
        rotation[0][0] * vector[0] + rotation[0][1] * vector[1] + rotation[0][2] * vector[2],
        rotation[1][0] * vector[0] + rotation[1][1] * vector[1] + rotation[1][2] * vector[2],
        rotation[2][0] * vector[0] + rotation[2][1] * vector[1] + rotation[2][2] * vector[2],
    )

    assert native[0] == moira_approx(expected[0], kind="distance")
    assert native[1] == moira_approx(expected[1], kind="distance")
    assert native[2] == moira_approx(expected[2], kind="distance")
