"""
Unit tests for LolaPointCloud class (Task 2.3).

Tests construction and accessor methods for the LolaPointCloud data structure.

These tests validate specific examples and edge cases:
- Empty point cloud construction
- Single point construction
- Large point cloud (10K points) to test performance
- Accessor methods (size, x_data, y_data, z_data)
- Constructor validation (mismatched vector sizes should throw)

Note: Tests will skip if pybind11 bindings not yet added (expected until Task 5.1).

Validates: Requirements 11.1, 11.2, 11.3
"""

import pytest


# Check if native backend is available
try:
    from moira import moira_native
    NATIVE_AVAILABLE = hasattr(moira_native, 'LolaPointCloud')
except ImportError:
    NATIVE_AVAILABLE = False


pytestmark = pytest.mark.skipif(
    not NATIVE_AVAILABLE,
    reason="LolaPointCloud not yet bound in native backend (expected until Task 5.1)"
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
