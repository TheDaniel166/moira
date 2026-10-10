from __future__ import annotations

import hashlib
import json
from pathlib import Path

from moira._spk_body_kernel import SmallBodyKernel
from moira.daf_writer import write_spk_type13
from scripts import build_comet_catalog
from scripts import refresh_comet_catalog_solutions as refresh
from scripts.audit_comet_solution_freshness import SCHEMA as AUDIT_SCHEMA


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _body(number: int, offset: float, solution: str) -> dict[str, object]:
    epochs = [2451545.0 + index for index in range(7)]
    states = [
        [offset + axis * 100.0 + index for index in range(7)]
        for axis in range(6)
    ]
    return {
        "number": number,
        "naif_id": 1_000_000 + number,
        "name": f"{number}P/Test",
        "center": 10,
        "frame": 1,
        "states": states,
        "epochs_jd": epochs,
        "window_size": 7,
        "clamped": False,
        "start": "2000-01-01",
        "stop": "2000-01-07",
        "target_solution": solution,
        "sampling_policy": build_comet_catalog._sampling_policy(),
        "base_nodes": 7,
        "adaptive_nodes": 0,
        "extremum_brackets": 0,
        "apsidal_sampling_certificate": {"status": "certified", "passed": True},
        "response_receipts": {"base": {"sha256": solution}},
    }


def _record(body: dict[str, object]) -> dict[str, object]:
    return {
        "number": body["number"],
        "naif_id": body["naif_id"],
        "name": body["name"],
        "full_name": body["name"],
        "nodes": 7,
        "clamped": False,
        "start": body["start"],
        "stop": body["stop"],
        "fetch_s": 0.0,
        "target_solution": body["target_solution"],
        "sampling_policy": body["sampling_policy"],
        "base_nodes": 7,
        "adaptive_nodes": 0,
        "extremum_brackets": 0,
        "apsidal_sampling_certificate": body["apsidal_sampling_certificate"],
        "response_receipts": body["response_receipts"],
        "max_node_error_km": 0.0,
    }


def test_refresh_replaces_only_stale_body_and_preserves_source(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()
    first = _body(1, 1000.0, "JPL#1")
    stale = _body(2, 2000.0, "JPL#OLD")
    kernel_path = source / "comet_shard_000.bsp"
    write_spk_type13(kernel_path, bodies=[first, stale])
    records = [_record(first), _record(stale)]
    metadata = {
        "shard": 0,
        "kernel": kernel_path.name,
        "kernel_bytes": kernel_path.stat().st_size,
        "window": ["1600-01-01", "2500-01-01"],
        "step_days": 10,
        "window_size": 7,
        "sampling_policy": build_comet_catalog._sampling_policy(),
        "records": records,
        "failures": [],
        "naif_map": {record["name"]: record["naif_id"] for record in records},
    }
    (source / "comet_shard_000.metadata.json").write_text(
        json.dumps(metadata), encoding="utf-8"
    )
    master = {
        "requested": 2,
        "built": 2,
        "failed": 0,
        "sampling_policy": build_comet_catalog._sampling_policy(),
        "records": records,
        "failures": [],
        "naif_map": metadata["naif_map"],
    }
    master_path = source / "comet_master.json"
    master_path.write_text(json.dumps(master), encoding="utf-8")
    build_comet_catalog._write_manifest(source)
    source_kernel_sha = _sha256(kernel_path)
    source_master_sha = _sha256(master_path)
    audit_path = tmp_path / "audit.json"
    audit_path.write_text(
        json.dumps(
            {
                "schema": AUDIT_SCHEMA,
                "completed": True,
                "catalog_master_sha256": source_master_sha,
                "summary": {"error": 0, "stale": 1},
                "records": [
                    {
                        "number": 1,
                        "status": "match",
                        "current_target_solution": "JPL#1",
                    },
                    {
                        "number": 2,
                        "status": "stale",
                        "current_target_solution": "JPL#NEW",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    replacement = _body(2, 9000.0, "JPL#NEW")
    calls: list[int] = []
    monkeypatch.setattr(
        refresh.builder,
        "_fetch_comet",
        lambda number: calls.append(number) or replacement,
    )
    monkeypatch.setattr(refresh.builder, "THROTTLE_S", 0.0)

    result = refresh.refresh_catalog(source, output, audit_path)

    assert calls == [2]
    assert result["receipt"]["refreshed_numbers"] == [2]
    assert _sha256(kernel_path) == source_kernel_sha
    assert _sha256(master_path) == source_master_sha
    output_master = json.loads((output / "comet_master.json").read_text())
    assert [record["target_solution"] for record in output_master["records"]] == [
        "JPL#1",
        "JPL#NEW",
    ]
    kernel = SmallBodyKernel(output / "comet_shard_000.bsp")
    try:
        assert kernel.position_tdb(10, 1_000_001, 2451545.0)[0] == 1000.0
        assert kernel.position_tdb(10, 1_000_002, 2451545.0)[0] == 9000.0
    finally:
        kernel.close()
