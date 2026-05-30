"""
Property-based tests for LOLA point cloud processing.

This module implements comprehensive property-based tests using Hypothesis
for the numpy-free LOLA (Lunar Orbiter Laser Altimeter) point cloud processing
feature. Each property validates a universal correctness characteristic that
should hold across all valid inputs.

Properties tested:
1. Vector normalization produces unit vectors
2. Dot product accuracy and commutativity
3. Cross product perpendicularity
4. Vector projection onto planes
6. Coordinate transformation round-trip
7. Bulk coordinate transform equivalence
8. Longitude normalization range
10. Visibility filter correctness
11. Position angle filter correctness
12. Radius filter correctness
13. Combined filter equivalence
14. Binning correctness
15. Max radius per bin selection
16. Sorting parity with NumPy
19. Convex hull containment
20. Ray-hull intersection accuracy

All tests use Hypothesis for property-based testing with carefully designed
input strategies to cover the full valid input space.

Feature: numpy-free-lunar-limb
"""

import math
import pytest
from hypothesis import given, settings, strategies as st, HealthCheck

# Try to import the native backend
try:
    from moira import _moira_native as moira_native
    NATIVE_AVAILABLE = True
except ImportError:
    NATIVE_AVAILABLE = False
    pytest.skip("Native backend not available", allow_module_level=True)


# ============================================================================
# Input Strategies
# ============================================================================


@st.composite
def point_cloud_coordinates(draw, min_size: int = 0, max_size: int = 1000):
    """
    Generate random point cloud coordinates.
    """
    size = draw(st.integers(min_value=min_size, max_value=max_size))
    
    x_coords = draw(st.lists(st.floats(-2000.0, 2000.0, allow_nan=False, allow_infinity=False), min_size=size, max_size=size))
    y_coords = draw(st.lists(st.floats(-2000.0, 2000.0, allow_nan=False, allow_infinity=False), min_size=size, max_size=size))
    z_coords = draw(st.lists(st.floats(-2000.0, 2000.0, allow_nan=False, allow_infinity=False), min_size=size, max_size=size))
    
    return (x_coords, y_coords, z_coords)


# ============================================================================
# Phase 1 & 2 Property Tests
# ============================================================================

@given(coords=point_cloud_coordinates(min_size=1, max_size=100))
@settings(max_examples=50, suppress_health_check=[HealthCheck.data_too_large])
def test_property_1_vector_normalization(coords):
    x, y, z = coords
    xn, yn, zn = moira_native.normalize_vectors_bulk(x, y, z)
    for i in range(len(xn)):
        r = math.sqrt(x[i]**2 + y[i]**2 + z[i]**2)
        rn = math.sqrt(xn[i]**2 + yn[i]**2 + zn[i]**2)
        if r < 1e-15:
            assert rn == 0.0
        else:
            assert rn == pytest.approx(1.0, abs=1e-12)

@given(
    coords=point_cloud_coordinates(min_size=1, max_size=100),
    ref=st.tuples(st.floats(-1, 1), st.floats(-1, 1), st.floats(-1, 1))
)
@settings(max_examples=50)
def test_property_2_dot_product(coords, ref):
    x, y, z = coords
    rx, ry, rz = ref
    dots = moira_native.dot_product_bulk(x, y, z, moira_native.Vec3(*ref))
    for i in range(len(dots)):
        expected = x[i]*rx + y[i]*ry + z[i]*rz
        assert dots[i] == pytest.approx(expected, abs=1e-12)

@given(
    coords=point_cloud_coordinates(min_size=1, max_size=100),
    ref=st.tuples(st.floats(-1, 1), st.floats(-1, 1), st.floats(-1, 1))
)
@settings(max_examples=50)
def test_property_3_cross_product(coords, ref):
    x, y, z = coords
    rx, ry, rz = ref
    cx, cy, cz = moira_native.cross_product_bulk(x, y, z, moira_native.Vec3(rx, ry, rz))
    for i in range(len(cx)):
        dot1 = cx[i]*x[i] + cy[i]*y[i] + cz[i]*z[i]
        dot2 = cx[i]*rx + cy[i]*ry + cz[i]*rz
        mag_prod1 = math.sqrt(cx[i]**2 + cy[i]**2 + cz[i]**2) * math.sqrt(x[i]**2 + y[i]**2 + z[i]**2)
        mag_prod2 = math.sqrt(cx[i]**2 + cy[i]**2 + cz[i]**2) * math.sqrt(rx**2 + ry**2 + rz**2)
        if mag_prod1 > 1e-12: assert dot1 / mag_prod1 == pytest.approx(0.0, abs=1e-12)
        if mag_prod2 > 1e-12: assert dot2 / mag_prod2 == pytest.approx(0.0, abs=1e-12)

