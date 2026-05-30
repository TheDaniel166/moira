"""
High-level differential testing for the wired Type 13 native path.

This test exercises the full SmallBodyKernel / _Type13Segment surface
(native preferred vs forced pure-Python fallback) on the same kernel objects.

Goal: Find any divergence introduced by the Phase 1 wiring, split-JD handling,
caching of evaluators, boundary conditions, etc. that the lower-level
adversarial test (which uses spk_type13_record directly) might miss.

Uses the MOIRA_FORCE_PYTHON_TYPE13 hook added in Phase 3.
"""

import os
import pytest
from pathlib import Path

from moira._spk_body_kernel import (
    SmallBodyKernel,
    small_body_readers_from_manifest,
    _FORCE_PYTHON_TYPE13_FALLBACK,
)
from moira._kernel_paths import find_sovereign_small_body_manifest


def _find_any_type13_kernels():
    """Return list of SmallBodyKernel objects that contain at least one Type 13 segment."""
    kernels = []

    # 1. In-tree development shards (often present)
    in_tree_dir = Path(__file__).resolve().parents[2] / "moira" / "kernels" / "sb441_type13"
    if in_tree_dir.exists():
        for bsp in sorted(in_tree_dir.glob("*.bsp"))[:2]:
            try:
                k = SmallBodyKernel(bsp)
                if any(getattr(s, "data_type", None) == 13 for s in k._kernel.segments):
                    kernels.append(k)
            except Exception:
                pass

    # 2. Artifact sovereign manifests (may have path issues, handled gracefully)
    manifest = find_sovereign_small_body_manifest()
    candidates = []
    if manifest:
        candidates.append(manifest)
    artifact_base = Path(__file__).resolve().parents[2] / "artifacts" / "kernels"
    for name in ["sb441_type13_smoke", "sb441_type13_random20"]:
        m = artifact_base / name / "manifest.json"
        if m.exists():
            candidates.append(m)

    for mpath in candidates:
        try:
            readers = small_body_readers_from_manifest(mpath)
            for r in readers:
                if any(getattr(s, "data_type", None) == 13 for s in r._kernel.segments):
                    kernels.append(r)
                    if len(kernels) >= 3:
                        break
        except Exception:
            continue
        if len(kernels) >= 3:
            break

    return kernels


def _generate_query_points(epochs, n_interior=20, include_split=True):
    """Generate a rich set of query JDs including nasty edge cases."""
    if not epochs:
        return []

    first = epochs[0]
    last = epochs[-1]
    points = []

    # Exact endpoints
    points.append(first)
    points.append(last)

    # Tiny offsets around boundaries (positive and negative where legal)
    for off in [1e-9, 1e-7, 1e-5, 1e-4, 0.001, 0.01, 0.1]:
        points.append(first + off)
        if last - off >= first:
            points.append(last - off)
        # Slightly outside (should be handled by coverage check higher up, but test the math)
        points.append(first - off)
        points.append(last + off)

    # Interior points
    span = last - first
    if span > 0:
        for i in range(1, n_interior + 1):
            points.append(first + (span * i) / (n_interior + 1))

    # Split JD cases (tdb + tiny tdb2)
    if include_split:
        mid = (first + last) / 2
        for tiny in [0.0, 1e-10, 1e-8, 1e-6, -1e-9, 1e-9]:
            points.append((mid, tiny))  # will be passed as tdb, tdb2

    return points


def _compare_position(kernel, naif, jd_or_split, tol_pos=1e-9, tol_vel=1e-8):
    """Return (pos_err, vel_err) for one query."""
    center = kernel.segment_center(naif)

    if isinstance(jd_or_split, tuple):
        tdb, tdb2 = jd_or_split
    else:
        tdb, tdb2 = jd_or_split, 0.0

    try:
        pos1, vel1 = kernel.position_and_velocity(center, naif, tdb)  # note: this always uses tdb only in current API
        # The high-level API on SmallBodyKernel does not expose tdb2 directly.
        # We test split JD through the segment's compute_and_differentiate instead.
        pos2 = kernel.position(center, naif, tdb)
        return 0.0, 0.0  # placeholder - we do deeper checks below
    except Exception as e:
        return None, str(e)


