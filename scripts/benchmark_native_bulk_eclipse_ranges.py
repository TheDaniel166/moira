"""Benchmark the admitted public bulk-eclipse range route.

Performance evidence only. Scientific validation remains in the eclipse
oracle and integration suites.
"""

from __future__ import annotations

import argparse
import gc
import json
import platform
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

import moira
from moira._kernel_paths import find_planetary_kernel
from moira.eclipse import EclipseCalculator
from moira.spk_reader import SpkReader


J2000_UT1 = 2451545.0
HORIZONS_YEARS = (1, 10, 100, 1000)
PYTHON_BASELINE_HORIZONS = {1, 10}


def _elapsed(callable_):
    gc.collect()
    started = time.perf_counter()
    result = callable_()
    return time.perf_counter() - started, result


def _event_signature(events):
    return [
        (
            event.jd_ut,
            str(event.data.eclipse_type),
            event.data.is_solar_eclipse,
            event.data.is_lunar_eclipse,
        )
        for event in events
    ]


def _compare(native_events, python_events) -> float:
    native_signature = _event_signature(native_events)
    python_signature = _event_signature(python_events)
    if len(native_signature) != len(python_signature):
        raise RuntimeError(
            "native/Python eclipse count mismatch: "
            f"{len(native_signature)} != {len(python_signature)}"
        )
    residuals = []
    for native, python in zip(native_signature, python_signature):
        if native[1:] != python[1:]:
            raise RuntimeError(
                "native/Python eclipse identity mismatch: "
                f"{native!r} != {python!r}"
            )
        residuals.append(abs(native[0] - python[0]) * 86400.0)
    maximum = max(residuals, default=0.0)
    if maximum > 0.1:
        raise RuntimeError(
            f"native/Python eclipse timing residual {maximum:.6f}s exceeds 0.1s"
        )
    return maximum


def benchmark(*, repeats: int) -> dict:
    kernel = find_planetary_kernel()
    if kernel is None:
        raise RuntimeError("No planetary kernel found")

    report = {
        "schema": "moira.native_bulk_eclipse_ranges.benchmark.v1",
        "evidence_class": "performance_only",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "moira_version": moira.__version__,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor(),
        "kernel": str(kernel),
        "start_jd_ut1": J2000_UT1,
        "candidate_policy": {
            "separation_ceiling_deg": 2.0,
            "scan_step_days": 2.0,
            "padding_days": 35.0,
            "native_role": "candidate discovery only",
            "python_role": "time policy, refinement, classification, range filtering, result assembly",
        },
        "timing_policy": {
            "warm_reader": True,
            "normal_repeats": repeats,
            "long_horizon_repeats": 1,
            "python_baseline_horizons_years": sorted(PYTHON_BASELINE_HORIZONS),
        },
        "results": {},
    }

    with SpkReader(kernel) as reader:
        # Warm native segment/evaluator caches before measuring standard load.
        for family in ("solar", "lunar"):
            getattr(
                EclipseCalculator(reader=reader),
                f"{family}_eclipses_in_range",
            )(J2000_UT1, J2000_UT1 + 365.25)

        for years in HORIZONS_YEARS:
            jd_end = J2000_UT1 + 365.25 * years
            horizon = {}
            native_repeats = repeats if years <= 10 else 1
            for family in ("solar", "lunar"):
                native_samples = []
                native_events = None
                for _ in range(native_repeats):
                    calc = EclipseCalculator(reader=reader)
                    elapsed, events = _elapsed(
                        lambda calc=calc: getattr(
                            calc,
                            f"{family}_eclipses_in_range",
                        )(J2000_UT1, jd_end)
                    )
                    native_samples.append(elapsed)
                    if native_events is None:
                        native_events = events
                    elif _event_signature(events) != _event_signature(native_events):
                        raise RuntimeError("native eclipse benchmark is not deterministic")

                family_result = {
                    "event_count": len(native_events),
                    "native_seconds": native_samples,
                    "native_median_seconds": statistics.median(native_samples),
                }

                if years in PYTHON_BASELINE_HORIZONS:
                    python_samples = []
                    python_events = None
                    for _ in range(repeats):
                        calc = EclipseCalculator(reader=reader)
                        elapsed, events = _elapsed(
                            lambda calc=calc: getattr(
                                calc,
                                f"_{family}_eclipses_in_range_python",
                            )(J2000_UT1, jd_end)
                        )
                        python_samples.append(elapsed)
                        if python_events is None:
                            python_events = events
                    max_residual = _compare(native_events, python_events)
                    python_median = statistics.median(python_samples)
                    native_median = family_result["native_median_seconds"]
                    family_result.update(
                        {
                            "python_seconds": python_samples,
                            "python_median_seconds": python_median,
                            "speedup_median": python_median / native_median,
                            "max_parity_residual_seconds": max_residual,
                        }
                    )
                horizon[family] = family_result
            report["results"][str(years)] = horizon
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.repeats <= 0:
        raise SystemExit("--repeats must be > 0")

    report = benchmark(repeats=args.repeats)
    rendered = json.dumps(report, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
