"""Provisional independent lunar NASA-compatible five-millennium discovery.

Each search uses Moira's NASA-style apparent-vector lunar canon and DE441;
it is a compatibility policy, not a reproduction of NASA's ephemeris.  Search
completeness and physical accuracy are not certified.  Outputs and checkpoints
are kept outside the source tree and never overwrite completed results.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import csv
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
from moira.eclipse import EclipseCalculator
from moira.eclipse_canon import (
    DEFAULT_LUNAR_CANON_METHOD,
    _ut_to_tt_nasa_catalog,
    lunar_canon_source_model,
)
from moira.spk_reader import SpkReader

from discovery import END_TT, FIELDS, ROOT, START_TT, file_hash
from discovery import historical_year, partition_boundaries, source_fingerprint, write_json_new


def _scan_chunk(args: tuple[int, float, float, str, str, str, str]) -> tuple[int, int]:
    index, lo, hi, kernel, directory, fingerprint, runner_sha = args
    target = Path(directory) / f"chunk_{index:03d}.json"
    checksum = Path(directory) / f"chunk_{index:03d}.sha256"
    if target.exists():
        if not checksum.exists() or checksum.read_text(encoding="ascii").strip() != file_hash(target):
            raise RuntimeError(f"resume chunk {index} has a missing or invalid content digest")
        chunk = json.loads(target.read_text(encoding="utf-8"))
        if (chunk["bounds_tt"] != [lo, hi] or chunk["fingerprint"] != fingerprint
                or chunk["runner_sha256"] != runner_sha):
            raise RuntimeError(f"resume chunk {index} does not match the frozen run")
        return index, len(chunk["rows"])
    if checksum.exists():
        raise RuntimeError(f"resume chunk {index} has a digest but no payload")
    rows = []
    with SpkReader(Path(kernel)) as reader:
        calculator = EclipseCalculator(reader=reader)
        # The maximum occurs close to full moon. A two-day UT margin also
        # exceeds the maximum NASA-canon delta T over the specified range;
        # unlike indexing native events, this independently searches lunations.
        cursor = lo - 2.0
        previous_tt = -math.inf
        while True:
            event = calculator.next_lunar_eclipse_canon(cursor)
            tt = _ut_to_tt_nasa_catalog(event.jd_ut)
            if tt <= previous_tt or event.jd_ut <= cursor:
                raise RuntimeError("NASA-compatible search failed chronological ordering")
            if tt >= hi:
                break
            if lo <= tt < hi:
                rows.append({"family": "lunar", "year_astronomical": historical_year(tt),
                             "jd_tt": tt, "jd_ut1": event.jd_ut,
                             "eclipse_type": str(event.data.eclipse_type),
                             "saros_series": event.data.saros_series,
                             "lunation_number": event.data.saros_lunation_number})
            previous_tt = tt
            cursor = event.jd_ut + 2.0
    write_json_new(target, {"bounds_tt": [lo, hi], "fingerprint": fingerprint,
                            "runner_sha256": runner_sha, "rows": rows})
    with checksum.open("x", encoding="ascii") as stream:
        stream.write(file_hash(target) + "\n")
    return index, len(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--kernel-sha256", required=True)
    parser.add_argument("--start-jd-tt", type=float, default=START_TT)
    parser.add_argument("--end-jd-tt", type=float, default=END_TT)
    parser.add_argument("--jobs", type=int, default=8)
    options = parser.parse_args(argv)
    lo, hi = options.start_jd_tt, options.end_jd_tt
    if not (math.isfinite(lo) and math.isfinite(hi) and lo < hi and 1 <= options.jobs <= 16):
        parser.error("TT bounds must be finite and ordered and jobs in [1,16]")
    if lo < START_TT or hi > END_TT:
        parser.error("the search margin is established only over the five-millennium range")
    os.environ["MOIRA_NO_DOWNLOAD"] = "1"
    out = options.directory.resolve()
    if out == ROOT or ROOT in out.parents:
        parser.error("output directory must be outside the source tree")
    out.mkdir(parents=True, exist_ok=True)
    kernel_value = find_planetary_kernel()
    if kernel_value is None:
        raise RuntimeError("no planetary kernel is available with downloads disabled")
    kernel = Path(kernel_value).resolve()
    kernel_hash = file_hash(kernel)
    if kernel_hash.lower() != options.kernel_sha256.lower():
        raise RuntimeError("kernel SHA-256 does not match the requested value")
    native = Path(_moira_native.__file__).resolve()
    if ROOT not in native.parents:
        raise RuntimeError("loaded native extension is outside the isolated source tree")
    bounds = partition_boundaries(lo, hi)
    fingerprint = source_fingerprint()
    runner_sha = file_hash(Path(__file__))
    limits = ("Independent Moira NASA-compatible discovery is not a proof of event "
              "completeness or NASA ephemeris reproduction; DE441 and the selected "
              "apparent-vector convention remain Moira model choices.")
    meta = {"schema": "moira-eclipse-canon-discovery-v1", "product_status": "provisional",
            "family": "lunar", "mode": "nasa_compat", "moira_version": moira.__version__,
            "canon_method": DEFAULT_LUNAR_CANON_METHOD,
            "source_model": lunar_canon_source_model(DEFAULT_LUNAR_CANON_METHOD),
            "source_root": str(ROOT), "source_fingerprint_sha256": fingerprint,
            "native_extension": str(native), "native_extension_sha256": file_hash(native),
            "kernel": str(kernel), "kernel_sha256": kernel_hash,
            "python": sys.version, "platform": platform.platform(),
            "runner_sha256": runner_sha, "bounds_tt": bounds,
            "time_policy": "NASA-canon polynomial delta T with month-midpoint year; UT1 and TT explicitly separated",
            "calendar": "Julian before 1582-10-15, Gregorian thereafter; astronomical years",
            "search": "independent NASA-canon lunar search, 2-day overlap, half-open computed-TT partitions",
            "limitations": limits}
    metadata = out / "run.json"
    if metadata.exists():
        if json.loads(metadata.read_text(encoding="utf-8")) != meta:
            raise RuntimeError("resume metadata differ from the requested run")
    else:
        if any(out.iterdir()):
            raise RuntimeError("new output directory is not empty")
        write_json_new(metadata, meta)
    merged, receipt_path = out / "discovery.csv", out / "receipt.json"
    if merged.exists() or receipt_path.exists():
        raise RuntimeError("completed or partial merged output exists; choose a new directory")
    started = time.monotonic()
    tasks = [(i, start, end, str(kernel), str(out), fingerprint, runner_sha)
             for i, (start, end) in enumerate(zip(bounds, bounds[1:]))]
    with ProcessPoolExecutor(max_workers=options.jobs) as executor:
        futures = {executor.submit(_scan_chunk, task): task[0] for task in tasks}
        completed = 0
        for future in as_completed(futures):
            index = futures[future]
            try:
                _, count = future.result()
            except Exception as exc:
                with (out / "errors.jsonl").open("a", encoding="utf-8") as log:
                    log.write(json.dumps({"chunk": index, "error": f"{type(exc).__name__}: {exc}"}) + "\n")
                # A running chunk can finish, but do not keep scheduling the
                # rest of the five-millennium workload after a failed chunk.
                for pending in futures:
                    pending.cancel()
                raise
            completed += 1
            print(json.dumps({"mode": "nasa_compat", "chunk": index,
                              "completed": completed, "total_chunks": len(tasks),
                              "events_in_chunk": count,
                              "seconds": round(time.monotonic() - started, 2)}), flush=True)
    all_rows = []
    for index in range(len(tasks)):
        chunk_path = out / f"chunk_{index:03d}.json"
        checksum = out / f"chunk_{index:03d}.sha256"
        if not checksum.exists() or checksum.read_text(encoding="ascii").strip() != file_hash(chunk_path):
            raise RuntimeError(f"chunk {index} changed after its checkpoint")
        chunk = json.loads(chunk_path.read_text(encoding="utf-8"))
        all_rows.extend(chunk["rows"])
    ids = [row["lunation_number"] for row in all_rows]
    if any(key is None for key in ids) or len(set(ids)) != len(ids):
        raise RuntimeError("missing or duplicate lunation identities")
    if any(a["jd_tt"] >= b["jd_tt"] for a, b in zip(all_rows, all_rows[1:])):
        raise RuntimeError("discovery rows are not strictly chronological")
    if (file_hash(kernel) != kernel_hash or source_fingerprint() != fingerprint
            or file_hash(Path(__file__)) != runner_sha):
        raise RuntimeError("kernel or source changed during the run")
    with merged.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(all_rows)
    receipt = {"status": "provisional", "family": "lunar", "mode": "nasa_compat",
               "canon_method": DEFAULT_LUNAR_CANON_METHOD, "row_count": len(all_rows),
               "merged_sha256": file_hash(merged), "source_fingerprint_sha256": fingerprint,
               "kernel_sha256": kernel_hash, "runner_sha256": runner_sha,
               "elapsed_seconds": round(time.monotonic() - started, 2),
               "chunk_hashes": {f"chunk_{i:03d}.json": file_hash(out / f"chunk_{i:03d}.json")
                                for i in range(len(tasks))}, "limits": limits}
    write_json_new(receipt_path, receipt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
