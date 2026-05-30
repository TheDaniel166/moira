"""
scripts/compare_type13_vs_sb441.py

Head-to-head accuracy comparison: Type 13 reshards vs original sb441-n373s.bsp.

Question answered:
    Do the ~3.5" errors at the 1960 epoch for distant TNOs (Orcus, Ixion,
    Varuna, Quaoar) originate from the Type 13 resampling step, or are they
    already present in the underlying sb441-n373s.bsp orbit solution?

Method:
    For each fixture case, run asteroid_at() under two KernelPool configurations:

      pool_orig  — [de441, sb441-n373s.bsp]
                   Uses the original Type 2 Chebyshev data directly.

      pool_shard — [de441, shard_014.bsp]
                   Uses the Type 13 Hermite reshard that contains the TNOs.

    Both pools use heliocentric center=10 TNO segments and resolve the Sun via
    de441's barycentric Sun ephemeris (KernelPool phase-2 center chaining).

Bodies covered:
    Main-belt: Ceres, Pallas, Juno, Vesta   — expected near-zero delta
    TNOs:      Varuna, Ixion, Quaoar, Orcus  — the interesting cases

Reference: tests/fixtures/horizons_asteroid_reference.json
"""

from __future__ import annotations

import json
import sys
from math import asin, degrees, sqrt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from moira._kernel_paths import find_kernel, find_planetary_kernel
from moira._spk_body_kernel import SmallBodyKernel
from moira.asteroids import asteroid_at
from moira.spk_reader import KernelPool, SpkReader, use_reader_override

FIXTURE = ROOT / "tests" / "fixtures" / "horizons_asteroid_reference.json"
MANIFEST_DIR = ROOT / "moira" / "kernels" / "sb441_type13"
SHARD_14 = MANIFEST_DIR / "sb441_type13_shard_014.bsp"

FOCUS = {"Ceres", "Pallas", "Juno", "Vesta", "Varuna", "Ixion", "Quaoar", "Orcus"}


def _angle_diff_arcsec(a: float, b: float) -> float:
    d = (a - b + 180.0) % 360.0 - 180.0
    return d * 3600.0


def _build_orig_pool() -> KernelPool:
    de441 = SpkReader(find_planetary_kernel())
    sb441 = SmallBodyKernel(find_kernel("sb441-n373s.bsp"))
    return KernelPool([de441, sb441])


def _build_shard_pool() -> KernelPool:
    de441 = SpkReader(find_planetary_kernel())
    shard = SmallBodyKernel(SHARD_14)
    return KernelPool([de441, shard])


def main() -> None:
    if not FIXTURE.exists():
        print("Fixture not found — run scripts/build_asteroid_horizons_fixture.py first.")
        sys.exit(1)

    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    cases = [c for c in data.get("cases", []) if "error" not in c and c["body"] in FOCUS]

    pool_orig = _build_orig_pool()
    pool_shard = _build_shard_pool()

    rows: list[dict] = []

    for case in cases:
        body = case["body"]
        jd_ut = case["jd_ut"]
        ref_lon = case["ecl_lon_deg"]
        ref_lat = case["ecl_lat_deg"]
        label = case["label"]

        try:
            with use_reader_override(pool_orig):
                r_orig = asteroid_at(body, jd_ut)
            orig_lon_err = _angle_diff_arcsec(r_orig.longitude, ref_lon)
            orig_lat_err = (r_orig.latitude - ref_lat) * 3600.0
        except Exception as e:
            orig_lon_err = orig_lat_err = float("nan")
            orig_note = str(e)[:60]
        else:
            orig_note = ""

        try:
            with use_reader_override(pool_shard):
                r_shard = asteroid_at(body, jd_ut)
            shard_lon_err = _angle_diff_arcsec(r_shard.longitude, ref_lon)
            shard_lat_err = (r_shard.latitude - ref_lat) * 3600.0
        except Exception as e:
            shard_lon_err = shard_lat_err = float("nan")
            shard_note = str(e)[:60]
        else:
            shard_note = ""

        rows.append({
            "body": body,
            "label": label,
            "orig_lon": orig_lon_err,
            "orig_lat": orig_lat_err,
            "shard_lon": shard_lon_err,
            "shard_lat": shard_lat_err,
            "orig_note": orig_note,
            "shard_note": shard_note,
        })

    pool_orig.close()
    pool_shard.close()

    # Print results grouped by body
    col = 12
    hdr = (
        "Body         Epoch                   "
        "ORIG lon\"   ORIG lat\"    SHARD lon\"  SHARD lat\"   delta lon\""
    )
    print(hdr)
    print("-" * len(hdr))

    prev_body = None
    for r in sorted(rows, key=lambda x: (x["body"], x["label"])):
        if r["body"] != prev_body:
            if prev_body is not None:
                print()
            prev_body = r["body"]

        delta_lon = r["shard_lon"] - r["orig_lon"]
        note = (r["orig_note"] or r["shard_note"])
        note_str = f"  [{note}]" if note else ""

        def _fmt(v: float) -> str:
            return f"{'N/A':>10}" if v != v else f"{v:>+10.3f}"

        print(
            f"{r['body']:<12} {r['label']:<22} "
            f"{_fmt(r['orig_lon'])} {_fmt(r['orig_lat'])}  "
            f"{_fmt(r['shard_lon'])} {_fmt(r['shard_lat'])}  "
            f"{_fmt(delta_lon)}"
            f"{note_str}"
        )

    print()
    print("Interpretation:")
    print("  delta lon ~= 0  => resampling introduces no additional error")
    print("  delta lon >> 0  => Type 13 Hermite fit degrades accuracy")
    print("  (ORIG errors >> 0 confirm errors are in the sb441 orbit solution)")
    print()
    print("Note: main-belt N/A for pool_shard is expected — shard_014 contains")
    print("  only TNOs; main-belt bodies live in shards 001-013.")


if __name__ == "__main__":
    main()
