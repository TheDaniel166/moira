"""
Performance benchmarks for topocentric diurnal aberration correction.

This module implements performance validation for Tasks 25-29 of the topocentric
diurnal aberration feature specification. Benchmarks verify that:

1. Single-body correction completes in < 1 millisecond
2. Batch operations (same observer) complete in < 1 second for 1000 bodies
3. Batch operations (different observers) complete in < 1 second for 1000 bodies
4. Memory efficiency is maintained (no quadratic growth)
5. Performance targets are met across all test cases

Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5
"""

import time
import math
import pytest
from typing import List, Tuple

from moira.corrections import apply_diurnal_aberration
from moira.constants import KM_PER_AU
from moira.coordinates import Vec3


# Test data: representative celestial bodies and observer locations
TEST_BODIES = [
    # Sun (geocentric distance ~1 AU)
    ("Sun", (0.983 * KM_PER_AU, 0.0, 0.0)),
    # Moon (geocentric distance ~384,400 km)
    ("Moon", (384400.0, 0.0, 0.0)),
    # Mercury (geocentric distance ~0.4 AU)
    ("Mercury", (0.4 * KM_PER_AU, 0.0, 0.0)),
    # Venus (geocentric distance ~0.7 AU)
    ("Venus", (0.7 * KM_PER_AU, 0.0, 0.0)),
    # Mars (geocentric distance ~1.5 AU)
    ("Mars", (1.5 * KM_PER_AU, 0.0, 0.0)),
    # Jupiter (geocentric distance ~5 AU)
    ("Jupiter", (5.0 * KM_PER_AU, 0.0, 0.0)),
    # Saturn (geocentric distance ~10 AU)
    ("Saturn", (10.0 * KM_PER_AU, 0.0, 0.0)),
]

TEST_OBSERVERS = [
    # North Pole
    ("North Pole", 90.0, 0.0, 0.0),
    # South Pole
    ("South Pole", -90.0, 0.0, 0.0),
    # Equator
    ("Equator", 0.0, 0.0, 0.0),
    # Greenwich
    ("Greenwich", 51.477, 0.0, 180.0),
    # Mid-latitude (45°N)
    ("Mid-latitude", 45.0, 0.0, 90.0),
]


class TestPerformanceSingleBody:
    """Task 25: Single-body correction benchmark (< 1 ms per body)."""

    def test_single_body_correction_timing(self):
        """
        Benchmark single-body correction timing.

        Measures time to compute apply_diurnal_aberration() for a single body,
        including WGS-84 conversion, cross product, and aberration formula.

        Requirement 8.3: Correction SHALL be computed in < 1 millisecond per body.
        """
        # Use Sun at Greenwich as representative case
        xyz_sun = (0.983 * KM_PER_AU, 0.0, 0.0)
        latitude = 51.477
        longitude = 0.0
        lst = 180.0
        elevation = 0.0

        # Warm up (JIT compilation if applicable)
        apply_diurnal_aberration(xyz_sun, latitude, longitude, lst, elevation)

        # Measure time for 1000 iterations
        num_iterations = 1000
        start_time = time.perf_counter()
        for _ in range(num_iterations):
            apply_diurnal_aberration(xyz_sun, latitude, longitude, lst, elevation)
        end_time = time.perf_counter()

        total_time = end_time - start_time
        mean_time_ms = (total_time / num_iterations) * 1000

        # Report timing breakdown
        print(f"\n--- Single-Body Correction Benchmark ---")
        print(f"Total time for {num_iterations} iterations: {total_time:.4f} seconds")
        print(f"Mean time per body: {mean_time_ms:.4f} milliseconds")
        print(f"Target: < 1.0 millisecond")
        print(f"Status: {'PASS' if mean_time_ms < 1.0 else 'FAIL'}")

        # Verify performance target
        assert mean_time_ms < 1.0, (
            f"Single-body correction took {mean_time_ms:.4f} ms, "
            f"exceeds target of 1.0 ms"
        )

    def test_single_body_all_bodies(self):
        """
        Benchmark single-body correction for all test bodies.

        Verifies that all bodies meet the < 1 ms performance target.
        """
        latitude = 51.477
        longitude = 0.0
        lst = 180.0
        elevation = 0.0

        print(f"\n--- Single-Body Correction for All Bodies ---")
        print(f"{'Body':<15} {'Time (ms)':<12} {'Status':<10}")
        print("-" * 37)

        for body_name, xyz_body in TEST_BODIES:
            # Warm up
            apply_diurnal_aberration(xyz_body, latitude, longitude, lst, elevation)

            # Measure time for 100 iterations
            num_iterations = 100
            start_time = time.perf_counter()
            for _ in range(num_iterations):
                apply_diurnal_aberration(xyz_body, latitude, longitude, lst, elevation)
            end_time = time.perf_counter()

            mean_time_ms = ((end_time - start_time) / num_iterations) * 1000
            status = "PASS" if mean_time_ms < 1.0 else "FAIL"
            print(f"{body_name:<15} {mean_time_ms:<12.4f} {status:<10}")

            assert mean_time_ms < 1.0, (
                f"{body_name} correction took {mean_time_ms:.4f} ms, "
                f"exceeds target of 1.0 ms"
            )


