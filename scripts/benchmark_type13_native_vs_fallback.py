"""
Phase 3 Benchmark: Native Type 13 Hermite vs Pure-Python Fallback

Measures the performance delta for SPK Type 13 evaluation after wiring the
native `SpkSegmentEvaluator` (data_type=13) as the preferred path.

Compares:
  - Native path (default after Phase 1)
  - Pure-Python fallback (forced via MOIRA_FORCE_PYTHON_TYPE13=1 or flag)

Focuses on real sovereign Type 13 shards (sb441_type13_* artifacts).

Outputs structured JSON artifact + human-readable summary with speedups.

Usage:
    python scripts/benchmark_type13_native_vs_fallback.py
    MOIRA_FORCE_PYTHON_TYPE13=1 python scripts/benchmark_type13_native_vs_fallback.py   # for pure-Py baseline
"""

from __future__ import annotations

import json
import os
import statistics
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from moira._kernel_paths import find_sovereign_small_body_manifest
from moira._spk_body_kernel import (
    SmallBodyKernel,
    small_body_readers_from_manifest,
    _FORCE_PYTHON_TYPE13_FALLBACK,
)
from moira import moira_native

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ARTIFACT = Path("tests/artifacts/benchmarks/type13_native_evaluation_phase3.json")
WARMUP = 3
REPEATS = 5
POSITIONS_PER_RUN = 2000          # realistic single-body repeated query load
BULK_BODIES = 50                  # for simulated bulk-style workload
MICRO_WINDOW_SIZES = (4, 8, 12)   # common window sizes seen in Type 13 data

