"""
Capture a granular bottleneck snapshot for the live planetary calculation flow.

This script records stage-by-stage timings for the current public planetary
pipeline under the repo `.venv` runtime. It is intentionally diagnostic rather
than comparative: the goal is to expose where time is spent along the flow as
it exists today, not to claim a speedup.
"""

from __future__ import annotations

import json
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import moira.planets as planets
from moira._kernel_paths import find_planetary_kernel
from moira.constants import Body
from moira import moira_native as _moira_native
from moira.spk_reader import SpkReader

ARTIFACT = Path("tests/artifacts/benchmarks/planetary_flow_bottleneck_snapshot.json")
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


@dataclass
class _Metric:
    calls: int = 0
    inclusive_ns: int = 0
    exclusive_ns: int = 0


class _StageProfiler:
    def __init__(self) -> None:
        self._metrics: dict[str, _Metric] = {}
        self._stack: list[dict[str, Any]] = []

    def wrap(self, name: str, fn: Callable[..., Any]) -> Callable[..., Any]:
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            start_ns = time.perf_counter_ns()
            frame = {"name": name, "start_ns": start_ns, "child_ns": 0}
            self._stack.append(frame)
            try:
                return fn(*args, **kwargs)
            finally:
                end_ns = time.perf_counter_ns()
                popped = self._stack.pop()
                elapsed_ns = end_ns - int(popped["start_ns"])
                child_ns = int(popped["child_ns"])
                metric = self._metrics.setdefault(name, _Metric())
                metric.calls += 1
                metric.inclusive_ns += elapsed_ns
                metric.exclusive_ns += elapsed_ns - child_ns
                if self._stack:
                    self._stack[-1]["child_ns"] += elapsed_ns

        wrapped.__name__ = getattr(fn, "__name__", name)
        wrapped.__doc__ = getattr(fn, "__doc__", None)
        return wrapped

    def snapshot(self, wall_seconds: float, *, stage_order: list[str]) -> dict[str, Any]:
        ranked = []
        for name, metric in sorted(
            self._metrics.items(),
            key=lambda item: item[1].inclusive_ns,
            reverse=True,
        ):
            inclusive_seconds = metric.inclusive_ns / 1_000_000_000
            exclusive_seconds = metric.exclusive_ns / 1_000_000_000
            ranked.append(
                {
                    "name": name,
                    "calls": metric.calls,
                    "inclusive_seconds": inclusive_seconds,
                    "exclusive_seconds": exclusive_seconds,
                    "avg_inclusive_ms": (inclusive_seconds * 1000.0) / metric.calls,
                    "avg_exclusive_ms": (exclusive_seconds * 1000.0) / metric.calls,
                    "share_of_wall_percent": (inclusive_seconds / wall_seconds) * 100.0 if wall_seconds else 0.0,
                }
            )

        ordered_lookup = {entry["name"]: entry for entry in ranked}
        ordered = [ordered_lookup[name] for name in stage_order if name in ordered_lookup]
        return {
            "wall_seconds": wall_seconds,
            "ranked_stages": ranked,
            "ordered_stages": ordered,
        }


@dataclass
class _PatchTarget:
    obj: Any
    attr: str
    label: str


@contextmanager
def _instrument(targets: list[_PatchTarget]) -> Any:
    profiler = _StageProfiler()
    originals: list[tuple[Any, str, Any]] = []
    for target in targets:
        original = getattr(target.obj, target.attr)
        originals.append((target.obj, target.attr, original))
        setattr(target.obj, target.attr, profiler.wrap(target.label, original))
    try:
        yield profiler
    finally:
        for obj, attr, original in reversed(originals):
            setattr(obj, attr, original)


def _sample_jds(reader: SpkReader, count: int) -> list[float]:
    start_jd, end_jd = reader.epoch_range(0, 10)
    margin = min(30.0, (end_jd - start_jd) / 1000.0)
    lo = start_jd + margin
    hi = end_jd - margin
    if hi <= lo:
        raise RuntimeError("Insufficient Sun coverage span for planetary bottleneck snapshot")
    step = (hi - lo) / (count - 1)
    return [lo + i * step for i in range(count)]


def _planet_at_workload(reader: SpkReader, jds: list[float]) -> None:
    for jd_ut in jds:
        for body in BODIES:
            planets.planet_at(body, jd_ut, reader=reader)


def _all_planets_workload(reader: SpkReader, jds: list[float]) -> None:
    for jd_ut in jds:
        planets.all_planets_at(jd_ut, bodies=BODIES, reader=reader)


