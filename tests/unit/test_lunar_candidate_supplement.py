"""Contract checks for opt-in, uncertified lunar catalog candidate rows."""
from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "eclipse_catalog"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("test_lunar_candidate_supplement_runner", SCRIPTS / "lunar_candidate_supplement.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
sys.modules["lunar_candidate_supplement"] = runner
merge_spec = importlib.util.spec_from_file_location("test_lunar_candidate_supplement_merger", SCRIPTS / "merge_lunar_candidate_supplement.py")
merger = importlib.util.module_from_spec(merge_spec)
merge_spec.loader.exec_module(merger)


def test_non_detection_and_unsupported_domain_are_unresolved(monkeypatch):
    entry = {"lunation_number": 1, "jd_ut1": 10., "_catalog_index": 1}
    monkeypatch.setattr(runner, "inspect_lunar_shadow_candidate", lambda *a, **kw:
                        SimpleNamespace(complete=False, status="unresolved", event=None, reason="not certified"))
    row = runner.calculate_candidate(object(), entry, "danjon_angular")
    assert row["status"] == "unresolved" and row["complete"] is False
    assert "candidate_type" not in row
    def unsupported(*args, **kwargs):
        raise runner.LunarShadowDomainError("outside supported geometry")
    monkeypatch.setattr(runner, "inspect_lunar_shadow_candidate", unsupported)
    row = runner.calculate_candidate(object(), entry, "static_finite_cone")
    assert row["status"] == "unresolved" and "outside supported geometry" in row["reason"]


def test_output_separates_policy_rows_and_retry_errors(tmp_path, monkeypatch):
    kernel = tmp_path / "kernel.bsp"
    kernel.write_bytes(b"fake kernel")
    index = tmp_path / "index.csv"
    index.write_text("family,jd_tt,jd_ut1,lunation_number\nlunar,2,1.9,1\n", encoding="utf-8")
    receipt = tmp_path / "index-receipt.json"
    receipt.write_text(json.dumps({"status": "provisional", "family": "lunar", "row_count": 1,
        "merged_sha256": runner.lunar.sha256(index), "kernel_sha256": runner.lunar.sha256(kernel),
        "source_fingerprint_sha256": "frozen"}), encoding="utf-8")
    monkeypatch.setattr(runner.lunar, "find_planetary_kernel", lambda: kernel)
    monkeypatch.setattr(runner.lunar, "source_digest", lambda: "frozen-detail")
    monkeypatch.setattr(runner.discovery, "source_fingerprint", lambda: "frozen")
    class Reader:
        def __init__(self, path):
            assert path == kernel
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
    monkeypatch.setattr(runner, "SpkReader", Reader)
    monkeypatch.setattr(runner, "EclipseCalculator", lambda **kwargs: object())
    def candidate(calculator, entry, policy):
        if policy == "static_finite_cone":
            raise RuntimeError("failed")
        return {"lunation_number": 1, "catalog_index": 1, "policy": policy,
                "status": "unresolved", "reason": "not excluded", "complete": False}
    monkeypatch.setattr(runner, "calculate_candidate", candidate)
    output = tmp_path / "candidates.csv"
    args = ["--index", str(index), "--index-receipt", str(receipt),
            "--output", str(output), "--kernel-sha256", runner.lunar.sha256(kernel)]
    assert runner.main(args) == 1
    with output.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert [row["status"] for row in rows] == ["unresolved", "error"]
    assert all(row["complete"] == "False" for row in rows)
    with pytest.raises(FileExistsError):
        runner.main(args)
    monkeypatch.setattr(runner, "calculate_candidate", lambda calc, entry, policy: {
        "lunation_number": 1, "catalog_index": 1, "policy": policy,
        "status": "unresolved", "reason": "not excluded", "complete": False})
    assert runner.main(args + ["--resume"]) == 0
    ledger = output.with_suffix(".csv.journal.jsonl").read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["status"] for line in ledger] == ["unresolved", "error", "unresolved"]
    merged = tmp_path / "merged.csv"
    merge_args = ["--index", str(index), "--index-receipt", str(receipt),
                  "--output", str(merged), "--kernel-sha256", runner.lunar.sha256(kernel),
                  "--shard", str(output)]
    assert merger.main(merge_args) == 0
    merged_receipt = json.loads(merged.with_suffix(".csv.receipt.json").read_text(encoding="utf-8"))
    assert merged_receipt["status_counts"] == {"detected": 0, "unresolved": 2, "error": 0}
    assert merged_receipt["index_sha256"] == runner.lunar.sha256(index)
    output.write_text(output.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    merge_args[merge_args.index("--output") + 1] = str(tmp_path / "altered.csv")
    with pytest.raises(ValueError, match="altered candidate shard"):
        merger.main(merge_args)


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("policy", ["danjon_angular", "static_finite_cone"])
def test_de441_controls_keep_non_native_candidate_labels(eclipse_calculator, policy):
    from moira.julian import julian_day
    entry = {"lunation_number": 253, "jd_ut1": julian_day(2020, 7, 5, 4.5), "_catalog_index": 1}
    row = runner.calculate_candidate(eclipse_calculator, entry, policy)
    assert row["status"] == "detected" and row["complete"] is False
    assert row["candidate_type"] == "penumbral"
    assert row["margin_unit"] == ("rad" if policy == "danjon_angular" else "km")
    assert row["p1_jd_ut1"] < row["penumbral_max_jd_ut1"] < row["p4_jd_ut1"]
