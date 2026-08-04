#!/usr/bin/env python
"""Profile one admitted Phase 6 physical-visibility event workload.

This produces performance-attribution evidence, not scientific validation and
not a native-admission decision. The measured engine checkout must be clean;
set ``MOIRA_PHASE6_REPO_ROOT`` when this profiler lives outside that checkout.
"""

from __future__ import annotations

import argparse
import cProfile
from datetime import datetime, timezone
import os
from pathlib import Path
import platform
import pstats
import sys
from time import perf_counter
from typing import Any


os.environ.setdefault("MOIRA_NO_DOWNLOAD", "1")

_PROFILER_PATH = Path(__file__).resolve()
_DEFAULT_ROOT = _PROFILER_PATH.parent.parent
_ROOT = Path(
    os.environ.get("MOIRA_PHASE6_REPO_ROOT", str(_DEFAULT_ROOT))
).resolve()
sys.path.insert(0, str(_ROOT))

import moira  # noqa: E402
from moira._visibility_lut import VisibilityDataPackConfig  # noqa: E402
from moira.heliacal import (  # noqa: E402
    PhysicalVisibilitySearchPolicy,
    physical_visibility_assessment,
    physical_visibility_event,
)
from moira.spk_reader import get_reader, set_kernel_path  # noqa: E402
from scripts.benchmark_physical_visibility_phase6 import (  # noqa: E402
    _EVENT_WORKLOADS,
    _PACK_MANIFEST_SHA256,
    _assert_assessment_truth,
    _assert_event_truth,
    _fingerprint,
    _git_receipt,
    _jsonable,
    _native_receipt,
    _policy,
    _sha256_file,
    _write_output,
)


