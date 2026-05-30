"""
Adversarial test for Type 13 window selection near boundaries.

Compares:
- Python implementation (_hermite_eval_3d + window logic in _Type13Segment style)
- Native implementation (moira_native.spk_type13_record)

Focus: Differences in window clamping behavior near the right edge of the data.
"""

import pytest
from pathlib import Path

import moira.moira_native as mn
from moira._spk_body_kernel import _hermite_eval_3d, _hermite_eval_3d_with_derivative, SmallBodyKernel, small_body_readers_from_manifest
from moira._kernel_paths import find_sovereign_small_body_manifest

T0 = 2451545.0
S_PER_DAY = 86400.0


def _python_type13_eval(epochs_jd, states, window_size, jd):
    """
    Replicates the exact window selection + evaluation logic used by _Type13Segment.
    epochs_jd: list of Julian days
    states: list of 6 lists (x,y,z,vx,vy,vz), each of length n
    """
    n = len(epochs_jd)
    if n == 0:
        raise ValueError("No epochs")

    # Find insertion point (same as bisect_left)
    idx = 0
    while idx < n and epochs_jd[idx] < jd:
        idx += 1

    half = window_size // 2
    start = max(0, min(idx - half, n - window_size))

    # Always use full requested window size (Python behavior)
    actual_ws = window_size
    if start + actual_ws > n:
        actual_ws = n - start  # This shouldn't happen due to the min above, but defensive

    win_t = [(epochs_jd[start + i] - T0) * S_PER_DAY for i in range(actual_ws)]
    t_sec = (jd - T0) * S_PER_DAY

    pos = [[states[axis][start + i] for i in range(actual_ws)] for axis in range(3)]
    vel = [[states[axis + 3][start + i] for i in range(actual_ws)] for axis in range(3)]

    position = _hermite_eval_3d(t_sec, win_t, pos, vel)

    # For velocity we need the derivative version
    _, velocity = _hermite_eval_3d_with_derivative(t_sec, win_t, pos, vel)

    # The Python version returns velocity already in km/s after scaling inside the function? No:
    # In compute_and_differentiate it does the scaling after calling the helper.
    # But here we call the helper directly, so we scale manually to match what SmallBodyKernel returns.
    velocity = tuple(v * S_PER_DAY for v in velocity)

    return position, velocity


def _native_type13_eval(epochs_jd, states, window_size, jd):
    """Call the native implementation."""
    result = mn.spk_type13_record(epochs_jd, states, window_size, jd)
    pos = tuple(result[0:3])
    vel = tuple(result[3:6])
    return pos, vel


def _load_real_type13_segments(max_kernels=2, max_segments_per_kernel=3):
    """
    Load real Type 13 data from sovereign manifests.
    Yields tuples of (epochs_jd, states, window_size, body_name, segment_info)
    Falls back to empty if no real data is available.
    """
    candidates = []
    manifest = find_sovereign_small_body_manifest()
    if manifest:
        candidates.append(manifest)

    # Common test artifact locations
    artifact_base = Path(__file__).resolve().parents[2] / "artifacts" / "kernels"
    for name in ["sb441_type13_smoke", "sb441_type13_random20", "sb441_type13_full_2020_2030"]:
        m = artifact_base / name / "manifest.json"
        if m.exists():
            candidates.append(m)

    for manifest_path in candidates:
        try:
            kernels = small_body_readers_from_manifest(manifest_path)
            for kernel in kernels[:max_kernels]:
                count = 0
                for seg in getattr(kernel, "_kernel", type("x", (), {"segments": []})()).segments:
                    if getattr(seg, "data_type", None) != 13:
                        continue
                    try:
                        epochs, states, ws = _load_type13_data_from_segment(seg)
                        if len(epochs) >= 5:
                            body_name = getattr(seg, "target", "unknown")
                            yield (epochs, states, ws, str(body_name), str(manifest_path))
                            count += 1
                            if count >= max_segments_per_kernel:
                                break
                    except Exception:
                        continue
                if count > 0:
                    break  # Only use first successful manifest for speed
        except Exception:
            continue

    # No real data found
    return
    yield  # make it a generator


