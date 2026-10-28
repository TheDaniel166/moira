"""Benchmark the time per call of Moira's main astronomy products.

Performance evidence only. Scientific validation remains in the oracle,
authority, and integration suites named by
``wiki/03_validation/VALIDATION_ASTRONOMY.md``; a timing here says nothing
about accuracy.

Method (shared with ``scripts/benchmark_native_bulk_eclipse_ranges.py`` and
the archived Phase 2 planetary benchmarks):

- one warm ``SpkReader`` on the discovered planetary kernel, downloads
  disabled by the caller;
- one untimed warm-up pass per product, then ``--repeats`` timed passes;
- ``gc.collect()`` before every timed pass, ``time.perf_counter`` timing;
- every pass shifts its epochs by a fraction of a day, so no pass reuses an
  epoch from an earlier pass and per-epoch caches cannot answer for it;
- the report gives the median and best pass, divided by the calls per pass.

Position products run on two epoch sets: ``modern`` (1900-2100) and
``mixed_era`` (evenly spaced across the kernel's Sun coverage), so record-level
SPK evaluation on long kernels is visible separately from the common case.
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import platform
import statistics
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import moira
from moira import Moira
from moira._kernel_paths import find_planetary_kernel
from moira.constants import Body
from moira.julian import julian_day
from moira.nutation_2000a import nutation_2000a
from moira.planets import all_planets_at, planet_at, sky_position_at
from moira.precession import precession_matrix
from moira.rise_set import find_phenomena
from moira.spk_reader import SpkReader, use_reader_override

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "moira.astronomy_speed.benchmark.v1"
BODIES = [
    Body.SUN, Body.MOON, Body.MERCURY, Body.VENUS, Body.MARS,
    Body.JUPITER, Body.SATURN, Body.URANUS, Body.NEPTUNE, Body.PLUTO,
]
SITE_LAT = 51.4779
SITE_LON = -0.0015
MODERN_START = julian_day(1900, 1, 1, 0.0)
MODERN_END = julian_day(2100, 1, 1, 0.0)
SEARCH_START = julian_day(2026, 1, 1, 0.0)


def _even(lo: float, hi: float, count: int) -> list[float]:
    step = (hi - lo) / (count - 1)
    return [lo + i * step for i in range(count)]


def _timed(fn) -> float:
    gc.collect()
    started = time.perf_counter()
    fn()
    return time.perf_counter() - started


def _measure(name, product, epoch_set, calls, repeats, run, note=None):
    """Run ``run(pass_index)`` once untimed, then ``repeats`` timed passes."""
    run(-1)
    samples = [_timed(lambda i=i: run(i)) for i in range(repeats)]
    median = statistics.median(samples)
    row = {
        "name": name,
        "product": product,
        "epoch_set": epoch_set,
        "calls_per_pass": calls,
        "repeats": repeats,
        "pass_seconds": samples,
        "median_ms_per_call": median * 1000.0 / calls,
        "best_ms_per_call": min(samples) * 1000.0 / calls,
    }
    if note:
        row["note"] = note
    print(f"{name:<34} {epoch_set:<10} {row['median_ms_per_call']:10.4f} ms/call", flush=True)
    return row


def _git_commit() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        )
        dirty = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=ROOT, capture_output=True, text=True, check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return out.stdout.strip() + ("+dirty" if dirty.stdout.strip() else "")


def _cpu_name() -> str:
    if platform.system() == "Windows":
        try:
            out = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-CimInstance Win32_Processor).Name"],
                capture_output=True, text=True, check=True, timeout=30,
            )
            if out.stdout.strip():
                return out.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            pass
    return platform.processor()


def benchmark(repeats: int, event_repeats: int, epochs: int) -> dict:
    kernel = find_planetary_kernel()
    if kernel is None:
        raise RuntimeError("No planetary kernel found; this benchmark needs a local kernel")
    rows: list[dict] = []

    with SpkReader(kernel) as reader:
        lo, hi = reader.epoch_range(0, 10)
        margin = min(30.0, (hi - lo) / 1000.0)
        sets = {
            "modern": _even(MODERN_START, MODERN_END, epochs),
            "mixed_era": _even(lo + margin, hi - margin, epochs),
        }

        def shifted(jds, i):
            offset = 0.137 * (i + 2)
            return [jd + offset for jd in jds]

        # Kernel-bound positions.
        for set_name, jds in sets.items():
            n = len(jds)

            def raw(i, jds=jds):
                for jd in shifted(jds, i):
                    reader.position(0, 10, jd)
            rows.append(_measure(
                "spk_position_ssb_sun", "raw SPK position (SSB->Sun, TDB)",
                set_name, n, repeats, raw,
            ))

            def apparent(i, jds=jds):
                for jd in shifted(jds, i):
                    for body in BODIES:
                        planet_at(body, jd, reader=reader)
            rows.append(_measure(
                "planet_at", "apparent geocentric ecliptic place, one body",
                set_name, n * len(BODIES), repeats, apparent,
            ))

            def all_bodies(i, jds=jds):
                for jd in shifted(jds, i):
                    all_planets_at(jd, bodies=BODIES, reader=reader)
            rows.append(_measure(
                "all_planets_at", "apparent geocentric places, 10 bodies at one epoch",
                set_name, n, repeats, all_bodies,
            ))

            def sky(i, jds=jds):
                for jd in shifted(jds, i):
                    for body in (Body.SUN, Body.MOON, Body.MARS):
                        sky_position_at(body, jd, SITE_LAT, SITE_LON, reader=reader)
            rows.append(_measure(
                "sky_position_at", "topocentric apparent RA/Dec/Az/Alt with refraction, one body",
                set_name, n * 3, repeats, sky,
            ))

        # Earth orientation (kernel-free).
        eo_jds = sets["modern"]

        def nut(i):
            for jd in shifted(eo_jds, i):
                nutation_2000a(jd)
        rows.append(_measure(
            "nutation_2000a", "IAU 2000A nutation angles", "modern",
            len(eo_jds), repeats, nut,
        ))

        def prec(i):
            for jd in shifted(eo_jds, i):
                precession_matrix(jd)
        rows.append(_measure(
            "precession_matrix", "IAU 2006 precession matrix", "modern",
            len(eo_jds), repeats, prec,
        ))

        def gast(i):
            for jd in shifted(eo_jds, i):
                moira.apparent_sidereal_time_at(jd, SITE_LON)
        rows.append(_measure(
            "apparent_sidereal_time_at", "apparent local sidereal time", "modern",
            len(eo_jds), repeats, gast,
        ))

        # Event searches on the same warm reader.
        def rise_set(i):
            with use_reader_override(reader):
                for day in range(10):
                    for body in (Body.SUN, Body.MOON):
                        find_phenomena(body, SEARCH_START + day + 0.137 * (i + 2), SITE_LAT, SITE_LON)
        rows.append(_measure(
            "find_phenomena", "rise, set and transits for one body over one day",
            "2026", 20, event_repeats, rise_set,
        ))

    # Facade products use the facade's own reader on the same discovered kernel.
    m = Moira()
    chart_epochs = [
        datetime(1900, 1, 1, tzinfo=timezone.utc) + timedelta(days=d)
        for d in _even(0.0, 73048.0, epochs)
    ]

    def charts(i):
        for dt in chart_epochs:
            m.chart(dt + timedelta(hours=3.3 * (i + 2)))
    rows.append(_measure(
        "Moira.chart", "full chart: default bodies plus nodes and Lilith",
        "modern", len(chart_epochs), repeats, charts,
    ))

    def star(i):
        for dt in chart_epochs:
            m.fixed_star("Sirius", dt + timedelta(hours=3.3 * (i + 2)))
    rows.append(_measure(
        "Moira.fixed_star", "apparent place of a catalog star", "modern",
        len(chart_epochs), repeats, star,
    ))

    def stations(i):
        start = SEARCH_START + 0.137 * (i + 2)
        m.stations(Body.MERCURY, start, start + 365.25)
    rows.append(_measure(
        "Moira.stations", "Mercury stations over one year", "2026", 1,
        event_repeats, stations, note="one call = one year searched",
    ))

    def phases(i):
        start = SEARCH_START + 0.137 * (i + 2)
        m.moon_phases(start, start + 365.25)
    rows.append(_measure(
        "Moira.moon_phases", "lunar phases over one year", "2026", 1,
        event_repeats, phases, note="one call = one year searched",
    ))

    def occult(i):
        start = SEARCH_START + 0.137 * (i + 2)
        m.occultations(start, start + 30.0)
    rows.append(_measure(
        "Moira.occultations", "lunar occultations over 30 days, default targets", "2026", 1,
        event_repeats, occult, note="one call = 30 days searched",
    ))

    return {
        "schema": SCHEMA,
        "evidence_class": "performance_only",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "moira_version": moira.__version__,
        "git_commit": _git_commit(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "processor": _cpu_name(),
        "logical_cpus": os.cpu_count(),
        "kernel": Path(kernel).name,
        "kernel_bytes": Path(kernel).stat().st_size,
        "environment": {
            key: os.environ.get(key)
            for key in ("MOIRA_NO_DOWNLOAD", "MOIRA_TEST_MODE", "MOIRA_STRICT_KNOWN_ISSUES")
        },
        "timing_policy": {
            "warm_reader": True,
            "untimed_warmup_passes": 1,
            "repeats": repeats,
            "event_repeats": event_repeats,
            "epochs_per_set": epochs,
            "epoch_shift_per_pass_days": 0.137,
            "statistic": "median pass / calls per pass",
        },
        "results": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--event-repeats", type=int, default=3)
    parser.add_argument("--epochs", type=int, default=200)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.repeats <= 0 or args.event_repeats <= 0 or args.epochs < 2:
        raise SystemExit("--repeats and --event-repeats must be > 0; --epochs must be >= 2")

    report = benchmark(args.repeats, args.event_repeats, args.epochs)
    rendered = json.dumps(report, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