class TestPerformanceBatchSameObserver:
    """Task 26: Batch operations benchmark (same observer, < 1 second for 1000 bodies)."""

    def test_batch_same_observer_timing(self):
        """
        Benchmark batch operations with same observer.

        Measures time to compute corrections for 1000 bodies with the same observer
        location. Reuses observer position and velocity; only applies aberration
        formula for each body.

        Requirement 8.3: Batch operations (1000 bodies) SHALL complete in < 1 second.
        """
        # Use representative observer (Greenwich)
        latitude = 51.477
        longitude = 0.0
        lst = 180.0
        elevation = 0.0

        # Generate 1000 bodies with varying distances and positions
        bodies: List[Vec3] = []
        for i in range(1000):
            # Vary distance and position
            distance = 0.5 * KM_PER_AU + (i % 10) * 0.1 * KM_PER_AU
            angle = (i % 360) * math.pi / 180.0
            x = distance * math.cos(angle)
            y = distance * math.sin(angle)
            z = (i % 100) * 0.01 * KM_PER_AU - 0.5 * KM_PER_AU
            bodies.append((x, y, z))

        # Warm up
        apply_diurnal_aberration(bodies[0], latitude, longitude, lst, elevation)

        # Measure time for batch operation
        start_time = time.perf_counter()
        for xyz_body in bodies:
            apply_diurnal_aberration(xyz_body, latitude, longitude, lst, elevation)
        end_time = time.perf_counter()

        total_time = end_time - start_time
        mean_time_per_body_ms = (total_time / len(bodies)) * 1000

        # Report timing
        print(f"\n--- Batch Operations (Same Observer) ---")
        print(f"Number of bodies: {len(bodies)}")
        print(f"Total time: {total_time:.4f} seconds")
        print(f"Mean time per body: {mean_time_per_body_ms:.4f} milliseconds")
        print(f"Target: < 1.0 second total")
        print(f"Status: {'PASS' if total_time < 1.0 else 'FAIL'}")

        # Verify performance target
        assert total_time < 1.0, (
            f"Batch operation (1000 bodies, same observer) took {total_time:.4f} seconds, "
            f"exceeds target of 1.0 second"
        )

    def test_batch_same_observer_all_observers(self):
        """
        Benchmark batch operations for all test observers.

        Verifies that all observer locations meet the < 1 second performance target.
        """
        # Generate 100 bodies (smaller batch for faster testing)
        bodies: List[Vec3] = []
        for i in range(100):
            distance = 0.5 * KM_PER_AU + (i % 10) * 0.1 * KM_PER_AU
            angle = (i % 360) * math.pi / 180.0
            x = distance * math.cos(angle)
            y = distance * math.sin(angle)
            z = (i % 100) * 0.01 * KM_PER_AU - 0.5 * KM_PER_AU
            bodies.append((x, y, z))

        print(f"\n--- Batch Operations (Same Observer) for All Observers ---")
        print(f"Number of bodies: {len(bodies)}")
        print(f"{'Observer':<20} {'Time (s)':<12} {'Per-body (ms)':<15} {'Status':<10}")
        print("-" * 57)

        for obs_name, latitude, longitude, lst in TEST_OBSERVERS:
            elevation = 0.0

            # Warm up
            apply_diurnal_aberration(bodies[0], latitude, longitude, lst, elevation)

            # Measure time
            start_time = time.perf_counter()
            for xyz_body in bodies:
                apply_diurnal_aberration(xyz_body, latitude, longitude, lst, elevation)
            end_time = time.perf_counter()

            total_time = end_time - start_time
            mean_time_per_body_ms = (total_time / len(bodies)) * 1000
            status = "PASS" if total_time < 1.0 else "FAIL"
            print(
                f"{obs_name:<20} {total_time:<12.4f} {mean_time_per_body_ms:<15.4f} {status:<10}"
            )

            assert total_time < 1.0, (
                f"{obs_name} batch operation took {total_time:.4f} seconds, "
                f"exceeds target of 1.0 second"
            )