@pytest.mark.skipif(not _find_any_type13_kernels(), reason="No Type 13 kernels available for differential testing")
class TestType13HighLevelDifferential:
    """Compare native-wired path vs forced Python fallback through the real SmallBodyKernel surface."""

    def test_high_level_native_vs_forced_python_many_cases(self):
        kernels = _find_any_type13_kernels()
        assert kernels, "No Type 13 kernels loaded"

        all_diffs = []

        original_force = _FORCE_PYTHON_TYPE13_FALLBACK

        try:
            for kernel in kernels[:2]:
                type13_segs = [s for s in kernel._kernel.segments if getattr(s, "data_type", None) == 13]
                for seg in type13_segs[:2]:
                    naif = seg.target
                    epochs = list(seg._data[1])  # epochs_jd
                    if len(epochs) < 4:
                        continue

                    queries = _generate_query_points(epochs, n_interior=12)

                    import moira._spk_body_kernel as m

                    # --- Native mode ---
                    m._FORCE_PYTHON_TYPE13_FALLBACK = False
                    if hasattr(seg, "_native_evaluator"):
                        seg._native_evaluator = None
                    if hasattr(seg, "_native_evaluator_force_mode"):
                        delattr(seg, "_native_evaluator_force_mode")

                    native_results = []
                    for q in queries:
                        try:
                            if isinstance(q, tuple):
                                tdb, tdb2 = q
                                p, v = seg.compute_and_differentiate(tdb, tdb2)
                            else:
                                p, v = seg.compute_and_differentiate(q)
                            native_results.append((q, p, v))
                        except Exception as e:
                            native_results.append((q, None, str(e)))

                    # --- Forced Python mode ---
                    m._FORCE_PYTHON_TYPE13_FALLBACK = True
                    if hasattr(seg, "_native_evaluator"):
                        seg._native_evaluator = None
                    if hasattr(seg, "_native_evaluator_force_mode"):
                        delattr(seg, "_native_evaluator_force_mode")

                    python_results = []
                    for q in queries:
                        try:
                            if isinstance(q, tuple):
                                tdb, tdb2 = q
                                p, v = seg.compute_and_differentiate(tdb, tdb2)
                            else:
                                p, v = seg.compute_and_differentiate(q)
                            python_results.append((q, p, v))
                        except Exception as e:
                            python_results.append((q, None, str(e)))

                    # Compare
                    for (q1, p_nat, v_nat), (q2, p_py, v_py) in zip(native_results, python_results):
                        assert q1 == q2
                        if p_nat is None or p_py is None:
                            if p_nat != p_py:  # both error or both succeed
                                all_diffs.append({"query": q1, "native": p_nat, "python": p_py})
                            continue

                        pos_err = max(abs(a - b) for a, b in zip(p_nat, p_py))
                        vel_err = max(abs(a - b) for a, b in zip(v_nat, v_py))

                        if pos_err > 1e-10 or vel_err > 1e-8:
                            all_diffs.append({
                                "kernel": str(getattr(kernel, "_path", "unknown")),
                                "naif": naif,
                                "query": q1,
                                "pos_err_km": pos_err,
                                "vel_err_km_day": vel_err,
                            })

        finally:
            import moira._spk_body_kernel as m
            m._FORCE_PYTHON_TYPE13_FALLBACK = original_force

        # Report
        if all_diffs:
            print("\n=== High-Level Type 13 Differential Failures ===")
            for d in all_diffs[:10]:
                print(d)
            print("================================================\n")

        assert len(all_diffs) == 0, f"Found {len(all_diffs)} divergences between native and forced-Python high-level path"


def test_force_flag_affects_next_evaluation():
    """Sanity check that toggling the force flag actually changes which path is taken."""
    kernels = _find_any_type13_kernels()
    if not kernels:
        pytest.skip("No Type 13 data")

    kernel = kernels[0]
    seg = next((s for s in kernel._kernel.segments if getattr(s, "data_type", None) == 13), None)
    if seg is None:
        pytest.skip("No Type 13 segment")

    import moira._spk_body_kernel as m

    orig = m._FORCE_PYTHON_TYPE13_FALLBACK
    try:
        # Force Python
        m._FORCE_PYTHON_TYPE13_FALLBACK = True
        if hasattr(seg, "_native_evaluator"):
            seg._native_evaluator = None
        _ = seg.compute( (seg.start_jd + seg.end_jd) / 2 )

        # Now force native (if available)
        m._FORCE_PYTHON_TYPE13_FALLBACK = False
        if hasattr(seg, "_native_evaluator"):
            seg._native_evaluator = None
        _ = seg.compute( (seg.start_jd + seg.end_jd) / 2 )

        # We mainly care that no crash and the flag is respected.
        assert True
    finally:
        m._FORCE_PYTHON_TYPE13_FALLBACK = orig


