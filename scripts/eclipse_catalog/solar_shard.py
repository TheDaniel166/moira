"""Build provisional solar rows in resumable, provenance-checked shards.

Each generator runs in a subprocess with the current interpreter; no CSV is
shared across workers. The model source must be frozen for the whole run.
Resuming is delegated to generate.py's own metadata check.
"""

import argparse
import concurrent.futures
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path
import moira
from moira._kernel_paths import find_planetary_kernel
from solar_generate import (
    REPO_ROOT,
    discovery_fingerprint,
    has_error,
    package_digest,
    source_fingerprint,
)

HERE = Path(__file__).resolve().parent


def hashfile(path):
    d = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            d.update(block)
    return d.hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--index", type=Path, required=True)
    p.add_argument("--index-receipt", type=Path, required=True)
    p.add_argument("--directory", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--start-year", type=int, default=-1999)
    p.add_argument("--end-year", type=int, default=3000)
    p.add_argument("--shards", type=int, default=20)
    p.add_argument("--jobs", type=int, default=4)
    p.add_argument("--contacts", choices=("yes", "no"), default="yes")
    p.add_argument(
        "--kernel-sha256", required=True, help="expected SHA256 of the ephemeris kernel"
    )
    p.add_argument("--merge-only", action="store_true")
    args = p.parse_args()
    n_years = args.end_year - args.start_year + 1
    if n_years <= 0 or not 1 <= args.shards <= n_years or args.jobs < 1:
        p.error("invalid range, shards or jobs")
    index = args.index.resolve()
    index_receipt = args.index_receipt.resolve()
    directory = args.directory.resolve()
    out = args.output.resolve()
    if any(path == REPO_ROOT or REPO_ROOT in path.parents for path in (directory, out)):
        raise RuntimeError("bulk catalog output must be outside the source checkout")
    if out in (index, index_receipt):
        raise RuntimeError("output would overwrite input")
    directory.mkdir(parents=True, exist_ok=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    meta_out = out.with_suffix(".metadata.json")
    if out.exists() or meta_out.exists():
        raise RuntimeError("merged destination exists; choose a new output")
    kernel = Path(find_planetary_kernel()).resolve()
    kernel_hash = hashfile(kernel)
    if kernel_hash.lower() != args.kernel_sha256.lower():
        raise RuntimeError("kernel SHA256 mismatch")
    index_hash = hashfile(index)
    runner_hash = hashfile(HERE / "solar_generate.py")
    shard_runner_hash = hashfile(Path(__file__))
    receipt_hash = hashfile(index_receipt)
    discovery_receipt = json.loads(index_receipt.read_text(encoding="utf8"))
    if (
        discovery_receipt.get("status") != "provisional"
        or discovery_receipt.get("family") != "solar"
        or discovery_receipt.get("merged_sha256") != index_hash
        or discovery_receipt.get("kernel_sha256") != kernel_hash
        or discovery_receipt.get("source_fingerprint_sha256") != discovery_fingerprint()
    ):
        raise RuntimeError(
            "discovery receipt does not match current index, kernel, or source"
        )
    source_hash = package_digest(Path(moira.__file__).resolve().parent)
    source_state = source_fingerprint()
    kernel_stat = kernel.stat()
    kernel_attestation = {
        "path": str(kernel),
        "size": kernel_stat.st_size,
        "mtime_ns": kernel_stat.st_mtime_ns,
        "sha256": kernel_hash,
    }
    attestation_path = directory / "kernel_attestation.json"
    if attestation_path.exists():
        if (
            json.loads(attestation_path.read_text(encoding="utf8"))
            != kernel_attestation
        ):
            raise RuntimeError("existing kernel attestation differs")
    else:
        with attestation_path.open("x", encoding="utf8") as f:
            f.write(json.dumps(kernel_attestation, indent=2))
    ranges = [
        (
            args.start_year + n_years * i // args.shards,
            args.start_year + n_years * (i + 1) // args.shards - 1,
        )
        for i in range(args.shards)
    ]
    shards = [
        (start, end, directory / f"shard_{i:03d}.csv")
        for i, (start, end) in enumerate(ranges)
    ]

    def run(entry):
        start, end, path = entry
        cmd = [
            sys.executable,
            "-B",
            str(HERE / "solar_generate.py"),
            "--index",
            str(index),
            "--index-receipt",
            str(index_receipt),
            "--output",
            str(path),
            "--start-year",
            str(start),
            "--end-year",
            str(end),
            "--contacts",
            args.contacts,
            "--kernel-sha256",
            kernel_hash,
            "--parent-kernel-attestation",
            str(attestation_path),
            "--resume",
        ]
        with path.with_suffix(".log").open("a", encoding="utf8") as log:
            result = subprocess.run(
                cmd, stdout=log, stderr=subprocess.STDOUT, check=False
            )
        if result.returncode:
            raise RuntimeError(
                f"shard {path.name} failed (exit {result.returncode}); see {path.with_suffix('.log')}"
            )
        print(f"completed {path.name} [{start}, {end}]", flush=True)

    if not args.merge_only:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
            for future in concurrent.futures.as_completed(
                [pool.submit(run, s) for s in shards]
            ):
                future.result()
    with index.open(newline="", encoding="utf8") as f:
        all_events = list(csv.DictReader(f))
    if len(all_events) != discovery_receipt.get("row_count") or any(
        r.get("family") != "solar" for r in all_events
    ):
        raise RuntimeError("discovery count or family differs from receipt")
    all_keys = [int(r["lunation_number"]) for r in all_events]
    if len(all_keys) != len(set(all_keys)):
        raise RuntimeError("duplicate index lunations")
    events = [
        r
        for r in all_events
        if args.start_year <= int(r["year_astronomical"]) <= args.end_year
    ]
    keys = [int(r["lunation_number"]) for r in events]
    if len(keys) != len(set(keys)):
        raise RuntimeError("duplicate index lunations")
    expected = {int(r["lunation_number"]): int(r["year_astronomical"]) for r in events}
    seen = {}
    schema = None
    canonical = None
    metadata = []
    for start, end, path in shards:
        mpath = path.with_suffix(".metadata.json")
        m = json.loads(mpath.read_text(encoding="utf8"))
        if (
            m["range"] != [start, end]
            or m["lunations"] is not None
            or m["contacts"] != args.contacts
        ):
            raise RuntimeError(f"shard options mismatch: {path}")
        if (
            m["event_index_sha256"] != index_hash
            or m["event_index_receipt_sha256"] != receipt_hash
            or m["runner_sha256"] != runner_hash
            or m["engine_package_sha256"] != source_hash
            or m["native_source_sha256"] != source_state["native_source_sha256"]
        ):
            raise RuntimeError(
                f"index, runner, or package fingerprint mismatch: {path}"
            )
        if Path(m["kernel_path"]).resolve() != kernel:
            raise RuntimeError(f"kernel path mismatch: {path}")
        comparable = {k: v for k, v in m.items() if k not in ("range", "lunations")}
        if canonical is None:
            canonical = comparable
        elif comparable != canonical:
            raise RuntimeError(f"engine, runner, input or environment mismatch: {path}")
        with path.open(newline="", encoding="utf8") as f:
            reader = csv.DictReader(f)
            if schema is None:
                schema = reader.fieldnames
            elif schema != reader.fieldnames:
                raise RuntimeError(f"schema mismatch: {path}")
            for row in reader:
                key = int(row["lunation_number"])
                if key in seen:
                    raise RuntimeError(f"duplicate row: {key}")
                if key not in expected or not start <= expected[key] <= end:
                    raise RuntimeError(f"out of range row: {key}")
                if None in row or any(v is None for v in row.values()):
                    raise RuntimeError(f"truncated row: {key}")
                if has_error(row):
                    raise RuntimeError(f"computation error for lunation {key}")
                seen[key] = row
        metadata.append(
            {"path": str(path), "sha256": hashfile(path), "range": [start, end]}
        )
    missing = set(expected) - seen.keys()
    if missing:
        raise RuntimeError(
            f"{len(missing)} missing index rows; first {sorted(missing)[:10]}"
        )
    with out.open("x", newline="", encoding="utf8") as f:
        writer = csv.DictWriter(f, fieldnames=schema)
        writer.writeheader()
        writer.writerows(seen[k] for k in keys)
    if (
        hashfile(kernel) != kernel_hash
        or hashfile(index) != index_hash
        or hashfile(index_receipt) != receipt_hash
        or hashfile(HERE / "solar_generate.py") != runner_hash
        or hashfile(Path(__file__)) != shard_runner_hash
        or source_fingerprint() != source_state
        or discovery_fingerprint() != discovery_receipt["source_fingerprint_sha256"]
    ):
        raise RuntimeError(
            "kernel, index, runner, or package changed during generation"
        )
    output_meta = {
        "common": canonical,
        "kernel_sha256": kernel_hash,
        "range": [args.start_year, args.end_year],
        "row_count": len(keys),
        "shards": metadata,
        "merged_sha256": hashfile(out),
        "shard_runner_sha256": shard_runner_hash,
        "interpretation": "Provisional research output; P5 acceptance remains open. Merged only after index and matching provenance checks; scientific accuracy requires separate validation.",
    }
    with meta_out.open("x", encoding="utf8") as f:
        f.write(json.dumps(output_meta, indent=2))
    print(
        json.dumps(
            {
                "rows": len(keys),
                "output": str(out),
                "sha256": output_meta["merged_sha256"],
            }
        )
    )


if __name__ == "__main__":
    main()