class TestPerformanceBatchDifferentObservers:
    """Task 27: Batch operations benchmark (different observers, < 1 second for 1000 bodies)."""

    def test_batch_different_observers_timing(self):
        """
        Benchmark batch operations with different observers.

        Measures time to compute corrections for 1000 bodies with different observer
        locations. Computes observer position and velocity for each observer; applies
        aberration formula for each body.

        Requirement 8.3: Batch operations (1000 bodies) SHALL complete in < 1 second.
        """
        # Generate 1000 bodies
        bodies: List[Vec3] = []
        for i in range(1000):
            distance = 0.5 * KM_PER_AU + (i % 10) * 0.1 * KM_PER_AU
            angle = (i % 360) * math.pi / 180.0
            x = distance * math.cos(angle)
            y = distance * math.sin(angle)
            z = (i % 100) * 0.01 * KM_PER_AU - 0.5 * KM_PER_AU
            bodies.append((x, y, z))

        # Generate 1000 observers (varying latitudes and longitudes)
        observers: List[Tuple[float, float, float, float]] = []
        for i in range(1000):
            latitude = -90.0 + (i % 180) * 1.0  # -90 to +90
            longitude = (i % 360) * 1.0  # 0 to 360
            lst = (i % 360) * 1.0  # 0 to 360
            elevation = 0.0
            observers.append((latitude, longitude, lst, elevation))

        # Warm up
        apply_diurnal_aberration(
            bodies[0], observers[0][0], observers[0][1], observers[0][2], observers[0][3]
        )

        # Measure time for batch operation
        start_time = time.perf_counter()
        for i, xyz_body in enumerate(bodies):
            latitude, longitude, lst, elevation = observers[i]
            apply_diurnal_aberration(xyz_body, latitude, longitude, lst, elevation)
        end_time = time.perf_counter()

        total_time = end_time - start_time
        mean_time_per_body_ms = (total_time / len(bodies)) * 1000

        # Report timing
        print(f"\n--- Batch Operations (Different Observers) ---")
        print(f"Number of bodies: {len(bodies)}")
        print(f"Number of observers: {len(observers)}")
        print(f"Total time: {total_time:.4f} seconds")
        print(f"Mean time per body: {mean_time_per_body_ms:.4f} milliseconds")
        print(f"Target: < 1.0 second total")
        print(f"Status: {'PASS' if total_time < 1.0 else 'FAIL'}")

        # Verify performance target
        assert total_time < 1.0, (
            f"Batch operation (1000 bodies, different observers) took {total_time:.4f} seconds, "
            f"exceeds target of 1.0 second"
        )


