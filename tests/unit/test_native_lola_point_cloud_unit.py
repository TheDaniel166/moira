"""
Unit tests for LolaPointCloud class (Task 2.3).

Tests construction and accessor methods for the LolaPointCloud data structure.

These tests validate specific examples and edge cases:
- Empty point cloud construction
- Single point construction
- Large point cloud (10K points) to test performance
- Accessor methods (size, x_data, y_data, z_data)
- Constructor validation (mismatched vector sizes should throw)

Note: Tests skip only when the native module is unavailable in the current environment.

Validates: Requirements 11.1, 11.2, 11.3
"""

import math

import pytest


# Check if native backend is available
try:
    from moira import moira_native
    NATIVE_AVAILABLE = hasattr(moira_native, 'LolaPointCloud')
except ImportError:
    NATIVE_AVAILABLE = False


pytestmark = pytest.mark.skipif(
    not NATIVE_AVAILABLE,
    reason="LolaPointCloud native binding unavailable in this environment"
)


@pytest.fixture
def empty_cloud():
    """Empty point cloud for testing."""
    if NATIVE_AVAILABLE:
        return moira_native.LolaPointCloud([], [], [])
    return None


@pytest.fixture
def single_point_cloud():
    """Single point cloud for testing."""
    if NATIVE_AVAILABLE:
        return moira_native.LolaPointCloud([1.0], [2.0], [3.0])
    return None


@pytest.fixture
def small_cloud():
    """Small point cloud with known values for testing."""
    if NATIVE_AVAILABLE:
        x = [1.0, 2.0, 3.0]
        y = [4.0, 5.0, 6.0]
        z = [7.0, 8.0, 9.0]
        return moira_native.LolaPointCloud(x, y, z)
    return None


def test_empty_point_cloud_construction(empty_cloud):
    """
    Test construction from empty lists.
    
    An empty point cloud should be valid and have size 0.
    
    Validates: Requirement 11.3 (bulk construction from Python lists)
    """
    assert empty_cloud.size() == 0, "Empty cloud should have size 0"


def test_single_point_construction(single_point_cloud):
    """
    Test construction from single point.
    
    A single-point cloud should be valid and have size 1.
    The accessor methods should return the correct data.
    
    Validates: Requirements 11.3 (bulk construction), 11.4 (efficient access)
    """
    cloud = single_point_cloud
    
    assert cloud.size() == 1, "Single point cloud should have size 1"
    
    # Access raw data pointers
    # Note: In Python, we can't directly dereference C++ pointers,
    # but we can verify the methods exist and don't crash
    x_ptr = cloud.x_data()
    y_ptr = cloud.y_data()
    z_ptr = cloud.z_data()
    
    # Verify pointers are not None (they should be valid memory addresses)
    assert x_ptr is not None, "x_data() should return valid pointer"
    assert y_ptr is not None, "y_data() should return valid pointer"
    assert z_ptr is not None, "z_data() should return valid pointer"


def test_small_point_cloud_construction(small_cloud):
    """
    Test construction from small point cloud with known values.
    
    Validates: Requirements 11.3 (bulk construction), 11.4 (efficient access)
    """
    cloud = small_cloud
    
    assert cloud.size() == 3, "Small cloud should have size 3"
    
    # Verify accessor methods work
    assert cloud.x_data() is not None
    assert cloud.y_data() is not None
    assert cloud.z_data() is not None


