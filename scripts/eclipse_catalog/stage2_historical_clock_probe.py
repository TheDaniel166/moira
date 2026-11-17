"""Reproduce one bounded historical TT clock probe using the project venv.

This measures one conditional frozen-record finite-cone policy, not a native
angular-model eclipse or a continuous/physical absence proof. Run from the
isolated checkout with MOIRA_NO_DOWNLOAD=1. The optional JSON output is
created exclusively, so an existing receipt is never overwritten.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
from time import perf_counter
from types import SimpleNamespace


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def source_fingerprint(repo: Path) -> tuple[str, int]:
    """Hash selected Python and native source files, not all build inputs."""
    sources = [repo / "CMakeLists.txt"]
    sources.extend(path for path in (repo / "moira").rglob("*.py") if "__pycache__" not in path.parts)
    sources.extend(path for path in (repo / "src" / "native").rglob("*")
                   if path.is_file() and path.suffix.lower() in {".c", ".cc", ".cpp", ".h", ".hpp"})
    value = hashlib.sha256()
    for path in sorted(sources, key=lambda item: item.relative_to(repo).as_posix()):
        name = path.relative_to(repo).as_posix().encode("utf-8")
        value.update(len(name).to_bytes(8, "big"))
        value.update(name)
        value.update(bytes.fromhex(digest(path)))
    return value.hexdigest(), len(sources)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if os.environ.get("MOIRA_NO_DOWNLOAD") != "1":
        raise SystemExit("Set MOIRA_NO_DOWNLOAD=1 before running this probe")

    repo = Path.cwd().resolve()
    before, count_before = source_fingerprint(repo)
    from moira import _moira_native
    from moira._kernel_paths import find_planetary_kernel
    from moira.lunar_shadow_events import inspect_lunar_shadow_tt_interval
    from moira.spk_reader import SpkReader

    binary = Path(_moira_native.__file__).resolve()
    if binary.parent != repo / "moira":
        raise SystemExit("Loaded native binary does not belong to this checkout")
    kernel = find_planetary_kernel()
    if kernel is None:
        raise SystemExit("No planetary kernel is installed")
    expected_kernel = "9a824e6a8ce3d39f8a513b17278ff7b7ad226f964c76d2019b0a51d8808d6ff5"
    reader = SpkReader(kernel)
    instant_tt = 1248813.457560655
    timer = perf_counter()
    result = inspect_lunar_shadow_tt_interval(
        SimpleNamespace(_reader=reader), instant_tt, instant_tt,
        earth_radius_scale=1.01, max_exhaustive_clock_states=3_000_000,
    )
    seconds = perf_counter() - timer
    after, count_after = source_fingerprint(repo)
    if before != after or count_before != count_after:
        raise SystemExit("Selected source files changed during probe; no receipt written")
    if result.kernel_sha256_at_reader_open != expected_kernel:
        raise SystemExit("The discovered kernel is not the pinned DE441 resource")
    receipt = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "selected_source_fingerprint_sha256": before,
        "selected_source_file_count": count_before,
        "source_fingerprint_scope": "moira/**/*.py, src/native C/C++ source and headers, CMakeLists.txt; not full build provenance",
        "native_binary_path": str(binary),
        "native_binary_sha256": digest(binary),
        "kernel_path": str(kernel),
        "kernel_sha256_at_reader_open": result.kernel_sha256_at_reader_open,
        "tt_start": instant_tt,
        "tt_end": instant_tt,
        "model": result.model,
        "policy": result.execution_policy,
        "earth_radius_scale": 1.01,
        "max_exhaustive_clock_states": result.max_exhaustive_clock_states,
        "exhaustive_clock_states_checked": result.exhaustive_clock_states_checked,
        "exhaustive_clock_cache_hits": result.exhaustive_clock_cache_hits,
        "route_bounds_evaluated": result.route_bounds_evaluated,
        "clock_obligations": result.clock_obligations,
        "norm_obligations": result.norm_obligations,
        "status": result.status,
        "reason": result.reason,
        "penumbral_margin_lower_km": result.penumbral_margin_lower_km,
        "penumbral_margin_upper_km": result.penumbral_margin_upper_km,
        "elapsed_seconds": seconds,
        "limits": "One warm-environment represented TT point; finite-cone copied-record policy differs from native 13.9-second angular control. No live-route, continuous-time, physical-accuracy, or search-completeness proof. Source fingerprint is not build or runtime attestation.",
    }
    encoded = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        with args.output.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(encoded)
    print(encoded, end="")


if __name__ == "__main__":
    main()
