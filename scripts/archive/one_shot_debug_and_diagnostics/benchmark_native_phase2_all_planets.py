"""
Benchmark the public Phase 2 `all_planets_at(...)` chart-style workload.

This measures the canonical multi-body planetary product rather than raw
reader helpers, comparing the admitted native planetary evaluator against the
forced Python fallback route on the same public surface under cold-reader and
warm-reader conditions.
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

import moira.spk_reader as spk_reader
import moira.planets as planets_module
from moira._kernel_paths import find_planetary_kernel
from moira.constants import Body
from moira.planets import all_planets_at
from moira.spk_reader import SpkReader

ARTIFACT = Path("tests/artifacts/benchmarks/native_phase2_all_planets.json")
REPEATS = 7
SAMPLE_DATES = 24
BODIES = [
    Body.SUN,
    Body.MOON,
    Body.MERCURY,
    Body.VENUS,
    Body.MARS,
    Body.JUPITER,
    Body.SATURN,
    Body.URANUS,
    Body.NEPTUNE,
    Body.PLUTO,
]


@contextmanager
def _native_planetary_evaluator(enabled: bool):
    original = planets_module._get_native_planetary_evaluator
    if not enabled:
        planets_module._get_native_planetary_evaluator = lambda reader: None
    try:
        yield
    finally:
        planets_module._get_native_planetary_evaluator = original


def _sample_jds(reader: SpkReader, count: int) -> list[float]:
    start_jd, end_jd = reader.epoch_range(0, 10)
    margin = min(30.0, (end_jd - start_jd) / 1000.0)
    lo = start_jd + margin
    hi = end_jd - margin
    if hi <= lo:
        raise RuntimeError("Insufficient Sun coverage span for all_planets_at benchmark")
    step = (hi - lo) / (count - 1)
    return [lo + i * step for i in range(count)]


def _call_cases(reader: SpkReader, jds: list[float]) -> None:
    for jd_ut in jds:
        all_planets_at(jd_ut, bodies=BODIES, reader=reader)


def _measure_cold(kernel_path: Path, jds: list[float], native_enabled: bool) -> float:
    with _native_planetary_evaluator(native_enabled):
        start = time.perf_counter()
        with SpkReader(kernel_path) as reader:
            _call_cases(reader, jds)
        return time.perf_counter() - start


def _measure_warm(kernel_path: Path, jds: list[float], native_enabled: bool) -> float:
    with _native_planetary_evaluator(native_enabled):
        with SpkReader(kernel_path) as reader:
            _call_cases(reader, jds)
            start = time.perf_counter()
            _call_cases(reader, jds)
            return time.perf_counter() - start


def _summarize(name: str, python_runs: list[float], native_runs: list[float]) -> dict[str, float | int | str]:
    python_best = min(python_runs)
    native_best = min(native_runs)
    python_median = statistics.median(python_runs)
    native_median = statistics.median(native_runs)
    return {
        "name": name,
        "repeat_count": REPEATS,
        "body_count": len(BODIES),
        "jd_count": SAMPLE_DATES,
        "calls_per_run": SAMPLE_DATES,
        "bodies_per_call": len(BODIES),
        "python_best_seconds": python_best,
        "native_best_seconds": native_best,
        "python_median_seconds": python_median,
        "native_median_seconds": native_median,
        "speedup_best": python_best / native_best,
        "speedup_median": python_median / native_median,
    }


def main() -> None:
    if (
        planets_module._moira_native is None
        or not hasattr(planets_module._moira_native, "NativePlanetaryEvaluator")
    ):
        raise RuntimeError("Native planetary evaluator is not available in moira.moira_native")

    kernel_path = find_planetary_kernel()
    with SpkReader(kernel_path) as reader:
        jds = _sample_jds(reader, SAMPLE_DATES)

    cold_python_runs: list[float] = []
    cold_native_runs: list[float] = []
    warm_python_runs: list[float] = []
    warm_native_runs: list[float] = []

    for _ in range(REPEATS):
        cold_python_runs.append(_measure_cold(kernel_path, jds, False))
        cold_native_runs.append(_measure_cold(kernel_path, jds, True))
        warm_python_runs.append(_measure_warm(kernel_path, jds, False))
        warm_native_runs.append(_measure_warm(kernel_path, jds, True))

    functions = [
        _summarize("all_planets_at_default_cold_reader", cold_python_runs, cold_native_runs),
        _summarize("all_planets_at_default_warm_reader", warm_python_runs, warm_native_runs),
    ]

    summary = {
        "python_total_best_seconds": sum(item["python_best_seconds"] for item in functions),
        "native_total_best_seconds": sum(item["native_best_seconds"] for item in functions),
        "python_total_median_seconds": sum(item["python_median_seconds"] for item in functions),
        "native_total_median_seconds": sum(item["native_median_seconds"] for item in functions),
    }
    summary["speedup_best"] = summary["python_total_best_seconds"] / summary["native_total_best_seconds"]
    summary["speedup_median"] = summary["python_total_median_seconds"] / summary["native_total_median_seconds"]

    payload = {
        "phase": "phase2_all_planets_public_surface_native_evaluator",
        "kernel": str(kernel_path),
        "bodies": BODIES,
        "jd_count": SAMPLE_DATES,
        "comparison": "native planetary evaluator vs forced Python fallback on the admitted public route",
        "functions": functions,
        "summary": summary,
    }

    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