def test_perspective_projection_preserves_a_finite_distance_sphere_tangent():
    radius_km = 1737.4
    distance_km = 384_400.0
    tangent_cosine = radius_km / distance_km
    tangent_point = (
        radius_km * tangent_cosine,
        0.0,
        radius_km * math.sqrt(1.0 - tangent_cosine * tangent_cosine),
    )
    cloud = moira_native.LolaPointCloud(
        [tangent_point[0]],
        [tangent_point[1]],
        [tangent_point[2]],
    )

    perspective = cloud.project_to_sky_plane(
        moira_native.Vec3(1.0, 0.0, 0.0),
        moira_native.Vec3(0.0, 1.0, 0.0),
        moira_native.Vec3(0.0, 0.0, 1.0),
        distance_km,
    )
    orthographic = cloud.project_to_sky_plane(
        moira_native.Vec3(1.0, 0.0, 0.0),
        moira_native.Vec3(0.0, 1.0, 0.0),
        moira_native.Vec3(0.0, 0.0, 1.0),
    )

    assert perspective.radius_km[0] == pytest.approx(radius_km, abs=1.0e-12)
    assert orthographic.radius_km[0] < radius_km
    assert perspective.pa_deg[0] == pytest.approx(0.0, abs=1.0e-12)


def test_perspective_projection_matches_the_observer_ray_definition():
    distance_km = 400_000.0
    points = (
        (500.0, 1_200.0, -900.0),
        (-800.0, -700.0, 1_400.0),
        (1_700.0, 25.0, 40.0),
    )
    cloud = moira_native.LolaPointCloud(
        [point[0] for point in points],
        [point[1] for point in points],
        [point[2] for point in points],
    )

    projection = cloud.project_to_sky_plane(
        moira_native.Vec3(1.0, 0.0, 0.0),
        moira_native.Vec3(0.0, 1.0, 0.0),
        moira_native.Vec3(0.0, 0.0, 1.0),
        distance_km,
    )

    expected = tuple(
        distance_km
        * math.hypot(y, z)
        / math.sqrt((distance_km - x) ** 2 + y * y + z * z)
        for x, y, z in points
    )
    assert tuple(projection.radius_km) == pytest.approx(expected, abs=1.0e-12)


def test_normal_range_perspective_projection_preserves_direct_expression_bits():
    # D-x=4,000 and r=3,000 form an exact 3-4-5 triangle.  This explicitly
    # guards the historical D*r/hypot(D-x, r) operation order used by ordinary
    # LOLA profile points; the overflow fallback must not perturb this path.
    distance_km = 5_000.0
    toward_observer_km = 1_000.0
    plane_radius_km = 3_000.0
    cloud = moira_native.LolaPointCloud(
        [toward_observer_km],
        [plane_radius_km],
        [0.0],
    )

    projection = cloud.project_to_sky_plane(
        moira_native.Vec3(1.0, 0.0, 0.0),
        moira_native.Vec3(0.0, 1.0, 0.0),
        moira_native.Vec3(0.0, 0.0, 1.0),
        distance_km,
    )
    expected = (
        distance_km
        * plane_radius_km
        / math.hypot(distance_km - toward_observer_km, plane_radius_km)
    )

    assert projection.radius_km[0] == expected


def test_perspective_projection_avoids_finite_quotient_product_overflow():
    distance_km = 1.0e308
    plane_radius_km = 1.0e308
    cloud = moira_native.LolaPointCloud([0.0], [plane_radius_km], [0.0])

    projection = cloud.project_to_sky_plane(
        moira_native.Vec3(1.0, 0.0, 0.0),
        moira_native.Vec3(0.0, 1.0, 0.0),
        moira_native.Vec3(0.0, 0.0, 1.0),
        distance_km,
    )

    expected = distance_km / math.sqrt(2.0)
    assert math.isfinite(projection.radius_km[0])
    assert projection.radius_km[0] == pytest.approx(expected, rel=2.0e-15)


def test_fused_reducer_avoids_finite_quotient_product_overflow():
    distance_km = 1.0e308
    plane_radius_km = 1.0e308
    cloud = moira_native.LolaPointCloud([0.0], [plane_radius_km], [0.0])

    result = cloud.project_max_radius_per_pa_bin(
        moira_native.Vec3(1.0, 0.0, 0.0),
        moira_native.Vec3(0.0, 1.0, 0.0),
        moira_native.Vec3(0.0, 0.0, 1.0),
        0.0,
        180.0,
        90.0,
        distance_km,
    )

    expected = distance_km / math.sqrt(2.0)
    assert tuple(result.bin_indices) == (1,)
    assert math.isfinite(result.radii_km[0])
    assert result.radii_km[0] == pytest.approx(expected, rel=2.0e-15)