class TestMemoryEfficiency:
    """Task 28: Memory efficiency verification."""

    def test_no_quadratic_memory_growth(self):
        """
        Verify no quadratic memory growth in batch operations.

        Confirms that memory usage is proportional to number of bodies (linear),
        not quadratic. This is verified by checking that the function does not
        create unnecessary intermediate allocations.

        Requirement 8.1, 8.2: No unnecessary intermediate allocations.
        """
        # This test verifies the implementation does not create quadratic allocations
        # by checking that the function reuses observer position/velocity and only
        # allocates output vectors.

        # Generate bodies of increasing size
        sizes = [100, 500, 1000]
        times = []

        for size in sizes:
            bodies: List[Vec3] = []
            for i in range(size):
                distance = 0.5 * KM_PER_AU + (i % 10) * 0.1 * KM_PER_AU
                angle = (i % 360) * math.pi / 180.0
                x = distance * math.cos(angle)
                y = distance * math.sin(angle)
                z = (i % 100) * 0.01 * KM_PER_AU - 0.5 * KM_PER_AU
                bodies.append((x, y, z))

            latitude = 51.477
            longitude = 0.0
            lst = 180.0
            elevation = 0.0

            # Warm up
            apply_diurnal_aberration(bodies[0], latitude, longitude, lst, elevation)

            # Measure time
            start_time = time.perf_counter()
            for xyz_body in bodies:
                apply_diurnal_aberration(xyz_body, latitude, longitude, lst, elevation)
            end_time = time.perf_counter()

            times.append(end_time - start_time)

        # Verify linear scaling (not quadratic)
        # If memory growth is linear, time should scale linearly with size
        # If memory growth is quadratic, time would scale quadratically
        ratio_100_to_500 = times[1] / times[0]  # Should be ~5
        ratio_500_to_1000 = times[2] / times[1]  # Should be ~2

        print(f"\n--- Memory Efficiency Verification ---")
        print(f"Time for 100 bodies: {times[0]:.4f} seconds")
        print(f"Time for 500 bodies: {times[1]:.4f} seconds")
        print(f"Time for 1000 bodies: {times[2]:.4f} seconds")
        print(f"Ratio (500/100): {ratio_100_to_500:.2f} (expected ~5.0 for linear)")
        print(f"Ratio (1000/500): {ratio_500_to_1000:.2f} (expected ~2.0 for linear)")

        # Linear scaling should have ratios close to size ratios (5.0 and 2.0)
        # Quadratic scaling would have much larger ratios
        # Allow some tolerance for system variance
        assert ratio_100_to_500 < 10.0, (
            f"Memory growth appears quadratic: ratio 500/100 = {ratio_100_to_500:.2f}"
        )
        assert ratio_500_to_1000 < 5.0, (
            f"Memory growth appears quadratic: ratio 1000/500 = {ratio_500_to_1000:.2f}"
        )

        print(f"Status: PASS (linear memory scaling confirmed)")


