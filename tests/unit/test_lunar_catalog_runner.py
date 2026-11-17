"""Contract checks for the provisional lunar catalog validation runner."""
from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "eclipse_catalog"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("lunar_catalog_test_runner", SCRIPTS / "lunar_detail.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
sys.modules["lunar_detail"] = runner
merge_spec = importlib.util.spec_from_file_location("lunar_catalog_test_merger", SCRIPTS / "merge_lunar_detail.py")
merger = importlib.util.module_from_spec(merge_spec)
merge_spec.loader.exec_module(merger)


@pytest.fixture
def catalog_case(tmp_path, monkeypatch):
    kernel = tmp_path / "kernel.bsp"
    kernel.write_bytes(b"test kernel, no astronomical content")
    index = tmp_path / "discovery.csv"
    rows = [
        {"family": "lunar", "jd_tt": 1, "jd_ut1": 0.9, "lunation_number": 1},
        {"family": "lunar", "jd_tt": 2, "jd_ut1": 1.9, "lunation_number": 2},
    ]
    with index.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    index_receipt = tmp_path / "receipt.json"
    index_receipt.write_text(json.dumps({"status": "provisional", "family": "lunar",
        "merged_sha256": runner.sha256(index), "kernel_sha256": runner.sha256(kernel),
        "source_fingerprint_sha256": "discovery-source", "row_count": len(rows)}), encoding="utf-8")
    monkeypatch.setattr(runner, "find_planetary_kernel", lambda: kernel)
    monkeypatch.setattr(runner, "source_digest", lambda: "detail-source")
    monkeypatch.setattr(runner.discovery, "source_fingerprint", lambda: "discovery-source")
    class Reader:
        def __init__(self, path):
            assert path == kernel
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
    monkeypatch.setattr(runner, "SpkReader", Reader)
    monkeypatch.setattr(runner, "EclipseCalculator", lambda **kwargs: object())
    output = tmp_path / "detail.csv"
    args = ["--index", str(index), "--index-receipt", str(index_receipt),
            "--output", str(output), "--kernel-sha256", runner.sha256(kernel)]
    return args, output, index, index_receipt


def test_resume_preserves_error_attempt_and_requires_explicit_resume(catalog_case, monkeypatch):
    args, output, _, _ = catalog_case
    def first(calc, entry):
        if int(entry["lunation_number"]) == 2:
            raise ValueError("simulated failure")
        return {"lunation_number": 1, "status": "ok", "error": ""}
    monkeypatch.setattr(runner, "calculate_row", first)
    assert runner.main(args) == 1
    with output.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert [r["status"] for r in rows] == ["ok", "error"]
    with pytest.raises(FileExistsError):
        runner.main(args)
    monkeypatch.setattr(runner, "calculate_row", lambda calc, entry: {
        "lunation_number": int(entry["lunation_number"]), "status": "ok", "error": ""})
    assert runner.main(args + ["--resume"]) == 0
    ledger = output.with_suffix(".csv.journal.jsonl").read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["status"] for line in ledger] == ["ok", "error", "ok"]


def test_rejects_receipt_that_does_not_hash_discovery(catalog_case):
    args, output, index, _ = catalog_case
    index.write_text(index.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="discovery receipt"):
        runner.main(args)
    assert not output.exists()


def test_index_rejects_duplicate_and_unordered_lunations(tmp_path):
    index = tmp_path / "index.csv"
    index.write_text("lunation_number,jd_tt,jd_ut1\n1,1,1\n1,2,2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        runner.read_index(index, 0, 1)
    index.write_text("lunation_number,jd_tt,jd_ut1\n1,2,2\n2,1,1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="strictly increasing"):
        runner.read_index(index, 0, 1)


@pytest.mark.requires_ephemeris
def test_real_de441_total_event_row_retains_identity_contacts_and_margins(eclipse_calculator):
    from moira.julian import julian_day

    event = eclipse_calculator.next_lunar_eclipse(julian_day(2022, 11, 7))
    entry = {"lunation_number": event.data.saros_lunation_number,
             "jd_ut1": event.jd_ut, "_catalog_index": 1}
    row = runner.calculate_row(eclipse_calculator, entry)
    assert row["status"] == "ok"
    assert row["lunation_number"] == entry["lunation_number"]
    assert row["eclipse_type"] == "Total"
    assert row["p1_jd_ut1"] < row["u1_jd_ut1"] < row["u2_jd_ut1"] < row["jd_ut1"]
    assert row["jd_ut1"] < row["u3_jd_ut1"] < row["u4_jd_ut1"] < row["p4_jd_ut1"]
    assert row["penumbral_margin_earth_radii"] > row["umbral_margin_earth_radii"] > row["total_margin_earth_radii"] > 0


def test_merge_checks_shard_hashes_and_maintains_discovery_order(catalog_case, monkeypatch):
    args, output, index, index_receipt = catalog_case
    monkeypatch.setattr(runner, "calculate_row", lambda calc, entry: {
        "catalog_index": entry["_catalog_index"], "lunation_number": int(entry["lunation_number"]),
        "status": "ok", "error": ""})
    shard0 = output.with_name("shard0.csv")
    shard1 = output.with_name("shard1.csv")
    def shard_args(path, number):
        copy = list(args)
        copy[copy.index("--output") + 1] = str(path)
        return copy + ["--shard-index", str(number), "--shard-count", "2"]
    assert runner.main(shard_args(shard0, 0)) == 0
    assert runner.main(shard_args(shard1, 1)) == 0
    merge_args = ["--index", str(index), "--index-receipt", str(index_receipt),
                  "--output", str(output), "--kernel-sha256", args[args.index("--kernel-sha256") + 1],
                  "--shard", str(shard1), "--shard", str(shard0)]
    assert merger.main(merge_args) == 0
    with output.open(encoding="utf-8", newline="") as f:
        assert [r["lunation_number"] for r in csv.DictReader(f)] == ["1", "2"]
    with pytest.raises(FileExistsError):
        merger.main(merge_args)
    shard0.write_text(shard0.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    other_output = output.with_name("other.csv")
    merge_args[merge_args.index("--output") + 1] = str(other_output)
    with pytest.raises(ValueError, match="altered shard"):
        merger.main(merge_args)
    assert not other_output.exists()