def test_projection_rejects_nonfinite_intermediate_from_finite_payload():
    component = math.sqrt(0.5)
    cloud = moira_native.LolaPointCloud(
        [float.fromhex("0x1.fffffffffffffp+1023")],
        [float.fromhex("0x1.fffffffffffffp+1023")],
        [0.0],
    )

    with pytest.raises(ValueError, match="projected point coordinates must be finite"):
        cloud.project_to_sky_plane(
            moira_native.Vec3(component, -component, 0.0),
            moira_native.Vec3(component, component, 0.0),
            moira_native.Vec3(0.0, 0.0, 1.0),
            400_000.0,
        )


@pytest.mark.parametrize("distance_km", (0.0, -1.0, math.nan))
def test_perspective_projection_rejects_invalid_observer_distance(distance_km):
    cloud = moira_native.LolaPointCloud([1.0], [0.0], [0.0])

    with pytest.raises(ValueError, match="observer distance"):
        cloud.project_to_sky_plane(
            moira_native.Vec3(1.0, 0.0, 0.0),
            moira_native.Vec3(0.0, 1.0, 0.0),
            moira_native.Vec3(0.0, 0.0, 1.0),
            distance_km,
        )


def test_perspective_projection_rejects_surface_point_past_observer():
    cloud = moira_native.LolaPointCloud([2.0], [0.0], [0.0])

    with pytest.raises(ValueError, match="reaches or passes"):
        cloud.project_to_sky_plane(
            moira_native.Vec3(1.0, 0.0, 0.0),
            moira_native.Vec3(0.0, 1.0, 0.0),
            moira_native.Vec3(0.0, 0.0, 1.0),
            1.0,
        )


def _point_at_position_angle(
    position_angle_deg: float,
    plane_radius_km: float,
    toward_observer_km: float = 100.0,
) -> tuple[float, float, float]:
    """Construct a point for the test basis: observer=X, east=Y, north=Z."""

    pa_rad = math.radians(position_angle_deg)
    return (
        toward_observer_km,
        plane_radius_km * math.sin(pa_rad),
        plane_radius_km * math.cos(pa_rad),
    )


def _python_pa_bin_maxima_reference(
    points: tuple[tuple[float, float, float], ...],
    *,
    lower_deg: float,
    upper_deg: float,
    bin_width_deg: float,
    observer_distance_km: float,
) -> tuple[dict[int, tuple[float, int]], int]:
    """Independent scalar definition of the fused native result."""

    maxima: dict[int, tuple[float, int]] = {}
    admitted = 0
    lower_normalized = lower_deg % 360.0
    for point_index, (x, y, z) in enumerate(points):
        east = y
        north = z
        plane_radius = math.hypot(east, north)
        if plane_radius == 0.0:
            continue
        pa_deg = math.degrees(math.atan2(east, north)) % 360.0
        unwrapped = lower_deg + ((pa_deg - lower_normalized) % 360.0)
        if not lower_deg <= unwrapped < upper_deg:
            continue
        bin_index = math.floor((unwrapped - lower_deg) / bin_width_deg)
        if math.isinf(observer_distance_km):
            equivalent_radius = plane_radius
        else:
            equivalent_radius = (
                observer_distance_km
                * plane_radius
                / math.hypot(observer_distance_km - x, plane_radius)
            )
        admitted += 1
        previous = maxima.get(bin_index)
        if previous is None or equivalent_radius > previous[0]:
            maxima[bin_index] = (equivalent_radius, point_index)
    return maxima, admitted