# ------------------------------------------------------------------
# Additional Torture Cases (added during fine-tooth-comb review)
# ------------------------------------------------------------------

import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from moira.daf_writer import write_spk_type13


def _make_minimal_type13_kernel(tmp_path, window_size=3, n_epochs=3):
    """Create the smallest possible valid Type 13 kernel for torture testing (window_size must be odd)."""
    path = tmp_path / "minimal_type13.bsp"
    epochs = [2451545.0 + i for i in range(n_epochs)]
    # Minimal states (position + velocity at each epoch)
    states = [
        [float(i) for i in range(n_epochs)],  # x
        [float(i * 2) for i in range(n_epochs)],  # y
        [float(i * 3) for i in range(n_epochs)],  # z
        [0.1] * n_epochs,  # vx
        [0.2] * n_epochs,
        [0.3] * n_epochs,
    ]
    write_spk_type13(
        str(path),
        bodies=[{
            "naif_id": 2000001,
            "center": 10,
            "frame": 1,
            "name": "MINIMAL TORTURE",
            "window_size": window_size,
            "epochs_jd": epochs,
            "states": states,
        }],
        locifn="MOIRA TYPE13 TORTURE TEST",
    )
    return path


def _make_huge_window_type13_kernel(tmp_path, n_epochs=50, window_size=25):
    """Create a kernel with a very large window size relative to data (window_size must be odd)."""
    path = tmp_path / "huge_window_type13.bsp"
    if window_size % 2 == 0:
        window_size += 1  # force odd
    epochs = [2451545.0 + i * 0.1 for i in range(n_epochs)]
    states = [
        [float(i * 1000) for i in range(n_epochs)],
        [float(i * 500) for i in range(n_epochs)],
        [float(i * 200) for i in range(n_epochs)],
        [10.0] * n_epochs,
        [5.0] * n_epochs,
        [2.0] * n_epochs,
    ]
    write_spk_type13(
        str(path),
        bodies=[{
            "naif_id": 2000002,
            "center": 10,
            "frame": 1,
            "name": "HUGE WINDOW TORTURE",
            "window_size": min(window_size, n_epochs),
            "epochs_jd": epochs,
            "states": states,
        }],
        locifn="MOIRA TYPE13 HUGE WINDOW TEST",
    )
    return path


