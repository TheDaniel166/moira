"""Resume a provisional native eclipse discovery with immutable run inputs.

This validation tool searches overlapping TT partitions and filters each event
by its computed TT. It neither certifies discovery completeness nor validates
the physical model. Outputs belong in a new directory outside the source tree.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import sys
import time

import moira
from moira import _moira_native
from moira._kernel_paths import find_planetary_kernel
from moira.eclipse import EclipseCalculator, _ut1_to_ephemeris_tt
from moira.julian import julian_day
from moira.spk_reader import SpkReader

START_TT = 990923.5
END_TT = 2817152.5
FIELDS = ("family", "year_astronomical", "jd_tt", "jd_ut1", "eclipse_type",
          "saros_series", "lunation_number")
ROOT = Path(moira.__file__).resolve().parent.parent


def file_hash(path: Path) -> str:
    """Return the SHA-256 of a file without holding it in memory."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_fingerprint() -> str:
    """Bind package resources, native sources and this runner to one digest."""
    digest = hashlib.sha256()
    roots = (ROOT / "moira", ROOT / "src" / "native")
    paths = []
    for root in roots:
        paths.extend(p for p in root.rglob("*") if p.is_file()
                     and "__pycache__" not in p.parts
                     and p.suffix.lower() not in (".pyc", ".pyo"))
    paths.extend((ROOT / "pyproject.toml", Path(__file__).resolve()))
    for path in sorted(set(paths), key=lambda p: str(p.relative_to(ROOT)).lower()):
        name = path.relative_to(ROOT).as_posix().encode("utf-8")
        digest.update(name + b"\0" + file_hash(path).encode("ascii") + b"\n")
    return digest.hexdigest()


def historical_year(jd: float) -> int:
    """Use the historical Julian/Gregorian calendar and astronomical year."""
    z = math.floor(jd + 0.5)
    if z >= 2299161:
        alpha = math.floor((z - 1867216.25) / 36524.25)
        a = z + 1 + alpha - math.floor(alpha / 4)
    else:
        a = z
    b = a + 1524
    c = math.floor((b - 122.1) / 365.25)
    d = math.floor(365.25 * c)
    e = math.floor((b - d) / 30.6001)
    month = e - 1 if e < 14 else e - 13
    return c - 4716 if month > 2 else c - 4715


def partition_boundaries(start: float, end: float) -> list[float]:
    """Match the investigation's 50-year bins and shorter kernel handoff bins."""
    candidates = ([start, end] + [julian_day(y, 1, 1) for y in range(-1950, 3001, 50)]
                  + [julian_day(y, 1, 1) for y in (1960, 1970, 1980, 1990, 2000, 2010)])
    return sorted(set(x for x in candidates if start <= x <= end))