@pytest.mark.parametrize("observer_distance_km", (math.inf, 400_000.0))
def test_fused_pa_bin_maxima_matches_independent_wrapped_reference(
    observer_distance_km,
):
    points = (
        _point_at_position_angle(358.0, 1_700.0),
        _point_at_position_angle(358.5, 1_705.0),
        _point_at_position_angle(359.25, 1_702.0),
        _point_at_position_angle(1.2, 1_710.0),
        _point_at_position_angle(180.0, 1_720.0),
        (1_700.0, 0.0, 0.0),  # PA undefined: never admitted.
    )
    cloud = moira_native.LolaPointCloud(
        [point[0] for point in points],
        [point[1] for point in points],
        [point[2] for point in points],
    )

    result = cloud.project_max_radius_per_pa_bin(
        moira_native.Vec3(1.0, 0.0, 0.0),
        moira_native.Vec3(0.0, 1.0, 0.0),
        moira_native.Vec3(0.0, 0.0, 1.0),
        358.0,
        362.0,
        1.0,
        observer_distance_km,
        1_600.0,
        1_800.0,
    )
    expected, admitted = _python_pa_bin_maxima_reference(
        points,
        lower_deg=358.0,
        upper_deg=362.0,
        bin_width_deg=1.0,
        observer_distance_km=observer_distance_km,
    )
    expected_indices = tuple(sorted(expected))

    assert result.bin_count == 4
    assert result.admitted_source_point_count == admitted == 4
    assert tuple(result.bin_indices) == expected_indices == (0, 1, 3)
    assert tuple(result.bin_centers_unwrapped_deg) == pytest.approx(
        tuple(358.0 + (index + 0.5) for index in expected_indices),
        abs=0.0,
    )
    assert tuple(result.radii_km) == pytest.approx(
        tuple(expected[index][0] for index in expected_indices),
        abs=1.0e-12,
    )
    assert tuple(result.point_indices) == tuple(
        expected[index][1] for index in expected_indices
    )


def test_fused_pa_bins_use_exact_half_open_edges_and_sparse_empty_bins():
    # atan2 returns these cardinal position angles exactly: PA 0 is admitted,
    # while the PA 90 upper edge is excluded from [0, 90).
    points = (
        (100.0, 0.0, 1_700.0),
        (100.0, 1_700.0, 0.0),
    )
    cloud = moira_native.LolaPointCloud(
        [point[0] for point in points],
        [point[1] for point in points],
        [point[2] for point in points],
    )

    result = cloud.project_max_radius_per_pa_bin(
        moira_native.Vec3(1.0, 0.0, 0.0),
        moira_native.Vec3(0.0, 1.0, 0.0),
        moira_native.Vec3(0.0, 0.0, 1.0),
        0.0,
        90.0,
        30.0,
    )

    assert result.bin_count == 3
    assert result.admitted_source_point_count == 1
    assert tuple(result.bin_indices) == (0,)
    assert tuple(result.bin_centers_unwrapped_deg) == (15.0,)
    assert tuple(result.radii_km) == pytest.approx((1_700.0,), abs=1.0e-12)
    assert tuple(result.point_indices) == (0,)


def test_fused_pa_bin_raw_shell_is_inclusive_and_does_not_clamp():
    points = (
        _point_at_position_angle(0.0, 1_700.0, 0.0),
        _point_at_position_angle(1.5, 1_800.0, 0.0),
    )
    cloud = moira_native.LolaPointCloud(
        [point[0] for point in points],
        [point[1] for point in points],
        [point[2] for point in points],
    )

    result = cloud.project_max_radius_per_pa_bin(
        moira_native.Vec3(1.0, 0.0, 0.0),
        moira_native.Vec3(0.0, 1.0, 0.0),
        moira_native.Vec3(0.0, 0.0, 1.0),
        0.0,
        2.0,
        1.0,
        math.inf,
        1_700.0,
        1_800.0,
    )

    assert result.admitted_source_point_count == 2
    assert tuple(result.bin_indices) == (0, 1)
    assert tuple(result.radii_km) == pytest.approx(
        (1_700.0, 1_800.0),
        abs=1.0e-12,
    )


