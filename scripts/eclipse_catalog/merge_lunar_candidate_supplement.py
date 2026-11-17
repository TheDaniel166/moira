"""Merge provisional lunar candidate shards without certifying their searches."""
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path

import discovery
import lunar_candidate_supplement as candidates
import lunar_detail as lunar


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--index-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--kernel-sha256", required=True)
    parser.add_argument("--shard", type=Path, action="append", required=True)
    args = parser.parse_args(argv)
    index, index_receipt, output = (path.resolve() for path in (args.index, args.index_receipt, args.output))
    shards = [path.resolve() for path in args.shard]
    if len(set(shards)) != len(shards):
        raise ValueError("repeated shard path")
    if output.is_relative_to(lunar.ROOT) or not output.parent.is_dir():
        raise ValueError("output parent must exist outside the checkout")
    finish = output.with_suffix(output.suffix + ".receipt.json")
    inputs = {index, index_receipt, *shards}
    for shard in shards:
        inputs.update(shard.with_suffix(shard.suffix + suffix) for suffix in
                      (".metadata.json", ".receipt.json", ".journal.jsonl"))
    if {output, finish} & inputs:
        raise ValueError("an output would overwrite an input")
    if output.exists() or finish.exists():
        raise FileExistsError("output or receipt already exists")
    kernel_value = lunar.find_planetary_kernel()
    if kernel_value is None:
        raise RuntimeError("planetary kernel unavailable")
    kernel = Path(kernel_value).resolve()
    kernel_hash = lunar.sha256(kernel)
    if kernel_hash.lower() != args.kernel_sha256.lower():
        raise ValueError("kernel SHA-256 mismatch")
    index_hash, receipt_hash = lunar.sha256(index), lunar.sha256(index_receipt)
    source_hash, discovery_hash = lunar.source_digest(), discovery.source_fingerprint()
    runner_hash = lunar.sha256(Path(candidates.__file__))
    reference = json.loads(index_receipt.read_text(encoding="utf-8"))
    full_index = lunar.read_index(index, 0, 1)
    if (reference.get("status") != "provisional" or reference.get("family") != "lunar"
            or reference.get("merged_sha256") != index_hash or reference.get("row_count") != len(full_index)
            or reference.get("kernel_sha256") != kernel_hash
            or reference.get("source_fingerprint_sha256") != discovery_hash):
        raise ValueError("discovery receipt does not match index, source and kernel")
    expected = {(int(row["lunation_number"]), policy): row for row in full_index for policy in candidates.POLICIES}
    merged, numbers, records = {}, set(), []
    shard_count = len(shards)
    uniform = None
    for shard in shards:
        meta_path = shard.with_suffix(shard.suffix + ".metadata.json")
        done_path = shard.with_suffix(shard.suffix + ".receipt.json")
        journal_path = shard.with_suffix(shard.suffix + ".journal.jsonl")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        done = json.loads(done_path.read_text(encoding="utf-8"))
        if (meta.get("schema") != "moira-lunar-candidate-supplement-shard-v1"
                or meta.get("index") != str(index) or meta.get("index_sha256") != index_hash
                or meta.get("index_receipt") != str(index_receipt) or meta.get("index_receipt_sha256") != receipt_hash
                or meta.get("kernel_sha256") != kernel_hash or meta.get("source_sha256") != source_hash
                or meta.get("discovery_source_sha256") != discovery_hash or meta.get("runner_sha256") != runner_hash
                or meta.get("shard_count") != shard_count or not isinstance(meta.get("shard_index"), int)
                or meta.get("policies") != list(candidates.POLICIES) or meta.get("provisional") is not True):
            raise ValueError(f"candidate shard metadata mismatch: {shard}")
        number = meta["shard_index"]
        if not 0 <= number < shard_count or number in numbers:
            raise ValueError("invalid or repeated shard index")
        numbers.add(number)
        comparable = {key: value for key, value in meta.items() if key not in ("shard_index", "selected_events", "expected_rows")}
        if uniform is None:
            uniform = comparable
        elif uniform != comparable:
            raise ValueError("candidate shard policies or environment differ")
        shard_hash, journal_hash = lunar.sha256(shard), lunar.sha256(journal_path)
        if (done.get("schema") != "moira-lunar-candidate-supplement-shard-receipt-v1"
                or done.get("provisional") is not True or done.get("complete_without_errors") is not True
                or done.get("output_sha256") != shard_hash or done.get("journal_sha256") != journal_hash
                or done.get("source_sha256") != source_hash or done.get("discovery_source_sha256") != discovery_hash
                or done.get("runner_sha256") != runner_hash or done.get("kernel_sha256") != kernel_hash):
            raise ValueError(f"incomplete, failed or altered candidate shard: {shard}")
        selected = lunar.read_index(index, number, shard_count)
        wanted = {(int(row["lunation_number"]), policy) for row in selected for policy in candidates.POLICIES}
        if (meta.get("selected_events") != len(selected) or meta.get("expected_rows") != len(wanted)
                or done.get("row_count") != len(wanted)):
            raise ValueError("candidate shard count does not match index partition")
        with shard.open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            if tuple(reader.fieldnames or ()) != candidates.FIELDS:
                raise ValueError("unexpected candidate shard schema")
            rows = list(reader)
        keys = [(int(row["lunation_number"]), row["policy"]) for row in rows]
        if len(keys) != len(set(keys)) or set(keys) != wanted:
            raise ValueError("candidate shard missing, duplicating or misplacing a policy row")
        for key, row in zip(keys, rows):
            if (key in merged or row["complete"] != "False" or row["status"] not in ("detected", "unresolved")
                    or int(row["catalog_index"]) != expected[key]["_catalog_index"]):
                raise ValueError("candidate status, completeness or discovery order is invalid")
            if row["status"] == "unresolved" and (not row["reason"] or row["candidate_type"]):
                raise ValueError("unresolved candidate must retain reason and no asserted type")
            if row["status"] == "detected" and (row["reason"] or row["candidate_type"] not in ("penumbral", "partial", "total")):
                raise ValueError("detected candidate must have a candidate type and no error reason")
            merged[key] = row
        counts = {name: sum(row["status"] == name for row in rows) for name in ("detected", "unresolved", "error")}
        if done.get("status_counts") != counts:
            raise ValueError("candidate shard status receipt does not match its rows")
        records.append({"path": str(shard), "sha256": shard_hash,
                        "metadata_sha256": lunar.sha256(meta_path), "receipt_sha256": lunar.sha256(done_path),
                        "journal_sha256": journal_hash, "shard_index": number, "rows": len(rows)})
    if set(merged) != set(expected) or numbers != set(range(shard_count)):
        raise ValueError("candidate shards do not account for the discovery identities and policies")

    def inputs_unchanged() -> bool:
        if (lunar.sha256(kernel) != kernel_hash or lunar.sha256(index) != index_hash
                or lunar.sha256(index_receipt) != receipt_hash or lunar.source_digest() != source_hash
                or discovery.source_fingerprint() != discovery_hash or lunar.sha256(Path(candidates.__file__)) != runner_hash):
            return False
        for record in records:
            shard = Path(record["path"])
            if (lunar.sha256(shard) != record["sha256"]
                    or lunar.sha256(shard.with_suffix(shard.suffix + ".metadata.json")) != record["metadata_sha256"]
                    or lunar.sha256(shard.with_suffix(shard.suffix + ".receipt.json")) != record["receipt_sha256"]
                    or lunar.sha256(shard.with_suffix(shard.suffix + ".journal.jsonl")) != record["journal_sha256"]):
                return False
        return True

    if not inputs_unchanged():
        raise RuntimeError("inputs changed during merge")
    with output.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=candidates.FIELDS)
        writer.writeheader()
        writer.writerows(merged[(int(row["lunation_number"]), policy)] for row in full_index for policy in candidates.POLICIES)
        stream.flush()
        os.fsync(stream.fileno())
    if not inputs_unchanged():
        raise RuntimeError("inputs changed during output writing; no receipt issued")
    statuses = {name: sum(row["status"] == name for row in merged.values()) for name in ("detected", "unresolved", "error")}
    receipt = {"schema": "moira-lunar-candidate-supplement-merge-v1", "provisional": True,
               "output_sha256": lunar.sha256(output), "row_count": len(merged), "status_counts": statuses,
               "index": str(index), "index_sha256": index_hash, "index_receipt_sha256": receipt_hash,
               "kernel_sha256": kernel_hash, "source_sha256": source_hash,
               "discovery_source_sha256": discovery_hash, "runner_sha256": runner_hash,
               "merger_sha256": lunar.sha256(Path(__file__)),
               "shards": sorted(records, key=lambda record: record["shard_index"]),
               "limits": uniform["limits"]}
    with finish.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"provisional": True, "rows": len(merged), "status_counts": statuses, "output": str(output)}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
