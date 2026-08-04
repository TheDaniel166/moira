#!/usr/bin/env python
"""Reproducible Phase 6 benchmark for admitted physical visibility truth.

This is performance evidence only. It binds an explicit planetary kernel and
an explicit immutable visibility data pack, rejects fail-closed fast paths,
and replays the two independently validated Phase 3 event workloads.

Set ``MOIRA_PHASE6_REPO_ROOT`` when the harness lives outside the clean engine
checkout being measured. This lets a dirty development tree host the harness
while imports and Git identity still come from an isolated revision.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
from enum import Enum
import gc
from hashlib import sha256
import json
from math import ceil
import os
from pathlib import Path
import platform
from statistics import fmean, median, pstdev
import subprocess
import sys
from time import perf_counter
from typing import Any, Callable


os.environ.setdefault("MOIRA_NO_DOWNLOAD", "1")

_HARNESS_PATH = Path(__file__).resolve()
_DEFAULT_ROOT = _HARNESS_PATH.parent.parent
_ROOT = Path(
    os.environ.get("MOIRA_PHASE6_REPO_ROOT", str(_DEFAULT_ROOT))
).resolve()
sys.path.insert(0, str(_ROOT))

import moira  # noqa: E402
from moira import moira_native  # noqa: E402
from moira._visibility_lut import (  # noqa: E402
    VisibilityDataPackConfig,
    load_visibility_data_pack,
)
from moira.heliacal import (  # noqa: E402
    PhysicalBackgroundScope,
    PhysicalDirectionalBackground,
    PhysicalVisibilityPhase,
    PhysicalVisibilityPolicy,
    PhysicalVisibilitySearchPolicy,
    PhysicalVisibilityStatus,
    physical_visibility_assessment,
    physical_visibility_event,
)
from moira.spk_reader import get_reader, set_kernel_path  # noqa: E402


_SCHEMA = "moira.physical-visibility.phase6-benchmark/v1"
_PACK_MANIFEST_SHA256 = (
    "cf93433a9f66a5ea92832271ce3c4b023fcc8693164803539a9f1be85b17468c"
)
_EVENT_TIME_TOLERANCE_SECONDS = 0.5

# Development budgets, not public SLAs. They are frozen before any Phase 6
# optimization or native implementation and apply only to the exact workloads
# and reference-machine class recorded in the emitted artifact.
_BUDGETS_SECONDS = {
    "process_first_assessment": 3.0,
    "warm_assessment_median": 0.5,
    "jupiter_30_day_event_median": 15.0,
    "sirius_20_day_event_median": 15.0,
}


@dataclass(frozen=True, slots=True)
class EventWorkload:
    workload_id: str
    body: str
    phase: PhysicalVisibilityPhase
    jd_start: float
    search_window_days: int
    latitude_deg: float
    longitude_deg: float
    expected_event_jd_ut: float


_EVENT_WORKLOADS = (
    EventWorkload(
        workload_id="jupiter_30_day_event",
        body="Jupiter",
        phase=PhysicalVisibilityPhase.MORNING_FIRST_RISING,
        jd_start=2460050.5,
        search_window_days=30,
        latitude_deg=35.0,
        longitude_deg=35.0,
        expected_event_jd_ut=2460070.591375516,
    ),
    EventWorkload(
        workload_id="sirius_20_day_event",
        body="Sirius",
        phase=PhysicalVisibilityPhase.MORNING_FIRST_RISING,
        jd_start=2461240.5,
        search_window_days=20,
        latitude_deg=30.0,
        longitude_deg=-90.0,
        expected_event_jd_ut=2461255.950317484,
    ),
)


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(*arguments: str) -> str:
    completed = subprocess.run(
        ("git", *arguments),
        cwd=_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _git_receipt() -> dict[str, Any]:
    status = _git("status", "--porcelain", "--untracked-files=all")
    return {
        "revision": _git("rev-parse", "HEAD"),
        "branch": _git("branch", "--show-current") or None,
        "dirty": bool(status),
        "status_lines": status.splitlines(),
    }


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {
            str(key): _jsonable(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value


def _fingerprint(value: Any) -> str:
    payload = json.dumps(
        _jsonable(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return sha256(payload).hexdigest()


def _timing_summary(samples: list[float]) -> dict[str, Any]:
    if not samples:
        raise ValueError("timing samples must not be empty")
    ordered = sorted(samples)
    mean_seconds = fmean(samples)
    p95_index = max(0, ceil(0.95 * len(ordered)) - 1)
    return {
        "sample_count": len(samples),
        "samples_seconds": samples,
        "minimum_seconds": ordered[0],
        "median_seconds": median(samples),
        "mean_seconds": mean_seconds,
        "p95_nearest_rank_seconds": ordered[p95_index],
        "maximum_seconds": ordered[-1],
        "population_standard_deviation_seconds": (
            pstdev(samples) if len(samples) > 1 else 0.0
        ),
        "coefficient_of_variation": (
            pstdev(samples) / mean_seconds
            if len(samples) > 1 and mean_seconds
            else 0.0
        ),
    }


def _time_calls(
    call: Callable[[], Any],
    *,
    repeats: int,
) -> tuple[dict[str, Any], list[Any]]:
    if repeats < 1:
        raise ValueError("repeats must be at least one")
    samples: list[float] = []
    results: list[Any] = []
    for _ in range(repeats):
        gc.collect()
        started = perf_counter()
        result = call()
        samples.append(perf_counter() - started)
        results.append(result)
    return _timing_summary(samples), results


def _policy() -> PhysicalVisibilityPolicy:
    return PhysicalVisibilityPolicy(
        background=PhysicalDirectionalBackground(
            photopic_luminance_cd_m2=0.0001,
            scotopic_luminance_cd_m2=0.00015,
            scope=PhysicalBackgroundScope.DARK_SKY_ANCHOR,
            component_ids=("phase3_reference_dark_sky",),
            source_id="phase3_reference_dark_sky_v1",
            source_receipt_sha256="a" * 64,
            method_id="source_locked_reference_anchor_v1",
        ),
        expected_manifest_sha256=_PACK_MANIFEST_SHA256,
    )


def _assert_assessment_truth(result: Any) -> None:
    if result.status is not PhysicalVisibilityStatus.EVALUATED:
        raise RuntimeError(
            "assessment benchmark entered a fail-closed fast path: "
            f"status={result.status.value}, reason={result.reason}"
        )
    if result.data_pack_receipt is None:
        raise RuntimeError("assessment benchmark has no data-pack receipt")
    if result.true_target_altitude_deg is None:
        raise RuntimeError("assessment benchmark has no evaluated target geometry")


def _assert_event_truth(result: Any, workload: EventWorkload) -> None:
    if result.status is not PhysicalVisibilityStatus.EVALUATED:
        raise RuntimeError(
            f"{workload.workload_id} entered a fail-closed fast path: "
            f"status={result.status.value}, reason={result.reason}"
        )
    if result.event_jd_ut is None:
        raise RuntimeError(f"{workload.workload_id} returned no event time")
    residual_seconds = abs(
        result.event_jd_ut - workload.expected_event_jd_ut
    ) * 86400.0
    if residual_seconds > _EVENT_TIME_TOLERANCE_SECONDS:
        raise RuntimeError(
            f"{workload.workload_id} event residual {residual_seconds:.6f}s "
            f"exceeds {_EVENT_TIME_TOLERANCE_SECONDS:.3f}s"
        )
    if (
        result.solver_receipt.crossing_completeness_state
        != "certified_lipschitz_zero_enclosure"
    ):
        raise RuntimeError(
            f"{workload.workload_id} did not retain certified crossing truth"
        )


def _native_receipt() -> dict[str, Any]:
    backend = Path(str(moira_native.__backend_file__)).resolve()
    stat = backend.stat()
    manifest_function = getattr(
        moira_native,
        "_build_input_manifest_sha256",
        None,
    )
    marker_function = getattr(
        moira_native,
        "_build_provenance_marker",
        None,
    )
    return {
        "backend_file": str(backend),
        "backend_bytes": stat.st_size,
        "backend_modified_ns": stat.st_mtime_ns,
        "backend_sha256": _sha256_file(backend),
        "build_input_manifest_sha256": (
            manifest_function() if callable(manifest_function) else None
        ),
        "build_provenance_marker": (
            marker_function() if callable(marker_function) else None
        ),
    }


def _write_output(path: Path, payload: dict[str, Any], *, overwrite: bool) -> None:
    path = path.resolve()
    if path.exists() and not overwrite:
        raise FileExistsError(
            f"refusing to replace existing benchmark artifact: {path}"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    if temporary.exists():
        raise FileExistsError(f"temporary output already exists: {temporary}")
    encoded = json.dumps(
        payload,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
    ) + "\n"
    temporary.write_text(encoded, encoding="utf-8", newline="\n")
    temporary.replace(path)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-pack", type=Path, required=True)
    parser.add_argument("--kernel", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--assessment-repeats", type=int, default=5)
    parser.add_argument("--pack-load-repeats", type=int, default=3)
    parser.add_argument("--event-repeats", type=int, default=1)
    parser.add_argument(
        "--event-case",
        action="append",
        choices=tuple(item.workload_id for item in _EVENT_WORKLOADS),
        dest="event_cases",
    )
    parser.add_argument("--skip-events", action="store_true")
    parser.add_argument("--assert-budget", action="store_true")
    args = parser.parse_args()
    if args.assert_budget:
        if args.assessment_repeats < 5:
            parser.error("--assert-budget requires --assessment-repeats >= 5")
        if args.pack_load_repeats < 3:
            parser.error("--assert-budget requires --pack-load-repeats >= 3")
        if not args.skip_events and args.event_repeats < 3:
            parser.error("--assert-budget requires --event-repeats >= 3")
    return args


def main() -> None:
    args = _parse_args()
    data_pack = args.data_pack.resolve()
    kernel = args.kernel.resolve()
    manifest_path = data_pack / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"visibility manifest not found: {manifest_path}")
    actual_manifest_sha256 = _sha256_file(manifest_path)
    if actual_manifest_sha256 != _PACK_MANIFEST_SHA256:
        raise RuntimeError(
            "visibility manifest identity mismatch: "
            f"{actual_manifest_sha256} != {_PACK_MANIFEST_SHA256}"
        )
    if not kernel.is_file():
        raise FileNotFoundError(f"planetary kernel not found: {kernel}")

    git_receipt = _git_receipt()
    if git_receipt["dirty"]:
        raise RuntimeError(
            "benchmark engine checkout must be clean; use "
            "MOIRA_PHASE6_REPO_ROOT to target an isolated worktree"
        )

    set_kernel_path(kernel)
    config = VisibilityDataPackConfig(
        data_pack,
        expected_manifest_sha256=_PACK_MANIFEST_SHA256,
    )
    policy = _policy()

    first_started = perf_counter()
    first_assessment = physical_visibility_assessment(
        "Jupiter",
        2460070.591375516,
        35.0,
        35.0,
        data_pack_config=config,
        policy=policy,
    )
    first_seconds = perf_counter() - first_started
    _assert_assessment_truth(first_assessment)

    pack_timing, loaded_packs = _time_calls(
        lambda: load_visibility_data_pack(config),
        repeats=args.pack_load_repeats,
    )
    pack_fingerprints = {
        _fingerprint(item.receipt) for item in loaded_packs
    }
    if len(pack_fingerprints) != 1:
        raise RuntimeError("data-pack receipt changed across benchmark loads")

    assessment_timing, assessments = _time_calls(
        lambda: physical_visibility_assessment(
            "Jupiter",
            2460070.591375516,
            35.0,
            35.0,
            data_pack_config=config,
            policy=policy,
        ),
        repeats=args.assessment_repeats,
    )
    for assessment in assessments:
        _assert_assessment_truth(assessment)
    assessment_fingerprints = {
        _fingerprint(item) for item in assessments
    }
    if len(assessment_fingerprints) != 1:
        raise RuntimeError("assessment result changed across benchmark repeats")

    selected_ids = set(
        args.event_cases
        or (item.workload_id for item in _EVENT_WORKLOADS)
    )
    event_results: dict[str, Any] = {}
    if not args.skip_events:
        for workload in _EVENT_WORKLOADS:
            if workload.workload_id not in selected_ids:
                continue
            timing, results = _time_calls(
                lambda workload=workload: physical_visibility_event(
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
                ),
                repeats=args.event_repeats,
            )
            for result in results:
                _assert_event_truth(result, workload)
            fingerprints = {_fingerprint(item) for item in results}
            if len(fingerprints) != 1:
                raise RuntimeError(
                    f"{workload.workload_id} changed across benchmark repeats"
                )
            representative = results[-1]
            event_results[workload.workload_id] = {
                "workload": _jsonable(workload),
                "timing": timing,
                "result_fingerprint_sha256": next(iter(fingerprints)),
                "status": representative.status.value,
                "event_jd_ut": representative.event_jd_ut,
                "event_time_residual_seconds": abs(
                    representative.event_jd_ut
                    - workload.expected_event_jd_ut
                )
                * 86400.0,
                "scalar_evaluation_count": (
                    representative.solver_receipt.scalar_evaluation_count
                ),
                "crossing_completeness_state": (
                    representative.solver_receipt.crossing_completeness_state
                ),
            }

    reader_identity = getattr(get_reader(), "_kernel_identity", None)
    checks = {
        "process_first_assessment": (
            first_seconds <= _BUDGETS_SECONDS["process_first_assessment"]
        ),
        "warm_assessment_median": (
            assessment_timing["median_seconds"]
            <= _BUDGETS_SECONDS["warm_assessment_median"]
        ),
    }
    for workload_id, result in event_results.items():
        budget_key = f"{workload_id}_median"
        checks[budget_key] = (
            result["timing"]["median_seconds"]
            <= _BUDGETS_SECONDS[budget_key]
        )

    payload = {
        "schema": _SCHEMA,
        "evidence_class": "performance_only_not_scientific_validation",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "harness": {
            "path": str(_HARNESS_PATH),
            "sha256": _sha256_file(_HARNESS_PATH),
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
                "manifest_sha256": actual_manifest_sha256,
                "receipt": _jsonable(loaded_packs[-1].receipt),
            },
        },
        "measurement_policy": {
            "timer": "time.perf_counter",
            "garbage_collection_before_each_timed_repeat": True,
            "assessment_repeats": args.assessment_repeats,
            "pack_load_repeats": args.pack_load_repeats,
            "event_repeats": args.event_repeats,
            "event_time_regression_tolerance_seconds": (
                _EVENT_TIME_TOLERANCE_SECONDS
            ),
            "network": "disabled_by_explicit_local_resources",
        },
        "budgets": {
            "kind": "phase6_reference_machine_development_gate_not_public_sla",
            "seconds": _BUDGETS_SECONDS,
            "checks": checks,
            "all_executed_checks_pass": all(checks.values()),
        },
        "results": {
            "process_first_assessment": {
                "seconds": first_seconds,
                "status": first_assessment.status.value,
                "result_fingerprint_sha256": _fingerprint(first_assessment),
            },
            "data_pack_validation": {
                "timing": pack_timing,
                "receipt_fingerprint_sha256": next(iter(pack_fingerprints)),
            },
            "warm_assessment": {
                "timing": assessment_timing,
                "result_fingerprint_sha256": next(
                    iter(assessment_fingerprints)
                ),
            },
            "events": event_results,
        },
        "native_admission": {
            "decision": "pending_profile_and_candidate_microbenchmarks",
            "native_work_admitted": False,
            "reason": (
                "budget failure alone does not identify a stable numerical "
                "kernel or justify moving Python-owned semantics"
            ),
        },
    }

    if args.output is not None:
        _write_output(args.output, payload, overwrite=args.overwrite)
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    if args.assert_budget and not all(checks.values()):
        failures = [name for name, passed in checks.items() if not passed]
        raise SystemExit(f"Phase 6 performance budgets failed: {failures}")


if __name__ == "__main__":
    main()