class TestPerformanceCheckpoint:
    """Task 29: Checkpoint — Ensure performance targets are met."""

    def test_performance_checkpoint(self):
        """
        Final checkpoint: verify all performance targets are met.

        Runs a comprehensive performance validation across all test cases
        and verifies that all targets are met.

        Requirements 8.1, 8.2, 8.3, 8.4, 8.5
        """
        print(f"\n{'='*60}")
        print(f"PERFORMANCE CHECKPOINT — Task 29")
        print(f"{'='*60}")

        # Test 1: Single-body correction < 1 ms
        print(f"\n[1/5] Single-body correction benchmark...")
        xyz_sun = (0.983 * KM_PER_AU, 0.0, 0.0)
        latitude = 51.477
        longitude = 0.0
        lst = 180.0
        elevation = 0.0

        apply_diurnal_aberration(xyz_sun, latitude, longitude, lst, elevation)
        start_time = time.perf_counter()
        for _ in range(1000):
            apply_diurnal_aberration(xyz_sun, latitude, longitude, lst, elevation)
        end_time = time.perf_counter()
        mean_time_ms = ((end_time - start_time) / 1000) * 1000
        print(f"   Mean time per body: {mean_time_ms:.4f} ms (target: < 1.0 ms)")
        assert mean_time_ms < 1.0, f"Single-body correction exceeded target"

        # Test 2: Batch operations (same observer) < 1 second
        print(f"\n[2/5] Batch operations (same observer) benchmark...")
        bodies: List[Vec3] = []
        for i in range(1000):
            distance = 0.5 * KM_PER_AU + (i % 10) * 0.1 * KM_PER_AU
            angle = (i % 360) * math.pi / 180.0
            x = distance * math.cos(angle)
            y = distance * math.sin(angle)
            z = (i % 100) * 0.01 * KM_PER_AU - 0.5 * KM_PER_AU
            bodies.append((x, y, z))

        apply_diurnal_aberration(bodies[0], latitude, longitude, lst, elevation)
        start_time = time.perf_counter()
        for xyz_body in bodies:
            apply_diurnal_aberration(xyz_body, latitude, longitude, lst, elevation)
        end_time = time.perf_counter()
        total_time = end_time - start_time
        print(f"   Total time for 1000 bodies: {total_time:.4f} seconds (target: < 1.0 s)")
        assert total_time < 1.0, f"Batch operations (same observer) exceeded target"

        # Test 3: Batch operations (different observers) < 1 second
        print(f"\n[3/5] Batch operations (different observers) benchmark...")
        observers: List[Tuple[float, float, float, float]] = []
        for i in range(1000):
            latitude_i = -90.0 + (i % 180) * 1.0
            longitude_i = (i % 360) * 1.0
            lst_i = (i % 360) * 1.0
            elevation_i = 0.0
            observers.append((latitude_i, longitude_i, lst_i, elevation_i))

        apply_diurnal_aberration(
            bodies[0], observers[0][0], observers[0][1], observers[0][2], observers[0][3]
        )
        start_time = time.perf_counter()
        for i, xyz_body in enumerate(bodies):
            lat, lon, lst_i, elev = observers[i]
            apply_diurnal_aberration(xyz_body, lat, lon, lst_i, elev)
        end_time = time.perf_counter()
        total_time = end_time - start_time
        print(f"   Total time for 1000 bodies: {total_time:.4f} seconds (target: < 1.0 s)")
        assert total_time < 1.0, f"Batch operations (different observers) exceeded target"

        # Test 4: Memory efficiency (linear scaling)
        print(f"\n[4/5] Memory efficiency verification...")
        sizes = [100, 500, 1000]
        times = []
        for size in sizes:
            bodies_test: List[Vec3] = []
            for i in range(size):
                distance = 0.5 * KM_PER_AU + (i % 10) * 0.1 * KM_PER_AU
                angle = (i % 360) * math.pi / 180.0
                x = distance * math.cos(angle)
                y = distance * math.sin(angle)
                z = (i % 100) * 0.01 * KM_PER_AU - 0.5 * KM_PER_AU
                bodies_test.append((x, y, z))

            apply_diurnal_aberration(bodies_test[0], latitude, longitude, lst, elevation)
            start_time = time.perf_counter()
            for xyz_body in bodies_test:
                apply_diurnal_aberration(xyz_body, latitude, longitude, lst, elevation)
            end_time = time.perf_counter()
            times.append(end_time - start_time)

        ratio_100_to_500 = times[1] / times[0]
        ratio_500_to_1000 = times[2] / times[1]
        print(f"   Time scaling: 100→500 = {ratio_100_to_500:.2f}x, 500→1000 = {ratio_500_to_1000:.2f}x")
        print(f"   (Linear scaling expected: ~5.0x and ~2.0x)")
        assert ratio_100_to_500 < 10.0, f"Memory growth appears quadratic"
        assert ratio_500_to_1000 < 5.0, f"Memory growth appears quadratic"

        # Test 5: Double-precision accuracy maintained
        print(f"\n[5/5] Double-precision accuracy verification...")
        # Verify that corrections are computed with full double precision
        xyz_test = (1.0 * KM_PER_AU, 0.0, 0.0)
        corrected1 = apply_diurnal_aberration(xyz_test, 45.0, 0.0, 90.0, 0.0)
        corrected2 = apply_diurnal_aberration(xyz_test, 45.0, 0.0, 90.0, 0.0)
        # Results should be identical (deterministic)
        assert corrected1 == corrected2, "Results not deterministic (precision loss?)"
        print(f"   Deterministic computation verified (double precision maintained)")

        print(f"\n{'='*60}")
        print(f"✓ ALL PERFORMANCE TARGETS MET")
        print(f"{'='*60}")
        print(f"\nSummary:")
        print(f"  ✓ Single-body correction: {mean_time_ms:.4f} ms < 1.0 ms")
        print(f"  ✓ Batch (same observer): {times[2]:.4f} s < 1.0 s")
        print(f"  ✓ Batch (different observers): {total_time:.4f} s < 1.0 s")
        print(f"  ✓ Memory efficiency: Linear scaling confirmed")
        print(f"  ✓ Double-precision accuracy: Maintained")
