"""Refresh solution-drifted comets without refetching unchanged catalog bodies.

This consumes a completed ``audit_comet_solution_freshness.py`` report.  It
copies the source catalog into a new directory, reads unchanged Type-13 node
tables from their existing shards, fetches and certifies only stale bodies, and
re-emits each affected shard.  The source catalog is never modified.

Every replacement body must still match the solution identity reported by the
audit.  The comet builder also checks that every refinement response matches
the base response, so source changes during a refresh fail closed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from moira._spk_body_kernel import SmallBodyKernel  # noqa: E402
from moira.daf_writer import write_spk_type13  # noqa: E402
from scripts import build_comet_catalog as builder  # noqa: E402
from scripts.audit_comet_solution_freshness import SCHEMA as AUDIT_SCHEMA  # noqa: E402


RECEIPT_SCHEMA = "moira.comet-solution-refresh/v1"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            json.dump(payload, stream, indent=2)
            stream.write("\n")
        temporary.replace(path)
    except Exception:
        if temporary is not None and temporary.exists():
            temporary.unlink()
        raise


def _copy_file_without_mutating_source(source: Path, destination: Path) -> None:
    if destination.exists():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.suffix == ".bsp":
        try:
            os.link(source, destination)
            return
        except OSError:
            pass
    shutil.copy2(source, destination)


def _clone_catalog_top_level(source_dir: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for source in sorted(source_dir.iterdir()):
        if source.is_file() and (
            source.name in {"manifest.json", "comet_master.json"}
            or source.name.startswith(builder.SHARD_PREFIX + "_")
        ):
            _copy_file_without_mutating_source(source, output_dir / source.name)


def _load_audit(path: Path) -> tuple[dict, dict[int, str]]:
    audit = json.loads(path.read_text(encoding="utf-8"))
    if audit.get("schema") != AUDIT_SCHEMA or not audit.get("completed"):
        raise ValueError("solution audit must be a completed freshness report")
    summary = audit.get("summary") or {}
    if int(summary.get("error", -1)) != 0:
        raise ValueError("solution audit contains authority-query errors")
    stale: dict[int, str] = {}
    for record in audit.get("records", []):
        if record.get("status") != "stale":
            continue
        number = int(record["number"])
        solution = record.get("current_target_solution")
        if not solution:
            raise ValueError(f"stale audit record {number} lacks current solution")
        stale[number] = str(solution)
    if not stale:
        raise ValueError("solution audit contains no stale bodies to refresh")
    return audit, stale


def _extract_shard_bodies(
    kernel_path: Path,
    records: list[dict[str, object]],
) -> dict[int, dict[str, object]]:
    records_by_naif = {int(record["naif_id"]): record for record in records}
    kernel = SmallBodyKernel(kernel_path)
    try:
        bodies: dict[int, dict[str, object]] = {}
        for segment in kernel._kernel.segments:
            if int(segment.data_type) != 13:
                raise RuntimeError(
                    f"{kernel_path.name} contains non-Type-13 segment "
                    f"{segment.data_type}"
                )
            naif_id = int(segment.target)
            if naif_id not in records_by_naif:
                raise RuntimeError(
                    f"{kernel_path.name} segment {naif_id} is absent from metadata"
                )
            states, epochs_jd, window_size = segment._data
            record = records_by_naif[naif_id]
            bodies[naif_id] = {
                "naif_id": naif_id,
                "name": str(record["name"]),
                "center": int(segment.center),
                "frame": int(segment.frame),
                "states": [list(axis) for axis in states],
                "epochs_jd": list(epochs_jd),
                "window_size": int(window_size),
            }
    finally:
        kernel.close()
    if set(bodies) != set(records_by_naif):
        raise RuntimeError(f"{kernel_path.name} body roster disagrees with metadata")
    return bodies


def _record_from_body(
    original: dict[str, object],
    body: dict[str, object],
    *,
    fetch_seconds: float,
) -> dict[str, object]:
    return {
        "number": int(original["number"]),
        "naif_id": int(body["naif_id"]),
        "name": str(body["name"]),
        "full_name": original.get("full_name"),
        "nodes": len(body["epochs_jd"]),
        "clamped": bool(body["clamped"]),
        "start": body["start"],
        "stop": body["stop"],
        "fetch_s": round(fetch_seconds, 1),
        "target_solution": body["target_solution"],
        "sampling_policy": body["sampling_policy"],
        "base_nodes": body["base_nodes"],
        "adaptive_nodes": body["adaptive_nodes"],
        "extremum_brackets": body["extremum_brackets"],
        "apsidal_sampling_certificate": body["apsidal_sampling_certificate"],
        "response_receipts": body["response_receipts"],
    }


def _refresh_shard(
    output_dir: Path,
    metadata_path: Path,
    expected_solutions: dict[int, str],
) -> list[dict[str, object]]:
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    records = metadata["records"]
    selected = {
        int(record["number"]): expected_solutions[int(record["number"])]
        for record in records
        if int(record["number"]) in expected_solutions
    }
    if not selected:
        return []
    if all(
        record.get("target_solution") == selected.get(int(record["number"]))
        for record in records
        if int(record["number"]) in selected
    ):
        print(f"=== shard {metadata['shard']:03d}: SKIP (already refreshed) ===")
        return [record for record in records if int(record["number"]) in selected]

    kernel_path = output_dir / metadata["kernel"]
    bodies = _extract_shard_bodies(kernel_path, records)
    records_by_number = {int(record["number"]): record for record in records}
    refreshed: list[dict[str, object]] = []
    for number, expected_solution in sorted(selected.items()):
        started = time.perf_counter()
        body = builder._fetch_comet(number)
        elapsed = time.perf_counter() - started
        if body["target_solution"] != expected_solution:
            raise RuntimeError(
                f"{number}P solution advanced after audit: expected "
                f"{expected_solution!r}, fetched {body['target_solution']!r}"
            )
        bodies[int(body["naif_id"])] = body
        replacement = _record_from_body(
            records_by_number[number],
            body,
            fetch_seconds=elapsed,
        )
        records_by_number[number] = replacement
        refreshed.append(replacement)
        print(
            f"  [REFRESH] {number:>4}P {body['target_solution']} "
            f"nodes={len(body['epochs_jd'])} {elapsed:.1f}s",
            flush=True,
        )
        if builder.THROTTLE_S:
            time.sleep(builder.THROTTLE_S)

    ordered_records = [records_by_number[int(record["number"])] for record in records]
    ordered_bodies = [bodies[int(record["naif_id"])] for record in ordered_records]
    writable = [
        {
            key: body[key]
            for key in (
                "naif_id",
                "name",
                "center",
                "frame",
                "states",
                "epochs_jd",
                "window_size",
            )
        }
        for body in ordered_bodies
    ]
    temporary_kernel = kernel_path.with_name(f".{kernel_path.name}.refresh.tmp")
    write_spk_type13(
        temporary_kernel,
        bodies=writable,
        locifn="MOIRA COMET CATALOG",
    )
    check = SmallBodyKernel(temporary_kernel)
    try:
        for record in refreshed:
            body = bodies[int(record["naif_id"])]
            record["max_node_error_km"] = builder._verify(
                check,
                int(record["naif_id"]),
                body["epochs_jd"],
                body["states"],
            )
    finally:
        check.close()

    metadata["records"] = ordered_records
    metadata["failures"] = []
    metadata["kernel_bytes"] = temporary_kernel.stat().st_size
    metadata["naif_map"] = {
        str(record["name"]): int(record["naif_id"])
        for record in ordered_records
    }
    temporary_metadata = metadata_path.with_name(f".{metadata_path.name}.refresh.tmp")
    _atomic_write_json(temporary_metadata, metadata)
    temporary_kernel.replace(kernel_path)
    temporary_metadata.replace(metadata_path)
    print(
        f"=== shard {metadata['shard']:03d}: {len(refreshed)} refreshed, "
        f"{len(records) - len(refreshed)} preserved ===",
        flush=True,
    )
    return refreshed


def _rebuild_master(output_dir: Path, source_master: dict) -> dict:
    records: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []
    for metadata_path in sorted(
        output_dir.glob(f"{builder.SHARD_PREFIX}_*.metadata.json")
    ):
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        records.extend(metadata["records"])
        failures.extend(metadata.get("failures", []))
    records.sort(key=lambda record: int(record["number"]))
    master = dict(source_master)
    master["requested"] = len(records) + len(failures)
    master["built"] = len(records)
    master["failed"] = len(failures)
    master["records"] = records
    master["failures"] = failures
    master["naif_map"] = {
        str(record["name"]): int(record["naif_id"])
        for record in records
    }
    _atomic_write_json(output_dir / "comet_master.json", master)
    builder._write_manifest(output_dir)
    return master


def refresh_catalog(
    source_dir: Path,
    output_dir: Path,
    audit_path: Path,
    *,
    response_cache_dir: Path | None = None,
) -> dict:
    source_dir = source_dir.resolve()
    output_dir = output_dir.resolve()
    if source_dir == output_dir:
        raise ValueError("refresh output must differ from the source catalog")
    source_master_path = source_dir / "comet_master.json"
    if not source_master_path.exists():
        raise FileNotFoundError(f"source catalog lacks {source_master_path.name}")
    audit, stale = _load_audit(audit_path)
    if audit.get("catalog_master_sha256") != _sha256_file(source_master_path):
        raise ValueError("solution audit is not bound to the source catalog master")
    _clone_catalog_top_level(source_dir, output_dir)

    old_cache = builder.RESPONSE_CACHE_DIR
    builder.RESPONSE_CACHE_DIR = response_cache_dir or (
        output_dir
        / ".horizons-cache"
        / f"{builder.HORIZONS_REQUEST_CACHE_VERSION}-solution-refresh"
    )
    refreshed: list[dict[str, object]] = []
    try:
        for metadata_path in sorted(
            output_dir.glob(f"{builder.SHARD_PREFIX}_*.metadata.json")
        ):
            refreshed.extend(_refresh_shard(output_dir, metadata_path, stale))
    finally:
        builder.RESPONSE_CACHE_DIR = old_cache

    if {int(record["number"]) for record in refreshed} != set(stale):
        missing = sorted(set(stale) - {int(record["number"]) for record in refreshed})
        raise RuntimeError(f"refresh did not replace every stale comet: {missing}")
    source_master = json.loads(source_master_path.read_text(encoding="utf-8"))
    master = _rebuild_master(output_dir, source_master)
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "source_catalog": str(source_dir),
        "source_comet_master_sha256": _sha256_file(source_master_path),
        "authority_audit": str(audit_path.resolve()),
        "authority_audit_sha256": _sha256_file(audit_path),
        "refreshed_body_count": len(refreshed),
        "refreshed_numbers": sorted(int(record["number"]) for record in refreshed),
        "affected_shards": sorted(
            {
                int(path.stem.split("_")[-1].split(".")[0])
                for path in output_dir.glob(
                    f"{builder.SHARD_PREFIX}_*.metadata.json"
                )
                if any(
                    int(record["number"]) in stale
                    for record in json.loads(path.read_text(encoding="utf-8"))[
                        "records"
                    ]
                )
            }
        ),
        "output_comet_master_sha256": _sha256_file(
            output_dir / "comet_master.json"
        ),
        "output_manifest_sha256": _sha256_file(output_dir / "manifest.json"),
    }
    _atomic_write_json(output_dir / "solution-refresh-receipt.json", receipt)
    return {"master": master, "receipt": receipt}


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("audit", type=Path)
    parser.add_argument("--response-cache-dir", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = refresh_catalog(
        args.source_dir,
        args.output_dir,
        args.audit,
        response_cache_dir=args.response_cache_dir,
    )
    receipt = result["receipt"]
    print(
        "DONE: "
        f"{receipt['refreshed_body_count']} bodies refreshed across "
        f"{len(receipt['affected_shards'])} shards",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