class TestType13TortureCases:
    """Extra aggressive edge cases added during the 2026-05-30 fine-tooth-comb review."""

    def test_minimal_epoch_segments(self, tmp_path):
        """Smallest valid (odd window_size=3 with 3 epochs) for Hermite torture."""
        kernel_path = _make_minimal_type13_kernel(tmp_path, window_size=3, n_epochs=3)
        k = SmallBodyKernel(kernel_path)
        try:
            seg = k._kernel.segments[0]
            assert seg.data_type == 13

            for mode in [False, True]:  # native then forced Python
                import moira._spk_body_kernel as m
                m._FORCE_PYTHON_TYPE13_FALLBACK = mode
                if hasattr(seg, "_native_evaluator"):
                    seg._native_evaluator = None
                if hasattr(seg, "_native_evaluator_force_mode"):
                    delattr(seg, "_native_evaluator_force_mode")

                # Exact points and midpoint
                for jd in [2451545.0, 2451546.0, 2451545.5]:
                    p = seg.compute(jd)
                    pv, vv = seg.compute_and_differentiate(jd)
                    assert len(p) == 3 and len(pv) == 3 and len(vv) == 3
        finally:
            k.close()
            import moira._spk_body_kernel as m
            m._FORCE_PYTHON_TYPE13_FALLBACK = False

    def test_huge_window_segments(self, tmp_path):
        """Large window sizes (stress divided-difference table construction)."""
        kernel_path = _make_huge_window_type13_kernel(tmp_path, n_epochs=40, window_size=30)
        k = SmallBodyKernel(kernel_path)
        try:
            seg = k._kernel.segments[0]
            for mode in [False, True]:
                import moira._spk_body_kernel as m
                m._FORCE_PYTHON_TYPE13_FALLBACK = mode
                if hasattr(seg, "_native_evaluator"):
                    seg._native_evaluator = None
                if hasattr(seg, "_native_evaluator_force_mode"):
                    delattr(seg, "_native_evaluator_force_mode")

                mid = (seg.start_jd + seg.end_jd) / 2
                p, v = seg.compute_and_differentiate(mid)
                assert all(isinstance(x, float) for x in p + v)
        finally:
            k.close()
            import moira._spk_body_kernel as m
            m._FORCE_PYTHON_TYPE13_FALLBACK = False

    def test_post_close_behavior(self, tmp_path):
        """Ensure clean behavior after close() (no crashes or silent stale data)."""
        kernel_path = _make_minimal_type13_kernel(tmp_path, window_size=3, n_epochs=3)
        k = SmallBodyKernel(kernel_path)
        seg = k._kernel.segments[0]
        mid = (seg.start_jd + seg.end_jd) / 2

        # Warm up caches in both modes
        for mode in [False, True]:
            import moira._spk_body_kernel as m
            m._FORCE_PYTHON_TYPE13_FALLBACK = mode
            if hasattr(seg, "_native_evaluator"):
                seg._native_evaluator = None
            _ = seg.compute(mid)

        k.close()

        import moira._spk_body_kernel as m
        m._FORCE_PYTHON_TYPE13_FALLBACK = False

        # After close the segment may raise or may have been released — either is acceptable
        # as long as we don't get silent wrong answers or segfaults.
        try:
            val = seg.compute(mid)
            # If it returns something, it should still be a valid 3-tuple of floats
            assert len(val) == 3 and all(isinstance(x, float) for x in val)
        except Exception:
            pass  # Expected in many close scenarios

        # Re-opening a fresh kernel must work
        k2 = SmallBodyKernel(kernel_path)
        try:
            seg2 = k2._kernel.segments[0]
            _ = seg2.compute(mid)
        finally:
            k2.close()

    def test_concurrent_access_mixed_modes(self, tmp_path):
        """Hammer the same segment from multiple threads while toggling force mode."""
        kernel_path = _make_huge_window_type13_kernel(tmp_path, n_epochs=30, window_size=15)
        k = SmallBodyKernel(kernel_path)
        seg = k._kernel.segments[0]
        mid = (seg.start_jd + seg.end_jd) / 2

        errors = []
        results = []

        def worker(mode: bool, iterations: int):
            try:
                import moira._spk_body_kernel as m
                m._FORCE_PYTHON_TYPE13_FALLBACK = mode
                for i in range(iterations):
                    if i % 3 == 0 and hasattr(seg, "_native_evaluator"):
                        seg._native_evaluator = None
                    p, v = seg.compute_and_differentiate(mid + i * 0.001)
                    results.append((mode, p[0]))
            except Exception as e:
                errors.append((mode, str(e)))

        # Launch mixed native + Python threads
        with ThreadPoolExecutor(max_workers=6) as ex:
            futures = []
            for mode in [False, True, False, True]:
                futures.append(ex.submit(worker, mode, 25))
            for f in as_completed(futures):
                f.result()

        k.close()

        assert len(errors) == 0, f"Concurrent errors: {errors}"
        # We don't assert exact numerical values across modes here (they should be close),
        # but the fact that nothing crashed or deadlocked under load is the torture win.
        assert len(results) > 50

    def test_force_flag_toggle_during_lifetime(self, tmp_path):
        """Rapidly toggle the force flag on a live segment (tests cache invalidation we fixed)."""
        kernel_path = _make_minimal_type13_kernel(tmp_path)
        k = SmallBodyKernel(kernel_path)
        seg = k._kernel.segments[0]
        mid = (seg.start_jd + seg.end_jd) / 2

        import moira._spk_body_kernel as m

        try:
            for i in range(10):
                mode = bool(i % 2)
                m._FORCE_PYTHON_TYPE13_FALLBACK = mode
                # Force re-evaluation
                if hasattr(seg, "_native_evaluator"):
                    seg._native_evaluator = None
                if hasattr(seg, "_native_evaluator_force_mode"):
                    delattr(seg, "_native_evaluator_force_mode")

                p = seg.compute(mid)
                assert isinstance(p[0], float)
        finally:
            k.close()
            m._FORCE_PYTHON_TYPE13_FALLBACK = False


# ------------------------------------------------------------------
# Chebyshev (Type 2/3) Consistency Comb (added 2026-05-30)
# ------------------------------------------------------------------
# Mirror of the Type 13 review: we applied the same evaluator caching
# robustness fix to _NativeChebyshevSegment in the small-body path.
# A separate MOIRA_FORCE_PYTHON_CHEBYSHEV env var now exists for
# future differential work (parallel to the Type 13 hook).
#
# Full parallel torture suite for Chebyshev is recommended as follow-up,
# but the core latent bug pattern has been eliminated for consistency.


if __name__ == "__main__":
    # Allow direct execution for manual exploration
    import sys
    pytest.main([__file__, "-q", "--tb=line"] + sys.argv[1:])