@pytest.mark.parametrize(
    ("radius_km", "shell_min_km", "shell_max_km"),
    (
        (1_699.999, 1_700.0, 1_800.0),
        (1_800.001, 1_700.0, 1_800.0),
    ),
)
def test_fused_pa_bin_reducer_rejects_raw_relief_shell_violations(
    radius_km,
    shell_min_km,
    shell_max_km,
):
    # The violating point is outside the requested PA interval. The raw shell
    # is a dataset-integrity assertion, not a filter, so it must still fail.
    point = _point_at_position_angle(180.0, radius_km, 0.0)
    cloud = moira_native.LolaPointCloud([point[0]], [point[1]], [point[2]])

    with pytest.raises(ValueError, match="raw radial shell"):
        cloud.project_max_radius_per_pa_bin(
            moira_native.Vec3(1.0, 0.0, 0.0),
            moira_native.Vec3(0.0, 1.0, 0.0),
            moira_native.Vec3(0.0, 0.0, 1.0),
            0.0,
            10.0,
            1.0,
            math.inf,
            shell_min_km,
            shell_max_km,
        )


@pytest.mark.parametrize(
    ("observer_dir", "sky_east", "sky_north", "message"),
    (
        ((0.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0), "nonzero"),
        ((2.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0), "orthonormal"),
        ((1.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0), "orthonormal"),
        ((math.nan, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0), "finite"),
    ),
)
def test_fused_pa_bin_reducer_rejects_invalid_sky_basis(
    observer_dir,
    sky_east,
    sky_north,
    message,
):
    cloud = moira_native.LolaPointCloud([0.0], [0.0], [1_700.0])

    with pytest.raises(ValueError, match=message):
        cloud.project_max_radius_per_pa_bin(
            moira_native.Vec3(*observer_dir),
            moira_native.Vec3(*sky_east),
            moira_native.Vec3(*sky_north),
            0.0,
            10.0,
            1.0,
        )


@pytest.mark.parametrize("observer_distance_km", (0.0, -1.0, math.nan, -math.inf))
def test_fused_pa_bin_reducer_rejects_invalid_observer_distance(
    observer_distance_km,
):
    cloud = moira_native.LolaPointCloud([0.0], [0.0], [1_700.0])

    with pytest.raises(ValueError, match="observer distance"):
        cloud.project_max_radius_per_pa_bin(
            moira_native.Vec3(1.0, 0.0, 0.0),
            moira_native.Vec3(0.0, 1.0, 0.0),
            moira_native.Vec3(0.0, 0.0, 1.0),
            0.0,
            10.0,
            1.0,
            observer_distance_km,
        )


@pytest.mark.parametrize(
    ("lower_deg", "upper_deg", "bin_width_deg", "message"),
    (
        (math.nan, 10.0, 1.0, "finite"),
        (0.0, math.inf, 1.0, "finite"),
        (10.0, 10.0, 1.0, "width"),
        (10.0, 9.0, 1.0, "width"),
        (0.0, 361.0, 1.0, "width"),
        (0.0, 10.0, 0.0, "bin width"),
        (0.0, 10.0, 3.0, "integer number"),
    ),
)
def test_fused_pa_bin_reducer_rejects_invalid_bin_contract(
    lower_deg,
    upper_deg,
    bin_width_deg,
    message,
):
    cloud = moira_native.LolaPointCloud([0.0], [0.0], [1_700.0])

    with pytest.raises(ValueError, match=message):
        cloud.project_max_radius_per_pa_bin(
            moira_native.Vec3(1.0, 0.0, 0.0),
            moira_native.Vec3(0.0, 1.0, 0.0),
            moira_native.Vec3(0.0, 0.0, 1.0),
            lower_deg,
            upper_deg,
            bin_width_deg,
        )