_SCHEMA = "moira.physical-visibility.phase6-profile/v1"
_SPECTRAL_FILES = {
    "_visibility_lut.py",
    "_visibility_spectral.py",
    "_visibility_targets.py",
}
_GEOMETRY_FILES = {
    "coordinates.py",
    "corrections.py",
    "julian.py",
    "nutation_2000a.py",
    "obliquity.py",
    "planets.py",
    "precession.py",
    "rise_set.py",
    "spk_reader.py",
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-pack", type=Path, required=True)
    parser.add_argument("--kernel", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--event-case",
        choices=tuple(item.workload_id for item in _EVENT_WORKLOADS),
        default="jupiter_30_day_event",
    )
    parser.add_argument("--top-functions", type=int, default=75)
    return parser.parse_args()


def _function_record(
    key: tuple[str, int, str],
    value: tuple[Any, ...],
) -> dict[str, Any]:
    primitive_calls, total_calls, internal_seconds, cumulative_seconds, _ = value
    filename, line, function = key
    return {
        "filename": filename,
        "line": line,
        "function": function,
        "primitive_calls": primitive_calls,
        "total_calls": total_calls,
        "internal_seconds": internal_seconds,
        "cumulative_seconds": cumulative_seconds,
    }


def _cluster_for(key: tuple[str, int, str]) -> str:
    filename, _line, function = key
    basename = Path(filename).name.lower()
    function_lower = function.lower()
    if basename == "_visibility_event_solver.py":
        return "event_solver"
    if basename in _SPECTRAL_FILES:
        return "spectral_target_and_pack"
    if "moira._moira_native" in function_lower:
        return "native_substrate"
    if basename in _GEOMETRY_FILES:
        return "astronomical_geometry"
    if basename == "heliacal.py":
        return "physical_visibility_orchestration"
    return "other"


def _profile_summary(
    profiler: cProfile.Profile,
    *,
    top_functions: int,
) -> dict[str, Any]:
    stats = pstats.Stats(profiler)
    records = [
        _function_record(key, value)
        for key, value in stats.stats.items()
    ]
    by_cumulative = sorted(
        records,
        key=lambda item: item["cumulative_seconds"],
        reverse=True,
    )[:top_functions]
    by_internal = sorted(
        records,
        key=lambda item: item["internal_seconds"],
        reverse=True,
    )[:top_functions]

    cluster_internal: dict[str, float] = {}
    for key, value in stats.stats.items():
        cluster = _cluster_for(key)
        cluster_internal[cluster] = (
            cluster_internal.get(cluster, 0.0) + value[2]
        )
    total_internal = sum(cluster_internal.values())
    clusters = {
        name: {
            "internal_seconds": seconds,
            "share_of_profile_internal_time": (
                seconds / total_internal if total_internal else 0.0
            ),
        }
        for name, seconds in sorted(
            cluster_internal.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    }
    return {
        "profiler": "cProfile deterministic call profiler",
        "interpretation": (
            "internal-time clusters are non-overlapping attribution; "
            "cumulative function times overlap and must not be summed"
        ),
        "total_calls": stats.total_calls,
        "primitive_calls": stats.prim_calls,
        "total_internal_seconds": stats.total_tt,
        "clusters_by_internal_time": clusters,
        "top_by_cumulative_seconds": by_cumulative,
        "top_by_internal_seconds": by_internal,
    }


def main() -> None:
    args = _parse_args()
    git_receipt = _git_receipt()
    if git_receipt["dirty"]:
        raise RuntimeError(
            "profile engine checkout must be clean; set "
            "MOIRA_PHASE6_REPO_ROOT to an isolated worktree"
        )

    data_pack = args.data_pack.resolve()
    manifest = data_pack / "manifest.json"
    if not manifest.is_file():
        raise FileNotFoundError(f"visibility manifest not found: {manifest}")
    manifest_sha256 = _sha256_file(manifest)
    if manifest_sha256 != _PACK_MANIFEST_SHA256:
        raise RuntimeError(
            "visibility manifest identity mismatch: "
            f"{manifest_sha256} != {_PACK_MANIFEST_SHA256}"
        )
    kernel = args.kernel.resolve()
    if not kernel.is_file():
        raise FileNotFoundError(f"planetary kernel not found: {kernel}")

    workload = next(
        item
        for item in _EVENT_WORKLOADS
        if item.workload_id == args.event_case
    )
    set_kernel_path(kernel)
    config = VisibilityDataPackConfig(
        data_pack,
        expected_manifest_sha256=_PACK_MANIFEST_SHA256,
    )
    policy = _policy()

    warm_assessment = physical_visibility_assessment(
        workload.body,
        workload.expected_event_jd_ut,
        workload.latitude_deg,
        workload.longitude_deg,
        data_pack_config=config,
        policy=policy,
    )
    _assert_assessment_truth(warm_assessment)

    profiler = cProfile.Profile()
    started = perf_counter()
    result = profiler.runcall(
        physical_visibility_event,
        workload.body,
        workload.phase,
        workload.jd_start,
        workload.latitude_deg,
        workload.longitude_deg,
        data_pack_config=config,
        policy=policy,
        search_policy=PhysicalVisibilitySearchPolicy(
            search_window_days=workload.search_window_days
        ),
    )
    wall_seconds = perf_counter() - started
    _assert_event_truth(result, workload)

    reader_identity = getattr(get_reader(), "_kernel_identity", None)
    payload = {
        "schema": _SCHEMA,
        "evidence_class": "performance_attribution_only_not_validation",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "harness": {
            "profile_path": str(_PROFILER_PATH),
            "profile_sha256": _sha256_file(_PROFILER_PATH),
            "benchmark_path": str(
                _ROOT / "scripts" / "benchmark_physical_visibility_phase6.py"
            ),
            "benchmark_sha256": _sha256_file(
                _ROOT / "scripts" / "benchmark_physical_visibility_phase6.py"
            ),
        },
        "engine": {
            **git_receipt,
            "moira_version": moira.__version__,
            "python": sys.version,
            "python_executable": sys.executable,
            "platform": platform.platform(),
            "processor": platform.processor(),
            "logical_cpu_count": os.cpu_count(),
            "native": _native_receipt(),
        },
        "resources": {
            "kernel": {
                "path": str(kernel),
                "bytes": kernel.stat().st_size,
                "content_identity": _jsonable(reader_identity),
            },
            "visibility_data_pack": {
                "path": str(data_pack),
                "manifest_sha256": manifest_sha256,
                "receipt": _jsonable(result.data_pack_receipt),
            },
        },
        "workload": _jsonable(workload),
        "result": {
            "status": result.status.value,
            "event_jd_ut": result.event_jd_ut,
            "event_time_residual_seconds": abs(
                result.event_jd_ut - workload.expected_event_jd_ut
            )
            * 86400.0,
            "scalar_evaluation_count": (
                result.solver_receipt.scalar_evaluation_count
            ),
            "crossing_completeness_state": (
                result.solver_receipt.crossing_completeness_state
            ),
            "result_fingerprint_sha256": _fingerprint(result),
        },
        "measurement": {
            "wall_seconds_under_profiler": wall_seconds,
            "warning": (
                "cProfile overhead makes wall time unsuitable for the "
                "unprofiled performance budget"
            ),
            "profile": _profile_summary(
                profiler,
                top_functions=args.top_functions,
            ),
        },
        "native_admission": {
            "native_work_admitted": False,
            "decision": "pending_candidate_microbenchmarks",
        },
    }
    _write_output(args.output, payload, overwrite=args.overwrite)
    print(
        f"profiled {workload.workload_id}: "
        f"{wall_seconds:.3f}s, {payload['measurement']['profile']['total_calls']} calls"
    )


if __name__ == "__main__":
    main()
