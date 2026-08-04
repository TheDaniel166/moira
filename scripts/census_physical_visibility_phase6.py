#!/usr/bin/env python
"""Count repeated calls inside one admitted Phase 6 event workload.

This is performance-attribution evidence only. It temporarily wraps selected
Python functions, preserves their return values and exceptions, and records
exact-input reuse. The measured engine checkout must be clean; set
``MOIRA_PHASE6_REPO_ROOT`` when this harness lives outside that checkout.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import os
from pathlib import Path
import platform
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
import moira._visibility_spectral as spectral_module  # noqa: E402
import moira.heliacal as heliacal_module  # noqa: E402
from moira._visibility_lut import (  # noqa: E402
    VisibilityDataPack,
    VisibilityDataPackConfig,
)
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


_SCHEMA = "moira.physical-visibility.phase6-call-census/v1"


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
    return parser.parse_args()


def _counter_summary(counter: Counter[tuple[Any, ...]]) -> dict[str, int]:
    calls = counter.total()
    return {
        "calls": calls,
        "unique_exact_inputs": len(counter),
        "repeated_exact_input_calls": calls - len(counter),
        "inputs_called_more_than_once": sum(
            count > 1 for count in counter.values()
        ),
        "maximum_calls_for_one_exact_input": max(
            counter.values(), default=0
        ),
    }


def _grouped_summary(
    counter: Counter[tuple[Any, ...]],
    key: Callable[[tuple[Any, ...]], str],
) -> dict[str, dict[str, int]]:
    grouped: dict[str, Counter[tuple[Any, ...]]] = {}
    for item, count in counter.items():
        grouped.setdefault(key(item), Counter())[item] = count
    return {
        group: _counter_summary(values)
        for group, values in sorted(grouped.items())
    }


def main() -> None:
    args = _parse_args()
    git_receipt = _git_receipt()
    if git_receipt["dirty"]:
        raise RuntimeError(
            "census engine checkout must be clean; set "
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

    horizontal_calls: Counter[tuple[Any, ...]] = Counter()
    planetary_profile_calls: Counter[tuple[Any, ...]] = Counter()
    stellar_profile_calls: Counter[tuple[Any, ...]] = Counter()
    direct_spectrum_calls: Counter[tuple[Any, ...]] = Counter()
    response_validation_calls: Counter[tuple[Any, ...]] = Counter()

    original_horizontal = heliacal_module._true_horizontal
    original_planetary_profile = VisibilityDataPack.resolve_target_profile
    original_stellar_profile = (
        VisibilityDataPack.resolve_stellar_target_profile
    )
    original_direct_spectrum = (
        VisibilityDataPack.interpolate_direct_extinction_spectrum
    )
    original_response_validation = (
        spectral_module._validate_response_weights
    )

    def counted_horizontal(
        body: str,
        jd_ut: float,
        lat: float,
        lon: float,
    ) -> tuple[float, float]:
        horizontal_calls[(body, jd_ut, lat, lon)] += 1
        return original_horizontal(body, jd_ut, lat, lon)

    def counted_planetary_profile(
        pack: VisibilityDataPack,
        target_id: str,
        context: Any,
    ) -> Any:
        planetary_profile_calls[
            (
                target_id,
                context.phase_angle_deg,
                context.saturn_effective_ring_sub_latitude_deg,
            )
        ] += 1
        return original_planetary_profile(pack, target_id, context)

    def counted_stellar_profile(
        pack: VisibilityDataPack,
        target_id: str,
        *,
        catalog_name: str,
        catalog_nomenclature: str,
        catalog_visual_magnitude: float,
    ) -> Any:
        stellar_profile_calls[
            (
                target_id,
                catalog_name,
                catalog_nomenclature,
                catalog_visual_magnitude,
            )
        ] += 1
        return original_stellar_profile(
            pack,
            target_id,
            catalog_name=catalog_name,
            catalog_nomenclature=catalog_nomenclature,
            catalog_visual_magnitude=catalog_visual_magnitude,
        )

    def counted_direct_spectrum(
        pack: VisibilityDataPack,
        *,
        target_true_altitude_deg: float,
    ) -> Any:
        direct_spectrum_calls[(target_true_altitude_deg,)] += 1
        return original_direct_spectrum(
            pack,
            target_true_altitude_deg=target_true_altitude_deg,
        )

    def counted_response_validation(
        values: tuple[float, ...],
        label: str,
    ) -> None:
        response_validation_calls[(label,)] += 1
        return original_response_validation(values, label)

    heliacal_module._true_horizontal = counted_horizontal
    VisibilityDataPack.resolve_target_profile = counted_planetary_profile
    VisibilityDataPack.resolve_stellar_target_profile = counted_stellar_profile
    VisibilityDataPack.interpolate_direct_extinction_spectrum = (
        counted_direct_spectrum
    )
    spectral_module._validate_response_weights = counted_response_validation
    try:
        started = perf_counter()
        result = physical_visibility_event(
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
    finally:
        heliacal_module._true_horizontal = original_horizontal
        VisibilityDataPack.resolve_target_profile = original_planetary_profile
        VisibilityDataPack.resolve_stellar_target_profile = (
            original_stellar_profile
        )
        VisibilityDataPack.interpolate_direct_extinction_spectrum = (
            original_direct_spectrum
        )
        spectral_module._validate_response_weights = (
            original_response_validation
        )

    _assert_event_truth(result, workload)
    reader_identity = getattr(get_reader(), "_kernel_identity", None)
    horizontal_by_body = _grouped_summary(
        horizontal_calls,
        lambda item: str(getattr(item[0], "value", item[0])),
    )
    payload = {
        "schema": _SCHEMA,
        "evidence_class": "performance_call_census_only_not_validation",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "harness": {
            "path": str(_HARNESS_PATH),
            "sha256": _sha256_file(_HARNESS_PATH),
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
            "wall_seconds_with_counting_wrappers": wall_seconds,
            "warning": (
                "wrapper overhead makes wall time unsuitable for the "
                "unprofiled performance budget"
            ),
            "exact_input_reuse": {
                "true_horizontal": {
                    **_counter_summary(horizontal_calls),
                    "by_body": horizontal_by_body,
                },
                "planetary_target_profile": _counter_summary(
                    planetary_profile_calls
                ),
                "stellar_target_profile": _counter_summary(
                    stellar_profile_calls
                ),
                "direct_extinction_spectrum": _counter_summary(
                    direct_spectrum_calls
                ),
                "response_weight_validation": {
                    "calls": response_validation_calls.total(),
                    "by_label": {
                        str(item[0]): count
                        for item, count in sorted(
                            response_validation_calls.items()
                        )
                    },
                },
            },
        },
        "native_admission": {
            "native_work_admitted": False,
            "decision": "pending_reuse_pilot_and_candidate_microbenchmarks",
        },
    }
    _write_output(args.output, payload, overwrite=args.overwrite)
    print(
        f"counted {workload.workload_id}: {wall_seconds:.3f}s; "
        f"horizontal {horizontal_calls.total()} calls / "
        f"{len(horizontal_calls)} exact inputs; "
        f"planetary profiles {planetary_profile_calls.total()} / "
        f"{len(planetary_profile_calls)}; "
        f"stellar profiles {stellar_profile_calls.total()} / "
        f"{len(stellar_profile_calls)}"
    )


if __name__ == "__main__":
    main()
