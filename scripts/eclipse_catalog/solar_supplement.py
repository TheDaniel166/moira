"""Resumable provisional native solar hybrid and instantaneous-cap evidence.

This validation pass adds no swept path or catalog width. A hybrid witness is
constructive; unresolved does not mean non-hybrid or eclipse absence. A cap
candidate is sampled and does not certify complete intersection topology.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
import json
import math
import os
import re
import sys
import time
from pathlib import Path

os.environ["MOIRA_NO_DOWNLOAD"] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import moira
from moira._kernel_paths import find_planetary_kernel
from moira.eclipse import EclipseCalculator, EclipseEvent
from moira.solar_eclipse_clipped import inspect_instantaneous_clipped_central_boundary
from moira.solar_eclipse_hybrid import classify_solar_central_path
from moira.spk_reader import SpkReader

from solar_generate import REPO_ROOT, discovery_fingerprint, sha256, source_fingerprint


def write_new_json(path: Path, value: object) -> None:
    """Write exclusively; interrupted JSON is rejected on the next resume."""
    with path.open("x", encoding="utf8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def inspect_event(
    calc, row: dict[str, str], arc_samples: int, max_evaluations: int
) -> dict:
    """Recompute one detailed row's hybrid witnesses and instantaneous cap."""
    started = time.perf_counter()
    key = int(row["lunation_number"])
    result = {
        "lunation_number": key,
        "source_jd_ut1": row["jd_ut1"],
        "hybrid_status": "error",
        "cap_status": "error",
    }
    try:
        if row["status"] != "ok":
            raise ValueError("detailed input row is not successful")
        jd = float(row["jd_ut1"])
        if not math.isfinite(jd):
            raise ValueError("event epoch is nonfinite")
        data = calc.calculate_jd(jd)
        if not data.is_solar_eclipse or data.saros_lunation_number != key:
            raise ValueError("detailed row and recalculated event identity differ")
        event = EclipseEvent(jd_ut=jd, data=data)
        hybrid = classify_solar_central_path(
            calc, event, max_evaluations=max_evaluations
        )
        result.update(
            hybrid_status=hybrid.status,
            hybrid_reason=hybrid.reason,
            hybrid_axis_interval=hybrid.axis_interval,
            hybrid_annular_witness=(
                asdict(hybrid.annular_witness) if hybrid.annular_witness else None
            ),
            hybrid_total_witness=(
                asdict(hybrid.total_witness) if hybrid.total_witness else None
            ),
            hybrid_transitions=[asdict(item) for item in hybrid.transitions],
            hybrid_evaluation_count=hybrid.evaluation_count,
            hybrid_budget_exhausted=hybrid.budget_exhausted,
            hybrid_transition_list_complete=False,
            hybrid_subtype=hybrid.subtype,
        )
        cap = inspect_instantaneous_clipped_central_boundary(
            calc, jd, arc_samples=arc_samples
        )
        boundary = cap.boundary
        result.update(
            cap_status=cap.status,
            cap_reason=cap.reason,
            cap_complete=cap.complete,
            cap_topology=boundary.topology if boundary else None,
            cap_cone_sample_count=len(boundary.cone_arc) if boundary else None,
            cap_horizon_sample_count=len(boundary.horizon_arc) if boundary else None,
        )
    except Exception as exc:
        # This is an explicit failure ledger, not a scientific absence result.
        result.update(status="error", error=f"{type(exc).__name__}: {exc}")
    else:
        result.update(status="ok", error=None)
    result["elapsed_seconds"] = round(time.perf_counter() - started, 4)
    return result


