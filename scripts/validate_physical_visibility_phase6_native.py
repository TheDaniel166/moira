#!/usr/bin/env python
"""Validate admitted Phase 6 native kernels against Python oracles.

This binds one exact immutable visibility pack and a clean engine revision,
checks boundary-inclusive planetary and direct-extinction grids, exercises
deterministic concurrency, and records kernel-only performance evidence.
Scientific validation remains owned by the earlier source and holdout gates.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import math
import os
from pathlib import Path
import platform
import sys
from typing import Any


os.environ.setdefault("MOIRA_NO_DOWNLOAD", "1")

_HARNESS_PATH = Path(__file__).resolve()
_ROOT = _HARNESS_PATH.parent.parent
sys.path.insert(0, str(_ROOT))

import moira  # noqa: E402
from moira import moira_native  # noqa: E402
from moira._visibility_lut import (  # noqa: E402
    VisibilityDataPackConfig,
    load_visibility_data_pack,
)
from moira._visibility_targets import (  # noqa: E402
    VisibilityTargetContext,
    _BAND_WAVELENGTH_NM,
    _SPECTRAL_BIN_START_NM,
    _resolve_response_weights_python,
)
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


_SCHEMA = "moira.physical-visibility.phase6-native-validation/v1"
_TOLERANCES = {
    "response_ratio_absolute": 5.0e-15,
    "response_weight_absolute": 5.0e-18,
    "response_normalization_absolute": 2.0e-15,
    "direct_extinction_magnitude_absolute": 2.0e-15,
    "direct_transmission_absolute": 2.0e-15,
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-pack", type=Path, required=True)
    parser.add_argument("--kernel", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--performance-iterations", type=int, default=2000)
    parser.add_argument("--performance-repeats", type=int, default=5)
    args = parser.parse_args()
    if args.performance_iterations < 100:
        parser.error("--performance-iterations must be at least 100")
    if args.performance_repeats < 3:
        parser.error("--performance-repeats must be at least 3")
    return args


def _maximum_absolute_difference(
    left: tuple[float, ...],
    right: tuple[float, ...],
) -> float:
    return max(abs(a - b) for a, b in zip(left, right, strict=True))


def _response_cases(pack: Any) -> list[tuple[Any, VisibilityTargetContext]]:
    cases: list[tuple[Any, VisibilityTargetContext]] = []
    for profile in pack._target_profiles:
        lower, upper = profile.color_model.phase_angle_domain_deg
        if profile.target_id == "Saturn":
            phase_count = 101
            ring_latitudes = tuple(27.0 * index / 100.0 for index in range(101))
        else:
            phase_count = 1001
            ring_latitudes = (None,)
        for ring_latitude in ring_latitudes:
            for index in range(phase_count):
                cases.append(
                    (
                        profile,
                        VisibilityTargetContext(
                            phase_angle_deg=(
                                lower
                                + (upper - lower) * index / (phase_count - 1)
                            ),
                            saturn_effective_ring_sub_latitude_deg=(
                                ring_latitude
                            ),
                        ),
                    )
                )
    return cases


def _response_native_tuple(
    profile: Any,
    context: VisibilityTargetContext,
) -> tuple[float, tuple[float, ...], tuple[float, ...]]:
    resolved = profile.resolve(context)
    return (
        resolved.scotopic_to_photopic_ratio,
        resolved.photopic_extinction_weights,
        resolved.scotopic_extinction_weights,
    )


def _sample_evenly(values: list[Any], count: int) -> list[Any]:
    if len(values) <= count:
        return values
    return [
        values[round(index * (len(values) - 1) / (count - 1))]
        for index in range(count)
    ]


def main() -> None:
    args = _parse_args()
    git_receipt = _git_receipt()
    if git_receipt["dirty"]:
        raise RuntimeError("native validation requires a clean engine checkout")

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
    pack = load_visibility_data_pack(
        VisibilityDataPackConfig(
            data_pack,
            expected_manifest_sha256=_PACK_MANIFEST_SHA256,
        )
    )

    response_cases = _response_cases(pack)
    response_maxima = {
        "ratio_absolute": 0.0,
        "photopic_weight_absolute": 0.0,
        "scotopic_weight_absolute": 0.0,
        "photopic_normalization_absolute": 0.0,
        "scotopic_normalization_absolute": 0.0,
    }
    for profile, context in response_cases:
        band_deltas = profile.color_model.band_differential_magnitudes(context)
        expected = _resolve_response_weights_python(
            base_scotopic_to_photopic_ratio=(
                profile.base_scotopic_to_photopic_ratio
            ),
            base_photopic=profile.base_photopic_extinction_weights,
            base_scotopic=profile.base_scotopic_extinction_weights,
            band_deltas=band_deltas,
        )
        actual = _response_native_tuple(profile, context)
        response_maxima["ratio_absolute"] = max(
            response_maxima["ratio_absolute"], abs(actual[0] - expected[0])
        )
        response_maxima["photopic_weight_absolute"] = max(
            response_maxima["photopic_weight_absolute"],
            _maximum_absolute_difference(actual[1], expected[1]),
        )
        response_maxima["scotopic_weight_absolute"] = max(
            response_maxima["scotopic_weight_absolute"],
            _maximum_absolute_difference(actual[2], expected[2]),
        )
        response_maxima["photopic_normalization_absolute"] = max(
            response_maxima["photopic_normalization_absolute"],
            abs(math.fsum(actual[1]) - 1.0),
        )
        response_maxima["scotopic_normalization_absolute"] = max(
            response_maxima["scotopic_normalization_absolute"],
            abs(math.fsum(actual[2]) - 1.0),
        )

    altitude_lower, altitude_upper = pack.domain.target_true_altitude_deg
    altitudes = tuple(
        altitude_lower + (altitude_upper - altitude_lower) * index / 2000.0
        for index in range(2001)
    )
    direct_maxima = {
        "extinction_magnitude_absolute": 0.0,
        "transmission_absolute": 0.0,
    }
    for altitude in altitudes:
        expected = pack._interpolate_direct_extinction_spectrum_python(
            target_true_altitude_deg=altitude
        )
        actual = pack.interpolate_direct_extinction_spectrum(
            target_true_altitude_deg=altitude
        )
        direct_maxima["extinction_magnitude_absolute"] = max(
            direct_maxima["extinction_magnitude_absolute"],
            _maximum_absolute_difference(
                actual.extinction_magnitude,
                expected.extinction_magnitude,
            ),
        )
        direct_maxima["transmission_absolute"] = max(
            direct_maxima["transmission_absolute"],
            _maximum_absolute_difference(
                actual.transmission,
                expected.transmission,
            ),
        )

    response_thread_cases = _sample_evenly(response_cases, 512)
    response_serial = [
        _fingerprint(_response_native_tuple(profile, context))
        for profile, context in response_thread_cases
    ]
    with ThreadPoolExecutor(max_workers=8) as executor:
        response_concurrent = list(
            executor.map(
                lambda case: _fingerprint(
                    _response_native_tuple(case[0], case[1])
                ),
                response_thread_cases,
            )
        )
    direct_thread_altitudes = tuple(_sample_evenly(list(altitudes), 256))
    direct_serial = [
        _fingerprint(
            pack.interpolate_direct_extinction_spectrum(
                target_true_altitude_deg=altitude
            )
        )
        for altitude in direct_thread_altitudes
    ]
    with ThreadPoolExecutor(max_workers=8) as executor:
        direct_concurrent = list(
            executor.map(
                lambda altitude: _fingerprint(
                    pack.interpolate_direct_extinction_spectrum(
                        target_true_altitude_deg=altitude
                    )
                ),
                direct_thread_altitudes,
            )
        )

    jupiter = next(
        profile
        for profile in pack._target_profiles
        if profile.target_id == "Jupiter"
    )
    iterations = args.performance_iterations
    performance_contexts = tuple(
        VisibilityTargetContext(phase_angle_deg=12.0 * index / (iterations - 1))
        for index in range(iterations)
    )
    performance_deltas = tuple(
        jupiter.color_model.band_differential_magnitudes(context)
        for context in performance_contexts
    )
    performance_altitudes = tuple(
        altitude_lower
        + (altitude_upper - altitude_lower) * index / (iterations - 1)
        for index in range(iterations)
    )

    def python_response_batch() -> float:
        return math.fsum(
            _resolve_response_weights_python(
                base_scotopic_to_photopic_ratio=(
                    jupiter.base_scotopic_to_photopic_ratio
                ),
                base_photopic=jupiter.base_photopic_extinction_weights,
                base_scotopic=jupiter.base_scotopic_extinction_weights,
                band_deltas=band_deltas,
            )[0]
            for band_deltas in performance_deltas
        )

    def native_response_batch() -> float:
        return math.fsum(
            moira_native._physical_visibility_resolve_response_weights(
                _BAND_WAVELENGTH_NM,
                band_deltas,
                _SPECTRAL_BIN_START_NM,
                jupiter.base_scotopic_to_photopic_ratio,
                jupiter.base_photopic_extinction_weights,
                jupiter.base_scotopic_extinction_weights,
            )[0]
            for band_deltas in performance_deltas
        )

    def python_direct_batch() -> float:
        return math.fsum(
            pack._interpolate_direct_extinction_spectrum_python(
                target_true_altitude_deg=altitude
            ).transmission[200]
            for altitude in performance_altitudes
        )

    def native_direct_batch() -> float:
        return math.fsum(
            pack.interpolate_direct_extinction_spectrum(
                target_true_altitude_deg=altitude
            ).transmission[200]
            for altitude in performance_altitudes
        )

    performance: dict[str, Any] = {}
    for name, python_call, native_call in (
        ("response_weights", python_response_batch, native_response_batch),
        ("direct_extinction", python_direct_batch, native_direct_batch),
    ):
        python_timing, python_results = _time_calls(
            python_call, repeats=args.performance_repeats
        )
        native_timing, native_results = _time_calls(
            native_call, repeats=args.performance_repeats
        )
        batch_tolerance = iterations * (
            _TOLERANCES["response_ratio_absolute"]
            if name == "response_weights"
            else _TOLERANCES["direct_transmission_absolute"]
        )
        maximum_batch_difference = max(
            abs(python_value - native_value)
            for python_value, native_value in zip(
                python_results,
                native_results,
                strict=True,
            )
        )
        if maximum_batch_difference > batch_tolerance:
            raise RuntimeError(f"{name} batch checksum differs")
        performance[name] = {
            "iterations_per_sample": iterations,
            "maximum_batch_checksum_absolute_difference": (
                maximum_batch_difference
            ),
            "batch_checksum_absolute_tolerance": batch_tolerance,
            "python": python_timing,
            "native": native_timing,
            "median_speedup": (
                python_timing["median_seconds"]
                / native_timing["median_seconds"]
            ),
        }

    checks = {
        "response_ratio": response_maxima["ratio_absolute"]
        <= _TOLERANCES["response_ratio_absolute"],
        "response_photopic_weights": response_maxima[
            "photopic_weight_absolute"
        ]
        <= _TOLERANCES["response_weight_absolute"],
        "response_scotopic_weights": response_maxima[
            "scotopic_weight_absolute"
        ]
        <= _TOLERANCES["response_weight_absolute"],
        "response_photopic_normalization": response_maxima[
            "photopic_normalization_absolute"
        ]
        <= _TOLERANCES["response_normalization_absolute"],
        "response_scotopic_normalization": response_maxima[
            "scotopic_normalization_absolute"
        ]
        <= _TOLERANCES["response_normalization_absolute"],
        "direct_extinction_magnitude": direct_maxima[
            "extinction_magnitude_absolute"
        ]
        <= _TOLERANCES["direct_extinction_magnitude_absolute"],
        "direct_transmission": direct_maxima["transmission_absolute"]
        <= _TOLERANCES["direct_transmission_absolute"],
        "response_deterministic_concurrency": (
            response_concurrent == response_serial
        ),
        "direct_deterministic_concurrency": direct_concurrent == direct_serial,
        "response_speedup_at_least_2x": (
            performance["response_weights"]["median_speedup"] >= 2.0
        ),
        "direct_speedup_at_least_2x": (
            performance["direct_extinction"]["median_speedup"] >= 2.0
        ),
    }

    reader_identity = getattr(get_reader(), "_kernel_identity", None)
    payload = {
        "schema": _SCHEMA,
        "evidence_class": "native_differential_and_performance_not_scientific_validation",
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
                "manifest_sha256": manifest_sha256,
                "receipt": _jsonable(pack.receipt),
            },
        },
        "differential": {
            "tolerances": _TOLERANCES,
            "response_case_count": len(response_cases),
            "response_grid": {
                "non_saturn_phase_points_per_target": 1001,
                "saturn_phase_points": 101,
                "saturn_ring_latitude_points": 101,
                "boundaries_included": True,
            },
            "response_observed_maxima": response_maxima,
            "direct_case_count": len(altitudes),
            "direct_grid": {
                "altitude_points": 2001,
                "boundaries_included": True,
            },
            "direct_observed_maxima": direct_maxima,
        },
        "concurrency": {
            "worker_count": 8,
            "response_case_count": len(response_thread_cases),
            "direct_case_count": len(direct_thread_altitudes),
        },
        "performance": {
            "kind": "kernel_only_not_public_sla",
            "repeats": args.performance_repeats,
            "measurements": performance,
        },
        "checks": checks,
        "all_checks_pass": all(checks.values()),
        "native_admission": {
            "native_work_admitted": all(checks.values()),
            "admitted_kernels": [
                "physical_visibility_response_weights_v1",
                "physical_visibility_direct_extinction_v1",
            ],
            "python_reference_retained": True,
            "python_owned_semantics_unchanged": True,
        },
    }
    _write_output(args.output, payload, overwrite=args.overwrite)
    print(
        f"response cases={len(response_cases)}, "
        f"direct cases={len(altitudes)}, checks={checks}"
    )
    if not all(checks.values()):
        failures = [name for name, passed in checks.items() if not passed]
        raise SystemExit(f"Phase 6 native validation failed: {failures}")


if __name__ == "__main__":
    main()