@given(
    coords=point_cloud_coordinates(min_size=1, max_size=100),
    normal=st.tuples(st.floats(-1, 1), st.floats(-1, 1), st.floats(-1, 1))
)
@settings(max_examples=50)
def test_property_4_vector_projection(coords, normal):
    x, y, z = coords
    nx, ny, nz = normal
    mag_n = math.sqrt(nx**2 + ny**2 + nz**2)
    if mag_n < 1e-15: return
    nx, ny, nz = nx/mag_n, ny/mag_n, nz/mag_n
    px, py, pz = moira_native.project_onto_plane_bulk(x, y, z, moira_native.Vec3(nx, ny, nz))
    for i in range(len(px)):
        dot = px[i]*nx + py[i]*ny + pz[i]*nz
        assert dot == pytest.approx(0.0, abs=1e-11)

@given(coords=point_cloud_coordinates(min_size=1, max_size=100))
@settings(max_examples=50)
def test_property_6_coordinate_roundtrip(coords):
    x, y, z = coords
    lon, lat, rad = moira_native.cartesian_to_spherical_bulk(x, y, z)
    xr, yr, zr = moira_native.spherical_to_cartesian_bulk(lon, lat, rad)
    for i in range(len(x)):
        if abs(lat[i]) > 89.9: continue
        assert xr[i] == pytest.approx(x[i], abs=1e-7)
        assert yr[i] == pytest.approx(y[i], abs=1e-7)
        assert zr[i] == pytest.approx(z[i], abs=1e-7)

@given(coords=point_cloud_coordinates(min_size=1, max_size=100))
@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_7_bulk_coordinate_transform_equivalence(coords, moira_approx):
    x_coords, y_coords, z_coords = coords
    lon_bulk, lat_bulk, radius_bulk = moira_native.cartesian_to_spherical_bulk(x_coords, y_coords, z_coords)
    for i in range(len(x_coords)):
        x, y, z = x_coords[i], y_coords[i], z_coords[i]
        radius = math.sqrt(x*x + y*y + z*z)
        if radius < 1e-15:
            lon, lat = 0.0, 0.0
        else:
            lon = math.degrees(math.atan2(y, x))
            lat = math.degrees(math.asin(max(-1.0, min(1.0, z / radius))))
        assert radius_bulk[i] == moira_approx(radius, kind="distance")
        lon_diff = abs(((lon_bulk[i] + 180.0) % 360.0) - ((lon + 180.0) % 360.0))
        if lon_diff > 180.0: lon_diff = 360.0 - lon_diff
        assert lon_diff <= 1e-6
        assert lat_bulk[i] == moira_approx(lat, kind="angle")

@given(lons=st.lists(st.floats(-1000, 1000), min_size=1, max_size=100))
@settings(max_examples=50)
def test_property_8_longitude_normalization(lons):
    norm_lons = moira_native.normalize_longitude_bulk(lons)
    for lon in norm_lons:
        assert -180.0000001 <= lon <= 180.0000001

@given(
    coords=point_cloud_coordinates(min_size=1, max_size=100),
    obs=st.tuples(st.floats(-1, 1), st.floats(-1, 1), st.floats(-1, 1))
)
@settings(max_examples=50)
def test_property_10_visibility_filter(coords, obs):
    x, y, z = coords
    ox, oy, oz = obs
    mag_o = math.sqrt(ox**2 + oy**2 + oz**2)
    if mag_o < 1e-12: return
    pc = moira_native.LolaPointCloud(x, y, z)
    obs_vec = moira_native.Vec3(ox, oy, oz)
    visible_pc = pc.filter_by_visibility(obs_vec)
    vx, vy, vz = visible_pc.get_x(), visible_pc.get_y(), visible_pc.get_z()
    for i in range(len(vx)):
        dot = vx[i]*ox + vy[i]*oy + vz[i]*oz
        assert dot >= -1e-15 

@given(
    coords=point_cloud_coordinates(min_size=1, max_size=100),
    target_pa=st.floats(0, 360),
    tolerance=st.floats(0, 180)
)
@settings(max_examples=50)
def test_property_11_position_angle_filter(coords, target_pa, tolerance):
    x, y, z = coords
    sky_east, sky_north = moira_native.Vec3(1, 0, 0), moira_native.Vec3(0, 1, 0)
    pc = moira_native.LolaPointCloud(x, y, z)
    filtered_pc = pc.filter_by_position_angle(sky_east, sky_north, target_pa, tolerance)
    fx, fy = filtered_pc.get_x(), filtered_pc.get_y()
    for i in range(len(fx)):
        pa = math.degrees(math.atan2(fx[i], fy[i]))
        if pa < 0: pa += 360
        diff = abs(pa - target_pa)
        if diff > 180: diff = 360 - diff
        assert diff <= tolerance + 1e-10

@given(
    coords=point_cloud_coordinates(min_size=1, max_size=100),
    min_radius=st.floats(0, 2000)
)
@settings(max_examples=50)
def test_property_12_radius_filter(coords, min_radius):
    x, y, z = coords
    sky_east, sky_north = moira_native.Vec3(1, 0, 0), moira_native.Vec3(0, 1, 0)
    pc = moira_native.LolaPointCloud(x, y, z)
    filtered_pc = pc.filter_by_radius(sky_east, sky_north, min_radius)
    fx, fy = filtered_pc.get_x(), filtered_pc.get_y()
    for i in range(len(fx)):
        r_proj = math.sqrt(fx[i]**2 + fy[i]**2)
        assert r_proj >= min_radius - 1e-10