# Representative bodies from the smoke/random20 shards (stable across runs)
PREFERRED_BODIES = [
    2000001,   # Ceres (very common in sb441 shards)
    2000004,   # Vesta
    2000216,   # Kleopatra
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_type13_manifest() -> Path | None:
    """Prefer small, fast manifests for benchmarking."""
    candidates = [
        ROOT / "tests/artifacts/kernels/sb441_type13_smoke/manifest.json",
        ROOT / "tests/artifacts/kernels/sb441_type13_random20/manifest.json",
        find_sovereign_small_body_manifest(),
    ]
    for c in candidates:
        if c and c.exists():
            return c
    return None


def _discover_type13_kernels_direct() -> list[Path]:
    """Fallback discovery for Type 13 data when manifests have path issues."""
    found: list[Path] = []

    # 1. In-tree sovereign shards (often present for development)
    in_tree = ROOT / "moira/kernels/sb441_type13"
    if in_tree.exists():
        found.extend(sorted(in_tree.glob("*.bsp")))

    # 2. Artifact directories (various layouts)
    base = ROOT / "tests/artifacts/kernels"
    for name in ("sb441_type13_smoke", "sb441_type13_random20", "sb441_type13_full_2020_2030"):
        d = base / name
        if d.exists():
            found.extend(d.glob("*.bsp"))
            for sub in d.iterdir():
                if sub.is_dir():
                    found.extend(sub.glob("**/*.bsp"))

    # 3. Classic kernels known to contain Type 13 (used by other native benchmarks)
    for classic in ("sb441-n373s.bsp", "asteroids.bsp", "centaurs.bsp", "minor_bodies.bsp"):
        p = base / classic
        if p.exists():
            found.append(p)

    return sorted(set(found))[:6]  # limit for reasonable benchmark runtime


@contextmanager
def _load_type13_kernels(manifest_path: Path | None):
    kernels: list[SmallBodyKernel] = []
    try:
        if manifest_path and manifest_path.exists():
            try:
                kernels = small_body_readers_from_manifest(manifest_path)
            except FileNotFoundError:
                # Manifest has broken relative paths (common in some artifact layouts).
                # Fall back to direct discovery.
                pass

        if not kernels:
            for bsp in _discover_type13_kernels_direct():
                try:
                    kernels.append(SmallBodyKernel(bsp))
                except Exception:
                    pass
        yield kernels
    finally:
        for k in kernels:
            try:
                k.close()
            except Exception:
                pass


def _pick_representative_segment(kernels: list[SmallBodyKernel]) -> tuple[Any, int] | None:
    """Return (kernel, naif_id) for a Type 13 body we can benchmark."""
    for kernel in kernels:
        for seg in kernel._kernel.segments:
            if getattr(seg, "data_type", None) != 13:
                continue
            naif = seg.target
            if naif in PREFERRED_BODIES or len(str(naif)) >= 7:  # prefer numbered asteroids
                return kernel, naif
        # Fallback: first Type 13 we find
        for seg in kernel._kernel.segments:
            if getattr(seg, "data_type", None) == 13:
                return kernel, seg.target
    return None


def _sample_jds_in_coverage(kernel: SmallBodyKernel, naif: int, count: int) -> list[float]:
    cov = kernel.coverage()
    for (center, target), (start, end) in cov.items():
        if target == naif:
            margin = min(0.5, (end - start) * 0.01)
            lo = start + margin
            hi = end - margin
            step = (hi - lo) / max(1, count - 1)
            return [lo + i * step for i in range(count)]
    return [2451545.0 + i * 0.01 for i in range(count)]


def _time_native_vs_python(
    kernel: SmallBodyKernel,
    naif: int,
    jds: list[float],
) -> dict[str, float]:
    """Time the current path (whatever the flag says) vs explicitly forced Python."""
    # Current path (native if available and not forced)
    center = kernel.segment_center(naif)
    runs_native = []
    for _ in range(REPEATS):
        for _ in range(WARMUP):
            kernel.position(center, naif, jds[0])  # warm
        start = time.perf_counter()
        for jd in jds:
            kernel.position(center, naif, jd)
        runs_native.append(time.perf_counter() - start)

    # Force Python fallback path
    prev = _FORCE_PYTHON_TYPE13_FALLBACK
    try:
        import moira._spk_body_kernel as m
        m._FORCE_PYTHON_TYPE13_FALLBACK = True
        # Re-acquire segment caches by closing/reopening is heavy; instead we just time
        # a fresh loop (the flag is checked on every _load_native_evaluator call).
        runs_python = []
        for _ in range(REPEATS):
            start = time.perf_counter()
            for jd in jds:
                kernel.position(center, naif, jd)
            runs_python.append(time.perf_counter() - start)
    finally:
        import moira._spk_body_kernel as m
        m._FORCE_PYTHON_TYPE13_FALLBACK = prev

    return {
        "native_best_s": min(runs_native),
        "native_median_s": statistics.median(runs_native),
        "python_best_s": min(runs_python),
        "python_median_s": statistics.median(runs_python),
        "speedup_best": min(runs_python) / min(runs_native) if min(runs_native) > 0 else 0.0,
        "speedup_median": statistics.median(runs_python) / statistics.median(runs_native)
        if statistics.median(runs_native) > 0 else 0.0,
    }


def _micro_benchmark_hermite(
    kernel: SmallBodyKernel,
    naif: int,
    window_sizes: tuple[int, ...],
) -> dict[str, Any]:
    """Direct micro-benchmark of the Hermite math (bypasses higher-level overhead)."""
    seg = next((s for s in kernel._kernel.segments if s.target == naif and s.data_type == 13), None)
    if seg is None:
        return {"error": "no suitable segment"}

    # Force load the raw data once
    states, epochs_jd, ws = seg._data
    n = len(epochs_jd)
    if n < max(window_sizes) + 2:
        return {"error": "segment too short for microbench"}

    # Pick a point near the middle for stable windows
    t = epochs_jd[n // 2]
    t_sec = (t - 2451545.0) * 86400.0

    results = {}
    for ws in window_sizes:
        half = ws // 2
        start = max(0, min(n // 2 - half, n - ws))
        win_t = [(epochs_jd[start + i] - 2451545.0) * 86400.0 for i in range(ws)]
        pos = [axis[start : start + ws] for axis in states[:3]]
        vel = [axis[start : start + ws] for axis in states[3:]]

        # Python reference
        from moira._spk_body_kernel import _hermite_eval_3d, _hermite_eval_3d_with_derivative

        runs_py = []
        for _ in range(REPEATS):
            start_t = time.perf_counter()
            for _ in range(1000):
                _hermite_eval_3d(t_sec, win_t, pos, vel)
                _hermite_eval_3d_with_derivative(t_sec, win_t, pos, vel)
            runs_py.append(time.perf_counter() - start_t)

        # Native (via the evaluator the segment would use)
        evaluator = None
        try:
            evaluator = moira_native.load_spk_segment_evaluator(
                str(seg.path), int(seg.start_i), int(seg.end_i), bool(seg._little_endian), 13
            )
        except Exception:
            pass

        runs_native = []
        if evaluator is not None:
            for _ in range(REPEATS):
                start_t = time.perf_counter()
                for _ in range(1000):
                    evaluator.position(t, 0.0)
                    evaluator.position_and_velocity(t, 0.0)
                runs_native.append(time.perf_counter() - start_t)

        key = f"window_{ws}"
        results[key] = {
            "window_size": ws,
            "python_1000_calls_best_s": min(runs_py),
            "python_1000_calls_median_s": statistics.median(runs_py),
        }
        if runs_native:
            results[key]["native_1000_calls_best_s"] = min(runs_native)
            results[key]["native_1000_calls_median_s"] = statistics.median(runs_native)
            results[key]["speedup_best"] = min(runs_py) / min(runs_native)
            results[key]["speedup_median"] = statistics.median(runs_py) / statistics.median(runs_native)

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    manifest = _find_type13_manifest()
    if manifest is None:
        print("ERROR: No sovereign Type 13 manifest found. Cannot run Phase 3 benchmark.")
        sys.exit(1)

    print(f"Using manifest: {manifest}")
    print(f"Native backend: {getattr(moira_native, '__backend_file__', 'unknown')}")
    print(f"Force-Python flag at start: {_FORCE_PYTHON_TYPE13_FALLBACK}")

    results: dict[str, Any] = {
        "phase": "phase3_type13_native_evaluation",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "manifest": str(manifest),
        "native_backend": getattr(moira_native, "__backend_file__", None),
        "force_python_default": _FORCE_PYTHON_TYPE13_FALLBACK,
        "cases": [],
    }

    with _load_type13_kernels(manifest) as kernels:
        pick = _pick_representative_segment(kernels)
        if pick is None:
            print("ERROR: No Type 13 segments found in loaded kernels.")
            sys.exit(1)

        kernel, naif = pick
        print(f"Benchmarking NAIF {naif} on {kernel._path.name}")

        jds = _sample_jds_in_coverage(kernel, naif, POSITIONS_PER_RUN)

        # High-level repeated single-body workload (most relevant to asteroid_at)
        case = {
            "name": f"repeated_position_naif{naif}",
            "naif_id": naif,
            "kernel": str(kernel._path.name),
            "sample_count": len(jds),
            "repeats": REPEATS,
        }
        timings = _time_native_vs_python(kernel, naif, jds)
        case.update(timings)
        results["cases"].append(case)

        print(f"  Repeated position: native median {timings['native_median_s']:.4f}s vs "
              f"python {timings['python_median_s']:.4f}s "
              f"(~{timings['speedup_median']:.1f}x)")

        # Micro-benchmark of the actual Hermite math (isolates evaluation cost)
        micro = _micro_benchmark_hermite(kernel, naif, MICRO_WINDOW_SIZES)
        results["micro_hermite"] = micro

        if "error" not in micro:
            for ws_key, m in micro.items():
                if "speedup_median" in m:
                    print(f"  Micro window {m['window_size']}: ~{m['speedup_median']:.1f}x (native vs py)")

    # Write artifact
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nWrote artifact: {ARTIFACT}")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