def main(argv: list[str] | None = None) -> int:
    """Compute or resume event chunks and emit an independently bound receipt."""
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--detail", type=Path, required=True)
    p.add_argument("--detail-receipt", type=Path, required=True)
    p.add_argument("--directory", type=Path, required=True)
    p.add_argument("--kernel-sha256", required=True)
    p.add_argument("--chunk-size", type=int, default=100)
    p.add_argument("--arc-samples", type=int, default=65)
    p.add_argument("--max-evaluations", type=int, default=512)
    p.add_argument("--resume", action="store_true")
    p.add_argument(
        "--retry-errors",
        action="store_true",
        help="retry failed rows as a new immutable chunk version",
    )
    args = p.parse_args(argv)
    if args.chunk_size < 1 or args.arc_samples < 3 or args.max_evaluations < 1:
        p.error("chunk size, arc samples, or evaluation budget is invalid")
    if args.retry_errors and not args.resume:
        p.error("--retry-errors requires --resume")
    detail, detail_receipt, out = (
        args.detail.resolve(),
        args.detail_receipt.resolve(),
        args.directory.resolve(),
    )
    if out == REPO_ROOT or REPO_ROOT in out.parents:
        raise ValueError("bulk evidence must be written outside the source checkout")
    out.mkdir(parents=True, exist_ok=True)
    if detail.parent == out or detail_receipt.parent == out:
        raise ValueError("supplement output must not share an input directory")
    meta_path, result_path, receipt_path = (
        out / "metadata.json",
        out / "solar_supplement.jsonl",
        out / "receipt.json",
    )
    if result_path.exists() or receipt_path.exists():
        raise RuntimeError("completed output exists; choose a new directory")
    kernel = Path(find_planetary_kernel()).resolve()
    kernel_hash = sha256(kernel)
    if kernel_hash != args.kernel_sha256:
        raise RuntimeError("kernel hash mismatch")
    detail_hash, detail_receipt_hash = sha256(detail), sha256(detail_receipt)
    source = source_fingerprint()
    discovery_hash = discovery_fingerprint()
    detail_meta = json.loads(detail_receipt.read_text(encoding="utf8"))
    common = detail_meta["common"]
    if (
        detail_meta["merged_sha256"] != detail_hash
        or detail_meta["kernel_sha256"] != kernel_hash
        or any(common.get(k) != v for k, v in source.items())
    ):
        raise RuntimeError(
            "detail receipt does not match detail, kernel, or current source"
        )
    discovery_receipt = Path(common["event_index_receipt"])
    if sha256(discovery_receipt) != common["event_index_receipt_sha256"]:
        raise RuntimeError("detail discovery receipt changed")
    discovery_meta = json.loads(discovery_receipt.read_text(encoding="utf8"))
    if discovery_meta.get("source_fingerprint_sha256") != discovery_hash:
        raise RuntimeError("current discovery source differs from detailed input")
    with detail.open(newline="", encoding="utf8") as stream:
        rows = list(csv.DictReader(stream))
    keys = [int(row["lunation_number"]) for row in rows]
    if (
        len(rows) != detail_meta["row_count"]
        or len(keys) != len(set(keys))
        or any(row["status"] != "ok" for row in rows)
    ):
        raise RuntimeError("detailed input has bad count, duplicate identity, or error")
    meta = {
        "schema": "moira-provisional-solar-evidence-v1",
        "status": "provisional",
        "engine_version": moira.__version__,
        "detail": str(detail),
        "detail_sha256": detail_hash,
        "detail_receipt": str(detail_receipt),
        "detail_receipt_sha256": detail_receipt_hash,
        "source": source,
        "discovery_source_sha256": discovery_hash,
        "supplement_runner_sha256": sha256(Path(__file__)),
        "kernel": str(kernel),
        "kernel_sha256": kernel_hash,
        "chunk_size": args.chunk_size,
        "arc_samples": args.arc_samples,
        "max_evaluations": args.max_evaluations,
        "model": "native; WGS84; geometric unrefracted Sun-center horizon; UT1",
        "limitations": "Witnesses and sampled instantaneous cap candidates; no complete central-path topology, swept path, or catalog-width claim.",
    }
    if meta_path.exists():
        if not args.resume or json.loads(meta_path.read_text(encoding="utf8")) != meta:
            raise RuntimeError(
                "existing metadata requires an exactly matching explicit resume"
            )
    else:
        if any(out.iterdir()):
            raise RuntimeError("new supplement directory is not empty")
        write_new_json(meta_path, meta)
    failures, merged, chunk_hashes = [], [], {}
    started = time.perf_counter()
    with SpkReader(kernel) as reader:
        calc = EclipseCalculator(reader=reader)
        for offset in range(0, len(rows), args.chunk_size):
            subset = rows[offset : offset + args.chunk_size]
            prefix = f"chunk_{offset // args.chunk_size:05d}"
            chunk = out / f"{prefix}.json"
            retry_pattern = re.compile(re.escape(prefix) + r"\.retry_([0-9]{5})\.json$")
            retry_files = sorted(
                path
                for path in out.glob(f"{prefix}.retry_*.json")
                if retry_pattern.fullmatch(path.name)
            )
            versions = ([chunk] if chunk.exists() else []) + retry_files
            if retry_files and not chunk.exists():
                raise RuntimeError("retry chunk exists without initial chunk")
            for version in versions:
                chunk_receipt = version.with_suffix(".receipt.json")
                if not chunk_receipt.exists():
                    raise RuntimeError("resumed chunk has no integrity receipt")
                recorded = json.loads(chunk_receipt.read_text(encoding="utf8"))
                if recorded != {
                    "chunk_sha256": sha256(version),
                    "metadata_sha256": sha256(meta_path),
                }:
                    raise RuntimeError("resumed chunk fingerprint differs")
                candidate = json.loads(version.read_text(encoding="utf8"))
                if [item["lunation_number"] for item in candidate] != [
                    int(row["lunation_number"]) for row in subset
                ]:
                    raise RuntimeError("resumed chunk identity differs from input")
                saved = candidate
            if not versions:
                chunk_receipt = chunk.with_suffix(".receipt.json")
                if chunk_receipt.exists():
                    raise RuntimeError("chunk receipt exists without its chunk")
                saved = [
                    inspect_event(calc, row, args.arc_samples, args.max_evaluations)
                    for row in subset
                ]
                write_new_json(chunk, saved)
                write_new_json(
                    chunk_receipt,
                    {
                        "chunk_sha256": sha256(chunk),
                        "metadata_sha256": sha256(meta_path),
                    },
                )
            elif args.retry_errors and any(item["status"] != "ok" for item in saved):
                # Preserve every failed version for audit; retry only failed rows.
                by_key = {int(row["lunation_number"]): row for row in subset}
                saved = [
                    inspect_event(
                        calc,
                        by_key[item["lunation_number"]],
                        args.arc_samples,
                        args.max_evaluations,
                    )
                    if item["status"] != "ok"
                    else item
                    for item in saved
                ]
                chunk = out / f"{prefix}.retry_{len(retry_files) + 1:05d}.json"
                chunk_receipt = chunk.with_suffix(".receipt.json")
                write_new_json(chunk, saved)
                write_new_json(
                    chunk_receipt,
                    {
                        "chunk_sha256": sha256(chunk),
                        "metadata_sha256": sha256(meta_path),
                    },
                )
                versions.append(chunk)
            else:
                chunk = versions[-1]
            failures.extend(
                item["lunation_number"] for item in saved if item["status"] != "ok"
            )
            merged.extend(saved)
            for version in versions or [chunk]:
                chunk_hashes[version.name] = sha256(version)
            print(
                json.dumps(
                    {
                        "completed": len(merged),
                        "total": len(rows),
                        "errors": len(failures),
                        "elapsed_seconds": round(time.perf_counter() - started, 2),
                    }
                ),
                flush=True,
            )
    if (
        sha256(kernel) != kernel_hash
        or sha256(detail) != detail_hash
        or sha256(detail_receipt) != detail_receipt_hash
        or source_fingerprint() != source
        or discovery_fingerprint() != discovery_hash
        or sha256(Path(__file__)) != meta["supplement_runner_sha256"]
    ):
        raise RuntimeError("kernel, input, or source changed during supplement")
    if failures:
        raise RuntimeError(
            f"{len(failures)} evidence rows have computation errors: {failures[:10]}"
        )
    with result_path.open("x", encoding="utf8") as stream:
        for item in merged:
            stream.write(json.dumps(item, sort_keys=True, allow_nan=False) + "\n")
    write_new_json(
        receipt_path,
        {
            "status": "provisional",
            "row_count": len(merged),
            "merged_sha256": sha256(result_path),
            "chunk_sha256": chunk_hashes,
            "metadata_sha256": sha256(meta_path),
            "detail_sha256": detail_hash,
            "kernel_sha256": kernel_hash,
            "limits": meta["limitations"],
        },
    )
    print(
        json.dumps(
            {
                "rows": len(merged),
                "output": str(result_path),
                "sha256": sha256(result_path),
            }
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