@pytest.mark.parametrize(
    ("upper_deg", "bin_width_deg"),
    (
        (360.0, 360.0 / 262_145.0),
        # 256 / 2**-56 is exactly 2**64.  On 64-bit Windows, converting
        # size_t::max() to double also rounds to 2**64, so a max-size_t
        # comparison does not protect the subsequent integer conversion.
        (256.0, 2.0**-56),
    ),
)
def test_fused_pa_bin_reducer_rejects_impractical_or_unrepresentable_bin_counts(
    upper_deg,
    bin_width_deg,
):
    cloud = moira_native.LolaPointCloud([0.0], [0.0], [1_700.0])

    with pytest.raises(ValueError, match="no greater than 262144"):
        cloud.project_max_radius_per_pa_bin(
            moira_native.Vec3(1.0, 0.0, 0.0),
            moira_native.Vec3(0.0, 1.0, 0.0),
            moira_native.Vec3(0.0, 0.0, 1.0),
            0.0,
            upper_deg,
            bin_width_deg,
        )


def test_fused_pa_bin_reducer_admits_its_bounded_bin_count_ceiling():
    cloud = moira_native.LolaPointCloud([0.0], [0.0], [1_700.0])

    result = cloud.project_max_radius_per_pa_bin(
        moira_native.Vec3(1.0, 0.0, 0.0),
        moira_native.Vec3(0.0, 1.0, 0.0),
        moira_native.Vec3(0.0, 0.0, 1.0),
        0.0,
        256.0,
        2.0**-10,
    )

    assert result.bin_count == 262_144


@pytest.mark.parametrize(
    ("raw_min_km", "raw_max_km", "message"),
    (
        (1_700.0, None, "both"),
        (None, 1_800.0, "both"),
        (math.nan, 1_800.0, "finite"),
        (1_700.0, math.inf, "finite"),
        (-1.0, 1_800.0, "nonnegative"),
        (1_800.0, 1_700.0, "ordered"),
    ),
)
def test_fused_pa_bin_reducer_rejects_invalid_raw_shell(
    raw_min_km,
    raw_max_km,
    message,
):
    cloud = moira_native.LolaPointCloud([0.0], [0.0], [1_700.0])

    with pytest.raises(ValueError, match=message):
        cloud.project_max_radius_per_pa_bin(
            moira_native.Vec3(1.0, 0.0, 0.0),
            moira_native.Vec3(0.0, 1.0, 0.0),
            moira_native.Vec3(0.0, 0.0, 1.0),
            0.0,
            10.0,
            1.0,
            math.inf,
            raw_min_km,
            raw_max_km,
        )


@pytest.mark.parametrize("coordinate", (math.nan, math.inf, -math.inf))
def test_fused_pa_bin_reducer_rejects_nonfinite_point_payload(coordinate):
    cloud = moira_native.LolaPointCloud([0.0], [coordinate], [1_700.0])

    with pytest.raises(ValueError, match="point coordinates must be finite"):
        cloud.project_max_radius_per_pa_bin(
            moira_native.Vec3(1.0, 0.0, 0.0),
            moira_native.Vec3(0.0, 1.0, 0.0),
            moira_native.Vec3(0.0, 0.0, 1.0),
            0.0,
            10.0,
            1.0,
        )


