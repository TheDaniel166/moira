"""
Low-overhead stage timing snapshot for the live planetary calculation flow.

Unlike the wrapper-heavy bottleneck profiler, this script measures the main
planetary stages by direct workload replay. The intent is to preserve the real
execution shape of the post-native hot path while still exposing where time is
spent.
"""

from __future__ import annotations

import json
import os
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from moira._kernel_paths import find_planetary_kernel
from moira.constants import Body
from moira.julian import decimal_year
from moira.planets import (
    _apply_rotation_matrix,
    _build_apparent_context,
    _deflectors_for_body,
    _earth_barycentric_state,
    _geocentric_state,
    _longitude_rate,
    _planet_at_core,
    all_planets_at,
    planet_at,
)
from moira.corrections import (
    apply_aberration,
    apply_deflection,
    apply_frame_bias,
    apply_light_time,
)
from moira.coordinates import icrf_to_ecliptic
from moira.obliquity import nutation as _nutation
from moira.spk_reader import SpkReader

ARTIFACT = Path(
    os.getenv(
        "MOIRA_STAGE_TIMING_ARTIFACT",
        "tests/artifacts/benchmarks/planetary_flow_stage_timing.json",
    )
)
SAMPLE_DATES = 24
REPEATS = 7
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
DEFLECTED_BODIES = [
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
class StageResult:
    name: str
    calls: int
    median_seconds: float
    best_seconds: float

    def as_dict(self, reference_wall: float | None = None) -> dict[str, float | int | str]:
        payload = {
            "name": self.name,
            "calls": self.calls,
            "median_seconds": self.median_seconds,
            "best_seconds": self.best_seconds,
            "avg_median_ms": (self.median_seconds * 1000.0) / self.calls if self.calls else 0.0,
            "avg_best_ms": (self.best_seconds * 1000.0) / self.calls if self.calls else 0.0,
        }
        if reference_wall:
            payload["share_of_reference_percent"] = (self.median_seconds / reference_wall) * 100.0
        return payload


def _sample_jds(reader: SpkReader, count: int) -> list[float]:
    start_jd, end_jd = reader.epoch_range(0, 10)
    margin = min(30.0, (end_jd - start_jd) / 1000.0)
    lo = start_jd + margin
    hi = end_jd - margin
    if hi <= lo:
        raise RuntimeError("Insufficient Sun coverage span for stage timing snapshot")
    step = (hi - lo) / (count - 1)
    return [lo + i * step for i in range(count)]


def _median(values: list[float]) -> float:
    return statistics.median(values)


def _measure(fn, repeats: int = REPEATS) -> tuple[float, float]:
    runs: list[float] = []
    for _ in range(repeats):
        start = time.perf_counter()
        fn()
        runs.append(time.perf_counter() - start)
    return _median(runs), min(runs)


def _prepare_work_items(reader: SpkReader, jds: list[float]) -> tuple[list[tuple[float, float]], list[tuple[str, float]], list[tuple[str, float, float]]]:
    jd_pairs: list[tuple[float, float]] = []
    body_jd_pairs: list[tuple[str, float]] = []
    body_jdtt_pairs: list[tuple[str, float, float]] = []

    for jd_ut in jds:
        year, month, *_ = planet_at.__globals__["_approx_year"](jd_ut)
        jd_tt = planet_at.__globals__["ut_to_tt"](jd_ut, decimal_year(year, month))
        jd_pairs.append((jd_ut, jd_tt))
        for body in BODIES:
            body_jd_pairs.append((body, jd_ut))
            body_jdtt_pairs.append((body, jd_ut, jd_tt))
    return jd_pairs, body_jd_pairs, body_jdtt_pairs


def main() -> None:
    kernel_path = find_planetary_kernel()
    if kernel_path is None:
        raise RuntimeError("No planetary kernel found for stage timing snapshot")

    with SpkReader(kernel_path) as reader:
        jds = _sample_jds(reader, SAMPLE_DATES)
        jd_pairs, body_jd_pairs, body_jdtt_pairs = _prepare_work_items(reader, jds)

        # Warm the normal public surfaces and gather shared contexts.
        for body, jd_ut in body_jd_pairs:
            planet_at(body, jd_ut, reader=reader)
        for jd_ut in jds:
            all_planets_at(jd_ut, bodies=BODIES, reader=reader)

        contexts = []
        for jd_ut, jd_tt in jd_pairs:
            context = _build_apparent_context(jd_tt, reader, apparent=True, nutation=True, vector_cache={})
            contexts.append((jd_ut, jd_tt, context))

        all_work = [(body, jd_ut, jd_tt, context) for jd_ut, jd_tt, context in contexts for body in BODIES]
        deflected_work = [(body, jd_tt, context) for jd_ut, jd_tt, context in contexts for body in DEFLECTED_BODIES]
        geostate_work = [(body, jd_tt, context.vector_cache) for jd_ut, jd_tt, context in contexts for body in BODIES]
        context_by_jd = {jd_tt: context for _jd_ut, jd_tt, context in contexts}

        def measure_public_planet_at() -> None:
            for body, jd_ut in body_jd_pairs:
                planet_at(body, jd_ut, reader=reader)

        def measure_public_all_planets() -> None:
            for jd_ut in jds:
                all_planets_at(jd_ut, bodies=BODIES, reader=reader)

        def measure_ut_to_tt() -> None:
            for jd_ut, _jd_tt in jd_pairs:
                year, month, *_ = planet_at.__globals__["_approx_year"](jd_ut)
                planet_at.__globals__["ut_to_tt"](jd_ut, decimal_year(year, month))

        def measure_build_context() -> None:
            for _jd_ut, jd_tt in jd_pairs:
                _build_apparent_context(jd_tt, reader, apparent=True, nutation=True, vector_cache={})

        def measure_nutation_only() -> None:
            for _jd_ut, jd_tt in jd_pairs:
                _nutation(jd_tt)

        def measure_earth_barycentric_state() -> None:
            for _jd_ut, jd_tt, context in contexts:
                _earth_barycentric_state(jd_tt, reader, context.vector_cache)

        def measure_light_time() -> None:
            for body, _jd_ut, jd_tt, context in all_work:
                apply_light_time(
                    body,
                    jd_tt,
                    reader,
                    context.earth_ssb,
                    lambda body_, jd_tt_, reader_: planet_at.__globals__["_barycentric"](
                        body_, jd_tt_, reader_, context.vector_cache
                    ),
                )

        def measure_deflection() -> None:
            for body, jd_tt, context in deflected_work:
                xyz_geo, _ = apply_light_time(
                    body,
                    jd_tt,
                    reader,
                    context.earth_ssb,
                    lambda body_, jd_tt_, reader_: planet_at.__globals__["_barycentric"](
                        body_, jd_tt_, reader_, context.vector_cache
                    ),
                )
                apply_deflection(xyz_geo, _deflectors_for_body(body, jd_tt, reader, context))

        def measure_aberration() -> None:
            for body, _jd_ut, jd_tt, context in all_work:
                xyz_geo, _ = apply_light_time(
                    body,
                    jd_tt,
                    reader,
                    context.earth_ssb,
                    lambda body_, jd_tt_, reader_: planet_at.__globals__["_barycentric"](
                        body_, jd_tt_, reader_, context.vector_cache
                    ),
                )
                apply_aberration(xyz_geo, context.earth_vel)

        def measure_frame_bias() -> None:
            for body, _jd_ut, jd_tt, context in all_work:
                xyz_geo, _ = apply_light_time(
                    body,
                    jd_tt,
                    reader,
                    context.earth_ssb,
                    lambda body_, jd_tt_, reader_: planet_at.__globals__["_barycentric"](
                        body_, jd_tt_, reader_, context.vector_cache
                    ),
                )
                apply_frame_bias(xyz_geo)

        def measure_rotation_apply() -> None:
            for body, _jd_ut, jd_tt, context in all_work:
                xyz_geo, _ = apply_light_time(
                    body,
                    jd_tt,
                    reader,
                    context.earth_ssb,
                    lambda body_, jd_tt_, reader_: planet_at.__globals__["_barycentric"](
                        body_, jd_tt_, reader_, context.vector_cache
                    ),
                )
                xyz_geo = apply_frame_bias(xyz_geo)
                _apply_rotation_matrix(context.rot_mat, xyz_geo)

        def measure_icrf_to_ecliptic() -> None:
            for body, _jd_ut, jd_tt, context in all_work:
                xyz_geo, _ = apply_light_time(
                    body,
                    jd_tt,
                    reader,
                    context.earth_ssb,
                    lambda body_, jd_tt_, reader_: planet_at.__globals__["_barycentric"](
                        body_, jd_tt_, reader_, context.vector_cache
                    ),
                )
                xyz_geo = apply_frame_bias(xyz_geo)
                xyz_geo = _apply_rotation_matrix(context.rot_mat, xyz_geo)
                icrf_to_ecliptic(xyz_geo, context.obliquity)

        def measure_geocentric_state() -> None:
            for body, jd_tt, cache in geostate_work:
                _geocentric_state(body, jd_tt, reader, cache)

        def measure_longitude_rate() -> None:
            for body, jd_tt, cache in geostate_work:
                xyz_rate, vel_rate = _geocentric_state(body, jd_tt, reader, cache)
                context = context_by_jd[jd_tt]
                _longitude_rate(xyz_rate, vel_rate, context.obliquity)

        def measure_planet_at_core() -> None:
            for body, jd_ut, jd_tt, context in all_work:
                _planet_at_core(
                    body,
                    jd_ut,
                    reader=reader,
                    obliquity=context.obliquity,
                    apparent=True,
                    aberration=True,
                    grav_deflection=True,
                    nutation=True,
                    center="geocentric",
                    frame="ecliptic",
                    observer_lat=None,
                    observer_lon=None,
                    observer_elev_m=0.0,
                    lst_deg=None,
                    jd_tt=jd_tt,
                    _dpsi_deg=context.dpsi_deg,
                    _deps_deg=context.deps_deg,
                    _rot_mat=context.rot_mat,
                    _vector_cache=context.vector_cache,
                    _context=context,
                )

        public_planet_at_median, public_planet_at_best = _measure(measure_public_planet_at)
        public_all_planets_median, public_all_planets_best = _measure(measure_public_all_planets)

        stage_results = [
            StageResult("planet_at_public_warm", len(body_jd_pairs), public_planet_at_median, public_planet_at_best),
            StageResult("all_planets_at_public_warm", len(jds), public_all_planets_median, public_all_planets_best),
        ]

        reference_wall = public_planet_at_median

        stage_specs = [
            ("ut_to_tt", len(jd_pairs), measure_ut_to_tt),
            ("build_apparent_context", len(jd_pairs), measure_build_context),
            ("nutation_2000a", len(jd_pairs), measure_nutation_only),
            ("earth_barycentric_state", len(jd_pairs), measure_earth_barycentric_state),
            ("apply_light_time", len(all_work), measure_light_time),
            ("apply_deflection", len(deflected_work), measure_deflection),
            ("apply_aberration", len(all_work), measure_aberration),
            ("apply_frame_bias", len(all_work), measure_frame_bias),
            ("apply_rotation_matrix", len(all_work), measure_rotation_apply),
            ("icrf_to_ecliptic", len(all_work), measure_icrf_to_ecliptic),
            ("geocentric_state", len(geostate_work), measure_geocentric_state),
            ("longitude_rate", len(geostate_work), measure_longitude_rate),
            ("planet_at_core", len(all_work), measure_planet_at_core),
        ]

        for name, calls, fn in stage_specs:
            median_seconds, best_seconds = _measure(fn)
            stage_results.append(StageResult(name, calls, median_seconds, best_seconds))

    payload = {
        "phase": "planetary_flow_stage_timing",
        "kernel": str(kernel_path),
        "body_set": BODIES,
        "jd_count": SAMPLE_DATES,
        "reference": {
            "planet_at_public_warm_median_seconds": public_planet_at_median,
            "all_planets_at_public_warm_median_seconds": public_all_planets_median,
        },
        "stages": [result.as_dict(reference_wall=reference_wall) for result in stage_results],
    }

    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
