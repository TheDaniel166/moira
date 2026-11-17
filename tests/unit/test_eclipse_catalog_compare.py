"""Tests for provisional catalog comparison semantics and input integrity."""
import csv
import importlib.util
import json
from pathlib import Path

import pytest


path = Path(__file__).resolve().parents[2] / "scripts" / "eclipse_catalog" / "compare.py"
spec = importlib.util.spec_from_file_location("eclipse_catalog_compare", path)
compare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compare)


def test_skyfield_unique_unmatched_and_competing_are_preserved():
    rows = [
        {"skyfield_present": "True", "skyfield_jd_tt": "100.0", "lunation_number": "1"},
        {"skyfield_present": "True", "skyfield_jd_tt": "110.0", "lunation_number": ""},
        {"skyfield_present": "True", "skyfield_jd_tt": "120.0", "lunation_number": ""},
        {"skyfield_present": "True", "skyfield_jd_tt": "120.5", "lunation_number": ""},
        {"skyfield_present": "True", "skyfield_jd_tt": "130.0", "lunation_number": ""},
        {"skyfield_present": "False", "skyfield_jd_tt": ""},
    ]
    assigned, unresolved = compare.assign_skyfield(rows, {1: [100.1], 2: [120.1], 3: [129.0], 4: [131.0]})
    assert set(assigned) == {1}
    assert [r["status"] for r in unresolved] == ["unmatched", "ambiguous", "ambiguous", "ambiguous"]
    assert unresolved[-1]["candidate_lunations"] == [3, 4]


def test_broad_types_keep_lunar_penumbral_distinct_from_partial():
    assert compare.broad_type("Penumbral", "lunar") == "N"
    assert compare.broad_type("Partial", "lunar") == "P"
    assert compare.broad_type("H3", "solar") == "H"
    with pytest.raises(ValueError):
        compare.broad_type("N", "solar")


def test_historical_calendar_cutover_and_numeric_time_diff():
    assert compare.historical_jd(1582, 10, 4, "00:00:00") == 2299159.5
    assert compare.historical_jd(1582, 10, 15, "00:00:00") == 2299160.5
    changes = compare.compare_fields({"jd_tt": "2450000.0", "status": ""},
                                     {"jd_tt": "2450000.5", "status": "unresolved"})
    assert changes["jd_tt"]["delta_seconds"] == 43200
    assert changes["status"]["new"] == "unresolved"


def write_csv(path, fields, rows, delimiter=","):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, delimiter=delimiter)
        writer.writeheader()
        writer.writerows(rows)


def test_discovery_only_join_retains_missing_and_never_overwrites(tmp_path):
    index = tmp_path / "index.csv"
    fields = ["lunation_number", "jd_tt", "eclipse_type", "saros_series"]
    current = {"lunation_number": "1", "jd_tt": "2450000", "eclipse_type": "Total", "saros_series": "17"}
    write_csv(index, fields, [current])
    receipt = tmp_path / "receipt.json"
    receipt.write_text(json.dumps({"status": "provisional", "family": "lunar", "row_count": 1,
                                   "merged_sha256": compare.digest(index), "kernel_sha256": "test",
                                   "source_fingerprint_sha256": "source"}), encoding="utf-8")
    baseline = tmp_path / "baseline.csv"
    write_csv(baseline, fields, [current])
    old_detail = tmp_path / "old_detail.csv"
    write_csv(old_detail, fields, [current])
    nasa = tmp_path / "nasa.tsv"
    write_csv(nasa, ["astro_year", "month", "day", "tt", "lunation", "saros", "type"],
              [{"astro_year": "1995", "month": "Oct", "day": "9", "tt": "12:00:00",
                "lunation": "1", "saros": "017", "type": "T"},
               {"astro_year": "1996", "month": "Jan", "day": "1", "tt": "12:00:00",
                "lunation": "2", "saros": "018", "type": "N"}], delimiter="\t")
    reference = tmp_path / "skyfield.csv"
    write_csv(reference, ["lunation_number", "skyfield_present", "skyfield_type", "skyfield_jd_tt"],
              [{"lunation_number": "1", "skyfield_present": "True", "skyfield_type": "Total",
                "skyfield_jd_tt": "2450000"},
               {"lunation_number": "", "skyfield_present": "True", "skyfield_type": "Penumbral",
                "skyfield_jd_tt": "2000000"}])
    out = tmp_path / "results"
    args = ["--family", "lunar", "--discovery", str(index), "--discovery-receipt", str(receipt),
            "--baseline-index", str(baseline), "--baseline-detail", str(old_detail), "--nasa", str(nasa),
            "--reference", str(reference), "--output-dir", str(out)]
    assert compare.main(args) == 0
    rows = [json.loads(line) for line in (out / "rows.jsonl").read_text().splitlines()]
    assert len(rows) == 2 and rows[0]["presence"]["detail"] is None
    assert rows[1]["presence"]["current"] is False and rows[1]["presence"]["nasa"] is True
    unmatched = [json.loads(line) for line in (out / "unmatched_reference.jsonl").read_text().splitlines()]
    assert unmatched[0]["status"] == "unmatched"
    summary = json.loads((out / "summary.json").read_text())
    assert summary["counts"].get("current_nasa_saros_difference", 0) == 0
    with pytest.raises(RuntimeError, match="new and empty"):
        compare.main(args)


