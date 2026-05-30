import json
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from moira.julian import (
    apparent_sidereal_time as dispatched_apparent_sidereal_time,
    earth_rotation_angle as dispatched_earth_rotation_angle,
    greenwich_mean_sidereal_time as dispatched_greenwich_mean_sidereal_time,
)
from moira.moira_native import (
    apparent_sidereal_time as native_apparent_sidereal_time,
    earth_rotation_angle as native_earth_rotation_angle,
    greenwich_mean_sidereal_time as native_greenwich_mean_sidereal_time,
)


@dataclass(frozen=True)
class FunctionBenchmark:
    name: str
    sample_count: int
    repeats: int
    python_best_seconds: float
    native_best_seconds: float
    python_median_seconds: float
    native_median_seconds: float
    speedup_best: float
    speedup_median: float


@dataclass(frozen=True)
class BenchmarkSummary:
    sample_count: int
    repeats: int
    python_total_best_seconds: float
    native_total_best_seconds: float
    python_total_median_seconds: float
    native_total_median_seconds: float
    speedup_best: float
    speedup_median: float


def _build_sidereal_samples(sample_count: int) -> tuple[list[float], list[tuple[float, float, float]]]:
    jd_values = []
    gast_values = []

    for i in range(sample_count):
        jd_ut = (i * 48271.0) % 5_000_000.0
        dpsi = ((i * 104729) % 2000000) / 1_000_000.0 - 1.0
        obliquity = 20.0 + (((i * 130363) % 5000000) / 1_000_000.0)
        jd_values.append(jd_ut)
        gast_values.append((jd_ut, dpsi, obliquity))

    return jd_values, gast_values


def _time_call(fn, payload, repeats: int, tuple_payload: bool = False) -> list[float]:
    durations: list[float] = []

    for _ in range(repeats):
        start = time.perf_counter()
        if tuple_payload:
            for item in payload:
                fn(*item)
        else:
            for item in payload:
                fn(item)
        durations.append(time.perf_counter() - start)

    return durations


def _summarize(name: str, sample_count: int, repeats: int, py_times: list[float], native_times: list[float]) -> FunctionBenchmark:
    python_best = min(py_times)
    native_best = min(native_times)
    python_median = statistics.median(py_times)
    native_median = statistics.median(native_times)

    return FunctionBenchmark(
        name=name,
        sample_count=sample_count,
        repeats=repeats,
        python_best_seconds=python_best,
        native_best_seconds=native_best,
        python_median_seconds=python_median,
        native_median_seconds=native_median,
        speedup_best=python_best / native_best,
        speedup_median=python_median / native_median,
    )


def main() -> int:
    artifact_dir = _ROOT / "tests" / "artifacts" / "benchmarks"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / "native_phase1_sidereal.json"

    sample_count = 200_000
    repeats = 7
    jd_values, gast_values = _build_sidereal_samples(sample_count)

    py_earth_rotation_angle = dispatched_earth_rotation_angle.__wrapped__
    py_greenwich_mean_sidereal_time = dispatched_greenwich_mean_sidereal_time.__wrapped__
    py_apparent_sidereal_time = dispatched_apparent_sidereal_time.__wrapped__

    # Warm-up
    _time_call(py_earth_rotation_angle, jd_values[:1000], repeats=1)
    _time_call(native_earth_rotation_angle, jd_values[:1000], repeats=1)
    _time_call(py_greenwich_mean_sidereal_time, jd_values[:1000], repeats=1)
    _time_call(native_greenwich_mean_sidereal_time, jd_values[:1000], repeats=1)
    _time_call(py_apparent_sidereal_time, gast_values[:1000], repeats=1, tuple_payload=True)
    _time_call(native_apparent_sidereal_time, gast_values[:1000], repeats=1, tuple_payload=True)

    era_benchmark = _summarize(
        "earth_rotation_angle",
        sample_count,
        repeats,
        _time_call(py_earth_rotation_angle, jd_values, repeats=repeats),
        _time_call(native_earth_rotation_angle, jd_values, repeats=repeats),
    )
    gmst_benchmark = _summarize(
        "greenwich_mean_sidereal_time",
        sample_count,
        repeats,
        _time_call(py_greenwich_mean_sidereal_time, jd_values, repeats=repeats),
        _time_call(native_greenwich_mean_sidereal_time, jd_values, repeats=repeats),
    )
    gast_benchmark = _summarize(
        "apparent_sidereal_time",
        sample_count,
        repeats,
        _time_call(py_apparent_sidereal_time, gast_values, repeats=repeats, tuple_payload=True),
        _time_call(native_apparent_sidereal_time, gast_values, repeats=repeats, tuple_payload=True),
    )

    python_total_best = (
        era_benchmark.python_best_seconds
        + gmst_benchmark.python_best_seconds
        + gast_benchmark.python_best_seconds
    )
    native_total_best = (
        era_benchmark.native_best_seconds
        + gmst_benchmark.native_best_seconds
        + gast_benchmark.native_best_seconds
    )
    python_total_median = (
        era_benchmark.python_median_seconds
        + gmst_benchmark.python_median_seconds
        + gast_benchmark.python_median_seconds
    )
    native_total_median = (
        era_benchmark.native_median_seconds
        + gmst_benchmark.native_median_seconds
        + gast_benchmark.native_median_seconds
    )

    summary = BenchmarkSummary(
        sample_count=sample_count,
        repeats=repeats,
        python_total_best_seconds=python_total_best,
        native_total_best_seconds=native_total_best,
        python_total_median_seconds=python_total_median,
        native_total_median_seconds=native_total_median,
        speedup_best=python_total_best / native_total_best,
        speedup_median=python_total_median / native_total_median,
    )

    payload = {
        "phase": "phase1_sidereal",
        "functions": [
            asdict(era_benchmark),
            asdict(gmst_benchmark),
            asdict(gast_benchmark),
        ],
        "summary": asdict(summary),
    }
    artifact_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print("Phase 1 sidereal benchmark")
    print(f"Artifact: {artifact_path}")
    for benchmark in (era_benchmark, gmst_benchmark, gast_benchmark):
        print(
            f"{benchmark.name}: "
            f"python median={benchmark.python_median_seconds:.6f}s, "
            f"native median={benchmark.native_median_seconds:.6f}s, "
            f"median speedup={benchmark.speedup_median:.2f}x"
        )
    print(
        "overall: "
        f"python median={summary.python_total_median_seconds:.6f}s, "
        f"native median={summary.native_total_median_seconds:.6f}s, "
        f"median speedup={summary.speedup_median:.2f}x"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
