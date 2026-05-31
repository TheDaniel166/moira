"""
Measure native small-body workloads through the current sovereign reader path.

This script does not compare against the retired jplephem-backed reader path.
Its purpose is to establish explicit timings for representative native small-body
workloads across type-2 and type-13 kernels so Phase 2 measurement is no longer
implicit.
"""

from __future__ import annotations

import json
import statistics
import sys
import time
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from moira._kernel_paths import find_kernel, find_planetary_kernel
from moira._spk_body_kernel import SmallBodyKernel
from moira.asteroids import asteroid_at
from moira.comets import comet_at
from moira import moira_native
from moira.spk_reader import KernelPool, SpkReader

ARTIFACT = Path("tests/artifacts/benchmarks/native_phase2_small_bodies.json")
SAMPLE_COUNT = 5000
REPEATS = 7

REPRESENTATIVE_CASES = (
    ("raw_position_sb441_ceres", "sb441-n373s.bsp", 2000001, "raw_position"),
    ("raw_position_centaurs_chiron", "centaurs.bsp", 2002060, "raw_position"),
    ("raw_position_minor_bodies_pandora", "minor_bodies.bsp", 2000055, "raw_position"),
    ("public_asteroid_eros", "asteroids.bsp", "Eros", "public_asteroid"),
    ("public_comet_halley", "comets.bsp", "Halley", "public_comet"),
)


@contextmanager
def _reader_pool():
    readers = [SpkReader(find_planetary_kernel())]
    try:
        for kernel_name in ("sb441-n373s.bsp", "asteroids.bsp", "centaurs.bsp", "minor_bodies.bsp", "comets.bsp"):
            path = find_kernel(kernel_name)
            if path.exists():
                readers.append(SmallBodyKernel(path))
        pool = KernelPool(readers)
        yield pool
    finally:
        for reader in reversed(readers):
            try:
                reader.close()
            except Exception:
                pass


def _sample_jds(start_jd: float, end_jd: float, count: int) -> list[float]:
    margin = min(1.0, (end_jd - start_jd) / 1000.0)
    lo = start_jd + margin
    hi = end_jd - margin
    step = (hi - lo) / (count - 1)
    return [lo + i * step for i in range(count)]


def _measure_raw_position(path: Path, naif_id: int) -> dict[str, float | int | str]:
    kernel = SmallBodyKernel(path)
    try:
        coverage = kernel.coverage()
        key = next(pair for pair in coverage if pair[1] == naif_id)
        jds = _sample_jds(*coverage[key], SAMPLE_COUNT)
        runs = []
        for _ in range(REPEATS):
            start = time.perf_counter()
            center = kernel.segment_center(naif_id)
            for jd in jds:
                kernel.position(center, naif_id, jd)
            runs.append(time.perf_counter() - start)
        return {
            "kind": "raw_position",
            "naif_id": naif_id,
            "sample_count": SAMPLE_COUNT,
            "repeats": REPEATS,
            "best_seconds": min(runs),
            "median_seconds": statistics.median(runs),
        }
    finally:
        kernel.close()


def _measure_public_asteroid(body_name: str, reader) -> dict[str, float | int | str]:
    runs = []
    jds = [2451545.0 + i * 0.01 for i in range(SAMPLE_COUNT)]
    for _ in range(REPEATS):
        start = time.perf_counter()
        for jd in jds:
            asteroid_at(body_name, jd, reader=reader)
        runs.append(time.perf_counter() - start)
    return {
        "kind": "public_asteroid",
        "body": body_name,
        "sample_count": SAMPLE_COUNT,
        "repeats": REPEATS,
        "best_seconds": min(runs),
        "median_seconds": statistics.median(runs),
    }


def _measure_public_comet(body_name: str, reader) -> dict[str, float | int | str]:
    runs = []
    jds = [2451545.0 + i * 0.01 for i in range(SAMPLE_COUNT)]
    for _ in range(REPEATS):
        start = time.perf_counter()
        for jd in jds:
            comet_at(body_name, jd, reader=reader)
        runs.append(time.perf_counter() - start)
    return {
        "kind": "public_comet",
        "body": body_name,
        "sample_count": SAMPLE_COUNT,
        "repeats": REPEATS,
        "best_seconds": min(runs),
        "median_seconds": statistics.median(runs),
    }


def main() -> None:
    results = []
    with _reader_pool() as pool:
        for label, kernel_name, body_ref, kind in REPRESENTATIVE_CASES:
            if kind == "raw_position":
                path = find_kernel(kernel_name)
                if not path.exists():
                    continue
                metrics = _measure_raw_position(path, int(body_ref))
                metrics["name"] = label
                metrics["kernel"] = kernel_name
                results.append(metrics)
            elif kind == "public_asteroid":
                metrics = _measure_public_asteroid(str(body_ref), pool)
                metrics["name"] = label
                metrics["kernel"] = kernel_name
                results.append(metrics)
            elif kind == "public_comet":
                metrics = _measure_public_comet(str(body_ref), pool)
                metrics["name"] = label
                metrics["kernel"] = kernel_name
                results.append(metrics)

    payload = {
        "phase": "phase2_small_body_measurement",
        "planetary_kernel": str(find_planetary_kernel()),
        "native_backend": moira_native.__backend_file__,
        "results": results,
    }
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
