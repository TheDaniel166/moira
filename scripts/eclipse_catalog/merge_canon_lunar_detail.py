"""Merge validated provisional NASA-compatible lunar-detail shards safely.

Merging establishes integrity and complete accounting relative to the named
discovery index. It does not certify discovery, contacts, or physical accuracy.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path

import discovery
import canon_lunar_detail as lunar


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--index-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--kernel-sha256", required=True)
    parser.add_argument("--shard", type=Path, action="append", required=True)
    args = parser.parse_args(argv)

    index, index_receipt, output = (p.resolve() for p in (args.index, args.index_receipt, args.output))
    shards = [p.resolve() for p in args.shard]
    if len(set(shards)) != len(shards):
        raise ValueError("repeated shard path")
    if output.is_relative_to(lunar.ROOT) or not output.parent.is_dir():
        raise ValueError("output directory must exist outside the source checkout")
    finish = output.with_suffix(output.suffix + ".receipt.json")
    inputs = {index, index_receipt, *shards}
    for shard in shards:
        inputs.update(shard.with_suffix(shard.suffix + ext) for ext in (
            ".metadata.json", ".receipt.json", ".journal.jsonl"))
    if {output, finish} & inputs:
        raise ValueError("a merge output would overwrite an input")
    if output.exists() or finish.exists():
        raise FileExistsError("merge output or receipt already exists")

    kernel_value = lunar.find_planetary_kernel()
    if kernel_value is None:
        raise RuntimeError("planetary kernel unavailable")
    kernel = Path(kernel_value).resolve()
    kernel_hash = lunar.sha256(kernel)
    if kernel_hash.lower() != args.kernel_sha256.lower():
        raise ValueError("kernel SHA-256 mismatch")
    index_hash, receipt_hash = lunar.sha256(index), lunar.sha256(index_receipt)
    detail_source, discovery_source = lunar.source_digest(), discovery.source_fingerprint()
    reference = json.loads(index_receipt.read_text(encoding="utf-8"))
    full_index = lunar.read_index(index, 0, 1)
    if (reference.get("status") != "provisional" or reference.get("family") != "lunar"
            or reference.get("mode") != "nasa_compat"
            or reference.get("runner_sha256") != lunar.sha256(Path(__file__).with_name("canon_discovery.py"))
            or reference.get("merged_sha256") != index_hash
            or reference.get("kernel_sha256") != kernel_hash
            or reference.get("source_fingerprint_sha256") != discovery_source
            or reference.get("row_count") != len(full_index)):
        raise ValueError("discovery receipt does not match index, source and kernel")

    expected = {int(row["lunation_number"]): row for row in full_index}
    merged = {}
    shard_numbers = set()
    shard_count = len(shards)
    records = []
    for shard in shards:
        meta_path = shard.with_suffix(shard.suffix + ".metadata.json")
        done_path = shard.with_suffix(shard.suffix + ".receipt.json")
        journal_path = shard.with_suffix(shard.suffix + ".journal.jsonl")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        done = json.loads(done_path.read_text(encoding="utf-8"))
        if (meta.get("schema") != "moira-nasa-compat-lunar-detailed-shard-v1"
                or meta.get("index") != str(index) or meta.get("index_sha256") != index_hash
                or meta.get("index_receipt") != str(index_receipt)
                or meta.get("index_receipt_sha256") != receipt_hash
                or meta.get("kernel_sha256") != kernel_hash
                or meta.get("source_sha256") != detail_source
                or meta.get("discovery_source_sha256") != discovery_source
                or meta.get("shard_count") != shard_count
                or not isinstance(meta.get("shard_index"), int)):
            raise ValueError(f"shard metadata mismatch: {shard}")
        number = meta["shard_index"]
        if not 0 <= number < shard_count or number in shard_numbers:
            raise ValueError("invalid or repeated shard index")
        shard_numbers.add(number)
        shard_hash, journal_hash = lunar.sha256(shard), lunar.sha256(journal_path)
        if (done.get("provisional") is not True or done.get("complete_without_row_errors") is not True
                or done.get("error_lunations") != [] or done.get("output_sha256") != shard_hash
                or done.get("journal_sha256") != journal_hash
                or done.get("kernel_sha256") != kernel_hash or done.get("source_sha256") != detail_source):
            raise ValueError(f"incomplete, failed, or altered shard: {shard}")
        expected_for_shard = {int(row["lunation_number"]) for row in lunar.read_index(index, number, shard_count)}
        if meta.get("selected_rows") != len(expected_for_shard) or done.get("row_count") != len(expected_for_shard):
            raise ValueError("shard count does not match index partition")
        with shard.open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            if tuple(reader.fieldnames or ()) != lunar.FIELDS:
                raise ValueError("unexpected lunar shard schema")
            rows = list(reader)
        ids = [int(row["lunation_number"]) for row in rows]
        if len(ids) != len(set(ids)) or set(ids) != expected_for_shard:
            raise ValueError("shard missing, repeating or misplacing lunations")
        for key, row in zip(ids, rows):
            if key in merged or row["status"] != "ok" or row["error"]:
                raise ValueError("shard has duplicate identity or error status")
            if int(row["catalog_index"]) != expected[key]["_catalog_index"]:
                raise ValueError("shard catalog order does not match discovery")
            merged[key] = row
        records.append({"path": str(shard), "sha256": shard_hash,
                        "metadata_sha256": lunar.sha256(meta_path),
                        "receipt_sha256": lunar.sha256(done_path), "journal_sha256": journal_hash,
                        "shard_index": number, "rows": len(rows)})
    if set(merged) != set(expected) or shard_numbers != set(range(shard_count)):
        raise ValueError("shards do not account for every discovery event")
    if (lunar.sha256(kernel) != kernel_hash or lunar.sha256(index) != index_hash
            or lunar.sha256(index_receipt) != receipt_hash or lunar.source_digest() != detail_source
            or discovery.source_fingerprint() != discovery_source
            or lunar.sha256(Path(__file__).with_name("canon_discovery.py")) != reference["runner_sha256"]):
        raise RuntimeError("inputs changed during merge")
    with output.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=lunar.FIELDS)
        writer.writeheader()
        writer.writerows(merged[int(row["lunation_number"])] for row in full_index)
        stream.flush()
        os.fsync(stream.fileno())
    if (lunar.sha256(kernel) != kernel_hash or lunar.sha256(index) != index_hash
            or lunar.sha256(index_receipt) != receipt_hash or lunar.source_digest() != detail_source
            or discovery.source_fingerprint() != discovery_source
            or lunar.sha256(Path(__file__).with_name("canon_discovery.py")) != reference["runner_sha256"]):
        raise RuntimeError("inputs changed during output writing; no receipt was issued")
    for record in records:
        shard = Path(record["path"])
        if (lunar.sha256(shard) != record["sha256"]
                or lunar.sha256(shard.with_suffix(shard.suffix + ".metadata.json")) != record["metadata_sha256"]
                or lunar.sha256(shard.with_suffix(shard.suffix + ".receipt.json")) != record["receipt_sha256"]
                or lunar.sha256(shard.with_suffix(shard.suffix + ".journal.jsonl")) != record["journal_sha256"]):
            raise RuntimeError("shard inputs changed during output writing; no receipt was issued")
    receipt = {"schema": "moira-nasa-compat-lunar-detail-merge-v1", "mode": "nasa_compat", "provisional": True,
               "output_sha256": lunar.sha256(output), "row_count": len(merged),
               "index": str(index), "index_sha256": index_hash, "index_receipt_sha256": receipt_hash,
               "kernel_sha256": kernel_hash, "source_sha256": detail_source,
               "discovery_source_sha256": discovery_source, "merger_sha256": lunar.sha256(Path(__file__)),
               "shards": sorted(records, key=lambda record: record["shard_index"]),
               "limits": "Complete only relative to canon discovery index; missing contacts are not certified absence. Margins are at canon greatest-axis epoch. NASA compatibility is not exact NASA-model parity."}
    with finish.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"provisional": True, "rows": len(merged), "output": str(output)}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
