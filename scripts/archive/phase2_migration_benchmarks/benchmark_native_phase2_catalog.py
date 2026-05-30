"""
Benchmark native DAF/SPK catalog reading against the prior jplephem summary walk.
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
from moira._kernel_paths import find_planetary_kernel

ARTIFACT = Path("tests/artifacts/benchmarks/native_phase2_catalog.json")
REPEATS = 15


@contextmanager
def _native_catalog(enabled: bool):
    original = spk_reader._HAS_NATIVE_DAF
    spk_reader._HAS_NATIVE_DAF = enabled
    try:
        yield
    finally:
        spk_reader._HAS_NATIVE_DAF = original


def _measure_open(path: Path, enabled: bool) -> float:
    with _native_catalog(enabled):
        start = time.perf_counter()
        reader = spk_reader.SpkReader(path)
        elapsed = time.perf_counter() - start
        reader.close()
        return elapsed


def main() -> None:
    if not spk_reader._HAS_NATIVE_DAF:
        raise RuntimeError("native DAF catalog reader is not available in moira.moira_native")

    kernel_path = find_planetary_kernel()
    python_runs = [_measure_open(kernel_path, False) for _ in range(REPEATS)]
    native_runs = [_measure_open(kernel_path, True) for _ in range(REPEATS)]

    payload = {
        "phase": "phase2_catalog_slice",
        "kernel": str(kernel_path),
        "repeats": REPEATS,
        "python_best_seconds": min(python_runs),
        "native_best_seconds": min(native_runs),
        "python_median_seconds": statistics.median(python_runs),
        "native_median_seconds": statistics.median(native_runs),
    }
    payload["speedup_best"] = payload["python_best_seconds"] / payload["native_best_seconds"]
    payload["speedup_median"] = payload["python_median_seconds"] / payload["native_median_seconds"]

    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