def write_json_new(path: Path, data: dict) -> None:
    """Write a new receipt, refusing to replace an existing file."""
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", choices=("solar", "lunar"), required=True)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--kernel-sha256", required=True)
    parser.add_argument("--start-jd-tt", type=float, default=START_TT)
    parser.add_argument("--end-jd-tt", type=float, default=END_TT)
    args = parser.parse_args(argv)
    start, end = args.start_jd_tt, args.end_jd_tt
    if not (math.isfinite(start) and math.isfinite(end) and start < end):
        parser.error("the TT bounds must be finite and ordered")
    os.environ["MOIRA_NO_DOWNLOAD"] = "1"
    out = args.directory.resolve()
    if out == ROOT or ROOT in out.parents:
        parser.error("output directory must be outside the source tree")
    out.mkdir(parents=True, exist_ok=True)
    kernel_value = find_planetary_kernel()
    if kernel_value is None:
        raise RuntimeError("no planetary kernel is available with downloads disabled")
    kernel = Path(kernel_value).resolve()
    kernel_hash = file_hash(kernel)
    if kernel_hash.lower() != args.kernel_sha256.lower():
        raise RuntimeError("kernel SHA-256 does not match the requested value")
    native = Path(_moira_native.__file__).resolve()
    if ROOT not in native.parents:
        raise RuntimeError("loaded native extension is outside the isolated source tree")
    bounds = partition_boundaries(start, end)
    fingerprint = source_fingerprint()
    meta = {"schema": "moira-eclipse-discovery-v1", "product_status": "provisional",
            "family": args.family, "mode": "native", "moira_version": moira.__version__,
            "source_root": str(ROOT), "source_fingerprint_sha256": fingerprint,
            "native_extension": str(native), "native_extension_sha256": file_hash(native),
            "kernel": str(kernel), "kernel_sha256": kernel_hash,
            "python": sys.version, "platform": platform.platform(),
            "runner_sha256": file_hash(Path(__file__)), "bounds_tt": bounds,
            "time_policy": "native ephemeris-bound TT and UT1",
            "calendar": "Julian before 1582-10-15, Gregorian thereafter; astronomical years",
            "search": "2-day overlapping UT1 search; half-open computed-TT partitions",
            "limitations": "Native discovery is not proof of event completeness or physical accuracy."}
    meta_path = out / "run.json"
    if meta_path.exists():
        if json.loads(meta_path.read_text(encoding="utf-8")) != meta:
            raise RuntimeError("resume metadata differ from the requested run")
    else:
        if any(out.iterdir()):
            raise RuntimeError("new output directory is not empty")
        write_json_new(meta_path, meta)
    merged = out / "discovery.csv"
    receipt_path = out / "receipt.json"
    if merged.exists() or receipt_path.exists():
        raise RuntimeError("completed or partial merged output exists; choose a new directory")
    started = time.monotonic()
    all_rows = []
    with SpkReader(kernel) as reader:
        calc = EclipseCalculator(reader=reader)
        search = getattr(calc, args.family + "_eclipses_in_range")
        for i, (lo, hi) in enumerate(zip(bounds, bounds[1:])):
            chunk_path = out / f"chunk_{i:03d}.json"
            if chunk_path.exists():
                chunk = json.loads(chunk_path.read_text(encoding="utf-8"))
                if chunk["bounds_tt"] != [lo, hi] or chunk["fingerprint"] != fingerprint:
                    raise RuntimeError(f"resume chunk {i} does not match run metadata")
                rows = chunk["rows"]
            else:
                try:
                    rows = []
                    for event in search(lo - 2.0, hi + 2.0):
                        tt = _ut1_to_ephemeris_tt(event.jd_ut, reader)
                        if lo <= tt < hi:
                            rows.append({"family": args.family, "year_astronomical": historical_year(tt),
                                         "jd_tt": tt, "jd_ut1": event.jd_ut,
                                         "eclipse_type": str(event.data.eclipse_type),
                                         "saros_series": event.data.saros_series,
                                         "lunation_number": event.data.saros_lunation_number})
                    write_json_new(chunk_path, {"bounds_tt": [lo, hi], "fingerprint": fingerprint, "rows": rows})
                except Exception as exc:
                    with (out / "errors.jsonl").open("a", encoding="utf-8") as log:
                        log.write(json.dumps({"chunk": i, "bounds_tt": [lo, hi],
                                              "error": f"{type(exc).__name__}: {exc}"}) + "\n")
                    raise
            all_rows.extend(rows)
            print(json.dumps({"family": args.family, "chunk": i + 1,
                              "chunks": len(bounds) - 1, "events": len(all_rows),
                              "seconds": round(time.monotonic() - started, 2)}), flush=True)
    ids = [row["lunation_number"] for row in all_rows]
    if any(key is None for key in ids) or len(set(ids)) != len(ids):
        raise RuntimeError("missing or duplicate lunation identities")
    if any(a["jd_tt"] >= b["jd_tt"] for a, b in zip(all_rows, all_rows[1:])):
        raise RuntimeError("discovery rows are not strictly chronological")
    if file_hash(kernel) != kernel_hash or source_fingerprint() != fingerprint:
        raise RuntimeError("kernel or source changed during the run")
    with merged.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(all_rows)
    receipt = {"status": "provisional", "family": args.family, "row_count": len(all_rows),
               "merged_sha256": file_hash(merged), "source_fingerprint_sha256": fingerprint,
               "kernel_sha256": kernel_hash, "elapsed_seconds": round(time.monotonic() - started, 2),
               "chunk_hashes": {f"chunk_{i:03d}.json": file_hash(out / f"chunk_{i:03d}.json")
                                for i in range(len(bounds) - 1)},
               "limits": meta["limitations"]}
    write_json_new(receipt_path, receipt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