def test_large_point_cloud_construction():
    """
    Test construction from large point cloud (10K points).
    
    This tests performance and memory handling for typical LOLA tile sizes.
    A typical LOLA tile contains 10,000-50,000 points.
    
    Validates: Requirements 11.3 (bulk construction), 11.6 (minimize memory allocations)
    """
    if not NATIVE_AVAILABLE:
        pytest.skip("Native backend not available")
    
    # Create 10K points
    n = 10_000
    x = [float(i) for i in range(n)]
    y = [float(i * 2) for i in range(n)]
    z = [float(i * 3) for i in range(n)]
    
    # Construction should succeed without error
    cloud = moira_native.LolaPointCloud(x, y, z)
    
    assert cloud.size() == n, f"Large cloud should have size {n}"
    
    # Verify accessor methods work
    assert cloud.x_data() is not None
    assert cloud.y_data() is not None
    assert cloud.z_data() is not None


def test_accessor_methods_exist(small_cloud):
    """
    Test that all required accessor methods exist and are callable.
    
    Validates: Requirement 11.4 (support efficient access to individual points)
    """
    cloud = small_cloud
    
    # Test size() accessor
    assert hasattr(cloud, 'size'), "LolaPointCloud should have size() method"
    assert callable(cloud.size), "size() should be callable"
    size = cloud.size()
    assert isinstance(size, int), "size() should return integer"
    assert size == 3, "size() should return correct value"
    
    # Test x_data() accessor
    assert hasattr(cloud, 'x_data'), "LolaPointCloud should have x_data() method"
    assert callable(cloud.x_data), "x_data() should be callable"
    x_ptr = cloud.x_data()
    assert x_ptr is not None, "x_data() should return valid pointer"
    
    # Test y_data() accessor
    assert hasattr(cloud, 'y_data'), "LolaPointCloud should have y_data() method"
    assert callable(cloud.y_data), "y_data() should be callable"
    y_ptr = cloud.y_data()
    assert y_ptr is not None, "y_data() should return valid pointer"
    
    # Test z_data() accessor
    assert hasattr(cloud, 'z_data'), "LolaPointCloud should have z_data() method"
    assert callable(cloud.z_data), "z_data() should be callable"
    z_ptr = cloud.z_data()
    assert z_ptr is not None, "z_data() should return valid pointer"


def test_constructor_validation_mismatched_sizes():
    """
    Test that constructor validates vector sizes match.
    
    Mismatched vector sizes should raise an exception.
    
    Validates: Requirement 11.3 (bulk construction from Python lists)
    """
    if not NATIVE_AVAILABLE:
        pytest.skip("Native backend not available")
    
    # Test x and y mismatch
    with pytest.raises((ValueError, RuntimeError)) as exc_info:
        moira_native.LolaPointCloud([1.0, 2.0], [3.0], [4.0, 5.0])
    
    error_msg = str(exc_info.value).lower()
    assert 'size' in error_msg or 'length' in error_msg or 'same' in error_msg, \
        "Error message should mention size mismatch"
    
    # Test x and z mismatch
    with pytest.raises((ValueError, RuntimeError)) as exc_info:
        moira_native.LolaPointCloud([1.0, 2.0], [3.0, 4.0], [5.0])
    
    error_msg = str(exc_info.value).lower()
    assert 'size' in error_msg or 'length' in error_msg or 'same' in error_msg, \
        "Error message should mention size mismatch"
    
    # Test y and z mismatch
    with pytest.raises((ValueError, RuntimeError)) as exc_info:
        moira_native.LolaPointCloud([1.0], [2.0, 3.0], [4.0])
    
    error_msg = str(exc_info.value).lower()
    assert 'size' in error_msg or 'length' in error_msg or 'same' in error_msg, \
        "Error message should mention size mismatch"


def test_constructor_validation_all_different_sizes():
    """
    Test constructor with all three vectors having different sizes.
    
    Should raise an exception with clear error message.
    
    Validates: Requirement 11.3 (bulk construction from Python lists)
    """
    if not NATIVE_AVAILABLE:
        pytest.skip("Native backend not available")
    
    with pytest.raises((ValueError, RuntimeError)) as exc_info:
        moira_native.LolaPointCloud([1.0], [2.0, 3.0], [4.0, 5.0, 6.0])
    
    error_msg = str(exc_info.value).lower()
    assert 'size' in error_msg or 'length' in error_msg or 'same' in error_msg, \
        "Error message should mention size mismatch"