def _patch_targets() -> tuple[list[_PatchTarget], list[str]]:
    targets = [
        _PatchTarget(planets, "planet_at", "planet_at"),
        _PatchTarget(planets, "all_planets_at", "all_planets_at"),
        _PatchTarget(planets, "_native_all_planets_admitted", "_native_all_planets_admitted"),
        _PatchTarget(planets, "_build_apparent_context", "_build_apparent_context"),
        _PatchTarget(planets, "_planet_at_core", "_planet_at_core"),
        _PatchTarget(planets, "_npe_public_route_segment_specs", "_npe_public_route_segment_specs"),
        _PatchTarget(planets, "_npe_body_route_segment_specs", "_npe_body_route_segment_specs"),
        _PatchTarget(planets, "_prefill_npe_public_vector_cache", "_prefill_npe_public_vector_cache"),
        _PatchTarget(planets, "_npe_batch_barycentric_positions", "_npe_batch_barycentric_positions"),
        _PatchTarget(planets, "_barycentric", "_barycentric"),
        _PatchTarget(planets, "_barycentric_state", "_barycentric_state"),
        _PatchTarget(planets, "_earth_barycentric", "_earth_barycentric"),
        _PatchTarget(planets, "_earth_barycentric_state", "_earth_barycentric_state"),
        _PatchTarget(planets, "_geocentric", "_geocentric"),
        _PatchTarget(planets, "_geocentric_state", "_geocentric_state"),
        _PatchTarget(planets, "_deflectors_for_body", "_deflectors_for_body"),
        _PatchTarget(planets, "_compose_rotation_matrix", "_compose_rotation_matrix"),
        _PatchTarget(planets, "_apply_rotation_matrix", "_apply_rotation_matrix"),
        _PatchTarget(planets, "_longitude_rate", "_longitude_rate"),
        _PatchTarget(planets, "_nutation", "_nutation"),
        _PatchTarget(planets, "mean_obliquity", "mean_obliquity"),
        _PatchTarget(planets, "ut_to_tt", "ut_to_tt"),
        _PatchTarget(planets, "decimal_year", "decimal_year"),
        _PatchTarget(planets, "local_sidereal_time", "local_sidereal_time"),
        _PatchTarget(planets, "precession_matrix_equatorial", "precession_matrix_equatorial"),
        _PatchTarget(planets, "nutation_matrix_equatorial", "nutation_matrix_equatorial"),
        _PatchTarget(planets, "apply_light_time", "apply_light_time"),
        _PatchTarget(planets, "apply_aberration", "apply_aberration"),
        _PatchTarget(planets, "apply_deflection", "apply_deflection"),
        _PatchTarget(planets, "apply_frame_bias", "apply_frame_bias"),
        _PatchTarget(planets, "topocentric_correction", "topocentric_correction"),
        _PatchTarget(planets, "apply_diurnal_aberration", "apply_diurnal_aberration"),
        _PatchTarget(planets, "apply_refraction", "apply_refraction"),
        _PatchTarget(planets, "icrf_to_ecliptic", "icrf_to_ecliptic"),
        _PatchTarget(planets, "icrf_to_equatorial", "icrf_to_equatorial"),
        _PatchTarget(planets, "equatorial_to_horizontal", "equatorial_to_horizontal"),
        _PatchTarget(SpkReader, "position", "SpkReader.position"),
        _PatchTarget(SpkReader, "position_and_velocity", "SpkReader.position_and_velocity"),
        _PatchTarget(_moira_native.NativeSpkKernelHandle, "segment_position", "NativeSpkKernelHandle.segment_position"),
        _PatchTarget(
            _moira_native.NativeSpkKernelHandle,
            "segment_position_and_velocity",
            "NativeSpkKernelHandle.segment_position_and_velocity",
        ),
        _PatchTarget(
            _moira_native.NativeSpkKernelHandle,
            "load_segment_evaluator",
            "NativeSpkKernelHandle.load_segment_evaluator",
        ),
        _PatchTarget(
            _moira_native.NativeSpkKernelHandle,
            "batch_segment_position_and_velocity",
            "NativeSpkKernelHandle.batch_segment_position_and_velocity",
        ),
        _PatchTarget(
            _moira_native.NativeSpkKernelHandle,
            "batch_segment_position_requests",
            "NativeSpkKernelHandle.batch_segment_position_requests",
        ),
    ]
    stage_order = [target.label for target in targets]
    return targets, stage_order