def test_detail_shard_receipt_binds_csv_index_and_discovery_source(tmp_path):
    path = tmp_path / "shard.csv"
    write_csv(path, ["lunation_number", "status"], [{"lunation_number": "1", "status": "ok"}])
    metadata = path.with_name(path.name + ".metadata.json")
    metadata.write_text(json.dumps({"index_sha256": "index", "index_receipt_sha256": "receipt",
                                    "discovery_source_sha256": "source"}), encoding="utf-8")
    receipt = tmp_path / "shard.receipt.json"
    receipt.write_text(json.dumps({"output_sha256": compare.digest(path), "kernel_sha256": "kernel",
                                  "row_count": 1, "complete_without_row_errors": True}), encoding="utf-8")
    assert set(compare.read_detail([path], [receipt], "index", "receipt", "source", "lunar", "kernel")) == {1}
    with pytest.raises(ValueError, match="discovery source"):
        compare.read_detail([path], [receipt], "index", "receipt", "wrong", "lunar", "kernel")
    with pytest.raises(ValueError, match="receipt mismatch"):
        compare.read_detail([path], [receipt], "index", "wrong", "source", "lunar", "kernel")
    receipt.write_text(json.dumps({"schema": "moira-native-lunar-detail-merge-v1",
        "provisional": True, "shards": [{"shard_index": 0}], "output_sha256": compare.digest(path),
        "kernel_sha256": "kernel", "row_count": 1, "index_sha256": "index",
        "index_receipt_sha256": "receipt", "discovery_source_sha256": "source"}), encoding="utf-8")
    assert set(compare.read_detail([path], [receipt], "index", "receipt", "source", "lunar", "kernel")) == {1}
    path.write_text("modified", encoding="utf-8")
    with pytest.raises(ValueError, match="digest mismatch"):
        compare.read_detail([path], [receipt], "index", "receipt", "source", "lunar", "kernel")


def test_solar_supplement_is_verified_and_unresolved_is_not_absence(tmp_path):
    fields = ["lunation_number", "jd_tt", "eclipse_type", "saros_series", "status"]
    row = {"lunation_number": "1", "jd_tt": "2450000", "eclipse_type": "Total",
           "saros_series": "17", "status": "ok"}
    index = tmp_path / "index.csv"
    baseline = tmp_path / "baseline.csv"
    detail = tmp_path / "detail.csv"
    for path in (index, baseline, detail):
        write_csv(path, fields, [row])
    receipt = tmp_path / "index.json"
    receipt.write_text(json.dumps({"status": "provisional", "family": "solar", "row_count": 1,
                                   "merged_sha256": compare.digest(index), "kernel_sha256": "kernel",
                                   "source_fingerprint_sha256": "source"}), encoding="utf-8")
    detail_receipt = tmp_path / "detail.json"
    detail_receipt.write_text(json.dumps({"merged_sha256": compare.digest(detail),
        "kernel_sha256": "kernel", "row_count": 1, "common": {
            "event_index_sha256": compare.digest(index),
            "event_index_receipt_sha256": compare.digest(receipt)}}), encoding="utf-8")
    nasa = tmp_path / "nasa.json"
    nasa.write_text(json.dumps({"rows": [[1, 1995, "Oct", 9, "12:00:00", 60, 1, 17, "T"]]}), encoding="utf-8")
    ref = tmp_path / "ew.csv"
    write_csv(ref, ["lunation", "type"], [{"lunation": "1", "type": "T"}])
    supplement = tmp_path / "supplement.jsonl"
    supplement.write_text(json.dumps({"lunation_number": 1, "status": "ok", "hybrid_status": "unresolved",
                                     "cap_status": "candidate", "cap_complete": False}) + "\n", encoding="utf-8")
    supplement_receipt = tmp_path / "supplement.json"
    supplement_receipt.write_text(json.dumps({"status": "provisional", "merged_sha256": compare.digest(supplement),
        "kernel_sha256": "kernel", "detail_sha256": compare.digest(detail), "row_count": 1}), encoding="utf-8")
    output = tmp_path / "out"
    args = ["--family", "solar", "--discovery", str(index), "--discovery-receipt", str(receipt),
            "--baseline-index", str(baseline), "--baseline-detail", str(baseline), "--nasa", str(nasa),
            "--reference", str(ref), "--detail", str(detail), "--detail-receipt", str(detail_receipt),
            "--supplement", str(supplement), "--supplement-receipt", str(supplement_receipt), "--output-dir", str(output)]
    assert compare.main(args) == 0
    result = json.loads((output / "rows.jsonl").read_text(encoding="utf-8"))
    assert result["solar_supplement"]["hybrid_status"] == "unresolved"
    assert result["solar_supplement"]["cap_complete"] is False