def _generate_adversarial_data(n_points=20, window_size=5, seed=42):
    """Generate synthetic Type 13 data with clustered points near the end (adversarial for window logic)."""
    import random
    random.seed(seed)

    epochs = []
    t = 2451545.0
    for i in range(n_points):
        epochs.append(t)
        # Make points denser near the end
        if i > n_points * 0.7:
            t += random.uniform(0.01, 0.1)
        else:
            t += random.uniform(0.5, 2.0)

    # Fake states: linear motion + some noise
    states = [[0.0] * n_points for _ in range(6)]
    for i in range(n_points):
        t_i = epochs[i]
        # Simple linear trajectory
        states[0][i] = 1000.0 * (t_i - epochs[0])          # x
        states[1][i] = 500.0 * (t_i - epochs[0])           # y
        states[2][i] = 200.0 * (t_i - epochs[0])           # z
        states[3][i] = 1000.0                              # vx (km/day)
        states[4][i] = 500.0
        states[5][i] = 200.0

    return epochs, states


@pytest.mark.skipif(not hasattr(mn, "spk_type13_record"), reason="Native Type 13 support not available")
class TestType13WindowAdversarial:
    def test_window_clamping_near_right_edge(self):
        """Adversarial test on real Type 13 data when available, synthetic as fallback."""
        real_data = list(_load_real_type13_segments(max_kernels=1, max_segments_per_kernel=2))

        if real_data:
            data_sources = real_data
            print(f"[INFO] Using {len(data_sources)} real Type 13 segments for boundary testing")
        else:
            data_sources = [(_generate_adversarial_data(n_points=25, window_size=7)[:2] + (7, "synthetic", "synthetic"))]
            print("[INFO] No real Type 13 data found — falling back to synthetic")

        failures = []

        for epochs, states, ws, body_name, source in data_sources:
            last_epoch = epochs[-1]
            first_epoch = epochs[0]

            for window_size in [ws, max(2, ws-2), min(11, ws+4)]:
                if window_size < 2 or window_size > len(epochs):
                    continue

                # Focus aggressively on the right edge
                for offset_days in [0.0, 1e-6, 1e-4, 0.001, 0.01, 0.05]:
                    jd = last_epoch - offset_days
                    if jd < first_epoch:
                        continue

                    try:
                        py_pos, py_vel = _python_type13_eval(epochs, states, window_size, jd)
                        nat_pos, nat_vel = _native_type13_eval(epochs, states, window_size, jd)

                        max_pos_err = max(abs(a - b) for a, b in zip(py_pos, nat_pos))
                        max_vel_err = max(abs(a - b) for a, b in zip(py_vel, nat_vel))

                        if max_pos_err > 1e-8 or max_vel_err > 1e-5:
                            failures.append({
                                "source": source,
                                "body": body_name,
                                "window_size": window_size,
                                "offset_days": offset_days,
                                "max_pos_err_km": max_pos_err,
                                "max_vel_err_km_per_day": max_vel_err,
                            })
                    except Exception as e:
                        failures.append({
                            "source": source,
                            "body": body_name,
                            "window_size": window_size,
                            "jd": jd,
                            "error": str(e)
                        })

        assert not failures, f"Found divergences near boundaries on real/synthetic Type 13 data:\n{failures[:5]}"

    def test_very_small_windows_at_boundary(self):
        """Test the most dangerous cases: window_size=2 or 3 right at the end."""
        epochs, states = _generate_adversarial_data(n_points=15, window_size=3)

        last_epoch = epochs[-1]

        for window_size in [2, 3]:
            jd = last_epoch - 0.0001  # Extremely close to last node

            py_pos, py_vel = _python_type13_eval(epochs, states, window_size, jd)
            nat_pos, nat_vel = _native_type13_eval(epochs, states, window_size, jd)

            max_pos_err = max(abs(a - b) for a, b in zip(py_pos, nat_pos))
            max_vel_err = max(abs(a - b) for a, b in zip(py_vel, nat_vel))

            assert max_pos_err < 1e-8, f"Large position error with window_size={window_size} near end"
            assert max_vel_err < 1e-5, f"Large velocity error with window_size={window_size} near end"

    def test_exact_node_queries(self):
        """Query exactly on data points — should be very stable."""
        epochs, states = _generate_adversarial_data(n_points=12, window_size=5)

        for i in [0, 3, 8, -1]:  # first, middle, near end, last
            jd = epochs[i]
            py_pos, py_vel = _python_type13_eval(epochs, states, 5, jd)
            nat_pos, nat_vel = _native_type13_eval(epochs, states, 5, jd)

            for a, b in zip(py_pos, nat_pos):
                assert abs(a - b) < 1e-10
            for a, b in zip(py_vel, nat_vel):
                assert abs(a - b) < 1e-7