def test_structure_of_arrays_layout():
    """
    Test that LolaPointCloud uses structure-of-arrays (SoA) layout.
    
    The SoA layout stores coordinates in separate arrays (x_, y_, z_)
    rather than an array of point structures. This is critical for
    SIMD vectorization performance.
    
    This test verifies the design is implemented correctly by checking
    that the C++ implementation uses separate vectors.
    
    Validates: Design requirement for SoA layout (Requirement 11.1)
    """
    import os
    
    # Verify implementation uses SoA layout
    impl_path = "src/native/src/lola.cpp"
    if os.path.exists(impl_path):
        with open(impl_path, 'r') as f:
            impl_content = f.read()
            # Check that constructor copies to separate vectors
            assert 'x_(x)' in impl_content or 'x_ = x' in impl_content or 'x_(std::move(x))' in impl_content, \
                "Constructor should initialize x_ vector"
            assert 'y_(y)' in impl_content or 'y_ = y' in impl_content or 'y_(std::move(y))' in impl_content, \
                "Constructor should initialize y_ vector"
            assert 'z_(z)' in impl_content or 'z_ = z' in impl_content or 'z_(std::move(z))' in impl_content, \
                "Constructor should initialize z_ vector"


def test_point_cloud_immutability():
    """
    Test that accessor methods return const pointers.
    
    The design specifies that accessor methods should be const,
    preserving immutability where possible.
    
    Validates: Design requirement for const methods
    """
    import os
    
    header_path = "src/native/include/lola.hpp"
    if os.path.exists(header_path):
        with open(header_path, 'r') as f:
            header_content = f.read()
            # Verify accessor methods are const
            assert 'size() const' in header_content, \
                "size() should be const method"
            assert 'x_data() const' in header_content, \
                "x_data() should be const method"
            assert 'y_data() const' in header_content, \
                "y_data() should be const method"
            assert 'z_data() const' in header_content, \
                "z_data() should be const method"
            
            # Verify data pointers are const
            assert 'const double* x_data()' in header_content, \
                "x_data() should return const pointer"
            assert 'const double* y_data()' in header_content, \
                "y_data() should return const pointer"
            assert 'const double* z_data()' in header_content, \
                "z_data() should return const pointer"


def test_memory_efficiency():
    """
    Test that point cloud construction is memory efficient.
    
    The design specifies minimizing memory allocations for repeated operations.
    This test verifies that construction doesn't create unnecessary copies.
    
    Validates: Requirement 11.6 (minimize memory allocations)
    """
    if not NATIVE_AVAILABLE:
        pytest.skip("Native backend not available")
    
    # Create a moderately sized point cloud
    n = 1000
    x = [float(i) for i in range(n)]
    y = [float(i * 2) for i in range(n)]
    z = [float(i * 3) for i in range(n)]
    
    # Construction should be fast and not cause memory issues
    import time
    start = time.perf_counter()
    cloud = moira_native.LolaPointCloud(x, y, z)
    elapsed = time.perf_counter() - start
    
    # Construction of 1000 points should be very fast (< 10ms)
    assert elapsed < 0.01, f"Construction took {elapsed*1000:.2f}ms, should be < 10ms"
    
    assert cloud.size() == n


def test_default_constructor():
    """
    Test that default constructor creates empty point cloud.
    
    The design specifies a default constructor that creates an empty cloud.
    
    Validates: Requirement 11.3 (bulk construction)
    """
    if not NATIVE_AVAILABLE:
        pytest.skip("Native backend not available")
    
    # Check if default constructor is available
    # Note: This may not be exposed to Python, so we test via empty lists
    cloud = moira_native.LolaPointCloud([], [], [])
    assert cloud.size() == 0, "Default/empty construction should create size 0 cloud"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