def test_lunar_candidates_keep_policies_and_unresolved_without_promoting_them(tmp_path):
    path = tmp_path / "candidates.csv"
    fields = ["lunation_number", "policy", "status", "complete", "reason"]
    rows = [{"lunation_number": "1", "policy": "danjon_angular", "status": "detected", "complete": "False"},
            {"lunation_number": "1", "policy": "static_finite_cone", "status": "unresolved",
             "complete": "False", "reason": "local search inconclusive"}]
    write_csv(path, fields, rows)
    meta = path.with_name(path.name + ".metadata.json")
    meta.write_text(json.dumps({"index_sha256": "index", "index_receipt_sha256": "receipt",
                                "discovery_source_sha256": "source"}), encoding="utf-8")
    receipt = tmp_path / "candidates.receipt.json"
    receipt.write_text(json.dumps({"schema": "moira-lunar-candidate-supplement-shard-receipt-v1",
        "provisional": True, "complete_without_errors": True, "row_count": 2,
        "output_sha256": compare.digest(path), "kernel_sha256": "kernel"}), encoding="utf-8")
    found = compare.read_lunar_candidates([path], [receipt], "index", "receipt", "source", "kernel", {1})
    assert found[1]["static_finite_cone"]["status"] == "unresolved"
    assert found[1]["danjon_angular"]["status"] == "detected"
    with pytest.raises(ValueError, match="both policies"):
        compare.read_lunar_candidates([path], [receipt], "index", "receipt", "source", "kernel", {1, 2})


def test_optional_nasa_compatible_discovery_preserves_mode_specific_identities(tmp_path):
    fields = ["lunation_number", "jd_tt", "eclipse_type", "saros_series"]
    native = tmp_path / "native.csv"
    compat = tmp_path / "compat.csv"
    write_csv(native, fields, [{"lunation_number": "1", "jd_tt": "2450000", "eclipse_type": "Total", "saros_series": "17"}])
    write_csv(compat, fields, [{"lunation_number": "2", "jd_tt": "2450100", "eclipse_type": "Penumbral", "saros_series": "18"}])
    native_receipt, compat_receipt = tmp_path / "native.json", tmp_path / "compat.json"
    native_receipt.write_text(json.dumps({"status": "provisional", "family": "lunar", "row_count": 1,
        "merged_sha256": compare.digest(native), "kernel_sha256": "kernel", "source_fingerprint_sha256": "source"}), encoding="utf-8")
    compat_receipt.write_text(json.dumps({"status": "provisional", "mode": "nasa_compat", "family": "lunar", "row_count": 1,
        "merged_sha256": compare.digest(compat), "kernel_sha256": "kernel", "source_fingerprint_sha256": "source"}), encoding="utf-8")
    compat_detail = tmp_path / "compat_detail.csv"
    write_csv(compat_detail, [*fields, "status"], [{"lunation_number": "2", "jd_tt": "2450100",
        "eclipse_type": "Penumbral", "saros_series": "18", "status": "ok"}])
    compat_detail_receipt = tmp_path / "compat_detail.json"
    compat_detail_receipt.write_text(json.dumps({"schema": "moira-nasa-compat-lunar-detail-merge-v1",
        "mode": "nasa_compat", "provisional": True, "shards": [{"shard_index": 0}],
        "output_sha256": compare.digest(compat_detail), "index_sha256": compare.digest(compat),
        "index_receipt_sha256": compare.digest(compat_receipt), "kernel_sha256": "kernel",
        "discovery_source_sha256": "source", "row_count": 1}), encoding="utf-8")
    nasa = tmp_path / "nasa.tsv"
    write_csv(nasa, ["astro_year", "month", "day", "tt", "lunation", "saros", "type"],
              [{"astro_year": "1996", "month": "Jan", "day": "17", "tt": "12:00:00",
                "lunation": "2", "saros": "018", "type": "N"}], delimiter="\t")
    ref = tmp_path / "skyfield.csv"
    write_csv(ref, ["lunation_number", "skyfield_present", "skyfield_type", "skyfield_jd_tt"], [])
    out = tmp_path / "out"
    assert compare.main(["--family", "lunar", "--discovery", str(native), "--discovery-receipt", str(native_receipt),
        "--compat-discovery", str(compat), "--compat-discovery-receipt", str(compat_receipt),
        "--compat-detail", str(compat_detail), "--compat-detail-receipt", str(compat_detail_receipt),
        "--baseline-index", str(native), "--baseline-detail", str(native), "--nasa", str(nasa),
        "--reference", str(ref), "--output-dir", str(out)]) == 0
    rows = [json.loads(line) for line in (out / "rows.jsonl").read_text().splitlines()]
    assert rows[0]["presence"]["current"] and not rows[0]["presence"]["compat"]
    assert rows[1]["presence"]["compat"] and not rows[1]["presence"]["current"]
    assert rows[1]["presence"]["compat_detail"] and rows[1]["compat_detail"]["status"] == "ok"
    assert rows[1]["broad_types"]["compat"] == "N"
    assert json.loads((out / "summary.json").read_text())["counts"]["native_compat_membership_difference"] == 2