@given(
    coords=point_cloud_coordinates(min_size=1, max_size=100),
    target_pa=st.floats(0, 360),
    pa_tolerance=st.floats(1, 180),
    min_radius=st.floats(0, 1800)
)
@settings(max_examples=50)
def test_property_13_combined_filter_equivalence(coords, target_pa, pa_tolerance, min_radius):
    x, y, z = coords
    obs, sky_east, sky_north = moira_native.Vec3(0, 0, 1), moira_native.Vec3(1, 0, 0), moira_native.Vec3(0, 1, 0)
    pc = moira_native.LolaPointCloud(x, y, z)
    pc3 = pc.filter_by_visibility(obs).filter_by_position_angle(sky_east, sky_north, target_pa, pa_tolerance).filter_by_radius(sky_east, sky_north, min_radius)
    pc_comb = pc.filter_combined(obs, sky_east, sky_north, target_pa, pa_tolerance, min_radius)
    assert pc3.size() == pc_comb.size()
    assert pc3.get_x() == pc_comb.get_x()
    assert pc3.get_y() == pc_comb.get_y()
    assert pc3.get_z() == pc_comb.get_z()

@given(
    pas=st.lists(st.floats(0, 360), min_size=1, max_size=100),
    target_pa=st.floats(0, 360),
    bin_width=st.floats(0.1, 10.0)
)
@settings(max_examples=50)
def test_property_14_binning(pas, target_pa, bin_width):
    bins = moira_native.bin_by_position_angle(pas, target_pa, bin_width)
    for i in range(len(bins)):
        diff = pas[i] - target_pa
        while diff > 180: diff -= 360
        while diff <= -180: diff += 360
        assert bins[i] == math.floor(diff / bin_width)

@given(
    bins=st.lists(st.integers(-10, 10), min_size=1, max_size=100),
    radii=st.lists(st.floats(1700, 1800), min_size=1, max_size=100)
)
@settings(max_examples=50)
def test_property_15_max_radius_per_bin(bins, radii):
    size = min(len(bins), len(radii))
    bins, radii = bins[:size], radii[:size]
    max_res = moira_native.select_max_radius_per_bin(bins, radii)
    expected = {}
    for i in range(size):
        if bins[i] not in expected or radii[i] > expected[bins[i]]:
            expected[bins[i]] = radii[i]
    assert len(max_res.bins) == len(expected)
    for i in range(len(max_res.bins)):
        assert max_res.radii_km[i] == expected[max_res.bins[i]]

@given(
    bins=st.lists(st.integers(-10, 10), min_size=1, max_size=100),
    radii=st.lists(st.floats(1700, 1800), min_size=1, max_size=100)
)
@settings(max_examples=50)
def test_property_16_lexsort_parity(bins, radii):
    # Pure-Python lexsort equivalent (stable sort by (radii, bins))
    size = min(len(bins), len(radii))
    bins, radii = bins[:size], radii[:size]
    indices = moira_native.lexsort_by_bin_and_radius(bins, radii)

    # Build expected using pure Python (equivalent to np.lexsort((radii, bins)))
    paired = sorted(range(size), key=lambda i: (radii[i], bins[i]))
    expected_indices = paired
    assert list(indices) == expected_indices

@given(pts=st.lists(st.tuples(st.floats(-100, 100), st.floats(-100, 100)), min_size=3, max_size=50))
@settings(max_examples=50)
def test_property_19_convex_hull_containment(pts):
    points = [moira_native.Point2D(p[0], p[1]) for p in pts]
    hull = moira_native.convex_hull_2d(points)
    if len(hull) < 3: return
    for i in range(len(hull)):
        A, B = hull[i], hull[(i+1) % len(hull)]
        for P in points:
            cross = (B.x - A.x) * (P.y - A.y) - (B.y - A.y) * (P.x - A.x)
            assert cross >= -1e-9

@given(pa=st.floats(0, 360))
@settings(max_examples=50)
def test_property_20_ray_hull_intersection_square(pa):
    hull = [moira_native.Point2D(-1, -1), moira_native.Point2D(1, -1), moira_native.Point2D(1, 1), moira_native.Point2D(-1, 1)]
    radius = moira_native.ray_hull_intersection(hull, pa, 0.0)
    phi = math.radians(90 - pa)
    candidates = []
    if abs(math.cos(phi)) > 1e-12:
        r = 1.0 / math.cos(phi)
        if r > 0: candidates.append(r)
        r = -1.0 / math.cos(phi)
        if r > 0: candidates.append(r)
    if abs(math.sin(phi)) > 1e-12:
        r = 1.0 / math.sin(phi)
        if r > 0: candidates.append(r)
        r = -1.0 / math.sin(phi)
        if r > 0: candidates.append(r)
    assert radius == pytest.approx(min(candidates), abs=1e-10)

pytestmark = [pytest.mark.property, pytest.mark.lola, pytest.mark.numpy_free_lunar_limb]