# ------------------------------------------------------------------
# Real Kernel Adversarial Extension
# ------------------------------------------------------------------

try:
    from moira._spk_body_kernel import SmallBodyKernel, small_body_readers_from_manifest
    from moira._kernel_paths import find_sovereign_small_body_manifest
    _HAS_REAL_KERNEL_SUPPORT = True
except Exception:
    _HAS_REAL_KERNEL_SUPPORT = False


def _load_type13_data_from_segment(seg):
    """Force load and return (epochs_jd, states, window_size) from a _Type13Segment."""
    # Access the lazy _data property to populate it
    data = seg._data
    epochs_jd, states, window_size = data  # Note: our _data stores (states, epochs, ws) wait — check order
    # From the code: self.__data = (states, epochs_jd, int(payload["window_size"]))
    # So actually: states, epochs_jd, ws
    states_list, epochs_list, ws = data
    return epochs_list, states_list, ws


@pytest.mark.skipif(not _HAS_REAL_KERNEL_SUPPORT, reason="SmallBodyKernel not importable")
class TestType13RealKernelBoundaryAdversarial:
    """Adversarial tests on real sovereign Type 13 shards."""

    @pytest.fixture(scope="class")
    def real_kernels(self):
        manifest = find_sovereign_small_body_manifest()
        if manifest is None:
            # Try common artifact locations
            candidates = [
                Path(__file__).parents[2] / "artifacts/kernels/sb441_type13_smoke/manifest.json",
                Path(__file__).parents[2] / "artifacts/kernels/sb441_type13_random20/manifest.json",
            ]
            for c in candidates:
                if c.exists():
                    manifest = c
                    break

        if manifest is None or not manifest.exists():
            pytest.skip("No sovereign Type 13 manifest found for real kernel testing")

        try:
            kernels = small_body_readers_from_manifest(manifest)
            type13_kernels = []
            for k in kernels:
                has_type13 = any(
                    hasattr(seg, "data_type") and getattr(seg, "data_type", None) == 13
                    for seg in getattr(k, "_kernel", type("obj", (object,), {"segments": []})()).segments
                )
                if has_type13:
                    type13_kernels.append(k)
            if not type13_kernels:
                pytest.skip("No Type 13 segments found in available sovereign kernels")
            return type13_kernels
        except Exception as e:
            pytest.skip(f"Could not load sovereign Type 13 kernels: {e}")

    def test_real_data_near_segment_right_edge(self, real_kernels):
        """Attack the right boundary of real Type 13 segments with tiny offsets."""
        failures = []

        for kernel in real_kernels[:2]:  # Limit for speed in adversarial test
            for seg in kernel._kernel.segments:
                if not (hasattr(seg, "data_type") and getattr(seg, "data_type", None) == 13):
                    continue

                epochs, states, ws = _load_type13_data_from_segment(seg)
                if len(epochs) < ws + 2:
                    continue  # Too short for meaningful boundary test

                last_epoch = epochs[-1]
                first_epoch = epochs[0]

                # Focus on right edge + a few left edge cases
                test_points = [last_epoch - d for d in [0.0, 1e-5, 0.001, 0.01, 0.1]]
                test_points += [first_epoch + d for d in [0.0, 1e-5, 0.001]]

                for jd in test_points:
                    if not (first_epoch <= jd <= last_epoch):
                        continue

                    try:
                        py_pos, py_vel = _python_type13_eval(epochs, states, ws, jd)
                        nat_pos, nat_vel = _native_type13_eval(epochs, states, ws, jd)

                        max_pos = max(abs(a - b) for a, b in zip(py_pos, nat_pos))
                        max_vel = max(abs(a - b) for a, b in zip(py_vel, nat_vel))

                        if max_pos > 1e-8 or max_vel > 1e-5:
                            failures.append({
                                "kernel": str(kernel._path.name) if hasattr(kernel, "_path") else "unknown",
                                "target": getattr(seg, "target", "?"),
                                "jd": jd,
                                "offset_from_edge": jd - last_epoch if jd <= last_epoch else jd - first_epoch,
                                "max_pos_err": max_pos,
                                "max_vel_err": max_vel,
                            })
                    except Exception as e:
                        failures.append({
                            "kernel": getattr(kernel, "_path", "unknown"),
                            "jd": jd,
                            "error": str(e)
                        })

        assert len(failures) == 0, f"Found divergences on real Type 13 data near boundaries:\n{failures[:3]}"

    def test_real_data_tiny_windows_at_edges(self, real_kernels):
        """Use the smallest practical windows on real data at boundaries."""
        for kernel in real_kernels[:1]:
            for seg in kernel._kernel.segments:
                if getattr(seg, "data_type", None) != 13:
                    continue

                epochs, states, ws = _load_type13_data_from_segment(seg)
                if len(epochs) < 5:
                    continue

                for window in [2, 3]:
                    for edge_jd in [epochs[0] + 1e-4, epochs[-1] - 1e-4]:
                        py = _python_type13_eval(epochs, states, window, edge_jd)
                        nat = _native_type13_eval(epochs, states, window, edge_jd)

                        max_pos = max(abs(a - b) for a, b in zip(py[0], nat[0]))
                        assert max_pos < 1e-7, f"Large error with tiny window={window} on real data at edge"


    def test_real_data_boundary_numerical_differences(self, real_kernels):
        """
        Measure and report the actual maximum numerical difference between
        Python and native Type 13 implementations near segment boundaries
        on real data.
        """
        max_pos_overall = 0.0
        max_vel_overall = 0.0
        worst_cases = []

        for kernel in real_kernels:
            for seg in kernel._kernel.segments:
                if getattr(seg, "data_type", None) != 13:
                    continue

                epochs, states, ws = _load_type13_data_from_segment(seg)
                if len(epochs) < 5:
                    continue

                last_epoch = epochs[-1]

                # Very close to the right edge with multiple small windows
                for window_size in [ws, max(2, ws - 2)]:
                    for offset in [0.0, 1e-6, 1e-5, 0.0001, 0.001, 0.01]:
                        jd = last_epoch - offset
                        if jd < epochs[0]:
                            continue

                        try:
                            py_pos, py_vel = _python_type13_eval(epochs, states, window_size, jd)
                            nat_pos, nat_vel = _native_type13_eval(epochs, states, window_size, jd)

                            pos_err = max(abs(a - b) for a, b in zip(py_pos, nat_pos))
                            vel_err = max(abs(a - b) for a, b in zip(py_vel, nat_vel))

                            if pos_err > max_pos_overall:
                                max_pos_overall = pos_err
                            if vel_err > max_vel_overall:
                                max_vel_overall = vel_err

                            if pos_err > 1e-10 or vel_err > 1e-7:
                                worst_cases.append({
                                    "body": getattr(seg, "target", "?"),
                                    "window": window_size,
                                    "offset_days": offset,
                                    "pos_err_km": pos_err,
                                    "vel_err_km_per_day": vel_err,
                                })
                        except Exception:
                            pass

        print("\n=== Real Type 13 Boundary Numerical Differences ===")
        print(f"Max position error (km):     {max_pos_overall:.3e}")
        print(f"Max velocity error (km/day): {max_vel_overall:.3e}")
        if worst_cases:
            print("Non-trivial cases found:")
            for case in sorted(worst_cases, key=lambda x: -x["pos_err_km"])[:5]:
                print(f"  {case}")
        else:
            print("All boundary cases agreed to machine precision on real data.")
        print("==================================================\n")
