#!/usr/bin/env python
"""Microbenchmark stable Phase 6 physical-visibility numerical clusters.

The measurements attribute cost only. They do not validate scientific truth,
change a public performance promise, or admit a native implementation. The
engine checkout and explicit resources are bound exactly as in the Phase 6
baseline harness.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gc
import math
import os
from pathlib import Path
import platform
import sys
from typing import Any, Callable


os.environ.setdefault("MOIRA_NO_DOWNLOAD", "1")

_HARNESS_PATH = Path(__file__).resolve()
_DEFAULT_ROOT = _HARNESS_PATH.parent.parent
_ROOT = Path(
    os.environ.get("MOIRA_PHASE6_REPO_ROOT", str(_DEFAULT_ROOT))
).resolve()
sys.path.insert(0, str(_ROOT))

import moira  # noqa: E402
from moira._visibility_lut import (  # noqa: E402
    VisibilityDataPackConfig,
    load_visibility_data_pack,
)
from moira._visibility_spectral import (  # noqa: E402
    TargetSpectralProfile,
    _validate_response_weights,
    condition_target,
)
from moira._visibility_targets import VisibilityTargetContext  # noqa: E402
from moira.spk_reader import get_reader, set_kernel_path  # noqa: E402
from scripts.benchmark_physical_visibility_phase6 import (  # noqa: E402
    _PACK_MANIFEST_SHA256,
    _fingerprint,
    _git_receipt,
    _jsonable,
    _native_receipt,
    _sha256_file,
    _time_calls,
    _write_output,
)


_SCHEMA = "moira.physical-visibility.phase6-microbenchmark/v1"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-pack", type=Path, required=True)
    parser.add_argument("--kernel", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--iterations", type=int, default=2000)
    parser.add_argument("--repeats", type=int, default=5)
    args = parser.parse_args()
    if args.iterations < 100:
        parser.error("--iterations must be at least 100")
    if args.repeats < 3:
        parser.error("--repeats must be at least 3")
    return args


def _measure_batch(
    operation: Callable[[], Any],
    *,
    iterations: int,
    repeats: int,
) -> dict[str, Any]:
    timing, results = _time_calls(operation, repeats=repeats)
    fingerprints = {_fingerprint(value) for value in results}
    if len(fingerprints) != 1:
        raise RuntimeError("microbenchmark result changed across repeats")
    timing["iterations_per_sample"] = iterations
    timing["median_nanoseconds_per_iteration"] = (
        timing["median_seconds"] * 1_000_000_000.0 / iterations
    )
    return {
        "timing": timing,
        "result_fingerprint_sha256": next(iter(fingerprints)),
    }


def main() -> None:
    args = _parse_args()
    git_receipt = _git_receipt()
    if git_receipt["dirty"]:
        raise RuntimeError(
            "microbenchmark engine checkout must be clean; set "
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
    set_kernel_path(kernel)

    config = VisibilityDataPackConfig(
        data_pack,
        expected_manifest_sha256=_PACK_MANIFEST_SHA256,
    )
    pack = load_visibility_data_pack(config)
    iterations = args.iterations
    phase_contexts = tuple(
        VisibilityTargetContext(
            phase_angle_deg=12.0 * index / max(1, iterations - 1)
        )
        for index in range(iterations)
    )
    altitudes = tuple(
        0.25 + (45.0 - 0.25) * index / max(1, iterations - 1)
        for index in range(iterations)
    )
    representative = pack.resolve_target_profile(
        "Jupiter", phase_contexts[iterations // 2]
    )
    representative_profile = TargetSpectralProfile(
        target_id=representative.target_id,
        top_of_atmosphere_visual_magnitude=-2.0,
        scotopic_to_photopic_ratio=(
            representative.scotopic_to_photopic_ratio
        ),
        photopic_extinction_weights=(
            representative.photopic_extinction_weights
        ),
        scotopic_extinction_weights=(
            representative.scotopic_extinction_weights
        ),
        photometry_model_id="phase6_microbenchmark",
        photometry_source_ids=("phase6_microbenchmark",),
        spectral_profile_id=representative.spectral_profile_id,
        spectral_source_ids=representative.spectral_source_ids,
        spectral_source_receipt_sha256=(
            representative.spectral_source_receipt_sha256
        ),
        spectral_model_details=representative.spectral_model_details,
    )
    representative_direct = pack.interpolate_direct_extinction_spectrum(
        target_true_altitude_deg=10.0
    )

    def resolve_planetary_profiles() -> float:
        return math.fsum(
            pack.resolve_target_profile(
                "Jupiter", context
            ).scotopic_to_photopic_ratio
            for context in phase_contexts
        )

    def resolve_stellar_profiles() -> float:
        return math.fsum(
            pack.resolve_stellar_target_profile(
                "Sirius",
                catalog_name="Sirius",
                catalog_nomenclature="alf CMa",
                catalog_visual_magnitude=-1.46,
            ).scotopic_to_photopic_ratio
            for _ in range(iterations)
        )

    def interpolate_direct_spectra() -> float:
        return math.fsum(
            pack.interpolate_direct_extinction_spectrum(
                target_true_altitude_deg=altitude
            ).transmission[200]
            for altitude in altitudes
        )

    def validate_response_weight_pairs() -> int:
        for _ in range(iterations):
            _validate_response_weights(
                representative.photopic_extinction_weights,
                "photopic_extinction_weights",
            )
            _validate_response_weights(
                representative.scotopic_extinction_weights,
                "scotopic_extinction_weights",
            )
        return iterations * 2

    def construct_internal_profiles() -> float:
        last = representative_profile
        for _ in range(iterations):
            last = TargetSpectralProfile(
                target_id=representative.target_id,
                top_of_atmosphere_visual_magnitude=-2.0,
                scotopic_to_photopic_ratio=(
                    representative.scotopic_to_photopic_ratio
                ),
                photopic_extinction_weights=(
                    representative.photopic_extinction_weights
                ),
                scotopic_extinction_weights=(
                    representative.scotopic_extinction_weights
                ),
                photometry_model_id="phase6_microbenchmark",
                photometry_source_ids=("phase6_microbenchmark",),
                spectral_profile_id=representative.spectral_profile_id,
                spectral_source_ids=representative.spectral_source_ids,
                spectral_source_receipt_sha256=(
                    representative.spectral_source_receipt_sha256
                ),
                spectral_model_details=(
                    representative.spectral_model_details
                ),
            )
        return last.scotopic_to_photopic_ratio

    def condition_targets() -> float:
        return math.fsum(
            condition_target(
                representative_profile,
                representative_direct,
                0.5,
            ).conditioned_target_magnitude
            for _ in range(iterations)
        )

    operations = {
        "jupiter_dynamic_target_profile_resolution": (
            resolve_planetary_profiles
        ),
        "sirius_invariant_target_profile_resolution": (
            resolve_stellar_profiles
        ),
        "direct_extinction_spectrum_interpolation": (
            interpolate_direct_spectra
        ),
        "response_weight_validation_pair": validate_response_weight_pairs,
        "internal_target_profile_construction": construct_internal_profiles,
        "condition_target_spectral_integration": condition_targets,
    }
    measurements: dict[str, Any] = {}
    gc_was_enabled = gc.isenabled()
    try:
        for name, operation in operations.items():
            measurements[name] = _measure_batch(
                operation,
                iterations=iterations,
                repeats=args.repeats,
            )
    finally:
        if gc_was_enabled and not gc.isenabled():
            gc.enable()

    reader_identity = getattr(get_reader(), "_kernel_identity", None)
    payload = {
        "schema": _SCHEMA,
        "evidence_class": "performance_microbenchmark_only_not_validation",
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
                "receipt": _jsonable(pack.receipt),
            },
        },
        "measurement_policy": {
            "timer": "time.perf_counter",
            "iterations_per_sample": iterations,
            "repeats": args.repeats,
            "garbage_collection_before_each_timed_repeat": True,
            "phase_angle_grid_deg": [0.0, 12.0],
            "target_true_altitude_grid_deg": [0.25, 45.0],
        },
        "measurements": measurements,
        "native_admission": {
            "native_work_admitted": False,
            "decision": "pending_candidate_pilot_and_differential_design",
        },
    }
    _write_output(args.output, payload, overwrite=args.overwrite)
    for name, measurement in measurements.items():
        nanoseconds = measurement["timing"][
            "median_nanoseconds_per_iteration"
        ]
        print(f"{name}: {nanoseconds:.1f} ns/iteration median")


if __name__ == "__main__":
    main()