def _profile_warm_scenario(
    name: str,
    kernel_path: Path,
    workload: Callable[[SpkReader, list[float]], None],
    jds: list[float],
    stage_order: list[str],
) -> dict[str, Any]:
    with SpkReader(kernel_path) as reader:
        workload(reader, jds)
        targets, _ = _patch_targets()
        with _instrument(targets) as profiler:
            start = time.perf_counter()
            workload(reader, jds)
            wall_seconds = time.perf_counter() - start
    payload = profiler.snapshot(wall_seconds, stage_order=stage_order)
    payload["name"] = name
    payload["reader_mode"] = "warm"
    return payload


def _profile_cold_scenario(
    name: str,
    kernel_path: Path,
    workload: Callable[[SpkReader, list[float]], None],
    jds: list[float],
    stage_order: list[str],
) -> dict[str, Any]:
    open_start = time.perf_counter()
    with SpkReader(kernel_path) as reader:
        reader_open_seconds = time.perf_counter() - open_start
        targets, _ = _patch_targets()
        with _instrument(targets) as profiler:
            start = time.perf_counter()
            workload(reader, jds)
            call_wall_seconds = time.perf_counter() - start
    payload = profiler.snapshot(call_wall_seconds, stage_order=stage_order)
    payload["name"] = name
    payload["reader_mode"] = "cold"
    payload["reader_open_seconds"] = reader_open_seconds
    payload["total_wall_seconds_including_open"] = reader_open_seconds + call_wall_seconds
    return payload


def _profile_single_body(
    name: str,
    kernel_path: Path,
    body: str,
    jd_ut: float,
    stage_order: list[str],
) -> dict[str, Any]:
    with SpkReader(kernel_path) as reader:
        planets.planet_at(body, jd_ut, reader=reader)
        targets, _ = _patch_targets()
        with _instrument(targets) as profiler:
            start = time.perf_counter()
            planets.planet_at(body, jd_ut, reader=reader)
            wall_seconds = time.perf_counter() - start
    payload = profiler.snapshot(wall_seconds, stage_order=stage_order)
    payload["name"] = name
    payload["reader_mode"] = "warm"
    payload["body"] = body
    payload["jd_ut"] = jd_ut
    return payload


def _profile_single_all_planets(
    name: str,
    kernel_path: Path,
    jd_ut: float,
    stage_order: list[str],
) -> dict[str, Any]:
    with SpkReader(kernel_path) as reader:
        planets.all_planets_at(jd_ut, bodies=BODIES, reader=reader)
        targets, _ = _patch_targets()
        with _instrument(targets) as profiler:
            start = time.perf_counter()
            planets.all_planets_at(jd_ut, bodies=BODIES, reader=reader)
            wall_seconds = time.perf_counter() - start
    payload = profiler.snapshot(wall_seconds, stage_order=stage_order)
    payload["name"] = name
    payload["reader_mode"] = "warm"
    payload["jd_ut"] = jd_ut
    payload["body_count"] = len(BODIES)
    return payload


def main() -> None:
    kernel_path = find_planetary_kernel()
    if kernel_path is None:
        raise RuntimeError("No planetary kernel found for bottleneck snapshot")

    targets, stage_order = _patch_targets()
    _ = targets  # The list itself is recreated per profiling context.

    with SpkReader(kernel_path) as reader:
        jds = _sample_jds(reader, SAMPLE_DATES)
    representative_jd = jds[len(jds) // 2]

    scenarios = [
        _profile_single_body(
            "planet_at_single_mars_default_warm",
            kernel_path,
            Body.MARS,
            representative_jd,
            stage_order,
        ),
        _profile_single_body(
            "planet_at_single_moon_default_warm",
            kernel_path,
            Body.MOON,
            representative_jd,
            stage_order,
        ),
        _profile_single_all_planets(
            "all_planets_at_single_default_warm",
            kernel_path,
            representative_jd,
            stage_order,
        ),
        _profile_warm_scenario(
            "planet_at_default_workload_warm_reader",
            kernel_path,
            _planet_at_workload,
            jds,
            stage_order,
        ),
        _profile_warm_scenario(
            "all_planets_at_default_workload_warm_reader",
            kernel_path,
            _all_planets_workload,
            jds,
            stage_order,
        ),
        _profile_cold_scenario(
            "planet_at_default_workload_cold_reader",
            kernel_path,
            _planet_at_workload,
            jds,
            stage_order,
        ),
        _profile_cold_scenario(
            "all_planets_at_default_workload_cold_reader",
            kernel_path,
            _all_planets_workload,
            jds,
            stage_order,
        ),
    ]

    payload = {
        "phase": "planetary_flow_bottleneck_snapshot",
        "kernel": str(kernel_path),
        "body_set": list(BODIES),
        "jd_count": SAMPLE_DATES,
        "representative_jd_ut": representative_jd,
        "scenarios": scenarios,
    }

    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
