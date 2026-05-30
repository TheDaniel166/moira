"""
Benchmark the first native Phase 2 ephemeris slice.

Compares the existing jplephem segment evaluation path against the new native
Chebyshev-record evaluator while preserving the same Python reader and segment
selection logic.
"""

from __future__ import annotations

import json
import sys
import statistics
import time
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import moira.spk_reader as spk_reader
from moira._kernel_paths import find_planetary_kernel
from moira.spk_reader import SpkReader

ARTIFACT = Path("tests/artifacts/benchmarks/native_phase2_ephemeris.json")
SAMPLE_COUNT = 20000
REPEATS = 7


@contextmanager
def _native_ephemeris(enabled: bool):
    original = spk_reader._HAS_NATIVE_SPK
    spk_reader._HAS_NATIVE_SPK = enabled
    try:
        yield
    finally:
        spk_reader._HAS_NATIVE_SPK = original


def _sample_jds(reader: SpkReader, center: int, target: int, count: int) -> list[float]:
    start_jd, end_jd = reader.epoch_range(center, target)
    margin = min(1.0, (end_jd - start_jd) / 1000.0)
    lo = start_jd + margin
    hi = end_jd - margin
    if hi <= lo:
        raise RuntimeError(f"Insufficient coverage span for ({center}, {target})")
    step = (hi - lo) / (count - 1)
    return [lo + i * step for i in range(count)]


def _bench_position(reader: SpkReader, jds: list[float], center: int, target: int) -> float:
    start = time.perf_counter()
    for jd in jds:
        reader.position(center, target, jd)
    return time.perf_counter() - start


def _bench_state(reader: SpkReader, jds: list[float], center: int, target: int) -> float:
    start = time.perf_counter()
    for jd in jds:
        reader.position_and_velocity(center, target, jd)
    return time.perf_counter() - start


def _measure(label: str, fn, reader: SpkReader, jds: list[float], center: int, target: int) -> dict[str, float | int | str]:
    python_runs: list[float] = []
    native_runs: list[float] = []

    for _ in range(REPEATS):
        with _native_ephemeris(False):
            python_runs.append(fn(reader, jds, center, target))
        with _native_ephemeris(True):
            native_runs.append(fn(reader, jds, center, target))

    python_best = min(python_runs)
    native_best = min(native_runs)
    python_median = statistics.median(python_runs)
    native_median = statistics.median(native_runs)

    return {
        "name": label,
        "center": center,
        "target": target,
        "sample_count": len(jds),
        "repeats": REPEATS,
        "python_best_seconds": python_best,
        "native_best_seconds": native_best,
        "python_median_seconds": python_median,
        "native_median_seconds": native_median,
        "speedup_best": python_best / native_best,
        "speedup_median": python_median / native_median,
    }


def main() -> None:
    if not spk_reader._HAS_NATIVE_SPK:
        raise RuntimeError("Native SPK evaluator is not available in moira.moira_native")

    kernel_path = find_planetary_kernel()
    with SpkReader(kernel_path) as reader:
        position_jds = _sample_jds(reader, 0, 10, SAMPLE_COUNT)
        state_jds = _sample_jds(reader, 0, 3, SAMPLE_COUNT)

        results = [
            _measure("position_sun_barycenter", _bench_position, reader, position_jds, 0, 10),
            _measure("state_emb_barycenter", _bench_state, reader, state_jds, 0, 3),
        ]

    summary = {
        "sample_count": SAMPLE_COUNT,
        "repeats": REPEATS,
        "python_total_best_seconds": sum(item["python_best_seconds"] for item in results),
        "native_total_best_seconds": sum(item["native_best_seconds"] for item in results),
        "python_total_median_seconds": sum(item["python_median_seconds"] for item in results),
        "native_total_median_seconds": sum(item["native_median_seconds"] for item in results),
    }
    summary["speedup_best"] = summary["python_total_best_seconds"] / summary["native_total_best_seconds"]
    summary["speedup_median"] = summary["python_total_median_seconds"] / summary["native_total_median_seconds"]

    payload = {
        "phase": "phase2_ephemeris_slice1",
        "kernel": str(kernel_path),
        "functions": results,
        "summary": summary,
    }

    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
