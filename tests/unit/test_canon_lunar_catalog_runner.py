"""NASA-compatible detailed catalog contract and real-ephemeris controls."""
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
spec = importlib.util.spec_from_file_location("canon_lunar_detail", SCRIPTS / "canon_lunar_detail.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
sys.modules["canon_lunar_detail"] = runner
merge_spec = importlib.util.spec_from_file_location("canon_lunar_merge_test", SCRIPTS / "merge_canon_lunar_detail.py")
merger = importlib.util.module_from_spec(merge_spec)
merge_spec.loader.exec_module(merger)


@pytest.fixture
def catalog_case(tmp_path, monkeypatch):
    kernel = tmp_path / "kernel.bsp"
    kernel.write_bytes(b"synthetic kernel")
    index = tmp_path / "discovery.csv"
    rows = [dict(family="lunar", jd_tt=n, jd_ut1=n-.1, lunation_number=n) for n in (1, 2)]
    with index.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    receipt = tmp_path / "receipt.json"
    receipt.write_text(json.dumps({"status": "provisional", "family": "lunar", "mode": "nasa_compat",
        "runner_sha256": runner.sha256(SCRIPTS / "canon_discovery.py"),
        "merged_sha256": runner.sha256(index), "kernel_sha256": runner.sha256(kernel),
        "source_fingerprint_sha256": "fake-discovery-source", "row_count": len(rows)}), encoding="utf-8")
    monkeypatch.setattr(runner, "find_planetary_kernel", lambda: kernel)
    monkeypatch.setattr(runner, "source_digest", lambda: "fake-detail-source")
    monkeypatch.setattr(runner.discovery, "source_fingerprint", lambda: "fake-discovery-source")
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
    args = ["--index", str(index), "--index-receipt", str(receipt), "--output", str(output),
            "--kernel-sha256", runner.sha256(kernel)]
    return args, output, index, receipt


def test_rejects_native_receipt_and_does_not_overwrite(catalog_case):
    args, output, _, receipt = catalog_case
    data = json.loads(receipt.read_text(encoding="utf-8"))
    data["mode"] = "native"
    receipt.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="discovery receipt"):
        runner.main(args)
    assert not output.exists()


def test_shard_resume_and_checked_merge(catalog_case, monkeypatch):
    args, output, index, index_receipt = catalog_case
    monkeypatch.setattr(runner, "calculate_row", lambda calc, entry: {
        "catalog_index": entry["_catalog_index"], "lunation_number": int(entry["lunation_number"]),
        "lunar_mode": "nasa_compat", "status": "ok", "error": ""})
    shards = [output.with_name("shard0.csv"), output.with_name("shard1.csv")]
    for number, shard in enumerate(shards):
        subset = list(args)
        subset[subset.index("--output") + 1] = str(shard)
        subset += ["--shard-index", str(number), "--shard-count", "2"]
        assert runner.main(subset) == 0
        with pytest.raises(FileExistsError):
            runner.main(subset)
    merge_args = ["--index", str(index), "--index-receipt", str(index_receipt), "--output", str(output),
                  "--kernel-sha256", args[args.index("--kernel-sha256") + 1],
                  "--shard", str(shards[1]), "--shard", str(shards[0])]
    assert merger.main(merge_args) == 0
    with output.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert [r["lunation_number"] for r in rows] == ["1", "2"]
    assert all(r["lunar_mode"] == "nasa_compat" for r in rows)
    with pytest.raises(FileExistsError):
        merger.main(merge_args)
    shards[0].write_text(shards[0].read_text(encoding="utf-8") + "\n", encoding="utf-8")
    merge_args[merge_args.index("--output") + 1] = str(output.with_name("other.csv"))
    with pytest.raises(ValueError, match="altered shard"):
        merger.main(merge_args)


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("year,month,day", [(2022, 11, 7), (-1903, 2, 1)])
def test_real_canon_detail_matches_public_compatibility_view(eclipse_calculator, year, month, day):
    from moira.compat.nasa.eclipse import translate_lunar_eclipse_event
    from moira.julian import julian_day

    event = eclipse_calculator.next_lunar_eclipse_canon(julian_day(year, month, day))
    entry = {"lunation_number": event.data.saros_lunation_number, "jd_ut1": event.jd_ut,
             "eclipse_type": str(event.data.eclipse_type), "_catalog_index": 1}
    row = runner.calculate_row(eclipse_calculator, entry)
    direct = translate_lunar_eclipse_event(eclipse_calculator, event)
    assert row["status"] == "ok" and row["lunar_mode"] == "nasa_compat"
    assert row["canon_method"] == direct.canon_method
    assert row["lunation_number"] == entry["lunation_number"]
    assert abs(row["jd_ut1"] - direct.jd_ut) * 86400 < 0.1
    assert abs(row["gamma_earth_radii"] - direct.gamma_earth_radii) < 1e-6
    for name in ("p1", "u1", "u2", "u3", "u4", "p4"):
        actual, expected = row[name + "_jd_ut1"], getattr(direct.contacts, name + "_ut")
        assert (actual is None) == (expected is None)
        if actual is not None:
            assert abs(actual - expected) * 86400 < 0.1
